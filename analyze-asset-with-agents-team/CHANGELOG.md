# Changelog

## v1.1.0 — 2026-05-01

Two cross-cutting changes that apply across every agent and the orchestrator.

### Added

- **跨步骤规则：报告输出语言** — every markdown file produced by the skill (`01_basic_data/basic_data.md`, `02_extra_data/*.md`, `03_answers/*.md`, `04_summary/summary.md`) MUST be written in 简体中文. Process language (search queries, internal reasoning, tool calls) remains unrestricted, so analysts can still query English-language sources for better retrieval. Tickers, persona names, metric abbreviations, and direct English quotes stay in original form. Rule is restated explicitly in every analyst dispatch and the supervisor dispatch in `SKILL.md`, plus a short reminder block in each of the 7 agent files.
- **跨步骤规则：跨市场上市处理 (Cross-Listed Stocks)** — when the asset is a stock with multiple public listings (A股+H股, ADR+H股, A股+H股+ADR), the skill now:
  - Detects cross-listings during Step 1c via WebSearch and populates `IS_CROSS_LISTED`, `LISTINGS` (array), and `PRIMARY_VENUE` variables.
  - Invokes `fetch_stock_data.py` once per listing in Step 3 (parallel where possible).
  - Adds cross-market `market_queries` to `stock.md` profile (A/H premium-discount, ADR arbitrage, southbound/northbound flow, dividend tax, ADTV liquidity comparison).
  - Renders a `## 跨市场对比` block in `basic_data.md` with all listings normalized to one currency (CNY or USD with FX rate disclosed) plus per-market K-line charts.
  - Each analyst forms ONE consolidated business view and adds a `### 跨市场观察` subsection comparing the listings on their own framework's terms (margin-of-safety, latticework, Wright's-Law IRR, 产业链, 大道至简, 板块轮动+资金面).
  - Supervisor MUST output a `## 跨市场首选 (Preferred Venue Recommendation)` section naming which listing offers better investment value (估值更低 / 流动性更好 / 性价比更高 / 投资者准入便利 / 股息税差) or stating the listings are equivalent with the trade-offs.
- `stock.md` profile gains an `## identification` cross-listing detection block with a reference table of common patterns (宁德时代, 比亚迪, 阿里巴巴, 京东, 中国人寿, 招商银行, 中国平安, etc.).

### Changed

- `SKILL.md` Step 1c: stocks now resolve `LISTINGS` / `IS_CROSS_LISTED` / `PRIMARY_VENUE` in addition to the primary identifier.
- `SKILL.md` Step 3: stock data fetch is iterated per listing when cross-listed.
- `SKILL.md` Step 6: analyst dispatch prompt now passes `LISTINGS`, `IS_CROSS_LISTED`, `PRIMARY_VENUE`, and the output-language rule.
- `SKILL.md` Step 7: supervisor dispatch passes the cross-listing context plus the cross-market recommendation requirement.
- `supervisor-analyst.md` output template adds a conditional `## 跨市场首选` section between `## 五、综合投资建议` and `## 六、免责声明`.

### Behavior

- Single-listing stocks (e.g. 茅台 `600519.SS` only): unchanged behavior. Cross-listing sections are entirely omitted (no empty stubs).
- Crypto and private companies: unchanged — neither output-language nor cross-listing rules add new content for them beyond the language rule, since cross-listing is stock-specific.

## v1.0.0 — 2026-04-17

First release of the generalized multi-asset skill (renamed from `analyze-stock-with-agents-team`).

**Supported asset classes:** publicly listed stocks (US / HK / A-share), cryptocurrencies, and privately held companies.

### Added

- Pluggable `asset_profiles/` layer — one markdown file per asset class (`stock.md`, `crypto.md`, `private.md`) supplying identification rules, data-fetch command, macro/fundamental/market WebSearch queries, and the basic_data.md output template. Adding a 4th class is a copy-one-file operation.
- `scripts/fetch_crypto_data.py` — CoinGecko primary + Binance fallback. Emits the same JSON contract as `fetch_stock_data.py` and renders 3Y daily + weekly candlestick PNGs via `mplfinance`.
- `SKILL.md` Step 1 now detects `ASSET_CLASS` (`stock` / `crypto` / `private`) from the user's query; Steps 3–5 are profile-driven.
- All 6 analyst agents + supervisor received a bilingual "资产类别适应说明" paragraph telling them to apply their framework honestly across asset classes (e.g. Buffett on crypto should explain what the asset lacks; Cathie Wood on a private AI co. should apply Wright's Law to cost curves; 招财大牛猫 on a private company should note "N/A — no public market data").
- Supervisor handles missing-perspective cases (e.g. no technicals for private companies) without fabricating data.

### Changed

- Skill directory renamed: `analyze-stock-with-agents-team/` → `analyze-asset-with-agents-team/`.
- Analyst answer-file headers generalized: `STOCK_CODE` / `COMPANY_NAME` / `股票价格` replaced with `ASSET_CLASS` / `ASSET_ID` / `ASSET_NAME` / `当前价格`.
- `scripts/fetch_stock_data.py` gained an optional `--asset-class` flag for CLI symmetry with the crypto fetcher (default `stock`, behaviour unchanged).
