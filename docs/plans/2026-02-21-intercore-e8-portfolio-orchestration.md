# Implementation Plan: E8 — Cross-Project Portfolio Runs

**Bead:** iv-b1os
**PRD:** `docs/prds/2026-02-21-intercore-e8-portfolio-orchestration.md`

## Overview

Add portfolio runs to Intercore — a parent run that tracks child runs across multiple projects with aggregated gates, cross-project dependencies, and resource budgets.

## Phase 0: Schema Migration (v9→v10)

### P0.1: Add columns to `runs` table

**File:** `internal/db/schema.sql`
- Add to runs table definition: `parent_run_id TEXT, max_dispatches INTEGER DEFAULT 0`

**File:** `internal/db/db.go`
- Bump `currentSchemaVersion` and `maxSchemaVersion` from 9 to 10
- Add v9→v10 migration block:
```go
if currentVersion >= 9 && currentVersion < 10 {
    v10Stmts := []string{
        "ALTER TABLE runs ADD COLUMN parent_run_id TEXT",
        "ALTER TABLE runs ADD COLUMN max_dispatches INTEGER DEFAULT 0",
    }
    // ... same isDuplicateColumnError guard pattern
}
```

### P0.2: Add `project_deps` table

**File:** `internal/db/schema.sql`
```sql
CREATE TABLE IF NOT EXISTS project_deps (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    portfolio_run_id    TEXT NOT NULL REFERENCES runs(id),
    upstream_project    TEXT NOT NULL,
    downstream_project  TEXT NOT NULL,
    created_at          INTEGER NOT NULL DEFAULT (unixepoch()),
    UNIQUE(portfolio_run_id, upstream_project, downstream_project)
);
CREATE INDEX IF NOT EXISTS idx_project_deps_portfolio ON project_deps(portfolio_run_id);
```

### P0.3: Add index for parent_run_id queries

**File:** `internal/db/schema.sql`
```sql
CREATE INDEX IF NOT EXISTS idx_runs_parent ON runs(parent_run_id) WHERE parent_run_id IS NOT NULL;
```

**Tests:** `internal/db/db_test.go` — add `TestMigrate_V9ToV10` verifying columns exist after migration.

**Commit:** `feat(intercore): schema v10 — portfolio run columns + project_deps (E8 P0)`

---

## Phase 1: Portfolio Run Model (F1+F2)

### P1.1: Extend Run struct

**File:** `internal/phase/phase.go`
- Add to `Run` struct:
```go
ParentRunID   *string
MaxDispatches int
```

**File:** `internal/phase/store.go`
- Update `Create()` INSERT to include `parent_run_id, max_dispatches`
- Update `Get()` SELECT to scan `parent_run_id, max_dispatches`
- Update `List()` and `ListActive()` to scan new columns

### P1.2: Add portfolio query methods

**File:** `internal/phase/store.go`
- `GetChildren(ctx, parentRunID) ([]*Run, error)` — `SELECT * FROM runs WHERE parent_run_id = ?`
- `IsPortfolio(ctx, runID) (bool, error)` — check if run has children (or project_dir is empty)
- `GetPortfolioParent(ctx, runID) (*Run, error)` — follow parent_run_id to get portfolio run

### P1.3: Portfolio create CLI

**File:** `cmd/ic/run.go`
- Add `--projects` flag to `cmdRunCreate`: comma-separated project paths
- When `--projects` is set:
  1. Create portfolio run with `project_dir = ""`, `parent_run_id = nil`
  2. For each project: create child run with `parent_run_id = portfolio.ID`
  3. Output portfolio ID + child IDs

### P1.4: Portfolio status in `ic run status`

**File:** `cmd/ic/run.go`
- In `cmdRunStatus`, if run has children (check `GetChildren`), append children summary
- JSON output: add `"children"` array with child run summaries
- Text output: add "Children:" section with per-child status line

### P1.5: `ic run list --portfolio` filter

**File:** `cmd/ic/run.go`
- Add `--portfolio` flag to `cmdRunList`
- When set, filter to runs where `project_dir = ''` (portfolio runs have empty project_dir)

### P1.6: Review-driven fixes

- **Atomic portfolio creation:** Wrap portfolio + children creation in a single DB transaction. Add `CreatePortfolio(ctx, portfolio *Run, children []*Run) (string, []string, error)` that does BEGIN/INSERT portfolio/INSERT children/COMMIT.
- **Guard `Current()` against empty project_dir:** Add `if projectDir == "" { return nil, ErrEmptyProject }` to prevent matching portfolio runs.
- **Event type naming:** Use existing flat naming convention (`child_advanced`, `child_completed`, `upstream_changed`) — no dots.
- **Cancel cascade:** `ic run cancel <portfolio-id>` should also cancel all active child runs. Add `CancelPortfolio(ctx, portfolioRunID)` that cancels portfolio + children + their dispatches.
- **HookHandler guard:** Skip hook execution for portfolio runs (ProjectDir is empty, no hooks to run).

