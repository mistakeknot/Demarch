# Architecture Review: Broadcast Confirmation Flow Plan
**Plan:** `apps/autarch/docs/plans/2026-02-23-broadcast-confirmation-flow.md`
**Reviewed:** 2026-02-23
**Full review:** `.claude/reviews/fd-architecture-broadcast-plan.md`
**Scope:** Module boundaries, coupling, pattern correctness, simplicity, design gaps

---

## Summary

The plan's phase state machine (Command → Target → Confirm → Execute) is architecturally sound. TDD discipline is strong. Three structural problems require correction before Task 5 begins; one design gap must be resolved before Task 6 is non-stub.

---

## 1. Boundaries and Coupling

### 1.1 Critical: `UnifiedApp` Has No `tmuxClient` or `sessionName` Field

**Severity: Must Fix**

Task 5 Step 4 assumes `a.tmuxClient` and `a.sessionName` exist on `UnifiedApp`. They do not. The actual struct (lines 26–72 of `internal/tui/unified_app.go`) contains only `client *autarch.Client`, `palette *Palette`, and layout/view fields. No tmux client field and no session name field exist. Task 5 will not compile as written.

**Fix:** Add `tmuxClient *tmux.Client` and `sessionName string` (or equivalent source) to `UnifiedApp` before Task 5. Wire in `NewUnifiedApp`. Determine session name source (config, CLI flag, or auto-detection from attached session)—the plan does not specify.

### 1.2 Structural: `PaneCountMsg` Belongs in `messages.go`, Not `palette_types.go`

**Severity: Must Fix**

`internal/tui/messages.go` is the canonical home for all Bubble Tea message types in the `tui` package (`ProjectCreatedMsg`, `AgentRunStartedMsg`, `IntermuteStartedMsg`, etc.). Placing `PaneCountMsg` in `palette_types.go` splits the convention and makes the message non-discoverable for any future view routing.

**Fix:** Move `PaneCountMsg` to `messages.go`. Keep `PaneCounts` (the data struct) in `palette_types.go`.

### 1.3 Coupling Risk: `FetchPaneCounts` as a Public Exported Field

**Severity: Recommended Fix**

The plan adds `FetchPaneCounts func() tea.Msg` as an exported field on `Palette`. All existing `Palette` configuration uses methods (`SetCommands`, `SetSize`). A public function field is inconsistent with this API style, bypasses zero-value safety, and creates a fragile initialization-order dependency between Palette and UnifiedApp.

**Fix:** Replace with `func (p *Palette) SetPaneFetcher(f func() tea.Msg)` storing to an unexported field. This matches the established API style.

### 1.4 Dependency Direction: `internal/bigend/tmux` to `internal/tui`

**Observation (no change required)**

`GetAgentPanes` is added to `internal/bigend/tmux/client.go`. The wiring in `unified_app.go` (in `internal/tui`) importing `internal/bigend/tmux` is an existing pattern—no new boundary crossing is introduced.

---

## 2. Pattern Analysis

### 2.1 Phase State Machine: Correct

The Command/Target/Confirm state machine is correctly modeled with clear transitions. Keeping all phase logic in `palette.go` with shared types in `palette_types.go` is appropriate for the current size. Tests cover all transitions including Esc back-navigation and Ctrl+C global escape.

### 2.2 Anti-Pattern: Action Has No Structured Access to Resolved Target/Counts

**Severity: Must Fix (Design Gap)**

The `Command.Action func() tea.Cmd` signature gives broadcast actions no way to receive the selected `Target` or `PaneCounts` at execution time. The `BroadcastAction` struct defined in Task 1 is never wired to anything in the plan. Task 6 marks actions as stubs with `// TODO: implement actual send-to-panes via tmux SendKeys`—the TODO cannot be resolved without changing this signature.

The integration test in Task 7 works around this by having the closure close over `p` (the palette pointer) and read `p.target`/`p.paneCounts` after `Hide()`. This works by accident—those fields are not reset by `Hide()`—but it documents the gap rather than solving it.

**Fix (smallest change):** Add `BroadcastHandler func(BroadcastAction) tea.Cmd` to `Command`, used only when `Broadcast: true`. In `updateConfirmPhase`, call `pendingCmd.BroadcastHandler(BroadcastAction{Target: p.target, PaneCounts: p.paneCounts})` instead of `pendingCmd.Action()`. Remove the unused `BroadcastAction` from Task 1 scope and introduce it in the task where it gains a real caller.

