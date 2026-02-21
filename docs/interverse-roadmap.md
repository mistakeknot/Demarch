# Interverse Roadmap

**Modules:** 37 | **Open beads (root tracker):** 325 | **Blocked (root tracker):** 37 | **Last updated:** 2026-02-21
**Structure:** [`CLAUDE.md`](../CLAUDE.md)
**Machine output:** [`docs/roadmap.json`](roadmap.json)

---

## Ecosystem Snapshot

| Module | Location | Version | Status | Roadmap | Open Beads (context) |
|--------|----------|---------|--------|---------|----------------------|
| autarch | hub/autarch | 0.1.0 | active | yes | n/a |
| clavain | hub/clavain | 0.6.60 | active | yes | n/a |
| interchart | plugins/interchart | 0.1.0 | early | no | n/a |
| intercheck | plugins/intercheck | 0.2.0 | active | yes | 4 |
| intercraft | plugins/intercraft | 0.1.0 | active | yes | 4 |
| interdev | plugins/interdev | 0.2.0 | active | yes | 4 |
| interdoc | plugins/interdoc | 5.1.1 | active | yes | 4 |
| interfluence | plugins/interfluence | 0.2.5 | active | yes | 4 |
| interflux | plugins/interflux | 0.2.19 | active | yes | 19 |
| interform | plugins/interform | 0.1.0 | active | yes | 4 |
| interject | plugins/interject | 0.1.6 | active | yes | 4 |
| interkasten | plugins/interkasten | 0.4.3 | active | yes | 12 |
| interlearn | plugins/interlearn | 0.1.0 | early | no | n/a |
| interleave | plugins/interleave | 0.1.1 | active | yes | n/a |
| interlens | plugins/interlens | 2.2.4 | active | yes | 4 |
| interline | plugins/interline | 0.2.6 | active | yes | 4 |
| interlock | plugins/interlock | 0.2.1 | active | yes | 10 |
| intermap | plugins/intermap | 0.1.3 | active | yes | n/a |
| intermem | plugins/intermem | 0.2.2 | active | yes | n/a |
| intermute | services/intermute | — | active | yes | 29 |
| intermux | plugins/intermux | 0.1.1 | active | yes | 4 |
| internext | plugins/internext | 0.1.2 | active | yes | 4 |
| interpath | plugins/interpath | 0.2.2 | active | yes | 4 |
| interpeer | plugins/interpeer | 0.1.0 | active | yes | n/a |
| interphase | plugins/interphase | 0.3.3 | active | yes | 4 |
| interpub | plugins/interpub | 0.1.3 | active | yes | 4 |
| intersearch | plugins/intersearch | 0.1.1 | active | yes | 4 |
| interserve | plugins/interserve | 0.1.4 | active | yes | 4 |
| interslack | plugins/interslack | 0.1.0 | active | yes | 4 |
| interstat | plugins/interstat | 0.2.5 | active | yes | 4 |
| intersynth | plugins/intersynth | 0.1.3 | active | yes | n/a |
| intertest | plugins/intertest | 0.1.1 | active | yes | n/a |
| interverse | root | — | active | yes | n/a |
| interwatch | plugins/interwatch | 0.1.2 | active | yes | 4 |
| tldr-swinton | plugins/tldr-swinton | 0.7.14 | active | yes | 15 |
| tool-time | plugins/tool-time | 0.3.5 | active | yes | 12 |
| tuivision | plugins/tuivision | 0.1.4 | active | yes | 4 |

**Legend:** active = recent commits or active tracker items; early = manifest exists but roadmap maturity is limited. `n/a` means there is no module-local `.beads` database.

---

## Roadmap

### Now (P0-P1)

No P0-P1 items.

**Recently completed:** iv-yiq9 (Trim CLAUDE.md cc/claude-user documentation), iv-4eau (Default subagents to Haiku/Sonnet (economy model routing)), iv-udyq (Consolidate wildcard hooks (tool-time + hookify)), iv-bdbg (Cache interserve codex_query results), iv-puiu (Audit and uninstall unused plugins), iv-eqql (Disable Serena file I/O and think_about_* tools), iv-1mq4 (Narrow intercheck PostToolUse matcher), iv-6an0 (Fix TOCTOU bugs: non-atomic gate check + missing CAS guard), iv-ibdc (Fix non-atomic gate check in phase/machine.go (wrap evaluateGate+UpdatePhase in BeginTx)), iv-mokx (Fix missing CAS guard on dispatch UpdateStatus (add AND status=? to WHERE)), iv-erb1 (Deduplicate CLAUDE_SESSION_ID env writes), iv-mew5 (Register or remove interserve pre-read-intercept.sh), iv-iu31 (Remove tool-time PreToolUse binding, extract Task redirect to clavain), iv-juzy (Fix interflux hooks.json schema), iv-mctg (Add matcher to intercheck context-monitor.sh), iv-h7e2 (F2: Define integration.json schema + interbase-stub.sh template), iv-2lfb (F1: Build infra/interbase/ — centralized interbase.sh SDK), iv-gcu2 (Dual-mode plugin architecture — interbase SDK + integration manifest), iv-byh3 (Define platform kernel + lifecycle UX architecture), iv-7o7n (Document slicing for flux-drive agents (P0 token optimization))

