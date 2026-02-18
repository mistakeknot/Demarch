# Research: Intercore Hooks and SQLite DB Pattern

**Date:** 2026-02-17  
**Context:** Understanding existing patterns for rewriting Clavain hooks as thin adapters to intercore's SQLite database.

## Executive Summary

Clavain has **20 hook scripts** (4,424 total lines) using **~15 temp files** in `/tmp/` for state management. Intercore provides a Go CLI (`ic`) with a SQLite WAL database at `.clavain/intercore.db` offering:
- **State operations** (key-value JSON with TTL)
- **Sentinel guards** (atomic throttle checks with auto-prune)
- **Path safety** (no traversal attacks, validates `.db` extension and CWD containment)

**Migration pattern:** Replace temp file I/O with `ic state set/get` and `ic sentinel check` calls via `lib-intercore.sh` bash wrappers. Intercore already has a companion bash library ready for hooks to use.

---

## 1. Existing Clavain Hook Infrastructure

### Hook Inventory

**20 hook scripts, 4,424 total lines:**

| Script | Lines | Purpose | Temp Files Used |
|--------|-------|---------|-----------------|
| `session-start.sh` | 313 | Context injection, companion detection, sprint scan | None (reads hook state from DB in future) |
| `session-handoff.sh` | 142 | Incomplete work detection on Stop | `/tmp/clavain-stop-*`, `/tmp/clavain-handoff-*` |
| `sprint-scan.sh` | 539 | Sprint awareness scanner (sourced by session-start) | `/tmp/clavain-discovery-brief-*.cache` |
| `bead-agent-bind.sh` | 91 | Bind agent ID to beads on claim | None (uses Intermute API) |
| `auto-compound.sh` | 119 | Auto-trigger `/compound` on Stop after commits/insights | `/tmp/clavain-stop-*`, `/tmp/clavain-compound-last-*` |
| `auto-drift-check.sh` | 112 | Auto-trigger `/interwatch:watch` after shipped work | `/tmp/clavain-stop-*`, `/tmp/clavain-drift-last-*` |
| `auto-publish.sh` | 163 | Auto-bump patch version + sync marketplace on `git push` | `/tmp/clavain-autopub.lock` |
| `catalog-reminder.sh` | 30 | Remind to run `gen-catalog.py` after component changes | `/tmp/clavain-catalog-remind-*.lock` |
| `lib-sprint.sh` | 881 | Sprint state management (CRUD, phase advance, claim/release) | None (uses beads + future DB) |
| `lib.sh` | 262 | Shared utilities (JSON escaping, plugin discovery, inflight agent detection) | None |
| `lib-interspect.sh` | 1291 | Interspect routing override library | None (uses `.claude/interspect.db` SQLite) |
| `lib-signals.sh` | 81 | Shared signal detection for Stop hooks | None |
| `lib-verdict.sh` | 128 | Verdict aggregation for multi-agent reviews | None |

**Key Observations:**
- **9 `/tmp/` files** actively used across hooks (52 total references)
- **Sentinel pattern:** `/tmp/clavain-stop-*` (shared stop guard), `/tmp/clavain-*-last-*` (throttle sentinels)
- **Hook types:**
  - **SessionStart:** 1 (session-start.sh)
  - **Stop:** 3 (auto-compound, auto-drift-check, session-handoff)
  - **PostToolUse:** 3 (auto-publish, bead-agent-bind, catalog-reminder)
  - **Libraries:** 7 (sourced by hooks)

### Temp File Patterns

**Current temp file usage (from `ic compat status` mapping):**

| Key | Temp File Pattern | Used By | Purpose |
|-----|-------------------|---------|---------|
| `dispatch` | `/tmp/clavain-dispatch-*.json` | (future: sprint dispatch state) | Sprint dispatch manifests |
| `stop` | `/tmp/clavain-stop-*` | `auto-compound.sh`, `auto-drift-check.sh`, `session-handoff.sh` | Shared stop sentinel (one hook blocks per cycle) |
| `compound_throttle` | `/tmp/clavain-compound-last-*` | `auto-compound.sh` | 5-min throttle for auto-compound |
| `drift_throttle` | `/tmp/clavain-drift-last-*` | `auto-drift-check.sh` | 10-min throttle for drift check |
| `handoff` | `/tmp/clavain-handoff-*` | `session-handoff.sh` | Once-per-session handoff guard |
| `autopub` | `/tmp/clavain-autopub*.lock` | `auto-publish.sh` | 60s global sentinel for auto-publish |
| `catalog_remind` | `/tmp/clavain-catalog-remind-*.lock` | `catalog-reminder.sh` | Once-per-session catalog reminder |
| `discovery_brief` | `/tmp/clavain-discovery-brief-*.cache` | `sprint-scan.sh` (via lib-sprint) | Discovery brief scan cache |

