# Flux-Drive Verdict: mcp_agent_mail Gap Analysis

**Date:** 2026-02-24
**Document Reviewed:** `/home/mk/projects/Demarch/docs/research/research-mcp-agent-mail-gap-analysis.md`
**Reviewers:** fd-architecture, fd-systems, fd-user-product, fd-decisions
**Verdict:** **NEEDS REWORK — Critical issues block adoption**

---

## Executive Summary

The gap analysis is strategically well-scoped and operationally thorough in its comparison, but contains **six critical issues** that prevent adoption of the proposed priority list:

1. **Adoption 2 (Ack Semantics) is already implemented** in intermute. The document misidentifies what exists.
2. **"Maybe" on companion server is a dangerous non-decision** that invites architectural drift without a named trigger condition.
3. **P1/P2/P3 priorities are inverted** — the most concrete need (workflow macros) is rated P2, while speculative future needs (FTS5, contact policy) are rated P1.
4. **Five P1/P2 items lack problem validation** from production Demarch sprints. All justifications are forward-looking or theoretical.
5. **Layer boundary violation hidden in the ack proposal** — Intercore (L1) would query intermute (L1) for gate conditions, creating horizontal coupling that contradicts the document's praise for "mechanism vs policy" separation.
6. **Interspect dependencies are unverified** — the learning loop does not currently read intermute messages, yet FTS5 adoption is justified primarily by future Interspect Phase 2 value.

**Recommendation:** Rework the analysis to start from **observable Demarch coordination failures**, not from mcp_agent_mail's feature set. Resolve the companion server question to a named signpost. Reverse-prioritize to put the only documented need (workflow macros) at P1, and defer speculative items until concrete consumers exist.

---

## Detailed Findings

### P0 — Ack Semantics Already Implemented (fd-architecture)

**Status:** Must fix the document before any implementation work begins.

The gap analysis proposes adding `ack_required` boolean to intermute and a `POST /api/messages/{id}/ack` endpoint as a P1 item. Both already exist:

- `core.Message.AckRequired` at `/home/mk/projects/Demarch/core/intermute/internal/core/models.go:35`
- `MarkAck()` in storage interface at `/home/mk/projects/Demarch/core/intermute/internal/storage/storage.go:33`
- `handleMessageAction` dispatches `ack` vs `read` to distinct event types at `/home/mk/projects/Demarch/core/intermute/internal/http/handlers_messages.go`

**The real gap is narrower:** Intercore's gate system does not currently evaluate `message.acked` as a condition. The wiring is missing, not the schema.

**Layer concern:** If Intercore (L1) begins querying intermute's HTTP API to evaluate gate conditions, two L1 components become directly coupled horizontally. Current gate evaluation is entirely local to Intercore's own state. Pulling in intermute creates an availability dependency at the kernel layer.

**Correct layer for gate integration:** Clavain (L2) should:
1. Watch for sprint-phase transitions
2. Query intermute's ack status via its client
3. Write a gate artifact that Intercore reads

This preserves L1 isolation and keeps policy in L2 where it belongs.

**Action:** Retarget adoption 2 at "integrate intermute ack status as gate condition" with explicit layer-crossing design. Do not add schema or endpoints — wire the existing ones to Intercore gates.

---

### P0 — Companion Server Question Left as Unresolved Non-Decision (fd-decisions)

**Status:** Blocks architectural clarity; invites drift.

The document asks "Should we use mcp_agent_mail as a companion MCP server?" and answers "Maybe, for specific use cases. But this should be a deliberate architectural decision, not drift."

This is exactly the structure of drift: a tool that is "already configured as an MCP server in the Clavain plugin" (true; confirmed in research repo) with a fuzzy boundary condition ("for specific use cases"). The next engineer reading this may treat the companion server as available infrastructure without revisiting the architectural implications.

**The false dichotomy:** The document presents only two options:
- Option A: Don't integrate, cherry-pick 5 ideas
- Option B: "Maybe" use as a companion MCP server

The correct third option: **Defer entirely until Track C Agency Specs design is complete.** The document itself acknowledges P3 items should wait for Track C. Apply the same logic to the companion server decision.

**Recommendation:** Convert "maybe" to a signpost:

