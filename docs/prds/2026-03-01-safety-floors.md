# PRD: Safety Floors for Safety-Critical Agents

**Bead:** iv-db5pc

## Problem

Flux-drive's model routing can demote safety-critical agents (fd-safety, fd-correctness) to Haiku via category defaults or future complexity routing, undermining review quality. Experiment data shows fd-safety ran on Haiku 47% of the time before manual routing.yaml overrides were added — but those overrides are brittle and disconnected from the role definitions that declare safety policy.

## Solution

Wire `min_model` from `agent-roles.yaml` into `lib-routing.sh` as a hard post-resolution clamp. After the normal model resolution chain (overrides → phases → categories → defaults), check the agent's role `min_model` and upgrade if the resolved model is weaker. This makes agent-roles.yaml the single source of truth for safety policy while keeping routing.yaml overrides as defense-in-depth.

## Features

### F1: min_model Enforcement in lib-routing.sh

**What:** Add model tier comparison and clamping logic to the dispatch path in `lib-routing.sh`.

**Acceptance criteria:**
- [ ] `lib-routing.sh` reads `min_model` from `agent-roles.yaml` for the dispatched agent's role
- [ ] Model tier ordering defined: haiku=1, sonnet=2, opus=3
- [ ] If resolved model tier < min_model tier, resolved model is upgraded to min_model
- [ ] Clamping is a post-resolution step (after all routing.yaml resolution, after complexity routing)
- [ ] Existing routing.yaml overrides continue to work unchanged (defense-in-depth)
- [ ] Tests verify: agent in reviewer role resolves to haiku → gets clamped to sonnet
- [ ] Tests verify: agent in checker role resolves to haiku → no clamping (no min_model)

### F2: Expand agent-roles.yaml Coverage

**What:** Add `min_model: sonnet` to the `planner` role so fd-architecture and fd-systems are also protected.

**Acceptance criteria:**
- [ ] `planner` role in agent-roles.yaml has `min_model: sonnet`
- [ ] Comment updated to reflect enforcement status (no longer "informational only")
- [ ] No min_model set for `editor` or `checker` roles (explicitly left out this iteration)

### F3: Clamping Observability

**What:** Log clamping events to stderr with a structured format for passive interspect collection.

**Acceptance criteria:**
- [ ] When clamping occurs, emit structured log: `[safety-floor] agent=<name> resolved=<model> clamped_to=<min_model> role=<role>`
- [ ] Log goes to stderr (not stdout) so it doesn't interfere with dispatch output
- [ ] No direct interspect evidence emission (passive collection via existing hooks)

## Non-goals

- Editor role floor (fd-performance, fd-user-product, fd-game-design) — revisit with experiment data
- Direct interspect evidence emission for clamping events — passive collection is sufficient for now
- Changing the routing.yaml override mechanism — kept as defense-in-depth
- Modifying complexity routing (B2) behavior — min_model clamp is independent

## Dependencies

- `interverse/interflux/config/flux-drive/agent-roles.yaml` — exists, needs minor edits
- `os/clavain/config/routing.yaml` — exists, no changes needed
- `lib-routing.sh` — the dispatch code that needs the enforcement logic (need to locate exact file)

## Open Questions

- None blocking this iteration. Editor role floor deferred to future experiment data.
