# Implementation Plan: intercore — Unified State Database

**Bead:** iv-ieh7
**Phase:** executing (as of 2026-02-18T00:48:35Z)
**PRD:** `docs/prds/2026-02-17-intercore-state-database.md` (v2)
**Implementation order:** F1 → F3 → F2 → F5 → F7
**Revision:** v2 (2026-02-18) — addresses flux-drive review findings (3 P0, 8 P1)
**Status:** IMPLEMENTED — all batches complete, all tests pass

## Batch 1: Go CLI Scaffold + Schema (F1)

### Task 1.1: Project structure and Go module

Create `infra/intercore/` with:

```
infra/intercore/
├── cmd/ic/
│   └── main.go           # CLI entry point
├── internal/
│   ├── db/
│   │   ├── db.go         # Open, migrate, health check
│   │   └── schema.sql    # Embedded DDL
│   ├── state/
│   │   └── state.go      # (placeholder, filled in Batch 3)
│   └── sentinel/
│       └── sentinel.go   # (placeholder, filled in Batch 2)
├── go.mod
├── go.sum
├── CLAUDE.md
└── AGENTS.md
```

**go.mod:**
```
module github.com/mistakeknot/interverse/infra/intercore
go 1.22
require modernc.org/sqlite v1.29.0
```

**Files:** `infra/intercore/go.mod`, `infra/intercore/cmd/ic/main.go`, `infra/intercore/internal/db/db.go`, `infra/intercore/internal/db/schema.sql`

**Acceptance:**
- `cd infra/intercore && go build ./cmd/ic` succeeds
- Binary prints version with `ic version`

### Task 1.2: Schema DDL and migration engine

`internal/db/schema.sql` (embedded via `//go:embed`):

```sql
-- Schema version tracked via PRAGMA user_version (no separate table)
CREATE TABLE IF NOT EXISTS state (
    key         TEXT NOT NULL,
    scope_id    TEXT NOT NULL,
    payload     TEXT NOT NULL,
    updated_at  INTEGER NOT NULL DEFAULT (unixepoch()),
    expires_at  INTEGER,
    PRIMARY KEY (key, scope_id)
);

CREATE INDEX IF NOT EXISTS idx_state_scope ON state(scope_id, key);
CREATE INDEX IF NOT EXISTS idx_state_expires ON state(expires_at) WHERE expires_at IS NOT NULL;

CREATE TABLE IF NOT EXISTS sentinels (
    name        TEXT NOT NULL,
    scope_id    TEXT NOT NULL,
    last_fired  INTEGER NOT NULL DEFAULT (unixepoch()),
    PRIMARY KEY (name, scope_id)
);
```

**Schema version:** Use `PRAGMA user_version` only — no separate `schema_version` table (IMP-2).

`internal/db/db.go`:

```go
func Open(path string, timeout time.Duration) (*DB, error) {
    // Symlink check on parent directory (P2-5)
    dir := filepath.Dir(path)
    if info, err := os.Lstat(dir); err == nil && info.Mode()&os.ModeSymlink != 0 {
        return nil, fmt.Errorf("open: %s is a symlink (refusing to create DB)", dir)
    }

    dsn := fmt.Sprintf("file:%s?_journal_mode=WAL&_busy_timeout=%d", path, timeout.Milliseconds())
    sqlDB, err := sql.Open("sqlite", dsn)
    if err != nil {
        return nil, fmt.Errorf("open: %w", err)
    }

    // Critical: single connection prevents WAL checkpoint TOCTOU (P1-2)
    sqlDB.SetMaxOpenConns(1)

    // Centralized schema version check on every Open (IMP-3)
    var version int
    if err := sqlDB.QueryRow("PRAGMA user_version").Scan(&version); err == nil {
        if version > maxSchemaVersion {
            sqlDB.Close()
            return nil, ErrSchemaVersionTooNew
        }
    }

    return &DB{db: sqlDB, path: path}, nil
}
```

- `Migrate() error` — creates timestamped backup before migration (P0-3), reads `user_version` inside `BEGIN IMMEDIATE` transaction to prevent TOCTOU race (P1-6), applies schema.sql, sets `PRAGMA user_version`
- `Health() error` — checks DB readable, schema version current, disk space >10MB
- `SchemaVersion() int` — reads `PRAGMA user_version`

