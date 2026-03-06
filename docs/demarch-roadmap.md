# Demarch Roadmap

**Modules:** 61 | **Open beads:** 698 (per `bd stats`, 2026-03-06) | **Blocked:** 68 | **Closed:** 2,567 | **Last updated:** 2026-03-06
**Structure:** [`CLAUDE.md`](../CLAUDE.md)
**Machine output:** [`docs/roadmap.json`](roadmap.json)

---

## Ecosystem Snapshot

| Module | Location | Version | Status | Roadmap | Open Beads (context) |
|--------|----------|---------|--------|---------|----------------------|
| agent-rig | core/agent-rig | 0.1.0 | early | no | n/a |
| autarch | apps/autarch | 0.1.0 | active | yes | n/a |
| clavain | os/clavain | 0.6.155 | active | yes | n/a |
| interband | core/interband | — | planned | no | n/a |
| interbench | core/interbench | — | planned | no | n/a |
| intercache | interverse/intercache | 0.2.0 | early | no | n/a |
| interchart | interverse/interchart | 0.1.8 | early | no | n/a |
| intercheck | interverse/intercheck | 0.2.0 | active | yes | 4 |
| intercom | apps/intercom | 1.1.0 | active | yes | n/a |
| intercore | core/intercore | — | active | yes | n/a |
| intercraft | interverse/intercraft | 0.1.2 | active | yes | 4 |
| interdeep | interverse/interdeep | 0.1.6 | early | no | n/a |
| interdev | interverse/interdev | 0.2.0 | active | yes | 4 |
| interdoc | interverse/interdoc | 5.1.2 | active | yes | 4 |
| interfluence | interverse/interfluence | 0.2.8 | active | yes | 4 |
| interflux | interverse/interflux | 0.2.36 | active | yes | n/a |
| interform | interverse/interform | 0.1.0 | active | yes | 4 |
| interject | interverse/interject | 0.1.9 | active | yes | 4 |
| interkasten | interverse/interkasten | 0.4.9 | early | no | n/a |
| interknow | interverse/interknow | 0.1.2 | early | no | n/a |
| interlearn | interverse/interlearn | 0.1.0 | active | yes | 8 |
| interleave | interverse/interleave | 0.1.1 | early | no | n/a |
| interlens | interverse/interlens | 2.2.4 | active | yes | 4 |
| interline | interverse/interline | 0.2.11 | active | yes | 4 |
| interlock | interverse/interlock | 0.2.7 | active | yes | n/a |
| intermap | interverse/intermap | 0.1.5 | active | yes | 7 |
| intermem | interverse/intermem | 0.2.3 | active | yes | n/a |
| intermonk | interverse/intermonk | 0.1.1 | early | no | n/a |
| intermute | core/intermute | — | active | yes | n/a |
| intermux | interverse/intermux | 0.1.2 | active | yes | 4 |
| intername | interverse/intername | 0.1.1 | early | no | n/a |
| internext | interverse/internext | 0.1.4 | active | yes | 4 |
| interpath | interverse/interpath | 0.3.0 | active | yes | 4 |
| interpeer | interverse/interpeer | 0.1.0 | early | no | n/a |
| interphase | interverse/interphase | 0.3.13 | active | yes | 4 |
| interplug | interverse/interplug | 0.1.0 | early | no | n/a |
| interpub | interverse/interpub | 0.1.7 | active | yes | 4 |
| interpulse | interverse/interpulse | 0.1.3 | early | no | n/a |
| interrank | interverse/interrank | 0.1.0 | early | no | n/a |
| interscribe | interverse/interscribe | 0.1.1 | early | no | n/a |
| intersearch | interverse/intersearch | 0.2.0 | active | yes | 4 |
| intersense | interverse/intersense | 0.1.0 | early | no | n/a |
| interserve | interverse/interserve | 0.1.5 | active | yes | 4 |
| intership | interverse/intership | 0.3.0 | early | no | n/a |
| intersight | interverse/intersight | 0.1.3 | early | no | n/a |
| interskill | interverse/interskill | 0.1.1 | early | no | n/a |
| interslack | interverse/interslack | 0.1.0 | active | yes | 4 |
| interspect | interverse/interspect | 0.1.6 | early | [vision](./interspect-vision.md) | n/a |
| interstat | interverse/interstat | 0.2.15 | active | yes | 4 |
| intersynth | interverse/intersynth | 0.1.6 | early | no | n/a |
| intertest | interverse/intertest | 0.1.2 | early | no | n/a |
| intertrace | interverse/intertrace | 0.1.2 | early | no | n/a |
| intertrack | interverse/intertrack | 0.1.0 | active | yes | n/a |
| intertree | interverse/intertree | 0.1.0 | early | no | n/a |
| intertrust | interverse/intertrust | 0.1.2 | early | no | n/a |
| interverse | root | — | active | yes | n/a |
| interwatch | interverse/interwatch | 0.2.0 | active | yes | 5 |
| marketplace | core/marketplace | — | active | yes | n/a |
| tldr-swinton | interverse/tldr-swinton | 0.7.17 | active | yes | n/a |
| tool-time | interverse/tool-time | 0.3.5 | active | yes | n/a |
| tuivision | interverse/tuivision | 0.1.6 | active | yes | 4 |

