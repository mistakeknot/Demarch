# Architecture Review: Native Kernel Coordination Plan

**Plan file:** `/home/mk/projects/Demarch/docs/plans/2026-02-25-native-kernel-coordination.md`
**Review date:** 2026-02-25
**Reviewer:** Flux-drive Architecture & Design Reviewer

---

## Summary Verdict

The strategic direction — unifying coordination into Intercore — is correct. The L1↔L1 no-import boundary is correctly reasoned. The migration phasing is sound. However, the plan has four structural problems that will cause bugs or permanent technical debt if not resolved before implementation: a broken transaction protocol, a UUID mismatch against established conventions, an event bus mismatch requiring schema surgery, and an under-specified Task 9 that cannot safely remove Intermute's `file_reservations` table with what the plan provides. A fifth concern — code duplication of the glob algorithm — is real but the plan's reasoning for it is correct; the recommendation is to document it rather than resolve it by coupling.

---

## Section 1: Boundaries and Coupling

### 1.1 L1↔L1 Boundary — Correct Decision, Correct Mechanism

The plan's decision not to import Intermute from Intercore (or vice versa) is correct. Intermute and Intercore are sibling L1 modules with separate `go.mod` files (`github.com/mistakeknot/intercore` and `github.com/mistakeknot/intermute`). There is no replace directive between them in either module file. Introducing one would create a Go module cycle that the toolchain cannot resolve, and would permanently couple two components that are intended to remain independently deployable.

The chosen mechanism — Interlock shells out to `ic` CLI, Intermute dual-writes via a separate `sql.Open` connection — is the correct seam for cross-module coordination at L1. The `ic` CLI is already the established integration surface for all shell-level callers (`lib-intercore.sh`, Clavain hooks, Interspect). This is consistent.

### 1.2 Dual-Write: Two `sql.DB` Connections to the Same File

The `CoordinationBridge` in Task 7 opens a second `sql.DB` with `MaxOpenConns(1)` against Intercore's `intercore.db`. Intercore's `db.go` already opens that file with `MaxOpenConns(1)` and WAL mode. Two separate `sql.DB` instances against the same file in WAL mode is safe for concurrent reads from different processes. However, `CoordinationBridge.MirrorReserve` uses `INSERT OR IGNORE`, meaning it silently swallows write conflicts. If Intermute processes a reservation before Intercore has swept a conflict from a crashed agent, the bridge will insert without error while the in-memory conflict detection has already passed. This is correct behavior for a best-effort mirror, but the plan's description in Task 3 ("Errors from bridge are logged but don't fail the primary operation") must also explicitly say bridge writes are non-transactional with respect to Intermute's own reservation write. That is, Intermute commits to `file_reservations`, then separately calls `MirrorReserve`. If the bridge write fails, Intercore's view is stale until the next sweep. The plan acknowledges this implicitly via the sweeper but doesn't state the inconsistency window explicitly, which will confuse the implementing agent.

**Recommendation:** Add a comment in `coordination_bridge.go` stating the consistency model: Intercore's `coordination_locks` is eventually consistent during the dual-write phase; authoritative source for conflict decisions during this period is still Intermute's `file_reservations`.

### 1.3 Task 9 Removes Authoritative State Without a Cutover Guard

Task 9's Step 2 says to delete `Reserve()`, `ReleaseReservation()`, `CheckConflicts()`, `ActiveReservations()`, `AgentReservations()` from Intermute's `sqlite.go` and replace them with thin proxies that read/write `coordination_locks` via bridge. At this point, Intermute's HTTP handlers (`handlers_reservations.go`) start querying Intercore's DB directly through the bridge connection.

This creates a hidden dependency: Intermute's HTTP API now silently fails if `intercore.db` does not exist (Intercore not initialized in the project). Before Task 7, Intermute degraded correctly to its own store when coordination bridge was disabled. After Task 9, there is no degraded path. The plan does not define what Intermute returns if the bridge DB is unavailable, nor does it define a startup check.

**Must fix before Task 9:** Define an explicit guard — either Intermute fails loudly at startup if `--intercore-db` is required but absent, or retain the old `file_reservations` path as a fallback (preferred). Removing the fallback without a liveness check makes the service fragile.

### 1.4 Scope Semantics Mismatch Between Systems

Intermute's `Reservation.Project` is a short human-readable name (e.g., `"Demarch"` derived from `basename` of the git root). Intercore's `coordination_locks.scope` is described in the plan as the project directory path (e.g., `"/home/mk/projects/Demarch"`). The `pre-edit.sh` hook already uses `basename` to derive project name for Intermute. The proposed `ic coordination check --scope="$PROJECT_DIR"` uses the full path.

