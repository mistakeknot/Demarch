# Synthesis Report: intercore Implementation Plan Review

**Context:** intercore state database plan — SQLite-backed CLI (`ic`) for Clavain hook infrastructure
**Plan:** `docs/plans/2026-02-17-intercore-state-database.md`
**PRD:** `docs/prds/2026-02-17-intercore-state-database.md` (v2)
**Date:** 2026-02-17
**Agents:** 4 launched, 4 completed, 0 failed

---

## Verdict Summary

| Agent | Domain | Status | Summary |
|-------|--------|--------|---------|
| fd-correctness (Julik) | Correctness | NEEDS_ATTENTION | 3 high production-breaking bugs, 2 medium corruption risks, 1 low observability gap |
| fd-architecture | Architecture | NEEDS_ATTENTION | Clean boundaries; false batch sequencing and YAGNI violations need pre-implementation fixes |
| fd-quality | Quality/Style | NEEDS_ATTENTION | 5 blocking issues (bash strict mode, goroutine misuse, missing concurrency tests); approved after fixes |
| fd-safety | Safety/Security | NEEDS_ATTENTION | 3 P0 security/deployment blockers including path traversal and irreversible migration failures |

**Overall Verdict: NEEDS_CHANGES**

All four agents agree the plan has sound fundamentals but must not proceed to implementation without resolving P0/P1 findings. No agent returned a clean verdict.

---

## Findings

### P0 — Must Fix Before Implementation

**P0-1: Path traversal via `--db` flag** — fd-safety
*File: Task 1.3 (CLI framework)*
The `--db` flag accepts arbitrary filesystem paths with no validation. An attacker or buggy hook can write a SQLite file header to `/root/.ssh/authorized_keys`, `/root/.local/bin/ic`, or any other path the process can reach. The plan has zero mitigation.

Required fix: Add `validateDBPath()` enforcing `.db` extension, no `..`, and path must be under CWD or within a `.clavain/` directory. Add adversarial test cases (paths to `/etc/passwd`, SSH keys, `../` escapes).

---

