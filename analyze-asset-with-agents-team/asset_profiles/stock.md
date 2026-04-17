---
asset_class: stock
display_name: 股票 / Publicly Listed Stock
venues: [NYSE, NASDAQ, HKEX, SSE, SZSE]
currency_map: {US: USD, HK: HKD, A: CNY}
---

# Stock Asset Profile

Use this profile when `ASSET_CLASS = stock`. Covers US / HK / A-share listed equities.

## identification

The user gives either a ticker or a company name. Resolve to:

- `ASSET_ID` — ticker, e.g. `AAPL`, `00700.HK`, `600519.SS`
- `ASSET_NAME` — full company name (`Apple Inc.`, `腾讯控股有限公司`)
- `ASSET_VENUE` — specific exchange: `NYSE` | `NASDAQ` | `HKEX` | `SSE` | `SZSE`
- `CURRENCY` — derived from exchange: US → USD, HK → HKD, A → CNY
- Helper vars for the fetch script:
  - `TICKER` — raw symbol (`AAPL`, `NVDA`, `00700`, `600519`)
  - `MARKET` — `US` | `HK` | `A`

If multiple companies match the name (e.g. "Tesla" might be a Chinese namesake on SZSE), ask the user to clarify before proceeding.

## data_fetch_command

```bash
uv run --script ~/.claude/skills/analyze-asset-with-agents-team/scripts/fetch_stock_data.py \
    --asset-class stock \
    --ticker <TICKER> \
    --market <US|HK|A> \
    --output-dir "$(pwd)/${BASE_DIR}/01_basic_data"
```

Ticker conventions for `--ticker`:
- US: raw symbol (`AAPL`, `NVDA`, `TSLA`)
- HK: digits only, e.g. `00700` (strip `.HK`)
- A-share: 6-digit code, e.g. `600519` (strip `.SS` / `.SZ`)

Parse stdout JSON and capture `current_price`, `as_of_date`, `daily_chart_relpath`, `weekly_chart_relpath`, `daily_trend_description`, `weekly_trend_description`, `data_source`, `period_start`, `period_end`, `period_high`, `period_low`.

If the script exits non-zero or returns `{"error": ...}`, fall back to WebSearch for the current price and skip chart embedding. Note the degradation in the report.

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

- `<ASSET_ID> PE ratio PB ratio PS ratio current`
- `<ASSET_ID> PEG ratio forward PE`
- `<ASSET_ID> historical PE ratio 5 year 10 year percentile`
- `<ASSET_ID> 20 day 200 day moving average RSI`
- `<ASSET_ID> institutional ownership changes hedge fund holdings`
- `<ASSET_ID> analyst rating consensus price target`

## basic_data_template

Save as `{BASE_DIR}/01_basic_data/basic_data.md`:

```markdown
# {ASSET_ID} / {ASSET_NAME} - 股票调研指标 MECE 框架

资产类别: Stock (公开上市股票)
资产代码: {ASSET_ID}
当前价格: {CURRENT_PRICE} {CURRENCY}  （数据源: {data_source}，截至 {PRICE_AS_OF}）
交易场所: {ASSET_VENUE}
当前时间戳: {DISPLAY_TIMESTAMP} UTC+8
本次分析工具: {TOOL_NAME} / {MODEL_NAME}
货币单位声明: 本报告中所有金额以 **{CURRENCY}** 为主币；若引用其他货币来源，会显式标注原货币及换算汇率。

---

## 最近3年 日K 图

![3-Year Daily K-line]({daily_chart_relpath})

**走势描述**: {daily_trend_description}

（区间: {period_start} → {period_end}；区间最高 {period_high} {CURRENCY}；区间最低 {period_low} {CURRENCY}）

## 最近3年 周K 图

![3-Year Weekly K-line]({weekly_chart_relpath})

**走势描述**: {weekly_trend_description}

---

## 一、 外部环境 (External Environment)

### 1. 宏观经济指标 (Macro)
- **美联储基准利率 (Fed Funds Rate)：** {当前区间及最近政策方向}
- **中国央行基准利率 (PBOC)：** {最新 1年期 LPR / 5年期 LPR，及 7 天逆回购利率，政策方向}
- **通胀数据 (CPI/PPI)：** {中美最新 CPI/PPI 数据及趋势}
- **地缘政治风险：** {与该公司相关的地缘政治风险}

### 2. 行业特征指标 (Industry)
- **行业增速：** {行业当前增速，所处发展阶段}
- **政策导向：** {相关政府政策、监管趋势}
- **竞争格局：** {行业集中度，主要竞争对手，价格竞争情况}

---

## 二、 公司基本面 (Company Fundamentals)

### 1. 财务健康度 (Financials)
- **盈利能力：** 毛利率 {X}% | 净利率 {X}% | ROE {X}%
- **现金获取能力：** 经营性现金流 {X} {CURRENCY} | 自由现金流(FCF) {X} {CURRENCY}
- **资产结构：** 资产负债率 {X}% | 流动比率 {X} | 利息保障倍数 {X}

### 2. 业务竞争优势 (Business)
- **核心技术/壁垒：** {专利数量、研发投入占比 (R&D {X} {CURRENCY} / 营收 {X}%)}
- **市场份额：** {市场份额、品牌溢价、用户黏性}
- **管理与治理：** {管理层背景、内部人持股比例}
- **供应链韧性：** {关键零部件自给率或多元化情况}

---

## 三、 市场交易面 (Market & Trading)

### 1. 估值水平 (Valuation)
- **相对估值：** PE {X}x | PB {X}x | PS {X}x
- **成长估值：** PEG {X}
- **历史分位：** 当前 PE 在过去 5 年处于 {X}% 分位

### 2. 技术与情绪 (Technical & Sentiment)
- **价格动量：** 20日均线 {X} {CURRENCY} | 200日均线 {X} {CURRENCY} | RSI {X}
- **资金流向：** {机构持仓变动、主力资金流向}
- **市场情绪：** {分析师评级、目标价 {X} {CURRENCY}、盈利预期方向}
```
