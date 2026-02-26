# Correctness Review: Native Kernel Coordination Plan
# 2026-02-25-native-kernel-coordination.md

**Reviewer:** Julik (flux-drive Correctness Reviewer)
**Date:** 2026-02-25
**Plan:** `docs/plans/2026-02-25-native-kernel-coordination.md`
**Files examined:**
- `core/intercore/internal/db/db.go`
- `core/intermute/internal/storage/sqlite/sqlite.go` (Reserve, SweepExpired)
- `core/intermute/internal/glob/overlap.go`
- `core/intercore/internal/lock/lock.go`
- `core/intermute/internal/storage/sqlite/sweeper.go`
- `core/intercore/internal/event/store.go`

---

## Invariants This Plan Must Preserve

Before listing findings, these are the invariants that must hold at all times. I derived them from the existing code and the plan's stated goals.

**I1 — Mutual exclusion is serial.** At most one `Reserve()` call may insert a lock row that overlaps an existing exclusive active lock in the same scope. No concurrent call may sneak past the conflict check.

**I2 — Released locks stay released.** `released_at` is write-once. Once set, no code path re-activates a row or re-uses its ID.

**I3 — Dual-write is best-effort shadow, never authoritative.** During the migration phase (Task 7), Intermute's primary `file_reservations` table is still the single source of truth. A failure in the bridge must not roll back the primary reservation.

**I4 — Sweep is idempotent.** Running sweep twice in quick succession must not double-release or emit duplicate events.

**I5 — Schema version is monotonic.** A binary that knows only schema version 19 must refuse to open a version-20 database (handled by `maxSchemaVersion`), and the migration must not leave the DB in a partially-migrated state.

**I6 — The `ROLLBACK; BEGIN IMMEDIATE` pattern must not corrupt an already-committed transaction.** Issuing `ROLLBACK` after `BeginTx` has already started a deferred transaction discards that transaction's deferred lock and any work done before the `ROLLBACK`.

**I7 — PID liveness check is only trustworthy on the same host.** `syscall.Kill(pid, 0)` is a same-host check. A PID from a different host cannot be evaluated this way.

**I8 — Transfer atomicity.** If `Transfer()` commits on zero rows (because the scope filter matched nothing), the caller must not interpret this as a success that consumed some locks.

---

## Findings

### CRITICAL — C1: `ROLLBACK; BEGIN IMMEDIATE` destroys the `database/sql` transaction object

**Severity:** P0 — will cause silent data corruption or panics under load.
**Affected tasks:** Task 1 (Reserve), Task 6 (Transfer)

**The plan writes:**

```go
tx, err := s.db.BeginTx(ctx, nil)          // opens deferred tx; driver takes a real connection
if err != nil { return nil, ... }
defer tx.Rollback()

if _, err := tx.ExecContext(ctx, "ROLLBACK; BEGIN IMMEDIATE"); err != nil {
    return nil, fmt.Errorf("begin immediate: %w", err)
}
```

**Why this is broken — the interleaving that causes corruption:**

`database/sql` binds a `*sql.Tx` to a specific underlying connection and tracks whether that connection's transaction is still live. When `ROLLBACK` is sent through the same `Tx` object, `database/sql` does not know the transaction ended inside the statement string — it still believes `tx` is open. The subsequent `BEGIN IMMEDIATE` starts a new, raw, untracked transaction on that same connection. Now:

