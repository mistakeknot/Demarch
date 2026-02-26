# Architecture Review: Pollard Progressive Result Reveal Plan
**Source plan:** `docs/plans/2026-02-23-pollard-progressive-reveal.md`
**Full review:** `.claude/reviews/fd-architecture-progressive-reveal.md`
**Date:** 2026-02-23

## Summary

Three blockers and one high-severity coupling issue must be resolved before implementation begins. See the full review for fix paths.

### Blocker 1 — Coordinator.SetProgram Is Never Called

`Coordinator.sendMsg` delivers messages via `p.Send(msg)`. If `p` is nil, all sends are no-ops. The codebase has zero calls to `coordinator.SetProgram`. The plan does not add one. Every message case in Task 2 (`HunterStartedMsg`, `HunterCompletedMsg`, etc.) will compile and appear correct while silently doing nothing at runtime. The feature cannot function without wiring the coordinator to the tea.Program after `tea.NewProgram(...)` in `unified_app.go:Run`.

### Blocker 2 — Dual State Machines on the Same Event Stream

`ResearchOverlay` already owns `hunterStatuses map[string]research.HunterStatus` and `findings []research.Finding`. The plan creates identical fields in `PollardView` and allocates a `ResearchOverlay` inside it. Both accumulate state from the same events via different paths. The overlay's `Update` is never called (it only processes messages when `visible == true`; the plan never calls `v.researchOverlay.Update(msg)`), so the overlay's state will always be stale. The plan has two tracking authorities with no reconciliation.

### Blocker 3 — ResearchOverlay Allocated but Receives No Messages and Renders Nothing

`PollardView.researchOverlay` is set in Task 1 but never referenced in Tasks 2–5. Its `Update` is not called in the message loop. Its `View()` is not composited into `PollardView.View()`. It is dead allocation.

### High — Shared Coordinator Creates Cross-Tab Run Cancellation

`Coordinator.StartRun` cancels any existing active run before starting a new one. Sharing one coordinator between `GurgehConfig` and `PollardView` means a Pollard "Run Research" action silently kills any in-progress Gurgeh onboarding research, and vice versa. The coordinator is cheap to construct; each view should own its own instance.

## Recommended Fix Path (Before Implementing the Plan)

1. Give PollardView its own `research.NewCoordinator(nil)` in `main.go` — do not share with GurgehConfig.
2. Call `coordinator.SetProgram(p)` for each coordinator in `unified_app.go:Run` after `p := tea.NewProgram(...)`.
3. Remove `hunterStatuses` and `runActive` from `PollardView`. Forward all research messages to `v.researchOverlay.Update(msg)` and read state from it. ResearchOverlay is the single tracking authority.
4. Only after the above: implement Tasks 2–5 of the plan with the simplified surface.
