# Interchart Combined View Analysis

**Date:** 2026-02-21
**URL:** https://mistakeknot.github.io/interchart/
**Screenshots:** `/tmp/interchart-ecosystem.png` (ecosystem only), `/tmp/interchart-both.png` (combined)
**Method:** Puppeteer headless Chrome at 1920x1080, D3 force settled 4s, Sprint toggled, settled 3s

---

## Summary

The combined Ecosystem + Sprint view is **functional but cluttered**. The 10-phase sprint pipeline (rendered as labeled rounded-rect boxes with directional arrows) overlays directly on top of the D3 force-directed ecosystem graph, creating significant visual congestion in the center of the viewport. There are **78 overlapping text label pairs** out of 179 total text elements.

---

## What Is Displayed

### Header Bar
- Title: "Interverse"
- Two toggle buttons: **Ecosystem** (active, blue) and **Sprint** (active, green)
- Stats: "123 nodes · 185 edges · 11 domains · Generated 2/21/2026"
- Search box (top right)
- Hamburger menu (top left, below header)

### Sprint Phase Pipeline (10 phases in a racetrack/horseshoe layout)

The sprint phases are rendered as rectangular boxes arranged in a U-shape around the viewport edges:

| # | Phase | Category | Artifact | Position |
|---|-------|----------|----------|----------|
| 1 | Brainstorm | ideation | brainstorm doc | top-left |
| 2 | Strategize | ideation | PRD + feature beads | upper-left |
| 3 | Write Plan | planning | implementation plan | top-center |
| 4 | Review Plan | planning | review verdict | upper-right |
| 5 | Execute | building | code changes | top-right |
| 6 | Test | building | test results | bottom-right |
| 7 | Quality Gates | quality | review reports | lower-right |
| 8 | Resolve | quality | resolved findings | bottom-center |
| 9 | Reflect | learning | learnings doc | lower-left |
| 10 | Ship | shipping | merged PR / pushed commits | bottom-left |

Each box shows: phase number, phase name (bold), category label, and artifact description.

Blue directional arrows connect sequential phases (1→2→3→4→5↓6→7→8→9→10).

Gate labels appear between certain phases:
- "Plan approved" between Write Plan → Review Plan
- "Plan exists" between Review Plan → Execute
- "Tests pass" between Execute/Test → Quality Gates
- "Findings resolved" between Resolve → Reflect
- "skip (trivial tasks)" shortcut arrow from Strategize area

### Ecosystem Force Graph (D3)

The ecosystem graph occupies the center of the viewport with 123 nodes representing:
- **Plugins** (colored circles, ~30 plugins): intercheck, intercraft, interdev, interdoc, interfluence, interflux, interform, interject, interkasten, interlearn, interleave, interlens, interline, interlock, intermap, intermem, intermux, internext, interpath, interpeer, interphase, interpub, intersearch, interserve, interslack, interstat, intersynth, intertest, interwatch, tldr-swinton, tool-time, tuivision
- **Skills** (smaller circles): Each plugin has child skill nodes (e.g., flux-drive, flux-research, fd-architecture, etc. under interflux)
- **Hub components**: clavain (large node), with many skill children (brainstorming, code-review-discipline, dispatching-parallel-agents, etc.)
- **Services/SDK**: Intercore, Intermute, Interbase, Autarch
- **Hooks**: PostToolUse, PreToolUse, SessionStart, SessionEnd, Stop
- **Domain clusters**: 11 domains visible as cluster labels (Analytics/Observability, Coordination/Dispatch, Design/Product, Discovery/Context Stack, etc.)

Edges (185 total) connect plugins to skills, plugins to domains, and components to each other. The domain clusters show as semi-transparent polygonal hulls.

### Visual Characteristics of the Combined View

**Color coding:**
- Sprint phase boxes: dark background with colored borders (orange for ideation, green for building, etc.)
- Ecosystem nodes: domain-colored circles (blue, green, orange, pink, teal, red)
- Interverse hub node: large light blue circle at center
- Clavain: medium blue-green circle with many radiating skill edges

