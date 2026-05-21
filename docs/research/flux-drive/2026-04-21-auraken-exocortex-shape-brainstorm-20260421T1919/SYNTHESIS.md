---
artifact_type: flux-drive-synthesis
brainstorm: docs/brainstorms/2026-04-21-auraken-exocortex-shape-brainstorm.md
agents: [fd-decisions, fd-user-product, fd-systems, fd-resilience, fd-perception]
stage_2_skipped: [fd-people, fd-safety]
date: 2026-04-21
---

# Flux-Drive Synthesis — Auraken Exocortex Shape Brainstorm

## Convergence (findings named by 3+ agents)

### C1. Shape A is the only shape ready for schema v1 — but schema-v1 ≠ shape-commitment

**Agents**: fd-decisions (P0), fd-systems (F8), fd-resilience (verdict), fd-user-product (verdict).

Schema v1 is structurally cheap to reverse. The *product commitment* Shape A implies (proprietary moat, Hermes-clean, curated-only focus) is **not** cheap to reverse once the Hermes overlay ships — Shape B's corpus-ingestion UX and Shape C's authoring UX become fork-or-build-inside-constraints decisions, both expensive. The brainstorm conflates the two reversibility costs.

**Disagreement within the convergence**: fd-decisions wants `profile_origin` as a schema hook now (cheap optionality). fd-systems F8 argues *against* unifying schema — says Shape-A-only schema is safer; unification after B/C constraints are known. fd-user-product adds a new schema field to the table (see C3).

### C2. Camera/engine tension with Shape B is a categorical boundary, not a trade-off

**Agents**: fd-decisions (P1), fd-perception (P1 — "most consequential finding"), fd-user-product (P0 UP-03).

Three agents independently escalated this. The brainstorm treats Principle 1 ("camera not engine") as negotiable tension. All three reviewers say it isn't. The specific failure mode: if Shape B ships as **retrieval** ("here's what you wrote in March about X"), it's functionally identical to Mem/Reflect/Notion AI — commoditized. The **camera** version delivers inconsistency-as-question, using the corpus to generate a provocation rather than return a result. The distinction is not cosmetic: it determines schema fields, interaction design, and whether Shape B honors Principles 1, 2, and 7 at all.

### C3. Meadows validation gate has a scope limitation the brainstorm didn't flag

**Agents**: fd-decisions (P1), fd-systems (F1), fd-resilience (R1).

Meadows 12-point rediscovery validates *expert extraction from curated corpus*. It doesn't transfer to Shape B (user's ground truth is unreliable — they may not be able to articulate what the pipeline should find) or Shape C (no external anchor at all). Two consequences: (1) each shape needs its own validation gate, designed before pipeline work on that shape starts; (2) the Meadows gate itself is a single-point-of-failure for Shape A credibility — no redundancy or confidence scoring.

### C4. "Alex is representative" is a population of one — insufficient for Shape B product commitment

**Agents**: fd-perception (P1), fd-user-product (P0 UP-01), fd-decisions (P2 — Alex-as-archetype conflates two segments).

Shape B is developed at equal depth to Shape A but rests on one user's anecdote. The PKM graveyard pattern (Evernote, Roam abandonment within 6–12 months) is strong prior evidence *against* user-maintained knowledge substrates. The brainstorm doesn't weigh it.

### C5. Competitive landscape is absent from the frame

**Agents**: fd-perception (P1), fd-user-product (UP-07 implicit).

The brainstorm frames shape selection as internal (A vs B vs C) without asking where Auraken's lens-selection advantage survives in the Mem / Reflect / Heptabase / Notion AI / Tana / Granola / Rewind space. Shape B enters a crowded category; the "exocortex" metaphor sets user expectations (Memex, Clark extended-cognition) that Shapes B/C don't actually deliver — they deliver retrieval + reflection, not load-bearing externalized working memory.

## Divergence / Novel Angles (named by 1–2 agents, worth weighing)

### D1. Shape C1 vs C2 split — emotionally-motivated corpus

**Agent**: fd-user-product (UP-04).

The Evernote-graveyard pattern applies to *intellectually-motivated* user-curated knowledge bases (C1: thinker-councils for productivity). But **emotionally-motivated** inputs — a deceased relative's letters, a fictional character, a mentor's archive — sustain maintenance cost where productivity motivation doesn't, and have **no competition** in the exocortex category. This is a genuinely new shape the brainstorm didn't name. If Shape C gets investment, start with C2.

### D2. Shapes as funnel, not alternatives

**Agent**: fd-perception (P2).

Users may naturally graduate A → B → C over time (curated roster onboards them, corpus accumulates from conversations, authoring emerges from specialization). If so, "which shape first?" is the wrong question — the right question is whether the product architecture supports a retention funnel. Changes the investment decision significantly.

### D3. PHILOSOPHY Principle 12 applies to Shape B and wasn't surfaced

**Agent**: fd-user-product (UP-11).

A user's self-corpus is a historical artifact. Stale frames are more dangerous than thin frames. Shape B without temporal confidence weighting treats two-year-old frames as equivalent to current ones, which will confuse "genuine unresolved contradiction" with "user changed their mind and the profile doesn't know." This is a schema-level decision, not an implementation detail.

