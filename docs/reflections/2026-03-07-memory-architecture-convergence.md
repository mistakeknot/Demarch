---
artifact_type: reflection
bead: iv-nnxzo
stage: reflect
---

# Reflection: Memory Architecture Convergence

**Sprint:** iv-nnxzo (P1 research)
**Complexity:** 3/5 (moderate) — actual was ~2 (simpler than expected)
**Deliverables:** Brainstorm (system map) + PRD (taxonomy + recommendations)

## What was built

A comprehensive survey of Demarch's 10 memory-shaped systems, organized into a 5-category taxonomy (C1-C5), with 5 key decisions and 5 actionable recommendations (R3.1-R3.5).

## Patterns discovered

1. **The "unify retrieval, not storage" principle.** This came out clearly from the survey — the real pain is fragmented read paths, not fragmented storage. Migrating 10 systems into one DB would be high-risk, high-cost, and wouldn't solve the discoverability problem. A thin retrieval layer (R3.1 `/recall`) solves 80% of the pain at 10% of the cost.

2. **Intermem as the gold standard for decay.** Intermem's grace-period + linear-decay + hysteresis model is well-designed and battle-tested. Other systems either have no decay (interspect evidence grows unbounded) or crude decay (interknow's review-count archival misses time-based staleness). Standardizing on intermem's pattern (R3.3) avoids reinventing decay per-system.

3. **C3 (learned preferences) should stay plugin-local.** Initial instinct was to centralize everything, but interest profiles and voice profiles are ML model parameters specific to their plugins. No other system needs to read them. The kernel provides the evidence (C2) that feeds these models — that's the right boundary.

## Decisions validated

- **D1 (unify retrieval)** was validated by counting the separate read paths — 5 different query mechanisms for overlapping knowledge. A unified `/recall` is clearly needed.
- **D3 (converge interknow + compound docs)** was validated by the overlap analysis — both store engineering patterns with YAML frontmatter, differ only in location and tooling. `docs/solutions/` is the natural home (73 existing entries, human-readable).

## Complexity calibration

Estimated C3 (moderate), actual was closer to C2. The survey phase was fast because each system has good CLAUDE.md docs and clear storage boundaries. The taxonomy fell out naturally from the survey — the 5 categories were obvious once all 10 systems were laid out side by side. Future research beads that are "survey + categorize + recommend" should be estimated at C2.

## What's next

The PRD identifies 3 priority tiers:
- **P2:** Unified retrieval (R3.1), converge interknow + compound docs (R3.2), document taxonomy in PHILOSOPHY.md (R3.5)
- **P3:** Standardize decay across interspect, intercore, intercache (R3.3)
- **No action:** C3 preferences (R3.4), intermem (already good), session artifacts (already kernel-scoped)

R3.5 (document in PHILOSOPHY.md) is the lowest-effort highest-value next step — prevents future plugins from creating yet another knowledge store.
