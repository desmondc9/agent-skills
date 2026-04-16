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

### [analyze-stock-with-agents-team](./analyze-stock-with-agents-team/)

Runs a comprehensive multi-expert stock investment analysis for any US, Hong Kong, or A-share stock, using 6 parallel analyst personas plus a synthesis supervisor.

**Features:**
- Auto-identifies the stock (ticker or company name, any market)
- Gathers MECE baseline data: macro, fundamentals, valuation, technicals
- Dispatches 6 analyst agents **in parallel**, each producing independent research + a recommendation:
  - 🔴 **Warren Buffett** — value investing, economic moats, margin of safety
  - 🟣 **Charlie Munger** — mental models, inversion, psychology of misjudgment
  - 🔵 **Cathie Wood** — disruptive innovation, Wright's Law, 5-year targets
  - 🟢 **王煜全** — global tech transfer, China industrial clusters, geopolitics
  - 🟡 **招财大牛猫** — A/HK market tactics, technical + fundamental hybrid
  - 🟠 **段永平** — stop doing list, business essence, management integrity
- **Supervisor agent** synthesizes all six perspectives into a structured final report
- Every run saves to a timestamped folder: `01_basic_data/`, `02_extra_data/`, `03_answers/`, `04_summary/`

**Install:**
```bash
npx skills add desmondc9/agent-skills@analyze-stock-with-agents-team -g
```

**Usage:** Just ask naturally — the skill auto-triggers on investment-analysis intent:

```
帮我分析一下苹果公司值不值得买
analyze Tesla stock for me
腾讯现在能买吗？
Should I buy NVDA now?
```

**Prerequisites:** None beyond a Claude Code environment with `WebSearch`, `WebFetch`, `Bash`, and `Task` tools enabled.

See the [skill README](./analyze-stock-with-agents-team/SKILL.md) for the full workflow and agent personas.

**Disclaimer:** AI-generated analysis for informational purposes only. Not investment advice.

---

## License

Apache 2.0 — see [LICENSE](./LICENSE).
