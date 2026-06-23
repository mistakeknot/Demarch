---
date: 2026-06-22
bead: sylveste-5p7s
title: "[microrouter] F2: D2 heuristic-baseline measurement — sibling to .19.9, parallel-runnable"
type: scope-spike
status: scoping-only
recommendation: likely-moot
author: scoping subagent (backlog-run)
---

# Scoping — sylveste-5p7s (D2 heuristic-baseline measurement)

> **Do not run.** This is a scoping pass only. The conclusion below is that the bead's
> question has already been answered by the work that superseded it. No code was written,
> no beads were closed, nothing was pushed.

## TL;DR

**likely-moot.** sylveste-5p7s is a stale child of an epic that was killed five weeks before
this scoping. Its premise — a β-deferral with a 2026-06-30 review date and a `.19.9`
accumulation window to run parallel to — no longer exists. The D2 question it was created to
answer ("does the `agent-roles.yaml` heuristic leave enough headroom to justify a learned
router?") was already measured twice, against a pre-registered decision rule, and both times
returned "no — keep the epic killed." Running D2 to its original protocol now would re-derive
a conclusion that is already in the tree.

The honest action is to **close sylveste-5p7s MOOT** with a pointer to the existing
measurement artifacts. The bead body's own coordination clause ("if D2 says kill epic, re-open
.19.10") is unsatisfiable: `.19.10`, `.19.9`, and the entire `.19` epic are closed.

## What the bead asks for (verbatim premise)

From `followon.json .scope_spikes[3]` / bead body:

- File D2 as a **sibling under `.19`, runnable in parallel with `.19.9`**.
- Eval protocol: replay shadow over the `.beads/` **verdict corpus** (closed beads with
  `verdict_status`); per-verdict record `(heuristic_recommendation, what_was_used,
  judge_flag_outcome)`; heuristic hit-rate per `(agent, complexity_tier)` cell; oracle upper
  bound from `verdict_outcome` aggregation OR a 200-sample manual-relabel subset.
- Pre-registered decision rule: `<5%` headroom → close `.19`; `5–15%` → narrow `.19.1` to
  stable-7-only; `>15%` or long-tail → `.19.1` resumes as content-feature classifier.
- Coordination: D2 is a CHECKPOINT not a gate; if "kill" before 2026-06-30, immediately re-open
  `.19.10`. Result doc at `docs/research/2026-MM-DD-microrouter-heuristic-baseline-d2.md`.

Every load-bearing object in that premise (`.19`, `.19.9`, `.19.1`, `.19.10`, the 2026-06-30
review, the β-deferral) is gone.

## Evidence the premise collapsed (verified against files, not memory)

1. **The parent PRD is SUPERSEDED and names this bead as stale.**
   `docs/prds/2026-05-06-microrouter-architecture-deferral-prd.md:10–14`:
   > **⚠️ SUPERSEDED 2026-05-08** — This PRD operationalized a β-deferral decision that was
   > invalidated the next day by `.19.1` Phase 1 measurement (commit `7f224cca`). The `.19`
   > microrouter epic was closed because `agent-roles.yaml` covers only 6.2% of subagent
   > dispatches — adding a learned router on top can't help at that scope. … **What's stale**:
   > the `.19.10` bead, the F1–F4 child beads (`Sylveste-1mp6/5p7s/ngft/58tb`) … the deferral
   > deadline is moot because the architecture was killed not deferred.

   sylveste-5p7s is literally enumerated in the "what's stale" list.

2. **The routing cluster wound down with zero open beads.**
   `docs/handoffs/2026-05-17-routing-cluster-wound-down.md`:
   > Microrouter/SLM/routing cluster has zero open beads after this session. `.19` epic was
   > already closed 2026-05-09 … the conditional successor Sylveste-zge closed MOOT after
   > measurement (post-0zy agreement on `core-builtin-general` = 89.6%, above 85% trigger).
   > Whole arc — heuristic baseline → LoRA kill → declaration hygiene → CI gate → conditional
   > successor measurement — is a closed loop. Any future learned-routing question needs a
   > **fresh scoping bead written against then-current workload.**

   That last sentence is the project's own ruling: do not resurrect the old beads; if the
   question matters, write a new one. sylveste-5p7s is an old bead.

3. **D2's question has already been measured, against its own decision rule.**
   The heuristic-baseline measurement ran on 2026-05-06, was re-run after coverage extension on
   2026-05-11, and a conditional successor measurement ran 2026-05-17:

   | Artifact | Finding |
   |---|---|
   | `docs/brainstorms/2026-05-06-microrouter-heuristic-baseline.md` | 6.2% coverage → "kill the LoRA epic; the heuristic doesn't even apply to 94% of traffic." |
   | `docs/brainstorms/2026-05-11-microrouter-heuristic-rerun.md` | Corrected coverage 97.1% on the *identifiable* population; the sub-90%-agreement categories diagnosed as **YAML declaration bugs** (interflux-researcher `opus`→`haiku`, core-planner `opus`→`sonnet`), not learned-router opportunities. Explicit: "**Microrouter .19 stays killed.** Nothing in this measurement justifies reviving learned routing as a primary lever." |
   | `docs/research/microrouter-phase1/baseline-2026-05-17-zge-trigger-check.txt` | Post-declaration-fix agreement: `core-builtin-general` 89.6%, overall 91.5%. Above the 85% trigger → Sylveste-zge closed MOOT. |

   D2's decision-rule branches (`<5%` / `5–15%` / `>15%` headroom) were designed to choose
   between "close epic," "narrow router," and "full router." The actual measurements landed
   firmly in the "close epic / it's a declaration bug" region. The decision has been made.

4. **The original kill rationale predates and undercuts D2's own oracle protocol.**
   D2 proposed a `.beads/` verdict-corpus replay with a `verdict_outcome` oracle. The live work
   chose a cheaper, already-available path — interstat `agent_runs` dispatch replay
   (`docs/research/microrouter-phase1/baseline.py`) — because it directly answers the survival
   question without building a verdict-corpus harness. The D2 protocol as written was never the
   path taken, and the path that *was* taken already resolved the question.

## The testable hypothesis (if one insisted on running it)

> **H_D2:** Replaying the `agent-roles.yaml` heuristic over the dispatch corpus, the headroom
> (oracle_accuracy − heuristic_accuracy) on routing-eligible traffic is ≥5% and concentrated
> enough to justify building a learned router.

This is the testable claim. But note: the **null** (headroom <5% / it's a declaration bug) has
already been observed three times. The platform doctrine (test-null-hypothesis-first) was already
honored by the 2026-05-06/05-11/05-17 measurements — each carried a pre-registered kill rule and
each fired the kill. Re-running H_D2 is testing a null that has already failed to reject in the
direction that kills the project.

## Pre-registered KILL RULE

Because the substance is already measured, the kill rule here is a **moot-confirmation gate**, not
a fresh multi-week measurement:

> **Close sylveste-5p7s MOOT** if ALL of the following hold (each is already true as of
> 2026-06-22, verified above):
> 1. The `.19` epic and `.19.9`/`.19.10` are closed (no parallel-runnable sibling exists).
> 2. A heuristic-baseline measurement with a pre-registered decision rule exists in-tree and
>    landed in the "keep killed" region (it does: 91.5% overall, 89.6% on the largest category,
>    above the 85% trigger).
> 3. No new workload-level pain has appeared since 2026-05-17 that re-opens the learned-router
>    question (none surfaced in handoffs; see Sylveste-s10 below for the *correct* place any such
>    question would now be scoped).
>
> **Only reverse to "pursue"** if a fresh, then-current workload measurement shows a *single*
> routing-eligible category with sustained ≥15% headroom over ≥200 dispatches that is NOT
> explainable as a declaration bug. That is a new bead's job, not this one's.

## Method (brief) — for the MOOT close, not for running D2

1. Confirm bead status in canonical Dolt (read-only here): `sylveste-5p7s` is `open`, `P2`,
   `updated_at 2026-05-06` — never touched since creation. (Confirmed via `.beads/issues.jsonl`.)
2. Close MOOT with note pointing at the three measurement artifacts above + the SUPERSEDED PRD
   banner + the 2026-05-17 wind-down handoff.
3. Do NOT file followups (per the wind-down handoff's "fresh scoping bead" rule — that bead
   already exists: **Sylveste-s10**, the post-cluster small-local-model workload scoping, which is
   the sanctioned home for any revived routing-as-SLM question).

## Rough effort

- **As a MOOT close: ~15 minutes** (read three artifacts already cited, write the close note).
  The user/workstation does the actual `bd close` — this scoping does not touch beads.
- **If someone insisted on running D2 to its original protocol: days** (build the `.beads/`
  verdict-corpus replay harness + 200-sample manual relabel) — to re-derive an answer already in
  the tree. Not recommended.

## Honest recommendation: likely-moot

This is not a "park for later" — parking implies the question might mature. The question already
matured, got answered, and the cluster was deliberately wound down with an explicit "write a
fresh bead if you ever need this again" instruction. sylveste-5p7s is residue of a deferral that
was reversed within 48 hours. Closing it MOOT (with breadcrumbs) is the correct disposition; the
one legitimate forward path for any learned-routing question is **Sylveste-s10**, which is already
scoped against the *current* workload.

### One caveat worth recording

There is a small, real, *non-microrouter* finding buried in the same measurements: two
`agent-roles.yaml` declaration bugs (interflux-researcher, core-planner) were identified and a
fix bead (Sylveste-0zy) was filed for them. If anyone reaches sylveste-5p7s looking for "is the
routing heuristic healthy," the answer is "yes, after 0zy's declaration fixes — agreement is
~91%." That is the substance D2 would have produced, and it already exists.

## Refs (all verified to exist)

- Bead source: `~/.claude/jobs/a67c894c/tmp/backlog-run/followon.json` `.scope_spikes[3]`
- SUPERSEDED PRD naming this bead stale: `docs/prds/2026-05-06-microrouter-architecture-deferral-prd.md:10–14`
- Wind-down handoff: `docs/handoffs/2026-05-17-routing-cluster-wound-down.md`
- Kill-analysis brainstorm: `docs/brainstorms/2026-05-06-microrouter-heuristic-baseline.md`
- Coverage-rerun brainstorm: `docs/brainstorms/2026-05-11-microrouter-heuristic-rerun.md`
- Measurement outputs: `docs/research/microrouter-phase1/baseline-2026-05-06.txt`,
  `baseline-2026-05-11.txt`, `baseline-2026-05-17-zge-trigger-check.txt`, `baseline.py`
- Sanctioned successor scoping bead (current-workload home for any revived question): `Sylveste-s10`
- MEMORY: `project_microrouter_19_killed.md`
