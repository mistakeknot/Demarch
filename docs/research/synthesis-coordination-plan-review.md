# Synthesis: Native Kernel Coordination Plan Review

**Target:** `/home/mk/projects/Demarch/docs/plans/2026-02-25-native-kernel-coordination.md`
**Date:** 2026-02-25
**Reviewers:** 4 flux-drive agents (correctness, safety, architecture, quality)
**Verdict:** **NEEDS_ATTENTION** — Do not proceed to implementation

---

## Executive Summary

The plan's strategic direction is sound — unifying coordination into Intercore via SQLite is architecturally correct, the L1↔L1 boundary is properly reasoned, and the phasing strategy (dual-write → cleanup) is appropriate. However, the plan contains **6 blocking P0 findings** that will cause runtime failures, data corruption, or security breaches if implemented as written. Additionally, **9 P1 findings** represent correctness holes that require fixes before Task 3 (CLI) ships.

**Go/No-Go:** **STOP** — Do not schedule implementation until all P0 findings are resolved.

---

## Validation Summary

| Aspect | Result |
|--------|--------|
| Agents completed | 4/4 (100%) |
| Valid findings | 46 raw → 15 deduplicated |
| P0 CRITICAL | 6 |
| P1 HIGH | 9 |
| P2 MEDIUM | 6 |
| P3 NICE-TO-HAVE | 2 (not blocking) |
| Convergence | 5 findings discovered by 2+ agents (very high confidence) |

---

## Critical Blockers (P0 — Must Fix Before Implementation)

### 1. **ROLLBACK; BEGIN IMMEDIATE Corrupts database/sql State** (C1, ARCH-1)
- **Tasks affected:** 1, 6
- **Severity:** P0 CRITICAL
- **Agents:** fd-correctness, fd-quality, fd-architecture (3 independent reports)

The proposed pattern violates Go's `database/sql` contract:
```go
tx, err := s.db.BeginTx(ctx, nil)
if _, err := tx.ExecContext(ctx, "ROLLBACK; BEGIN IMMEDIATE") { ... }
```

`database/sql` wraps the connection in a state machine. Issuing raw `ROLLBACK` inside an open `BeginTx` transaction leaves the connection in an inconsistent state. The `defer tx.Rollback()` will send a second `ROLLBACK` to the driver, causing "transaction already committed" panics or silent data loss.

**Fix:** Use `sql.TxOptions{Isolation: sql.LevelSerializable}` which `modernc.org/sqlite` maps to `BEGIN IMMEDIATE`:
```go
tx, err := s.db.BeginTx(ctx, &sql.TxOptions{Isolation: sql.LevelSerializable})
defer tx.Rollback()
```

**Status:** Blocking Tasks 1, 6

---

### 2. **Shell Argument Injection in pre-edit.sh** (SAFETY-1)
- **Tasks affected:** 8
- **Severity:** P0 CRITICAL (exploitable)
- **Agent:** fd-safety

The proposed hook constructs JSON via string interpolation:
```bash
echo '{"decision":"block","reason":"INTERLOCK: '"$FILE_PATH"' reserved by '"$blocker"'"}'
```

If `FILE_PATH` contains `'` or `$`, shell metacharacters execute. Example:
```bash
FILE_PATH="foo' $(rm -rf ~) 'bar"
# becomes:
echo '{"decision":"block","reason":"INTERLOCK: foo' $(rm -rf ~) 'bar reserved by ...
# executes: rm -rf ~
```

The `$blocker` value comes from `ic` output via `jq -r`, and compromised agents can write malicious owner strings that execute when the hook reads them back.

**Fix:** Use `jq -nc --arg` for all dynamic values:
```bash
jq -nc --arg fp "$FILE_PATH" --arg bl "$blocker" \
    '{"decision":"block","reason":("INTERLOCK: " + $fp + " reserved by " + $bl)}'
```

**Status:** Blocking Task 8

---

### 3. **PID Reuse Attack on named_lock Sweep** (SAFETY-2)
- **Tasks affected:** 5
- **Severity:** P0 CRITICAL (race condition with timing window)
- **Agent:** fd-safety

