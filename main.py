import yfinance as yf
import pandas as pd
import pandas_ta as ta
import requests
import os
import mplfinance as mpf
import matplotlib.pyplot as plt
from datetime import datetime, timedelta, timezone
try:
    from zoneinfo import ZoneInfo
except ImportError:
    # Compatibility for Python versions below 3.9 (not an issue since we use 3.13)
    from datetime import timezone as ZoneInfo
import json
import argparse
from dotenv import load_dotenv

# Load environment variables (for local testing)
load_dotenv()

TICKERS = ["BITU", "ORCX", "PLTG", "CRWU", "CCUP", "OKLL", "USD", "GGLL"]
KAKAO_REST_API_KEY = os.getenv("KAKAO_REST_API_KEY")
KAKAO_CLIENT_SECRET = os.getenv("KAKAO_CLIENT_SECRET")
KAKAO_REFRESH_TOKEN = os.getenv("KAKAO_REFRESH_TOKEN")

# Underlying asset mapping for each ticker (for news collection)
UNDERLYING_MAP = {
    "BITU": "BTC-USD",
    "ORCX": "ORCL",
    "PLTG": "PLTR",
    "CRWU": "CRWV",
    "CCUP": "CRCL",
    "OKLL": "OKLO",
    "USD": ["NVDA", "AMD", "AVGO", "MU"],
    "GGLL": "GOOGL"
}

# 추천 무료 뉴스 매체 (사용자 요청: AP, CNBC, Reuters, Yahoo, Investing, Stock Analysis)
PREFERRED_PUBLISHERS = [
    "Associated Press", "AP", "CNBC", "Reuters", "Yahoo Finance", 
    "Investing.com", "Stock Analysis"
]

# 기타 메이저 뉴스 매체 (페이월 제외)
MAJOR_PUBLISHERS = [
    "Bloomberg", "CNN", "Forbes", "Fortune", "Business Insider", 
    "The New York Times", "NYT", "The Economist", "Financial Times"
]

# 유료 결제 유도/페이월 매체 (반드시 제외)
EXCLUDED_PUBLISHERS = [
    "The Motley Fool", "Motley Fool", "Barrons", "Barron's", 
    "Wall Street Journal", "WSJ", "MarketWatch", "Investor's Business Daily", "IBD", "Zacks"
]

def fetch_and_analyze(ticker_symbol):
    try:
        ticker = yf.Ticker(ticker_symbol)
        df = ticker.history(period="1y")
        
        if df.empty:
            return f"❌ {ticker_symbol}: Unable to fetch data."

        # Get long name (fallback if Fast Info is missing)
        long_name = ""
        try:
            # info call might be slow, so timeout/exception handling needed but simplified here.
            # fast_info doesn't provide name. Using info.
            long_name = ticker.info.get('longName', ticker.info.get('shortName', ''))
        except:
            long_name = ""

        # Calculate indicators
        df['RSI'] = ta.rsi(df['Close'], length=14)
        df['EMA20'] = ta.ema(df['Close'], length=20)
        df['EMA60'] = ta.ema(df['Close'], length=60)
        df['EMA120'] = ta.ema(df['Close'], length=120)

        # Close price information
        last_row = df.iloc[-1]
        prev_close = df.iloc[-2]['Close']
        current_close = last_row['Close']
        change_pct = ((current_close - prev_close) / prev_close) * 100

        # After-hours information
        after_hours_price = None
        after_hours_change = None
        try:
            info = ticker.info
            after_hours_price = info.get('postMarketPrice')
            if after_hours_price:
                after_hours_change = ((after_hours_price - current_close) / current_close) * 100
        except:
            pass

        # Generate chart
        chart_filename = f"{ticker_symbol}_chart.png"
        generate_chart(ticker_symbol, df, chart_filename)

        # Fetch news
        news, news_asset = fetch_news(ticker_symbol)

        # Analyze strategy signals
        # NaN check
        c_rsi = last_row['RSI'] if not pd.isna(last_row['RSI']) else 50
        c_ema20 = last_row['EMA20'] if not pd.isna(last_row['EMA20']) else 0
        c_ema60 = last_row['EMA60'] if not pd.isna(last_row['EMA60']) else 0
        c_ema120 = last_row['EMA120'] if not pd.isna(last_row['EMA120']) else 0
        
        # 1st Buy: Bearish Alignment (20 < 60 < 120*) AND Close < EMA20
        # *EMA 120 is included in alignment check only if available (for new listings)
        alignment_buy = (c_ema20 < c_ema60)
        if c_ema120 > 0:
            alignment_buy = alignment_buy and (c_ema60 < c_ema120)
            
        is_buy_1 = alignment_buy and (c_ema20 > 0) and (current_close < c_ema20)
        
        # 2nd Buy: 1st Buy Condition Met AND RSI < 30
        is_buy_2 = is_buy_1 and (c_rsi < 30)
        
        # 1st Sell: Bullish Alignment (20 > 60 > 120*) AND Close > EMA20 AND RSI > 70
        # *EMA 120 is included in alignment check only if available (for new listings)
        alignment_sell = (c_ema20 > c_ema60)
        if c_ema120 > 0:
            alignment_sell = alignment_sell and (c_ema60 > c_ema120)

        is_sell_1 = alignment_sell and (current_close > c_ema20) and (c_rsi > 70)

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
            "NewsAsset": news_asset,
            "Signals": {
                "Buy1": is_buy_1,
                "Buy2": is_buy_2,
                "Sell1": is_sell_1
            }
        }
        return result
    except Exception as e:
        return f"❌ {ticker_symbol}: Error occurred - {str(e)}"

