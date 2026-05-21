---
agent: fd-atc-surveillance
source_domain: Air traffic control — IFR clearances; Secondary Surveillance Radar (SSR Mode C/S); TCAS Resolution Advisories; ICAO Annex 11 (Air Traffic Services); FAA Order 7110.65 (Air Traffic Control)
decision_lens: Clearance (one-time gate authorizing corridor entry) vs surveillance loop (continuous verification that the cleared aircraft is maintaining its authorized corridor); pre-radar procedural control vs radar separation assurance
reviewed: 2026-05-06
target_passage: sylveste-vision.md §7.1 lines 456–465 (Break phase spec)
---

# ATC Surveillance Review — §7.1 Break Phase Structure

## Stance on Gate vs Continuous

**Continuous surveillance is structurally mandatory for high-criticality subsystems; clearance-only is acceptable only in low-density, low-consequence airspace.**

An IFR clearance authorizes entry into a protected corridor. It is issued after the controller has verified that the aircraft meets the conditions for corridor entry — equipment, certification, current position, intended route. The clearance is a gate: pass the conditions, receive authorization.

But a clearance is not separation assurance. Separation assurance is provided by the surveillance loop: secondary surveillance radar (SSR Mode C/S) returns a position and altitude squawk every 12 seconds; the controller verifies that the aircraft is maintaining its cleared corridor throughout the flight, not just at corridor entry. The clearance authorizes; the surveillance loop verifies. They are structurally different instruments with different operational roles.

Pre-radar ATC — procedural control, used in oceanic airspace and remote areas today — operated on clearances alone: aircraft reported positions at defined waypoints (position reports), and controllers maintained separation by planning. Procedural control works when traffic density is low, position report intervals are defined and enforced, and the consequences of position deviation are recoverable before the next report. It fails — catastrophically — when traffic density exceeds the controller's ability to maintain situational awareness from position reports alone, or when position deviation occurs between reports with no intermediate detection.

The Break phase as specified — ≥N receipts before Epoch — is procedural control. The gate is the IFR clearance: it authorizes Epoch entry. But once the clearance is issued, there is no surveillance loop. The subsystem's position in "contradiction-surfacing corridor" is not tracked between Compound exit and the next Epoch trigger. The specification is operating a pre-radar control paradigm for a system where the consequences of undetected deviation are non-trivial.

---

## P0 Finding — Break Gate Provides Clearance to Epoch Without a Surveillance Loop; No Mechanism Detects Post-Entry Corridor Deviation

**Severity: P0**

**Location:** `docs/sylveste-vision.md` lines 456–470 — Break phase spec (456–465) followed by Epoch phase spec (466–470). The Epoch spec defines when Epoch is triggered (§7.11) and what happens at trigger (re-demonstration at current tier), but specifies no ongoing surveillance mechanism equivalent to SSR during the Epoch corridor.

**The failure scenario:** Subsystem accumulates N Break receipts during Compound, receives its clearance to Epoch. It enters the Epoch corridor. Between Epoch entry and the first Epoch trigger (which fires only on defined events: "major model API change, architecture migration, subsystem replacement" — §7.1 lines 466–468), the subsystem's self-observation mechanism degrades. It stops surfacing contradictions. No Epoch trigger fires because none of the defined trigger events occur. The subsystem operates in Epoch for an extended period with effectively blind self-observation, trust maintained by the §7.3 decay model which does not account for Break-silence anomalies.

The structural failure is that the clearance (Break gate result) is being used as ongoing separation assurance — the same error that procedural control makes when position reports are late or absent. In ATC terms: the aircraft filed a flight plan, received a clearance, reported departure, and then went radio-silent. Without radar, the controller doesn't know where the aircraft is. With radar, the deviation is visible at the next scan (12 seconds).

**What breaks:** The §7.1 text states "without Break, confident subsystems accumulate compounding evidence in only their own favor" (lines 463–465). This is precisely the Epoch failure mode: a subsystem that earned the Break clearance on the basis of active Compound-phase self-observation, then coasted through Epoch on that clearance, accumulating positive Epoch evidence (Interflux findings, gate pass rates) with no contradiction-surfacing. The compounding operates in Epoch just as it would without Break at all — because Break stopped operating the moment the clearance was issued.

