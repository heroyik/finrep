import yfinance as yf
import pandas as pd
import pandas_ta as ta
import requests
import os
import mplfinance as mpf
import matplotlib.pyplot as plt
from datetime import datetime, timedelta, timezone
import json
from dotenv import load_dotenv

# 환경 변수 로드 (로컬 테스트용)
load_dotenv()

TICKERS = ["BITU", "ORCX", "PLTG", "CRWU", "CCUP", "OKLL"]
KAKAO_REST_API_KEY = os.getenv("KAKAO_REST_API_KEY")
KAKAO_CLIENT_SECRET = os.getenv("KAKAO_CLIENT_SECRET")
KAKAO_REFRESH_TOKEN = os.getenv("KAKAO_REFRESH_TOKEN")

# 종목별 기초자산 매핑 (뉴스 수집용)
UNDERLYING_MAP = {
    "BITU": "BTC-USD",
    "ORCX": "ORCL",
    "PLTG": "PLTR",
    "CRWU": "CRWV",
    "CCUP": "CRCL",
    "OKLL": "OKLO"
}

# 메이저 뉴스 매체 리스트
MAJOR_PUBLISHERS = [
    "Reuters", "Bloomberg", "CNBC", "Financial Times", "WSJ", "Wall Street Journal", 
    "MarketWatch", "Associated Press", "AP", "CNN", "Forbes", "Fortune", "Business Insider", 
    "The New York Times", "NYT", "The Economist", "Barrons", "Investor's Business Daily", "IBD",
    "Yahoo Finance"
]

def fetch_and_analyze(ticker_symbol):
    try:
        ticker = yf.Ticker(ticker_symbol)
        df = ticker.history(period="1y")
        
        if df.empty:
            return f"❌ {ticker_symbol}: 데이터를 가져올 수 없습니다."

        # 종목명 가져오기 (Fast Info 없을 경우 대비)
        long_name = ""
        try:
            # info 호출은 느릴 수 있으므로 타임아웃/예외처리 필요하나 간편하게 시도
            # fast_info는 name 제공 안함. info 사용.
            long_name = ticker.info.get('longName', ticker.info.get('shortName', ''))
        except:
            long_name = ""

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

        # 시간외 정보
        after_hours_price = None
        after_hours_change = None
        try:
            info = ticker.info
            after_hours_price = info.get('postMarketPrice')
            if after_hours_price:
                after_hours_change = ((after_hours_price - current_close) / current_close) * 100
        except:
            pass

        # 차트 생성
        chart_filename = f"{ticker_symbol}_chart.png"
        generate_chart(ticker_symbol, df, chart_filename)

        # 뉴스 수집
        news = fetch_news(ticker_symbol)

        # 전략 신호 분석
        # NaN 체크
        c_rsi = last_row['RSI'] if not pd.isna(last_row['RSI']) else 50
        c_ema20 = last_row['EMA20'] if not pd.isna(last_row['EMA20']) else 0
        c_ema60 = last_row['EMA60'] if not pd.isna(last_row['EMA60']) else 0
        c_ema120 = last_row['EMA120'] if not pd.isna(last_row['EMA120']) else 0
        
        # 1차 매수: EMA20 < EMA60 < EMA120 (역배열)
        is_buy_1 = (c_ema20 < c_ema60) and (c_ema60 < c_ema120) and (c_ema20 > 0)
        
        # 2차 매수: 1차 매수 충족 AND RSI < 30
        is_buy_2 = is_buy_1 and (c_rsi < 30)
        
        # 1차 매도: EMA20 > EMA60, EMA120 (정배열 가정 혹은 20이 가장 높음) AND RSI > 70
        # 사용자 요청: "EMA(20) > EMA(60), EMA(120)" -> 20이 60, 120보다 큼.
        # 엄격한 정배열(20>60>120)을 적용할지, 단순히 20이 짱인 경우를 볼지.
        # 매수와 대칭성을 위해 20 > 60 > 120 (정배열)을 기준으로 잡되,
        # 문맥상 과열권 매도이므로 20 > 60 and 20 > 120 조건이 합리적일 수 있음.
        # 여기서는 "정배열(Bullish Alignment)"인 20 > 60 > 120 으로 정의하겠습니다.
        is_sell_1 = (c_ema20 > c_ema60) and (c_ema60 > c_ema120) and (c_rsi > 70)

        result = {
            "Symbol": ticker_symbol,
            "LongName": long_name,
            "Price": round(current_close, 2),
            "Change": round(change_pct, 2),
            "AfterPrice": round(after_hours_price, 2) if after_hours_price else None,
            "AfterChange": round(after_hours_change, 2) if after_hours_change else None,
            "RSI": round(c_rsi, 2),
            "EMA20": round(c_ema20, 2),
            "EMA60": round(c_ema60, 2),
            "EMA120": round(c_ema120, 2),
            "Chart": chart_filename,
            "News": news,
            "Signals": {
                "Buy1": is_buy_1,
                "Buy2": is_buy_2,
                "Sell1": is_sell_1
            }
        }
        return result
    except Exception as e:
        return f"❌ {ticker_symbol}: 에러 발생 - {str(e)}"

