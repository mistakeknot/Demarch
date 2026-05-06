# fd-safety findings — microrouter deferral operationalization plan

**Plan:** `docs/plans/2026-05-06-microrouter-deferral-operationalization.md`
**Script under review:** `scripts/deferral-check.sh` (proposed)
**Hook target:** `.claude/settings.json` SessionStart
**Risk classification:** Medium (new hook with destructive side effect; no new network exposure; no credential handling)

---

## P0 findings

### P0-1 — Exit code 2 from SessionStart hook does NOT block: BLOCKING intent is silently dropped

**Location:** Task 7 (`scripts/deferral-check.sh`, lines with `exit 2`) and Task 8 (hook wiring)

The script is designed to signal a BLOCKING session state by exiting with code 2. The hook command in Task 8 wraps the invocation as:

```
bash -c "cd \"$PROJECT_DIR\" && bash scripts/deferral-check.sh 2>&1 || true"
```

The `|| true` suffix resets the exit code to 0 regardless of what `deferral-check.sh` returns. Claude Code never sees exit 2. This is a compound failure: even if the `|| true` were removed, SessionStart is documented as a non-blocking event. From `/home/mk/.claude/plugin-development.md`:

```
| SessionStart | startup|resume|clear|compact | session_id, source | No (context injection only) |
```

The "Can block?" column is `No`. The interflux fd-safety domain says "exit codes follow the convention (0=allow, 2=block with message, other=passthrough)" — that applies to `PreToolUse`/`UserPromptSubmit`/`Stop` hooks, not SessionStart. Exit 2 from a SessionStart hook is treated as a non-zero exit that goes to stderr at most; it does not gate session entry.

**Impact:** Every piece of the escalation ladder (7-day nag, 14-day BLOCK, deadline BLOCK) described in the PRD and Must-Haves is inert. The hook emits text to stderr that may appear in session context, but it cannot prevent any action. The "active enforcement with teeth" the PRD requires does not exist as implemented.

**Mitigation options:**
1. Change the escalation hook from SessionStart to `UserPromptSubmit`. That event can block. A `UserPromptSubmit` hook that checks deferral state and returns a block response for the first N prompts after the deadline fires with actual teeth.
2. If the intent is advisory-only (nag visible in session context), remove the `exit 2` calls and replace with `exit 0` + stderr output, and update the PRD/Must-Haves to describe the mechanism as advisory rather than blocking.
3. A hybrid: SessionStart for the advisory nag + a dedicated `UserPromptSubmit` hook that fires only after checking a marker file written by the SessionStart hook (see `docs/solutions/patterns/cross-hook-marker-file-coordination-20260308.md`).

### P0-2 — Auto-close fires on partial state when `bd close` fails silently on open children

**Location:** `scripts/deferral-check.sh` deadline-passed branch

The script auto-closes the `.19` epic with:
```bash
bd close sylveste-s3z6.19 --reason "..." 2>/dev/null || true
bd set-state "$BEAD" phase=done 2>/dev/null || true
exit 2
```

The `.19` epic currently has at minimum 4 OPEN children: `Sylveste-906` (P0), `Sylveste-emv` (P0), `Sylveste-jm4` (P0), and `sylveste-s3z6.19.10` (in-progress with 3 open children of its own). The `bd close --help` output shows `--force` is required to "Force close pinned issues or unsatisfied gates." Without `--force`, `bd close sylveste-s3z6.19` will fail with an unsatisfied-gate error when children are open.

The `2>/dev/null || true` swallows that failure silently. `bd set-state phase=done` then succeeds, setting `phase=done` on the `.19.10` bead even though the `.19` epic was never closed.

On the next session start, the hook checks `[[ "$PHASE" == "done" ]] && exit 0` and exits immediately — permanently disabling all future deadline and check-in enforcement. The `.19` epic remains OPEN while the hook believes the situation is resolved.

This is the worst partial-state outcome: the hook runs its destructive side effect path, the destruiction fails, the hook marks itself as complete, and enforcement is silently disabled.

**CLAUDE.md constraint also violated:** CLAUDE.md rule (b) states "closing an epic" is a condition requiring human confirmation before proceeding. The script is planned to auto-close an epic without human action from a SessionStart hook. Even if the mechanism worked, it conflicts with the project's own bead-close policy.

