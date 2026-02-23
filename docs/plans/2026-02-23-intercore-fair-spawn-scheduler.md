# Plan: Fair Spawn Scheduler in Intercore

**Bead:** iv-4nem
**Phase:** done
**Date:** 2026-02-23
**Complexity:** 2/5 (simple)

## Problem

Intercore's `Spawn()` directly exec's agent processes with no queuing, rate limiting, or backoff. `SpawnPolicy` provides reject-or-allow guard rails (budget, concurrency caps, depth), but nothing paces spawns or handles resource exhaustion gracefully. If a caller spawns 10 agents in rapid succession, all 10 start simultaneously — no fairness, no backoff on failure, no headroom awareness.

## Design

### Approach: Adapt NTM scheduler as `internal/scheduler/` package

Port the reference scheduler from `research/ntm/internal/scheduler/` into `core/intercore/internal/scheduler/`, adapting it to Intercore's conventions:

- **CLI-first**: Exposed via `ic scheduler` subcommands (submit, status, stats, pause/resume)
- **SQLite persistence**: Job queue stored in the Intercore DB (not in-memory only) so it survives process restarts
- **SpawnPolicy integration**: The existing `CheckPolicy()` runs as a pre-enqueue guard; the scheduler adds queuing and pacing on top

### What to port vs what to skip

**Port (core value):**
- `scheduler.go` — Scheduler struct, Submit/Cancel/Stats, worker loop
- `job.go` — SpawnJob struct, status transitions, priority
- `queue.go` — FairScheduler with per-session fair queuing
- `limiter.go` — Token bucket rate limiter (global + per-agent)
- `caps.go` — Per-agent concurrency caps with ramp-up/cooldown
- `backoff.go` — Backoff controller for resource errors

