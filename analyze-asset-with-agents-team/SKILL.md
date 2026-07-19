---
name: analyze-asset-with-agents-team
version: 1.1.0
description: "[DEPRECATED 已废弃 — 请勿使用 / do not use. 本 skill 不再维护，仅保留作历史参考。] Use this skill whenever the user asks to analyze, research, evaluate, or get a recommendation on any investment asset — a publicly listed stock (US NYSE/NASDAQ, HK HKEX, A-share SSE/SZSE), a cryptocurrency or token (BTC, ETH, SOL, DeFi governance tokens, etc.), or a privately held company (Stripe, OpenAI, SpaceX, 字节跳动, etc.) — or mentions such an asset in an investment context. Triggers include: '分析XX股票', 'should I buy NVDA', '值得投资吗', 'analyze AAPL', 'analyze BTC', 'is ETH a buy', 'is Stripe a good investment', '帮我研究一下腾讯', '现在能买XX吗', '字节跳动值不值得买', 'OpenAI估值'. The skill auto-detects asset class, loads the matching profile (asset_profiles/<class>.md) for data sources, macro/fundamental/market queries, and output template, then runs a comprehensive multi-expert workflow: (1) identifies the asset, (2) fetches price history + charts via a per-class Python script (stock via akshare/yfinance, crypto via CoinGecko/Binance; private companies skip this step), (3) gathers MECE baseline data via WebSearch using the profile's query sets, (4) dispatches 6 analyst agents IN PARALLEL — Warren Buffett, Charlie Munger, Cathie Wood, 王煜全 (Wang Yuquan), 招财大牛猫, 段永平 — each applying their framework to this specific asset class and producing independent research + a recommendation, then (5) runs a supervisor agent to synthesize all six perspectives into a final structured report. Do NOT use this skill for non-investment questions about an asset, portfolio optimization, tax advice, or real-time trading signals."
---

# 多资产类别投资多视角分析工作流 (Multi-Asset, Multi-Expert Investment Analysis)

> **⚠️ DEPRECATED / 已废弃**：本 skill 已废弃，不再维护，保留仅供历史参考。请不要用它执行新的分析任务。

You are a professional investment analysis coordinator. Execute the full workflow below for **any investment asset** the user asks about — publicly listed stock, cryptocurrency, or private company. The workflow is **profile-driven**: once you identify the asset class, you load the matching profile file, and that file supplies the class-specific data sources, WebSearch queries, and output template.

**Design note:** This skill bundles 7 analyst personas under `agents/`, one asset-profile markdown per supported class under `asset_profiles/`, and Python data-fetch scripts under `scripts/`. Since the skill is installed standalone (not as a Claude Code plugin), the analyst markdown files are dispatched at runtime by reading each file and passing its body as a prompt to a `general-purpose` Task agent. Asset-profile files are read the same way and their sections (`## macro_queries`, `## basic_data_template`, etc.) guide the step-by-step work.

**Supported asset classes (out of the box):**
- `stock` — US (NYSE/NASDAQ), HK (HKEX), A-share (SSE/SZSE)
- `crypto` — BTC, ETH, SOL, any token with a CoinGecko listing or Binance USDT pair
- `private` — Stripe, OpenAI, SpaceX, ByteDance, other venture-backed or privately held companies

Adding a new class (ETF, commodity, real estate) = drop a new `asset_profiles/<class>.md` file in the same format; no changes needed to this SKILL.md.

