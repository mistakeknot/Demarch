# Research Agenda Synthesis — Brainstorm + Plan Files

**Date:** 2026-02-20
**Purpose:** Synthesize 17 brainstorm files and 20+ plan files into thematic research bullets for the research agenda.

---

## Source Coverage

### Brainstorm files analyzed
- linsenkasten-flux-agents (2026-02-15)
- multi-session-phase4-merge-agent (2026-02-15)
- sprint-resilience (2026-02-15)
- token-efficient-skill-loading (2026-02-15)
- agent-rig-autonomous-sync (2026-02-16)
- flux-drive-document-slicing (2026-02-16)
- interbus-central-integration-mesh (2026-02-16)
- linsenkasten-phase1-agents (2026-02-16)
- sprint-resilience-phase2 (2026-02-16)
- subagent-context-flooding (2026-02-16)
- token-budget-controls (2026-02-16)
- intercore-e3-hook-cutover (2026-02-19)
- reflect-phase-learning-loop (2026-02-19)
- autarch-status-tool (2026-02-20)
- cost-aware-agent-scheduling (2026-02-20)
- intercore-rollback-recovery (2026-02-20)
- sprint-handover-kernel-driven (2026-02-20)

### Plan files analyzed
- cross-module-integration-opportunities
- framework-benchmark-freshness-automation
- heterogeneous-collaboration-routing
- interband-sideband-hardening
- multi-framework-interoperability-benchmark
- repository-aware-benchmark-expansion
- role-aware-latent-memory-experiments
- bias-aware-product-decision-framework
- blueprint-distillation-sprint-intake
- catalog-reminder-interwatch-escalation
- hierarchical-dispatch-meta-agent
- interscribe-extraction-plan
- session-start-drift-summary-injection
- shift-work-boundary-formalization
- tldrs-import-graph-compression-dedup
- tldrs-longcodezip-block-compression
- tldrs-precomputed-context-bundles
- tldrs-structured-output-serialization
- tldrs-symbol-popularity-index
- reflect-phase-sprint-integration

---

## Thematic Groupings

### Theme 1: Token Efficiency — Skill Loading and Document Routing

**Sources:** token-efficient-skill-loading (brainstorm), flux-drive-document-slicing (brainstorm), tldrs-longcodezip-block-compression (plan), tldrs-import-graph-compression-dedup (plan), tldrs-precomputed-context-bundles (plan), tldrs-symbol-popularity-index (plan), tldrs-structured-output-serialization (plan), blueprint-distillation-sprint-intake (plan)

These all share the same core problem: reducing the token cost of providing context to LLM agents. Each attacks a different layer:
- Skill loading: 60-70% of tokens in inter-* skills are ceremony (reading instructions), not work (doing the thing). Solution: SKILL-compact.md files + pre-computation scripts.
- Document slicing: flux-drive sends full documents to all agents (75K tokens for 5-agent review). Per-agent content routing via Interserve spark classification reduces this 50-70%.
- tldrs compression: within-function block compression via LongCodeZip preserves high-value blocks under budget pressure; import graph deduplication removes redundant transitive imports; precomputed bundles eliminate cold-start latency; symbol popularity index guides pruning decisions.
- Blueprint distillation: compress high-entropy brainstorm/PRD docs into structured, execution-ready constraint schemas before sprint intake to reduce plan-phase context bloat.

### Theme 2: Token Budget Enforcement and Cost-Aware Dispatch

**Sources:** token-budget-controls (brainstorm), cost-aware-agent-scheduling (brainstorm), heterogeneous-collaboration-routing (plan)

These address the budget-enforcement layer. Current state: flux-drive dispatches agents purely on relevance scores with no budget awareness; intercore's budget algebra exists but is dead-lettered; interstat measurement is batch-only (NULLs during live sessions).

Proposed approach (Variant D/hybrid): sprint creation accepts --token-budget parameter; sprint_advance() checks cumulative estimated cost against budget before each phase; flux-drive receives FLUX_BUDGET_REMAINING env var and applies existing triage cut logic; post-phase token writeback feeds AggregateTokens() for subsequent checks. Key distinctions: billing_tokens (input+output) for budget caps vs effective_context (includes cache) for window checks.

Heterogeneous routing extends this by labeling tasks (routine/risky/high-complexity/recovery-needed) and dispatching to cost-appropriate agents via policy engine (homogeneous, cost-first, quality-first).