**Mitigation:** Either (a) require `--force` and accept cascade-close of all children (see P1-1 below for that risk), or (b) do not issue `bd close sylveste-s3z6.19` from the hook; instead write a bd note and set a state field that surfaces the deadline miss as a human-attention item, and leave the actual epic close to a human-confirmed `/clavain:route` action. Option (b) aligns with CLAUDE.md's policy and removes the partial-state risk entirely.

---

## P1 findings

### P1-1 — Cascade semantics of `bd close sylveste-s3z6.19` are undefined in the plan

**Location:** Task 7, deadline-passed branch; PRD F3

If `--force` were added and `bd close sylveste-s3z6.19` succeeded, the plan does not document whether that cascades to close all open children. The `.19` epic has 4 open P0-level tracking beads (`Sylveste-906`, `Sylveste-emv`, `Sylveste-jm4`) representing concrete security/safety deficits in the microrouter (privacy inner-quench, circular calibration, ineligible_agents safety floor bypass). Silently closing these via epic cascade would remove them from `bd ready` and `bd blocked` output, making P0 safety work invisible.

The plan's Must-Haves do not mention these three beads or whether they should be addressed before the epic closes. The PRD F3 acceptance criterion says "D2 may still run independently" after auto-close, implying the work is considered abandonable — but the P0 safety beads are not D2 work; they are separate tracking items for exploitable defects.

**Impact:** Auto-close-epic on deadline miss, if it worked, may silently orphan or close 3 open P0 safety defect beads.

**Mitigation:** Before wiring auto-close behavior, explicitly enumerate what happens to `Sylveste-906`, `Sylveste-emv`, and `Sylveste-jm4`. If those beads survive epic close as standalone items, confirm that explicitly in the script or via `--force` semantics documentation.

### P1-2 — `bd close` and `bd set-state` run concurrently with other SessionStart hooks under Dolt

**Location:** Task 8 hook wiring; `.claude/settings.json`

From `/home/mk/.claude/plugin-development.md`: "Multiple hooks on the same event run in parallel." The existing `startup|resume|clear` SessionStart hook already runs `bd stats` and potentially `bd prime`, both of which issue reads against the per-project Dolt server. The proposed new hook issues `bd close` (a write) concurrently.

The project's own `beads-troubleshooting.md` documents that concurrent `bd` invocations against the per-project Dolt DB cause journal corruption: "two concurrent `bd` invocations writing the same per-project Dolt DB simultaneously. The per-project layout doesn't fully serialize independent `bd` CLI processes." The recovery requires either `dolt_gc()` or a full `bd init --force` + restore.

**Impact:** The deadline-passed path, when it fires, runs a write hook in parallel with other read hooks. This is exactly the concurrent-write scenario that previously caused journal corruption (documented as encountered 2026-04-27 in `sylveste-a80e`). The corruption risk is low on any given session start but cumulative over every session that fires near the deadline.

**Mitigation:** Serialize the write path. Either run `bd close`/`bd set-state` synchronously after the other hooks, or use a marker file as an intermediate (SessionStart writes the marker, a PostToolUse or UserPromptSubmit hook acts on it once the session is running and other hooks have finished).

### P1-3 — Hook timeout of 5 seconds is insufficient for `bd close` under Dolt startup latency

**Location:** Task 8, hook JSON entry (`"timeout":5`)

The plan wires the hook with `"timeout":5`. The plugin documentation specifies the default as 60 seconds and the unit is seconds. A `bd close` on an epic involves at minimum: Dolt connection establishment (if the server was killed or sleeping), one write transaction, and a Dolt commit. Under normal conditions this takes 1-3 seconds. After a long laptop sleep or Dolt crash-recovery, the Dolt server must restart, which takes 5-15 seconds before any query is accepted.

If the hook times out mid-`bd close`, the Dolt write is aborted but `bd set-state phase=done` may or may not have run depending on timing. Either outcome leaves inconsistent state.

**Mitigation:** Increase `"timeout"` to at least 30 seconds for the auto-close path, matching the order of magnitude of Dolt recovery time documented in `beads-troubleshooting.md`. Alternatively, separate the read-only advisory path (check-in nag, which should be fast) from the write path (deadline close, which is slow and should run with longer timeout or not from a hook at all).

