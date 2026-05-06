---
artifact_type: brainstorm
bead: sylveste-s3z6.19.10
stage: discover
date: 2026-05-06
extends: docs/brainstorms/2026-05-05-microrouter-track-b6-design-revision.md
supersedes_in_part: docs/brainstorms/2026-05-04-microrouter-track-b6-design-revision.md (re: v0 architecture commit)
findings_absorbed: [Track C P0-D, Track C P0-F]
decision_authority: arouth1
decision_date: 2026-05-06
review_after: .19.9 ships + 4 sprints of pass@1 telemetry
---

# Microrouter Architecture α/β/γ — Decision Brainstorm

`.19.8` closed on 2026-05-04 with **α** as v0 (judge family ≠ baseline anchor). `.19.5` audit-trail unconformity then absorbed as `Sylveste-a5u`. After that, Track C of an extended flux-review surfaced **γ** (judge-ensemble across disjoint model families) as a third architecture that breaks circular calibration without requiring outcome data — relevant if `.19.9` (interspect outcome-column extension) doesn't ship in time to make β viable. This bead exists to evaluate γ against the already-chosen α and the already-deferred β before any of `.19.2`/`.19.3`/`.19.4` start work.

## Decision

**v0 architecture: defer to β after `.19.9` ships + 4 sprints of pass@1 telemetry accumulate.**

- α (the .19.8 commit) is **shelved** — no `.19.2` corpus build, no `.19.3` LoRA training, no `.19.4` eval until β telemetry is ready.
- γ is **documented and rejected** as v0; preserved as a contingency if β telemetry does not accumulate cleanly (see Open Questions).
- β becomes v0 in time-shifted form, no longer a "v1 future migration."

The decision was made via interview-driven AskUserQuestion on 2026-05-06 with α/β/γ + a "run D2 first" option presented; the user selected the deferral path explicitly over γ-now and α-now.

### Decision authority

**arouth1** (project owner). The interview format is the canonical authority surface for `.19` architecture forks per the 2026-05-04 handoff directive ("Resolve α vs β vs γ via AskUserQuestion (one fork at a time per global preference)"). This brainstorm doc is the named record.

### Decision deadline / review trigger

**~2026-06-30** (soft target). Revisit when `.19.9` (interspect outcome-column extension) is closed AND four full sprints of pass@1 data have been written to the new event family. Earlier revisit triggers:

1. `.19.9` ships and the first sprint of pass@1 data shows obviously-broken capture (label noise > 30%) — escalate immediately to γ-fallback.
2. A change of strategic priority makes microrouter latency/privacy wins urgent before telemetry matures (e.g., a privacy incident that the heuristic can't address) — re-open this decision.
3. Heuristic baseline measurement (D2 from the 2026-05-05 brainstorm) gets run as a side project and the headroom is < 5% — close the entire `.19` epic instead of waiting.

### Re-entry cost (if `.19.3` LoRA had already run)

**Zero today.** None of `.19.2` (corpus build), `.19.3` (LoRA training), or `.19.4` (eval harness) has started. The shelving of α is purely a doc-and-bead-state change.

For future reference, if α had run and we were switching to β:

- **Relabel cost**: 2K-5K examples × bead-clean-close lookup ~= O(minutes) of bd queries; ~free at the margin.
- **Retrain cost**: Qwen3.5-3B + rank-16 LoRA on M5 Max ≈ 2-6 hours per training run; trivial.
- **Eval re-run cost**: replay over the eval matrix ≈ 30-60 min.
- **Total** (if α had shipped): ~half-day of compute + the operator time to inspect new metrics. Not a barrier.

## α / β / γ evaluation table

| Axis | α (judge family ≠ anchor) | β (observed pass@1 anchor) | γ (judge-ensemble across disjoint families) |
|---|---|---|---|
| **Holdout graded against** | Single judge family (Gemini 2.5 OR local Qwen3.6-35B); baseline anchor = existing GPT-5.5/Opus `routing-calibration.json` | Real outcomes: bead clean-close (no defect/regression bead in N=4 sprints), CI pass, sprint reflection verdicts | Disjoint-family ensemble (GPT-5.5 + Claude Opus + Gemini 2.5 + local Qwen3.6-35B); high-confidence consensus IS the label |
| **Circularity risk** | Medium — anchor JSON was partly built by GPT-family judges; family separation reduces but doesn't eliminate | None by construction — outcomes are independent of any judge | Low — cross-family agreement cancels family-specific biases |
| **Data prereq** | `routing-calibration.json` populated from organic work + ≥2K judge labels | `.19.9` event family + 4 sprints of pass@1 accumulation (months) | Inference budget for 4-way ensemble across 2K-5K examples; no new event family |
| **Inference cost (one-time)** | ~$10-50 (Vertex AI Gemini) OR ~hours of local Qwen3.6-35B compute | ~zero for labels (outcomes are free) — but `.19.9` engineering is 3-5 days | ~$30-150 (Gemini × ensemble share) + Claude+OpenAI subscription leverage + Qwen local compute |
| **Time to first training run** | Days | Months (`.19.9` + 4 sprints) | Days-to-week |
| **Long-tail coverage (one-shot generated agents)** | Weak — name-keyed lookup memorizes seen agents | Strong if outcomes exist for the long tail | Strong-ish — ensemble disagreement is itself a signal for router abstention |
| **What if a judge is wrong?** | Single-judge SPOF | N/A (no judge) | Disagreement triggers human review or fallback to heuristic; consensus errors require systematic family-shared bias |
| **Compatibility with future β migration** | Yes — switch anchor when `.19.9` matures | Already β | Yes — γ ensemble can be downgraded to β-anchor when telemetry is ready |
| **Operational complexity** | Low — one judge call per example | Low for inference; high for telemetry pipeline | Medium — 4-way orchestration, family rotation, disagreement handling |
| **Re-entry cost from current state** | Zero (`.19.2`/`.19.3` not started) | Zero today, but β can never be v0 without months of telemetry | Zero (`.19.2`/`.19.3` not started); adds ensemble-orchestration to `.19.2` |
| **Risk of "ensemble agreeing on easy cases only"** | N/A | N/A | Real — must measure per-tier consensus; if consensus < 80% on hard tiers, fall back to heuristic for those tiers |

## Why defer to β instead of shipping γ-now or α-now

**Against γ-now:** γ's appeal is real (no circularity, no telemetry wait). But the underlying premise — that any learned router beats `agent-roles.yaml` by enough to justify the work — is unmeasured (D2 from 2026-05-05). Spending inference budget on a 4-way ensemble before knowing the heuristic's headroom is a category error: better data quality on a possibly-unnecessary model.

**Against α-now:** α has the same unmeasured-headroom problem as γ AND known circularity. Worse on both axes.

**For β-after-telemetry:** β is the only architecture where the ground-truth signal is independent of the judge population. Once telemetry exists, β makes the headroom question answerable directly (compare router vs heuristic on real pass@1 outcomes, not on judge agreement). Months of waiting for telemetry is a deliberate choice to avoid building on circular calibration.

**Against deferral as a "do nothing" trap:** the deferral has a concrete next action (`.19.9` becomes the critical-path P0, see "What this means for downstream beads" below). It's not a freeze; it's a re-prioritization to the prereq that all three architectures benefit from.

## Why γ is preserved (not deleted) as a contingency

If `.19.9` ships but pass@1 telemetry produces noisy labels (>30% label-noise rate), or if 4 sprints don't accumulate enough volume for stable training, γ is the cheapest re-entry to a learned router without circularity. Operating cost (~$30-150 + Qwen local compute) and engineering cost (ensemble orchestration in `.19.2`) are bounded.

The contingency trigger is one of:
1. After `.19.9` ships, the first sprint of pass@1 data shows label noise above some threshold (TBD; ~30% pre-registered as a placeholder).
2. After 4 sprints, pass@1 volume per (agent, complexity_tier) cell is below the minimum needed for stable training (TBD; tracked in `.19.2`).
3. Strategic priority flips and microrouter latency/privacy becomes urgent before telemetry matures.

## What this means for downstream beads

| Bead | Was | Becomes |
|---|---|---|
| `.19.9` | Hard prereq for β, scheduled flexibly | **Critical-path P0** — drives the deadline for the entire epic to resume |
| `.19.1` | Design doc + paper deep-read for LoRA distillation (already pre-revised in 2026-05-05 to "heuristic measurement first") | **Stays open, blocked on `.19.9`**. When β telemetry is ready, `.19.1` writes the β design doc — not α, not γ |
| `.19.2` | Build labeled corpus | **Blocked on `.19.9` + 4 sprints**. The corpus is built from pass@1 outcomes once available, not from judge labels |
| `.19.3` | LoRA training pipeline | Blocked on `.19.2` |
| `.19.4` | Eval harness | Blocked on `.19.2` |
| `.19.5` | Resolver integration in Clavain | Stays paused; non-architectural fixes from 2026-05-05 D5 still apply if heuristic-only routing is enriched |
| `.19.6` | Privacy-routing extension | Stays paused; depends on `.19.5` |
| `.19.7` | Confidence-cascade verifier (stretch) | Stays paused; re-evaluate post-`.19.1` |
| Track C γ-finding beads (none filed yet) | N/A | This brainstorm is the canonical record; no new bead needed for γ as a contingency |

## What this does NOT do

- **Does not run D2** (heuristic-baseline measurement). D2 is still a worthwhile sanity check — if the heuristic is within 5% of an oracle, the entire `.19` epic should close, β telemetry or not. D2 should be a separate bead under `.19` (file as a follow-up). The deferral decision is independent: even if D2 says "epic survives," β-after-telemetry remains the v0 architecture.
- **Does not change `.19.8` state.** `.19.8` (the design revision absorbing P0-B/C/D/E + α v0 commit) stays closed. Its α-as-v0 framing is now treated as "documented but not implemented" — the work it gated never started.
- **Does not file `.19.9` priority change as a separate bead.** `.19.9` is already P0-OPEN. The strategy/plan phase of this sprint will update its body to reflect critical-path framing.

## Done when

- This brainstorm doc is committed to `docs/brainstorms/`.
- `.19.10` body and notes are updated to point at this doc and record: (a) decision = β-deferred, (b) authority = arouth1, (c) deadline = `.19.9` + 4 sprints, (d) re-entry cost = zero today.
- `.19.1` body is updated to note that v0 design = β (not α from .19.8); design work resumes when telemetry is available.
- `.19.2` body is updated to note label source = pass@1 outcomes from `.19.9`, not judge labels.
- `.19.9` body is updated to call out its critical-path role for the entire `.19` epic.
- A new bead is filed for D2 (heuristic-baseline measurement) as an independent epic-survival check, runnable in parallel with `.19.9` work.
- `.beads/issues.jsonl` is regenerated.

## Open questions deferred to strategy/plan phase

1. **D2 follow-up bead title and scope.** The 2026-05-05 brainstorm's Approach E framing ("replay shadow over verdict corpus, compare heuristic vs oracle") is a starting point but needs a concrete eval protocol. Either as a child of `.19` or as a sibling under the broader routing epic.
2. **γ contingency trigger thresholds.** "Label noise > 30%" and "volume per cell < N" are placeholders. The strategy doc should pin the actual numbers based on what's defensible from training-data theory (LoRA stability literature: ~1K-2K per class).
3. **`.19.9` definition of "ships."** Does pass@1 require ALL of (CI pass, bead clean-close, reflection verdict)? Or is bead clean-close alone sufficient for v0? The 2026-05-05 brainstorm proposed N=4 sprints for clean-close; the other signals are stronger but rarer.
4. **What if `.19.9` itself is deferred or de-prioritized?** Then this whole decision becomes "epic indefinitely paused." The strategy phase should set a re-decision deadline if `.19.9` doesn't make progress in N weeks.
5. **Can D1 (dormant-five prune) ship independently?** The 2026-05-05 D1 (move fd-game-design / fd-people / fd-decisions / fd-resilience / fd-perception out of always-triaged) is orthogonal to architecture and ships value immediately. Strategy phase should confirm and either schedule it or punt to a separate lane.

## Review Caveats (added 2026-05-06 post-flux-drive)

A balanced flux-drive review (fd-decisions, fd-systems, fd-perception) returned 1 P0 + 9 P1 + 4 P2. Full synthesis at `docs/research/flux-drive/2026-05-06-microrouter-architecture-decision-brainstorm-a4dbb251/synthesis.md`. The decision (β-deferred) stays. The following caveats correct or qualify the doc above:

### Caveat 1 — β does NOT "break circularity by construction" (corrects body claim)

The doc's framing that β's anchor is "independent of any judge" is too strong. fd-systems showed the loop just relocates: pass@1 outcomes accumulate WHILE the live `agent-roles.yaml` heuristic decides which model handles each task. So pass@1 is "did the heuristic's choice succeed" — a router trained on this anchor learns to imitate the heuristic plus noise, not to do strictly better than it. The circularity shifts from `judge → calibration → judge` to `heuristic → outcome → router`. Label-noise detection cannot fire during the 4-sprint accumulation, only after.

This does not invalidate β as the right v0 architecture, but it changes the design constraint: β's anchor is "heuristic-imitator with outcome filter" not "ground truth." The strategy phase MUST address this with one or more of:

- **Off-policy randomized traffic during accumulation** — randomize the model choice for some fraction of calls (e.g., 5-10%) so pass@1 outcomes cover non-heuristic decisions.
- **Manual-override weighting** — up-weight outcomes from sessions where the user manually overrode the heuristic; these are the cleanest "would-the-router-have-known-better" examples.
- **Heuristic-stratified eval split** — measure per-strata recall (heuristic-easy / heuristic-hard) so we can detect "router only matches heuristic on easy cases."
- **Loss penalty for heuristic agreement** — train with a regularizer that discourages exact heuristic mimicry; encourage divergence on uncertain cases.

If none of these are acceptable, γ (judge-ensemble across disjoint families) becomes the only architecture that genuinely breaks the loop, and the deferral decision should be reconsidered.

### Caveat 2 — operational definitions are deferred, not done

"4 sprints of pass@1 telemetry" lacks an operational definition (volume per cell, quality threshold, sprint-counting rule). "Label noise > 30%" trigger is a placeholder with no measurement protocol. "5% headroom" for D2 is a judgment call. The strategy phase MUST pin these as pre-registered numbers before accumulation begins, or the deadline becomes pliable under deadline pressure (Schelling trap risk per fd-systems P1.2).

### Caveat 3 — coordination + cascade gaps

D2 (heuristic-baseline measurement) was named as parallel-runnable but has no coordination point with the deferral. If D2 says "kill the epic" at week 6, the deferral was wasted; if D2 says "epic survives" at week 2, that doesn't unblock anything. Strategy phase MUST define D2's relationship to the deferral as either a gate, a checkpoint, or an abort signal.

7 paused beads + a 2-month coordination gap also need: (a) a check-in cadence (every N sprints, re-confirm the deferral is still right), (b) an `.19.8` body note explaining α-as-shelved (so future readers don't conflate "closed" with "shipped"), and (c) an escalation path / backup decision authority for the case where the named authority is unavailable when the deadline arrives.

### What this section does NOT do

- Re-open the α/β/γ choice. The deferral stays.
- Block strategy-phase work. All caveats are addressable in the PRD.
- Document the full P1/P2 findings inline — see synthesis doc for those.
