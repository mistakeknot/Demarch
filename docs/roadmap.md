# Interverse Roadmap

**Modules:** 35 | **Open beads (root tracker):** 338 | **Blocked (root tracker):** 52 | **Last updated:** 2026-02-20
**Structure:** [`CLAUDE.md`](../CLAUDE.md)
**Machine output:** [`docs/roadmap.json`](roadmap.json)

---

## Ecosystem Snapshot

| Module | Location | Version | Status | Roadmap | Open Beads (context) |
|--------|----------|---------|--------|---------|----------------------|
| autarch | hub/autarch | 0.1.0 | early | no | n/a |
| clavain | hub/clavain | 0.6.42 | active | yes | 13 |
| intercheck | plugins/intercheck | 0.1.4 | active | yes | 4 |
| intercraft | plugins/intercraft | 0.1.0 | active | yes | 4 |
| interdev | plugins/interdev | 0.2.0 | active | yes | 4 |
| interdoc | plugins/interdoc | 5.1.1 | active | yes | 4 |
| interfluence | plugins/interfluence | 0.2.3 | active | yes | 4 |
| interflux | plugins/interflux | 0.2.16 | active | yes | 19 |
| interform | plugins/interform | 0.1.0 | active | yes | 4 |
| interject | plugins/interject | 0.1.6 | active | yes | 4 |
| interkasten | plugins/interkasten | 0.4.2 | active | yes | 12 |
| interleave | plugins/interleave | 0.1.1 | early | no | n/a |
| interlens | plugins/interlens | 2.2.4 | active | yes | 4 |
| interline | plugins/interline | 0.2.4 | active | yes | 4 |
| interlock | plugins/interlock | 0.2.1 | active | yes | 10 |
| intermap | plugins/intermap | 0.1.3 | early | no | n/a |
| intermem | plugins/intermem | 0.2.1 | early | no | n/a |
| intermute | services/intermute | — | active | yes | 29 |
| intermux | plugins/intermux | 0.1.1 | active | yes | 4 |
| internext | plugins/internext | 0.1.2 | active | yes | 4 |
| interpath | plugins/interpath | 0.2.2 | active | yes | 4 |
| interpeer | plugins/interpeer | 0.1.0 | early | no | n/a |
| interphase | plugins/interphase | 0.3.2 | active | yes | 4 |
| interpub | plugins/interpub | 0.1.2 | active | yes | 4 |
| intersearch | plugins/intersearch | 0.1.1 | active | yes | 4 |
| interserve | plugins/interserve | 0.1.1 | active | yes | 4 |
| interslack | plugins/interslack | 0.1.0 | active | yes | 4 |
| interstat | plugins/interstat | 0.2.2 | active | yes | 4 |
| intersynth | plugins/intersynth | 0.1.2 | early | no | n/a |
| intertest | plugins/intertest | 0.1.1 | early | no | n/a |
| interverse | root | — | active | yes | n/a |
| interwatch | plugins/interwatch | 0.1.2 | active | yes | 4 |
| tldr-swinton | plugins/tldr-swinton | 0.7.14 | active | yes | 15 |
| tool-time | plugins/tool-time | 0.3.2 | active | yes | 12 |
| tuivision | plugins/tuivision | 0.1.4 | active | yes | 4 |

**Legend:** active = recent commits or active tracker items; early = manifest exists but roadmap maturity is limited. `n/a` means there is no module-local `.beads` database.

---

## Roadmap

### Now (P0-P1)

- [intercore] **iv-0k8s** E6: Rollback and recovery — three-layer revert (blocked by iv-9ofb, iv-9plh, iv-c6az)
- [intercore] **iv-ishl** E7: Autarch Phase 1 — Bigend migration + ic tui (blocked by iv-9plh, iv-c6az)
- [clavain] **iv-kj6w** A2: Sprint handover — sprint skill becomes kernel-driven (blocked by iv-ngvy)

