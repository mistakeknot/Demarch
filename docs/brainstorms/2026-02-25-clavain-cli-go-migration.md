# Brainstorm: clavain-cli Go Migration

**Bead:** iv-1xtgd (P0 epic: Bash-Heavy L2 Logic Migration)
**Date:** 2026-02-25
**Status:** Brainstorm

## Problem

The Clavain L2 orchestration layer runs on ~3,500 lines of Bash across 7 lib files and 12 hook scripts. The critical hotspot is **lib-sprint.sh** (1,360 lines, 40 functions, 62 jq calls) — a state machine with budget math, phase transitions, gate enforcement, and checkpoint management. This Bash code is:

1. **Fragile** — 62 jq pipelines with no type safety. Budget arithmetic in Bash (`$(( ))`) truncates silently. Associative array accumulation bugs were caught by review agents (iv-8fgu).
2. **Slow** — Each `clavain-cli` invocation sources lib-sprint.sh + lib-intercore.sh + lib.sh + lib-spec.sh (~2,600 lines parsed per call). Sprint workflows make 10-20 calls per phase transition.
3. **Untestable** — Functions depend on global state, environment variables, and file system. No unit tests exist for budget math or phase transition logic.
4. **Hard to evolve** — Adding agency specs (C1), stage budgets, and fleet routing required increasingly complex jq pipelines that are unreadable and unreviewable.

## Landscape

### Current Architecture

```
Skills (markdown) → clavain-cli (Bash) → lib-sprint.sh (Bash, 1360 lines)
                                          ├── lib-intercore.sh (Bash, 605 lines) → ic (Go)
                                          ├── lib-spec.sh (Bash, 222 lines)
                                          ├── lib.sh (Bash, 407 lines)
                                          └── lib-verdict.sh (Bash, 128 lines)
```

### What Already Exists in Go

- **ic binary** (core/intercore/) — L1 kernel. Manages runs, dispatches, gates, state, events, artifacts, agents, budgets. 303-line operations.go in the Autarch Go wrapper.
- **pkg/intercore/client.go** (apps/autarch/) — L3 Go client for ic. 18 unit + 2 integration tests. Ships with Autarch.
- **DispatchWatcher** (apps/autarch/) — Polls ic dispatch status, emits Bubble Tea messages. Already handles the dispatch lifecycle.

### What lib-sprint.sh Does That ic Does NOT

| Function cluster | Count | Lines | ic equivalent? |
|-----------------|-------|-------|----------------|
| Sprint CRUD (create, find, read) | 3 | ~120 | Partial — `ic run create/status/list` exists, but sprint = run + bead metadata + epic linking |
| Phase transitions (advance, next-step, pause) | 4 | ~200 | `ic run advance` exists, but sprint_advance() also records artifacts, checks gates, handles pause triggers |
| Budget math (remaining, stage, check) | 7 | ~250 | `ic run budget` returns raw totals, but stage allocation, phase cost estimates, and per-stage checks are all in Bash |
| Gate enforcement | 2 | ~80 | `ic gate check` exists, but enforce_gate() wraps it with skip-gate env var, error formatting |
| Checkpoints | 5 | ~100 | No ic equivalent — checkpoint is a Clavain-specific concept (file-based) |
| Bead claiming/tracking | 4 | ~60 | No ic equivalent — uses `bd` CLI |
| Complexity classification | 2 | ~40 | No ic equivalent |
| Children management | 2 | ~50 | No ic equivalent — uses `bd` CLI |
| Agent tracking | 2 | ~40 | `ic run agent add/list` exists |
| Sprint-scan discovery | 1 file | 548 lines | No ic equivalent |

**Key insight:** About 60% of lib-sprint.sh is orchestration logic that *wraps* ic calls with bead tracking, budget allocation, and phase policies. The remaining 40% is pure Clavain concepts (checkpoints, complexity, children) with no kernel dependency.

## Target Architecture

```
Skills (markdown) → clavain-cli (Go binary) → ic (Go binary) → SQLite
                     ├── sprint-create         ├── run create
                     ├── sprint-advance        ├── run advance
                     ├── budget-remaining      ├── run budget
                     ├── checkpoint-*          └── state get/set
                     ├── classify-complexity
                     └── close-children

lib-sprint.sh → thin shim (~50 lines)
  Backward compat: sources lib-intercore.sh
  All 40 functions delegate to Go binary
```

### Location: `os/clavain/cmd/clavain-cli/`