**Tests:** `internal/phase/store_test.go` — `TestCreatePortfolioRun`, `TestGetChildren`, `TestIsPortfolio`, `TestCurrentRejectsEmpty`, `TestCancelPortfolioCascade`

**Commit:** `feat(intercore): portfolio run model + CLI (E8 F1+F2)`

---

## Phase 2: Project Dependencies (F3)

### P2.1: Dependencies store

**File:** `internal/portfolio/deps.go` (new)
```go
package portfolio

type DepStore struct { db *sql.DB }

func NewDepStore(db *sql.DB) *DepStore
func (s *DepStore) Add(ctx, portfolioRunID, upstream, downstream string) error
func (s *DepStore) List(ctx, portfolioRunID string) ([]Dep, error)
func (s *DepStore) Remove(ctx, portfolioRunID, upstream, downstream string) error
func (s *DepStore) GetDownstream(ctx, portfolioRunID, upstream string) ([]string, error)
```

### P2.2: Dependencies CLI

**File:** `cmd/ic/portfolio.go` (new)
- `ic portfolio dep add <portfolio-id> --upstream=/p1 --downstream=/p2`
- `ic portfolio dep list <portfolio-id>`
- `ic portfolio dep remove <portfolio-id> --upstream=/p1 --downstream=/p2`

**File:** `cmd/ic/main.go`
- Add `portfolio` to command dispatch in `run()`
- Add help text for portfolio subcommands

**Tests:** `internal/portfolio/deps_test.go` — `TestAddDep`, `TestListDeps`, `TestDuplicateRejected`, `TestGetDownstream`

**Commit:** `feat(intercore): project dependency graph (E8 F3)`

---

## Phase 3: Portfolio Gates (F4)

### P3.1: Add `children_at_phase` gate condition

**File:** `internal/phase/gate.go`
- Add new gate check type: `CheckChildrenAtPhase`
- Implementation: query all child runs for portfolio, check each child's phase index >= target phase index in the **child's own** chain
- **Phase chain constraint:** Children should use the same phase chain as the portfolio. If a child has a different chain, compare by phase **name** — if the target phase name doesn't exist in the child's chain, treat that child as "past" the phase (it never had it)
- Evidence includes list of child run IDs that are behind

### P3.2: Register portfolio gate rules

**File:** `internal/phase/gate.go`
- In gate rules map, for portfolio runs (detected by `project_dir == ""`), add `children_at_phase` as a hard gate on every phase transition
- Gate evaluation needs to know if a run is a portfolio — pass `isPortfolio bool` to `evaluateGate` or check `run.ProjectDir == ""`

### P3.3: Interface for children query

The gate evaluator needs to query children. Add to the existing querier interfaces:
**File:** `internal/phase/gate.go`
- Extend `RuntrackQuerier` or add new `PortfolioQuerier` interface:
```go
type PortfolioQuerier interface {
    GetChildren(ctx context.Context, runID string) ([]*Run, error)
}
```
- Pass to `evaluateGate` when available

**Tests:** `internal/phase/gate_test.go` — `TestPortfolioGate_AllChildrenPass`, `TestPortfolioGate_ChildBehind`, `TestPortfolioGate_NonPortfolioSkipped`

**Commit:** `feat(intercore): portfolio gates — children_at_phase (E8 F4)`

---

## Phase 4: Event Relay (F5)

### P4.1: Relay loop

**File:** `internal/portfolio/relay.go` (new)
```go
package portfolio

type Relay struct {
    portfolioID string
    store       *phase.Store
    depStore    *DepStore
    interval    time.Duration
    cursors     map[string]int64  // project_dir → last event ID
}

func NewRelay(portfolioID string, store *phase.Store, depStore *DepStore, interval time.Duration) *Relay
func (r *Relay) Run(ctx context.Context) error  // blocking loop
func (r *Relay) poll(ctx context.Context) error  // single poll cycle
```

**Behavior per cycle:**
1. Load portfolio and children from store
2. For each child: open child's project DB (read-only), query phase_events since cursor
3. For each new event: write to portfolio's phase_events with `reason = "relay:<source_project>"`
4. Check project_deps: if child advanced past a phase that's an upstream dependency, emit `dependency.upstream_changed` event

### P4.2: New event types

**File:** `internal/phase/phase.go` or `internal/event/types.go`
- Add event type constants: `EventPortfolioChildAdvanced`, `EventPortfolioChildCompleted`, `EventDependencyUpstreamChanged`

### P4.3: Relay CLI

**File:** `cmd/ic/portfolio.go`
- `ic portfolio relay <portfolio-id> [--interval=2s]` — runs the relay loop
- Exits cleanly on SIGINT/SIGTERM
- Logs events as they're relayed

### P4.4: Cross-DB access helper

**File:** `internal/portfolio/dbpool.go` (new)
- Helper to open project DBs **read-only** for relay queries
- Use `?mode=ro` in DSN to enforce read-only at SQLite level
- Set longer busy_timeout (500ms vs default 100ms) since relay is background
- **Absolute path enforcement:** Validate child `project_dir` values are absolute paths; reject relative paths
- Cache open DB handles, close all on relay shutdown
- Handle missing DBs gracefully (child project may not have run `ic init` yet)

