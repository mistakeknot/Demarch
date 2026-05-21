# fd-assay-office-hallmarks — Review of sylveste-vision.md v5.0

**Lens:** London Assay Office hallmark inspector in the Goldsmiths' tradition.
**Decision question:** Would a 1545 hallmark inspector recognize Interspect as a true assay office, or as a goldsmith inspecting his own ingots?

## Domain Framing
A hallmark is a permanent, irrevocable mark stamped into the metal itself by an authority structurally separate from the maker. The hallmark is not a record of intent; it is a record of fact at a moment of assay. A true hallmarking system has four properties: (1) substrate separation between maker and assayer; (2) immutable provenance — once stamped, the mark cannot be silently removed; (3) wardens of the touch — a body higher than the assayer that audits the assayer; (4) a chain of custody for the assay event itself.

## P0 Findings

### P0-1: Maturity advancements are not hallmarks; they are computed values
The doc describes maturity as a state ("M1 Built, M2 Operational") that the system displays in the mesh table. This is a current-state view, not a hallmark log. A 1545 inspector would ask: when Persistence advanced from M1 to M2, where is the stamp recording that event, who witnessed it, and what was the evidence at that moment? The doc has no immutable advancement log distinct from current state. A subsystem that silently demotes can erase its own history; a subsystem that re-promotes can do so without anyone forensically reconstructing the original advancement.
**Fix:** Introduce an immutable hallmark-log table (advancement_events) with: subsystem, from_level, to_level, timestamp, evidence_snapshot_hash, assayer_identity, optional human_witness_signature. Append-only. Demotion writes a new event; it does not edit the prior advancement.

### P0-2: No wardens of the touch — Interspect audits itself
The Goldsmiths' system survived for centuries because it had a higher authority (the Wardens) that audited the assay offices themselves. Sylveste names Interspect as the assayer and explicitly carves it out: "Interspect itself is the one exception — as the assessor, its own maturity is evaluated by human attestation and controlled FluxBench experiments." Today FluxBench is M0/planned. So in practice, Interspect's correctness is currently un-audited. The "human attestation" path is whatever the operator decides.
**Fix:** Either (a) commit to FluxBench M2 as a precondition for Interspect-as-assayer, with a documented fallback during the bootstrap period, or (b) introduce a non-Interspect external check — e.g., a quarterly third-party run that re-derives a sample of recent maturity decisions from raw evidence and flags divergences.

## P1 Findings

### P1-1: Substrate separation is logical, not physical
A real assay office occupies a different building, employs different staff, uses different scales, and follows a different chain of command from the goldsmiths it inspects. Interspect's substrate separation from Intercore is namespace-level only: same SQLite, same process tree, same machine, same operator. If Intercore drops events, Interspect cannot tell. The "structurally independent" claim is asserted at the conceptual level but not at the substrate level.
**Fix:** Either downgrade the claim from "architecturally independent" to "logically independent within the same substrate," or commit to a separate evidence channel (e.g., a separate write-path that mirrors kernel events to a different store, with periodic reconciliation).

### P1-2: Trust transfer protocol does not match the new-master-accepts-old-steel ceremony
When a master goldsmith retires and a new one inherits the workshop, the Goldsmiths' Company runs a formal acceptance: the old steel is verified, the new master's punch is registered, the transition is hallmarked. The doc's Auraken→Skaffen transfer is closer to "probationary access with a verification period" — the form of an acceptance ceremony but not the substance. There is no registered punch, no ceremony of acceptance, no record that survives the transition.
**Fix:** Treat subsystem replacement as a hallmarked event — record (replaced_subsystem, replacement, evidence_at_handoff, probation_window, success_criteria) immutably, with the same dignity as the advancement-events log.

### P1-3: Human authority reservation lacks its own hallmark
"The right to redefine trust criteria remains permanently with humans." Good. But when a human revises a threshold, where is that revision stamped? Is the operator's identity recorded? Can a forensic reviewer five years later reconstruct who changed what when, and why? The principle is named but not instrumented.
**Fix:** Treat threshold revisions as hallmarked events: append-only log with operator identity, prior value, new value, justification text, and (ideally) a co-signer requirement.

## P2 Findings

### P2-1: Maturity-from-the-mesh-table can drift from maturity-from-the-evidence
If two operators with the same evidence both compute maturity, do they get the same answer? The Tier-1/2/3 weights and aggregation function aren't specified (this overlaps fd-evidence-pipeline-integrity). An assay office requires reproducibility — two assayers must independently derive the same fineness. Today, the system likely cannot demonstrate this.

### P2-2: No ceremony for evidence retirement
When evidence ages out, what record survives? The Goldsmiths' system retains records of every assay forever; the question is what counts as currently in force. The doc has no equivalent "currently in force" vs "historically valid" distinction for evidence.

### P2-3: Cross-subsystem hallmark interactions are unaddressed
The interface evidence table (Ontology/Governance, Routing/Measurement, etc.) names cross-cell signals but those signals don't have their own hallmarks. When the "Routing/Measurement attribution chain" passes a check, where is that stamped?

## Cross-track signal
This finding-set converges with **fd-evidence-pipeline-integrity** on the Tier-aggregation-and-versioning gap, with **fd-trust-mechanics** on the unbounded-demotion-latency and trust-transfer-vibe-check issues, and with **fd-scriptorium** on the canonical-exemplar/append-only discipline.

## Summary
Interspect is an assayer without wardens, stamping marks that are not permanent into a substrate it shares with the smiths. The principle of independent verification is correctly named but is not yet instantiated as an institution.