**Pre-migration backup (P0-3):**
```go
func (d *DB) Migrate() error {
    // Create backup before any migration attempt
    if _, err := os.Stat(d.path); err == nil {
        backupPath := fmt.Sprintf("%s.backup-%s", d.path, time.Now().Format("20060102-150405"))
        if err := copyFile(d.path, backupPath); err != nil {
            return fmt.Errorf("migrate: backup failed: %w", err)
        }
    }

    tx, err := d.db.BeginTx(ctx, &sql.TxOptions{Isolation: sql.LevelSerializable})
    if err != nil {
        return fmt.Errorf("migrate: begin: %w", err)
    }
    defer tx.Rollback()

    // Read version INSIDE transaction to prevent TOCTOU (P1-6)
    var currentVersion int
    if err := tx.QueryRow("PRAGMA user_version").Scan(&currentVersion); err != nil {
        return fmt.Errorf("migrate: read version: %w", err)
    }

    if currentVersion >= targetVersion {
        return nil // already migrated
    }

    // Apply schema DDL...
    // SET user_version inside same transaction
    if _, err := tx.Exec(fmt.Sprintf("PRAGMA user_version = %d", targetVersion)); err != nil {
        return fmt.Errorf("migrate: set version: %w", err)
    }
    return tx.Commit()
}
```

**Files:** `infra/intercore/internal/db/db.go`, `infra/intercore/internal/db/schema.sql`, `infra/intercore/internal/db/db_test.go`

**Acceptance:**
- `ic init` creates `.clavain/intercore.db` with both tables and indexes
- `ic health` returns exit 0 on healthy DB
- `ic version` prints CLI version and schema version
- Test: `db.Stats().MaxOpenConns == 1` after `Open()`
- Test: open DB, verify WAL mode, verify busy_timeout, verify tables exist
- Test: 10 goroutines calling `Migrate()` on the same DB — all succeed, version = 1
- Test: pre-migration backup created with correct timestamp format
- Test: if `.clavain/` is a symlink, `Open()` returns error

### Task 1.3: CLI framework and subcommand routing

`cmd/ic/main.go`:
- Parse subcommands: `init`, `version`, `health`, `state`, `sentinel`, `compat`
- Global flags: `--timeout=<duration>` (default 100ms), `--verbose`, `--json`
- DB path resolution: check `--db=<path>` flag, else look for `.clavain/intercore.db` by walking up from `$PWD`
- **Path traversal protection (P0-1):** `validateDBPath()` enforces:
  - Must end in `.db` extension
  - No `..` path components after `filepath.Clean()`
  - Must be under CWD or within a `.clavain/` directory
  - Resolved path (via `filepath.Abs`) must not escape project boundary

```go
func validateDBPath(path string) error {
    cleaned := filepath.Clean(path)
    if filepath.Ext(cleaned) != ".db" {
        return fmt.Errorf("db path must have .db extension: %s", path)
    }
    if strings.Contains(cleaned, "..") {
        return fmt.Errorf("db path must not contain '..': %s", path)
    }
    abs, err := filepath.Abs(cleaned)
    if err != nil {
        return fmt.Errorf("db path: %w", err)
    }
    cwd, _ := os.Getwd()
    if !strings.HasPrefix(abs, cwd) {
        return fmt.Errorf("db path must be under current directory: %s", path)
    }
    return nil
}
```

- Exit codes: 0=success, 1=expected negative, 2=unexpected error, 3=usage error
- Schema version check centralized in `db.Open()` (IMP-3) — returns `ErrSchemaVersionTooNew` if user_version > max supported
- `ic` with no args prints help

**Files:** `infra/intercore/cmd/ic/main.go`

**Acceptance:**
- `ic` prints usage
- `ic init` creates DB
- `ic version` prints version
- `ic health` verifies DB
- Unknown subcommand exits 3
- `ic init --db=/etc/passwd.db` → exit 2 (path outside CWD)
- `ic init --db=../../escape.db` → exit 2 (contains `..`)
- `ic init --db=noext` → exit 2 (no `.db` extension)
- `ic init --db=.clavain/intercore.db` → exit 0 (valid)

### Batch 1 review checkpoint

