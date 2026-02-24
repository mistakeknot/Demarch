#!/usr/bin/env bash
# audit-roadmap-beads.sh — Check consistency between roadmap and beads database.
# Usage: audit-roadmap-beads.sh [--json] [roadmap-path]
# Default roadmap: docs/demarch-roadmap.md (relative to repo root)

set -euo pipefail

# Parse flags
JSON_MODE=false
ROADMAP=""
for arg in "$@"; do
    case "$arg" in
        --json) JSON_MODE=true ;;
        *) ROADMAP="$arg" ;;
    esac
done

# Find repo root
REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
ROADMAP="${ROADMAP:-$REPO_ROOT/docs/demarch-roadmap.md}"

if [[ ! -f "$ROADMAP" ]]; then
    if $JSON_MODE; then
        echo '{"error":"roadmap not found","path":"'"$ROADMAP"'"}'
    else
        echo "ERROR: Roadmap not found: $ROADMAP"
    fi
    exit 1
fi

# Extract all iv-* IDs from roadmap
ALL_IDS=$(grep -oP 'iv-[a-z0-9]+' "$ROADMAP" | sort -u)
TOTAL_ROADMAP=$(echo "$ALL_IDS" | wc -l | tr -d ' ')

# Separate completed IDs (on lines containing "Recently completed" or after "## Completed")
# The roadmap uses "Recently completed:" inline format
COMPLETED_LINE=$(grep -i 'recently completed' "$ROADMAP" || true)
COMPLETED_IDS=""
if [[ -n "$COMPLETED_LINE" ]]; then
    COMPLETED_IDS=$(echo "$COMPLETED_LINE" | grep -oP 'iv-[a-z0-9]+' | sort -u)
fi

# Active IDs = all IDs minus completed IDs
if [[ -n "$COMPLETED_IDS" ]]; then
    ACTIVE_IDS=$(comm -23 <(echo "$ALL_IDS") <(echo "$COMPLETED_IDS"))
else
    ACTIVE_IDS="$ALL_IDS"
fi
TOTAL_ACTIVE=$(echo "$ACTIVE_IDS" | grep -c . || true)
TOTAL_COMPLETED=$(echo "$COMPLETED_IDS" | grep -c . || true)

# Check each active roadmap ID against beads
MISSING_BEADS=()
FOUND=0
while IFS= read -r id; do
    [[ -z "$id" ]] && continue
    if bd show "$id" --json >/dev/null 2>&1; then
        FOUND=$((FOUND + 1))
    else
        MISSING_BEADS+=("$id")
    fi
done <<< "$ACTIVE_IDS"

# Check completed IDs for closed bead status
UNCLOSED_COMPLETED=()
while IFS= read -r id; do
    [[ -z "$id" ]] && continue
    status=$(bd show "$id" --json 2>/dev/null | python3 -c "import sys,json; print(json.load(sys.stdin).get('status',''))" 2>/dev/null || echo "missing")
    if [[ "$status" != "closed" ]]; then
        UNCLOSED_COMPLETED+=("$id ($status)")
    fi
done <<< "$COMPLETED_IDS"

# Find open beads NOT in roadmap
OPEN_BEADS=$(bd list --status=open --json 2>/dev/null | python3 -c "
import sys, json
for line in sys.stdin:
    line = line.strip()
    if not line: continue
    try:
        obj = json.loads(line)
        print(obj.get('id', ''))
    except: pass
" 2>/dev/null | sort -u)

ORPHANED_BEADS=()
while IFS= read -r id; do
    [[ -z "$id" ]] && continue
    if ! echo "$ALL_IDS" | grep -qx "$id"; then
        ORPHANED_BEADS+=("$id")
    fi
done <<< "$OPEN_BEADS"

# Calculate coverage
if [[ "$TOTAL_ACTIVE" -gt 0 ]]; then
    COVERAGE=$((FOUND * 100 / TOTAL_ACTIVE))
else
    COVERAGE=100
fi

# Determine confidence level
if [[ "$COVERAGE" -eq 100 ]] && [[ ${#MISSING_BEADS[@]} -eq 0 ]]; then
    CONFIDENCE="green"
elif [[ "$COVERAGE" -ge 95 ]]; then
    CONFIDENCE="blue"
elif [[ "$COVERAGE" -ge 80 ]]; then
    CONFIDENCE="yellow"
else
    CONFIDENCE="orange"
fi

# Output
if $JSON_MODE; then
    cat <<ENDJSON
{
  "coverage_pct": $COVERAGE,
  "confidence": "$CONFIDENCE",
  "roadmap_ids_total": $TOTAL_ROADMAP,
  "roadmap_ids_active": $TOTAL_ACTIVE,
  "roadmap_ids_completed": $TOTAL_COMPLETED,
  "active_with_bead": $FOUND,
  "missing_beads": $(if [[ ${#MISSING_BEADS[@]} -eq 0 ]]; then echo '[]'; else printf '"%s"\n' "${MISSING_BEADS[@]}" | python3 -c "import sys,json; print(json.dumps([l.strip().strip('\"') for l in sys.stdin if l.strip()]))" 2>/dev/null || echo '[]'; fi),
  "unclosed_completed": $(if [[ ${#UNCLOSED_COMPLETED[@]} -eq 0 ]]; then echo '[]'; else printf '"%s"\n' "${UNCLOSED_COMPLETED[@]}" | python3 -c "import sys,json; print(json.dumps([l.strip().strip('\"') for l in sys.stdin if l.strip()]))" 2>/dev/null || echo '[]'; fi),
  "orphaned_open_beads": ${#ORPHANED_BEADS[@]}
}
ENDJSON
else
    echo "=== Roadmap-Bead Consistency Audit ==="
    echo "Roadmap: $ROADMAP"
    echo ""
    echo "IDs in roadmap:     $TOTAL_ROADMAP (active: $TOTAL_ACTIVE, completed: $TOTAL_COMPLETED)"
    echo "Active with bead:   $FOUND / $TOTAL_ACTIVE"
    echo "Coverage:           ${COVERAGE}%"
    echo "Confidence:         $CONFIDENCE"
    echo ""

    if [[ ${#MISSING_BEADS[@]} -gt 0 ]]; then
        echo "ERROR: Roadmap IDs with no bead (${#MISSING_BEADS[@]}):"
        for id in "${MISSING_BEADS[@]}"; do
            echo "  - $id"
        done
        echo ""
    fi

    if [[ ${#UNCLOSED_COMPLETED[@]} -gt 0 ]]; then
        echo "INFO: Recently completed with non-closed bead (${#UNCLOSED_COMPLETED[@]}):"
        for entry in "${UNCLOSED_COMPLETED[@]}"; do
            echo "  - $entry"
        done
        echo ""
    fi

    if [[ ${#ORPHANED_BEADS[@]} -gt 0 ]]; then
        echo "WARNING: Open beads not in roadmap (${#ORPHANED_BEADS[@]} of $(echo "$OPEN_BEADS" | grep -c . || true) total open):"
        # Show first 20 only to avoid wall of text
        shown=0
        for id in "${ORPHANED_BEADS[@]}"; do
            if [[ $shown -ge 20 ]]; then
                echo "  ... and $((${#ORPHANED_BEADS[@]} - 20)) more"
                break
            fi
            echo "  - $id"
            ((shown++))
        done
        echo ""
    fi

    if [[ ${#MISSING_BEADS[@]} -eq 0 ]] && [[ ${#UNCLOSED_COMPLETED[@]} -eq 0 ]]; then
        echo "All roadmap IDs have corresponding beads."
    fi
fi
