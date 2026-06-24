#!/usr/bin/env bash
# heal-dolt.sh — Fix stale Dolt locks and ensure server is running.
# Called by SessionStart hook. Safe to run anytime.
# Guard against infinite recursion: bd auto_heal calls this, and this calls bd
[[ -n "${BD_HEALING:-}" ]] && exit 0

set -euo pipefail

BEADS_DIR="${1:-.beads}"
DOLT_DIR="$BEADS_DIR/dolt"
DB_DIR="$DOLT_DIR/Sylveste"
PORT_FILE="$BEADS_DIR/dolt-server.port"
SERVER_INFO="$DOLT_DIR/.dolt/sql-server.info"
DB_SERVER_INFO="$DB_DIR/.dolt/sql-server.info"

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

if [[ "${CODEX_SANDBOX_NETWORK_DISABLED:-}" == "1" ]]; then
    echo "heal-dolt: Codex sandbox cannot probe localhost Dolt reliably — skipping" >&2
    exit 0
fi

# Arm the recursion guard only now that we know bd will actually run.
export BD_HEALING=1

# Bounded budget for the whole heal operation (anytime stopping criterion).
# Override with HEAL_DOLT_BUDGET_S for tuning. The default 5s captures ~95%
# of healthy cold-starts; beyond that, fall through to the JSONL-fallback
# path rather than block the user's first prompt indefinitely.
HEAL_BUDGET_S="${HEAL_DOLT_BUDGET_S:-5}"

read_live_server_info() {
    local info_file pid port rest
    for info_file in "$SERVER_INFO" "$DB_SERVER_INFO"; do
        [[ -f "$info_file" ]] || continue
        IFS=: read -r pid port rest <"$info_file" || continue
        [[ "$pid" =~ ^[0-9]+$ ]] || continue
        [[ "$port" =~ ^[0-9]+$ ]] || continue
        if kill -0 "$pid" 2>/dev/null; then
            printf '%s:%s:%s\n' "$pid" "$port" "$info_file"
            return 0
        fi
    done
    return 1
}

tracked_server_pid() {
    local pid=""
    if [[ -f "$BEADS_DIR/dolt-server.pid" ]]; then
        pid=$(cat "$BEADS_DIR/dolt-server.pid" 2>/dev/null || true)
        [[ "$pid" =~ ^[0-9]+$ ]] && printf '%s\n' "$pid" && return 0
    fi

    local live
    live=$(read_live_server_info 2>/dev/null) || return 1
    printf '%s\n' "${live%%:*}"
}

recover_port_file() {
    local live pid port info_file current_port
    live=$(read_live_server_info 2>/dev/null) || return 0
    pid="${live%%:*}"
    live="${live#*:}"
    port="${live%%:*}"
    info_file="${live#*:}"

    current_port=""
    [[ -f "$PORT_FILE" ]] && current_port=$(cat "$PORT_FILE" 2>/dev/null || true)
    if [[ "$current_port" != "$port" ]]; then
        printf '%s\n' "$port" >"$PORT_FILE"
        echo "heal-dolt: recovered port $port from $info_file (PID $pid)" >&2
    fi
}

restart_tracked_server() {
    local live pid port
    live=$(read_live_server_info 2>/dev/null) || return 1
    pid="${live%%:*}"
    live="${live#*:}"
    port="${live%%:*}"

    echo "heal-dolt: restarting unresponsive tracked Dolt server PID $pid on port $port" >&2
    kill "$pid" 2>/dev/null || true

    local i
    for i in $(seq 1 20); do
        kill -0 "$pid" 2>/dev/null || break
        sleep 0.1
    done
    kill -0 "$pid" 2>/dev/null && kill -KILL "$pid" 2>/dev/null || true

    rm -f "$SERVER_INFO" "$DB_SERVER_INFO" "$PORT_FILE" "$BEADS_DIR/dolt-server.pid"
}

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
    local tracked_pid
    tracked_pid=$(tracked_server_pid 2>/dev/null || true)
    if [[ -z "$tracked_pid" ]]; then
        echo "heal-dolt: no tracked Dolt server PID; skipping orphan sweep" >&2
        return 0
    fi

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
recover_port_file

# Phase 2: Kill orphaned dolt processes (only if we found stale locks)
if [[ "$healed" -eq 1 ]]; then
    kill_orphans
fi

# Phase 3: Ensure Dolt is running. Bound the start with a budget — if Dolt
# can't come up within HEAL_BUDGET_S the downstream `bd stats || fallback`
# in settings.json picks up the slack rather than blocking the user.
if ! bd --sandbox dolt test >/dev/null 2>&1; then
    restart_tracked_server || true
    echo "heal-dolt: starting Dolt server (budget ${HEAL_BUDGET_S}s)" >&2
    if ! out=$(timeout "${HEAL_BUDGET_S}" bd --sandbox dolt start 2>&1); then
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
            bd --sandbox stats >/dev/null 2>&1 && break
            sleep 0.1
        done
        # echo back the start tail for observability
        printf '%s\n' "$out" | tail -1 >&2
    fi
fi
