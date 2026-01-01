import yfinance as yf
import pandas as pd
import pandas_ta as ta
import requests
import os
import mplfinance as mpf
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
from dotenv import load_dotenv

# 환경 변수 로드 (로컬 테스트용)
load_dotenv()

TICKERS = ["BITU", "ORCX", "PLTG", "CRWU", "CCUP", "OKLL"]
KAKAO_REST_API_KEY = os.getenv("KAKAO_REST_API_KEY")
KAKAO_CLIENT_SECRET = os.getenv("KAKAO_CLIENT_SECRET")
KAKAO_REFRESH_TOKEN = os.getenv("KAKAO_REFRESH_TOKEN")

def fetch_and_analyze(ticker_symbol):
    try:
        ticker = yf.Ticker(ticker_symbol)
        df = ticker.history(period="1y")
        
        if df.empty:
            return f"❌ {ticker_symbol}: 데이터를 가져올 수 없습니다."

        # 지표 계산
        df['RSI'] = ta.rsi(df['Close'], length=14)
        df['EMA20'] = ta.ema(df['Close'], length=20)
        df['EMA60'] = ta.ema(df['Close'], length=60)
        df['EMA120'] = ta.ema(df['Close'], length=120)

        # 종가 정보
        last_row = df.iloc[-1]
        prev_close = df.iloc[-2]['Close']
        current_close = last_row['Close']
        change_pct = ((current_close - prev_close) / prev_close) * 100

        # 시간외 정보 (yfinance의 fast_info 또는 info 사용)
        after_hours_price = None
        after_hours_change = None
        try:
            # info 대신 fast_info 또는 직접 긁어오기 (yfinance는 시간외 데이터가 불안정할 수 있음)
            # 여기서는 info['postMarketPrice'] 시도
            info = ticker.info
            after_hours_price = info.get('postMarketPrice')
            if after_hours_price:
                after_hours_change = ((after_hours_price - current_close) / current_close) * 100
        except:
            pass

        # 차트 생성
        chart_filename = f"{ticker_symbol}_chart.png"
        generate_chart(ticker_symbol, df, chart_filename)

        result = {
            "Symbol": ticker_symbol,
            "Price": round(current_close, 2),
            "Change": round(change_pct, 2),
            "AfterPrice": round(after_hours_price, 2) if after_hours_price else None,
            "AfterChange": round(after_hours_change, 2) if after_hours_change else None,
            "RSI": round(last_row['RSI'], 2) if not pd.isna(last_row['RSI']) else "N/A",
            "EMA20": round(last_row['EMA20'], 2) if not pd.isna(last_row['EMA20']) else "N/A",
            "EMA60": round(last_row['EMA60'], 2) if not pd.isna(last_row['EMA60']) else "N/A",
            "EMA120": round(last_row['EMA120'], 2) if not pd.isna(last_row['EMA120']) else "N/A",
            "Chart": chart_filename
        }
        return result
    except Exception as e:
        return f"❌ {ticker_symbol}: 에러 발생 - {str(e)}"

def generate_chart(symbol, df, filename):
    # 최근 60영업일 데이터만 사용 (차트 가독성)
    plot_df = df.tail(60).copy()
    
    # 공백 데이터 제거
    plot_df = plot_df.dropna(subset=['Open', 'High', 'Low', 'Close'])
    
    # EMA 선 설정
    apds = [
        mpf.make_addplot(plot_df['EMA20'], color='red', width=0.7),
        mpf.make_addplot(plot_df['EMA60'], color='cyan', width=0.7),
        mpf.make_addplot(plot_df['EMA120'], color='lime', width=0.7),
        mpf.make_addplot(plot_df['RSI'], panel=1, color='black', width=0.7, secondary_y=False)
    ]
    
    # 스타일 설정
    style = mpf.make_mpf_style(base_mpf_style='charles', gridstyle='', facecolor='white', edgecolor='black')
    
    # 차트 폴더 생성
    if not os.path.exists("public/charts"):
        os.makedirs("public/charts")
    
    # 차트 저장
    full_path = os.path.join("public/charts", filename)
    
    fig, axes = mpf.plot(
        plot_df,
        type='candle',
        addplot=apds,
        volume=False,
        figratio=(12, 8),
        style=style,
        returnfig=True,
        panel_ratios=(2, 1), # 메인 차트와 RSI 비율
        tight_layout=True
    )
    
    # 제목 및 축 설정 (한글 깨짐 방지를 위해 영어 사용)
    axes[0].set_title(f"{symbol} Daily Chart", fontsize=15, fontweight='bold')
    axes[2].set_ylabel('RSI(14)', fontsize=10)
    
    plt.savefig(full_path, dpi=100)
    plt.close()