> "We defer mcp_agent_mail as a companion server until the Agency Specs design clarifies cross-project coordination requirements. Trigger condition: if any Clavain sprint requires cross-project message routing, revisit this decision. Until then, mcp_agent_mail remains read-only reference for implementation patterns."

Add to AGENTS.md: "Do not add mcp_agent_mail to Clavain plugin MCP server configuration without consulting the keeper of Track C architecture."

---

### P1 — Priority List is Inverted (fd-user-product, fd-decisions)

**Current ranking:**
- P1: Ack semantics (already built), FTS5 search (no current consumer)
- P2: Contact policy (speculative future), Workflow macros (documented need)
- P3: Git archive (expensive, correct deferral)

**North star metric:** "Cost to ship a reviewed, tested change" across autonomy, quality, and token efficiency.

**Actual priority based on north-star alignment:**

**P1 (Do Now):**
- **Workflow macros (currently P2):** Every coordination session today costs multiple sequential MCP round-trips. Each lost context between calls can leave abandoned reservations. This directly increases token cost and failure surface. This is a **measured operational friction**, not speculative.

**P2 (When Consumer Exists):**
- **Ack gate conditions:** The field exists. Defer until a specific gate transition is designed that references `message.acked`. Then the wiring is trivial.
- **FTS5 message search:** Interspect Phase 2 has no concrete design. Interspect's current evidence collection (documented in `lib-interspect.sh`) reads hook events, not intermute messages. Defer until Interspect Phase 2 is scoped.

**P3 (When Topology Changes):**
- **Contact policy:** Within a Clavain sprint, all agents are operator-spawned and trusted. No current runaway message flooding problem. Defer until agent topology grows to multi-project or sub-agent spawning.
- **Git archive:** Architecturally sound deferral; correct P3 rating.

**Also P3:**
- **Message expiry:** The document notes "unbounded growth" as a threat but rates it P3. At current sprint velocity, determine when intermute.db becomes operationally problematic. If the answer is "6 months," pre-position the expiry logic now as a background task. Quantify the trigger.

---

### P1 — No Problem Validation from Production Demarch Sprints (fd-user-product, fd-decisions)

**Signal quality:** The five adoptions are justified with theoretical future states, not observed failures.

No evidence that:
- Any gate transition has failed because a review agent did not acknowledge findings (ack semantics)
- Any operator has been unable to answer a sprint question due to lack of message search (FTS5)
- Any sprint has had runaway message flooding (contact policy)
- Any coordination session has failed due to context loss between MCP calls (the macro case is an exception — this is observable)

**What the analysis should include:**
- A section: "Demarch Coordination Failures Observed" with 2-3 concrete sprint incidents that led to the proposed adoptions
- Or: if no incidents exist, that signals P1/P2 urgency may be inflated and should be downgraded to "research only" until real failures occur

**The sunk-cost dimension:** Having read mcp_agent_mail's implementation makes FTS5 triggers and contact policy state machines feel concrete and low-effort. Items requiring original design work (e.g., Interspect-native message indexing) are invisible because they were never surfaced by the reference system. The cherry-picked items may be survivorship-biased — good ideas that survived because they were already implemented elsewhere, not because they are the best solutions for Demarch's actual problems.

---

### P1 — Interspect Dependencies Are Unverified (fd-systems, fd-user-product)

**Finding:** FTS5 message search is justified with "high leverage for Interspect Phase 2" and rated P1. Interspect does not currently use this.

**Evidence:** Interspect's evidence collection in `/home/mk/projects/Demarch/os/clavain/hooks/lib-interspect.sh` reads:
- Hook events (overrides, agent errors, session signals)
- Sprint artifacts and phase state
- NOT intermute messages

There is no scoped Interspect Phase 2 design that names message mining as a requirement. The claim that "FTS5 is high-impact for Interspect Phase 2" is a forward-inference from an unimplemented feature.

**Also relevant:** FTS5 message mining creates Goodhart's Law risk (fd-systems): Interspect could learn to exclude review agents whose findings are deferred but important, conflating "dismissed" with "irrelevant." This degrades the quality axis that Demarch's frontier depends on.

**Action:** Defer FTS5 to P3. Revisit when:
- Interspect Phase 2 has a concrete design that specifies message mining requirements
- Or: operator observes an actual sprint forensics need that text search would address

---

### P2 — Contact Policy Scope Understated (fd-architecture, fd-user-product)

