# Fleet Registry Enrichment + Flux-Drive Integration

**Bead:** iv-lx00
**Date:** 2026-03-01
**Status:** Brainstorm complete

## What We're Building

Two things that close the gap between C2 (fleet registry) and its consumers:

1. **Interstat cost enrichment** — Wire actual per-agent×model token costs from interstat SQLite into `fleet-registry.yaml`. Uses a hybrid flow: offline baseline via `scan-fleet.sh` + runtime delta lookup via `lib-fleet.sh` when interstat is available.

2. **Flux-drive consumption** — Wire `fleet-registry.yaml` into flux-drive's dispatch path so agent selection and budgeting use registry data (capabilities, actual costs, cold-start tokens) instead of hardcoded defaults.

C3 Composer (constraint solver that matches agency specs to fleet registry within budget) is out of scope — separate bead.

## Why This Approach

The fleet registry already exists (506 lines, 25 agents, full metadata). But it's disconnected:
- `cold_start_tokens` are hand-curated estimates, not actual costs
- Flux-drive doesn't read the registry — it uses hardcoded agent rosters and budget.yaml defaults
- The interstat SQLite database has actual per-agent×model cost data from 34+ runs, but no mechanism to feed it back into the registry

The hybrid data flow (offline baseline + runtime delta) was chosen because:
- **Offline merge** via `scan-fleet.sh` gives auditable, versioned cost data in YAML — humans can inspect and override
- **Runtime delta** via `lib-fleet.sh` catches recent cost changes (e.g., a new agent's first 3 runs) without waiting for the next scan
- **Graceful degradation** — if interstat is unavailable at runtime, the offline baseline (YAML) is always there

## Key Decisions

1. **Hybrid data flow** over pure-offline or pure-runtime. scan-fleet.sh writes `actual_tokens` (mean, p50, p90) and `finding_density` per agent×model into fleet-registry.yaml. lib-fleet.sh checks interstat for runs newer than the registry's `last_scan` timestamp and overlays fresher data.

2. **Scope: enrichment + wiring only, not C3.** The Composer (constraint solver) is a separate design problem. This sprint makes the registry useful — C3 makes it autonomous.

3. **Flux-drive reads registry for cost estimation.** Step 1.2c (budget-aware agent selection) currently uses `budget.yaml` defaults when interstat has < 3 runs. With this change, it falls back to `fleet-registry.yaml` actual_tokens first, then budget.yaml defaults. Resolution: interstat live > registry actual_tokens > budget.yaml defaults.

4. **Per-agent×model cost fields.** New fields in fleet-registry.yaml under each agent's `models` section:
   ```yaml
   models:
     preferred: sonnet
     supported: [haiku, sonnet, opus]
     actual_tokens:
       sonnet: {mean: 38500, p50: 35000, p90: 52000, runs: 12}
       haiku: {mean: 28000, p50: 26000, p90: 38000, runs: 5}
     finding_density:
       sonnet: 3.2   # findings per run
       haiku: 1.8
   ```

5. **scan-fleet.sh writes a `last_scan` timestamp** at the top of fleet-registry.yaml. lib-fleet.sh uses this to determine if runtime delta is needed (check interstat for runs after last_scan).

## Open Questions

- Should scan-fleet.sh run automatically (e.g., post-session hook) or only on-demand? Lean toward on-demand for now.
- How to handle agents with < 3 interstat runs — show the data as `preliminary: true`? Or only write when we have statistical confidence?
- Does flux-drive's Step 2.0.5 (model routing) need to read the registry too, or is routing.yaml sufficient? Lean toward keeping routing.yaml as the model source and registry as the cost/capability source (separation of concerns).