### Next (P2)

**Interspect Routing Overrides**
- [interspect] **iv-r6mf** F1: routing-overrides.json schema + flux-drive reader
- [interspect] **iv-8fgu** F2: routing-eligible pattern detection + propose flow
- [interspect] **iv-gkj9** F3: apply override + canary + git commit
- [interspect] **iv-2o6c** F4: status display + revert for routing overrides
- [interspect] **iv-6liz** F5: manual routing override support
- [interspect] **iv-5su3** Autonomous mode flag
- [interspect] **iv-c2b4** /interspect:disable command
- [interspect] **iv-g0to** /interspect:reset command

**Interspect Safety & Evaluation**
- [interspect] **iv-88yg** Structured commit message format
- [interspect] **iv-003t** Global modification rate limiter
- [interspect] **iv-0fi2** Circuit breaker
- [interspect] **iv-drgo** Privilege separation (proposer/applier)
- [interspect] **iv-bj0w** Conflict detection
- [interspect] **iv-435u** Counterfactual shadow evaluation
- [interspect] **iv-izth** Eval corpus construction
- [interspect] **iv-rafa** Meta-learning loop
- [interspect] **iv-t1m4** Prompt tuning (Type 3) overlay-based
- [interspect] **iv-m6cd** Session-start summary injection

**Intercore Event-Driven Advancement**
- [intercore] **iv-otvb** F1: Schema + Store — phase_actions table (v14 migration)
- [intercore] **iv-qjm3** F2: CLI — ic run action subcommands (add/list/update/delete)
- [intercore] **iv-z5pc** F3: Resolution — template variables in ic run advance output
- [intercore] **iv-pipe** F4: Bash integration — sprint skill consumes kernel actions
- [intercore] **iv-14g9** TOCTOU prevention: phased dispatch coordination
- [clavain] **iv-r9j2** A3: Event-driven advancement — phase transitions trigger auto-dispatch

**Clavain Orchestration & Fleet**
- [clavain] **iv-asfy** C1: Agency specs — declarative per-stage agent/model/tool config
- [clavain] **iv-lx00** C2: Agent fleet registry — capability + cost profiles per agent×model
- [clavain/interphase] **iv-zsio** Integrate full discovery pipeline into sprint workflow
- [clavain] **iv-frqh** F5: clavain:setup modpack — auto-install ecosystem-only plugins
- [clavain] **iv-zyym** Evaluate Claude Hub for event-driven GitHub agent dispatch

**Multi-Agent Coordination & Interlock**
- [interlock] **iv-gg8v** F2: Auto-Release on Clean Files
- [interlock] **iv-5ijt** F3: Structured negotiate_release MCP Tool
- [interlock] **iv-6u3s** F4: Sprint Scan Release Visibility
- [interlock] **iv-2jtj** F5: Escalation Timeout for Unresponsive Agents
- [intermute] **iv-ev4o** Agent capability discovery via intermute registration
- [intermute] **iv-jc4j** Heterogeneous agent routing experiments (SC-MAS/Dr. MAS)
- [intermute] **iv-quk4** Hierarchical dispatch: meta-agent for N-agent fan-out

**Flux-Drive Evolution & Review Intelligence**
- [flux-drive-spec] **iv-ia66** Phase 2: Extract domain detection library
- [flux-drive-spec] **iv-0etu** Phase 3: Extract scoring/synthesis Python library
- [flux-drive-spec] **iv-e8dg** Phase 4: Migrate Clavain to consume the library
- [interflux] **iv-wz3j** Role-aware latent memory architecture experiments
- [interflux] **iv-qjwz** AgentDropout: dynamic redundancy elimination for flux-drive reviews
- [interflux] **iv-905u** Intermediate result sharing between parallel flux-drive agents
- [interflux] **iv-6ikc** Plan intershift extraction (cross-AI dispatch engine)
- [interflux] **iv-sdqv** Plan interscribe extraction (knowledge compounding)

**Token Efficiency & Benchmarks**
- [interstat] **iv-0lt** Extract cache_hints metrics in score_tokens.py
- [interstat] **iv-1gb** Add cache-friendly format queries to regression_suite.json
- [interstat] **iv-4728** Consolidate upstream-check.sh API calls (24 to 12)
- [interstat] **iv-3w1x** Split upstreams.json into config + state files
- [interstat] **iv-v81k** Repository-aware benchmark expansion for agent coding tasks
- [intercache] **iv-p4qq** Smart semantic caching across sessions
- [intercache] **iv-xuec** Security threat model for token optimization techniques

