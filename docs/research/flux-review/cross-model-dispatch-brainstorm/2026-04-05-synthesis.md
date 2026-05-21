---
artifact_type: review-synthesis
method: flux-review
target: "docs/brainstorms/2026-04-04-cross-model-dispatch-brainstorm.md"
target_description: "Cross-model dispatch — evidence-proportional tier routing for interflux expansion pool"
tracks: 4
track_a_agents: [fd-staged-dispatch-correctness, fd-safety-floor-invariant, fd-budget-integration, fd-expansion-signal-quality, fd-backward-compat]
track_b_agents: [fd-clinical-triage-resource, fd-insurance-actuarial, fd-power-grid-dispatch, fd-news-editorial]
track_c_agents: [fd-venetian-glass-grading, fd-han-salt-monopoly, fd-polynesian-wayfinding, fd-japanese-sword-testing]
track_d_agents: [fd-byzantine-typikon-liturgical, fd-ayurvedic-constitution, fd-songline-navigation]
date: 2026-04-05
---

# Cross-Track Synthesis: Cross-Model Dispatch Brainstorm

**Target:** `docs/brainstorms/2026-04-04-cross-model-dispatch-brainstorm.md`
**Tracks:** 4 (Adjacent + Orthogonal + Distant + Esoteric)
**Total agents:** 16 (5 + 4 + 4 + 3)
**Total findings:** ~53 (15 + 16 + 7 + 15)

## Critical Findings (P0/P1)

### P0: Safety Floor Bypass via Empty Model Return
**Source:** Track A — fd-safety-floor-invariant (SFI-1)

`_routing_apply_safety_floor` returns empty on empty input. If `_routing_downgrade` returns an empty string (bash function failure, unrecognized model name, case fall-through), the safety floor is bypassed entirely — the most critical invariant in the system fails silently.

**Fix:** Guard before floor clamp: `[[ -n "$model" ]] || model="haiku"`. Add INVARIANT comment. This was the only P0 across all 53 findings — and it's a 1-line fix.

### P1 Cluster: Missing Primitives (3 findings, Track A)

Three brainstorm-assumed primitives don't exist:
- **SFI-2:** `_routing_downgrade()` has no implementation. Must handle: opus→sonnet, sonnet→haiku, haiku→haiku, empty→unchanged, local model names.
- **SDC-2:** No per-agent model override mechanism. Step 2.0.5 returns a JSON map with no way to inject per-agent adjustments for Stage 2.
- **BC-1:** No feature gate. Every comparable interflux feature (AgentDropout, incremental expansion, B2 routing) has a config toggle. Cross-model dispatch needs `cross_model_dispatch: { enabled: true, mode: shadow|enforce }` in budget.yaml.

### P1 Cluster: Speculative Launch Bypass (2 findings, Tracks A + D)

- **SDC-1 (Track A):** Speculative launches (Step 2.2a.6) fire before `routing_adjust_expansion_tier` is called — they bypass tier adjustment entirely.
- **TYP-03 (Track D):** Even if fixed, speculative launches use partial Stage 1 signal. Score=2 at speculative time is weaker evidence than score=2 at full expansion time. Fix: apply `speculative_score = max(score - 1, 1)` discount.

### P1 Cluster: Budget Accounting (2 findings, Tracks A + B)

- **BI-1 (Track A):** Budget pressure computed from pre-adjustment estimates — conservative bias. Two-pass needed.
- **Finding 10 (Track B, fd-power-grid-dispatch):** No spinning reserve for speculative launches — budget pressure computed without setting aside capacity for late-arriving agents. Fix: subtract `speculative_launch_count × avg_sonnet_cost` from available budget before computing pressure.

## Cross-Track Convergence

These findings appeared independently in 2+ tracks — the highest-confidence signals because they were discovered through independent reasoning paths at different semantic distances.

### Convergence 1: Two-Axis Tier Assignment (4/4 tracks)
**Convergence score: 4/4 — unanimous**

The brainstorm's tier function takes one content signal: expansion score. All four tracks independently identify a missing second axis.