def fetch_news(ticker_symbol):
    underlying_data = UNDERLYING_MAP.get(ticker_symbol, ticker_symbol)
    
    # Normalize to list
    if isinstance(underlying_data, list):
        search_tickers = underlying_data
        display_name = f"Semiconductors ({', '.join(search_tickers)})" # or just generic
    else:
        search_tickers = [underlying_data]
        display_name = underlying_data

    try:
        all_news = []
        for sym in search_tickers:
            t = yf.Ticker(sym)
            news = t.news
            if news:
                all_news.extend(news)
        
        if not all_news:
            return [], display_name

        # Sort by publish time (descending)
        # yfinance news items usually have 'providerPublishTime'
        # Handle cases where it might be missing or nested
        def get_pub_time(n):
            content = n.get('content', n)
            return content.get('providerPublishTime', 0)
            
        all_news.sort(key=get_pub_time, reverse=True)
        
        news_list = all_news
        filtered_news = []

        seen_titles = set()
        seen_links = set()

        for n in news_list:
            content = n.get('content', n) 
            title = content.get('title')
            provider = content.get('provider', {})
            publisher = provider.get('displayName', provider.get('name', content.get('publisher', 'Unknown')))
            link_obj = content.get('canonicalUrl', content.get('clickThroughUrl', {}))
            link = link_obj.get('url', content.get('link'))
            
            if not title or not link or title == "None": continue
            
            # Deduplication Check
            if title in seen_titles or link in seen_links:
                continue

            # 제외 매체 체크
            if any(ex.lower() in publisher.lower() for ex in EXCLUDED_PUBLISHERS):
                continue

            # 선호 매체 및 메이저 매체 체크
            if any(pref.lower() in publisher.lower() for pref in PREFERRED_PUBLISHERS) or \
               any(major.lower() in publisher.lower() for major in MAJOR_PUBLISHERS):
                filtered_news.append({
                    "title": title,
                    "publisher": publisher,
                    "link": link
                })
                seen_titles.add(title)
                seen_links.add(link)
            
            if len(filtered_news) >= 3: break
        
        # Fallback: If no major news found, try to include any news (excluding blocked)
        if len(filtered_news) < 2:
            for n in news_list:
                content = n.get('content', n)
                title = content.get('title')
                provider = content.get('provider', {})
                publisher = provider.get('displayName', provider.get('name', content.get('publisher', 'Unknown')))
                link_obj = content.get('canonicalUrl', content.get('clickThroughUrl', {}))
                link = link_obj.get('url', content.get('link'))
                if not title or not link or title == "None": continue
                
                # 제외 매체 체크 (백업 루프에서도 제외)
                if any(ex.lower() in publisher.lower() for ex in EXCLUDED_PUBLISHERS):
                    continue
                
                # Check duplication again (explicitly against seen sets)
                if title in seen_titles or link in seen_links:
                    continue

                filtered_news.append({
                    "title": title,
                    "publisher": publisher,
                    "link": link
                })
                seen_titles.add(title)
                seen_links.add(link)
                if len(filtered_news) >= 3:
                    break
                    
        return filtered_news, display_name
    except Exception as e:
        print(f"Error fetching news for {ticker_symbol}: {e}")
        return [], display_name

