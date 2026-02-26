# Safety Review: Native Kernel Coordination Plan

**Plan:** `/home/mk/projects/Demarch/docs/plans/2026-02-25-native-kernel-coordination.md`
**Date:** 2026-02-25
**Reviewer:** Flux-drive Safety Reviewer
**Risk Classification:** HIGH

---

## Threat Model

**Deployment context:** Local developer machine / autonomous agent fleet. The `ic` binary runs on the same machine as all agents (Claude, Codex, Gemini). No network exposure for `ic` itself; Intermute exposes HTTP on localhost `:7338`. The Intercore DB lives at `.clavain/intercore.db` and is a single-writer, WAL-mode SQLite file.

**Untrusted inputs:**
- All `--pattern`, `--owner`, `--scope`, `--reason` CLI flags passed to `ic coordination` — any agent including Codex dispatches can call this
- `FILE_PATH` extracted from Claude Code hook input JSON in `pre-edit.sh`
- `$INTERMUTE_AGENT_ID` from the environment (set by agent config, not verified)
- The Intermute DB path discovered by walk-up from a user-supplied directory

**Credentials:** No API keys involved. SQLite files are the only sensitive artifact. The intercore.db is at `0600` after `ic init`, which is good.

**Deployment path:** All changes land directly on `main`. Migration runs on first `ic init` or `ic` invocation after deploy. Rollback requires manual intervention.

---

## Findings

### Finding 1 — CRITICAL: Shell Argument Injection in Pre-Edit Hook (Task 8)

**Severity:** HIGH | **Exploitability:** DIRECT | **Blast radius:** Full file-system write access for any agent

**Location:** Plan Task 8, Step 3 — proposed `pre-edit.sh` rewrite

The proposed hook code inlines unsanitized shell values into an unquoted string passed to `jq`:

```bash
echo '{"decision":"block","reason":"INTERLOCK: '"$FILE_PATH"' reserved by '"$blocker"'"}'
```

`$FILE_PATH` comes from `echo "$INPUT" | jq -r '.tool_input.file_path // empty'` — it is an LLM-generated or agent-generated file path that has already passed through `jq -r` but has not been validated as safe for further shell interpolation. A file path containing a single quote, dollar sign, or backtick breaks the JSON structure or executes arbitrary shell code.

Example: if `FILE_PATH` is set to `foo' $(rm -rf ~) 'bar`, the `echo` line becomes:
```bash
echo '{"decision":"block","reason":"INTERLOCK: foo' $(rm -rf ~) 'bar reserved by ...
```
This executes `rm -rf ~` as a shell subcommand.

**The same pattern exists for `$blocker`**, which is extracted from `ic` JSON output via `jq -r '.[0].owner // "unknown"'`. Owner values are stored verbatim from whatever the calling agent passed as `--owner=`. A compromised or misbehaving agent can write a malicious owner string into the DB that later executes when the hook reads it back.

**Mitigation:** Never build JSON by string interpolation in bash. Use `jq -nc` with `--arg` for all dynamic values. The existing `pre-edit.sh` already does this correctly in the auto-reserve block at line 170:

```bash
# Correct pattern — already present in the file:
RESERVE_PAYLOAD=$(jq -nc \
    --arg agent "$INTERMUTE_AGENT_ID" \
    --arg project "$PROJECT" \
    --arg pattern "$REL_PATH" \
    --arg reason "auto-reserve: editing" \
    '{agent_id:$agent, project:$project, path_pattern:$pattern, exclusive:true, reason:$reason, ttl_minutes:15}')
```

The proposed rewrite must use the same pattern everywhere:

```bash
jq -nc --arg fp "$FILE_PATH" --arg bl "$blocker" \
    '{"decision":"block","reason":("INTERLOCK: " + $fp + " reserved by " + $bl)}'
```

**Also flagged:** The auto-reserve call in the proposed rewrite uses unquoted variable expansion in a pattern that mixes flag-value assignment:

```bash
ic coordination reserve --owner="$INTERMUTE_AGENT_ID" --scope="$PROJECT_DIR" \
    --pattern="$FILE_PATH" --ttl=900 --reason="auto-reserve: editing"
```

This is safe because each value is separately double-quoted and passed to `exec` via bash word-splitting, not a subshell string eval. This specific form is acceptable. The JSON construction above is the critical failure point.

