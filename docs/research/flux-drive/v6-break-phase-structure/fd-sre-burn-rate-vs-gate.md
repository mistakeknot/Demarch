# fd-sre-burn-rate-vs-gate — Findings

**Decision lens:** SRE platform engineering. Burn-rate alerts (continuous) vs promotion gates (boundary). The diagnostic question: does a zero-alert window mean nothing went wrong, or that observation went blind?

**Stance:** **Hybrid, with continuous primary and gate as floor.** The §7.1 spec as written (`docs/sylveste-vision.md:456-465`) is structurally a single-shot gate with a count threshold. From an SRE perspective this is the worst of both worlds: it inherits the gate's blindness to mid-window failures and the count's vulnerability to end-of-window catch-up, without the early-detect property of a burn-rate signal. The fix is not to swap one for the other but to make Break receipt rate a Tier-2 evidence stream in its own right (per §7.1's explicit "observational" tier on line 443), with the ≥N count surviving as a non-negotiable floor that cannot be cleared by a single late-window burst.

---

## P1 — Late-window burst clears the gate but violates jo-ha-kyū

**Location:** `docs/sylveste-vision.md:459-460` ("A subsystem cannot enter Epoch unless it has logged ≥N Break receipts in its Compound window.")

**Failure scenario:** A subsystem completes weeks 1-11 of a 12-week Compound window with zero Break receipts. Self-observation has effectively gone silent — no contradictions surfaced, no quarantines opened against own promotion case. In week 12, an external Interspect audit (or a Clavain reviewer's nudge during a sprint reflection) prompts a backfill: the subsystem files N Break receipts in two days, all genuine but all triggered exogenously. Gate passes at week 12 boundary. Subsystem advances to Epoch.

**Why this is P1, not P2:** The brainstorm source explicitly frames Break as "the explicit break where the system must reveal *its own* contradiction" (`docs/brainstorms/2026-04-26-flux-explore-sylveste-flywheel.md:27`). A late-window burst triggered by external prompting is operationally indistinguishable from the counterfeit kyū the design was built to prevent. The gate cannot tell the difference between "self-observation was healthy throughout Compound" and "self-observation was blind for 11 weeks then was kicked into action by a third party." The vision document at line 464-465 stakes the entire legitimacy of the trust lifecycle on this distinction; the gate variant cannot enforce it.

**Smallest viable fix:** Add a temporal-distribution constraint to the gate. One diff hunk in §7.1 around line 460:

> A subsystem cannot enter Epoch unless it has logged ≥N Break receipts in its Compound window, **with no contiguous quiet period exceeding W weeks where W is per-subsystem-specified in the promotion criteria of §7.1**.

This adds a "longest gap" check alongside the count check. A late burst still clears the count but fails the gap test, surfacing the operational signal the count alone cannot.

---

## P1 — Quiet Compound window is indistinguishable from blind self-observation

**Location:** `docs/sylveste-vision.md:464-465` ("a subsystem that cannot find contradictions to surface is a subsystem whose self-observation has gone blind.")

**Failure scenario:** A high-throughput subsystem (e.g., a hypothetical Interspect at M3 reviewing thousands of evidence events per Compound window) genuinely has no contradictions to surface because it is operating cleanly within its current envelope. A low-throughput subsystem (e.g., a niche pillar with sparse activity) has no contradictions to surface because its self-observation channel is broken. Both arrive at Epoch boundary with zero Break receipts. Under the gate variant, both fail the gate identically; under a naive continuous-rate variant, both report rate=0 identically. **Neither variant distinguishes a healthy quiet observer from a blind one.**

**SRE-domain analogue:** A burn-rate alert with zero firings can mean (a) error budget is intact and traffic is healthy, or (b) the metric pipeline is broken and emitting no events. The standard SRE remediation is a **liveness probe on the observation pipeline itself**: a separate signal that confirms the metric collector is alive even when no errors are firing. The Break phase needs the same.

**Why this is P1:** Under either gate or continuous, the design provides no mechanism to distinguish healthy-quiet from blind-quiet. This is exactly the failure mode the line 464-465 framing was supposed to prevent, and the spec as written does not prevent it.

**Smallest viable fix:** Require subsystems to publish a Break-channel heartbeat: a Tier-2 evidence stream that the self-observation mechanism executed (even if it surfaced nothing) at expected cadence. Distinct from filing a Break receipt; analogous to a synthetic monitor versus an organic alert. Add to the promotion-criteria schema in §7.1: `break_channel_heartbeat: <cadence>` per subsystem.

---

## P2 — N is a fixed integer not indexed to subsystem activity volume

**Location:** `docs/sylveste-vision.md:459` (the literal "≥N" constant).

**Failure scenario:** Plugins with operation throughputs differing by 50× share the same N. For a high-throughput subsystem, ≥N is a tick-box. For a low-throughput subsystem, ≥N is a genuine barrier to Epoch advancement. The trust architecture systematically advances active subsystems faster than slower-maturing ones, regardless of whether their actual self-observation health differs.

**Smallest viable fix:** Specify N as a function of the subsystem's evidence volume in the Compound window (e.g., `N = max(N_floor, ceil(α × evidence_count))`), per-subsystem-tuned via promotion criteria, not a global constant. Document this in §7.1 alongside the existing per-subsystem promotion-criteria text on line 449-450.

---

## Implications for downstream calls

- **#2 (who scores):** Interspect's role as severity scorer (line 458) is correct under hybrid but its latency window matters. If Interspect cannot score Break receipts in real-time, the rate signal lags by the scoring queue depth. Recommend: continuous Break-rate signal uses receipt-filed timestamps, not Interspect-scored timestamps, with severity reweighting applied retroactively.
- **#3 (threshold form):** Threshold should be expressed as **(count_floor, max_quiet_gap, heartbeat_cadence)** triple, not a single integer. Hybrid with three orthogonal dimensions is more diagnostically useful than any single threshold.
- **#5 (consequence framing):** Failing the count_floor at Epoch boundary is hard-fail (no Epoch). Failing the max_quiet_gap is soft-fail (Compound window extends; subsystem stays at current maturity). Failing heartbeat_cadence is a Demote signal (§7.1 line 474-477) — observation pipeline is broken, trust must drop.

## Cross-references / anti-overlap

- I am leaving sample-size justification of N to **fd-progressive-delivery-shadow-eval** and **fd-ml-canary-break-rate** (false-promotion rate calculation is their lane). My finding #3 only flags that N is a constant; the question of what N's statistical floor should be is theirs.
- I am leaving the formal liveness-property characterization to **fd-runtime-assurance-break-observability**. My P1 #2 (heartbeat) is the SRE-flavored fix; runtime-assurance will likely frame this as a liveness invariant requiring continuous monitoring.
- I am leaving the gaming-incentive analysis to **fd-spc-break-process-control**. My P1 #1 touches the late-burst behavior but stops at the operational symptom; SPC's lens on inspection-gaming is the deeper diagnostic.
- I am leaving distribution-shift between Compound-evaluation and Epoch-operation to **fd-ml-canary-break-rate**.
