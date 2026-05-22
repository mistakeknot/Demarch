#!/usr/bin/env bash
#
# check-rig-drift — doctor/CI wrapper for the generated Interverse inventory.
#
# Usage:
#   scripts/check-rig-drift.sh [--json] [--verbose]
#
# Environment overrides for tests and non-standard checkouts:
#   SYLVESTE_ROOT
#   INTERVERSE_INVENTORY_RIG
#   INTERVERSE_INVENTORY_MARKETPLACE
#
# Exit codes:
#   0 — no high-severity drift
#   1 — high-severity drift detected
#   2 — usage or inventory generation error

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="${SYLVESTE_ROOT:-$(cd "$SCRIPT_DIR/.." && pwd)}"
INVENTORY_SCRIPT="$SCRIPT_DIR/interverse_inventory.py"

JSON_OUT=false
VERBOSE=false

for arg in "$@"; do
    case "$arg" in
        --json) JSON_OUT=true ;;
        --verbose|-v) VERBOSE=true ;;
        --help|-h)
            sed -n '2,/^$/p' "$0" | sed 's/^# \?//'
            exit 0
            ;;
        --fix)
            echo "check-rig-drift: --fix is no longer supported; edit the reported manifest/path drift directly." >&2
            exit 2
            ;;
        *) echo "check-rig-drift: unknown flag: $arg" >&2; exit 2 ;;
    esac
done

args=(--root "$ROOT" --check)
if [[ "$JSON_OUT" == true ]]; then
    args+=(--json)
fi
if [[ "$VERBOSE" == true ]]; then
    args+=(--verbose)
fi

python3 "$INVENTORY_SCRIPT" "${args[@]}"
