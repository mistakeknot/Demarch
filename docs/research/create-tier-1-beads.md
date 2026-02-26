# Create Tier 1 Beads (Sprint Bridge)

**Date:** 2026-02-25
**Parent Epic:** iv-ip4zr

## Summary

Created 3 Tier 1 (Sprint Bridge) beads under the parent epic iv-ip4zr. These represent the foundational work to connect Autarch's TUI layer (L3) to Intercore's sprint orchestration (L1).

## Beads Created

| # | ID | Title | Type | Priority |
|---|-----|-------|------|----------|
| 1 | **iv-cl86n** | [autarch] Go wrapper for ic CLI (pkg/intercore/client.go) | feature | P0 |
| 2 | **iv-4hcuq** | [autarch/coldwine] Create Sprint action from epic context | feature | P0 |
| 3 | **iv-8by7z** | [autarch/tui] Sprint status view with phase advancement | feature | P0 |

## Dependency Graph

```
iv-ip4zr (parent epic)
  depends on iv-cl86n (Go wrapper)
  depends on iv-4hcuq (Sprint creation)
  depends on iv-8by7z (Sprint status view)

iv-4hcuq (Sprint creation) --depends on--> iv-cl86n (Go wrapper)
iv-8by7z (Sprint status view) --depends on--> iv-cl86n (Go wrapper)
```

The Go wrapper (iv-cl86n) is the critical path -- both the Coldwine sprint creation and the sprint status view depend on it. The parent epic (iv-ip4zr) depends on all three, meaning it cannot close until all three are complete.

## Bead Details

### 1. iv-cl86n -- Go wrapper for ic CLI

Creates `pkg/intercore/client.go` -- a Go client that shells out to `ic --json` and parses results. This mirrors the existing `lib-intercore.sh` bash wrapper but in Go, providing the foundational bridge between Autarch (Go/L3) and Intercore (L1). Must support:

- `run create/status/advance/cancel`
- `dispatch spawn/status/wait/list`
- `gate check`
- `state get/set`
- `events stream`
- Graceful degradation when `ic` binary is missing

### 2. iv-4hcuq -- Create Sprint action from epic context

Adds a "Create Sprint" command/action in ColdwineView that:
- Calls `ic run create` via the Go wrapper
- Captures the run ID and associates it with the current epic
- Sets initial phase, loads agency specs
- Stores run ID in Coldwine's SQLite

This is the single most important missing piece -- it connects task management to sprint orchestration.

### 3. iv-8by7z -- Sprint status view with phase advancement

New view (or Bigend sub-view) showing:
- Current sprint phase
- Token budget consumed/remaining
- Active dispatches
- Phase history timeline
- Gate status
- "Phase Advance" action (calls `ic run advance` after checking gates)

Reads from `ic run status` + `ic dispatch list`. Replaces the manual `ic run status` CLI workflow.

## Execution Order

1. **iv-cl86n** (Go wrapper) -- must complete first
2. **iv-4hcuq** and **iv-8by7z** -- can proceed in parallel once the wrapper is done
