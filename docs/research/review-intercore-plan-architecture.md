# Architecture Review: intercore Implementation Plan

**Reviewer:** flux-drive architecture reviewer
**Date:** 2026-02-17
**Subject:** `/root/projects/Interverse/docs/plans/2026-02-17-intercore-state-database.md`
**PRD:** `/root/projects/Interverse/docs/prds/2026-02-17-intercore-state-database.md` (v2)

---

## Executive Summary

The intercore implementation plan defines a well-scoped Go CLI (`ic`) for SQLite-backed state operations targeting Clavain hook infrastructure. The architecture is **structurally sound** with clear module boundaries, appropriate dependency direction, and a conservative migration strategy. However, the plan exhibits **premature batching complexity** that creates false dependencies, obscures the minimal viable integration path, and invites rework. The relationship to intermute is correctly scoped (no overlap), but the batch structure contradicts the stated feature independence.

**Key Findings:**

1. **Boundaries & coupling:** Clean separation between `cmd/ic`, `internal/db`, `internal/state`, `internal/sentinel`. No boundary violations. Dependency direction is correct (cmd → internal packages, no reverse deps).

2. **Batch structure creates unnecessary coupling:** Batches 2 (sentinels) and 3 (state) are declared independent but artificially sequenced. Batch 4 (bash library) depends on both, forcing serial execution despite no technical dependency between sentinels and state. This structure optimizes for "ship highest-value feature first" at the cost of parallel work and natural integration checkpoints.

3. **Schema design is appropriate:** Composite primary keys `(key, scope_id)` and `(name, scope_id)` correctly model the scoping intent. Indexes cover expected query patterns. TTL enforcement in queries (not triggers) is the right tradeoff for a CLI tool. No schema/domain leakage from intermute.

4. **intermute relationship is correct:** Zero overlap. intermute handles agent messaging and domain entities (specs, epics, stories) with composite `(project, id)` keys. intercore handles ephemeral hook state with `(key, scope_id)` keys. No shared tables, no shared semantics. Both use SQLite + WAL, but for entirely different purposes.

5. **Rework risk from read-fallback migration:** Batch 5 introduces compatibility shims (`ic compat status`, `ic compat check`) that assume consumers will use read-fallback during migration. But no consumer integration is planned until Batch 5, meaning Batches 1-4 ship code that has never been tested in the real consumption path. High risk of discovering edge cases (path resolution, JSON escaping, concurrency) only after all features are complete.

6. **YAGNI violations:** The bash library (`lib-intercore.sh`) includes `intercore_sentinel_check_many` for batching multiple sentinel checks in a single invocation — but the CLI has no such batch command. The library invents a multi-check protocol (`name:scope:interval` tuples) that doesn't exist in the underlying CLI. Either the CLI needs a batch sentinel endpoint (scope creep) or the library function is speculative complexity.

---

## 1. Boundaries & Coupling

### Module Structure

```
cmd/ic/            # CLI entry point, subcommand routing, flag parsing
internal/db/       # SQLite open, migrate, health, schema embed
internal/state/    # State CRUD (set/get/list/prune)
internal/sentinel/ # Sentinel check/reset/list/prune
```

**Assessment:** Boundaries are clean. `cmd/ic` depends on `internal/*`, but internal packages do not depend on each other or on `cmd`. State and sentinel logic are fully isolated — they share only the `*sql.DB` handle passed from `cmd/ic`.

**Dependency direction:** Correct. CLI layer depends on domain logic (state, sentinel) and infrastructure (db). Infrastructure depends on nothing (pure Go stdlib + `modernc.org/sqlite`). No circular dependencies, no leaky abstractions.

**API surface:** The plan correctly specifies that v1 is CLI-only with no public Go API. This avoids premature commitment to Go package stability while the CLI semantics are still being validated with real usage.

**Package coupling:** State and sentinel packages are **completely independent**. They share:
- Schema file (`internal/db/schema.sql`) — but different tables
- Transaction pattern (`BEGIN IMMEDIATE`) — but no shared code
- DB handle type (`*sql.DB`) — but passed from outside, not owned

