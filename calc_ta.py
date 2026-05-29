import json, subprocess, os, sys
SCRIPT = r'C:\Users\lixiangliu\.codex\skills\futuapi\scripts\quote\get_kline.py'
def fetch(sym):
    r = subprocess.run(['python', SCRIPT, sym, '--ktype', '1d', '--num', '220', '--json'], capture_output=True, text=True)
    all_lines = (r.stdout + '\n' + r.stderr).splitlines()
    for line in all_lines:
        s = line.strip()
        if s.startswith('{') and '"data"' in s and '"code"' in s:
            try:
                return json.loads(s)
            except: pass
    return None
def ma(arr, n):
    return sum(arr[-n:])/n if len(arr)>=n else None
def rsi(closes, n=14):
    if len(closes)<n+1: return None
    gains=losses=0.0
    for i in range(-n,0):
        d=closes[i]-closes[i-1]
        if d>=0: gains+=d
        else: losses-=d
    if losses==0: return 100.0
    rs=gains/losses
    return 100-100/(1+rs)
def ema(closes,n):
    if len(closes)<n: return None
    k=2/(n+1)
    e=sum(closes[:n])/n
    for c in closes[n:]:
        e=c*k+e*(1-k)
    return e
def macd(closes):
    e12=ema(closes,12); e26=ema(closes,26)
    if e12 is None or e26 is None: return None
    return e12-e26
syms = sys.argv[1:]
for sym in syms:
    d=fetch(sym)
    if not d:
        print(f"{sym}: NO_DATA"); continue
    cs=[x['close'] for x in d['data']]
    vols=[x['volume'] for x in d['data']]
    last=cs[-1]; prev=cs[-2]
    chg=(last-prev)/prev*100
    avgv20=sum(vols[-21:-1])/20 if len(vols)>=21 else None
    vol_ratio = vols[-1]/avgv20 if avgv20 else None
    m20=ma(cs,20) or 0; m50=ma(cs,50) or 0; m100=ma(cs,100) or 0; m200=ma(cs,200) or 0
    r=rsi(cs) or 0
    mline=macd(cs) or 0
    vr = f"{vol_ratio:.2f}x" if vol_ratio else "N/A"
    print(f"{sym}: last={last:.2f} chg={chg:+.2f}% volR={vr} MA20={m20:.2f} MA50={m50:.2f} MA100={m100:.2f} MA200={m200:.2f} RSI14={r:.1f} MACD={mline:.2f}")
