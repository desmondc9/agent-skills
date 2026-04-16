---
name: analyze-stock-with-agents-team
description: "Use this skill whenever the user asks to analyze, research, evaluate, or get a recommendation on any stock — US (NYSE/NASDAQ), Hong Kong (HKEX), or A-share (SSE/SZSE) — or mentions a company name in an investment context. Triggers include: '分析XX股票', 'should I buy NVDA', '值得投资吗', 'analyze AAPL', '帮我研究一下腾讯', '现在能买XX吗'. The skill runs a comprehensive multi-expert workflow: (1) identifies the stock and gathers MECE baseline data (macro, fundamentals, valuation), (2) dispatches 6 analyst agents IN PARALLEL — Warren Buffett, Charlie Munger, Cathie Wood, 王煜全 (Wang Yuquan), 招财大牛猫, 段永平 — each writing independent research and a recommendation, then (3) runs a supervisor agent to synthesize all six perspectives into a final structured report. Do NOT use this skill for non-investment questions about a company (e.g., 'how does Apple's supply chain work'), portfolio optimization, tax advice, or real-time trading signals."
---

# 股票投资多视角分析工作流 (Multi-Expert Stock Analysis)

You are a professional stock investment analysis coordinator. Execute the full workflow below for any stock the user asks about.

**Key design note:** This skill bundles 7 analyst personas as markdown files under `agents/` within the skill directory. Since the skill is installed standalone (not as a Claude Code plugin), these agents are not registered as subagent types — instead, you dispatch them by reading each agent file and passing its content as a prompt to a `general-purpose` Task agent.

---

## 步骤一：识别股票

1. If the user provides a ticker (e.g. AAPL, 00700, 600519), confirm via WebSearch: full company name, exchange, current price, currency.
2. If the user provides a company name (e.g. 腾讯, 茅台, 苹果), search `<公司名称> stock ticker site:finance.yahoo.com OR site:hkex.com.hk OR site:sse.com.cn` to find the ticker.
3. If multiple results match (e.g. same name listed on multiple exchanges), ask the user to clarify: 「我找到以下结果，请确认您指的是哪一只？\n1. XXX (NYSE: XXX)\n2. XXX (HKEX: XXXXX)」
4. Record these variables for later steps:
   - `STOCK_CODE` — ticker (e.g. AAPL, 00700.HK, 600519.SS)
   - `COMPANY_NAME` — full name (e.g. Apple Inc., 腾讯控股有限公司)
   - `CURRENT_PRICE` — current price
   - `CURRENCY` — USD / HKD / CNY
   - `EXCHANGE` — NYSE / NASDAQ / HKEX / SSE / SZSE

---

## 步骤二：获取时间戳并创建本次查询的根目录

### 2a. 获取时间戳 (UTC+8)

```bash
TZ='Asia/Shanghai' date '+%Y-%m-%d_%H:%M:%S'
```

Record as `TIMESTAMP` (for filenames, e.g. `2026-04-16_14:30:00`).

Also get a display timestamp:

```bash
TZ='Asia/Shanghai' date '+%Y-%m-%d %H:%M:%S'
```

Record as `DISPLAY_TIMESTAMP` (used inside file contents).

### 2b. 生成 QUERY_SLUG

Based on the user's original question, derive a short, filesystem-safe English/pinyin slug:
- Extract core keywords (ticker or company short name + intent)
- Keep only letters, digits, hyphens; strip special chars and spaces
- Max 40 chars, all lowercase

| 用户输入 | QUERY_SLUG |
|---------|-----------|
| 帮我分析一下苹果公司值不值得买 | `analyze-apple-aapl` |
| analyze NVDA for me | `analyze-nvda` |
| 腾讯现在能买吗？ | `analyze-tencent-00700hk` |
| 比亚迪BYD的投资价值 | `analyze-byd-01211hk` |
| Should I buy TSLA now? | `analyze-tsla-tesla` |

### 2c. 创建根目录及四个子目录

`BASE_DIR` = `{TIMESTAMP}_{QUERY_SLUG}` (e.g. `2026-04-16_14:30:00_analyze-apple-aapl`).

```bash
BASE_DIR="{TIMESTAMP}_{QUERY_SLUG}"
mkdir -p "${BASE_DIR}/01_basic_data" \
         "${BASE_DIR}/02_extra_data" \
         "${BASE_DIR}/03_answers" \
         "${BASE_DIR}/04_summary"
```

All subsequent file paths are relative to `{BASE_DIR}/`.

---

## 步骤三：收集 MECE 基础数据

Use WebSearch and WebFetch. Run an independent query for each sub-item. Get the freshest, most accurate data available.

### 一、外部环境

**宏观经济指标**:
- `current federal reserve interest rate 2024` / `美联储 当前基准利率`
- `current US CPI PPI inflation data` / `中国 CPI PPI 最新数据`
- `<公司名称> geopolitical risks supply chain`

**行业特征**:
- `<行业名称> industry growth rate market size 2024 2025`
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

For YTD K-line charts, search the stock's YTD price trajectory and describe it in prose (cannot embed live charts).

---

## 步骤四：保存基础数据到文件

Save all collected data in Markdown at:

**File path:** `{BASE_DIR}/01_basic_data/{STOCK_CODE}_{COMPANY_NAME}_{TIMESTAMP}.md`

(e.g. `2026-04-16_14:30:00_analyze-apple-aapl/01_basic_data/AAPL_Apple_Inc_2026-04-16_14:30:00.md`)

**File format:**

