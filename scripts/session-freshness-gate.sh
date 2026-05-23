#!/usr/bin/env bash
# session-freshness-gate.sh — Skip SessionStart re-orientation when state hasn't changed.
#
# Captures the project's "orientation state" (git HEAD, beads tip SHA, hashes of
# CLAUDE.md / AGENTS.md / MEMORY.md) into .claude/session-state.json. On
# subsequent invocations, compare the live state to the saved state:
#   - If unchanged: exit 0 (caller should skip the orientation work).
#   - If changed:   write the new state, exit 1 (caller should run orientation).
#   - If missing:   write the state, exit 1 (first run; treat as stale).
#
# Wire-up in .claude/settings.json (per-project hook example):
#
#   "SessionStart": [
#     {
#       "matcher": "startup|resume|clear",
#       "hooks": [
#         {
#           "type": "command",
#           "command": "bash $PROJECT_DIR/scripts/session-freshness-gate.sh && exit 0; bash .beads/heal-dolt.sh .beads 2>&1 || true; bd stats 2>/dev/null | head -1"
#         }
#       ]
#     }
#   ]
#
# The `&& exit 0` short-circuits when state is fresh — the LLM gets no
# system-reminder text from this hook and saves the per-fire token cost.
# When state is stale, the original orientation work runs and the new
# state is recorded for the next session.
#
# Per IC-01 (sylveste-a4oj.8): saves 10-16K tok/hr on idle /loop ticks
# where the project state hasn't actually changed between ticks.

set -euo pipefail

PROJECT_DIR="${PROJECT_DIR:-$(pwd)}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# shellcheck source=lib-freshness.sh
source "$SCRIPT_DIR/lib-freshness.sh"

STATE_FILE="$PROJECT_DIR/.claude/session-state.json"

# ─── Capture live orientation state ────────────────────────────────────

cd "$PROJECT_DIR"

# Files whose content materially changes the LLM's orientation. Missing
# files are silently dropped from the manifest.
ORIENTATION_FILES=()
for f in CLAUDE.md AGENTS.md GEMINI.md PHILOSOPHY.md MISSION.md; do
    [[ -f "$PROJECT_DIR/$f" ]] && ORIENTATION_FILES+=("$PROJECT_DIR/$f")
done

# Synthetic state values (not single files):
GIT_SHA=""
if git rev-parse --git-dir >/dev/null 2>&1; then
    GIT_SHA=$(git rev-parse HEAD 2>/dev/null || echo "no-head")
fi

BEADS_SHA=""
if [[ -d "$PROJECT_DIR/.beads" ]]; then
    # Prefer a content-stable signal: most recent jsonl mtime + line count.
    # Don't try to talk to Dolt — it may be down, and we want this fast.
    if [[ -f "$PROJECT_DIR/.beads/issues.jsonl" ]]; then
        BEADS_SHA=$(sha256sum "$PROJECT_DIR/.beads/issues.jsonl" 2>/dev/null | cut -d' ' -f1)
    fi
fi

# User-memory state (if present — stored in ~/.claude/projects/<slug>/memory/MEMORY.md)
MEMORY_PATH=""
PROJECT_SLUG=$(echo "$PROJECT_DIR" | sed 's|/|-|g')   # e.g. -home-mk-projects-Sylveste
CANDIDATE="$HOME/.claude/projects/$PROJECT_SLUG/memory/MEMORY.md"
if [[ -f "$CANDIDATE" ]]; then
    MEMORY_PATH="$CANDIDATE"
fi

# Container/host runtime epoch — the freshness manifest is otherwise blind to
# runtime state (Dolt liveness, ephemeral container resets). boot_id flips on
# every new cloud container, forcing a stale-classify on the first session
# of a new container regardless of content hashes. Cheap, decisive, closes
# the biggest observability gap in the estimator (PR #19 follow-up review,
# control-theoretic + mission-command convergence).
BOOT_ID=""
if [[ -r /proc/sys/kernel/random/boot_id ]]; then
    BOOT_ID=$(cat /proc/sys/kernel/random/boot_id 2>/dev/null || true)
fi

# Compose the manifest: orientation files + synthetic keys.
current=$(freshness_compute_manifest_paths "${ORIENTATION_FILES[@]}" ${MEMORY_PATH:+"$MEMORY_PATH"})
[[ -n "$GIT_SHA" ]]   && current=$(echo "$current" | freshness_add_key git_sha   "$GIT_SHA")
[[ -n "$BEADS_SHA" ]] && current=$(echo "$current" | freshness_add_key beads_sha "$BEADS_SHA")
[[ -n "$BOOT_ID" ]]   && current=$(echo "$current" | freshness_add_key boot_id   "$BOOT_ID")

# ─── Compare to saved ──────────────────────────────────────────────────

if echo "$current" | freshness_compare "$STATE_FILE" "session" 2>/dev/null; then
    # Fresh: no orientation changes since last session start.
    exit 0
fi

# Stale or missing: persist the new state and signal the caller to proceed.
mkdir -p "$(dirname "$STATE_FILE")"
echo "$current" > "$STATE_FILE"
exit 1
