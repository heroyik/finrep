import yfinance as yf
import pandas as pd
import pandas_ta as ta
import os
from main import generate_chart

def test_annotation():
    symbol = "NVDA" # Use a high-volume stock for testing
    ticker = yf.Ticker(symbol)
    df = ticker.history(period="1y")
    
    # Calculate indicators as per main.py logic
    df['RSI'] = ta.rsi(df['Close'], length=14)
    df['EMA20'] = ta.ema(df['Close'], length=20)
    df['EMA60'] = ta.ema(df['Close'], length=60)
    df['EMA120'] = ta.ema(df['Close'], length=120)
    
    filename = "test_annotation_chart.png"
    print(f"Generating test chart for {symbol}...")
    generate_chart(symbol, df, filename)
    
    expected_path = os.path.join("public/charts", filename)
    if os.path.exists(expected_path):
        print(f"✅ Test successful! Chart saved to: {expected_path}")
    else:
        print("❌ Test failed! Chart not found.")

if __name__ == "__main__":
    # Ensure public/charts exists
    if not os.path.exists("public/charts"):
        os.makedirs("public/charts")
    test_annotation()
