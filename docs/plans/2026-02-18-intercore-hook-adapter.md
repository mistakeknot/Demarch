# Intercore Hook Adapter Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use clavain:executing-plans to implement this plan task-by-task.

**Bead:** iv-wo1t
**Phase:** executing (as of 2026-02-18T06:43:02Z)
**Reviews:** fd-correctness (3 P0, 2 P1), fd-architecture (1 P0, 1 P1, 1 P2, 1 P3, 3 S), fd-quality (4 P1)

**Goal:** Replace all `/tmp/clavain-*` temp file sentinels in Clavain hooks with atomic intercore DB calls via `lib-intercore.sh`.

**Architecture:** Each hook currently uses `touch`/`-f`/`stat` on temp files for throttle guards and once-per-session sentinels. These get replaced with `intercore_sentinel_check` (for sentinel/throttle patterns) and `intercore_state_set`/`intercore_state_get` (for cached data). All wrappers are in `infra/intercore/lib-intercore.sh` which fails safe when `ic` is unavailable — no behavioral change for users without intercore installed.

**Tech Stack:** Bash (hooks), Go (intercore `ic` CLI), SQLite (intercore DB)

**Key files:**
- `infra/intercore/lib-intercore.sh` — bash wrapper library (extend with new helpers)
- `hub/clavain/hooks/catalog-reminder.sh` — simplest hook (1 sentinel)
- `hub/clavain/hooks/session-handoff.sh` — 2 sentinels (stop + handoff)
- `hub/clavain/hooks/auto-compound.sh` — stop sentinel + time-based throttle
- `hub/clavain/hooks/auto-drift-check.sh` — stop sentinel + time-based throttle
- `hub/clavain/hooks/auto-publish.sh` — global sentinel with 60s TTL
- `hub/clavain/hooks/lib-sprint.sh` — discovery cache invalidation

---

## Mapping Reference

| Temp File Pattern | intercore Key | intercore Call | Interval |
|-------------------|---------------|----------------|----------|
| `/tmp/clavain-stop-$SID` | `stop` | `sentinel check stop $SID --interval=0` | once-per-session |
| `/tmp/clavain-handoff-$SID` | `handoff` | `sentinel check handoff $SID --interval=0` | once-per-session |
| `/tmp/clavain-compound-last-$SID` | `compound_throttle` | `sentinel check compound_throttle $SID --interval=300` | 5 min |
| `/tmp/clavain-drift-last-$SID` | `drift_throttle` | `sentinel check drift_throttle $SID --interval=600` | 10 min |
| `/tmp/clavain-autopub.lock` | `autopub` | `sentinel check autopub global --interval=60` | 60s |
| `/tmp/clavain-catalog-remind-$SID.lock` | `catalog_remind` | `sentinel check catalog_remind $SID --interval=0` | once-per-session |
| `/tmp/clavain-discovery-brief-*.cache` | `discovery_brief` | `state delete discovery_brief $scope` | cache invalidation |

Sentinel names are internal to Clavain hooks and isolated by scope_id (usually session ID).
No namespace collisions with user-facing keys because hooks use session scope.

---

## Review Fixes Applied

The following P0/P1 findings from the flux-drive review have been incorporated:

1. **P0-1 (correctness):** Removed `2>&1` from wrapper — stderr must propagate so DB errors are visible. Exit code 2 now falls through to legacy path instead of being treated as "throttled".
2. **P0-2 (correctness):** Added documentation note about fallback TOCTOU being intentional (legacy-compatible).
3. **P0-3 (correctness):** Wrapper now handles exit code 2 (error) explicitly, falling through to legacy instead of via `|| exit 0`.
4. **P0-arch (architecture):** Added version header to lib-intercore.sh and sync check in integration tests.
5. **P1-qual (quality):** Moved `intercore_sentinel_reset_all` and `intercore_state_delete_all` to Task 1 so all wrappers are defined before the copy in Task 2.
6. **P1-qual (quality):** Added legacy fallback tests (with `INTERCORE_BIN=""`).
7. **P1-arch (architecture):** Added `intercore_check_or_die` convenience helper to reduce per-hook boilerplate.
8. **P2-arch (architecture):** Added TOCTOU safety comment for stop sentinel blocks.
9. **S1-arch (architecture):** Changed discovery cache invalidation from sentinel to state (correct abstraction).
10. **S3-arch (architecture):** Moved cleanup to session-handoff.sh only (one hook per stop cycle).

