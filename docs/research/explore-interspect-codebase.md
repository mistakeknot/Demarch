# Interspect Subsystem Exploration — Canary Monitoring Research

**Date:** 2026-02-16  
**Purpose:** Comprehensive understanding of interspect's existing implementation for canary monitoring brainstorm  
**Scope:** lib-interspect.sh, hooks, commands, tests, DB schema, existing canary references

---

## Executive Summary

Interspect is Clavain's observability-first improvement engine implementing an OODA loop (Observe → Orient → Decide → Act). The canary monitoring system is **fully designed but minimally implemented**. The infrastructure exists (DB schema, library functions, command stubs) but the monitoring logic itself is not yet active. Key finding: canary records are created when routing overrides are applied, but there's no background process or hook that checks them for degradation.

**Implementation status:**
- ✅ **Schema:** `canary` table with all fields (window_uses, baseline_override_rate, status, etc.)
- ✅ **Creation:** Canary records inserted on routing override apply
- ✅ **Display:** `/interspect:status` shows active canaries count
- ✅ **Closure:** Canary status updated on revert
- ❌ **Monitoring:** No active checking of canary windows or baseline comparison
- ❌ **Alerts:** No degradation detection or user notifications

---

## 1. Full lib-interspect.sh Analysis

**Location:** `/root/projects/Interverse/hub/clavain/hooks/lib-interspect.sh` (863 lines)

### 1.1 Core Database Schema

The `canary` table (lines 91-106) tracks post-modification metrics:

```sql
CREATE TABLE canary (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    file TEXT NOT NULL,                      -- target file modified
    commit_sha TEXT NOT NULL,                -- git commit that applied the change
    group_id TEXT,                           -- links related modifications
    applied_at TEXT NOT NULL,                -- ISO 8601 UTC timestamp
    window_uses INTEGER NOT NULL DEFAULT 20, -- uses before verdict (not 5 - updated post-Oracle)
    uses_so_far INTEGER NOT NULL DEFAULT 0,  -- incremented on each flux-drive run
    window_expires_at TEXT,                  -- 14-day fallback (whichever comes first)
    baseline_override_rate REAL,             -- pre-change override rate
    baseline_fp_rate REAL,                   -- pre-change false positive rate
    baseline_finding_density REAL,           -- findings per invocation
    baseline_window TEXT,                    -- JSON: time range, session IDs, N
    status TEXT NOT NULL DEFAULT 'active',   -- active | passed | reverted | expired_human_edit
    verdict_reason TEXT                      -- human-readable verdict
);
```

**Key insight:** The schema supports both **use-based** (20 uses) and **time-based** (14 days) canary windows, whichever expires first. This prevents canaries from staying active indefinitely on low-activity projects.

### 1.2 Evidence and Modifications Tables

**Evidence table** (lines 69-82): Records all override events, agent dispatches, corrections. Fields:
- `session_id`, `seq`, `source` (agent name), `event` (override/agent_dispatch), `override_reason` (agent_wrong/deprioritized/already_fixed)
- `context` (JSON blob), `project`, `project_lang`, `project_type`
- Indexed on session, source, project, event, timestamp

**Modifications table** (lines 108-119): Records all applied changes. Fields:
- `group_id` (groups related changes), `mod_type` (routing/context_injection/prompt_tuning)
- `target_file`, `commit_sha`, `confidence`, `status` (applied/reverted/superseded)
- Cross-referenced with canary via `group_id`

**Sessions table** (lines 84-89): Tracks session lifecycle. NULL `end_ts` after 24 hours = "dark session" (abandoned/crashed).

### 1.3 Routing Override Apply Flow

**Function:** `_interspect_apply_routing_override()` (lines 529-598)

**Pre-validation steps** (before flock):
1. Validate agent name format: `fd-<lowercase-name>` only (SQL injection protection)
2. Validate evidence_ids is JSON array
3. Validate target path (no traversal, must be in allow-list)
4. Write commit message to temp file (no shell injection)

