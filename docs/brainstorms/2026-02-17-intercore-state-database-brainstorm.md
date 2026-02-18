# intercore: State Database for the Interverse

**Bead:** iv-ieh7
**Phase:** brainstorm (as of 2026-02-18T00:02:21Z)
**Date:** 2026-02-17
**Status:** Brainstorm complete

## What We're Building

A Go CLI (`ic`) backed by a single SQLite database (`intercore.db`) that replaces the ~15 scattered temp files in `/tmp/clavain-*` and `~/.interband/` with a unified, queryable state store. It lives at `plugins/intercore/` as a proper Claude Code plugin.

intercore absorbs two of the three current temp file categories:
1. **Structured state** — dispatch progress, bead phase snapshots, checkpoint data, discovery caches
2. **Throttle sentinels** — once-per-session guards, rate-limit timestamps, stop-hook coordination

It explicitly does NOT absorb:
3. **Mutex locks** — the existing `mkdir`-based POSIX atomic locks stay as filesystem operations (consolidate under `/tmp/intercore/locks/`)

## Why This Approach

### The Problem

The current hook infrastructure communicates through a sprawl of temp files:
- 5+ structured JSON files (dispatch, bead phase, checkpoint, discovery cache)
- 5+ sentinel/throttle touch files (stop guard, compound throttle, drift throttle, handoff guard, catalog reminder)
- 4+ mkdir-based mutex directories (sprint lock, advance lock, claim lock, checkpoint lock)

This causes:
- **Race conditions in throttles** — two concurrent sessions can both `find -mmin` and both pass (TOCTOU)
- **No queryability** — answering "what phase is this run in?" requires knowing which temp file pattern to check
- **Cleanup complexity** — each pattern has its own TTL logic, stale detection, and deletion strategy
- **Cross-session blindness** — one session can't easily see another's state

### Why Option B (state + sentinels, keep mutexes)

Oracle (GPT-5.2 Pro) and industry research converged on this split:

**State in DB:** Atomic updates beat "write temp JSON + mv". Schema and indexing (`WHERE session_id = ?`) beat pattern-matching `/tmp`. TTL/retention is cleaner than `find ... -mmin ... -delete`. Multi-reader in WAL mode is excellent.

**Sentinels in DB:** The biggest correctness win. With SQLite, throttle claims become atomic: `UPDATE sentinels SET last_fired = NOW() WHERE last_fired <= cutoff` + check `changes()`. One winner, guaranteed. Eliminates the TOCTOU race in `find -mmin`.

**Mutexes stay filesystem:** Bash hooks can't hold a SQLite transaction open across arbitrary shell operations (file writes, git commands). DB-backed mutexes would require lease-based locking with heartbeats — massive complexity. `mkdir` is POSIX-atomic, zero-latency, proven.

Industry precedent: Temporal, DBOS, Microsoft durabletask-go use SQLite for state. Turborepo/Nx keep filesystem locks. Gunnar Morling's durable execution engine (2025) uses SQLite as sole state backend.

### Why Go

Consistent with `bd` CLI. Compiled binary = fast startup from bash hooks. Mature SQLite drivers (mattn/go-sqlite3 or modernc.org/sqlite). Easy schema migrations. Hooks call `ic state set ...` like they call `bd set-state ...`.

### Why single DB with rate-limited writes (not split DB)

Oracle flagged that high-frequency dispatch status writes could `SQLITE_BUSY` important operations. Two options: rate-limit writes or split into two DB files. Rate-limiting is simpler — one DB, one schema, and the statusline already polls at ~1s intervals so sub-second dispatch writes are wasted. The `ic` binary debounces dispatch updates (write only on state change, max ~4-10 Hz).

## Key Decisions

