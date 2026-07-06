#!/usr/bin/env bash
# Longitudinal OYRF cost-calibration exporter.
# Public output: data/cost-trajectory.csv
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DEFAULT_OUTPUT="$ROOT/data/cost-trajectory.csv"
OUTPUT="$DEFAULT_OUTPUT"
WINDOW_DAYS="${OYRF_WINDOW_DAYS:-7}"
SINCE=""
DRY_RUN=0
TIMEOUT_SECONDS="${OYRF_COST_QUERY_TIMEOUT_SECONDS:-20}"
# Interstat's cost-query.sh is private tooling and deliberately gitignored
# (see .gitignore: interverse/), so it is absent on any fresh clone/CI
# checkout by design. OYRF_COST_QUERY_OVERRIDE lets callers (tests, or
# alternate local setups) point at a substitute script without needing
# the real private path to exist.
COST_QUERY="${OYRF_COST_QUERY_OVERRIDE:-$ROOT/interverse/interstat/scripts/cost-query.sh}"

usage() {
  cat <<'USAGE'
Usage: bash estimate-costs.sh [--dry-run] [--output PATH] [--window-days N] [--since ISO8601]

Append one OYRF longitudinal cost-calibration row to cost-trajectory.csv.

Options:
  --dry-run          Write a deterministic fixture row; never reads private Interstat data.
  --output PATH      CSV path to write/append. Defaults to data/cost-trajectory.csv.
  --window-days N    Lookback window when deriving --since. Defaults to 7.
  --since ISO8601    Explicit Interstat lower bound, e.g. 2026-04-23T00:00:00Z.
  --help             Show this help.

The live mode calls interverse/interstat/scripts/cost-query.sh baseline with a
short timeout and falls back to an interstat-empty public row when private metrics
are unavailable, so CI can run safely without credentials or local databases.
USAGE
}

while [ "$#" -gt 0 ]; do
  case "$1" in
    --dry-run)
      DRY_RUN=1
      ;;
    --output=*)
      OUTPUT="${1#--output=}"
      ;;
    --output)
      shift
      OUTPUT="${1:?--output requires a path}"
      ;;
    --window-days=*)
      WINDOW_DAYS="${1#--window-days=}"
      ;;
    --window-days)
      shift
      WINDOW_DAYS="${1:?--window-days requires an integer}"
      ;;
    --since=*)
      SINCE="${1#--since=}"
      ;;
    --since)
      shift
      SINCE="${1:?--since requires an ISO-8601 timestamp}"
      ;;
    --help|-h)
      usage
      exit 0
      ;;
    *)
      echo "error: unknown argument: $1" >&2
      usage >&2
      exit 2
      ;;
  esac
  shift
done

case "$WINDOW_DAYS" in
  ''|*[!0-9]*)
    echo "error: --window-days must be a non-negative integer" >&2
    exit 2
    ;;
esac

if [ -z "$SINCE" ]; then
  SINCE="$(python3 - "$WINDOW_DAYS" <<'PY'
from datetime import datetime, timedelta, timezone
import sys
window_days = int(sys.argv[1])
print((datetime.now(timezone.utc) - timedelta(days=window_days)).strftime("%Y-%m-%dT%H:%M:%SZ"))
PY
)"
fi

