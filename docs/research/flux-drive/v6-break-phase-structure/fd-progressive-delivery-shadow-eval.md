# fd-progressive-delivery-shadow-eval — Findings

**Decision lens:** Progressive delivery / shadow evaluation. Canary gates (binary, fast, miss gradual drift) vs shadow eval (continuous metric stream, requires a decision rule). Diagnostic question: what is the earliest signal that this rollout is degrading, and is the gate's N chosen with a sample-size calculation that bounds false-promotion probability?

**Stance:** **Hybrid leaning continuous, with a structural precedent argument.** The §6 shadow-apprenticeship pattern (new M2 sources running shadow-mode before going active) already establishes that Sylveste prefers continuous monitoring over single-shot gates for trust-related decisions. The Break phase as currently spec'd at `docs/sylveste-vision.md:456-465` is a single-shot canary at the Compound→Epoch boundary, which is the *opposite* of the established pattern. Either the existing precedent is wrong (unlikely — it is load-bearing for §6) or the Break phase should extend it. Continuous monitoring with a decision rule is the structurally consistent choice.

---

## P0 — N is chosen without a sample-size calculation; false-promotion rate is unquantified

**Location:** `docs/sylveste-vision.md:459` ("≥N Break receipts in its Compound window") — N is named but never calibrated.

**Failure scenario:** Suppose a healthy self-observer surfaces contradictions at a true rate of 30% per evaluable opportunity (sprint, evidence event, whichever the unit turns out to be). A degraded self-observer with a partial blind spot surfaces at 5%. With N=3 and a 30-opportunity Compound window:
- Healthy observer expected count: 9. P(count ≥ 3) ≈ 0.999.
- Degraded observer expected count: 1.5. P(count ≥ 3) ≈ 0.19.

That 0.19 is the **false-promotion rate** for a degraded self-observer at N=3. With dozens of subsystems cycling through Compound→Epoch repeatedly across the platform, this compounds: the long-run fraction of Epoch-resident subsystems with degraded self-observation is bounded only by `(degraded_population_share × 0.19)`. The trust architecture cannot quantify this fraction, which means it cannot quantify the integrity of the flywheel.

**Why P0:** The vision document stakes Sylveste's credibility on "evidence that compounds" (line 14) and "trust advances when the evidence warrants it" (line 21). A trust-promotion gate whose false-pass rate is unspecified is, in progressive delivery terms, a canary deploy with no rollback criteria. This is not a slow quality drift; it is a foundational gap in the architecture's claim to evidence-grounded trust. Drop everything until N has a sample-size rationale.

**Smallest viable fix:** Add to §7.1 alongside the per-subsystem promotion-criteria text at line 449-450 an explicit field:

> `break_threshold_calibration: { false_promotion_rate_target: <float>, healthy_baseline_rate: <float>, degraded_baseline_rate: <float>, derived_N: <int>, derived_W: <window> }`

Each subsystem's promotion criteria must publish derived N from a stated false-promotion target, with healthy and degraded baselines specified. If baselines are unknown for new subsystems, the field declares them unknown and N is set to the conservative high-tail value until baselines are observed.

---

## P1 — Continuous-mode variant lacks a decision rule (shadow-eval without abort criteria)

**Location:** `docs/sylveste-vision.md:443-450` (Tier-2 observational evidence) and `:456-465` (Break phase prose).

**Failure scenario:** Hypothetically swap the gate for "Break receipt rate becomes Tier-2 evidence about self-observation health." Now a subsystem with rate-below-threshold has its rate logged and aggregated alongside other Tier-2 signals. **But Tier-2 evidence per line 448-449 is sufficient for promotion when it meets threshold; it is never operationally tied to Epoch eligibility under the continuous variant as drafted.** The continuous mode degrades to logging: rate is reported, no action gate fires, the subsystem advances to Epoch on its non-Break Tier-2 signals.

**Why P1:** In progressive delivery, shadow eval without an abort signal is just metric collection. The jo-ha-kyū requirement (line 461-465) demands operational consequence, not measurement. A continuous-mode Break that does not block Epoch advancement when rate is below threshold violates the design intent.

**Smallest viable fix:** Continuous-mode variant must specify the decision rule explicitly. Add to §7.1 directly:

> Under continuous-mode, Epoch eligibility requires Break-receipt rate ≥ R over the Compound window, where R is per-subsystem-specified in promotion criteria. A subsystem with rate < R is held in Compound; the Compound window is extended until rate recovers or until a configured timeout triggers Demote review.

