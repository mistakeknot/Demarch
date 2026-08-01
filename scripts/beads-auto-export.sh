#!/usr/bin/env bash
# Export Dolt → .beads/issues.jsonl and commit it, when and only when that is
# both needed and safe. Invoked from the post-commit hook.
#
# Why a dedicated commit rather than folding the export into the commit that
# triggered it: staging issues.jsonl from pre-commit widens the commit. With
# `git commit -- <paths>` the hook runs against a temporary index, so a
# `git add` there puts the export into a commit that explicitly named other
# paths, and leaves the real index dirty afterward. Measured, not assumed.
# A separate pathspec commit keeps every other commit exactly as authored.
#
# Fail-open throughout. This runs after the user's commit already succeeded;
# nothing here may fail it, and nothing here may block. Diagnostics go to
# .beads/auto-export.log.
set -uo pipefail

ROOT="$(git rev-parse --show-toplevel 2>/dev/null)" || exit 0
cd "$ROOT" || exit 0

LOG="$ROOT/.beads/auto-export.log"
log() { printf '%s %s\n' "$(date -u +%FT%TZ)" "$*" >>"$LOG" 2>/dev/null || true; }

# ─── Guards ───────────────────────────────────────────────────────────

# Re-entrancy: the commit this hook makes will itself fire post-commit. Without
# this the hook recurses until something breaks.
if git diff-tree --no-commit-id --name-only -r HEAD 2>/dev/null \
     | grep -qx '.beads/issues.jsonl'; then
  exit 0
fi

# Never create a commit while git is mid-sequence. post-commit fires during
# cherry-pick and --amend, and inserting a commit there rewrites what the
# operation is doing underneath it.
GIT_DIR_PATH="$(git rev-parse --git-dir 2>/dev/null)" || exit 0
for marker in rebase-merge rebase-apply MERGE_HEAD CHERRY_PICK_HEAD REVERT_HEAD BISECT_LOG; do
  if [ -e "$GIT_DIR_PATH/$marker" ]; then
    log "skip: $marker present"
    exit 0
  fi
done

# An explicit opt-out, and the escape hatch for scripted flows that manage the
# export themselves.
if [ "${BEADS_NO_AUTO_EXPORT:-}" = "1" ]; then
  log "skip: BEADS_NO_AUTO_EXPORT=1"
  exit 0
fi

command -v bd >/dev/null 2>&1 || exit 0
[ -f "$ROOT/scripts/check_beads_jsonl_dolt_sync.py" ] || exit 0

# ─── Decide ───────────────────────────────────────────────────────────

# Ask the same checker that guards commits, so the trigger and the guard can
# never disagree about what "in sync" means. ~0.3s; a full export is ~3s, which
# is why this is a probe and not an unconditional export.
probe_err="$(mktemp "${TMPDIR:-/tmp}/sylveste-probe-err.XXXXXX")" || exit 0
probe="$(python3 "$ROOT/scripts/check_beads_jsonl_dolt_sync.py" --json --strict-extra 2>"$probe_err")"
probe_rc=$?
probe_msg="$(head -1 "$probe_err" 2>/dev/null)"
rm -f "$probe_err"

# A failing probe means bead state stops being exported. Say so out loud.
#
# This used to be `2>/dev/null || true` followed by a silent `exit 0` on empty
# output, which folded two very different situations into one: bd genuinely
# absent (a cloud session — correctly silent, nothing to export from), and the
# probe running and failing (bd broken, schema mismatch, Dolt server down).
# The second is the same shape as the bug this whole mechanism replaced: the
# export quietly stops while every commit still succeeds and nothing says why.
# Observed for real when a schema migration left `bd sql` unable to build a
# view, so the probe errored on every commit and the log was the only trace.
#
# The test is "did it produce a verdict", NOT "did it exit 0". This checker is
# also the pre-commit guard, so it exits non-zero precisely when it finds drift
# — which is the case where an export IS wanted. Keying the failure branch on
# the exit code disables the export exactly when it is needed, which is what the
# first version of this check did until the ordering suite caught it.
#
# bd's presence was checked above, so empty output here is a real failure rather
# than an absent tool.
if [ -z "$probe" ]; then
  log "PROBE FAILED rc=$probe_rc: $probe_msg"
  echo "beads: auto-export probe failed — bead state is NOT being exported." >&2
  [ -n "$probe_msg" ] && echo "       $probe_msg" >&2
  echo "       Until this is fixed, export by hand before pushing:" >&2
  echo "         bd export --output .beads/issues.jsonl" >&2
  exit 0
