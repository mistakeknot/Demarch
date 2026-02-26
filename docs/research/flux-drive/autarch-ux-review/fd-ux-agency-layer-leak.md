# Architecture Review: Agency Layer Leaks in Autarch

**Reviewer:** fd-ux-agency-layer-leak
**Date:** 2026-02-25
**Scope:** /home/mk/projects/Demarch/apps/autarch/
**Lens:** Layered architecture separation of concerns -- every business rule, state machine, or policy decision found in the TUI layer is a defect against the "apps are pure renderers" contract.

---

## Executive Summary

Autarch's vision document explicitly states: "apps should be pure rendering surfaces that read kernel state and submit intents to the OS." The current codebase contains substantial agency logic embedded in the application layer that would need to be duplicated by any replacement UI client. The Gurgeh arbiter is the most severe case (acknowledged debt), but Coldwine's dispatch-to-task state machine and Pollard's hardcoded research policies are also significant.

Findings are prioritized by **blast radius** -- the amount of logic a second UI client would need to reimplement.

---

## Finding 1: Gurgeh Arbiter -- Full Sprint Orchestration Engine in App Layer

**Priority:** P0 (Critical)
**Blast Radius:** Complete reimplementation required by any replacement client
**Status:** Acknowledged debt (autarch-vision.md, lines 89-99)

### Evidence

The arbiter orchestrator at `/home/mk/projects/Demarch/apps/autarch/internal/gurgeh/arbiter/orchestrator.go` is a 1310-line agency engine containing:

1. **8-phase state machine** (types.go:16-42): `PhaseVision -> PhaseProblem -> PhaseUsers -> PhaseFeaturesGoals -> PhaseCUJs -> PhaseRequirements -> PhaseScopeAssumptions -> PhaseAcceptanceCriteria`. The phase chain definition, phase ordering, and valid transitions are all hardcoded in the app layer. A second client must know this exact chain.

2. **Advance/gate logic** (orchestrator.go:310-433): `advanceInternal()` runs consistency checks, blocks on blocker-severity conflicts, updates confidence scores, generates drafts for the next phase, and decides when to trigger research scans. This is pure policy -- "when can a phase advance?" is an OS-level decision.

3. **Confidence scoring model** (confidence/calculator.go:28-78): Five-axis scoring (Completeness, Consistency, Specificity, Research, Assumptions) with fixed weights and shape-aware modifiers. The `Total()` method on `ConfidenceScore` (types.go:126-132) defines fixed weights: `0.20 * Completeness + 0.25 * Consistency + 0.20 * Specificity + 0.20 * Research + 0.15 * Assumptions`. Any alternative client must replicate these exact weights.

4. **Consistency engine** (consistency/engine.go:48-66): Cross-section conflict detection with blocker/warning severity classification. The `checkUserFeatureAlignment()` function (engine.go:68-83) encodes domain rules (solo users vs enterprise features). Vision alignment checks (consistency/vision.go:20-54) encode what constitutes a vision contradiction.

5. **Phase-specific research policy** (research_phases.go:15-50): `DefaultResearchPlan()` hardcodes which hunters run at which phase: Vision gets github-scout + hackernews-trendwatcher; Problem gets arxiv-scout + openalex; FeaturesGoals gets competitor-tracker + github-scout; Requirements gets github-scout. This is a policy decision about what research is appropriate at each stage.

6. **Handoff threshold policy** (orchestrator.go:672-698): `GetHandoffOptions()` uses `state.Confidence.Research < 0.7` to recommend deep research and `state.Confidence.Total() >= 0.7` to recommend task generation. These thresholds are policy decisions embedded in the app.

7. **Model routing** (types.go:62-84): `DefaultModelTiers()` and `ModelForPhase()` decide which LLM model serves each phase. Per-phase model selection is an OS-layer routing decision.

8. **Draft generation with LLM calls** (generator.go:52-96, orchestrator.go:362-429): The orchestrator drives LLM conversations: it calls `exploration.GeneratePhase()`, `exploration.GeneratePhaseFromContext()`, `exploration.PropagateChanges()`, and `exploration.Revise()`. It decides the generation strategy (cached extraction vs context-aware generation vs full exploration). This is the most expensive agency logic to duplicate.

### Blast Radius Assessment

A web dashboard client for Gurgeh would need to reimplement: the phase chain, advance guards, consistency engine, confidence calculator, research policy, handoff thresholds, model routing, and LLM conversation orchestration. This is approximately 2500+ lines of agency logic.

---

