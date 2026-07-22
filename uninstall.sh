#!/usr/bin/env bash
# uninstall.sh -- Remove Clavain and interagency-marketplace plugins
#
# Usage:
#   bash uninstall.sh [--help] [--dry-run] [--keep-marketplace]
#
# Flags:
#   --help              Show this usage message and exit
#   --dry-run           Show what would happen without executing
#   --keep-marketplace  Remove plugins but keep the marketplace registered

set -euo pipefail

# --- Shared helpers ---
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DRY_RUN=false  # must be set before sourcing (run() depends on it)
source "$SCRIPT_DIR/lib/installer-common.sh"

# --- State ---
KEEP_MARKETPLACE=false
CACHE_DIR="${HOME}/.claude/plugins/cache/interagency-marketplace"

# --- Parse arguments ---
for arg in "$@"; do
    case "$arg" in
        --help|-h)
            cat <<'USAGE'
uninstall.sh -- Remove Clavain and interagency-marketplace plugins

Usage:
  bash uninstall.sh [--help] [--dry-run] [--keep-marketplace]

Flags:
  --help              Show this usage message and exit
  --dry-run           Show what would happen without executing
  --keep-marketplace  Remove plugins but keep the marketplace registered
USAGE
            exit 0
            ;;
        --dry-run) DRY_RUN=true ;;
        --keep-marketplace) KEEP_MARKETPLACE=true ;;
        *)
            printf "${RED}Unknown flag: %s${RESET}\n" "$arg"
            printf "Run with --help for usage.\n"
            exit 1
            ;;
    esac
done

# --- Preflight ---
log ""
log "${BOLD}Sylveste Uninstaller${RESET}"
log ""

if ! command -v claude &>/dev/null; then
    fail "claude CLI not found, nothing to uninstall"
    exit 0
fi

# --- Discover installed interagency plugins ---
log "${BOLD}Finding installed interagency-marketplace plugins...${RESET}"

PLUGINS=()
if [[ -d "$CACHE_DIR" ]]; then
    for dir in "$CACHE_DIR"/*/; do
        [[ -d "$dir" ]] || continue
        name=$(basename "$dir")
        PLUGINS+=("$name")
    done
fi

if [[ ${#PLUGINS[@]} -eq 0 ]]; then
    warn "No interagency-marketplace plugins found in cache"
else
    log "  Found ${#PLUGINS[@]} plugins: ${PLUGINS[*]}"
fi

# --- Uninstall plugins ---
log ""
log "${BOLD}Uninstalling plugins...${RESET}"

for plugin in "${PLUGINS[@]}"; do
    log "  Removing ${plugin}..."
    if run claude plugin uninstall "${plugin}@interagency-marketplace" 2>&1; then
        [[ "$DRY_RUN" != true ]] && success "Removed ${plugin}"
    else
        warn "Could not uninstall ${plugin} (may already be removed)"
    fi
done

# --- Remove marketplace ---
if [[ "$KEEP_MARKETPLACE" == false ]]; then
    log ""
    log "${BOLD}Removing marketplace...${RESET}"
    if run claude plugin marketplace remove interagency-marketplace 2>&1; then
        [[ "$DRY_RUN" != true ]] && success "Marketplace removed"
    else
        warn "Could not remove marketplace (may already be removed)"
    fi
else
    log ""
    log "  ${DIM}Keeping marketplace registered (--keep-marketplace)${RESET}"
fi

# --- Clean cache ---
if [[ -d "$CACHE_DIR" ]] && [[ "$KEEP_MARKETPLACE" == false ]]; then
    log ""
    log "${BOLD}Cleaning cache...${RESET}"
    if run rm -rf "$CACHE_DIR"; then
        [[ "$DRY_RUN" != true ]] && success "Cache cleared"
    fi
fi

# --- Gemini CLI ---
if command -v gemini &>/dev/null; then
    log ""
    log "${BOLD}Uninstalling Gemini skills...${RESET}"
    
    GEMINI_SOURCE=""
    if [[ -f "scripts/install-gemini-interverse.sh" ]]; then
        GEMINI_SOURCE="."
    elif [[ -f "${HOME}/.local/share/Sylveste/scripts/install-gemini-interverse.sh" ]]; then
        GEMINI_SOURCE="${HOME}/.local/share/Sylveste"
    fi
    
    if [[ -n "$GEMINI_SOURCE" ]]; then
        if [[ "$DRY_RUN" == true ]]; then
            log "  ${DIM}[DRY RUN] Would run bash ${GEMINI_SOURCE}/scripts/install-gemini-interverse.sh uninstall${RESET}"
        else
            if bash "$GEMINI_SOURCE/scripts/install-gemini-interverse.sh" uninstall >/dev/null 2>&1; then
                success "Gemini skills uninstalled"
            else
                warn "Could not uninstall Gemini skills"
            fi
        fi
    else
        warn "Gemini uninstall script not found. Remove skills manually: gemini skills uninstall <skill_name> --scope user"
    fi
fi

# --- Kimi Code CLI ---
if command -v kimi &>/dev/null; then
    log ""
    log "${BOLD}Uninstalling Kimi integration...${RESET}"

    KIMI_SOURCE=""
    if [[ -f "os/Clavain/scripts/install-kimi.sh" ]]; then
        KIMI_SOURCE="$(cd "os/Clavain" && pwd)"
    elif [[ -f "$SCRIPT_DIR/os/Clavain/scripts/install-kimi.sh" ]]; then
        KIMI_SOURCE="$SCRIPT_DIR/os/Clavain"
    elif [[ -f "${HOME}/.local/share/Sylveste/os/Clavain/scripts/install-kimi.sh" ]]; then
        KIMI_SOURCE="${HOME}/.local/share/Sylveste/os/Clavain"
    fi

    if [[ -n "$KIMI_SOURCE" ]]; then
        if [[ "$DRY_RUN" == true ]]; then
            log "  ${DIM}[DRY RUN] Would run bash ${KIMI_SOURCE}/scripts/install-kimi.sh uninstall --source ${KIMI_SOURCE}${RESET}"
        else
            if bash "$KIMI_SOURCE/scripts/install-kimi.sh" uninstall --source "$KIMI_SOURCE" >/dev/null 2>&1; then
                success "Kimi integration uninstalled"
            else
                warn "Could not uninstall Kimi integration"
            fi
        fi
    else
        warn "Kimi uninstall script not found. Remove manually: ~/.agents/skills/clavain symlink and managed blocks in ~/.kimi-code/"
    fi
fi

# --- Done ---
log ""
if [[ "$DRY_RUN" == true ]]; then
    success "Dry run complete, no changes made"
else
    success "Sylveste uninstalled"
    log ""
    log "  To reinstall: ${BLUE}curl -fsSL https://raw.githubusercontent.com/mistakeknot/Sylveste/main/install.sh | bash${RESET}"
fi
log ""
