# Correctness Review: Intercore Hook Adapter Migration
**Bead:** iv-wo1t
**Reviewer:** Julik (Flux-drive Correctness Reviewer)
**Date:** 2026-02-17
**Plan:** docs/plans/2026-02-18-intercore-hook-adapter.md

## Executive Summary

The migration from bash temp-file sentinels to intercore SQLite DB calls is fundamentally sound. The Go sentinel implementation provides correct atomic claim semantics via `INSERT OR IGNORE` + conditional `UPDATE ... RETURNING` in a transaction. However, **three P0 correctness issues** and **six P1-P3 concerns** exist in the plan, primarily around stderr suppression, fallback divergence, and race-after-reset windows.

**Key findings:**
1. **P0**: Suppressing stderr in the wrapper hides DB errors that indicate the sentinel didn't write — this breaks the fail-safe claim
2. **P0**: The fallback legacy touch happens AFTER checking for existence, creating a TOCTOU race identical to the old code — expected, but undocumented as a deliberate regression acceptance
3. **P1**: `intercore_sentinel_reset_all` has a list-then-reset TOCTOU — new sentinels added between list and reset are missed

---

## P0 Findings (Data Corruption / Silent Failure Risk)

### P0-1: Stderr Suppression Hides Sentinel Write Failures

**Location:** Plan Task 1, Step 1, `intercore_sentinel_check_or_legacy` function line 59

**Code:**
```bash
"$INTERCORE_BIN" sentinel check "$name" "$scope_id" --interval="$interval" >/dev/null 2>&1
return $?
```

**Problem:** The `2>&1` redirection suppresses all stderr output, including error messages from `ic sentinel check` when the DB operation fails (e.g., `SQLITE_BUSY`, `SQLITE_CORRUPT`, disk full, permission denied). The wrapper then returns the exit code (2 = error) as if it were a throttle decision.

**Failure narrative:**
1. Hook A calls `intercore_sentinel_check_or_legacy "stop" "$SID" 0 "/tmp/clavain-stop-$SID"`
2. `ic sentinel check stop $SID --interval=0` hits `SQLITE_BUSY` because another process holds a write lock
3. `ic` writes "ic: sentinel check: database is locked" to stderr and exits with code 2
4. Wrapper suppresses stderr, sees exit 2, returns 2 (nonzero = throttled in bash `||` chain)
5. Hook A exits early thinking the sentinel was already claimed
6. Hook B runs immediately after, same BUSY error, same suppression
7. Hook C runs, DB lock clears, sentinel claim succeeds
8. **Result:** Both Hook A and Hook B were suppressed silently due to transient DB contention, only Hook C ran

**Correct behavior:** Hook A and Hook B should have fallen back to temp-file sentinel when DB became unavailable, preserving the atomic claim race. Instead, they exited without writing ANY sentinel (DB or temp-file), breaking the mutual exclusion guarantee.

**Impact:** When DB is under contention (multiple hooks racing at Stop event), all but one hook may silently skip sentinel writes, allowing duplicate execution (e.g., `auto-compound` and `session-handoff` both fire, producing two "block" decisions, confusing Claude).

**Exit code contract violation:** The plan claims exit 0 = allowed, 1 = throttled, but does not specify what exit 2 means. The existing `lib-intercore.sh` at line 42 suppresses stdout only:
```bash
"$INTERCORE_BIN" sentinel check "$name" "$scope_id" --interval="$interval" >/dev/null
```
This DOES allow stderr to propagate, which is correct. The plan's new wrapper adds `2>&1`, which is a regression.

**Fix:**
```bash
intercore_sentinel_check_or_legacy() {
    local name="$1" scope_id="$2" interval="$3" legacy_file="$4"
    if intercore_available; then
        # Suppress stdout (allowed/throttled message), preserve stderr (errors)
        # Exit 0 = allowed, 1 = throttled, 2 = error → fall back
        if "$INTERCORE_BIN" sentinel check "$name" "$scope_id" --interval="$interval" >/dev/null; then
            return 0  # allowed
        elif [[ $? -eq 1 ]]; then
            return 1  # throttled
        fi
        # Exit code 2 or 3 = error → fall through to legacy path
        # (error already written to stderr by ic, no suppression)
    fi
    # Fallback: temp file check
    # ... rest of legacy logic
}
```

**Severity:** P0 — DB errors are transient and common (especially on Stop hooks which race), silent suppression creates non-deterministic sentinel skipping that can duplicate hook execution or skip critical work.

---

