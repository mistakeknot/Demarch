# Flux-Drive Review Synthesis — Small-Local-Model Rescoping (Sylveste-s10)

**Reviewed:** 2026-05-17
**Document:** `/Users/sma/projects/Sylveste/docs/brainstorms/2026-05-17-small-local-model-rescoping.md`
**Agents:** fd-decisions, fd-systems, fd-perception, fd-resilience
**Bead:** Sylveste-s10

---

## Verdict

**PROMOTE C' and E to Phase-1, with mandatory pre-steps.** Conditional pass.

The brainstorm shows strong decision discipline and correctly kills three weak candidates (A, C, D). But three convergent findings block immediate Phase-1 promotion:

1. **Kill-rule calibration is sunk-cost anchored** (fd-decisions, fd-systems, fd-resilience) — the ">50% prob / >20% improvement" threshold reads as post-hoc from the microrouter loss rather than first-principles for THIS task.
2. **C' scope-shift acknowledged but unresolved** (fd-decisions, fd-perception, fd-resilience) — the brainstorm's open-questions section flags the generative→retrieval reframe but the Recommendation section proceeds without a decision.
3. **Phase-1 measurement design lacks pre-committed kill thresholds** (fd-decisions, fd-resilience) — both C' and E can return inconclusive results that force mid-bead renegotiation instead of clean pass/fail.

Plus one P1 single-reviewer finding too important to bury: **E has an invisible false-negative feedback loop** (fd-systems) — the classifier is blind to what it filters; retraining on dispatches-that-fired bakes the classifier's biases in. Concept drift becomes undetectable.

---

## Convergent Findings (≥2 reviewers independently flagged)

| Severity | Finding | Reviewers | Status |
|----------|---------|-----------|--------|
| **P1** | Kill-rule inherited from microrouter loss, not first-principles | fd-decisions, fd-systems, fd-resilience | **Must resolve before Phase-1** |
| **P1** | C' reframes from "sub-10B generative" to "100M embedding" without explicit acknowledgment | fd-decisions, fd-perception, fd-resilience | **Must resolve before Phase-1** |
| **P1** | Phase-1 measurement lacks pre-committed kill thresholds | fd-decisions, fd-resilience | **Must resolve before Phase-1** |
| **P2** | Workload sampling is recency-biased (session memory only, not dispatch logs) | fd-perception, fd-systems (implicit) | Run territory lookup before promoting |
| **P2** | E latency-versus-recall inversion (latency win unvalidated, recall risk understated) | fd-perception, fd-resilience | Benchmark classifier latency before commitment |

---

## P1 Findings (Consolidated, line-cited)

### P1.1 Kill-rule calibration may be sunk-cost anchored
- **Location:** lines 1–17 (Frame), 98–107 (Ranking table), 121 (open question)
- **Lead:** fd-decisions. **Concurring:** fd-resilience, fd-systems
- **Issue:** ">50% prob of >20% improvement" appears anchored to the 85% microrouter trigger rather than derived from C'/E task structure. For narrow tasks with weak baselines (keyword search, no pre-filter), the bar may be too strict.
- **Recommendation:** Re-validate per-candidate:
  - **C':** Embeddings systematically beat keyword search on semantic similarity → ">40% prob of >15% improvement" is achievable. Accept F1 ≥ 0.78 as Phase-1 success.
  - **E:** Verify 99% recall at 30% suppression is in the Pareto frontier (back-of-envelope: sample 100 dispatch outcomes, judge manually). If >40% suppressible, feasible. If <15%, experiment is low-value.

