#!/usr/bin/env bash
# doc-pilot — OpenClaw adapter installer
# Usage: bash adapters/claw/install.sh
set -e

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
CLAW_SKILLS="${HOME}/.openclaw/skills"

echo "📦 Installing doc-pilot skills for OpenClaw..."
echo "   Source : $REPO_DIR"
echo "   Target : $CLAW_SKILLS"
echo ""

mkdir -p "$CLAW_SKILLS"

# ── Symlink core scripts (shared with Claude Code adapter) ──────────────────
for skill in doc-pilot doc-pilot-pdf doc-pilot-analyst; do
    TARGET="$CLAW_SKILLS/$skill"
    if [ -L "$TARGET" ] || [ -d "$TARGET" ]; then
        echo "  ↩  $skill already exists — skipping (remove manually to reinstall)"
        continue
    fi
    mkdir -p "$TARGET"

    # Link scripts directory (shared engine — same Python, works everywhere)
    ln -s "$REPO_DIR/skills/$skill/scripts" "$TARGET/scripts"

    # Use Claw-specific SKILL.md (OpenClaw metadata + ~/.openclaw/ paths)
    cp "$REPO_DIR/adapters/claw/skills/$skill/SKILL.md" "$TARGET/SKILL.md"

    echo "  ✓  $skill"
done

# ── Memory directory ────────────────────────────────────────────────────────
mkdir -p "$CLAW_SKILLS/doc-pilot/memory/tasks"
mkdir -p "$CLAW_SKILLS/doc-pilot/memory/templates"
echo "  ✓  memory/ directories created"

# ── Dependency check ────────────────────────────────────────────────────────
echo ""
echo "Checking dependencies..."
if python3 -c "import fitz" 2>/dev/null; then
    echo "  ✓  PyMuPDF (fitz) available"
else
    echo "  ✗  PyMuPDF not found — installing..."
    pip3 install pymupdf
fi

echo ""
echo "✅ Done. Restart OpenClaw and try:"
echo '   "Help me fix my Bosch dishwasher showing E9"'
echo '   "Walk me through this PDF: /path/to/manual.pdf"'
