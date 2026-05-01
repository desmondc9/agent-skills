---
asset_class: stock
display_name: 股票 / Publicly Listed Stock
venues: [NYSE, NASDAQ, HKEX, SSE, SZSE]
currency_map: {US: USD, HK: HKD, A: CNY}
---

# Stock Asset Profile

Use this profile when `ASSET_CLASS = stock`. Covers US / HK / A-share listed equities.

## identification

The user gives either a ticker or a company name. Resolve the **primary listing** to:

- `ASSET_ID` — ticker, e.g. `AAPL`, `00700.HK`, `600519.SS`
- `ASSET_NAME` — full company name (`Apple Inc.`, `腾讯控股有限公司`)
- `ASSET_VENUE` — specific exchange: `NYSE` | `NASDAQ` | `HKEX` | `SSE` | `SZSE`
- `CURRENCY` — derived from exchange: US → USD, HK → HKD, A → CNY
- Helper vars for the fetch script:
  - `TICKER` — raw symbol (`AAPL`, `NVDA`, `00700`, `600519`)
  - `MARKET` — `US` | `HK` | `A`

If multiple **distinct companies** match the name (e.g. "Tesla" might be a Chinese namesake on SZSE), ask the user to clarify before proceeding.

### Cross-listing detection

The same underlying company is often listed on multiple exchanges. Resolve cross-listings via WebSearch:

- `<ASSET_NAME> dual listing A股 H股`
- `<ASSET_NAME> ADR HKEX SSE SZSE`
- `<ASSET_NAME> 同时上市 港股 A股 美股`

Common cross-listing patterns to watch for:

| 模式 | 示例 |
|------|------|
| A股 + H股 | 宁德时代 `300750.SZ` + `03750.HK`；比亚迪 `002594.SZ` + `01211.HK`；中国平安 `601318.SS` + `02318.HK`；招商银行 `600036.SS` + `03968.HK` |
| 美股 ADR + H股 | 阿里巴巴 `BABA` + `09988.HK`；京东 `JD` + `09618.HK`；网易 `NTES` + `09999.HK`；百度 `BIDU` + `09888.HK` |
| A股 + H股 + 美股 ADR | 中国人寿 `601628.SS` + `02628.HK` + `LFC`；中石油 `601857.SS` + `00857.HK` + `PTR`(已退市)|
| 单一上市（无跨市场） | 茅台 `600519.SS`；台积电 `TSM` (ADR) + `2330.TW`(同公司，但 .TW 不在本 skill 支持范围内) |

Variables to populate when cross-listed:

- `IS_CROSS_LISTED` — `true` / `false`
- `LISTINGS` — array of listings, each with `{ticker, market, venue, currency}`. Example for 宁德时代:
  ```json
  [
    {"ticker": "300750", "market": "A", "venue": "SZSE", "currency": "CNY"},
    {"ticker": "03750",  "market": "HK","venue": "HKEX", "currency": "HKD"}
  ]
  ```
- `PRIMARY_VENUE` — pick the home market by default (A-share for mainland-China-incorporated companies; US for US-incorporated companies). For tied cases, pick the listing with larger market cap or higher ADTV.

If `IS_CROSS_LISTED = false`, set `LISTINGS` to a single-element array containing the resolved primary listing.

## data_fetch_command

For each entry in `LISTINGS`, run:

```bash
uv run --script ~/.claude/skills/analyze-asset-with-agents-team/scripts/fetch_stock_data.py \
    --asset-class stock \
    --ticker <TICKER> \
    --market <US|HK|A> \
    --output-dir "$(pwd)/${BASE_DIR}/01_basic_data"
```

When `IS_CROSS_LISTED = true`, invoke this command **once per listing** (in parallel where possible — e.g. via background shells). Each invocation produces its own JSON record + two PNG charts named after the ticker (no collisions).

