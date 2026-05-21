# fd-runtime-assurance-break-observability — Findings

**Decision lens:** Formal verification / runtime monitors for safety-critical systems. The diagnostic distinction is between properties **proved at a boundary** (proof obligations: checked once, at compile time or phase transition) and properties **enforced as runtime invariants** (continuous monitors: violation must be detected immediately, not at the next check point). Adequacy question: does the monitor detect a violation when it occurs, or only retrospectively at the next phase boundary?

**Stance:** **Continuous monitor required; gate is a category error.** The property the §7.1 prose actually asserts at lines 464-465 — "a subsystem that cannot find contradictions to surface is a subsystem whose self-observation has gone blind" — is a **liveness invariant**, not a retrospective property. Liveness invariants cannot be enforced by a boundary check; they require continuous monitoring with a violation condition that fires immediately on entry to the bad state. The gate variant at line 459 is checking the wrong shape of property. The spec is not internally consistent: lines 456-460 describe a retrospective gate, lines 461-465 assert a liveness property the gate cannot enforce.

---

## P0 — Mid-Compound observation failure is undetectable under the gate variant

**Location:** `docs/sylveste-vision.md:459-460` (gate check at Compound→Epoch boundary) vs `:464-465` (claim that the system enforces continuous self-observation health).

**Failure scenario:** A subsystem files N Break receipts in weeks 1-2 of a 12-week Compound window — perhaps as part of an integration burst when new evidence streams come online. The receipts are genuine, severity-scored properly by Interspect, no gaming. In week 3, the self-observation mechanism silently fails: an upstream Interspect channel disconnects, a contradiction-detection rule is shadowed by a refactor, a quarantine pipeline backs up. Weeks 3-12: zero Break receipts, no diagnostic signal. At week 12 the gate evaluates: count = N. Pass. Subsystem advances to Epoch having been **effectively unobserved for 83% of its Compound window**.

The trust architecture has no mechanism — no monitor, no probe, no signal — that fires during weeks 3-12 to indicate the observation channel is dead. Under the gate variant, the only available detection point is the next Compound→Epoch boundary, which has already passed. The mechanism that would catch this (regression indicators per line 474-475) only fires on *demotion*-side evidence, not on observation-channel-failure evidence.

**Why P0:** The vision document's whole §7 architecture rests on the claim that trust is grounded in continuous evidence (line 14: "evidence that compounds"; line 20: "evidence compounds per-subsystem"). A 10-week observation blackout that the architecture cannot detect is data corruption at the foundation: the maturity tier the subsystem holds in Epoch is grounded in weeks 1-2 of evidence and 10 weeks of nothing. This is not a slow quality issue; the trust state is wrong on entry to Epoch and the architecture cannot tell. Drop everything.

**Smallest viable fix:** Add a runtime-monitor invariant to §7.1, alongside or replacing the gate language at line 459-460:

> The Break phase enforces a liveness invariant during Compound: the subsystem must surface at least one Break receipt within every rolling window of length W, where W is per-subsystem-specified in promotion criteria. Failure to satisfy the invariant fires immediately as a Tier-2 regression signal (§7.4) and does not wait for Compound→Epoch boundary evaluation.

This converts the property from "N receipts accumulated by boundary" (retrospective) to "rolling-window receipt presence" (liveness). The monitor can fire mid-Compound. The 10-week blackout becomes detectable in week 3 + W, not week 12.

---

## P0 — The spec asserts a property the chosen mechanism cannot enforce

**Location:** Internal inconsistency between `docs/sylveste-vision.md:459` ("≥N Break receipts in its Compound window") and `:464-465` ("a subsystem that cannot find contradictions to surface is a subsystem whose self-observation has gone blind").

**Failure scenario:** A reader of v6 takes line 464-465 as a statement about what the architecture *enforces*. They reason: "If self-observation goes blind, the architecture catches it." They build downstream design (§§7.2-7.11) atop this assumption — Demote propagation rules, regression-indicator semantics, Epoch-trigger rubrics. But the gate at line 459 only enforces a count at boundary: a subsystem whose self-observation goes blind in weeks 3-12 of a 12-week window with N=2 receipts in weeks 1-2 will pass cleanly. Line 464-465 is descriptively false under the gate variant. Downstream design rests on a property the architecture does not have.

**Why P0:** This is a foundational specification defect. Two passages of the same section disagree about what the system enforces. Either line 459 is correct (count gate, no liveness guarantee) and line 464-465 is wishful prose to be deleted, or line 464-465 is correct (liveness guarantee) and line 459 must be replaced with a monitor specification. Cannot ship v6 with both readings live.

**Smallest viable fix:** Replace line 459-460 with the rolling-window invariant from P0 #1 above. Line 464-465 then describes what the architecture actually does. Alternative: weaken line 464-465 to describe a *retrospective audit observation*, not an enforced property — but this guts the Break phase's design intent.

---

## P1 — Interspect's severity scoring is post-hoc audit, not runtime monitor

**Location:** `docs/sylveste-vision.md:457-458` ("Self-surfaced contradictions, scored for severity by Interspect rather than by the pillar surfacing them").

