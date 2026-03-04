# Brainstorm: Postgres Outbox + LISTEN/NOTIFY for Intercom Message Delivery

**Bead:** iv-nt43u
**Date:** 2026-03-03
**Context:** Replace fire-and-forget HTTP dual-writes and 1s Postgres polling with durable, event-driven message delivery between Node host and Rust daemon.

## Problem

The current Node→Rust message bridge has three failure modes:

1. **Silent message loss**: `dualWriteToPostgres()` in `db.ts` fires HTTP POST to intercomd with 3s timeout. If intercomd is down, restarting, or slow, the message is lost forever. Failures logged at `debug` level — invisible in production.

2. **Latency floor**: `message_loop.rs` polls Postgres every 1 second (`poll_interval_ms`). Even when a message arrives instantly, the user waits up to 1s before dispatch begins. Under load with multiple groups, polling wastes DB connections.

3. **No delivery contract**: There's no acknowledgment, no retry, no dead-letter queue. The system is at-most-once: if any hop fails, the message is gone.

## Design Space

### Key Decision: Where does the outbox live?

**Option 1: Node writes outbox to Postgres directly**
- Node gets a `pg` client talking to the same Postgres as intercomd
- INSERT to outbox table in Node, NOTIFY fires from Postgres trigger
- Rust LISTEN loop wakes up, drains outbox rows
- Pro: True durability — message survives any process crash
- Pro: Single source of truth (Postgres)
- Con: Node needs a new Postgres dependency (`pg` or `postgres` npm package)
- Con: Two processes sharing one Postgres — need connection pool discipline

**Option 2: Node writes outbox to local file, Rust polls file**
- Node writes JSON files to `data/outbox/{timestamp}.json`
- Rust uses existing inotify/poll watcher pattern from `ipc.rs`
- Pro: No new Node dependencies
- Con: File-based, no ACID guarantees, no LISTEN/NOTIFY
- Con: Re-introduces polling, just at a different layer
- Con: Doesn't solve the fundamental problem

**Option 3: Node keeps HTTP to intercomd, but intercomd persists to outbox before processing**
- Node still POSTs to `/v1/db/messages`
- intercomd writes to outbox table before returning 200
- Separate drain loop processes outbox
- Pro: Node changes are minimal (just check for 200 response)
- Con: Still fire-and-forget if intercomd is down
- Con: Doesn't fix the "intercomd is unreachable" failure mode

**Decision: Option 1** — Node writes directly to Postgres. This is the only option that guarantees message durability even when intercomd is down. The Node→intercomd HTTP path remains as a fallback but is no longer the primary message delivery mechanism.

### Key Decision: Outbox schema design

**Narrow outbox (recommended):**
```sql
CREATE TABLE IF NOT EXISTS message_outbox (
  id BIGSERIAL PRIMARY KEY,
  chat_jid TEXT NOT NULL,
  payload_type TEXT NOT NULL,     -- 'message', 'chat_metadata'
  payload JSONB NOT NULL,
  status TEXT NOT NULL DEFAULT 'pending',  -- pending, processing, delivered, failed
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  delivered_at TIMESTAMPTZ,
  attempts INTEGER NOT NULL DEFAULT 0,
  last_error TEXT
);
CREATE INDEX IF NOT EXISTS idx_outbox_pending ON message_outbox(status, created_at)
  WHERE status = 'pending';
```

**Wide outbox (rejected):** Separate columns per message field — too rigid, breaks when schema changes.

**Why JSONB payload:** Different payload types (messages vs chat metadata) have different shapes. JSONB avoids schema coupling between Node and Rust.

### Key Decision: LISTEN/NOTIFY vs pure polling

**LISTEN/NOTIFY with fallback poll (recommended):**
- Postgres trigger fires `NOTIFY intercom_outbox` on INSERT
- Rust maintains a dedicated LISTEN connection
- On NOTIFY: immediately drain pending rows
- Fallback: 30s poll catches any missed notifications (connection drops)
- Latency: ~50ms (NOTIFY) vs 1000ms (current poll)

**Pure NOTIFY (rejected):** If the Postgres connection drops between NOTIFY and processing, messages are lost until the next poll. Always need a fallback.

**Pure polling at faster interval (rejected):** 100ms poll would reduce latency but dramatically increase DB load. LISTEN/NOTIFY is free when idle.

