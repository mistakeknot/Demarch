# Demarch Roadmap

**Modules:** 46 (39 versioned) | **Open beads:** 212 | **Blocked:** 59 | **In-progress:** 4 | **Closed:** 1,704 | **Last updated:** 2026-02-23
**Structure:** [`CLAUDE.md`](../CLAUDE.md)
**Machine output:** [`docs/roadmap.json`](roadmap.json)

---

## Ecosystem Snapshot

| Module | Location | Version | Status | Roadmap | Open Beads |
|--------|----------|---------|--------|---------|------------|
| agent-rig | core/agent-rig | 0.1.0 | active | yes | n/a |
| autarch | apps/autarch | 0.1.0 | active | yes | n/a |
| clavain | os/clavain | 0.6.66 | active | yes | n/a |
| interband | core/interband | — | active | yes | n/a |
| interbase | sdk/interbase | — | active | yes | n/a |
| interbench | core/interbench | — | active | yes | n/a |
| interchart | interverse/interchart | 0.1.0 | active | yes | 9 |
| intercheck | interverse/intercheck | 0.2.0 | active | yes | 4 |
| intercom | apps/intercom | 1.1.0 | active | yes | 9 |
| intercore | core/intercore | — | active | yes | n/a |
| intercraft | interverse/intercraft | 0.1.1 | active | yes | 4 |
| interdev | interverse/interdev | 0.2.0 | active | yes | 4 |
| interdoc | interverse/interdoc | 5.1.1 | active | yes | 4 |
| interfin | interverse/interfin | — | active | yes | 9 |
| interfluence | interverse/interfluence | 0.2.6 | active | yes | 4 |
| interflux | interverse/interflux | 0.2.21 | active | yes | 19 |
| interform | interverse/interform | 0.1.0 | active | yes | 4 |
| interject | interverse/interject | 0.1.7 | active | yes | 4 |
| interkasten | interverse/interkasten | 0.4.4 | active | yes | 12 |
| interlearn | interverse/interlearn | 0.1.0 | active | yes | 8 |
| interleave | interverse/interleave | 0.1.1 | active | yes | n/a |
| interlens | interverse/interlens | 2.2.4 | active | yes | 4 |
| interline | interverse/interline | 0.2.6 | active | yes | 4 |
| interlock | interverse/interlock | 0.2.2 | active | yes | 10 |
| intermap | interverse/intermap | 0.1.3 | active | yes | n/a |
| intermem | interverse/intermem | 0.2.2 | active | yes | n/a |
| intermute | core/intermute | — | active | yes | 29 |
| intermux | interverse/intermux | 0.1.2 | active | yes | 4 |
| internext | interverse/internext | 0.1.2 | active | yes | 4 |
| interpath | interverse/interpath | 0.2.2 | active | yes | 4 |
| interpeer | interverse/interpeer | 0.1.0 | active | yes | n/a |
| interphase | interverse/interphase | 0.3.3 | active | yes | 4 |
| interpub | interverse/interpub | 0.1.3 | active | yes | 4 |
| intersearch | interverse/intersearch | 0.1.1 | active | yes | 4 |
| interserve | interverse/interserve | 0.1.4 | active | yes | 4 |
| interslack | interverse/interslack | 0.1.0 | active | yes | 4 |
| interstat | interverse/interstat | 0.2.5 | active | yes | 4 |
| intersynth | interverse/intersynth | 0.1.4 | active | yes | n/a |
| intertest | interverse/intertest | 0.1.1 | active | yes | n/a |
| interwatch | interverse/interwatch | 0.1.4 | active | yes | 4 |
| marketplace | core/marketplace | — | active | yes | n/a |
| tldr-swinton | interverse/tldr-swinton | 0.7.14 | active | yes | 15 |
| tool-time | interverse/tool-time | 0.3.5 | active | yes | 12 |
| tuivision | interverse/tuivision | 0.1.5 | active | yes | 4 |

