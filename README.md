[English](#english) | [中文](#中文)

---

<a name="english"></a>

# doc-pilot

> Navigate any document, step by step. Gets smarter every use.

**doc-pilot is a host-agnostic document navigation engine** for manuals, PDFs, and long documents.
It fetches the right document, finds the relevant section, guides you step by step,
and learns from every completion — so similar tasks start faster next time.

It can be packaged as a **skill, tool, or workflow adapter** inside different agent runtimes.

[![License](https://img.shields.io/badge/license-Apache%202.0-blue.svg)](LICENSE)
[![PyMuPDF](https://img.shields.io/badge/PDF-PyMuPDF%20AGPL3-orange.svg)](https://pymupdf.readthedocs.io/)
[![Claude Code](https://img.shields.io/badge/adapter-Claude%20Code-blueviolet.svg)](https://claude.ai/code)
[![Claw](https://img.shields.io/badge/adapter-OpenClaw-brightgreen.svg)](https://openclaw.ai)
[![CLI](https://img.shields.io/badge/adapter-CLI%20%2F%20standalone-blue.svg)](#quick-start--cli--standalone)

> This repository ships adapters for **Claude Code**, **OpenClaw**, and a **standalone CLI**.
> The core engine is host-agnostic — same Python scripts run everywhere.

---

## Use Cases

| Scenario | How doc-pilot helps |
|----------|---------------------|
| 🏠 **Smart home systems** | Let your LLM guide users through appliance installation, configuration, and troubleshooting — grounded in the actual manual |
| 🔧 **After-sales & repair assistants** | Turn device handbooks into executable step-by-step fault diagnosis flows with branching and failure memory |
| 🏢 **Enterprise doc assistants** | Convert SOPs, ops runbooks, and process docs into trackable task navigation with cross-session progress |
| 🤖 **Agent toolchains** | Embed as a host-agnostic document navigation engine into any agent runtime (Claude Code, OpenClaw, custom) |

---

## 应用场景

| 场景 | doc-pilot 的作用 |
|------|-----------------|
| 🏠 **家庭智能系统** | 让大模型根据家电说明书指导用户完成安装、配置和故障排查 |
| 🔧 **售后与维修助手** | 把设备手册转成可执行的分步排障流程，支持失败分支和历史记忆 |
| 🏢 **企业文档助手** | 把 SOP、运维手册和流程文档转成可跨会话跟踪进度的任务导航 |
| 🤖 **Agent 工具链** | 作为宿主无关的文档导航引擎，接入 Claude Code、OpenClaw 或自定义 runtime |

---

## How is this different?

| | Direct LLM | RAG / PDF parser | doc-pilot |
|--|--|--|--|
| Finds the document for you | ✗ | ✗ | ✅ |
| Step-by-step with ✅ / ❌ branching | ✗ | ✗ | ✅ |
| Stateful — picks up where you left off | ✗ | ✗ | ✅ |
| Cross-session memory | ✗ | ✗ | ✅ |
| Learns from completions | ✗ | ✗ | ✅ |
| Routes to best agent per task | ✗ | ✗ | ✅ |
| Portable across agent runtimes | ✗ | ✗ | ✅ |

Not just document extraction. Not just question answering. Not just workflow memory.

---

## Demo

```
Invoke from your agent host:
  "My Bosch dishwasher is showing E9. Help me fix it."

doc-pilot:
  ✦ Fetching Bosch SGS4HMI61E manual...
  ✦ Classified section: TROUBLESHOOTING (confidence 0.94)
  ✦ Template matched: bosch_e9_water_inlet
    └─ success rate 87%  |  6 prior completions  |  avg 14 min

  📋 Fix E9 — Water Inlet Fault   Steps: 4   Est: 10–20 min

  ▶ Step 1 of 4: Check water supply valve
    1. Locate the valve behind the machine (bottom-left)
    2. Confirm it is fully open (counter-clockwise)
    3. Expected: water flows when tap is run nearby

  ✅ Done, next step   ❌ Didn't work, try another way

  ▶ Step 2 of 4: Clean the inlet filter
    ⚠  Known failure point — affects 27% of attempts at this step
    1. Turn off water supply, unscrew the inlet hose
    2. Remove mesh filter with pliers — rinse under tap
```

---

## Host Integrations

doc-pilot's core workflow is portable. The host is responsible for:
receiving user input, providing file/network access, and executing prompts.

| Host | Status | Install |
|------|--------|---------|
| Claude Code (skills) | ✅ Available | [Quick Start →](#quick-start--claude-code) |
| OpenClaw (skills) | ✅ Available | [Quick Start →](#quick-start--openclaw) |
| CLI / standalone | ✅ Available | [Quick Start →](#quick-start--cli--standalone) |
| Other agent runtimes | 🔜 Adaptable | [Integration contract →](#host-integration-contract) |

---

## Quick Start — Claude Code

**Prerequisites:** Claude Code · Python 3.8+ · `pip install pymupdf`

```bash
git clone https://github.com/bianzichu-rgb/doc-pilot-skills ~/.claude/skills/doc-pilot-suite

ln -s ~/.claude/skills/doc-pilot-suite/skills/doc-pilot         ~/.claude/skills/doc-pilot
ln -s ~/.claude/skills/doc-pilot-suite/skills/doc-pilot-pdf     ~/.claude/skills/doc-pilot-pdf
ln -s ~/.claude/skills/doc-pilot-suite/skills/doc-pilot-analyst ~/.claude/skills/doc-pilot-analyst

pip install pymupdf
```

Verify it works in 3 steps — in order:

```
# 1 — Does it find documents?
"Help me troubleshoot Bosch SGS4HMI61E E9 error"

# 2 — Does it build a step plan?
"Walk me through this PDF: ./manuals/router_setup.pdf"

# 3 — Does it remember? (run again after completing #1)
"My Bosch dishwasher shows E9 again"
```

**Expected output after step 1:**
```
✓ Fetched manual (SGS4HMI61E, 48 pages)
✓ Classified section: TROUBLESHOOTING
✓ Built 4-step plan
✓ Saved reusable template → bosch_e9_water_inlet.json
```

**Expected output after step 3 (second run):**
```
✓ Template matched: bosch_e9_water_inlet
  success rate 87%  |  prior completions: 1  ← your run recorded
  Known issue at Step 2: inlet filter (27% fail rate)
```

---

## Quick Start — OpenClaw

**Prerequisites:** [OpenClaw](https://openclaw.ai) installed · Python 3.8+ · `pip install pymupdf`

```bash
git clone https://github.com/bianzichu-rgb/doc-pilot-skills
cd doc-pilot-skills
bash adapters/claw/install.sh
```

The installer symlinks the shared engine scripts into `~/.openclaw/skills/` and copies
the OpenClaw-adapted `SKILL.md` files (with `metadata.openclaw.*` fields and emoji triggers).

Then in OpenClaw, just say:
```
"帮我修博世洗碗机 E9 故障"
"Walk me through this PDF: /path/to/manual.pdf"
```

The skills auto-trigger on matching phrases. All three sub-skills
(`doc-pilot`, `doc-pilot-pdf`, `doc-pilot-analyst`) are available in the
[ClawHub](https://clawhub.openclaw.ai) marketplace — search `doc-pilot`.

---

## Quick Start — CLI / Standalone

No agent runtime needed. Works with or without an API key.

```bash
git clone https://github.com/bianzichu-rgb/doc-pilot-skills
cd doc-pilot-skills
pip install pymupdf
```

**With a local PDF:**
```bash
python adapters/cli/doc_pilot_cli.py \
  --task "Fix E9 error on my dishwasher" \
  --doc /path/to/bosch_manual.pdf \
  --task-type fault_diagnosis --brand bosch --fault-code E9
```

**Using a saved template (no document needed):**
```bash
# List available templates
python adapters/cli/doc_pilot_cli.py --list-templates

# Run with template match
python adapters/cli/doc_pilot_cli.py \
  --task "Fix E9" --task-type fault_diagnosis --brand bosch --fault-code E9
```

**With automatic plan generation (requires `ANTHROPIC_API_KEY`):**
```bash
export ANTHROPIC_API_KEY=sk-ant-...
python adapters/cli/doc_pilot_cli.py \
  --task "Set up Nginx reverse proxy" --doc /path/to/nginx_guide.pdf
```

**Without an API key** — CLI extracts and classifies the document, then prints
a structured prompt ready to paste into any LLM (ChatGPT, Claude.ai, etc.):
```
📋 Paste this into any LLM to generate your step plan:
──────────────────────────────────────────────────────
Task: Fix E9 error on my dishwasher
Document sections: [TROUBLESHOOTING] Error Codes (p.12-15)
...
```

---

## Adapter comparison

| Feature | Claude Code | OpenClaw | CLI |
|---------|-------------|----------|-----|
| Install | symlink to `~/.claude/skills/` | `bash adapters/claw/install.sh` | `python adapters/cli/doc_pilot_cli.py` |
| Trigger | natural language | natural language + emoji | `--task` flag |
| URL fetch | ✅ (WebFetch tool) | ✅ (built-in browser) | ⚠️ manual paste |
| Template memory | ✅ | ✅ | ✅ |
| API plan gen | via host LLM | via host LLM | via `ANTHROPIC_API_KEY` |
| Session hook | ✅ onSessionEnd | ✅ onSessionEnd | manual |

---

## Quick Start — Generic Host

The core engine requires no framework. Any host that can:
- pass a user prompt to an LLM
- execute Python scripts
- read/write local files

...can run doc-pilot. Full integration contract → [see below](#host-integration-contract).

```bash
# Standalone PDF extraction (no host needed)
python skills/doc-pilot-pdf/scripts/extract.py ./manual.pdf --output ./manual.md

# Standalone section classification
python skills/doc-pilot-analyst/scripts/analyse.py ./manual.md

# Standalone template lookup
python skills/doc-pilot/scripts/template_store.py lookup \
  --task-type fault_diagnosis --product dishwasher --brand bosch --fault-code E9
```

---

## What it learns

<details>
<summary>Example: learned template JSON</summary>

```json
{
  "template_id": "bosch_e9_water_inlet",
  "task_type": "fault_diagnosis",
  "product_category": "dishwasher",
  "brand": "bosch",
  "fault_code": "E9",
  "completion_rate": 0.87,
  "usage_count": 6,
  "avg_duration_sec": 847,
  "steps": [
    { "step_id": "s1", "title": "Check water supply valve",      "historical_fail_rate": 0.12, "run_count": 6 },
    { "step_id": "s2", "title": "Clean the inlet filter",        "historical_fail_rate": 0.27, "run_count": 5 },
    { "step_id": "s3", "title": "Test inlet valve solenoid",     "historical_fail_rate": 0.40, "run_count": 3 },
    { "step_id": "s4", "title": "Call service — replace valve",  "historical_fail_rate": 0.00, "run_count": 1 }
  ]
}
```

</details>

<details>
<summary>Example: live task state (cross-session persistence)</summary>

```json
{
  "task_id": "task_20260402_bosch_e9",
  "summary": "Fix E9 water inlet fault — Bosch SGS4HMI61E",
  "current_step": 2,
  "completed_steps": ["s1"],
  "failure_path": ["s1"],
  "final_outcome": null,
  "started_at": "2026-04-02T09:14:00Z",
  "template_source": "bosch_e9_water_inlet"
}
```

Resume in a later session: `"Continue my dishwasher repair"`

</details>

---

## Core Capabilities

- 📄 **Auto-fetch** — PDF path, URL, or product name → engine finds the document
- 🏗️ **Layout-aware extraction** — font hierarchy, dual-column, TOC, spec tables preserved
- 🗂️ **Section classifier** — 9 semantic categories so long manuals don't overwhelm context
- 🧠 **Template memory** — proven step plans reused; high-failure steps flagged proactively
- 📈 **EWMA learning** — success rates update per completion (α=0.2); no manual curation
- 🤖 **Multi-agent dispatch** — routes to best available agent per capability + task type
- 🔁 **Session consolidation** — auto-distills patterns after every session

---

## How the learning loop works

```
First run on a document type
  → generates TaskPlan from document content
  → records each step outcome  ✅ / ❌
  → saves template to memory/templates/

Second run on same document type
  → matches template → reuses proven steps
  → warns on steps with >20% historical fail rate
  → EWMA update:  rate = 0.2 × result + 0.8 × history

Multi-agent learning
  → tracks which agent performed best per capability + task type
  → routes to the proven winner next time
```

---

## Engine Architecture

```
core engine
├── fetch_doc.py       ← acquisition: PDF / URL / web search
├── task_state.py      ← stateful step machine (JSON persistence)
├── template_store.py  ← CRUD + EWMA learning flywheel
└── agent_dispatch.py  ← capability router (skill / API / tool)

host adapters (current: Claude Code skills)
├── doc-pilot/         ← orchestrator SKILL.md + scripts
├── doc-pilot-pdf/     ← PDF → Markdown adapter
└── doc-pilot-analyst/ ← section classifier adapter

memory/ (local, gitignored)
├── templates/         ← learned step plans per document type
├── agent_registry.json← agent capabilities + routing config
└── skill_performance.json
```

---

## Host Integration Contract

To integrate doc-pilot into a new agent runtime, the host must provide:

| Requirement | Notes |
|-------------|-------|
| Prompt execution | Pass user input to an LLM with tool-use or function-call support |
| File system access | Read/write to a local `memory/` directory for state + templates |
| Python 3.8+ runtime | For the core engine scripts |
| `pip install pymupdf` | PDF extraction only — optional if PDF support is not needed |

**Minimum integration flow:**
```
user_input
  → [host] route to doc-pilot orchestrator
  → fetch_doc.py  (determine acquisition strategy)
  → extract.py    (if PDF — optional)
  → analyse.py    (if long doc — optional)
  → template_store.py lookup (check for prior completions)
  → [LLM] generate or reuse TaskPlan
  → task_state.py (stateful step tracking)
  → [host] present steps, collect ✅/❌ feedback
  → template_store.py record (update learning)
```

The host does not need to implement memory, routing, or learning —
those are handled by the engine scripts.

---

## Limitations

- **Structured documents work best** — repair manuals, setup guides, troubleshooting trees
- **Scanned PDFs not yet supported** — image-only PDFs require OCR (on roadmap)
- **Template quality needs volume** — ≥3 similar completions before template creation; first runs use LLM generation
- **`claude_api` agents disabled by default** — direct API routing requires `ANTHROPIC_API_KEY` and opt-in in `memory/agent_registry.json`
- **Web fetch quality varies** — depends on source availability and document structure

---

## Roadmap

- [x] Claude Code adapter
- [x] OpenClaw adapter
- [x] Standalone CLI adapter
- [ ] OCR fallback for scanned PDFs
- [ ] `template export --sanitize` — strip device identifiers before sharing
- [ ] Sample template library for common appliance brands (Bosch, Miele, LG, Dyson)
- [ ] Template version history + rollback
- [ ] Web UI adapter (FastAPI + simple frontend)

---

## Contributing

**Most valuable:** a `memory/templates/*.json` file.
Each one is real accumulated experience on a document type that others can import.

1. Complete a task with doc-pilot
2. Find the template in `~/.claude/skills/doc-pilot/memory/templates/`
3. Remove personal identifiers (serial numbers, custom names)
4. Open a PR

**Test locally:**
```bash
python skills/doc-pilot-pdf/scripts/extract.py ./manual.pdf
python skills/doc-pilot-analyst/scripts/analyse.py ./extracted.md
python skills/doc-pilot/scripts/template_store.py lookup \
  --task-type fault_diagnosis --product dishwasher --brand bosch --fault-code E9
```

---

## License

Apache 2.0.

`doc-pilot-pdf` depends on [PyMuPDF](https://pymupdf.readthedocs.io/) (AGPL 3.0).
Redistribution including `doc-pilot-pdf` requires AGPL compliance.
[Commercial licenses](https://artifex.com/) available from Artifex.

---
---

<a name="中文"></a>

# doc-pilot

> 逐步导航任何文档，越用越聪明。

**doc-pilot 是一个宿主无关的文档任务导航引擎**，适用于说明书、PDF 和长文档。
它先找到正确的文档，定位相关章节，一步步带你完成任务，
并把每次完成经验沉淀下来——让下次同类任务更快开始。

它可以被封装成 **skill、tool 或 workflow adapter**，接入不同的 agent 运行环境。

[![许可证](https://img.shields.io/badge/许可证-Apache%202.0-blue.svg)](LICENSE)
[![Claude Code](https://img.shields.io/badge/适配器-Claude%20Code-blueviolet.svg)](https://claude.ai/code)
[![OpenClaw](https://img.shields.io/badge/适配器-OpenClaw-brightgreen.svg)](https://openclaw.ai)
[![CLI](https://img.shields.io/badge/适配器-CLI%20独立运行-blue.svg)](#快速开始--cli--独立运行)

> 本仓库提供 **Claude Code**、**OpenClaw** 和**独立 CLI** 三种适配器。
> 核心引擎宿主无关——同一套 Python 脚本在所有环境中运行。

---

## 和现有方案有什么不同？

| | 直接问模型 | RAG / PDF 解析器 | doc-pilot |
|--|--|--|--|
| 自动找文档 | ✗ | ✗ | ✅ |
| 有 ✅ / ❌ 分支的逐步引导 | ✗ | ✗ | ✅ |
| 有状态——可继续上次进度 | ✗ | ✗ | ✅ |
| 跨会话记忆 | ✗ | ✗ | ✅ |
| 从完成记录中学习 | ✗ | ✗ | ✅ |
| 按任务类型调度最优智能体 | ✗ | ✗ | ✅ |
| 可移植到不同 agent 宿主 | ✗ | ✗ | ✅ |

不只是文档提取，不只是问答，不只是流程记录。

---

## 演示

```
在你的 agent 宿主中调用：
  "我的博世洗碗机显示 E9，帮我修。"

doc-pilot:
  ✦ 正在获取博世 SGS4HMI61E 说明书...
  ✦ 章节分类：故障排除（置信度 0.94）
  ✦ 匹配模板：bosch_e9_water_inlet
    └─ 成功率 87%  |  已完成 6 次  |  平均用时 14 分钟

  📋 修复 E9 — 进水故障   步骤：4 步   预计：10–20 分钟

  ▶ 第 1 步 / 共 4 步：检查进水阀
    1. 找到机器后面左下角的进水阀
    2. 确认已完全逆时针拧开（开启状态）
    3. 预期结果：打开附近水龙头时有水流

  ✅ 完成，下一步   ❌ 没用，换个方法

  ▶ 第 2 步 / 共 4 步：清洁进水过滤网
    ⚠  已知高失败率步骤 — 历史上 27% 的尝试在此卡住
```

---

## 宿主集成

doc-pilot 的核心工作流是可移植的。宿主需要提供：接收用户输入、访问文件和网络、执行 prompt。

| 宿主 | 状态 | 安装方式 |
|------|------|---------|
| Claude Code（skills） | ✅ 已支持 | [快速开始 →](#快速开始--claude-code) |
| OpenClaw（skills） | ✅ 已支持 | [快速开始 →](#快速开始--openclaw) |
| CLI / 独立运行 | ✅ 已支持 | [快速开始 →](#快速开始--cli--独立运行) |
| 其他 agent runtime | 🔜 可适配 | [集成接口说明 →](#宿主集成接口) |

---

## 快速开始 — Claude Code

**前置条件：** Claude Code · Python 3.8+ · `pip install pymupdf`



```bash
git clone https://github.com/bianzichu-rgb/doc-pilot-skills ~/.claude/skills/doc-pilot-suite

ln -s ~/.claude/skills/doc-pilot-suite/skills/doc-pilot         ~/.claude/skills/doc-pilot
ln -s ~/.claude/skills/doc-pilot-suite/skills/doc-pilot-pdf     ~/.claude/skills/doc-pilot-pdf
ln -s ~/.claude/skills/doc-pilot-suite/skills/doc-pilot-analyst ~/.claude/skills/doc-pilot-analyst

pip install pymupdf
```

按顺序验证 3 件事：

```
# 1 — 它真的能找文档吗？
"帮我排查博世 SGS4HMI61E 的 E9 故障"

# 2 — 它真的会生成分步计划吗？
"帮我逐步读这个 PDF：./manuals/router_setup.pdf"

# 3 — 它真的会记住并复用吗？（完成第 1 次后再运行）
"我的博世洗碗机又显示 E9 了"
```

**第 1 次运行后你应该看到：**
```
✓ 已获取说明书（SGS4HMI61E，48 页）
✓ 章节分类：故障排除
✓ 已生成 4 步计划
✓ 已保存可复用模板 → bosch_e9_water_inlet.json
```

**第 3 次运行后你应该看到：**
```
✓ 匹配模板：bosch_e9_water_inlet
  成功率 87%  |  已完成次数：1  ← 你的记录已被保存
  第 2 步已知问题：进水过滤网堵塞（失败率 27%）
```

---

## 快速开始 — OpenClaw

**前置条件：** [OpenClaw](https://openclaw.ai) · Python 3.8+ · `pip install pymupdf`

```bash
git clone https://github.com/bianzichu-rgb/doc-pilot-skills
cd doc-pilot-skills
bash adapters/claw/install.sh
```

安装完成后，在 OpenClaw 中直接说：
```
"帮我修博世洗碗机 E9 故障"
"帮我逐步读这个 PDF：/path/to/manual.pdf"
```

三个子技能（`doc-pilot`、`doc-pilot-pdf`、`doc-pilot-analyst`）也已上架
[ClawHub](https://clawhub.openclaw.ai)，搜索 `doc-pilot` 即可一键安装。

---

## 快速开始 — CLI / 独立运行

无需任何 agent 运行环境，有没有 API Key 都能用。

```bash
git clone https://github.com/bianzichu-rgb/doc-pilot-skills
cd doc-pilot-skills
pip install pymupdf
```

**使用本地 PDF：**
```bash
python adapters/cli/doc_pilot_cli.py \
  --task "修复洗碗机 E9 故障" \
  --doc /path/to/bosch_manual.pdf \
  --task-type fault_diagnosis --brand bosch --fault-code E9
```

**使用已有模板（不需要文档）：**
```bash
python adapters/cli/doc_pilot_cli.py --list-templates
python adapters/cli/doc_pilot_cli.py \
  --task "修复 E9" --task-type fault_diagnosis --brand bosch --fault-code E9
```

**配置 API Key 自动生成计划：**
```bash
export ANTHROPIC_API_KEY=sk-ant-...
python adapters/cli/doc_pilot_cli.py --task "配置 Nginx 反向代理" --doc /path/to/guide.pdf
```

**没有 API Key** — CLI 提取并分类文档后，打印一段结构化提示词，可直接粘贴到任意 LLM（ChatGPT、Claude.ai 等）。

---

## 适配器对比

| 功能 | Claude Code | OpenClaw | CLI |
|------|-------------|----------|-----|
| 安装 | 软链接到 `~/.claude/skills/` | `bash adapters/claw/install.sh` | `python adapters/cli/doc_pilot_cli.py` |
| 触发方式 | 自然语言 | 自然语言 + emoji 关键词 | `--task` 参数 |
| URL 抓取 | ✅ WebFetch 工具 | ✅ 内置浏览器 | ⚠️ 需手动粘贴 |
| 模板记忆 | ✅ | ✅ | ✅ |
| 计划生成 | 通过宿主 LLM | 通过宿主 LLM | 通过 `ANTHROPIC_API_KEY` |
| 会话钩子 | ✅ onSessionEnd | ✅ onSessionEnd | 手动执行 |

---

## 快速开始 — 通用宿主

核心引擎不依赖任何框架。任何能够：
- 向 LLM 传递用户 prompt
- 执行 Python 脚本
- 读写本地文件

…的宿主都可以运行 doc-pilot。完整接口说明见下方。

```bash
# 单独运行 PDF 提取（无需宿主）
python skills/doc-pilot-pdf/scripts/extract.py ./manual.pdf --output ./manual.md

# 单独运行章节分类
python skills/doc-pilot-analyst/scripts/analyse.py ./manual.md

# 单独运行模板查找
python skills/doc-pilot/scripts/template_store.py lookup \
  --task-type fault_diagnosis --product dishwasher --brand bosch --fault-code E9
```

---

## 它学到了什么

<details>
<summary>示例：已学习的模板 JSON</summary>

```json
{
  "template_id": "bosch_e9_water_inlet",
  "task_type": "fault_diagnosis",
  "product_category": "dishwasher",
  "brand": "bosch",
  "fault_code": "E9",
  "completion_rate": 0.87,
  "usage_count": 6,
  "avg_duration_sec": 847,
  "steps": [
    { "step_id": "s1", "title": "检查进水阀",       "historical_fail_rate": 0.12, "run_count": 6 },
    { "step_id": "s2", "title": "清洁进水过滤网",   "historical_fail_rate": 0.27, "run_count": 5 },
    { "step_id": "s3", "title": "测试进水电磁阀",   "historical_fail_rate": 0.40, "run_count": 3 },
    { "step_id": "s4", "title": "联系维修更换进水阀", "historical_fail_rate": 0.00, "run_count": 1 }
  ]
}
```

</details>

<details>
<summary>示例：实时任务状态（跨会话持久化）</summary>

```json
{
  "task_id": "task_20260402_bosch_e9",
  "summary": "修复 E9 进水故障 — 博世 SGS4HMI61E",
  "current_step": 2,
  "completed_steps": ["s1"],
  "failure_path": ["s1"],
  "final_outcome": null,
  "started_at": "2026-04-02T09:14:00Z",
  "template_source": "bosch_e9_water_inlet"
}
```

下次会话直接说：`"继续我的洗碗机维修"`

</details>

---

## 核心能力

- 📄 **自动获取文档** — PDF 路径、URL 或产品名称，引擎自动找到说明书
- 🏗️ **版面感知提取** — 字体层级、双栏排版、目录、规格表，结构完整保留
- 🗂️ **章节语义分类** — 9 个类别，先定位相关章节再开始步骤导航
- 🧠 **模板记忆** — 沉淀已验证步骤；历史高失败率步骤提前预警
- 📈 **EWMA 自动学习** — 每次完成自动更新成功率（α=0.2），无需人工整理
- 🤖 **多智能体调度** — 按能力 + 任务类型路由到最优智能体
- 🔁 **会话自动汇总** — 每次会话结束后自动提炼导航规律

---

## 学习机制

```
首次使用某类文档
  → 从文档内容生成任务计划
  → 记录每步结果  ✅ / ❌
  → 保存模板到 memory/templates/

再次使用同类文档
  → 匹配模板 → 复用已验证步骤
  → 失败率 >20% 的步骤提前预警
  → EWMA 更新：rate = 0.2 × 新结果 + 0.8 × 历史

多智能体学习
  → 追踪每种能力 + 任务类型的最优智能体
  → 下次自动路由到已验证的最优选项
```

---

## 引擎架构

```
核心引擎（宿主无关）
├── fetch_doc.py       ← 文档获取：PDF / URL / 网络搜索
├── task_state.py      ← 有状态步骤机（JSON 持久化）
├── template_store.py  ← 模板增删改查 + EWMA 学习飞轮
└── agent_dispatch.py  ← 能力路由（技能/API/工具）

宿主适配层（当前：Claude Code skills）
├── doc-pilot/         ← 编排器 SKILL.md + 脚本
├── doc-pilot-pdf/     ← PDF → Markdown 适配器
└── doc-pilot-analyst/ ← 章节分类适配器

memory/（本地，已 gitignore）
├── templates/         ← 每类文档的已学习步骤计划
├── agent_registry.json← 智能体能力 + 路由配置
└── skill_performance.json
```

---

## 宿主集成接口

将 doc-pilot 接入新的 agent runtime，宿主需要提供：

| 需求 | 说明 |
|------|------|
| Prompt 执行 | 将用户输入传递给支持工具调用的 LLM |
| 文件系统访问 | 对本地 `memory/` 目录的读写权限，用于状态和模板 |
| Python 3.8+ 运行时 | 执行核心引擎脚本 |
| `pip install pymupdf` | 仅 PDF 提取需要，其他功能可选 |

**最小集成流程：**
```
用户输入
  → [宿主] 路由到 doc-pilot 编排器
  → fetch_doc.py   （确定文档获取策略）
  → extract.py     （如果是 PDF — 可选）
  → analyse.py     （如果是长文档 — 可选）
  → template_store.py lookup （检查历史模板）
  → [LLM] 生成或复用任务计划
  → task_state.py  （有状态步骤跟踪）
  → [宿主] 呈现步骤，收集 ✅/❌ 反馈
  → template_store.py record （更新学习）
```

宿主不需要实现记忆、路由或学习逻辑——这些都由引擎脚本处理。

---

## 已知限制

- **结构化文档效果最好** — 维修手册、安装指南、故障排除树；叙述性文档提取准确率较低
- **扫描版 PDF 暂不支持** — 纯图片 PDF 需要 OCR，在路线图中
- **模板需要积累** — ≥3 次同类完成才会创建模板，首次总是由 LLM 生成
- **`claude_api` 智能体默认关闭** — 需配置 `ANTHROPIC_API_KEY` 并在 `memory/agent_registry.json` 中手动启用
- **网络抓取质量** — 依赖搜索结果和来源结构，可能因文档来源不同而有差异

---

## 路线图

- [x] Claude Code 适配器
- [x] OpenClaw 适配器
- [x] 独立 CLI 适配器
- [ ] 扫描版 PDF 的 OCR 回退支持
- [ ] `template export --sanitize` — 导出前自动移除设备标识符
- [ ] 常见家电品牌示例模板库（博世、美诺、LG、戴森）
- [ ] 模板版本历史与回滚
- [ ] Web UI 适配器（FastAPI + 简单前端）

---

## 贡献指南

**最有价值的贡献**是一个 `memory/templates/*.json` 文件——每个文件代表某类文档的真实使用经验。

1. 用 doc-pilot 完成一次任务
2. 在 `~/.claude/skills/doc-pilot/memory/templates/` 找到生成的模板
3. 移除个人标识符（序列号、自定义名称等）
4. 发起 PR

本地测试方式：
```bash
python skills/doc-pilot-pdf/scripts/extract.py ./your_manual.pdf
python skills/doc-pilot-analyst/scripts/analyse.py ./extracted.md
python skills/doc-pilot/scripts/template_store.py lookup \
  --task-type fault_diagnosis --product dishwasher --brand bosch --fault-code E9
```

---

## 许可证

代码采用 **Apache 2.0** 许可证。

`doc-pilot-pdf` 依赖 [PyMuPDF](https://pymupdf.readthedocs.io/)（AGPL 3.0）。
再分发包含 `doc-pilot-pdf` 的产品须遵守 AGPL 3.0。
如需商业许可，联系 [Artifex](https://artifex.com/)。