This means an Intermute reservation for project `"Demarch"` and an Intercore coordination lock for scope `"/home/mk/projects/Demarch"` refer to the same files but will never match in a cross-system conflict check. The dual-write bridge in Task 7 uses `project` as scope when calling `MirrorReserve`, so Intermute reservations in the bridge will use the short name while native `ic coordination` calls from Clavain hooks will use the full path.

**Must fix:** Standardize the scope value before Task 7. The simplest option is to always use the canonical absolute path of the project root, derived from `git rev-parse --show-toplevel`. The `interlock-check.sh` already does this for `PROJECT_ROOT`. `DiscoverIntercoreDB` already walks up from `projectDir` to find the DB, so Intercore already treats `projectDir` as the anchor. Normalize all callers to use the absolute path.

---

## Section 2: Pattern Analysis

### 2.1 Transaction Protocol — Broken Pattern

The plan uses this sequence in both `Reserve` and `Transfer`:

```go
tx, err := s.db.BeginTx(ctx, nil)
// ...
if _, err := tx.ExecContext(ctx, "ROLLBACK; BEGIN IMMEDIATE"); err != nil {
```

This is incorrect and will corrupt transaction state in Go's `database/sql`. `database/sql` wraps each `BeginTx` call in a connection-level transaction state. Issuing `ROLLBACK; BEGIN IMMEDIATE` as raw SQL inside an already-begun transaction violates the driver's connection state machine. The `defer tx.Rollback()` that follows will call `ROLLBACK` on a transaction that the driver believes is still open but which the SQLite engine has already committed (via `BEGIN IMMEDIATE`). Under concurrent load this causes "sql: transaction has already been committed or rolled back" panics, and under the race detector it will flag the state mutation.

The correct pattern for `BEGIN IMMEDIATE` in Go with `modernc.org/sqlite` is:

```go
tx, err := s.db.BeginTx(ctx, &sql.TxOptions{Isolation: sql.LevelSerializable})
```

`modernc.org/sqlite` maps `LevelSerializable` to `BEGIN IMMEDIATE`. All existing Intercore transaction code uses `BeginTx(ctx, nil)` — none use the `ROLLBACK; BEGIN IMMEDIATE` pattern. The project's CLAUDE.md note "MaxOpenConns(1) prevents WAL checkpoint TOCTOU" is the mechanism used everywhere else; with a single connection, `BeginTx(ctx, nil)` is already serialized by the connection pool. The plan should not introduce the raw SQL pattern.

Additionally: after `MaxOpenConns(1)`, concurrent calls to `Reserve` will queue at the pool level, not race at the SQLite level. `BEGIN IMMEDIATE` is still correct for correctness under multi-process access (separate agent processes sharing the same DB file), but it must go through the driver.

**Must fix:** Replace `"ROLLBACK; BEGIN IMMEDIATE"` with `BeginTx(ctx, &sql.TxOptions{Isolation: sql.LevelSerializable})` in Tasks 1 and 6.

### 2.2 ID Generation — UUID Conflicts with Project Convention

Task 1's `store.go` calls `uuid.NewString()` to generate lock IDs. Intercore's established convention is 8-character base36 alphanumeric IDs generated by a local `generateID()` function (present in `dispatch`, `discovery`, `lane`, `runtrack` packages). The MEMORY.md confirms: "Run IDs are base36 alphanumeric (e.g., `5953m6kz`), NOT hex." Google/uuid is an indirect dependency in `go.mod`; it is not used in any `internal/` package in Intercore.

Using UUIDs for coordination lock IDs creates a visible inconsistency when locks appear alongside dispatch IDs, run IDs, and lane IDs in the event bus output and `ic coordination list`. Operators will encounter IDs of two different shapes in the same tool output.

**Must fix:** Copy the `generateID()` pattern from `internal/dispatch/dispatch.go` into `internal/coordination/` or extract it to a shared internal utility (it is already duplicated across 4 packages). Do not add a direct dependency on `google/uuid` in coordination code.

### 2.3 Event Bus Integration — Schema Mismatch

Task 4 proposes calling `evStore.AddCoordinationEvent(...)` or "reusing `AddDispatchEvent` with coordination source". Neither works without schema surgery:

- `AddDispatchEvent` requires a `dispatchID` as its first positional parameter — coordination locks have no dispatch ID unless attached to a run.
- `ListEvents` merges `phase_events`, `dispatch_events`, and `discovery_events` via UNION ALL with a fixed column contract (`id, run_id, source, event_type, from_state, to_state, reason, created_at`). A `coordination_events` table would need to be added to all three UNION ALL queries across `ListEvents` and `ListAllEvents`.
- Coordination events are not run-scoped by default (a file reservation may exist outside any run). The existing event query `WHERE run_id = ?` would exclude coordination events that have no `run_id`.

The plan acknowledges "add coordination source constant" but does not define a `coordination_events` table or update the UNION query. The step "Verify events visible via `ic events tail`" will fail as written because `ListEvents` does not query a coordination table.

**Must fix:** Either (a) define a `coordination_events` table with the same column contract as `dispatch_events` and add it to the UNION in `ListEvents`/`ListAllEvents`, or (b) store coordination events in `dispatch_events` with a sentinel `dispatch_id` (e.g., `"coord:<lock_id>"`). Option (b) requires no schema change and matches the existing single-table pattern. The plan must specify which path is taken.

### 2.4 Glob Algorithm Duplication — Necessary but Under-Documented

The plan copies `PatternsOverlap` from `core/intermute/internal/glob/` to `core/intercore/internal/coordination/`. This is the correct choice given the L1↔L1 boundary. The source algorithm at `/home/mk/projects/Demarch/core/intermute/internal/glob/overlap.go` is a complete NFA-based implementation with `ValidateComplexity`, `PatternsOverlap`, `segmentPatternsOverlap`, and the BFS state machine.

The concern is future drift: if the algorithm is patched in one location (e.g., a bug fix for a character class edge case), the other copy will silently diverge. The plan offers no mechanism to detect this.

**Recommendation (not must-fix):** Add a comment block at the top of `core/intercore/internal/coordination/glob.go` stating it is a copy of `core/intermute/internal/glob/overlap.go` taken at a specific commit hash, and that changes to either require manual synchronization. This is a documentation obligation, not a code obligation. The project already tolerates this pattern in other areas (e.g., `generateID` is duplicated across 4 packages).

### 2.5 `isTableExistsError` Helper — Referenced But Not Defined

Task 1's migration guard calls `isTableExistsError(err)`:

```go
if err != nil && !isTableExistsError(err) {
    return fmt.Errorf("v20 coordination_locks: %w", err)
}
```

This helper does not exist in `db.go`. The existing helpers are `isDuplicateColumnError` (for `ALTER TABLE ADD COLUMN`) and `isUniqueConstraintError` (in `discovery/store.go`). There is no `isTableExistsError`. For `CREATE TABLE IF NOT EXISTS`, the `IF NOT EXISTS` guard means the error case should never arise in practice — the helper call is both undefined and unnecessary. Remove it.

### 2.6 Interlock Hook Fallback — Parallel Architectures

Task 8's `pre-edit.sh` rewrite introduces a conditional:

```bash
if command -v ic &>/dev/null; then
    # ic path
else
    # HTTP fallback
fi
```

This creates two parallel code paths in the hook that must both be tested, both be maintained, and both be reasoned about during incident response. The current hook has a single path to Intermute. The CLAUDE.md plugin design principle says "Never duplicate the same behavior in both — single enforcement point per concern."

The fallback also breaks the consistency guarantee: if `ic` is unavailable, the hook falls through to HTTP reservation checking against Intermute, but Intermute (post-Task 9) reads from `coordination_locks`. If `ic` is unavailable because `intercore.db` is corrupt, the HTTP path will also fail. The fallback offers no additional resilience; it just creates code that can drift.

**Recommendation:** Remove the `else` branch from the hook. If `ic` is unavailable, emit `{"additionalContext": "INTERLOCK: ic not found, skipping coordination check"}` and exit 0 (fail-open), matching the existing `intermute_curl` failure behavior. Task 8 should be gated on Task 9 completing so the HTTP path is no longer the authoritative source by the time the hook switches.

---

## Section 3: Simplicity and YAGNI

### 3.1 Transfer (Task 6) — No Current Consumer

The `Transfer` method atomically reassigns all active locks from one agent to another. The plan states this is for "session handoff". There is no caller of this today in Interlock, Clavain hooks, or any shell script. The `intercore_lock` Bash functions do not implement handoff. No existing agent lifecycle event triggers a transfer.