**Legend:** active = recent commits or active tracker items; early = manifest exists but roadmap maturity is limited. `n/a` means there is no module-local `.beads` database.

---

## Open Epics

| Bead | Priority | Title | Status |
|------|----------|-------|--------|
| iv-w7bh | P1 | Intermap: Project-Level Code Mapping | open |
| iv-14g9 | P2 | TOCTOU prevention: phased dispatch coordination | open |
| iv-pt53 | P2 | Interoperability: cross-module agent discovery, result sharing, and framework benchmarking | blocked |
| iv-5jqi | P3 | [interbase] SDK roadmap — extended API, plugin author guide, additional migrations | open |
| iv-6376 | P3 | [intercore] E9: Autarch Phase 2 — Pollard + Gurgeh migration | open |
| iv-6ixw | P3 | [clavain] C5: Self-building loop — Clavain runs its own development sprints | blocked |
| iv-qr0f | P4 | [intercore] E10: Sandboxing + Autarch Phase 3 (Coldwine) | blocked |

---

## Roadmap

### Now (P0-P1)

**P1 Epic**

- **iv-w7bh** [P1] [epic] Intermap: Project-Level Code Mapping

<details>
<summary>Recently completed (20 items)</summary>

- iv-xuec — Token optimization security threat model + P0/P1 mitigations
- iv-frqh — Modpack auto-install plan tasks marked done
- Expanded compact freshness tooling to cover all 13 skills
- iv-x971 — Cost reconciliation plan
- iv-jc4j — Heterogeneous routing experiment design
- iv-hapr — Session-handoff hook fires on stale in-progress beads
- iv-f6ps — Discovery pipeline shipped-vs-planned contradictions resolved
- iv-v5al — Phase/gate naming mismatch fix
- iv-lqsk — Interspect feedback signal taxonomy defined
- iv-bdbg — Cache interserve codex_query results
- iv-4eau — Default subagents to Haiku/Sonnet (economy model routing)
- iv-7o7n — Document slicing for flux-drive agents (P0 token optimization)
- iv-bad — ArbiterView concurrent map read/write panic fix
- iv-586 — Intermute Reserve() glob overlap detection fix
- iv-cec — SaveRevision non-atomic writes fix
- iv-fi4 — Stop ignoring ValidationResult.Errors in writeSpec() and applyReadySuggestions()
- iv-dfg — Praude status list UX port
- iv-1mq4 — Narrow intercheck PostToolUse matcher
- iv-udyq — Consolidate wildcard hooks (tool-time + hookify)
- iv-puiu — Audit and uninstall unused plugins

</details>

### Next (P2)

**In-Progress (4 items)**

| Bead | Title | Blocks | Blocked By |
|------|-------|--------|------------|
| iv-dthn | Research: inter-layer feedback loops and optimization thresholds | iv-pt53 | — |
| iv-jc4j | [intermute] Heterogeneous agent routing experiments | iv-wz3j, iv-pt53 | iv-qznx |
| iv-p4qq | Smart semantic caching across sessions (intercache) [sprint:true] | iv-pt53 | — |
| iv-qznx | [interflux] Multi-framework interoperability benchmark and scoring harness | iv-jc4j, iv-v81k, iv-pt53 | — |

---

**Clavain Sprint & Workflow Consolidation**

- [clavain] **iv-xxyi** F1: Expand /route — absorb sprint preamble
- [clavain] **iv-qe1j** F2: Slim /sprint — strip preamble, keep phase sequencer
- [clavain] **iv-3ngh** F2: Slim /sprint — pure phase sequencer
- [clavain] **iv-czz4** F3: Update routing table and cross-references
- [clavain] **iv-hks2** Unify /route -> /sprint -> /work into adaptive single-entry workflow
- [clavain] **iv-4728** Consolidate upstream-check.sh API calls (24 to 12)
- [clavain] **iv-3w1x** Split upstreams.json into config + state files
- [clavain/interphase] **iv-zsio** Integrate full discovery pipeline into sprint workflow

