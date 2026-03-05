#!/usr/bin/env bash
# Beads recovery script: kills zombies, stops orphan monitors, re-inits from JSONL
# Usage: bash .beads/recover.sh
set -euo pipefail

echo "=== Beads Recovery ==="

# 1. Kill all idle-monitors across all projects
echo "Killing idle-monitors..."
ps aux | grep "bd dolt idle-monitor" | grep -v grep | awk '{print $2}' | xargs -r kill 2>/dev/null || true

# 2. Kill all dolt sql-servers
echo "Killing dolt servers..."
ps aux | grep "dolt sql-server" | grep -v grep | awk '{print $2}' | xargs -r kill 2>/dev/null || true

# 3. Use bd's built-in killall (v0.58+)
sleep 2
bd dolt killall 2>/dev/null || true

# 4. Verify JSONL exists and has content
JSONL=".beads/issues.jsonl"
if [[ ! -f "$JSONL" ]]; then
    echo "ERROR: $JSONL not found. Cannot recover."
    exit 1
fi
LINES=$(wc -l < "$JSONL")
echo "JSONL has $LINES issues"

# 5. Re-init from JSONL
echo "Re-initializing from JSONL..."
bd dolt stop 2>/dev/null || true
sleep 2
bd init --from-jsonl --force --prefix iv

# 6. Verify
echo ""
echo "=== Verification ==="
bd list 2>&1 | wc -l
echo "issues loaded"
bd dolt status 2>&1
echo ""
echo "Recovery complete."
