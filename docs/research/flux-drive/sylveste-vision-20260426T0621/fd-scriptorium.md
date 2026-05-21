# fd-scriptorium — Review of sylveste-vision.md v5.0

**Lens:** Carolingian scriptorium master overseeing manuscript reproduction across centuries.
**Decision question:** If Sylveste runs ten years and produces millions of evidence artifacts, can future operators identify which are canonical, which are derived, and which are corrupted descendants of an early bad copy?

## Domain Framing
Monastic scriptoria produced the textual infrastructure of Western Europe by enforcing four disciplines: (1) the master exemplar — one canonical copy in a known location, against which all others are checked; (2) the lineage record — every copy traces its descent from a specific exemplar through identified scribes; (3) the rasura — when a scribe needed to correct text, the correction was visibly different from the original (the parchment was scraped) so corrections could not be confused with corruptions; (4) the colophon — every manuscript ends with attribution, date, and place, embedded in the artifact.

## P0 Findings

### P0-1: No canonical-exemplar discipline for evidence artifacts
The doc's "evidence" is described as accumulating — kernel events, gate outcomes, dispatch results, review findings, human corrections. Nothing in the doc names a master exemplar for any of these. If two sprints produce conflicting evidence about Routing's behavior (one says gate-pass-rate 72%, another says 68% over an overlapping window), what makes one canonical? In a scriptorium, the answer is the master exemplar in the abbey library; in Sylveste, there is no answer.
**Fix:** Designate a canonical store per evidence type with a named location and a write-discipline (single writer, append-only, checksummed). Other stores are explicitly derived; conflicts are resolved by re-deriving from the canonical store.

### P0-2: The cost-baseline lineage is broken at the artifact level
$1.17 (Feb 28 2026) and $2.93 (Mar 18 2026) are reported in the vision. The doc explains the rise as "expanded review scope rather than efficiency regression." This explanation is not embedded in the artifact — it is in the prose around the number. Without an embedded colophon (which fleet, which routing rules, which model versions, which review configuration produced each measurement), neither value is reproducible. Six months from now, no one will be able to reconstruct the conditions that generated $2.93. Two years from now, the number will be a free-floating folk-fact.
**Fix:** Attach a colophon to every published cost measurement: as-of date, fleet snapshot hash, routing-overrides snapshot, model versions, review configuration, sample size. Treat cost values without colophons as informally citable but not authoritative.

## P1 Findings

### P1-1: Evidence-transformation chain has no copy-error discipline
The chain "kernel event → Interspect signal → routing override → outcome measurement" is a multi-stage copy chain. In a scriptorium, every copy stage is checksummed against its source. Sylveste's pipeline has no equivalent: an Interspect signal derived from kernel events has no recoverable proof that it correctly summarized those events. If the derivation logic has a bug, the bug propagates through every downstream measurement.
**Fix:** Each derivation produces (output, source_event_hash_set, derivation_rule_version). Downstream consumers can independently re-derive from the source set; periodic reconciliation runs catch drift.

### P1-2: SQLite-as-system-of-record permits silent overwrite
SQLite tables, by default, support UPDATE. If a sprint's outcome record can be edited, scriptorium discipline is violated — there is no rasura, no visible correction. A bug, a malicious actor, or an over-eager cleanup script could modify history. The doc's "durable system of record" claim does not address whether durability includes immutability.
**Fix:** Distinguish two storage classes — current state (mutable) and history (append-only). Evidence artifacts belong in the second class. Use SQLite triggers or a separate event table to enforce.

### P1-3: 1,456-bead corpus has no exemplar-of-the-exemplar
Beads track work over time, edited as work progresses. The doc cites "1,456 beads tracked, 1,239 closed" as a sign of the system building itself. But beads are mutable; their state at any past time is not preserved. If one wanted to ask "what was the bead corpus on Feb 28 2026 when cost was $1.17?" the answer is reconstructible only from external snapshots or git history of the bead store. The doc treats the bead count as evidence; the evidence has no preserved past form.
**Fix:** Daily/weekly snapshots of bead state, hash-anchored, retained indefinitely. Or move beads to an append-only event-sourced model where past state is reconstructible by replay.

### P1-4: Sprint-output-as-evidence allows no formal correction protocol
A scribe who realized they had made a copy error scraped the parchment and wrote in the correction — the correction was visibly different. Sylveste's sprint outputs (gate decisions, review findings, etc.) can be silently overwritten by re-running. There is no rasura: a deliberate correction is indistinguishable from a silent corruption. The interspect-correction skill exists for routing decisions but is not generalized to other evidence types.
**Fix:** Treat all evidence corrections as new events with a "supersedes" reference, never as edits. Make the correction relation queryable so a forensic reviewer can see what was corrected when by whom.

## P2 Findings

### P2-1: No colophon discipline for review findings
The 589-agent fleet produces findings continuously. Each finding is presumably written somewhere, but the doc doesn't say findings are stamped with the agent's tier-at-time-of-finding, the prompt-version, the model version. Six months later, a finding from a then-stub agent and a finding from a then-proven agent are indistinguishable in the corpus.

### P2-2: Vision-doc-as-canonical needs its own colophon
The vision document itself is dated 2026-04-11, version 5.0. Good. But the underlying claims (cost figures, bead counts, plugin counts, agent counts) are not anchored to a hash or a snapshot — they are just stated. A future reader cannot verify they read v5.0 against a snapshot of the codebase.

### P2-3: External validation citations need preservation
The Symbolica and stigmergy citations are external; the doc cites them now but does not preserve them (no archival URL, no PDF in repo). If the linked papers move or are revised, the doc's external validation evaporates silently.

## Cross-track signal
Converges with **fd-assay-office-hallmarks** on append-only discipline; with **fd-evidence-pipeline-integrity** on attribution-chain integrity; with **fd-trust-mechanics** on what gets logged when humans override.

## Summary
Sylveste produces evidence at scriptorium scale and treats it with manuscript-era casualness — silent overwrite, no master exemplar, no colophons, no rasura. The system that generates the most evidence will be the system that suffers most from missing preservation discipline.
