import asyncio
from datetime import datetime, timedelta
from fastapi import FastAPI
from fastapi.concurrency import asynccontextmanager
import httpx
import sqlite3
from fastapi.responses import HTMLResponse
import json
import os
import glob
import pandas as pd

def get_db_connection():
    return sqlite3.connect(db_name)

API_KEY = "7debd621db3e040663ecb13aa169325090cb094e55374cd3ae4531f2af397383"
url = "http://apis.data.go.kr/B552584/ArpltnInforInqireSvc/getMsrstnAcctoRltmMesureDnsty"
db_name = "dustlist.db"
db_name0="finedust.db"

guList = [
    "강남구", "강동구", "강북구", "강서구", "관악구", 
    "광진구", "구로구", "금천구", "노원구", "도봉구", 
    "동작구", "마포구", "서대문구", "서초구", "성동구", 
    "성북구", "송파구", "양천구", "영등포구", "용산구", 
    "은평구", "종로구", "중구", "중랑구", "동대문구"
]



async def fetch_data(client, location, sem, start_date, end_date):
    # 💡 [진짜 해결책] msrstnName을 'stationName'으로, dataGubun을 'dataTerm'으로 정확히 교정했습니다.
    params = {
        "serviceKey": API_KEY,
        "returnType": "json",
        "numOfRows": "100",
        "pageNo": "1",
        "stationName": location,   # 💡 정부 문서상 정식 명칭
        "dataTerm": "DAILY",       # 💡 정부 문서상 정식 명칭
        "ver": "1.3"
    }
    
    async with sem:
        try:
            response = await client.get(url, params=params, timeout=15.0)
            if "application/json" not in response.headers.get("content-type", "").lower():
                return []
                
            raw_data = response.json()
            items = raw_data.get("response", {}).get("body", {}).get("items", [])
        except Exception:
            return []

    if not items:
        return []
        
    refined_result = []
    for item in items:
        station = item.get("stationName") or location
        # 실시간 API 응답 날짜 형식: "2026-07-22 14:00"
        raw_time = (item.get("dataTime") or "").strip()
        
        if raw_time and len(raw_time) >= 10:
            date_part = raw_time[:10]  # "2026-07-22"만 분리
            
            # 어제/오늘 범위 내에 매칭되는 데이터 필터링
            if start_date <= date_part <= end_date:
                refined_result.append({
                    "location": station,       
                    "dataTime": raw_time, 
                    "dustValue": item.get("pm10Value")
                })
            
    if refined_result:
        print(f"✅ [{location}] 어제/오늘 데이터 수집 성공 -> {len(refined_result)}건")
    return refined_result

async def update_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 테이블이 없을 때를 대비해 임시로 먼저 생성해 줍니다.
    cursor.execute(
        "CREATE TABLE IF NOT EXISTS dust_history (location TEXT, dataTime TEXT, dustValue TEXT)"
    )
    
    # 현재 DB에 저장된 미세먼지 데이터 개수를 확인합니다.
    cursor.execute("SELECT COUNT(*) FROM dust_history")
    if cursor.fetchone()[0] > 0:
        print("▶ [안내] DB에 데이터가 이미 존재합니다. 외부 API 수집을 건너뜁니다.")
        conn.close()
        return # ★ 데이터가 있으면 여기서 즉시 함수를 끝내버립니다. (아래 코드가 절대 안 돕니다)
    
    conn.close()
    
    
    tasks = []
    sem = asyncio.Semaphore(3)  
    
    today = datetime.now()
    yesterday = today - timedelta(days=1)
    
    # "YYYY-MM-DD" 하이픈 구조 유지
    start_date_str = yesterday.strftime("%Y-%m-%d")
    end_date_str = today.strftime("%Y-%m-%d")

    print(f"\n🚀 [파라미터 교정 완료] 어제/오늘 날짜 필터 기한: {start_date_str} ~ {end_date_str}")
    
    async with httpx.AsyncClient() as client:
        for gu in guList:
            tasks.append(fetch_data(client, gu, sem, start_date_str, end_date_str))
        results = await asyncio.gather(*tasks)

    flat_results = [item for sublist in results if sublist for item in sublist]
    
    # 시간 최신순 정렬
    flat_results.sort(key=lambda x: x["dataTime"], reverse=True)
    
    print(f"🏁 정제 프로세스 완료! 최종 매칭 데이터: {len(flat_results)}건\n")
    
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "CREATE TABLE IF NOT EXISTS dust_history (location TEXT, dataTime TEXT, dustValue TEXT)"
    )
    cursor.execute("DELETE FROM dust_history")
    
    for item in flat_results:
        cursor.execute(
            "INSERT INTO dust_history (location, dataTime, dustValue) VALUES (?, ?, ?)",
            (item["location"], item["dataTime"], item["dustValue"]),
        )
    
    conn.commit()
    conn.close()
    print("💾 SQL에 저장을 완료했습니다!")
    
