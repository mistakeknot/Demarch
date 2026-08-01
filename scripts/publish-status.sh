#!/usr/bin/env bash
# `ic publish status` plus the content verdict it omits.
#
# `ic publish status` compares plugin.json / marketplace / installed VERSION
# NUMBERS. When they agree it prints a clean table — and says nothing about
# whether the published artifact contains the code that is committed.
#
# clavain read that table as fully in sync (0.6.293 everywhere) for three days
# while a committed hook fix had never shipped: the fix landed after the bump
# and nothing touched the version file again. The version table was accurate and
# useless. See Sylveste-egrc / Sylveste-gyrd.
#
# This wrapper exists so nobody sees the reassuring half on its own.
#
# Usage: publish-status.sh [plugin-dir]     (defaults to $PWD)
set -uo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PLUGIN_DIR="${1:-$PWD}"

name=""
if [[ -f "$PLUGIN_DIR/.claude-plugin/plugin.json" ]] && command -v jq >/dev/null 2>&1; then
    name="$(jq -r '.name // empty' "$PLUGIN_DIR/.claude-plugin/plugin.json" 2>/dev/null)"
fi

echo "── version agreement ──────────────────────────────────────────"
if command -v ic >/dev/null 2>&1; then
    (cd "$PLUGIN_DIR" && ic publish status 2>&1) || true
else
    echo "  ic not on PATH — skipping version table"
fi

echo
echo "── content verdict ────────────────────────────────────────────"
# Names come from a manifest on disk; pass as a separate argv entry, never spliced.
if [[ -n "$name" ]]; then
    python3 "$REPO_ROOT/scripts/check-publish-drift.py" --plugin "$name"
    rc=$?
else
    python3 "$REPO_ROOT/scripts/check-publish-drift.py"
    rc=$?
fi

if [[ "$rc" -eq 0 ]]; then
    echo
    echo "  ✓ published artifact contains the committed source"
fi
exit "$rc"
