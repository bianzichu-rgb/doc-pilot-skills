---
name: doc-pilot
description: >
  Turns any document into a step-by-step task navigator that gets smarter every use.
  Trigger automatically when users say: "help me do X step by step", "walk me through",
  "how do I install/fix/configure/set up", "I need to complete X", "take me through this",
  "step by step guide", "navigate me through", "帮我一步步做", "怎么安装/修复/配置",
  "带我做", "逐步操作". Supports PDF files (via doc-pilot-pdf), URLs (WebFetch),
  and any local Markdown. Handles manuals, deployment docs, IKEA assembly, API guides,
  medical instructions, tax forms — any procedural document. Core differentiator:
  local template library learns from every task completion — same document types get
  faster and more accurate over time. Also learns which external Claude skills perform
  best for different document types.
allowed-tools: WebFetch, WebSearch, Read, Write, Glob, Bash(python *)
hooks:
  onSessionEnd:
    script: scripts/consolidate_learnings.py
---

# doc-pilot

**Turns any document into a step-by-step task navigator. Gets smarter every use.**

---
<!-- Live experience injection — executed before Claude reads this file, zero token overhead -->
**Known navigation patterns (from past completions):**
!`python ~/.claude/skills/doc-pilot/scripts/template_store.py list-templates 2>/dev/null || echo "No templates yet"`

**Top-performing helper skills:**
!`python ~/.claude/skills/doc-pilot/scripts/template_store.py skill-stats 2>/dev/null || echo "No skill data yet"`

**Recent session log:**
!`tail -20 ~/.claude/skills/doc-pilot/memory/session_log.md 2>/dev/null || echo "No session log yet"`
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

Before invoking any helper capability, query the dispatch layer to select the best available agent:

```bash
# Which agent should handle PDF extraction for this task type?
python ~/.claude/skills/doc-pilot/scripts/agent_dispatch.py best-agent \
  --capability pdf_extraction --task-type "appliance_manual"

# Which agent handles translation?
python ~/.claude/skills/doc-pilot/scripts/agent_dispatch.py best-agent \
  --capability translation

# List all agents that support a capability
python ~/.claude/skills/doc-pilot/scripts/agent_dispatch.py list-agents \
  --capability fault_diagnosis
```

After using an agent, record the outcome so the dispatcher learns:
```bash
python ~/.claude/skills/doc-pilot/scripts/agent_dispatch.py record \
  --agent "doc-pilot-pdf" --capability "pdf_extraction" \
  --task-type "appliance_manual" --outcome ok
```

**Agent types in the registry** (`memory/agent_registry.json`):

| Type | Examples | Use case |
|------|----------|----------|
| `claude_skill` | doc-pilot-pdf, doc-pilot-analyst | Structured extraction / classification |
| `claude_api` | claude-haiku, claude-sonnet, claude-opus | Direct LLM call (translation, complex reasoning, safety-critical) |
| `claude_tool` | WebSearch, WebFetch | Online search / URL fetch |

`claude_api` agents are **disabled by default** — enable them in `memory/agent_registry.json` once `ANTHROPIC_API_KEY` is set. The dispatcher automatically routes to the highest-performing enabled agent for each capability.

---

## Step 1: Document Acquisition

### Local PDF
```bash
python ~/.claude/skills/doc-pilot-pdf/scripts/extract.py "<pdf_path>" --output /tmp/doc_extracted.md
```
Then: `Read /tmp/doc_extracted.md`

### URL
Use `WebFetch <url>` to get the page content.

### Local Markdown / text
Use `Read <path>` directly.

### Unknown source — search first
Use `WebSearch "<product> <model> manual pdf"` then WebFetch the best result.

---

## Step 2: Section Classification (optional, use for long documents)

```bash
python ~/.claude/skills/doc-pilot-analyst/scripts/analyse.py /tmp/doc_extracted.md --filter troubleshooting
```

Use the output to focus on the relevant section rather than sending the whole document.

---

## Step 3: Template Lookup

```bash
python ~/.claude/skills/doc-pilot/scripts/template_store.py lookup \
  --task-type "<fault_diagnosis|installation|maintenance|setup|recipe>" \
  --product "<product_category>" \
  --brand "<brand_if_known>" \
  --fault-code "<error_code_if_any>"
```

If a template is returned, use its steps as the base plan (show the historical success rate
and common failure points to the user). If no template, proceed to LLM generation.

---

## Step 4: Generate TaskPlan

Create a structured plan with 3–6 steps. Rules:
- Start with the simplest, most likely solution
- Order from user-self-serviceable → requires professional help
- Each step title ≤ 10 words
- Step 1 detail: 3–5 numbered sub-steps with expected outcomes

**Output format** (present to user):

