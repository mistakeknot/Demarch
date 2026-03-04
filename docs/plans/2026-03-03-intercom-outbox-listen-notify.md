# Implementation Plan: Postgres Outbox + LISTEN/NOTIFY

**Bead:** iv-nt43u | **PRD:** docs/prd/2026-03-03-intercom-outbox-listen-notify.md

## Step 1: Outbox schema + NOTIFY trigger

**Files:** `apps/intercom/rust/intercom-core/src/persistence.rs`

Add to `ensure_schema()` after the existing `registered_groups` table:

```sql
CREATE TABLE IF NOT EXISTS message_outbox (
  id BIGSERIAL PRIMARY KEY,
  chat_jid TEXT NOT NULL,
  payload_type TEXT NOT NULL,
  payload JSONB NOT NULL,
  status TEXT NOT NULL DEFAULT 'pending',
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  delivered_at TIMESTAMPTZ,
  attempts INTEGER NOT NULL DEFAULT 0,
  last_error TEXT
);
CREATE INDEX IF NOT EXISTS idx_outbox_pending
  ON message_outbox(status, created_at)
  WHERE status = 'pending';

-- Trigger: notify intercomd when new outbox row arrives
CREATE OR REPLACE FUNCTION notify_outbox_insert() RETURNS TRIGGER AS $$
BEGIN
  PERFORM pg_notify('intercom_outbox', NEW.id::TEXT);
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_trigger WHERE tgname = 'trg_outbox_notify'
  ) THEN
    CREATE TRIGGER trg_outbox_notify
      AFTER INSERT ON message_outbox
      FOR EACH ROW EXECUTE FUNCTION notify_outbox_insert();
  END IF;
END;
$$;
```

Add outbox query methods to `PgPool`:

```rust
/// Claim up to `limit` pending outbox rows atomically.
/// Uses SELECT FOR UPDATE SKIP LOCKED to prevent concurrent drains from
/// double-processing. Transitions status from 'pending' to 'processing'.
pub async fn claim_outbox_rows(&self, limit: i64) -> anyhow::Result<Vec<OutboxRow>> {
    // SQL:
    // UPDATE message_outbox
    // SET status = 'processing', attempts = attempts + 1
    // WHERE id IN (
    //   SELECT id FROM message_outbox
    //   WHERE status = 'pending' AND attempts < 5
    //   ORDER BY created_at
    //   FOR UPDATE SKIP LOCKED
    //   LIMIT $1
    // )
    // RETURNING *
}

/// Mark an outbox row as delivered.
pub async fn mark_outbox_delivered(&self, id: i64) -> anyhow::Result<()> { ... }

/// Mark an outbox row as failed (permanent — deserialization error, max attempts).
pub async fn mark_outbox_failed(&self, id: i64, error: &str) -> anyhow::Result<()> { ... }

/// Reset an outbox row back to 'pending' for retry (transient error).
pub async fn mark_outbox_retry(&self, id: i64, error: &str) -> anyhow::Result<()> { ... }

/// Reset stale 'processing' rows back to 'pending' (crash recovery on startup).
pub async fn recover_stale_outbox_rows(&self) -> anyhow::Result<i64> { ... }

/// Delete old delivered rows (cleanup).
pub async fn cleanup_outbox(&self, older_than_days: i64) -> anyhow::Result<i64> { ... }
```

Add `OutboxRow` struct:
```rust
pub struct OutboxRow {
    pub id: i64,
    pub chat_jid: String,
    pub payload_type: String,
    pub payload: serde_json::Value,
    pub status: String,
    pub created_at: String,
    pub attempts: i32,
}
```

**Tests:** Unit test `claim_outbox_rows` SQL produces correct RETURNING rows with `status = 'processing'` (pattern from `claim_due_tasks`).

**Verify:** `npm run rust:test` passes.

## Step 2: Outbox drain loop (Rust)

**Files:** `apps/intercom/rust/intercomd/src/outbox.rs` (new)

Create `outbox.rs` with:

```rust
pub async fn run_outbox_drain(
    pool: PgPool,
    queue: Arc<GroupQueue>,
    drain_signal: tokio::sync::mpsc::Receiver<()>,
    mut shutdown: watch::Receiver<bool>,
) { ... }
```

**Design principle:** The drain is a pure write path. It claims outbox rows, stores them in the destination table, then hands off to `queue.enqueue_message_check()`. All dispatch logic (trigger checking, cursor advancement, context accumulation, container piping) stays in `process_group_messages()` — no duplication.

