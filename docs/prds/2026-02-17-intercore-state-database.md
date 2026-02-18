# PRD: intercore — Unified State Database

**Bead:** iv-ieh7
**Version:** v2 (revised per 4-agent review 2026-02-17)

## Problem

The Clavain hook infrastructure communicates through ~15 scattered temp files in `/tmp/`, each with its own naming convention, TTL logic, and cleanup strategy. This causes TOCTOU race conditions in throttle guards, makes cross-session state invisible, and requires every new hook to invent its own state management pattern.

## Solution

A Go CLI (`ic`) backed by a single SQLite WAL database (`intercore.db`) that provides atomic state operations and throttle guards callable from bash hooks. Lives at `infra/intercore/` as foundational infrastructure (not a plugin — hooks and plugins depend on it, so it sits below them in the dependency graph).

## Scope: v1

v1 solves the two core problems — **ephemeral state chaos** and **TOCTOU throttle races** — with the minimum feature set:

| Feature | What it solves |
|---------|---------------|
| F1: Scaffold + Schema | Go CLI, SQLite DB, auto-migration |
| F3: Sentinel Operations | Atomic throttle guards (replaces touch-file + `find -mmin`) |
| F2: State Operations | Structured ephemeral state (replaces JSON temp files) |
| F5: Bash Integration Library | Drop-in wrappers for hooks |
| F7: Backward Compatibility | Read-fallback migration (not dual-write) |

**Deferred to v2** (after measuring adoption):
- ~~F4: Run Tracking~~ — overlaps with beads (`bd set-state`, `bd state`). If run observability is needed, extend beads instead.
- ~~F6: Mutex Consolidation~~ — `mkdir` locks work; consolidation is admin work, not a user pain point.

## Features

### F1: Go CLI Scaffold and Schema

**What:** Create `infra/intercore/` with Go module, SQLite schema, auto-migration, and the `ic` CLI entry point.

**Acceptance criteria:**
- [ ] `go build ./cmd/ic` produces a working binary
- [ ] Running `ic init` creates `intercore.db` with tables (`state`, `sentinels`) and schema version tracking via `PRAGMA user_version`
- [ ] Schema migrations run automatically on first use and on version bumps, each wrapped in `BEGIN IMMEDIATE; ... COMMIT;`
- [ ] WAL mode enabled by default (persistent after first `PRAGMA journal_mode=WAL`)
- [ ] `busy_timeout` set via DSN parameter so it applies to every connection (default 100ms; override with `ic --timeout=<duration>`)
- [ ] `ic version` prints CLI version and schema version
- [ ] `ic health` checks DB is readable, schema is current, and disk has >10MB free
- [ ] `ic` with no args prints usage summary with all commands
- [ ] All errors include actionable recovery suggestions (e.g., "Run 'ic init' to create the database")
- [ ] `ic` checks `PRAGMA user_version` on startup; if schema version > max supported, exits with clear upgrade message
- [ ] All timestamp columns are `INTEGER NOT NULL DEFAULT (unixepoch())` — no TEXT timestamps
- [ ] Schema includes indexes: `state(scope_id, key)`, `state(expires_at)`, `sentinels(name, scope_id)`

**Module structure:**
- Module path: `github.com/mistakeknot/interverse/infra/intercore`
- Package layout: `cmd/ic/` (CLI entry), `internal/db/` (SQLite layer), `internal/state/` (state ops), `internal/sentinel/` (throttle logic)
- No public Go API in v1 — CLI only, bash hooks shell out
- SQLite driver: `modernc.org/sqlite` (pure Go, no CGO)
- CLI framework: standard `flag` package or lightweight library (Kong preferred for subcommands)

### F2: State Operations

**What:** CRUD operations for structured ephemeral state (key/scope_id/payload), replacing JSON temp files and interband sideband entries.

