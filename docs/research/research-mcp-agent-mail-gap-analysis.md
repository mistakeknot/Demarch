# mcp_agent_mail vs Demarch — Gap Analysis

**Date:** 2026-02-24
**Source:** research/mcp_agent_mail (commit HEAD), Demarch vision docs, intermute/interlock source
**Purpose:** Identify what mcp_agent_mail does that Demarch should be doing (or doing better)

---

## Executive Summary

mcp_agent_mail is a focused, well-designed multi-agent messaging server. Demarch's coordination stack (intermute + interlock) already covers most of the same ground but with a different architecture. The interesting gaps are not "we're missing X" but "they solved X more elegantly" or "they thought about a problem we haven't addressed yet."

**5 things worth stealing. 3 things Demarch does better. 2 things neither does well.**

---

## What mcp_agent_mail Does That We Should Adopt

### 1. Contact Policy (Privacy-by-Default Messaging)

**What they do:** Agents have a `contact_policy` field (`open`, `auto`, `contacts_only`, `block_all`). Before Agent A can message Agent B, there's an explicit handshake (`request_contact` → `respond_contact`). This prevents message spam and gives agents control over their inbox.

**What we do:** Intermute has no contact model. Any registered agent can message any other agent in the same project. Interlock's negotiation protocol is specifically for file release — not general messaging permissions.

**Why it matters for Demarch:** As autonomy increases (L2→L3→L4), agents will spawn sub-agents that spawn sub-agents. Without contact policy, a runaway agent could flood the message bus. More importantly, Interspect's learning loop needs signal quality — if agents can filter out irrelevant messages, the signal/noise ratio improves.

**Adoption path:** Add `contact_policy` field to intermute's `agents` table. Default to `open` for backward compatibility (Demarch agents within a sprint trust each other). Enforce at `POST /api/messages`. Low-effort, high-value guardrail for multi-project scenarios.

### 2. Message Acknowledgment Semantics

**What they do:** Messages can have `ack_required=true`. Recipients must explicitly call `acknowledge_message()`. Unacknowledged messages are visible in inbox queries, creating a persistent "action needed" queue.

**What we do:** Intermute has `ack` and `read` events in the append-only events table, but there's no concept of "this message requires acknowledgment." It's fire-and-forget — the sender has no way to know if the recipient processed the message vs just received it.

**Why it matters for Demarch:** Gate transitions often depend on "did the review agent actually process the findings?" Currently, Clavain polls for completion via sprint state. Ack semantics would let Intercore enforce "review agent acknowledged all findings before Ship gate opens" as a kernel-level invariant, not an OS-level poll.

**Adoption path:** Add `ack_required` boolean to intermute's messages schema. Add `POST /api/messages/{id}/ack` endpoint (distinct from existing `read`). Intercore gates can then reference `message.acked` as a gate condition.

### 3. Full-Text Search Over Messages (FTS5)

**What they do:** SQLite FTS5 virtual table indexing message subjects and bodies. BM25 ranking. Query syntax with phrases, prefixes, boolean operators.

**What we do:** Intermute has no message search. Finding a message requires knowing the thread_id or iterating through inbox cursors. No full-text indexing.

**Why it matters for Demarch:** As sprints accumulate, the message history becomes institutional knowledge. "What did the review agent say about the auth refactor?" requires search. Interspect's learning loop could mine message history for patterns (e.g., "which review findings are consistently dismissed?" requires searching message bodies).

**Adoption path:** Add FTS5 virtual table to intermute.db. Index `messages.body` and `messages.subject`. Add `GET /api/messages/search?q=...` endpoint. Moderate effort, high leverage for Interspect Phase 2.

### 4. Workflow Macros (Compound Operations)

**What they do:** `macro_start_session`, `macro_prepare_thread`, `macro_file_reservation_cycle`, `macro_contact_handshake` — each bundles 2-5 tool calls into one atomic operation. Reduces round-trips and prevents partial setup.

**What we do:** Interlock has individual tools. Starting a coordination session requires: `reserve_files` + `list_agents` + `send_message`. Each is a separate MCP call. If the agent's context compresses between calls, it may forget to complete the sequence.

**Why it matters for Demarch:** Token efficiency is a frontier axis. Each MCP round-trip costs tokens for the tool call + response parsing. Macros reduce this. More importantly, they encode "the right way to do X" — the compound operation pattern from Clavain's philosophy.

**Adoption path:** Add compound tools to interlock MCP server: `join_session` (register + reserve + announce), `handoff_files` (release + notify + transfer reservations). These are thin wrappers, not new primitives — fits the "mechanism, not policy" kernel principle because the macros live in the driver layer (L2).

### 5. Git-Backed Message Archive (Audit Trail)

**What they do:** Every message, reservation, and agent action gets committed to a per-project git repo (`.mcp-mail/`). Messages are stored as YAML+Markdown files. Full `git log`, `git blame`, `git diff` history.

