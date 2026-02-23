# Inter-Layer Feedback Loops and Optimization Thresholds

**Bead:** iv-dthn
**Date:** 2026-02-23
**Sources:** fd-systems findings, fd-performance review, oracle-token-efficiency-review, token-efficiency-agent-orchestration-2026

## The 7 Optimization Layers

| Layer | Name | Key Technique | Best-Case Savings |
|-------|------|---------------|-------------------|
| L1 | Prompt Architecture | File indirection, lazy discovery | 70-88% |
| L2 | Model Routing | Haiku/Sonnet/Opus tiering | 60-80% |
| L3 | Context Isolation | Subagents as GC, fan-out | 67% (but 15x token cost) |
| L4 | Context Compression | LLMLingua, gist tokens, caching | 20-26x compression |
| L5 | Retrieval Architecture | Multi-strategy search (RRF) | Variable |
| L6 | Output Efficiency | Patches, JSON compression, verdicts | 18-31% |
| L7 | Meta-Orchestration | AgentDropout, trajectory pruning | 21-34% |

## Causal Interaction Map

```
  L1 (Prompt)
    │
    ├──→ L4 (Compression): File indirection reduces compressible content
    │    BUT indirection headers break prompt caching [ANTI-PATTERN]
    │
    ├──→ L5 (Retrieval): Lazy discovery means retrieval must compensate
    │    for missing context at call time
    │
    └──→ L2 (Routing): Schema pruning affects model capability requirements
         (simpler prompts → Haiku viable → cost savings)

  L2 (Routing)
    │
    ├──→ L3 (Isolation): Cheaper models enable more subagents
    │    BUT bullwhip effect: Haiku failures cascade to Sonnet → Opus
    │    [FEEDBACK LOOP: see Loop 3]
    │
    └──→ L6 (Output): Cheaper models produce noisier output → more
         post-processing needed

  L3 (Isolation)
    │
    ├──→ L4 (Compression): Subagent summaries are lossy compression
    │    Evidence lost in summarization → verification failures → rework
    │
    └──→ L7 (Meta): More agents = more coordination overhead
         AgentDropout reduces this BUT risks dropping critical agents

  L4 (Compression)
    │
    ├──→ L5 (Retrieval): CRITICAL LOOP — compressed text has different
    │    embeddings than original → vector search degrades
    │    [FEEDBACK LOOP: see Loop 1]
    │
    └──→ L4 (Self): Compression invalidates prompt caching
         [ANTI-PATTERN: compression + caching are mutually exclusive]

  L5 (Retrieval)
    │
    ├──→ L1 (Prompt): Retrieved context expands prompt → back to L1
    │    [FEEDBACK LOOP: see Loop 1 continuation]
    │
    └──→ L3 (Isolation): Multi-strategy retrieval is token-expensive
         → push to subagent → but subagent needs context too

  L6 (Output)
    │
    └──→ L7 (Meta): Verdict filtering reduces downstream agent input
         BUT aggressive filtering loses signal for trajectory pruning

  L7 (Meta)
    │
    └──→ L2 (Routing): AgentDropout changes effective agent count
         → routing table assumptions invalidated
         [FEEDBACK LOOP: see Loop 4]
```

## The 4 Critical Feedback Loops

### Loop 1: Compression ↔ Retrieval (P1, Circular)

```
L4 Compression → embeddings change → L5 retrieval degrades
→ more context fetched → L1 prompt grows → L4 must compress more
```

**Threshold:** Compression ratio > 5x degrades retrieval by ~30% (estimated from LLMLingua papers). Beyond this point, retrieval quality loss exceeds compression savings.

**Mitigation:**
- Embed BEFORE compression (cache original embeddings)
- Use compression only for one-shot contexts, not for indexed content
- intercache (iv-p4qq) stores pre-compression embeddings

**Decision rule:** If content will be retrieved later, do NOT compress it. If content is one-shot (Oracle review, single-use analysis), compress freely.

### Loop 2: Token Efficiency Paradox (P1, Paradox)

```
Over-optimize → quality degrades → retries/rework → NET HIGHER cost
```

**Threshold:** Quality score below 0.7 (on flux-drive 1-5 scale, normalized) triggers retries. Each retry costs ~1.5x the original run. Break-even: optimization must preserve quality > 0.7 to be net positive.

