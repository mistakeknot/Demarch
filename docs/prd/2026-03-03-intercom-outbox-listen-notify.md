# PRD: Postgres Outbox + LISTEN/NOTIFY for Intercom Message Delivery

**Bead:** iv-nt43u | **Priority:** P1 | **Effort:** ~6 days
**Parent Epic:** iv-83du3 (Intercom message delivery reliability)

## Problem

Intercom's Node→Rust message bridge silently loses messages. The current `dualWriteToPostgres()` fires HTTP POSTs with a 3s timeout, logging failures at `debug` level. Combined with 1-second polling, this creates a system where messages can be lost without any error indication and delivery latency is artificially floored at 1 second.

**Impact:** Users send messages that never get a response. The system provides no indication that anything went wrong. This undermines trust in the platform.

## Solution

Replace fire-and-forget HTTP dual-writes with a Postgres outbox pattern, and replace 1-second polling with LISTEN/NOTIFY event-driven wakeup.

## Features

### F1: Outbox Table Schema
**What:** Add `message_outbox` table to Postgres `ensure_schema()` with JSONB payload, status tracking, retry counting, and error recording.

**Acceptance criteria:**
- Table created automatically on intercomd startup via `ensure_schema()`
- Supports `pending`, `processing`, `delivered`, `failed` status transitions
- Index on `(status, created_at) WHERE status = 'pending'` for efficient drain queries
- NOTIFY trigger fires `intercom_outbox` channel on INSERT

### F2: Node Direct Postgres Writer
**What:** Node host connects directly to Postgres and writes incoming messages to the outbox table instead of HTTP POST to intercomd.

**Acceptance criteria:**
- Node reads `INTERCOM_POSTGRES_DSN` from environment (same DSN as intercomd)
- Single `pg.Client` connection with automatic reconnect (exponential backoff, 1s→30s)
- `storeMessage()` and `storeChatMetadata()` write to outbox instead of calling `dualWriteToPostgres()`
- SQLite write still happens first (backward compatible, removed in Phase 3)
- If Postgres is unavailable, falls back to SQLite-only with WARN log (not debug)
- Connection health exposed via existing `/healthz` or similar

### F3: Rust Outbox Drain Loop
**What:** intercomd drains the outbox using atomic claim pattern (`SELECT FOR UPDATE SKIP LOCKED`) and processes each row by inserting into the appropriate destination table.

**Acceptance criteria:**
- Claims up to 10 pending rows per drain cycle (configurable via `intercom.toml`)
- Each claimed row: parse `payload_type`, deserialize JSONB, INSERT into destination table (`messages` or `chats`)
- On success: mark `delivered`, set `delivered_at`
- On failure: increment `attempts`, set `last_error`. After 5 failures: mark `failed`
- Failed rows don't block other messages (per-row error handling)
- Runs as a new background loop alongside existing message_loop

### F4: LISTEN/NOTIFY Integration
**What:** intercomd maintains a dedicated Postgres connection for LISTEN on the `intercom_outbox` channel. On NOTIFY, immediately triggers an outbox drain.

**Acceptance criteria:**
- Dedicated connection separate from the main PgPool (LISTEN requires holding a connection)
- On connection drop: reconnect with exponential backoff (1s, 2s, 4s, 8s, 16s, 30s cap)
- 30-second fallback poll catches any missed notifications during reconnect window
- LISTEN loop runs as a new background task, sends drain signal to outbox drain loop via tokio channel
- Graceful shutdown via existing `watch::Receiver<bool>`

### F5: Message Loop Migration
**What:** Replace `poll_once()` in `message_loop.rs` with outbox-driven dispatch. The outbox drain feeds directly into the existing GroupQueue.

**Acceptance criteria:**
- `poll_once()` no longer queries `get_new_messages()` — messages arrive via outbox drain
- Per-group agent timestamp tracking (`AgentTimestamps`) preserved for accumulated context
- `recover_pending_messages()` still runs on startup (now reads from outbox 'pending' rows too)
- Existing group queue dispatch (trigger checking, context accumulation, container piping) unchanged
- Fallback: `orchestrator.use_outbox` config flag to toggle between outbox and legacy polling (default: true)

### F6: Outbox Cleanup
**What:** Periodic cleanup of delivered outbox rows to prevent unbounded table growth.

**Acceptance criteria:**
- Runs every 1 hour (or configurable interval)
- Deletes rows where `status = 'delivered' AND delivered_at < now() - interval '7 days'`
- Logs count of deleted rows at INFO level
- Does not delete `failed` rows (these need manual investigation)

## Non-Goals (This Phase)

- **Reverse outbox (Rust→Node):** Response delivery from containers to Telegram still uses HTTP callback. Addressed in future phase.
- **SQLite removal:** Node keeps writing to SQLite. Removed in Phase 3 (iv-sjz6t).
- **Container IPC changes:** Stdout marker parsing stays. Addressed in Phase 2 (iv-fkq60).
- **Multi-instance support:** Single-instance deployment only. `SKIP LOCKED` already handles concurrent access but no active-active testing.

## Technical Design

### Data Flow (After)

```
Telegram message arrives
    ↓
Node: storeMessage() → SQLite INSERT (primary, kept for Phase 1)
    ↓
Node: pg.Client → INSERT INTO message_outbox (chat_jid, 'message', {...})
    ↓
Postgres: NOTIFY intercom_outbox trigger fires
    ↓
Rust: LISTEN loop receives notification
    ↓
Rust: Outbox drain claims pending rows (SELECT FOR UPDATE SKIP LOCKED)
    ↓
Rust: Parse payload, INSERT into messages table
    ↓
Rust: Check trigger, enqueue to GroupQueue (existing path)
    ↓
Container dispatch + response delivery (unchanged)
```

### File Changes

| File | Change |
|------|--------|
| `intercom-core/src/persistence.rs` | Add `message_outbox` table to `ensure_schema()`, add outbox query methods |
| `intercomd/src/outbox.rs` (new) | Outbox drain loop, LISTEN/NOTIFY integration |
| `intercomd/src/main.rs` | Spawn outbox drain + LISTEN tasks |
| `intercomd/src/message_loop.rs` | Add config flag to skip legacy polling when outbox is active |
| `src/db.ts` | Replace `dualWriteToPostgres()` with direct Postgres outbox INSERT |
| `src/pg-writer.ts` (new) | Postgres client wrapper with reconnect logic |
| `config/intercom.toml` | Add `orchestrator.use_outbox` flag |
| `package.json` | Add `pg` dependency |

### Migration Path

1. Deploy outbox schema (zero-downtime: just adds a table and trigger)
2. Deploy Rust outbox drain + LISTEN loop (runs alongside existing polling)
3. Deploy Node Postgres writer (messages now go to outbox AND legacy HTTP)
4. Verify outbox delivery works end-to-end
5. Set `use_outbox = true` to disable legacy polling
6. Remove `dualWriteToPostgres()` from Node

Each step is independently deployable and reversible.

## Success Metrics

- **Zero message loss:** Every message written to outbox reaches the `messages` table and triggers dispatch
- **Latency < 200ms p95:** Time from Node outbox INSERT to Rust drain (target: ~50ms via NOTIFY)
- **Crash resilience:** Kill intercomd mid-processing → on restart, pending outbox rows are re-processed
- **Operational visibility:** Outbox pending count, drain latency, and failure count logged and queryable
