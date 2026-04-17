---
asset_class: private
display_name: 未上市公司 / Private Company
venues: [Private market, Secondary marketplaces, Venture rounds]
currency_map: {default: USD}
---

# Private Company Asset Profile

Use this profile when `ASSET_CLASS = private`. Covers venture-backed startups, unicorns, and privately held mature companies — any company **without a publicly traded ticker**, where valuation is set by primary funding rounds and secondary transactions rather than a continuous order book.

## identification

The user gives a company name (`Stripe`, `OpenAI`, `SpaceX`, `字节跳动`). Resolve to:

- `ASSET_ID` — lowercase slug (`stripe`, `openai`, `spacex`, `bytedance`)
- `ASSET_NAME` — canonical name (`Stripe, Inc.`, `OpenAI`, `Space Exploration Technologies Corp.`, `字节跳动 / ByteDance`)
- `ASSET_VENUE` — `Private (USA)` / `Private (China)` / `Private (EU)` — country of incorporation, with the word "Private" explicit
- `CURRENCY` — primary reporting currency, usually `USD` for US companies; `CNY` or `USD` acceptable for Chinese companies, confirm with the user if both are used in sources
- Helper note: if multiple companies share the name, ask the user to clarify (e.g. "Palantir" was private until 2020, but "Palantir" today is public — confirm they mean a private company and not the listed version).

**Important:** if the "company" the user names actually has a public ticker (including ADRs or dual listings), switch to the `stock` profile instead. This profile is strictly for companies with no public equity trading.

## data_fetch_command

**No fetcher script.** Private companies have no continuous public price history. Skip Step 3 and proceed straight to the WebSearch queries below. The `01_basic_data/assets/` directory stays empty (or is omitted entirely).

Set these fallback variables manually so the basic_data template renders cleanly:

- `CURRENT_PRICE` → last primary-round share price **or** "implied per-share value at last round" **or** "N/A (no published share price)"
- `PRICE_AS_OF` → date of the last primary round (or most recent secondary mark)
- `data_source` → cite primary sources (Crunchbase, PitchBook, TechCrunch, SEC filings of investors)

## macro_queries

Private-company performance depends on the venture funding climate and the public comparables market:

- `current federal reserve interest rate` / `美联储 当前基准利率` （影响 VC 募资与 DPI）
- `venture capital funding climate Q current year` / `PitchBook venture monitor latest`
- `<industry> private company valuation multiples revenue`
- `<industry> public company average EV to revenue PS ratio` （用作可比）
- `<industry> IPO market open closed sentiment`
- `<ASSET_NAME> country regulation compliance`

## fundamental_queries

Since public financials are optional, use a "best-available" funnel:

**Funding & Cap Table:**
- `<ASSET_NAME> funding rounds history Crunchbase`
- `<ASSET_NAME> latest Series funding amount valuation lead investor`
- `<ASSET_NAME> total funding raised to date`
- `<ASSET_NAME> cap table ownership founder investor`
- `<ASSET_NAME> secondary market share price Forge Hiive EquityZen`

**Business Fundamentals (if disclosed):**
- `<ASSET_NAME> annual revenue ARR latest`
- `<ASSET_NAME> gross margin operating margin profitable cash flow positive`
- `<ASSET_NAME> burn rate runway cash position`
- `<ASSET_NAME> customer count growth rate year over year`
- `<ASSET_NAME> headcount employees growth`

**Competitive Position:**
- `<ASSET_NAME> market share industry ranking`
- `<ASSET_NAME> key competitors head to head`
- `<ASSET_NAME> key product differentiation moat technology`
- `<ASSET_NAME> management founder background`

**Exit Path Signals:**
- `<ASSET_NAME> IPO filing S-1 rumor`
- `<ASSET_NAME> acquisition offer rumor strategic interest`

## market_queries

For private companies, "market" means **comparable-public multiples** and **secondary-market marks**:

- `<ASSET_NAME> implied valuation revenue multiple` （计算 EV / Revenue 并与可比公众公司比较）
- `<nearest public comp 1> PE PS EV/Revenue current`
- `<nearest public comp 2> PE PS EV/Revenue current`
- `<ASSET_NAME> secondary market tender offer employee liquidity round price`
- `<ASSET_NAME> mutual fund markdown markup Fidelity T Rowe Price` （许多共同基金会定期对持有的私有公司股权重新估值）
- `<ASSET_NAME> 409A valuation recent` （若找得到）

## basic_data_template

Save as `{BASE_DIR}/01_basic_data/basic_data.md`:

```markdown
# {ASSET_ID} / {ASSET_NAME} - 未上市公司调研指标 MECE 框架

资产类别: Private Company (未上市公司)
资产标识: {ASSET_ID}
最新估值: {CURRENT_PRICE} {CURRENCY} per share  （或："last-round implied ${VALUATION} post-money"；若无公开价格：写 "N/A — 最近一次融资于 {PRICE_AS_OF} 完成，估值 {VALUATION}"）
主要数据来源: {data_source}（如 Crunchbase / PitchBook / 公司公告）
注册地/性质: {ASSET_VENUE}
当前时间戳: {DISPLAY_TIMESTAMP} UTC+8
本次分析工具: {TOOL_NAME} / {MODEL_NAME}
货币单位声明: 本报告中所有金额以 **{CURRENCY}** 为主币；估值、融资额、可比公司指标若来源货币不同，将显式换算并注明汇率与日期。

> 本资产无公开价格历史；本报告用「融资轨迹 + 可比上市公司倍数 + 二级市场成交」替代 K 线与公众市场估值。

---

## 融资轨迹 (Funding Timeline)

| 轮次 | 时间 | 融资额 ({CURRENCY}) | 投后估值 ({CURRENCY}) | 领投 | 备注 |
|------|------|-------------------|---------------------|------|------|
| {Seed} | {YYYY-MM} | {X} | {X} | {投资人} | {用途/里程碑} |
| {Series A} | {YYYY-MM} | {X} | {X} | {投资人} | {里程碑} |
| {Series B} | {YYYY-MM} | {X} | {X} | {投资人} | {里程碑} |
| ...  | ... | ... | ... | ... | ... |
| **最新轮** | {YYYY-MM} | **{X}** | **{X}** | {投资人} | {结构：纯主要 / 含老股转让比例} |

**累计融资额：** {X} {CURRENCY}
**最新估值增速（相邻两轮年化）：** {+/-X}% p.a.
**二级市场参考价：** {若有来自 Forge / Hiive / 员工要约回购的成交价，列此}

---

## 一、 外部环境 (External Environment)

### 1. 宏观 / 融资环境 (Macro & Funding Climate)
- **美联储基准利率 (Fed Funds Rate)：** {当前水平及方向 — 决定 VC LP 募资难度与晚期估值倍数}
- **风险资本融资环境：** {最近季度 VC 总投资额、同比变化，后期轮次情况}
- **IPO 市场窗口：** {当前是否开放，最近同行业 IPO 表现}

### 2. 行业特征 (Industry)
- **行业增速：** {行业 CAGR，所处发展阶段}
- **政策导向：** {关键监管/政策对该赛道的影响}
- **行业竞争：** {头部集中度，主要已上市/未上市对手}

---

## 二、 公司基本面 (Company Fundamentals)

### 1. 业务指标 (Business Metrics — 公开可得的部分)
- **收入 / ARR：** {X} {CURRENCY}，同比增速 {+X}%  （来源：{来源}）
- **毛利率 / 经营利润率：** {X}% / {X}%  （若披露）
- **现金消耗 / 净现金头寸 / 可用跑道：** {X} {CURRENCY} 月消耗；{X} 个月跑道
- **客户/用户规模：** {X}，同比 {+/-X}%

### 2. 业务竞争优势 (Business)
- **核心技术/壁垒：** {技术、专利、数据、网络效应}
- **管理层：** {创始人背景、关键人员、主要董事}
- **重要客户 / 分销：** {集中度，前 5 客户占比}
- **资本效率：** {累计融资 / ARR 比值；或 LTV/CAC 若披露}

---

## 三、 市场与流动性面 (Market & Liquidity)

### 1. 估值水平 (Valuation — 以可比公开公司为锚)
- **最新估值：** {X} {CURRENCY}（{post-money / pre-money}；日期 {PRICE_AS_OF}）
- **隐含 EV / Revenue：** {X}x
- **隐含 EV / ARR：** {X}x
- **可比上市公司（列 2–3 个）：**
  | 可比公司 | 票 | EV/Revenue | EV/EBITDA | 增速 |
  |---------|----|-----------|-----------|-----|
  | {Comp 1} | {ticker} | {X}x | {X}x | {+X}% |
  | {Comp 2} | {ticker} | {X}x | {X}x | {+X}% |
- **相对可比公司：** {溢价/折价 {X}%}

### 2. 流动性与退出信号 (Liquidity & Exit Signals)
- **二级市场成交：** {最近可得的 Forge/Hiive 报价或员工要约价}
- **共同基金持股估值：** {Fidelity / T. Rowe Price 对该公司持股的最新季度估值变动}
- **IPO / 并购信号：** {是否有 S-1 传闻、战略收购意向、指定承销商等}
```