| Decision | Choice | Rationale |
|---|---|---|
| Scope | State + sentinels (not mutexes) | Correctness win for sentinels; mutexes need POSIX atomicity |
| Location | `plugins/intercore/` | Independent plugin, matches `inter-*` pattern |
| Language | Go binary (`ic` CLI) | Consistent with `bd`, fast startup, proper SQLite |
| DB file | Single `intercore.db` with WAL | Rate-limit hot writes instead of splitting DBs |
| Mutex strategy | Keep filesystem, consolidate under `/tmp/intercore/locks/` | `mkdir` is proven; add owner metadata for debugging |

## Schema (Draft)

### Tables

```sql
-- Structured state (replaces JSON temp files and interband sideband)
CREATE TABLE state (
    key         TEXT NOT NULL,       -- e.g., "dispatch", "bead_phase", "checkpoint"
    scope_type  TEXT NOT NULL,       -- "session", "pid", "project", "sprint"
    scope_id    TEXT NOT NULL,       -- session UUID, PID, project path hash, sprint ID
    payload     TEXT NOT NULL,       -- JSON blob
    updated_at  TEXT NOT NULL,       -- ISO 8601
    expires_at  TEXT,                -- NULL = never expires
    PRIMARY KEY (key, scope_type, scope_id)
);

-- Throttle sentinels (replaces touch files and once-per-session guards)
CREATE TABLE sentinels (
    name        TEXT NOT NULL,       -- e.g., "compound", "drift", "handoff", "stop"
    scope_type  TEXT NOT NULL,       -- "session", "global"
    scope_id    TEXT NOT NULL,       -- session UUID or "*"
    last_fired  TEXT NOT NULL,       -- ISO 8601
    interval_s  INTEGER NOT NULL,    -- minimum seconds between fires (0 = once-ever for scope)
    PRIMARY KEY (name, scope_type, scope_id)
);

-- Run tracking (the tables from the bead description)
CREATE TABLE runs (
    id          TEXT PRIMARY KEY,    -- UUID
    project     TEXT NOT NULL,       -- project path
    goal        TEXT,                -- what this run is trying to achieve
    status      TEXT NOT NULL DEFAULT 'active',  -- active, completed, failed, abandoned
    phase       TEXT,                -- current phase (brainstorm, planned, executing, shipping, done)
    bead_id     TEXT,                -- linked bead ID (if any)
    session_id  TEXT,                -- CLAUDE_SESSION_ID
    created_at  TEXT NOT NULL,
    updated_at  TEXT NOT NULL
);

CREATE TABLE agents (
    id          TEXT PRIMARY KEY,    -- UUID
    run_id      TEXT NOT NULL REFERENCES runs(id),
    type        TEXT NOT NULL,       -- "claude-code", "codex", "oracle", etc.
    name        TEXT,                -- human-readable label
    status      TEXT NOT NULL DEFAULT 'running',  -- running, completed, failed
    output_file TEXT,                -- path to output file
    pid         INTEGER,             -- OS PID if applicable
    created_at  TEXT NOT NULL,
    updated_at  TEXT NOT NULL
);

CREATE TABLE artifacts (
    id          TEXT PRIMARY KEY,    -- UUID
    run_id      TEXT NOT NULL REFERENCES runs(id),
    phase       TEXT NOT NULL,       -- which phase produced this
    path        TEXT NOT NULL,       -- file path
    type        TEXT NOT NULL,       -- "brainstorm", "prd", "plan", "review", "code"
    created_at  TEXT NOT NULL
);

CREATE TABLE phase_gates (
    run_id      TEXT NOT NULL REFERENCES runs(id),
    phase       TEXT NOT NULL,       -- phase being gated
    status      TEXT NOT NULL,       -- "passed", "failed", "skipped"
    evidence    TEXT,                -- JSON: what was checked, what passed/failed
    checked_at  TEXT NOT NULL,
    PRIMARY KEY (run_id, phase)
);
```

### Key Operations

