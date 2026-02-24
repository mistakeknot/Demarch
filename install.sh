#!/usr/bin/env bash
# install.sh -- Curl-fetchable installer for Demarch (Clavain + Interverse)
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
            cat <<'USAGE'
install.sh -- Curl-fetchable installer for Demarch (Clavain + Interverse)

Usage:
  curl -fsSL https://raw.githubusercontent.com/mistakeknot/Demarch/main/install.sh | bash
  bash install.sh [--help] [--dry-run] [--verbose]

Flags:
  --help      Show this usage message and exit
  --dry-run   Show what would happen without executing
  --verbose   Enable debug output
USAGE
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
    "$@"
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

# go (REQUIRED, builds intercore kernel)
if command -v go &>/dev/null; then
    go_ver=$(go version | grep -Eo 'go[0-9]+\.[0-9]+' | head -1 | sed 's/go//')
    go_major="${go_ver%%.*}"
    go_minor="${go_ver#*.}"
    if [[ "$go_major" -ge 2 ]] || { [[ "$go_major" -eq 1 ]] && [[ "$go_minor" -ge 22 ]]; }; then
        success "go ${go_ver} found (>= 1.22)"
    else
        fail "go ${go_ver} found but >= 1.22 required"
        log "  Update Go: ${BLUE}https://go.dev/dl/${RESET}"
        exit 1
    fi
else
    fail "go not found"
    log "  Go >= 1.22 is required to build the intercore kernel."
    log "  Install: ${BLUE}https://go.dev/dl/${RESET}"
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
MARKET_OUT=$(run claude plugin marketplace add mistakeknot/interagency-marketplace 2>&1) && {
    [[ "$DRY_RUN" != true ]] && success "Marketplace added"
} || {
    if echo "$MARKET_OUT" | grep -qi "already"; then
        [[ "$DRY_RUN" != true ]] && success "Marketplace already added"
    else
        fail "Marketplace add failed:"
        log "  $MARKET_OUT"
        exit 1
    fi
}

# Step 1b: Update marketplace (ensures latest plugin versions)
log "  Updating marketplace..."
if run claude plugin marketplace update interagency-marketplace 2>&1; then
    [[ "$DRY_RUN" != true ]] && success "Marketplace updated"
else
    warn "Marketplace update returned non-zero (continuing with cached version)"
fi

# Step 2: Install Clavain
log "  Installing Clavain..."
INSTALL_OUT=$(run claude plugin install clavain@interagency-marketplace 2>&1) && {
    [[ "$DRY_RUN" != true ]] && success "Clavain installed"
} || {
    if echo "$INSTALL_OUT" | grep -qi "already"; then
        [[ "$DRY_RUN" != true ]] && success "Clavain already installed"
    else
        fail "Clavain install failed:"
        log "  $INSTALL_OUT"
        exit 1
    fi
}

# Step 3: Install Interverse companion plugins
CLAVAIN_DIR=$(find "${CACHE_DIR}/interagency-marketplace/clavain" -name "agent-rig.json" -exec dirname {} \; 2>/dev/null | sort -V | tail -1)
MODPACK="${CLAVAIN_DIR}/scripts/modpack-install.sh"

if [[ -n "$CLAVAIN_DIR" ]] && [[ -f "$MODPACK" ]]; then
    log ""
    log "${BOLD}Installing Interverse companion plugins...${RESET}"
    MODPACK_FLAGS=""
    [[ "$DRY_RUN" == true ]] && MODPACK_FLAGS="--dry-run"
    [[ "$VERBOSE" != true ]] && MODPACK_FLAGS="$MODPACK_FLAGS --quiet"

    if MODPACK_OUT=$(bash "$MODPACK" $MODPACK_FLAGS 2>/dev/null); then
        # JSON is on stdout; stderr was suppressed
        MODPACK_JSON=$(echo "$MODPACK_OUT" | grep -E '^\{' | tail -1)
        N_INSTALLED=$(echo "$MODPACK_JSON" | jq -r '.installed // .would_install | length' 2>/dev/null || echo "?")
        N_PRESENT=$(echo "$MODPACK_JSON" | jq -r '.already_present | length' 2>/dev/null || echo "?")
        N_FAILED=$(echo "$MODPACK_JSON" | jq -r '.failed | length' 2>/dev/null || echo "0")

        N_OPTIONAL=$(echo "$MODPACK_JSON" | jq -r '.optional_available | length' 2>/dev/null || echo "0")

        if [[ "$DRY_RUN" == true ]]; then
            success "Would install ${N_INSTALLED} plugins (${N_PRESENT} already present)"
        else
            success "Installed ${N_INSTALLED} new plugins (${N_PRESENT} already present)"
            if [[ "$N_FAILED" != "0" ]] && [[ "$N_FAILED" != "null" ]]; then
                warn "${N_FAILED} plugins failed to install"
                echo "$MODPACK_JSON" | jq -r '.failed[]' 2>/dev/null | while read -r p; do
                    warn "  Failed: $p"
                done
            fi
        fi

        if [[ "$N_OPTIONAL" != "0" ]] && [[ "$N_OPTIONAL" != "null" ]]; then
            log "  ${DIM}${N_OPTIONAL} optional plugins available. Run /clavain:setup in Claude Code to browse and install them.${RESET}"
        fi
    else
        warn "Modpack install had errors (continuing)"
        [[ "$VERBOSE" == true ]] && log "  $MODPACK_OUT"
    fi
