# Intercom Architecture Redesign — Research Synthesis

**Date:** 2026-03-03
**Research agents:** interdeep:research-planner, interflux:best-practices-researcher, interflux:repo-research-analyst
**Review agents generated:** 5 (fd-delivery-guarantee-model, fd-ipc-transport-design, fd-container-output-extraction, fd-process-boundary-collapse, fd-group-isolation-under-redesign)

---

## Problem Statement

Intercom's dual-process architecture (Node host + Rust daemon "intercomd") has a fragile message delivery pipeline with multiple failure points:

1. **Fire-and-forget dual-writes** — Node writes to SQLite, then HTTP POSTs to Rust Postgres with 3s timeout; failures silently dropped
2. **1-second polling** — Rust polls Postgres every second for new messages; adds latency floor, wastes resources
3. **Docker stdout marker parsing** — Container output extracted by parsing `---INTERCOM_OUTPUT_START/END---` markers from stdout; partial reads and truncation cause silent failures
4. **No delivery guarantees** — Messages can be lost at every hop with no retry or acknowledgment
5. **Multiple network hops** — Telegram → Node → HTTP POST → Rust → Docker → stdout → HTTP callback → Node → Telegram

## Architecture Options Evaluated

### Option A: Keep Dual-Process + Postgres LISTEN/NOTIFY (Recommended)

**What changes:**
- Replace fire-and-forget HTTP dual-writes with a Postgres outbox table + LISTEN/NOTIFY
- Node writes to outbox (INSERT), Postgres fires NOTIFY to intercomd
- Intercomd drains outbox with at-least-once semantics (mark delivered after processing)
- Replace 1s polling with event-driven wakeup; keep fallback poll at 30s for missed notifications

**Why this wins:**
- Lowest implementation risk — both processes stay in their current languages
- No new infrastructure (Postgres already running)
- LISTEN/NOTIFY latency is ~50ms (vs 1000ms polling)
- Outbox pattern provides durability: crashes don't lose messages
- Reversible: can fall back to polling at any time
- Preserves Node's async I/O strength (channels) + Rust's CPU strength (orchestration)

**What doesn't change:**
- Node still owns Telegram/WhatsApp channels (Grammy, Baileys)
- Rust still owns container dispatch, scheduling, queue management
- Per-group isolation preserved via GroupQueue
- Container stdout markers (fix separately, see Option E below)

**Effort:** ~6 days (2d schema + outbox, 2d LISTEN loop in Rust, 1d Node listener, 1d migration)

**Risks:**
- LISTEN/NOTIFY has 8KB payload limit (mitigated: payload is just `{msg_id, chat_jid}`, actual data fetched from table)
- Connection drops can miss NOTIFYs (mitigated: 30s fallback poll catches up)
- Single Postgres connection for LISTEN (mitigated: dedicated connection pool slot)

### Option B: Single-Process Collapse (Rust Absorbs Everything)

**What changes:**
- Rust takes over Grammy Telegram bot, WhatsApp via Baileys equivalent
- SQLite and Node eliminated entirely
- Single Postgres for all persistence
- No IPC — everything in-process

**Advantages:**
- Eliminates all IPC complexity — no dual-writes, no HTTP callbacks, no polling
- Single process to monitor, restart, debug
- Hermes-style simplicity (synchronous message flow within one process)

**Disadvantages:**
- Grammy has no maintained Rust equivalent — would need to use teloxide or grammers
- Baileys (WhatsApp Web protocol) has no Rust equivalent at all
- stream-accumulator.ts (real-time Telegram message editing) is heavily Node-specific
- Summarizer (GPT-5.3 Codex call) would need rewriting
- 4-6 weeks effort for ~10ms latency improvement over Option A
- Not reversible — once Node is removed, going back is a full rewrite

**Verdict:** Too much effort for marginal reliability gain over Option A. The dual-process split is not the core problem; the unreliable bridge is.

### Option C: Single-Process Collapse (Node Absorbs Everything)

**What changes:**
- Node takes over container dispatch (Docker spawning via dockerode)
- Node takes over scheduling (node-cron or custom)
- Rust daemon eliminated
- SQLite becomes sole database (or Node talks to Postgres directly)

**Advantages:**
- Node already handles channels — simpler to add container dispatch than to port channels to Rust
- dockerode is mature for Docker management
- No IPC at all

**Disadvantages:**
- Node's single-threaded event loop is not ideal for concurrent container management
- Rust's per-group queue (GroupQueue with concurrency caps) would need reimplementation
- Loses Rust's type safety and performance for CPU-bound scheduling logic
- SELECT FOR UPDATE SKIP LOCKED (Bug 3) is cleaner in Rust with tokio-postgres than in Node with pg