def fetch_market_indices():
    """
    Fetch data for Major 4 Indices: S&P 500, Dow, Nasdaq, Russell 2000
    Returns a list of dicts with Name, Price, Change, ChangePercent
    """
    indices = [
        {"name": "S&P 500", "symbol": "^GSPC"},
        {"name": "Dow Jones", "symbol": "^DJI"},
        {"name": "Nasdaq", "symbol": "^IXIC"},
        {"name": "Russell 2000", "symbol": "^RUT"}
    ]
    
    results = []
    print("Fetching major indices data...")
    
    for idx in indices:
        try:
            ticker = yf.Ticker(idx["symbol"])
            price = None
            change_pct = None
            
            # Try fast_info first
            if hasattr(ticker, 'fast_info'):
                try:
                    price = ticker.fast_info['last_price']
                    prev_close = ticker.fast_info['previous_close']
                    change_pct = ((price - prev_close) / prev_close) * 100
                except:
                    pass
            
            # Fallback to history
            if price is None:
                hist = ticker.history(period="2d")
                if not hist.empty:
                    current = hist.iloc[-1]['Close']
                    if len(hist) > 1:
                        prev = hist.iloc[-2]['Close']
                        price = current
                        change_pct = ((current - prev) / prev) * 100
                    else:
                        price = current
                        change_pct = 0.0
            
            if price is not None:
                results.append({
                    "name": idx["name"],
                    "symbol": idx["symbol"],
                    "price": price,
                    "change_pct": change_pct
                })
            else:
                results.append({
                    "name": idx["name"],
                    "symbol": idx["symbol"],
                    "price": 0.0,
                    "change_pct": 0.0,
                    "error": True
                })
                
        except Exception as e:
            print(f"Error fetching index {idx['name']}: {e}")
            results.append({
                "name": idx["name"],
                "symbol": idx["symbol"],
                "price": 0.0,
                "change_pct": 0.0,
                "error": True
            })
            
    return results

def fetch_market_highlights():
    """
    Check 52-week highs for major indices.
    Returns list of highlight strings.
    """
    indices = [
        {"name": "S&P 500", "symbol": "^GSPC"},
        {"name": "Dow Jones", "symbol": "^DJI"},
        {"name": "Nasdaq", "symbol": "^IXIC"},
        {"name": "Russell 2000", "symbol": "^RUT"}
    ]
    
    highlights = []
    print("Checking market highlights...")
    
    for idx in indices:
        try:
            t = yf.Ticker(idx["symbol"])
            # Use info for 52-week high data
            info = t.info
            price = info.get('regularMarketPrice') or info.get('currentPrice')
            year_high = info.get('fiftyTwoWeekHigh')
            
            if price and year_high:
                # threshold: within 1% of 52-week high
                if price >= year_high * 0.99:
                    highlights.append(f"🚀 <strong>{idx['name']}</strong> is trading near its 52-week high, signaling strong momentum.")
        except Exception as e:
            print(f"Error checking highlight for {idx['name']}: {e}")
            
    return highlights

