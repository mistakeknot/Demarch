---
title: "C3 Composer — Dispatch Plan Generator"
category: patterns
date: 2026-03-03
bead: iv-240m
tags: [clavain, go, composer, dispatch, fleet-registry, safety-floors]
relevance: high
---

# C3 Composer — Dispatch Plan Generator

## What Was Built

Go subcommand `clavain-cli compose --stage=<stage>` that joins agency spec role requirements against fleet registry agent capabilities, applies Interspect calibration for model tiers, enforces safety floors, checks budget, and emits deterministic JSON dispatch plans on stdout. First external Go dependency added to clavain-cli (gopkg.in/yaml.v3).

Cross-repo wiring: flux-drive launch phase consumes the plan (Step 2.0.4), sprint pipeline exports `CLAVAIN_COMPOSE_PLAN` env var.

## Key Learnings

### 1. Safety Floor Invariant vs. Routing Overrides

**Problem:** Routing overrides can `exclude` agents, removing them from the active fleet before `matchRole` runs. If a safety-floor agent (fd-safety, fd-correctness) is excluded, the safety invariant is silently violated — no agent, no floor check.

**Fix:** Emit `WARNING:safety_floor_excluded:<agent>:<reason>` at exclusion time. The invariant can't be enforced if the agent doesn't exist in the plan, but the warning makes the violation visible.

**Pattern:** When two policies can conflict (safety floors vs. exclusion overrides), the weaker one should emit a high-severity warning. Never silently let one policy defeat another.

### 2. nil Map Panic in Go Struct Merge

**Problem:** `mergeSpec(base, override)` writes to `base.Stages[stageName]`, but if `base.Stages` was never initialized (YAML file has no `stages:` key), the map is nil and assignment panics.

**Fix:** Guard with `if base.Stages == nil { base.Stages = make(map[string]StageSpec) }` before the range loop.

**Pattern:** Any Go function that writes to a map field of a struct parameter must check for nil first. YAML/JSON unmarshaling into structs leaves maps as nil when the key is absent.

### 3. Silent Error Swallowing in Optional Loaders

**Problem:** `loadInterspectCalibration()` and `loadRoutingOverrides()` returned nil for both "file missing" (expected) and "file corrupt" (bug). Corrupt config files were invisible.

**Fix:** Distinguish file-not-found (return nil silently) from unmarshal errors (log to stderr, then return nil). Optional loaders should degrade gracefully but not hide parse failures.

### 4. Monorepo Git Subproject Commits

**Gotcha:** Root `.gitignore` has `os/`, so `git add` from monorepo root is blocked. Even `git add -f` doesn't persist through commit. Must `cd` into the subproject and commit from there. Each subproject (os/clavain, interverse/interflux) has its own git repo.

### 5. Bats jq Assertion Pattern

**Gotcha:** `jq -e '.array[] | select(pred) | empty'` returns exit 4 (not 1) when no elements match, because jq's `-e` treats no output as falsy. Use count-based assertions instead: `jq '[.array[] | select(pred)] | length'` then `[ "$count" -eq 0 ]`.

## Architecture Decision: Shell Bridge Pattern

The Go binary is the source of truth for dispatch plans. Shell consumers access it through `lib-compose.sh`, which provides:
- `compose_dispatch(sprint_id, stage)` — returns JSON on stdout
- `compose_available()` — health check
- `_compose_find_cli()` — binary resolution across 4 locations

This pattern (Go binary + thin shell bridge) is the template for the broader Go consolidation effort (iv-d4wk0).

## Test Strategy

- 16 Go unit tests (table-driven, fixture files in testdata/)
- 7 bats integration tests against real config files
- Smoke test with production fleet-registry.yaml (6 agents, safety floors enforced)

## Files

- `os/clavain/cmd/clavain-cli/compose.go` — implementation (610 lines)
- `os/clavain/cmd/clavain-cli/compose_test.go` — unit tests
- `os/clavain/tests/shell/test_compose.bats` — integration tests
- `os/clavain/scripts/lib-compose.sh` — shell bridge
- `interverse/interflux/skills/flux-drive/phases/launch.md` — consumer wiring
- `os/clavain/hooks/lib-sprint.sh` — sprint pipeline wiring
