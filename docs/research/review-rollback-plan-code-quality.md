# Code Quality Review: 2026-02-20-intercore-rollback-recovery.md

**Reviewer:** Flux-drive Quality & Style Reviewer
**Date:** 2026-02-20
**Target:** `/root/projects/Interverse/docs/plans/2026-02-20-intercore-rollback-recovery.md`
**Codebase:** `/root/projects/Interverse/infra/intercore/`
**Go version:** 1.22, `modernc.org/sqlite`

---

## Summary

The plan is well-structured and largely idiomatic. Four concerns merit attention before implementation: a logic bug in `ChainPhasesBetween` that inverts the semantic meaning of the output, redundant terminal-status checks spread across the call chain, use of `map[string]interface{}` where typed structs would be safer and are already established in the codebase for similar output, and a test for `MarkArtifactsRolledBack` that couples itself to the phase store via a cross-package instantiation pattern that differs from how the runtrack test suite currently achieves FK satisfaction. None of these are blockers, but the `ChainPhasesBetween` logic issue will produce a silent correctness bug in production.

---

## Finding 1 — CRITICAL: `ChainPhasesBetween` semantic inversion

**Location:** Task 2, Step 3 — `internal/phase/phase.go`

**Severity:** Critical (silent correctness bug)

The function is documented as "returns the phases strictly between from and to (exclusive on both ends)" but its comment block contradicts itself and the implementation computes a range from `fromIdx+1` to `toIdx`, which means when called as:

```go
rolledBack := ChainPhasesBetween(chain, targetPhase, fromPhase)
```

with `targetPhase="brainstorm"` and `fromPhase="planned"`, the result will be `["brainstorm-reviewed", "strategized", "planned"]`. This is the desired set — phases that get rolled back. However, the function name and docstring say `from` is the earlier boundary and `to` is the later boundary. The naming is flipped relative to how callers pass arguments: `ChainPhasesBetween(chain, targetPhase, fromPhase)`.

The test case in `TestChainPhasesBetween` confirms this:
```go
{"a", "d", []string{"b", "c", "d"}},  // from=a, to=d → phases a+1..d
```

And the machine test `TestRollback_RolledBackPhases` verifies 3 phases are returned for `targetPhase=brainstorm`, `currentPhase=planned`. This checks out arithmetically, but the naming inversion means:

1. A future reader of `ChainPhasesBetween(chain, targetPhase, fromPhase)` at the call site will need to mentally invert the arg order to understand what they are getting.
2. If anyone calls the function with natural argument order `(chain, fromPhase, targetPhase)` they silently get `nil` (backward check returns nil).
3. The docstring says "exclusive on both ends" but the implementation is inclusive of `to`.

**Recommendation:** Rename to `ChainPhasesBetweenExclusive` and `ChainPhasesBetweenInclusive` to make the boundary contract explicit, OR flip the parameter names to match the actual usage: `func ChainPhasesAfterUntilInclusive(chain []string, after, until string)`. At minimum, update the docstring to correctly state the range is `(from, to]` not `(from, to)`, and add a comment at the call site explaining the arg inversion.

The simplest safe fix: rename the params to match the call convention:

```go
// ChainPhasesBetween returns the phases strictly after `before` up to and
// including `upTo`, in forward chain order. Returns nil if `before` is not
// before `upTo` in the chain, or if either is not found.
// Call as: ChainPhasesBetween(chain, targetPhase, currentPhase)
// to get all phases that will be rolled back.
func ChainPhasesBetween(chain []string, before, upTo string) []string {
```

Add a test case that inverts the natural reading to make the contract explicit:
```go
{"d", "a", nil},  // upTo before before = nil (not: "phases from d to a")
```

This already exists in the plan but the test passes `("a", "d")` which is the `before=a, upTo=d` case and does return `["b","c","d"]` — fine. The issue is purely the docstring and usage-site readability.

---

## Finding 2 — MEDIUM: Redundant terminal-status check in `RollbackPhase`

**Location:** Task 3, Step 3 — `internal/phase/store.go`

