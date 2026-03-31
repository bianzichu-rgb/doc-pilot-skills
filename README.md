# doc-pilot Skills Suite

> **Turn any document into a step-by-step task navigator. Gets smarter every use.**

A collection of three Claude Code Skills that give Claude layout-aware document understanding,
semantic structure analysis, and self-learning task navigation.

---

## Skills in this repo

| Skill | Description | Standalone |
|-------|-------------|-----------|
| [`doc-pilot`](skills/doc-pilot/) | Main navigator: fetch → classify → navigate → learn | ✅ Primary entry point |
| [`doc-pilot-pdf`](skills/doc-pilot-pdf/) | Layout-aware PDF → Markdown (font hierarchy, TOC, figures) | ✅ Use alone to extract PDFs |
| [`doc-pilot-analyst`](skills/doc-pilot-analyst/) | Semantic section classifier (troubleshooting / installation / etc.) | ✅ Use alone to analyse docs |

---

## What makes this different from just asking Claude

| | Ask Claude directly | doc-pilot |
|--|---|---|
| Document source | Manual paste | Auto-fetch (PDF / URL / search) |
| Output | One-time answer | Stateful step-by-step with ✅/❌ |
| Failure handling | Re-ask | Branch to next approach |
| Cross-session memory | None | Persists task progress |
| **Learning** | **Resets every time** | **Accumulates templates — same doc types get faster** |
| **Skill awareness** | **None** | **Tracks which helper skills work best per task type** |

---

## Installation

```bash
# Clone into your Claude skills directory
git clone https://github.com/<you>/doc-pilot-skills ~/.claude/skills/doc-pilot-suite

# Symlink each skill
ln -s ~/.claude/skills/doc-pilot-suite/skills/doc-pilot       ~/.claude/skills/doc-pilot
ln -s ~/.claude/skills/doc-pilot-suite/skills/doc-pilot-pdf   ~/.claude/skills/doc-pilot-pdf
ln -s ~/.claude/skills/doc-pilot-suite/skills/doc-pilot-analyst ~/.claude/skills/doc-pilot-analyst

# Install the only external dependency (for PDF extraction)
pip install pymupdf
```

---

## Usage examples

```
"Help me fix my Bosch dishwasher showing E9 error"
→ doc-pilot auto-triggers, fetches manual, navigates troubleshooting steps

"Extract the structure of this PDF: /path/to/manual.pdf"
→ doc-pilot-pdf extracts with font hierarchy, TOC, figure registry

"What sections does this manual cover?" + paste Markdown
→ doc-pilot-analyst classifies sections by type with confidence scores
```

---

## The Learning Flywheel

```
First use of a document type
  → Claude reads doc → generates TaskPlan
  → User completes steps (✅/❌ feedback recorded)
  → Outcome written to memory/templates/

Next time same document type appears
  → Template matched → steps reused (with historical success rates)
  → Failing steps flagged proactively
  → EWMA updates: new_rate = 0.2 × result + 0.8 × history

Skill meta-learning
  → When doc-pilot uses another Claude skill (translation, search, etc.)
  → Records whether it helped for that task type
  → Prefers proven skills on future similar tasks
```

Templates are stored locally in `~/.claude/skills/doc-pilot/memory/` — private by default.
You can share template JSON files with others to bootstrap their experience library.

---

## Supported document types

- Home appliance manuals (Bosch, Miele, Dyson, Panasonic, ...)
- IKEA / furniture assembly guides
- Kubernetes / Docker / DevOps deployment docs
- API integration documentation (Stripe, Twilio, ...)
- Medical device instructions
- Tax and government forms
- Firmware update procedures
- Cooking programs (appliance-specific recipes)

---

## Architecture

```
doc-pilot/
├── SKILL.md                    ← Main trigger + workflow instructions
├── references/
│   └── doc_types.md            ← Document type recognition guide
├── scripts/
│   ├── fetch_doc.py            ← Acquisition strategy + CognoLiving cache
│   ├── task_state.py           ← TaskPlan state machine (JSON persistence)
│   └── template_store.py       ← Template CRUD + EWMA + skill performance tracking
└── memory/                     ← Auto-generated at runtime
    ├── tasks/                  ← Per-task JSON (full execution trace)
    ├── templates/              ← Per-document-type learned templates
    └── skill_performance.json  ← External skill effectiveness tracking

doc-pilot-pdf/
├── SKILL.md
└── scripts/
    └── extract.py              ← Font hierarchy + TOC + dedup + spec tables

doc-pilot-analyst/
├── SKILL.md
└── scripts/
    └── analyse.py              ← 9-category classifier + figure registry
```

---

## Contributing

Template JSON files in `memory/templates/` are the most valuable contribution.
Each template represents accumulated real-world experience for a specific document type.
Export yours and open a PR — others can import them to skip the cold-start phase.

---

## License

Apache 2.0