**Mitigation:**
- Set quality floor per agent role (e.g., fd-safety never drops below Sonnet)
- Monitor retry rate as a proxy for over-optimization
- Budget includes 20% retry headroom

**Decision rule:** If an optimization causes >15% retry rate increase, disable it. Measure retry rate over 20+ runs before concluding.

### Loop 3: Bullwhip Effect in Model Routing (P2, Cascade)

```
Haiku overloaded → fallback to Sonnet → Sonnet overloaded
→ fallback to Opus → cost spikes, latency explodes
```

**Threshold:** Haiku error rate > 10% triggers cascade. Each tier upgrade is ~3x cost. A sustained 20% Haiku failure rate can 5x total cost.

**Mitigation:**
- Circuit breaker per tier: max 3 retries before permanent upgrade for session
- Pre-warm with health check before routing
- Budget cap kills the run rather than cascading indefinitely
- Sticky routing: once upgraded, stay upgraded for the session (avoid oscillation)

**Decision rule:** If Haiku success rate for a task type < 85%, route that type directly to Sonnet. Don't attempt to save money on tasks Haiku can't handle.

### Loop 4: AgentDropout ↔ Routing Invalidation (P2, Stability)

```
AgentDropout removes agent → routing table assumes N agents
→ coverage gap → missed finding → user trust erodes
→ add agent back → savings evaporate
```

**Threshold:** AgentDropout safe when historical calibration has 20+ reviews AND the dropped agent's unique finding rate < 5%. Below this sample size, dropout is gambling.

**Mitigation:**
- Require minimum calibration window (20 reviews) before enabling dropout
- Never drop agents with unique P0/P1 finding history
- Track "would have caught" metrics on shadow runs

**Decision rule:** Only drop agents whose findings are fully subsumed by other agents over 20+ reviews. Never drop safety-critical agents (fd-safety, fd-correctness).

## The Additivity Problem

Individual layer savings are NOT additive. Three overlapping optimizations:

| Optimization | Target | Individual Savings |
|-------------|--------|-------------------|
| File indirection (L1) | Orchestrator context bloat | 70% |
| AgentDropout (L7) | Orchestrator prompt + completion | 21.6% / 18.4% |
| Context isolation (L3) | Orchestrator context per agent | 67% |

All three target the same pool: **orchestrator context**. The real ceiling for combined optimization on this pool is **80-90%** after cache warm-up, not 70% + 67% + 21.6%.

**Rule:** When estimating combined savings, identify the common pool. Savings from different pools (e.g., L1 prompt size + L6 output format) DO add. Savings from the same pool compound multiplicatively, not additively.

**Formula for same-pool savings:**
```
combined = 1 - (1 - s1) × (1 - s2) × (1 - s3)
Example: 1 - (0.30 × 0.33 × 0.784) = 92.2% (not 70 + 67 + 21.6 = 158.6%)
```

## Threshold Summary

| Interaction | Threshold | Signal | Action |
|------------|-----------|--------|--------|
| Compression ratio | > 5x | Retrieval recall drops | Stop compressing indexed content |
| Quality floor | < 0.7 normalized | Retry rate > 15% | Disable optimization |
| Haiku failure rate | > 10% per task type | Error rate dashboard | Route to Sonnet for that type |
| Haiku task-type success | < 85% | Per-type metrics | Permanent upgrade to Sonnet |
| AgentDropout calibration | < 20 reviews | Sample count | Block dropout until calibrated |
| Dropped agent unique rate | > 5% | Shadow run tracking | Re-add agent |
| Same-pool optimization cap | > 90% | Budget tracking | Don't stack more optimizations |

## Recommendations for Demarch

1. **Embed before compress** — intercache (iv-p4qq) should store original embeddings, not compressed ones
2. **Compression = one-shot only** — never compress content that will be retrieved or cached
3. **Quality floor per role** — fd-safety and fd-correctness always get Sonnet minimum
4. **Circuit breakers on routing** — sticky session routing, max 3 retries per tier
5. **20-review calibration** — AgentDropout, trajectory pruning, and any statistical optimization needs 20+ sample baseline
6. **Measure retry rate** — this is the canary for over-optimization; track at interstat level
7. **Same-pool audit** — before stacking optimizations, verify they target different token pools