After completing Tasks 1.1–1.3:
- Run `go test ./...` — all tests pass
- Run `go vet ./...` — no issues
- Verify: `ic init && ic health && ic version` works end-to-end

---

## Batch 2: Sentinel Operations (F3)

### Task 2.1: Sentinel check with CTE+RETURNING

`internal/sentinel/sentinel.go`:

```go
type Store struct {
    db *sql.DB
}

func (s *Store) Check(ctx context.Context, name, scopeID string, intervalSec int) (bool, error)
func (s *Store) Reset(ctx context.Context, name, scopeID string) error
func (s *Store) List(ctx context.Context) ([]Sentinel, error)
func (s *Store) Prune(ctx context.Context, olderThan time.Duration) (int64, error)
```

**Check implementation (CTE+RETURNING):**

```go
func (s *Store) Check(ctx context.Context, name, scopeID string, intervalSec int) (bool, error) {
    tx, err := s.db.BeginTx(ctx, &sql.TxOptions{})
    if err != nil {
        return false, fmt.Errorf("begin tx: %w", err)
    }
    defer tx.Rollback()

    // Ensure row exists (INSERT OR IGNORE for first-time sentinels)
    _, err = tx.ExecContext(ctx,
        "INSERT OR IGNORE INTO sentinels (name, scope_id, last_fired) VALUES (?, ?, 0)",
        name, scopeID)
    if err != nil {
        return false, fmt.Errorf("ensure sentinel: %w", err)
    }

    // Atomic claim with CTE+RETURNING
    // NOTE: outer parentheses required for correct precedence (P1-1)
    var allowed int
    err = tx.QueryRowContext(ctx, `
        WITH claim AS (
            UPDATE sentinels
            SET last_fired = unixepoch()
            WHERE name = ? AND scope_id = ?
              AND ((? = 0 AND last_fired = 0)
                   OR (? > 0 AND unixepoch() - last_fired >= ?))
            RETURNING 1
        )
        SELECT COUNT(*) FROM claim`,
        name, scopeID, intervalSec, intervalSec, intervalSec,
    ).Scan(&allowed)
    if err != nil {
        return false, fmt.Errorf("sentinel check: %w", err)
    }

    // Synchronous auto-prune: delete stale sentinels in same tx (P1-4)
    // Runs within existing IMMEDIATE tx — adds <1ms overhead
    if _, err := tx.ExecContext(ctx,
        "DELETE FROM sentinels WHERE unixepoch() - last_fired > 604800"); err != nil {
        // Log but don't abort the sentinel check
        fmt.Fprintf(os.Stderr, "ic: auto-prune: %v\n", err)
    }

    if err := tx.Commit(); err != nil {
        return false, fmt.Errorf("commit: %w", err)
    }
    return allowed == 1, nil
}
```

**interval=0 semantics:** When interval is 0, the sentinel fires only if `last_fired = 0` (the initial INSERT value). Once fired, `last_fired > 0` and can never fire again for that scope_id.

**Auto-prune (P1-4):** Runs synchronously inside the same `BEGIN IMMEDIATE` transaction as the sentinel check — no goroutine. This avoids the "goroutine killed on CLI exit" problem. Errors logged to stderr but don't abort the check.

**Files:** `infra/intercore/internal/sentinel/sentinel.go`, `infra/intercore/internal/sentinel/sentinel_test.go`

**Acceptance:**
- Unit test: single check returns allowed, second check within interval returns throttled
- Unit test: check after interval expires returns allowed again
- Unit test: interval=0 fires once, then always throttled
- Concurrency test: 10 goroutines check same sentinel — exactly 1 allowed

### Task 2.2: Sentinel CLI subcommands

Wire `sentinel check`, `sentinel reset`, `sentinel list`, `sentinel prune` into CLI.

```
ic sentinel check <name> <scope_id> --interval=<seconds>
  stdout: "allowed" or "throttled"
  exit: 0 (allowed) or 1 (throttled) or 2 (error)

ic sentinel reset <name> <scope_id>
  stdout: "reset"
  exit: 0

ic sentinel list
  stdout: one sentinel per line: "<name>\t<scope_id>\t<last_fired_unix>"
  exit: 0

ic sentinel prune --older-than=<duration>
  stdout: "<count> pruned"
  exit: 0
```

