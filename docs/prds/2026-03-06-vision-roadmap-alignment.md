---
artifact_type: prd
bead: iv-ey5wb
stage: design
---
# PRD: Vision/Philosophy/Roadmap Alignment

## Problem
Demarch's three top-level docs (PHILOSOPHY.md, demarch-vision.md, demarch-roadmap.md) have drifted apart. Factual claims in the vision are stale, the roadmap is an inventory of 230+ items rather than a strategic program, and status counts are inconsistent across surfaces.

## Solution
Surgically compress and align the three docs: update the vision with current facts, compress the roadmap to 5-10 true frontier items with a generated inventory appendix, clarify the autonomy boundary, and make status counts self-documenting.

## Features

### F1: Roadmap Compression
**What:** Restructure the roadmap "Now" section from 48 items to 5-10 true frontier priorities, moving the rest to a generated appendix.
**Acceptance criteria:**
- [ ] "Now" section has ≤10 items, each with a clear 1-sentence description of why it's frontier
- [ ] Full bead inventory is preserved in an appendix section labeled "Generated Inventory"
- [ ] Module ecosystem table remains as reference (no changes)

### F2: Vision Factual Update
**What:** Update the "Where We Are" section of demarch-vision.md with current facts.
**Acceptance criteria:**
- [ ] North-star metric section reflects that baseline was measured (2026-02-28)
- [ ] P0 priorities list reflects current bead states (iv-r6mf closed, iv-30zy3 closed)
- [ ] "8 of 10 epics shipped" count is updated to current kernel state
- [ ] Version bumped to 3.2, date updated to 2026-03-06

### F3: Autonomy Boundary Clarification
**What:** Clarify the tension between "never pushes without human confirmation" and Level 4 auto-ship.
**Acceptance criteria:**
- [ ] Vision doc explicitly states that "human confirmation" at L4 means policy-level approval, not per-push confirmation
- [ ] Philosophy doc's trust ladder cross-references the vision's autonomy ladder with a note explaining the orthogonality

### F4: Status Count Consistency
**What:** Make all status counts in vision and roadmap self-documenting about their scope and source.
**Acceptance criteria:**
- [ ] Each status count states its source (e.g., "698 open beads per `bd stats` as of 2026-03-06")
- [ ] Vision and roadmap either use the same scope or explain the difference

### F5: Interspect Roadmap Coverage
**What:** Add roadmap coverage for Interspect, which is central to the adaptive routing thesis.
**Acceptance criteria:**
- [ ] Interspect has a "Roadmap" column value of "yes" in the ecosystem table (or an explanation of what exists)
- [ ] At minimum, the roadmap references interspect-vision.md as the planning doc

## Non-goals
- Rewriting PHILOSOPHY.md (it's excellent as-is, only the autonomy cross-reference is in scope)
- Adding new modules or changing the architecture
- Generating module-level roadmaps for all 26 modules without them
- Changing the naming convention or pillar structure

## Dependencies
- Live `bd stats` output for current counts
- Current bead states for P0 priority updates
- Existing interspect-vision.md for roadmap coverage

## Open Questions
- Should the roadmap "Now" items be linked to beads or free-standing descriptions? (Recommendation: keep bead links for traceability)
