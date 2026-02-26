# Create Tier 3 Beads (Feedback Loops)

**Date:** 2026-02-25
**Parent Epic:** iv-ip4zr
**Tier 1 Go Wrapper Dependency:** iv-cl86n

## Summary

Created 3 Tier 3 (Feedback Loops) beads under the Autarch Intercore integration epic. All three depend on the Go wrapper bead (iv-cl86n) and are children of the parent epic (iv-ip4zr).

## Beads Created

### 1. Pollard to Sprint Integration (iv-deldu)

- **Title:** [autarch/pollard] Feed research results into sprint artifacts
- **Type:** feature | **Priority:** P2
- **Description:** Add "Research this spec" action that triggers a Pollard research run scoped to a spec/epic, then stores results as an Intercore run artifact via ic run artifact add. Bridges Pollard insights into the sprint lifecycle so research findings are available during plan review and execution phases.

### 2. Intermute Bidirectional Sync (iv-cguwq)

- **Title:** [autarch] Bidirectional sync between local sources and Intermute
- **Type:** feature | **Priority:** P2
- **Description:** Push local changes (Coldwine SQLite writes, Gurgeh YAML specs) to Intermute server when available. Pull remote changes back for cross-agent visibility. Use Intermute WritableDataSource interface (CreateEpic/CreateStory/CreateTask) which exists but is never called. Enable multi-agent coordination where agents read/write through Intermute while Autarch stays usable offline.

### 3. Auto-Advance with Gate Enforcement (iv-fj20z)

- **Title:** [autarch] Auto-advance sprint phases on action completion
- **Type:** feature | **Priority:** P2
- **Description:** When a phase action (e.g. plan review, code execution) completes successfully, optionally auto-advance to the next phase. Enforce gate checks before advancing. Configurable per-phase: some phases auto-advance (brainstorm-reviewed to strategized), others require manual confirmation (plan-reviewed to executing). Uses ic gate check + ic run advance.

## Dependency Wiring

### All 3 depend on Go wrapper (iv-cl86n):
- iv-deldu depends on iv-cl86n (blocks)
- iv-cguwq depends on iv-cl86n (blocks)
- iv-fj20z depends on iv-cl86n (blocks)

### All 3 are children of parent epic (iv-ip4zr):
- iv-ip4zr depends on iv-deldu (blocks)
- iv-ip4zr depends on iv-cguwq (blocks)
- iv-ip4zr depends on iv-fj20z (blocks)

## Bead IDs

| # | Bead | ID |
|---|------|----|
| 1 | Pollard to Sprint integration | iv-deldu |
| 2 | Intermute bidirectional sync | iv-cguwq |
| 3 | Auto-advance with gate enforcement | iv-fj20z |
