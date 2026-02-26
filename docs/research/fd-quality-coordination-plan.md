# Quality Review: Native Kernel Coordination Plan

**Reviewer:** fd-quality (Flux-drive Quality & Style)
**Plan:** `docs/plans/2026-02-25-native-kernel-coordination.md`
**Date:** 2026-02-25
**Scope:** Go (Tasks 1–8), Shell (Task 8 pre-edit.sh)

---

## Summary

The plan is architecturally sound and follows the right instincts (SQLite for serialization, glob overlap reuse, dual-write migration). However there are six concrete defects that will cause bugs or test failures if implemented as written, plus several convention mismatches with the existing Intercore codebase. None are blockers to the overall design, but all should be resolved before the implementation tasks are handed off.

---

## Finding 1 — CRITICAL: `ROLLBACK; BEGIN IMMEDIATE` inside `BeginTx` is a database/sql protocol violation

**Tasks affected:** Task 1 (`Reserve`), Task 6 (`Transfer`)

**Location:** `store.go` — `Reserve()` and `Transfer()`:

```go
tx, err := s.db.BeginTx(ctx, nil)
// ...
if _, err := tx.ExecContext(ctx, "ROLLBACK; BEGIN IMMEDIATE"); err != nil {
```

**Problem:** `database/sql` wraps the connection in a transaction state machine. Once `BeginTx` succeeds, the driver has issued `BEGIN` on the underlying connection. Executing a raw `ROLLBACK` through `ExecContext` on that same `*sql.Tx` corrupts `database/sql`'s internal state — the connection is returned to the pool in an unknown transaction state, leading to silent data corruption or panics on subsequent use.

The `ROLLBACK; BEGIN IMMEDIATE` pattern is a workaround used at the raw driver level (e.g., `mattn/go-sqlite3` with `_txlock=immediate` DSN option). It is not safe through `database/sql`'s `Tx` abstraction.

**Fix:** Pass `sql.TxOptions{Isolation: sql.LevelSerializable}` to `BeginTx`. For modernc.org/sqlite, this maps to `BEGIN IMMEDIATE`:

```go
tx, err := s.db.BeginTx(ctx, &sql.TxOptions{Isolation: sql.LevelSerializable})
if err != nil {
    return nil, fmt.Errorf("begin immediate: %w", err)
}
defer tx.Rollback()
```

If the driver does not honor `LevelSerializable` as `IMMEDIATE` (verify against modernc behavior), the alternative is to set `_txlock=immediate` in the DSN at `Open` time, so all transactions on this DB handle are immediate. Do not use the raw SQL statement approach through `database/sql`.

---

## Finding 2 — HIGH: `*int64` for nullable timestamps conflicts with established codebase convention

**Tasks affected:** Task 1 (`types.go`, `scanLock`)

**Location:** `types.go`:
```go
ExpiresAt  *int64 `json:"expires_at,omitempty"`
ReleasedAt *int64 `json:"released_at,omitempty"`
```

And in `scanLock`:
```go
return rows.Scan(&l.ID, ..., &l.ExpiresAt, &l.ReleasedAt, ...)
```

**Problem:** The existing Intercore stores use `sql.NullString` as the scan target for nullable columns, then convert to `*string` after validity check (confirmed in `runtrack/store.go` and `action/store.go`). Scanning directly into `*int64` with `modernc.org/sqlite` is not guaranteed to work correctly — the driver may not populate the pointed-to value from NULL without an intermediate `sql.NullInt64`. This will cause silent zero-value corruption when a lock has no expiry.

The `Reason`, `DispatchID`, and `RunID` fields in `Lock` have the same problem — they are `string` in the struct but map to nullable `TEXT` columns. Scanning NULL into a `string` produces an empty string, which is ambiguous (was the field absent or explicitly set to empty?).

**Fix:** Follow the established `sql.NullInt64` / `sql.NullString` scan-then-assign pattern:

```go
func scanLock(rows *sql.Rows, l *Lock) error {
    var expiresAt, releasedAt sql.NullInt64
    var reason, dispatchID, runID sql.NullString
    err := rows.Scan(
        &l.ID, &l.Type, &l.Owner, &l.Scope, &l.Pattern, &l.Exclusive,
        &reason, &l.TTLSeconds, &l.CreatedAt,
        &expiresAt, &releasedAt, &dispatchID, &runID,
    )
    if err != nil {
        return err
    }
    if expiresAt.Valid  { l.ExpiresAt  = &expiresAt.Int64 }
    if releasedAt.Valid { l.ReleasedAt = &releasedAt.Int64 }
    if reason.Valid     { l.Reason     = reason.String }
    if dispatchID.Valid { l.DispatchID = dispatchID.String }
    if runID.Valid      { l.RunID      = runID.String }
    return nil
}
```

---

## Finding 3 — HIGH: `EventFunc` signature does not match codebase event handler contract

**Tasks affected:** Task 4 (`store.go` event callback)

**Location:** `store.go` proposed type:
```go
type EventFunc func(ctx context.Context, eventType, lockID, owner, pattern, scope, reason string, runID string)
```

**Problem:** The existing event system uses `event.Handler` — a `func(ctx context.Context, e event.Event) error` — registered via `Notifier.Subscribe`. The plan's `EventFunc` is a bespoke flat-argument function with no error return. This:

1. Cannot be registered with the existing `Notifier` without an adapter shim, introducing unnecessary indirection.
2. Drops error returns, so the caller cannot distinguish emission failures.
3. The `event.Event` struct already carries `RunID`, `Source`, `Type`, `Reason`, `FromState`, `ToState` — the plan's flat args duplicate this.

**Fix:** Change `Store.onEvent` to accept an `event.Event` value and return an error, matching `event.Handler`:

```go
// In store.go
type OnEventFunc func(ctx context.Context, e event.Event) error

type Store struct {
    db      *sql.DB
    onEvent OnEventFunc // nil = no-op
}
```

Call it after commit:

```go
if s.onEvent != nil {
    e := event.Event{
        RunID:  lock.RunID,
        Source: event.SourceCoordination,
        Type:   "coordination.acquired",
        Reason: lock.Reason,
    }
    _ = s.onEvent(ctx, e) // log error but don't fail the reserve
}
```

This integrates cleanly with the existing `Notifier.Subscribe` pattern without adapter code.

---

## Finding 4 — MEDIUM: `rows.Scan` errors are silently dropped in `Transfer`

**Tasks affected:** Task 6 (`Transfer`)

**Location:** `store.go` — `Transfer()`:

```go
for fromRows.Next() {
    var p string
    fromRows.Scan(&p)   // error ignored
    fromPatterns = append(fromPatterns, p)
}
fromRows.Close()

// ...
for toRows.Next() {
    var toPattern string
    toRows.Scan(&toPattern)   // error ignored
```

**Problem:** Silently ignoring `rows.Scan` errors means an I/O failure mid-iteration appends empty strings to the patterns slice. The overlap check then operates on corrupt input and may allow a conflicting transfer when it should have rejected it. The project convention (confirmed in `runtrack/store.go`) is to return scan errors immediately.

Additionally, `fromRows.Err()` and `toRows.Err()` are never checked after the loops. This is also missing from the conflict-check loop in `Reserve` — the plan checks `rows.Err()` there but the error from `rows.Close()` (implicitly deferred) is not checked. The project uses `defer rows.Close()` + `rows.Err()` check after the loop.

**Fix:** In `Transfer`, assign and check scan errors:

```go
if err := fromRows.Scan(&p); err != nil {
    fromRows.Close()
    return 0, fmt.Errorf("scan from-patterns: %w", err)
}
```

Check `fromRows.Err()` and `toRows.Err()` after each loop. Keep `defer rows.Close()` for all query results so the connection is released even on early return.

---

## Finding 5 — MEDIUM: `CoordinationBridge` in Task 7 opens SQLite with unreliable DSN PRAGMAs

