# Native Kernel Coordination Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use clavain:executing-plans to implement this plan task-by-task.

**Goal:** Unify file reservations, named locks, and dispatch write-sets into a single `coordination_locks` table in Intercore's SQLite, then incrementally migrate Intermute and Interlock to use it.

**Architecture:** New `internal/coordination/` package in Intercore with Store (SQLite, `BEGIN IMMEDIATE`), glob overlap algorithm (copied from Intermute), CLI commands (`ic coordination`), event bus integration, and sweeper. Intermute dual-writes during migration. Interlock becomes a thin bridge to `ic`.

**Tech Stack:** Go 1.22, modernc.org/sqlite, Intercore CLI (manual arg parsing), Intercore event bus (`event.Notifier`), Intermute SQLite store, Interlock MCP (mcp-go)

---

## Task 1: Coordination Store — Schema and Migration (F1)

**Bead:** iv-ehx2s
**Phase:** executing (as of 2026-02-25T23:36:06Z)
**Files:**
- Modify: `core/intercore/internal/db/db.go` (bump version 19→20, add migration block)
- Modify: `core/intercore/internal/db/schema.sql` (add `coordination_locks` table + indexes)
- Create: `core/intercore/internal/coordination/store.go`
- Create: `core/intercore/internal/coordination/types.go`
- Test: `core/intercore/internal/coordination/store_test.go`
- Test: `core/intercore/internal/db/db_test.go` (update version assertions)

**Step 1: Write the schema additions**

Add to `core/intercore/internal/db/schema.sql`:

```sql
CREATE TABLE IF NOT EXISTS coordination_locks (
    id           TEXT PRIMARY KEY,
    type         TEXT NOT NULL CHECK(type IN ('file_reservation', 'named_lock', 'write_set')),
    owner        TEXT NOT NULL,
    scope        TEXT NOT NULL,
    pattern      TEXT NOT NULL,
    exclusive    INTEGER NOT NULL DEFAULT 1,
    reason       TEXT,
    ttl_seconds  INTEGER,
    created_at   INTEGER NOT NULL,
    expires_at   INTEGER,
    released_at  INTEGER,
    dispatch_id  TEXT,
    run_id       TEXT
);

CREATE INDEX IF NOT EXISTS idx_coord_active ON coordination_locks(scope, type)
    WHERE released_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_coord_owner ON coordination_locks(owner)
    WHERE released_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_coord_expires ON coordination_locks(expires_at)
    WHERE released_at IS NULL AND expires_at IS NOT NULL;
```

**Step 2: Write the migration in db.go**

In `core/intercore/internal/db/db.go`:
- Bump `currentSchemaVersion` and `maxSchemaVersion` to `20`
- Add migration guard block for v19→v20 in `Migrate()`:

```go
// Migration from v19 to v20: add coordination_locks table.
// Lower bound is >= 19 (current max version), not >= 3.
// CREATE TABLE IF NOT EXISTS handles idempotency — no need for isTableExistsError guard
// (that helper doesn't exist in db.go; only isDuplicateColumnError exists).
if currentVersion >= 19 && currentVersion < 20 {
    if _, err := tx.ExecContext(ctx, `CREATE TABLE IF NOT EXISTS coordination_locks (
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
        run_id TEXT)`); err != nil {
        return fmt.Errorf("v20 coordination_locks: %w", err)
    }
    // Also create coordination_events table (see Task 4):
    if _, err := tx.ExecContext(ctx, `CREATE TABLE IF NOT EXISTS coordination_events (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        lock_id TEXT NOT NULL,
        run_id TEXT,
        event_type TEXT NOT NULL,
        owner TEXT NOT NULL,
        pattern TEXT NOT NULL,
        scope TEXT NOT NULL,
        reason TEXT,
        created_at INTEGER NOT NULL)`); err != nil {
        return fmt.Errorf("v20 coordination_events: %w", err)
    }
    // Indexes created by schema.sql (IF NOT EXISTS)
}
```

**Step 3: Update db_test.go version assertions**

Change `want 19` → `want 20` in `TestMigrate_CreatesTablesAndVersion`. Add `"coordination_locks"` to the table existence check list.

**Step 4: Run migration tests**

Run: `cd core/intercore && go test -race ./internal/db/ -v`
Expected: PASS with updated version checks

**Step 5: Write types.go**

Create `core/intercore/internal/coordination/types.go`:

```go
package coordination

import "time"

const (
    TypeFileReservation = "file_reservation"
    TypeNamedLock       = "named_lock"
    TypeWriteSet        = "write_set"
)

type Lock struct {
    ID          string     `json:"id"`
    Type        string     `json:"type"`
    Owner       string     `json:"owner"`
    Scope       string     `json:"scope"`
    Pattern     string     `json:"pattern"`
    Exclusive   bool       `json:"exclusive"`
    Reason      string     `json:"reason,omitempty"`
    TTLSeconds  int        `json:"ttl_seconds,omitempty"`
    CreatedAt   int64      `json:"created_at"`
    ExpiresAt   *int64     `json:"expires_at,omitempty"`
    ReleasedAt  *int64     `json:"released_at,omitempty"`
    DispatchID  string     `json:"dispatch_id,omitempty"`
    RunID       string     `json:"run_id,omitempty"`
}

type ConflictInfo struct {
    BlockerID      string `json:"blocker_id"`
    BlockerOwner   string `json:"blocker_owner"`
    BlockerPattern string `json:"blocker_pattern"`
    BlockerReason  string `json:"blocker_reason,omitempty"`
}

type ReserveResult struct {
    Lock      *Lock          `json:"lock,omitempty"`
    Conflict  *ConflictInfo  `json:"conflict,omitempty"`
}

// ListFilter controls what List() returns.
type ListFilter struct {
    Scope    string
    Owner    string
    Type     string
    Active   bool // if true, only released_at IS NULL
}

func (l *Lock) IsActive() bool {
    if l.ReleasedAt != nil {
        return false
    }
    if l.ExpiresAt != nil && *l.ExpiresAt < time.Now().Unix() {
        return false
    }
    return true
}
```

**Step 6: Write store.go with Reserve, Release, Check, List**

Create `core/intercore/internal/coordination/store.go`:

```go
package coordination

import (
    "context"
    "database/sql"
    "fmt"
    "time"
)

// generateID produces an 8-char base36 ID matching Intercore convention (dispatch, run, etc.).
// Extract from internal/dispatch/dispatch.go to a shared internal/idgen/ package, or copy the pattern.
func generateID() string {
    // Same algorithm as dispatch.go: base36-encode crypto/rand bytes, truncate to 8 chars
    // See internal/dispatch/dispatch.go for reference implementation
    b := make([]byte, 5)
    rand.Read(b)
    return strings.ToLower(base36Encode(b))[:8]
}

type Store struct {
    db *sql.DB
}

func NewStore(db *sql.DB) *Store {
    return &Store{db: db}
}

// Reserve acquires a coordination lock. Uses BEGIN IMMEDIATE for serializable writes.
// Returns the lock on success, or ConflictInfo if blocked.
func (s *Store) Reserve(ctx context.Context, lock Lock) (*ReserveResult, error) {
    // Validate glob complexity BEFORE any DB access to prevent DoS via pathological patterns.
    // ValidateComplexity checks MaxTokens and MaxWildcards (copied from Intermute's glob package).
    if err := ValidateComplexity(lock.Pattern); err != nil {
        return nil, fmt.Errorf("invalid pattern: %w", err)
    }

    if lock.ID == "" {
        lock.ID = generateID()
    }
    lock.CreatedAt = time.Now().Unix()
    if lock.TTLSeconds > 0 {
        exp := lock.CreatedAt + int64(lock.TTLSeconds)
        lock.ExpiresAt = &exp
    }

    // BEGIN IMMEDIATE via LevelSerializable — modernc.org/sqlite maps this correctly.
    // Do NOT use raw "ROLLBACK; BEGIN IMMEDIATE" inside BeginTx — it corrupts database/sql state.
    tx, err := s.db.BeginTx(ctx, &sql.TxOptions{Isolation: sql.LevelSerializable})
    if err != nil {
        return nil, fmt.Errorf("begin immediate: %w", err)
    }
    defer tx.Rollback()

    // Inline sweep of expired locks (same-transaction, sentinel pattern).
    // NOTE: Inline sweep does NOT emit events (performance tradeoff — runs on every Reserve).
    // External `ic coordination sweep` emits coordination.expired events per cleaned lock.
    now := time.Now().Unix()
    tx.ExecContext(ctx, `UPDATE coordination_locks SET released_at = ?
        WHERE released_at IS NULL AND expires_at IS NOT NULL AND expires_at < ?`, now, now)

    // Check for conflicts
    rows, err := tx.QueryContext(ctx, `SELECT id, owner, pattern, reason, exclusive
        FROM coordination_locks
        WHERE scope = ? AND released_at IS NULL
          AND (expires_at IS NULL OR expires_at > ?)
          AND owner != ?`, lock.Scope, now, lock.Owner)
    if err != nil {
        return nil, fmt.Errorf("query conflicts: %w", err)
    }
    defer rows.Close()

    for rows.Next() {
        var existing struct {
            id, owner, pattern, reason string
            exclusive                  bool
        }
        if err := rows.Scan(&existing.id, &existing.owner, &existing.pattern, &existing.reason, &existing.exclusive); err != nil {
            return nil, err
        }
        // Skip shared+shared
        if !lock.Exclusive && !existing.exclusive {
            continue
        }
        overlap, err := PatternsOverlap(lock.Pattern, existing.pattern)
        if err != nil {
            return nil, fmt.Errorf("overlap check: %w", err)
        }
        if overlap {
            return &ReserveResult{Conflict: &ConflictInfo{
                BlockerID:      existing.id,
                BlockerOwner:   existing.owner,
                BlockerPattern: existing.pattern,
                BlockerReason:  existing.reason,
            }}, nil
        }
    }
    if err := rows.Err(); err != nil {
        return nil, err
    }

    // Insert the lock
    _, err = tx.ExecContext(ctx, `INSERT INTO coordination_locks
        (id, type, owner, scope, pattern, exclusive, reason, ttl_seconds, created_at, expires_at, dispatch_id, run_id)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)`,
        lock.ID, lock.Type, lock.Owner, lock.Scope, lock.Pattern, lock.Exclusive,
        lock.Reason, lock.TTLSeconds, lock.CreatedAt, lock.ExpiresAt, lock.DispatchID, lock.RunID)
    if err != nil {
        return nil, fmt.Errorf("insert: %w", err)
    }

    if err := tx.Commit(); err != nil {
        return nil, fmt.Errorf("commit: %w", err)
    }

    return &ReserveResult{Lock: &lock}, nil
}

// Release marks a lock as released. Releases by ID or by owner+scope.
func (s *Store) Release(ctx context.Context, id, owner, scope string) (int64, error) {
    now := time.Now().Unix()
    var res sql.Result
    var err error

    if id != "" {
        res, err = s.db.ExecContext(ctx,
            `UPDATE coordination_locks SET released_at = ? WHERE id = ? AND released_at IS NULL`, now, id)
    } else if owner != "" && scope != "" {
        res, err = s.db.ExecContext(ctx,
            `UPDATE coordination_locks SET released_at = ? WHERE owner = ? AND scope = ? AND released_at IS NULL`,
            now, owner, scope)
    } else {
        return 0, fmt.Errorf("release requires id or owner+scope")
    }
    if err != nil {
        return 0, err
    }
    return res.RowsAffected()
}

// Check returns conflicting active locks for a given pattern in a scope.
func (s *Store) Check(ctx context.Context, scope, pattern, excludeOwner string) ([]Lock, error) {
    // Validate glob complexity BEFORE any DB access to prevent DoS.
    if err := ValidateComplexity(pattern); err != nil {
        return nil, fmt.Errorf("invalid pattern: %w", err)
    }
    now := time.Now().Unix()
    query := `SELECT id, type, owner, scope, pattern, exclusive, reason, ttl_seconds,
        created_at, expires_at, released_at, dispatch_id, run_id
        FROM coordination_locks
        WHERE scope = ? AND released_at IS NULL AND (expires_at IS NULL OR expires_at > ?)`
    args := []any{scope, now}
    if excludeOwner != "" {
        query += " AND owner != ?"
        args = append(args, excludeOwner)
    }

    rows, err := s.db.QueryContext(ctx, query, args...)
    if err != nil {
        return nil, err
    }
    defer rows.Close()

    var conflicts []Lock
    for rows.Next() {
        var l Lock
        if err := scanLock(rows, &l); err != nil {
            return nil, err
        }
        overlap, err := PatternsOverlap(pattern, l.Pattern)
        if err != nil {
            return nil, err
        }
        if overlap {
            conflicts = append(conflicts, l)
        }
    }
    return conflicts, rows.Err()
}

// List returns locks matching the filter.
func (s *Store) List(ctx context.Context, f ListFilter) ([]Lock, error) {
    now := time.Now().Unix()
    query := "SELECT id, type, owner, scope, pattern, exclusive, reason, ttl_seconds, created_at, expires_at, released_at, dispatch_id, run_id FROM coordination_locks WHERE 1=1"
    var args []any

    if f.Scope != "" {
        query += " AND scope = ?"
        args = append(args, f.Scope)
    }
    if f.Owner != "" {
        query += " AND owner = ?"
        args = append(args, f.Owner)
    }
    if f.Type != "" {
        query += " AND type = ?"
        args = append(args, f.Type)
    }
    if f.Active {
        query += " AND released_at IS NULL AND (expires_at IS NULL OR expires_at > ?)"
        args = append(args, now)
    }
    query += " ORDER BY created_at DESC"

    rows, err := s.db.QueryContext(ctx, query, args...)
    if err != nil {
        return nil, err
    }
    defer rows.Close()

    var locks []Lock
    for rows.Next() {
        var l Lock
        if err := scanLock(rows, &l); err != nil {
            return nil, err
        }
        locks = append(locks, l)
    }
    return locks, rows.Err()
}

func scanLock(rows *sql.Rows, l *Lock) error {
    // Use sql.NullInt64 for nullable columns (expires_at, released_at) to avoid
    // scan errors on NULL values. Convert to *int64 after scan.
    var expiresAt, releasedAt sql.NullInt64
    err := rows.Scan(&l.ID, &l.Type, &l.Owner, &l.Scope, &l.Pattern, &l.Exclusive,
        &l.Reason, &l.TTLSeconds, &l.CreatedAt, &expiresAt, &releasedAt,
        &l.DispatchID, &l.RunID)
    if err != nil {
        return err
    }
    if expiresAt.Valid {
        l.ExpiresAt = &expiresAt.Int64
    }
    if releasedAt.Valid {
        l.ReleasedAt = &releasedAt.Int64
    }
    return nil
}
```