Flow:
1. On startup: call `pool.recover_stale_outbox_rows()` to reset any `processing` rows left by a crash
2. Wait on `drain_signal` (from LISTEN) or 30s fallback timeout
3. Call `pool.claim_outbox_rows(10)` — claims rows atomically with `status = 'processing'`
4. For each row:
   - Match `payload_type`:
     - `"message"` → deserialize payload as `NewMessage`, call `pool.store_message(&msg)`, then `queue.enqueue_message_check(&row.chat_jid)`
     - `"chat_metadata"` → deserialize as `StoreChatMetadataRequest`, call `pool.store_chat_metadata()`
   - On success: `pool.mark_outbox_delivered(row.id)`
   - On deserialization error (permanent): `pool.mark_outbox_failed(row.id, &err.to_string())`
   - On transient DB error: `pool.mark_outbox_retry(row.id, &err.to_string())` — back to `pending`
   - Rows with `attempts >= 5` are claimed but marked `failed` (max-attempts guard is in the claim SQL)
5. After drain cycle, if any rows were claimed, loop immediately (there may be more)
6. If no rows claimed, go back to waiting

Note: Per-group `AgentTimestamps` and cursor advancement are handled by `process_group_messages()` when it runs after `enqueue_message_check()` — the drain does not need to track these.

**Files:** `apps/intercom/rust/intercomd/src/main.rs`

- Add `mod outbox;` to module list
- In `serve()`, after spawning message_loop, spawn outbox drain:
  ```rust
  let (drain_tx, drain_rx) = tokio::sync::mpsc::channel::<()>(16);
  let outbox_handle = tokio::spawn(async move {
      outbox::run_outbox_drain(pool, queue, drain_rx, shutdown).await;
  });
  ```

**Tests:** Integration test: insert outbox row → drain loop picks it up → message appears in `messages` table → `enqueue_message_check` called.

**Verify:** `npm run rust:test` passes.

## Step 3: LISTEN/NOTIFY loop (Rust)

**Files:** `apps/intercom/rust/intercomd/src/outbox.rs`

Add LISTEN loop function and DSN redaction helper:

```rust
/// Redact password from DSN for safe logging.
fn redact_dsn(dsn: &str) -> String {
    // Replace password between :// user: and @ with "***"
    // e.g., "postgres://user:secret@host/db" → "postgres://user:***@host/db"
}

pub async fn run_listen_loop(
    dsn: String,
    drain_tx: tokio::sync::mpsc::Sender<()>,
    mut shutdown: watch::Receiver<bool>,
) { ... }
```

Flow:
1. Connect to Postgres with a **separate** `tokio_postgres::connect()` (not via PgPool — LISTEN holds the connection)
2. `client.execute("LISTEN intercom_outbox", &[]).await`
3. Loop: `tokio::select!` on:
   - `connection.next()` notification → `drain_tx.try_send(())` (non-blocking — drop signal if channel full, drain will catch up)
   - `shutdown.changed()` → return
4. On connection error: log WARN with `redact_dsn(&dsn)`, exponential backoff (1s→30s), reconnect, re-LISTEN
5. The 30s fallback poll in `run_outbox_drain` handles the reconnect window

**Important:** Use `try_send()` not `send().await` for the drain signal. If the channel is full (drain already signaled), dropping the notification is harmless — the drain will process all pending rows when it wakes.

**Files:** `apps/intercom/rust/intercomd/src/main.rs`

Spawn the LISTEN loop alongside the drain loop:
```rust
let listen_handle = tokio::spawn(async move {
    outbox::run_listen_loop(dsn, drain_tx, shutdown).await;
});
```

**Verify:** `npm run rust:test` passes. Manual test: INSERT into outbox → see drain log within <200ms.

## Step 4: OrchestratorConfig flag

**Files:** `apps/intercom/rust/intercom-core/src/config.rs`

Add to `OrchestratorConfig`:
```rust
/// Use outbox-based message delivery instead of legacy polling.
/// When true, Node writes to message_outbox and Rust drains it.
/// When false, Rust polls the messages table directly (legacy).
pub use_outbox: bool,
```

Default in Rust `Default` impl: `false` (safe default — legacy polling unless explicitly opted in). Production config sets `true` after verification.

**Files:** `apps/intercom/rust/intercomd/src/main.rs`

Conditionally spawn outbox drain OR message loop based on `config.orchestrator.use_outbox`:
```rust
if config.orchestrator.use_outbox {
    // Spawn outbox drain + LISTEN
    info!("outbox mode enabled — spawning drain + LISTEN loops");
} else {
    // Spawn legacy message_loop
    info!("legacy polling mode — spawning message_loop");
}
```

**Files:** `config/intercom.toml`

Add (explicitly opt in for production):
```toml
[orchestrator]
use_outbox = true
```

**Verify:** Toggle flag → old behavior still works. Without the config line, Rust defaults to `false` (legacy).

## Step 5: Node Postgres writer

**Files:** `apps/intercom/package.json`

Add dependency: `"pg": "^8.13.0"` (and `"@types/pg": "^8.11.0"` to devDependencies).