---

### Task 1: Extend lib-intercore.sh with sentinel_check_or_legacy

**Files:**
- Modify: `infra/intercore/lib-intercore.sh`
- Test: `infra/intercore/test-integration.sh` (extend)

This task adds a `intercore_sentinel_check_or_legacy` function that tries intercore first, falls back to temp-file check. This enables incremental migration — hooks can switch to the new function immediately while keeping backward compat for systems without `ic`.

**Step 1: Write the new wrapper functions in lib-intercore.sh**

Add these functions after the existing `intercore_sentinel_check`:

```bash
# lib-intercore.sh — Bash wrappers for intercore CLI
# Version: 0.1.0 (source: infra/intercore/lib-intercore.sh)
# Re-copy to hub/clavain/hooks/ on major intercore updates; version is pinned to plugin release.
INTERCORE_WRAPPER_VERSION="0.1.0"

# Shared sentinel for Stop hook anti-cascade protocol.
# All Stop hooks MUST check this sentinel before doing work to prevent
# multiple Stop hooks from firing in the same stop cycle.
INTERCORE_STOP_DEDUP_SENTINEL="stop"

# intercore_sentinel_check_or_legacy — try ic sentinel, fall back to temp file.
# Args: $1=name, $2=scope_id, $3=interval_sec, $4=legacy_file (temp file path)
# Returns: 0 if allowed (proceed), 1 if throttled (skip)
# Side effect: touches legacy file as fallback when ic unavailable or erroring
intercore_sentinel_check_or_legacy() {
    local name="$1" scope_id="$2" interval="$3" legacy_file="$4"
    if intercore_available; then
        # Suppress stdout (allowed/throttled message), preserve stderr (errors)
        # Exit 0 = allowed, 1 = throttled, 2+ = error → fall through to legacy
        local rc=0
        "$INTERCORE_BIN" sentinel check "$name" "$scope_id" --interval="$interval" >/dev/null || rc=$?
        if [[ $rc -eq 0 ]]; then
            return 0  # allowed
        elif [[ $rc -eq 1 ]]; then
            return 1  # throttled
        fi
        # Exit code 2+ = DB error — fall through to legacy path
        # (error message already written to stderr by ic)
    fi
    # Fallback: temp file check (known TOCTOU race — see Note on Fallback TOCTOU below)
    if [[ -f "$legacy_file" ]]; then
        if [[ "$interval" -eq 0 ]]; then
            return 1  # once-per-session: file exists = throttled
        fi
        local file_mtime now
        file_mtime=$(stat -c %Y "$legacy_file" 2>/dev/null || stat -f %m "$legacy_file" 2>/dev/null || echo 0)
        now=$(date +%s)
        if [[ $((now - file_mtime)) -lt "$interval" ]]; then
            return 1  # within throttle window
        fi
    fi
    touch "$legacy_file"
    return 0
}

# intercore_check_or_die — Convenience wrapper: check sentinel, exit 0 if throttled.
# Args: $1=name, $2=scope_id, $3=interval, $4=legacy_path
# Returns: 0 if allowed. Exits the calling script (exit 0) if throttled.
# This eliminates the per-hook boilerplate of type-check + inline fallback.
intercore_check_or_die() {
    local name="$1" scope_id="$2" interval="$3" legacy_path="$4"
    if type intercore_sentinel_check_or_legacy &>/dev/null; then
        intercore_sentinel_check_or_legacy "$name" "$scope_id" "$interval" "$legacy_path" || exit 0
        return 0
    fi
    # Inline fallback (wrapper unavailable — lib-intercore.sh failed to source)
    if [[ -f "$legacy_path" ]]; then
        if [[ "$interval" -eq 0 ]]; then
            exit 0  # once-per-session: file exists = throttled
        fi
        local file_mtime now
        file_mtime=$(stat -c %Y "$legacy_path" 2>/dev/null || stat -f %m "$legacy_path" 2>/dev/null || echo 0)
        now=$(date +%s)
        if [[ $((now - file_mtime)) -lt "$interval" ]]; then
            exit 0  # within throttle window
        fi
    fi
    touch "$legacy_path"
    return 0
}

# intercore_sentinel_reset_or_legacy — try ic sentinel reset, fall back to rm.
# Args: $1=name, $2=scope_id, $3=legacy_glob (temp file glob pattern)
intercore_sentinel_reset_or_legacy() {
    local name="$1" scope_id="$2" legacy_glob="$3"
    if intercore_available; then
        "$INTERCORE_BIN" sentinel reset "$name" "$scope_id" >/dev/null 2>&1 || true
        return 0
    fi
    # Fallback: rm legacy files
    # shellcheck disable=SC2086
    rm -f $legacy_glob 2>/dev/null || true
}

# intercore_sentinel_reset_all — reset all scopes for a given sentinel name.
# Args: $1=name, $2=legacy_glob (temp file glob pattern for fallback)
# NOTE: Has list-then-reset TOCTOU — acceptable for cache invalidation,
# NOT for mutual-exclusion sentinels. Use ic sentinel reset-all when added.
intercore_sentinel_reset_all() {
    local name="$1" legacy_glob="$2"
    if intercore_available; then
        local scope
        while IFS=$'\t' read -r _name scope _fired; do
            [[ "$_name" == "$name" ]] || continue
            "$INTERCORE_BIN" sentinel reset "$name" "$scope" >/dev/null 2>&1 || true
        done < <("$INTERCORE_BIN" sentinel list 2>/dev/null || true)
        return 0
    fi
    # Fallback: rm legacy files
    # shellcheck disable=SC2086
    rm -f $legacy_glob 2>/dev/null || true
}

# intercore_state_delete_all — delete all scopes for a given state key.
# Args: $1=key, $2=legacy_glob (temp file glob pattern for fallback)
# Use for cache invalidation (not throttle sentinels).
intercore_state_delete_all() {
    local key="$1" legacy_glob="$2"
    if intercore_available; then
        local scope
        while read -r scope; do
            "$INTERCORE_BIN" state delete "$key" "$scope" 2>/dev/null || true
        done < <("$INTERCORE_BIN" state list "$key" 2>/dev/null || true)
        return 0
    fi
    # Fallback: rm legacy files
    # shellcheck disable=SC2086
    rm -f $legacy_glob 2>/dev/null || true
}

# intercore_cleanup_stale — prune old sentinels (replaces find -mmin -delete).
# Called ONCE per stop cycle from session-handoff.sh only — not from every hook.
intercore_cleanup_stale() {
    if intercore_available; then
        "$INTERCORE_BIN" sentinel prune --older-than=1h >/dev/null 2>&1 || true
        return 0
    fi
    # Fallback: clean legacy temp files
    find /tmp -maxdepth 1 \( -name 'clavain-stop-*' -o -name 'clavain-drift-last-*' -o -name 'clavain-compound-last-*' \) -mmin +60 -delete 2>/dev/null || true
}
```