The sweep calls `syscall.Kill(pid, 0)` to detect dead lock owners:
```go
func pidAlive(pid int) bool {
    err := syscall.Kill(pid, 0)
    return err == nil || err == syscall.EPERM
}
```

If Agent A crashes with PID 1234, the OS can reassign PID 1234 to an unrelated process. Sweep calls `kill(1234, 0)`, sees the new process is alive, and never releases Agent A's lock. The lock becomes permanent.

Alternatively, PID counter wraps and 1234 is briefly reassigned to a short-lived process. Sweep catches it dead, releases the lock. Agent A continues running, believing it owns the lock. Two agents now hold conflicting locks.

**Mitigations required:**
- Make TTL mandatory on all `named_lock` entries (schema constraint: `NOT NULL` for `ttl_seconds` when `type='named_lock'`)
- Add hostname check before `pidAlive()` — extract hostname from `"PID:hostname"` format and skip remote PIDs
- Consider heartbeat renewal model: locks must be explicitly renewed before TTL expires

**Status:** Blocking Task 5

---

### 4. **Glob Pattern DoS — ValidateComplexity Not Enforced** (SAFETY-3)
- **Tasks affected:** 2, 3
- **Severity:** P0 CRITICAL (denial-of-service)
- **Agent:** fd-safety

The plan says to copy `ValidateComplexity` from Intermute's glob package but `Store.Reserve()` never calls it:
```go
// Plan's Reserve() loop does NOT validate pattern:
rows, err := tx.QueryContext(ctx, `SELECT ... FROM coordination_locks ...`)
for rows.Next() {
    overlap, err := PatternsOverlap(lock.Pattern, existing.pattern)  // no validation
```

With 100 active locks each holding a moderately complex glob pattern, and a caller submitting `**/**/**/**/**/**/**/**/**/**` (valid within token limits if `ValidateComplexity` is not called), the NFA-based overlap check is O(token^2) per comparison = 2500 steps per lock pair. 100 locks = 250,000 BFS steps before each commit.

A Codex dispatch can call `ic coordination reserve` in a loop 1000 times. After 1000 calls: 1000 rows * 2500 steps = 2.5M CPU cycles per subsequent Reserve. This freezes kernel coordination for all agents.

**Fix:** Call `ValidateComplexity(lock.Pattern)` at the start of `Reserve()` before any DB access, and at the start of `Check()` before fetching rows.

**Status:** Blocking Tasks 2, 3

---

### 5. **isTableExistsError Helper Does Not Exist** (C2)
- **Tasks affected:** 1
- **Severity:** P0 CRITICAL (compile error)
- **Agents:** fd-correctness, fd-quality

Migration block references undefined helper:
```go
if err != nil && !isTableExistsError(err) {
    return fmt.Errorf("v20 coordination_locks: %w", err)
}
```

`isTableExistsError` is not defined in `db.go`. Only `isDuplicateColumnError` exists. Since `CREATE TABLE IF NOT EXISTS` never returns "table exists" error, the guard is unnecessary.

**Fix:** Remove the undefined reference entirely:
```go
if _, err := tx.ExecContext(ctx, `CREATE TABLE IF NOT EXISTS coordination_locks (...)`); err != nil {
    return fmt.Errorf("v20 coordination_locks: %w", err)
}
```

**Status:** Blocking Task 1

---

### 6. **Event Bus Schema Mismatch — coordination_events Table Undefined** (ARCH-3)
- **Tasks affected:** 4
- **Severity:** P1 → P0 (blocking Task 4 success)
- **Agent:** fd-architecture

Task 4 proposes to emit coordination events via `evStore.AddCoordinationEvent(...)` but:
- No `coordination_events` table is defined in schema.sql
- `ListEvents()` uses UNION ALL with fixed columns (`id, run_id, source, event_type, ...`). Coordination source is not in the union.
- Coordination locks are not run-scoped, so existing `WHERE run_id = ?` filters exclude them.