**Smallest viable fix:** Add a surveillance loop specification to §7.1 immediately after line 470: "A subsystem in Epoch is under Break-equivalent surveillance: Interspect monitors the subsystem's contradiction-surfacing rate against the rate established in its Compound window. A Compound-equivalent rate drop (defined as [X]% below the established rate for [Y] consecutive observation sub-periods) generates a Break-deviation alert, escalated to Ockham for review. This surveillance loop operates between Epoch triggers, not only at Epoch trigger events." This converts the Epoch phase from clearance-inherited to surveillance-loop-maintained — the radar upgrade from procedural to radar separation.

---

## P1 Finding — Break Receipts Are Not Required to Be Temporally Distributed; Burst Position Reports Do Not Demonstrate Sustained Navigational Accuracy

**Severity: P1**

**Location:** `docs/sylveste-vision.md` line 459: "...logged ≥N Break receipts in its Compound window." No temporal distribution requirement is specified.

**The failure scenario:** FAA Order 7110.65 requires that IFR aircraft on procedural control (no radar) file position reports at defined compulsory reporting points throughout the route — not just at departure and destination. A position report at departure and destination satisfies the filing requirement but provides no information about whether the aircraft was in its cleared corridor at any intermediate point.

The Break gate equivalent: a subsystem files all N receipts in a single sprint (departure position report), then goes silent for the remainder of the Compound window (no intermediate reports), and files no further receipts before gate evaluation (destination position report). The gate is satisfied — N receipts were logged. But the controller has no situational awareness of what happened between sprint 1 and the gate evaluation. The subsystem's self-observation behavior throughout Compound is invisible; only the sprint-1 burst and the final gate count are known.

In high-density airspace (Class A/B equivalent: M3+ governance and routing subsystems), procedural control separation standards are several times larger than radar separation standards precisely because the controller cannot detect between-report deviations. If the Break spec is procedural-control-equivalent, the effective trust buffer must be correspondingly larger — or the spec must require position reports (temporal distribution of Break receipts).

**What breaks:** The trust lifecycle's stated purpose is to provide evidence that compounds per-subsystem (vision §0, line 14). A burst of Break receipts in sprint 1 provides evidence that the subsystem was self-observing in sprint 1. It provides no evidence about sprints 2 through N. The compounding claim is not supported by the gate-without-distribution structure.

**Smallest viable fix:** Add a position-report requirement at line 459: "Break receipts must be distributed across the Compound window: at least one qualifying receipt must be logged in each [defined observation sub-period]. A sub-period in which zero qualifying receipts are logged generates a position-report gap, recorded as a Break-health anomaly. Three consecutive position-report gaps generate a Break-health review by Interspect." This is the procedural control position-report requirement transposed to the Break spec — it does not require full radar (continuous monitoring) but establishes a minimum reporting cadence that provides intermediate situational awareness.

---

## P2 Finding — Epoch Trigger Inherits Break Clearance Without Radar Handoff Protocol; Surveillance Baseline Is Not Re-Established Under New Conditions

**Severity: P2**

**Location:** `docs/sylveste-vision.md` lines 466–470: "When environmental conditions shift — a major model API change, an architecture migration, a subsystem replacement — trust is partially reset. The subsystem retains its maturity tier but must re-demonstrate at that tier under new conditions."

**The failure scenario:** In ATC, a sector handoff — when a flight transitions from one controller's sector to another — requires explicit re-establishment of surveillance contact. The receiving controller verifies the aircraft's position on their radar, confirms the squawk code, and takes formal control. The previous sector's clearance and radar track do not carry over automatically; they are the briefing for the handoff, not the handoff itself. The new controller must independently confirm position before assuming responsibility for separation.

