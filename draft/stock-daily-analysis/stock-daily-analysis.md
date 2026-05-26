生成一份中文《美股收盘日报》，标题格式为“美股收盘日报｜YYYY-MM-DD”。必须使用最新可靠数据，优先参考并标注权威来源链接，包括 CNBC、Reuters、Bloomberg、MarketWatch、WSJ、Investing、Yahoo Finance、Barchart、Koyfin、TradingView、Finviz、FactSet、Nasdaq、公司 IR 官网、SEC 文件、CME FedWatch、FRED、美国财政部、EIA 等；也可参考 SemiAnalysis、Citrini Research、https://x.com/aleabitoreddit (对https://x.com/aleabitoreddit 推荐的股票重点进行跟踪）。如果数据还是找不到，尝试使用 futu 相关的 skills 进行检索。不要编造数据；若无法获取可靠数据，明确写“暂无可靠数据”。若来源数据冲突，说明差异并优先采用更权威或更实时来源。

报告风格：专业、清晰、数据驱动，适合投资复盘和次日交易计划。目标：帮助快速理解昨夜美股发生了什么、为什么涨跌、资金在买什么卖什么、板块/个股异动、接下来风险与机会。

必须按以下结构输出：

0. 今日一句话总结：3-5 句话概括大盘涨跌/震荡、核心驱动、risk-on/risk-off、市场宽度、最值得关注主线，并给出“今日市场状态：...”一句判断。

1. 大盘表现总览：表格列 Dow Jones、S&P 500、Nasdaq Composite、Nasdaq 100/QQQ、Russell 2000/IWM、SOX 半导体指数、VIX 的收盘点位、涨跌幅、日内高低点、成交量变化、技术状态。说明标普/纳指是否创历史或阶段新高或跌破关键均线，纳指是否强于标普，小盘是否跑赢/跑输，半导体是否领先，VIX 上升/下降及避险含义。

2. 盘中走势复盘：按时间线写盘前、开盘后、午盘、尾盘、盘后重要财报/新闻及期货/个股异动。解释核心涨跌原因，是利率、财报、AI 主线或其他驱动，是否有 sell the news、buy the dip、short squeeze、rotation。

3. 宏观环境：
3.1 美债收益率：表格列 2Y、10Y、30Y、2Y-10Y、10Y-30Y 的最新水平、日变化、市场含义。分析 10Y 是否接近 4.5%、4.6%、4.7% 等关键压力位，长端利率对科技估值影响，曲线陡峭/扁平，债市交易逻辑。
3.2 Fed 降息预期：列 CME FedWatch 对下一次 FOMC 降息/不降息概率、年内预期降息次数、较前一日变化、Fed 官员讲话影响。
3.3 美元、黄金、原油、比特币：表格列 DXY、黄金、WTI、Brent、BTC、ETH 的最新价格、涨跌幅、含义，并解释美元、黄金、油价、加密货币所反映的风险偏好。
3.4 当日重要经济数据：列 CPI/PPI/PCE/非农/初请/零售/ISM/JOLTS/消费者信心/房地产/财政部拍卖等实际值、预期值、前值、市场解读。

4. 板块表现：列 S&P 500 十一个板块：XLK、XLC、XLY、XLF、XLI、XLV、XLP、XLE、XLU、XLB、XLRE 的排名、当日涨跌幅、近5日、近1月、跑赢/跑输标普、主要驱动。说明最强/最弱板块，成长/价值、周期/防御，高切低或 AI 硬件向软件、能源、电力、光通信、工业、金融等轮动。

5. 主题与风格表现：覆盖 SMH/SOXX、IGV、CIBR/HACK、CLOU/WCLD、BOTZ/AIQ、光通信代表股、数据中心/电力代表股、核电/SMR、储能、IWO、IWN、RSP、QQQ/SCHG、VTV 的当日涨跌幅、近5日、近1月、解读。判断 AI 硬件、软件补涨、半导体利好钝化、小盘参与、等权是否跑赢、市值权重集中度。

6. 市场宽度与参与度：
6.1 均线参与度：统计 S&P 500、Nasdaq 100、Nasdaq Composite、NYSE、Russell 2000 高于 20/50/100/200 日均线比例并解读；判断过热/恐慌、50 日是否高于 50%、中期趋势、指数与参与度背离。
6.2 涨跌家数、新高新低：NYSE 与 Nasdaq 的上涨家数、下跌家数、涨跌比、52 周新高、新低、新高-新低差值并解读。
6.3 其他内部指标：尽量补充 Advance/Decline Line、McClellan Oscillator、Put/Call Ratio、VIX term structure、VVIX、MOVE、HY/IG spread、成交量、上涨/下跌成交量比例；没有可靠数据则注明。

7. 技术面分析：表格分析 SPY、QQQ、IWM、SMH、IGV、XLK、XLC、XLY 的当前价格、20/50/100/200 日线、RSI、MACD/趋势、关键支撑、关键压力。说明是否远离均线、超买/超卖、放量滞涨、假突破风险、不能跌破的位置、突破后上行空间、明日上涨确认信号和回调风险位置。