**Clavain Agency Configuration & Fleet Registry**

- [clavain] **iv-asfy** C1: Agency specs — declarative per-stage agent/model/tool config
- [clavain] **iv-lx00** C2: Agent fleet registry — capability + cost profiles (blocked by iv-asfy)
- [clavain] **iv-ho3** Epic: StrongDM Factory Substrate — validation-first infrastructure
- [intermute] **iv-jc4j** Heterogeneous agent routing experiments (in-progress, blocked by iv-qznx)
- [interverse] **iv-quk4** Hierarchical dispatch: meta-agent for N-agent fan-out
- [interverse] **iv-6ikc** Plan intershift extraction (cross-AI dispatch engine)
- [interverse] **iv-zyym** Evaluate Claude Hub for event-driven GitHub agent dispatch

**Interspect Routing Override System**

- [interspect] **iv-r6mf** F1: routing-overrides.json schema + flux-drive reader
- [interspect] **iv-8fgu** F2: routing-eligible pattern detection + propose flow (blocked by iv-r6mf)
- [interspect] **iv-gkj9** F3: apply override + canary + git commit (blocked by iv-8fgu)
- [interspect] **iv-2o6c** F4: status display + revert for routing overrides (blocked by iv-gkj9)
- [interspect] **iv-6liz** F5: manual routing override support (blocked by iv-r6mf)
- [interspect] **iv-5su3** Autonomous mode flag
- [interspect] **iv-c2b4** /interspect:disable command
- [interspect] **iv-g0to** /interspect:reset command

**Interspect Safety, Evaluation & Learning**

- [interspect] **iv-003t** Global modification rate limiter
- [interspect] **iv-0fi2** Circuit breaker
- [interspect] **iv-drgo** Privilege separation (proposer/applier)
- [interspect] **iv-bj0w** Conflict detection (blocked by iv-rafa)
- [interspect] **iv-88yg** Structured commit message format
- [interspect] **iv-435u** Counterfactual shadow evaluation
- [interspect] **iv-izth** Eval corpus construction
- [interspect] **iv-rafa** Meta-learning loop
- [interspect] **iv-t1m4** Prompt tuning (Type 3) overlay-based
- [interspect] **iv-m6cd** Session-start summary injection

**Interlock Multi-Agent File Coordination**

- [interlock] **iv-gg8v** F2: Auto-Release on Clean Files
- [interlock] **iv-5ijt** F3: Structured negotiate_release MCP Tool
- [interlock] **iv-6u3s** F4: Sprint Scan Release Visibility
- [interlock] **iv-2jtj** F5: Escalation Timeout for Unresponsive Agents (blocked by iv-5ijt)
- [interverse] **iv-14g9** [epic] TOCTOU prevention: phased dispatch coordination
- [interverse] **iv-pt53** [epic] Interoperability: cross-module agent discovery and benchmarking (blocked by iv-dthn, iv-jc4j, iv-p4qq, iv-qznx)

**Flux-Drive Library Extraction & Interflux Intelligence**

- [flux-drive-spec] **iv-ia66** Phase 2: Extract domain detection library
- [flux-drive-spec] **iv-0etu** Phase 3: Extract scoring/synthesis Python library
- [flux-drive-spec] **iv-e8dg** Phase 4: Migrate Clavain to consume the library
- [interflux] **iv-8cf5** F4: Interflux capability declarations in plugin.json
- [interflux] **iv-qjwz** AgentDropout: dynamic redundancy elimination (blocked by iv-ynbh)
- [interflux] **iv-wz3j** Role-aware latent memory architecture experiments (blocked by iv-jc4j)

**Autarch TUI Rendering & Performance**

