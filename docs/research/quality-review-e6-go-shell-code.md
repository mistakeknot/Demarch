# Quality Review: E6 Rollback and Recovery

**Date:** 2026-02-20
**Reviewer:** Flux-drive Quality & Style Reviewer
**Scope:** 12 files — Go 1.22 + Bash (lib-intercore.sh, test-integration.sh)
**Diff source:** `/tmp/qg-diff-1771610037.txt`

---

## Project Context

intercore is a Go CLI (`ic`) backed by a single SQLite WAL database. Key constraints:
- `SetMaxOpenConns(1)` — all DB access is serialized
- Error wrapping with `%w` is the project convention
- Exit codes: 0=success, 1=not-found, 2=error, 3=usage
- Store layer owns persistence; machine layer owns lifecycle policy
- `modernc.org/sqlite` (pure Go, no CGO) — no `UPDATE ... RETURNING` in CTEs

---

## Overall Assessment

**Verdict: needs-changes**

The E6 rollback implementation is architecturally sound. The phase-rewind path is intentionally authoritative (no optimistic concurrency), the audit trail is fully preserved, the artifact and agent cleanup follows the commit order correctly, and integration test coverage across 19 test cases is comprehensive. Two medium-severity issues need resolution before merge. The remaining findings are low or informational.

---

## Universal Quality Checks

### Naming Consistency

All new identifiers follow project conventions:
- `CancelByRun`, `MarkArtifactsRolledBack`, `FailAgentsByRun` — verb+noun, exported, consistent with existing `CountArtifacts`, `ListArtifacts`
- `CodeRollbackEntry` — clear noun for a projection struct
- `cmdRunRollback`, `cmdRunRollbackWorkflow`, `cmdRunRollbackCode` — matches `cmdRunCancel`, `cmdRunStatus` pattern
- `intercore_run_rollback`, `intercore_run_rollback_dry`, `intercore_run_code_rollback` — snake_case, matches all existing wrapper names
- `ErrInvalidRollback`, `ErrTerminalRun` — error sentinel naming matches `ErrNotFound`, `ErrStalePhase`

No naming issues found.

### File Organization

All new code is placed in the correct packages:
- Phase machine logic in `internal/phase/machine.go`
- Store methods in `internal/phase/store.go` and `internal/runtrack/store.go`
- CLI routing in `cmd/ic/run.go`
- Shell wrappers in `lib-intercore.sh`

No ad-hoc structure introduced.

### API Design Consistency

`Rollback` follows the signature pattern of `Advance`: `(ctx, store, runID, ..., callback)` returning `(*Result, error)`. The `PhaseEventCallback` type is reused. `RollbackResult` mirrors `AdvanceResult`. The dual-mode dispatch in `cmdRunRollback` (`--layer=code` vs `--to-phase`) is routed cleanly with early returns and clear usage messages.

### Test Strategy

Test coverage is appropriate to risk level:
- Unit tests for `RollbackPhase` cover: success, forward-target rejection, completed-run reversion
- Machine tests cover: basic rollback, terminal-run rejection, rolled-back-phases count
- Store tests cover: `MarkArtifactsRolledBack` (success, empty-phases guard), `FailAgentsByRun`, `ListArtifactsForCodeRollback`
- Integration tests cover 8 distinct scenarios including dry-run, completed-run reversion, cancelled-run rejection, forward-target rejection, and all three bash wrappers

The test strategy matches the risk level (write path + audit trail).

### Dependency Discipline

No new Go dependencies introduced. No new shell dependencies.

---

## Go-Specific Findings

### Q1. MEDIUM — Duplicate terminal-status guard and extra Get in RollbackPhase

**Files:** `internal/phase/machine.go:340-342`, `internal/phase/store.go:498-507`

`machine.go:Rollback` already fetches the run (line 334) and checks for terminal status (lines 340-342) before calling `store.RollbackPhase`. Inside `RollbackPhase`, `store.go:498-507` then calls `s.Get(ctx, id)` a second time and repeats the exact same `StatusCancelled || StatusFailed` guard. This is a layering violation: the machine owns lifecycle policy; the store owns persistence. The duplicate guard in the store also means a third `Get` call will execute (the run was also fetched in `cmdRunRollbackWorkflow:107` for dry-run validation).

The established pattern elsewhere in the codebase is that `UpdatePhase` (store) does not re-fetch or re-validate status — it trusts the machine to have done so. `RollbackPhase` should follow the same contract.

**Recommended fix:**

Option A (preferred): Remove the `Get` and terminal-status guard from `RollbackPhase`. The store-layer validation of chain membership (ChainContains, ChainPhaseIndex) can use the already-fetched run passed in:

```go
// RollbackPhase rewinds a run's phase pointer backward.
// Caller is responsible for status validation; this method validates chain membership only.
func (s *Store) RollbackPhase(ctx context.Context, id, currentPhase, targetPhase string, chain []string) error {
    if !ChainContains(chain, targetPhase) {
        return fmt.Errorf("rollback: target phase %q not in chain", targetPhase)
    }
    // ... index validation, then UPDATE
}
```

Option B: Keep the store-layer guard as defence-in-depth but document that explicitly and pass the run in to avoid the second `Get`:

```go
func (s *Store) RollbackPhase(ctx context.Context, run *Run, targetPhase string) error {
    if run.Status == StatusCancelled || run.Status == StatusFailed {
        return ErrTerminalRun // defence-in-depth; machine should have checked first
    }
    // ...
}
```

Either option removes one DB round-trip per rollback.

---

### Q2. MEDIUM — enc.Encode return value discarded in all JSON output paths

**File:** `cmd/ic/run.go:131-134` (dry-run), `:198-200` (workflow), `:256-258` (code query)

All three JSON output paths call `enc.Encode(output)` without checking the error return. While `json.Encoder.Encode` rarely fails for `map[string]interface{}` with simple value types, a full pipe buffer or a closed stdout will return a non-nil error that is silently swallowed. The downstream consumer then receives truncated JSON with no signal.

Other `cmdRun*` functions in the codebase (e.g., `cmdRunStatus`, `cmdRunTokens`) also discard this — it is a shared weakness — but rollback output is consumed by automation (bash wrappers pipe it through `jq`), making silent truncation particularly harmful.

**Recommended fix (consistent with project error pattern):**

```go
if err := enc.Encode(output); err != nil {
    fmt.Fprintf(os.Stderr, "ic: run rollback: encode output: %v\n", err)
    // Do not return non-zero — the encode error is usually an I/O error on the
    // caller's end, not a rollback failure. Log and continue.
}
```

Or if the project decides to treat this as fatal: `return 2`.

---

### Q3. LOW — Exit code 1 conflates "not found" with "terminal run rejection"

**File:** `cmd/ic/run.go:110-114` (not found → exit 1), `:157-159` (terminal run → exit 1)

The project exit-code contract is: 0=success, 1=not-found, 2=error, 3=usage. A cancelled run that cannot be rolled back is a valid run that exists — it is not "not found". Returning exit 1 for both conditions means a Bash caller doing `ic run rollback "$id" ... || handle_error` cannot distinguish "that run ID doesn't exist" from "that run is cancelled and cannot be rolled back."

```bash
# Bash caller cannot distinguish these today:
ic run rollback $id --to-phase=brainstorm  # exit 1: run not found
ic run rollback $id --to-phase=brainstorm  # exit 1: run is cancelled (terminal)
```

**Recommended:** Return exit 2 for `ErrTerminalRun` (a semantic error, not a lookup failure). This is consistent with how `ErrTerminalRun` is handled in `cmdRunAdvance` (returns exit 2).

---

### Q4. LOW — Redundant Get call inside RollbackPhase store method

**File:** `internal/phase/store.go:498-501`

This is a consequence of Q1 but worth noting independently. With `SetMaxOpenConns(1)`, every `Get` acquires the exclusive connection. A rollback that goes through `cmdRunRollbackWorkflow` executes:

1. `pStore.Get` at cmd/ic/run.go:107 (dry-run validation)
2. `store.Get` at machine.go:334 (status check inside `Rollback`)
3. `s.Get` at store.go:499 (inside `RollbackPhase`)

That is three reads of the same row in a single request. Eliminating the store-layer `Get` (as per Q1) reduces this to two, which is still one more than necessary but acceptable given the validation at different scopes.

---

### Q5. LOW — MarkArtifactsRolledBack silent idempotency undocumented

**File:** `internal/runtrack/store.go:730`

```go
"UPDATE run_artifacts SET status = 'rolled_back' WHERE run_id = ? AND status = 'active' AND phase IN (%s)"
```

Only artifacts in `status='active'` are updated. Artifacts already in `status='rolled_back'` (from a prior rollback of the same phases) are silently skipped. The return count will be 0 for a re-rollback, which the caller in `cmdRunRollbackWorkflow` displays in the JSON output as `"marked_artifacts": 0`. A consumer might interpret this as "nothing was done" rather than "everything was already in the correct state."

The behavior is correct and idempotent by design, but the doc comment should state this explicitly:

```go
// MarkArtifactsRolledBack sets status='rolled_back' on artifacts in the given phases
// that are currently status='active'. Already-rolled-back artifacts are skipped
// (idempotent). Returns the count of newly updated artifacts.
```

---

## Shell-Specific Findings

### Q6. LOW — intercore_run_rollback suppresses stderr unconditionally

**File:** `lib-intercore.sh:995`

```bash
"$INTERCORE_BIN" "${args[@]}" ${INTERCORE_DB:+--db="$INTERCORE_DB"} 2>/dev/null
```