**Tasks affected:** Task 7 (`coordination_bridge.go`)

**Location:**
```go
db, err := sql.Open("sqlite", "file:"+dbPath+"?_pragma=journal_mode%3DWAL&_pragma=busy_timeout%3D5000")
// ...
db.Exec("PRAGMA busy_timeout = 5000")
db.Exec("PRAGMA journal_mode = WAL")
```

**Problem:** The intercore `CLAUDE.md` documents explicitly: "PRAGMAs must be set explicitly after `sql.Open` (DSN `_pragma` is unreliable)." The bridge does both (good on the explicit calls) but also leaves the DSN PRAGMAs in, creating an inconsistency. More critically, the `db.Exec` calls return errors that are silently discarded. If the PRAGMA application fails — which can happen when two connections attempt WAL mode setup on the same file — the bridge silently proceeds with an unconfigured connection.

**Fix:** Mirror the `db.Open` pattern exactly:

```go
sqlDB, err := sql.Open("sqlite", "file:"+dbPath)
if err != nil {
    return nil, fmt.Errorf("coordination bridge open: %w", err)
}
sqlDB.SetMaxOpenConns(1)
if _, err := sqlDB.Exec(fmt.Sprintf("PRAGMA busy_timeout = %d", 5000)); err != nil {
    sqlDB.Close()
    return nil, fmt.Errorf("coordination bridge: set busy_timeout: %w", err)
}
if _, err := sqlDB.Exec("PRAGMA journal_mode = WAL"); err != nil {
    sqlDB.Close()
    return nil, fmt.Errorf("coordination bridge: set WAL: %w", err)
}
```

Drop the DSN PRAGMA parameters entirely — they are redundant and flagged as unreliable by the project's own documentation.

---

## Finding 6 — MEDIUM: Migration guard condition is wrong for a new table (v19→v20)

**Tasks affected:** Task 1 (`db.go` migration block)

**Location:**
```go
if currentVersion >= 3 && currentVersion < 20 {
    _, err := tx.ExecContext(ctx, `CREATE TABLE IF NOT EXISTS coordination_locks ...`)
    if err != nil && !isTableExistsError(err) {
        return fmt.Errorf("v20 coordination_locks: %w", err)
    }
    // Indexes created by schema.sql (IF NOT EXISTS)
}
```

**Problems:**

1. The lower bound `currentVersion >= 3` is wrong for a v19→v20 migration. The existing pattern for new tables (see v11 in `db.go`) uses the version at which the parent table was introduced as the lower bound because the DDL block in `schema.sql` already creates the table for fresh installs. For a fully new table with no dependencies, the lower bound should be `currentVersion >= 19` (only migrate databases that already have all prior schema applied). Using `>= 3` will attempt to create the table on databases as old as v3, before the schema stabilized.

2. `isTableExistsError` is not defined in `db.go` — the existing helper is `isDuplicateColumnError`. Since `CREATE TABLE IF NOT EXISTS` never returns a "table already exists" error (the `IF NOT EXISTS` suppresses it), this guard is unnecessary. Remove the error filter entirely and use standard `%w` wrapping.

3. The indexes are referenced as "created by schema.sql" but `schema.sql` runs via `tx.ExecContext(ctx, schemaDDL)` after all migration guards. The migration block should include the `CREATE INDEX IF NOT EXISTS` statements directly, or the comment should be removed — the current wording is misleading about execution order.

**Fix:**

