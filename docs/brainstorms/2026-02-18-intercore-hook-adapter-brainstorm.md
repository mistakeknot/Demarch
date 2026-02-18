# Intercore Hook Adapter — Brainstorm

**Bead:** iv-wo1t
**Phase:** brainstorm (as of 2026-02-18T06:26:19Z)
**Date:** 2026-02-18
**Status:** Skipped to planning (requirements clear)

## What We're Building

Rewrite Clavain's bash hooks as thin adapters that use intercore's SQLite DB (`ic` CLI) instead of temp files in `/tmp/clavain-*`.

## Why This Approach

- intercore v0.1.0 already provides `sentinel check`, `state set/get` with TTL, and atomic TOCTOU-safe operations
- `lib-intercore.sh` provides fail-safe bash wrappers (silent fallback when `ic` unavailable)
- `ic compat status` already maps all 9 legacy temp file patterns to intercore keys
- Temp files in `/tmp` don't survive reboots, lack atomicity, and can't be queried

## Key Decisions

1. **Approach:** Direct replacement using `lib-intercore.sh` wrappers — no new abstraction layer
2. **Migration:** Hook-by-hook, starting with simplest (catalog-reminder.sh) to validate the pattern
3. **Backward compat:** Not needed — `lib-intercore.sh` already fails safe (returns 0 when `ic` unavailable)
4. **Scope:** All hooks that use `/tmp/clavain-*` patterns (6 hooks, 9 temp file patterns)

## Hooks to Adapt

| Hook | Temp Files | intercore Equivalent |
|------|-----------|---------------------|
| `session-handoff.sh` | `stop-*`, `handoff-*` | `sentinel check stop $SID --interval=0`, `sentinel check handoff $SID --interval=0` |
| `auto-compound.sh` | `stop-*`, `compound-last-*` | `sentinel check stop`, `sentinel check compound_throttle --interval=300` |
| `auto-drift-check.sh` | `stop-*`, `drift-last-*` | `sentinel check stop`, `sentinel check drift_throttle --interval=600` |
| `auto-publish.sh` | `autopub.lock` | `sentinel check autopub $SID --interval=60` |
| `catalog-reminder.sh` | `catalog-remind-*.lock` | `sentinel check catalog_remind $SID --interval=0` |
| `lib-sprint.sh` | `discovery-brief-*.cache` | `state set discovery_brief $SID` with TTL |

## Open Questions

None — proceed to planning.
