import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DATA = json.loads((ROOT / "us_market_close_data_2026-05-27.json").read_text(encoding="utf-8"))
K = DATA["klines"]
S = DATA["snapshots"]
G = DATA["groups"]
A = DATA["anomalies"]
NEWS = DATA["news"]
REPORT_DATE = DATA["report_date"]


def pct(x):
    return "暂无可靠数据" if x is None else f"{x:+.2f}%"


def num(x, n=2):
    return "暂无可靠数据" if x is None else f"{x:,.{n}f}"


def money_vol(v):
    if v is None:
        return "暂无可靠数据"
    if v >= 1_000_000_000:
        return f"{v/1_000_000_000:.2f}B"
    if v >= 1_000_000:
        return f"{v/1_000_000:.2f}M"
    return f"{v:,.0f}"


def row(code):
    return K.get(code, {})


def snap(code):
    return S.get(code, {})


def line(code):
    x = row(code)
    if not x:
        return [code, "暂无可靠数据", "暂无可靠数据", "暂无可靠数据", "暂无可靠数据", "暂无可靠数据"]
    return [code.replace("US.", ""), num(x.get("close")), pct(x.get("day_pct")), pct(x.get("5d_pct")), pct(x.get("1m_pct")), x.get("trend", "")]


def md_table(headers, rows):
    out = ["| " + " | ".join(headers) + " |", "| " + " | ".join(["---"] * len(headers)) + " |"]
    for r in rows:
        out.append("| " + " | ".join(str(c).replace("\n", "<br>") for c in r) + " |")
    return "\n".join(out)


def news_items(keyword, n=3):
    data = NEWS.get(keyword, {}).get("data", [])[:n]
    parts = []
    for item in data:
        title = item.get("title", "").replace("<em>", "").replace("</em>", "")
        url = item.get("url", "")
        parts.append(f"[{title}]({url})")
    return "；".join(parts) if parts else "暂无可靠数据"


def top_bottom(codes, top=True, n=6):
    vals = [(c, row(c).get("day_pct")) for c in codes if c in K and row(c).get("day_pct") is not None]
    vals.sort(key=lambda x: x[1], reverse=top)
    return vals[:n]


def watch_label(code):
    x = row(code)
    if not x:
        return "需要观察"
    p = x.get("day_pct") or 0
    rsi = x.get("rsi14") or 50
    trend = x.get("trend", "")
    if rsi >= 75:
        return "短线过热"
    if "跌破20日线" in trend and p < -1:
        return "破位风险"
    if "跌破20日线" in trend:
        return "回踩支撑"
    if p >= 3 and "多头" in trend:
        return "继续强势"
    if p <= -2 and "多头" in trend:
        return "高位震荡"
    if "MACD负" in trend:
        return "需要观察"
    return "继续强势" if "多头" in trend else "需要观察"


def stock_row(code, note=""):
    x = row(code)
    if not x:
        return [code.replace("US.", ""), "暂无可靠数据", "暂无可靠数据", "暂无可靠数据", "暂无可靠数据", "暂无可靠数据", "需要观察"]
    return [
        code.replace("US.", ""), pct(x.get("day_pct")), x.get("trend", ""), note or "暂无可靠个股新闻", num(x.get("support")), num(x.get("resistance")), watch_label(code)
    ]


def group_perf_table(codes, include_trend=True):
    rows = []
    for c in codes:
        x = row(c)
        if not x:
            rows.append([c.replace("US.", ""), "暂无可靠数据", "暂无可靠数据", "暂无可靠数据", "暂无可靠数据"] + (["暂无可靠数据"] if include_trend else []))
        else:
            rows.append([c.replace("US.", ""), pct(x.get("day_pct")), pct(x.get("5d_pct")), pct(x.get("1m_pct")), num(x.get("close"))] + ([x.get("trend", "")] if include_trend else []))
    return rows

sector_rows = sorted(group_perf_table(G["sectors"]), key=lambda r: float(r[1].replace('%','').replace('+','')) if r[1] != '暂无可靠数据' else -999, reverse=True)
theme_rows = group_perf_table(G["themes"])

