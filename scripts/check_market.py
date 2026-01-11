import yfinance as yf
from datetime import datetime
import os
import sys

try:
    from zoneinfo import ZoneInfo
except ImportError:
    # Fallback for Python < 3.9 though the workflow uses 3.13
    from datetime import timezone, timedelta
    class ZoneInfo:
        def __init__(self, name):
            self.name = name

def is_market_open_today():
    """
    Checks if the US stock market (NYSE/NASDAQ) was open today (NY time).
    Compares the current date in NY with the latest date available for ^GSPC.
    """
    try:
        # 1. Get current date in New York
        ny_tz = ZoneInfo("America/New_York")
        now_ny = datetime.now(ny_tz)
        today_ny = now_ny.strftime("%Y-%m-%d")
        
        print(f"Current NY Time: {now_ny.strftime('%Y-%m-%d %H:%M:%S %Z')}")
        print(f"Target Date (NY): {today_ny}")

        # 2. Get latest trading date from yfinance
        # Use ^GSPC (S&P 500) as a proxy for the entire US market
        ticker = yf.Ticker("^GSPC")
        # period="1d" should return the latest finalized or currently trading daily bar
        hist = ticker.history(period="1d")
        
        if hist.empty:
            print("No market data fetched. Defaulting to True (execute).")
            return True
        
        last_trading_date = hist.index[-1].strftime("%Y-%m-%d")
        print(f"Latest Market Trading Date: {last_trading_date}")

        # 3. Compare
        if last_trading_date == today_ny:
            print("Market was OPEN today. Proceeding with execution.")
            return True
        else:
            print(f"Market was CLOSED today (Holiday or Weekend). Skipping.")
            return False
            
    except Exception as e:
        print(f"Error checking market status: {e}")
        # In case of error, we default to True to avoid missing a report
        return True

if __name__ == "__main__":
    is_open = is_market_open_today()
    
    # Set GitHub Actions output if running in CI
    github_output = os.getenv("GITHUB_OUTPUT")
    if github_output:
        with open(github_output, "a") as f:
            f.write(f"is_open={str(is_open).lower()}\n")
    
    # Exit with 0 regardless, we use the output for control flow
    sys.exit(0)
