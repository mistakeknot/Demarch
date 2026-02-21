# PRD: Portfolio-Level Dependency/Scheduling Primitives

**Bead:** iv-wp62

## Problem

Intercore E8 shipped portfolio orchestration with cross-project runs, dependency recording, and event relay. However, dependencies are notification-only: the relay emits `upstream_changed` events when upstreams advance, but nothing *prevents* a downstream from advancing before its upstream reaches the required phase. This makes the dependency graph decorative rather than enforced.

## Solution

Add dependency-aware gate conditions and scheduling queries to the portfolio package, making the dependency graph participate in the existing gate evaluation system. When a child run tries to advance, check whether all of its upstream dependencies have reached the target phase.

## Features

### F1: Cycle Detection in Dependency Add (P0)

Prevent cycles in the dependency graph. Currently only self-loops are rejected.

**Behavior:**
- When `ic portfolio dep add` is called, run DFS from downstream through existing edges
- If upstream is reachable from downstream, reject with error: "cycle detected: <path>"
- Use in-memory DFS — graph is small (typically <20 edges per portfolio)

**Acceptance:**
- `ic portfolio dep add P --upstream=A --downstream=B` succeeds
- `ic portfolio dep add P --upstream=B --downstream=A` fails with "cycle detected: A → B → A"
- `ic portfolio dep add P --upstream=A --downstream=C` + `ic portfolio dep add P --upstream=C --downstream=A` fails
- Self-loop still rejected (existing behavior preserved)

### F2: `CheckUpstreamsAtPhase` Gate Condition (P0)

New gate check type that blocks a child run's advance when any of its upstream dependencies haven't reached the target phase.

**Behavior:**
- During `evaluateGate()`, when a run has `parent_run_id` set, load the portfolio's dependency edges
- Find all upstreams for this child's project dir
- For each upstream, resolve its child run within the same portfolio and check its phase
- If any upstream child run is behind the target phase: gate fails with evidence listing which upstreams are behind
- The check fires on every child run advance attempt, not just portfolio-level advances

**Gate injection logic in `evaluateGate()`:**
```
if run.ParentRunID != "" && pq != nil:
    upstreams = deps.GetUpstream(portfolioRunID, run.ProjectDir)
    for each upstream:
        upstreamRun = find child run where project_dir = upstream
        if upstreamRun.phase < targetPhase:
            fail with evidence
```

**New interfaces needed:**
- `DepQuerier` — narrow interface: `GetUpstream(ctx, portfolioRunID, downstream) ([]string, error)`
- Added to `evaluateGate()` signature alongside existing `PortfolioQuerier`

**Tier:** Hard (P0-P1). The whole purpose of dependency edges is to prevent premature execution. Override via `--disable-gates`.

**Acceptance:**
- Portfolio with A→B dep: advance B past "executing" while A is at "planned" → gate blocked with evidence
- Portfolio with A→B dep: advance B past "executing" while A is at "executing" → gate passes
- Non-portfolio runs unaffected (no `parent_run_id`, check skipped)
- `ic gate check <child-run-id>` shows upstream gate evidence

### F3: `ic portfolio status` CLI Enhancement (P1)

Show each child's readiness status based on the dependency graph.

**Behavior:**
- `ic portfolio status <portfolio-id>` lists all children with:
  - Current phase
  - Dependency status: "ready" (all upstreams at or past current phase) or "blocked by: <upstream-projects>"
  - Active dispatch count
- `--json` flag for machine-readable output

**Acceptance:**
- Portfolio with A→B dep, A at "planned", B at "brainstorm": B shows "ready" (A is ahead)
- Portfolio with A→B dep, A at "planned", B at "executing": B shows "blocked by: A (planned < executing)"

### F4: `ic portfolio order` CLI — Topological Sort (P1)

Display the dependency-implied execution order.

**Behavior:**
- Compute topological sort of the dependency graph
- Print projects in dependency-respecting order (upstream first)
- Detect cycles (should be impossible if F1 works, but defense in depth)

**Acceptance:**
- A→B, A→C, B→C prints: A, B, C
- No deps prints all projects in alphabetical order
- Empty portfolio prints nothing

### F5: `IsChildReady` Query Function (P2)

Portfolio package function for readiness check. Used by higher layers (Clavain, Bigend) to determine which children can be advanced.

**Behavior:**
- `IsChildReady(ctx, portfolioRunID, childProjectDir, targetPhase) (bool, []BlockingUpstream, error)`
- Returns ready=true if all upstream deps are at or past `targetPhase`
- Returns list of blocking upstreams with their current phase when not ready
- Opens upstream DBs via DBPool (read-only) for cross-DB queries

**Acceptance:**
- Ready child returns (true, nil, nil)
- Blocked child returns (false, [{Project: "/a", CurrentPhase: "planned", RequiredPhase: "executing"}], nil)
- Missing upstream DB returns error (not false — distinguishes "upstream behind" from "upstream unreachable")

## Non-goals

- Phase-specific dependency triggers (e.g., "block B until A reaches specifically 'review'")
- Transitive closure queries
- Auto-advance on upstream unblock (event-driven scheduling)
- Priority-based scheduling among siblings
- Visual dependency graph rendering

## Technical Constraints

- Pure Go, no CGO (modernc.org/sqlite)
- `SetMaxOpenConns(1)` per DB
- Cross-DB reads via existing `DBPool` (read-only child handles)
- New gate condition must integrate via the existing interface injection pattern
- Schema change not needed — all data is already in `project_deps` table

## Risks

- **Cross-DB reads for gate evaluation:** Child advance needs to read the portfolio DB to check deps. If the child DB and portfolio DB are different files, this requires the advance command to open a second DB. Mitigation: for same-DB portfolios (most common case), this is a single SQL query. For cross-DB, use the existing DBPool.
- **Gate evaluation latency:** DFS cycle check and upstream phase lookup add latency to every child advance. Mitigation: graphs are small (<20 nodes), SQLite reads are fast (<1ms), total overhead is negligible.
