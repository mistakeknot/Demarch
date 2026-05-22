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
#   bash scripts/bd-grep.sh -s <open|in_progress|done|deferred|wont_fix|closed>
#   bash scripts/bd-grep.sh -t <bug|feature|epic|...>   # case-insensitive
#   bash scripts/bd-grep.sh <keyword> -p 0 -s open      # combine
#   bash scripts/bd-grep.sh <keyword> --title-only      # tighter haystack
#
# Output: one line per matching issue — `<id>  [<status>]  <title>`.
# Sorted by priority asc, then id asc (case-folded). Limited to 50 hits
# unless --all. Truncation is announced on stdout when it happens.

set -euo pipefail

JSONL="${BD_JSONL:-.beads/issues.jsonl}"
if [[ ! -f "$JSONL" ]]; then
    echo "bd-grep: $JSONL not found (run from repo root)" >&2
    exit 1
fi

VALID_STATUSES="open in_progress done deferred wont_fix closed blocked"

usage() {
    cat <<'USAGE'
bd-grep.sh — read-only search across .beads/issues.jsonl

Usage:
  bash scripts/bd-grep.sh <keyword>                # full-text search
  bash scripts/bd-grep.sh -p <0-4>                 # filter by priority
  bash scripts/bd-grep.sh -s <status>              # filter by status
  bash scripts/bd-grep.sh -t <issue_type>          # case-insensitive
  bash scripts/bd-grep.sh <kw> -p 0 -s open        # combine
  bash scripts/bd-grep.sh <kw> --title-only        # tighter haystack
  bash scripts/bd-grep.sh <kw> --all               # no 50-hit cap

Valid status values: open in_progress done deferred wont_fix closed blocked
Valid priority values: 0 1 2 3 4 (P0=highest, P4=lowest)

Output: <id>  [<status>]  <title>
Sorted by priority asc, then id asc (case-folded). Limited to 50 hits
unless --all; truncation is announced on stdout.
USAGE
}

keyword=""
priority=""
status=""
itype=""
limit=50
title_only=0

while [[ $# -gt 0 ]]; do
    case "$1" in
        -p) priority="$2"; shift 2 ;;
        -s) status="$2"; shift 2 ;;
        -t) itype="$2"; shift 2 ;;
        --all) limit=0; shift ;;
        --title-only) title_only=1; shift ;;
        -h|--help) usage; exit 0 ;;
        *) if [[ -z "$keyword" ]]; then keyword="$1"; else echo "bd-grep: unexpected arg '$1'" >&2; exit 2; fi; shift ;;
    esac
done

# Validate priority — silent "0 hits" on an invalid value is the wrong UX.
if [[ -n "$priority" && ! "$priority" =~ ^[0-4]$ ]]; then
    echo "bd-grep: priority must be 0-4 (got '$priority')" >&2
    exit 2
fi

# Validate status — accept any of the known values.
if [[ -n "$status" ]]; then
    matched=0
    for s in $VALID_STATUSES; do
        [[ "$status" == "$s" ]] && { matched=1; break; }
    done
    if [[ "$matched" -eq 0 ]]; then
        echo "bd-grep: status must be one of: $VALID_STATUSES (got '$status')" >&2
        exit 2
    fi
fi

python3 - "$JSONL" "$keyword" "$priority" "$status" "$itype" "$limit" "$title_only" <<'PY'
import json, sys
path, keyword, priority, status, itype, limit, title_only = sys.argv[1:8]
limit = int(limit)
title_only = title_only == "1"
kw = keyword.lower() if keyword else None
itype_lc = itype.lower() if itype else None
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
        # Skip session-memory rows emitted by bd's auto-memory feature
        # (not real issues; they show up with _type=memory).
        if o.get("_type") == "memory":
            continue
        if priority and str(o.get("priority", "")) != priority:
            continue
        if status and o.get("status", "") != status:
            continue
        if itype_lc and (o.get("issue_type", "") or "").lower() != itype_lc:
            continue
        if kw:
            if title_only:
                blob = str(o.get("title", "")).lower()
            else:
                blob = " ".join(str(o.get(k, "")) for k in ("id","title","description")).lower()
            if kw not in blob:
                continue
        hits.append(o)
# Case-fold the id sort key so Sylveste-906 doesn't lead sylveste-22oi.
hits.sort(key=lambda o: (o.get("priority", 9), (o.get("id") or "").lower()))
total = len(hits)
if limit > 0 and total > limit:
    hits = hits[:limit]
    truncated = True
else:
    truncated = False
for o in hits:
    iid = o.get("id", "?")
    st = (o.get("status") or "?")[:11]
    title = (o.get("title") or "").replace("\n", " ")
    print(f"{iid:18s}  [{st:11s}]  {title[:90]}")
if truncated:
    # Stdout-visible so it isn't lost in pipelines.
    print(f"-- showing {limit}/{total} hits — pass --all to see the rest")
print(f"-- {total} hit{'s' if total!=1 else ''}", file=sys.stderr)
PY