### P1.2 C' sidesteps the problem frame
- **Location:** lines 20–34 (Frame), 61–72 (Candidate C), 110–113 (Recommendation)
- **Lead:** fd-decisions. **Concurring:** fd-perception, fd-resilience
- **Issue:** Original frame asks for "sub-10B local specialist (fine-tuned or zero-shot)." C' answers with a 100M-param retrieval embedding model. The reframe is honest in the C' section but the Recommendation section proceeds as if no reframe happened. Next implementer may infer embedding models *are* the answer to the generative SLM question.
- **Recommendation:** Pick one before opening bead:
  - **Option A: Accept scope drift.** Rename to "Local-inference specialist rescoping" — retrieval + classifiers in scope. Original "sub-10B generative" question deferred or closed MOOT.
  - **Option B: Restore generative constraint.** Kill C'. Keep only E (which IS generative-shaped: reads agent+doc, decides yes/no).
  - Document the choice in the bead acceptance criteria.

### P1.3 Phase-1 measurement lacks pre-committed kill thresholds
- **Location:** lines 113–115 (Recommendations), 124–125 (open question 4)
- **Lead:** fd-decisions. **Concurring:** fd-resilience (provides concrete MVPs)
- **Issue:** C' says "precision/recall against closed-as-duplicate set" without stating a kill threshold. E says "kill if recall < 95%" but the stated risk floor in the prose is 99%. Without pre-committed thresholds, measurement returns mid-range numbers and forces mid-bead renegotiation.
- **Recommendation:** Pre-commit explicit thresholds:
  - **C' MVP (30 min):** Embed 50 random closed-bead title+desc pairs with BGE-small zero-shot. Grid-search cosine threshold. ADVANCE if F1 ≥ 0.75 AND manual spot-check (5 pairs) shows ≥3 are legitimate duplicates. CLOSE MOOT if F1 < 0.70.
  - **E MVP (60 min):** Train logistic regression on 80 Interspect dispatches (BGE embed of agent-desc + doc-excerpt → finding_count > 0). ADVANCE if recall ≥99% at suppression ≥20% OR recall ≥97% at suppression ≥30%. CLOSE MOOT if recall <95% at all thresholds ≥20%.
  - **Mid-experiment trip-wires:** For C', if median cosine <0.40 on first 10 pairs, stop (embeddings not capturing semantics). For E, if >80% agent descriptions are near-identical post-embedding, stop (classifier cannot discriminate).

### P1.4 Invisible false-negative feedback loop in E
- **Location:** lines 85–96 (Candidate E)
- **Lead:** fd-systems (single-reviewer but P1)
- **Issue:** If E filters out an agent that *would have* produced substantive findings, the finding is never logged. Retraining the classifier uses biased ground truth. Over time, the classifier becomes blind to types of findings it filters. The brainstorm acknowledges recall floor but treats it as a one-shot cost, not a degenerative loop.
- **Recommendation:** Before Phase-1 commit to a ground-truth-preservation protocol:
  - (a) randomly dispatch 5–10% of *filtered-out* agents anyway (measure real recall continuously), OR
  - (b) hold out a fixed test set of pre-classifier dispatch outcomes and re-evaluate quarterly
  - Otherwise the classifier optimizes toward its own blind spots.

### P1.5 Intertrust + Interspect overlap with E not checked
- **Location:** lines 85–96 (Candidate E)
- **Lead:** fd-perception (single-reviewer but P1)
- **Issue:** intertrust already scores agents on trust/precision (per project memory). Are E and intertrust solving the same problem? The brainstorm never checks. If intertrust suppression already exists, E is a duplicate of in-house infrastructure.
- **Recommendation:** Before Phase-1, 30-min discovery: diagram the existing decision flow (intertrust score → dispatch → Interspect outcome). Show where E injects a new decision point. If E *replaces* an existing stage, this is a redesign not an optimization — different blast radius, different bead structure.

---

## P2 Findings

### P2.1 Silent adoption-driven redundancy in C'
- **Location:** lines 62–72
- **Lead:** fd-systems
- **Issue:** If C' works, users stop doing manual duplicate-check thinking. Bead corpus becomes *more* redundant over time because cognitive friction is gone. Ground truth was generated under regime where users did their own dedup.
- **Recommendation:** Phase-1 for C' should include 6-week prospective pre/post analysis: measure duplicate density (title/desc similarity histogram) before vs after C' ships. If redundancy increases, the system has trained users to stop thinking — a system-boundary problem, not a model problem.