The §7.11 Epoch trigger is a sector handoff: changed environmental conditions require the subsystem to re-demonstrate. But §7.1 does not specify whether the Break evidence from the previous Compound window carries over to the new Epoch sector or must be re-established. "Re-demonstrate at that tier under new conditions" (line 470) presumably requires new positive evidence — but does it require new Break evidence? If the previous Break clearance carries over, the new sector has inherited a trust baseline that was established under conditions that no longer hold.

Post-architecture-migration, a subsystem's self-observation mechanisms may need to be retested against the new substrate. The contradiction-surfacing rate established in Compound was calibrated against the pre-migration environment. A handoff that inherits the pre-migration Break clearance without establishing a new Break baseline is a controller assuming separation responsibility without confirming the aircraft's current position.

**Smallest viable fix:** Add to §7.11 (Epoch trigger rubric) — or if not specified in this passage, add a clause to §7.1's Epoch spec after line 470: "An Epoch trigger that involves a substrate, architecture, or model change resets the Break baseline: the subsystem must establish a new Break receipt rate against the new substrate before its Epoch clearance is renewed. Until the new Break baseline is established, the subsystem operates at provisional Epoch status with reduced gate-tier authority (§7.X provisional authority rubric)." This is the radar handoff protocol: don't inherit; re-confirm.

---

## Implications for Downstream Calls

**Call #2 (scoring):** The ATC lens adds a criticality-based airspace classification to the scoring framework. Class A/B equivalent (M3+ governance, routing, kernel) must be scored under continuous surveillance requirements; Class G equivalent (M1–M2 non-critical) can use procedural-control position-report cadence. This is complementary to the nuclear maintenance rule's a-category/b-category distinction — both arrive at a tiered requirement based on consequence.

**Call #3 (threshold form):** The position-report cadence requirement (P1 fix) is the threshold form recommendation from this lens: a minimum distribution requirement per observation sub-period, not just a total count. This aligns with all four Track B agents' threshold form recommendations.

**Call #5 (consequence framing):** Break-deviation alerts (P0 fix) should be framed as TCAS RA equivalents: they are generated by continuous surveillance, override the current clearance status, and require immediate Ockham review — even if the Break gate was formally passed. A TCAS RA is not advisory; it is a resolution advisory that preempts the controller's clearance. The consequence framing should make clear that continuous surveillance can trigger a Break-health review even on a gate-passed subsystem.

---

## Cross-References to Track B

- **fd-nuclear-maintenance-rule:** The a-category/b-category classification maps directly to the ATC Class A/B vs Class G airspace distinction. Both arrive at: high-criticality subsystems require continuous monitoring (radar/a-category); low-criticality subsystems can use periodic inspection/procedural control. The criticality classification is the key design decision, and both disciplines recommend making it explicit and pre-specified rather than uniform.
- **fd-continuous-controls-monitoring:** The CCM zero-receipt floor is the financial equivalent of the ATC position-report gap alert. Both treat silence as a potential instrument failure rather than confirmed health. The operational mechanism is the same: sustained silence triggers a health review, not a health confirmation.
- **fd-postmarket-surveillance:** The pharmacovigilance post-Epoch surveillance obligation (P0) is the same structural gap as the ATC surveillance loop post-clearance (P0 here). Both disciplines converge on: the gate authorizes entry; a separate and ongoing monitoring mechanism verifies continued corridor maintenance. The Epoch-as-clearance-without-surveillance is the core shared finding of Track B.

---

## Summary Verdict

The Break spec is procedural control — clearance-based, appropriate for low-traffic, low-consequence airspace. For M3+ governance and routing subsystems (Class A/B airspace equivalent), procedural control is not adequate separation assurance. The radar upgrade required is: a surveillance loop that verifies the subsystem's self-observation corridor throughout Epoch, triggered by rate deviation rather than only by defined Epoch trigger events. The clearance (gate) remains as the Epoch entry condition — the IFR clearance is still required and meaningful. But the clearance without the surveillance loop is a pre-radar control paradigm that cannot detect the failure mode it was designed to prevent.

**Verdict: Continuous surveillance required for M3+ subsystems; gate-only (procedural control) acceptable for M1–M2 with mandatory position-report cadence.**