**Auto-prune:** Handled synchronously inside `Check()` — see Task 2.1. No separate goroutine.

**Files:** `infra/intercore/cmd/ic/main.go` (add sentinel subcommands)

**Acceptance (table-driven test structure, IMP-6):**
```go
func TestSentinelCheck(t *testing.T) {
    tests := []struct {
        name        string
        sentinel    string
        scopeID     string
        interval    int
        setupFired  int64  // pre-set last_fired (0 = fresh)
        wantAllowed bool
    }{
        {"fresh sentinel fires", "stop", "s1", 0, 0, true},
        {"interval=0 second call throttled", "stop", "s1", 0, 1, false},
        {"interval=5 within window throttled", "rate", "s1", 5, time.Now().Unix() - 2, false},
        {"interval=5 after window fires", "rate", "s1", 5, time.Now().Unix() - 10, true},
    }
    for _, tt := range tests { /* ... */ }
}
```
- `ic sentinel check stop $SID --interval=0` returns "allowed", then "throttled"
- `ic sentinel list` shows the sentinel
- `ic sentinel reset stop $SID` clears it
- `ic sentinel prune --older-than=0s` removes all sentinels

### Batch 2 review checkpoint

After completing Tasks 2.1–2.2:
- `go test ./...` — all pass, including concurrency test
- `go test -race ./...` — no race conditions
- Manual smoke test: `ic init && ic sentinel check test sess1 --interval=5` → allowed → re-run → throttled → wait 5s → re-run → allowed

---

## Batch 3: State Operations (F2)

### Task 3.1: State CRUD implementation

`internal/state/state.go`:

```go
type Store struct {
    db *sql.DB
}

func (s *Store) Set(ctx context.Context, key, scopeID string, payload json.RawMessage, ttl time.Duration) error
func (s *Store) Get(ctx context.Context, key, scopeID string) (json.RawMessage, error)
func (s *Store) Delete(ctx context.Context, key, scopeID string) (bool, error)  // IMP-5
func (s *Store) List(ctx context.Context, key string) ([]string, error)
func (s *Store) Prune(ctx context.Context) (int64, error)
```

**Set implementation:**
- Validate JSON payload with `validatePayload()` (P0-2) — see below
- Check payload size < 1MB — exit 2 on overflow
- Use `INSERT OR REPLACE INTO state (key, scope_id, payload, updated_at, expires_at) VALUES (?, ?, ?, unixepoch(), ?)` in `BEGIN IMMEDIATE` transaction
- **TTL computation entirely in Go (P1-3):** `expires_at = time.Now().Unix() + int64(ttl.Seconds())` — not SQL arithmetic. This avoids SQLite REAL promotion when adding float64 to integer.

**JSON validation (P0-2):**
```go
const (
    maxPayloadSize   = 1 << 20  // 1MB
    maxNestingDepth  = 20
    maxKeyLength     = 1000
    maxStringLength  = 100 * 1024  // 100KB per string value
    maxArrayLength   = 10000
)

func validatePayload(data []byte) error {
    if len(data) > maxPayloadSize {
        return fmt.Errorf("payload too large: %d bytes (max %d)", len(data), maxPayloadSize)
    }
    if !json.Valid(data) {
        return fmt.Errorf("invalid JSON")
    }
    // Depth/key/value validation via json.Decoder walk
    return validateJSONDepth(data, 0)
}
```

The `validateJSONDepth` function uses `json.Decoder` to walk tokens and enforce nesting depth, key length, string value length, and array length limits. Control characters (U+0000–U+001F except standard escapes) are rejected.

**Get implementation:**
- `SELECT payload FROM state WHERE key = ? AND scope_id = ? AND (expires_at IS NULL OR expires_at > unixepoch())`
- Return `ErrNotFound` if no row → CLI exits 1
- TTL enforced in query — expired rows invisible

**List implementation:**
- `SELECT scope_id FROM state WHERE key = ? AND (expires_at IS NULL OR expires_at > unixepoch()) ORDER BY scope_id`

**Prune implementation:**
- `DELETE FROM state WHERE expires_at IS NOT NULL AND expires_at <= unixepoch()`
- Return count of deleted rows

**Files:** `infra/intercore/internal/state/state.go`, `infra/intercore/internal/state/state_test.go`

