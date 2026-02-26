# Interdoc Analysis: Intercore AGENTS.md Refresh

**Date:** 2026-02-25
**Target:** `/home/mk/projects/Demarch/core/intercore/AGENTS.md`
**Current length:** 595 lines
**Target length:** 400-500 lines

## Executive Summary

The current AGENTS.md is significantly outdated. It documents ~12 of the 23 internal packages and is missing 7 entire CLI command groups that exist in the codebase. The schema has grown from v10 to v20 with 6 new table groups. The Architecture section's file tree is stale and the Location field still says `infra/intercore/` (pre-monorepo path).

## Inventory: What Exists in Code vs Documentation

### CLI Command Groups (from main.go switch statement)

| Command | In AGENTS.md | In CLAUDE.md | Notes |
|---------|:---:|:---:|-------|
| init | Yes | Yes | |
| version | Yes | Yes | |
| health | Yes | Yes | |
| sentinel | Yes | Yes | |
| state | Yes | Yes | |
| dispatch | Yes | Yes | |
| run | Yes | Yes | |
| events | Yes | Yes | |
| gate | Yes | Yes | |
| lock | Yes | Yes | |
| portfolio | Yes | Yes | |
| config | Yes | Yes | |
| agency | Yes | Yes | |
| compat | Yes | Yes | |
| **interspect** | **NO** | **NO** | record, query subcommands |
| **discovery** | **NO** | **Yes** | submit, status, list, score, promote, dismiss, feedback, profile, decay, rollback, search |
| **lane** | **NO** | **NO** | create, list, status, close, events, sync, members, velocity |
| **cost** | **NO** | **Yes** | reconcile, list |
| **scheduler** | **NO** | **Yes** | submit, status, stats, pause, resume, list, cancel, prune |
| **coordination** | **NO** | **NO** | reserve, release, check, list, sweep, transfer |

5 command groups (interspect, lane, coordination, and partially discovery/cost/scheduler) are completely missing from AGENTS.md.

### Internal Packages (from internal/)

| Package | In AGENTS.md | Notes |
|---------|:---:|-------|
| action | Partially | Mentioned in Phase Actions section but not in architecture tree |
| agency | Yes | |
| audit | **NO** | Tamper-evident audit trail with SHA-256 hash chain (v15) |
| budget | Yes | Now also has reconcile.go, composition.go |
| coordination | **NO** | Unified file reservations, named locks, write-sets (v20) |
| db | Yes | Schema now at v20 (was v10 in docs) |
| discovery | **NO** | Research discovery pipeline (v9) |
| dispatch | Yes | |
| event | Yes | Now has 5 source types (was 2) |
| handoff | **NO** | Structured YAML handoff format for session context |
| lane | **NO** | Thematic work lanes with velocity scoring (v13) |
| lifecycle | **NO** | Formalized agent state machine with stall detection |
| lock | Yes | |
| phase | Yes | Now has tx_queriers.go |
| portfolio | Yes | |
| redaction | **NO** | Secret scanning with 4 modes (off/warn/redact/block) |
| runtrack | Yes | |
| scheduler | **NO** | Fair spawn scheduler with paced dispatch creation (v19) |
| scoring | **NO** | Multi-factor agent-task assignment scoring |
| sentinel | Yes | |
| state | Yes | |

11 of 23 packages are undocumented in AGENTS.md.

### Schema Tables (from schema.sql)

| Table | Schema Version | In AGENTS.md |
|-------|:---:|:---:|
| state | v1 | Yes |
| sentinels | v1 | Yes |
| dispatches | v2 | Yes |
| merge_intents | v11 | Partially |
| runs | v3 | Yes |
| phase_events | v3 | Yes |
| run_agents | v4 | Yes |
| run_artifacts | v4 | Yes |
| dispatch_events | v5 | Yes |
| interspect_events | v7 | **NO** |
| discoveries | v9 | **NO** |
| discovery_events | v9 | **NO** |
| feedback_signals | v9 | **NO** |
| interest_profile | v9 | **NO** |
| project_deps | v10 | Yes |
| lanes | v13 | **NO** |
| lane_events | v13 | **NO** |
| lane_members | v13 | **NO** |
| phase_actions | v14 | Partially |
| audit_log | v15 | **NO** |
| cost_reconciliations | v17 | **NO** |
| scheduler_jobs | v19 | **NO** |
| coordination_locks | v20 | **NO** |
| coordination_events | v20 | **NO** |