### P2.2 Resource contention with V4 spike (EOD 2026-05-19)
- **Location:** line 18, lines 113–116
- **Lead:** fd-resilience
- **Issue:** Brainstorm claims sub-4B runs alongside large-MoE "without VRAM contention" but doesn't validate against flash-moe peak memory pressure during concurrent k8c/0gi.2.7 workloads. M5 Max running simultaneous experiments. Phase-1 timing collides with the V4 spike calendar kill (EOD 2026-05-19).
- **Recommendation:** Before opening Phase-1 beads, measure flash-moe peak VRAM and compute headroom. C' MVP needs ~2hr GPU; E MVP runs on CPU. If headroom <8GB during V4 spike window, defer Phase-1 to post-2026-05-19 or run on CPU only.

### P2.3 E latency-versus-recall inversion
- **Location:** lines 85–96
- **Lead:** fd-perception, fd-resilience
- **Issue:** Cost savings dismissed as negligible (~$5/month), so latency is the motivation. But classifier latency is unvalidated. If TF-IDF + LR takes >100ms, total flux-drive run latency improvement may be <5s (~1%). Meanwhile the recall risk (missing a real finding) is stated as severe ("worse than redundant dispatch") but not reflected in the 95% kill rule.
- **Recommendation:** Benchmark proposed classifier latency locally first. If >200ms p50, the latency win vanishes. Either commit to ≥99% recall (matches stated risk aversion) or drop E and reinvest in C'.

### P2.4 Diminishing-returns curve not inspected for E
- **Location:** lines 85–96
- **Lead:** fd-resilience
- **Issue:** Brainstorm proposes 99% recall at 30% suppression without checking feasibility. Microrouter hit 89.6% and was killed *because* the next 10% costs dramatically more. E may be on the same curve: 3-rule heuristic at 50%/98%, LR at 60%/97%, fine-tuned 7B at 65%/96%. Assumes 99% is achievable without measuring.
- **Recommendation:** Sample 100 dispatch outcomes from Interspect, manually judge "would a classifier suppress this?" If >40% are suppressible, 30%@99% is in frontier. If <15%, problem is trivial and not worth ML.

### P2.5 Workload sampling is recency-biased
- **Location:** lines 122–124 (open question 2)
- **Lead:** fd-perception
- **Issue:** 5 candidates come from session memory + visible beads. None are weighted by FREQUENCY. Explore (candidate B) is anchored to Sylveste-9ve but author doesn't know if Explore was high-volume before dormancy or always marginal. E was deemed "latency-attractive" without measuring actual flux-drive dispatch frequency.
- **Recommendation:** Before finalizing kill rule, run a 5-min dispatch-frequency audit on `~/.claude/interstat/metrics.db`. Top-20 agents by April-2026 count. If any candidate (or hidden workload) appears in top 10, escalate regardless of corpus concerns. If Explore shows 0 in April, B stays deferred.

---

## Unique High-Value Findings (Single Reviewer, P1-equivalent)

