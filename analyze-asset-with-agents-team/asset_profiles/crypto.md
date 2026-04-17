---
asset_class: crypto
display_name: 加密货币 / Cryptocurrency
venues: [Bitcoin L1, Ethereum L1, Solana, Other L1/L2, CEX composite]
currency_map: {default: USD}
---

# Crypto Asset Profile

Use this profile when `ASSET_CLASS = crypto`. Covers layer-1 / layer-2 native tokens, DeFi governance tokens, and major stablecoins — anything with a public OHLCV history on CoinGecko or a major exchange.

## identification

The user gives either a symbol (`BTC`, `ETH`, `SOL`) or a coin name (`Bitcoin`, `Ethereum`, `Solana`). Resolve to:

- `ASSET_ID` — symbol in uppercase (`BTC`, `ETH`, `SOL`) plus CoinGecko id for the fetch script
- `ASSET_NAME` — canonical name (`Bitcoin`, `Ethereum`, `Solana`)
- `ASSET_VENUE` — concise description: `Bitcoin L1`, `Ethereum L1`, `Solana L1`, `Polygon L2`, `Multi-chain`
- `CURRENCY` — `USD` by default; BTC-denominated side-quote optional in the report
- Helper vars for the fetch script:
  - `COIN_ID` — CoinGecko id, e.g. `bitcoin`, `ethereum`, `solana`
  - `SYMBOL` — uppercase symbol for the Binance fallback, e.g. `BTC`, `ETH`

If the user says "ETH" but could reasonably mean **Ethernity Chain (ERN)**, **Ethereum Classic (ETC)**, or another token, ask them to clarify before proceeding.

## data_fetch_command

```bash
uv run --script ~/.claude/skills/analyze-asset-with-agents-team/scripts/fetch_crypto_data.py \
    --asset-class crypto \
    --coin-id <COIN_ID> \
    --symbol <SYMBOL> \
    --output-dir "$(pwd)/${BASE_DIR}/01_basic_data"
```

Parse stdout JSON and capture the same fields as the stock fetcher: `current_price`, `as_of_date`, `daily_chart_relpath`, `weekly_chart_relpath`, `daily_trend_description`, `weekly_trend_description`, `data_source`, `period_start`, `period_end`, `period_high`, `period_low`.

If the script exits non-zero or returns `{"error": ...}`, fall back to WebSearch for the current price and skip chart embedding. Note the degradation in the report.

## macro_queries

- `current federal reserve interest rate` / `美联储 当前基准利率`
- `US Dollar Index DXY current level trend`
- `Bitcoin dominance BTC.D current`
- `total crypto market cap TOTAL current` / `crypto market cap trend 90 day`
- `stablecoin supply USDT USDC total current`
- `<ASSET_NAME> sector TVL DeFi Llama` (if applicable — skip for pure L1 monetary plays like BTC)
- `crypto regulation US SEC ETF` / `EU MiCA crypto regulation status`

## fundamental_queries

Tokenomics + on-chain + protocol economics take the place of traditional fundamentals:

- `<ASSET_NAME> circulating supply total supply max supply`
- `<ASSET_NAME> inflation rate emission schedule halving`
- `<ASSET_NAME> token unlock schedule next 12 months`
- `<ASSET_NAME> holder concentration top 10 wallets whales`
- `<ASSET_NAME> protocol revenue annualized fees last 30 days`
- `<ASSET_NAME> TVL total value locked`
- `<ASSET_NAME> daily active addresses transaction count`
- `<ASSET_NAME> developer activity GitHub commits active devs`
- `<ASSET_NAME> roadmap upcoming upgrades`
- `<ASSET_NAME> governance token voting decentralization`

## market_queries

- `<SYMBOL> price today USD` (sanity check vs fetcher output)
- `<SYMBOL>USDT funding rate perpetual futures current` (Binance / Bybit)
- `<SYMBOL> perp open interest OI current`
- `<SYMBOL> 30 day realized volatility`
- `<SYMBOL> ETF flows spot ETF net inflow` (BTC, ETH only)
- `<SYMBOL> Coinbase premium` / `<SYMBOL> exchange netflow 7 day`
- `<ASSET_NAME> analyst price target 12 month` (treat with skepticism — crypto PT consensus is noisy)

