# Correctness Review: Intercore Rollback and Recovery Plan

**Reviewer:** Julik (Flux-drive Correctness Reviewer)
**Date:** 2026-02-20
**Target:** `docs/plans/2026-02-20-intercore-rollback-recovery.md`
**Source files reviewed:**
- `/root/projects/Interverse/infra/intercore/internal/phase/store.go`
- `/root/projects/Interverse/infra/intercore/internal/phase/machine.go`
- `/root/projects/Interverse/infra/intercore/internal/phase/phase.go`
- `/root/projects/Interverse/infra/intercore/internal/phase/errors.go`
- `/root/projects/Interverse/infra/intercore/internal/phase/gate.go`
- `/root/projects/Interverse/infra/intercore/internal/runtrack/store.go`
- `/root/projects/Interverse/infra/intercore/internal/runtrack/runtrack.go`
- `/root/projects/Interverse/infra/intercore/internal/dispatch/dispatch.go`
- `/root/projects/Interverse/infra/intercore/internal/db/db.go`
- `/root/projects/Interverse/infra/intercore/internal/db/schema.sql`
- `/root/projects/Interverse/infra/intercore/internal/event/store.go`
- `/root/projects/Interverse/infra/intercore/internal/event/event.go`
- `/root/projects/Interverse/infra/intercore/internal/event/handler_spawn.go`
- `/root/projects/Interverse/infra/intercore/cmd/ic/run.go`

---

## Established Invariants

These are the invariants that the existing codebase enforces. Any change must preserve them.

1. **Optimistic concurrency on phase transitions.** `UpdatePhase()` uses `WHERE id = ? AND phase = ?`. Two concurrent `Advance()` calls cannot both succeed -- the second gets `ErrStalePhase`.

2. **Terminal status is a one-way door.** `StatusCancelled` and `StatusFailed` are terminal. `StatusCompleted` is terminal. No existing code path reverts a terminal status. `Advance()` rejects terminal runs via `ErrTerminalRun`.

3. **`completed_at` is set exactly once,** when `UpdateStatus()` is called with a terminal status. It uses `COALESCE(?, completed_at)` -- once set, it sticks (unless raw SQL overrides it).

4. **Event bus consumers are at-least-once and cursor-based.** Consumers track dual high-water marks. They expect monotonically increasing event IDs per table. Events are never deleted.

5. **`SetMaxOpenConns(1)` on SQLite.** Only one connection is open at a time. This serializes all SQL operations within a single process. Cross-process concurrency relies on SQLite's file-level locking and `busy_timeout`.

6. **Gates count artifacts without status filtering.** `CountArtifacts()` (line 279 in `runtrack/store.go`) uses `COUNT(*) FROM run_artifacts WHERE run_id = ? AND phase = ?` -- no `WHERE status = 'active'` filter.

7. **`AddArtifact()` omits the `status` column.** It inserts 8 named columns. After schema v8 adds a NOT NULL DEFAULT 'active' `status` column, this INSERT must still work because of the DEFAULT.

8. **`ListArtifacts()` scans exactly 8 columns.** It will break on schema v8 unless updated.

---

## Findings

### FINDING 1 -- CRITICAL: Concurrent Rollback vs. Advance Race (Missing Optimistic Concurrency)

**Severity:** CRITICAL
**Affected code:** Task 3, `RollbackPhase()` (plan lines 368-418)

The plan's `RollbackPhase()` uses:

```sql
UPDATE runs SET phase = ?, status = 'active', updated_at = ?, completed_at = NULL
WHERE id = ?
```

This has **no `WHERE phase = ?` guard**. Meanwhile, `Advance()` calls `UpdatePhase()` which uses:

```sql
UPDATE runs SET phase = ?, updated_at = ?
WHERE id = ? AND phase = ?
```

The plan's comment says "rollback is an authoritative operation" and deliberately skips optimistic concurrency. This is a design choice, not a bug per se, but it creates a concrete race.

**Failure interleaving:**

1. Process A calls `Rollback(ctx, store, runID, "brainstorm", ...)`. At plan line 607, it reads the run: `fromPhase = "strategized"`.
2. Process B calls `Advance(ctx, store, runID, ...)`. It reads the run: `fromPhase = "strategized"`, computes `toPhase = "planned"`.
3. Process B executes `UpdatePhase(ctx, id, "strategized", "planned")` -- succeeds, run is now `planned`.
4. Process A executes `RollbackPhase(ctx, id, "strategized", "brainstorm")` -- the UPDATE has no `WHERE phase = ?`, so it succeeds. Run is now `brainstorm`.
5. Process B records an advance event: "strategized -> planned". Process A records a rollback event: "strategized -> brainstorm".
6. The audit trail now shows: `advance(strategized->planned)` followed by `rollback(strategized->brainstorm)`. But the rollback's `fromPhase` was stale -- the actual transition was `planned->brainstorm`. The audit trail is wrong.

