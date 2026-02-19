# Plan: Blueprint Distillation for Sprint Intake

**Bead:** `iv-6i37`
**Date:** 2026-02-19

## Inputs
- Synthesis brainstorm: `docs/brainstorms/2026-02-16-clavain-token-efficiency-synthesis-brainstorm.md`
- Token efficiency research: `docs/research/token-efficiency-agent-orchestration-2026.md`
- Related threads: `iv-cu5w`, `iv-1zh2.4`

## Goal
Add an explicit blueprint-distillation step in sprint intake to compress high-entropy source docs into structured, execution-ready constraints.

## Scope
- Define blueprint artifact schema (constraints, invariants, must-not-breaks, validation hooks).
- Integrate blueprint step into brainstorm/strategy/plan flow.
- Persist blueprint artifact for reuse across sessions.
- Add quality checks that prevent narrative-noise propagation.

## Milestones
1. Artifact contract
Define required fields and quality bar for blueprint output.

2. Pipeline insertion
Insert blueprint extraction into strategy path before planning.

3. Persistence and retrieval
Store artifacts for reuse in later plan/execute stages.

4. Evaluation
Compare plan quality and token usage with/without blueprint step.

## Dependency Plan
- Depends on closed token-budget groundwork (`iv-8m38`) only for measurement framing; implementation can proceed.
- Coordinate with handoff artifact work for schema alignment.

## Validation Gates
- Plans generated from blueprints retain critical constraints.
- Measurable token reduction in plan intake context.
- Human review shows less noise and better actionability.

## Risks and Mitigations
- Over-abstraction can omit nuance: keep trace links back to source sections.
- Added workflow step may slow throughput: allow skip/override for simple tasks.