def fetch_news(ticker_symbol):
    underlying = UNDERLYING_MAP.get(ticker_symbol, ticker_symbol)
    try:
        t = yf.Ticker(underlying)
        news_list = t.news
        filtered_news = []
        
        if not news_list:
            return []

        for n in news_list:
            # yfinance news 구조 대응 (데이터가 'content' 필드 내부에 있음)
            content = n.get('content', n) 
            title = content.get('title')
            
            # publisher 확인
            provider = content.get('provider', {})
            publisher = provider.get('name', content.get('publisher', 'Unknown'))
            
            # link 확인 (canonicalUrl or clickThroughUrl)
            link_obj = content.get('canonicalUrl', content.get('clickThroughUrl', {}))
            link = link_obj.get('url', content.get('link'))
            
            if not title or not link or title == "None": continue
            
            if any(major.lower() in publisher.lower() for major in MAJOR_PUBLISHERS):
                filtered_news.append({
                    "title": title,
                    "publisher": publisher,
                    "link": link
                })
            
            if len(filtered_news) >= 3:
                break
        
        # 필터링된 뉴스가 부족하면 상위 뉴스 그냥 노출 (백업)
        if len(filtered_news) < 3:
            for n in news_list:
                content = n.get('content', n)
                title = content.get('title')
                provider = content.get('provider', {})
                publisher = provider.get('name', content.get('publisher', 'Market News'))
                link_obj = content.get('canonicalUrl', content.get('clickThroughUrl', {}))
                link = link_obj.get('url', content.get('link'))
                
                if not title or not link or title == "None": continue
                
                if title not in [fn['title'] for fn in filtered_news]:
                    filtered_news.append({
                        "title": title,
                        "publisher": publisher,
                        "link": link
                    })
                if len(filtered_news) >= 3:
                    break
                    
        return filtered_news
    except Exception as e:
        print(f"Error fetching news for {underlying}: {e}")
        return []

