# Quality Review: intercore Implementation Plan

**PRD:** `docs/prds/2026-02-17-intercore-state-database.md` (v2)
**Plan:** `docs/plans/2026-02-17-intercore-state-database.md`
**Date:** 2026-02-17
**Reviewer:** Flux-drive Quality & Style Reviewer
**Reference:** `services/intermute/` (established Go 1.22 + modernc.org/sqlite patterns)

## Executive Summary

The implementation plan demonstrates **strong Go idioms and correctness** but has **critical gaps in error handling, testing strategy, and bash library quality**. Most issues are fixable before implementation starts. The plan correctly learns from intermute's database patterns but misses several established testing and shell scripting conventions.

**Severity distribution:**
- **Blocking (must fix before implementation):** 5 findings
- **High (fix during implementation):** 8 findings
- **Medium (improve if time permits):** 6 findings
- **Low (cosmetic/future improvement):** 3 findings

**Key strengths:**
- Error wrapping with `%w` is consistently specified
- Sentinel implementation uses correct CTE+RETURNING pattern
- Schema design follows SQLite/WAL best practices
- CLI framework is sound (exit codes, DB path resolution, help text)

**Key weaknesses:**
- Missing concurrency tests with `-race` flag for critical paths
- Bash library has injection-prone patterns and missing strict mode
- No table-driven test examples specified
- Integration test script has quoting vulnerabilities
- Auto-prune goroutine error handling is unsafe

---

## Blocking Issues (Must Fix Before Implementation)

### B1. Bash library missing strict mode and safe expansion

**Location:** Task 4.1 `lib-intercore.sh`

**Issue:** The bash library does not require `set -euo pipefail` and has multiple unsafe expansion patterns that will cause split/glob bugs and injection vulnerabilities.

**Problems:**

1. **No strict mode declared:** The library should start with `set -euo pipefail` or document why it's incompatible. Without `-e`, command failures will be silently swallowed. Without `-u`, typos become empty strings. Without `-o pipefail`, pipeline failures will be masked.

2. **Unsafe command substitution:** Line 324 has unquoted command expansion:
   ```bash
   _INTERCORE_BIN=$(command -v ic 2>/dev/null || command -v intercore 2>/dev/null)
   ```
   Should be double-quoted in assignment context (though this particular case is safe because `command -v` output is always a single path).

3. **Unsafe string interpolation in shell-out:** Line 337 has:
   ```bash
   echo "$json" | "$_INTERCORE_BIN" state set "$key" "$scope_id" 2>/dev/null
   ```
   If `$json` contains shell metacharacters or newlines, the pipe will break. This is correct only if the caller guarantees JSON is safe. Document this requirement or use `printf '%s\n' "$json"` for safer output.

4. **IFS manipulation without restoration:** Line 365 has:
   ```bash
   IFS=: read -r name scope_id interval <<< "$spec"
   ```
   This modifies `IFS` for the duration of the command, which is correct. But if the function is called in a subshell where `set -e` is active and `read` returns non-zero (e.g., malformed input), the function will exit without cleanup. Add input validation.

5. **Missing quoting in loops:** Line 366-371 has:
   ```bash
   if "$_INTERCORE_BIN" sentinel check "$name" "$scope_id" --interval="$interval" >/dev/null 2>&1; then
   ```
   Variables are correctly quoted. Good.

**Reference:** Clavain hooks use `set -euo pipefail` at the top of every script (`auto-compound.sh` line 24, `lib.sh` line 1 does NOT have it but should — this is a project gap, not a convention to follow).

**Fix:** Add this header to `lib-intercore.sh`:
```bash
#!/usr/bin/env bash
# lib-intercore.sh — Bash wrappers for intercore CLI
# Source this file in hooks: source "$(dirname "$0")/lib-intercore.sh"

# IMPORTANT: This library is designed to be sourced, not executed.
# Sourced scripts should NOT use 'set -e' because it can cause the parent shell to exit.
# Callers should use 'set -euo pipefail' in their own scripts.
# This library uses explicit error checking and fail-safe returns.

_INTERCORE_BIN=""
```

And add input validation to `intercore_sentinel_check_many`:
```bash
for spec in "$@"; do
    IFS=: read -r name scope_id interval <<< "$spec" || {
        echo "0 "  # Fail-safe: allow on parse error
        continue
    }
    # ... rest of loop
done
```

