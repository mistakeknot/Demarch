#!/usr/bin/env bash
# audit-roadmap-beads.sh — Check consistency between roadmap and beads database.
# Usage: audit-roadmap-beads.sh [--json] [roadmap-path]
# Default roadmap: docs/sylveste-roadmap.md (relative to repo root)

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
ROADMAP="${ROADMAP:-$REPO_ROOT/docs/sylveste-roadmap.md}"

# Cloud-guard: cloud sessions can't run bd; skip cleanly so we don't produce
# misleading "missing from beads" results for every roadmap entry.
GUARD_LIB="$REPO_ROOT/scripts/lib-cloud-guard.sh"
if [[ -r "$GUARD_LIB" ]]; then
    # shellcheck source=lib-cloud-guard.sh
    source "$GUARD_LIB"
    if cloud_session; then
        if $JSON_MODE; then
            echo '{"skipped":"cloud read-only mode","reason":"audit requires bd CLI"}'
        else
            cloud_log_skip "audit-roadmap-beads"
        fi
        exit 0
    fi
    if ! command -v bd >/dev/null 2>&1; then
        if $JSON_MODE; then
            echo '{"skipped":"bd not on PATH","reason":"workstation bd install required"}'
        else
            workstation_log_missing_bd "audit-roadmap-beads"
        fi
        exit 0
    fi
fi

if [[ ! -f "$ROADMAP" ]]; then
    if $JSON_MODE; then
        echo '{"error":"roadmap not found","path":"'"$ROADMAP"'"}'
    else
        echo "ERROR: Roadmap not found: $ROADMAP"
    fi
    exit 1
fi

# Extract current and legacy bead IDs without requiring GNU grep.
extract_ids() {
    grep -Eio '(sylveste|iv)-[a-z0-9]+([.-][a-z0-9]+)*' || true
}

ALL_IDS="$(extract_ids < "$ROADMAP" | LC_ALL=C sort -fu)"
ALL_IDS_NORMALIZED="$(printf '%s\n' "$ALL_IDS" | tr '[:upper:]' '[:lower:]' | LC_ALL=C sort -u)"
TOTAL_ROADMAP=$(printf '%s\n' "$ALL_IDS" | grep -c . || true)

# Separate completed IDs (on lines containing "Recently completed" or after "## Completed")
# The roadmap uses "Recently completed:" inline format
COMPLETED_LINE=$(grep -i 'recently completed' "$ROADMAP" || true)
COMPLETED_IDS=""
if [[ -n "$COMPLETED_LINE" ]]; then
    COMPLETED_IDS=$(printf '%s\n' "$COMPLETED_LINE" | extract_ids | LC_ALL=C sort -fu)
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
    status=$(bd show "$id" --json 2>/dev/null | jq -r '
        if type == "array" then (.[0].status // "") else (.status // "") end
    ' 2>/dev/null || echo "missing")
    if [[ "$status" != "closed" ]]; then
        UNCLOSED_COMPLETED+=("$id ($status)")
    fi
done <<< "$COMPLETED_IDS"

# Find open beads NOT in roadmap
OPEN_BEADS=$(bd list --status=open --json --limit 0 2>/dev/null | jq -r '
    if type == "array" then .[]?.id else .id? end
' 2>/dev/null | LC_ALL=C sort -fu)

ORPHANED_BEADS=()
while IFS= read -r id; do
    [[ -z "$id" ]] && continue
    if ! printf '%s\n' "$ALL_IDS_NORMALIZED" | grep -Fqx "$(printf '%s' "$id" | tr '[:upper:]' '[:lower:]')"; then
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
            shown=$((shown + 1))
        done
        echo ""
    fi

    if [[ ${#MISSING_BEADS[@]} -eq 0 ]] && [[ ${#UNCLOSED_COMPLETED[@]} -eq 0 ]]; then
        echo "All roadmap IDs have corresponding beads."
    fi
fi