## Finding 2: Coldwine Dispatch-to-Task State Machine

**Priority:** P1 (High)
**Blast Radius:** Task status transition logic must be duplicated

### Evidence

`/home/mk/projects/Demarch/apps/autarch/internal/tui/views/coldwine.go`, lines 359-399, contains a state machine that maps dispatch completion outcomes to task status transitions:

```go
// Lines 377-389: Dispatch outcome -> task status mapping
switch d.Status {
case "completed":
    if d.ExitCode != nil && *d.ExitCode == 0 {
        newStatus = autarch.TaskStatusDone
    } else {
        newStatus = autarch.TaskStatusPending // non-zero exit -> retry
    }
case "failed", "cancelled":
    newStatus = autarch.TaskStatusPending
default:
    return v, nil
}
```

This is a business rule: "a completed dispatch with exit code 0 means the task is done; a non-zero exit code means retry." A second client must know this rule to correctly update task status when observing dispatch completions.

Additionally, the `taskMatchesDispatch()` function (coldwine.go:639-655) implements a fallback matching strategy (primary: dispatch ID from Intercore state; secondary: name matching; tertiary: legacy agent field matching). This matching policy is needed by any client that observes dispatch completions and correlates them to tasks.

### Related: Task-to-Dispatch Mapping Persistence

Lines 424-447 of coldwine.go show the view directly writing to Intercore state (`ic.StateSet(ctx, "task.dispatch_id", ...)`) when a dispatch is created. The view is authoring system-of-record state, not submitting an intent. The OS layer should manage this mapping when it handles the dispatch request.

### Blast Radius Assessment

Any client monitoring dispatches and displaying task status must duplicate: the exit-code-to-status mapping, the task-dispatch matching fallback chain, and the state persistence calls. Approximately 100 lines of policy.

---

## Finding 3: Coldwine Sprint Creation with Direct Kernel Calls

**Priority:** P1 (High)
**Blast Radius:** Sprint lifecycle management bypasses OS layer

### Evidence

`/home/mk/projects/Demarch/apps/autarch/internal/tui/views/coldwine.go`, lines 876-897, shows the Coldwine view directly calling `ic.RunCreate()` to create sprints:

```go
return func() tea.Msg {
    ctx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
    defer cancel()
    runID, err := ic.RunCreate(ctx, ".", goal,
        intercore.WithScopeID(epicID),
    )
    return sprintCreatedMsg{runID: runID, epicID: epicID, goal: goal, err: err}
}
```

Per the vision document's write-path contract (autarch-vision.md, lines 74-87), "Only policy-governing mutations go through the OS." Sprint creation is a policy-governing mutation -- the OS should validate whether this user/project is allowed to create a sprint, apply routing policy, and return the run ID. The app calling `ic.RunCreate()` directly bypasses any OS-level sprint creation policy.

The same issue applies to `dispatchSelectedTask()` (coldwine.go:763-800) which calls `ic.DispatchSpawn()` directly.

### Blast Radius Assessment

Any client that creates sprints or dispatches tasks must duplicate: the timeout handling, the scope ID association, and the epic-to-run state mapping (`ic.StateSet("epic.run_id", ...)`). Approximately 60 lines of integration logic.

---

## Finding 4: Pollard Hardcoded Hunter Set and Research Policy

**Priority:** P2 (Medium)
**Blast Radius:** Research configuration is app-layer policy

### Evidence

`/home/mk/projects/Demarch/apps/autarch/internal/tui/views/pollard.go`, line 500:

```go
hunterNames := []string{"competitor-tracker", "hackernews-trendwatcher", "github-scout"}
```

The "Run Research" command palette action hardcodes which hunters to run. This is a policy decision: the choice of hunter set for a general research scan should be an OS-level configuration, not an app-layer constant. A second client would either duplicate this list (creating drift risk) or need to discover available/recommended hunters from the OS.

### Related: Insight Linking Policy

`/home/mk/projects/Demarch/apps/autarch/internal/tui/views/pollard.go`, lines 526-538, contains a spec selection policy for linking insights:

```go
// Link to the first validated spec; fall back to first spec
specID := specs[0].ID
for _, s := range specs {
    if s.Status == autarch.SpecStatusValidated || s.Status == autarch.SpecStatusResearch {
        specID = s.ID
        break
    }
}
```

The heuristic "prefer validated/research specs when linking insights" is a business rule embedded in the view.

### Blast Radius Assessment

A second client doing research must know: which hunters to run by default, and which spec to link insights to. Approximately 20 lines of policy.

