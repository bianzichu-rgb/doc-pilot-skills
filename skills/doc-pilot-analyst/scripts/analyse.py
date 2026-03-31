#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
doc-pilot-analyst: analyse.py
Semantic section classifier + figure/cross-reference registry.

Ported from CognoLiving 2.0 (schema_mapper.py, hams_visual_assembler.py).
Zero external dependencies — pure Python stdlib.

Usage:
  python analyse.py <md_path>          # analyse a Markdown file
  python analyse.py -                  # read Markdown from stdin
  python analyse.py <md_path> --filter troubleshooting
  python analyse.py <md_path> --json
"""

import sys
import re
import json
import argparse
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, field, asdict

# ─── Section Categories ────────────────────────────────────────────────────────

CATEGORIES = {
    "SAFETY": {
        "keywords_zh": ["安全", "警告", "注意", "危险", "重要安全", "安全信息", "安全注意事项",
                        "使用注意", "安全须知", "警示", "防止", "小心"],
        "keywords_en": ["safety", "warning", "caution", "danger", "hazard",
                        "important safety", "precautions", "risk", "do not"],
    },
    "TECHNICAL_SPEC": {
        "keywords_zh": ["规格", "参数", "技术数据", "技术规格", "产品规格", "性能参数",
                        "额定", "功率", "尺寸", "重量", "容量"],
        "keywords_en": ["specifications", "technical data", "dimensions", "capacity",
                        "ratings", "specs", "performance", "power supply",
                        "declaration of conformity"],
    },
    "INSTALLATION": {
        "keywords_zh": ["安装", "组装", "准备工作", "拆箱", "安装步骤", "安装前",
                        "连接管路", "固定", "水平调整"],
        "keywords_en": ["installation", "assembly", "getting started", "setup",
                        "mounting", "unpacking", "leveling", "plumbing", "wiring"],
    },
    "OPERATION": {
        "keywords_zh": ["操作", "使用方法", "功能介绍", "使用", "控制", "按钮",
                        "设置", "自定义", "程序", "模式", "开关", "日常使用",
                        "使用说明", "功能", "调节", "控制面板", "程序表", "洗涤程序"],
        "keywords_en": ["operation", "how to use", "using", "controls", "daily use",
                        "instructions", "cycles", "programs", "options", "buttons", "panel"],
    },
    "PARTS": {
        "keywords_zh": ["零部件", "清单", "包装内容", "配件", "部件名称", "各部分名称"],
        "keywords_en": ["parts", "components", "accessories", "packing list",
                        "what's in the box", "contents", "items included"],
    },
    "MAINTENANCE": {
        "keywords_zh": ["保养", "维护", "清洁", "清洗", "养护", "除垢", "更换滤网",
                        "定期", "滤芯", "日常维护"],
        "keywords_en": ["maintenance", "cleaning", "care", "looking after",
                        "servicing", "storage", "descale", "filter"],
    },
    "TROUBLESHOOTING": {
        "keywords_zh": ["故障", "排查", "解决", "错误代码", "问题", "异常",
                        "报错", "维修", "检修", "闪烁"],
        "keywords_en": ["troubleshooting", "error codes", "problems", "fault",
                        "fix", "repair", "service info", "diagnosis"],
    },
    "FAQ": {
        "keywords_zh": ["常见问题", "问答", "保修", "售后", "质保", "法律声明",
                        "免责", "版权", "合规"],
        "keywords_en": ["faq", "frequently asked questions", "warranty",
                        "copyright", "legal", "fcc", "regulatory"],
    },
    "RECIPE": {
        "keywords_zh": ["食谱", "烹饪", "程序", "场景", "应用", "建议", "推荐"],
        "keywords_en": ["recipe", "cooking", "baking", "use case", "tips",
                        "recommended", "applications"],
    },
}


# ─── Data Structures ───────────────────────────────────────────────────────────

@dataclass
class Section:
    title: str
    category: str
    confidence: float
    start_line: int
    end_line: int
    content_preview: str = ""


@dataclass
class FigureRef:
    label: str
    page_hint: Optional[int]
    line_num: int


@dataclass
class AnalysisResult:
    sections: List[Section] = field(default_factory=list)
    figures: List[FigureRef] = field(default_factory=list)
    cross_refs: List[Dict] = field(default_factory=list)
    total_lines: int = 0


# ─── Section Classifier ────────────────────────────────────────────────────────

def classify_heading(text: str) -> Tuple[str, float]:
    """
    3-tier classification:
    Tier 1: exact keyword match (case-insensitive)
    Tier 2: substring match
    Tier 3: partial word match
    Returns (category, confidence)
    """
    text_lower = text.lower().strip()

    # Tier 1: exact phrase match
    for cat, kw_groups in CATEGORIES.items():
        for kw in kw_groups.get("keywords_zh", []) + kw_groups.get("keywords_en", []):
            if kw.lower() == text_lower:
                return cat, 1.0

    # Tier 2: substring match in heading text
    for cat, kw_groups in CATEGORIES.items():
        all_kw = kw_groups.get("keywords_zh", []) + kw_groups.get("keywords_en", [])
        for kw in all_kw:
            if kw.lower() in text_lower:
                return cat, 0.9

    # Tier 3: keyword appears in first 60 chars of heading
    text_head = text_lower[:60]
    for cat, kw_groups in CATEGORIES.items():
        all_kw = kw_groups.get("keywords_zh", []) + kw_groups.get("keywords_en", [])
        matches = sum(1 for kw in all_kw if kw.lower() in text_head)
        if matches >= 1:
            return cat, 0.7

    return "GENERAL", 0.5


# ─── Figure & Cross-Reference Registry ────────────────────────────────────────

FIGURE_PATTERN = re.compile(
    r'\[Image on page (\d+)[^\]]*\]|(?:Figure|Fig\.|Table)\s+(\d+|[A-Z])',
    re.IGNORECASE
)
CROSSREF_PATTERN = re.compile(
    r'(?:see|refer to|as shown in|图|表)\s+(?:Figure|Fig\.|Table|图|表)\s*\.?\s*(\d+|[A-Z])',
    re.IGNORECASE
)


def extract_figures_and_refs(lines: List[str]) -> Tuple[List[FigureRef], List[Dict]]:
    figures = []
    cross_refs = []

    for i, line in enumerate(lines):
        # Figure placeholders from doc-pilot-pdf
        m = FIGURE_PATTERN.search(line)
        if m:
            page = int(m.group(1)) if m.group(1) else None
            label = m.group(0)
            figures.append(FigureRef(label=label, page_hint=page, line_num=i + 1))

        # Cross-references ("see Figure 3", "如图2所示")
        cx = CROSSREF_PATTERN.search(line)
        if cx:
            cross_refs.append({"line": i + 1, "ref": cx.group(0), "target": cx.group(1)})

    return figures, cross_refs


# ─── Main Analysis ─────────────────────────────────────────────────────────────

HEADING_PATTERN = re.compile(r'^(#{1,4})\s+(.+)$')


def analyse_markdown(text: str) -> AnalysisResult:
    lines = text.split('\n')
    result = AnalysisResult(total_lines=len(lines))

    # Find all headings and their line positions
    headings: List[Tuple[int, int, str]] = []  # (line_num, level, title)
    for i, line in enumerate(lines):
        m = HEADING_PATTERN.match(line.strip())
        if m:
            level = len(m.group(1))
            title = m.group(2).strip()
            headings.append((i, level, title))

    # Segment document into sections based on headings
    for idx, (line_num, level, title) in enumerate(headings):
        # Section ends at next heading of same or higher level
        end_line = len(lines) - 1
        for j in range(idx + 1, len(headings)):
            if headings[j][1] <= level:
                end_line = headings[j][0] - 1
                break

        cat, conf = classify_heading(title)

        # Extract a short preview from section content
        section_lines = lines[line_num + 1: min(line_num + 6, end_line + 1)]
        preview = " ".join(l.strip() for l in section_lines if l.strip())[:120]

        result.sections.append(Section(
            title=title,
            category=cat,
            confidence=conf,
            start_line=line_num + 1,
            end_line=end_line + 1,
            content_preview=preview,
        ))

    # If no headings found, treat whole doc as one section
    if not headings and text.strip():
        cat, conf = classify_heading(text[:100])
        result.sections.append(Section(
            title="(no headings detected)",
            category=cat,
            confidence=conf,
            start_line=1,
            end_line=len(lines),
            content_preview=text[:120],
        ))

    # Extract figures and cross-references
    result.figures, result.cross_refs = extract_figures_and_refs(lines)

    return result


# ─── Output Formatters ─────────────────────────────────────────────────────────

CATEGORY_EMOJI = {
    "SAFETY": "⚠️",
    "TECHNICAL_SPEC": "📊",
    "INSTALLATION": "🔧",
    "OPERATION": "▶️",
    "PARTS": "🔩",
    "MAINTENANCE": "🧹",
    "TROUBLESHOOTING": "🔍",
    "FAQ": "📋",
    "RECIPE": "🍳",
    "GENERAL": "📄",
}


def format_human(result: AnalysisResult, filter_cat: Optional[str] = None) -> str:
    lines = ["Document Structure Analysis", "=" * 40]

    shown = result.sections
    if filter_cat:
        fc = filter_cat.upper()
        shown = [s for s in result.sections if fc in s.category.upper()]

    if not shown:
        lines.append(f"No sections found matching: {filter_cat}")
    else:
        for s in shown:
            emoji = CATEGORY_EMOJI.get(s.category, "📄")
            conf_str = f"{s.confidence:.0%}"
            lines.append(
                f"{emoji} [{s.category:<16}] {s.title}  "
                f"(lines {s.start_line}-{s.end_line}, confidence {conf_str})"
            )
            if s.content_preview:
                lines.append(f"   ↳ {s.content_preview[:100]}...")

    lines.append("")
    lines.append(f"Figures: {len(result.figures)} registered  |  "
                 f"Cross-references: {len(result.cross_refs)}")

    if result.cross_refs:
        lines.append("\nCross-references:")
        for cr in result.cross_refs[:10]:
            lines.append(f"  Line {cr['line']}: {cr['ref']}")

    return "\n".join(lines)


def format_json(result: AnalysisResult) -> str:
    return json.dumps({
        "sections": [asdict(s) for s in result.sections],
        "figures": [asdict(f) for f in result.figures],
        "cross_refs": result.cross_refs,
        "total_lines": result.total_lines,
    }, ensure_ascii=False, indent=2)


# ─── CLI ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Semantic document structure analyser")
    parser.add_argument("path", help="Path to Markdown file, or - for stdin")
    parser.add_argument("--filter", "-f", help="Show only sections matching this category")
    parser.add_argument("--json", action="store_true", help="Output JSON")
    args = parser.parse_args()

    if args.path == "-":
        text = sys.stdin.read()
    else:
        p = Path(args.path)
        if not p.exists():
            print(f"ERROR: File not found: {p}", file=sys.stderr)
            sys.exit(1)
        text = p.read_text(encoding="utf-8")

    result = analyse_markdown(text)

    if args.json:
        print(format_json(result))
    else:
        print(format_human(result, filter_cat=args.filter))


if __name__ == "__main__":
    main()
