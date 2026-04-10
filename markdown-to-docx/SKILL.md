---
name: markdown-to-docx
description: "Use this skill whenever the user wants to convert a Markdown file to a Word document (.docx). Triggers include: 'convert markdown to Word', 'convert .md to .docx', 'render mermaid to Word', 'generate Word doc from markdown', 'export markdown as docx', or any request to turn a .md file into a .docx. Use this skill even if the user just says 'make a Word doc from this markdown' or 'convert this to Word'. This skill handles: (1) native Word TOC placed after the document header block (H1 title + metadata + '---' separator), (2) Mermaid diagram blocks rendered to high-resolution PNG and embedded as images, and (3) tables formatted with colored header rows, alternating row shading, and borders. Do NOT use for PDFs, Google Docs, spreadsheets, or general DOCX editing unrelated to Markdown conversion."
---

# Markdown → DOCX Conversion

Converts any Markdown file to a professionally formatted Word document (.docx) using a bundled Python pipeline: **pandoc** + **mmdc** (Mermaid CLI) + **python-docx** post-processing.

## What This Skill Does

1. **Pre-processes Markdown** — strips any manually written `## Table of Contents` section, injects TOC placeholder strings after the first `---` separator (i.e., right after the document header block: title + metadata + `---`)
2. **Renders Mermaid diagrams** — finds every ` ```mermaid ` fenced block, renders each to a high-resolution PNG (2400 px wide, 3× scale), and replaces the block with an image reference
3. **Converts with pandoc** — produces the base `.docx` from the processed Markdown
4. **Post-processes the DOCX** — replaces the TOC placeholders with a native Word TOC field (`{ TOC \o "1-3" \h \z \u }`) and applies table formatting (dark header row, alternating row shading, cell borders)

## Usage

```bash
python <skill-scripts-path>/convert_markdown_to_docx.py <input.md> [output.docx]
```

- `input.md` — path to the Markdown file (required)
- `output.docx` — output path (optional; defaults to `<input>.docx`)

**Example:**
```bash
python ~/.claude/skills/markdown-to-docx/scripts/convert_markdown_to_docx.py solution.md
python ~/.claude/skills/markdown-to-docx/scripts/convert_markdown_to_docx.py docs/report.md docs/report.docx
```

## How to Run for the User

When the user asks to convert a markdown file:

1. Identify the input file path from the user's request
2. Determine the output path (default: same name, `.docx` extension)
3. Run the script:
   ```bash
   python ~/.claude/skills/markdown-to-docx/scripts/convert_markdown_to_docx.py <input.md> [output.docx]
   ```
4. Report the output path and file size
5. Remind the user to open the `.docx` in Word and click **"Update Table"** when prompted to populate the TOC with page numbers

## Prerequisites

All of these must be installed on the system:

| Tool | Purpose | Install |
|------|---------|---------|
| `pandoc` | Markdown → DOCX base conversion | `sudo apt install pandoc` |
| `mmdc` (Mermaid CLI) | Render Mermaid diagrams to PNG | `npm install -g @mermaid-js/mermaid-cli` |
| `python-docx` | Post-process DOCX (TOC, tables) | `pip install python-docx` |
| `chromium-browser` | Headless rendering for mmdc | `sudo apt install chromium-browser` |

The script expects Chromium at `/usr/bin/chromium-browser` and writes a `puppeteer.json` config automatically.

## Markdown Document Structure

For best results, the input Markdown should follow this structure:

```markdown
# Document Title

**Author:** Name  
**Date:** 2026-04-10  
**Version:** 1.0

---

(TOC will be inserted here automatically)

## Section 1
...

## Section 2
...
```

The `---` separator after the header block is required for the TOC to be positioned correctly. If it is missing, the TOC will not be inserted.

## Output Details

- **TOC**: Native Word field positioned after the header block. Word will show "Error! No table of contents entries found." until the user opens the file and clicks **Update Table** — this is expected.
- **Mermaid diagrams**: Rendered PNGs are stored in `_mermaid_imgs/` next to the input file. These are reused on subsequent runs.
- **Tables**: Header row → dark blue (`#1F3864`) background with white bold text. Even rows → light blue (`#EBF0FA`) shading. All cells → grey (`#BFBFBF`) borders.

## Troubleshooting

**Mermaid diagrams fail to render:**
- Check that `chromium-browser` is at `/usr/bin/chromium-browser`: `which chromium-browser`
- Check that mmdc is installed: `mmdc --version`
- Individual diagram failures are warned but do not stop conversion; the original fenced block is kept in the output

**TOC not inserted / "Expected 2 TOC placeholders, found 0":**
- The input Markdown must have a standalone `---` line after the document header
- Check that no manual `## Table of Contents` section is consuming the `---` line

**pandoc fails:**
- Ensure pandoc is installed: `pandoc --version`
- Check stderr output for details

**python-docx not found:**
- Install with: `pip install python-docx`
