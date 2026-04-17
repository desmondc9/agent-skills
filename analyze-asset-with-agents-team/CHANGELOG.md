# Changelog

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