| Track | Agent | Framing |
|-------|-------|---------|
| A (Adjacent) | fd-expansion-signal-quality | Score distribution clusters at 2; insufficient signal granularity for meaningful differentiation |
| B (Orthogonal) | fd-clinical-triage-resource | Under-triage risk asymmetry — same score means different things for different domain criticalities |
| B (Orthogonal) | fd-insurance-actuarial | Expected value = P(finding) × severity, not a composite score. Score conflates proximity and severity |
| C (Distant) | fd-japanese-sword-testing | Domain reasoning complexity is independent of evidence strength — haiku on a complex domain is structurally different from haiku on a simple domain |
| C (Distant) | fd-polynesian-wayfinding | Signal strength ≠ signal difficulty to interpret. Weak evidence on a complex domain needs MORE capability, not less |
| D (Esoteric) | All three agents | `routing_adjust_expansion_tier` is a two-variable function in a three-variable problem. Missing variable: agent capacity/constitution |

**The fix converges too:** Add `domain_complexity: low|medium|high` to `agent-roles.yaml`. The effective tier becomes `max(score_tier, complexity_floor, safety_floor)`. Tracks C and D also suggest `max_model` ceiling for simple domains.

### Convergence 2: Pool-Level Quality Floor (3/4 tracks)
**Convergence score: 3/4**

Per-agent safety floors do not guarantee pool-level quality. Budget compression can simultaneously downgrade all planners/editors to haiku while only safety-floored agents survive.

| Track | Agent | Framing |
|-------|-------|---------|
| B (Orthogonal) | fd-insurance-actuarial | Correlated downgrade risk — individual haiku decisions compound into portfolio-level P0 |
| B (Orthogonal) | fd-power-grid-dispatch | Spinning reserve — capacity set aside for contingency, not consumed by the primary dispatch |
| D (Esoteric) | fd-byzantine-typikon-liturgical | Per-feast floors ≠ Lenten pool-wide floors. Budget compression needs a pool-level guarantee |
| D (Esoteric) | fd-ayurvedic-constitution | Constitutional capacity ignored — `fd-architecture` has min_model:sonnet in agent-roles.yaml but expansion tier adjustment doesn't read it |

**Fix:** After per-agent adjustment, assert: at least one planner/reviewer-role agent at sonnet. Cap simultaneous haiku downgrades at `floor(pool_size / 2)`.

### Convergence 3: No Escalation / Reassessment Path (3/4 tracks)
**Convergence score: 3/4**

Tier assignment is one-shot. No mechanism exists for a low-tier agent to signal "I found something that exceeds my capability."

| Track | Agent | Framing |
|-------|-------|---------|
| B (Orthogonal) | fd-clinical-triage-resource | ED mandates reassessment on patient deterioration. No re-triage mechanism exists. |
| B (Orthogonal) | fd-news-editorial | Stringer has no way to call the desk — no escalation from low-tier to high-tier followup |
| C (Distant) | fd-polynesian-wayfinding | Progressive commitment — weak signals should increase attention, not decrease investment |
| D (Esoteric) | fd-songline-navigation | Stage 2 findings revealing new P0/P1 have no return path to trigger secondary expansion |

**Fix (v1):** Advisory logging only — after each agent completion, compare finding severity against assigned tier. Flag `tier-escalation-candidate` if finding severity ≥ P1 and agent was downgraded. No dynamic restart needed. The data enables future escalation logic.

### Convergence 4: Calibration Feedback Loop (3/4 tracks)
**Convergence score: 3/4**

The tier-to-outcome mapping is set once and never validated. Every parallel discipline depends on feedback loops the brainstorm defers.

| Track | Agent | Framing |
|-------|-------|---------|
| A (Adjacent) | fd-expansion-signal-quality | No validation that expansion scores predict finding value. Open Question 3 should be in-scope. |
| B (Orthogonal) | fd-insurance-actuarial | No loss experience feedback — 50 runs with no empirical basis for recalibrating score→tier mapping |
| B (Orthogonal) | fd-clinical-triage-resource | Triage nurse competency — uncalibrated scoring on high-stakes decisions |
| D (Esoteric) | fd-ayurvedic-constitution | Interspect calibration emit deferred without justification despite existing infrastructure |

