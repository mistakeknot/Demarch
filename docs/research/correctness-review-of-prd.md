# Correctness Review: intercore State Database PRD

**Reviewer:** Julik (fd-correctness)
**Document:** `/root/projects/Interverse/docs/prds/2026-02-17-intercore-state-database.md`
**Bead:** iv-ieh7
**Date:** 2026-02-17

## Executive Summary

The PRD proposes a SQLite-backed Go CLI (`ic`) to replace scattered temp files with atomic state operations. The sentinel atomic claim pattern, run tracking, and dual-write mode all have **critical correctness gaps** that will cause lost updates, phantom claims, stale reads, and silent corruption under concurrent load.

**Priority distribution:**
- **P0 (will corrupt data):** 3 issues
- **P1 (will cause 3AM pages):** 4 issues
- **P2 (undefined behavior):** 3 issues
- **P3 (technical debt):** 2 issues

**Recommendation:** Do NOT implement F3 (sentinels) or F7 (dual-write) as written. Fix P0/P1 issues before any code is written.

---

## Issue 1: Sentinel Atomic Claim — TOCTOU Still Possible (P0)

**Severity:** P0 — Silent sentinel corruption under concurrent load

### The Claim

> From the PRD and brainstorm:
>
> ```
> UPDATE sentinels SET last_fired = NOW() WHERE last_fired <= cutoff
> ```
> + check `changes()`. One winner, guaranteed. Eliminates the TOCTOU race in `find -mmin`.

### The Problem

**This pattern has a race condition when used across separate connections.** The PRD does not specify connection pooling strategy, and the described pattern only works if both the UPDATE and the changes() check happen **on the same connection in the same transaction.**

#### Failure Narrative (2-session race)