**Sentinel Lifecycle:**
- **Creation:** `touch /tmp/clavain-<type>-<scope>`
- **TTL check:** `stat -c %Y` (mtime) → compute age in seconds
- **Cleanup:** `find /tmp -name 'clavain-*' -mmin +60 -delete` (stale pruning)

**TOCTOU Risk:**
- Multiple hooks can run concurrently (SessionStart + PostToolUse)
- Shared `/tmp/clavain-stop-*` sentinel prevents cascade blocks
- Race window: between `[[ -f sentinel ]]` check and `touch sentinel` write

---

## 2. Intercore Infrastructure

### Architecture

**Location:** `infra/intercore/` (CLI tool, not a plugin)  
**Database:** `.clavain/intercore.db` (auto-discovered by walking up from CWD)  
**Version:** CLI v0.1.0, schema v1  
**Driver:** `modernc.org/sqlite` (pure Go, no CGO)

**File Structure:**
```
infra/intercore/
├── cmd/ic/main.go          CLI entry point (632 lines)
├── internal/
│   ├── db/
│   │   ├── db.go          Connection, migration, health (191 lines)
│   │   ├── schema.sql     Embedded DDL (2 tables: state, sentinels)
│   │   └── disk.go        Disk space check (Linux syscall)
│   ├── state/state.go     State CRUD with JSON validation (201 lines)
│   └── sentinel/sentinel.go  Atomic throttle guards (125 lines)
├── lib-intercore.sh        Bash wrappers for hooks (44 lines)
└── test-integration.sh     End-to-end CLI tests (98 lines)
```

### SQLite Schema

**Two tables, no version table (uses `PRAGMA user_version`):**

```sql
-- state: key-value store with TTL
CREATE TABLE state (
    key         TEXT NOT NULL,
    scope_id    TEXT NOT NULL,
    payload     TEXT NOT NULL,       -- JSON validated before insert
    updated_at  INTEGER NOT NULL DEFAULT (unixepoch()),
    expires_at  INTEGER,             -- NULL = never expires
    PRIMARY KEY (key, scope_id)
);
CREATE INDEX idx_state_scope ON state(scope_id, key);
CREATE INDEX idx_state_expires ON state(expires_at) WHERE expires_at IS NOT NULL;

-- sentinels: atomic throttle guards
CREATE TABLE sentinels (
    name        TEXT NOT NULL,
    scope_id    TEXT NOT NULL,
    last_fired  INTEGER NOT NULL DEFAULT (unixepoch()),
    PRIMARY KEY (name, scope_id)
);
```

**Design Notes:**
- **State:** `REPLACE INTO` for upserts, TTL enforced at read time + manual prune
- **Sentinels:** Auto-prune in same transaction during `Check()` (deletes rows older than 7 days)
- **WAL mode:** Single connection (`SetMaxOpenConns(1)`) prevents checkpoint TOCTOU

### CLI Commands

**State operations:**
```bash
ic state set <key> <scope_id> [--ttl=<dur>]   # Reads JSON from stdin or @filepath
ic state get <key> <scope_id>                 # Prints JSON to stdout, exit 0=found, 1=not found
ic state delete <key> <scope_id>              # Returns "deleted" or "not found"
ic state list <key>                           # Lists all scope_ids for key
ic state prune                                # Deletes expired rows
```

**Sentinel operations:**
```bash
ic sentinel check <name> <scope_id> --interval=<sec>   # Exit 0=allowed, 1=throttled
ic sentinel reset <name> <scope_id>                    # Clears a sentinel
ic sentinel list                                       # Lists all sentinels
ic sentinel prune --older-than=<dur>                   # Manual prune (auto-prune runs on Check)
```