def generate_chart(symbol, df, filename):
    # 최근 60영업일 데이터만 사용 (차트 가독성)
    plot_df = df.tail(60).copy()
    
    # 공백 데이터 제거
    plot_df = plot_df.dropna(subset=['Open', 'High', 'Low', 'Close'])
    
    # EMA 선 설정 (데이터가 존재하는 경우에만 추가)
    apds = []
    
    # EMA 20
    if 'EMA20' in plot_df.columns and not plot_df['EMA20'].isnull().all():
        apds.append(mpf.make_addplot(plot_df['EMA20'], color='#f59e0b', width=1.2, label='EMA 20'))
        
    # EMA 60
    if 'EMA60' in plot_df.columns and not plot_df['EMA60'].isnull().all():
        apds.append(mpf.make_addplot(plot_df['EMA60'], color='#8b5cf6', width=1.2, label='EMA 60'))
        
    # EMA 120 (상장 초기 종목 등 데이터 부족 시 제외)
    if 'EMA120' in plot_df.columns and not plot_df['EMA120'].isnull().all():
        apds.append(mpf.make_addplot(plot_df['EMA120'], color='#64748b', width=1.2, label='EMA 120'))
        
    # RSI
    if 'RSI' in plot_df.columns and not plot_df['RSI'].isnull().all():
        apds.append(mpf.make_addplot(plot_df['RSI'], panel=1, color='#313d4a', width=1.0, secondary_y=False))
    
    # 미니멀 스타일 설정
    mc = mpf.make_marketcolors(up='#10b981', down='#f43f5e', edge='inherit', wick='inherit', volume='inherit')
    style = mpf.make_mpf_style(
        marketcolors=mc, 
        gridstyle=':', 
        gridcolor='#f1f5f9',
        facecolor='white', 
        edgecolor='#cbd5e1',
        rc={'font.family': 'sans-serif', 'font.size': 6.5}
    )
    
    # 차트 폴더 생성
    if not os.path.exists("public/charts"):
        os.makedirs("public/charts")
    
    # 차트 저장
    full_path = os.path.join("public/charts", filename)
    
    # 여백을 넉넉하게 설정하여 차트 본문(박스)을 정중앙에 배치
    fig, axes = mpf.plot(
        plot_df,
        type='candle',
        addplot=apds,
        volume=False,
        figratio=(12, 8), # 가로세로 비율 조정
        style=style,
        returnfig=True,
        panel_ratios=(2, 1),
        tight_layout=False,
        ylabel='',
        ylabel_lower=''
    )
    
    # 사용자 피드백 반영: 왼쪽 여백을 오렌지 가이드라인에 맞춰 축소 (0.2 -> 0.12)
    # 우측 여백은 유지 (right=0.8)
    # 상하 여백은 기존 유지 (top=0.8, bottom=0.2)
    plt.subplots_adjust(left=0.12, right=0.8, top=0.8, bottom=0.2)
    
    # Legend 설정 (심플하게)
    axes[0].legend(loc='upper left', fontsize=6, frameon=False)
    
    # RSI 수평선
    axes[2].axhline(y=70, color='#f43f5e', linestyle='--', linewidth=0.6, alpha=0.3)
    axes[2].axhline(y=30, color='#10b981', linestyle='--', linewidth=0.6, alpha=0.3)
    
    # 축 설정 정리
    axes[0].set_ylabel('')
    axes[2].set_ylabel('')
    
    # 폰트 및 틱 설정 (숫자가 차트 박스 밖으로 여유 있게 나오도록 pad 조정)
    for ax in axes:
        ax.tick_params(axis='y', labelsize=6, pad=5)
        ax.tick_params(axis='x', labelsize=6, pad=5)
    
    plt.savefig(full_path, dpi=160)
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


