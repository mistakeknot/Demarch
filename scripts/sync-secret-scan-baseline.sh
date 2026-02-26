#!/usr/bin/env bash
# demarch-managed: secret-scan-baseline v1
#
# Sync the secret-scanning baseline files into product repos.
#
# Usage:
#   scripts/sync-secret-scan-baseline.sh           # dry run (all repos)
#   scripts/sync-secret-scan-baseline.sh --apply   # write files (all repos)
#   scripts/sync-secret-scan-baseline.sh --repo core/intercore --apply
set -euo pipefail

APPLY=false
declare -a TARGET_REPOS=()

usage() {
  cat <<'EOF'
Usage: sync-secret-scan-baseline.sh [--apply] [--repo <path>]...

Options:
  --apply         Write changes. Default is dry-run.
  --repo <path>   Target a specific repo path relative to Demarch root.
  -h, --help      Show this help.
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --apply)
      APPLY=true
      shift
      ;;
    --repo)
      if [[ $# -lt 2 ]]; then
        echo "ERROR: --repo requires a path argument" >&2
        exit 1
      fi
      TARGET_REPOS+=("$2")
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "ERROR: unknown argument: $1" >&2
      usage >&2
      exit 1
      ;;
  esac
done

REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
TEMPLATE_DIR="$REPO_ROOT/scripts/templates/secret-scan"
REPO_LIST_SCRIPT="$REPO_ROOT/scripts/secret-scan-repo-list.sh"
MANAGED_MARKER="demarch-managed: secret-scan-baseline"

if [[ ! -x "$REPO_LIST_SCRIPT" ]]; then
  echo "ERROR: missing executable repo list script: $REPO_LIST_SCRIPT" >&2
  exit 1
fi

if [[ ${#TARGET_REPOS[@]} -eq 0 ]]; then
  while IFS= read -r repo; do
    [[ -z "$repo" ]] && continue
    TARGET_REPOS+=("$repo")
  done < <("$REPO_LIST_SCRIPT" "$REPO_ROOT")
fi

normalize_repo_path() {
  local repo="$1"
  if [[ "$repo" = /* ]]; then
    if [[ "$repo" != "$REPO_ROOT/"* ]]; then
      echo ""
      return
    fi
    echo "${repo#"$REPO_ROOT"/}"
    return
  fi
  echo "$repo"
}

is_managed_file() {
  local path="$1"
  [[ -f "$path" ]] || return 1
  head -n 5 "$path" | rg -q "$MANAGED_MARKER"
}

sync_file() {
  local repo_abs="$1"
  local rel_dest="$2"
  local template="$3"
  local mode="$4"

  local dest="$repo_abs/$rel_dest"
  local repo_rel="${repo_abs#"$REPO_ROOT"/}"

  if [[ -f "$dest" ]] && ! is_managed_file "$dest"; then
    echo "SKIP  $repo_rel/$rel_dest (existing unmanaged file)"
    return 2
  fi

  if [[ -f "$dest" ]] && cmp -s "$template" "$dest"; then
    echo "OK    $repo_rel/$rel_dest"
    return 0
  fi

  if ! $APPLY; then
    echo "WOULD $repo_rel/$rel_dest"
    return 1
  fi

  mkdir -p "$(dirname "$dest")"
  cp "$template" "$dest"
  chmod "$mode" "$dest"
  echo "WRITE $repo_rel/$rel_dest"
  return 1
}

updated=0
skipped=0
errors=0

for repo_in in "${TARGET_REPOS[@]}"; do
  repo_rel="$(normalize_repo_path "$repo_in")"
  if [[ -z "$repo_rel" ]]; then
    echo "ERROR: repo path outside Demarch root: $repo_in" >&2
    errors=$((errors + 1))
    continue
  fi

  repo_abs="$REPO_ROOT/$repo_rel"
  if [[ ! -d "$repo_abs/.git" ]]; then
    echo "ERROR: not a repo path: $repo_rel" >&2
    errors=$((errors + 1))
    continue
  fi

  sync_file "$repo_abs" ".github/workflows/secret-scan.yml" "$TEMPLATE_DIR/secret-scan.yml" "0644" || rc=$?
  rc="${rc:-0}"
  if [[ "$rc" -eq 1 ]]; then updated=$((updated + 1)); fi
  if [[ "$rc" -eq 2 ]]; then skipped=$((skipped + 1)); fi
  unset rc

  sync_file "$repo_abs" ".gitleaks.toml" "$TEMPLATE_DIR/gitleaks.toml" "0644" || rc=$?
  rc="${rc:-0}"
  if [[ "$rc" -eq 1 ]]; then updated=$((updated + 1)); fi
  if [[ "$rc" -eq 2 ]]; then skipped=$((skipped + 1)); fi
  unset rc

  sync_file "$repo_abs" "scripts/validate-gitleaks-waivers.sh" "$TEMPLATE_DIR/validate-gitleaks-waivers.sh" "0755" || rc=$?
  rc="${rc:-0}"
  if [[ "$rc" -eq 1 ]]; then updated=$((updated + 1)); fi
  if [[ "$rc" -eq 2 ]]; then skipped=$((skipped + 1)); fi
  unset rc
done

echo
if $APPLY; then
  echo "Sync complete: $updated file(s) written, $skipped skipped, $errors error(s)."
else
  echo "Dry run complete: $updated file(s) would change, $skipped skipped, $errors error(s)."
  echo "Run with --apply to write changes."
fi

if (( errors > 0 )); then
  exit 1
fi
