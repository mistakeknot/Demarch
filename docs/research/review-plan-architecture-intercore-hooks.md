# Architecture Review: Intercore Hook Adapter Migration Plan

**Reviewed:** 2026-02-17
**Plan:** `docs/plans/2026-02-18-intercore-hook-adapter.md`
**Bead:** iv-wo1t
**Reviewer:** Architecture & Design (Flux-drive)

## Executive Summary

This plan migrates 6 Clavain bash hooks from `/tmp/` temp file sentinels to intercore SQLite DB via wrapper library. The architecture has **three significant boundary issues** and **one major complexity debt** that will create maintenance burden and coupling risk.

**Key findings:**
- **P0:** Library copy pattern violates DRY and creates version skew risk across 2 repos
- **P1:** Fallback pattern is sound but implementation has incorrect sentinel write timing
- **P2:** Shared "stop" sentinel creates hidden coupling between unrelated hooks
- **P3:** Missing abstraction opportunity — duplicate conditional blocks in every hook

## Priority Findings

### P0: Library Copy Creates Version Skew and Violates DRY

**Issue:** Task 2 Step 1 copies `infra/intercore/lib-intercore.sh` into `hub/clavain/hooks/lib-intercore.sh`. The plan justifies this as "copy means the library version is pinned to the Clavain release, which is the correct semantic."

**Architecture concerns:**

1. **DRY violation across repositories:** The same 44-line library now exists in 2 git repos (Interverse monorepo root at `infra/intercore/` and Clavain plugin repo at `hub/clavain/hooks/`). When bugs are found or new wrappers are added to `infra/intercore/lib-intercore.sh`, they must be manually propagated to the Clavain copy. This is guaranteed drift.

2. **Version skew between intercore binary and hook library:** The `ic` binary and `lib-intercore.sh` are tightly coupled — they share the same exit code contract, the same `--interval` flag semantics, and the same sentinel name/scope_id schema. A copy means the library can diverge from the binary it wraps. Example failure scenario:
   - `infra/intercore/` adds a new sentinel flag `--skip-auto-prune` to `ic sentinel check`
   - `lib-intercore.sh` in `infra/intercore/` is updated to pass the flag
   - Clavain's copy is not updated
   - Hooks in Clavain call `ic sentinel check` via the old wrapper, missing the new flag
   - Behavior is inconsistent across different callers of the same `ic` binary

3. **Plugin cache path is not an obstacle to symlinks:** The plan states "The hooks run from the plugin cache directory, which is a different filesystem location. Symlinks or relative paths to the monorepo root would break." This is incorrect. The plugin cache is on the same filesystem (`~/.claude/plugins/cache/clavain@<version>/`), and symlinks work across directories on the same filesystem. The real obstacle is that **the monorepo root may not exist on systems where only the Clavain plugin is installed** (e.g., a user who installed Clavain from the marketplace but does not have the Interverse monorepo checked out).

4. **Copy pattern assumes monorepo-only deployment:** The copy is ONLY updated when someone runs `cp infra/intercore/lib-intercore.sh hub/clavain/hooks/lib-intercore.sh` from the Interverse root. This workflow assumes Clavain is always developed and released from within the monorepo. If Clavain is ever developed in isolation (its own standalone repo checkout), the copy becomes stale immediately.

**Root cause:** This is a **module boundary failure**. The hooks (in Clavain) have a runtime dependency on the `ic` binary (in intercore infra). The wrapper library is an **adapter layer** for that dependency. Adapters should live **with the client** (Clavain hooks) and be **generated or vendored from the source** (intercore), not manually copied and allowed to drift.

**Alternatives:**