def get_access_token():
    """Refresh Token을 이용해 새로운 Access Token 발급"""
    url = "https://kauth.kakao.com/oauth/token"
    data = {
        "grant_type": "refresh_token",
        "client_id": KAKAO_REST_API_KEY,
        "client_secret": KAKAO_CLIENT_SECRET,
        "refresh_token": KAKAO_REFRESH_TOKEN
    }
    response = requests.post(url, data=data)
    tokens = response.json()
    if "access_token" in tokens:
        return tokens["access_token"]
    else:
        raise Exception(f"Error refreshing token: {tokens}")

import json

def generate_html_report(results):
    now = datetime.now()
    date_str = now.strftime('%Y-%m-%d %H:%M:%S KST')
    
    html_template = f"""
    <!DOCTYPE html>
    <html lang="ko">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Daily Stock Briefing - {now.strftime('%Y-%m-%d')}</title>
        <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;800&display=swap" rel="stylesheet">
        <style>
            :root {{
                --bg-gradient: linear-gradient(135deg, #0f172a 0%, #1e1b4b 100%);
                --card-bg: rgba(255, 255, 255, 0.05);
                --accent-blue: #38bdf8;
                --accent-green: #10b981;
                --accent-red: #f43f5e;
                --text-main: #f8fafc;
                --text-dim: #94a3b8;
            }}
            body {{
                font-family: 'Inter', sans-serif;
                background: var(--bg-gradient);
                color: var(--text-main);
                margin: 0;
                padding: 40px 20px;
                min-height: 100vh;
                display: flex;
                flex-direction: column;
                align-items: center;
            }}
            .container {{
                max-width: 1000px;
                width: 100%;
            }}
            header {{
                text-align: center;
                margin-bottom: 40px;
            }}
            h1 {{
                font-size: 2.5rem;
                font-weight: 800;
                margin-bottom: 10px;
                background: linear-gradient(to right, #38bdf8, #818cf8);
                -webkit-background-clip: text;
                -webkit-text-fill-color: transparent;
            }}
            .date {{
                color: var(--text-dim);
                font-size: 1rem;
            }}
            .grid {{
                display: flex;
                flex-direction: column;
                gap: 30px;
            }}
            .card {{
                background: var(--card-bg);
                backdrop-filter: blur(10px);
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 20px;
                padding: 30px;
                width: 100%;
                box-sizing: border-box;
            }}
            .card-header {{
                display: flex;
                justify-content: space-between;
                align-items: flex-start;
                margin-bottom: 20px;
                flex-wrap: wrap;
                gap: 20px;
            }}
            .symbol-box {{
                display: flex;
                flex-direction: column;
            }}
            .symbol {{
                font-size: 2rem;
                font-weight: 800;
                margin-bottom: 4px;
            }}
            .price-section {{
                display: flex;
                gap: 40px;
                flex-wrap: wrap;
            }}
            .price-item {{
                display: flex;
                flex-direction: column;
            }}
            .price-label {{
                font-size: 0.75rem;
                color: var(--text-dim);
                text-transform: uppercase;
                margin-bottom: 4px;
            }}
            .price-value {{
                font-size: 1.75rem;
                font-weight: 700;
            }}
            .price-change {{
                font-size: 1rem;
                font-weight: 600;
            }}
            .up {{ color: var(--accent-green); }}
            .down {{ color: var(--accent-red); }}
            .chart-box {{
                margin: 20px 0;
                border-radius: 12px;
                overflow: hidden;
                border: 1px solid rgba(255, 255, 255, 0.1);
                background: white;
            }}
            .chart-box img {{
                width: 100%;
                height: auto;
                display: block;
            }}
            .indicators {{
                display: grid;
                grid-template-columns: repeat(4, 1fr);
                gap: 20px;
                border-top: 1px solid rgba(255, 255, 255, 0.1);
                padding-top: 20px;
            }}
            .indicator-item {{
                display: flex;
                flex-direction: column;
            }}
            .label {{
                font-size: 0.75rem;
                color: var(--text-dim);
                text-transform: uppercase;
                letter-spacing: 0.05em;
                margin-bottom: 4px;
            }}
            .value {{
                font-size: 1.1rem;
                font-weight: 600;
            }}
            footer {{
                margin-top: 60px;
                text-align: center;
                color: var(--text-dim);
                font-size: 0.875rem;
            }}
            @media (max-width: 600px) {{
                .indicators {{
                    grid-template-columns: 1fr 1fr;
                }}
                .price-section {{
                    gap: 20px;
                }}
            }}
            .value {{
                font-size: 1rem;
                font-weight: 600;
            }}
            footer {{
                margin-top: 60px;
                text-align: center;
                color: var(--text-dim);
                font-size: 0.875rem;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <header>
                <h1>Daily Stock Briefing</h1>
                <p class="date">Updated at: {date_str}</p>
            </header>
            <div class="grid">
    """
    
    for res in results:
        if isinstance(res, str): continue
        
        c_class = "up" if res['Change'] >= 0 else "down"
        c_sign = "+" if res['Change'] >= 0 else ""
        
        a_class = "up" if (res['AfterChange'] or 0) >= 0 else "down"
        a_sign = "+" if (res['AfterChange'] or 0) >= 0 else ""
        
        html_template += f"""
                <div class="card">
                    <div class="card-header">
                        <div class="symbol-box">
                            <div class="symbol">{res['Symbol']}</div>
                        </div>
                        <div class="price-section">
                            <div class="price-item">
                                <span class="price-label">At Close</span>
                                <span class="price-value">{res['Price']}</span>
                                <span class="price-change {c_class}">{c_sign}{res['Change']}%</span>
                            </div>
        """
        
        if res['AfterPrice']:
            html_template += f"""
                            <div class="price-item">
                                <span class="price-label">After Hours</span>
                                <span class="price-value">{res['AfterPrice']}</span>
                                <span class="price-change {a_class}">{a_sign}{res['AfterChange']}%</span>
                            </div>
            """
            
        html_template += f"""
                        </div>
                    </div>
                    
                    <div class="chart-box">
                        <img src="charts/{res['Chart']}" alt="{res['Symbol']} Chart">
                    </div>
                    
                    <div class="indicators">
                        <div class="indicator-item">
                            <span class="label">RSI(14)</span>
                            <span class="value">{res['RSI']}</span>
                        </div>
                        <div class="indicator-item">
                            <span class="label">EMA(20)</span>
                            <span class="value">{res['EMA20']}</span>
                        </div>
                        <div class="indicator-item">
                            <span class="label">EMA(60)</span>
                            <span class="value">{res['EMA60']}</span>
                        </div>
                        <div class="indicator-item">
                            <span class="label">EMA(120)</span>
                            <span class="value">{res['EMA120']}</span>
                        </div>
                    </div>
                </div>
        """
        
    html_template += """
            </div>
            <footer>
                <p>Data provided by Yahoo Finance & Automated by Antigravity</p>
            </footer>
        </div>
    </body>
    </html>
    """
    # 'public' 폴더 생성 및 리포트 저장
    if not os.path.exists("public"):
        os.makedirs("public")
    
    report_path = os.path.join("public", "index.html")
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(html_template)
    print(f"HTML report generated: {report_path}")

