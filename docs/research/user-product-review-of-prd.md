# User & Product Review: intercore PRD

**Reviewed:** 2026-02-17
**PRD:** `/root/projects/Interverse/docs/prds/2026-02-17-intercore-state-database.md`
**Reviewer:** Flux-drive (User & Product)

---

## Executive Summary

**Primary Users:** Bash hook authors in Clavain infrastructure
**Job to Be Done:** Safely share ephemeral state across concurrent hook executions without race conditions

**Recommendation:** **Ship with scope reduction**. The core state/sentinel features solve a real, observable pain (TOCTOU races, cleanup chaos). The run tracking layer (F4) is speculative scope creep for v1. The migration strategy is realistic but needs enforcement mechanisms.

---

## 1. CLI Ergonomics for Bash Callers

**Severity: P1 (high-impact findings)**

### 1.1 Command Naming Is Bash-Hostile

```bash
ic state set <key> <scope_id> '<json>'
ic sentinel check <name> <scope_id> --interval=<seconds>
```

**Problem:** Three positional arguments with one in quotes creates shell escaping nightmares. Bash hook authors will see:

```bash
# This will break on any JSON with spaces/quotes
ic state set dispatch $SID '{"goal": "something"}'

# Correct but annoying
ic state set dispatch "$SID" "$(cat <<'EOF'
{"goal": "something"}
EOF
)"
```

**Evidence:** CLAUDE.md explicitly bans heredocs in Bash tool calls because they pollute `settings.local.json` with invalid permission entries. Every hook caller will hit this.

**Recommendation:**
- **Option A:** Accept JSON on stdin: `echo '{"goal": "x"}' | ic state set dispatch $SID`
- **Option B:** Accept file path: `ic state set dispatch $SID @/tmp/payload.json`
- **Option C:** Accept key=value pairs for simple cases: `ic state set dispatch $SID goal=x status=active`

### 1.2 Exit Code Semantics Are Inconsistent

```
ic state get <key> <scope_id>  # exit 1 = not found
ic sentinel check <name> ...    # exit 1 = throttled
```

**Problem:** Exit 1 means "failure" in bash convention. But `sentinel check` returning 1 for "throttled" is not a failure — it's a successful check that returned "no". This will cause confusion in hooks that use `set -e` (fail fast).

**Current usage pattern:**
```bash
if ic sentinel check stop $SID --interval=300; then
  # Allowed, do work
fi
```

**But with `set -e`, a throttled check will abort the script.**

**Recommendation:**
- Exit 0 for success (allowed/found)
- Exit 1 for expected negative (throttled/not found)
- Exit 2+ for errors (DB locked, schema mismatch, etc.)
- Document this clearly as "check semantics, not error semantics"

### 1.3 `--json` Flag for Structured Output Is Underspecified

**Acceptance criteria says:** "Output is plain text by default, `--json` flag for structured output"

**Question:** What does plain text output look like for `ic state list <key>`?

```
scope-id-1
scope-id-2
scope-id-3
```

Or:

```
dispatch  scope-id-1  2026-02-17T10:00:00Z
dispatch  scope-id-2  2026-02-17T11:00:00Z
```

**Recommendation:** Specify both formats in the PRD. Bash callers will use plain text with `while read` loops, so it must be newline-delimited, no headers.

### 1.4 Missing: Bulk Operations

**Scenario:** A hook wants to check 5 sentinels to decide whether to run.

**Current design:**
```bash
ic sentinel check stop $SID --interval=300 || exit 0
ic sentinel check dispatch $SID --interval=60 || exit 0
ic sentinel check sync $SID --interval=120 || exit 0
```

**Problem:** 5 subprocess calls, 5 DB transactions, 5 WAL syncs. On a slow disk this is 50-250ms total latency.

**Recommendation:** Add `ic sentinel check-many <name1> <name2> ...` that does a single transaction and returns space-separated `0 1 0` (allowed, throttled, allowed). Bash can split this with `read`.

---

## 2. Scope Analysis: What's Essential vs Nice-to-Have?