**Step 7: Write the failing tests for store**

Create `core/intercore/internal/coordination/store_test.go` — tests for Reserve (success, conflict, shared+shared allowed), Release (by ID, by owner+scope), Check (overlap, exclude-owner), List (filters). Use `tempDB` pattern from `db_test.go`.

**Step 8: Run tests to verify they fail**

Run: `cd core/intercore && go test -race ./internal/coordination/ -v`
Expected: FAIL (package doesn't exist yet or tests reference unwritten code)

**Step 9: Verify tests pass after writing store.go**

Run: `cd core/intercore && go test -race ./internal/coordination/ -v`
Expected: PASS

**Step 10: Commit**

```bash
git add core/intercore/internal/db/db.go core/intercore/internal/db/schema.sql
git add core/intercore/internal/coordination/
git commit -m "feat(intercore): add coordination_locks table and store (v20 migration)"
```

---

## Task 2: Glob Overlap Algorithm (F1)

**Bead:** iv-ehx2s (continued)
**Phase:** executing (as of 2026-02-25T23:36:06Z)
**Files:**
- Create: `core/intercore/internal/coordination/glob.go`
- Test: `core/intercore/internal/coordination/glob_test.go`

**Step 1: Write glob overlap tests**

Create `core/intercore/internal/coordination/glob_test.go` with test cases copied from Intermute's `core/intermute/internal/glob/overlap_test.go`. Key cases:
- `"*.go"` vs `"main.go"` → overlap
- `"src/*.go"` vs `"src/main.go"` → overlap
- `"src/*.go"` vs `"tests/*.go"` → no overlap (different prefix)
- `"*"` vs `"anything"` → overlap
- `"src/a.go"` vs `"src/b.go"` → no overlap (different literals)
- Shared+shared should be handled at Store level, not glob level

**Step 2: Run tests to verify they fail**

Run: `cd core/intercore && go test -race ./internal/coordination/ -run TestPatterns -v`
Expected: FAIL (PatternsOverlap not defined)

**Step 3: Copy and adapt PatternsOverlap from Intermute**

Create `core/intercore/internal/coordination/glob.go`. Copy the NFA-based algorithm from `core/intermute/internal/glob/overlap.go` (tokenizer, segment overlap, BFS state machine). Rename package to `coordination`. Do NOT import from Intermute — no L1↔L1 coupling.

Key functions to copy:
- `PatternsOverlap(a, b string) (bool, error)`
- `segmentPatternsOverlap(a, b string) (bool, error)`
- `tokenize(s string) ([]token, error)`
- `addClosure(states, tokens)` (epsilon expansion for `*`)
- `rangesOverlap(a, b []charRange) bool`
- `ValidateComplexity(pattern string) error` — **CRITICAL**: Must be called by `Reserve()` and `Check()` before any DB access to prevent NFA DoS via pathological glob patterns
- Complexity guards: `MaxTokens`, `MaxWildcards`

**Step 4: Run tests to verify they pass**

Run: `cd core/intercore && go test -race ./internal/coordination/ -run TestPatterns -v`
Expected: PASS

**Step 5: Commit**

```bash
git add core/intercore/internal/coordination/glob.go core/intercore/internal/coordination/glob_test.go
git commit -m "feat(intercore): add glob overlap algorithm for coordination conflict detection"
```

---

## Task 3: CLI Commands — `ic coordination` (F1)

**Bead:** iv-ehx2s (continued)
**Phase:** executing (as of 2026-02-25T23:36:06Z)
**Files:**
- Create: `core/intercore/cmd/ic/coordination.go`
- Modify: `core/intercore/cmd/ic/main.go` (add `coordination` case to switch)

**Step 1: Wire the subcommand in main.go**

Add `case "coordination":` to the switch in `main()`, calling `cmdCoordination(ctx, subArgs)`.

**Step 2: Write coordination.go with reserve/release/check/list/sweep**

Create `core/intercore/cmd/ic/coordination.go`. Follow the pattern from `cmd/ic/lock.go` for argument parsing (manual, no framework).

Subcommands:
- `ic coordination reserve --owner=<> --scope=<> --pattern=<> [--exclusive] [--ttl=<sec>] [--reason=<>] [--type=file_reservation] [--dispatch=<>] [--run=<>]`
- `ic coordination release <id>` or `ic coordination release --owner=<> --scope=<>`
- `ic coordination check --scope=<> --pattern=<> [--exclude-owner=<>]` — exit 0 = clear, exit 1 = conflict
- `ic coordination list [--scope=<>] [--owner=<>] [--type=<>] [--active]`
- `ic coordination sweep [--older-than=<duration>] [--dry-run]`

For `--json` output: use `json.NewEncoder(os.Stdout).Encode()` when `flagJSON` is true, otherwise human-readable table.

**Step 3: Write integration tests**

Add test cases to `core/intercore/test-integration.sh` (existing BATS-style integration test file):
- Reserve a file, check it exists in list
- Reserve conflicting pattern, verify exit 1
- Release by ID, verify gone from list
- Release by owner+scope, verify all released
- Check with exclude-owner
- Sweep expired locks

**Step 4: Build and test manually**

Run: `cd core/intercore && go build -o ic ./cmd/ic/ && ./ic coordination reserve --owner=test --scope=/tmp/test --pattern="*.go" --ttl=60 --reason="testing"`
Expected: JSON output with lock ID

Run: `cd core/intercore && ./ic coordination list --active`
Expected: Shows the lock just created

**Step 5: Run full test suite**

Run: `cd core/intercore && go test -race ./... && bash test-integration.sh`
Expected: All tests pass

**Step 6: Commit**

```bash
git add core/intercore/cmd/ic/coordination.go core/intercore/cmd/ic/main.go
git add core/intercore/test-integration.sh
git commit -m "feat(intercore): add ic coordination CLI commands (reserve, release, check, list, sweep)"
```

---

## Task 4: Event Bus Integration (F2)

**Bead:** iv-qaoly
**Phase:** executing (as of 2026-02-25T23:36:06Z)
**Files:**
- Modify: `core/intercore/internal/coordination/store.go` (add event callback)
- Modify: `core/intercore/internal/event/event.go` (add coordination source constant)
- Modify: `core/intercore/cmd/ic/coordination.go` (wire notifier)
- Test: `core/intercore/internal/coordination/store_test.go` (add event emission tests)

**Step 1: Add coordination_events table to schema.sql**

Add to `core/intercore/internal/db/schema.sql` (also added to v19→v20 migration in Task 1):

```sql
CREATE TABLE IF NOT EXISTS coordination_events (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    lock_id    TEXT NOT NULL,
    run_id     TEXT,                -- NULL for non-run-scoped locks
    event_type TEXT NOT NULL,       -- coordination.acquired | .released | .conflict | .expired | .transferred
    owner      TEXT NOT NULL,
    pattern    TEXT NOT NULL,
    scope      TEXT NOT NULL,
    reason     TEXT,
    created_at INTEGER NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_coord_events_run ON coordination_events(run_id)
    WHERE run_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_coord_events_scope ON coordination_events(scope);
```

**Step 2: Add coordination event source and storage**

In `core/intercore/internal/event/event.go`, add:

```go
const SourceCoordination = "coordination"

// AddCoordinationEvent inserts into coordination_events table.
func (s *Store) AddCoordinationEvent(ctx context.Context, eventType, lockID, owner, pattern, scope, reason, runID string) error {
    _, err := s.db.ExecContext(ctx, `INSERT INTO coordination_events
        (lock_id, run_id, event_type, owner, pattern, scope, reason, created_at)
        VALUES (?, NULLIF(?,''), ?, ?, ?, ?, ?, ?)`,
        lockID, runID, eventType, owner, pattern, scope, reason, time.Now().Unix())
    return err
}
```

**Step 3: Add coordination_events to ListEvents UNION**

In `core/intercore/internal/event/event.go`, modify `ListEvents()` to include a 5th UNION member for coordination events. The existing UNION normalizes columns across tables (phase_events, dispatch_events, interspect_events, discovery_events). Add:

```sql
UNION ALL
SELECT id + ? AS id, COALESCE(run_id, '') AS run_id, 'coordination' AS source,
    event_type, owner || ':' || pattern AS detail, reason, created_at
FROM coordination_events WHERE id > ?
```

Add `sinceCoordID` cursor parameter alongside the existing per-table cursors. The offset added to `id` must not collide with other table ID spaces — use a new offset constant (e.g., `coordOffset = 4_000_000_000`).

For `--all` mode (no run filter): include all coordination events.
For run-scoped mode: `WHERE run_id = ?` filters naturally (locks created with `--run=<id>` are visible).

**Step 4: Add SetEventFunc method to Store (backward-compatible)**

Modify `coordination/store.go` — use `SetEventFunc` instead of changing `NewStore` signature (so Task 1 callers aren't broken):

```go
// EventFunc is called after coordination state changes. It MUST NOT block.
// Matches the signature needed for AddCoordinationEvent.
type EventFunc func(ctx context.Context, eventType, lockID, owner, pattern, scope, reason, runID string) error

type Store struct {
    db      *sql.DB
    onEvent EventFunc  // nil = no event emission
}

func NewStore(db *sql.DB) *Store {
    return &Store{db: db}
}

// SetEventFunc sets the event callback. Call after NewStore, before Reserve/Release.
func (s *Store) SetEventFunc(fn EventFunc) {
    s.onEvent = fn
}
```

Call `s.onEvent(ctx, "coordination.acquired", lock.ID, lock.Owner, lock.Pattern, lock.Scope, lock.Reason, lock.RunID)` after successful Reserve commit. Call `s.onEvent(...)` with `"coordination.released"` after Release, `"coordination.conflict"` when blocked, `"coordination.expired"` when sweep cleans, `"coordination.transferred"` on transfer.

**Step 5: Wire in coordination.go**

In `cmd/ic/coordination.go`, create the event callback that calls `evStore.AddCoordinationEvent(...)`:

```go
coordStore.SetEventFunc(func(ctx context.Context, eventType, lockID, owner, pattern, scope, reason, runID string) error {
    if err := evStore.AddCoordinationEvent(ctx, eventType, lockID, owner, pattern, scope, reason, runID); err != nil {
        return err
    }
    return notifier.Notify(ctx, event.Event{
        Source:    event.SourceCoordination,
        Type:     eventType,
        RunID:    runID,
    })
})
```

**Step 6: Write tests for event emission**

Add tests in `store_test.go` that use a mock `EventFunc` to verify:
- Reserve success → `coordination.acquired` emitted with correct lock metadata
- Reserve conflict → `coordination.conflict` emitted with blocker info
- Release → `coordination.released` emitted
- Sweep → `coordination.expired` emitted per cleaned lock (not suppressed by inline sweep)

**Step 7: Run tests**

Run: `cd core/intercore && go test -race ./internal/coordination/ -v`
Expected: PASS

**Step 8: Verify events visible via `ic events tail`**

Build and test: create a run, reserve with `--run=<run_id>`, then `ic events tail <run_id>`. Verify coordination events appear in the unified event stream.

Also test `ic events tail --all` to verify coordination events appear even without a run_id.

**Step 9: Commit**

```bash
git add core/intercore/internal/db/schema.sql
git add core/intercore/internal/coordination/store.go
git add core/intercore/internal/event/event.go
git add core/intercore/cmd/ic/coordination.go
git add core/intercore/internal/coordination/store_test.go
git commit -m "feat(intercore): emit coordination events through event bus (new coordination_events table)"
```

---

## Task 5: Crash Recovery Sweeper (F3)

**Bead:** iv-sg04f
**Phase:** executing (as of 2026-02-25T23:36:06Z)
**Files:**
- Create: `core/intercore/internal/coordination/sweep.go`
- Test: `core/intercore/internal/coordination/sweep_test.go`

**Step 1: Write the sweep function**

Create `core/intercore/internal/coordination/sweep.go`:

```go
package coordination

import (
    "context"
    "os"
    "syscall"
    "time"
    "strconv"
    "strings"
)

type SweepResult struct {
    Expired  int `json:"expired"`   // TTL expired
    Total    int `json:"total"`
}

// Sweep cleans expired locks by TTL only.
// PID-based liveness was removed due to PID reuse attack risk — all lock types
// MUST have non-null TTLs. Named locks use longer TTLs (e.g., 300s) with renewal.
// The olderThan parameter adds a grace period: only expire locks whose expires_at
// is older than (now - olderThan). Pass 0 for no grace period.
func (s *Store) Sweep(ctx context.Context, olderThan time.Duration, dryRun bool) (*SweepResult, error) {
    now := time.Now().Unix()
    cutoff := now
    if olderThan > 0 {
        cutoff = now - int64(olderThan.Seconds())
    }
    result := &SweepResult{}

    // Find TTL-expired locks
    rows, err := s.db.QueryContext(ctx, `SELECT id, type, owner, scope, pattern, exclusive,
        reason, ttl_seconds, created_at, expires_at, released_at, dispatch_id, run_id
        FROM coordination_locks
        WHERE released_at IS NULL AND expires_at IS NOT NULL AND expires_at < ?`, cutoff)
    if err != nil {
        return nil, err
    }
    defer rows.Close()

    var expired []Lock
    for rows.Next() {
        var l Lock
        if err := scanLock(rows, &l); err != nil {
            return nil, err
        }
        expired = append(expired, l)
    }
    if err := rows.Err(); err != nil {
        return nil, err
    }

    result.Expired = len(expired)
    result.Total = result.Expired

    if dryRun || result.Total == 0 {
        return result, nil
    }

    // Release all expired locks
    for _, l := range expired {
        if _, err := s.Release(ctx, l.ID, "", ""); err != nil {
            continue // best-effort
        }
        if s.onEvent != nil {
            s.onEvent(ctx, "coordination.expired", l.ID, l.Owner, l.Pattern, l.Scope, "sweep", l.RunID)
        }
    }
    return result, nil
}
```

**Step 2: Write sweep tests**

Create `core/intercore/internal/coordination/sweep_test.go`:
- Test expired lock cleanup (create lock with TTL=1, sleep 2s, sweep)
- Test stale PID cleanup (create named_lock with owner "99999:test", verify swept)
- Test dry-run mode (verify no changes made)
- Test sweep emits events

**Step 3: Run tests**

Run: `cd core/intercore && go test -race ./internal/coordination/ -run TestSweep -v`
Expected: PASS

**Step 4: Wire sweep into `ic coordination sweep` CLI**

Already wired in Task 3 — verify `ic coordination sweep --dry-run` and `ic coordination sweep --older-than=5m` work.

**Step 5: Commit**

```bash
git add core/intercore/internal/coordination/sweep.go core/intercore/internal/coordination/sweep_test.go
git commit -m "feat(intercore): add crash recovery sweeper for coordination locks"
```

---

## Task 6: Reservation Transfer (F4)

**Bead:** iv-nu9kx
**Phase:** executing (as of 2026-02-25T23:36:06Z)
**Files:**
- Modify: `core/intercore/internal/coordination/store.go` (add Transfer method)
- Modify: `core/intercore/cmd/ic/coordination.go` (add transfer subcommand)
- Test: `core/intercore/internal/coordination/store_test.go` (add transfer tests)

**Step 1: Write the Transfer method**

Add to `coordination/store.go`:

```go
// Transfer atomically reassigns all active locks from one owner to another.
func (s *Store) Transfer(ctx context.Context, fromOwner, toOwner, scope string, force bool) (int64, error) {
    // BEGIN IMMEDIATE via LevelSerializable — same pattern as Reserve().
    tx, err := s.db.BeginTx(ctx, &sql.TxOptions{Isolation: sql.LevelSerializable})
    if err != nil {
        return 0, fmt.Errorf("begin immediate: %w", err)
    }
    defer tx.Rollback()

    now := time.Now().Unix()

    if !force {
        // Check for conflicts: would the transferred locks conflict with toOwner's existing locks?
        // Get fromOwner's active exclusive locks
        fromRows, err := tx.QueryContext(ctx, `SELECT pattern FROM coordination_locks
            WHERE owner = ? AND scope = ? AND released_at IS NULL
            AND (expires_at IS NULL OR expires_at > ?) AND exclusive = 1`, fromOwner, scope, now)
        if err != nil {
            return 0, err
        }
        var fromPatterns []string
        for fromRows.Next() {
            var p string
            if err := fromRows.Scan(&p); err != nil {
                fromRows.Close()
                return 0, fmt.Errorf("scan from-patterns: %w", err)
            }
            fromPatterns = append(fromPatterns, p)
        }
        fromRows.Close()
        if err := fromRows.Err(); err != nil {
            return 0, fmt.Errorf("read from-patterns: %w", err)
        }

        // Get toOwner's active exclusive locks
        toRows, err := tx.QueryContext(ctx, `SELECT pattern FROM coordination_locks
            WHERE owner = ? AND scope = ? AND released_at IS NULL
            AND (expires_at IS NULL OR expires_at > ?) AND exclusive = 1`, toOwner, scope, now)
        if err != nil {
            return 0, err
        }
        for toRows.Next() {
            var toPattern string
            if err := toRows.Scan(&toPattern); err != nil {
                toRows.Close()
                return 0, fmt.Errorf("scan to-patterns: %w", err)
            }
            for _, fp := range fromPatterns {
                overlap, err := PatternsOverlap(fp, toPattern)
                if err != nil {
                    toRows.Close()
                    return 0, fmt.Errorf("overlap check in transfer: %w", err)
                }
                if overlap {
                    toRows.Close()
                    return 0, fmt.Errorf("transfer conflict: %s overlaps with existing lock %s", fp, toPattern)
                }
            }
        }
        toRows.Close()
        if err := toRows.Err(); err != nil {
            return 0, fmt.Errorf("read to-patterns: %w", err)
        }
    }

    // Perform the transfer
    res, err := tx.ExecContext(ctx, `UPDATE coordination_locks SET owner = ?
        WHERE owner = ? AND scope = ? AND released_at IS NULL
        AND (expires_at IS NULL OR expires_at > ?)`, toOwner, fromOwner, scope, now)
    if err != nil {
        return 0, err
    }

    n, _ := res.RowsAffected()
    if err := tx.Commit(); err != nil {
        return 0, err
    }

    return n, nil
}
```

**Step 2: Wire CLI subcommand**

Add `transfer` case in `coordination.go`:
`ic coordination transfer --from=<agent> --to=<agent> --scope=<project> [--force]`

**Step 3: Write tests**

- Transfer 3 locks from agent A to agent B, verify owner changed
- Transfer with conflict (B has exclusive lock overlapping A's), verify error without `--force`
- Transfer with `--force`, verify success despite conflict
- Transfer emits `coordination.transferred` events

**Step 4: Run tests**

Run: `cd core/intercore && go test -race ./internal/coordination/ -run TestTransfer -v`
Expected: PASS

**Step 5: Commit**

```bash
git add core/intercore/internal/coordination/store.go core/intercore/cmd/ic/coordination.go
git add core/intercore/internal/coordination/store_test.go
git commit -m "feat(intercore): add ic coordination transfer for session handoff"
```

---

## Task 7: Intermute Dual-Write Bridge (F5)

**Bead:** iv-7g4ao
**Phase:** executing (as of 2026-02-25T23:36:06Z)
**Files:**
- Modify: `core/intermute/cmd/intermute/main.go` (add `--coordination-dual-write` flag + `--intercore-db` flag)
- Create: `core/intermute/internal/storage/sqlite/coordination_bridge.go`
- Test: `core/intermute/internal/storage/sqlite/coordination_bridge_test.go`
- Modify: `core/intermute/internal/storage/sqlite/sqlite.go` (wrap Reserve/Release to dual-write)

**Step 1: Add CLI flags for dual-write**

In `core/intermute/cmd/intermute/main.go`, add:
- `--coordination-dual-write` (bool, default false)
- `--intercore-db` (string, default empty — auto-discover via walk-up)

**Step 2: Write the coordination bridge**

Create `core/intermute/internal/storage/sqlite/coordination_bridge.go`:

```go
package sqlite

import (
    "database/sql"
    "fmt"
    "os"
    "path/filepath"
    "time"
)

type CoordinationBridge struct {
    db      *sql.DB
    enabled bool
}

// NewCoordinationBridge opens the Intercore DB for dual-write.
func NewCoordinationBridge(dbPath string) (*CoordinationBridge, error) {
    if dbPath == "" {
        return &CoordinationBridge{enabled: false}, nil
    }
    // Use MaxOpenConns(1) — critical for shared DB safety
    db, err := sql.Open("sqlite", "file:"+dbPath+"?_pragma=journal_mode%3DWAL&_pragma=busy_timeout%3D5000")
    if err != nil {
        return nil, err
    }
    db.SetMaxOpenConns(1)
    db.Exec("PRAGMA busy_timeout = 5000")
    db.Exec("PRAGMA journal_mode = WAL")
    return &CoordinationBridge{db: db, enabled: true}, nil
}

// normalizeScope converts Intermute's short project name (e.g., "Demarch") to
// the canonical absolute path (e.g., "/home/mk/projects/Demarch") that Intercore uses.
// Uses git rev-parse --show-toplevel if available, otherwise resolves via walk-up.
// This is CRITICAL for cross-system conflict detection — mismatched scopes = false negatives.
func normalizeScope(project string) string {
    // If already absolute, return as-is
    if filepath.IsAbs(project) {
        return filepath.Clean(project)
    }
    // Try git rev-parse from CWD
    out, err := exec.Command("git", "rev-parse", "--show-toplevel").Output()
    if err == nil {
        return strings.TrimSpace(string(out))
    }
    // Fallback: resolve relative to CWD
    abs, err := filepath.Abs(project)
    if err != nil {
        return project
    }
    return abs
}

// MirrorReserve writes a reservation to coordination_locks.
// NOTE: project is normalized to absolute path via normalizeScope() to match Intercore's scope format.
func (b *CoordinationBridge) MirrorReserve(id, agentID, project, pattern string, exclusive bool, reason string, ttlSeconds int, createdAt int64, expiresAt *int64) error {
    if !b.enabled {
        return nil
    }
    project = normalizeScope(project)
    _, err := b.db.Exec(`INSERT OR IGNORE INTO coordination_locks
        (id, type, owner, scope, pattern, exclusive, reason, ttl_seconds, created_at, expires_at)
        VALUES (?, 'file_reservation', ?, ?, ?, ?, ?, ?, ?, ?)`,
        id, agentID, project, pattern, exclusive, reason, ttlSeconds, createdAt, expiresAt)
    return err
}

// MirrorRelease marks a lock as released in coordination_locks.
func (b *CoordinationBridge) MirrorRelease(id string) error {
    if !b.enabled {
        return nil
    }
    _, err := b.db.Exec(`UPDATE coordination_locks SET released_at = ? WHERE id = ? AND released_at IS NULL`,
        time.Now().Unix(), id)
    return err
}

func (b *CoordinationBridge) Close() error {
    if b.db != nil {
        return b.db.Close()
    }
    return nil
}

// DiscoverIntercoreDB walks up from projectDir looking for .clavain/intercore.db.
func DiscoverIntercoreDB(projectDir string) string {
    dir := projectDir
    for {
        candidate := filepath.Join(dir, ".clavain", "intercore.db")
        if _, err := os.Stat(candidate); err == nil {
            return candidate
        }
        parent := filepath.Dir(dir)
        if parent == dir {
            return ""
        }
        dir = parent
    }
}
```

**Step 3: Wire bridge into Store's Reserve and Release**

In `sqlite.go`, add `bridge *CoordinationBridge` field to `Store`. After successful `Reserve()` commit, call `s.bridge.MirrorReserve(...)`. After successful `ReleaseReservation()`, call `s.bridge.MirrorRelease(...)`. Errors from bridge are logged but don't fail the primary operation.

**IMPORTANT — Dual-write inconsistency window:** Between Intermute's commit to `file_reservations` and the `MirrorReserve` call, `ic coordination check` sees false negatives. During the dual-write phase, `ic coordination check` MUST query **both** `coordination_locks` AND `file_reservations` (via Intermute HTTP fallback) until Task 9 cleanup removes the legacy table. Document this in Task 3's `check` subcommand: add `--dual-write` flag that also queries Intermute HTTP as a secondary source.

**Step 4: Write tests**

Test that dual-write creates matching rows in both tables. Test that bridge errors don't fail the primary reservation. Test that disabled bridge is a no-op.

**Step 5: Run tests**

Run: `cd core/intermute && go test -race ./internal/storage/sqlite/ -v`
Expected: PASS

**Step 6: Commit**

```bash
git add core/intermute/internal/storage/sqlite/coordination_bridge.go
git add core/intermute/internal/storage/sqlite/coordination_bridge_test.go
git add core/intermute/internal/storage/sqlite/sqlite.go
git add core/intermute/cmd/intermute/main.go
git commit -m "feat(intermute): add coordination dual-write bridge to intercore.db"
```

---

## Task 8: Interlock MCP Bridge to `ic` (F6)

**Bead:** iv-r5vlt
**Phase:** executing (as of 2026-02-25T23:36:06Z)
**Files:**
- Create: `interverse/interlock/internal/icclient/icclient.go` (wrapper for `ic coordination` CLI)
- Modify: `interverse/interlock/internal/tools/tools.go` (swap HTTP calls for `ic` calls)
- Modify: `interverse/interlock/hooks/pre-edit.sh` (call `ic` instead of interlock-check.sh)
- Modify: `interverse/interlock/scripts/interlock-check.sh` (rewrite to use `ic coordination check`)
- Test: `interverse/interlock/internal/icclient/icclient_test.go`

**Step 1: Write the ic CLI wrapper**

Create `interverse/interlock/internal/icclient/icclient.go`:

```go
package icclient

import (
    "context"
    "encoding/json"
    "fmt"
    "os/exec"
)

type Client struct {
    binary string // path to ic binary, empty = auto-discover
}

func New() *Client {
    path, _ := exec.LookPath("ic")
    return &Client{binary: path}
}

func (c *Client) Available() bool {
    return c.binary != ""
}

// Reserve calls ic coordination reserve.
func (c *Client) Reserve(ctx context.Context, owner, scope, pattern, reason string, ttlSec int, exclusive bool) (json.RawMessage, error) {
    args := []string{"--json", "coordination", "reserve",
        "--owner=" + owner, "--scope=" + scope, "--pattern=" + pattern,
        fmt.Sprintf("--ttl=%d", ttlSec)}
    if reason != "" {
        args = append(args, "--reason="+reason)
    }
    if !exclusive {
        args = append(args, "--exclusive=false")
    }
    return c.run(ctx, args...)
}

// Release calls ic coordination release.
func (c *Client) Release(ctx context.Context, id string) (json.RawMessage, error) {
    return c.run(ctx, "--json", "coordination", "release", id)
}

// ReleaseAll calls ic coordination release --owner --scope.
func (c *Client) ReleaseAll(ctx context.Context, owner, scope string) (json.RawMessage, error) {
    return c.run(ctx, "--json", "coordination", "release", "--owner="+owner, "--scope="+scope)
}

// Check calls ic coordination check. Returns exit 0 = clear, exit 1 = conflict.
func (c *Client) Check(ctx context.Context, scope, pattern, excludeOwner string) ([]byte, bool, error) {
    args := []string{"--json", "coordination", "check", "--scope=" + scope, "--pattern=" + pattern}
    if excludeOwner != "" {
        args = append(args, "--exclude-owner="+excludeOwner)
    }
    out, err := c.run(ctx, args...)
    if err != nil {
        if exitErr, ok := err.(*exec.ExitError); ok && exitErr.ExitCode() == 1 {
            return out, true, nil // conflict
        }
        return nil, false, err
    }
    return out, false, nil
}

// List calls ic coordination list.
func (c *Client) List(ctx context.Context, owner, scope string) (json.RawMessage, error) {
    args := []string{"--json", "coordination", "list", "--active"}
    if owner != "" {
        args = append(args, "--owner="+owner)
    }
    if scope != "" {
        args = append(args, "--scope="+scope)
    }
    return c.run(ctx, args...)
}

func (c *Client) run(ctx context.Context, args ...string) (json.RawMessage, error) {
    cmd := exec.CommandContext(ctx, c.binary, args...)
    out, err := cmd.Output()
    if err != nil {
        return out, err
    }
    return out, nil
}
```

**Step 2: Modify tools.go to use ic client with HTTP fallback**

In `internal/tools/tools.go`, modify `RegisterAll` to accept both an `*icclient.Client` and the existing `*client.Client` (HTTP). Each tool handler:
1. If `icClient.Available()`, use `icClient.Reserve(...)` etc.
2. Else fall back to existing HTTP `client.CreateReservation(...)` (fail-open)

**Step 3: Rewrite pre-edit.sh to use `ic`**

Replace the `interlock-check.sh` call with:
```bash
if command -v ic &>/dev/null; then
    # Single atomic reserve call eliminates TOCTOU (check-then-reserve race).
    # Reserve returns conflict info on exit 1, or creates the lock on exit 0.
    result=$(ic --json coordination reserve \
        --owner="$INTERMUTE_AGENT_ID" \
        --scope="$PROJECT_DIR" \
        --pattern="$FILE_PATH" \
        --ttl=900 \
        --reason="auto-reserve: editing" 2>/dev/null)
    rc=$?
    if [[ $rc -eq 1 ]]; then
        # conflict found — Reserve returned conflict info
        # SAFETY: use jq --arg to prevent shell injection from FILE_PATH and blocker values
        blocker=$(echo "$result" | jq -r '.conflict.blocker_owner // "unknown"')
        jq -nc --arg fp "$FILE_PATH" --arg bl "$blocker" \
            '{"decision":"block","reason":"INTERLOCK: \($fp) reserved by \($bl)"}'
        exit 0
    fi
    # exit 0 = lock acquired, proceed
else
    # Fallback to HTTP check
    source "$(dirname "$0")/lib.sh"
    # ... existing interlock-check.sh logic
fi
```

**Step 4: Write icclient tests**

Test with a real `ic` binary (build it first in test setup). Test Reserve, Release, Check, List operations.

**Step 5: Run tests**

Run: `cd interverse/interlock && go test -race ./internal/icclient/ -v`
Expected: PASS

**Step 6: Commit**

```bash
git add interverse/interlock/internal/icclient/
git add interverse/interlock/internal/tools/tools.go
git add interverse/interlock/hooks/pre-edit.sh
git add interverse/interlock/scripts/interlock-check.sh
git commit -m "feat(interlock): bridge MCP tools and hooks to ic coordination"
```

---

## Task 9: Cleanup Legacy Reservation Storage (F7) — DEFERRED

**Bead:** iv-gibz3
**Status:** Deferred to separate sprint. The dual-write bridge (Task 7) and ic bridge (Task 8) must be validated in production before removing legacy storage.
**Phase:** executing (as of 2026-02-25T23:36:06Z)
**Files:**
- Modify: `core/intermute/internal/storage/sqlite/sqlite.go` (remove Reserve/Release/CheckConflict, proxy to coordination_locks)
- Modify: `core/intermute/internal/storage/sqlite/coordination_bridge.go` (remove dual-write, make bridge the primary)
- Modify: `core/intermute/internal/http/handlers_reservations.go` (read from coordination_locks)
- Modify: `core/intercore/cmd/ic/lock.go` (reimplement on coordination_locks)
- Modify: `os/clavain/hooks/lib-intercore.sh` (`intercore_lock` → `ic coordination reserve`)

**Step 1: Proxy Intermute reservation endpoints to coordination_locks**

In `handlers_reservations.go`, change `listReservations` and `checkConflicts` to query `coordination_locks` table via the bridge DB connection instead of `file_reservations`.

**Step 2: Remove Intermute's own reservation methods**

Delete `Reserve()`, `ReleaseReservation()`, `CheckConflicts()`, `ActiveReservations()`, `AgentReservations()` from `sqlite.go`. Replace with thin proxies that read/write `coordination_locks` via bridge.

**Step 3: Remove dual-write flag and code**

Remove `--coordination-dual-write` flag, `MirrorReserve()`, `MirrorRelease()`. The bridge becomes the only reservation path.

**Step 4: Reimplement `ic lock` on coordination_locks**

In `cmd/ic/lock.go`:
- `ic lock acquire <name> <scope>` → `ic coordination reserve --type=named_lock --pattern=<name> --scope=<scope> --owner=<PID:hostname>`
- `ic lock release <name> <scope>` → `ic coordination release --owner=<PID:hostname> --scope=<scope>` (filtered by pattern match)
- `ic lock list` → `ic coordination list --type=named_lock`
- `ic lock stale` → `ic coordination sweep --dry-run`
- `ic lock clean` → `ic coordination sweep`

Keep the existing CLI interface unchanged — backward compatibility.

**Step 5: Update lib-intercore.sh**

Change `intercore_lock()` to use `ic coordination reserve --type=named_lock` instead of `ic lock acquire`. Change `intercore_unlock()` to use `ic coordination release`. Change `intercore_lock_clean()` to use `ic coordination sweep`.

**Step 6: Run full test suite**

Run: `cd core/intercore && go test -race ./... && bash test-integration.sh`
Run: `cd core/intermute && go test -race ./...`
Run: `cd interverse/interlock && go test -race ./...`
Expected: All pass

**Step 7: Remove filesystem lock directory**

Remove `/tmp/intercore/locks/` creation from `lock.Manager`. The `internal/lock/` package can be kept for backward compat but its `Manager` is now unused.

**Step 8: Commit**

```bash
git add core/intermute/internal/storage/sqlite/ core/intermute/internal/http/
git add core/intercore/cmd/ic/lock.go
git add os/clavain/hooks/lib-intercore.sh
git commit -m "feat: complete coordination migration — remove legacy reservation storage"
```

---

## Dependency Order

```
Task 1 (schema) → Task 2 (glob) → Task 3 (CLI) → Task 4 (events)
                                                 → Task 5 (sweep)
                                                 → Task 6 (transfer)
Task 3 + 4 + 5 + 6 → Task 7 (Intermute dual-write)
Task 7 → Task 8 (Interlock bridge)
Task 8 → Task 9 (cleanup)
```

Tasks 4, 5, and 6 can be parallelized after Task 3.
Tasks 7-9 are sequential (migration phases).

---

## Review Fixes Applied (flux-drive, 2026-02-25)

All 6 P0 and key P1 findings from the 4-agent flux-drive review have been incorporated:

### P0 Fixes
1. **ROLLBACK; BEGIN IMMEDIATE → `sql.LevelSerializable`** (Tasks 1, 6): Fixed `Reserve()` and `Transfer()` to use `sql.TxOptions{Isolation: sql.LevelSerializable}` instead of raw `ROLLBACK; BEGIN IMMEDIATE` which corrupts `database/sql` state.
2. **Shell injection in pre-edit.sh** (Task 8): Replaced string interpolation with `jq -nc --arg` for all dynamic values in JSON output.
3. **PID reuse attack → TTL-only sweep** (Task 5): Removed `findStalePIDs`, `parsePID`, `pidAlive` entirely. All lock types use TTL-based expiry with `olderThan` grace period. Named locks use longer TTLs with renewal.
4. **Glob DoS — ValidateComplexity enforcement** (Tasks 1, 2): Added `ValidateComplexity(pattern)` call at entry of both `Reserve()` and `Check()` before any DB access.
5. **isTableExistsError undefined** (Task 1): Removed undefined helper reference. `CREATE TABLE IF NOT EXISTS` handles idempotency. Fixed migration lower bound from `>= 3` to `>= 19`.
6. **Event bus schema mismatch** (Task 4): Added `coordination_events` table definition to migration and schema.sql. Added UNION member to `ListEvents()`. Specified `AddCoordinationEvent()` method and cursor integration.

### P1 Fixes
- **UUID → base36 IDs** (Task 1): Changed `uuid.NewString()` to `generateID()` matching Intercore convention.
- **scanLock nullable handling** (Task 1): Changed `*int64` to `sql.NullInt64` scan pattern for `expires_at` and `released_at`.
- **Transfer() Scan error handling** (Task 6): Added `Scan()` error checks and `rows.Err()` after both loops.
- **Scope normalization** (Task 7): Added `normalizeScope()` to convert Intermute short names to absolute paths.
- **SetEventFunc backward compat** (Task 4): Changed from `NewStore(db, onEvent)` to `NewStore(db)` + `SetEventFunc()` method.
- **pre-edit.sh TOCTOU** (Task 8): Replaced check-then-reserve with single atomic `ic coordination reserve` call.
- **Dual-write inconsistency window** (Task 7): Documented that `ic coordination check` must query both tables during dual-write phase.
- **Inline sweep events** (Task 1): Documented that inline sweep does NOT emit events (performance tradeoff); external `ic coordination sweep` does.
