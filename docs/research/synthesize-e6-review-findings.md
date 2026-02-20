# Synthesis: E6 Rollback Quality Gates Review

**Date:** 2026-02-20
**Mode:** quality-gates
**Context:** 12 files changed across Go and Shell. Risk domains: database/transaction safety, phase state machine, CLI rollback orchestration. 3 agents ran: fd-architecture, fd-quality, fd-correctness.

---

## Validation

- 3/3 agents valid (Findings Index + Verdict present in all)
- 0 agents failed or malformed
- fd-architecture: 7 findings (3 P2, 4 P3) — Verdict: needs-changes
- fd-quality: 9 findings (2 MEDIUM, 4 LOW, 3 INFO) — Verdict: needs-changes
- fd-correctness: 8 findings (2 HIGH, 3 MEDIUM, 3 LOW) — Verdict: needs-changes

---

## Overall Verdict: needs-changes | Gate: FAIL

No P0/P1 findings, but 2 HIGH-severity correctness bugs and 6 MEDIUM-severity structural issues block a clean merge. The implementation is architecturally coherent and test coverage is solid, but the multi-store write sequence has a critical atomicity gap and a concrete TOCTOU race.

---

## Deduplicated Findings

### HIGH (count: 2)

**C-01 — Four sequential store writes with no cross-store transaction** (convergence: 3/3)
- Location: `cmd/ic/run.go:cmdRunRollbackWorkflow` lines 155–181
- `phase.Rollback`, `MarkArtifactsRolledBack`, `CancelByRun`, and `FailAgentsByRun` are four separate SQLite transactions. A SIGKILL between step 1 (phase rewind committed to DB) and steps 2–4 leaves the run with rewound phase but stale artifact/dispatch/agent statuses. A subsequent `ic run advance` will pass gate checks with inflated `CountArtifacts` counts because rolled-back phase artifacts remain `status='active'`.
- Fix: Wrap all four writes in a single `db.BeginTx`. The `SetMaxOpenConns(1)` single-connection model makes this safe. Expose as `RollbackAll(ctx, tx, runID, targetPhase)` in `internal/phase/machine.go` or a new `internal/rollback/` package.
- Raised by: fd-correctness (C-01), confirmed by fd-architecture (A-06), fd-quality (partial-rollback pattern)

**C-02 — TOCTOU double-read in Rollback — concurrent advance corrupts rolled-back phase set** (convergence: 2/3)
- Location: `internal/phase/machine.go:Rollback` + `internal/phase/store.go:RollbackPhase`
- `machine.go:Rollback` calls `store.Get` then `store.RollbackPhase` calls `store.Get` again. Between the two reads, a concurrent `ic run advance` can commit a phase transition. The `UPDATE` in `RollbackPhase` has no `WHERE phase = ?` guard (unlike `UpdatePhase`). The rollback commits, but `RolledBackPhases` reflects the stale first read, causing `MarkArtifactsRolledBack` to under-mark artifacts from the newer phase.
- Fix: Add `AND phase = ?` to the UPDATE in `RollbackPhase`; return `ErrStalePhase` when `n == 0` (run still exists). Mirror the optimistic concurrency pattern from `UpdatePhase`. Note: "direct UPDATE" in the design comment means no retry loop, not no stale-phase guard.
- Raised by: fd-correctness (C-02), fd-quality (Q4 — redundant Get)

### MEDIUM (count: 6, after dedup)

**C-03 / A-06 — Silent partial failure — exit 0 with partially applied rollback** (convergence: 3/3)
- Location: `cmd/ic/run.go:cmdRunRollbackWorkflow` lines 166–181
- Errors from `MarkArtifactsRolledBack`, `CancelByRun`, and `FailAgentsByRun` are printed as stderr warnings and discarded; function returns exit 0. CI callers see success. Output JSON shows `marked_artifacts=0` which is indistinguishable from "nothing to mark."
- Fix: Return exit 2 when any cleanup step fails after a successful phase rewind. Or add `"artifact_marking_failed": true` to output JSON.

**A-01 — Rollback orchestration lives in the CLI layer, not a service layer** (convergence: 2/3)
- Location: `cmd/ic/run.go:cmdRunRollbackWorkflow` lines 93–203
- The 110-line function is the only intercore operation coordinating across three stores that lives in the CLI layer. Not testable from unit tests. Every other multi-step operation (advance, skip, gate override) has a coordinator in `internal/phase/machine.go`.
- Fix: Extract into `RollbackRun(ctx, pStore, rtStore, dStore, evStore, runID, toPhase, reason, callback)` in `internal/phase/machine.go`. CLI becomes a thin wrapper.