**Locked apply flow** (via `_interspect_apply_override_locked`, lines 602-703):
1. **Read current overrides** (inside flock for TOCTOU safety)
2. **Deduplication check:** If override already exists, update metadata only (no new canary)
3. **Build override JSON** using `jq -n --arg` (no shell interpolation)
4. **Merge and dedup** via `jq unique_by(.agent)`
5. **Atomic write:** temp file + rename pattern
6. **Git commit** with `-F` flag (commit message from file, not arg)
7. **DB inserts inside flock:**
   - Modification record: `tier='persistent'`, `mod_type='routing'`, `confidence=1.0`
   - **Canary record:** window_uses=20, window_expires_at=+14 days, status='active'
8. **Rollback on failure:** unstage + restore working tree

**Exit codes:**
- `0` = success, prints commit SHA + canary reminder
- `1` = validation failure or git commit failure

**Canary creation code** (lines 683-696):
```bash
expires_at=$(date -u -d "+14 days" +%Y-%m-%dT%H:%M:%SZ 2>/dev/null \
    || date -u -v+14d +%Y-%m-%dT%H:%M:%SZ 2>/dev/null)

sqlite3 "$db" "INSERT INTO canary (file, commit_sha, group_id, applied_at, window_uses, window_expires_at, status)
    VALUES ('${filepath}', '${commit_sha}', '${escaped_agent}', '${ts}', 20, '${expires_at}', 'active');"
```

**Critical gap:** Baseline metrics (`baseline_override_rate`, `baseline_fp_rate`, `baseline_finding_density`) are **not computed or inserted**. The schema has the fields, but they're left NULL. This means canaries are created but have nothing to compare against.

### 1.4 Protected Paths Enforcement

**Manifest location:** `.clavain/interspect/protected-paths.json`

Three arrays:
- `protected_paths`: Interspect CANNOT modify (e.g., hooks, lib-interspect.sh itself)
- `modification_allow_list`: Interspect CAN modify (e.g., `.claude/routing-overrides.json`)
- `always_propose`: Requires user approval even in autonomous mode

**Validation functions:**
- `_interspect_is_protected()` — glob matching via bash extended globbing
- `_interspect_is_allowed()` — allow-list check
- `_interspect_validate_target()` — combines both (reject if protected OR not in allow-list)

### 1.5 Confidence Gate (Counting Rules)

**Config:** `.clavain/interspect/confidence.json`  
**Defaults:** 3 sessions, 2 projects/languages, 5 events, 80% agent_wrong

**Function:** `_interspect_classify_pattern()` (lines 304-317)

Returns:
- `"ready"` — all 3 thresholds met (eligible for proposal)
- `"growing"` — 1-2 thresholds met
- `"emerging"` — no thresholds met

**Query helper:** `_interspect_get_classified_patterns()` (lines 321-337) — queries evidence, groups by source/event/reason, classifies each pattern.

### 1.6 Routing Eligibility

**Function:** `_interspect_is_routing_eligible()` (lines 369-415)

Checks (all must pass):
1. Agent name format valid
2. Config loaded
3. Not blacklisted
4. Has override events (total > 0)
5. **agent_wrong percentage >= 80%** (not just "sometimes wrong" — consistently irrelevant)

Returns: `"eligible"` or `"not_eligible:<reason>"`

### 1.7 Git Operation Serialization

**Function:** `_interspect_flock_git()` (lines 709-727)

Uses `flock` on `.clavain/interspect/.git-lock` with 30-second timeout. Prevents concurrent session races on git operations. Critical for multi-session safety.

### 1.8 Secret Detection & Sanitization

**Functions:**
- `_interspect_redact_secrets()` (lines 733-760) — detects/redacts API keys, tokens, passwords, connection strings
- `_interspect_sanitize()` (lines 768-796) — strips ANSI, control chars, truncates to 500 chars, redacts secrets, rejects instruction-like patterns

**Used by:** `_interspect_insert_evidence()` before every DB insert.

### 1.9 Missing Canary Logic

