# desmondc9-agent-skills

A collection of Claude Code skills for document processing, investment analysis, and productivity workflows.

## Skills 

### [markdown-to-docx](./markdown-to-docx/)

Converts any Markdown file to a professionally formatted Word document (`.docx`).

**Features:**
- Native Word Table of Contents (auto-updates in Word)
- Mermaid diagrams rendered to high-resolution PNG and embedded
- Tables with styled header rows, alternating shading, and borders

**Install:**
```bash
npx skills add desmondc9/agent-skills@markdown-to-docx -g
```

**Prerequisites:** `pandoc`, `mmdc` (Mermaid CLI), `python-docx`, `chromium-browser`

See the [skill README](./markdown-to-docx/SKILL.md) for full usage and troubleshooting.

---

### [analyze-asset-with-agents-team](./analyze-asset-with-agents-team/)

Runs a comprehensive multi-expert investment analysis across **any asset class** — publicly listed stocks (US / HK / A-share), cryptocurrencies (BTC, ETH, SOL, any token), or privately held companies (Stripe, OpenAI, SpaceX, 字节跳动) — using 6 parallel analyst personas plus a synthesis supervisor.

**Features:**
- Auto-detects asset class (`stock` / `crypto` / `private`) from the user's query and loads the matching **asset profile** (`asset_profiles/<class>.md`)
- Per-class data fetch:
  - Stocks → 3Y daily + weekly K-line charts via `akshare` / `yfinance` + `mplfinance`
  - Crypto → 3Y daily + weekly candlesticks via CoinGecko + Binance fallback
  - Private companies → funding-timeline table + comparable-company multiples (no chart)
- Gathers MECE baseline data per class: macro context, fundamentals/tokenomics/funding history, and market/on-chain/liquidity signals
- Dispatches 6 analyst agents **in parallel**, each applying their framework honestly to the given asset class:
  - 🔴 **Warren Buffett** — value investing, economic moats, margin of safety
  - 🟣 **Charlie Munger** — mental models, inversion, psychology of misjudgment
  - 🔵 **Cathie Wood** — disruptive innovation, Wright's Law, 5-year targets
  - 🟢 **王煜全** — global tech transfer, China industrial clusters, geopolitics
  - 🟡 **招财大牛猫** — A/HK market tactics, technical + fundamental hybrid
  - 🟠 **段永平** — stop-doing list, business essence, management integrity
- **Supervisor agent** synthesizes all six perspectives into a structured final report, with graceful handling of class-specific gaps (e.g. technicals are "N/A" for private companies)
- Every run saves to a timestamped folder: `01_basic_data/`, `02_extra_data/`, `03_answers/`, `04_summary/`
- Extensible: adding a 4th asset class (ETF, commodity, real estate) is a single new file in `asset_profiles/`

**Install:**
```bash
npx skills add desmondc9/agent-skills@analyze-asset-with-agents-team -g
```

**Usage:** Just ask naturally — the skill auto-triggers on investment-analysis intent across any supported asset class:

```
# Stocks
帮我分析一下苹果公司值不值得买
analyze Tesla stock for me
腾讯现在能买吗？
Should I buy NVDA now?

# Crypto
analyze BTC
is ETH a good long-term hold?
SOL 还值得买吗？

# Private companies
Is Stripe a good investment?
OpenAI 的估值合理吗？
analyze SpaceX as a private investment
字节跳动值不值得买
```

**Prerequisites:** `uv` for running the bundled Python data-fetch scripts (stock and crypto fetchers). Otherwise a Claude Code environment with `WebSearch`, `WebFetch`, `Bash`, and `Task` tools enabled.

See the [skill README](./analyze-asset-with-agents-team/SKILL.md) for the full profile-driven workflow and agent personas.

**Disclaimer:** AI-generated analysis for informational purposes only. Not investment advice.

---

### [deep-company-analysis](./deep-company-analysis/)

Generates a structured deep-dive research report on any **company, stock, or crypto project** from both **growth and value investing** perspectives. Uses an 8-dimension framework covering industry dynamics, management quality, financials, growth drivers, valuation, policy & geopolitics, technology disruption risks, and a crypto-specific appendix.

**Features:**
- Executive Summary that identifies the 5 highest-impact dimensions with quantitative evidence and tracking KPIs
- Dual-lens analysis: every dimension examined from both growth-investing and value-investing angles
- Strict output discipline: no "buy/sell/hold" recommendations; all data sourced; speculative claims marked; inapplicable dimensions explicitly labeled
- Competitive benchmarking against peers and industry medians for all key metrics
- 3-year / 5-year / 10-year trend analysis (or actual history if < 10 years)
- Dedicated crypto appendix (tokenomics, on-chain metrics, governance risks, MEV, regulatory status) when analyzing blockchain/Web3 projects
- Per-dimension 200-word summaries + a 12-month "综合观察清单" of trackable catalysts

**Install:**
```bash
npx skills add desmondc9/agent-skills@deep-company-analysis -g
```

**Usage:** Just ask naturally — the skill auto-triggers on deep-research intent:

```
深度分析一下腾讯
帮我调研一下 NVDA
research Apple as a long-term investment
OpenAI 的基本面怎么样
analyze ETH from a fundamentals perspective
```

**Prerequisites:** A Claude Code environment with `WebSearch` and `WebFetch` tools enabled.

See the [skill README](./deep-company-analysis/SKILL.md) for the full workflow and [REFERENCE.md](./deep-company-analysis/REFERENCE.md) for the complete 8-dimension analysis template.

---

## License

Apache 2.0 — see [LICENSE](./LICENSE).
