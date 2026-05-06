---
date: 2026-05-05
bead: sylveste-s3z6.19.8
parent_epic: sylveste-s3z6.19
status: decided
supersedes: docs/research/flux-review/microrouter-track-b6/2026-05-01-synthesis.md (architecture forks only)
---

# Microrouter Track B6 — Design Revision (`.19.8`)

## TL;DR

The original `.19.8` brief framed two architecture forks (α vs β judge family; calibration freeze SHA enforcement) and a holdout-agents workload. Empirical investigation collapsed all of those into a single prior question: **does a learned router beat the existing `agent-roles.yaml` heuristic at all?** That assumption underpins every other design choice in `.19` and has never been measured. This revision re-scopes `.19.1` accordingly.

## Empirical findings (load-bearing)

### Finding 1 — β is not a v0 option

The original synthesis offered Architecture β: anchor the holdout against observed downstream pass@1 instead of the calibration posterior. Investigation:

- `routing-calibration.json` doesn't exist in production on this machine (only `os/Clavain/cmd/clavain-cli/testdata/`).
- `~/.clavain/interspect/interspect.db` has 19 sessions, **0 evidence rows**.
- The `hit_rate` field in the testdata example is computed from `verdict_status == "NEEDS_ATTENTION"` (quality-gates judge flag), not actual task outcomes. Source: `interverse/interspect/hooks/lib-interspect.sh:3293+` (`verdict_outcome` aggregation).
- No event family in interspect captures CI pass / user acceptance / clean bead closure as a primary signal.

Implication: β has no anchor data. Building it requires a new event family (`interspect-task-outcome`) plus a multi-week data-accumulation window before training labels stabilise.

### Finding 2 — Most "core" cognitive reviewers are dormant

The 12 always-triaged reviewers split sharply by usage:

| Reviewer | Synthesis appearances |
|---|---|
| fd-architecture, fd-safety, fd-correctness, fd-quality, fd-user-product, fd-performance, fd-systems | constant (every flux-drive run) |
| fd-game-design | 1 in `.claude/flux-drive-output/` |
| fd-decisions | 2 |
| fd-people, fd-resilience, fd-perception | 0–1 each |

The dormant five never produced load-bearing findings. Keeping them in the always-triaged set adds triage cost without insight.

### Finding 3 — The agent population is bimodal

Registry: 357 agents, 0 "proven" (use ≥3, lines >150), 215 stubs. The 12 stable reviewers are *not in the project's `.claude/agents/`* registry — they live in interflux's plugin dir. The registry tracks **generated** agents only. Generated agents pattern: created during one flux-review of a specific document, used 1–2 times, never again.

Implication for routing: the workload is not "predict tier for an agent the router has seen N times." It is "stable-7 agents called constantly + a long tail of esoteric one-shots." A router trained on agent name → tier cannot generalise to the long tail. The latency/privacy wins that motivated `.19` come disproportionately from the long tail (the stable-7 are mostly sonnet-floored, so 5 of 7 bypass routing entirely).

### Finding 4 — The null hypothesis was never tested

`agent-roles.yaml` already encodes role → `model_tier` plus `min_model` safety floors plus `domain_complexity`. lib-routing.sh already clamps. The microrouter epic implicitly assumes a learned router beats this heuristic by enough to justify a multi-week LoRA distillation project, but **no measurement of the heuristic's headroom exists**. Three weeks of design work (`.19.1` through `.19.7`) is conditional on an unmeasured assumption.

## Decisions

### D1 — Prune the dormant five from the always-triaged core

Move `fd-game-design`, `fd-people`, `fd-decisions`, `fd-resilience`, `fd-perception` out of the always-triaged set. They remain available via interflux's distant-domain triage when a review's content scores them in. The stable core becomes seven: `fd-architecture`, `fd-safety`, `fd-correctness`, `fd-quality`, `fd-user-product`, `fd-performance`, `fd-systems`.

Rationale: zero observed signal from these five across the corpus reviewed. Cost of keeping them: triage churn + an unmaintained surface.

Out-of-scope here: the actual file moves and config edits. Tracked separately as a follow-up bead under the interflux epic, not under `.19`.

### D2 — Run a heuristic-baseline measurement before any other `.19` work (Approach E)

Before `.19.1` proceeds, measure how the existing `agent-roles.yaml` heuristic performs against historical workload. Concrete shape:

- Replay shadow over the existing verdict corpus.
- For each verdict, record: (heuristic recommendation, what was actually used, judge-flag outcome).
- Compute heuristic hit-rate per (agent, complexity_tier) cell.
- Compare against an oracle upper bound constructed from the verdict outcomes.
- Quantify "headroom": the gap between heuristic and oracle, broken down by tier and by routing-eligible vs sonnet-floored agents.

Decision rule:
- **Heuristic within ~5% of oracle on routing-eligible traffic → kill the epic.** The LoRA distillation is solving a non-problem; ship a `.19-CLOSE` bead documenting the measurement.
- **Headroom >5% but concentrated in stable-7 → narrow `.19.1` to a learned router for those 7 only.** Holdout methodology is straightforward; β telemetry can come later.
- **Headroom >5% concentrated in the long tail (generated agents) → `.19.1` redesigns to a content-feature classifier**, not a name-keyed lookup. The classifier features come from agent file frontmatter (role, domain, description length, line count, distillation lineage). β telemetry becomes hard prereq because evaluating a content-feature classifier on novel agents requires real outcomes, not judge agreement.