**Skip (not needed for v1):**
- `headroom.go` — Pre-spawn resource checking (requires runtime metrics collection we don't have yet)
- `progress.go` — Progress tracking UI (Intercore is CLI, not TUI)
- Batch operations beyond SubmitBatch (keep simple)

### Integration points

1. **`ic dispatch spawn`** — add `--scheduled` flag. When set, submit to scheduler instead of direct exec. When not set, existing behavior unchanged (backward compatible).
2. **`ic scheduler` subcommand** — new: `start`, `stop`, `status`, `submit`, `stats`, `pause`, `resume`
3. **Config** — new keys: `scheduler_max_concurrent`, `scheduler_rate_limit`, `scheduler_agent_caps`

### Schema changes

New `scheduler_jobs` table (migration):

```sql
CREATE TABLE IF NOT EXISTS scheduler_jobs (
    id          TEXT PRIMARY KEY,
    status      TEXT NOT NULL DEFAULT 'pending',  -- pending, running, completed, failed, cancelled
    priority    INTEGER NOT NULL DEFAULT 5,
    agent_type  TEXT NOT NULL DEFAULT 'codex',
    session_name TEXT,
    batch_id    TEXT,
    dispatch_id TEXT,                              -- links to dispatches table after spawn
    spawn_opts  TEXT NOT NULL,                     -- JSON SpawnOptions
    max_retries INTEGER NOT NULL DEFAULT 3,
    retry_count INTEGER NOT NULL DEFAULT 0,
    error_msg   TEXT,
    created_at  INTEGER NOT NULL,
    started_at  INTEGER,
    completed_at INTEGER,
    FOREIGN KEY (dispatch_id) REFERENCES dispatches(id)
);
CREATE INDEX IF NOT EXISTS idx_scheduler_jobs_status ON scheduler_jobs(status);
CREATE INDEX IF NOT EXISTS idx_scheduler_jobs_session ON scheduler_jobs(session_name);
```

## Tasks

### Task 1: Port core scheduler types [DONE]

**Files:** `core/intercore/internal/scheduler/scheduler.go`, `job.go`, `config.go`

- [x] Port `SpawnJob`, `Config`, `Stats` types from NTM
- [x] Adapt `SpawnJob` to wrap `dispatch.SpawnOptions` instead of NTM-specific fields
- [x] Port `DefaultConfig()` with sensible Intercore defaults (max_concurrent=4, rate=10/min)
- [x] Add JSON serialization for SQLite persistence

### Task 2: Port fair queue and rate limiter [DONE]

**Files:** `core/intercore/internal/scheduler/queue.go`, `limiter.go`

- [x] Port `FairScheduler` (per-session fair queuing)
- [x] Port `RateLimiter` (token bucket, global + per-agent)
- [x] Port associated tests

### Task 3: Port concurrency caps and backoff [DONE]

**Files:** `core/intercore/internal/scheduler/caps.go`, `backoff.go`

- [x] Port `AgentCaps` (per-agent concurrency with ramp-up and cooldown on failure)
- [x] Port `BackoffController` (exponential backoff on resource errors, global pause)
- [x] Port error classification (`ClassifyError`)

### Task 4: Implement scheduler core [DONE]

**File:** `core/intercore/internal/scheduler/scheduler.go`

- [x] Port `Scheduler.worker()`, `processJobs()`, `executeJob()` loop
- [x] The executor function calls `dispatch.Spawn()` — connecting scheduler to existing dispatch
- [x] Port Submit, Cancel, CancelSession, CancelBatch, Stats, Pause/Resume
- [x] Write tests: submit/execute/complete cycle, cancellation, rate limiting, backoff retry

### Task 5: Add SQLite persistence layer [DONE]

**File:** `core/intercore/internal/scheduler/store.go`

- [x] Add `scheduler_jobs` table migration (schema v19)
- [x] Implement `Store` with Create/Get/Update/List/Prune operations
- [x] On scheduler start: recover pending/running jobs from DB (crash recovery)
- [x] On job completion: update DB record

### Task 6: Add CLI subcommands [DONE]

**File:** `core/intercore/cmd/ic/scheduler_cmd.go`

- [x] `ic scheduler status <id>` — show job details
- [x] `ic scheduler stats` — show queue stats by status
- [x] `ic scheduler submit --prompt-file=<f> --project=<dir>` — submit a job
- [x] `ic scheduler pause` / `resume` — via state table
- [x] `ic scheduler list` / `cancel` / `prune`
- [x] Wire `ic dispatch spawn --scheduled` to submit through scheduler

### Task 7: Wire to existing dispatch and write tests [DONE]

- [x] Modify `ic dispatch spawn` to accept `--scheduled` flag
- [x] When `--scheduled`: create scheduler job, return job ID (not dispatch ID)
- [x] Poll via `ic scheduler status <job-id>` → maps to dispatch status after execution
- [x] Unit tests: submit/execute/complete cycle, cancellation, rate limiting, backoff retry, concurrency limit
- [x] Store tests: CRUD, recovery, prune
- [x] All 19 packages pass with `-race` flag

## Files Changed

| File | Change |
|------|--------|
| `core/intercore/internal/scheduler/job.go` | **New** — SpawnJob, JobType, JobStatus, JobPriority types |
| `core/intercore/internal/scheduler/queue.go` | **New** — JobQueue (priority heap), FairScheduler (per-session) |
| `core/intercore/internal/scheduler/limiter.go` | **New** — RateLimiter (token bucket), PerAgentLimiter |
| `core/intercore/internal/scheduler/caps.go` | **New** — AgentCaps (ramp-up, cooldown on failure) |
| `core/intercore/internal/scheduler/backoff.go` | **New** — BackoffController (exponential, jitter, global pause) |
| `core/intercore/internal/scheduler/scheduler.go` | **New** — Scheduler core (worker loop, executeJob, Submit/Cancel/Stats) |
| `core/intercore/internal/scheduler/store.go` | **New** — SQLite persistence (Create/Get/Update/List/Prune/Recover) |
| `core/intercore/internal/scheduler/scheduler_test.go` | **New** — 9 tests (start/stop, submit, concurrency, cancel, pause, retry, batch, hooks) |
| `core/intercore/internal/scheduler/store_test.go` | **New** — 5 tests (CRUD, list, recover, prune) |
| `core/intercore/cmd/ic/scheduler_cmd.go` | **New** — CLI subcommands (submit, status, stats, list, pause, resume, cancel, prune) |
| `core/intercore/cmd/ic/main.go` | **Edit** — add `case "scheduler"` routing |
| `core/intercore/cmd/ic/dispatch.go` | **Edit** — add `--scheduled` flag to dispatch spawn |
| `core/intercore/internal/db/schema.sql` | **Edit** — add `scheduler_jobs` table (v19) |
| `core/intercore/internal/db/db.go` | **Edit** — bump schema version 18→19 |
| `core/intercore/internal/db/db_test.go` | **Edit** — update version assertions 18→19 |

## Non-Goals

- No headroom guard in v1 (requires runtime metrics infrastructure)
- No daemon mode — scheduler runs embedded in `ic` process
- No HTTP API — CLI only per Intercore convention
- No changes to existing direct-spawn path (backward compatible)

## Testing

- `go test ./internal/scheduler/...` — unit tests for each component
- `go test -race ./internal/scheduler/...` — race detection
- `bash test-integration.sh` — integration tests with real DB
- Manual: `ic scheduler submit --prompt-file=test.md --project=. && ic scheduler status`
