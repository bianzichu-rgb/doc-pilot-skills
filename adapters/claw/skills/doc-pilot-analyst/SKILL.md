---
name: doc-pilot-analyst
description: >
  Semantic document structure analyser that classifies sections into categories
  (safety, installation, operation, troubleshooting, specs, maintenance, FAQ, recipes, etc.)
  and registers figure/table cross-references. Use this whenever: a user wants to know what
  a document covers, asks to find sections related to a topic, wants a structural overview,
  or when doc-pilot needs to locate the right chapter before generating task steps.
  Supports Chinese, English, and Japanese.
emoji: 🗂️
triggers:
  - "what sections does this document cover"
  - "find the troubleshooting section"
  - "analyse this document"
  - "document structure"
  - "这个文档有哪些章节"
  - "找故障排除"
metadata.openclaw.os: ["darwin", "linux", "win32"]
metadata.openclaw.requires.bins: ["python3"]
---

# doc-pilot-analyst

Classify document sections by semantic type and map figure/table cross-references.
No external dependencies beyond Python — works on any Markdown text.

## When to use

- User asks "what does this document cover?" or "find the troubleshooting section"
- User wants a structural overview before diving in
- `doc-pilot` needs to locate relevant chapters for task navigation

## How to run

```bash
python3 ~/.openclaw/skills/doc-pilot-analyst/scripts/analyse.py <md_path_or_-> [--filter <category>] [--json]
```

**Arguments:**
- `md_path_or_-` — path to a Markdown file, or `-` to read from stdin
- `--filter` — only show sections matching a category (e.g. `troubleshooting`, `installation`)
- `--json` — output raw JSON instead of human-readable summary

## Output (human-readable)

```
Document Structure Analysis
============================
[TROUBLESHOOTING]  Error Codes & Solutions (p.12-15)
[INSTALLATION]     Getting Started / Setup (p.3-6)
[TECHNICAL_SPEC]   Specifications (p.28)
[OPERATION]        Daily Use (p.7-11)
...

Figures: 14 registered | Cross-references found: 8
```

## Categories

| Code | Description |
|------|-------------|
| `SAFETY` | Warnings, hazards, precautions |
| `INSTALLATION` | Setup, assembly, mounting |
| `OPERATION` | Daily use, controls, programs |
| `TROUBLESHOOTING` | Error codes, faults, repair |
| `TECHNICAL_SPEC` | Dimensions, power, ratings |
| `MAINTENANCE` | Cleaning, descaling, filters |
| `FAQ` | Warranty, legal, compliance |
| `RECIPE` | Cooking programs, use cases |
| `PARTS` | Components, accessories list |

## Part of the doc-pilot suite

- Feed output from `doc-pilot-pdf` into this for structured analysis
- Pass section locations to `doc-pilot` for targeted task navigation
