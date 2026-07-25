import asyncio
from datetime import datetime, timedelta
from fastapi import FastAPI
from fastapi.concurrency import asynccontextmanager
import httpx
import sqlite3
from fastapi.responses import HTMLResponse
import json
import templates
import database
import os
import glob
import matplotlib.pyplot as plt
import pandas as pd 
from statsmodels.tsa.stattools import acf, pacf
import templates0

plt.rcParams['font.family'] = 'Malgun Gothic'  # 윈도우 기본 한글 폰트 설정
plt.rcParams['axes.unicode_minus'] = False 

API_KEY = "7debd621db3e040663ecb13aa169325090cb094e55374cd3ae4531f2af397383"
url = "http://apis.data.go.kr/B552584/ArpltnInforInqireSvc/getMsrstnAcctoRltmMesureDnsty"
db_name = "dustlist.db"

def get_db_connection():
    return sqlite3.connect(db_name)

async def my_api_scheduler():
    while True:
        try:
            print("🌐 [스케줄러] 1시간 주기가 되어 실시간 API를 딱 1번 호출합니다...")
            database.update_db()  # 실시간 최신 미세먼지 수집 가동!
        except Exception as e:
            print(f"🚨 스케줄러 API 수집 대기 중 (Quota 초과 등): {e}")

        await asyncio.sleep(3600)  # 다음 수집 때까지 정확히 1시간(3600초) 휴식!

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("⏳ 서버 시작 중... 최신 미세먼지 데이터를 가져옵니다.")   
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS dust_history (
            location TEXT, 
            dataTime TEXT, 
            dustValue TEXT
        )
    """)
    
    cursor.execute("create index if not exists idx_time on dust_history(dataTime desc)")
    conn.commit()
    conn.close()    

    asyncio.create_task(database.update_db())  # 여기서 한 번 수집하므로 홈페이지 열 때는 유저 대기 시간이 없습니다.
    yield
    print("⏳ 서버가 종료됩니다.")

app = FastAPI(lifespan=lifespan)

@app.get("/", response_class=HTMLResponse)
async def get_data(selected_time: str = None,background_tasks: BackgroundTasks):
    global scheduler_started
    
    if not scheduler_started and background_tasks:
        background_tasks.add_task(my_api_scheduler)
        scheduler_started=True
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute(""" select distinct dataTime from dust_history order by dataTime desc """)
    time_rows = cursor.fetchall()
    if not selected_time and time_rows:
            selected_time = time_rows[0][0]
            
    cursor.execute(
        "SELECT location, dataTime, dustValue FROM dust_history WHERE dataTime = ?", 
        (selected_time,)
    )  
    rows = cursor.fetchall()
    conn.close()
    
    last_results = []
    for row in rows:
        last_results.append({
            "location": row[0],
            "dustValue": row[2]
        })
            
    options_html = ""
    for time in time_rows:
        # time[0]을 사용해 튜플 안의 진짜 시간 글자를 꺼내어 단추 문장을 만듭니다.
        is_selected = "selected" if time[0] == selected_time else ""
        options_html += f'<option value="{time[0]}" {is_selected}>{time[0]}</option>'
      
    json_data = json.dumps(last_results, ensure_ascii=False)
    
    final_view = templates.html_view.replace("__DATA__", json_data)
    final_view = final_view.replace("__OPTIONS_GOES_HERE__", options_html)
    return final_view

@app.get("/predict", response_class=HTMLResponse)
def get_chart():
    # 1. 앞에서 그린 표(HTML)와 그래프 이미지 코드를 한 번에 받아옵니다.
    html_table, img_base64 = database.get_files() 
    
    # 2. 이미지 태그(<img>)와 표를 상하로 쾅 찍어서 화면에 띄웁니다. (끝!)
    return f"""
    <html>
    <body style="padding: 20px; text-align: center; font-family: sans-serif; background-color: #f8f9fa;">
        <h2>📊 주요 4개 구 미세먼지 비교 그래프</h2>
        <div style="margin-bottom: 30px;">
            <img src="data:image/png;base64,{img_base64}" style="max-width:100%; height:auto;">
        </div>
        <h2>📋 상세 데이터 표</h2>
        <div style="display: inline-block; text-align: left;">{html_table}</div>
    </body>
    </html>
    """
    
@app.get("/predict/calc", response_class=HTMLResponse)
def cal_arima():
    data,dates= database.get_gangnam_data()
    
    if not data or len(data) < 7:
        return """
        <html>
            <body style="text-align: center; padding: 50px; font-family: sans-serif;">
                <h2 style="color: #d35400;">⏳ 실시간 미세먼지 데이터 수집 중...</h2>
                <p style="color: #666;">Render 서버가 처음 켜져서 미세먼지 원본 CSV 데이터를 DB에 채워 넣는 중입니다.</p>
                <p style="color: #999;"><b>1~2분 뒤에 이 페이지를 새로고침(F5)</b> 하시면 AI 예측 그래프가 나타납니다!</p>
            </body>
        </html>
        """    
    
    acf_values = acf(data, nlags=5)
    pacf_values = pacf(data, nlags=5)
    I_values = pd.Series(data).diff().dropna().round(2).tolist()
    
    df = pd.DataFrame({"Date": dates, "value":data})
        
    html_table = df.T.to_html(classes="table table-striped", index=False)
    plot_img = templates0.get_plots(acf_values,pacf_values,I_values)
    
    html_img = templates0.get_htmlplot(dates,data)
    # HTML 구조를 갖춰서 반환
    html_content = f"""
    <html>
        <head><title>ARIMA Prediction</title></head>
        <body>
        <table width= "100%">
        <tr>
        <div style="text-align: center; margin-bottom: 20px;">
                    <img src="data:image/png;base64,{plot_img}" style="width: 100%; border: 1px solid #ccc; border-radius: 5px;">
                </div>
        <td width ="33%"><h2>PACF</h2><p>{pacf_values}</p></td>
        <td width ="33%"><h2>I</h2><p>{I_values}</p></td>
        <td width ="33%"><h2>ACF</h2><p>{acf_values}</p></td>
        </tr>
        </table>
        <img src="data:image/png;base64,{html_img}" style="width: 100%; border: 1px solid #ccc; border-radius: 5px;">
        <h2>Gangnam Dust Prediction</h2>
        {html_table}

        </body>
    </html>
    """
    return HTMLResponse(content=html_content)

if __name__ == "__main__":
    import uvicorn

    # 배포 서버의 포트(Port)에 맞춰서 자동으로 켜지게 설정
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=False)