```
## 📋 Task: [task_summary]
**Steps:** [N total]  |  **Estimated:** [X–Y min]

**Step 1 of N: [title]**
1. [sub-step with expected outcome]
2. [sub-step]
3. [sub-step]
...

---
✅ Done, next step  |  ❌ Didn't work, try another way
```

---

## Step 5: Handle User Feedback

When user signals ✅ (done / completed / worked / 好了 / 成功):
```bash
python ~/.claude/skills/doc-pilot/scripts/task_state.py advance \
  --task-id "<task_id>" --action completed
```

When user signals ❌ (failed / not working / 没用 / 还是不行):
```bash
python ~/.claude/skills/doc-pilot/scripts/task_state.py advance \
  --task-id "<task_id>" --action failed
```

Then present the next step detail based on the updated task state.

---

## Step 6: Task Completion

When all steps done (any outcome), record the result:
```bash
python ~/.claude/skills/doc-pilot/scripts/task_state.py complete \
  --task-id "<task_id>" --outcome "<self_resolved|escalated|abandoned>"

python ~/.claude/skills/doc-pilot/scripts/template_store.py record \
  --task-id "<task_id>"
```

This updates the template library with EWMA-smoothed success rates.

---

## Skill Performance Tracking (Meta-Learning)

When you use an external Claude skill during a task (e.g., a search skill, a translation
skill, a code-execution skill), record whether it helped:

```bash
python ~/.claude/skills/doc-pilot/scripts/template_store.py skill-feedback \
  --skill-name "<skill_name>" \
  --task-type "<task_type>" \
  --outcome "<helpful|not_helpful|error>" \
  --notes "<optional one-line note>"
```

The skill performance log (`memory/skill_performance.json`) accumulates over time.
Before using an external skill for a task type, check its historical performance:

```bash
python ~/.claude/skills/doc-pilot/scripts/template_store.py skill-stats \
  --task-type "<task_type>"
```

This is part of the learning flywheel: doc-pilot learns not just which task steps work,
but also which helper skills are most reliable for which document types.

---

## Task State Format

Tasks are persisted to `~/.claude/skills/doc-pilot/memory/tasks/<task_id>.json`.
Each task records: steps, completion path, failure path, duration, template source.

---

## Rules

- Never hallucinate steps — only generate steps grounded in the document content
- If the document doesn't cover the user's question, say so and offer to search
- Always show progress: "Step 2 of 4 — [title]"
- When a step fails repeatedly, suggest escalation to professional help
- Keep step titles short and action-oriented ("Check the drain filter", not "You should look at the drain filter area")
- If template has a known high-failure step, warn the user proactively

---

## Example Triggers

| User says | doc-pilot does |
|-----------|----------------|
| "My Bosch dishwasher shows E9, help me fix it" | Searches for manual, identifies TROUBLESHOOTING section, generates fault-diagnosis plan |
| "Walk me through setting up Kubernetes ingress" | WebFetch official docs, generates installation plan |
| "IKEA KALLAX assembly, step by step" | Fetches PDF, extracts with doc-pilot-pdf, navigates assembly |
| "帮我一步步蒸东星斑" | Fetches/reads appliance manual for steam function, generates cooking navigation |

---

## Self-Learning Architecture

### Live Experience Injection (Zero Context Cost)

At the start of any task, pull live experience summaries without loading full files:

```bash
# Check if we have templates for this task type (fast — only prints summary)
python ~/.claude/skills/doc-pilot/scripts/template_store.py list-templates --task-type "<type>"

# Check skill performance before invoking an external skill
python ~/.claude/skills/doc-pilot/scripts/template_store.py skill-stats --task-type "<type>"
```

Only load a full template (`show-template`) when a match is found. This keeps context lean.

### Session-End Consolidation (Auto Hook)

At session end, `scripts/consolidate_learnings.py` runs automatically and:
1. Scans all tasks completed this session
2. Identifies patterns (steps that always fail, steps that always succeed)
3. Updates template success rates
4. Writes a human-readable `memory/session_log.md` entry

### Reflection Loop (When a Task Goes Wrong)

If a user abandons a task or all steps fail, run a reflection pass:

```
Reflection prompt: "This task failed. Steps attempted: [X, Y, Z].
Last error: [description]. What should the step plan have been?
Suggest an improved step sequence for next time."
```

Write the reflection output to `memory/templates/<key>_reflection.md`.
On the next similar task, Read this file before generating the new plan.

### Navigation Pattern Library

Successful navigation sequences are distilled into `references/navigation_patterns.md`.
Read this file at the start of tasks that match a known pattern. It contains:
- Proven step sequences for common task types
- Known failure points and their workarounds
- Time estimates based on real completion data
