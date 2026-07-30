# Intercom Transport Target — A2A

The protocol Sylveste agents speak to other agents is the Linux-Foundation-governed **Agent2Agent (A2A) protocol**, v1.0+. This is a canonical decision, not a suggestion: every transport-abstraction design in Intercom, every agent-↔-agent surface (Hermes, Skaffen, Hassease, Auraken, Codex bridge), and every cross-vendor interop point targets A2A. Sylveste does not invent a private agent-↔-agent protocol shape.

This document anchors `sylveste-ewy3.4`, `sylveste-2nfd` (transport interface abstraction), and `sylveste-benl.6` (Signal transport). It supersedes any prior implicit assumptions about Sylveste-private agent messaging shapes.

## Why A2A

- **Linux Foundation governance** (since late 2025), 150+ orgs in production, ADK 1.0 ships native A2A across Python / TypeScript / Go / Java with feature parity at the protocol level.
- **Tasks are first-class.** A long-running agent invocation returns a `task_id` immediately, streams progress via SSE, and survives network disconnects. This matches Sylveste sprint semantics far better than a request-response RPC would.
- **Cross-vendor.** A2A-compliant Sylveste agents can be invoked by Google ADK clients, Anthropic Agent SDK clients (once they ship the bridge), and any LangGraph/Mastra/Goose agent that speaks A2A. Conversely, Sylveste agents can call any external A2A agent without bespoke adapters.
- **Standardized identity and discovery.** `GET /.well-known/agent.json` returns an Agent Card declaring capabilities, skills, security schemes. Sylveste gets agent discovery for free.
- **Authoritative spec.** `spec/a2a.proto` is the normative source; language bindings regenerate from it. No specification drift across SDKs.

## Three transport classes, one canonical form

Intercom carries three categories of message; each maps to a transport but all share **A2A Task as the canonical internal form**:

| Class | Transport | Surface |
|---|---|---|
| Human → agent | Telegram, Signal, web | A user sends a message to a Sylveste agent (Hermes, Auraken, Hassease) |
| Agent → agent | A2A | A Sylveste agent invokes another Sylveste agent (or an external A2A agent) |
| Agent → tool | MCP | Sylveste agents call tools; this lane is unchanged |

Human↔agent transports are adapters: an inbound Telegram/Signal message is translated into an A2A `Message` (`role: ROLE_USER`, with `parts` carrying text/file/data), wrapped in a `SendMessageRequest`, and dispatched through the same routing path as a native A2A call. Outbound agent responses come back as A2A `Message` (`role: ROLE_AGENT`) and the transport adapter renders them for the human surface (Telegram markdown, Signal reactions, etc.).

This means Telegram/Signal are *adapters around A2A*, not parallel message paths. The routing, scheduler, subprocess manager, and evidence pipeline see one canonical shape.

## Sylveste-sprint ↔ A2A-Task adapter layer

The two abstractions are not the same; the difference is durable identity vs. runtime execution.

| A2A | Sylveste |
|---|---|
| `Task.id` | Ephemeral runtime handle |
| `Task.contextId` | Maps to the bead ID (e.g. `sylveste-ewy3.4`) |
| `Task.history` | A2A's interaction log for the task |
| `Task.artifacts` | Maps to Sylveste evidence file references (Dolt-backed) |
| `Task.metadata` | Carries Sylveste-specific fields (sprint phase, agent identity, model tier) |
| A2A `Message` parts | Text + file + data, exactly the parts Sylveste already records |

**Mapping rules:**

1. One Sylveste **sprint** corresponds to one A2A `contextId`. Every Task within the sprint shares that `contextId`.
2. Each **agent invocation** within a sprint is one A2A Task. The phase (`brainstorm`, `strategy`, `plan`, `execute`, `review`, `ship`) goes in `Task.metadata.sprint_phase`.
3. Each **completed action** writes a Sylveste evidence row keyed by `task_id` + `contextId`. The artifact is referenced from `Task.artifacts` so external A2A clients can fetch it via standard endpoints.
4. **Bead identity is canonical**, A2A identity is derived. The bead never moves; `task_id` is a per-run handle. Tasks are GC-eligible once their evidence is sealed.
5. **TaskState mapping**: `TASK_STATE_WORKING` ↔ in_progress, `TASK_STATE_COMPLETED` ↔ closed (with evidence sealed), `TASK_STATE_INPUT_REQUIRED` ↔ blocked-on-human (the bead surfaces this), `TASK_STATE_AUTH_REQUIRED` ↔ blocked-on-capability-token (Gridfire denial).

## Endpoints Sylveste agents expose

Every Sylveste agent that becomes A2A-addressable exposes the standard A2A endpoint set:

- `POST /messages` → `SendMessage` (synchronous)
- `POST /messages:stream` → `SendStreamingMessage` (SSE)
- `GET /tasks/{id}` → `GetTask`
- `GET /tasks/{id}:subscribe` → `SubscribeToTask` (SSE)
- `GET /tasks` → `ListTasks` (with cursor pagination)
- `POST /tasks/{id}:cancel` → `CancelTask`
- Push-notification config endpoints for webhook-driven progress
- `GET /.well-known/agent.json` → Agent Card