**Autarch TUI & Memory Promotion**
- [autarch] **iv-26pj** Streaming buffer / history split per agent panel
- [autarch] **iv-ht1l** Pollard: progressive result reveal per hunter
- [autarch] **iv-xlpg** Pollard: optional-death hunter resilience
- [intermem] **iv-f7po** F3: Multi-file tiered promotion — AGENTS.md index + docs/intermem/ detail
- [intermem] **iv-bn4j** F4: One-shot tiered migration — --migrate-to-tiered

**Research & Futures**
- [research] **iv-3kee** Research: product-native agent orchestration (whitespace opportunity)
- [research] **iv-dthn** Research: inter-layer feedback loops and optimization thresholds
- [research] **iv-fzrn** Research: multi-agent hallucination cascades & failure taxonomy
- [research] **iv-exos** Research: bias-aware product decision framework
- [research] **iv-jk7q** Research: cognitive load budgets & progressive disclosure review UX

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
- [intercore] **iv-1et1** Document current CLI surface for interspect/compat commands
- [interverse] **iv-1n6z** Monorepo build orchestrator (interbuild) with change detection
- [clavain] **iv-1vny** C4: Cross-phase handoff protocol — structured output-to-input contracts (blocked by iv-asfy)
- [interject] **iv-1x2n** Redacta: Elevating Video Content with GitHub Copilot CLI - DEV Community
- [autarch] **iv-1yck** Bigend: htop-style cost + tool columns per agent
- [interject] **iv-22w** Discover and install prebuilt plugins through marketplaces - Claude Code Docs
- [clavain] **iv-240m** C3: Composer — match agency specs to fleet registry within budget (blocked by iv-asfy, iv-lx00)

---

## Module Highlights

### clavain (hub/clavain)
Clavain is an autonomous software agency — 15 skills, 4 agents, 52 commands, 22 hooks, 1 MCP server. 31 companion plugins in the inter-* constellation. 1000 beads tracked, 660 closed, 339 open. Runs on its own TUI (Autarch), backed by Intercore kernel and Interspect profiler.

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
v0.4.3. Bidirectional sync between local filesystems and Notion with three-way merge conflict resolution and crash-safe WAL recovery. Exposes 21 MCP tools for hierarchy discovery, raw signal gathering, and sync control — delegating classification and tagging to agent skills rather than hardcoding behavior.

---

## Research Agenda

- **Lens-driven agent review (linsenkasten)** — FLUX podcast cognitive augmentation lenses for agent evaluation, MCP integration, severity classification, and phase-specific agent selection
- **Sprint resilience and kernel handoff** — Resume tracking, fault tolerance, multi-layer rollback recovery, and bidirectional bead-kernel sync to migrate sprint state to intercore kernel
- **Token efficiency and cost-aware dispatch** — Lazy skill loading, token budget controls per sprint, dispatch cost tracking, and write-behind for subagent context results
- **Document slicing and context compression** — Per-agent section filtering via interserve, import-graph compression, block compression, precomputed context bundles, and symbol-popularity indexing
- **Intercore kernel evolution (E3-E8)** — Hook cutover for sprint state, spawn handler wiring, discovery pipeline for kernel-native research intake, and portfolio orchestration across projects
- **Multi-session agent coordination** — Merge review for multi-agent sessions, hierarchical dispatch meta-agent, session-start drift summary injection, and autonomous sync mechanics
- **Plugin ecosystem and synergy** — Dual-mode architecture (standalone + integrated), cross-plugin interoperability catalog, plugin-synergy discovery, and unified interbus central integration mesh
- **Portfolio and dependency scheduling** — Cross-project portfolio runs with parent-child linking, dependency-aware phase scheduling, TOCTOU guards, and portfolio relay patterns
- **Dashboard and visualization** — Bigend TUI kernel state migration, autarch status tool validation, interchart D3 force graph ecosystem diagram, and tui-kernel validation patterns
- **Event-driven phase advancement** — Automatic phase transition dispatch, event-driven run progression, terminal status exhaustiveness, and gate check flow
- **Thematic sprint organization** — Label-based work lanes for sequencing, shift-work boundary formalization, blueprint distillation sprint intake, and role-aware memory experiments
- **Framework and context optimization** — Multi-framework interoperability benchmarking, repository-aware benchmark expansion, context freshness automation via interwatch, and reminder escalation patterns
- **Advanced state management** — Hierarchical config resolution for model routing, static routing tables, drift detection summaries, and bias-aware product decision frameworks
- **Code extraction and tools** — Interscribe symbol extraction, structured output serialization, longcodezip block compression, and advanced TUI automation with tuivision patterns

---

## Cross-Module Dependencies

Major dependency chains spanning multiple modules:

- **iv-wz3j** (interflux) blocked by **iv-jc4j** (intermute)
- **iv-3r6q** (interflux) blocked by **iv-r6mf** (interspect)
- **iv-5pvo** (intercore) blocked by **iv-ev4o** (interverse)

---

## Modules Without Roadmaps

- `plugins/interchart`
- `plugins/interlearn`

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