1. `tx.Commit()` (line 256 of the plan's store.go) sends `COMMIT` for the *new* raw transaction, which works.
2. `defer tx.Rollback()` fires on function exit. `database/sql` sends `ROLLBACK` on the connection. If any other goroutine has since grabbed the connection (with `MaxOpenConns(1)` this is the only connection), the deferred `ROLLBACK` will silently abort an unrelated operation.

More precisely, with `MaxOpenConns(1)`, the connection pool has exactly one connection. After the manual `ROLLBACK; BEGIN IMMEDIATE`, the `*sql.Tx` object still holds the connection exclusively. The `defer tx.Rollback()` will always fire and always send a stray `ROLLBACK` after the `COMMIT` already completed. This sends `ROLLBACK` when SQLite is in autocommit mode, which is harmless *only if* nothing started a new transaction on the connection between the commit and the defer. With a single connection and no intervening calls this may appear to work in testing, but it breaks the `database/sql` connection lifecycle contract. Under any retry or concurrent use scenario, `database/sql`'s internal state for that connection becomes inconsistent.

**Failure narrative:** Two calls to `Reserve()` arrive 1ms apart on a system where the single connection serializes them.

```
Goroutine A: tx_A = db.BeginTx(deferred) → connection borrowed
Goroutine A: tx_A.Exec("ROLLBACK; BEGIN IMMEDIATE") → raw IMMEDIATE tx started
Goroutine A: conflict check + INSERT  → succeeds
Goroutine A: tx_A.Commit() → commits raw tx; connection released back to pool
Goroutine A: defer tx_A.Rollback() fires → sends ROLLBACK on the *same* connection
             (the connection is now in autocommit, ROLLBACK is a no-op here, ok)
Goroutine B: tx_B = db.BeginTx(deferred) → gets the same connection
Goroutine B: tx_B.Exec("ROLLBACK; BEGIN IMMEDIATE") → ROLLBACK aborts goroutine B's deferred tx
             (harmless so far since nothing was written under deferred)
             BEGIN IMMEDIATE → ok
Goroutine A: defer tx_A.Rollback() fires **again** due to a retry path, or because
             the error path returned early before Commit and now the deferred fires —
             this ROLLBACK now kills goroutine B's IMMEDIATE tx mid-flight.
```

Even if the exact interleaving above doesn't fire in a single-connection pool, the design violates `database/sql`'s ownership model. The `*sql.Tx` object has an internal flag that tracks whether `Rollback()` or `Commit()` has been called; calling `Exec("ROLLBACK")` bypasses this flag, meaning the `defer tx.Rollback()` will always fire a second real `ROLLBACK` to the driver, even after a successful commit.

**The correct fix:** Use `sql.TxOptions` with `Isolation` set, but SQLite via `modernc.org` does not map Go isolation levels to `BEGIN IMMEDIATE`. The established pattern for this driver is to exec `BEGIN IMMEDIATE` as a raw statement *without* `BeginTx` first, then manage the connection manually — or use a helper that runs `BEGIN IMMEDIATE` via `db.Exec` and wraps all subsequent queries in the same connection using a connection checkout:

```go
// Correct pattern for modernc.org/sqlite with IMMEDIATE:
conn, err := s.db.Conn(ctx)
if err != nil { return nil, err }
defer conn.Close()

if _, err := conn.ExecContext(ctx, "BEGIN IMMEDIATE"); err != nil {
    return nil, fmt.Errorf("begin immediate: %w", err)
}
committed := false
defer func() {
    if !committed {
        conn.ExecContext(context.Background(), "ROLLBACK")
    }
}()

// ... conflict check and INSERT using conn.QueryContext / conn.ExecContext ...

if _, err := conn.ExecContext(ctx, "COMMIT"); err != nil {
    return nil, fmt.Errorf("commit: %w", err)
}
committed = true
```

This pattern exists in the Intercore codebase's existing lock manager (filesystem-based). The same pattern must be applied to `Reserve()` and `Transfer()` in the plan.

---

### CRITICAL — C2: Migration block range is wrong — schema v12 through v15 are silently skipped

**Severity:** P0 — databases at versions 12–18 will have no migration guard applied but will still get `CREATE TABLE IF NOT EXISTS` which hides the gap.
**Affected tasks:** Task 1 (migration in db.go)

**The plan's migration guard:**

```go
if currentVersion >= 3 && currentVersion < 20 {
    _, err := tx.ExecContext(ctx, `CREATE TABLE IF NOT EXISTS coordination_locks (...)`)
    ...
}
```

**The problem:** Every prior migration block in `db.go` has a tight upper bound (`< 6`, `< 8`, `< 10`, etc.) so it only runs for databases that haven't seen that version yet. The plan's guard `currentVersion < 20` is correct for the upper bound. The lower bound `>= 3` is also correct (table `runs` exists from v3).

However, looking at the actual `db.go` migration sequence: blocks exist for v5→v6, v4→v8, v3→v10, v2→v11, v3→v12, v2→v12, v2→v18, v3→v16. There is **no block for v13, v14, v15, or v17**. This means a database at v12 has those migration blocks skipped silently because the `currentVersion >= N` lower bounds are never met for v13/v14/v15.

The coordination_locks table block will still run for v12 databases (`>= 3` is satisfied), so the table will be created. But the `user_version` will be set to 20, which permanently seals those skipped migration ranges. If someone later adds a v13→v14 migration guard, it will never fire on any database that went through v12→v20 directly.

This is not a new problem introduced by the plan — it exists in the current migration structure. However, the plan's block **should document this explicitly** and confirm that v13–v15 ranges are intentionally inert. More dangerously: the `isTableExistsError` helper referenced in the plan does not exist in `db.go`. Only `isDuplicateColumnError` exists. Using `CREATE TABLE IF NOT EXISTS` makes this moot, but the plan's fallback error check `&& !isTableExistsError(err)` will fail to compile.

**Fix:** Remove the `isTableExistsError` reference — `CREATE TABLE IF NOT EXISTS` already handles the idempotent case. Use the same pattern as existing migrations:

```go
if currentVersion >= 3 && currentVersion < 20 {
    if _, err := tx.ExecContext(ctx, `CREATE TABLE IF NOT EXISTS coordination_locks (...)`); err != nil {
        return fmt.Errorf("v20 coordination_locks: %w", err)
    }
    // Indexes are handled by schema.sql via IF NOT EXISTS
}
```

---

### CRITICAL — C3: Reserve() conflict check excludes the requesting owner — shared-reader starvation of exclusive writers

**Severity:** P1 — correctness hole that allows an exclusive lock to be acquired when the owner already holds a shared lock on the same pattern.
**Affected tasks:** Task 1 (store.go Reserve)

**The plan's conflict query:**

```sql
SELECT id, owner, pattern, reason, exclusive
FROM coordination_locks
WHERE scope = ? AND released_at IS NULL
  AND (expires_at IS NULL OR expires_at > ?)
  AND owner != ?   -- excludes the requesting owner
```

**The problem:** This exclusion means an owner who already holds an exclusive lock on `"src/*.go"` can call `Reserve()` again with `"src/main.go"` and the check will see no conflict (their own lock is excluded). For named locks this is intentional re-entrant behavior. For file reservations used as write-set guards, it can mask a logical double-reservation by the same agent.

More seriously: the query also excludes same-owner **shared** locks from the conflict check. If agent A holds a shared lock on `"*.go"` and then calls `Reserve()` for an **exclusive** lock on `"main.go"`, the conflict check skips agent A's own shared lock. The new exclusive lock is granted. Now agent A holds both a shared and exclusive lock on overlapping patterns — which is a contradiction since exclusive locks require no other reader.

This matters if the plan's design intent is that `owner != ?` is purely for upgrade/renewal semantics. If it is, that intent must be stated and the system must guarantee the same owner cannot hold conflicting-type locks simultaneously.

**Fix:** If re-entrant locking by the same owner is the intent, document it explicitly. If it is not the intent (especially for file reservations), the conflict check must also check for same-owner type-upgrade conflicts:

```sql
-- Conflict if: a different owner has any incompatible lock,
--              OR the same owner is trying to escalate from shared to exclusive.
WHERE scope = ? AND released_at IS NULL AND (expires_at IS NULL OR expires_at > ?)
  AND NOT (owner = ? AND exclusive = 0)  -- allow same-owner shared → exclusive upgrade
  -- or simply remove the owner exclusion entirely and handle renewal at a higher level
```

---

### HIGH — H1: Dual-write is not atomic with the primary Intermute reservation

**Severity:** P1 — observable inconsistency window during the migration phase.
**Affected tasks:** Task 7 (coordination bridge)

**The plan's approach (Task 7, Step 3):**

> After successful Reserve() commit, call s.bridge.MirrorReserve(...). Errors from bridge are logged but don't fail the primary operation.

This creates a window:

```
T1: Intermute commits reservation R to file_reservations  → visible to all Intermute readers
T2: Intercore CLI queries coordination_locks for R         → R not yet mirrored, sees false negative
T3: MirrorReserve() writes R to coordination_locks        → now visible
```

During the window between T1 and T3, any `ic coordination check` call will see the reservation as absent and may grant a conflicting lock to another agent. This is not just a theoretical window: with 60-second sweep intervals and HTTP round trips, T2 could be seconds after T1.

**The plan acknowledges bridge errors don't fail the primary** — this is correct for durability (the primary must not be blocked by a shadow write). But the plan does not acknowledge the read-path inconsistency: any code that reads *only* `coordination_locks` during the dual-write phase will see a stale view.

**Fix:** During the dual-write phase, `ic coordination check` must query *both* tables (via a UNION or by checking `file_reservations` in Intermute when `ic` is connected). The plan's Task 8 (Interlock bridge) should keep the HTTP fallback path active until Task 9 removes the legacy store. Alternatively, document the inconsistency window explicitly as accepted and bound it: if `MirrorReserve` is synchronous and called before control returns to the HTTP handler, the window is bounded to the HTTP handler's own latency (usually < 1ms for a same-process SQLite write).

**The bridge opens a second `*sql.DB` to the same file with `MaxOpenConns(1)`.** This means two `*sql.DB` instances share the same WAL file. WAL mode supports multiple readers + one writer, so this is safe from SQLite's perspective. However, both `*sql.DB` instances have their own connection pool, each with `MaxOpenConns(1)`. Intermute uses one connection, the bridge uses one connection: total = 2 concurrent writers possible. With `busy_timeout = 5000ms` on both sides, they will serialize via SQLite's write lock. This is correct, but the plan must confirm both `sql.DB` instances have `busy_timeout` set. The bridge sets it in the connection string and also via `db.Exec("PRAGMA busy_timeout = 5000")` — redundant but harmless.

---

### HIGH — H2: Sweep is a read-then-write race with `Reserve()`

**Severity:** P1 — sweep can release a lock that Reserve just committed, or Reserve can grant a lock on a row that sweep is about to release.
**Affected tasks:** Task 5 (sweep.go)

**The plan's sweep implementation:**

```go
// 1. TTL-expired locks
expiredLocks, err := s.findExpired(ctx, now)   // autocommit SELECT
// 2. Stale named_lock owners
staleLocks, err := s.findStalePIDs(ctx, now)    // autocommit SELECT
// Release all found locks
for _, l := range append(expiredLocks, staleLocks...) {
    s.Release(ctx, l.ID, "", "")               // autocommit UPDATE
}
```

**Failure narrative — sweep races with Reserve:**

```
Sweep:    SELECT id ... WHERE expires_at < NOW  → finds lock L (expires_at = now-1)
Reserve:  BEGIN IMMEDIATE
Reserve:  inline sweep UPDATE SET released_at WHERE expires_at < now  → releases L
Reserve:  conflict check → L is released, no conflict found
Reserve:  INSERT new lock N → commits
Sweep:    Release(L.ID) → UPDATE SET released_at WHERE id = L.ID AND released_at IS NULL
          → L is already released (released_at set by Reserve's inline sweep) → 0 rows affected, ok
```

This interleaving is actually safe because `Release()` is guarded by `released_at IS NULL` — it is idempotent. **However:** the sweep's `findStalePIDs` query also runs outside any transaction. If sweep finds a stale lock at time T, then between T and the `Release()` call, a new `Reserve()` could grant a new lock N with an overlapping pattern (having seen the stale lock as "still live" through the conflict check's inline sweep). Then sweep's `Release()` fires — but `Release(L.ID)` targets the old lock L, not new lock N. New lock N survives correctly.

