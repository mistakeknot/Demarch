<!-- flux-run-uuid: 3507b048-2a14-484a-ad19-b1066bab6c97 -->
<!-- dispatch-mode: orchestrator-embodied (Task tool unavailable in nested skill context) -->

### Findings Index
- P0 | M-1 | "Initial findings #1 (durable memory)" | Missing accession primitive — no stable ID joins beads/sessions/agents/plugins
- P0 | M-2 | "Design philosophy / 'evidence earns authority'" | Evidence chain breaks at every plugin boundary because there is no shared accession ledger
- P1 | M-3 | "Initial findings #1 + #7" | Memory graduation overwrites prior state — auto-memory promotion is destructive, not append-only
- P1 | M-4 | "Initial findings tier 2 (routing calibration)" | Trust scores surface as confidence numbers without citation backref to evidence
- P1 | M-5 | "Initial findings #2 (parallel fleet + synthesis)" | Synthesis verdicts are not loanable — receiving plugin cannot reconcile findings on return
- P2 | M-6 | "Initial findings #6 (real task tracker)" | No deaccession protocol — when beads close, sessions age out, plugins deprecate, the chain silently breaks
- P1 | M-7 | "Anti-patterns to avoid / structural reframings" | The structural reframing is: 5 of the 7 targets are catalog functions of one missing registrar primitive

Verdict: risky

---

## Summary

The prior pass treats memory, AGENTS.md, observability, task tracking, and synthesis as five separate deprecation targets. From the registrar lens they are all catalog functions of one missing primitive: a registrar — the system that assigns and binds the accession identifier that every other system references. Sylveste's "every action produces evidence" depends on this primitive existing; it does not, and so each plugin invents its own ID space (cass session IDs, bead IDs, agent UUIDs, plugin slugs, hook event IDs). The chain that PHILOSOPHY.md claims as the warrant for authority is broken at every plugin boundary. This is the meta-pattern the prior pass missed.

## Issues Found

### 1. P0 | Missing accession primitive — no stable ID joins beads/sessions/agents/plugins

A museum object carries an immutable accession ID assigned at acquisition. Every conservation report, every loan, every re-attribution joins on that ID. Without it, the chain is uncomputable.

Claude Code has at least seven ID spaces: bead IDs (Demarch-XXXX), cass session IDs, hook event IDs, agent UUIDs, plugin slugs, MCP tool invocation IDs, model dispatch IDs. None is canonical. None is referenced by all the others. interspect events, interstat token records, intertrust scores, intermem auto-memory facts, and interknow patterns each carry one or two IDs but never all the IDs needed to reconstruct the chain.

Failure scenario: A trust score in intertrust drops for an agent. To explain why, an operator needs to walk back: which sessions contributed → which findings → which beads → which artifacts → which hook events → which model dispatches. At each plugin boundary, one ID space ends and the next begins, and there is no join key. The score is correct but unfalsifiable. The "evidence earns authority" principle cannot be enforced because the evidence cannot be reconstructed from records alone.

Fix: A native primitive — call it the `quire` or `accession` — that issues a single ID for any "action that produces evidence" (a tool call, a session, an agent dispatch, a bead transition, a hook event). Every plugin records that ID alongside its own. The ID is the join key for the entire ecosystem. This is not "yet another ID" — it is the registrar primitive that lets the existing IDs be reconciled.

This is the structural reframing the prior pass missed: "every action produces evidence" without an accession primitive is a slogan, not a system.

### 2. P0 | Evidence chain breaks at every plugin boundary

PHILOSOPHY.md states "Every action produces evidence. Receipts, not narratives." But the receipts are not addressable across plugins. cass holds session evidence; beads hold bead-state evidence; interstat holds token evidence; interspect holds routing evidence; intertrust holds trust evidence; interknow holds pattern evidence. None of these can be joined to answer: "what was the full evidence trail behind this routing decision?"

This is exactly the museum failure where conservation reports cannot be matched to accession records. The museum still has the object and still has the reports; what it has lost is the chain that licenses claims about the object. Sylveste has the same problem in software form.

Failure scenario: A user asks Anthropic support: "why did Claude Code route my request to Haiku for this task?" The answer requires walking back from the routing decision to the calibration model to the training events to the original session evidence. With a registrar-grade chain, the answer is a query. Without it, the answer is "no one can reconstruct it."

Fix: Native primitive must surface a `chain_for(any_id)` function: given any artifact ID, return the linked chain of upstream evidence. This is a registrar's basic job — given an accession number, return the full record.

### 3. P1 | Memory graduation overwrites — destroys prior state

intermem graduates auto-memory facts to AGENTS.md/CLAUDE.md. interknow updates pattern authority weights. In museum practice, conservation reports are append-only — never overwriting prior reports, even when later work supersedes them. The chain *is* the appended sequence.

The review treats memory graduation as a positive feature ("auto-graduates stable facts"). From the registrar lens, this is destructive. When the pre-graduation state is lost, the chain that licenses the post-graduation claim is lost too. Six months later, the AGENTS.md fact cannot be falsified because the evidence trail that produced it is gone.

Failure scenario: A graduated AGENTS.md fact turns out to be wrong (model hallucination that survived n graduations). To unwind it, the operator needs to find the original evidence — which session, which agent's claim, what countervailing data was overridden. If graduation overwrites, this is impossible. The AGENTS.md fact is unfalsifiable.

