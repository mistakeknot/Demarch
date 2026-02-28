# Disagreement → Resolution → Routing Signal Pipeline

**Bead:** iv-5muhg
**Date:** 2026-02-28

## What We're Building

A pipeline that captures when review agents disagree, records how humans resolve the disagreement, and feeds that resolution as a routing signal to Interspect. This implements the learning loop from PHILOSOPHY.md: "disagreement at time T, human resolution at T+1, routing signal at T+2."

The pieces exist but aren't connected:
- **T (disagreement):** interflux synthesis detects conflicts via deduplication Rules 4-5, producing `severity_conflict` metadata on findings
- **T+1 (resolution):** clavain:resolve records outcomes via `_trust_record_outcome()` in intertrust
- **T+2 (routing signal):** interspect consumes evidence via `_interspect_insert_evidence()` and applies routing overrides

The gap: no code takes a resolution event from T+1 and feeds it as evidence to interspect at T+2.

## Why This Approach

**Event-driven via kernel** — emit a new `disagreement_resolved` event type through intercore's event system, then have interspect's cursor consumer pick it up asynchronously.

Why not a thin shell wire in clavain:resolve?
- The event bus already exists and interspect already has a cursor consumer registered
- Kernel events are durable, replayable, and content-addressed (Gridfire envelopes)
- Decouples the resolution action from the routing signal — resolve doesn't need to know about interspect
- Aligns with OODAR Phase 2 direction — formalizing event types for Orient/Decide

## Key Decisions

1. **Integration point: clavain:resolve** — When a finding with `severity_conflict` is resolved and the resolution changes a decision, resolve emits a `disagreement_resolved` event to the kernel
2. **Impact-gated threshold** — Only emit when the resolution changed a decision (discarded a high-severity finding, or accepted despite disagreement). Matches PHILOSOPHY.md: "does resolving this change a decision? If yes, amplify."
3. **New intercore event type** — `disagreement_resolved` event in Go with envelope, emitted through existing event.Store
4. **Interspect cursor consumer** — Interspect's existing cursor picks up the new event type and calls `_interspect_insert_evidence()` to create evidence records
5. **Schema carries conflict context** — The event payload includes: finding_id, agents involved, their severity ratings, which was chosen, and why

## Disagreement Event Schema

```
disagreement_resolved event:
  source: "review"
  type: "disagreement_resolved"
  payload:
    finding_id: string          # interflux finding ID
    agents: map[string]string   # agent_name → severity (the severity_conflict map)
    resolution: string          # "accepted" | "discarded" | "modified"
    chosen_severity: string     # the final severity after resolution
    impact: string              # "decision_changed" | "severity_overridden"
    session_id: string          # for trace linkage
    project: string             # project context
  envelope: (standard Gridfire envelope)
```

## Flow

```
interflux synthesis          clavain:resolve           intercore events          interspect
────────────────────         ──────────────            ───────────────           ──────────
Detect severity_conflict  →  Human accepts/discards →  Emit disagreement_     → Cursor consumer
on finding                   finding                   resolved event            picks up event
                                                                               → Insert evidence
                                                                               → Evaluate for
                                                                                 routing override
```

## What Exists Already

| Component | File | What it does |
|-----------|------|--------------|
| Conflict detection | interflux synthesis Rules 4-5 | Detects severity_conflict, preserves both ratings |
| Trust feedback | intertrust `_trust_record_outcome()` | Records accepted/discarded with severity weighting |
| Evidence insertion | interspect `_interspect_insert_evidence()` | Creates evidence rows with sanitization |
| Event store | intercore `event.Store` | Durable event bus with cursor support |
| Cursor consumer | interspect cursor registration | `ic events cursor register interspect-consumer` |
| Routing overrides | interspect routing-overrides.json | Agent-scoped overrides with canary support |

## What We Need to Build

1. **New event type in intercore** — `disagreement_resolved` in the event schema, emittable through event.Store
2. **Emit logic in clavain:resolve** — detect severity_conflict on resolved finding, check impact gate, emit event via `ic events emit`
3. **CLI command: `ic events emit`** — currently events are read-only from CLI (only `tail` and `cursor`). Need an emit subcommand for external producers
4. **Consumer logic in interspect** — extend cursor consumer to handle `disagreement_resolved` events and convert to evidence records

## Open Questions

- Should the impact gate be configurable (e.g., minimum severity spread before emitting)?
- Should we batch evidence insertion or insert per-event?
- How do we handle disagreements that are never resolved (finding ignored)?
