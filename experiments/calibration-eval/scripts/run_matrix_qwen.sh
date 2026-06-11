#!/usr/bin/env bash
# Qwen3.5 5-rung ladder per the strengthen-Step-1 plan.
# Logprob arm dropped: catalog advertises `logprobs` for these models but the
# routing returns null (verified by direct curl 2026-06-11); only OpenAI-proxied
# models actually deliver logprobs on this portal.
set -uo pipefail
cd "$(dirname "$0")/.."
source .venv/bin/activate

LADDER=(
  "openai-api/nous/qwen/qwen3.5-9b"
  "openai-api/nous/qwen/qwen3.5-27b"
  "openai-api/nous/qwen/qwen3.5-35b-a3b"
  "openai-api/nous/qwen/qwen3.5-122b-a10b"
  "openai-api/nous/qwen/qwen3.5-397b-a17b"
)

CUSTOM=src/tasks.py@calibration_custom
for M in "${LADDER[@]}"; do
  echo "=== $M ==="
  inspect eval $CUSTOM                          --model "$M" --log-dir runs
  inspect eval $CUSTOM -T elicitation=sampling  --model "$M" --log-dir runs
  inspect eval $CUSTOM -T reflect=true          --model "$M" --log-dir runs

  inspect eval src/tasks.py@calibration_mmlu       --model "$M" --limit 300 --log-dir runs
  # calibration_gpqa omitted: gated HF dataset, no HF token in this environment
  inspect eval src/tasks.py@calibration_truthfulqa --model "$M"             --log-dir runs
  inspect eval src/tasks.py@calibration_gsm8k      --model "$M" --limit 300 --log-dir runs
done
echo "QWEN MATRIX DONE"
