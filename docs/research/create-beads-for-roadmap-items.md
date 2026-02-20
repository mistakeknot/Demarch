# Clavain Roadmap Beads — Creation Log

**Date:** 2026-02-20
**Scope:** Created beads for all Clavain roadmap items (Tracks A, B, C) that did not yet have beads.

## Beads Created

| Roadmap ID | Bead ID   | Title                                      | Type    | Priority |
|------------|-----------|---------------------------------------------|---------|----------|
| A2         | iv-kj6w   | Sprint handover — sprint skill becomes kernel-driven | feature | P1       |
| A3         | iv-r9j2   | Event-driven advancement — phase transitions trigger auto-dispatch | feature | P2       |
| B1         | iv-dd9q   | Static routing table — phase-to-model mapping in config | feature | P2       |
| B2         | iv-k8xn   | Complexity-aware routing — task complexity drives model selection | feature | P2       |
| B3         | iv-i198   | Adaptive routing — Interspect outcomes drive model/agent selection | feature | P3       |
| C1         | iv-asfy   | Agency specs — declarative per-stage agent/model/tool config | feature | P2       |
| C2         | iv-lx00   | Agent fleet registry — capability + cost profiles per agent×model | feature | P2       |
| C3         | iv-240m   | Composer — match agency specs to fleet registry within budget | feature | P3       |
| C4         | iv-1vny   | Cross-phase handoff protocol — structured output-to-input contracts | feature | P3       |
| C5         | iv-6ixw   | Self-building loop — Clavain runs its own development sprints | epic    | P3       |

## Dependency Graph (for future wiring)

### Track A: Kernel Primacy
```
A1 (done) → iv-kj6w (A2) → iv-r9j2 (A3)
```

### Track B: Intelligent Routing
```
iv-dd9q (B1) → iv-k8xn (B2) → iv-i198 (B3)
                   ↑                ↑
              E1 (done)      iv-thp7 (Interspect)
```

### Track C: Agency Architecture
```
iv-asfy (C1) → iv-lx00 (C2) → iv-240m (C3) → iv-6ixw (C5)
    ↓                                              ↑
iv-1vny (C4) ──────────────────────────────────────┘
                                                    ↑
iv-r9j2 (A3) ──────────────────────────────────────┘
iv-dd9q (B1) → iv-lx00 (C2)
```

### Cross-Track Dependencies
- **C5** (self-building loop) depends on C3, C4, and A3 — the convergence point
- **C2** (fleet registry) depends on B1 (routing table) for model tier data
- **B2** depends on B1 and E1 (done)
- **B3** depends on B2 and Interspect kernel integration (iv-thp7)

## Notes

- All beads created from `/root/projects/Interverse` (Interverse root beads DB at `.beads/`)
- All titles prefixed with `[clavain]` for filtering
- References to `hub/clavain/docs/roadmap.md` included in each description
- The `beads.role` warning is cosmetic — beads were created successfully
- Dependency wiring (`bd link`) not yet done — bead IDs are captured above for that step
