# Architecture Review: Broadcast Confirmation Flow Plan
**Date:** 2026-02-23
**Plan:** `/home/mk/projects/Demarch/apps/autarch/docs/plans/2026-02-23-broadcast-confirmation-flow.md`
**Reviewer:** fd-architecture (Flux-drive Architecture & Design Reviewer)

---

## Executive Summary

The plan is sound in principle and correctly identifies the right files to change. The TDD discipline is strong and the phase state machine is clean. However, three structural problems need correction before implementation begins: a missing tmux client field in `UnifiedApp`, a misclassified message type that must live in `internal/tui/messages.go`, and a leaky abstraction where palette state is exposed directly to the integration test's action closure. One additional coupling risk—`FetchPaneCounts func() tea.Msg` as a public field on Palette—should be addressed before the design solidifies.

---

## 1. Boundaries and Coupling

### 1.1 Critical: `UnifiedApp` Has No `tmuxClient` or `sessionName` Field

**Severity: Must Fix**

Task 5, Step 4 instructs:

> "In `unified_app.go`, after creating the palette, set the fetch function. The `UnifiedApp` struct already has access to `tmuxClient`."

This assumption is wrong. The actual `UnifiedApp` struct (lines 26–72 of `unified_app.go`) contains:

```go
type UnifiedApp struct {
    client           *autarch.Client
    currentView      View
    codingAgent      *agent.Agent
    agentSelector    *pkgtui.AgentSelector
    selectedAgent    string
    tabs             *TabBar
    dashViews        []View
    palette          *Palette
    width            int
    height           int
    // ...log pane, resize coalescer, onboarding, intermute fields
}
```

There is no `tmuxClient` field and no `sessionName` field. If this step is implemented as written, it will not compile. The plan defers the wiring to "check the `UnifiedApp` struct for the `tmuxClient` field name and `sessionName` field" without verifying these exist.

**Required correction:** Before Task 5 Step 4, add a `tmuxClient *tmux.Client` field to `UnifiedApp` and wire it through `NewUnifiedApp`. The tmux client already exists as a standalone `internal/bigend/tmux.Client`—the link just needs to be made explicit. Also resolve whether session name is taken from a config, a CLI flag, or a discovery call; this is not specified anywhere in the plan.

### 1.2 Structural: `PaneCountMsg` Is a Message Type and Belongs in `messages.go`

**Severity: Must Fix**

The plan creates `PaneCountMsg` in `internal/tui/palette_types.go`. However, `internal/tui/messages.go` already exists as the canonical home for all Bubble Tea message types in the `tui` package (it defines `ProjectCreatedMsg`, `SpecCompletedMsg`, `AgentRunStartedMsg`, `IntermuteStartedMsg`, etc.). Adding a new message type to `palette_types.go` creates a split convention: some messages are in `messages.go`, others hidden in `palette_types.go`. The unified app or any future view that needs to handle `PaneCountMsg` in its own Update path would need to import from a non-obvious location.

**Required correction:** Move `PaneCountMsg` to `internal/tui/messages.go`. Keep `palette_types.go` for palette-only types: `Phase`, `Target`, `PaneCounts`, `BroadcastAction`. This follows the existing pattern and keeps message routing discoverable.

### 1.3 Coupling Risk: `FetchPaneCounts` as a Public Exported Field on `Palette`

**Severity: Recommended Fix**

The plan adds:

```go
// In Palette struct:
FetchPaneCounts func() tea.Msg
```

This is a public field (exported, directly assignable). The existing `Palette` API uses methods for all configuration (`SetCommands`, `SetSize`, `Show`, `Hide`). A public function field is inconsistent with this style and creates a hidden dependency between `Palette` and `UnifiedApp` that is not enforced by an interface—it's a raw function pointer set post-construction.

This is particularly fragile because:
- Nothing prevents callers from setting it to a function that blocks or panics.
- The zero value (`nil`) is a valid program state that silently degrades (the code guards with `if p.FetchPaneCounts != nil`), but this guard is easy to miss when testing or mocking.
- It exposes `palette.go` internals to the parent's initialization order.

**Recommended correction:** Replace with a constructor injection pattern or a `SetPaneFetcher(f func() tea.Msg)` method that matches the style of `SetCommands`. The integration test in Task 7 demonstrates the problem: it directly assigns `p.FetchPaneCounts = func() tea.Msg { ... }` at the test level, coupling test setup to struct layout.

### 1.4 Dependency Direction: `internal/bigend/tmux` vs. `internal/tui`

**Observation (no change required, monitor)**