This independence is **not reflected in the batch structure**, which forces Batch 2 (sentinels) to complete before Batch 3 (state) begins. The plan justifies this as "ship highest-value feature first," but that's a **product sequencing decision masquerading as a technical dependency**. Batches 2 and 3 could be developed in parallel or in reverse order with zero technical impact.

**Recommended change:** Restructure batches to reflect true dependencies:
- **Batch 1:** Scaffold + schema (F1) — foundation for everything
- **Batch 2a:** Sentinel operations (F3) — independent track
- **Batch 2b:** State operations (F2) — independent track (can run in parallel with 2a)
- **Batch 3:** Bash library (F5) — depends on completion of 2a AND 2b
- **Batch 4:** Compatibility shims (F7) — depends on Batch 3

This reveals the true parallelization opportunity and removes the false "sentinels first" sequencing.

---

## 2. Pattern Analysis

### Schema Design

**State table:**
```sql
CREATE TABLE state (
    key         TEXT NOT NULL,
    scope_id    TEXT NOT NULL,
    payload     TEXT NOT NULL,
    updated_at  INTEGER NOT NULL DEFAULT (unixepoch()),
    expires_at  INTEGER,
    PRIMARY KEY (key, scope_id)
);
```

**Assessment:** Composite PK `(key, scope_id)` correctly models "each key can have multiple scopes, each scope has one payload per key." The `INSERT OR REPLACE` upsert pattern (Task 3.1) is appropriate for this schema. TTL via `expires_at` is simple and query-enforceable.

**Sentinel table:**
```sql
CREATE TABLE sentinels (
    name        TEXT NOT NULL,
    scope_id    TEXT NOT NULL,
    last_fired  INTEGER NOT NULL DEFAULT (unixepoch()),
    PRIMARY KEY (name, scope_id)
);
```

**Assessment:** Same composite PK pattern. `last_fired` as INTEGER (Unix epoch) is correct. The sentinel CTE+RETURNING query (Task 2.1) correctly handles atomic claim-if-eligible:

```sql
WITH claim AS (
    UPDATE sentinels
    SET last_fired = unixepoch()
    WHERE name = ? AND scope_id = ?
      AND (? = 0 AND last_fired = 0
           OR ? > 0 AND unixepoch() - last_fired >= ?)
    RETURNING 1
)
SELECT COUNT(*) FROM claim
```

This pattern is **correct** for avoiding TOCTOU races. The plan's note that `changes()` is unsafe with pooled connections is accurate — `changes()` is connection-local state, while RETURNING is result-set-based.

**Index coverage:**
- `idx_state_scope ON state(scope_id, key)` — supports "list all keys for scope"
- `idx_state_expires ON state(expires_at)` — supports prune, partial index (WHERE expires_at IS NOT NULL) reduces size
- Sentinel table has no indexes beyond the PK — reasonable for small tables (plan assumes <1000 sentinels)

**TTL enforcement:** All state queries include `AND (expires_at IS NULL OR expires_at > unixepoch())`. This is the **correct choice** for a CLI tool that opens/closes the DB on every invocation. Trigger-based deletion would require a background process or scheduled task, adding deployment complexity for no user-visible benefit (expired rows are invisible anyway).

**Comparison to intermute schema:**

| Dimension | intermute | intercore |
|-----------|-----------|-----------|
| **Purpose** | Agent messaging, domain entities | Ephemeral hook state, throttle guards |
| **Scoping key** | `(project, id)` | `(key, scope_id)` |
| **Tables** | 14 (events, messages, inbox_index, thread_index, agents, specs, epics, stories, tasks, insights, sessions, cujs, cuj_feature_links, file_reservations) | 2 (state, sentinels) |
| **Domain** | Multi-agent coordination, product artifacts | Hook infrastructure state |
| **Overlap** | **None** — completely different semantics | |

**Finding:** No schema collision. intermute's `(project, id)` scoping is for multi-tenant agent coordination. intercore's `(key, scope_id)` scoping is for hook-local state (scope_id = session ID or bead ID). They could coexist in the same DB without conflict, but there's no reason to merge them — their lifecycles and access patterns are unrelated.

### Anti-Pattern Detection

