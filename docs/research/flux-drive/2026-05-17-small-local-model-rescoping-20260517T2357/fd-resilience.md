---
title: "Resilience Review: Small-Local-Model Rescoping"
type: flux-drive/resilience-review
date: 2026-05-17T23:57Z
target: docs/brainstorms/2026-05-17-small-local-model-rescoping.md
---

# Resilience Review — Small-Local-Model Rescoping

## Summary

This brainstorm applies appropriately strict kill-rules to 5 candidates but promotes 2 (C' and E) to Phase-1 measurement without addressing resource contention, antifragility attribution, or graceful degradation. C' (embedding-based duplicate detection) is well-scoped and has clean ground truth, but E (flux-review pre-filter) operates near the diminishing-returns threshold where 99% recall at 30% suppression may prove unachievable at sub-10B scale. The proposal lacks mid-experiment trip-wires and fallback paths, creating risk of wasted measurement effort during a calendar-constrained period (V4 spike EOD 2026-05-19). Staging is present but fragile — small changes to hypothesis or corpus size could invalidate Phase-1 conclusions before Phase-2 even begins.

## Findings

### [P1] FINDING: Resource contention with V4 spike and flash-moe unquantified
**Location**: docs/brainstorms/2026-05-17-small-local-model-rescoping.md:18, 113–116
**Resilience lens**: Resource competition & antifragility
**Issue**: The brainstorm states C' should run "sub-4B so it can run alongside large-MoE without VRAM contention," but does not cite actual VRAM budget during flash-moe peak load (Qwen 35B–122B + concurrent k8c/0gi.2.7 workloads). The M5 Max is simultaneously running:
  - Qwen 35B+ in flash-moe experiments (Sylveste-2ss, Sylveste-bov)
  - DeepSeek V4 spike on RunPod (Sylveste-0gi.2.7, calendar kill EOD 2026-05-19)
  - Potential k8c Qwen 35B inference (Sylveste-k8c)

The claim "ideally sub-4B" is not validated against observed peak memory pressure. If Phase-1 for C' or E requires 6–12 hours of active GPU use, it will compete with the V4 spike's final days.

**Recommendation**: Measure flash-moe's current VRAM footprint (peak and sustained) and compute the minimum VRAM headroom needed for C'/E Phase-1. If headroom < 8GB, either defer Phase-1 to post-V4-close or run C'/E Phase-1 on CPU (BGE-small fine-tuning or logistic-regression training is feasible on CPU, though slow). Document the resource-allocation decision explicitly in the bead.

---

### [P1] FINDING: Phase-1 attribution paths missing — measurement can only return yes/no
**Location**: docs/brainstorms/2026-05-17-small-local-model-rescoping.md:113–116
**Resilience lens**: Antifragility
**Issue**: The brainstorm proposes:
  - C': "precision/recall against the existing closed-as-duplicate set"
  - E: "measure recall at the threshold where 30% of dispatches are filtered. Kill if recall < 95%"

Both designs measure a single metric (precision/recall or recall), with a kill-threshold, but neither articulates *why* failure would occur, making the measurement brittle:
  - If C' precision drops to 55%, is it (a) the corpus is too noisy, (b) embeddings don't capture "bead duplication" semantics, (c) ground-truth labeling was inconsistent, or (d) the threshold was wrong?
  - If E recall drops to 90%, is it (a) agent descriptions are too generic, (b) the 30% filter target was too aggressive, (c) Interspect outcomes are mislabeled, or (d) TF-IDF + embeddings can't distinguish finding-bearing docs?

Without attribution, a failed Phase-1 teaches nothing, and the user cannot debug or iterate — the project just closes MOOT, and the question remains unanswered.

**Recommendation**: For each candidate, add an **attribution checklist** to the Phase-1 design:
  - C': Validate 10 random closed-dup pairs by hand; check BGE-small zero-shot cosine similarity on those pairs. Measure label-consistency (how often do two beads labeled "closed-as-dup" actually have confusable titles?). Measure threshold sensitivity (how much does precision drop per 0.05 cosine-similarity threshold shift?).
  - E: Compute inter-annotator agreement on 20 random dispatch outcomes (is "returned findings" unambiguous?). Measure agent-description entropy (how many agents have identical descriptions, which would be hard for a classifier to distinguish?). Measure document excerpt quality (are the excerpts representative of actual agent match likelihood?).

---

### [P2] FINDING: Smallest viable experiment design is implicit, not explicit
**Location**: docs/brainstorms/2026-05-17-small-local-model-rescoping.md:113–116
**Resilience lens**: Creative constraints
**Issue**: The brainstorm proposes Phase-1 experiments but does not articulate the *minimum* viable scope:
  - C': "precision/recall against the existing closed-as-duplicate set" — How many pairs? The brainstorm's open question 124 suggests "50 closed-as-duplicate pairs + 50 unrelated pairs is small." But 100 pairs on a cosine-similarity threshold is a 2–3 hour experiment (load corpus, embed, compute threshold, evaluate). No justification for why 100 vs 200 vs 500.
  - E: "train a tiny classifier (could even be logistic regression on TF-IDF + agent embedding)" — How many dispatches? How many features? TF-IDF on agent description + document excerpt is well-defined, but the experiment design is vague ("tiny classifier").

Vague scope + calendar pressure (V4 spike close EOD 2026-05-19) + competing VRAM = high likelihood Phase-1 balloons from "6 hours" to "let's just fine-tune to be safe" = resource overrun.

**Recommendation**: Specify minimum viable Phase-1 for each:
  - **C' MVP**: (1) Load closed-bead corpus (one-time, ~5 min). (2) Download BGE-small (cached, ~1 min). (3) Embed 50 random bead pairs (10 closed-dup, 40 random negatives) and compute cosine similarity. (4) Grid-search threshold (0.3–0.8) for max F1. (5) Measure precision/recall on those 50 pairs. Time: ~30 min. Acceptance: If F1 >= 0.75, advance to Phase-2 (embed full corpus, evaluate on held-out set). If F1 < 0.70, close MOOT with attribution checklist completed.
  - **E MVP**: (1) Load 50 random Interspect dispatches with `finding_count` > 0 and 50 with `finding_count` = 0. (2) Compute TF-IDF features on agent description + document excerpt. (3) Train logistic regression. (4) Measure recall at decision thresholds where 20%, 30%, 40% of dispatches are suppressed. Time: ~1 hour. Acceptance: If recall > 99% at any threshold >= 20% suppression, advance. If recall <= 95% at 30% suppression, close MOOT (recall floor is unachievable).

---

### [P2] FINDING: Mid-experiment trip-wires absent — Phase-1 can drift into Phase-2 unaware
**Location**: docs/brainstorms/2026-05-17-small-local-model-rescoping.md:113–116
**Resilience lens**: Staging & sequencing
**Issue**: The brainstorm defines kill-thresholds for *completion* (recall < 95% for E, implied F1 threshold for C') but not *during-experiment* trip-wires that would halt work early:
  - For C': If BGE-small zero-shot on the first 10 pairs scores < 0.4 average cosine similarity (suggesting embeddings don't capture bead semantics), continuing to 50 pairs is wasted time.
  - For E: If the first 20 dispatches show that agent descriptions are near-identical and document excerpts are identical ("all Flux-review agents have the same description"), logistic regression cannot learn to distinguish them — kill before 50.

Without trip-wires, a struggling Phase-1 can silently consume 12 hours while the user thinks it's "in progress" and the V4 spike close approaches.

**Recommendation**: Add explicit mid-experiment trip-wires to each bead:
  - **C' trip-wires**:
    - After embedding 10 pairs: If median cosine similarity < 0.40, stop and debug (embeddings not capturing semantics).
    - After threshold grid-search: If F1 < 0.65 on 50-pair sample, stop (model cannot achieve Phase-2 acceptance threshold even with full corpus).
  - **E trip-wires**:
    - After 20 dispatches: Compute agent-description uniqueness (are > 80% of agent descriptions identical?). If yes, stop (classifier cannot distinguish).
    - After logistic-regression train: If accuracy on training set < 85%, stop (model is not learning, likely mislabeled outcomes).

---

### [P2] FINDING: Graceful degradation and SPOF risk for C' and E not addressed
**Location**: docs/brainstorms/2026-05-17-small-local-model-rescoping.md:113–116
**Resilience lens**: Single-point-of-failure & antifragility
**Issue**: Both C' and E propose local inference (embedding model on M5 Max for C', logistic regression for E). Neither brainstorm articulates what happens if:
  - The model/classifier becomes unavailable (crash, bug, incompatible dependency)
  - The inference latency balloons unexpectedly
  - Corpus/weights become corrupt