The real risk is the **inline sweep in Reserve vs the external sweep**:

```
Reserve A: BEGIN IMMEDIATE (gets exclusive write lock)
Reserve A: inline sweep: marks lock L as released (expires_at < now)
Reserve A: conflict check: no conflicts
Reserve A: COMMIT → grants lock N
Sweep:     findExpired: SELECT WHERE expires_at < now → finds lock L (already released, released_at IS NOT NULL → skipped by WHERE clause) → safe
```

The inline sweep in `Reserve()` is correct. The external `Sweep()` is safe because `Release()` is idempotent. The risk is if the external sweep's collect phase and release phase are far apart in wall time. Since `findExpired` runs a SELECT without a lock, the collected IDs may include rows that have already been re-reserved under a new ID (impossible since IDs are UUIDs, not reused) or rows that have already been released by `Reserve()`'s inline sweep. Both are handled correctly by the `released_at IS NULL` guard in `Release()`.

**The one genuine hole:** `findStalePIDs` does not filter by `released_at IS NULL AND (expires_at IS NULL OR expires_at > now)`. The query is:

```sql
WHERE released_at IS NULL AND type = 'named_lock'
```

This includes locks with `expires_at` in the past that haven't been swept yet. `findExpired` will also find these. So a single lock can appear in both `expiredLocks` and `staleLocks`, and `Release()` will be called twice for the same ID. With `released_at IS NULL` guard, the second call is a no-op. But `onEvent` is called twice, emitting two `coordination.expired` events for the same lock. Monitoring that counts expiration events will double-count.

