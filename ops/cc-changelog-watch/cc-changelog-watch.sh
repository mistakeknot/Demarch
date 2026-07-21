#!/usr/bin/env bash
# Weekly Claude Code changelog watcher (bead Sylveste-b15, goal 7b585d72).
# Estate-drift pattern: fetch CHANGELOG.md, diff the latest version against
# last-seen state, and keep at most ONE open "cc-changelog:" bead in the
# Sylveste beads db carrying the unreviewed delta. The capability→plugin
# mapping deliberately happens in-session, not here (zero unattended LLM
# cost) — see docs/goals/2026-07-21-cc-changelog-watcher-charter.md.
# Fail-open: network/parse trouble logs and exits 0.
set -u
[ -f "$HOME/.claude-automations-paused" ] && exit 0
export PATH="$HOME/.local/bin:$HOME/bin:$PATH"

STATE_DIR="${XDG_STATE_HOME:-$HOME/.local/state}/cc-changelog-watch"
STATE_FILE="$STATE_DIR/last-seen"
CHANGELOG_URL="https://raw.githubusercontent.com/anthropics/claude-code/main/CHANGELOG.md"
BEAD_REPO="$HOME/projects/Sylveste"
BEAD_TITLE_PREFIX="cc-changelog: unreviewed Claude Code releases"

mkdir -p "$STATE_DIR"

changelog="$(curl -sf --connect-timeout 10 --max-time 30 "$CHANGELOG_URL")" || {
    echo "cc-changelog-watch: fetch failed (offline?), skipping" >&2
    exit 0
}

latest="$(printf '%s\n' "$changelog" | sed -n 's/^## \([0-9][0-9.]*\).*/\1/p' | head -1)"
if [ -z "$latest" ]; then
    echo "cc-changelog-watch: could not parse a '## <version>' heading — format drift?" >&2
    exit 0
fi

last_seen=""
[ -f "$STATE_FILE" ] && last_seen="$(cat "$STATE_FILE")"

if [ -z "$last_seen" ]; then
    printf '%s\n' "$latest" > "$STATE_FILE"
    echo "cc-changelog-watch: baseline recorded at $latest (no bead filed)"
    exit 0
fi

if [ "$latest" = "$last_seen" ]; then
    echo "cc-changelog-watch: no delta (still $latest)"
    exit 0
fi

# Delta = changelog body from the newest "## " heading down to (excluding)
# the last-seen version's heading. Cap size so bead descriptions stay sane.
delta="$(printf '%s\n' "$changelog" | awk -v last="## $last_seen" '
    $0 == last {exit}
    /^## /{on=1}
    on {print}
')"
delta_trimmed="$(printf '%s\n' "$delta" | head -200)"

cd "$BEAD_REPO" || exit 0
body="Delta ${last_seen} → ${latest}, fetched $(date -u +%F) by cc-changelog-watch.timer on zklw.

${delta_trimmed}

Next: in-session mapping pass — map new capabilities to Sylveste plugins, file candidate beads, refresh the digest and AgMoDB's claude-code entry (charter: docs/goals/2026-07-21-cc-changelog-watcher-charter.md)."

existing="$(bd list --status=open 2>/dev/null | grep -Fi "cc-changelog:" | head -1 | awk '{print $1}')"
if [ -n "$existing" ]; then
    if bd comment "$existing" -m "$body" >/dev/null 2>&1; then
        echo "cc-changelog-watch: delta ${last_seen} → ${latest} appended to open bead ${existing}"
    else
        echo "cc-changelog-watch: bd comment failed; state NOT advanced (will retry next run)" >&2
        exit 0
    fi
else
    if bd create --title="${BEAD_TITLE_PREFIX} (${last_seen} → ${latest})" \
        --description="$body" --type=task --priority=2 >/dev/null 2>&1; then
        echo "cc-changelog-watch: delta ${last_seen} → ${latest} filed as new bead"
    else
        echo "cc-changelog-watch: bd create failed; state NOT advanced (will retry next run)" >&2
        exit 0
    fi
fi
printf '%s\n' "$latest" > "$STATE_FILE"
exit 0
