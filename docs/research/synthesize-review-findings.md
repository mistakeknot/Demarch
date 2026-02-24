# Synthesis: Broadcast Confirmation Flow Review (3 Agents)

**Date:** 2026-02-23
**Review Type:** Plan Review (Step 4 of sprint)
**Agents:** 3 flux-drive specialists (Architecture, Correctness, Quality)
**Plan:** `apps/autarch/docs/plans/2026-02-23-broadcast-confirmation-flow.md`
**Verdict:** **NEEDS_ATTENTION** (3 P0/P1 blockers, 7 total findings)

---

## Executive Summary

All three agents completed validation successfully. The plan demonstrates solid TDD discipline and correct state machine design, but has three **mandatory compilation/logic blockers** that must be fixed before Task 5 begins, plus four additional high-priority issues. The core architecture is sound; the corrections are localized to specific structs and type definitions.

---

## Agent Validation

| Agent | Status | Findings | Verdict |
|-------|--------|----------|---------|
| Architecture (fd-architecture) | ✓ Valid | 4 HIGH, 2 MEDIUM, 1 LOW | Implement with corrections |
| Correctness (fd-correctness) | ✓ Valid | 2 HIGH, 2 MEDIUM, 2 LOW | Required fixes before Task 5 |
| Quality (fd-quality) | ✓ Valid | 1 MUST-FIX, 4 MEDIUM/LOW | Consolidate test helpers, type safety |

**Validation:** 3/3 agents valid, 0 failed.

---

## Deduplicated Findings (Priority Order)

### P0: Compilation/Execution Blockers (Must Fix Before Task 5)

#### **BLOCKER 1: `UnifiedApp` Has No `tmuxClient` or `sessionName` Field**

**Agents:** Architecture (1.1), Correctness (Finding 1 reference)
**Severity:** P0 — Compilation failure in Task 5 Step 4
**Location:** `internal/tui/unified_app.go`, struct definition

**Issue:** The plan states "The `UnifiedApp` struct already has access to `tmuxClient`" but the actual struct (lines 26–72) does not contain this field. Task 5 Step 4 will not compile without it.

**Fix:**
```go
type UnifiedApp struct {
    // ... existing fields ...
    tmuxClient   *tmux.Client
    sessionName  string  // from config, CLI flag, or auto-detect
}
```

Wire through `NewUnifiedApp` and determine session name source (flag, environment, or auto-detected).

**Convergence:** 2/3 agents (Architecture 1.1, implicit in Correctness)

---

#### **BLOCKER 2: `PaneCountMsg` Belongs in `internal/tui/messages.go`, Not `palette_types.go`**

**Agents:** Architecture (1.2)
**Severity:** P0 — Structural violation, discoverability gap
**Location:** `internal/tui/palette_types.go` (Task 1)

**Issue:** `internal/tui/messages.go` is the canonical home for all Bubble Tea message types (`ProjectCreatedMsg`, `SpecCompletedMsg`, `AgentRunStartedMsg`, `IntermuteStartedMsg`). Adding `PaneCountMsg` to `palette_types.go` splits the convention and makes message routing non-obvious.

**Fix:**
- Move `PaneCountMsg` to `internal/tui/messages.go`
- Keep `PaneCounts` type itself in `palette_types.go` (palette-specific data)
- Existing pattern: keep message wrappers in `messages.go`, domain types in domain files

---

#### **BLOCKER 3: `pendingCmd *Command` Points Into Replaceable Slice (Use-After-Free)**

**Agents:** Correctness (Finding 1), Quality (implicit in test concerns)
**Severity:** P0 — Silent data corruption, "leaky" pattern
**Location:** `internal/tui/palette.go` Task 3, `updateCommandPhase`, `Selected()` method

**Issue:** `Selected()` returns `&p.commands[idx]` (pointer into backing array). `SetCommands` replaces `p.commands`. Any call to `SetCommands` while palette is in `PhaseTarget` or `PhaseConfirm` invalidates `pendingCmd`. If GC runs between `SetCommands` and final `Enter`, `pendingCmd.Action()` dereferences freed memory.

**Concrete scenario:** Task 6 adds new broadcast commands via `updateCommands()` → `SetCommands()` during normal flow. If this happens while palette is mid-flow, silent corruption.

**Fix:**
```go
// In Palette struct:
pendingCmd    Command  // store a COPY, not a pointer
hasPendingCmd bool

// In updateCommandPhase (Task 3):
if cmd.Broadcast {
    p.pendingCmd = *cmd   // copy the value (Action func is safe by value)
    p.hasPendingCmd = true
    p.phase = PhaseTarget
}

// In updateConfirmPhase (Task 3):
case "enter":
    if p.hasPendingCmd {
        action := p.pendingCmd.Action
        p.Hide()
        return p, action()
    }

// In Hide():
p.hasPendingCmd = false
```