All stderr from `ic run rollback` is redirected to `/dev/null`. This swallows actionable error messages such as "target phase is not behind current phase" and "run not found". The `intercore_available` guard prevents "binary missing" noise, but that does not justify suppressing semantic errors. The project pattern in `intercore_dispatch_tokens` also uses `2>/dev/null` — this is a shared weakness, but rollback failure is higher stakes.

At minimum, `intercore_run_rollback_dry` (the preview function) should preserve stderr so callers can see why a preview rejected the target. For the mutating wrappers, consider routing stderr to a log file or preserving it with a conditional `${INTERCORE_SILENT:+2>/dev/null}` pattern.

**Quoting:** All variable expansions in the new functions use double-quotes or arrays correctly. The `${INTERCORE_DB:+--db="$INTERCORE_DB"}` pattern is used consistently. No quoting issues found.

**Strict mode:** `lib-intercore.sh` is sourced, not executed standalone, so the absence of `set -euo pipefail` is expected and correct.

---

## Test-Specific Findings

### Q7. INFO — TestStore_FailAgentsByRun missing per-agent assertion for id2

**File:** `internal/runtrack/store_test.go:895-901`

```go
for _, a := range agents {
    if a.ID == id1 && a.Status != StatusFailed {
        t.Errorf("agent %s status = %q, want failed", a.ID, a.Status)
    }
    if a.ID == id3 && a.Status != StatusCompleted {
        t.Errorf("completed agent %s status = %q, want completed (unchanged)", a.ID, a.Status)
    }
}
```

Agent `id2` (second active agent, unlabeled in the test) is never explicitly asserted. The `count == 2` check at line 885 verifies the SQL updated two rows, but does not verify which rows. If a future refactor changes the `WHERE` clause to match differently, the count check alone would not catch it.

**Recommended:** Add an explicit check for `id2`:

```go
if a.ID == id2 && a.Status != StatusFailed {
    t.Errorf("agent %s status = %q, want failed", a.ID, a.Status)
}
```

(Where `id2` is captured from the return of the second `store.AddAgent` call.)

### Q8. INFO — TestStore_MarkArtifactsRolledBack does not test re-rollback idempotency

**File:** `internal/runtrack/store_test.go:820-855`

The idempotency of `MarkArtifactsRolledBack` (already-rolled-back artifacts get count=0 on a second call) is not tested. Given the undocumented behavior flagged in Q5, a test like:

```go
// Second call should be idempotent — already rolled_back artifacts not re-counted
count2, err := store.MarkArtifactsRolledBack(ctx, "testrun1", []string{"strategized", "planned"})
if count2 != 0 {
    t.Errorf("idempotent call count = %d, want 0", count2)
}
```

would both document and guard this behavior.

### Q9. INFO — test-integration.sh seq expansion style

**File:** `test-integration.sh:1092`

```bash
for i in $(seq 9); do
```

The script uses `$(seq 9)` rather than `{1..9}` (bash brace expansion). Both are correct and `seq` is available in this environment. Minor inconsistency with the `# shellcheck shell=bash` annotation since `{1..9}` is more idiomatic for bash and avoids a subprocess. No correctness risk.

---

## Improvements (non-blocking)

**I1. Pass run struct into RollbackPhase to eliminate the extra Get**

`RollbackPhase(ctx, run *Run, targetPhase string)` would let the machine pass the already-fetched run, removing one DB round-trip and making chain validation operate on data already in memory.

**I2. Consolidate the two-branch query in ListArtifactsForCodeRollback**

The `if filterPhase != nil` branch duplicates the full query body. A single parameterized query:

```sql
WHERE a.run_id = ? AND (? IS NULL OR a.phase = ?)
```

would reduce duplication, though the current approach is explicit and readable with no performance difference on SQLite.

**I3. Distinct stderr messages for ErrTerminalRun vs ErrNotFound**

Even if exit codes remain the same (a separate decision), the stderr messages could differ:
- Not found: `"ic: run rollback: not found: %s\n"`
- Terminal: `"ic: run rollback: cannot rollback cancelled/failed run: %s\n"`

This gives Bash callers log-level signal even without exit-code differentiation.

**I4. Document no-optimistic-concurrency rationale in RollbackPhase store method**

The machine.go docstring for `Rollback` explains this clearly. The store method `RollbackPhase` has only a one-line note. Adding the rationale inline ("rollback is authoritative — a concurrent advance that raced here is expected to lose") would prevent the question from recurring during code review.

---

## Summary of Severity Distribution

| Severity | Count |
|---|---|
| MEDIUM | 2 |
| LOW | 4 |
| INFO | 3 |

The two medium issues (duplicate store-layer guard with extra Get, and silently discarded encode errors) should be addressed before merge. The low findings can be resolved in a follow-up or alongside the medium fixes. The informational findings are for awareness only.
