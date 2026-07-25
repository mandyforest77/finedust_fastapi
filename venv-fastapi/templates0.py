import base64
import io
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from statsmodels.tsa.statespace.sarimax import SARIMAX
import pandas as pd

def get_plots(acf_v, pacf_v,I_v):
    plt.rcParams["font.family"] = "Malgun Gothic"
    fig, (ax1, ax2, ax3) = plt.subplots(1, 3, figsize=(14, 3.5))

    # 왼쪽 ACF / 오른쪽 PACF 그래프 생성
    ax1.stem(range(len(pacf_v)), pacf_v)
    ax1.set_title("PACF 그래프")
    
    ax2.plot(I_v, marker="o", color="orange")
    ax2.axhline(y=0, color="red", linestyle="--")  # 기준선 0
    ax2.set_title("1차 차분 (d 결정용)")

    ax3.stem(range(len(acf_v)), acf_v)
    ax3.set_title("ACF 그래프")
    
    # 이미지 글자 코드(Base64) 변환
    buf = io.BytesIO()
    plt.savefig(buf, format="png", bbox_inches="tight")
    plt.close()
    return base64.b64encode(buf.getvalue()).decode("utf-8")

def get_htmlplot(dates,data):
    plt.rcParams["font.family"] = "Malgun Gothic"
    fig, ax = plt.subplots(figsize=(12, 14))
    # 🚀 [수정 완] 뒤에 .dt 를 빼고 바로 .strftime()을 쓰시면 됩니다!
    short_dates = pd.to_datetime(dates).strftime("%m/%d").str.lstrip("0").tolist()
    short_dates = [d.replace("/0", "/") for d in short_dates]  # 02/28 -> 2/28

    
    ax.plot(short_dates, data, marker="o", color="royalblue", linewidth=2)
    ax.set_title("강남구 미세먼지 ARIMA예상", fontsize=14, pad=15)
    ax.tick_params(axis="x", rotation=45)  # 날짜 글자 45도 돌리기
    ax.grid(True, linestyle="--", alpha=0.5)  # 배경에 연한 모눈종이 선 추가

    model = SARIMAX(data,order=(1, 0, 0), 
                    seasonal_order=(1,1,0,7),trend="c").fit()
    forecast= model.forecast(steps=5).tolist()
    future_dates = [f"3/{i}" for i in range(1, 6)]
    
    connected_dates = [short_dates[-1]] + future_dates
    connected_forecast = [data[-1]] + forecast
    ax.plot(connected_dates, connected_forecast, marker="x", color="orange", linestyle="--")
    
    real_3month_data = [28, 36, 42, 54, 49]
    # 자연스럽게 파란선 끝(2월 마지막날)에서부터 이어지도록 풀칠해 줍니다.
    connected_real = [data[-1]] + real_3month_data

    # 3. 진짜 정답 그래프 그리기 (초록색 실선으로 겹쳐 그리기)
    ax.plot(
        connected_dates,
        connected_real,
        marker="s",
        color="limegreen",
        linewidth=2.5,
        label="진짜 정답",
    )
    
    plt.draw()
    buf = io.BytesIO()
    plt.savefig(buf, format="png", bbox_inches="tight")
    plt.close()
    return base64.b64encode(buf.getvalue()).decode("utf-8")
    