market_rows = []
market_map = [
    ("Dow Jones", "US.DIA", "DIA ETF代理"),
    ("S&P 500", "US.SPY", "SPY ETF代理"),
    ("Nasdaq Composite", "US.QQQ", "QQQ代理，非综合指数"),
    ("Nasdaq 100/QQQ", "US.QQQ", "QQQ"),
    ("Russell 2000/IWM", "US.IWM", "IWM"),
    ("SOX半导体", "US.SMH", "SMH/SOXX代理"),
    ("VIX", "US.VXX", "VXX期货ETN代理"),
]
for name, code, note in market_map:
    x = row(code)
    if x:
        market_rows.append([name, num(x.get("close")), pct(x.get("day_pct")), f"{num(x.get('high'))}/{num(x.get('low'))}", pct(x.get("vol_chg_pct")), x.get("trend", ""), note])
    else:
        market_rows.append([name, "暂无可靠数据", "暂无可靠数据", "暂无可靠数据", "暂无可靠数据", "暂无可靠数据", note])

treas = DATA.get("treasury", [])
if isinstance(treas, list) and len(treas) >= 2:
    prev, cur = treas[-2], treas[-1]
    tsy_rows = [
        ["2Y", f"{cur['2Y']:.2f}%", f"{(cur['2Y']-prev['2Y'])*100:+.0f}bp", "短端小幅回落，降息预期未进一步恶化"],
        ["10Y", f"{cur['10Y']:.2f}%", f"{(cur['10Y']-prev['10Y'])*100:+.0f}bp", "低于4.5%，科技估值压力边际缓和"],
        ["30Y", f"{cur['30Y']:.2f}%", f"{(cur['30Y']-prev['30Y'])*100:+.0f}bp", "长端仍在5%附近，期限溢价风险未消失"],
        ["2Y-10Y", f"{cur['2Y']-cur['10Y']:+.2f}%", f"{((cur['2Y']-cur['10Y'])-(prev['2Y']-prev['10Y']))*100:+.0f}bp", "倒挂略收敛"],
        ["10Y-30Y", f"{cur['30Y']-cur['10Y']:+.2f}%", f"{((cur['30Y']-cur['10Y'])-(prev['30Y']-prev['10Y']))*100:+.0f}bp", "长端曲线基本稳定"],
    ]
else:
    tsy_rows = [["2Y/10Y/30Y", "暂无可靠数据", "暂无可靠数据", "美国财政部接口未返回有效数据"]]

macro_rows = []
for label, code, meaning in [
    ("DXY代理", "US.UUP", "美元持平偏强，风险资产未获得额外美元宽松助力"),
    ("黄金代理", "US.GLD", "黄金回落且RSI超卖，避险需求降温但也可能接近短线修复区"),
    ("WTI代理", "US.USO", "油价代理大跌，地缘新闻未转化为油价上行"),
    ("Brent代理", "US.BNO", "布油代理同步走弱"),
    ("BTC", "CC.BTC", "加密资产小涨但仍低于20日线"),
    ("ETH", "CC.ETH", "ETH小涨，趋势仍偏修复"),
]:
    x = row(code)
    macro_rows.append([label, num(x.get("close")) if x else "暂无可靠数据", pct(x.get("day_pct")) if x else "暂无可靠数据", meaning])

tech_rows = []
for c in ["US.SPY", "US.QQQ", "US.IWM", "US.SMH", "US.IGV", "US.XLK", "US.XLC", "US.XLY"]:
    x = row(c)
    tech_rows.append([c.replace("US.", ""), num(x.get("close")), num(x.get("ma20")), num(x.get("ma50")), num(x.get("ma100")), num(x.get("ma200")), num(x.get("rsi14"),1), "正" if (x.get("macd") or 0) > 0 else "负", num(x.get("support")), num(x.get("resistance"))])

mega_notes = {
    "US.NVDA": "绩后连跌四日；期权成交活跃",
    "US.MSFT": "美国国防部97亿美元企业软件合同",
    "US.AAPL": "延续强势，RSI显著偏热",
    "US.GOOGL": "横盘偏弱，跌破20日线",
    "US.AMZN": "领涨七巨头之一",
    "US.META": "大涨修复，仍低于1月趋势高点区",
    "US.TSLA": "SpaceX合并传闻与期权活跃；技术过热信号并存",
}
mega_rows = [stock_row(c, mega_notes.get(c, "")) for c in G["mega"]]

