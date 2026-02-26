# Correctness Review — Intent Submission Mechanism (iv-gyq9l)

**Plan reviewed:** docs/plans/2026-02-26-intent-submission-mechanism.md
**Verdict file:** .clavain/verdicts/fd-correctness-intent-plan.md
**Reviewer:** Julik (fd-correctness)
**Date:** 2026-02-25

---

## First Step: Invariant Inventory

These are the behavioral contracts that must remain true after this plan lands. Findings are tied back to these invariants.

**INV-1 (Sprint ID coherence):** Any call to `SprintCreate` must resolve to one canonical ic run ID before that ID is used for downstream metadata writes. Holding a bead ID where a run ID is expected is silent corruption of the sprint registry.

**INV-2 (No half-committed sprints):** If the L2 path (clavain-cli) succeeds in creating a sprint and the code then falls through to `ic.RunCreate` as a "fallback," there will be two ic runs for one intent. The fallback must only fire when clavain-cli definitively fails, not after it succeeds.

**INV-3 (TrackAgent non-interference):** The goroutine spawned by the dispatch tracking path must operate on a scoped context tied to the dispatch it was created for, not the ambient TUI state at the time it wakes.

**INV-4 (Advance idempotency):** Calling clavain-cli sprint-advance and then calling ic.RunAdvance in the same code path is a double-advance. This bypasses phase gates and is exactly the invariant the OS layer was built to protect.

**INV-5 (Error signal fidelity):** Errors from subprocess calls in policy-enforcing paths must be visible. Swallowed errors defeat the OS layer silently.

---

## Codebase State Observed

Before assessing the plan's proposed changes, I verified the current state of the files being modified.

**coldwine.go:990** — `ic.DispatchSpawn` is called inside a `tea.Cmd` closure that correctly snapshots mutable values (`ic`, `taskID`, `taskTitle`, `runID`) before entering the goroutine. The existing dispatch pattern is safe.

**coldwine.go:1121** — `ic.RunCreate` is called with `intercore.WithScopeID(epicID)`. The result `runID` is immediately packaged into `sprintCreatedMsg{runID: runID, epicID: epicID, ...}` and dispatched back to the Bubble Tea model. The message handler then uses `runID` for `ic.StateSet` linking calls.

**coldwine_mode.go:87 (advancePhase)** — Correctly snapshots `runID = v.runs[v.selectedRun].ID` before the closure. The existing advance is a single `ic.RunAdvance` call with a 10-second timeout. Clean.

**coldwine_mode.go:102 (cancelRun)** — Single `ic.RunCancel` call with a 5-second timeout. Clean.

**sprint_commands.go:83 (advance)** — Calls `ic.RunList` then `ic.RunAdvance(ctx, runs[0].ID)` inside an `asyncResponse` goroutine. The context is the one passed to `HandleMessage`.

**sprint_commands.go:127 (create)** — Calls `ic.RunCreate(ctx, ".", goal)` inside `asyncResponse`. No scope ID is set here (sprint_commands has no epic context).

**sprint_commands.go:183 (dispatch spawn)** — Calls `ic.DispatchSpawn(ctx, runs[0].ID, ...)` inside `asyncResponse`. Same pattern.

The existing code is TOCTOU-aware (the comment at line 75 in coldwine_mode.go says "NOT from a cached activeRun pointer") and Bubble Tea threading model-safe (closures snapshot before goroutine entry). The plan's proposed additions must not regress these properties.

---

## Finding 1: Bead ID Assigned as Run ID (BLOCKING, P0)

**Plan location:** Task 4, Step 2
**Invariant violated:** INV-1

The plan's replacement for `coldwine.go:1121` shows:

```go
beadID, err := clavainClient.SprintCreate(ctx, goal,
    clavain.WithSprintComplexity(3),
)
if err != nil {
    runID, err = ic.RunCreate(...)
} else {
    runID = beadID  // assigns bead ID as run ID
}
```

The comment below this block says "The TUI needs the run ID — will resolve in state write." But `runID` is immediately returned via `sprintCreatedMsg{runID: runID, ...}` and that message's handler passes `runID` to `ic.StateSet` for epic-to-run linking. The resolution never happens.

Bead IDs (e.g., `iv-abc12`) and ic run IDs (e.g., `5k9z2xmn`, base36 alphanumeric) are different namespaces. The ic kernel will reject or silently misroute a StateSet call made with a bead ID. The sprint exists in L2 but the epic link in L1 is broken.

**Concrete failure sequence:**

1. User creates sprint from epic `epic-001`.
2. `clavainClient.SprintCreate` succeeds, returns `"iv-abc12"` (a bead ID).
3. `runID` is assigned `"iv-abc12"`.
4. `sprintCreatedMsg{runID: "iv-abc12", epicID: "epic-001"}` is returned to the model.
5. Message handler calls `ic.StateSet(ctx, "iv-abc12", "scope", "epic-001")`.
6. ic kernel sees an unknown run key `"iv-abc12"`, either rejects or silently drops.
7. Epic `epic-001` shows no sprint in the TUI. User creates another. Now there are two L2 sprints for one intent.