**Effort assessment:** The document calls this "low-effort guardrail" but the adoption path is understated by 3-4x.

Contact policy with four states (`open`, `auto`, `contacts_only`, `block_all`) plus two-step handshake requires:
- New `contacts` join table (agent_id, contact_id, status, created_at)
- New endpoints: `POST /api/contacts/request`, `POST /api/contacts/respond`, `GET /api/contacts`
- Send handler must join against contacts table before delivering

**Actual effort:** Medium, not low. The table rating is correct; the body prose contradicts it.

**Layer placement:** Correct. Contact policy belongs in intermute (L1 coordination service), not in interlock (L2 driver). This decision is architecturally sound.

**Priority concern:** Within a Clavain sprint, all agents are operator-spawned and implicitly trusted. No current threat model justifies this. Defer to P3 until agent topology changes.

---

### P2 — Workflow Macros Risk Partial-Failure Semantics (fd-architecture)

**Proposal:** Add `join_session` (register + reserve + announce) and `handoff_files` (release + notify + transfer) as compound MCP tools in interlock.

**Architectural concern:** The three operations are currently independent endpoints with clean success/failure semantics. A compound tool that calls them sequentially creates a partial-failure mode that doesn't exist today.

If `register` succeeds, `reserve` succeeds, but `announce` fails:
- The compound tool fails
- But the side effects (agent registered, files reserved) are not rolled back
- The caller receives an error but is in a partially-setup state

**Correct approaches:**
1. Make operations genuinely atomic in intermute (one endpoint, one transaction)
2. Keep individual tools and document the sequence in a Clavain skill with error handling and rollback

**Layer placement:** Skills belong in Clavain L2 policy, not in MCP driver layer. CLAUDE.md states: "Hooks handle per-file enforcement. Skills handle session-level strategic decisions." Coordination sequences are session-level decisions.

**Note:** This is the highest north-star-aligned item (reduces token cost, failure surface), so the effort is worth doing. Just do it in skills, not in MCP server.

---

### P2 — FTS5 Index Size Needs a Cap (fd-architecture)

**Concern:** Proposal recommends indexing `messages.body`. If message bodies contain large content (file diffs, review findings, code snippets), the FTS5 index grows significantly.

intermute uses SQLite with WAL mode. FTS5 virtual tables add shadow tables (`messages_fts_data`, `messages_fts_idx`). Without a maximum body size or a separate fts-eligible column, the index could become a storage bottleneck.

**Recommendation:** If FTS5 is adopted, add one of:
- Maximum body size limit (e.g., 10KB for FTS5 indexing)
- Separate `body_summary` column indexed instead of full body
- Configuration to exclude message bodies above a threshold

---

### P2 — Systems Thinking: Contact Policy + Interspect Creates Reinforcing Exclusion Loop (fd-systems)

**Loop dynamic:** Contact policy (especially `contacts_only` or `block_all` defaults) means certain messages never reach intended recipients. A message was sent and ignored — not ignored because irrelevant, but ignored because it was never delivered.

Interspect, reading an evidence gap for certain agent pairs, interprets absence of correction signals as confirmation that those messages are irrelevant. It proposes reducing those paths further. Over 2 years, progressively prunes agent communication paths that are actually blind spots in evidence collection, not noise.

**Gap in Interspect:** The evidence schema (documented in `docs/interspect-vision.md`) records dismissals and corrections, but does not record "message delivery confirmed, no response generated." This missing event type is the crux of the loop.

**Action:** If contact policy is adopted, Interspect's evidence schema must track delivery confirmation separately from response absence.

---

### P2 — Systems Thinking: Ack Semantics + Gate Conditions Create Deadlock at Scale (fd-systems)

**Balancing loop:** Ack semantics enable efficient event-driven gate blocking. But at scale (multiple concurrent sprints, budget exhaustion, agent crashes), unacknowledged messages cascade upward.

When a review agent reaches token budget mid-sprint:
- Agent stops
- `ack_required` message is not acknowledged
- Ship gate is blocked, permanently
- No recovery path exists unless timeout or human intervention (which undermines autonomy axis)

At L3-L4 autonomy with nested agent spawning, one mid-chain agent failure blocks the entire sprint through gate conditions. The recovery model is not scoped.

