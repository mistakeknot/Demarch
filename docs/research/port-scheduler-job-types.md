# Port Scheduler Job Types: NTM to Intercore

**Date:** 2026-02-23
**Source:** `research/ntm/internal/scheduler/job.go`
**Target:** `core/intercore/internal/scheduler/job.go`

## Summary

Adapted the NTM scheduler's `job.go` types into Intercore's `internal/scheduler/` package. The NTM scheduler was designed around tmux pane management (session creation, pane splitting, agent launching). Intercore's scheduler wraps the existing `dispatch.Spawn()` pipeline, so the job types and struct fields were adapted accordingly.

## Adaptations Made

### Package and Module

| Aspect | NTM | Intercore |
|--------|-----|-----------|
| Package | `scheduler` (same) | `scheduler` |
| Module path | `research/ntm/internal/scheduler` | `github.com/mistakeknot/interverse/infra/intercore/internal/scheduler` |
| Go version | 1.22 | 1.22 (matches `go.mod`) |

### JobType Constants

NTM defined three job types oriented around tmux operations:

```go
// NTM (removed)
JobTypeSession     = "session"      // Create a new tmux session
JobTypePaneSplit   = "pane_split"   // Split an existing pane
JobTypeAgentLaunch = "agent_launch" // Launch an agent in a pane
```

Intercore replaces these with dispatch-oriented types:

```go
// Intercore (new)
JobTypeDispatch = "dispatch" // Spawn a single agent dispatch
JobTypeBatch    = "batch"    // Batch of related dispatches
```

**Rationale:** Intercore has no tmux dependency. All agent spawning goes through `dispatch.Spawn()`. The `batch` type supports the `SubmitBatch` flow referenced in the scheduler plan.

### SpawnJob Struct Changes

#### Removed Fields

| Field | Reason |
|-------|--------|
| `PaneIndex int` | NTM-specific (tmux pane targeting). Intercore dispatches don't target panes. |
| `Result *SpawnResult` | The dispatch package already defines `SpawnResult` (`dispatch.SpawnResult`). The scheduler job links to dispatches via `DispatchID` after execution; carrying a separate result struct would duplicate state. |

#### Renamed Fields

| NTM Field | Intercore Field | Reason |
|-----------|-----------------|--------|
| `Directory string` | `ProjectDir string` | Matches `dispatch.SpawnOptions.ProjectDir` naming convention. Consistency with existing Intercore code. |

#### Added Fields

| Field | Type | Purpose |
|-------|------|---------|
| `SpawnOpts` | `string` | JSON-serialized `dispatch.SpawnOptions`. Enables SQLite persistence (the `scheduler_jobs.spawn_opts` column) without importing the dispatch package at the type level. |
| `DispatchID` | `string` | Links to the `dispatches` table after the spawn executes. Set by the scheduler's `executeJob()` once `dispatch.Spawn()` returns a result. Maps to `scheduler_jobs.dispatch_id` FK. |

#### Retained Fields (unchanged)

All of these were kept as-is with identical types and semantics:

- `ID string` -- unique job identifier
- `Type JobType` -- job classification
- `Priority JobPriority` -- queue ordering
- `SessionName string` -- fair-queuing key (per-session fairness)
- `AgentType string` -- agent type label (codex, claude, etc.)
- `Status JobStatus` -- lifecycle state
- `CreatedAt`, `ScheduledAt`, `StartedAt`, `CompletedAt` -- timestamps
- `Error string` -- failure message
- `RetryCount`, `MaxRetries`, `RetryDelay` -- retry mechanics
- `BatchID`, `ParentJobID` -- job grouping/hierarchy
- `Metadata map[string]interface{}` -- extensible context
- `Callback func(*SpawnJob)` -- completion hook (json:"-")
- `ctx context.Context`, `cancel context.CancelFunc` -- cancellation
- `mu sync.RWMutex` -- concurrency safety

### Status and Priority Constants

All status constants retained verbatim:

```
StatusPending, StatusScheduled, StatusRunning, StatusCompleted,
StatusFailed, StatusCancelled, StatusRetrying
```

All priority constants retained verbatim:

