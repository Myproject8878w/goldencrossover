import requests
import pandas as pd
import numpy as np
import time
from datetime import datetime, timedelta

# --- SETTINGS ---
SHORT_EMA = 50
LONG_EMA = 200
TIMEFRAMES = ['1h', '4h', '1d']
QUOTE_ASSET = "USDT"

# For testing, we look back 30 days. For live alerts, change to 1.
LOOKBACK_DAYS = 30 

# Alternate Binance endpoints to bypass GitHub IP blocks
BASE_URLS = ["https://api.binance.com", "https://api1.binance.com", "https://api2.binance.com"]

def safe_request(path, params=None):
    """Tries multiple Binance URLs until one works."""
    for base in BASE_URLS:
        try:
            resp = requests.get(base + path, params=params, timeout=10)
            if resp.status_code == 200:
                return resp.json()
        except:
            continue
    return None

def fetch_data(symbol, interval):
    """Fetches public candle data."""
    data = safe_request("/api/v3/klines", {'symbol': symbol, 'interval': interval, 'limit': 300})
    if not data: return None
    
    df = pd.DataFrame(data, columns=['ot','o','h','l','close','v','ct','q','n','tb','tq','i'])
    df['close'] = df['close'].astype(float)
    df['time'] = pd.to_datetime(df['ct'], unit='ms')
    return df

def detect_crossover(df):
    """Logic for the Golden Cross."""
    if df is None or len(df) < LONG_EMA: return False
    
    # Calculate EMA
    df['ema50'] = df['close'].ewm(span=SHORT_EMA, adjust=False).mean()
    df['ema200'] = df['close'].ewm(span=LONG_EMA, adjust=False).mean()
    
    # Time window for the cross
    cutoff = datetime.utcnow() - timedelta(days=LOOKBACK_DAYS)
    
    # Look for the specific crossing point
    for i in range(1, len(df)):
        if df['time'].iloc[i] >= cutoff:
            # Golden Cross: 50 EMA goes ABOVE 200 EMA
            if df['ema50'].iloc[i] > df['ema200'].iloc[i] and \
               df['ema50'].iloc[i-1] <= df['ema200'].iloc[i-1]:
                return True
    return False

# --- MAIN EXECUTION ---
print(f"--- STARTING SCAN (Lookback: {LOOKBACK_DAYS} days) ---")

market_data = safe_request("/api/v3/exchangeInfo")
if not market_data:
    print("Error: Could not connect to Binance API.")
    exit()

symbols = [s['symbol'] for s in market_data['symbols'] 
           if s['status'] == 'TRADING' and s['symbol'].endswith(QUOTE_ASSET)]

print(f"Found {len(symbols)} pairs. Scanning top 100 for speed...")

results = []
for symbol in symbols[:100]:
    row = {'Symbol': symbol}
    found = False
    for tf in TIMEFRAMES:
        df = fetch_data(symbol, tf)
        if detect_crossover(df):
            row[tf] = "🚀 CROSS"
            found = True
        else:
            row[tf] = "-"
    
    if found:
        results.append(row)
        print(f"Signal found: {symbol}")
    
    time.sleep(0.1) # Prevent rate limiting

if results:
    print("\n--- SCAN RESULTS ---")
    print(pd.DataFrame(results).to_string(index=False))
else:
    print("\nNo crossovers found in this period.")