Ticker conventions for `--ticker`:
- US: raw symbol (`AAPL`, `NVDA`, `TSLA`, `BABA`)
- HK: digits only, e.g. `00700`, `03750`, `09988` (strip `.HK`)
- A-share: 6-digit code, e.g. `600519`, `300750` (strip `.SS` / `.SZ`)

Parse each invocation's stdout JSON and capture `current_price`, `as_of_date`, `daily_chart_relpath`, `weekly_chart_relpath`, `daily_trend_description`, `weekly_trend_description`, `data_source`, `period_start`, `period_end`, `period_high`, `period_low`. Tag each record with its `LISTINGS` entry so the basic_data template can render the cross-market comparison.

If any invocation exits non-zero or returns `{"error": ...}`, fall back to WebSearch for that listing's current price and skip chart embedding for that market only. Note the degradation in the report. Do not abandon the cross-market analysis if at least one market succeeds.

## macro_queries

Run each as an independent WebSearch:

- `current federal reserve interest rate` / `美联储 当前基准利率`
- `China PBOC current LPR 1-year 5-year` / `PBOC 7-day reverse repo rate` / `中国人民银行 当前 LPR 1年 5年`
- `current US CPI PPI inflation data` / `中国 CPI PPI 最新数据`
- `<ASSET_NAME> geopolitical risks supply chain`
- `<industry> industry growth rate market size`
- `<ASSET_NAME> industry regulation policy government`
- `<industry> competitive landscape market share concentration`

## fundamental_queries

- `<ASSET_ID> gross margin net margin ROE annual`
- `<ASSET_ID> free cash flow operating cash flow`
- `<ASSET_ID> debt to equity ratio current ratio interest coverage`
- `<ASSET_NAME> competitive moat patents R&D spending`
- `<ASSET_NAME> market share brand customer retention`
- `<ASSET_NAME> management CEO biography insider ownership`
- `<ASSET_NAME> supply chain key components vertical integration`

## market_queries