- [autarch] **iv-0jfz** Implement design token system for Autarch TUI
- [autarch] **iv-8nly** Implement virtualized lists with Fenwick tree in Bigend
- [autarch] **iv-a0zv** Implement resize coalescing in Bigend
- [autarch] **iv-omzb** Implement inline mode with scrollback preservation (blocks: iv-as0jw, iv-redzz, iv-l2hj8, iv-jjcx6)
- [autarch] **iv-t217** Implement dirty row tracking in Bigend TUI
- [autarch] **iv-26pj** Streaming buffer / history split per agent panel
- [autarch] **iv-m33r** Implement budget degradation with PID controller

**Autarch Product Features & Pollard**

- [autarch] **iv-16z** Wire Coldwine and Pollard signal emitters
- [autarch] **iv-1pkt** Implement phase-based confirmation flow for broadcast actions
- [autarch] **iv-6iu** Integrate Epic/Task generation into unified onboarding flow
- [autarch] **iv-ht1l** Pollard: progressive result reveal per hunter
- [autarch] **iv-l8p** TUI Pollard scan integration
- [autarch] **iv-xlpg** Pollard: optional-death hunter resilience

**Token Efficiency, Benchmarking & Context Engineering**

- [interstat] **iv-0lt** Extract cache_hints metrics in score_tokens.py
- [interstat] **iv-1gb** Add cache-friendly format queries to regression_suite.json
- [interstat] **iv-v81k** Repository-aware benchmark expansion (blocked by iv-qznx)
- [interserve] **iv-fv1f** Implement multi-strategy context estimation
- [interverse] **iv-xuec** Security threat model for token optimization techniques
- [interverse] **iv-jk7q** Research: cognitive load budgets & progressive disclosure review UX

**Core Infrastructure, Memory & Scheduling**

- [intercore] **iv-4nem** Implement fair spawn scheduler
- [intercore] **iv-rjz3** Sandbox specs — SandboxSpec schema on dispatches
- [intercore] **iv-x971** Cost reconciliation — billing vs self-reported token verification
- [intermem] **iv-f7po** F3: Multi-file tiered promotion (blocks: iv-bn4j)
- [intermem] **iv-bn4j** F4: One-shot tiered migration (blocked by iv-f7po)
- [interverse] **iv-sdqv** Plan interscribe extraction (knowledge compounding)

**Intercache: Semantic Caching**

- [intercache] **iv-0qhl** Phase 1: Core cache — blob store + manifest + MCP tools (blocks: iv-3ua2)
- [intercache] **iv-3ua2** Phase 2: Session intelligence — tracking + warming + git hook (blocked by iv-0qhl, blocks: iv-qu6c)
- [intercache] **iv-qu6c** Phase 3: Embedding persistence — storage + semantic search (blocked by iv-3ua2)
- **iv-p4qq** Smart semantic caching across sessions (intercache) — in-progress, sprint:true

**Intercom Messaging Gateway**

- [intercom] **iv-902u6** Gate approval via Telegram
- [intercom] **iv-elbnh** Session continuity across model switches
- [intercom] **iv-niu3a** Discovery triage via messaging
- [intercom] **iv-wjbex** Sprint status push notifications

**Interverse Research & Strategic Exploration**

- **iv-3kee** Research: product-native agent orchestration (whitespace opportunity)
- **iv-dthn** Research: inter-layer feedback loops and optimization thresholds (in-progress)
- **iv-exos** Research: bias-aware product decision framework
- **iv-fzrn** Research: multi-agent hallucination cascades & failure taxonomy
- **iv-j80d** F3: Update routing table and cross-references
- **iv-zzo4** Investigate interflux install failure on new computer
- **iv-x6by** Research: Interspect adaptive profiling and dynamic rule evolution
- **iv-q21d** Research: Fleet orchestration and portfolio management
- **iv-wqk6** Research: The Discovery Pipeline (Level -1)
- **iv-1b3n** Research: Advanced multi-agent coordination
- **iv-zyw5** Research: Token efficiency and context hygiene
- **iv-cuc8** Research: Early and planned modules

