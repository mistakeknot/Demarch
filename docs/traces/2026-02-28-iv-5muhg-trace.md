# Integration Trace: iv-5muhg — Disagreement → resolution → routing signal pipeline

**Date:** 2026-02-28
**Bead:** iv-5muhg (closed)
**Tracer:** intertrace v0.1.0

## Scope

Files traced: 15 (across 3 commits in 4 repos: root monorepo, intercore, clavain, interspect)
Tracers run: event-bus, contracts, companion-graph

## Event Bus Findings

### `disagreement_resolved` (producer: os/clavain/commands/resolve.md:155)

| Consumer | Verified | Evidence |
|----------|----------|----------|
| interverse/interspect | Yes | cursor registration + hook_id allowlist |

The event pipeline is correctly wired post-fix. Before the iv-5muhg fixes, the interspect hook_id allowlist was missing this event type — the pipeline was silently inert.

## Contract Findings

7 contracts with unverified consumers (monorepo-wide scan):

| Contract | Unverified Consumer | Confidence |
|----------|-------------------|------------|
| `phase.advance` | Interspect | P1 — declared consumer, no direct code evidence found |
| `dispatch.status_change` | Clavain hooks, Interspect | P1 — declared consumers, no direct code evidence found |
| `coordination conflicts` | Interlock MCP | P2 — grep pattern may not match actual invocation |
| `discovery list` | Clavain bash | P2 — grep pattern may not match actual invocation |
| `discovery profile` | Clavain bash | P2 — grep pattern may not match actual invocation |
| `scheduler stats` | Clavain bash | P2 — grep pattern may not match actual invocation |
| `config get` | Clavain bash | P2 — grep pattern may not match actual invocation |

### Analysis

The P1 findings (`phase.advance`, `dispatch.status_change`) are worth investigating — Interspect is declared as a consumer of these event types in contract-ownership.md but the tracer found no direct code reference. This could be a real integration gap or a grep pattern miss (interspect may consume these indirectly through `ic events tail --all`).

The P2 findings are likely false negatives — the tracer greps for the exact contract name (e.g., `discovery list`) but Clavain invokes these as `ic discovery list` or parses their JSON output, which may not match the grep pattern verbatim.

## Companion Graph Findings

16/16 edges verified. No unverified edges found.

## Validation Against Known iv-5muhg Gaps

The iv-5muhg sprint found 5 integration gaps. Intertrace's ability to rediscover them:

| Gap | Detectable? | Notes |
|-----|------------|-------|
| 1. interspect hook_id not in allowlist | Yes (post-fix shows verified; pre-fix would show hook_id_allowlist_missing) | Core strength of event tracer |
| 2. `ic state set` stdin vs positional args | No | Code correctness bug, not an integration gap — out of scope |
| 3. Scope ID mismatch between get/set | No | Code correctness bug, not an integration gap — out of scope |
| 4. `_ = insertReplayInput(...)` discarded error | No | Go code quality bug — out of scope |
| 5. galiana/interwatch not consuming disagreement events | Partially — contract tracer finds unverified Interspect consumers for event contracts | Would need galiana/interwatch in contract-ownership as declared consumers to fully detect |

**Result: 1 of 4 integration gaps directly detectable, 1 partially detectable.** Gaps #2-4 are code correctness bugs that require deeper analysis than edge verification. Gap #5 is only detectable if the expected consumers are declared somewhere (contract-ownership, companion-graph, or AGENTS.md).
