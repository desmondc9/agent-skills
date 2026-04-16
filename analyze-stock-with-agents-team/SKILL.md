---
name: analyze-stock-with-agents-team
description: "Use this skill whenever the user asks to analyze, research, evaluate, or get a recommendation on any stock — US (NYSE/NASDAQ), Hong Kong (HKEX), or A-share (SSE/SZSE) — or mentions a company name in an investment context. Triggers include: '分析XX股票', 'should I buy NVDA', '值得投资吗', 'analyze AAPL', '帮我研究一下腾讯', '现在能买XX吗'. The skill runs a comprehensive multi-expert workflow: (1) identifies the stock and fetches real-time price + 3-year K-line charts via a Python script (akshare/yfinance + mplfinance), (2) gathers MECE baseline data (macro, fundamentals, valuation) via WebSearch, (3) dispatches 6 analyst agents IN PARALLEL — Warren Buffett, Charlie Munger, Cathie Wood, 王煜全 (Wang Yuquan), 招财大牛猫, 段永平 — each writing independent research and a recommendation, then (4) runs a supervisor agent to synthesize all six perspectives into a final structured report. Do NOT use this skill for non-investment questions about a company, portfolio optimization, tax advice, or real-time trading signals."
---

# 股票投资多视角分析工作流 (Multi-Expert Stock Analysis)

You are a professional stock investment analysis coordinator. Execute the full workflow below for any stock the user asks about.

**Design note:** This skill bundles 7 analyst personas under `agents/` and one Python data-fetch script under `scripts/`. Since the skill is installed standalone (not as a Claude Code plugin), the analyst markdown files are dispatched at runtime by reading each file and passing its body as a prompt to a `general-purpose` Task agent.

