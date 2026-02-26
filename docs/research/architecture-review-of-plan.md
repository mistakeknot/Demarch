# Architecture Review: Intent Submission Mechanism
**Plan:** `/home/mk/projects/Demarch/docs/plans/2026-02-26-intent-submission-mechanism.md`
**Bead:** iv-gyq9l
**Date:** 2026-02-26
**Reviewer:** fd-architecture (Claude Sonnet 4.6)

---

## Review Scope

This plan creates `apps/autarch/pkg/clavain/` — a Go subprocess client that routes 5 write operations through `clavain-cli` (L2 OS layer) instead of calling `ic` (L1 kernel) directly from Autarch (L3). The plan mirrors the existing `pkg/intercore/` pattern and includes graceful degradation plus an incremental "track-only" approach for dispatch.

The four specific questions asked:
1. Does the subprocess client pattern preserve layer boundaries correctly?
2. Is the graceful degradation (fallback to direct ic) architecturally sound, or does it undermine the intent?
3. Are there coupling concerns with the wiring approach in Tasks 4-5?
4. Is the incremental approach for dispatch (track-only, not mediate) reasonable?

---

## 1. Boundary and Coupling Analysis

### Layer Boundary Correctness: Sound with One Gap

The subprocess client pattern correctly solves the L3->L2 boundary problem. `pkg/clavain/` lives inside `apps/autarch/`, imports no L2 source code, and communicates only via the `clavain-cli` binary contract. This mirrors `pkg/intercore/` exactly. The type duplication in `types.go` (`SprintCreateResult`, `AdvanceResult`, etc.) is deliberate and correct — shared types would create a compile-time dependency from L3 into L2's Go module, which would be worse than the current bypass.

One genuine gap: `pkg/clavain/` has no health check in `New()`. The `pkg/intercore/` client runs `ic health` at construction time. The clavain client skips this entirely. This matters because `Available()` is the fallback decision point — if `clavain-cli` is on PATH but broken (binary exists, core libraries missing), `Available()` returns true and the app routes calls into a failing client. The `pkg/intercore/` pattern should be followed faithfully here.

**The bypass inventory is correctly classified.** The plan explicitly keeps `ic.StateSet()` at `coldwine.go:420,528,951` as direct calls. Reading the actual codebase confirms `StateSet` writes metadata keys (`epic_id`, `task_id`, `dispatch_id`) linking entities — these are observation writes, not policy transitions. This classification is architecturally correct.

### Dependency Direction: Clean

The plan introduces no new cross-module import. `pkg/clavain/` only imports stdlib. The calling sites in `internal/tui/views/` will add `"github.com/mistakeknot/autarch/pkg/clavain"` to their imports, which is a same-module intra-layer dependency. No circular risk.

### New Dependency Between Independent Modules

The `SprintCommandRouter` in `sprint_commands.go` currently takes only `*intercore.Client`. Task 5 proposes adding a `clavain` client to it. The router's constructor signature will change from `NewSprintCommandRouter(inner, iclient)` to `NewSprintCommandRouter(inner, iclient, clavainClient)`. The plan's code snippet (Task 5 Step 1) does not show how `clavainClient` is passed into `SprintCommandRouter` — it just shows the body of the replaced handler function, assuming the client is already in scope. The constructor change is not planned. This is an execution gap that will cause a compile error when implementing Task 5.

---

## 2. Pattern Analysis

### Pattern Alignment

The `client.go` code in the plan is a faithful copy of `pkg/intercore/client.go` with `ic` replaced by `clavain-cli`. The option pattern, `execRaw`/`execText`/`execJSON` helpers, `ErrUnavailable` sentinel, and `Available()` convenience function all match. This is correct pattern reuse.

Two divergences from the reference pattern are present and both are bugs:

**Divergence 1 — Missing health check.** `pkg/intercore.New()` runs `ic health` and returns `ErrUnavailable` if the check fails. `pkg/clavain.New()` only calls `exec.LookPath`. If `clavain-cli` is installed but broken, the client is constructed successfully and all subsequent calls fail at invocation time with opaque errors rather than at construction time with a clear `ErrUnavailable`.

**Divergence 2 — `baseArgs()` is missing.** `pkg/intercore` uses `baseArgs(useJSON bool)` to prepend `--db` and `--json` flags before any subcommand. The clavain client has no equivalent. `execJSON` in the plan calls `json.Unmarshal` on whatever stdout the binary produces — callers must know whether a given command produces JSON or plain text, creating a contract that is only inferable by reading the binary's source. The intercore pattern is self-documenting about this distinction via `execJSON` vs `execText`. This is a lower-severity divergence since clavain-cli has no `--json` global flag, but the comment discipline could be stronger.

### Anti-Pattern: Goroutine Fire-and-Forget in Task 4

Task 4 Step 3 introduces a goroutine fire-and-forget for agent tracking:

```go
go func() {
    tctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
    defer cancel()
    _ = clavainClient.TrackAgent(tctx, epicID, taskTitle, "task", dispatchID)
}()
```