**Lifecycle:**
```bash
ic init                  # Create/migrate DB
ic health                # Check DB readable, schema current, disk space >10MB
ic version               # Print CLI version + schema version
ic compat status         # Show legacy temp file vs DB coverage
ic compat check <key>    # Check if key has data in DB
```

**Exit Codes:**
- `0` = success / allowed / found
- `1` = expected negative (throttled, not found)
- `2` = unexpected error (DB corruption, invalid JSON)
- `3` = usage error (missing arg)

**Global Flags:**
- `--db=<path>` (default: auto-discovered `.clavain/intercore.db`)
- `--timeout=<dur>` (busy timeout, default 100ms)
- `--verbose`, `--json`

### Security

**Path Traversal Protection (`validateDBPath`):**
- Must end in `.db` extension
- No `..` components
- Must resolve under CWD (prevents `/tmp/evil.db`)
- Parent directory must not be a symlink

**JSON Payload Validation:**
- Max size: 1MB
- Max nesting: 20 levels
- Max key length: 1000 chars
- Max string value: 100KB
- Max array length: 10,000 elements

**Integration test coverage:**
- Path traversal (`/tmp/evil.db`, `../../escape.db`, `noext`)
- Invalid JSON rejection
- TTL enforcement (visible before expiry, invisible after)
- Sentinel throttle (allowed → throttled → reset → allowed)
- State CRUD roundtrip

### SQLite Patterns (modernc.org/sqlite Constraints)

**Important:** `modernc.org/sqlite` does NOT support:
- `WITH claim AS (UPDATE ... RETURNING) SELECT ...` (CTE + UPDATE RETURNING)

**Workaround:** Direct `UPDATE ... RETURNING` with row counting:
```go
rows, err := tx.QueryContext(ctx, `
    UPDATE sentinels SET last_fired = unixepoch()
    WHERE name = ? AND scope_id = ?
      AND ((? = 0 AND last_fired = 0)
           OR (? > 0 AND unixepoch() - last_fired >= ?))
    RETURNING 1`, name, scopeID, interval, interval, interval)
allowed := 0
for rows.Next() { allowed++ }
return allowed == 1, nil
```

**Connection Management:**
- `SetMaxOpenConns(1)` (single writer for WAL correctness)
- PRAGMAs set explicitly after `sql.Open` (DSN `_pragma` unreliable)
- `busy_timeout` prevents immediate `SQLITE_BUSY` on contention

**Transaction Isolation:**
- State set: transaction (REPLACE INTO)
- State get: no transaction (read-only)
- Sentinel check: transaction (atomic claim + auto-prune)
- Migrate: transaction (DDL + version update, exclusive lock via temp table)

**Migration Safety:**
- Pre-migration backup (`.backup-YYYYMMDD-HHMMSS`)
- Schema version read inside transaction (prevents TOCTOU)
- `CREATE TABLE IF NOT EXISTS` (idempotent)

---

## 3. Bash Library for Hooks (`lib-intercore.sh`)

**Location:** `infra/intercore/lib-intercore.sh` (44 lines)  
**Usage:** `source "$(dirname "$0")/lib-intercore.sh"` (NO `set -e` — fail-safe by default)

**Functions:**

```bash
intercore_available()
    # Returns 0 if ic binary exists AND health check passes, 1 otherwise
    # Caches INTERCORE_BIN path for reuse
    # Logs error to stderr if DB broken

intercore_state_set <key> <scope_id> <json>
    # Writes JSON to state table
    # Returns 0 always (fail-safe — if DB unavailable, no-op)

intercore_state_get <key> <scope_id>
    # Reads JSON from state table
    # Prints JSON to stdout (empty string if not found or unavailable)

intercore_sentinel_check <name> <scope_id> <interval>
    # Atomic claim-if-eligible check
    # Returns 0 (allowed) or 1 (throttled or unavailable)
```

**Fail-Safe Design:**
- All wrappers return success (0) if `ic` binary not found or DB unavailable
- This prevents hooks from blocking Claude when intercore is not installed
- Individual hooks decide whether to degrade gracefully or hard-fail

