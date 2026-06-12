#!/usr/bin/env bash
# lib-cloud-guard.sh — sourceable detection for Claude Code remote (cloud)
# environments. Used by every script that invokes `bd` so they degrade the
# same way: cleanly + read-only on cloud, loudly + actionably on workstation.
#
# Usage (from a calling script):
#
#   SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
#   source "$SCRIPT_DIR/lib-cloud-guard.sh"
#
#   if cloud_session; then
#       cloud_log_skip "audit-roadmap-beads"
#       exit 0
#   fi
#
#   if ! command -v bd >/dev/null 2>&1; then
#       workstation_log_missing_bd "audit-roadmap-beads"
#       exit 0
#   fi
#
# Detection: we treat the environment as "cloud" iff Claude Code's documented
# remote-env signals are set. We deliberately do NOT use `command -v bd` as
# a cloud proxy — a workstation with a temporarily broken PATH would be
# misdiagnosed and the actual bug (broken PATH) would be hidden behind a
# misleading "cloud mode" message. See PR #19 follow-up review.

# Returns 0 if the current shell is a Claude Code cloud_default session.
cloud_session() {
    [[ "${CLAUDE_CODE_REMOTE_ENVIRONMENT_TYPE:-}" == cloud_default ]] && return 0
    [[ "${IS_SANDBOX:-}" == "yes" ]] && return 0
    return 1
}

# One-line stderr message: "cloud read-only mode, skipping <op>". Use when the
# guard wants to no-op a bd-dependent operation in a cloud session.
cloud_log_skip() {
    local op="${1:-operation}"
    echo "${op}: cloud read-only mode (CLAUDE_CODE_REMOTE_ENVIRONMENT_TYPE=${CLAUDE_CODE_REMOTE_ENVIRONMENT_TYPE:-unset}, IS_SANDBOX=${IS_SANDBOX:-unset}) — skipping bd-dependent path" >&2
}

# One-line stderr message: "bd missing on workstation, this is a real bug".
# Use when the guard determines the environment is NOT cloud but bd is still
# absent from PATH. Distinct message so the diagnostic is actionable.
workstation_log_missing_bd() {
    local op="${1:-operation}"
    echo "${op}: bd not on PATH (and not a cloud session) — install bd (https://github.com/gastownhall/beads) or fix your PATH" >&2
}