The step "Verify events visible via `ic events tail`" will fail because the query has no coordination source.

**Fix options:**
- **(a)** Define `coordination_events` table matching dispatch_events schema, add to migration block, add to UNION queries
- **(b)** Store coordination events in `dispatch_events` with sentinel `dispatch_id = "coord:<lock_id>"` (no schema change)

Option (b) is simpler but requires the plan to specify it.

**Status:** Blocking Task 4

---

## High-Priority (P1 — Blocks Shipping Task to Next Stage)

### H1: Reserve() Conflict Check Excludes Same Owner
**Agents:** fd-correctness | **Tasks:** 1

Conflict query uses `WHERE ... owner != ?` which allows an owner to hold both shared and exclusive locks on overlapping patterns. This violates exclusive lock semantics.

**Fix:** Add type-upgrade check or document re-entrant locking semantics explicitly.

---

### H2: Dual-Write Creates Observable Inconsistency Window
**Agents:** fd-correctness | **Tasks:** 7

Intermute commits to `file_reservations`, then separately calls `MirrorReserve()` to `coordination_locks`. During this window, `ic coordination check` sees false negatives. The plan acknowledges this implicitly but does not state the read-path fix: `ic` must query both tables during dual-write phase.

**Fix:** Document the inconsistency window explicitly and require `ic coordination check` to query both tables until Task 9 cleanup removes `file_reservations`.

---

### H3: Sweep Reads Then Writes Without Transaction
**Agents:** fd-correctness | **Tasks:** 5

External `Sweep()` runs `findExpired()` and `findStalePIDs()` outside any transaction. The same lock can appear in both lists (expired by TTL AND stale by PID), causing `Release()` to be called twice, emitting duplicate `coordination.expired` events.

**Fix:** De-duplicate the two lists by ID before the release loop, or exclude TTL-expired rows from `findStalePIDs`.

---

### H4: Transfer() Missing Scan Error Handling
**Agents:** fd-correctness, fd-quality (convergence) | **Tasks:** 6

Transfer reads patterns from `fromRows` and `toRows` without checking `Scan()` errors. I/O failure mid-scan appends empty strings to the patterns slice, corrupting the overlap check.

**Fix:** Check `err := fromRows.Scan(...)` and return errors immediately. Also call `fromRows.Err()` and `toRows.Err()` after loops.

---

### H5: MirrorReserve Uses INSERT OR IGNORE
**Agents:** fd-correctness | **Tasks:** 7

`INSERT OR IGNORE` on PRIMARY KEY conflict silently drops the row. If UUIDs collide (astronomically unlikely but architecturally unsound) or Intermute generates duplicates, the mirror loses data without error. The plan should distinguish between "idempotent replay" and "genuine ID conflict."

**Recommendation:** Use `INSERT OR REPLACE` (upsert) if data should converge, or document the semantic choice.

---

### ARCH-1 (Duplicate of C1): Transaction Protocol
**Agents:** fd-architecture | **Tasks:** 1, 6

See C1 above — fd-architecture independently confirmed the database/sql violation.

---

### ARCH-2: UUID vs Base36 ID Format
**Agents:** fd-architecture | **Tasks:** 1

Lock IDs use `uuid.NewString()` instead of the project's 8-char base36 `generateID()` pattern. Creates visible inconsistency in event bus output. Extract `generateID()` from `internal/dispatch/dispatch.go` to a shared `internal/idgen/` utility.

---

### ARCH-4: Scope Semantics Mismatch
**Agents:** fd-architecture | **Tasks:** 7, 8

Intermute's `Reservation.Project` is a short name (`"Demarch"`). Intercore's `coordination_locks.scope` is the full path (`"/home/mk/projects/Demarch"`). The dual-write bridge will create locks with incompatible scope values, breaking cross-system conflict checks.

**Fix:** Standardize scope to canonical absolute path of git root across all callers. Use `git rev-parse --show-toplevel`.

---

## Medium-Priority (P2 — Reduces Quality, Requires Documentation)