### P4.5: Persist relay cursors

**File:** `internal/portfolio/relay.go`
- Store cursors in the portfolio DB's `state` table: key=`relay-cursor`, scope_id=`<project_dir>`
- On startup, load cursors from state table (avoids replaying all events on crash/restart)
- Update cursor after each successful poll cycle

**Tests:** `internal/portfolio/relay_test.go` — `TestRelayPollsChildEvents`, `TestRelayEmitsDependencyEvent`, `TestRelayCursorPersistence`

**Commit:** `feat(intercore): portfolio event relay (E8 F5)`

---

## Phase 5: Max Concurrent Dispatches (F6)

### P5.1: Budget check in dispatch spawn

**File:** `internal/dispatch/dispatch.go`
- In `Create()` or `Spawn()`, before INSERT:
  1. Check if dispatch's run has a `parent_run_id`
  2. If so, load portfolio run's `max_dispatches`
  3. If max_dispatches > 0, count active dispatches across all sibling runs
  4. If at limit, return a new error `ErrDispatchLimitReached`

### P5.2: `ic run set --max-dispatches`

**File:** `cmd/ic/run.go`
- Add `--max-dispatches` flag to `cmdRunSet`
- Only valid for portfolio runs (reject for non-portfolio with error message)

### P5.3: Portfolio dispatch count via relay-maintained cache

The dispatch count cannot use a simple local query — child dispatches live in each child project's DB. Instead:

**Approach: Relay-maintained counter in portfolio DB state table.**

**File:** `internal/portfolio/relay.go`
- During each relay poll cycle, count active dispatches per child project DB
- Write total to portfolio DB's `state` table: key=`active-dispatch-count`, scope_id=`<portfolio_run_id>`

**File:** `internal/dispatch/dispatch.go`
- In dispatch creation path, if run has `parent_run_id`:
  1. Load portfolio run to get `max_dispatches`
  2. Read `active-dispatch-count` from state table (O(1) local read)
  3. If count >= max_dispatches and max_dispatches > 0: return `ErrDispatchLimitReached`
- **Staleness tolerance:** Counter is up to 2s stale (relay poll interval). Accept ~2s burst window — it's a budget hint, not a hard lock.

**File:** `cmd/ic/run.go`
- When relay is NOT running, dispatch spawn skips the limit check (degrade gracefully instead of blocking)

**Tests:** `internal/dispatch/dispatch_test.go` — `TestDispatchLimitEnforced`, `TestDispatchLimitUnlimited`, `TestDispatchLimitNoRelay`

**Commit:** `feat(intercore): portfolio max-dispatches enforcement (E8 F6)`

---

## Phase 6: Help Text + Integration Test

### P6.1: Update main.go help

**File:** `cmd/ic/main.go`
- Add portfolio commands to help text
- Add `--projects` and `--max-dispatches` to run create help

### P6.2: Integration test

**File:** `test-portfolio-integration.sh` (new)
- End-to-end: create portfolio with 2 projects, add dependency, advance children, check portfolio gate, verify relay events

### P6.3: Update CLAUDE.md + AGENTS.md

**File:** `CLAUDE.md`
- Add Portfolio Quick Reference section

**Commit:** `docs(intercore): portfolio orchestration docs + integration test (E8 P6)`

---

## File Inventory

| File | Action | Phase |
|------|--------|-------|
| `internal/db/schema.sql` | edit | P0 |
| `internal/db/db.go` | edit | P0 |
| `internal/db/db_test.go` | edit | P0 |
| `internal/phase/phase.go` | edit | P1 |
| `internal/phase/store.go` | edit | P1 |
| `internal/phase/store_test.go` | edit | P1 |
| `cmd/ic/run.go` | edit | P1, P5 |
| `internal/portfolio/deps.go` | new | P2 |
| `internal/portfolio/deps_test.go` | new | P2 |
| `cmd/ic/portfolio.go` | new | P2, P4 |
| `cmd/ic/main.go` | edit | P2, P6 |
| `internal/phase/gate.go` | edit | P3 |
| `internal/phase/gate_test.go` | edit | P3 |
| `internal/portfolio/relay.go` | new | P4 |
| `internal/portfolio/dbpool.go` | new | P4 |
| `internal/portfolio/relay_test.go` | new | P4 |
| `internal/dispatch/dispatch.go` | edit | P5 |
| `internal/dispatch/store.go` | edit | P5 |
| `internal/dispatch/dispatch_test.go` | edit | P5 |
| `test-portfolio-integration.sh` | new | P6 |
| `CLAUDE.md` | edit | P6 |

## Estimated Scope

- ~8 existing files modified, ~7 new files
- ~600-800 lines of new Go code + ~400 lines of tests
- Schema migration is low-risk (additive columns + new table)
- Relay is the most complex piece (cross-DB polling)
