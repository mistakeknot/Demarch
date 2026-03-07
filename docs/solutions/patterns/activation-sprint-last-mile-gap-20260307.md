---
module: System
date: 2026-03-07
problem_type: best_practice
component: development_workflow
symptoms:
  - "Feature described as multi-session build turns out to be a config flip"
  - "Infrastructure exists but returns stubs or unavailable status"
  - "Plugin hooks exist but are never installed/deployed"
root_cause: incomplete_setup
resolution_type: workflow_improvement
severity: medium
tags: [activation-sprint, last-mile, packaging, verification, deployment-gap]
---

# Activation Sprint Pattern: Built But Never Deployed

## Pattern

Design-first development cultures produce thorough brainstorms and implementations, but the "last mile" of testing and activation gets deferred. The result: complete infrastructure that's never been tested end-to-end, with estimated effort wildly exceeding actual effort.

## Instances

Three consecutive beads exhibited this pattern:

| Bead | Expected Effort | Actual Effort | Root Cause |
|------|----------------|---------------|------------|
| iv-zsio | Effort 4, Risk 3 | One-line manifest + reinstall | interphase plugin.json didn't reference hooks; cache was empty |
| iv-godia | Effort 3 | Already committed, just needed bead close | Work done in prior session, plan checkbox unchecked |
| iv-2s7k7 | Effort 3, "Build a 3-layer system" | Verification + config flip | All 4 layers already built, just never tested or activated (delegation.mode=shadow) |

## Detection Signals

- Bead description says "build X" but `infer-action` returns `execute` (plan exists)
- Investigation reveals the infrastructure exists in code but mode is `off`/`shadow`
- Plugin or hook exists in source but isn't in the installed cache
- Zero events in tracking tables despite the recording code existing

## Resolution Pattern

1. **Verify end-to-end** — Don't assume components work just because they exist. Test each integration point.
2. **Fix pipeline breaks** — Common: DB path resolution in subagent context, missing allowlist entries, empty plugin caches
3. **Flip the switch** — Change mode from `shadow`/`off` to `enforce`/`on`
4. **Smoke test** — Run one real transaction through the entire pipeline

## Prevention

- Add "activation verification" as a standard gate after implementation
- Discovery scanner should flag `shadow`/`off` modes as potential activation candidates
- First-run verification (like the one added in iv-t712t) catches setup gaps early
- When brainstorming a bead, check if the infrastructure already exists before estimating effort

## Key Insight

Fail-safe design (every dependency optional, never blocks) is correct for resilience but creates a blind spot: you can't tell the difference between "working correctly" and "not installed at all" because both produce the same observable behavior — silent degradation to stubs.
