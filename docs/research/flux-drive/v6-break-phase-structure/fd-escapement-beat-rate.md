---
agent: fd-escapement-beat-rate
source_domain: 19th-century Kew Observatory chronometer regulation — escapement beat-rate, daily rate journal, isochronism, bench-trial
decision_lens: Is the Break phase a Kew Observatory bench-trial (discrete pass/fail at a 45-day boundary) or the continuous beat-error and rate-residual record (sustained-mode metric in which any single reading is meaningless)?
track: C (Distant — structural isomorphisms)
date: 2026-05-06
target_decision: §7.1 Break phase — gate-vs-continuous
---

# fd-escapement-beat-rate — Findings

## The Central Isomorphism

The Kew Observatory Certificates of Rating (issued from 1884 to the 1930s) represent the highest external validation available to a marine chronometer. To receive a certificate, a chronometer had to complete a 45-day trial across five temperature bands and demonstrate daily rate within prescribed tolerances. A passed trial produced a certificate.

The regulator's practice, however, was never the trial alone. Every chronometer kept at a workshop maintained a **running journal** — a continuous record of daily rate (seconds gained or lost per 24-hour period), recorded morning and evening, annotated with temperature and any adjustment events. The journal was the working instrument. The Kew trial was a terminal proof that the journal's preparation had been adequate.

Two properties the Kew system distinguished, which the certificate alone could not:

1. **Beat-error**: the asymmetry between the tick and tock of the escapement — the difference between the duration of the impulse to the balance on one swing versus the return. Measured as a continuous waveform at the bench. High beat-error means the escapement is not symmetrically releasing energy; the chronometer may still keep daily rate within tolerance *on average* but has elevated susceptibility to positional error (changes in orientation relative to gravity) and temperature excursion.

2. **Isochronism**: the property of keeping the same rate at all amplitudes of the balance oscillation. A balance that runs fast at high amplitude and slow at low amplitude is not isochronous. The chronometer may keep rate in a climate-controlled room (where amplitude is stable) and fail in service (where temperature excursions and positional changes vary the amplitude). The Kew trial crossed temperature bands precisely to stress-test isochronism — a discrete methodology for probing what is fundamentally a continuous property.

The failure mode for a non-isochronous chronometer: it passes the Kew trial (which is conducted under controlled conditions) and fails in service (where conditions vary). A navigator relying on a Kew-certificated chronometer that was not isochronous would accumulate dead-reckoning error that could be fatal.

§7.1's Break gate is a Kew trial specification without the running journal or the isochronism test.

---

## P0 — Gate Model Imposed on an Isochronism Property

**Mechanism name: Kew-without-isochronism**

**Location:** `docs/sylveste-vision.md` lines 456-465, specifically: "A subsystem cannot enter Epoch unless it has logged ≥N Break receipts in its Compound window."

Self-observation health is, at its core, an isochronism property: does the pillar surface contradictions at a consistent rate across varying operating amplitudes (high-load sprints, low-load maintenance periods, edge-case stress events, ordinary steady-state)? A pillar that surfaces contradictions reliably only under high-load conditions is not exhibiting self-observation as a stable faculty — it is exhibiting a load-dependent response that will fail under low-amplitude conditions, exactly as a non-isochronous balance fails when the operating temperature changes.

The ≥N gate does not test across operating amplitudes. A pillar could accumulate all N receipts during a single high-load sprint cycle (the equivalent of a chronometer kept at high amplitude for the entire trial) and clear the gate. In service — during steady-state operation, under low-amplitude sprint regimes — the self-observation rate collapses.

**Concrete failure scenario:** The lattice pillar (Interweave/lattice) is under active development for six of its eight Compound sprint cycles, then enters a maintenance steady-state. During the active phase, it surfaces N Break receipts naturally (high-load generates many internal contradictions). During steady-state, contradiction density drops. Break gate clears. Epoch arrives. Under Epoch conditions (new architecture migration), the pillar's operating amplitude is again high but in an unfamiliar domain. The self-observation faculty that appeared robust during active development was amplitude-dependent, not isochronous. The navigator has an error in position.

**Smallest viable fix:** Require Break receipts to be sampled from both high-load and low-load operating windows, not just from the Compound window in aggregate. The minimum specification: "≥N/2 Break receipts drawn from sprint cycles where the pillar's Interspect gate-pass rate was below its Compound median (low-load regime) and ≥N/2 from cycles above the median." This directly tests isochronism — does the self-observation function at low amplitude as well as high?

---

## P1 — No Beat-Error Equivalent in the Receipt Cadence

**Mechanism name: Missing beat-error measurement**

**Location:** `docs/sylveste-vision.md` lines 456-465 (Break definition).

Beat-error is measured by comparing the tick interval against the tock interval on the same escapement. A perfect escapement has tick = tock; the asymmetry is the error. The regulator measures this directly with a beat-rate tester or an electronic timer on the bench — it is a feature of the escapement's regularity, not of its average rate.

For Break receipts, the equivalent: the temporal regularity of receipt arrival within the Compound window. Two pillars may produce the same mean inter-receipt interval but radically different beat-error:

- Pillar A: receipts at intervals of 3, 3, 4, 3, 3 sprint cycles — low beat-error, regular escapement
- Pillar B: receipts at intervals of 1, 1, 12, 1, 1 sprint cycles — high beat-error, asymmetric escapement that is regularly irregular

