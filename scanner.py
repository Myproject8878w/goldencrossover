import requests
import pandas as pd
import numpy as np
import time
from datetime import datetime, timedelta

# Configuration
SHORT_EMA = 50
LONG_EMA = 200
TIMEFRAMES = ['1h', '4h', '1d']
QUOTE_ASSET = "USDT"

def fetch_klines(symbol, interval):
    """Fetches candle data using Binance Public API (No API Key required)"""
    url = "https://api.binance.com/api/v3/klines"
    params = {'symbol': symbol, 'interval': interval, 'limit': 300}
    try:
        response = requests.get(url, params=params, timeout=10)
        if response.status_code != 200: return None
        
        data = response.json()
        # Create DataFrame from raw list
        df = pd.DataFrame(data, columns=[
            'open_time', 'open', 'high', 'low', 'close', 'volume',
            'close_time', 'qav', 'num_trades', 'taker_base', 'taker_quote', 'ignore'
        ])
        df['close'] = df['close'].astype(float)
        df['timestamp'] = pd.to_datetime(df['close_time'], unit='ms')
        return df
    except Exception:
        return None

def check_golden_cross(df):
    """Detects if 50 EMA crossed above 200 EMA in the last 24 hours"""
    if df is None or len(df) < LONG_EMA: return False
    
    # Calculate EMA (more common for Golden Cross than SMA)
    df['ema50'] = df['close'].ewm(span=SHORT_EMA, adjust=False).mean()
    df['ema200'] = df['close'].ewm(span=LONG_EMA, adjust=False).mean()
    
    # Define the 24-hour window
    cutoff = datetime.utcnow() - timedelta(hours=24)
    recent = df[df['timestamp'] >= cutoff]
    
    if recent.empty: return False

    # Check for crossover logic: 
    # Current: EMA50 > EMA200 AND Previous: EMA50 <= EMA200
    for i in range(1, len(df)):
        if df['timestamp'].iloc[i] >= cutoff:
            if df['ema50'].iloc[i] > df['ema200'].iloc[i] and \
               df['ema50'].iloc[i-1] <= df['ema200'].iloc[i-1]:
                return True
    return False

# 1. Get List of Symbols
try:
    resp = requests.get("https://api.binance.com/api/v3/exchangeInfo")
    data = resp.json()
    # Safely get symbols list
    symbols = [s['symbol'] for s in data.get('symbols', []) 
               if s['status'] == 'TRADING' and s['symbol'].endswith(QUOTE_ASSET)]
except Exception as e:
    print(f"Failed to fetch market info: {e}")
    symbols = []

print(f"Scanning {len(symbols)} pairs...")
found_signals = []

# 2. Run Scan (Limited to top 150 pairs to avoid GitHub timeouts)
for symbol in symbols[:150]:
    row = {'Symbol': symbol}
    hit = False
    for tf in TIMEFRAMES:
        df = fetch_klines(symbol, tf)
        if check_golden_cross(df):
            row[tf] = "🚀 GOLDEN"
            hit = True
        else:
            row[tf] = "-"
    
    if hit:
        found_signals.append(row)
    time.sleep(0.1) # Be kind to Binance API

# 3. Print Results
if found_signals:
    print("\n" + "="*30)
    print("GOLDEN CROSS ALERTS (Last 24h)")
    print("="*30)
    print(pd.DataFrame(found_signals).to_string(index=False))
else:
    print("\nNo Golden Crosses found in the last 24 hours.")
