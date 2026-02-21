# Portfolio-Level Dependency/Scheduling Primitives

**Bead:** iv-wp62

## Problem Statement

Intercore's portfolio orchestration (E8) shipped cross-project runs, dependency recording, event relay, and portfolio-level gates. However, the dependency graph is **notification-only**: when an upstream project advances, the relay emits an `upstream_changed` event, but nothing *blocks* a downstream project from advancing before its upstream reaches the required phase.

The gap: dependencies can be recorded (`ic portfolio dep add`) and observed (relay events), but they don't produce **scheduling constraints**. A downstream child run can advance freely regardless of where its upstream dependency stands.

## Current State

### What E8 shipped
1. **`project_deps` table** — records (portfolio_run_id, upstream, downstream) edges
2. **`DepStore`** — CRUD for dependency edges (Add, List, Remove, GetDownstream, GetUpstream)
3. **Relay** — polls child DBs, emits `upstream_changed` events when an upstream project's run advances
4. **`CheckChildrenAtPhase` gate** — blocks portfolio advance until all children reach target phase
5. **Advisory dispatch limits** — `max_dispatches` field with TOCTOU-vulnerable enforcement

### What's missing
1. **Dependency-aware gates** — no gate condition that says "downstream X can't advance past phase Y until upstream Z is at phase Y"
2. **Scheduling primitives** — no `ic portfolio schedule` or readiness check based on dependency graph
3. **Topological ordering** — no way to compute or display the execution order implied by dependency edges
4. **Cycle detection** — `DepStore.Add` prevents self-loops but not A→B→A cycles
5. **Phase-specific dependency triggers** — deps are project-level, not "wait until upstream reaches phase X"

## Design Space

### A. Dependency Gate Condition

**Option A1: `CheckUpstreamsAtPhase` — per-child gate injection (recommended)**
When evaluating a child run's advance in the context of a portfolio, check whether all of its upstream dependencies have reached (or passed) the child's *current target phase*. This makes the dependency graph participate in the existing gate system rather than inventing a parallel mechanism.

- Implementation: In `evaluateGate()`, when a run has `parent_run_id != ""`, load the portfolio's deps, find this run's upstreams, and check their phase index.
- New gate check type: `CheckUpstreamsAtPhase`
- The check fires on every child advance, not just portfolio advances
- Keeps the gate pattern consistent (interface injection, evidence, tier-based enforcement)

**Option A2: Separate scheduler process**
A standalone scheduler that computes readiness and blocks/unblocks runs. Over-engineering — the gate system already has the enforcement mechanism.

**Option A3: Event-driven blocking**
When `upstream_changed` fires, check if downstream is now unblocked and auto-advance it. Fragile — auto-advance may not be wanted and couples the relay to phase advancement.

### B. Where to Evaluate Dependency Gates

**Option B1: During child `ic run advance` (recommended)**
The advance caller (Clavain sprint, lib-sprint.sh) calls `ic run advance <child-id>`. The gate evaluator checks upstreams by querying the portfolio DB. This keeps gating synchronous with the advance attempt.

- Requires: `ic run advance` must know whether the run has a parent and, if so, open the portfolio DB to check deps + upstream phases.
- Challenge: child DB and portfolio DB are separate SQLite files. The advance call operates on the child DB. It needs to read the portfolio DB for dependency information.
- Solution: Pass portfolio context via `--portfolio-db=<path>` or auto-discover by reading `parent_run_id` from the child's run record and finding the portfolio DB.

**Option B2: During portfolio relay cycle**
The relay evaluates readiness per-child and writes a "blocked/unblocked" status. Child advance reads this status. Introduces staleness (up to 2s).

**Option B3: Pre-flight check in the CLI**
`ic portfolio check-ready <portfolio-id> <child-project>` answers "can this child advance?" based on deps. The caller (lib-sprint.sh) checks before advancing. Non-atomic but pragmatic.

### C. Cross-DB Access Pattern

**Option C1: Portfolio DB provides scheduling API (recommended)**
Add a function to the portfolio package: `IsChildReady(ctx, portfolioRunID, childProjectDir) (bool, evidence)` that:
1. Loads deps where `downstream_project = childProjectDir`
2. For each upstream, opens its DB via DBPool (read-only) and reads the run's phase
3. Compares upstream phase index to child's target phase index
4. Returns ready/not-ready with evidence

This keeps the portfolio package owning all cross-DB queries.

**Option C2: Push readiness state to child DB**
Relay writes a "readiness" state entry into each child DB. Problem: child DBs are opened read-only by the relay.

### D. Phase-Specific vs. Phase-Agnostic Dependencies

**Option D1: Phase-agnostic with same-phase matching (recommended for MVP)**
A dependency edge means: "downstream can't advance to phase X until upstream is at or past phase X". Same-phase matching is the simplest rule and covers the common case (e.g., "don't start executing plugin B until SDK A has finished executing").

**Option D2: Phase-specific triggers**
Each dep edge specifies: "downstream blocked until upstream reaches phase Y". More flexible but more complex schema. Defer.

### E. Topological Ordering

**Option E1: Compute on demand (recommended)**
`ic portfolio order <portfolio-id>` computes topological sort of the dependency graph and prints execution order. Pure computation, no persistence. Useful for humans and for Clavain to decide spawn order.

**Option E2: Persist in table**
Store computed order. Stale after any dep change. Unnecessary complexity.

### F. Cycle Detection

**Option F1: DFS on Add (recommended)**
When adding a dependency edge, run DFS from downstream back through the graph. If upstream is reachable from downstream, the new edge would create a cycle. Reject with error.

This is already needed — the current self-loop check only prevents A→A, not A→B→A.

## Proposed MVP Scope

1. **Cycle detection in `DepStore.Add`** — DFS check before inserting
2. **`CheckUpstreamsAtPhase`** gate condition — blocks child advance when upstreams are behind
3. **`IsChildReady` query** — portfolio package function for readiness check
4. **`ic portfolio order`** CLI — topological sort of dependency graph
5. **`ic portfolio status`** CLI — shows each child's readiness status based on deps
6. **Integration tests** — multi-project scenarios with blocking/unblocking

## Defer

- Phase-specific dependency triggers (schema change for `event_trigger` column on `project_deps`)
- Transitive closure queries
- Auto-advance on upstream unblock
- Priority-based scheduling (which downstream starts first when upstream completes)
- Visual dependency graph rendering

## Key Questions

1. **Should the dependency gate be hard or soft?** Recommendation: hard (P0-P1 priority), because the whole point is to prevent premature execution. But allow `--disable-gates` override.

2. **How does the child know its portfolio context?** The child run record has `parent_run_id`. From that, the advance logic can locate the portfolio run's DB. For same-DB portfolios (portfolio and children in same DB), this is trivial. For cross-DB portfolios, we need the portfolio DB path — either via state table or by resolving the portfolio run's project_dir.

3. **Should readiness block at the CLI level or gate level?** Gate level — it integrates with the existing tier system and produces structured evidence. The CLI just surfaces it.

## Prior Art

- **`CheckChildrenAtPhase`** (gate.go) — exactly the pattern to follow, but in reverse direction (checking upstreams instead of children)
- **`DepStore.GetUpstream`** — already exists, returns upstream projects for a downstream
- **Relay `upstream_changed` events** — already fires, but only as notification. This feature makes it a gate input.
- **Bigend aggregator** — consumes multi-project state similarly