**Step 2: Verify lib-intercore.sh syntax**

Run: `bash -n infra/intercore/lib-intercore.sh`
Expected: no output (clean parse)

**Step 3: Add integration test for the new wrapper**

Add to `infra/intercore/test-integration.sh` before the "All integration tests passed" line:

```bash
echo "=== lib-intercore.sh Wrapper ==="
# Source the library and test the wrapper with a real ic binary
export INTERCORE_BIN="$IC_BIN"
source "$SCRIPT_DIR/lib-intercore.sh"
INTERCORE_BIN="$IC_BIN"  # force available

# Test sentinel_check_or_legacy with ic available
intercore_sentinel_check_or_legacy "wrapper_test" "test-session" 0 "/tmp/clavain-wrapper-test" && pass "wrapper: first check allowed" || fail "wrapper: first check should be allowed"
intercore_sentinel_check_or_legacy "wrapper_test" "test-session" 0 "/tmp/clavain-wrapper-test" && fail "wrapper: second check should be throttled" || pass "wrapper: second check throttled"

# Test reset
intercore_sentinel_reset_or_legacy "wrapper_test" "test-session" "/tmp/clavain-wrapper-test"
pass "wrapper: reset"

# Verify sentinel was reset (next check should be allowed)
intercore_sentinel_check_or_legacy "wrapper_test" "test-session" 0 "/tmp/clavain-wrapper-test" && pass "wrapper: check after reset allowed" || fail "wrapper: check after reset should be allowed"

# Test cleanup
intercore_cleanup_stale
pass "wrapper: cleanup"

echo "=== Legacy Fallback Path ==="
# Test with ic unavailable (forces legacy temp-file path)
INTERCORE_BIN_SAVED="$INTERCORE_BIN"
INTERCORE_BIN=""
rm -f /tmp/clavain-legacy-test

intercore_sentinel_check_or_legacy "legacy_test" "test-session" 0 "/tmp/clavain-legacy-test" && pass "legacy: first check allowed" || fail "legacy: first check should be allowed"
[[ -f "/tmp/clavain-legacy-test" ]] && pass "legacy: sentinel file created" || fail "legacy: sentinel file missing"
intercore_sentinel_check_or_legacy "legacy_test" "test-session" 0 "/tmp/clavain-legacy-test" && fail "legacy: second check should be throttled" || pass "legacy: second check throttled"

rm -f /tmp/clavain-legacy-test
INTERCORE_BIN="$INTERCORE_BIN_SAVED"  # restore

echo "=== Version Sync Check ==="
# Verify Clavain's copy is in sync (if present in monorepo)
CLAVAIN_LIB="$SCRIPT_DIR/../../hub/clavain/hooks/lib-intercore.sh"
if [[ -f "$CLAVAIN_LIB" ]]; then
    CLAVAIN_VER=$(grep '^INTERCORE_WRAPPER_VERSION=' "$CLAVAIN_LIB" | cut -d'"' -f2)
    SOURCE_VER=$(grep '^INTERCORE_WRAPPER_VERSION=' "$SCRIPT_DIR/lib-intercore.sh" | cut -d'"' -f2)
    if [[ "$CLAVAIN_VER" = "$SOURCE_VER" ]]; then
        pass "version sync: source=$SOURCE_VER clavain=$CLAVAIN_VER"
    else
        fail "version sync: source=$SOURCE_VER != clavain=$CLAVAIN_VER (re-copy lib-intercore.sh)"
    fi
fi
```

