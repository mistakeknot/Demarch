#!/usr/bin/env bash
# shellcheck disable=SC2155

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ROOT_DOCS_DIR="$ROOT_DIR/docs"
OUTPUT="${1:-$ROOT_DOCS_DIR/roadmap.json}"

# Read project config from .interwatch/project.yaml if available
_PROJECT_YAML="$ROOT_DIR/.interwatch/project.yaml"
if [ -z "${ROADMAP_PROJECT:-}" ] && [ -f "$_PROJECT_YAML" ] && command -v yq >/dev/null 2>&1; then
    ROADMAP_PROJECT="$(yq -r '.project // ""' "$_PROJECT_YAML")"
    if [ -z "${ROADMAP_SCAN_DIRS:-}" ]; then
        _yaml_dirs="$(yq -r '.roadmap.scan_dirs // [] | join(":")' "$_PROJECT_YAML")"
        [ -n "$_yaml_dirs" ] && ROADMAP_SCAN_DIRS="$_yaml_dirs"
    fi
fi
ROADMAP_PROJECT="${ROADMAP_PROJECT:-$(basename "$ROOT_DIR" | tr '[:upper:]' '[:lower:]')}"
EM_DASH="—"

require() {
    command -v "$1" >/dev/null 2>&1 || {
        echo "Required command not found: $1" >&2
        exit 1
    }
}

extract_version() {
    local module_dir="$1"
    local version
    if [ -f "$module_dir/.claude-plugin/plugin.json" ]; then
        version="$(jq -r '.version // empty' "$module_dir/.claude-plugin/plugin.json")"
        [ -n "$version" ] && echo "$version" && return
    fi
    if [ -f "$module_dir/package.json" ]; then
        version="$(jq -r '.version // empty' "$module_dir/package.json")"
        [ -n "$version" ] && echo "$version" && return
    fi
    if [ -f "$module_dir/pyproject.toml" ]; then
        version="$(grep -m1 -E '^version\s*=' "$module_dir/pyproject.toml" | sed -E 's/^version[[:space:]]*=[[:space:]]*\"([^\"]+)\".*$/\1/')"
        [ -n "$version" ] && echo "$version" && return
    fi
    echo "$EM_DASH"
}

module_roadmap_file() {
    local module_dir="$1"
    local module="$2"
    local new_canonical="$module_dir/docs/roadmap.md"
    local old_canonical="$module_dir/docs/${module}-roadmap.md"

    if [ -f "$new_canonical" ]; then
        echo "$new_canonical"
    elif [ -f "$old_canonical" ]; then
        echo "$old_canonical"
    else
        echo ""
    fi
}

add_module() {
    local module="$1"
    local location="$2"
    local version="$3"
    local roadmap_source="$4"
    local open_beads="$5"
    local status="$6"

    jq -c -n \
        --arg module "$module" \
        --arg location "$location" \
        --arg version "$version" \
        --arg roadmap_source "$roadmap_source" \
        --argjson open_beads "$open_beads" \
        --arg status "$status" \
        '{module:$module,location:$location,version:$version,has_roadmap:($roadmap_source!="none"),roadmap_source:$roadmap_source,open_beads:$open_beads,status:$status}' \
        >>"$MODULES_FILE"
}

add_no_roadmap_module() {
    local module="$1"
    local location="$2"
    local version="$3"
    local notes="$4"
    jq -c -n --arg module "$module" --arg location "$location" --arg version "$version" --arg notes "$notes" \
        '{module:$module,location:$location,version:$version,notes:$notes}' >>"$NO_ROADMAP_FILE"
}

# --- Beads-derived item collection (replaces markdown/JSON parsers) ---

# (Module extraction, phase mapping, status mapping, and title stripping are all done in the jq pass)