if [[ "$OUTPUT" != /* ]]; then
  OUTPUT="$PWD/$OUTPUT"
fi
mkdir -p "$(dirname "$OUTPUT")"

CAPTURED_AT="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
RAW_JSON="[]"
SOURCE_HINT="interstat-empty"

if [ "$DRY_RUN" -eq 1 ]; then
  RAW_JSON='{}'
  SOURCE_HINT="dry-run-fixture"
elif [ ! -x "$COST_QUERY" ]; then
  echo "warning: Interstat cost query not executable at $COST_QUERY; writing interstat-empty row" >&2
elif ! command -v timeout >/dev/null 2>&1; then
  echo "warning: timeout(1) unavailable; skipping live Interstat query and writing interstat-empty row" >&2
else
  if RAW_JSON="$(timeout "$TIMEOUT_SECONDS" "$COST_QUERY" baseline --since="$SINCE" --repo="$ROOT" 2>/dev/null)"; then
    SOURCE_HINT="interstat"
  else
    rc=$?
    echo "warning: Interstat cost query failed or timed out (rc=$rc); writing interstat-empty row" >&2
    RAW_JSON="[]"
    SOURCE_HINT="interstat-empty"
  fi
fi

if [ -z "${RAW_JSON//[[:space:]]/}" ]; then
  RAW_JSON="[]"
  SOURCE_HINT="interstat-empty"
fi

OYRF_OUTPUT="$OUTPUT" \
OYRF_RAW_JSON="$RAW_JSON" \
OYRF_CAPTURED_AT="$CAPTURED_AT" \
OYRF_WINDOW_DAYS="$WINDOW_DAYS" \
OYRF_SOURCE_HINT="$SOURCE_HINT" \
python3 <<'PY'
from __future__ import annotations

import csv
import json
import os
from pathlib import Path
from typing import Any

HEADER = [
    "captured_at",
    "window_days",
    "session_count",
    "total_tokens",
    "input_tokens",
    "output_tokens",
    "total_cost_usd",
    "cost_per_session_usd",
    "source",
]


def as_int(value: Any) -> int:
    if value in (None, ""):
        return 0
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return 0


def as_float(value: Any) -> float:
    if value in (None, ""):
        return 0.0
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def first_number(mapping: dict[str, Any], *names: str) -> Any:
    for name in names:
        value = mapping.get(name)
        if value not in (None, "") and not isinstance(value, (dict, list)):
            return value
    return 0


def nested_mapping(mapping: dict[str, Any], name: str) -> dict[str, Any]:
    value = mapping.get(name)
    return value if isinstance(value, dict) else {}


def add_metrics(target: dict[str, float], item: dict[str, Any]) -> None:
    measurement_window = nested_mapping(item, "measurement_window")
    token_metrics = nested_mapping(item, "tokens")

    session_count = as_int(first_number(item, "session_count", "sessions", "total_sessions"))
    if not session_count:
        session_count = as_int(first_number(measurement_window, "sessions", "session_count", "total_sessions"))
    target["session_count"] += session_count

    input_tokens = as_int(first_number(item, "input_tokens", "prompt_tokens"))
    if not input_tokens:
        input_tokens = as_int(first_number(token_metrics, "input", "input_tokens", "prompt_tokens"))
    output_tokens = as_int(first_number(item, "output_tokens", "completion_tokens"))
    if not output_tokens:
        output_tokens = as_int(first_number(token_metrics, "output", "output_tokens", "completion_tokens"))
    target["input_tokens"] += input_tokens
    target["output_tokens"] += output_tokens

    total_tokens = as_int(first_number(item, "total_tokens", "tokens"))
    if not total_tokens:
        total_tokens = as_int(first_number(token_metrics, "total", "total_tokens", "tokens"))
    if not total_tokens:
        total_tokens = input_tokens + output_tokens
    target["total_tokens"] += total_tokens

    target["total_cost_usd"] += as_float(
        first_number(item, "total_usd", "total_cost_usd", "cost_usd", "usd", "cost")
    )


output = Path(os.environ["OYRF_OUTPUT"])
raw = os.environ["OYRF_RAW_JSON"]
source_hint = os.environ["OYRF_SOURCE_HINT"]
metrics = {
    "session_count": 0.0,
    "total_tokens": 0.0,
    "input_tokens": 0.0,
    "output_tokens": 0.0,
    "total_cost_usd": 0.0,
}
source = source_hint

try:
    data = json.loads(raw)
except json.JSONDecodeError:
    data = []
    source = "interstat-empty"

if source_hint == "dry-run-fixture":
    source = "dry-run-fixture"
elif isinstance(data, dict):
    add_metrics(metrics, data)
    source = "interstat" if source_hint == "interstat" else "interstat-empty"
elif isinstance(data, list):
    if data:
        for item in data:
            if isinstance(item, dict):
                add_metrics(metrics, item)
        source = "interstat"
    else:
        source = "interstat-empty"
else:
    source = "interstat-empty"

# If Interstat returned input/output tokens but no total, repair the total field.
if not metrics["total_tokens"]:
    metrics["total_tokens"] = metrics["input_tokens"] + metrics["output_tokens"]

session_count = int(metrics["session_count"])
total_cost = float(metrics["total_cost_usd"])
cost_per_session = total_cost / session_count if session_count else 0.0
row = {
    "captured_at": os.environ["OYRF_CAPTURED_AT"],
    "window_days": str(int(os.environ["OYRF_WINDOW_DAYS"])),
    "session_count": str(session_count),
    "total_tokens": str(int(metrics["total_tokens"])),
    "input_tokens": str(int(metrics["input_tokens"])),
    "output_tokens": str(int(metrics["output_tokens"])),
    "total_cost_usd": f"{total_cost:.6f}",
    "cost_per_session_usd": f"{cost_per_session:.6f}",
    "source": source,
}

write_header = True
if output.exists() and output.stat().st_size > 0:
    with output.open(newline="", encoding="utf-8") as handle:
        reader = csv.reader(handle)
        existing_header = next(reader, [])
    if existing_header != HEADER:
        raise SystemExit(f"refusing to append to {output}: unexpected header {existing_header!r}")
    write_header = False

with output.open("a", newline="", encoding="utf-8") as handle:
    writer = csv.DictWriter(handle, fieldnames=HEADER)
    if write_header:
        writer.writeheader()
    writer.writerow(row)

print(f"wrote {output} source={source} captured_at={row['captured_at']}")
PY