The `resolveRunID` function exists in the plan's `sprint.go` and would fix this. It is never called in the wiring step.

**Fix:** Immediately after `SprintCreate` returns, call `runID, err = clavainClient.resolveRunID(ctx, beadID)`. Handle that error as a fatal sprint creation failure. Alternatively, have `clavain-cli sprint-create --json` emit `{"bead_id": "iv-abc12", "run_id": "5k9z2xmn"}` and parse it using the `SprintCreateResult` type already defined in `types.go`.

---

## Finding 2: Double-Advance in Success Branch (BLOCKING, P0)

**Plan location:** Task 4, Step 4
**Invariant violated:** INV-4

The plan's replacement for `coldwine_mode.go` advance shows:

```go
if clavainClient != nil {
    _, advErr := clavainClient.SprintAdvance(ctx, beadID, currentPhase)
    if advErr != nil {
        result, err = ic.RunAdvance(ctx, runID)  // fallback path: correct
    } else {
        result, err = ic.RunAdvance(ctx, runID)  // success path: BUG
    }
}
```

Both branches call `ic.RunAdvance`. The success-branch comment says "Re-fetch result from ic for TUI rendering" — but `ic.RunAdvance` does not read state; it mutates it. It advances the phase.

`clavain-cli sprint-advance` internally calls `ic RunAdvance` to perform the advancement. The plan's success branch then calls `ic.RunAdvance` a second time. The phase advances twice in a single user action.

**Concrete failure sequence:**

1. Run is in phase `brainstorm`. Gate is open.
2. User presses 'a' to advance.
3. `SprintAdvance` shells out to clavain-cli, which calls `ic RunAdvance` internally.
4. Run moves: `brainstorm` to `brainstorm-reviewed`. Gate for next phase is not yet open.
5. `advErr == nil`. Plan enters the "success" branch.
6. Plan calls `ic.RunAdvance(ctx, runID)` again.
7. ic evaluates the gate for `brainstorm-reviewed -> planning`.
8. If gate is open: run moves to `planning`. Two phases consumed in one keypress. A gate-guarded phase was bypassed.
9. If gate is blocked: `ic.RunAdvance` returns a blocked result. TUI shows "Gate blocked" even though the first advance succeeded. User is confused.

Either outcome is wrong. The double-advance is the exact kind of gate bypass the OS layer was designed to prevent.

**Fix:** In the success branch, do not call `ic.RunAdvance`. Instead call `ic.RunGet(ctx, runID)` to read current run state after clavain-cli's advance, and synthesize an `AdvanceResult` from the difference between `currentPhase` and the fetched run's phase. Or have `clavain-cli sprint-advance` emit structured JSON (`from_phase`, `to_phase`, `advanced`, `reason`) and parse it. The `AdvanceResult` type is already defined in `types.go`.

---

## Finding 3: `fmt.Fprintf(nil, "")` — Undefined Behavior (P1)

**Plan location:** Task 3, dispatch.go, `DispatchTask`
**Invariant violated:** INV-5

```go
_, err := c.execText(ctx, args...)
if err != nil {
    // Non-fatal: tracking failure doesn't block dispatch
    fmt.Fprintf(nil, "") // no-op, keeping the pattern clear
}
```

`fmt.Fprintf` requires a non-nil `io.Writer`. Passing `nil` compiles because interface nil satisfies the type signature, but `fmt.Fprintf` calls `w.Write(p)` on the writer at runtime. For an empty format string with no arguments, Go's fmt package may optimize away the write — making this appear to work. But:

1. `go vet` flags calls to `fmt.Fprintf` with a nil first argument. This breaks `go test ./...` in the default vet-enabled mode.
2. Any future change adding a format verb to the string literal will cause a guaranteed nil-pointer dereference.
3. The tracking error is completely silenced. The OS layer cannot know that TrackAgent failed.

**Fix:** Remove the line. If stderr logging is desired: `fmt.Fprintf(os.Stderr, "clavain: TrackAgent failed (non-fatal): %v\n", err)`.

---

## Finding 4: asyncResponse Context Not Propagated to Subprocess (P1)

**Plan location:** Task 5, sprint_commands.go wiring
**Invariant violated:** INV-3 (partial)

The existing `asyncResponse` function:

```go
func asyncResponse(fn func() string) <-chan pkgtui.StreamMsg {
    ch := make(chan pkgtui.StreamMsg, 2)
    go func() {
        defer close(ch)
        result := fn()
        ...
    }()
    return ch
}
```

The context from `HandleMessage(ctx context.Context, ...)` is captured in each closure but `asyncResponse` has no mechanism to signal the goroutine to stop if the caller's context is cancelled. Existing ic calls complete in milliseconds. The new clavain-cli subprocess calls have a `DefaultTimeout` of 15 seconds.

If the user closes the chat panel or the TUI session ends while a clavain-cli subprocess is running, the subprocess continues for up to 15 seconds — potentially holding file locks, writing to shared state, or emitting events into ic after the caller no longer cares about the result.

The buffered channel size of 2 prevents a goroutine leak: the goroutine will send its two messages into the buffer and exit. But the subprocess itself runs to timeout or completion regardless.

