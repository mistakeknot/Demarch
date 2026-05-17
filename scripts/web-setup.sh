#!/usr/bin/env bash
# web-setup.sh -- Setup script for Claude Code on the web.
#
# Paste `bash scripts/web-setup.sh` into the environment's "Setup script" field.
# Runs once during container init, before Claude Code launches.
#
# Installs the binaries the repo's SessionStart hook expects:
#   - bd        (Beads CLI)             -- required by .beads/heal-dolt.sh
#   - dolt      (DoltHub SQL server)    -- managed by `bd dolt`
# Ensures $HOME/go/bin and $HOME/.local/bin are on PATH for subsequent shells,
# then delegates the rest of the project bring-up to install.sh (builds ic,
# clones intercore from GitHub, installs Claude/Codex/Gemini bits if their
# CLIs are present).
#
# Safe to re-run; each step is idempotent.

set -euo pipefail

log()  { printf '[web-setup] %s\n' "$*"; }
warn() { printf '[web-setup] WARN: %s\n' "$*" >&2; }

# --- PATH bootstrap ---------------------------------------------------------
# Setup runs before Claude Code launches; later shells inherit PATH from the
# container's profile, so we persist additions to ~/.bashrc as well as the
# current process.
mkdir -p "${HOME}/.local/bin"

ensure_path_line() {
    local line="$1"
    local rc="${HOME}/.bashrc"
    touch "$rc"
    grep -qxF "$line" "$rc" || printf '%s\n' "$line" >> "$rc"
}

ensure_path_line 'export PATH="$HOME/.local/bin:$HOME/go/bin:$PATH"'
export PATH="$HOME/.local/bin:$HOME/go/bin:$PATH"

# --- Beads CLI (bd) ---------------------------------------------------------
if command -v bd >/dev/null 2>&1; then
    log "bd already installed at $(command -v bd)"
else
    log "Installing bd (Beads CLI) via go install..."
    # Canonical module path per docs/guide-full-setup.md
    go install github.com/mistakeknot/beads/cmd/bd@latest
    log "bd installed: $(command -v bd || echo MISSING)"
fi

# --- Dolt -------------------------------------------------------------------
if command -v dolt >/dev/null 2>&1; then
    log "dolt already installed at $(command -v dolt)"
else
    log "Installing dolt..."
    # Official installer drops the binary into /usr/local/bin (needs no sudo
    # in this container; falls back gracefully if it does).
    if curl -fsSL https://github.com/dolthub/dolt/releases/latest/download/install.sh | bash; then
        log "dolt installed: $(command -v dolt || echo MISSING)"
    else
        warn "dolt installer failed; heal-dolt hook will fall back to JSONL"
    fi
fi

# --- Project install --------------------------------------------------------
# install.sh handles: ic build (clones intercore if not present), bd init,
# Claude/Codex/Gemini skill setup when those CLIs exist. In a fresh web
# container, only the ic build will actually do work; the rest will warn-skip.
if [[ -x ./install.sh ]] || [[ -f ./install.sh ]]; then
    log "Running ./install.sh ..."
    if bash ./install.sh; then
        log "install.sh completed"
    else
        warn "install.sh exited non-zero; check output above"
    fi
else
    warn "install.sh not found in $(pwd); skipping project install"
fi

log "done. PATH for next shell: $HOME/.local/bin:$HOME/go/bin:..."