---

## 4. Migration Patterns

### Pattern 1: Sentinel Replacement

**Before (temp file TTL check):**
```bash
SENTINEL="/tmp/clavain-stop-${SESSION_ID}"
if [[ -f "$SENTINEL" ]]; then
    exit 0
fi
touch "$SENTINEL"
```

**After (intercore sentinel):**
```bash
source "${SCRIPT_DIR}/lib-intercore.sh"
if ! intercore_sentinel_check "stop" "$SESSION_ID" 0; then
    exit 0
fi
```

**Differences:**
- **Atomicity:** Intercore uses `UPDATE ... RETURNING` (TOCTOU-safe), temp files have race window
- **Auto-prune:** Intercore auto-deletes sentinels >7 days in same transaction
- **Scope:** Temp files use session ID, intercore can use any scope (session, project, global)

**Interval Semantics:**
- `--interval=0` → fire at most once per scope (one-time sentinel)
- `--interval=300` → fire at most once per 5 minutes (throttle sentinel)

### Pattern 2: State Replacement

**Before (temp file JSON storage):**
```bash
STATE_FILE="/tmp/clavain-dispatch-${SESSION_ID}.json"
jq -nc '{"phase":"brainstorm"}' > "$STATE_FILE"
STATE=$(cat "$STATE_FILE" 2>/dev/null | jq .)
```

**After (intercore state):**
```bash
source "${SCRIPT_DIR}/lib-intercore.sh"
intercore_state_set "dispatch" "$SESSION_ID" '{"phase":"brainstorm"}'
STATE=$(intercore_state_get "dispatch" "$SESSION_ID")
```

**Differences:**
- **Validation:** Intercore validates JSON before write (size, depth, structure)
- **TTL:** Native support via `--ttl` flag (temp files need manual mtime checks)
- **Atomic:** State operations run in transactions (temp files use `mktemp` + `mv`)

### Pattern 3: TTL State

**Before (temp file + mtime check):**
```bash
THROTTLE_SENTINEL="/tmp/clavain-compound-last-${SESSION_ID}"
if [[ -f "$THROTTLE_SENTINEL" ]]; then
    MTIME=$(stat -c %Y "$THROTTLE_SENTINEL")
    NOW=$(date +%s)
    if [[ $((NOW - MTIME)) -lt 300 ]]; then
        exit 0
    fi
fi
touch "$THROTTLE_SENTINEL"
```

**After (intercore sentinel with interval):**
```bash
source "${SCRIPT_DIR}/lib-intercore.sh"
if ! intercore_sentinel_check "compound_throttle" "$SESSION_ID" 300; then
    exit 0
fi
```

**Benefits:**
- **6 lines → 4 lines** (simpler)
- **Atomic TTL check** (no TOCTOU race)
- **Auto-cleanup** (no stale `/tmp/` files)

---

## 5. Hook-by-Hook Migration Plan

### High Priority (Sentinel-Heavy)

| Hook | Temp Files | Migration |
|------|------------|-----------|
| `session-handoff.sh` | `/tmp/clavain-stop-*`, `/tmp/clavain-handoff-*` | Replace with `sentinel check stop <session> 0` + `sentinel check handoff <session> 0` |
| `auto-compound.sh` | `/tmp/clavain-stop-*`, `/tmp/clavain-compound-last-*` | Replace with `sentinel check stop <session> 0` + `sentinel check compound_throttle <session> 300` |
| `auto-drift-check.sh` | `/tmp/clavain-stop-*`, `/tmp/clavain-drift-last-*` | Replace with `sentinel check stop <session> 0` + `sentinel check drift_throttle <session> 600` |
| `auto-publish.sh` | `/tmp/clavain-autopub.lock` | Replace with `sentinel check autopub global 60` |
| `catalog-reminder.sh` | `/tmp/clavain-catalog-remind-*.lock` | Replace with `sentinel check catalog_remind <session> 0` |

### Medium Priority (State + Sentinel)

| Hook | Temp Files | Migration |
|------|------------|-----------|
| `sprint-scan.sh` | `/tmp/clavain-discovery-brief-*.cache` | Replace with `state set discovery_brief <session> <json> --ttl=1h` + `state get` |