**What exists:**
- Canary record creation on apply
- Schema for baseline metrics and verdict tracking
- Status field and indexes

**What's missing:**
- **Baseline computation:** No code computes `baseline_override_rate`, `baseline_fp_rate`, or `baseline_finding_density` from pre-change evidence
- **Window tracking:** `uses_so_far` is never incremented (would need flux-drive integration or a post-triage hook)
- **Degradation detection:** No comparison of post-change metrics vs baseline
- **Verdict logic:** No automated verdict assignment or status transitions
- **Alerts:** No user notifications when canary window closes or degradation detected

---

## 2. Interspect Hooks

### 2.1 interspect-evidence.sh (PostToolUse)

**Trigger:** After Task tool calls (agent dispatch)  
**Action:** Records `agent_dispatch` events in evidence table  
**Fields:** `subagent_type`, `description` from tool input

**Silent hook:** No output, fail-open (exits 0 on any error).

**Code flow:**
1. Extract session_id from hook JSON
2. Check if tool_name == "Task"
3. Build context JSON with jq
4. Call `_interspect_insert_evidence`

**Relevance to canary:** Evidence feeds pattern detection, but doesn't interact with canary monitoring.

### 2.2 interspect-session.sh (SessionStart)

**Trigger:** Session start  
**Action:** Inserts row into `sessions` table with `start_ts`  
**Silent hook:** No output, fail-open

**Code flow:**
1. Extract session_id
2. Insert: `INSERT OR IGNORE INTO sessions (session_id, start_ts, project)`

**Relevance to canary:** Establishes session tracking for evidence aggregation. Dark sessions (no `end_ts` after 24h) are flagged in health checks.

### 2.3 interspect-session-end.sh (Stop)

**Trigger:** Session end  
**Action:** Updates `sessions` table with `end_ts`  
**Does NOT participate in sentinel protocol:** No JSON output, doesn't block

**Code flow:**
1. Extract session_id
2. Update: `UPDATE sessions SET end_ts = '${TS}' WHERE session_id = '${E_SID}' AND end_ts IS NULL`

**Relevance to canary:** Closes session record for evidence window calculations. Does NOT check or update canaries.

**Critical gap:** This would be the natural place to check active canaries and increment `uses_so_far`, but it doesn't.

---

## 3. Interspect Commands

### 3.1 /interspect (main analysis)

**Purpose:** Detect patterns, classify by counting rules, report readiness  
**Phase:** "Phase 2: Evidence + Proposals" (routing overrides available via propose)

**Report sections:**
1. **Ready patterns:** All 3 thresholds met, eligible for proposals
2. **Growing patterns:** 1-2 thresholds met, shows missing criteria
3. **Emerging patterns:** No thresholds met, watching
4. **Evidence health summary:** Total events, overrides, dispatches, sessions
5. **Recommendations:** Based on data health

**Routing eligibility footer:** Checks routing-eligible patterns, displays count, suggests `/interspect:propose`.

**Canary relevance:** None — this command is about evidence analysis, not canary monitoring.

### 3.2 /interspect:status

**Purpose:** Show current state — sessions, evidence stats, active canaries, modifications

**Query:**
```bash
ACTIVE_CANARIES=$(sqlite3 "$DB" "SELECT COUNT(*) FROM canary WHERE status = 'active';")
ACTIVE_MODS=$(sqlite3 "$DB" "SELECT COUNT(*) FROM modifications WHERE status = 'applied';")
```

**Routing overrides section:**
- Reads `.claude/routing-overrides.json` with shared flock (prevents torn reads)
- Displays override table with agent, action, reason, created, source
- **Should** check canary table for status but doesn't explicitly link them

**Navigation hints:** Points to other commands (/interspect, /evidence, /health, /propose, /revert).

**Gap:** Shows canary count but doesn't display canary details (window progress, baseline vs current, verdict status). This would be valuable UX.

### 3.3 /interspect:evidence

**Purpose:** Detailed evidence view for a specific agent  
**Sections:** Event breakdown, weekly timeline (histogram), recent events, pattern status

**No canary interaction.**

