#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
doc-pilot template_store.py
Learning flywheel: task template CRUD + EWMA updates + skill performance tracking.

Ported & extended from CognoLiving 2.0 Phase B architecture.
No external dependencies.

Usage:
  # Template operations
  python template_store.py lookup   --task-type <type> --product <cat> [--brand <b>] [--fault-code <fc>]
  python template_store.py record   --task-id <id>
  python template_store.py list-templates [--task-type <type>]
  python template_store.py show-template --template-id <tid>

  # Skill performance tracking (meta-learning)
  python template_store.py skill-feedback --skill-name <name> --task-type <type> --outcome <helpful|not_helpful|error> [--notes <text>]
  python template_store.py skill-stats    [--task-type <type>]
"""

import sys
import json
import argparse
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Dict, List, Any

MEMORY_DIR = Path(__file__).parent.parent / "memory"
TASK_DIR = MEMORY_DIR / "tasks"
TEMPLATE_DIR = MEMORY_DIR / "templates"
SKILL_PERF_FILE = MEMORY_DIR / "skill_performance.json"

for d in (TASK_DIR, TEMPLATE_DIR):
    d.mkdir(parents=True, exist_ok=True)

EWMA_ALPHA = 0.2  # New data weight: 20%, history: 80%
MIN_TASKS_FOR_TEMPLATE = 3  # Minimum completions before creating a template


# ─── Helpers ──────────────────────────────────────────────────────────────────

def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def ewma(old: float, new_val: float, alpha: float = EWMA_ALPHA) -> float:
    return alpha * new_val + (1 - alpha) * old


def atomic_write(path: Path, data: Dict):
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(path)


def template_key(task_type: str, product: str, brand: Optional[str],
                 fault_code: Optional[str]) -> str:
    parts = [task_type.lower(), product.lower()]
    if brand:
        parts.append(brand.lower())
    if fault_code:
        parts.append(fault_code.upper())
    return "_".join(p for p in parts if p)


# ─── Template Lookup ───────────────────────────────────────────────────────────

def cmd_lookup(args):
    """Find best matching template for a given task profile."""
    key = template_key(args.task_type, args.product or "",
                       args.brand, args.fault_code)

    # Layer 1: Exact key match
    exact_path = TEMPLATE_DIR / f"{key}.json"
    if exact_path.exists():
        tmpl = json.loads(exact_path.read_text(encoding="utf-8"))
        if tmpl.get("completion_rate", 0) >= 0.6:  # Min viable template
            print(json.dumps({"found": True, "source": "exact_match", "template": tmpl},
                             ensure_ascii=False, indent=2))
            return

    # Layer 2: Partial key match (drop fault_code, then brand)
    candidates = []
    for tmpl_path in TEMPLATE_DIR.glob("*.json"):
        try:
            t = json.loads(tmpl_path.read_text(encoding="utf-8"))
            score = _match_score(t, args.task_type, args.product or "",
                                 args.brand, args.fault_code)
            if score > 0.5:
                candidates.append((score, t))
        except Exception:
            continue

    if candidates:
        candidates.sort(key=lambda x: x[0], reverse=True)
        best_score, best = candidates[0]
        if best.get("completion_rate", 0) >= 0.6:
            print(json.dumps({
                "found": True,
                "source": "partial_match",
                "match_score": best_score,
                "template": best
            }, ensure_ascii=False, indent=2))
            return

    print(json.dumps({"found": False, "message": "No suitable template — use LLM generation"},
                     ensure_ascii=False))


def _match_score(tmpl: Dict, task_type: str, product: str,
                 brand: Optional[str], fault_code: Optional[str]) -> float:
    score = 0.0
    if tmpl.get("task_type", "").lower() == task_type.lower():
        score += 0.4
    if tmpl.get("product_category", "").lower() == (product or "").lower():
        score += 0.3
    if brand and tmpl.get("brand", "").lower() == brand.lower():
        score += 0.2
    if fault_code and tmpl.get("fault_code", "").upper() == fault_code.upper():
        score += 0.1
    return score


# ─── Record Task Outcome & Update/Create Template ─────────────────────────────

def cmd_record(args):
    """Record a completed task into the template library (EWMA update)."""
    task_path = TASK_DIR / f"{args.task_id}.json"
    if not task_path.exists():
        print(f"ERROR: Task not found: {args.task_id}", file=sys.stderr)
        sys.exit(1)

    task = json.loads(task_path.read_text(encoding="utf-8"))
    outcome = task.get("final_outcome", "")
    success = 1.0 if outcome == "self_resolved" else 0.0
    escalated = 1.0 if outcome == "escalated" else 0.0

    key = template_key(
        task.get("task_type", "general"),
        task.get("product_category", ""),
        task.get("brand"),
        task.get("fault_code"),
    )
    tmpl_path = TEMPLATE_DIR / f"{key}.json"

    if tmpl_path.exists():
        # Update existing template with EWMA
        tmpl = json.loads(tmpl_path.read_text(encoding="utf-8"))
        old_rate = tmpl.get("completion_rate", 0.5)
        old_esc = tmpl.get("escalation_rate", 0.1)
        old_dur = tmpl.get("avg_duration_sec", 0)
        new_dur = task.get("total_duration_sec", 0)

        tmpl["completion_rate"] = ewma(old_rate, success)
        tmpl["escalation_rate"] = ewma(old_esc, escalated)
        tmpl["avg_duration_sec"] = ewma(old_dur, new_dur) if new_dur > 0 else old_dur
        tmpl["usage_count"] = tmpl.get("usage_count", 0) + 1
        tmpl["last_updated"] = now_iso()
        tmpl["sourced_from"].append(args.task_id)

        # Update per-step failure stats
        for step in tmpl.get("steps", []):
            sid = step["step_id"]
            fail_count = task["failure_path"].count(sid)
            step["fail_count"] = step.get("fail_count", 0) + fail_count
            step["run_count"] = step.get("run_count", 0) + 1
            if step["run_count"] > 0:
                step["historical_fail_rate"] = step["fail_count"] / step["run_count"]

        atomic_write(tmpl_path, tmpl)
        print(json.dumps({
            "action": "updated",
            "template_id": key,
            "new_completion_rate": tmpl["completion_rate"],
            "usage_count": tmpl["usage_count"],
        }, ensure_ascii=False))

    else:
        # Check if enough history to create a new template
        similar_count = sum(
            1 for p in TASK_DIR.glob("*.json")
            if _is_similar_task(json.loads(p.read_text(encoding="utf-8")), task)
        )

        if similar_count < MIN_TASKS_FOR_TEMPLATE:
            print(json.dumps({
                "action": "stored_only",
                "message": f"Need {MIN_TASKS_FOR_TEMPLATE} similar tasks to create template "
                           f"(have {similar_count})",
            }, ensure_ascii=False))
            return

        # Create new template from this task's steps
        steps = []
        for s in task.get("steps", []):
            fail_count = task["failure_path"].count(s["step_id"])
            steps.append({
                "step_id": s["step_id"],
                "title": s["title"],
                "difficulty": s.get("difficulty", "normal"),
                "skill_tags": s.get("skill_tags", []),
                "safety_level": s.get("safety_level", "safe"),
                "on_fail_goto": s.get("on_fail_goto"),
                "fail_count": fail_count,
                "run_count": 1,
                "historical_fail_rate": float(fail_count),
            })

        new_tmpl = {
            "template_id": key,
            "task_type": task.get("task_type", "general"),
            "product_category": task.get("product_category", ""),
            "brand": task.get("brand"),
            "fault_code": task.get("fault_code"),
            "steps": steps,
            "usage_count": 1,
            "completion_rate": success,
            "escalation_rate": escalated,
            "avg_duration_sec": float(task.get("total_duration_sec", 0)),
            "sourced_from": [args.task_id],
            "created_at": now_iso(),
            "last_updated": now_iso(),
            "auto_generated": True,
        }
        atomic_write(tmpl_path, new_tmpl)
        print(json.dumps({
            "action": "created",
            "template_id": key,
            "completion_rate": success,
        }, ensure_ascii=False))


def _is_similar_task(a: Dict, b: Dict) -> bool:
    return (a.get("task_type") == b.get("task_type") and
            a.get("product_category") == b.get("product_category") and
            a.get("brand") == b.get("brand"))


# ─── Skill Performance Tracking (Meta-Learning) ───────────────────────────────

def _load_skill_perf() -> Dict:
    if SKILL_PERF_FILE.exists():
        try:
            return json.loads(SKILL_PERF_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"skills": {}, "last_updated": now_iso()}


def cmd_skill_feedback(args):
    """Record whether an external skill was helpful for a given task type."""
    perf = _load_skill_perf()
    skill = args.skill_name
    task_type = args.task_type
    outcome = args.outcome  # "helpful" | "not_helpful" | "error"

    if skill not in perf["skills"]:
        perf["skills"][skill] = {}

    if task_type not in perf["skills"][skill]:
        perf["skills"][skill][task_type] = {
            "helpful": 0, "not_helpful": 0, "error": 0,
            "total": 0, "helpful_rate": 0.0,
            "notes": [], "last_used": now_iso(),
        }

    entry = perf["skills"][skill][task_type]
    entry[outcome] = entry.get(outcome, 0) + 1
    entry["total"] = entry.get("total", 0) + 1
    entry["helpful_rate"] = entry["helpful"] / entry["total"]
    entry["last_used"] = now_iso()

    if args.notes:
        entry["notes"].append({"note": args.notes, "at": now_iso(), "outcome": outcome})
        entry["notes"] = entry["notes"][-10:]  # Keep last 10 notes

    perf["last_updated"] = now_iso()
    atomic_write(SKILL_PERF_FILE, perf)

    print(json.dumps({
        "skill": skill, "task_type": task_type, "outcome": outcome,
        "helpful_rate": entry["helpful_rate"], "total_uses": entry["total"],
    }, ensure_ascii=False))


def cmd_skill_stats(args):
    """Show performance stats for all skills (optionally filtered by task type)."""
    perf = _load_skill_perf()

    if not perf["skills"]:
        print("No skill performance data yet.")
        return

    rows = []
    for skill, task_data in perf["skills"].items():
        for task_type, entry in task_data.items():
            if args.task_type and task_type != args.task_type:
                continue
            rows.append({
                "skill": skill,
                "task_type": task_type,
                "helpful_rate": entry.get("helpful_rate", 0),
                "total_uses": entry.get("total", 0),
                "helpful": entry.get("helpful", 0),
                "not_helpful": entry.get("not_helpful", 0),
                "error": entry.get("error", 0),
                "last_used": entry.get("last_used", ""),
            })

    # Sort by helpful_rate desc
    rows.sort(key=lambda r: r["helpful_rate"], reverse=True)

    if args.json if hasattr(args, 'json') else False:
        print(json.dumps(rows, ensure_ascii=False, indent=2))
    else:
        print(f"{'Skill':<30} {'Task Type':<20} {'Rate':>6} {'Uses':>5}")
        print("-" * 65)
        for r in rows:
            bar = "█" * int(r["helpful_rate"] * 10) + "░" * (10 - int(r["helpful_rate"] * 10))
            print(f"{r['skill']:<30} {r['task_type']:<20} "
                  f"{r['helpful_rate']:>5.0%}  {r['total_uses']:>4}  {bar}")


# ─── List / Show Templates ─────────────────────────────────────────────────────

def cmd_list_templates(args):
    templates = []
    for p in sorted(TEMPLATE_DIR.glob("*.json"), key=lambda f: f.stat().st_mtime, reverse=True):
        try:
            t = json.loads(p.read_text(encoding="utf-8"))
            if args.task_type and t.get("task_type") != args.task_type:
                continue
            templates.append({
                "template_id": t["template_id"],
                "task_type": t.get("task_type"),
                "product_category": t.get("product_category"),
                "brand": t.get("brand"),
                "fault_code": t.get("fault_code"),
                "completion_rate": t.get("completion_rate", 0),
                "usage_count": t.get("usage_count", 0),
                "steps": len(t.get("steps", [])),
            })
        except Exception:
            continue
    print(json.dumps(templates, ensure_ascii=False, indent=2))


def cmd_show_template(args):
    p = TEMPLATE_DIR / f"{args.template_id}.json"
    if not p.exists():
        print(f"ERROR: Template not found: {args.template_id}", file=sys.stderr)
        sys.exit(1)
    print(p.read_text(encoding="utf-8"))


# ─── CLI ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="doc-pilot template store + skill tracker")
    sub = parser.add_subparsers(dest="command")

    # lookup
    p = sub.add_parser("lookup")
    p.add_argument("--task-type", required=True)
    p.add_argument("--product", default="")
    p.add_argument("--brand")
    p.add_argument("--fault-code")

    # record
    p = sub.add_parser("record")
    p.add_argument("--task-id", required=True)

    # list-templates
    p = sub.add_parser("list-templates")
    p.add_argument("--task-type")

    # show-template
    p = sub.add_parser("show-template")
    p.add_argument("--template-id", required=True)

    # skill-feedback
    p = sub.add_parser("skill-feedback")
    p.add_argument("--skill-name", required=True)
    p.add_argument("--task-type", required=True)
    p.add_argument("--outcome", choices=["helpful", "not_helpful", "error"], required=True)
    p.add_argument("--notes")

    # skill-stats
    p = sub.add_parser("skill-stats")
    p.add_argument("--task-type")
    p.add_argument("--json", action="store_true")

    args = parser.parse_args()
    dispatch = {
        "lookup": cmd_lookup,
        "record": cmd_record,
        "list-templates": cmd_list_templates,
        "show-template": cmd_show_template,
        "skill-feedback": cmd_skill_feedback,
        "skill-stats": cmd_skill_stats,
    }
    if args.command not in dispatch:
        parser.print_help()
        sys.exit(1)
    dispatch[args.command](args)


if __name__ == "__main__":
    main()