**Acceptance criteria:**
- [ ] `ic state set <key> <scope_id>` reads JSON payload from **stdin** (avoids shell quoting issues)
- [ ] Also supports `ic state set <key> <scope_id> @<filepath>` to read from a file
- [ ] `ic state set` supports `--ttl=<duration>` to set `expires_at` (Go `time.ParseDuration` strings: `5m`, `24h`)
- [ ] `ic state get <key> <scope_id>` returns payload JSON (exit 0) or empty (exit 1)
- [ ] **TTL enforced in queries**: all `SELECT` include `AND (expires_at IS NULL OR expires_at > unixepoch())`
- [ ] `ic state list <key>` lists all scope_ids for a given key (one per line, no headers)
- [ ] `ic state prune` deletes expired rows, returns count deleted (background optimization, not correctness requirement)
- [ ] JSON payloads validated before insertion (exit 2 on invalid JSON); max payload 1MB
- [ ] Output is plain text by default (newline-delimited), `--json` flag for structured output
- [ ] All write operations use `BEGIN IMMEDIATE` transactions
- [ ] Read-only operations use `DEFERRED` transactions

**Removed from v1:** `--debounce` flag. Debounce belongs in the caller (bash hook in-memory cache), not in a CLI that opens/closes DB per invocation.

**Removed from v1:** `scope_type` column. `scope_id` is an opaque string — callers encode type in the key name if needed (e.g., key=`dispatch`, scope_id=session ID). Add `scope_type` in v2 if polymorphic queries prove necessary.

### F3: Sentinel Operations

**What:** Atomic claim-if-eligible throttle checks, replacing touch-file + `find -mmin` guards.

**Acceptance criteria:**
- [ ] `ic sentinel check <name> <scope_id> --interval=<seconds>` returns "allowed" (exit 0) or "throttled" (exit 1) in a single atomic operation
- [ ] Implementation uses **CTE + RETURNING** pattern (not `changes()`) to avoid connection-pool TOCTOU:
  ```sql
  WITH claim AS (
    UPDATE sentinels
    SET last_fired = unixepoch()
    WHERE name = ? AND scope_id = ?
      AND (last_fired IS NULL OR unixepoch() - last_fired >= ?)
    RETURNING 1
  )
  SELECT COUNT(*) AS allowed FROM claim;
  ```
- [ ] If sentinel row doesn't exist, `INSERT OR IGNORE` creates it before the claim attempt
- [ ] When `--interval=0`, sentinel fires at most once per scope_id (once-per-session guard)
- [ ] Documented limitation: if hook crashes after sentinel fires but before work completes, sentinel blocks retry. Use explicit state tracking (`ic state set`) for critical actions that must complete.
- [ ] Concurrent calls correctly serialize via `BEGIN IMMEDIATE` — only one wins
- [ ] `ic sentinel reset <name> <scope_id>` clears a sentinel (for testing/recovery)
- [ ] `ic sentinel list` shows all active sentinels with `last_fired` timestamps
- [ ] `ic sentinel prune --older-than=<duration>` cleans up stale sentinels
- [ ] Auto-prune: after each `sentinel check`, asynchronously delete sentinels older than 7 days

### F5: Bash Integration Library

**What:** A thin `lib-intercore.sh` bash library that wraps `ic` commands for use in existing hooks, providing drop-in replacements for current temp file operations.

**Acceptance criteria:**
- [ ] `intercore_state_set <key> <scope_id> <json>` wraps `ic state set` — pipes JSON via stdin to avoid quoting issues
- [ ] `intercore_state_get <key> <scope_id>` wraps `ic state get`, returns payload or empty string
- [ ] `intercore_sentinel_check <name> <scope_id> <interval>` wraps `ic sentinel check`, returns 0 (allowed) or 1 (throttled)
- [ ] `intercore_available()` returns 0 if `ic` binary is on PATH and `ic health` succeeds
- [ ] **Fail-safe with distinction:**
  - "DB unavailable" (no binary, no DB file): fail-safe, return 0, never block workflow
  - "DB available but broken" (schema mismatch, corruption): fail-loud, return 1, log error to stderr
- [ ] Library auto-discovers `ic` binary location (PATH or `~/.local/bin/ic`)
- [ ] `intercore_sentinel_check_many <name1:scope1:interval1> <name2:scope2:interval2> ...` batches multiple sentinel checks in a single `ic` invocation (reduces subprocess overhead)

### F7: Backward Compatibility — Read-Fallback Migration

**What:** Gradual migration from temp files to intercore using a **read-fallback** strategy (not dual-write). intercore writes to DB only; legacy consumers try DB first, fall back to legacy files.

**Rationale:** Dual-write has no atomic cross-backend commit. If DB write succeeds but file write fails (or vice versa), state diverges permanently. Read-fallback avoids this by maintaining a single source of truth (DB) while letting legacy readers gracefully degrade.