**Action:** Before integrating ack semantics as gate conditions, design the recovery semantics for budget-exhausted or crashed agents. Either:
- Implement timeout-based unblocking (which requires message expiry TTL, which is not defined)
- Or: document that human intervention is required (which contradicts autonomy claims)

---

### P2 — Stale Documentation: AGENTS.md Gotcha Entry is Wrong (fd-user-product)

**Location:** `/home/mk/projects/Demarch/core/intermute/AGENTS.md` (line 202, approximately)

**Current text:** "No ack persistence - Ack/read events logged but no status columns updated"

**Actual state:** The SQLite store DOES persist ack status. `RecipientStatus` struct includes `AckAt` timestamp. `MarkAck()` updates the database.

**Risk:** A future agent will read this gotcha and implement duplicate ack persistence logic, creating a conflicting implementation or wasted work.

**Action:** Update documentation immediately. This is a concrete blocking issue independent of all other findings.

---

### P3 — Systems Thinking: Message Expiry TTL Destroys Interspect's Evidence Corpus (fd-systems)

**Pace layer mismatch:** Interspect's learning requires 3+ sessions, 2+ projects, N events of same pattern over months. Evidence that justifies exclusions may span 6+ months.

Message expiry operating on fast TTL (days to weeks) prunes that evidence before the threshold is reached. Pace layer split is structural.

**Hysteresis problem:** Once TTL deletes message history, it cannot be reconstituted. Unlike overrides that can be reverted, deleted messages are a one-way door. Interspect's Phase 3 plan (shadow eval corpus) explicitly requires "real eval corpus, not synthetic tests." TTL-based GC is an architectural threat.

**Tagging problem:** Messages don't know their future importance at send time. The tag mechanism that identifies "Interspect-relevant messages" exempt from TTL is not defined.

**Action:** If message expiry is implemented, coordinate with Interspect phase design. Messages relevant to Interspect must be tagged and preserved. Define the tagging and preservation mechanism before implementing TTL.

---

### P3 — Systems Thinking: Cross-Project Coordination Is a Different System Class (fd-systems)

**Current scope:** Within-project coordination assumes shared trust, shared sprint lifecycle, bounded agent population, single goal.

**Cross-project boundary:** All assumptions dissolve:
- Agent populations open-ended
- Trust not inherited
- Lifecycle heterogeneous (Project A in execute, Project B in review)
- Interspect evidence is project-scoped; cross-project falls outside measurement boundary

**Emergent behavior:** Simple rules at within-project scale (any agent can message any) produce interference patterns at cross-project scale. File reservations are project-scoped; cross-project file access has no current primitive. Phase semantics are incompatible.