### Later (P3-P4)

**P3 Themes** (37+ items across these areas):

**Clavain Self-Building Loop** — C4 cross-phase handoff protocol (blocked by iv-asfy), C5 self-building loop where Clavain runs its own development sprints (blocked by iv-1vny, iv-240m). Prerequisite: agency specs (iv-asfy) must land first.

**Intercore E-Series** — E9 Autarch Phase 2 (Pollard + Gurgeh migration), E10 Sandboxing + Autarch Phase 3 (Coldwine, blocked by E9). Write-path namespace validation and auditing. These form a sequential chain gating the next generation of Autarch capabilities.

**Autarch Advanced Features** — Pollard parallel model race and confidence tiers, Gurgeh spec sprint lifecycle with run versioning and crash-resume, Coldwine risk-gated autopilot with steering queues and ActionResult chaining. Arbiter extraction phases 1-3. Advanced rendering: shimmer/gradient effects, widget state persistence, hit grid, one-writer rule enforcement.

**SDK & Plugin Ecosystem** — Interbase SDK roadmap with extended API, plugin author guide, and additional migrations (iv-5jqi epic). Monorepo build orchestrator (interbuild) with change detection. Marketplace manifest drift auto-close. Version-bump to Interwatch signal pipeline. First-run onboarding tutorial for Autarch.

**Research & Future** — Guardian agent patterns. Prompt compression (LLMLingua, gist tokens). NudgeNik-style LLM agent state classification. Conformal alerting for interstat budgets. GitHub PR integration service (interhub).

**P4 Backlog:** 37 items in deep backlog. These are speculative, low-priority, or dependent on multiple P2/P3 completions before they become actionable.

---

## Module Deep Dives

