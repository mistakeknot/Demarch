# PRD: Darwinian Evolver — Selective Adoption

**Bead:** iv-ymm3i
**Date:** 2026-02-28
**Status:** Draft
**Source:** Flux-drive review of Imbue's Darwinian Evolver (5 agents, synthesis complete)

## Problem Statement

Imbue's Darwinian Evolver demonstrates powerful evolutionary optimization patterns for LLM-driven code/prompt improvement. A 5-agent review assessed architectural fit, economic viability, knowledge system overlap, pre-filter applicability, and adoption classification. The verdict: **selective adoption** of 2 mechanisms, not wholesale import.

Two genuine gaps were identified in Demarch:
1. **Failure signal absence (P0):** Interknow only compounds successes — agents repeat failed approaches across sessions
2. **No post-fix verification (P1):** After resolving review findings, no cheap check confirms the fix actually addressed the flagged pattern before re-review

## Features

### F1: Failure Signal in Interknow (P0 — Adapt from Learning Log)

**What:** Extend interknow's knowledge entry format to capture failed approaches alongside successes.

**Schema additions** (YAML frontmatter):
- `outcome`: `success | failure | regression | inconclusive`
- `attempted_change`: What was tried (free text)
- `observed_outcome`: What happened (free text)
- `impact_score`: 1-5 effectiveness rating
- `bead_id`: Links entry to specific task lineage

**Skill changes:**
- `/interknow:compound` — add `--outcome=failure` path for recording failed approaches
- `/interknow:recall` — distinguish failure entries with "CAUTION:" prefix in output
- Shorter decay for failure entries (30 days vs 60 days for successes)

**Success metric:** Zero repeated failed approaches in sessions that recall relevant failure entries.

### F2: Post-Fix Verification Command (P1 — Adopt Verification Filter)

**What:** A `verify-fix` command that checks whether a flagged pattern still exists after a fix is applied.

**Behavior:**
1. Takes finding ID + current diff
2. Checks if the flagged code pattern/file still contains the issue
3. Returns pass/fail before triggering expensive full re-review

**Integration point:** Slots into flux-drive's resolve workflow — after `/clavain:resolve` applies fixes, `verify-fix` runs before re-dispatching quality gates.

**Success metric:** 10-20% reduction in review token spend for iterative fix cycles.

### F3: Findings-Identity Feedback Loop (P2 — Enhance Synthesis)

**What:** During intersynth synthesis, compute findings fingerprints per agent. Flag >80% overlap between agents and feed signal to interspect for routing override proposals.

**Integration point:** Extends intersynth synthesis agent's deduplication phase.

**Success metric:** Detects and flags redundant agent dispatch; reduces per-review cost.

### F4: Interspect Baseline Rescaling (P2 — Tune)

**What:** Apply Imbue's range-utilization technique to Interspect evidence scoring. If scores cluster in a narrow band, rescale to use full [0,1] range for better discrimination.

**Integration point:** ~10-line change to `ic interspect score` aggregation.

**Success metric:** Improved routing decision quality when evidence scores cluster.

## Out of Scope

- **Population-level evolutionary dynamics** — negative ROI ($480-1000/cycle vs $1.17/change baseline). A/B testing via shadow routing captures 80-90% of benefit at <5% cost.
- **Sigmoid-weighted selection** — conflicts with earned authority and transparent scoring principles.
- **Organism/Evaluator/Mutator abstraction** — Demarch already has equivalent separation across Intercore/Clavain/agents.
- **`interevolve` plugin** — deferred until Interspect reaches Level 3+ autonomy with positive metrics.

## Implementation Priority

| # | Feature | Classification | Effort | Impact | Reversibility |
|---|---------|---------------|--------|--------|---------------|
| 1 | F1: Failure signal in interknow | Adapt | ~3 hours | High (P0 gap) | Fully reversible |
| 2 | F2: Post-fix verification | Adopt | ~2 hours | Medium (token savings) | Fully reversible |
| 3 | F3: Findings-identity feedback | Enhance | ~4 hours | Medium (cost reduction) | Fully reversible |
| 4 | F4: Baseline rescaling | Tune | ~30 min | Low (routing quality) | Fully reversible |

## Dependencies

- F1 depends on interknow plugin access
- F2 depends on flux-drive resolve workflow
- F3 depends on intersynth synthesis agent
- F4 depends on interspect scoring code

## Evidence

- 5-agent flux-drive review: `.clavain/reviews/darwinian-evolver-integration/`
- Synthesis: `.clavain/reviews/darwinian-evolver-integration/synthesis.md`
- Research review: `docs/research/imbue-darwinian-evolver-arc-agi-2-review-2026-02-27.md`
- Source code: `docs/research/darwinian_evolver/` (cloned repo)
