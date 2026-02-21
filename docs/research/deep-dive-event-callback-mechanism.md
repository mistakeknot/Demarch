# Event Callback Mechanism in Intercore's Phase Machine

Deep-dive analysis of how phase transitions trigger event callbacks, and how dispatch spawning could be wired to phase machine events.

## 1. PhaseEventCallback Mechanism (machine.go)

### Definition
```go
type PhaseEventCallback func(runID, eventType, fromPhase, toPhase, reason string)
```
- **Signature**: Takes 5 string parameters (run ID, event type, from/to phases, reason)
- **Optional**: Can be nil (Advance checks before calling, line 237)
- **Fire-and-Forget**: Called OUTSIDE the transaction (line 236), after commit succeeds
- **Error Handling**: Errors are NOT logged — it's fire-and-forget by design

### Invocation Pattern
The callback is fired at 4 distinct points in `Advance()`:

1. **Auto-advance disabled pause** (line 125)
   - Called when `!run.AutoAdvance && cfg.SkipReason == ""`
   - Event type: `EventPause`
   - Reason: "auto_advance disabled"

2. **Hard gate block** (line 201)
   - Called when gate evaluation returns `GateFail + TierHard`
   - Event type: `EventBlock`
   - Reason: gate evidence + skip reason (if provided)

3. **Successful phase advance** (line 238)
   - Called after UpdatePhase + AddEvent + status transition (all in same tx)
   - Event type: `EventAdvance` (the normal case)
   - Reason: gate evidence + skip reason (if provided)

4. **Rollback** (phase.go, line 304 in Rollback function)
   - Called after RollbackPhase + AddEvent
   - Event type: `EventRollback`
   - Reason: user-provided reason string

### Atomicity Guarantees
- **Transaction Isolation**: All gate checks, phase updates, event recording, and status transitions happen in a single ACID transaction (lines 52-234)
- **Callback Outside TX**: Callback fires after commit succeeds (line 236), preventing TOCTOU races
- **No Callback on Rollback**: Callback fires inside BeginTx...Commit in Rollback, not after (by design in line 304)

## 2. Event Bus Architecture (notifier.go + handlers.go)

### Notifier Pattern
`event.Notifier` is a **pub/sub dispatcher** registered in `cmdRunAdvance` (run.go, line 368):

```go
notifier := event.NewNotifier()
notifier.Subscribe("log", event.NewLogHandler(...))
notifier.Subscribe("hook", event.NewHookHandler(...))
notifier.Subscribe("spawn", event.NewSpawnHandler(...))
```

The notifier is passed to the phase callback (line 456-467):
```go
phaseCallback := func(runID, eventType, fromPhase, toPhase, reason string) {
    e := event.Event{
        RunID:     runID,
        Source:    event.SourcePhase,
        Type:      eventType,
        FromState: fromPhase,
        ToState:   toPhase,
        Reason:    reason,
        Timestamp: time.Now(),
    }
    notifier.Notify(ctx, e)
}
```

### Subscribers

#### 1. LogHandler (handler_log.go)
- **Purpose**: Print structured event lines to stderr
- **Behavior**: Writes `[event] source=... type=... run=... from=... to=...` to stderr
- **Silent Mode**: Can be silenced with `quiet=true` flag

#### 2. HookHandler (handler_hook.go)
- **Purpose**: Execute convention-based shell hooks
- **Hook Paths**: `.clavain/hooks/on-phase-advance` (phases) or `.clavain/hooks/on-dispatch-change` (dispatches)
- **Mechanism**: 
  - Marshals event to JSON
  - Passes it on stdin to the hook script
  - **Detached goroutine**: Hook runs in background to avoid blocking DB connection (line 53)
  - **Timeout**: 5 seconds (line 18)
  - **Signal delivery**: Hooks run async, so phase advance returns immediately

#### 3. SpawnHandler (handler_spawn.go) — AUTO-SPAWN MECHANISM
- **Purpose**: Auto-spawn agents when phase reaches "executing"
- **Trigger**: `if e.Source != SourcePhase || e.ToState != "executing"` (line 34)
- **Mechanism**:
  1. Queries `ListPendingAgentIDs(ctx, e.RunID)` (line 38)
  2. For each pending agent, calls `spawner.SpawnByAgentID(ctx, agentID)` (line 48)
  3. Logs result ("agent X started" or "agent X failed")