### P0-2: Fallback Temp-File TOCTOU Is Undocumented Regression Acceptance

**Location:** Plan Task 1, Step 1, `intercore_sentinel_check_or_legacy` function lines 63-75

**Code:**
```bash
# Fallback: temp file check
if [[ -f "$legacy_file" ]]; then
    if [[ "$interval" -eq 0 ]]; then
        return 1  # once-per-session: file exists = throttled
    fi
    # ... stat/mtime check ...
fi
touch "$legacy_file"
return 0
```

**Problem:** This is the exact TOCTOU pattern the old code used (`[ -f file ] && exit 0; touch file`), which is NOT atomic. Two hooks can both check `[[ -f file ]]`, see false, then both `touch` the file and return 0 (allowed). The intercore DB path fixes this via `INSERT OR IGNORE` + conditional `UPDATE ... RETURNING`, but the fallback reintroduces the race.

**Failure narrative (interval=0, once-per-session sentinel):**
1. Hook A (auto-compound) and Hook B (session-handoff) both fire at Stop event
2. `ic` is not installed, so both use fallback
3. Hook A: `[[ -f /tmp/clavain-stop-$SID ]]` → false
4. Hook B: `[[ -f /tmp/clavain-stop-$SID ]]` → false (not yet touched)
5. Hook A: `touch /tmp/clavain-stop-$SID`, returns 0 (allowed)
6. Hook B: `touch /tmp/clavain-stop-$SID`, returns 0 (allowed)
7. **Result:** Both hooks execute, both return "block" decision with different prompts

**Is this a bug?** No — it's the KNOWN legacy behavior. The plan even says "This is TOCTOU-safe" for the DB path and "known TOCTOU, accepted for legacy" for the fallback. However, the plan does NOT document the consequence: **systems without `ic` installed have weaker mutual exclusion than systems with `ic`**.