---

### Finding 2 — HIGH: PID Reuse Attack on Named Lock Sweep (Task 5)

**Severity:** HIGH | **Exploitability:** MEDIUM (requires timing) | **Blast radius:** Lock stolen from live agent, agent proceeds without coordination

**Location:** `/home/mk/projects/Demarch/core/intercore/internal/coordination/sweep.go` — `pidAlive()` and `findStalePIDs()`

The plan uses `syscall.Kill(pid, 0)` to determine whether the owning process is alive before forcibly releasing a `named_lock`. This is a classic PID reuse race:

1. Agent A holds a named_lock, owner = `"12345:hostname"`. Agent A crashes, PID 12345 is released by the OS.
2. Within 30 seconds (the typical sweep interval), a new unrelated process — potentially another agent or any system process — gets PID 12345.
3. Sweep runs, calls `kill(12345, 0)` → returns 0 (process exists), concludes lock is alive, does not release it.
4. Agent A's lock is now permanently held by a process that has no knowledge of it. The lock never expires (no TTL on named_locks), and is never swept.

Alternatively, the race goes the other direction:

1. Agent A is alive with PID 12345 and holds a named_lock with no TTL.
2. OS PID counter wraps and briefly reassigns 12345 to a very short-lived process.
3. Sweep catches the window where kill(12345, 0) returns ESRCH, releases the lock.
4. Agent B acquires it. Agent A continues running and believes it holds the lock. Two agents now hold the same exclusive lock.

**The `EPERM` handling makes this worse.** The `pidAlive` function treats `EPERM` as "alive" (correct for cross-user processes). But in a multi-user environment where Codex agents run as `claude-user` and Clavain runs as `mk`, the sweeper running as `mk` will see EPERM for all Codex agent PIDs, meaning it can never sweep any Codex-held named_lock regardless of whether the process is alive.

**Mitigations:**
- Require mandatory TTLs on all named_locks. The schema allows `ttl_seconds` to be NULL — make it NOT NULL with a minimum value (e.g., 300s) for `named_lock` type. This eliminates the permanent-lock scenario entirely.
- Store lock acquisition timestamp and require periodic heartbeat renewal (re-calling `ic coordination reserve` with the same ID extends the TTL). If a lock has not been renewed within 2x the TTL, it is swept regardless of PID state.
- If PID-based sweep is retained, add a hostname check: `parts[1]` from the `"PID:hostname"` format. Only attempt kill(pid, 0) if hostname matches the local machine. Locks owned by a different hostname are always considered stale (or require a different sweep mechanism).
- Document the PID reuse window explicitly. The current plan does not mention it.

---

### Finding 3 — HIGH: Glob Pattern DoS Not Enforced at Reservation Entry Point (Tasks 2 and 3)

**Severity:** HIGH | **Exploitability:** EASY | **Blast radius:** O(N*M) CPU per reservation attempt, where N and M are token counts; can freeze kernel coordination for all agents

**Location:** Plan Task 2 references copying `MaxTokens=50, MaxWildcards=10` from Intermute's `overlap.go`, but the `Store.Reserve()` code in Task 1 / Task 3 does not call `ValidateComplexity()` before entering the conflict-check loop.

Looking at the existing Intermute glob code at `/home/mk/projects/Demarch/core/intermute/internal/glob/overlap.go`, the `ValidateComplexity()` function exists and the plan says to copy it. But `Store.Reserve()` as written calls `PatternsOverlap(lock.Pattern, existing.pattern)` in a loop over all existing active locks — with no validation of either pattern before the loop begins.

The conflict-check loop in `store.go` (lines 207-243 of the plan):
```go
rows, err := tx.QueryContext(ctx, `SELECT id, owner, pattern, reason, exclusive
    FROM coordination_locks
    WHERE scope = ? AND released_at IS NULL ...`)
for rows.Next() {
    // ...
    overlap, err := PatternsOverlap(lock.Pattern, existing.pattern)
```

With 100 active locks each having a moderately complex pattern, and an incoming pattern like `**/**/**/**/**/**/**/**/**/**` (valid within limits if ValidateComplexity is not called), the NFA-based overlap check is called 100 times. If an agent submits a pattern that is maximally complex but still within the BFS state space, this is O(MaxTokens^2) per comparison — 2500 steps per lock pair, 250,000 steps total.

