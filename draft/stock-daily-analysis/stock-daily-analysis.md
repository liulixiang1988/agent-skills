生成一份中文《美股收盘日报》，标题格式为“美股收盘日报｜YYYY-MM-DD”。必须使用最新可靠数据，优先参考并标注权威来源链接，包括 CNBC、Reuters、Bloomberg、MarketWatch、WSJ、Investing、Yahoo Finance、Barchart、Koyfin、TradingView、Finviz、FactSet、Nasdaq、公司 IR 官网、SEC 文件、CME FedWatch、FRED、美国财政部、EIA 等；也可参考 SemiAnalysis、Citrini Research、https://x.com/aleabitoreddit (对https://x.com/aleabitoreddit 推荐的股票重点进行跟踪）。

## 执行要求

在开始写日报前，**先执行并使用**以下 skills，而不是只把它们当成参考名称：

- `$futuapi`
- `$futu-news-search`
- `$futu-stock-digest`
- `$futu-comment-sentiment`
- `$futu-capital-anomaly`
- `$futu-derivatives-anomaly`
- `$futu-technical-anomaly`

执行规则：

- 先判断当前会话里这些 skill 是否可用；只要可用，就必须优先调用，不要跳过。
- 若 skill 已触发但没有独立 MCP tool 暴露，不要误判为“不能用”；应按 skill 指引直接运行其本地脚本。
- `futuapi` 的本地脚本位于该 skill 目录下的 `scripts/` 子目录；需要行情/快照/K线/财报/分析师评级/期权/卖空等结构化数据时，先解析 `$futuapi` skill 的实际安装路径，再调用对应脚本。
- 如果权威媒体与 futu 结构化数据都可获得，优先用权威媒体解释事件，用 futu 数据补充行情、技术、资金、衍生品、情绪等结构化维度。
- 只有在 futu skill 不可用、脚本执行失败、或 OpenD/SDK/权限报错且无法恢复时，才允许退回纯公开网页来源；此时必须在文中明确说明缺失原因。

## 最低覆盖标准

- `先用 futu` 的目标是提高结构化数据质量，不是缩小报告覆盖面；最终日报必须同时满足本节的最低覆盖标准。
- 如果某字段在 futu 中未直接拿到，但可以通过代理 ETF、权威媒体、公司 IR、官方数据源稳定补齐，就必须补齐，而不是留空。
- 若最低覆盖标准中的某项无法补齐，必须在对应章节写明具体原因，例如：接口不支持、权限不足、公开来源无可核验数据、来源冲突无法判定。
- 不允许因为单一数据源缺失就跳过整个维度；应先尝试 futu，再尝试权威公开来源或明确标注的代理数据。

## 执行前清单

在正式写日报前，先列出并尽量一次性抓取以下 symbol/checklist；缺一项都不要提前进入写作。

### 大盘与宏观代理

- 指数/ETF：`US.DIA` `US.SPY` `US.QQQ` `US.IWM` `US.SMH`
- 波动率代理：优先 `US.^VIX`；若不可用，退回 `VIXY` 或其他明确标注的波动率代理
- 宏观代理：`US.GLD` `US.USO` `US.UUP`
- 如需要半导体补充：`US.SOXX`

### 十一个板块 ETF

- `US.XLK` `US.XLC` `US.XLY` `US.XLF` `US.XLI` `US.XLV` `US.XLP` `US.XLE` `US.XLU` `US.XLB` `US.XLRE`

### 主题与风格 ETF

- `US.SMH` `US.SOXX` `US.IGV` `US.CIBR` `US.HACK` `US.CLOU` `US.WCLD` `US.BOTZ` `US.AIQ`
- `US.IWO` `US.IWN` `US.RSP` `US.QQQ` `US.SCHG` `US.VTV`

### 七巨头

- `US.NVDA` `US.MSFT` `US.AAPL` `US.GOOGL` `US.AMZN` `US.META` `US.TSLA`

### AI 硬件 / 半导体

- `US.NVDA` `US.AMD` `US.AVGO` `US.MRVL` `US.MU` `US.TSM` `US.ASML` `US.ARM` `US.INTC` `US.QCOM` `US.SMCI` `US.DELL` `US.HPE` `US.ANET` `US.CLS` `US.VRT` `US.COHR` `US.LITE` `US.AAOI` `US.TSEM` `US.SIVE`