**Fix for the double-event bug:** Either de-duplicate the two lists by ID before releasing, or exclude TTL-expired rows from `findStalePIDs`:

```go
func (s *Store) findStalePIDs(ctx context.Context, now int64) ([]Lock, error) {
    rows, err := s.db.QueryContext(ctx, `SELECT ...
        FROM coordination_locks
        WHERE released_at IS NULL AND type = 'named_lock'
          AND (expires_at IS NULL OR expires_at >= ?)`, now)  // exclude already-expired
```

---

### HIGH — H3: Transfer's conflict check does not hold a write lock during the check phase

**Severity:** P1 — a concurrent `Reserve()` can grant a conflicting lock between Transfer's check and its UPDATE.
**Affected tasks:** Task 6 (Transfer)

**The plan's Transfer implementation:**

```go
tx, err := s.db.BeginTx(ctx, nil)                          // deferred tx
tx.ExecContext(ctx, "ROLLBACK; BEGIN IMMEDIATE")            // same C1 bug as Reserve
// Check for conflicts (reads fromOwner's and toOwner's patterns)
fromRows, _ := tx.QueryContext(...)
toRows, _ := tx.QueryContext(...)
// overlap check loop...
// Perform the transfer
res, err := tx.ExecContext(ctx, `UPDATE coordination_locks SET owner = ? ...`)
```

