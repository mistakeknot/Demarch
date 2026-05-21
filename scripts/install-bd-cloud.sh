#!/usr/bin/env bash
# install-bd-cloud.sh — Manual / opt-in installer for `bd` (beads CLI) and
# `dolt` in a Claude Code remote-environment container.
#
# Cloud_default sessions are read-only on beads by convention (see CLAUDE.md
# "Cloud Sessions") — they grep .beads/issues.jsonl directly and do not run
# the bd CLI. Run this script only when a specific cloud task genuinely
# needs to write to beads (rare: typically the workstation files beads).
#
# Idempotent: skips work if both binaries are already at the expected
# versions. Cost when binaries are absent: ~3s (download + extract).
#
# Usage:
#   bash scripts/install-bd-cloud.sh
#
# Override versions:
#   BD_VERSION=1.0.5 DOLT_VERSION=2.1.0 bash scripts/install-bd-cloud.sh

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
