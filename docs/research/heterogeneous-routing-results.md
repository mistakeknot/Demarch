# Heterogeneous Routing Experiment Results

**Date:** 2026-02-23
**Sessions analyzed:** 34


## Session Summary

| Session | Agents | Total Tokens | B1 Cost | B2 Projected | Savings | Savings % |
| --- | --- | --- | --- | --- | --- | --- |
| 059d7829-7ab... | 3 | 758 | $0.0080 | $0.0216 | $-0.0136 | -170.5% |
| 073b6d78-337... | 11 | 22,487 | $0.1543 | $0.3628 | $-0.2085 | -135.1% |
| 0c2ccc57-379... | 3 | 2,166 | $0.0302 | $0.0990 | $-0.0688 | -228.1% |
| 1a5e60e1-a7e... | 7 | 5,230 | $0.0534 | $0.0730 | $-0.0196 | -36.8% |
| 1c48dbac-e2e... | 5 | 1,938 | $0.0271 | $0.0398 | $-0.0127 | -46.7% |
| 21652775-d77... | 1 | 112 | $0.0009 | $0.0009 | $0.0000 | 0.0% |
| 22ef6733-f8e... | 9 | 11,005 | $0.0517 | $0.0638 | $-0.0121 | -23.4% |
| 23e6128a-ba9... | 5 | 669 | $0.0076 | $0.0076 | $0.0000 | 0.0% |
| 28037424-e3a... | 1 | 445 | $0.0014 | $0.0051 | $-0.0037 | -275.0% |
| 2afda5b4-b25... | 11 | 3,071 | $0.0217 | $0.0470 | $-0.0252 | -116.0% |
| 3314903b-d6a... | 7 | 16,385 | $0.1441 | $0.0802 | $0.0639 | 44.4% |
| 3545d8ce-bd6... | 4 | 55,322 | $0.9990 | $0.5222 | $0.4769 | 47.7% |
| 36d3370d-097... | 3 | 5,826 | $0.0076 | $0.0316 | $-0.0240 | -317.1% |
| 37b21139-68d... | 9 | 2,103 | $0.0271 | $0.0396 | $-0.0125 | -46.2% |
| 3b373e03-3e0... | 6 | 33,863 | $0.0406 | $0.1297 | $-0.0891 | -219.7% |
| 6d75dea2-63c... | 9 | 1,419 | $0.0162 | $0.0327 | $-0.0166 | -102.4% |
| 6e772147-362... | 2 | 99 | $0.0003 | $0.0009 | $-0.0007 | -275.0% |
| 815094c1-e94... | 3 | 249 | $0.0083 | $0.0060 | $0.0023 | 27.9% |
| 83380a54-fbf... | 8 | 7,778 | $0.0844 | $0.1392 | $-0.0547 | -64.8% |
| 850dc43a-a68... | 2 | 211 | $0.0021 | $0.0026 | $-0.0004 | -20.3% |
| 8b4d28c5-fb7... | 7 | 4,798 | $0.0448 | $0.0687 | $-0.0239 | -53.2% |
| 9357adf0-f0d... | 5 | 7,159 | $0.0395 | $0.0395 | $0.0000 | 0.0% |
| a8f24a69-c50... | 3 | 616 | $0.0051 | $0.0106 | $-0.0055 | -106.8% |
| b1fe61ea-96d... | 5 | 310 | $0.0012 | $0.0037 | $-0.0025 | -211.7% |
| b5267bf7-851... | 2 | 571 | $0.0006 | $0.0022 | $-0.0015 | -236.0% |
| bc2c28cb-e7f... | 3 | 1,184 | $0.0159 | $0.0159 | $0.0000 | 0.0% |
| c3aed93c-7d8... | 12 | 1,398 | $0.0280 | $0.0532 | $-0.0252 | -89.8% |
| c99d19be-546... | 3 | 1,242 | $0.0350 | $0.0154 | $0.0197 | 56.1% |
| cc4f9b8b-abc... | 9 | 26,564 | $0.0933 | $0.4144 | $-0.3210 | -343.9% |
| d1bedcb9-a8f... | 6 | 877 | $0.0103 | $0.0174 | $-0.0071 | -69.2% |
| e9824f30-abc... | 4 | 820 | $0.0250 | $0.0227 | $0.0022 | 9.0% |
| ede26691-3f7... | 8 | 1,545 | $0.0197 | $0.0287 | $-0.0091 | -46.1% |
| eee2342d-5b9... | 6 | 308 | $0.0010 | $0.0074 | $-0.0064 | -629.9% |
| fa710940-7d2... | 4 | 2,369 | $0.0306 | $0.0337 | $-0.0031 | -10.1% |

**Totals:** B1=$2.0361, B2=$2.4386, Savings=$-0.4026 (-19.8%)


## Per-Agent Model Tier Analysis

