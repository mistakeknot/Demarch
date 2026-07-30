#!/usr/bin/env bash
# Pre-commit hook: keep docs/canon/autonomy.md's generated position block honest.
#
# Install: bash scripts/install-pre-commit-hook.sh
#
# What this guards
# ----------------
# The block records two facts about the running system — the declared delegation
# level and the Track A no-touch streak. Both are read live by
# scripts/gen-autonomy-position.py. A hand-edited or stale block makes the canon
# page assert something about the system that is not true, which is worse than
# having no number at all.
#
# Why it is path-scoped rather than unconditional
# -----------------------------------------------
# The streak is a live counter: it ticks on its own, with no commit involved. An
# unconditional check would block every commit anywhere in a 60-repo monorepo
# whenever that counter moved — friction with no safety payoff, since a stale
# streak line does not make any *change in this commit* wrong.
#
# What does make a commit wrong is changing the machinery the block describes
# while leaving the block behind. So: hard-fail when the commit touches the
# canon page, the generator, or the kernel package that supplies the level;
# advise otherwise. `--check --require-sources` is available for a deliberate
# audit, and CI proves the checker still fails loudly on a source-less checkout.

set -euo pipefail

ROOT="$(git rev-parse --show-toplevel)"
GEN="$ROOT/scripts/gen-autonomy-position.py"

[ -f "$GEN" ] || exit 0

# Paths whose change can invalidate the generated block.
GUARDED_RE='^(docs/canon/autonomy\.md|scripts/gen-autonomy-position\.py|core/intercore/pkg/autonomy/)'

staged="$(git diff --cached --name-only --diff-filter=ACMR)"
if printf '%s\n' "$staged" | grep -Eq "$GUARDED_RE"; then
    strict=1
else
    strict=0
fi

output=""
rc=0
output="$(python3 "$GEN" --check 2>&1)" || rc=$?

case "$rc" in
    0) exit 0 ;;
    1) : ;;  # stale — handled below
    2)
        # "Could not verify", not "stale". A developer whose PATH has no `ic`
        # with the autonomy subcommand cannot check this and must not be blocked
        # by it. Say so plainly rather than failing on an inconclusive result.
        echo "pre-commit: could not verify docs/canon/autonomy.md's position block." >&2
        printf '%s\n' "$output" | sed 's/^/            /' >&2
        exit 0
        ;;
    *)
        echo "pre-commit: gen-autonomy-position.py failed (rc=$rc):" >&2
        echo "$output" >&2
        exit "$rc"
        ;;
esac

if [ "$strict" -eq 0 ]; then
    echo "pre-commit: note — docs/canon/autonomy.md's position block is stale." >&2
    echo "            Not blocking: this commit does not touch the autonomy machinery." >&2
    echo "            Refresh with: python3 scripts/gen-autonomy-position.py" >&2
    exit 0
fi

cat >&2 <<EOF
pre-commit: docs/canon/autonomy.md's generated position block is stale, and this
            commit touches the machinery it describes.

            The block would then claim a delegation level or streak that is not
            what the running system reports.

            Fix:
              python3 scripts/gen-autonomy-position.py
              git add docs/canon/autonomy.md

            The regeneration is deliberately not auto-staged: the block reflects
            live kernel state, and sweeping an unrelated state change into your
            commit is exactly the surprise this hook exists to prevent.
EOF
exit 1
