---
status: complete
priority: p2
issue_id: "002"
bead: iv-hqo0q
tags: [interwatch, drift-detection, signals]
dependencies: []
---

# interwatch: bead-count reconciliation signal

## Problem Statement

Docs claim specific bead counts ("Open: 698 | Blocked: 68 | Closed: 2,567") that drift as beads are created/closed. The existing `component_count_changed` signal only checks skill/command/agent filesystem counts, not bead statistics from `bd stats`.

## Proposed Solutions

New signal type `bead_count_mismatch` in `interwatch-scan.py`:
1. Run `bd stats` to get actual open/closed/blocked counts
2. Scan doc text for patterns like "Open: NNN", "Blocked: NNN", "Closed: N,NNN"
3. Compare claimed vs actual
4. Return number of mismatches as signal value

## Acceptance Criteria

- [x] New `bead_count_mismatch` signal type in SIGNAL_EVALUATORS
- [x] Parse `bd stats` output for open/closed/blocked counts
- [x] Regex extraction of count claims from doc text
- [x] Signal fires when any claimed count differs from actual
- [x] Added to roadmap signal template in watchables.yaml
- [x] Weight: 3 (deterministic — counts are provably wrong)

## Work Log

### 2026-03-06 - Created

**By:** Claude Code

**Actions:**
- Created bead iv-hqo0q and this todo from drift gap analysis (iv-ey5wb retrospective)

### 2026-03-06 - Implemented

**By:** Claude Code

**Actions:**
- Added `eval_bead_count_mismatch()` to `interwatch-scan.py` (parses bd stats, regex-matches count claims, compares)
- Registered in SIGNAL_EVALUATORS dict and deterministic signals list
- Added to roadmap default watchable + signal template in watchables.yaml
- Added to signals.md reference doc
- Smoke tested: 0 mismatches on roadmap (just updated), 2 on vision (counts drifted during session)