**Severity:** Blocking — bash libraries without strict mode guidance will be copied into hooks that DO use strict mode, causing unexpected failures.

---

### B2. Integration test script has quoting vulnerabilities

**Location:** Task 4.2 `test-integration.sh`

**Problem:** Line 400 has:
```bash
export INTERCORE_DB="/tmp/intercore-test-$$.db"
```
This is correct (no quoting needed for variable assignment). But line 394-395 has:
```bash
cd "$(dirname "$0")"
go build -o /tmp/ic-test ./cmd/ic
```

If the script directory path contains spaces, `$(dirname "$0")` will be word-split. Should be:
```bash
cd "$(dirname "${BASH_SOURCE[0]}")" || exit 1
```

Also, the script uses `exit 1` on test failures but doesn't clean up the temp DB. Add a trap:
```bash
#!/usr/bin/env bash
set -euo pipefail

cleanup() {
    rm -f /tmp/ic-test "$INTERCORE_DB" "${INTERCORE_DB}-wal" "${INTERCORE_DB}-shm"
}
trap cleanup EXIT
```

**Reference:** intermute doesn't have an integration test script to reference. But Clavain hooks use `trap` for cleanup (`auto-compound.sh` doesn't — another gap in the reference codebase).

**Fix:** Add trap-based cleanup and use `${BASH_SOURCE[0]}` instead of `$0`.

**Severity:** Blocking — integration tests must be reliable. A failed test leaving temp files will accumulate garbage.

---

### B3. Missing concurrency test for `SetMaxOpenConns(1)`

**Location:** Task 1.2 "Acceptance" (line 84)

**Problem:** The plan specifies `SetMaxOpenConns(1)` (line 72) but does NOT specify a concurrency test to verify this works. intermute has `race_test.go` that tests concurrent operations with `-race` flag, but intercore's plan only mentions `-race` in Batch 2 checkpoint (line 219).