## basic_data_template

Save as `{BASE_DIR}/01_basic_data/basic_data.md`:

```markdown
# {ASSET_ID} / {ASSET_NAME} - 加密资产调研指标 MECE 框架

资产类别: Crypto (加密货币)
资产代码: {ASSET_ID}  (CoinGecko id: {COIN_ID})
当前价格: {CURRENT_PRICE} {CURRENCY}  （数据源: {data_source}，截至 {PRICE_AS_OF}）
主要流通场所: {ASSET_VENUE}
当前时间戳: {DISPLAY_TIMESTAMP} UTC+8
本次分析工具: {TOOL_NAME} / {MODEL_NAME}
货币单位声明: 本报告中所有金额以 **{CURRENCY}** 为主币。加密资产的价格波动极大，引用的链上数据（TVL、市值、供应量）请注明快照时间。

---

## 近 3 年（或自诞生以来）日K 图

![3-Year Daily Candlestick]({daily_chart_relpath})

**走势描述**: {daily_trend_description}

（区间: {period_start} → {period_end}；区间最高 {period_high} {CURRENCY}；区间最低 {period_low} {CURRENCY}）

## 近 3 年 周K 图

![3-Year Weekly Candlestick]({weekly_chart_relpath})

**走势描述**: {weekly_trend_description}

---

## 一、 外部环境 (External Environment)

### 1. 宏观/流动性 (Macro & Liquidity)
- **美联储基准利率 (Fed Funds Rate)：** {当前区间及最近政策方向 — 决定风险资产整体溢价}
- **美元指数 (DXY)：** {当前水平及趋势 — 与加密资产通常负相关}
- **BTC 市占 (Dominance)：** {当前百分比，趋势 — 判断风险偏好在 BTC 还是山寨}
- **加密总市值 (TOTAL)：** {当前水平，90 日变化}
- **稳定币总供应 (USDT + USDC)：** {当前水平，近期增减 — 代表场内购买力}

### 2. 监管与板块 (Regulation & Sector)
- **监管态度：** {美国 SEC / ETF / MiCA 等关键进展}
- **所属板块 TVL / 规模：** {若为 DeFi / L2 / RWA 等，给出板块 TVL 与份额}
- **竞争格局：** {同类主要竞品 + 相对市值排名}

---

## 二、 代币经济学与链上基本面 (Tokenomics & On-chain)

### 1. 代币经济 (Tokenomics)
- **供应：** 流通 {X} / 总量 {X} / 最大 {X}
- **通胀/减半/释放：** {年化通胀率、下一次解锁/减半时间与体量}
- **持仓集中度：** {前 10 地址占比 {X}%；团队 / 基金会 / VC 锁仓情况}

### 2. 链上活跃度 (On-chain Activity)
- **TVL（若适用）：** {X} {CURRENCY}，90 日变化 {+/-X}%
- **活跃地址：** 日活 {X}（7 日均），同比 {+/-X}%
- **交易/费用：** 30 日年化手续费 {X} {CURRENCY}；协议净收入 {X} {CURRENCY}
- **开发者活跃度：** 过去 30 日 GitHub 活跃贡献者 {X}，最近重大升级：{描述}

---

## 三、 市场交易面 (Market & Trading)

### 1. 衍生品与资金 (Derivatives & Flows)
- **永续资金费率：** {+/-X}% 年化（Binance / Bybit 综合）
- **永续未平仓 (OI)：** {X} {CURRENCY}
- **30 日实现波动率：** {X}%
- **现货 ETF 净流入（若为 BTC/ETH）：** 7 日 {+/-X} {CURRENCY}

### 2. 情绪与仓位 (Sentiment & Positioning)
- **交易所净流入：** {+/-X} 个 / 7 日 （负值 = 正在被提到钱包，通常偏多）
- **Coinbase 溢价 / 韩国泡菜溢价：** {+/-X}%
- **分析师/链上研究共识：** {多空倾向，主要目标价（带保留意见）}
```