`GetAgentPanes` is added to `internal/bigend/tmux/client.go`. The wiring in `unified_app.go` (which lives in `internal/tui`) imports `internal/bigend/tmux`. This import direction already exists in the codebase (Bigend's tmux client is the source of tmux integration). The plan does not introduce a new crossing here, so no boundary violation occurs.

However, `detectAgentType` in the plan uses a different classification set from the existing `detector.go` in the same package. `detector.go` defines `AgentType` constants (`AgentClaude`, `AgentCodex`, `AgentAider`, `AgentCursor`) and detects agents by session name. The plan's `detectAgentType` function uses a parallel string-matching approach on pane title. These two detection paths will diverge over time.

**Recommended action:** Have `GetAgentPanes` use `Detector.detectByName` (the existing session-name detection logic) rather than introducing a second title-based classifier. This avoids two agent-type classifiers in the same package that will drift.

---

## 2. Pattern Analysis

### 2.1 Phase State Machine: Clean

The Command/Target/Confirm state machine is correctly modeled as a value type with clear transitions. The decision to keep all phase logic in `palette.go` and share types via `palette_types.go` is correct for the current scale—the type file is small and cohesive.

The tests exercise all transitions including Esc back-navigation and Ctrl+C global escape. This is thorough.

### 2.2 Anti-Pattern: Action Closure Reads `p.target` and `p.paneCounts` After Hide

In Task 7's integration test and in Task 6's stub commands, the Action closure is defined as:

```go
Action: func() tea.Cmd {
    executedTarget = p.target      // reads palette state
    executedCounts = p.paneCounts  // reads palette state
    return nil
},
```

The Action closure closes over `p` (the Palette pointer). When `Action()` is called, `Hide()` has already been invoked, which resets `p.pendingCmd` to nil. However, `p.target` and `p.paneCounts` are not reset by `Hide()`—they persist until the next `Show()`. This means the test works, but by accident of timing.

The broader design problem: the selected `Target` and `PaneCounts` are not passed as arguments to the Action. The Action callback signature is `func() tea.Cmd`, which gives the action no structured access to what was chosen. In production use ("Send Prompt to Agents"), the action implementor must know *which* panes to send to. There is no mechanism for this—the `BroadcastAction` struct is defined in `palette_types.go` but never used in the plan.

**Required correction:** Change the Action signature for broadcast commands, or thread the resolved `BroadcastAction` through the execution path. The simplest fix that stays consistent with the existing `Command.Action func() tea.Cmd` signature: define a separate `BroadcastAction func(BroadcastAction) tea.Cmd` field on `Command`, used only when `Broadcast: true`. Alternatively, use a closure-capture approach but capture a copy of target/counts *before* calling Hide, not reading from palette state inside the action. This is a protocol gap—Task 6 explicitly marks the actions as stubs with `// TODO: implement actual send-to-panes via tmux SendKeys`, which means this gap will be hit immediately in the next task.

### 2.3 Duplication: Agent-Type String Detection

As noted in §1.4, `detectAgentType` in the plan duplicates the classification logic already in `internal/bigend/tmux/detector.go`. The existing `Detector.detectByName` works on session name strings. The plan's version works on pane title strings. Both use the same `strings.ToLower` + `strings.Contains` approach. This creates two sources of truth for which strings mean "claude" vs "codex" vs "gemini".

Note: The existing detector does not include "gemini" as a type—it handles Claude, Codex, Aider, and Cursor. Adding Gemini only in the new function means `AgentType` constants in `detector.go` are incomplete relative to the new code's expectations.

**Required correction:** Add `AgentGemini AgentType = "gemini"` to `detector.go` and extend `detectByName` to handle it. Then `GetAgentPanes` uses the Detector rather than a new function.

### 2.4 Test Infrastructure: `exec.ExitError` in Test Without Import

The test in Task 2 references `&exec.ExitError{}` but the plan notes in passing "Note: The `exec.ExitError` reference needs an import — add `"os/exec"` to test imports." `exec.ExitError` is not constructable as `&exec.ExitError{}` (it has an unexported `ProcessState *os.ProcessState` field that matters for behavior). This test will compile but the mock runner's `err` field won't correctly trigger `strings.Contains(stderr, "no server running")` logic—the error check in `GetAgentPanes` inspects `stderr` content, not the error type. The no-server case works via the stderr string check, not the error value. The test's use of `&exec.ExitError{}` as the error is misleading but functional.

**Minor fix:** Use `errors.New("exit status 1")` in the test for clarity, since the implementation does not type-assert the error.

---

## 3. Simplicity and YAGNI

### 3.1 `BroadcastAction` Struct Is Defined But Never Used

`palette_types.go` defines:

```go
type BroadcastAction struct {
    Target     Target
    PaneCounts PaneCounts
}
```

This type appears nowhere else in the plan's 7 tasks. It is neither passed to the Action callback nor returned from any method. It is pure speculative scaffolding.

**Recommendation:** Remove it from Task 1. If the action signature needs it (per §2.2 above), introduce it in the task where it gets a real consumer. Adding types without callers is premature.

### 3.2 `Phase.String()` Method Is Tested but Has No Production Consumer

`Phase.String()` is implemented and tested. Looking across the plan, it is never called in any View rendering—the `viewTargetPhase` and `viewConfirmPhase` methods do not use `p.phase.String()`. The test coverage is harmless, but the method itself serves only test assertions and debug logging. This is acceptable but worth noting: if the method is for debug visibility, mark it with a comment; if it is for display, wire it.

### 3.3 Esc Behavior Asymmetry at `PhaseCommand`

In `updateCommandPhase`, Esc hides the palette. In `updateTargetPhase`, Esc goes back to `PhaseCommand` but does not hide. The test `TestPalette_EscGoesBackOnePhase` exercises this, and it is correct per the PRD intent. However, after Esc from target back to command phase, the pending command (`pendingCmd`) is not cleared. If the user then presses Esc again to close the palette and then reopens it, the palette resets on `Show()`, so this is safe. But if the user navigates back to PhaseCommand and then presses Enter on a different (non-broadcast) command, `pendingCmd` still points to the previous broadcast command. This is benign because `pendingCmd` is only read in `updateConfirmPhase`, which is not reachable from a non-broadcast Enter in `updateCommandPhase`. Document this invariant in a comment to prevent future regressions.

---

## 4. Smallest Viable Corrections

Listed in priority order. Items 1 and 2 are blockers for compilation. Item 3 is a design gap that blocks the next feature iteration. Items 4–6 are quality improvements.

### Blocker 1: Add `tmuxClient` to `UnifiedApp` Before Task 5

Add to the `UnifiedApp` struct:

```go
tmuxClient   *tmux.Client
sessionName  string  // or read from config/flags
```

Wire in `NewUnifiedApp` or via a functional option. Determine session name source (flag, environment, or auto-detected from attached session). This is a prerequisite for Task 5 Step 4 to compile.

### Blocker 2: Move `PaneCountMsg` to `messages.go`

In `palette_types.go`, remove `PaneCountMsg`. Add to `internal/tui/messages.go`:

```go
// PaneCountMsg carries fetched pane counts back to the palette during broadcast target selection.
type PaneCountMsg struct {
    Counts PaneCounts
    Err    error
}
```

Note: `PaneCounts` itself stays in `palette_types.go`—it is a palette-specific data type. Only the message wrapper moves.

### Design Gap: Thread `BroadcastAction` Through Execution or Remove It

Either:
- Remove `BroadcastAction` from Task 1 and add a `BroadcastHandler func(BroadcastAction) tea.Cmd` field to `Command` used only when `Broadcast: true`, or
- Keep `Action func() tea.Cmd` but ensure a copy of target/counts is captured before `Hide()` in `updateConfirmPhase`

The second option is the smallest change:

```go
case "enter":
    if p.pendingCmd != nil {
        action := p.pendingCmd.Action
        captured := BroadcastAction{Target: p.target, PaneCounts: p.paneCounts}
        _ = captured // available for closure capture if action needs it
        p.Hide()
        return p, action()
    }
```

This is still incomplete without the action signature change. Recommend the first option (dedicated handler field) as a clean seam.

### Recommended: Replace Duplicate Detector with Existing `Detector`

In `GetAgentPanes`, instead of `detectAgentType(title)`, use the existing `Detector`:

```go
d := &Detector{}
info := d.detectByName(pane.Title) // or session name equivalent
```

Add `AgentGemini` to `detector.go` constants. This keeps one classification path.

### Recommended: Use `SetPaneFetcher` Method Instead of Public Field

Replace:
```go
p.FetchPaneCounts = func() tea.Msg { ... }
```

With:
```go
func (p *Palette) SetPaneFetcher(f func() tea.Msg) {
    p.fetchPaneCounts = f  // unexported
}
```

Call via `a.palette.SetPaneFetcher(...)` in `unified_app.go`.

### Minor: Remove `BroadcastAction` Struct from Task 1 Scope

Remove from `palette_types.go` in Task 1. Reintroduce in the task where it gains a real caller.

---

## 5. Integration Risk Summary

| Risk | Impact | Likelihood | Mitigation |
|------|--------|-----------|------------|
| `tmuxClient` field missing from `UnifiedApp` | Build failure in Task 5 | Certain | Add field before Task 5 |
| `PaneCountMsg` in wrong file | Discoverability, future routing confusion | High over time | Move to `messages.go` |
| Action has no access to resolved target/counts | Feature is non-functional beyond stub | Certain at Task 6+ | Fix action signature now |
| Duplicate agent-type detection diverges | Gemini added in one path, missed in other | Medium | Consolidate in Detector |
| `FetchPaneCounts` public field | Fragile initialization order | Low short-term | Use method setter |

---

## Verdict

Implement with corrections. The core state machine (Phase/Target/Confirm in palette.go), the type separation into palette_types.go, and the async fetch via Bubble Tea command are all architecturally correct. The TDD approach is well-executed. The three blockers above must be resolved before Task 5 begins; the design gap in action signature must be resolved before Task 6 is anything more than a stub.
