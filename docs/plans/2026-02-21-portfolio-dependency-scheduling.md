# Plan: Portfolio-Level Dependency/Scheduling Primitives

**Bead:** iv-wp62
**PRD:** `docs/prds/2026-02-21-portfolio-dependency-scheduling.md`

## Overview

Add dependency-aware scheduling to intercore's portfolio orchestration. The dependency graph (already stored in `project_deps`) will participate in gate evaluation, blocking child run advancement when upstream dependencies haven't reached the required phase.

## Tasks

### Task 1: Cycle Detection in DepStore.Add

**File:** `internal/portfolio/deps.go`
**Tests:** `internal/portfolio/deps_test.go`

Add a `HasPath` method to DepStore that checks whether a directed path exists between two nodes via DFS. Call it in `Add()` before inserting — if `HasPath(ctx, portfolioRunID, downstream, upstream)` returns true, the new edge (upstream→downstream) would create a cycle.

**Implementation:**
1. Add `HasPath(ctx, portfolioRunID, from, to string) (bool, error)` — DFS using `GetDownstream` to walk the graph
2. In `Add()`, before the INSERT, call `HasPath(ctx, portfolioRunID, downstream, upstream)` — note the argument order: we check if downstream can already reach upstream (which means adding upstream→downstream creates a cycle)
3. Return `fmt.Errorf("add dep: cycle detected: adding %s → %s would create a cycle", upstream, downstream)` on detection

**Tests to add:**
- `TestAddDep_CycleDetection` — A→B exists, try adding B→A, expect error
- `TestAddDep_TransitiveCycleDetection` — A→B, B→C exist, try adding C→A, expect error
- `TestAddDep_NoCycleFalsePositive` — A→B, A→C exist, adding C→B should succeed (no cycle)
- `TestHasPath` — direct and transitive path detection

### Task 2: DepQuerier Interface + Gate Integration

**Files:** `internal/phase/gate.go`, `internal/portfolio/deps.go`

Add a `DepQuerier` interface to the gate evaluation and a new `CheckUpstreamsAtPhase` gate condition.

**Implementation:**

1. In `internal/phase/gate.go`:
   - Add constant `CheckUpstreamsAtPhase = "upstreams_at_phase"`
   - Add `DepQuerier` interface:
     ```go
     type DepQuerier interface {
         GetUpstream(ctx context.Context, portfolioRunID, downstream string) ([]string, error)
     }
     ```
   - Extend `evaluateGate()` signature to accept `dq DepQuerier`
   - Add gate injection: when `run.ParentRunID != nil`, inject `CheckUpstreamsAtPhase` rule with `phase = toPhase`
   - Implement the check:
     - Call `dq.GetUpstream(ctx, *run.ParentRunID, run.ProjectDir)` to get upstream projects
     - For each upstream, call `pq.GetChildren(ctx, *run.ParentRunID)` to find the upstream's child run
     - Compare upstream child's phase index against target phase index
     - If any upstream is behind: fail with evidence listing which upstreams are behind

2. Update all callers of `evaluateGate()` and `EvaluateGate()`:
   - `Advance()` in `machine.go` — add `dq DepQuerier` parameter
   - `EvaluateGate()` in `gate.go` — add `dq DepQuerier` parameter
   - `cmd/ic/run.go` — wire `DepStore` as `DepQuerier` when portfolio context available
   - `cmd/ic/gate.go` — wire `DepStore` as `DepQuerier`

**Tests:**
- Unit test in `internal/phase/gate_test.go` (if exists) or new file
- Stub `DepQuerier` for testing

### Task 3: Wire CLI — Run Advance + Gate Check

**File:** `cmd/ic/run.go`, `cmd/ic/gate.go`

Wire the new `DepQuerier` parameter through the CLI commands.

**Implementation:**
1. In `cmdRunAdvance`: if the run has `parent_run_id`, create a `DepStore` from the same DB and pass to `Advance()`
2. In `cmdGateCheck`: same wiring for `EvaluateGate()`
3. For same-DB portfolios (portfolio run and children share the same intercore.db), the DepStore uses the already-open DB handle — no new connections needed

