# Interspect Canary Monitoring (iv-cylo)

**Bead:** iv-cylo
**Phase:** brainstorm (as of 2026-02-16T20:00:29Z)
**Date:** 2026-02-16
**Status:** Brainstorm
**Blocks:** iv-rafa (meta-learning), iv-ukct (revert command), iv-t1m4 (prompt tuning), iv-5su3 (autonomous mode), iv-jo3i (verdict engine), iv-sisi (statusline integration)

---

## What We're Building

Active canary monitoring for routing overrides. When interspect excludes an agent from flux-drive triage, a canary record is created (this already works). What's missing: the monitoring logic that detects degradation and alerts the user.

**Scope:** Three metrics, rolling baselines, window-based monitoring, alert on degradation. NO auto-revert — human triggers revert manually via `/interspect:revert`.

## What Already Exists

### Canary Table Schema (lib-interspect.sh)

```sql
CREATE TABLE IF NOT EXISTS canary (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    file TEXT NOT NULL,
    commit_sha TEXT NOT NULL,
    group_id TEXT,                    -- agent name (e.g., "fd-game-design")
    applied_at TEXT NOT NULL,
    window_uses INTEGER NOT NULL DEFAULT 20,
    uses_so_far INTEGER NOT NULL DEFAULT 0,
    window_expires_at TEXT,
    baseline_override_rate REAL,      -- NULL — never computed
    baseline_fp_rate REAL,            -- NULL — never computed
    baseline_finding_density REAL,    -- NULL — never computed
    baseline_window TEXT,             -- NULL — never computed
    status TEXT NOT NULL DEFAULT 'active',
    verdict_reason TEXT               -- NULL — never set
);
```

### Canary Record Creation (in `_interspect_apply_override_locked`)

When an override is applied, a canary record is inserted with:
- `window_uses = 20`
- `window_expires_at = now + 14 days`
- `status = 'active'`
- All baseline columns NULL
- `uses_so_far = 0`

### What's NOT Implemented

1. **Baseline computation** — No function computes the three baseline metrics from historical evidence
2. **Use counting** — `uses_so_far` is never incremented (no hook updates it)
3. **Metric collection** — No function collects post-override metrics for comparison
4. **Degradation detection** — No statistical comparison of baseline vs current
5. **Alert generation** — No output to `/interspect:status` or statusline
6. **Window expiration** — No check for time-based expiry
7. **Verdict recording** — `verdict_reason` is never written

## Why This Approach

### Observable Metrics for Absent Agents

The fundamental challenge: an excluded agent produces no findings. We can't measure what it *would have* caught. Instead, we measure **proxy signals** that suggest the exclusion may have hurt quality:

1. **Override rate** (overrides/session): After excluding fd-game-design, are users overriding *other* agents more frequently? An increase suggests remaining agents are producing findings the excluded one would have caught differently, or that review quality shifted.

2. **FP rate** (overrides with `agent_wrong` / total overrides): If FP rate across remaining agents increases after an exclusion, it may indicate the excluded agent was providing complementary coverage that kept other agents' findings relevant.

3. **Finding density** (total corrections recorded per session): A significant drop in total corrections could mean the excluded agent was the primary contributor and its absence changes the review dynamic.

### Window-Based Monitoring

- **20-use window OR 14-day expiry** (whichever comes first)
- Baseline computed from the last 20 sessions *before* the override was applied (requires min 15 observations)
- If fewer than 15 prior sessions, canary starts without baseline → "monitoring: insufficient baseline, collecting data"
- Window counts "uses" = sessions where flux-drive ran (not all sessions — some may be in projects without the override)

### Alert Threshold

The bead description says "ALERT on degradation" without specifying a threshold. Design choices:

**Option A: Percentage-based threshold (simple)**
- Alert if any metric degrades by >20% relative to baseline
- Pro: Easy to understand, easy to implement
- Con: Small sample sizes make 20% volatile (20 sessions is borderline)

**Option B: Standard deviation threshold (statistical)**
- Alert if any metric exceeds baseline + 1.5σ (where σ is computed from the baseline window)
- Pro: Accounts for natural variance
- Con: Needs more data points for σ to be meaningful, complex for bash