---

## Finding 5: Gurgeh Review Package -- Parallel Quality Scoring in App Layer

**Priority:** P2 (Medium)
**Blast Radius:** Quality assessment logic exists in two places within the app, complicating extraction

### Evidence

Autarch contains two independent quality scoring systems:

1. **Arbiter confidence calculator** (`internal/gurgeh/arbiter/confidence/calculator.go`): Scores specs on 5 axes during the sprint flow.

2. **Review package** (`internal/gurgeh/review/`): Contains `CompletenessReviewer` (completeness.go), `AcceptanceCriteriaReviewer` (criteria.go), `CUJReviewer` (cuj.go), and `ScopeReviewer` (scope.go) -- each with their own scoring logic.

These are not exact duplicates but they assess overlapping concerns (completeness, acceptance criteria quality) with different scoring mechanisms. When extracting to the OS layer, both need to be reconciled into a single quality evaluation system. The review package uses a `ReviewResult.Score` float with penalty deductions (criteria.go:28, -0.15 for empty criterion, -0.1 for vague, -0.05 for unmeasurable). The arbiter uses a 5-axis weighted model.

The vision's Phase 1 extraction plan says "extract confidence scoring model into a reusable OS-level component" -- but the review package's quality scoring would also need extraction, and the two systems use incompatible scoring semantics.

### Blast Radius Assessment

A second client performing spec quality assessment must implement both scoring systems or choose which one to use. The inconsistency between the two makes extraction more complex than acknowledged in the vision document.

---

## Finding 6: Dispatch Watcher Polling Logic in App Layer

**Priority:** P2 (Medium)
**Blast Radius:** Polling protocol must be duplicated

### Evidence

`/home/mk/projects/Demarch/apps/autarch/internal/tui/dispatch_watcher.go` implements a full dispatch completion detection protocol:

- Polls `ic.DispatchList()` on a timer (lines 54-88)
- Maintains a `known` map tracking dispatch IDs to last-seen status (line 27)
- Detects terminal state transitions by comparing current vs previous status (lines 73-81)
- Emits `DispatchCompletedMsg` only on first observation of terminal state (dedup logic)
- Defines terminal states: "completed", "failed", "cancelled" (line 96)

This polling protocol, including the dedup logic and terminal state definitions, would need to be duplicated by any client that needs real-time dispatch status. The vision document mentions the signal broker as a rendering optimization (autarch-vision.md, lines 202-215), but the actual polling and state-tracking logic is agency logic that belongs at the OS level (or should be a kernel event subscription).

### Blast Radius Assessment

Any client monitoring dispatch progress must reimplement: the polling loop, known-state tracking, terminal state definitions, and completion dedup. Approximately 50 lines of protocol logic.

---

## Finding 7: Task Decomposition Rules in Coldwine

**Priority:** P2 (Medium)
**Blast Radius:** Epic-to-task generation policy embedded in app

### Evidence

`/home/mk/projects/Demarch/apps/autarch/internal/coldwine/tasks/generate.go`, lines 46-116, contains a `Generator` that implements task decomposition policy:

- Decides whether an epic is "foundational" and needs a setup task (line 66)
- Automatically generates a test task for every epic (lines 99-115)
- Creates task dependencies (test tasks depend on implementation tasks, line 109-113)
- Generates implementation tasks from stories or directly from the epic (lines 80-97)
- Task type classification (implementation, test, documentation, review, setup, research -- lines 28-35)

These decomposition rules are business logic about how work should be structured. Per the vision (Phase 3), "Extract Coldwine's task decomposition and agent coordination into Clavain skills that use kernel dispatch primitives." Until that extraction, any alternative task management interface must duplicate these generation rules.

### Blast Radius Assessment

A second client generating tasks from epics must reimplement the entire task generation strategy. Approximately 150 lines of policy.

---

## Finding 8: PRD-to-Epic Import Logic in Coldwine

**Priority:** P3 (Low)
**Blast Radius:** Spec-to-epic conversion policy embedded in app

### Evidence

`/home/mk/projects/Demarch/apps/autarch/internal/coldwine/prd/import.go` contains `ImportFromPRD()` which converts Gurgeh specs into Coldwine epics. The test (import_test.go:47-69) shows the conversion rules: a PRD becomes one epic; requirements become stories; complexity maps to estimate strings ("medium" -> "M"); priority integers map to priority labels (1 -> "p1").

This is a domain translation layer that embeds business rules about how specs should decompose into epics. It sits in the app layer but represents OS-level workflow policy ("when a spec is ready, create these epics with these properties").