**Layout interaction:**
- The ecosystem force graph is centered and occupies roughly the middle 60% of the viewport
- Sprint phase boxes are positioned around the periphery in a racetrack pattern
- Phases 3 (Write Plan), 4 (Review Plan), 7 (Quality Gates), 8 (Resolve) sit AT the edges of the ecosystem graph, causing overlap
- Phase 8 (Resolve) directly overlaps with the interject, intermem, and interfluence cluster area
- Phase 3 (Write Plan) overlaps with the interdev skill labels area

---

## Overlap / Clutter Analysis

### Quantitative Overlap
- **Total text elements:** 179
- **Overlapping text pairs:** 78 (43.6% pairwise overlap rate)
- This is HIGH — nearly half of all possible label pairs in proximity are physically overlapping

### Worst Overlap Zones

1. **Center (y: 400-600, x: 800-1000):** The Resolve phase box (phase 8) sits directly on top of the interject, interdoc, interfluence, intermem cluster. Labels are unreadable.

2. **Upper-center (y: 280-340, x: 760-960):** Write Plan phase box overlaps with interdev skills (working-with-claude-code, developing-claude-code-plugins, create-agent-skills, writing-skills). The phase metadata text ("planning", "implementation plan") merges with skill labels.

3. **Right-center (y: 400-600, x: 1050-1200):** Quality Gates and Review Plan boxes overlap with clavain's skill satellite nodes (code-review-discipline, executing-plans, dispatching-parallel-agents, etc.).

4. **Interflux cluster (y: 850-960, x: 950-1100):** The interflux plugin with its 12+ flux-drive skill children is extremely dense. Labels like fd-architecture, fd-correctness, fd-user-product, fd-quality, fd-game-design, fd-performance, fd-systems, fd-decisions, fd-people, fd-resilience, fd-perception plus the researcher skills ALL overlap each other. This is an ecosystem-only problem (not caused by sprint overlay).

5. **Domain cluster labels:** "Analytics Observability" and "Analytics Quality Stack" overlap at the same position (x:909, y:634). "Discovery Context Stack" and "Discovery Research" overlap at similar y positions. The cluster hull labels need more spacing.

### Can You Make Out the Participates-In Edges?

**Barely.** There appear to be thin connecting lines between some ecosystem nodes and sprint phase boxes, but they are:
- Very thin (1-2px) and low contrast against the dark background
- Lost in the web of ecosystem edges (185 edges already connecting nodes)
- Not clearly distinguishable from the ecosystem's own inter-node edges
- The blue directional arrows between sprint phases are clearly visible, but the "participates-in" edges from ecosystem nodes to phases are not prominent enough

---

## Recommendations

1. **Spatial separation:** The sprint racetrack needs more padding from the ecosystem graph center. Either push the phase boxes further to the edges, or shrink/offset the ecosystem graph when sprint view is active.

2. **Participates-in edge styling:** These edges need to be visually distinct — consider dashed lines, a unique color (e.g., gold/amber), or animated particles to differentiate from ecosystem structural edges.

3. **Interflux density:** The interflux cluster with 12+ fd-* children needs a collapse/expand interaction, or the children need radial spacing. Even without the sprint overlay, this area is unreadable.

4. **Domain cluster label deduplication:** Some domain names appear at identical positions. The hull label placement algorithm should check for collision and offset.

5. **Z-ordering:** Sprint phase boxes should render above ecosystem content with a subtle backdrop blur or shadow to create visual hierarchy.

6. **Zoom-to-fit:** When both views activate, the viewport should auto-zoom to fit all content with margins, rather than maintaining the ecosystem-only zoom level.

---

## Raw Data

### SVG Stats
- SVG dimensions: 1920 x 1036
- SVG child groups: 2 (likely ecosystem-layer and sprint-layer)
- Circles: 133
- Lines: 183
- Paths: 18
- Rects: 10
- Texts: 179

### Toggle State (confirmed)
- Ecosystem: active (class: `toggle-btn active`)
- Sprint: active (class: `toggle-btn active`)
- Both toggles confirmed active after click
