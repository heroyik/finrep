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

def fetch_and_analyze(ticker_symbol):
    try:
        ticker = yf.Ticker(ticker_symbol)
        df = ticker.history(period="1y")
        
        if df.empty:
            return f"❌ {ticker_symbol}: 데이터를 가져올 수 없습니다."

        df['RSI'] = ta.rsi(df['Close'], length=14)
        df['EMA20'] = ta.ema(df['Close'], length=20)
        df['EMA60'] = ta.ema(df['Close'], length=60)
        df['EMA120'] = ta.ema(df['Close'], length=120)

        last_row = df.iloc[-1]
        prev_close = df.iloc[-2]['Close']
        current_close = last_row['Close']
        change_pct = ((current_close - prev_close) / prev_close) * 100

        result = {
            "Symbol": ticker_symbol,
            "Price": round(current_close, 2),
            "Change": round(change_pct, 2),
            "RSI": round(last_row['RSI'], 2) if not pd.isna(last_row['RSI']) else "N/A",
            "EMA20": round(last_row['EMA20'], 2) if not pd.isna(last_row['EMA20']) else "N/A",
            "EMA60": round(last_row['EMA60'], 2) if not pd.isna(last_row['EMA60']) else "N/A",
            "EMA120": round(last_row['EMA120'], 2) if not pd.isna(last_row['EMA120']) else "N/A"
        }
        return result
    except Exception as e:
        return f"❌ {ticker_symbol}: 에러 발생 - {str(e)}"

def format_message(results):
    now = datetime.now()
    message = f"📊 미국 증시 브리핑 ({now.strftime('%Y-%m-%d')})\n\n"
    
    for res in results:
        if isinstance(res, str):
            message += f"{res}\n"
            continue
        
        emoji = "📈" if res['Change'] >= 0 else "📉"
        message += f"[{res['Symbol']}] {res['Price']} ({emoji} {res['Change']}%)\n"
        message += f" - RSI: {res['RSI']}\n"
        message += f" - EMA: 20:{res['EMA20']} / 60:{res['EMA60']} / 120:{res['EMA120']}\n\n"
    
    return message

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
        print(f"Error refreshing token: {tokens}")
        return None

import json

def send_kakao_message(message):
    if not KAKAO_REST_API_KEY or not KAKAO_REFRESH_TOKEN:
        print("Kakao configuration missing. Printing message to console:")
        print(message)
        return

    access_token = get_access_token()
    if not access_token:
        return

    url = "https://kapi.kakao.com/v2/api/talk/memo/default/send"
    headers = {
        "Authorization": f"Bearer {access_token}"
    }
    
    template_object = {
        "object_type": "text",
        "text": message,
        "link": {
            "web_url": "https://finance.yahoo.com",
            "mobile_web_url": "https://finance.yahoo.com"
        },
        "button_title": "자세히 보기"
    }
    
    payload = {
        "template_object": json.dumps(template_object)
    }
    
    try:
        response = requests.post(url, headers=headers, data=payload)
        response.raise_for_status()
        print("KakaoTalk message sent successfully!")
    except Exception as e:
        print(f"Failed to send KakaoTalk message: {e}")
        if response:
            print(f"Response: {response.json()}")

if __name__ == "__main__":
    report_data = []
    for ticker in TICKERS:
        print(f"Analyzing {ticker}...")
        report_data.append(fetch_and_analyze(ticker))
    
    briefing_msg = format_message(report_data)
    send_kakao_message(briefing_msg)