watch_codes = ["US.NVDA","US.AMD","US.AVGO","US.MRVL","US.GOOGL","US.MSFT","US.META","US.AMZN","US.ORCL","US.CRM","US.NOW","US.SNOW","US.ADBE","US.PANW","US.CRWD","US.PLTR","US.DDOG","US.NET","US.LITE","US.COHR","US.AAOI","US.TSEM","US.AVGO","US.ANET","US.FLNC","US.OKLO","US.VST","US.CEG","US.ETN","US.VRT","US.PWR","US.GEV","US.APLD","US.IREN"]
seen=[]
watch_rows=[]
for c in watch_codes:
    if c not in seen:
        seen.append(c)
        watch_rows.append(stock_row(c))
watch_rows.append(["SIVE", "暂无可靠数据", "暂无可靠数据", "Futu 未返回可确认标的；可能代码不标准", "暂无可靠数据", "暂无可靠数据", "需要观察"])

semi_top = ", ".join([f"{c.replace('US.','')} {v:+.2f}%" for c,v in top_bottom(G['semis'], True, 5)])
semi_bottom = ", ".join([f"{c.replace('US.','')} {v:+.2f}%" for c,v in top_bottom(G['semis'], False, 5)])
soft_top = ", ".join([f"{c.replace('US.','')} {v:+.2f}%" for c,v in top_bottom(G['software'], True, 5)])
infra_top = ", ".join([f"{c.replace('US.','')} {v:+.2f}%" for c,v in top_bottom(G['infra'], True, 5)])

nvda_anom = A.get("US.NVDA", {})
amd_anom = A.get("US.AMD", {})
avgo_anom = A.get("US.AVGO", {})
tsla_anom = A.get("US.TSLA", {})