**Step 4: Run integration tests**

Run: `cd infra/intercore && bash test-integration.sh`
Expected: All tests pass including new wrapper tests

**Step 5: Commit**

```bash
git add infra/intercore/lib-intercore.sh infra/intercore/test-integration.sh
git commit -m "feat(intercore): add sentinel_check_or_legacy wrappers for hook migration"
```

---

### Task 2: Migrate catalog-reminder.sh (simplest hook — 1 sentinel)

**Files:**
- Modify: `hub/clavain/hooks/catalog-reminder.sh`

This is the simplest hook: one once-per-session sentinel, no throttle timing. Perfect validation that the pattern works.

**Step 1: Source lib-intercore.sh in catalog-reminder.sh**

Add after the existing `set -euo pipefail` line:

```bash
# Source intercore wrappers (fail-safe: falls back to temp files)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/../../infra/intercore/lib-intercore.sh" 2>/dev/null || true
```

Note: The path traversal from `hub/clavain/hooks/` to `infra/intercore/` requires `../../infra/intercore/`. But since this hook runs from the plugin cache directory at runtime (not the monorepo), we need to detect the monorepo root dynamically. Use an alternative approach:

```bash
# Source intercore wrappers — resolve monorepo root from git
_IC_LIB=""
if command -v git &>/dev/null; then
    _IC_ROOT="$(git rev-parse --show-toplevel 2>/dev/null)"
    [[ -n "$_IC_ROOT" && -f "$_IC_ROOT/infra/intercore/lib-intercore.sh" ]] && _IC_LIB="$_IC_ROOT/infra/intercore/lib-intercore.sh"
fi
# Fallback: check if ic is on PATH (lib-intercore.sh may be installed separately)
if [[ -z "$_IC_LIB" ]]; then
    _IC_LIB="$(dirname "$(command -v ic 2>/dev/null)")/../lib-intercore.sh" 2>/dev/null || true
    [[ -f "$_IC_LIB" ]] || _IC_LIB=""
fi
[[ -n "$_IC_LIB" ]] && source "$_IC_LIB" 2>/dev/null || true
```