def get_files():
    current_dir = os.path.dirname(os.path.abspath(__file__))
    folder_path = os.path.join(current_dir, "dust_files")
    
    all_files = glob.glob(os.path.join(folder_path, "*.csv"))
    
    conn=sqlite3.connect(db_name0)
    cursor=conn.cursor()

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS finedust (
            location TEXT, 
            dataTime TEXT, 
            dustValue INTEGER
        )
    ''')
    
    cursor.execute("SELECT COUNT(*) FROM finedust")
    if cursor.fetchone()[0] > 0:
        print("이미 db가 있습니다. API불필요")
        final_df = pd.read_sql_query("SELECT location, dataTime, dustValue FROM predict_history", conn)
        conn.close()
        final_df['date'] = final_df['dataTime'].str[:10]
        target_gus = ['중구', '강북구', '강남구', '서초구']
        final_df = final_df[final_df['location'].isin(target_gus)]
        summary_table = final_df.groupby(['location', 'date'])['dustValue'].mean().round(1).unstack(fill_value=0)
        
        import matplotlib.pyplot as plt
        import io, base64
        plt.rcParams['font.family'] = 'Malgun Gothic'

        summary_table.T.plot(kind='line', marker='o', figsize=(10, 4), grid=True)
        buf = io.BytesIO()
        plt.savefig(buf, format='png', bbox_inches='tight')
        img_base64 = base64.b64encode(buf.getvalue()).decode('utf-8')
        plt.close()
        
        return summary_table.to_html(), img_base64
    
    df_list = []
    total_rows = 0
    for file_path in all_files:
        target_cols = ['주소','측정일시','측정소명','PM10']
        # CSV 파일 읽기 (cp949 인코딩 적용)
        df_csv = pd.read_csv(file_path, usecols=target_cols, encoding='cp949')
        df_csv = df_csv[df_csv['주소'].str.contains('서울', na=False)]
        
        if df_csv.empty:
            continue
            
        # [핵심 수정 1] 날짜가 2024112314 같은 연속된 숫자일 때 글자를 강제로 쪼개 안전하게 파싱합니다.
        str_date = df_csv['측정일시'].astype(str).str.strip()
        
        # 기본 믹스드 파싱 시도
        parsed_date = pd.to_datetime(str_date, format='mixed', errors='coerce')
        
        # 만약 판다스 파싱이 실패해서 전부 NaT(빈값)가 되었다면 수동으로 글자를 쪼갭니다.
        if parsed_date.isnull().all():
            # 앞 4자리(년)-중간2자리(월)-그다음2자리(일) 조합
            safe_date_str = str_date.str[:4] + '-' + str_date.str[4:6] + '-' + str_date.str[6:8]
            parsed_date = pd.to_datetime(safe_date_str, errors='coerce')
            
        df_to_db = pd.DataFrame({
            'location': df_csv['측정소명'],
            # DB용 풀 날짜 포맷 (%Y-%m-%d %H:%M)
            'dataTime': parsed_date.dt.strftime('%Y-%m-%d %H:%M').fillna("1970-01-01 00:00"),
            'dustValue': pd.to_numeric(df_csv['PM10'], errors='coerce').fillna(0).astype(int)
        })
        
        # [핵심 수정 2] 중복 저장되던 append 코드를 한 줄만 남기고 지웠습니다.
        df_list.append(df_to_db)
            
        file_name = os.path.basename(file_path)
        print(f"  -> 📄 {file_name}: 서울 데이터 {len(df_to_db)}건 추출 완료")
    
    if df_list:
        final_df = pd.concat(df_list, ignore_index=True)
        
        # 'dataTime' 문자열에서 앞 10자리(YYYY-MM-DD) 추출
        final_df['date'] = final_df['dataTime'].str[:10]
        
        # [핵심 수정] 측정소명(location)이 '~구'로 끝나는 정상 자치구 데이터만 남깁니다.
        # (강남대로, 강변북로, 홍릉로 같은 도로변 측정소 자동 제거)
        eng_gus = {'중구': 'Jung-gu', '강북구': 'Gangbuk-gu', '강남구': 'Gangnam-gu', '서초구': 'Seocho-gu'}
        final_df['location'] = final_df['location'].map(eng_gus)
        summary_table = final_df.groupby(['location', 'date'])['dustValue'].mean().round(1).unstack(fill_value=0)
        
        import matplotlib.pyplot as plt
        import io, base64
        # plt.rcParams['font.family'] = 'Malgun Gothic' # 한글 깨짐 방지

        # 1. 엑셀 차트 그리듯 plt.plot으로 선 그래프 그리기
        summary_table.T.plot(kind='line', marker='o', figsize=(10, 4), grid=True)
        
        # 2. 그린 그래프를 글자 코드(img_base64)로 임시 변환하기
        buf = io.BytesIO()
        plt.savefig(buf, format='png', bbox_inches='tight')
        img_base64 = base64.b64encode(buf.getvalue()).decode('utf-8')
        plt.close() # 메모리 청소

        # 3. 데이터베이스 저장 후 두 개를 메인 화면으로 전달
        final_df[['location', 'dataTime', 'dustValue']].to_sql("predict_history", conn, if_exists="append", index=False)
        conn.commit()
        conn.close()
        
        return summary_table.to_html(), img_base64
    
    conn.close()
    return None

def get_gangnam_data():
    # DB에서 강남구의 날짜별 미세먼지 평균 데이터를 가져옵니다.
    conn = sqlite3.connect(db_name0)
    query = """
        SELECT substr(dataTime, 1, 10) as date, AVG(dustValue) as dustValue
        FROM predict_history
        WHERE location = '강남구'
        GROUP BY date
        ORDER BY date ASC
    """
    gangnam_df = pd.read_sql(query, conn)
    conn.close()

    if gangnam_df.empty:
        return [], []

    # 날짜 리스트와 수치 리스트를 나누어 반환합니다.
    return gangnam_df['dustValue'].tolist(), gangnam_df['date'].tolist()