**Why this is blocking:** SQLite with `MaxOpenConns > 1` can cause `SQLITE_BUSY` errors or connection-local PRAGMA issues (as documented in intermute's `AGENTS.md` line 269-271). The plan must verify that `MaxOpenConns(1)` prevents these issues.

**Reference:** intermute has `internal/storage/sqlite/race_test.go`:
```go
func TestConcurrentWrites(t *testing.T) {
    // ... sets MaxOpenConns(1), spawns 10 goroutines, verifies no race
}
```

**Fix:** Add to Task 1.2 acceptance criteria:
```
- Concurrency test: 10 goroutines calling Migrate() or Health() concurrently — no race, no SQLITE_BUSY
- Run `go test -race ./internal/db` — no warnings
```

**Severity:** Blocking — concurrency bugs in DB layer are silent and catastrophic. Must test before shipping.

---

### B4. Sentinel auto-prune goroutine error handling is unsafe

**Location:** Task 2.2, line 206-207

**Problem:** The plan says:
> Auto-prune: After every `sentinel check`, spawn a goroutine to `DELETE FROM sentinels WHERE unixepoch() - last_fired > 604800` (7 days). Non-blocking, errors swallowed.

**Why this is unsafe:**
1. **Spawning a goroutine in a CLI command is wrong.** CLI processes exit immediately after the command completes. If `ic sentinel check` spawns a goroutine and returns, the process exits before the DELETE runs. The goroutine dies.
2. **"Errors swallowed" is a code smell.** If the DELETE fails (e.g., SQLITE_BUSY), the sentinel table grows unbounded. This should at least log to stderr.

**Reference:** intermute doesn't spawn goroutines in CLI-like contexts. All background work happens in the long-running server process.

**Fix:** Either:
1. **Run the DELETE synchronously** in the same transaction as the sentinel check (preferred — adds <1ms to the operation).
2. **Run it in a separate `DEFERRED` transaction** after the sentinel check commits, but BEFORE returning to the caller.
3. **Document that auto-prune is best-effort** and add a `ic sentinel prune` manual command (already in the plan).

**Recommended fix:** Change line 206-207 to:
```
Auto-prune: After every `sentinel check` commits, run a separate DEFERRED transaction to DELETE FROM sentinels WHERE unixepoch() - last_fired > 604800. Log errors to stderr but do not fail the command. Auto-prune is best-effort; operators can manually run `ic sentinel prune` if needed.
```

**Severity:** Blocking — the current design will not work as specified.

---

### B5. No table-driven test examples specified

**Location:** All test tasks (1.2, 2.1, 3.1)

**Problem:** The plan specifies unit tests but does NOT show the expected test structure. Go best practice (and intermute convention) is table-driven tests for boundary cases and error conditions.

**Reference:** intermute uses table-driven tests in `internal/storage/sqlite/sqlite_test.go` (not shown in the excerpt, but implied by the multiple `TestSQLite*` functions).

**Why this matters:** Without table-driven test guidance, the implementer will write 10 separate test functions for 10 edge cases. This is verbose and hard to maintain. Table-driven tests are the Go idiom.

**Fix:** Add a table-driven test example to Task 2.1 acceptance:
```
- Unit test (table-driven): test cases for interval=0, interval=5, concurrent checks, expired sentinel, missing row
  Example structure:
  ```go
  func TestSentinelCheck(t *testing.T) {
      tests := []struct{
          name     string
          interval int
          setup    func(*Store)
          wantOK   bool
          wantErr  bool
      }{
          {"first check with interval=0", 0, nil, true, false},
          {"second check with interval=0", 0, setupExisting, false, false},
          {"check within interval", 5, setupRecentFire, false, false},
          {"check after interval", 5, setupExpiredFire, true, false},
      }
      for _, tt := range tests {
          t.Run(tt.name, func(t *testing.T) {
              // ... run test case
          })
      }
  }
  ```
```

**Severity:** Blocking — test strategy must be clear before implementation starts.

---

## High-Priority Issues (Fix During Implementation)

### H1. Error wrapping context is inconsistent

**Location:** Task 2.1, line 136-167 (sentinel Check implementation)

**Problem:** The error wrapping is mostly good but has inconsistencies:
- Line 136: `return false, fmt.Errorf("begin tx: %w", err)` — Good, clear context
- Line 144: `return false, fmt.Errorf("ensure sentinel: %w", err)` — Good
- Line 163: `return false, fmt.Errorf("sentinel check: %w", err)` — Too vague. What failed? Query? Scan?
- Line 166: `return false, fmt.Errorf("commit: %w", err)` — Good

**Fix:** Line 163 should be:
```go
return false, fmt.Errorf("query sentinel claim: %w", err)
```

This matches intermute's pattern (`internal/storage/sqlite/sqlite.go` line 95-100 wraps errors with precise operation names).

**Severity:** High — vague error contexts make debugging harder.

---

### H2. Sentinel CTE uses positional parameters unsafely

**Location:** Task 2.1, line 150-161

**Problem:** The CTE query binds `intervalSec` **three times** as separate positional parameters (line 160):
```go
name, scopeID, intervalSec, intervalSec, intervalSec,
```

This is correct but fragile. If someone refactors the query and removes one `?` placeholder, the binding order breaks silently.

**Fix:** Use a variable or add a comment:
```go
// Bind intervalSec three times: once for interval=0 check, twice for elapsed check
err = tx.QueryRowContext(ctx, `...`, name, scopeID, intervalSec, intervalSec, intervalSec).Scan(&allowed)
```

**Severity:** High — silent binding errors are catastrophic. Add comments or use named parameters (not supported by database/sql in Go, so comments are the best option).

---

### H3. Health() check is underspecified

**Location:** Task 1.2, line 74

**Problem:** The plan says `Health() error` should check:
1. DB readable
2. Schema version current
3. Disk space >10MB

But it does NOT specify:
- What "DB readable" means (can we `SELECT 1`? Can we read from `state` table?)
- How to check disk space (use `syscall.Statfs`? Shell out to `df`?)
- What happens if schema version is TOO OLD (should we return an error or auto-migrate?)

**Reference:** intermute doesn't have a `Health()` function. This is new API surface.

**Fix:** Clarify the acceptance criteria:
```
Health() error:
  - SELECT 1 FROM state LIMIT 0 (verify table exists and is readable)
  - PRAGMA user_version returns expected version (if too old, suggest "run 'ic init' to migrate"; if too new, suggest "upgrade ic binary")
  - syscall.Statfs on DB file's parent directory, check Available > 10MB
  - Return first error encountered (fail-fast, not aggregate errors)
```

**Severity:** High — unclear acceptance criteria lead to inconsistent implementations.

---

### H4. Missing error test cases for state operations

**Location:** Task 3.1, line 260-267

**Problem:** The acceptance criteria list happy-path tests (roundtrip, TTL, invalid JSON, >1MB). But they do NOT test:
- What happens if `scopeID` is empty string?
- What happens if `key` is empty string?
- What happens if `payload` is valid JSON but not an object (e.g., `"string"` or `123`)?
- What happens if two processes race to `Set` the same key?

**Reference:** intermute tests project isolation (`TestSQLiteProjectIsolation` line 31) but doesn't test empty-string edge cases (gap in reference codebase).

**Fix:** Add to Task 3.1 acceptance:
```
- Error tests: empty key returns error, empty scope_id returns error
- Edge case: JSON payload is a primitive ("string", 123, null) — allowed or rejected? (Decision: allowed, no schema constraint)
- Concurrency test: two Set calls on same key race — last-write-wins (documented behavior)
```

**Severity:** High — undefined behavior under edge cases is a bug waiting to happen.

---

### H5. TTL enforcement in State.Get is specified but not enforced in List

**Location:** Task 3.1, line 248-253

**Problem:** The `Get` query correctly filters `WHERE (expires_at IS NULL OR expires_at > unixepoch())` (line 248). But the `List` query (line 253) also has the same filter. This is correct, but the plan doesn't specify what happens if:
- A key has 10 scope_ids, 5 are expired. Does List return 5 rows or 10 rows?

**Answer:** The query is correct (returns 5 rows). But this should be tested.

**Fix:** Add to Task 3.1 acceptance:
```
- TTL in List: set key=test for scope1,scope2,scope3 with TTL=1s. After 2s, set key=test for scope4. List should return only scope4.
```

**Severity:** High — TTL enforcement must be tested in all query paths.

---

### H6. JSON validation is underspecified

**Location:** Task 3.1, line 242-243

**Problem:** The plan says:
> Validate JSON payload (`json.Valid()`) — exit 2 on invalid

But it does NOT specify:
- Does `json.Valid()` accept empty string `""`? (Answer: no, it returns false.)
- Does it accept whitespace-only `"   "`? (Answer: no.)
- Does it accept `null`? (Answer: yes, `null` is valid JSON.)
- Should we reject `null` explicitly or allow it?

**Reference:** intermute doesn't validate JSON payloads (it stores them as `TEXT` and trusts the caller). This is a new requirement for intercore.

**Fix:** Add to Task 3.1:
```
- JSON validation: reject empty string, whitespace-only, and invalid syntax. Allow `null`, primitives, objects, arrays.
- If payload is empty, return error "payload cannot be empty"
- Test case: `echo '' | ic state set k s` → exit 2
- Test case: `echo 'null' | ic state set k s` → exit 0 (null is valid JSON)
```

**Severity:** High — vague validation rules lead to surprising behavior.

---

### H7. Missing sentinel reset safety check

**Location:** Task 2.2, line 192-194

**Problem:** The `ic sentinel reset <name> <scope_id>` command has no confirmation prompt and no dry-run mode. This is dangerous for production use.

**Reference:** intermute doesn't have reset/delete commands (it's append-only). But the plan should consider safety.