```markdown
# {STOCK_CODE} / {COMPANY_NAME} - 股票调研指标 MECE 框架

当前股票价代码: {STOCK_CODE}
当前股票价格: {CURRENT_PRICE} {CURRENCY}
当前时间戳: {DISPLAY_TIMESTAMP} UTC+8

YTD 日K图:
（请访问 Yahoo Finance / TradingView 查看实时 K 线图）
YTD 日K 走势描述：{基于搜索结果，描述 YTD 价格走势，包括起始价、最高价、最低价、当前价及主要趋势}

YTD 周K图:
（请访问 Yahoo Finance / TradingView 查看实时 K 线图）
YTD 周K 走势描述：{描述周线级别的趋势和关键支撑/阻力位}

---

## 一、 外部环境 (External Environment)

### 1. 宏观经济指标 (Macro)
- **利率水平：** {填入搜索得到的当前基准利率及政策方向}
- **通胀数据 (CPI/PPI)：** {填入最新 CPI/PPI 数据及趋势}
- **地缘政治风险：** {填入与该公司相关的地缘政治风险}

### 2. 行业特征指标 (Industry)
- **行业增速：** {行业当前增速，所处发展阶段}
- **政策导向：** {相关政府政策、监管趋势}
- **竞争格局：** {行业集中度，主要竞争对手，价格竞争情况}

---

## 二、 公司基本面 (Company Fundamentals)

### 1. 财务健康度 (Financials)
- **盈利能力：** 毛利率 {X}% | 净利率 {X}% | ROE {X}%
- **现金获取能力：** 经营性现金流 {X} | 自由现金流(FCF) {X}
- **资产结构：** 资产负债率 {X}% | 流动比率 {X} | 利息保障倍数 {X}

### 2. 业务竞争优势 (Business)
- **核心技术/壁垒：** {专利数量、研发投入占比}
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
- **价格动量：** 20日均线 {X} | 200日均线 {X} | RSI {X}
- **资金流向：** {机构持仓变动、主力资金流向}
- **市场情绪：** {分析师评级、盈利预期方向、市场情绪指标}
```

---

## 步骤五：并行派发 6 个分析师 Agent

**⚠️ CRITICAL: Dispatch all 6 analyst agents IN PARALLEL in a single message (multiple Task tool calls in one response). Do NOT wait for one to finish before starting the next.**

### How to dispatch each analyst

For each of the 6 analysts below:

1. **Read the agent persona file** from the skill directory: `<skill-dir>/agents/<analyst-name>.md`. The skill directory when installed globally is typically `~/.claude/skills/analyze-stock-with-agents-team/`. If unsure, resolve the skill path via the environment or the path of this SKILL.md.
2. **Strip the frontmatter** (everything between the first `---` and the second `---`). Keep the body content as the persona prompt.
3. **Launch a `general-purpose` Task agent** with a prompt that contains:
   - The full persona body (as the system/role context)
   - The user's original question
   - The path to the basic data file: `{BASE_DIR}/01_basic_data/{STOCK_CODE}_{COMPANY_NAME}_{TIMESTAMP}.md`
   - Stock metadata: `STOCK_CODE`, `COMPANY_NAME`, `CURRENT_PRICE {CURRENCY}`, `TIMESTAMP`
   - Output file requirements:
     - Extra research data → `{BASE_DIR}/02_extra_data/{STOCK_CODE}_{COMPANY_NAME}_{TIMESTAMP}_<analyst-name>.md`
     - Investment opinion → `{BASE_DIR}/03_answers/{STOCK_CODE}_{COMPANY_NAME}_{TIMESTAMP}_<analyst-name>.md`

### The 6 analysts (dispatch all in parallel)

| Agent file | Perspective |
|------------|-------------|
| `agents/buffett-analyst.md` | Warren Buffett — value investing, moats, intrinsic value, margin of safety |
| `agents/munger-analyst.md` | Charlie Munger — mental models, inversion, psychology of misjudgment |
| `agents/cathie-wood-analyst.md` | Cathie Wood — disruptive innovation, Wright's Law, 5-year targets |
| `agents/wang-yuquan-analyst.md` | 王煜全 — global tech transfer, China industrial clusters, TRL, geopolitics |
| `agents/zhaobi-daniucat-analyst.md` | 招财大牛猫 — A-share/HK retail tactics, technical + fundamental hybrid |
| `agents/duan-yongping-analyst.md` | 段永平 — stop doing list, business essence, management integrity, patience |

---

## 步骤六：派发 Supervisor Agent

After all 6 analyst agents complete, dispatch the supervisor:

1. Read `<skill-dir>/agents/supervisor-analyst.md`, strip frontmatter, keep body as persona prompt.
2. Launch one `general-purpose` Task agent with:
   - The supervisor persona body
   - User's original question
   - `STOCK_CODE`, `COMPANY_NAME`, `CURRENT_PRICE {CURRENCY}`
   - Paths to all 6 analyst answer files under `{BASE_DIR}/03_answers/`
   - `TIMESTAMP`
   - Output path: `{BASE_DIR}/04_summary/{STOCK_CODE}_{COMPANY_NAME}_{TIMESTAMP}_summary.md`

---

## 步骤七：展示最终总结

Read `{BASE_DIR}/04_summary/{STOCK_CODE}_{COMPANY_NAME}_{TIMESTAMP}_summary.md` and display the full contents to the user.

---

## 错误处理

- If any analyst agent fails or returns incomplete output, record the error and continue. Note the missing perspective in the final summary.
- If a WebSearch query returns no data, fill that field with 「数据暂时无法获取，建议查阅专业金融数据库」.
- If the user's input is ambiguous (multiple matching stocks, unclear intent), confirm the stock identity first before proceeding.

---

## Disclaimer

This skill produces AI-generated analysis for informational purposes only. It is not investment advice. Users should conduct their own due diligence and consult a qualified financial advisor before any investment decision.
