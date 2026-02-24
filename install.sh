#!/usr/bin/env bash
# install.sh — Curl-fetchable installer for Demarch (Clavain + Interverse)
#
# Usage:
#   curl -fsSL https://raw.githubusercontent.com/mistakeknot/Demarch/main/install.sh | bash
#   bash install.sh [--help] [--dry-run] [--verbose]
#
# Flags:
#   --help      Show this usage message and exit
#   --dry-run   Show what would happen without executing
#   --verbose   Enable debug output

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
VERBOSE=false
HAS_BD=false
CACHE_DIR="${HOME}/.claude/plugins/cache"

# --- Parse arguments ---
for arg in "$@"; do
    case "$arg" in
        --help|-h)
            sed -n '2,/^$/p' "$0" | sed 's/^# \?//'
            exit 0
            ;;
        --dry-run) DRY_RUN=true ;;
        --verbose) VERBOSE=true ;;
        *)
            printf "${RED}Unknown flag: %s${RESET}\n" "$arg"
            printf "Run with --help for usage.\n"
            exit 1
            ;;
    esac
done

# --- Logging ---
log() {
    printf "%b\n" "$*"
}

debug() {
    if [[ "$VERBOSE" == true ]]; then
        printf "${DIM}  [debug] %s${RESET}\n" "$*"
    fi
}

success() {
    printf "${GREEN}  ✓ %s${RESET}\n" "$*"
}

warn() {
    printf "${YELLOW}  ! %s${RESET}\n" "$*"
}

fail() {
    printf "${RED}  ✗ %s${RESET}\n" "$*"
}

# --- Command execution (dry-run aware) ---
run() {
    if [[ "$DRY_RUN" == true ]]; then
        printf "${DIM}  [DRY RUN] %s${RESET}\n" "$*"
        return 0
    fi
    debug "exec: $*"
    eval "$@"
}

# --- Prerequisites ---
log ""
log "${BOLD}Demarch Installer${RESET}"
log "${DIM}Clavain + Interverse plugin ecosystem${RESET}"
log ""

log "${BOLD}Checking prerequisites...${RESET}"

# claude CLI (REQUIRED)
if command -v claude &>/dev/null; then
    success "claude CLI found"
    debug "$(command -v claude)"
else
    fail "claude CLI not found"
    log "  Claude Code is required. Install: ${BLUE}https://claude.ai/download${RESET}"
    exit 1
fi

# jq (REQUIRED)
if command -v jq &>/dev/null; then
    success "jq found"
    debug "$(command -v jq)"
else
    fail "jq not found"
    log "  jq is required. Install: ${BLUE}https://jqlang.github.io/jq/download/${RESET}"
    exit 1
fi

# git (WARN)
if command -v git &>/dev/null; then
    success "git found"
    debug "$(command -v git)"
else
    warn "git not found (not required, but recommended)"
fi

# bd / Beads CLI (OPTIONAL)
if command -v bd &>/dev/null; then
    success "bd (Beads CLI) found"
    debug "$(command -v bd)"
    HAS_BD=true
else
    warn "Beads CLI (bd) not found. Install with: go install github.com/mistakeknot/beads/cmd/bd@latest"
fi

log ""

# --- Installation ---
log "${BOLD}Installing...${RESET}"

# Step 1: Add marketplace
log "  Adding interagency-marketplace..."
run 'claude plugins marketplace add mistakeknot/interagency-marketplace 2>/dev/null || true'
if [[ "$DRY_RUN" != true ]]; then
    success "Marketplace added"
fi

# Step 2: Install Clavain
log "  Installing Clavain..."
run 'claude plugins install clavain@interagency-marketplace 2>/dev/null || true'
if [[ "$DRY_RUN" != true ]]; then
    success "Clavain installed"
fi

# Step 3: Beads init (conditional)
if [[ "$HAS_BD" == true ]] && git rev-parse --is-inside-work-tree &>/dev/null 2>&1; then
    log "  Initializing Beads in current project..."
    run 'bd init 2>/dev/null || true'
    if [[ "$DRY_RUN" != true ]]; then
        success "Beads initialized"
    fi
else
    debug "Skipping bd init (bd not available or not in a git repo)"
fi

log ""

# --- Verification ---
log "${BOLD}Verifying installation...${RESET}"

if [[ "$DRY_RUN" == true ]]; then
    log "  ${DIM}[DRY RUN] Would check for ${CACHE_DIR}/interagency-marketplace/clavain/${RESET}"
    log ""
    success "Dry run complete — no changes made"
elif [[ -d "${CACHE_DIR}/interagency-marketplace/clavain" ]]; then
    success "Clavain installed successfully!"
else
    fail "Installation may have failed. Run 'claude plugins list' to check."
    exit 1
fi

# --- Next steps ---
log ""
log "${GREEN}✓ Demarch installed successfully!${RESET}"
log ""
log "${BOLD}Next steps:${RESET}"
log "  1. Open Claude Code in any project:  ${BLUE}claude${RESET}"
log "  2. Install companion plugins:        ${BLUE}/clavain:setup${RESET}"
log "  3. Start working:                    ${BLUE}/clavain:route${RESET}"
log ""
log "${BOLD}Guides:${RESET}"
log "  Power user:   ${BLUE}https://github.com/mistakeknot/Demarch/blob/main/docs/guide-power-user.md${RESET}"
log "  Full setup:   ${BLUE}https://github.com/mistakeknot/Demarch/blob/main/docs/guide-full-setup.md${RESET}"
log "  Contributing: ${BLUE}https://github.com/mistakeknot/Demarch/blob/main/docs/guide-contributing.md${RESET}"
log ""