1. Session A calls `ic sentinel check compound SID --interval=300`
2. Session B calls `ic sentinel check compound SID --interval=300` 100ms later
3. Both sessions open their own SQLite connection (Go's `database/sql` default behavior)
4. Both sessions execute `SELECT last_fired FROM sentinels WHERE name='compound' AND scope_id='SID'` → both see `2026-02-17 10:00:00`
5. Both sessions compute `cutoff = now() - 300s = 2026-02-17 10:05:00`
6. Both sessions execute `UPDATE sentinels SET last_fired = '2026-02-17 10:10:00' WHERE name='compound' AND scope_id='SID' AND last_fired <= '2026-02-17 10:05:00'`
   - Session A wins the write lock first → UPDATE affects 1 row → `changes() = 1` → returns "allowed"
   - Session B waits for lock (blocked on WAL)
   - Session A commits and releases lock
   - Session B's UPDATE now runs against the **already-updated row** where `last_fired = '2026-02-17 10:10:00'` → `last_fired <= cutoff` is FALSE → **UPDATE affects 0 rows** → `changes() = 0` → returns "throttled"

**This works correctly!** But only because of WAL serialization.

#### The Real Race: changes() on Pooled Connections

The `changes()` function in SQLite **only** returns the number of rows affected by the **last statement on that connection.** If the CLI uses a connection pool (Go's default with `database/sql.DB`), the following can happen:

1. Session A: connection #1 executes `UPDATE ... WHERE last_fired <= cutoff` → affects 1 row
2. Session A: releases connection #1 back to pool
3. Session B: grabs connection #1 from pool, runs `SELECT` query for status check
4. Session A: grabs connection #2 from pool, runs `SELECT changes()` → **returns 0** (connection #2 never ran the UPDATE)

**Result:** Session A thinks it was throttled when it actually won the claim. Session B might think it won when it didn't. **Phantom throttles and phantom allows.**

### Existing Intermute Evidence

From `/root/projects/Interverse/services/intermute/AGENTS.md`:

> PRAGMAs (WAL, busy_timeout) only apply to connection they're run on — useless with pooled connections

The same applies to `changes()`. **Connection-local state does not survive round-trips through a pool.**

### Correct Implementation

**Two options:**

**Option A: Single-statement CTE with RETURNING (SQLite 3.35+)**

```sql
WITH claim AS (
  UPDATE sentinels
  SET last_fired = datetime('now')
  WHERE name = ? AND scope_id = ?
    AND (last_fired IS NULL OR unixepoch('now') - unixepoch(last_fired) >= ?)
  RETURNING 1
)
SELECT COUNT(*) AS allowed FROM claim;
```

Returns 1 if claim succeeded, 0 if throttled. **Atomic, single connection, no changes() needed.**

**Option B: Explicit Transaction with Same Connection**

```go
tx, err := db.Begin()
defer tx.Rollback() // rollback if not committed

result, err := tx.Exec(
    "UPDATE sentinels SET last_fired = ? WHERE name = ? AND scope_id = ? AND last_fired <= ?",
    now, name, scopeID, cutoff,
)
rowsAffected, _ := result.RowsAffected() // this is safe within a transaction
tx.Commit()

if rowsAffected == 1 {
    return "allowed"
} else {
    return "throttled"
}
```

**Recommendation:** Use Option A (CTE + RETURNING) for simplicity and portability. Document the SQLite version requirement (3.35+, released 2021, available everywhere).

---

## Issue 2: Run Tracking — No Uniqueness Constraint on Active Runs (P0)

**Severity:** P0 — Two sessions can create conflicting runs for the same bead

### The Problem

The `runs` table schema has no uniqueness constraint to prevent two sessions from creating concurrent active runs for the same bead/project combination.

#### Schema from PRD

```sql
CREATE TABLE runs (
    id          TEXT PRIMARY KEY,    -- UUID
    project     TEXT NOT NULL,
    goal        TEXT,
    status      TEXT NOT NULL DEFAULT 'active',
    phase       TEXT,
    bead_id     TEXT,
    session_id  TEXT,
    created_at  TEXT NOT NULL,
    updated_at  TEXT NOT NULL
);
```

**No unique constraint on `(project, bead_id, status)`.**

#### Failure Narrative (2-session bead race)

1. User runs `clavain:work iv-xyz` in session A
2. Session A calls `ic run create --project=. --bead=iv-xyz --session=A` → creates run `run-001` with status=active
3. Session A crashes (network disconnect, `kill -9`, laptop closed)
4. User runs `/resume` and reruns `clavain:work iv-xyz` in session B
5. Session B calls `ic run create --project=. --bead=iv-xyz --session=B` → creates run `run-002` with status=active
6. **Now there are TWO active runs for bead iv-xyz**
7. Both runs log artifacts, both update phase, both create agents
8. Query `ic run current` returns the **most recent** run (run-002), orphaning all work from run-001

**Silent data corruption:** Artifacts from run-001 are invisible. Phase history is split across two runs. No consolidated view.

### Correct Implementation

**Add a partial unique index:**

```sql
CREATE UNIQUE INDEX idx_runs_active_bead
ON runs(project, bead_id)
WHERE status = 'active' AND bead_id IS NOT NULL;
```

This enforces: **at most one active run per (project, bead_id) pair.**

**Migration path from orphaned sessions:**

```bash
ic run create --project=. --bead=iv-xyz --session=B
# Returns error: UNIQUE constraint failed
# User runs:
ic run list --project=. --bead=iv-xyz --status=active
# Shows run-001 from session A (claimed 60 minutes ago)
# User decides:
ic run abandon run-001  # marks status=abandoned
# Now the create succeeds
```

**Alternative:** Automatic claim-with-timeout (like `sprint_claim()` in lib-sprint.sh). If existing active run is older than 60 minutes, auto-abandon it and create a new one.

---

## Issue 3: Debounce Mechanism — No Cross-Invocation State (P1)

**Severity:** P1 — Debounce is useless for CLI invocations

### The Claim

> From F2 acceptance criteria:
>
> Write rate limiting: `ic state set` with `--debounce` skips write if payload unchanged and last write was < 250ms ago

### The Problem

**`ic` is a CLI, not a daemon.** Each invocation is a separate process. There is **no in-memory cache** to detect "payload unchanged and last write was < 250ms ago" without reading from the database.

#### What Happens in Practice

```bash
# Hook dispatches 5 agents in a loop (statusline dispatch updates)
for agent in agent1 agent2 agent3 agent4 agent5; do
    ic state set dispatch $SID "{\"agents\": [...], \"phase\": \"executing\"}" --debounce
    # Each invocation:
    # 1. Opens DB connection
    # 2. Reads current state row for (dispatch, session, SID)
    # 3. Compares payload JSON (string equality? semantic equality? hash?)
    # 4. Checks updated_at timestamp
    # 5. If < 250ms ago AND payload identical → skip write
    # 6. Else → UPDATE
    # 7. Closes DB connection
done
```

**Cost of debounce:** 5 DB reads + 5 JSON comparisons to avoid... 5 DB writes. **Net loss.** The debounce adds latency and complexity with no throughput win.

#### Why This Happens

The PRD conflates two different debounce strategies:

1. **Daemon-side debounce** (interline polls dispatch status every 1s, batches writes) — this works because the poller has in-memory state
2. **CLI-side debounce** (each `ic` invocation checks DB for "did I just write this?") — this adds a read to avoid a write, **negative value**

### When Debounce Works

Debounce is useful when:
- The writer is a long-running process with in-memory cache (daemon, service, REPL)
- Write frequency far exceeds read frequency (100 Hz updates polled at 1 Hz)
- The debounce check is cheaper than the write (in-memory hash comparison vs. network RPC)

**None of these apply to a CLI.**

### Correct Implementation Options

**Option A: Remove --debounce from CLI**

Document that debounce should happen **in the caller** (the bash hook or interline poller), not in `ic`.

```bash
# Bash hook pseudocode
_last_dispatch_json=""
_last_dispatch_ts=0

dispatch_update() {
    local new_json="$1"
    local now=$(date +%s%N)
    local elapsed_ms=$(( (now - _last_dispatch_ts) / 1000000 ))

    if [[ "$new_json" == "$_last_dispatch_json" && $elapsed_ms -lt 250 ]]; then
        return 0  # skip
    fi

    ic state set dispatch "$SID" "$new_json"
    _last_dispatch_json="$new_json"
    _last_dispatch_ts="$now"
}
```

**Option B: Debounce via DB-side TTL + upsert-only-if-changed**

Store a hash of the payload in the state row:

```sql
CREATE TABLE state (
    key         TEXT NOT NULL,
    scope_type  TEXT NOT NULL,
    scope_id    TEXT NOT NULL,
    payload     TEXT NOT NULL,
    payload_hash TEXT NOT NULL,  -- SHA256 of payload
    updated_at  TEXT NOT NULL,
    ...
);

-- CLI logic:
-- 1. Compute hash of new payload
-- 2. Run:
UPDATE state
SET payload = ?, payload_hash = ?, updated_at = datetime('now')
WHERE key = ? AND scope_type = ? AND scope_id = ?
  AND (payload_hash != ? OR unixepoch('now') - unixepoch(updated_at) >= 0.25);

-- If changes() == 0 → debounced (payload identical + recent write)
-- If changes() == 1 → updated
```

This avoids the extra read, but still requires computing a hash on every call.

**Recommendation:** Option A. Let callers manage debounce. The CLI should be a thin, fast writer.

---

## Issue 4: Dual-Write Mode — Partial Failure Corruption (P0)

**Severity:** P0 — Lost writes and stale reads during migration

### The Claim

> From F7:
>
> In dual-write mode, `ic state set dispatch` also writes `/tmp/clavain-dispatch-$$.json`

### The Problem

**Dual-write has no atomic commit across DB + filesystem.** If one write succeeds and the other fails, consumers see inconsistent state.

#### Failure Scenarios

**Scenario 1: DB write succeeds, file write fails**

1. Hook calls `ic state set dispatch $SID '{"phase": "executing"}'`
2. SQLite UPDATE succeeds → state row updated
3. Attempt to write `/tmp/clavain-dispatch-$$.json` fails (disk full, permission denied, /tmp mounted noexec)
4. `ic` exits with error
5. **interline** (which still reads the legacy file) shows stale phase
6. **New consumers** (reading from DB) show correct phase
7. User sees "phase: planned" in statusline but logs say "phase: executing"

**Scenario 2: File write succeeds, DB write fails**

1. File write succeeds → `/tmp/clavain-dispatch-$$.json` updated
2. SQLite write fails (SQLITE_BUSY after 5s timeout, disk error, constraint violation)
3. `ic` exits with error
4. **interline** shows new phase (reads file)
5. **New consumers** show stale phase (DB not updated)
6. Opposite inconsistency

**Scenario 3: Interleaved writes from two sessions**

1. Session A: writes DB first, then file (order 1)
2. Session B: writes file first, then DB (order 2)
3. Timeline:
   - T0: Session A writes DB with payload `{"phase": "executing", "agents": [A1, A2]}`
   - T1: Session B writes file with payload `{"phase": "shipping", "agents": [B1]}`
   - T2: Session A writes file with payload `{"phase": "executing", "agents": [A1, A2]}`  ← **overwrites B's update**
   - T3: Session B writes DB with payload `{"phase": "shipping", "agents": [B1]}`
4. Final state: DB says "shipping", file says "executing" ← **permanent divergence**

### Why This Can't Be Fixed with Ordering

**There is no 2PC (two-phase commit) between SQLite and filesystem writes.** Any ordering (DB-first or file-first) can be interleaved by concurrent writers.

### Existing Evidence from lib-sprint.sh

The codebase already knows this is a problem. From `lib-sprint.sh:204`:

```bash
# CORRECTNESS: ALL updates to sprint_artifacts MUST go through this function.
# Direct `bd set-state` calls bypass the lock and cause lost-update races.
```

Sprint functions use **filesystem locks** to serialize dual-field updates (read JSON, modify, write JSON). This prevents lost updates **within a single storage backend.**

**Dual-write spans two backends with no coordination.** The lock would have to cover both the DB write AND the file write, but:
- If the lock is a DB row → file writes aren't protected
- If the lock is a file → DB writes aren't protected
- If the lock is in `/tmp/intercore/locks/` → both DB and file contend on the same lock, but `ic` would need to **hold the lock across both writes**, which means:
  - Lock acquisition before any writes
  - Both writes in sequence (doubles latency)
  - Lock release after both writes
  - If `ic` crashes between writes → **stale lock, both systems blocked**

### Correct Implementation

**Do NOT implement dual-write as described.** Instead:

**Migration Strategy: Graceful Cutover with Read Fallback**

1. **Phase 1: ic writes to DB only, readers fall back to legacy**
   - `ic state set` writes to DB
   - `ic state get` reads from DB, returns data
   - **interline/interband** try DB first (`ic state get`), fall back to legacy file if empty/missing
   - Both systems work, legacy files decay naturally

2. **Phase 2: Migrate legacy files to DB (one-time batch)**
   - Script reads all `/tmp/clavain-*.json` and `~/.interband/` entries
   - Imports into intercore with `ic state set`
   - Validates import with `ic state get`

3. **Phase 3: Deprecate legacy files**
   - Remove fallback logic from interline/interband
   - Hooks stop writing legacy files
   - Cleanup script deletes stale temp files

**Key insight:** Reads can be dual-mode (try DB, fall back to file). Writes should be single-mode (DB only). This avoids the dual-write consistency trap.

**Alternative: Write-Ahead + Async Reconciliation**

- `ic` writes to DB immediately (source of truth)
- Background goroutine (or cron job) syncs DB → legacy files every 1 second
- Legacy consumers see up-to-1s stale data during migration
- After migration complete, stop the sync goroutine

This tolerates temporary inconsistency but avoids corruption.

---

## Issue 5: TTL-Based Expiry — Stale Read Window (P2)

**Severity:** P2 — Callers can read expired rows between expiry time and prune

### The Problem

The PRD specifies:
- `expires_at` column for TTL
- `ic state prune` deletes expired rows

**But prune is manual.** Rows with `expires_at < NOW()` remain in the table until someone runs `ic state prune`.

#### Failure Narrative

1. Hook writes dispatch state with `ic state set dispatch $SID '...' --ttl=5m`
2. 5 minutes pass → row is logically expired but still in DB
3. New session runs `ic state get dispatch $SID` → **returns expired data**
4. Session makes decisions based on stale dispatch info (wrong phase, wrong agent list)

### Why This Matters for intercore

Dispatch state and discovery caches have **correctness implications**:
- **Dispatch state:** Agent list, phase, bead binding → wrong agent gets invoked
- **Discovery cache:** Stale sprint list → wrong sprint resumed
- **Bead phase snapshots:** Stale phase → gate checks pass when they should block

TTL isn't just "cleanup convenience" — it's a **correctness boundary**. Expired state should be invisible.

### Correct Implementation

**Enforce TTL in queries, not just in prune:**

```sql
-- ic state get (current)
SELECT payload FROM state
WHERE key = ? AND scope_type = ? AND scope_id = ?;

-- ic state get (correct)
SELECT payload FROM state
WHERE key = ? AND scope_type = ? AND scope_id = ?
  AND (expires_at IS NULL OR expires_at > datetime('now'));
```

**Prune becomes a background cleanup optimization**, not a correctness requirement.

**Add to PRD:**
- All `SELECT` queries MUST include `AND (expires_at IS NULL OR expires_at > datetime('now'))`
- Document this as a **hard requirement** in the CLI implementation
- Add a test: set TTL to 1 second, wait 2 seconds, verify `ic state get` returns empty

---

## Issue 6: Sentinel Interval=0 (Once-Per-Session) — No Idempotency (P1)

**Severity:** P1 — Hook crashes can bypass once-per-session guards

### The Claim

> When `--interval=0`, sentinel fires exactly once per scope_id (once-per-session guard)

### The Problem

**"Fires exactly once" is not the same as "hook runs exactly once."** If the hook crashes after the sentinel fires but before the hook completes, the sentinel prevents retry.

#### Failure Narrative (stop-hook guard)

1. Hook runs `ic sentinel check stop $SID --interval=0` → returns "allowed"
2. Sentinel row inserted: `{name: "stop", scope_id: SID, last_fired: NOW(), interval_s: 0}`
3. Hook does expensive work (runs Oracle, generates artifacts)
4. **Hook crashes** (OOM, timeout, user Ctrl-C)
5. User reruns the command
6. Hook runs `ic sentinel check stop $SID --interval=0` → sentinel already fired → returns "throttled"
7. **Hook skips work that never completed**

### When Once-Per-Session Matters

From existing hooks:
- **stop guard** (`/tmp/clavain-stop-${SID}`) — prevents duplicate stop actions
- **handoff guard** (`/tmp/clavain-handoff-${SID}`) — prevents double session-end processing

These are **lifecycle guards**, not **idempotency guards**. The current `touch` file implementation has the same problem (file created = guard active, even if hook crashes).

### Correct Implementation Options

**Option A: Document the limitation**

```markdown
## Sentinel interval=0 Semantics

`--interval=0` means "fire at most once per scope_id per session lifetime."

If the calling hook crashes after the sentinel fires but before the work completes,
the sentinel will block retry. Use interval=0 only for idempotent or best-effort
actions (e.g., "send Slack message at most once").

For critical actions that must complete, use explicit state tracking:
- `ic state set <key> <scope> '{"status": "done"}'`
- Check status before running work
```

**Option B: Two-phase commit for critical guards**

```bash
# Critical hook pattern
if ic sentinel check critical-work $SID --interval=0; then
    ic state set critical-work-status $SID '{"status": "started"}'
    do_critical_work
    ic state set critical-work-status $SID '{"status": "done"}'
else
    # Sentinel blocked — check if work already completed
    status=$(ic state get critical-work-status $SID | jq -r '.status')
    if [[ "$status" == "done" ]]; then
        echo "Work already completed"
        exit 0
    elif [[ "$status" == "started" ]]; then
        echo "Work in progress or crashed — manual recovery needed"
        exit 1
    fi
fi
```

**Recommendation:** Option A (document). The existing `touch`-file guards have the same crash-recovery gap. This is a known trade-off.

---

## Issue 7: WAL Mode Across Multiple Databases (P2)

**Severity:** P2 — WAL pragmas are connection-local, may not apply to all readers

### The Claim

> WAL mode enabled by default with a configurable `busy_timeout` (default 5s)

### The Problem

From intermute's AGENTS.md:

> PRAGMAs (WAL, busy_timeout) only apply to connection they're run on — useless with pooled connections

If `ic` uses `database/sql.DB` (Go's standard pooled DB handle), each connection in the pool needs pragmas applied **on first use**. The schema doesn't store "this DB is WAL mode" — it's a per-connection setting.

#### How WAL Mode Actually Works

**WAL mode is persistent** (stored in the DB file header after first `PRAGMA journal_mode=WAL`), **but busy_timeout is not.** Each new connection defaults to `busy_timeout=0` (fail immediately on lock).

#### Failure Narrative

1. First `ic` invocation runs `PRAGMA journal_mode=WAL` → DB is now in WAL mode (persistent)
2. Second `ic` invocation opens a new connection, does NOT run `PRAGMA busy_timeout=5000`
3. Concurrent write from session A holds the write lock
4. Session B's `UPDATE` immediately fails with `SQLITE_BUSY` (timeout=0)
5. Session B returns error, hook fails

### Correct Implementation

**Apply busy_timeout on every connection open:**

```go
func openDB(path string) (*sql.DB, error) {
    db, err := sql.Open("sqlite", path)
    if err != nil {
        return nil, err
    }

    // Set connection limits (important for WAL mode)
    db.SetMaxOpenConns(10)
    db.SetMaxIdleConns(5)

    // Apply WAL mode (idempotent, persistent after first call)
    if _, err := db.Exec("PRAGMA journal_mode=WAL"); err != nil {
        return nil, fmt.Errorf("enable WAL: %w", err)
    }

    // CRITICAL: busy_timeout must be set on EVERY connection
    // Use a connection hook or set it in the DSN
    // Option 1: DSN parameter (modernc.org/sqlite supports this)
    // db, err := sql.Open("sqlite", path+"?_busy_timeout=5000")

    // Option 2: Explicit SetConnMaxLifetime + init query
    db.SetConnMaxLifetime(0) // connections live forever
    // First query on each connection should be:
    // PRAGMA busy_timeout=5000

    return db, nil
}
```

**Best practice:** Use DSN parameters for pragma settings that need to apply to every connection:

```go
dsn := fmt.Sprintf("%s?_journal_mode=WAL&_busy_timeout=5000", dbPath)
db, err := sql.Open("sqlite", dsn)
```

**Add to PRD acceptance criteria:**

```
- [ ] busy_timeout applies to all connections (verify with concurrent write test)
- [ ] Test: 5 concurrent `ic state set` calls → all succeed (no SQLITE_BUSY)
```

---

## Issue 8: Run Tracking — `ic run current` with Multiple Projects (P1)

**Severity:** P1 — Undefined behavior when working across projects

### The Claim

> `ic run current` returns the active run for the current session/project (most recent active run)

### The Problem

**What is "current project"?** The PRD specifies:

```sql
CREATE TABLE runs (
    project     TEXT NOT NULL,  -- project path
    session_id  TEXT,
    ...
);
```

**But `ic run current` doesn't take `--project` as a required argument.** How does it determine which project's run to return?

#### Ambiguity Cases

1. **Multi-project session:** User runs `clavain:work` in `/root/projects/A`, then `cd /root/projects/B && clavain:work`. What does `ic run current` return?
   - Most recent run across all projects? (B's run)
   - Run for `$PWD`? (depends on where CLI is invoked)
   - Most recent run for `$CLAUDE_SESSION_ID`? (could be either A or B)

2. **Shared session across projects:** Two tmux panes, same session ID, different `$PWD`. Both run `ic run current` — do they see the same run or different runs?

3. **DB location:** If intercore.db is **global** (`~/.intercore/intercore.db`), it has runs from all projects. If it's **project-local** (`.clavain/intercore.db`), each project has its own DB. The PRD lists this as an open question.

### Correct Implementation

**Require `--project` for all run commands:**

```bash
ic run create --project=/root/projects/A --goal="..." --session=$CLAUDE_SESSION_ID
ic run current --project=/root/projects/A --session=$CLAUDE_SESSION_ID
```

**Or infer from environment:**

```bash
# ic infers project from $PWD (absolute path)
cd /root/projects/A
ic run create --goal="..."  # implicitly sets project=/root/projects/A
ic run current              # returns run for project=/root/projects/A, session=$CLAUDE_SESSION_ID
```

**Tiebreaker query:**

```sql
SELECT id FROM runs
WHERE project = ? AND session_id = ? AND status = 'active'
ORDER BY created_at DESC
LIMIT 1;
```

If multiple active runs exist (shouldn't happen with the unique constraint from Issue 2), return the most recent.

**Add to PRD:**

```markdown
### Project Scope Resolution

All `ic run` commands infer `project` from:
1. `--project=<path>` flag (explicit)
2. `$PWD` (implicit, absolute path)
3. Error if both are missing

Run queries filter by `project` unless `--all-projects` is specified.
```

---

## Issue 9: State Table Primary Key — No Index on session_id (P2)

**Severity:** P2 — Slow queries for "all state for this session"

### The Schema

```sql
CREATE TABLE state (
    key         TEXT NOT NULL,
    scope_type  TEXT NOT NULL,
    scope_id    TEXT NOT NULL,
    payload     TEXT NOT NULL,
    updated_at  TEXT NOT NULL,
    expires_at  TEXT,
    PRIMARY KEY (key, scope_type, scope_id)
);
```

### The Problem

**Common query pattern:** "Get all dispatch state for session `SID`"

```bash
ic state list dispatch --scope=session:$SID
```

**SQLite query plan:**

```sql
SELECT key, scope_id, payload FROM state
WHERE key = 'dispatch' AND scope_type = 'session';
-- Index used: PRIMARY KEY (key, scope_type, scope_id)
-- Rows scanned: ALL rows where key='dispatch' AND scope_type='session'
-- Filter: scope_id MUST match (full table scan of matching prefix)
```

If there are 1000 active sessions, this scans 1000 rows to find 1.

### Why This Matters

Interline statusline polls dispatch state every 1 second. With 10 active sessions, that's 10 queries/sec. With 100 sessions (multi-agent rig), that's 100 queries/sec.

**Without an index on `(scope_type, scope_id)`, every query is O(N) in the number of sessions.**

### Correct Implementation

**Add a secondary index:**

```sql
CREATE INDEX idx_state_scope ON state(scope_type, scope_id, key);
```

Now the query becomes:

```sql
SELECT key, scope_id, payload FROM state
WHERE scope_type = 'session' AND scope_id = ?;
-- Index used: idx_state_scope
-- Rows scanned: 1 (direct lookup)
```

**Benefit:** O(log N) instead of O(N) for session-scoped queries.

---

## Issue 10: Sentinel Prune — No Automatic Cleanup (P3)

**Severity:** P3 — Sentinel table grows unbounded

### The Problem

The PRD specifies:

```
ic sentinel prune --older-than=<duration>  # cleans up stale sentinels
```

**But prune is manual.** Who runs it? When?

Without automatic cleanup:
- Sentinels accumulate (one row per `check` that fired)
- Table size grows linearly with session count
- Query performance degrades (primary key scans)

### Example Growth

- 10 sessions/day × 5 sentinels/session × 365 days = **18,250 rows/year**
- Each row ~100 bytes → 1.8 MB (negligible)
- But index size grows, cache pressure increases, vacuum takes longer

### Correct Implementation

**Option A: Automatic prune on every sentinel check**

```go
func SentinelCheck(name, scopeID string, interval int) (bool, error) {
    // 1. Try to claim sentinel (UPDATE + check changes())
    allowed := ...

    // 2. Prune stale sentinels (async, don't block response)
    go func() {
        // Delete sentinels older than 7 days where scope_type = "session"
        db.Exec("DELETE FROM sentinels WHERE scope_type = 'session' AND unixepoch('now') - unixepoch(last_fired) > 604800")
    }()

    return allowed, nil
}
```

**Option B: Cron job or systemd timer**

```bash
# /etc/cron.daily/intercore-prune
#!/bin/bash
ic sentinel prune --older-than=7d
ic state prune --expired
```

**Option C: TTL index (SQLite 3.45+)**

SQLite 3.45 (unreleased as of Jan 2025) will support automatic row expiration. Until then, Option A or B.

**Recommendation:** Option A (auto-prune after each check). Cost is negligible (DELETE with indexed WHERE), runs in background, no external dependencies.

---

## Issue 11: Schema Migration — No Rollback Strategy (P3)

**Severity:** P3 — Forward-only migrations can't be undone

### The PRD Claim

> Schema migrations run automatically on first use and on version bumps

### The Problem

**What happens when a migration breaks production?**

Example scenario:
1. `ic` v0.2.0 adds a new column to `state` table
2. Migration runs automatically on first `ic state set` call
3. Migration has a bug (wrong column type, missing index)
4. All `ic state get` calls now fail
5. **Hooks can't read dispatch state → Clavain is broken**
6. User wants to rollback to v0.1.0

**But the DB schema is now v0.2.0.** Old `ic` binary can't read the new schema.

### Correct Implementation

**Schema version table + compatibility matrix:**

```sql
CREATE TABLE schema_version (
    version INTEGER PRIMARY KEY,
    applied_at TEXT NOT NULL
);
```

**Migration files:**

```
migrations/
  001_initial.sql
  002_add_runs_table.sql
  003_add_sentinels_index.sql
  ...
```

**Version compatibility:**

```
ic v0.1.0 → requires schema version 1
ic v0.2.0 → requires schema version 1-3 (can read v1, v2, v3; writes as v3)
ic v0.3.0 → requires schema version 3-5
```

**Rollback strategy:**

1. **Forward-compatible schema changes** (add column with DEFAULT, add index) — safe, no rollback needed
2. **Breaking schema changes** (drop column, change type) — require explicit downgrade migration
3. **Emergency rollback:** Keep old `ic` binary, add `ic migrate rollback --to-version=2` command

**Add to PRD:**

```markdown
## Schema Migration Strategy

- Migrations are forward-only by default (add columns, add indexes, add tables)
- Breaking changes require a major version bump and explicit migration plan
- Schema version is stored in `schema_version` table
- `ic` binary checks compatibility on startup: if DB schema version > max supported version, exit with error
```

---

## Summary of Recommendations

| Issue | Severity | Fix Complexity | Must Fix Before |
|-------|----------|----------------|-----------------|
| 1. Sentinel atomic claim (TOCTOU) | P0 | Medium | F3 implementation |
| 2. Run tracking uniqueness | P0 | Low | F4 implementation |
| 4. Dual-write partial failure | P0 | High | F7 implementation (or skip F7 entirely) |
| 5. TTL stale read window | P2 | Low | F2 implementation |
| 6. Sentinel interval=0 idempotency | P1 | Low (doc only) | F3 implementation |
| 7. WAL mode connection pooling | P2 | Low | F1 implementation |
| 8. Run current project scope | P1 | Medium | F4 implementation |
| 9. State table index on scope | P2 | Low | F2 implementation |
| 3. Debounce in CLI | P1 | Low (remove feature) | F2 implementation |
| 10. Sentinel prune automation | P3 | Low | Post-launch |
| 11. Schema migration rollback | P3 | Medium | Post-launch |

**Critical path blockers (P0):**
1. Fix sentinel pattern (use CTE + RETURNING)
2. Add unique constraint on active runs
3. Remove dual-write or implement read-fallback strategy

**High-priority fixes (P1):**
1. Document sentinel interval=0 crash-recovery gap
2. Clarify `ic run current` project scoping
3. Remove `--debounce` flag (or move to caller)

**Medium-priority hardening (P2):**
1. Enforce TTL in all SELECT queries
2. Apply busy_timeout to all connections
3. Add index on `(scope_type, scope_id)`

**Post-launch improvements (P3):**
1. Auto-prune sentinels
2. Schema migration rollback plan

---

## Testing Requirements

To validate the fixes, the plan MUST include:

### Concurrency Tests

```bash
# Test 1: Concurrent sentinel claims (5 sessions, same sentinel)
for i in {1..5}; do
    ic sentinel check test-guard session-X --interval=60 &
done
wait
# Expected: exactly 1 "allowed", 4 "throttled"

# Test 2: Concurrent run creation (2 sessions, same bead)
ic run create --project=. --bead=test-bead --session=A &
ic run create --project=. --bead=test-bead --session=B &
wait
# Expected: 1 succeeds, 1 fails with UNIQUE constraint error

# Test 3: Concurrent state updates (10 sessions, same key)
for i in {1..10}; do
    ic state set test-key session-X "{\"count\": $i}" &
done
wait
# Expected: all 10 succeed, final state has count=<one of 1-10> (last writer wins)
```

### TTL Enforcement Tests

```bash
# Test: Expired state is invisible
ic state set ephemeral session-X '{"data": "test"}' --ttl=1s
sleep 2
result=$(ic state get ephemeral session-X)
[[ -z "$result" ]] || echo "FAIL: got expired data"
```

### Crash Recovery Tests

```bash
# Test: Sentinel fires, hook crashes, retry is blocked
ic sentinel check crash-test session-X --interval=0  # returns "allowed"
# Simulate crash (no state cleanup)
ic sentinel check crash-test session-X --interval=0  # returns "throttled"
# Expected: documented behavior, user must manually clear sentinel or use state tracking
```

---

## Conclusion

The intercore PRD has a **solid high-level design** (SQLite + WAL + Go CLI), but the **concurrency and consistency details are underspecified.** The sentinel atomic claim pattern has a critical flaw (changes() on pooled connections), run tracking has no uniqueness constraint, and dual-write mode will cause data corruption.

**Do not implement F3, F4, or F7 as currently specified.** Fix the P0 issues first, document the P1 limitations, and add the P2 indexes/pragmas. The resulting system will be correct, fast, and maintainable.

The existing codebase (`lib-sprint.sh`, `intermute`) already demonstrates the right patterns:
- Filesystem locks for cross-process coordination
- Read-then-verify for atomic state transitions
- WAL mode + busy_timeout for SQLite concurrency
- Explicit state tracking for idempotency

Apply these patterns to intercore, and the temp file sprawl will collapse into a clean, correct state database.

---

**Next Steps:**

1. Review this analysis with the team
2. Update PRD to fix P0/P1 issues
3. Write a revised plan with correctness tests
4. Implement F1 (schema + CLI scaffold) with fixed patterns
5. Validate with concurrency tests before shipping F2-F4