8. 重点个股新闻与异动：
8.1 七巨头：NVDA、MSFT、AAPL、GOOGL、AMZN、META、TSLA 的涨跌幅、原因、技术位置、后续关注。判断七巨头集体上涨还是分化，谁拉动指数/拖累指数，监管/财报/产品/AI/反垄断/评级/目标价新闻。
8.2 AI 硬件/半导体：覆盖 NVDA、AMD、AVGO、MRVL、MU、TSM、ASML、ARM、INTC、QCOM、SMCI、DELL、HPE、ANET、CLS、VRT、COHR、LITE、AAOI、TSEM、SIVE 等，说明大涨/大跌原因、催化类型、拥挤度、sell the news、GPU 向光通信/电力/软件切换。
8.3 软件/SaaS/AI 应用：覆盖 CRM、NOW、SNOW、ORCL、ADBE、PANW、CRWD、DDOG、NET、MDB、PLTR、APP、TEAM、WDAY、INTU、SHOP 等，说明是否跑赢、AI 替代 SaaS 叙事、AI Agent/数据云/工作流催化、财报/评级/机构加仓/产品发布。
8.4 AI 电力/数据中心/能源基础设施：覆盖 CEG、VST、NRG、ETN、PWR、GEV、VRT、FLNC、OKLO、SMR、BE、NEE、SO、DUK、APLD、IREN、CORZ 等，说明数据中心电力链、核电/天然气/储能/电网设备/液冷/基础设施新闻、AI 数据中心需求重估、监管/订单/融资/并购/政策催化。
8.5 其他显著异动：列财报后大涨大跌、盘后异动、评级变动、并购、SEC 调查、管理层变动、回购/增发/二次发行、空头报告、指引变化。

9. 财报日历与财报解读：
9.1 昨夜重点已公布财报：表格列公司、收入、EPS、是否 beat、指引、盘后反应、核心解读，并分析收入/EPS/毛利率/运营利润率/FCF/RPO/ARR/订单/backlog/云收入/AI 收入/指引/股价反应与质量。
9.2 接下来 1-3 个交易日重要财报：日期、公司、市场关注点、可能影响板块。特别关注 NVDA、AVGO、AMD、MRVL、MU、TSM、ASML、CRM、NOW、SNOW、ORCL、ADBE、PANW、CRWD、GOOGL、MSFT、AMZN、META、AAPL、TSLA、VRT、ANET、DELL、SMCI、COHR、LITE、AAOI、CEG、VST、FLNC、OKLO 等。

10. 机构观点与资金流：整理当天重要机构观点、策略目标点位调整、AI/半导体/软件/能源/电力/金融观点变化、重点股票评级变动、ETF 资金流、期权异动、大宗交易、内部人交易、回购公告。用表格列机构/来源、观点、涉及资产、市场影响。

11. 板块轮动判断：在 AI 硬件主升浪、AI 硬件高位震荡、AI 硬件利好钝化、软件补涨/估值修复、高切低、全面 risk-on、防御 risk-off、宽度扩散、指数强内部弱、普跌恐慌、超跌反弹等状态中明确判断。回答资金流入/流出、AI 主线健康度、半导体领先性、软件相对走强、小盘参与、防御异动、趋势延续或顶部震荡。

12. 我的重点关注股观察：跟踪核心科技/AI：NVDA、AMD、AVGO、MRVL、GOOGL、MSFT、META、AMZN、ORCL；软件：CRM、NOW、SNOW、ADBE、PANW、CRWD、PLTR、DDOG、NET；光通信/AI 互连：LITE、COHR、AAOI、TSEM、SIVE、MRVL、AVGO、ANET；AI 电力/数据中心基础设施：FLNC、OKLO、VST、CEG、ETN、VRT、PWR、GEV、APLD、IREN。每只输出股票、当日涨跌、当前趋势、关键新闻、支撑位、压力位、我的判断。判断标签只能使用：继续强势、高位震荡、短线过热、回踩支撑、破位风险、等财报催化、利好兑现、低位修复、需要观察。

13. 明日交易计划/观察清单：
13.1 宏观观察：10Y、美债关键位置、DXY、油价/黄金/VIX、Fed 讲话、经济数据。
13.2 大盘观察：SPY/QQQ 支撑压力，SMH 是否强于 QQQ，IGV 是否跑赢，IWM 是否参与。
13.3 板块观察：AI 硬件、软件、金融/工业/能源、防御、市场宽度。
13.4 个股观察：列 10-20 只明天最值得关注股票及原因。

14. 风险提示：列美债收益率上行、通胀预期反弹、降息预期下降、地缘、油价、AI sell the news、半导体拥挤、软件财报、宽度恶化、信用利差、VIX、个股财报、政策/监管、美元走强等风险。表格列风险维度、当前状态、风险等级，维度包括宏观利率、市场宽度、AI 拥挤度、财报风险、地缘风险、技术面、流动性；等级使用低/中/中高/高。

15. 最终结论：包括“今日市场结论”3-5 句话；“当前市场阶段”必须从强趋势上涨、高位震荡、健康回调、板块轮动、风险偏好下降、普跌恐慌、超跌反弹中选择一个；“我的操作倾向”用中性语言说明是否适合追高/逢低/等待财报/控制仓位、关注和谨慎板块，明确不构成投资建议；“最值得关注的 5 个信号”列明次日 5 个最重要观察信号。