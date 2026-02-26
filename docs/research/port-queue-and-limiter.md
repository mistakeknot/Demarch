# Port Analysis: NTM Queue & Limiter to Intercore Scheduler

## Source Files

- **NTM queue.go**: `/home/mk/projects/Demarch/research/ntm/internal/scheduler/queue.go` (519 lines)
- **NTM limiter.go**: `/home/mk/projects/Demarch/research/ntm/internal/scheduler/limiter.go` (~300 lines)
- **NTM job.go**: `/home/mk/projects/Demarch/research/ntm/internal/scheduler/job.go` (defines SpawnJob, JobType, JobPriority, JobStatus)

## Target Files

- `/home/mk/projects/Demarch/core/intercore/internal/scheduler/queue.go`
- `/home/mk/projects/Demarch/core/intercore/internal/scheduler/limiter.go`

## Key Adaptations

### queue.go

1. **Package**: Changed from NTM's `scheduler` (same name, different module) to Intercore's `scheduler`.
2. **JobType reference**: NTM defines `JobTypeSession`, `JobTypePaneSplit`, `JobTypeAgentLaunch` (tmux-oriented). Intercore will use `JobTypeDispatch`, `JobTypeBatch` from the sibling `job.go` in the same package. The queue code references `JobType` and `JobPriority` generically via the `SpawnJob` struct, so the queue itself is type-agnostic -- it only uses these in stats tracking maps.
3. **QueueStats.ByType map key**: Changed from `map[JobType]int` to `map[string]int` for simpler JSON serialization. The `Enqueue`, `Dequeue`, `Remove`, and `Stats` methods convert `job.Type` to `string()` when indexing this map.
4. **All functions preserved**: `JobQueue`, `NewJobQueue`, `Enqueue`, `Dequeue`, `Peek`, `Get`, `Remove`, `Len`, `IsEmpty`, `Stats`, `ListAll`, `ListBySession`, `ListByBatch`, `CountBySession`, `CountByBatch`, `Clear`, `CancelSession`, `CancelBatch`.
5. **jobHeap**: Kept verbatim -- implements `heap.Interface` for `*SpawnJob`.
6. **FairScheduler**: Kept verbatim -- `FairScheduler`, `FairSchedulerConfig`, `DefaultFairSchedulerConfig`, `NewFairScheduler`, `Enqueue`, `TryDequeue`, `MarkComplete`, `Queue`, `RunningCount`.

### limiter.go

1. **Package**: Same `scheduler` package.
2. **All types/functions preserved**: `RateLimiter`, `LimiterConfig`, `LimiterStats`, `DefaultLimiterConfig`, `NewRateLimiter`, `Wait`, `TryAcquire`, `TimeUntilNextToken`, `SetRate`, `SetCapacity`, `SetMinInterval`, `Stats`, `Reset`, `AvailableTokens`, `Waiting`.
3. **PerAgentLimiter preserved**: `PerAgentLimiter`, `AgentLimiterConfig`, `DefaultAgentLimiterConfig`, `NewPerAgentLimiter`, `GetLimiter`, `Wait`, `AllStats`.
4. **Agent type mapping** (the key behavioral change):

| NTM Agent | NTM Config | Intercore Agent | Intercore Config |
|-----------|-----------|-----------------|-----------------|
| `"cc"` (Claude Code) | rate=1.5, cap=3, interval=500ms | `"claude"` | rate=1.5, cap=3, interval=500ms |
| `"cod"` (Codex) | rate=1.0, cap=2, interval=800ms | `"codex"` | rate=1.0, cap=2, interval=800ms |
| `"gmi"` (Gemini) | rate=2.0, cap=5, interval=400ms | *(removed)* | -- |

Note: `"gmi"` is dropped because Intercore's dispatch system currently only supports Codex agents (see `spawn.go` default `AgentType = "codex"`). The default limiter config (rate=2.0, cap=5, interval=300ms) applies to any unknown agent type, so if Gemini or other runtimes are added later, they will get reasonable defaults automatically.

## SpawnJob Dependency

Both files reference `SpawnJob`, `JobType`, `JobPriority`, `JobStatus`, and status constants (`StatusRunning`, etc.) that must exist in a sibling `job.go` within the same package. The queue and limiter code assumes these types exist but does not define them. The following types/constants are required from `job.go`:

- `type JobType string` with constants `JobTypeDispatch`, `JobTypeBatch`
- `type JobPriority int` with constants `PriorityUrgent`, `PriorityHigh`, `PriorityNormal`, `PriorityLow`
- `type JobStatus string` with constants `StatusPending`, `StatusScheduled`, `StatusRunning`, `StatusCompleted`, `StatusFailed`, `StatusCancelled`, `StatusRetrying`
- `type SpawnJob struct` with fields: `ID`, `Type`, `Priority`, `SessionName`, `AgentType`, `BatchID`, `CreatedAt`, `Status`, plus methods `Cancel()`, `GetStatus()`, `Context()`

## Structural Notes

- Both files are fully self-contained within the `scheduler` package (no imports from other intercore packages).
- The queue uses `container/heap` and `sync.RWMutex`.
- The limiter uses `context`, `sync.Mutex`, and `time`.
- No database dependency -- these are pure in-memory data structures.
- Thread-safe: all public methods use appropriate locking.
