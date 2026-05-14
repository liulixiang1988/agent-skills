# 市场与 URL 模式

stockanalysis.com 是首选数据源：覆盖完整、字段稳定、URL 可拼接。除 A 股外，三大报表（利润表 / 资产负债表 / 现金流量表）都按统一模板提供 4-10 年历史。

## URL 拼接规则

每只股票的财务数据按"基础页 + 子路径"组织。基础页拼接规则按市场不同：

| 市场 | 基础页 URL 模式 | 示例（美光 / 腾讯 / SK海力士） |
|---|---|---|
| 美股 | `https://www.stockanalysis.com/stocks/{ticker}/` | `…/stocks/mu/` |
| 港股 | `https://www.stockanalysis.com/quote/hkg/{code}/` | `…/quote/hkg/0700/`（去掉前导 0 也通常有效）|
| 韩股 | `https://www.stockanalysis.com/quote/krx/{code}/` | `…/quote/krx/000660/` |
| A 股（沪） | `https://www.stockanalysis.com/quote/sha/{code}/` | `…/quote/sha/600519/` |
| A 股（深） | `https://www.stockanalysis.com/quote/shz/{code}/` | `…/quote/shz/000001/` |

> **A 股注意**：stockanalysis.com 对 A 股覆盖有限，部分小市值股票可能无数据。失败时回退到 Futu API（见下文）。

## 三大报表子路径

在基础页后追加：

| 报表 | 子路径 | 关键字段 |
|---|---|---|
| 利润表 | `financials/` | revenue, gross profit/margin, operating income/margin, net income, EPS (diluted) |
| 资产负债表 | `financials/balance-sheet/` | total assets, total liabilities, total equity, cash & equivalents, total debt |
| 现金流量表 | `financials/cash-flow-statement/` | operating cash flow, capital expenditure, free cash flow, dividends paid |

**完整示例**（美光资产负债表）：
`https://www.stockanalysis.com/stocks/mu/financials/balance-sheet/`

## 财年口径差异（重要）

不同公司的财年截止月不一致，做对比时**必须显式标注**，不能直接把"FY2025"当成日历年 2025：

| 公司类型 | 常见财年截止 | 影响 |
|---|---|---|
| 多数美股、A 股、港股 | 12 月 | 直接对应日历年 |
| 美光 (MU) | 8 月底 | FY2025 = 2024-08 ~ 2025-08 |
| 苹果 (AAPL) | 9 月底 | FY2024 = 2023-10 ~ 2024-09 |
| 英伟达 (NVDA) | 1 月底 | FY2025 = 2024-02 ~ 2025-01 |
| 沃尔玛、思科等多家美国零售/科技 | 1-7 月 | 各异 |

调用 WebFetch 提取数据时，prompt 里要求一并返回 "fiscal year end date"，确保读到的是哪个时段的数据。

## 货币换算

韩股、港股财报以本币（KRW / HKD）记账，做跨市场对比时统一折算为美元：

| 货币 | 近似汇率（仅供横向对照） |
|---|---|
| KRW → USD | 1 USD ≈ 1,400 KRW |
| HKD → USD | 1 USD ≈ 7.8 HKD |
| CNY → USD | 1 USD ≈ 7.2 CNY |
| JPY → USD | 1 USD ≈ 150 JPY |

> 这些汇率是粗估，仅用于让读者对比时有量级感。**报告里要明确标注 "按 1 USD ≈ X 折算"**，并且本币原值也保留一份。

## A 股回退方案（Futu API）

stockanalysis.com 对 A 股覆盖不全时，可用 Futu API 的 snapshot 接口拿基础估值数据：

```bash
python3 ~/.claude/skills/futuapi/scripts/quote/get_snapshot.py SH.600519 --json
```

但 Futu API **不提供历史财报数据**，只有当下的市值、PE、PB、TTM 营收/净利润等快照字段。如果用户要做"近三年"分析而 stockanalysis.com 也查不到，需向用户说明数据缺口并询问是否换标的或仅用快照数据。

## WebFetch 调用示例

每个报表用一个 WebFetch 调用，并行发起以节省时间：

```
WebFetch(
  url="https://www.stockanalysis.com/stocks/mu/financials/",
  prompt="Extract Micron's annual income statement for the last three fiscal years.
          Include: revenue, gross profit, gross margin, operating income, operating
          margin, net income, EPS diluted, and the fiscal year end date."
)
```

提取出的数据通常以 millions USD 为单位（韩股是 millions KRW），照原样保留并在表格里标注单位。
