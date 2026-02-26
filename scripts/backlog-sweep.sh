#!/usr/bin/env bash
# One-time backlog sweep: defer/close stale beads to reduce open count.
# Usage: bash scripts/backlog-sweep.sh [--apply]
#
# Default: dry-run mode (prints what would change, no mutations).
# Pass --apply to execute the changes.
set -euo pipefail

APPLY=false
STALE_DAYS=${STALE_DAYS:-30}
INTERJECT_CLOSE_DAYS=${INTERJECT_CLOSE_DAYS:-14}

if [[ "${1:-}" == "--apply" ]]; then
    APPLY=true
fi

# Ensure bd is available
if ! command -v bd &>/dev/null; then
    echo "ERROR: bd CLI not found" >&2
    exit 1
fi

echo "Backlog sweep — stale_days=$STALE_DAYS, interject_close_days=$INTERJECT_CLOSE_DAYS"
echo "Mode: $([ "$APPLY" = true ] && echo "APPLY" || echo "DRY-RUN")"
echo "---"

defer_count=0
close_count=0
skip_count=0
protect_count=0

# Get all open beads as JSON
beads_json=$(BEADS_DIR="${BEADS_DIR:-}" bd list --status=open --json 2>/dev/null) || {
    echo "ERROR: failed to list beads" >&2
    exit 1
}

bead_count=$(echo "$beads_json" | jq 'length')
echo "Open beads: $bead_count"
echo ""

now_epoch=$(date +%s)
stale_epoch=$((now_epoch - STALE_DAYS * 86400))
interject_epoch=$((now_epoch - INTERJECT_CLOSE_DAYS * 86400))

while IFS= read -r bead; do
    id=$(echo "$bead" | jq -r '.id')
    title=$(echo "$bead" | jq -r '.title')
    priority=$(echo "$bead" | jq -r '.priority // 4 | floor')
    updated=$(echo "$bead" | jq -r '.updated_at // .created_at // ""')

    # Priority guard FIRST — never sweep P0 or P1
    if [[ "$priority" -le 1 ]]; then
        protect_count=$((protect_count + 1))
        continue
    fi

    # Parse updated_at to epoch (handle ISO format)
    if [[ -z "$updated" ]]; then
        continue
    fi
    updated_epoch=$(date -d "$updated" +%s 2>/dev/null) || continue

    # Interject-originated beads with no activity: close after INTERJECT_CLOSE_DAYS
    if [[ "$title" == "[interject]"* ]] && [[ "$updated_epoch" -lt "$interject_epoch" ]]; then
        if [[ "$APPLY" == true ]]; then
            bd close "$id" --reason="stale-sweep: interject item, no activity for ${INTERJECT_CLOSE_DAYS}d" 2>/dev/null && \
                echo "CLOSED: $id — $title" || \
                echo "FAILED to close: $id"
        else
            echo "WOULD CLOSE: $id — $title (interject, updated $(date -d "@$updated_epoch" +%Y-%m-%d))"
        fi
        close_count=$((close_count + 1))
        continue
    fi

    # General stale beads (P2+): defer after STALE_DAYS
    if [[ "$updated_epoch" -lt "$stale_epoch" ]]; then
        if [[ "$APPLY" == true ]]; then
            bd update "$id" --status=deferred 2>/dev/null && \
                echo "DEFERRED: $id — $title" || \
                echo "FAILED to defer: $id"
        else
            echo "WOULD DEFER: $id — $title (updated $(date -d "@$updated_epoch" +%Y-%m-%d))"
        fi
        defer_count=$((defer_count + 1))
        continue
    fi

    skip_count=$((skip_count + 1))
done < <(echo "$beads_json" | jq -c '.[]')

echo ""
echo "Summary:"
echo "  Protected (P0/P1): $protect_count"
echo "  Would close (interject stale): $close_count"
echo "  Would defer (general stale): $defer_count"
echo "  Kept (recent enough): $skip_count"