| ID | Task | Issue | Fix |
|----|------|-------|-----|
| M1 | 5 | PID check ignores hostname; cross-host locks never swept | Add hostname validation before `pidAlive()` |
| M2 | 1,4 | Inline sweep in Reserve() emits no events — invisible to monitoring | Call `s.onEvent()` after inline sweep or document as accepted gap |
| M3 | 3,8 | Hook is TOCTOU: check-then-reserve instead of reserve-as-gate | Single `ic coordination reserve` call as authoritative check |
| M4 | 6 | Missing `rows.Err()` after pattern scan loops in Transfer | Add error checks after each loop |
| QUALITY-1 | 1 | `*int64` for nullable timestamps violates codebase convention | Use `sql.NullInt64` scan + assign pattern |
| QUALITY-2 | 4 | `EventFunc` signature does not match `event.Handler` contract | Accept `event.Event` value, return error |

---

## Low-Priority (P3 — Style, Clarification, Non-Blocking)

- **L1:** Remove `isTableExistsError` call (already covered in C2)
- **L2:** `NewStore` signature change in Task 4 breaks Task 1 callers — use `SetEventFunc` method instead
- **L3:** Migration guard comment is misleading about schema.sql execution order
- **L4:** `olderThan` parameter accepted but unused in Sweep queries
- **QUALITY-3:** Test helper naming — use `setupTestStore(t)` pattern, not `tempDB`
- **QUALITY-4:** `parsePID` has unreachable guard (`len(parts) < 1` is always false)
- **QUALITY-5:** `pidAlive` uses direct `==` instead of `errors.Is(err, syscall.EPERM)` — duplicate function

---

## Agent Convergence Analysis

**High convergence (2+ agents independently found):**
1. **C1 / ARCH-1:** `ROLLBACK; BEGIN IMMEDIATE` corrupts database/sql (3 agents: correctness, architecture, quality)
2. **C2:** `isTableExistsError` undefined (2 agents: correctness, quality)
3. **H4:** `Transfer()` missing Scan errors (2 agents: correctness, quality)

**Unique contributions:**
- **fd-safety:** Shell injection (SAFETY-1), PID reuse (SAFETY-2), Pattern DoS (SAFETY-3)
- **fd-architecture:** UUID vs base36 (ARCH-2), Event schema (ARCH-3), Scope mismatch (ARCH-4), Transfer deadlock (C3.1)
- **fd-quality:** Event callback signature (QUALITY-2), Nullable scan pattern (QUALITY-1), Test naming (QUALITY-3)

**Confidence:** Very high on P0 findings (3 agents confirm transaction protocol). P1 findings have broad coverage across all agents.

---

## Files Referenced

**Verdict JSON:** `/home/mk/projects/Demarch/.clavain/verdicts/coordination-plan-review.json`

**Agent Reports:**
- `/home/mk/projects/Demarch/docs/research/fd-correctness-coordination-plan.md`
- `/home/mk/projects/Demarch/docs/research/fd-safety-coordination-plan.md`
- `/home/mk/projects/Demarch/docs/research/fd-architecture-coordination-plan.md`
- `/home/mk/projects/Demarch/docs/research/fd-quality-coordination-plan.md`

**Target Plan:**
- `/home/mk/projects/Demarch/docs/plans/2026-02-25-native-kernel-coordination.md`

---

## Recommended Process

1. **Week 1:** Fix all P0 findings (C1, C2, SAFETY-1, SAFETY-2, SAFETY-3, ARCH-3). Tasks 1, 5, 8 cannot proceed without these.
2. **Week 2:** Fix P1 findings (H1–H5, ARCH-1, ARCH-2, ARCH-4). Re-submit plan for 4-agent review.
3. **Week 3:** Implementation begins only after re-review passes.

Total estimated fix scope: 40–60 hours (mostly pre-implementation spec work, no code changes yet).

---

## Verdict

**Status:** NEEDS_ATTENTION
**Overall Verdict:** RISKY
**Go/No-Go:** STOP — Do not schedule implementation.
**Blockers:** 6 P0 findings (2 compile errors, 4 runtime failures/security issues)