**Options:**
1. Add `--force` flag (required for reset to proceed)
2. Add `--dry-run` flag (show what would be reset)
3. Print the current `last_fired` timestamp before resetting

**Recommendation:** Add a confirmation prompt if the sentinel exists and was recently fired (< 1 hour ago). Otherwise, reset silently (fail-fast).

**Fix:** Add to Task 2.2 CLI spec:
```
ic sentinel reset <name> <scope_id> [--force]
  If sentinel was fired within the last hour, require --force flag
  stdout: "reset <name> for <scope_id> (last_fired: <timestamp>)"
  exit: 0
```

**Severity:** High — destructive commands need safety rails.

---

### H8. CLI framework does not specify help text format

**Location:** Task 1.3, line 93

**Problem:** The plan says `ic` with no args prints help, but it does NOT specify the format. Should it print to stdout or stderr? Should it exit 0 or 3?

**Convention:** Most CLI tools print help to **stdout** and exit **0** when invoked with no args or `--help`. They print usage errors to **stderr** and exit **3** when given invalid args.

**Reference:** intermute doesn't have a CLI (it's a server). But standard Go CLI tools (kubectl, docker, git) follow this convention.

**Fix:** Add to Task 1.3:
```
- `ic` with no args prints help to stdout, exits 0
- `ic --help` prints help to stdout, exits 0
- `ic unknown-command` prints error to stderr ("unknown command: unknown-command"), exits 3
- Help format: usage summary, subcommand list, global flags, examples
```