Actually, this is over-engineered. The hooks run inside the Clavain plugin, and the intercore binary `ic` is installed globally. The `lib-intercore.sh` wrappers just need `ic` on PATH. Simplest approach: **copy `lib-intercore.sh` into Clavain's hooks directory** so it's always available alongside the hooks. This avoids cross-module path resolution entirely.

**Step 1 (revised): Copy lib-intercore.sh to Clavain hooks**

```bash
cp infra/intercore/lib-intercore.sh hub/clavain/hooks/lib-intercore.sh
```

The Clavain hooks already source `lib.sh` from the same directory. This follows the same pattern.

**Step 2: Replace temp file sentinel with intercore wrapper**

In `catalog-reminder.sh`, replace lines 21-23:

```bash
# Old:
SENTINEL="/tmp/clavain-catalog-remind-${CLAUDE_SESSION_ID:-unknown}.lock"
[ -f "$SENTINEL" ] && exit 0
touch "$SENTINEL"
```

With:

```bash
# Source intercore wrappers (fail-safe: falls back to temp files)
source "${BASH_SOURCE[0]%/*}/lib-intercore.sh" 2>/dev/null || true

# One reminder per session (intercore sentinel or temp file fallback)
_SID="${CLAUDE_SESSION_ID:-unknown}"
intercore_check_or_die "catalog_remind" "$_SID" 0 "/tmp/clavain-catalog-remind-${_SID}.lock"
```

**Step 3: Verify syntax**

Run: `bash -n hub/clavain/hooks/catalog-reminder.sh`
Expected: no output (clean parse)

**Step 4: Commit**

```bash
git add hub/clavain/hooks/catalog-reminder.sh hub/clavain/hooks/lib-intercore.sh
git commit -m "feat(clavain): migrate catalog-reminder.sh to intercore sentinel"
```

---

### Task 3: Migrate session-handoff.sh (2 sentinels: stop + handoff)

**Files:**
- Modify: `hub/clavain/hooks/session-handoff.sh`

This hook uses two once-per-session sentinels: `stop` (shared across Stop hooks to prevent cascading) and `handoff` (per-hook dedup).

**Step 1: Source lib-intercore.sh**

Add after line 18 (`set -euo pipefail`):

```bash
# Source intercore wrappers (fail-safe)
source "${BASH_SOURCE[0]%/*}/lib-intercore.sh" 2>/dev/null || true
```

**Step 2: Replace the stop sentinel (lines 35-40)**

Replace:
```bash
STOP_SENTINEL="/tmp/clavain-stop-${SESSION_ID}"
if [[ -f "$STOP_SENTINEL" ]]; then
    exit 0
fi
touch "$STOP_SENTINEL"
```

With:
```bash
# CRITICAL: Stop sentinel must be written unconditionally to prevent hook cascade.
# The wrapper handles DB-vs-file internally, but if the wrapper is unavailable
# (e.g., lib-intercore.sh failed to source), intercore_check_or_die falls back
# to inline temp file logic. See Note on Fallback TOCTOU.
intercore_check_or_die "$INTERCORE_STOP_DEDUP_SENTINEL" "$SESSION_ID" 0 "/tmp/clavain-stop-${SESSION_ID}"
```

**Step 3: Replace the handoff sentinel (lines 43-46)**

Replace:
```bash
SENTINEL="/tmp/clavain-handoff-${SESSION_ID}"
if [[ -f "$SENTINEL" ]]; then
    exit 0
fi
```

With:
```bash
intercore_check_or_die "handoff" "$SESSION_ID" 0 "/tmp/clavain-handoff-${SESSION_ID}"
```

