# Plan: Formalize Interactive-to-Autonomous Shift-Work Boundary

**Bead:** `iv-xweh`
**Date:** 2026-02-19

## Inputs
- Design reference: `hub/clavain/docs/research/shift-work-boundary.md`
- Flux-drive review notes on boundary and safety constraints (bead notes)

## Goal
Make the shift from interactive planning to autonomous execution explicit, measurable, and safe within Clavain workflows.

## Scope
- Define spec-completeness gate criteria.
- Reuse existing clodex toggle (no new parallel mode).
- Add human-confirmed checklist gate before autonomous switch.
- Add pause/escape hatch and mandatory incremental commit checkpoints.

## Milestones
1. Boundary contract
Define explicit entry conditions for autonomous execution (plan completeness, tests/scenarios, acceptance criteria).

2. Gate implementation
Implement structured completeness check and confirmation flow.

3. Execution safety controls
Add pause/resume controls, batch ceiling, and commit cadence guardrails.

4. Docs + workflow updates
Update `/lfg` and related workflow docs with named boundary semantics.

## Dependency Plan
- No hard blockers; design and contract work can proceed now.
- Coordinate with quality-gate and execution orchestration logic owners.

## Validation Gates
- Autonomous mode activates only when completeness checks pass.
- Users can reliably pause/override autonomous execution.
- Post-change runs show reduced ambiguity at interactive/autonomous handoff.

## Risks and Mitigations
- Heuristic false positives: prefer explicit checklist artifacts over fragile text grep.
- UX friction: keep confirmation concise and allow explicit override.
- Safety regressions: enforce commit checkpoints and rollback instructions.
