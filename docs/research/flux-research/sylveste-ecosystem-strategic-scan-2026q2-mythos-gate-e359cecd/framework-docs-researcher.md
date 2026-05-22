---
date: 2026-05-22
agent: framework-docs-researcher (host-supplemented; agent failed web access)
target: Big Lab agent SDK 2026-Q2 shipments and overlap with Sylveste
scope: Anthropic, OpenAI, Google, OSS, Standards
note: "Original agent invocation returned no findings (web tools unavailable in its environment). Host (claude) re-ran the scan via WebSearch + WebFetch. Sources cited."
---

# Big Lab Agent SDK Roadmap Signals — 2026-Q2

What shipped between 2026-03-01 and 2026-05-22 across the major agent platforms, and what each shipment means for the Sylveste subsystem it overlaps. Source citations at end of each section.

## 1. Anthropic — Claude Code & Claude Agent SDK

**Shipments verified in the SDK CHANGELOG:**

- **Task tools replace TodoWrite (v0.2.142+, Q1→Q2 2026 rollout).** `TaskCreate / TaskUpdate / TaskGet / TaskList` — a first-class task model with stable IDs, accumulation semantics, and exported types. (Sylveste-internal note: this is the harness-level system reminders that nag Claude every session. Beads is our durable alternative.)
- **`forkSession` + session metadata (`tag`, `createdAt`, `renameSession`, `tagSession`, paginated `listSessions`) — v0.2.76+.** First-class session branching and labeling, with `sessionStore` (alpha) for mirroring transcripts to external storage. Direct overlap with Sylveste's session lifecycle and intermux/intermute tracking.
- **`ConfigChange`, `TeammateIdle`, `TaskCompleted` hook events — v0.2.49+.** Multi-agent coordination primitives are now first-class in the SDK; the hook system surfaces teammate idle states. This is what intermux/interlock has been building bottom-up.
- **MCP non-blocking startup + `alwaysLoad: true` per-server flag — v0.2.142+.** MCP servers connect in background; sessions start immediately; slow servers report `status: "pending"`. Speeds session start, which is exactly what `sylveste-z55b` (SessionStart refactor) is targeting.
- **`agentProgressSummaries` (AI-generated progress for running subagents) — v0.2.72+.** Periodic summaries emitted on `task_progress`. Overlaps with what interspect/interject would observe from sub-agent telemetry.
- **`startup()` pre-warm + `bun build --compile` support — v0.2.89+, v0.3.144.** First-query latency 20× faster when startup cost is amortized.
- **`resolveSettings()` (alpha) — v0.2.136+.** Inspect merged settings without spawning the CLI; reads MDM (plist/HKLM/HKCU). Useful for Sylveste's doctor.
- **OpenTelemetry trace context propagation — v0.2.113+.** Caller's active trace context forwards to the CLI subprocess; spans nest under distributed trace. Confirms OTEL is the cross-vendor instrumentation lingua franca.
- **`Bun` and Claude Code v2.1.69 → 2.1.101+ in five weeks (April 2026)** — Opus 4.6 1M context rollout, flicker-free rendering.

**Plugin & Skills:**
- `reloadPlugins()`, plugin dependency enforcement (disable refuses dependents; enable force-enables transitive deps), `claude plugin validate` skills directory check.
- `skills` option (`string[] | 'all'`) on the SDK to control which Skills load into the main session.
- `user-invocable: false` Skills correctly excluded from `supportedCommands()`.

**Overlap with Sylveste subsystems:**