### fd-systems: Common substrate is the real scoping question
All 5 candidates (A, B, C, C', D, E) depend on the same "cheap-classifier-on-text" infrastructure. The brainstorm treats them as independent. The real scoping question is **"should we build the cheap-classifier-on-text platform?"** Once that exists, all 5 are downstream applications. Current factoring obscures the platform decision.

**Action:** Reframe the epic. Phase A measures C' as the minimal application of the infrastructure. Phase B commits to the platform only if Phase A + E together hit ROI threshold. Prevents the inertia problem ("we built it, now we must use it").

### fd-systems: Pace-layer mismatch C' vs E
C' retrains quarterly; E needs weekly or online learning. **3–4 orders of magnitude difference in ops costs.** Grouping them as the same initiative misallocates maintenance budget. The brainstorm doesn't surface this.

### fd-systems: Cross-domain frames the user explicitly asked for
- **IR:** duplicate detection is NDCG@k (ranking), not binary classification. Use mean reciprocal rank, not precision/recall, for C'.
- **Recommender systems:** dispatch outcomes are implicit feedback. Cold-start problem for new agents.
- **OR:** E is admission-control. Use bandit algorithms with bounded regret rather than fixed-threshold classifier.
- **Control theory:** recall is set-point, concept drift is disturbance. PID-loop threshold adaptation > static retraining.
- **Biological systems:** immune tolerance (learn to ignore safe queries); apoptosis (retire stale classifiers on schedule).

### fd-resilience: Smallest-viable-experiment MVPs
Concrete <60min Phase-1 designs (incorporated above into P1.3).

### fd-decisions: B's dependency on Sylveste-9ve creates hidden critical path
B (Explore resurrection) depends on Sylveste-9ve diagnosing whether dormancy is cost-driven. **If 9ve is not expected within 2 weeks, open a speculative B measurement bead assuming cost is the blocker; pivot if 9ve contradicts.** Don't let B starve indefinitely on a dependency that may never resolve.

---

## Tensions Across Reviewers

| Tension | Resolution |
|---------|------------|
| Is C' honest? (generative-frame escape) | **Reframe before Phase-1: choose generative-only OR retrieval-included constraint** |
| Is 99% recall at 30% suppression achievable for E? | **Run 2hr diminishing-returns check: sample 100 outcomes, manual relevance judgment** |
| Is >50%/>20% the right threshold? | **Agreed: context-dependent. C': >40%/>15%. E: re-examine after latency check.** |
| Should B wait on Sylveste-9ve? | **fd-decisions explicit: if 9ve >2 weeks out, open speculative B bead anyway** |

No fundamental disagreement on candidate quality. All tensions are about **measurement design**, not about which candidates to pursue.

---

## Recommended Actions Before Phase-1 Promotion

### Mandatory (block Phase-1 beads)

1. **Clarify C' scope.** Decide: is retrieval in scope for "small-local-model"? Document in bead acceptance criteria.
2. **Pre-commit kill thresholds.** C': F1 ≥0.75 MVP / F1 ≥0.80 Phase-2. E: recall ≥99% at suppression ≥20% OR drop E.
3. **Re-validate kill rule per-candidate.** Don't reuse the microrouter 85%/20% threshold without justification.

### Strongly Recommended (pre-Phase-1, <3 hours total)

4. **Run C' MVP (30 min):** 50-pair embed + threshold grid-search. Gate Phase-1 on result.
5. **Run E MVP (60 min):** LR on 80 dispatches. Gate Phase-1 on result.
6. **Latency benchmark.** Time TF-IDF + LR on M5 Max. If >200ms, latency motivation vanishes.
7. **Diminishing-returns check for E.** Manual judgment on 100 dispatch outcomes.
8. **Dispatch-frequency audit.** Top-20 agents in interstat.db. Check for hidden workload candidates.
9. **Intertrust overlap check.** 30-min discovery. Does E duplicate intertrust suppression?

### Nice-to-Have

10. **Platform infrastructure decision.** Reframe C' + E as first apps of "cheap-classifier-on-text" platform.
11. **Cross-domain frame for E.** Sketch one bandit/cascade alternative.

---

## Files

- Brainstorm: `docs/brainstorms/2026-05-17-small-local-model-rescoping.md`
- fd-decisions: `fd-decisions.md` (this directory)
- fd-systems: `fd-systems.md` (this directory)
- fd-perception: `fd-perception.md` (this directory)
- fd-resilience: `fd-resilience.md` (this directory)
- Research synthesis (parallel run): `docs/research/flux-research/sub-10b-local-specialists-narrow-devtool-tasks-20260517T2357/SYNTHESIS.md`
