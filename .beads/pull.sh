#!/usr/bin/env bash
# Pull beads dolt database from filesystem remote.
# Workaround for `bd dolt pull` "no store available" error (bd v0.56.1).
set -euo pipefail

DB_DIR="/home/mk/projects/Demarch/.beads/dolt/beads_iv"
cd "$DB_DIR"

output=$(/home/mk/.local/bin/dolt sql -q "CALL dolt_pull('origin')" 2>&1)
echo "beads pull: ok"
echo "$output" | tail -3
