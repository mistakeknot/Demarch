#!/usr/bin/env bash
# demarch-managed: secret-scan-baseline v1
#
# Run backfill secret scanning across product repos and write a summary report.
set -euo pipefail

SINCE="180 days ago"
FULL_HISTORY=false
FAIL_ON_FINDINGS=false
declare -a TARGET_REPOS=()

usage() {
  cat <<'EOF'
Usage: backfill-secret-scan.sh [options]

Options:
  --since "<expr>"      git log --since expression (default: "180 days ago")
  --full-history        scan full git history (overrides --since)
  --repo <path>         target a specific repo path relative to Demarch root
  --fail-on-findings    return non-zero if any findings are detected
  -h, --help            show this help
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --since)
      if [[ $# -lt 2 ]]; then
        echo "ERROR: --since requires a value" >&2
        exit 1
      fi
      SINCE="$2"
      shift 2
      ;;
    --full-history)
      FULL_HISTORY=true
      shift
      ;;
    --repo)
      if [[ $# -lt 2 ]]; then
        echo "ERROR: --repo requires a path" >&2
        exit 1
      fi
      TARGET_REPOS+=("$2")
      shift 2
      ;;
    --fail-on-findings)
      FAIL_ON_FINDINGS=true
      shift
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
REPO_LIST_SCRIPT="$REPO_ROOT/scripts/secret-scan-repo-list.sh"
DATE_UTC="$(date -u +%F)"
STAMP_UTC="$(date -u +%FT%TZ)"
REPORT_DIR="$REPO_ROOT/docs/reports/security/secret-scan-backfill-$DATE_UTC"
SUMMARY_FILE="$REPO_ROOT/docs/reports/security/secret-scan-backfill-$DATE_UTC.md"

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

ensure_gitleaks() {
  if command -v gitleaks >/dev/null 2>&1; then
    command -v gitleaks
    return
  fi

  local version="${GITLEAKS_VERSION:-8.24.2}"
  local arch
  case "$(uname -m)" in
    x86_64|amd64) arch="x64" ;;
    aarch64|arm64) arch="arm64" ;;
    *)
      echo "ERROR: unsupported architecture for auto-install: $(uname -m)" >&2
      exit 1
      ;;
  esac

  local tool_dir="$REPO_ROOT/.tmp/tools/gitleaks/$version"
  local bin="$tool_dir/gitleaks"
  if [[ ! -x "$bin" ]]; then
    mkdir -p "$tool_dir"
    local tarball="$tool_dir/gitleaks.tar.gz"
    curl -sSfL "https://github.com/gitleaks/gitleaks/releases/download/v${version}/gitleaks_${version}_linux_${arch}.tar.gz" -o "$tarball"
    tar -xzf "$tarball" -C "$tool_dir" gitleaks
    chmod 0755 "$bin"
  fi
  echo "$bin"
}

if [[ ${#TARGET_REPOS[@]} -eq 0 ]]; then
  while IFS= read -r repo; do
    [[ -z "$repo" ]] && continue
    TARGET_REPOS+=("$repo")
  done < <("$REPO_LIST_SCRIPT" "$REPO_ROOT")
fi

mkdir -p "$REPORT_DIR"
GITLEAKS_BIN="$(ensure_gitleaks)"
LOG_OPTS="--all --since=$SINCE"
if $FULL_HISTORY; then
  LOG_OPTS="--all"
else
  if ! SINCE_DATE="$(date -u -d "$SINCE" +%F 2>/dev/null)"; then
    echo "ERROR: invalid --since expression: $SINCE" >&2
    exit 1
  fi
  LOG_OPTS="--all --since=$SINCE_DATE"
fi

declare -a SUMMARY_ROWS=()
clean_count=0
finding_count=0
error_count=0
total_findings=0

for repo_in in "${TARGET_REPOS[@]}"; do
  repo_rel="$(normalize_repo_path "$repo_in")"
  if [[ -z "$repo_rel" ]]; then
    echo "ERROR: repo path outside Demarch root: $repo_in" >&2
    error_count=$((error_count + 1))
    SUMMARY_ROWS+=("| \`$repo_in\` | error | 0 | path outside root |")
    continue
  fi

  repo_abs="$REPO_ROOT/$repo_rel"
  if [[ ! -d "$repo_abs/.git" ]]; then
    echo "ERROR: not a repo path: $repo_rel" >&2
    error_count=$((error_count + 1))
    SUMMARY_ROWS+=("| \`$repo_rel\` | error | 0 | missing .git |")
    continue
  fi

  file_slug="${repo_rel//\//__}"
  json_report="$REPORT_DIR/${file_slug}.json"
  cmd_log="$REPORT_DIR/${file_slug}.log"
  config_arg=()
  if [[ -f "$repo_abs/.gitleaks.toml" ]]; then
    config_arg=(--config "$repo_abs/.gitleaks.toml")
  fi

  echo "Scanning $repo_rel ..."
  set +e
  "$GITLEAKS_BIN" git \
    --no-banner \
    --redact \
    --report-format json \
    --report-path "$json_report" \
    --log-opts="$LOG_OPTS" \
    "${config_arg[@]}" \
    "$repo_abs" \
    >"$cmd_log" 2>&1
  rc=$?
  set -e

  findings="0"
  if [[ -s "$json_report" ]]; then
    findings="$(jq 'length' "$json_report" 2>/dev/null || echo 0)"
  fi

  case "$rc" in
    0)
      clean_count=$((clean_count + 1))
      SUMMARY_ROWS+=("| \`$repo_rel\` | clean | 0 | \`${json_report#"$REPO_ROOT"/}\` |")
      ;;
    1)
      if (( findings > 0 )); then
        finding_count=$((finding_count + 1))
        total_findings=$((total_findings + findings))
        SUMMARY_ROWS+=("| \`$repo_rel\` | findings | $findings | \`${json_report#"$REPO_ROOT"/}\` |")
      else
        error_count=$((error_count + 1))
        SUMMARY_ROWS+=("| \`$repo_rel\` | error | 0 | \`${cmd_log#"$REPO_ROOT"/}\` |")
      fi
      ;;
    *)
      error_count=$((error_count + 1))
      SUMMARY_ROWS+=("| \`$repo_rel\` | error | $findings | \`${cmd_log#"$REPO_ROOT"/}\` |")
      ;;
  esac
done

{
  echo "# Secret Scan Backfill Report ($DATE_UTC)"
  echo
  echo "- Generated (UTC): $STAMP_UTC"
  echo "- Scanner: \`$("$GITLEAKS_BIN" version | tr -d '\n')\`"
  echo "- Log options: \`$LOG_OPTS\`"
  echo
  echo "## Summary"
  echo
  echo "- Repos scanned: ${#TARGET_REPOS[@]}"
  echo "- Clean: $clean_count"
  echo "- Repos with findings: $finding_count"
  echo "- Total findings: $total_findings"
  echo "- Errors: $error_count"
  echo
  echo "## Results"
  echo
  echo "| Repository | Status | Findings | Artifact |"
  echo "|---|---|---:|---|"
  for row in "${SUMMARY_ROWS[@]}"; do
    echo "$row"
  done
} > "$SUMMARY_FILE"

echo "Backfill summary written: ${SUMMARY_FILE#"$REPO_ROOT"/}"
echo "Raw artifacts directory: ${REPORT_DIR#"$REPO_ROOT"/}"

if $FAIL_ON_FINDINGS && (( finding_count > 0 )); then
  exit 1
fi

if (( error_count > 0 )); then
  exit 1
fi