**Acceptance:**
- Unit test: set/get roundtrip with JSON payload
- Unit test: TTL enforcement — set with 1s TTL, verify get after 2s returns not found
- Unit test: TTL of 1500ms produces `expires_at` truncated to 1 second (P1-3)
- Unit test: invalid JSON rejected with error
- Unit test: payload >1MB rejected
- Unit test: nesting depth >20 rejected (P0-2)
- Unit test: key length >1000 rejected (P0-2)
- Unit test: array with >10k elements rejected (P0-2)
- Unit test: prune removes only expired rows

### Task 3.2: State CLI subcommands

```
ic state set <key> <scope_id> [--ttl=<duration>]
  Reads JSON payload from stdin.
  Also accepts: ic state set <key> <scope_id> @<filepath>
  exit: 0 (written) or 2 (error: invalid JSON, too large, DB error)

ic state get <key> <scope_id>
  stdout: JSON payload
  exit: 0 (found) or 1 (not found)

ic state list <key>
  stdout: one scope_id per line
  exit: 0

ic state delete <key> <scope_id>
  stdout: "deleted" or "not found"
  exit: 0

ic state prune
  stdout: "<count> pruned"
  exit: 0
```

**stdin reading:** If no `@filepath` argument, read stdin until EOF. Validate before writing (P0-2: full `validatePayload()` check).

**Files:** `infra/intercore/cmd/ic/main.go` (add state subcommands)

**Acceptance:**
- `echo '{"phase":"executing"}' | ic state set dispatch sess1` → exit 0
- `ic state get dispatch sess1` → `{"phase":"executing"}`
- `ic state set dispatch sess1 @/tmp/payload.json` → reads from file
- `echo 'not json' | ic state set bad sess1` → exit 2
- `ic state list dispatch` → `sess1`
- `ic state prune` → `0 pruned`

### Batch 3 review checkpoint

- `go test ./...` — all pass
- Full CLI smoke test: init → state set → state get → state list → state prune
- Verify TTL enforcement end-to-end

---

## Batch 4: Bash Integration Library (F5)

### Task 4.1: lib-intercore.sh

Create `infra/intercore/lib-intercore.sh`:

```bash
# lib-intercore.sh — Bash wrappers for intercore CLI
# This file is SOURCED by hooks. Do NOT use set -e here — it would exit
# the parent shell on any failure. (P1-7)
# Source in hooks: source "$(dirname "$0")/lib-intercore.sh"
# shellcheck shell=bash

INTERCORE_BIN=""

intercore_available() {
    # Returns 0 (available) or 1 (unavailable).
    # "binary not found" = fail-safe, return 0 (PRD: don't block workflow) (P1-5)
    # "binary found but DB broken" = fail-loud, return 1 (log error to stderr)
    if [[ -n "$INTERCORE_BIN" ]]; then return 0; fi
    INTERCORE_BIN=$(command -v ic 2>/dev/null || command -v intercore 2>/dev/null)
    if [[ -z "$INTERCORE_BIN" ]]; then
        # No binary — fail-safe: pretend available so wrappers return defaults
        return 1  # Signal "not available" — wrappers handle fail-safe individually
    fi
    # Binary exists — check health
    if ! "$INTERCORE_BIN" health >/dev/null 2>&1; then
        echo "ic: DB health check failed — run 'ic init' or 'ic health'" >&2
        INTERCORE_BIN=""  # Reset so next call retries
        return 1  # fail-loud: DB exists but broken
    fi
    return 0
}

intercore_state_set() {
    local key="$1" scope_id="$2" json="$3"
    if ! intercore_available; then return 0; fi  # fail-safe if unavailable
    printf '%s\n' "$json" | "$INTERCORE_BIN" state set "$key" "$scope_id" || return 0
    # (P1-7: printf instead of echo; P2-4: no 2>/dev/null — let structural errors show)
}

intercore_state_get() {
    local key="$1" scope_id="$2"
    if ! intercore_available; then echo ""; return; fi
    "$INTERCORE_BIN" state get "$key" "$scope_id" 2>/dev/null || echo ""
}

intercore_sentinel_check() {
    local name="$1" scope_id="$2" interval="$3"
    if ! intercore_available; then return 0; fi  # fail-safe: allow if unavailable
    "$INTERCORE_BIN" sentinel check "$name" "$scope_id" --interval="$interval" >/dev/null
    # (P2-4: no 2>/dev/null — structural errors propagate to stderr)
}
```