Even if the `ROLLBACK; BEGIN IMMEDIATE` bug (C1) is fixed, there is still a logical gap: the conflict check evaluates patterns from `toOwner`'s existing locks against `fromOwner`'s locks to be transferred. But it does not check whether any *third* agent's locks conflict with the newly transferred locks under `toOwner`. After transfer, `toOwner` holds locks that were valid for `fromOwner` but may overlap with a lock granted to agent C between when Transfer started and when it committed.

**Failure narrative:**

```
Transfer(from=A, to=B):  BEGIN IMMEDIATE → gets write lock
Transfer:  reads A's patterns: ["src/*.go"]
Transfer:  reads B's patterns: []  → no conflicts
Agent C:   blocks on IMMEDIATE until Transfer commits
Transfer:  UPDATE owner = B for A's lock on "src/*.go" → commits, releases write lock
Agent C:   BEGIN IMMEDIATE
Agent C:   conflict check: B now owns "src/*.go" exclusive
           → C's request for "src/main.go" is blocked → correct behavior

But consider:
Transfer(from=A, to=B):  reads B's existing locks
                          B has no locks → no conflict detected
Agent C:   IMMEDIATELY after Transfer commits, Reserve("src/*.go", owner=B) → C granted
           No wait — C cannot be granted if B now owns "src/*.go" → this is fine.
```

Actually `BEGIN IMMEDIATE` for the transfer is sufficient to serialize correctly against concurrent `Reserve()` calls, provided the C1 bug is fixed. The description above is not a race because `BEGIN IMMEDIATE` holds a write lock across the entire check-and-update. The real issue with Transfer is that **`fromRows.Scan` errors are silently dropped**:

```go
for fromRows.Next() {
    var p string
    fromRows.Scan(&p)   // error returned but ignored!
    fromPatterns = append(fromPatterns, p)
}
```

And similarly for `toRows.Scan`. A scan error leaves `p` as its zero value (empty string), which is appended to `fromPatterns`. `PatternsOverlap("", toPattern)` will either return `true` (false conflict, blocking a valid transfer) or `false` (missing conflict, allowing an incorrect transfer), depending on how `PatternsOverlap` handles empty strings.

**Fix:** Check `fromRows.Scan` and `toRows.Scan` errors. Also call `fromRows.Err()` after the loop:

```go
if err := fromRows.Scan(&p); err != nil {
    fromRows.Close()
    return 0, fmt.Errorf("scan fromOwner pattern: %w", err)
}
```

---

### HIGH — H4: `MirrorReserve` uses `INSERT OR IGNORE` — silent ID collision masking

**Severity:** P1 — if Intercore and Intermute independently generate the same UUID (astronomically unlikely but architecturally unsound), or if a replay bug causes duplicate IDs, the mirror silently drops the second insert.
**Affected tasks:** Task 7 (coordination_bridge.go)

**The plan's MirrorReserve:**

```go
_, err := b.db.Exec(`INSERT OR IGNORE INTO coordination_locks
    (id, type, owner, scope, pattern, exclusive, reason, ttl_seconds, created_at, expires_at)
    VALUES (?, 'file_reservation', ?, ?, ?, ?, ?, ?, ?, ?)`, ...)
```

`INSERT OR IGNORE` on a `PRIMARY KEY` conflict silently drops the row and returns `nil` error. If the same lock ID is mirrored twice (e.g., due to an HTTP retry), the second call is a no-op. This is correct for idempotency. But if a different reservation happens to have the same UUID as an existing lock (UUID collision or a bug in ID generation), the mirror will silently drop the new reservation, and monitoring will never see it in `coordination_locks`.

More importantly, `INSERT OR IGNORE` does not distinguish between "already mirrored (idempotent)" and "genuine ID conflict". If a genuine conflict exists (meaning the primary Intermute store has two rows with the same UUID, which would be a bug), the mirror silently loses one.

The correct pattern for idempotent mirroring is `INSERT OR REPLACE` (upsert) if the data should converge, or return an error on genuine conflicts. For this case, `INSERT OR IGNORE` is acceptable since UUIDs practically never collide, but the plan should document the semantic choice and add a check that verifies the existing row has the same owner/pattern when the ID already exists.

---

### HIGH — H5: The `ROLLBACK; BEGIN IMMEDIATE` pattern bypasses the `busy_timeout` retry path