**Migration phases:**

**Phase 1: Read-fallback (v1 launch)**
- [ ] `ic state set` writes to DB only (single source of truth)
- [ ] `ic state get` reads from DB only
- [ ] Updated consumers (interline, interband) try `ic state get` first; if empty/unavailable, fall back to legacy temp file
- [ ] Hooks begin using `lib-intercore.sh` wrappers instead of writing temp files directly

**Phase 2: Validation (4 weeks post-launch)**
- [ ] `ic compat status` reports which consumers still fall back to legacy files
- [ ] Verify all active hooks use `lib-intercore.sh`
- [ ] Run `ic compat check <key>` to test if a consumer can read from DB for a specific key

**Phase 3: Legacy removal**
- [ ] Remove fallback logic from consumers
- [ ] Remove temp file writes from hooks
- [ ] Cleanup script deletes stale temp files: `rm -f /tmp/clavain-dispatch-*.json /tmp/clavain-bead-*.json /tmp/clavain-stop-*`

## Error Handling

### Exit Code Conventions

| Exit Code | Meaning | Example |
|-----------|---------|---------|
| 0 | Success / allowed / found | `ic state get` returns payload |
| 1 | Expected negative result | `ic sentinel check` → throttled; `ic state get` → not found |
| 2 | Unexpected error | Invalid JSON, DB corruption, constraint violation |
| 3 | Usage error | Missing required argument, unknown subcommand |

### Error Output

- All errors written to stderr, never stdout
- Format: `ic: <context>: <message>` (e.g., `ic: state set: invalid JSON payload`)
- All errors include actionable recovery suggestion
- `--verbose` flag logs SQL statements, timings, and lock wait durations to stderr

### Go Error Patterns

- All errors wrapped with `fmt.Errorf("context: %w", err)` for stack traces
- Sentinel errors for expected failures: `ErrNotFound`, `ErrThrottled`, `ErrSchemaVersion`
- `SQLITE_BUSY` handled by `busy_timeout` DSN parameter — no manual retry loops
- Unexpected panics caught by top-level recover, logged to stderr, exit 2

### Database Error Handling

- DB file locked: wait up to `busy_timeout` (default 100ms, configurable), then exit 2
- DB file missing: exit 2 with "Run 'ic init' to create the database"
- Schema version mismatch (too new): exit 2 with "Upgrade intercore to v<required>"
- WAL corruption: exit 2 with "Run 'ic health' to diagnose"
- Disk full: exit 2 with "Disk full, cannot write to WAL"

## Technical Specifications

### Schema DDL

```sql
PRAGMA journal_mode = WAL;
PRAGMA user_version = 1;

CREATE TABLE state (
    key         TEXT NOT NULL,
    scope_id    TEXT NOT NULL,
    payload     TEXT NOT NULL,
    updated_at  INTEGER NOT NULL DEFAULT (unixepoch()),
    expires_at  INTEGER,
    PRIMARY KEY (key, scope_id)
);

CREATE INDEX idx_state_scope ON state(scope_id, key);
CREATE INDEX idx_state_expires ON state(expires_at) WHERE expires_at IS NOT NULL;

CREATE TABLE sentinels (
    name        TEXT NOT NULL,
    scope_id    TEXT NOT NULL,
    last_fired  INTEGER NOT NULL DEFAULT (unixepoch()),
    PRIMARY KEY (name, scope_id)
);

CREATE TABLE schema_version (
    version     INTEGER PRIMARY KEY,
    applied_at  INTEGER NOT NULL DEFAULT (unixepoch())
);
```

### Transaction Isolation

| Operation | Isolation | Rationale |
|-----------|-----------|-----------|
| `state set` | `BEGIN IMMEDIATE` | Write lock before read to prevent lost updates |
| `state get` | `DEFERRED` | Read-only, no lock contention |
| `sentinel check` | `BEGIN IMMEDIATE` | Claim must serialize — only one winner |
| `sentinel reset` | `BEGIN IMMEDIATE` | Write operation |
| `state prune` | `BEGIN IMMEDIATE` | Bulk delete, acquire lock early |

### Performance Budget

