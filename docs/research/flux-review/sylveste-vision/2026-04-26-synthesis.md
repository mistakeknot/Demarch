---
artifact_type: review-synthesis
method: flux-review
target: "/home/mk/projects/Sylveste/docs/sylveste-vision.md"
target_description: "Sylveste vision document v5.0 — autonomous software development agency platform with evidence-compounding trust architecture"
tracks: 2
track_a_agents: [fd-evidence-pipeline-integrity, fd-trust-mechanics, fd-kernel-boundary, fd-dispatch-economics, fd-flywheel-dynamics]
track_c_agents: [fd-assay-office-hallmarks, fd-scriptorium, fd-tidal-bore, fd-perfumer-accord, fd-polynesian-wayfinding]
date: 2026-04-26
quality_mode: economy
---

# Multi-Track Deep Review — Sylveste Vision v5.0

## Critical Findings (P0/P1)

### P0-A. Tier-weight aggregation and evidence schema versioning are unspecified
The vision asserts evidence "compounds" via three tiers (controlled / observational / anecdotal) but never defines the numerical weights, the aggregation function, or the conflict-resolution rule when tiers disagree. Two reviewers given the same evidence cannot independently compute the same maturity score. There is also no schema-versioning story for stored evidence — a kernel-event field addition silently invalidates promotion criteria.
**Surfaced by:** fd-evidence-pipeline-integrity (Track A); reinforced by fd-assay-office-hallmarks (Track C, which named the same gap as "the assayer cannot reproduce another assayer's fineness").
**Fix:** Specify per-tier weight constants, aggregation function, conflict-resolution rule. Either freeze evidence at write time with versioned evaluators, or treat schema migration as an epoch trigger.

### P0-B. Evidence sources are not substrate-independent — five sources, one star
Five evidence sources (Interspect, Interweave, Interop, Factory Substrate, FluxBench) are presented as enrichment, but most or all derive from the same kernel events. A kernel-level anomaly propagates into every "independent" source simultaneously. The five-source framing operationally collapses to one source amplified.
**Surfaced by:** fd-polynesian-wayfinding (Track C); convergent with fd-tidal-bore (Track C) on phase-aligned spurious evidence and fd-evidence-pipeline-integrity (Track A) on independent verification weakness.
**Fix:** Identify which sources are substrate-independent. Designate at least one (FluxBench is the natural candidate as a controlled-experiment runner) with its own data path. Add cross-source independence tests; correlated sources reduce effective evidence count.

### P0-C. Demotion latency unbounded; trust transfer protocol is a vibe-check
The Earn/Compound/Epoch/Demote lifecycle has no upper bound on demotion windows for any criticality tier, and the Auraken→Skaffen trust-transfer protocol is "probationary access with a verification period" with no period length, comparison threshold, or abort criteria specified. Both gaps mean a misbehaving subsystem operates at its prior trust level for unspecified time.
**Surfaced by:** fd-trust-mechanics (Track A); convergent with fd-assay-office-hallmarks (Track C, "no wardens of the touch") and fd-polynesian-wayfinding (Track C, "no procedure for total disorientation recovery").
**Fix:** Specify per-tier demotion windows (Critical: hours; High: hours-to-day; Medium: day-to-week). For trust transfer, specify probation duration, comparison metrics with thresholds, and rollback criteria.

### P0-D. Cost-per-landable-change is not normalized; Goodhart caveat is acknowledged but not engineered
The named north star metric has no normalization for change size, no anti-Goodhart structural mechanism, and no confidence interval on the reported $2.93. The interpretation of $1.17 → $2.93 ("expanded review scope, not regression") is plausible but structurally unprovable from the metric alone.
**Surfaced by:** fd-dispatch-economics (Track A); convergent with fd-perfumer-accord (Track C, "count metrics dominate composition metrics") and fd-scriptorium (Track C, "cost baselines float free of their generating conditions").
**Fix:** Define a complexity-normalized variant. Commit to at least one anti-Goodhart structural mechanism (held-out task set, blind quarterly eval). Report mean ± stddev with sample size.