**Prerequisites on the host system:**
- `uv` — [astral-sh/uv](https://github.com/astral-sh/uv) (used to run the Python scripts with PEP 723 inline dependencies). Scripts auto-install their deps on first run.

---

## 跨步骤规则：报告输出语言 (Final Report Language — 简体中文)

**Every markdown file produced by this skill — `01_basic_data/basic_data.md`, all files in `02_extra_data/`, all files in `03_answers/`, and `04_summary/summary.md` — MUST be written in 简体中文 (Simplified Chinese).** This applies to every analyst agent and the supervisor.

Rules:
1. **Process is unrestricted, output is Chinese.** Agents may think, plan, search the web, read documents, and call tools in any language they like (English search queries often retrieve better results, that is fine). What matters is the **content of the markdown files written to disk**: every section heading, every prose paragraph, every bullet, every table caption, and every "如果分析师说话" first-person quote MUST be in 简体中文.
2. **Proper nouns and technical terms may stay in their original form.** Tickers (`AAPL`, `00700.HK`, `300750.SZ`), company names (`Apple Inc.`, `Tencent Holdings`), persona names (`Cathie Wood`, `Buffett`), metric abbreviations (`PE`, `PB`, `ROE`, `FCF`, `DCF`, `TAM`, `CAGR`, `TRL`), framework names (`Wright's Law`, `S-curve`), currencies (`USD`, `HKD`, `CNY`), and direct quotes from English-language sources are all fine to leave in English. The surrounding analytical prose is Chinese.
3. **Quoted source material may stay in original language**, but every quote should be followed by a one-line Chinese paraphrase if the original is not Chinese.
4. **Every analyst-agent dispatch prompt and the supervisor dispatch prompt must restate this rule explicitly**, alongside the currency rule below.

---

## 跨步骤规则：货币单位统一 (Currency-Unit Consistency)

**In every file produced by this skill, every monetary value MUST be explicitly labeled with its currency** (USD / HKD / CNY / etc.). The report's **primary currency** (`CURRENCY`) is determined in Step 1 from the asset profile: stocks → trading currency of the primary listing; crypto → `USD`; private companies → usually `USD` for US companies, confirm for non-US.

Rules:
1. All prices, market caps, revenue, FCF, target prices, valuations, funding rounds, TVL, etc. must carry an explicit currency suffix — e.g. `175.23 USD`, `¥2,145 亿 CNY`, `HK$ 420.5`, `95,000 USD` (for BTC).
2. If a source cites a different currency (e.g. a Wall Street estimate for a HK company quoted in USD, or a Chinese private company round quoted in CNY while the report uses USD), **convert to the primary currency** and note the conversion: `折合 USD ~= 22.40 (汇率 7.82, 2026-04-16)`.
3. Never mix currencies implicitly in the same table or sentence without explicit labels.
4. **For cross-listed stocks (see next rule), normalize all comparable metrics to a single currency for the cross-market comparison table — preferred order: CNY for primarily-China-revenue businesses, USD otherwise.** Always disclose the FX rate and the as-of date.
5. Every analyst agent and the supervisor must follow this rule. Pass the primary currency and the requirement explicitly in their prompts.

---

## 跨步骤规则：跨市场上市处理 (Cross-Listed Stocks — A股 / 港股 / 美股 ADR)

When `ASSET_CLASS = stock`, many companies are listed on **more than one exchange** (e.g. 宁德时代 `300750.SZ` + `03750.HK`; 比亚迪 `002594.SZ` + `01211.HK`; 阿里巴巴 `BABA` NYSE + `09988.HK`; 京东 `JD` NASDAQ + `09618.HK`; 中国人寿 `601628.SS` + `02628.HK` + `LFC` NYSE). The skill MUST detect these cases and analyze **all listings together**.

Rules:
1. **Detect cross-listing during Step 1c** via WebSearch (`<ASSET_NAME> dual listing A股 H股`, `<ASSET_NAME> ADR HKEX SSE SZSE`). If only one listing exists, set `IS_CROSS_LISTED = false` and proceed normally.
2. **If cross-listed**, populate a `LISTINGS` array — one entry per market — with `{ASSET_ID, ASSET_VENUE, MARKET, CURRENCY}`. Pick a `PRIMARY_VENUE` (default: home market — A-share for mainland-China companies, US for US companies — confirm via market-cap weight if ambiguous). The report's `CURRENCY` field is the primary venue's trading currency.
3. **Step 3 fetches price + chart data from EVERY listing in `LISTINGS`** — invoke the data-fetch script once per market (run them in parallel). Each listing produces its own `current_price` / `as_of_date` / `daily_chart_relpath` / `weekly_chart_relpath`. Charts are stored under `01_basic_data/assets/` with the market suffix in the filename (the script already namespaces by ticker, so no changes are needed beyond multiple invocations).
4. **Step 4 adds cross-market queries** (see `stock.md` profile `## market_queries`) — A/H premium-discount, ADR-vs-local arbitrage, liquidity (ADTV) comparison, southbound/northbound flow direction.
5. **Step 5's `basic_data.md` includes a "跨市场对比" section** showing each listing's price, P/E, P/B, ADTV, market cap (all normalized to ONE currency — typically CNY or USD, with FX rate noted), and the implied A/H or ADR premium-discount.
6. **Step 6 dispatches each analyst with the full `LISTINGS` context, not just one ticker.** Each analyst forms ONE consolidated view of the underlying business but must comment on whether one listing is materially cheaper, more liquid, or more accessible to the user's likely venue. The currency rule kicks in: every cross-market money figure carries its currency tag.
7. **Step 7's supervisor MUST produce an explicit "跨市场首选 (Preferred Venue)" recommendation** in the final summary — naming which listing offers better investment value and explaining the reason (cheaper valuation / better liquidity / lower friction / regulatory access / dividend tax). If listings are roughly equivalent, say so explicitly with the trade-offs.
8. If `IS_CROSS_LISTED = false`, skip the cross-market sections entirely (do NOT pad with "N/A" stubs).

---

## 步骤一：识别投资标的 (Asset Identification)

### 1a. Detect `ASSET_CLASS`

Pick one of `stock` / `crypto` / `private` based on the user's question:

- **stock** — user mentions a ticker pattern (`AAPL`, `NVDA`, `00700`, `00700.HK`, `600519`, `600519.SS`), names a well-known public company (Apple, Tesla, 腾讯, 茅台), or uses the word "stock" / "股票" / "A股" / "港股" / "美股".
- **crypto** — user mentions a crypto symbol (`BTC`, `ETH`, `SOL`, `DOGE`), uses words like "crypto" / "coin" / "token" / "加密货币" / "币" / "链" / "DeFi" / "L2", or references an L1/L2 protocol.
- **private** — user mentions a known privately held company (Stripe, OpenAI, SpaceX, xAI, Anthropic, 字节跳动/ByteDance, SHEIN), uses phrases like "private company" / "pre-IPO" / "startup" / "unicorn" / "未上市" / "一级市场" / "估值", or names a company with no public ticker.

**If ambiguous** (e.g. the user just says "analyze ETH" — could be Ethereum the coin or a less-famous namesake; or says "analyze Palantir" — Palantir was private until 2020 but the user may mean the public stock today), ask the user to clarify **before** proceeding.

### 1b. Load the asset profile

Read the matching profile file:

```
<skill-dir>/asset_profiles/<ASSET_CLASS>.md
```

Where `<skill-dir>` is typically `~/.claude/skills/analyze-asset-with-agents-team/`. Treat the profile's `## identification` section as authoritative for how to resolve the asset.

### 1c. Resolve and record asset variables

Following the profile's `## identification` guidance, use WebSearch to confirm the asset and fill in this **unified variable set** that every downstream step reads:

- `ASSET_CLASS` — `stock` / `crypto` / `private`
- `ASSET_ID` — canonical identifier of the **primary listing** (`AAPL`, `00700.HK`, `600519.SS`, `BTC`, `ETH`, `stripe`, `openai`)
- `ASSET_NAME` — full human-readable name
- `ASSET_VENUE` — exchange / chain / domicile of the primary listing (see profile)
- `CURRENCY` — primary reporting currency (the primary listing's trading currency for stocks)
- Any **class-specific helper vars** defined in the profile:
  - stock → `TICKER`, `MARKET` (`US` / `HK` / `A`); plus cross-listing vars (see below)
  - crypto → `COIN_ID` (CoinGecko), `SYMBOL`
  - private → no helper vars; valuation data comes from WebSearch only

**For `ASSET_CLASS = stock`, also resolve cross-listing variables (see "跨市场上市处理" rule above):**

- `IS_CROSS_LISTED` — `true` if the same company has more than one public listing, else `false`. Determine via WebSearch (`<ASSET_NAME> dual listing A H share`, `<ASSET_NAME> ADR HKEX`).
- `LISTINGS` — array of `{ticker, market, venue, currency}` for every public listing of the same underlying company. For a single-listing stock, this array has one entry. For 宁德时代, it has two (`{300750, A, SZSE, CNY}` and `{03750, HK, HKEX, HKD}`). For 阿里巴巴, two (`{BABA, US, NYSE, USD}` and `{09988, HK, HKEX, HKD}`).
- `PRIMARY_VENUE` — the `LISTINGS` entry chosen as the primary one (use home market by default; for ambiguous cases, the listing with the larger market cap / ADTV).

If multiple **distinct companies** match the user's input (e.g. "Tesla" might mean a Chinese namesake on SZSE), ask for clarification before proceeding. If the user names a single company that happens to be cross-listed, **do not** ask which market to use — analyze all and recommend a preferred venue in the final report.

Note: `CURRENT_PRICE` is **not** set here — it is fetched by the profile's data script in Step 3 (for `stock` and `crypto`) or by WebSearch from primary funding sources (for `private`).

---

## 步骤二：时间戳、工具/模型标识、BASE_DIR

### 2a. 获取时间戳 (UTC+8)

```bash
TZ='Asia/Shanghai' date '+%Y-%m-%d_%H:%M:%S'
```

Record as `TIMESTAMP` (for filenames, e.g. `2026-04-17_10:45:00`). Also:

```bash
TZ='Asia/Shanghai' date '+%Y-%m-%d %H:%M:%S'
```

Record as `DISPLAY_TIMESTAMP` (for file contents).

### 2b. 确定 TOOL_NAME 和 MODEL_NAME

These tag the output directory so the user can tell which CLI + model produced the analysis.

- `TOOL_NAME`: the CLI tool running this skill. Use a filesystem-safe lowercase slug.
  - Claude Code CLI → `claude-code`
  - Kimi CLI / Kimi Code → `kimi-code`
  - OpenAI Codex CLI → `codex-cli`
  - Unknown → `default`
- `MODEL_NAME`: the model identifier. Use a filesystem-safe lowercase slug.
  - Examples: `sonnet-4.6`, `opus-4.6`, `haiku-4.5`, `k-2.5`, `gpt-5-codex`
  - Unknown → `default`

Sanitize both: lowercase, keep only `[a-z0-9.-]`, replace other chars with `-`, collapse repeats.

### 2c. 生成 QUERY_SLUG

Short filesystem-safe English/pinyin slug derived from the user's question: core keywords only, `[a-z0-9-]`, ≤40 chars.

| 用户输入 | QUERY_SLUG |
|---------|-----------|
| 帮我分析一下苹果公司值不值得买 | `analyze-apple-aapl` |
| analyze NVDA for me | `analyze-nvda` |
| 腾讯现在能买吗？ | `analyze-tencent-00700hk` |
| analyze BTC | `analyze-btc` |
| Is ETH a buy right now? | `analyze-eth` |
| 字节跳动值不值得买 | `analyze-bytedance` |
| Is Stripe a good investment? | `analyze-stripe` |

### 2d. BASE_DIR

```
BASE_DIR = {TIMESTAMP}_{QUERY_SLUG}_{TOOL_NAME}_{MODEL_NAME}
```

Examples:
- `2026-04-17_10:45:00_analyze-apple-aapl_claude-code_sonnet-4.6`
- `2026-04-17_10:45:00_analyze-btc_claude-code_sonnet-4.6`
- `2026-04-17_10:45:00_analyze-stripe_claude-code_sonnet-4.6`

Create the directory tree:

```bash
BASE_DIR="{TIMESTAMP}_{QUERY_SLUG}_{TOOL_NAME}_{MODEL_NAME}"
mkdir -p "${BASE_DIR}/01_basic_data/assets" \
         "${BASE_DIR}/02_extra_data" \
         "${BASE_DIR}/03_answers" \
         "${BASE_DIR}/04_summary"
```

All subsequent paths are relative to `{BASE_DIR}/`. For `ASSET_CLASS = private`, the `01_basic_data/assets/` directory may end up empty (no charts are generated); leave it in place for consistency.

---

## 步骤三：获取价格与走势图（Profile-Driven Data Fetch）

Look up the **`## data_fetch_command`** section in the asset profile loaded in Step 1b and execute it. The profile tells you which script to run (if any), what arguments to pass, and which JSON fields to capture.

- `stock` → runs `scripts/fetch_stock_data.py` (akshare → yfinance fallback) and writes 3Y daily + weekly K-line PNGs. **If `IS_CROSS_LISTED = true`, run the script ONCE PER LISTING in `LISTINGS` (in parallel where possible).** Capture each listing's JSON output into a per-listing record. The K-line filenames already include the ticker, so charts from different markets do not collide.
- `crypto` → runs `scripts/fetch_crypto_data.py` (CoinGecko → Binance fallback) and writes 3Y daily + weekly candlestick PNGs.
- `private` → **no script is run.** Fill `CURRENT_PRICE` / `PRICE_AS_OF` / `data_source` from WebSearch on primary funding rounds per the profile's `## data_fetch_command` instructions.

Standard JSON fields returned by the fetch scripts (both stock and crypto use the same schema):

- `current_price` → `CURRENT_PRICE`
- `as_of_date` → `PRICE_AS_OF`
- `daily_chart_relpath`, `weekly_chart_relpath` → paths used inside the markdown
- `daily_trend_description`, `weekly_trend_description` → pre-generated trend text
- `data_source` → `akshare` / `yfinance` / `coingecko` / `binance`
- `period_start`, `period_end`, `period_high`, `period_low` — all in `CURRENCY`

If the script exits non-zero or returns `{"error": ...}`, fall back to WebSearch for the current price and skip chart embedding, but continue the rest of the workflow. Note the degradation in the report.

---

## 步骤四：收集 MECE 基础数据 (Profile-Driven WebSearch)

Open the asset profile loaded in Step 1b and run an independent WebSearch (or WebFetch for detail pages) per item in these three sections:

- `## macro_queries` — external environment (rates, liquidity, sector health, regulation)
- `## fundamental_queries` — what the asset is worth intrinsically (earnings/moat for stocks; tokenomics + on-chain for crypto; funding history + business metrics for private)
- `## market_queries` — how the market is currently priced and positioned (valuation multiples, flows, sentiment)

Substitute placeholder variables (`<ASSET_ID>`, `<ASSET_NAME>`, `<industry>`, `<SYMBOL>`, etc.) from the Step 1c variable set before issuing each query.

Tag every monetary value you extract with its original currency, and convert to `CURRENCY` where needed (see the currency-consistency rule at the top).

---

## 步骤五：保存基础数据文件 (Profile-Driven Template)

Find the **`## basic_data_template`** section in the asset profile. That markdown block is your output template. Fill in the Step 1c variables + Step 3 fetch results + Step 4 WebSearch findings, then save to:

```
{BASE_DIR}/01_basic_data/basic_data.md
```

(`BASE_DIR` already encodes `{TIMESTAMP}_{QUERY_SLUG}_{TOOL_NAME}_{MODEL_NAME}`, so inner filenames stay short.)

For `ASSET_CLASS = stock` and `ASSET_CLASS = crypto`, this includes the two K-line / candlestick PNGs from Step 3. For `ASSET_CLASS = private`, the template replaces charts with a **funding-timeline table** — no image embedding is expected.

---

## 步骤六：并行派发 6 个分析师 Agent

**⚠️ CRITICAL: Dispatch all 6 analyst agents IN PARALLEL in a single message (multiple Task tool calls in one response). Do NOT wait for one to finish before the next.**

### How to dispatch each analyst

For each of the 6 analysts:

1. Read `<skill-dir>/agents/<analyst-name>.md`. The skill dir is typically `~/.claude/skills/analyze-asset-with-agents-team/`.
2. Strip the frontmatter (between the first `---` and the second `---`). Keep the body as the persona prompt.
3. Launch a `general-purpose` Task agent with a prompt containing:
   - The full persona body as role/system context
   - The user's original question
   - Basic data file path: `{BASE_DIR}/01_basic_data/basic_data.md`
   - **Asset metadata (class-aware)**:
     - `ASSET_CLASS` — `stock` / `crypto` / `private` (**always include** — agents will adapt their framework based on this)
     - `ASSET_ID`, `ASSET_NAME`, `ASSET_VENUE`
     - `CURRENT_PRICE {CURRENCY}` (for private companies pass "last-round implied price {CURRENCY}" or "N/A" with the latest post-money valuation and date)
     - `PRICE_AS_OF`, `TIMESTAMP`
   - **For `ASSET_CLASS = stock`**, also pass:
     - `IS_CROSS_LISTED` (`true` / `false`)
     - `LISTINGS` — full array; for each entry include `ticker`, `market`, `venue`, `currency`, `current_price`, `as_of_date`
     - `PRIMARY_VENUE` — which entry to treat as the primary listing
     - **Cross-listing instruction (only when `IS_CROSS_LISTED = true`):** "Form ONE consolidated view of the underlying business. In the answer file, dedicate one subsection to comparing the listings — which is materially cheaper / more liquid / better for a typical investor — and feed your venue preference (or no preference, with reasons) up to the supervisor."
   - **Output language rule (restate explicitly):** "Your final answer file MUST be written in 简体中文. Tickers, persona names, metric abbreviations (PE, ROE, FCF, DCF, TAM, CAGR, TRL), and direct English quotes are fine; everything else — section prose, bullets, table captions, your first-person 'if I spoke' quote — is Simplified Chinese. Process language (search queries, tool calls, internal thinking) is unrestricted."
   - **Currency rule (restate explicitly):** primary currency is `{CURRENCY}`; every monetary value must be explicitly labeled with currency; non-primary currencies must be converted with a noted exchange rate. For cross-listed stocks, normalize the cross-market comparison table to a single currency (CNY for primarily-China-revenue companies, USD otherwise) and disclose the FX rate.
   - Output paths (use the analyst short name, i.e. filename stem of the agent .md):
     - Extra research data → `{BASE_DIR}/02_extra_data/<analyst-name>.md` (e.g. `buffett-analyst.md`)
     - Investment opinion → `{BASE_DIR}/03_answers/<analyst-name>.md`

### The 6 analysts (dispatch all in parallel)

| Agent file | Perspective |
|------------|-------------|
| `agents/buffett-analyst.md` | Warren Buffett — value, moats, intrinsic value, margin of safety |
| `agents/munger-analyst.md` | Charlie Munger — mental models, inversion, psychology of misjudgment |
| `agents/cathie-wood-analyst.md` | Cathie Wood — disruptive innovation, Wright's Law, 5-year targets |
| `agents/wang-yuquan-analyst.md` | 王煜全 — global tech transfer, China industrial clusters, TRL, geopolitics |
| `agents/zhaobi-daniucat-analyst.md` | 招财大牛猫 — A/HK retail tactics, technical + fundamental hybrid |
| `agents/duan-yongping-analyst.md` | 段永平 — stop doing list, business essence, management integrity, patience |

**Agents will adapt to `ASSET_CLASS` themselves** (see the "Asset-class adaptation" paragraph at the top of each agent body). For crypto and private companies, expect some analysts to explicitly note "outside my circle of competence" or "my framework barely applies here" — that is valuable signal for the supervisor, not a failure mode.

---

## 步骤七：派发 Supervisor Agent

Once all 6 analyst agents complete:

1. Read `<skill-dir>/agents/supervisor-analyst.md`, strip frontmatter.
2. Launch one `general-purpose` Task agent with:
   - The supervisor persona body
   - User's original question
   - `ASSET_CLASS`, `ASSET_ID`, `ASSET_NAME`, `ASSET_VENUE`, `CURRENT_PRICE {CURRENCY}` (or "N/A — last-round valuation" for private), `PRICE_AS_OF`
   - **For `ASSET_CLASS = stock`**: also pass `IS_CROSS_LISTED`, the full `LISTINGS` array (with each listing's ticker / venue / currency / current price / ADTV / market cap), and `PRIMARY_VENUE`.
   - **Output language rule (restated):** "The summary file MUST be written in 简体中文. Tickers, persona names, metric abbreviations, and direct English quotes are fine; analytical prose, headings, and recommendations are Simplified Chinese."
   - **Currency rule (restated):** primary currency `{CURRENCY}`; all money values explicitly labeled and consistent. For cross-listed stocks, the cross-market comparison table normalizes to one currency (CNY for primarily-China-revenue businesses, USD otherwise) and discloses the FX rate.
   - **Cross-listing instruction (only when `IS_CROSS_LISTED = true`):** "The summary MUST contain a section titled `## 跨市场首选 (Preferred Venue Recommendation)` that names which listing offers better investment value and explains the reason — typically one of: 估值更低 (lower P/E, P/B, or A/H discount), 流动性更好 (higher ADTV, narrower bid-ask), 更具性价比 (better risk-adjusted entry), 投资者准入便利 (regulatory or tax friction for the user's likely venue), 股息税差 (dividend withholding-tax difference). If two listings are roughly equivalent, say so explicitly and list the trade-offs."
   - Paths to all 6 analyst answer files in `{BASE_DIR}/03_answers/` (e.g. `buffett-analyst.md`, `munger-analyst.md`, …)
   - Timestamp `TIMESTAMP`, tool `TOOL_NAME`, model `MODEL_NAME`
   - Output: `{BASE_DIR}/04_summary/summary.md`
   - **Reminder to handle missing perspectives gracefully:** for cryptos and private companies, some technical / market-flow sections may be absent or "N/A"; that is expected and should be noted rather than filled with speculation.

---

## 步骤八：展示最终总结

Read `{BASE_DIR}/04_summary/summary.md` and display the full contents to the user.

---

## 错误处理

- If an analyst agent fails, record the error, continue, and note the missing perspective in the final summary.
- If the Python data script fails (e.g. network issue), fall back to WebSearch-based current price and skip chart embedding; note the degraded state in the report.
- If WebSearch returns no data for a sub-item, fill with 「数据暂时无法获取，建议查阅专业金融数据库」.
- If the user's input is ambiguous (e.g. asset class unclear, or multiple assets share the same name), confirm identity first before proceeding.
- If the user's asset doesn't cleanly fit any supported class (ETF, commodity futures, real-estate fund, etc.), tell them which classes are currently supported and ask how they'd like to proceed — **do not** silently bucket it into a wrong class.

---

## Disclaimer

This skill produces AI-generated analysis for informational purposes only. It is not investment advice. Users should conduct their own due diligence and consult a qualified financial advisor before any investment decision.
