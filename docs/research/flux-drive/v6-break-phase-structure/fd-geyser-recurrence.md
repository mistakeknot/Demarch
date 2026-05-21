---
agent: fd-geyser-recurrence
source_domain: Yellowstone geyser hydrothermal forecasting
decision_lens: Is a Break receipt like a geyser eruption (discrete event whose count over a window means little without inter-event-interval distribution) or like a continuous tilt reading (rate signal whose variance over the window is the actual evidence)?
track: C (Distant — structural isomorphisms)
date: 2026-05-06
target_decision: §7.1 Break phase — gate-vs-continuous
---

# fd-geyser-recurrence — Findings

## The Central Isomorphism

Yellowstone's hydrothermal observatory does not forecast eruptions by counting events. It monitors the continuous reservoir-temperature and seismicity record from which eruptions emerge. A geyser observatory that only tallied eruption counts and declared a geyser "healthy" if it erupted ≥N times in a window would miss the most critical information: the inter-eruption interval distribution and its variance.

Old Faithful is forecastable precisely because its inter-eruption interval is low-variance (narrow distribution around a mean that shifts predictably with eruption duration). Steamboat — the world's tallest active geyser — is not forecastable on counts because its inter-eruption interval is heteroscedastic: it can be dormant for years, then erupt in rapid succession. An Old-Faithful-style ≥N-in-window count is meaningless for Steamboat's behavior.

The distinction matters because **dormancy and degradation are indistinguishable from count data alone**. A geyser that has been dormant for three years and one that has gone permanently extinct both show zero eruptions. The continuous reservoir record distinguishes them: the dormant geyser shows maintained subsurface temperature and seismicity; the extinct conduit shows cooling and silence.

§7.1's ≥N Break receipts gate is an eruption-count model applied to a phenomenon whose health signal lives in the continuous record.

---

## P0 — Count Threshold Loses Inter-Receipt Interval Distribution

**Mechanism name: Eruption-count model applied to an interval-distributed phenomenon**

**Location:** `docs/sylveste-vision.md` lines 456-465, specifically: "A subsystem cannot enter Epoch unless it has logged ≥N Break receipts in its Compound window."

The ≥N gate treats Break receipts as independent events whose count over a window is the summary statistic. In geyser forecasting, this is equivalent to asserting that a geyser that erupted N times in one week is equivalent to one that erupted N times in one year. The inter-event interval distribution is the actual signal for conduit health.

A pillar can satisfy ≥N via two radically different regimes:
- Regime A: receipts distributed at roughly even intervals across the Compound window — the Old-Faithful pattern of a healthy conduit with stable reservoir dynamics
- Regime B: receipts clustered at the end of the window, preceded by a long silence — the Steamboat pattern that can indicate either benign dormancy (conduit accumulating charge) or conduit degradation (low-frequency eruptions from a partially blocked system)

These regimes pass the same ≥N gate. They are not the same artifact.

**Concrete failure scenario:** Pillar X is Clavain's gate-tier logic. During its Compound window it produces zero Break receipts for eleven weeks (self-observation appears to have gone silent), then surfaces N receipts in the final week before Epoch. The ≥N gate passes. Epoch transition occurs. Under Epoch conditions (new model API), Clavain's self-observation fails completely — the final-week burst was real but not representative of sustained capability. The continuous record would have flagged the eleven-week silence as an anomaly; the count gate could not.

**Smallest viable fix:** Add an inter-receipt-interval requirement to the gate spec at `docs/sylveste-vision.md` line 458:

> "logged ≥N Break receipts with no inter-receipt gap exceeding G sprint cycles"

G should be calibrated per-pillar during initial Compound windows (roughly: the per-pillar natural surfacing interval under stable conditions). This is the equivalent of the Old Faithful empirical interval — not universal, but per-system.

---

## P0 — Dormancy Indistinguishable from Degradation

**Mechanism name: Extinct-vs-dormant conduit problem**

**Location:** `docs/sylveste-vision.md` lines 453-465 (Compound + Break definitions).

The spec notes (lines 464-465): "a subsystem that cannot find contradictions to surface is a subsystem whose self-observation has gone blind." This correctly identifies degraded self-observation as dangerous. But it conflates two distinct states:

1. **Genuine dormancy**: a pillar in a steady-state period where the operating environment genuinely produces few contradictions to surface. The conduit is healthy; the reservoir is simply not charged.
2. **Degraded self-observation**: the conduit is blocked. The reservoir may be charging but pressure is not converting to eruption — i.e., the self-observation faculty is failing to translate internal tensions into surfaced receipts.

In the Yellowstone observatory, these are distinguished by the continuous record: dormancy shows flat-but-present reservoir temperature and microseismicity; conduit degradation shows temperature rise without seismicity (no brittle response), or cooling (abandonment).

The ≥N gate treats both as identical: zero or low receipts in the window. The gate cannot distinguish "healthy and quiet" from "failing and silent."