**Prerequisites on the host system:**
- `uv` — [astral-sh/uv](https://github.com/astral-sh/uv) (used to run the Python script with PEP 723 inline dependencies). The script auto-installs `akshare`, `yfinance`, `mplfinance`, `pandas`, `matplotlib` on first run.

---

## 跨步骤规则：货币单位统一 (Currency-Unit Consistency)

**In every file produced by this skill, every monetary value MUST be explicitly labeled with its currency** (USD / HKD / CNY / etc.). The report's **primary currency** is the stock's trading currency (US → USD, HK → HKD, A-share → CNY), determined in Step 1.

Rules:
1. All prices, market caps, revenue, FCF, target prices, etc. must carry an explicit currency suffix — e.g. `175.23 USD`, `¥2,145 亿 CNY`, `HK$ 420.5`.
2. If a source cites a different currency (e.g. Wall Street estimate quotes a HK company in USD), **convert to the primary currency** and note the conversion: `折合 USD ~= 22.40 (汇率 7.82, 2026-04-16)`.
3. Never mix currencies implicitly in the same table or sentence without explicit labels.
4. Every analyst agent and the supervisor must follow this rule. Pass the primary currency and the requirement explicitly in their prompts.

---

## 步骤一：识别股票

1. If the user provides a ticker (e.g. AAPL, 00700, 600519), confirm via WebSearch: full company name, exchange, current price, currency.
2. If the user provides a company name (e.g. 腾讯, 茅台, 苹果), search `<公司名称> stock ticker site:finance.yahoo.com OR site:hkex.com.hk OR site:sse.com.cn`.
3. If multiple results match, ask the user to clarify: 「我找到以下结果，请确认您指的是哪一只？\n1. XXX (NYSE: XXX)\n2. XXX (HKEX: XXXXX)」
4. Record these variables:
   - `STOCK_CODE` — ticker (e.g. `AAPL`, `00700.HK`, `600519.SS`)
   - `COMPANY_NAME` — full name (e.g. `Apple Inc.`, `腾讯控股有限公司`)
   - `MARKET` — `US` | `HK` | `A`
   - `CURRENCY` — primary currency of the report: `USD` | `HKD` | `CNY`
   - `EXCHANGE` — NYSE / NASDAQ / HKEX / SSE / SZSE

Note: `CURRENT_PRICE` is NOT set here — it is fetched accurately by the Python script in Step 3.

---

## 步骤二：时间戳、工具/模型标识、BASE_DIR

### 2a. 获取时间戳 (UTC+8)

```bash
TZ='Asia/Shanghai' date '+%Y-%m-%d_%H:%M:%S'
```

Record as `TIMESTAMP` (for filenames, e.g. `2026-04-16_14:30:00`). Also:

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
| 比亚迪BYD的投资价值 | `analyze-byd-01211hk` |

### 2d. BASE_DIR

```
BASE_DIR = {TIMESTAMP}_{QUERY_SLUG}_{TOOL_NAME}_{MODEL_NAME}
```

Examples:
- `2026-04-16_14:30:00_analyze-apple-aapl_claude-code_sonnet-4.6`
- `2026-04-16_14:30:00_analyze-apple-aapl_kimi-code_k-2.5`

Create the directory tree:

```bash
BASE_DIR="{TIMESTAMP}_{QUERY_SLUG}_{TOOL_NAME}_{MODEL_NAME}"
mkdir -p "${BASE_DIR}/01_basic_data/assets" \
         "${BASE_DIR}/02_extra_data" \
         "${BASE_DIR}/03_answers" \
         "${BASE_DIR}/04_summary"
```

All subsequent paths are relative to `{BASE_DIR}/`.

---

## 步骤三：获取准确价格 + 生成3年K线图 (Python script via uv)

Run the bundled script to fetch accurate data and write two PNG charts into `01_basic_data/assets/`.

**Skill dir resolution:** when installed globally, the skill lives at `~/.claude/skills/analyze-stock-with-agents-team/`. The script is at `<skill-dir>/scripts/fetch_stock_data.py`.

```bash
uv run --script ~/.claude/skills/analyze-stock-with-agents-team/scripts/fetch_stock_data.py \
    --ticker <ticker-for-data-source> \
    --market <US|HK|A> \
    --output-dir "$(pwd)/${BASE_DIR}/01_basic_data"
```

Ticker conventions for `--ticker`:
- US: raw symbol (`AAPL`, `NVDA`, `TSLA`)
- HK: digits only, e.g. `00700` (strip `.HK`)
- A-share: 6-digit code, e.g. `600519` (strip `.SS` / `.SZ`)

The script prints a JSON object to stdout. Parse it and capture:
- `current_price` → `CURRENT_PRICE` (accurate, sourced from akshare → yfinance fallback)
- `as_of_date` → `PRICE_AS_OF`
- `daily_chart_relpath` / `weekly_chart_relpath` → paths used inside the markdown
- `daily_trend_description` / `weekly_trend_description` → pre-generated trend text
- `data_source` → `akshare` or `yfinance` (cite in the markdown)
- `period_start`, `period_end`, `period_high`, `period_low` — all in `CURRENCY`

If the script exits non-zero or returns `{"error": ...}`, fall back to WebSearch for the current price and skip chart embedding, but continue the rest of the workflow. Note the degradation in the report.

---

## 步骤四：收集 MECE 基础数据 (WebSearch)

Use WebSearch and WebFetch for everything the Python script does NOT provide. Run an independent query per sub-item.

### 一、外部环境

**宏观经济指标**:
- `current federal reserve interest rate` / `美联储 当前基准利率`
- `current US CPI PPI inflation data` / `中国 CPI PPI 最新数据`
- `<公司名称> geopolitical risks supply chain`

**行业特征**:
- `<行业名称> industry growth rate market size`
- `<公司名称> industry regulation policy government`
- `<行业名称> competitive landscape market share concentration`

### 二、公司基本面

**财务健康度**:
- `<STOCK_CODE> gross margin net margin ROE annual`
- `<STOCK_CODE> free cash flow operating cash flow`
- `<STOCK_CODE> debt to equity ratio current ratio interest coverage`

**业务竞争优势**:
- `<公司名称> competitive moat patents R&D spending`
- `<公司名称> market share brand customer retention`
- `<公司名称> management CEO biography insider ownership`
- `<公司名称> supply chain key components vertical integration`

### 三、市场交易面

**估值**:
- `<STOCK_CODE> PE ratio PB ratio PS ratio current`
- `<STOCK_CODE> PEG ratio forward PE`
- `<STOCK_CODE> historical PE ratio 5 year 10 year percentile`

**技术与情绪**:
- `<STOCK_CODE> 20 day 200 day moving average RSI`
- `<STOCK_CODE> institutional ownership changes hedge fund holdings`
- `<STOCK_CODE> analyst rating consensus price target`

Tag every monetary value you extract with its original currency, and convert to `CURRENCY` where needed (see the currency-consistency rule at the top).

---

## 步骤五：保存基础数据文件

Save the Markdown at:

```
{BASE_DIR}/01_basic_data/{STOCK_CODE}_{COMPANY_NAME}_{TIMESTAMP}.md
```

**File template:**

```markdown
# {STOCK_CODE} / {COMPANY_NAME} - 股票调研指标 MECE 框架

当前股票代码: {STOCK_CODE}
当前股票价格: {CURRENT_PRICE} {CURRENCY}  （数据源: {data_source}，截至 {PRICE_AS_OF}）
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
- **利率水平：** {填入搜索得到的当前基准利率及政策方向}
- **通胀数据 (CPI/PPI)：** {最新 CPI/PPI 数据及趋势}
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

---

## 步骤六：并行派发 6 个分析师 Agent

**⚠️ CRITICAL: Dispatch all 6 analyst agents IN PARALLEL in a single message (multiple Task tool calls in one response). Do NOT wait for one to finish before the next.**

### How to dispatch each analyst

For each of the 6 analysts:

1. Read `<skill-dir>/agents/<analyst-name>.md`. The skill dir is typically `~/.claude/skills/analyze-stock-with-agents-team/`.
2. Strip the frontmatter (between the first `---` and the second `---`). Keep the body as the persona prompt.
3. Launch a `general-purpose` Task agent with a prompt containing:
   - The full persona body as role/system context
   - The user's original question
   - Basic data file path: `{BASE_DIR}/01_basic_data/{STOCK_CODE}_{COMPANY_NAME}_{TIMESTAMP}.md`
   - Stock metadata: `STOCK_CODE`, `COMPANY_NAME`, `CURRENT_PRICE {CURRENCY}`, `PRICE_AS_OF`, `TIMESTAMP`
   - **Currency rule (restate explicitly):** primary currency is `{CURRENCY}`; every monetary value must be explicitly labeled with currency; non-primary currencies must be converted with a noted exchange rate.
   - Output paths:
     - Extra research data → `{BASE_DIR}/02_extra_data/{STOCK_CODE}_{COMPANY_NAME}_{TIMESTAMP}_<analyst-name>.md`
     - Investment opinion → `{BASE_DIR}/03_answers/{STOCK_CODE}_{COMPANY_NAME}_{TIMESTAMP}_<analyst-name>.md`

### The 6 analysts (dispatch all in parallel)

| Agent file | Perspective |
|------------|-------------|
| `agents/buffett-analyst.md` | Warren Buffett — value, moats, intrinsic value, margin of safety |
| `agents/munger-analyst.md` | Charlie Munger — mental models, inversion, psychology of misjudgment |
| `agents/cathie-wood-analyst.md` | Cathie Wood — disruptive innovation, Wright's Law, 5-year targets |
| `agents/wang-yuquan-analyst.md` | 王煜全 — global tech transfer, China industrial clusters, TRL, geopolitics |
| `agents/zhaobi-daniucat-analyst.md` | 招财大牛猫 — A/HK retail tactics, technical + fundamental hybrid |
| `agents/duan-yongping-analyst.md` | 段永平 — stop doing list, business essence, management integrity, patience |

---

## 步骤七：派发 Supervisor Agent

Once all 6 analyst agents complete:

1. Read `<skill-dir>/agents/supervisor-analyst.md`, strip frontmatter.
2. Launch one `general-purpose` Task agent with:
   - The supervisor persona body
   - User's original question
   - `STOCK_CODE`, `COMPANY_NAME`, `CURRENT_PRICE {CURRENCY}`, `PRICE_AS_OF`
   - **Currency rule (restated):** primary currency `{CURRENCY}`; all money values explicitly labeled and consistent.
   - Paths to all 6 analyst answer files in `{BASE_DIR}/03_answers/`
   - Timestamp `TIMESTAMP`, tool `TOOL_NAME`, model `MODEL_NAME`
   - Output: `{BASE_DIR}/04_summary/{STOCK_CODE}_{COMPANY_NAME}_{TIMESTAMP}_summary.md`

---

## 步骤八：展示最终总结

Read `{BASE_DIR}/04_summary/{STOCK_CODE}_{COMPANY_NAME}_{TIMESTAMP}_summary.md` and display the full contents to the user.

---

## 错误处理

- If an analyst agent fails, record the error, continue, and note the missing perspective in the final summary.
- If the Python data script fails (e.g. network issue), fall back to WebSearch-based current price and skip chart embedding; note the degraded state in the report.
- If WebSearch returns no data for a sub-item, fill with 「数据暂时无法获取，建议查阅专业金融数据库」.
- If the user's input is ambiguous, confirm the stock identity first before proceeding.

---

## Disclaimer

This skill produces AI-generated analysis for informational purposes only. It is not investment advice. Users should conduct their own due diligence and consult a qualified financial advisor before any investment decision.
