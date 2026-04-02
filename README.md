[English](#english) | [中文](#中文)

---

<a name="english"></a>

# doc-pilot

> Navigate any document, step by step. Gets smarter every use.

**doc-pilot turns manuals, PDFs, and long documents into stateful task walkthroughs.**
It fetches the right document, finds the relevant section, guides you step by step,
and learns from every completion — so similar tasks start faster next time.

[![License](https://img.shields.io/badge/license-Apache%202.0-blue.svg)](LICENSE)
[![PyMuPDF](https://img.shields.io/badge/PDF-PyMuPDF%20AGPL3-orange.svg)](https://pymupdf.readthedocs.io/)
[![Claude Code](https://img.shields.io/badge/runs%20on-Claude%20Code-blueviolet.svg)](https://claude.ai/code)

> This repo contains the **doc-pilot skill suite for Claude Code** — three standalone skills
> that can be used together or independently.

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

Not just document extraction. Not just question answering. Not just workflow memory.

---

## Demo

```
You:  My Bosch dishwasher is showing E9. Help me fix it.

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

You:  ❌

doc-pilot:
  ▶ Step 2 of 4: Clean the inlet filter
    ⚠  Known failure point — affects 27% of attempts at this step
    1. Turn off water supply, unscrew the inlet hose
    2. Remove mesh filter with pliers — rinse under tap
    3. Expected: filter was blocked with debris
```

---

## Try it in 3 minutes

**Prerequisites:** Claude Code · Python 3.8+ · `pip install pymupdf`

```bash
git clone https://github.com/bianzichu-rgb/doc-pilot-skills ~/.claude/skills/doc-pilot-suite

ln -s ~/.claude/skills/doc-pilot-suite/skills/doc-pilot         ~/.claude/skills/doc-pilot
ln -s ~/.claude/skills/doc-pilot-suite/skills/doc-pilot-pdf     ~/.claude/skills/doc-pilot-pdf
ln -s ~/.claude/skills/doc-pilot-suite/skills/doc-pilot-analyst ~/.claude/skills/doc-pilot-analyst

pip install pymupdf
```

Then open Claude Code and try these three things — in order — to verify it works:

```
# 1 — Does it find documents?
"Help me troubleshoot Bosch SGS4HMI61E E9 error"

# 2 — Does it build a step-by-step plan?
"Walk me through this PDF: ./manuals/router_setup.pdf"

# 3 — Does it remember? (run again after completing #1)
"My Bosch dishwasher shows E9 again"
```

**What you should see after step 1:**
```
✓ Fetched manual (SGS4HMI61E service manual, 48 pages)
✓ Classified section: TROUBLESHOOTING
✓ Built 4-step plan
✓ Saved reusable template → bosch_e9_water_inlet.json
```

**What you should see after step 3 (second run):**
```
✓ Template matched: bosch_e9_water_inlet
  success rate 87%  |  prior completions: 1  ← your run was recorded
  Known issue at Step 2: inlet filter blockage (27% fail rate)
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
    {
      "step_id": "s1",
      "title": "Check water supply valve",
      "historical_fail_rate": 0.12,
      "run_count": 6
    },
    {
      "step_id": "s2",
      "title": "Clean the inlet filter",
      "historical_fail_rate": 0.27,
      "run_count": 5
    },
    {
      "step_id": "s3",
      "title": "Test inlet valve solenoid",
      "historical_fail_rate": 0.40,
      "run_count": 3
    },
    {
      "step_id": "s4",
      "title": "Call service — replace inlet valve",
      "historical_fail_rate": 0.0,
      "run_count": 1
    }
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

Pick up this task in a later session: `"Continue my dishwasher repair"`

</details>

---

## Features

- 📄 **Auto-fetch** — PDF path, URL, or product name → doc-pilot finds the document
- 🏗️ **Layout-aware extraction** — font hierarchy, dual-column, TOC, spec tables preserved
- 🗂️ **Section classifier** — 9 semantic categories so long manuals don't overwhelm context
- 🧠 **Template memory** — proven step plans reused; high-failure steps flagged proactively
- 📈 **EWMA learning** — success rates update per completion (α=0.2); no manual curation
- 🤖 **Multi-agent dispatch** — routes to best available agent per capability + task type
- 🔁 **Session consolidation** — `onSessionEnd` hook auto-distills patterns after every session

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
  → recorded in memory/skill_performance.json
```

Share your `memory/templates/*.json` files — others can import them to skip the cold-start phase.

---

## Skills in this repo

| Skill | What it does | Use standalone? |
|-------|-------------|-----------------|
| [`doc-pilot`](skills/doc-pilot/) | Orchestrator: fetch → classify → navigate → learn | ✅ Main entry point |
| [`doc-pilot-pdf`](skills/doc-pilot-pdf/) | PDF → Markdown with font hierarchy, TOC, figures | ✅ PDF extractor |
| [`doc-pilot-analyst`](skills/doc-pilot-analyst/) | Classifies sections into 9 semantic categories | ✅ Doc analyser |

---

## Architecture

```
doc-pilot/
├── SKILL.md               ← trigger conditions + full workflow
├── scripts/
│   ├── fetch_doc.py       ← acquisition: PDF / URL / search
│   ├── task_state.py      ← step state machine (JSON persistence)
│   ├── template_store.py  ← CRUD + EWMA learning
│   └── agent_dispatch.py  ← capability router (skill / API / tool)
└── memory/
    ├── templates/         ← learned step plans per document type
    ├── agent_registry.json← available agents + capabilities (local, gitignored)
    └── skill_performance.json (local, gitignored)

doc-pilot-pdf/scripts/extract.py     ← font hierarchy, TOC, dual-col, spec tables
doc-pilot-analyst/scripts/analyse.py ← 9-category classifier + figure registry
```

---

## Limitations

- **Structured documents work best** — repair manuals, setup guides, troubleshooting trees.
  Narrative or legal documents have lower step extraction accuracy.
- **Scanned PDFs** — image-only PDFs with no text layer are not supported. OCR fallback is on the roadmap.
- **Template quality depends on volume** — a template is only created after ≥3 similar completions.
  First runs always use LLM generation.
- **Agent routing** — `claude_api` agents (haiku/sonnet/opus) are disabled by default.
  Direct API routing requires `ANTHROPIC_API_KEY` and manual opt-in in `memory/agent_registry.json`.
- **Web fetch quality** — manual retrieval via search depends on source availability and structure.

---

## Roadmap

- [ ] OCR fallback for scanned PDFs
- [ ] `template export --sanitize` — strip device identifiers before sharing
- [ ] Sample template library for common appliance brands (Bosch, Miele, LG, Dyson)
- [ ] Template version history + rollback
- [ ] Benchmark agent routing quality across task types

---

## Contributing

The most valuable contribution is a `memory/templates/*.json` file.
Each one represents real accumulated experience on a document type.

1. Complete a task with doc-pilot
2. Find the generated template in `~/.claude/skills/doc-pilot/memory/templates/`
3. Remove any personal identifiers (serial numbers, custom names)
4. Open a PR — others skip the cold-start phase

To test a skill locally:
```bash
# Test PDF extraction
python ~/.claude/skills/doc-pilot-pdf/scripts/extract.py ./your_manual.pdf

# Test section classification
python ~/.claude/skills/doc-pilot-analyst/scripts/analyse.py ./extracted.md

# Test template lookup
python ~/.claude/skills/doc-pilot/scripts/template_store.py lookup \
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

**doc-pilot 把说明书、PDF 和长文档变成可持续跟踪进度的任务导航。**
它先找到正确的文档，再定位相关章节，然后一步步带你完成任务，
并把每次完成经验沉淀下来——让下次同类任务更快开始。

[![许可证](https://img.shields.io/badge/许可证-Apache%202.0-blue.svg)](LICENSE)
[![Claude Code](https://img.shields.io/badge/运行于-Claude%20Code-blueviolet.svg)](https://claude.ai/code)

> 这个仓库提供的是面向 **Claude Code** 的 doc-pilot 技能套件，包含三个可独立使用的技能。

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

不只是文档提取，不只是问答，不只是流程记录。

---

## 演示

```
你：  我的博世洗碗机显示 E9，帮我修。

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

你：  ❌

doc-pilot:
  ▶ 第 2 步 / 共 4 步：清洁进水过滤网
    ⚠  已知高失败率步骤 — 历史上 27% 的尝试在此卡住
    1. 关闭进水阀，从机器背面拧下进水管
    2. 用钳子取出网状过滤器，在水龙头下冲洗
    3. 预期结果：过滤器被杂质堵塞
```

---

## 3 分钟快速验证

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
✓ 已获取说明书（SGS4HMI61E 服务手册，48 页）
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
    {
      "step_id": "s1",
      "title": "检查进水阀",
      "historical_fail_rate": 0.12,
      "run_count": 6
    },
    {
      "step_id": "s2",
      "title": "清洁进水过滤网",
      "historical_fail_rate": 0.27,
      "run_count": 5
    },
    {
      "step_id": "s3",
      "title": "测试进水电磁阀",
      "historical_fail_rate": 0.40,
      "run_count": 3
    },
    {
      "step_id": "s4",
      "title": "联系维修——更换进水阀",
      "historical_fail_rate": 0.0,
      "run_count": 1
    }
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

## 功能

- 📄 **自动获取文档** — 给它 PDF 路径、URL 或产品名称，它自动找到说明书
- 🏗️ **版面感知提取** — 字体层级、双栏排版、目录、规格表，结构完整保留
- 🗂️ **章节语义分类** — 9 个类别（安全/安装/故障排除/规格…），先定位再导航，不淹没上下文
- 🧠 **模板记忆** — 沉淀已验证步骤；历史高失败率步骤在你踩坑前主动预警
- 📈 **EWMA 自动学习** — 每次完成自动更新成功率（α=0.2），无需人工整理
- 🤖 **多智能体调度** — 按能力 + 任务类型路由到最优智能体（子技能或 Claude API 模型）
- 🔁 **会话自动汇总** — `onSessionEnd` 钩子在每次会话结束后自动提炼导航规律

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
  → 记录于 memory/skill_performance.json
```

导出你的 `memory/templates/*.json` 文件并发起 PR——帮助他人跳过冷启动阶段。

---

## 技能列表

| 技能 | 功能 | 可单独使用？ |
|------|------|------------|
| [`doc-pilot`](skills/doc-pilot/) | 编排器：获取 → 分类 → 导航 → 学习 | ✅ 主入口 |
| [`doc-pilot-pdf`](skills/doc-pilot-pdf/) | PDF → Markdown（字体层级/目录/图表） | ✅ 单独 PDF 提取 |
| [`doc-pilot-analyst`](skills/doc-pilot-analyst/) | 章节语义分类，9 个类别 | ✅ 单独文档分析 |

---

## 架构

```
doc-pilot/
├── SKILL.md               ← 触发条件 + 完整工作流
├── scripts/
│   ├── fetch_doc.py       ← 文档获取：PDF / URL / 搜索
│   ├── task_state.py      ← 步骤状态机（JSON 持久化）
│   ├── template_store.py  ← 模板增删改查 + EWMA 学习
│   └── agent_dispatch.py  ← 能力路由（技能/API/工具）
└── memory/
    ├── templates/         ← 每类文档的已学习步骤计划
    ├── agent_registry.json← 可用智能体 + 能力（本地，已 gitignore）
    └── skill_performance.json（本地，已 gitignore）

doc-pilot-pdf/scripts/extract.py     ← 字体层级/目录/双栏/规格表
doc-pilot-analyst/scripts/analyse.py ← 9 类语义分类 + 图表注册表
```

---

## 已知限制

- **结构化文档效果最好** — 维修手册、安装指南、故障排除树。叙述性或法律文档提取准确率较低。
- **扫描版 PDF 暂不支持** — 纯图片 PDF（无文字层）无法处理，OCR 回退在路线图中。
- **模板需要积累** — 需要 ≥3 次同类完成后才会创建模板，首次运行总是由 LLM 生成计划。
- **智能体路由** — `claude_api` 智能体（haiku/sonnet/opus）默认关闭，需配置 `ANTHROPIC_API_KEY` 并在 `memory/agent_registry.json` 中手动启用。
- **网络抓取质量** — 依赖搜索结果和来源结构，可能因文档来源不同而有差异。

---

## 路线图

- [ ] 扫描版 PDF 的 OCR 回退支持
- [ ] `template export --sanitize` — 导出前自动移除设备标识符
- [ ] 常见家电品牌示例模板库（博世、美诺、LG、戴森）
- [ ] 模板版本历史与回滚
- [ ] 跨任务类型的智能体路由质量基准测试

---

## 贡献指南

最有价值的贡献是一个 `memory/templates/*.json` 文件，
每个文件代表某类文档的真实使用经验积累。

1. 用 doc-pilot 完成一次任务
2. 在 `~/.claude/skills/doc-pilot/memory/templates/` 找到生成的模板
3. 移除个人标识符（序列号、自定义名称等）
4. 发起 PR — 帮助他人跳过冷启动阶段

本地测试方式：
```bash
# 测试 PDF 提取
python ~/.claude/skills/doc-pilot-pdf/scripts/extract.py ./your_manual.pdf

# 测试章节分类
python ~/.claude/skills/doc-pilot-analyst/scripts/analyse.py ./extracted.md

# 测试模板查找
python ~/.claude/skills/doc-pilot/scripts/template_store.py lookup \
  --task-type fault_diagnosis --product dishwasher --brand bosch --fault-code E9
```

---

## 许可证

代码采用 **Apache 2.0** 许可证。

`doc-pilot-pdf` 依赖 [PyMuPDF](https://pymupdf.readthedocs.io/)（AGPL 3.0）。
再分发包含 `doc-pilot-pdf` 的产品须遵守 AGPL 3.0。
如需商业许可，联系 [Artifex](https://artifex.com/)。