Detailed status for modules with substantive strategic context. All other modules have one-line summaries in the [Ecosystem Snapshot](#ecosystem-snapshot) table above; their per-module roadmaps are auto-generated from beads via `scripts/generate-module-roadmaps.sh`.

### clavain (os/clavain)

Autonomous software agency — 16 skills, 4 agents, 53 commands, 22 hooks, 1 MCP server. 35 companion plugins. 1,419 beads tracked, 1,098 closed.

**What's Working:** Full product lifecycle (Discover → Design → Build → Ship), three-layer architecture (Kernel/OS/Drivers), multi-agent review engine (interflux), phase-gated `/sprint` pipeline, cross-AI peer review via Oracle, parallel Codex dispatch, 165 structural tests, multi-agent file coordination (interlock), signal-based drift detection (interwatch), Interspect analytics, Intercore kernel as durable state.

**What's Not Working Yet:** No adaptive model routing (B3). Agency architecture is implicit (not declarative specs/fleet registry). Outcome measurement limited (Interspect collects evidence but no override applied yet).

**Three Parallel Tracks:** Track A (Kernel Integration: A1-A3 all done), Track B (Model Routing: B1-B2 done, B3 open P3), Track C (Agency Architecture: C1 done, C2-C5 open). Tracks converge at C5: self-building Clavain that orchestrates its own development sprints.

### intercore (core/intercore)

Orchestration kernel — Go CLI + SQLite. 8 of 10 epics shipped (E1-E8). E1-E7 cover kernel primitives, event reactors, hook cutover, Interspect integration, discovery pipeline, rollback/recovery, and Autarch Phase 1. E8 adds portfolio orchestration with cross-project relay, portfolio runs, and dispatch budgets.

**Open Epics:** E9 (Autarch Phase 2 — Pollard + Gurgeh migration, P3, unblocked) and E10 (Sandboxing + Autarch Phase 3, P4, blocked by E9). Dependency chain: E5+E7 → E9, E8+E9 → E10.

### interflux (interverse/interflux)

Stable feature-complete multi-agent review engine (2 skills, 3 commands, 12 agents, 2 MCP servers) in quality/ops phase. 19 open beads — highest bead count in Interverse.

**What's Working:** Document/file/diff triage with dynamic scoring and staged dispatch, multi-agent research with cost-tiered timeouts and source attribution, domain detection + knowledge injection, protocol specification with 3 conformance levels, synthesis contracts.

**What's Not Working Yet:** No bead queue integration at plugin level, no cross-run cost telemetry dashboard, some domain profiles have coarse research directives, convergence policies not yet benchmarked on long-tail stacks.

**Phases:** Phase 1 (Contract Tightening — reliability, confidence, bead feedback), Phase 2 (Integration — domain depth, DX, Clavain interop), Phase 3 (Scale — adaptive selection, cost controls, knowledge hygiene).

### interlock (interverse/interlock)

Phase 1+2 shipped — per-session git index isolation, commit serialization, blocking edit enforcement, automatic file reservation. MCP server with 9 tools wrapping intermute. 95 structural tests, graceful fail-open when intermute unavailable.

**What's Next:** P2.1 Workflow Integration (auto-join, sprint visibility, bead-agent binding, post-commit broadcast), P2.3 UX/Recovery (interline visibility, automated conflict resolution), Operational improvements (telemetry, status transparency, diagnostics).

### interkasten (interverse/interkasten)

v0.4.4 — production-ready bidirectional Notion sync. 21 MCP tools, 130 tests. Three-way merge via `node-diff3`, WAL-based crash recovery, circuit breaker + exponential backoff, beads issue sync with snapshot-based diff detection, soft-delete with 30-day GC.

**What's Next:** P2.1 Webhooks + Real-Time Sync (webhook receiver, Cloudflare edge, polling fallback), P2.2 Operational Quality (conflict resolver extraction, async beads bridge, config validation), P2.3 Team-Ready Workflows (multi-user conflict resolution, drift observability, safer bulk workflows).

### intermute (core/intermute)

Multi-agent coordination service — Go + SQLite. Core APIs for agent-to-agent messaging, WebSocket delivery, cursor-based inbox, file reservation with shared-lock behavior and background sweep cleanup, domain APIs for specs/epics/stories/tasks/insights/sessions.

**What's Next:** Now (production hardening — startup diagnostics, retry/backoff, DB retention, metrics, operations runbooks, conflict semantics). Next (API versioning, pagination consistency, SDK-ready contracts, developer test fixtures, pluggable storage research). Later (horizontal scalability, hierarchical locking, preflight conflict prediction, mutation audit).

### tldr-swinton (interverse/tldr-swinton)

Token-efficiency context layer. 15 open beads. Production-ready CLI + MCP surfaces, multi-language extraction, semantic search with faiss/colbert backends, diff-aware context workflows, eval wiring through interbench.

**What's Next:** P2.1 Deep Clavain integration (default low-cost context source, stage integration map, context handoff metadata), P2.2 Parity with beads (symbol-boundary truncation, ultracompact depth control, source-aware slice, cache-friendly format), P2.3 Reliability/adoption (friction reduction, MCP telemetry, bug-class mitigation). P2 Scale (long-context persistence, mixed-mode planner, architecture-risk benchmarks, latency-control envelopes).

---

## Research Agenda

- **Kernel E-Series Completion** — Implement E3 (hook migration), E5 (discovery pipeline), E6 (rollback/recovery), E8 (portfolio orchestration) to establish kernel as unified runtime
- **Event-Driven Phase Advancement** — Wire phase transitions through event-emitting action system; `ic run advance` returns resolved next-command(s) via `phase_actions` table
- **Multi-Session File Coordination** — Git-index-per-session + flock-serialized commits, mandatory file reservations on edit, session registration in sprint flow
- **Sprint Resilience & Resume** — Kernel-driven sprint state via `ic run`, cached run ID at claim, session-start sprint detection for zero-setup resume
- **Cost-Aware Agent Scheduling** — Token spend as first-class resource: sprint budgets, budget-aware phase-advance checks, PID controller for degradation
- **Flux-Drive Document Slicing** — Interserve Go MCP server classifying document sections per agent domain; per-agent temp files reducing token consumption 50-70%
- **Cognitive Lens Integration** — Flux-drive lens agents for structured reasoning; triage pre-filter excluding cognitive agents from diff inputs
- **Dual-Mode Plugin Architecture** — Interbase.sh SDK + integration.json schema so plugins work as both CLI and MCP; interflux as reference implementation
- **Agent Capability Discovery** — End-to-end: agents advertise capabilities at registration, intermute filters by capability, consumers query via `ic agent list --capability=`
- **Thematic Work Lanes** — Lanes as first-class kernel entity (auto-discover from `bd label lane:*`), sprint/discovery filtering, lane-scoped scheduling
- **Portfolio Orchestration** — E8 for multi-project coordination: portfolio lanes, dependency scheduling, rollback policy, portfolio-level advance gates
- **Token-Efficient Context Engineering** — Compact SKILL.md generation, pre-computed signals, LLMLingua/gist token compression, subagent context flooding prevention
- **Structured Reflection & Learning** — Reflect phase gate in sprint workflow, kernel-native reflect, durable learning artifacts (not just beads)
- **Plugin Publishing Validation** — Capability declarations, integration.json schema compliance, MCP server health checks as pre-publish gates
- **Safe Approval Flows** — Evaluate phase gate approvals over chat, high-signal message summaries, compact diff artifacts for PR review

---

## Cross-Module Dependencies

Major dependency chains spanning multiple modules:

**Clavain Workflow Unification (iv-hks2 hub)**
- iv-czz4, iv-3ngh, iv-tpi5, iv-j80d, iv-qe1j, iv-xxyi all blocked by **iv-hks2**

**Intermute/Interflux Routing Chain**
- **iv-wz3j** (interflux latent memory) blocked by **iv-jc4j** (intermute routing)
- **iv-jc4j** (intermute routing) blocked by **iv-qznx** (interflux benchmark)
- **iv-3r6q** (interflux) blocked by **iv-r6mf** (interspect routing overrides)

**Interspect Routing Override Chain**
- **iv-r6mf** -> **iv-8fgu** -> **iv-gkj9** -> **iv-2o6c** (sequential F1-F4)
- **iv-6liz** (F5 manual override) also blocked by **iv-r6mf**

**Intercache Phased Chain**
- **iv-0qhl** (Phase 1) -> **iv-3ua2** (Phase 2) -> **iv-qu6c** (Phase 3)

**Bigend Inline Mode (iv-omzb hub)**
- **iv-omzb** blocks: iv-as0jw, iv-redzz, iv-l2hj8, iv-jjcx6

**Agency Specs Chain (iv-asfy hub)**
- **iv-asfy** blocks: iv-lx00, iv-1vny, iv-240m
- iv-1vny + iv-240m -> **iv-6ixw** (C5 self-building loop)

**Intercore Evolution Chain**
- **iv-6376** (E9) -> **iv-qr0f** (E10)

**Interoperability Convergence (iv-pt53)**
- **iv-pt53** blocked by iv-dthn, iv-jc4j, iv-p4qq, iv-qznx (all four must complete)

---

## Keeping Current

```
# Regenerate this roadmap JSON from current repo state
scripts/sync-roadmap-json.sh docs/roadmap.json

# Regenerate via interpath command flow (Claude Code)
/interpath:roadmap    (from Demarch root)

# Auto-generate module-level roadmaps from beads
scripts/generate-module-roadmaps.sh

# Or via interpath command (runs the script)
/interpath:propagate  (from Demarch root)
```