collect_items_from_beads() {
    # Collect roadmap items from beads (single source of truth).
    # Requires: bd CLI available.

    if ! command -v bd >/dev/null 2>&1; then
        echo "Warning: bd not found, skipping bead-derived items" >&2
        return
    fi

    local beads_json
    beads_json="$(bd list --json --limit 0 --all 2>/dev/null)" || return

    local count
    count="$(echo "$beads_json" | jq 'length')"
    [ "$count" -gt 0 ] || return

    # Transform all beads to roadmap items in a single jq pass (no per-bead jq calls).
    # This handles 3000+ beads efficiently.
    echo "$beads_json" | jq -c '
        .[] |
        select(.id != null and .title != null) |
        select(.status != "closed") |
        {
            module: (
                if (.title | test("^\\[")) then
                    (.title | capture("^\\[(?<m>[^\\]]+)\\]") | .m | split("/")[0])
                elif (.labels // [] | any(startswith("mod:"))) then
                    (.labels | map(select(startswith("mod:"))) | .[0] | ltrimstr("mod:"))
                else
                    "demarch"
                end
            ),
            id: .id,
            title: (.title | gsub("^\\[[^\\]]+\\]\\s*"; "")),
            phase: (if .priority <= 1 then "now" elif .priority == 2 then "next" else "later" end),
            priority: ("P" + (.priority | tostring)),
            status: (
                if .dependency_count > 0 and .status != "closed" then "blocked"
                elif .status == "in_progress" then "in_progress"
                elif .status == "blocked" then "blocked"
                else "open"
                end
            ),
            source: "beads",
            source_file: "beads",
            blocked_by: [],
            notes: (.title | gsub("^\\[[^\\]]+\\]\\s*"; ""))
        }
    ' >> "$ITEMS_FILE" 2>/dev/null || true

    # Note: cross-dep resolution via ID_TO_MODULE is skipped for beads-derived items
    # since bd list --json doesn't provide dependency IDs (only counts).
    # Cross-module dependencies will be empty until bd adds dep ID export.
}

# === MAIN ===

require jq

TMP_DIR="$(mktemp -d)"
chmod 700 "$TMP_DIR"
trap 'rm -rf "$TMP_DIR"' EXIT

MODULES_FILE="$TMP_DIR/modules.jsonl"
ITEMS_FILE="$TMP_DIR/items.jsonl"
HIGHLIGHTS_FILE="$TMP_DIR/highlights.jsonl"
RESEARCH_FILE="$TMP_DIR/research.jsonl"
NO_ROADMAP_FILE="$TMP_DIR/no-roadmap.jsonl"
CROSS_FILE="$TMP_DIR/cross.jsonl"
touch "$MODULES_FILE" "$ITEMS_FILE" "$HIGHLIGHTS_FILE" "$RESEARCH_FILE" "$NO_ROADMAP_FILE" "$CROSS_FILE"

# --- Module metadata scanning (filesystem-based) ---

if [ -n "${ROADMAP_SCAN_DIRS:-}" ]; then
    IFS=: read -ra _scan_dirs <<< "$ROADMAP_SCAN_DIRS"
    SCAN_BASES=()
    for _d in "${_scan_dirs[@]}"; do
        [[ "$_d" = /* ]] && SCAN_BASES+=("$_d") || SCAN_BASES+=("$ROOT_DIR/$_d")
    done
else
    SCAN_BASES=()
    for _candidate in "$ROOT_DIR"/*/; do
        [ -d "$_candidate" ] || continue
        _base="$(basename "$_candidate")"
        [[ "$_base" == .* || "$_base" == "docs" || "$_base" == "scripts" ]] && continue
        _has_module=0
        for _sub in "$_candidate"/*/; do
            [ -d "$_sub" ] || continue
            if [ -f "$_sub/.claude-plugin/plugin.json" ] || [ -f "$_sub/CLAUDE.md" ]; then
                _has_module=1; break
            fi
        done
        if [ "$_has_module" -eq 1 ]; then
            SCAN_BASES+=("${_candidate%/}")
        fi
    done
fi

for base in "${SCAN_BASES[@]}"; do
    [ -d "$base" ] || continue
    while IFS= read -r -d '' module_dir; do
        module="$(basename "$module_dir")"
        module_location="${module_dir#$ROOT_DIR/}"
        version="$(extract_version "$module_dir")"
        roadmap_md_source="$(module_roadmap_file "$module_dir" "$module")"
        roadmap_json="$module_dir/docs/roadmap.json"
        roadmap_source="none"

        if [ -f "$roadmap_json" ] || [ -n "$roadmap_md_source" ]; then
            roadmap_source="beads"
            add_module "$module" "$module_location" "$version" "$roadmap_source" 0 "active"
        else
            if [ "$version" = "$EM_DASH" ]; then
                status="planned"
            else
                status="early"
            fi
            add_module "$module" "$module_location" "$version" "$roadmap_source" 0 "$status"
            add_no_roadmap_module "$module" "$module_location" "$version" "No docs/roadmap.md"
        fi
    done < <(find "$base" -mindepth 1 -maxdepth 1 -type d -print0 | sort -z)
done

# Add root project module
add_module "$ROADMAP_PROJECT" "root" "$(extract_version "$ROOT_DIR")" "beads" 0 "active"

# --- Collect items from beads (single source of truth) ---

collect_items_from_beads

# --- Compute stats and assemble output ---

module_count="$(jq -s 'length' "$MODULES_FILE")"
if [ "$module_count" -eq 0 ]; then
    echo "No modules discovered. Set ROADMAP_SCAN_DIRS or ensure top-level dirs contain plugin.json subdirs." >&2
    exit 1
fi

open_beads="$(jq -s '[.[] | select(.status == "open" or .status == "in_progress" or .status == "blocked")] | unique_by(.id) | length' "$ITEMS_FILE")"
blocked_items="$(jq -s '[.[] | select((.status=="blocked") or ((.blocked_by | length) > 0))] | unique_by(.id) | length' "$ITEMS_FILE")"

# Write pre-assembled arrays to temp files for jq --slurpfile (avoids ARG_MAX)
jq -s '.' "$MODULES_FILE" > "$TMP_DIR/modules.json"
jq -s '[.[] | select(.phase == "now")]' "$ITEMS_FILE" > "$TMP_DIR/now.json"
jq -s '[.[] | select(.phase == "next")]' "$ITEMS_FILE" > "$TMP_DIR/next.json"
jq -s '[.[] | select(.phase == "later")]' "$ITEMS_FILE" > "$TMP_DIR/later.json"
jq -s '.' "$HIGHLIGHTS_FILE" > "$TMP_DIR/highlights.json"
jq -s '.' "$RESEARCH_FILE" > "$TMP_DIR/research.json"
jq -s '.' "$CROSS_FILE" > "$TMP_DIR/cross.json"
jq -s '.' "$NO_ROADMAP_FILE" > "$TMP_DIR/no_roadmap.json"

if ! jq -n \
    --arg project "$ROADMAP_PROJECT" \
    --arg kind "${ROADMAP_PROJECT}-monorepo-roadmap" \
    --arg generated_at "$(date -u +%Y-%m-%dT%H:%M:%S%:z)" \
    --argjson module_count "$module_count" \
    --argjson open_beads "$open_beads" \
    --argjson blocked "$blocked_items" \
    --slurpfile modules "$TMP_DIR/modules.json" \
    --slurpfile roadmap_now "$TMP_DIR/now.json" \
    --slurpfile roadmap_next "$TMP_DIR/next.json" \
    --slurpfile roadmap_later "$TMP_DIR/later.json" \
    --slurpfile module_highlights "$TMP_DIR/highlights.json" \
    --slurpfile research_agenda "$TMP_DIR/research.json" \
    --slurpfile cross_module_dependencies "$TMP_DIR/cross.json" \
    --slurpfile modules_without "$TMP_DIR/no_roadmap.json" \
    '{project:$project,kind:$kind,generated_at:$generated_at,module_count:$module_count,open_beads:$open_beads,blocked:$blocked,modules:$modules[0],snapshot:$modules[0],roadmap:{now:$roadmap_now[0],next:$roadmap_next[0],later:$roadmap_later[0]},module_highlights:$module_highlights[0],research_agenda:$research_agenda[0],cross_module_dependencies:$cross_module_dependencies[0],modules_without_roadmaps:$modules_without[0],dependency_graph:$cross_module_dependencies[0]}' \
    >"$OUTPUT"; then
    echo "Failed to write $OUTPUT" >&2
    exit 1
fi

jq -M . "$OUTPUT" >"${OUTPUT}.tmp" && mv "${OUTPUT}.tmp" "$OUTPUT"
echo "Wrote roadmap JSON: $OUTPUT"
