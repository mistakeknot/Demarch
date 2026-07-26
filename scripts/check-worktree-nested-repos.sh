#!/usr/bin/env bash
#
# check-worktree-nested-repos — worktree-first contract doctor check (n2ma).
#
# The Sylveste root repo gitignores ~115 independent nested git repos (most of
# interverse/, all of core/, apps/, research/). A git worktree of the ROOT repo
# checks out only tracked files, so those nested repos are ABSENT from it — a
# root worktree materializes almost none of the plugins. Operations that expect
# them (ic publish waves, cross-repo sweeps) then silently no-op.
#
# This check detects when the current directory is a ROOT-repo worktree and
# warns which nested repos are absent, so the hazard fails loud. It is a no-op
# (exit 0, silent) in the main checkout or in a nested-repo worktree.
#
# See docs/guide-worktree-first-coordination.md §5 and §7.
#
# Usage:
#   scripts/check-worktree-nested-repos.sh [--json] [--verbose]
#
# Environment overrides for tests:
#   SYLVESTE_ROOT        — treat this path as the main checkout root
#   WORKTREE_CHECK_CWD   — evaluate as if the session ran here (default: $PWD)
#
# Exit codes:
#   0 — not in a root worktree, OR in one with no absent nested repos
#   1 — in a root worktree with nested repos absent (warning surfaced)
#   2 — usage error

set -euo pipefail

JSON_OUT=false
VERBOSE=false
for arg in "$@"; do
    case "$arg" in
        --json) JSON_OUT=true ;;
        --verbose|-v) VERBOSE=true ;;
        --help|-h) sed -n '2,/^$/p' "$0" | sed 's/^# \?//'; exit 0 ;;
        *) echo "check-worktree-nested-repos: unknown flag: $arg" >&2; exit 2 ;;
    esac
done

CWD="${WORKTREE_CHECK_CWD:-$PWD}"

# Resolve the git common dir (points at the MAIN repo's .git even from a worktree)
# and the current worktree's own toplevel.
common_dir="$(git -C "$CWD" rev-parse --git-common-dir 2>/dev/null || true)"
git_dir="$(git -C "$CWD" rev-parse --git-dir 2>/dev/null || true)"
toplevel="$(git -C "$CWD" rev-parse --show-toplevel 2>/dev/null || true)"

if [[ -z "$common_dir" || -z "$toplevel" ]]; then
    # Not in a git repo — nothing to assert.
    "$JSON_OUT" && echo '{"in_worktree":false,"absent":[],"status":"ok"}'
    exit 0
fi

# In a linked worktree, git-dir != git-common-dir. In the main checkout they are
# the same path (both resolve to <root>/.git).
abs_common="$(cd "$(dirname "$common_dir")" 2>/dev/null && pwd)/$(basename "$common_dir")" || abs_common="$common_dir"
in_worktree=false
if [[ "$git_dir" != "$common_dir" ]]; then
    in_worktree=true
fi

# The MAIN checkout root is the parent of the common .git dir.
main_root="$(cd "$toplevel" && git rev-parse --path-format=absolute --git-common-dir 2>/dev/null | xargs dirname 2>/dev/null || true)"
[[ -z "$main_root" ]] && main_root="$(dirname "$common_dir")"
main_root="${SYLVESTE_ROOT:-$main_root}"

if [[ "$in_worktree" != true ]]; then
    "$JSON_OUT" && echo '{"in_worktree":false,"absent":[],"status":"ok"}'
    exit 0
fi

# Are we in a worktree of the ROOT Sylveste repo, or of a nested repo?
# Heuristic: the main repo root contains interverse/ AND core/ AND a .beads/.
is_root_repo=false
if [[ -d "$main_root/interverse" && -d "$main_root/core" ]]; then
    is_root_repo=true
fi
if [[ "$is_root_repo" != true ]]; then
    # Worktree of a nested repo — the per-repo-worktree happy path. No warning.
    "$JSON_OUT" && echo '{"in_worktree":true,"root_repo":false,"absent":[],"status":"ok"}'
    exit 0
fi

# Enumerate nested git repos present in the MAIN checkout that are gitignored by
# root (hence absent from this worktree). Compare against what THIS worktree has.
mapfile -t nested < <(
    cd "$main_root" 2>/dev/null || exit 0
    find interverse core apps research masaq -maxdepth 2 -name .git \
        \( -type d -o -type f \) 2>/dev/null \
        | sed 's|/\.git$||' \
        | while read -r d; do
            git check-ignore "$d" >/dev/null 2>&1 && echo "$d"
          done \
        | sort -u
)

absent=()
for repo in "${nested[@]}"; do
    # Absent from the worktree if the path doesn't exist OR isn't a git repo here.
    if [[ ! -e "$toplevel/$repo/.git" ]]; then
        absent+=("$repo")
    fi
done

if (( ${#absent[@]} == 0 )); then
    "$JSON_OUT" && echo '{"in_worktree":true,"root_repo":true,"absent":[],"status":"ok"}'
    exit 0
fi

if "$JSON_OUT"; then
    printf '{"in_worktree":true,"root_repo":true,"absent":['
    for i in "${!absent[@]}"; do
        (( i > 0 )) && printf ','
        printf '"%s"' "${absent[$i]}"
    done
    printf '],"status":"warn"}\n'
else
    echo "WARNING: this is a ROOT-repo worktree ($toplevel)." >&2
    echo "  ${#absent[@]} nested repos are ABSENT here and will not be seen by" >&2
    echo "  publish waves or cross-repo sweeps. Run those from the main checkout:" >&2
    echo "    $main_root" >&2
    if "$VERBOSE"; then
        printf '  absent: %s\n' "${absent[*]}" >&2
    else
        printf '  absent (first 8): %s ...\n' "$(printf '%s ' "${absent[@]:0:8}")" >&2
    fi
fi
exit 1