def send_kakao_link(briefing_url):
    if not KAKAO_REST_API_KEY or not KAKAO_REFRESH_TOKEN:
        print(f"Kakao configuration missing. Briefing URL: {briefing_url}")
        return

    access_token = get_access_token()
    
    url = "https://kapi.kakao.com/v2/api/talk/memo/default/send"
    headers = {
        "Authorization": f"Bearer {access_token}"
    }

    # 이미지 URL 및 템플릿 최적화
    # 가장 단순하고 확실한 'text' 템플릿으로 변경하여 버튼 활성화 테스트
    template_object = {
        "object_type": "text",
        "text": f"📊 오늘의 미국 증시 브리핑\n{datetime.now().strftime('%Y-%m-%d')} 주요 ETF 분석 리포트가 준비되었습니다.",
        "link": {
            "web_url": briefing_url,
            "mobile_web_url": briefing_url
        },
        "button_title": "리포트 보기"
    }
    
    payload = {
        "template_object": json.dumps(template_object)
    }
    
    response = requests.post(url, headers=headers, data=payload)
    if response.status_code == 200:
        print("KakaoTalk message sent successfully!")
    else:
        print(f"Failed to send KakaoTalk message: {response.status_code} - {response.text}")
        raise Exception(f"Kakao API Error: {response.text}")

if __name__ == "__main__":
    report_data = []
    for ticker in TICKERS:
        print(f"Analyzing {ticker}...")
        report_data.append(fetch_and_analyze(ticker))
    
    # HTML 리포트 생성
    generate_html_report(report_data)
    
    # GitHub Pages URL (사용자 계정과 레포 이름에 맞게 수정 필요)
    GITHUB_USER = "heroyik"
    REPO_NAME = "finrep"
    briefing_url = f"https://{GITHUB_USER}.github.io/{REPO_NAME}/"
    
    # 카카오톡 링크 전송
    send_kakao_link(briefing_url)