More critically: **nothing prevents the same Codex dispatch from calling `ic coordination reserve` in a tight loop** with a new pattern each time. Each call acquires BEGIN IMMEDIATE, runs the loop, commits a new row, and returns. After 1000 such calls, every subsequent Reserve call iterates 1000 rows * 2500 steps = 2.5M BFS steps before committing.

**Mitigations:**
- Call `ValidateComplexity(lock.Pattern)` at the start of `Reserve()`, before any DB access, and return an error if the pattern exceeds limits. This is a pre-condition that must be enforced at every entry point — CLI (`ic coordination reserve`), MCP tool handler, and direct `Store.Reserve()` calls.
- Add a per-owner limit: reject reservations when a single owner already holds more than N active locks in a scope (suggested: 50). This prevents accumulation-based DoS independent of pattern complexity.
- In `Check()`, apply the same `ValidateComplexity` guard on the input pattern before fetching any rows.

---

### Finding 4 — HIGH: Migration Rollback Is Not Feasible for Task 9 (Cleanup Phase)

**Severity:** HIGH | **Exploitability:** N/A (operational risk, not security) | **Blast radius:** Complete loss of reservation history; agents proceed without conflict detection if rollback is needed

**Location:** Plan Task 9 — "Cleanup Legacy Reservation Storage"

Task 9 deletes Intermute's `file_reservations` table logic (the methods `Reserve()`, `ReleaseReservation()`, `CheckConflicts()`, `ActiveReservations()`) and removes the `--coordination-dual-write` bridge. The plan states no explicit rollback procedure.

The actual destruction sequence is:
1. Task 9, Step 2: Delete `Reserve()` / `ReleaseReservation()` / `CheckConflicts()` from `sqlite.go`
2. Task 9, Step 3: Remove dual-write flag and `MirrorReserve()` / `MirrorRelease()`

At this point:
- If Intercore is unavailable (DB corruption, schema mismatch, binary not updated), Intermute has no fallback. Reservation API calls return errors. Interlock enters fail-open mode, meaning no coordination at all.
- Rolling back to pre-Task-9 code requires both reverting the Go source AND determining whether the `coordination_locks` table has diverged from what `file_reservations` would contain. This is non-trivial if agents have been running for hours after cutover.
- The `file_reservations` table itself is never explicitly dropped in the plan (only the Go code wrapping it), so the data survives in Intermute's DB. But after Task 9, no code reads or writes it. It is stranded.

**The plan has no rollback trigger criteria.** What observable signal causes the team to initiate rollback? What is the maximum acceptable window between Tasks 8 and 9?

**Mitigations required before Task 9 is greenlit:**
- Define explicit go/no-go criteria for cutover: minimum observation period after Task 8 (suggested: 48h with dual-write active and verified), metric thresholds (e.g., zero coordination errors in event bus, sweep counts match between old and new tables).
- Retain `file_reservations` table and Intermute's methods as deprecated-but-functional for at least one release cycle. Removing the table and code in the same commit eliminates the fallback path.
- Write a verification script that compares active rows in `file_reservations` vs `coordination_locks` after dual-write is enabled — a measurable pass/fail pre-cutover check.
- Document rollback procedure explicitly: which commits to revert, in what order, whether DB migration is reversible (it is — the `coordination_locks` table can simply be ignored by old code, but the `user_version` bump to 20 will cause `ErrSchemaVersionTooNew` on old binaries until reverted).

---

### Finding 5 — MEDIUM: Shared SQLite DB Between Two Processes Lacks Coordination Protocol

**Severity:** MEDIUM | **Exploitability:** MEDIUM (timing-dependent) | **Blast radius:** Duplicate reservations, phantom conflicts, data corruption under write pressure

**Location:** Task 7 — Intermute CoordinationBridge opens `intercore.db` independently

The plan has Intermute open Intercore's SQLite DB through a second connection (`CoordinationBridge.db`) with its own connection pool (`SetMaxOpenConns(1)`). Intercore's own `db.Open()` also sets `MaxOpenConns(1)`. Two separate `*sql.DB` handles point at the same WAL-mode file.