**1. God module risk in `lib-intercore.sh`:**

The bash library (Task 4.1) includes:
- `intercore_available()` — checks binary + health
- `intercore_state_set()` — thin wrapper
- `intercore_state_get()` — thin wrapper
- `intercore_sentinel_check()` — thin wrapper
- `intercore_sentinel_check_many()` — **invents a batch protocol not present in CLI**

The `check_many` function parses `name:scope:interval` tuples and loops over them, calling `ic sentinel check` serially. This is **premature optimization** — it doesn't reduce subprocess overhead (still one `ic` invocation per sentinel), and it introduces a parsing layer that the CLI doesn't understand.

**Recommendation:** Remove `intercore_sentinel_check_many` from the initial library. If batching proves necessary after real usage, add a CLI subcommand `ic sentinel check-batch` that accepts newline-delimited `name scope interval` triples and processes them in a single transaction. The library can then wrap that.

**2. Fail-safe vs fail-loud distinction:**

The library correctly distinguishes:
- **DB unavailable** (binary missing, no DB file): fail-safe, return 0
- **DB broken** (schema mismatch, corruption): fail-loud, return 1, log to stderr

This is the **right pattern** for optional infrastructure. However, the implementation has a subtle bug:

```bash
intercore_state_set() {
    local key="$1" scope_id="$2" json="$3"
    if ! intercore_available; then return 0; fi  # fail-safe if unavailable
    echo "$json" | "$_INTERCORE_BIN" state set "$key" "$scope_id" 2>/dev/null
    return 0  # fail-safe on write errors
}
```

The `2>/dev/null` suppresses **all** stderr, including the "DB broken" error that `intercore_available` is supposed to emit. This means the fail-safe/fail-loud distinction is lost on write operations.

**Fix:** Only suppress stderr for **expected negative outcomes** (like "not found" on get), not for structural errors:

```bash
intercore_state_set() {
    local key="$1" scope_id="$2" json="$3"
    if ! intercore_available; then return 0; fi
    echo "$json" | "$_INTERCORE_BIN" state set "$key" "$scope_id" || return 0
}
```

Let structural errors (invalid JSON, DB corruption) propagate to stderr. Swallow only the return code (0 vs 2) to preserve fail-safe behavior.

**3. Schema version check on every command:**

The plan specifies (Task 1.3):
> Schema version check on every command (except `init`): if user_version > max supported, exit 2 with upgrade message

This is **correct** for preventing data corruption from version skew. However, it's implemented at the wrong layer. The plan places it in `cmd/ic/main.go` (CLI routing layer), which means every subcommand duplicates the check.

**Recommendation:** Move schema version check into `internal/db.Open()`. Return a sentinel error `ErrSchemaVersionTooNew` that the CLI translates into exit code 2 + upgrade message. This centralizes the check and ensures it runs even if a future refactor bypasses the CLI layer.

---

## 3. Simplicity & YAGNI

### Premature Abstraction: Batch 5 Compatibility Shims

The plan defers **all consumer integration** to Batch 5 (Tasks 5.1-5.3), after the CLI, library, and integration tests are complete. This creates a **validation gap**:

- Batches 1-4 build the full feature set (init, health, state, sentinels, bash library, integration test)
- Batch 5 discovers edge cases from real consumers (interline, Clavain hooks) and realizes the library wrappers don't handle:
  - Path resolution ambiguity (hooks run from various CWDs, library assumes `ic` is on PATH)
  - JSON escaping differences between `echo "$json" | ic` and `ic state set @file`
  - Concurrency between hook invocations during rapid turn cycles

**Result:** Rework in Batches 1-4 to fix assumptions baked into the schema, CLI semantics, or library wrappers.

**Alternative structure (tighter validation loop):**

1. **Batch 1:** Scaffold + schema + CLI framework (F1)
2. **Batch 2:** Sentinel operations (F3) — CLI + Go tests
3. **Batch 2.5:** **Migrate one real consumer** (e.g., auto-compound.sh stop sentinel) — validates path resolution, fail-safe behavior, and concurrency
4. **Batch 3:** State operations (F2) — CLI + Go tests
5. **Batch 3.5:** **Migrate one real consumer** (e.g., interline reading dispatch state) — validates JSON roundtrip, TTL enforcement
6. **Batch 4:** Bash library (F5) — wraps validated patterns from 2.5 and 3.5
7. **Batch 5:** Compatibility shims + migration docs (F7)