(Also remove the now-redundant `touch "$SENTINEL"` on line 86.)

**Step 4: Replace the stale sentinel cleanup (lines 140-141)**

Replace:
```bash
find /tmp -maxdepth 1 -name 'clavain-stop-*' -mmin +60 -delete 2>/dev/null || true
```

With:
```bash
if type intercore_cleanup_stale &>/dev/null; then
    intercore_cleanup_stale
else
    find /tmp -maxdepth 1 -name 'clavain-stop-*' -mmin +60 -delete 2>/dev/null || true
fi
```

**Step 5: Verify syntax**

Run: `bash -n hub/clavain/hooks/session-handoff.sh`
Expected: no output

**Step 6: Commit**

```bash
git add hub/clavain/hooks/session-handoff.sh
git commit -m "feat(clavain): migrate session-handoff.sh to intercore sentinels"
```

---

### Task 4: Migrate auto-compound.sh (stop sentinel + 5-min throttle)

**Files:**
- Modify: `hub/clavain/hooks/auto-compound.sh`

This hook has the stop sentinel (shared) plus a time-based throttle (5 minutes = 300 seconds).

**Step 1: Source lib-intercore.sh**

Add after `set -euo pipefail`:

```bash
source "${BASH_SOURCE[0]%/*}/lib-intercore.sh" 2>/dev/null || true
```

**Step 2: Replace the stop sentinel (lines 48-53)**

Replace:
```bash
STOP_SENTINEL="/tmp/clavain-stop-${SESSION_ID}"
if [[ -f "$STOP_SENTINEL" ]]; then
    exit 0
fi
touch "$STOP_SENTINEL"
```

With:
```bash
# Claim stop sentinel FIRST (before throttle check) to prevent other hooks
# from analyzing the transcript, even if this hook exits due to throttle.
intercore_check_or_die "$INTERCORE_STOP_DEDUP_SENTINEL" "$SESSION_ID" 0 "/tmp/clavain-stop-${SESSION_ID}"
```

**Step 3: Replace the compound throttle (lines 56-63)**

Replace the throttle sentinel check AND the standalone `touch "$THROTTLE_SENTINEL"` on line 100 with:

```bash
# THEN check throttle (5-min cooldown specific to this hook)
intercore_check_or_die "compound_throttle" "$SESSION_ID" 300 "/tmp/clavain-compound-last-${SESSION_ID}"
```

Note: `intercore_check_or_die` handles both DB and legacy paths. The intercore DB writes atomically at check time; the legacy path touches the file inside the helper. Remove the standalone `touch "$THROTTLE_SENTINEL"` later in the file.

**Step 4: Replace stale cleanup (lines 116-117)**

Remove the cleanup call entirely from auto-compound.sh. Cleanup now runs ONCE per stop cycle from session-handoff.sh only (S3 fix).

**Step 5: Verify syntax**

Run: `bash -n hub/clavain/hooks/auto-compound.sh`
Expected: no output

**Step 6: Commit**

```bash
git add hub/clavain/hooks/auto-compound.sh
git commit -m "feat(clavain): migrate auto-compound.sh to intercore sentinels"
```

---

### Task 5: Migrate auto-drift-check.sh (stop sentinel + 10-min throttle)

**Files:**
- Modify: `hub/clavain/hooks/auto-drift-check.sh`

Nearly identical to auto-compound.sh but with 600s (10 min) throttle.

**Step 1: Source lib-intercore.sh**

Add after `set -euo pipefail`:

```bash
source "${BASH_SOURCE[0]%/*}/lib-intercore.sh" 2>/dev/null || true
```

**Step 2: Replace the stop sentinel (lines 42-46)**

Same pattern as Task 4:

```bash
# Claim stop sentinel FIRST (before throttle check)
intercore_check_or_die "$INTERCORE_STOP_DEDUP_SENTINEL" "$SESSION_ID" 0 "/tmp/clavain-stop-${SESSION_ID}"
```

**Step 3: Replace the drift throttle (lines 49-56)**

Replace the throttle check AND standalone `touch` with:

```bash
# THEN check throttle (10-min cooldown specific to this hook)
intercore_check_or_die "drift_throttle" "$SESSION_ID" 600 "/tmp/clavain-drift-last-${SESSION_ID}"
```

**Step 4: Replace stale cleanup (lines 109-110)**

Remove cleanup from auto-drift-check.sh. Cleanup runs ONCE from session-handoff.sh only.

**Step 5: Verify syntax**

Run: `bash -n hub/clavain/hooks/auto-drift-check.sh`
Expected: no output

**Step 6: Commit**

```bash
git add hub/clavain/hooks/auto-drift-check.sh
git commit -m "feat(clavain): migrate auto-drift-check.sh to intercore sentinels"
```

---

### Task 6: Migrate auto-publish.sh (global sentinel with 60s TTL)

**Files:**
- Modify: `hub/clavain/hooks/auto-publish.sh`

This hook uses a global sentinel (not per-session) with a 60s expiry window.

**Step 1: Source lib-intercore.sh**

Add inside the `main()` function, after the jq guard:

```bash
source "${BASH_SOURCE[0]%/*}/lib-intercore.sh" 2>/dev/null || true
```

**Step 2: Replace the sentinel check (lines 57-68)**

Replace the sentinel check AND standalone `touch "$sentinel"` (line 91) with:

```bash
    intercore_check_or_die "autopub" "global" 60 "/tmp/clavain-autopub.lock"
```

Note: `intercore_check_or_die` handles both DB (writes atomically) and legacy (touches file inside helper). Remove the standalone `touch` later in the function.

**Step 4: Verify syntax**

Run: `bash -n hub/clavain/hooks/auto-publish.sh`
Expected: no output

**Step 5: Commit**

```bash
git add hub/clavain/hooks/auto-publish.sh
git commit -m "feat(clavain): migrate auto-publish.sh to intercore sentinel"
```

---

### Task 7: Migrate lib-sprint.sh discovery cache invalidation

**Files:**
- Modify: `hub/clavain/hooks/lib-sprint.sh`

The `sprint_invalidate_caches` function deletes `/tmp/clavain-discovery-brief-*.cache` files. Discovery caches are **cached data** (not throttle sentinels), so use `ic state delete` — the correct abstraction for cache invalidation. The `intercore_state_delete_all` helper was already defined in Task 1.

**Step 1: Source lib-intercore.sh**

Add at the top of `lib-sprint.sh` (after the double-source guard):

```bash
# Source intercore wrappers (for cache invalidation via state delete)
source "${BASH_SOURCE[0]%/*}/lib-intercore.sh" 2>/dev/null || true
```

**Step 2: Replace sprint_invalidate_caches (line 880)**

Replace:
```bash
sprint_invalidate_caches() {
    rm -f /tmp/clavain-discovery-brief-*.cache 2>/dev/null || true
}
```

With:
```bash
sprint_invalidate_caches() {
    if type intercore_state_delete_all &>/dev/null; then
        intercore_state_delete_all "discovery_brief" "/tmp/clavain-discovery-brief-*.cache"
    else
        rm -f /tmp/clavain-discovery-brief-*.cache 2>/dev/null || true
    fi
}
```

**Step 3: Verify syntax**

Run: `bash -n hub/clavain/hooks/lib-sprint.sh`
Expected: no output

**Step 4: Commit**

```bash
git add hub/clavain/hooks/lib-sprint.sh
git commit -m "feat(clavain): migrate discovery cache invalidation to intercore state"
```

---

### Task 8: Integration verification and ic compat status update

**Files:**
- Verify: All modified hooks
- Run: `infra/intercore/test-integration.sh`
- Run: `ic compat status` to confirm migration state

**Step 1: Run intercore integration tests**

Run: `cd infra/intercore && bash test-integration.sh`
Expected: All tests pass

**Step 2: Syntax-check all modified hooks**

