import csv
import html
import json
import math
import re
import subprocess
import sys
import time
import urllib.parse
import urllib.request
from datetime import date
from pathlib import Path

from futu import *

REPORT_DATE = "2026-05-27"
ROOT = Path(__file__).resolve().parent
FUTUAPI = Path(r"C:\Users\lixiangliu\.codex\skills\futuapi\scripts")
CLAUDE = Path(r"C:\Users\lixiangliu\.claude\skills")

GROUPS = {
    "market": ["US.DIA", "US.SPY", "US.QQQ", "US.IWM", "US.SMH", "US.SOXX", "US.VXX"],
    "sectors": ["US.XLK", "US.XLC", "US.XLY", "US.XLF", "US.XLI", "US.XLV", "US.XLP", "US.XLE", "US.XLU", "US.XLB", "US.XLRE"],
    "themes": ["US.SMH", "US.SOXX", "US.IGV", "US.CIBR", "US.HACK", "US.CLOU", "US.WCLD", "US.BOTZ", "US.AIQ", "US.IWO", "US.IWN", "US.RSP", "US.SCHG", "US.VTV"],
    "mega": ["US.NVDA", "US.MSFT", "US.AAPL", "US.GOOGL", "US.AMZN", "US.META", "US.TSLA"],
    "semis": ["US.NVDA", "US.AMD", "US.AVGO", "US.MRVL", "US.MU", "US.TSM", "US.ASML", "US.ARM", "US.INTC", "US.QCOM", "US.SMCI", "US.DELL", "US.HPE", "US.ANET", "US.CLS", "US.VRT", "US.COHR", "US.LITE", "US.AAOI", "US.TSEM"],
    "software": ["US.CRM", "US.NOW", "US.SNOW", "US.ORCL", "US.ADBE", "US.PANW", "US.CRWD", "US.DDOG", "US.NET", "US.MDB", "US.PLTR", "US.APP", "US.TEAM", "US.WDAY", "US.INTU", "US.SHOP"],
    "infra": ["US.CEG", "US.VST", "US.NRG", "US.ETN", "US.PWR", "US.GEV", "US.VRT", "US.FLNC", "US.OKLO", "US.SMR", "US.BE", "US.NEE", "US.SO", "US.DUK", "US.APLD", "US.IREN", "US.CORZ"],
    "macro": ["US.GLD", "US.USO", "US.BNO", "US.UUP", "CC.BTC", "CC.ETH"],
}
ALL_CODES = []
for values in GROUPS.values():
    for code in values:
        if code not in ALL_CODES:
            ALL_CODES.append(code)

NAME = {
    "US.DIA":"Dow Jones/DIA", "US.SPY":"S&P 500/SPY", "US.QQQ":"Nasdaq 100/QQQ", "US.IWM":"Russell 2000/IWM", "US.SMH":"SOX proxy/SMH", "US.SOXX":"SOX proxy/SOXX", "US.VXX":"VIX futures/VXX",
}


def clean_json_from_output(text):
    match = re.search(r"(\{.*\})", text, flags=re.S)
    if not match:
        return None
    try:
        return json.loads(match.group(1))
    except Exception:
        return None


def pct(a, b):
    if b in (None, 0) or a is None:
        return None
    return (a / b - 1) * 100


def fmt_pct(x):
    return "暂无可靠数据" if x is None else f"{x:+.2f}%"


def fmt_num(x, decimals=2):
    if x is None:
        return "暂无可靠数据"
    return f"{x:,.{decimals}f}"


def ema(values, span):
    if not values:
        return None
    alpha = 2 / (span + 1)
    out = values[0]
    for v in values[1:]:
        out = alpha * v + (1 - alpha) * out
    return out


def calc_rsi(closes, period=14):
    if len(closes) < period + 1:
        return None
    gains, losses = [], []
    for i in range(-period, 0):
        diff = closes[i] - closes[i-1]
        gains.append(max(diff, 0))
        losses.append(max(-diff, 0))
    avg_gain = sum(gains) / period
    avg_loss = sum(losses) / period
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return 100 - 100 / (1 + rs)