This is a Bubble Tea concurrency violation. The project's CLAUDE.md states Action closures run on a goroutine pool but Model fields must not be read from them — closures must snapshot data before entering the goroutine. More critically: unmanaged goroutines launched from `tea.Cmd` closures are invisible to Bubble Tea's lifecycle. If the program exits before the goroutine completes, it is leaked. The project memory records this pattern explicitly under "tea.Cmd goroutine safety."

The correct pattern is to fire the tracking as a second `tea.Cmd` returned from the `taskDispatchedMsg` handler, not as a raw goroutine.

### Anti-Pattern: Panic on nil Writer in dispatch.go

Task 3's `dispatch.go` contains:

```go
fmt.Fprintf(nil, "") // no-op, keeping the pattern clear
```

`fmt.Fprintf(nil, ...)` panics in Go — `nil` does not satisfy `io.Writer`. This code will compile but panic at runtime if the error branch is hit. Remove the line.

### Premature Abstraction in gate.go and artifact.go

`gate.go` defines `EnforceGate()` and `GateOverride()`. Looking at `clavain-cli`'s actual command surface (`main.go`), `enforce-gate` exists but `gate-override` does not. `GateOverride` returns `ErrUnavailable` immediately — it is an unimplemented stub that always errors. Neither `EnforceGate` nor `GateOverride` appear as callers in Tasks 4-5.

Similarly, `artifact.go`'s `SetArtifact` and `GetArtifact` have no callers in Tasks 4-5. The bypass inventory table explicitly says `ic.StateSet()` artifact calls are kept as-is.

Both files are dead code in this sprint. Their presence increases the new package's surface area without providing behavioral coverage. Per the project's YAGNI guideline ("Check new abstractions have more than one real caller before extraction"), both files should be deferred.

---

## 3. Graceful Degradation: Correct Intent, Structural Problem

The graceful degradation strategy is architecturally sound in principle. It mirrors the existing `iclient == nil` guard pattern used throughout `ColdwineView`. The fallback preserves operational continuity and allows incremental deployment.

However, the wiring code for sprint advance in Task 4 Step 4 is structurally wrong:

```go
if clavainClient != nil {
    _, advErr := clavainClient.SprintAdvance(ctx, beadID, currentPhase)
    if advErr != nil {
        result, err = ic.RunAdvance(ctx, runID)  // fallback on failure
    } else {
        result, err = ic.RunAdvance(ctx, runID)  // same call on success
    }
} else {
    result, err = ic.RunAdvance(ctx, runID)
}
```

Both branches of `advErr` call `ic.RunAdvance`. The plan's comment says this is intentional: "clavain-cli sprint-advance enforces gate policy, then we re-read the result from ic for TUI rendering." But this is a double-advance. Reading `clavain-cli/sprint.go` (cmdSprintAdvance) confirms it calls `ic run advance` internally. Calling `ic.RunAdvance` again afterward attempts to advance the run a second time. The second call will either silently succeed (advancing an already-advanced run) or return an error that is then surfaced to the TUI as an advance failure when the first advance actually succeeded.

This must be resolved before implementation. Two valid options:

**Option A (pre-flight only):** Call `clavain-cli enforce-gate` (which exists and does not advance) as the L2 check, then call `ic.RunAdvance` once if the gate passes. This splits the gate enforcement from the advance execution.

**Option B (full mediation):** Call `clavain-cli sprint-advance` and let it own the advance. After success, call `ic.RunStatus` (a read, not a write) to get the typed `AdvanceResult` for TUI rendering.

Option A fits the "incremental" framing better since it requires no changes to how clavain-cli's sprint-advance output is parsed.

### Fallback as Permanent Architecture Risk

The plan's "Scope Notes" defer removing fallback branches until "clavain-cli is guaranteed installed." This is a valid short-term position, but the fallback creates an invisible testing gap: integration tests running without clavain-cli only exercise the fallback path, not the primary path. The plan should note that integration tests must run with clavain-cli present to validate L2 routing is actually engaged.

---

## 4. Dispatch Incremental Approach: Acceptable but Misnamed

The decision to track rather than mediate dispatch is architecturally reasonable. It separates observation from control, and the L2 OS layer learns about dispatches without blocking or controlling them.

The structural problem is that `DispatchTask()` always returns an error:

```go
return "", fmt.Errorf("dispatch-task not yet mediated by clavain-cli — use ic.DispatchSpawn() and call clavain.TrackAgent() separately")
```

A method that always errors is not a callable API — it is a stub masquerading as a function. Any caller that follows the signature must handle an error that is not a transient failure but a permanent design decision. This couples callers to a temporary implementation state.

The method should be either:
- Renamed `TrackDispatch(ctx, beadID, agentName string, agentType, dispatchID string) error` with non-fatal semantics (absorb failure, log if possible), or
- Removed from this sprint entirely, leaving only `TrackAgent` exported.

---