```bash
cd apps/intercom && npm install pg @types/pg
```

**Files:** `apps/intercom/src/pg-writer.ts` (new)

```typescript
import { Client } from 'pg';
import { logger } from './logger.js';

let pgClient: Client | null = null;
let reconnectTimer: NodeJS.Timeout | null = null;
let reconnectAttempt = 0;

export async function initPgWriter(dsn: string): Promise<void> { ... }

export async function writeToOutbox(
  chatJid: string,
  payloadType: 'message' | 'chat_metadata',
  payload: unknown,
): Promise<boolean> {
  if (!pgClient) return false;
  try {
    await pgClient.query(
      'INSERT INTO message_outbox (chat_jid, payload_type, payload) VALUES ($1, $2, $3)',
      [chatJid, payloadType, JSON.stringify(payload)],
    );
    return true;
  } catch (err) {
    logger.warn({ err: (err as Error).message }, 'outbox write failed');
    return false;
  }
}

async function reconnect(dsn: string): Promise<void> { ... }
// Exponential backoff: 1s, 2s, 4s, 8s, 16s, 30s cap
```

**Files:** `apps/intercom/src/db.ts`

Replace `dualWriteToPostgres()` calls in `storeMessage()`, `storeMessageDirect()`, and `storeChatMetadata()` with `writeToOutbox()`, falling back to legacy HTTP on failure:

```typescript
// Before (fire-and-forget HTTP):
dualWriteToPostgres('/messages', { id, chat_jid, ... });

// After (durable outbox with fallback):
const wrote = await writeToOutbox(chat_jid, 'message', { id, chat_jid, sender, ... });
if (!wrote) {
  logger.warn({ chat_jid }, 'outbox write failed, falling back to HTTP');
  dualWriteToPostgres('/messages', { id, chat_jid, sender, ... });
}
```

Keep the `dualWriteToPostgres()` function as active fallback (not dead code — used when Postgres is unavailable).

**Files:** `apps/intercom/src/index.ts`

At startup, call `initPgWriter(process.env.INTERCOM_POSTGRES_DSN)` after channel initialization.

**Verify:** `npm run build` succeeds. `npm test` passes. Manual test: send Telegram message → see outbox row in Postgres → intercomd drains it → response arrives.

## Step 6: Outbox cleanup + monitoring

**Files:** `apps/intercom/rust/intercomd/src/outbox.rs`

Add cleanup loop:
```rust
pub async fn run_outbox_cleanup(pool: PgPool, mut shutdown: watch::Receiver<bool>) {
    let interval = Duration::from_secs(3600); // 1 hour
    loop {
        tokio::select! {
            _ = tokio::time::sleep(interval) => {
                match pool.cleanup_outbox(7).await {
                    Ok(count) if count > 0 => info!(deleted = count, "outbox cleanup"),
                    _ => {}
                }
            }
            _ = shutdown.changed() => return,
        }
    }
}
```

**Files:** `apps/intercom/rust/intercomd/src/main.rs`

Spawn the cleanup loop.

Add outbox stats to the `/readyz` endpoint:
```rust
// Count pending, processing, failed rows
let outbox_stats = pool.outbox_stats().await;
```

**Verify:** `npm run rust:test` passes.

## Step 7: Tests and verification

**All tests:**
```bash
cd apps/intercom && npm run rust:test  # Rust tests (should be 160+)
cd apps/intercom && npm test           # Node tests
cd apps/intercom && npm run build      # TypeScript compilation
```

**Manual verification on ethics-gradient:**
1. Restart intercomd → schema migration adds outbox table + trigger
2. Restart intercom (Node) → connects to Postgres, outbox writer ready
3. Send Telegram message → outbox row created → drain picks up within 200ms → response delivered
4. Kill intercomd mid-drain → restart → `recover_stale_outbox_rows()` resets processing rows → rows re-processed
5. Check `/readyz` shows outbox stats
6. Toggle `use_outbox = false` → legacy polling resumes
7. Verify outbox write failure → falls back to `dualWriteToPostgres()` HTTP path

## Implementation Order

Steps 1-3 are Rust-only (schema, drain, LISTEN). Steps 4-5 bridge Rust config and Node writer. Step 6 is cleanup. Step 7 is final verification.

Steps 1, 2, 3 must be sequential (each builds on prior).
Steps 4 and 5 can be done in parallel after Step 3.
Step 6 depends on Step 2.
Step 7 is final.

Note: The old Step 6 (message loop integration / dispatch extraction) was removed. The outbox drain calls `queue.enqueue_message_check()` directly — all dispatch logic stays in `process_group_messages()` with zero duplication.

## Rollback

At any point, setting `use_outbox = false` in `intercom.toml` and restarting intercomd reverts to legacy polling. Node's SQLite writes are unchanged. Zero-downtime rollback.
