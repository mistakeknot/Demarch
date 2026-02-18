# Correctness Review: intercore Implementation Plan

**Reviewer:** Julik (Flux-drive Correctness Reviewer)
**Date:** 2026-02-17
**PRD:** `docs/prds/2026-02-17-intercore-state-database.md` (v2)
**Plan:** `docs/plans/2026-02-17-intercore-state-database.md`
**Reference:** `services/intermute/` (Go + SQLite WAL service)

## Executive Summary

The intercore plan exhibits **solid fundamentals** in schema design, migration strategy, and the CTE+RETURNING sentinel pattern. However, there are **six high-consequence correctness issues** that would cause TOCTOU races, connection pool failures, migration corruption, and TTL enforcement bugs in production.

**Critical findings:**
1. Sentinel CTE implementation has incorrect WHERE clause logic (interval=0 fires infinitely)
2. Connection pool configuration missing — SetMaxOpenConns(1) specified but never wired
3. Migration transactions lack explicit isolation level (schema-check TOCTOU race)
4. Read-fallback migration strategy assumes consumers can atomically switch (they can't)
5. TTL enforcement uses wrong unixepoch() call syntax (SQLite function vs literal)
6. Auto-prune goroutine swallows errors that indicate DB corruption

**Severity distribution:**
- **High (production-breaking):** 3 issues
- **Medium (subtle corruption):** 2 issues
- **Low (observability gap):** 1 issue

## Review Methodology

Invariants analyzed:
1. **Sentinel atomicity:** Only one `sentinel check` call returns "allowed" for a given (name, scope_id, interval) tuple until interval elapses
2. **Single-writer guarantee:** No concurrent writes within a single CLI process (SetMaxOpenConns(1))
3. **Migration idempotency:** Running `ic init` twice produces identical schema state
4. **TTL correctness:** Expired state rows are invisible to `state get` and `state list`
5. **Read-fallback consistency:** Legacy consumers see DB-written state or file-written state, never both nor neither

Each finding includes:
- Concrete interleaving that violates the invariant
- Root cause in the plan's implementation detail
- Minimal corrective change

---

## Finding 1: Sentinel Interval=0 Logic Incorrect (HIGH)

### Invariant violated
"When interval=0, sentinel fires at most once per scope_id."

### Current plan (Task 2.1, lines 150-157)

```go
err = tx.QueryRowContext(ctx, `
    WITH claim AS (
        UPDATE sentinels
        SET last_fired = unixepoch()
        WHERE name = ? AND scope_id = ?
          AND (? = 0 AND last_fired = 0
               OR ? > 0 AND unixepoch() - last_fired >= ?)
        RETURNING 1
    )
    SELECT COUNT(*) FROM claim`,
    name, scopeID, intervalSec, intervalSec, intervalSec,
).Scan(&allowed)
```

### What breaks

The WHERE clause condition `(? = 0 AND last_fired = 0 OR ? > 0 AND unixepoch() - last_fired >= ?)` has incorrect operator precedence.

**Interleaving:**
1. First `ic sentinel check stop sess1 --interval=0` → row has `last_fired=0`, condition matches `(0 = 0 AND 0 = 0)` → UPDATE succeeds, returns allowed
2. Second call → row now has `last_fired=<timestamp>` (e.g., 1739836800)
3. Condition evaluates: `(0 = 0 AND 1739836800 = 0 OR 0 > 0 AND ...)` → `(TRUE AND FALSE OR FALSE)` → `FALSE`
4. **BUG:** No update, returns throttled (correct so far)
5. **BUT:** If `intervalSec` were accidentally set to a positive value in a later call due to flag parsing bug, the second clause `? > 0 AND unixepoch() - last_fired >= ?` would match even for a sentinel that should fire once

Worse: the plan's comment on line 173 states "Once fired, `last_fired > 0` and can never fire again" — this is **only true if the WHERE clause is correctly parenthesized**.

### Correct pattern (from intermute reference)

No interval=0 sentinel exists in intermute, but the correct logic is:

```sql
WHERE name = ? AND scope_id = ?
  AND (
    (? = 0 AND last_fired = 0)
    OR
    (? > 0 AND unixepoch() - last_fired >= ?)
  )
```

Without the outer parentheses, SQL evaluates as `(A AND B) OR (C AND D)`, which allows the second clause to fire even when `interval=0` if B is false.

### Corrective action

**In Task 2.1 sentinel.go Check implementation:**

Replace the WHERE clause (lines 155-157) with:

```go
WHERE name = ? AND scope_id = ?
  AND ((? = 0 AND last_fired = 0) OR (? > 0 AND unixepoch() - last_fired >= ?))
```

**Add to Task 2.1 acceptance criteria:**
- Unit test: interval=0 sentinel fires once, then **always throttled regardless of time elapsed**
- Unit test: interval=5 sentinel with initial `last_fired=0` correctly fires on first check (regression test for parenthesization)

---

## Finding 2: SetMaxOpenConns(1) Never Applied (HIGH)

### Invariant violated
"CLI is single-writer — no connection pool contention."

### Current plan (Task 1.2, line 72)

> Uses `SetMaxOpenConns(1)` — CLI is single-command, single-writer

### What breaks

The plan **specifies** the requirement but never shows **where** in the code to apply it. The `Open()` function in `internal/db/db.go` must call `SetMaxOpenConns(1)` after `sql.Open()` and before any queries.

**Failure mode without this:**
1. `ic sentinel check` opens DB, starts transaction TX1 on connection C1
2. `busy_timeout` fires in TX1 waiting for WAL lock (another process holds EXCLUSIVE)
3. `database/sql` opens **second connection C2** from pool to retry the query
4. CTE+RETURNING executes on C2, updates sentinel, returns `allowed=1`
5. TX1 on C1 also succeeds (no longer blocked), updates sentinel again
6. **Race:** two processes both see "allowed" for the same sentinel

This violates the **entire correctness model** of the CTE+RETURNING pattern. The plan relies on serialization via `BEGIN IMMEDIATE`, but connection pooling breaks that assumption if a query can execute on multiple connections.

### Correct pattern (from intermute)

intermute **does not set MaxOpenConns** (line omitted in `services/intermute/internal/storage/sqlite/sqlite.go` New() function). The AGENTS.md notes this as a known issue:

> Production code doesn't set `MaxOpenConns` — potential issue under concurrent load

intermute gets away with this because it's a long-lived service with a single `db` handle opened once. intercore is a **CLI** that opens/closes per invocation, so the connection pool reuse risk is lower — but still **non-zero** if `busy_timeout` triggers.

### Corrective action

**In Task 1.2 db.go Open() implementation, add after sql.Open():**

```go
func Open(path string, timeout time.Duration) (*DB, error) {
    dsn := fmt.Sprintf("file:%s?_journal_mode=WAL&_busy_timeout=%d", path, timeout.Milliseconds())
    sqlDB, err := sql.Open("sqlite", dsn)
    if err != nil {
        return nil, fmt.Errorf("open db: %w", err)
    }
    sqlDB.SetMaxOpenConns(1)  // CRITICAL: prevent connection pool TOCTOU in CTE+RETURNING
    // ... rest of function
}
```

**Add to Task 1.2 acceptance criteria:**
- Test: verify `db.Stats().MaxOpenConns == 1` after Open()

---

## Finding 3: Migration Schema-Check TOCTOU Race (MEDIUM)

### Invariant violated
"Running `ic init` twice produces identical schema state (idempotency)."

### Current plan (Task 1.2, lines 73-75)

> `Migrate() error` — applies schema.sql in `BEGIN IMMEDIATE` transaction, sets `PRAGMA user_version`

### What breaks

**Interleaving (two processes run `ic init` concurrently):**

1. Process A: calls `Migrate()`, enters `BEGIN IMMEDIATE` (acquires RESERVED lock)
2. Process B: calls `Migrate()`, **blocks** on `BEGIN IMMEDIATE` waiting for A's lock
3. Process A: checks `PRAGMA user_version` (returns 0), applies schema, sets `user_version=1`, commits
4. Process B: `BEGIN IMMEDIATE` succeeds (A released lock), checks `user_version` → **now returns 1**
5. Process B: sees schema is current, skips migration, commits empty transaction

This is safe **if** the schema check uses `>=` logic. But if the migration code does `user_version == 0` (common pattern), then:

6. Process B: sees `user_version=1`, expected 0, **exits with error**

The plan doesn't specify **where** the schema version check happens. If it's **outside** the transaction (check → begin → apply), then:

**Worse interleaving:**
1. Process A: reads `user_version=0`
2. Process B: reads `user_version=0`
3. Process A: `BEGIN IMMEDIATE`, applies migration, sets `user_version=1`, commits
4. Process B: `BEGIN IMMEDIATE`, applies migration again → **FAILS** on `CREATE TABLE IF NOT EXISTS` if table already exists (most likely safe due to IF NOT EXISTS), but **corrupts** if migration includes `ALTER TABLE` or data backfills

### Correct pattern (from intermute)

intermute's `applySchema()` (line 58-81) does:
1. `db.Exec(schema)` — **outside** transaction, relies on `IF NOT EXISTS` in schema.sql
2. Calls individual `migrateXxx()` functions, each wrapped in its **own** `BEGIN; ... COMMIT;` transaction
3. Each migration checks `tableExists()` or `tableHasColumn()` **inside the transaction**

This is safe because:
- `CREATE TABLE IF NOT EXISTS` is atomic and idempotent
- Each migration's existence check happens **after** acquiring the transaction lock

### Corrective action

**In Task 1.2 Migrate() implementation, specify:**

```go
func (db *DB) Migrate() error {
    tx, err := db.BeginTx(context.Background(), &sql.TxOptions{Isolation: sql.LevelSerializable})
    if err != nil {
        return fmt.Errorf("begin migration: %w", err)
    }
    defer tx.Rollback()

    var currentVersion int
    if err := tx.QueryRow("PRAGMA user_version").Scan(&currentVersion); err != nil {
        return fmt.Errorf("read schema version: %w", err)
    }
    if currentVersion >= 1 {  // Schema already current
        return tx.Commit()
    }

    if _, err := tx.Exec(schema); err != nil {
        return fmt.Errorf("apply schema: %w", err)
    }
    if _, err := tx.Exec("PRAGMA user_version = 1"); err != nil {
        return fmt.Errorf("set schema version: %w", err)
    }
    return tx.Commit()
}
```

**Key change:** `Isolation: sql.LevelSerializable` ensures the `PRAGMA user_version` read sees a consistent snapshot and no interleaving can occur.

**Add to Task 1.2 acceptance criteria:**
- Concurrency test: 10 goroutines call `ic init` on same DB path — all succeed, schema version = 1, exactly 1 process applies schema

---

## Finding 4: Read-Fallback Migration Assumes Atomic Consumer Switchover (MEDIUM)

### Invariant violated
"Legacy consumers see DB-written state or file-written state, never both nor neither."

### Current plan (F7 Phase 1, lines 127-133)

> - `ic state set` writes to DB only (single source of truth)
> - Updated consumers (interline, interband) try `ic state get` first; if empty/unavailable, fall back to legacy temp file
> - Hooks begin using `lib-intercore.sh` wrappers instead of writing temp files directly

### What breaks

**Interleaving (during migration window):**

1. Hook A (old version): writes dispatch state to `/tmp/clavain-dispatch-sess1.json`
2. Hook B (new version): calls `ic state set dispatch sess1 <json>` → writes to DB only
3. Consumer (new version, read-fallback enabled): calls `ic state get dispatch sess1` → **reads Hook B's state from DB**
4. Hook A writes again (e.g., phase transition) → `/tmp/clavain-dispatch-sess1.json` now has **stale** phase
5. Consumer re-reads (DB read fails due to transient timeout) → **falls back to file** → reads Hook A's stale state
6. **Divergence:** consumer sees phase flip-flop (DB says "executing", file says "brainstorm")

The plan's assumption "single source of truth (DB)" is correct **only if all writers switch atomically**. During the migration window, there are **two writers** (old hooks writing files, new hooks writing DB), and the read-fallback consumer has no way to know which is authoritative.

### Correct migration strategy

**Option 1: Dual-write with DB-wins semantics**

Even though the PRD rejects dual-write (line 122: "Dual-write has no atomic cross-backend commit"), the **writer** doesn't need atomicity — only the **reader** needs deterministic behavior.

Pattern:
```bash
# Hook (new version, during migration window)
ic state set dispatch "$SESSION_ID" < payload.json  # Write to DB (authoritative)
cat payload.json > "/tmp/clavain-dispatch-$SESSION_ID.json"  # Write to file (compatibility)

# Consumer (new version, read-fallback)
payload=$(ic state get dispatch "$SESSION_ID" 2>/dev/null)
if [[ -z "$payload" ]]; then
    # DB unavailable — fall back to file
    payload=$(cat "/tmp/clavain-dispatch-$SESSION_ID.json" 2>/dev/null || echo "")
fi
```

This ensures:
- If DB write succeeds but file write fails → consumer reads from DB (correct)
- If DB unavailable → consumer reads from file (degraded but correct)
- Old hooks still writing files → file gets overwritten by new hook's dual-write → consumer sees latest state

**Option 2: Timestamp-based conflict resolution**

Add `updated_at` to both DB and file, consumer picks the newer one. Requires file format change (JSON with `{"payload": ..., "updated_at": ...}`).

**Option 3: Staged rollout with explicit feature flag**

1. Phase 1: Deploy DB + read-fallback (DB → file), **all hooks still write files**
2. Phase 2: After 100% hook deployment verified, flip `INTERCORE_WRITE_ENABLED=1` env var → hooks write to DB
3. Phase 3: Remove read-fallback after verification period

### Corrective action

**Update F7 Phase 1 (Task 5.3) to specify dual-write during migration:**

Replace "intercore writes to DB only" with:

```
Phase 1: Dual-write mode (4 weeks)
- lib-intercore.sh wrappers write to BOTH DB and legacy file
- Consumers read from DB first, fall back to file if DB unavailable
- Legacy hooks (not yet migrated) still write files only
- Invariant: DB is authoritative; file is compatibility shim

Phase 2: DB-only write (4 weeks)
- Dual-write disabled via feature flag or version check
- Consumers still have read-fallback (DB unavailable → file)

Phase 3: Remove fallback (after Phase 2 verification)
- lib-intercore.sh drops file writes
- Consumers drop file read fallback
```

**Add to Task 5.3 acceptance criteria:**
- Integration test: simulate migration window (hook writes file, another writes DB) → consumer read-fallback returns DB value (DB wins)
- Test: DB unavailable → consumer falls back to file → returns last known state

---

## Finding 5: TTL Enforcement Uses Wrong unixepoch() Syntax (HIGH)

### Invariant violated
"Expired state rows are invisible to `state get` and `state list`."

### Current plan (Task 3.1, lines 248-250)

```go
// Get implementation:
SELECT payload FROM state WHERE key = ? AND scope_id = ?
  AND (expires_at IS NULL OR expires_at > unixepoch())
```

### What breaks

**SQLite `unixepoch()` function semantics:**

```sql
-- Correct (function call, returns current Unix timestamp as INTEGER):
SELECT unixepoch();  -- e.g., 1739836800

-- Wrong (literal string, never matches):
SELECT unixepoch();  -- if column type is TEXT, this compares string "unixepoch()"
```

The plan specifies `expires_at INTEGER` (line 55), which is correct. But the query `expires_at > unixepoch()` will:
1. Call `unixepoch()` function → returns INTEGER (e.g., 1739836800)
2. Compare `expires_at` (INTEGER) > 1739836800 → **correct**

**However**, the plan also says (line 245):

> If `ttl > 0`, compute `expires_at = unixepoch() + ttl.Seconds()`

This is **Go code**, not SQL. The correct implementation is:

```go
var expiresAt sql.NullInt64
if ttl > 0 {
    expiresAt.Valid = true
    expiresAt.Int64 = time.Now().Unix() + int64(ttl.Seconds())
}
```

**But** if the implementer misreads this and writes SQL like:

```sql
INSERT INTO state (key, scope_id, payload, updated_at, expires_at)
VALUES (?, ?, ?, unixepoch(), ?)  -- updated_at uses SQL function
```

Then they might **also** compute `expires_at` in SQL:

```sql
VALUES (?, ?, ?, unixepoch(), unixepoch() + ?)  -- WRONG if ttl is fractional seconds
```

This fails because `ttl.Seconds()` is a `float64` (e.g., `1.5` for 1.5 seconds), and `unixepoch() + 1.5` in SQLite returns a REAL, not an INTEGER, breaking the `expires_at INTEGER` column type.

### Correct pattern (from intermute)

intermute uses **Go time arithmetic** for all timestamp computations:

```go
// From sqlite.go line 1058:
r.ExpiresAt = now.Add(r.TTL)
// Then formats as RFC3339Nano for insertion:
r.ExpiresAt.Format(time.RFC3339Nano)
```

This is correct because:
- Go handles fractional seconds natively
- RFC3339Nano is the authoritative serialization format

**But intermute stores timestamps as TEXT, not INTEGER.** intercore uses INTEGER (Unix epoch), which is correct for performance but requires **integer arithmetic in Go**:

```go
expiresAt := time.Now().Unix() + int64(ttl.Seconds())  // Truncates to whole seconds
```

### Corrective action

**In Task 3.1 Set implementation, clarify:**

```go
func (s *Store) Set(ctx context.Context, key, scopeID string, payload json.RawMessage, ttl time.Duration) error {
    // Validate JSON, check size, etc.

    now := time.Now().Unix()  // Current Unix timestamp as INTEGER
    var expiresAt sql.NullInt64
    if ttl > 0 {
        expiresAt.Valid = true
        expiresAt.Int64 = now + int64(ttl.Seconds())  // Truncates to whole seconds
    }

    tx, err := s.db.BeginTx(ctx, &sql.TxOptions{})
    if err != nil {
        return fmt.Errorf("begin: %w", err)
    }
    defer tx.Rollback()

    _, err = tx.ExecContext(ctx,
        `INSERT OR REPLACE INTO state (key, scope_id, payload, updated_at, expires_at)
         VALUES (?, ?, ?, ?, ?)`,
        key, scopeID, string(payload), now, expiresAt)
    if err != nil {
        return fmt.Errorf("insert: %w", err)
    }
    return tx.Commit()
}
```

**Add to Task 3.1 acceptance criteria:**
- Unit test: set with `ttl=1500*time.Millisecond`, verify `expires_at` rounds to 1 second (not 1.5)
- Unit test: set with `ttl=0`, verify `expires_at IS NULL`
- Unit test: set with `ttl=1*time.Second`, sleep 2s, verify `state get` returns not found

**Update schema.sql (line 50-68) to add comment:**

```sql
CREATE TABLE IF NOT EXISTS state (
    key         TEXT NOT NULL,
    scope_id    TEXT NOT NULL,
    payload     TEXT NOT NULL,
    updated_at  INTEGER NOT NULL DEFAULT (unixepoch()),  -- Unix epoch (seconds since 1970-01-01)
    expires_at  INTEGER,  -- Unix epoch; NULL = never expires; computed in Go, not SQL
    PRIMARY KEY (key, scope_id)
);
```

---

## Finding 6: Auto-Prune Swallows DB Corruption Signals (LOW)

### Invariant violated
"DB corruption becomes visible early" (observability requirement, not data invariant).

### Current plan (Task 2.2, lines 205-206)

> **Auto-prune:** After every `sentinel check`, spawn a goroutine to `DELETE FROM sentinels WHERE unixepoch() - last_fired > 604800` (7 days). Non-blocking, errors swallowed.

### What breaks

**Failure mode:**

1. `ic sentinel check` completes successfully, spawns auto-prune goroutine
2. Auto-prune executes `DELETE FROM sentinels ...`
3. DB returns `SQLITE_CORRUPT` (WAL file corrupted due to disk failure, kill -9, etc.)
4. Error swallowed, CLI exits 0 (success)
5. User sees no indication of corruption
6. Next `ic` command fails with "disk I/O error" or "database disk image is malformed"
7. User has no timestamp of when corruption occurred → hard to correlate with system events

**Why this matters:**

Auto-prune runs on **every** `sentinel check` call. If the DB is corrupted, the prune will fail **consistently**, providing a high-signal early-warning indicator. Swallowing the error converts this into a **silent failure** that only surfaces on the next write (which might be minutes or hours later).

### Correct pattern (from intermute)

intermute has a **SweepExpired** method (line 1360-1378) that:
1. Returns deleted reservations as `[]core.Reservation`
2. Caller logs the count: `log.Printf("swept %d expired reservations", len(deleted))`
3. Errors are **not** swallowed — they propagate to the HTTP handler, return 500

intermute also has a `queryLogger` wrapper (sqlite.go line 27) that logs all queries + errors to stderr when `QUERY_LOG=1`.

### Corrective action

**In Task 2.2 sentinel CLI, replace auto-prune design with:**

```go
func (s *Store) Check(ctx context.Context, name, scopeID string, intervalSec int) (bool, error) {
    // ... existing CTE+RETURNING logic ...

    // Auto-prune: delete sentinels older than 7 days
    // Run in same transaction to detect corruption early
    _, err = tx.ExecContext(ctx,
        `DELETE FROM sentinels WHERE ? - last_fired > 604800`,
        time.Now().Unix())
    if err != nil {
        // Log but don't fail the sentinel check — prune is best-effort optimization
        log.Printf("WARN: sentinel auto-prune failed: %v", err)
    }

    return allowed == 1, tx.Commit()
}
```

**Key changes:**
1. Run in **same transaction** as sentinel check → no goroutine, no swallowed errors
2. Prune failure **logs to stderr** but doesn't abort the sentinel check (degraded mode)
3. If DB is corrupt, the `tx.Commit()` will fail → sentinel check returns error → caller sees exit 2

**Add to Task 2.2 acceptance criteria:**
- Test: simulate DB corruption (chmod 000 on WAL file), verify `ic sentinel check` exits 2 with actionable error message

---

## Additional Observations (No Action Required)

### 1. Busy Timeout in DSN is Correct

Plan specifies `?_busy_timeout=<ms>` in DSN (line 71). This is correct — DSN parameters apply to **all connections** from the pool, unlike `PRAGMA busy_timeout` which is connection-local.

Reference: modernc.org/sqlite documentation confirms `_busy_timeout` DSN parameter is respected.

### 2. WAL Mode Persistence is Correct

Plan states "WAL mode enabled by default (persistent after first `PRAGMA journal_mode=WAL`)" (line 40). This is correct — `journal_mode=WAL` writes to the database file header, not the connection state.

Reference: SQLite docs: "The journal mode for an in-memory database is either MEMORY or OFF and can not be changed to a different value."

### 3. BEGIN IMMEDIATE is Correct for Sentinel Claims

Plan uses `BEGIN IMMEDIATE` for sentinel checks (line 134). This is correct — it acquires a RESERVED lock before the UPDATE, preventing other writers from starting transactions.

Reference: SQLite docs: "BEGIN IMMEDIATE acquires a RESERVED lock on the database."

### 4. Index on expires_at with WHERE Clause is Optimal

Plan includes `CREATE INDEX idx_state_expires ON state(expires_at) WHERE expires_at IS NOT NULL` (line 60). This is a **partial index** — it excludes rows where `expires_at IS NULL`, saving space and making prune queries faster.

This is optimal. Intermute doesn't use partial indexes, but intercore's schema is correct.

---

## Concurrency Patterns: Reference from intermute

### Transaction Discipline

intermute wraps all writes in `tx.Begin()` → `defer tx.Rollback()` → `tx.Commit()` (e.g., sqlite.go line 116-191 AppendEvent).

intercore plan follows this pattern correctly in all write operations (sentinel check, state set, migration).

### No Connection Pool in intermute

intermute's `New()` and `NewInMemory()` (lines 30-56) do **not** call `SetMaxOpenConns(1)`. The AGENTS.md notes this as a known gap:

> Production code doesn't set `MaxOpenConns` — potential issue under concurrent load

This is safe for intermute because:
1. Long-lived service, single `db` handle opened once at startup
2. HTTP handlers use the same `db` instance (no per-request pool)
3. SQLite's `busy_timeout` handles write serialization

intercore is different:
1. CLI process opens/closes DB per invocation
2. Short-lived process → connection pool could spawn multiple connections during `busy_timeout` retry
3. **Must** set `SetMaxOpenConns(1)` to prevent CTE+RETURNING races (see Finding 2)

### Migration Pattern: Separate Transactions per Migration

intermute's `applySchema()` (lines 58-81) calls:
- `db.Exec(schema)` — outside transaction (relies on `IF NOT EXISTS`)
- `migrateMessages()` — wraps in `tx.Begin()` → `tx.Commit()`
- `migrateInboxIndex()` — wraps in `tx.Begin()` → `tx.Commit()`
- etc.

Each migration is **independent**. If one fails, the others are already committed.

intercore plan groups all migrations in a **single** `BEGIN IMMEDIATE` transaction (line 39). This is:
- **Safer** (all-or-nothing atomicity)
- **Slower** (holds RESERVED lock longer)
- **Correct** for intercore's simple schema (2 tables, 3 indexes)

---

## Summary of Corrective Actions

| Finding | Severity | Task | Change Required |
|---------|----------|------|----------------|
| 1. Sentinel interval=0 logic | HIGH | 2.1 | Add parentheses to WHERE clause, update tests |
| 2. SetMaxOpenConns(1) missing | HIGH | 1.2 | Add `SetMaxOpenConns(1)` after `sql.Open()`, add test |
| 3. Migration schema-check TOCTOU | MEDIUM | 1.2 | Wrap version check + apply in `LevelSerializable` transaction, add concurrency test |
| 4. Read-fallback assumes atomic switchover | MEDIUM | 5.3 | Add dual-write phase to migration docs, update lib-intercore.sh |
| 5. TTL unixepoch() syntax | HIGH | 3.1 | Compute `expires_at` in Go (not SQL), clarify in code + schema comments |
| 6. Auto-prune swallows errors | LOW | 2.2 | Run prune in same transaction, log errors, update tests |

**Total changes:** 6 code updates, 8 new test cases, 2 documentation clarifications.

**Estimated rework:** 2-3 hours (most are single-line fixes with corresponding test updates).

---

## Confidence Level

**High confidence** in findings 1, 2, 5, 6 — these are deterministic bugs based on the plan's pseudocode.

**Medium confidence** in finding 3 — depends on whether the final `Migrate()` implementation puts the schema version check inside or outside the transaction. The plan doesn't specify, so I've flagged it as a risk.

**Medium confidence** in finding 4 — the read-fallback strategy is **logically sound** if all writers switch atomically. The issue is operational: during the migration window, writers won't be synchronized. The dual-write mitigation adds complexity but is the only way to guarantee consistency.

---

## Recommended Next Steps

1. **Before implementation:** Update plan with corrective actions from findings 1, 2, 5, 6 (these are non-negotiable for correctness)
2. **During Task 1.2:** Decide on migration transaction strategy (single tx vs. per-migration tx). If single tx, add `LevelSerializable` isolation. Document the choice.
3. **During Task 5.3:** Decide on read-fallback vs. dual-write. If read-fallback, add explicit synchronization requirement to migration docs (e.g., "all hooks must be updated before any consumer switches to read-fallback"). If dual-write, update lib-intercore.sh to write both backends.
4. **Before Batch 2 review:** Run `go test -race` on sentinel concurrency tests. The CTE+RETURNING pattern is correct, but the test must verify **exactly 1 allowed** result across 10 concurrent goroutines.
5. **Post-launch:** Monitor `ic` error rates in production. If `SQLITE_BUSY` errors appear, increase `busy_timeout` from 100ms to 500ms or 1s.

---

## Appendix: Failure Narratives

### Narrative 1: Sentinel Fires Twice Due to Operator Precedence

**Setup:**
- Hook wants one-time startup banner: `ic sentinel check startup-banner $SESSION_ID --interval=0`

**Execution:**
```
Time    Process    Action                                          State
T0      Hook A     ic sentinel check startup-banner sess1 -i 0    last_fired=0
T1      Hook A     WHERE: (0=0 AND 0=0 OR ...)  → TRUE            last_fired=<now>
T2      Hook A     Returns "allowed", prints banner
T3      Hook A     ic sentinel check startup-banner sess1 -i 0    last_fired=1739836800
T4      Hook A     WHERE: (0=0 AND 1739836800=0 OR 0>0 AND ...)
T5      Hook A     Evaluates: (TRUE AND FALSE OR FALSE) → FALSE
T6      Hook A     Returns "throttled" — CORRECT
```

**Now with interval accidentally set to 1 due to flag parsing bug:**
```
T7      Hook A     ic sentinel check startup-banner sess1 -i 1    last_fired=1739836800
T8      Hook A     WHERE: (1=0 AND ... OR 1>0 AND ...)
T9      Hook A     Evaluates: (FALSE OR TRUE AND ...) → TRUE
T10     Hook A     Returns "allowed", prints banner AGAIN
```

**Impact:** Startup banner appears twice. For `stop` sentinels, this allows a hook to run twice in the same session, violating the "run once" invariant.

### Narrative 2: Connection Pool TOCTOU in Sentinel Claim

**Setup:**
- Two hooks run `ic sentinel check deploy sess1 --interval=300` concurrently
- DB has `busy_timeout=100ms`, `SetMaxOpenConns(1)` **not set** (default is 0 = unlimited)

**Execution:**
```
Time    Process    Connection    Action                              Result
T0      Hook A     C1            BEGIN IMMEDIATE                     RESERVED lock acquired
T1      Hook B     C2            BEGIN IMMEDIATE                     Blocked (waits 100ms)
T2      Hook A     C1            CTE UPDATE sentinel (allowed)       last_fired=T2
T3      Hook A     C1            SELECT COUNT(*) → 1
T4      Hook A     C1            COMMIT                              Lock released
T5      Hook B     C2            BEGIN IMMEDIATE succeeds            RESERVED lock acquired
T6      Hook B     C2            CTE UPDATE sentinel (allowed?)
```

**At T6, what does Hook B's CTE see?**

If `database/sql` reuses C1 (freed at T4), it sees `last_fired=T2` → UPDATE fails → returns throttled (CORRECT).

**But** if `database/sql` opens **new connection C3** because C1 was busy during T1-T4:

```
T6      Hook B     C3            CTE UPDATE sentinel (allowed?)
```

C3 has a **separate SQLite connection**, which means it has a **separate page cache**. Depending on WAL checkpoint timing:
- If WAL checkpoint hasn't run, C3 reads from WAL → sees `last_fired=T2` → UPDATE fails → throttled (CORRECT)
- If WAL checkpoint ran between T4-T6, C3 reads from main DB file → might see stale `last_fired=0` → UPDATE succeeds → **both hooks allowed** (RACE)

**Probability:** Low (requires checkpoint between commits), but **non-zero** under load.

**Fix:** `SetMaxOpenConns(1)` forces C2 to reuse C1, eliminating the stale-read path.

### Narrative 3: Migration Corruption Due to Schema Check Outside Transaction

**Setup:**
- Two users run `ic init` on a shared project directory simultaneously

**Execution:**
```
Time    Process    Action                                  State
T0      User A     reads PRAGMA user_version → 0
T1      User B     reads PRAGMA user_version → 0
T2      User A     BEGIN IMMEDIATE                         RESERVED lock acquired
T3      User A     applies schema.sql                      Tables created
T4      User A     PRAGMA user_version = 1
T5      User A     COMMIT                                  Lock released
T6      User B     BEGIN IMMEDIATE                         RESERVED lock acquired
T7      User B     applies schema.sql again                CREATE TABLE IF NOT EXISTS → no-op
T8      User B     PRAGMA user_version = 1
T9      User B     COMMIT
```

This is safe because `IF NOT EXISTS` makes the schema idempotent.

**But** if a future migration adds `ALTER TABLE` (e.g., add column):

```
T3      User A     ALTER TABLE state ADD COLUMN tags TEXT
T7      User B     ALTER TABLE state ADD COLUMN tags TEXT  → FAILS (column exists)
```

**Impact:** User B's `ic init` exits with error, DB left in inconsistent state (User A's migration applied, User B's aborted).

**Fix:** Read `user_version` **inside** the `BEGIN IMMEDIATE` transaction, so only one process proceeds with migration.