**Failure scenario:** Interspect reads Break receipts and assigns severity. From a runtime-monitor perspective, the scoring is a **post-hoc audit**: it runs after the receipt is filed, with whatever queueing/batching/scheduling latency Interspect has. If Interspect's scoring queue is 48 hours deep (consistent with §7.3's evidence quarantine pattern), then the rolling-window invariant from P0 #1 cannot be evaluated in real time on **scored** receipts — only on filed receipts.

This forces a choice: evaluate the invariant against filed-but-unscored receipts (real-time, but a subsystem could file low-severity receipts to clear the invariant and the scorer's later downgrade has no operational effect) or against scored receipts (correct severity weighting, but the invariant lags by the scoring latency, defeating real-time monitoring).

**Why P1:** Required to exit v6 quality gate because the gate↔continuous decision implies Interspect's role and latency must be specified. The spec at line 457-458 names Interspect as scorer but does not characterize the scoring pipeline as monitor-or-audit, and the answer materially affects whether continuous-mode is operationally feasible.

**Smallest viable fix:** Add to §7.1 around line 458:

> Interspect performs severity scoring asynchronously (audit role, not runtime monitor). Liveness-invariant evaluation uses filed-receipt timestamps with severity-weighted re-evaluation when scoring completes; a subsystem whose receipts are subsequently downgraded below the severity floor receives a Tier-2 regression signal applied retroactively to the affected Compound window.

This makes explicit that Interspect is post-hoc and that the architecture handles the latency through retroactive re-evaluation, not by waiting for scoring at the gate.

---

## P1 — Continuous-mode variant lacks a quantitative violation condition

**Location:** §7.1 prose at `docs/sylveste-vision.md:456-465` describes Break qualitatively; no quantitative rate or window threshold is stated for the continuous-mode reading.

**Failure scenario:** Engineers attempting to implement the continuous variant cannot determine when a subsystem is in violation. "Sustained rate" without a quantitative floor is qualitative; a runtime monitor cannot distinguish compliant from non-compliant runs. This is the formal-verification analogue of an under-specified safety property: the spec describes the *intent* but not the *condition*, and engineers in different parts of the system will pick different thresholds.

**Why P1:** Required to exit quality gate. A monitor without a violation condition is not a monitor.

**Smallest viable fix:** Promotion-criteria schema must include `break_invariant: { rolling_window: <duration>, min_receipts_in_window: <int>, min_severity_floor: <enum> }`. The trio defines the invariant precisely.

---

## P2 — Gate variant systematically undercounts late-Compound receipts

**Location:** `docs/sylveste-vision.md:459` (boundary check) interacting with §7.3 evidence-quarantine pattern (referenced but not in this excerpt).

**Failure scenario:** Receipts filed in the last 48 hours of Compound may not have completed Interspect scoring at gate-evaluation time. If the gate evaluates against scored receipts, late receipts are systematically undercounted — subsystems that file continuously toward window-end fail despite healthy self-observation; subsystems that front-load pass cleanly. This is a structural bias toward front-loaded receipt patterns, which is exactly the counterfeit-kyū failure mode the design was meant to prevent.

**Smallest viable fix:** Per the P1 #1 fix above, evaluate against filed-receipt timestamps with retroactive severity re-evaluation. Eliminates the undercount.

---

## Implications for downstream calls

- **#2 (who scores):** Interspect must be characterized as **post-hoc audit, not runtime monitor**. This is a hard constraint on the architecture and downstream §§7.3-7.11 must respect it. If §7.4 regression indicators are expected to fire in real time, they cannot rely on Interspect-scored severity; they must use filed-receipt presence.
- **#3 (threshold form):** Threshold form must be a **rolling-window invariant** (`{window_duration, min_count, min_severity}`), not a boundary count. This is the only form that enforces the liveness property line 464-465 asserts.
- **#5 (consequence framing):** Violation of the rolling-window invariant fires **mid-Compound as a Tier-2 regression signal** per §7.4, not as a Compound→Epoch gate failure. The consequence is integration into the existing demote-pipeline, not a new pass/fail boundary.

## Cross-references / anti-overlap

- I am leaving SLO/burn-rate framing to **fd-sre-burn-rate-vs-gate**. Their concept of a "burn-rate alert" is operationally close to my "rolling-window invariant" but their lens is alerting/budget; mine is property-shape/monitor-architecture. We will likely converge on the same fix shape from different vocabulary.
- I am leaving sample-size and false-promotion-rate calculation to **fd-progressive-delivery-shadow-eval** and **fd-ml-canary-break-rate**. My P1 #2 only says "quantitative threshold required"; the question of *what value* the threshold should take given a target false-promotion rate is theirs.
- I am leaving SPC control-chart vocabulary and gameability analysis to **fd-spc-break-process-control**. My P0 findings are about property-shape correctness; SPC's lens on gaming-incentives is orthogonal and complementary.
- The runtime-monitor framing implies a **reactive demotion path** when the invariant fires mid-Compound. The SRE agent will likely propose similar via burn-rate alerting; the SPC agent via control-limit excursions. Three flavors of the same fix; the architecture should pick one vocabulary and stay consistent.
