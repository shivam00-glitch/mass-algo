import requests
import pandas as pd
import os

BOT = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT = os.getenv("TELEGRAM_CHAT_ID")

def send_tg(msg):
    try:
        if BOT and CHAT:
            url = f"https://api.telegram.org/bot{BOT}/sendMessage"
            requests.post(url, data={"chat_id": CHAT, "text": msg}, timeout=15)
            print("Telegram sent")
        else:
            print("Telegram secret missing")
    except Exception as e:
        print(f"Telegram error: {e}")

def ema(s, span):
    return s.ewm(span=span, adjust=False).mean()

def rsi_calc(close, period=14):
    delta = close.diff()
    gain = delta.where(delta > 0, 0)
    loss = -delta.where(delta < 0, 0)
    avg_gain = gain.rolling(period).mean()
    avg_loss = loss.rolling(period).mean()
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    return rsi

print("Fetching NIFTY...")
df = None
bases = ["https://query1.finance.yahoo.com", "https://query2.finance.yahoo.com"]
headers = {"User-Agent": "Mozilla/5.0"}

for base in bases:
    try:
        url = f"{base}/v8/finance/chart/%5ENSEI?interval=5m&range=1d"
        r = requests.get(url, headers=headers, timeout=20)
        j = r.json()
        result = j["chart"]["result"][0]
        ts = result["timestamp"]
        q = result["indicators"]["quote"][0]
        df = pd.DataFrame({
            "ts": ts,
            "open": q["open"],
            "high": q["high"],
            "low": q["low"],
            "close": q["close"],
            "volume": q["volume"]
        })
        df = df.dropna(subset=["close"])
        if len(df) > 0:
            break
    except Exception as e:
        print(f"Retry {base}: {e}")
        continue

try:
    if df is None or len(df) == 0:
        msg = "Mass Algo: No data from Yahoo\n>>> HOLD - No Trade"
        print(msg)
        send_tg(msg)
    else:
        print(f"candles: {len(df)}")
        if len(df) < 30:
            msg = "Mass Algo: Market closed time\n>>> HOLD - No Trade"
            print(msg)
            send_tg(msg)
        else:
            df["ema20"] = ema(df["close"], 20)
            df["rsi"] = rsi_calc(df["close"], 14)
            tp = (df["high"] + df["low"] + df["close"]) / 3
            vol = df["volume"].fillna(0)
            df["vwap"] = (tp * vol).cumsum() / vol.cumsum().replace(0, float("nan"))
            df["vwap"] = df["vwap"].fillna(df["close"])
            close = float(df["close"].iloc[-1])
            ema20 = float(df["ema20"].iloc[-1])
            rsi = float(df["rsi"].iloc[-1])
            vwap = float(df["vwap"].iloc[-1])
            print(f"NIFTY {close:.2f} RSI {rsi:.1f} VWAP {vwap:.2f} EMA20 {ema20:.2f}")
            if close > vwap and rsi > 55 and close > ema20:
                signal = ">>> SIGNAL BUY NIFTY ATM CE - Only Buying"
            elif close < vwap and rsi < 45 and close < ema20:
                signal = ">>> SIGNAL BUY NIFTY ATM PE - Only Buying"
            else:
                signal = ">>> HOLD - No Trade"
            print(signal)
            msg = f"Mass Algo NIFTY\nPrice {close:.2f}\nRSI {rsi:.1f}\nVWAP {vwap:.2f}\n{signal}"
            send_tg(msg)
except Exception as e:
    print(f"Error: {e}")
    send_tg(f"Mass Algo Error {e}\n>>> HOLD - No Trade")
