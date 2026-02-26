#!/usr/bin/env bash
# demarch-managed: secret-scan-baseline v1
#
# Enforce metadata and expiration on inline gitleaks waivers.
#
# Required format on the same line as the `gitleaks:allow` marker:
#   gitleaks:allow reason=<slug> owner=<team-or-user> expires=YYYY-MM-DD
set -euo pipefail

TODAY_UTC="${TODAY_UTC:-$(date -u +%F)}"
TODAY_EPOCH="$(date -u -d "$TODAY_UTC" +%s)"
ERRORS=0
COUNT=0

while IFS= read -r match; do
  COUNT=$((COUNT + 1))
  file="${match%%:*}"
  rest="${match#*:}"
  line_no="${rest%%:*}"
  line_text="${rest#*:}"
  prefix="${file}:${line_no}"

  if [[ ! "$line_text" =~ reason=([^[:space:]]+) ]]; then
    echo "ERROR ${prefix} missing required waiver field: reason=<slug>"
    ERRORS=$((ERRORS + 1))
  fi

  if [[ ! "$line_text" =~ owner=([^[:space:]]+) ]]; then
    echo "ERROR ${prefix} missing required waiver field: owner=<team-or-user>"
    ERRORS=$((ERRORS + 1))
  fi

  if [[ ! "$line_text" =~ expires=([0-9]{4}-[0-9]{2}-[0-9]{2}) ]]; then
    echo "ERROR ${prefix} missing required waiver field: expires=YYYY-MM-DD"
    ERRORS=$((ERRORS + 1))
    continue
  fi

  expires="${BASH_REMATCH[1]}"
  if ! expires_epoch="$(date -u -d "$expires" +%s 2>/dev/null)"; then
    echo "ERROR ${prefix} has invalid expires date: $expires"
    ERRORS=$((ERRORS + 1))
    continue
  fi

  if (( expires_epoch < TODAY_EPOCH )); then
    echo "ERROR ${prefix} waiver expired on ${expires}"
    ERRORS=$((ERRORS + 1))
  fi
done < <(
  rg --line-number --no-heading --hidden \
    --glob '!.git/**' \
    --glob '!node_modules/**' \
    --glob '!vendor/**' \
    --glob '!dist/**' \
    --glob '!build/**' \
    --glob '!**/*.md' \
    --glob '!**/*.markdown' \
    --glob '!scripts/validate-gitleaks-waivers.sh' \
    'gitleaks:allow'
)

if (( COUNT == 0 )); then
  echo "No gitleaks waivers found."
fi

if (( ERRORS > 0 )); then
  echo "Waiver validation failed with ${ERRORS} error(s)."
  exit 1
fi

echo "Waiver validation passed (${COUNT} waiver line(s) checked)."
