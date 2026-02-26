# Create 6 Autarch Self-Hosting Beads

**Date:** 2026-02-24
**Task:** Create beads for the Autarch self-hosting priority list and wire dependency chain.

## Beads Created

| ID | Priority | Title | Type |
|---|---|---|---|
| iv-mjybd | P0 | [autarch] Fix Bigend context cancellation and goroutine lifecycle leaks | bug (pre-existing) |
| iv-62f6e | P1 | [autarch] Kernel visibility — read Intercore DB in Bigend | feature |
| iv-77a0w | P2 | [autarch] Implement stubbed TUI commands (New Spec, New Epic, etc.) | feature |
| iv-vtcwi | P2 | [autarch] Intent submission — Coldwine write path to Clavain/Intercore | feature |
| iv-fsuaj | P3 | [autarch] Interspect dashboard — surface profiler data in TUI | feature |
| iv-mj16n | P3 | [autarch] Sprint context — project Clavain state into TUI | feature |

## Dependency Chain

```
iv-mjybd (P0 bug fix)
  └── iv-62f6e (P1 kernel visibility)
        ├── iv-fsuaj (P3 Interspect dashboard)
        └── iv-mj16n (P3 Sprint context)

iv-77a0w (P2 stubbed commands)
  └── iv-vtcwi (P2 intent submission)
```

### Rationale

- **Kernel visibility depends on P0 bug fix** (iv-62f6e → iv-mjybd): The Bigend goroutine lifecycle leaks must be fixed before adding a new data source (intercore.db reading) that spawns additional async work.
- **Intent submission depends on stubbed commands** (iv-vtcwi → iv-77a0w): Can't build write paths until the basic CRUD command stubs are implemented as UI entry points.
- **Interspect dashboard and Sprint context both depend on kernel visibility** (iv-fsuaj → iv-62f6e, iv-mj16n → iv-62f6e): Both need the Intercore DB reading infrastructure that kernel visibility establishes. They are independent of each other.

## Execution Output

### bd show iv-mjybd (pre-existing)
Confirmed P0 bug bead exists with correct scope: context cancellation, goroutine lifecycle leaks, and deterministic shutdown sequencing.

### bd ready
Shows iv-mjybd in the ready queue (no blockers). The newly created beads are correctly blocked:
- iv-62f6e blocked by iv-mjybd
- iv-vtcwi blocked by iv-77a0w
- iv-fsuaj blocked by iv-62f6e
- iv-mj16n blocked by iv-62f6e
- iv-77a0w has no blockers (ready for work)

### bd list --status=open | grep autarch
Confirmed all 6 beads appear in open bead list with correct dependency annotations. Total of 31 open autarch beads exist across the project.

## Observations

1. **iv-77a0w is immediately workable** — it has no blockers, so stub implementation can start in parallel with the P0 bug fix.
2. **Two existing beads overlap with the new ones:**
   - `iv-k1q4` (P4): "[autarch] Coldwine: intent submission to Clavain OS" — overlaps with iv-vtcwi (P2). The new P2 bead is broader (covers all apps, not just Coldwine). May want to close iv-k1q4 as superseded.
   - `iv-6abk` (P3): "[autarch] Signal broker: connect to Intercore event bus" — related to iv-62f6e (kernel visibility) but distinct (event bus vs direct DB read).
3. **The `beads.role` warning** appears on every `bd create` — project needs `bd init` to set the role.