**Concrete failure scenario:** Interop in a stable synchronization period has few genuine contradictions to surface — its integrations are working, there are no cross-system inconsistencies, the environment is not presenting novel stress. Its Break-receipt rate is legitimately low. Under the ≥N gate, this appears identical to a pillar whose self-observation has gone blind. Interop is either wrongly demoted (if gate is strict) or wrongly cleared by Interspect inferring degradation where there is none. No mechanism exists to classify which case applies.

**Smallest viable fix:** Define a per-pillar baseline Break-receipt rate during the first Compound window (analogous to the observatory establishing a geyser's natural interval). Subsequent windows require rate within a tolerance band of the baseline, not absolute count. Silence within the tolerance band is classified as dormancy; silence significantly below baseline triggers a separate investigation gate (not an automatic fail). This is the "inter-eruption interval anomaly detection" pattern from the observatory.

---

## P1 — No Precursor Model; Forecast-vs-Actual Divergence Not Used as Evidence

**Mechanism name: Reactive eruption-recording vs predictive reservoir-monitoring**

**Location:** `docs/sylveste-vision.md` lines 456-465 (Break definition).

The spec records Break receipts as they arrive. There is no mechanism to forecast when the next receipt should arrive and treat the forecast-vs-actual gap as evidence about self-observation health. In geyser forecasting, the inter-eruption interval forecast is itself a state indicator: a geyser whose eruptions arrive early indicates excess reservoir charging; a geyser whose eruptions arrive late or not at all indicates conduit obstruction.

For Sylveste, the equivalent: a pillar whose Break receipts arrive at a rate *faster* than its established baseline may indicate elevated internal contradiction density (a meaningful signal about the subsystem's operational health — a kind of excess-pressure state). A pillar whose receipts arrive *slower* than baseline may indicate either dormancy or degradation. The deviation from forecast is itself trust evidence, distinct from the receipt content.

**Concrete failure scenario:** Ockham has established a baseline Break-receipt interval of approximately one receipt per three sprints. For six sprints, no receipt arrives. This deviation from forecast is not currently captured as evidence — neither as a Tier-2 demotion signal nor as a flag for manual inspection. The divergence is simply silence. The observatory equivalent: the seismograph records nothing and no alarm fires because the monitoring system only records eruptions, not inter-eruption silences.

---

## P2 — Compound Window Length Not Calibrated to Natural Inter-Receipt Interval

**Mechanism name: Window-to-interval mismatch**

**Location:** §7.1 Break definition and §7.3 decay model (decay model window referenced but not specified in the target passage).

The Compound window length is not specified in the target passage, but the ≥N threshold implies a window. If the window is shorter than the pillar's natural inter-receipt interval, the gate will systematically fail healthy pillars (requiring more eruptions than the natural cadence produces). If the window is longer than N times the natural interval, the gate is too permissive (a pillar could satisfy ≥N with long gaps that the gate ignores).

The Yellowstone observatory calibrates observation windows to the expected inter-eruption interval: for Old Faithful, a 24-hour window is meaningful; for Steamboat, a window must be multi-year. Applying a universal window to heteroscedastic systems produces unreliable inference.

---

## Stance on Gate vs Continuous

The geyser domain does not present gate-vs-continuous as a choice; in 30 years of Yellowstone monitoring, the observatory has never forecasted eruptions from counts alone. The continuous record (tilt, temperature, seismicity, GPS deformation) is the epistemic foundation; discrete eruption events are the confirmation that the continuous record was correctly read.

Applied to Break: the continuous variant (option b — rate as sustained evidence) is the epistemic foundation. The discrete gate (option a — ≥N receipts) is a serviceable summary statistic only if it encodes the distribution properties of the continuous record (inter-receipt intervals, variance, silence duration). A gate that captures only count is to geyser forecasting what a tally of eruption events is to reservoir science: true, but not sufficient and potentially misleading.

**The heteroscedasticity problem is the deepest finding:** some Sylveste pillars will surface Break receipts in bursts (Steamboat); others will surface them as a steady drizzle (Old Faithful). A universal ≥N threshold is calibrated for neither. The first pass at a fix is to require per-pillar baseline calibration during the initial Compound window, with subsequent windows evaluated against that baseline.

---

## Implications for Downstream Calls

**#2 (who scores):** Interspect-scored severity is analogous to eruption-column height — a quality measure of each event. But the observatory also tracks inter-eruption interval variance. Interspect should record receipt timestamps with precision sufficient to compute inter-receipt intervals, not just severity scores.

**#3 (threshold form):** Threshold should be expressed as a rate band with a variance ceiling, not a count. "≥N receipts" should become "mean inter-receipt interval within [L, U] sprint cycles, variance below V" for per-pillar calibrated L, U, V.

**#5 (consequence framing):** The spec's observation that "a subsystem that cannot find contradictions to surface is a subsystem whose self-observation has gone blind" (lines 464-465) needs a dormancy carve-out. The consequence of silence should be conditional on whether silence is within the per-pillar dormancy tolerance band, not applied uniformly.
