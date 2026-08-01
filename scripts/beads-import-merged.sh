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
# It helps a lot, but not always, and the exception is worth knowing: bd stamps
# the IMPORTING actor onto dependency records, so the same bead serializes
# differently on each machine ("Claude Code" on zklw, "mistakeknot" here).
# ~3,300 beads carry dependencies, so every export that alternates machines
# rewrites them all and this filter degrades to nearly a full import. Measured
# 3 rows on a same-machine merge, 3,313 on a cross-machine one. Sorting the
# lines does not help — the difference is content, not order. Tracked as the
# actor-churn bead; fixing it there fixes it here.
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

# Bounded, because an unbounded import can hang the pull outright.
#
# Observed on zklw: `bd import` blocked in futex_wait with an open socket to its
# own Dolt server, 5 seconds of CPU in 5 minutes and not growing, while other bd
# processes held the server. Twice. Without a bound, `git pull` never returns
# and the deletion pass after it never runs — the pull has to be killed by hand,
# which is what happened.
#
# Timing out is not silent. The rows are still in the file; what is lost is only
# that they have not been loaded yet, and saying so is what lets someone fix it.
_bd_import_timeout="${BEADS_IMPORT_TIMEOUT:-120}"
if command -v timeout >/dev/null 2>&1; then
  _bd_runner="timeout $_bd_import_timeout"
elif command -v gtimeout >/dev/null 2>&1; then
  _bd_runner="gtimeout $_bd_import_timeout"
else
  _bd_runner=""
fi

# shellcheck disable=SC2086
$_bd_runner bd import "$TMP"
rc=$?

if [ $rc -eq 124 ]; then
  rows="$(grep -c . "$TMP" 2>/dev/null || echo '?')"
  echo "beads: import timed out after ${_bd_import_timeout}s — $rows row(s) were NOT loaded." >&2
  echo "       Your git pull finished; the local database is behind the file." >&2
  echo "       Retry with:  bd import .beads/issues.jsonl" >&2
  echo "       If it hangs again, another bd process is likely holding the Dolt server." >&2
fi
exit 0
