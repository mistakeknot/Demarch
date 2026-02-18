# Quality Review: intercore PRD

**Document:** `/root/projects/Interverse/docs/prds/2026-02-17-intercore-state-database.md`
**Reviewer:** Flux-drive Quality & Style Reviewer
**Date:** 2026-02-17

## Summary

This PRD describes a Go CLI (`ic`) backed by SQLite for unified state management in the Clavain hook infrastructure. The document is well-structured with clear features and acceptance criteria. However, it has gaps in error handling patterns, testing strategy, observability, and Go-specific implementation details.

---

## Universal Quality Issues

### P0: Missing Error Handling Strategy

**Location:** F2, F3, F4 acceptance criteria

**Issue:** The PRD specifies exit codes (0/1) for CLI commands but does not establish:
- Error message format conventions (stderr vs stdout, structured vs plain text)
- Partial failure semantics (e.g., `ic state prune` — what if some deletes fail?)
- Database error handling patterns (locked DB, corrupted WAL, disk full)
- Retry/backoff strategy for transient failures (busy_timeout is mentioned in F1 but not consistently applied)

**Impact:** Without explicit error handling contracts, hook integrations will be fragile and hooks may silently fail or hang.

**Recommendation:** Add a dedicated **Error Handling** section specifying:
- Standard error output format (`ic: <context>: <error>` on stderr)
- Exit code conventions (0=success, 1=expected failure, 2=unexpected failure, 3=usage error)
- How partial failures are communicated (exit 1 + count on stderr)
- Timeout/retry behavior for DB operations
- Fail-safe behavior when DB is unavailable (F5 mentions "never blocks" but F2-F4 don't)

---

### P0: Missing Test Strategy

**Location:** All features

**Issue:** No acceptance criteria specify testing requirements. Critical gaps:
- Concurrency testing for F3 (sentinel race conditions are the core problem being solved)
- WAL mode corruption recovery
- TTL/expiration edge cases (clock skew, system time changes)
- Performance benchmarks (hook latency budget is critical — hooks block user actions)
- Bash integration library error paths

**Impact:** The PRD solves race conditions but provides no verification that the solution works.

**Recommendation:** Add acceptance criteria for each feature:
- **F1:** Schema migration tests (up/down, version skipping)
- **F2:** Concurrency test for debounce logic
- **F3:** Race test with 10+ concurrent `sentinel check` calls (only one should succeed)
- **F4:** Cross-session run tracking tests
- **F5:** Error simulation tests (ic binary missing, DB locked, invalid JSON)
- **F6:** Stale lock detection with killed processes

---

### P1: Missing Observability/Debugging Support

**Location:** All features

**Issue:** No acceptance criteria for debugging tools or telemetry:
- How do you inspect active transactions?
- How do you diagnose lock contention?
- Is there a `--verbose` or `--dry-run` flag?
- Does `ic` log to a file, or only stderr?
- How do you trace sentinel behavior across sessions?

**Impact:** When throttle logic misbehaves (the most likely failure mode), operators will have no visibility.

**Recommendation:** Add to F1 or create **F8: Observability**:
- `ic debug db-stats` — DB size, WAL size, table row counts, lock wait histogram
- `ic debug query <sql>` — Direct SQL query for power users
- `--verbose` flag for all commands (logs SQL, timings, lock waits)
- Optional telemetry appends to `~/.clavain/intercore-telemetry.jsonl`

---

### P2: Schema Design: Timestamp Format Ambiguity

**Location:** F1 (schema), F2 (TTL), F3 (sentinels)

**Issue:** The PRD does not specify timestamp column types. SQLite best practices:
- Use `INTEGER` (Unix epoch seconds) for exact comparisons and arithmetic
- Use `TEXT` (ISO8601) for human readability
- **Never mix both** — query performance and indexing depend on consistency

The PRD mentions `expires_at`, `last_fired`, `created_at` but doesn't specify format.

**Impact:** Mixing formats will cause slow queries, incorrect TTL logic, or timezone bugs.

**Recommendation:** Add to F1 acceptance criteria:
- "All timestamp columns are `INTEGER NOT NULL DEFAULT (unixepoch())` with `CHECK (column_name > 0)`"
- "All duration arguments (`--ttl`, `--interval`, `--max-age`) accept Go `time.ParseDuration` strings (e.g., `5m`, `24h`)"
- If human-readable timestamps are required, add a `datetime(timestamp, 'unixepoch')` computed column

---

### P2: Schema Design: Missing Indexes

**Location:** F1 (schema)

**Issue:** No acceptance criteria specify indexes. Critical queries that will be slow without indexes:
- F2: `SELECT payload FROM state WHERE key = ? AND scope_id = ?` (point lookup)
- F2: `DELETE FROM state WHERE expires_at < unixepoch()` (prune)
- F3: `SELECT last_fired FROM sentinels WHERE name = ? AND scope_id = ?` (throttle check)
- F4: `SELECT * FROM runs WHERE project_path = ? AND status = 'active' ORDER BY created_at DESC LIMIT 1` (run current)

**Impact:** Queries will degrade as the DB grows, causing hook latency spikes.

**Recommendation:** Add to F1:
- "Schema includes indexes on: `(key, scope_id)`, `(expires_at)`, `(name, scope_id)`, `(project_path, status, created_at)`"
- "Index creation is part of the migration, not manual"

---

### P3: Acceptance Criteria Completeness: JSON Validation

**Location:** F2 (`ic state set`)

**Issue:** F2 says `ic state set <key> <scope_id> '<json>'` but doesn't specify:
- Is the JSON validated before insertion?
- What happens if invalid JSON is passed?
- Is there a max payload size?

**Impact:** Hooks will pass invalid JSON and fail silently, or the DB will accumulate garbage.

**Recommendation:** Add to F2:
- "JSON payloads are validated before insertion (exit 2 on invalid JSON)"
- "Max payload size: 1MB (exit 2 on overflow)"
- "Empty string is valid JSON (`""` or `null`)"

---

## Go-Specific Issues

### P1: CLI Naming Collision Risk

**Location:** CLI name `ic`

**Issue:** `ic` is a **very common abbreviation** and may conflict:
- Existing shell aliases or functions (user-defined)
- Future system tools
- Single-letter commands are discouraged in Go CLI design (hard to search, autocomplete ambiguity)

However, counterpoint: `bd` (beads) is also single-letter and already in use.

**Recommendation (soft):** Document the naming decision and rationale in the PRD. If collision occurs, the mitigation is:
- Full binary name is `intercore`, symlinked as `ic`
- Hooks can use `command -v ic || command -v intercore` for discovery
- Bash library uses `intercore_*` prefix (already specified in F5)

**Verdict:** P2 risk, acceptable given precedent (`bd`), but should be documented.

---

### P0: Module Structure Not Specified

**Location:** F1

**Issue:** The PRD does not specify:
- Go module path (e.g., `github.com/mistakeknot/intercore`)
- Package structure (`cmd/ic/`, `internal/db/`, `internal/cli/`, `pkg/client/`?)
- Whether there's a Go library API or only a CLI
- Whether hooks will shell out to `ic` or use a Go client library (F5 implies shell-only)

**Impact:** Without a clear module structure, the codebase will drift into anti-patterns (everything in `main.go`, God objects, tight coupling).

**Recommendation:** Add to F1:
- "Module path: `github.com/mistakeknot/interverse/plugins/intercore`"
- "Package structure: `cmd/ic/` (CLI entry point), `internal/db/` (SQLite layer), `internal/state/` (business logic), `internal/sentinel/` (throttle logic), `internal/run/` (orchestration tracking)"
- "No public Go API in v1 — CLI only, bash hooks shell out"

---

### P1: SQLite Driver Choice Missing Performance/Safety Tradeoffs

**Location:** Open Questions #4

**Issue:** The PRD lists two SQLite drivers but doesn't provide decision criteria:

| Driver | Pros | Cons |
|--------|------|------|
| `modernc.org/sqlite` | Pure Go, cross-compiles easily, no CGO | 2-3x slower than mattn, less battle-tested |
| `github.com/mattn/go-sqlite3` | Fastest, most mature, C SQLite | Requires CGO (complicates builds), binary size |

For this workload (low-volume, hook-triggered writes), **performance difference is negligible** (< 5ms per query). The real question is: do you need cross-compilation?

**Recommendation:** Change from "Open Question" to decision:
- **Use `modernc.org/sqlite`** unless profiling shows hook latency > 50ms
- Rationale: simpler build, faster CI, no CGO pain, acceptable performance for < 1000 ops/sec

---

### P1: Error Handling: No Go Idiom Guidance

**Location:** F1-F4 (all CLI commands)

**Issue:** The PRD specifies exit codes but not Go error handling patterns:
- Should errors be wrapped with `%w` for stack traces?
- Are sentinel errors (e.g., `ErrNotFound`) used for expected failures?
- How are DB errors (`SQLITE_BUSY`, `SQLITE_LOCKED`) handled?
- Is there a retry loop for transient failures, or does `busy_timeout` handle it?

**Impact:** Inconsistent error handling will make debugging and hook integration painful.

**Recommendation:** Add to F1 acceptance criteria:
- "All errors are wrapped with context using `fmt.Errorf(..., %w, err)` to preserve stack traces"
- "Expected failures (e.g., state not found, sentinel throttled) use sentinel errors (`ErrNotFound`, `ErrThrottled`) and return exit 1"
- "Unexpected failures (DB corruption, panics) are logged to stderr and return exit 2"
- "`busy_timeout` is set to 5s (configurable via `--db-timeout`), no manual retry loops"

---

### P2: Concurrency: No Guidance on Transaction Isolation

**Location:** F3 (sentinel check)

**Issue:** F3 says "atomic transaction" but doesn't specify SQLite isolation level:
- SQLite default is `DEFERRED` (optimistic locking, can fail on commit)
- `IMMEDIATE` locks on BEGIN (prevents most contention failures)
- `EXCLUSIVE` locks for entire transaction (slowest, safest)

For F3 (sentinel check), **`IMMEDIATE` is required** to guarantee "only one wins" semantics.

**Recommendation:** Add to F3 acceptance criteria:
- "`ic sentinel check` uses `BEGIN IMMEDIATE` to acquire write lock before reading `last_fired`"
- "All write operations (`state set`, `sentinel check`, `run phase`) use `IMMEDIATE` transactions"
- "Read-only operations (`state get`, `run status`) use `DEFERRED` transactions"

---

### P2: Testing: No Guidance on Table-Driven Tests

**Location:** All features

**Issue:** The PRD has no testing strategy, but Go convention is **table-driven tests**. Critical for:
- F2: State CRUD edge cases (empty key, invalid JSON, expired TTL)
- F3: Sentinel interval edge cases (interval=0, negative interval, concurrent claims)
- F4: Run lifecycle transitions (active → completed, orphaned agents)

**Recommendation:** Add to each feature's acceptance criteria:
- "Unit tests use table-driven test pattern with `t.Run(name, func(t)...)` subtests"
- "Concurrency tests use `t.Parallel()` and `testing/quick` for property-based testing"
- "Integration tests use `t.TempDir()` for ephemeral test databases"

---

### P3: CLI Design: Missing Bash Completion

**Location:** F1 (CLI scaffold)

**Issue:** No mention of shell completion. Standard Go CLI libraries (e.g., Cobra, Kong) support auto-generated completions.

**Impact:** `ic` will be harder to use interactively (but hooks don't need completion).

**Recommendation (nice-to-have):** Add to F1:
- "`ic completion bash|zsh` generates shell completion scripts"
- Install instructions in plugin README

---

## Language-Agnostic Findings

### P2: Acceptance Criteria: Missing Performance Budget

**Location:** All features

**Issue:** Hooks are latency-sensitive (they block user actions). No acceptance criteria specify:
- Max latency per `ic` command (P50, P99)
- DB size growth rate
- Query performance degradation over time

**Recommendation:** Add to F1 or create **F8: Performance**:
- "`ic` commands complete in < 50ms P99 on a DB with 10,000 state rows and 1,000 sentinels"
- "DB file size grows by < 10KB per day of normal usage"
- "`ic state prune` runs in < 100ms for 1,000 expired rows"

---

### P3: Feature Scope: F6 (Mutex Consolidation) Out of Scope?

**Location:** F6

**Issue:** F6 reorganizes filesystem mutexes under `/tmp/intercore/locks/` but **does not use the database**. This is pure filesystem operations + metadata tracking.

Question: Is this feature pulling in too much non-database work? The PRD's core value is "replace temp files with SQLite" but F6 keeps temp files (as lock dirs).

**Recommendation:** Consider moving F6 to a separate PRD/phase. If kept, clarify:
- "F6 does not use intercore.db — it's a namespace consolidation + introspection tool"
- "Lock directories are still `mkdir`-based for atomicity, but owner metadata is standardized"

---

### P4: Backward Compatibility: Dual-Write Complexity

**Location:** F7

**Issue:** Dual-write mode is **notoriously hard to get right**:
- Write order matters (DB first or legacy first?)
- What if DB write succeeds but legacy write fails?
- How do you verify dual-write correctness?
- How do you measure adoption to know when to remove legacy compat?

**Recommendation:** Add to F7:
- "Dual-write always writes DB first, then legacy (fail-safe: DB is authoritative)"
- "Legacy write failures are logged but do not fail the command (exit 0)"
- "`ic debug compat-usage` reports legacy write attempts (telemetry for deprecation timeline)"
- "Migration script validates that DB and legacy files are in sync before enabling read-from-DB-only mode"

---

### P4: Open Question #1 (DB Location) Missing Decision Criteria

**Location:** Open Questions #1

**Issue:** The PRD lists two options but doesn't provide decision criteria. Analysis:

| Location | Pros | Cons |
|----------|------|------|
| `.clavain/intercore.db` | Matches beads, per-project isolation, trivial backup | No cross-project queries, manual cleanup |
| `~/.intercore/intercore.db` | Cross-project queries, single cleanup point | Session isolation harder, who owns the file? |

**Recommendation:** Decide now:
- **Use `.clavain/intercore.db`** (project-relative) for v1
- Rationale: Matches beads, avoids multi-project ownership issues, F4 (run tracking) is project-scoped
- If cross-project queries are needed later, add a `ic global` subcommand with a separate `~/.intercore/global.db`

---

## Summary of Priorities

### P0 (Must Fix Before Implementation)
1. **Error handling strategy** (exit codes, partial failures, DB errors, retry logic)
2. **Test strategy** (concurrency tests for sentinels, WAL recovery, bash integration error paths)
3. **Go module structure** (package layout, no God objects)
4. **Transaction isolation level** (sentinel check requires `BEGIN IMMEDIATE`)
5. **JSON validation** (invalid JSON handling, max payload size)

### P1 (Should Fix Before Shipment)
1. **Observability** (debug commands, verbose mode, telemetry)
2. **SQLite driver choice** (pick `modernc.org/sqlite` and document rationale)
3. **Go error handling idioms** (sentinel errors, `%w` wrapping, busy_timeout config)

### P2 (Nice to Have)
1. **Timestamp format** (INTEGER for all timestamps, document in schema)
2. **Indexes** (explicitly list required indexes in F1)
3. **Performance budget** (P99 latency < 50ms, DB growth limits)
4. **Bash completion** (nice for interactive use)
5. **F6 scope** (consider splitting out mutex consolidation)

### P3-P4 (Quality of Life)
1. **Dual-write complexity** (DB-first ordering, adoption telemetry)
2. **Open Question #1** (pick project-relative DB now)

---

## Go-Specific Idiom Checklist

- [ ] Module path specified (e.g., `github.com/mistakeknot/interverse/plugins/intercore`)
- [ ] Package structure matches responsibility layering (`cmd/`, `internal/`, no `pkg/` in v1)
- [ ] Errors wrapped with `%w` for stack traces
- [ ] Sentinel errors for expected failures (`ErrNotFound`, `ErrThrottled`)
- [ ] Table-driven tests with `t.Run()` subtests
- [ ] Concurrency tests use `t.Parallel()` and test race conditions (`go test -race`)
- [ ] CLI uses a standard library (Cobra, Kong, or flag package)
- [ ] SQLite driver choice documented (`modernc.org/sqlite` recommended)
- [ ] Transaction isolation specified (`IMMEDIATE` for writes, `DEFERRED` for reads)
- [ ] No interface bloat (accept interfaces, return structs — but this is CLI-only, no public API)

---

## Conclusion

This PRD is **structurally solid** with clear features and acceptance criteria. The major gaps are:

1. **No error handling contract** (P0)
2. **No test strategy** (P0, especially concurrency tests)
3. **Missing Go module structure** (P0)
4. **No observability plan** (P1)

Once these gaps are filled, the PRD is ready for implementation. The core design (SQLite + WAL + atomic sentinels) is sound and addresses the stated problem (TOCTOU races in temp files).

**Recommendation:** Add a **Technical Specifications** section covering:
- Go module structure
- SQLite schema DDL with types and indexes
- Error handling conventions
- Test strategy (unit, concurrency, integration)
- Performance budget
- Observability hooks

This will reduce implementation ambiguity and provide a reference for code review.