```go
if currentVersion >= 19 && currentVersion < 20 {
    stmts := []string{
        `CREATE TABLE IF NOT EXISTS coordination_locks (
            id TEXT PRIMARY KEY,
            type TEXT NOT NULL CHECK(type IN ('file_reservation','named_lock','write_set')),
            owner TEXT NOT NULL,
            scope TEXT NOT NULL,
            pattern TEXT NOT NULL,
            exclusive INTEGER NOT NULL DEFAULT 1,
            reason TEXT,
            ttl_seconds INTEGER,
            created_at INTEGER NOT NULL,
            expires_at INTEGER,
            released_at INTEGER,
            dispatch_id TEXT,
            run_id TEXT)`,
        `CREATE INDEX IF NOT EXISTS idx_coord_active ON coordination_locks(scope, type) WHERE released_at IS NULL`,
        `CREATE INDEX IF NOT EXISTS idx_coord_owner ON coordination_locks(owner) WHERE released_at IS NULL`,
        `CREATE INDEX IF NOT EXISTS idx_coord_expires ON coordination_locks(expires_at) WHERE released_at IS NULL AND expires_at IS NOT NULL`,
    }
    for _, stmt := range stmts {
        if _, err := tx.ExecContext(ctx, stmt); err != nil {
            return fmt.Errorf("migrate v19→v20 coordination_locks: %w", err)
        }
    }
}
```

---

## Finding 7 — LOW: Test helper naming diverges from established project convention

**Tasks affected:** Task 1 (store_test.go), Task 5 (sweep_test.go)

**Location:** Plan Step 7 says "Use `tempDB` pattern from `db_test.go`."

**Problem:** This is imprecise. The actual pattern used in Intercore package tests is not `tempDB` — it is `setupTestStore(t)` (confirmed in `runtrack/store_test.go`), which opens the DB, runs `Migrate`, constructs the store, and registers cleanup — all in one call. The `tempDB` helper in `db_test.go` is only used within the `db` package itself to test the DB layer directly.

The `coordination` package tests should follow `setupTestStore`'s pattern:

```go
func setupTestStore(t *testing.T) *Store {
    t.Helper()
    dir := t.TempDir()
    path := filepath.Join(dir, "test.db")
    d, err := db.Open(path, 100*time.Millisecond)
    if err != nil {
        t.Fatalf("Open: %v", err)
    }
    if err := d.Migrate(context.Background()); err != nil {
        t.Fatalf("Migrate: %v", err)
    }
    t.Cleanup(func() { d.Close() })
    return New(d.SqlDB(), nil) // nil onEvent for unit tests
}
```

Test names should follow the `TestStore_<Action>_<Case>` convention established in `runtrack/store_test.go`, not generic `TestReserve` or `TestSweep` names. Example: `TestStore_Reserve_Conflict`, `TestStore_Release_ByOwnerScope`.

---

## Finding 8 — LOW: `icclient.Check` error-type assertion should use `errors.As`

**Tasks affected:** Task 8 (`icclient.go`)

**Location:**
```go
if exitErr, ok := err.(*exec.ExitError); ok && exitErr.ExitCode() == 1 {
    return out, true, nil
}
```

**Problem:** Using a direct type assertion `err.(*exec.ExitError)` does not unwrap error chains. If `exec.Command.Output()` wraps the exit error (which it does not today, but is a fragile assumption), the assertion fails silently. The project convention for sentinel error checks uses `errors.Is`; for typed error extraction the Go standard is `errors.As`:

```go
var exitErr *exec.ExitError
if errors.As(err, &exitErr) && exitErr.ExitCode() == 1 {
    return out, true, nil
}
```

This is also the pattern used in `lock.go` (`errors.Is(err, syscall.EPERM)`), consistent with the rest of the codebase.

---

## Finding 9 — LOW: `findStalePIDs` unused parameter and trailing comma

**Tasks affected:** Task 5 (`sweep.go`)

**Location:**
```go
func (s *Store) findStalePIDs(ctx context.Context, now int64) ([]Lock, error) {
    rows, err := s.db.QueryContext(ctx, `SELECT ... WHERE released_at IS NULL AND type = 'named_lock'`, )
```

**Problems:**

1. The `now int64` parameter is accepted but never used in the function body. This will produce a compile error in Go (`now declared and not used`) unless the query is intended to filter by expiry — in which case the filter `AND (expires_at IS NULL OR expires_at > ?)` is missing, creating an inconsistency with the `findExpired` query which already handles TTL expiry.