**Legend:** active = recent commits or active tracker items; early = manifest exists but roadmap maturity is limited. `n/a` means there is no module-local `.beads` database.

---

## Roadmap

### Now — Frontier Priorities

**8 items defining the next phase.** Full inventory in [Detailed Now Inventory](#detailed-now-inventory) below.

1. **[interverse] iv-wie5i** Discovery OS integration — Close the research→backlog loop with event-driven scan triggers and automated triage. *Why frontier: completes the Discover macro-stage, unblocking autonomous problem discovery.*
2. **[interverse] iv-t712t** First-stranger experience — README, install, clavain setup. *Why frontier: the platform play requires other people to be able to run it.*
3. **[interverse] iv-4xnp4** C1 Agency specs — Declarative per-stage agent/model/tool config. *Why frontier: unblocks Track C convergence (C2-C5 all depend on this).*
4. **[interverse] iv-sksfx** Interspect Phase 2 — Evidence-driven agent selection and canary monitoring. *Why frontier: the adaptive routing flywheel has the override mechanism (iv-r6mf shipped) but not yet the evidence→proposal pipeline.*
5. **[interverse] iv-w7bh** Intermap — Project-level code mapping. *Why frontier: hub for the extraction chain, blocks 9 downstream beads.*
6. **[intercom] iv-awny7** Intercom Rust/Postgres cutover — Finish control-plane migration (6 subtasks). *Why frontier: eliminates dual-persistence and Node scaffolding, prerequisite for Intercom reliability work.*
7. **[intercore] iv-fo0rx** Canonical landed-change entity — Define the north-star denominator. *Why frontier: blocks iv-544dn (measurement read model) which blocks the full Interspect evidence pipeline.*
8. **[interverse] iv-2s7k7** Codex-first routing — Auto-delegate CC work to Codex with closed-loop calibration. *Why frontier: the multi-runtime dispatch strategy for Track B.*

**Recently completed:**
- iv-r6mf — Interspect routing overrides F1-F5 (shipped, 127/127 tests passing)
- iv-30zy3 — Durable session-bead-run attribution ledger (kernel v26)
- iv-b46xi — North star baseline ($1.17/landable change)
- iv-544dn — Interspect event validity and outcome attribution (research)
- iv-iglsh — Codex installer docs and SKILL metadata refresh

### Detailed Now Inventory

All P0-P1 items for reference. Items marked ✓ are closed.

- ✓ [intercore/interstat] **iv-30zy3** Durable session-bead-run attribution ledger
- ✓ [interspect] **iv-r6mf** F1: routing-overrides.json schema + flux-drive reader
- ✓ [interverse] **iv-b46xi** Measure north star — cost-per-landable-change baseline
- [intercore] **iv-fo0rx** Define canonical landed-change entity and north-star denominator (blocks iv-544dn)
- [intercom] **iv-awny7** Finish Rust/Postgres control-plane cutover (6 subtasks: iv-awny7.1-.6)
- [interverse] **iv-wie5i** Discovery OS integration (blocks iv-faq6)
- [interverse] **iv-t712t** First-stranger experience
- [interverse] **iv-4xnp4** C1 Agency specs
- [interverse] **iv-sksfx** Interspect Phase 2 — routing overrides chain
- [clavain/interphase] **iv-zsio** Integrate full discovery pipeline into sprint workflow
- [clavain] **iv-asfy** C1: Agency specs — declarative per-stage config
- [interverse] **iv-2s7k7** Codex-first routing
- [interspect] **iv-w3ee6** Preserve raw review semantics in evidence ingestion (blocks iv-544dn)
- [intercore/events] **iv-057uu** Define canonical measurement read model (blocks iv-544dn)
- [interverse] **iv-nnxzo** Research: Memory architecture convergence
- [interverse] **iv-wie5i.2** Research: Discovery ranking precision (blocks iv-wie5i)
- [interverse] **iv-sksfx.1** Research: Offline routing evals (blocks iv-sksfx)
- [interverse] **iv-t712t.3** Research: First-stranger setup failure taxonomy (blocks iv-t712t)
- [interverse] **iv-g36hy** Sprint execution recording in CXDB (blocked by iv-296, iv-ho3)
- [interverse] **iv-83du3** Intercom message delivery reliability
- [interverse] **iv-w7bh** Intermap: Project-Level Code Mapping

### Next (P2)

**Intent Architecture & OS Routing**
- [intercore] **iv-mlca1** F1: Shared intent types (core/intercore/pkg/contract/)
- [clavain] **iv-6ocmi** F2: OS intent router (clavain-cli intent submit)
- [autarch] **iv-4ggh8** F3: Autarch intent migration
- [intercom] **iv-g6wtc** F4: Intercom intent migration
- [clavain] **iv-lx00** C2: Agent fleet registry — capability + cost profiles per agent×model
- [clavain] **iv-14g9** TOCTOU prevention: phased dispatch coordination

**Interspect Adaptive Routing**
- [interspect] **iv-5ztam** Epic: Evidence-driven agent selection
- [interspect] **iv-8fgu** F2: Routing-eligible pattern detection + propose flow
- [interspect] **iv-gkj9** F3: Apply override + canary + git commit
- [interspect] **iv-2o6c** F4: Status display + revert for routing overrides
- [interspect] **iv-6liz** F5: Manual routing override support
- [interspect] **iv-drgo** Privilege separation (proposer/applier)
- [interspect] **iv-435u** Counterfactual shadow evaluation
- [interspect] **iv-003t** Global modification rate limiter
- [interspect] **iv-0fi2** Circuit breaker
- [interspect] **iv-rafa** Meta-learning loop
- [interspect] **iv-t1m4** Prompt tuning (Type 3) overlay-based
- [interspect] **iv-izth** Eval corpus construction
- [interspect] **iv-x6by** Research: Adaptive profiling and dynamic rule evolution

**Intercom Features & Messaging**
- [intercom] **iv-romro/iv-0ewaq** Image/document understanding (multimodal input pipeline)
- [intercom] **iv-o6z3i/iv-sgrz8** Voice message support via Whisper transcription
- [intercom] **iv-7iy1i/iv-vorsr** Warm container pool for faster response latency
- [intercom] **iv-jw6nh/iv-kmn6b** Message delivery confirmation feedback
- [intercom] **iv-r3am8/iv-tpjhx** Conversation memory search (FTS5/semantic)
- [intercom] **iv-hkrlc/iv-3no5z** Typing indicator persists after send_message
- [intercom] **iv-elbnh** Session continuity across model switches
- [intercom] **iv-niu3a** Discovery triage via messaging
- [intercom] **iv-wjbex** Sprint status push notifications
- [intercom] **iv-902u6** Gate approval via Telegram
- [intercom] **iv-0am8w** SessionResetPolicy: idle timeout and daily reset per group
- [intercom] **iv-p3h62** Hermes-style pairing system to replace static allowlists
- [intercom] **iv-q0ddx** Decouple user identity from session: add user_peers table

**Multi-Agent Coordination & Hermes Patterns**
- [wcm] **iv-fwwhl** Epic: WCM multi-agent coordination patterns
- [wcm] **iv-goiyq** Convergence-divergence detection with per-domain calibration
- [wcm] **iv-2n0ew** Idle-time micro-task dispatch with budget gate
- [wcm] **iv-ofgtl** Verifiable work commitment lifecycle with Goodhart resistance
- [wcm] **iv-6bwm7** Research: Measure agent idle time and coordination overhead
- [wcm] **iv-zfvdf** Define interface contract convention using run_artifacts
- [wcm] **iv-hvoyx** Wire intra-sprint bug reporting via review_events
- [hermes] **iv-a0q2r** Adapt parent_session_id compression chain
- [hermes] **iv-7h6tp** Adapt check_fn tool gating pattern
- [hermes] **iv-w1dcl** Adopt 40/60 head/tail output truncation
- [hermes] **iv-qyx8z** Adopt memory-flush-before-compress pattern
- [hermes] **iv-f8s9q** Port Anthropic prompt caching strategy

**Intermap, Interlock & Tool Infrastructure**
- [intermap] **iv-dl72x** F1: Audit existing Intermap MCP tools
- [intermap] **iv-728k** F1: Go MCP scaffold + Python subprocess bridge
- [intermap] **iv-vwj3** F2: Extract Python modules from tldr-swinton
- [intermap] **iv-mif9** F3: Remove moved tools from tldr-swinton
- [intermap] **iv-h3jl** F4: Project registry + path resolver
- [intermap] **iv-3kz0v** F5: Write real Intermap vision and roadmap docs
- [intermap] **iv-80s4e** F6: Cross-project dependency graph MCP tool
- [intermap] **iv-dta9w** F7: Architecture pattern detection MCP tool
- [intermap] **iv-54iqe** F8: Live change awareness MCP tool
- [interlock] **iv-6u3s** F4: Sprint scan release visibility
- [interlock] **iv-gg8v** F2: Auto-release on clean files
- [tool-composition] **iv-w41fn** Expand sequencing hints from real failure data
- [tool-composition] **iv-qi80j** Audit real sessions for unhinted sequencing pipelines

**Metrics, Instrumentation & Flux-Drive**
- [intertrack] **iv-mi8e0** Metrics instrumentation plugin
- [intertrack] **iv-hqdvn** Establish metrics artifact convention
- [intertrack] **iv-z90qq** F1: Interknow failure-signal metrics
- [intertrack] **iv-yhjy4** F2: Verify-fix token savings metrics
- [intertrack] **iv-74moz** F3: Findings-identity overlap metrics
- [intertrack] **iv-f462h** F4: Baseline rescaling discrimination metrics
- [interstat] **iv-v81k** Repository-aware benchmark expansion
- [interstat] **iv-0lt** Extract cache_hints metrics in score_tokens.py
- [interstat] **iv-1gb** Add cache-friendly format queries to regression_suite.json
- [flux-drive] **iv-ia66** Phase 2: Extract domain detection library
- [flux-drive] **iv-0etu** Phase 3: Extract scoring/synthesis Python library
- [flux-drive] **iv-e8dg** Phase 4: Migrate Clavain to consume the library
- [flux-drive] **iv-jgdct** Apply complexity-aware routing across all subagents
- [flux-drive] **iv-qjwz** AgentDropout: dynamic redundancy elimination
- [flux-drive] **iv-quk4** Hierarchical dispatch: meta-agent for N-agent fan-out

**Research & Assessments**
- **iv-1d3v2** Research: Portfolio orchestration economics and dependent-project fan-out
- **iv-i76wv** Research: Autonomy safety policy for auto-remediate and auto-ship
- **iv-dtxkn** Research: Human attention budgets and review UX for multi-agent output
- **iv-lpfin** Research: Standalone degradation matrix for Interverse plugins
- **iv-sym01** Research: Symphony spec analysis — what to adopt
- **iv-sym02** External issue tracker adapter for beads (blocked by iv-sym01)
- **iv-sym03** Dispatch-level retry with exponential backoff (blocked by iv-sym01)
- **iv-zyw5** Research: Token efficiency and context hygiene
- **iv-1b3n** Research: Advanced multi-agent coordination
- **iv-wqk6** Research: The Discovery Pipeline (Level -1)
- **iv-q21d** Research: Fleet orchestration and portfolio management
- **iv-jk7q** Research: Cognitive load budgets and progressive disclosure review UX
- **iv-3kee** Research: Product-native agent orchestration (whitespace opportunity)
- **iv-exos** Research: Bias-aware product decision framework
- **iv-fzrn** Research: Multi-agent hallucination cascades and failure taxonomy
- [research] **iv-iry5n** gemini-api-updater-doc | **iv-m5zw2** cass_memory_system | **iv-vogko** franken_agent_detection | **iv-7v5ow** frankensearch | **iv-9erqx** llm_docs | **iv-ewjom** post_compact_reminder | **iv-ngiet** ultimate_bug_scanner | **iv-qi6k0** automated_plan_reviser_pro | **iv-9dxkz** llm_multi_round_coding_tournament | **iv-w14e1** ntm — integration/inspiration assessments

**Autarch, Bigend & Standalone Features**
- [autarch] **iv-16z** Wire Coldwine and Pollard signal emitters
- [autarch] **iv-l8p** TUI Pollard scan integration
- [autarch] **iv-6iu** Integrate Epic/Task generation into unified onboarding flow
- [autarch] **iv-1pkt** Phase-based confirmation flow for broadcast actions
- [bigend] **iv-8nly** Virtualized lists with Fenwick tree
- [bigend] **iv-m33r** Budget degradation with PID controller
- [intermem] **iv-f7po** F3: Multi-file tiered promotion
- [intermem] **iv-bn4j** F4: One-shot tiered migration
- [intersight] **iv-rjgi9** Optimize Playwright MCP token efficiency
- [interflux] **iv-wz3j** Role-aware latent memory architecture experiments
- **iv-ho3** Epic: StrongDM Factory Substrate
- **iv-zyym** Evaluate Claude Hub for event-driven GitHub agent dispatch
- **iv-sdqv** Plan interscribe extraction (knowledge compounding)
- **iv-6ikc** Plan intershift extraction (cross-AI dispatch engine)
- **iv-fv1f** Implement multi-strategy context estimation

### Later (P3)

- [interverse] **iv-aac9z** F5: Kernel library bindings (intercore/pkg/client/) (blocked by iv-6ocmi)
- [interverse] **iv-sym04** Continuous dispatch daemon mode for Clavain (blocked by iv-sym01)
- [interverse] **iv-sym05** Workspace isolation via git worktree per task (blocked by iv-sym01)
- [interverse] **iv-sym06** Real-time token budget enforcement mid-execution (blocked by iv-sym01)
- [interverse] **iv-sym07** Harness engineering audit: repo health pre-routing gate (blocked by iv-sym01)
- [interverse] **iv-lthzo** Document cross-hook marker-file coordination pattern
- [intercom] **iv-m4y43** Deprecate dualWriteToPostgres fallback
- [intercom] **iv-st0dv** DSN stored indefinitely in PgPool memory
- [intercom] **iv-del8c** Quick reply templates (skip container)
- [intercom] **iv-niap5** Token budget tracking in chat
- [intercom] **iv-azezf** Agent-to-agent shared memory layer
- [intercom] **iv-29les** Self-improvement loop (scheduled self-review)
- [interverse] **iv-7c810** Repeat accuracy benchmark with Sonnet to test model-capability sensitivity
- [interverse] **iv-eu7ge** Self-improvement loop: scheduled self-review of Intercom codebase
- [interverse] **iv-kvu1u** Quick reply templates for common queries (skip container spin-up)
- [interverse] **iv-m3mu5** Token budget tracking and cost awareness in chat
- [interverse] **iv-yww42** Agent-to-agent shared memory layer
- [interverse] **iv-gx405** bd ready --verify: cross-check each result is still open before printing
- [interverse] **iv-sjz6t** Phase 3: Retire SQLite dual-persistence (blocked by iv-83du3, iv-nt43u)
- [interverse] **iv-pkv4y** Study VerifierContext pattern: reuse agent sandbox for reward verification

---

## Module Highlights

### intercheck (interverse/intercheck)
Intercheck is the quality and session-health layer for Claude Code and Codex operations, focused on preventing unsafe edits before damage occurs.

### intercraft (interverse/intercraft)
Intercraft captures architecture guidance and auditable agent-native design patterns for complex agent behavior.

### interdev (interverse/interdev)
Interdev provides MCP and CLI-oriented developer workflows for discoverability, command execution, and environment tooling.

### interdoc (interverse/interdoc)
Interdoc synchronizes AGENTS.md/CLAUDE.md governance and enables recursive documentation maintenance with review tooling.

### interfluence (interverse/interfluence)
Interfluence provides voice and style adaptation by profile, giving outputs that fit project conventions.

### interform (interverse/interform)
Interform raises visual and interaction quality for user-facing artifacts and interface workflows.

### interject (interverse/interject)
Interject provides ambient discovery and research execution services for agent workflows.

### interlearn (interverse/interlearn)
Interlearn indexes cross-repo solution documents and provides search and audit capabilities for institutional knowledge reuse.

### interlens (interverse/interlens)
Interlens is the cognitive-lens platform for structured reasoning and belief synthesis.

### interline (interverse/interline)
Interline provides session state visibility with statusline signals for multi-agent and phase-aware workflows.

### intermap (interverse/intermap)
Project-level code mapping via 9 MCP tools: registry, call graphs, impact analysis, cross-project deps, architecture detection, live changes, and agent overlay.

### intermux (interverse/intermux)
Intermux surfaces active agent sessions and task progress to support coordination and observability.

### internext (interverse/internext)
Internext prioritizes work proposals and tradeoffs with explicit value-risk scoring.

### interpath (interverse/interpath)
Interpath generates artifacts across roadmap, PRD, vision, changelog, and status from repository intelligence.

### interphase (interverse/interphase)
Interphase manages phase tracking, gate enforcement, and work discovery within Clavain and bead-based workflows.

### interpub (interverse/interpub)
Interpub provides safe version bumping, publishing, and release workflows for plugins and companion modules.

### intersearch (interverse/intersearch)
Intersearch underpins semantic search and Exa-backed discovery shared across Interverse modules.

### interserve (interverse/interserve)
Interserve supports Codex-side classification and context compression for dispatch efficiency.

### interslack (interverse/interslack)
InterSlack connects workflow events to team communication channels with actionable context.

### interstat (interverse/interstat)
Interstat measures token consumption, workflow efficiency, and decision cost across agent sessions.

### interwatch (interverse/interwatch)
Interwatch monitors documentation freshness — auto-discovers watchable docs by convention, detects drift via 14 signal types, scores confidence, and dispatches to generators for refresh.

### tuivision (interverse/tuivision)
Tuivision automates TUI and terminal UI testing through scriptable sessions and screenshot workflows.

---

## Research Agenda

- **Sprint resilience and agent coordination** — Multi-phase work on sprint handover, agent claiming protocols, shift-work boundary formalization, and cross-phase handoff to make long-running autonomous work survive session boundaries.
- **Token and cost optimization** — Token-efficient skill loading, budget controls, cost-aware agent scheduling, cost reconciliation, and accuracy gap measurement to reduce per-change cost and improve output quality.
- **Clavain kernel evolution** — Go migration of clavain-cli, kernel schema validation, native kernel coordination, hierarchical dispatch meta-agent, adaptive routing (b3), composer (c3), self-building loop (c5), and unified routing engine.
- **Intercore event pipeline** — Hook cutover (e3), discovery pipeline (e5), portfolio orchestration (e8), rollback recovery, fair spawn scheduler, sandbox specs, and Go wrapper for Autarch integration.
- **Observability and tracing** — Unified structured logging, MCP instrumentation middleware, intertrace cross-module integration tracer, tool selection failure instrumentation, and fleet registry enrichment for operational visibility.
- **Review and safety systems** — Interspect approve/propose flows, pattern detection, routing overrides, disagreement pipeline, agent trust scoring, safety floors, and Go redaction library for secure multi-agent review.
- **Plugin ecosystem maturity** — Dual-mode plugin architecture, publishing validation pipeline overhaul, plugin synergy catalog, data-driven plugin boundaries, modpack auto-install, and interverse plugin decomposition.
- **Code intelligence and mapping** — Intermap project-level code mapping, Python sidecar, live changes hardening, TLDRs import graph compression (dedup, longcodezip, precomputed context bundles, symbol popularity index), and intercache.
- **Knowledge and learning loops** — Reflect-phase learning loop, knowledge distillation pipeline, review quality feedback loop, intermonk dialectic reasoning, interdeep deep research, and role-aware latent memory experiments.
- **Multi-agent collaboration** — Interlock window identity, intermute contact policies and broadcast/topic messages, adopt mcp-agent-mail patterns, heterogeneous collaboration routing, and "when Claudes meet" interaction patterns.
- **SDK and cross-language support** — Interbase multi-language SDK, Go module path alignment, interbump transactional safety, and gemini CLI integration adapter for broader agent and language coverage.
- **Developer experience and onboarding** — First-stranger experience, project onboard skill, Autarch status tool, bigend migration (dirty row tracking, inline log pane), session start drift summary injection, and search surface documentation.
- **Document and artifact pipelines** — Flux-drive document slicing and intermediate findings, interscribe doc quality and extraction, CUJs as first-class artifacts, intent contracts, blueprint distillation sprint intake, and factory substrate for reproducible builds.
- **Application layer (Intercom and Intersight)** — Intercom H2 last-mile delivery, outbox listen-notify, interfin design, intersight UI design analysis, and interchart ecosystem diagrams.
- **Operational workflows** — Backlog hygiene gate, thematic work lanes, oodarc shared observation loops, Pollard hunter progressive reveal, catalog reminder escalation, and intent submission mechanism for structured planning.

---

## Cross-Module Dependencies

Major dependency chains spanning multiple modules:

- **iv-5ztam** (interverse) blocked by **iv-003t** (interspect)
- **iv-5ztam** (interverse) blocked by **iv-0fi2** (interspect)
- **iv-5ztam** (interverse) blocked by **iv-2o6c** (interspect)
- **iv-5ztam** (interverse) blocked by **iv-435u** (interspect)
- **iv-5ztam** (interverse) blocked by **iv-5su3** (interspect)
- **iv-5ztam** (interverse) blocked by **iv-6liz** (interspect)
- **iv-5ztam** (interverse) blocked by **iv-88yg** (interspect)
- **iv-5ztam** (interverse) blocked by **iv-8fgu** (interspect)
- **iv-5ztam** (interverse) blocked by **iv-bj0w** (interspect)
- **iv-5ztam** (interverse) blocked by **iv-c2b4** (interspect)
- **iv-5ztam** (interverse) blocked by **iv-drgo** (interspect)
- **iv-5ztam** (interverse) blocked by **iv-g0to** (interspect)
- **iv-5ztam** (interverse) blocked by **iv-gkj9** (interspect)
- **iv-5ztam** (interverse) blocked by **iv-izth** (interspect)
- **iv-5ztam** (interverse) blocked by **iv-m6cd** (interspect)
- **iv-5ztam** (interverse) blocked by **iv-rafa** (interspect)
- **iv-5ztam** (interverse) blocked by **iv-t1m4** (interspect)
- **iv-mi8e0** (interverse) blocked by **iv-74moz** (intertrack)
- **iv-mi8e0** (interverse) blocked by **iv-f462h** (intertrack)
- **iv-mi8e0** (interverse) blocked by **iv-hqdvn** (intertrack)
- **iv-mi8e0** (interverse) blocked by **iv-yhjy4** (intertrack)
- **iv-mi8e0** (interverse) blocked by **iv-z90qq** (intertrack)
- **iv-5ubkh** (fd) blocked by **iv-5ztam** (interverse)
- **iv-3r6q** (interflux) blocked by **iv-r6mf** (interspect)

---

## Modules Without Roadmaps

- `core/agent-rig`
- `core/interband`
- `core/interbench`
- `interverse/intercache`
- `interverse/interchart`
- `interverse/interdeep`
- `interverse/interkasten`
- `interverse/interknow`
- `interverse/interleave`
- `interverse/intermonk`
- `interverse/intername`
- `interverse/interpeer`
- `interverse/interplug`
- `interverse/interpulse`
- `interverse/interrank`
- `interverse/interscribe`
- `interverse/intersense`
- `interverse/intership`
- `interverse/intersight`
- `interverse/interskill`
- `interverse/interspect`
- `interverse/intersynth`
- `interverse/intertest`
- `interverse/intertrace`
- `interverse/intertree`
- `interverse/intertrust`

---

## Keeping Current

```
# Regenerate this roadmap JSON from current repo state
scripts/sync-roadmap-json.sh docs/roadmap.json

# Regenerate via interpath command flow (Claude Code)
/interpath:roadmap    (from Interverse root)

# Propagate items to subrepo roadmaps
/interpath:propagate  (from Interverse root)
```
