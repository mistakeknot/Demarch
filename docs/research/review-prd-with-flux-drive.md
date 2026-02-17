# Flux-Drive Review: Interspect Canary Monitoring PRD

**Reviewer:** Flux-Drive User & Product Reviewer
**Document:** `/root/projects/Interverse/docs/prds/2026-02-16-interspect-canary-monitoring.md`
**Date:** 2026-02-16
**Primary User:** Claude Code users using Clavain's interspect subsystem for routing override management

---

## Executive Summary

This PRD proposes adding monitoring, detection, and alerting logic to the existing canary table infrastructure for routing overrides in interspect. The primary user is a developer who has allowed interspect to exclude an agent from flux-drive code reviews and wants to know if that exclusion degraded review quality before the change becomes permanent.

**Overall Assessment:** Well-scoped, implementable, and solves a real problem. The PRD demonstrates strong evidence of codebase awareness and realistic constraints. However, there are **P0 clarity gaps** around metric definitions, **P1 missing edge cases** around concurrent overrides and project context, and **P2 UX concerns** around alert fatigue and false positives.

**Verdict:** READY FOR PLANNING with required clarifications (P0 items must be addressed before implementation begins).

---

## P0 Issues (Blocking Implementation)

### P0-1: Ambiguous Metric Definitions

**Finding:** F2 and F3 specify three metrics but don't define them precisely enough for unambiguous implementation.

**Evidence:**
- F2: "override_rate, fp_rate, finding_density" — are these computed per-session or cumulative?
- F3: "computes average of sample metrics" — average across what? All samples? Last N samples?
- F2: "Computes metrics for the current session only (not cumulative)" — this implies per-session snapshots, but then F3's "average" becomes unclear about denominator.

**Impact:** Two implementers would build different systems. One might compute `override_rate` as "overrides in this session divided by 1" (always an integer), another as "overrides in this session divided by number of opportunities" (undefined denominator).

**Fix Required:**
Add a "Metric Definitions" subsection to F2 with SQL-level precision:
```sql
-- override_rate: overrides per session (this session only)
SELECT CAST(COUNT(*) AS REAL) FROM evidence
WHERE session_id = $current_session AND event = 'override';

-- fp_rate: agent_wrong percentage (this session only)
SELECT CAST(SUM(CASE WHEN override_reason = 'agent_wrong' THEN 1 ELSE 0 END) AS REAL) / NULLIF(COUNT(*), 0)
FROM evidence
WHERE session_id = $current_session AND event = 'override';

-- finding_density: total evidence events (this session only)
SELECT COUNT(*) FROM evidence WHERE session_id = $current_session;
```

Then in F3, specify: "For each active canary, computes the arithmetic mean of sample metrics across all samples for that canary (from `canary_samples` table)."

### P0-2: "Session With Zero Evidence Events" Dedup Logic Underspecified

**Finding:** F2 says "Skips sessions with zero evidence events (not a 'flux-drive use')" but also says "Dedup: does not insert duplicate samples for the same (canary_id, session_id)." These interact in an underspecified way.

**Scenario:**
1. Session A starts, interspect hooks load, session_id recorded in `sessions` table
2. User never invokes flux-drive (zero evidence events)
3. Session-end hook runs — skip due to zero evidence
4. Later in the same session, user runs flux-drive (evidence recorded)
5. Session-end hook runs again (can session-end fire twice?) OR user manually triggers canary sample recording

**Questions:**
- Can session-end hook fire multiple times per session?
- If a session initially had zero evidence but later gains evidence, how is the sample backfilled?
- Does "zero evidence events" mean zero total or zero in the evidence table at session-end time?

**Impact:** Implementation might record samples at the wrong time or miss valid sessions.

