import requests, pandas as pd, os, time
from datetime import datetime
from zoneinfo import ZoneInfo

BOT = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT = os.getenv("TELEGRAM_CHAT_ID")

def push(text):
    try:
        requests.post(f"https://api.telegram.org/bot{BOT}/sendMessage", json={"chat_id": CHAT, "text": text}, timeout=15)
    except Exception as e:
        print(e)

def send_tg(msg):
    if not BOT or not CHAT:
        print(msg); return
    cur = ""
    for line in msg.split("\n"):
        if len(cur)+len(line)+1 > 3500:
            push(cur); cur = ""
        cur += line + "\n"
    if cur: push(cur)

def rsi(s, p=14):
    d = s.diff()
    g = d.clip(lower=0).rolling(p).mean()
    l = -d.clip(upper=0).rolling(p).mean()
    rs = g/(l+1e-9)
    return 100-(100/(1+rs))

def fetch(symbol, rng, interval):
    for base in ["https://query1.finance.yahoo.com","https://query2.finance.yahoo.com"]:
        try:
            r = requests.get(f"{base}/v8/finance/chart/{symbol}?range={rng}&interval={interval}", headers={"User-Agent":"Mozilla/5.0"}, timeout=15).json()
            res = r["chart"]["result"][0]
            ts = res["timestamp"]
            q = res["indicators"]["quote"][0]
            df = pd.DataFrame({"ts":ts,"close":q["close"],"high":q["high"],"low":q["low"],"vol":q["volume"]})
            df = df.dropna(subset=["close"])
            return df
        except: continue
    return None

INDICES = {"NIFTY":"^NSEI","BANKNIFTY":"^NSEBANK","SENSEX":"^BSESN","FINNIFTY":"^CNXFIN"}

STOCKS = {"RELIANCE":"RELIANCE.NS","HDFCBANK":"HDFCBANK.NS","ICICIBANK":"ICICIBANK.NS","INFY":"INFY.NS","TCS":"TCS.NS","SBIN":"SBIN.NS","TATAMOTORS":"TATAMOTORS.NS","ITC":"ITC.NS","AXISBANK":"AXISBANK.NS","KOTAKBANK":"KOTAKBANK.NS","LT":"LT.NS","TITAN":"TITAN.NS","SUNPHARMA":"SUNPHARMA.NS","TATASTEEL":"TATASTEEL.NS","ADANIENT":"ADANIENT.NS","ADANIPORTS":"ADANIPORTS.NS","ASIANPAINT":"ASIANPAINT.NS","BAJFINANCE":"BAJFINANCE.NS","BAJAJFINSV":"BAJAJFINSV.NS","BHARTIARTL":"BHARTIARTL.NS","BPCL":"BPCL.NS","CIPLA":"CIPLA.NS","COALINDIA":"COALINDIA.NS","DIVISLAB":"DIVISLAB.NS","DRREDDY":"DRREDDY.NS","EICHERMOT":"EICHERMOT.NS","GRASIM":"GRASIM.NS","HCLTECH":"HCLTECH.NS","HDFCLIFE":"HDFCLIFE.NS","HEROMOTOCO":"HEROMOTOCO.NS","HINDALCO":"HINDALCO.NS","INDUSINDBK":"INDUSINDBK.NS","JSWSTEEL":"JSWSTEEL.NS","MARUTI":"MARUTI.NS","NTPC":"NTPC.NS","ONGC":"ONGC.NS","POWERGRID":"POWERGRID.NS","SBILIFE":"SBILIFE.NS","TATACONSUM":"TATACONSUM.NS","TATAPOWER":"TATAPOWER.NS","TECHM":"TECHM.NS","ULTRACEMCO":"ULTRACEMCO.NS","WIPRO":"WIPRO.NS","APOLLOHOSP":"APOLLOHOSP.NS","BRITANNIA":"BRITANNIA.NS","BAJAJAUTO":"BAJAJ-AUTO.NS","NESTLEIND":"NESTLEIND.NS","SHRIRAMFIN":"SHRIRAMFIN.NS","VEDL":"VEDL.NS","TATACHEM":"TATACHEM.NS"}

now = datetime.now(ZoneInfo("Asia/Kolkata"))
hm = now.strftime("%H:%M")
out = [f"Mass Algo {hm} - FULL COMPLETE"]

out.append("\n--- INDEX 15min Only Buying ---")
for name, sym in INDICES.items():
    df = fetch(sym,"5d","5m")
    if df is None or len(df)<5:
        out.append(f"{name}: HOLD"); continue
    df["dt"] = pd.to_datetime(df["ts"], unit="s", utc=True).dt.tz_convert("Asia/Kolkata")
    today = df[df["dt"].dt.date == now.date()]
    if len(today)<2:
        out.append(f"{name}: HOLD"); continue
    c = today["close"]
    ema = c.ewm(span=20).mean().iloc[-1]
    r = rsi(c).iloc[-1]
    tp = (today["high"]+today["low"]+today["close"])/3
    vwap = (tp*today["vol"]).sum()/(today["vol"].sum()+1e-9)
    price = c.iloc[-1]
    if hm < "09:30":
        sig = "WAIT"
    elif price>vwap and price>ema*1.0005 and r>58:
        sig = "BUY CE - Only Buying"
    elif price<vwap and price<ema*0.9995 and r<42:
        sig = "BUY PE - Only Buying"
    else:
        sig = "HOLD"
    out.append(f"{name} {round(price,1)}: {sig}")

out.append("\n--- 50 STOCKS SWING Daily No Flip ---")
for name, sym in STOCKS.items():
    df = fetch(sym,"6mo","1d")
    time.sleep(0.2)
    if df is None or len(df)<25:
        out.append(f"{name}: HOLD"); continue
    c = df["close"]
    ema = c.ewm(span=20).mean().iloc[-1]
    r = rsi(c).iloc[-1]
    price = c.iloc[-1]
    if pd.isna(r) or pd.isna(ema):
        sig = "HOLD"
    elif price>ema and r>55:
        sig = "SWING CALL - Only Buying"
    elif price<ema and r<45:
        sig = "SWING PUT - Only Buying"
    else:
        sig = "HOLD"
    out.append(f"{name} {round(price,1)}: {sig}")

final = "\n".join(out)
print(final)
send_tg(final)