### Theme 3: Sprint Lifecycle Resilience, Continuity, and Recovery

**Sources:** sprint-resilience (brainstorm), sprint-resilience-phase2 (brainstorm), intercore-rollback-recovery (brainstorm)

These address sprint workflow fragility from three angles:
- Phase continuity: CLAVAIN_BEAD_ID is in-memory only; session restarts lose context. Solution: sprint bead as source of truth with parent-child bead hierarchy; session-start hook injects resume hints.
- Autonomy: too many confirmation prompts at non-critical moments. Solution: auto-advance by default, pause only for design ambiguity, gate failures, test failures, or user-set breakpoints.
- Rollback: phase transitions are forward-only. Solution: three-layer rollback — (1) workflow state rewind (marking intervening artifacts/dispatches as rolled_back), (2) code rollback query (dispatch metadata → commit SHAs and file paths for VCS-agnostic revert planning), (3) discovery/backlog rollback (deferred to E5).

### Theme 4: Intercore Kernel Migration and Sprint Handover

**Sources:** intercore-e3-hook-cutover (brainstorm), sprint-handover-kernel-driven (brainstorm)

These are sequential migration milestones in the Clavain autonomy ladder:
- E3 (Hook Cutover): big-bang migration of sprint state from beads-backed temp files to intercore ic run. Custom 8-phase chain: brainstorm → brainstorm-reviewed → strategized → planned → plan-reviewed → executing → shipping → done. Six workstreams: lib-sprint.sh rewrite, sentinel cleanup, session state switch, event reactor, agent tracking, gate integration.
- A2 (Sprint Handover): post-E3 cleanup — delete ~600 lines of beads fallback code, make ic availability a hard requirement for sprint operations, cache run ID once per session (eliminating per-call bd state lookups), delete shell transition table (ic stores the chain). Identity model clarified: bead = user-facing handle, ic run = internal execution state.

### Theme 5: Reflect Phase and Learning Loop

**Sources:** reflect-phase-learning-loop (brainstorm), reflect-phase-sprint-integration (plan)

Clavain's sprint lifecycle currently ends at "done" with no mandatory learning capture step. The /compound skill exists but is manually invoked and easy to skip. The reflect phase adds a mandatory 10th phase (after polish, before done) that gates sprint completion on at least one learning artifact (docs/solutions/ entry, auto-memory update, skill improvement commit, or complexity calibration note). Gate scales with complexity: C1 = any one-liner note, C3 = full solution doc. Implementation requires intercore DefaultPhaseChain update + Clavain transition table + sprint_next_step() mapping.

### Theme 6: Subagent Context Flooding and Verdict Protocol

**Sources:** subagent-context-flooding (brainstorm)

When flux-drive dispatches 6-8 agents and each returns 3-5K tokens, the orchestrator loses ~30K tokens reading output. Quality-gates and review are worse — results come inline through TaskOutput. Fix: wire the already-existing lib-verdict.sh infrastructure (verdict_write, verdict_parse_all, verdict_get_attention) into flux-drive, flux-research, quality-gates, and review. Each agent writes full findings to disk; the orchestrator reads 1-line verdict summaries (~5 tokens/agent) and only drills into NEEDS_ATTENTION detail files. This pattern exists in shared-contracts.md and flux-drive's launch phase; it needs extension to quality-gates and review.

Related: hierarchical-dispatch-meta-agent (plan) extends this with a full meta-agent fan-out pattern where the parent launches one meta-agent that dispatches workers internally and returns a single synthesis result to the parent, further limiting parent context growth.

### Theme 7: Autarch Status Tool and Kernel Observability

**Sources:** autarch-status-tool (brainstorm)

Minimal TUI to answer "what's running right now?" by reading intercore kernel state exclusively via ic CLI — no filesystem scanning, no tmux scraping. Three-pane layout: active runs with phase progress bars, dispatches per selected run, and a live event stream. Architecture: standalone binary (cmd/status/main.go) using pkg/tui styles. Polling at 3s default with follow mode for event streaming. Validates the kernel API surface is sufficient for TUI rendering before the full Bigend migration.

### Theme 8: Agent Rig Autonomous Sync

**Sources:** agent-rig-autonomous-sync (brainstorm)

