# PRD: clavain-cli Go Migration

**Bead:** iv-1xtgd (P0 epic: Bash-Heavy L2 Logic Migration)
**Date:** 2026-02-25
**Status:** PRD

## Problem

The Clavain L2 orchestration layer's critical path — `clavain-cli` — sources ~2,600 lines of Bash per invocation across lib-sprint.sh (1,360 lines, 40 functions, 62 jq calls), lib-intercore.sh, lib.sh, and lib-spec.sh. Sprint workflows make 10-20 calls per phase transition, each re-parsing all libraries. Budget arithmetic uses Bash `$(( ))` which truncates silently. Phase transition logic is untestable due to global state and file system dependencies. Adding new features (agency specs, stage budgets, fleet routing) requires increasingly complex jq pipelines.

## Solution

Replace `clavain-cli` (Bash dispatcher + lib-sprint.sh) with a Go binary at `os/clavain/cmd/clavain-cli/`. The binary implements all 28 sprint commands natively in Go with type-safe arithmetic, table-driven tests, and structured JSON output. It calls `ic` and `bd` via subprocess (preserving the L1/L2 boundary). A thin Bash shim replaces lib-sprint.sh for backward compatibility during migration.

## Features

### F1: Go Binary Scaffold + Sprint CRUD

**What:** Initialize the Go module, set up CLI framework (cobra or plain flag dispatch), implement subprocess helpers for `ic` and `bd`, and deliver the 3 Sprint CRUD commands.

**Commands:** `sprint-create`, `sprint-find-active`, `sprint-read-state`

**Acceptance criteria:**
- [ ] `os/clavain/cmd/clavain-cli/` contains a Go module with `go.mod`
- [ ] `clavain-cli help` prints the same usage text as current Bash version
- [ ] `clavain-cli sprint-create <title>` creates an ic run + bd bead and returns the sprint ID (plain text)
- [ ] `clavain-cli sprint-find-active` returns JSON array of active sprints (same schema as current Bash)
- [ ] `clavain-cli sprint-read-state <id>` returns JSON sprint state (same schema)
- [ ] Subprocess helpers handle `ic` and `bd` not-on-PATH gracefully (exit 1 with clear error)
- [ ] `go test ./...` passes with `-race` flag
- [ ] Unknown commands exit 1 with "unknown command" message (matching current behavior)

### F2: Budget Math Engine

**What:** Type-safe budget arithmetic replacing 250 lines of Bash `$(( ))` + jq pipelines. All budget calculations use `int64` to prevent silent truncation.

**Commands:** `sprint-budget-remaining`, `sprint-budget-stage`, `sprint-budget-stage-check`, `budget-total`, `sprint-budget-stage-remaining`, `sprint-stage-tokens-spent`, `sprint-record-phase-tokens`

**Acceptance criteria:**
- [ ] `sprint-budget-remaining <bead_id>` returns remaining tokens as integer (matches Bash output)
- [ ] `sprint-budget-stage <bead_id>` returns per-stage budget allocation JSON
- [ ] `sprint-budget-stage-check <bead_id>` exits 0 if within budget, 1 if exceeded (with structured error)
- [ ] Budget math uses `int64` throughout — no floating point, no truncation
- [ ] Table-driven unit tests cover: zero budget, max int64, stage exhaustion, negative remaining, phase-cost estimation
- [ ] Phase-to-stage mapping matches the 9-phase model (brainstorm → done)
- [ ] Stage allocation percentages configurable (currently: research 20%, plan 10%, build 50%, review 15%, ship 5%)

### F3: Phase Transitions + Gate Enforcement

**What:** The sprint state machine — phase advancement, gate checks, pause detection, and artifact tracking. This is the core orchestration logic.

**Commands:** `sprint-advance`, `sprint-next-step`, `enforce-gate`, `sprint-should-pause`, `advance-phase`, `record-phase`, `set-artifact`, `get-artifact`, `infer-action`

**Acceptance criteria:**
- [ ] `sprint-advance <bead_id> <current_phase> [artifact_path]` returns structured result: advanced/blocked + reason
- [ ] `sprint-next-step <phase>` returns the next phase name (9-phase sequence)
- [ ] `enforce-gate <bead_id> <target_phase> <artifact_path>` calls `ic gate check` and respects `CLAVAIN_SKIP_GATE` env var
- [ ] `sprint-should-pause <bead_id>` returns structured pause trigger or empty (budget exceeded, manual pause, stale phase)
- [ ] `set-artifact` / `get-artifact` / `record-phase` / `advance-phase` / `infer-action` all match current behavior
- [ ] Pause triggers: budget_exceeded, manual_pause (auto_advance=false), stale_phase
- [ ] Table-driven tests for all 9 phase transitions and gate enforcement
- [ ] Gate skip via `CLAVAIN_SKIP_GATE='reason'` env var logged but allowed

