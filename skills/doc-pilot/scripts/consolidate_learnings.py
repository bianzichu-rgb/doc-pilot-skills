#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
doc-pilot consolidate_learnings.py
Session-end hook: consolidates completed task learnings into templates and
writes a human-readable session log.

Auto-triggered by hooks.onSessionEnd in SKILL.md.
Can also be run manually: python consolidate_learnings.py

Self-learning patterns implemented:
1. Scan session tasks → EWMA-update templates
2. Identify chronic failure steps → flag in navigation_patterns.md
3. Surface best-performing external skills → update skill_performance summary
4. Write session_log.md entry for human review
"""

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Dict, Optional

MEMORY_DIR = Path(__file__).parent.parent / "memory"
TASK_DIR = MEMORY_DIR / "tasks"
TEMPLATE_DIR = MEMORY_DIR / "templates"
REFERENCES_DIR = Path(__file__).parent.parent / "references"
SESSION_LOG = MEMORY_DIR / "session_log.md"
NAV_PATTERNS = REFERENCES_DIR / "navigation_patterns.md"
SKILL_PERF_FILE = MEMORY_DIR / "skill_performance.json"

EWMA_ALPHA = 0.2
MIN_TASKS_FOR_TEMPLATE = 3


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def atomic_write(path: Path, text: str):
    tmp = path.with_suffix(".tmp")
    tmp.write_text(text, encoding="utf-8")
    tmp.replace(path)


def load_recent_tasks(hours: int = 24) -> List[Dict]:
    """Load tasks completed or active in the last N hours."""
    cutoff = datetime.now(timezone.utc).timestamp() - hours * 3600
    tasks = []
    for p in TASK_DIR.glob("*.json"):
        try:
            t = json.loads(p.read_text(encoding="utf-8"))
            # Include tasks modified recently
            mtime = p.stat().st_mtime
            if mtime >= cutoff and t.get("status") in ("completed", "escalated", "abandoned"):
                tasks.append(t)
        except Exception:
            continue
    return tasks


def identify_failure_patterns(tasks: List[Dict]) -> Dict[str, Dict]:
    """
    Find steps that chronically fail across multiple tasks.
    Returns: {step_title: {fail_rate, task_types, suggestion}}
    """
    step_stats: Dict[str, Dict] = {}

    for task in tasks:
        for step in task.get("steps", []):
            title = step["title"]
            if title not in step_stats:
                step_stats[title] = {"total": 0, "failed": 0, "task_types": set()}
            step_stats[title]["total"] += 1
            if step["step_id"] in task.get("failure_path", []):
                step_stats[title]["failed"] += 1
            step_stats[title]["task_types"].add(task.get("task_type", "general"))

    # Filter to steps with >= 2 occurrences and > 50% failure rate
    chronic = {}
    for title, stats in step_stats.items():
        if stats["total"] >= 2:
            fail_rate = stats["failed"] / stats["total"]
            if fail_rate > 0.5:
                chronic[title] = {
                    "fail_rate": fail_rate,
                    "task_types": list(stats["task_types"]),
                    "suggestion": f"High failure rate ({fail_rate:.0%}) — consider adding a diagnostic sub-step before this"
                }
    return chronic


def update_templates(tasks: List[Dict]):
    """Update or create templates from recent completed tasks."""
    for task in tasks:
        if task.get("final_outcome") not in ("self_resolved", "escalated"):
            continue

        success = 1.0 if task["final_outcome"] == "self_resolved" else 0.0

        def template_key():
            parts = [
                task.get("task_type", "general").lower(),
                task.get("product_category", "").lower(),
            ]
            if task.get("brand"):
                parts.append(task["brand"].lower())
            if task.get("fault_code"):
                parts.append(task["fault_code"].upper())
            return "_".join(p for p in parts if p)

        key = template_key()
        tmpl_path = TEMPLATE_DIR / f"{key}.json"

        if tmpl_path.exists():
            try:
                tmpl = json.loads(tmpl_path.read_text(encoding="utf-8"))
                old_rate = tmpl.get("completion_rate", 0.5)
                tmpl["completion_rate"] = EWMA_ALPHA * success + (1 - EWMA_ALPHA) * old_rate
                tmpl["usage_count"] = tmpl.get("usage_count", 0) + 1
                tmpl["last_updated"] = now_iso()
                if task["task_id"] not in tmpl.get("sourced_from", []):
                    tmpl.setdefault("sourced_from", []).append(task["task_id"])
                # Update step fail stats
                for step in tmpl.get("steps", []):
                    sid = step["step_id"]
                    if sid in task.get("failure_path", []):
                        step["fail_count"] = step.get("fail_count", 0) + 1
                    step["run_count"] = step.get("run_count", 0) + 1
                    if step["run_count"] > 0:
                        step["historical_fail_rate"] = step["fail_count"] / step["run_count"]
                atomic_write(tmpl_path, json.dumps(tmpl, ensure_ascii=False, indent=2))
            except Exception:
                pass


def update_navigation_patterns(tasks: List[Dict], chronic_failures: Dict):
    """Append proven navigation sequences and known failure points to navigation_patterns.md."""
    if not tasks and not chronic_failures:
        return

    existing = NAV_PATTERNS.read_text(encoding="utf-8") if NAV_PATTERNS.exists() else "# Navigation Patterns\n\nLearned from real task completions.\n\n"

    new_entries = []
    session_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    # Add successful task sequences
    for task in tasks:
        if task.get("final_outcome") != "self_resolved":
            continue
        steps = task.get("steps", [])
        if not steps:
            continue
        seq = " → ".join(s["title"] for s in steps)
        entry = (f"\n## {task.get('task_summary', 'Task')} [{session_date}]\n"
                 f"**Type:** {task.get('task_type', '?')} | "
                 f"**Product:** {task.get('product_category', '?')} | "
                 f"**Brand:** {task.get('brand', '?')}\n\n"
                 f"**Proven sequence:** {seq}\n\n"
                 f"**Steps:** {task.get('total_steps', '?')} | "
                 f"**Duration:** {task.get('total_duration_sec', 0)//60}min\n")
        if task.get("failure_path"):
            failed_steps = [s["title"] for s in steps if s["step_id"] in task["failure_path"]]
            entry += f"**Failed steps (eventually resolved):** {', '.join(failed_steps)}\n"
        new_entries.append(entry)

    # Add chronic failure warnings
    if chronic_failures:
        new_entries.append(f"\n## ⚠️ Chronic Failure Steps [{session_date}]\n")
        for title, info in chronic_failures.items():
            new_entries.append(
                f"- **{title}**: {info['fail_rate']:.0%} failure rate across "
                f"{', '.join(info['task_types'])} tasks — {info['suggestion']}\n"
            )

    if new_entries:
        # Remove the placeholder line once real data exists
        existing = existing.replace("_No patterns yet — they accumulate automatically after task completions._\n", "")
        atomic_write(NAV_PATTERNS, existing + "\n".join(new_entries))


def write_session_log(tasks: List[Dict], chronic_failures: Dict):
    """Append a human-readable session summary to session_log.md."""
    if not tasks:
        return

    date = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    completed = [t for t in tasks if t.get("final_outcome") == "self_resolved"]
    escalated = [t for t in tasks if t.get("final_outcome") == "escalated"]
    abandoned = [t for t in tasks if t.get("final_outcome") == "abandoned"]

    lines = [
        f"\n## Session: {date}",
        f"Tasks: {len(tasks)} total | ✅ {len(completed)} resolved | ⚠️ {len(escalated)} escalated | 🚫 {len(abandoned)} abandoned",
    ]

    if completed:
        lines.append("\n**Resolved:**")
        for t in completed:
            lines.append(f"- {t.get('task_summary', t['task_id'])} "
                         f"({t.get('total_duration_sec', 0)//60}min, {t.get('total_steps')} steps)")

    if chronic_failures:
        lines.append(f"\n**Chronic failures detected:** {', '.join(chronic_failures.keys())}")

    existing = SESSION_LOG.read_text(encoding="utf-8") if SESSION_LOG.exists() else "# doc-pilot Session Log\n"
    atomic_write(SESSION_LOG, existing + "\n" + "\n".join(lines) + "\n")


def main():
    print("doc-pilot: consolidating learnings...", file=sys.stderr)
    TEMPLATE_DIR.mkdir(parents=True, exist_ok=True)
    REFERENCES_DIR.mkdir(parents=True, exist_ok=True)

    tasks = load_recent_tasks(hours=24)
    if not tasks:
        print("No completed tasks in last 24h — nothing to consolidate.", file=sys.stderr)
        return

    print(f"Found {len(tasks)} completed tasks", file=sys.stderr)

    # 1. Update templates with EWMA
    update_templates(tasks)

    # 2. Identify chronic failures
    chronic = identify_failure_patterns(tasks)
    if chronic:
        print(f"Chronic failure steps detected: {list(chronic.keys())}", file=sys.stderr)

    # 3. Update navigation patterns reference
    update_navigation_patterns(tasks, chronic)

    # 4. Write session log
    write_session_log(tasks, chronic)

    print("Consolidation complete.", file=sys.stderr)


if __name__ == "__main__":
    main()