New Go module in the Clavain repo. Separate from Intercore (L1) and Autarch (L3). The binary:
- Calls `ic` via subprocess (same pattern as lib-intercore.sh — the ic binary is the contract)
- Calls `bd` via subprocess for bead operations
- Implements budget math, phase policies, checkpoint I/O natively in Go
- Outputs JSON (for Bash callers) or plain text (for human callers)

### What NOT to Migrate

- **Hook scripts** (session-start.sh, auto-publish.sh, etc.) — Lightweight glue. Keep in Bash.
- **lib-intercore.sh** — Already thin. Will be replaced naturally as callers switch to Go binary.
- **lib-verdict.sh** — Small (128 lines), already simple file I/O.
- **sprint-scan.sh** — Discovery logic. Migrate later as a separate concern.

## Migration Strategy

### Phase 1: Go Binary Core (Sprint CRUD + Budget)

Build the Go binary with the 12 highest-value functions:

1. `sprint-create` — Create sprint (ic run create + bd metadata)
2. `sprint-find-active` — List active sprints (ic + bd query)
3. `sprint-read-state` — Read sprint state (ic run status + bd state)
4. `sprint-advance` — Phase transition (ic run advance + artifact registration + pause checks)
5. `sprint-next-step` — Determine next phase from current
6. `sprint-budget-remaining` — Type-safe budget arithmetic
7. `sprint-budget-stage` — Per-stage budget allocation
8. `sprint-budget-stage-check` — Stage budget enforcement
9. `budget-total` — Total budget query
10. `enforce-gate` — Gate check with skip-gate override
11. `classify-complexity` — Complexity scoring
12. `complexity-label` — Score to label mapping

**Deliverable:** Go binary that passes the same integration tests as current Bash (same inputs → same outputs).

### Phase 2: Checkpoint + Claiming

Migrate checkpoint management and bead claiming:

13. `checkpoint-write` — Write checkpoint file (Go file I/O)
14. `checkpoint-read` — Read checkpoint
15. `checkpoint-validate` — Validate git SHA
16. `checkpoint-clear` — Clear checkpoint
17. `checkpoint-completed-steps` — Parse completed steps
18. `sprint-claim` / `sprint-release` — Session claiming
19. `bead-claim` / `bead-release` — Bead claiming

### Phase 3: Children + Shim + Cleanup

20. `close-children` — Cascade close child beads
21. `close-parent-if-done` — Check if parent can be closed
22-28. Remaining commands (set-artifact, record-phase, infer-bead, etc.)

Then:
- Replace lib-sprint.sh with a thin shim that delegates to the Go binary
- Update plugin.json to build and ship the Go binary
- Remove Bash-only functions from lib-sprint.sh

## Risks and Mitigations

| Risk | Mitigation |
|------|-----------|
| **Go binary not available on PATH** | Launcher script auto-builds from source (same pattern as ic in install.sh). Fallback: lib-sprint.sh Bash implementation stays as degraded path. |
| **Breaking backward compat** | Go binary outputs exact same JSON as Bash. Integration tests compare outputs. Bash shim delegates transparently. |
| **bd CLI dependency** | Go binary shells out to `bd` (same as Bash does). No new dependency. |
| **Plugin distribution** | plugin.json gets a build step. `launch-clavain-cli.sh` auto-builds if binary missing. |
| **Two implementations during migration** | Phase 1 migrates the most-called functions first. Each function is switched atomically in the shim. |

## Success Criteria

1. `clavain-cli` is a Go binary that handles all 28 commands
2. lib-sprint.sh is <100 lines (thin shim only)
3. Budget math has unit tests with edge cases (zero budget, overflow, stage exhaustion)
4. Phase transition logic has table-driven tests for all 9 phases
5. Sprint workflow latency improves measurably (target: 2x faster per-call)
6. No behavioral changes visible to skills or hooks (backward compat)

## Open Questions

1. Should the Go binary share types with Autarch's `pkg/intercore/`? Or duplicate for independence?
2. Should sprint-scan.sh (548 lines, discovery logic) be included in this epic or deferred?
3. Should the Go binary have its own SQLite for checkpoint state, or keep using files?

## Decision: Scoping

- **In scope:** 28 clavain-cli commands → Go binary, lib-sprint.sh → thin shim, integration tests
- **Out of scope:** sprint-scan.sh migration, hook script migration, lib-intercore.sh removal
- **Deferred:** Cross-layer shared SDK (revisit when both Autarch and Clavain consume sprint types)