**Impact:** On systems without `ic` (new Clavain users who haven't run `ic init` yet), the Stop hooks have the same race they've always had. This is acceptable IF:
- The race is rare (hooks run sequentially in most cases)
- The consequences are low (duplicate "block" prompts are noisy but not corrupting)

**Missing documentation:** The plan should state in the "Notes for the Implementer" section:
> **Degraded mutual exclusion without intercore:** On systems without `ic` installed, the temp-file fallback retains the original TOCTOU race where two hooks can both claim the same sentinel. This is acceptable because (1) Claude Code runs hooks sequentially by default, making races rare, and (2) the worst outcome is duplicate "block" prompts, not data corruption.

**Fix:** Add the above note to the plan. No code change needed — this is working as designed.

**Severity:** P0 — Not because the fallback is broken (it's intentionally legacy-compatible), but because the plan does NOT clearly state that the fallback provides weaker guarantees than the DB path. This could confuse implementers who assume "fail-safe" means "same semantics, just uses temp files." It doesn't — it means "degrades to old TOCTOU behavior."

---

### P0-3: Return Code Propagation in Wrapper Inverts Sentinel Logic

**Location:** Plan Task 2-7, all hook modifications

**Pattern in plan:**
```bash
if type intercore_sentinel_check_or_legacy &>/dev/null; then
    intercore_sentinel_check_or_legacy "stop" "$SESSION_ID" 0 "/tmp/clavain-stop-${SESSION_ID}" || exit 0
else
    # legacy fallback
fi
```

**Problem:** The `|| exit 0` assumes that the function returns 0 = allowed (proceed), nonzero = throttled (exit). But if the function returns exit code 2 (error), the hook also exits with 0 (success), which is correct for the hook (fail-open), but the `|| exit 0` pattern is misleading.

**Wait, is this actually a problem?** Let me trace through the exit codes:
- `ic sentinel check` exits 0 = allowed, 1 = throttled, 2 = error
- Wrapper returns 0 = allowed (proceed), 1 = throttled (skip), 2 = error (fall back)
- But the plan's wrapper does `return $?` after `ic sentinel check`, so it DOES return 2 on error
- Hook does `intercore_sentinel_check_or_legacy ... || exit 0`, so exit 2 → exit 0 (hook succeeds without blocking)

**Wait, that's wrong.** If the wrapper returns 2 (error), the hook should EITHER:
1. Fall back to legacy temp-file logic (what the wrapper should do internally), OR
2. Exit 0 (fail-open)

The current plan does #2 (exit 0 on error), but the wrapper ALSO has fallback logic. So there are two fallback layers:
- First layer: wrapper internal fallback (if `intercore_available` returns false OR `ic` exits nonzero)
- Second layer: hook-level fallback (if wrapper doesn't exist, use inline legacy logic)

**But the wrapper's first layer ONLY falls back if `intercore_available` returns false (binary not found or health check failed).** It does NOT fall back on `ic sentinel check` errors (exit 2). So if `ic sentinel check` returns 2, the wrapper returns 2, the hook sees nonzero, runs `exit 0`, and the sentinel is never written to temp file OR DB.

**Correct fix:** See P0-1 fix — the wrapper should catch exit code 2 and fall through to the temp-file path.

**Severity:** P0 — Same as P0-1, this is a silent failure mode where DB errors cause sentinels to not fire at all.

---

## P1 Findings (Race Conditions / Consistency Issues)

### P1-1: `intercore_sentinel_reset_all` List-Then-Reset TOCTOU

**Location:** Plan Task 1, Step 2 (revised), `intercore_sentinel_reset_all` function lines 606-619

**Code:**
```bash
intercore_sentinel_reset_all() {
    local name="$1" legacy_glob="$2"
    if intercore_available; then
        # List all scopes for this sentinel and reset each
        local scope
        while IFS=$'\t' read -r _name scope _fired; do
            [[ "$_name" == "$name" ]] || continue
            "$INTERCORE_BIN" sentinel reset "$name" "$scope" >/dev/null 2>&1 || true
        done < <("$INTERCORE_BIN" sentinel list 2>/dev/null || true)
        return 0
    fi
    # ...
}
```

**Problem:** The function lists all sentinels (`ic sentinel list`), then iterates and resets each one. Between the `list` and the `reset`, a new sentinel with the same name but different scope_id could be added by a concurrent hook. That new sentinel will not appear in the list, so it won't be reset.

**Failure narrative:**
1. Session A's `sprint_invalidate_caches` calls `intercore_sentinel_reset_all "discovery_brief" "..."`
2. Function runs `ic sentinel list`, gets scopes: `[session-a, session-b]`
3. Session C (concurrent, different session) calls `ic sentinel check discovery_brief session-c --interval=0`
4. Session C's sentinel is inserted: `discovery_brief / session-c / last_fired=<now>`
5. Session A's reset loop runs: resets `discovery_brief/session-a`, resets `discovery_brief/session-b`
6. Session A's reset completes, returns 0
7. **Result:** `discovery_brief/session-c` is still active (last_fired set), was NOT reset

**Impact:** Cache invalidation is incomplete. When `sprint_invalidate_caches` is called (e.g., after closing a bead), it's supposed to clear ALL discovery caches so the next session sees fresh data. But if a concurrent session added a discovery_brief sentinel during the reset, that session's cache is still marked "valid" even though the underlying data changed.

**How likely is this?** Very low. The `discovery_brief` sentinel is only used in the discovery cache pattern (not implemented in the current plan). The plan mentions it as a placeholder for future work. So this is a latent bug that will only manifest if the discovery cache pattern is actually implemented AND two sessions are running concurrently in the same repo.

**Correct fix:** Use a wildcard DELETE in SQL:
```bash
intercore_sentinel_reset_all() {
    local name="$1" legacy_glob="$2"
    if intercore_available; then
        # Single DELETE with wildcard: DELETE FROM sentinels WHERE name = ?
        # No list-then-reset race.
        "$INTERCORE_BIN" sentinel reset "$name" "*" 2>&1 | grep -v 'not found' || true
        return 0
    fi
    # ...
}
```

But wait — the plan notes that `ic sentinel reset <name> <scope_id>` does `DELETE WHERE name = ? AND scope_id = ?`, so passing `*` as scope_id would only match a literal `*`. The plan RECOGNIZES this and chooses the list-then-reset approach.

**Better fix:** Add a new `ic sentinel reset-all <name>` subcommand that does `DELETE FROM sentinels WHERE name = ?` atomically. Then:
```bash
intercore_sentinel_reset_all() {
    local name="$1" legacy_glob="$2"
    if intercore_available; then
        "$INTERCORE_BIN" sentinel reset-all "$name" >/dev/null 2>&1 || true
        return 0
    fi
    rm -f $legacy_glob 2>/dev/null || true
}
```

This avoids the TOCTOU and matches the temp-file fallback semantics (which uses `rm -f /tmp/clavain-discovery-brief-*.cache`, a single atomic syscall that removes all matching files).

**Severity:** P1 — The race is real but low-likelihood (requires concurrent sessions in the same repo during cache invalidation). The fix is trivial (add `reset-all` subcommand to `ic`). Mark as "fix before discovery_brief pattern is actually used."

---

### P1-2: Auto-Compound Two-Stage Guard Has Misleading Comment

**Location:** Plan Task 4, auto-compound.sh migration

**Code in plan:**
```bash
# Step 2: Replace the stop sentinel (lines 48-53)
if type intercore_sentinel_check_or_legacy &>/dev/null; then
    intercore_sentinel_check_or_legacy "stop" "$SESSION_ID" 0 "/tmp/clavain-stop-${SESSION_ID}" || exit 0
else
    # legacy fallback
fi

# Step 3: Replace the compound throttle (lines 56-63)
if type intercore_sentinel_check_or_legacy &>/dev/null; then
    intercore_sentinel_check_or_legacy "compound_throttle" "$SESSION_ID" 300 "/tmp/clavain-compound-last-${SESSION_ID}" || exit 0
else
    # legacy fallback
fi
```

**Problem:** The plan's description says "The stop sentinel (shared) plus a time-based throttle (5 minutes = 300 seconds)." This is correct, but the plan does NOT explain the critical ordering invariant: **the stop sentinel MUST be checked first, before the throttle.**

**Why does order matter?** Because the stop sentinel (interval=0, once-per-session) is used by ALL Stop hooks (`auto-compound`, `session-handoff`, `auto-drift-check`) to ensure only ONE hook fires per session. The compound_throttle sentinel (interval=300) is specific to auto-compound, preventing it from firing more than once per 5 minutes.

**Correct flow:**
1. Check stop sentinel (interval=0): if already claimed by another hook, exit
2. Claim stop sentinel (write it so no other hook can proceed)
3. Check throttle sentinel (interval=300): if fired <5min ago, exit
4. Claim throttle sentinel (write it)
5. Do the work

**The plan DOES preserve this order** (stop sentinel check is Step 2, throttle check is Step 3), but it doesn't EXPLAIN why. An implementer might reverse the order ("check the throttle first to fail fast before touching the stop sentinel"), which would break the mutual exclusion guarantee.

**Failure narrative if order reversed:**
1. Hook A (auto-compound) checks compound_throttle (interval=300), sees last_fired was 10min ago, proceeds
2. Hook B (session-handoff) checks its own throttle (not applicable, no throttle), proceeds
3. Hook A checks stop sentinel, claims it
4. Hook B checks stop sentinel, sees it's claimed, exits
5. **Result:** Hook A fires (correct)

Wait, that's correct. Let me try again:

1. Hook A (auto-compound) checks compound_throttle, sees last_fired was 2min ago (within throttle), exits
2. Hook A never checks stop sentinel, never claims it
3. Hook B (session-handoff) checks stop sentinel, claims it, fires
4. **Result:** Hook B fires, Hook A doesn't

Is that wrong? No — Hook A is throttled, so it SHOULD exit. The stop sentinel exists to prevent CASCADING (Hook A fires → returns block → Hook B fires → returns another block). If Hook A is throttled, it doesn't fire, so there's no cascade.

**So what's the actual invariant?** The stop sentinel prevents multiple hooks from ALL firing in the same Stop event cycle. The throttle prevents a SINGLE hook from firing too frequently. Checking throttle first is CORRECT (fail fast), checking stop first is ALSO correct (claim mutual exclusion first).

**Is there a real bug here?** No. The plan's order (stop first, throttle second) is safe but not required. Checking throttle first is also safe. The only requirement is that the throttle sentinel is NOT shared across hooks (each hook has its own throttle key: `compound_throttle`, `drift_throttle`).

**BUT:** The plan has `touch "$STOP_SENTINEL"` on line 53 (after the stop check), then throttle check on lines 56-63, then `touch "$THROTTLE_SENTINEL"` on line 100 (at the end). This order means the stop sentinel is claimed BEFORE the throttle check, so if the throttle check fails, the stop sentinel is ALREADY claimed, preventing other hooks from running even though this hook didn't do any work.

**Is THAT a bug?** Yes. Here's the correct failure:

**Failure narrative (with plan's proposed order):**
1. Hook A (auto-compound) checks stop sentinel (interval=0), claims it (writes `/tmp/clavain-stop-$SID`)
2. Hook A checks compound_throttle (interval=300), sees last_fired was 2min ago, exits
3. Hook B (session-handoff) checks stop sentinel, sees it's claimed, exits
4. Hook C (auto-drift-check) checks stop sentinel, sees it's claimed, exits
5. **Result:** No hook fires, even though Hook B and Hook C were eligible

**Correct order:**
1. Check stop sentinel (don't claim yet, just return early if already claimed)
2. Check throttle (if throttled, exit WITHOUT claiming stop)
3. Claim stop sentinel (write it)
4. Do the work
5. Claim throttle sentinel (write it)

**How to implement check-without-claim?** The current `[ -f file ]` pattern does check-without-claim naturally. The `intercore_sentinel_check` wrapper does claim (writes last_fired). So we need TWO wrappers:
- `intercore_sentinel_is_claimed` — read-only check, returns 0 if NOT claimed, 1 if claimed
- `intercore_sentinel_claim` — write-only claim, writes last_fired

But that's a significant redesign. Let me re-read the plan's code...

**Re-reading auto-compound.sh lines 48-53 in the plan:**
```bash
STOP_SENTINEL="/tmp/clavain-stop-${SESSION_ID}"
if [[ -f "$STOP_SENTINEL" ]]; then
    exit 0
fi
touch "$STOP_SENTINEL"
```

This is check-then-claim. The plan's replacement:
```bash
if type intercore_sentinel_check_or_legacy &>/dev/null; then
    intercore_sentinel_check_or_legacy "stop" "$SESSION_ID" 0 "/tmp/clavain-stop-${SESSION_ID}" || exit 0
else
    STOP_SENTINEL="/tmp/clavain-stop-${SESSION_ID}"
    [[ -f "$STOP_SENTINEL" ]] && exit 0
    touch "$STOP_SENTINEL"
fi
```

The wrapper does `UPDATE ... WHERE last_fired = 0 RETURNING 1` (atomic check-and-claim). If it returns 1 (throttled), the hook exits. If it returns 0 (allowed), the sentinel is ALREADY claimed (last_fired was updated). So there's no way to "check without claiming."

**Is this a problem?** Let me re-read the original `auto-compound.sh` to see the actual order...

From the earlier read:
```bash
# Guard: if another Stop hook already fired this cycle, don't cascade
STOP_SENTINEL="/tmp/clavain-stop-${SESSION_ID}"
if [[ -f "$STOP_SENTINEL" ]]; then
    exit 0
fi
# Write sentinel NOW — before transcript analysis — to minimize TOCTOU window
touch "$STOP_SENTINEL"

# Guard: throttle — at most once per 5 minutes
THROTTLE_SENTINEL="/tmp/clavain-compound-last-${SESSION_ID}"
if [[ -f "$THROTTLE_SENTINEL" ]]; then
    THROTTLE_MTIME=$(...)
    if [[ $((THROTTLE_NOW - THROTTLE_MTIME)) -lt 300 ]]; then
        exit 0
    fi
fi
```

**Aha!** The original code writes the stop sentinel BEFORE checking the throttle. The comment even says "Write sentinel NOW — before transcript analysis — to minimize TOCTOU window." So the plan's order is CORRECT — it matches the original.

**Why is this correct?** Because the stop sentinel's purpose is to prevent cascading hooks from ANALYZING the transcript multiple times. Even if the throttle check fails, the stop sentinel should still be claimed so no other hook does the expensive transcript analysis.

**So there's no bug here.** The order is intentional. The "cost" is that if Hook A claims the stop sentinel then exits due to throttle, Hook B can't run even if it wasn't throttled. But that's DESIRED behavior — only one hook should do the transcript analysis per Stop event.

**Severity:** Not a bug, but the plan should add a comment explaining the order:
```bash
# Claim stop sentinel FIRST (before throttle check) to prevent other hooks
# from analyzing the transcript, even if this hook exits due to throttle.
intercore_sentinel_check_or_legacy "stop" "$SESSION_ID" 0 "..." || exit 0

# THEN check throttle (5-min cooldown specific to this hook)
intercore_sentinel_check_or_legacy "compound_throttle" "$SESSION_ID" 300 "..." || exit 0
```

**Reclassify:** P2 — Documentation gap, not a correctness bug.

---

### P1-3: Sentinel Auto-Prune Timing Is Inconsistent Across Hooks

**Location:** Plan Task 1, sentinel.go lines 72-75 (auto-prune in transaction), vs Task 3 Step 4, session-handoff.sh line 140 (find -mmin +60)

**Code:**
```go
// sentinel.go line 72-75
// Synchronous auto-prune: delete stale sentinels in same tx
if _, err := tx.ExecContext(ctx,
    "DELETE FROM sentinels WHERE unixepoch() - last_fired > 604800"); err != nil {
    fmt.Fprintf(os.Stderr, "ic: auto-prune: %v\n", err)
}
```

**Hooks cleanup:**
```bash
# session-handoff.sh line 140
find /tmp -maxdepth 1 -name 'clavain-stop-*' -mmin +60 -delete 2>/dev/null || true

# auto-compound.sh line 117
find /tmp -maxdepth 1 \( -name 'clavain-stop-*' -o -name 'clavain-drift-last-*' -o -name 'clavain-compound-last-*' \) -mmin +60 -delete 2>/dev/null || true
```

**Problem:** The Go auto-prune uses 604800 seconds (7 days), but the bash cleanup uses 60 minutes (1 hour). This is a **10080× difference** in retention.

**Impact:** The intercore DB will accumulate sentinels for 7 days before pruning, but the temp files are deleted after 1 hour. This means:
- Systems WITH `ic`: Old sessions' sentinels live for 7 days (not a problem, they're marked as fired so they don't block)
- Systems WITHOUT `ic`: Old sessions' temp files are deleted after 1 hour (matches current behavior)

**Is this a problem?** No, different retention is fine. The 7-day retention in the DB allows `ic sentinel list` to show history for debugging ("why did this hook not fire?"). The 1-hour retention for temp files is aggressive cleanup to avoid `/tmp` clutter.

**But:** The plan does NOT explain this difference. An implementer might assume "1 hour" is the correct threshold and change the Go code to match:
```go
// WRONG: Don't do this
"DELETE FROM sentinels WHERE unixepoch() - last_fired > 3600"
```

**Correct documentation:** Add to plan Task 1 notes:
> **Retention policy difference:** The DB auto-prune uses 7 days (604800 sec) to preserve history for debugging, while temp-file cleanup uses 1 hour (60 min) for aggressive cleanup. This is intentional — the DB can afford longer retention, and keeping fired sentinels aids post-mortem analysis.

**Severity:** P2 — Documentation gap, not a bug. The current thresholds are reasonable.

---

## P2 Findings (Edge Cases / Future Concerns)

### P2-1: `intercore_cleanup_stale` Calls Prune Without Arguments

**Location:** Plan Task 3 Step 4, replacement for find -mmin

**Code:**
```bash
if type intercore_cleanup_stale &>/dev/null; then
    intercore_cleanup_stale
else
    find /tmp -maxdepth 1 -name 'clavain-stop-*' -mmin +60 -delete 2>/dev/null || true
fi
```

**Wrapper from plan Task 1:**
```bash
intercore_cleanup_stale() {
    if intercore_available; then
        "$INTERCORE_BIN" sentinel prune --older-than=1h >/dev/null 2>&1 || true
        return 0
    fi
    # Fallback: clean legacy temp files
    find /tmp -maxdepth 1 \( -name 'clavain-stop-*' -o -name 'clavain-drift-last-*' -o -name 'clavain-compound-last-*' \) -mmin +60 -delete 2>/dev/null || true
}
```

**Issue:** The wrapper calls `ic sentinel prune --older-than=1h`, but the Go auto-prune in `sentinel.Check` uses 604800 sec (7 days). This means:
- Auto-prune (runs on every `ic sentinel check`): deletes sentinels >7 days old
- Manual prune (runs via `intercore_cleanup_stale`): deletes sentinels >1 hour old

**Wait, that's inconsistent.** If the manual prune uses 1 hour, it will delete sentinels that the auto-prune would keep. Is that a problem?

**No — it's correct.** The auto-prune runs in the SAME transaction as the sentinel check, so it can't delete the sentinel being checked (it just got updated). The manual prune runs SEPARATELY, typically at the end of a hook after all sentinel checks are done. Using 1-hour threshold for manual prune matches the temp-file cleanup behavior and is safe (sentinels older than 1 hour are from previous sessions, safe to delete).

**But:** The 7-day auto-prune is ALSO running on every `ic sentinel check`, so sentinels older than 1 hour but younger than 7 days will be kept by the auto-prune, then deleted by the manual prune. This is redundant but harmless.

**Recommendation:** Make the auto-prune threshold configurable or remove it entirely (rely on manual prune). But for v1, the current behavior is safe.

**Severity:** P3 — Minor inconsistency, no correctness impact.

---

### P2-2: Plan's Step 3 Touch Removal Is Incomplete

**Location:** Plan Task 4 Step 3, auto-compound.sh migration

**Plan text:**
> "And the `touch "$THROTTLE_SENTINEL"` on line 100. Replace both with: ..."

**Then:**
> "Move the throttle sentinel touch into the else branch (before the `exit 0` at end), and remove the standalone `touch "$THROTTLE_SENTINEL"` later in the file since `intercore_sentinel_check_or_legacy` handles writing the sentinel atomically."

**Problem:** The plan says "remove the standalone touch" but ALSO says "move it into the else branch." These are contradictory. The correct behavior:
- **Intercore path:** No explicit touch needed, `ic sentinel check` writes last_fired atomically
- **Legacy path:** Explicit `touch "$THROTTLE_SENTINEL"` needed after all guards pass

**Plan should say:**
> "Remove the standalone `touch "$THROTTLE_SENTINEL"` on line 100. For the legacy path, add `touch "$THROTTLE_SENTINEL"` inside the else branch AFTER all checks pass."

**Severity:** P2 — Ambiguous instruction, implementer might misinterpret.

---

### P2-3: Copy lib-intercore.sh Bloats Clavain Plugin on Every Intercore Update

**Location:** Plan Task 2 Step 1 (revised)

**Plan text:**
> "Actually, this is over-engineered. ... Simplest approach: **copy `lib-intercore.sh` into Clavain's hooks directory** so it's always available alongside the hooks."

**Problem:** Every time `intercore` is updated (new wrappers, bug fixes), the Clavain plugin needs to re-copy `lib-intercore.sh` and release a new version. This creates a version skew risk where Clavain is using an old `lib-intercore.sh` that doesn't match the installed `ic` binary.

**Better approach:** Install `lib-intercore.sh` alongside `ic` binary (e.g., `/usr/local/bin/ic` → `/usr/local/lib/intercore/lib-intercore.sh`), then source it with a fallback:
```bash
# Try installed lib first, fall back to bundled copy
if [[ -f /usr/local/lib/intercore/lib-intercore.sh ]]; then
    source /usr/local/lib/intercore/lib-intercore.sh
elif [[ -f "${BASH_SOURCE[0]%/*}/lib-intercore.sh" ]]; then
    source "${BASH_SOURCE[0]%/*}/lib-intercore.sh"
fi
```

**Severity:** P2 — Maintenance burden, not a correctness issue. The copy approach works, just creates coupling.

---

## P3 Findings (Style / Minor Issues)

### P3-1: Wrapper Function Name Uses `_or_legacy` Suffix Inconsistently

**Functions:**
- `intercore_sentinel_check_or_legacy` ✅
- `intercore_sentinel_reset_or_legacy` ✅
- `intercore_sentinel_reset_all` ❌ (no `_or_legacy` suffix)
- `intercore_cleanup_stale` ❌ (no `_or_legacy` suffix)

**Issue:** The `_or_legacy` suffix clearly indicates "tries intercore, falls back to temp files." But `intercore_cleanup_stale` also has fallback logic. Should be `intercore_cleanup_stale_or_legacy` for consistency.

**Severity:** P3 — Style inconsistency, not a bug.

---

### P3-2: Plan Uses `type ... &>/dev/null` Instead of `command -v`

**Code:**
```bash
if type intercore_sentinel_check_or_legacy &>/dev/null; then
```

**Better:**
```bash
if declare -f intercore_sentinel_check_or_legacy >/dev/null 2>&1; then
```

**Why:** `type` is a bash builtin that outputs text ("intercore_sentinel_check_or_legacy is a function"), while `declare -f` is the idiomatic way to check if a function exists. Also, `&>` is a bash-ism; `>/dev/null 2>&1` is POSIX-portable (though these are bash scripts, so `&>` is fine).

**Severity:** P3 — Style preference, both work.

---

### P3-3: Sentinel Prune in `sentinel.go` Logs to Stderr on Failure But Continues

**Location:** sentinel.go lines 72-75

**Code:**
```go
if _, err := tx.ExecContext(ctx,
    "DELETE FROM sentinels WHERE unixepoch() - last_fired > 604800"); err != nil {
    fmt.Fprintf(os.Stderr, "ic: auto-prune: %v\n", err)
}
```

**Issue:** If the prune DELETE fails (e.g., DB corruption, disk error), the error is logged to stderr but the transaction still commits. This means the sentinel check succeeded (last_fired was updated) even though the cleanup failed.

**Is this a problem?** No — the prune is a best-effort cleanup. If it fails, the DB will accumulate stale rows, but that doesn't affect correctness (stale rows have last_fired >7 days, so they won't match any checks).

**But:** The error goes to stderr, which (per P0-1) should NOT be suppressed by the wrapper. So if auto-prune fails, the hook will see the error on stderr. Should the wrapper treat this as a fatal error? No — the sentinel check SUCCEEDED, only the cleanup failed.

**Recommendation:** Change the auto-prune log prefix to make it clear it's non-fatal:
```go
fmt.Fprintf(os.Stderr, "ic: sentinel check: warning: auto-prune failed: %v\n", err)
```

**Severity:** P3 — Minor UX issue, not a correctness bug.

---

## Summary Table

| ID | Severity | Issue | Impact | Fix Complexity |
|----|----------|-------|--------|----------------|
| P0-1 | P0 | Stderr suppression hides DB errors | Sentinels not written on transient DB errors | Trivial (remove `2>&1`) |
| P0-2 | P0 | Fallback TOCTOU not documented as regression | Confusing semantics (DB=atomic, fallback=racy) | Trivial (add note) |
| P0-3 | P0 | Exit code 2 causes sentinel skip | Same as P0-1 | Trivial (catch exit 2) |
| P1-1 | P1 | `reset_all` list-then-reset TOCTOU | Incomplete cache invalidation | Medium (add `reset-all` subcommand) |
| P1-2 | P2 | Stop/throttle order not explained | Implementer confusion (but plan is correct) | Trivial (add comment) |
| P1-3 | P2 | Auto-prune 7d vs cleanup 1h not documented | Retention policy confusion | Trivial (add note) |
| P2-1 | P3 | Auto-prune vs manual prune threshold | Redundant cleanup, no impact | Low (unify thresholds) |
| P2-2 | P2 | Ambiguous "remove touch" instruction | Implementer might misinterpret | Trivial (clarify wording) |
| P2-3 | P2 | Copy lib-intercore.sh creates version skew | Maintenance burden | Medium (install alongside `ic`) |
| P3-1 | P3 | Inconsistent `_or_legacy` suffix | Style inconsistency | Trivial (rename) |
| P3-2 | P3 | `type` instead of `declare -f` | Style preference | Trivial (change command) |
| P3-3 | P3 | Auto-prune error log is terse | UX issue | Trivial (reword message) |

---

## Recommended Fixes

### Must Fix Before Merge (P0)

1. **Remove stderr suppression in wrapper:**
   ```bash
   # Line 59 in plan's intercore_sentinel_check_or_legacy
   # OLD:
   "$INTERCORE_BIN" sentinel check "$name" "$scope_id" --interval="$interval" >/dev/null 2>&1
   # NEW:
   if "$INTERCORE_BIN" sentinel check "$name" "$scope_id" --interval="$interval" >/dev/null; then
       return 0  # allowed
   elif [[ $? -eq 1 ]]; then
       return 1  # throttled
   fi
   # Fall through to legacy on error (exit 2/3)
   ```

2. **Document fallback TOCTOU as intentional:**
   Add to plan's "Notes for the Implementer" section:
   > **Fallback sentinel behavior:** Systems without `ic` installed use temp-file sentinels which have a known TOCTOU race (two hooks can both claim the same sentinel). This is acceptable because (1) hooks run sequentially in most cases, and (2) the worst outcome is duplicate prompts, not data corruption. The intercore DB path provides strict atomic mutual exclusion.

3. **Add routing-eligible check before reset_all:**
   Document that `intercore_sentinel_reset_all` should only be used for patterns where the TOCTOU is acceptable (cache invalidation), NOT for mutual-exclusion sentinels (stop, handoff).

### Should Fix Before v1 (P1)

4. **Add `ic sentinel reset-all <name>` subcommand:**
   ```go
   func (s *Store) ResetAll(ctx context.Context, name string) (int64, error) {
       result, err := s.db.ExecContext(ctx,
           "DELETE FROM sentinels WHERE name = ?", name)
       if err != nil {
           return 0, fmt.Errorf("reset-all: %w", err)
       }
       return result.RowsAffected()
   }
   ```

### Nice to Have (P2-P3)

5. Clarify stop/throttle ordering with comment
6. Document auto-prune retention difference
7. Consider installing lib-intercore.sh alongside `ic` binary
8. Rename `intercore_cleanup_stale` → `intercore_cleanup_stale_or_legacy`

---

## Final Verdict

**Plan is APPROVED with P0 fixes required.**

The migration design is sound. The Go sentinel implementation is correct (atomic claim via conditional UPDATE in transaction). The bash wrappers provide proper fail-safe fallback. The three P0 issues are all fixable with trivial changes (remove `2>&1`, add documentation, handle exit code 2). The P1 reset_all race is low-priority (only affects future cache pattern). Implement P0 fixes before merge, defer P1-P3 to follow-up issues.
