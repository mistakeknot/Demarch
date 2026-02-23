#!/usr/bin/env bash
# Test that SKILL-compact.md files exist, have manifests, and are up-to-date.
#
# Usage:
#   bash scripts/test-compact-freshness.sh              # Test all known skills
#   bash scripts/test-compact-freshness.sh <skill-dir>  # Test one skill
#
# Exit codes: 0 = all pass, 1 = failures found

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

PASS=0
FAIL=0

pass() { echo "  ✓ $1"; PASS=$((PASS + 1)); }
fail() { echo "  ✗ $1"; FAIL=$((FAIL + 1)); }

KNOWN_SKILLS=(
    "interverse/interwatch/skills/doc-watch"
    "interverse/interpath/skills/artifact-gen"
    "interverse/interflux/skills/flux-drive"
)

test_skill() {
    local skill_dir="$1"
    local name
    name=$(basename "$(dirname "$skill_dir")")/$(basename "$skill_dir")
    echo "=== $name ==="

    # Test 1: SKILL-compact.md exists
    if [[ -f "$skill_dir/SKILL-compact.md" ]]; then
        pass "SKILL-compact.md exists"
    else
        fail "SKILL-compact.md missing"
        return
    fi

    # Test 2: SKILL-compact.md is non-empty and has content
    local lines
    lines=$(wc -l < "$skill_dir/SKILL-compact.md")
    if [[ "$lines" -ge 20 ]]; then
        pass "SKILL-compact.md has $lines lines (>=20)"
    else
        fail "SKILL-compact.md too short: $lines lines (expected >=20)"
    fi

    # Test 3: Manifest exists
    if [[ -f "$skill_dir/.skill-compact-manifest.json" ]]; then
        pass ".skill-compact-manifest.json exists"
    else
        fail ".skill-compact-manifest.json missing"
        return
    fi

    # Test 4: Manifest is valid JSON
    if python3 -c "import json; json.load(open('$skill_dir/.skill-compact-manifest.json'))" 2>/dev/null; then
        pass "Manifest is valid JSON"
    else
        fail "Manifest is not valid JSON"
        return
    fi

    # Test 5: Manifest lists SKILL.md
    if python3 -c "import json; d=json.load(open('$skill_dir/.skill-compact-manifest.json')); assert 'SKILL.md' in d" 2>/dev/null; then
        pass "Manifest includes SKILL.md"
    else
        fail "Manifest missing SKILL.md entry"
    fi

    # Test 6: All manifest entries correspond to existing files
    local missing_files=0
    while IFS= read -r filename; do
        local found=false
        for f in "$skill_dir"/SKILL.md "$skill_dir"/phases/*.md "$skill_dir"/references/*.md; do
            [[ -f "$f" ]] || continue
            if [[ "$(basename "$f")" == "$filename" ]]; then
                found=true
                break
            fi
        done
        if ! $found; then
            missing_files=$((missing_files + 1))
        fi
    done < <(python3 -c "import json; [print(k) for k in json.load(open('$skill_dir/.skill-compact-manifest.json'))]")

    if [[ "$missing_files" -eq 0 ]]; then
        pass "All manifest entries map to existing files"
    else
        fail "$missing_files manifest entries point to missing files"
    fi

    # Test 7: Source file hashes match manifest (freshness check)
    if bash "$ROOT_DIR/scripts/gen-skill-compact.sh" --check "$skill_dir" >/dev/null 2>&1; then
        pass "Source hashes match manifest (compact file is fresh)"
    else
        fail "Source hashes differ from manifest (compact file is stale)"
    fi

    # Test 8: SKILL.md has compact-mode preamble
    if grep -q 'compact.*SKILL-compact' "$skill_dir/SKILL.md" 2>/dev/null; then
        pass "SKILL.md has compact-mode preamble"
    else
        fail "SKILL.md missing compact-mode preamble"
    fi

    echo ""
}

# Main
if [[ $# -gt 0 ]]; then
    # Test a specific skill directory
    skill_dir="$1"
    [[ "$skill_dir" = /* ]] || skill_dir="$ROOT_DIR/$skill_dir"
    test_skill "$skill_dir"
else
    # Test all known skills
    for skill in "${KNOWN_SKILLS[@]}"; do
        test_skill "$ROOT_DIR/$skill"
    done
fi

echo "=== Results ==="
echo "  Passed: $PASS"
echo "  Failed: $FAIL"

[[ "$FAIL" -eq 0 ]]
