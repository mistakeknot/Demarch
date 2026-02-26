#!/usr/bin/env bash
# demarch-managed: secret-scan-baseline v1
#
# Print product repository paths in the Demarch monorepo.
# Paths are relative to repo root.
set -euo pipefail

REPO_ROOT="${1:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}"

cd "$REPO_ROOT"

find apps core interverse os sdk \
  -mindepth 2 \
  -maxdepth 2 \
  -type d \
  -name .git \
  -print \
  | sed 's#/.git$##' \
  | sort