Intercom hosts the HTTP server; per-agent Agent Cards differ by `skills`, `capabilities`, and `securitySchemes`. The Agent Card for Hermes advertises Signal/Telegram personality skills; Hassease advertises code-execution skills with effects-allowlist disclosures; Skaffen advertises lens-driven reasoning skills.

## Identity per Sylveste agent

Each Sylveste agent that the world can address through A2A has:

- A stable **agent identity URI** (e.g. `sylveste://agent/hermes`).
- A published **Agent Card** under that identity's HTTP root.
- A set of **capability declarations** (`streaming`, `pushNotifications`, `extendedAgentCard`).
- A **security scheme** anchored on MCP OAuth Resource Indicators (RFC 8707) — see `docs/canon/authz-token-model.md` and the Gridfire-v1 alignment under `sylveste-ewy3.3`.

Multi-agent flows that today happen via intermute (tmux paste-buffer) keep working locally as a fast path; A2A is the canonical surface across hosts and across vendors.

## Authentication

Per A2A §7, Agent Cards declare `securitySchemes`. Sylveste's chosen scheme is **OAuth2 with Resource Indicators** matching the Gridfire-v1 decision (`sylveste-ewy3.3`). Tokens are scoped to the specific Sylveste agent the caller intends to reach; cross-agent token confusion is denied by default. Mutual-TLS is acceptable for local-only fast-path between co-resident Sylveste agents; the public surface uses OAuth2.

## Versioning

Sylveste asserts `A2A-Version: 1.0` on all requests and accepts `0.3` (the default per spec §3.2.6) inbound. The `A2A-Extensions` header carries any Sylveste-specific extension URIs (e.g. `sylveste://ext/sprint-phase` for the `sprint_phase` metadata convention). Extensions are additive; they never gate base-protocol compatibility.

## What this does NOT cover

A2A defines the *wire*. It does not define:

- The Sylveste **phase-gate model** (brainstorm → strategy → plan → execute → review → ship). That stays in Clavain.
- The **evidence pipeline** (Interspect/Interstat closed-loop calibration). That stays in Sylveste with A2A artifacts as the export surface.
- The **[human delegation ladder](autonomy.md#1-human-delegation-ladder-l0l5)** (L0–L5). That is Sylveste policy carried in Task metadata, not an A2A primitive.
- The **bead tracker**. Beads remain canonical for durable work-tracking; A2A Tasks are runtime execution handles.

A2A is the wire; Sylveste is the policy + receipts + sprint model on top.

## Acceptance criteria delta — downstream beads

### sylveste-2nfd (Design transport interface abstraction in Intercom)

The interface design must:

1. Define a `Transport` interface in `apps/Intercom/go/internal/transport/` with concrete implementations for `telegram`, `signal`, and `a2a`. Telegram and Signal are adapters that translate to/from A2A `Message`/`Task`; A2A is the native shape.
2. Move existing `internal/telegram/` under `internal/transport/telegram/` as part of the migration. Preserve all current behavior.
3. The routing layer (`internal/routing/`) reads canonical A2A `Message`/`Task` shapes, not transport-specific types.
4. The scheduler (`internal/scheduler/`) keys work by `Task.id` (runtime) and bead/contextId (durable). The two stores stay distinct.
5. Document the interface contract in `apps/Intercom/AGENTS.md` Transport section.

### sylveste-benl.6 (Add Signal transport to Intercom)

Signal transport must:

1. Implement the same `Transport` interface as Telegram. No direct talking to routing — only via A2A `Message` translation.
2. Reuse Intercom's subprocess manager for agent dispatch; the dispatch interface is A2A Task creation, not a Signal-shaped object.
3. Burst collection / command routing logic lives in the Signal adapter; downstream consumers see A2A messages only.

### sylveste-ewy3.3 (Gridfire v1 = MCP OAuth Resource Indicators)

The Gridfire-v1 token model is the security scheme advertised in Sylveste Agent Cards. Per-agent Resource Indicators map to per-agent identity URIs. A token scoped to `sylveste://agent/hermes` cannot be replayed against `sylveste://agent/hassease`.

## Why this anchor matters

Three high-leverage P0 epics block on the transport-abstraction work: Auraken→Hermes overlay (`sylveste-22oi`), Skaffen Go migration (`sylveste-benl`), and Hassease daemon (`sylveste-nr6x`). Without a transport target decision, each would invent its own message shape, and a unifying refactor would be required later. Anchoring on A2A now means each of those workstreams can ship against the same wire shape, with no rework when cross-vendor interop becomes a launch requirement.

## References

- A2A spec: https://a2a-protocol.org/latest/specification/ (§4.1 Tasks, §4.2 Streaming, §8 Agent Cards, §7 Auth, §11.3 HTTP endpoints).
- A2A is governed by the Linux Foundation; ADK 1.0 documentation: https://google.github.io/adk-docs/a2a/.
- Sylveste synthesis: `docs/research/flux-research/sylveste-ecosystem-strategic-scan-2026q2-mythos-gate-e359cecd/SYNTHESIS.md` (Tier 1 #2).
- Gridfire v1 token alignment: `docs/canon/authz-token-model.md` (pending update under `sylveste-ewy3.3`).
- Beads: `sylveste-ewy3.4` (this decision), `sylveste-2nfd` (interface), `sylveste-benl.6` (Signal adapter).