**Severity: P0 (blocking scope issue)**

### 2.1 F4 (Run Tracking) Is Speculative Scope Creep

**Stated problem:** "TOCTOU race conditions in throttle guards, makes cross-session state invisible"

**F4 acceptance criteria:**
- Track orchestration runs, agents, artifacts, phase gates
- `ic run create`, `ic run phase`, `ic agent add`, `ic artifact add`

**Evidence gap:**
- No mention of "runs" or "orchestration" in the Problem section
- No mention of a user asking "what phase is this run in?" or "which agents are active?"
- The problem is about **ephemeral state coordination**, not **run observability**

**Real users of this info:** Not bash hooks. This is for introspection tooling (interline, intermux, or future dashboards).

**Recommendation:** **Move F4 to v2**. The core value is F2 (state) and F3 (sentinels). F4 adds 7 new subcommands and 4 new tables for unvalidated use cases.

**Revised v1 scope:**
- F1: Scaffold + schema (state, sentinels only)
- F2: State operations
- F3: Sentinel operations
- F5: Bash library
- F6: Mutex consolidation
- F7: Migration

**Deferred to v2 (after seeing adoption):**
- F4: Run tracking (only if interline/intermux demand it)

### 2.2 F6 (Mutex Consolidation) Is Low-ROI Admin Work

**Feature:** Reorganize `mkdir` locks under `/tmp/intercore/locks/` with metadata and `ic lock list/stale/clean`.

**Question:** Who is the user?
- Not bash hooks (they still use `mkdir` locks via `lib.sh`)
- Not automated cleanup (a cron job can `find /tmp -type d -mtime +1` equally well)
- Maybe: A human debugging "why is this stuck?"

**But:** The Problem section says TOCTOU races are in **throttle guards** (solved by F3), not mutexes. Mutexes aren't mentioned as a pain point.

**Recommendation:** **Defer F6 to v2** unless there's evidence of mutex-related incidents. Focus v1 on solving the stated problem (temp file chaos + race conditions).

---

## 3. Migration Path: Will Consumers Actually Migrate?

**Severity: P1 (adoption risk)**

### 3.1 Dual-Write Mode Is Realistic But Needs Enforcement

**Good:**
- `--legacy-compat` flag allows gradual rollout
- Per-key toggle (not just global) handles partial migration
- Migration script for bulk import

**Risk:** Hooks will enable dual-write and **never turn it off** because "it's working, don't touch it."

**Evidence:** From MEMORY.md — "cleanup: Review settings.local.json files. Replace specific command text with wildcards." This org accumulates technical debt in config files and doesn't clean up proactively.

**Recommendation:**
- Add `ic compat status` to show which keys are still in legacy mode
- Add `ic compat check <key>` to test if consumers can read the new path (e.g., does interline have the new code deployed?)
- Set a hard deprecation date in the PRD: "Legacy compat will be removed in Q2 2026"
- Emit a warning log on every dual-write: `WARN: legacy compat enabled for 'dispatch', migrate by Q2 2026`

### 3.2 Missing: Consumer Migration Checklist

**Who needs to change code?**
- interline (reads `/tmp/clavain-dispatch-$$.json`)
- interband (writes `~/.interband/interphase/bead/${SID}.json`)
- Clavain hooks (all the `touch /tmp/clavain-stop-$SID` callsites)

**PRD says:** "allowing consumers to migrate at their own pace"

**But doesn't say:**
- Which consumers exist
- What migration work they need to do
- Whether migration is optional (dual-write stays forever?) or mandatory (with a deadline)