### 软件 / SaaS / AI 应用

- `US.CRM` `US.NOW` `US.SNOW` `US.ORCL` `US.ADBE` `US.PANW` `US.CRWD` `US.DDOG` `US.NET` `US.MDB` `US.PLTR` `US.APP` `US.TEAM` `US.WDAY` `US.INTU` `US.SHOP`

### AI 电力 / 数据中心 / 能源基础设施

- `US.CEG` `US.VST` `US.NRG` `US.ETN` `US.PWR` `US.GEV` `US.VRT` `US.FLNC` `US.OKLO` `US.SMR` `US.BE` `US.NEE` `US.SO` `US.DUK` `US.APLD` `US.IREN` `US.CORZ`

### 宽度与内部指标

- 尽量补齐：NYSE / Nasdaq 涨跌家数、涨跌比、52 周新高新低、总成交量
- 若无法从 futu 获取，允许用 Reuters、AP、TradingView、Barchart、Finviz、Yahoo Finance 等公开来源补齐

## 输出前自检

- 大盘表是否包含 `DIA/SPY/QQQ/IWM/SMH`，以及 `VIX` 或明确标注的 VIX 代理
- 板块表是否仍然是 **11 个板块 ETF**，不要混入个股替代板块
- 主题表是否覆盖 `SMH/SOXX/IGV/CIBR/HACK/CLOU/WCLD/BOTZ/AIQ/IWO/IWN/RSP/QQQ/SCHG/VTV`
- 重点关注股观察是否至少覆盖模板中列出的核心科技、软件、光通信、AI 电力基础设施名单
- 对最低覆盖标准中的空值，是否写明了无法补齐的具体原因

数据获取优先级：（1）权威财经媒体与官方数据源；（2）若公开来源缺失或需要补充结构化的行情、技术、资金、衍生品、情绪、新闻数据，必须主动使用以下 futu 相关 skill 检索（不是兜底，而是结构化数据的首选）：
- `futuapi`：指数/ETF/个股的实时行情、快照、K线、买卖盘、成交、分时；财报与财务数据；分析师评级与目标价；ETF/板块估值；分红回购；股东持股；十大经纪商；卖空；期权链与隐含波动率。
- `futu-news-search`：检索个股的最新新闻、公告、研报（默认 10 条，按时间排序，带原文链接）。
- `futu-stock-digest`：对单只股票最新公开新闻进行解读，提取关键事件并判断影响方向。
- `futu-comment-sentiment`：聚合 Futu 社区讨论，输出多空情绪分布与零售讨论热度。
- `futu-capital-anomaly`：资金分布、买卖经纪商、资金流向、卖空数量与比例的异动信号。
- `futu-derivatives-anomaly`：牛熊证街货、期权大单、IV、PCR、聪明钱信号等衍生品异动。
- `futu-technical-anomaly`：K 线形态与 MACD/RSI/KDJ/CCI/MA/BOLL 等技术指标的异动事件。

调用 futu skill 前，先把用户提到的股票名/中英文公司名/代码归一化为标准 symbol（例如 `US.NVDA`、`US.TSLA`、`HK.00700`）。多只股票或多维度（资金/技术/衍生品）需求时，并行调用对应 skill 以减少耗时。所有 futu skill 返回数据需在日报中标注“数据来源：富途 OpenAPI / Futunn”。

如果需要直接运行 `futuapi` 脚本，可优先使用这些脚本模式：

- 先定位 `$futuapi` skill 根目录，以下用 `<futuapi-skill-dir>` 表示该目录。
- 快照：`python <futuapi-skill-dir>/scripts/quote/get_snapshot.py US.NVDA US.SPY --json`
- K 线：`python <futuapi-skill-dir>/scripts/quote/get_kline.py US.SPY --ktype 1d --num 250 --json`
- 分时：`python <futuapi-skill-dir>/scripts/quote/get_rt_data.py US.SPY --json`
- 财报/财务：`python <futuapi-skill-dir>/scripts/quote/get_financials_statements.py US.NVDA --json`
- 分析师评级：`python <futuapi-skill-dir>/scripts/quote/get_research_rating_summary.py US.NVDA --json`

需要补充时优先追加这些脚本：