This structure **interleaves validation with implementation**, catching integration bugs when only one feature is live rather than after all features are complete.

### Unnecessary Complexity: Integration Test Script

Task 4.2 creates `test-integration.sh` with:
- Build `ic` to `/tmp/ic-test`
- Export `PATH="/tmp:$PATH"`
- Create test DB via `INTERCORE_DB` env var
- Run state/sentinel/TTL tests
- Clean up temp files

**Problem:** This duplicates coverage already provided by Go unit tests (Tasks 2.1, 3.1) and doesn't test the **real integration surface** — the bash library sourced by hooks.

**What's missing:** A test that:
1. Sources `lib-intercore.sh` as hooks do
2. Calls `intercore_state_set`, `intercore_state_get`, `intercore_sentinel_check` as hooks do
3. Validates fail-safe behavior when `ic` is not on PATH
4. Validates fail-loud behavior when DB is corrupted

**Recommendation:** Replace Task 4.2 integration test with a **hook simulation test**:
```bash
#!/usr/bin/env bash
# test-hook-integration.sh
set -euo pipefail

cd "$(dirname "$0")"
go build -o /tmp/ic ./cmd/ic
export PATH="/tmp:$PATH"
export INTERCORE_DB="/tmp/test-$$.db"

ic init

# Source the library as hooks do
source ./lib-intercore.sh

# Test state operations via library
intercore_state_set dispatch sess1 '{"phase":"executing"}'
result=$(intercore_state_get dispatch sess1)
[[ "$result" == '{"phase":"executing"}' ]] || exit 1

# Test sentinel via library
intercore_sentinel_check stop sess1 0 || exit 1
intercore_sentinel_check stop sess1 0 && exit 1 || true  # Should be throttled

# Test fail-safe (binary not on PATH)
export PATH="/usr/bin:/bin"
intercore_state_get dispatch sess1 || true  # Should return empty, not error

# Cleanup
rm -f /tmp/ic "$INTERCORE_DB" "${INTERCORE_DB}-wal" "${INTERCORE_DB}-shm"
echo "Hook integration tests passed."
```

This tests the **actual consumption path** rather than reimplementing CLI tests in bash.

### Speculative Features: `intercore_sentinel_check_many`

As noted in Section 2, the library includes a batch sentinel check that doesn't exist in the CLI. The justification is "reduces subprocess overhead," but:
- The library implementation still spawns one `ic` process per sentinel (no actual batching)
- The `:` delimiter format (`name:scope:interval`) is bash-specific and not reusable by other consumers
- No consumer in the plan uses this function — it's pure speculation

**Recommendation:** Delete `intercore_sentinel_check_many` from the initial library. If a consumer needs to check multiple sentinels, they can loop:

```bash
for name in stop drift compound; do
    if ! intercore_sentinel_check "$name" "$SESSION_ID" 300; then
        continue  # Throttled, skip
    fi
    # Do work
done
```

If this pattern proves expensive (profiling shows subprocess overhead is significant), **then** add a CLI batch command and library wrapper. Premature optimization here adds code that will never be tested until a consumer adopts it.

---

## 4. Schema Design Decisions

### Composite Primary Keys vs Separate ID Column

The plan uses composite PKs `(key, scope_id)` and `(name, scope_id)` rather than an auto-increment `id` column + unique constraint. This is **correct** for the access patterns:

- State lookups are always by `(key, scope_id)` — no use case for "get row by id"
- Sentinel checks are always by `(name, scope_id)` — no use case for "get sentinel by id"

Composite PKs enforce uniqueness at the schema level and avoid the need for `SELECT id WHERE key=? AND scope_id=?` before every upsert. The `INSERT OR REPLACE` pattern (state) and `INSERT OR IGNORE` + CTE+UPDATE (sentinels) both work naturally with composite PKs.

**Comparison to alternatives:**

