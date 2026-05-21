---
track: B
track_name: Orthogonal — Parallel Professional Disciplines
agents: [fd-nuclear-maintenance-rule, fd-continuous-controls-monitoring, fd-postmarket-surveillance, fd-atc-surveillance]
decision_question: "§7.1 Break phase: discrete gate (≥N receipts before Epoch) vs continuous-mode requirement (sustained contradiction-surfacing rate as Tier-2 evidence of self-observation health)"
produced: 2026-05-06
---

# Track B Summary — §7.1 Break Phase Structure

## Convergence Verdict

**Hybrid — gate as entry condition retained; continuous monitoring mandatory in Epoch; tiered by subsystem criticality.**

No Track B agent recommends replacing the ≥N gate. All four recommend adding a continuous monitoring layer around it. The convergence point is structural: the gate is the right entry condition for Epoch (the IFR clearance, the NDA approval, the a-category goal publication, the SOX 404 annual opinion) — but gate passage does not constitute ongoing health assurance. A distinct, always-on surveillance mechanism is required to verify that the self-observation behavior that earned the gate continues to operate after it. For M1–M2 subsystems, a cadence-distributed gate with minimum reporting intervals may be adequate. For M3+ governance and routing subsystems, all four disciplines independently mandate continuous monitoring.

The strongest convergence in this track is on a finding that is currently absent from the §7.1 spec: **the zero-receipt floor / position-report gap / control-silent alert / post-market surveillance obligation are four discipline-specific names for the same missing primitive** — a mechanism that treats sustained absence of Break receipts as a health failure signal rather than a health confirmation.

---

## Cross-Discipline Operational Patterns

### 1. Gate and surveillance are structurally separate instruments — never conflate them

All four disciplines have made this distinction operationally load-bearing:

- **Nuclear (10 CFR 50.65):** b-category inspection gates vs a-category rolling-window functional failure rate monitoring. The rule exists because gates failed for safety-critical systems.
- **Financial audit (SOX 404 / CCM):** Annual audit opinion vs CCM exception-rate dashboard. CCM was built to fill the gap between annual attestations.
- **Pharma (NDA/REMS/PBRER):** Approval gate vs ongoing pharmacovigilance. Post-1962 law explicitly separates the two as distinct, concurrent obligations.
- **ATC (IFR / SSR):** Clearance vs secondary surveillance radar. The radar loop is not a better gate — it is a categorically different instrument that verifies corridor maintenance throughout the flight.

**Sylveste implication:** Break-as-gate is the correct design for Epoch entry. Continuous Break-rate monitoring in Epoch is a structurally separate requirement, not an enhancement to the gate. The §7.1 spec conflates them by stopping the Break spec at gate passage.

### 2. Silence is not health — it must be investigated

All four disciplines independently treat sustained absence of expected signal as a potential instrument failure, not evidence of system health:

- **Nuclear:** A system in a-category must demonstrate sustained performance against measurement goals. A system that produces no functional failure indicators within a monitoring period is not automatically healthy — it must demonstrate the monitoring mechanism is operating.
- **CCM:** A control that fires zero exceptions is "control silent" — suspicious, not confirmed healthy. CCM dashboards escalate zero-exception periods for investigation.
- **Pharma:** "Absence of adverse event signal is not evidence of absence of risk" — it may be evidence of signal-detection failure. ICH E2E requires minimum-detectable-signal calibration.
- **ATC:** A flight that files no intermediate position reports between departure and destination is lost contact, not confirmed on-route. FAA 7110.65 procedures for lost communication apply.

**Sylveste implication:** The §7.1 spec needs a zero-receipt floor: a defined number of consecutive observation sub-periods with zero Break receipts triggers a Break-health review by Interspect, not a gate passage. This is a single spec addition (one clause) with no architectural change required.

### 3. Criticality governs monitoring intensity — uniform treatment across subsystems is operationally wrong

Three of four disciplines (nuclear, ATC, pharma) explicitly tier their monitoring requirements by consequence:

- **Nuclear:** a-category is mandatory for safety-critical equipment regardless of past inspection record; b-category is available only for lower-consequence equipment.
- **ATC:** Class A/B airspace (high-density, high-consequence) requires continuous radar surveillance; Class G (low-density, low-consequence) permits procedural position-report control.
- **Pharma:** REMS (Risk Evaluation and Mitigation Strategies) applies mandatory enhanced post-market surveillance only to drugs with serious identified risks; standard pharmacovigilance applies to others.

**Sylveste implication:** A uniform ≥N gate across all M-tiers and subsystem criticality levels is operationally incorrect. Ockham (dispatch), Interspect (audit), Intercore (kernel), and Governance pillars are high-criticality (Class A/B / a-category / REMS-eligible) and require continuous Break-rate monitoring in Epoch. M1–M2 non-critical subsystems may use a position-report-cadence gate (minimum distribution requirement) without full continuous surveillance.

### 4. Entry events do not transfer obligation — handoffs require re-establishment

Two disciplines (pharma, ATC) surface this explicitly, and it is implicit in nuclear and CCM:

- **ATC:** Sector handoff requires re-establishment of surveillance contact. The previous sector's radar track is briefing material, not authority transfer.
- **Pharma:** Epoch-equivalent label-change triggers require a new benefit-risk assessment against the current risk profile, not inheritance of the pre-change approval.

**Sylveste implication:** When an Epoch trigger fires (model API change, architecture migration, subsystem replacement), the Break evidence from the prior Compound window is briefing material — it must not carry over as authorization for the new Epoch corridor. §7.11 (Epoch trigger rubric) should specify that substrate-changing Epoch triggers reset the Break baseline and require a provisional monitoring period before full Epoch clearance is renewed.

---

## Highest-Confidence Finding

**The zero-receipt floor is absent from the current spec and its absence is a P0 across all four disciplines.**

Every Track B agent independently identified that the current spec has no mechanism to detect a subsystem that passes the Break gate and then stops surfacing contradictions. This is not a design tradeoff — it is an omission. The §7.1 text explicitly states the failure mode to prevent ("a subsystem that cannot find contradictions to surface is a subsystem whose self-observation has gone blind") and the current spec has no detection mechanism for this exact failure mode post-gate. The fix is minimal: add a zero-receipt floor with a health-review escalation path. This does not change the gate structure, does not require architectural changes, and does not alter any other lifecycle phase. It is additive.

---

## Per-Agent Verdicts (one line each)

- **fd-nuclear-maintenance-rule:** Gate is b-category; M3+ governance and routing subsystems warrant a-category continuous monitoring with rolling window, pre-specified goals, and zero-receipt floor by 10 CFR 50.65 classification.

- **fd-continuous-controls-monitoring:** Gate is a SOX-404-style point-in-time opinion; CCM requires adding a zero-receipt floor (control-silent alert) and rate-normalized threshold (not absolute count) to produce a persistent health signal alongside the entry condition.

- **fd-postmarket-surveillance:** Gate is the NDA approval event; post-Epoch surveillance obligation must continue — the pre-1962 "prove once, operate indefinitely" model is the failure mode Break was designed to prevent, but the current spec replicates it post-Epoch.

- **fd-atc-surveillance:** Gate is the IFR clearance; Epoch without a surveillance loop is pre-radar procedural control — acceptable in low-density airspace (M1–M2), unacceptable for high-criticality Class A/B equivalent subsystems where undetected corridor deviation is the primary risk.