The Transfer operation adds 80 lines of store code, a CLI subcommand, and conflict-check logic that duplicates the `Reserve` conflict scan with a different query shape. The conflict scan in `Transfer` iterates rows in a nested loop without closing the outer cursor before the inner query, which will deadlock with `MaxOpenConns(1)` (SQLite cannot open a second read while a read cursor is open on the same connection).

**Recommendation:** Remove Task 6 from this sprint. Implement it when an actual session-handoff caller exists. This is a clean YAGNI case: no concrete consumer, speculative API, and a latent deadlock bug.

### 3.2 Sweep PID Detection — Platform-Specific and Fragile

`findStalePIDs` parses `owner` as `"PID:hostname"` and calls `syscall.Kill(pid, 0)`. This works only on Linux/macOS. The plan targets a Linux server (confirmed by environment info). However:

- PIDs are recycled by the OS. A new process may have the same PID as a crashed agent within minutes on a busy system.
- `parsePID` splits on `:` and takes `parts[0]`. If the owner format is ever changed (e.g., `"agent-uuid:PID:hostname"` as used in Intermute), the parser silently returns PID 0 and skips the lock.
- `named_lock` is the only type swept for PID death, but the new unified table also holds `file_reservation` and `write_set` entries. Agents holding file reservations crash too. The plan sweeps them only by TTL, not by PID death.

The PID-based sweep is a copy of the existing `internal/lock/lock.go` stale-detection logic. That logic is already present and working in the filesystem lock manager. For the SQLite-backed coordination store, TTL-based expiry is sufficient and correct for `file_reservation` and `write_set` types (they should always have TTLs). PID-based cleanup for `named_lock` is a reasonable optimization but should be explicitly guarded against PID recycling with a minimum age threshold (e.g., "only consider PID dead if lock is older than 30 seconds").

**Recommendation:** Remove PID-based sweep from the initial implementation. Add TTL-only sweep for all types. Add a code comment that PID-based named_lock sweep can be added later with a minimum-age guard to reduce recycling false positives.

### 3.3 Migration Guard Condition in Task 1

The proposed migration guard is:

```go
if currentVersion >= 3 && currentVersion < 20 {
    // CREATE TABLE IF NOT EXISTS coordination_locks
}
```

All existing migration guards follow a similar shape. However, the comment in Task 1 says "indexes created by schema.sql (IF NOT EXISTS)" — but `schema.sql` is applied via `CREATE TABLE IF NOT EXISTS` on the entire DDL block after all guards complete. The coordination indexes need to be included in the migration guard block explicitly, or they must be added to `schema.sql` with `IF NOT EXISTS`. The plan's current code omits the indexes from the migration block and says schema.sql handles them, but schema.sql is only applied via a single `ExecContext` at the end of `Migrate()`. If the table already exists (migration ran before), the schema.sql exec will succeed via `IF NOT EXISTS` but still re-attempt index creation — which is fine because the indexes also use `IF NOT EXISTS`. This actually works, but the comment in the plan is misleading and will confuse the implementer.

**Minor fix:** Remove the misleading comment or make the index creation explicit in the migration guard.

---

## Section 4: Dependency Order Assessment

The stated dependency graph is correct:

```
Task 1 (schema) → Task 2 (glob) → Task 3 (CLI) → Tasks 4, 5, 6 (parallel)
Tasks 4+5 → Task 7 (dual-write)
Task 7 → Task 8 (interlock bridge)
Task 8 → Task 9 (cleanup)
```

One correction: Task 6 (Transfer) should be removed (see 3.1). Tasks 4 and 5 can both proceed after Task 3 without depending on each other. Task 8 can be parallelized with Task 7 if the `ic` binary is available from Task 3, since the Interlock bridge only requires the binary to exist, not Intermute's dual-write to be active.

