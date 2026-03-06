---
artifact_type: brainstorm
bead: iv-godia
stage: brainstorm
---
# Brainstorm: Capture Routing Decisions as Replayable Kernel Facts

**Bead:** iv-godia
**Date:** 2026-03-06

## Problem

Routing offline eval (iv-sksfx.1) needs to answer: "What if we had used a different model for this agent?" Today, routing decisions are ephemeral — `ic route model` computes the result and prints it, but nothing is persisted. To build counterfactual rows, you'd have to infer decisions from dispatch records (which model was used?) and guess which routing rule produced it. That's fragile and incomplete.

## What Needs to Be Captured

A routing decision record needs to reconstruct one review/agent opportunity:

1. **Input context:** phase, category, agent name, project, dispatch/run/session IDs for join
2. **Resolution trace:** which rule won (override, phase-category, phase-model, default-category, default, fallback), the policy version (routing.yaml hash), whether a safety floor was applied and what it clamped from→to
3. **Candidate/selected sets:** all models that were eligible, which was selected, which were excluded (by floor or override)
4. **Routing context:** complexity score, bead ID, any Interspect override active at decision time

This is distinct from dispatch records (which track execution) — a routing decision happens *before* dispatch and determines *which model* the dispatch uses.

## Design

### Option A: New table `routing_decisions`
Add a v27 migration with a `routing_decisions` table. Store follows landed/session pattern. CLI adds `ic route record` and `ic route list`.

### Option B: Extend events table
Use the existing `events` table with `kind=routing_decision` and JSON payload.

### Recommendation: Option A
A dedicated table is better because:
- Typed columns enable efficient SQL queries for counterfactual analysis (WHERE selected_model != ?)
- JOIN to dispatches via dispatch_id is clean
- The landed/session store pattern is well-established

## Scope

- v27 migration: `routing_decisions` table
- `internal/routing/decision.go`: Decision store (Record, Get, List)
- `cmd/ic/route.go`: `ic route record` and `ic route list` subcommands
- Tests following session/landed patterns
- NOT in scope: wiring into actual routing calls (that's the caller's job — Clavain's route.md)