- **Error Handling**: Errors log but don't stop spawning other agents (line 48-51)

### Event Record
The unified `Event` struct (event.go):
```go
type Event struct {
    ID        int64     // auto
    RunID     string
    Source    string    // "phase", "dispatch", "discovery"
    Type      string    // "advance", "block", "pause", "rollback"
    FromState string    // from_phase or from_status
    ToState   string    // to_phase or to_status
    Reason    string    // optional
    Timestamp time.Time
}
```

## 3. ic run advance CLI (run.go, cmdRunAdvance)

### Flow Summary (lines 324-523)
1. Parse `--priority`, `--disable-gates`, `--skip-reason` flags
2. Open DB + create stores (phase, runtrack, event, dispatch)
3. **Create notifier** + subscribe handlers (line 368)
4. Get run info for ProjectDir (line 372)
5. **Subscribe hooks** (line 381)
6. Build **auto-spawn handler** (lines 401-452):
   - Looks up agent by ID
   - Checks for prior dispatch config (reuses model/sandbox/prompt if available)
   - Falls back to convention-based path: `.ic/prompts/{agent_name}.md`
   - Calls `dispatch.Spawn()` to create and start the process
7. **Subscribe spawn handler** (line 453)
8. Call `phase.Advance()` with phaseCallback (line 483-487)
9. Output result as JSON or human-readable (line 501-517)

### Key Lines for Spawn Wiring

**Auto-spawn spawner function (lines 401-452)**:
```go
spawner := event.AgentSpawnerFunc(func(ctx context.Context, agentID string) error {
    agent, err := rtStore.GetAgent(ctx, agentID)  // Get agent record
    if err != nil { return fmt.Errorf("spawn lookup: %w", err) }

    var opts dispatch.SpawnOptions
    opts.ProjectDir = run.ProjectDir
    opts.AgentType = agent.AgentType

    // Reuse prior dispatch config (model, sandbox, prompt)
    if agent.DispatchID != nil { ... }

    // Fallback: convention path
    if opts.PromptFile == "" && agent.Name != nil {
        opts.PromptFile = filepath.Join(run.ProjectDir, ".ic", "prompts", *agent.Name+".md")
    }

    spawnResult, err := dispatch.Spawn(ctx, dStore, opts)
    if err != nil { return fmt.Errorf("spawn: agent %s: %w", agentID, err) }

    // Link dispatch back to agent (CAS: only if not already linked)
    if err := rtStore.UpdateAgentDispatch(ctx, agentID, spawnResult.ID); err != nil {
        if spawnResult.Cmd != nil && spawnResult.Cmd.Process != nil {
            _ = spawnResult.Cmd.Process.Kill()  // Kill orphan on link failure
        }
        return fmt.Errorf("spawn: link dispatch to agent %s: %w", agentID, err)
    }
    return nil
})
notifier.Subscribe("spawn", event.NewSpawnHandler(rtStore, spawner, os.Stderr))
```

**Result processing (lines 519-522)**:
```go
if result.Advanced {
    return 0
}
return 1  // Block/pause = exit code 1
```

## 4. Sprint Advance in lib-sprint.sh (hooks/lib-sprint.sh)

### sprint_advance Function (lines 547-610)

**Current Implementation**:
```bash
sprint_advance() {
    local sprint_id="$1"
    local current_phase="$2"
    
    local run_id=$(_sprint_resolve_run_id "$sprint_id") || return 1
    
    # Budget check
    if [[ -z "${CLAVAIN_SKIP_BUDGET:-}" ]]; then
        "$INTERCORE_BIN" run budget "$run_id" 2>/dev/null
        if [[ $? -eq 1 ]]; then  # Exceeded
            echo "budget_exceeded|$current_phase|..."
            return 1
        fi
    fi
    
    # Call ic run advance (returns JSON)
    result=$(intercore_run_advance "$run_id") || true
    advanced=$(echo "$result" | jq -r '.advanced // false' 2>/dev/null)
    
    if [[ "$advanced" == "false" || "$advanced" == "null" ]]; then
        # Extract event_type and to_phase
        event_type=$(echo "$result" | jq -r '.event_type // ""' 2>/dev/null)
        to_phase=$(echo "$result" | jq -r '.to_phase // ""' 2>/dev/null)
        
        case "$event_type" in
            block) echo "gate_blocked|$to_phase|Gate prerequisites not met" ;;
            pause) echo "manual_pause|$to_phase|auto_advance=false" ;;
            *) ... check if phase changed ...
        esac
        return 1
    fi
    
    # Success: from_phase → to_phase
    from_phase=$(echo "$result" | jq -r '.from_phase // ""' 2>/dev/null)
    to_phase=$(echo "$result" | jq -r '.to_phase // ""' 2>/dev/null)
    
    sprint_invalidate_caches
    sprint_record_phase_tokens "$sprint_id" "$current_phase" 2>/dev/null || true
    echo "Phase: $from_phase → $to_phase (auto-advancing)" >&2
    return 0
}
```

