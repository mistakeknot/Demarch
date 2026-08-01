#!/usr/bin/env bash
# Import the issue rows a merge actually brought in, rather than all 3,810.
#
# `bd import` on the whole file takes ~49s here. The script this replaced
# avoided that by filtering to new-or-newer rows before importing — but it
# filtered by reimplementing bd's staleness rule, which is precisely the
# duplication that was worth retiring.
#
# So the filter is cheap and dumb instead: git already knows which lines this
# merge changed, and every issue is exactly one line. We hand bd the changed
# rows and bd still decides, row by row, whether each one may be applied. The
# guarantee stays bd's; only the size of the batch is ours.
#
# When it cannot tell what changed, it imports everything. Slow beats wrong:
# an import that silently skips a machine's work is the failure this whole
# path exists to prevent.
#
# Usage: beads-import-merged.sh [<before-ref>]      (default: ORIG_HEAD)
set -uo pipefail

ROOT="$(git rev-parse --show-toplevel 2>/dev/null)" || exit 0
JSONL="$ROOT/.beads/issues.jsonl"
[ -f "$JSONL" ] || exit 0
command -v bd >/dev/null 2>&1 || exit 0      # cloud session; nothing to import into

BEFORE="${1:-ORIG_HEAD}"

if ! git -C "$ROOT" rev-parse --verify --quiet "$BEFORE" >/dev/null 2>&1; then
  exec bd import "$JSONL"
fi

if git -C "$ROOT" diff --quiet "$BEFORE" HEAD -- .beads/issues.jsonl 2>/dev/null; then
  exit 0                                     # the merge did not touch bead state
fi

TMP="$(mktemp "${TMPDIR:-/tmp}/beads-merged.XXXXXX.jsonl")" || exec bd import "$JSONL"
trap 'rm -f "$TMP"' EXIT

# '^+{' matches added JSON rows and cannot match the '+++ b/...' file header.
# A modified row shows up as a '-' for the old text and a '+' for the new, so
# taking the '+' side gets updates as well as creations. Rows that only
# disappear are deletions, which are not an import's business — deletions
# travel through .beads/deletions.jsonl.
git -C "$ROOT" diff "$BEFORE" HEAD -- .beads/issues.jsonl \
  | grep '^+{' | cut -c2- > "$TMP" || true

if [ ! -s "$TMP" ]; then
  exit 0
fi

bd import "$TMP"