**Fix:** Minimum viable: log `(agent, expansion_score, adjusted_tier, finding_count, max_finding_severity)` per run. 3 fields, available at run completion. After 20 runs, sufficient for correlation analysis. Promote Open Question 3 from deferred to in-scope.

### Convergence 5: Correlated Signal Inflation (2/4 tracks)
**Convergence score: 2/4**

Expansion scores can be inflated by correlated evidence from the same root finding.

| Track | Agent | Framing |
|-------|-------|---------|
| C (Distant) | fd-polynesian-wayfinding | Multi-signal convergence requires signal independence — two correlated signals should count as one |
| C (Distant) | fd-venetian-glass-grading | Grade validity — high score from non-adjacent domain is phantom adjacency inflation |

**Fix:** Add `trigger_source_id` to expansion score contributions. Deduplicate before summing.

## Domain-Expert Insights (Track A)

The adjacent-domain review produced the implementation-level findings that directly block writing a plan:

1. **Pipeline ordering must be specified as a sequence diagram.** Three separate findings (SDC-1 speculative bypass, BI-1 pre-adjustment estimates, SFI-1 empty model) all trace to unspecified ordering. The brainstorm needs an explicit sequence: `expansion_score → sort by score DESC → per-agent tier adjust → budget pressure → safety floor → dispatch`.

2. **Score distribution makes the feature modest, not transformative.** ESQ-1: expansion scores cluster at 2 in practice (~70%). Tier adjustment is a no-op for score=2. Projected savings should be revised from 15-40K to 0-15K per run. The feature's primary value shifts from cost savings to quality differentiation (right-sizing models to tasks).

3. **Operational infrastructure is table stakes.** Every comparable feature has a config toggle, shadow mode, and rollback path. The brainstorm needs: `cross_model_dispatch: { enabled: true, mode: shadow|enforce }` in budget.yaml.

## Parallel-Discipline Insights (Track B)

The orthogonal review surfaced three cross-cutting operational patterns:

1. **Risk asymmetry (ED triage):** Over-investing in a low-value agent wastes tokens. Under-investing in a high-value agent misses findings. The costs are asymmetric — the brainstorm treats them symmetrically. Fix: `undertriage_risk` field in agent-roles.yaml for agents adjacent to safety-critical domains.

2. **Merit order (power grid):** Agents must be processed in descending expansion score order, not arbitrary order. High-score agents get first claim on budget headroom. Two-line sort before the dispatch loop.

3. **Continuous budget curve (power grid):** Budget pressure as three discrete states (low/medium/high) creates a cliff at 50%. Replace with continuous `pressure_ratio` (0.0-1.0) in the API; implement thresholds internally.

## Structural Insights (Track C)

The distant-domain review's unifying contribution: **tier assignment is one-dimensional when it should be two-dimensional.** All four distant domains — from Venetian glassblowing to Polynesian wayfinding — independently converge on this. The missing dimension is domain reasoning complexity, independent of evidence strength.

Additional structural patterns:
- **Savings recycling (Han salt):** Token savings from downgrades are tracked but never reinvested. An upgrade pass after the adjustment loop would recycle savings into borderline-case upgrades.
- **One-shot tier is correct (Venetian glass):** Mid-run tier switching is the glassblowing equivalent of changing furnace temperature mid-process — risky. The brainstorm's exclusion of dynamic switching is validated.

## Frontier Patterns (Track D)

The esoteric-domain review's most surprising contributions:

1. **Byzantine concurrence rules → tiebreaker.** Equal expansion scores with no tiebreaker means arbitrary iteration order determines outcomes. Fix: sort by `(score DESC, role_priority DESC, name ASC)`.

2. **Ayurvedic prakriti → agent constitution.** The function ignores `min_model` from agent-roles.yaml during expansion. `fd-architecture` has `min_model: sonnet` but expansion mode doesn't read it. The safety floor function covers explicitly listed agents, but agent-roles.yaml has broader coverage. Fix: read constitutional floor before safety floor.

