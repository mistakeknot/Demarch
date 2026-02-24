# Quality & Style Review: Broadcast Confirmation Flow Plan
**Date:** 2026-02-23
**Plan:** `/home/mk/projects/Demarch/apps/autarch/docs/plans/2026-02-23-broadcast-confirmation-flow.md`
**Reviewer:** fd-quality (Flux-drive Quality & Style)
**Scope:** Go, Bubble Tea TUI, internal/tui, internal/bigend/tmux

---

## Executive Summary

The plan is well-structured and demonstrates good TDD discipline with red-green-commit cycles. The core design is sound. There are five issues worth addressing before implementation, ranging from a naming collision that will fail compilation to a behavioral gap in the integration test. None block the overall approach.

---

## Finding 1 — FAIL: `mockRunner` Conflicts With Established `fakeRunner` Convention

**Severity:** Must-fix (compilation failure in test binary)

**Location:** Task 2, `internal/bigend/tmux/agent_panes_test.go`

The plan defines a new `mockRunner` struct in `agent_panes_test.go`:

```go
type mockRunner struct {
    stdout string
    stderr string
    err    error
}
```

The existing test file in the same package is `/home/mk/projects/Demarch/apps/autarch/internal/bigend/tmux/client_actions_test.go`, which defines:

```go
type fakeRunner struct {
    calls [][]string
}
```

Both files are in `package tmux` (same test binary). Introducing a second test-helper type named `mockRunner` does not conflict with `fakeRunner` by name, but the plan's `mockRunner` has a different signature from `fakeRunner` — that is fine on its own. The real problem is conceptual: the codebase already has a settled convention of calling these `fakeRunner` (see also `internal/coldwine/git/diff_runner_test.go`, `internal/coldwine/tmux/session_test.go`, and three other files). Using `mockRunner` is an inconsistency that will confuse future contributors when they see two different names for the same concept in adjacent test files.

**Additionally:** The `fakeRunner` in `client_actions_test.go` only records calls; it returns empty strings and no error. The plan's `mockRunner` carries `stdout`, `stderr`, and `err` fields for configurable output. This richer variant is a useful addition, but it should be named `fakeRunner` and placed in a shared `_test.go` file (or the existing `client_actions_test.go` extended), since the two test files sharing a package can share test helpers.

**Fix:** Rename `mockRunner` to `fakeRunner` in the new test file. Because `client_actions_test.go` already declares a `fakeRunner` with a different field set, consolidate them into a single `fakeRunner` that satisfies both test needs — or split into a named variant like `fakeRunnerOutput` for the new test. The simplest resolution is to unify in a single `testhelpers_test.go` file in the package:

```go
// internal/bigend/tmux/testhelpers_test.go
package tmux

type fakeRunner struct {
    stdout string
    stderr string
    err    error
    calls  [][]string
}

func (f *fakeRunner) Run(name string, args ...string) (string, string, error) {
    f.calls = append(f.calls, append([]string{name}, args...))
    return f.stdout, f.stderr, f.err
}
```

Both `client_actions_test.go` and the new `agent_panes_test.go` then use this one type. This removes the type conflict entirely and aligns with the project-wide `fakeRunner` naming pattern.

---

## Finding 2 — RISK: `detectAgentType` Returns Bare String Constants — Should Reuse `AgentType`

**Severity:** Moderate — type safety and consistency

**Location:** Task 2, `internal/bigend/tmux/client.go` (proposed `detectAgentType`)

The existing `detector.go` in the same package already defines:

```go
type AgentType string

const (
    AgentClaude AgentType = "claude"
    AgentCodex  AgentType = "codex"
    AgentAider  AgentType = "aider"
    AgentCursor AgentType = "cursor"
)
```

The plan introduces a new parallel type `AgentPane.AgentType string` (bare `string`) with inline string literals `"claude"`, `"codex"`, `"gemini"`, `"user"`, `"unknown"`. This creates two competing classification systems in the same package: the existing typed `AgentType` constants and the new ad-hoc strings. In addition, `AgentClaude` is `"claude"` in both but `"gemini"` does not exist in `detector.go` — the Gemini agent type is not covered in the current detector at all.

**Consequences:**
- A caller comparing `pane.AgentType == "claude"` gets no compile-time safety; a typo is a silent mismatch.
- `AgentType` from `detector.go` is exported and can be referenced from outside the package; the bare `string` cannot be constrained.
- The two representations will diverge over time as agent types are added to one but not the other.

**Fix:** Change `AgentPane.AgentType` to `AgentType`, add `AgentGemini AgentType = "gemini"` and `AgentUser AgentType = "user"` (or `AgentUnknown`) to the existing const block in `detector.go`, and have `detectAgentType` return `AgentType`:

```go
// In detector.go — add missing types:
const (
    AgentClaude  AgentType = "claude"
    AgentCodex   AgentType = "codex"
    AgentGemini  AgentType = "gemini"
    AgentAider   AgentType = "aider"
    AgentCursor  AgentType = "cursor"
    AgentUser    AgentType = "user"
    AgentUnknown AgentType = "unknown"
)

// AgentPane:
type AgentPane struct {
    ID        string
    AgentType AgentType
    Title     string
}

// detectAgentType returns AgentType:
func detectAgentType(title string) AgentType {
    lower := strings.ToLower(title)
    switch {
    case strings.Contains(lower, "claude"):
        return AgentClaude
    case strings.Contains(lower, "codex"):
        return AgentCodex
    case strings.Contains(lower, "gemini"):
        return AgentGemini
    case strings.Contains(lower, "user"),
         strings.Contains(lower, "bash"),
         strings.Contains(lower, "zsh"):
        return AgentUser
    default:
        return AgentUnknown
    }
}
```

The `TestDetectAgentType` tests compare to `"claude"` etc., which still works because `AgentType` is a `string` underlying type.

---

## Finding 3 — SMELL: `exec.ExitError{}` Literal in Test Is Uninstantiable

**Severity:** Compile error in proposed test

**Location:** Task 2, `agent_panes_test.go`, `TestGetAgentPanes_EmptyOnNoServer`

```go
runner := &mockRunner{
    stderr: "no server running on /tmp/tmux-1000/default",
    err:    &exec.ExitError{},
}
```

`exec.ExitError` embeds `*os.ProcessState`, which has unexported fields. `&exec.ExitError{}` compiles but the resulting value has a nil `ProcessState`, and calling any method on it (e.g., `ExitCode()`) will panic. More importantly, the implementation in `GetAgentPanes` does not type-assert the error to `*exec.ExitError` — it only inspects `stderr` content. The test therefore does not need a real `ExitError` at all; any non-nil `error` will trigger the stderr-inspection branch.

**Fix:** Replace with `errors.New("exit status 1")` (no `os/exec` import needed in the test):

```go
runner := &fakeRunner{
    stderr: "no server running on /tmp/tmux-1000/default",
    err:    errors.New("exit status 1"),
}
```

This is also the pattern used by `execRunner` — the error returned by `cmd.Run()` for a non-zero exit is an `*exec.ExitError`, but from the caller's perspective it is just an opaque `error`. The test should treat it the same way.

---

## Finding 4 — SMELL: `FetchPaneCounts func() tea.Msg` on Palette Struct Is a Leaky Pattern

**Severity:** Design concern — addressable at implementation time but worth flagging now

**Location:** Task 5, `palette.go` Palette struct

```go
FetchPaneCounts func() tea.Msg
```

The plan places this as a public exported field directly on `Palette`. The concern is that an exported function field on a struct is effectively an ad-hoc interface with no contract enforcement — it is easy to forget to set, cannot be mocked through type assertions, and the zero value (nil) requires a nil-guard inside `updateCommandPhase`, which the implementation correctly adds but which is a silent no-op that can mask wiring failures in production.

This is fine for the current scope where there is exactly one caller (`unified_app.go`). The MEMORY.md for this project notes the Bubble Tea threading model: `Model.Update()` and `View()` are always on the same goroutine, so the func field is safe without synchronization.

**However**, the pattern diverges from the `accept interfaces` idiom used elsewhere in this codebase (e.g., `Runner` interface in `runner.go`, `CommandProvider` in `view.go`). An interface would be:

```go
type PaneCountFetcher interface {
    FetchPaneCounts(session string) (PaneCounts, error)
}
```

That said, the plan's approach is pragmatic given that:
1. `tea.Msg` is the Bubble Tea return convention for async command functions.
2. The `tmuxClient` in `unified_app.go` is not currently exposed through an interface.
3. Adding an interface solely for this one method adds indirection without proportional value at this stage.

**Recommendation:** Keep the func field for now, but make it unexported (`fetchPaneCounts`) to prevent accidental external mutation, and add a setter:

```go
// In Palette struct:
fetchPaneCounts func() tea.Msg

// Setter (replaces direct field assignment in unified_app.go):
func (p *Palette) SetPaneCountFetcher(fn func() tea.Msg) {
    p.fetchPaneCounts = fn
}
```

This matches how `unified_app.go` configures other behaviors (via methods, not direct field access). The plan already mentions `SetPaneCounts` in Task 5's Step 3 header but then uses direct field assignment in Step 4 — the setter approach is more consistent with the existing API surface.

---

## Finding 5 — GAP: Integration Test Reads State From Palette After Action Closes It

**Severity:** Low — test logic correctness concern

**Location:** Task 7, `TestPalette_FullBroadcastFlow`

```go
p.SetCommands([]Command{
    {Name: "Send Prompt", Broadcast: true, Action: func() tea.Cmd {
        executedTarget = p.target       // reads p.target here
        executedCounts = p.paneCounts   // reads p.paneCounts here
        return nil
    }},
})
```

The `Action` closure captures `p` by reference. When `Action()` is called inside `updateConfirmPhase`, the sequence is:

```go
action := p.pendingCmd.Action
p.Hide()         // resets p.phase = PhaseCommand, p.pendingCmd = nil
return p, action() // action() runs AFTER Hide() resets state
```

`Hide()` resets `phase` and `pendingCmd` but does NOT reset `target` or `paneCounts`. So the test currently happens to pass — `p.target` and `p.paneCounts` are still set when `action()` runs. But this is fragile: if `Hide()` is ever extended to clear `target` and `paneCounts` (which is a natural cleanup), the integration test silently captures wrong values.

More importantly, the integration test is inadvertently testing that `action()` can inspect palette-internal state at call time. The production pattern should be to pass `BroadcastAction` as a parameter to the action, not rely on closures reading Palette state. The `BroadcastAction` struct is already defined in the plan.

**Fix:** Change the `Command.Action` signature for broadcast commands to receive the resolved context:

```go
// Option A: Separate field for broadcast actions
type Command struct {
    Name            string
    Description     string
    Action          func() tea.Cmd
    BroadcastAction func(BroadcastAction) tea.Cmd
    Broadcast       bool
}
```

Or, simpler and requiring no signature change to `Command`:

**Fix (minimal):** When `updateConfirmPhase` executes, capture target and counts before calling `Hide()`, and pass them via closure:

```go
func (p *Palette) updateConfirmPhase(msg tea.KeyMsg) (*Palette, tea.Cmd) {
    switch msg.String() {
    case "esc":
        p.phase = PhaseTarget
        return p, nil
    case "enter":
        if p.pendingCmd != nil {
            action := p.pendingCmd.Action
            // Snapshot before Hide() modifies state
            ba := BroadcastAction{Target: p.target, PaneCounts: p.paneCounts}
            _ = ba // ba available for future use
            p.Hide()
            return p, action()
        }
        p.Hide()
        return p, nil
    }
    return p, nil
}
```

The integration test should be updated to not rely on reading `p.target` from inside the action:

```go
Action: func() tea.Cmd {
    executed = true  // just verify it was called
    return nil
},
```

And verify the target was set by checking `p.target` before the final Enter (already done via the phase assertions in the test).

---

## Positive Findings (No Action Required)

**Table-driven tests:** `TestPhaseString`, `TestTargetLabel`, `TestPaneCountsForTarget`, and `TestDetectAgentType` all use the idiomatic `[]struct{ ... }` table pattern correctly. No issues.

**iota enums with String()/Label():** Correct Go idiom. The asymmetry (`Phase` uses `String()`, `Target` uses `Label()`) is intentional — `String()` is the machine-readable identity used in logs and test assertions; `Label()` is the human-readable display string shown in the TUI. This is a good separation and matches how the codebase uses `pkgtui` display styles.

**Error wrapping:** `fmt.Errorf("failed to list panes: %w: %s", err, stderr)` follows the `%w` convention established throughout `client.go`. Correct.

**Graceful degradation for no-server:** Returning `nil, nil` for the "no server running" case is correct and consistent with how `RefreshCache()` handles the same condition in the existing client.

**Phase-aware Update decomposition:** Splitting `Update` into `updateCommandPhase`, `updateTargetPhase`, `updateConfirmPhase` is the right call — the existing single-method Update would become unreadable with three phases inlined. This follows the pattern established by `UnifiedApp`'s own Update decomposition.

**`Show()` resetting phase state:** Resetting `phase`, `target`, and `pendingCmd` in `Show()` ensures the palette is clean on every open. Correct and necessary given Bubble Tea's value-copy model.

**Test file placement:** All new tests are in the correct packages (`package tui` for internal/tui, `package tmux` for internal/bigend/tmux). No `_test` package suffix is used, which matches the existing test files in both packages.

**`-race` flag in all test run commands:** Every test step in the plan specifies `-race`. This is consistent with the project's CLAUDE.md requirement ("Always test with `-race` flag").

---

## Summary of Required Changes

| # | Finding | Action | Location |
|---|---------|--------|----------|
| 1 | `mockRunner` name conflicts with `fakeRunner` convention | Rename to `fakeRunner`; consolidate into shared test helper | `agent_panes_test.go` |
| 2 | `AgentPane.AgentType` as bare `string` duplicates `AgentType` type | Change field type to `AgentType`; add `AgentGemini`, `AgentUser`, `AgentUnknown` to `detector.go` | `client.go`, `detector.go` |
| 3 | `&exec.ExitError{}` is non-functional in test | Replace with `errors.New("exit status 1")` | `agent_panes_test.go` |
| 4 | `FetchPaneCounts` as exported field bypasses encapsulation | Make unexported; add `SetPaneCountFetcher` setter | `palette.go`, `unified_app.go` |
| 5 | Integration test action reads post-`Hide()` palette state | Capture target/counts before `Hide()`; don't read palette state from inside action closures | `palette_test.go`, `palette.go` |
