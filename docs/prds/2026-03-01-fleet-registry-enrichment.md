# PRD: Fleet Registry Enrichment + Flux-Drive Integration

**Bead:** iv-lx00

## Problem

The fleet registry (`config/fleet-registry.yaml`) catalogs 25 agents with capabilities and static cost estimates, but its `cold_start_tokens` are hand-curated guesses. Meanwhile, interstat has actual per-agent×model token data from 34+ production runs — but this data never flows back into the registry. Flux-drive's cost estimation (Step 1.2c) falls back to `budget.yaml` defaults when interstat has < 3 runs, ignoring the registry entirely.

## Solution

Enrich the fleet registry with actual interstat cost data (hybrid offline+runtime), then wire it into flux-drive's cost estimation as a middle fallback tier between live interstat and hardcoded budget.yaml defaults.

## Features

### F1: Interstat Cost Enrichment in scan-fleet.sh

**What:** Add a `--enrich-costs` flag to `scan-fleet.sh` that queries the interstat SQLite database and writes per-agent×model cost statistics into `fleet-registry.yaml`.

**Acceptance criteria:**
- [ ] `scan-fleet.sh --enrich-costs` queries interstat's `agent_runs` table and computes mean, p50, p90 tokens and finding count per (subagent_type, model) pair
- [ ] Results are written into each agent's `models.actual_tokens` and `models.finding_density` fields in fleet-registry.yaml
- [ ] Agents with < 3 runs for a model get `preliminary: true` flag on that model's data
- [ ] A `last_enrichment` ISO timestamp is written at the top level of fleet-registry.yaml
- [ ] `--dry-run` mode shows what would change without modifying the file
- [ ] Handles missing interstat DB gracefully (warns and exits 0)

### F2: Runtime Cost Delta in lib-fleet.sh

**What:** Add a `fleet_cost_estimate_live` function to `lib-fleet.sh` that checks interstat for runs newer than the registry's `last_enrichment` timestamp, returning fresh cost data when available.

**Acceptance criteria:**
- [ ] `fleet_cost_estimate_live <agent_id> [model]` returns actual token estimate incorporating post-enrichment interstat runs
- [ ] Falls back to `fleet_cost_estimate` (static YAML) when interstat is unavailable or has no newer data
- [ ] Uses the existing interstat SQLite path resolution (interstat plugin cache discovery)
- [ ] No yq dependency for the runtime path — reads `last_enrichment` via grep/sed from YAML header
- [ ] Returns empty/error gracefully when both interstat and registry lack data for an agent

### F3: Wire Fleet Registry into Flux-Drive Cost Estimation

**What:** Update flux-drive's Step 1.2c (budget-aware agent selection) to use the fleet registry as a fallback tier between live interstat and budget.yaml defaults.

**Acceptance criteria:**
- [ ] Cost estimation resolution order: interstat live (>= 3 runs) → `fleet_cost_estimate_live` (registry + delta) → `budget.yaml` defaults
- [ ] `estimate-costs.sh` sources `lib-fleet.sh` and uses `fleet_cost_estimate_live` for agents with < 3 interstat runs
- [ ] Cost source is reported in triage table: `source: interstat (N runs)` or `source: fleet-registry` or `source: default`
- [ ] Existing behavior unchanged when fleet registry is absent (graceful degradation)

## Non-goals

- C3 Composer (constraint solver matching agency specs to fleet) — separate bead
- Automatic scan-fleet.sh scheduling (post-session hook) — on-demand for now
- Changing model routing based on registry data — routing.yaml stays the model source
- Adding new agents to the registry — scan-fleet.sh already handles discovery

## Dependencies

- `fleet-registry.yaml` (exists, 506 lines, 25 agents)
- `lib-fleet.sh` (exists, query API with yq)
- `scan-fleet.sh` (exists, agent discovery + YAML merge)
- Interstat SQLite database (`agent_runs` table with subagent_type, model, total_tokens)
- `interverse/interflux/scripts/estimate-costs.sh` (flux-drive cost estimation)
- `interverse/interflux/config/flux-drive/budget.yaml` (fallback defaults)

## Open Questions

- Should `scan-fleet.sh --enrich-costs` be a separate script or a flag on the existing script? Lean toward flag (keeps one tool).
- Exact SQLite query for p50/p90 — SQLite doesn't have PERCENTILE_CONT. Use ORDER BY + LIMIT + OFFSET approximation, or a Python helper.
