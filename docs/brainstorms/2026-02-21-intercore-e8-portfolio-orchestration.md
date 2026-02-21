# E8: Level 4 Orchestrate — Cross-Project Portfolio Runs

**Bead:** iv-b1os

## Problem Statement

Intercore currently manages runs scoped to individual projects. There's no way to:
1. Track a coordinated effort across multiple projects (e.g., "ship SDK v2 across interbase + intermute + 3 plugins")
2. Express dependency between projects ("intermute changes must land before plugins update")
3. Enforce portfolio-level gates ("all child runs must pass before shipping")
4. Limit total concurrent dispatches across a portfolio (cost/resource control)

The Bigend aggregator already polls multiple project DBs, but there's no kernel-level orchestration primitive. Higher layers (Clavain, Bigend) must manually coordinate, which is error-prone and loses auditability.

## Current State

### What exists
- **Runs** are scoped by `project_dir` with optional `scope_id` grouping, but no parent/child hierarchy
- **Dispatches** have no concurrency limits — any number can be active simultaneously
- **Events** are per-project (stored in each project's DB), with no cross-project relay
- **Gates** evaluate per-run conditions (artifact exists, agents complete, verdict exists) but cannot aggregate across runs
- **Bigend aggregator** already iterates project DBs on 2s polling cycle — this is the existing multi-DB pattern

### What's missing
- Parent/child relationship between runs (portfolio → project runs)
- Project dependency graph (`project_deps` table)
- Cross-project event relay
- Portfolio-level gate aggregation
- Max-concurrent-dispatch budget across a portfolio

## Design Space

### A. Portfolio Run Model

**Option A1: `parent_run_id` on runs table** (recommended)
- Add nullable FK `parent_run_id TEXT REFERENCES runs(id)` to existing `runs` table
- Portfolio run is just a run with `project_dir = ''` (no single project) and children linked via `parent_run_id`
- `ic run create --projects=a,b --goal="..."` creates 1 portfolio + N children atomically
- Query children: `SELECT * FROM runs WHERE parent_run_id = ?`
- Reuses existing run lifecycle, events, status model

**Option A2: Separate `portfolios` table**
- Dedicated table for portfolio metadata, separate from runs
- More schema complexity, doesn't reuse run lifecycle
- Reject: over-engineering for MVP

### B. Where to Store Cross-Project State

**Option B1: Portfolio run's own project DB** (recommended)
- Portfolio run lives in a "portfolio DB" (e.g., `.clavain/intercore-portfolio.db`)
- Children are recorded as run_agents or via `parent_run_id` in portfolio DB
- Cross-project queries hit the portfolio DB, not individual project DBs
- Simple: one DB for portfolio state, no cross-DB transactions

**Option B2: Relay in each project DB**
- Each project DB gets a `relay_events` table written by the relay process
- Complex: N DBs to coordinate, duplication concerns
- Reject: too much complexity

**Option B3: Shared central DB**
- One global DB for all portfolio + relay state
- Issue: breaks the "each project is independent" model
- Could work as the portfolio DB in B1

### C. Dependency Graph

**Option C1: `project_deps` in portfolio DB** (recommended)
- Table: `(portfolio_run_id, upstream_project, downstream_project, event_trigger)`
- When upstream project's run advances past a phase, emit `dependency.upstream_changed` event
- Downstream project's run gates can include "upstream at phase X" condition
- Detected by relay loop polling upstream run status

**Option C2: Inline in run metadata**
- Dependency graph stored as JSON in portfolio run's metadata
- Simpler but harder to query, no event emission
- Reject: doesn't integrate with gate system

### D. Event Relay

**Option D1: Polling relay loop in `ic` binary** (recommended)
- New command: `ic portfolio relay <portfolio-id>` runs a polling loop
- Tails each child run's events from their project DBs
- Writes aggregated events to portfolio DB's event table
- Similar to Bigend's `Refresh()` pattern but kernel-level
- Can run as a systemd service or in-process

**Option D2: Push from each project DB**
- Each `ic` invocation checks if run has a parent and pushes events upstream
- Tight coupling, requires all `ic` calls to know about portfolio
- Reject: breaks encapsulation

### E. Resource Scheduling

**Option E1: Token budget at portfolio level** (recommended)
- Portfolio run has `token_budget` (existing field) that applies across all children
- Before spawning a dispatch, check: `sum(child_dispatches.tokens) < portfolio.token_budget`
- Max concurrent dispatches: `portfolio.max_dispatches` field (new)
- Enforcement: `ic dispatch spawn` checks portfolio budget if `parent_run_id` is set

**Option E2: Separate scheduler service**
- Over-engineering for current scale
- Reject: kernel should own this

### F. Portfolio Gate Semantics

**Option F1: All-children-pass** (recommended for MVP)
- Portfolio can only advance when all child runs have passed the equivalent phase gate
- New gate type: `children_at_phase` — checks all child runs are at or past a given phase
- Portfolio phase chain mirrors children's phase chain
- `ic gate check <portfolio-id>` aggregates child gate results

**Option F2: Quorum-based**
- M-of-N children must pass
- Useful for non-critical children (nice-to-have)
- Defer to later iteration

## Proposed MVP Scope

Focus on the minimum that unblocks multi-project sprints:

1. **Schema**: `parent_run_id` on runs + `project_deps` table + `max_dispatches` field
2. **CLI**: `ic run create --projects=a,b` (creates portfolio + children), `ic portfolio status <id>`, `ic portfolio relay <id>`
3. **Gates**: `children_at_phase` gate type for portfolio runs
4. **Budget**: Portfolio-level `token_budget` + `max_dispatches` enforcement
5. **Events**: `dependency.upstream_changed` event type + relay loop writing to portfolio DB

**Defer to E8.5 or later:**
- Cross-project dependency graph with transitive closure
- Quorum-based portfolio gates
- Dispatch priority/preemption across portfolio
- Automatic portfolio creation from beads epic

## Key Questions

1. **Where does the portfolio DB live?** Options: `.clavain/portfolio.db` (project-independent), or under a designated "root" project. Recommendation: `.clavain/portfolio.db` in the workspace root.

2. **Does the relay need to be long-running?** For MVP, a polling loop that runs during `ic portfolio relay` is sufficient. Bigend can also serve as the relay since it already polls project DBs.

3. **How does Bigend display portfolio runs?** Bigend's aggregator already enriches with kernel state — it can query the portfolio DB in addition to project DBs. Portfolio runs show as a distinct "portfolio" project in the sidebar.

## Prior Art

- **Bigend aggregator** (`hub/autarch/internal/bigend/aggregator/`) — multi-project polling, event dedup, activity merge
- **Scope ID pattern** — `dispatches.scope_id` already groups dispatches across a run; extend to portfolio
- **Gate system** (`internal/gates/`) — condition-based evaluation with tier-based enforcement; extend with portfolio condition
- **Event bus** (`internal/events/`) — append-only with cursor-based consumption; relay is a new event source