## 5. Wiring Coupling Assessment (Tasks 4-5)

### SprintCreate Return Value Impedance Mismatch

`ic.RunCreate` returns a run ID (plain base36 string). `clavain-cli sprint-create` returns a bead ID. The TUI's `sprintCreatedMsg` carries `runID` as its primary key. Task 4 Step 2 assigns `runID = beadID` with the comment "will resolve in state write," but no resolution is implemented in Task 4. The `sprintCreatedMsg` handler downstream expects a run ID for display and state linkage.

The plan's private `resolveRunID(ctx, beadID)` method in `sprint.go` does exactly what is needed — it calls `sprint-read-state` and parses the JSON to extract the run ID. This method must be called explicitly after `SprintCreate` returns. Skipping this step means the TUI shows a bead ID where a run ID is expected, and downstream `ic.StateSet` calls will use the wrong identifier.

This is a behavioral correctness issue, not just a style note.

### ColdwineView Client Initialization Placement

Task 4 Step 1 says to add the clavain client "In the struct or constructor" with an inline `clavain.New()` call. The correct location is as a named field `cclient *clavain.Client` on `ColdwineView`, initialized alongside `iclient` in the view's constructor. Initializing inside an `Action` closure will construct a new client on every command invocation — calling `exec.LookPath` on every palette menu action. This is minor performance waste but is also inconsistent with the `iclient` pattern.

### Missing Field Declaration and Constructor Update for SprintCommandRouter

`SprintCommandRouter` has an `iclient *intercore.Client` field declared on the struct. Task 5 adds clavain calls inside handler methods but does not:
1. Add a `cclient *clavain.Client` field to the struct
2. Update `NewSprintCommandRouter` to accept and store it
3. Show where `NewSprintCommandRouter` is called to wire in the new client

All three omissions must be addressed before Task 5 compiles.

---

## 6. YAGNI Assessment

The planned file layout is wider than this sprint's actual scope:

| File | Callers in plan | Assessment |
|------|----------------|------------|
| `client.go` | All tasks | Keep |
| `types.go` | All tasks | Keep |
| `sprint.go` | Tasks 4-5 | Keep |
| `dispatch.go` | Task 4 (TrackAgent only) | Trim: remove DispatchTask stub, keep TrackAgent |
| `gate.go` | None | Defer entirely |
| `artifact.go` | None | Defer entirely |

Reducing to 5 files and removing 2 unimplemented stubs is a smaller viable change that still achieves the sprint's stated goal. `gate.go` and `artifact.go` should be created when their callers are wired in, which is explicitly deferred future work.

---

## Summary of Findings

### Must-Fix (behavioral or compilation failures)

1. **Double-advance in SprintAdvance wiring** (Task 4 Step 4): Both branches of `advErr` call `ic.RunAdvance`. Since `clavain-cli sprint-advance` calls `ic run advance` internally, this advances the run twice on success. Use Option A (call `enforce-gate`, then `ic.RunAdvance` once) or Option B (let clavain own the advance, read back via `ic.RunStatus`).

2. **BeadID assigned as RunID** (Task 4 Step 2): `runID = beadID` in `sprintCreatedMsg` is incorrect. Call `clavainClient.resolveRunID(ctx, beadID)` (or the equivalent public helper) before constructing the message.

3. **`fmt.Fprintf(nil, "")` panics at runtime** (Task 3 dispatch.go): Remove the line.

4. **SprintCommandRouter constructor not updated** (Task 5): Add `cclient *clavain.Client` field, update `NewSprintCommandRouter` signature, and update the construction callsite.

### Recommended Fixes (reduce risk and entropy)

5. **Add health check to `clavain.New()`**: Call `clavain-cli` with a lightweight no-op to verify execution. Aligns with `pkg/intercore` reference pattern.

6. **Replace raw goroutine with tea.Cmd** (Task 4 Step 3): Move `TrackAgent` call into a `tea.Cmd` returned from the `taskDispatchedMsg` handler, not a raw `go func()`.

7. **Rename or remove `DispatchTask()`**: A method that always returns an error is not an API. Either expose `TrackAgent` directly, or name it `TrackDispatch` with non-fatal semantics.

8. **Defer `gate.go` and `artifact.go`**: No callers exist in this sprint. Creating stub files now violates YAGNI and inflates the package surface.

9. **Move clavain client init to ColdwineView field**: Consistent with `iclient` pattern, avoids repeated `exec.LookPath` calls.

---

## Verdict

The strategic direction is correct. The subprocess client pattern preserves L3->L2 boundaries without compile-time coupling, the bypass inventory is correctly classified, and the incremental track-only approach for dispatch is a pragmatic fit for the sprint's scope. The overall structure mirrors established `pkg/intercore/` conventions appropriately.

Four must-fix issues in Tasks 3-5 will cause panics, incorrect run state, or compile failures. None require redesign — they are implementation-level corrections. The plan should be annotated with these corrections before execution, or the implementing agent must be made aware of them.