- `ic` commands complete in < 50ms P99 on a DB with 10,000 state rows and 1,000 sentinels
- DB file size grows by < 10KB per day of normal usage
- `ic state prune` runs in < 100ms for 1,000 expired rows
- Process startup overhead (Go binary cold start): < 20ms

### Connection Management

- Use `database/sql` with `SetMaxOpenConns(1)` — single-writer for WAL mode correctness
- Set `busy_timeout` via DSN parameter: `file:<path>?_busy_timeout=100`
- WAL mode set via `PRAGMA journal_mode=WAL` on first connection (persistent)
- No connection pooling — CLI process lifetime is a single command

## Non-goals

- **Replacing beads (bd)** — beads is the authoritative issue tracker and permanent phase/dependency store. intercore handles ephemeral/session state only.
- **Replacing interband entirely** — interband may evolve into a view layer, but that's a separate decision post-v1 adoption review.
- **DB-backed mutexes** — filesystem `mkdir` locks stay. Mutex consolidation (F6) deferred to v2.
- **Run tracking (F4)** — deferred to v2. If run observability is needed, extend beads (`bd run create`) rather than adding domain tables to intercore.
- **Telemetry migration** — `~/.clavain/telemetry.jsonl` stays as append-only flat file.
- **MCP server** — intercore is CLI-first. MCP exposure is a future feature.
- **Multi-machine distribution** — local-only, single-machine.
- **Dual-write mode** — replaced by read-fallback strategy to avoid cross-backend consistency issues.

## Dependencies

- Go 1.21+ (already available on server)
- SQLite driver: `modernc.org/sqlite` (pure Go, no CGO — simpler builds, easier distribution)
- SQLite version: 3.35+ (for CTE + RETURNING in sentinel claims)
- Existing hook infrastructure (`lib.sh`, `lib-gates.sh`, `lib-sprint.sh`) for integration points

## Decisions (resolved from review)

| Question | Decision | Rationale |
|----------|----------|-----------|
| DB file location | `.clavain/intercore.db` (project-relative) | Matches beads, per-project isolation, trivial backup |
| SQLite driver | `modernc.org/sqlite` (pure Go) | No CGO, simpler builds; performance difference negligible for <1000 ops/sec |
| Sentinel implementation | CTE + RETURNING | `changes()` is connection-local — unsafe with pooled connections |
| Migration strategy | Read-fallback | Dual-write has no atomic cross-backend commit |
| Project location | `infra/intercore/` | Infrastructure, not companion plugin — avoids dependency inversion |
| Schema paradigm | Ephemeral KV (state + sentinels) | Run tracking belongs in beads; no mixed paradigm |
| interband relationship | Deferred to post-v1 | Ship intercore, measure adoption, then decide |
| Scope_type column | Removed | YAGNI — scope_id is opaque string; add polymorphism in v2 if needed |
| Debounce flag | Removed | CLI opens/closes DB per invocation — debounce belongs in caller |

## Success Metrics (Post-Launch)

### Adoption (4 weeks)
- [ ] 10+ hooks migrated to `lib-intercore.sh`
- [ ] 5+ temp file patterns eliminated
- [ ] interline reading dispatch state from intercore

### Reliability (8 weeks)
- [ ] Zero TOCTOU races in sentinels
- [ ] <1% of `ic` calls fail due to DB lock timeouts
- [ ] No schema migration failures

### Cleanup (12 weeks)
- [ ] Legacy read-fallback disabled for all keys
- [ ] All temp file writes removed from hooks

## Implementation Order

1. **F1: Scaffold** — Go module, schema, CLI entry point, `ic init`, `ic health`, `ic version`
2. **F3: Sentinels** — Highest-value feature (fixes TOCTOU races), independent of F2
3. **F2: State operations** — Builds on schema from F1, uses same transaction patterns as F3
4. **F5: Bash library** — Wraps F2/F3, enables hook migration
5. **F7: Read-fallback** — After all features stabilize, update consumers

This order ships the highest-value feature (atomic sentinels) earliest, validates the core approach, then builds incrementally.

## Review History

- **v1** (2026-02-17): Initial PRD
- **v2** (2026-02-17): Revised per 4-agent review (quality, architecture, correctness, user-product). Changes: moved to `infra/`, dropped F4/F6, replaced dual-write with read-fallback, fixed sentinel CTE pattern, resolved all open questions, added error handling + technical specs + success metrics.