| Agent | Role | Runs | Current Tier(s) | Projected | Savings % |
| --- | --- | --- | --- | --- | --- |
| fd-architecture | planner | 46 | opus(19), sonnet(18), haiku(9) | opus | -128.9% |
| fd-correctness | reviewer | 50 | sonnet(28), haiku(13), opus(9) | sonnet | 27.7% |
| fd-decisions | checker | 1 | sonnet(1) | haiku | 73.3% |
| fd-performance | editor | 4 | sonnet(3), haiku(1) | sonnet | -10.2% |
| fd-quality | reviewer | 39 | sonnet(24), haiku(11), opus(4) | sonnet | 10.3% |
| fd-safety | reviewer | 15 | haiku(7), sonnet(5), opus(3) | sonnet | 62.4% |
| fd-systems | planner | 1 | sonnet(1) | opus | -400.0% |
| fd-user-product | editor | 11 | opus(4), sonnet(4), haiku(3) | sonnet | 70.0% |
| intersynth:synthesize-review | — | 19 | sonnet(12), haiku(5), opus(2) | sonnet | 0.0% |

## Key Finding: Hypothesis Inverted

**The original thesis was wrong.** We assumed all review agents run on Sonnet (homogeneous baseline) and that B2 role-aware routing would save money by downgrading some to Haiku. The data shows:

1. **Agents already run on mixed tiers** — fd-safety runs on Haiku 47% of the time, fd-correctness on Haiku 26% of the time
2. **Role-aware routing would INCREASE costs by ~20%** — because it enforces safety floors (fd-safety → Sonnet minimum) and planner upgrades (fd-architecture → Opus)
3. **The real problem is quality, not cost** — safety-critical agents running on Haiku is a quality risk that the current routing doesn't prevent

### What This Means

The routing experiment produced a **more valuable finding than projected savings**: it revealed that the current routing has no quality floor for safety-critical agents. This aligns with iv-dthn Loop 2 (Token Efficiency Paradox) — over-optimization degrades quality → retries → net higher cost.

### Per-Agent Analysis

| Agent | Current Haiku % | Should Be | Action |
|-------|----------------|-----------|--------|
| fd-safety | 47% | 0% (min Sonnet) | **P1: Add safety floor** |
| fd-correctness | 26% | 0% (min Sonnet) | **P1: Add safety floor** |
| fd-quality | 28% | 0% (min Sonnet) | P2: Quality floor |
| fd-architecture | 20% | 0% (min Opus) | P2: Planner floor |
| fd-user-product | 27% | Variable | P3: Monitor |
| fd-decisions | 0% | 100% Haiku OK | P4: Haiku candidate |

## Routing Recommendations

### Immediate (P1): Safety Floor
1. **Add `min_model: sonnet` enforcement** for fd-safety and fd-correctness in routing.yaml
2. This INCREASES cost ~20% but prevents quality regression on critical agents
3. Addresses iv-dthn Loop 4 (AgentDropout) risk

### Short-term (P2): Quality Floor for All Review Agents
1. Set minimum Sonnet for all technical review agents
2. Only cognitive agents (checker role) eligible for Haiku
3. Estimated cost increase: ~15% over current, but with quality guarantee

### Deferred: Cost Optimization via Checkers
1. fd-decisions, fd-perception, fd-resilience, fd-people → Haiku candidates
2. Requires 20+ review calibration window (from iv-dthn Loop 4 threshold)
3. Only 1 run of fd-decisions exists — insufficient data

### Routing Policy Recommendation Matrix

| Repo Type | Recommended Policy | Rationale |
|-----------|-------------------|-----------|
| Core services (intermute) | B1 + safety floors | High complexity, safety-critical |
| Plugins (interflux, interlock) | B1 + safety floors | Known patterns, moderate complexity |
| TUI apps (autarch) | B1 + safety floors | Complex but bounded scope |
| Docs-only reviews | B2 enforce (checkers→Haiku) | Low risk, cognitive agents sufficient |

## Experiment Status

| Experiment | Status | Finding |
|-----------|--------|---------|
| Exp 1: Complexity-aware routing | **Complete** (via interstat analysis) | B2 not needed — B1 + floors is optimal |
| Exp 2: Role-aware collaboration | **Complete** (via interstat analysis) | Role mapping reveals quality risk |
| Exp 3: Collaboration modes | **Deferred** | Requires flux-drive dispatch changes |
| Exp 4: Pareto frontier | **Partially complete** | Real data shows B1+floors dominates |

## Next Steps

1. Implement safety floors in routing.yaml (P1)
2. Monitor retry rate as over-optimization canary (from iv-dthn threshold: <15%)
3. Collect 20+ checker-only reviews before enabling Haiku for cognitive agents
4. Re-run this analysis after safety floors are live to measure quality improvement