- 历史 K 线批量计算技术位：对 checklist 里的 ETF/个股批量调用 `get_kline.py`
- 快照补齐：对缺失的 ETF/个股继续追加 `get_snapshot.py`
- 若 `US.^VIX` 不可用，改用可交易代理并在文中注明“VIX 代理”
- 宽度与新闻补齐：若 futu 没有直接返回，使用 Reuters/AP/Barchart/Finviz/Yahoo Finance 补齐

运行前先做最小环境检查：

- `python <futuapi-skill-dir>/scripts/check_env.py`

若环境检查失败，先报错并说明原因，不要静默跳过 futu 数据。

不要编造数据；若无法获取可靠数据，明确写“暂无可靠数据”。若来源数据冲突，说明差异并优先采用更权威或更实时来源。

报告风格：专业、清晰、数据驱动，适合投资复盘和次日交易计划。目标：帮助快速理解昨夜美股发生了什么、为什么涨跌、资金在买什么卖什么、板块/个股异动、接下来风险与机会。

必须按以下结构输出：

0. 今日一句话总结：3-5 句话概括大盘涨跌/震荡、核心驱动、risk-on/risk-off、市场宽度、最值得关注主线，并给出“今日市场状态：...”一句判断。

1. 大盘表现总览：表格列 Dow Jones、S&P 500、Nasdaq Composite、Nasdaq 100/QQQ、Russell 2000/IWM、SOX 半导体指数、VIX 的收盘点位、涨跌幅、日内高低点、成交量变化、技术状态。说明标普/纳指是否创历史或阶段新高或跌破关键均线，纳指是否强于标普，小盘是否跑赢/跑输，半导体是否领先，VIX 上升/下降及避险含义。
（数据来源：可使用 `futuapi` 批量拉取 `US.DIA`、`US.SPY`、`US.QQQ`、`US.IWM`、`US.SMH`、`US.^VIX` 的实时快照、K 线、成交量。）

2. 盘中走势复盘：按时间线写盘前、开盘后、午盘、尾盘、盘后重要财报/新闻及期货/个股异动。解释核心涨跌原因，是利率、财报、AI 主线或其他驱动，是否有 sell the news、buy the dip、short squeeze、rotation。
（数据来源：可用 `futuapi` 获取 SPY/QQQ 分时数据复盘日内走势；用 `futu-news-search` 检索当日重要个股新闻；用 `futu-stock-digest` 对盘后异动个股做新闻解读。）

3. 宏观环境：
3.1 美债收益率：表格列 2Y、10Y、30Y、2Y-10Y、10Y-30Y 的最新水平、日变化、市场含义。分析 10Y 是否接近 4.5%、4.6%、4.7% 等关键压力位，长端利率对科技估值影响，曲线陡峭/扁平，债市交易逻辑。
3.2 Fed 降息预期：列 CME FedWatch 对下一次 FOMC 降息/不降息概率、年内预期降息次数、较前一日变化、Fed 官员讲话影响。
3.3 美元、黄金、原油、比特币：表格列 DXY、黄金、WTI、Brent、BTC、ETH 的最新价格、涨跌幅、含义，并解释美元、黄金、油价、加密货币所反映的风险偏好。
（数据来源：可用 `futuapi` 拉取 BTC/ETH 等加密货币行情，以及 `US.GLD`、`US.USO`、`US.UUP` 等 ETF 的快照作为美元/黄金/原油代理。）
3.4 当日重要经济数据：列 CPI/PPI/PCE/非农/初请/零售/ISM/JOLTS/消费者信心/房地产/财政部拍卖等实际值、预期值、前值、市场解读。

4. 板块表现：列 S&P 500 十一个板块：XLK、XLC、XLY、XLF、XLI、XLV、XLP、XLE、XLU、XLB、XLRE 的排名、当日涨跌幅、近5日、近1月、跑赢/跑输标普、主要驱动。说明最强/最弱板块，成长/价值、周期/防御，高切低或 AI 硬件向软件、能源、电力、光通信、工业、金融等轮动。
（数据来源：可用 `futuapi` 并行拉取 11 个板块 ETF 的快照与不同周期 K 线，计算涨跌幅与相对表现。）

5. 主题与风格表现：覆盖 SMH/SOXX、IGV、CIBR/HACK、CLOU/WCLD、BOTZ/AIQ、光通信代表股、数据中心/电力代表股、核电/SMR、储能、IWO、IWN、RSP、QQQ/SCHG、VTV 的当日涨跌幅、近5日、近1月、解读。判断 AI 硬件、软件补涨、半导体利好钝化、小盘参与、等权是否跑赢、市值权重集中度。
（数据来源：可用 `futuapi` 批量拉取上述主题 ETF 的行情与历史 K 线。）

