#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
doc-pilot agent_dispatch.py
Multi-agent capability router with performance-aware selection.

Each "agent" is any callable capability: a Claude Code sub-skill, a direct Claude API
model variant, an external API, or a Claude tool (WebSearch, etc.).

The dispatcher answers: "For task_type X needing capability Y, which agent should I call?"
Decision is based on: agent enabled state + historical success rate (from skill_performance.json).

Usage:
  python agent_dispatch.py list-agents [--capability <cap>]
  python agent_dispatch.py best-agent  --capability <cap> [--task-type <type>]
  python agent_dispatch.py record      --agent <name> --capability <cap> --task-type <type> --outcome <ok|fail>
  python agent_dispatch.py show-registry
"""

import sys
import json
import argparse
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Dict, Any

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout = open(sys.stdout.fileno(), mode='w', encoding='utf-8', buffering=1)

MEMORY_DIR   = Path(__file__).parent.parent / "memory"
REGISTRY_FILE = MEMORY_DIR / "agent_registry.json"
PERF_FILE     = MEMORY_DIR / "skill_performance.json"
EWMA_ALPHA    = 0.25   # slightly faster adaptation than template store (0.2)

MEMORY_DIR.mkdir(parents=True, exist_ok=True)

# ─── Default Registry ─────────────────────────────────────────────────────────

DEFAULT_REGISTRY: Dict[str, Any] = {
    "_schema": "1.0",
    "_note": "Edit this file to enable/disable agents or add new ones. 'enabled: false' agents are never dispatched.",
    "agents": {
        # ── Built-in Claude Code Sub-Skills ──────────────────────────────────
        "doc-pilot-pdf": {
            "type": "claude_skill",
            "capabilities": ["pdf_extraction", "layout_analysis", "toc_extraction"],
            "invoke": "python ~/.claude/skills/doc-pilot-pdf/scripts/extract.py <input> --output <output>",
            "notes": "Font-hierarchy PDF extractor. Best for multi-column manuals, spec tables.",
            "enabled": True
        },
        "doc-pilot-analyst": {
            "type": "claude_skill",
            "capabilities": ["section_classification", "structure_analysis", "category_routing"],
            "invoke": "python ~/.claude/skills/doc-pilot-analyst/scripts/analyse.py <input>",
            "notes": "9-category semantic classifier. Use before navigating long documents.",
            "enabled": True
        },
        # ── Claude API Model Variants ─────────────────────────────────────────
        # Enable by setting enabled=true and ensuring ANTHROPIC_API_KEY is set.
        "claude-haiku": {
            "type": "claude_api",
            "model": "claude-haiku-4-5-20251001",
            "capabilities": ["translation", "fast_qa", "text_summarization", "language_detection"],
            "notes": "Fast + cheap. Best for preprocessing: translate non-English sections, detect language, quick filtering.",
            "enabled": False,
            "requires_env": "ANTHROPIC_API_KEY"
        },
        "claude-sonnet": {
            "type": "claude_api",
            "model": "claude-sonnet-4-6",
            "capabilities": ["complex_reasoning", "multi_step_planning", "ambiguous_instructions", "fault_diagnosis"],
            "notes": "Balanced. Use for fault diagnosis on unusual error codes or poorly-structured manuals.",
            "enabled": False,
            "requires_env": "ANTHROPIC_API_KEY"
        },
        "claude-opus": {
            "type": "claude_api",
            "model": "claude-opus-4-6",
            "capabilities": ["complex_reasoning", "multi_step_planning", "ambiguous_instructions", "safety_critical"],
            "notes": "Highest accuracy. Reserve for safety-critical steps or very complex multi-dependency tasks.",
            "enabled": False,
            "requires_env": "ANTHROPIC_API_KEY"
        },
        # ── Claude Built-in Tools ─────────────────────────────────────────────
        "websearch": {
            "type": "claude_tool",
            "capabilities": ["document_search", "product_lookup", "manual_search", "error_code_lookup"],
            "invoke": "WebSearch",
            "notes": "Use when no local PDF or URL is provided. Good for recent firmware and error codes.",
            "enabled": True
        },
        "webfetch": {
            "type": "claude_tool",
            "capabilities": ["url_document_fetch", "online_manual_fetch"],
            "invoke": "WebFetch",
            "notes": "Direct URL retrieval. Prefer over websearch when URL is already known.",
            "enabled": True
        }
    }
}

# ─── Registry I/O ─────────────────────────────────────────────────────────────

def _load_registry() -> Dict[str, Any]:
    if REGISTRY_FILE.exists():
        try:
            return json.loads(REGISTRY_FILE.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            pass
    # First run: write default and return it
    _save_registry(DEFAULT_REGISTRY)
    return DEFAULT_REGISTRY


def _save_registry(reg: Dict[str, Any]) -> None:
    tmp = REGISTRY_FILE.with_suffix(".tmp")
    tmp.write_text(json.dumps(reg, indent=2, ensure_ascii=False), encoding="utf-8")
    tmp.replace(REGISTRY_FILE)


# ─── Performance I/O (reuses skill_performance.json format) ───────────────────

def _load_perf() -> Dict[str, Any]:
    if PERF_FILE.exists():
        try:
            return json.loads(PERF_FILE.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            pass
    return {}


def _save_perf(perf: Dict[str, Any]) -> None:
    tmp = PERF_FILE.with_suffix(".tmp")
    tmp.write_text(json.dumps(perf, indent=2, ensure_ascii=False), encoding="utf-8")
    tmp.replace(PERF_FILE)


def _agent_perf_key(agent: str, capability: str, task_type: Optional[str]) -> str:
    parts = ["agent", agent, capability]
    if task_type:
        parts.append(task_type)
    return "/".join(parts)


# ─── Commands ─────────────────────────────────────────────────────────────────

def cmd_list_agents(capability: Optional[str]) -> None:
    reg = _load_registry()
    perf = _load_perf()
    agents = reg.get("agents", {})
    print(f"{'Agent':<22} {'Type':<14} {'Enabled':<8} {'Capabilities'}")
    print("-" * 80)
    for name, cfg in agents.items():
        if capability and capability not in cfg.get("capabilities", []):
            continue
        caps = ", ".join(cfg.get("capabilities", []))
        enabled = "✓" if cfg.get("enabled", False) else "✗"
        print(f"{name:<22} {cfg.get('type',''):<14} {enabled:<8} {caps}")


def cmd_best_agent(capability: str, task_type: Optional[str]) -> None:
    reg = _load_registry()
    perf = _load_perf()
    agents = reg.get("agents", {})

    candidates = []
    for name, cfg in agents.items():
        if not cfg.get("enabled", False):
            continue
        if capability not in cfg.get("capabilities", []):
            continue
        key = _agent_perf_key(name, capability, task_type)
        entry = perf.get(key, {})
        rate = entry.get("success_rate", 0.7)   # default optimistic prior
        calls = entry.get("total_calls", 0)
        candidates.append((name, rate, calls, cfg))

    if not candidates:
        # Fall back: check without task_type filter
        if task_type:
            cmd_best_agent(capability, None)
            return
        print(f"NO_AGENT_AVAILABLE capability={capability}")
        return

    # Sort: highest success rate first; break ties by most calls (more data = more confident)
    candidates.sort(key=lambda x: (x[1], x[2]), reverse=True)
    best_name, best_rate, best_calls, best_cfg = candidates[0]

    print(f"BEST_AGENT={best_name}")
    print(f"type={best_cfg.get('type')}")
    print(f"success_rate={best_rate:.2f}")
    print(f"total_calls={best_calls}")
    if "invoke" in best_cfg:
        print(f"invoke={best_cfg['invoke']}")
    if "model" in best_cfg:
        print(f"model={best_cfg['model']}")
    notes = best_cfg.get("notes", "")
    if notes:
        print(f"notes={notes}")

    if len(candidates) > 1:
        print(f"\nAlternatives ({len(candidates)-1}):")
        for name, rate, calls, cfg in candidates[1:]:
            print(f"  {name:<20} rate={rate:.2f}  calls={calls}")


def cmd_record(agent: str, capability: str, task_type: Optional[str], outcome: str) -> None:
    perf = _load_perf()
    key = _agent_perf_key(agent, capability, task_type)
    entry = perf.get(key, {"success_rate": 0.7, "total_calls": 0, "last_updated": ""})

    result = 1.0 if outcome == "ok" else 0.0
    old_rate = entry["success_rate"]
    new_rate = EWMA_ALPHA * result + (1 - EWMA_ALPHA) * old_rate
    entry["success_rate"] = round(new_rate, 4)
    entry["total_calls"] = entry.get("total_calls", 0) + 1
    entry["last_updated"] = datetime.now(timezone.utc).isoformat()
    perf[key] = entry
    _save_perf(perf)

    trend = "+" if result > old_rate else ("-" if result < old_rate else "=")
    print(f"Recorded {agent}/{capability} outcome={outcome} rate={old_rate:.2f}→{new_rate:.2f} {trend}")


def cmd_show_registry() -> None:
    reg = _load_registry()
    print(json.dumps(reg, indent=2, ensure_ascii=False))


# ─── CLI ──────────────────────────────────────────────────────────────────────

def main():
    p = argparse.ArgumentParser(description="doc-pilot agent capability dispatcher")
    sub = p.add_subparsers(dest="cmd")

    ls = sub.add_parser("list-agents")
    ls.add_argument("--capability", default=None)

    ba = sub.add_parser("best-agent")
    ba.add_argument("--capability", required=True)
    ba.add_argument("--task-type", default=None)

    rec = sub.add_parser("record")
    rec.add_argument("--agent",      required=True)
    rec.add_argument("--capability", required=True)
    rec.add_argument("--task-type",  default=None)
    rec.add_argument("--outcome",    required=True, choices=["ok", "fail"])

    sub.add_parser("show-registry")

    args = p.parse_args()
    if args.cmd == "list-agents":
        cmd_list_agents(args.capability)
    elif args.cmd == "best-agent":
        cmd_best_agent(args.capability, args.task_type)
    elif args.cmd == "record":
        cmd_record(args.agent, args.capability, args.task_type, args.outcome)
    elif args.cmd == "show-registry":
        cmd_show_registry()
    else:
        p.print_help()


if __name__ == "__main__":
    main()