Run:
```bash
for f in hub/clavain/hooks/catalog-reminder.sh hub/clavain/hooks/session-handoff.sh hub/clavain/hooks/auto-compound.sh hub/clavain/hooks/auto-drift-check.sh hub/clavain/hooks/auto-publish.sh hub/clavain/hooks/lib-sprint.sh hub/clavain/hooks/lib-intercore.sh; do bash -n "$f" || echo "FAIL: $f"; done
```
Expected: no output (all clean)

**Step 3: Verify ic compat status shows DB coverage**

Run: `ic init && ic compat status`

The output should show `yes` in the DB column for all keys that have been migrated. (Actual DB entries only appear after hooks run in a real session, but the compat status should at least show the key names.)

**Step 4: Final commit**

```bash
git add -A
git commit -m "feat(clavain): complete hook adapter migration to intercore DB (iv-wo1t)

All 6 hooks that used /tmp/clavain-* temp files now route through intercore
sentinel DB when ic is available, with transparent fallback to temp files.

Migrated hooks:
- catalog-reminder.sh (1 sentinel)
- session-handoff.sh (2 sentinels)
- auto-compound.sh (stop + 5min throttle)
- auto-drift-check.sh (stop + 10min throttle)
- auto-publish.sh (global 60s sentinel)
- lib-sprint.sh (cache invalidation)

New lib-intercore.sh wrappers:
- intercore_sentinel_check_or_legacy (DB-first, exit 2 → legacy fallback)
- intercore_check_or_die (convenience: check + exit 0 if throttled)
- intercore_sentinel_reset_or_legacy
- intercore_sentinel_reset_all
- intercore_state_delete_all (for cache invalidation)
- intercore_cleanup_stale"
```

---

## Notes for the Implementer

1. **Fail-safe principle**: `intercore_check_or_die` handles all three layers: (a) try `ic sentinel check` via DB, (b) if `ic` errors (exit 2+), fall through to temp file, (c) if lib-intercore.sh failed to source, use inline legacy temp file logic. Hooks just call one function. Zero regression risk.

2. **The `stop` sentinel is shared (anti-cascade protocol)**: Multiple Stop hooks (`session-handoff`, `auto-compound`, `auto-drift-check`) all check the same `$INTERCORE_STOP_DEDUP_SENTINEL` sentinel to prevent cascading. The first hook to fire claims it. **All Stop hooks MUST check this sentinel before doing work.** The constant is defined in `lib-intercore.sh` and is greppable.

3. **Stop/throttle ordering**: Claim the stop sentinel FIRST (before throttle check). This prevents other hooks from analyzing the transcript, even if this hook exits due to its throttle. This is intentional — only one hook should do expensive transcript analysis per Stop event.

4. **`intercore_sentinel_check_or_legacy` return codes**: Returns 0 = allowed (proceed), 1 = throttled (skip), falls through to legacy on exit 2+ (error). The `|| exit 0` pattern via `intercore_check_or_die` handles all cases.

5. **Note on Fallback TOCTOU (P0-2)**: Systems without `ic` installed use temp-file sentinels which have a known TOCTOU race (two hooks can both claim the same sentinel). This is acceptable because (1) Claude Code runs hooks sequentially by default, making races rare, and (2) the worst outcome is duplicate "block" prompts, not data corruption. The intercore DB path provides strict atomic mutual exclusion.

6. **No `session-start.sh` changes**: The bead description mentioned `session-start.sh`, but it doesn't use any `/tmp/clavain-*` temp files. Future work may move some of that to intercore state, but that's a separate bead.

7. **Copy vs. symlink for lib-intercore.sh**: Copying into `hub/clavain/hooks/` is deliberate — hooks run from the plugin cache directory. The copy includes a `INTERCORE_WRAPPER_VERSION` header and the integration test verifies sync. Re-copy when updating intercore.

8. **Discovery cache uses `state delete`, not sentinel**: Discovery caches are cached data (not throttle guards), so `intercore_state_delete_all` uses `ic state delete` instead of `ic sentinel reset`. This keeps `ic sentinel list` output clean — only throttle guards appear there.

9. **Cleanup runs once per stop cycle**: `intercore_cleanup_stale` is called ONLY from `session-handoff.sh` (the "primary" Stop hook). Not from auto-compound or auto-drift-check. This avoids redundant DB transactions.