**Severity:** P1 — under write contention from Intermute, Intercore's Reserve() will fail immediately instead of retrying.
**Affected tasks:** Task 1, Task 6

When `BEGIN IMMEDIATE` is issued as a raw string via `tx.ExecContext()`, the SQLite driver's busy handler is active but the Go `database/sql` layer does not retry. With `MaxOpenConns(1)` on both the Intercore and Intermute `*sql.DB` instances sharing the same WAL file, write contention is expected. The `busy_timeout = 5000ms` pragma tells SQLite to spin-wait for up to 5 seconds before returning `SQLITE_BUSY`. This is correct and will work.

However, since the bug in C1 means the implementation uses `BeginTx` + raw `ROLLBACK; BEGIN IMMEDIATE`, and if C1 is fixed to use `db.Conn()` + raw `BEGIN IMMEDIATE`, the `busy_timeout` pragma applies correctly (it is set per-connection). The fix path is safe.

The concern is specifically: if a caller receives `SQLITE_BUSY` from `BEGIN IMMEDIATE` (timeout exceeded), the plan has no retry loop. The caller gets an error. For a CLI tool this is fine (the user re-runs). For the Interlock MCP bridge (Task 8) which calls `ic` as a subprocess, a `SQLITE_BUSY` timeout will return exit code 1, and the Interlock tool will report a failure to the agent. The plan should document expected behavior under sustained contention and whether callers are expected to retry.

---

### MEDIUM — M1: PID liveness check is host-scoped; cross-host locks are never swept

**Severity:** P2 — named locks held by agents on remote hosts will never be identified as stale via PID check.
**Affected tasks:** Task 5 (sweep.go)

**The plan's sweep:**

```go
func parsePID(owner string) int {
    parts := strings.SplitN(owner, ":", 2)
    pid, err := strconv.Atoi(parts[0])
    ...
}
func pidAlive(pid int) bool {
    err := syscall.Kill(pid, 0)
    return err == nil || err == syscall.EPERM
}
```

The owner format is `"PID:hostname"`. The sweep parses the PID and calls `syscall.Kill(pid, 0)` without verifying the hostname matches the local host. If a lock was acquired by an agent on a different machine with PID 1234, and the local machine also has a live process with PID 1234 (likely — init/systemd is always PID 1 on every Linux host), `pidAlive(1234)` returns `true` and the lock is never swept.

The existing `internal/lock/lock.go` has the same design (inherited pattern) — `tryBreakStale` also calls `pidAlive` without host checking. This is a known limitation for filesystem locks.

For the SQLite coordination store, a PID from a different host should be compared against `os.Hostname()`. If the hostname does not match, PID liveness cannot be determined locally and the lock should fall back to TTL-based expiry only.

**Fix:**

```go
localHost, _ := os.Hostname()
func (s *Store) findStalePIDs(ctx context.Context, now int64) ([]Lock, error) {
    ...
    for rows.Next() {
        ...
        pid, host := parsePIDHost(l.Owner)
        if host != "" && host != localHost {
            continue  // cannot check remote PIDs; rely on TTL
        }
        if pid > 0 && !pidAlive(pid) {
            stale = append(stale, l)
        }
    }
}
```

---

### MEDIUM — M2: The inline sweep in `Reserve()` is inside `BEGIN IMMEDIATE` but emits no events

**Severity:** P2 — observability gap; expired locks swept during Reserve are invisible to monitoring.
**Affected tasks:** Task 1, Task 4

**The plan's inline sweep:**

```go
tx.ExecContext(ctx, `UPDATE coordination_locks SET released_at = ?
    WHERE released_at IS NULL AND expires_at IS NOT NULL AND expires_at < ?`, now, now)
```

This runs inside the `BEGIN IMMEDIATE` transaction and correctly serializes the expiry. However, `s.onEvent` is not called for these inline-swept locks. Task 4 wires `s.onEvent` for Reserve/Release/Sweep explicitly. The inline sweep in `Reserve()` is a silent side-channel that expires locks without any event emission.

The existing `Sweep()` method calls `s.onEvent(ctx, "coordination.expired", ...)` per lock. The inline sweep does a bulk `UPDATE` without collecting which rows were updated. To emit events, the plan would need to use `UPDATE ... RETURNING id, owner, pattern, scope` (which `modernc.org/sqlite` supports) or do a SELECT first.

The plan should document this gap explicitly: inline sweep is a correctness tool (ensures the conflict check sees a consistent state) but is not observable. If debugging lock starvation, operators will not see inline-swept expirations in the event log.

---

### MEDIUM — M3: `Check()` is not serialized — it races with concurrent `Reserve()` calls

