# PRD: Static Routing Table — Phase-to-Model Mapping

**Bead:** iv-1kd4 (sprint), iv-dd9q (original)
**Flux-drive reviews:** [architecture](../research/review-prd-architecture.md), [quality](../research/review-prd-quality-style.md), [user-product](../research/review-prd-user-experience.md), [correctness](../research/review-prd-correctness.md)

## Problem

Clavain has two independent model routing systems (dispatch tiers for Codex CLI, agent frontmatter for Claude subagents) that don't share configuration. Phase-to-model mappings are hardcoded in scripts and commands, making it impossible to change routing policy without editing code. There's no single place to declare "brainstorm uses Opus, execute uses Sonnet."

## Solution

Create a declarative `config/routing.yaml` config file with two namespaced sections — `subagents:` (Claude model aliases) and `dispatch:` (Codex tier mappings) — unified by phase. Build a shell reader library (`scripts/lib-routing.sh`) that both dispatch.sh and the /model-routing command consult. Zero runtime overhead when the file doesn't exist (falls back to existing behavior).

## Design Decisions (from flux-drive review)

1. **Two-section schema** — `subagents:` uses Claude aliases (`haiku`/`sonnet`/`opus`/`inherit`), `dispatch:` uses Codex tier names (`fast`/`deep`/model IDs). No namespace bridging needed — each consumer reads its own section.
2. **Nested-inheritance schema** (from brainstorm) — `defaults → phases → overrides`. Each phase can override category defaults. Resolution is self-documenting: read top-to-bottom.
3. **Profiles deferred to B1b** — Ship `defaults:` + `phases:` + `overrides:` only. Named profiles add parser complexity and require unresolved state management. Defer until real usage patterns emerge.
4. **routing.yaml is read-only source of truth** — `/model-routing` stops sed-editing agent frontmatter. Instead, agents consult routing.yaml at dispatch time via `routing_resolve_model`. Frontmatter `model:` lines become fallback-only (used when routing.yaml is absent).
5. **Library lives in `scripts/`** — `lib-routing.sh` goes alongside `dispatch.sh`, not in `hooks/` (it's not a hook).
6. **`dispatch:` section replaces `tiers.yaml`** — Single file for all routing. `dispatch.sh` reads `routing.yaml` instead of `tiers.yaml`. Migration: tiers.yaml content moves into `dispatch:` section.

## Schema

```yaml
# config/routing.yaml
#
# Static model routing policy for Clavain (Track B1).
# Two namespaces: subagents (Claude Code) and dispatch (Codex CLI).
# Resolution: overrides > phases[current].categories > phases[current].model > defaults.categories > defaults.model

subagents:
  defaults:
    model: sonnet
    categories:
      research: haiku
      review: sonnet
      workflow: sonnet
      synthesis: haiku

  phases:
    brainstorm:
      model: opus
      categories:
        research: haiku      # research stays cheap even in brainstorm
    strategy:
      model: opus
    plan:
      model: sonnet
    execute:
      model: sonnet
    quality-gates:
      categories:
        review: opus          # reviews get opus for quality-gates
    ship:
      model: sonnet

  overrides: {}
    # fd-safety: opus        # example: pin specific agent regardless of phase

dispatch:
  tiers:
    fast:
      model: gpt-5.3-codex-spark
      description: Scoped read-only tasks, exploration, verification
    fast-clavain:
      model: gpt-5.3-codex-spark-xhigh
      description: Clavain interserve-mode read-only tasks
    deep:
      model: gpt-5.3-codex
      description: Generative tasks, implementation, complex reasoning
    deep-clavain:
      model: gpt-5.3-codex-xhigh
      description: Clavain interserve-mode high-complexity tasks
  fallback:
    fast: deep
    fast-clavain: deep-clavain
    deep-clavain: deep
```

## Features

### F1: Routing Config Schema
**What:** Define `config/routing.yaml` with the two-section nested-inheritance schema above.
**Acceptance criteria:**
- [ ] `config/routing.yaml` exists with the schema shown above
- [ ] `subagents:` section has `defaults:` (model + categories), `phases:` (per-phase model + category overrides), `overrides:` (per-agent pinning)
- [ ] `dispatch:` section has `tiers:` and `fallback:` (migrated from tiers.yaml)
- [ ] Schema is self-documenting with inline comments explaining resolution order
- [ ] Maximum nesting depth is 3 levels (parseable by existing line-by-line technique)

### F2: Config Reader Library
**What:** Shell library (`scripts/lib-routing.sh`) that parses `routing.yaml` and resolves phase + category to a model tier.
**Acceptance criteria:**
- [ ] `routing_resolve_model --phase <phase> [--category <category>] [--agent <agent-name>]` returns the correct model tier
- [ ] Resolution order: per-agent override > phase-specific category > phase-level model > default category > default model
- [ ] Returns empty string (not error) when routing.yaml doesn't exist — callers use their existing defaults
- [ ] Uses line-by-line YAML parsing consistent with dispatch.sh pattern (no external YAML library)
- [ ] Parses routing.yaml once per shell process; uses global associative array cache so N calls within one hook/script do not cause N file reads
- [ ] `routing_list_mappings` prints the full routing table for status display
- [ ] `routing_resolve_dispatch_tier <tier-name>` resolves dispatch tier from `dispatch:` section (replaces `resolve_tier_model` in dispatch.sh)
- [ ] Priority when both `--phase` and explicit `--tier` are provided: `--tier` wins (explicit > config)

### F3: Dispatch Integration
**What:** Wire `dispatch.sh` to read `dispatch:` section from `routing.yaml` (replacing `tiers.yaml`) and accept optional `--phase` context.
**Acceptance criteria:**
- [ ] `dispatch.sh` reads `dispatch.tiers` from `routing.yaml` instead of `tiers.yaml`
- [ ] `dispatch.sh` accepts optional `--phase <name>` flag for future phase-aware dispatch (B2 hook point)
- [ ] When `--phase` is NOT provided, behavior is identical to current (tier resolution only)
- [ ] `--tier` and `--model` flags still override routing.yaml (explicit > config > default)
- [ ] Interserve skill passes phase context when available (from sprint state)
- [ ] `tiers.yaml` is removed after migration (replaced by `dispatch:` section in routing.yaml)
- [ ] Fallback: if routing.yaml doesn't exist, falls back to hardcoded default tier (current behavior)

### F4: Subagent Integration
**What:** Wire `/model-routing` command to read routing.yaml instead of sed-editing agent frontmatter.
**Acceptance criteria:**
- [ ] `/model-routing status` shows the resolved routing table from routing.yaml for all phases + categories
- [ ] `/model-routing economy` writes economy defaults to `subagents.defaults` in routing.yaml (research=haiku, review=sonnet, workflow=sonnet)
- [ ] `/model-routing quality` writes quality defaults to `subagents.defaults` in routing.yaml (all=inherit)
- [ ] Agent frontmatter `model:` lines are preserved as fallback (used when routing.yaml is absent)
- [ ] Backward compatible: if routing.yaml doesn't exist, economy/quality behave identically to current implementation (sed-edit frontmatter)

## Non-goals

- **Complexity-aware routing (B2)** — This is static config only. No runtime complexity detection or dynamic model switching.
- **Adaptive routing (B3)** — No Interspect feedback loop or outcome-driven selection.
- **Named profiles (B1b)** — Deferred. The `economy`/`quality` modes write directly to `subagents.defaults` rather than switching between named profile objects.
- **Interflux agent frontmatter management** — This PRD covers Clavain's routing.yaml. Companion plugins can read it in a follow-up.
- **Token budget enforcement** — Routing.yaml declares models, not budgets. Budget tracking remains in lib-sprint.sh.

## Dependencies

- Existing `config/dispatch/tiers.yaml` — migrated into routing.yaml, then removed
- Existing `commands/model-routing.md` — modified to read/write routing.yaml
- Existing `scripts/dispatch.sh` — modified to source lib-routing.sh and read routing.yaml
- Existing agent frontmatter files in `agents/{review,workflow}/*.md` — kept as fallback

## Resolved Questions (from flux-drive review)

- **Location:** `config/routing.yaml` (decided, alongside dispatch config)
- **Namespace bridging:** Not needed — separate `subagents:` and `dispatch:` sections
- **Profiles:** Deferred to B1b
- **Source of truth:** routing.yaml (agents read from it at dispatch time, frontmatter is fallback)
- **Library location:** `scripts/lib-routing.sh` (not hooks/)
- **tiers.yaml migration:** routing.yaml replaces tiers.yaml
