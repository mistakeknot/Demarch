#!/usr/bin/env bash
# gen-skill-compact.sh — Generate SKILL-compact.md from full skill docs
#
# Usage:
#   gen-skill-compact.sh <skill-dir>          # Generate compact file
#   gen-skill-compact.sh --check <skill-dir>  # Check freshness only
#   gen-skill-compact.sh --check-all          # Check all known skills
#
# LLM backend (default: claude -p):
#   GEN_COMPACT_CMD="claude -p" gen-skill-compact.sh <dir>
#   GEN_COMPACT_CMD="oracle --wait -p" gen-skill-compact.sh <dir>
#
# Exit codes:
#   0 = success (generate) or all fresh (check)
#   1 = stale files found (check mode)
#   2 = manifest missing or error

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INTERVERSE_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# Default LLM command — override with GEN_COMPACT_CMD env var
LLM_CMD="${GEN_COMPACT_CMD:-claude -p}"

# Known skill directories (relative to Interverse root)
KNOWN_SKILLS=(
    "interverse/interwatch/skills/doc-watch"
    "interverse/interpath/skills/artifact-gen"
    "interverse/interflux/skills/flux-drive"
    "os/clavain/skills/interserve"
    "os/clavain/skills/engineering-docs"
    "os/clavain/skills/subagent-driven-development"
    "os/clavain/skills/dispatching-parallel-agents"
    "os/clavain/skills/file-todos"
    "os/clavain/skills/writing-plans"
    "os/clavain/skills/code-review-discipline"
    "os/clavain/skills/landing-a-change"
    "os/clavain/skills/executing-plans"
    "os/clavain/skills/brainstorming"
)

# ─── Helpers ──────────────────────────────────────────────────────────