These are indistinguishable by count. Pillar B's high-beat-error pattern indicates an escapement that regularly enters long-silence states — potentially a healthy soak period (the burst after a long quiet), or potentially an early sign of a sticky pallet that will eventually fail to release the train entirely.

**Concrete failure scenario:** Ockham's dispatch logic shows a beat-error pattern in Break receipts: short bursts of self-observation followed by long silences, cyclically. The ≥N gate passes repeatedly because count is satisfied. A regulator reviewing the running journal would immediately flag the asymmetric beat as a watch item: the escapement is not holding energy uniformly. When the long-silence phase extends — as sticky-pallet problems compound over time — the self-observation faculty fails entirely. The gate never saw it coming because it was reading count, not interval regularity.

**Smallest viable fix:** Add a beat-error metric to the Break receipt record: the standard deviation of inter-receipt intervals across the Compound window, normalized to the mean interval. Flag as a watch item if the coefficient of variation exceeds a calibrated threshold. This does not block Epoch transition (that would require calibration first) but feeds Tier-2 evidence about self-observation health per the option b framing.

---

## P2 — Compound Window Not Paired with Running-Journal Record

**Mechanism name: Kew trial without the regulator's journal**

**Location:** `docs/sylveste-vision.md` lines 453-465 (Compound + Break definitions).

The spec implicitly treats the ≥N Break receipts as the complete record — a Kew trial. But Kew trials were meaningful because the running journal preceded them. The journal is what a regulator reads to understand trend: is the daily rate improving, stable, or drifting? Is the temperature coefficient of rate increasing (a sign of spring fatigue)? Is the long-term trend toward gaining or losing?

For Break receipts in the continuous-mode variant (option b), the equivalent is a running journal of receipt rate per sprint cycle, maintained throughout Compound — not just the cumulative count at window's end. The option b framing mentions that "rate becoming Tier-2 evidence about self-observation health" but does not specify the running record that would make the rate trend readable.

Without the running journal, rate-as-evidence is a derived assertion ("the rate was sufficient") rather than an auditable trace ("the rate was X in cycles 1-5, Y in cycles 6-10, trending toward Z"). The difference is whether an operator can diagnose a drifting trend before it becomes a gate failure, or only discover it at the gate.

**Implication for downstream call #3 (threshold form):** The threshold should not be expressed as a count or a summary rate; it should reference a rate trend from the running journal. "Rate above threshold for ≥W consecutive sprint cycles, with no downward trend exceeding T%/cycle" would be a journal-grounded threshold.

---

## P2 — Interspect Adjustment Events Not Recorded with Projected Steady-State Effect

**Mechanism name: Adjustment without settlement**

**Location:** `docs/sylveste-vision.md` lines 456-460 (Break scoring).

When a regulator adjusts a chronometer — moves the regulator index, alters the beat-error, corrects the mean-time screw — the running journal records: the immediate effect (rate changed from +3s/day to +0.5s/day) and the projected steady-state effect (expected rate after 48-hour thermal settlement: +1s/day). The adjustment event is not complete until the settlement observation confirms the adjustment held.

When Interspect scores a Break receipt and adjusts its model of a pillar's self-observation health, it is making a calibration event. The spec does not require that this event record both the immediate effect (new evidence weight) and the projected effect (expected impact on future receipt scoring). Without the settlement record, Interspect adjustments are "adjustments without confirmation" — a regulator who turned the mean-time screw and forgot to check the rate 48 hours later.

---

## Stance on Gate vs Continuous

The chronometer regulation tradition answers the gate-vs-continuous question by preserving both and specifying their relationship precisely:

1. The continuous running-journal record is the instrument. It is always active. Without it, the trial means nothing.
2. The bench trial (Kew) is a discrete proof event, conducted under controlled conditions, that certifies the running journal's preparation was adequate.
3. The trial result does not replace the journal. A certificated chronometer still runs a daily journal in service.

Applied to Break: the continuous-mode requirement (option b — rate as Tier-2 evidence) is the running journal; the discrete gate (option a — ≥N receipts) is the bench trial. **The bench trial does not replace the journal; it follows from it.** A Break gate that triggers on ≥N receipts without a prior continuous rate record is a Kew trial conducted without the prior journal — the certificate is uninterpretable.

The isochronism finding is the deepest contribution: a pillar that maintains self-observation rate under one amplitude and fails under another is not isochronous. The Kew trial's multi-temperature protocol was specifically designed to test isochronism — to stress the chronometer across amplitudes. §7.1's Break phase lacks the amplitude-variation equivalent. This is not a minor calibration question; it is the central design decision about what Break is meant to certify.

---

## Implications for Downstream Calls

**#2 (who scores):** Interspect adjustment events (re-scorings of Break receipts, updates to severity models) must be logged with both immediate and projected steady-state effect. Without settlement records, the scoring instrument's behavior is opaque.

**#3 (threshold form):** The threshold should be expressed against the running journal, not as a terminal count. "Rate-above-threshold for ≥W consecutive cycles, confirmed by beat-error metric below V" is a journal-grounded threshold that tests isochronism.

**#5 (consequence framing):** Epoch transition is the analog of the chronometer entering service after the Kew trial. The running journal does not stop at Epoch — it continues, now under Epoch conditions. The spec should specify that Break-receipt rate monitoring continues through Epoch (not just through Compound), and that Epoch conditions constitute the amplitude-variation test that the Compound window may not have supplied.