def technical_state(rows):
    if not rows:
        return {}
    closes = [r["close"] for r in rows]
    last = rows[-1]
    prev = rows[-2] if len(rows) > 1 else None
    ma = {}
    for n in (20, 50, 100, 200):
        ma[n] = sum(closes[-n:]) / n if len(closes) >= n else None
    ema12 = ema(closes[-60:], 12)
    ema26 = ema(closes[-60:], 26)
    macd = None if ema12 is None or ema26 is None else ema12 - ema26
    support = min(r["low"] for r in rows[-20:]) if len(rows) >= 20 else min(r["low"] for r in rows)
    resistance = max(r["high"] for r in rows[-20:]) if len(rows) >= 20 else max(r["high"] for r in rows)
    volume_change = pct(last["volume"], prev["volume"]) if prev else None
    return {
        "date": last["time"][:10], "close": last["close"], "open": last["open"], "high": last["high"], "low": last["low"], "volume": last["volume"],
        "day_pct": pct(last["close"], prev["close"]) if prev else None,
        "5d_pct": pct(last["close"], rows[-6]["close"]) if len(rows) >= 6 else None,
        "1m_pct": pct(last["close"], rows[-22]["close"]) if len(rows) >= 22 else None,
        "vol_chg_pct": volume_change,
        "ma20": ma[20], "ma50": ma[50], "ma100": ma[100], "ma200": ma[200],
        "rsi14": calc_rsi(closes), "macd": macd, "support": support, "resistance": resistance,
        "trend": classify_trend(last["close"], ma, calc_rsi(closes), macd),
    }


def classify_trend(close, ma, rsi, macd):
    if ma.get(20) and close < ma[20]:
        base = "跌破20日线"
    elif ma.get(20) and ma.get(50) and close > ma[20] > ma[50]:
        base = "多头排列"
    elif ma.get(50) and close > ma[50]:
        base = "50日线上方"
    else:
        base = "震荡/偏弱"
    if rsi is not None and rsi > 70:
        base += "，RSI偏热"
    elif rsi is not None and rsi < 30:
        base += "，RSI超卖"
    if macd is not None:
        base += "，MACD正" if macd > 0 else "，MACD负"
    return base


def fetch_snapshots(codes):
    ctx = OpenQuoteContext(host="127.0.0.1", port=11111)
    out = {}
    bad = []
    try:
        for code in codes:
            ret, data = ctx.get_market_snapshot([code])
            if ret != RET_OK or data is None or data.empty:
                bad.append({"code": code, "error": str(data)})
                continue
            row = data.iloc[0]
            out[code] = {
                "code": row.get("code"), "name": row.get("name"), "last_price": float(row.get("last_price", 0) or 0),
                "open": float(row.get("open_price", 0) or 0), "high": float(row.get("high_price", 0) or 0),
                "low": float(row.get("low_price", 0) or 0), "prev_close": float(row.get("prev_close_price", 0) or 0),
                "volume": int(row.get("volume", 0) or 0), "turnover": float(row.get("turnover", 0) or 0),
            }
    finally:
        ctx.close()
    return out, bad


def fetch_klines(codes):
    ctx = OpenQuoteContext(host="127.0.0.1", port=11111)
    out, bad = {}, []
    try:
        for index, code in enumerate(codes, 1):
            ret, data, key = ctx.request_history_kline(code, start="2025-06-01", end=REPORT_DATE, ktype=KLType.K_DAY, autype=AuType.QFQ, max_count=300, session=Session.NONE)
            if ret != RET_OK or data is None or data.empty:
                bad.append({"code": code, "error": str(data)})
                continue
            rows = []
            for _, row in data.iterrows():
                rows.append({"time": row.get("time_key", ""), "open": float(row.get("open", 0) or 0), "high": float(row.get("high", 0) or 0), "low": float(row.get("low", 0) or 0), "close": float(row.get("close", 0) or 0), "volume": int(row.get("volume", 0) or 0)})
            out[code] = technical_state(rows)
            if index % 55 == 0:
                time.sleep(31)
            else:
                time.sleep(0.15)
    finally:
        ctx.close()
    return out, bad


