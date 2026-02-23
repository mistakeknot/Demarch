# Brainstorm: Running Heterogeneous Routing Experiments Across Demarch

**Bead:** iv-jocaw
**Date:** 2026-02-23
**Parent:** iv-jc4j (experiment design), iv-dthn (feedback loop thresholds)

## Context

Phase A (B2 shadow mode) and Phase B (agent-roles.yaml) are shipped. Shadow mode logs routing decisions to stderr during every flux-drive review. We need to actually **run the experiments** and **collect results**.

## What Infrastructure Already Exists

| Component | Status | What It Gives Us |
|-----------|--------|-----------------|
| B2 shadow logging (lib-routing.sh) | Live | `[B2-shadow] complexity=C2 would change model: sonnet → haiku` on stderr |
| interstat metrics.db | Live | Per-agent token counts, model, timestamps in SQLite |
| interbench | Working | Run capture + content-addressed artifact store (no replay yet) |
| flux-drive output | Structured | Per-agent `.md` with Findings Index, `findings.json`, convergence counts |
| intersynth verdicts | Working | Deduped findings, severity, convergence tracking |
| budget.yaml | Configured | Per-input-type and per-agent token budgets |
| agent-roles.yaml | New | Dr. MAS role→model→agent mappings |

## Key Insight: We Don't Need a New Runner

The experiment infrastructure is already the normal flux-drive pipeline. Each flux-drive review already:
1. Classifies complexity (shadow mode logs what B2 would change)
2. Dispatches agents with tracked token costs (interstat)
3. Produces structured findings with convergence metrics (intersynth)
4. Captures artifacts (can pipe through interbench)

**The experiment is: run flux-drive on diverse repos, then analyze the captured data.**

## Experiment Execution Strategy

### Approach 1: Batch Reviews (Sequential)
Run `/interflux:flux-drive` on 7 target repos sequentially, capturing shadow data. Then analyze.

**Pros:** Simple, deterministic, one session per review.
**Cons:** Slow (7+ sessions), B1-only data (shadow doesn't change routing).

### Approach 2: Shadow + Enforce A/B
Run each repo twice: once with `complexity.mode: off` (B1 baseline), once with `complexity.mode: enforce` (B2 active). Compare outputs.

**Pros:** Direct A/B comparison, real model-switching data.
**Cons:** 14+ reviews needed, complexity-enforce may not be ready for production.

### Approach 3: Hybrid — Shadow First, Then Selective Enforce
1. Run 7 reviews with shadow mode (current state) — establishes baseline + shadow projections
2. Pick 3 repos where shadow shows most divergence (e.g., where C1/C2 tasks would get Haiku)
3. Run those 3 with enforce mode — actual heterogeneous routing
4. Compare: did enforce produce different quality? Cost savings real?

**Pros:** Data-driven selection of enforce targets, lower risk, 10 total reviews.
**Cons:** Still multiple sessions, partial coverage.

### Recommended: Approach 3 (Hybrid)

## Target Repos (Diverse Pillar Coverage)

| Repo | Type | Pillar | Expected Complexity | Why This Repo |
|------|------|--------|-------------------|---------------|
| core/intermute | Go service | Core (L1) | C4-C5 (complex) | Heavy concurrency, real production code |
| core/interbench | Go CLI | Core (L1) | C2-C3 (simple-moderate) | Small, focused — Haiku candidate |
| interverse/interlock | Go MCP plugin | Interverse (L3) | C3 (moderate) | Recently modified, known quality |
| interverse/intercache | Claude plugin | Interverse (L3) | C2-C3 (simple-moderate) | New plugin, Haiku candidate |
| os/clavain | Meta-plugin | Clavain (L2) | C5 (architectural) | Huge, complex, Opus territory |
| apps/autarch | TUI app (Go) | Autarch (L3) | C4 (complex) | Bubble Tea + DB, real app |
| interverse/interflux | Review engine | Interverse (L3) | C3-C4 (moderate-complex) | Self-referential — reviewing the reviewer |

## Data Collection Plan

For each review, capture:

1. **Shadow routing log** — redirect stderr to file: `2>/tmp/routing-shadow-{repo}.log`
2. **interstat metrics** — query `agent_runs` table after review for per-agent token counts
3. **Findings quality** — save `findings.json` and `summary.md`
4. **Convergence** — how many agents found the same issues independently
5. **Timing** — wall clock per agent (from interstat timestamps)

### Analysis Script Needs
- Query interstat SQLite for cross-review comparison
- Parse shadow logs to compute projected savings
- Compare finding quality across B1 vs B2-enforce runs
- Generate Pareto frontier chart (cost vs quality for each policy)

## Experiment Schedule

### Phase 1: Shadow Baseline (7 reviews)
Run flux-drive on all 7 repos with current `mode: shadow`.
Collect: shadow logs, interstat data, findings, convergence.
Estimated: 1-2 sessions.

### Phase 2: Analyze Shadow Data
Parse shadow logs to identify:
- Which repos would see the most model changes under B2
- Which agents would be affected (Haiku vs Sonnet shifts)
- Projected cost savings
Write: `docs/research/heterogeneous-routing-results.md` (partial)

### Phase 3: Selective Enforce (3 reviews)
Pick 3 repos with highest projected divergence.
Switch to `mode: enforce`, re-run flux-drive.
Compare: actual vs projected savings, quality impact.

### Phase 4: Role-Aware Test (3 reviews)
Same 3 repos, but with agent-roles.yaml consumed by dispatch.
Compare: role-aware vs uniform Sonnet.

### Phase 5: Results + Recommendation
- Write final results document
- Pareto frontier analysis
- Routing recommendation matrix
- Update routing.yaml with approved changes (or keep shadow)

## Open Questions

1. How do we measure "quality" of a review? Options:
   - Finding count (crude but measurable)
   - Unique finding rate per agent (measures agent contribution)
   - User-rated finding relevance (subjective, hard to automate)
   - Convergence score (more agents agree = higher confidence)

2. Should we test collaboration modes (Exp 3) in this sprint or defer?
   - Collaboration modes require changes to flux-drive dispatch logic
   - Could defer to a follow-up bead

3. What's the minimum viable experiment?
   - 7 shadow reviews + analysis might be enough to make routing decisions
   - Enforce testing is a bonus that validates shadow projections

## Risk Register

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Shadow data shows no meaningful divergence | Medium | Sprint produces no actionable changes | Still validates B1 as optimal |
| Enforce mode degrades quality on complex repos | Low | Wasted effort, need to revert | Only enforce on simple repos where Haiku is likely safe |
| interstat data insufficient for comparison | Low | Can't compute cost deltas | Manual token counting from flux-drive output |
| Reviews take too long (budget exhaustion) | Medium | Can't complete all 7 repos | Prioritize 4 most diverse repos |