**What it does**:
1. Resolves sprint_id → run_id via bd state lookup
2. Checks remaining token budget (exit 1 = exceeded)
3. Calls `ic run advance <id> --json` via wrapper `intercore_run_advance()`
4. Parses JSON result to check `.advanced` field
5. On success: invalidates discovery cache, records phase tokens, returns 0
6. On block/pause: outputs structured reason (pipe-separated), returns 1

**What it DOESN'T do**:
- No hook invocation (hooks are called by ic automatically)
- No agent spawning (SpawnHandler in ic does that)
- No dispatch creation (auto-spawn mechanism in ic handles that)

## 5. Dispatch Spawning Mechanisms

### Option 1: Auto-Spawn Handler (IMPLEMENTED in ic)
**Trigger**: `PhaseEventCallback` → `notifier.Notify()` → `SpawnHandler` (on phase="executing")
**Mechanism**: 
- Handler calls `spawner.SpawnByAgentID(ctx, agentID)` for each pending agent
- Spawner looks up agent config (model, sandbox, prompt path)
- Calls `dispatch.Spawn()` to create record + start process
- Links dispatch ID back to agent record (CAS)
**Wiring**: Already in place in cmdRunAdvance (lines 401-453)
**Cost**: Happens synchronously during `notifier.Notify()`, which runs AFTER phase commit

### Option 2: Convention-Based Hook (NOT YET USED)
**Trigger**: `HookHandler` invokes `.clavain/hooks/on-phase-advance` script
**Mechanism**: 
- Hook receives JSON event on stdin
- Hook script can inspect phase transition
- Hook script calls `ic dispatch spawn --prompt-file=...` to spawn agents
- Hook runs in detached goroutine (line 53 in handler_hook.go)
**Cost**: Async hook execution, hook must handle errors

### Option 3: Direct Dispatch Record Creation
**Not Yet Implemented**: Could extend AdvanceResult to include dispatch IDs created during phase transition
**Would require**: 
- Extend Run model to include agent list (or query separately)
- Call dispatch.Spawn() inside phase transaction or callback
- NOT recommended: breaks separation of concerns, adds complexity

## 6. Current Wiring Diagram

```
ic run advance <id>
├─ phase.Advance(ctx, store, ..., phaseCallback)
│  ├─ BeginTx()
│  ├─ evaluateGate()
│  ├─ UpdatePhaseQ()
│  ├─ AddEventQ()
│  ├─ Commit()
│  └─ phaseCallback(runID, eventType, fromPhase, toPhase, reason)  [OUTSIDE TX]
│
└─ notifier.Notify(ctx, event)
   ├─ LogHandler    → stderr [echo event]
   ├─ HookHandler   → .clavain/hooks/on-phase-advance [async goroutine]
   └─ SpawnHandler  → spawner.SpawnByAgentID() [SYNC]
      └─ dispatch.Spawn(ctx, dStore, opts)
         ├─ Create dispatch record (DB)
         ├─ Start agent process (exec.Cmd)
         └─ UpdateAgentDispatch() [link back]
```

## 7. Key Findings & Design Insights

### Callback Guarantees
1. **ACID Transaction**: Phase transition, event recording, and status update happen atomically
2. **Callback Outside TX**: Fire-and-forget semantics prevent TOCTOU races
3. **No Error Propagation**: Callback errors are not logged — this is intentional (fire-and-forget design)

### Event Bus Model
- **Synchronous Dispatch**: All handlers called in order (no goroutines in main dispatch path)
- **Async Hook Execution**: Only HookHandler detaches to goroutine (line 53)
- **Auto-Spawn Synchronous**: SpawnHandler runs sync, returns before ic exits
- **Multiple Subscribers**: Notifier pattern allows easy addition of new handlers