| Pattern | Pros | Cons |
|---------|------|------|
| Composite PK (plan) | Enforces uniqueness, natural upsert, no extra index | Requires full key on every query |
| Auto-increment ID + unique(key,scope) | Single-column joins, stable row identity | Requires lookup before upsert, extra index |

For a **CLI tool with no cross-table joins**, composite PKs are the simpler choice.

### INTEGER Timestamps vs TEXT RFC3339

The plan uses `INTEGER NOT NULL DEFAULT (unixepoch())` for all timestamps. This is **correct** for:
- Arithmetic (TTL checks, interval math) — `unixepoch() - last_fired >= ?` is a simple integer comparison
- Storage efficiency — 8 bytes vs 25+ bytes for RFC3339 strings
- Index efficiency — integer comparison is faster than string comparison

intermute uses TEXT timestamps (`created_at TEXT NOT NULL`) for RFC3339Nano serialization. This is a **different tradeoff**:
- intermute exposes timestamps in JSON API responses — RFC3339 is human-readable and portable
- intercore timestamps are **internal only** (never exposed to consumers except via prune count) — no readability requirement

**Finding:** No consistency issue. The two projects optimize for different constraints (API portability vs CLI efficiency).

### TTL Enforcement: Query-Time vs Trigger-Based

The plan enforces TTL in queries: `WHERE (expires_at IS NULL OR expires_at > unixepoch())`. Expired rows remain in the DB until manually pruned via `ic state prune`.

**Tradeoffs:**

| Approach | Pros | Cons |
|----------|------|------|
| Query-time (plan) | No background process, expired rows invisible to reads | Rows consume space until pruned |
| DELETE trigger | Automatic cleanup | Requires cron/systemd timer, adds deployment complexity |
| DELETE on write | Cleanup piggybacked on writes | Unpredictable write latency |

For a **CLI tool invoked from hooks with <50ms budget**, query-time enforcement is correct. The auto-prune goroutine in Task 2.2 (delete sentinels older than 7 days after every `sentinel check`) provides cleanup without blocking the foreground operation.

**Recommendation:** Extend auto-prune to state table as well:
```go
// In internal/sentinel/sentinel.go Check() method, after commit:
go func() {
    ctx, cancel := context.WithTimeout(context.Background(), 1*time.Second)
    defer cancel()
    _, _ = s.db.ExecContext(ctx, "DELETE FROM sentinels WHERE unixepoch() - last_fired > 604800")
    _, _ = s.db.ExecContext(ctx, "DELETE FROM state WHERE expires_at IS NOT NULL AND expires_at <= unixepoch()")
}()
```

This centralizes cleanup in one place and ensures both tables are pruned on the most frequent operation (sentinel checks run every hook invocation).

---

## 5. Relationship to intermute

### Domain Separation

| Concern | intermute | intercore |
|---------|-----------|-----------|
| **Purpose** | Multi-agent messaging, coordination, product domain (specs/epics/stories) | Ephemeral hook state, throttle guards |
| **Lifecycle** | Persistent across sessions | Scoped to session or bead, short TTL |
| **Access pattern** | REST API, WebSocket, Go SDK | CLI from bash hooks |
| **Schema** | 14 tables (events, messages, domain entities, file reservations) | 2 tables (state, sentinels) |
| **Scoping** | `(project, id)` for multi-tenancy | `(key, scope_id)` for hook-local state |

**Finding:** **Zero overlap**. intermute is a service for agent-to-agent communication. intercore is infrastructure for hook-to-hook state. They use SQLite for different reasons:
- intermute: Embedded DB for single-process service with no external DB dependency
- intercore: File-backed KV store for bash hooks with atomic operations

### Could They Be Merged?

**Technical feasibility:** Yes. Add `state` and `sentinels` tables to intermute schema, expose `/api/state` and `/api/sentinels` endpoints, update Clavain hooks to call intermute HTTP API instead of shelling out to `ic`.

**Architectural correctness:** **No**. This creates a **dependency inversion**:
- Clavain hooks are foundational infrastructure (session start, stop, post-tool-use)
- intermute is an optional service (only runs for multi-agent workflows, may not be available in single-agent setups)
- Making hooks depend on intermute **elevates intermute from optional service to required infrastructure**

