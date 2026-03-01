# Interserve Retirement & Unified Routing Engine

**Date:** 2026-03-01
**Status:** Brainstorm complete
**Trigger:** Interserve MCP server causing session friction (hook interference, startup failures) while its core vision — intelligent model routing — is a kernel concern, not a plugin concern.

## What We're Building

A unified routing engine in intercore that answers: **given this task, which model/agent should handle it?** using cost-aware capability matching with interspect evidence feedback.

This retires interserve as a plugin and promotes its core insight (route work to the cheapest capable agent) into kernel infrastructure where it belongs.

## Why This Approach

### The Philosophy Demands It

PHILOSOPHY.md makes four claims that converge on routing-as-kernel:

1. **"Route to the best model for the job — automated measurement determines which."** (Agent architecture) — Routing is a platform primitive, not a plugin feature.

2. **"Plugins are dumb and independent. The platform is smart and aware."** (Plugin ecosystem) — A plugin that makes routing decisions violates the architecture. Plugins declare capabilities; the platform composes them.

3. **"A quality floor is non-negotiable; above it, route to the cheapest model that clears the bar."** (Core Bet #4) — This IS the routing algorithm, stated as philosophical axiom.

4. **"Routing evolves from static tiers through complexity-aware to fully adaptive, where selection becomes empirical."** (Agent architecture) — The evolution path is platform-level, using interspect evidence.

### What Interserve Got Right and Wrong

**Right:** The classify → route → dispatch pattern. The insight that not every task needs Opus. The graceful fallback design (keyword matching when LLM unavailable).

**Wrong:** Being a plugin. Routing is platform intelligence. A plugin doing platform work creates friction because it's fighting the architecture — hooks intercepting tool calls, MCP servers that need to be running, Codex dependencies that may not be available. The same logic compiled into intercore is just a function call.

### Existing Infrastructure That Converges

| Component | Location | Current role | Future role |
|-----------|----------|-------------|------------|
| lib-routing.sh | os/clavain/scripts/ | Safety floors, model resolution | Shell interface to `ic route` |
| agent-roles.yaml | os/clavain/config/ | Agent → minimum model mapping | Capability floor definitions |
| dispatch.sh | os/clavain/scripts/ | Codex tier dispatch (fast/deep) | Dispatch target selected by router |
| interspect evidence | interverse/interspect/ | Agent success/failure tracking | Evidence feed for routing decisions |
| model-routing skill | os/clavain/skills/ | Economy/performance toggle | User-facing routing policy control |
| interflux triage | interverse/interflux/ | Agent selection scoring | Consumer of routing decisions |
| interserve classify | interverse/interserve/ | Section → agent classification | Seeds intercore classify.go |

## Key Decisions

### 1. Routing lives in intercore (L1 kernel)

**Decision:** `core/intercore/internal/routing/` is the home.

**Rationale:** Routing is mechanism, not policy. The kernel provides the routing engine; Clavain (L2) provides policy overlays (safety floors, economy/performance toggle). This follows the mechanism/policy separation principle.

**CLI:** `ic route <task-type> [--context=...] [--budget=...]` returns the recommended model + dispatch method.

### 2. Two-pass routing algorithm

**Decision:** Filter by capability, then rank by cost.

1. **Capability filter:** Which models CAN handle this task type? Uses agent-roles.yaml floors + task requirements (needs tools? needs sandbox? needs multi-turn?).
2. **Cost rank:** Of capable models, which is cheapest? Uses static cost table + interspect evidence (if model X fails 40% of the time on task type Y, its effective cost is higher).

This directly implements Core Bet #4: "quality floor is non-negotiable; above it, route to the cheapest model that clears the bar."

### 3. Interserve plugin retired

**Decision:** Retire interserve. Redistribute its capabilities:

| Capability | Destination | Rationale |
|-----------|-------------|-----------|
| `extract_sections` | interflux internal | Only consumer; pure Go, no dependencies |
| `classify_sections` (keyword) | intercore routing | Becomes one task-classification strategy |
| `classify_sections` (LLM) | Deferred | Re-enable when routing engine supports LLM-assisted classification |
| `codex_query` | Dropped | dispatch.sh already handles Codex delegation; codex_query was a thin wrapper |
| `pre-read-intercept.sh` | Dropped | Primary friction source; routing decisions should be made at dispatch time, not by intercepting tool calls |

### 4. Evidence-driven routing evolution

**Decision:** Start with static routing tables, evolve to evidence-driven.

- **Phase 1 (static):** Cost table + capability floors. Same as today but unified.
- **Phase 2 (evidence-aware):** Interspect success rates adjust effective cost. Model X failing 40% on task Y makes it 2.5x more expensive in practice.
- **Phase 3 (adaptive):** Router proposes policy changes based on evidence trends. Human approves via trust ladder (Level 4: agent proposes policy changes).

This matches the OODAR lens: observe (interspect evidence) → orient (pattern classification) → decide (routing proposal) → act (apply override) → reflect (canary monitoring).

### 5. lib-routing.sh becomes a thin shell wrapper

**Decision:** lib-routing.sh calls `ic route` under the hood but retains its shell API for backward compatibility.

Existing consumers (hooks, skills, dispatch.sh) continue calling shell functions. The functions shell out to the compiled Go router. This is the strangler-fig pattern from PHILOSOPHY.md: "Wrap old in new."

## Open Questions

1. **Task type taxonomy:** What are the routing-relevant task types? Candidates: file-read, code-generation, review-judgment, simple-extraction, search, classification, multi-turn-dialogue. How granular?

2. **Cost table format:** Static YAML? Fetched from API? How often does it need updating as model pricing changes?

3. **Interspect integration depth:** Does the router query interspect directly (Go library call) or through the event pipeline? Direct is faster; pipeline is more decoupled.

4. **Migration path for lib-routing.sh consumers:** How many callers need updating? Can `ic route` return shell-friendly output (e.g., `MODEL=sonnet TIER=fast`) that lib-routing.sh can `eval`?

5. **Interserve deprecation timeline:** Disable immediately (it's causing friction now) or keep running until intercore routing is built?

## What Dies

- `interverse/interserve/` plugin (entire repo)
- `pre-read-intercept.sh` hook
- `codex_query` MCP tool
- `clodex-toggle` command (routing decisions move to the engine)
- `INTERSERVE_CLASSIFY_LLM` env var

## What's Born

- `core/intercore/internal/routing/` — unified routing engine
- `ic route` CLI command
- Cost-aware capability matching as a first-class kernel primitive
- Evidence feedback loop: interspect → routing → dispatch → interspect
