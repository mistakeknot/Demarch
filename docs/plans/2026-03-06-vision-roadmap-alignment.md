---
artifact_type: plan
bead: iv-ey5wb
stage: executing
---
# Vision/Roadmap Alignment — Implementation Plan

**Goal:** Align Demarch's three top-level docs (PHILOSOPHY.md, demarch-vision.md, demarch-roadmap.md) so they tell a coherent, factually current story.

**Architecture:** Pure docs work — no code changes. Edit markdown files only.

**Bead:** iv-ey5wb

---

### Task 1: Update vision "Where We Are" section (F2)

**Files:**
- Modify: `docs/demarch-vision.md`

**Step 1:** Update the "Where We Are" section:
- [x] Change "has never measured" the north-star to reference the 2026-02-28 baseline
- [x] Update "8 of 10 epics shipped" to reflect current kernel state
- [x] Update the P0 priority list under "What's Next" to reflect current states:
  - iv-r6mf: CLOSED (routing overrides shipped)
  - iv-30zy3: CLOSED (session attribution shipped)
  - iv-ho3: note that it's P2 in the live system, not P0
  - iv-b46xi: note the baseline was measured
- [x] Bump version to 3.2 and date to 2026-03-06

**Step 2:** Update the "Status" field from "Draft" to "Active" (the vision has been active for months)

---

### Task 2: Clarify autonomy boundary (F3)

**Files:**
- Modify: `docs/demarch-vision.md` (Design Principles § Gates, and § Autonomy Ladder)
- Modify: `PHILOSOPHY.md` (§ Earned Authority, trust ladder note)

**Step 1:** In demarch-vision.md, find the "never pushes code to a remote repository without human confirmation" statement. Add clarification:
- [x] At L0-L2: per-change human confirmation (current operating level)
- [x] At L3: human sets shipping policy (which repos, which thresholds)
- [x] At L4: human approves the policy; agent pushes when policy conditions are met

**Step 2:** In PHILOSOPHY.md § Earned Authority, after the trust ladder, add a 1-sentence cross-reference:
- [x] Note that the vision's autonomy ladder (L0-L4) tracks system capability, which is orthogonal to the trust delegation ladder here. (This note already partially exists at line 106.)

---

### Task 3: Compress roadmap "Now" section (F1)

**Files:**
- Modify: `docs/demarch-roadmap.md`

**Step 1:** Read the current "Now" section and identify the true frontier items (items that are actively being worked or that unblock significant downstream work).

**Step 2:** Rewrite the "Now" section with 5-10 true frontier priorities:
- [x] Each item gets a 1-sentence "why this is frontier" rationale
- [x] Bead IDs preserved for traceability
- [x] Recently-completed items moved out of "Now"

**Step 3:** Move the full current "Now" item list to a "### Detailed Now Inventory" subsection or appendix:
- [x] Preserves all information for reference
- [x] Clearly labeled as auto-generated/inventory

**Step 4:** Clean up the "Recently completed" section:
- [x] Remove state-change noise (claimed_at/claimed_by entries)
- [x] Replace with actual completed beads with their descriptions

---

### Task 4: Fix status counts (F4)

**Files:**
- Modify: `docs/demarch-roadmap.md` (header)
- Modify: `docs/demarch-vision.md` (where counts appear)

**Step 1:** Run `bd stats --allow-stale` to get current counts.

**Step 2:** Update the roadmap header with current counts and explicit scope:
- [x] Format: "**Open beads:** 698 (per `bd stats`, 2026-03-06)"
- [x] Include closed count for context

**Step 3:** Ensure vision doc's counts match or explain the difference.

---

### Task 5: Add Interspect roadmap coverage (F5)

**Files:**
- Modify: `docs/demarch-roadmap.md` (ecosystem table, interspect row)

**Step 1:** Check if `docs/interspect-vision.md` exists (it's referenced in demarch-vision.md).

**Step 2:** Update the interspect row in the ecosystem table:
- [x] Change roadmap column from "no" to link to interspect-vision.md (covers planning)
- [x] Or add a note in the roadmap referencing the vision doc as the planning surface

---

### Task 6: Commit and verify

**Step 1:** Verify no broken links or factual errors in the updated docs.

**Step 2:** Commit all changes:
```bash
git add docs/demarch-vision.md docs/demarch-roadmap.md PHILOSOPHY.md
git commit -m "docs: align vision/philosophy/roadmap (iv-ey5wb)"
```
