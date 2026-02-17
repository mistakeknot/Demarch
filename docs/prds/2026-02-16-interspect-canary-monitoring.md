# PRD: Interspect Canary Monitoring

**Bead:** iv-cylo
**Brainstorm:** `docs/brainstorms/2026-02-16-interspect-canary-monitoring-brainstorm.md`

## Problem

When interspect excludes an agent from flux-drive triage via a routing override, there's no way to know if review quality degraded. The canary table schema exists and records are created at override-apply time, but baselines are never computed, use counts are never incremented, and no degradation detection runs. If an exclusion was wrong, the user has no signal until they notice a defect escape manually.

**Impact:** This is the safety net for the entire routing override system. Without canary monitoring, overrides are fire-and-forget — 6 downstream features (meta-learning, autonomous mode, verdict engine, statusline integration, revert UX, prompt tuning) are blocked waiting for this signal.

## Solution

Implement the three-metric canary monitoring system described in the bead: compute baselines at override-apply time, collect per-session samples during the monitoring window, detect degradation via percentage-based comparison, and surface alerts through session-start injection and `/interspect:status`.

**Architecture:** Hook-based collection (session-end records samples, session-start checks alerts) + on-demand evaluation (`/interspect:status`). No background process, no auto-revert.

## Features

### F1: Baseline Computation

**What:** Compute rolling baseline metrics from historical evidence at override-apply time.

**Acceptance criteria:**
- [ ] New function `_interspect_compute_canary_baseline` in lib-interspect.sh
- [ ] Queries last 20 sessions before apply timestamp (configurable via `canary_min_baseline_window` in confidence.json)
- [ ] Computes three metrics:
  - Override rate: overrides per session
  - FP rate: `agent_wrong` overrides / total overrides
  - Finding density: total evidence events per session
- [ ] If fewer than `canary_min_baseline` (default 15) sessions exist, returns NULL baselines
- [ ] Stores baselines + window boundaries in canary record columns
- [ ] Called inside `_interspect_apply_override_locked` before canary INSERT
- [ ] Baseline query filters by project (from canary file path context)

### F2: Canary Sample Collection

**What:** Record per-session metric snapshots during the canary monitoring window.

**Acceptance criteria:**
- [ ] New `canary_samples` table in DB schema (id, canary_id, session_id, ts, override_rate, fp_rate, finding_density)
- [ ] DB migration adds table to existing databases
- [ ] New function `_interspect_record_canary_sample` in lib-interspect.sh
- [ ] Called from session-end hook (`interspect-session-end.sh`) when active canaries exist
- [ ] Computes metrics for the current session only (not cumulative)
- [ ] Increments `canary.uses_so_far` atomically
- [ ] Skips sessions with zero evidence events (not a "flux-drive use")
- [ ] Dedup: does not insert duplicate samples for the same (canary_id, session_id)

### F3: Degradation Detection

**What:** Compare canary samples against baselines to detect quality degradation.

**Acceptance criteria:**
- [ ] New function `_interspect_evaluate_canary` in lib-interspect.sh
- [ ] For each active canary, computes average of sample metrics
- [ ] Compares against baseline with configurable threshold (`canary_alert_pct`, default 20%)
- [ ] Noise floor: ignores differences < `canary_noise_floor` (default 0.1) absolute
- [ ] Verdict is worst across all three metrics: PASSED, ALERT, INSUFFICIENT_BASELINE, EXPIRED_UNUSED
- [ ] Stores verdict in `canary.status` and `canary.verdict_reason`
- [ ] Called when `uses_so_far >= window_uses` OR `now > window_expires_at`
- [ ] Multiple active canaries evaluated independently with note about confounding

### F4: Alert Surface

**What:** Surface canary alerts through session-start injection and `/interspect:status`.

**Acceptance criteria:**
- [ ] Session-start hook (`interspect-session.sh`) checks for canaries with `status = 'alert'`
- [ ] If alerts exist, injects warning via `additionalContext` JSON: "Canary alert: routing override for {agent} may have degraded review quality. Run `/interspect:status` for details."
- [ ] `/interspect:status` shows canary section with: verdict, sample count / window total, progress bar, metric comparison (baseline vs current), next action hint
- [ ] Active canaries show: "monitoring: N/20 uses (M days remaining)"
- [ ] Completed canaries show: "PASSED" or "ALERT: {reason}"
- [ ] NULL-baseline canaries show: "monitoring (insufficient baseline, collecting data)"

### F5: Configuration Extension

**What:** Add canary-specific thresholds to confidence.json.

**Acceptance criteria:**
- [ ] New fields in confidence.json: `canary_window_uses` (default 20), `canary_window_days` (default 14), `canary_min_baseline` (default 15), `canary_alert_pct` (default 20), `canary_noise_floor` (default 0.1)
- [ ] All canary functions read from confidence.json with fallback defaults
- [ ] Existing `_interspect_load_confidence` extended (not a separate loader)

## Non-goals

- **Auto-revert** — Canary alerts but does not auto-remove overrides. Human reverts manually via `/interspect:revert`.
- **Galiana integration** — Full recall measurement deferred to v2. Proxy metrics only.
- **Background monitoring process** — No daemon, goroutine, or cron job. Hook-based + on-demand.
- **Cross-project canaries** — Each project monitors independently.
- **ML-based detection** — That's iv-jo3i (verdict engine). We implement percentage-based comparison here.
- **Statusline integration** — That's iv-sisi. We emit the signal; statusline consumes it.
- **Model override canaries** — Only routing (agent exclusion) canaries in v1.

## Dependencies

- **Routing overrides (iv-nkak)** — Already shipped. Canary records created at apply time.
- **Evidence store** — Already active. Session tracking and evidence collection working.
- **Confidence.json** — Already loaded by `_interspect_load_confidence`. Extending, not replacing.
- **Session hooks** — Already running (`interspect-session.sh`, `interspect-session-end.sh`). Extending, not replacing.

## Success Metrics

- **Coverage:** 100% of interspect-created overrides have active canaries
- **Baseline computation:** >80% of canaries have non-NULL baselines (depends on project history)
- **Alert accuracy:** 0 false-positive alerts in first 30 days
- **Detection latency:** Degradation detected within 5 sessions of onset
- **No performance regression:** Session-end hook adds <500ms for canary sample collection
