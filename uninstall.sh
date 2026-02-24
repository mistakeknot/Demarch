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

# --- Colors (TTY-aware) ---
if [ -t 1 ]; then
    RED='\033[0;31m'
    GREEN='\033[0;32m'
    YELLOW='\033[0;33m'
    BLUE='\033[0;34m'
    BOLD='\033[1m'
    DIM='\033[2m'
    RESET='\033[0m'
else
    RED=''
    GREEN=''
    YELLOW=''
    BLUE=''
    BOLD=''
    DIM=''
    RESET=''
fi

# --- State ---
DRY_RUN=false
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

# --- Logging ---
log() { printf "%b\n" "$*"; }
success() { printf "${GREEN}  ✓ %s${RESET}\n" "$*"; }
warn() { printf "${YELLOW}  ! %s${RESET}\n" "$*"; }
fail() { printf "${RED}  ✗ %s${RESET}\n" "$*"; }

run() {
    if [[ "$DRY_RUN" == true ]]; then
        printf "${DIM}  [DRY RUN] %s${RESET}\n" "$*"
        return 0
    fi
    "$@"
}

# --- Preflight ---
log ""
log "${BOLD}Demarch Uninstaller${RESET}"
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

# --- Done ---
log ""
if [[ "$DRY_RUN" == true ]]; then
    success "Dry run complete, no changes made"
else
    success "Demarch uninstalled"
    log ""
    log "  To reinstall: ${BLUE}curl -fsSL https://raw.githubusercontent.com/mistakeknot/Demarch/main/install.sh | bash${RESET}"
fi
log ""