6. 市场宽度与参与度：
6.1 均线参与度：统计 S&P 500、Nasdaq 100、Nasdaq Composite、NYSE、Russell 2000 高于 20/50/100/200 日均线比例并解读；判断过热/恐慌、50 日是否高于 50%、中期趋势、指数与参与度背离。
6.2 涨跌家数、新高新低：NYSE 与 Nasdaq 的上涨家数、下跌家数、涨跌比、52 周新高、新低、新高-新低差值并解读。
6.3 其他内部指标：尽量补充 Advance/Decline Line、McClellan Oscillator、Put/Call Ratio、VIX term structure、VVIX、MOVE、HY/IG spread、成交量、上涨/下跌成交量比例；没有可靠数据则注明。

7. 技术面分析：表格分析 SPY、QQQ、IWM、SMH、IGV、XLK、XLC、XLY 的当前价格、20/50/100/200 日线、RSI、MACD/趋势、关键支撑、关键压力。说明是否远离均线、超买/超卖、放量滞涨、假突破风险、不能跌破的位置、突破后上行空间、明日上涨确认信号和回调风险位置。
（数据来源：可用 `futuapi` 拉取日线 K 线计算均线/RSI/MACD；用 `futu-technical-anomaly` 对每个 ETF 检索当日技术指标异动事件，如金叉死叉、超买超卖、形态突破。）

8. 重点个股新闻与异动：
（数据来源：本章节涉及大量个股，建议并行调用以下 futu skill 高效采集——`futuapi` 取行情/快照/财务/分析师评级/卖空；`futu-news-search` 取最新新闻与公告；`futu-stock-digest` 做新闻事件解读；`futu-comment-sentiment` 看零售情绪；`futu-capital-anomaly` 看资金流向与经纪商行为；`futu-derivatives-anomaly` 看期权大单与 IV 异动；`futu-technical-anomaly` 看 K 线与技术指标异动。对 NVDA、AMD、AVGO、MRVL、TSM、ASML 等 AI 主线股，建议同时跑技术/资金/衍生品三个 anomaly skill。）
8.1 七巨头：NVDA、MSFT、AAPL、GOOGL、AMZN、META、TSLA 的涨跌幅、原因、技术位置、后续关注。判断七巨头集体上涨还是分化，谁拉动指数/拖累指数，监管/财报/产品/AI/反垄断/评级/目标价新闻。
8.2 AI 硬件/半导体：覆盖 NVDA、AMD、AVGO、MRVL、MU、TSM、ASML、ARM、INTC、QCOM、SMCI、DELL、HPE、ANET、CLS、VRT、COHR、LITE、AAOI、TSEM、SIVE 等，说明大涨/大跌原因、催化类型、拥挤度、sell the news、GPU 向光通信/电力/软件切换。
8.3 软件/SaaS/AI 应用：覆盖 CRM、NOW、SNOW、ORCL、ADBE、PANW、CRWD、DDOG、NET、MDB、PLTR、APP、TEAM、WDAY、INTU、SHOP 等，说明是否跑赢、AI 替代 SaaS 叙事、AI Agent/数据云/工作流催化、财报/评级/机构加仓/产品发布。
8.4 AI 电力/数据中心/能源基础设施：覆盖 CEG、VST、NRG、ETN、PWR、GEV、VRT、FLNC、OKLO、SMR、BE、NEE、SO、DUK、APLD、IREN、CORZ 等，说明数据中心电力链、核电/天然气/储能/电网设备/液冷/基础设施新闻、AI 数据中心需求重估、监管/订单/融资/并购/政策催化。
8.5 其他显著异动：列财报后大涨大跌、盘后异动、评级变动、并购、SEC 调查、管理层变动、回购/增发/二次发行、空头报告、指引变化。

