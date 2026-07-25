---
artifact_type: goal-charter
bead: Sylveste-rfs
complexity: 2
stage: goal-formed
---

# Goal Charter: Interline Sideband Cutover — Retire the Interphase Writer

## Why (leverage)

KD 11 consumer-migration, final step. Research findings (2026-07-20): the
cutover is further along than the bead assumed — interline's statusline
reader already prefers the kernel-authored interband envelope
(`statusline.sh:308`) with a legacy `/tmp` fallback, and envelope parity is
test-proven (clavain-cli `sideband_test.go`, shipped 0.6.278). What remains
is retiring the duplicate interphase writer (`_gate_update_statusline`,
lib-gates.sh — exactly one call site at :493) so the kernel is the single
sideband authority, per f-005's ordering rule: the reader keeps its legacy
fallback and the kernel keeps dual-writing until one clean release.

Ceremony note: classifier said C4 via the blast-radius keyword bump
("retire/drop" on a cosmetic statusline surface); mk ratified C2 override —
logged as calibration evidence for the bump heuristic.

## Scope

**In:**
1. Retire `_gate_update_statusline` in
   `interverse/interphase/hooks/lib-gates.sh` — remove the function and its
   single call site (line ~493); interphase stops writing both sideband
   paths.
2. Regression test proving the reader renders bead+phase from a
   kernel-authored interband envelope alone (no legacy `/tmp` file present).
3. Follow-up bead: drop the legacy `/tmp/clavain-bead-*` path from the
   kernel writer AND the reader fallback after one clean release
   (0.6.279+). That bead is this goal's successor.

**Out:**
- Legacy-path removal itself (soaks one release, per mk's sequencing call).
- interphase's broader retirement (separate KD 11 arc).

**Accepted residual risk (mk-ratified, C2):** phase transitions that flow
only through interphase gate-advance (not clavain-cli sprint-advance) lose
sideband updates until interphase itself retires. Cosmetic — statusline
display only; the bd-query layer (statusline step 1.5b) still shows
in-progress beads.

## Acceptance criteria

1. `_gate_update_statusline` and its call site are gone from interphase;
   `grep -rn "_gate_update_statusline\|clavain-bead" interverse/interphase/hooks/`
   returns no writer code.
2. Regression test passes: with only a kernel-authored envelope on disk
   (no `/tmp` sideband), the statusline renders the bead id and phase.
3. interphase and interline test suites pass.
4. Follow-up legacy-removal bead filed and referenced as successor.
5. Work committed; Sylveste-rfs closed with evidence.

## Completion condition (literal — handed to /goal)

Interline sideband cutover complete: interphase's _gate_update_statusline
writer and its call site removed; a regression test proving the statusline
renders bead+phase from a kernel-authored interband envelope alone (no
legacy /tmp file) passes with exit 0 shown in surfaced output; interphase
and interline test suites pass; a follow-up bead for legacy /tmp path
removal after one clean release is filed; work committed and bead
Sylveste-rfs closed with evidence. Or stop after 25 turns.

## Successor obligations

The legacy-path-removal bead (filed inside this goal) is the recorded
successor.
