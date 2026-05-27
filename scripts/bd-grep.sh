#!/usr/bin/env bash
# bd-grep.sh — Cloud-friendly read-only search across .beads/issues.jsonl.
#
# Cloud_default sessions read beads as a flat JSONL file (see CLAUDE.md
# "Cloud Sessions"). This wrapper provides the common queries without
# requiring the bd CLI or a running Dolt server.
#
# Usage:
#   bash scripts/bd-grep.sh <keyword>                   # full-text search
#   bash scripts/bd-grep.sh -p <0-4>                    # filter by priority
#   bash scripts/bd-grep.sh -s <open|in_progress|done>  # filter by status
#   bash scripts/bd-grep.sh -t <bug|feature|epic|...>   # filter by issue_type
#   bash scripts/bd-grep.sh <keyword> -p 0 -s open      # combine
#
# Output: one line per matching issue — `<id>  [<status>]  <title>`.
# Sorted by priority asc, then id asc. Limited to 50 hits unless --all.

set -euo pipefail

JSONL="${BD_JSONL:-.beads/issues.jsonl}"
if [[ ! -f "$JSONL" ]]; then
    echo "bd-grep: $JSONL not found (run from repo root)" >&2
    exit 1
fi

keyword=""
priority=""
status=""
itype=""
limit=50

while [[ $# -gt 0 ]]; do
    case "$1" in
        -p) priority="$2"; shift 2 ;;
        -s) status="$2"; shift 2 ;;
        -t) itype="$2"; shift 2 ;;
        --all) limit=0; shift ;;
        -h|--help) sed -n '2,16p' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
        *) if [[ -z "$keyword" ]]; then keyword="$1"; else echo "bd-grep: unexpected arg '$1'" >&2; exit 2; fi; shift ;;
    esac
done

python3 - "$JSONL" "$keyword" "$priority" "$status" "$itype" "$limit" <<'PY'
import json, sys, re
path, keyword, priority, status, itype, limit = sys.argv[1:7]
limit = int(limit)
kw = keyword.lower() if keyword else None
hits = []
with open(path, encoding="utf-8") as f:
    for line in f:
        line = line.strip()
        if not line:
            continue
        try:
            o = json.loads(line)
        except json.JSONDecodeError:
            continue
        if o.get("_type") == "memory":
            continue
        if priority and str(o.get("priority", "")) != priority:
            continue
        if status and o.get("status", "") != status:
            continue
        if itype and o.get("issue_type", "") != itype:
            continue
        if kw:
            blob = " ".join(str(o.get(k, "")) for k in ("id","title","description")).lower()
            if kw not in blob:
                continue
        hits.append(o)
hits.sort(key=lambda o: (o.get("priority", 9), o.get("id", "")))
if limit > 0:
    hits = hits[:limit]
for o in hits:
    iid = o.get("id", "?")
    st = (o.get("status") or "?")[:11]
    title = (o.get("title") or "").replace("\n", " ")
    print(f"{iid:18s}  [{st:11s}]  {title[:90]}")
print(f"-- {len(hits)} hit{'s' if len(hits)!=1 else ''}", file=sys.stderr)
PY
