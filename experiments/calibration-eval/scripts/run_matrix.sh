#!/usr/bin/env bash
# Step-1 full run matrix per RUNBOOK.md §3.
# Ladder verified against $NOUS_BASE_URL/models on 2026-06-11: the portal serves
# exactly two Hermes rungs. Logprob probe fell back -> logprob arm skipped.
set -uo pipefail
cd "$(dirname "$0")/.."
source .venv/bin/activate

LADDER=(
  "openai-api/nous/nousresearch/hermes-4-70b"
  "openai-api/nous/nousresearch/hermes-4-405b"
)

CUSTOM=src/tasks.py@calibration_custom
for M in "${LADDER[@]}"; do
  echo "=== $M ==="
  inspect eval $CUSTOM                          --model "$M" --log-dir runs
  inspect eval $CUSTOM -T elicitation=sampling  --model "$M" --log-dir runs
  inspect eval $CUSTOM -T reflect=true          --model "$M" --log-dir runs

  inspect eval src/tasks.py@calibration_mmlu       --model "$M" --limit 300 --log-dir runs
  inspect eval src/tasks.py@calibration_gpqa       --model "$M"             --log-dir runs
  inspect eval src/tasks.py@calibration_truthfulqa --model "$M"             --log-dir runs
  inspect eval src/tasks.py@calibration_gsm8k      --model "$M" --limit 300 --log-dir runs
done
echo "MATRIX DONE"
