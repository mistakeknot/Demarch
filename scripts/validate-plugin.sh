#!/bin/bash
#
# validate-plugin — structural validator for Claude Code plugins.
#
# Checks plugin.json schema, declared file existence, hooks format,
# hardcoded secrets, and marketplace version alignment.
#
# Usage:
#   validate-plugin.sh              # run from plugin root
#   validate-plugin.sh --all        # scan all interverse/* plugins
#   validate-plugin.sh --help
#
# Exit codes: 0 = pass (warnings ok), 1 = errors found, 2 = usage error

set -euo pipefail

# --- Colors (TTY-aware) ---
if [ -t 1 ]; then
    RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[0;33m'; CYAN='\033[0;36m'; NC='\033[0m'
else
    RED=''; GREEN=''; YELLOW=''; CYAN=''; NC=''
fi

ERRORS=0
WARNINGS=0
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

error() { echo -e "${RED}[ERROR]${NC} $1"; ERRORS=$((ERRORS + 1)); }
warn()  { echo -e "${YELLOW}[WARN]${NC}  $1" >&2; WARNINGS=$((WARNINGS + 1)); }
ok()    { echo -e "${GREEN}[OK]${NC}    $1"; }

usage() {
    echo "Usage: $0 [--all] [--help]"
    echo ""
    echo "  (no args)  Validate the plugin in the current directory"
    echo "  --all      Validate all plugins under interverse/*"
    echo "  --help     Show this help"
    exit 2
}

# =============================================================================
# Validate a single plugin at the given root directory
# =============================================================================
validate_plugin() {
    local plugin_root="$1"
    local plugin_json="$plugin_root/.claude-plugin/plugin.json"

    # --- 1. plugin.json exists and is valid JSON ---
    if [ ! -f "$plugin_json" ]; then
        error "No .claude-plugin/plugin.json found at $plugin_root"
        return
    fi

    if ! jq empty "$plugin_json" 2>/dev/null; then
        error "plugin.json: invalid JSON"
        return  # can't continue if JSON is broken
    fi
    ok "plugin.json: valid JSON"

    local plugin_name
    plugin_name=$(jq -r '.name // empty' "$plugin_json")

    # --- 2. Required fields ---
    if [ -z "$plugin_name" ]; then
        error "plugin.json: missing required field 'name'"
    fi

    local version
    version=$(jq -r '.version // empty' "$plugin_json")
    if [ -z "$version" ]; then
        error "plugin.json: missing required field 'version'"
    elif ! echo "$version" | grep -qE '^[0-9]+\.[0-9]+\.[0-9]+(-[a-zA-Z0-9.]+)?$'; then
        error "plugin.json: version '$version' is not valid semver (expected X.Y.Z)"
    fi

    # --- 3. Author format ---
    local author_type
    author_type=$(jq -r '.author | type' "$plugin_json")
    if [ "$author_type" = "string" ]; then
        error "plugin.json: author must be object with .name, got string"
    elif [ "$author_type" = "object" ]; then
        local author_name
        author_name=$(jq -r '.author.name // empty' "$plugin_json")
        if [ -z "$author_name" ]; then
            error "plugin.json: author object missing required field 'name'"
        fi
    elif [ "$author_type" != "null" ]; then
        error "plugin.json: author must be object, got $author_type"
    fi

    # --- 4-6. Declared files exist on disk ---
    local all_ok=true

    # Skills — must be directories
    local skills
    skills=$(jq -r '.skills[]? // empty' "$plugin_json" 2>/dev/null)
    while IFS= read -r entry; do
        [ -z "$entry" ] && continue
        local resolved="$plugin_root/${entry#./}"
        if [ ! -e "$resolved" ]; then
            error "skills: declared path '$entry' does not exist"
            all_ok=false
        elif [ ! -d "$resolved" ]; then
            error "skills: '$entry' must be a directory, got file"
            all_ok=false
        fi
    done <<< "$skills"

    # Commands — must be .md files
    local commands
    commands=$(jq -r '.commands[]? // empty' "$plugin_json" 2>/dev/null)
    while IFS= read -r entry; do
        [ -z "$entry" ] && continue
        local resolved="$plugin_root/${entry#./}"
        if [ ! -f "$resolved" ]; then
            error "commands: declared file '$entry' does not exist"
            all_ok=false
        fi
    done <<< "$commands"

    # Agents — must be .md files
    local agents
    agents=$(jq -r '.agents[]? // empty' "$plugin_json" 2>/dev/null)
    while IFS= read -r entry; do
        [ -z "$entry" ] && continue
        local resolved="$plugin_root/${entry#./}"
        if [ ! -f "$resolved" ]; then
            error "agents: declared file '$entry' does not exist"
            all_ok=false
        fi
    done <<< "$agents"

    if $all_ok; then
        ok "All declared files exist"
    fi

    # --- 7. hooks.json structure ---
    # Check declared hooks path first, then standard locations
    local hooks_path
    hooks_path=$(jq -r '.hooks // empty' "$plugin_json")

    if [ -n "$hooks_path" ]; then
        local hooks_file="$plugin_root/${hooks_path#./}"
        if [ ! -f "$hooks_file" ]; then
            error "hooks: declared file '$hooks_path' does not exist"
        else
            validate_hooks_json "$hooks_file" "$hooks_path"
        fi
    fi

    # Check standard hooks locations on disk
    local std_hooks=""
    if [ -f "$plugin_root/hooks/hooks.json" ]; then
        std_hooks="$plugin_root/hooks/hooks.json"
    elif [ -f "$plugin_root/.claude-plugin/hooks/hooks.json" ]; then
        std_hooks="$plugin_root/.claude-plugin/hooks/hooks.json"
    fi

    if [ -n "$std_hooks" ]; then
        # Validate structure if not already checked via declared path
        local declared_resolved=""
        [ -n "$hooks_path" ] && declared_resolved="$plugin_root/${hooks_path#./}"

        if [ "$std_hooks" != "$declared_resolved" ]; then
            # Standard-path hooks exist but aren't the declared path
            if [ -z "$hooks_path" ]; then
                # 9. Undeclared hooks.json on disk
                warn "hooks/hooks.json exists on disk but not declared in plugin.json (may be auto-loaded)"
            fi
            validate_hooks_json "$std_hooks" "$(basename "$(dirname "$std_hooks")")/hooks.json"
        fi
    fi

    # --- 8. Hardcoded secrets in mcpServers env ---
    local env_values
    env_values=$(jq -r '.mcpServers // {} | to_entries[] | .value.env // {} | to_entries[] | "\(.key)=\(.value)"' "$plugin_json" 2>/dev/null || true)
    while IFS= read -r kv; do
        [ -z "$kv" ] && continue
        local key="${kv%%=*}"
        local val="${kv#*=}"

        # Skip variable references like ${VAR}
        if echo "$val" | grep -qE '^\$\{.*\}$'; then
            continue
        fi
        # Skip empty values
        [ -z "$val" ] && continue

        # Check for patterns that look like literal secrets
        local is_secret=false
        # UUID pattern (like API keys)
        if echo "$val" | grep -qE '^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'; then
            is_secret=true
        fi
        # Long hex string (20+ chars)
        if echo "$val" | grep -qE '^[0-9a-fA-F]{20,}$'; then
            is_secret=true
        fi
        # Base64-shaped (32+ chars, alphanumeric with +/=)
        if echo "$val" | grep -qE '^[A-Za-z0-9+/=]{32,}$'; then
            is_secret=true
        fi
        # sk-/pk-/key- prefixed tokens
        if echo "$val" | grep -qE '^(sk|pk|key|token|secret)-'; then
            is_secret=true
        fi

        if $is_secret; then
            error "mcpServers env: '$key' appears to contain a hardcoded secret (use \${$key} instead)"
        fi
    done <<< "$env_values"

    # --- 10. Undeclared skills/commands/agents on disk ---
    check_undeclared_dir "$plugin_root" "$plugin_json" "skills" "skills"
    check_undeclared_dir "$plugin_root" "$plugin_json" "commands" "commands"
    check_undeclared_dir "$plugin_root" "$plugin_json" "agents" "agents"

    # --- 11. Version mismatch with marketplace ---
    check_marketplace_version "$plugin_root" "$plugin_name" "$version"
}

# =============================================================================
# Validate hooks.json structure
# =============================================================================
validate_hooks_json() {
    local file="$1"
    local label="$2"

    if ! jq empty "$file" 2>/dev/null; then
        error "$label: invalid JSON"
        return
    fi

    local top_type
    top_type=$(jq -r '.hooks | type' "$file" 2>/dev/null)
    if [ "$top_type" = "null" ]; then
        error "$label: missing top-level 'hooks' key"
    elif [ "$top_type" = "array" ]; then
        error "$label: top-level 'hooks' must be an object, got array"
    elif [ "$top_type" != "object" ]; then
        error "$label: top-level 'hooks' must be an object, got $top_type"
    else
        local key_count
        key_count=$(jq '.hooks | keys | length' "$file")
        if [ "$key_count" -eq 0 ]; then
            warn "$label: 'hooks' object is empty (no event handlers defined)"
        fi
    fi
}

# =============================================================================
# Check for undeclared files on disk (warn only)
# =============================================================================
check_undeclared_dir() {
    local plugin_root="$1"
    local plugin_json="$2"
    local dir_name="$3"
    local json_key="$4"

    # Collect declared paths
    local declared
    declared=$(jq -r ".${json_key}[]? // empty" "$plugin_json" 2>/dev/null | while IFS= read -r p; do
        # Normalize: strip leading ./
        echo "${p#./}"
    done)

    # Scan known directories
    local scan_dirs=("$plugin_root/$dir_name")
    # For agents, also check subdirs (interflux uses agents/review/, agents/research/)
    for d in "${scan_dirs[@]}"; do
        [ -d "$d" ] || continue
        # Find .md files (commands/agents) or subdirs (skills)
        while IFS= read -r found; do
            [ -z "$found" ] && continue
            local rel="${found#$plugin_root/}"

            # Check if this path is covered by declarations
            local is_declared=false
            while IFS= read -r decl; do
                [ -z "$decl" ] && continue
                # Exact match
                if [ "$rel" = "$decl" ]; then
                    is_declared=true
                    break
                fi
                # Declared as directory that contains this file
                if [ -d "$plugin_root/$decl" ] && [[ "$rel" == "$decl"/* ]]; then
                    is_declared=true
                    break
                fi
            done <<< "$declared"

            if ! $is_declared; then
                case "$json_key" in
                    skills)
                        # Only warn about directories, not individual skill files within
                        [ -d "$found" ] && warn "$dir_name: undeclared directory '$rel' exists on disk"
                        ;;
                    commands|agents)
                        [[ "$found" == *.md ]] && warn "$dir_name: undeclared file '$rel' exists on disk"
                        ;;
                esac
            fi
        done < <(find "$d" -maxdepth 3 -name "*.md" -o -type d -mindepth 1 -maxdepth 1 2>/dev/null)
    done
}

# =============================================================================
# Check marketplace version alignment
# =============================================================================
check_marketplace_version() {
    local plugin_root="$1"
    local plugin_name="$2"
    local plugin_version="$3"

    [ -z "$plugin_name" ] && return
    [ -z "$plugin_version" ] && return

    # Walk up looking for core/marketplace/ (same pattern as interbump)
    local marketplace_json=""
    local dir="$plugin_root"
    for _ in 1 2 3 4; do
        dir="$(dirname "$dir")"
        if [ -f "$dir/core/marketplace/.claude-plugin/marketplace.json" ]; then
            marketplace_json="$dir/core/marketplace/.claude-plugin/marketplace.json"
            break
        fi
    done
    # Fallback: sibling layout
    if [ -z "$marketplace_json" ] && [ -f "$plugin_root/../interagency-marketplace/.claude-plugin/marketplace.json" ]; then
        marketplace_json="$plugin_root/../interagency-marketplace/.claude-plugin/marketplace.json"
    fi

    if [ -z "$marketplace_json" ]; then
        return  # no marketplace found — skip silently
    fi

    local mp_version
    mp_version=$(jq -r --arg name "$plugin_name" '.plugins[] | select(.name == $name) | .version' "$marketplace_json" 2>/dev/null)

    if [ -z "$mp_version" ]; then
        warn "plugin '$plugin_name' not found in marketplace.json"
    elif [ "$mp_version" != "$plugin_version" ]; then
        warn "version mismatch: plugin.json=$plugin_version, marketplace.json=$mp_version"
    fi
}

# =============================================================================
# Main
# =============================================================================
main() {
    local mode="single"

    for arg in "$@"; do
        case "$arg" in
            --all)  mode="all" ;;
            --help|-h) usage ;;
            *) echo "Unknown argument: $arg" >&2; usage ;;
        esac
    done

    if [ "$mode" = "all" ]; then
        # Find monorepo root — walk up from script location
        local monorepo_root="$SCRIPT_DIR/.."
        local interverse_dir="$monorepo_root/interverse"
        if [ ! -d "$interverse_dir" ]; then
            echo -e "${RED}Error: Cannot find interverse/ directory relative to script${NC}" >&2
            exit 2
        fi

        local total_errors=0 total_warnings=0 plugin_count=0 failed_count=0

        for plugin_dir in "$interverse_dir"/*/; do
            [ -f "$plugin_dir/.claude-plugin/plugin.json" ] || continue
            local name
            name=$(basename "$plugin_dir")

            echo -e "\n${CYAN}━━━ $name ━━━${NC}"
            ERRORS=0
            WARNINGS=0
            validate_plugin "${plugin_dir%/}" || true

            plugin_count=$((plugin_count + 1))
            total_errors=$((total_errors + ERRORS))
            total_warnings=$((total_warnings + WARNINGS))
            if [ "$ERRORS" -gt 0 ]; then failed_count=$((failed_count + 1)); fi
        done

        echo -e "\n${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
        echo -e "validate-plugin --all: $plugin_count plugins, ${RED}$total_errors errors${NC}, ${YELLOW}$total_warnings warnings${NC}, $failed_count failed"

        if [ "$total_errors" -gt 0 ]; then exit 1; fi
        exit 0
    fi

    # Single plugin mode
    local plugin_root
    plugin_root="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"

    if [ ! -f "$plugin_root/.claude-plugin/plugin.json" ]; then
        echo -e "${RED}Error: Not in a plugin directory (no .claude-plugin/plugin.json)${NC}" >&2
        exit 2
    fi

    validate_plugin "$plugin_root" || true

    echo ""
    echo -e "validate-plugin: ${RED}$ERRORS errors${NC}, ${YELLOW}$WARNINGS warnings${NC}"

    if [ "$ERRORS" -gt 0 ]; then exit 1; fi
    exit 0
}

main "$@"
