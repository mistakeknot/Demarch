# Sylveste v1.0 Stability Contract

**Status:** Draft
**Date:** 2026-03-21
**Bead:** Sylveste-enxv.1
**Grounded in:** 6-agent cross-domain research (versioning philosophy, maturity models, OSS readiness signals, cybernetics/VSM, agent ecosystem readiness, game design readiness)

---

## 1. What v1.0.0 Means

v1.0.0 is a **stability commitment**, not a feature release. Following the pattern of Go 1.0, Terraform 1.0, and Rust 1.0: the declaration signals that the *mechanism for evolving without breaking* is operational, not that all features are complete.

The pharmaceutical analogy: v1.0 is an NDA approval — sufficient evidence of efficacy under defined conditions — not complete understanding of the drug.

**The threshold:** Three calibration loops (routing, gates, phase-cost) operate autonomously without human intervention. The system improves itself without manual cranking.

---

## 2. Three-Layer Compatibility Model

### Layer 1: Structural API Stability (SemVer-protected until v2.0)

What is frozen:
- `ic` CLI commands (input arguments, output shapes, exit codes)
- Plugin manifest schema (`plugin.json`)
- Hook lifecycle and contract (`hooks.json` format, event names)
- Event stream format (event types, field names)
- Kernel data model (runs, phases, gates, dispatches, state, locks)
- Bead schema and state transitions
- Configuration contract (CLAUDE.md, AGENTS.md, `.clavain/` keys)

**Migration guarantee:** Plugins built for v1.0 load in v1.x without code changes.

**Enforcement:** Automated schema validation, contract tests, plugin compatibility matrix.

### Layer 2: Behavioral Policies (evolve with notice, not SemVer)

What may change:
- Model routing decisions (which model for which task)
- Gate thresholds (calibration adjusts from outcome history)
- Review agent behavior (scoring, what is examined)
- Default prompts and system messages
- Cost and token consumption (efficiency improvements)

**Mechanism:** Behavioral changelog with `[behavior]` tag. GODEBUG-style pinning: projects declare `sylveste-compat: 1.2` to freeze behavioral defaults to a specific version's values.

**Enforcement:** Interspect overlay logs, canary windows before defaults change, compatibility version pinning.

### Layer 3: Model-Dependent Behavior (not promised, adaptation guaranteed)

What is explicitly stochastic:
- Specific code outputs (non-deterministic by design)
- Model availability (external dependency)
- Output quality floor (depends on model capabilities)
- Timing and latency (provider infrastructure-dependent)
- Cost per token (provider pricing changes externally)

**What IS promised:** The system detects model changes within N sprints, falls back gracefully, and re-optimizes routing without human intervention. The *adaptation mechanism* is stable even when the models are not.

**Model changes are NOT platform breaking changes** — analogous to Terraform's core/provider boundary. Model routing is documented in a separate changelog from platform releases.

---

## 3. What v1.0.0 Excludes

Following Terraform's provider exclusion pattern and Kubernetes' alpha/beta API exclusion:

| Excluded | Rationale |
|----------|-----------|
| Interverse plugins (53+) | Evolve independently, like Terraform providers. Plugin API is stable; plugin behavior is not a platform promise. |
| Output quality floor | Property of models, not platform. Platform promises routing and gating, not intelligence. |
| Behavioral determinism | Stochastic outputs are a feature, not a bug. Same input will not produce identical outputs. |
| Universal domain coverage | v1.0 covers the declared Operational Design Domain. Arbitrary software development is v2.0+. |
| Autonomy L4+ | No auto-merge or auto-deploy. Human approval required at ship phase. L4+ are v2.0+ goals. |
| Cost stability | Token pricing changes externally. Platform promises cost-aware routing, not cost guarantees. |

---

## 4. Operational Design Domain (ODD)

v1.0 declares what it is designed for. Expanding the ODD is a separate axis from version bumps.

### In Scope (v1.0)

