#!/usr/bin/env bash
# bd-show.sh — Cloud-friendly read-only `bd show` against .beads/issues.jsonl.
#
# Prints the full record for a single bead by id, formatted readably.
# Companion to scripts/bd-grep.sh — see CLAUDE.md "Cloud Sessions".
#
# Usage:
#   bash scripts/bd-show.sh <id>           # human-readable
#   bash scripts/bd-show.sh <id> --json    # raw JSON

set -euo pipefail

JSONL="${BD_JSONL:-.beads/issues.jsonl}"
if [[ ! -f "$JSONL" ]]; then
    echo "bd-show: $JSONL not found (run from repo root)" >&2
    exit 1
fi

if [[ $# -lt 1 ]]; then
    echo "Usage: bash scripts/bd-show.sh <id> [--json]" >&2
    exit 2
fi

iid="$1"
fmt="${2:-text}"

python3 - "$JSONL" "$iid" "$fmt" <<'PY'
import json, sys
path, iid, fmt = sys.argv[1:4]
match = None
with open(path, encoding="utf-8") as f:
    for line in f:
        line = line.strip()
        if not line:
            continue
        try:
            o = json.loads(line)
        except json.JSONDecodeError:
            continue
        if o.get("id") == iid:
            match = o
            break
if match is None:
    print(f"bd-show: no issue with id {iid!r}", file=sys.stderr)
    sys.exit(1)
if fmt == "--json":
    print(json.dumps(match, indent=2))
    sys.exit(0)
print(f"id:          {match.get('id')}")
print(f"title:       {match.get('title','')}")
print(f"status:      {match.get('status','')}")
print(f"priority:    P{match.get('priority','?')}")
print(f"issue_type:  {match.get('issue_type','')}")
parent = match.get("parent_id") or match.get("parent")
if parent:
    print(f"parent:      {parent}")
labels = match.get("labels") or []
if labels:
    print(f"labels:      {', '.join(labels)}")
desc = match.get("description") or ""
if desc:
    print("---")
    print(desc.rstrip())
ac = match.get("acceptance_criteria") or ""
if ac:
    print("--- acceptance_criteria ---")
    print(ac.rstrip())
notes = match.get("notes") or ""
if notes:
    print("--- notes ---")
    print(notes.rstrip())
PY