2. The trailing comma after the query string (`, )`) is a syntax artifact that Go will accept but is a style inconsistency — all other `QueryContext` calls in the codebase do not have trailing commas on single-argument calls.

**Fix:** Either use `now` in the query (to exclude locks that are already caught by TTL expiry) or remove the parameter:

```go
func (s *Store) findStalePIDs(ctx context.Context) ([]Lock, error) {
    rows, err := s.db.QueryContext(ctx,
        `SELECT id, type, owner, scope, pattern, exclusive,
         reason, ttl_seconds, created_at, expires_at, released_at, dispatch_id, run_id
         FROM coordination_locks
         WHERE released_at IS NULL AND type = 'named_lock'
           AND (expires_at IS NULL OR expires_at > ?)`, time.Now().Unix())
```

---

## Finding 10 — LOW: `parsePID` guard is unreachable as written

**Tasks affected:** Task 5 (`sweep.go`)

**Location:**
```go
func parsePID(owner string) int {
    parts := strings.SplitN(owner, ":", 2)
    if len(parts) < 1 {   // unreachable
        return 0
    }
```

**Problem:** `strings.SplitN` with `n=2` always returns at least one element (the whole string) when the separator is not found, and exactly two elements when it is found. `len(parts) < 1` is never true. The actual guard should be `len(parts) < 2` to detect the case where the owner string has no colon:

```go
parts := strings.SplitN(owner, ":", 2)
if len(parts) < 2 {
    return 0
}
```

This matches the identical pattern in `lock.go`'s `writeOwnerFile`, which uses `len(parts) == 2` as the condition to extract the PID.

---

## Finding 11 — LOW: `pidAlive` uses `err == syscall.EPERM` instead of `errors.Is`

**Tasks affected:** Task 5 (`sweep.go`)

**Location:**
```go
func pidAlive(pid int) bool {
    err := syscall.Kill(pid, 0)
    return err == nil || err == syscall.EPERM
}
```

**Problem:** The existing `lock.go` already defines the identical function and uses `errors.Is(err, syscall.EPERM)` for the comparison. Direct `==` comparison of `syscall.Errno` values works in practice but diverges from the codebase's established pattern.

Do not duplicate this function — import or move it to a shared location (e.g., `internal/coordination/proc.go`) or directly reuse `lock.go`'s `pidAlive`. If coordination and lock packages are both in `internal/`, create a shared `internal/proc/proc.go` with the `PidAlive` function and call it from both.

---

## Convention Summary

| Area | Established pattern | Plan's deviation |
|---|---|---|
| Nullable int64 columns | `sql.NullInt64` scan, then `*int64` assign | Direct `*int64` scan |
| Nullable string columns | `sql.NullString` scan, then `*string` or `string` assign | Direct `string` scan |
| Event callbacks | `event.Handler` (`func(ctx, Event) error`) | Bespoke flat-arg `EventFunc` |
| Test store helpers | `setupTestStore(t)` opens+migrates+cleans | Plan references `tempDB` |
| Test naming | `TestStore_Action_Case` | Plan says `TestReserve`, `TestSweep` |
| Sentinel errors | `errors.Is` / `errors.As` | Direct type assertion in icclient |
| PRAGMA setting | Explicit after `sql.Open`, errors checked | DSN + silent `db.Exec` in bridge |

---

## Items Not Flagged

- The glob overlap NFA algorithm copy (Task 2) is explicitly sanctioned — no L1→L1 import, copy is correct approach.
- The `uuid.NewString()` call is fine — `github.com/google/uuid` is already an indirect dependency in `go.mod`.
- The `BEGIN IMMEDIATE` serialization goal is correct — SQLite requires it for atomic read-check-write; only the mechanism for achieving it is wrong.
- The `INSERT OR IGNORE` in `MirrorReserve` is appropriate for dual-write idempotency.
- The `olderThan time.Duration` parameter in `Sweep` is declared but only used implicitly through the TTL path — the plan should clarify whether it filters by `created_at + olderThan` as a floor, or is reserved for a future stale-age check.
