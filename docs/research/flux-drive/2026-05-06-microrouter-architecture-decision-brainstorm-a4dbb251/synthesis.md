---
target: docs/brainstorms/2026-05-06-microrouter-architecture-decision-brainstorm.md
bead: sylveste-s3z6.19.10
review_quality: balanced
review_date: 2026-05-06
agents: [fd-decisions, fd-systems, fd-perception]
---

# Synthesis — microrouter architecture decision brainstorm

## Verdict

**NEEDS_ATTENTION** — 1 P0 + 9 P1 findings across three agents. The deferral decision is strategically sound and the four bead acceptance criteria (table, deadline, authority, re-entry cost) are met. But one finding (fd-systems P0) materially weakens the central claim that "β breaks circularity by construction," and several P1s expose unoperationalized triggers and missing coordination points that the strategy phase MUST address before this is shippable.

## P0 findings (1)

### P0.1 — fd-systems: β's circularity is deferred, not broken

The brainstorm's load-bearing claim is that β anchors training on observed outcomes that are "independent of any judge." fd-systems demonstrates this is wrong. β's outcomes (bead-clean-close, CI pass, sprint reflection verdicts) accumulate *while the live `agent-roles.yaml` heuristic controls which model handles each task*. So pass@1 = "did the heuristic's choice succeed?" The router trained on this anchor learns to imitate the heuristic (which examples passed) plus a noise term, not to do strictly better than it. The circularity shifts from `judge → calibration → judge` to `heuristic → outcome → learned-router`. Label-noise detection only fires AFTER telemetry collection, not during accumulation — so a 4-sprint accumulation can finish before this defect surfaces.

**Implication:** β's strongest argument over α/γ is materially weaker than the brainstorm claims. β doesn't break the loop, it shifts the loop's anchor from a model judge to the existing heuristic. To recover the "breaks circularity" property, β needs to inject some non-heuristic-controlled traffic during accumulation (e.g., randomized off-policy decisions for some fraction of calls; or include outcomes from manual user overrides; or weight the training loss to penalize "agree-with-heuristic" predictions).

## P1 findings (9, deduped across agents)

1. **Operational definition of "4 sprints"** (fd-systems, fd-perception) — what counts as one sprint of pass@1 data? Volume per (agent, complexity_tier) cell? Quality threshold? Without a pre-registered definition, the deadline becomes pliable.
2. **Schelling trap / pressure to declare β ready** (fd-systems) — implicit pressure as 2026-06-30 approaches to declare 4 weak sprints "done" to unblock paused work. Pre-registered volume + quality thresholds break this.
3. **Label noise > 30% trigger is a placeholder** (fd-decisions, fd-perception) — no measurement protocol, no operational owner, unfalsifiable post-hoc.
4. **Bead-clean-close as a pass@1 proxy is biased** (fd-perception) — failure modes: deferred-as-closed beads, slow-burn regressions beyond 4-sprint window, ascertainment bias favoring monitored work over one-shot agents (which are the actual source of latency/privacy wins per 2026-05-05 D3).
5. **D2 (heuristic-baseline) coordination is missing** (fd-systems, fd-decisions) — D2 might conclude "kill the epic" mid-deferral. The brainstorm names D2 as parallel-runnable but doesn't define a coordination point (gate? checkpoint? abort signal?).
6. **`.19.8` α-as-shelved is opaque to future readers** (fd-decisions) — bead stays CLOSED but the v0 commit is now treated as not-implemented. Future readers will not understand the state without the brainstorm-as-context.
7. **Single decision authority + 2-month deferral** (fd-decisions) — no escalation path if arouth1 is unavailable when the deadline arrives. Especially fragile given the project's parallel-session activity.
8. **Cascade gap risk** (fd-systems) — 7 paused beads + dependent epics may lose coordination context. No keep-alive signal or check-in cadence specified.
9. **Calibration freeze cut date drift** (fd-perception) — the 2026-05-04 brainstorm proposed 2026-05-15 freeze. Under deferral, that freeze date is irrelevant for β (β doesn't read the calibration JSON), but the brainstorm doesn't explicitly retire it. Loose end for `.19.2`.

## P2 findings (4)

1. **γ contingency re-entry cost understated for mid-deferral trigger** (fd-systems) — "zero today" is correct only if triggered before any telemetry accumulation. Mid-deferral triggers add sunk-time + ensemble-orchestration + Qwen3.6-35B install/VRAM friction.
2. **Evidence base rests on single mental model** (fd-perception) — "independent signals > ensemble signals" framing not engaged with γ's diversity advantage or "D2 + γ in parallel" alternative.
3. **5% headroom threshold is a judgment call dressed as empirical** (fd-perception) — D2's kill criterion is acknowledged as judgment but used as if operational.
4. **Sprint reflection verdicts are soft/unvalidated** (fd-perception) — qualitative, endogenous, not consistency-checked.

## Bead acceptance criteria — verification

| Criterion | Status | Notes |
|---|---|---|
| Explicit α/β/γ evaluation table with cost/risk/coverage tradeoffs | ✅ | Present and structured |
| Decision deadline | ✅ | 2026-06-30 soft target, with three earlier triggers |
| Named decision authority | ✅ | arouth1, recorded in frontmatter |
| Re-entry cost estimate (if `.19.3` LoRA already ran) | ✅ | Zero today; quantified hypothetical (~half-day of compute) for if α had shipped |

All four met. The issues are with **what's downstream** of the decision (operationalization of triggers, coordination, cascade), not with the decision-record itself.

## Recommended next actions

The strategy phase (Step 2) should produce a PRD that pins:

1. **Address P0** — Either (a) revise β's framing to acknowledge heuristic-controlled circularity and add a mitigation (e.g., off-policy randomization, manual-override weighting, or a heuristic-stratified eval split), OR (b) re-open the architecture decision with this knowledge — γ's value proposition increases under this finding because γ's anchor is judges-across-families, not heuristic-controlled outcomes.
2. **Operational definitions for "4 sprints"** — concrete volume + quality + coverage thresholds, pre-registered before accumulation begins.
3. **D2 coordination** — explicit gate or checkpoint relative to deferral deadline.
4. **`.19.8` body update** — add a closing note that α-as-v0 commit is shelved per `.19.10`, with link to this brainstorm.
5. **Escalation path** — name a backup decision authority OR define an auto-revert (e.g., if no human decision by 2026-07-15, default to running D2 unconditionally).
6. **D1 timing decision** — ship dormant-five prune now or wait for `.19.1` resumption.

The brainstorm itself is publishable as-is with a "review caveats" section appended pointing at this synthesis. The strategy phase is where the operationalization happens.

## Per-agent reports

- `fd-decisions.md` — 5 P1 + 2 P2, focus on reversibility, sunk-cost, decision-record discipline, fourth-option framing
- `fd-systems.md` — 1 P0 + 3 P1 + 2 P2 + 2 P3, focus on feedback loops, cascade, pace layers, Schelling traps
- `fd-perception.md` — 4 P1 + 3 P2 + 1 P3, focus on sensemaking, label-noise operationalization, survivor bias, temporal drift
