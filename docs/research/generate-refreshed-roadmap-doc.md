# Research: Generate Refreshed Roadmap Doc

**Date:** 2026-02-27
**Task:** Refresh `docs/demarch-roadmap.md` from canonical `docs/roadmap.json` and live bead data.

## Input Sources

1. **`docs/roadmap.json`** -- freshly generated, 53 modules, 94 module-level open beads, structured roadmap items in now/next/later phases
2. **`docs/demarch-roadmap.md`** -- existing human-facing roadmap, last updated 2026-02-27 (previous pass), 51 modules listed, 384 open beads count (stale)
3. **`bd list --status=open --limit 0`** -- 458 open beads (bd stats), 6 in-progress, 46 blocked, 1,822 closed
4. **`bd stats`** -- total 2,301 issues across entire project

## Key Changes Between Old and New

### Stats Update
- Module count: 51 -> 53 (2 new modules counted)
- Versioned modules: 43 -> 46 (some modules now have version numbers)
- Open beads: 384 -> 458 (new discovery items, research repos, recovered beads)
- Closed beads: 1,748 -> 1,822 (+74 closed since last snapshot)
- In-progress: 0 -> 6 (intercom IronClaw migration active)
- Blocked: 0 -> 46
- Total issues: ~2,147 -> 2,301

### Version Changes
- Clavain: 0.6.66 -> 0.6.106
- interfluence: 0.2.7 -> 0.2.8
- interflux: 0.2.29 -> 0.2.30

### Priority Distribution (Open Beads)
- P0: 11 beads (includes 8 research:repo epics + 3 core: iv-w7bh, iv-r6mf, iv-ho3)
- P1: 15 beads (includes research:repo epics + core: iv-t712t, iv-b46xi, iv-zsio, iv-6376, iv-be0ik)
- P2: 88 beads (bulk of active work)
- P3: 265-279 beads (research, backlog)
- P4: 105-124 beads (deep backlog, recovered docs, roadmap recovery)

### Module Status Changes
- Several modules changed from `active` to `early` status in roadmap.json (intercache, interchart, interkasten, interknow, interleave, intername, interplug, interpulse, intersense, intership, interskill, intertree, intertrust)
- interbase still missing from roadmap.json modules array but exists at sdk/interbase
- intermap open_beads changed from n/a to 6

### New Active Work
- **IronClaw migration** (iv-yfkln epic) -- 6 in-progress beads, Intercom Rust migration
- **StrongDM Factory Substrate** (iv-ho3) -- new P0 feature epic for validation-first Clavain infrastructure
- **Research repos** -- large batch of dicklesworthstone research assessment epics added across P0-P3

### Structural Observations
- The roadmap.json "now" phase contains 56 items (24 module-level + 32 interverse platform rollups)
- The "next" phase contains 68 items (module-level + interverse rollups)
- Many open epics are discovery/research items from interject source adapters, not core feature work

## Approach for Refresh

1. Preserve overall document structure and prose sections
2. Update header stats from bd stats
3. Update Ecosystem Snapshot table with fresh versions and bead counts from roadmap.json
4. Reorganize Open Epics to reflect current P0/P1/P2 priority assignments
5. Update Now/Next/Later sections with current bead data
6. Update cross-module dependency chains
7. Update module deep dives with current versions and status
8. Keep research agenda largely intact, updating any completed items

## Output

Written to: `docs/demarch-roadmap.md`