**Action:** Do not attempt cross-project coordination until Track C design clarifies the system class boundaries and how within-project primitives compose (or don't) across project boundaries.

---

### P3 — Systems Thinking: Git Archive + WebSocket Real-Time Creates Pace Layer Split (fd-systems)

**Split:** Real-time WebSocket delivery (millisecond timescale) vs. periodic git archival (minute/hour timescale).

**Archive interval as event horizon:** Any event between archive runs exists only in SQLite WAL, not git. More frequent archival = smaller exposure window. But "periodic background job" suggests longer intervals in practice.

**Quiet failure mode:** Archive job failure (silent, background process) degrades eval corpus without alerting. Interspect Phase 3 eval corpus depends on archive reliability.

**Action:** If git archival is adopted, design the integrity guarantees. Either:
- Make archive job visible/monitored (not background-silent)
- Or: implement synchronous archival on critical messages (ack_required, gate decisions)

---

### P3 — Decision Quality: No Smallest Experiment to Validate Before Commitment (fd-decisions)

**Option not considered:** Run mcp_agent_mail locally against one real sprint to observe whether cross-project messaging creates value. This is the lightest commitment that would generate empirical data.

**Alternative validation:** Prototype five cherry-picked items as thin wrappers (e.g., FTS5 script over existing database without schema migration) to validate effort estimates before committing to "small effort."

**Current state:** The document recommends action on P1 items without proposing any learning experiments to validate impact and effort.

**Action:** Before implementation, design one "starter option" experiment per major adoption path. Report results before committing to full implementation.

---

## Summary Table

| Finding | Severity | Category | Recommendation |
|---------|----------|----------|-----------------|
| Ack semantics already built | P0 | Implementation | Fix document; retarget at gate integration layer; do not add schema |
| Companion server is unresolved non-decision | P0 | Decision | Convert "maybe" to named signpost; defer to Track C trigger |
| Priority list inverted | P1 | Prioritization | P1: macros; P2: ack gates, FTS5; P3: contact policy, expiry validation |
| No production problem validation | P1 | Analysis | Add section "Demarch Coordination Failures Observed" before proposing solutions |
| Interspect dependencies unverified | P1 | Scope | Defer FTS5 to P3 until Interspect Phase 2 is scoped |
| Layer boundary violation in gate proposal | P1 | Architecture | Intercore-intermute coupling must go through Clavain L2 policy layer |
| Contact policy scope understated | P2 | Effort estimation | Medium effort, not low; cost of state machine and endpoints well-scoped |
| Workflow macros risk partial-failure | P2 | Layer placement | Implement in Clavain skills with error handling, not MCP compound tools |
| Contact policy + Interspect evidence gap | P2 | Systems thinking | Interspect must track "message delivered, no response" separately from dismissal |
| Ack + gates create deadlock at scale | P2 | Systems thinking | Design recovery semantics for budget-exhausted agents before implementation |
| AGENTS.md stale documentation | P2 | Blocking issue | Update immediately; prevents duplicate implementation |
| Message expiry threatens eval corpus | P3 | Systems thinking | Coordinate preservation mechanism with Interspect Phase 3 before implementing TTL |
| Cross-project is different system class | P3 | Architecture | Defer cross-project work until Track C design clarifies boundaries |
| Git archive + real-time pace layer split | P3 | Systems thinking | Design integrity guarantees; make archive job visible or implement synchronous archival |
| No starter experiments proposed | P3 | Validation | Design one experiment per adoption path; validate before committing |

---

## Highest-Risk Items

**Companion Server Non-Decision (P0):** The document diagnoses that companion server should be "deliberate decision, not drift," then leaves it as "maybe, for specific use cases" with no named trigger. This is structurally identical to drift. **Fix by:** Converting "maybe" to a pre-committed deferral with a clear signpost ("re-evaluate when Track C defines cross-project messaging").

**Gate Boundary Violation (P1):** If Intercore queries intermute for gate conditions, L1-L1 coupling breaks the documented advantage of "mechanism vs policy" separation. **Fix by:** Routing through Clavain L2 policy that queries both systems and writes gate artifacts, preserving L1 isolation.

**Inverted Priorities (P1):** Pushing speculative items (FTS5, contact policy) to P1 while deferring the only documented need (workflow macros) to P2 will result in wasted effort on low-value infrastructure. **Fix by:** Reverse-prioritize based on north-star alignment and problem validation.

---

## Recommended Path Forward

**Before any implementation:**

1. **Resolve the companion server question.** Add to AGENTS.md: "mcp_agent_mail remains research reference. Do not add to Clavain MCP configuration until Track C design is complete."

2. **Fix AGENTS.md documentation.** Update ack persistence gotcha; prevent duplicate implementation work.

3. **Validate problem statement.** Add section "Demarch Coordination Failures Observed" to the gap analysis. If no failures exist, defer P1/P2 items to research-only status.

4. **Reverse-prioritize.** P1: Workflow macros (documented need). P2: Ack gate integration (when gate designed), FTS5 (when Interspect Phase 2 scoped). P3: Contact policy, expiry (when topology changes).

5. **Design layer boundaries.** If ack semantics become gate condition, route through Clavain L2 policy, not direct Intercore-intermute coupling.

6. **Propose starter experiments.** For companion server path and FTS5 adoption, design minimal experiments to validate effort and impact before commitment.

**After rework:**

- Re-submit gap analysis for flux-drive review focusing on revised problem statement and prioritization
- Include decision gates for each P2 item ("urgent when X happens")
- Include systems-level analysis of how proposed adoptions interact with Interspect, gates, and Clavain lifecycle

---

## Reviewers

- **fd-architecture:** Architecture, layer placement, coupling analysis
- **fd-systems:** Systems thinking, feedback loops, pace layers, causal dynamics
- **fd-user-product:** User-centric prioritization, benefit validation, problem discovery
- **fd-decisions:** Decision quality, bias, signposts, starter options

**Generated:** 2026-02-24
