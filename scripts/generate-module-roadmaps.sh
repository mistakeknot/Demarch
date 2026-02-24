#!/usr/bin/env bash
# generate-module-roadmaps.sh — Auto-generate module-level roadmap files from beads state.
# Usage: generate-module-roadmaps.sh [--dry-run]
#
# For each module directory under apps/, os/, core/, interverse/, sdk/:
#   - Queries beads for open/in-progress/blocked/recently-closed items
#   - Writes docs/roadmap.md with standardized format
#   - Links back to the root Demarch Roadmap for strategic context

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DRY_RUN=false
DATE="$(date +%Y-%m-%d)"
UPDATED=0
CREATED=0
SKIPPED=0

for arg in "$@"; do
    case "$arg" in
        --dry-run) DRY_RUN=true ;;
    esac
done

require() {
    command -v "$1" >/dev/null 2>&1 || {
        echo "Required command not found: $1" >&2
        exit 1
    }
}

require bd

# Compute relative path from module docs/ to root docs/demarch-roadmap.md
relative_root_roadmap() {
    local module_location="$1"
    # Count depth from module docs/ dir: interverse/interflux/docs/ needs ../../../docs/demarch-roadmap.md
    # module_location is e.g. "interverse/interflux" (2 segments), plus 1 for the docs/ subdir = 3
    local depth
    depth="$(echo "$module_location" | tr '/' '\n' | wc -l)"
    depth=$((depth + 1))  # +1 for docs/ subdirectory
    local prefix=""
    for ((i = 0; i < depth; i++)); do
        prefix="../${prefix}"
    done
    echo "${prefix}docs/demarch-roadmap.md"
}

for base in "$ROOT_DIR/apps" "$ROOT_DIR/os" "$ROOT_DIR/core" "$ROOT_DIR/interverse" "$ROOT_DIR/sdk"; do
    [ -d "$base" ] || continue
    while IFS= read -r -d '' module_dir; do
        module="$(basename "$module_dir")"
        module_location="${module_dir#$ROOT_DIR/}"

        # Query beads for this module
        open_items=""
        in_progress_items=""
        blocked_items=""
        closed_items=""

        open_items="$(bd list --status=open 2>/dev/null | grep -i "\b${module}\b" || true)"
        in_progress_items="$(bd list --status=in_progress 2>/dev/null | grep -i "\b${module}\b" || true)"
        blocked_items="$(bd blocked 2>/dev/null | grep -i "\b${module}\b" || true)"
        closed_items="$(bd list --status=closed --limit=20 2>/dev/null | grep -i "\b${module}\b" | head -10 || true)"

        # Count items
        open_count=0
        [ -n "$open_items" ] && open_count="$(echo "$open_items" | wc -l)"
        ip_count=0
        [ -n "$in_progress_items" ] && ip_count="$(echo "$in_progress_items" | wc -l)"
        blocked_count=0
        [ -n "$blocked_items" ] && blocked_count="$(echo "$blocked_items" | wc -l)"
        closed_count=0
        [ -n "$closed_items" ] && closed_count="$(echo "$closed_items" | wc -l)"

        total=$((open_count + ip_count + blocked_count))

        # Skip modules with no beads at all
        if [ "$total" -eq 0 ] && [ "$closed_count" -eq 0 ]; then
            SKIPPED=$((SKIPPED + 1))
            continue
        fi

        roadmap_rel="$(relative_root_roadmap "$module_location")"
        output_dir="$module_dir/docs"
        output_file="$output_dir/roadmap.md"

        if $DRY_RUN; then
            if [ -f "$output_file" ]; then
                echo "[dry-run] Would update: $module_location/docs/roadmap.md (open=$open_count, in_progress=$ip_count, blocked=$blocked_count)"
            else
                echo "[dry-run] Would create: $module_location/docs/roadmap.md (open=$open_count, in_progress=$ip_count, blocked=$blocked_count)"
            fi
            continue
        fi

        # Ensure docs/ directory exists
        mkdir -p "$output_dir"

        # Track if this is new or updated
        if [ -f "$output_file" ]; then
            UPDATED=$((UPDATED + 1))
        else
            CREATED=$((CREATED + 1))
        fi

        # Generate the roadmap
        {
            echo "# ${module} Roadmap"
            echo ""
            echo "> Auto-generated from beads on ${DATE}. Strategic context: [Demarch Roadmap](${roadmap_rel})"
            echo ""

            if [ -n "$in_progress_items" ]; then
                echo "## In Progress"
                echo ""
                echo "$in_progress_items" | while IFS= read -r line; do
                    echo "- $line"
                done
                echo ""
            fi

            if [ -n "$blocked_items" ]; then
                echo "## Blocked"
                echo ""
                echo "$blocked_items" | while IFS= read -r line; do
                    echo "- $line"
                done
                echo ""
            fi

            if [ -n "$open_items" ]; then
                echo "## Open Items"
                echo ""
                echo "$open_items" | while IFS= read -r line; do
                    echo "- $line"
                done
                echo ""
            fi

            if [ -n "$closed_items" ]; then
                echo "## Recently Closed"
                echo ""
                echo "$closed_items" | while IFS= read -r line; do
                    echo "- $line"
                done
                echo ""
            fi
        } > "$output_file"

    done < <(find "$base" -mindepth 1 -maxdepth 1 -type d -print0 | sort -z)
done

if $DRY_RUN; then
    echo ""
    echo "Dry run complete. No files written."
else
    echo "Module roadmaps generated: ${CREATED} created, ${UPDATED} updated, ${SKIPPED} skipped (no beads)"
fi
