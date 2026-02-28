# Plan: intertrack — Feature Metrics Instrumentation Plugin

**Bead:** iv-dvdkg
**Date:** 2026-02-28
**PRD:** docs/prds/2026-02-28-darwinian-evolver-selective-adoption.md
**Reference:** interverse/interstat/ (measurement plugin pattern)

## Overview

Create `interverse/intertrack/` — a plugin that tracks feature-level success metrics. Where interstat measures token consumption (cost), intertrack measures feature outcomes (effectiveness). Each instrumented feature emits metric events via a simple shell API; intertrack stores observations in SQLite and surfaces them via skills.

## Tasks

### T1: Plugin scaffold and manifest
**Files:** `interverse/intertrack/.claude-plugin/plugin.json`, `CLAUDE.md`, `AGENTS.md`, `README.md`

- Create plugin manifest (name: intertrack, version: 0.1.0)
- No MCP server — hooks + skills only (same pattern as interstat)
- Skills directory: `skills/`
- Write CLAUDE.md with data flow, cross-layer interface, schema reference

### T2: SQLite schema and init script
**Files:** `interverse/intertrack/scripts/init-db.sh`
**DB location:** `~/.claude/intertrack/metrics.db`

Tables:
```sql
-- Metric definitions (what we measure)
CREATE TABLE IF NOT EXISTS metric_definitions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,        -- e.g. 'repeated_failure_rate'
    feature TEXT NOT NULL,            -- e.g. 'F1', 'F2', 'F3', 'F4'
    plugin TEXT NOT NULL,             -- e.g. 'interknow', 'interflux'
    description TEXT,
    unit TEXT DEFAULT 'ratio',        -- ratio, count, percentage, tokens, ms
    direction TEXT DEFAULT 'lower',   -- lower_is_better, higher_is_better
    target_value REAL,                -- success metric threshold
    baseline_value REAL,              -- pre-feature baseline (nullable)
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

-- Metric observations (individual measurements)
CREATE TABLE IF NOT EXISTS metric_observations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    metric_name TEXT NOT NULL,        -- FK to metric_definitions.name
    value REAL NOT NULL,
    session_id TEXT,
    bead_id TEXT,
    context TEXT,                     -- JSON blob for extra context
    observed_at TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (metric_name) REFERENCES metric_definitions(name)
);

-- Baselines (periodic snapshots)
CREATE TABLE IF NOT EXISTS metric_baselines (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    metric_name TEXT NOT NULL,
    value REAL NOT NULL,
    sample_count INTEGER,
    snapshot_at TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (metric_name) REFERENCES metric_definitions(name)
);
```

Indexes: metric_name, observed_at, session_id, bead_id, feature.
WAL mode + busy_timeout=5000 (same as interstat).
Schema version via `PRAGMA user_version = 1`.

### T3: Metric recording script (cross-layer interface)
**Files:** `interverse/intertrack/scripts/track-record.sh`, `interverse/intertrack/scripts/track-query.sh`

**track-record.sh** — the write API (called by instrumented plugins):
```bash
# Usage: track-record.sh <metric_name> <value> [--session <id>] [--bead <id>] [--context '{"key":"val"}']
# Example: track-record.sh repeated_failure_rate 0.0 --session abc123 --bead iv-z90qq
```
- Auto-init DB if missing
- INSERT into metric_observations
- Exit 0 always (never break caller hooks)