**Convergence:** 2/3 agents (Correctness, Architecture notices the anti-pattern)

---

### P1: High-Priority Issues (Before Task 6 / Stubs)

#### **P1-1: `Action` Closure Reads Palette State From Separate Goroutine (Data Race)**

**Agents:** Correctness (Finding 2), Quality (Finding 5, integration test)
**Severity:** P1 — Silent data race, shows up only under `-race`
**Location:** Task 6 broadcast `Action` stubs, Task 7 integration test

**Issue:** The plan's integration test (Task 7) has:
```go
Action: func() tea.Cmd {
    executedTarget = p.target      // reads palette field
    executedCounts = p.paneCounts  // reads palette field
    return nil
}
```

When this closure is called as a `tea.Cmd`, Bubble Tea runs it on a **separate goroutine**. Meanwhile, `Update()` on the main goroutine may write to `p.target` and `p.paneCounts`. This is a data race detectable with `-race`.

**Production impact:** Task 6's `Action` stubs will be filled in with real tmux commands. Those stubs will naturally try to close over `p.target` and `p.paneCounts` to know which panes to send to — creating the same race.

**Fix:** Capture the resolved context **before** calling `Hide()`:
```go
func (p *Palette) updateConfirmPhase(msg tea.KeyMsg) (*Palette, tea.Cmd) {
    switch msg.String() {
    case "enter":
        if p.hasPendingCmd {
            action := p.pendingCmd.Action
            // CAPTURE NOW, before Hide() may clear state
            broadcastCtx := BroadcastAction{
                Target:     p.target,
                PaneCounts: p.paneCounts,
            }
            p.Hide()
            // Action must NOT close over palette fields
            // Pass broadcastCtx via wrapper or closure capture
            return p, func() tea.Msg {
                // Use broadcastCtx, not p.target/p.paneCounts
                return action()
            }
        }
        p.Hide()
        return p, nil
    }
    return p, nil
}
```

Add comment to `Command.Action`:
```go
// Action is called from a tea.Cmd goroutine (different from Update/View).
// MUST NOT read palette or app fields — those are on a different goroutine.
// Capture needed context (e.g., BroadcastAction) at confirm time, before Hide().
Action func() tea.Cmd
```

**Convergence:** 2/3 agents (Correctness Finding 2, Quality Finding 5)

---

#### **P1-2: Duplicate Agent-Type Detection (Will Diverge)**

**Agents:** Architecture (1.4, 2.3), Quality (Finding 2)
**Severity:** P1 — Two classification systems in same package, Gemini incomplete
**Location:** `internal/bigend/tmux/detector.go` vs. plan's new `detectAgentType`

**Issue:** The existing `detector.go` defines `AgentType` consts (`AgentClaude`, `AgentCodex`, `AgentAider`, `AgentCursor`). The plan adds a parallel string-detection in `GetAgentPanes` that includes `"gemini"` but `detector.go` does not have `AgentGemini` constant. These two paths will diverge.

**Fix:** Add missing agent types to `detector.go`:
```go
const (
    AgentClaude  AgentType = "claude"
    AgentCodex   AgentType = "codex"
    AgentGemini  AgentType = "gemini"
    AgentAider   AgentType = "aider"
    AgentCursor  AgentType = "cursor"
    AgentUser    AgentType = "user"    // or AgentUnknown
)
```

Change `AgentPane.AgentType` from bare `string` to `AgentType`:
```go
type AgentPane struct {
    ID        string
    AgentType AgentType  // not string
    Title     string
}
```

Use the existing `Detector` or unify `detectAgentType` in `detector.go`.

**Convergence:** 2/3 agents (Architecture 2.3, Quality Finding 2)

---

#### **P1-3: `mockRunner` / `fakeRunner` Naming Inconsistency (Test Hygiene)**

**Agents:** Quality (Finding 1)
**Severity:** P1 — Inconsistent naming, test maintainability
**Location:** `internal/bigend/tmux/agent_panes_test.go` (Task 2)

**Issue:** The plan defines `mockRunner` but the codebase convention (seen in 5+ existing test files) is `fakeRunner`. Both test files in the same package will have test helpers with different names.

**Fix:** Rename to `fakeRunner` and consolidate:
- Create `internal/bigend/tmux/testhelpers_test.go`
- Move unified `fakeRunner` struct (with `stdout`, `stderr`, `err`, `calls` fields)
- Both `client_actions_test.go` and `agent_panes_test.go` import it

---

### P2: Important Issues (Before Shipping)

#### **P2-1: `exec.ExitError` Literal Is Non-Functional**