**Severity:** P2 — `Check()` is a read-only operation that reports current conflicts but provides no guarantee. This is structurally fine for advisory checks but the plan uses it as a pre-condition in the Interlock hook.
**Affected tasks:** Task 3, Task 8

**The plan's pre-edit.sh hook:**

```bash
conflicts=$(ic --json coordination check --scope="$PROJECT_DIR" --pattern="$FILE_PATH" ...)
if [[ $? -eq 1 ]]; then
    echo '{"decision":"block",...}'
    exit 0
fi
# No conflict — auto-reserve
ic coordination reserve --owner="$INTERMUTE_AGENT_ID" ...
```

This is a TOCTOU window: check then reserve. Between the check (exit 0 = clear) and the reserve call, another agent may acquire an exclusive lock on the same pattern. The reserve call should be the authoritative check (Reserve returns conflict info). The pre-check is an optimization to give better error messages, but the hook treats it as the gating decision and calls reserve separately.

If `ic coordination reserve` returns a conflict, the hook is already past the decision point and will not block the edit — the tool just runs the auto-reserve silently with `|| true`. This means the block logic is never exercised on the second concurrent writer.

**Fix:** The hook should call `ic coordination reserve` as the single gating operation and inspect its exit code/output:

```bash
result=$(ic --json coordination reserve --owner="..." --scope="..." --pattern="..." --ttl=900 ... 2>/dev/null)
if [[ $(echo "$result" | jq -r '.conflict // empty') != "" ]]; then
    blocker=$(echo "$result" | jq -r '.conflict.blocker_owner // "unknown"')
    echo '{"decision":"block","reason":"INTERLOCK: '"$FILE_PATH"' reserved by '"$blocker"'"}'
    exit 0
fi
```

---

### MEDIUM — M4: The `Transfer()` method has a missing `rows.Err()` check for `fromRows`

