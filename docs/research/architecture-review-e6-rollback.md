# Architecture Review — E6 Rollback & Recovery

Date: 2026-02-20
Diff reviewed: /tmp/qg-diff-1771610037.txt
Scope: 12 files — cmd/ic/run.go, internal/dispatch/dispatch.go, internal/phase/machine.go + store.go + tests, internal/runtrack/runtrack.go + store.go + tests, lib-intercore.sh, CLAUDE.md, test-integration.sh

---

## Context

This change adds workflow rollback (`ic run rollback --to-phase=<p>`) and a code-artifact query (`ic run rollback --layer=code`) to intercore. The workflow rollback rewinds a run's phase pointer, marks affected artifacts as rolled-back, cancels active dispatches, and fails active agents. The code query is a read-only JOIN of run_artifacts with dispatches that surfaces which files a code-reverting operator would need to handle.

The implementation adds 217 lines of CLI Go, 74 lines in machine.go, 57 lines in store.go, 205 lines in runtrack/store.go, 40 lines in lib-intercore.sh, and 129 integration test lines. It introduces one new error sentinel (ErrInvalidRollback), one new type (CodeRollbackEntry), and one new store method per affected package.

---

## Findings Summary

Seven findings were identified. Two are P2 (structural, affect testability and correctness consistency). Five are P3 (localized, low breakage risk but create maintenance debt).

The overall verdict is **needs-changes**. The P2 issues do not block execution — the feature works correctly end-to-end — but they violate the architectural boundary that has kept intercore maintainable: multi-store orchestration belongs in a service function, not a CLI handler. The P3 issues are straightforward to address before shipping.

Full findings are in /root/projects/Interverse/.clavain/quality-gates/fd-architecture.md.

---

## Key Findings

### P2 — A-01: Rollback orchestration is in the CLI layer

`cmdRunRollbackWorkflow` wires four stores (phase, runtrack, dispatch, event) in a 110-line CLI function. Every other stateful multi-step operation in intercore (Advance, gate override) is coordinated by a function in `internal/phase/machine.go` that the CLI calls as a single unit. The rollback sequence is not unit-testable from within the Go package layer.

**Fix**: extract a `RollbackRun(ctx, pStore, rtStore, dStore, evStore, ...)` function into `machine.go` or a new `internal/rollback/` package.

### P2 — A-02: Terminal-status check is duplicated across machine.go and store.go

`phase.Rollback` in machine.go checks `StatusCancelled || StatusFailed` before calling `store.RollbackPhase`, which performs the identical check. The existing `Advance` function does not pre-check invariants that the store enforces. This split means a change to which statuses are rollback-eligible requires updating two sites.

**Fix**: remove the guard from machine.Rollback; rely on `ErrTerminalRun` from the store as the single enforcement point.

### P2 — A-03: One subcommand routes two semantically distinct operations

`ic run rollback` with `--layer=code` is a read-only artifact query; without it, it is a write operation that mutates four tables. The `--dry-run` flag is silently irrelevant when `--layer=code` is present. The intercore convention is one verb per operation (`ic gate check` vs `ic gate override`).

**Fix**: expose the code-rollback query as a separate subcommand (`ic run rollback-info` or `ic run artifacts --rollback`).

---

## What Works Well

- The phase.Rollback function is well-commented and cleanly parallel to Advance in structure.
- RollbackPhase in store.go correctly clears completed_at and reverts status=active in a single UPDATE, avoiding a two-step status update.
- MarkArtifactsRolledBack uses a dynamically constructed IN clause rather than N individual UPDATEs — correct for the batch case.
- CountArtifacts now excludes rolled-back artifacts from gate evaluation, which is the correct behavior for re-execution after rollback.
- The integration test suite covers the critical paths: dry-run, workflow rollback, completed-run rollback, cancelled-run rejection, forward-target rejection, and wrapper functions.
- The bash wrappers follow the established lib-intercore.sh conventions exactly (intercore_available guard, INTERCORE_DB passthrough).
