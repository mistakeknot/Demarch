# Interbus: Intermodule Integration Mesh for Clavain and Hub/Plugin Ecosystem

**Bead:** iv-psf2
**Phase:** brainstorm (as of 2026-02-16T00:00:00Z)
**Date:** 2026-02-16
**Status:** approach selected, ready for strategy/planning

## What We’re Building

## Bead Tracking

- **Parent:** `iv-psf2` — Interbus rollout tracking bead
- **Wave 1:** `iv-psf2.1` — Core workflow modules
  - `iv-psf2.1.1` — interphase adapter
  - `iv-psf2.1.2` — interflux adapter
  - `iv-psf2.1.3` — interdoc adapter
  - `iv-psf2.1.4` — interlock adapter
- **Wave 2:** `iv-psf2.2` — Visibility and safety modules
  - `iv-psf2.2.1` — intercheck adapter
  - `iv-psf2.2.2` — interline adapter
  - `iv-psf2.2.3` — interwatch adapter
  - `iv-psf2.2.4` — interpub adapter
  - `iv-psf2.2.5` — interslack adapter
  - `iv-psf2.2.6` — internext adapter
  - `iv-psf2.2.7` — intercraft adapter
  - `iv-psf2.2.8` — interform adapter
- **Wave 3:** `iv-psf2.3` — Supporting utility modules
  - `iv-psf2.3.1` — tool-time adapter
  - `iv-psf2.3.2` — tldr-swinton adapter
  - `iv-psf2.3.3` — intersearch adapter

_All waves are intentionally ordered with Wave 1 as the hard dependency baseline._

We will introduce **Interbus**, a lightweight integration mesh inside Interverse that standardizes how Clavain and adjacent modules communicate for workflow orchestration, artifacts, and phase transitions.

Interbus is not a heavyweight microservice rewrite. It is a thin, explicit contract layer with thin adapters so modules can emit and consume **integration intents** (such as `discover_work`, `start_sprint`, `phase_transition`, `review_pass`) without hard dependency on each other’s implementation details.

The first implementation focus is Clavain, then expand to modules that already participate in sprint-like flows:
- `interphase` (phase/bridge)
- `interflux` (review + flux-drive)
- `interpub` (release hooks)
- `interwatch` (doc freshness signal)
- `interdoc` (artifact linkage)
- `interlock` (file coordination metadata)

The immediate gain is that `/clavain` commands can keep existing ergonomics while reducing brittle cross-command and cross-plugin assumptions.

## Why This Is the Right Approach

Current integrations are high-performing where they work but fragmented:
- command aliases call into other plugin entry points implicitly,
- multiple modules maintain duplicated state transitions,
- discovery, phase tracking, and artifact registration are often parallel and drift-prone.

Interbus solves this by centralizing _intent semantics_ and moving orchestration to metadata instead of direct chaining.

Concrete benefits:
1. **Lower coupling:** plugin-to-plugin calls become intent envelopes.
2. **Better observability:** every intent emits structured lifecycle traces.
3. **Lower error blast radius:** consumers choose to ignore unknown intent versions safely.
4. **Higher reuse:** additional modules plug in by declaring adapters.
5. **Simpler codex tooling:** command wrappers can inspect intent streams for continuation points and resumability.

Why not keep everything direct forever? It already works, but each new integration adds hidden coupling. Interbus gives a bounded abstraction at the point where complexity is already high.

## Proposed Design

Interbus has two layers:
1. **Protocol layer:** a stable shell-compatible schema:
   - `interbus.publish <intent> [--artifact ...] [--context ...] [--payload ...]`
   - `interbus.subscribe <intent> [--module ...] [--watch ...]`
   - `interbus.emit` and `interbus.consume` helper subcommands for plugin scripts.
2. **Adapter layer:** small wrappers in each plugin to translate local events to/from Interbus.

Event envelope fields:
- `event_id` (ulid)
- `intent` (canonical name, versioned)
- `context_id` (sprint/bead/issue correlation)
- `artifact_path`
- `severity` (`info|warn|error`)
- `producer`, `consumers`, `source_hook`
- `payload` (JSON, opaque to producer)

Core Clavain changes:
- `sprint` command checks for pending intents before local inference.
- `strategy`/`write-plan`/`work` publish phase events and artifact references.
- `quality-gates` publishes gate results and emits a completion signal consumed by future commands.
- `sprint-status` can subscribe and display recent interbus activity.

Interbus first ships as a `bash` shim in `os/clavain/hooks` for zero-friction adoption, with a Go/Python backend moved out later only if volume warrants.

## Open Questions

1. Should Interbus include a persistence layer now, or be ephemeral + durable projection later?
2. What is the minimal intent schema v1? (My recommendation: 5-7 core intents only.)
3. Should interbus events be signed/hmac’ed for shared-hosted environments, or trust local path ACLs for now?
4. How strict should intent versioning be between patch/minor changes?

## Scope / YAGNI Boundaries

**In scope**
- `clavain` command adapter hooks for intents
- `interphase` compatibility adapter for phase transitions
- `interflux` gate result event adapter
- docs/docs + CLI help for intent catalog and lifecycle
- minimal subscriber mode for debugging (`interbus replay`)

**Out of scope (v1)**
- replacing all cross-plugin calls at once
- distributed transport redesign
- central event broker service
- strict access control framework

## Phase Tracking Note

Interbus is selected as the default approach for this workstream and should now proceed to `/clavain:write-plan`.
