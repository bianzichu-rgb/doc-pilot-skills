[English](#english) | [中文](#中文)

---

<a name="english"></a>

# doc-pilot

> **Navigate any document, step by step. Gets smarter every use.**

[![License](https://img.shields.io/badge/license-Apache%202.0-blue.svg)](LICENSE)
[![PyMuPDF](https://img.shields.io/badge/PDF-PyMuPDF%20AGPL3-orange.svg)](https://pymupdf.readthedocs.io/)
[![Claude Code](https://img.shields.io/badge/Claude%20Code-Skills-blueviolet.svg)](https://claude.ai/code)

---

You paste a manual. Claude gives you one answer. You close the tab and start over next time.

**doc-pilot turns any document into a guided, stateful walkthrough** — with branching when steps fail, memory that persists across sessions, and a template library that learns from every completion so the same job gets faster each time.

---

## Demo

```
You:  My Bosch dishwasher is showing E9. Help me fix it.

doc-pilot:
  ✦ Fetching Bosch SGS4HMI61E manual...
  ✦ Classified section: TROUBLESHOOTING (confidence 0.94)
  ✦ Matched template: bosch_e9_water_inlet [success rate 87%, 6 prior completions]

  📋 Task: Fix E9 — Water Inlet Fault  |  Steps: 4  |  Est: 10–20 min

  ▶ Step 1 of 4: Check water supply valve
    1. Locate the valve behind the machine (usually bottom-left)
    2. Confirm it is turned fully counter-clockwise (open)
    3. Expected: valve is open → water flows when tap is run nearby

  ✅ Done, move to Step 2   ❌ Didn't work, try another way

You:  ❌

doc-pilot:
  ▶ Step 2 of 4: Clean the inlet filter
    1. Turn off water supply, unscrew the inlet hose at the back
    2. Remove the mesh filter with pliers — rinse under tap
    3. Expected: filter was blocked with debris
```

---

## Features

- 📄 **Auto-fetch** — give it a PDF path, a URL, or just a product name; doc-pilot finds the document
- 🏗️ **Layout-aware PDF extraction** — font hierarchy, dual-column, TOC, spec tables — all preserved
- 🗂️ **Section classifier** — 9 categories (Safety / Installation / Troubleshooting / Specs / ...) so long manuals don't overwhelm context
- 🧠 **Template memory** — completed tasks are stored; same document type next time starts with a proven step plan
- 📈 **EWMA learning** — success rates update automatically; high-failure steps get flagged before you hit them
- 🤖 **Multi-agent dispatch** — routes PDF extraction, translation, complex reasoning to the best available agent (sub-skill or Claude API model)
- 🔁 **Self-healing loop** — session-end hook consolidates learnings into `navigation_patterns.md` automatically

---

## Skills in this repo

| Skill | What it does | Use alone? |
|-------|-------------|-----------|
| [`doc-pilot`](skills/doc-pilot/) | Orchestrator: fetch → classify → navigate → learn | ✅ Main entry point |
| [`doc-pilot-pdf`](skills/doc-pilot-pdf/) | PDF → Markdown with font hierarchy, TOC, figures | ✅ Standalone PDF extractor |
| [`doc-pilot-analyst`](skills/doc-pilot-analyst/) | Classifies sections into 9 semantic categories | ✅ Standalone doc analyser |

---

## Quick Start

```bash
# 1. Clone
git clone https://github.com/bianzichu-rgb/doc-pilot-skills ~/.claude/skills/doc-pilot-suite

# 2. Link skills
ln -s ~/.claude/skills/doc-pilot-suite/skills/doc-pilot         ~/.claude/skills/doc-pilot
ln -s ~/.claude/skills/doc-pilot-suite/skills/doc-pilot-pdf     ~/.claude/skills/doc-pilot-pdf
ln -s ~/.claude/skills/doc-pilot-suite/skills/doc-pilot-analyst ~/.claude/skills/doc-pilot-analyst

# 3. Install the only dependency (PDF extraction)
pip install pymupdf
```

Then just talk to Claude Code:
```
"Help me install this router"        → fetches manual, navigates installation
"My washing machine shows E9"        → fetches manual, troubleshooting plan
"Walk me through this PDF"           → extracts + classifies + navigates
"帮我一步步设置这个路由器"              → 同上，支持中文
```

---

## How It Learns

```
First run on a document type
  → generates TaskPlan from document content
  → records each step outcome (✅ / ❌)
  → saves template to memory/templates/

Next run on the same document type
  → matches template → reuses proven steps
  → warns you about historically high-failure steps
  → EWMA update: rate = 0.2 × new_result + 0.8 × history

Multi-agent learning
  → tracks which agent (doc-pilot-pdf / claude-haiku / websearch)
    performed best for each capability + task type
  → routes to the proven winner next time
```

Templates live in `~/.claude/skills/doc-pilot/memory/` — private by default.
Share your `memory/templates/` files in a PR to help others skip cold-start.

---

## Architecture

```
doc-pilot/
├── SKILL.md               ← trigger conditions + full workflow
├── scripts/
│   ├── fetch_doc.py       ← PDF / URL / search acquisition
│   ├── task_state.py      ← step state machine (JSON)
│   ├── template_store.py  ← CRUD + EWMA learning
│   └── agent_dispatch.py  ← capability router (skill / API / tool)
└── memory/
    ├── templates/         ← learned step plans per document type
    ├── agent_registry.json← available agents + capabilities
    └── skill_performance.json

doc-pilot-pdf/scripts/extract.py    ← font hierarchy, TOC, dual-col, spec tables
doc-pilot-analyst/scripts/analyse.py← 9-category classifier + figure registry
```

---

## Contributing

The most valuable contribution is a `memory/templates/` JSON file.
Each one represents real accumulated experience on a specific document type.
Export yours → open a PR → others skip the cold-start.

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

> **逐步导航任何文档，越用越聪明。**

[![许可证](https://img.shields.io/badge/许可证-Apache%202.0-blue.svg)](LICENSE)
[![Claude Code](https://img.shields.io/badge/Claude%20Code-Skills-blueviolet.svg)](https://claude.ai/code)

---

你把说明书粘贴进去，Claude 给你一个回答，然后下次遇到同样的问题，你又得从头开始。

**doc-pilot 把任何文档变成有状态的逐步向导** —— 步骤失败时自动切换方案，进度跨会话保存，模板库从每次完成中学习，同类任务每次都更快。

---

## 演示

```
你：  我的博世洗碗机显示E9，帮我修。

doc-pilot:
  ✦ 正在获取博世 SGS4HMI61E 说明书...
  ✦ 章节分类：故障排除（置信度 0.94）
  ✦ 匹配模板：bosch_e9_进水故障 [成功率 87%，已完成 6 次]

  📋 任务：修复 E9 — 进水故障  |  步骤：4 步  |  预计：10–20 分钟

  ▶ 第 1 步 / 共 4 步：检查进水阀
    1. 找到机器后面的进水阀（通常在左下角）
    2. 确认阀门完全逆时针拧开（开启状态）
    3. 预期结果：阀门开启 → 打开附近水龙头时有水流

  ✅ 完成，下一步   ❌ 没用，换个方法

你：  ❌

doc-pilot:
  ▶ 第 2 步 / 共 4 步：清洁进水过滤网
    1. 关闭进水阀，从机器背面拧下进水管
    2. 用钳子取出网状过滤器，在水龙头下冲洗
    3. 预期结果：过滤器被杂质堵塞
```

---

## 功能

- 📄 **自动获取文档** — 给它 PDF 路径、URL 或产品名称，doc-pilot 自动找到说明书
- 🏗️ **版面感知 PDF 提取** — 字体层级、双栏排版、目录、规格表，完整保留结构
- 🗂️ **章节语义分类** — 9 个类别（安全 / 安装 / 故障排除 / 规格参数 / ...），长文档不再淹没上下文
- 🧠 **模板记忆** — 已完成任务存储为模板，下次同类文档直接使用已验证步骤
- 📈 **EWMA 自动学习** — 成功率持续更新，高失败率步骤在你踩坑前就会提前警告
- 🤖 **多智能体调度** — 将 PDF 提取、翻译、复杂推理路由到最优智能体（子技能或 Claude API 模型）
- 🔁 **自愈学习闭环** — 会话结束时自动汇总学习成果到 `navigation_patterns.md`

---

## 技能列表

| 技能 | 功能 | 可单独使用？ |
|------|------|------------|
| [`doc-pilot`](skills/doc-pilot/) | 编排器：获取 → 分类 → 导航 → 学习 | ✅ 主入口 |
| [`doc-pilot-pdf`](skills/doc-pilot-pdf/) | PDF → Markdown（字体层级 / 目录 / 图表） | ✅ 单独 PDF 提取 |
| [`doc-pilot-analyst`](skills/doc-pilot-analyst/) | 将章节分类为 9 个语义类别 | ✅ 单独文档分析 |

---

## 快速开始

```bash
# 1. 克隆
git clone https://github.com/bianzichu-rgb/doc-pilot-skills ~/.claude/skills/doc-pilot-suite

# 2. 软链接各技能
ln -s ~/.claude/skills/doc-pilot-suite/skills/doc-pilot         ~/.claude/skills/doc-pilot
ln -s ~/.claude/skills/doc-pilot-suite/skills/doc-pilot-pdf     ~/.claude/skills/doc-pilot-pdf
ln -s ~/.claude/skills/doc-pilot-suite/skills/doc-pilot-analyst ~/.claude/skills/doc-pilot-analyst

# 3. 安装唯一外部依赖（PDF 提取）
pip install pymupdf
```

然后直接跟 Claude Code 说话：
```
"帮我安装这个路由器"          → 获取说明书，导航安装步骤
"洗衣机显示 E9 怎么办"        → 获取说明书，生成故障排除计划
"帮我逐步读这个 PDF"           → 提取 + 分类 + 导航
"Help me set up this router"  → same, supports English
```

---

## 学习机制

```
首次使用某类文档
  → 从文档内容生成任务计划
  → 记录每步结果（✅ / ❌）
  → 保存模板到 memory/templates/

下次同类文档出现
  → 匹配模板 → 复用已验证步骤
  → 提前警告历史高失败率步骤
  → EWMA 更新：rate = 0.2 × 新结果 + 0.8 × 历史

多智能体学习
  → 追踪哪个智能体（doc-pilot-pdf / claude-haiku / websearch）
    在每种能力 + 任务类型上表现最好
  → 下次自动路由到已验证的最优智能体
```

模板存储于本地 `~/.claude/skills/doc-pilot/memory/`，默认私有。
导出你的 `memory/templates/` 文件并发起 PR，帮助他人跳过冷启动阶段。

---

## 贡献

最有价值的贡献是一个 `memory/templates/` JSON 文件。
每个文件代表某类文档的真实使用经验积累。
导出 → 发起 PR → 他人跳过冷启动。

---

## 许可证

代码采用 **Apache 2.0** 许可证。

`doc-pilot-pdf` 依赖 [PyMuPDF](https://pymupdf.readthedocs.io/)（AGPL 3.0）。
再分发包含 `doc-pilot-pdf` 的产品须遵守 AGPL 3.0。
如需商业许可，联系 [Artifex](https://artifex.com/)。