**Impact:** The audit trail records a lie. The `fromPhase` in the rollback event does not match what was actually in the DB at the moment of the UPDATE. Any event bus consumer replaying the trail will compute a different state than what the DB contains.

**Also note:** Because `Rollback()` reads the run first (line 607, `store.Get`) and then later does `store.RollbackPhase()`, there is a TOCTOU gap. Between the read and the write, any number of advances could happen.

**Fix:** Add a `WHERE phase = currentPhase` guard to `RollbackPhase()`, just like `UpdatePhase()` does. Return `ErrStalePhase` if 0 rows affected. The caller (the `Rollback` machine function) should retry or fail.

```go
result, err := s.db.ExecContext(ctx, `
    UPDATE runs SET phase = ?, status = 'active', updated_at = ?, completed_at = NULL
    WHERE id = ? AND phase = ?`,
    targetPhase, now, id, currentPhase,
)
```

If the argument is "rollback should win over advance", then the fix is to use a serializable transaction that reads-then-writes atomically. But the simpler and more consistent fix is optimistic concurrency, matching the existing pattern.

---

### FINDING 2 -- HIGH: `completed_at = NULL` Reversion Without Downstream Audit

**Severity:** HIGH
**Affected code:** Task 3, `RollbackPhase()` (plan line 403)

The `RollbackPhase()` UPDATE unconditionally sets `completed_at = NULL`. This violates invariant 3 ("completed_at is set exactly once").

**Concrete concern:** Any downstream system that has cached `completed_at` (e.g., an event bus consumer that saw the `StatusCompleted` transition and stored the completion timestamp) will now have stale data. The run will appear to have never been completed.

**More specifically:** The `UpdateStatus()` method (store.go line 162-185) sets `completed_at` using `COALESCE(?, completed_at)`, which preserves the first non-NULL value. But `RollbackPhase()` blows it away with `completed_at = NULL` via a direct UPDATE. These two methods have incompatible assumptions about whether `completed_at` can be cleared.

**Also:** The event bus `dispatch_events` table uses `completed_at` on dispatches (not runs), but the conceptual issue stands: completed -> active is a state machine edge that does not exist today. The plan adds it, but the plan does not update `IsTerminalStatus()` to account for the fact that "completed" is no longer truly terminal when rollback exists.

**Fix:**
1. Document explicitly that rollback creates a `completed -> active` transition.
2. Consider recording a dedicated `completed_at_cleared` timestamp or keeping the original `completed_at` in a separate field for audit purposes.
3. Audit all callers of `IsTerminalStatus()`. Today it returns true for "completed" -- after this change, "completed" is only terminal if no rollback has been performed. Either change `IsTerminalStatus()` semantics or accept the semantic oddity.

---

### FINDING 3 -- HIGH: ListArtifacts Column Count Mismatch (Will Break Existing Callers)

**Severity:** HIGH
**Affected code:** Task 5, Step 5 (plan lines 796-815) and existing code at `runtrack/store.go` line 236-274

The plan adds a `status` column to `run_artifacts` (schema v8). The plan says to update `ListArtifacts` to scan 9 columns (adding `status`). However, the plan's test in Step 1 (line 714) calls `ListArtifacts()` and checks `a.Status`.

**The problem:** The existing `AddArtifact()` at `runtrack/store.go` line 220-225 does:

```go
INSERT INTO run_artifacts (
    id, run_id, phase, path, type, content_hash, dispatch_id, created_at
) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
```

This does NOT include `status`. After the schema migration adds `status TEXT NOT NULL DEFAULT 'active'`, the INSERT will still work because of the DEFAULT. This part is fine.

**But:** The `ListArtifacts()` SELECT at lines 241-247 currently selects 8 columns:
```sql
SELECT id, run_id, phase, path, type, content_hash, dispatch_id, created_at
```

The plan says to change this to 9 columns. The Scan at lines 263-266 expects exactly as many columns as the SELECT returns. If the schema migration (Task 1) deploys before the Go binary is rebuilt (Task 5), the old binary's ListArtifacts will work fine because it only SELECTs named columns, not `SELECT *`. So there is no runtime break from the schema migration alone.