Fix: Memory graduation must be append-only at the persistence layer even if the user-visible AGENTS.md is current-state. Every graduation event records {pre-state hash, post-state hash, evidence-chain, graduation-rule, agent-id, timestamp}. The chain remains queryable indefinitely. Disk is cheap; the chain's integrity is not.

This must be a platform primitive — every plugin that writes durable memory needs to write it append-only or no plugin's chain is trustworthy.

### 4. P1 | Trust assertion without citation

Routing decisions, trust scores, and gate thresholds surface as numbers (0.87 confidence, tier-3 trust, 142ms threshold). Museum attributions cite their evidence — "attributed to Rembrandt, Wetering 2014" not just "Rembrandt." Without the citation, the attribution is unfalsifiable.

intertrust scores, interspect routing decisions, and intercept gate verdicts all behave as the bare attribution. The user sees the number; the evidence is not surfaced unless the user knows the right plugin to query.

Failure scenario: An agent gets routed to Haiku because its trust score dropped below threshold. The user wants to contest this. The trust score has no surfaced citation chain ("dropped because: 3 P1 findings missed in sessions {X, Y, Z}, evidence: {hook events 1-7}"). The user has no path to challenge or correct.

Fix: Native trust/routing/gate primitives must enforce that every score is accompanied by a citation chain accessible from the score. The score is the headline; the chain is the warrant. Make the chain a first-class field, not an implementation detail.

This unifies what intertrust, interspect, and intercept all need separately. One primitive: scored-with-citation.

### 5. P1 | Synthesis verdicts are not loanable

When a museum loans an object, the receiving institution's records and the lender's records must reconcile on return. interflux/intersynth produces synthesis verdicts that other plugins consume — a verdict from flux-drive feeds into clavain:quality-gates, which feeds into landing-a-change, which feeds into ship.

But the synthesis verdict is consumed without a loan record. No ID joins the verdict back to the originating agent findings. If the verdict turns out wrong, no plugin can return to the lender (the agent who produced the finding) and reconcile.

Failure scenario: A clavain:land step proceeds because synthesis returned `safe`. Two days later, a P0 bug surfaces. To trace the failure, the operator needs to walk back from the land event to the synthesis decision to the agent findings to the input the agent received. Without a loan record, the trail breaks at synthesis.

Fix: Synthesis verdicts must carry a loan-record envelope: {verdict, contributing-agent-IDs, finding-IDs cited, dissent recorded, returned-to-lender-on-failure: yes/no, reconciliation-path}.

This makes the parallel-fleet primitive registrar-grade rather than just orchestration-grade.

### 6. P2 | No deaccession protocol

Museums have explicit, board-approved deaccession — never silent deletion. The review does not address what happens when:
- Beads close (their evidence is still referenced by reflect docs)
- cass sessions age out (interstat baselines were computed from them)
- Plugins are deprecated (their patterns are referenced by other plugins)
- Auto-memory facts are demoted (downstream artifacts cited them)

Without explicit deaccession, references silently break. The museum equivalent is the cataloged painting being thrown out without record; everything that cited it points to nothing.

Fix: Native primitive defines deaccession events — every removable artifact emits a deaccession event before deletion, and downstream consumers can subscribe to repair their references. This is the missing closure of the chain.

### 7. P1 | Structural reframing — 5 of 7 are catalog functions of one missing registrar

The prior 7 targets, viewed through the registrar lens:
- #1 (memory) — catalog of facts
- #4 (observability) — catalog of measurements
- #6 (task tracker) — catalog of work
- #7 (managed AGENTS.md) — catalog of conventions
- #2 (synthesis) — catalog of agent findings

All five are *catalog* functions. The missing primitive is the *registrar* — the function that assigns and binds the accession ID that all five catalogs reference. Anthropic ships catalog tools (TodoWrite, AGENTS.md reading) but no registrar. Sylveste's plugins each invent their own.

If the registrar primitive ships, the five catalog plugins consume the same ID space and become composable in a way they currently are not. The deprecation pattern is then: "register the catalog interface against the registrar; let plural catalogs implement."

Failure scenario: Anthropic ships native memory (item #1) without a registrar. Plugin authors immediately write adapters between native memory and bead IDs, between native memory and cass IDs, etc. The integration matrix grows quadratically. Six months later, the same plugins exist with the same problem, just with a new ID space added to the seven.

Fix: Make the registrar primitive #0 — ship it before any of the seven. The seven then ship as catalogs against the registrar, and the deprecation list becomes coherent.

This is the structural reframing the success criteria asked for and the prior pass missed.

## Improvements

1. Decompose "every action produces evidence" into the four registrar functions: assign (issue ID), bind (link to other IDs), append (never overwrite), surface (chain_for(id) query). Make these four the primitive.
2. Audit the existing 7 targets: which assume a registrar that doesn't exist? At least 5 do.
3. Trust/routing/gate primitives must surface the citation chain alongside the score. Treat the score-without-citation pattern as a P1 anti-pattern in PHILOSOPHY.md.
4. Memory graduation persistence layer must be append-only. The user-visible state can collapse; the underlying chain stays.
5. Define deaccession explicitly for each long-lived artifact (beads, sessions, plugins, memories). Silent deletion is a chain break.

--- VERDICT ---
STATUS: fail
FILES: 0 changed
FINDINGS: 7 (P0: 2, P1: 4, P2: 1)
SUMMARY: The missing registrar primitive is the structural reframing: 5 of the 7 prior targets are catalog functions of one absent registrar. Until the registrar primitive ships, "every action produces evidence" is a slogan with broken chains at every plugin boundary.
---

<!-- flux-drive:complete -->
