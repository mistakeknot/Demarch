#!/usr/bin/env bash
# beads-sync-guard.sh — advisory guard against a STALE local beads Dolt DB.
#
# HAZARD
#   beads stores live state in a Dolt database; the git-tracked export is
#   .beads/issues.jsonl. After a `git pull` that updates issues.jsonl, the
#   local Dolt DB is NOT automatically re-imported, so `bd search` / `bd show`
#   silently return STALE results. (Observed 2026-06-20: Dolt had 1406 issues
#   vs 3489 lines in the JSONL — a ~2000-issue gap; epic sylveste-owjn was
#   invisible to `bd` until `bd import` ran.)
#
# WHAT THIS DOES
#   Compares the live Dolt issue count (`bd --sandbox count`) against the number of
#   *issue* lines in .beads/issues.jsonl (excluding "_type":"memory" records,
#   which `bd count` does not count). If they diverge beyond a tolerance, it
#   prints a one-line advisory pointing the user at `bd import`. It never
#   blocks: every exit path returns 0.
#
# PROPERTIES
#   - cheap   : a `bd --sandbox count` (a single COUNT(*) against a warm Dolt server)
#               plus a `wc -l` and one grep. Sub-second in practice; a
#               hard timeout guarantees it never hangs a SessionStart.
#   - advisory: warns on stderr, always exit 0. Never blocks pull/commit/session.
#   - accurate: count-vs-count with a small tolerance; low false-positive.
#
# EXIT CODE: always 0 (advisory). The signal is the presence/absence of the
#            warning on stderr, not the exit status.
#
# ENV OVERRIDES
#   BEADS_SYNC_GUARD_TOLERANCE   integer drift tolerated before warning (default 0)
#   BEADS_SYNC_GUARD_TIMEOUT     seconds to wait for `bd --sandbox count` (default 3)
#   BEADS_JSONL                  path to issues.jsonl (default .beads/issues.jsonl)
#   PROJECT_DIR                  repo root (default: git toplevel, else $PWD)

set -u

# ─── Locate repo root ──────────────────────────────────────────────────
PROJECT_DIR="${PROJECT_DIR:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}"
cd "$PROJECT_DIR" 2>/dev/null || exit 0

JSONL="${BEADS_JSONL:-$PROJECT_DIR/.beads/issues.jsonl}"
TOLERANCE="${BEADS_SYNC_GUARD_TOLERANCE:-0}"
TIMEOUT_S="${BEADS_SYNC_GUARD_TIMEOUT:-3}"

# ─── Cloud / sandbox: beads are read-only, JSONL is the source of truth ──
# Mirror scripts/lib-cloud-guard.sh detection (env vars only — never `which bd`,
# so a workstation with a broken PATH is not misdiagnosed as cloud).
if [ "${CLAUDE_CODE_REMOTE_ENVIRONMENT_TYPE:-}" = "cloud_default" ] || \
   [ "${IS_SANDBOX:-}" = "yes" ] || \
   [ "${CODEX_SANDBOX_NETWORK_DISABLED:-}" = "1" ]; then
    # No Dolt to compare against; the comparison is meaningless. Stay silent.
    exit 0
fi

# ─── bd present? ───────────────────────────────────────────────────────
if ! command -v bd >/dev/null 2>&1; then
    # Not cloud, but bd is missing. This is a real (but non-fatal) condition;
    # we can't compute the Dolt side. Stay quiet on stderr to avoid SessionStart
    # noise — a missing bd is surfaced by other tooling (PRIME / heal-dolt).
    exit 0
fi

# ─── JSONL present? ────────────────────────────────────────────────────
if [ ! -f "$JSONL" ]; then
    exit 0
fi

