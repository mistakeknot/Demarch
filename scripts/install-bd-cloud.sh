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
# Linux-only. Refuses to install on darwin/freebsd/windows because the URL
# template is hard-coded for linux releases and a downloaded ELF would
# silently fail at exec time.
#
# Security: SHA256 verified after download. The bd archive is checked against
# the upstream publisher's checksums.txt (one fetch per install). The dolt
# archive is checked against a constant pinned in this file (dolt's upstream
# does not publish a signed checksums file). Override via *_SHA256_* env
# vars; mismatch fails closed.
#
# Usage:
#   bash scripts/install-bd-cloud.sh
#
# Override versions or checksums:
#   BD_VERSION=1.0.5 DOLT_VERSION=2.1.0 \
#   DOLT_SHA256_AMD64=<expected-hex> \
#   bash scripts/install-bd-cloud.sh

set -euo pipefail

BD_VERSION="${BD_VERSION:-1.0.4}"
DOLT_VERSION="${DOLT_VERSION:-2.0.4}"
INSTALL_DIR="${INSTALL_DIR:-$HOME/.local/bin}"

# Pinned checksums for the default versions. If you bump *_VERSION above,
# either update these or pass *_SHA256_* via env. Mismatch is fail-closed.
PINNED_DOLT_SHA256_AMD64_v2_0_4="d5a1924b164c6f25d30b9134f914669913397d706c0ccad1b17623343426728c"

log() { echo "install-bd-cloud: $*" >&2; }
die() { log "ERROR: $*"; exit 1; }

[[ "$(uname -s)" == "Linux" ]] || die "Linux-only installer (uname=$(uname -s)); refusing"

want_arch() {
    case "$(uname -m)" in
        x86_64|amd64) echo amd64 ;;
        aarch64|arm64) echo arm64 ;;
        *) die "unsupported arch: $(uname -m)" ;;
    esac
}

ARCH=$(want_arch)
mkdir -p "$INSTALL_DIR"

verify_sha256() {
    local file="$1" expected="$2"
    local actual
    actual=$(sha256sum "$file" 2>/dev/null | awk '{print $1}')
    [[ "$actual" == "$expected" ]] || die "sha256 mismatch on $file (expected=$expected actual=$actual)"
}

install_bd() {
    if command -v bd >/dev/null 2>&1; then
        local have
        have=$(bd --version 2>/dev/null | awk '{print $3}' || echo "")
        if [[ "$have" == "$BD_VERSION" ]]; then
            log "bd $BD_VERSION already installed"
            return 0
        fi
    fi
    local base="https://github.com/gastownhall/beads/releases/download/v${BD_VERSION}"
    local asset="beads_${BD_VERSION}_linux_${ARCH}.tar.gz"
    local tmp
    tmp=$(mktemp -d)
    trap 'rm -rf "$tmp"' RETURN

    log "downloading bd $BD_VERSION ($base/$asset)"
    curl -fsSL --max-time 60 -o "$tmp/$asset" "$base/$asset" \
        || die "bd download failed"

    # Verify against the upstream-published checksums.txt unless overridden.
    local expected="${BD_SHA256:-}"
    if [[ -z "$expected" ]]; then
        log "fetching upstream checksums.txt for verification"
        curl -fsSL --max-time 30 -o "$tmp/checksums.txt" "$base/checksums.txt" \
            || die "checksums.txt download failed (network or upstream removed it)"
        expected=$(awk -v a="$asset" '$2==a {print $1}' "$tmp/checksums.txt")
        [[ -n "$expected" ]] || die "asset $asset not found in upstream checksums.txt"
    fi
    verify_sha256 "$tmp/$asset" "$expected"

    tar -xzf "$tmp/$asset" -C "$tmp"
    install -m 0755 "$tmp/bd" "$INSTALL_DIR/bd"
    log "installed bd → $INSTALL_DIR/bd (sha256 ok)"
}

install_dolt() {
    if command -v dolt >/dev/null 2>&1; then
        log "dolt already installed at $(command -v dolt)"
        return 0
    fi
    local base="https://github.com/dolthub/dolt/releases/download/v${DOLT_VERSION}"
    local asset="dolt-linux-${ARCH}.tar.gz"
    local tmp
    tmp=$(mktemp -d)
    trap 'rm -rf "$tmp"' RETURN

    log "downloading dolt $DOLT_VERSION ($base/$asset)"
    curl -fsSL --max-time 60 -o "$tmp/$asset" "$base/$asset" \
        || die "dolt download failed"

    # Dolt upstream does not publish a checksums file. Verify against the
    # constant pinned in this file (or env override).
    local expected=""
    case "$ARCH" in
        amd64)
            if [[ "$DOLT_VERSION" == "2.0.4" ]]; then
                expected="${DOLT_SHA256_AMD64:-$PINNED_DOLT_SHA256_AMD64_v2_0_4}"
            else
                expected="${DOLT_SHA256_AMD64:-}"
            fi
            ;;
        arm64)
            expected="${DOLT_SHA256_ARM64:-}"
            ;;
    esac
    [[ -n "$expected" ]] || die "no pinned sha256 for dolt $DOLT_VERSION/$ARCH; set DOLT_SHA256_${ARCH^^}"
    verify_sha256 "$tmp/$asset" "$expected"

    tar -xzf "$tmp/$asset" -C "$tmp"
    install -m 0755 "$tmp/dolt-linux-${ARCH}/bin/dolt" "$INSTALL_DIR/dolt"
    log "installed dolt → $INSTALL_DIR/dolt (sha256 ok)"
}

install_bd
install_dolt

# Surface PATH state so the caller knows whether `bd` is actually invocable.
if ! command -v bd >/dev/null 2>&1; then
    log "WARN: $INSTALL_DIR is not on PATH — add: export PATH=\"$INSTALL_DIR:\$PATH\""
fi
