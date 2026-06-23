# Decision-Quality Review — Small-Local-Model Rescoping

## Summary

The brainstorm demonstrates **strong decision discipline and self-awareness**, applying the kill-rule rigorously and correctly downranking most candidates. The ranking table's verdicts are well-supported by evidence within each section. However, three decision-quality gaps emerged: (1) the kill rule calibration may be anchored on the microrouter loss rather than derived from first principles about workload-model fit, (2) the C' embedding candidate escapes the stated framing (small-local-model → retrieval) without explicitly acknowledging this reframe, and (3) Phase-1 measurement design for both C' and E leaves success criteria ambiguous, risking measurement failures that look like inconclusive results. The recommendations (C' + E measurement beads) are sound, but the reasoning path has invisible turns.

**Verdict:** Act on C' and E measurement recommendations as-written; clarify the reframe from generative-to-retrieval before opening C' bead; pre-commit explicit kill thresholds for both C' and E Phase-1 before measurement starts.

---

## Findings

### [P1] FINDING: Kill-rule calibration anchored on microrouter loss, not workload-model fundamentals

**Location**: `docs/brainstorms/2026-05-17-small-local-model-rescoping.md`, lines 1–17 (Frame), lines 98–107 (Ranking)

**Issue**: The kill rule ("If no candidate has both (a) measurable current pain and (b) >50% probability of >20% improvement") is presented as a constraint on candidates C, D, A; it also governs the verdicts in the ranking table. However, the rule appears post-hoc rationalized from the microrouter close (lines 10–12: "above the 85% trigger") rather than independently derived from decision theory or the task structure. The open question on line 121 flags this: "the microrouter cluster was killed precisely because we didn't apply a strict-enough threshold up front." This suggests the brainstorm may have **overcorrected** — applying stricter thresholds to future work to punish the past decision.

**Decision-quality lens**: Sunk cost fallacy + anchoring bias. The user is anchored on the microrouter failure ($time spent, learning lost) and may be raising kill-rule thresholds to avoid repeating that loss, rather than setting thresholds based on the current decision context (do C' and E have measurable pain and upside independent of what happened to .19?).

**Recommendation**: Before committing to the ">50% probability of >20% improvement" framing, answer: What is the baseline kill rule for *any* speculative model investment in this org? Is it 50%/20%, or is it context-dependent (e.g., 30%/10% for low-cost experiments with reversible failure modes)? If the rule is truly context-independent, justify it; if it's context-dependent, make the dependency explicit so future rescoping beads can calibrate their own thresholds. For C' and E specifically, state the actual thresholds pre-Phase-1.

---

### [P1] FINDING: C' embedding-model recommendation sidesteps the stated problem frame without acknowledgment

**Location**: `docs/brainstorms/2026-05-17-small-local-model-rescoping.md`, lines 20–34 (What it might unlock), lines 61–72 (Candidate C. bd P-tier/type classification), lines 105–113 (Recommendation)

**Issue**: The problem frame (lines 16–18) asks: "Is there a narrow task class in the Sylveste workload where a **sub-10B local specialist (fine-tuned or zero-shot)** would beat the current heuristic + cloud-tier routing?" The phrase "specialist" and "(fine-tuned or zero-shot)" implies generative inference — training or prompting a language/task model.

Candidate C (bd P-tier/type) fails on this frame because "Ground truth is noisy" and "specialist value: marginal" (lines 69–70). The brainstorm then **redefines the problem** in line 71: "Duplicate detection via embedding similarity is the **strongest candidate within this bucket** — embeddings can be 100M params, ground truth is clean."

This is **not a sub-10B language model**; it's a retrieval embedding model (100M params, vector similarity). The reframe is honest in the C' section, but the **recommendation section (lines 110–113) treats C' as a measurement bead without re-stating that the problem has shifted from "generative specialist" to "retrieval specialist."** The next reviewer or implementer will see "C'. bd duplicate-detection embedding model" and must infer that embedding-models don't count as language models.

**Decision-quality lens**: Problem reframing without explicit acknowledgment; implicit redefinition of success criteria.

**Recommendation**: In the Recommendation section, explicitly re-state: "C' is a **retrieval problem, not a generative SLM problem**. The original frame asked for fine-tuned or zero-shot generative models; C' sidesteps the frame by asking whether embeddings solve a sub-problem better. This is a valid reframe (duplicates *are* a real pain), but Phase-1 measurement should test it as a new problem, not as an answer to the original 'sub-10B generative' question." This clarity prevents Sylveste-s10's child bead (C' measurement) from discovering mid-stream that it's solving the wrong problem.

