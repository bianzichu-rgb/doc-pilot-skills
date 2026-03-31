#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
doc-pilot task_state.py
TaskPlan state machine — persistent JSON-based task tracking.

Ported from CognoLiving 2.0 (qa_schemas.py, task_store.py).
No external dependencies.

Usage:
  python task_state.py create   --task-id <id> --summary <text> --steps-json <json>
  python task_state.py advance  --task-id <id> --action <completed|failed>
  python task_state.py complete --task-id <id> --outcome <self_resolved|escalated|abandoned>
  python task_state.py show     --task-id <id>
  python task_state.py list     [--status in_progress]
"""

import sys
import json
import argparse
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, List, Dict, Any

MEMORY_DIR = Path(__file__).parent.parent / "memory" / "tasks"
MEMORY_DIR.mkdir(parents=True, exist_ok=True)


# ─── Data Helpers ─────────────────────────────────────────────────────────────

def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_task(task_id: str) -> Dict:
    path = MEMORY_DIR / f"{task_id}.json"
    if not path.exists():
        print(f"ERROR: Task not found: {task_id}", file=sys.stderr)
        sys.exit(1)
    return json.loads(path.read_text(encoding="utf-8"))


def save_task(task: Dict):
    task_id = task["task_id"]
    path = MEMORY_DIR / f"{task_id}.json"
    # Atomic write (temp → replace)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(task, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(path)


# ─── Commands ─────────────────────────────────────────────────────────────────

def cmd_create(args):
    """Create a new task and persist it."""
    task_id = args.task_id or str(uuid.uuid4())

    # Parse steps from JSON string
    try:
        steps_raw = json.loads(args.steps_json)
    except json.JSONDecodeError as e:
        print(f"ERROR: Invalid --steps-json: {e}", file=sys.stderr)
        sys.exit(1)

    steps = []
    for i, s in enumerate(steps_raw):
        steps.append({
            "step_id": i + 1,
            "title": s.get("title", f"Step {i+1}"),
            "description": s.get("description", ""),
            "status": "current" if i == 0 else "pending",
            "difficulty": s.get("difficulty", "normal"),
            "skill_tags": s.get("skill_tags", []),
            "safety_level": s.get("safety_level", "safe"),
            "on_fail_goto": s.get("on_fail_goto"),
            "attempts": [],
            "expected_success_rate": s.get("expected_success_rate", 0.0),
        })

    task = {
        "task_id": task_id,
        "task_summary": args.summary,
        "task_type": args.task_type or "general",
        "product_category": args.product or "",
        "brand": args.brand or None,
        "fault_code": args.fault_code or None,
        "template_id": args.template_id or None,
        "source": args.source or "llm_generated",
        "total_steps": len(steps),
        "current_step": 1,
        "status": "in_progress",
        "steps": steps,
        "completion_path": [],
        "failure_path": [],
        "final_outcome": "",
        "created_at": now_iso(),
        "last_active_at": now_iso(),
        "completed_at": "",
        "total_duration_sec": 0,
        "skills_used": [],  # tracks external skills invoked during this task
    }

    save_task(task)
    print(json.dumps({"task_id": task_id, "status": "created", "total_steps": len(steps)},
                     ensure_ascii=False))


def cmd_advance(args):
    """Advance to the next step after user feedback (completed or failed)."""
    task = load_task(args.task_id)

    if task["status"] != "in_progress":
        print(f"ERROR: Task is already {task['status']}", file=sys.stderr)
        sys.exit(1)

    action = args.action  # "completed" or "failed"
    current_idx = task["current_step"] - 1
    step = task["steps"][current_idx]

    # Record attempt
    step["attempts"].append({
        "attempted_at": now_iso(),
        "action": action,
    })
    step["status"] = "completed" if action == "completed" else "failed"

    if action == "completed":
        task["completion_path"].append(step["step_id"])
    else:
        task["failure_path"].append(step["step_id"])

    # Determine next step — check on_fail_goto for branching
    if action == "failed" and step.get("on_fail_goto"):
        next_step_id = step["on_fail_goto"]
        task["current_step"] = next_step_id
    else:
        task["current_step"] += 1

    task["last_active_at"] = now_iso()

    # Check if done
    if task["current_step"] > task["total_steps"]:
        if action == "completed":
            task["status"] = "completed"
            task["final_outcome"] = "self_resolved"
            outcome_msg = "✅ All steps completed — issue resolved!"
        else:
            task["status"] = "escalated"
            task["final_outcome"] = "escalated"
            outcome_msg = "⚠️ All steps attempted — recommend professional assistance."
        task["completed_at"] = now_iso()
        save_task(task)
        print(json.dumps({
            "status": task["status"],
            "final_outcome": task["final_outcome"],
            "message": outcome_msg,
            "task_id": task["task_id"],
        }, ensure_ascii=False))
        return

    # Set next step as current
    next_idx = task["current_step"] - 1
    task["steps"][next_idx]["status"] = "current"
    next_step = task["steps"][next_idx]

    save_task(task)
    print(json.dumps({
        "status": "in_progress",
        "current_step": task["current_step"],
        "total_steps": task["total_steps"],
        "next_step_title": next_step["title"],
        "next_step_difficulty": next_step.get("difficulty", "normal"),
        "next_step_safety": next_step.get("safety_level", "safe"),
        "expected_success_rate": next_step.get("expected_success_rate", 0.0),
        "task_id": task["task_id"],
    }, ensure_ascii=False))


def cmd_complete(args):
    """Mark task as fully complete with a final outcome."""
    task = load_task(args.task_id)
    task["status"] = args.outcome if args.outcome in ("completed", "escalated", "abandoned") else "completed"
    task["final_outcome"] = args.outcome or "self_resolved"
    task["completed_at"] = now_iso()

    # Calculate duration
    try:
        created = datetime.fromisoformat(task["created_at"])
        task["total_duration_sec"] = int((datetime.now(timezone.utc) - created).total_seconds())
    except Exception:
        task["total_duration_sec"] = 0

    save_task(task)
    print(json.dumps({
        "task_id": task["task_id"],
        "final_outcome": task["final_outcome"],
        "total_steps": task["total_steps"],
        "completion_path": task["completion_path"],
        "failure_path": task["failure_path"],
        "duration_sec": task["total_duration_sec"],
    }, ensure_ascii=False))


def cmd_show(args):
    task = load_task(args.task_id)
    print(json.dumps(task, ensure_ascii=False, indent=2))


def cmd_list(args):
    tasks = []
    for f in sorted(MEMORY_DIR.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True):
        try:
            t = json.loads(f.read_text(encoding="utf-8"))
            if args.status and t.get("status") != args.status:
                continue
            tasks.append({
                "task_id": t["task_id"],
                "summary": t.get("task_summary", ""),
                "status": t.get("status", ""),
                "created_at": t.get("created_at", ""),
                "current_step": t.get("current_step", 1),
                "total_steps": t.get("total_steps", 0),
            })
        except Exception:
            continue
    print(json.dumps(tasks, ensure_ascii=False, indent=2))


# ─── CLI ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="doc-pilot task state manager")
    sub = parser.add_subparsers(dest="command")

    # create
    p_create = sub.add_parser("create")
    p_create.add_argument("--task-id")
    p_create.add_argument("--summary", required=True)
    p_create.add_argument("--steps-json", required=True, help='JSON array of step objects')
    p_create.add_argument("--task-type", default="general")
    p_create.add_argument("--product", default="")
    p_create.add_argument("--brand")
    p_create.add_argument("--fault-code")
    p_create.add_argument("--template-id")
    p_create.add_argument("--source", default="llm_generated")

    # advance
    p_adv = sub.add_parser("advance")
    p_adv.add_argument("--task-id", required=True)
    p_adv.add_argument("--action", choices=["completed", "failed"], required=True)

    # complete
    p_comp = sub.add_parser("complete")
    p_comp.add_argument("--task-id", required=True)
    p_comp.add_argument("--outcome", default="self_resolved",
                        choices=["self_resolved", "escalated", "abandoned"])

    # show
    p_show = sub.add_parser("show")
    p_show.add_argument("--task-id", required=True)

    # list
    p_list = sub.add_parser("list")
    p_list.add_argument("--status")

    args = parser.parse_args()
    dispatch = {
        "create": cmd_create,
        "advance": cmd_advance,
        "complete": cmd_complete,
        "show": cmd_show,
        "list": cmd_list,
    }
    if args.command not in dispatch:
        parser.print_help()
        sys.exit(1)
    dispatch[args.command](args)


if __name__ == "__main__":
    main()
