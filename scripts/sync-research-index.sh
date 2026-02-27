#!/usr/bin/env bash
set -euo pipefail

OWNER="${1:-Dicklesworthstone}"

if ! command -v gh >/dev/null 2>&1; then
  echo "error: gh CLI is required" >&2
  exit 1
fi

if ! command -v jq >/dev/null 2>&1; then
  echo "error: jq is required" >&2
  exit 1
fi

ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
RESEARCH_DIR="$ROOT/research"
OUT_MD="$RESEARCH_DIR/REPO_INDEX.md"

if [[ ! -d "$RESEARCH_DIR" ]]; then
  echo "error: research directory not found at $RESEARCH_DIR" >&2
  exit 1
fi

tmp_json="$(mktemp)"
tmp_tsv="$(mktemp)"
tmp_names="$(mktemp)"
trap 'rm -f "$tmp_json" "$tmp_tsv" "$tmp_names"' EXIT

gh repo list "$OWNER" --limit 1000 \
  --json name,url,description,updatedAt,isArchived,isFork,stargazerCount,primaryLanguage \
  > "$tmp_json"

jq -r '
  .[]
  | [
      .name,
      .url,
      ((.description // "") | gsub("[\\r\\n]+"; " ") | gsub("\\t+"; " ") | gsub("\\|"; "/")),
      (.primaryLanguage.name // ""),
      (.stargazerCount | tostring),
      .updatedAt,
      (.isArchived | tostring),
      (.isFork | tostring)
    ]
  | join("\u001f")
' "$tmp_json" | sort > "$tmp_tsv"

jq -r '.[].name' "$tmp_json" | sort > "$tmp_names"

total_owner="$(jq 'length' "$tmp_json")"
local_owner=0
missing_owner=0

while IFS= read -r repo; do
  if [[ -d "$RESEARCH_DIR/$repo/.git" ]]; then
    ((local_owner += 1))
  else
    ((missing_owner += 1))
  fi
done < "$tmp_names"

other_local_count="$({
  find "$RESEARCH_DIR" -mindepth 2 -maxdepth 2 -type d -name .git -printf '%h\n' \
    | xargs -r -n1 basename \
    | sort \
    | grep -vxF -f "$tmp_names" || true
} | wc -l | tr -d ' ')"

generated_at="$(date -u +"%Y-%m-%d %H:%M:%S UTC")"

{
  echo "# Research Repo Index"
  echo
  echo "Generated: $generated_at"
  echo
  printf 'Owner: `%s`\n' "$OWNER"
  echo
  echo "## Summary"
  echo
  echo "- Owner repos discovered: $total_owner"
  echo "- Owner repos cloned locally: $local_owner"
  echo "- Owner repos missing locally: $missing_owner"
  echo "- Additional non-owner local clones: $other_local_count"
  echo
  echo "## Owner Repositories"
  echo
  echo "| Repo | Local | HEAD | Stars | Lang | Updated | Flags | Description |"
  echo "|---|---|---|---:|---|---|---|---|"

  while IFS=$'\x1f' read -r name url desc lang stars updated archived fork; do
    local_state="no"
    head="-"
    if [[ -d "$RESEARCH_DIR/$name/.git" ]]; then
      local_state="yes"
      head="$(git -C "$RESEARCH_DIR/$name" rev-parse --short HEAD 2>/dev/null || echo "?")"
    fi

    updated_date="${updated%%T*}"

    flags=""
    if [[ "$archived" == "true" ]]; then
      flags="archived"
    fi
    if [[ "$fork" == "true" ]]; then
      if [[ -n "$flags" ]]; then
        flags="$flags, fork"
      else
        flags="fork"
      fi
    fi
    if [[ -z "$flags" ]]; then
      flags="-"
    fi

    if [[ -z "$lang" ]]; then
      lang="-"
    fi
    if [[ -z "$desc" ]]; then
      desc="-"
    fi

    echo "| [\`$name\`]($url) | $local_state | \`$head\` | $stars | $lang | $updated_date | $flags | $desc |"
  done < "$tmp_tsv"

  echo
  echo "## Additional Non-Owner Local Clones"
  echo

  mapfile -t other_local < <(
    find "$RESEARCH_DIR" -mindepth 2 -maxdepth 2 -type d -name .git -printf '%h\n' \
      | xargs -r -n1 basename \
      | sort \
      | grep -vxF -f "$tmp_names" || true
  )

  if (( ${#other_local[@]} == 0 )); then
    echo "None."
  else
    echo "| Repo | Origin | HEAD |"
    echo "|---|---|---|"
    for repo in "${other_local[@]}"; do
      origin="$(git -C "$RESEARCH_DIR/$repo" remote get-url origin 2>/dev/null || echo "-")"
      head="$(git -C "$RESEARCH_DIR/$repo" rev-parse --short HEAD 2>/dev/null || echo "-")"
      echo "| \`$repo\` | $origin | \`$head\` |"
    done
  fi
} > "$OUT_MD"

echo "Wrote $OUT_MD"
