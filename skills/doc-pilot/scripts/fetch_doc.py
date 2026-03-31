#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
doc-pilot fetch_doc.py
Document acquisition helper — finds and retrieves documents from various sources.

This script is called by doc-pilot to resolve document sources before navigation.
It does NOT do HTTP fetching itself (that's done by Claude's WebFetch tool).
Instead, it helps determine the best acquisition strategy and prepares search queries.

Usage:
  python fetch_doc.py strategy --hint "<user description>"
  python fetch_doc.py search-query --brand "<brand>" --model "<model>" --doc-type "<type>"
  python fetch_doc.py cache-check --key "<cache_key>"
  python fetch_doc.py cache-save  --key "<cache_key>" --path "<md_file_path>"
"""

import sys
import json
import hashlib
import argparse
import re
from pathlib import Path
from typing import Optional

MEMORY_DIR = Path(__file__).parent.parent / "memory"
DOC_CACHE_DIR = MEMORY_DIR / "doc_cache"
DOC_CACHE_DIR.mkdir(parents=True, exist_ok=True)

# CognoLiving's existing perfect_md library (3478 pre-processed manuals)
COGNO_MD_DIR = Path(r"C:\AI\CognoLiving 2.0\perfect_md")


# ─── Strategy Determination ───────────────────────────────────────────────────

def cmd_strategy(args):
    """Determine the best acquisition strategy based on user's description."""
    hint = args.hint.lower()

    strategies = []

    # 1. Check if it's a local file path
    if re.search(r'[a-zA-Z]:\\|\.pdf$|\.md$|\.txt$|\/\w+\.\w+', args.hint):
        strategies.append({
            "type": "local_file",
            "priority": 1,
            "action": "Read the file directly. If it's a PDF, run doc-pilot-pdf extract first.",
            "note": "Detected file path pattern"
        })

    # 2. Check CognoLiving pre-processed library
    if COGNO_MD_DIR.exists():
        brand_model_match = re.search(r'([a-zA-Z]+)\s+([A-Z0-9\-]+)', args.hint)
        if brand_model_match:
            brand = brand_model_match.group(1)
            model = brand_model_match.group(2)
            candidates = list(COGNO_MD_DIR.glob(f"*{brand}*{model}*.md")) + \
                         list(COGNO_MD_DIR.glob(f"*{model}*.md"))
            if candidates:
                strategies.append({
                    "type": "cogno_library",
                    "priority": 1,
                    "file": str(candidates[0]),
                    "action": f"Read {candidates[0]} — pre-processed high-quality Markdown available",
                    "note": f"Found {len(candidates)} match(es) in CognoLiving library"
                })

    # 3. URL detected
    if re.search(r'https?://', args.hint):
        strategies.append({
            "type": "url",
            "priority": 2,
            "action": "WebFetch the URL directly",
        })

    # 4. Default: web search
    strategies.append({
        "type": "web_search",
        "priority": 3,
        "action": "Use WebSearch to find the official manual or documentation",
        "suggested_query": _build_search_query(args.hint),
    })

    # Sort by priority
    strategies.sort(key=lambda s: s["priority"])
    print(json.dumps({"strategies": strategies}, ensure_ascii=False, indent=2))


def _build_search_query(hint: str) -> str:
    # Extract brand + model if present
    m = re.search(r'([A-Za-z]+(?:\s+[A-Z][a-z0-9]+)?)\s+([A-Z][A-Z0-9\-]{2,})', hint)
    if m:
        return f"{m.group(1)} {m.group(2)} user manual PDF filetype:pdf"
    return f"{hint} user manual PDF"


# ─── Search Query Builder ─────────────────────────────────────────────────────

def cmd_search_query(args):
    """Build an optimized search query for finding a product manual."""
    parts = []
    if args.brand:
        parts.append(args.brand)
    if args.model:
        parts.append(args.model)
    doc_type = args.doc_type or "user manual"
    parts.append(doc_type)
    parts.append("PDF")

    queries = [
        " ".join(parts),
        f'"{args.brand} {args.model}" manual site:manualslib.com' if args.brand and args.model else "",
        f"{args.brand} {args.model} 使用说明书" if args.brand else "",
    ]
    queries = [q for q in queries if q.strip()]

    print(json.dumps({"queries": queries}, ensure_ascii=False, indent=2))


# ─── Document Cache ────────────────────────────────────────────────────────────

def _cache_key_hash(key: str) -> str:
    return hashlib.md5(key.lower().strip().encode()).hexdigest()[:12]


def cmd_cache_check(args):
    """Check if a document is already cached locally."""
    h = _cache_key_hash(args.key)
    meta_path = DOC_CACHE_DIR / f"{h}_meta.json"
    md_path = DOC_CACHE_DIR / f"{h}.md"

    if meta_path.exists() and md_path.exists():
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        print(json.dumps({
            "found": True,
            "cache_path": str(md_path),
            "cached_at": meta.get("cached_at"),
            "source": meta.get("source"),
            "size_chars": md_path.stat().st_size,
        }, ensure_ascii=False))
    else:
        print(json.dumps({"found": False}))


def cmd_cache_save(args):
    """Save a document to local cache."""
    from datetime import datetime, timezone
    h = _cache_key_hash(args.key)
    src_path = Path(args.path)

    if not src_path.exists():
        print(f"ERROR: Source file not found: {args.path}", file=sys.stderr)
        sys.exit(1)

    md_path = DOC_CACHE_DIR / f"{h}.md"
    meta_path = DOC_CACHE_DIR / f"{h}_meta.json"

    # Copy content
    md_path.write_text(src_path.read_text(encoding="utf-8"), encoding="utf-8")

    # Save metadata
    meta = {
        "key": args.key,
        "hash": h,
        "source": args.path,
        "cached_at": datetime.now(timezone.utc).isoformat(),
    }
    meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")

    print(json.dumps({
        "saved": True,
        "cache_path": str(md_path),
        "key_hash": h,
    }, ensure_ascii=False))


# ─── CLI ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="doc-pilot document acquisition helper")
    sub = parser.add_subparsers(dest="command")

    p = sub.add_parser("strategy")
    p.add_argument("--hint", required=True, help="User's description of document source")

    p = sub.add_parser("search-query")
    p.add_argument("--brand")
    p.add_argument("--model")
    p.add_argument("--doc-type", default="user manual")

    p = sub.add_parser("cache-check")
    p.add_argument("--key", required=True)

    p = sub.add_parser("cache-save")
    p.add_argument("--key", required=True)
    p.add_argument("--path", required=True)

    args = parser.parse_args()
    dispatch = {
        "strategy": cmd_strategy,
        "search-query": cmd_search_query,
        "cache-check": cmd_cache_check,
        "cache-save": cmd_cache_save,
    }
    if args.command not in dispatch:
        parser.print_help()
        sys.exit(1)
    dispatch[args.command](args)


if __name__ == "__main__":
    main()
