# Port Analysis: NTM caps.go & backoff.go to Intercore Scheduler

## Overview

Ported two files from `research/ntm/internal/scheduler/` into `core/intercore/internal/scheduler/`:

1. **`caps.go`** -- Per-agent concurrency cap management with ramp-up and cooldown
2. **`backoff.go`** -- Exponential backoff with jitter for resource exhaustion errors

## Source Files

- NTM original: `/home/mk/projects/Demarch/research/ntm/internal/scheduler/caps.go` (725 lines)
- NTM original: `/home/mk/projects/Demarch/research/ntm/internal/scheduler/backoff.go` (548 lines)

## Target Files

- `/home/mk/projects/Demarch/core/intercore/internal/scheduler/caps.go`
- `/home/mk/projects/Demarch/core/intercore/internal/scheduler/backoff.go`

## Changes Applied to caps.go

### Removals (CodexThrottle / ratelimit dependency)

The NTM version imported `github.com/Dicklesworthstone/ntm/internal/ratelimit` and had an AIMD-based Codex throttle integrated into the caps system. All of these were removed:

| Removed Item | Type | Reason |
|---|---|---|
| `import "github.com/Dicklesworthstone/ntm/internal/ratelimit"` | import | Intercore has no NTM ratelimit package |
| `codexThrottle *ratelimit.CodexThrottle` | field on `AgentCaps` | Dependency on removed package |
| Codex throttle initialization in `NewAgentCaps()` | constructor logic | No longer needed |
| Codex throttle gate check in `TryAcquire()` | method logic | Was cod-specific rate limiting |
| `CodexThrottle() *ratelimit.CodexThrottle` | method | Returns removed type |
| `SetCodexThrottle(ct *ratelimit.CodexThrottle)` | method | Sets removed type |
| `RecordCodexRateLimit(paneID string, waitSeconds int)` | method | NTM-specific rate limit tracking |
| `RecordCodexSuccess()` | method | NTM-specific success tracking |
| `CodexThrottleStatus() *ratelimit.CodexThrottleStatus` | method | Returns removed type |
| Codex throttle reset in `Reset()` | method logic | No longer needed |

### Renames

| NTM Name | Intercore Name | Reason |
|---|---|---|
| `CodexCapConfig()` | `ConservativeCapConfig()` | Generic name, not tied to specific agent type |

### Agent Type Changes in DefaultAgentCapsConfig

NTM used abbreviated agent type keys tied to tmux pane prefixes. Intercore uses full agent type names matching its dispatch system.

| NTM Key | Intercore Key | Config Source |
|---|---|---|
| `"cc"` | `"claude"` | `DefaultAgentCapConfig()` -- MaxConcurrent 4, standard defaults |
| `"cod"` | `"codex"` | `ConservativeCapConfig()` -- MaxConcurrent 3, ramp-up enabled, 60s interval, 120s recovery |
| `"gmi"` | (removed) | Gemini not included in initial Intercore config |

### Preserved Core API

All core types and methods were preserved without modification:

**Types:** `AgentCapConfig`, `AgentCapsConfig`, `AgentCaps`, `agentCapState`, `CapsStats`, `AgentCapStats`

**Public methods on AgentCaps:**
- `NewAgentCaps(cfg)` -- constructor
- `TryAcquire(agentType)` -- non-blocking slot acquisition
- `Acquire(ctx, agentType)` -- blocking slot acquisition with context cancellation
- `Release(agentType)` -- slot release with waiter notification
- `RecordFailure(agentType)` -- triggers cooldown cap reduction
- `RecordSuccess(agentType)` -- resets cooldown timer
- `GetRunning(agentType)` -- current running count
- `GetCurrentCap(agentType)` -- current effective cap
- `GetAvailable(agentType)` -- available slots
- `Stats()` -- full cap statistics
- `SetCap(agentType, cap)` -- dynamic cap adjustment
- `ForceRampUp(agentType)` -- immediate cap increase to max
- `Reset()` -- full state reset

