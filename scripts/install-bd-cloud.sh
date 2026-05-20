#!/usr/bin/env bash
# install-bd-cloud.sh — Install `bd` (beads CLI) and `dolt` into a cloud
# Claude Code remote-environment container.
#
# Containers are ephemeral, so this runs once per container creation. Called
# from .beads/heal-dolt.sh when `bd` is missing from PATH. Idempotent: skips
# work if both binaries are already in place at the expected versions.
#
# Wire into a managed environment's setup hook to avoid the on-demand path:
#   bash scripts/install-bd-cloud.sh
# Per-session cost when binaries are absent: ~3s (download + extract).

set -euo pipefail

BD_VERSION="${BD_VERSION:-1.0.4}"
DOLT_VERSION="${DOLT_VERSION:-2.0.4}"
INSTALL_DIR="${INSTALL_DIR:-/root/.local/bin}"

log() { echo "install-bd-cloud: $*" >&2; }

want_arch() {
    case "$(uname -m)" in
        x86_64|amd64) echo amd64 ;;
        aarch64|arm64) echo arm64 ;;
        *) log "unsupported arch: $(uname -m)"; exit 1 ;;
    esac
}

ARCH=$(want_arch)
mkdir -p "$INSTALL_DIR"

install_bd() {
    if command -v bd >/dev/null 2>&1; then
        local have
        have=$(bd --version 2>/dev/null | awk '{print $3}' || echo "")
        if [[ "$have" == "$BD_VERSION" ]]; then
            log "bd $BD_VERSION already installed"
            return 0
        fi
    fi
    local url="https://github.com/gastownhall/beads/releases/download/v${BD_VERSION}/beads_${BD_VERSION}_linux_${ARCH}.tar.gz"
    local tmp
    tmp=$(mktemp -d)
    log "downloading bd $BD_VERSION ($url)"
    if ! curl -fsSL --max-time 30 -o "$tmp/bd.tar.gz" "$url"; then
        log "bd download failed"; rm -rf "$tmp"; return 1
    fi
    tar -xzf "$tmp/bd.tar.gz" -C "$tmp"
    install -m 0755 "$tmp/bd" "$INSTALL_DIR/bd"
    rm -rf "$tmp"
    log "installed bd → $INSTALL_DIR/bd"
}

install_dolt() {
    if command -v dolt >/dev/null 2>&1; then
        log "dolt already installed at $(command -v dolt)"
        return 0
    fi
    local url="https://github.com/dolthub/dolt/releases/download/v${DOLT_VERSION}/dolt-linux-${ARCH}.tar.gz"
    local tmp
    tmp=$(mktemp -d)
    log "downloading dolt $DOLT_VERSION ($url)"
    if ! curl -fsSL --max-time 30 -o "$tmp/dolt.tar.gz" "$url"; then
        log "dolt download failed"; rm -rf "$tmp"; return 1
    fi
    tar -xzf "$tmp/dolt.tar.gz" -C "$tmp"
    install -m 0755 "$tmp/dolt-linux-${ARCH}/bin/dolt" "$INSTALL_DIR/dolt"
    rm -rf "$tmp"
    log "installed dolt → $INSTALL_DIR/dolt"
}

install_bd
install_dolt