elif [[ -n "$CLAVAIN_DIR" ]]; then
    warn "Modpack install script not found at $MODPACK"
    warn "Run /clavain:setup in Claude Code to install companion plugins"
else
    warn "Clavain install directory not found in cache"
    warn "Run /clavain:setup in Claude Code to install companion plugins"
fi

log ""

# Step 4: Beads init (conditional)
if [[ "$HAS_BD" == true ]] && git rev-parse --is-inside-work-tree &>/dev/null; then
    log "  Initializing Beads in current project..."
    if run bd init 2>/dev/null; then
        [[ "$DRY_RUN" != true ]] && success "Beads initialized"
    else
        warn "Beads init returned non-zero (may already be initialized, continuing)"
    fi
else
    debug "Skipping bd init (bd not available or not in a git repo)"
fi

# Step 5: Build intercore kernel (ic)
log "  Building intercore kernel (ic)..."

# Determine source directory
IC_SRC=""
if [[ -f "core/intercore/cmd/ic/main.go" ]]; then
    IC_SRC="core/intercore"
elif [[ -f "../core/intercore/cmd/ic/main.go" ]]; then
    IC_SRC="../core/intercore"
fi

if [[ -z "$IC_SRC" ]]; then
    # Curl-pipe mode: clone intercore repo directly
    IC_TMPDIR=$(mktemp -d)
    trap 'rm -rf "$IC_TMPDIR"' EXIT
    log "    Cloning intercore source..."
    if run git clone --depth=1 https://github.com/mistakeknot/intercore.git "$IC_TMPDIR/intercore" 2>/dev/null; then
        IC_SRC="$IC_TMPDIR/intercore"
    else
        warn "Could not clone intercore source. Run '/clavain:setup' after cloning the repo to build ic."
        IC_SRC=""
    fi
fi

if [[ -n "$IC_SRC" ]]; then
    # Ensure ~/.local/bin exists
    run mkdir -p "${HOME}/.local/bin"

    if run go build -C "$IC_SRC" -mod=readonly -o "${HOME}/.local/bin/ic" ./cmd/ic; then
        [[ "$DRY_RUN" != true ]] && success "ic built and installed to ~/.local/bin/ic"
    else
        fail "ic build failed"
        log "  Try manually: go build -C core/intercore -o ~/.local/bin/ic ./cmd/ic"
        exit 1
    fi

    # Initialize ic database
    if [[ "$DRY_RUN" != true ]]; then
        if "${HOME}/.local/bin/ic" init 2>/dev/null; then
            success "ic database initialized"
        else
            warn "ic init returned non-zero (may already be initialized, continuing)"
        fi

        if "${HOME}/.local/bin/ic" health >/dev/null 2>&1; then
            success "ic health check passed"
        else
            warn "ic health check failed. Run 'ic health' to diagnose."
        fi
    fi

    # Check if ~/.local/bin is on PATH
    if ! echo "$PATH" | tr ':' '\n' | grep -qx "${HOME}/.local/bin"; then
        warn "~/.local/bin is not on your PATH"
        log "  Add to your shell config: ${BLUE}export PATH=\"\$HOME/.local/bin:\$PATH\"${RESET}"
    fi
else
    warn "Skipping ic build (source not available)"
fi

log ""

# --- Verification ---
log "${BOLD}Verifying installation...${RESET}"

if [[ "$DRY_RUN" == true ]]; then
    log "  ${DIM}[DRY RUN] Would verify Clavain installation via 'claude plugin list'${RESET}"
    log ""
    success "Dry run complete, no changes made"
elif claude plugin list 2>/dev/null | grep -q "clavain"; then
    success "Clavain installed and loaded!"
elif [[ -d "${CACHE_DIR}/interagency-marketplace/clavain" ]]; then
    warn "Clavain files found in cache but not in 'claude plugin list'. May need session restart."
else
    fail "Installation may have failed. Run 'claude plugin list' to check."
    exit 1
fi

# Verify ic
if command -v ic &>/dev/null; then
    if ic health >/dev/null 2>&1; then
        success "ic kernel healthy"
    else
        warn "ic found but health check failed"
    fi
elif [[ -x "${HOME}/.local/bin/ic" ]]; then
    warn "ic built but not on PATH. Add ~/.local/bin to PATH."
else
    warn "ic not found, kernel features will be unavailable"
fi

# --- Next steps ---
log ""
log "${GREEN}✓ Demarch installed successfully!${RESET}"
log ""
log "${BOLD}Next steps:${RESET}"
log "  1. Ensure ~/.local/bin is on PATH:  ${BLUE}export PATH=\"\$HOME/.local/bin:\$PATH\"${RESET}"
log "  2. Open Claude Code in any project:  ${BLUE}claude${RESET}"
log "  3. Install companion plugins:        ${BLUE}/clavain:setup${RESET}"
log "  4. Start working:                    ${BLUE}/clavain:route${RESET}"
log ""
log "${BOLD}Guides:${RESET}"
log "  Power user:   ${BLUE}https://github.com/mistakeknot/Demarch/blob/main/docs/guide-power-user.md${RESET}"
log "  Full setup:   ${BLUE}https://github.com/mistakeknot/Demarch/blob/main/docs/guide-full-setup.md${RESET}"
log "  Contributing: ${BLUE}https://github.com/mistakeknot/Demarch/blob/main/docs/guide-contributing.md${RESET}"
log ""