For C', the fallback is "use keyword search or manual review" (pre-specialist status quo). For E, it's "dispatch all agents without pre-filtering" (current state). But the brainstorm never states these fallbacks explicitly, and both fallbacks are reasonable — which means the specialist is *adding optionality, not replacing a critical path*. That's a very different risk posture.

**Recommendation**: Document the graceful-degradation path for each:
  - **C'**: If embedding model is unavailable, `bd search "<kw>"` falls back to keyword match (existing behavior). Inference latency budget: < 200ms p50 (stated). If latency > 500ms in production, disable the model and fall back to keyword search. No data loss; purely UX regression (slower duplicate detection).
  - **E**: If classifier is unavailable, dispatch all agents (existing behavior, no cost savings). Inference latency budget: < 200ms p50 (stated). If recall < 99% at any suppression threshold, disable the classifier permanently and accept 80 dispatches/week. Cost savings are ~$5/month (line 93) — below noise level. The real win is latency (line 94: "cutting 30% would visibly speed up flux-drive runs"). If latency improvement < 5s per run, disable.

Then ask: **If the fallback is always acceptable, what's the true acceptance criterion for the specialist?** For C', it's "faster than keyword search + better than hand review." For E, it's "latency improvement > 5s per run, OR recall < 99% is unachievable and we accept 90% recall for 40% suppression." Re-frame Phase-1 around those constraints.

