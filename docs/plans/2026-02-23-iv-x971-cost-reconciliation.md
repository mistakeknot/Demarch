# Plan: Cost Reconciliation — billing vs self-reported token verification

**Bead:** iv-x971
**Date:** 2026-02-23
**Complexity:** 2/5 (simple)

## Context

Token tracking per dispatch is shipped (`input_tokens`, `output_tokens`, `cache_hits` on `dispatches` table, aggregation via `AggregateTokens`, budget checking via `budget.Checker`). What's missing is **verification** — the ability to compare what agents self-report vs what actually gets billed (e.g., from Anthropic's billing API).

The kernel records contracts and telemetry; the OS provides billing API integration. This plan covers the kernel side only.

## Tasks

### Task 1: Add `cost_reconciliations` table (schema v17)

**File:** `internal/db/schema.sql`

Add a new table:
```sql
CREATE TABLE IF NOT EXISTS cost_reconciliations (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id          TEXT NOT NULL,
    dispatch_id     TEXT,              -- NULL = run-level reconciliation
    reported_in     INTEGER NOT NULL,  -- self-reported input tokens
    reported_out    INTEGER NOT NULL,  -- self-reported output tokens
    billed_in       INTEGER NOT NULL,  -- billing API input tokens
    billed_out      INTEGER NOT NULL,  -- billing API output tokens
    delta_in        INTEGER NOT NULL,  -- billed_in - reported_in
    delta_out       INTEGER NOT NULL,  -- billed_out - reported_out
    source          TEXT NOT NULL DEFAULT 'manual', -- 'manual', 'anthropic', 'openai'
    created_at      INTEGER NOT NULL DEFAULT (unixepoch())
);
CREATE INDEX IF NOT EXISTS idx_cost_recon_run ON cost_reconciliations(run_id);
CREATE INDEX IF NOT EXISTS idx_cost_recon_dispatch ON cost_reconciliations(dispatch_id) WHERE dispatch_id IS NOT NULL;
```

**File:** `internal/db/db.go`

- Bump `currentSchemaVersion` and `maxSchemaVersion` from 16 to 17
- No ALTER TABLE migration needed — new table is created fresh by DDL

### Task 2: Add `cost.reconciliation_discrepancy` event type + store

**File:** `internal/budget/reconcile.go` (new)

```go
package budget

// Event type for reconciliation discrepancy
const EventCostDiscrepancy = "cost.reconciliation_discrepancy"

// Reconciliation holds the result of comparing reported vs billed tokens.
type Reconciliation struct {
    ID         int64
    RunID      string
    DispatchID string // empty = run-level
    ReportedIn int64
    ReportedOut int64
    BilledIn   int64
    BilledOut  int64
    DeltaIn    int64  // billed - reported
    DeltaOut   int64
    Source     string // "manual", "anthropic", "openai"
}

// ReconcileStore handles cost reconciliation CRUD.
type ReconcileStore struct { db *sql.DB }

func NewReconcileStore(db *sql.DB) *ReconcileStore

// Reconcile compares billed tokens against self-reported tokens.
// For run-level: aggregates all dispatches via AggregateTokens.
// For dispatch-level: reads single dispatch tokens.
// Records the reconciliation and emits discrepancy event if delta != 0.
func (s *ReconcileStore) Reconcile(ctx, runID, dispatchID, billedIn, billedOut int64, source string, recorder EventRecorder) (*Reconciliation, error)

// List returns reconciliations for a run, ordered by created_at desc.
func (s *ReconcileStore) List(ctx, runID string, limit int) ([]Reconciliation, error)
```

Key behaviors:
- Compute `delta_in = billed_in - reported_in`, same for out
- If either delta is non-zero, call `recorder(ctx, runID, EventCostDiscrepancy, reason)` where reason includes the delta amounts
- Insert the reconciliation row
- Return the Reconciliation struct

### Task 3: Add `ic cost reconcile` CLI command

**File:** `cmd/ic/cost.go` (new)

Add top-level `"cost"` case in `cmd/ic/main.go` switch:
```go
case "cost":
    exitCode = cmdCost(ctx, subArgs)
```

Subcommands:
- `ic cost reconcile <run_id> --billed-in=N --billed-out=N [--dispatch=<id>] [--source=manual]`
  - Opens DB, creates ReconcileStore, calls Reconcile
  - Outputs JSON or text with reported vs billed vs delta
  - Exit 0 if deltas are zero, exit 1 if discrepancy found
- `ic cost list <run_id> [--limit=N]`
  - Lists past reconciliations for the run

### Task 4: Tests

**File:** `internal/budget/reconcile_test.go` (new)

- `TestReconcileNoDelta` — matching tokens, no event emitted
- `TestReconcileWithDiscrepancy` — mismatched tokens, event emitted, delta computed correctly
- `TestReconcileDispatchLevel` — single dispatch reconciliation
- `TestReconcileList` — list reconciliations ordered by time

**File:** `internal/db/db_test.go`

- Add migration test for v16→v17 (verify `cost_reconciliations` table exists after migration)

### Task 5: Update CLAUDE.md quick reference

**File:** `CLAUDE.md`

Add `## Cost Quick Reference` section with `ic cost reconcile` and `ic cost list` usage examples.

## File Change Summary

| File | Change |
|------|--------|
| `internal/db/schema.sql` | Add `cost_reconciliations` table + indexes |
| `internal/db/db.go` | Bump schema version 16 → 17 |
| `internal/budget/reconcile.go` | New: ReconcileStore + Reconciliation type |
| `internal/budget/reconcile_test.go` | New: reconciliation unit tests |
| `internal/db/db_test.go` | Add v16→v17 migration test |
| `cmd/ic/cost.go` | New: `ic cost` CLI subcommand |
| `cmd/ic/main.go` | Add `case "cost"` routing |
| `CLAUDE.md` | Add cost quick reference |

## Non-goals

- Billing API integration (OS responsibility — Clavain or a dedicated module)
- Automatic periodic reconciliation (future work)
- Cost-based scheduling decisions (separate bead)
