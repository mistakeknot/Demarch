# fd-perception findings — microrouter architecture decision brainstorm

## P1 findings

### P1-A: Bead-clean-close is a proxy with unexamined failure modes (Map vs Territory)

The β-anchor definition rests on bead-clean-close (no defect/regression bead in N=4 sprints) as the ground-truth signal. The document treats this as "real outcomes: independent of any judge" but confuses bead state (closed without certain children filed) for territory (actual code shipped useful to users). The failure modes:

1. **Deferred closure**: A bead can be closed with label `deferred` or `blocked` by policy, encoding decision not to ship rather than successful delivery. The pass@1 metric ignores the label — only the presence/absence of `defect`/`regression` children counts.
2. **Absence of evidence vs. evidence of absence**: A bead closed clean may simply mean "no one filed a regression bead yet," not "this code has no defects." The 4-sprint window is a detection delay, not a ground truth window. Slow-burn regressions found in month 5 are invisible to training.
3. **Ascertainment bias**: High-confidence work (e.g., refactors with extensive rollback runbooks, safety reviews) is more likely to produce defect beads when issues arise because reviewers actively file them. Exploratory work (quick agents, dogfood features) is less likely to have defect beads filed even if broken, because no one is yet monitoring them. The metric thus biases training data toward conservative tasks.

**Impact**: The microrouter trained on bead-clean-close data will overfit to the subset of work that is actively monitored for regressions. Long-tail agents (mentioned in 2026-05-05 as the actual source of latency/privacy wins) are generated one-shot and rarely have regression beads filed against them. The pass@1 anchor inherits this bias invisibly.

---

### P1-B: The "label noise > 30%" trigger is a placeholder without measurement protocol (Information Quality & Signal/Noise)

Section "Why γ is preserved (not deleted)" cites the contingency trigger: **"the first sprint of pass@1 data shows label noise above some threshold (TBD; ~30% pre-registered as a placeholder)."**

The document does not define:
- How label noise is measured (disagreement rate between what CI says and what bead closure says? Variance in regression detection delay?)
- Why 30% is defensible (connection to LoRA training stability? Drawn from the 1K–2K empirical floor cited in 2026-05-04?)
- Who decides when the threshold is crossed (automated detection, manual review, some combination?)

**Open question 4** in the 2026-05-06 doc defers this to strategy phase, but the deferral language ("pre-registered as a placeholder") frames it as a minor detail. In practice, if label noise > 30% is discovered post-`.19.9` and the threshold is never pinned, the trigger is unactionable. The decision to escalate to γ becomes a judgment call, not a gate, and the deferral loses its empirical hook.

**Impact**: The contingency trigger is defined just vaguely enough that it can be invoked post-hoc to justify γ-fallback OR rationalized away as "within acceptable range." This gives the deferral decision cover without falsifiability.

---

### P1-C: Four-sprint accumulation vs. long-tail agent population (Signal & Survivor Bias)

The brainstorm proposes N=4 sprints as the volume threshold before β telemetry "stabilises." The 2026-05-04 document cites empirical floors: ~1K–2K examples per class for LoRA stability.

But the actual agent population (per 2026-05-05 Finding 3) is bimodal: **357 agents, 215 are stubs, 0 are "proven" (≥3 uses + >150 lines), 7 stable agents are mostly Sonnet-floored.**

Implications for 4-sprint data accumulation:
1. **Class imbalance**: If routing decisions are (agent, complexity_tier, model_tier) then the 7 stable agents will dominate training volume. The generated long-tail agents (one-shots, where latency/privacy wins matter per the motivation) will have 1–10 examples each across 4 sprints.
2. **Survivor bias in closed beads**: Bead closure itself is selection — tasks that complete are more likely to have clean verdicts than abandoned or indefinite work. The 4-sprint window captures "work that reached closure," biasing against stuck tasks (where routing errors have highest cost).
3. **Temporal correlation**: Pass@1 data from 4 consecutive sprints is likely to share season, mode of work (e.g., "all flux-review depth"), and operator (the user). Training on such correlated data will overfit to current conditions and generalize poorly if the workload shifts.