**P0-2: JSON payload depth/size/key limits missing** — fd-safety
*File: Task 3.1 (State CRUD)*
The plan validates `json.Valid()` and `size < 1MB` but imposes no nesting depth, per-key, per-value, or array length limits. A 10,000-level nested object causes stack overflow during `jq` parsing in hooks. Shell injection is possible via unquoted `jq -r` outputs if consumers do not quote variables (e.g., interline's `bd show $bead` where `bead` contains `$(touch /tmp/pwned)`).

Required fix: Add `validatePayload()` with depth limit (20), key length limit (1000), string value limit (100KB), array length limit (10k), and control character filter. Add test cases for each.

---

**P0-3: Irreversible migration failures with no recovery path** — fd-safety
*File: Task 1.2 (Schema migration)*
No pre-migration backup is created. If migration fails (disk full, kill -9, corruption), the user is left with no DB and no documented recovery path. Code downgrade (v2 binary → v1 schema) is blocked by the "exit 2 if version too new" check with no escape hatch (`--downgrade` or `--force-version`).

Required fix: Create timestamped backup (`.backup-YYYYMMDD-HHMMSS`) before migration. Add `ic migrate --downgrade --to=<N>` command. Document recovery procedures in AGENTS.md.

---

### P1 — Must Fix Before Implementation

**P1-1: Sentinel interval=0 WHERE clause has wrong operator precedence** — fd-correctness (HIGH)
*File: Task 2.1 (sentinel.go Check)*
The WHERE clause `(? = 0 AND last_fired = 0 OR ? > 0 AND unixepoch() - last_fired >= ?)` evaluates as `(A AND B) OR (C AND D)` due to missing outer parentheses. If `interval` is accidentally passed as a positive value to a sentinel that should fire only once, the second `OR` clause fires and the sentinel allows a second execution.

Required fix: Add parentheses: `((? = 0 AND last_fired = 0) OR (? > 0 AND unixepoch() - last_fired >= ?))`. Add unit tests for interval=0 second-call throttle and the first-call regression.

---

**P1-2: SetMaxOpenConns(1) specified but never wired** — fd-correctness (HIGH)
*File: Task 1.2 (db.go Open)*
The plan states `SetMaxOpenConns(1)` is required but shows no code location where it is applied. Without it, `database/sql` opens a second connection during `busy_timeout` retry, and the CTE+RETURNING sentinel pattern can allow two concurrent callers to both receive "allowed" due to WAL checkpoint timing.

Required fix: Add `sqlDB.SetMaxOpenConns(1)` immediately after `sql.Open()` in `Open()`. Add test: `db.Stats().MaxOpenConns == 1` after `Open()`.

---

**P1-3: TTL computation mixes SQL function and Go arithmetic unsafely** — fd-correctness (HIGH)
*File: Task 3.1 (state Set)*
The plan implies `expires_at = unixepoch() + ttl.Seconds()` but `ttl.Seconds()` is `float64` (e.g., `1.5s`). SQLite returns REAL when adding a float to an integer, breaking the `INTEGER` column type. The plan is ambiguous about whether this is SQL or Go arithmetic.

Required fix: Compute `expires_at` entirely in Go: `time.Now().Unix() + int64(ttl.Seconds())`. Add comment in schema.sql: `-- computed in Go, not SQL`. Add unit test: TTL of 1500ms produces `expires_at` truncated to 1 second.

---

**P1-4: Auto-prune goroutine will not execute in CLI context** — fd-correctness (LOW) / fd-quality (BLOCKING)
*File: Task 2.2 (sentinel auto-prune)*
Two agents independently flagged this. A goroutine spawned in a CLI command is killed when the main goroutine exits — the goroutine dies before the DELETE runs. Additionally, errors are swallowed, hiding DB corruption signals.

Required fix (convergent recommendation): Run prune in the same transaction as the sentinel check (adds <1ms). Log failures to stderr but do not abort the sentinel check. (fd-correctness suggests same-tx; fd-quality suggests synchronous deferred transaction — either resolves the goroutine issue.)

---

**P1-5: `intercore_available()` returns wrong exit code when binary absent** — fd-safety
*File: Task 4.1 (lib-intercore.sh)*
PRD specifies: "binary not found = fail-safe (return 0)". Current implementation returns `1` (fail-loud) when `command -v ic` returns empty. This blocks every hook on machines without `ic` during rollout, violating the non-blocking design requirement.

Required fix: Return 0 when binary not found; return 1 only when binary exists but `ic health` fails.

---

**P1-6: Schema migration TOCTOU race when schema check is outside transaction** — fd-correctness (MEDIUM) / fd-safety (HIGH)
*File: Task 1.2 (Migrate)*
Two agents flagged the same root cause with different framing. If the `PRAGMA user_version` check is read before `BEGIN IMMEDIATE`, two concurrent `ic init` processes can both see version 0, both acquire the lock sequentially, and both attempt to apply schema. Currently safe via `IF NOT EXISTS`, but any future `ALTER TABLE` migration will fail for the second process.

Required fix: Read `user_version` inside the `BEGIN IMMEDIATE` (or `LevelSerializable`) transaction. Add concurrency test: 10 goroutines calling `Migrate()` on the same DB — all succeed, version = 1.

---

**P1-7: Bash library missing strict-mode guidance and unsafe `echo "$json" |` pattern** — fd-quality (BLOCKING)
*File: Task 4.1 (lib-intercore.sh)*
Sourced bash libraries must not use `set -e` themselves (they exit the parent shell), but the plan provides no header comment explaining this. The `echo "$json" |` pattern is less safe than `printf '%s\n' "$json" |` for payloads containing null bytes or leading hyphens. `_INTERCORE_BIN` uses a non-standard underscore-uppercase naming convention.

Required fix: Add header comment explaining sourcing semantics. Use `printf '%s\n'`. Rename to `INTERCORE_BIN` or `_intercore_bin` per bash convention. Add `shellcheck` pass requirement to Task 4.1 acceptance criteria.

---

**P1-8: Unsafe `touch` pattern in MIGRATION.md example** — fd-safety
*File: Task 5.3 (example hook migration)*
The example migration code uses `touch "$SENTINEL"`, which is vulnerable to symlink attacks (attacker races to create a symlink before `touch` runs). This pattern is already documented as insecure in the existing codebase (`safety-review-of-f3-f4.md`) and will be copy-pasted by hook authors.

Required fix: Replace `touch` with `mkdir` (atomic `O_EXCL`) in all migration examples. Add a "Security Notes" section to MIGRATION.md documenting why `touch` is unsafe.

---

### P2 — Should Fix (Recommended)

**P2-1: Read-fallback migration assumes atomic consumer switchover** — fd-correctness (MEDIUM) / fd-safety (MEDIUM)
*File: Task 5.3 (read-fallback strategy)*
Two agents flagged the dual-writer risk during migration. During the window when old hooks write temp files and new hooks write to DB, a consumer falling back from DB to file can read stale state (phase flip-flop). Also: stale legacy temp files left from previous sessions will incorrectly gate hooks after migration because `intercore_available` returns false and the file is present.

Recommendation: Specify a cleanup step (delete all `/tmp/clavain-*` files) before enabling read-fallback. Add `ic compat status` staleness detection. If dual-write is not adopted, document the migration window constraint explicitly (all hooks must upgrade before any consumer switches to read-fallback).

---

**P2-2: `intercore_sentinel_check_many` speculative function with no CLI backing** — fd-architecture (CRITICAL by their rubric)
*File: Task 4.1 (lib-intercore.sh)*
The bash library includes `intercore_sentinel_check_many` which parses `name:scope:interval` tuples and loops over them — but the CLI has no `check-batch` subcommand. The function still spawns one `ic` process per sentinel (no actual batching) and introduces a colon-delimited format that no consumer uses.

Recommendation: Remove from initial library. Add `ic sentinel check-batch` CLI command only if profiling proves subprocess overhead is material.

---

**P2-3: Batch structure forces false sequencing between independent features** — fd-architecture
*File: Batch 2/3 ordering*
The plan sequences Batch 2 (sentinels) → Batch 3 (state) → Batch 4 (bash library). But state and sentinels are fully independent — they share only the DB handle and schema file. This delays state operations unnecessarily if sentinel work encounters complexity.

Recommendation: Restructure to allow parallel tracks (Batch 2a: sentinels, Batch 2b: state). Interleave one real consumer migration into each track to validate assumptions before the bash library is written.

---

**P2-4: `2>/dev/null` in `intercore_state_set` suppresses structural errors** — fd-architecture / fd-quality
*File: Task 4.1 (lib-intercore.sh)*
The bash library uses `2>/dev/null` on write operations, which suppresses both expected failures (write during unavailability) and structural errors (DB corruption, schema mismatch). The fail-safe/fail-loud distinction is lost.

Recommendation: Use `|| return 0` to swallow return codes but let structural errors propagate to stderr.

---

**P2-5: `.clavain/` directory creation has no symlink check** — fd-safety
*File: Task 1.2 (`Open()` + `Migrate()`)*
`os.MkdirAll` does not detect if `.clavain/` is a symlink to `/etc/`. An attacker who pre-creates the symlink redirects DB writes to the target directory.

Recommendation: Use `os.Lstat` to detect symlinks before `MkdirAll`. Reject if `.clavain` is a symlink.

---

### P3 / IMP — Nice-to-Have

**IMP-1: No benchmark for 50ms P99 performance budget** — fd-quality (MEDIUM)
PRD commits to 50ms P99; no benchmark task is specified. Add `db_bench_test.go` measuring state get/set and sentinel check at 10k existing rows.

**IMP-2: Schema version tracking uses two mechanisms** — fd-quality (MEDIUM)
Both `PRAGMA user_version` and a `schema_version` table are mentioned. Use only `PRAGMA user_version` for v1.

**IMP-3: Centralize schema version check in `db.Open()`** — fd-architecture
Current plan scatters the "is DB migrated?" check across subcommands. Move to `Open()`, return `ErrSchemaVersionTooNew` / `ErrNotMigrated`.

**IMP-4: Replace Task 4.2 integration test with hook simulation test** — fd-architecture
Current test re-implements CLI tests in bash. A hook simulation test that sources `lib-intercore.sh` and validates fail-safe behavior tests the actual consumption path.

**IMP-5: Add `ic state delete <key> <scope_id>` command** — fd-architecture (LOW)
No per-key delete command exists; only bulk prune. Needed for testing and manual state reset.

**IMP-6: Table-driven test structure not specified** — fd-quality (BLOCKING by their rubric)
No test structure example is given. Implementer may write 10 separate test functions instead of table-driven. Add example structure to Task 2.1 and 3.1 acceptance criteria.

**IMP-7: Add rollback guidance and backup/restore docs to AGENTS.md** — fd-quality / fd-safety
Document: pre-migration backup restore, schema downgrade (`ic migrate --downgrade`), WAL recovery, sentinel reset, DB corruption recovery steps.

---

## Conflicts

**None.** All four agents agree on the severity of P0/P1 findings. Where multiple agents flagged the same issue (auto-prune goroutine, migration TOCTOU, read-fallback migration), their recommended fixes converge on the same solution.

The only framing difference: fd-architecture rates the batch reordering as "Critical (Fix Before Implementation)" while fd-quality does not mention it. This is a scope difference, not a conflict — architecture reviews batch structure, quality reviews code patterns.

---

## Cross-Agent Convergence

| Issue | Agents | Convergence |
|-------|--------|-------------|
| Auto-prune goroutine unsafe | fd-correctness, fd-quality | 2/4 — same root cause, same fix |
| Migration TOCTOU race | fd-correctness, fd-safety | 2/4 — same race, same isolation fix |
| Read-fallback migration risk | fd-correctness, fd-safety | 2/4 — same divergence scenario |
| `intercore_available()` return code bug | fd-safety, fd-architecture (stderr) | 2/4 — related but distinct aspects |
| Bash library stderr suppression | fd-architecture, fd-quality | 2/4 — same `2>/dev/null` issue |
| `sentinel_check_many` YAGNI | fd-architecture, fd-quality (implied) | 2/4 |

---

## Summary

**Validation:** 4/4 agents valid
**Verdict:** needs-changes
**Gate:** FAIL
**P0:** 3 | **P1:** 8 | **P2:** 5 | **IMP:** 7
**Conflicts:** none

The intercore plan has a sound architecture, correct schema design, and appropriate WAL/CTE patterns. It does not proceed to implementation until:

1. Path traversal protection on `--db` flag (P0-1)
2. JSON depth/size/key validation (P0-2)
3. Pre-migration backup and `--downgrade` escape hatch (P0-3)
4. Sentinel WHERE clause parenthesization (P1-1)
5. `SetMaxOpenConns(1)` wired in `Open()` (P1-2)
6. TTL computation in Go, not SQL (P1-3)
7. Auto-prune goroutine replaced with synchronous in-tx delete (P1-4)
8. `intercore_available()` fail-safe return code (P1-5)
9. Migration schema-check inside transaction (P1-6)
10. Bash library strict-mode header and `printf` pattern (P1-7)
11. `touch` replaced with `mkdir` in MIGRATION.md examples (P1-8)

Estimated rework: 3-4 hours to update the plan document; implementation time unchanged (most fixes are single-line or additive).

---

## Files

- fd-correctness report: `docs/research/review-intercore-plan-correctness.md`
- fd-architecture report: `docs/research/review-intercore-plan-architecture.md`
- fd-quality report: `docs/research/review-intercore-plan-quality.md`
- fd-safety report: `docs/research/review-intercore-plan-safety.md`
- Target plan: `docs/plans/2026-02-17-intercore-state-database.md`
