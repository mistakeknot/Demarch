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

**Intermem & Intercore: Memory, Storage & Discovery**
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