**Severity:** High — inconsistent help behavior breaks scripts and user expectations.

---

## Medium-Priority Issues (Improve If Time Permits)

### M1. Schema version tracking uses two mechanisms

**Location:** Task 1.2, line 73-75

**Problem:** The plan specifies both `PRAGMA user_version` (line 73) and a `schema_version` table (PRD line 202-206). This is redundant.

**Which to use?**
- `PRAGMA user_version` is built-in, atomic, and survives schema changes. **Preferred.**
- `schema_version` table is explicit and queryable in SQL. Useful for migration history.

**Recommendation:** Use **only** `PRAGMA user_version` for v1. Add `schema_version` table in v2 if migration history becomes important.

**Fix:** Remove `schema_version` table from the DDL (PRD line 202-206). Keep only `PRAGMA user_version`.

**Severity:** Medium — redundant mechanisms add complexity without value.

---

### M2. Batch 1 review checkpoint missing coverage check

**Location:** Line 104-110

**Problem:** The checkpoint says:
> Run `go test ./...` — all tests pass
> Run `go vet ./...` — no issues

But it does NOT say to run coverage checks. intermute's test guide (line 242-253) shows `go test -cover ./...` as a standard check.

**Fix:** Add to Batch 1 checkpoint:
```
- Run `go test -cover ./...` — aim for >70% coverage in internal/db/
```

**Severity:** Medium — low coverage is a smell, but not a blocker.

---

### M3. Migration docs lack rollback guidance

**Location:** Task 5.2, line 468-476

**Problem:** The migration docs should explain what happens if:
- A hook is partially migrated (writes to DB but other hooks still read temp files)
- The migration is rolled back (DB is unavailable, need to revert to temp files)

**Fix:** Add to MIGRATION.md outline:
```
5. Rollback procedure: if intercore is unavailable, hooks fall back to temp files automatically (read-fallback design). No manual rollback needed.
6. Partial migration is safe: hooks using intercore write to DB, legacy hooks read temp files. No data loss.
```

**Severity:** Medium — clear rollback guidance reduces deployment risk.

---

### M4. No benchmark for 50ms performance budget

**Location:** PRD line 221-224, plan line 559-560

**Problem:** The PRD specifies a 50ms P99 budget, but the plan does NOT include a benchmark task. How will we verify the budget is met?

**Fix:** Add Task 6.2.5:
```
Write benchmark test:
  - `internal/db/db_bench_test.go`
  - Benchmark state set/get, sentinel check with 10k existing rows
  - Target: <50ms P99 on t2.medium (2 vCPU, SSD)
  - Run: `go test -bench=. -benchmem ./internal/db`
```

**Severity:** Medium — performance budgets without measurement are aspirational.

---

### M5. Prune operations do not return deleted row IDs

**Location:** Task 2.2 line 199-203, Task 3.2 line 284-287

**Problem:** Both `ic sentinel prune` and `ic state prune` return a count of deleted rows, but they do NOT return which rows were deleted. For debugging, it's useful to know WHAT was pruned.

**Options:**
1. Add `--verbose` flag to print deleted keys (one per line to stderr before final count)
2. Add `--dry-run` flag to show what WOULD be deleted without deleting
3. Keep current design (count only) for simplicity

**Recommendation:** Keep count-only for v1. Add `--verbose` in v2 if users request it.

**Severity:** Medium — nice-to-have, not essential.

---

### M6. No guidance on DB file backup/restore

**Location:** Task 6.1, documentation task

**Problem:** The plan does not specify how to backup or restore the DB. For a state database, this is important.

**Fix:** Add to AGENTS.md:
```
## Backup and Restore

Backup:
  - Stop all hooks (no active writes)
  - Copy `.clavain/intercore.db`, `.clavain/intercore.db-wal`, `.clavain/intercore.db-shm`
  - Or use SQLite online backup API (future enhancement)

Restore:
  - Stop all hooks
  - Replace `.clavain/intercore.db` with backup
  - Delete `-wal` and `-shm` files (they are specific to the checkpoint)
  - Run `ic health` to verify

Corruption recovery:
  - Run `ic init` to re-create schema (idempotent)
  - If WAL is corrupt, delete `.db-wal` and `.db-shm`, re-run `ic health`
```