### D4. Shape-B's four capabilities are not equal-value

**Agent**: fd-user-product (UP-07).

"Recall forgotten connections" = weak, already commoditized (PKM). "Surface inconsistency between past and present self" = strong, differentiating, Principle-1-honoring. The weakest capability is easiest to build first. If Shape B ships, the MVP should be inconsistency-detection only, not retrieval.

### D5. Profile-sharing economic thesis collapses without sharing

**Agent**: fd-user-product (UP-08), fd-systems (F3 Cobra Effect adjacent).

Shape C's moat story depends on profile-sharing network effects. Without sharing, Shape C is a premium add-on for lone-wolf researchers — small market, high support cost. Profile-sharing has unresolved consent chain (third-party corpus → extracted profile → downstream users invoke extracted frames). Near-term Shape C case should be restated *without* sharing; if that case isn't compelling, Shape C defers until the legal path is clear.

### D6. Shape C adversarial dynamics: jailbreak profiles, overfit profiles

**Agent**: fd-systems (F3), fd-resilience (R2).

Without a validation gate, Shape C's shared-profile marketplace has predictable failure modes: users craft "unconstrained advisor" profiles to bypass safety; authors optimize for personal fit → profiles don't transfer. Network effects fail because the shared unit is low-quality.

## What Changed About the Decision

**Before the review**: the brainstorm implicitly framed this as "pick a shape, or sequence them." Schema v1 seemed like a cheap commitment with `profile_origin` as hedge.

**After the review**:

1. **Schema v1 should ship Shape-A-only**, not multi-shape-accommodating. The `profile_origin` hook is cheap but `corpus_interaction_mode` + temporal-confidence-weighting would be non-trivial additions if Shape B is preserved as a real option. Keep Shape B/C as documented extension points, not active schema fields.

2. **Meadows validation gate is Shape-A-specific**. This should be named in the validation block of the schema as a scope limitation, so future Shape-B/C pipeline work doesn't inherit a gate it can't satisfy.

3. **Shape B's MVP (if pursued) is inconsistency-detection, not retrieval**. This is an interaction-design commitment upstream of any schema work — Principle 1 compliance gates Shape B's existence, not its details.

4. **Shape C should be decomposed into C1 (thinker-councils) and C2 (emotionally-motivated corpora)**. C2 is the better wedge if C is pursued; C1 has documented failure patterns.

5. **Competitive landscape analysis is a prerequisite** to committing depth to Shape B. Can be a separate beads artifact; not blocking schema v1.

6. **Shape-as-funnel reframing** deserves explicit consideration in the next brainstorm iteration — changes whether A/B/C are alternatives or lifecycle stages.

## Recommended Immediate Actions

**Before schema v1 merges (sylveste-2xzz)**:

- Ship schema for Shape A only. No `profile_origin` in active fields; include as documented extension point in a comment. This honors fd-systems F8 (avoid premature unification) while preserving fd-decisions' optionality concern.
- Add an explicit **scope** block to the schema for the validation section: "Meadows gate validates expert-extraction-from-curated-corpus. Shape B/C validation gates TBD — do not reuse."
- Add a `corpus_interaction_mode` field design note (not active, documented) with values `prompt | recall | both`. This forces the camera-vs-engine decision to be present at interface boundary when Shape B is revisited.

**After schema v1, before any Shape B pipeline investment**:

- Small Alex-archetype sanity test using the newly-consented Bits and Bobs corpus: run extraction, check whether **inconsistency-detection** (not retrieval) surfaces something Alex finds genuinely surprising about his own writing. One data point > zero data points.
- Competitive landscape analysis as a research artifact in `docs/research/`. Frame: where does lens-selection + thinker-profile overlay beat Mem/Reflect/Heptabase? If it doesn't, Shape B defers.
- File a new bead under sylveste-i0px for "Shape-as-funnel reframing analysis" — explicit cross-shape retention design question.

**After Meadows validation (sylveste-am7w)**:

- Revisit Shape C decomposition (C1 thinker-councils vs. C2 emotionally-motivated). File as separate beads if pursued.
- Decide Shape C governance (how to signal quality differences between curated and user-authored) before any profile-sharing UX.

## Stage 2 Agents Skipped

- **fd-people** (trust/authority dynamics for shared profiles): would add workflow-trust angle when profile-sharing ships. Not blocking schema v1; defer to pre-Shape-C work.
- **fd-safety** (third-party corpus consent, prompt-injection via upload): fd-resilience covered adversarial input surface. Not blocking schema v1; defer to pre-Shape-B deployment.

## Key Tensions the User Must Decide

1. **Schema hedging strategy**: ship bare Shape A (fd-systems F8 preferred) or preserve `profile_origin` hedge (fd-decisions preferred). Both are defensible.
2. **Shape B's existence as a product option**: keep Shape B on the roadmap *only if* it ships as inconsistency-detection-as-camera (honoring Principle 1), or cut Shape B from consideration to avoid PKM commoditization.
3. **Shape C decomposition**: accept C1/C2 split and pivot to C2-first framing, or defer Shape C entirely pending legal-path clarity on profile-sharing.
4. **Competitive landscape gate**: require competitive analysis before Shape B commitment (low-cost, high-clarity), or ship without it (faster, higher drift risk).