### P0-E. Phase 3-4 bootstrap unspecified; min() trust creates stuck-loop dynamic
The Governance↔Routing↔Measurement feedback cycle is "bootstrapped by manually-set initial governance policy" but the doc doesn't specify what that policy is, what schema it uses, or how it transitions away. Independently, system trust = min(maturity) means most evidence accumulation produces no observable advancement; the laggard cell is the only thing that matters operationally.
**Surfaced by:** fd-flywheel-dynamics (Track A); reinforced by fd-perfumer-accord (Track C, "subtraction discipline is the missing master signature").
**Fix:** Specify bootstrap policy schema, source, and transition criteria. Replace min() with a percentile aggregation (e.g., 10th-percentile maturity) or weight by criticality.

## Cross-Track Convergence

The strongest signal of this review is that Track A (specialist domain experts) and Track C (distant-domain lenses) independently identified the same five structural gaps. Convergence ranked by score (2/2 means both tracks):

### 1. Independent verification is asserted, not instantiated (2/2)
- **Track A (fd-evidence-pipeline-integrity):** Interspect runs on the same kernel it audits; substrate separation is namespace-level only.
- **Track C (fd-assay-office-hallmarks):** "An assayer without wardens, stamping marks that are not permanent into a substrate it shares with the smiths."
- **Different framings, same gap:** the verifying authority shares failure modes with the verified.

### 2. Append-only / immutability discipline missing for evidence (2/2)
- **Track A (fd-evidence-pipeline-integrity, fd-trust-mechanics):** No evidence schema versioning; threshold revisions not logged with operator identity.
- **Track C (fd-assay-office-hallmarks, fd-scriptorium):** Maturity advancements are computed values not hallmarks; SQLite permits silent overwrite; no rasura discipline.
- **Different framings, same gap:** the system can rewrite its own past.

### 3. Cross-source independence is assumed but not tested (2/2)
- **Track A (fd-flywheel-dynamics):** Phase 1 → Phase 2 likely has hidden Interop dependencies; sprint-as-evidence undifferentiated by quality.
- **Track C (fd-tidal-bore, fd-polynesian-wayfinding):** Five evidence sources may be one source amplified; correlated-noise events produce spurious bores; "five filtered views of one substrate."
- **Different framings, same gap:** the doc treats source diversity as solving what only substrate diversity can solve.

### 4. No procedure for instrument failure or epoch recovery (2/2)
- **Track A (fd-trust-mechanics, fd-flywheel-dynamics):** Demotion latency unbounded; cascade demotion in DAG unspecified; in-flight work behavior during demotion unstated.
- **Track C (fd-polynesian-wayfinding):** No dead-reckoning when evidence pipeline degrades; no post-epoch recovery procedure.
- **Different framings, same gap:** the doc describes steady state and hand-waves transitions.

### 5. Count is celebrated; composition and subtraction are not (2/2)
- **Track A (fd-dispatch-economics):** 589-agent fleet has no tail-management story; Opus 95% of cost presented as incidental.
- **Track C (fd-perfumer-accord):** Plugin count celebrated as growth; no sunset, deprecation, or consolidation in the doc; subtraction discipline missing.
- **Different framings, same gap:** the vision rewards growth and is silent on simplicity.

## Domain-Expert Insights (Track A)

**Theme: the load-bearing parameters are unspecified.** Across all five Track A reviews, the recurring pattern is that the doc names a mechanism (tier weights, demotion latency, schema versioning, cost normalization, balancing-loop dampening) and stops one parameter short of operational specification. Each gap is individually small; together they mean the system's behavior is determined by whatever defaults are encoded in code, not by the doctrine the vision describes.

**Theme: kernel-boundary thesis is real for data and softer for capability.** The "host-agnostic kernel" claim (fd-kernel-boundary) survives for SQLite-backed durability but doesn't survive a real port test. The multi-OS L2-peer scenario (Clavain + Skaffen) is introduced without a coordination contract — concurrent advancement of the same run is undefined.

**Theme: the cost story is the easiest hardening target.** fd-dispatch-economics found four operational issues (no normalization, no confidence interval, fleet bloat, fixed quarantine window) all of which the existing instrumentation can address. The cost section is honest about the $1.17 → $2.93 trajectory; making it rigorous is one PRD's worth of work.

## Structural Insights (Track C)

