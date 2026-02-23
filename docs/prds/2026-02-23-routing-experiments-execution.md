# PRD: Heterogeneous Routing Experiment Execution

**Bead:** iv-jocaw
**Date:** 2026-02-23
**Parent:** iv-jc4j

## Problem

B2 complexity routing infrastructure is built and running in shadow mode, but we have zero empirical data on whether heterogeneous routing actually saves tokens without degrading review quality. Without this data, routing policy decisions are theoretical.

## Goal

Run controlled experiments across 7 Demarch repos to validate or reject heterogeneous routing. Produce a routing recommendation matrix backed by real data.

## Core Capabilities

### F0: Shadow Baseline Collection
- Run flux-drive reviews on 7 diverse repos with `mode: shadow`
- Capture shadow routing logs, interstat metrics, findings, convergence data
- Build an analysis dataset: per-agent tokens, complexity tier, projected model, actual model

### F1: Analysis Script
- Query interstat SQLite for cross-review token comparison
- Parse B2-shadow logs to compute projected savings per repo/agent
- Generate comparison tables: B1 cost vs projected B2 cost per repo
- Identify repos with highest divergence (candidates for enforce testing)

### F2: Selective Enforce Validation
- Switch 3 high-divergence repos to `mode: enforce`
- Re-run flux-drive and capture identical metrics
- Compare: actual savings vs shadow projections, quality preservation

### F3: Results Document + Recommendation Matrix
- Write `docs/research/heterogeneous-routing-results.md` with full data
- Pareto frontier: cost vs quality for each policy tested
- Routing recommendation matrix: per-repo-type optimal policy
- Update `routing.yaml` if evidence supports a policy change

## Non-Goals
- Collaboration mode experiments (Exp 3 from parent) — defer to follow-up
- Production rollout of enforce mode — this sprint produces evidence only
- Changes to flux-drive dispatch logic — only routing.yaml config changes
- Building a dashboard — analysis is script-based, one-time

## Quality Metric

"Quality" of a review is measured by:
1. **Finding count** — total findings per review
2. **Unique finding rate** — findings only one agent reported (measures agent contribution)
3. **Convergence score** — findings multiple agents reported independently (measures confidence)
4. **P0/P1 finding preservation** — critical findings must not be lost under B2

A policy passes if: finding count within 10% of baseline AND zero P0/P1 findings lost.

## Dependencies
- B2 shadow mode (shipped)
- agent-roles.yaml (shipped)
- interstat metrics.db (live)
- flux-drive pipeline (working)

## Risks
- Shadow shows no divergence → validates B1 as optimal (still useful)
- Budget exhaustion before all 7 repos → prioritize 4 most diverse