**A-02 / Q1 — Duplicate terminal-status validation split between machine.go and store.go** (convergence: 2/3)
- Location: `internal/phase/machine.go:340`, `internal/phase/store.go:504–507`
- Both `phase.Rollback` and `store.RollbackPhase` check terminal status and return `ErrTerminalRun`. A change to the allowed-terminal set will miss one site. The store also re-calls `Get` (per Q4), doubling DB round-trips.
- Fix: Remove guard from `machine.Rollback`; keep only in `store.RollbackPhase`. Pass the already-fetched run struct in to eliminate the extra Get. (Consistent with intercore's pattern: store enforces structural invariants, machine enforces workflow policy.)

**Q-02 — enc.Encode return values discarded in all three JSON output paths** (convergence: 1/3)
- Location: `cmd/ic/run.go` lines ~131–258 (dry-run, workflow, code paths)
- All three `enc.Encode(output)` calls discard error return. A full pipe buffer or write failure produces truncated JSON silently.
- Fix: Check error and `fmt.Fprintf(os.Stderr, ...)` the failure in each path.

**C-05 — AddArtifact omits status column — Artifact.Status nil on first read** (convergence: 1/3)
- Location: `internal/runtrack/store.go:AddArtifact` lines 220–232
- INSERT omits `status`; DB DEFAULT 'active' applies correctly but the returned `Artifact` struct has `Status == nil`. No current caller dereferences it immediately, but it is a latent nil-pointer trap.
- Fix: Include `status` explicitly in the INSERT as `'active'`.

**C-06 — Dispatch event written with empty dispatch_id — invalid NOT NULL semantic** (convergence: 1/3)
- Location: `cmd/ic/run.go:cmdRunRollbackWorkflow` line 185
- `AddDispatchEvent(ctx, "", runID, ...)` — `NULLIF(?, '')` is applied to `run_id` and `reason` but not `dispatchID`. Empty string stored in `dispatch_id TEXT NOT NULL`. SQLite does not reject empty strings for NOT NULL, so no error is raised, but event bus consumers joining on `dispatch_id` return nonsensical rows.
- Fix: Remove the aggregate `AddDispatchEvent` call. Pass non-nil `eventRecorder` to `dispatch.New` so per-dispatch events fire naturally via the existing `UpdateStatus` path.

### P3 / NICE-TO-HAVE (count: 10)

- A-03: Separate `ic run rollback --layer=code` (read-only) into `ic run rollback-info` (write/read conflation, --dry-run silently inert with --layer=code)
- A-04: Add `ArtifactStatusActive` and `ArtifactStatusRolledBack` constants to `internal/runtrack/runtrack.go`
- A-05 / Q5: Comment `artifact_exists` gate rule in `gate.go` referencing that `CountArtifacts` excludes rolled-back artifacts (convergence: 2/3)
- C-04: Migration guard comment says "v7→v8" but fires for v4–v7; maintenance trap for future non-idempotent migrations
- A-07: `lib-intercore.sh` version jumps 0.6.0→1.1.0 for purely additive changes; AGENTS.md still references v0.6.0
- Q-03: Exit code 1 conflates "run not found" with "terminal run cannot be rolled back" — Bash callers cannot distinguish
- Q-06: `intercore_run_rollback` suppresses stderr unconditionally — actionable rollback errors swallowed
- Q-07: `TestStore_FailAgentsByRun` loop checks id1 and id3 but never asserts id2 status
- C-07: `CancelByRun` comment says "active dispatches" but implementation correctly covers "spawned" too — documentation gap only
- C-08: No test for partial failure interleaving; no test verifying `CountArtifacts` excludes rolled-back artifacts for gate evaluation

---

## Conflicts

**CONFLICT-01: C-02 TOCTOU vs "authoritative rollback" design decision**
- fd-correctness: absence of `WHERE phase = ?` in `RollbackPhase` UPDATE is a correctness bug
- Code comment: "direct UPDATE — rollback is authoritative" (intended)
- Resolution: fd-correctness is correct. "Authoritative" means no retry loop, not no stale-phase guard. The WHERE guard should be added; the retry loop should not.

**CONFLICT-02: A-02/Q1 fix direction**
- fd-architecture: remove guard from `machine.Rollback`, keep in `store.RollbackPhase`
- fd-quality: remove from `store.RollbackPhase`, keep in `machine.Rollback`
- Resolution: fd-architecture direction. The established intercore pattern is that store enforces structural invariants and machine enforces workflow policy. The terminal-status check is a structural invariant (the run must not be in a finalized state before writing).

---

## Summary Table

| Severity | Count | Top Finding |
|----------|-------|-------------|
| HIGH | 2 | C-01: no cross-store transaction; C-02: TOCTOU double-read |
| MEDIUM | 6 | C-03: silent partial failure; A-01: CLI-layer orchestration; A-02/Q1: duplicate guard |
| P3/IMP | 10 | artifact status constants, migration guard comment, version bump mismatch, etc. |
| Conflicts | 2 | TOCTOU design intent; terminal-guard removal direction |

---

## Output Files

- Synthesis report: `/root/projects/Interverse/.clavain/quality-gates/synthesis.md`
- Findings JSON: `/root/projects/Interverse/.clavain/quality-gates/findings.json`
- Verdict files: `/root/projects/Interverse/.clavain/verdicts/fd-architecture.json`, `fd-quality.json`, `fd-correctness.json`
- Agent reports: `/root/projects/Interverse/.clavain/quality-gates/fd-architecture.md`, `fd-quality.md`, `fd-correctness.md`