fi

read -r export_needed safe_to_export missing_count <<EOF
$(printf '%s' "$probe" | python3 -c '
import json, sys
try:
    d = json.load(sys.stdin)
except Exception:
    print("false false 0"); raise SystemExit
print(str(d.get("export_needed", False)).lower(),
      str(d.get("safe_to_export", False)).lower(),
      len(d.get("missing_in_dolt", [])))
')
EOF

if [ "$safe_to_export" != "true" ]; then
  # JSONL holds issues Dolt has never seen — typically another machine's work
  # that was pulled but never imported. Exporting would overwrite them out of
  # existence. Say so loudly and change nothing.
  #
  # Two situations produce this state and they need opposite responses, which
  # is exactly why it is not resolved automatically:
  #   - another machine's issues were pulled but never imported -> import them
  #   - an issue was deleted here                               -> record the
  #     deletion, so the other machine performs it too
  # Nothing here can tell those apart, so it asks rather than guesses.
  #
  # The second answer used to be a bare `bd export`. That drops the row and
  # loses the intent: the other machine sees only an absence, which is not a
  # deletion signal, keeps its copy, and writes the bead back on its next
  # export. beads-confirm-deletion.sh writes the intent down instead.
  log "REFUSED: $missing_count issue(s) exist only in the JSONL; exporting would delete them"
  echo "beads: NOT auto-exporting — $missing_count issue(s) exist only in .beads/issues.jsonl," >&2
  echo "       so exporting now would delete them. Which is it?" >&2
  echo "         another machine's work  ->  bd import .beads/issues.jsonl" >&2
  echo "         deleted here on purpose ->  scripts/beads-confirm-deletion.sh <id>..." >&2
  echo "       See the list with: python3 scripts/check_beads_jsonl_dolt_sync.py" >&2
  exit 0
fi

# ─── Export and commit ────────────────────────────────────────────────

if [ "$export_needed" = "true" ]; then
  if ! bd export --output "$ROOT/.beads/issues.jsonl" >>"$LOG" 2>&1; then
    log "export failed; leaving the working tree alone"
    echo "beads: auto-export failed; run 'bd export --output .beads/issues.jsonl' by hand" >&2
    exit 0
  fi
fi

# Commit against HEAD, not against the index, and do it even when no export was
# needed.
#
# The probe compares the working-tree file to Dolt. That says nothing about what
# is committed — and only the committed copy is pushed. A hand-run `bd export`
# that was never committed leaves the file matching Dolt perfectly while HEAD
# still holds the stale version, so a probe-only check concludes "in sync" and
# the change sits uncommitted indefinitely. Observed exactly that, once.
if git diff --quiet HEAD -- .beads/issues.jsonl 2>/dev/null; then
  log "export matches HEAD; no commit"
  exit 0
fi

# Pathspec form: commits this file only, even when other changes are staged.
if git commit -q -m "beads: sync export (automated)" -- .beads/issues.jsonl >>"$LOG" 2>&1; then
  log "committed export $(git rev-parse --short HEAD)"
else
  log "commit failed; export left in the working tree for the next commit"
  echo "beads: export refreshed but could not be committed; it is staged in your working tree" >&2
fi
exit 0
