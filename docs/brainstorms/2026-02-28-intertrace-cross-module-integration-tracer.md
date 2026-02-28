---
bead: iv-4iy6g
type: brainstorm
date: 2026-02-28
status: active
---

# Intertrace — Cross-Module Data Flow Integration Tracer

**Bead:** iv-4iy6g

## What We're Building

A Clavain companion plugin that automates cross-module integration gap discovery. Given a recently shipped feature (via bead ID), intertrace walks the monorepo module graph to find consumers that should read the new data but don't. Produces ranked findings for human triage, with optional bead creation for confirmed gaps.

**Origin:** During the iv-5muhg disagreement pipeline sprint, 5 integration gaps were found manually across 4 modules (intersynth, interspect, clavain/galiana, interwatch) — all shipped same session. The manual process (reading PHILOSOPHY.md + grepping code + tracing data flow by hand) is exactly what intertrace automates.

## Why This Approach

**Thin plugin over intermap, not a new MCP server.** Intertrace is a stateless analyzer — it runs, produces output, and exits. No persistent state, no expensive initialization, no real-time queries. It calls intermap's existing MCP tools (project_registry, cross_project_deps, code_structure, impact_analysis) and adds gap-detection logic on top.

This follows the newly codified MCP server criteria: new servers only for persistent state, expensive init, real-time queries, or external service bridges. Stateless analysis uses skills + shell libs.

## Key Decisions

### 1. Trigger Model — Phased Delivery

| Phase | Trigger | Deliverable |
|-------|---------|-------------|
| 1 | Post-ship audit (`/intertrace <bead-id>`) | Slash command + shell tracers |
| 2 | Review-time (`fd-integration` agent) | Interflux review agent |
| 3 | On-demand monorepo scan (`/intertrace --scan`) | Full-graph analysis |

Phase 1 is the primary deliverable. Phase 2 adds preventive catching during flux-drive. Phase 3 is the long-term systemic view.

### 2. Input Model — Bead ID

```
/intertrace iv-5muhg

1. bd show iv-5muhg → bead metadata
2. Find commits mentioning iv-5muhg → changed files
3. intermap code_structure on changed files → new functions/events
4. For each new producer: find expected consumers
5. For each expected consumer: verify code evidence
6. Output: gap list ranked by evidence strength
```

Bead ID is the primary input. Clean integration with the beads workflow — every shipped feature already has a bead.

### 3. Data Sources — Phased Expansion

**Phase 1 (machine-readable, high signal):**
- Event bus: `ic events emit` calls → who consumes? (cursor registrations, hook_id allowlists)
- Contracts: `contract-ownership.md` declared consumers → code evidence exists?
- Companion graph: `companion-graph.json` edges → import/call/source evidence exists?

**Phase 2 (heuristic, medium signal):**
- Shell lib sourcing: `lib-*.sh` discovery patterns → which plugins source which libraries?
- MCP tool cross-references: `plugin.json` env/server refs beyond INTERMUTE

**Phase 3 (prose parsing, lower signal):**
- AGENTS.md "Integration Points" table scraping → structured edge declarations

No config file — tracers are enabled as they ship. The tracer interface is uniform: input (edge declaration) → output (verified/unverified + evidence).

### 4. Output Model — Report First, Beads on Confirm

Findings are presented ranked, not auto-created as beads. User picks which gaps to promote.

```
Integration gaps found: 3

P1: galiana has no consumer for disagreement_resolved
    Source: contract-ownership.md declares galiana as consumer
    Evidence: no ic events tail --consumer=galiana found
    Impact: trust calibration blind to disagreements

P2: interwatch missing companion-graph edge
    ...
```

Options: create beads for selected gaps, create all, or just save report to `docs/traces/`.

### 5. Gap Ranking — Evidence Strength

| Priority | Criteria |
|----------|----------|
| P1 (high confidence gap) | Contract declares consumer + zero code evidence; event emitted + zero cursor registrations; companion-graph edge + zero import/call evidence |
| P2 (medium confidence) | AGENTS.md mentions integration + weak code evidence; event type exists + consumer exists but allowlist missing |
| P3 (low confidence / docs) | Undeclared edge found in code (missing docs, not missing code); heuristic grep match only |

### 6. Architecture — Thin Plugin

```
interverse/intertrace/
  .claude-plugin/plugin.json
  skills/intertrace.md          # /intertrace slash command
  agents/review/fd-integration.md  # flux-drive agent (phase 2)
  hooks/                        # post-ship hook (phase 2+)
  lib/
    trace-events.sh             # event bus tracer
    trace-contracts.sh          # contract verifier
    trace-companion.sh          # companion-graph verifier
  tests/
```

Calls intermap MCP tools for structure data. Gap detection logic lives in the skill/agent layer.

### 7. MCP Server Strategy (Canon Decision)

Codified in `docs/canon/mcp-server-criteria.md` with pointer in root AGENTS.md:

- **New MCP server when:** persistent state, expensive init, real-time queries, external service bridge
- **Skills + shell libs when:** stateless analysis, calls existing servers, batch output, infrequent use

## Open Questions

- **intermap extension:** Should `cross_project_deps` be extended to detect shell-source edges and event-bus edges? Or should intertrace do its own discovery and only use intermap for the project list + code structure?
- **Companion graph maintenance:** Should intertrace auto-update companion-graph.json when it finds undeclared-but-wired edges? Or just report them?
- **fd-integration triage score:** What domain_boost values should fd-integration get in flux-drive's scoring model?
- **Post-ship hook:** Should /intertrace run automatically after `bd close` via a beads hook? Or stay manual-only?

## Validation

The iv-5muhg sprint is the ground truth test case. Intertrace should, when pointed at iv-5muhg's commits, rediscover at least 4 of the 5 gaps that were found manually:
1. interspect hook_id not in allowlist (event consumer gap)
2. `ic state set` stdin vs positional args (contract usage gap)
3. Scope ID mismatch between get/set (contract usage gap)
4. `_ = insertReplayInput(...)` discarded error (code correctness — may be out of scope)
5. galiana/interwatch not consuming disagreement events (consumer gap)

Gap #4 is a code correctness bug, not an integration gap — intertrace may reasonably not catch it. Gaps #1, #2, #3, #5 are all integration gaps that should be detectable.
