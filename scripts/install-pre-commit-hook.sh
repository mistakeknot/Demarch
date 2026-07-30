#!/usr/bin/env bash
# Install the autonomy-position pre-commit check into .git/hooks/pre-commit.
#
# Idempotent, and non-destructive to the beads-managed section that already
# occupies that file: this appends its own marker-delimited block and rewrites
# only between its own markers on re-run. Beads owns
# `--- BEGIN/END BEADS INTEGRATION ---`; leave it alone.
#
# Usage: bash scripts/install-pre-commit-hook.sh [--check]
#   --check  exit 1 if the hook is not installed, install nothing

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
HOOK="$ROOT/.git/hooks/pre-commit"
BEGIN="# --- BEGIN SYLVESTE AUTONOMY POSITION ---"
END="# --- END SYLVESTE AUTONOMY POSITION ---"

BLOCK="$BEGIN
# Managed by scripts/install-pre-commit-hook.sh. Do not hand-edit.
if [ -x \"\$(git rev-parse --show-toplevel)/scripts/pre-commit-hook.sh\" ]; then
  \"\$(git rev-parse --show-toplevel)/scripts/pre-commit-hook.sh\" \"\$@\" || exit \$?
fi
$END"

if [[ "${1:-}" == "--check" ]]; then
    if [[ -f "$HOOK" ]] && grep -qF "$BEGIN" "$HOOK"; then
        echo "pre-commit: autonomy-position check installed"
        exit 0
    fi
    echo "pre-commit: autonomy-position check NOT installed — run scripts/install-pre-commit-hook.sh" >&2
    exit 1
fi

chmod +x "$ROOT/scripts/pre-commit-hook.sh"

if [[ ! -f "$HOOK" ]]; then
    printf '#!/usr/bin/env sh\n%s\n' "$BLOCK" > "$HOOK"
    chmod +x "$HOOK"
    echo "installed $HOOK"
    exit 0
fi

if grep -qF "$BEGIN" "$HOOK"; then
    # Rewrite only our own block; everything else in the file is untouched.
    python3 - "$HOOK" "$BEGIN" "$END" "$BLOCK" <<'PY'
import re, sys
path, begin, end, block = sys.argv[1:5]
text = open(path, encoding="utf-8").read()
pattern = re.compile(re.escape(begin) + r".*?" + re.escape(end), re.DOTALL)
open(path, "w", encoding="utf-8").write(pattern.sub(lambda _: block, text))
PY
    echo "refreshed the autonomy-position block in $HOOK"
    exit 0
fi

printf '\n%s\n' "$BLOCK" >> "$HOOK"
chmod +x "$HOOK"
echo "appended the autonomy-position block to $HOOK"
