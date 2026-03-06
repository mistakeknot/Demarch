---
artifact_type: brainstorm
bead: iv-ey5wb
stage: brainstorm
---
# Brainstorm: Vision/Philosophy/Roadmap Alignment

**Bead:** iv-ey5wb
**Date:** 2026-03-06

## Problem Statement

The bead's analysis identified that Demarch has a strong philosophical core and a real working system, but the top-level documents have drifted apart. The roadmap has 719 open items, the vision references bead priorities that have since changed, and status counts differ across surfaces. This is the kind of silent drift that PHILOSOPHY.md specifically warns about: "Stale documentation is silent technical debt."

## Current State of the Five Gaps

### Gap 1: Roadmap Overload
The roadmap has 48 "now" items, 132 "next" items, 50 "later" items. That's not a roadmap — it's an inventory. A top-level roadmap should answer "what are the 5-10 things that define the next phase?" The auto-generated module table (61 rows) is useful as a reference section but shouldn't be the spine of the document.

**What changed since the analysis:** iv-30zy3 (session attribution) just shipped, iv-r6mf (routing overrides) was already done. Some P0s have been completed but the doc doesn't reflect it.

### Gap 2: Drift Between Vision and Roadmap
The vision (v3.1, dated 2026-02-27) says:
- The north-star metric "had never been measured" — but a baseline was computed on 2026-02-28
- Lists iv-ho3 as a P0 — but in the live bead system it's P2/open
- Lists iv-r6mf as the P0 frontier — but it was already implemented (closed this session)
- Says "8 of 10 epics shipped" — current kernel state has progressed further

### Gap 3: Autonomy Boundary Contradiction
The vision says "never pushes code to a remote repository without human confirmation" as an invariant that "holds regardless of autonomy level." The philosophy's trust ladder says Level 4 is "Agent proposes policy changes" and the autonomy ladder says Level 4 is "Auto-ship." These are in tension unless "human confirmation" can mean "policy-level approval" rather than "per-push confirmation." This needs explicit clarification.

### Gap 4: Missing Module Roadmaps
The roadmap table shows 26 modules without roadmaps (marked "no"). Interspect — central to the adaptive routing thesis — is listed as "early" with no roadmap. This is a meaningful gap because interspect IS the flywheel engine.

### Gap 5: Status Count Inconsistency
The roadmap header says "719 open / 78 blocked." Live `bd stats` shows "698 open / 68 blocked." The vision references different counts. These are likely different scopes (live vs snapshot), but the reader can't tell.

## Proposed Solutions

### Option A: Surgical Fixes (Minimal)
Fix the factual errors, update stale numbers, clarify the autonomy boundary. Don't restructure.
- Effort: 30 minutes
- Risk: Low
- Impact: Low — fixes symptoms but the roadmap remains an inventory

### Option B: Compress and Align (Recommended)
1. Rewrite the roadmap "Now" section to 5-10 true frontier items
2. Move the full module inventory to a generated appendix section
3. Update the vision "Where We Are" section with current facts
4. Clarify the autonomy boundary in both vision and philosophy
5. Make status counts self-documenting (state their scope)

- Effort: 2-3 hours
- Risk: Medium — touching multiple docs, need to be careful not to lose context
- Impact: High — aligns the three core docs into a coherent narrative

### Option C: Full Rewrite
Rewrite vision v4.0 from scratch, rebuild roadmap structure, update philosophy.
- Effort: Full day
- Risk: High — might lose hard-won nuance in the philosophy
- Impact: Unclear — the philosophy is already excellent, rewriting risks degrading it

## Recommendation

**Option B.** The philosophy is strong and shouldn't be touched (except the autonomy clarification). The vision needs a factual update, not a rewrite. The roadmap needs structural compression, not more content. The key principle: make each doc serve its purpose without duplicating or contradicting the others.

## Scope Constraints

- Do NOT rewrite PHILOSOPHY.md beyond the autonomy clarification
- Do NOT change the architectural structure or naming
- DO update factual claims with current evidence
- DO compress the roadmap to a true strategic document
- DO make scope/sourcing of counts explicit