### P1-4 — Date arithmetic has no DST guard but server is UTC; user laptop runs unknown timezone

**Location:** `scripts/deferral-check.sh` lines computing `TODAY_EPOCH` and `DEADLINE_EPOCH`

The server (`zklw`) runs UTC (confirmed: `timedatectl` shows `Time zone: Etc/UTC`). `date +%Y-%m-%d` on the server is unambiguous.

The risk is if the script is ever run on a developer machine in a DST-observing timezone. On the day of a DST spring-forward, `date -d "$TODAY" +%s` may produce a value that is 23 hours rather than 24 hours past midnight, making "today" computationally identical to "yesterday" for a window of 0-3600 seconds. For a deadline check this is low-stakes (off by one day). For the `(TODAY_EPOCH - CHECK_IN_EPOCH) / 86400` calculation, a DST-shifted day means `DAYS_PAST` could be off by 1, potentially mis-classifying a 13-day overdue check-in as 14+ days and triggering BLOCKING a day early.

This is not exploitable but is a source of unexpected behavior for any contributor running locally on macOS or a non-UTC Linux machine.

**Mitigation:** Export `TZ=UTC` at the top of the script before any `date` calls. One line fix.

### P1-5 — `.claude/settings.json` is committed to a public repo; `scripts/deferral-check.sh` runs on every contributor's session start

**Location:** Task 8; `.gitignore` (settings.json is tracked, settings.local.json is gitignored)

`git ls-files .claude/settings.json` confirms the file is tracked. `git remote -v` confirms the repo is `github.com/mistakeknot/Sylveste`, a public repository. `docs/guide-contributing.md` describes an external-contributor fork+PR workflow.

Any contributor who PRs a change to `scripts/deferral-check.sh` will have that change run on every other contributor's `startup|resume|clear` session start as a `bash` execution. The script currently reads bd state and conditionally runs `bd close`. A malicious or accidentally broken PR to this script runs with full session permissions under `bash` before the user has done anything.

This is the committed-hook trust surface described in CLAUDE.md's "Security: AGENTS.md Trust Boundary" section, extended to shell scripts referenced by `settings.json`.

**Mitigation options:**
1. Move the hook entry from `.claude/settings.json` to `.claude/settings.local.json` (gitignored). Each user manually opts in. This is the lowest-trust-surface option.
2. Keep it in `settings.json` but add a note in CLAUDE.md listing `scripts/deferral-check.sh` as security-relevant, requiring code review from the owner before merge, matching the `AGENTS.md Trust Boundary` policy.
3. Given that this hook is specific to one bead ID (`sylveste-s3z6.19.10`) owned by `arouth1`, a per-user hook in `settings.local.json` is more appropriate than a project-wide committed hook. The bead is not a shared project invariant; it is personal work-tracking for one operator.

---

## P2 findings

### P2-1 — Auto-close fires on first session resume after deadline, with no grace period

**Location:** `scripts/deferral-check.sh` deadline-passed branch; PRD F3

The hook fires on `startup|resume|clear`. If the user's laptop sleeps through 2026-06-30, the first `resume` after waking will trigger the auto-close path immediately. There is no "nag for N days first" behavior between deadline-pass and auto-close — the check-in nag (7-day, 14-day) applies to the check-in date, not the deadline date. Once `TODAY_EPOCH > DEADLINE_EPOCH`, the script jumps directly to `bd close`.

The PRD explicitly chose "close epic" as the auto-revert default because "a deferral that quietly extends is a worse failure mode than a deferral that closes too early." That's a documented, deliberate design choice. The safety concern is whether a multi-day gap between laptop sleeps (e.g., 2 weeks of vacation that happen to straddle 2026-06-30) could result in an auto-close the operator did not intend and cannot easily detect.

**Mitigation:** Given the P0-2 finding (close will fail silently anyway), this is partially moot for the current implementation. If the close mechanism is fixed, consider a 3-7 day grace window between deadline-pass and auto-close. The grace window would surface the BLOCKING stderr message on each session start for those days before acting.

### P2-2 — `bd state` output parsing is fragile; grep against "no .* state set" can match valid content