9. 财报日历与财报解读：
9.1 昨夜重点已公布财报：表格列公司、收入、EPS、是否 beat、指引、盘后反应、核心解读，并分析收入/EPS/毛利率/运营利润率/FCF/RPO/ARR/订单/backlog/云收入/AI 收入/指引/股价反应与质量。
（数据来源：可用 `futuapi` 拉取财报数据（利润表/资产负债表/现金流/主营构成）；用 `futu-news-search` + `futu-stock-digest` 取财报解读新闻；用 `futu-capital-anomaly` 看财报后资金动向；用 `futu-derivatives-anomaly` 看期权 IV 是否塌缩、是否有大单押注。）
9.2 接下来 1-3 个交易日重要财报：日期、公司、市场关注点、可能影响板块。特别关注 NVDA、AVGO、AMD、MRVL、MU、TSM、ASML、CRM、NOW、SNOW、ORCL、ADBE、PANW、CRWD、GOOGL、MSFT、AMZN、META、AAPL、TSLA、VRT、ANET、DELL、SMCI、COHR、LITE、AAOI、CEG、VST、FLNC、OKLO 等。
（数据来源：可用 `futuapi` 查询财报日历与分析师预期。）

10. 机构观点与资金流：整理当天重要机构观点、策略目标点位调整、AI/半导体/软件/能源/电力/金融观点变化、重点股票评级变动、ETF 资金流、期权异动、大宗交易、内部人交易、回购公告。用表格列机构/来源、观点、涉及资产、市场影响。
（数据来源：可用 `futuapi` 拉取分析师评级与目标价、内部人交易、股东变动；用 `futu-capital-anomaly` 看资金流向与经纪商买卖；用 `futu-derivatives-anomaly` 看期权异动；用 `futu-news-search` 检索评级与机构观点新闻。）

11. 板块轮动判断：在 AI 硬件主升浪、AI 硬件高位震荡、AI 硬件利好钝化、软件补涨/估值修复、高切低、全面 risk-on、防御 risk-off、宽度扩散、指数强内部弱、普跌恐慌、超跌反弹等状态中明确判断。回答资金流入/流出、AI 主线健康度、半导体领先性、软件相对走强、小盘参与、防御异动、趋势延续或顶部震荡。

12. 我的重点关注股观察：跟踪核心科技/AI：NVDA、AMD、AVGO、MRVL、GOOGL、MSFT、META、AMZN、ORCL；软件：CRM、NOW、SNOW、ADBE、PANW、CRWD、PLTR、DDOG、NET；光通信/AI 互连：LITE、COHR、AAOI、TSEM、SIVE、MRVL、AVGO、ANET；AI 电力/数据中心基础设施：FLNC、OKLO、VST、CEG、ETN、VRT、PWR、GEV、APLD、IREN。每只输出股票、当日涨跌、当前趋势、关键新闻、支撑位、压力位、我的判断。判断标签只能使用：继续强势、高位震荡、短线过热、回踩支撑、破位风险、等财报催化、利好兑现、低位修复、需要观察。
（数据来源：对每只重点关注股，建议并行调用 `futuapi`（行情/K线/支撑压力位）+ `futu-news-search`（关键新闻）+ `futu-technical-anomaly`（技术信号）+ `futu-capital-anomaly`（资金动向）+ `futu-comment-sentiment`（社区情绪）。综合输出更立体的判断。）

13. 明日交易计划/观察清单：
13.1 宏观观察：10Y、美债关键位置、DXY、油价/黄金/VIX、Fed 讲话、经济数据。
13.2 大盘观察：SPY/QQQ 支撑压力，SMH 是否强于 QQQ，IGV 是否跑赢，IWM 是否参与。
13.3 板块观察：AI 硬件、软件、金融/工业/能源、防御、市场宽度。
13.4 个股观察：列 10-20 只明天最值得关注股票及原因。

14. 风险提示：列美债收益率上行、通胀预期反弹、降息预期下降、地缘、油价、AI sell the news、半导体拥挤、软件财报、宽度恶化、信用利差、VIX、个股财报、政策/监管、美元走强等风险。表格列风险维度、当前状态、风险等级，维度包括宏观利率、市场宽度、AI 拥挤度、财报风险、地缘风险、技术面、流动性；等级使用低/中/中高/高。

15. 最终结论：包括“今日市场结论”3-5 句话；“当前市场阶段”必须从强趋势上涨、高位震荡、健康回调、板块轮动、风险偏好下降、普跌恐慌、超跌反弹中选择一个；“我的操作倾向”用中性语言说明是否适合追高/逢低/等待财报/控制仓位、关注和谨慎板块，明确不构成投资建议；“最值得关注的 5 个信号”列明次日 5 个最重要观察信号。