**Option C: Simple count threshold (pragmatic)**
- Alert if override rate in the canary window is ≥20% higher than baseline (absolute, not relative)
- Alert if any metric moves in the "worse" direction by a configurable margin
- Pro: Most practical for shell-based implementation, deterministic
- Con: Less statistically rigorous

**Recommendation: Option A with a floor.** Alert if metric degrades by >20% relative to baseline, with a floor of absolute change ≥0.1 (to avoid alerting on noise like 0.05→0.07). This is 80% of the safety with 20% of the complexity, matching the bead's philosophy.

### Where Monitoring Runs

**Option 1: Session-end hook (incremental)**
- At session end, check if any active canaries exist
- If so, compute current metrics for this session, increment `uses_so_far`, compare against baseline
- Pro: Real-time, catches degradation fast
- Con: Adds latency to session teardown, needs to query evidence within the session

**Option 2: `/interspect:status` (on-demand)**
- When user runs `/interspect:status`, compute canary verdicts
- Pro: No hook overhead, user pulls when ready
- Con: User might forget, degradation goes unnoticed

**Option 3: Session-start hook (check + nudge)**
- At session start, check active canaries, compute current metrics if window is filling
- If degradation detected, inject a warning via `additionalContext`
- Pro: User sees alerts naturally at session start
- Con: Adds startup latency

**Recommendation: Hybrid of 1 + 3.**
- **Session-end hook**: Increment `uses_so_far`, compute per-session metrics, store in a new `canary_samples` table
- **Session-start hook**: Check for active canaries with verdict. If ALERT, inject warning into session context
- **`/interspect:status`**: Always shows full canary detail on demand

### Baseline Computation

The baseline must be computed at override-apply time (snapshot of "before"). Currently, the apply function creates the canary record but leaves baselines NULL.

**When to compute:** Inside `_interspect_apply_override_locked`, after the git commit succeeds and before the canary INSERT. Query the last 20 sessions (min 15) and compute:

```sql
-- Override rate: overrides per session
SELECT CAST(COUNT(*) AS REAL) / COUNT(DISTINCT session_id)
FROM evidence
WHERE event = 'override'
AND ts < '{apply_ts}'
AND session_id IN (
    SELECT session_id FROM sessions
    ORDER BY start_ts DESC LIMIT 20
);

-- FP rate: agent_wrong / total overrides
SELECT CAST(SUM(CASE WHEN override_reason = 'agent_wrong' THEN 1 ELSE 0 END) AS REAL) / COUNT(*)
FROM evidence
WHERE event = 'override'
AND ts < '{apply_ts}'
AND session_id IN (
    SELECT session_id FROM sessions
    ORDER BY start_ts DESC LIMIT 20
);

-- Finding density: total evidence events per session
SELECT CAST(COUNT(*) AS REAL) / COUNT(DISTINCT session_id)
FROM evidence
WHERE ts < '{apply_ts}'
AND session_id IN (
    SELECT session_id FROM sessions
    ORDER BY start_ts DESC LIMIT 20
);
```

Store these + the window boundaries in `baseline_override_rate`, `baseline_fp_rate`, `baseline_finding_density`, `baseline_window`.

### Canary Samples Table

Need a new table to store per-session metric snapshots during the canary window:

```sql
CREATE TABLE IF NOT EXISTS canary_samples (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    canary_id INTEGER NOT NULL REFERENCES canary(id),
    session_id TEXT NOT NULL,
    ts TEXT NOT NULL,
    override_rate REAL,
    fp_rate REAL,
    finding_density REAL
);
```

This avoids recomputing metrics from raw evidence every time — samples are immutable snapshots.

### Verdict Logic

After 20 uses (or 14-day expiry), compute verdict:

```
For each metric (override_rate, fp_rate, finding_density):
  current_avg = AVG(canary_samples.metric) for this canary
  baseline = canary.baseline_metric

  if baseline is NULL:
    verdict = "INSUFFICIENT_BASELINE"
  elif abs(current_avg - baseline) < 0.1:
    verdict = "PASSED" (within noise floor)
  elif current_avg > baseline * 1.2:
    verdict = "ALERT" (degraded by >20%)
  else:
    verdict = "PASSED"
```