WAL mode allows concurrent readers + one writer. With two separate processes each having `MaxOpenConns(1)`, the effective writer pool is 2. WAL handles this correctly at the SQLite level — only one writer proceeds, the other blocks on `SQLITE_BUSY` with the 5s timeout. This is not data corruption in the traditional sense.

However, the plan's `Reserve()` in `store.go` uses this pattern:

```go
tx, err := s.db.BeginTx(ctx, nil)   // begins DEFERRED
// ...
if _, err := tx.ExecContext(ctx, "ROLLBACK; BEGIN IMMEDIATE"); err != nil {
```

Calling `ROLLBACK; BEGIN IMMEDIATE` as a single `ExecContext` is fragile. `database/sql` wraps the connection in a transaction — executing `ROLLBACK` inside an active `BeginTx()` transaction puts the `*sql.Tx` object and the underlying connection into an inconsistent state. The `*sql.Tx`'s `Commit()` and `Rollback()` methods will subsequently call `COMMIT` or `ROLLBACK` on a connection that has already had its transaction manually closed. This is a use-after-rollback bug that can either silently succeed (commit nothing), panic, or return a confusing driver error.

The correct pattern for `BEGIN IMMEDIATE` in `database/sql` is to use `db.BeginTx(ctx, &sql.TxOptions{})` and configure the isolation level, or open the connection with `_txlock=immediate` in the DSN, or use `pragma locking_mode = EXCLUSIVE`. The inline `ROLLBACK; BEGIN IMMEDIATE` string is a workaround that breaks the abstraction.

**Mitigations:**
- Open Intercore DB with `?_txlock=immediate` DSN parameter for the coordination store connection. This makes every `BeginTx` automatically use `BEGIN IMMEDIATE` without the inline ROLLBACK hack. Verify this is supported by `modernc.org/sqlite`.
- If `_txlock` is not available, use `db.Conn(ctx)` to get a dedicated `*sql.Conn`, call `conn.ExecContext(ctx, "BEGIN IMMEDIATE")` directly, and commit/rollback via `conn.ExecContext`. Do not mix `BeginTx` with manual ROLLBACK strings.
- Document the cross-process write pattern explicitly. The 5s busy timeout must be tuned for the expected write rate — at high agent density (10+ agents), contention can exhaust the timeout.

---

### Finding 6 — MEDIUM: Unverified Owner Identity — Any Agent Can Release Another Agent's Lock

**Severity:** MEDIUM | **Exploitability:** EASY | **Blast radius:** Agent can release reservations it does not own, enabling other agents to overwrite files mid-edit

**Location:** Plan Task 1 — `Store.Release()` implementation

The `Release` by `owner+scope` path:

```go
} else if owner != "" && scope != "" {
    res, err = s.db.ExecContext(ctx,
        `UPDATE coordination_locks SET released_at = ? WHERE owner = ? AND scope = ? AND released_at IS NULL`,
        now, owner, scope)
```

There is no authentication binding `--owner=<X>` to the calling agent's actual identity. Any agent that knows (or guesses) another agent's owner string can call `ic coordination release --owner=<victim> --scope=<scope>` and silently release all of that agent's locks.

The `--owner` value is agent-assigned, not kernel-assigned. The existing lock system uses `"PID:hostname"` as the owner format, which provides weak identity (hostname is guessable, PIDs are predictable). Codex dispatch agents all run on the same machine, so hostname provides no isolation.

This is especially dangerous combined with the Transfer feature (Task 6), where `--force` allows transferring any agent's locks to any other owner without checking the caller's identity.

**Mitigations:**
- For the local, single-machine threat model, full authentication is not required. The practical mitigation is: enforce that `ic coordination release` without `--id` requires either the lock's original `dispatch_id` or `run_id` (which the releasing agent must know), not just `owner+scope`. Owner+scope bulk-release should require an explicit `--force` flag to prevent accidental or adversarial bulk release.
- Document that the `transfer --force` command is an administrative operation, not an agent-accessible operation. If Interlock MCP exposes transfer capability to agents, restrict it to a non-force mode only.

---

### Finding 7 — MEDIUM: `git pull --rebase` in Pre-Edit Hook Is Externally Triggered

**Severity:** MEDIUM | **Exploitability:** LOW (requires another agent to craft commit messages) | **Blast radius:** Working tree corruption, merge conflicts introduced mid-session

