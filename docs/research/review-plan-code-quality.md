# Code Quality Review: Broadcast Confirmation Flow Plan
**Plan file:** `apps/autarch/docs/plans/2026-02-23-broadcast-confirmation-flow.md`
**Reviewer:** Flux-drive Quality & Style
**Date:** 2026-02-23
**Language scope:** Go
**Sources read:** `internal/bigend/tmux/runner.go`, `client.go`, `detector.go`, `client_actions_test.go`, `internal/tui/palette.go`, `unified_app.go`, `pkg/tui/view.go`, `CLAUDE.md` (autarch), `AGENTS.md` (root), `MEMORY.md` (autarch)

---

## Summary

The plan is well-structured with correct TDD discipline, proper error-wrapping convention, and idiomatic iota enum design. Five issues warrant correction before implementation: two are compile-time failures, two are design concerns, and one is a test fragility risk. The overall architecture is sound.

Full review with code samples: `/home/mk/projects/Demarch/.claude/reviews/fd-quality-broadcast-plan.md`

---

## Finding 1 — NAMING: `mockRunner` Conflicts With Established `fakeRunner` Convention

The plan introduces `mockRunner` in `agent_panes_test.go` (package `tmux`). The existing `client_actions_test.go` in the same package already defines `fakeRunner`. Every other test file across the codebase (`internal/coldwine/git/`, `internal/coldwine/tmux/`) uses `fakeRunner` for this pattern.

Two differently-named test helpers for the same concept in adjacent files in the same package will cause confusion for implementers. The two variants (call-recorder vs output-configurer) can be consolidated into a single `fakeRunner` with both field sets in a `testhelpers_test.go` file.

**Fix:** Rename to `fakeRunner`. Consolidate into a shared test helper in the package.

---

## Finding 2 — COMPILE ERROR: `&exec.ExitError{}` Is Unusable in Tests

In `TestGetAgentPanes_EmptyOnNoServer`, the plan assigns `err: &exec.ExitError{}`. `exec.ExitError` embeds `*os.ProcessState` with unexported fields — the zero-value literal compiles but panics on any method call. The `GetAgentPanes` implementation only inspects `stderr` string content, not the error type, so no typed `ExitError` is needed at all.

**Fix:** Replace with `errors.New("exit status 1")`. Remove the `"os/exec"` test import.

---

## Finding 3 — TYPE SAFETY: `AgentPane.AgentType` Duplicates Existing `AgentType`

`detector.go` in the same `tmux` package already defines `type AgentType string` with constants `AgentClaude`, `AgentCodex`, `AgentAider`, `AgentCursor`. The plan declares `AgentPane.AgentType` as a bare `string` with inline literals `"claude"`, `"codex"`, `"gemini"`, etc. — creating two parallel classification systems. `AgentGemini` is missing from `detector.go` entirely.

**Fix:** Change `AgentPane.AgentType` field type to `AgentType`. Add `AgentGemini`, `AgentUser`, and `AgentUnknown` to the const block in `detector.go`. Change `detectAgentType` return type to `AgentType`.

---

## Finding 4 — ENCAPSULATION: `FetchPaneCounts` Should Be Unexported With a Setter

The plan exposes `FetchPaneCounts func() tea.Msg` as a public exported field on `Palette`. The rest of the `Palette` API is entirely method-based (`SetCommands`, `SetSize`, `Show`, `Hide`, `Visible`, `Update`, `View`). An exported mutable function field on a struct bypasses encapsulation and requires a nil-guard inside `updateCommandPhase` that silently no-ops if the caller forgets to wire it.

**Fix:** Make the field unexported (`fetchPaneCounts`). Add a `SetPaneCountFetcher(fn func() tea.Msg)` method. The plan mentions a setter in the Task 5 Step 3 header but uses direct field assignment in Step 4 — align them.

---

## Finding 5 — TEST FRAGILITY: Integration Test Action Reads Post-`Hide()` Palette State

In `TestPalette_FullBroadcastFlow`, the `Action` closure reads `p.target` and `p.paneCounts` from inside the action body. The execution order in `updateConfirmPhase` is: capture action pointer → call `Hide()` → call `action()`. `Hide()` currently does not clear `target` or `paneCounts`, so the test passes. But if `Hide()` is ever extended to reset those fields (a natural cleanup), the test silently captures wrong values.

**Fix:** Snapshot `target` and `paneCounts` into a `BroadcastAction` value before calling `Hide()`. Update the integration test to verify behavior through observable state rather than reading palette internals from inside the action closure.

---

## Positive: No Issues With

- Table-driven tests for all enum `String()`/`Label()` methods — correct idiom
- `Phase`/`Target` iota enums with asymmetric `String()`/`Label()` — intentional and correct
- `%w` error wrapping in `GetAgentPanes` — consistent with `client.go` convention
- `nil, nil` return for no-server graceful degradation — matches `RefreshCache()` pattern
- Phase decomposition into `updateCommandPhase` / `updateTargetPhase` / `updateConfirmPhase`
- `-race` flag on every test run command — required by project convention
- `Show()` resetting all phase state — correct for Bubble Tea value-copy model
- `BroadcastAction` struct as context carrier — right abstraction for future action parameterization