**track-query.sh** — the read API (JSON output, same pattern as interstat's cost-query.sh):
```bash
track-query.sh status              # All metrics: current vs target vs baseline
track-query.sh metric <name>       # Time series for one metric
track-query.sh feature <F1|F2|F3|F4>  # All metrics for a feature
track-query.sh baseline-snapshot   # Snapshot current values as new baselines
```

### T4: Seed metric definitions
**Files:** `interverse/intertrack/config/metrics.yaml`

Pre-seed the 12 metrics from the PRD:

```yaml
metrics:
  # F1: Failure signal in interknow
  - name: repeated_failure_rate
    feature: F1
    plugin: interknow
    unit: ratio
    direction: lower
    target: 0.0
    description: "% of sessions that attempt an approach already recorded as failed"
  - name: failure_entry_recall_rate
    feature: F1
    plugin: interknow
    unit: ratio
    direction: higher
    target: 1.0
    description: "% of sessions with relevant failure entries that successfully recall them"
  - name: failure_entry_count
    feature: F1
    plugin: interknow
    unit: count
    direction: higher
    target: null
    description: "Total failure entries vs success entries over time"

  # F2: Post-fix verification
  - name: verify_fix_pass_rate
    feature: F2
    plugin: interflux
    unit: ratio
    direction: higher
    target: 0.8
    description: "% of fixes that pass verification on first attempt"
  - name: review_token_savings
    feature: F2
    plugin: interflux
    unit: percentage
    direction: higher
    target: 0.10
    description: "Token savings by skipping full re-review when verify-fix passes"
  - name: verify_fix_false_negative_rate
    feature: F2
    plugin: interflux
    unit: ratio
    direction: lower
    target: 0.05
    description: "Fixes that pass verify-fix but fail subsequent full review"

  # F3: Findings-identity feedback loop
  - name: overlap_detection_rate
    feature: F3
    plugin: intersynth
    unit: ratio
    direction: higher
    target: 0.20
    description: "% of multi-agent reviews where >80% findings overlap detected"
  - name: agents_saved_per_review
    feature: F3
    plugin: intersynth
    unit: count
    direction: higher
    target: 1.0
    description: "Redundant agents removed by overlap-triggered routing overrides"
  - name: per_review_token_reduction
    feature: F3
    plugin: intersynth
    unit: percentage
    direction: higher
    target: 0.05
    description: "Token savings on reviews where overlap was detected"

  # F4: Baseline rescaling
  - name: score_spread_ratio
    feature: F4
    plugin: interspect
    unit: ratio
    direction: higher
    target: 2.0
    description: "Post-rescaling spread / pre-rescaling spread (target: 2x)"
  - name: ranking_divergence_rate
    feature: F4
    plugin: interspect
    unit: ratio
    direction: higher
    target: 0.10
    description: "% of routing decisions where rescaling changes top-agent ranking"
  - name: false_positive_regression
    feature: F4
    plugin: interspect
    unit: ratio
    direction: lower
    target: 0.0
    description: "FP rate increase in agent selection post-rescaling vs baseline"
```

T4 also includes `scripts/seed-metrics.sh` that reads this YAML and INSERTs into metric_definitions.

### T5: Skills
**Files:** `interverse/intertrack/skills/status.md`, `interverse/intertrack/skills/report.md`

**/intertrack:status** — quick health dashboard:
- Calls `track-query.sh status`
- Shows each metric: name, current value, target, baseline, trend (improving/regressing/stable)
- Color-coded: green (meeting target), yellow (within 20%), red (missing target)

**/intertrack:report** — detailed feature report:
- Takes optional feature arg (F1/F2/F3/F4)
- Shows time series, observation count, baseline history
- Calls `track-query.sh feature <name>`

### T6: Hooks
**Files:** `interverse/intertrack/hooks/hooks.json`, `interverse/intertrack/hooks/session-start.sh`

Minimal hook set for v0.1.0:
- **SessionStart**: auto-init DB, report metric count as additionalContext
- No PostToolUse hook yet — instrumented plugins call `track-record.sh` directly

### T7: Documentation
**Files:** `interverse/intertrack/docs/intertrack-vision.md`, `interverse/intertrack/docs/intertrack-roadmap.md`

Follow existing conventions. Vision covers: what intertrack is, why it exists (feature-level metrics gap), design principles (measure outcomes not effort, piggyback on existing hooks, degrade gracefully). Roadmap references child beads iv-z90qq through iv-f462h.

## Execution Order

T1 → T2 → T3 → T4 → T5 → T6 → T7

T1-T4 are sequential (each builds on prior). T5-T7 can parallelize after T4.

## Success Criteria

- `scripts/init-db.sh` creates schema without errors
- `scripts/track-record.sh repeated_failure_rate 0.0` writes to DB
- `scripts/track-query.sh status` returns JSON with all 12 metrics
- `/intertrack:status` shows readable dashboard
- Plugin installs cleanly via marketplace
