# Roadmap Refresh Analysis: interpath:roadmap (2026-02-27)

**Date:** 2026-02-27
**Task:** Refresh docs/demarch-roadmap.md via interpath:roadmap skill
**Outcome:** Committed as `43acb11`

---

## Execution Summary

The `interpath:roadmap` skill invoked `interpath:artifact-gen` with the roadmap artifact type. The interpath sync-roadmap-json.sh wrapper failed because the Demarch monorepo does not have a `scripts/sync-roadmap-json.sh` at its root (the wrapper expects an Interverse plugin monorepo layout). Discovery proceeded directly from the Demarch `.beads/issues.jsonl` database and the interverse module tree instead.

Artifact type auto-detected as **monorepo-roadmap** (Demarch has `.beads/` and `interverse/*/` plugin subdirectories but no root `.claude-plugin/plugin.json`). Output written to `docs/demarch-roadmap.md` per the Demarch naming convention.

Roadmap-bead consistency check: 126 iv-IDs in roadmap, zero errors, all P0-P2 open beads represented.

---

## Key Findings

### 1. Five new P0 epics were created on 2026-02-23

The previous roadmap (2026-02-23) had zero P0 items. The refresh reveals five P0 epics added on the same date, establishing a clear priority stack for the next sprint:

| Bead | Title |
|------|-------|
| iv-4xnp4 | P0: C1 Agency specs — unblock Track C convergence |
| iv-b46xi | P0: Measure north star — cost-per-landable-change baseline |
| iv-sksfx | P0: Interspect Phase 2 — routing overrides (iv-r6mf chain) |
| iv-t712t | P0: First-stranger experience — README, install, clavain setup |
| iv-wie5i | P0: Discovery OS integration — close the research→backlog loop |

Two feature-level P0 beads also exist: iv-asfy (C1 agency specs implementation, zero dependencies, unblocked) and iv-zsio (discovery pipeline integration into sprint). The agency specs bead (iv-asfy) is the single highest-priority unblocked item in the tracker.

### 2. The previous sprint cleared entirely

All four previously in-progress beads and the blocked P2 epic were closed on 2026-02-23:

- iv-dthn — Research: inter-layer feedback loops (closed)
- iv-jc4j — [intermute] Heterogeneous agent routing experiments (closed)
- iv-p4qq — Smart semantic caching / intercache (closed)
- iv-qznx — [interflux] Multi-framework interoperability benchmark (closed)
- iv-pt53 — Interoperability epic (closed, was blocked by all four above)

Additional significant completions in the same batch: the Clavain sprint-consolidation chain (iv-hks2, iv-xxyi, iv-qe1j, iv-3ngh, iv-czz4 — all closed), the full intercache three-phase chain (iv-0qhl, iv-3ua2, iv-qu6c), the Bigend inline-mode chain (iv-omzb and four dependents), and six Autarch TUI beads. The tracker currently shows zero in-progress items.

### 3. Eleven new modules extracted; module count grew from 46 to 51

A refactoring wave on 2026-02-25 extracted single-responsibility plugins from existing modules:

| New Module | Extracted From | Purpose |
|------------|---------------|---------|
| intercache | (new) | Cross-session semantic cache |
| interknow | interflux | Knowledge compounding + qmd MCP |
| intername | clavain | Agent/agency deterministic naming |
| interplug | interdev | Plugin development toolkit |
| interpulse | intercheck | Session context pressure monitoring |
| intersearch | interflux/intercache | Shared embeddings (nomic-embed-text-v1.5) + Exa |
| intersense | interflux | Domain detection scripts (11 profiles) |
| intership | clavain | Culture ship names for spinner verbs |
| interskill | interdev | Skill authoring toolkit |
| intertree | interkasten | Project hierarchy management |
| intertrust | interspect | Agent trust scoring engine |

All 11 new modules are at version 0.1.x or 0.2.x and are immediately active. The extraction eliminates cross-cutting concerns that were entangled in larger plugins (notably interflux and interkasten), reducing their maintenance surface.

---

## Bead Count Changes

| Metric | Previous (2026-02-23) | Current (2026-02-27) |
|--------|----------------------|---------------------|
| Total | ~1,975 | 2,147 |
| Open | 212 | 384 |
| Closed | 1,704 | 1,748 |
| In-progress | 4 | 0 |
| Blocked (status) | 59 | 0 |
| Cancelled | n/a | 15 |
| Modules | 46 | 51 |

The open bead count jumped from 212 to 384 primarily due to the 4,336-label backfill operation and bead recovery: 153 new beads were created (mostly interject discovery items — 130 of the 384 open beads are unreviewed interject discovery items), and 73 were closed.

---

## Dependency Graph Changes

| Chain | Status |
|-------|--------|
| Intercache (0qhl → 3ua2 → qu6c) | COMPLETE — all 3 phases closed |
| Bigend inline mode (omzb hub) | COMPLETE — omzb + 4 dependents closed |
| Clavain sprint consolidation (hks2) | COMPLETE — all 5 beads closed |
| Interspect routing override (r6mf chain) | OPEN — F1 is P0, F2-F5 chain follows |
| Agency specs (asfy hub) | OPEN — C1 is P0, unblocked; C2-C5 follow |
| Intermap epic (w7bh) | OPEN — P1, 11-bead feature chain |
| Interlock (F2 + F4) | PARTIALLY COMPLETE — F3+F5 closed, F2+F4 remain |
| Intercore E9 → E10 | OPEN — E9 unblocked (P3), E10 blocked by E9 (P4) |

---

## Notes on sync-roadmap-json.sh Failure

The interpath:roadmap skill calls a sync-roadmap-json.sh wrapper to regenerate `docs/roadmap.json` from current repo state. The wrapper at `/home/mk/.claude/plugins/cache/interagency-marketplace/interpath/0.2.3/scripts/sync-roadmap-json.sh` failed with "could not locate scripts/sync-roadmap-json.sh" because it expects to be run from an Interverse plugin monorepo root (which has `plugins/*/` structure), not from the Demarch monorepo root (which has `interverse/*/` structure). The `docs/roadmap.json` was not regenerated in this refresh. This is a known limitation of the interpath wrapper when run from Demarch directly.

The roadmap markdown was generated from live `.beads/issues.jsonl` data, which is the authoritative source. `docs/roadmap.json` remains at its pre-refresh state.