| Anthropic ship | Sylveste subsystem | Verdict |
|---|---|---|
| Task tools (`TaskCreate/Update/Get/List`) | Beads | **Keep beads.** Beads has Dolt-backed history, cross-session continuity, parent/child relationships, and no harness-only lifetime. Task tools are session-local. Beads stays. |
| `forkSession` + session metadata | intermux/intermute, Clavain session lifecycle | **Adopt-partial.** Migrate to native session APIs where possible; keep coordination semantics. |
| `ConfigChange/TeammateIdle/TaskCompleted` hooks | interlock, intermute | **Adopt.** This is what we've been building. Switch to the native hook events. |
| MCP non-blocking + `alwaysLoad` | Clavain SessionStart | **Adopt.** Directly satisfies `sylveste-z55b` and reduces hook health budget. |
| `agentProgressSummaries` | interspect evidence | **Adopt-partial.** Augment Interspect with these summaries; don't replace structured evidence. |
| OTEL context propagation | Interspect, interflux | **Adopt.** Emit OTEL alongside Dolt rows. Validates best-practices-researcher's "inspire-only" verdict — actually it's "adopt-now-for-cross-vendor". |

**Mythos-launch implications:** Opus 4.6 1M context already shipped April 2026. The next gen (Mythos) is expected to push tool-composition + long-horizon planning. Sylveste's bet on "many small composed plugins" remains correct, but more of the *plumbing* is now in the SDK — we need to consume it, not duplicate it.