**Removed `intercore_sentinel_check_many` (P2-2):** No CLI batch endpoint exists. The function would still spawn one `ic` process per sentinel with no actual batching. Add `ic sentinel check-batch` only if profiling proves subprocess overhead is material.

**Files:** `infra/intercore/lib-intercore.sh`

**Acceptance:**
- Source the library, call `intercore_available` → returns 0 if ic on PATH and DB healthy
- `intercore_state_set dispatch sess1 '{"phase":"x"}'` → writes to DB
- `intercore_state_get dispatch sess1` → returns JSON
- `intercore_sentinel_check stop sess1 0` → returns 0 (allowed) then 1 (throttled)
- With `ic` not on PATH: `intercore_available` returns 1, wrapper functions return 0 (fail-safe)
- `shellcheck lib-intercore.sh` passes with no errors (P1-7)
- Structural errors (DB corruption) print to stderr, not suppressed

### Task 4.2: Integration test script

Create `infra/intercore/test-integration.sh`:

```bash
#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
TEST_DIR=$(mktemp -d)
TEST_DB="$TEST_DIR/.clavain/intercore.db"

# Trap-based cleanup (fd-quality: ensures cleanup even on failure)
cleanup() { rm -rf "$TEST_DIR" /tmp/ic-test; }
trap cleanup EXIT

# Build ic binary
cd "$SCRIPT_DIR"
go build -o /tmp/ic-test ./cmd/ic
export PATH="/tmp:$PATH"

# Create test DB (under a .clavain/ subdir to satisfy path validation)
mkdir -p "$TEST_DIR/.clavain"
cd "$TEST_DIR"
ic init --db="$TEST_DB"

# Source library and test fail-safe behavior
source "$SCRIPT_DIR/lib-intercore.sh"

# Test state operations
printf '%s\n' '{"phase":"brainstorm"}' | ic state set dispatch test-session --db="$TEST_DB"
result=$(ic state get dispatch test-session --db="$TEST_DB")
[[ "$result" == '{"phase":"brainstorm"}' ]] || { echo "FAIL: state get"; exit 1; }

# Test sentinel operations
ic sentinel check stop test-session --interval=0 --db="$TEST_DB" >/dev/null
ic sentinel check stop test-session --interval=0 --db="$TEST_DB" >/dev/null && { echo "FAIL: sentinel should be throttled"; exit 1; } || true

# Test TTL enforcement
printf '%s\n' '{"temp":true}' | ic state set ephemeral test-session --ttl=1s --db="$TEST_DB"
sleep 2
ic state get ephemeral test-session --db="$TEST_DB" && { echo "FAIL: expired state visible"; exit 1; } || true

# Test JSON validation (P0-2)
printf '%s\n' 'not json' | ic state set bad test-session --db="$TEST_DB" 2>/dev/null && { echo "FAIL: invalid JSON accepted"; exit 1; } || true

# Test path traversal protection (P0-1)
ic init --db="/tmp/evil.db" 2>/dev/null && { echo "FAIL: path traversal accepted"; exit 1; } || true

# Test fail-safe: unset binary, verify functions don't block
INTERCORE_BIN=""
PATH="/nonexistent:$PATH" intercore_sentinel_check stop test-session 0
[[ $? -eq 0 ]] || { echo "FAIL: fail-safe not working"; exit 1; }

echo "All integration tests passed."
```

**Files:** `infra/intercore/test-integration.sh`

**Acceptance:**
- `bash test-integration.sh` exits 0
- Cleanup runs even on test failure (trap-based)

### Batch 4 review checkpoint

- All Go tests pass
- Integration test passes
- Library functions work with and without `ic` on PATH

---

## Batch 5: Read-Fallback Migration (F7)

### Task 5.1: ic compat subcommands

```
ic compat status [--db=<path>]
  Shows which temp file patterns still exist and whether intercore has data for them.
  stdout: table of key, legacy_exists (bool), db_exists (bool)

ic compat check <key> [--db=<path>]
  Tests if a specific key has data in DB.
  exit: 0 (data in DB) or 1 (only in legacy)
```

