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

### [analyze-asset-with-agents-team](./analyze-asset-with-agents-team/) — ⚠️ DEPRECATED

> **已废弃，不再维护。** 保留仅供历史参考，请勿用于新的分析任务。

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

### [transcribing-meeting-recordings](./transcribing-meeting-recordings/)

Converts any meeting recording (`.mp4` / `.mov` / `.mkv` / `.wav` / `.m4a` / `.mp3`) into a cleaned, timestamped **SRT transcript with real participant names** — especially Chinese / multilingual content. Combines **whisperx** (faster-whisper + alignment + pyannote diarization) with a Microsoft Teams / Zoom **video-frame trick**: the active-speaker banner in the recording is read off the frame, letting you map anonymized `SPEAKER_XX` clusters onto the real names of the people in the call.

**Features:**
- Single-pass whisperx pipeline: ASR (large-v3) + word-level alignment + pyannote speaker diarization, tuned to fit **8 GB GPUs** (`--compute_type int8 --batch_size 4`)
- Post-processor (`make_srt.py`) that strips Whisper's YouTube-training hallucinations (`请不吝点赞订阅...`), spaces CJK/ASCII boundaries (`shipment加A` → `shipment 加 A`), smooths short diarization "flake" cues, and merges consecutive same-speaker cues
- **Speaker identification via video frames** — extract one frame per `SPEAKER_XX` at a clean utterance, read the Teams / Zoom active-speaker banner, fill in a markdown mapping table; the SRT then carries real names
- Handles pyannote **over-segmentation** (one person split into 2+ clusters) by collapsing duplicate names during merge
- Per-meeting `speakers.md` mapping + parent-folder `speakers.md` roster pattern for **cross-meeting** name tracking (pyannote labels are not stable across recordings; aliases incl. Whisper Chinese-name homophones are recorded)
- Captures every failure mode encountered in practice — Python 3.14 / torchaudio incompatibility, 3 separate Hugging Face license walls, CUDA OOM at default batch size, Whisper hallucinations during silence — so the next run avoids them

**Install:**
```bash
npx skills add desmondc9/agent-skills@transcribing-meeting-recordings -g
```

**Usage:** Drop a recording into a folder, then:

```bash
ffmpeg -i meeting.mp4 -vn -ac 1 -ar 16000 -c:a pcm_s16le audio.wav
whisperx audio.wav --model large-v3 --language zh --diarize \
  --diarize_model pyannote/speaker-diarization-3.1 \
  --compute_type int8 --batch_size 4 --output_format json
cp <skill>/templates/speakers.template.md ./speakers.md
python3 <skill>/scripts/make_srt.py   # → transcript.srt
```

Then for each `SPEAKER_XX`, extract a frame (`ffmpeg -ss <t> -i meeting.mp4 -frames:v 1 spk_XX.jpg`), read the Teams banner, fill in the name in `speakers.md`, and re-run `make_srt.py`.

**Prerequisites:** `ffmpeg`, Python 3.11 (**not 3.14** — torchaudio incompatibility), `uv tool install whisperx --python 3.11`, an NVIDIA GPU (≥ 6 GB recommended), and acceptance of three pyannote gated repos on Hugging Face (`speaker-diarization-3.1`, `segmentation-3.0`, `speaker-diarization-community-1`).

See the [skill README](./transcribing-meeting-recordings/SKILL.md) for the full pipeline, prerequisites, and the Common Mistakes table.

---

### [analyze-value](./analyze-value/)

Estimates the **intrinsic value** of a company, stock, or cash-flow-generating asset (commercial real estate, 收租物业) using the valuation methodology from 吴军《财商训练课·企业估值》: **ignore cost and historical price — value only depends on how much free cash flow the asset will keep producing, and how risky that is.** Implements risk-adjusted discounted cash flow (DCF) with a CAPM-style β discount, plus a baseline check for risky fixed-income (理财 / 票据 / 债券) against the risk-free deposit rate.

