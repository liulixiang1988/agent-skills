---
name: stock-financials-analysis
description: Pulls 3-year financial statements (income, balance sheet, cash flow) for a single stock and produces a deep Chinese-language report, OR compares multiple peers head-to-head. Use whenever the user asks to 分析/解读/看一下 a company's 财报/财务/营收/利润/资产负债/现金流, asks for 三年/近三年/最近几年 financials, or wants to compare multiple stocks 对比/PK/比较 on financial metrics. Triggers on phrases like "帮我看下 X 的财报"、"分析 X 这三年的财务"、"X 和 Y 哪个更好"、"对比 A B C 三家". Covers US/HK/KR/A-share stocks via stockanalysis.com.
---

# 股票三年财务分析与同业对比

把一只股票的近三年三大报表浓缩成"数据表 + 关键判断 + 风险提示"的中文报告；或把 2-4 只同业股票放在一起做横向对比。

## 触发与分流

用户的请求落入以下两种模式之一：

| 模式 | 用户提问示例 | 走哪个流程 |
|---|---|---|
| **单股深度分析** | "分析美光这三年的财务"、"帮我看下腾讯的财报"、"NVDA 近三年怎么样" | 走 §单股流程 |
| **同业对比** | "对比三星和 SK 海力士"、"美光、海力士、三星谁更强"、"BABA 和 PDD 比较" | 走 §对比流程 |

如果用户先做了单股分析、再说"对比一下 X 和 Y"，**继承上一次的主标的**作为对比的第一家，再加上用户新提到的对手。

## 标的解析

用户给的可能是中文名（"腾讯"）、英文简称（"NVDA"）、或带前缀代码（"US.MU"）。先解析为：
- **公司中文名**（用于报告标题，如"美光科技"）
- **市场代码**（US/HK/KR/SHA/SHZ）
- **stockanalysis.com 上的 ticker/code**（用于拼 URL）

不确定时用 AskUserQuestion 让用户确认，不要瞎猜（特别是中港同名股、ADR 与原股的关系）。

URL 拼接规则与各市场 ticker 写法详见 `references/markets.md`。

## 单股流程（三年深度分析）

### 1. 并行拉取三大报表

**必须**用一次 message 内多个 WebFetch 并行拉取，不要串行——三个请求互相独立，串行会浪费 1-2 分钟：

```
WebFetch(url=「基础页+financials/」, prompt="...利润表...")
WebFetch(url=「基础页+financials/balance-sheet/」, prompt="...资产负债表...")
WebFetch(url=「基础页+financials/cash-flow-statement/」, prompt="...现金流量表...")
```

每个 prompt 里都要显式要求返回 **fiscal year end date**，避免读到的是 TTM 还是 FY 搞不清。

具体的 URL 模式、字段清单、A 股回退方案见 `references/markets.md`。

### 2. 按模板组装报告

读 `references/templates.md` 的 **模板 A**，把数据填进去。务必保留：
- 三大报表表格（每张表都有"趋势/解读"列）
- §四「关键判断」段落（5 条以内，每条解释 why）
- 财年说明 + 数据源链接 + 免责声明

### 3. 收尾

报告末尾留一个 hook，邀请用户继续深挖：
> "如需进一步对比同业，或拉取最近 4 个季度的季报演变，告诉我即可。"

## 对比流程（同业横向对比）

### 1. 确认对手与主题

如果用户只给了对手名字没给主题（"对比三星和 SK 海力士"），自己根据上下文推断报告主题（"内存三巨头三年对决"），但**不要自作主张加第三、第四家**——除非用户明确说"还有 X"。

### 2. 并行拉取多家三大报表

每家 3 个 WebFetch，多家并行——一次 message 可以发起 6-12 个 WebFetch 调用。Claude Code 单 message 多 tool 的并行能力是这个 skill 节省时间的关键，**不要嫌多**。

### 3. 货币换算

韩股/港股/日股的报表是本币，做横向对比时统一折算为美元：
- 表格里同时列本币原值和折算值（如 `₩97.1 万亿 ≈ $694 亿`）
- 报告开头明确标注汇率（如 `按 1 USD ≈ 1,400 KRW 折算`）
- 汇率表见 `references/markets.md`

### 4. 按模板 B 组装

模板 B 的"投资视角的'个性'对比"那张表是核心——纯数字看不出 alpha 在哪，要把"为什么投 A 不投 B"的判断显式写出来。维度至少包括：
- 业务纯度（纯赛道 vs 多元化）
- 核心 beta 弹性（对当前主题的暴露度）
- 周期波动性
- 估值锚（PE 区间）
- 地缘风险
- 适合的投资人画像

### 5. 行业份额一节（可选）

当对比主题集中在某个垂直市场（HBM、云计算、新能源车、电商）时，纯财务对比不够，需要补一段行业份额数据。这部分通常需要凭已有知识写，注明"行业研究报告普遍数据"。

## 数据可信度与边界

- **stockanalysis.com 字段稳定**，但偶尔会把 TTM 和 FY 混在一起。WebFetch prompt 要明确要求 "annual" + "fiscal year end date"。
- **A 股覆盖有限**：小市值股票可能查不到。失败时回退到 Futu API 的 snapshot（仅快照，无历史）；如果用户坚持要历史财报又查不到，告诉他数据缺口，不要编。
- **细分业务数据缺失**：stockanalysis.com 只有公司总账，看不到分部数据（如三星的 DS 部门、亚马逊的 AWS）。这种细分需求要么向用户说明、要么从公司年报 PDF 补——后者超出本 skill 范围。
- **不报 PE/PB 估值**：本 skill 只做报表分析，不做估值判断。如果用户问"现在贵不贵"，建议他用 Futu snapshot 看实时 PE，或单独要求估值分析。

## 报告风格硬约束

- **中文输出**，数字保留原始单位（百万 USD 或亿 USD），表头明确标注
- **每张表都要有"趋势/解读"列**，不能只给数字
- **关键判断段必须解释 why**，不能只复述数字
- **必须写风险提示**（至少 2-3 条）
- **结尾必须有免责声明**：`> 仅供学习研究，不构成投资建议。`
- **数据源链接必须给**，方便用户核验

## 快速参考

- 各市场 URL 模式、汇率表、A 股回退方案 → `references/markets.md`
- 单股报告模板 A、对比报告模板 B、写作要点 → `references/templates.md`
