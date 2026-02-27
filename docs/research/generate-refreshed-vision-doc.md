# Research: Generate Refreshed Vision Doc

**Date:** 2026-02-27
**Purpose:** Analyze inputs and produce a refreshed `docs/demarch-vision.md`

---

## Inputs Analyzed

1. **docs/demarch-vision.md** (v3.0, 2026-02-21) — current vision doc
2. **docs/roadmap.json** — 53 modules listed, generated 2026-02-27
3. **AGENTS.md** — root agent instructions, references "42 companion plugins" in interverse/
4. **docs/demarch-roadmap.md** — 51 modules (43 versioned), 384 open beads, 1,748 closed, 15 cancelled

## Key Factual Discrepancies Found

### Module and Plugin Counts

| Claim | Old Vision Doc | Current Reality | Source |
|-------|---------------|-----------------|--------|
| Companion plugins | "33+" | 42 companion plugins (42 in AGENTS.md, 43 directories in interverse/) | `ls interverse/` = 43 dirs; AGENTS.md line says "42 companion plugins" |
| Total modules | "42 modules" (Origins section) | 53 modules | roadmap.json `module_count: 53` |
| Interverse directory count | — | 43 subdirectories | `ls -d interverse/*/` |

**Resolution:** The CLAUDE.md says "42 companion plugins" and AGENTS.md directory table says "42 companion plugins". The interverse/ directory has 43 subdirectories. The difference is likely that one directory is a non-plugin artifact or the count was taken before the most recent addition. Using "42" for companion plugins per CLAUDE.md, "53" for total modules per roadmap.json.

### Version Numbers

| Module | Old Vision Doc | Current | Source |
|--------|---------------|---------|--------|
| Clavain | "Version 0.6.60" | 0.6.106 | roadmap.json snapshot |
| Vision doc version | 3.0 | Should be 3.1 | Refresh increment |

### Kernel Epics

| Claim | Old Vision Doc | Current | Source |
|-------|---------------|---------|--------|
| Kernel epics | "10 of 12 epics shipped" | "8 of 10 epics shipped (E1-E8)" | roadmap.md intercore section |

**Note:** The old doc said "10 of 12" but roadmap.md says "8 of 10". The numbering scheme may have changed (consolidated some epics). Using the roadmap.md phrasing: "8 of 10 epics shipped (E1-E8)".

### Bead Tracking

| Metric | Old Vision Doc | Current | Source |
|--------|---------------|---------|--------|
| Total tracked | 1,419 | 2,147+ (384 open + 1,748 closed + 15 cancelled) | roadmap.md header |
| Closed | 1,098 | 1,748 | roadmap.md header |

### Clavain Stats

| Metric | Old Vision Doc | Current | Source |
|--------|---------------|---------|--------|
| Skills | 16 | 16 | roadmap.md clavain section |
| Agents | — | 4 | roadmap.md clavain section |
| Commands | — | 53 | roadmap.md clavain section |
| Hooks | — | 22 | roadmap.md clavain section |

### New Architectural Elements

1. **Intercom** — `apps/intercom` (v1.1.0), multi-runtime AI assistant (Claude, Gemini, Codex). Not mentioned in old vision doc at all. Belongs to L3 Apps alongside Autarch.
2. **11 new plugins extracted 2026-02-25** from Clavain/interflux/interkasten: intercache, interknow, intername, interplug, interpulse, intersearch, intersense, intership, interskill, intertree, intertrust.
3. **Intermap** elevated to P1 epic — Go MCP server + Python analysis bridge for project-level code mapping.
4. **5 new P0 epics created 2026-02-23** — agency specs, north star metric, Interspect routing overrides, first-stranger experience, discovery OS integration.

### Stack Diagram Updates Needed

The old stack diagram mentions:
- "33+ companion plugins" -> should be "42 companion plugins"
- The Apps layer only mentions Autarch apps (Bigend, Gurgeh, Coldwine, Pollard) but should also mention Intercom

### "Where We Are" Section — Full Refresh

Old:
- Kernel: 10 of 12 epics shipped
- OS: Version 0.6.60
- Ecosystem: 33+ companion plugins
- Self-building: 1,419 beads tracked, 1,098 closed

New:
- Kernel: 8 of 10 epics shipped (E1-E8). Runs, phases, gates, dispatches, events, discovery pipeline, rollback, portfolio orchestration, TOCTOU prevention, cost-aware scheduling, fair spawn scheduler, sandbox specs. All landed and tested.
- OS: Version 0.6.106. 16 skills, 4 agents, 53 commands, 22 hooks, 1 MCP server. Full sprint lifecycle (brainstorm -> ship) is kernel-driven. Sprint consolidation complete (/route -> /sprint -> /work unified).
- Model routing: Static routing and complexity-aware routing (C1-C5) shipped. Adaptive routing (B3) is the next frontier, blocked on Interspect routing overrides.
- Review engine: 12 specialized review agents + 5 research agents, deployed through interflux with multi-agent synthesis. Capability declarations shipped.
- Ecosystem: 42 companion plugins shipped, each independently installable. 11 new plugins extracted 2026-02-25 from Clavain/interflux/interkasten for single-responsibility. 53 total modules across the monorepo.
- Apps: Autarch TUI (Bigend monitoring, inline mode shipped) + Intercom multi-runtime AI assistant (v1.1.0).
- Profiler: Evidence collection shipped (override tracking, false positive rates, finding density). Routing override chain (F1-F5) is the P0 frontier.
- Self-building: 2,147+ beads tracked (1,748 closed, 384 open, 15 cancelled). The system has been building itself for months.

### "What's Next" Section Updates

Track A status unchanged (done).
Track B: Same status — B1-B2 done, B3 open via iv-sksfx (now explicitly P0).
Track C: Same status — C1 open (iv-asfy, now P0). C2-C5 open.

New additions to the narrative:
- 5 explicit P0 epics now defined (agency specs, north star metric, Interspect routing, first-stranger experience, discovery OS integration)
- Intermap P1 epic for project-level code mapping
- Intercache chain completed (3 phases closed)
- Interlock partially complete (F3, F5 closed)
- Clavain workflow unification complete
- Bigend inline mode complete

### Origins Section Update

"42 modules" should become "53 modules" to match roadmap.json.

## Refresh Strategy

1. Bump version to 3.1, update date to 2026-02-27
2. Preserve all vision/philosophy prose verbatim
3. Update all factual claims with current data
4. Add Intercom to the Apps layer in the stack diagram and descriptions
5. Update "Where We Are" comprehensively
6. Update "What's Next" with fresh P0 epic information
7. Keep the same general structure and format

---

## Output

The refreshed `docs/demarch-vision.md` has been written directly. See the file for the complete updated vision document.