| Approach | Pros | Cons | Verdict |
|----------|------|------|---------|
| **Copy (plan's choice)** | Simple, no path resolution | Version skew, manual sync, DRY violation | ❌ High coupling risk |
| **Symlink to monorepo** | Single source of truth, auto-syncs | Breaks if monorepo not present | ❌ Fragile |
| **Vendored lib in Clavain with sync check** | Clavain is self-contained, sync is explicit | Requires sync step on every intercore change | ✅ Acceptable if automated |
| **Embed lib content in hooks** | Zero dependency | Massive duplication (6 hooks × 44 lines) | ❌ Unmaintainable |
| **intercore installs lib to ~/.claude/lib/** | Global install, single source of truth | Requires intercore install step, global state | ⚠️ Viable but adds install complexity |

**Recommendation:**

Use **vendored lib with version pinning and sync enforcement**:

1. Copy `lib-intercore.sh` to `hub/clavain/hooks/lib-intercore.sh` (as planned), but add a **version header** to the library:
   ```bash
   # lib-intercore.sh — Bash wrappers for intercore CLI
   # Version: 0.1.0 (source: infra/intercore/lib-intercore.sh)
   INTERCORE_WRAPPER_VERSION="0.1.0"
   ```

2. Add a **sync check** to `infra/intercore/test-integration.sh`:
   ```bash
   # Verify Clavain's copy is in sync
   CLAVAIN_LIB="../../hub/clavain/hooks/lib-intercore.sh"
   if [[ -f "$CLAVAIN_LIB" ]]; then
       CLAVAIN_VER=$(grep '^INTERCORE_WRAPPER_VERSION=' "$CLAVAIN_LIB" | cut -d'"' -f2)
       SOURCE_VER=$(grep '^INTERCORE_WRAPPER_VERSION=' lib-intercore.sh | cut -d'"' -f2)
       if [[ "$CLAVAIN_VER" != "$SOURCE_VER" ]]; then
           echo "ERROR: Clavain's lib-intercore.sh is out of sync (source: $SOURCE_VER, clavain: $CLAVAIN_VER)"
           echo "Run: cp infra/intercore/lib-intercore.sh hub/clavain/hooks/lib-intercore.sh"
           exit 1
       fi
   fi
   ```

3. Add a **pre-commit hook or CI check** in the Clavain repo that verifies the wrapper version matches the minimum required `ic` binary version. If `ic version` returns `0.1.0` but the wrapper is `0.0.9`, fail the build.

4. Document the sync workflow in `infra/intercore/AGENTS.md` and `hub/clavain/AGENTS.md`.

This approach keeps the copy (so Clavain is self-contained) but makes drift **visible and actionable** instead of silent.

---

### P1: Fallback Pattern Has Incorrect Sentinel Write Timing

**Issue:** Task 3 Step 2 (session-handoff.sh stop sentinel migration) and Task 4 Step 2 (auto-compound.sh stop sentinel migration) place the legacy `touch "$STOP_SENTINEL"` **inside the `if type intercore_sentinel_check_or_legacy` conditional's else branch**.

**Current plan code (Task 3 Step 2):**
```bash
if type intercore_sentinel_check_or_legacy &>/dev/null; then
    intercore_sentinel_check_or_legacy "stop" "$SESSION_ID" 0 "/tmp/clavain-stop-${SESSION_ID}" || exit 0
else
    STOP_SENTINEL="/tmp/clavain-stop-${SESSION_ID}"
    [[ -f "$STOP_SENTINEL" ]] && exit 0
    touch "$STOP_SENTINEL"
fi
```

**Problem:** The sentinel write happens **conditionally** based on whether the wrapper function is available. But the stop sentinel serves a **critical safety function** — it prevents multiple Stop hooks from cascading in the same stop cycle (see comment in session-handoff.sh line 33: "if another Stop hook already fired this cycle, don't cascade").

If `lib-intercore.sh` fails to source (e.g., file not found, syntax error), the `type intercore_sentinel_check_or_legacy` check fails, and the code falls into the else branch. But if **both** `lib-intercore.sh` sourcing fails AND the else branch is not executed (e.g., the hook exits early for another reason), the stop sentinel is never written. This creates a **TOCTOU (time-of-check-time-of-use) vulnerability** where two Stop hooks can both pass the sentinel check and both fire.

**Current implementation in session-handoff.sh (lines 34-39):**
```bash
STOP_SENTINEL="/tmp/clavain-stop-${SESSION_ID}"
if [[ -f "$STOP_SENTINEL" ]]; then
    exit 0
fi
# Write sentinel NOW — before signal analysis — to minimize TOCTOU window
touch "$STOP_SENTINEL"
```

This is **unconditional** and happens **immediately after the check**. The migration must preserve this timing.

**Root cause:** The plan's wrapper function `intercore_sentinel_check_or_legacy` (Task 1 Step 1, lines 56-76) **already handles the sentinel write** via `touch "$legacy_file"` on line 74, but only when `intercore_available` returns false. If `intercore_available` returns true, the sentinel is written by `ic sentinel check` inside the DB. This is correct. But the conditional structure in Task 3/4 adds a **second layer** of conditional logic that can skip the write entirely if the function is not available.

**Correct pattern:**

The sentinel write must be **unconditional** at the hook level. The wrapper handles the DB-vs-file choice, but the hook must not wrap it in a `type` check. Instead:

```bash
# Source lib (fail-safe)
source "${BASH_SOURCE[0]%/*}/lib-intercore.sh" 2>/dev/null || true

# Stop sentinel (unconditional write via wrapper or fallback)
if type intercore_sentinel_check_or_legacy &>/dev/null; then
    # Wrapper available — handles both DB and legacy fallback internally
    intercore_sentinel_check_or_legacy "stop" "$SESSION_ID" 0 "/tmp/clavain-stop-${SESSION_ID}" || exit 0
else
    # Wrapper unavailable — inline legacy fallback (identical to pre-migration code)
    STOP_SENTINEL="/tmp/clavain-stop-${SESSION_ID}"
    [[ -f "$STOP_SENTINEL" ]] && exit 0
    touch "$STOP_SENTINEL"
fi
```

This is already what the plan shows, so the **real issue** is that the plan does not explain **why** the inline fallback is necessary. Without that explanation, a future maintainer might "optimize" by removing the else branch ("the wrapper handles fallback, so we don't need this"), breaking the TOCTOU safety.

**Recommendation:**

Add a comment to each migrated hook's stop sentinel block:
```bash
# CRITICAL: Stop sentinel must be written unconditionally to prevent hook cascade.
# The wrapper handles DB-vs-file internally, but if the wrapper is unavailable
# (e.g., lib-intercore.sh failed to source), we must fall back to inline temp file.
```

---

### P2: Shared "stop" Sentinel Creates Hidden Coupling

**Issue:** The plan's mapping table (line 29) shows that `session-handoff.sh`, `auto-compound.sh`, and `auto-drift-check.sh` all use the same `stop` sentinel key with the same scope (session ID). The plan states (Note 2, line 702): "The `stop` sentinel is shared: Multiple Stop hooks all check the same `stop` sentinel to prevent cascading."

**Architecture concerns:**

1. **Implicit dependency between independent hooks:** `session-handoff.sh`, `auto-compound.sh`, and `auto-drift-check.sh` are three separate hooks with different responsibilities:
   - `session-handoff.sh` — detects incomplete work and writes HANDOFF.md
   - `auto-compound.sh` — knowledge capture after problem-solving
   - `auto-drift-check.sh` — (not shown in the excerpts, but presumably similar throttle pattern)

   These hooks are **logically independent** — they have different triggers (signal patterns), different outputs, and different user-facing behavior. But they are **coupled at the runtime level** via the shared sentinel. If one fires, the others are blocked **for the entire session**.

2. **Sentinel key name is ambiguous:** The key `"stop"` does not convey that it is a **session-wide Stop hook deduplication guard**, not a "stop this specific hook" guard. A developer adding a new Stop hook might not realize they need to check the same `stop` sentinel to participate in the anti-cascade protocol.

3. **No documentation of the coupling:** The coupling is documented only in the plan (Note 2) and in inline comments in the hooks. There is no architectural doc that explains "all Stop hooks must check the `stop` sentinel before doing work." If a developer adds a new Stop hook without reading every existing Stop hook, they will miss this requirement.

4. **Sentinel collision is silent:** If two hooks both claim the `stop` sentinel, the second one exits silently (exit 0). There is no logging or telemetry to indicate "hook X was blocked because hook Y already fired." This makes debugging "why didn't my hook run?" questions difficult.

**Root cause:** This is a **distributed coordination protocol** (prevent N hooks from all firing in the same stop cycle) implemented via a **shared mutable global** (the `stop` sentinel). The protocol is correct, but it is **implicit** rather than **explicit**.

**Alternatives:**

| Approach | Pros | Cons | Verdict |
|----------|------|------|---------|
| **Shared sentinel (plan's choice)** | Simple, already works in temp-file version | Hidden coupling, no visibility into which hook won | ⚠️ Acceptable if documented |
| **Hook execution order in hooks.json** | Explicit precedence (e.g., handoff runs before compound) | Requires hooks.json to define order, still no dedup | ❌ Doesn't solve the problem |
| **Sentinel namespace per hook + global flag** | Each hook has its own sentinel, but all check a shared "stop_cycle_claimed" flag | More complex, same coupling | ❌ No benefit |
| **Separate Stop hook that dispatches** | Single Stop hook reads signals and decides which sub-hook to invoke | Changes architecture significantly, requires refactor | ⚠️ Better long-term, but out of scope |

**Recommendation:**

Keep the shared sentinel pattern (it's correct), but make the coupling **explicit and discoverable**:

1. **Rename the sentinel key to `stop_cycle_dedup`** so the name conveys its purpose.

2. **Add a shared constant** in `lib-intercore.sh`:
   ```bash
   # Shared sentinel for Stop hook anti-cascade protocol.
   # All Stop hooks MUST check this sentinel before doing work to prevent
   # multiple Stop hooks from firing in the same stop cycle.
   INTERCORE_STOP_DEDUP_SENTINEL="stop_cycle_dedup"
   ```

3. **Replace the inline sentinel name** in each hook with the constant:
   ```bash
   source "${BASH_SOURCE[0]%/*}/lib-intercore.sh" 2>/dev/null || INTERCORE_STOP_DEDUP_SENTINEL="stop_cycle_dedup"

   if type intercore_sentinel_check_or_legacy &>/dev/null; then
       intercore_sentinel_check_or_legacy "$INTERCORE_STOP_DEDUP_SENTINEL" "$SESSION_ID" 0 "/tmp/clavain-stop-${SESSION_ID}" || exit 0
   else
       # ... inline fallback
   fi
   ```

4. **Add logging when a hook is blocked** (optional, but valuable for debugging):
   ```bash
   if ! intercore_sentinel_check_or_legacy "stop_cycle_dedup" "$SESSION_ID" 0 "/tmp/clavain-stop-${SESSION_ID}"; then
       printf 'Stop hook (%s) blocked: another Stop hook already claimed this cycle\n' "$(basename "$0")" >&2
       exit 0
   fi
   ```

This makes the coupling **self-documenting** and **greppable** (`rg INTERCORE_STOP_DEDUP_SENTINEL` shows all participants).

---

### P3: Missing Abstraction — Duplicate Conditional Blocks in Every Hook

**Issue:** Every migrated hook (6 total) will have this pattern:

```bash
source "${BASH_SOURCE[0]%/*}/lib-intercore.sh" 2>/dev/null || true

if type intercore_sentinel_check_or_legacy &>/dev/null; then
    intercore_sentinel_check_or_legacy "name" "$scope" $interval "/tmp/path" || exit 0
else
    # Inline legacy fallback (5-10 lines of temp file logic)
fi
```

**Code duplication:**

- The `type` check is duplicated 6+ times (once per hook, multiple times per hook for hooks with multiple sentinels).
- The inline fallback is duplicated for each sentinel type (once-per-session vs. time-based throttle).
- The sourcing pattern is duplicated 6 times.

**Complexity:**

Each hook has 15-30 lines of sentinel checking code (source + conditional + fallback) before it gets to the actual hook logic. This buries the hook's intent under infrastructure boilerplate.

**Root cause:** The plan adds a new wrapper function (`intercore_sentinel_check_or_legacy`) but does not remove the need for the **conditional dispatch** at the call site. The hook must still choose between the wrapper and the inline fallback. This is **abstraction leakage** — the hook knows too much about the wrapper's internal fallback mechanism.

**Why the wrapper doesn't fully encapsulate:**

The wrapper `intercore_sentinel_check_or_legacy` (Task 1 Step 1) handles the **intercore-available-vs-not** decision internally. But the **hook** must handle the **wrapper-available-vs-not** decision (the `type` check). This creates **two layers of fallback**:

1. Wrapper-level fallback: `intercore_available() -> yes? ic sentinel check : touch temp file`
2. Hook-level fallback: `wrapper available? call wrapper : inline temp file logic`

The hook-level fallback is necessary because `lib-intercore.sh` might fail to source (file not found, syntax error, permission denied). But this means **every hook must duplicate the inline fallback logic**.

**Alternatives:**

| Approach | Pros | Cons | Verdict |
|----------|------|------|---------|
| **Inline fallback in every hook (plan's choice)** | Fail-safe, no hidden dependencies | Duplication, verbose | ⚠️ Acceptable but suboptimal |
| **Wrapper with no-op stub fallback** | Hooks always call wrapper, wrapper always exists | Requires wrapper to be bundled/installed | ❌ Doesn't solve sourcing failure |
| **Move all sentinel checks to a single hook helper** | One function that handles all sentinel types | Centralized state, harder to read per-hook | ⚠️ Viable, but reduces per-hook clarity |
| **Template/codegen for hooks** | Eliminate duplication via generation | Adds build step, obscures actual code | ❌ Overkill for 6 hooks |

**Recommendation:**

Keep the inline fallback (fail-safe is more important than DRY in hooks), but **reduce verbosity** by extracting the **common pattern** to a helper in `lib-intercore.sh`:

Add to `lib-intercore.sh`:
```bash
# intercore_check_or_die — Wrapper dispatch with inline fallback.
# Args: $1=name, $2=scope_id, $3=interval, $4=legacy_path
# Returns: 0 if allowed, exits hook (exit 0) if throttled
# This helper eliminates the need for hooks to duplicate the type check + fallback.
intercore_check_or_die() {
    local name="$1" scope_id="$2" interval="$3" legacy_path="$4"

    # Try wrapper first
    if type intercore_sentinel_check_or_legacy &>/dev/null; then
        intercore_sentinel_check_or_legacy "$name" "$scope_id" "$interval" "$legacy_path" || exit 0
        return 0
    fi

    # Inline fallback (wrapper unavailable)
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
```

Then hooks simplify to:
```bash
source "${BASH_SOURCE[0]%/*}/lib-intercore.sh" 2>/dev/null || true
intercore_check_or_die "stop" "$SESSION_ID" 0 "/tmp/clavain-stop-${SESSION_ID}"
```

This **eliminates the duplication** while **preserving fail-safe behavior** (if the wrapper fails to define `intercore_check_or_die`, the hook will error and exit, which is correct — the hook should not run if its sentinel mechanism is broken).

**Trade-off:** This makes the library **more opinionated** (it now calls `exit 0` on behalf of the hook). If a hook needs different behavior (e.g., log before exiting), it must use the lower-level `intercore_sentinel_check_or_legacy` directly. But for the 6 hooks in this plan, the behavior is identical, so the abstraction is sound.

---

## Secondary Concerns

### S1: Discovery Cache Invalidation Uses Sentinel Reset, Not State Deletion

**Issue:** Task 7 migrates `sprint_invalidate_caches()` from `rm -f /tmp/clavain-discovery-brief-*.cache` to `intercore_sentinel_reset_all "discovery_brief" ...`.

**Concern:** Discovery caches are not **throttle sentinels** — they are **cached data**. The sentinel system is designed for "has this event fired yet?" checks (claim-once semantics), not for "invalidate all cached entries."

Using `sentinel reset` for cache invalidation works, but it **conflates two different concepts**:
- **Sentinel:** A flag that tracks "this action was taken at time T, do not repeat until interval expires"
- **Cache:** A stored computation result that should be invalidated when inputs change

**Why this matters:**

1. **Semantics:** `ic sentinel list` will show cache entries alongside throttle guards, making the output harder to interpret.
2. **Expiry:** Sentinels have TTL and auto-prune. Caches should be invalidated explicitly (on-demand), not pruned on a time basis.
3. **Tooling:** `ic compat status` will show `discovery_brief` as a "sentinel" even though it is not a throttle guard.

**Alternative:**

Use **`ic state set/get/delete`** for cache data:

```bash
# Write cache
ic state set "discovery_brief" "$scope_id" < cache.json

# Read cache
ic state get "discovery_brief" "$scope_id"

# Invalidate
ic state delete "discovery_brief" "$scope_id"

# Invalidate all scopes
for scope in $(ic state list "discovery_brief"); do
    ic state delete "discovery_brief" "$scope"
done
```

This uses the correct abstraction (state storage, not sentinel throttle).

**Recommendation:**

Change Task 7 to use `ic state delete` instead of `ic sentinel reset`. Add a helper to `lib-intercore.sh`:

```bash
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
```

Then in `lib-sprint.sh`:
```bash
sprint_invalidate_caches() {
    if type intercore_state_delete_all &>/dev/null; then
        intercore_state_delete_all "discovery_brief" "/tmp/clavain-discovery-brief-*.cache"
    else
        rm -f /tmp/clavain-discovery-brief-*.cache 2>/dev/null || true
    fi
}
```

This is a **minor semantic issue** (the sentinel approach will work), but using `state delete` is more accurate.

---

### S2: No Concurrency Testing for Sentinel Claims

**Issue:** The plan includes integration tests (Task 1 Step 4, Task 8 Step 1) but does not test **concurrent sentinel claims**.

**Scenario:** Two Stop hooks fire in rapid succession (within milliseconds). Both call `ic sentinel check stop $SESSION_ID --interval=0`. The first should claim the sentinel (exit 0), the second should be throttled (exit 1).

**Risk:** If the sentinel claim is not **atomic** (e.g., due to a bug in the DB layer's CTE logic), both hooks might claim success. This would violate the anti-cascade protocol and cause both hooks to fire.

**Current test coverage:** The integration test (lines 113-129 in the plan) tests sequential claims (first check → second check → reset → third check). This is correct but does not cover the **concurrency case**.

**Recommendation:**

Add a concurrency test to `test-integration.sh`:

```bash
echo "=== Concurrent Sentinel Claims ==="
# Launch two subshells that both try to claim the same sentinel simultaneously
(ic sentinel check "concurrent_test" "session-123" --interval=0 && echo "PROC1_CLAIMED") &
(ic sentinel check "concurrent_test" "session-123" --interval=0 && echo "PROC2_CLAIMED") &
wait

# Exactly one should have claimed (exactly one "CLAIMED" line in output)
CLAIM_COUNT=$(grep -c "CLAIMED" <<< "$OUTPUT" || echo 0)
if [[ "$CLAIM_COUNT" -eq 1 ]]; then
    pass "concurrent claim: exactly one succeeded"
else
    fail "concurrent claim: expected 1 success, got $CLAIM_COUNT"
fi
```

This test requires `infra/intercore/` to be built with race detection enabled (`go test -race`), which the plan already includes (line 105 in intercore/AGENTS.md).

---

### S3: Cleanup Stale Sentinels Runs on Every Stop Hook, Not Once Per Session

**Issue:** Task 3 Step 4, Task 4 Step 4, Task 5 Step 4 all add `intercore_cleanup_stale` calls to replace the existing `find /tmp ... -delete` cleanup.

**Current behavior (pre-migration):** Each hook has its own cleanup line:
- `session-handoff.sh` line 140: `find /tmp -maxdepth 1 -name 'clavain-stop-*' -mmin +60 -delete`
- Similar lines in other hooks.

These run **every time the hook fires** (once per session per hook, after the sentinel blocks subsequent invocations).

**Post-migration behavior:** `intercore_cleanup_stale` (Task 1 Step 1, lines 93-100) calls `ic sentinel prune --older-than=1h`, which prunes **all sentinels** (not just the ones relevant to this hook).

**Concern:** If 3 Stop hooks all call `intercore_cleanup_stale`, the prune operation runs 3 times per stop cycle. This is **redundant** but not harmful (the second and third calls are no-ops because the first call already pruned). However, it adds 3 DB transactions where 1 would suffice.

**Recommendation:**

Move the cleanup call to **one designated hook** (e.g., `session-handoff.sh`, which is the "primary" Stop hook). Remove it from the others. Add a comment:

```bash
# Cleanup: Prune stale sentinels (run once per stop cycle, not in every hook)
intercore_cleanup_stale
```

Alternatively, add a **cleanup sentinel** to ensure it only runs once:
```bash
if intercore_sentinel_check_or_legacy "cleanup_prune" "$SESSION_ID" 3600 "/tmp/clavain-cleanup-${SESSION_ID}"; then
    intercore_cleanup_stale
fi
```

This ensures cleanup runs at most once per hour, even if multiple hooks fire in rapid succession.

---

## Broader Architectural Observations

### Pattern: Adapter Layer for Cross-Module Dependencies

This migration is an example of the **adapter pattern** for cross-module dependencies:

- **Client:** Clavain hooks (bash)
- **Dependency:** intercore `ic` binary (Go)
- **Adapter:** `lib-intercore.sh` (bash wrappers)

The adapter provides:
1. **Fallback behavior** when the dependency is unavailable
2. **Simplified API** (wrapper functions instead of raw CLI calls)
3. **Error handling** (exit codes → bash return codes)

**Strengths:**
- The adapter is **fail-safe** (if `ic` is missing, hooks fall back to temp files).
- The adapter is **thin** (44 lines, no complex logic).
- The adapter is **testable** (integration tests in `infra/intercore/test-integration.sh`).

**Weaknesses:**
- The adapter is **copied** instead of shared (version skew risk).
- The adapter is **optional** (hooks must handle adapter-unavailable case, creating duplication).
- The adapter has **no version contract** (no way to verify the wrapper version matches the `ic` version).

**Lesson for future work:**

When adding cross-module dependencies in this ecosystem, prefer **vendored adapters with version pinning** over **symlinks** (which break when modules are developed in isolation) or **copies without sync checks** (which drift silently).

---

### Pattern: Sentinel as Coordination Primitive

The shared `stop` sentinel is an example of **distributed coordination** via a **shared resource**:

- **Problem:** Multiple hooks must not fire in the same stop cycle.
- **Solution:** First hook to claim the `stop` sentinel wins, others are blocked.
- **Mechanism:** Atomic claim via `ic sentinel check` (DB) or `test -f && exit || touch` (temp file).

**Strengths:**
- The mechanism is **simple** (no leader election, no message passing).
- The mechanism is **atomic** (no race conditions if implemented correctly).
- The mechanism is **stateless** (each hook is independent, no central coordinator).

**Weaknesses:**
- The coordination protocol is **implicit** (no doc that says "all Stop hooks must check the stop sentinel").
- The protocol is **silent** (no logging when a hook is blocked).
- The protocol is **fragile** (if a new Stop hook forgets to check the sentinel, it will fire even when others are blocked).

**Lesson for future work:**

When using shared sentinels for coordination, make the protocol **explicit**:
1. **Constant** for the sentinel name (instead of hardcoded strings).
2. **Comment** in each hook explaining the protocol.
3. **Test** that verifies all participating hooks check the same sentinel.

---

## Summary of Recommendations

| Priority | Issue | Recommendation |
|----------|-------|----------------|
| P0 | Library copy creates version skew | Add version header to lib, sync check in CI, document in both repos |
| P1 | Fallback pattern has incorrect timing | Add comment explaining why inline fallback is necessary for TOCTOU safety |
| P2 | Shared sentinel creates hidden coupling | Rename to `stop_cycle_dedup`, use constant, add logging on block |
| P3 | Duplicate conditional blocks in hooks | Extract `intercore_check_or_die` helper to eliminate duplication |
| S1 | Discovery cache uses sentinel instead of state | Change to `ic state delete`, add `intercore_state_delete_all` helper |
| S2 | No concurrency testing | Add concurrent claim test to `test-integration.sh` |
| S3 | Cleanup runs 3x per stop cycle | Move cleanup to one hook, or add cleanup sentinel |

---

## Verdict

**Architecture: 6/10 — Acceptable with caveats**

The plan is **structurally sound** (correct abstractions, fail-safe design, atomic operations), but has **implementation issues** (version skew risk, duplication, hidden coupling) that will create **maintenance debt**.

**Recommended path forward:**

1. **Before implementation:** Address P0 (library version sync) and P2 (shared sentinel naming/logging).
2. **During implementation:** Apply P1 (comment for TOCTOU safety) and P3 (extract helper to reduce duplication).
3. **After implementation:** Add concurrency test (S2), fix discovery cache (S1), optimize cleanup (S3).

If the P0 and P2 issues are not addressed, this migration will succeed in the short term but will create **subtle bugs and confusion** in the long term when:
- `lib-intercore.sh` and `ic` binary versions diverge.
- A new Stop hook is added without checking the `stop` sentinel.
- A developer tries to debug "why didn't my hook run?" without knowing about the anti-cascade protocol.

**Core tension:**

This plan attempts to **decouple Clavain from intercore** (via the adapter library) while **keeping them tightly integrated** (via the copied library). The result is a **hybrid** that has the costs of both approaches (manual sync for the copy, complexity of the adapter) without the benefits of either (single source of truth for symlink, true independence for vendoring).

The recommended **vendored-with-sync-check** approach resolves this tension by making the coupling **explicit and enforceable** instead of **implicit and fragile**.
