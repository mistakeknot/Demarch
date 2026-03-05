# Pipeline Audit: Multi-Tool Composition Gaps

**Bead:** iv-zdrpo
**Date:** 2026-03-05
**Scope:** All 45 commands in `os/clavain/commands/` and 16 skills in `os/clavain/skills/`

## Method

Audited each command and skill file for multi-plugin pipelines where one plugin/tool MUST run before another. Cross-referenced against the 4 existing sequencing hints in `os/clavain/config/tool-composition.yaml`. Identified within-domain disambiguation gaps from prior benchmark evidence and command analysis.

---

## Covered Pipelines

These pipelines are already represented by existing sequencing hints:

| # | Hint | Evidence (Commands/Skills) |
|---|------|---------------------------|
| 1 | interpath -> interlock: resolve paths before reserving | `project-onboard` (interpath seeds content, interlock coordinates agents) |
| 2 | interflux -> clavain: flux-drive before sprint execution | `sprint` Step 4 -> Step 5, `strategy` Phase 4, `execute-plan` gate check, `work` Phase 1b |
| 3 | clavain -> clavain: enforce-gate before sprint-advance | `sprint` Steps 5/7, `work` Phase 1b, `execute-plan` gate, `quality-gates` Phase 5b |
| 4 | interstat -> clavain: set-bead-context before sprint work | `sprint` Bead Token Attribution, `route` Steps 1/3/4 (register bead for interstat) |

---

## Uncovered Pipelines

New sequencing relationships found in the audit. Ordered by frequency of encounter in sprint workflows.

| # | Pipeline | Type | Evidence | Recommended Hint |
|---|----------|------|----------|-----------------|
| 1 | clavain -> interflux | sequencing | `brainstorm` Phase 1.1 dispatches `interflux:research:repo-research-analyst` before design capture | "repo-research must complete before brainstorm design capture" |
| 2 | interflux -> interflux | sequencing | `quality-gates` Phase 4 dispatches fd-* review agents, then Phase 5 dispatches `intersynth:synthesize-review` | "review agents must complete before synthesis agent runs" |
| 3 | intersynth -> clavain | sequencing | `quality-gates` Phase 5b reads synthesis verdict before enforce-gate for shipping | "synthesis verdict required before shipping gate check" |
| 4 | clavain -> interspect | sequencing | `quality-gates` Phase 5a records verdict outcomes to interspect evidence after synthesis | "record verdict evidence to interspect after quality gate synthesis" |
| 5 | interspect -> clavain | sequencing | `reflect` Step 7 reads interspect evidence to calibrate agent routing for future sprints | "interspect evidence calibrates agent routing after sprint reflect" |
| 6 | interstat -> clavain | sequencing | `reflect` Step 6 calibrates phase cost estimates from interstat history | "interstat history feeds phase cost calibration after reflect" |
| 7 | clavain -> intertrust | sequencing | `resolve` Step 5 emits trust feedback to intertrust after resolving findings | "emit trust feedback to intertrust after resolving review findings" |
| 8 | clavain -> intercore | sequencing | `resolve` Step 5b emits disagreement events via `ic events emit` after trust feedback | "emit kernel disagreement events after trust recording" |
| 9 | interflux -> interpath | sequencing | `strategy` Phase 4 runs flux-drive on PRD; `project-onboard` Phase 5 runs interpath after brainstorm | "validate PRD with flux-drive before interpath content seeding" |
| 10 | clavain -> interserve | sequencing | `executing-plans` Step 2A dispatches to Codex via interserve after plan classification | "classify plan tasks before dispatching to Codex agents" |
| 11 | interphase -> clavain | sequencing | `sprint` uses `sprint-find-active` and `sprint-read-state` from interphase before routing | "read interphase sprint state before route dispatch decision" |
| 12 | interwatch -> clavain | sequencing | `sprint-status` Section 1 reads handoff files; `status --scope=interwatch` delegates to interwatch | "check interwatch drift status as input to sprint status scan" |
| 13 | clavain -> interkasten | sequencing | `project-onboard` Phase 4b registers project in intertree via interkasten | "scaffold project infrastructure before registering in Notion" |
| 14 | interflux -> clavain | sequencing | `work` Phase 1b dispatches `interflux:learnings-researcher` before execution starts | "search institutional learnings before plan execution" |

---

## Within-Domain Disambiguation Gaps

Plugin pairs in the same domain where agents could select the wrong tool due to overlapping descriptions or capabilities.

| # | Plugins | Domain | Confusion Evidence | Recommended Hint |
|---|---------|--------|-------------------|-----------------|
| 1 | interwatch vs intercheck | quality | Benchmark T2: both handle "drift" — interwatch detects doc drift, intercheck validates config | "interwatch=doc freshness drift, intercheck=config validation drift" |
| 2 | interpath vs interdoc | docs | Benchmark T10: both generate docs — interpath creates product artifacts, interdoc refreshes AGENTS.md | "interpath=product artifacts (vision/roadmap), interdoc=AGENTS.md refresh" |
| 3 | intersearch vs tldr-swinton | discovery | Both do code search — intersearch uses embeddings, tldr-swinton uses structural analysis | "intersearch=semantic embedding search, tldr-swinton=structural code analysis" |
| 4 | interlock vs intermux | coordination | Both handle agent coordination — interlock reserves files, intermux monitors agent activity | "interlock=file reservation+messaging, intermux=agent visibility+monitoring" |
| 5 | interflux vs interpeer | quality | Both review code — interflux uses fd-* agents (Claude), interpeer uses cross-AI (Oracle/Codex) | "interflux=Claude-native multi-agent review, interpeer=cross-AI second opinion" |
| 6 | interphase vs clavain | phase-control | Both manage sprint phases — interphase stores phase state, clavain orchestrates transitions | "interphase=phase state storage+gates, clavain=orchestration+dispatch" |
| 7 | interject vs intersearch | discovery | Both surface context — interject does ambient triage, intersearch does explicit queries | "interject=ambient inbox triage, intersearch=explicit code/embedding query" |
| 8 | interwatch vs interkasten | docs | Both track doc health — interwatch detects staleness, interkasten syncs with Notion | "interwatch=local doc freshness, interkasten=Notion bidirectional sync" |

---

## Impact Assessment

**Highest-impact uncovered pipelines** (encountered every sprint):

1. **interflux -> intersynth -> clavain** (rows 2-3): The quality-gates fan-out/fan-in pattern is the most complex multi-plugin pipeline in the system. Every sprint hits it. No sequencing hint exists for the synthesis step.

2. **clavain -> interspect/intertrust** (rows 4, 7): The closed-loop feedback pipelines (verdict evidence, trust recording) run silently after every quality gate and resolve cycle. Mis-ordering could corrupt calibration data.

3. **interphase -> clavain** (row 11): Route's sprint resume depends on interphase state. Without this hint, an agent might try to advance phases before reading current state.

**Highest-impact disambiguation gaps:**

1. **intersearch vs tldr-swinton** (row 3): Both appear in the discovery curation group. An agent asked to "search the codebase" has no signal for which to prefer.

2. **interlock vs intermux** (row 4): Both appear in the coordination-stack curation group. "Check what other agents are doing" could route to either.

## Recommendations

1. Add 5-6 highest-impact sequencing hints from the uncovered table (rows 1-5, 11)
2. Add disambiguation hints for all 8 within-domain pairs
3. Consider adding a `pipeline` concept to tool-composition.yaml for multi-step chains (e.g., the quality-gates fan-out/fan-in sequence)