compute_manifest() {
    local skill_dir="$1"
    local manifest="{}"

    # Hash SKILL.md + all phase and reference files
    for f in "$skill_dir"/SKILL.md "$skill_dir"/phases/*.md "$skill_dir"/references/*.md; do
        [[ -f "$f" ]] || continue
        local hash
        hash=$(sha256sum "$f" | cut -d' ' -f1)
        local relpath
        relpath=$(basename "$f")
        manifest=$(echo "$manifest" | jq --arg k "$relpath" --arg v "$hash" '. + {($k): $v}')
    done

    echo "$manifest" | jq -S '.'
}

check_freshness() {
    local skill_dir="$1"
    local manifest_path="$skill_dir/.skill-compact-manifest.json"

    if [[ ! -f "$manifest_path" ]]; then
        echo "MISSING: $manifest_path" >&2
        return 2
    fi

    if [[ ! -f "$skill_dir/SKILL-compact.md" ]]; then
        echo "MISSING: $skill_dir/SKILL-compact.md" >&2
        return 2
    fi

    local current
    current=$(compute_manifest "$skill_dir")
    local saved
    saved=$(cat "$manifest_path")

    if [[ "$current" == "$saved" ]]; then
        echo "FRESH: $skill_dir"
        return 0
    else
        echo "STALE: $skill_dir" >&2
        # Show which files changed
        diff <(echo "$saved" | jq -S '.') <(echo "$current" | jq -S '.') >&2 || true
        return 1
    fi
}

generate_compact_structural() {
    # Deterministic fallback: extract structure without LLM.
    # Keeps headings, code blocks, tables, scoring formulas, first sentence per section.
    local skill_dir="$1"
    local skill_name
    skill_name=$(basename "$skill_dir")

    echo "Generating compact (structural mode) for: $skill_dir" >&2

    {
        echo "# ${skill_name} — Compact Reference"
        echo ""

        for f in "$skill_dir"/SKILL.md "$skill_dir"/phases/*.md "$skill_dir"/references/*.md; do
            [[ -f "$f" ]] || continue

            local in_code_block=false
            local in_table=false
            local last_was_heading=false

            while IFS= read -r line; do
                # Code block boundaries
                if [[ "$line" =~ ^\`\`\` ]]; then
                    echo "$line"
                    if $in_code_block; then
                        in_code_block=false
                    else
                        in_code_block=true
                    fi
                    continue
                fi

                # Inside code block: keep everything
                if $in_code_block; then
                    echo "$line"
                    continue
                fi

                # Headings: always keep
                if [[ "$line" =~ ^#{1,4}\  ]]; then
                    echo ""
                    echo "$line"
                    echo ""
                    last_was_heading=true
                    in_table=false
                    continue
                fi

                # Table rows: keep all
                if [[ "$line" =~ ^\| ]]; then
                    echo "$line"
                    in_table=true
                    last_was_heading=false
                    continue
                fi
                if $in_table && [[ -z "$line" ]]; then
                    in_table=false
                fi

                # Scoring formulas and key assignments (lines with =, score, weight)
                if [[ "$line" =~ (score|weight|formula|confidence|threshold|priority) ]] && [[ "$line" =~ [=\+\-\*] ]]; then
                    echo "$line"
                    last_was_heading=false
                    continue
                fi

                # Bullet points with keywords (keep structural bullets)
                if [[ "$line" =~ ^[[:space:]]*[-\*] ]] && [[ "$line" =~ (must|required|always|never|skip|include|exclude|check|verify|run|use|set|if|when|only|default) ]]; then
                    echo "$line"
                    last_was_heading=false
                    continue
                fi

                # First non-empty line after a heading (the topic sentence)
                if $last_was_heading && [[ -n "$line" ]] && [[ ! "$line" =~ ^[[:space:]]*$ ]]; then
                    echo "$line"
                    last_was_heading=false
                    continue
                fi

                last_was_heading=false
            done < "$f"
        done

        echo ""
        echo "---"
        echo "For edge cases or full reference, read SKILL.md and its phases/ directory."
    }
}

generate_compact() {
    local skill_dir="$1"

    if [[ ! -f "$skill_dir/SKILL.md" ]]; then
        echo "Error: $skill_dir/SKILL.md not found" >&2
        return 2
    fi

    # Structural mode: deterministic extraction without LLM.
    if [[ "${LLM_CMD}" == "structural" ]]; then
        local output
        output=$(generate_compact_structural "$skill_dir")
        _write_compact "$skill_dir" "$output"
        return 0
    fi

    # Check if LLM is available
    local llm_bin
    llm_bin=$(echo "$LLM_CMD" | cut -d' ' -f1)
    if ! command -v "$llm_bin" >/dev/null 2>&1; then
        echo "Warning: $llm_bin not found, falling back to structural mode" >&2
        local output
        output=$(generate_compact_structural "$skill_dir")
        _write_compact "$skill_dir" "$output"
        return 0
    fi

    echo "Generating compact for: $skill_dir" >&2

    # Concatenate all source files
    local content=""
    for f in "$skill_dir"/SKILL.md "$skill_dir"/phases/*.md "$skill_dir"/references/*.md; do
        [[ -f "$f" ]] || continue
        content+="
--- FILE: $(basename "$f") ---
$(cat "$f")
"
    done

    local skill_name
    skill_name=$(basename "$skill_dir")

    local prompt="Summarize this skill into a single compact instruction file (50-200 lines depending on complexity).

Rules:
- Keep: algorithm steps, decision points, output contracts, tables, code blocks, scoring formulas
- Remove: examples, rationale, verbose descriptions, 'why' explanations, alternatives considered
- Preserve exact scoring formulas and selection rules (these ARE the algorithm)
- Add at the bottom: 'For edge cases or full reference, read SKILL.md and its phases/ directory.'
- Start with: '# [Skill Name] (compact)'
- Use markdown formatting

Skill content to summarize:

$content"

    # Call LLM
    local output
    output=$(echo "$prompt" | $LLM_CMD 2>/dev/null)

    if [[ -z "$output" ]] || ! echo "$output" | grep -q '[a-zA-Z]'; then
        echo "Warning: LLM returned empty output, falling back to structural mode" >&2
        output=$(generate_compact_structural "$skill_dir")
    fi

    _write_compact "$skill_dir" "$output"
}

_write_compact() {
    local skill_dir="$1"
    local output="$2"

    # Write compact file via temp (owner-only permissions — T1 hardening)
    local tmpfile
    tmpfile=$(mktemp)
    chmod 600 "$tmpfile"
    echo "$output" > "$tmpfile"
    mv "$tmpfile" "$skill_dir/SKILL-compact.md"
    echo "Wrote: $skill_dir/SKILL-compact.md ($(wc -l < "$skill_dir/SKILL-compact.md") lines)" >&2

    # Write manifest via temp (owner-only permissions — T1 hardening)
    tmpfile=$(mktemp)
    chmod 600 "$tmpfile"
    compute_manifest "$skill_dir" > "$tmpfile"
    mv "$tmpfile" "$skill_dir/.skill-compact-manifest.json"
    echo "Wrote: $skill_dir/.skill-compact-manifest.json" >&2
}

# ─── Main ─────────────────────────────────────────────────────────────

case "${1:-}" in
    --check-all)
        stale=0
        for skill in "${KNOWN_SKILLS[@]}"; do
            full_path="$INTERVERSE_ROOT/$skill"
            if ! check_freshness "$full_path"; then
                stale=1
            fi
        done
        exit "$stale"
        ;;
    --check)
        skill_dir="${2:?Usage: gen-skill-compact.sh --check <skill-dir>}"
        # Resolve to absolute path
        if [[ ! "$skill_dir" = /* ]]; then
            skill_dir="$INTERVERSE_ROOT/$skill_dir"
        fi
        check_freshness "$skill_dir"
        ;;
    --help|-h)
        echo "Usage:"
        echo "  gen-skill-compact.sh <skill-dir>          Generate compact file"
        echo "  gen-skill-compact.sh --check <skill-dir>  Check freshness"
        echo "  gen-skill-compact.sh --check-all          Check all known skills"
        echo ""
        echo "Environment:"
        echo "  GEN_COMPACT_CMD  LLM command (default: claude -p)"
        echo "                   Set to 'structural' for deterministic extraction (no LLM)"
        echo "                   Auto-falls back to structural if LLM binary not found"
        ;;
    "")
        echo "Error: skill directory required" >&2
        echo "Usage: gen-skill-compact.sh <skill-dir>" >&2
        exit 2
        ;;
    *)
        skill_dir="$1"
        if [[ ! "$skill_dir" = /* ]]; then
            skill_dir="$INTERVERSE_ROOT/$skill_dir"
        fi
        generate_compact "$skill_dir"
        ;;
esac
