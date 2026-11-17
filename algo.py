
import requests, pandas as pd
from urllib.parse import quote

def ema(s,p):
    return s.ewm(span=p, adjust=False).mean()

def rsi_calc(s,p=14):
    d=s.diff()
    up=(d.where(d>0,0)).rolling(p).mean()
    dn=(-d.where(d<0,0)).rolling(p).mean()
    return 100-(100/(1+up/dn))

def get_intraday(key):
    ek = quote(key, safe='')
    url = f"https://api.upstox.com/v2/historical-candle/intraday/{ek}/5minute"
    r = requests.get(url, timeout=15).json()
    df = pd.DataFrame(r['data']['candles'], columns=['ts','open','high','low','close','volume','oi'])
    return df.sort_values('ts').reset_index(drop=True)

df = get_intraday("NSE_INDEX|Nifty 50")
df['ema20']=ema(df['close'],20)
df['rsi']=rsi_calc(df['close'],14)
df['vwap']=((df['high']+df['low']+df['close'])/3*df['volume']).cumsum()/df['volume'].cumsum()
l=df.iloc[-1]
print(f"NIFTY {l['close']} RSI:{round(l['rsi'],1)} VWAP:{round(l['vwap'],1)}")
if l['close']>l['vwap'] and l['rsi']>55:
    print(">>> SIGNAL: BUY NIFTY ATM CE - Only Buying")
elif l['close']<l['vwap'] and l['rsi']<45:
    print(">>> SIGNAL: BUY NIFTY ATM PE - Only Buying")
else:
    print(">>> HOLD")