**Agents:** Correctness (Finding 5), Quality (Finding 3)
**Severity:** P2 — Poor test hygiene, misleading error mock
**Location:** Task 2 `TestGetAgentPanes_EmptyOnNoServer`

**Issue:** `&exec.ExitError{}` has an unexported `ProcessState` field that becomes nil. The implementation doesn't type-assert it, so the test works by accident. Using a generic `error` is clearer.

**Fix:**
```go
runner := &fakeRunner{
    stderr: "no server running on /tmp/tmux-1000/default",
    err:    errors.New("exit status 1"),
}
```

---

#### **P2-2: Colon Delimiter Breaks on Pane Titles With Colons**

**Agents:** Correctness (Finding 6)
**Severity:** P2 — Silent parsing bug, pane counts wrong for colons in titles
**Location:** Task 2 `GetAgentPanes` format string

**Issue:** Format string uses `"#{pane_id}:#{pane_title}:#{session_name}"` with colon delimiter. Pane title `"project: task 1"` produces `%0:project: task 1:dev` → `SplitN(line, ":", 3)` = `["%0", "project", " task 1:dev"]`. Session name is misidentified.

**Fix:** Use tab delimiter (existing pattern in `RefreshCache`):
```go
format := "#{pane_id}\t#{pane_title}\t#{session_name}"
parts := strings.SplitN(line, "\t", 3)
```

---

#### **P2-3: `sessionName` Captured by Reference in Closure**

**Agents:** Correctness (Finding 3)
**Severity:** P2 — Potential future race if sessionName becomes mutable
**Location:** Task 5 `unified_app.go`, `FetchPaneCounts` wiring

**Issue:** The closure captures `a.sessionName` by reference. If any code mutates `a.sessionName` after palette setup (future feature), the goroutine running `GetAgentPanes` would race.

**Fix:** Capture at setup time:
```go
sessionName := a.sessionName
a.palette.FetchPaneCounts = func() tea.Msg {
    if a.tmuxClient == nil {
        return PaneCountMsg{}
    }
    panes, err := a.tmuxClient.GetAgentPanes(sessionName)  // use local copy
    // ...
}
```

Add comment: "`sessionName` must not be mutated after palette setup."

---

### P3: Nice-to-Have / Recommendations

#### **P3-1: `FetchPaneCounts` As Public Field Bypasses Encapsulation**

**Agents:** Architecture (1.3), Quality (Finding 4)
**Severity:** P3 — Design pattern consistency
**Location:** Task 5 `palette.go`

**Issue:** Public exported function field breaks the existing pattern (all Palette config via methods like `SetCommands`, `SetSize`, `Show`). Zero value (`nil`) is silently ignored.

**Recommendation:** Make unexported and add setter:
```go
// In Palette:
fetchPaneCounts func() tea.Msg

// Setter:
func (p *Palette) SetPaneCountFetcher(fn func() tea.Msg) {
    p.fetchPaneCounts = fn
}
```

Call via `a.palette.SetPaneCountFetcher(...)` in `unified_app.go`.

---

#### **P3-2: `BroadcastAction` Struct Defined But Unused (Premature Scaffolding)**

**Agents:** Architecture (3.1)
**Severity:** P3 — Design clarity
**Location:** Task 1 `palette_types.go`

**Issue:** `BroadcastAction` is defined but never appears in any of the 7 tasks. It is speculative scaffolding.

**Recommendation:** Remove from Task 1. Reintroduce in Task 6 when it gains a real consumer (if the Action signature is changed to accept it). Alternatively, use it as shown in P1-1 fix above (capture and pass context).

---

#### **P3-3: `BroadcastAction` Struct Never Used to Pass Context to Action**

**Agents:** Correctness (Finding 2 implicit), Architecture (2.2)
**Severity:** P3 — Design gap, marked TODO in plan
**Location:** Task 6 `updateCommands` Action stubs

**Issue:** Task 6 has `// TODO: implement actual send-to-panes via tmux SendKeys`, but there is no mechanism to pass the resolved `Target` and `PaneCounts` to the action. The plan defines `BroadcastAction` for this but never threads it.

**Recommendation:** Either:
1. Change `Command.Action` signature for broadcast commands (add `BroadcastHandler func(BroadcastAction) tea.Cmd` field), or
2. Capture `BroadcastAction` at confirm time and make it available to Action via closure (see P1-1 fix)

---

#### **P3-4: Stale Pane Counts on Palette Re-Open**

**Agents:** Correctness (Finding 7)
**Severity:** P3 — Minor UX, acceptable design consequence
**Location:** Task 3 `Show()`, Task 5 async fetch

**Issue:** `Show()` resets `phase` and `target` but not `paneCounts`. If agents exit between close and re-open, user briefly sees stale counts until new `FetchPaneCounts` completes.