Sources: [claude-agent-sdk-typescript CHANGELOG](https://github.com/anthropics/claude-agent-sdk-typescript/blob/main/CHANGELOG.md), [claude-code CHANGELOG](https://github.com/anthropics/claude-code/blob/main/CHANGELOG.md), [claude-code April 2026 changelog overview](https://help.apiyi.com/en/claude-code-changelog-2026-april-updates-en.html), [Anthropic April-23 postmortem](https://www.anthropic.com/engineering/april-23-postmortem)

---

## 2. OpenAI — Codex, Agents SDK, Responses API

**Shipments:**

- **OpenAI Agents SDK + Temporal integration: GA on 2026-03-23** (preview was July 2025). Each agent invocation = Temporal Activity; built-in retries, replay, deterministic recovery from crash. This is the production durable-execution story; LangGraph adoption is shrinking.
- **GPT-5.3-Codex on Responses API (Q2 2026).** Codex-class model usable directly via Responses API for agent flows.
- **Responses API: Skills support (local + hosted container), server-side compaction, WebSocket mode.** Skills now first-class in the API surface, not just in the Codex CLI.
- **Codex Goal Mode — stable across CLI, IDE, app.** Long-horizon execution targeting an objective; pause-on-blocker, pause-on-limit. This is "agent works for hours/days." Direct competitor to Clavain sprints.
- **Codex Remote Computer Use.** Operate desktop apps after device lock, including via Codex Mobile; short-lived auth + covered displays + relock-on-input safeguards.
- **`codex remote-control` daemon + Codex SDK in `openai-codex` package** — concurrent turn routing, approval modes, device-code auth.
- **`codex doctor`** — support-ready diagnostics across runtime/auth/terminal/network/config/local state. Sylveste-equivalent is `/clavain doctor`; direct overlap.
- **Agents SDK harness + sandbox update — April 2026.** Configurable memory, sandbox-aware orchestration, "Codex-like filesystem tools." Sandbox is now a first-class concern in the SDK, not bolt-on.
- **Assistants API deprecation in progress** — Responses API absorbs the feature set.

**Overlap with Sylveste subsystems:**

| OpenAI ship | Sylveste subsystem | Verdict |
|---|---|---|
| Agents SDK + Temporal GA | Intercore dispatch/runs | **Pivot consideration.** Intercore solves a subset of what Temporal+Agents SDK now solves. Best-practices-researcher flagged this. The honest call: Sylveste's value over Temporal+Agents is the evidence + trust ladder + plugin composition; not the durable execution itself. Adopt Temporal underneath Intercore, keep our policy layer on top. |
| Codex Goal Mode | Clavain sprints (brainstorm→strategy→plan→execute→review→ship) | **Defend.** Goal Mode is open-ended; Clavain's value is the *phased gate model* + receipts. Continue, but make sure sprint receipts are visibly better than Goal Mode's. |
| `codex doctor` | `/clavain doctor` | **Inspire-only.** Already overlapping; our checks are deeper. |
| Codex Remote Computer Use | Hassease + Hermes deploy | **Watch.** Codex Mobile + remote desktop = the kind of "agent works while you sleep" surface Sylveste Hassease is angling at. Don't compete on remote-desktop; differentiate on Signal/Telegram personality + evidence. |
| Responses API Skills | Clavain skills / interflux skills | **Direct overlap.** Skills are now a cross-vendor primitive. Sylveste skills need to be portable. |
| Server-side compaction | Lattice / interspect / Clavain context management | **Adopt-inspire.** Server-side compaction is part of Anthropic's plan too. The "Event Compaction" pattern is platform-wide. |

**Mythos-launch implications:** OpenAI's "Codex SDK + Agents SDK + Temporal" stack is now the most durable-execution-grade alternative to LangGraph/CrewAI. Sylveste must not look like "another LangGraph" — must be visibly the *evidence-flywheel + plugin-composition* play. The plumbing is increasingly cross-vendor; the *policy* is where Sylveste differentiates.

Sources: [OpenAI Responses API changelog](https://developers.openai.com/api/docs/changelog), [Codex changelog](https://developers.openai.com/codex/changelog), [OpenAI Agents SDK + Temporal GA blog](https://temporal.io/blog/announcing-openai-agents-sdk-integration), [Help Net Security on Agents SDK harness/sandbox](https://www.helpnetsecurity.com/2026/04/16/openai-agents-sdk-harness-and-sandbox-update/)

---

## 3. Google — Gemini ADK, A2A, Vertex Agent Engine

**Shipments:**

- **ADK 1.0 stable across Python/TypeScript/Go/Java (early 2026).** All four SDKs have identical feature parity at the protocol level.
- **A2A protocol now governed by Linux Foundation; 150+ orgs in production (May 2026).** Cross-vendor agent-to-agent messaging is now a Linux Foundation project with multi-vendor governance.
- **A2A v0.3+ upgrade: Tasks as first-class abstraction.** Client sends task, gets `task_id`, monitors via SSE. Long-running operations survive network disconnects. Token-by-token streaming.
- **ADK Event Compaction.** Sliding window of recent events + LLM-summarized state for older ones. Reported -38% token use, -18% latency in production benchmarks.
- **Vertex AI Agent Engine + Gemini Enterprise Agent Platform** — managed runtime for ADK/A2A agents on Cloud Run + Azure variants (App Service, ACA, Fabric).
- **Deprecated SDK module sunset 2026-06-24** — migration deadline.

**Overlap with Sylveste subsystems:**

| Google ship | Sylveste subsystem | Verdict |
|---|---|---|
| A2A protocol (Linux Foundation) | Inter-agent messaging (intermute/interlock) + intercom transport (`sylveste-2nfd`) | **Adopt-strongly.** This is the cross-vendor standard. Sylveste's transport abstraction (in design now) should target A2A natively. Don't invent a private protocol. |
| ADK 1.0 multi-language SDKs | Skaffen Go migration (`sylveste-benl`) | **Inspire-port.** Skaffen is Sylveste's Go port. ADK Go SDK is reference for what "Go agent SDK" looks like today. |
| Event Compaction | Lattice / interspect | **Adopt-inspire.** The pattern (sliding window + state summary) is what Sylveste should apply to long sessions. |
| Vertex Agent Engine | Hermes deploy + Hassease daemon | **Skip.** Google-managed runtime; Sylveste is OSS self-hosted. |

**Mythos-launch implications:** A2A is the single most important external standard for Sylveste. If we ship transport abstraction (`sylveste-2nfd`) targeting an arbitrary protocol shape, we miss the wave. If we target A2A, we get cross-vendor interop for free.

Sources: [Google ADK A2A docs](https://google.github.io/adk-docs/a2a/), [ADK Gemini Enterprise docs](https://docs.cloud.google.com/gemini-enterprise-agent-platform/build/adk), [ADK 1.0 + A2A multi-agent standard blog](https://explore.n1n.ai/blog/google-adk-1-0-a2a-protocol-multi-agent-standard-2026-05-04), [Agent2Agent upgrade blog](https://cloud.google.com/blog/products/ai-machine-learning/agent2agent-protocol-is-getting-an-upgrade)

---

## 4. OSS / Startup ecosystem

**Active and relevant:**

- **Temporal 1.0 (January 2026)** + **OpenAI Agents SDK integration GA (March 2026)**. $300M raise at $5B valuation Feb 17, 2026. 9.1T cumulative actions; 1.86T from AI-native companies. This is now the production durable-execution backbone.
- **Restate launched commercially March 2026.** Temporal alternative; lighter-weight; explicit state machines for agents.
- **Inngest Temporal-compatible workflows (February 2026).** Event-driven durable execution.
- **Langfuse acquired by ClickHouse (January 2026).** OSS-first eval/observability platform unchanged in stewardship; remains self-hosted-friendly. Best self-hosted option for agent eval at production scale.
- **Braintrust** — eval-first, commercial. SOC 2 cloud; enterprise hybrid self-host. CI/CD-friendly with eval gates that auto-block merges on quality regression.
- **Laminar / Latitude / MLflow** — emerging agent observability players. Latitude differentiates on agent-first (multi-turn, GEPA auto-generation, issue lifecycle, MCC eval quality).
- **Pydantic AI + Logfire**, **Mastra**, **smolagents (HF)**, **Llama Stack**, **Goose (Block)**, **LangGraph Cloud**, **Inngest Agent Kit**, **Agno** — all converging on durable-execution + explicit-state patterns.

**Gartner 2026 AI Ops report:** 89% of multi-agent deployments that started with ≥3 agents converged to a single agent with more tools by production. (Signal: multi-agent is more expensive than expected; tools beat agents for many real workloads.)

**Overlap with Sylveste subsystems:**

| OSS ship | Sylveste subsystem | Verdict |
|---|---|---|
| Temporal | Intercore dispatch/runs | **Adopt as substrate** (best-practices-researcher concurs). Keep Sylveste's policy layer on top. |
| Langfuse self-hosted | Interspect evidence + Interstat metrics | **Adopt.** Adopt as eval backend; Sylveste keeps the evidence/calibration policy. Stop building parallel eval in-house. |
| Restate / Inngest | Alternative durable-exec | **Inspire.** Temporal is the leader; only consider alternatives if Temporal licensing turns hostile. |
| LangGraph (declining) | n/a | **Skip / avoid.** Industry is migrating off. |
| 89% multi→single agent convergence | interflux multi-track review | **Re-examine.** Sylveste's bet is multi-agent *review* (parallel-then-synthesize), which is different from multi-agent *execution*. Review benefits from diversity. Execution apparently doesn't. Sharpen the distinction in docs. |

Sources: [Temporal blog](https://temporal.io/blog/announcing-openai-agents-sdk-integration), [Inngest durable-exec blog](https://www.inngest.com/blog/durable-execution-key-to-harnessing-ai-agents), [Langfuse alternatives 2026](https://www.braintrust.dev/articles/langfuse-alternatives-2026), [Laminar top 6 agent observability platforms](https://laminar.sh/article/2026-04-23-top-6-agent-observability-platforms), [State machines vs prompts](https://blogs.subhanshumg.com/stop-building-agents-like-prompts-build-them-like-state-machines), [Latitude agent eval comparison](https://latitude.so/blog/best-ai-agent-evaluation-platforms-2026-comprehensive-comparison)

---

## 5. Standards & Protocols

- **MCP under Linux Foundation governance since December 2025; v2.1 Streamable HTTP transport (95% latency reduction vs. older versions).** 10,000+ active MCP servers; 500+ public; 97M monthly SDK downloads. Anthropic, OpenAI, Google DeepMind all support MCP.
- **MCP OAuth 2.x Resource Indicators (RFC 8707).** MCP clients now required to use resource indicators; tokens scoped to specific server. This is **the** capability-scoping primitive Sylveste should adopt for the Gridfire v1 spec — it's already an industry standard.
- **A2A protocol (Linux Foundation, 150+ orgs).** See Google section. Cross-vendor agent-to-agent transport.
- **OpenTelemetry agent conventions: pre-RFC.** OTEL Agent Tracing SIG (~40 participants) exploring conventions but nothing stable. Best-practices-researcher's "inspire-only" verdict holds: emit OTEL alongside Dolt, but don't gate Mythos on conventions stabilizing.
- **OpenInference (Arize), AGNTCY, Model Spec attestations** — various attestation-and-evidence proposals; none yet standardized.

**Verdict on standards stack for Sylveste:**

| Standard | Maturity | Sylveste action |
|---|---|---|
| MCP v2.1 + Streamable HTTP | Production | **Adopt.** Already wide; many Sylveste plugins already MCP servers. |
| MCP OAuth Resource Indicators | Production-required | **Adopt for Gridfire v1.** This *is* capability-scoped tokens, ready-made. |
| A2A (Linux Foundation) | Production (150+ orgs) | **Target with `sylveste-2nfd` transport abstraction.** |
| OTEL agent conventions | Pre-RFC | **Emit traces; don't gate.** |

Sources: [MCP roadmap 2026](https://callsphere.ai/blog/model-context-protocol-mcp-2026-roadmap-scalability-enterprise-auth), [MCP technical deep dive 2026](https://dasroot.net/posts/2026/04/model-context-protocol-mcp-technical-deep-dive/), [Auth0 on MCP auth updates](https://auth0.com/blog/mcp-specs-update-all-about-auth/), [MCP security risks & mitigations (SOC Prime)](https://socprime.com/blog/mcp-security-risks-and-mitigations/)

---

## Top 3 Existential Risks (what's been Stripe-Atlas'd by Big Lab)

### 1. **Durable execution: Temporal + OpenAI Agents SDK GA (March 2026) eats most of what Intercore does for sub-agent dispatch and recovery.**
Intercore solves sub-agent dispatch, run tracking, locks, and crash recovery. As of 2026-03-23, this is now a one-line integration in the OpenAI Agents SDK. The honest answer: Intercore's value is no longer the dispatcher — it's the *evidence/policy/trust* layer on top. Refactor Intercore to sit *over* a Temporal substrate (or compatible durable-exec layer), not next to one.

### 2. **Eval/calibration: Langfuse (self-hosted, ClickHouse-backed) + OTEL conventions make Interspect's evidence schema increasingly idiosyncratic.**
Interspect's value is the *closed-loop calibration policy* (canary windows, routing overrides, agent trust scores). The storage and eval engine are not where Sylveste should differentiate. Adopt Langfuse as the eval backend; keep the policy layer in Sylveste. If we don't, in 12 months Sylveste's "evidence pipeline" will look like a worse Langfuse with custom schemas.

### 3. **Session + multi-agent primitives: Anthropic SDK v0.2.49+ (`ConfigChange`, `TeammateIdle`, `TaskCompleted`, `forkSession`) ships native versions of what intermute/interlock built bottom-up.**
This isn't a kill, but it means the bottom-up coordination work we did in 2026-Q1 is now mostly handled by the SDK. Migrate to the native hook events; keep Sylveste's *coordination policy* (reservations, conflict resolution, multi-session safety) on top. Don't ship a parallel hook system.

**Honest synthesis:** None of these obsolete Sylveste — but each forces the same shift: stop owning the substrate, own the *policy and evidence*. The flywheel is policy + receipts; the runtime is increasingly someone else's.

---

## What this means for the Mythos window

1. **Adopt MCP OAuth Resource Indicators for the Gridfire v1 spec.** Don't invent capability tokens — they exist already in production.
2. **Target A2A in transport abstraction (`sylveste-2nfd`).** Cross-vendor interop is the wave.
3. **Adopt Temporal under Intercore (or at minimum, write the Intercore→Temporal adapter spike).** This is the substrate shift.
4. **Adopt Langfuse self-hosted as the Interspect eval backend.** Stop maintaining custom eval code.
5. **Use native Anthropic SDK hooks (`ConfigChange`, `TeammateIdle`, `TaskCompleted`) for intermute/interlock.** Migrate off bottom-up patterns where the SDK now provides primitives.