**Severity:** Medium — users will ask for this eventually. Document it now.

---

## Low-Priority Issues (Cosmetic / Future)

### L1. File structure shows placeholder comments

**Location:** Task 1.1, line 23-25

**Problem:** The file structure shows:
```
internal/state/state.go      # (placeholder, filled in Batch 3)
internal/sentinel/sentinel.go # (placeholder, filled in Batch 2)
```

This is fine for planning, but the actual placeholder files should have a TODO comment and a package doc comment, not be empty.

**Fix:** Specify that placeholder files should be:
```go
// Package state provides state CRUD operations.
// TODO(Batch 3): Implement Set, Get, List, Prune.
package state
```

**Severity:** Low — cosmetic, but improves code review experience.

---

### L2. CLI does not support `--version` vs `version` subcommand

**Location:** Task 1.3, line 88-102

**Problem:** The plan shows `ic version` (subcommand) but does not specify whether `ic --version` (flag) should also work.

**Convention:** Most tools support both `tool version` and `tool --version`. The flag form is more common.

**Fix:** Add to Task 1.3:
```
- `ic --version` prints version, exits 0 (same as `ic version`)
- `ic version` also works (subcommand form)
```

**Severity:** Low — minor UX improvement.

---

### L3. Module path includes `infra/` but PRD says it's foundational

**Location:** Task 1.1, line 34

**Problem:** The module path is `github.com/mistakeknot/interverse/infra/intercore`, which implies it lives in `infra/` directory. But Go module paths should match directory structure. If `infra/intercore/` is the physical path, then `go get github.com/mistakeknot/interverse/infra/intercore` will fail (404) unless the repo has a `go.mod` at the root that declares the module as a workspace.

**Fix:** Either:
1. Use module path `github.com/mistakeknot/intercore` and move the repo to `github.com/mistakeknot/intercore` (dedicated repo)
2. Use module path `github.com/mistakeknot/interverse/infra/intercore` and add a workspace `go.work` file at the Interverse repo root
3. Keep current path and document that this module is not `go get`-able until the Interverse repo supports Go workspaces

**Recommendation:** Option 3 for v1 (local-only CLI). Option 1 for v2 if intercore becomes a library.

**Severity:** Low — only matters if we publish the module to pkg.go.dev.

---

## Positive Findings (Things Done Well)

1. **Error wrapping with `%w`:** Consistently specified throughout the plan (lines 136, 144, 163, 166). This matches intermute's pattern.

2. **Sentinel CTE+RETURNING pattern:** Correctly identified the `changes()` TOCTOU issue and specified the correct CTE pattern (line 150-161). This is a sophisticated detail that many plans miss.

3. **WAL mode + busy_timeout via DSN:** Correctly specified that `busy_timeout` must be in the DSN (line 71) so it applies to every connection. This matches intermute's documented SQLite gotcha (AGENTS.md line 269-271).

4. **Exit code convention:** Clear exit code semantics (0=success, 1=expected negative, 2=error, 3=usage). This is better than most CLI tools.

5. **Fail-safe design in bash library:** Functions like `intercore_available()` return success (0) if the binary is unavailable, preventing hooks from blocking workflows (line 336). This is correct for optional infrastructure.

6. **Composite primary keys for multi-tenancy:** The schema uses `(key, scope_id)` as the primary key for `state` table (PRD line 185-191), matching intermute's `(project, id)` pattern. Good consistency.

7. **TTL enforcement in queries:** All read queries include `WHERE (expires_at IS NULL OR expires_at > unixepoch())` (line 248). This is the correct place to enforce TTL (not in the application layer).

8. **Auto-prune is best-effort:** The plan correctly identifies that auto-prune is an optimization, not a correctness requirement (line 206, PRD line 68). This prevents the plan from over-engineering the prune mechanism.

---

## Recommendations Summary

### Before Implementation Starts (Blocking)

1. **Fix bash library strict mode guidance** (B1) — add header comments explaining sourcing vs execution, add input validation to `sentinel_check_many`
2. **Fix integration test quoting and cleanup** (B2) — use `${BASH_SOURCE[0]}`, add trap-based cleanup
3. **Add concurrency test for DB layer** (B3) — test `SetMaxOpenConns(1)` with 10 goroutines
4. **Fix sentinel auto-prune design** (B4) — run synchronously or document best-effort behavior
5. **Add table-driven test examples** (B5) — show expected test structure for sentinel and state tests