---

### [P2] FINDING: Diminishing-returns curve not inspected — 99% recall at 30% suppression may be Pareto frontier
**Location**: docs/brainstorms/2026-05-17-small-local-model-rescoping.md:85–96
**Resilience lens**: Diminishing returns & creative destruction
**Issue**: For E, the brainstorm proposes "recall floor must be ~99%" (line 95) and measures at "the threshold where 30% of dispatches are filtered" (line 115). But does not check: **Is 99% recall at 30% suppression even achievable?**

The microrouter close hit 89.6% with heuristics (line 12) and was killed because the next 10% would cost "dramatically more than the first 89.6%." The E candidate is similar: 80 dispatches/week with 50% false-positives (agent says "no findings" but findings exist). A 3-rule heuristic ("skip if document is empty", "skip if agent never matches", etc.) might hit 50% suppression at 98% recall. A logistic regression might hit 60% suppression at 97% recall. A 7B specialist fine-tuned end-to-end might hit 65% suppression at 96% recall.

The brainstorm assumes 99% recall is achievable at 30% suppression without measuring the curve first.

**Recommendation**: Before Phase-1 measurement, run a **back-of-envelope diminishing-returns check**:
  - E: Sample 100 dispatch outcomes from Interspect. For each, manually estimate "would a classifier have predicted 'no findings'?" (read the agent description + document excerpt, imagine a human judging "relevance"). Measure baseline: "how many did the human judge as low-relevance?" If > 40%, then 30% suppression at 99% recall is infeasible (the human would be wrong 1/2 the time). If < 15%, then 99% recall is achievable even with poor classifiers, and the experiment is low-value.
  - C': Sample 50 closed-bead pairs. For each, measure: "would cosine-similarity threshold = 0.5 catch this duplicate?" Count true positives at that threshold. If TPs > 45/50, the threshold is strong and fine-tuning likely won't improve much (diminishing returns). If TPs < 20/50, a better embedding model might help.

This ~2-hour effort (baseline sampling) informs Phase-1 scope and kill-thresholds.

---

### [P1] FINDING: Duplicate-detection (C') uses embedding-not-generative escape hatch; re-frame as retrieval problem or acknowledge scope drift
**Location**: docs/brainstorms/2026-05-17-small-local-model-rescoping.md:61–72, open-questions 123
**Resilience lens**: Creative constraints & problem framing
**Issue**: The brainstorm's title is "Small-local-model (sub-10B) rescoping" (line 2, 16: "Is there a narrow task class... where a sub-10B local specialist"). But C' proposes using a 100M-parameter sentence-embedding model (BGE-small, all-MiniLM-L6), explicitly rejecting the generative framing: "This is *not* generative inference — it's a retrieval problem" (line 113). The open question 123 even asks: "If the user's intent was specifically generative SLM, this candidate doesn't count."

This is honest but signals a scope shift: the brainstorm is answering "is there a local specialist task?" by proposing a retrieval model (which is simpler than generative SLMs). That's a valid answer, but it's not answering the original question. It's answering a *different* question: "is there a local-inference task?"

**Recommendation**: Reframe C' explicitly in one of two ways:
  - **Option A: Accept scope drift.** Rename the brainstorm "Local-inference specialist rescoping" (not "sub-10B") and focus on retrieval + small classifiers. C' is then a strong candidate because retrieval models are cheap and clean. The original question ("sub-10B generative SLM") remains open and is deferred or closed MOOT.
  - **Option B: Restore generative constraint.** If the user's intent is specifically "generative SLM for bead tasks," kill C' and keep only E (which is generative: it reads agent+doc and decides yes/no). Re-evaluate candidates A–D with the generative constraint in mind (e.g., "can a 3B generative model fine-tuned on 100 (agent, decision) pairs beat keyword search?").

