# Correctness Review: Broadcast Confirmation Flow Implementation Plan
**Reviewer:** Julik (Flux-drive Correctness Reviewer)
**Date:** 2026-02-23
**Plan file:** `apps/autarch/docs/plans/2026-02-23-broadcast-confirmation-flow.md`
**Status:** Issues found — plan has one genuine lifetime/data-race concern, two logic bugs, and one test correctness problem. The threading model analysis in the prompt is correct; clarifications follow.

---

## Invariants Established Before Review

From CLAUDE.md, AGENTS.md, and project MEMORY.md:

1. **Bubble Tea threading model:** `Model.Update()` and `View()` are always called on the same goroutine. All mutations to model fields happen serially — no mutex is needed for fields that are only accessed from `Update()` and `View()`. This is the authoritative statement from the project.
2. **`tea.Cmd` callbacks run on a separate goroutine.** A function that satisfies `tea.Cmd` is `func() tea.Msg`. Bubble Tea runs these in a goroutine pool. The callback runs concurrently with respect to other `Update()` cycles.
3. **`Palette` is a value type (`*Palette` pointer field inside `UnifiedApp`).** Bubble Tea copies `UnifiedApp` on every `Update()`. Because `palette` is a `*Palette`, all copies share the same heap-allocated `Palette`. Mutations to `*Palette` fields in `Update()` are visible to the next `Update()` call.
4. **`tmux.Client.run()` delegates to `Runner.Run()`** which calls `exec.Command` — a new `exec.Cmd` per invocation. No shared mutable state in `run()`. Concurrent calls from multiple goroutines are safe.
5. **The `sessionCache` in `tmux.Client` is protected by `sync.RWMutex`.** Concurrent reads and writes to the cache are safe.
6. **`-race` is required** for all test runs (autarch CLAUDE.md).
7. **`Command.Action func() tea.Cmd` is a function value captured at registration time.** It is set once in `initPaletteCommands` / `updateCommands` and never mutated thereafter.

---

## Finding 1 (HIGH): `pendingCmd *Command` Points Into a Slice That `SetCommands` Replaces — Use-After-Free

**Severity:** High. Silent use of stale data. Any call to `updateCommands()` while the palette is in `PhaseTarget` or `PhaseConfirm` invalidates `pendingCmd`.

**Location:**
- Plan Task 3, the struct addition: `pendingCmd *Command`
- `palette.go` `Selected()` method (existing, line 80): `return &p.commands[idx]`
- `updateCommands()` in `internal/tui/unified_app.go` (line 615): calls `a.palette.SetCommands(cmds)` which replaces `p.commands`

**The mechanism.**

`pendingCmd` is set in `updateCommandPhase`:
```go
p.pendingCmd = cmd  // cmd is &p.commands[idx] from Selected()
p.phase = PhaseTarget
```

`Selected()` returns `&p.commands[idx]` — a pointer directly into the backing array of `p.commands`.

`SetCommands` replaces the slice:
```go
func (p *Palette) SetCommands(cmds []Command) {
    p.commands = cmds   // old backing array is abandoned
    p.updateMatches()
}
```

After `SetCommands`, the old backing array may be garbage collected. `pendingCmd` now points to freed memory. In Go, the GC does not immediately reclaim, but if the GC runs between `SetCommands` and the final `Enter` confirm, the `pendingCmd.Action()` call dereferences potentially collected memory.

**Concrete interleaving that corrupts.**

1. User opens palette, filters to "Send Prompt to Agents", presses Enter.
2. `updateCommandPhase`: `p.pendingCmd = &p.commands[N]` (pointer into current backing array).
3. `p.phase = PhaseTarget` is set.
4. Meanwhile, some Bubble Tea event (e.g., `tea.WindowSizeMsg` or a new command from `updateCommands`) causes `UnifiedApp.Update()` to call `a.updateCommands()`.
   - Actually, looking at the code: `updateCommands()` is only called from `enterDashboard()`. It does NOT run during normal Update cycles. So in the current implementation this race does not trigger through `updateCommands()` unless dashboard is re-entered.
   - However, the broader problem remains: `SetCommands` is a public API and **any caller** that replaces the commands slice while the palette is mid-flow invalidates `pendingCmd`.
