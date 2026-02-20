# Architecture Review: Intercore Rollback and Recovery (E6)

**Plan:** `/root/projects/Interverse/docs/plans/2026-02-20-intercore-rollback-recovery.md`
**Reviewer:** Flux-drive Architecture & Design Reviewer
**Date:** 2026-02-20
**Mode:** Codebase-aware (CLAUDE.md, AGENTS.md, source code read)

---

## Executive Summary

The plan is structurally sound at the store and machine layers (Tasks 1–5). The phase machine's `Rollback()` mirrors `Advance()` appropriately, and the store methods are correctly scoped to their packages. There are two structural problems and one naming problem that need attention before implementation begins. None require redesigning the plan; all are fixable with targeted changes.

---

## Findings

### MUST-FIX

---

#### F1 — CLI handler is an implicit orchestrator with no atomicity guarantee

**Severity:** Must-fix (correctness / integration risk)
**Location:** Plan Task 6, `cmdRunRollbackWorkflow` in `/root/projects/Interverse/infra/intercore/cmd/ic/run.go`

The rollback workflow handler performs four separate mutations against three different stores in sequence, with no shared transaction:

```go
// Phase rewind (phase.Store)
result, err := phase.Rollback(ctx, pStore, runID, toPhase, reason, callback)

// Artifact marking (runtrack.Store)
markedArtifacts, err := rtStore.MarkArtifactsRolledBack(ctx, runID, result.RolledBackPhases)

// Dispatch cancellation (dispatch.Store)
cancelledDispatches, err := dStore.CancelByRunAndPhases(ctx, runID, result.RolledBackPhases)

// Agent failure (runtrack.Store again)
failedAgents, err := rtStore.FailAgentsByRun(ctx, runID)
```

The errors after `phase.Rollback` are downgraded to warnings (`fmt.Fprintf(os.Stderr, "warning: ...")`). This means the system can reach a state where:
- The run's phase pointer is at `brainstorm`
- Artifacts from `strategized` and `planned` still read `status = 'active'`
- Active dispatches were not cancelled

That is a partially-rolled-back run with no recovery path, and no indication in the DB that anything is incomplete. The plan describes the transaction as atomic ("Dispatch/artifact marking happens in the same transaction as the phase rewind") but the implementation does not enforce this.

**The project's own CLAUDE.md documents the transaction pattern for migrations. The same discipline applies here.**

**Smallest viable fix:** Move the three-step mutation into a single `*sql.Tx`. All three stores accept a `*sql.DB` injected via their `New()` constructors. The cleanest path is to expose a `BeginTx` helper on the `db.DB` wrapper (it already wraps `*sql.DB`) and pass the `*sql.Tx` to each store's operations, or use a new `RunRollbackTx(ctx, tx, runID, phases)` function per store. If a full cross-store transaction is undesirable, the minimum acceptable fix is to change the warning-and-continue pattern into an error-and-abort pattern so callers know a partial rollback occurred and can retry.

The existing `cmdRunCancel` in the same file uses a simpler pattern (single store, single write) and does not have this problem. The new rollback handler is meaningfully more complex and needs the same atomicity discipline applied to migrations in `db.go`.

---

#### F2 — `CodeRollbackEntry` and `ListArtifactsForCodeRollback` are misplaced in `runtrack/`

**Severity:** Must-fix (boundary violation)
**Location:** Plan Task 7, additions to `/root/projects/Interverse/infra/intercore/internal/runtrack/store.go`

`ListArtifactsForCodeRollback` performs a `LEFT JOIN dispatches d ON a.dispatch_id = d.id` inside `runtrack/store.go`. This makes `runtrack/` reach across the boundary into `dispatch/`'s table. The `dispatch` package already has its own `Store` and schema ownership over the `dispatches` table. The `runtrack` package currently queries only `run_artifacts` and `run_agents`; it has no other joins to `dispatches`.