### Low Priority (Future DB Integration)

| Hook | Current State | Future Migration |
|------|---------------|------------------|
| `lib-sprint.sh` | Uses beads (`bd state`) | Could migrate sprint state to intercore for portability (beads remains source of truth) |
| `lib-interspect.sh` | Uses `.claude/interspect.db` (separate SQLite) | Could consolidate into intercore DB |

---

## 6. Testing Strategy

### Existing Coverage

**Intercore:**
- `test-integration.sh` (19 tests: state CRUD, sentinel throttle, TTL, path validation, JSON rejection)
- Unit tests: `internal/db/db_test.go`, `internal/state/state_test.go`, `internal/sentinel/sentinel_test.go`
- Race detector: `go test -race ./...`

**Hooks:**
- No automated tests (validation is manual `bash -n` syntax checks)

### Post-Migration Testing

**1. Smoke test (per hook):**
```bash
# Before migration: capture temp file behavior
ic compat status > before.txt
# After migration: verify DB state
ic compat status > after.txt
diff before.txt after.txt
```

**2. Functional test (end-to-end):**
```bash
# Trigger hook condition (e.g., git push for auto-publish)
# Verify sentinel fired: ic sentinel list
# Verify state written: ic state get <key> <scope>
```

**3. Concurrency test:**
```bash
# Launch parallel Claude sessions
# Verify only one Stop hook blocks (shared sentinel)
# Verify throttle intervals enforced (compound 5min, drift 10min)
```

---

## 7. Rollout Strategy

### Phase 1: Sentinel Migration (Low Risk)

**Target hooks:** `session-handoff.sh`, `auto-compound.sh`, `auto-drift-check.sh`, `auto-publish.sh`, `catalog-reminder.sh`

**Steps:**
1. Add `source lib-intercore.sh` to each hook
2. Replace temp file checks with `intercore_sentinel_check` calls
3. Remove `find /tmp -name 'clavain-*' -delete` cleanup (auto-prune handles it)
4. Test: trigger each hook condition, verify `ic sentinel list` shows correct entries

**Rollback:** Revert to temp files (wrappers fail-safe if `ic` unavailable)

### Phase 2: State Migration (Medium Risk)

**Target:** `sprint-scan.sh` (discovery cache)

**Steps:**
1. Replace cache write: `jq ... > /tmp/cache` → `ic state set discovery_brief <session> <json> --ttl=1h`
2. Replace cache read: `cat /tmp/cache` → `ic state get discovery_brief <session>`
3. Test: verify cache hit/miss behavior matches temp file version

### Phase 3: Complex State (Future)

**Target:** `lib-sprint.sh` (sprint state), `lib-interspect.sh` (routing overrides)

**Approach:** Gradual adoption (keep beads/interspect DB as primary, use intercore as cache/replication)

---

## 8. Key Learnings

### Intercore Design Strengths

1. **Atomic operations:** `UPDATE ... RETURNING` for sentinel claims (no TOCTOU)
2. **Auto-cleanup:** Sentinels auto-prune in same transaction (no stale `/tmp/` files)
3. **Validation:** JSON size/depth/structure checked before storage
4. **Security:** Path traversal protection, symlink checks, CWD containment
5. **Observability:** `ic compat status` shows migration progress, `ic sentinel list` shows active guards

### Clavain Hook Conventions

1. **Fail-safe:** Hooks must not block Claude if dependencies unavailable (jq, bd, ic)
2. **Shared sentinels:** `/tmp/clavain-stop-*` prevents cascade blocks across Stop hooks
3. **Throttle intervals:** 5min (compound), 10min (drift check), 60s (autopub), 0 (one-time)
4. **Cleanup strategy:** `find /tmp -name 'clavain-*' -mmin +60 -delete` (stale pruning)

### Migration Trade-offs

| Aspect | Temp Files | Intercore DB |
|--------|------------|--------------|
| **Atomicity** | TOCTOU race window | Atomic (transaction + RETURNING) |
| **Cleanup** | Manual `find` (per-hook) | Auto-prune (in sentinel check) |
| **Visibility** | `ls /tmp/clavain-*` | `ic sentinel list`, `ic state list` |
| **Portability** | Works everywhere | Requires `ic` binary + `.clavain/intercore.db` |
| **Failure mode** | Stale files accumulate | Graceful degradation (wrappers fail-safe) |