The sequential dependency from Task 7 → Task 9 is real and important. Task 9 must not be executed until Intermute has been running with dual-write enabled in production long enough to verify that `coordination_locks` mirrors all active reservations without gaps. The plan should state a validation criterion before Task 9 begins (e.g., run `ic coordination list --active` and compare row count against `SELECT COUNT(*) FROM file_reservations WHERE released_at IS NULL` in Intermute's DB).

---

## Must-Fix List (Blocking Issues)

These must be resolved before implementation begins. Each is a defect that would survive code review and cause a runtime failure or permanent architectural problem.

**M1 — Transaction Protocol (Task 1, Task 6)**
Replace `tx.ExecContext(ctx, "ROLLBACK; BEGIN IMMEDIATE")` with `s.db.BeginTx(ctx, &sql.TxOptions{Isolation: sql.LevelSerializable})`. The current form corrupts `database/sql` connection state.
Files: `core/intercore/internal/coordination/store.go`

**M2 — ID Format (Task 1)**
Replace `uuid.NewString()` with the project's 8-char base36 `generateID()`. Extract from `internal/dispatch/dispatch.go` to `internal/coordination/` or a shared `internal/idgen/` package.
Files: `core/intercore/internal/coordination/store.go`, `core/intercore/internal/coordination/types.go`

**M3 — Event Bus Schema (Task 4)**
Define a `coordination_events` table with the dispatch_events column contract, add a migration block for it, and add it to the UNION ALL in `ListEvents` and `ListAllEvents`. Alternatively, adopt option (b): store events in `dispatch_events` with `dispatch_id = "coord:" + lockID`.
Files: `core/intercore/internal/event/store.go`, `core/intercore/internal/db/schema.sql`, `core/intercore/internal/db/db.go`

**M4 — Scope Normalization (Tasks 7, 8)**
Standardize `scope` to the canonical absolute path of the project root across all callers. Document the canonical form in `coordination/types.go`. Fix `DiscoverIntercoreDB` walk-up to normalize to `filepath.Clean(dir)` at each level.
Files: `core/intermute/internal/storage/sqlite/coordination_bridge.go`, `interverse/interlock/hooks/pre-edit.sh`, `interverse/interlock/scripts/interlock-check.sh`

**M5 — Task 9 Cutover Guard**
Before Task 9 removes the `file_reservations` path, require that Intermute validates the `--intercore-db` flag at startup and logs a fatal error if the DB is unreachable. The plan must define the validation criterion for promotion from dual-write to single-write.
Files: `core/intermute/cmd/intermute/main.go`

---

## Recommended Cleanup (Non-Blocking)

These are optional improvements that reduce long-term entropy. They can be deferred to a follow-up sprint.

**C1 — Remove Transfer (Task 6)**
No current consumer exists. The nested cursor deadlock in the conflict scan needs to be fixed before this ships anyway. Remove the task and add a `// TODO(transfer): implement when session-handoff is needed` comment.

**C2 — Simplify PID Sweep (Task 5)**
Remove PID-based sweep. Use TTL-only for all lock types. Add minimum-age guard as a precondition for any future PID-based cleanup.

**C3 — Document Glob Copy (Task 2)**
Add a source-commit reference comment in `glob.go`. Prevents silent drift.

**C4 — Remove `isTableExistsError` Call (Task 1)**
`CREATE TABLE IF NOT EXISTS` never errors on duplicate tables. The call is undefined and unnecessary.

**C5 — Remove Dual-Path Hook (Task 8)**
Remove the `else` fallback branch in `pre-edit.sh`. Emit advisory and exit 0 on `ic` unavailability.

---

## File References

The findings above reference the following files:

- `/home/mk/projects/Demarch/docs/plans/2026-02-25-native-kernel-coordination.md` — plan under review
- `/home/mk/projects/Demarch/core/intercore/internal/db/db.go` — migration guard pattern, transaction conventions
- `/home/mk/projects/Demarch/core/intercore/internal/event/store.go` — event bus UNION ALL structure
- `/home/mk/projects/Demarch/core/intercore/internal/event/event.go` — source constants
- `/home/mk/projects/Demarch/core/intercore/internal/lock/lock.go` — existing filesystem lock (sweep PID pattern origin)
- `/home/mk/projects/Demarch/core/intercore/internal/dispatch/dispatch.go` — `generateID()` canonical form
- `/home/mk/projects/Demarch/core/intermute/internal/glob/overlap.go` — algorithm to be copied
- `/home/mk/projects/Demarch/core/intermute/internal/storage/sqlite/sqlite.go` — `Reserve()` implementation, `file_reservations` schema
- `/home/mk/projects/Demarch/core/intermute/cmd/intermute/main.go` — startup flag surface
- `/home/mk/projects/Demarch/interverse/interlock/internal/client/client.go` — current HTTP client
- `/home/mk/projects/Demarch/interverse/interlock/internal/tools/tools.go` — MCP tool registration
- `/home/mk/projects/Demarch/interverse/interlock/hooks/pre-edit.sh` — hook to be rewritten
- `/home/mk/projects/Demarch/interverse/interlock/scripts/interlock-check.sh` — current conflict check
- `/home/mk/projects/Demarch/core/intercore/lib-intercore.sh` — `intercore_lock` functions
