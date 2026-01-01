import yfinance as yf
import pandas as pd
import pandas_ta as ta
import requests
import os
from datetime import datetime, timedelta
from dotenv import load_dotenv

# 환경 변수 로드 (로컬 테스트용)
load_dotenv()

TICKERS = ["BITU", "ORCX", "PLTG", "CRWU", "CCUP", "OKLL"]
KAKAO_REST_API_KEY = os.getenv("KAKAO_REST_API_KEY")
KAKAO_CLIENT_SECRET = os.getenv("KAKAO_CLIENT_SECRET")
KAKAO_REFRESH_TOKEN = os.getenv("KAKAO_REFRESH_TOKEN")

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
                max-width: 800px;
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
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
                gap: 20px;
            }}
            .card {{
                background: var(--card-bg);
                backdrop-filter: blur(10px);
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 20px;
                padding: 24px;
                transition: transform 0.3s ease, border-color 0.3s ease;
            }}
            .card:hover {{
                transform: translateY(-5px);
                border-color: var(--accent-blue);
            }}
            .symbol {{
                font-size: 1.5rem;
                font-weight: 800;
                margin-bottom: 8px;
                display: flex;
                justify-content: space-between;
                align-items: center;
            }}
            .price {{
                font-size: 2rem;
                font-weight: 600;
                margin-bottom: 4px;
            }}
            .change {{
                font-size: 1.1rem;
                font-weight: 600;
                margin-bottom: 20px;
            }}
            .up {{ color: var(--accent-green); }}
            .down {{ color: var(--accent-red); }}
            .indicators {{
                display: grid;
                grid-template-columns: 1fr 1fr;
                gap: 12px;
                border-top: 1px solid rgba(255, 255, 255, 0.1);
                padding-top: 16px;
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
        
        change_class = "up" if res['Change'] >= 0 else "down"
        change_sign = "+" if res['Change'] >= 0 else ""
        
        html_template += f"""
                <div class="card">
                    <div class="symbol">
                        {res['Symbol']}
                        <span class="{change_class}">{ "📈" if res['Change'] >= 0 else "📉" }</span>
                    </div>
                    <div class="price">${res['Price']}</div>
                    <div class="change {change_class}">{change_sign}{res['Change']}%</div>
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
    
    with open("index.html", "w", encoding="utf-8") as f:
        f.write(html_template)
    print("HTML report generated: index.html")

def send_kakao_link(briefing_url):
    if not KAKAO_REST_API_KEY or not KAKAO_REFRESH_TOKEN:
        print(f"Kakao configuration missing. Briefing URL: {briefing_url}")
        return

    access_token = get_access_token()
    
    url = "https://kapi.kakao.com/v2/api/talk/memo/default/send"
    headers = {
        "Authorization": f"Bearer {access_token}"
    }

    template_object = {
        "object_type": "feed",
        "content": {
            "title": "📊 오늘의 미국 증시 브리핑",
            "description": f"{datetime.now().strftime('%Y-%m-%d')} 주요 ETF 분석 리포트가 완성되었습니다.",
            "image_url": "https://images.unsplash.com/photo-1611974717483-939e68d06746?q=80&w=200&h=200&auto=format&fit=crop",
            "link": {
                "web_url": briefing_url,
                "mobile_web_url": briefing_url
            }
        },
        "buttons": [
            {
                "title": "리포트 보기",
                "link": {
                    "web_url": briefing_url,
                    "mobile_web_url": briefing_url
                }
            }
        ]
    }
    
    payload = {
        "template_object": json.dumps(template_object)
    }
    
    response = requests.post(url, headers=headers, data=payload)
    if response.status_code == 200:
        print("KakaoTalk link sent successfully!")
    else:
        print(f"Failed to send KakaoTalk link: {response.status_code} - {response.text}")
        raise Exception("Kakao API Error")

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