# ─── Count JSONL *issue* lines (exclude memory records) ────────────────
# `bd count` counts the Dolt `issues` table; `bd export` writes memories
# (lines with "_type":"memory") into the same JSONL by default. To compare
# like-with-like we subtract memory lines from the raw line count. We also
# subtract any blank lines. Tolerant of optional whitespace after the colon.
# NOTE: `grep -c` prints the count AND exits 1 when the count is 0, so a
# `|| echo 0` fallback would append a second "0" and corrupt the arithmetic.
# We accept grep's printed count unconditionally and sanitize to digits.
count_lines() {  # count_lines <pattern> <file>
    local n
    n=$(grep -c "$1" "$2" 2>/dev/null)
    case "$n" in ''|*[!0-9]*) n=0 ;; esac
    printf '%s' "$n"
}
total_lines=$(count_lines '' "$JSONL")
blank_lines=$(count_lines '^[[:space:]]*$' "$JSONL")
memory_lines=$(count_lines '"_type"[[:space:]]*:[[:space:]]*"memory"' "$JSONL")
jsonl_issues=$(( total_lines - blank_lines - memory_lines ))
[ "$jsonl_issues" -lt 0 ] && jsonl_issues=0

# ─── Count live Dolt issues, with a hard timeout ───────────────────────
# `bd --sandbox count` (no filters) == total issues in the Dolt `issues` table.
# Use `timeout`/`gtimeout` if available; otherwise a portable background+wait
# fallback so a wedged Dolt server can never hang the hook.
run_bd_count() {
    if command -v timeout >/dev/null 2>&1; then
        timeout "$TIMEOUT_S" bd --sandbox count 2>/dev/null
        return $?
    elif command -v gtimeout >/dev/null 2>&1; then
        gtimeout "$TIMEOUT_S" bd --sandbox count 2>/dev/null
        return $?
    fi
    # Portable fallback: run bd in the background, kill it if it overruns.
    local out_file rc
    out_file="$(mktemp 2>/dev/null || echo /tmp/bd_count.$$)"
    ( bd --sandbox count >"$out_file" 2>/dev/null ) &
    local bd_pid=$!
    local waited=0
    while kill -0 "$bd_pid" 2>/dev/null; do
        if [ "$waited" -ge "$TIMEOUT_S" ]; then
            kill "$bd_pid" 2>/dev/null
            wait "$bd_pid" 2>/dev/null
            rm -f "$out_file"
            return 124
        fi
        sleep 1
        waited=$(( waited + 1 ))
    done
    wait "$bd_pid" 2>/dev/null
    rc=$?
    cat "$out_file" 2>/dev/null
    rm -f "$out_file"
    return $rc
}

dolt_raw="$(run_bd_count)"
bd_rc=$?

# If bd count failed, timed out, or returned non-numeric output, we cannot
# compute a trustworthy Dolt side. Stay silent — false silence beats a false
# alarm for an advisory guard (Dolt-down is handled by heal-dolt.sh).
case "$dolt_raw" in
    ''|*[!0-9]*) exit 0 ;;
esac
[ "$bd_rc" -ne 0 ] && exit 0
dolt_issues="$dolt_raw"

# ─── Compare ───────────────────────────────────────────────────────────
drift=$(( jsonl_issues - dolt_issues ))
abs_drift=${drift#-}   # absolute value

if [ "$abs_drift" -gt "$TOLERANCE" ]; then
    if [ "$drift" -gt 0 ]; then
        # JSONL ahead of Dolt → the post-pull staleness case. `bd import` fixes it.
        printf 'beads: STALE local DB — JSONL has %d issues, Dolt has %d (%d not yet imported).\n' \
            "$jsonl_issues" "$dolt_issues" "$drift" >&2
        printf "beads: run 'bd import' to load the pulled issues (bd search/show are stale until you do).\n" >&2
    else
        # Dolt ahead of JSONL → local changes not yet exported. `bd export` / sync fixes it.
        printf 'beads: JSONL behind Dolt — Dolt has %d issues, JSONL has %d (%d unexported).\n' \
            "$dolt_issues" "$jsonl_issues" "$abs_drift" >&2
        printf "beads: run 'bd backup sync' (or 'bd export --output .beads/issues.jsonl') before committing.\n" >&2
    fi
fi

# Always advisory.
exit 0