**Recently completed:** iv-bld6 (F2: Workflow state rollback (ic run rollback --to-phase)), iv-2yef (Autarch: ship minimal status tool as kernel validation wedge), iv-pbmc (Cost-aware agent scheduling with token budgets), iv-8jpf (Add reflect/compound phase to default sprint chain), iv-3sns (E4.1: Kernel interspect_events table + ic interspect record CLI), iv-shra (E4.2: Durable cursor registration for long-lived consumers), iv-ooon (Harmonize Clavain docs with revised vision — 6 drift fixes), iv-yeka (Update roadmap.md for new vision + parallel tracks), iv-lhdb (P0: Event emission authority — only kernel should emit state events), iv-s6zo (F1: lib-sprint.sh rewrite — ic run CRUD), iv-l49k (Apply Oracle review synthesis — 10 themes across 3 vision docs), iv-l49k.3 (T3: Move policy out of kernel doc — scoring, decay, presets, revert), iv-l49k.4 (T4: Resolve ic state contradiction — promote to public primitive), iv-l49k.2 (T2: Add write-path contracts — define who can mutate kernel state), iv-l49k.6 (T6: Create shared glossary — resolve term overloading across docs), iv-l49k.1 (T1: Normalize stack to 3 layers — remove 'Layer 3: Drivers' language), iv-ckkr (Apply vision doc review findings — 17 content moves + doc fixes), iv-unsw (Rewrite vision.md — autonomous software agency identity), iv-byh3 (Define platform kernel + lifecycle UX architecture), iv-7o7n (Document slicing for flux-drive agents (P0 token optimization))

### Next (P2)

**Autarch TUI & Dashboard**
- [autarch] **iv-1d9u** Bigend: dashboard metrics from kernel aggregates
- [autarch] **iv-26pj** Streaming buffer / history split per agent panel
- [autarch] **iv-4c16** Bigend: bootstrap-then-stream event viewport
- [autarch] **iv-4zle** Bigend: two-pane lazy* layout (list + detail)
- [autarch] **iv-9au2** Bigend: swap agent monitoring to ic dispatch list
- [autarch] **iv-gv7i** Bigend: swap run progress to ic events tail
- [autarch] **iv-ht1l** Pollard: progressive result reveal per hunter
- [autarch] **iv-jaxw** Typed KernelEvent enum for all observable state changes
- [autarch] **iv-knwr** pkg/tui: validate components with kernel data
- [autarch] **iv-lemf** Bigend: swap project discovery to ic run list
- [autarch] **iv-xlpg** Pollard: optional-death hunter resilience
- [autarch] **iv-xu31** Adopt 4-state status model with consistent icons

**Interspect: Routing, Overrides & Safety**
- [interspect] **iv-003t** Global modification rate limiter
- [interspect] **iv-0fi2** Circuit breaker
- [interspect] **iv-2o6c** F4: status display + revert for routing overrides
- [interspect] **iv-5su3** Autonomous mode flag
- [interspect] **iv-6liz** F5: manual routing override support
- [interspect] **iv-8fgu** F2: routing-eligible pattern detection + propose flow
- [interspect] **iv-bj0w** Conflict detection
- [interspect] **iv-drgo** Privilege separation (proposer/applier)
- [interspect] **iv-gkj9** F3: apply override + canary + git commit
- [interspect] **iv-r6mf** F1: routing-overrides.json schema + flux-drive reader

**Interspect: Evaluation, Learning & Commands**
- [interspect] **iv-435u** Counterfactual shadow evaluation
- [interspect] **iv-88yg** Structured commit message format
- [interspect] **iv-c2b4** /interspect:disable command
- [interspect] **iv-g0to** /interspect:reset command
- [interspect] **iv-izth** Eval corpus construction
- [interspect] **iv-m6cd** Session-start summary injection
- [interspect] **iv-rafa** Meta-learning loop
- [interspect] **iv-t1m4** Prompt tuning (Type 3) overlay-based

**Interlock: Multi-Agent File Coordination**
- [interlock] **iv-1aug** F1: Release Response Protocol (release_ack / release_defer)
- [interlock] **iv-2jtj** F5: Escalation Timeout for Unresponsive Agents
- [interlock] **iv-5ijt** F3: Structured negotiate_release MCP Tool
- [interlock] **iv-6u3s** F4: Sprint Scan Release Visibility
- [interlock] **iv-gg8v** F2: Auto-Release on Clean Files

**Clavain: Routing, Configuration & Sprint Infrastructure**
- [clavain] **iv-3w1x** Split upstreams.json into config + state files
- [clavain] **iv-4728** Consolidate upstream-check.sh API calls (24 to 12)
- [clavain] **iv-asfy** C1: Agency specs — declarative per-stage agent/model/tool config
- [clavain] **iv-dd9q** B1: Static routing table — phase-to-model mapping in config
- [clavain] **iv-k8xn** B2: Complexity-aware routing — task complexity drives model selection
- [clavain] **iv-lx00** C2: Agent fleet registry — capability + cost profiles per agent×model
- [clavain] **iv-o1qz** F4: Sprint skill cleanup — remove lib-gates.sh and redundant calls
- [clavain] **iv-pfe5** F5: Update bats-core tests for ic-only sprint path
- [clavain] **iv-r9j2** A3: Event-driven advancement — phase transitions trigger auto-dispatch
- [clavain] **iv-s80p** F1: ic guard and run ID cache for sprint functions
- [clavain] **iv-sl2z** F3: Remove shell transition table, read chain from ic
- [clavain] **iv-smqm** F2: Remove beads fallback from lib-sprint.sh

