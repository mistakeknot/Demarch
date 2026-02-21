# PRD: Intercore E8 — Cross-Project Portfolio Runs

**Bead:** iv-b1os

## Problem

Intercore manages runs scoped to individual projects. When coordinated work spans multiple projects (e.g., shipping an SDK update across interbase + intermute + 3 plugins), there is no kernel-level orchestration. Higher layers must manually coordinate, losing auditability and making cross-project gates impossible.

## Solution

Add portfolio runs — a parent run that tracks child runs across multiple projects, with aggregated gates, cross-project event relay, and portfolio-level resource budgets.

## Features

### F1: Portfolio Run Schema (P0)
Add `parent_run_id TEXT` (nullable FK) to `runs` table. Portfolio runs have `project_dir = ''` and children linked via `parent_run_id`. Add `max_dispatches INT` field for concurrent dispatch limits.

**Schema migration (v9→v10):**
```sql
ALTER TABLE runs ADD COLUMN parent_run_id TEXT REFERENCES runs(id);
ALTER TABLE runs ADD COLUMN max_dispatches INTEGER DEFAULT 0;
```

**Acceptance:**
- Migration runs cleanly on existing DBs
- `parent_run_id` is queryable; children retrievable via `SELECT * FROM runs WHERE parent_run_id = ?`
- Existing runs unaffected (parent_run_id is NULL)

### F2: Portfolio CLI — Create + Status (P0)
`ic run create --projects=a,b --goal="..."` creates a portfolio run + N child runs atomically.

**Behavior:**
1. Create portfolio run (project_dir='', phases from default chain)
2. For each project: create child run with `parent_run_id` pointing to portfolio
3. Return portfolio ID + child IDs
4. `ic run status <portfolio-id>` shows portfolio + children summary
5. `ic run list --portfolio` lists portfolio runs only

**Acceptance:**
- `ic run create --projects=/p1,/p2 --goal="test"` creates 3 runs (1 portfolio + 2 children)
- `ic run status <portfolio-id> --json` includes `children` array
- `ic run list --portfolio` filters to portfolio-only runs

### F3: Project Dependencies Table (P1)
Add `project_deps` table to track inter-project dependency edges within a portfolio.

**Schema:**
```sql
CREATE TABLE project_deps (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    portfolio_run_id TEXT NOT NULL REFERENCES runs(id),
    upstream_project TEXT NOT NULL,
    downstream_project TEXT NOT NULL,
    created_at INTEGER NOT NULL DEFAULT (unixepoch())
);
```

**CLI:**
- `ic portfolio dep add <portfolio-id> --upstream=/p1 --downstream=/p2`
- `ic portfolio dep list <portfolio-id>`

**Acceptance:**
- Dependencies stored and retrievable
- Duplicate (portfolio, upstream, downstream) tuples rejected

### F4: Portfolio Gate — Children At Phase (P1)
New gate condition: `children_at_phase` — portfolio can only advance when all child runs are at or past the portfolio's target phase.

**Behavior:**
- Gate evaluator loads all child runs for portfolio
- Checks each child's current phase index >= portfolio's target phase index
- If any child is behind: gate fails with evidence listing which children are behind
- `ic gate check <portfolio-id>` shows aggregated result

**Gate rule additions:**
- For portfolio runs (parent_run_id IS NULL AND project_dir = ''), add `children_at_phase` as a hard gate on every phase transition

**Acceptance:**
- Portfolio with 2 children: both at phase 3 → portfolio gate for phase 3 passes
- Portfolio with 2 children: one at phase 2, one at phase 3 → portfolio gate for phase 3 fails
- `ic gate check <portfolio-id>` returns evidence listing child run IDs and their phases

### F5: Portfolio Event Relay (P2)
Poll child run events and aggregate into portfolio's event stream. Emit `dependency.upstream_changed` when relevant.

**Behavior:**
- `ic portfolio relay <portfolio-id>` runs a polling loop (default 2s interval)
- Reads child runs' phase_events and dispatch_events from their project DBs
- Writes relay entries to portfolio DB with source attribution (source_project, source_run_id)
- When a child run advances past a dependency-relevant phase, check project_deps and emit `dependency.upstream_changed` event to downstream child runs

**Event types added:**
- `portfolio.child_advanced` — child run advanced a phase
- `portfolio.child_completed` — child run reached terminal phase
- `dependency.upstream_changed` — upstream dependency satisfied

**Acceptance:**
- Relay correctly polls 2+ project DBs
- Events from children appear in `ic events tail <portfolio-id>`
- `dependency.upstream_changed` fires when upstream child advances past dependency phase

### F6: Max Concurrent Dispatches (P2)
Enforce `max_dispatches` limit across all child runs in a portfolio.

**Behavior:**
- Before `ic dispatch spawn`, if the run has a `parent_run_id`, query the portfolio's `max_dispatches`
- Count active dispatches across all sibling runs: `SELECT COUNT(*) FROM dispatches WHERE status IN ('spawned','running') AND scope_id IN (SELECT id FROM runs WHERE parent_run_id = ?)`
- If count >= max_dispatches and max_dispatches > 0: reject spawn with exit code 1 and message
- `ic run set <portfolio-id> --max-dispatches=5` sets the limit

**Acceptance:**
- Portfolio with max_dispatches=2, 2 active dispatches → third spawn rejected
- Portfolio with max_dispatches=0 (unlimited) → no limit enforced
- Budget enforcement works across child runs in different project DBs

## Non-goals (E8.5+)
- Cross-project dependency graph with transitive closure
- Quorum-based portfolio gates (M-of-N)
- Dispatch priority/preemption across portfolio
- Automatic portfolio creation from beads epics
- Long-running relay as systemd service (MVP: `ic portfolio relay` foreground process)

## Dependencies
- E5 (discovery) — shipped
- E6 (rollback) — shipped
- No blockers

## Technical Constraints
- Portfolio DB uses same SQLite + modernc.org/sqlite driver as project DBs
- Portfolio DB path: `.clavain/intercore.db` in workspace root (same as project DB, but portfolio runs have `project_dir=''`)
- Single-writer constraint: relay loop must not conflict with other `ic` commands on same DB
- Migration must be backward-compatible (new columns with defaults)

## Risks
- **Cross-DB queries**: Relay needs to open multiple SQLite DBs simultaneously. modernc.org/sqlite supports multiple connections but we use `SetMaxOpenConns(1)` per DB.
- **Stale relay data**: Polling introduces lag. For MVP this is acceptable (2s resolution matches Bigend).
- **Portfolio DB location**: If portfolio runs share the same DB as project runs, need to handle `project_dir=''` correctly in existing queries that filter by project_dir.