def generate_html_report(results):
    # KST 시간 설정 (UTC+9)
    now_utc = datetime.now(timezone.utc)
    now_kst = now_utc + timedelta(hours=9)
    date_str = now_kst.strftime('%Y-%m-%d %H:%M:%S KST')
    
    html_template = f"""
    <!DOCTYPE html>
    <html lang="ko">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Daily Stock Briefing - {now_kst.strftime('%Y-%m-%d')}</title>
        <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap" rel="stylesheet">
        <style>
            :root {{
                --bg-gradient: linear-gradient(135deg, #0f172a 0%, #1e1b4b 100%);
                --card-bg: rgba(255, 255, 255, 0.05);
                --accent-blue: #38bdf8;
                --accent-green: #10b981;
                --accent-red: #f43f5e;
                --text-main: #f8fafc;
                --text-dim: #94a3b8;
                --buy-bg: rgba(16, 185, 129, 0.15);
                --buy-text: #34d399;
                --sell-bg: rgba(244, 63, 94, 0.15);
                --sell-text: #fb7185;
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
            
            /* Dashboard Section */
            .dashboard {{
                background: rgba(0, 0, 0, 0.3);
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 16px;
                padding: 24px;
                margin-bottom: 40px;
            }}
            .dash-grid {{
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
                gap: 20px;
                margin-bottom: 20px;
            }}
            .dash-item {{
                background: var(--card-bg);
                border-radius: 12px;
                padding: 16px;
                display: flex;
                flex-direction: column;
                align-items: center;
                text-align: center;
            }}
            .dash-title {{
                font-size: 0.9rem;
                font-weight: 600;
                color: var(--text-dim);
                margin-bottom: 12px;
                text-transform: uppercase;
                letter-spacing: 0.05em;
            }}
            .ticker-badges {{
                display: flex;
                flex-wrap: wrap;
                gap: 8px;
                justify-content: center;
            }}
            .badge {{
                padding: 6px 12px;
                border-radius: 20px;
                font-weight: 700;
                font-size: 0.9rem;
            }}
            .badge.buy {{ background: var(--buy-bg); color: var(--buy-text); border: 1px solid var(--buy-text); }}
            .badge.sell {{ background: var(--sell-bg); color: var(--sell-text); border: 1px solid var(--sell-text); }}
            .badge.empty {{ background: rgba(255,255,255,0.05); color: var(--text-dim); font-weight: 400; }}
            
            .strategy-legend {{
                font-size: 0.8rem;
                color: var(--text-dim);
                border-top: 1px solid rgba(255, 255, 255, 0.1);
                padding-top: 15px;
                line-height: 1.6;
            }}
            .strategy-legend strong {{ color: var(--text-main); margin-right: 4px; }}
            .strategy-row {{ margin-bottom: 4px; }}

            /* Stock Cards */
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
            .symbol-row {{
                display: flex;
                align-items: baseline;
                gap: 10px;
                flex-wrap: wrap;
            }}
            .symbol {{
                font-size: 2rem;
                font-weight: 800;
                line-height: 1;
            }}
            .symbol-desc {{
                font-size: 0.9rem;
                color: var(--text-dim);
                font-weight: 400;
                line-height: 1;
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
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 12px;
                overflow: hidden;
                background: white;
                cursor: zoom-in;
            }}
            .chart-box img {{
                width: 100%;
                display: block;
            }}
            
            /* News Section */
            .news-section {{
                margin-top: 20px;
                border-top: 1px solid rgba(255, 255, 255, 0.1);
                padding-top: 20px;
            }}
            .news-header {{
                font-size: 0.9rem;
                color: var(--text-dim);
                text-transform: uppercase;
                margin-bottom: 15px;
                letter-spacing: 0.05em;
                display: flex;
                align-items: center;
                gap: 8px;
            }}
            .news-list {{
                display: flex;
                flex-direction: column;
                gap: 16px;
            }}
            .news-item {{
                display: flex;
                flex-direction: column;
                gap: 4px;
            }}
            .news-link {{
                color: var(--text-main);
                text-decoration: none;
                font-size: 1.05rem;
                font-weight: 600;
                line-height: 1.4;
            }}
            .news-link:hover {{
                color: var(--accent-blue);
                text-decoration: underline;
            }}
            .news-source {{
                font-size: 0.8rem;
                color: var(--text-dim);
                font-weight: 400;
            }}

            /* Modal */
            .modal {{
                display: none;
                position: fixed;
                z-index: 1000;
                top: 0;
                left: 0;
                width: 100%;
                height: 100%;
                background-color: rgba(0,0,0,0.95);
                padding: 20px;
                box-sizing: border-box;
                justify-content: center;
                align-items: center;
            }}
            .modal-content {{
                max-width: 100%;
                max-height: 100%;
                border-radius: 8px;
                object-fit: contain;
            }}

            footer {{
                margin-top: 60px;
                text-align: center;
                color: var(--text-dim);
                font-size: 0.875rem;
            }}
            @media (max-width: 600px) {{
                .symbol-desc {{
                    display: block;
                    width: 100%;
                    margin-top: 4px;
                }}
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <header>
                <h1>Daily Stock Briefing</h1>
                <p class="date">Updated at: {date_str}</p>
            </header>
            
            <!-- Signal Dashboard -->
            <div class="dashboard">
                <div class="dash-grid">
    """
    
    # Dashboard Content Logic
    valid_results = [r for r in results if not isinstance(r, str)]
    buy1_tickers = [r['Symbol'] for r in valid_results if r['Signals']['Buy1']]
    buy2_tickers = [r['Symbol'] for r in valid_results if r['Signals']['Buy2']]
    sell1_tickers = [r['Symbol'] for r in valid_results if r['Signals']['Sell1']]

    # 1. 1st Buy List
    if buy1_tickers:
        html_template += """
                    <!-- 1차 매수 -->
                    <div class="dash-item">
                        <div class="dash-title">Bullish Setup (1st Buy)</div>
                        <div class="ticker-badges">
        """
        for t in buy1_tickers:
            html_template += f'<div class="badge buy">{t}</div>'
        html_template += """
                        </div>
                    </div>
        """

    # 2. 2nd Buy List
    if buy2_tickers:
        html_template += """
                    <!-- 2차 매수 -->
                    <div class="dash-item">
                        <div class="dash-title">Oversold & Bullish (2nd Buy)</div>
                        <div class="ticker-badges">
        """
        for t in buy2_tickers:
            html_template += f'<div class="badge buy">{t}</div>'
        html_template += """
                        </div>
                    </div>
        """
    
    # 3. Sell List
    if sell1_tickers:
        html_template += """
                    <!-- 1차 매도 -->
                    <div class="dash-item">
                        <div class="dash-title">Overbought & Peak (Sell)</div>
                        <div class="ticker-badges">
        """
        for t in sell1_tickers:
            html_template += f'<div class="badge sell">{t}</div>'
        html_template += """
                        </div>
                    </div>
        """

    html_template += """
                </div>
                <div class="strategy-legend">
                    <div class="strategy-row"><strong>1차 매수:</strong> EMA(20) < EMA(60) < EMA(120) (역배열/저점구간)</div>
                    <div class="strategy-row"><strong>2차 매수:</strong> 1차 매수 조건 충족 + RSI(14) < 30 (과매도 심화)</div>
                    <div class="strategy-row"><strong>1차 매도:</strong> EMA(20) > EMA(60) > EMA(120) + RSI(14) > 70 (정배열 과열)</div>
                </div>
            </div>

            <div class="grid">
    """
    
    for res in valid_results:
        c_class = "up" if res['Change'] >= 0 else "down"
        c_sign = "+" if res['Change'] >= 0 else ""
        a_class = "up" if (res['AfterChange'] or 0) >= 0 else "down"
        a_sign = "+" if (res['AfterChange'] or 0) >= 0 else ""
        
        # Symbol + Description
        desc_html = f'<span class="symbol-desc">({res["LongName"]})</span>' if res["LongName"] else ""
        
        html_template += f"""
                <div class="card">
                    <div class="card-header">
                        <div class="symbol-box">
                            <div class="symbol-row">
                                <span class="symbol">{res['Symbol']}</span>
                                {desc_html}
                            </div>
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
                    
                    <div class="chart-box" onclick="openModal('charts/{res['Chart']}')">
                        <img src="charts/{res['Chart']}" alt="{res['Symbol']} Chart">
                    </div>
                    
                    <div class="news-section">
                        <div class="news-header">
                            <span>📰</span> Related News & Market Insights
                        </div>
                        <div class="news-list">
        """
        
        for n in res['News']:
            html_template += f"""
                            <div class="news-item">
                                <a href="{n['link']}" target="_blank" class="news-link">{n['title']}</a>
                                <span class="news-source">Source: {n['publisher']}</span>
                            </div>
            """
            
        html_template += f"""
                        </div>
                    </div>
                </div>
        """
        
    html_template += """
            </div>
            <footer>
                <p>&copy; 2026 FinRep. Powered by Yahoo Finance.</p>
            </footer>
        </div>

        <div id="modal" class="modal" onclick="closeModal()">
            <img class="modal-content" id="modalImg">
        </div>

        <script>
            function openModal(src) {
                document.getElementById('modal').style.display = 'flex';
                document.getElementById('modalImg').src = src;
            }
            function closeModal() {
                document.getElementById('modal').style.display = 'none';
            }
        </script>
    </body>
    </html>
    """
    
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
    now_kst = datetime.now(timezone.utc) + timedelta(hours=9)
    k_date = now_kst.strftime('%Y-%m-%d')
    
    template_object = {
        "object_type": "text",
        "text": f"📊 오늘의 미국 증시 브리핑\n{k_date} 주요 ETF 분석 리포트가 준비되었습니다.",
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

