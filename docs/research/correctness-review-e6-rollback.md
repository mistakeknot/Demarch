# Correctness Review — E6 Rollback and Recovery

**Reviewer:** Julik (Flux-drive Correctness Reviewer)
**Date:** 2026-02-20
**Scope:** E6 Rollback & Recovery — 12 files, Go 1.22 + SQLite (modernc.org/sqlite, WAL, SetMaxOpenConns(1))

Full findings are at: `/root/projects/Interverse/.clavain/quality-gates/fd-correctness.md`

---

## Invariants Established

1. **Phase monotonicity**: `phase` only moves forward during normal operation. Rollback is the deliberate exception and must be atomic with all downstream cleanup.
2. **Status consistency**: `status='completed'` implies `phase=terminal` and `completed_at IS NOT NULL`. Rollback clearing `completed_at` must also clear `status`.
3. **Artifact liveness**: `CountArtifacts` counts only artifacts valid for the active phase range. Rolled-back artifacts must not count toward gate checks.
4. **Dispatch-run binding**: Active dispatches for a rolled-back run must not continue writing results as if the run is at the pre-rollback phase.
5. **Audit completeness**: Every phase transition (including rollback) must be recorded in `phase_events` before the function returns.
6. **Atomic multi-table consistency**: After rollback, `runs.phase`, `run_artifacts.status`, `dispatches.status`, and `run_agents.status` must be mutually consistent.

---

## Findings Index

| SEVERITY | ID | Section | Title |
|----------|----|---------|-------|
| HIGH | C-01 | Transaction Safety | Four sequential store writes with no cross-store transaction — partial failure leaves DB inconsistent |
| HIGH | C-02 | TOCTOU / Double-Read | `Rollback` in machine.go + `RollbackPhase` in store.go both call `store.Get` — phase can advance between reads |
| MEDIUM | C-03 | Silent Partial Failure | Artifact and agent failure steps are downgraded to warnings — exit 0 on partial rollback |
| MEDIUM | C-04 | Migration Comment Mismatch | v7→v8 guard covers v4–v7 without documentation — maintenance trap for future migrations |
| MEDIUM | C-05 | `AddArtifact` Omits `status` | In-memory `Artifact.Status` is nil after insert; only populated after a `ListArtifacts` re-read |
| LOW | C-06 | `CancelByRun` Doc Imprecision | Code cancels `spawned` + `running`; comment says "active dispatches" — misleading for readers |
| LOW | C-07 | Empty `dispatch_id` in Event Bus | `AddDispatchEvent(ctx, "", ...)` stores `""` in `dispatch_id TEXT NOT NULL` — semantically invalid |
| LOW | C-08 | No Test for Partial Failure Paths | No test verifies state after phase rewind succeeds and artifact/agent cleanup fails |

**Verdict: needs-changes**

---

## Summary

The E6 rollback implementation is architecturally sound and each individual store method is correctly written. The critical gap is **atomicity**: the four sequential writes in `cmdRunRollbackWorkflow` (phase rewind, artifact marking, dispatch cancellation, agent failure) are separate SQLite transactions. A process kill between step 1 and steps 2–4 leaves the run's phase pointer rewound while artifacts, dispatches, and agents still reflect the pre-rollback world — causing subsequent gate checks (`CountArtifacts`) to see stale data. The secondary issue is a TOCTOU double-read: `Rollback` and `RollbackPhase` each call `store.Get` independently, so a concurrent `ic run advance` can slip between the two reads, causing the rollback to commit against a stale `currentPhase` and under-mark artifacts. The empty `dispatch_id` written to the event bus (C-07) is a concrete data quality bug that will produce invalid rows in `dispatch_events`.

---

## Key Issues Detail

### C-01 (HIGH) — No Cross-Store Transaction

**File:** `/root/projects/Interverse/infra/intercore/cmd/ic/run.go`, `cmdRunRollbackWorkflow`

The four operations after `phase.Rollback` succeeds are sequential without a wrapping transaction:

```go
result, err := phase.Rollback(...)          // committed
markedArtifacts, err := rtStore.MarkArtifactsRolledBack(...)  // separate tx
cancelledDispatches, err := dStore.CancelByRun(...)            // separate tx
failedAgents, err := rtStore.FailAgentsByRun(...)              // separate tx
```

A SIGKILL between step 1 and step 2 leaves `runs.phase='brainstorm'` but `run_artifacts.status='active'` for phases that should be rolled back. `CountArtifacts` will return inflated counts, causing gates to pass incorrectly on the next advance.

**Fix:** Wrap all four in `db.BeginTx` or expose a single `RollbackAll` function that performs them atomically.

### C-02 (HIGH) — TOCTOU Double-Read

**File:** `/root/projects/Interverse/infra/intercore/internal/phase/machine.go` + `store.go`

`machine.go:Rollback` calls `store.Get`, validates phase, then calls `store.RollbackPhase` which calls `store.Get` again. The `UPDATE` in `RollbackPhase` has no `WHERE phase = ?` guard:

```sql
UPDATE runs SET phase = ?, status = 'active', updated_at = ?, completed_at = NULL
WHERE id = ?
```

A concurrent `ic run advance` committing between the two reads causes the rollback to commit against the wrong `currentPhase`, and `RolledBackPhases` returned to the caller will be incomplete (missing the phases added by the concurrent advance).

**Fix:** Add `AND phase = ?` to the `UPDATE` in `RollbackPhase`, return `ErrStalePhase` on `n==0` (same pattern as `UpdatePhase`).

### C-07 (LOW) — Empty dispatch_id in Event Bus

**File:** `/root/projects/Interverse/infra/intercore/cmd/ic/run.go`, line 185

```go
evStore.AddDispatchEvent(ctx, "", runID, "", dispatch.StatusCancelled, "rollback", reason)
```

`AddDispatchEvent` does not apply `NULLIF(?, '')` to `dispatchID`. This stores `""` in `dispatch_events.dispatch_id`. Remove this call and instead pass a non-nil `eventRecorder` to `dispatch.New` so per-dispatch cancellation events are recorded naturally through the existing `UpdateStatus` path.

---

## Improvements

- **I-01:** Expose `RollbackAll` atomic function wrapping all four writes in one `db.BeginTx`.
- **I-02:** Add `ic run rollback <id> --repair` to re-attempt failed cleanup steps without re-doing the phase rewind.
- **I-03:** Add `"errors": []` to output JSON to distinguish "nothing to mark" from "error suppressed."
- **I-04:** Add `status` to the `idx_run_artifacts_phase` index to optimize `MarkArtifactsRolledBack` scans on large artifact sets.
