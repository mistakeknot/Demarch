# Synthesis Verdict: Broadcast Confirmation Flow Plan

**Date:** 2026-02-23
**Review Type:** Plan Review (flux-drive, 3 agents)
**Plan:** `apps/autarch/docs/plans/2026-02-23-broadcast-confirmation-flow.md`

---

## Verdict

**Status:** NEEDS_ATTENTION

**Gate:** FAIL

**Summary:** 3 P0 blockers (compilation failures, use-after-free), 5 P1/P2 issues (data race, duplicate agent detection, test hygiene). Core design is sound; corrections are localized.

---

## Validation

- Architecture: VALID (4 HIGH, 2 MEDIUM, 1 LOW)
- Correctness: VALID (2 HIGH, 2 MEDIUM, 2 LOW)
- Quality: VALID (1 MUST-FIX, 4 MEDIUM/LOW)

All agents completed; no errors.

---

## P0 Blockers (MUST FIX BEFORE TASK 5)

### BLOCKER 1: Missing `tmuxClient` / `sessionName` Fields in `UnifiedApp`
- **Impact:** Compilation failure in Task 5 Step 4
- **Fix:** Add both fields to struct, wire through `NewUnifiedApp`
- **Files:** `internal/tui/unified_app.go`

### BLOCKER 2: `PaneCountMsg` in Wrong File
- **Impact:** Violates canonical message location convention, breaks discoverability
- **Fix:** Move to `internal/tui/messages.go` (keep `PaneCounts` in `palette_types.go`)
- **Files:** `internal/tui/palette_types.go` → `internal/tui/messages.go`

### BLOCKER 3: `pendingCmd *Command` Points Into Replaceable Slice (Use-After-Free)
- **Impact:** Silent data corruption; SetCommands invalidates pointer
- **Fix:** Store Command value copy + hasPendingCmd bool flag
- **Files:** `internal/tui/palette.go`

---

## P1/P2 High-Priority Issues

### P1-1: Data Race — Action Closure Reads Palette State From Goroutine
- **Impact:** Silent race on p.target / p.paneCounts when Action runs as tea.Cmd
- **Fix:** Capture BroadcastAction context before Hide(); add goroutine safety comment
- **Files:** `internal/tui/palette.go`

### P1-2: Duplicate Agent-Type Detection (Will Diverge)
- **Impact:** Two classification systems; Gemini type incomplete
- **Fix:** Add AgentGemini/AgentUser/AgentUnknown to detector.go; unify
- **Files:** `internal/bigend/tmux/detector.go`, `client.go`

### P1-3: Test Naming Inconsistency (mockRunner vs. fakeRunner)
- **Impact:** Violates codebase convention; maintainability
- **Fix:** Rename to fakeRunner; consolidate in testhelpers_test.go
- **Files:** `internal/bigend/tmux/agent_panes_test.go`

### P2-1: Colon Delimiter Parsing Bug (Pane Titles With Colons)
- **Impact:** Silent pane count corruption for titles like "project: task 1"
- **Fix:** Use tab delimiter (matches RefreshCache pattern)
- **Files:** `internal/bigend/tmux/client.go`

### P2-2: sessionName Captured by Reference (Goroutine Safety)
- **Impact:** Potential race if sessionName ever becomes mutable
- **Fix:** Capture at setup time; add comment
- **Files:** `internal/tui/unified_app.go`

---

## P3 Recommendations

- Replace public `FetchPaneCounts` field with `SetPaneCountFetcher()` method (consistency)
- Remove unused `BroadcastAction` struct from Task 1 (re-add in Task 6)
- Document stale pane count behavior and pendingCmd lifetime invariant

---

## Recommendation

**Fix all P0 and P1 issues before execution.** All corrections are localized and do not affect core design. Estimated fix time: 2–3 hours. Core state machine, async fetch pattern, and TDD approach are correct and should proceed.

---

## Key Files

Full analysis: `/home/mk/projects/Demarch/docs/research/synthesize-review-findings.md`