14 of 24 tables are missing or only partially documented.

### Bash Wrappers (lib-intercore.sh, 585 lines, 45 functions)

Documented wrappers: ~25 functions
Missing from docs:
- `intercore_run_rollback` / `intercore_run_rollback_dry` / `intercore_run_code_rollback`
- `intercore_run_action_add/list/update/delete`
- `intercore_run_advance` (newer version with JSON actions)
- `intercore_agency_load` / `intercore_agency_validate`

## Stale Content Identified

1. **Location field:** Says `infra/intercore/` -- should be `core/intercore/`
2. **Schema version references:** AGENTS.md mentions "schema v4", "schema v5", "schema v10" as if they were recent; actual schema is at v20
3. **Architecture file tree:** Missing 11 packages (action, audit, coordination, discovery, handoff, lane, lifecycle, redaction, scheduler, scoring, and their sub-files)
4. **CLI Commands section:** Missing 5 command groups entirely
5. **Test counts:** Says "~155 tests across 12 packages" -- actual is ~529 Go test functions
6. **Integration test count:** Says "~105+ tests" but file is 1320 lines
7. **Event sources:** Only documents phase + dispatch sources; actual has 5 (+ interspect, discovery, coordination)
8. **lib-intercore.sh version:** Says "v0.6.0" -- needs verification

## Structural Issues

1. Several sections exceed 80 lines:
   - CLI Commands: 64 lines (borderline, OK)
   - Portfolio Orchestration Module: ~70 lines (OK)
   - The combined dispatch + run + lock + phase + event sections are individually fine

2. The document is well-structured but needs the new modules added without making it balloon. Strategy: keep the same depth for new modules as existing ones (brief overview + CLI commands + key behavior notes).

## Rewrite Plan

### Sections to Keep (with updates)
- Overview (fix location, update schema version)
- Architecture (add missing packages to tree)
- CLI Commands (add missing 5 command groups)
- Exit Codes / Global Flags (unchanged)
- Dispatch Module (minor updates)
- Run Tracking Module (minor updates)
- Lock Module (keep as-is)
- Phase Module (keep as-is)
- Gate System (keep as-is)
- Event Bus Module (update sources list, mention coordination/interspect/discovery)
- Portfolio Orchestration Module (keep as-is)
- Security (keep as-is)
- SQLite Patterns (keep as-is)
- Testing (update counts)
- Recovery Procedures (keep as-is)

### New Sections to Add (compact)
- Coordination Module (~20 lines)
- Scheduler Module (~15 lines)
- Lane Module (~15 lines)
- Discovery Pipeline (~15 lines)
- Cost Reconciliation (~10 lines)
- Interspect Events (~8 lines)
- Audit Trail (~8 lines)
- Supporting Libraries (~10 lines for handoff, lifecycle, redaction, scoring)

### Sections to Extract to Topic Files
None needed -- keeping descriptions compact for new modules should keep total under 500 lines.

### Content to Remove
- Verbose "Legacy: Complexity-Based Skip" section (3 lines summary instead of 8)
- Some redundant bash wrapper listings that duplicate the CLI reference
- "Column Allowlist" subsection in Event Bus (move to inline note)

## Changes Made

The rewrite:
1. Fixed location from `infra/intercore/` to `core/intercore/`
2. Updated schema version from various mentions to v20
3. Added 11 missing packages to architecture tree
4. Added 5 missing CLI command groups (coordination, scheduler, lane, interspect, cost)
5. Added compact documentation for 7 new modules
6. Updated test counts (529 Go tests, 1320-line integration suite)
7. Updated event bus to show all 5 source types
8. Added lib-intercore.sh wrapper documentation for newer functions
9. Kept total under 500 lines by being concise about new modules
10. Preserved all Design Decisions content
11. Proper cased "Intercore" throughout prose
