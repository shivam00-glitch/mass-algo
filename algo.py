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
        url = f"{base}/v8/finance/chart/%5ENSEI?interval=5m&range=5d"
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
        df["dt"] = pd.to_datetime(df["ts"], unit="s", utc=True).dt.tz_convert("Asia/Kolkata")
        today = pd.Timestamp.now(tz="Asia/Kolkata").date()
        dft = df[df["dt"].dt.date == today].reset_index(drop=True)
        print(f"total candles: {len(df)}, today candles: {len(dft)}")
        if len(dft) == 0:
            msg = "Mass Algo: Market closed / Holiday\n>>> HOLD - No Trade"
            print(msg)
            send_tg(msg)
        elif len(dft) < 2:
            msg = "Mass Algo: Market warming up...\n>>> HOLD - No Trade"
            print(msg)
            send_tg(msg)
        else:
            df["ema20"] = ema(df["close"], 20)
            df["rsi"] = rsi_calc(df["close"], 14)
            dft = df[df["dt"].dt.date == today].reset_index(drop=True)
            tp = (dft["high"] + dft["low"] + dft["close"]) / 3
            vol = dft["volume"].fillna(0)
            has_vol = vol.sum() > 0
            if has_vol:
                vwap = float(((tp * vol).cumsum() / vol.cumsum()).iloc[-1])
            else:
                vwap = float(dft["close"].iloc[-1])
            close = float(dft["close"].iloc[-1])
            ema20 = float(dft["ema20"].iloc[-1])
            rsi = float(dft["rsi"].iloc[-1])
            tnow = dft["dt"].iloc[-1].strftime("%H:%M")
            print(f"NIFTY {close:.2f} @ {tnow} RSI {rsi:.1f} VWAP {vwap:.2f} EMA20 {ema20:.2f}")
            if has_vol:
                ce_vwap_ok = close > vwap
                pe_vwap_ok = close < vwap
            else:
                ce_vwap_ok = True
                pe_vwap_ok = True
            if ce_vwap_ok and rsi > 55 and close > ema20:
                signal = ">>> SIGNAL BUY NIFTY ATM CE - Only Buying"
            elif pe_vwap_ok and rsi < 45 and close < ema20:
                signal = ">>> SIGNAL BUY NIFTY ATM PE - Only Buying"
            else:
                signal = ">>> HOLD - No Trade"
            print(signal)
            msg = (f"Mass Algo NIFTY {tnow}\nPrice {close:.2f}\nRSI {rsi:.1f}\nVWAP {vwap:.2f}\nEMA20 {ema20:.2f}\n{signal}")
            send_tg(msg)
except Exception as e:
    print(f"Error: {e}")
    send_tg(f"Mass Algo Error {e}\n>>> HOLD - No Trade")