**Recommendation:** Document this as a design consequence of async fetching. Optionally fetch proactively in `Show()` if stale display is unacceptable.

---

#### **P3-5: Esc Behavior Asymmetry at `PhaseCommand`**

**Agents:** Architecture (3.3)
**Severity:** P3 — Invariant clarity
**Location:** Task 3 `updateCommandPhase`, `updateTargetPhase`

**Issue:** In `updateTargetPhase`, Esc goes back to `PhaseCommand` but does not hide the palette. If user then presses Esc again to close, re-opens, and picks a non-broadcast command, `pendingCmd` still holds the previous broadcast command (since it's only cleared on `Hide()` from confirm phase or direct Esc from command phase). The code is correct but the invariant is subtle.

**Recommendation:** Document in a comment: "If user Esc backs from target to command phase, `pendingCmd` is not cleared. Since `pendingCmd` is only read in confirm phase (reachable only via Enter on a broadcast command), the invariant is safe."

---

## Conflicts Between Agents

**None detected.** All three agents agree on the three P0 blockers and the data race in P1-1. Minor differences in recommendation framing (Architecture recommends method setter; Quality agrees; Correctness focuses on thread safety) are complementary, not contradictory.

---

## Summary of Changes Before Implementation

### MUST-FIX (Before Task 5):
1. Add `tmuxClient` and `sessionName` fields to `UnifiedApp` struct
2. Move `PaneCountMsg` to `internal/tui/messages.go`
3. Change `pendingCmd` from `*Command` to `Command` (value type) + `hasPendingCmd bool`
4. Capture broadcast context before `Hide()` in `updateConfirmPhase` to prevent goroutine data races

### SHOULD-FIX (Before Task 6):
5. Add `AgentGemini`, `AgentUser`, `AgentUnknown` to `detector.go`; change `AgentPane.AgentType` to typed `AgentType`
6. Rename `mockRunner` to `fakeRunner`; consolidate test helpers
7. Fix `exec.ExitError` mock to `errors.New("exit status 1")`
8. Use tab delimiter in `GetAgentPanes` format string (fix colon parsing bug)
9. Capture `sessionName` at palette setup time

### NICE-TO-HAVE (Design improvements):
10. Make `fetchPaneCounts` unexported with `SetPaneCountFetcher` setter method
11. Remove unused `BroadcastAction` struct from Task 1 (or use in Task 6)
12. Document `pendingCmd` lifetime invariant and stale count behavior

---

## Files to Update

| File | Tasks Affected | Changes |
|------|---|---|
| `internal/tui/palette_types.go` | Task 1 | Remove `PaneCountMsg`; keep/clarify `BroadcastAction` |
| `internal/tui/messages.go` | Task 1 | Add `PaneCountMsg` |
| `internal/tui/palette.go` | Tasks 3, 5, 7 | `pendingCmd Command + hasPendingCmd bool`; capture broadcast context; add setter method |
| `internal/tui/unified_app.go` | Task 5 | Add `tmuxClient`, `sessionName` fields; use setter; capture session name at setup time |
| `internal/bigend/tmux/client.go` | Task 2 | Fix pane format delimiter to tab; add `AgentGemini` etc. |
| `internal/bigend/tmux/detector.go` | Task 2 | Add `AgentGemini`, `AgentUser`, `AgentUnknown` consts |
| `internal/bigend/tmux/agent_panes_test.go` | Task 2 | Rename `mockRunner` to `fakeRunner`; fix `exec.ExitError` mock |
| `internal/bigend/tmux/testhelpers_test.go` | Task 2 | Create new file with unified `fakeRunner` |

---

## Verdict & Gate

**Overall Verdict:** **NEEDS_ATTENTION** (3 P0, 5 P1/P2)

**Gate Status:** **FAIL** — Plan requires corrections before execution

**Recommendation:**
1. Fix three P0 blockers immediately (tmuxClient/sessionName fields, PaneCountMsg location, pendingCmd pointer lifetime)
2. Fix P1-1 data race before Task 6 implementation
3. Address remaining P1/P2 items before final merge
4. Proceed with implementation; all corrections are localized and do not affect core design

---

## Conclusion

The plan demonstrates strong TDD discipline and correct state machine architecture. The phase machine (Command → Target → Confirm), async pane fetching via Bubble Tea commands, and type separation are all sound. The three critical blockers are structural/naming issues that must be resolved before Task 5 (missing fields, wrong file, wrong data type). The data race in P1-1 is real but fixable with a small context-capture refactor. All other findings are either minor hygiene improvements or design recommendations. The core feature is viable with these corrections.

**Time to fix:** ~2 hours for blockers + P1 items, ~1 hour for remaining quality items.