**Location:** `scripts/deferral-check.sh` lines reading state fields

```bash
CHECK_IN=$(bd state "$BEAD" deferral_check_in 2>/dev/null | grep -v "no .* state set" | head -1)
```

If a state field value itself contains "no" followed by arbitrary text followed by "state set" (e.g., a note value like "no deadline extension state set"), the `grep -v` will incorrectly filter it out, leaving `CHECK_IN` empty and silently disabling the check-in enforcement.

This is unlikely given the specific field names (`deferral_check_in`, `deferral_deadline`) but the pattern is fragile. The correct approach is to check the exit code of `bd state` or parse structured output (`--json` if available) rather than grepping the human-readable "no X state set" message format, which is a UI string that could change across bd versions.

**Mitigation:** Use `bd state "$BEAD" deferral_check_in --json 2>/dev/null` and parse with `jq`, or check `bd state` exit code (non-zero when field is absent) rather than grepping the message text.

### P2-3 — `auto_revert_action` field has no integrity protection; typo or accidental edit disables auto-close

**Location:** Task 6 (`bd set-state auto_revert_action=auto-close-epic`); `scripts/deferral-check.sh`

The script gates auto-close on `[[ "$AUTO_REVERT" == "auto-close-epic" ]]`. Any edit to this field (misspelling, case change, accidental reset) silently disables the auto-close and falls through to the plain BLOCKING branch. This is by design — the field is the human override mechanism. For a single-operator project, this is acceptable.

The finding is filed to document it explicitly: the field is the intentional override, not a security gap. No mitigation required unless the project gains multiple operators who need tamper evidence.

### P2-4 — Commit attribution uses "Claude Opus 4.7 (1M context)" but current active model is claude-sonnet-4-6

**Location:** Task 12 commit message

The plan's commit message template includes `Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>`. The session is powered by `claude-sonnet-4-6` (stated in system env). Recent commits in the repo use the same `Claude Opus 4.7` attribution (e.g., commit `1c0661a0`), so the project has an established pattern of using Opus 4.7 attribution uniformly. However, if this plan is executed by a Sonnet session rather than an Opus session, the attribution is inaccurate.

This is low-stakes (attribution is cosmetic) but worth flagging for auditability. If the project cares about accurate model attribution, the executing agent should substitute its own model ID. If uniformity is the convention (all Claude sessions credited to Opus 4.7), that should be noted in CLAUDE.md or AGENTS.md so future contributors follow it deliberately.

---

## P3 findings

### P3-1 — Bead ID hardcoding is correct scope; no lateral trigger risk

**Location:** `scripts/deferral-check.sh` line `BEAD="sylveste-s3z6.19.10"`

The script hardcodes the single bead ID. A search of `bd search "deferral_deadline"` returns no results, confirming no other beads currently carry this state field. The hardcoding is the right design choice — it limits blast radius to one bead and prevents any accidental lateral triggering from other beads that might coincidentally acquire deferral state. No action required; confirmed safe.

### P3-2 — Leap-second risk is negligible for daily date comparison

The date arithmetic uses `date +%Y-%m-%d` which truncates to calendar day. Leap seconds affect sub-second precision, not day boundaries. The `86400`-second divisor for `DAYS_PAST` calculation could theoretically be off by 1 on a day with a leap second, but the resulting error is at most 1 second on a `86400`-second scale, which rounds to 0 days error. No mitigation needed.

---

## Verdict

NEEDS_ATTENTION — The core blocking mechanism is silently inert (SessionStart cannot block; `|| true` swallows exit 2), and the auto-close path risks partial Dolt state when `bd close` fails on open children while `bd set-state phase=done` succeeds, permanently disabling future enforcement. Two P0 findings must be resolved before the plan is executed.

Key decisions required before execution:
1. Confirm whether the escalation mechanism should use `UserPromptSubmit` (can block) or accept advisory-only semantics and remove `exit 2` calls.
2. Confirm whether auto-close-epic from a hook should be replaced with "surface a notice and require human action via `/clavain:route`" to align with CLAUDE.md's bead-close policy for epics.
3. Address what happens to the 3 open P0 child beads (`Sylveste-906`, `Sylveste-emv`, `Sylveste-jm4`) if the `.19` epic closes.
