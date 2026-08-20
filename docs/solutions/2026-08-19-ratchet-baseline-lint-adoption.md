---
artifact_type: solution
stage: compound
category: quality-gates
tags: [lint, ratchet, baseline, brownfield, gates, ci, adoption, waivers]
---

# Adopting a lint gate on brownfield: ratchet the baseline, waiver the known

Solved 2026-08-19 in `bridger` (`tools/lint_senses.py`, `tools/lint_rooms.py`,
`reviews/senses-baseline.json`, `reviews/room-waivers.json`) while gating a
corpus with 322 pre-existing defects and two known-bad-but-live rooms.

## The trap: a new gate on old content can only block or lie

Write a strict lint for an existing corpus/codebase and you get one of two
failure modes. Either the gate fails on day one over defects nobody is fixing
this quarter (so it gets disabled or skipped, and now catches nothing), or you
loosen the checks until the existing content passes (and the gate no longer
catches the defect class you built it for). A third variant: fix-everything-
first, which turns "add a gate" into an unbounded cleanup project and the gate
ships never.

## The pattern: two channels for two kinds of known-bad

1. **Ratchet baseline** for bulk defects: run the lint once, freeze every
   current finding into a committed baseline file keyed by a stable defect
   identity (`domain|kind|detail|sense`, not line numbers — lines shift).
   The gate fails only on findings NOT in the baseline. New rot fails
   immediately; the 322 old defects become a triage backlog, not a blocker.
   When one is fixed, the gate prints "N baseline defects no longer present;
   tighten with --write-baseline" — the ratchet only turns one way if you
   re-freeze on green.
2. **Dated waivers** for individually known exceptions: a small JSON of
   `{item: {reason, since}}` where the reason names why it is exempt and what
   unblocks it ("over-length trim is an edit-lane call for mk"). Waived items
   print loudly as WAIVED with their violations — green but never silent.

Both files are committed and reviewed like code; the diff of a baseline or a
waiver IS the review surface for "we are choosing to live with this."

## Why not one mechanism

A baseline is for populations (hundreds of findings, triaged in bulk, burned
down over time). A waiver is for individuals (this one item, this stated
reason, this owner). Folding waivers into the baseline hides the reason;
folding the baseline into waivers makes 322 hand-entries nobody reads.

## Prevention

- Defect identity must survive unrelated edits, or the ratchet churns.
- The gate must exit non-zero on new findings even while the baseline is
  huge — a warning-only gate is a dashboard, not a gate.
- Print fixed-but-still-baselined counts so shrinkage is visible and the
  re-freeze is deliberate.

Related: [`2026-08-19-corrections-overlay-for-derived-data.md`](2026-08-19-corrections-overlay-for-derived-data.md)
— where the fixes themselves must land when the linted content is derived.