Choose one and document the decision in the bead.

---

### [P1] FINDING: Kill-rule calibration inherited from microrouter without re-validation
**Location**: docs/brainstorms/2026-05-17-small-local-model-rescoping.md:16, 121–122
**Resilience lens**: Assumption locks & first principles
**Issue**: The brainstorm inherits the kill-rule ">50% probability of >20% improvement" from the microrouter cluster (line 16, implied in line 121: "the microrouter cluster was killed precisely because we didn't apply a strict-enough threshold up front"). But the microrouter cluster was optimizing *general routing across all agent roles* — a very broad task with many edge cases and high variability. C' (bead duplicate detection) and E (flux-review pre-filter) are *narrower* and *more constrained*. The kill-rule may be too strict for narrow tasks.

Specifically:
  - Microrouter was competing against a *strong* heuristic baseline (89.6% agreement, line 12). C' and E are competing against *weak* baselines (keyword search, no pre-filtering). The bar for "20% improvement" should be lower.
  - Microrouter had ~5000 active beads generating ~200 routing decisions/day. C' has ~1000 closed beads (one-time corpus). E has ~80 dispatches/week (low-volume, low-cost service). The cost of failure is lower, so the probability-of-success threshold can be lower.

**Recommendation**: Re-validate the kill-rule for each candidate:
  - **C'**: A 20% improvement in duplicate-detection means: if keyword search (current) catches 6/10 duplicates, the embedding model must catch 7.2/10. That's achievable — embedding models are known to outperform keyword search on semantic similarity. Propose ">40% probability of >15% improvement" (lower threshold for narrow task). Acceptance: If F1 >= 0.78 on Phase-1, advance.
  - **E**: A 20% improvement in dispatch pre-filter means: if current dispatch success rate is 50% (50% false positives, guessing), the classifier must achieve 60% true-negative rate at 99% recall. Phase-1 kill-rule: "If recall < 99% at any suppression threshold >= 20%, close MOOT." This is stricter than the microrouter's ">85% trigger" — re-evaluate whether 99% is necessary or if 97% is acceptable (depends on user tolerance for missed findings).

---

## Smallest-Viable-Experiment Redesign

### C' (bd duplicate detection) MVP

**Experiment design**: 2-hour Phase-1 measurement
1. **Setup** (15 min): Download BGE-small (cached if available). Load closed-bead JSONL (~1000 beads). Filter to beads closed with tag `closed-as-duplicate` (count expected: 50–200).
2. **Sample ground truth** (30 min): Randomly select 15 pairs labeled "closed-as-duplicate" and 35 random negative pairs (unrelated beads). Measure label quality: manually inspect 5 closed-dup pairs — do they actually describe the same problem? If > 3/5 are legitimate duplicates, proceed. Otherwise, document label noise and adjust expectation.
3. **Zero-shot embedding** (30 min): Embed all 50 pairs with BGE-small. Compute cosine similarity for each pair. Grid-search threshold (0.3–0.8) to maximize F1 on the 50-pair sample.
4. **Evaluation** (15 min): Report precision, recall, F1 at optimal threshold. Check Pareto frontier: "What recall is achievable at 95% precision?" and vice versa.

**Acceptance criteria**:
- **ADVANCE to Phase-2**: F1 >= 0.75 on 50-pair sample AND >= 3/5 manual inspection pairs are legitimate duplicates.
- **CLOSE MOOT**: F1 < 0.70 OR label noise > 40% (hard to fix fine-tuning on noisy labels).

**Phase-2** (if advanced): Fine-tune BGE-small or train a lightweight embedding-adapter on full closed-bead corpus; evaluate on held-out set (200 pairs, 50 true-duplicates).

---

### E (flux-review pre-filter) MVP

**Experiment design**: 2–3 hour Phase-1 measurement
1. **Data preparation** (30 min): Query Interspect outcomes (dispatch_id, agent_description, document_excerpt, finding_count). Sample 100 dispatches: 50 with finding_count > 0 (positive class) and 50 with finding_count = 0 (negative class). Spot-check 5 from each class: do the tags match reality? (Read the actual finding or confirm "no findings.")
2. **Feature engineering** (30 min): Compute TF-IDF on agent_description + document_excerpt. Optionally compute agent embedding (using a small pre-trained model, ~100-dim). Concatenate features into a vector for each dispatch.
3. **Logistic regression** (30 min): Train logistic regression on 80 dispatches (train set). Evaluate on 20 held-out dispatches (test set). Measure: recall at suppression thresholds [0.2, 0.3, 0.4]. Compute operating point: at what suppression threshold is recall >= 99%?
4. **Attribution** (15 min): If recall < 99% at 30% suppression, analyze failure modes: "Which negatives were misclassified as positives (false positives)?" Examine agent descriptions (are they too generic?) and document excerpts (are they too similar?).

