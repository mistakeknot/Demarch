# Systems-Thinking Review — Small-Local-Model Rescoping

## Summary

The brainstorm correctly identifies two viable candidates (C' embedding-based duplicate detection and E flux-review pre-filter) and applies sound cost-benefit reasoning within the domain of ML feasibility. However, it misses three systemic blind spots: (1) all five candidates share a common cheap-classifier-on-text substrate that should be the real scoping question, (2) the feedback-loop dynamics of C' and E are asymmetric — C' has silent adoption risks while E hides its false negatives — and (3) the kill rule ">50% probability of >20% improvement" is not isomorphic across task types (retrieval vs classification), creating Schelling-point ambiguity that could resurrect similar proposals later. The causal-chain reasoning about why microrouter's lessons don't apply to specialists is sound but under-specified; explicit framing of "general routing" vs "narrow-task specialization" as different system shapes would strengthen the rejection of revival attempts. Finally, cross-domain perspectives (information retrieval, recommender systems, operations research, control theory) are entirely absent, leaving the scoping vulnerable to reframing attacks.

## Findings

### [P1] FINDING: Invisible false-negative feedback loop in E (flux-review pre-filter)

**Location**: docs/brainstorms/2026-05-17-small-local-model-rescoping.md:85–96

**Issue**: The brainstorm correctly identifies that "recall floor must be ~99%" (line 95) but does not map the feedback loop that makes recall unobservable. If E filters out an agent that *would have* produced substantive findings, the finding is never logged in Interspect, so retraining the classifier uses data that is biased by the classifier's own decisions. Over time, the classifier becomes increasingly blind to the types of findings it filters. The brainstorm says "false negatives are expensive" but treats this as a one-shot cost, not a degenerative feedback system.

**Lens**: Feedback loops / Unintended consequences

**Recommendation**: Before Phase-1 measurement on E, commit to a ground-truth logging strategy: either (a) randomly dispatch ~5–10% of filtered-out agents anyway (to measure real recall), or (b) use a held-out test set of recent dispatch outcomes that pre-dates the classifier. Otherwise, you will optimize the classifier toward invisibility.

---

### [P1] FINDING: Silent adoption-driven redundancy in C' (duplicate detection)

**Location**: docs/brainstorms/2026-05-17-small-local-model-rescoping.md:62–72

**Issue**: The brainstorm assumes ground truth is "clean" because "which beads were closed as duplicates" is unambiguous (line 71). But if C' works well, users will stop doing manual duplicate-check thinking when filing beads. They will rely on the system to catch duplicates. This creates a second-order effect: the bead corpus becomes *more* redundant over time, not less, because the cognitive friction that used to produce careful titles is gone. The ground truth (closed-as-duplicate set) was generated under a regime where users did their own dedup thinking; the new regime has different user behavior. The classifier trained on the old regime may not transfer.

**Lens**: Feedback loops / Emergence / Unintended consequences

**Recommendation**: Phase-1 measurement for C' should include a prospective pre/post analysis: measure duplicate density (title/description similarity histogram) of beads filed in the 6 weeks before C' ships vs 6 weeks after. If redundancy increases, the system has inadvertently trained users to stop thinking. This is not a model problem — it's a system boundary problem.

---

### [P2] FINDING: Kill rule uses non-isomorphic metric across candidates

**Location**: docs/brainstorms/2026-05-17-small-local-model-rescoping.md:99–107, 119–121

**Issue**: The ranking table and open question (line 121) both reference ">50% probability of >20% improvement" as the uniform kill threshold. But "20% improvement" means different things across candidates:
- A (lens triage): 20% of findings used → ~0.8 additional findings/run (currently 8/11)
- C' (duplicate detection): 20% reduction in duplicate-hunt time → ~15min/week
- E (flux-review pre-filter): 20% latency reduction → ~20s per run, ~30min/week
- D (commit-msg scoring): N/A (killed on regex coverage, not on improvement metric)

These are incommensurable without conversion to a common currency (dollars, hours, cognitive load). The Schelling point (where both author and reader agree on the threshold) is broken. This creates risk that later advocates for A or other dead candidates will reframe "improvement" differently and resurrect rejected proposals.

**Lens**: Schelling-point risks / Causal chains

**Recommendation**: Pre-commit to a single improvement metric before measurement begins. Options: (a) cost per dispatch (hours + dollars), (b) wall-clock time to complete a flux-drive session, (c) human cognitive effort (Likert scale). Require the same metric for any revival proposal.

---

### [P2] FINDING: Common substrate (cheap-classifier-on-text) is the real scoping question

**Location**: docs/brainstorms/2026-05-17-small-local-model-rescoping.md:36–107 (all five candidates)

**Issue**: A, C', E, and elements of B and D all depend on the same substrate: a sub-4B text classifier that runs locally in <200ms. The brainstorm treats them as independent candidates. But the presence of this infrastructure is a one-time decision, not five decisions. Once you have a cheap-classifier-on-text rig, you can deploy C', E, and other future variants at marginal cost. Conversely, if you decide not to build it, all five candidates fail simultaneously.

**Lens**: Emergence / Causal chains / Factoring

**Recommendation**: Reframe the scoping question: "Should we build a sub-4B local text-classifier platform and invest in annotation/training infrastructure?" If yes, promote C' and E as the first two applications and commit to a 6-month window to find 3–5 more. If no, kill all five and close the bead. The current independent-candidate factoring obscures the infrastructure commitment.

---

### [P2] FINDING: Microrouter causal-chain reasoning is sound but under-specified

**Location**: docs/brainstorms/2026-05-17-small-local-model-rescoping.md:10–16, 30–34

**Issue**: The brainstorm correctly separates "general routing (which model to call)" from "narrow-task specialization" and notes that the 85%-heuristic-baseline lesson may not transfer. But the causal-chain difference is not made explicit. Routing is a *permutation problem* (you have N models, pick the right one for each query); specialization is a *classification problem* (does this input belong to my narrow task?). These have different training regimes (routing needs balanced examples of all task types; specialists need domain-specific ground truth), different failure modes (a router that always picks one model is clearly broken; a specialist that rejects 99% of inputs might be correct), and different measurement strategies (router accuracy is global; specialist precision/recall are task-specific).

**Lens**: Causal chains / Systems dynamics

**Recommendation**: Codify this distinction in a short "system shapes" addendum. Explicitly state: "Routing systems generalize across distributions; specialization systems optimize for one. Revival proposals for general-purpose learned components (like microrouter or Explore-as-a-router) will be rejected unless they address the pace-layer mismatch [see Lens 4] and re-measure against domain-specific ground truth, not aggregate metrics." This prevents future advocates from conflating the two.

---

### [P1] FINDING: Pace-layer mismatch between C' and E is not surfaced

**Location**: docs/brainstorms/2026-05-17-small-local-model-rescoping.md:105–107

**Issue**: C' (duplicate detection) and E (dispatch pre-filter) are grouped as "PROMOTE" but have radically different operational cadences. C' can retrain quarterly (bead corpus changes slowly); E needs online or weekly retraining (flux-drive dispatch outcomes change with every run, and concept drift is fast). The brainstorm does not discuss this. Quarterly retraining is a manual-annotation task; weekly retraining requires automation. The systems-operations costs are 3–4 orders of magnitude apart.

**Lens**: Pace layers / Systems dynamics

**Recommendation**: Phase-1 measurement for both should include a "retraining schedule" specification: How often must the model retrain? Who runs the retraining job? How will concept drift be detected and trigger emergency retraining? C' and E should not be treated as the same initiative; they may require different architectural choices (offline vs online learning, manual vs automated annotation, quarterly vs continuous integration).

---

### [P1] FINDING: Cross-domain frames entirely absent

**Location**: docs/brainstorms/2026-05-17-small-local-model-rescoping.md (throughout)

**Issue**: User explicitly requested "information retrieval, recommender systems, operations research, control theory, even biological-systems lenses for resource-allocation analogies." The brainstorm uses only ML-feasibility frames (corpus size, ground-truth quality, baseline strength) and does not import external perspectives that might reframe the candidates or suggest hidden risks.

**Lens**: Cross-domain reasoning

**Recommendation**: Before Phase-1 measurement:
- **IR frame**: Duplicate detection is NDCG@k problem — measure success by ranking quality (top-5 duplicates correct?) not binary classification. This reframes the ground-truth question: a bead with 10 similar beads may have 3 "true" duplicates and 7 "related" ones; IR thinks in ranking, not binary classification.
- **Recommender-systems frame**: Dispatch outcomes (agents that fire substantive findings) are implicit feedback. Current ground truth is explicit (Interspect has `finding_count`). Implicit feedback is biased toward what we tried. Consider: what agents did we *not* dispatch because the keyword triage was permissive, and what would they have found? This is the cold-start problem in recommender systems.
- **Operations-research frame**: Dispatch scheduler is a queue-discipline problem. The pre-filter classifier is a admission-control policy. Traditional OR asks: should the server (LLM) process job X, or queue it? Apply bandit algorithms (Thompson sampling, UCB) instead of a fixed threshold.
- **Control-theory frame**: Recall floor (99%) is a set-point. Concept drift is a disturbance. Design a control loop: monitor recall in a held-out test set, adjust threshold dynamically using PID (proportional-integral-derivative) instead of static retraining.
- **Biological-systems frame**: Immune-system tolerance: the classifier should "learn to ignore" novel queries that look dangerous but are safe (false alarms). Apoptosis: stale classifiers should retire when drift exceeds threshold. Allostasis: shift the set-point when operational conditions change.

---

### [P3] FINDING: B (Explore resurrection) dependency is correctly flagged but not risk-modeled

**Location**: docs/brainstorms/2026-05-17-small-local-model-rescoping.md:50–59

**Issue**: The brainstorm correctly defers B pending Sylveste-9ve diagnosis (line 117). But does not explore the risk: if the cause is workflow drift (users switched to direct grep/Read), making Explore cheaper will not bring it back. Cheaper cost on a task users no longer want is a type of waste. The brainstorm mentions this implicitly ("cost or workflow shift?") but doesn't commit to a diagnosis protocol.

**Lens**: Causal chains / Unintended consequences

**Recommendation**: Sylveste-9ve should measure not just "why did Explore stop firing" but "what would users need from Explore to adopt it again?" (e.g., 10ms latency, structured output format, integration with grep results). Cost reduction alone is unlikely to move the needle if the workflow has changed.

---

## Cross-domain frames (the user explicitly asked)

- **Information Retrieval**: Duplicate detection is a ranking problem (NDCG@k), not binary classification. Success metric: "top-5 suggested duplicates include all true duplicates." Ground truth is the bead-closure history, but IR assumes ranking relevance is a spectrum (1–5 stars) not binary.

- **Recommender Systems**: Dispatch outcomes are implicit feedback biased by what we tried. Agent A's findings are observable only if we dispatched A. An agent we filtered out leaves no trace. This is the cold-start problem. Solution: stratified random sampling (dispatch 5–10% of filtered agents) to estimate recall of the unobserved cohort.

- **Operations Research**: Dispatch pre-filter is a queue-admission problem. Traditional OR applies bandit algorithms (Thompson sampling, UCB) to decide "admit or defer this job?" Use these instead of a fixed threshold, and adapt the threshold online as feedback arrives.

- **Control Theory**: Recall floor (99%) is a set-point; concept drift is a disturbance; classifier threshold is the control input. Design a feedback loop: monitor recall in a held-out test set, use PID to adjust threshold dynamically. Don't retrain; adapt the threshold online to track the set-point as drift occurs.

- **Biological Systems**: Immune tolerance (learn to ignore novel queries that are safe, not attacks), apoptosis (retire stale classifiers when drift exceeds threshold), and allostasis (shift the set-point when operational conditions change). These suggest monitoring mechanisms (novelty detection, drift detection) before retraining.

---

## Strongest systems-level reframe

**The real scoping question is not "which 5 candidates should we measure?" but "should we build a cheap-local-text-classifier platform infrastructure?"**

Once you commit to the infrastructure, C' and E become low-cost applications, and the marginal cost of discovering and shipping a third and fourth candidate drops to near-zero. Conversely, if you decide not to build it, all five candidates fail regardless of their individual merits.

The current candidate-by-candidate factoring obscures this infrastructure decision. Recommend reframing Sylveste-s10 as a two-phase bead:

1. **Phase A (Scoping)**: Measure C' (duplicate detection) as the *minimal* application of cheap-local-classifier infrastructure. If it shows promise (>80% precision/recall at threshold, operational cost <$10/month, users find it helpful), escalate to Phase B.

2. **Phase B (Infrastructure commitment)**: Build the platform, commit to annotation/training workflow, and seed it with C' and E as the first two applications. Commit to a 6-month window to find 3–5 more use cases (measure impact on dispatch latency, user cognitive load, code quality).

If Phase A shows no signal, the infrastructure investment is not justified, and you close the entire epic. If Phase A shows strong signal, you have a clear path to Phase B and beyond.

This reframing also surfaces the systems-level risk: **once the infrastructure exists, there is organizational inertia to use it, even for weak candidates**. Guard against this by pre-committing to a return-on-investment threshold for Phase B escalation (e.g., "infrastructure is only justified if Phase A + E together save >5 hours/week of human time or >$100/month in cloud costs").