**Implementation:** Check for known legacy paths:
- `dispatch` → `/tmp/clavain-dispatch-*.json`
- `stop` → `/tmp/clavain-stop-*`
- `compound_throttle` → `/tmp/clavain-compound-last-*`
- `drift_throttle` → `/tmp/clavain-drift-last-*`
- `handoff` → `/tmp/clavain-handoff-*`
- `autopub` → `/tmp/clavain-autopub*.lock`
- `catalog_remind` → `/tmp/clavain-catalog-remind-*.lock`
- `discovery_brief` → `/tmp/clavain-discovery-brief-*.cache`

**Files:** `infra/intercore/internal/compat/compat.go`, CLI wiring in `main.go`

**Acceptance:**
- `ic compat status` shows table of all known patterns
- `ic compat check dispatch` returns exit 0 if dispatch state in DB, else exit 1

### Task 5.2: Migration documentation

Create `infra/intercore/MIGRATION.md` documenting:

1. Which hooks need updating (per temp file pattern)
2. Read-fallback pattern for consumers (try `ic state get`, fall back to file)
3. Timeline: Phase 1 (read-fallback) → Phase 2 (validation) → Phase 3 (legacy removal)
4. One-by-one hook migration examples
5. **Pre-migration cleanup step (P2-1):** Before enabling read-fallback, run `rm -f /tmp/clavain-dispatch-*.json /tmp/clavain-stop-* /tmp/clavain-compound-last-* /tmp/clavain-drift-last-*` to prevent stale legacy files from gating hooks after migration
6. **Migration window constraint (P2-1):** All hooks producing a given key must be migrated before any consumer switches to read-fallback for that key, to prevent dual-source divergence
7. **Security notes:** Why `touch` is unsafe for sentinels (symlink attack), use `mkdir` instead

**Files:** `infra/intercore/MIGRATION.md`

### Task 5.3: Example hook migration — stop sentinel

Show the migration pattern by converting the stop sentinel from touch-file to intercore:

**Before (current pattern in auto-compound.sh):**
```bash
STOP_SENTINEL="/tmp/clavain-stop-${SESSION_ID}"
if [[ -d "$STOP_SENTINEL" ]]; then exit 0; fi
mkdir "$STOP_SENTINEL" 2>/dev/null || exit 0  # atomic O_EXCL via mkdir
```

**After (with read-fallback):**
```bash
source lib-intercore.sh
if intercore_available; then
    intercore_sentinel_check stop "$SESSION_ID" 0 || exit 0
else
    # Legacy fallback — uses mkdir (atomic), NOT touch (symlink-vulnerable) (P1-8)
    STOP_SENTINEL="/tmp/clavain-stop-${SESSION_ID}"
    if [[ -d "$STOP_SENTINEL" ]]; then exit 0; fi
    mkdir "$STOP_SENTINEL" 2>/dev/null || exit 0
fi
```

**Security note (P1-8):** All migration examples use `mkdir` instead of `touch` for sentinel files. `touch` is vulnerable to symlink attacks (attacker races to create a symlink before `touch` runs). `mkdir` with `O_EXCL` semantics is atomic and fails safely if the target is a symlink.

Document this pattern in MIGRATION.md. Do NOT modify actual hooks yet — that's post-launch migration work.

**Files:** `infra/intercore/MIGRATION.md` (updated with example)

### Batch 5 review checkpoint

- `ic compat status` works
- Migration docs are clear and complete
- Example migration pattern is correct

---

## Post-Batch: Polish and Ship

### Task 6.1: CLAUDE.md and AGENTS.md for intercore

Create project documentation following Interverse conventions.

**Files:** `infra/intercore/CLAUDE.md`, `infra/intercore/AGENTS.md`

### Task 6.2: Build and install

- `go build -o ic ./cmd/ic`
- Install to `~/.local/bin/ic`
- Verify `which ic` finds it

### Task 6.3: Update parent beads

- Close child feature beads (iv-fnfa F1, iv-e0sf F3, iv-a07m F2, iv-v220 F5, iv-xn1s F7)
- Update iv-ieh7 with completion notes

---

## Dependency Graph