**Severity:** Medium (violation of single-responsibility, creates maintenance hazard)

The plan proposes `RollbackPhase` (the Store method) performs its own `run.Status == StatusCancelled || run.Status == StatusFailed` check, and then the `Rollback` machine function in Task 4 also checks `run.Status == StatusCancelled || run.Status == StatusFailed` before calling `store.RollbackPhase`. This duplicates the guard in the call chain.

Compare to how `UpdatePhase` works in the existing codebase: `UpdatePhase` does no status-awareness at all — it does an optimistic `WHERE id = ? AND phase = ?` update and returns `ErrStalePhase` or `ErrNotFound`. The terminal-status rejection is done by `Advance` (the machine function) before calling the store. The store layer handles data integrity; the machine layer handles business rules.

The proposed `RollbackPhase` breaks this pattern by:
1. Fetching the full run (an extra SELECT query) before the UPDATE
2. Duplicating status checks that the machine already performs

This is not a serious bug (double-checking is conservative), but it adds a round-trip query to every rollback and creates a divergence from the established store/machine split. The existing `SkipPhase` store method does guard terminal status — so there is some precedent — but `SkipPhase` cannot delegate to a higher layer since it has no machine wrapper. `RollbackPhase` will always be called from `Rollback()`.

**Recommendation:** Remove the status-check and the preliminary `Get` from `RollbackPhase`. Replace with a direct `UPDATE ... WHERE id = ?` that does NOT condition on `status` (the machine handles that). Return `ErrNotFound` only if `RowsAffected == 0`. This keeps the store method data-only, avoids the extra SELECT, and matches `UpdatePhase`'s pattern:

```go
func (s *Store) RollbackPhase(ctx context.Context, id, targetPhase string) error {
    now := time.Now().Unix()
    result, err := s.db.ExecContext(ctx, `
        UPDATE runs SET phase = ?, status = 'active', updated_at = ?, completed_at = NULL
        WHERE id = ?`,
        targetPhase, now, id,
    )
    if err != nil {
        return fmt.Errorf("rollback phase: %w", err)
    }
    n, err := result.RowsAffected()
    if err != nil {
        return fmt.Errorf("rollback phase: %w", err)
    }
    if n == 0 {
        return ErrNotFound
    }
    return nil
}
```

Note: this also simplifies the signature — the `currentPhase` parameter is not used in the UPDATE (it is already verified by the machine before calling). Removing it eliminates a misleading unused parameter.

The test `TestRollbackPhase_CompletedRun` verifies the `completed_at = NULL` revert — that test is valid and should be kept.

**Signature adjustment (cascading):** If `currentPhase` is dropped from `RollbackPhase`, update `Rollback()` in machine.go to call `store.RollbackPhase(ctx, runID, targetPhase)` instead of `store.RollbackPhase(ctx, runID, fromPhase, targetPhase)`.

---

## Finding 3 — MEDIUM: `map[string]interface{}` for CLI output — use typed structs

**Location:** Task 6, `cmdRunRollbackWorkflow` and `cmdRunRollbackCode`

**Severity:** Medium (inconsistency, type-safety loss, JSON key stability risk)

The plan uses `map[string]interface{}` for constructing JSON output in two places:

```go
// dry-run output
output := map[string]interface{}{
    "dry_run":            true,
    "from_phase":        run.Phase,
    "to_phase":          toPhase,
    "rolled_back_phases": rolledBackPhases,
}

// rollback result output
output := map[string]interface{}{
    "from_phase":            result.FromPhase,
    "to_phase":              result.ToPhase,
    "rolled_back_phases":    result.RolledBackPhases,
    "reason":                result.Reason,
    "cancelled_dispatches":  cancelledDispatches,
    "marked_artifacts":      markedArtifacts,
    "failed_agents":         failedAgents,
}
```

The existing codebase uses typed structs with `json:` tags for all structured CLI output — for example in `cmd/ic/run.go` (the run status output uses typed structs). Map-based JSON has three practical drawbacks here:

