# desmondc9-agent-skills

A collection of Claude Code skills for document processing and productivity workflows.

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

## License

Apache 2.0 — see [LICENSE](./LICENSE).
