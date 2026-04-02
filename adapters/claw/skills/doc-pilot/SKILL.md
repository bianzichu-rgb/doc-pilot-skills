---
name: doc-pilot
description: >
  Turns any document into a step-by-step task navigator that gets smarter every use.
  Trigger automatically when users say: "help me do X step by step", "walk me through",
  "how do I install/fix/configure/set up", "I need to complete X", "take me through this",
  "step by step guide", "navigate me through", "帮我一步步做", "怎么安装/修复/配置",
  "带我做", "逐步操作". Supports PDF files (via doc-pilot-pdf), URLs, and local Markdown.
  Handles manuals, deployment docs, IKEA assembly, API guides, medical instructions —
  any procedural document. Local template library learns from every task completion.
emoji: 🧭
triggers:
  - "walk me through"
  - "step by step"
  - "help me fix"
  - "how do I install"
  - "how do I configure"
  - "navigate me through"
  - "帮我一步步"
  - "逐步操作"
  - "怎么安装"
  - "帮我修"
metadata.openclaw.os: ["darwin", "linux", "win32"]
metadata.openclaw.requires.bins: ["python3"]
metadata.openclaw.requires.pip: ["pymupdf"]
hooks:
  onSessionEnd:
    script: scripts/consolidate_learnings.py
---

# doc-pilot

**Turns any document into a step-by-step task navigator. Gets smarter every use.**

---
<!-- Live experience injection — executed before the agent reads this file -->
**Known navigation patterns (from past completions):**
!`python3 ~/.openclaw/skills/doc-pilot/scripts/template_store.py list-templates 2>/dev/null || echo "No templates yet"`

**Top-performing helper skills:**
!`python3 ~/.openclaw/skills/doc-pilot/scripts/template_store.py skill-stats 2>/dev/null || echo "No skill data yet"`

**Recent session log:**
!`tail -20 ~/.openclaw/skills/doc-pilot/memory/session_log.md 2>/dev/null || echo "No session log yet"`
---

## Core Workflow

```
1. Understand what the user wants to accomplish
2. Obtain the document (PDF / URL / local file / search)
3. Classify relevant sections (call doc-pilot-analyst if helpful)
4. Check template library for this document type
5. Generate or reuse a TaskPlan (3-6 steps)
6. Present Step 1 with detailed instructions
7. Wait for user feedback (✅ Done / ❌ Failed)
8. Advance or branch, record outcome
9. On completion: update template library
```

---

## Agent Dispatch (Capability Routing)

Before invoking any helper capability, query the dispatch layer:

```bash
python3 ~/.openclaw/skills/doc-pilot/scripts/agent_dispatch.py best-agent \
  --capability pdf_extraction --task-type "appliance_manual"
```

After using an agent, record the outcome:
```bash
python3 ~/.openclaw/skills/doc-pilot/scripts/agent_dispatch.py record \
  --agent "doc-pilot-pdf" --capability "pdf_extraction" \
  --task-type "appliance_manual" --outcome ok
```

---

## Step 1: Document Acquisition

### Local PDF
```bash
python3 ~/.openclaw/skills/doc-pilot-pdf/scripts/extract.py "<pdf_path>" --output /tmp/doc_extracted.md
```

### URL
Fetch the URL content using your available web tool.

### Local Markdown / text
Read the file directly.

### Unknown source — search first
Search for `"<product> <model> manual pdf"` then fetch the best result.

---

## Step 2: Section Classification (optional, for long documents)

```bash
python3 ~/.openclaw/skills/doc-pilot-analyst/scripts/analyse.py /tmp/doc_extracted.md --filter troubleshooting
```

---

## Step 3: Template Lookup

```bash
python3 ~/.openclaw/skills/doc-pilot/scripts/template_store.py lookup \
  --task-type "<fault_diagnosis|installation|maintenance|setup|recipe>" \
  --product "<product_category>" \
  --brand "<brand_if_known>" \
  --fault-code "<error_code_if_any>"
```

---

## Step 4: Generate TaskPlan

Create a structured plan with 3–6 steps. Rules:
- Start with the simplest, most likely solution
- Order from user-self-serviceable → requires professional help
- Each step title ≤ 10 words

**Output format:**

```
## 📋 Task: [task_summary]
**Steps:** [N total]  |  **Estimated:** [X–Y min]

**Step 1 of N: [title]**
1. [sub-step with expected outcome]
2. [sub-step]
3. [sub-step]

---
✅ Done, next step  |  ❌ Didn't work, try another way
```

---

## Step 5: Handle User Feedback

When user signals ✅:
```bash
python3 ~/.openclaw/skills/doc-pilot/scripts/task_state.py advance \
  --task-id "<task_id>" --action completed
```

When user signals ❌:
```bash
python3 ~/.openclaw/skills/doc-pilot/scripts/task_state.py advance \
  --task-id "<task_id>" --action failed
```

---

## Step 6: Task Completion

```bash
python3 ~/.openclaw/skills/doc-pilot/scripts/task_state.py complete \
  --task-id "<task_id>" --outcome "<self_resolved|escalated|abandoned>"

python3 ~/.openclaw/skills/doc-pilot/scripts/template_store.py record \
  --task-id "<task_id>"
```

---

## Rules

- Never hallucinate steps — only generate steps grounded in the document content
- If the document doesn't cover the user's question, say so and offer to search
- Always show progress: "Step 2 of 4 — [title]"
- When a step fails repeatedly, suggest escalation to professional help
- If template has a known high-failure step, warn the user proactively