**Location:** `/home/mk/projects/Demarch/interverse/interlock/hooks/pre-edit.sh` lines 42-47 (existing code, carried forward into new plan)

The hook currently performs `git pull --rebase` when it receives a `"commit:<hash>"` inbox message from another agent. This logic is retained in the plan (the hook is modified for `ic` integration but this section is unchanged). The trigger is an inbox message where the subject starts with `"commit:"` — any agent (or a compromised inbox) can send such a message to cause another agent to pull and rebase mid-session.

An adversarial agent that controls the inbox could:
1. Send `commit:abc123` to agent B's inbox
2. Agent B's next edit triggers `git pull --rebase`
3. If there are real uncommitted changes in agent B's working tree, the rebase may fail or succeed and silently change which files are being edited

The pull also runs without checking whether the current working tree is clean, meaning a rebase on a dirty tree could fail and leave the repo in a `REBASE_HEAD` state where subsequent git operations behave unexpectedly.

This is not introduced by the current plan but is worth flagging because the plan's Task 8 continues to rely on this hook code path.

**Mitigation:** Before `git pull --rebase`, check `git status --porcelain` and skip the pull if any tracked files are modified. This limits the rebase to clean-tree states, preventing the worst-case working-tree corruption.

---

### Finding 8 — LOW: Migration Guard Condition Has Wrong Lower Bound (Task 1)

**Severity:** LOW | **Exploitability:** LOW | **Blast radius:** Migration skip on very old DBs

**Location:** Plan Task 1, Step 2 — migration guard in `db.go`

The plan writes:
```go
if currentVersion >= 3 && currentVersion < 20 {
    _, err := tx.ExecContext(ctx, `CREATE TABLE IF NOT EXISTS coordination_locks ...`)
```

The lower bound `currentVersion >= 3` is inconsistent with the existing migration pattern in `db.go`. Looking at the actual migration file, all migrations that add new tables use `currentVersion >= 3` (the version where the core tables were first created). This is correct and matches the existing style. The `CREATE TABLE IF NOT EXISTS` makes it idempotent. This is not a bug — it is consistent with the existing pattern and safe to implement as written.

However, indexes are not created in the migration block — the plan says "Indexes created by schema.sql (IF NOT EXISTS)". The schema DDL is applied at line 265 of `db.go` (`tx.ExecContext(ctx, schemaDDL)`) after all per-version guards. This means the indexes will be created on first migration regardless of whether the table already existed. This is correct.

**No action required on this finding.**

---

### Finding 9 — LOW: Intermute Bridge Opens DB Without Symlink Check

**Severity:** LOW | **Exploitability:** LOW | **Blast radius:** Intermute opens a symlink-targeted file instead of the real intercore.db

**Location:** Plan Task 7 — `CoordinationBridge.NewCoordinationBridge()`

The existing `db.Open()` in Intercore checks that the parent directory of the DB path is not a symlink:

```go
// From /home/mk/projects/Demarch/core/intercore/internal/db/db.go lines 41-43:
dir := filepath.Dir(path)
if info, err := os.Lstat(dir); err == nil && info.Mode()&os.ModeSymlink != 0 {
    return nil, fmt.Errorf("open: %s is a symlink (refusing to create DB)")
}
```

The plan's `CoordinationBridge` opens the Intercore DB directly via `sql.Open("sqlite", "file:"+dbPath+"?...")` without this symlink check. If `DiscoverIntercoreDB()` walks up the directory tree and finds a `.clavain/intercore.db` that is itself a symlink pointing to `/dev/null` or a world-writable location, Intermute opens it without complaint.

**Mitigation:** Apply the same `os.Lstat` check in `NewCoordinationBridge` before calling `sql.Open`. This is a one-liner that matches the existing Intercore guard.

---

## Pre-Deploy Checklist

The following checks must have measurable pass/fail outcomes before deploying Tasks 7-9.

### Before deploying Task 7 (dual-write enabled):
- [ ] Run `ic coordination list --active` and `ic run agent list <run_id>` — both return valid JSON (schema v20 verified)
- [ ] Start Intermute with `--coordination-dual-write --intercore-db=<path>` and confirm startup log shows "coordination bridge: enabled"
- [ ] Reserve a file through Intermute's HTTP API; verify the row appears in `coordination_locks` via `ic coordination list`
- [ ] Release through Intermute; verify `released_at` is set in both `file_reservations` and `coordination_locks`
- [ ] Confirm Intercore and Intermute can write concurrently: run 5 parallel `ic coordination reserve` calls while Intermute is actively writing; verify no `SQLITE_BUSY` errors after 5s timeout