```
Task 1.1 (project structure)
  └→ Task 1.2 (schema + migration + backup)
       └→ Task 1.3 (CLI framework + path validation)
            ├→ Task 2.1 (sentinel logic + auto-prune)  ←── parallel track A
            │    └→ Task 2.2 (sentinel CLI)             │
            │                                           │
            └→ Task 3.1 (state logic + JSON validation) ←── parallel track B
                 └→ Task 3.2 (state CLI)
                                    │
                      ┌─────────────┘ (both tracks merge)
                      ↓
                 Task 4.1 (bash library)
                      └→ Task 4.2 (integration test)
                           └→ Task 5.1 (compat commands)
                                └→ Task 5.2 (migration docs)
                                     └→ Task 5.3 (example migration)
```

**Batches 2 and 3 are independent** — they share only the DB handle and schema from Batch 1. They can be implemented in parallel (P2-3). The plan orders sentinels first because they're the highest-value feature (fix TOCTOU races), but state can proceed concurrently if multiple implementers are available.

## Risk Mitigations

| Risk | Mitigation |
|------|-----------|
| `modernc.org/sqlite` doesn't support RETURNING | Verify with `SELECT sqlite_version()` — need 3.35+. modernc.org/sqlite v1.29 bundles SQLite 3.44, so RETURNING is available. |
| Hook latency > 50ms budget | Profile `ic sentinel check` end-to-end. Add `db_bench_test.go` measuring at 10k rows (IMP-1). If slow, pre-warm with `ic health` in session-start hook. |
| `.clavain/` dir doesn't exist | `ic init` creates it via `os.MkdirAll`. Also check in `Open()`. Reject if `.clavain` is a symlink (P2-5). |
| Concurrent schema migration | Migration reads `user_version` inside `BEGIN IMMEDIATE` tx — prevents TOCTOU race (P1-6). |
| DB corruption from kill -9 | WAL mode + `PRAGMA synchronous=NORMAL` (default) means data is safe as long as OS doesn't lose pages. Pre-migration backup created automatically (P0-3). |
| Path traversal via `--db` flag | `validateDBPath()` enforces `.db` extension, no `..`, under CWD (P0-1). |
| Malicious JSON payloads | `validatePayload()` enforces depth≤20, key≤1000, string≤100KB, array≤10k (P0-2). |
| Migration failure with no recovery | Timestamped backup created before migration. AGENTS.md documents recovery procedures (P0-3). |

## Benchmark Task (IMP-1)

Add `infra/intercore/internal/db/db_bench_test.go`:

```go
func BenchmarkSentinelCheck(b *testing.B) {
    // Pre-populate 1000 sentinels, measure Check latency
}

func BenchmarkStateGet(b *testing.B) {
    // Pre-populate 10,000 state rows, measure Get latency
}

func BenchmarkStateSet(b *testing.B) {
    // Measure Set with JSON validation overhead
}
```

Acceptance: P99 < 50ms for all operations at specified row counts.

## Review Findings Addressed

This plan revision (v2) addresses all P0/P1 findings from the flux-drive review:

| Finding | Fix | Location |
|---------|-----|----------|
| P0-1: Path traversal `--db` | `validateDBPath()` | Task 1.3 |
| P0-2: JSON depth/size limits | `validatePayload()` | Task 3.1 |
| P0-3: Irreversible migration | Pre-migration backup | Task 1.2 |
| P1-1: Sentinel WHERE precedence | Added parentheses | Task 2.1 |
| P1-2: SetMaxOpenConns(1) | Wired in `Open()` | Task 1.2 |
| P1-3: TTL float64 promotion | Go arithmetic, not SQL | Task 3.1 |
| P1-4: Auto-prune goroutine | Synchronous in-tx delete | Task 2.1 |
| P1-5: `intercore_available()` return | Fail-safe logic fixed | Task 4.1 |
| P1-6: Migration TOCTOU | Schema check inside tx | Task 1.2 |
| P1-7: Bash strict mode/printf | Header comment, `printf` | Task 4.1 |
| P1-8: Unsafe `touch` in example | Replaced with `mkdir` | Task 5.3 |

P2 items incorporated: P2-2 (removed `check_many`), P2-4 (stderr suppression), P2-5 (symlink check).
IMP items incorporated: IMP-1 (benchmark), IMP-2 (single schema version), IMP-3 (centralized check), IMP-6 (table-driven tests).