```
PriorityUrgent(0), PriorityHigh(1), PriorityNormal(2), PriorityLow(3)
```

### Methods

All methods retained with identical signatures and logic:

| Method | Signature | Notes |
|--------|-----------|-------|
| `NewSpawnJob` | `(id, jobType, sessionName) *SpawnJob` | Factory with sensible defaults (PriorityNormal, 3 retries, 1s delay) |
| `Cancel` | `()` | Fires context cancel, sets StatusCancelled if pending/scheduled |
| `Context` | `() context.Context` | Read-locked context accessor |
| `IsCancelled` | `() bool` | Checks status + context error |
| `IsTerminal` | `() bool` | Completed, Failed, or Cancelled |
| `SetStatus` | `(JobStatus)` | Updates status with auto-timestamping |
| `SetError` | `(error)` | Stores error string |
| `GetStatus` | `() JobStatus` | Read-locked status accessor |
| `QueueDuration` | `() time.Duration` | Created -> Scheduled (or now) |
| `ExecutionDuration` | `() time.Duration` | Started -> Completed (or now) |
| `TotalDuration` | `() time.Duration` | Created -> Completed (or now) |
| `CanRetry` | `() bool` | RetryCount < MaxRetries |
| `IncrementRetry` | `()` | Bumps count, sets StatusRetrying, clears error |
| `Clone` | `() *SpawnJob` | Deep copy for reporting (no callback/context/result) |

The `Clone` method was updated to copy `ProjectDir`, `SpawnOpts`, and `DispatchID` instead of the removed `PaneIndex`, `Directory`, and `Result`.

### Removed Types

| Type | Reason |
|------|--------|
| `SpawnResult` struct | Already defined in `dispatch.SpawnResult` (`spawn.go:36-40`). The scheduler links to dispatch results via `DispatchID` rather than embedding a separate result type. |

## Integration with Existing Dispatch

The `SpawnOpts` field bridges the scheduler and dispatch packages:

1. **Submit time:** Caller serializes `dispatch.SpawnOptions` to JSON, stores in `SpawnOpts`
2. **Persistence:** `SpawnOpts` maps directly to the `scheduler_jobs.spawn_opts TEXT` column
3. **Execute time:** Scheduler deserializes `SpawnOpts` back to `dispatch.SpawnOptions`, calls `dispatch.Spawn()`
4. **Post-execute:** `DispatchID` is set from `dispatch.SpawnResult.ID`

This avoids a compile-time dependency from the scheduler types on the dispatch package, keeping the types file self-contained.

## Schema Alignment

The struct fields align 1:1 with the `scheduler_jobs` table from the plan:

| Column | Struct Field | Type |
|--------|-------------|------|
| `id` | `ID` | `TEXT PRIMARY KEY` |
| `status` | `Status` | `TEXT` |
| `priority` | `Priority` | `INTEGER` |
| `agent_type` | `AgentType` | `TEXT` |
| `session_name` | `SessionName` | `TEXT` |
| `batch_id` | `BatchID` | `TEXT` |
| `dispatch_id` | `DispatchID` | `TEXT` (FK -> dispatches) |
| `spawn_opts` | `SpawnOpts` | `TEXT` (JSON) |
| `max_retries` | `MaxRetries` | `INTEGER` |
| `retry_count` | `RetryCount` | `INTEGER` |
| `error_msg` | `Error` | `TEXT` |
| `created_at` | `CreatedAt` | `INTEGER` (unix) |
| `started_at` | `StartedAt` | `INTEGER` (unix) |
| `completed_at` | `CompletedAt` | `INTEGER` (unix) |

Fields not persisted: `Callback`, `ctx`, `cancel`, `mu`, `RetryDelay`, `Metadata`, `ProjectDir` (redundant with SpawnOpts JSON).

## Verification

The file compiles cleanly:

```bash
cd core/intercore && go vet ./internal/scheduler/
# (no errors)
```

## Files

- **Created:** `core/intercore/internal/scheduler/job.go`
- **Reference:** `research/ntm/internal/scheduler/job.go`
- **Plan:** `docs/plans/2026-02-23-intercore-fair-spawn-scheduler.md`