**Interstat: Token Metrics & Benchmarking**
- [interstat] **iv-0lt** Extract cache_hints metrics in score_tokens.py
- [interstat] **iv-1gb** Add cache-friendly format queries to regression_suite.json
- [interstat] **iv-bazo** F4: interstat status (collection progress)
- [interstat] **iv-dkg8** F3: interstat report (analysis queries + decision gate)
- [interstat] **iv-lgfi** F2: Conversation JSONL parser (token backfill)
- [interstat] **iv-qi8j** F1: PostToolUse:Task hook (real-time event capture)
- [interstat] **iv-v81k** Repository-aware benchmark expansion for agent coding tasks

**Flux-Drive & Interflux: Review Engine Evolution**
- [flux-drive-spec] **iv-0etu** Phase 3: Extract scoring/synthesis Python library
- [flux-drive-spec] **iv-e8dg** Phase 4: Migrate Clavain to consume the library
- [flux-drive-spec] **iv-ia66** Phase 2: Extract domain detection library
- [interflux] **iv-905u** Intermediate result sharing between parallel flux-drive agents
- [interflux] **iv-qjwz** AgentDropout: dynamic redundancy elimination for flux-drive reviews
- [interflux] **iv-wz3j** Role-aware latent memory architecture experiments

**Intermem, Intercore & Storage**
- [intermem] **iv-bn4j** F4: One-shot tiered migration — --migrate-to-tiered
- [intermem] **iv-f7po** F3: Multi-file tiered promotion — AGENTS.md index + docs/intermem/ detail
- [intercore] **iv-fra3** E5: Discovery pipeline — kernel primitives for research intake
- [intermute] **iv-jc4j** Heterogeneous agent routing experiments inspired by SC-MAS/Dr. MAS
- [interwatch] **iv-mqm4** Session-start drift summary injection

**Interverse Research: Architecture & Strategy**
- [interverse] **iv-3kee** Research: product-native agent orchestration (whitespace opportunity)
- [interverse] **iv-6ikc** Plan intershift extraction (cross-AI dispatch engine)
- [interverse] **iv-dthn** Research: inter-layer feedback loops and optimization thresholds
- [interverse] **iv-ev4o** Agent capability discovery via intermute registration
- [interverse] **iv-exos** Research: bias-aware product decision framework
- [interverse] **iv-fzrn** Research: multi-agent hallucination cascades & failure taxonomy
- [interverse] **iv-jk7q** Research: cognitive load budgets & progressive disclosure review UX
- [interverse] **iv-l5ap** Research: transactional orchestration & error recovery patterns
- [interverse] **iv-p4qq** Smart semantic caching across sessions (intercache)
- [interverse] **iv-quk4** Hierarchical dispatch: meta-agent for N-agent fan-out
- [interverse] **iv-sdqv** Plan interscribe extraction (knowledge compounding)
- [interverse] **iv-xuec** Security threat model for token optimization techniques
- [interverse] **iv-zyym** Evaluate Claude Hub for event-driven GitHub agent dispatch

### Later (P3)

- [interject] **iv-045** Show HN: Off Grid – Run AI text, image gen, vision offline on your phone
- [interverse] **iv-0681** Crash recovery + error aggregation for multi-agent sessions
- [interverse] **iv-0d3a** flux-gen UX: onboarding, integration, docs mentions
- [interject] **iv-0fl7** Exa MCP Integration with Codex | Composio
- [interverse] **iv-0plv** Backend cost arbitrage — multi-model routing in clodex
- [interject] **iv-0r8** Building Interactive Programs inside Claude Code - DEV Community
- [interject] **iv-13q** viktorxhzj/feishu-webhook-skill: A Claude Code skill for sending messages to Fei
- [interverse] **iv-1626** Version-bump → Interwatch signal
- [autarch] **iv-16sw** Pollard: parallel model race for confidence scoring
- [interverse] **iv-173y** Research: guardian agent patterns (formalize quality-gates)
- [interverse] **iv-19m** tldrs: slice command should optionally include source code
- [interverse] **iv-19oc** Research: prompt compression techniques (LLMLingua, gist tokens) for agent context
- [interject] **iv-1cn** Show HN: Skill that lets Claude Code/Codex spin up VMs and GPUs
- [interverse] **iv-1n6z** Monorepo build orchestrator (interbuild) with change detection
- [clavain] **iv-1vny** C4: Cross-phase handoff protocol — structured output-to-input contracts (blocked by iv-asfy)
- [interject] **iv-1x2n** Redacta: Elevating Video Content with GitHub Copilot CLI - DEV Community
- [autarch] **iv-1yck** Bigend: htop-style cost + tool columns per agent
- [interject] **iv-22w** Discover and install prebuilt plugins through marketplaces - Claude Code Docs
- [clavain] **iv-240m** C3: Composer — match agency specs to fleet registry within budget (blocked by iv-asfy, iv-lx00)
- [tldrs] **iv-2izz** LongCodeZip block-level compression