### During Implementation (High Priority)

1. **Improve error context specificity** (H1) — "sentinel check" → "query sentinel claim"
2. **Document sentinel CTE parameter binding** (H2) — add comment for triple `intervalSec` binding
3. **Clarify Health() acceptance criteria** (H3) — specify SELECT 1, disk space check, schema version comparison
4. **Add error test cases for state ops** (H4) — empty key, empty scope_id, primitive JSON
5. **Test TTL enforcement in List** (H5) — verify expired rows are filtered
6. **Clarify JSON validation rules** (H6) — document null/empty/whitespace handling
7. **Add safety check for sentinel reset** (H7) — require --force for recently-fired sentinels
8. **Specify help text format** (H8) — stdout vs stderr, exit codes

### If Time Permits (Medium Priority)

1. **Remove redundant schema_version table** (M1) — use only PRAGMA user_version
2. **Add coverage check to Batch 1 checkpoint** (M2) — run `go test -cover`
3. **Add rollback guidance to MIGRATION.md** (M3) — document fail-safe behavior
4. **Add benchmark for 50ms budget** (M4) — write `db_bench_test.go`
5. **Consider verbose prune output** (M5) — defer to v2
6. **Document backup/restore procedures** (M6) — add to AGENTS.md

### Future Improvements (Low Priority)

1. **Improve placeholder file quality** (L1) — add package doc + TODO comments
2. **Support `--version` flag** (L2) — in addition to `version` subcommand
3. **Clarify module path strategy** (L3) — document local-only vs go-gettable module

---

## Language-Specific Deep Dive

### Go Idioms (Score: 8/10)

**Strengths:**
- Error wrapping with `%w` is correct and consistent
- Uses `context.Context` in all store methods (not shown in plan excerpts but implied)
- Follows "accept interfaces, return structs" (store methods return concrete types)
- Uses `sql.TxOptions{}` for transaction control (line 134)
- Embeds schema with `//go:embed` (line 47)

**Weaknesses:**
- Missing table-driven test guidance (B5)
- Error contexts are sometimes vague (H1)
- No guidance on sentinel errors vs wrapped errors (should `ErrNotFound` be a sentinel or a wrapped error?)

**Recommendation:** Add a section to Task 1.2:
```
Error handling conventions:
  - Use sentinel errors for expected failures: `var ErrNotFound = errors.New("not found")`
  - Wrap unexpected errors with context: `fmt.Errorf("query state: %w", err)`
  - Check sentinel errors with `errors.Is(err, ErrNotFound)`
  - Never return `sql.ErrNoRows` directly — wrap it or convert to ErrNotFound
```

### Naming Conventions (Score: 9/10)

**Strengths:**
- Package names are short and clear: `db`, `state`, `sentinel`
- Function names follow Go convention: `Open`, `Migrate`, `Health` (exported), `applySchema` (internal)
- CLI subcommands are lowercase: `state set`, `sentinel check`
- Variable names are clear: `scopeID`, `intervalSec`, `expiresAt`

**Weaknesses:**
- The bash library uses `_INTERCORE_BIN` (uppercase with underscore prefix) which is unconventional. Should be `_intercore_bin` (lowercase, per bash convention for private variables) or `INTERCORE_BIN` (uppercase, per bash convention for exported variables). The underscore prefix convention is not standard.

**Recommendation:** Change `_INTERCORE_BIN=""` to `INTERCORE_BIN=""` (no underscore prefix, uppercase for global).

### CLI Design Patterns (Score: 8/10)

**Strengths:**
- Clear exit code semantics (0, 1, 2, 3)
- Subcommand structure is intuitive: `ic <noun> <verb>` (state set, sentinel check)
- Global flags are scoped: `--timeout`, `--verbose`, `--json`
- DB path resolution is smart (flag → walk up for `.clavain/intercore.db`)

**Weaknesses:**
- No `--help` vs `help` subcommand guidance (L2)
- No `--dry-run` mode for destructive commands (M5, H7)
- No `--quiet` mode for scripting (might be useful for `ic sentinel check` in cron jobs)

**Recommendation:** Add `--quiet` flag to suppress all output except errors:
```
ic sentinel check stop $SID --interval=0 --quiet
  exit: 0 (allowed) or 1 (throttled), no stdout
```

