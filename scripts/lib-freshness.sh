#!/usr/bin/env bash
# lib-freshness.sh — Generic dirty-bit / freshness check via content-hashed manifests.
#
# Source this from a script:
#   source "$(dirname "$0")/lib-freshness.sh"
#
# Then call:
#   freshness_compute_manifest <file>...           # echo JSON manifest of {basename: sha256}
#   freshness_compute_manifest_paths <path>...     # echo JSON manifest of {abs_path: sha256}
#   freshness_check <manifest_path> <file>...      # 0=fresh, 1=stale, 2=missing
#   freshness_update <manifest_path> <file>...     # write manifest (creates parent dir)
#
# Design:
#   A "manifest" is a sorted JSON object mapping a stable key (basename or abs path)
#   to the sha256 of the file's contents. Two manifests compare equal iff every
#   referenced file has the same content. Saving the manifest after a successful
#   run lets the next invocation skip work when nothing has changed.
#
# Use cases:
#   - Skill compaction (gen-skill-compact.sh): regenerate SKILL-compact.md only
#     when SKILL.md or its phase files changed.
#   - SessionStart orientation: skip bd prime / heal-dolt / bd stats when the
#     project's git SHA + memory + beads state are unchanged since last session.
#   - Module roadmap regeneration: skip if no beads in the module changed.
#
# Extracted from scripts/gen-skill-compact.sh per bead sylveste-a4oj.8.

set -euo pipefail

# ─── Manifest computation ──────────────────────────────────────────────

# Compute manifest keyed by basename. Use when file paths are stable
# within a single directory (e.g., SKILL.md + phases/*.md in a skill dir).
freshness_compute_manifest() {
    local manifest='{}'
    local f hash relpath
    for f in "$@"; do
        [[ -f "$f" ]] || continue
        hash=$(sha256sum "$f" | cut -d' ' -f1)
        relpath=$(basename "$f")
        manifest=$(echo "$manifest" | jq --arg k "$relpath" --arg v "$hash" '. + {($k): $v}')
    done
    echo "$manifest" | jq -S '.'
}

# Compute manifest keyed by absolute path. Use when files come from
# multiple directories and basenames could collide (e.g., MEMORY.md from
# user-memory + MEMORY.md from project docs).
freshness_compute_manifest_paths() {
    local manifest='{}'
    local f hash abspath
    for f in "$@"; do
        [[ -f "$f" ]] || continue
        hash=$(sha256sum "$f" | cut -d' ' -f1)
        abspath=$(cd "$(dirname "$f")" && pwd)/$(basename "$f")
        manifest=$(echo "$manifest" | jq --arg k "$abspath" --arg v "$hash" '. + {($k): $v}')
    done
    echo "$manifest" | jq -S '.'
}

# Add a synthetic key/value pair to the manifest (e.g., git HEAD SHA). Useful
# for capturing state that is not a single file's content (a commit, a count,
# a directory listing hash). Pipe a manifest in, get a manifest out.
#
# Usage:
#   freshness_compute_manifest a.md b.md | freshness_add_key git_sha "$(git rev-parse HEAD)"
freshness_add_key() {
    local key="$1"
    local value="$2"
    jq --arg k "$key" --arg v "$value" '. + {($k): $v}' | jq -S '.'
}

# ─── Freshness comparison ──────────────────────────────────────────────

# Compare a current manifest (passed via stdin) against a saved one at
# manifest_path. Echoes a status line to stderr; returns:
#   0 = fresh (manifests match)
#   1 = stale (manifests differ — diff written to stderr when verbose)
#   2 = missing (saved manifest does not exist)
#
# Verbose mode (FRESHNESS_VERBOSE=1) prints the diff on stale.
freshness_compare() {
    local manifest_path="$1"
    local label="${2:-$manifest_path}"
    local current saved
    current=$(cat)

    if [[ ! -f "$manifest_path" ]]; then
        echo "MISSING: $label ($manifest_path)" >&2
        return 2
    fi

    saved=$(cat "$manifest_path")

    if [[ "$current" == "$saved" ]]; then
        [[ "${FRESHNESS_VERBOSE:-0}" == 1 ]] && echo "FRESH: $label" >&2
        return 0
    fi

    echo "STALE: $label" >&2
    if [[ "${FRESHNESS_VERBOSE:-0}" == 1 ]]; then
        diff <(echo "$saved" | jq -S '.') <(echo "$current" | jq -S '.') >&2 || true
    fi
    return 1
}

# Convenience: compute manifest from file list, compare against saved.
# Usage: freshness_check <manifest_path> <label> <file>...
freshness_check() {
    local manifest_path="$1"
    local label="$2"
    shift 2
    freshness_compute_manifest "$@" | freshness_compare "$manifest_path" "$label"
}

# Update the saved manifest file. Creates parent directory if missing.
# Usage: freshness_update <manifest_path> <file>...
freshness_update() {
    local manifest_path="$1"
    shift
    mkdir -p "$(dirname "$manifest_path")"
    freshness_compute_manifest "$@" > "$manifest_path"
}

# ─── Self-test ─────────────────────────────────────────────────────────
# Run with: bash lib-freshness.sh --self-test

if [[ "${1:-}" == "--self-test" ]]; then
    set +e
    tmp=$(mktemp -d)
    trap 'rm -rf "$tmp"' EXIT

    echo "alpha" > "$tmp/a.txt"
    echo "beta"  > "$tmp/b.txt"
    manifest="$tmp/manifest.json"

    # First call: missing
    freshness_check "$manifest" "self-test" "$tmp/a.txt" "$tmp/b.txt"
    [[ $? -eq 2 ]] || { echo "FAIL: expected missing (2)"; exit 1; }
    echo "PASS: missing-manifest detected"

    # Update + recheck: fresh
    freshness_update "$manifest" "$tmp/a.txt" "$tmp/b.txt"
    freshness_check  "$manifest" "self-test" "$tmp/a.txt" "$tmp/b.txt"
    [[ $? -eq 0 ]] || { echo "FAIL: expected fresh (0)"; exit 1; }
    echo "PASS: fresh-manifest detected"

    # Mutate + recheck: stale
    echo "alpha-modified" > "$tmp/a.txt"
    freshness_check "$manifest" "self-test" "$tmp/a.txt" "$tmp/b.txt"
    [[ $? -eq 1 ]] || { echo "FAIL: expected stale (1)"; exit 1; }
    echo "PASS: stale-manifest detected"

    # add-key: synthetic state
    keyed=$(freshness_compute_manifest "$tmp/a.txt" | freshness_add_key git_sha abc123)
    echo "$keyed" | jq -e '.git_sha == "abc123"' >/dev/null || { echo "FAIL: add-key"; exit 1; }
    echo "PASS: add-key works"

    echo "All self-tests passed."
fi