---

## Module Highlights

### clavain (hub/clavain)
Clavain is a recursively self-improving multi-agent rig for Claude Code — 23 skills, 4 agents, 41 commands, 19 hooks, 1 MCP server. 19 companion plugins shipped. 364 beads closed, 0 open. Average lead time: 8.8 hours.

### intercheck (plugins/intercheck)
Intercheck is the quality and session-health layer for Claude Code and Codex operations, focused on preventing unsafe edits before damage occurs.

### intercraft (plugins/intercraft)
Intercraft captures architecture guidance and auditable agent-native design patterns for complex agent behavior.

### interdev (plugins/interdev)
Interdev provides MCP and CLI-oriented developer workflows for discoverability, command execution, and environment tooling.

### interdoc (plugins/interdoc)
Interdoc synchronizes AGENTS.md/CLAUDE.md governance and enables recursive documentation maintenance with review tooling.

### interfluence (plugins/interfluence)
Interfluence provides voice and style adaptation by profile, giving outputs that fit project conventions.

### interflux (plugins/interflux)
interflux is at stable feature-complete breadth (2 skills, 3 commands, 12 agents, 2 MCP servers) and now in a "quality and operations" phase: tightening edge-case behavior, improving observability, and codifying long-term scalability assumptions.

### interform (plugins/interform)
Interform raises visual and interaction quality for user-facing artifacts and interface workflows.

### interject (plugins/interject)
Interject provides ambient discovery and research execution services for agent workflows.

### interlens (plugins/interlens)
Interlens is the cognitive-lens platform for structured reasoning and belief synthesis.

### interline (plugins/interline)
Interline provides session state visibility with statusline signals for multi-agent and phase-aware workflows.

### interlock (plugins/interlock)
Interlock has shipped Phase 1+2 of multi-session coordination: per-session git index isolation, commit serialization, blocking edit enforcement, and automatic file reservation. The system now provides a complete safety layer from first edit through commit.

### intermux (plugins/intermux)
Intermux surfaces active agent sessions and task progress to support coordination and observability.

### internext (plugins/internext)
Internext prioritizes work proposals and tradeoffs with explicit value-risk scoring.

### interpath (plugins/interpath)
Interpath generates artifacts across roadmap, PRD, vision, changelog, and status from repository intelligence.

### interphase (plugins/interphase)
Interphase manages phase tracking, gate enforcement, and work discovery within Clavain and bead-based workflows.

### interpub (plugins/interpub)
Interpub provides safe version bumping, publishing, and release workflows for plugins and companion modules.

### intersearch (plugins/intersearch)
Intersearch underpins semantic search and Exa-backed discovery shared across Interverse modules.

### interserve (plugins/interserve)
Interserve supports Codex-side classification and context compression for dispatch efficiency.

### interslack (plugins/interslack)
InterSlack connects workflow events to team communication channels with actionable context.

### interstat (plugins/interstat)
Interstat measures token consumption, workflow efficiency, and decision cost across agent sessions.

### interwatch (plugins/interwatch)
Interwatch monitors documentation freshness and confidence so stale artifacts are identified before they mislead decisions.

### tldr-swinton (plugins/tldr-swinton)
tldr-swinton is the token-efficiency context layer for AI code workflows. The product has:

### tuivision (plugins/tuivision)
Tuivision automates TUI and terminal UI testing through scriptable sessions and screenshot workflows.

### interkasten (plugins/interkasten)
v0.4.2. Bidirectional Notion sync plugin with a WAL-based protocol (pending → target_written → committed → delete) and three-way merge for conflict resolution. With 12 open beads, active focus spans triage signal refinement, beads-to-Notion issue sync, and the 21-tool MCP surface; webhook receiver and interphase integration are queued for v0.5.x.