The existing codebase uses a different pattern for cross-package queries: `runtrack` exposes a `RuntrackQuerier` interface, and the `phase` package calls through that interface (see `machine.go`, line 44: `rt RuntrackQuerier`). This keeps cross-package data access mediated through interfaces, not raw SQL joins.

Putting a SQL join to `dispatches` inside `runtrack/store.go` means:
1. `runtrack` now has an implicit dependency on `dispatch/`'s schema without importing the package or going through its store — it bypasses the abstraction.
2. If `dispatches` schema changes (column rename, table split), `runtrack` silently breaks.
3. `CodeRollbackEntry` conflates two domains (file artifact metadata + dispatch identity) into a struct that lives in neither domain cleanly.

**Smallest viable fix — two options:**

Option A (preferred for this codebase's style): Move `ListArtifactsForCodeRollback` and `CodeRollbackEntry` into `cmd/ic/run.go` as a query that the CLI handler builds directly using both stores. The CLI already imports both `runtrack` and `dispatch`. The handler can call `rtStore.ListArtifacts(ctx, runID, nil)` and then for each artifact with a non-nil `DispatchID` call `dStore.Get(ctx, *a.DispatchID)` to hydrate the dispatch name. This is N+1 but for a CLI query over a single run it is fine, and it keeps `runtrack` clean.

Option B: Extract a dedicated `internal/rollback/` package that imports both `runtrack` and `dispatch` and owns the join query. This is the right call only if two or more distinct callers need this cross-domain query. With only one CLI caller today this introduces an abstraction with a single consumer, which violates the YAGNI rule the project's design decisions enforce.

Option A is the right call for now.

---

### ADVISORY (should address, not a blocker)

---

#### A1 — `RollbackPhase` duplicates terminal-status guard already in `Rollback()`

**Severity:** Advisory (redundancy / maintenance surface)
**Location:** Plan Task 3, `RollbackPhase` in `phase/store.go`; Plan Task 4, `Rollback` in `phase/machine.go`

`RollbackPhase` starts with:
```go
if run.Status == StatusCancelled || run.Status == StatusFailed {
    return ErrTerminalRun
}
```

`Rollback()` also starts with:
```go
if run.Status == StatusCancelled || run.Status == StatusFailed {
    return nil, ErrTerminalRun
}
```

Both do a `store.Get()` and check the guard. `Rollback()` then immediately calls `store.RollbackPhase()`, so the guard fires twice on two separate reads. In a concurrent environment this creates a check-then-act gap: the status could change between the check in `Rollback()` and the check in `RollbackPhase()`. The second guard in `RollbackPhase` is therefore not redundant as a correctness measure but does add complexity.

The existing `Advance()` function resolves this by performing the guard only at the machine level and relying on the store's `UPDATE ... WHERE phase = expectedPhase` (optimistic concurrency) for the actual safety net. `RollbackPhase` deliberately skips optimistic concurrency (the plan comment says "rollback is an authoritative operation"). If that is accepted, the store-level guard becomes a convenience check, not a correctness requirement.

**Recommendation:** Consolidate the terminal-status check in `Rollback()` only. Remove it from `RollbackPhase`. This makes `RollbackPhase` a lower-level method that trusts its caller (the machine function) to have validated status. Add a comment to that effect. The `Rollback()` machine function performs a `store.Get()` and already has this check before calling `RollbackPhase()`, so the only additional risk is direct callers of `RollbackPhase()` bypassing the guard — but the store method is package-private in behavior (it's exported only for test purposes and the machine function). If external callers are expected, keep the guard in `RollbackPhase` and remove it from `Rollback()`.

---

#### A2 — `CancelByRunAndPhases` ignores its `phases` argument

**Severity:** Advisory (misleading API contract)
**Location:** Plan Task 5, `CancelByRunAndPhases` in `/root/projects/Interverse/infra/intercore/internal/dispatch/dispatch.go`

The function signature accepts `phases []string` but the implementation cancels all non-terminal dispatches for the run regardless of phase:

```go
// Plan comment: "For rollback, we cancel ALL non-terminal dispatches for the run."
result, err := s.db.ExecContext(ctx, `
    UPDATE dispatches SET status = ?, completed_at = ?
    WHERE scope_id = ? AND status NOT IN ('completed', 'failed', 'cancelled', 'timeout')`,
    StatusCancelled, now, runID,
)
```

The `phases` parameter is silently unused. This is both a misleading API (callers believe they are doing phase-scoped cancellation) and a scope-creep risk (it cancels dispatches that may belong to phases the user did not roll back, including the target phase itself).

The root cause is that `dispatches` has no `phase` column — they link to phases only indirectly via `run_artifacts.dispatch_id`. The plan acknowledges this in a comment but proceeds to accept the `phases` parameter anyway.

**Smallest viable fix:** Rename the function to `CancelAllByRun(ctx, runID)` and remove the `phases` parameter. Update the call site in Task 6 accordingly. The caller in `cmdRunRollbackWorkflow` can document that dispatch cancellation is run-scoped, not phase-scoped. This is honest about the actual behavior and prevents future callers from passing a `phases` argument expecting phase filtering that will never work. If phase-scoped dispatch cancellation is needed later, it requires a schema change to add a `phase` column to `dispatches` or a join through `run_artifacts`, and that is a separate task.

---

#### A3 — Dry-run computes `rolledBackPhases` in the CLI, not through the machine function

**Severity:** Advisory (logic duplication)
**Location:** Plan Task 6, `cmdRunRollbackWorkflow` in `cmd/ic/run.go`

The dry-run path in `cmdRunRollbackWorkflow` calls `phase.ChainPhasesBetween()` directly:

```go
rolledBackPhases := phase.ChainPhasesBetween(chain, toPhase, run.Phase)
if rolledBackPhases == nil {
    fmt.Fprintf(os.Stderr, "...")
    return 1
}
if dryRun {
    // return rolledBackPhases directly
}
```

The actual rollback path calls `phase.Rollback()`, which internally calls `ChainPhasesBetween()` again and returns the result in `RollbackResult.RolledBackPhases`. The same chain-computation logic runs in two different locations. If `ChainPhasesBetween`'s semantics change, the dry-run output could diverge from what an actual rollback would do.

**Smallest viable fix:** `Rollback()` should accept a `dryRun bool` parameter that skips the store write and event recording but returns the `RollbackResult` with `RolledBackPhases` populated. The CLI handler then calls `phase.Rollback(ctx, ..., dryRun: true)` for both paths and the chain computation stays in one place. Alternatively, extract a `phase.ComputeRollback(run *Run, targetPhase string) (*RollbackResult, error)` pure function that the CLI can call for dry-run without touching the store. Either eliminates the duplication. The latter is slightly simpler because it avoids adding a `dryRun` flag to a function that already has multiple parameters.

---

#### A4 — Event bus notification in `cmdRunRollbackWorkflow` uses a fake dispatch ID

**Severity:** Advisory (data correctness)
**Location:** Plan Task 6, `cmdRunRollbackWorkflow` in `cmd/ic/run.go`

```go
if cancelledDispatches > 0 {
    evStore.AddDispatchEvent(ctx, "", runID, "", dispatch.StatusCancelled, "rollback", reason)
}
```

`AddDispatchEvent` signature: `(ctx, dispatchID, runID, fromStatus, toStatus, eventType, reason)`. The call passes `""` for `dispatchID` (the primary FK) and `""` for `fromStatus`. Looking at the `event/store.go` implementation:

```go
INSERT INTO dispatch_events (dispatch_id, run_id, from_status, to_status, event_type, reason)
VALUES (?, NULLIF(?, ''), ?, ?, ?, NULLIF(?, ''))
```

`NULLIF(?, '')` on `dispatchID` stores NULL. This inserts a row with `dispatch_id = NULL` and `from_status = ''`. For event consumers that join `dispatch_events` to `dispatches` on `dispatch_id`, this row will never join. For the `ListEvents` query in `event/store.go`, dispatch events are returned when `run_id` matches — so this event will surface in `ic events tail`, but with no `dispatch_id` and an empty `from_status`, which is misleading.

Compare with how `cmdRunAdvance` uses the event recorder: it fires the recorder per-dispatch inside `UpdateStatus`, which has the actual dispatch ID. The rollback path bypasses `UpdateStatus` entirely (it uses a bulk `UPDATE` without the recorder callback) and then adds a synthetic event with no meaningful ID.

**Smallest viable fix:** Either drop the synthetic event entirely (the individual dispatch cancellations are already audit-able via the `run_id` filter on the phase rollback event) or change `CancelAllByRun` to return a slice of cancelled dispatch IDs and record one event per dispatch. The former is simpler and does not compromise the audit trail for the rollback operation itself, which is already recorded by `phase.Rollback()`.

---

## Pattern Summary

| Finding | Severity | Location | Action |
|---------|----------|----------|--------|
| F1: No atomicity across 3-store mutation | Must-fix | Task 6 `cmdRunRollbackWorkflow` | Wrap in single `*sql.Tx` or abort-on-partial |
| F2: `runtrack` cross-boundary SQL join to `dispatches` | Must-fix | Task 7 `ListArtifactsForCodeRollback` | Move join to CLI handler or new package |
| A1: Duplicate terminal-status guard | Advisory | Tasks 3+4 store + machine | Remove from `RollbackPhase`, keep in `Rollback` |
| A2: Unused `phases` param in `CancelByRunAndPhases` | Advisory | Task 5 dispatch method | Rename to `CancelAllByRun`, drop param |
| A3: Dry-run duplicates chain computation | Advisory | Task 6 CLI dry-run path | Extract `ComputeRollback` pure function |
| A4: Synthetic event with no dispatch ID | Advisory | Task 6 event recording | Drop synthetic event or use real IDs |

---

## What the Plan Gets Right

- `Rollback()` mirroring `Advance()` structurally (store method + machine function separation) is correct and follows the established pattern exactly.
- `ChainPhasesBetween()` and `ChainPhaseIndex()` as pure helper functions belong in `phase/` next to `ChainContains()` and `ChainIsValidTransition()` — correct placement.
- `RollbackResult` as a value type returned from the machine function mirrors `AdvanceResult` — correct.
- `MarkArtifactsRolledBack` with a `phases []string` parameter in `runtrack/` is correctly scoped: `run_artifacts` is owned by `runtrack/`, the method touches only that table.
- `FailAgentsByRun` in `runtrack/` is correctly scoped: `run_agents` is owned by `runtrack/`.
- The schema migration pattern (version bump + `ALTER TABLE ADD COLUMN` with `isDuplicateColumnError` guard) matches the existing v5→v6 migration exactly.
- `EventRollback` constant added to `phase/phase.go` is the right location alongside the other event constants.
- `ErrInvalidRollback` sentinel in `phase/errors.go` follows the existing `errors.New` pattern.
- The bash wrapper in `lib-intercore.sh` follows the existing guard-then-delegate pattern used by `intercore_run_budget` and other wrappers.
- The dependency graph in the plan is accurate and the parallel-execution grouping (Tasks 1+2 independent, Tasks 3+5+7 parallel) is sound.

---

## Sequencing Recommendation

If the team proceeds:

1. Fix F2 before writing `ListArtifactsForCodeRollback` — it changes where the code goes, not how it works.
2. Fix F1 before committing Task 6 — it changes the transaction model, which affects what error handling Task 6 needs.
3. Address A2 (rename `CancelByRunAndPhases`) when writing Task 5 — it is a one-line rename now and a breaking refactor later.
4. A1, A3, A4 can be addressed during code review of the relevant tasks without blocking other work.