The plan correctly places intercore in `infra/` (foundational) rather than `services/` (optional). This dependency direction is **load-bearing** for the plugin ecosystem:

```
Dependency layers (bottom to top):
1. infra/intercore     — foundational state for hooks
2. hub/clavain         — hooks depend on intercore
3. services/intermute  — optional service for multi-agent coordination
4. plugins/interlock   — depends on intermute (MCP, file reservations)
```

If intercore were merged into intermute, layer 2 would depend on layer 3, creating a circular dependency (hooks → service → hooks).

**Recommendation:** Keep them separate. If future work reveals shared patterns (e.g., both need WAL recovery helpers), extract to a shared `internal/sqlite` library. But merging the domain models would violate layer separation.

---

## 6. Batch Structure Creates False Dependencies

### Current Batch Order (from Plan)

1. **Batch 1:** Scaffold + schema + CLI framework (F1)
2. **Batch 2:** Sentinel operations (F3) — depends on Batch 1
3. **Batch 3:** State operations (F2) — depends on Batch 2 (per plan: "build incrementally")
4. **Batch 4:** Bash library (F5) — depends on Batch 3
5. **Batch 5:** Read-fallback migration (F7) — depends on Batch 4

### True Dependency Graph

```
Batch 1 (F1: Scaffold)
  ├── Batch 2 (F3: Sentinels) — independent
  └── Batch 3 (F2: State)     — independent
        ↓
      Batch 4 (F5: Bash library) — depends on BOTH 2 and 3
        ↓
      Batch 5 (F7: Migration) — depends on 4
```

**Key insight:** Batches 2 and 3 have **no dependency** on each other. They can be implemented in parallel, in reverse order, or by different people. The plan sequences them only to "ship highest-value feature (sentinels) first," but this is a **product decision**, not a technical constraint.

**Impact of artificial sequencing:**

