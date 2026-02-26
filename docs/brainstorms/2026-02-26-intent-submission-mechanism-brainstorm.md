# Intent Submission Mechanism — Brainstorm

**Bead:** iv-gyq9l
**Date:** 2026-02-26
**Status:** Brainstorm complete

## Problem

Apps (Autarch L3) bypass the OS layer (Clavain L2) by calling Intercore (L1) directly for policy-governing write operations. This means TUI-created sprints have no token budget, no phase actions, no bead linkage, and no complexity-based routing policy applied.

**Evidence:** `coldwine.go:1121` calls `ic.RunCreate()` directly via `pkg/intercore`. `sprint_commands.go` routes all `/sprint` slash commands through `pkg/intercore`. Five write operations currently bypass L2.

## What We're Building

A `pkg/clavain/` Go client in `apps/autarch/` that shells out to `clavain-cli` for all 5 policy-governing write operations, matching the existing `pkg/intercore/` subprocess pattern.

### The 5 Intents

| Intent | clavain-cli command | Current bypass location |
|--------|-------------------|----------------------|
| Sprint creation | `sprint-create` | `coldwine.go:1121` → `ic.RunCreate()` |
| Task dispatch | (new: `dispatch-task`) | `coldwine.go:990` → `ic.DispatchSpawn()` |
| Run advancement | `sprint-advance` | `run_actions.go` → `ic.RunAdvance()` |
| Gate override | `enforce-gate` (+ new override) | Missing from TUI entirely |
| Artifact submission | `set-artifact` | `run_dashboard.go:460` partial bypass |

### Architecture

```
Layer 3 (Autarch TUI)
  └── pkg/clavain/         ← NEW: OS client (subprocess to clavain-cli)
  └── pkg/intercore/       ← EXISTING: kernel client (subprocess to ic)

Layer 2 (Clavain OS)
  └── cmd/clavain-cli/     ← EXISTING: policy enforcement binary

Layer 1 (Intercore kernel)
  └── ic                   ← EXISTING: kernel binary
```

Call chain example (sprint creation):
```
Coldwine TUI
  → pkg/clavain.SprintCreate(goal, complexity, lane)
    → exec: clavain-cli sprint-create <goal> [--complexity=N] [--lane=L]
      → bd create + ic run create + budget + phases + actions
    ← returns: beadID, runID
  → Update view with new sprint
```

### pkg/clavain/ Structure

```
apps/autarch/pkg/clavain/
├── client.go        # Client struct, binary discovery, exec helper
├── sprint.go        # SprintCreate, SprintAdvance, SprintReadState
├── dispatch.go      # DispatchTask
├── gate.go          # EnforceGate, OverrideGate
├── artifact.go      # SetArtifact, GetArtifact
├── types.go         # SprintResult, AdvanceResult, GateResult (parse clavain-cli JSON)
└── client_test.go   # Table-driven tests with mock exec
```

### Callsite Rewiring

| File | Current call | New call |
|------|-------------|----------|
| `coldwine.go:1121` | `ic.RunCreate()` | `clavain.SprintCreate()` |
| `coldwine.go:990` | `ic.DispatchSpawn()` | `clavain.DispatchTask()` |
| `sprint_commands.go` | `ic.RunAdvance()` | `clavain.SprintAdvance()` |
| `run_dashboard.go` | `ic.StateSet()` (artifact) | `clavain.SetArtifact()` |
| (new) | — | `clavain.OverrideGate()` (gate override button) |

### Graceful Degradation

If `clavain-cli` is not on PATH (e.g., running Autarch without Clavain installed):
- `pkg/clavain/client.go` checks binary availability at construction
- If unavailable: log warning, fall back to direct `ic` calls via `pkg/intercore/`
- This preserves the current behavior for standalone Autarch users

## Why This Approach

1. **Matches existing pattern** — `pkg/intercore/` already shells out to `ic`. `pkg/clavain/` shells out to `clavain-cli`. Same architecture, same testing approach.
2. **No new protocol** — subprocess exec is the simplest IPC. Fork-per-call overhead is negligible for 5 infrequent write operations (user-initiated, not hot path).
3. **Preserves layer boundaries** — Autarch imports `pkg/clavain/` (L2 client), not clavain-cli source. No L1/L2 coupling leak.
4. **clavain-cli already exists** — we just shipped the Go binary (F1-F5). The command surface is complete and tested.

## Key Decisions

- **Subprocess client** over IPC/socket — simplicity wins for 5 infrequent operations
- **All 5 intents at once** — complete the architectural fix rather than iterate
- **Fallback to direct ic** — graceful degradation when clavain-cli absent
- **Types duplicated in pkg/clavain/types.go** — parse clavain-cli JSON output, don't import clavain-cli source (layer independence)

## Open Questions

- Does `clavain-cli` need a new `dispatch-task` subcommand? Current commands don't cover dispatch policy. May need to add this to `os/clavain/cmd/clavain-cli/`.
- Should gate override be a new TUI button in RunDashboard, or a slash command in the palette?

## Scope

- Create `apps/autarch/pkg/clavain/` client package (6 files)
- Add `dispatch-task` to `os/clavain/cmd/clavain-cli/` if needed
- Rewire 5 callsites in Coldwine, SprintCommands, RunDashboard
- Add gate override UI element (button or palette command)
- Table-driven tests for the client package
