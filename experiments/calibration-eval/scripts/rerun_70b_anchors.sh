#!/usr/bin/env bash
# Re-run the 70B public-benchmark anchors that failed before the hf_dataset fix.
# GPQA intentionally omitted: gated HF dataset, no token in this environment.
set -uo pipefail
cd "$(dirname "$0")/.."
source .venv/bin/activate
M="openai-api/nous/nousresearch/hermes-4-70b"
inspect eval src/tasks.py@calibration_mmlu       --model "$M" --limit 300 --log-dir runs
inspect eval src/tasks.py@calibration_truthfulqa --model "$M"             --log-dir runs
inspect eval src/tasks.py@calibration_gsm8k      --model "$M" --limit 300 --log-dir runs
echo "ANCHORS-70B DONE"
