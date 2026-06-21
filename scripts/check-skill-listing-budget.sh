#!/usr/bin/env bash
#
# check-skill-listing-budget — guard the eager skill-listing prefix size.
#
# Every plugin SKILL.md's frontmatter `description:` is loaded into the model's
# context prefix on every session. With no budget, that listing creeps as
# plugins are added (a prior compaction cut it to ~34.9KB; it had crept back to
# ~38.5KB with no guard). This gate sums the deduplicated description bytes and
# fails when they exceed a budget, so new skills must stay within budget or
# justify raising it.
#
# Usage:
#   scripts/check-skill-listing-budget.sh [--json] [--verbose]
#
# Environment overrides (for tests / non-standard checkouts):
#   SKILL_LISTING_BUDGET_BYTES   max allowed total (default 33000)
#   SKILL_PLUGINS_ROOT           plugins dir (default ~/.claude/plugins)
#   SYLVESTE_ROOT                repo root (default: parent of this script's dir)
#
# Exit codes:
#   0 — within budget
#   1 — over budget
#   2 — usage or measurement error
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="${SYLVESTE_ROOT:-$(cd "$SCRIPT_DIR/.." && pwd)}"
AUDIT="$SCRIPT_DIR/perf/audit-skill-contributions.py"

BUDGET="${SKILL_LISTING_BUDGET_BYTES:-33000}"
PLUGINS_ROOT="${SKILL_PLUGINS_ROOT:-$HOME/.claude/plugins}"
JSON_OUT=false
VERBOSE=false

for arg in "$@"; do
    case "$arg" in
        --json) JSON_OUT=true ;;
        --verbose | -v) VERBOSE=true ;;
        --help | -h)
            sed -n '2,/^$/p' "$0" | sed 's/^# \?//'
            exit 0
            ;;
        *)
            echo "unknown argument: $arg" >&2
            exit 2
            ;;
    esac
done

if [[ ! -f "$AUDIT" ]]; then
    echo "skill-budget: audit script not found at $AUDIT" >&2
    exit 2
fi
if [[ ! -d "$PLUGINS_ROOT" ]]; then
    echo "skill-budget: plugins root not found at $PLUGINS_ROOT (set SKILL_PLUGINS_ROOT)" >&2
    exit 2
fi

# The audit cross-references an interstat metrics DB for MCP usage, which need
# not exist in CI. desc_bytes comes purely from SKILL.md frontmatter, so point
# --db at a path that won't exist and let the audit's usage lookup come back
# empty — the byte totals are unaffected.
audit_json=$(python3 "$AUDIT" \
    --plugins-root "$PLUGINS_ROOT" \
    --db "/nonexistent-skill-budget-db" \
    --out - 2>/dev/null) || {
    echo "skill-budget: audit failed" >&2
    exit 2
}

total=$(printf '%s' "$audit_json" | python3 -c "
import sys, json
rows = json.load(sys.stdin)
print(sum(int(r.get('desc_bytes', 0)) for r in rows))
" 2>/dev/null) || {
    echo "skill-budget: could not sum desc_bytes" >&2
    exit 2
}

case "$total" in '' | *[!0-9]*)
    echo "skill-budget: non-numeric total '$total'" >&2
    exit 2
    ;;
esac

over=$((total - BUDGET))
tokens=$((total / 4))

if $JSON_OUT; then
    status=$([[ "$total" -le "$BUDGET" ]] && echo "ok" || echo "over")
    printf '{"total_bytes":%d,"budget_bytes":%d,"over_by":%d,"approx_tokens":%d,"status":"%s"}\n' \
        "$total" "$BUDGET" "$over" "$tokens" "$status"
fi

if [[ "$total" -le "$BUDGET" ]]; then
    if $VERBOSE && ! $JSON_OUT; then
        echo "skill-listing budget OK: ${total}B / ${BUDGET}B (~${tokens} tok), ${over#-}B headroom"
    fi
    exit 0
fi

if ! $JSON_OUT; then
    echo "skill-listing OVER BUDGET: ${total}B > ${BUDGET}B (~${tokens} tok, +${over}B)" >&2
    echo "  The eager skill listing loads into every session prefix. Either trim" >&2
    echo "  the biggest descriptions (scripts/perf/audit-skill-contributions.py" >&2
    echo "  --plugins-root \"$PLUGINS_ROOT\" lists them) or, if the growth is" >&2
    echo "  justified, raise SKILL_LISTING_BUDGET_BYTES in CI deliberately." >&2
fi
exit 1