**The real risk:** The plan modifies the `Artifact` struct to add a `Status *string` field and updates the Scan. But the `CountArtifacts()` gate method (line 279) does `COUNT(*)`. After rollback marks artifacts as `rolled_back`, CountArtifacts still counts them. This means:

**Gate bypass after rollback:** A run is at phase "brainstorm", has artifacts from a prior cycle that were marked `rolled_back`, then tries to advance. The `artifact_exists` gate checks `CountArtifacts()` which counts `rolled_back` artifacts too. The gate passes on stale data.

**Fix:** Either:
- (a) Update `CountArtifacts()` to filter `WHERE status = 'active'` (or `WHERE status != 'rolled_back'`), or
- (b) Accept that rolled-back artifacts still satisfy gates (document this as intentional).

Option (a) is the correct choice because the whole point of marking artifacts as rolled back is to indicate they are no longer valid for the current phase.

---

### FINDING 4 -- HIGH: Non-Atomic Rollback Across Three Stores (CLI Layer)

**Severity:** HIGH
**Affected code:** Task 6, `cmdRunRollbackWorkflow()` (plan lines 993-1100)

The CLI handler performs four sequential operations with no transaction boundary:

1. `phase.Rollback()` -- rewrites the run's phase (line 1053)
2. `rtStore.MarkArtifactsRolledBack()` -- marks artifacts (line 1063)
3. `dStore.CancelByRunAndPhases()` -- cancels dispatches (line 1069)
4. `rtStore.FailAgentsByRun()` -- fails agents (line 1075)

If the process crashes after step 1 but before steps 2-4, you have:
- Run is at the rollback target phase.
- Artifacts from rolled-back phases are still status='active'.
- Dispatches are still running.
- Agents are still active.

**Moreover:** Steps 2-4 are treated as warnings (the error is logged to stderr but the CLI returns 0). This means partial failure is silently accepted.

**Impact:** A dispatcher or SpawnHandler could see the run at "brainstorm" phase but with active agents from "executing" phase still running. The SpawnHandler (handler_spawn.go) triggers on `e.ToState == "executing"`, so it would not re-fire for a rollback. But the existing agents would keep running against a now-invalidated phase context.

**Fix:** Wrap all four operations in a single SQL transaction. Since the stores currently accept `*sql.DB`, not `*sql.Tx`, this requires either:
- (a) A new method on the DB type that provides a shared `*sql.Tx` across stores, or
- (b) A `RollbackAll(ctx, runID, targetPhase, reason)` function that opens a single transaction and does all four operations.

If full transactional wrapping is not feasible in the short term, at minimum: if any of steps 2-4 fail, the function should return a non-zero exit code and print a clear "rollback partially applied" warning with instructions to manually complete the remaining steps.

---

### FINDING 5 -- MEDIUM: Event Recording Order (Phase Change Without Audit Trail on Crash)

**Severity:** MEDIUM
**Affected code:** Task 4, `Rollback()` function (plan lines 596-643)

The `Rollback()` function does:
1. `store.RollbackPhase()` -- phase is updated (line 617)
2. `store.AddEvent()` -- audit event is recorded (line 622)

If the process crashes between 1 and 2, the phase was rewound but no audit event was recorded. The audit trail has a gap.

**This matches the existing pattern in `Advance()`.** Lines 165-180 of `machine.go` show the same order: `UpdatePhase()` first, then `AddEvent()`. The plan's comment at line 590 explicitly notes this: "Rollback does NOT delete events or artifacts -- those are marked separately."

**Assessment:** This is an accepted design decision in the existing codebase. Both `Advance()` and `Rollback()` prefer "state change succeeds, audit may be lost" over "audit recorded, state change may not happen." This is a defensible choice for a kernel that prioritizes forward progress.

**However:** The `Advance()` code at least uses optimistic concurrency on the UPDATE, so a retry would detect the stale phase. The rollback UPDATE (as written) has no such protection -- a retry after crash could apply the rollback again at a different phase (see Finding 1).

**Recommendation:** If Finding 1 is fixed (adding `WHERE phase = ?` to the rollback UPDATE), then this finding is downgraded to LOW -- the retry would fail with ErrStalePhase since the phase already changed.

---

### FINDING 6 -- MEDIUM: Bulk Dispatch Cancellation Skips Individual Event Recording

