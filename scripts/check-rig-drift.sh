#!/usr/bin/env bash
#
# check-rig-drift — detect drift between interverse plugins and agent-rig.json
#
# Checks:
#   1. Plugins in interverse/ with marketplace entries but missing from agent-rig.json
#   2. Plugins in agent-rig.json that don't exist in interverse/
#   3. Description mismatches between plugin.json and agent-rig.json
#   4. Marketplace registration gaps (plugin exists but not in marketplace)
#
# Usage:
#   scripts/check-rig-drift.sh [--fix] [--json] [--verbose]
#
# Exit codes:
#   0 — no drift
#   1 — drift detected
#   2 — usage error

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
RIG_JSON="$ROOT/os/clavain/agent-rig.json"
INTERVERSE="$ROOT/interverse"
MARKETPLACE="${HOME}/.claude/plugins/marketplaces/interagency-marketplace/.claude-plugin/marketplace.json"

# --- Colors ---
if [ -t 1 ]; then
    RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[0;33m'; DIM='\033[2m'; BOLD='\033[1m'; NC='\033[0m'
else
    RED=''; GREEN=''; YELLOW=''; DIM=''; BOLD=''; NC=''
fi

FIX=false
JSON_OUT=false
VERBOSE=false

for arg in "$@"; do
    case "$arg" in
        --fix) FIX=true ;;
        --json) JSON_OUT=true ;;
        --verbose|-v) VERBOSE=true ;;
        --help|-h)
            sed -n '2,/^$/p' "$0" | sed 's/^# \?//'
            exit 0
            ;;
        *) printf "${RED}Unknown flag: %s${NC}\n" "$arg"; exit 2 ;;
    esac
done

# --- Validation ---
if [[ ! -f "$RIG_JSON" ]]; then
    printf "${RED}agent-rig.json not found at %s${NC}\n" "$RIG_JSON"
    exit 2
fi

if [[ ! -d "$INTERVERSE" ]]; then
    printf "${RED}interverse/ not found at %s${NC}\n" "$INTERVERSE"
    exit 2
fi

# --- Extract data ---