**fd-assay-office-hallmarks → maker/assayer separation:** The Goldsmiths' centuries of practice insist that the verifier occupy a different building and answer to a different authority than the maker. Maps directly onto the Interspect-runs-on-Intercore problem. Concrete improvement: an immutable advancement-events log distinct from current-state mesh display, and a "wardens" check (FluxBench at M2 minimum) before claiming Interspect is the assay office.

**fd-scriptorium → master-exemplar discipline:** Carolingian copying produced ten centuries of textual continuity by enforcing canonical-exemplar lineage and visible-correction (rasura). Maps onto the missing canonical-store concept for evidence and the missing colophon discipline for cost figures. Concrete improvement: cost values published with embedded snapshot hashes; evidence corrections recorded as new events with "supersedes" references, never as edits.

**fd-tidal-bore → phase alignment in funnel geometry:** Distributed periodic energy meeting a narrowing channel produces walls. Maps onto the v5 expansion's risk: five new evidence sources coming online together can phase-align in their first weeks and produce a spurious convergence-of-evidence bore. Concrete improvement: shadow mode for new sources with explicit independence tests before promotion to active.

**fd-perfumer-accord → composition vs ingredient list:** Subtraction is the master discipline; a great accord has a heart note that defines its character. Maps onto the doc's missing heart-note designation and missing sunset story. Concrete improvement: pick one capability as the doc's heart-note (the kernel-driven sprint lifecycle is the strongest candidate); add quarterly subtraction discipline at the strategic level.

**fd-polynesian-wayfinding → redundant-cue navigation without continuous instruments:** Apprenticeship before voyaging, dead-reckoning through cue-loss, etak reference frames. Maps onto the missing shadow-mode requirement, missing instrument-failure procedure, and missing periodic-snapshot reference frame. Concrete improvement: name a human-wayfinder operational role for outage periods; designate quarterly state snapshots as etak fixes.

## Synthesis Assessment

**Overall quality of the target:** The vision is strong on architecture, honest about current state vs aspiration, and unusually self-consistent for a v5 doc. The composition is excellent at the top (the pitch) and the bottom (layered survival, open source) and muddier in the middle (which capability defines what Sylveste *is* during a working sprint).

**Highest-leverage improvement:** Specify the load-bearing parameters that are currently undefined — tier weights and aggregation function, per-tier demotion latency, evidence freshness/decay windows, per-subsystem promotion criteria. This is one PRD; it would resolve roughly 60% of P0/P1 findings across both tracks. Without it, the doctrine is internally consistent but operationally untestable.

**Surprising finding (cross-track):** The most damning convergence is on the substrate-independence question. Track A reached it as "the verifier shares failure modes with the verified"; Track C reached it as "five filtered views of one substrate" and "an assayer without wardens." Neither track alone framed it sharply enough to drive a fix; together they make it the structural P0 of the document. The vision's evidence thesis depends on source diversity, but the diversity exists at the API level and not the substrate level — a gap that no single specialist would name as starkly as the convergent reading does.

**Semantic distance value:** The two tracks contributed qualitatively different things. Track A produced operationally-specific fixes (specify N, parameterize M, bound the window). Track C produced framings that an operator can carry into design conversations (hallmark log, master exemplar, dead reckoning, heart note, tidal bore). The distant track did not restate the adjacent track's findings in different vocabulary; it surfaced the cross-cutting principle (independent verification, append-only history, redundant cues, subtraction discipline, dead reckoning) that ties the specific gaps together. The two-track minimum was sufficient to detect convergence; a 3- or 4-track run would likely add orthogonal-discipline operational patterns (broadcast scheduling, supply chain, ATC) that were not part of this configuration.

---

## Severity Roll-up

| Severity | Count | Distribution |
|----------|-------|--------------|
| P0 | 12 | Track A: 7, Track C: 5 |
| P1 | 22 | Track A: 13, Track C: 9 |
| P2 | 19 | Track A: 11, Track C: 8 |

## Recommended Next Action

A single follow-on PRD addressing the five P0 convergence themes above would harden the doc materially. Suggested title: "Sylveste Evidence Infrastructure — Operational Parameters and Substrate Discipline." Estimated scope: parameter specification (tier weights, demotion windows, freshness curves, per-subsystem criteria), cross-source independence tests, immutable advancement-events log, normalized cost metric, and bootstrap-policy specification.