def http_json(url, timeout=20):
    req = urllib.request.Request(url, headers={"User-Agent": "stock-daily-analysis/0.1"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception as exc:
        return {"error": str(exc)}


def futu_news(keyword, size=5):
    params = urllib.parse.urlencode({"keyword": keyword, "size": size, "news_type": 1, "lang": "zh-CN", "sort_type": 2})
    return http_json("https://ai-news-search.futunn.com/news_search?" + params)


def futu_feed(keyword, size=30):
    params = urllib.parse.urlencode({"keyword": keyword, "size": size})
    data = http_json("https://ai-news-search.futunn.com/stock_feed?" + params)
    posts = []
    for item in data.get("data", []) if isinstance(data, dict) else []:
        text = html.unescape(re.sub("<[^>]+>", " ", (item.get("title", "") + " " + item.get("desc", ""))))
        posts.append({"time": item.get("publish_time"), "text": " ".join(text.split())})
    return {"raw_code": data.get("code") if isinstance(data, dict) else None, "filtered_symbol_hits": [p for p in posts if keyword.upper().replace("US.", "") in p["text"].upper()][:10], "sample_count": len(posts)}


def treasury_yields():
    url = "https://home.treasury.gov/resource-center/data-chart-center/interest-rates/pages/xml?data=daily_treasury_yield_curve&field_tdr_date_value_month=202605"
    try:
        raw = urllib.request.urlopen(url, timeout=20).read().decode("utf-8")
        entries = re.findall(r"<entry>(.*?)</entry>", raw, flags=re.S)
        rows = []
        for e in entries:
            def grab(tag):
                m = re.search(fr"<d:{tag}[^>]*>(.*?)</d:{tag}>", e)
                return m.group(1) if m else None
            dt = grab("NEW_DATE")
            if dt:
                rows.append({"date": dt[:10], "2Y": float(grab("BC_2YEAR") or "nan"), "10Y": float(grab("BC_10YEAR") or "nan"), "30Y": float(grab("BC_30YEAR") or "nan")})
        rows = [r for r in rows if not math.isnan(r["2Y"])]
        return rows[-2:]
    except Exception as exc:
        return {"error": str(exc)}


def run_anomaly(kind, code):
    script = {
        "technical": CLAUDE / "futu-technical-anomaly" / "scripts" / "handle_technical_anomaly.py",
        "capital": CLAUDE / "futu-capital-anomaly" / "scripts" / "handle_capital_anomaly.py",
        "derivatives": CLAUDE / "futu-derivatives-anomaly" / "scripts" / "handle_derivatives_anomaly.py",
    }[kind]
    try:
        cp = subprocess.run([sys.executable, str(script), code, "--time-range", "7", "--language-id", "0", "--json"], capture_output=True, text=True, timeout=45, encoding="utf-8", errors="replace")
        parsed = clean_json_from_output(cp.stdout)
        if parsed:
            content = parsed.get("data", {}).get("content") or parsed.get("data", {}).get("retMsg") or ""
            return {"ok": cp.returncode == 0, "retMsg": parsed.get("data", {}).get("retMsg"), "content": content[:1800]}
        return {"ok": False, "error": (cp.stderr or cp.stdout)[-500:]}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


def main():
    print("fetching snapshots...", flush=True)
    snapshots, bad_snap = fetch_snapshots(ALL_CODES)
    valid_codes = list(snapshots.keys())
    print(f"snapshots: {len(valid_codes)} valid, {len(bad_snap)} bad", flush=True)
    print("fetching klines...", flush=True)
    klines, bad_k = fetch_klines(valid_codes)
    print(f"klines: {len(klines)} valid, {len(bad_k)} bad", flush=True)
    news_keywords = ["S&P 500", "Nvidia", "Microsoft", "Tesla", "Micron", "Federal Reserve", "Treasury yields", "AI data center", "IREN", "oil"]
    news = {}
    for kw in news_keywords:
        print(f"news: {kw}", flush=True)
        news[kw] = futu_news(kw, 5)
    feed = {}
    for sym in ["NVDA", "TSLA", "META", "LITE"]:
        print(f"feed: {sym}", flush=True)
        feed[sym] = futu_feed(sym, 30)
    anomalies = {}
    for code in ["US.NVDA", "US.AMD", "US.AVGO", "US.TSLA"]:
        anomalies[code] = {}
        for kind in ["technical", "capital", "derivatives"]:
            print(f"anomaly: {code} {kind}", flush=True)
            anomalies[code][kind] = run_anomaly(kind, code)
    result = {
        "report_date": REPORT_DATE,
        "groups": GROUPS,
        "snapshots": snapshots,
        "klines": klines,
        "bad_snapshot": bad_snap,
        "bad_kline": bad_k,
        "news": news,
        "feed": feed,
        "anomalies": anomalies,
        "treasury": treasury_yields(),
        "sources": {
            "futu": "富途 OpenAPI / Futunn",
            "futu_news": "https://ai-news-search.futunn.com/news_search",
            "futu_feed": "https://ai-news-search.futunn.com/stock_feed",
            "treasury": "https://home.treasury.gov/resource-center/data-chart-center/interest-rates/pages/xml?data=daily_treasury_yield_curve",
            "cme": "https://www.cmegroup.com/markets/interest-rates/cme-fedwatch-tool.html"
        }
    }
    out = ROOT / f"us_market_close_data_{REPORT_DATE}.json"
    out.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(out)

if __name__ == "__main__":
    main()
