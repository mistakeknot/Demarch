#!/usr/bin/env bash
# One ladder rung of the Step-1 matrix (model passed as $1); used to run the
# remaining Qwen rungs in parallel after rung 1 validated sequentially.
set -uo pipefail
cd "$(dirname "$0")/.."
source .venv/bin/activate

M="$1"
CUSTOM=src/tasks.py@calibration_custom
echo "=== $M ==="
inspect eval $CUSTOM                          --model "$M" --log-dir runs
inspect eval $CUSTOM -T elicitation=sampling  --model "$M" --log-dir runs
inspect eval $CUSTOM -T reflect=true          --model "$M" --log-dir runs
inspect eval src/tasks.py@calibration_mmlu       --model "$M" --limit 300 --log-dir runs
inspect eval src/tasks.py@calibration_truthfulqa --model "$M"             --log-dir runs
inspect eval src/tasks.py@calibration_gsm8k      --model "$M" --limit 300 --log-dir runs
echo "RUNG DONE: $M"