1. Key name typos (`"from_phase"` vs `"from-phase"`) are invisible at compile time — bash scripts that parse `jq '.from_phase'` will silently get `null` if a key is mistyped.
2. Go's `encoding/json` serializes `map[string]interface{}` with keys in sorted order (alphabetical), not declaration order. This is rarely a problem but can surprise when reading raw output.
3. The `RollbackResult` struct already exists (defined in Task 4's machine.go addition). The CLI output nearly mirrors it — defining a separate output struct costs four lines and eliminates the map.

The `CodeRollbackEntry` struct in Task 7 is done correctly with `json:` tags and slice output. That approach should be used for the workflow output too.

**Recommendation:** Define a CLI output struct in `cmd/ic/run.go`:

```go
type rollbackOutput struct {
    FromPhase           string   `json:"from_phase"`
    ToPhase             string   `json:"to_phase"`
    RolledBackPhases    []string `json:"rolled_back_phases"`
    Reason              string   `json:"reason,omitempty"`
    CancelledDispatches int64    `json:"cancelled_dispatches"`
    MarkedArtifacts     int64    `json:"marked_artifacts"`
    FailedAgents        int64    `json:"failed_agents"`
}

type rollbackDryRunOutput struct {
    DryRun          bool     `json:"dry_run"`
    FromPhase       string   `json:"from_phase"`
    ToPhase         string   `json:"to_phase"`
    RolledBackPhases []string `json:"rolled_back_phases"`
}
```

This matches the pattern in the existing codebase for other structured output, eliminates the `interface{}` import concern, and makes key names auditable at compile time.

Note: In Go 1.18+, `any` is the idiomatic alias for `interface{}`. If the codebase has not yet adopted `any`, keep the existing style. Checking the existing source — `store.go` in runtrack uses `[]interface{}` for args — so the project has not adopted `any`. No action needed on that front, but the map approach remains the concern.

---

## Finding 4 — MEDIUM: Task 5 test uses cross-package phase store — breaks from runtrack test pattern

**Location:** Task 5, Step 1 — `internal/runtrack/store_test.go`

**Severity:** Medium (coupling, test fragility)

The proposed test creates a `phase.Store` inside `runtrack/store_test.go` to satisfy the foreign key constraint:

```go
pStore := phase.New(store.DB())
runID, err := pStore.Create(ctx, &phase.Run{ProjectDir: "/tmp/test", Goal: "test"})
```

The existing `runtrack/store_test.go` uses a different, already-established pattern: a `createHelperRun` helper that inserts a run row directly via raw SQL against `d.SqlDB()`:

```go
func createHelperRun(t *testing.T, d *db.DB, id string) {
    t.Helper()
    _, err := d.SqlDB().Exec(`
        INSERT INTO runs (id, project_dir, goal, status, phase, complexity,
            force_full, auto_advance, created_at, updated_at)
        VALUES (?, '/tmp/test', 'test goal', 'active', 'brainstorm', 3, 0, 1, ?, ?)`,
        id, time.Now().Unix(), time.Now().Unix(),
    )
    ...
}
```

Using `phase.New(store.DB())` instead of `createHelperRun` introduces a cross-package import (`phase`) into the `runtrack` test file, creating a circular-import-like coupling concern (the packages are not circular since `runtrack` does not import `phase`, but the test file now does). More critically, the proposed test signature for `setupTestStore` returns only `*Store`, but the call `store.DB()` implies a `DB()` accessor method that does not exist on `runtrack.Store` — the current `setupTestStore` returns `(*Store, *db.DB)` and the raw `*db.DB` is passed to `createHelperRun`. This will not compile as written.

**Recommendation:** Use the existing `createHelperRun` pattern instead:

```go
func TestMarkArtifactsRolledBack(t *testing.T) {
    store, d := setupTestStore(t)
    ctx := context.Background()

    createHelperRun(t, d, "run-rollback-test")
    runID := "run-rollback-test"

    _, err = store.AddArtifact(ctx, &Artifact{RunID: runID, Phase: "brainstorm", Path: "/tmp/a.md", Type: "file"})
    ...
```

This keeps the runtrack test package self-contained, avoids importing phase, and matches the established helper pattern. The same fix applies to `TestCancelAgentsByPhases` and `TestListArtifactsWithDispatches`.

Additionally, note that `TestCancelAgentsByPhases` in the plan does not test `CancelAgentsByPhases` — it tests `FailAgentsByRun`. The test name should be `TestFailAgentsByRun` to match the function being tested. Misnaming tests makes coverage reports misleading.

---

## Finding 5 — LOW: Migration guard condition off-by-one

**Location:** Task 1, Step 5 — `internal/db/db.go`

**Severity:** Low (logic inconsistency with existing migration pattern)

The proposed v7→v8 migration guard is:

```go
if currentVersion >= 7 {
    // apply v7→v8 migration
}
```

The existing v5→v6 migration guard is:

```go
if currentVersion >= 5 {
    // apply v5→v6 migration
}
```

This reads correctly: "if the DB is at v5 or later, apply the v5→v6 delta." But notice that the migration function returns early at line 132-134:

```go
if currentVersion >= currentSchemaVersion {
    return nil // already migrated
}
```

When `currentSchemaVersion` becomes 8, a v8 DB returns early before reaching the migration block. A v7 DB has `currentVersion == 7`, which satisfies `>= 7`, so the block runs — correct. A v5 DB also satisfies `>= 7`? No — v5 is `currentVersion == 5`, which does NOT satisfy `>= 7`. So a v5 DB jumping to v8 would skip the v7→v8 block.

This is the same logic issue present in the existing migration for v5→v6: a DB at v0-v4 skips v5→v6 and jumps straight to the schema DDL apply. The existing code is consistent in this (potentially incomplete) pattern. The plan follows the same pattern, so there is no regression. However, both the existing and proposed migration blocks only apply their delta if the DB is AT or ABOVE the source version, meaning a very old DB jumping multiple schema versions may skip intermediate deltas and rely on the full schema DDL to compensate.

This is not a new problem introduced by this plan, but it is worth flagging as a known fragility in the migration architecture. No immediate action required — document the assumption: "the full schema DDL plus the guard-protected ALTER statements together get any DB from v0 to current."

---

## Finding 6 — LOW: `CancelByRunAndPhases` silently ignores the `phases` parameter

**Location:** Task 5, Step 8 — `internal/dispatch/dispatch.go`

**Severity:** Low (API contract mismatch — the parameter is a lie)

The function signature is:

```go
func (s *Store) CancelByRunAndPhases(ctx context.Context, runID string, phases []string) (int64, error)
```

But the implementation cancels ALL non-terminal dispatches for the run regardless of the `phases` argument:

```go
result, err := s.db.ExecContext(ctx, `
    UPDATE dispatches SET status = ?, completed_at = ?
    WHERE scope_id = ? AND status NOT IN ('completed', 'failed', 'cancelled', 'timeout')`,
    StatusCancelled, now, runID,
)
```

The `phases` parameter is never used. The comment in the implementation acknowledges this ("Dispatches don't have a phase column") but the function signature still accepts it. This is misleading.

Two options:

**Option A:** Remove the `phases` parameter and rename the function to `CancelActiveByRun(ctx context.Context, runID string)`. Update the call site in `cmdRunRollbackWorkflow`. The caller already has `result.RolledBackPhases` but does not need to pass it to this function. This is the honest API.

**Option B:** Keep the signature but add `_ = phases` with a comment explaining the dispatch table has no phase column, so all active dispatches for the run are cancelled. This preserves the illusion of phase-scoping for future implementation.

Option A is strongly preferred. Signatures that accept unused parameters create confusion and make code harder to audit. Given that this is an internal package (not a public API), refactoring the call site is cheap.

---

## Finding 7 — LOW: Integration test uses `grep -oP` (Perl regex) — portability break

**Location:** Task 8, Step 1 — `test-integration.sh`

**Severity:** Low (portability)

The proposed integration test extracts the run ID with:

```bash
ROLL_ID=$(./ic run create --project=. --goal="test rollback" | grep -oP '"id":\s*"\K[^"]+')
```

`grep -oP` uses Perl-compatible regular expressions, which is not available on macOS (where `grep` is BSD grep) or in POSIX-only environments. The existing `test-integration.sh` does not use `grep -oP` — it captures the whole JSON line via capturing `ic run create` which outputs just the ID (not JSON), based on `RUN_ID=$(ic run create ...)` without a grep at all.

Looking at the existing integration test:
```bash
RUN_ID=$(ic run create --project="$TEST_DIR" --goal="Integration test run" --complexity=3 --db="$TEST_DB")
```

`ic run create` appears to output only the run ID (8 chars), not a JSON blob. The `grep -oP` approach implies the rollback plan was written assuming JSON output from `ic run create`, but the existing behavior is plain ID output.

**Recommendation:** Match the existing pattern — capture the ID directly without grep:

```bash
ROLL_ID=$(./ic run create --project=. --goal="test rollback" --db="$TEST_DB")
```

Also: the rollback integration test blocks use `./ic` but the existing test defines an `ic()` shell function that calls `"$IC_BIN" "$@"` and uses `--db="$TEST_DB"` throughout. The new tests should use the `ic` function alias and pass `--db="$TEST_DB"` consistently.

---

## Finding 8 — LOW: Bash wrapper silently swallows stderr

**Location:** Task 9, Step 1 — `lib-intercore.sh`

**Severity:** Low (diagnostic information loss)

The proposed rollback wrappers suppress stderr with `2>/dev/null`:

```bash
intercore_run_rollback() {
    ...
    "$INTERCORE_BIN" "${args[@]}" ${INTERCORE_DB:+--db="$INTERCORE_DB"} 2>/dev/null
}
```

Looking at the existing wrappers in `lib-intercore.sh`:

```bash
intercore_run_skip() {
    ...
    "$INTERCORE_BIN" "${args[@]}" ${INTERCORE_DB:+--db="$INTERCORE_DB"} 2>/dev/null
}

intercore_run_tokens() {
    ...
    "$INTERCORE_BIN" run tokens "$run_id" --json ${INTERCORE_DB:+--db="$INTERCORE_DB"} 2>/dev/null
}
```

The existing pattern DOES suppress stderr, so `2>/dev/null` is consistent. No change needed. This is not a deviation — the fail-safe philosophy of the wrapper library (callers check return codes, not error text) justifies stderr suppression. This finding is informational only.

---

## Finding 9 — LOW: `Rollback` machine function fetches run twice

**Location:** Task 4, Step 3 — `internal/phase/machine.go`

**Severity:** Low (minor inefficiency)

The proposed `Rollback` function:
1. Calls `store.Get(ctx, runID)` to check status and compute `fromPhase`
2. Then calls `store.RollbackPhase(ctx, runID, fromPhase, targetPhase)` which (per the plan) also calls `store.Get(ctx, runID)` internally

If Finding 2's recommendation is adopted (removing the inner Get from `RollbackPhase`), this becomes moot — there is only one Get in the machine function. If the plan is implemented as written (with the inner Get), there are two round-trips to the DB for what is logically one operation.

This is tolerable given SQLite's WAL mode and the single-connection constraint, but it is worth noting. Adopting Finding 2's recommendation eliminates this automatically.

---

## Finding 10 — INFORMATIONAL: `Rollback` correctly does NOT use optimistic concurrency

**Location:** Task 4, Step 3 and Task 3 comment — "unlike UpdatePhase"

**Severity:** Informational (design validation)

The plan explicitly notes that rollback skips optimistic concurrency (the `WHERE phase = expectedPhase` guard in `UpdatePhase`). This is the correct design choice — rollback is an authoritative operator action, not an automated transition that could race against another agent. The comment "rollback is authoritative" in the docstring is sufficient justification.

The test `TestRollbackPhase_NotBehind` validates the correctness guard (`ErrInvalidRollback` for forward targets), which is the meaningful invariant to enforce. No race guard is needed because rollback is expected to be an infrequent, human-initiated operation.

---

## Finding 11 — INFORMATIONAL: Test setup naming inconsistency between packages

**Location:** Task 3 and Task 4 test code

**Severity:** Informational (minor)

The plan uses `setupTestStore(t)` in both `store_test.go` (Task 3) and `machine_test.go` (Task 4). However, the existing `machine_test.go` uses `setupMachineTest(t)` (which returns `(*Store, *runtrack.Store, *sql.DB, context.Context)`) while the existing `store_test.go` uses `setupTestStore(t)` (which returns `*Store`).

The new machine tests in Task 4 call `setupTestStore(t)` and then call `store.UpdatePhase(ctx, id, ...)` directly — but `UpdatePhase` exists on the store, so this works. However, this creates two different setup helper names in `machine_test.go` (the existing `setupMachineTest` and the new usages of `setupTestStore`). They produce different return types and the tests need to be careful which one they use.

**Recommendation:** Use `setupMachineTest(t)` (the existing helper) in `machine_test.go` tests, and extract `store` from the tuple: `store, _, _, ctx := setupMachineTest(t)`. The plan's tests use `store := setupTestStore(t)` in machine_test.go, which works only if `setupTestStore` is accessible (it is not exported from `store_test.go` within the same package — it is in the same `package phase`, so it is visible). This is fine, but using the existing `setupMachineTest` is more consistent with the established pattern in that file.

---

## Summary Table

| # | Severity | Location | Issue |
|---|----------|----------|-------|
| 1 | Critical | `phase/phase.go` — `ChainPhasesBetween` | Docstring says exclusive on both ends; implementation is `(from, upTo]`; argument inversion at call site risks future misuse |
| 2 | Medium | `phase/store.go` — `RollbackPhase` | Redundant double-Get; status-check belongs in machine, not store; unused `currentPhase` parameter |
| 3 | Medium | `cmd/ic/run.go` — CLI output | `map[string]interface{}` should be typed output structs matching codebase pattern |
| 4 | Medium | `runtrack/store_test.go` | Cross-package phase store usage; `store.DB()` method does not exist; use existing `createHelperRun` pattern; test name mismatch |
| 5 | Low | `db/db.go` — migration | Guard `>= 7` may skip delta for very old DBs; pre-existing architectural assumption, not a regression |
| 6 | Low | `dispatch/dispatch.go` — `CancelByRunAndPhases` | `phases` param is accepted but never used; rename to `CancelActiveByRun` |
| 7 | Low | `test-integration.sh` | `grep -oP` not portable; `ic run create` outputs plain ID, not JSON blob requiring grep |
| 8 | Low | `lib-intercore.sh` | `2>/dev/null` on stderr is consistent with existing pattern — informational only |
| 9 | Low | `phase/machine.go` — `Rollback` | Double-Get eliminated if Finding 2 adopted |
| 10 | Info | `Rollback` design | Correct to skip optimistic concurrency for authoritative rollback |
| 11 | Info | `machine_test.go` | Use `setupMachineTest` rather than `setupTestStore` for consistency |

---

## Priority Actions Before Implementation

1. **Fix `ChainPhasesBetween` docstring** to accurately describe the `(before, upTo]` contract, and add a comment at the call site in `Rollback()` explaining the argument order. (Finding 1)
2. **Remove `currentPhase` param and inner Get from `RollbackPhase`** — delegate status checking entirely to the machine layer. (Finding 2)
3. **Replace `map[string]interface{}` with typed output structs** for dry-run and workflow rollback CLI output. (Finding 3)
4. **Fix `TestMarkArtifactsRolledBack`** to use `createHelperRun(t, d, "run-id")` instead of `phase.New(store.DB())`. (Finding 4)
5. **Rename `CancelByRunAndPhases` to `CancelActiveByRun`** and drop the unused `phases` parameter. (Finding 6)
6. **Fix integration test ID extraction** to use plain capture without `grep -oP`, consistent with existing test pattern. (Finding 7)