---

## 9. Recommendations

### Immediate Actions

1. **Migrate sentinels first** (5 hooks, low risk, high impact — removes 9 temp file patterns)
2. **Add `ic init` to session-start hook** (create DB on first session if missing)
3. **Update AGENTS.md** (document `lib-intercore.sh` wrappers, sentinel semantics)

### Future Enhancements

1. **Consolidate sprint state** (lib-sprint.sh could use intercore for session-scoped state, beads for persistent artifacts)
2. **Unified observability** (`/clavain:status` command showing sentinels + state from `ic compat status`)
3. **Cross-session coordination** (interlock could use intercore for file reservation state)

### Guardrails

1. **Version check:** Hooks should verify `ic version` before first use (fail-safe if schema mismatch)
2. **Health monitoring:** `ic health` in session-start (log warning if DB unhealthy)
3. **Backward compat:** Keep temp file fallback for 2-3 releases (remove after confirmed stable)

---

## Appendix A: File Sizes

**Hooks (20 files, 4.4KB total):**
- Largest: `lib-interspect.sh` (51KB), `lib-sprint.sh` (33KB), `sprint-scan.sh` (21KB)
- Smallest: `dotfiles-sync.sh` (723 bytes), `catalog-reminder.sh` (902 bytes)

**Intercore (8 Go files, 1,449 lines):**
- `cmd/ic/main.go` (632 lines) — CLI dispatch
- `internal/state/state.go` (201 lines) — State CRUD + validation
- `internal/db/db.go` (191 lines) — Connection + migration
- `internal/sentinel/sentinel.go` (125 lines) — Sentinel guards

**Tests:**
- Integration: `test-integration.sh` (98 lines, 19 tests)
- Unit: 3 `*_test.go` files (not counted, minimal coverage)

---

## Appendix B: Temp File Audit

**9 temp file patterns, 52 total references across 6 hooks:**

| Pattern | Hooks | Count | Purpose |
|---------|-------|-------|---------|
| `/tmp/clavain-stop-*` | 3 | 12 | Shared stop sentinel |
| `/tmp/clavain-compound-last-*` | 2 | 12 | Compound throttle |
| `/tmp/clavain-drift-last-*` | 2 | 12 | Drift check throttle |
| `/tmp/clavain-handoff-*` | 1 | 4 | Handoff one-time |
| `/tmp/clavain-autopub.lock` | 1 | 4 | Autopub global sentinel |
| `/tmp/clavain-catalog-remind-*.lock` | 1 | 4 | Catalog reminder |
| `/tmp/clavain-discovery-brief-*.cache` | 1 | 1 | Discovery cache |

**Cleanup frequency:** `find ... -mmin +60 -delete` (3 hooks have this pattern)

---

## Appendix C: Intercore CLI Examples

**Sentinel (throttle check):**
```bash
# First call: allowed (exit 0, prints "allowed")
ic sentinel check compound_throttle sess-abc123 --interval=300

# Second call within 5 min: throttled (exit 1, prints "throttled")
ic sentinel check compound_throttle sess-abc123 --interval=300

# Reset sentinel
ic sentinel reset compound_throttle sess-abc123

# Third call: allowed again
ic sentinel check compound_throttle sess-abc123 --interval=300
```

**State (JSON storage):**
```bash
# Write state with 1h TTL
echo '{"phase":"brainstorm","timestamp":1708185600}' | \
    ic state set dispatch sess-abc123 --ttl=1h

# Read state (exit 0 if found, prints JSON)
ic state get dispatch sess-abc123
# Output: {"phase":"brainstorm","timestamp":1708185600}

# List all scope_ids for key
ic state list dispatch
# Output:
# sess-abc123
# sess-def456

# Delete state
ic state delete dispatch sess-abc123
# Output: deleted

# Read deleted state (exit 1, no output)
ic state get dispatch sess-abc123
```

**Compat status:**
```bash
ic compat status
# Output:
# KEY                  LEGACY  DB
# dispatch             no      yes
# stop                 yes     no
# compound_throttle    yes     no
# ...
```