### Blast Radius Assessment

A second client doing spec-to-epic conversion must replicate the mapping rules. Approximately 80 lines of policy.

---

## Finding 9: SprintCommandRouter Embeds CLI-Over-Chat Pattern

**Priority:** P3 (Low)
**Blast Radius:** Slash command parsing is app-specific (acceptable)

### Evidence

`/home/mk/projects/Demarch/apps/autarch/internal/tui/views/sprint_commands.go` implements `/sprint` and `/dispatch` slash commands that call Intercore directly. While the command parsing itself is inherently TUI-specific, certain decisions within it are policy:

- `/sprint advance` (line 78-91): Automatically selects the first active run (`runs[0]`) when advancing. This "advance the most recent run" heuristic is a policy decision.
- `/dispatch spawn` (line 166-188): Same pattern -- automatically targets the first active sprint's run.

These heuristics are mild -- the real concern is that they bypass the OS intent submission mechanism by calling `ic.RunAdvance()` and `ic.DispatchSpawn()` directly.

### Blast Radius Assessment

Low -- slash command UX is inherently TUI-specific. The direct `ic` calls duplicate the same issue identified in Finding 3.

---

## Summary Table

| # | Finding | Priority | Blast Radius (LOC) | Vision Extraction Phase |
|---|---------|----------|---------------------|------------------------|
| 1 | Gurgeh arbiter (full sprint engine) | P0 | ~2500 | Phase 1-2 (v1.5-v2) |
| 2 | Coldwine dispatch-to-task state machine | P1 | ~100 | Phase 3 (v2) |
| 3 | Coldwine direct kernel calls (sprint/dispatch) | P1 | ~60 | Phase 3 (v2) |
| 4 | Pollard hardcoded hunter set | P2 | ~20 | Phase 3+ (v3) |
| 5 | Dual quality scoring systems | P2 | ~400 (combined) | Phase 1 (v1.5) |
| 6 | Dispatch watcher polling protocol | P2 | ~50 | Phase 3 (v2) |
| 7 | Task decomposition rules | P2 | ~150 | Phase 3 (v2) |
| 8 | PRD-to-epic import logic | P3 | ~80 | Phase 3 (v2) |
| 9 | Sprint command router direct calls | P3 | ~20 | Phase 3 (v2) |

**Total agency logic in app layer:** Approximately 3,380 lines that a second UI client would need to reimplement.

---

## Relationship to Vision Document

The vision document (autarch-vision.md) explicitly acknowledges the Gurgeh arbiter and Coldwine orchestrator as extraction targets with a 3-phase plan. This review confirms the vision's assessment and adds specificity:

1. **Finding 5 (dual scoring) is not mentioned** in the extraction schedule. Phase 1 says "extract confidence scoring model" but does not address the review package's parallel scoring system. Both must be unified during extraction.

2. **Finding 4 (Pollard hunter policy) is not mentioned.** The vision says "Pollard operates independently of the kernel's discovery subsystem, which doesn't exist yet (v3)" but does not flag the hardcoded hunter set as an extraction target.

3. **Finding 6 (dispatch watcher)** is partially addressed by the signal architecture section (autarch-vision.md:202-215) but the current implementation is polling-based with app-level dedup logic, not event-driven.

4. **Findings 2-3 (Coldwine direct kernel calls)** violate the write-path contract documented at autarch-vision.md:74-87. The vision says apps should "submit intents to the OS" but these calls bypass the OS entirely.

---

## Recommendations

1. **Immediate (pre-v1.5):** Move the `ConfidenceScore.Total()` weights and `GetHandoffOptions()` thresholds to a configuration file loadable by both the arbiter and any future client. This is the lowest-cost change that reduces blast radius.

2. **Phase 1 (v1.5):** When extracting confidence scoring, also extract the review package's scoring system and unify them into a single OS-level quality evaluation API.

3. **Phase 2 (v2):** Extract the dispatch-to-task state machine (Finding 2) alongside the arbiter extraction. The exit-code-to-status mapping should become a kernel or OS concern.

4. **Phase 3 (v2):** Convert Coldwine's direct `ic.RunCreate()` and `ic.DispatchSpawn()` calls to OS intent submissions. The OS layer should own the epic-run association state (`epic.run_id`) rather than the view writing it directly.

5. **v3:** Move the hardcoded hunter set to OS configuration. The Pollard "Run Research" action should query the OS for the recommended hunter set rather than embedding it.