Without this, continuous mode is observation-only and the design has no teeth.

---

## P1 — Shadow-apprenticeship in §6 is structural precedent the Break phase contradicts

**Location:** §6 source-promotion shadow-mode pattern (referenced in vision document; pattern established for new M2 sources running shadow-mode before going active) vs `docs/sylveste-vision.md:456-465` Break-as-gate.

**Failure scenario:** Sylveste's design canon already has a worked example of "continuous shadow monitoring before promotion" — that is exactly what shadow-apprenticeship for M2 sources is. The Break phase is structurally the same problem: validate the integrity of a trust-state transition. But §7.1's Break is a single-shot gate, not a shadow-mode period. Two different patterns for the same design problem create inconsistency in how engineers reason about Sylveste trust mechanics: shadow-eval-style for source promotion, gate-style for Compound→Epoch. New contributors will pattern-match wrong.

**Why P1:** Architectural-coherence finding. Required to exit the v6 quality gate because v6 is consolidating the trust architecture; inconsistency between §6 and §7.1 will compound through downstream §§7.2-7.11 references. A reader of v6 should be able to derive the Break-phase shape from the §6 precedent and not be surprised.

**Smallest viable fix:** Reword §7.1 line 456-465 to frame Break as the analogue of shadow-apprenticeship at the Compound→Epoch boundary — receipt rate as the Tier-2 stream, with the rate-based decision rule providing the gate. Cross-link to §6 explicitly: "Break is the lifecycle-internal analogue of §6 shadow-apprenticeship: the subsystem's self-observation channel must demonstrate sustained activity, not merely accumulate a count."

---

## P2 — Epoch reset semantics for Break receipt history are undefined

**Location:** `docs/sylveste-vision.md:467-472` (Epoch phase) interacting with `:456-465` (Break gate).

**Failure scenario:** Subsystem enters Epoch (partial reset under new conditions, line 468-470). Subsystem must re-demonstrate at its tier. Question: do Break receipts from the prior Compound window count toward the post-Epoch Break gate, or are they zeroed? If they carry over, the post-Epoch Break gate is satisfiable by historical receipts from a prior operational context — directly violating the "re-demonstrate under new conditions" intent of line 469-470. If they zero, the spec must say so.

**Why P2:** Degrades over weeks-months as subsystems cycle through Epoch, but does not fire alarms day-one. Still operationally meaningful when it does fire.

**Smallest viable fix:** One-line addition in §7.1 around line 470: "Break receipt history is zeroed on Epoch reset; the new Compound window's gate evaluates only post-Epoch receipts."

---

## Implications for downstream calls

- **#2 (who scores):** Interspect's role as severity scorer (line 458) is the canary-analysis-service equivalent in progressive delivery. **Critical:** scorer must be external to the subsystem being scored. The spec already establishes this; preserve it.
- **#3 (threshold form):** Per my P0, threshold cannot be a single N — must be a calibration tuple `{healthy_baseline_rate, degraded_baseline_rate, false_promotion_target, window}` from which N (or rate threshold R) is derived. This is a sample-size-calculation form, not a hand-picked-integer form.
- **#5 (consequence framing):** Per my P1 #2, the consequence of failing the rate threshold should be Compound-window-extension with timeout-to-Demote, not immediate hard-fail. This matches progressive delivery's "hold the rollout, investigate, then either extend or rollback" pattern.

## Cross-references / anti-overlap

- The SRE agent (**fd-sre-burn-rate-vs-gate**) is likely converging on hybrid with quiet-gap detection. We agree on hybrid; my framing emphasizes false-promotion rate calibration, theirs emphasizes operational quiet-period detection. Complementary, not overlapping.
- I am leaving formal liveness-property analysis to **fd-runtime-assurance-break-observability** — my finding #2 stops at "decision rule needed" and does not characterize whether the rule is a safety or liveness property.
- I am leaving the SPC-style control-chart specification to **fd-spc-break-process-control** — my P1 #2 says "rate ≥ R" but SPC has the right vocabulary (UCL/LCL, CUSUM, EWMA) for *what shape* R should take.
- I am leaving the temporal-distribution-of-receipts and gameability-of-receipt-generation analyses to **fd-ml-canary-break-rate** — front-loaded burst detection and reward-hacking pattern recognition are their lane; my P1 #1 only flags the calibration gap that lets gameability matter.