**Impact**: The claim that 4 sprints gives "stable training" may be optimistic for the long-tail agents that motivated the epic. The router may learn stable patterns on the stable-7 (which don't need routing) while remaining brittle on the long tail.

---

### P1-D: Calibration freeze cut date is now in the past (Temporal Blind Spot)

The 2026-05-04 document recommended: **"Calibration freeze cut date (TBD in `.19.1`, recommended: 2026-05-15)"**

The current document (2026-05-06) defers `.19.9` + 4 sprints to ~2026-06-30 as the soft deadline for *deciding* on β vs γ. But:

1. If the freeze was meant to occur *before* telemetry accumulation begins, it should happen ~2026-05-15 (now ~9 days away).
2. If the freeze is deferred until 2026-06-30, any pass@1 outcomes generated between 2026-05-15 and the actual snapshot date will leak into the training data via the live `routing-calibration.json` (contrary to the SHA-pinning intent from Change #2 of 2026-05-04).
3. The document does not clarify whether "4 sprints of pass@1 accumulation" starts *after* the freeze is taken, or whether the freeze happens partway through accumulation.

**Impact**: The snapshot + hash-check design from 2026-05-04 becomes ambiguous under the deferral. If calibration data leaks post-snapshot into live routing and then downstream passes feed back into bead closures, the independence assumption ("outcomes are independent of any judge") erodes.

---

## P2 findings

### P2-A: Source diversity is narrow — evidence rests on a single perception (Sensemaking)

The decision to defer to β (over γ-now or α-now) rests on three arguments:
1. "β is the only architecture where ground-truth signal is independent of the judge population" (section "For β-after-telemetry")
2. "Months of waiting for telemetry is a deliberate choice to avoid building on circular calibration" (same section)
3. Deflection of γ-now and α-now by citing unmeasured headroom (section "Why defer to β instead")

All three rest on a single mental model: **that independent signal is intrinsically stronger than judge agreement**. This model is not wrong, but the document does not acknowledge alternatives:

- **Judge-ensemble approach (γ) breaks circularity via diversity, not independence.** Four disjoint families agreeing is a different kind of strength than one ground-truth source. The argument against γ-now (section "Against γ-now") is that we don't know the heuristic's headroom — but that argument equally applies to β: we don't know if bead-close-as-anchor will produce high-quality training data until it's measured.
- **The "unmeasured headroom" critique applies equally to β.** The document says D2 (heuristic-baseline measurement) is "a worthwhile sanity check" that "should be a separate bead" (section "What this does NOT do"). But if D2 is worth doing at all, deferring β until after D2 and β-telemetry accumulate adds a sequential wait. Doing D2 + γ in parallel might be faster.

**Impact**: The decision appears to follow from a principle (independent signals > ensemble signals) rather than from empirical comparison. The document does not engage with the possibility that γ's diversity advantage and quick timeline might outweigh β's independence advantage.

---

### P2-B: "Heuristic within ~5% of oracle" is a judgment call, not a derived number (Goodhart's Law & Narrative Fallacy)

The 2026-05-05 brainstorm (D2) proposes: **"Heuristic within ~5% of oracle on routing-eligible traffic → kill the epic."** It then says: **"The ~5% threshold for kill-vs-proceed is a judgement call, not a derived number."**

The 2026-05-06 document incorporates this logic into the deferral path: if D2 "says headroom < 5%, the entire `.19` epic should close" (section "What this does NOT do").

But:
1. What does "5% of oracle" mean operationally? 5% of the oracle's latency wins? 5% absolute improvement? 5% relative to the heuristic's current score?
2. Who observes whether the threshold is met — automated comparison, human review, or consensus?
3. What constitutes "heuristic within ~5%"—point estimate, confidence interval, per-tier disaggregation?

**Impact**: The deferral decision includes an auto-fail gate (kill if D2 shows <5% headroom) that is stated but not operationalized. This creates a loop: the decision depends on D2, D2 uses a threshold that is acknowledged to be a judgment call, so the decision ultimately rests on a judgment call made at an unknown future date. The deferral is not "wait for telemetry," it's "wait for a judgment that hasn't been made yet."

---

### P2-C: Sprint reflection verdicts as a data source are not validated (Information Quality)

The β-anchor definition (section "Architecture: β primary, α fallback") lists three sources for pass@1:
1. Bead-history verdicts (~498 closed beads)
2. Session JSONL outcomes (10K+ sessions indexed via cass)
3. **Sprint reflection artifacts** (`docs/reflections/*`)

The first two are quantifiable. The third — "sprint reflection artifacts for high-fidelity post-hoc judgments" — is qualitative and authored by the same person making routing decisions. No validation is proposed for:
- Whether reflection verdicts are consistent (same event judged the same way across multiple reflections)
- Whether they differ from bead-closure verdicts (and if so, which is the ground truth)
- Whether reflection bias (e.g., rationalizing in retrospect) affects the pass@1 labels

**Impact**: The anchoring source is partially soft data (reflections) that is harder to audit and may be endogenous to the decision-maker.

---

## P3 findings

### P3-A: Re-entry cost claim needs qualification (Temporal Reasoning)

Section "Re-entry cost (if `.19.3` LoRA had already run)" argues deferral is zero-cost **today** because no downstream work has started. But re-entry cost is not quite zero even in the current state:

1. **Opportunity cost**: Months of calendar time spent waiting for telemetry while the user and project capital are allocated to other work. If the routing epic is motivation for other priorities (e.g., "we need microrouter to unblock privacy work on `.19.6`"), the deferral delays those dependencies.
2. **Scope drift**: Changes in project context (new agents, new complexity tiers, new routing constraints) may shift the problem between now and 2026-06-30. Re-entry will require re-measuring D2 on the updated heuristic.
3. **Bead accumulation**: Four sprints of bead closures will accumulate in `.19.2` scope. At re-entry, the scope of work to label and build corpus is larger, not constant.

**Note**: None of these invalidate the deferral decision, but they weaken the "zero re-entry cost" framing. The cost is zero in implementation, non-zero in project calendar and scope.

---

### P3-B: Long-tail agent routing motivation is deferred, not resolved (Temporal Blind Spot)

The 2026-05-05 Finding 3 identifies that latency/privacy wins come disproportionately from the long-tail agents (one-shots), not the stable-7. The deferral plan defers β (and γ-fallback) architecture work while waiting for telemetry.

But the fundamental mismatch — that the stable-7 dominate training volume while the long-tail drives the value proposition — is not resolved by the deferral. At 2026-06-30, when the β-decision revisit happens, the same bimodal population will exist. The β architecture (trained on bead-close outcomes) will inherit the same long-tail brittleness unless the measurement protocol (in `.19.2`) explicitly upweights or conditions on long-tail coverage.

**Impact**: Deferral does not solve the core tension; it only postpones the moment when this tension becomes visible in `.19.2` dataset coverage analysis.

---

## Verdict

**NEEDS_ATTENTION** — The decision to defer to β is coherent in spirit (ground-truth signal > judge agreement) but rests on three unexamined blind spots: (1) bead-clean-close as a proxy confuses map (bead state) with territory (actual code utility), inheriting ascertainment bias from regression-monitoring practices; (2) the contingency trigger (label noise > 30%) is defined as a placeholder without measurement protocol, making it unfalsifiable; (3) the deferral defers not just data accumulation but also judgment calls (D2 headroom threshold) that should be resolved earlier, compressing a two-dimensional decision space (architecture choice × telemetry maturity) into a sequential path that may not be optimal for the long-tail motivation.

The document should be committed as-is (it is the decision record), but the strategy phase work for `.19.9` should frontload: (a) explicit definition of label-noise measurement and threshold with acceptance criteria; (b) D2 completion or deferral decision with clear re-entry date if deferred; (c) long-tail agent instrumentation in `.19.2` to ensure pass@1 telemetry is not dominated by the stable-7.