**Features:**
- Risk-adjusted DCF: `Value = Σ FCFₜ / [1 + r + β·(rm − r)]ᵗ` — higher risk (β) discounts harder, lowering valuation
- Free-cash-flow based, **not** net profit (易造假、要再投入), and **cost-blind** (固定资产/历史造价/历史股价 don't enter the formula)
- `dcf_valuation.py` script outputs per-year discounted FCF, ΣDCF, and valuation under **two conventions** (standard present-value, and 吴军's equivalent-deposit-principal), validated against the article's worked examples
- Expected-return mode for risky fixed income: probability-weighted payoff discounted back and compared to the bank baseline
- Commercial-real-estate guidance (supply/demand already lives in the FCF; self-occupied homes excluded)
- Discipline: gives a valuation **range with β / growth sensitivity**, labels currency and assumptions, no buy/sell calls — 追求方向性正确，不追求精确

**Install:**
```bash
npx skills add desmondc9/agent-skills@analyze-value -g
```

**Usage:** Ask naturally — the skill auto-triggers on valuation intent:

```
这家公司值多少钱？帮我估个值
用 DCF 给宁德时代估值
NVDA 现在是高估还是低估？
帮我看看这个商铺值不值这个价
这份年化 5% 的理财，相对存银行到底值多少？
```

**Prerequisites:** Python 3 (standard library only — no extra packages). `WebSearch` / `WebFetch` recommended for gathering the cash-flow inputs.

See the [skill README](./analyze-value/SKILL.md) for the workflow and [REFERENCE.md](./analyze-value/REFERENCE.md) for the full method, formulas, and the article's worked examples.

---

### [analyze-dip](./analyze-dip/)

Judges whether a **sharp crash / big pullback** in a stock, cryptocurrency, or other asset is a **buy-the-dip opportunity or a time to exit**, using the 10-step framework from the video 《AI硬件股暴跌，现在该抄底还是逃命？我的10步判断框架》 (Micron as the running case). The core discipline: never judge by *how much it dropped* or *whether the news sounds good/bad* — distinguish **「跌的是情绪」 from 「跌的是基本面/盈利逻辑」**.

**Features:**
- 10-question checklist, one key question per step: earnings-logic revisions (EPS revision), multi-model fair value (DCF + multiples), collective analyst re-pricing, growth quality (revenue/EPS growth, margins, key businesses like HBM), free-cash-flow trend, industry-level change, moat depth, balance-sheet safety, fundamentals-vs-sentiment, and the final **empty-position test** ("if I held none today, would I buy at this price?")
- Gate logic: if step 1 (earnings logic) fails, the rest don't matter — the framework says exit, not dip-buy
- Crypto adaptation table mapping each step's stock metrics to on-chain/protocol equivalents (fee revenue, NVT, MVRV, treasury runway, token unlocks)
- Structured output: a 10-step evidence matrix (✅/⚠️/❌) plus a directional verdict — 偏抄底（情绪错杀）/ 偏离场（逻辑已变）/ 证据不足 — with sources and assumptions labeled
- Doubles as a pre-purchase checklist before long-term holding (the original author's own usage)
- Platform-agnostic data gathering (Investing Pro, filings, WebSearch); no target prices, no investment advice

**Install:**
```bash
npx skills add desmondc9/agent-skills@analyze-dip -g
```

**Usage:** Ask naturally — the skill auto-triggers on crash/pullback decision intent:

```
NVDA 跌了 20%，现在该抄底还是离场？
BTC 暴跌，是抄底机会还是该跑？
帮我看看美光这次回调要不要补仓
buy the dip or get out of TSLA?
```

**Prerequisites:** A Claude Code environment with `WebSearch` / `WebFetch` for gathering earnings estimates, valuation data, analyst revisions, and sector news.

See the [skill README](./analyze-dip/SKILL.md) for the workflow and [REFERENCE.md](./analyze-dip/REFERENCE.md) for the per-step criteria, historical panic-selloff cases, and the crypto adaptation table.

---

## License

Apache 2.0 — see [LICENSE](./LICENSE).
