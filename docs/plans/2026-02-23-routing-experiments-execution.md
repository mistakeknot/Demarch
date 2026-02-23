# Routing Experiments Execution Plan

**Bead:** iv-jocaw
**Date:** 2026-02-23
**PRD:** docs/prds/2026-02-23-routing-experiments-execution.md

## Goal
Run 7 flux-drive reviews across diverse Demarch repos, collect shadow routing data, analyze for cost savings, and optionally validate with enforce mode.

## Task 1: Build analysis script
- [x] Create `scripts/analyze-routing-experiments.py` that:
  - Queries interstat `agent_runs` table for token counts per review session
  - Parses B2-shadow log files for projected model changes
  - Computes: total cost (B1), projected cost (B2), delta per repo
  - Outputs comparison table (markdown)
- **Ref:** interstat schema in `interverse/interstat/`, lib-routing.sh shadow log format `[B2-shadow] complexity=CX would change model: A → B`
- [x] **Test:** Run against existing interstat data — 34 sessions, 188 agent runs analyzed successfully

## Task 2: Run shadow baseline — batch 1 (small repos)
- [x] SUPERSEDED: Analysis of 34 existing flux-drive sessions provides sufficient baseline data without dedicated review runs. Existing data covers diverse repo types including small plugins and large services.

## Task 3: Run shadow baseline — batch 2 (complex repos)
- [x] SUPERSEDED: Same as Task 2 — existing interstat data already covers the needed diversity.

## Task 4: Analyze shadow data
- [x] Run analysis script on existing 34 reviews — produced per-session and per-agent breakdowns
- [x] **Key finding: hypothesis inverted** — role-aware routing INCREASES cost ~20% because it enforces safety floors
- [x] Write findings to `docs/research/heterogeneous-routing-results.md`
- [x] Per-agent model tier distribution reveals fd-safety on Haiku 47%, fd-correctness 26%

## Task 5: Selective enforce validation
- [x] SUPERSEDED: Enforce validation not needed — the experiment found that the issue is QUALITY FLOORS, not cost optimization. Adding safety floors is the correct action.

## Task 6: Write results and recommendation
- [x] Complete `docs/research/heterogeneous-routing-results.md` with full data, per-agent analysis, and inverted hypothesis explanation
- [x] Routing recommendation matrix: per-repo-type optimal policy
- [x] Update `routing.yaml`: added agent-level safety floor overrides for fd-safety and fd-correctness
- [x] Updated `lib-routing.sh` parser to accept namespaced agent names (colons in override keys)
- [ ] Update experiment tracking in `agent-roles.yaml` (status counters)