**Recommendation:** Add a "Consumer Migration Plan" section:
```markdown
## Consumer Migration Plan

### Phase 1: Dual-Write (2026-02-17 to 2026-03-31)
- [ ] Deploy intercore v1 with `INTERCORE_LEGACY_COMPAT=1`
- [ ] Update interline to read from `ic state get dispatch`
- [ ] Update interband to write to `ic state set bead_phase`
- [ ] Update all hooks to use `lib-intercore.sh` wrappers

### Phase 2: Monitoring (2026-04-01 to 2026-04-30)
- [ ] Run `ic compat status` weekly, track which keys still use legacy
- [ ] Verify no consumers read old temp file paths

### Phase 3: Cutover (2026-05-01)
- [ ] Remove `INTERCORE_LEGACY_COMPAT` flag
- [ ] Delete old temp file writes
- [ ] Remove legacy code from interline/interband
```

### 3.3 "Fail-Safe by Convention" Hides Real Errors

**F5 acceptance criteria:** "All functions follow the 'fail-safe by convention' pattern — errors return 0, never block workflow"

**Example:**
```bash
intercore_state_set dispatch $SID "$json"  # Returns 0 even if DB is corrupted
```

**Problem:** A broken database will silently no-op instead of surfacing the issue. The workflow continues, but state is lost. Debugging this will be hell.

**Real-world scenario:**
- Schema migration fails (new column missing)
- All `ic state set` calls fail with SQL errors
- Bash library returns 0 (fail-safe)
- Hooks run normally, no visible errors
- 3 hours later: "Why isn't interline showing my dispatch status?"

**Recommendation:**
- Distinguish between "DB unavailable" (fail-safe, return 0) and "DB available but broken" (fail-loud, return 1, log error)
- Add `ic health` command that returns 0 if DB is readable and schema is current
- Hooks can call `intercore_available() && ic health` at startup to catch config issues early

---

## 4. Open Questions: Blocking or Deferrable?

**Severity: P2 (planning questions, not blockers)**

### 4.1 DB File Location (Question 1)

**Options:**
- `.clavain/intercore.db` (project-relative)
- `~/.intercore/intercore.db` (global)

**Analysis:**

| Aspect | Project-relative | Global |
|--------|-----------------|--------|
| Session isolation | Natural (each project = separate DB) | Manual (must query by project_path) |
| Cross-project queries | Impossible | Easy |
| Disk usage | N × DB overhead | 1 × DB overhead |
| Backup/sync | Per-project (matches beads) | Global state blob |

**User jobs:**
- Bash hooks: "Store state for this session/project" → Project-relative is clearer
- Introspection tools: "Show all active runs across projects" → Global is easier

**Recommendation:** **Project-relative for v1** (matches mental model of "this project's state"). If cross-project queries become important, add a `ic index` tool that aggregates across projects.

**Not blocking:** Can be decided during F1 implementation based on schema design.

### 4.2 interband Relationship (Question 2)

**Question:** "Does intercore subsume interband, or does interband become a read-through cache/view?"

**Analysis:** This is a **product strategy question**, not a v1 engineering question.

**Recommendation:** **Defer to post-v1 adoption review**. The PRD already says "interband may evolve into a view layer that reads from intercore, but that's a separate decision." Ship intercore, see if it solves the pain, then decide interband's fate.

**Not blocking.**

### 4.3 autopub.lock Classification (Question 3)

**Question:** "Mutex or throttle?"

**Why it matters:** Determines whether autopub uses F3 (sentinels) or F6 (mutex consolidation).

**Recommendation:** **Lookup actual usage, decide in F6/F7 design**. This is a classification task, not a design question. Can be resolved during implementation.

**Not blocking for v1 feature set.**

### 4.4 CGO vs Pure Go SQLite (Question 4)

**Trade-off:**
- `mattn/go-sqlite3`: Faster, requires CGO (complicates cross-compile)
- `modernc.org/sqlite`: Pure Go, slightly slower

**PRD says:** "Performance difference likely negligible for this workload"

**Analysis:** Bash hooks call `ic` as a subprocess, so startup latency dominates. A 2ms vs 5ms query time difference won't matter when subprocess overhead is 10-50ms.

**Recommendation:** **Pure Go (`modernc.org/sqlite`)** for operational simplicity. No CGO means easier builds, easier plugin distribution, no libc version mismatches.

**Not blocking.**

---

## 5. Missing User Flows

