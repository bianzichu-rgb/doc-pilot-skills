# doc-pilot Skills Suite

> **Turn any document into a step-by-step task navigator. Gets smarter every use.**
> **把任何文档变成逐步任务导航，越用越聪明。**

A collection of three Claude Code Skills that give Claude layout-aware document understanding,
semantic structure analysis, and self-learning task navigation.

三个 Claude Code Skills 的组合，赋予 Claude 版面感知的文档理解、语义结构分析和自我学习的任务导航能力。

---

## Skills in this repo | 技能列表

| Skill | Description | 说明 | Standalone |
|-------|-------------|------|-----------|
| [`doc-pilot`](skills/doc-pilot/) | Main navigator: fetch → classify → navigate → learn | 主编排器：获取→分类→导航→学习 | ✅ Primary entry point |
| [`doc-pilot-pdf`](skills/doc-pilot-pdf/) | Layout-aware PDF → Markdown (font hierarchy, TOC, figures) | 版面感知 PDF 提取（字体层级、目录、图表） | ✅ Use alone to extract PDFs |
| [`doc-pilot-analyst`](skills/doc-pilot-analyst/) | Semantic section classifier (troubleshooting / installation / etc.) | 语义章节分类（故障/安装/操作等9类） | ✅ Use alone to analyse docs |

---

## What makes this different | 与直接问 Claude 的区别

| | Ask Claude directly 直接问 Claude | doc-pilot |
|--|---|---|
| Document source 文档来源 | Manual paste 手动粘贴 | Auto-fetch (PDF / URL / search) 自动获取 |
| Output 输出 | One-time answer 一次性回答 | Stateful step-by-step with ✅/❌ 有状态逐步导航 |
| Failure handling 失败处理 | Re-ask 重新提问 | Branch to next approach 自动切换方案 |
| Cross-session memory 跨会话记忆 | None 无 | Persists task progress 持久化任务进度 |
| **Learning 学习** | **Resets every time 每次重置** | **Accumulates templates 模板库越用越准** |
| **Agent awareness 智能体感知** | **None 无** | **Routes to best agent per capability 按能力调度最优智能体** |

---

## Installation | 安装

```bash
# Clone into your Claude skills directory | 克隆到 Claude skills 目录
git clone https://github.com/bianzichu-rgb/doc-pilot-skills ~/.claude/skills/doc-pilot-suite

# Symlink each skill | 为每个 skill 创建软链接
ln -s ~/.claude/skills/doc-pilot-suite/skills/doc-pilot       ~/.claude/skills/doc-pilot
ln -s ~/.claude/skills/doc-pilot-suite/skills/doc-pilot-pdf   ~/.claude/skills/doc-pilot-pdf
ln -s ~/.claude/skills/doc-pilot-suite/skills/doc-pilot-analyst ~/.claude/skills/doc-pilot-analyst

# Install the only external dependency (for PDF extraction) | 安装唯一外部依赖（PDF提取用）
pip install pymupdf
```

---

## Usage examples | 使用示例

```
"Help me fix my Bosch dishwasher showing E9 error"
"帮我修博世洗碗机显示E9故障"
→ doc-pilot auto-triggers, fetches manual, navigates troubleshooting steps
→ 自动触发，获取说明书，逐步导航故障排除步骤

"Extract the structure of this PDF: /path/to/manual.pdf"
"提取这个PDF的结构：/path/to/manual.pdf"
→ doc-pilot-pdf extracts with font hierarchy, TOC, figure registry
→ 按字体层级提取结构、目录和图表注册表

"What sections does this manual cover?" + paste Markdown
"这份说明书包含哪些章节？" + 粘贴Markdown
→ doc-pilot-analyst classifies sections by type with confidence scores
→ 按类型分类章节，输出置信度分数
```

---

## The Learning Flywheel | 自学习飞轮

```
First use of a document type | 首次使用某类文档
  → Claude reads doc → generates TaskPlan
  → 读取文档 → 生成任务计划
  → User completes steps (✅/❌ feedback recorded)
  → 用户完成步骤（✅/❌ 反馈记录）
  → Outcome written to memory/templates/
  → 结果写入 memory/templates/

Next time same document type appears | 下次同类文档出现
  → Template matched → steps reused (with historical success rates)
  → 匹配模板 → 复用步骤（含历史成功率）
  → Failing steps flagged proactively
  → 主动标注已知高失败率步骤
  → EWMA updates: new_rate = 0.2 × result + 0.8 × history

Agent meta-learning | 智能体元学习
  → doc-pilot records which agent performed best per capability
  → 记录每种能力哪个智能体表现最好
  → Dispatches to proven agent on future similar tasks
  → 下次同类任务优先调度已验证的智能体
```

模板存储于本地 `~/.claude/skills/doc-pilot/memory/`，默认私有。
你可以导出自己的模板 JSON 文件发起 PR，帮助他人跳过冷启动阶段。

