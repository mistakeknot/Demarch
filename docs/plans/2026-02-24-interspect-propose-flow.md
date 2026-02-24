# Interspect Propose Flow — Implementation Plan

**Bead:** iv-8fgu
**Date:** 2026-02-24

## Problem

`/clavain:interspect-propose` is non-functional because:
1. Evidence records use `interflux:fd-*` names; routing validation demands `fd-*`
2. `_interspect_get_classified_patterns()` doesn't normalize names for routing aggregation
3. No override events exist yet (only dispatch/advance/skip/cancel), so `agent_wrong_pct` is always 0%

## Tasks

### Task 1: Add name normalization helper ✅
- File: `os/clavain/hooks/lib-interspect.sh`
- Add `_interspect_normalize_agent_name()` that strips `interflux:` and `interflux:review:` prefixes
- Returns canonical `fd-*` form for routing purposes

### Task 2: Update `_interspect_get_classified_patterns()` to merge namespaced evidence ✅
- When aggregating for pattern classification, normalize source names
- Merge `interflux:fd-X` + `interflux:review:fd-X` + `fd-X` into one `fd-X` pattern
- Only apply normalization for `fd-*` pattern detection (don't change non-agent patterns like `kernel-phase`)

### Task 3: Update `_interspect_is_routing_eligible()` to accept namespaced names ✅
- Accept `interflux:fd-*` format in addition to `fd-*`
- Normalize internally before checking thresholds and blacklist

### Task 4: Verify `/interspect:correction` records in correct format ✅
- The correction command already uses `fd-*` format — confirmed correct
- The propose flow queries all three variants (fd-X, interflux:fd-X, interflux:review:fd-X)

### Task 5: Test end-to-end ✅
- Normalization verified: `interflux:fd-architecture` → `fd-architecture`, `interflux:review:fd-quality` → `fd-quality`
- `_interspect_get_classified_patterns` returns merged `fd-*` format patterns
- `_interspect_is_routing_eligible` correctly returns `not_eligible:no_override_events` (expected — no corrections recorded yet)
- Non-fd-* patterns (e.g., `kernel-phase`) pass through unchanged

## Files Modified

| File | Changes |
|------|---------|
| `os/clavain/hooks/lib-interspect.sh` | Add normalizer, update classified patterns query, relax eligibility check |
