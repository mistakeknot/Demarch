# Extract Interspect from Clavain into Standalone Plugin

**Bead:** iv-88cp2

## What We're Building

Extract the Interspect profiler subsystem from `os/clavain/` into `interverse/interspect/` as a standalone companion plugin. Interspect handles evidence collection, pattern classification, routing overrides, canary monitoring, and overlay generation. It's currently inlined in Clavain but has zero reverse dependencies on Clavain internals.

## Why This Approach

- **Clean extraction boundary**: lib-interspect.sh uses only standard CLI tools (jq, git, sqlite3) — no calls to Clavain functions (lib.sh, lib-sprint.sh, lib-intercore.sh)
- **Independent release cycle**: Interspect changes currently require a Clavain version bump + republish, even when Clavain itself is unchanged
- **Consistent ecosystem pattern**: Other profiler-adjacent tools (interflux, interphase) are already standalone companions
- **Modularity**: Users who don't want Interspect shouldn't need to carry 2661 lines of unused code in Clavain

## Extraction Inventory

### What Moves

| Component | Source (Clavain) | Destination (Interspect) | Lines |
|-----------|-----------------|-------------------------|-------|
| Core library | `hooks/lib-interspect.sh` | `hooks/lib-interspect.sh` | 2661 |
| Session start hook | `hooks/interspect-session.sh` | `hooks/interspect-session.sh` | 74 |
| Evidence hook | `hooks/interspect-evidence.sh` | `hooks/interspect-evidence.sh` | 55 |
| Session end hook | `hooks/interspect-session-end.sh` | `hooks/interspect-session-end.sh` | 46 |
| Commands (12) | `commands/interspect*.md` | `commands/interspect*.md` | ~600 |
| Default config | embedded in lib | `config/defaults/` | new |

### What Stays in Clavain

- `hooks.json` — remove 3 interspect hook bindings
- `plugin.json` — remove 12 interspect commands
- A thin `_discover_interspect_plugin()` function in `lib.sh` (already follows companion pattern)
- Skills that reference `/clavain:interspect*` commands — these become pass-throughs invoking the companion's commands

### State Migration

| File | Old Location | New Location |
|------|-------------|-------------|
| SQLite DB | `.clavain/interspect/interspect.db` | `.interspect/interspect.db` |
| Confidence config | `.clavain/interspect/confidence.json` | `.interspect/confidence.json` |
| Protected paths | `.clavain/interspect/protected-paths.json` | `.interspect/protected-paths.json` |
| Overlays dir | `.clavain/interspect/overlays/` | `.interspect/overlays/` |
| Routing overrides | `.claude/routing-overrides.json` | `.interspect/routing-overrides.json` |

Migration: auto-migrate on first SessionStart hook run. Move data, leave symlink at old location for backward compat during transition period.

## Key Decisions

1. **State directory**: `.interspect/` (project-scoped, consistent with `.interwatch/`, `.beads/`)
2. **Routing overrides**: Move to `.interspect/routing-overrides.json` (keep all state together)
3. **Migration**: Auto-migrate on first run with backward-compat symlink
4. **Phased extraction**: 3 phases, each independently shippable
   - Phase 1: Plugin scaffold + hooks + lib-interspect.sh (the hard part)
   - Phase 2: Move 12 commands, update Clavain plugin.json
   - Phase 3: Cleanup — remove dead code from Clavain, add CLAUDE.md/AGENTS.md, publish

## Function Inventory (59 functions, 9 subsystems)

- **Evidence & Storage** (7): db_path, project_name, ensure_db, insert_evidence, consume_kernel_events, validate_hook_id
- **Classification** (8): load_manifest, classify_pattern, get_classified_patterns, load_confidence, matches_any, is_protected, is_allowed, is_always_propose
- **Routing** (9): validate_target, is_routing_eligible, get_routing_eligible, is_cross_cutting, apply/read routing overrides (locked variants), override_exists
- **Autonomy & Circuit Breaker** (4): is_autonomous, set_autonomy, circuit_breaker_tripped, should_auto_apply
- **Approval** (5): approve_override, apply_propose (locked variants), revert_routing_override
- **Canary** (6): compute_baseline, record_sample, evaluate, check_canaries, get_summary
- **Overlays** (8): is_active, body, read_overlays, count_tokens, validate_id, write/disable (locked variants)
- **Blacklist** (2): blacklist_pattern, unblacklist_pattern
- **Utilities** (7): next_seq, normalize/validate agent_name, sql_escape, validate_overrides_path, redact_secrets, sanitize, flock_git

## Open Questions

1. **Clavain skill forwarding**: Should `/clavain:interspect` commands be kept as aliases that forward to `/interspect:*`, or should users learn the new command namespace? Recommendation: Keep aliases for one version cycle, then deprecate.
2. **Kernel integration**: lib-interspect.sh optionally calls `ic interspect query/record`. Should the Interspect plugin discover Intercore independently, or delegate through Clavain? Recommendation: Discover independently (same `ic` binary check).
3. **hooks.json ownership**: When Interspect has its own hooks.json, does Claude Code merge hooks from multiple plugins correctly? Yes — each plugin's hooks.json is independent. Verified by looking at how interphase hooks coexist with Clavain hooks.

## Risk Assessment

- **Low risk**: Clean extraction boundary, no reverse dependencies
- **Medium risk**: State migration — need to handle concurrent sessions (one on old Clavain, one on new Interspect) gracefully
- **Low risk**: Command namespace — aliases bridge the transition

## Next Steps

1. `/clavain:write-plan` — detailed task breakdown for all 3 phases
2. Execute Phase 1 (scaffold + hooks + lib) first — this is the structural change
3. Phases 2-3 can be separate sprints if needed
