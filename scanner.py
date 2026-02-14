import requests
import pandas as pd
import numpy as np
import time
from datetime import datetime, timedelta

# Settings
SHORT_WINDOW = 50
LONG_WINDOW = 200
TIMEFRAMES = ['1h', '4h', '1d']
QUOTE_ASSET = "USDT"

def fetch_klines(symbol, interval, limit=300):
    """Fetches public candle data without an API key."""
    url = f"https://api.binance.com/api/v3/klines"
    params = {'symbol': symbol, 'interval': interval, 'limit': limit}
    try:
        response = requests.get(url, params=params, timeout=10)
        data = response.json()
        df = pd.DataFrame(data, columns=[
            'open_time', 'open', 'high', 'low', 'close', 'volume',
            'close_time', 'qav', 'num_trades', 'taker_base', 'taker_quote', 'ignore'
        ])
        df['close'] = df['close'].astype(float)
        df['time'] = pd.to_datetime(df['close_time'], unit='ms')
        return df
    except:
        return None

def find_cross(df):
    """Checks for a Golden Cross in the last 24 hours."""
    if df is None or len(df) < LONG_WINDOW: return False
    
    # Calculate SMAs
    df['sma50'] = df['close'].rolling(SHORT_WINDOW).mean()
    df['sma200'] = df['close'].rolling(LONG_WINDOW).mean()
    
    # Look at the last 24 hours only
    last_24h = datetime.utcnow() - timedelta(hours=24)
    recent = df[df['time'] >= last_24h].copy()
    
    # Check for crossover: 50 was below 200, now it is above
    for i in range(1, len(df)):
        if df['time'].iloc[i] >= last_24h:
            if df['sma50'].iloc[i] > df['sma200'].iloc[i] and \
               df['sma50'].iloc[i-1] <= df['sma200'].iloc[i-1]:
                return True
    return False

# 1. Get all USDT symbols
exchange_info = requests.get("https://api.binance.com/api/v3/exchangeInfo").json()
symbols = [s['symbol'] for s in exchange_info['symbols'] 
           if s['status'] == 'TRADING' and s['symbol'].endswith(QUOTE_ASSET)]

print(f"Scanning {len(symbols)} pairs...")
results = []

for symbol in symbols[:100]: # Scanning first 100 to stay under GitHub's time limit
    status = {'Symbol': symbol}
    found_any = False
    for tf in TIMEFRAMES:
        df = fetch_klines(symbol, tf)
        if find_cross(df):
            status[tf] = "🚀 CROSS"
            found_any = True
        else:
            status[tf] = "-"
    
    if found_any:
        results.append(status)
    time.sleep(0.1) # Small delay to be nice