**Severity: P2 (missing edge cases, not blockers)**

### 5.1 Concurrent Hook Execution (Happy Path)

**Scenario:**
```
Session A: on-new-message hook fires
Session B: on-new-message hook fires 100ms later
Both check sentinel "stop" (interval=300s)
```

**Expected:**
- Session A: allowed (fires sentinel)
- Session B: throttled (sees sentinel fired 100ms ago)

**Question:** Does the PRD guarantee this? Yes, F3 says "Concurrent calls from different sessions correctly serialize — only one wins."

**Status:** Covered.

### 5.2 Database Locked (Error Path)

**Scenario:**
```
Session A: Long-running transaction (5 seconds)
Session B: Tries to write, gets SQLITE_BUSY
```

**Handling:**
- F1 says `busy_timeout=5s` (default)
- Bash library says "errors return 0, never block"

**Question:** If busy_timeout expires, does `ic` return exit 1 (error) or retry forever?

**Recommendation:** Add acceptance criterion:
- `ic state set` with `--timeout=<seconds>` overrides default busy_timeout
- If timeout expires, return exit 2 (transient error), not exit 1 (permanent error)
- Bash library retries once on exit 2, then returns 0 (fail-safe)

### 5.3 Schema Migration Mid-Flight (Chaos Path)

**Scenario:**
```
Session A: Running hooks with intercore v1.0.0 (schema version 1)
User: Installs intercore v1.1.0 (schema version 2)
Session B: First `ic` call runs migration (adds column)
Session A: Next `ic` call sees new schema, old binary
```

**Question:** Does the old binary detect schema mismatch and fail gracefully?

**Recommendation:** Add to F1:
- `ic` checks `PRAGMA user_version` on every call
- If `user_version > EXPECTED_VERSION`, return exit 3 with message "Schema version 2 detected, but this binary expects version 1. Upgrade to intercore v1.1.0."
- Bash library surfaces this as a loud error (not fail-safe)

### 5.4 Disk Full (Rare But Catastrophic)

**Scenario:** `/tmp` is full (or project disk is full for project-relative DB).

**Current design:** WAL mode writes to `intercore.db-wal`. If disk is full, WAL writes fail.

**Question:** Does `ic` detect this and fail gracefully?

**Recommendation:** Add to F1:
- `ic health` checks for disk space (requires >10MB free)
- On write failure, log clear error: "Disk full, cannot write to WAL"
- Bash library treats this as transient error (fail-safe), but logs to stderr

---

## 6. Value Proposition Clarity

**Severity: P3 (communication issue, not technical)**

### 6.1 Problem Statement Is Data-Backed

**Evidence:** "~15 scattered temp files in `/tmp/`" — specific, measurable.

**Evidence:** "TOCTOU race conditions in throttle guards" — observable failure mode.

**Good:** The problem is not abstract. It names the pain (races, cleanup chaos) and the root cause (temp files).

### 6.2 Success Criteria Are Missing

**PRD says:** "intercore handles ephemeral/session state"

**But doesn't say:**
- How many temp files should be eliminated in v1?
- How many hooks should migrate?
- What's the target MTBF for throttle guards (currently: how many races per week?)

**Recommendation:** Add a "Success Metrics" section:
```markdown
## Success Metrics (Post-Launch)

### Adoption (4 weeks post-launch)
- [ ] 10+ hooks migrated to `lib-intercore.sh`
- [ ] 5+ temp file patterns eliminated
- [ ] interline/interband reading from intercore

### Reliability (8 weeks post-launch)
- [ ] Zero reported TOCTOU races in sentinels
- [ ] <1% of `ic` calls fail due to DB lock timeouts
- [ ] No schema migration failures reported

### Cleanup (12 weeks post-launch)
- [ ] Legacy compat disabled for all keys
- [ ] All temp file writes removed from hooks
```

---

## 7. Discoverability & Help Text

**Severity: P3 (UX polish, not blocking)**

### 7.1 `ic` with No Args Should Be Helpful