**What we do:** Intermute stores everything in SQLite. The events table is append-only (good), but there's no git-level audit trail. If the database is lost, the history is gone.

**Why it matters for Demarch:** Demarch's philosophy is "durable over ephemeral." The kernel (Intercore) already uses SQLite with WAL mode, which is solid. But git-backed messages would give us: (a) cross-session searchability via standard tools, (b) backup via `git push`, (c) human-readable message history without any tooling, (d) blame/authorship tracking for Interspect evidence.

**Adoption path:** This is the most expensive item. Don't duplicate mcp_agent_mail's dual-persistence approach (SQLite + Git). Instead, consider a lighter version: periodic `git archive` of intermute's message history as a background job. Or: use mcp-agent-mail itself as the archive layer (it's already an MCP server in our stack).

---

## What Demarch Already Does Better

### 1. Real-Time Delivery (WebSocket)

mcp_agent_mail is **poll-based only** — agents call `fetch_inbox` periodically. Intermute has WebSocket real-time delivery (`WS /ws/agents/{agent_id}`). When Agent A sends a message, Agent B gets it immediately via the WebSocket hub broadcast.

**This matters because:** Poll-based coordination adds latency proportional to poll interval. For file negotiation (where Agent B is blocking Agent A), even 5 seconds of polling delay is expensive. Intermute's WebSocket model enables sub-second coordination.

### 2. Kernel/OS Separation (Mechanism vs Policy)

mcp_agent_mail is a monolith — the messaging protocol, file reservations, contact policy, and search are all in one 11K-line `app.py`. There's no concept of separating mechanism from policy.

Demarch's 3-layer architecture means coordination primitives live in the kernel (Intercore), coordination policy lives in the OS (Clavain), and the MCP surface lives in drivers (Interlock). This means you can swap the coordination policy without touching the kernel — e.g., a documentation project could use different file reservation TTLs than a code project.

### 3. Event Sourcing with Cursors

Intermute's append-only events table with cursor-based pagination is architecturally superior to mcp_agent_mail's timestamp-based ordering. Cursors are monotonically increasing integers — no clock skew issues, no ordering ambiguity, guaranteed exactly-once delivery when resuming from a cursor. mcp_agent_mail acknowledges this limitation in their docs ("ordering is by creation timestamp, not strict happens-before").

---

## Gaps Neither System Addresses Well

### 1. Message Expiry / Garbage Collection

mcp_agent_mail explicitly notes "messages archived forever (manual cleanup only)." Intermute has no expiry either. As sprints accumulate over weeks/months, the message store will grow unbounded. Need: configurable TTL per message importance level, with Interspect-grade messages exempt from expiry.

### 2. Cross-Project Coordination at Scale

mcp_agent_mail has cross-project contact requests (`to_agent="project:slug#AgentName"`) but no cross-project message routing or file reservation coordination. Intermute is project-scoped — no cross-project primitives at all. The Demarch vision doc identifies "Multi-Project Portfolio Orchestration" as gap 8.1, with kernel primitives landed but not yet orchestrated.

---

## Recommended Priority

| Priority | Gap | Effort | Impact | Target |
|----------|-----|--------|--------|--------|
| **P1** | Message acknowledgment semantics | Small | High | intermute |
| **P1** | FTS5 message search | Small | High | intermute |
| **P2** | Contact policy | Medium | Medium | intermute |
| **P2** | Workflow macros | Medium | High | interlock |
| **P3** | Git-backed message archive | Large | Medium | new or mcp-agent-mail integration |
| **P3** | Message expiry / GC | Medium | Medium | intermute |

**P1 items** are high-impact, low-effort additions to intermute that directly serve the Interspect learning loop and Intercore gate system.

**P2 items** become important as autonomy increases (more agents, more projects, more unsupervised sprints).

**P3 items** are architecture-level decisions that should wait for the Agency Specs (Track C) design to solidify.

---

## Design Decisions

### Should we integrate mcp_agent_mail directly?

**No.** The architectures are too different to merge cleanly:
- mcp_agent_mail is Python/FastMCP; intermute is Go
- mcp_agent_mail uses dual persistence (Git + SQLite); intermute uses SQLite only
- mcp_agent_mail is poll-based; intermute is WebSocket-first
- mcp_agent_mail is a monolith; Demarch separates mechanism/policy

**Instead:** Cherry-pick the 5 ideas above into the existing Demarch stack. The research clone stays useful as a reference for implementation details (e.g., FTS5 trigger patterns, contact policy state machine, macro composition patterns).

### Should we use mcp_agent_mail as a companion MCP server?

**Maybe, for specific use cases.** It's already configured as an MCP server in the Clavain plugin. For cross-project messaging where intermute's project scoping is too narrow, mcp_agent_mail could serve as a bridge layer. But this should be a deliberate architectural decision, not drift.