5. User presses "1" (target), then Enter (confirm). `updateConfirmPhase` calls `p.pendingCmd.Action()`.
6. If GC ran between steps 4 and 5, this is a use-after-free. In practice, the Command value may have been copied to the new slice, so the value is still valid — but this is fragile and implementation-dependent.

**Why this is real, not theoretical.** Even if `updateCommands()` is only called at init today, the pattern `pendingCmd *Command` pointing into a replaceable slice is architecturally wrong. A future developer adding a "refresh commands" flow, or the plan's Task 6 itself (which adds new broadcast commands via `updateCommands`), could trigger this in a multi-step onboarding sequence.

**Minimum fix.** Store the `Command` value, not a pointer to the slice element:

```go
// In palette struct:
pendingCmd *Command  →  pendingCmd Command  // store a copy
hasPendingCmd bool

// In updateCommandPhase:
if cmd.Broadcast {
    p.pendingCmd = *cmd   // copy the value (including the Action func)
    p.hasPendingCmd = true
    p.phase = PhaseTarget
    ...
}

// In updateConfirmPhase:
case "enter":
    if p.hasPendingCmd {
        action := p.pendingCmd.Action
        p.Hide()    // Hide() clears hasPendingCmd
        return p, action()
    }
```

`Hide()` should set `hasPendingCmd = false`. `Action` is a `func() tea.Cmd` — a function pointer (header + closure data pointer), copied by value, safe to retain.

---

## Finding 2 (HIGH): `Action` Closure in Integration Test Reads Palette Fields After `Hide()` — Data Reads Stale State

**Severity:** High in the test as written; HIGH if the same pattern propagates to production broadcast commands.

**Location:** Plan Task 7, `TestPalette_FullBroadcastFlow`:

```go
{Name: "Send Prompt", Broadcast: true, Action: func() tea.Cmd {
    executedTarget = p.target        // reads p.target
    executedCounts = p.paneCounts    // reads p.paneCounts
    return nil
}},
```

`p.Hide()` is called inside `updateConfirmPhase` **before** `action()` is invoked:

```go
func (p *Palette) updateConfirmPhase(msg tea.KeyMsg) (*Palette, tea.Cmd) {
    switch msg.String() {
    case "enter":
        if p.pendingCmd != nil {
            action := p.pendingCmd.Action
            p.Hide()                  // <-- Hide() resets p.phase = PhaseCommand, p.pendingCmd = nil
            return p, action()        // action() runs as a tea.Cmd — separate goroutine
        }
    }
}
```