### F4: Checkpoints + Claiming

**What:** Session checkpoint management (file-based) and bead/sprint claiming for multi-session safety.

**Commands:** `checkpoint-write`, `checkpoint-read`, `checkpoint-validate`, `checkpoint-clear`, `checkpoint-completed-steps`, `checkpoint-step-done`, `sprint-claim`, `sprint-release`, `bead-claim`, `bead-release`

**Acceptance criteria:**
- [ ] Checkpoint file format unchanged (JSON at `.clavain/checkpoint.json`)
- [ ] `checkpoint-write <bead_id> <phase> <step> <plan_path>` records bead, phase, step, plan path, git SHA, timestamp
- [ ] `checkpoint-read` outputs checkpoint JSON or empty `{}` if none
- [ ] `checkpoint-validate` warns (stderr) on git SHA mismatch but exits 0
- [ ] `checkpoint-completed-steps` returns ordered list of completed step names
- [ ] `sprint-claim <bead_id> <session_id>` sets session lock via bd state; exits 1 if already claimed by another session
- [ ] `sprint-release <bead_id>` clears session lock
- [ ] `bead-claim` / `bead-release` work via `bd update --status=in_progress` / bd state
- [ ] File operations use atomic write (write tmp + rename) to prevent corruption

### F5: Children + Shim + Cleanup

**What:** Child bead management, remaining utility commands, thin Bash shim, and plugin.json build integration.

**Commands:** `close-children`, `close-parent-if-done`, `classify-complexity`, `complexity-label`, `infer-bead`, `sprint-track-agent`, `sprint-complete-agent`, `sprint-invalidate-caches`

**Acceptance criteria:**
- [ ] `close-children <bead_id> <reason>` cascades close to child beads, returns count closed
- [ ] `close-parent-if-done <bead_id>` checks all children closed, closes parent if so
- [ ] `classify-complexity <bead_id> <description>` returns 1-5 score
- [ ] `complexity-label <score>` returns label (trivial/simple/moderate/complex/research)
- [ ] lib-sprint.sh replaced with thin shim (<100 lines) delegating to Go binary
- [ ] Shim falls back to sourcing lib-sprint.sh functions if Go binary not on PATH
- [ ] plugin.json updated with build step for Go binary
- [ ] All 28 commands pass integration tests comparing Go output vs current Bash output
- [ ] Sprint workflow latency measured and documented (target: 2x faster per-call)

## Non-goals

- **sprint-scan.sh migration** — 548-line discovery logic is a separate concern, deferred
- **Hook script migration** — session-start.sh, auto-publish.sh etc. are lightweight glue, stay in Bash
- **lib-intercore.sh removal** — will be replaced naturally as callers switch to Go binary
- **lib-verdict.sh migration** — small (128 lines), already simple file I/O
- **Cross-layer shared SDK** — Autarch and Clavain both consume sprint types, but sharing is deferred until both are stable
- **SQLite for checkpoint state** — keep file-based checkpoints for simplicity; revisit if corruption becomes an issue

## Dependencies

- **ic binary** (core/intercore/) — L1 kernel, called via subprocess. Must be on PATH.
- **bd CLI** (beads) — bead operations, called via subprocess. Must be on PATH.
- **Go 1.22+** — for build. Already required by ic and autarch.
- **Existing integration tests** — `os/clavain/tests/shell/test_lib_sprint.bats` (40 tests) provide behavioral spec.
- **pkg/intercore/types.go** (apps/autarch/) — reference for JSON schemas, but NOT imported (L2 binary must not depend on L3 code).

## Open Questions

1. **Cobra vs plain dispatch?** The current Bash dispatcher is a simple case statement. Cobra adds dependency weight but gives auto-completion and structured help. Recommendation: start with plain `flag` + manual dispatch (matching current simplicity), add cobra later if needed.
2. **Type sharing with Autarch?** Duplicate core types (Run, BudgetResult, GateResult) in the clavain-cli package for L2 independence. If types drift, extract a shared `pkg/sprint/types.go` later.
3. **Checkpoint file format?** Keep current JSON format. Add a `version` field for forward compatibility.