content = f"""# 美股收盘日报｜{REPORT_DATE}

数据口径说明：本报告已执行并使用 Futu 相关 skill：`futuapi` 环境检查通过，使用富途 OpenAPI/Futunn 拉取 ETF、个股、K线、技术指标、评级与异常检测；使用 `futu-news-search`/`futu-stock-digest` 的新闻搜索接口提取事件；使用 `futu-comment-sentiment` 的社区接口但按股票过滤后样本为0，故社区情绪标注为“暂无可靠数据”；使用 `futu-capital-anomaly`、`futu-derivatives-anomaly`、`futu-technical-anomaly` 检测 NVDA、AMD、AVGO、TSLA。Futu 对美股正式指数点位返回“不支持美股指数”，Yahoo Finance 被限流，CNBC/Reuters/MarketWatch 页面返回403/401，因此正式指数点位与精确市场宽度若无可靠机器可读数据则明确标注；大盘表现使用 DIA/SPY/QQQ/IWM/SMH/SOXX/VXX 等 ETF/ETN 代理。数据来源：富途 OpenAPI / Futunn、美国财政部收益率曲线、Futu 新闻搜索；收益率源：https://home.treasury.gov/resource-center/data-chart-center/interest-rates/pages/xml?data=daily_treasury_yield_curve 。

## 0. 今日一句话总结

美股 5月27日整体是“指数高位窄幅震荡，AI硬件分化降温，风险偏好仍未明显转弱”的交易日。SPY 基本收平，QQQ 小跌，DIA 小涨，IWM 小跌但近5日仍明显跑赢，说明市场并非单边 risk-off，而是高位获利了结和板块轮动并存。半导体 ETF 当日回落，但 5日和1月涨幅仍最强，AI 主线没有破坏，只是从“全线追涨”转入“拥挤交易消化”。今日市场状态：高位震荡中的板块轮动，追高胜率下降，低吸和等待确认更重要。

## 1. 大盘表现总览

{md_table(['指数/代理', '收盘/代理价格', '涨跌幅', '日内高/低', '成交量变化', '技术状态', '说明'], market_rows)}

SPY 收于 750.46，日跌 0.02%，QQQ 跌 0.11%，纳指代理没有继续显著跑赢标普；IWM 跌 0.05%，但近5日涨 6.36%，仍显示小盘近期参与度改善。SMH 跌 1.10%、SOXX 跌 1.07%，半导体从前几日强势中回吐，但近1月仍分别上涨 17.63% 与 23.84%。VXX 跌 2.42%，避险波动率代理继续走低，市场没有进入恐慌。

## 2. 盘中走势复盘

- 盘前：Futu 新闻显示三大股指期货偏弱，纳指100期货小跌；美国财政部数据中 10Y 从 4.50% 回落到 4.48%，利率压力边际缓和，但不足以推动指数大幅上攻。
- 开盘后：科技与半导体出现分化，NVDA、AMD、MRVL、ARM、QCOM 等回调，AAPL、AMZN、META、TSLA 承接指数。
- 午盘：资金从最拥挤的半导体和网络安全 ETF 中获利，CIBR/HACK/CLOU/WCLD 回落；IWM、IWO/IWN 与 RSP 维持相对韧性。
- 尾盘：SPY/QQQ 收在接近日内低位但未明显破坏趋势，VXX 下行显示尾盘避险需求不强。
- 盘后/新闻：Futu 新闻显示 MSFT 获美国国防部 97亿美元企业软件合同；NVDA 绩后连跌四日且期权成交活跃；IREN 因 16亿美元 Blackwell 系统扩张承诺大涨。

来源摘录：{news_items('Nvidia', 3)}；{news_items('Microsoft', 2)}；{news_items('IREN', 2)}。

## 3. 宏观环境

### 3.1 美债收益率

{md_table(['期限/曲线', '最新水平', '日变化', '市场含义'], tsy_rows)}

10Y 回到 4.48%，略低于 4.5% 压力位，对成长股估值是边际缓和；但 30Y 仍在 5%附近，说明长期期限溢价和财政供给压力没有消失。曲线仍倒挂，市场仍在“软着陆/再通胀/财政风险”之间反复定价。

### 3.2 Fed 降息预期

CME FedWatch 公共页面为 https://www.cmegroup.com/markets/interest-rates/cme-fedwatch-tool.html ，本次未获得可机器读取的概率数据，因此下一次 FOMC 降息/不降息概率与年内降息次数写为“暂无可靠数据”。Futu 新闻显示美联储副主席 Jefferson 强调在劳动力市场韧性下仍应关注将通胀恢复至2%，并称 AI 投资支持增长，这对降息交易不是明确鸽派信号。

### 3.3 美元、黄金、原油、比特币

{md_table(['资产', '最新价格/代理', '涨跌幅', '含义'], macro_rows)}

美元代理 UUP 持平，黄金代理 GLD 下跌且 RSI 超卖，油价代理 USO/BNO 大跌；这组组合更像“通胀/地缘溢价回落”而不是风险恐慌。BTC/ETH 小涨但仍在20日线下方，风险偏好温和，不是全面投机升温。

### 3.4 当日重要经济数据

本次可验证数据源未返回 CPI/PPI/PCE/非农/ISM/JOLTS 等顶级经济数据的当日实际值、预期值、前值；因此该项标注为暂无可靠数据。可确认的宏观事件是美国财政部收益率曲线更新和 Fed 官员讲话。

## 4. 板块表现

{md_table(['板块ETF', '当日', '近5日', '近1月', '收盘', '技术状态'], sector_rows)}

最强板块是 XLY（+1.76%）和 XLP（+1.14%），XLC 小涨，说明消费和部分通讯服务承接了指数；最弱是 XLE（-1.49%）、XLF（-0.83%）、XLK（-0.38%）。XLK 近1月 +14.86%、RSI 70.9，科技仍是中期主线但短线偏热。能源在油价代理下跌背景下领跌，金融则受到收益率曲线和风险偏好分化影响。

## 5. 主题与风格表现

{md_table(['主题/风格ETF', '当日', '近5日', '近1月', '收盘', '技术状态'], theme_rows)}

AI 硬件主题没有失守：SMH/SOXX 当日回调但近5日仍强；AIQ 仅小跌且近1月 +17.55%。网络安全和云软件短线降温，CIBR -2.89%、HACK -3.80%、CLOU -2.88%、WCLD -2.35%，更像高位获利了结。小盘成长 IWO +0.05%、小盘价值 IWN +0.06%，等权 RSP -0.07%，说明市场宽度没有显著恶化；但市值权重的 AI 硬件动能开始钝化。

## 6. 市场宽度与参与度

### 6.1 均线参与度

S&P 500、Nasdaq 100、Nasdaq Composite、NYSE、Russell 2000 高于 20/50/100/200 日均线比例未能从可用数据源取得可靠成分股级数据，标注为暂无可靠数据。代理观察：SPY/QQQ/IWM/RSP 均仍在多头技术结构，IWM 近5日跑赢，说明宽度没有明显塌缩。

### 6.2 涨跌家数、新高新低

NYSE/Nasdaq 上涨家数、下跌家数、52周新高新低未从权威机器可读源取得，标注为暂无可靠数据。可替代信号：RSP 仅 -0.07%，IWM 近5日 +6.36%，不支持“指数强、内部全面弱”的极端判断。

### 6.3 其他内部指标

Put/Call Ratio、VIX term structure、VVIX、MOVE、HY/IG spread 暂无可靠数据。VXX 当日 -2.42%，波动率代理继续下行；NVDA 期权 Put/Call 成交量比据 Futu 异常检测降至 0.4、低于近一年94%的交易日，显示其个股期权情绪偏乐观，但也提示拥挤风险。

## 7. 技术面分析

{md_table(['标的', '收盘', 'MA20', 'MA50', 'MA100', 'MA200', 'RSI14', 'MACD', '20日支撑', '20日压力'], tech_rows)}

SPY/QQQ/IWM/SMH 仍保持多头结构，QQQ RSI 69.7 接近偏热；XLK RSI 70.9 已偏热。SMH 当日跌破短线动能但仍高于均线，关键是后续能否守住 20日支撑区。IGV 仍多头但当日 -1.07%，软件补涨并非全面接棒；XLC 跌破20日线，通讯服务内部仍分化。

Futu 技术异动：NVDA 5/27 收盘跌破 MA20，BOLL 低于中轨，同时 RSI(6)/CCI/WMSR 进入超卖；AMD 5/26 KDJ 强超买但 MACD 金叉、MA5 上穿 MA10；AVGO 5/27 PSY 转超卖，5/21 MA5 下穿 MA10/MA20；TSLA CCI/AR/BR/WMSR 超买但 MACD 金叉。

## 8. 重点个股新闻与异动

### 8.1 七巨头

{md_table(['股票', '当日涨跌', '趋势', '关键新闻', '支撑位', '压力位', '判断'], mega_rows)}

七巨头分化明显：META、AMZN、TSLA、AAPL 拉动指数，NVDA/MSFT/GOOGL 偏弱。NVDA 绩后连跌四日，是半导体当日降温的核心；MSFT 有国防部合同利好但股价仍跌，说明大型软件/云龙头短线资金仍在轮动。

### 8.2 AI 硬件/半导体

半导体涨幅前列：{semi_top}。跌幅前列：{semi_bottom}。MU +3.63% 再创新高，SMCI +2.94%、TSM +2.52% 仍强；QCOM -6.20%、ARM -5.76%、MRVL -4.59%、TSEM -3.72% 显示拥挤交易降温。Futu 衍生品异常显示 NVDA 仍有大额看涨期权交易，同时看涨/看跌比极低，情绪偏乐观但也偏拥挤。

### 8.3 软件/SaaS/AI 应用

软件强弱分化：{soft_top}。APP +10.42%、TEAM +4.89%、NOW +2.20% 领涨；MDB、NET、CRWD、PANW、PLTR 等回调明显。网络安全和云 ETF 当日普跌，说明软件补涨不是全线扩散，而是集中在个别高动量或事件驱动标的。

### 8.4 AI 电力/数据中心/能源基础设施

电力/数据中心涨幅前列：{infra_top}。IREN +13.48%、APLD +8.51%、CORZ +3.15% 强势，说明资金仍在追逐 AI 算力基础设施和数据中心供给链。传统电力链 CEG、GEV、VST、NRG 当日回落，说明“AI电力”也在内部高低切换：更强的是数据中心/算力托管，弱的是前期高位公用事业和电网设备。

### 8.5 其他显著异动

Futu 新闻显示 IREN 因 16亿美元 Blackwell 系统扩张承诺大涨；油价相关新闻围绕霍尔木兹海峡和美国油轮事件，但 USO/BNO 仍大跌，说明市场暂未给出持续地缘风险溢价。暂无可靠 SEC 调查、管理层变动、回购/增发或空头报告数据。

## 9. 财报日历与财报解读

### 9.1 昨夜重点已公布财报

{md_table(['公司/事件', '收入', 'EPS', '是否beat', '指引', '盘后/当日反应', '核心解读'], [
    ['NVDA', '暂无可靠结构化财报数据', '暂无可靠结构化财报数据', '暂无可靠数据', '暂无可靠数据', '当日 -1.05%，Futu 新闻称绩后连跌四日', '利好兑现与拥挤交易消化并存'],
    ['MU', '暂无可靠结构化财报数据', '暂无可靠结构化财报数据', '暂无可靠数据', '暂无可靠数据', '当日 +3.63%，Futu 新闻称再创新高', 'AI存储链资金继续追逐'],
    ['IREN', '暂无可靠结构化财报数据', '暂无可靠结构化财报数据', '暂无可靠数据', '暂无可靠数据', '当日 +13.48%', '16亿美元 Blackwell 系统扩张承诺触发算力基础设施重估'],
])}

本次未获得可核验的收入、EPS、指引结构化财报表，故不编造。Futu 新闻与行情足以确认的事件是 NVDA 绩后走弱、MU 强势、IREN 因 Blackwell 系统扩张消息大涨。

### 9.2 接下来 1-3 个交易日重要财报

可用脚本未返回可靠财报日历，标注为暂无可靠数据。观察名单仍以 NVDA/AVGO/AMD/MRVL/MU/TSM/ASML、CRM/NOW/SNOW/ORCL/ADBE/PANW/CRWD、VRT/ANET/DELL/SMCI/COHR/LITE/AAOI、CEG/VST/FLNC/OKLO 为主。

## 10. 机构观点与资金流

{md_table(['来源/机构', '观点', '涉及资产', '市场影响'], [
    ['Tigress Financial / Futu OpenAPI-TipRanks', 'NVDA Buy，目标价 425，上调自 360', 'NVDA', '基本面机构观点仍强，但股价短线利好兑现'],
    ['Morgan Stanley / Futu OpenAPI-TipRanks', 'MSFT Buy，目标价 650', 'MSFT', 'AI/云长期叙事仍获机构支持'],
    ['Piper Sandler / Futu OpenAPI-TipRanks', 'TSLA Buy，目标价 500；但 Erste 为 Sell、DBS 为 Hold', 'TSLA', '特斯拉分歧大，短线受传闻与期权推动'],
    ['Goldman/Rosenblatt/UBS / Futu OpenAPI-TipRanks', 'AVGO 多家 Buy，目标价约 490-500', 'AVGO', '定制硅/AI连接链仍获机构支撑'],
    ['Futu capital anomaly', 'AVGO 5/27 特大单净流出1548.04万，小单净流入419.49万', 'AVGO', '大资金与小资金分歧'],
    ['Futu derivatives anomaly', 'NVDA/AVGO/TSLA 均出现期权大单；TSLA 有远期高行权价看涨大单', 'NVDA/AVGO/TSLA', '期权市场情绪偏热，需防波动放大'],
])}

ETF 资金流、内部人交易、大宗交易、回购公告本次暂无可靠数据。

## 11. 板块轮动判断

当前状态选择：AI硬件高位震荡 + 软件/小盘局部补涨 + 数据中心基础设施继续活跃。资金没有明显从 AI 主线撤离，但半导体最拥挤部分开始消化，软件和小盘参与度改善，数据中心/算力基础设施继续吸引资金。防御并未全面走强，VXX 下行也不支持 risk-off；更准确的判断是“强趋势后的高位轮动”，不是普跌恐慌。

## 12. 我的重点关注股观察

{md_table(['股票', '当日涨跌', '当前趋势', '关键新闻', '支撑位', '压力位', '判断'], watch_rows)}

数据来源：富途 OpenAPI / Futunn。支撑/压力为近20个交易日低点/高点的机械参考，不构成交易建议。

## 13. 明日交易计划/观察清单

### 13.1 宏观观察

重点看 10Y 能否继续低于 4.5%；若重新上穿 4.5%-4.6%，QQQ/SMH 的估值压力会回升。同步观察 UUP 是否继续偏强、USO/BNO 是否止跌、GLD 是否从超卖反弹，以及 VXX 是否从低位反抽。

### 13.2 大盘观察

SPY 支撑参考 {num(row('US.SPY').get('support'))}、压力 {num(row('US.SPY').get('resistance'))}；QQQ 支撑 {num(row('US.QQQ').get('support'))}、压力 {num(row('US.QQQ').get('resistance'))}。明日确认信号是 QQQ 重新跑赢 SPY、SMH 止跌跑赢 QQQ、IGV 不再被抛售、IWM 继续守住近5日强势。

### 13.3 板块观察

AI硬件看 NVDA/AMD/MRVL/ARM 是否止跌；软件看 NOW/APP/SNOW 与 PANW/CRWD/NET 是否分化收敛；数据中心看 IREN/APLD/CORZ 是否延续强势，以及 CEG/VST/GEV 是否企稳；防御看 XLP/XLV 是否继续跑赢。

### 13.4 个股观察

明日重点：NVDA（MA20与期权拥挤）、AMD（高位但动能强）、MRVL（大跌后支撑）、MU（强趋势是否延续）、TSM（是否继续强于SMH）、MSFT（合同利好是否被资金认可）、AMZN/META（七巨头领涨延续）、APP/NOW/SNOW（软件相对强弱）、PANW/CRWD/NET（网络安全高位回撤）、IREN/APLD/CORZ（数据中心热度）、VST/CEG/GEV（电力链能否修复）、TSLA（过热与传闻驱动）。

## 14. 风险提示

{md_table(['风险维度', '当前状态', '风险等级'], [
    ['宏观利率', '10Y 4.48%，低于4.5%但长端30Y仍约5.01%', '中'],
    ['市场宽度', 'RSP/IWM未明显破坏，但精确涨跌家数暂无可靠数据', '中'],
    ['AI拥挤度', 'SMH/SOXX近1月大涨，NVDA期权情绪偏乐观', '中高'],
    ['财报风险', 'NVDA绩后连跌四日，后续财报若sell the news会放大波动', '中高'],
    ['地缘风险', '油价代理大跌但霍尔木兹相关新闻仍需观察', '中'],
    ['技术面', 'XLK/CIBR/HACK等RSI偏热，部分软件高位回撤', '中高'],
    ['流动性/波动率', 'VXX低位下行，若反抽可能触发高beta回撤', '中'],
])}

## 15. 最终结论

今日市场结论：指数处在高位震荡，不是系统性 risk-off；AI硬件仍是中期主线但短线拥挤，资金开始在软件、小盘、数据中心基础设施之间寻找替代弹性。半导体当日回调主要是获利了结和利好兑现，尚未看到趋势级破坏；但 NVDA 跌破20日线需要明日确认。当前市场阶段：高位震荡。我的操作倾向：不适合无差别追高，更适合等待强势股回踩确认、选择仍有相对强度且未过热的分支，同时控制半导体和高RSI软件仓位；以上不构成投资建议。

最值得关注的 5 个信号：
1. 10Y 是否继续低于 4.5%。
2. SMH/SOXX 是否止跌并重新跑赢 QQQ。
3. NVDA 是否收回 MA20，或跌破后带动 AI 硬件二次回撤。
4. IWM/RSP 是否继续显示宽度扩散。
5. IREN/APLD/CORZ 与 CEG/VST/GEV 的分化是否继续，判断 AI基础设施轮动是否健康。
"""

out = ROOT / f"us_market_close_daily_{REPORT_DATE}.md"
out.write_text(content, encoding="utf-8")
print(out)