**Fix Required:**
Clarify in F2:
- "Zero evidence events" means `COUNT(*) FROM evidence WHERE session_id = $sid` returns 0 at the time session-end hook runs.
- If a session has no evidence at session-end, skip sample recording (no backfill logic — this is a session that didn't use flux-drive).
- Session-end hook runs exactly once per session (document assumption or add guard).

### P0-3: Project Context Filtering Undefined

**Finding:** F1 says "Baseline query filters by project (from canary file path context)" but doesn't specify how to extract project from file path or what "project" means in a multi-project monorepo.

**Evidence:**
- The canary table has a `file` column (the routing-overrides.json path)
- The evidence table has a `project` column (from `_interspect_project_name` which is `basename $(git rev-parse --show-toplevel)`)
- A routing override file might be `.claude/routing-overrides.json` (repo root) or `plugins/interflux/.claude/routing-overrides.json` (subproject)

**Scenario:**
- User works in Interverse monorepo (project name = "Interverse")
- Override created for `plugins/interflux/.claude/routing-overrides.json`
- Baseline query needs to filter evidence by project — is that "Interverse" (git root) or "interflux" (subdirectory basename)?

**Impact:** Baseline will mix sessions from different projects, polluting the signal. Or baseline will find zero sessions (because project name doesn't match).

**Fix Required:**
Add to F1 acceptance criteria:
- "Project name is extracted from `evidence.project` column, which is populated by `_interspect_project_name` (git root basename)."
- "All canaries in the same git repo share the same project context, regardless of subdirectory nesting."
- "If a monorepo wants per-subproject canaries, this is a non-goal (cross-project canaries are deferred to v2)."

Or if subproject granularity is intended:
- "Project name for filtering is derived from the override file path's second-to-last directory component (e.g., `plugins/interflux/.claude/routing-overrides.json` → project = 'interflux'). If file is at repo root, project = git root basename."

---

## P1 Issues (Implementation Will Stall or Diverge Without Clarity)

### P1-1: Multiple Active Canaries — Confounding Not Addressed

**Finding:** F3 says "Multiple active canaries evaluated independently with note about confounding" but doesn't specify what the note says, where it appears, or how to detect confounding.

**Evidence:**
- User excludes fd-game-design on Monday (canary 1)
- User excludes fd-performance on Wednesday (canary 2)
- Both canaries monitor the same 20-session window (overlap)
- Canary 1 alerts for increased override_rate — but is that because fd-game-design is gone or because fd-performance is gone?

**Impact:** User gets an alert but has no idea which override to revert. Alert becomes noise.

**Fix Required:**
Add to F4 acceptance criteria:
- "If multiple canaries have overlapping monitoring windows (applied_at timestamps within N days of each other), `/interspect:status` shows a warning: 'Multiple overrides active during this canary's window. Metrics may reflect cumulative impact. Consider reverting one at a time to isolate effect.'"
- "Session-start injection includes canary count: 'Canary alert: 2 routing overrides may have degraded review quality (fd-game-design, fd-performance). Run `/interspect:status` for details.'"

### P1-2: Window Expiry Without Sufficient Samples — Verdict Undefined

**Finding:** F3 says verdict is computed "when `uses_so_far >= window_uses` OR `now > window_expires_at`" but doesn't specify what happens if time expires with only 5 samples (not enough for statistical confidence).

**Scenario:**
- Override applied in a low-activity project
- 14 days pass, only 5 sessions recorded
- Window expires by time, not by use count
- Baseline had 15 sessions, canary has 5 — is that ALERT, PASSED, or INSUFFICIENT_DATA?

**Impact:** Alert on noise or miss real degradation because sample size too small.

**Fix Required:**
Add to F3 acceptance criteria:
- "If window expires by time with fewer than `canary_min_baseline` (default 15) samples, verdict = INSUFFICIENT_DATA (not ALERT or PASSED)."
- "INSUFFICIENT_DATA canaries are surfaced in `/interspect:status` with guidance: 'Monitoring window expired without sufficient data. Override remains active. Consider manual review or extending the window.'"

### P1-3: FP Rate Denominator-Zero Case

**Finding:** F2 specifies `fp_rate` as "agent_wrong overrides / total overrides" but doesn't handle the case where a session has zero overrides.

**Scenario:**
- Session with flux-drive activity but zero override events (all agents agreed)
- fp_rate denominator = 0 → division by zero
- Either skip the sample (but that biases the average toward sessions with overrides) or store NULL (but then F3's "average" is undefined)

**Impact:** Implementation will crash (divide by zero) or produce NaN/NULL samples that break alert logic.

**Fix Required:**
Add to F2 acceptance criteria:
- "If a session has zero override events, `fp_rate` is recorded as NULL (not 0, not NaN)."
- "When computing average in F3, NULL samples are excluded from the mean (denominator = count of non-NULL samples)."
- "If all samples have NULL fp_rate, that metric is skipped in the degradation check (no alert based on fp_rate alone)."

### P1-4: Session-Start Alert Injection — Hook Timing Unclear

**Finding:** F4 specifies session-start injection for alerts but doesn't specify when the verdict is computed (session-start time or session-end of the previous session).

**Evidence:**
- F3 says verdict is computed when `uses_so_far >= window_uses` OR `now > window_expires_at`
- F2 says session-end hook increments `uses_so_far` and records samples
- F4 says session-start hook checks for alerts

**Scenario:**
- Session 20 ends, increments `uses_so_far` to 20 (window complete)
- Session 21 starts immediately after
- Session-start hook runs — should it compute verdict now (adding latency) or should session-end of session 20 have computed it?

**Impact:** Either session-start adds unbounded latency (if verdict computation is expensive) or alerts appear one session late (if session-end computes verdict but doesn't inject).

**Fix Required:**
Add to F2 acceptance criteria:
- "After incrementing `uses_so_far`, if `uses_so_far >= window_uses`, calls `_interspect_evaluate_canary` to compute and store verdict."
- "Session-end hook does NOT inject alerts (no user-facing output) — only updates DB state."

And to F4:
- "Session-start hook reads `canary.status` (computed by previous session-end) and injects alerts if status = 'alert'. No verdict computation in session-start."

---

## P2 Issues (Quality of Life, Defer to Implementation)

### P2-1: Noise Floor of 0.1 May Be Too Low for Small Projects

**Finding:** F5 specifies `canary_noise_floor` default of 0.1, but this may still trigger false alerts in low-activity projects.

**Scenario:**
- Baseline: 2.0 overrides/session (from 15 sessions with 30 total overrides)
- Canary window: 2.1 overrides/session (from 20 sessions with 42 total overrides)
- Absolute diff = 0.1 (at noise floor), percentage diff = 5% (below 20% threshold)
- No alert — but if baseline was 0.5 overrides/session, a 0.1 increase would be 20% (alert)

**Impact:** Noise floor interacts with percentage threshold in unintuitive ways. Alert behavior depends on baseline magnitude.

**Recommendation:** Document the interaction in `/interspect:status` output. Add to F4: "Metric comparison output shows both absolute and percentage change: 'override_rate: 2.1/session (was 2.0, +5%, within threshold).'"

### P2-2: Window Extends to 14 Days But No Early Completion

**Finding:** F3 says window completes when `uses_so_far >= window_uses` OR time expires, but doesn't allow for early completion after sufficient confidence.

**Scenario:**
- Very active project, 20 uses reached in 2 days
- Verdict computed, PASSED
- Canary stays in "active" state for 12 more days (until time expires) even though verdict is already final

**Impact:** Statusline clutter, user confusion ("why is canary still active if it already passed?").

**Recommendation:** Add to F3: "Once verdict is computed (window complete by use count), canary status changes from 'active' to 'completed' (or 'alert'). Time expiry is only checked for canaries that haven't reached use count threshold."

### P2-3: Alert Fatigue — No Dismissal Mechanism

**Finding:** F4 specifies session-start injection for every session with an alert, but no way to acknowledge/dismiss the alert.

**Scenario:**
- Canary alerts on Monday
- User reads the alert, decides to investigate later (not ready to revert)
- Every new session injects the same alert

**Impact:** Alert becomes noise, user trains themselves to ignore it.

**Recommendation:** Add to F4 or defer to non-goals: "Alert injection repeats every session until revert or manual acknowledgment (v2 feature: `/interspect:ack-canary <id>`)."

### P2-4: Success Metric "0 False Positives in 30 Days" Untestable

**Finding:** Success metrics include "Alert accuracy: 0 false-positive alerts in first 30 days" but "false positive" is undefined (an alert is a prediction, not a verifiable fact).

**Evidence:**
- An alert means "metrics degraded per our threshold"
- Whether that degradation represents real quality loss is unobservable (we don't have Galiana ground truth)
- A "false positive" would require the user to label the alert as wrong — but that's subjective

**Impact:** Success metric is unverifiable, blocks retrospective evaluation.

**Recommendation:** Replace with observable proxy: "Alert precision: 100% of alerts triggered result in user action (revert or manual investigation via `/interspect:status`) within 7 days." Or: "Alert noise: <10% of alerts result in immediate revert (suggests alerts are actionable, not noise)."

---

## Edge Cases Analysis

### Covered by PRD

✅ **No baseline (fewer than 15 sessions before override):** F1 specifies NULL baselines, F4 specifies "insufficient baseline" UI
✅ **Multiple overrides:** F3 mentions "note about confounding" (though underspecified, see P1-1)
✅ **Window expiry without reaching use count:** F3 includes `now > window_expires_at` trigger
✅ **Zero evidence sessions:** F2 specifies skip logic

### Missing or Underspecified

❌ **Canary for an override that gets reverted mid-window:**
   - What happens to `uses_so_far` counting and verdict?
   - Recommendation: Add to F3: "If override is reverted (via `/interspect:revert`) before window completes, canary status changes to 'reverted' and verdict computation is skipped. Samples collected so far are preserved for future analysis."

❌ **User manually edits routing-overrides.json (outside interspect):**
   - Canary's `commit_sha` and `file` columns may no longer match HEAD
   - Recommendation: Add to non-goals or F3: "If override file is modified outside interspect (detected by commit_sha mismatch), canary status changes to 'invalidated' and no verdict is computed."

❌ **Session spans multiple projects (multi-root workspace):**
   - Evidence table has `project` column, but how is project determined when session touches multiple repos?
   - Recommendation: Add to F1 or non-goals: "Each canary filters evidence by the project where the override file lives (from `evidence.project` matching git root basename). Multi-project sessions record evidence per-project; only evidence matching the canary's project is counted."

❌ **Canary table grows unbounded (years of historical canaries):**
   - No cleanup/archival logic
   - Recommendation: Defer to non-goals: "Canary retention policy (archive canaries older than 90 days) deferred to v2."

❌ **Clock skew / time zone issues in `window_expires_at` computation:**
   - Expiry is computed as "now + 14 days" using `date -u` (UTC)
   - But session timestamps also use UTC (consistent)
   - Risk: BSD vs GNU date inconsistency (already handled in `_interspect_apply_override_locked` with fallback)
   - Recommendation: Document in F1: "All timestamps use UTC (`date -u`). BSD/GNU date compatibility handled via existing fallback in apply function."

---

## Architectural Concerns with Hook-Based Approach

### Hook Latency Budget

**Concern:** F2 requires session-end hook to:
1. Query active canaries
2. Compute 3 metrics from evidence table (potentially expensive JOIN)
3. Insert sample row
4. Increment `uses_so_far`
5. Conditionally evaluate canary (if window complete)

**Evidence from codebase:**
- Success metric: "Session-end hook adds <500ms for canary sample collection"
- Existing session-end hook (interspect-session-end.sh) only does a single UPDATE query (fast)
- Metric computation involves aggregating evidence table (potentially thousands of rows for long sessions)

**Impact:** If evidence table has 10K rows and 5 active canaries, 5 queries each scanning 10K rows = session-end hangs for 2-5 seconds.

**Mitigation in PRD:** Success metric sets 500ms upper bound (good), but doesn't specify how to achieve it.

**Recommendation:**
- Add to F2 acceptance criteria: "Metric queries use indexed columns (`session_id`, `event`, `override_reason` are already indexed per lib-interspect.sh schema)."
- Add to F2: "If metric computation exceeds 500ms (measured via `EXPLAIN QUERY PLAN`), use background job (fork to temp script, run async, update DB later) instead of blocking session-end."

### Concurrent Session-End Hooks (SQLite WAL Contention)

**Concern:** Multiple Claude Code sessions ending simultaneously = concurrent writes to `canary_samples` and `canary.uses_so_far`.

**Evidence from codebase:**
- DB uses WAL mode (`PRAGMA journal_mode=WAL` in lib-interspect.sh)
- No flock around canary sample writes (flock only used for git operations)
- SQLite WAL allows concurrent reads + single writer, but concurrent writes block

**Impact:** If 3 sessions end within 1 second, session-end hooks serialize at SQLite level → one session waits for others.

**Mitigation in PRD:** None mentioned.

**Recommendation:**
- Add to F2 acceptance criteria: "Canary sample insertion uses SQLite retry logic (3 retries with 100ms backoff) if `SQLITE_BUSY` error occurs."
- Or add to F2: "Sample recording is idempotent (INSERT OR IGNORE on unique(canary_id, session_id)) to prevent duplicates from retries."

### Session-Start Injection Adds Latency

**Concern:** F4 requires session-start hook to query `canary` table for alerts and inject via `additionalContext`.

**Evidence from codebase:**
- Existing session-start hook (hooks/interspect-session.sh) already does DB queries + injection
- Adding canary check = one more SELECT query (fast if indexed)

**Impact:** Minimal — one indexed SELECT on `canary` WHERE `status = 'alert'` is <10ms.

**Recommendation:** No change needed, but document in F4: "Alert check uses index on `canary.status` (already exists per lib-interspect.sh schema)."

---

## Scope Boundary Assessment

### Well-Bounded (Non-Goals Are Clear)

✅ **No auto-revert:** Explicitly deferred, human-in-the-loop preserved
✅ **No Galiana integration:** Deferred to v2, proxy metrics used instead
✅ **No background process:** Hook-based only, no daemon
✅ **No cross-project canaries:** Each project independent
✅ **No ML-based detection:** Percentage-based threshold (simple, deterministic)

### Boundary Risks (Scope Creep Potential)

⚠️ **"Statusline integration" is a non-goal but F4 references it:**
   - F4 says statusline integration is iv-sisi (deferred)
   - But F4 also says "/interspect:status shows canary section"
   - Is `/interspect:status` a command (in scope) or statusline UI (out of scope)?
   - **Clarification needed:** F4 should specify "/interspect:status is a slash command (not statusline UI). Statusline integration (visual indicator in terminal statusline) is deferred to iv-sisi."

⚠️ **"Model override canaries" deferred but F1 mentions "routing (agent exclusion) canaries in v1":**
   - Implies model override canaries might come later
   - But nowhere does the PRD define what a "model override canary" would monitor
   - **Recommendation:** Remove "model override canaries" from non-goals (or add clarifying sentence: "Model override canaries (for GPT-5 fallback overrides) deferred — not yet designed.")

---

## Testability of Acceptance Criteria

### Testable

✅ F1: "New function exists" — unit test
✅ F1: "Computes three metrics" — integration test with fixture data
✅ F2: "New table exists" — schema test
✅ F2: "Dedup logic" — insert same (canary_id, session_id) twice, assert single row
✅ F3: "Verdict logic" — table-driven test with different baseline/sample combinations
✅ F5: "Config fields exist" — JSON schema validation

### Ambiguous (Needs Clarification for Test Design)

⚠️ F1: "Baseline query filters by project (from canary file path context)" — How to set up test fixture? What file path → project mapping?
⚠️ F3: "Multiple active canaries evaluated independently with note about confounding" — What does "note" look like? String match test?
⚠️ F4: "Session-start hook injects warning" — How to test hook output? Mock stdin/stdout?

### Untestable (Success Metrics)

❌ "Alert accuracy: 0 false-positive alerts in first 30 days" — No ground truth, can't verify
✅ "Coverage: 100% of interspect-created overrides have active canaries" — Testable via DB query
✅ "No performance regression: Session-end hook adds <500ms" — Testable via benchmark

---

## User Flow Analysis

### Primary Flow: Override → Monitor → Alert → Revert

**Entry point:** User runs `/interspect:apply <agent>` (or interspect auto-proposes override)

**Steps:**
1. Override applied → canary created with NULL baselines (if <15 sessions) or computed baselines
2. User continues working across 20 sessions over 2 weeks
3. Each session end: sample recorded, `uses_so_far` incremented
4. Session 20 ends: verdict computed, stored in DB
5. Session 21 starts: alert injected "Canary alert: routing override for fd-game-design may have degraded review quality. Run `/interspect:status` for details."
6. User runs `/interspect:status`, sees metric comparison + verdict
7. User decides: `/interspect:revert fd-game-design` OR accept the risk

**Missing states:**
- What if user never runs `/interspect:status`? Alert repeats every session (see P2-3).
- What if user wants to extend monitoring window? Not addressed (defer to non-goals or add to F3).

### Alternative Flow: Monitoring Completes Without Degradation

**Steps:**
1-4. Same as above
5. Session 20 ends: verdict = PASSED
6. Session 21 starts: no alert (status ≠ 'alert')
7. User runs `/interspect:status`, sees "PASSED" verdict
8. Override becomes permanent (no further monitoring)

**Missing transitions:**
- How does user know monitoring completed? No notification (alert only fires on degradation).
- **Recommendation:** Add to F4: "If a canary completes with PASSED verdict in the last 24 hours, session-start injection includes success notice: 'Canary monitoring completed for fd-game-design override (PASSED). No quality degradation detected.'"

### Error Flow: Insufficient Baseline

**Steps:**
1. User applies override in new project (only 8 sessions of history)
2. Canary created with NULL baselines
3. 20 sessions pass, verdict = INSUFFICIENT_BASELINE
4. User runs `/interspect:status`, sees "monitoring (insufficient baseline, collecting data)"
5. User is stuck — no guidance on next action

**Missing recovery path:**
- User can't revert (no alert fired)
- User can't get confidence (no baseline)
- **Recommendation:** Add to F4: "INSUFFICIENT_BASELINE canaries show guidance: 'Not enough historical data to establish baseline. Override remains active. Consider: (a) manual review of recent sessions, (b) revert if uncertain, (c) wait for more data and reapply override.'"

---

## UX-Specific Concerns

### Information Hierarchy — Right Info at Right Time?

✅ **Session-start alert gives immediate action hint:** "Run `/interspect:status` for details or `/interspect:revert <agent>` to undo."
✅ **`/interspect:status` provides full detail:** Metric comparison, sample count, progress bar
⚠️ **No intermediate state visibility:** User can't check "how many sessions until verdict?" without running `/interspect:status` (statusline integration deferred, so this is expected).

**Recommendation:** No change (acceptable for v1, statusline integration will address in v2).

### Error Messages — Actionable Recovery?

✅ **Alert includes revert command:** User knows how to undo
❌ **INSUFFICIENT_BASELINE has no recovery path:** See "Error Flow" above
❌ **EXPIRED_UNUSED has no guidance:** F3 says "EXPIRED_UNUSED" verdict exists but F4 doesn't specify what user sees or what to do next

**Fix Required:** Add to F4: "EXPIRED_UNUSED canaries show: 'Monitoring window expired without flux-drive usage in this project. Override remains active but unmonitored. Run `/interspect:revert <agent>` to undo or `/interspect:extend-canary <id>` to restart monitoring (v2 feature).'"

### Progressive Disclosure — Beginners vs Advanced Users

✅ **Session-start alert is minimal (1 line), full detail behind `/interspect:status`:** Good progressive disclosure
⚠️ **Metric names (override_rate, fp_rate, finding_density) are jargon:** User may not understand what "FP rate increased 25%" means

**Recommendation:** Add to F4: "Metric comparison includes plain-language explanation: 'False-positive rate: 0.35 (was 0.28, +25%) — means 35% of agent findings were overridden as incorrect, up from 28% baseline. Higher FP rate suggests remaining agents may be less accurate.'"

### Default Behavior Quality

✅ **20-use / 14-day window is reasonable default:** Not too short (noisy) or too long (delayed feedback)
✅ **20% degradation threshold with 0.1 noise floor:** Balances sensitivity vs false positives
⚠️ **No way to tune per-override:** All canaries use global confidence.json thresholds (acceptable for v1, per-override tuning is scope creep)

**Recommendation:** No change (acceptable).

---

## Missing Workflows

### Missing: User Wants to Check Canary Status Mid-Window

**Current design:** User runs `/interspect:status` anytime (covered by F4).

**Gap:** What does `/interspect:status` show for an in-progress canary?

**Fix Required:** Add to F4: "Active canaries (window not complete) show: 'monitoring: 12/20 uses (7 days remaining), current metrics: override_rate=2.1 (baseline: 2.0), fp_rate=0.30 (baseline: 0.28), finding_density=8.5 (baseline: 9.0). Metrics are preliminary (not final verdict).'"

### Missing: User Wants to Know Why a Specific Session Triggered a Sample

**Scenario:** User sees canary alert, runs `/interspect:status`, sees 20 samples with varying metrics. Wants to drill into "which session had the spike?"

**Current design:** Samples are aggregated (only average shown), per-session detail not exposed.

**Recommendation:** Defer to non-goals (v2 feature: `/interspect:canary-detail <id>` shows per-session breakdown). Add note to F4: "Sample-level detail (per-session metric breakdown) deferred to v2."

---

## Terminal-Specific Constraints

### 80x24 Behavior

**Concern:** `/interspect:status` output might overflow in minimal terminals.

**Evidence:** F4 specifies: "verdict, sample count / window total, progress bar, metric comparison (baseline vs current), next action hint" — this is 5-7 lines per canary.

**Impact:** If 3 canaries exist, output is 15-21 lines (fits in 80x24). If 10 canaries (edge case), output is 50-70 lines (scrolls off screen).

**Recommendation:** Add to F4: "If more than 5 canaries exist, `/interspect:status` shows first 5 with '[+N more]' hint and guidance to filter by status (e.g., `/interspect:status --alerts-only`)." Or defer filtering to v2.

### Color Fallback

**Concern:** F4 mentions "progress bar" but doesn't specify if it uses color/unicode.

**Recommendation:** Add to F4: "Progress bar uses ASCII characters (`[=====>    ] 12/20`) with no color dependency. ANSI color codes (green for PASSED, red for ALERT) use fallback for NO_COLOR environments."

---

## Product Validation Questions

### Problem Definition — Evidence of Pain?

**Claim:** "Without canary monitoring, overrides are fire-and-forget — 6 downstream features blocked."

**Evidence:** PRD lists 6 blocked beads (iv-rafa, iv-ukct, iv-t1m4, iv-5su3, iv-jo3i, iv-sisi).

**Assessment:** Dependency chain is real (those beads require canary signal), but there's no evidence that **users** are currently suffering from lack of canary monitoring. This is architectural debt (blocked features) not user pain (observable problem).

**Risk:** Building infrastructure before validating user need. What if routing overrides are rarely used? What if users revert overrides manually based on intuition (no monitoring needed)?

**Recommendation:** Add to success metrics: "Usage baseline: ≥5 routing overrides created across ≥3 projects in first 30 days (validates that users actually use overrides enough to need monitoring)."

### Solution Fit — Does This Actually Solve the Problem?

**Problem:** "No way to know if review quality degraded after an exclusion."

**Solution:** Monitor 3 proxy metrics (override rate, FP rate, finding density).

**Gap:** None of these metrics directly measure "review quality." They measure **symptoms** (more overrides, higher FP rate) but not **outcomes** (bugs shipped, PRs rejected post-merge).

**Assessment:** This is explicitly called out in non-goals ("Galiana integration deferred to v2"). Proxy metrics are the MVP. Solution fits the constrained problem ("detect likely degradation" not "measure ground truth quality").

**Recommendation:** No change (acknowledged limitation).

### Alternatives Considered?

**PRD does not discuss alternatives.** For example:
- **Manual review:** User checks `/interspect:status` weekly (no auto-monitoring)
- **Time-based revert:** Overrides auto-expire after 30 days unless user confirms
- **Sampling:** Only monitor 1-in-5 overrides (reduce overhead)

**Recommendation:** Add "Alternatives Considered" section to PRD or defer to brainstorm doc (appears to be in brainstorm, not PRD — acceptable).

### Opportunity Cost

**PRD blocks 6 downstream beads but doesn't quantify user value of those beads.**

**Question:** Is canary monitoring the highest-priority interspect work? Or should effort go to (e.g.) improving agent accuracy to reduce overrides in the first place?

**Recommendation:** This is a planning/roadmap question, not a PRD concern. PRD assumes canary monitoring is prioritized (acceptable).

---

## Summary of Required Changes (Before Implementation)

| ID | Priority | Issue | Required Fix |
|----|----------|-------|--------------|
| P0-1 | Blocking | Metric definitions ambiguous | Add SQL-level metric definitions to F2 |
| P0-2 | Blocking | Zero-evidence dedup underspecified | Clarify skip logic and session-end hook run count in F2 |
| P0-3 | Blocking | Project filtering undefined | Specify project extraction logic in F1 |
| P1-1 | High | Confounding alert text missing | Add confounding warning format to F4 |
| P1-2 | High | Expired window with few samples | Add INSUFFICIENT_DATA verdict to F3 |
| P1-3 | High | FP rate divide-by-zero | Add NULL handling for fp_rate in F2 and F3 |
| P1-4 | High | Verdict computation timing unclear | Specify session-end computes, session-start reads in F2/F4 |

All P2 issues can be deferred to implementation or v2.

---

## Final Recommendation

**SHIP AFTER CLARIFICATIONS.** This PRD is 80% ready. The architecture is sound (hook-based, no background process, fail-safe defaults). The scope is well-bounded (explicit non-goals). The acceptance criteria are mostly testable.

**Before implementation:**
1. Address all P0 issues (add metric definitions, clarify project filtering, specify zero-evidence handling)
2. Address P1-3 and P1-4 (NULL handling for fp_rate, verdict timing)
3. Optional: Address P1-1 and P1-2 (confounding warning, INSUFFICIENT_DATA verdict) — these can be discovered during implementation but are better clarified now

**Implementation confidence:** High (assuming P0 fixes). The existing codebase (`lib-interspect.sh`, evidence collection hooks) provides a solid foundation. The new functions (`_interspect_compute_canary_baseline`, `_interspect_record_canary_sample`, `_interspect_evaluate_canary`) are well-scoped additions.

**User value:** Medium-high (unblocks 6 downstream features, provides safety net for routing overrides). Risk of alert fatigue exists (P2-3) but is acceptable for v1 with manual acknowledgment deferred to v2.

**Testing strategy:** Add integration tests for each feature (baseline computation, sample collection, verdict logic) using SQLite fixture data. Add hook tests using mock stdin JSON. Add performance benchmark for session-end hook (<500ms requirement).

---

## Appendix: User Segment Analysis

**Primary user segment:** Developers using Clavain's interspect subsystem in active projects with flux-drive enabled.

**Estimated segment size:** Small (interspect is a Clavain-internal feature, not public API). Likely <10 users initially (Clavain contributors).

**User journey:**
1. User enables flux-drive (multi-agent code review)
2. Agent fd-game-design produces false positives on non-game code
3. User (or interspect auto-propose) creates routing override to exclude fd-game-design
4. **NEW (this PRD):** Canary monitoring begins automatically
5. User works normally for 20 sessions
6. **NEW:** Alert fires if quality degrades
7. User investigates via `/interspect:status`
8. User decides: revert override OR accept risk

**Value proposition:** "Don't worry about routing overrides breaking your review quality — we'll tell you if it happens."

**Adoption barrier:** User must trust the proxy metrics (override rate, FP rate, finding density) as quality signals. If user doesn't understand metrics, alert becomes noise.

**Mitigation (from PRD):** Plain-language explanations in `/interspect:status` output (recommended in UX section above).

**Harm potential:** False-positive alerts → alert fatigue → user disables canary monitoring. False-negative (no alert when quality actually degraded) → user ships bugs. PRD mitigates first risk (20% threshold + noise floor), second risk is inherent to proxy metrics (deferred to Galiana integration in v2).

---

## Appendix: Flow State Transitions

```
Canary Lifecycle States:
  [Created] → active (baseline computed or NULL)
  active → alert (degradation detected)
  active → completed/PASSED (window complete, no degradation)
  active → INSUFFICIENT_BASELINE (window complete, NULL baseline)
  active → EXPIRED_UNUSED (time expired, uses_so_far=0)
  active → reverted (user runs /interspect:revert mid-window)
  active → invalidated (file edited outside interspect, NOT IN PRD)

  alert → reverted (user acts on alert)
  alert → alert (persists across sessions until user acts)

  PASSED → (terminal state, no further transitions)
  INSUFFICIENT_BASELINE → (terminal state, guidance in /interspect:status)
  EXPIRED_UNUSED → (terminal state, guidance needed, see P-findings)
  reverted → (terminal state)
```

**Missing transitions:** What if user wants to re-monitor after PASSED? (Non-goal, reapply override creates new canary.) What if user wants to extend window after EXPIRED_UNUSED? (Not addressed, see P2 findings.)
