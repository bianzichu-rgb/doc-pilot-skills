---
name: doc-pilot-pdf
description: >
  Layout-aware PDF to structured Markdown converter that preserves font-based heading
  hierarchy, table of contents, dual-column layouts, figures, and spec tables.
  Use this whenever: a user asks to read/extract/parse/convert a PDF, wants the structure
  of a manual or document, says "turn this PDF into text/Markdown", or when doc-pilot
  needs to process a local PDF file before navigation.
emoji: 📄
triggers:
  - "extract this PDF"
  - "read this PDF"
  - "convert PDF"
  - "parse this PDF"
  - "提取PDF"
  - "读取PDF"
metadata.openclaw.os: ["darwin", "linux", "win32"]
metadata.openclaw.requires.bins: ["python3"]
metadata.openclaw.requires.pip: ["pymupdf"]
---

# doc-pilot-pdf

Convert any local PDF into structured Markdown that preserves the document's logical
hierarchy — not just a raw text dump.

## When to use

- User provides a path to a local PDF and wants its content extracted
- User says "read this PDF", "extract the structure", "convert to Markdown"
- `doc-pilot` needs to process a local PDF before task navigation

## How to run

```bash
python3 ~/.openclaw/skills/doc-pilot-pdf/scripts/extract.py <pdf_path> [--output <md_path>] [--toc-only]
```

**Arguments:**
- `pdf_path` — absolute or relative path to the PDF
- `--output` — optional output .md file (default: prints to stdout)
- `--toc-only` — only print the table of contents and exit

## What it produces

- `## Table of Contents` block (from PDF bookmarks or font-size inference)
- Heading levels `#` / `##` derived from font sizes
- `<!-- Breadcrumb >` comment tags for context tracking
- `> **[Related Parts]**` blocks for indexed part lists
- Spec tables reconstructed from `Key: Value` lines
- `[Image on page N, position: top/middle/bottom]` figure placeholders
- Headers/footers stripped (top/bottom 6% of page)
- Duplicate lines removed

## Limitations

- Scanned/image-only PDFs produce minimal output (no embedded text)
- Merged-cell tables may not render perfectly
- Images are placeholders only, not extracted files

## Part of the doc-pilot suite

After extraction, pass the Markdown to:
- `doc-pilot-analyst` for section semantic classification
- `doc-pilot` for step-by-step task navigation
