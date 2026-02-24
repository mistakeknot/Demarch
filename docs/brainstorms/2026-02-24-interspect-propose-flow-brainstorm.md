# Brainstorm: Interspect Routing-Eligible Pattern Detection + Propose Flow

**Bead:** iv-8fgu
**Date:** 2026-02-24

## What We're Building

Making `/clavain:interspect-propose` work end-to-end. The command skeleton and library functions exist but are non-functional due to a name format mismatch between evidence collection and routing validation.

## Problem

Evidence DB records agent names as `interflux:fd-architecture`, `interflux:review:fd-quality`, etc. The routing system validates against `^fd-[a-z][a-z0-9-]*$`. Result: **zero patterns ever pass routing eligibility**, making the entire propose flow dead code.

## Root Cause

Two naming conventions collided:
1. **Evidence hooks** record the full plugin-namespaced agent name (e.g., `interflux:fd-architecture`)
2. **Routing overrides** use the short `fd-*` format (which is what flux-drive reads)

## Approach: Normalize at Query Time

Don't change how evidence is recorded — the namespaced format is correct for attribution. Instead, normalize when checking routing eligibility:

1. In `_interspect_get_classified_patterns()`: strip `interflux:` and `interflux:review:` prefixes when aggregating for routing purposes
2. In `_interspect_is_routing_eligible()`: relax validation to accept either format, normalize to `fd-*` internally
3. Merge `interflux:fd-X` and `interflux:review:fd-X` evidence into a single `fd-X` pattern for threshold counting

## Key Decisions

1. **Normalize, don't migrate** — don't alter 1888 existing evidence records
2. **Merge dispatch + review evidence** — `interflux:fd-architecture` and `interflux:review:fd-architecture` refer to the same agent capability
3. **Keep `fd-*` as the canonical routing override format** — that's what flux-drive reads
4. **Add override event support** — currently no `override` events in the DB; the correction flow (`/interspect:correction`) needs to actually insert them

## Open Question

The evidence DB has 1888 entries but zero `override` events. The propose flow relies on `agent_wrong_pct` from override events. Without corrections, no pattern will ever meet the 80% threshold regardless of name format. This means the correction recording path also needs verification.