# Plugins listed in agent-rig.json (all tiers)
rig_plugins=$(python3 -c "
import json, sys
rig = json.load(open('$RIG_JSON'))
seen = set()
for section in ['required', 'recommended', 'optional']:
    for p in rig['plugins'].get(section, []):
        name = p['source'].split('@')[0]
        marketplace = p['source'].split('@')[1] if '@' in p['source'] else ''
        if marketplace == 'interagency-marketplace':
            seen.add(name)
            print(name)
for name in sorted(seen):
    pass  # already printed
" | sort -u)

# Plugins in interverse/ that have plugin.json (i.e., are real plugins)
interverse_plugins=$(find "$INTERVERSE" -maxdepth 3 -path '*/.claude-plugin/plugin.json' -exec dirname {} \; 2>/dev/null \
    | xargs -I{} dirname {} \
    | xargs -I{} basename {} \
    | sort -u)

# Marketplace plugins (if available)
marketplace_plugins=""
if [[ -f "$MARKETPLACE" ]]; then
    marketplace_plugins=$(python3 -c "
import json
mkt = json.load(open('$MARKETPLACE'))
for p in mkt.get('plugins', []):
    if isinstance(p, dict):
        print(p.get('name', ''))
" | sort -u)
fi

# --- Check 1: interverse plugins with marketplace entries but not in rig ---
drift_count=0
missing_from_rig=()
not_in_marketplace=()
orphaned_in_rig=()
desc_mismatches=()

for plugin in $interverse_plugins; do
    # Skip non-plugin directories (marketplace itself, etc.)
    if [[ "$plugin" == "interagency-marketplace" ]]; then
        continue
    fi

    in_rig=$(echo "$rig_plugins" | grep -qx "$plugin" && echo "yes" || echo "no")
    in_marketplace=$(echo "$marketplace_plugins" | grep -qx "$plugin" && echo "yes" || echo "no")

    if [[ "$in_marketplace" == "yes" && "$in_rig" == "no" ]]; then
        missing_from_rig+=("$plugin")
        ((drift_count++))
    fi

    if [[ "$in_marketplace" == "no" ]]; then
        not_in_marketplace+=("$plugin")
    fi
done

# --- Check 2: rig plugins that don't exist in interverse ---
for plugin in $rig_plugins; do
    if ! echo "$interverse_plugins" | grep -qx "$plugin"; then
        orphaned_in_rig+=("$plugin")
        ((drift_count++))
    fi
done

# --- Check 3: description drift (rig vs plugin.json) ---
for plugin in $rig_plugins; do
    plugin_json="$INTERVERSE/$plugin/.claude-plugin/plugin.json"
    if [[ ! -f "$plugin_json" ]]; then
        continue
    fi

    # Get description from plugin.json
    local_desc=$(python3 -c "
import json
p = json.load(open('$plugin_json'))
print(p.get('description', ''))
" 2>/dev/null)

    # Get description from agent-rig.json
    rig_desc=$(python3 -c "
import json
rig = json.load(open('$RIG_JSON'))
for section in ['required', 'recommended', 'optional']:
    for p in rig['plugins'].get(section, []):
        name = p['source'].split('@')[0]
        if name == '$plugin':
            print(p.get('description', ''))
            break
" 2>/dev/null)

    # Rig descriptions are intentionally shorter — only flag if rig desc is empty
    if [[ -n "$local_desc" && -z "$rig_desc" ]]; then
        desc_mismatches+=("$plugin")
        ((drift_count++))
    fi
done

# --- Output ---
if [[ "$JSON_OUT" == true ]]; then
    python3 -c "
import json
print(json.dumps({
    'drift_count': $drift_count,
    'missing_from_rig': $(printf '%s\n' "${missing_from_rig[@]:-}" | python3 -c "import sys,json; print(json.dumps([l.strip() for l in sys.stdin if l.strip()]))"),
    'not_in_marketplace': $(printf '%s\n' "${not_in_marketplace[@]:-}" | python3 -c "import sys,json; print(json.dumps([l.strip() for l in sys.stdin if l.strip()]))"),
    'orphaned_in_rig': $(printf '%s\n' "${orphaned_in_rig[@]:-}" | python3 -c "import sys,json; print(json.dumps([l.strip() for l in sys.stdin if l.strip()]))"),
    'empty_rig_descriptions': $(printf '%s\n' "${desc_mismatches[@]:-}" | python3 -c "import sys,json; print(json.dumps([l.strip() for l in sys.stdin if l.strip()]))")
}, indent=2))
"
else
    printf "${BOLD}Rig Drift Check${NC}\n"
    printf "${DIM}agent-rig.json vs interverse/ vs marketplace${NC}\n\n"

    if [[ ${#missing_from_rig[@]} -gt 0 ]]; then
        printf "${RED}Published but not in agent-rig.json:${NC}\n"
        for p in "${missing_from_rig[@]}"; do
            printf "  ${RED}✗${NC} %s\n" "$p"
        done
        printf "\n"
    fi

    if [[ ${#orphaned_in_rig[@]} -gt 0 ]]; then
        printf "${YELLOW}In agent-rig.json but not in interverse/:${NC}\n"
        for p in "${orphaned_in_rig[@]}"; do
            printf "  ${YELLOW}!${NC} %s\n" "$p"
        done
        printf "\n"
    fi

    if [[ ${#desc_mismatches[@]} -gt 0 ]]; then
        printf "${YELLOW}Empty description in agent-rig.json:${NC}\n"
        for p in "${desc_mismatches[@]}"; do
            printf "  ${YELLOW}!${NC} %s\n" "$p"
        done
        printf "\n"
    fi

    if [[ "$VERBOSE" == true && ${#not_in_marketplace[@]} -gt 0 ]]; then
        printf "${DIM}Not in marketplace (unpublished):${NC}\n"
        for p in "${not_in_marketplace[@]}"; do
            printf "  ${DIM}· %s${NC}\n" "$p"
        done
        printf "\n"
    fi

    if [[ $drift_count -eq 0 ]]; then
        printf "${GREEN}✓ No drift detected${NC}\n"
        rig_count=$(echo "$rig_plugins" | wc -l | tr -d ' ')
        iv_count=$(echo "$interverse_plugins" | wc -l | tr -d ' ')
        printf "${DIM}  %s plugins in rig, %s in interverse${NC}\n" "$rig_count" "$iv_count"
    else
        printf "${RED}✗ %d drift issues found${NC}\n" "$drift_count"
    fi
fi

exit $( [[ $drift_count -eq 0 ]] && echo 0 || echo 1 )