### D3 — If the epic survives, evaluation method is leave-one-review-out + online regret (Approach D + C)

Replaces the original "by-time holdout + held-out-agents workload" plan, which assumed exchangeable agent-level draws. Generated agents within a review are tightly correlated; cross-review they vary widely. The right evaluation unit is the review.

- **Development-time**: leave-one-review-out cross-validation. Train on N–1 reviews, evaluate on the held-out review (including its generated agents). Average across folds. Tests both name-novelty and content-novelty in one shot.
- **Promotion gating**: online regret in shadow mode. Log per-decision regret against the heuristic baseline. Promote shadow→enforce when cumulative regret stays below threshold over a window with sufficient diversity (≥3 distinct sprint phases, ≥3 distinct agent categories).
- Standard cross-validation (the `.19.4` "by-time holdout" plan) is dropped — wrong tool for this regime.

### D4 — β as v1 architecture, with telemetry as a hard prereq (`.19.9`)

If D2 proves headroom and `.19.1` proceeds, the v0 architecture is α (different judge family from anchor — Gemini 2.5 or local Qwen3.6-35B consensus as augmentation judge; existing GPT-5.5/Opus calibration as the anchor, accepted as a known-circular limitation of v0). The v1 architecture is β.

Carve a new bead `sylveste-s3z6.19.9` for the telemetry prereq:

- New event family `interspect-task-outcome` writing CI/acceptance/clean-bead-closure signals.
- Pass@1 definition: bead clean-close = closed AND no child/related bead with label `bug`/`defect`/`regression` filed within **N=4 sprints**. (Conservative N: catches slow-burn regressions; doubles minimum data-accumulation time but accepts that cost for label fidelity.)
- Calibration freeze: snapshot the pass@1-anchored calibration file at the holdout cut date as `routing-calibration.SNAPSHOT-<date>.json`. SHA hash check enforced at training pipeline entry only (one place to fail loudly; cheaper than per-read; trusts other readers via convention).
- Β can only become v0 of any *future* router work after `.19.9` ships AND has accumulated ≥4 sprints of pass@1 data.

`.19.9` is a sibling of `.19.8`, not blocked by it. It can ship in parallel with `.19.1`'s heuristic measurement.

### D5 — Existing `.19.5`/`.19.6` corrections still stand

The non-architectural P0s from the synthesis (resolver below `overrides[agent]`; port 8422; no schema validator; lib-routing.sh is Bash; explicit fall-through table; rollback runbook; shadow log schema; privacy fail-closed) are preserved and apply unchanged if the epic survives D2. Those edits should land regardless because they're factual corrections; if D2 kills the epic, they get reverted as part of the `.19-CLOSE` work.

## What this means for downstream beads

| Bead | Was | Becomes |
|---|---|---|
| `.19.1` | Design doc + paper deep-read for LoRA distillation | **Phase 1**: heuristic-baseline measurement (Approach E). **Phase 2** (conditional): learned-router design narrowed by what Phase 1 reveals — narrow-set router OR content-feature classifier OR cancelled. |
| `.19.2` | Labelled corpus build | Conditional on `.19.1` Phase 2. If content-feature classifier path, the corpus is per-agent-frontmatter, not per-task-text. |
| `.19.3` | LoRA training | Conditional on `.19.1` Phase 2 + `.19.2`. Latency-weighted regret loss (not cost-weighted — Codex OAuth is free). Privacy is a resolver constraint, not in the loss. |
| `.19.4` | Eval matrix | Replaces "by-time holdout + held-out-agents workload" with leave-one-review-out + online regret (D3). Per-tier recall ≥0.60 gate retained. |
| `.19.5` | Resolver implementation | Unchanged corrections (D5). Conditional on `.19.1` Phase 2 surviving. |
| `.19.6` | Privacy extension | Unchanged corrections (D5). Conditional on `.19.5`. |
| `.19.7` | Verifier (gongfu cha pattern) | Re-evaluate post-`.19.1` Phase 2; verifier may become moot if content-feature classifier already provides confidence signals. |
| `.19.8` | This document | Done when committed. |
| `.19.9` | NEW: pass@1 telemetry pipeline | Sibling to `.19.8`. Hard prereq for any future v1 (β) router. Independent of D2 outcome — even if `.19` dies, telemetry is useful for general routing decisions. |

## Done when

- This brainstorm is committed to `docs/brainstorms/`.
- `.19.8` body is updated with a pointer to this doc and the four decisions (D1–D5).
- `.19.1` body is rewritten to two phases (heuristic measurement → conditional learned-router design).
- `.19.4` body is updated to leave-one-review-out + online regret.
- `.19.9` is created as a sibling of `.19.8` for the telemetry prereq.
- `.beads/issues.jsonl` is refreshed via `bd export -o .beads/issues.jsonl`.
- All staged in a single commit referencing `sylveste-s3z6.19.8`.

## Open questions deferred to `.19.1` Phase 1

- Exact oracle construction protocol for the headroom measurement (strong vs weak vs implicit oracle — synthesis named this gap; needs to be pinned before measurement runs).
- The "~5%" threshold for kill-vs-proceed is a judgement call, not a derived number. Phase 1 should report the headroom and let the user decide rather than auto-deciding.
- Whether the dormant-five prune (D1) is reversible if a future workload genuinely needs them — the bead-tracking question is downstream of the file-move work, not this design.