**Severity:** MEDIUM
**Affected code:** Task 5, `CancelByRunAndPhases()` (plan lines 878-907)

The plan's `CancelByRunAndPhases()` at line 901-903 says:

> "We don't have individual dispatch IDs here -- the event recorder handles per-dispatch events at the UpdateStatus level. For bulk cancellation, we skip individual event recording to avoid N queries."

The existing `dispatch.UpdateStatus()` (dispatch.go line 200) uses a transaction, reads the previous status, commits, then fires `s.eventRecorder`. The bulk UPDATE bypasses all of this:
- No per-dispatch previous status capture.
- No per-dispatch event recorder callback.
- No dispatch_events rows for the individual cancellations.

**Impact:** Event bus consumers that track dispatch lifecycle via `dispatch_events` will never see these cancellations. The only record is a single aggregate dispatch event recorded in the CLI handler (plan line 1082):

```go
evStore.AddDispatchEvent(ctx, "", runID, "", dispatch.StatusCancelled, "rollback", reason)
```

This event has an empty `dispatch_id` and empty `from_status`, which is semantically novel -- no existing dispatch event has these empty. Consumers that parse `dispatch_id` may fail or ignore this event.

**Fix:** Either:
- (a) Record individual dispatch events by first querying the affected dispatch IDs, then bulk-updating, then inserting events. This is N+1 queries but preserves the event bus contract.
- (b) Define a new event_type (e.g., `"bulk_cancel"`) with a JSON reason field that lists the affected dispatch IDs and count. This gives consumers enough to react without N queries.
- (c) Accept the gap and document it. If no existing consumer relies on per-dispatch cancellation events, this is acceptable. But it should be explicitly stated.

---

### FINDING 7 -- MEDIUM: `currentPhase` Parameter in `RollbackPhase()` Is Redundant and Error-Prone

**Severity:** MEDIUM
**Affected code:** Task 3, `RollbackPhase()` signature (plan line 373) and Task 4, `Rollback()` call (plan line 617)

`RollbackPhase()` takes `currentPhase` as a parameter, but then the implementation does `run, err := s.Get(ctx, id)` and validates against the chain using the freshly loaded run. However, it never actually uses `currentPhase` in the SQL UPDATE (see Finding 1 -- no WHERE clause).

In `Rollback()` at plan line 617, the caller passes `fromPhase` (which was read earlier and may be stale by now):

```go
if err := store.RollbackPhase(ctx, runID, fromPhase, targetPhase); err != nil {
```

But `RollbackPhase()` also does its own `store.Get()` at line 375. So it reads the run twice -- once in `Rollback()` and once in `RollbackPhase()`. The two reads could return different states.

**Fix:** Choose one approach:
- (a) `RollbackPhase()` trusts the caller's `currentPhase` and uses it in a `WHERE phase = ?` guard (preferred -- matches `UpdatePhase()` pattern).
- (b) `RollbackPhase()` does its own read and ignores the caller's parameter (remove it from the signature).

The current plan does neither consistently. The method reads the run, validates, but then ignores the validation in the SQL.

---

### FINDING 8 -- MEDIUM: Schema Migration v7->v8 Guard Is Wrong

**Severity:** MEDIUM
**Affected code:** Task 1, Step 5 (plan lines 114-128)

The plan adds the v7->v8 migration as:

```go
if currentVersion >= 7 {
    v8Stmts := []string{
        "ALTER TABLE run_artifacts ADD COLUMN status TEXT NOT NULL DEFAULT 'active'",
    }
```

But compare with the existing v5->v6 migration at db.go line 137:

```go
if currentVersion >= 5 {
```

The existing code at line 132 says `if currentVersion >= currentSchemaVersion { return nil }`, where `currentSchemaVersion` is being changed to 8. So the flow is:
1. Read `currentVersion` (e.g., 7).
2. Check `if currentVersion >= 8` -- false, proceed.
3. Check `if currentVersion >= 5` -- true, run v5->v6 (idempotent).
4. Check `if currentVersion >= 7` -- true, run v7->v8.
5. Apply schema DDL, set version to 8.

**This is correct for a DB at version 7.** But for a DB at version 5 or 6 that has never had the v5->v6 migration, the v7->v8 block also fires (because `currentVersion >= 7` is false for version 5). Wait -- actually, `currentVersion` is 5, `5 >= 7` is false, so the v7->v8 block does NOT fire. That is correct.

