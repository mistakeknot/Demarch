#!/usr/bin/env bash
# Push beads dolt database to filesystem remote.
# Workaround for `bd dolt push` "no store available" error (bd v0.56.1).
# Uses SQL-level CALL dolt_push() via the running dolt sql-server.
set -euo pipefail

DB_DIR="/home/mk/projects/Demarch/.beads/dolt/beads_iv"
cd "$DB_DIR"

output=$(/home/mk/.local/bin/dolt sql -q "CALL dolt_push('origin', 'main')" 2>&1)
status=$(echo "$output" | grep -oP '(?<=\| )\d+(?= +\|)' | head -1)

if [[ "$status" == "0" ]]; then
    echo "beads push: ok"
else
    echo "beads push: failed"
    echo "$output"
    exit 1
fi
