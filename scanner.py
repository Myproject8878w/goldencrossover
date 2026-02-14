import os
import time
import pandas as pd
import numpy as np
from binance.client import Client
from tqdm import tqdm

# Load API keys from GitHub Secrets
api_key = os.environ.get("BINANCE_API_KEY")
api_secret = os.environ.get("BINANCE_API_SECRET")

# Config
SHORT_WINDOW = 50
LONG_WINDOW = 200
TIMEFRAME = Client.KLINE_INTERVAL_4HOUR
LOOKBACK_DAYS = 5
QUOTE_ASSET = "USDT"
CANDLE_FETCH_LIMIT = 1000

client = Client(api_key, api_secret)

def klines_to_df(klines):
    df = pd.DataFrame(klines, columns=['open_time', 'open', 'high', 'low', 'close', 'volume', 'close_time', 'qav', 'num_tr', 'tbb', 'tbq', 'ignore'])
    df['close_time'] = pd.to_datetime(df['close_time'], unit='ms')
    df['close'] = df['close'].astype(float)
    return df

def detect_crosses(df):
    if len(df) < LONG_WINDOW + 2: return []
    df['sma_short'] = df['close'].rolling(SHORT_WINDOW).mean()
    df['sma_long'] = df['close'].rolling(LONG_WINDOW).mean()
    df.dropna(inplace=True)
    
    diff = df['sma_short'] - df['sma_long']
    sign = np.sign(diff)
    sign_shift = sign.shift(1)
    
    crosses = []
    # Golden Cross logic
    golden = (sign_shift < 0) & (sign > 0)
    # Death Cross logic
    death = (sign_shift > 0) & (sign < 0)
    
    for i in df.index[golden | death]:
        crosses.append({'type': 'golden' if golden.loc[i] else 'death', 'time': df.loc[i, 'close_time']})
    return crosses

# Main Scan
exchange_info = client.get_exchange_info()
symbols = [s['symbol'] for s in exchange_info['symbols'] if s['status'] == 'TRADING' and s['symbol'].endswith(QUOTE_ASSET)]

results = []
for symbol in tqdm(symbols):
    try:
        klines = client.get_klines(symbol=symbol, interval=TIMEFRAME, limit=CANDLE_FETCH_LIMIT)
        df = klines_to_df(klines)
        crosses = detect_crosses(df)
        if crosses:
            res = crosses[-1]
            results.append({'symbol': symbol, 'type': res['type'], 'time': res['time']})
        time.sleep(0.1) # Respect rate limits
    except:
        continue

if results:
    print(pd.DataFrame(results))
else:
    print("No crosses found.")
