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

# The bead id comes from --json, not from a column position. This line read
#
#     bd list --status=open | grep -Fi "cc-changelog:" | head -1 | awk '{print $1}'
#
# until 2026-08-06, and column 1 of `bd list` is the STATUS GLYPH:
#
#     ○ sylveste-j7vl ● P2 cc-changelog: unreviewed Claude Code releases (...)
#
# so "$existing" was literally "○" and every `bd comment` ran against a bead id
# that cannot exist. It shipped working because this branch is only reachable
# once an OPEN cc-changelog bead exists: the runs on 07-21 and 07-28 took the
# create path and succeeded, the run on 08-04 found the bead they had made, and
# from that point the job could never succeed again. It broke by accumulating
# its own success.
#
# Nine days of that were logged as "will retry next run", which was true of the
# control flow and false of the outcome. The only thing that noticed was the
# rig-receipt freshness gate on last-seen, because the state file is
# deliberately not advanced on failure -- that part worked exactly as designed.
#
# --limit 0 is belt and braces against the same shape one layer down. bd's table
# output pages at 50 and --json does not (measured on bd 1.1.2, both machines:
# 474 rows either way), but this bead sits at position 80 of the open list, so
# the day --json inherits that cap the lookup returns empty, the else branch
# reads it as "no open bead", and the job files a duplicate every week -- a
# failure quieter than the one being fixed, because it would still exit 0.
existing="$(bd list --status=open --limit 0 --json 2>/dev/null | python3 -c '
import json, sys
try:
    rows = json.load(sys.stdin)
except Exception:
    sys.exit(0)
for r in rows:
    if "cc-changelog:" in (r.get("title") or ""):
        print(r.get("id", ""))
        break
')"
# bd errors are reported, not swallowed. `>/dev/null 2>&1` on both calls is why
# a wrong bead id and a dead database looked identical for nine days: the log
# said "failed" and nothing said what failed.
if [ -n "$existing" ]; then
    if err="$(bd comment "$existing" "$body" 2>&1 >/dev/null)"; then
        echo "cc-changelog-watch: delta ${last_seen} → ${latest} appended to open bead ${existing}"
    else
        echo "cc-changelog-watch: bd comment on '${existing}' failed, state NOT advanced: ${err:-no output}" >&2
        exit 0
    fi
else
    if err="$(bd create --title="${BEAD_TITLE_PREFIX} (${last_seen} → ${latest})" \
        --description="$body" --type=task --priority=2 2>&1 >/dev/null)"; then
        echo "cc-changelog-watch: delta ${last_seen} → ${latest} filed as new bead"
    else
        echo "cc-changelog-watch: bd create failed, state NOT advanced: ${err:-no output}" >&2
        exit 0
    fi
fi
printf '%s\n' "$latest" > "$STATE_FILE"
exit 0