### 2.3 Duplication: Two Agent-Type Detectors in the Same Package

**Severity: Recommended Fix**

The plan's `detectAgentType(title string)` in `client.go` duplicates logic from `Detector.detectByName` in `internal/bigend/tmux/detector.go`. The existing detector handles Claude, Codex, Aider, and Cursor—but not Gemini. The new function adds Gemini but drops Aider and Cursor. Two classifiers in the same package will diverge.

**Fix:** Add `AgentGemini AgentType = "gemini"` to `detector.go` constants. Extend `Detector.detectByName` to handle it. Have `GetAgentPanes` use the Detector rather than a new standalone function.

### 2.4 Minor: `exec.ExitError` Construction in Test

The test in Task 2 uses `&exec.ExitError{}` as the mock error value. `exec.ExitError` requires `ProcessState` to be useful; the no-server detection in `GetAgentPanes` inspects `stderr` content, not the error type. The test works, but using `errors.New("exit status 1")` would be clearer.

---

## 3. Simplicity and YAGNI

### 3.1 `BroadcastAction` Defined but Never Used

`palette_types.go` in Task 1 defines `BroadcastAction` with `Target` and `PaneCounts` fields. This type appears nowhere else in the 7-task plan—it is not passed to any Action callback nor returned from any method. This is premature.

**Recommendation:** Remove from Task 1. Introduce it in the task where it gets a real caller (the fix for §2.2 above).

### 3.2 `Phase.String()` Has No Production Consumer

`Phase.String()` is tested and implemented but not called in any view rendering. The test assertions use it for error messages only. This is harmless but worth noting: if it is intended for debug logging, add a comment; if for display, wire it.

### 3.3 `pendingCmd` Not Cleared on Esc Back to PhaseCommand

When Esc navigates from PhaseTarget back to PhaseCommand, `pendingCmd` is not cleared. This is safe because `pendingCmd` is only read in `updateConfirmPhase`, which requires active progression through phases. However, the invariant is non-obvious. A comment documenting that `Show()` resets `pendingCmd` (the only reset path) would prevent future regressions.

---

## 4. Integration Risk Summary

| Risk | Impact | Likelihood | Mitigation |
|------|--------|-----------|------------|
| `tmuxClient` missing from `UnifiedApp` | Build failure at Task 5 | Certain | Add field before Task 5 |
| `PaneCountMsg` in wrong file | Message routing confusion over time | High | Move to `messages.go` |
| Action has no access to target/counts | Feature non-functional beyond stub | Certain at Task 6+ | Fix action signature now |
| Duplicate agent-type detection diverges | Gemini in one path, not other | Medium | Consolidate in Detector |
| `FetchPaneCounts` public field | Fragile initialization order | Low short-term | Use method setter |

---

## 5. What Is Correct

- Phase state machine design and transitions are clean and correctly bounded to `palette.go`.
- Separating types into `palette_types.go` is the right call at this size.
- Async pane count fetch via Bubble Tea command (returning `PaneCountMsg`) correctly avoids blocking `Update`.
- `GetAgentPanes` returning empty list on no-server implements correct graceful degradation.
- `NewClientWithRunner` injection for test isolation follows existing `client.go` convention exactly.
- All Esc/Ctrl+C phase transitions are correctly specified and tested.
- `Show()` resetting phase state is correctly specified.
- Build verification step after each commit is correctly included.

---

## 6. Recommended Task Adjustments

**Before Task 1:** Verify no `BroadcastAction` is added—defer it to the task where it gains a caller.

**Task 1:** Add `BroadcastHandler func(BroadcastAction) tea.Cmd` to `Command` instead of relying on `Action` for broadcast execution. Document that `Action` remains for non-broadcast commands.

**Before Task 5:** Add `tmuxClient *tmux.Client` and session name source to `UnifiedApp`. Determine session name source.

**Task 5:** Move `PaneCountMsg` to `messages.go`. Replace `FetchPaneCounts` public field with `SetPaneFetcher` method. Use `Detector.detectByName` (extended with Gemini) instead of new `detectAgentType`.

**Task 6:** With the `BroadcastHandler` fix in place, Task 6 actions become non-stubs immediately rather than requiring a follow-up plan.