---

### [P2] FINDING: Phase-1 measurement design for C' lacks explicit failure mode and kill threshold

**Location**: `docs/brainstorms/2026-05-17-small-local-model-rescoping.md`, lines 113–114 (Recommendation item 1), lines 124–125 (Open question 4)

**Issue**: The C' measurement plan says: "Phase-1 measurement: precision/recall against the existing closed-as-duplicate set." The open question (line 124) acknowledges the risk: "closed-as-dup pairs themselves may be undersampled (many duplicates may have been silently merged without the 'duplicate' tag)."

However, **no kill threshold is pre-committed**. The recommendation doesn't state: "If embedding model achieves <90% recall on the closed-as-duplicate test set, close the bead MOOT." Without this, the measurement can return a result (e.g., "85% precision, 75% recall") that feels inconclusive, forcing a mid-bead decision about whether that's good enough. This violates the principle that Phase-1 measurements must have pre-committed kill criteria.

Additionally, the acknowledged undersampling problem (line 124) suggests the test set may be systematically biased *toward* false negatives (missing real duplicates). A model that scores well on the test set might perform worse in production, where the unlabeled-duplicate tail is larger. No mitigation strategy is proposed.

**Decision-quality lens**: Premature commitment without guard rails. The measurement can produce inconclusive results that feel like learning, rather than clear pass/fail signals.

**Recommendation**: Before opening the C' bead, pre-commit: (a) Minimum recall threshold (e.g., 90% on closed-as-duplicate, 70% on a hand-labeled held-out set covering the miss tail); (b) maximum FP rate on a heuristic negative set (e.g., beads with similar keywords but clearly non-duplicates); (c) a decision rule ("if recall <90% AND precision >95%, defer and investigate data quality; if recall >90%, proceed to Phase-2 integration test"). This prevents the bead from drifting into exploratory measurement.

---

### [P2] FINDING: Phase-1 measurement for E (flux-review pre-filter) conflates latency value with recall risk

**Location**: `docs/brainstorms/2026-05-17-small-local-model-rescoping.md`, lines 85–96 (Candidate E), lines 107, 115–116 (Ranking / Recommendation)

**Issue**: The E candidate is ranked "maybe / maybe (latency-driven)" on "specialist beats heuristic / specialist beats prompt-eng" (lines 107). The rationale (lines 88–96) correctly identifies that cost savings are negligible (~$5/month, line 93) but latency wins are real (30–120s per dispatch, line 94). The recommendation (line 115) says: "measure recall at the threshold where 30% of dispatches are filtered. Kill if recall < 95% at that threshold."

The problem: **Latency wins are relative to the current dispatch process, not to absolute wall-time budget.** If cutting 30% of dispatches saves 12–36s per flux-drive run, but the run already takes 5 minutes, the latency delta is 4–12% improvement. The kill rule (recall <95%) is about false-negative risk, but the motivation (latency) is weak compared to the risk. This creates a mismatch: we're filtering 30% of work to save ~10% latency, which seems like acceptable overhead until the rare false negative surfaces.

Additionally, line 95 states the risk plainly: "Pre-filter that hides a real finding is worse than redundant dispatches." This is a **hard constraint** (quality > speed), but it's not reflected in the kill rule. The recommendation should either state "kill if recall <98% or false-negative rate >1%," or reconsider whether E is worth the risk at all.

**Decision-quality lens**: Unclear value hierarchy. The latency benefit doesn't justify the recall risk, unless the doc explicitly says "we're willing to miss 1 in 100 relevant findings to save 30s per run." It doesn't.

**Recommendation**: Clarify the recall floor for E before Phase-1 measurement. Either: (a) Commit to a higher recall threshold (e.g., 99%) that reflects the stated risk-aversion (line 95); (b) drop E and reinvest in C' or future candidates; or (c) explicitly commit to a recall-quality trade-off with specific numbers ("we accept missing 1 finding per 100 dispatch batches to save X hours/month"). The Phase-1 measurement design should follow from this clarification, not precede it.

---

### [P2] FINDING: B (Explore dispatch) dependency on Sylveste-9ve creates a hidden critical path

**Location**: `docs/brainstorms/2026-05-17-small-local-model-rescoping.md`, lines 50–59 (Candidate B), lines 59, 117 (Recommendation)