**Acceptance criteria**:
- **ADVANCE to Phase-2**: Recall >= 99% at suppression >= 20% OR recall >= 97% at suppression >= 30% (if 99% is borderline).
- **CLOSE MOOT**: Recall < 95% at all thresholds >= 20% suppression (recall floor unachievable). Or spot-check reveals 40%+ label noise.

**Phase-2** (if advanced): Train a small transformer or 2-layer LSTM on expanded dataset (500+ dispatches); optimize for recall at fixed suppression target.

---

## Trip-wires the brainstorm should add

### C' (bd duplicate detection)

1. **Zero-shot check (15 min in)**: Compute BGE-small cosine similarity on first 10 pairs. If median < 0.40, stop. Diagnosis: embeddings not capturing bead semantics. Proceed to attribution checklist (measure label quality, check if task is actually solvable).
2. **Label-quality check (45 min in)**: Manually inspect 5 closed-dup pairs. If > 2 are mislabeled or ambiguous, stop. Diagnosis: ground truth is too noisy to learn from. Close MOOT.
3. **F1 floor (105 min in)**: Compute F1 on 50-pair sample. If F1 < 0.65, stop. Diagnosis: embedding model cannot achieve acceptance threshold even at optimal threshold. Phase-2 fine-tuning will not help much (diminishing returns).

### E (flux-review pre-filter)

1. **Label consistency check (30 min in)**: Spot-check 5 positive-class and 5 negative-class samples. Manually verify: did the agent actually return findings? If disagreement > 20%, stop. Diagnosis: ground truth is mislabeled (e.g., `finding_count` is not reliable). Audit Interspect data quality before proceeding.
2. **Feature diversity check (60 min in)**: Compute TF-IDF vocabulary size and agent-embedding entropy. If > 80% of agent descriptions are identical, stop. Diagnosis: classifier cannot distinguish agents; problem is not solvable at this resolution.
3. **Training accuracy floor (105 min in)**: After logistic-regression train, measure training-set accuracy. If < 85%, stop. Diagnosis: model is not learning (likely mislabeled data or insufficient features). Do not proceed to test set.
4. **Recall-at-suppression check (120 min in)**: Measure recall at 20%, 30%, 40% suppression on test set. If recall < 97% at all thresholds >= 20%, stop and document (recall floor too low; specialist not viable at scale).

---

## Graceful-Degradation Paths

### C' (bd duplicate detection) — Fallback Architecture

**Normal path**: User runs `bd search "<kw>"` → embedding model scores results → returns top-N likely duplicates + keyword matches.

**Degradation path**:
- **Model unavailable** (crash, dependency issue): Return keyword-search results only (pre-specialist behavior). User experience: slower duplicate detection, no regression in accuracy.
- **Model slow** (latency > 500ms): Disable model in production; fall back to keyword search. Monitoring: measure p95 embedding-model latency per run. If p95 > 500ms for 3 consecutive weeks, disable.
- **Model output suspicious** (high similarity on unrelated beads): Disable and audit. Ground-truth check: sample 10 high-confidence predictions; manually verify. If > 3 are false positives, disable until model is re-trained.

**Acceptance for Phase-2**: Model must be faster than keyword search (median latency < 150ms vs ~50ms for keyword search) *and* must catch duplicates keyword search misses (manual spot-check: >= 3/10 duplicates are embedding-only, not keyword-matched).

### E (flux-review pre-filter) — Fallback Architecture

**Normal path**: Flux-drive triage → pre-filter classifier → dispatch to agent only if predicted "will return findings."

**Degradation path**:
- **Classifier unavailable** (crash, retrain needed): Dispatch all agents (pre-specialist behavior, current state). Cost: ~$5/month additional dispatch cost (negligible). Latency: +30–120s per flux-drive run (noticeable).
- **Classifier slow** (latency > 200ms): Disable; dispatch all agents. Monitoring: measure p95 classifier latency. If p95 > 200ms, disable.
- **Recall drops below 99%**: Disable permanently or escalate to manual review for edge cases. If recall = 97% at 30% suppression, accept if latency savings (5+ sec per run) justify occasional missed finding (1–3 per 100 runs).

**Acceptance for Phase-2**: Classifier must preserve recall >= 99% at suppression >= 20% *or* latency improvement must be >= 5 sec per run (worth the risk of occasional false negatives). If neither, close MOOT.