`action()` is returned as a `tea.Cmd`. Bubble Tea runs it on a **separate goroutine** after `Update()` returns. At that point:
- `p.phase` has been reset to `PhaseCommand` by `Hide()`
- `p.target` may still hold the selected value (Hide doesn't reset `p.target` in the proposed code — it only resets `phase` and `pendingCmd`)
- `p.paneCounts` is uncleared

So in the specific test, reading `p.target` and `p.paneCounts` after `Hide()` happens to be safe *today* because `Hide()` does not clear them. But this is coupling the test to `Hide()`'s implementation details.

**The deeper production concern.** The plan for Task 6's broadcast `Action` stubs say:
```go
Action: func() tea.Cmd {
    // TODO: implement actual send-to-panes via tmux SendKeys
    return nil
},
```

When this TODO is filled in, the real Action will need to know which target and pane counts were selected. The natural temptation is to close over `p` or `a` (the palette or app pointer). If the Action reads `p.target` and `p.paneCounts` from the goroutine that Bubble Tea runs `tea.Cmd` on, it is reading fields that are also being written by `Update()` on its own goroutine. That is a data race detectable by `-race`.

**The correct pattern.** Pass the resolved context to `Action` at the time it is dispatched — before `Hide()` clears state. The plan already defines `BroadcastAction` for this purpose but never uses it:

```go
// In palette_types.go (already in plan):
type BroadcastAction struct {
    Target     Target
    PaneCounts PaneCounts
}
```

Modify `Action` signature to accept a `BroadcastAction`, or capture the values at dispatch time inside `updateConfirmPhase`:

```go
case "enter":
    if p.hasPendingCmd {
        action := p.pendingCmd.Action
        // Capture the resolved context NOW, before Hide() may clear it
        captured := BroadcastAction{
            Target:     p.target,
            PaneCounts: p.paneCounts,
        }
        _ = captured  // pass to action or store in a cmd wrapper
        p.Hide()
        return p, action()  // action() should use `captured`, not read from `p`
    }
```

Because `Command.Action` is `func() tea.Cmd`, the cleanest approach is to define broadcast commands with a different signature and wrap:

```go
// Register as:
Action: func() tea.Cmd {
    // palette calls this after setting target; capture from closure here
    // This closure is called from Hide() path — use the captured value:
    return broadcastSendPrompt(captured.Target, captured.PaneCounts)
},
```

Alternatively, as noted in Finding 1's fix, store `pendingCmd` as a `Command` value copy (not pointer), and extend `Command` with a `BroadcastAction` field that is populated by the palette before calling `Action`:

```go
type Command struct {
    Name        string
    Description string
    Action      func() tea.Cmd
    Broadcast   bool
    // Populated by palette at confirm time — read-only by the time Action is called:
    ResolvedBroadcast BroadcastAction
}
```

The specific approach is flexible; the invariant is: **do not read palette fields from inside a `tea.Cmd` goroutine.**

---

## Finding 3 (MEDIUM): `FetchPaneCounts func() tea.Msg` Is Called as `tea.Cmd` — Missing Goroutine Boundary Acknowledgment in the Test

**Severity:** Medium. Test in Task 5 (`TestPalette_TargetPhaseReturnsFetchCmd`) confirms a non-nil `cmd` is returned, but does not call the `cmd` and feed the result back as a `PaneCountMsg`. The full round-trip is only tested by the integration test in Task 7, which uses a synchronous stub.

This is not a race condition by itself, but it creates a gap: the async path through `FetchPaneCounts` is never tested under the `-race` detector with a real goroutine.

**The actual async path:**

In `unified_app.go` (plan Task 5 Step 4):
```go
a.palette.FetchPaneCounts = func() tea.Msg {
    if a.tmuxClient == nil {
        return PaneCountMsg{}
    }
    panes, err := a.tmuxClient.GetAgentPanes(a.sessionName)
    ...
    return PaneCountMsg{Counts: counts}
}
```

This closure captures `a.tmuxClient` and `a.sessionName`. The function runs on a goroutine Bubble Tea allocates for `tea.Cmd` execution. At that point, `a.tmuxClient` is being read (not written). `a.sessionName` is a `string` (value type, immutable). `tmuxClient` is a `*tmux.Client` pointer — the pointer itself is read, and `GetAgentPanes` only uses `c.runner` (which is set once at construction) and creates new `exec.Command` instances per call. The `sessionCache` mutex inside `Client` protects concurrent reads. This specific path is safe.

**However, the plan does not note that `a.sessionName` must be immutable after the palette's `FetchPaneCounts` is set.** If any code path mutates `a.sessionName` (e.g., a future feature to rename sessions), the goroutine would race on the string header. Go strings are technically value-copied on assignment, so a read-write race on `a.sessionName` itself would need to be synchronized. This is a documentation gap, not a current bug.

**Recommendation.** Add a comment in `unified_app.go` noting that `sessionName` must not be mutated after palette setup, or capture it at setup time:

```go
sessionName := a.sessionName   // capture at setup time
a.palette.FetchPaneCounts = func() tea.Msg {
    if a.tmuxClient == nil {
        return PaneCountMsg{}
    }
    panes, err := a.tmuxClient.GetAgentPanes(sessionName)  // use local copy
    ...
}
```

---

## Finding 4 (MEDIUM): `updateTargetPhase` Returns No Error for Invalid Key — Silent No-Op

**Severity:** Medium. Not a correctness bug in the strict sense, but the user experience is: pressing any key other than 1-4 or Esc in target phase silently does nothing, including pressing Enter, which a user might try if they only know Enter confirms things.

**Location:** Plan Task 3, `updateTargetPhase`:
```go
func (p *Palette) updateTargetPhase(msg tea.KeyMsg) (*Palette, tea.Cmd) {
    switch msg.String() {
    case "esc":  ...
    case "1":    ...
    case "2":    ...
    case "3":    ...
    case "4":    ...
    }
    return p, nil   // any other key: silent no-op
}
```

Specifically, `enter` in target phase returns `nil` and stays in target phase. This is intentional — the user must press a number. But it means the palette is unresponsive to Enter. The existing tests do not verify that Enter in target phase is a no-op (and not accidentally consumed by the wrong branch).

**Recommendation.** This is acceptable behavior, but add a test:
```go
func TestPalette_TargetPhaseEnterIsNoOp(t *testing.T) {
    // Verify Enter does not advance to confirm phase
}
```

---

## Finding 5 (LOW): `exec.ExitError` in Test Is Not Importable as a Literal

**Severity:** Low. Compile error in the test as written.

**Location:** Plan Task 2, `TestGetAgentPanes_EmptyOnNoServer`:
```go
runner := &mockRunner{
    stderr: "no server running on /tmp/tmux-1000/default",
    err:    &exec.ExitError{},   // this line
}
```

`exec.ExitError` has an unexported field `ProcessState *os.ProcessState`. You cannot construct `&exec.ExitError{}` directly — its zero value has `ProcessState = nil`. If any code in `GetAgentPanes` calls `.ExitCode()` on the error cast to `*exec.ExitError`, it will panic with a nil pointer dereference.

The proposed `GetAgentPanes` implementation only calls `strings.Contains(stderr, "no server running")` and never inspects the error type. So the zero-value `exec.ExitError` is never cast or inspected. The test compiles and the nil `ProcessState` is never accessed.

But this is poor test hygiene. The `err` field should be a simple sentinel error for clarity:

```go
err: fmt.Errorf("exit status 1"),
```

Or use `errors.New("exit status 1")`. This signals "non-nil error" without implying a specific type.

---

## Finding 6 (LOW): `GetAgentPanes` Pane Title Can Contain Colons — Parser Splits Incorrectly

**Severity:** Low. Parsing bug for pane titles that contain the `:` delimiter.

**Location:** Plan Task 2, `GetAgentPanes` implementation:
```go
format := "#{pane_id}:#{pane_title}:#{session_name}"
// ...
parts := strings.SplitN(line, ":", 3)
paneID := parts[0]
title := parts[1]
sessName := parts[2]
```

tmux `#{pane_title}` is a free-form string set by the process running in the pane. A pane running `claude --some-flag:value` or a pane titled `project: task 1` would produce a line like:

```
%0:project: task 1:dev
```

`strings.SplitN(line, ":", 3)` with `n=3` produces: `["%0", "project", " task 1:dev"]`. `parts[1]` is `"project"` (truncated title), `parts[2]` is `" task 1:dev"` (misidentified as session name).

**Consequence.** The pane is filtered out (session name `" task 1:dev"` does not equal `"dev"`), or classified incorrectly. Pane counts are silently wrong.

**Fix.** Use a tab delimiter instead of colon, since tmux session names cannot contain tabs:
```go
format := "#{pane_id}\t#{pane_title}\t#{session_name}"
// ...
parts := strings.SplitN(line, "\t", 3)
```

This matches the pattern used by `RefreshCache` in `client.go` (line 99), which already uses `\t` as the tmux format separator. Using a consistent delimiter also prevents this class of bug in future additions.

---

## Finding 7 (LOW): `Show()` Resets Phase But Not `target` or `paneCounts` — Stale Display on Re-Open

**Severity:** Low. Minor UX issue.

**Location:** Plan Task 3, `Show()`:
```go
func (p *Palette) Show() tea.Cmd {
    p.visible = true
    p.phase = PhaseCommand
    p.target = TargetAll      // reset to TargetAll — good
    p.pendingCmd = nil
    p.input.Reset()
    p.selected = 0
    p.updateMatches()
    return p.input.Focus()
}
```

The plan does reset `p.target = TargetAll`. However, `p.paneCounts` is not reset. If the user:
1. Opens palette, selects a broadcast command, sees pane counts (Claude: 3).
2. Closes palette (Esc from command phase).
3. One agent exits (now Claude: 2).
4. Re-opens palette.

The target phase view will still show `Claude (3)` until the new `FetchPaneCounts` tea.Cmd completes and `PaneCountMsg` is delivered. Since counts are fetched async when entering PhaseTarget (not when Show() is called), this is unavoidable and acceptable. But it means there is a brief moment where stale counts are displayed.

**This is not a bug, it is a design consequence of async fetching.** Document it explicitly. If the stale display is unacceptable, fetch counts proactively in `Show()` as well (returning the fetch cmd from `Show()`).

---

## Threading Model Analysis (Requested)

### Q1: `pendingCmd *Command` lifetime

**Confirmed concern** (see Finding 1). The pointer becomes invalid after `SetCommands`. Store a copy of the `Command` value, not a pointer to the slice element.

### Q2: `FetchPaneCounts` closure captures `a.tmuxClient` and `a.sessionName`

**Confirmed safe for the current usage**, with the caveat documented in Finding 3:
- `a.tmuxClient` is a `*tmux.Client` — the pointer is captured and read-only after setup
- `a.sessionName` is a `string` — captured at closure creation time. If `a.sessionName` is only set during init and never mutated, there is no race. Capture it explicitly to be safe.
- `tmux.Client.run()` uses `execRunner` which creates fresh `exec.Command` per call — concurrent calls are safe.
- `sessionCache` uses `sync.RWMutex` — cache reads from the goroutine are safe.

### Q3: `Command.Action func() tea.Cmd` called from a different phase

**Confirmed safe with the fix from Finding 2.** The `Action` function value is a first-class value captured by the `Command` struct. It can safely be stored and called later. The issue is not about calling it from a different phase, but about what the Action **closes over** when it executes on a goroutine.

If `Action` closes over palette fields (`p.target`, `p.paneCounts`), it races with `Update()` on the palette goroutine. The fix is to capture the resolved `BroadcastAction` context before calling `action()`, and pass it through a wrapper or by embedding it in the Command at dispatch time.

### Q4: Update() and View() on same goroutine

**Confirmed correct.** The project's MEMORY.md is accurate: Bubble Tea's runtime calls `Update()` and `View()` on the same goroutine. All palette struct fields (`phase`, `target`, `paneCounts`, `pendingCmd`) are only ever read and written from `Update()` and `View()`. No mutex is needed for these fields. The `-race` detector will confirm this.

The **only** fields that cross goroutine boundaries are those read by `tea.Cmd` closures. Those are exactly the fields that Finding 2 flags.

---

## Summary Table

| # | Severity | Location | Issue |
|---|----------|----------|-------|
| 1 | HIGH | Task 3 `updateCommandPhase` | `pendingCmd *Command` points into `p.commands` backing array. `SetCommands` invalidates the pointer. Store a `Command` value copy, not a pointer to a slice element. |
| 2 | HIGH | Task 7 integration test + future production Action | `Action` closure reads `p.target`/`p.paneCounts` after `Hide()` from a `tea.Cmd` goroutine — data race. Capture `BroadcastAction` context before `Hide()` and pass to Action, not read from palette. |
| 3 | MEDIUM | Task 5 `FetchPaneCounts` wiring | `a.sessionName` captured by reference in closure. Capture at setup time to prevent future race if session name becomes mutable. Add comment. |
| 4 | MEDIUM | Task 3 `updateTargetPhase` | Enter key is silently ignored in target phase. No test covers this. Add a test. |
| 5 | LOW | Task 2 tmux test | `&exec.ExitError{}` constructs a zero-value struct with nil `ProcessState`. Use `fmt.Errorf("exit status 1")` instead. |
| 6 | LOW | Task 2 `GetAgentPanes` | Colon delimiter in format string breaks on pane titles containing colons. Use tab (`\t`) to match `RefreshCache` pattern. |
| 7 | LOW | Task 3 `Show()` | `paneCounts` not reset on Show. Stale counts briefly visible when re-entering PhaseTarget. Document and optionally fetch in Show(). |

---

## Required Changes Before Implementation

### Fix 1 (HIGH — Finding 1, pointer lifetime):

Change `pendingCmd *Command` to `pendingCmd Command` + `hasPendingCmd bool` in the Palette struct:

```go
// In Palette struct:
pendingCmd    Command
hasPendingCmd bool

// In updateCommandPhase:
if cmd.Broadcast {
    p.pendingCmd = *cmd   // copy the Command value
    p.hasPendingCmd = true
    p.phase = PhaseTarget
    ...
}

// In Hide():
func (p *Palette) Hide() {
    p.visible = false
    p.phase = PhaseCommand
    p.hasPendingCmd = false
}

// In updateConfirmPhase:
case "enter":
    if p.hasPendingCmd {
        action := p.pendingCmd.Action
        p.Hide()
        return p, action()
    }
```

Also update all nil checks on `pendingCmd` to check `hasPendingCmd`:
```go
// In viewTargetPhase and viewConfirmPhase:
if p.hasPendingCmd {
    cmdName = p.pendingCmd.Name
}
```

### Fix 2 (HIGH — Finding 2, Action goroutine reads palette state):

Capture the broadcast context before `Hide()` in `updateConfirmPhase`:

```go
func (p *Palette) updateConfirmPhase(msg tea.KeyMsg) (*Palette, tea.Cmd) {
    switch msg.String() {
    case "esc":
        p.phase = PhaseTarget
        return p, nil
    case "enter":
        if p.hasPendingCmd {
            action := p.pendingCmd.Action
            // Capture context now, before Hide() may clear state
            broadcastCtx := BroadcastAction{
                Target:     p.target,
                PaneCounts: p.paneCounts,
            }
            p.Hide()
            // Wrap action to receive context
            return p, func() tea.Msg {
                cmd := action()
                if cmd == nil {
                    return nil
                }
                return cmd() // or handle BroadcastAction differently
            }
        }
        p.Hide()
        return p, nil
    }
    return p, nil
}
```

For Task 6's Action stubs, document that the Action must not close over `p.*` fields. Pass `broadcastCtx` via a message or channel if needed. At minimum, add this comment to `Command.Action`:

```go
// Action is the function to execute when the command is confirmed.
// For broadcast commands, it is called from a tea.Cmd goroutine.
// MUST NOT read palette or app fields — those are on a different goroutine.
// Use BroadcastAction context captured at confirm time instead.
Action func() tea.Cmd
```

### Fix 3 (MEDIUM — Finding 3, sessionName capture):

```go
sessionName := a.sessionName   // capture at palette setup time
a.palette.FetchPaneCounts = func() tea.Msg {
    if a.tmuxClient == nil {
        return PaneCountMsg{}
    }
    panes, err := a.tmuxClient.GetAgentPanes(sessionName)
    ...
}
```

### Fix 4 (LOW — Finding 6, tab delimiter):

In `GetAgentPanes`:
```go
format := "#{pane_id}\t#{pane_title}\t#{session_name}"
// ...
parts := strings.SplitN(line, "\t", 3)
```

---

## Non-Issues (Confirmed Correct)

**`tmux.Client.run()` concurrent access.** Each call to `run()` delegates to `execRunner.Run()` which creates a new `exec.Command`. There is no shared mutable state between concurrent calls. The `-race` detector will produce no findings here.

**`sessionCache` mutex correctness.** The plan's `GetAgentPanes` calls `c.run()` (no cache involved) and does not interact with `sessionCache`. Cache access in other methods uses `sync.RWMutex` correctly.

**`FetchPaneCounts` function field on `Palette`.** `FetchPaneCounts` is set once during app initialization and never mutated. Reading it from `Update()` is safe — it is read-only after assignment. Calling it returns a `tea.Cmd`, which Bubble Tea executes on a goroutine. The function itself (`GetAgentPanes`) is safe for concurrent execution (new `exec.Command` per call, no shared mutable state).

**Phase state machine transitions.** The state machine is linear and deterministic: `PhaseCommand` -> `PhaseTarget` -> `PhaseConfirm` -> (execute and reset to `PhaseCommand`). Reverse transitions via Esc are also correct. `ctrl+c` closes from any phase. The tests cover all transitions.

**`Broadcast bool` zero-value.** Existing `Command` literals without `Broadcast` field default to `false`. The new field is backward-compatible with all existing command registrations in `initPaletteCommands` and `updateCommands`. No changes required to existing command registrations.

**Fuzzy search during PhaseTarget and PhaseConfirm.** The plan correctly stops forwarding key messages to `p.input` during non-command phases. The input is irrelevant to the user in target and confirm phases. Input state is reset by `Show()`. No input leak into phase decisions.

**`SetPaneCounts` / `PaneCountMsg` thread safety.** `PaneCountMsg` is delivered via the standard Bubble Tea message dispatch: the goroutine running `FetchPaneCounts` sends `PaneCountMsg` to the Bubble Tea runtime, which delivers it via `Update()` on the main goroutine. `Update()` then calls `p.paneCounts = msg.Counts`. This is safe — `paneCounts` is only written from `Update()`.