Per-listing queries (run for **every** entry in `LISTINGS`, substituting that listing's ticker):

- `<listing.ticker> PE ratio PB ratio PS ratio current`
- `<listing.ticker> PEG ratio forward PE`
- `<listing.ticker> historical PE ratio 5 year 10 year percentile`
- `<listing.ticker> 20 day 200 day moving average RSI`
- `<listing.ticker> institutional ownership changes hedge fund holdings`
- `<listing.ticker> analyst rating consensus price target`
- `<listing.ticker> ADTV average daily trading volume market cap`

Cross-market queries (run only when `IS_CROSS_LISTED = true`):

- `<ASSET_NAME> A股 H股 溢价 折价 当前 AH premium discount`
- `<ASSET_NAME> ADR HKEX premium discount arbitrage`
- `<ASSET_NAME> southbound northbound flow 港股通 沪深港通 holdings`
- `<ASSET_NAME> dividend withholding tax A H ADR comparison`
- `<ASSET_NAME> liquidity comparison A H ADR ADTV bid ask`
- `Hang Seng AH Premium Index current level 恒生 AH 股溢价指数`

## basic_data_template

Save as `{BASE_DIR}/01_basic_data/basic_data.md`. The template is **conditional** on `IS_CROSS_LISTED`. The single-listing path keeps the original layout; the cross-listed path adds a "跨市场对比" block and renders one K-line pair per market.

### Header (always)

```markdown
# {ASSET_NAME}（主上市: {ASSET_ID}）- 股票调研指标 MECE 框架

资产类别: Stock (公开上市股票)
主要上市: {ASSET_ID} @ {ASSET_VENUE}
当前价格（主上市）: {CURRENT_PRICE} {CURRENCY}  （数据源: {data_source}，截至 {PRICE_AS_OF}）
是否跨市场上市: {是 — 共 {N} 个市场 / 否}
当前时间戳: {DISPLAY_TIMESTAMP} UTC+8
本次分析工具: {TOOL_NAME} / {MODEL_NAME}
货币单位声明: 本报告主币为 **{CURRENCY}**（主上市的交易货币）。跨市场对比表统一换算到 **{NORMALIZED_CCY}**（CNY 或 USD），并注明换算汇率。
报告语言声明: 本 skill 的所有 markdown 输出文件均使用 **简体中文**；专有名词、代码、指标缩写保留原文。
```

### Single-listing path (`IS_CROSS_LISTED = false`)

Render the original sections — 3年日K图、3年周K图、外部环境、公司基本面、市场交易面 — as before.

### Cross-listed path (`IS_CROSS_LISTED = true`)

Insert these sections **before** "一、外部环境":

```markdown
## 跨市场上市清单 (Listings)

| 市场 | 代码 | 交易所 | 货币 | 当前价 | 截至 | 数据源 |
|------|------|--------|------|--------|------|--------|
| {market} | {ticker} | {venue} | {currency} | {current_price} {currency} | {as_of_date} | {data_source} |
| ... 每个 listing 一行 ...|

---

## 跨市场对比 (Cross-Market Comparison)

> 所有数值已统一换算到 **{NORMALIZED_CCY}**；汇率来源 / 截至日期：{FX_SOURCE} {FX_AS_OF}。

| 指标 | {listing_1.market} ({listing_1.ticker}) | {listing_2.market} ({listing_2.ticker}) | ... | 比较结论 |
|------|----------------|----------------|-----|---------|
| 当前价 ({NORMALIZED_CCY}) | {price_1} | {price_2} | | {哪个更便宜} |
| 市值 ({NORMALIZED_CCY}) | {mcap_1} | {mcap_2} | | |
| PE | {pe_1}x | {pe_2}x | | |
| PB | {pb_1}x | {pb_2}x | | |
| PS | {ps_1}x | {ps_2}x | | |
| 股息率 | {div_1}% | {div_2}% | | {扣税前/后} |
| 30日 ADTV ({NORMALIZED_CCY}) | {adtv_1} | {adtv_2} | | {哪个流动性更好} |
| 3年涨跌幅 | {ret_1}% | {ret_2}% | | |
| 估值历史分位 (5年) | {pct_1}% | {pct_2}% | | |

**A/H 溢价（如适用）**: {溢价值}% — 当 A 股相对 H 股 {溢价/折价}。基准来源: 恒生 AH 股溢价指数当前 {X}。
**ADR 溢价（如适用）**: {溢价值}% — ADR 相对本地 H 股或 A 股 {溢价/折价}。
**资金流向**：南向资金近 30 日净流入 {X} 亿 {CURRENCY}；北向资金 {X}。
**股息税差**：{描述各市场股息预提税差异，对长期持有的影响}。
**投资者准入**：{大陆个人投资者通过 港股通 / QDII / 美股直通车 等访问各市场的便利度与门槛}。

---

## 各市场 K线（每个 listing 一组）

### {listing_1.ticker} @ {listing_1.venue} — 最近3年 日K / 周K

![{listing_1.ticker} Daily]({listing_1.daily_chart_relpath})

**日K 走势描述**: {listing_1.daily_trend_description}
（区间: {listing_1.period_start} → {listing_1.period_end}；区间最高 {listing_1.period_high} {listing_1.currency}；区间最低 {listing_1.period_low} {listing_1.currency}）

![{listing_1.ticker} Weekly]({listing_1.weekly_chart_relpath})

**周K 走势描述**: {listing_1.weekly_trend_description}

### {listing_2.ticker} @ {listing_2.venue} — 最近3年 日K / 周K

（同上结构，对每个 listing 重复一次）

---
```

After the cross-market block, render the standard sections — "一、外部环境"、"二、公司基本面"（公司层面共享，无需按市场拆分）、"三、市场交易面"（按主上市为代表，但保留每个市场的关键指标快照）— exactly as in the single-listing path.
