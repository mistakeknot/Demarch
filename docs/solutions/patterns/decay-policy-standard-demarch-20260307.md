---
title: "Standardized decay policy across Demarch memory systems"
date: 2026-03-07
problem_type: documentation_gap
module: demarch
component: architecture
severity: medium
resolution_type: pattern
symptoms:
  - Each memory system had its own decay model or no decay at all
  - No consistent vocabulary for grace periods, decay rates, or hysteresis
  - Intercache had unbounded growth with no eviction policy
root_cause: Memory systems evolved independently without a shared decay standard
resolution: Adopt intermem's decay model (grace period + linear decay + hysteresis) as the standard, adapted per system's data characteristics
lastConfirmed: 2026-03-07
provenance: independent
review_count: 0
tags:
  - memory-architecture
  - decay
  - C1-C5-taxonomy
framework_version: "1.0"
---

# Standardized Decay Policy

All Demarch memory systems follow intermem's decay model as the standard pattern, adapted to each system's data characteristics.

## The Standard: Intermem's Model

Three components:
1. **Grace period** — new data is protected from decay for a configured duration
2. **Linear decay** — after grace, confidence decreases linearly per time period
3. **Hysteresis** — require consecutive staleness checks before demotion (prevents single-sweep false positives)

Reference implementation: `interverse/intermem/intermem/validator.py` (`apply_decay_penalty()`)

## Per-System Adaptation

| System | Layer | Grace Period | Decay Mechanism | Hysteresis | Implementation Status |
|--------|-------|-------------|-----------------|------------|----------------------|
| **Intermem** | C5 | 14 days | -0.1 confidence per 14d period | stale_streak >= 2 | Implemented |
| **Interspect** | C2 | 90 days | Evidence excluded from analysis after 90d rolling window | N/A (statistical) | Implemented (canary: 14d/20-use) |
| **Intercore** | C1 | 30 days | TTL-based: completed runs pruned after 30d | N/A (operational) | Partial (coordination locks have TTL; run pruning planned) |
| **Intercache** | C5 | None | Size-based LRU eviction at 500MB | 10% headroom buffer | Not yet implemented (policy defined) |
| **Interknow/docs/solutions/** | C4 | 10 reviews or 180 days | Archive on either trigger | 2 consecutive staleness checks | Partial (review-count implemented; 180d staleness defined) |

## Why Not One-Size-Fits-All

Each layer has different data characteristics:

- **C1 (Operational):** Data has a clear "done" state → TTL, not confidence decay
- **C2 (Evidence):** Statistical aggregates → rolling window, not per-entry decay
- **C3 (Preferences):** ML parameters → exponential moving average (plugin-local, not standardized)
- **C4 (Curated):** Human-validated patterns → provenance-based decay (review count + time)
- **C5 (Ephemeral):** Working memory → confidence decay (intermem) or LRU eviction (intercache)

## Evidence

- PHILOSOPHY.md § Memory Architecture — taxonomy and decay column
- intermem CLAUDE.md § Design Decisions — decay formula, hysteresis, grace period
- interspect AGENTS.md § Decay Policy — evidence rolling window
- intercore AGENTS.md § Decay Policy — TTL-based cleanup
- intercache CLAUDE.md § Decay Policy — size-based LRU
- interknow config/knowledge/README.md § Decay rules — review-count + time-based

## Verify

1. Check intermem decay: `grep -n "apply_decay_penalty\|GRACE_PERIOD\|DEMOTION_STREAK" interverse/intermem/intermem/validator.py`
2. Check interspect window: `grep -n "CANARY_WINDOW_DAYS\|rolling" interverse/interspect/hooks/lib-interspect.sh | head -5`
3. Check intercore TTL: `grep -n "ttl\|TTL\|expires_at" core/intercore/internal/coordination/store.go | head -5`
