#!/usr/bin/env bash
# heal-dolt.sh — Fix stale Dolt locks and ensure server is running.
# Called by SessionStart hook. Safe to run anytime.
# Guard against infinite recursion: bd auto_heal calls this, and this calls bd
[[ -n "${BD_HEALING:-}" ]] && exit 0
export BD_HEALING=1

set -euo pipefail

BEADS_DIR="${1:-.beads}"
DOLT_DIR="$BEADS_DIR/dolt"
DB_DIR="$DOLT_DIR/Sylveste"

# If bd isn't on PATH, exit cleanly. This is the expected state in
# cloud_default remote environments, where sessions read .beads/issues.jsonl
# directly as a flat file rather than running the bd CLI. See CLAUDE.md
# "Cloud Sessions" for the read-only-beads convention. For tasks that
# genuinely need the bd CLI in a cloud container, run scripts/install-bd-cloud.sh
# manually before starting work.
if ! command -v bd >/dev/null 2>&1; then
    echo "heal-dolt: bd not on PATH — skipping Dolt healing (cloud read-only mode)" >&2
    exit 0
fi

heal_lock() {
    local info_file="$1"
    [[ -f "$info_file" ]] || return 0

    local pid
    pid=$(cut -d: -f1 "$info_file" 2>/dev/null) || return 0
    [[ -z "$pid" ]] && return 0

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

    local orphans
    orphans=$(pgrep -f "dolt sql-server" 2>/dev/null || true)
    for pid in $orphans; do
        if [[ "$pid" != "$tracked_pid" ]]; then
            echo "heal-dolt: killing orphaned dolt process $pid" >&2
            kill "$pid" 2>/dev/null || true
        fi
    done
}

# Phase 1: Remove stale sql-server.info files
healed=0
heal_lock "$DOLT_DIR/.dolt/sql-server.info" || healed=1
heal_lock "$DB_DIR/.dolt/sql-server.info" || healed=1

# Phase 2: Kill orphaned dolt processes (only if we found stale locks)
if [[ "$healed" -eq 1 ]]; then
    kill_orphans
    sleep 1
fi

# Phase 3: Ensure Dolt is running
if ! bd dolt status >/dev/null 2>&1; then
    echo "heal-dolt: starting Dolt server" >&2
    bd dolt start 2>&1 | tail -1 >&2
fi