**Verdict:** Possible but loses Rust's strengths. Not recommended.

### Option D: Durable Message Queue (Redis Streams / NATS)

**What changes:**
- Add Redis Streams or NATS as message broker between Node and Rust
- Node publishes to queue, Rust consumes with acknowledgment
- At-least-once delivery guaranteed by the queue infrastructure

**Advantages:**
- Battle-tested delivery guarantees
- Consumer groups for horizontal scaling
- Built-in retry and dead-letter queues

**Disadvantages:**
- New infrastructure to deploy, monitor, and maintain
- Postgres LISTEN/NOTIFY gives identical guarantees for this use case (< 10k msgs/sec)
- Adds operational complexity (Redis/NATS is another service to crash)
- Overkill for single-instance system processing < 100 messages/day

**Verdict:** Over-engineered for current scale. Reconsider if Intercom needs multi-instance deployment.

### Option E: Container IPC Improvement (Independent of A-D)

**What changes (can be done alongside any option above):**
- Replace stdout marker parsing with Unix domain socket IPC between runner and container
- Container writes output to a UDS mounted as a Docker volume
- Runner reads from socket with framed protocol (length-prefixed JSON)

**Advantages:**
- Eliminates partial-read, truncation, and marker-boundary bugs
- Kernel-level buffering handles backpressure
- Survives container crash (Docker flushes buffered data)
- ~100µs per message vs stdout polling

**Implementation:**
- Mount a tmpfs at `/tmp/agent-ipc/` shared between host and container
- Container creates UDS server, host connects
- Framed protocol: 4-byte length prefix + JSON payload
- Fallback: keep stdout markers as degraded path for containers that don't support UDS

**Effort:** ~3 days

---

## Recommended Implementation Order

| Phase | What | Effort | Impact |
|-------|------|--------|--------|
| 1 | Postgres outbox table + LISTEN/NOTIFY (Option A) | 6d | Eliminates message loss, cuts latency from 1000ms to ~50ms |
| 2 | Container UDS IPC (Option E) | 3d | Eliminates stdout parsing bugs |
| 3 | SQLite retirement | 2d | Removes dual-persistence complexity |
| 4 | Evaluate single-process (Option B) | Future | Only if dual-process bridge still causes issues |

**Total for Phase 1-3:** ~11 days

---

## Key Patterns from Research

### From Hermes (single-process reference)
- **Always-log-local**: Persist task output before sending to remote platform (crash-safe audit)
- **Atomic dispatch exclusion**: File-lock prevents double-execution (Intercom uses SQL FOR UPDATE SKIP LOCKED — better)
- **Delivery target DSL**: "local" | "origin" | "platform:chat_id" — flexible routing (portable pattern)

### From production chat systems
- **Webhook + background processing**: Telegram/Slack/Discord all use: acknowledge webhook immediately (200), process asynchronously, retry delivery
- **Idempotent consumers**: Use external_id (Telegram message_id) as dedup key; INSERT ON CONFLICT DO NOTHING
- **At-least-once over exactly-once**: Accept duplicates, deduplicate on consumer side; distributed transactions are never worth it for chat

### From distributed systems best practices
- **Outbox pattern**: Write intent to outbox table in same transaction as business logic; background worker drains outbox
- **Postgres as queue**: For < 10k msgs/sec, Postgres LISTEN/NOTIFY + outbox is simpler and more reliable than Redis/NATS
- **Fallback polling**: Always keep a slow poll (30-60s) alongside event-driven notification to catch missed events

---

## Generated Review Agents

5 task-specific agents saved to `.claude/agents/`:

1. **fd-delivery-guarantee-model** — End-to-end message delivery contract audit
2. **fd-ipc-transport-design** — Wire-level IPC options evaluation
3. **fd-container-output-extraction** — Container stdout protocol correctness
4. **fd-process-boundary-collapse** — Migration feasibility and rollback safety
5. **fd-group-isolation-under-redesign** — Per-group isolation preservation

Specs saved to `.claude/flux-gen-specs/intercom-architecture-redesign.json`
Regenerate without LLM: `/flux-gen --from-specs .claude/flux-gen-specs/intercom-architecture-redesign.json`

To review the current codebase against these agents: `/flux-drive apps/intercom/`

---

## Sources

- PostgreSQL LISTEN/NOTIFY documentation
- OpenAI Swarm single-process agent orchestration
- Telegram Bot API webhook reliability guide
- SoftwareMill message delivery and deduplication strategies
- PostgreSQL as message broker (vs Redis)
- gRPC over Unix sockets patterns
- Idempotency patterns in stream processing
- Hermes Agent gateway/scheduler source analysis