**Fix:** Change `asyncResponse` to accept and propagate context: `asyncResponse(ctx context.Context, fn func(ctx context.Context) string)`. Each clavain-cli call inside the closure already accepts a context — pass it through. The subprocess will be killed when the caller's context is cancelled.

---

## Finding 5: Line-Scanning JSON Parser in resolveRunID (P2)

**Plan location:** Task 2, sprint.go
**Invariant violated:** INV-1 (dependent path)

```go
for _, line := range strings.Split(state, "\n") {
    line = strings.TrimSpace(line)
    if strings.HasPrefix(line, `"id"`) {
        parts := strings.SplitN(line, ":", 2)
        ...
    }
}
```

Failure modes: (1) Matches any JSON key starting with `"id"` at any nesting depth — `"identity"`, `"idle_timeout"`, a nested `"id"` inside a phase object. (2) If `sprint-read-state` outputs compact JSON (single line), the loop finds nothing and returns an error. (3) The colon split breaks on RFC3339 timestamps or any value containing a colon.

`resolveRunID` is on the critical path for INV-1 correctness. It must be robust.

**Fix:**
```go
var obj struct {
    ID string `json:"id"`
}
if err := json.Unmarshal([]byte(state), &obj); err != nil {
    return "", fmt.Errorf("resolveRunID: invalid JSON: %w", err)
}
if obj.ID == "" {
    return "", fmt.Errorf("could not resolve run ID for bead %s", beadID)
}
return obj.ID, nil
```

---

## Finding 6: GetArtifact Swallows All Errors (P2)

**Plan location:** Task 3, artifact.go
**Invariant violated:** INV-5

```go
func (c *Client) GetArtifact(...) (string, error) {
    result, err := c.execText(ctx, "get-artifact", beadID, artifactType)
    if err != nil {
        return "", nil // missing artifact is not an error
    }
    return result, nil
}
```

The comment says "missing artifact is not an error" but returns `("", nil)` for every error — subprocess crash, context timeout, permission denied, binary not found. A caller deciding whether to re-submit an artifact based on an empty return will silently skip submission after any transient subprocess failure.

**Fix:** Define a "not found" exit code or stderr pattern in the clavain-cli protocol. Return `("", nil)` only for that specific case. Return the error for all others.

---

## Direct Answers to the Prompt's Five Questions

**Q1: Sprint creation returns bead ID but TUI needs run ID — is the resolution correct?**
No. The plan acknowledges the mismatch, documents `resolveRunID`, but the wiring step assigns `runID = beadID` without calling `resolveRunID`. Finding 1 is the direct consequence.

**Q2: Fallback paths — could this create inconsistent state?**
Yes. If `SprintCreate` succeeds in L2 (clavain-cli ran and created the sprint) but the subsequent `resolveRunID` call fails (e.g., network timeout), the code falls through to `ic.RunCreate`. This creates a second ic run for the same sprint intent, orphaned from the L2 bead. The plan has no rollback for this scenario.

**Q3: Concurrent goroutine for TrackAgent at coldwine.go:990 — race conditions?**
The plan's proposed goroutine creates its own `context.Background()` (not derived from a parent), and captures `epicID`, `taskTitle`, and `dispatchID` which are already snapshotted by the outer closure. No race condition. The goroutine is safe. The concern is error visibility (Finding 3) not a data race.

**Q4: sprint-advance calls clavain-cli then re-reads from ic — state change between calls?**
The re-read is actually a second write (`ic.RunAdvance`), not a read. See Finding 2. Once fixed to use `ic.RunGet`, the TOCTOU risk is display-only: between clavain-cli's advance and the RunGet read, auto-advance could advance the run again. The TUI would show a stale "from_phase." Acceptable — this is a display artifact, not data corruption.

**Q5: Error handling in dispatch.go — the `fmt.Fprintf(nil, "")` pattern.**
This is not a no-op. See Finding 3. Remove it.

---

## Summary Table

| # | Severity | Location | Invariant | Issue |
|---|----------|----------|-----------|-------|
| 1 | P0 BLOCK | Task 4 Step 2, coldwine.go:1121 | INV-1 | Bead ID assigned to runID, breaking ic metadata writes |
| 2 | P0 BLOCK | Task 4 Step 4, coldwine_mode.go advance | INV-4 | Double-advance: clavain-cli + ic.RunAdvance both called in success path |
| 3 | P1 | Task 3, dispatch.go DispatchTask | INV-5 | `fmt.Fprintf(nil, "")` — undefined behavior, masks tracking errors |
| 4 | P1 | Task 5, sprint_commands.go asyncResponse | INV-3 | Context not propagated to clavain-cli subprocess goroutines |
| 5 | P2 | Task 2, sprint.go resolveRunID | INV-1 | Line-scanning JSON parser matches wrong keys silently |
| 6 | P2 | Task 3, artifact.go GetArtifact | INV-5 | All subprocess errors swallowed, not just "not found" |

**Verdict: CONDITIONAL PASS.** Two P0 findings must be resolved before implementation begins. The design is sound; the wiring is wrong in two specific places.