**Note:** Cross-DB portfolios (rare, not needed for MVP) would require opening the portfolio's DB to get dep edges. Defer this — document that MVP assumes same-DB portfolios.

### Task 4: Topological Sort — `ic portfolio order`

**File:** `cmd/ic/portfolio.go`, `internal/portfolio/topo.go`

Add topological sort of the dependency graph.

**Implementation:**
1. New file `internal/portfolio/topo.go`:
   - `TopologicalSort(deps []Dep) ([]string, error)` — Kahn's algorithm
   - Returns projects in dependency-respecting order (upstreams first)
   - Returns error if cycle detected (defense in depth)
2. New CLI subcommand in `cmd/ic/portfolio.go`:
   - `ic portfolio order <portfolio-id>` — loads deps, runs topo sort, prints order
   - `--json` flag for machine-readable output

**Tests:**
- `TestTopologicalSort` — various graph shapes (linear, diamond, forest)
- `TestTopologicalSort_Cycle` — should error (defense in depth)

### Task 5: Enhanced `ic portfolio status`

**File:** `cmd/ic/portfolio.go`

Enhance portfolio status to show dependency-aware readiness.

**Implementation:**
1. Load children + deps for the portfolio
2. For each child, compute readiness:
   - Get upstream projects from deps
   - For each upstream, find the child run and compare phase indices
   - Mark as "ready" or "blocked by: <upstream-projects with current phases>"
3. Print tabular output: `PROJECT  PHASE  STATUS  BLOCKED_BY`
4. `--json` flag with structured output

### Task 6: Integration Tests

**File:** `test-integration.sh`

Add portfolio dependency scheduling tests to the integration test suite.

**Scenarios:**
1. **Basic dep blocking:** Create portfolio with A→B dep, advance A to planned, try advancing B past planned — should be blocked
2. **Dep unblocking:** After advancing A past planned, B should be able to advance
3. **Cycle rejection:** `ic portfolio dep add` with cycle should fail
4. **Topological order:** `ic portfolio order` should print correct order
5. **Portfolio status readiness:** `ic portfolio status` should show blocked/ready status
6. **No-dep portfolio:** Portfolio without deps should advance freely (regression)

## Execution Order

Tasks 1-2 are core and must go first. Task 3 wires them into the CLI. Tasks 4-5 are independent display enhancements. Task 6 validates everything end-to-end.

```
Task 1 (cycle detection) ─────┐
                               ├── Task 3 (CLI wiring) ── Task 6 (integration tests)
Task 2 (gate integration) ────┘
Task 4 (topo sort) ── independent
Task 5 (status enhancement) ── depends on Task 2 conceptually
```

## Files Modified

| File | Change |
|------|--------|
| `internal/portfolio/deps.go` | Add `HasPath()`, cycle check in `Add()` |
| `internal/portfolio/deps_test.go` | Cycle detection tests, HasPath tests |
| `internal/portfolio/topo.go` | **New:** topological sort |
| `internal/portfolio/topo_test.go` | **New:** topo sort tests |
| `internal/phase/gate.go` | Add `CheckUpstreamsAtPhase`, `DepQuerier` interface, gate logic |
| `internal/phase/machine.go` | Add `dq DepQuerier` to `Advance()` and `EvaluateGate()` |
| `cmd/ic/run.go` | Wire `DepQuerier` in advance/gate commands |
| `cmd/ic/gate.go` | Wire `DepQuerier` in gate check command |
| `cmd/ic/portfolio.go` | Add `order` subcommand, enhance `status` display |
| `test-integration.sh` | Portfolio dependency scheduling tests |

## Estimated Scope

~400-500 lines of Go across 8-10 files. Core logic (cycle detection + gate check) is ~150 lines. Topo sort is ~60 lines. CLI wiring is ~100 lines. Tests are ~200 lines.