def fetch_market_news():
    """
    Fetch and curate top market news from major indices.
    Returns list of dicts {title, link, source}.
    """
    # Check all 4 indices for broad coverage
    indices = ["^GSPC", "^DJI", "^IXIC", "^RUT"] 
    all_news = []
    
    print("Fetching market driver news...")
    for sym in indices:
        try:
            t = yf.Ticker(sym)
            news = t.news
            if news:
                all_news.extend(news)
        except Exception as e:
            print(f"Error fetching news for {sym}: {e}")
            
    # Deduplicate by link and title
    seen_links = set()
    seen_titles = set()
    unique_news = []
    
    # Sort by publish time descending
    def get_pub_time(n):
        content = n.get('content', n)
        return content.get('providerPublishTime', 0)
    
    all_news.sort(key=get_pub_time, reverse=True)
    
    keywords = ["market", "stock", "dow", "s&p", "nasdaq", "rally", "plunge", "inflation", "fed", "rate", "earnings"]
    
    for n in all_news:
        content = n.get('content', n)
        title = content.get('title', '')
        # Handle provider extraction safely
        provider = content.get('provider', {})
        publisher = provider.get('displayName', provider.get('name', content.get('publisher', 'Unknown')))
        
        link_obj = content.get('canonicalUrl', content.get('clickThroughUrl', {}))
        link = link_obj.get('url', content.get('link'))
        
        if not title or not link: continue
        
        # Deduplication
        if link in seen_links or title in seen_titles:
            continue
            
        # Filter for relevant content (optional, but good for "drivers")
        # For now, we take top news but prioritize those with keywords if we implement scoring.
        # Simple approach: take top 4 distinct items.
        
        unique_news.append({
            "title": title,
            "link": link,
            "source": publisher
        })
        seen_links.add(link)
        seen_titles.add(title)
        
        if len(unique_news) >= 4:
            break
            
    return unique_news

def generate_chart(symbol, df, filename):
    # Use only recent 60 trading days (Chart Readability)
    plot_df = df.tail(60).copy()
    
    # Remove empty data
    plot_df = plot_df.dropna(subset=['Open', 'High', 'Low', 'Close'])
    
    # EMA line settings (Add only if data exists)
    apds = []
    
    # EMA 20
    if 'EMA20' in plot_df.columns and not plot_df['EMA20'].isnull().all():
        apds.append(mpf.make_addplot(plot_df['EMA20'], color='#f59e0b', width=1.2, label='EMA 20'))
        
    # EMA 60
    if 'EMA60' in plot_df.columns and not plot_df['EMA60'].isnull().all():
        apds.append(mpf.make_addplot(plot_df['EMA60'], color='#8b5cf6', width=1.2, label='EMA 60'))
        
    # EMA 120 (Exclude if insufficient data, e.g., newly listed stocks)
    if 'EMA120' in plot_df.columns and not plot_df['EMA120'].isnull().all():
        apds.append(mpf.make_addplot(plot_df['EMA120'], color='#64748b', width=1.2, label='EMA 120'))
        
    # RSI
    if 'RSI' in plot_df.columns and not plot_df['RSI'].isnull().all():
        apds.append(mpf.make_addplot(plot_df['RSI'], panel=1, color='#313d4a', width=1.0, secondary_y=False))
    
    # Minimal style settings
    mc = mpf.make_marketcolors(up='#10b981', down='#f43f5e', edge='inherit', wick='inherit', volume='inherit')
    style = mpf.make_mpf_style(
        marketcolors=mc, 
        gridstyle=':', 
        gridcolor='#f1f5f9',
        facecolor='white', 
        edgecolor='#cbd5e1',
        rc={'font.family': 'sans-serif', 'font.size': 6.5}
    )
    
    # Create chart folder
    if not os.path.exists("public/charts"):
        os.makedirs("public/charts")
    
    # Save chart
    full_path = os.path.join("public/charts", filename)
    print(f"Generating chart: {full_path}")
    
    # Set sufficient margins to center the chart body (box)
    fig, axes = mpf.plot(
        plot_df,
        type='candle',
        addplot=apds,
        volume=False,
        figratio=(12, 8), # Adjusted aspect ratio
        style=style,
        returnfig=True,
        panel_ratios=(2, 1),
        tight_layout=False,
        ylabel='',
        ylabel_lower=''
    )
    
    # Reflect user feedback: Reduce left margin per orange guideline (0.2 -> 0.12)
    # Maintain right margin (right=0.8)
    # Maintain top/bottom margins (top=0.8, bottom=0.2)
    plt.subplots_adjust(left=0.12, right=0.8, top=0.8, bottom=0.2)
    
    # Legend settings (Simple)
    axes[0].legend(loc='upper left', fontsize=6, frameon=False)
    
    # RSI Horizontal lines
    axes[2].axhline(y=70, color='#f43f5e', linestyle='--', linewidth=0.6, alpha=0.3)
    axes[2].axhline(y=30, color='#10b981', linestyle='--', linewidth=0.6, alpha=0.3)
    
    # Axis alignment settings
    axes[0].set_ylabel('')
    axes[2].set_ylabel('')
    
    # Font and tick settings (Adjust pad so numbers appear outside the chart box with sufficient space)
    for ax in axes:
        ax.tick_params(axis='y', labelsize=6, pad=5)
        ax.tick_params(axis='x', labelsize=6, pad=5)
    
    plt.savefig(full_path, dpi=160)
    plt.close()
    if os.path.exists(full_path):
        print(f"Successfully saved chart to {full_path}")
    else:
        print(f"Failed to save chart to {full_path}")