1. **Delays state operations unnecessarily:** If Batch 2 (sentinels) encounters unexpected complexity (e.g., CTE+RETURNING doesn't work as expected in modernc.org/sqlite, race condition in concurrent checks), Batch 3 (state) is blocked despite having no technical dependency on sentinels.

2. **Delays bash library unnecessarily:** Batch 4 is blocked on both 2 and 3, even though the library functions are independent (`intercore_state_*` does not call `intercore_sentinel_*`). The library could ship piecemeal:
   - After Batch 2: ship `intercore_sentinel_check` wrapper
   - After Batch 3: ship `intercore_state_set/get` wrappers

3. **Obscures parallelization opportunity:** The plan assumes a single implementer working serially. If two people are available, they could work Batches 2 and 3 in parallel, reducing total calendar time by ~40%.

**Recommended reordering:**

```
Batch 1: Scaffold + Schema (F1)
  ├─→ Batch 2a: Sentinel operations (F3)
  │     └─→ Batch 2a.1: Migrate one sentinel consumer (auto-compound.sh)
  │
  └─→ Batch 2b: State operations (F2)
        └─→ Batch 2b.1: Migrate one state consumer (interline dispatch)

Batch 3: Bash library (F5) — after 2a AND 2b complete
Batch 4: Compatibility shims + migration docs (F7)
```

This structure:
- Removes false sequencing between sentinels and state
- Interleaves validation (2a.1, 2b.1) with implementation
- Allows parallel work on 2a and 2b
- Defers generalization (bash library) until specific patterns are validated

---

## 7. Migration Strategy: Read-Fallback Correctness

The plan specifies **read-fallback** (not dual-write) for migrating from temp files to intercore. This is **architecturally correct**:

**Dual-write problems:**
- No atomic cross-backend commit (if DB write succeeds but file write fails, state diverges)
- No rollback strategy (if file write succeeds but DB write fails, can't undo file change)
- Conflict resolution complexity (if both backends have data, which is authoritative?)

**Read-fallback advantages:**
- Single source of truth (DB) from day one
- Graceful degradation (legacy consumers see stale data but don't break)
- Clear migration completion signal (when fallback code path stops executing, remove it)

**Implementation plan (Phase 1, from PRD):**
- `ic state set` writes to DB only
- `ic state get` reads from DB only
- Consumers (interline, hooks) try `ic state get`, fall back to legacy file if empty/unavailable

**Correctness issue:** The plan doesn't specify **how long** consumers must maintain fallback logic. If a consumer removes fallback too early (e.g., after observing 10 successful DB reads), and then `ic` becomes unavailable (binary deleted, DB corrupted), the consumer **hard-fails** instead of gracefully degrading to legacy behavior.

**Recommendation:** Add an **explicit fallback deprecation timeline** to the migration docs (Task 5.2):

```markdown
## Fallback Removal Timeline

1. **Week 0-4:** All consumers use read-fallback (try DB, fall back to file)
2. **Week 5:** Run `ic compat status` — verify all keys have DB data
3. **Week 6:** Remove fallback logic from **one** consumer (e.g., interline)
4. **Week 7-8:** Monitor for fallback invocations in remaining consumers
5. **Week 9:** If zero fallback invocations observed, remove from all consumers
6. **Week 10:** Delete legacy temp file writes from hooks

If `ic` becomes unavailable after Week 9, **fail-loud** — hooks should exit with error rather than silently degrading.
```

This gives a concrete decision gate rather than leaving "when to remove fallback" ambiguous.

---

## 8. Package Coupling Analysis

### Internal Package Dependencies

```
cmd/ic/
  ├── internal/db          (Open, Migrate, Health)
  ├── internal/state       (Set, Get, List, Prune)
  └── internal/sentinel    (Check, Reset, List, Prune)

internal/db/
  └── (no internal deps)

internal/state/
  └── internal/db (only *sql.DB handle, not db package types)

internal/sentinel/
  └── internal/db (only *sql.DB handle, not db package types)
```

**Assessment:** Clean unidirectional dependency graph. No cycles, no leaky abstractions.

**Potential coupling issue:** Both `state` and `sentinel` packages receive `*sql.DB` from `cmd/ic`, but they **don't validate** that the DB has been migrated. If `cmd/ic` mistakenly passes an uninitialized DB, `state.Set()` will fail with cryptic "no such table" errors.

**Recommendation:** Add a `db.Validate()` method that checks `PRAGMA user_version` and returns `ErrNotMigrated` if zero. Call it in `cmd/ic` before passing the DB to state/sentinel stores:

```go
// In cmd/ic/main.go
db, err := dbpkg.Open(dbPath, timeout)
if err != nil { ... }
if err := db.Validate(); err != nil {
    if errors.Is(err, dbpkg.ErrNotMigrated) {
        fmt.Fprintf(os.Stderr, "ic: database not initialized — run 'ic init'\n")
        os.Exit(2)
    }
    // other error handling
}
```

This centralizes the migration check (currently scattered across subcommands per Task 1.3) and provides clearer error messages.

---

## 9. Recommendations Summary

### Critical (Fix Before Implementation)

1. **Restructure batches to reflect true dependencies:**
   - Batches 2 (sentinels) and 3 (state) are independent — allow parallel work
   - Interleave consumer migration (2a.1, 2b.1) with feature implementation to validate assumptions early

2. **Remove `intercore_sentinel_check_many` from bash library:**
   - No CLI batch endpoint exists
   - Function doesn't reduce subprocess overhead (still one `ic` per sentinel)
   - Pure speculation with no consumer

3. **Fix fail-safe/fail-loud stderr suppression in `lib-intercore.sh`:**
   - `2>/dev/null` on `ic state set` suppresses both expected errors (invalid JSON) and structural errors (DB corruption)
   - Only suppress return codes, let structural errors propagate to stderr

### High Priority (Improves Validation)

4. **Replace integration test (Task 4.2) with hook simulation test:**
   - Current test duplicates Go unit test coverage
   - New test validates real consumption path: sourcing `lib-intercore.sh`, calling wrappers, fail-safe behavior

5. **Add explicit fallback deprecation timeline to migration docs:**
   - Current plan leaves "when to remove fallback" ambiguous
   - Concrete 10-week timeline with decision gates prevents premature removal

6. **Centralize schema version check in `internal/db.Open()`:**
   - Current plan duplicates check in every subcommand
   - Moving to `Open()` ensures all DB access paths are protected

### Medium Priority (Reduces Complexity)

7. **Extend auto-prune to state table:**
   - Current plan only prunes sentinels (Task 2.2)
   - State table also needs expired row cleanup

8. **Add `db.Validate()` method for migration check:**
   - Replaces scattered "is DB migrated?" checks in CLI subcommands
   - Provides clearer error messages ("run `ic init`" vs "no such table")

### Low Priority (Nice-to-Have)

9. **Consider `--db` flag default behavior:**
   - Current plan: walk up from `$PWD` looking for `.clavain/intercore.db`
   - Alternative: require explicit `--db` or `INTERCORE_DB` env var
   - Tradeoff: convenience vs explicitness (hooks must always pass full path)

10. **Add `ic state delete <key> <scope_id>` command:**
    - Current plan only has prune (bulk delete expired rows)
    - No way to delete a specific key without manually editing DB
    - Use case: cleanup after testing, manual state reset

---

## 10. Verdict

**Architecture: APPROVED with conditions**

The intercore implementation plan defines a **clean, well-bounded architecture** with correct dependency direction, appropriate schema design, and no overlap with intermute. The module structure (`cmd/ic`, `internal/db`, `internal/state`, `internal/sentinel`) correctly separates concerns, and the read-fallback migration strategy is sound.

**However, the batch structure creates unnecessary coupling** by forcing serial execution of independent features (sentinels and state). This optimizes for "ship highest-value first" at the cost of:
- Parallel work opportunities (if multiple implementers available)
- Early validation of integration assumptions (deferred to Batch 5)
- Natural checkpoints (consumer migration after each feature, not after all features)

**The plan is implementable as-is**, but restructuring batches per Recommendation #1 would reduce rework risk and calendar time.

**YAGNI violations** (`intercore_sentinel_check_many`, premature integration test) are **non-blocking** — they add complexity but don't compromise correctness. Remove them for cleaner initial implementation.

**Critical fixes** (stderr suppression in bash library, batch reordering) should be addressed **before Batch 2** to avoid baking incorrect assumptions into the code.

---

## Appendix: Comparison to Existing Patterns

### Temp File Patterns in Clavain Hooks (Current State)

| Hook | Temp File Pattern | Purpose | intercore Replacement |
|------|------------------|---------|---------------------|
| auto-compound.sh | `/tmp/clavain-stop-${SESSION_ID}` | Stop sentinel | `ic sentinel check stop $SESSION_ID 0` |
| auto-compound.sh | `/tmp/clavain-compound-last-${SESSION_ID}` | 5-min throttle | `ic sentinel check compound $SESSION_ID 300` |
| auto-drift-check.sh | `/tmp/clavain-drift-last-${SESSION_ID}` | Throttle | `ic sentinel check drift $SESSION_ID <interval>` |
| auto-publish.sh | `/tmp/clavain-autopub*.lock` | Once-per-push guard | `ic sentinel check autopub $COMMIT_HASH 0` |
| catalog-reminder.sh | `/tmp/clavain-catalog-remind-*.lock` | Once-per-change guard | `ic sentinel check catalog $SESSION_ID 0` |
| session-handoff.sh | `/tmp/clavain-handoff-*` | Once-per-session guard | `ic sentinel check handoff $SESSION_ID 0` |
| (dispatch state) | `/tmp/clavain-dispatch-*.json` | Dispatch phase tracking | `ic state set dispatch $SESSION_ID '{"phase":"..."}'` |

**Assessment:** All patterns fit cleanly into intercore's two-table model. No edge cases requiring custom tables or logic.

**Migration complexity:** Low. Each temp file operation maps 1:1 to an `ic` command. The bash library wrappers (`intercore_sentinel_check`, `intercore_state_set/get`) are drop-in replacements with fail-safe behavior.

**Concurrency safety:** Current touch-file pattern has TOCTOU races (check + touch are separate syscalls). intercore CTE+RETURNING eliminates these.

---

**End of Review**