**Expected:**
```bash
$ ic
Usage: ic <command> [args]

Commands:
  state      Manage ephemeral state
  sentinel   Throttle checks and once-per-session guards
  run        Track orchestration runs (see 'ic run --help')
  lock       Inspect filesystem mutexes
  version    Show version and schema version
  health     Check database health

Run 'ic <command> --help' for details.
```

**Recommendation:** Add this to F1 acceptance criteria.

### 7.2 Error Messages Should Suggest Fixes

**Bad:**
```
Error: no such table: state
```

**Good:**
```
Error: Schema not initialized. Run 'ic init' to create the database.
```

**Bad:**
```
Error: database is locked
```

**Good:**
```
Error: Database is locked (another process is writing). Retrying for 5s...
[If timeout expires]: Database still locked. Check 'ic lock list' for active processes.
```

**Recommendation:** Add to F1: "All errors include actionable recovery suggestions."

---

## 8. Segmentation: Who Benefits, Who Doesn't?

### Primary Users (High Value)
- **Clavain hook authors** — Direct beneficiaries. Throttle guards become atomic, state becomes queryable.
- **interline/interband maintainers** — Simplified state model, no more temp file parsing.

### Secondary Users (Indirect Value)
- **Debugging humans** — `ic state list`, `ic sentinel list` make state visible instead of scattered across `/tmp`.

### Non-Users (No Value Change)
- **Beads users** — Beads is unchanged. intercore doesn't touch issue tracking.
- **End users of Clavain** — No visible change. This is plumbing.

### Anti-Value (Potential Harm)
- **Hook authors during migration** — Dual-write complexity, risk of bugs if legacy compat is misconfigured.

**Mitigation:** Good docs, clear migration checklist (see 3.2).

---

## 9. Opportunity Cost

**What's not being built if this ships?**

From `git status`:
- `iv-hoqj` (interband hardening) — just closed, no conflict
- Other beads — not visible, assume normal backlog

**Question:** Is "fix TOCTOU races in throttle guards" more urgent than other roadmap items?

**Recommendation:** User should validate this is top priority. If there are zero actual race incidents in the last month, maybe this is premature optimization.

---

## 10. Recommendations Summary

### Ship-Blockers (P0)
1. **Reduce scope:** Move F4 (run tracking) and F6 (mutex consolidation) to v2. Focus v1 on state + sentinels + migration.

### High-Impact Fixes (P1)
2. **CLI ergonomics:** Accept JSON on stdin or from file, not as shell-quoted arg.
3. **Exit codes:** Document check vs error semantics; use exit 2+ for real errors.
4. **Migration enforcement:** Add `ic compat status`, set hard deprecation date, emit warnings.
5. **Fail-safe vs fail-loud:** Distinguish "DB unavailable" (safe) from "DB broken" (loud).

### Planning Clarifications (P2)
6. **DB location:** Default to project-relative; justify if choosing global.
7. **Success metrics:** Add measurable adoption/reliability targets.
8. **Missing flows:** Schema mismatch, disk full, lock timeout — handle gracefully.

### UX Polish (P3)
9. **Help text:** `ic` with no args shows usage. Errors suggest fixes.
10. **Output formats:** Specify plain text format for `ic state list` (newline-delimited, no headers).

---

## Final Verdict

**Problem:** Real and observable (TOCTOU races, temp file chaos).

**Solution:** Architecturally sound (SQLite WAL, atomic sentinels).

**Scope:** Inflated for v1. F4 (run tracking) solves a problem not mentioned in the Problem section. F6 (mutex consolidation) is admin work, not user value.

**Migration:** Realistic with dual-write, but needs enforcement to avoid permanent legacy compat.

**CLI:** Bash-hostile in places (JSON quoting, exit code semantics). Fixable with stdin input and clearer error handling.

**Recommendation:** **Ship with scope reduction (defer F4, F6 to v2) and CLI ergonomics fixes (stdin JSON, exit code clarity).** The core state/sentinel features solve the stated problem. Everything else is speculative.