```
# State operations
ic state set dispatch <session_id> '{"agents": [...], "phase": "executing"}'
ic state get dispatch <session_id>
ic state get bead_phase <session_id>
ic state prune --expired          # delete rows where expires_at < now

# Sentinel operations (atomic claim-if-eligible)
ic sentinel check compound <session_id> --interval=300
# Returns: "allowed" (and updates last_fired) or "throttled" (no change)
# Single atomic operation — no TOCTOU race

# Run tracking
ic run create --project=. --goal="implement intercore" --bead=iv-ieh7
ic run phase <run_id> executing
ic agent add <run_id> --type=codex --name="batch-1" --pid=12345
ic artifact add <run_id> --phase=planned --path=docs/plans/... --type=plan

# Queries
ic query "what phase is the current run in?"
ic query "which agents are active?"
ic query "what artifacts were produced in the planning phase?"
```

## Migration Path

### What moves to intercore

| Current Pattern | intercore Equivalent |
|---|---|
| `/tmp/clavain-dispatch-$$.json` | `ic state set dispatch pid:$$` |
| `/tmp/clavain-bead-${SID}.json` | `ic state set bead_phase session:${SID}` |
| `~/.interband/clavain/dispatch/*.json` | `ic state set dispatch ...` (interband becomes optional overlay) |
| `~/.interband/interphase/bead/*.json` | `ic state set bead_phase ...` |
| `.clavain/checkpoint.json` | `ic state set checkpoint project:${PWD_HASH}` |
| `/tmp/clavain-discovery-brief-*.cache` | `ic state set discovery_cache ...` with TTL |
| `/tmp/clavain-stop-${SID}` | `ic sentinel check stop ${SID} --interval=0` |
| `/tmp/clavain-compound-last-${SID}` | `ic sentinel check compound ${SID} --interval=300` |
| `/tmp/clavain-drift-last-${SID}` | `ic sentinel check drift ${SID} --interval=300` |
| `/tmp/clavain-handoff-${SID}` | `ic sentinel check handoff ${SID} --interval=0` |
| `/tmp/clavain-catalog-remind-${SID}.lock` | `ic sentinel check catalog_remind ${SID} --interval=300` |

### What stays (consolidated)

| Current Pattern | New Location |
|---|---|
| `/tmp/sprint-lock-${id}/` | `/tmp/intercore/locks/sprint/${id}/` |
| `/tmp/sprint-advance-lock-${id}/` | `/tmp/intercore/locks/sprint-advance/${id}/` |
| `/tmp/sprint-claim-lock-${id}/` | `/tmp/intercore/locks/sprint-claim/${id}/` |
| `/tmp/checkpoint-lock-*/` | `/tmp/intercore/locks/checkpoint/${hash}/` |
| `/tmp/clavain-autopub.lock` | `/tmp/intercore/locks/autopub/` (clarify: mutex vs throttle) |

### Backward compatibility

During migration, the `ic` binary can optionally write legacy files alongside DB updates (dual-write mode) so consumers like interline can migrate at their own pace. A `--legacy-compat` flag or config toggle controls this.

## Open Questions

1. **DB file location** — `.clavain/intercore.db` (project-relative, alongside checkpoint.json) or `~/.intercore/intercore.db` (global, like interband)? Project-relative matches beads pattern but means one DB per project.
2. **interband relationship** — Does intercore replace interband entirely, or does interband become a "view layer" that reads from intercore for statusline consumption?
3. **autopub.lock semantics** — Is this a mutex (don't run concurrently) or a throttle (don't run too often)? Determines which category it falls into.
4. **Telemetry** — Should `~/.clavain/telemetry.jsonl` also move into intercore? It's append-only observability, not state — might be better left as a flat file.

## References

- [Oracle analysis](/tmp/oracle-intercore-scope.md) — GPT-5.2 Pro trade-off analysis
- [Research: intercore state patterns](research-intercore-state-patterns.md) — detailed inventory of current patterns
- [Gunnar Morling: Durable Execution with SQLite](https://www.morling.dev/blog/building-durable-execution-engine-with-sqlite/)
- [Microsoft durabletask-go](https://github.com/microsoft/durabletask-go) — Go + SQLite durable execution
- [Cloudflare Durable Objects](https://blog.cloudflare.com/sqlite-in-durable-objects/) — SQLite as state backend
