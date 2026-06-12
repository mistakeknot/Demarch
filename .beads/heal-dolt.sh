#!/usr/bin/env bash
# heal-dolt.sh — Fix stale Dolt locks and ensure server is running.
# Called by SessionStart hook. Safe to run anytime.
# Guard against infinite recursion: bd auto_heal calls this, and this calls bd
[[ -n "${BD_HEALING:-}" ]] && exit 0

set -euo pipefail

BEADS_DIR="${1:-.beads}"
DOLT_DIR="$BEADS_DIR/dolt"
DB_DIR="$DOLT_DIR/Sylveste"

# Cloud detection lives in the shared guard lib so every bd-invoking script
# diagnoses the same way (see PR #19 follow-up — `command -v bd` is an
# unreliable cloud proxy because a workstation with a broken PATH gets
# misdiagnosed). Distinguish cloud (intent: read-only beads, skip silently)
# from workstation-missing-bd (real bug, log actionably).
GUARD_LIB="$(dirname "$BEADS_DIR")/scripts/lib-cloud-guard.sh"
if [[ -r "$GUARD_LIB" ]]; then
    # shellcheck source=../scripts/lib-cloud-guard.sh
    source "$GUARD_LIB"
    if cloud_session; then
        cloud_log_skip "heal-dolt"
        exit 0
    fi
    if ! command -v bd >/dev/null 2>&1; then
        workstation_log_missing_bd "heal-dolt"
        exit 0
    fi
else
    # lib missing — fall back to legacy behavior (bd-presence only).
    if ! command -v bd >/dev/null 2>&1; then
        echo "heal-dolt: bd not on PATH (lib-cloud-guard.sh also missing) — skipping" >&2
        exit 0
    fi
fi

# Arm the recursion guard only now that we know bd will actually run.
export BD_HEALING=1

# Bounded budget for the whole heal operation (anytime stopping criterion).
# Override with HEAL_DOLT_BUDGET_S for tuning. The default 5s captures ~95%
# of healthy cold-starts; beyond that, fall through to the JSONL-fallback
# path rather than block the user's first prompt indefinitely.
HEAL_BUDGET_S="${HEAL_DOLT_BUDGET_S:-5}"

heal_lock() {
    local info_file="$1"
    [[ -f "$info_file" ]] || return 0

    local pid
    pid=$(cut -d: -f1 "$info_file" 2>/dev/null) || return 0
    # Defensive parse: bare PID files (no colon) make `cut` return the whole
    # line. Require digits only before passing to kill.
    [[ "$pid" =~ ^[0-9]+$ ]] || return 0

    # Check if the PID is actually alive
    if ! kill -0 "$pid" 2>/dev/null; then
        echo "heal-dolt: removing stale lock (PID $pid dead): $info_file" >&2
        rm -f "$info_file"
        return 1  # signal that we healed something
    fi
    return 0
}

kill_orphans() {
    # Kill dolt sql-server processes not tracked by our PID file
    local tracked_pid=""
    [[ -f "$BEADS_DIR/dolt-server.pid" ]] && tracked_pid=$(cat "$BEADS_DIR/dolt-server.pid" 2>/dev/null)

    local orphans killed
    orphans=$(pgrep -f "dolt sql-server" 2>/dev/null || true)
    killed=()
    for pid in $orphans; do
        if [[ "$pid" != "$tracked_pid" ]]; then
            echo "heal-dolt: killing orphaned dolt process $pid" >&2
            kill "$pid" 2>/dev/null || true
            killed+=("$pid")
        fi
    done

    # Closed-loop wait: poll until killed PIDs are gone, up to 2s. Replaces a
    # fixed `sleep 1` that was either pure latency (nominal load) or too short
    # (slow disk + many orphans). Final SIGKILL on stragglers.
    [[ ${#killed[@]} -eq 0 ]] && return 0
    local i
    for i in $(seq 1 20); do
        local alive=0
        for pid in "${killed[@]}"; do
            kill -0 "$pid" 2>/dev/null && alive=1
        done
        [[ "$alive" -eq 0 ]] && return 0
        sleep 0.1
    done
    for pid in "${killed[@]}"; do
        kill -0 "$pid" 2>/dev/null && kill -KILL "$pid" 2>/dev/null || true
    done
}

# Phase 1: Remove stale sql-server.info files
healed=0
heal_lock "$DOLT_DIR/.dolt/sql-server.info" || healed=1
heal_lock "$DB_DIR/.dolt/sql-server.info" || healed=1

# Phase 2: Kill orphaned dolt processes (only if we found stale locks)
if [[ "$healed" -eq 1 ]]; then
    kill_orphans
fi

# Phase 3: Ensure Dolt is running. Bound the start with a budget — if Dolt
# can't come up within HEAL_BUDGET_S the downstream `bd stats || fallback`
# in settings.json picks up the slack rather than blocking the user.
if ! bd dolt status >/dev/null 2>&1; then
    echo "heal-dolt: starting Dolt server (budget ${HEAL_BUDGET_S}s)" >&2
    if ! out=$(timeout "${HEAL_BUDGET_S}" bd dolt start 2>&1); then
        rc=$?
        # timeout(1) returns 124 on timeout, 125+ on its own errors, otherwise
        # propagates the child's code.
        if [[ "$rc" -eq 124 ]]; then
            echo "heal-dolt: bd dolt start exceeded ${HEAL_BUDGET_S}s budget; falling through" >&2
        else
            # Surface full error context (not just `tail -1`) for diagnosis.
            echo "heal-dolt: bd dolt start failed (rc=$rc):" >&2
            printf '%s\n' "$out" >&2
        fi
    else
        # Readiness gap: `bd dolt status` (port open) trails Dolt accepting
        # queries by ~500ms-2s. Poll `bd stats` until success or 2s, so the
        # next caller doesn't race.
        for _ in $(seq 1 20); do
            bd stats >/dev/null 2>&1 && break
            sleep 0.1
        done
        # echo back the start tail for observability
        printf '%s\n' "$out" | tail -1 >&2
    fi
fi