**Internal methods:** `initialCap`, `getCapState`, `globalCapExceeded`, `removeWaiter`, `notifyWaiter`, `recoverFromCooldown`, `updateRampUp`

## Changes Applied to backoff.go

### No Structural Changes

The backoff.go file was ported essentially verbatim. It has no external dependencies beyond the standard library and types within the same package.

### Forward Reference: *Scheduler

The `BackoffController` struct contains a `scheduler *Scheduler` field. This type is expected to be defined in `scheduler.go` within the same package. Until that file is created, the package will not compile. This is intentional and matches the task specification ("forward-declared").

The `Scheduler` type needs at minimum two methods called by `BackoffController`:
- `Pause()` -- called when global backoff triggers queue pause
- `Resume()` -- called when global backoff ends or success resets backoff

### SpawnJob Dependency

`BackoffController.HandleError()` and the `onRetryExhausted` hook both reference `*SpawnJob`, which is already defined in the existing `job.go` in the Intercore scheduler package. The `SpawnJob` type in Intercore has the same `ID`, `RetryCount` fields used by backoff logic.

### Preserved Core API

**Types:** `ResourceErrorType`, `ResourceError`, `BackoffConfig`, `BackoffController`, `BackoffStats`

**Constants:** `ResourceErrorNone`, `ResourceErrorEAGAIN`, `ResourceErrorENOMEM`, `ResourceErrorENFILE`, `ResourceErrorEMFILE`, `ResourceErrorRateLimit`

**Public functions:**
- `ClassifyError(err, exitCode, stderr)` -- error classification with syscall, string pattern, and exit code checks
- `CalculateJitteredDelay(base, jitterFactor)` -- standalone jittered delay calculation
- `ExponentialBackoff(attempt, initial, max, multiplier)` -- standalone exponential backoff calculation

**Public methods on BackoffController:**
- `NewBackoffController(cfg)` -- constructor
- `SetScheduler(s)` -- set scheduler reference for pause/resume
- `SetHooks(onStart, onEnd, onExhausted)` -- event callbacks
- `HandleError(job, resErr)` -- process resource error, return (shouldRetry, delay)
- `RecordSuccess()` -- reset consecutive failures and backoff state
- `IsInGlobalBackoff()` -- check if global backoff is active
- `RemainingBackoff()` -- remaining time in global backoff
- `Stats()` -- backoff statistics
- `Reset()` -- full state reset

**Error classification patterns preserved:**
- EAGAIN: "resource temporarily unavailable", "eagain", "try again", "cannot allocate memory", "fork: retry/failed/cannot fork"
- ENOMEM: "out of memory", "enomem", "memory allocation failed", "not enough/insufficient memory"
- Rate limit: "rate limit", "too many requests", "quota exceeded", "429", "throttled"
- FD limit: "too many open files", "emfile", "enfile", "file table overflow"
- Exit codes: 11 (EAGAIN), 12 (ENOMEM), 137 (OOM kill)

## Compilation Status

The package currently does NOT compile because `*Scheduler` is undefined. This will be resolved when `scheduler.go` is ported/created in the same package. The `caps.go` file compiles independently (verified).

## Line Counts

| File | NTM Lines | Intercore Lines | Delta |
|---|---|---|---|
| `caps.go` | 725 | 509 | -216 (removed CodexThrottle, Gemini config) |
| `backoff.go` | 548 | 476 | -72 (identical logic, formatting) |

## Existing Package Context

The Intercore scheduler package already had:
- `job.go` (285 lines) -- `SpawnJob`, `JobType`, `JobPriority`, `JobStatus` types
- `limiter.go` -- rate limiter (not inspected)
- `queue.go` -- queue implementation (not inspected)

The new files integrate cleanly with the existing `SpawnJob` type used by `BackoffController.HandleError()`.
