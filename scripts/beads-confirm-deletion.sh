#!/usr/bin/env bash
# Record that a bead was deleted on purpose, so the other machine deletes it too.
#
# This is the answer to the auto-export's question. When a bead exists in
# .beads/issues.jsonl but not in Dolt, two situations look identical:
#
#   another machine's work, pulled but never imported  -> import it
#   deleted here on purpose                            -> confirm it
#
# Answering the second with a bare `bd export` drops the row from the file and
# loses the *intent*. The other machine then sees only an absence, which is not
# a deletion signal (a filtered export, or work not yet exported, looks the
# same), keeps its copy, and writes the bead back on its next export. The
# deletion silently undoes itself.
#
# So the intent is written down, in an append-only git-tracked ledger, and
# committed in the same commit as the export that acts on it. Split across two
# commits, a machine can pull the export without the ledger and resurrect the
# bead in the window between.
#
# Usage:
#   scripts/beads-confirm-deletion.sh <id> [<id>...]        # already deleted here
#   scripts/beads-confirm-deletion.sh --delete-local <id>   # delete here too
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
LEDGER="$ROOT/.beads/deletions.jsonl"
DELETE_LOCAL=0
NOTE=""
IDS=()

while [ $# -gt 0 ]; do
  case "$1" in
    --delete-local) DELETE_LOCAL=1 ;;
    --note) NOTE="${2:-}"; shift ;;
    -h|--help) sed -n '2,25p' "$0"; exit 0 ;;
    -*) echo "unknown flag: $1" >&2; exit 2 ;;
    *) IDS+=("$1") ;;
  esac
  shift
done

[ ${#IDS[@]} -gt 0 ] || { echo "usage: $(basename "$0") [--delete-local] [--note TEXT] <id>..." >&2; exit 2; }
command -v bd >/dev/null 2>&1 || { echo "bd not on PATH" >&2; exit 1; }

cd "$ROOT"

for id in "${IDS[@]}"; do
  if bd show "$id" >/dev/null 2>&1; then
    if [ "$DELETE_LOCAL" -eq 1 ]; then
      bd delete "$id" --force >/dev/null
      echo "deleted locally: $id"
    else
      # Recording a deletion that has not happened would ship an instruction to
      # destroy a bead that is still live here — the ledger would be a lie the
      # other machine acts on.
      echo "refusing: $id still exists in this database." >&2
      echo "          Delete it first, or pass --delete-local to do both." >&2
      exit 1
    fi
  fi
done

ts="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
actor="$(git config user.name 2>/dev/null || echo "${USER:-unknown}")"
machine="$(hostname -s 2>/dev/null || echo unknown)"

for id in "${IDS[@]}"; do
  python3 - "$LEDGER" "$id" "$ts" "$actor" "$machine" "$NOTE" <<'PY'
import json, sys, pathlib
ledger, issue_id, ts, actor, machine, note = sys.argv[1:7]
path = pathlib.Path(ledger)
path.parent.mkdir(parents=True, exist_ok=True)
row = {"id": issue_id, "deleted_at": ts, "actor": actor, "machine": machine}
if note:
    row["note"] = note
with path.open("a", encoding="utf-8") as fh:
    fh.write(json.dumps(row, sort_keys=True) + "\n")
PY
  echo "recorded deletion: $id"
done

bd export --output "$ROOT/.beads/issues.jsonl"

# One commit, pathspec form: the export and the intent that authorises it
# travel together or not at all.
git add -- .beads/deletions.jsonl >/dev/null 2>&1 || true
if git commit -q -m "beads: confirm deletion of ${IDS[*]}" \
      -- .beads/issues.jsonl .beads/deletions.jsonl 2>/dev/null; then
  echo "committed $(git rev-parse --short HEAD) — push to propagate the deletion"
else
  echo "nothing to commit; the export already matched HEAD" >&2
fi
