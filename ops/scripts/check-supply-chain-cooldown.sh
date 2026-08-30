#!/usr/bin/env bash
# Verify the npm supply-chain cooldown is ACTIVE, not merely configured.
#
# `min-release-age` is ignored silently by npm < 11.10. A repo can carry a
# correct .npmrc, pass review, and enforce nothing — the config being present
# is not evidence that it applies. This script separates the two questions and
# fails when they disagree.
#
# Exit codes:
#   0  configured AND enforceable
#   1  configured but NOT enforceable (npm too old) — the dangerous case
#   2  not configured
#
# Usage: check-supply-chain-cooldown.sh [dir ...]   (default: cwd)

set -uo pipefail

MIN_NPM_MAJOR=11
MIN_NPM_MINOR=10

npm_version="$(npm --version 2>/dev/null || echo "")"
if [ -z "$npm_version" ]; then
  echo "FAIL  npm not found on PATH — cannot assess enforcement."
  exit 1
fi

npm_major="${npm_version%%.*}"
npm_rest="${npm_version#*.}"
npm_minor="${npm_rest%%.*}"

enforceable=0
if [ "$npm_major" -gt "$MIN_NPM_MAJOR" ] 2>/dev/null; then
  enforceable=1
elif [ "$npm_major" -eq "$MIN_NPM_MAJOR" ] 2>/dev/null && [ "$npm_minor" -ge "$MIN_NPM_MINOR" ] 2>/dev/null; then
  enforceable=1
fi

if [ "$enforceable" -eq 1 ]; then
  echo "npm $npm_version — min-release-age IS enforced (need >= ${MIN_NPM_MAJOR}.${MIN_NPM_MINOR})"
else
  echo "npm $npm_version — min-release-age is SILENTLY IGNORED (need >= ${MIN_NPM_MAJOR}.${MIN_NPM_MINOR})"
  echo "      fix: npm install -g npm@latest"
fi

status=0
configured_any=0

for dir in "${@:-$PWD}"; do
  value="$(cd "$dir" 2>/dev/null && npm config get min-release-age 2>/dev/null)"
  if [ -z "$value" ] || [ "$value" = "undefined" ] || [ "$value" = "null" ]; then
    echo "  NOT CONFIGURED  $dir"
    [ "$status" -eq 0 ] && status=2
  else
    configured_any=1
    if [ "$enforceable" -eq 1 ]; then
      echo "  ACTIVE ${value}d      $dir"
    else
      echo "  INERT  ${value}d      $dir  <-- configured but not enforced"
      status=1
    fi
  fi
done

# A cooldown that is configured everywhere but enforced nowhere is the exact
# failure this script exists to name: it reads as protection in review while
# providing none at install time.
if [ "$configured_any" -eq 1 ] && [ "$enforceable" -eq 0 ]; then
  echo
  echo "VERDICT: cooldown is configured but INERT. Upgrade npm before trusting it."
  exit 1
fi

exit "$status"
