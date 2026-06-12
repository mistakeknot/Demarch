#!/usr/bin/env bash
# bd-create-checked.sh — wrapper around `bd create` with dup detection.
#
# Runs scripts/lib-bd-dup-check.py against open beads, prints any candidates
# above the threshold, and prompts for confirmation before creating.
#
# Usage:
#   bd-create-checked.sh -t task -p 2 --title "..." --description "..." [--labels x,y]
#
# All args are forwarded to `bd create`. The wrapper extracts --title and
# --description for the dup check.
#
# Bypass: set BD_DUP_CHECK_SKIP=1 to disable, or set BD_DUP_AUTO_PROCEED=1
# to print warnings without prompting (useful for CI/non-tty contexts).
#
# Per sylveste-a4oj.9.3.
set -u

REPO_ROOT="${REPO_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
LIB="${REPO_ROOT}/scripts/lib-bd-dup-check.py"

# Cloud-guard: creating beads from cloud doesn't survive the ephemeral
# container. Refuse loudly so the agent files the bead via PR description
# instead of silently losing the write.
GUARD_LIB="${REPO_ROOT}/scripts/lib-cloud-guard.sh"
if [[ -r "$GUARD_LIB" ]]; then
    # shellcheck source=lib-cloud-guard.sh
    source "$GUARD_LIB"
    if cloud_session; then
        echo "bd-create-checked: refusing to create in cloud read-only mode." >&2
        echo "  Beads writes don't survive the ephemeral container — note the candidate" >&2
        echo "  in the PR description and let the workstation file it." >&2
        echo "  (Override: bash scripts/install-bd-cloud.sh && bd create ...)" >&2
        exit 1
    fi
fi

if [[ "${BD_DUP_CHECK_SKIP:-0}" == "1" ]]; then
    exec bd create "$@"
fi

# Extract --title (and --description, --labels) from args without disturbing
# the original arg list. Standard getopts can't handle long options cleanly
# in bash, so we walk the args.
TITLE=""
DESC=""
LABELS=""
prev=""
for arg in "$@"; do
    case "$prev" in
        --title) TITLE="$arg" ;;
        --description) DESC="$arg" ;;
        --labels|-l) LABELS="$arg" ;;
    esac
    case "$arg" in
        --title=*) TITLE="${arg#--title=}" ;;
        --description=*) DESC="${arg#--description=}" ;;
        --labels=*) LABELS="${arg#--labels=}" ;;
        -l=*) LABELS="${arg#-l=}" ;;
    esac
    prev="$arg"
done

# Without a title there's nothing to dup-check on; let bd handle the missing
# arg and report its own error.
if [[ -z "$TITLE" ]] || [[ ! -f "$LIB" ]]; then
    exec bd create "$@"
fi

# Run the dup check. Capture stderr (where it prints warnings) and exit code.
# stdout is unused unless --json is passed.
warn_out=$(python3 "$LIB" \
    --title "$TITLE" \
    ${DESC:+--description "$DESC"} \
    ${LABELS:+--labels "$LABELS"} \
    2>&1 >/dev/null) || rc=$? || rc=0
rc=${rc:-0}

if [[ "$rc" -eq 0 ]]; then
    # No candidates above threshold — proceed.
    exec bd create "$@"
fi

# Candidates surfaced. Print them so the user can see.
printf '%s\n' "$warn_out" >&2

# Auto-proceed mode: print warnings, create anyway.
if [[ "${BD_DUP_AUTO_PROCEED:-0}" == "1" ]]; then
    echo "BD_DUP_AUTO_PROCEED=1 — creating despite candidates" >&2
    exec bd create "$@"
fi

# No TTY: cannot prompt; default to NOT creating (safer than auto-create on
# possible dup) and tell the user how to override.
if [[ ! -t 0 ]] || [[ ! -t 2 ]]; then
    echo "" >&2
    echo "No TTY available; refusing to create. Set BD_DUP_AUTO_PROCEED=1 to override," >&2
    echo "or BD_DUP_CHECK_SKIP=1 to bypass the check entirely." >&2
    exit 1
fi

# TTY available — prompt.
read -r -p "Create anyway? [y/N] " resp </dev/tty
case "$resp" in
    [yY]|[yY][eE][sS])
        exec bd create "$@"
        ;;
    *)
        echo "Cancelled. Use \`bd show <id>\` to inspect the candidate(s) above," >&2
        echo "or re-run with BD_DUP_CHECK_SKIP=1 to bypass." >&2
        exit 1
        ;;
esac