---

## Research Agenda

- **Sprint Lifecycle Resilience** — Unified redesign of sprint continuity (bead-first state, auto-advance autonomy, and three-layer rollback) to eliminate fragile env-var state and forward-only phase transitions
- **Intercore Kernel Migration** — Big-bang cutover of sprint state from beads to intercore ic run (E3), followed by fallback code deletion and single-identity model (A2) to reduce the sprint codebase by ~600 lines
- **Token Efficiency: Skill Loading and Document Routing** — Reduce per-invocation ceremony tokens 60-70% via SKILL-compact.md files, pre-computation scripts, and per-agent document slicing using Interserve spark classification
- **Token Efficiency: Context Compression** — Cut tldrs context costs via within-function block compression (LongCodeZip), import-graph deduplication, precomputed workspace bundles, and symbol popularity-guided pruning
- **Subagent Context Flooding** — Wire existing lib-verdict.sh verdict protocol into flux-drive, quality-gates, and review to replace inline TaskOutput flooding with 5-token verdict summaries and selective drill-down
- **Cost-Aware Agent Scheduling** — Connect sprint budget parameters to flux-drive triage and intercore budget algebra via phase-granularity token writeback, enabling soft budget enforcement without real-time JSONL parsing
- **Reflect Phase and Learning Loop** — Add a mandatory reflect phase to the sprint lifecycle (after polish, before done) gated on at least one learning artifact, closing the recursive self-improvement loop
- **Lens-Based Cognitive Review Agents** — Create 5 fd-lens-* flux-drive agents (systems, decisions, people, resilience, perception) that review strategy documents for thinking quality, backed by Interlens MCP tools
- **Agent Rig Autonomous Sync** — Generate setup.md and doctor.md plugin lists from agent-rig.json as single source of truth, with a self-heal runtime fallback and marketplace drift detection
- **Interbus Event Mesh** — Introduce a lightweight intent-envelope integration layer standardizing cross-module communication (discover_work, phase_transition, review_pass), enabling observability
- **Autarch Status Tool** — Build a minimal TUI reading intercore kernel state via ic CLI to validate the kernel API surface and provide real-time "what's running?" visibility before the full Bigend migration
- **Multi-Agent File Coordination** — Complete interlock Phase 4 with a reservation negotiation protocol (request_release/release_ack/release_defer) to enable clean file handoff without merge-agent overhead
- **Framework Benchmarking Ecosystem** — Build a runnable multi-framework benchmark harness (ADK, LangGraph, AutoGen, etc.) with freshness automation and repository-aware corpus expansion
- **Role-Aware Memory and Bias Gates** — Prototype role-scoped memory namespaces (planner/executor/reviewer) with leakage prevention, and design a bias-aware decision framework for high-risk LLM product judgments
- **Sprint Intake Quality and Knowledge Extraction** — Compress brainstorm inputs into structured blueprint artifacts before planning, and extract Clavain's compounding assets into a standalone interscribe plugin

---

## Cross-Module Dependencies

Major dependency chains spanning multiple modules:

- **iv-pfe5** (interverse) blocked by **iv-kj6w** (clavain)
- **iv-sl2z** (interverse) blocked by **iv-kj6w** (clavain)
- **iv-o1qz** (interverse) blocked by **iv-kj6w** (clavain)
- **iv-smqm** (interverse) blocked by **iv-kj6w** (clavain)
- **iv-s80p** (interverse) blocked by **iv-kj6w** (clavain)
- **iv-wz3j** (interflux) blocked by **iv-jc4j** (intermute)
- **iv-6abk** (autarch) blocked by **iv-ishl** (intercore)
- **iv-t4v6** (autarch) blocked by **iv-ishl** (intercore)
- **iv-8y3w** (autarch) blocked by **iv-ishl** (intercore)
- **iv-skyk** (autarch) blocked by **iv-fra3** (intercore)
- **iv-fsxc** (autarch) blocked by **iv-fra3** (intercore)
- **iv-3r6q** (interflux) blocked by **iv-r6mf** (interspect)
- **iv-5pvo** (intercore) blocked by **iv-ev4o** (interverse)

---

## Modules Without Roadmaps

- `hub/autarch`
- `plugins/interleave`
- `plugins/intermap`
- `plugins/intermem`
- `plugins/interpeer`
- `plugins/intersynth`
- `plugins/intertest`

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
