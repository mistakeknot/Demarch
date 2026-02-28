# Task 1 Implementation: Observation Package — Types and Interfaces

## Summary

Created `core/intercore/internal/observation/observation.go` and `observation_test.go` implementing a unified system-state observation layer. The package follows the `internal/budget/budget.go` pattern: narrow interfaces for each store dependency, a Collector struct, and a Collect() method that aggregates all sources.

## Files Created

- `/home/mk/projects/Demarch/core/intercore/internal/observation/observation.go` — types, interfaces, Collector, Collect()
- `/home/mk/projects/Demarch/core/intercore/internal/observation/observation_test.go` — unit test

## Design Decisions

### Interface Verification

All four interfaces were verified against actual store method signatures:

| Interface | Method | Store Source | Verified Signature |
|---|---|---|---|
| PhaseQuerier | Get | phase/store.go:124 | `Get(ctx context.Context, id string) (*phase.Run, error)` |
| PhaseQuerier | ListActive | phase/store.go:309 | `ListActive(ctx context.Context) ([]*phase.Run, error)` |
| DispatchQuerier | ListActive | dispatch/dispatch.go:345 | `ListActive(ctx context.Context) ([]*dispatch.Dispatch, error)` |
| DispatchQuerier | AggregateTokens | dispatch/dispatch.go:417 | `AggregateTokens(ctx context.Context, scopeID string) (*dispatch.TokenAggregation, error)` |
| EventQuerier | ListAllEvents | event/store.go:108 | `ListAllEvents(ctx context.Context, sincePhaseID, sinceDispatchID, sinceDiscoveryID int64, limit int) ([]event.Event, error)` |
| EventQuerier | ListEvents | event/store.go:68 | `ListEvents(ctx context.Context, runID string, sincePhaseID, sinceDispatchID, sinceDiscoveryID int64, limit int) ([]event.Event, error)` |
| SchedulerQuerier | CountByStatus | scheduler/store.go:140 | `CountByStatus(ctx context.Context) (map[string]int, error)` |

### Pattern Followed: budget.go

The budget package establishes the pattern:
- Define narrow interfaces (e.g., `PhaseStoreQuerier`) rather than depending on concrete `*Store` types
- Constructor takes interface dependencies (any may be nil)
- Main method queries each store, handling nil gracefully

The observation package follows this exactly:
- 4 narrow interfaces: PhaseQuerier, DispatchQuerier, EventQuerier, SchedulerQuerier
- `NewCollector(p, d, e, s)` accepts all four, any may be nil
- `Collect()` skips queries for nil stores and initializes empty slices

### Collect() Behavior

- **Default EventLimit**: 20 if 0 or negative
- **Timestamp**: `time.Now().UTC()`
- **Nil-safe**: All store queries guarded by nil checks; slices pre-initialized to empty (not nil)
- **Run-scoped mode** (RunID set): queries specific run via Get(), scoped events via ListEvents(), includes BudgetSummary if TokenBudget is set on the run
- **Global mode** (RunID empty): queries all active runs via ListActive(), global events via ListAllEvents(), no budget
- **Budget**: Only computed when RunID is set AND both phases and dispatches stores are available; uses TokenBudget field from phase.Run and AggregateTokens from dispatch store

### Helper Functions

- `runToSummary(*phase.Run) RunSummary` — extracts ID, Phase, Status, ProjectDir, Goal, CreatedAt
- `dispatchToSummary(*dispatch.Dispatch) AgentSummary` — extracts ID, AgentType, Status, Turns, InputTokens, OutputTokens, ScopeID (nil-safe dereference)

### Struct Field Mapping

Phase.Run fields used: ID, Phase, Status, ProjectDir, Goal, CreatedAt, TokenBudget (*int64)
Dispatch fields used: ID, AgentType, Status, Turns, InputTokens, OutputTokens, ScopeID (*string)
TokenAggregation fields used: TotalIn, TotalOut
Scheduler statuses mapped: "pending", "running", "retrying" (from map[string]int)

## Test Results

```
=== RUN   TestCollectReturnsSnapshot
--- PASS: TestCollectReturnsSnapshot (0.00s)
PASS
ok  	github.com/mistakeknot/intercore/internal/observation	0.002s
```

The test verifies:
- No error from Collect() with all-nil stores
- Non-nil snapshot returned
- Non-zero timestamp
- Non-nil but empty Runs, Events, and Dispatches.Agents slices
- Nil Budget (no run-scoped query)

## go vet

Clean — no issues reported.

## Type Inventory

| Type | Purpose |
|---|---|
| Snapshot | Top-level observation container |
| RunSummary | Condensed phase run |
| DispatchSummary | Dispatch aggregate with agent list |
| AgentSummary | Condensed dispatched agent |
| QueueSummary | Scheduler queue counts by status |
| BudgetSummary | Token budget state for a run |
| CollectOptions | Controls Collect() scoping |
| PhaseQuerier | Interface for phase store |
| DispatchQuerier | Interface for dispatch store |
| EventQuerier | Interface for event store |
| SchedulerQuerier | Interface for scheduler store |
| Collector | Aggregator struct |
