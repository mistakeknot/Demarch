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

# claude CLI (OPTIONAL for core/companion, REQUIRED for Claude plugins)
if command -v claude &>/dev/null; then
    success "claude CLI found"
    debug "$(command -v claude)"
    HAS_CLAUDE=true
else
    warn "claude CLI not found"
    log "  Claude Code is required for Claude plugins. Install: ${BLUE}https://claude.ai/download${RESET}"
    HAS_CLAUDE=false
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

if [[ "$HAS_CLAUDE" == true ]]; then
    # Step 0: Fix stale marketplace paths in known_marketplaces.json
    # Claude Code stores absolute installLocation paths at add-time. If the user's
    # $HOME has changed (different machine, different user, dotfile sync), marketplace
    # update fails trying to clone to a nonexistent path. Fix: rewrite all
    # installLocation values to use the current $HOME.
    KNOWN_MKT="${HOME}/.claude/plugins/known_marketplaces.json"
    if [[ -f "$KNOWN_MKT" ]] && command -v jq &>/dev/null; then
        EXPECTED_PREFIX="${HOME}/.claude/plugins/marketplaces"
        NEEDS_FIX=$(jq -r --arg pfx "$EXPECTED_PREFIX" '
            to_entries[]
            | select(.value.installLocation != null)
            | select(.value.installLocation | startswith($pfx) | not)
            | .key' "$KNOWN_MKT" 2>/dev/null)
        if [[ -n "$NEEDS_FIX" ]]; then
            debug "Fixing stale marketplace paths in known_marketplaces.json"
            jq --arg prefix "$EXPECTED_PREFIX" '
                to_entries | map(
                    if .value.installLocation != null then
                        .value.installLocation = ($prefix + "/" + .key)
                    else . end
                ) | from_entries' "$KNOWN_MKT" > "${KNOWN_MKT}.tmp" && \
                mv "${KNOWN_MKT}.tmp" "$KNOWN_MKT"
            success "Fixed marketplace paths for current \$HOME"
        fi
    fi

    # Step 0b: Remove legacy superpowers/compound-engineering marketplaces
    LEGACY_MARKETPLACES=(superpowers-marketplace every-marketplace)
    for mkt in "${LEGACY_MARKETPLACES[@]}"; do
        if [[ -f "$KNOWN_MKT" ]] && jq -e --arg m "$mkt" 'has($m)' "$KNOWN_MKT" &>/dev/null; then
            log "  Removing legacy marketplace: $mkt"
            if [[ "$DRY_RUN" == true ]]; then
                log "  ${DIM}[DRY RUN] Would remove $mkt from known_marketplaces.json${RESET}"
            else
                # Remove from known_marketplaces.json
                jq --arg m "$mkt" 'del(.[$m])' "$KNOWN_MKT" > "${KNOWN_MKT}.tmp" && \
                    mv "${KNOWN_MKT}.tmp" "$KNOWN_MKT"
                # Remove marketplace checkout directory
                if [[ -d "${HOME}/.claude/plugins/marketplaces/$mkt" ]]; then
                    rm -rf "${HOME}/.claude/plugins/marketplaces/$mkt"
                fi
                success "Removed legacy marketplace: $mkt"
            fi
        fi
    done

    # Step 1: Add marketplace
    log "  Adding interagency-marketplace..."
    if MARKET_OUT=$(run claude plugin marketplace add mistakeknot/interagency-marketplace 2>&1); then
        [[ "$DRY_RUN" != true ]] && success "Marketplace added" || true
    else
        if echo "$MARKET_OUT" | grep -qi "already"; then
            [[ "$DRY_RUN" != true ]] && success "Marketplace already added" || true
        else
            fail "Marketplace add failed:"
            log "  $MARKET_OUT"
            exit 1
        fi
    fi

    # Step 1b: Update marketplace (ensures latest plugin versions)
    log "  Updating marketplace..."
    if run claude plugin marketplace update interagency-marketplace 2>&1; then
        [[ "$DRY_RUN" != true ]] && success "Marketplace updated"
    else
        warn "Marketplace update returned non-zero (continuing with cached version)"
    fi

    # Step 2: Install Clavain
    log "  Installing Clavain..."
    if INSTALL_OUT=$(run claude plugin install clavain@interagency-marketplace 2>&1); then
        [[ "$DRY_RUN" != true ]] && success "Clavain installed" || true
    else
        if echo "$INSTALL_OUT" | grep -qi "already"; then
            [[ "$DRY_RUN" != true ]] && success "Clavain already installed" || true
        else
            fail "Clavain install failed:"
            log "  $INSTALL_OUT"
            exit 1
        fi
    fi

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
            # JSON is on stdout (multi-line); pipe full output through jq
            N_INSTALLED=$(echo "$MODPACK_OUT" | jq -r '.installed // .would_install | length' 2>/dev/null || echo "?")
            N_PRESENT=$(echo "$MODPACK_OUT" | jq -r '.already_present | length' 2>/dev/null || echo "?")
            N_FAILED=$(echo "$MODPACK_OUT" | jq -r '.failed | length' 2>/dev/null || echo "0")

            N_OPTIONAL=$(echo "$MODPACK_OUT" | jq -r '.optional_available | length' 2>/dev/null || echo "0")

            if [[ "$DRY_RUN" == true ]]; then
                success "Would install ${N_INSTALLED} plugins (${N_PRESENT} already present)"
            else
                success "Installed ${N_INSTALLED} new plugins (${N_PRESENT} already present)"
                if [[ "$N_FAILED" != "0" ]] && [[ "$N_FAILED" != "null" ]]; then
                    warn "${N_FAILED} plugins failed to install"
                    echo "$MODPACK_OUT" | jq -r '.failed[]' 2>/dev/null | while read -r p; do
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

fi

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

# --- Codex CLI (optional) ---
if command -v codex &>/dev/null; then
    log "${BOLD}Codex CLI detected — installing Codex skills...${RESET}"

    # Determine Clavain source for the interverse installer
    CODEX_SOURCE=""
    if [[ -n "${CLAVAIN_DIR:-}" ]] && [[ -f "$CLAVAIN_DIR/scripts/install-codex-interverse.sh" ]]; then
        CODEX_SOURCE="$CLAVAIN_DIR"
    elif [[ -f "os/clavain/scripts/install-codex-interverse.sh" ]]; then
        CODEX_SOURCE="os/clavain"
    fi

    if [[ -z "$CODEX_SOURCE" ]] && command -v git &>/dev/null; then
        # Curl-pipe mode: clone Clavain for Codex skill install
        CODEX_CLONE_DIR="${HOME}/.codex/clavain"
        if [[ -d "$CODEX_CLONE_DIR/.git" ]]; then
            log "  Updating Clavain checkout at $CODEX_CLONE_DIR"
            git -C "$CODEX_CLONE_DIR" pull --ff-only 2>/dev/null || true
        else
            log "  Cloning Clavain for Codex skills..."
            git clone https://github.com/mistakeknot/Clavain.git "$CODEX_CLONE_DIR" 2>/dev/null || true
        fi
        if [[ -f "$CODEX_CLONE_DIR/scripts/install-codex-interverse.sh" ]]; then
            CODEX_SOURCE="$CODEX_CLONE_DIR"
        fi
    fi

    if [[ -n "$CODEX_SOURCE" ]]; then
        if [[ "$DRY_RUN" == true ]]; then
            log "  ${DIM}[DRY RUN] Would install Codex skills via install-codex-interverse.sh${RESET}"
        else
            if bash "$CODEX_SOURCE/scripts/install-codex-interverse.sh" install --source "$CODEX_SOURCE" 2>&1; then
                success "Codex skills installed (Clavain + companions)"
            else
                warn "Codex skill install had errors (non-fatal, Claude Code install succeeded)"
            fi
        fi
    else
        warn "Codex interverse installer not found — run manually after cloning:"
        log "  ${BLUE}bash os/clavain/scripts/install-codex-interverse.sh install${RESET}"
    fi
    log ""
else
    debug "Codex CLI not found, skipping Codex skill setup"
fi


# --- Gemini CLI (optional) ---
if command -v gemini &>/dev/null; then
    log "${BOLD}Gemini CLI detected — installing Gemini skills...${RESET}"
    GEMINI_SOURCE=""
    
    if [[ -f "scripts/install-gemini-interverse.sh" ]]; then
        GEMINI_SOURCE="."
    elif command -v git &>/dev/null; then
        GEMINI_CLONE_DIR="${HOME}/.local/share/Demarch"
        if [[ -d "$GEMINI_CLONE_DIR/.git" ]]; then
            log "  Updating Demarch checkout at $GEMINI_CLONE_DIR"
            git -C "$GEMINI_CLONE_DIR" pull --ff-only 2>/dev/null || true
            git -C "$GEMINI_CLONE_DIR" submodule update --init --recursive 2>/dev/null || true
        else
            log "  Cloning Demarch for Gemini skills..."
            git clone --recursive https://github.com/mistakeknot/Demarch.git "$GEMINI_CLONE_DIR" 2>/dev/null || true
        fi
        if [[ -f "$GEMINI_CLONE_DIR/scripts/install-gemini-interverse.sh" ]]; then
            GEMINI_SOURCE="$GEMINI_CLONE_DIR"
        fi
    else
        warn "git not found. Cannot clone Demarch for Gemini skills."
    fi
    
    if [[ -n "$GEMINI_SOURCE" ]]; then
        if [[ "$DRY_RUN" == true ]]; then
            log "  ${DIM}[DRY RUN] Would install Gemini skills via install-gemini-interverse.sh${RESET}"
        else
            if bash "$GEMINI_SOURCE/scripts/install-gemini-interverse.sh" install >/dev/null 2>&1; then
                success "Gemini skills generated and linked globally"
            else
                warn "Gemini skill install had errors"
            fi
        fi
    else
        warn "Gemini installer not found. Run manually."
    fi
    log ""
else
    debug "Gemini CLI not found, skipping Gemini skill setup"
fi

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
if command -v codex &>/dev/null; then
    log ""
    log "${BOLD}Codex CLI:${RESET}"
    log "  Skills installed to ~/.agents/skills/ — restart Codex to load them."
    log "  Runbook: ${BLUE}https://github.com/mistakeknot/Demarch/blob/main/docs/guide-codex-setup.md${RESET}"
fi
if command -v gemini &>/dev/null; then
    log ""
    log "${BOLD}Gemini CLI:${RESET}"
    log "  Skills generated and linked to ~/.gemini/skills/ globally."
    log "  Runbook: ${BLUE}https://github.com/mistakeknot/Demarch/blob/main/docs/guide-gemini-setup.md${RESET}"
fi
log ""
log "${BOLD}Guides:${RESET}"
log "  Power user:   ${BLUE}https://github.com/mistakeknot/Demarch/blob/main/docs/guide-power-user.md${RESET}"
log "  Full setup:   ${BLUE}https://github.com/mistakeknot/Demarch/blob/main/docs/guide-full-setup.md${RESET}"
log "  Codex setup:  ${BLUE}https://github.com/mistakeknot/Demarch/blob/main/docs/guide-codex-setup.md${RESET}"
log "  Gemini setup: ${BLUE}https://github.com/mistakeknot/Demarch/blob/main/docs/guide-gemini-setup.md${RESET}"
log "  Contributing: ${BLUE}https://github.com/mistakeknot/Demarch/blob/main/docs/guide-contributing.md${RESET}"
log ""
