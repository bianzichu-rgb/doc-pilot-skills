#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
doc-pilot CLI adapter
Standalone command-line interface — no agent runtime required.

Modes:
  Template mode  — if a matching template exists, run the full interactive step loop.
  API mode       — if ANTHROPIC_API_KEY is set, call Claude directly to generate a plan.
  Prep mode      — extract + classify the document and print a structured prompt
                   ready to paste into any LLM.

Usage:
  python doc_pilot_cli.py --task "Fix E9 error on Bosch dishwasher" --doc /path/to.pdf
  python doc_pilot_cli.py --task "Set up Docker Compose" --doc https://docs.docker.com/...
  python doc_pilot_cli.py --task "IKEA KALLAX assembly" --search
  python doc_pilot_cli.py --list-templates
  python doc_pilot_cli.py --list-templates --task-type fault_diagnosis
"""

import sys
import os
import re
import json
import subprocess
import argparse
import textwrap
from pathlib import Path
from datetime import datetime

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout = open(sys.stdout.fileno(), mode='w', encoding='utf-8', buffering=1)

# ── Locate engine scripts ─────────────────────────────────────────────────────
# Works whether run from repo root or installed anywhere.
_HERE = Path(__file__).resolve().parent
_REPO = _HERE.parent.parent   # adapters/cli/ → adapters/ → repo root

def _find_script(relative: str) -> Path:
    """Find a script in the repo, checking multiple possible install locations."""
    candidates = [
        _REPO / "skills" / relative,
        Path.home() / ".claude" / "skills" / relative,
        Path.home() / ".openclaw" / "skills" / relative,
    ]
    for c in candidates:
        if c.exists():
            return c
    raise FileNotFoundError(
        f"Cannot find {relative}. "
        "Make sure you run this from the doc-pilot-skills repo root, "
        "or install the skills to ~/.claude/skills/ or ~/.openclaw/skills/"
    )

def _run(script_relative: str, *args) -> str:
    """Run an engine script and return stdout."""
    script = _find_script(script_relative)
    result = subprocess.run(
        [sys.executable, str(script)] + list(args),
        capture_output=True, text=True, encoding="utf-8"
    )
    if result.returncode != 0 and result.stderr:
        print(f"  [warn] {result.stderr.strip()}", file=sys.stderr)
    return result.stdout.strip()

# ── Display helpers ───────────────────────────────────────────────────────────

BOLD  = "\033[1m"
GREEN = "\033[92m"
RED   = "\033[91m"
CYAN  = "\033[96m"
DIM   = "\033[2m"
RESET = "\033[0m"

def _h(text: str) -> str:
    return f"{BOLD}{text}{RESET}"

def _ok(text: str) -> str:
    return f"{GREEN}✓{RESET} {text}"

def _warn(text: str) -> str:
    return f"{RED}⚠{RESET}  {text}"

def _step_header(n: int, total: int, title: str, fail_rate: float = 0.0) -> None:
    print(f"\n{BOLD}▶ Step {n} of {total}: {title}{RESET}")
    if fail_rate > 0.20:
        print(_warn(f"Known failure point — {fail_rate:.0%} historical fail rate"))

def _prompt(msg: str) -> str:
    return input(f"\n{CYAN}{msg}{RESET} ").strip()


# ── Template-based interactive loop ──────────────────────────────────────────

def run_template_session(template: dict, task_id: str) -> str:
    """Run an interactive step-by-step session from a template. Returns final outcome."""
    steps = template.get("steps", [])
    total = len(steps)
    task_summary = template.get("template_id", "task")
    cr = template.get("completion_rate", 0)
    uc = template.get("usage_count", 0)

    print(f"\n{_h('📋 Task:')} {task_summary}")
    print(f"   Source: template  |  Success rate: {cr:.0%}  |  Prior completions: {uc}")
    print(f"   Steps: {total}\n")

    current = 0
    while current < total:
        step = steps[current]
        step_id = step.get("step_id", f"s{current+1}")
        title = step.get("title", f"Step {current+1}")
        fail_rate = step.get("historical_fail_rate", 0.0)

        _step_header(current + 1, total, title, fail_rate)

        # If template has sub-steps, show them
        for i, sub in enumerate(step.get("sub_steps", []), 1):
            print(f"  {i}. {sub}")

        if not step.get("sub_steps"):
            print(f"  {DIM}(No detailed sub-steps in template — refer to your document){RESET}")

        answer = _prompt("✅ done / ❌ fail / ⏩ skip / 🚪 quit → ").lower()

        if answer in ("done", "✅", "d", "y", "yes", "ok", "好", "完成"):
            _run("doc-pilot/scripts/task_state.py",
                 "advance", "--task-id", task_id, "--action", "completed")
            current += 1
        elif answer in ("fail", "failed", "❌", "f", "no", "n", "没用", "不行"):
            _run("doc-pilot/scripts/task_state.py",
                 "advance", "--task-id", task_id, "--action", "failed")
            # On fail: try on_fail_goto, else advance anyway
            goto = step.get("on_fail_goto")
            if goto:
                idx = next((i for i, s in enumerate(steps) if s["step_id"] == goto), None)
                if idx is not None:
                    current = idx
                    continue
            current += 1
        elif answer in ("skip", "s", "⏩"):
            current += 1
        elif answer in ("quit", "q", "exit", "🚪"):
            return "abandoned"
        else:
            print("  Type: done / fail / skip / quit")

    return "self_resolved"


# ── API plan generation (requires ANTHROPIC_API_KEY) ──────────────────────────

def generate_plan_via_api(task: str, doc_content: str, sections_json: str) -> list:
    """Call Anthropic API to generate a step plan. Returns list of step dicts."""
    try:
        import anthropic
    except ImportError:
        return []

    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        return []

    client = anthropic.Anthropic(api_key=api_key)

    # Trim content to avoid hitting token limits
    doc_excerpt = doc_content[:8000] if doc_content else ""
    sections_summary = ""
    if sections_json:
        try:
            secs = json.loads(sections_json).get("sections", [])
            relevant = [s for s in secs if s.get("confidence", 0) > 0.5][:5]
            sections_summary = "\n".join(
                f"- [{s['category']}] {s['title']}" for s in relevant
            )
        except Exception:
            pass

    prompt = textwrap.dedent(f"""
    You are a document navigation assistant. Generate a clear step-by-step task plan.

    Task: {task}

    Document sections identified:
    {sections_summary or "(not classified)"}

    Relevant document excerpt:
    {doc_excerpt or "(no document provided — use general knowledge)"}

    Return a JSON array of 3-6 steps. Each step:
    {{
      "step_id": "s1",
      "title": "Short action title (≤10 words)",
      "sub_steps": ["sub-step 1", "sub-step 2", "sub-step 3"],
      "expected_outcome": "What success looks like"
    }}

    Only include steps grounded in the document. Start from simplest solution.
    Return ONLY the JSON array, no other text.
    """).strip()

    try:
        message = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=1024,
            messages=[{"role": "user", "content": prompt}]
        )
        text = message.content[0].text.strip()
        # Extract JSON array
        match = re.search(r'\[.*\]', text, re.DOTALL)
        if match:
            return json.loads(match.group())
    except Exception as e:
        print(f"  [warn] API plan generation failed: {e}", file=sys.stderr)

    return []


# ── Prep mode: structured output for paste-into-LLM ──────────────────────────

def print_prep_prompt(task: str, doc_content: str, sections_json: str) -> None:
    """Print a structured prompt the user can paste into any LLM."""
    print(f"\n{'─'*60}")
    print(_h("📋 Paste this into any LLM to generate your step plan:"))
    print('─'*60)
    print(textwrap.dedent(f"""
    You are a document navigation assistant.
    Task: {task}

    Based on the document content below, generate a clear 3-6 step plan.
    For each step: title (≤10 words), 3 sub-steps, expected outcome.
    Start from the simplest solution. Ground every step in the document.

    --- DOCUMENT CONTENT ---
    {(doc_content or "(no document)")[:4000]}
    --- END ---
    """).strip())
    print('─'*60)


# ── Main command ──────────────────────────────────────────────────────────────

def cmd_run(args):
    task     = args.task
    doc_hint = args.doc or ""
    brand    = args.brand or ""
    product  = args.product or ""
    fault    = args.fault_code or ""
    task_type = args.task_type or "general"

    print(f"\n{_h('doc-pilot')} — document task navigator\n")

    # ── Step 1: Document acquisition ─────────────────────────────────────────
    doc_content = ""
    sections_json = ""

    if doc_hint:
        # Determine strategy
        try:
            strategy_out = _run("doc-pilot/scripts/fetch_doc.py", "strategy", "--hint", doc_hint)
            strat = json.loads(strategy_out)[0] if strategy_out.startswith("[") else {}
            print(_ok(f"Strategy: {strat.get('type', 'unknown')} — {strat.get('action', '')}"))
        except Exception:
            pass

        # If it's a local PDF, extract it
        if doc_hint.lower().endswith(".pdf") and Path(doc_hint).exists():
            print(_ok(f"Extracting PDF: {Path(doc_hint).name}"))
            doc_content = _run("doc-pilot-pdf/scripts/extract.py", doc_hint)
            print(_ok(f"Extracted {len(doc_content)} chars"))

            # Classify sections
            if doc_content:
                import tempfile
                with tempfile.NamedTemporaryFile(mode='w', suffix='.md',
                                                 delete=False, encoding='utf-8') as f:
                    f.write(doc_content)
                    tmp_path = f.name
                sections_json = _run("doc-pilot-analyst/scripts/analyse.py",
                                     tmp_path, "--json")
                Path(tmp_path).unlink(missing_ok=True)
                if sections_json:
                    print(_ok("Classified document sections"))

        elif doc_hint.startswith("http"):
            print(f"  {DIM}URL fetching requires an agent runtime (Claude Code / Claw).{RESET}")
            print(f"  {DIM}Run: WebFetch {doc_hint} and paste content with --doc-text flag.{RESET}")

    # ── Step 2: Template lookup ───────────────────────────────────────────────
    print("")
    template = None
    try:
        lookup_args = ["lookup", "--task-type", task_type]
        if product:
            lookup_args += ["--product", product]
        if brand:
            lookup_args += ["--brand", brand]
        if fault:
            lookup_args += ["--fault-code", fault]

        lookup_out = _run("doc-pilot/scripts/template_store.py", *lookup_args)
        result = json.loads(lookup_out) if lookup_out else {}
        if result.get("found"):
            template = result["template"]
            cr = template.get("completion_rate", 0)
            uc = template.get("usage_count", 0)
            src = result.get("source", "")
            print(_ok(f"Template matched ({src}): {template['template_id']}"))
            print(f"   Success rate: {cr:.0%}  |  Completions: {uc}")
        else:
            print(f"  {DIM}No template found — generating plan...{RESET}")
    except Exception as e:
        print(f"  [warn] Template lookup failed: {e}", file=sys.stderr)

    # ── Step 3: Build or reuse task plan ─────────────────────────────────────
    steps = template.get("steps", []) if template else []

    if not steps:
        # Try API generation
        steps = generate_plan_via_api(task, doc_content, sections_json)
        if steps:
            print(_ok(f"Generated {len(steps)}-step plan via API"))
        else:
            # Prep mode: print structured prompt for paste-into-LLM
            print_prep_prompt(task, doc_content, sections_json)
            print(f"\n  {DIM}Set ANTHROPIC_API_KEY to enable automatic plan generation.{RESET}")
            return

    # ── Step 4: Create task state ─────────────────────────────────────────────
    task_id = f"cli_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    steps_json = json.dumps(steps)
    try:
        _run("doc-pilot/scripts/task_state.py",
             "create", "--task-id", task_id,
             "--summary", task,
             "--steps-json", steps_json,
             "--task-type", task_type)
    except Exception:
        pass  # Non-fatal — state tracking optional for CLI

    # ── Step 5: Interactive step loop ─────────────────────────────────────────
    # Use the template or generated steps
    effective_template = template or {
        "template_id": task,
        "steps": steps,
        "completion_rate": 0.0,
        "usage_count": 0,
    }
    outcome = run_template_session(effective_template, task_id)

    # ── Step 6: Record outcome ────────────────────────────────────────────────
    print(f"\n{'─'*60}")
    if outcome == "self_resolved":
        print(_ok("Task completed successfully!"))
    elif outcome == "abandoned":
        print(f"  Task abandoned.")
    else:
        print(f"  Outcome: {outcome}")

    try:
        _run("doc-pilot/scripts/task_state.py",
             "complete", "--task-id", task_id, "--outcome", outcome)
        _run("doc-pilot/scripts/template_store.py",
             "record", "--task-id", task_id)
        print(_ok("Outcome recorded — template library updated"))
    except Exception:
        pass

    print()


def cmd_list_templates(args):
    """List available templates."""
    list_args = ["list-templates"]
    if args.task_type:
        list_args += ["--task-type", args.task_type]
    out = _run("doc-pilot/scripts/template_store.py", *list_args)
    templates = json.loads(out) if out else []

    if not templates:
        print("No templates yet. Complete a task first.")
        return

    print(f"\n{'Template':<35} {'Type':<20} {'Rate':>6} {'Uses':>5}")
    print("─" * 72)
    for t in templates:
        rate = t.get("completion_rate", 0)
        bar = "█" * int(rate * 8) + "░" * (8 - int(rate * 8))
        print(f"{t['template_id']:<35} {t.get('task_type',''):<20} "
              f"{rate:>5.0%}  {t.get('usage_count', 0):>4}  {bar}")
    print()


# ── CLI entry point ───────────────────────────────────────────────────────────

def main():
    p = argparse.ArgumentParser(
        description="doc-pilot CLI — standalone document task navigator",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=textwrap.dedent("""
        Examples:
          # Navigate with a local PDF
          python doc_pilot_cli.py --task "Fix E9 on Bosch dishwasher" \\
            --doc /path/to/manual.pdf --brand bosch --fault-code E9

          # Navigate with a known fault code (uses templates)
          python doc_pilot_cli.py --task "Fix E9 error" \\
            --task-type fault_diagnosis --product dishwasher --brand bosch --fault-code E9

          # List all saved templates
          python doc_pilot_cli.py --list-templates

          # Set ANTHROPIC_API_KEY for automatic plan generation:
          export ANTHROPIC_API_KEY=sk-ant-...
        """)
    )
    p.add_argument("--task", help="What you want to accomplish")
    p.add_argument("--doc",  help="Document source: local path or URL")
    p.add_argument("--task-type", default="general",
                   help="Task type: fault_diagnosis / installation / maintenance / setup / recipe")
    p.add_argument("--product",    help="Product category (e.g. dishwasher)")
    p.add_argument("--brand",      help="Brand name (e.g. bosch)")
    p.add_argument("--fault-code", help="Error/fault code (e.g. E9)")
    p.add_argument("--list-templates", action="store_true",
                   help="List available templates and exit")

    args = p.parse_args()

    if args.list_templates:
        cmd_list_templates(args)
    elif args.task:
        cmd_run(args)
    else:
        p.print_help()


if __name__ == "__main__":
    main()