### Key Decision: How does the Rust side drain the outbox?

**Atomic claim pattern (recommended):**
```sql
UPDATE message_outbox
SET status = 'processing', attempts = attempts + 1
WHERE id IN (
  SELECT id FROM message_outbox
  WHERE status = 'pending'
  ORDER BY created_at
  FOR UPDATE SKIP LOCKED
  LIMIT 10
)
RETURNING *
```

This is the same pattern we implemented for `claim_due_tasks()` in Bug 3 (iv-lzyfp). Reuse the pattern.

After processing each row:
- Success: `UPDATE SET status = 'delivered', delivered_at = now()`
- Failure: `UPDATE SET status = 'failed', last_error = $1` (or back to 'pending' for retry)

### Key Decision: What about the existing message_loop.rs?

**Replace poll_once() with outbox drain (recommended):**
- The outbox drain replaces `get_new_messages()` polling
- Recovery is built into the outbox: 'pending' rows are always re-processed on startup
- Remove the dual-cursor complexity (last_timestamp / last_agent_timestamp for the message fetch path)
- Per-group agent timestamps remain for accumulated context tracking

**Keep both paths in parallel (rejected):** Adds complexity without benefit. If outbox works, polling is redundant.

### Key Decision: Node Postgres connection management

**Single connection with reconnect (recommended for now):**
- Node creates one `pg.Client` to Postgres at startup
- Uses same DSN as intercomd (`INTERCOM_POSTGRES_DSN` env var)
- Reconnect with exponential backoff on disconnect
- Node only writes, never reads — minimal load

**Connection pool (future):** If Node starts reading from Postgres (Phase 3: SQLite retirement), upgrade to `pg.Pool`. Not needed for Phase 1.

## Explored Ideas

### Hermes-style single-process
- Hermes avoids all IPC by running everything in one Python process
- Would require porting Grammy (Telegram SDK) to Rust — no maintained equivalent
- 4-6 weeks effort for ~10ms improvement over LISTEN/NOTIFY
- Rejected for this phase, revisit in Phase 4 if bridge still causes issues

### Redis Streams / NATS
- Adds infrastructure dependency for < 100 msgs/day workload
- Postgres LISTEN/NOTIFY provides identical guarantees at this scale
- Rejected unless multi-instance deployment is needed

### Unix domain socket for Node↔Rust IPC
- Faster than HTTP but doesn't solve durability
- Still need a persistence layer for crash recovery
- Socket + Postgres outbox = two transports for one operation
- Better applied to container IPC (Phase 2) where persistence isn't needed

## Risks and Mitigations

| Risk | Mitigation |
|------|-----------|
| Node Postgres connection contention with intercomd | Separate connection pools; Node only writes, Rust reads. Postgres handles this easily. |
| LISTEN/NOTIFY missed on connection drop | 30s fallback poll always catches up |
| Outbox table grows indefinitely | Periodic cleanup: DELETE WHERE status = 'delivered' AND delivered_at < now() - interval '7 days' |
| Postgres becomes single point of failure | Already is — intercomd depends on it entirely. No regression. |
| Node `pg` dependency adds complexity | `pg` is the most mature Node Postgres library (16M weekly downloads). Minimal risk. |

## Alignment

**Alignment:** This follows Demarch's "adopt mature tools, don't rebuild" philosophy — using Postgres LISTEN/NOTIFY (a battle-tested feature available since Postgres 9.0) instead of building custom message queuing infrastructure.

**Conflict/Risk:** None. The outbox pattern reduces accidental complexity (fire-and-forget HTTP → durable write) while preserving the dual-process boundary that aligns with "composition over capability."

## Open Questions

1. **Should the outbox also handle bot responses (Rust→Node)?** The current `TelegramBridge.send_text_to_jid()` uses HTTP POST to Node's callback server. This is also fire-and-forget. A reverse outbox could make response delivery durable too. → Defer to Phase 2 or 3.

2. **Should Node keep writing to SQLite at all during Phase 1?** Keeping SQLite writes is safe (backward compatible) but adds unnecessary work. → Keep SQLite for Phase 1 as fallback; remove in Phase 3.

3. **How to handle outbox rows for groups that are no longer registered?** → Skip during drain, mark as 'failed' with reason 'group_unregistered'. Don't block other groups.