Final verdict = worst across all three metrics. Store in `canary.status` and `canary.verdict_reason`.

### Alert Surface

1. **`/interspect:status`** — Shows canary section with verdict, sample count, progress
2. **Session-start injection** — If any canary has `status = 'alert'`, inject: "⚠️ Canary alert: routing override for {agent} may have degraded review quality. Run `/interspect:status` for details or `/interspect:revert {agent}` to undo."
3. **Statusline** (iv-sisi, downstream) — Show canary icon when alerts exist

### Edge Cases

1. **No sessions before override** — Baseline is NULL. Canary status = "monitoring (no baseline)". Still collects samples for future comparison if override is reapplied.

2. **Override reverted during canary window** — Status set to 'reverted' by revert command (already implemented). No verdict computed.

3. **Multiple overrides in quick succession** — Each gets its own canary. Metrics reflect cumulative state (all overrides active). Alert for one canary might be caused by a different override. Verdict includes note: "Multiple overrides active during monitoring — individual impact unclear."

4. **Project with no flux-drive usage during window** — `uses_so_far` stays 0. Window expires by time. Verdict = "EXPIRED_UNUSED". No alert.

5. **Session spans multiple projects** — Evidence is tagged per-project. Canary queries filter by project.

## Key Decisions

### What's a "use"?

A flux-drive "use" = a session where the evidence table has at least one `agent_dispatch` event AND the session's project matches the canary's project (inferred from the override file path).

**Simpler alternative:** Count every session end as a use regardless. This over-counts but is simpler and still provides a useful signal. The 14-day time bound prevents over-counting from mattering too much.

**Recommendation:** Count sessions with at least one evidence event. This is a reasonable proxy for "active flux-drive session" without needing flux-drive to emit a specific signal.

### Baseline Window Size

The bead says "rolling baseline from last 20 uses (min 15 observations)." This means:
- Look at the last 20 sessions before the override was applied
- If fewer than 15 exist, baseline is NULL (insufficient data)
- The 20/15 numbers are configurable via confidence.json

### Alert Threshold Configuration

Add to confidence.json:
```json
{
  "canary_window_uses": 20,
  "canary_window_days": 14,
  "canary_min_baseline": 15,
  "canary_alert_pct": 20,
  "canary_noise_floor": 0.1
}
```

## Implementation Components

1. **Baseline computation** — New function `_interspect_compute_canary_baseline` in lib-interspect.sh
2. **Baseline storage** — Update `_interspect_apply_override_locked` to call baseline computation before canary INSERT
3. **canary_samples table** — New table in DB schema + migration
4. **Sample collection** — New function `_interspect_record_canary_sample` called from session-end hook
5. **Verdict computation** — New function `_interspect_evaluate_canary` that compares samples vs baseline
6. **Window management** — New function `_interspect_check_canary_expiry` for time-based expiry
7. **Alert injection** — Update session-start hook to check for active alerts
8. **Status display** — Update `/interspect:status` to show canary details
9. **Tests** — Bats tests for all new functions

## What's NOT in Scope

- **Auto-revert** — Human triggers revert manually. This is explicit in the bead.
- **Galiana integration** — Full recall measurement deferred. Proxy metrics only.
- **Cross-project canaries** — Each project monitors independently.
- **Model override canaries** — Only routing (agent exclusion) canaries in v1.
- **Background goroutine** — No persistent process. Hook-based + on-demand only.
- **Statusline integration** — That's iv-sisi (downstream bead).
- **Verdict engine** — That's iv-jo3i (downstream bead). We implement the basic verdict logic here; iv-jo3i extends it with ML-based detection.

## Risk Assessment

**Low risk:** This is additive monitoring — it doesn't change any existing behavior. If canary monitoring has bugs, overrides still work fine (just unmonitored, which is the current state).

**Medium risk:** Baseline computation from historical evidence could be slow for large DBs. Mitigation: index on `sessions.start_ts` already exists; baseline query runs once per override apply.

**Low risk:** Session-end hook adds a few hundred ms of SQLite queries. Mitigation: Fail-open pattern, skip if no active canaries.
