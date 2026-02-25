#!/usr/bin/env bash
# check-go-module-paths.sh — Verify all first-party Go modules use canonical paths.
# Convention: github.com/mistakeknot/<dirname> for all in-scope modules.
# Exits non-zero if any module path is non-canonical.
set -euo pipefail

REPO_ROOT="${1:-.}"
errors=0

while IFS= read -r gomod; do
    # Get directory basename
    mod_dir="$(dirname "$gomod")"
    dirname="$(basename "$mod_dir")"

    # Read module path from go.mod
    mod_path="$(head -1 "$gomod" | awk '{print $2}')"
    expected="github.com/mistakeknot/${dirname}"

    if [[ "$mod_path" != "$expected" ]]; then
        rel="${gomod#"$REPO_ROOT"/}"
        echo "MISMATCH: $rel"
        echo "  current:  $mod_path"
        echo "  expected: $expected"
        echo
        errors=$((errors + 1))
    fi
done < <(find "$REPO_ROOT" -name go.mod \
    -not -path '*/research/*' \
    -not -path '*/.external/*' \
    -not -path '*/testdata/*' \
    -not -path '*/vendor/*' \
    -not -path '*/node_modules/*')

if [[ "$errors" -gt 0 ]]; then
    echo "Found $errors non-canonical module path(s)."
    exit 1
else
    echo "All Go module paths are canonical."
    exit 0
fi