The Interverse ecosystem has grown to 25+ plugins but agent-rig.json lists only 17, with interflux (the review engine) completely absent. Solution: generated + self-healing hybrid. agent-rig.json is the single source of truth; a generator script produces plugin lists in setup.md and doctor.md from it; setup.md includes a self-heal instruction for runtime fallback when lists drift. Generator runs in Clavain's post-bump.sh hook. Tier classification: required/recommended/optional/infrastructure. Drift detector warns when marketplace plugins aren't in any tier.

### Theme 9: Interbus Event Mesh for Cross-Module Integration

**Sources:** interbus-central-integration-mesh (brainstorm), cross-module-integration-opportunities (plan), interband-sideband-hardening (plan), catalog-reminder-interwatch-escalation (plan), session-start-drift-summary-injection (plan)

These cluster around making inter-module communication structured and observable rather than implicit:
- Interbus: lightweight integration mesh with intent envelope schema (event_id, intent, context_id, artifact_path, severity, producer/consumers). First implementation as a bash shim in os/clavain/hooks; Go/Python backend only if volume warrants. Core intents: discover_work, start_sprint, phase_transition, review_pass.
- Interband sideband hardening: protocol validation for known message types; multi-path loader discovery; fail-open behavior when interband is unavailable.
- Catalog-reminder → Interwatch: catalog-reminder.sh emits component_count_changed signal when component shape changes; Interwatch consumes it without waiting for a full manual watch cycle.
- Session-start drift injection: session-start.sh reads .interwatch/drift.json and injects a compact summary into session context when severity is Medium+.

### Theme 10: Lens-Based Flux-Drive Agents (Interlens)

**Sources:** linsenkasten-flux-agents (brainstorm), linsenkasten-phase1-agents (brainstorm)

Consolidate Interlens's 288 analytical lenses across 28 thematic frames into 5 flux-drive agents that review strategy documents for thinking quality rather than code correctness. Proposed agents: fd-lens-systems, fd-lens-decisions, fd-lens-people, fd-lens-resilience, fd-lens-perception. Phase 0 shipped fd-systems; Phase 1 (F1b) creates the remaining 4 agents. Architecture decision: agent files define analytical mission; Interlens MCP tools provide specific lenses on demand (graceful fallback to hardcoded subset when MCP unavailable). Severity system: Blind Spot (P1) / Missed Lens (P2) / Consider Also (P3). Deduplication handled in synthesis phase.

### Theme 11: Multi-Agent Coordination and Merge Protocol

**Sources:** multi-session-phase4-merge-agent (brainstorm)

After Phases 1-3 of interlock multi-session coordination (reservation system, blocking edit hook, auto-pull), the remaining gap is not conflict resolution but clean file handoff. Reservation negotiation protocol: Agent B sends request_release with priority+reason; Agent A's pre-edit hook evaluates urgency and either releases or replies with ETA. Protocol messages: request_release, release_ack, release_defer, release_escalate. Merge agent (for actual textual conflicts) is escalation path only, not the common path. The negotiate_release MCP tool already exists in interlock; this wires up the response side.

### Theme 12: Framework Benchmarking and Freshness Automation

**Sources:** multi-framework-interoperability-benchmark (plan), framework-benchmark-freshness-automation (plan), repository-aware-benchmark-expansion (plan)

Three related research programs:
- Multi-framework interoperability benchmark: runnable harness comparing ADK, LangGraph, AutoGen, agno, smolagents, CrewAI, SWE-agent on a 25+ task corpus. Common RunResult struct. Weekly CI smoke suite (5 tasks, <15 min). Outputs recommendation matrix for interflux/clavain routing defaults.
- Framework freshness automation: interwatch pollers for framework release tags and arXiv search terms; impact scoring for API breaks vs performance claims; auto-create review beads with priority mapping.
- Repository-aware benchmark expansion: (referenced but not read in full — assumed to extend corpus with repo-specific tasks)

### Theme 13: Role-Aware Memory and Bias-Aware Decision Gates

**Sources:** role-aware-latent-memory-experiments (plan), bias-aware-product-decision-framework (plan)

Two research programs addressing LLM judgment quality:
- Role-aware memory: define memory profiles (ephemeral/local/project-long) with role labels (planner, executor, reviewer, verifier); namespace isolation with TTL and purge APIs; audit hooks for cross-role leakage prevention; benchmark with intentional contamination probes.
- Bias-aware product decisions: taxonomy of biases relevant to Clavain product workflows (position, verbosity, authority, anchoring, framing, omission, status quo); map to brainstorm/strategy/planning decisions; define gate/escalation protocol using multi-judge structure and confidence rubric.