### Dispatch Spawning Architecture
- **Auto-Spawn on "executing"**: SpawnHandler is the primary mechanism
- **Agent Pre-Registration**: Agents must be added to run BEFORE phase advance (via ic run agent add)
- **Convention-Based Prompts**: Falls back to `.ic/prompts/{agent_name}.md` if no prior dispatch config
- **Depth Tracking**: Dispatch.ParentDispatchID enables spawn depth limiting (prevents infinite recursion)

### Where the Wiring Happens
- **In cmdRunAdvance (run.go)**: Notifier + handlers are set up
- **In phase.Advance (machine.go)**: Callback is invoked after commit
- **In handlers.go**: SpawnHandler queries agents and calls spawner
- **In dispatch/spawn.go**: Spawn creates DB record + starts process

## 8. How to Wire New Dispatch Spawning Logic

### Scenario 1: Spawn on Different Phase
Extend `SpawnHandler` logic:
```go
// Current: only on "executing"
if e.Source != SourcePhase || e.ToState != "executing" {
    return nil
}

// New: also on other phases if needed
if e.Source != SourcePhase {
    return nil
}
switch e.ToState {
case "executing": ...
case "shipping": ...  // spawn release agents
case "reflect": ...   // spawn retrospective agents
}
```

### Scenario 2: Spawn from Hook Script
Create `.clavain/hooks/on-phase-advance`:
```bash
#!/bin/bash
event=$(cat)  # Read JSON event from stdin
phase=$(echo "$event" | jq -r '.to_state')
run_id=$(echo "$event" | jq -r '.run_id')

case "$phase" in
    executing)
        # Spawn agents for execution phase
        ic dispatch spawn --prompt-file=.ic/prompts/executor.md ...
        ;;
    shipping)
        # Spawn release agents
        ic dispatch spawn --prompt-file=.ic/prompts/releaser.md ...
        ;;
esac
```

### Scenario 3: Pre-Register Agents + Auto-Spawn
Current flow (already implemented):
1. Before calling `ic run advance`:
   ```bash
   ic run agent add <run_id> --type=claude --name=executor
   ic run agent add <run_id> --type=claude --name=reviewer
   ```
2. Call `ic run advance <run_id>`
3. SpawnHandler auto-spawns both agents on "executing" phase

## 9. Sprint Integration Points

### current sprint_advance() flow
1. **Calls**: `intercore_run_advance()` wrapper → `ic run advance --json`
2. **ic side**: phase.Advance() fires phaseCallback → notifier.Notify() → SpawnHandler
3. **SpawnHandler**: Queries agents via rtStore.ListPendingAgentIDs()
4. **Returns to sprint_advance()**: JSON result with from_phase, to_phase, advanced
5. **sprint_advance()**: Parses result, logs phase transition

### Where to Hook Dispatch Spawning
- **Option A (Recommended)**: Pre-register agents via `ic run agent add` BEFORE calling sprint_advance()
- **Option B**: Create `.clavain/hooks/on-phase-advance` hook script for phase-specific spawning logic
- **Option C**: Modify SpawnHandler in ic to support phase-specific spawn rules (requires code change)

## 10. Critical Sections for Future Development

### If Adding Dispatch Rules to Phase Machine
File: `/root/projects/Interverse/infra/intercore/internal/phase/machine.go`
- Line 51-250: `Advance()` function
- Line 237-238: Callback invocation (fire-and-forget)
- Design: Keep callback simple, move complex logic to handlers

### If Adding New Event Handlers
File: `/root/projects/Interverse/infra/intercore/internal/event/handlers.go`
- Pattern: Implement `func Handler(ctx context.Context, e Event) error`
- Subscribe in `cmdRunAdvance` (run.go, line 368+)
- Example: SpawnHandler (handler_spawn.go)

### If Extending Sprint Integration
File: `/root/projects/Interverse/hub/clavain/hooks/lib-sprint.sh`
- Line 547-610: `sprint_advance()` function
- Pre-register agents BEFORE calling `intercore_run_advance()`
- OR: Create `.clavain/hooks/on-phase-advance` for phase-triggered spawning

---

**Document Version**: 1.0 (2026-02-21)  
**Scope**: intercore v1.1.0, Clavain integration, event bus pattern
