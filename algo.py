import requests
import pandas as pd
import os
from urllib.parse import quote

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
    return 100 - (100 / (1 + rs))

bases = ["https://query1.finance.yahoo.com", "https://query2.finance.yahoo.com"]
headers = {"User-Agent": "Mozilla/5.0"}

def fetch(symbol):
    for base in bases:
        try:
            url = f"{base}/v8/finance/chart/{quote(symbol, safe='')}?interval=5m&range=5d"
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
                return df
        except Exception as e:
            print(f"Retry {symbol} {base}: {e}")
            continue
    return None

def analyze(name, symbol, is_stock=False):
    print(f"Fetching {name}...")
    df = fetch(symbol)
    if df is None or len(df) == 0:
        return f"{name}: No data HOLD"
    try:
        df["dt"] = pd.to_datetime(df["ts"], unit="s", utc=True).dt.tz_convert("Asia/Kolkata")
        df["ema20"] = ema(df["close"], 20)
        df["rsi"] = rsi_calc(df["close"], 14)
        today = pd.Timestamp.now(tz="Asia/Kolkata").date()
        dft = df[df["dt"].dt.date == today].reset_index(drop=True)
        print(f"{name} total:{len(df)} today:{len(dft)}")
        if len(dft) == 0:
            return f"{name}: Closed HOLD"
        if len(dft) < 2:
            return f"{name}: Warming up HOLD"
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
        if has_vol:
            ce_ok = close > vwap
            pe_ok = close < vwap
        else:
            ce_ok = True
            pe_ok = True
        if ce_ok and rsi > 55 and close > ema20:
            sig = "BUY CE" if not is_stock else "STOCK CALL"
        elif pe_ok and rsi < 45 and close < ema20:
            sig = "BUY PE" if not is_stock else "STOCK PUT"
        else:
            sig = "HOLD"
        print(f"{name} {close:.2f} RSI {rsi:.1f} {sig}")
        label = "SIGNAL" if sig != "HOLD" else ">>> HOLD"
        return f"{name} {tnow} {close:.2f} RSI {rsi:.1f} {label} {sig}"
    except Exception as e:
        print(f"{name} Error {e}")
        return f"{name}: Error HOLD"

INDICES = {
    "NIFTY": "^NSEI",
    "BANKNIFTY": "^NSEBANK",
    "SENSEX": "^BSESN",
    "FINNIFTY": "^CNXFIN"
}

STOCKS = {
    "RELIANCE": "RELIANCE.NS",
    "HDFCBANK": "HDFCBANK.NS",
    "ICICIBANK": "ICICIBANK.NS",
    "INFY": "INFY.NS",
    "TCS": "TCS.NS",
    "SBIN": "SBIN.NS",
    "TATAMOTORS": "TATAMOTORS.NS",
    "ITC": "ITC.NS"
}

out = []
for n, s in INDICES.items():
    out.append(analyze(n, s, False))

stock_signals = []
for n, s in STOCKS.items():
    res = analyze(n, s, True)
    if "SIGNAL" in res:
        stock_signals.append(res)
        out.append(res)

if not stock_signals:
    out.append("STOCKS: No signal HOLD")

tnow_all = pd.Timestamp.now(tz="Asia/Kolkata").strftime("%H:%M")
msg = f"Mass Algo {tnow_all}\n" + "\n".join(out)
print(msg)
send_tg(msg)
