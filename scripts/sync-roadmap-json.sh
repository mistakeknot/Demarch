#!/usr/bin/env bash
# sync-roadmap-json.sh — generate docs/roadmap.json and docs/backlog.md.
#
# THIS IS A SHIM. The generator lives in interpath.
#
# Two copies of this script existed for four months and diverged. Remontoire's
# README already assigned ownership — "Beads owns backlog truth [...] Interpath
# owns generated roadmap artifacts" — but the monorepo kept its own fork, so
# which output you got depended on which script had run:
#
#   /interpath:roadmap  ->  plugin copy   (2026-03-08)
#   the LaunchAgent     ->  this copy     (2026-07-10)
#
# The plugin copy counted all 18 deferred beads as open work (481 -> 499),
# hardcoded blocked_by to [] and so dropped 127 dependency edges, emitted a
# timestamp that is malformed on macOS (%:z is GNU-only), and produced no
# backlog.md at all. Those fixes now live in interpath and this file delegates,
# so there is one generator and one place to fix it.
#
# INTERFACE PRESERVED: $1 = roadmap json path, $2 = backlog markdown path,
# both defaulting under docs/. The com.arouth.sylveste-roadmap LaunchAgent
# calls this path with explicit arguments and needs no change.

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ROOT_DOCS_DIR="$ROOT_DIR/docs"
OUTPUT="${1:-$ROOT_DOCS_DIR/roadmap.json}"
BACKLOG_OUTPUT="${2:-$ROOT_DOCS_DIR/backlog.md}"

GENERATOR="$ROOT_DIR/interverse/interpath/scripts/sync-roadmap-json.sh"

if [[ ! -x "$GENERATOR" && ! -r "$GENERATOR" ]]; then
    echo "sync-roadmap-json: generator not found at $GENERATOR" >&2
    echo "  interpath is a nested checkout; run 'git submodule update' or clone it." >&2
    exit 1
fi

# Pinned, not inferred. interpath falls back to the lowercased basename of the
# project root, which yields "sylveste" here only because the directory happens
# to be named Sylveste. The script this replaces hardcoded the value, and a
# renamed checkout or a worktree under another name would otherwise silently
# change `project`, `kind`, and the backlog heading.
export ROADMAP_PROJECT="${ROADMAP_PROJECT:-sylveste}"

# Run from the monorepo root: interpath resolves its project root with
# `git rev-parse --show-toplevel`, which reads the CURRENT DIRECTORY, not the
# script location. Invoked from inside interverse/interpath that would resolve
# to the interpath checkout and scan the wrong tree.
cd "$ROOT_DIR"

exec bash "$GENERATOR" "$OUTPUT" "$BACKLOG_OUTPUT"