Templates are stored locally in `~/.claude/skills/doc-pilot/memory/` — private by default.
Export yours and open a PR — others can import them to skip the cold-start phase.

---

## Supported document types | 支持的文档类型

- Home appliance manuals (Bosch, Miele, Dyson, Panasonic, ...) | 家电说明书
- IKEA / furniture assembly guides | 宜家等家具组装指南
- Kubernetes / Docker / DevOps deployment docs | 容器化部署文档
- API integration documentation (Stripe, Twilio, ...) | API 集成文档
- Medical device instructions | 医疗器械说明书
- Tax and government forms | 税务/政府表格
- Firmware update procedures | 固件升级流程
- Cooking programs (appliance-specific recipes) | 家电烹饪程序

---

## Architecture | 架构

```
doc-pilot/
├── SKILL.md                    ← Main trigger + workflow instructions | 主触发器 + 工作流
├── references/
│   └── doc_types.md            ← Document type recognition guide | 文档类型识别指南
├── scripts/
│   ├── fetch_doc.py            ← Acquisition strategy + document cache | 文档获取策略
│   ├── task_state.py           ← TaskPlan state machine (JSON persistence) | 任务状态机
│   ├── template_store.py       ← Template CRUD + EWMA + skill performance | 模板库 + 学习
│   └── agent_dispatch.py       ← Multi-agent capability router | 多智能体调度器
└── memory/                     ← Auto-generated at runtime | 运行时自动生成
    ├── tasks/                  ← Per-task JSON (full execution trace)
    ├── templates/              ← Per-document-type learned templates | 学习模板
    ├── agent_registry.json     ← Available agents + capabilities (user-editable) | 智能体注册表
    └── skill_performance.json  ← Agent effectiveness by capability + task type

doc-pilot-pdf/
├── SKILL.md
└── scripts/
    └── extract.py              ← Font hierarchy + TOC + dedup + spec tables

doc-pilot-analyst/
├── SKILL.md
└── scripts/
    └── analyse.py              ← 9-category classifier + figure registry
```

### Multi-Agent Dispatch | 多智能体调度

doc-pilot 可将不同能力路由到最合适的智能体——Claude 子技能、直接调用 Claude API 不同模型（haiku/sonnet/opus）、或 Claude 内置工具（WebSearch/WebFetch）。

doc-pilot can route capabilities to different agents — Claude sub-skills, direct Claude API
model variants (haiku/sonnet/opus), or Claude built-in tools (WebSearch/WebFetch):

```bash
# 查询：哪个智能体最适合处理家电说明书的PDF提取？
# Ask: "which agent is best for PDF extraction on appliance manuals?"
python ~/.claude/skills/doc-pilot/scripts/agent_dispatch.py best-agent \
  --capability pdf_extraction --task-type appliance_manual
# → BEST_AGENT=doc-pilot-pdf  success_rate=0.92  total_calls=14

# 在 memory/agent_registry.json 中启用直接 Claude API 智能体：
# Enable direct Claude API agents by editing memory/agent_registry.json:
# "claude-haiku": { "enabled": true, ... }  ← 快速翻译/预处理 / fast translation
# "claude-opus":  { "enabled": true, ... }  ← 安全关键步骤 / safety-critical steps
```

性能追踪使用 EWMA（α=0.25）——每次记录 `ok`/`fail` 结果都会更新智能体成功率，调度器自然向更优的智能体偏移。

The performance tracker uses EWMA (α=0.25) — each recorded `ok`/`fail` outcome nudges
the agent's success rate, so the dispatcher naturally shifts toward better-performing agents.

---

## Contributing | 贡献

`memory/templates/` 中的模板 JSON 文件是最有价值的贡献——每个模板代表某类文档的真实使用经验积累。导出你的模板发起 PR，帮助他人跳过冷启动阶段。

Template JSON files in `memory/templates/` are the most valuable contribution.
Each template represents accumulated real-world experience for a specific document type.
Export yours and open a PR — others can import them to skip the cold-start phase.

---

## License | 许可证

本仓库代码采用 **Apache 2.0** 许可证。

The code in this repository is licensed under **Apache 2.0**.

**第三方依赖声明 / Third-party dependency notice:**
`doc-pilot-pdf` 使用 [PyMuPDF (fitz)](https://pymupdf.readthedocs.io/) 进行PDF解析，
该库采用 **GNU AGPL 3.0** 许可证。若你再分发包含 `doc-pilot-pdf` 的产品，须遵守 AGPL 3.0（包括开放源代码）。
如 AGPL 与你的分发模式不兼容，可向 [Artifex](https://artifex.com/) 购买商业许可证。

`doc-pilot-pdf` uses [PyMuPDF (fitz)](https://pymupdf.readthedocs.io/) for PDF parsing,
which is licensed under **GNU AGPL 3.0**. If you redistribute a product that includes
`doc-pilot-pdf`, you must comply with AGPL 3.0 (including making source available).
PyMuPDF commercial licenses are available from [Artifex](https://artifex.com/) if
AGPL is incompatible with your distribution model.