For a DB at version 6: `6 >= 7` is false, so v7->v8 does not fire. But the schema DDL is applied at step 4, and the DDL has `CREATE TABLE IF NOT EXISTS run_artifacts` which includes the full table definition from schema.sql. If schema.sql is updated to include `status` (as the plan says in Step 4), then the DDL will create the table with `status` for new databases. For existing databases, `CREATE TABLE IF NOT EXISTS` is a no-op -- it does not add missing columns. So a DB at version 6 would skip the ALTER TABLE and not get the `status` column.

**Wait -- this is a real problem.** A database that was created at version 6 and never migrated to 7 would:
1. Have `currentVersion = 6`.
2. `6 >= 5` is true -- v5->v6 migration runs (idempotent).
3. `6 >= 7` is false -- v7->v8 migration SKIPS.
4. Schema DDL applies -- `CREATE TABLE IF NOT EXISTS run_artifacts` is a no-op (table exists).
5. Version is set to 8.
6. Result: schema version is 8 but `run_artifacts` has no `status` column.

**Actually, wait.** Looking more carefully at the db.go code: there is no v6->v7 migration block shown. Version went from 5 to 7 (via the v5->v6 block at `currentVersion >= 5` plus the DDL for interspect_events). The pattern is that the `>= 5` guard catches any DB at version 5 or 6. The proposed `>= 7` guard would catch DBs at version 7. A DB at version 6 would NOT get the v7->v8 ALTER TABLE.

**Fix:** The migration guard should be `if currentVersion >= 5` (or some version <= 7) to ensure that all databases below version 8 get the new column. The simplest correct guard is:

```go
if currentVersion < 8 {
    // v7 -> v8: add status column
    v8Stmts := ...
}
```

Or alternatively, just unconditionally run with `isDuplicateColumnError` protection (which the plan already has), and change the guard to `if currentVersion >= 5` (the earliest version that has the `run_artifacts` table at all).

---

### FINDING 9 -- MEDIUM: Pre-Skip State Not Cleared on Rollback

**Severity:** MEDIUM
**Affected code:** Task 4, `Rollback()` function (plan lines 596-643)

The `SkippedPhases()` method (store.go line 383) queries:

```sql
SELECT to_phase FROM phase_events WHERE run_id = ? AND event_type = 'skip'
```

If a phase was pre-skipped before a rollback, and then the run is rolled back past that phase, the skip event still exists. When the run advances again through that phase, `Advance()` will walk past it again (machine.go line 74).

**Scenario:**
1. Run is at "brainstorm". User skips "strategized".
2. Run advances through brainstorm-reviewed, skips strategized, lands at planned.
3. User rolls back to brainstorm.
4. User wants to NOT skip strategized this time.
5. Run advances: brainstorm -> brainstorm-reviewed -> (skip) -> planned. The old skip event is still in phase_events.

**Impact:** The skip is permanent and invisible after rollback. There is no "unskip" command.

**Fix:** Either:
- (a) `Rollback()` should insert a "clear-skip" event (new event type) for each rolled-back phase that had been pre-skipped, or
- (b) `SkippedPhases()` should only consider skip events that occurred after the most recent rollback event for that run, or
- (c) Document that pre-skips survive rollback, and if the user wants to un-skip, they need a new mechanism.

This is not a data corruption issue, but it is a correctness issue for the user-facing behavior.

---

### FINDING 10 -- LOW: `FailAgentsByRun` Is Too Broad

**Severity:** LOW
**Affected code:** Task 5, `FailAgentsByRun()` (plan lines 855-868)

The method marks ALL active agents for a run as failed, regardless of which phase they belong to. Agents do not have a `phase` column, so there is no way to target only agents from rolled-back phases.

If a run is rolled back from "planned" to "brainstorm", agents from the "brainstorm" phase (which is not being rolled back) would also be marked as failed.

**Impact:** Agents that were correctly working on the target phase get needlessly terminated. This is overly aggressive.

**Fix:** Either:
- (a) Add a `phase` column to `run_agents` (schema change, not in scope), or
- (b) Accept that rollback kills all agents and document it. The user is expected to re-create agents for the target phase after rollback. This is defensible for v1.

---

### FINDING 11 -- LOW: Rollback Machine Function Has Double-Read

**Severity:** LOW
**Affected code:** Task 4, `Rollback()` function (plan lines 596-617)

`Rollback()` calls `store.Get()` at line 598. Then it calls `store.RollbackPhase()` at line 617, which internally calls `store.Get()` again at plan line 375. This is two reads of the same row within a non-transactional context. Given `SetMaxOpenConns(1)`, these are serialized, but the second read could see a different state than the first.