def get_access_token():
    """Refresh Token to issue new Access Token"""
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






def generate_html_report(results, filename="index.html", market_date=""):
    # Set KST time (UTC+9)
    now_utc = datetime.now(timezone.utc)
    now_kst = now_utc + timedelta(hours=9)
    date_str = now_kst.strftime('%Y-%m-%d %H:%M:%S KST')
    
    # Market date line (English)
    market_date_line = f"Reference Market Date: {market_date}" if market_date else ""
    
    # ---------------------------------------------------------
    # Generate Summaries (Market Overview & Ticker Insights)
    # ---------------------------------------------------------
    valid_results = [r for r in results if isinstance(r, dict)]
    market_overview = "Markets are currently processing AI sector consolidation, inflation expectations, and recent geopolitical developments affecting global trade sentiments."
    
    # Try to find a better overview from broad news (BTC-USD or index proxies)
    for res in valid_results:
        # Check if News is a list and has items
        if res.get('Symbol') in ['BITU', 'USD'] and isinstance(res.get('News'), list) and len(res['News']) > 0:
            # Use a slightly more specific headline if available
            market_overview = f"Market pulse: {res['News'][0]['title']}"
            break
            
    ticker_summaries = []
    for res in valid_results:
        insight = "Moving in line with broader market sentiment and sector momentum."
        news_items = res.get('News')
        
        if isinstance(news_items, list) and len(news_items) > 0:
            insight = news_items[0]['title']
        elif res.get('Change', 0) > 3:
            insight = "Strong upward momentum observed without specific immediate headlines."
        elif res.get('Change', 0) < -3:
            insight = "Undergoing price correction amid broader sector sell-off."
            
        ticker_summaries.append({
            "symbol": res.get('Symbol', 'Unknown'),
            "insight": insight
        })
    
    ticker_summary_html = ""
    for item in ticker_summaries:
        ticker_summary_html += f"""
                    <div class="summary-item">
                        <span class="summary-symbol">{item['symbol']}</span>
                        <span class="summary-text">{item['insight']}</span>
                    </div>
        """
    # ---------------------------------------------------------
    
    html_template = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Daily US Stock Briefing - {now_kst.strftime('%Y-%m-%d')}</title>
        <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=Orbitron:wght@700;900&display=swap" rel="stylesheet">
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
                margin-bottom: 25px;
                padding: 20px;
                border: 2px solid #0ff;
                border-radius: 12px;
                box-shadow: 0 0 20px rgba(0, 255, 255, 0.1);
                background: rgba(10, 10, 10, 0.8);
            }}
            h1 {{
                font-family: 'Orbitron', sans-serif;
                font-weight: 900;
                font-size: 2.2rem;
                text-transform: uppercase;
                background: linear-gradient(90deg, #ff00de, #00ffea);
                -webkit-background-clip: text;
                -webkit-text-fill-color: transparent;
                text-shadow: 0 0 15px rgba(255, 0, 222, 0.4);
                letter-spacing: 1px;
                margin: 0 0 10px 0;
                line-height: 1.1;
            }}
            .header-sub {{
                font-family: 'Orbitron', sans-serif;
                color: #00ffea;
                letter-spacing: 2px;
                font-size: 0.9rem;
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
            .news-empty {{
                font-size: 0.9rem;
                color: var(--text-dim);
                font-style: italic;
            }}

            /* Market Summary */
            .summary-box {{
                background: rgba(255, 255, 255, 0.05);
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 12px;
                padding: 1.2rem;
                margin-top: 15px;
                margin-bottom: 25px;
            }}
            .summary-header {{
                font-size: 0.85rem;
                text-transform: uppercase;
                letter-spacing: 0.05em;
                color: var(--text-dim);
                margin-bottom: 0.5rem;
                display: flex;
                align-items: center;
                gap: 6px;
                font-weight: 600;
            }}
            .summary-item {{
                margin-bottom: 0.8rem;
                font-size: 0.95rem;
                line-height: 1.4;
                display: flex;
                align-items: flex-start;
            }}
            .summary-symbol {{
                display: inline-block;
                min-width: 60px;
                font-weight: 700;
                color: var(--accent);
                margin-right: 10px;
            }}
            .summary-text {{
                color: var(--text-base);
            }}
            @media (max-width: 600px) {{
                .summary-item {{
                    font-size: 0.9rem;
                }}
                .summary-symbol {{
                    min-width: 50px;
                }}
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

            /* Indices Grid */
            .indices-grid {{
                display: grid;
                grid-template-columns: repeat(2, 1fr);
                gap: 12px;
                margin-bottom: 24px;
            }}
            .index-card {{
                background: rgba(255, 255, 255, 0.05);
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 12px;
                padding: 16px;
                display: flex;
                flex-direction: column;
            }}
            .index-name {{
                font-size: 0.9rem;
                color: #38bdf8;
                margin-bottom: 8px;
                font-weight: 600;
            }}
            .index-price {{
                font-size: 1.1rem;
                font-weight: 700;
                color: var(--text-main);
                margin-bottom: 4px;
            }}
            .index-change {{
                font-size: 0.9rem;
                font-weight: 600;
            }}
            
            /* Market Commentary */
            .commentary-section {{
                margin-top: 20px;
                border-top: 1px solid rgba(255, 255, 255, 0.1);
                padding-top: 15px;
            }}
            .highlight-item {{
                margin-bottom: 8px;
                font-size: 0.95rem;
                color: var(--accent-green);
            }}
            .driver-item {{
                margin-bottom: 12px;
                display: flex;
                flex-direction: column;
            }}
            .driver-link {{
                color: var(--text-main);
                text-decoration: none;
                font-size: 0.95rem;
                font-weight: 500;
                line-height: 1.4;
            }}
            .driver-link:hover {{
                color: var(--accent-blue);
                text-decoration: underline;
            }}
            .driver-source {{
                font-size: 0.8rem;
                color: var(--text-dim);
                margin-top: 2px;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <header>
                <h1>Daily US Stock Briefing</h1>
                <div class="header-sub">{date_str}</div>
                <div class="header-sub" style="font-size: 0.8rem; margin-top: 5px; color: rgba(255, 255, 255, 0.7);">{market_date_line}</div>
            </header>
            
            <!-- Signal Dashboard -->
            <div class="dashboard">
                <div class="dash-grid">
    """
    
    # Dashboard Content Logic
    buy1_tickers = [r['Symbol'] for r in valid_results if r['Signals']['Buy1']]
    buy2_tickers = [r['Symbol'] for r in valid_results if r['Signals']['Buy2']]
    sell1_tickers = [r['Symbol'] for r in valid_results if r['Signals']['Sell1']]

    # 1. 1st Buy List
    if buy1_tickers:
        html_template += """
                    <!-- 1st Buy -->
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
                    <!-- 2nd Buy -->
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
                    <!-- 1st Sell -->
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
                    <div class="strategy-row"><strong>1st Buy:</strong> Bearish Alignment (20 < 60 < 120*) + Close < EMA(20)</div>
                    <div class="strategy-row"><strong>2nd Buy:</strong> 1st Buy Conditions Met + RSI(14) < 30 (Deep Oversold)</div>
                    <div class="strategy-row"><strong>1st Sell:</strong> Bullish Alignment (20 > 60 > 120*) + Close > EMA(20) + RSI(14) > 70</div>
                    <div class="strategy-row" style="margin-top: 10px; font-style: italic;">* Note: EMA(120) is optional for new stock listings.</div>
                </div>
            </div>
    """

    # Fetch Market Indices Data
    indices_data = fetch_market_indices()
    
    indices_html = '<div class="indices-grid">'
    for idx in indices_data:
        c_class = "up" if idx['change_pct'] >= 0 else "down"
        c_sign = "+" if idx['change_pct'] >= 0 else ""
        formatted_price = f"{idx['price']:,.2f}"
        formatted_change = f"{c_sign}{idx['change_pct']:.2f}%"
        
        indices_html += f"""
            <div class="index-card">
                <span class="index-name">{idx['name']}</span>
                <span class="index-price">{formatted_price}</span>
                <span class="index-change {c_class}">{formatted_change}</span>
            </div>
        """
    indices_html += '</div>'

    # Fetch Highlights & News
    highlights = fetch_market_highlights()
    market_news = fetch_market_news()
    
    commentary_html = '<div class="commentary-section">'
    
    # Highlights
    if highlights:
        commentary_html += '<div style="margin-bottom: 15px;">'
        for h in highlights:
            commentary_html += f'<div class="highlight-item">✅ {h}</div>'
        commentary_html += '</div>'
        
    # News Drivers
    if market_news:
        commentary_html += '<div class="summary-header"><span>📰</span> KEY MARKET DRIVERS</div>'
        for n in market_news:
            commentary_html += f"""
                <div class="driver-item">
                    <a href="{n['link']}" target="_blank" class="driver-link">{n['title']}</a>
                    <span class="driver-source">{n['source']}</span>
                </div>
            """
    else:
        commentary_html += '<div class="news-empty">No major headlines found.</div>'
        
    commentary_html += '</div>'

    html_template += f"""
            <!-- Market Summary -->
            <div class="summary-box">
                {indices_html}
                
                <div class="summary-header" style="margin-top: 1rem;">
                    <span>📝</span> MARKET COMMENTARY
                </div>
                {commentary_html}
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
                            <span>📰</span> Related News & Market {f"({res['NewsAsset']} Insights)" if res['NewsAsset'] != res['Symbol'] else "Insights"}
                        </div>
                        <div class="news-list">
        """
        
        if res['News']:
            for n in res['News']:
                html_template += f"""
                            <div class="news-item">
                                <a href="{n['link']}" target="_blank" class="news-link">{n['title']}</a>
                                <span class="news-source">Source: {n['publisher']}</span>
                            </div>
            """
        else:
            html_template += """
                            <div class="news-item">
                                <p class="news-empty">There are no significant news affecting today's stock price.</p>
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
                <p>Crafted by Google Antigravity based on <a href="https://heroyik.github.io" target="_blank" style="color: inherit; text-decoration: underline;">nIcK</a>'s trading strategy</p>
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
    
    report_path = os.path.join("public", filename)
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(html_template)
    print(f"HTML report {filename} generated: {report_path}")

def send_kakao_link(briefing_url, results, market_date):
    if not KAKAO_REST_API_KEY or not KAKAO_REFRESH_TOKEN:
        print(f"Kakao configuration missing. Briefing URL: {briefing_url}")
        return

    access_token = get_access_token()
    
    url = "https://kapi.kakao.com/v2/api/talk/memo/default/send"
    headers = {
        "Authorization": f"Bearer {access_token}"
    }

    # Extract signals
    valid_results = [r for r in results if not isinstance(r, str)]
    buy1 = [r['Symbol'] for r in valid_results if r['Signals']['Buy1']]
    buy2 = [r['Symbol'] for r in valid_results if r['Signals']['Buy2']]
    sell1 = [r['Symbol'] for r in valid_results if r['Signals']['Sell1']]

    # Build signal summary
    summary_parts = []
    if buy1: summary_parts.append(f"✅ 1차 매수: {', '.join(buy1)}")
    if buy2: summary_parts.append(f"🔥 2차 매수: {', '.join(buy2)}")
    if sell1: summary_parts.append(f"🚀 1차 매도: {', '.join(sell1)}")

    if not summary_parts:
        summary_text = "금일 매매신호가 탐지되지 않았습니다"
    else:
        summary_text = "\n".join(summary_parts)

    # Final text construction (Title + Body)
    # Header: 📊 nIcK의 미국 증시 브리핑
    # Body first line: YYYY-MM-DD 매매신호 브리핑이 준비되었습니다.
    full_text = f"📊 nIcK의 미국 증시 브리핑\n{market_date} 매매신호 브리핑이 준비되었습니다.\n{summary_text}"
    
    # Kakao Text template limit is 200 chars
    if len(full_text) > 200:
        full_text = full_text[:197] + "..."

    template_object = {
        "object_type": "text",
        "text": full_text,
        "link": {
            "web_url": briefing_url,
            "mobile_web_url": briefing_url
        },
        "button_title": "상세 리포트 보기"
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

def get_last_trading_date():
    """Fetches the last trading date from SPY history."""
    try:
        spy = yf.Ticker("SPY")
        hist = spy.history(period="5d")
        if hist.empty:
            return None
        return hist.index[-1].date().strftime('%Y-%m-%d')
    except Exception as e:
        print(f"Error fetching last trading date: {e}")
        return None

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="FinRep: Daily US Stock Briefing")
    parser.add_argument("--manual", action="store_true", help="Run in manual mode (updates index.html, skips Kakao notification)")
    args = parser.parse_args()

    # 1. Determine Target Date (Clock Time in NY) - What day is it locally?
    ny_tz = ZoneInfo("America/New_York")
    now_ny = datetime.now(ny_tz)
    target_date_str = now_ny.strftime('%Y-%m-%d')

    # 2. Determine Data Date (Market Reality) - What was the last actual trading day?
    data_date_str = get_last_trading_date()
    
    if not data_date_str:
        print("❌ Critical: Unable to fetch SPY data to determine market date.")
        # Determine fallback behavior? exit or fallback to target
        if not args.manual:
            exit(1)
        data_date_str = target_date_str # Fallback for manual if internet is weird but we want to try?

    print(f"Target Date (NY): {target_date_str}")
    print(f"Data Date (SPY):  {data_date_str}")

    # 3. Check for Auto-Run Validity
    # Only skip generation on SCHEDULED (cron) runs if the market was closed on the target date.
    # Manual runs (workflow_dispatch, manual flag) or Push triggers should always proceed.
    event_name = os.environ.get('GITHUB_EVENT_NAME', 'manual')
    is_scheduled = (event_name == 'schedule')
    is_manual = (event_name == 'workflow_dispatch') or args.manual
    
    if is_scheduled:
        # If auto-schedule, we only run if the Market was OPEN for the 'Target Date'.
        # Since we run at 07:00 KST (17:00/18:00 EST), the Data Date matches Target Date if market was open.
        # If target != data, it means market was closed on Target Date (e.g. Holiday or Weekend).
        if target_date_str != data_date_str:
            print(f"🚫 Market was CLOSED on {target_date_str}. (Last open: {data_date_str})")
            print("Skipping scheduled briefing generation for holiday/weekend.")
            exit(0)
        print(f"✅ Market was OPEN on {target_date_str}. Proceeding with scheduled run.")
    elif is_manual:
        print(f"✅ Manual execution triggered (Event: {event_name}). Proceeding regardless of market status.")
    else:
        print(f"✅ Proceeding with briefing (Trigger: {event_name}). Using latest data from {data_date_str}.")

    # 4. Set the official Reference Market Date for the report
    # ALWAYS use the Data Date, so the report says "Analysis of Jan 5" even if generated on "Jan 6 morning".
    market_date_str = data_date_str

    report_data = []
    for ticker in TICKERS:
        print(f"Analyzing {ticker}...")
        report_data.append(fetch_and_analyze(ticker))
    
    # Generate HTML report
    generate_html_report(report_data, "index.html", market_date_str)
    
    # GitHub Pages URL
    GITHUB_USER = "heroyik"
    REPO_NAME = "finrep"
    briefing_url = f"https://{GITHUB_USER}.github.io/{REPO_NAME}/"
    
    # Send KakaoTalk Link (Skip in manual mode)
    if not args.manual:
        send_kakao_link(briefing_url, report_data, market_date_str)
    else:
        print("Manual mode: Skipping KakaoTalk notification.")

