---
name: deep-company-analysis
description: "Generate a structured deep-dive research report on any company, stock, or crypto project from both growth and value investing perspectives. Use when the user asks to '深度分析', '调研', 'research', 'analyze' a specific company, stock, or token — or mentions evaluating an investment target with a comprehensive framework. Triggers include: '分析XX公司', '调研XX股票', '深度研究', '公司基本面分析', '企业调研报告', 'crypto project analysis'. Do NOT use for simple price checks, real-time trading signals, portfolio optimization, or tax advice."
---

# 深度企业分析 (Deep Company Analysis)

## Quick start

1. Ask the user for the **target company name / stock ticker / token symbol** (if not already provided).
2. Read `REFERENCE.md` — this is the full 8-dimension analysis framework.
3. Perform web research to gather quantitative data (financials, market share, on-chain metrics, etc.).
4. Generate the report in **Simplified Chinese** strictly following the output order and format in REFERENCE.md.
5. Output the complete report directly to the user (no intermediate files required unless requested).

## Workflow

### Step 1 — Identify target
- Resolve company name, ticker, or token symbol.
- Determine asset type: **public stock** / **private company** / **crypto/Web3 project**.
- Note the founding date (to determine available historical data range).

### Step 2 — Research & fill framework
- Use WebSearch/WebFetch to gather data for each dimension in REFERENCE.md.
- For every quantitative claim, annotate the source (财报/招股书/第三方机构/链上数据/行业白皮书).
- Mark speculative content with 【推测】.
- If a dimension is not applicable (e.g., a crypto project has no "debt-to-asset ratio"), explicitly label it: 【不适用】原因：...

### Step 3 — Generate report
- Output order is **mandatory**: Executive Summary → Dimensions 1–7 → Crypto Appendix (if applicable).
- Use `###` headers for each sub-dimension.
- Present time-series quantitative data in **tables**.
- After each main dimension, append a 200-word "维度核心摘要".
- End with a "综合观察清单" of 5–8 trackable indicators/events for the next 12 months.

### Step 4 — Compliance check
- Verify: no "买入/卖出/持有" recommendations appear.
- Verify: all currency values are explicitly labeled (USD / CNY / HKD / etc.).
- Verify: competitive benchmarks (vs peers and industry median) are included for key metrics.
- Verify: 3-year, 5-year, and 10-year time spans are covered (or noted if insufficient history).

## Key rules

- **Language**: Simplified Chinese throughout. English proper nouns, tickers, and metric abbreviations (PE, PB, ROE, FCF, etc.) may remain in original form.
- **No investment advice**: Only facts, logic, and evidence. No price targets or action recommendations.
- **Progressive disclosure**: If the user only wants a specific dimension, read REFERENCE.md and extract only that section while keeping cross-references intact.

## Reference

- Full framework: [REFERENCE.md](REFERENCE.md)