### 3.4 /interspect:correction

**Purpose:** Record manual override signal  
**Flow:**
1. Ask user: agent name, description, override reason (agent_wrong/deprioritized/already_fixed)
2. Insert evidence via `_interspect_insert_evidence`
3. Report total evidence count for agent

**High-quality manual signals** — the primary evidence collection mechanism (PostToolUse hooks can't capture AskUserQuestion responses).

**No canary interaction.**

### 3.5 /interspect:health

**Purpose:** Signal collection diagnostics  
**Checks:** Session tracking, evidence hooks, correction signals, DB health

**Status logic:**
- OK: >= 1 event in last 7 days
- WARN: events exist but none in last 7 days
- INACTIVE: no events ever

**Dark sessions section:** Reports count of sessions with no `end_ts` after 24h.

**No canary health checks** — doesn't report on active canary count, expiring windows, or stalled canaries.

### 3.6 /interspect:propose

**Purpose:** Detect routing-eligible patterns, present proposals  
**Flow:**
1. Get classified patterns (`_interspect_get_classified_patterns`)
2. Filter for "ready" + routing-eligible + not already applied
3. **Cross-cutting agent check:** fd-architecture/quality/safety/correctness show warnings
4. Present multi-select AskUserQuestion with evidence details
5. On approval: call `_interspect_apply_routing_override` for each selected agent

**Canary creation happens here** (via apply function).

**Batch mode:** Multiple agents can be selected and applied together, but each gets its own canary.

### 3.7 /interspect:revert

**Purpose:** Remove routing override, optionally blacklist pattern  
**Flow:**
1. Read routing-overrides.json, check override exists (idempotency)
2. Call `_interspect_revert_override_locked` inside flock:
   - Remove override from JSON with `jq 'del(.overrides[] | select(.agent == $agent))'`
   - Git commit with rollback on failure
   - **Close canary:** `UPDATE canary SET status = 'reverted' WHERE group_id = '${agent}' AND status = 'active'`
3. Ask user: Allow future proposals or blacklist permanently?
4. If blacklist: insert into `blacklist` table

**Canary interaction:** Sets status to 'reverted', but doesn't compute a verdict or check if degradation occurred.

### 3.8 /interspect:unblock

**Purpose:** Remove pattern from blacklist  
**Simple DELETE query:** `DELETE FROM blacklist WHERE pattern_key = '${agent}'`

**No canary interaction.**

---

## 4. Interspect Tests

**File:** `/root/projects/Interverse/hub/clavain/tests/shell/test_interspect_routing.bats` (246 lines)

**Setup:** Creates isolated temp git repo per test, sources lib-interspect.sh, creates minimal config files.

**Test coverage:**

| Area | Tests | Key Assertions |
|------|-------|----------------|
| Blacklist table | 1 | Table exists after ensure_db |
| SQL escape | 3 | Handles quotes, backslashes, control chars |
| Agent name validation | 6 | Accepts valid names, rejects injection/uppercase/non-fd |
| Path validation | 3 | Accepts relative, rejects absolute/traversal |
| Read routing overrides | 3 | Empty for missing, parses valid, handles malformed JSON |
| Write routing overrides | 2 | Round-trip, rejects invalid JSON |
| Override exists check | 2 | Returns 0/1 correctly |
| Routing eligibility | 6 | Blacklist, no events, 80% threshold, below threshold, injection, edge cases |
| Blacklist migration | 1 | ensure_db adds table to existing DB |

**Total:** 27 tests, all focused on library helpers and validation logic.

**No canary tests** — nothing tests canary creation, baseline computation, window tracking, or verdict logic.

**Missing test coverage:**
- Canary record insertion during apply
- Baseline metric computation (when implemented)
- Window expiration logic
- Degradation detection
- Verdict assignment
- Concurrent apply/revert races on canary table

---

## 5. Existing Canary References

### 5.1 AGENTS.md

**Quote (line 167):**
> **Canary monitoring:** After applying an override, Interspect monitors for 14 days or 20 uses. If the override causes problems, run `/interspect:revert` to undo.

**Implication:** User-facing documentation promises canary monitoring, but implementation is incomplete.

**Library functions listed:**
- `_interspect_apply_routing_override()` — "Full apply+commit+canary flow"

### 5.2 Routing Overrides Brainstorm (2026-02-15)

**Key decisions:**

**Canary metrics for routing** (Open Question #2):
> What does "degradation" mean for an exclusion? The excluded agent produces *no* findings (it's not running), so override rate doesn't apply. Candidate metric: "defect escape rate increased after exclusion" via Galiana. Needs Galiana integration to be useful.

**Removal/revert section:**
> **Canary-triggered alert:** If flux-drive's finding quality degrades after an exclusion (e.g., defects slip through that the excluded agent would have caught), the canary alerts. Human reverts manually.

**Commit message format** (lines 99-110):
```
[interspect] Exclude fd-game-design from project reviews

Evidence:
- override (agent_wrong): 5 occurrences across 4 sessions, 3 projects
- Confidence: ready (3/3 counting rules met)
- Risk: Medium → Safety: canary alert

Canary: 20 uses or 14 days
```

**Design intent:** Canaries are meant to detect degradation and alert, but the mechanism isn't specified.

### 5.3 Interspect Design Document (2026-02-15)

**Section 3.6: Canary Monitoring** (lines 274-300 of plan doc):

**Canary record structure:**
```json
{
  "window_uses": 20,
  "uses_so_far": 0,
  "window_expires_at": "2026-03-01T14:32:00Z",
  "baseline_override_rate": 0.4,
  "baseline_fp_rate": 0.3,
  "baseline_finding_density": 2.1,
  "baseline_window": {
    "sessions": ["s1", "s2", "..."],
    "time_range": "2026-01-15 to 2026-02-15",
    "observation_count": 25
  }
}
```

**Window size rationale:**
> With n=5 and a baseline rate of 0.4, a single additional override changes the rate by 20pp — statistically indistinguishable from noise (p=0.317). At n=20, the test has reasonable power.

**Design decisions:**
1. **20 uses or 14 days, whichever comes first** (prevents indefinite canaries on low-activity projects)
2. **Baseline computed from pre-change evidence** (rolling window, last 25 observations)
3. **Statistical power:** n=20 gives reasonable confidence for detecting real degradation

**Missing from implementation:**
- Baseline computation logic
- Statistical test for degradation
- Alert mechanism
- Verdict assignment logic

---

## 6. Implementation Gaps Summary

### What's Fully Implemented

| Component | Status | Location |
|-----------|--------|----------|
| DB schema | ✅ Complete | lib-interspect.sh:91-106 |
| Canary record creation | ✅ Working | lib-interspect.sh:691-696 |
| Canary closure on revert | ✅ Working | commands/interspect-revert.md |
| Canary count display | ✅ Working | commands/interspect-status.md |
| Routing override apply flow | ✅ Working | lib-interspect.sh:529-703 |
| Evidence collection | ✅ Working | hooks/interspect-*.sh |
| Pattern detection | ✅ Working | lib-interspect.sh:321-337 |
| Confidence gate | ✅ Working | lib-interspect.sh:304-317 |

### What's Missing (Canary-Specific)

| Component | Gap | Impact |
|-----------|-----|--------|
| Baseline computation | No code computes baseline metrics from pre-change evidence | Canaries created with NULL baselines, can't detect degradation |
| Window tracking | `uses_so_far` never incremented | Canaries never expire via use-based criterion |
| Degradation detection | No statistical test or comparison logic | No alerts even if metrics degrade |
| Verdict assignment | No automated verdict logic | Canaries stay 'active' forever or until manual revert |
| Alert mechanism | No user notifications | Silent degradation |
| Canary health UI | Status command shows count only | Can't see window progress or verdict reasons |
| Integration with flux-drive | No increment hook on triage run | Use-based window never advances |
| Time-based expiration | No background check for `window_expires_at` | 14-day fallback doesn't work |

### What's Documented But Not Built

| Feature | Documented In | Status |
|---------|---------------|--------|
| Statistical power analysis | Design doc §3.6 | Designed, not implemented |
| Defect escape rate metric | Brainstorm Open Q #2 | Needs Galiana integration |
| Canary-triggered alerts | Brainstorm removal section | Mentioned, not built |
| Baseline window JSON | Design doc canary record | Schema exists, never populated |
| Verdict reasons | Design doc canary record | Field exists, always NULL |

---

## 7. Canary Monitoring Architecture (Inferred Design)

Based on the schema, design docs, and gaps, here's what the **complete** canary system should look like:

### 7.1 Lifecycle Phases

**Phase 1: Baseline Computation (Pre-Apply)**
- Query evidence table for last N observations of the target agent/file
- Compute: override_rate, fp_rate, finding_density
- Store in `baseline_window` JSON with session IDs and time range

**Phase 2: Canary Creation (On Apply)**
- Insert canary record with computed baselines ✅
- Set window_uses=20, uses_so_far=0, status='active' ✅
- Compute window_expires_at = now + 14 days ✅

**Phase 3: Window Tracking (Post-Triage)**
- **Trigger:** After each flux-drive run (PostToolUse hook on flux-drive skill or periodic scan)
- Increment uses_so_far for relevant canaries
- Collect current metrics for the modified agent/file
- Check window closure: uses_so_far >= window_uses OR now >= window_expires_at

**Phase 4: Degradation Detection (On Window Close or Periodic)**
- Compare current metrics vs baseline
- Statistical test: is the difference significant? (e.g., two-proportion z-test for rates)
- Generate verdict: 'passed' (better/neutral) or 'failed' (worse)
- Store verdict_reason with test statistics

**Phase 5: Alert & Action (On Verdict)**
- If passed: set status='passed', log success
- If failed: set status='failed', create user notification, suggest revert
- User can manually revert or accept the change

### 7.2 Integration Points

**Flux-Drive Integration (Missing):**
- After triage step in flux-drive SKILL.md, check for active canaries for agents that ran
- Increment uses_so_far for matching canary records
- Collect metrics: override count, finding count from current session

**Periodic Canary Check (Missing):**
- Cron or Stop hook: scan for canaries with `status='active'`
- Check time-based expiration
- Compute verdict for closed windows
- Generate user-facing report

**Galiana Integration (Future):**
- Defect escape rate as a canary metric for routing overrides
- "Did excluding fd-safety cause more bugs to slip through?"
- Requires Galiana telemetry JSONL parsing

---

## 8. Key Learnings for Brainstorm

### 8.1 What Works Well

1. **Schema design is solid:** All necessary fields exist, properly indexed
2. **Flock serialization:** Git operations are safe from concurrent races
3. **Validation is thorough:** Agent names, paths, JSON format all validated
4. **Deduplication built-in:** unique_by(.agent) prevents duplicate overrides
5. **Rollback on failure:** Git operations rollback cleanly on error

### 8.2 Critical Gaps to Address

1. **Baseline computation is the #1 blocker:** Without baselines, canaries are decorative
2. **No integration with flux-drive:** Use-based windows can't advance
3. **No periodic canary scanner:** Time-based windows silently expire
4. **No statistical test:** Even with metrics, no logic to compare them
5. **No user-facing alerts:** Silent canaries provide no value

### 8.3 Design Tensions

**Routing override canary problem:**
> "The excluded agent produces *no* findings (it's not running), so override rate doesn't apply."

This is a fundamental challenge. For context overlays and prompt tuning, you can compare override rates before/after. For routing exclusions, the agent never runs, so you need a **proxy metric**:

**Option 1:** Defect escape rate (requires Galiana)  
**Option 2:** Overall override rate across remaining agents (did workload shift cause more noise?)  
**Option 3:** Finding density of related agents (did fd-architecture pick up slack when fd-safety was excluded?)  
**Option 4:** Manual check-ins only (canary window expires, ask user "did this help?")

### 8.4 Test Coverage Gaps

No tests for:
- Canary record creation (verify INSERT happens, fields populated)
- Baseline computation (when implemented)
- Window tracking (increment logic)
- Verdict assignment (statistical test)
- Concurrent canary updates (race conditions)

Recommend: Separate bats file `test_interspect_canary.bats` with 20+ tests covering lifecycle.

---

## 9. Recommended Implementation Order (For Brainstorm)

If the brainstorm decides to build out canary monitoring, here's the critical path:

1. **Baseline computation helper** — `_interspect_compute_baseline()` in lib-interspect.sh
   - Query evidence for last N observations
   - Compute override_rate, fp_rate, finding_density
   - Return JSON for baseline_window
   - Call from apply function before INSERT

2. **Metric collection helper** — `_interspect_collect_metrics()` in lib-interspect.sh
   - Query evidence for current window (since applied_at)
   - Compute same metrics as baseline
   - Return JSON

3. **Degradation test** — `_interspect_check_degradation()` in lib-interspect.sh
   - Compare current vs baseline
   - Two-proportion z-test for rates (or chi-square)
   - Return: 'passed' | 'failed' | 'inconclusive' + reason

4. **Canary scanner** — New Stop hook or periodic script
   - Find canaries with status='active'
   - Check expiration (uses_so_far >= window_uses OR now >= window_expires_at)
   - Collect metrics, run degradation test, update status + verdict_reason

5. **Flux-drive integration** — Hook in interflux
   - After triage, check for active canaries
   - Increment uses_so_far for agents that ran
   - Optional: collect finding counts for density metric

6. **User alerts** — `/interspect:canary-report` command
   - Show closed canaries with verdicts
   - Suggest revert for failed canaries
   - Archive old canaries (status != 'active')

7. **Status UI enhancement** — Update `/interspect:status`
   - Table of active canaries with progress (uses_so_far / window_uses, days remaining)
   - Link to detailed view

---

## 10. File Inventory

### Core Implementation
- `hub/clavain/hooks/lib-interspect.sh` — 863 lines, all core logic
- `hub/clavain/hooks/interspect-evidence.sh` — PostToolUse hook, agent dispatch tracking
- `hub/clavain/hooks/interspect-session.sh` — SessionStart hook, session tracking
- `hub/clavain/hooks/interspect-session-end.sh` — Stop hook, session close

### Commands (All in `hub/clavain/commands/`)
- `interspect.md` — Main analysis command (pattern detection + classification)
- `interspect-status.md` — Overview (sessions, evidence, canaries count, mods)
- `interspect-evidence.md` — Detailed agent evidence view
- `interspect-correction.md` — Manual override signal recording
- `interspect-health.md` — Signal collection diagnostics
- `interspect-propose.md` — Routing override proposals
- `interspect-revert.md` — Remove override + blacklist option
- `interspect-unblock.md` — Remove from blacklist

### Tests
- `hub/clavain/tests/shell/test_interspect_routing.bats` — 27 tests, validation + eligibility logic

### Documentation
- `hub/clavain/AGENTS.md` — User-facing canary promise (line 167)
- `hub/clavain/docs/plans/2026-02-15-interspect-design.md` — Full design spec with canary architecture
- `docs/brainstorms/2026-02-15-interspect-routing-overrides-brainstorm.md` — Canary design decisions

### Scripts
- `hub/clavain/scripts/interspect-init.sh` — DB initialization (creates tables, indexes)

---

## Conclusion

The interspect canary system has **excellent infrastructure** (schema, flock safety, validation) but is **functionally incomplete**. Canary records are created but never monitored, baselines are never computed, and verdicts are never assigned. The brainstorm should decide:

1. **Scope:** Build out full canary monitoring or defer to v2?
2. **Proxy metrics:** For routing overrides, what replaces override rate?
3. **Integration:** Flux-drive hook or periodic scanner for window tracking?
4. **User UX:** Active alerts vs passive reports?

The existing codebase provides a strong foundation — the missing pieces are well-defined and self-contained.