### Theme 14: Shift-Work Boundary and Sprint Intake Quality

**Sources:** shift-work-boundary-formalization (plan), blueprint-distillation-sprint-intake (plan)

These address the transition from interactive planning to autonomous execution:
- Shift-work boundary: define explicit entry conditions for autonomous mode (plan completeness, tests/scenarios, acceptance criteria); structured completeness gate; pause/resume controls with batch ceiling and commit cadence guardrails.
- Blueprint distillation: adds a distillation step in sprint intake to compress brainstorm/PRD docs into structured execution-ready constraint schemas (constraints, invariants, must-not-breaks, validation hooks) before planning.

### Theme 15: Interscribe Knowledge Compounding Extraction

**Sources:** interscribe-extraction-plan (plan)

Plan to extract Clavain's compounding assets (skills, commands, hooks, research agents) into a standalone `interscribe` companion plugin. Milestones: source inventory → boundary definition → phased migration (scaffold, dual-run bridge, cutover, cleanup) → compatibility shims and deprecation messaging. Goal: separate the knowledge-compounding concern from the sprint orchestration core.

---

## Synthesized Research Bullets

- **Sprint Lifecycle Resilience** — Unified redesign of sprint continuity (bead-first state, auto-advance autonomy, and three-layer rollback) to eliminate fragile env-var state and forward-only phase transitions.
- **Intercore Kernel Migration** — Big-bang cutover of sprint state from beads to intercore ic run (E3), followed by fallback code deletion and single-identity model (A2) to reduce the sprint codebase by ~600 lines.
- **Token Efficiency: Skill Loading and Document Routing** — Reduce per-invocation ceremony tokens 60-70% via SKILL-compact.md files, pre-computation scripts, and per-agent document slicing using Interserve spark classification.
- **Token Efficiency: Context Compression** — Cut tldrs context costs via within-function block compression (LongCodeZip), import-graph deduplication, precomputed workspace bundles, and symbol popularity-guided pruning.
- **Subagent Context Flooding** — Wire existing lib-verdict.sh verdict protocol into flux-drive, quality-gates, and review to replace inline TaskOutput flooding with 5-token verdict summaries and selective drill-down.
- **Cost-Aware Agent Scheduling** — Connect sprint budget parameters to flux-drive triage and intercore budget algebra via phase-granularity token writeback, enabling soft budget enforcement without real-time JSONL parsing.
- **Reflect Phase and Learning Loop** — Add a mandatory reflect phase to the sprint lifecycle (after polish, before done) gated on at least one learning artifact, closing the recursive self-improvement loop described in the Interverse vision.
- **Lens-Based Cognitive Review Agents** — Create 5 fd-lens-* flux-drive agents (systems, decisions, people, resilience, perception) that review strategy documents for thinking quality, backed by Interlens MCP tools for dynamic lens retrieval.
- **Agent Rig Autonomous Sync** — Generate setup.md and doctor.md plugin lists from agent-rig.json as single source of truth, with a self-heal runtime fallback and marketplace drift detection triggered on every version bump.
- **Interbus Event Mesh** — Introduce a lightweight intent-envelope integration layer standardizing cross-module communication (discover_work, phase_transition, review_pass), enabling observability and reducing brittle direct chaining.
- **Autarch Status Tool** — Build a minimal TUI reading intercore kernel state via ic CLI to validate the kernel API surface and provide real-time "what's running?" visibility before the full Bigend migration.
- **Multi-Agent File Coordination** — Complete interlock Phase 4 with a reservation negotiation protocol (request_release/release_ack/release_defer) to enable clean file handoff without merge-agent overhead.
- **Framework Benchmarking Ecosystem** — Build a runnable multi-framework benchmark harness (ADK, LangGraph, AutoGen, etc.) with freshness automation and repository-aware corpus expansion to inform interflux routing defaults.
- **Role-Aware Memory and Bias Gates** — Prototype role-scoped memory namespaces (planner/executor/reviewer) with leakage prevention, and design a bias-aware decision framework for escalating high-risk LLM product judgments.
- **Sprint Intake Quality and Knowledge Extraction** — Compress brainstorm inputs into structured blueprint artifacts before planning (reducing plan-phase context noise), and extract Clavain's compounding assets into a standalone interscribe plugin.