- Single-repository software development
- Languages: Go, Python, TypeScript, Rust (others functional but not fully qualified)
- Project types: CLI tools, libraries, web services, infrastructure
- Human review at phase gates — v1.0 supports [human delegation ladder](../canon/autonomy.md#1-human-delegation-ladder-l0l5) levels L1 through L3 (a supported range, not the current position, which that page records)
- Codebase size: 100 LOC to 1M LOC
- Team size: solo developer to small teams

### Out of Scope (v2.0+)

- Multi-repo coordination
- Novel domains without precedent (domain transfer)
- Autonomy L4+ (auto-ship, cross-repo learning)
- Monorepos >1M LOC (untested)
- Real-time or safety-critical systems

---

## 5. Milestone Path

### v0.7.0 — Closed-Loop Autonomy

**Gate:** All three calibration loops operate autonomously.

| Deliverable | Current State |
|-------------|---------------|
| Interspect routing override generation runs on schedule | Plumbing exists, zero production callers |
| Gate threshold calibration runs from historical data | Architecture exists, defaults hardcoded |
| Phase-cost calibration integrated into sprint flow | Manual trigger via calibrate-phase-costs |
| `bd doctor --deep` runs automatically, blocks on corruption | Manual invocation only |

**Exit criteria:**
- 10 consecutive sprints with no manual calibration intervention
- Deletion-recovery test: amnesiac sprints >15% worse, recovery <50 sprints
- All 6 PHILOSOPHY.md calibration domains at stage 3-4

### v0.8.0 — Evaluation Infrastructure + L3 Auto-Remediation

**Gate:** The system measures its own reliability and recovers from common failures.

| Deliverable | Current State |
|-------------|---------------|
| pass@k evaluation harness (3+ complexity tiers) | Not built |
| Adversarial test suite (semantic cascade detection >70%) | Not built |
| Canary window mechanism for model upgrades | Designed, not operational |
| Anomaly detection on core metrics with alerting | Not built |
| Autonomy L3: auto-remediation (retry, substitute, adjust) | Not built |
| All existential failure modes mechanically prevented | Partially (gates exist, enforcement incomplete) |

**Exit criteria:**
- pass@k metrics published for Sylveste codebase
- Semantic cascade detection rate >70%
- Model upgrade detection latency <1 sprint
- 100 consecutive sprints without existential failures

### v0.9.0 — External Validation + ODD Publication

**Gate:** Proven on codebases outside the developer's control.

| Deliverable | Current State |
|-------------|---------------|
| 2+ external same-class projects, 50+ sprints each | L0 only (self-building, 785+ sessions) |
| 3+ cross-domain projects, 20+ sprints each | Not started |
| ODD published in public documentation | Implicit in PHILOSOPHY.md |
| First-hour viability: install to shipped change <60 minutes | Onboarding is a known pain point |

**Exit criteria:**
- External metrics published alongside internal metrics
- 70%+ of new users complete first sprint without help
- Zero catastrophic failures on external projects

### v1.0.0 — Stability Commitment

**Gate:** All criteria from v0.7 + v0.8 + v0.9 sustained. No new features vs v0.9.x.

| Deliverable | Current State |
|-------------|---------------|
| API stability contract published | This document (draft) |
| Behavioral envelope published (pass@k, completion rates) | Not measured |
| Deletion-recovery test passed | Never run |
| External validation evidence published | Not collected |
| v1.x release plan (maintenance window, compat guarantees) | Not written |
| Backward compatibility tested (v1.0 plugins in v1.5) | Not possible yet |

**v1.0.0 ships zero new features.** Like Terraform 1.0 vs 0.15.5: the declaration is about stability, not capability.

---

## 6. The Deletion-Recovery Test

The single diagnostic test that validates v1.0 readiness across all six research frameworks simultaneously.

**Protocol:**
1. Snapshot all calibration state (interspect.db, routing overrides, calibration history, mutation store)
2. Delete the calibration state
3. Run 10 sprints on the standard problem distribution
4. Measure degradation vs baseline on: cost, duration, defect rate
5. Continue running without manual intervention on calibration
6. Measure sprints-to-recovery (when metrics return to baseline)

**Pass criteria:**
- Amnesiac sprints degrade >15% on at least two metrics (proves calibration state is load-bearing)
- Recovery occurs within 50 sprints (proves system is self-maintaining)
- No human touches calibration/routing/gate configuration during recovery (proves autonomy)

**What this validates:**
- VSM completeness: evidence data is operationally necessary
- Autopoietic closure: system reproduces its own parameters from outcomes
- Dissipative bifurcation: organized state is self-reinforcing
- Stigmergic propagation: outcomes coordinate future behavior
- Free energy minimization: system autonomously reduces surprise
- Requisite variety: calibration adds variety that defaults lack

---

## 7. Existential Failure Modes (must be absent at v1.0)

| Failure Mode | Description | Prevention |
|-------------|-------------|------------|
| Unbounded cascading | Wrong output amplified through phases | Phase gate circuit breakers, mechanically enforced |
| Semantic cascade | Valid syntax, wrong semantics, amplified | Adversarial testing, cross-phase consistency checks |
| Silent degradation | Model downgrade undetected | Anomaly detection, canary windows, <N sprint detection |
| State corruption | Unrecoverable beads/calibration state | `bd doctor --deep` auto-runs, blocks on corruption |
| Unprovenanced modification | Routing/thresholds change without receipt | Every overlay/override produces durable log entry |
| Infinite loops | Agent exceeds budget without termination | Hard token ceiling + wall-clock timeout, kernel-enforced |
| Degenerate strategy | Gate-farming, review-stuffing, model-hoarding | Metric rotation, diversity monitoring, randomized audits |

---

## 8. Breaking Change Communication

### Structural (API, schema, CLI)
- 2 minor releases of deprecation warnings before removal
- Migration guide published with each deprecation
- `bd doctor` and `/clavain:doctor` check for deprecated feature usage

### Behavioral (routing, gates, review criteria)
- `[behavior]` tag in release notes
- GODEBUG-style pinning: `sylveste-compat: <version>` in project config
- Changes justified by evidence (outcome data), not opinion

### Model-driven (new models, model deprecations)
- Separate model routing changelog from platform releases
- Model version pinning available
- Canary period before new model becomes default

---

## 9. Readiness Checklist (60 items)

### Structural Stability
- [ ] Public API surface documented (ic CLI, plugin.json, hooks, events)
- [ ] Deprecation policy published with timeline
- [ ] Plugin backward compat: v1.0 plugins load in v1.x
- [ ] Migration guide from v0.6.x to v1.0.0
- [ ] Kernel data model versioning with forward-compatible evolution

### Closed-Loop Autonomy
- [ ] Interspect routing override generation autonomous
- [ ] Gate threshold calibration autonomous from historical data
- [ ] Phase-cost calibration integrated into sprint flow
- [ ] All 6 PHILOSOPHY.md calibration domains at stage 3-4
- [ ] Deletion-recovery test passes

### Behavioral Stability
- [ ] pass@k metrics published for 3+ task complexity tiers
- [ ] Sprint completion rate >80% on self-building workloads
- [ ] Post-merge defect rate tracked with declining 90-day trend
- [ ] Gate false-positive rate <20%
- [ ] Gate false-negative rate measured by adversarial testing
- [ ] Cost per landable change tracked with automatic attribution
- [ ] Model upgrade impact report automated

### Failure Mode Absence
- [ ] No unbounded cascading failures
- [ ] No silent quality degradation
- [ ] No unrecoverable state corruption
- [ ] No unprovenanced self-modification
- [ ] No infinite agent loops
- [ ] Semantic cascade detection rate >70%
- [ ] No degenerate strategy collapse

### Recovery and Resilience
- [ ] Sprint rollback functional and tested
- [ ] Routing fallback functional (model unavailable -> next tier)
- [ ] Human escalation path works from any state
- [ ] Evidence recovery after recording failure
- [ ] Graceful degradation under rate-limit exhaustion

### Observability
- [ ] Distributed tracing with sprint-level trace IDs
- [ ] Cost attribution per sprint/phase/agent
- [ ] Quality dashboard (gate rates, completion rates, costs)
- [ ] Anomaly detection with alerting
- [ ] All 5 onboarding stage events instrumented

### Multi-Project Validation
- [ ] Self-building metrics published (L0)
- [ ] 2+ external same-class projects, 50+ sprints each (L1)
- [ ] 3+ cross-domain projects, 20+ sprints each (L2)
- [ ] Untested domains explicitly documented

### Game Design Criteria
- [ ] 90% of sprints have retroactive legibility
- [ ] Bounded surprise: defect rate within 2x baseline after any update
- [ ] Meta stability: no routing tier >70%, 5+ problem classes at >80%
- [ ] Strategy-outcome correlation statistically significant
- [ ] Operator expression measurable: different profiles -> different outcomes
- [ ] Onboarding: first shipped change <60 minutes, 70%+ success rate

### Cybernetic Viability
- [ ] VSM completeness: all five systems operational (S1-S5)
- [ ] Autopoietic closure: 3+ dimensions of self-reproduction
- [ ] Requisite variety: >80% tasks use specialized routing
- [ ] Free energy minimization: prediction error triggers autonomous response
- [ ] No alignment faking: Interspect cannot modify its own evaluation criteria

### Operational Design Domain
- [ ] In-scope domains published
- [ ] Out-of-scope domains published
- [ ] Autonomy tier promise published (L1-L3)
- [ ] Human oversight requirements documented

### Release Infrastructure
- [ ] v1.x maintenance commitment published (minimum 24 months)
- [ ] Security fix backport policy defined
- [ ] Backward compatibility test suite exists
- [ ] "State of Production Readiness" document template ready

---

## Research Provenance

This contract is grounded in findings from:
- `fd-versioning-philosophy`: SemVer contracts, pharma NDA analogy, GODEBUG-style pinning
- `fd-maturity-models`: NASA TRL 6-7 assessment, composite rubric, "ready to deploy vs ready to be relied upon"
- `fd-oss-readiness-signals`: Rust/Go/K8s/Terraform/Nix 1.0 empirical signals, stability mechanism pattern
- `fd-autopoiesis-viability`: Beer's VSM (S4 missing), deletion-recovery test, Ashby's requisite variety
- `fd-agent-ecosystem-readiness`: Three-layer stability model, semantic cascade, LangChain surface shrinkage
- `fd-game-design-readiness`: Degenerate strategy detection, first-hour viability, meta-stability signal

Full research at `.claude/flux-drive-output/fd-*.md` and `synthesis-v1-maturity.md`.
