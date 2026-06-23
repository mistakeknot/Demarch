## Flux Drive Review — Track B6 Microrouter Epic (sylveste-s3z6.19)

**Reviewed**: 2026-05-01 | **Agents**: 8 completed (4 commissioned Track B6 + 4 bonus concurrent) | **Verdict**: risky

### Verdict Summary

| Agent | Status | Summary |
|-------|--------|---------|
| fd-trading-router-bestexec | needs-changes | Shadow log lacks reason-code; promotion gate calendar-only; distribution collapse undetected |
| fd-triage-acuity-routing | risky | P0: garbage-response path could bypass fd-safety/fd-correctness safety floors |
| fd-dispatch-economic-grid | needs-changes | Local-tier label space missing; B3 freshness not a gate; loss design unblocked |
| fd-ss7-cascade-routing | needs-changes | Resolver terminal unproven; route flap; combination failures untested |
| fd-glacial-sediment-cascade-sorting | risky | P0: no-op short-circuit erases microrouter layer from shadow log |
| fd-gongfu-cha-cascade-discernment | risky | P0x2: circular calibration — judge family used for both labels and eval baseline |
| fd-ifa-divination-verifier-corpus | risky | P0: verifier (bead .19.7) would share corpus with microrouter |
| fd-yaki-ire-temper-promotion-gates | risky | P0: privacy=sensitive tasks can fall through to cloud when endpoint is down |

### Critical Findings (P0) — 6 total

P0-1 TRIAGE-1 (3/8 agents): ineligible_agents pre-call enforcement not specified — garbage response could bypass safety floor for fd-safety/fd-correctness (routing.yaml:33-37 invariant)
P0-2 GS-1: Audit-trail unconformity — no-op short-circuit erases microrouter layer from shadow log when router matches B3 output
P0-3 GC-1: Circular calibration — GPT-5.5/Opus used for both label augmentation (bead 3) and eval accuracy anchor (bead 4)
P0-4 GC-2: Co-located with P0-3 — accuracy target measured against judge-shaped calibrated baseline, not independent holdout
P0-5 IF-1: Verifier (bead .19.7) shares corpus and judge with microrouter — systematic judge error propagates to both
P0-6 YI-1: Privacy cloud leak — sensitive tasks escape to cloud when router endpoint is down and privacy_override=always

### Important Findings (P1) — 19 total

Resolver integration (bead .19.5, 8 findings):
- BESTEXEC-1 (2/8 agents): Shadow log lacks reason-code field — timeouts indistinguishable from B3 fallthroughs
- TRIAGE-2: Failure modes not individually tested (each needs named test case)
- SS7-1: Resolver chain terminal not proven reachable — no hardcoded last-resort below defaults.model
- SS7-2: Route flap from intermittent endpoint in 100ms window — cold-start variance invalidates soak metrics
- SS7-3: Simultaneous failure combinations not tested (timeout + calibration absent)
- GRID-2: B3 calibration freshness not a promotion prerequisite
- YI-2: Promotion auto-proceeds on aggregate metrics — no operator review gate for high-stakes agent failures
- YI-3: Garbage-response failure mode unnamed in resolver spec

Promotion gate (3/8 agents):
- BESTEXEC-3 + GS-3 + GRID-4: Calendar duration with no entry floor, no regime diversity requirement

Training and evaluation:
- GRID-1: Loss design deferred; no gate blocks pure cross-entropy — distillation collapse unblocked
- GRID-3: Local model tier labels not required in label space — router cannot dispatch to local fleet
- TRIAGE-3: Coverage report lacks per-complexity-tier breakdown
- GC-4: By-time holdout straddles 2026-04-29 routing regime change
- GS-2: Decision-space cardinality mismatch — binary local/cloud collapses 5-way complexity tiers
- IF-2: 5K example floor doesn't guarantee per-(agent, phase, tier) cell coverage
- IF-3: No startup self-test — router activates without verifying canonical probe cases

### Improvements (top 5)

1. Shadow log schema v2: add reason field + resolver_path array (BESTEXEC-1, SS7-4)
2. Hardcoded terminal: LAST_RESORT_MODEL="sonnet" compile-time constant + TestResolverChainExhaustionFallback (SS7-1)
3. Per-complexity-tier coverage report required in bead 2 Done When (TRIAGE-3)
4. Local-tier first-class decision: bead 1 must include {local:C1, local:C2} as output classes (GRID-3)
5. Privacy fallback spec: bead 6 must constrain to local models when endpoint is down (YI-1)

### Section Heat Map

| Section | P0 | P1 | P2 | Agents |
|---------|----|----|----|----|
| .19.5 — Resolver Integration | 2 | 8 | 6 | all 8 |
| .19.1 — Design Doc | 0 | 3 | 2 | grid, ss7, gongfu, glacial |
| .19.3 — Training Pipeline | 0 | 3 | 1 | grid, gongfu, ifa |
| .19.4 — Eval Harness | 0 | 3 | 2 | bestexec, triage, gongfu, glacial |
| .19.2 — Dataset | 0 | 2 | 2 | triage, gongfu, ifa |
| .19.6 — Privacy Extension | 1 | 0 | 0 | yaki-ire |
| .19.7 — Verifier (stretch) | 1 | 0 | 0 | ifa |
| Epic Success Criteria | 0 | 2 | 1 | bestexec, grid |

### Convergence

| Cluster | Agents | Severity |
|---------|--------|---------|
| ineligible_agents pre-call enforcement | TRIAGE-1, BESTEXEC-4, YI-3 | P0 cluster |
| Shadow log reason-code / per-layer audit | BESTEXEC-1, SS7-4 | P1 x2 |
| Promotion gate entry floor | BESTEXEC-3, GS-3, GRID-4 | P1 x3 |

### Conflicts

None detected. Commissioned agents and bonus agents flagged complementary domains. GRID-1 (cost-weighted loss required) and GC-1 (judge circular validation) are complementary — both must be addressed.

### Files

- Summary: docs/research/flux-drive/INPUT-20260501T2239/summary.md
- Findings: docs/research/flux-drive/INPUT-20260501T2239/findings.json
- Individual reports: 8 fd-*.md files in the same directory

Verdict: risky. Address P0 findings before shadow soak begins. Highest-priority: (1) ineligible_agents pre-call gate, (2) garbage-response failure mode in bead 5, (3) circular calibration design resolved before training.