**Severity:** P2 — I/O errors during pattern collection are silently dropped (matches the project's established pattern from MEMORY.md: "Always check rows.Err() after rows.Next() loops").
**Affected tasks:** Task 6

The plan's Transfer code calls `fromRows.Close()` at the end of the `fromRows.Next()` loop but never checks `fromRows.Err()`. Similarly `toRows.Err()` is not checked. An I/O error mid-scan will truncate `fromPatterns` silently, causing an incomplete conflict check that may allow a logically incorrect transfer.

**Fix:** Add `if err := fromRows.Err(); err != nil { return 0, err }` after each scan loop, before `rows.Close()`.

---

### LOW — L1: Migration guard uses `CREATE TABLE IF NOT EXISTS` but also checks `isTableExistsError` — the helper does not exist

**Severity:** compile error — will block Task 1 from building.
**Affected tasks:** Task 1

The plan's migration block ends with:

```go
if err != nil && !isTableExistsError(err) {
    return fmt.Errorf("v20 coordination_locks: %w", err)
}
```

`isTableExistsError` is not defined in `db.go`. Only `isDuplicateColumnError` exists. Since `CREATE TABLE IF NOT EXISTS` never returns an error for existing tables, this error check is dead code anyway. Remove it entirely.

---

### LOW — L2: `NewStore` signature change in Task 4 breaks the Task 1 `NewStore(db)` call

**Severity:** compilation error in sequencing — Task 1 creates `NewStore(db *sql.DB)`, Task 4 changes it to `NewStore(db *sql.DB, onEvent EventFunc)`.
**Affected tasks:** Task 1, Task 4

Any code written in Task 1 that calls `NewStore(db)` will fail to compile after Task 4 changes the signature. The plan should either add `onEvent` as an optional field set after construction (`store.OnEvent = fn`) or use a functional options pattern to avoid breaking callers. Since `EventFunc` is nil-safe (the plan checks `if s.onEvent != nil`), a `WithEventFunc(fn) func(*Store)` option or a `SetEventFunc` method avoids the breaking signature change.

---

### LOW — L3: `db.SetMaxOpenConns(1)` called after `db.Exec("PRAGMA busy_timeout")` in the bridge

**Severity:** ordering issue — queries may race before the connection limit is set.
**Affected tasks:** Task 7

In `NewCoordinationBridge`:

```go
db, err := sql.Open(...)
...
db.SetMaxOpenConns(1)       // set after sql.Open
db.Exec("PRAGMA busy_timeout = 5000")
db.Exec("PRAGMA journal_mode = WAL")
```

`sql.Open` is lazy — it does not open a connection. The first `db.Exec(...)` call triggers connection opening, and `MaxOpenConns` is already set to 1 before any query fires. This ordering is actually correct. However, the PRAGMAs are executed as autocommit statements. If the connection DSN already set `_pragma=journal_mode%3DWAL`, the explicit `PRAGMA journal_mode = WAL` is a no-op. But for `busy_timeout`, the DSN format uses `_pragma=busy_timeout%3D5000`. The intercore `db.go` comments note "DSN _pragma may not be applied reliably on all driver versions" and sets PRAGMAs explicitly after open for this reason — the bridge should do the same, which it does. Good.

---

### LOW — L4: `Sweep()` `dryRun` check short-circuits event emission but is only checked once

**Severity:** minor logic error — the `dryRun` path should also skip the `findExpired`/`findStalePIDs` queries for efficiency, but currently runs them.
**Affected tasks:** Task 5

The plan:

```go
result.Total = result.Expired + result.Stale

if dryRun || result.Total == 0 {
    return result, nil
}
```

This is a correct dry-run check — it reports what would be swept without acting. This is intentional. No bug here, but `olderThan time.Duration` parameter is accepted by `Sweep()` but never used in `findExpired` or `findStalePIDs`. The `ic coordination sweep --older-than=5m` CLI flag advertised in Task 3 would be silently ignored. The implementation should apply `olderThan` as an additional filter: only sweep locks older than `now - olderThan`.

---

## Summary Table

| ID | Severity | Task | Issue |
|----|----------|------|-------|
| C1 | P0 CRITICAL | 1, 6 | `ROLLBACK; BEGIN IMMEDIATE` inside `*sql.Tx` corrupts database/sql connection state |
| C2 | P0 CRITICAL | 1 | `isTableExistsError` does not exist; will not compile |
| C3 | P1 HIGH | 1 | Conflict check excludes same owner, allowing type-escalation contradiction |
| H1 | P1 HIGH | 7 | Dual-write creates observable inconsistency window for ic coordination check |
| H2 | P1 HIGH | 5 | Sweep double-counts/double-events for locks that are both expired and stale-PID |
| H3 | P1 HIGH | 6 | `fromRows.Scan` / `toRows.Scan` errors silently ignored, corrupting conflict check |
| H4 | P1 HIGH | 7 | `INSERT OR IGNORE` masks genuine ID conflicts in mirror without warning |
| H5 | P1 HIGH | 1, 6 | `busy_timeout` retry path works, but plan has no documented behavior for timeout |
| M1 | P2 MEDIUM | 5 | PID liveness check does not compare hostname; cross-host locks never swept |
| M2 | P2 MEDIUM | 1, 4 | Inline sweep in Reserve() expires locks silently — no event emitted, invisible to monitoring |
| M3 | P2 MEDIUM | 3, 8 | pre-edit.sh hook is TOCTOU: check-then-reserve instead of reserve-as-gate |
| M4 | P2 MEDIUM | 6 | Missing `rows.Err()` after `fromRows.Next()` and `toRows.Next()` loops |
| L1 | compile | 1 | `isTableExistsError` reference will not compile (same as C2, different call site) |
| L2 | compile | 1, 4 | `NewStore` signature changes in Task 4 break Task 1 callers |
| L3 | minor | 7 | PRAGMA ordering in bridge is correct but should be documented |
| L4 | minor | 5 | `olderThan` parameter accepted but never applied to queries |

---

## Recommended Changes Before Implementation

**Before writing any code:**

1. **Replace the `ROLLBACK; BEGIN IMMEDIATE` pattern** with `db.Conn()` + raw `BEGIN IMMEDIATE` in both `Reserve()` and `Transfer()`. This is the only correct way to use `BEGIN IMMEDIATE` with `database/sql` and `modernc.org/sqlite`. Use the committed flag pattern shown in C1's fix section. All existing transaction handling in this codebase uses `BeginTx(ctx, nil)` for deferred transactions — the new coordination store needs a different approach for IMMEDIATE writes.

2. **Remove `isTableExistsError`** from the migration block. `CREATE TABLE IF NOT EXISTS` is sufficient and the helper does not exist.

3. **Fix `fromRows.Scan` and `toRows.Scan` error handling** in Transfer before writing the test (the tests will not catch silent scan errors).

4. **Add `rows.Err()` checks** after all `rows.Next()` loops in `findExpired`, `findStalePIDs`, and Transfer.

5. **Fix pre-edit.sh hook** to use `ic coordination reserve` as the single authoritative gating check, not a check-then-reserve pattern.

6. **De-duplicate** the `expiredLocks` + `staleLocks` slices in `Sweep()` before the release loop to prevent double event emission.

7. **Add hostname comparison** in `findStalePIDs` before calling `pidAlive`.

8. **Use `SetEventFunc` method** instead of changing `NewStore` signature in Task 4 to avoid breaking Task 1 callers.