### Before deploying Task 8 (Interlock bridge to `ic`):
- [ ] Confirm `ic coordination check` exits 1 on conflict and 0 on clear (integration test)
- [ ] Verify `pre-edit.sh` hook uses `jq -nc --arg` for all JSON construction (no string interpolation)
- [ ] Run interlock integration tests: `cd interverse/interlock && go test -race ./...`

### Before deploying Task 9 (legacy cleanup):
- [ ] Dual-write has been active for at least 48 hours with agents running
- [ ] Row counts in `file_reservations` and `coordination_locks` are identical for the same time window (run the verification script)
- [ ] Rollback procedure documented: git revert commit hash for Task 9, confirm old Intercore binary tolerates schema v20 (it will — `coordination_locks` is additive, old code ignores it)
- [ ] Confirm `ic` binary version check: old binary with `maxSchemaVersion=19` will refuse to open a v20 DB. A version-gate upgrade procedure must be documented.

---

## Rollback Procedures

### Rolling back Task 1-3 (before dual-write):
- Revert the commit adding `coordination_locks` migration
- Old code ignores the table; new code can be re-enabled by re-applying the migration
- The `coordination_locks` table can be dropped manually: `ic` does not fail if extra tables exist
- **Verdict: fully reversible**

### Rolling back Task 7 (dual-write):
- Remove `--coordination-dual-write` flag from Intermute startup. Intermute reverts to single-write into `file_reservations`
- Existing `coordination_locks` rows are stranded but harmless
- **Verdict: fully reversible by flag change**

### Rolling back Task 8 (Interlock bridge):
- Revert `pre-edit.sh` and `tools.go` to HTTP-based path
- No data migration required
- **Verdict: fully reversible**

### Rolling back Task 9 (legacy cleanup — most dangerous):
- Must revert the commit removing `Reserve()` / `ReleaseReservation()` from Intermute sqlite.go
- Must re-enable `--coordination-dual-write` mode temporarily
- `file_reservations` table still exists in Intermute's DB (was never dropped) — data recovery is possible
- `coordination_locks` data is newer — a reconciliation script is needed to mirror it back to `file_reservations` for any reservations created after cutover
- **Verdict: partially reversible, requires manual reconciliation. Do not proceed without verification script in place.**

---

## Summary Table

| # | Finding | Severity | Exploitability | Task | Blocks Deploy? |
|---|---------|----------|----------------|------|----------------|
| 1 | Shell injection in pre-edit.sh JSON construction | HIGH | DIRECT | 8 | YES — Task 8 |
| 2 | PID reuse attack on named_lock sweep | HIGH | MEDIUM | 5 | YES — Task 5 |
| 3 | Glob pattern DoS — ValidateComplexity not called at entry | HIGH | EASY | 2/3 | YES — Task 3 |
| 4 | Task 9 migration has no defined rollback or go/no-go criteria | HIGH | N/A (ops) | 9 | YES — Task 9 |
| 5 | BEGIN IMMEDIATE via ROLLBACK string breaks sql.Tx abstraction | MEDIUM | MEDIUM | 1/6 | YES — Task 1 |
| 6 | Any agent can release another agent's lock by guessing owner | MEDIUM | EASY | 1 | NO (accept) |
| 7 | git pull --rebase triggered by untrusted inbox message | MEDIUM | LOW | 8 (existing) | NO (document) |
| 8 | Migration guard lower bound (informational, no action) | LOW | LOW | 1 | NO |
| 9 | Bridge skips symlink check on DB open | LOW | LOW | 7 | NO |

**Go/No-Go Verdict:** Do not proceed to Task 3 (CLI) until Findings 3 and 5 are resolved. Do not proceed to Task 5 (sweep) until Finding 2 is resolved. Do not proceed to Task 8 (Interlock bridge) until Finding 1 is resolved. Do not proceed to Task 9 (cleanup) until the rollback procedure and go/no-go criteria in Finding 4 are defined and tested.
