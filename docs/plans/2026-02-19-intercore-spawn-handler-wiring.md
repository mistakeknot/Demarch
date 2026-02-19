# Plan: Wire Auto-Agent-Spawn Handler into cmdRunAdvance

**Bead:** iv-347n
**Phase:** executing (as of 2026-02-19T06:23:11Z)
**Sprint:** iv-lc0i
**Date:** 2026-02-19
**Complexity:** 2/5 (simple)

## Context

The spawn handler (`internal/event/handler_spawn.go`) is fully implemented and tested (5 tests pass). It auto-spawns agents when phase transitions to "executing". What's missing:

1. **No concrete `AgentSpawner` implementation** — the `SpawnByAgentID` interface method has no implementor
2. **Spawn handler not subscribed** — `cmdRunAdvance` in `run.go` subscribes `log` and `hook` handlers but not `spawn`

## Design Decision: How to implement SpawnByAgentID

The `Agent` record in `run_agents` stores: `id, run_id, agent_type, name, status, dispatch_id`.
It does NOT store `prompt_file` — but `dispatch.Spawn` requires one.

**Approach: Closure adapter in cmdRunAdvance** (matches existing `dispatchRecorder` and `phaseCallback` patterns)

The closure has access to both `rtStore` and `dStore`, plus the `run` object (which has `ProjectDir`). For agents that have an existing `dispatch_id` (re-spawn scenario), it can look up the prior dispatch record to get `prompt_file`, `model`, etc. For agents without a prior dispatch, it uses the agent's `name` field as a convention-based prompt path (`<projectDir>/.ic/prompts/<name>.md`).

This avoids schema changes and matches the existing closure pattern.

## Tasks

### Task 1: Add `GetDispatch` accessor to dispatch.Store (if not already exposed)

**File:** `infra/intercore/internal/dispatch/dispatch.go`

Verify that `dispatch.Store` exposes a `Get(ctx, id) (*Dispatch, error)` method. It already does (line ~140). No code change needed — just confirm.

**Acceptance:** `dStore.Get(ctx, dispatchID)` returns a `*Dispatch` with `PromptFile`, `ProjectDir`, etc.

### Task 2: Create the `AgentSpawnerFunc` adapter type

**File:** `infra/intercore/internal/event/handler_spawn.go`

Add an adapter type for functional implementations (like `http.HandlerFunc` pattern):

```go
// AgentSpawnerFunc adapts a plain function to the AgentSpawner interface.
type AgentSpawnerFunc func(ctx context.Context, agentID string) error

func (f AgentSpawnerFunc) SpawnByAgentID(ctx context.Context, agentID string) error {
    return f(ctx, agentID)
}
```

This lets `cmdRunAdvance` pass a closure without defining a named struct.

**Acceptance:** `AgentSpawnerFunc` satisfies `AgentSpawner` interface.

### Task 3: Wire spawn handler in cmdRunAdvance

**File:** `infra/intercore/cmd/ic/run.go`, in `cmdRunAdvance` function (around line 219-236)

After `dStore` is created (line 236) and before `phaseCallback` (line 238), add:

```go
// Auto-spawn adapter: looks up agent, re-uses dispatch config or falls back to convention
spawner := event.AgentSpawnerFunc(func(ctx context.Context, agentID string) error {
    agent, err := rtStore.GetAgent(ctx, agentID)
    if err != nil {
        return fmt.Errorf("spawn lookup: %w", err)
    }

    var opts dispatch.SpawnOptions
    opts.ProjectDir = run.ProjectDir
    opts.AgentType = agent.AgentType

    // If agent has a prior dispatch, re-use its spawn config
    if agent.DispatchID != nil {
        d, err := dStore.Get(ctx, *agent.DispatchID)
        if err == nil && d.PromptFile != nil {
            opts.PromptFile = *d.PromptFile
            if d.Model != nil {
                opts.Model = *d.Model
            }
            if d.Sandbox != nil {
                opts.Sandbox = *d.Sandbox
            }
        }
    }

    // Fallback: convention-based prompt path
    if opts.PromptFile == "" && agent.Name != nil {
        opts.PromptFile = filepath.Join(run.ProjectDir, ".ic", "prompts", *agent.Name+".md")
    }

    if opts.PromptFile == "" {
        return fmt.Errorf("spawn: agent %s has no prompt file and no name for convention lookup", agentID)
    }

    result, err := dispatch.Spawn(ctx, dStore, opts)
    if err != nil {
        return err
    }

    // Link the new dispatch back to the agent record
    return rtStore.UpdateAgentDispatch(ctx, agentID, result.ID)
})
notifier.Subscribe("spawn", event.NewSpawnHandler(rtStore, spawner, os.Stderr))
```

**Note:** This requires `filepath` import and a new `UpdateAgentDispatch` method on rtStore.

**Acceptance:** `ic run advance` subscribes spawn handler. When phase transitions to "executing", pending agents get spawned.

### Task 4: Add `UpdateAgentDispatch` to runtrack.Store

**File:** `infra/intercore/internal/runtrack/store.go`

```go
// UpdateAgentDispatch sets the dispatch_id on an agent record.
func (s *Store) UpdateAgentDispatch(ctx context.Context, agentID, dispatchID string) error {
    now := time.Now().Unix()
    result, err := s.db.ExecContext(ctx, `
        UPDATE run_agents SET dispatch_id = ?, updated_at = ? WHERE id = ?`,
        dispatchID, now, agentID,
    )
    if err != nil {
        return fmt.Errorf("agent update dispatch: %w", err)
    }
    n, _ := result.RowsAffected()
    if n == 0 {
        return ErrAgentNotFound
    }
    return nil
}
```

**Acceptance:** Can link a dispatch ID back to an agent after spawning.

### Task 5: Add test for UpdateAgentDispatch

**File:** `infra/intercore/internal/runtrack/store_test.go`

Add a test that creates an agent, calls `UpdateAgentDispatch`, then verifies via `GetAgent` that `DispatchID` is set.

### Task 6: Add integration test for spawn wiring

**File:** `infra/intercore/cmd/ic/run_test.go` (or integration test)

Test that `ic run advance` with a pending agent in "executing" phase triggers spawn. This may need a mock `dispatch.sh` or test helper.

If full integration test is impractical, verify the wiring compiles and the subscribe call exists.

### Task 7: Run full test suite

```bash
cd infra/intercore && go test ./...
```

Verify all existing tests still pass plus new tests.

## Ordering

Task 1 (verify) → Task 2 (adapter type) → Task 4 (UpdateAgentDispatch) → Task 5 (test) → Task 3 (wire in run.go) → Task 6 (integration test) → Task 7 (full suite)

## Risk

- **Low:** Schema is unchanged. The spawn handler is no-op when no agents are pending.
- **Convention path may not exist:** If `<project>/.ic/prompts/<name>.md` doesn't exist, `dispatch.Spawn` will fail with "hash prompt" error. This is acceptable — the handler logs and continues (partial failure is already handled).