### Test Strategy (Score: 6/10)

**Strengths:**
- Specifies unit tests for all core operations
- Includes concurrency test for sentinels (Task 2.1, line 181)
- Includes integration test script (Task 4.2)
- Mentions `-race` flag (line 219)

**Weaknesses:**
- No table-driven test examples (B5) — major gap
- No coverage target specified until M2 (should be in Batch 1 checkpoint)
- No benchmark tests specified (M4)
- No fuzz testing considered (not critical for v1, but worth mentioning)

**Recommendation:** Add to Batch 1 checkpoint:
```
- Run `go test -race ./...` — no race warnings
- Run `go test -cover ./...` — >70% coverage in internal/db/, internal/state/, internal/sentinel/
- Run `go test -bench=. ./internal/db` — verify <50ms P99 for state get/set
```

### Bash Library Quality (Score: 5/10)

**Strengths:**
- Fail-safe design (return 0 if unavailable)
- Uses `command -v` instead of `which` (correct)
- Quotes variables in command invocations (line 337)

**Weaknesses:**
- No strict mode guidance (B1) — critical gap
- Uses `IFS=:` without validation (B1)
- Uses `echo "$json" |` instead of `printf '%s\n' "$json" |` (less safe)
- No shellcheck compliance mentioned

**Recommendation:** Add to Task 4.1 acceptance:
```
- shellcheck lib-intercore.sh passes with no warnings (or documents exceptions)
- Smoke test: source lib-intercore.sh in a hook, verify all functions work with paths containing spaces
```

---

## Comparison with intermute Reference Codebase

### What intercore SHOULD adopt from intermute:

1. **`SetMaxOpenConns(1)` pattern** — Already adopted (line 72). Good.
2. **Wrap errors with `%w`** — Already adopted. Good.
3. **Use `//go:embed` for schema** — Already adopted (line 47). Good.
4. **Table-driven tests** — NOT adopted. Must fix (B5).
5. **`-race` testing** — Partially adopted (mentioned in Batch 2 checkpoint). Should be in Batch 1.
6. **Test helpers like `newTestEnv(t)`** — NOT mentioned. Recommend adding:
   ```
   Add test helper in internal/db/db_test.go:
     func newTestDB(t *testing.T) *DB {
         t.Helper()
         db, err := OpenInMemory()
         if err != nil { t.Fatalf("open test db: %v", err) }
         t.Cleanup(func() { db.Close() })
         return db
     }
   ```

### What intercore should NOT adopt from intermute:

1. **InMemory store for production** — intermute has both `sqlite.Store` and `storage.InMemory`. intercore should NOT have an in-memory store (it's a CLI, not a server). Plan correctly omits this.
2. **WebSocket layer** — Not relevant for intercore. Correctly omitted.
3. **HTTP handlers** — Not relevant for intercore. Correctly omitted.
4. **Domain tables** — intermute has specs/epics/stories/tasks. intercore has only state/sentinels. Correctly scoped.

### What intercore does BETTER than intermute:

1. **TTL enforcement in queries** — intermute doesn't have TTL. intercore's design is correct (PRD line 66-67, plan line 248).
2. **Sentinel pattern** — intermute doesn't have throttle guards. intercore's CTE+RETURNING pattern is a novel contribution.
3. **Exit code semantics** — intermute doesn't have a CLI. intercore's exit code design is clearer than most CLI tools.

---

## Final Recommendation

**This plan is APPROVED FOR IMPLEMENTATION after fixing the 5 blocking issues (B1-B5).**

The plan demonstrates strong understanding of Go idioms, SQLite best practices, and CLI design. The blocking issues are fixable in <2 hours of planning work. The high-priority issues can be addressed during implementation as each batch completes.

**Estimated impact of fixing all issues:**
- Blocking fixes: +2 hours (planning)
- High-priority fixes: +4 hours (implementation)
- Medium-priority fixes: +3 hours (polish)
- Total: +9 hours (~1 day)

**Risk assessment after fixes:**
- Correctness risk: **Low** (sentinel CTE pattern is proven, TTL enforcement is sound)
- Performance risk: **Low** (WAL mode + single-writer is correct for CLI workload)
- Maintenance risk: **Medium** (bash library needs strict mode discipline, but plan now documents it)
- Adoption risk: **Low** (fail-safe design prevents workflow breakage)

**Ship it.**