3. **Songline initiation levels → finding capability classes.** Some finding types literally cannot be produced at haiku tier. No model exists of which findings require which minimum capability. This is the deepest structural insight — it reframes the problem from "how much should we invest" to "what is possible at each investment level."

## Synthesis Assessment

**Overall quality:** The brainstorm's core design (expansion-score-driven tier adjustment with budget pressure and safety floors) is sound and validated by all four tracks. The A+C hybrid recommendation is the right architecture.

**Highest-leverage improvement:** Add `domain_complexity` as a second axis to tier assignment. This resolves the unanimous 4/4 convergence finding, addresses the score-clustering problem (it matters even when score=2 if the domain is complex), and aligns with the existing `agent-roles.yaml` structure. Estimated: 2 YAML fields per agent + 2 checks in the routing function.

**Surprising finding:** The Ayurvedic constitution insight (AYU-01) — that `agent-roles.yaml` already declares `min_model` for planners/reviewers but the expansion tier function doesn't read it — means the brainstorm has a gap that the existing codebase already provides the infrastructure to fix. The floor data exists; it just isn't wired.

**Semantic distance value:** The outer tracks (C/D) contributed qualitatively different insights from the inner tracks (A/B). Track A found implementation bugs. Track B found operational patterns. Track C found the missing axis. Track D found the missing axis AND the pool-level guarantee gap AND the constitutional floor wiring gap. The insights compound rather than restate — each distance tier adds a new dimension of critique.

## Consolidated Must-Fix List (Before /write-plan)

| # | Finding | Source | Fix |
|---|---------|--------|-----|
| 1 | P0: Empty model bypasses safety floor | Track A SFI-1 | `[[ -n "$model" ]] \|\| model="haiku"` before floor clamp |
| 2 | P1: `_routing_downgrade()` doesn't exist | Track A SFI-2 | Implement using `_routing_model_tier()` |
| 3 | P1: No per-agent model override in dispatch | Track A SDC-2 | Stage 2 passes adjusted model directly to Task calls |
| 4 | P1: No feature gate | Track A BC-1 | `cross_model_dispatch: { enabled, mode }` in budget.yaml |
| 5 | P1: Speculative launches bypass tier adjustment | Track A SDC-1 | Call tier adjustment inside speculative launch loop |
| 6 | P1: Budget pressure uses pre-adjustment estimates | Track A BI-1 | Two-pass: tentative adjust → recompute pressure → final adjust |
| 7 | P1: No spinning reserve for speculative launches | Track B Finding 10 | Subtract reserve from available budget before pressure calc |
| 8 | P1: Constitutional floor not wired (agent-roles.yaml min_model ignored) | Track D AYU-01 | Read min_model from agent-roles.yaml in expansion function |
| 9 | P1: Correlated signals inflate expansion score | Track C P-WAY | Add `trigger_source_id`, deduplicate before summing |

## Consolidated Should-Fix List (First Iteration)

| # | Finding | Source | Fix |
|---|---------|--------|-----|
| 10 | `domain_complexity` + `max_model` fields | Tracks C+D (4/4 convergence) | Add to agent-roles.yaml, apply in tier function |
| 11 | Pool-level sonnet guarantee | Tracks B+D (3/4 convergence) | Assert ≥1 planner/reviewer at sonnet after adjustment |
| 12 | Calibration logging | Tracks A+B+D (3/4 convergence) | Log (agent, score, tier, finding_count, max_severity) |
| 13 | Merit order sort | Track B Finding 9 | Sort by score DESC before dispatch loop |
| 14 | Tiebreaker for equal scores | Track D TYP-01 | Sort by (score, role_priority, name) |
| 15 | Tier field in finding logs | Track C Finding 6 | Emit `tier` per agent for future weighted synthesis |
| 16 | Upgrade pass for savings recycling | Track C Finding 7 | One priority-ordered upgrade after adjustment loop |
| 17 | Escalation advisory logging | Tracks B+C+D (3/4 convergence) | Flag tier-escalation-candidate when finding severity > tier |
| 18 | Revised savings estimate | Track A ESQ-1 | 0-15K per run, not 15-40K |
