# fd-spc-break-process-control — Findings

**Decision lens:** Quality control engineering. Incoming inspection (gate at boundary, accepts all defects produced during process) vs in-process SPC (continuous, control-chart on process measurement, detects shifts during the process). Diagnostic question: at what point in the process does a deviation become detectable and actionable, and is incoming inspection being used to substitute for absent in-process monitoring?

**Stance:** **In-process SPC required; gate alone reproduces the classic incoming-inspection antipattern.** The gate variant at `docs/sylveste-vision.md:459-460` is incoming inspection on self-observation quality at the Compound→Epoch boundary. In quality-control practice, incoming inspection is acceptable only when (a) the cost of a defect reaching downstream is low, (b) inspection has high power to detect the defect, and (c) the production process itself is statistically stable. None of these hold for the Break phase: a blind subsystem reaching Epoch is high-cost (it propagates contaminated trust to dependents per §7.9), a count-only gate has low power (per fd-ml-canary's calculation, ≈19% false-promotion at N=3), and the production process — autonomous self-observation by a subsystem — is precisely what the architecture cannot assume is stable. Continuous receipt-rate monitoring with control limits is the SPC-correct response.

---

## P1 — Gate variant has no defined operational response to failure

**Location:** `docs/sylveste-vision.md:459-460` describes the gate condition but the spec at `:456-465` does not define what happens when the gate fails.

**Failure scenario:** A subsystem reaches Compound→Epoch boundary with N-1 Break receipts. The gate fails. What now? The spec is silent. Possible interpretations:
1. Subsystem stays in Compound; window extends until N is reached.
2. Subsystem's Compound window resets and re-runs.
3. Subsystem demotes per §7.1 line 474-477.
4. Subsystem holds in indeterminate state pending operator review.

Different implementations across pillars will pick different interpretations. Interspect-implementing-Break for plugin A may extend the window; Interspect-implementing-Break for plugin B may demote. The Trust Lifecycle becomes inconsistent across subsystems — a subsystem at "Compound" in plugin A is not the same operational state as "Compound" in plugin B because the gate-failure recovery semantics differ.

**Why P1:** Quality-control gates without a defined non-conformance response are operationally useless. In manufacturing, every incoming-inspection station has a documented disposition for fail: rework, scrap, deviation-with-exception. The Break gate has none. Required to exit v6 quality gate because §7.9 trust-propagation rules will reference Compound→Epoch transitions and need a deterministic disposition for failures.

**Smallest viable fix:** Add to §7.1 directly after line 460:

> A subsystem that fails the Break condition at Compound→Epoch evaluation: the Compound window extends by W (per-subsystem-specified) and the condition is re-evaluated. After a configured number of consecutive failures (default 2), the subsystem demotes per §7.5, with the failure recorded as a Tier-1 evidence event for the maturity downgrade.

This makes the failure path explicit, deterministic, and bounded.

---

## P1 — Gate creates inspection-gaming incentive; jo-ha-kyū violated in operational practice

**Location:** `docs/sylveste-vision.md:459` (count threshold) interacting with `:464-465` (jo-ha-kyū intent).

**Failure scenario:** Subsystem operators (human or AI agent) learn the N threshold over time. The dominant operational behavior under count-gate-with-late-eval is **end-of-window batch filing**: queue contradiction observations during the build phase, file them in a burst near Compound→Epoch boundary to clear the gate. Filing is decoupled from discovery. The receipts pass Interspect severity scoring (genuine contradictions, accurately scored). The count is met. The jo-ha-kyū intent — that the break interrupts the build — is violated: the break happens *after* the build, as a compliance-clearing artifact.

This is the classic quality-control inspection-gaming pattern. When a process is gated on a count at boundary, the process optimizes for clearing the count, not for the property the count was meant to measure. Demming's wisdom on this is direct: "Cease dependence on inspection to achieve quality. Eliminate the need for inspection on a mass basis by building quality into the product in the first place."

**Why P1:** The brainstorm source at `docs/brainstorms/2026-04-26-flux-explore-sylveste-flywheel.md:67` already named this risk — "pillars game Break by surfacing trivial contradictions" — and proposed Interspect severity scoring as mitigation. But severity scoring addresses *trivial* gaming, not *temporal* gaming. A subsystem can file high-severity receipts that are genuine but were discovered weeks before they were filed. The mitigation does not catch end-of-window batch filing of legitimate receipts.

**Smallest viable fix:** Replace the count gate with an in-process control chart on Break receipt rate. Specifically, an SPC chart with:
- **Centerline** = expected receipt rate per evidence-event-volume (per-subsystem-tuned baseline).
- **Lower control limit (LCL)** = baseline − 3σ. Excursion below LCL = process shift, fires Tier-2 regression signal mid-Compound.
- **Western Electric Rule 2** (8 consecutive points below centerline) = sustained drift, also fires.

The control chart fires when the *process* shifts, not when the count is met. Batch filing at end-of-window violates Rule 2 (8 consecutive zero-receipt sprints) regardless of whether the final batch clears a count. The temporal dimension is enforced by the process control vocabulary.

Document this in §7.1 around line 459-460:

> The Break phase enforces an in-process control on Break receipt rate: a subsystem in Compound must maintain receipt rate above per-subsystem-specified LCL for the duration of the window. Excursions below LCL fire as Tier-2 regression signals (§7.4) at the time of excursion, not at the Compound→Epoch boundary.

---

## P1 — Hysteresis band interaction with Break failure is undefined

**Location:** `docs/sylveste-vision.md:479-482` (hysteresis: "a subsystem that just demoted M3→M2 cannot re-promote on the same evidence window") interacting with Break gate failure.

**Failure scenario:** Subsystem at M3 fails Break gate. Per the P1 #1 fix, after consecutive failures it demotes to M2. Now: can the demoted M2 subsystem re-promote to M3 using the same Compound window's evidence (sans the Break failure that triggered the demotion)? The hysteresis text at line 479-482 says no for "the same evidence window that triggered demotion," but it is unclear whether Break-receipt-evidence specifically is included in the hysteresis band, or whether the band only covers the regression indicators that triggered the demotion.

The implementation question: is the hysteresis evidence-scoped (Break-related evidence is barred from same-window re-promotion) or trigger-scoped (only the specific evidence that triggered demotion is barred, and Break receipts that did clear could be re-used)?

**Why P1:** Hysteresis is the architecture's mechanism for preventing thrashing (line 481-482). If the band is trigger-scoped, a subsystem can demote on Break failure, then re-promote on the next Compound window using mostly the same evidence plus a single new Break receipt. This thrashes through the gate while satisfying the letter of the hysteresis rule. Required to exit quality gate because hysteresis is load-bearing for the convergence guarantee at line 481-482.

**Smallest viable fix:** Specify in §7.1 line 479-482:

> Break receipt evidence is evidence-scoped under hysteresis: a subsystem that demoted following Break failure cannot use any Break receipt from the demotion-triggering Compound window in subsequent re-promotion criteria. Break receipts in the post-demotion Compound window must be filed afresh.

---

## P2 — Continuous-mode lacks control limits; rate is observational without being actionable

**Location:** Hypothetical continuous-mode variant. The question's framing — "rate becomes Tier-2 evidence about self-observation health" — does not specify control limits.

**Failure scenario:** Continuous-mode reports rate as Tier-2 evidence per line 443. Operators observing the rate trend cannot determine whether a drop is normal process variation or a genuine shift requiring intervention. The signal is observational, not actionable. SPC's whole value proposition is that the chart's UCL/LCL converts observations into binary decisions: in-control or out-of-control. Without control limits, continuous-mode generates data without decisions.

**Smallest viable fix:** Specify continuous-mode threshold form as a control-chart triple `{baseline_rate, UCL, LCL}`, derived per-subsystem from observed historical receipt-rate distribution during a calibration phase (e.g., the subsystem's M0→M2 history). Add to promotion-criteria schema.

---

## P2 — Cost-of-late-detection asymmetry argues for in-process even if gate is cheaper to implement

**Location:** §7.1 trust-architecture cost framing combined with §7.9 dependency propagation (referenced).

**Failure scenario:** A blind subsystem reaching Epoch is not just locally wrong — it propagates per §7.9 to dependents. Other subsystems' promotion criteria use this subsystem's Epoch-resident maturity tier as Tier-2 evidence. The defect compounds across the dependency graph. By the time downstream symptoms (regression indicators on dependents) make the original blindness detectable, weeks of evidence have accumulated atop a contaminated foundation.

In manufacturing, this is the cost-asymmetry argument for SPC over incoming inspection: a defect caught at the source costs $1 to fix; the same defect caught downstream after assembly costs $100; after shipment $1000. Sylveste's evidence corpus has the same compounding-cost structure.

**Smallest viable fix:** No code change here — this is an argument for the P1 #2 fix (in-process control over boundary gate), framed as a cost-justification rather than a mechanism. Add as commentary in §7.1 around line 465: "In-process detection during Compound is preferred over boundary detection at Compound→Epoch transition: the trust dependency graph (§7.9) propagates Epoch-resident maturity to dependents, and late-detected defects contaminate dependent evidence streams disproportionately."

---

## Implications for downstream calls

- **#2 (who scores):** Interspect must compute and maintain the SPC chart, not merely score severity. Two distinct functions: (a) per-receipt severity scoring (current spec at line 458) and (b) per-subsystem control-chart maintenance with mid-Compound excursion alerting (the new role). The architecture must call this out.
- **#3 (threshold form):** Threshold form is `{baseline_rate, UCL, LCL, applicable_run_rules}` — a control chart specification, not a count. Run rules (Western Electric, Nelson, etc.) are part of the threshold; specify which set applies.
- **#5 (consequence framing):** Two-tier consequences:
  - **Mid-Compound LCL excursion:** Tier-2 regression signal per §7.4. Subsystem investigation triggered. Compound window may extend pending recovery.
  - **Sustained out-of-control state at Compound→Epoch boundary:** Demote per the deterministic disposition from P1 #1.

## Cross-references / anti-overlap

- The SRE agent (**fd-sre-burn-rate-vs-gate**) is likely framing the in-process detection as burn-rate alerting. We agree on the mechanism shape; my SPC vocabulary contributes the run-rules dimension (Western Electric, etc.) that the SRE framing typically lacks. Cite both.
- The runtime-assurance agent (**fd-runtime-assurance-break-observability**) is likely framing this as a liveness invariant with mid-Compound monitor. We agree the boundary check is the wrong shape; SPC contributes the *baseline-relative* and *variation-aware* dimensions that pure liveness monitors lack (a liveness monitor only knows "alive or dead"; an SPC chart knows "drifting").
- The ML-canary agent (**fd-ml-canary-break-rate**) is likely framing the gameability as Goodhart/reward-hacking. We agree on the gaming pathology; my P1 #2 covers the *temporal* dimension of gaming (end-of-window batch filing) that ML-style Goodhart analysis often misses because ML evaluation is typically not temporally distributed within an evaluation window.
- The progressive-delivery agent (**fd-progressive-delivery-shadow-eval**) is likely framing this as canary vs shadow-eval. Their structural-precedent argument from §6 is independent of mine and reinforces it from a different angle.
- I am specifically the only agent with vocabulary for **non-conformance disposition** (P1 #1) and **hysteresis-band evidence scoping** (P1 #3). Highlight these in synthesis as SPC-distinctive contributions.