**Fix:** Either:
- (a) Have `RollbackPhase()` accept the already-loaded `*Run` instead of re-reading, or
- (b) Remove the `store.Get()` from `RollbackPhase()` and trust the caller's validation (preferred -- matches the pattern where `UpdatePhase()` does no validation and relies on the caller).

---

### FINDING 12 -- LOW: Integration Test Uses `grep -oP` (Non-Portable)

**Severity:** LOW
**Affected code:** Task 8, integration test (plan lines 1332, 1373)

The test uses `grep -oP '"id":\s*"\K[^"]+'` which requires Perl-compatible regex (GNU grep). This works on this server but is not portable to macOS or Alpine.

**Fix:** Use `jq -r '.id'` instead, which is already used elsewhere in the test.

---

## Summary Table

| # | Severity | Finding | Fix Effort |
|---|----------|---------|------------|
| 1 | CRITICAL | Rollback UPDATE has no optimistic concurrency, enabling race with Advance that corrupts audit trail | Small (add WHERE clause) |
| 2 | HIGH | `completed_at = NULL` breaks "set once" invariant; `IsTerminalStatus("completed")` semantics change | Medium (design decision + audit callers) |
| 3 | HIGH | `CountArtifacts()` gate still counts rolled-back artifacts, enabling gate bypass | Small (add WHERE filter) |
| 4 | HIGH | CLI performs 4 non-atomic operations; partial failure leaves inconsistent state | Medium (transaction wrapping or compensation) |
| 5 | MEDIUM | Event recording after phase change (crash = audit gap); acceptable if Finding 1 is fixed | None (accepted pattern) |
| 6 | MEDIUM | Bulk dispatch cancellation silently drops per-dispatch events from event bus | Small (document or add bulk event type) |
| 7 | MEDIUM | `currentPhase` parameter in `RollbackPhase()` is validated but never used in SQL | Small (use it in WHERE clause, per Finding 1) |
| 8 | MEDIUM | Migration guard `currentVersion >= 7` skips v8 migration for DBs at version 5-6 | Small (change guard condition) |
| 9 | MEDIUM | Pre-skip events survive rollback; skipped phases remain skipped on re-advance | Medium (new event type or query filter) |
| 10 | LOW | `FailAgentsByRun` kills all agents including those in the target phase | Small (document or add phase column) |
| 11 | LOW | Double-read in Rollback + RollbackPhase (redundant, slight TOCTOU window) | Small (remove inner Get) |
| 12 | LOW | `grep -oP` in integration test is non-portable | Trivial (use jq) |

---

## Recommended Fix Priority

**Before implementation begins (blocking):**
1. Fix Finding 1: Add `WHERE phase = ?` to `RollbackPhase()` UPDATE.
2. Fix Finding 8: Change migration guard from `>= 7` to `< 8` (or `>= 5`).
3. Fix Finding 3: Add `WHERE status != 'rolled_back'` to `CountArtifacts()`.

**During implementation (should-fix):**
4. Fix Finding 4: Either wrap in transaction or document partial-failure recovery.
5. Fix Finding 7: Resolved automatically by Fix 1.
6. Fix Finding 2: Add comment/documentation about `completed_at` reversion semantics.
7. Fix Finding 6: Choose option (b) or (c) for dispatch event recording.

**After implementation (nice-to-have):**
8. Fix Finding 9: Design an "unskip on rollback" mechanism.
9. Fix Finding 11: Remove double-read.
10. Fix Finding 12: Use jq instead of grep -oP.
11. Fix Finding 10: Document agent kill behavior.

---

## Test Recommendations

1. **Add a concurrent rollback-vs-advance test.** Use `go test -race` with two goroutines: one calling `Advance()`, one calling `Rollback()`. Verify that exactly one succeeds and the audit trail is consistent.

2. **Add a gate-after-rollback test.** Create artifacts, rollback, verify that `CountArtifacts()` returns 0 for the rolled-back phases (after Fix 3).

3. **Add a crash-recovery simulation.** Use a test that performs `RollbackPhase()` but not `AddEvent()`, then verifies the system can recover (re-issue the rollback).

4. **Add a pre-skip-survives-rollback test.** Skip a phase, advance past it, rollback, verify the skip is (or is not) still active.

5. **Add a schema migration test for DB at version 5.** Create a v5 DB, migrate to v8, verify `status` column exists on `run_artifacts`.