**Issue**: The brainstorm says B "must close [Sylveste-9ve] first" (line 59) because "we don't yet know whether the cause is cost — it might be workflow drift or instrumentation" (line 57). The Recommendation (line 117) says: "If Explore dormancy is a cost problem, escalate B to a measurement bead then. Otherwise it stays dormant."

This creates a **hidden critical path**: Sylveste-s10 depends on Sylveste-9ve (30-min diagnosis per the handoff, line 20 of latest.md), and only *if* 9ve concludes "cost problem," does B become a candidate. The brainstorm correctly identifies the dependency but doesn't surface it as a blocking decision for the user. The implication is: "don't open a measurement bead for B until 9ve is done."

However, the handoff (latest.md, line 20) lists 9ve as fallback work if V4 Day-3 stalls — it's not a primary task. This means B measurement is implicitly deferring to 9ve's outcome, which could be months away. The brainstorm doesn't ask: "Is Sylveste-s10 willing to wait on 9ve? Or should we open B's measurement bead speculatively and pivot if 9ve returns 'workflow drift'?"

**Decision-quality lens**: Hidden critical path / option-value loss. The brainstorm makes a reasonable dependency call but doesn't weigh the cost of delaying B.

**Recommendation**: Explicitly state in Sylveste-s10 acceptance criteria: "Open C' and E measurement beads immediately. For B: explicitly tie the decision to Sylveste-9ve's verdict; if 9ve is not expected to close within 2 weeks, open a *speculative* B measurement bead that assumes cost is the blocker, and pivot if 9ve contradicts." This prevents B from drifting into indefinite deferral.

---

## Open questions the brainstorm got right

1. **Line 121: "Is the kill rule too strict?"** — Directly acknowledges sunk-cost risk. This self-awareness is strong.
2. **Line 122: "Am I missing workload candidates?"** — Recognizes the candidate pool is constrained by session memory. Suggests using interstat/metrics.db as a source of truth. Good methodological honesty.
3. **Line 123–124: "Is the embedding-not-generative escape hatch (C') honest?"** — Flags the reframe explicitly in open questions. The brainstorm knows it sidesteps the original problem and asks for external validation.
4. **Line 124–125: "Phase-1 measurement design."** — Acknowledges the test-set bias (undersampling of unlabeled duplicates) and the small test set size. Shows rigor.

---

## Decision traps the brainstorm avoided

1. **Sunk-cost cling**: The brainstorm did NOT say "we spent time on microrouter, so let's find a similar bet to validate the effort." It killed A (lens triage) on principle, not hope.
2. **False confidence in "narrow task class"**: The brainstorm didn't assume that any sub-10B model would win; it systematically checked whether ground truth, baseline competition, and workload size justified the bet.
3. **False dichotomy (heuristic vs specialist)**: The brainstorm correctly framed specialists as competing against heuristics, cloud tiers, AND prompt engineering. It didn't optimize for one baseline.
4. **Measuring outputs instead of inputs**: The brainstorm correctly identified (line 57 on B) that diagnosis must precede design. It didn't propose a solution to B's unknown cause.

---

## Counter-recommendations

**No changes to the C' + E recommendations.** Both candidates are well-supported and worth Phase-1 measurement. However:

1. **For C' (embedding model):** Pre-commit kill thresholds before opening the bead. Recommend: ≥90% recall on closed-as-duplicate, ≥95% precision on non-duplicates, <5% FP rate on heuristic negative set. If any threshold fails, close MOOT immediately (don't iterate the embedding model; declare the problem unsolved).

2. **For E (flux-review pre-filter):** Decide whether latency savings justify recall risk. Current risk statement (line 95) is too strong for the motivation. Either commit to ≥99% recall or drop E. If committed, use the same "kill immediately on metric failure" approach as C'.

3. **For B (Explore dispatch):** Explicitly surface the dependency on Sylveste-9ve in the Sylveste-s10 acceptance criteria. If 9ve isn't expected to close within 2 weeks, consider opening a speculative B bead to parallelize learning (assume cost, measure cost directly on Explore dispatch logs).

4. **Add a future spike**: Candidate F (unmentioned): leverage the large-MoE baseline (Qwen 35B/122B in concurrent VRAM). Could a mixture-of-expert gating mechanism run locally, using the large-MoE as a reference implementation? This sidesteps sub-10B constraints if gating itself is the win. (Not actionable now, but worth adding to the backlog for the next learned-routing scoping bead.)
