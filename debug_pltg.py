import yfinance as yf
import pandas as pd
import pandas_ta as ta

def debug_tickers():
    for ticker_symbol in ["BITU", "PLTG", "CRWU"]:
        ticker = yf.Ticker(ticker_symbol)
        df = ticker.history(period="1y")
        df['EMA20'] = ta.ema(df['Close'], length=20)
        df['EMA60'] = ta.ema(df['Close'], length=60)
        df['EMA120'] = ta.ema(df['Close'], length=120)
        
        last = df.iloc[-1]
        print(f"\n--- {ticker_symbol} (Data Length: {len(df)}) ---")
        print(f"EMA20: {last['EMA20']:.2f}")
        print(f"EMA60: {last['EMA60']:.2f}")
        print(f"EMA120: {last['EMA120']:.2f}")
        
        a1 = last['EMA20'] < last['EMA60']
        a2 = last['EMA60'] < last['EMA120'] if not pd.isna(last['EMA120']) else True
        print(f"20 < 60: {a1}")
        print(f"60 < 120: {a2}")
        print(f"Alignment: {a1 and a2}")


if __name__ == "__main__":
    debug_tickers()
