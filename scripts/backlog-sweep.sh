#!/usr/bin/env bash
set -euo pipefail

# One-time backlog sweep: defer or close stale interject beads.
# Usage: bash scripts/backlog-sweep.sh [--apply] [--stale-days=N]
#
# Dry-run by default. Pass --apply to execute changes.
# Only targets beads with [interject] title prefix.
# Never touches P0/P1 beads.

APPLY=false
STALE_DAYS=30

for arg in "$@"; do
    case "$arg" in
        --apply) APPLY=true ;;
        --stale-days=*) STALE_DAYS="${arg#*=}" ;;
        *) echo "Usage: $0 [--apply] [--stale-days=N]"; exit 1 ;;
    esac
done

export BEADS_DIR="${BEADS_DIR:-$(git rev-parse --show-toplevel 2>/dev/null)/.beads}"

if ! command -v bd >/dev/null 2>&1; then
    echo "Error: bd CLI not found" >&2
    exit 1
fi

echo "Backlog sweep — $(date -Iseconds)"
echo "Mode: $( $APPLY && echo 'APPLY' || echo 'DRY-RUN' )"
echo "Stale threshold: ${STALE_DAYS} days"
echo "---"

now=$(date +%s)
stale_threshold=$((now - STALE_DAYS * 86400))

closed=0
deferred=0
candidates=0
examined=0

# Get all open beads as JSON
beads_json=$(bd list --status=open --json 2>/dev/null) || {
    echo "Error: bd list failed" >&2
    exit 1
}

count=$(echo "$beads_json" | jq 'length')
echo "Total open beads: $count"
echo ""

echo "$beads_json" | jq -c '.[]' | while IFS= read -r bead; do
    title=$(echo "$bead" | jq -r '.title // ""')
    id=$(echo "$bead" | jq -r '.id // ""')
    priority=$(echo "$bead" | jq -r '.priority // 4')
    updated=$(echo "$bead" | jq -r '.updated_at // ""')

    # Only target [interject] beads
    case "$title" in
        "[interject]"*) ;;
        *) continue ;;
    esac

    examined=$((examined + 1))

    # Never touch P0/P1
    if [[ "$priority" -le 1 ]]; then
        continue
    fi

    # Check staleness
    if [[ -n "$updated" ]]; then
        updated_epoch=$(date -d "$updated" +%s 2>/dev/null) || continue
        if [[ "$updated_epoch" -gt "$stale_threshold" ]]; then
            continue
        fi
    fi

    # Check for phase state (has human interacted?)
    phase_result=$(bd state "$id" phase 2>/dev/null) || phase_result=""
    case "$phase_result" in
        ""|*"no "*|*"not set"*) ;;  # No phase — candidate
        *) continue ;;              # Has phase — skip
    esac

    candidates=$((candidates + 1))

    if [[ "$priority" -ge 3 ]]; then
        # P3+ → close
        if $APPLY; then
            bd close "$id" --reason="stale-sweep: ${STALE_DAYS}d inactive, no phase state" 2>/dev/null || true
            echo "CLOSED:   $id (P${priority}) — ${title:0:80}"
        else
            echo "WOULD CLOSE:  $id (P${priority}) — ${title:0:80}"
        fi
        closed=$((closed + 1))
    else
        # P2 → defer
        if $APPLY; then
            bd update "$id" --status=deferred 2>/dev/null || true
            echo "DEFERRED: $id (P${priority}) — ${title:0:80}"
        else
            echo "WOULD DEFER:  $id (P${priority}) — ${title:0:80}"
        fi
        deferred=$((deferred + 1))
    fi
done

echo ""
echo "---"
echo "Examined: ${examined} interject beads"
echo "Candidates: ${candidates} (stale, no phase state)"
echo "  Close: ${closed}"
echo "  Defer: ${deferred}"
if ! $APPLY; then
    echo ""
    echo "(dry-run — pass --apply to execute)"
fi
