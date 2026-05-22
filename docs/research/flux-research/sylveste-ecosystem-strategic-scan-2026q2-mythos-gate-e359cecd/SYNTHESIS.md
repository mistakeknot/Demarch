---
artifact_type: research-synthesis
method: flux-research
date: 2026-05-22
target: "Highest-leverage work in the Sylveste ecosystem for the Mythos-launch window"
agents: [best-practices-researcher, framework-docs-researcher (host-supplemented), repo-research-analyst, git-history-analyzer, learnings-researcher]
window: 3 months to Mythos launch
---

# Sylveste Strategic Scan — Q2 2026 Mythos Window

## TL;DR

The highest-leverage work in the Sylveste ecosystem for the next 3 months is **consolidation under external substrate plus closed-loop wiring of what's already half-built**, not new capability. Five concrete moves:

1. **Plugin inventory + install packs + drift gates** (flux-review found 4/4 track convergence on this; nothing downstream works without it).
2. **Transport abstraction targeting A2A** (`sylveste-2nfd` + `benl.6`) — unblocks Hermes, Skaffen Go, Hassease *and* gets cross-vendor interop for free. Don't invent a private protocol.
3. **Autonomy A:L3 routing-calibration wiring** (`sylveste-myyw`, `oyrf`) — the Mythos cost story. 3/5 loops already wired; routing is 2.5/4.
4. **Adopt Temporal under Intercore + Langfuse under Interspect** — both are now production-grade externally. Stop owning the substrate, own the policy.
5. **Gridfire v1 = MCP OAuth Resource Indicators (RFC 8707)** — capability tokens already standardized; adopt instead of designing.

The shift the data forces: Sylveste's moat is the *policy, receipts, and flywheel* — not the runtime, not the eval schema, not the coordination primitives. Each Big Lab ship in 2026-Q2 nudges Sylveste further up the stack. The platform should welcome that nudge, not resist it.

---

## What the evidence says

### Internal state (from repo-research-analyst, git-history-analyzer, learnings-researcher)

- **Maturity:** 60 Interverse plugins; most subsystems at M1–M2 (Built → Operational). **No subsystem has reached M3 (Calibrated).** M2→M3 transitions require 45–90 day observation windows — they're a measurement problem, not a code problem.
- **Closed-loop calibration scorecard:**
  - Gate thresholds: **4/4 wired** ✓
  - Phase-cost: **4/4 wired** ✓
  - Fleet budget: **4/4 wired** ✓
  - Routing: **2.5/4 wired** (file exists but SessionEnd auto-write missing)
  - Routing overrides: **1.5/4 wired** (proposals draft-only, no auto-apply)
- **Backlog vs. shipping reality:** 1,202 commits / 60 days, ~155 beads closed. Of 15 open P0 epics, only ~5 are actively moving in commit history. The other 10 are tracked-but-stalled, blocked on shared design dependencies (transport abstraction, Hermes overlay structure).
- **Critical-path convergence:** Hermes overlay, Skaffen Go migration, and Hassease daemon all block on **the same shared dependency** — transport interface abstraction (`sylveste-2nfd`, `benl.6`).
- **Recent strategic signal:** Microrouter `.19` killed correctly on 6.2% coverage measurement. Lattice v0c shipments (114→137 consume edges) are load-bearing for plugin discovery. DeepSeek V4 spike's hard wall-clock (2026-05-19) has expired — that decision point is settled, one way or the other.
- **Platform debt:** Nested-repo `GIT_INDEX_FILE` corruption fixed in interlock 0.2.14 but fragile; concurrent-agent bundling lacks structural fix; beads Dolt drift managed but non-idempotent.

### External state (from best-practices-researcher + framework-docs-researcher)

The agent-dev ecosystem made several Big Lab shipments in 2026-Q2 that directly overlap Sylveste subsystems:

| Big Lab ship | Date | Sylveste subsystem overlap | Honest verdict |
|---|---|---|---|
| **OpenAI Agents SDK + Temporal GA** | 2026-03-23 | Intercore dispatch/runs | Adopt as substrate, keep policy layer on top. |
| **Claude Code SDK `TeammateIdle`/`TaskCompleted`/`ConfigChange`/`forkSession`** | v0.2.49+ | intermute, interlock, intermux | Native hooks for what we built bottom-up — migrate. |
| **MCP non-blocking startup + `alwaysLoad`** | v0.2.142+ | Clavain SessionStart (`sylveste-z55b`) | Directly satisfies the refactor; adopt. |
| **OpenTelemetry context propagation in CLI** | v0.2.113+ | Interspect, interflux | OTEL is cross-vendor lingua franca; emit alongside Dolt. |
| **A2A protocol (Linux Foundation, 150+ orgs)** | Q2 2026 | `sylveste-2nfd` transport abstraction | Target A2A. Don't invent a private protocol. |
| **MCP OAuth Resource Indicators (RFC 8707, required)** | Q1 2026 | Gridfire v1 capability tokens | Already standardized; adopt instead of designing. |
| **Langfuse acquired by ClickHouse; remains OSS self-hosted** | Jan 2026 | Interspect evidence + Interstat metrics | Adopt as eval backend; Sylveste owns the policy. |
| **Codex Goal Mode + Remote Computer Use** | Q2 2026 | Clavain sprints + Hassease | Defend with phased-gate receipts; don't compete on remote desktop. |
| **Gartner: 89% multi→single agent convergence** | 2026 | interflux multi-track review | Sharpen distinction: review benefits from diversity; execution doesn't. |

**Top 3 existential risks:**

1. **Durable execution is now a one-line OpenAI/Temporal integration.** Intercore's value as a dispatcher is shrinking; its value as a policy + evidence layer is intact. Refactor accordingly.
2. **Langfuse self-hosted + OTEL conventions make Interspect's bespoke evidence schema look increasingly idiosyncratic.** Storage and eval aren't where Sylveste differentiates; the *closed-loop calibration policy* is.
3. **Claude SDK now ships the multi-agent hook primitives we built bottom-up.** Migrate to native events; keep coordination *policy* on top. Don't ship a parallel hook system.

None of these obsoletes Sylveste. Each forces the same shift: stop owning the substrate, own the policy and receipts.

---

## The five highest-leverage workstreams (ranked)

### Tier 1 — Mythos window (the next 8–10 weeks)

#### 1. Plugin inventory + install packs + drift gates
**Why first:** 4/4 flux-review tracks converged on this. It's the data foundation for Codex integration, marketplace publishing, doctor reliability, and stale-plugin detection. Without it, the next four workstreams keep tripping over manifest drift.

**Beads in flight:** `sylveste-wkjf` (P0, Codex skill ID fix), `sylveste-b4ch` (P1, generated inventory ledger), `sylveste-i0sa` (P1, install profile packs).

**Done when:** doctor validates manifest ↔ disk ↔ marketplace consistency; Codex install uses `core`/`review`/`docs` packs by default; `claude plugin disable` respects dependencies.

**Effort:** 1–2 weeks.

#### 2. Transport abstraction targeting A2A (the unblock-everything move)
**Why second:** Three high-leverage P0 epics (Hermes overlay `sylveste-22oi`, Skaffen Go migration `sylveste-benl`, Hassease daemon `sylveste-nr6x`) all block on this. Doing it right *also* gives Sylveste cross-vendor interop with the 150+ orgs already on A2A. Targeting an arbitrary private protocol shape would be self-inflicted lock-in.

**Beads in flight:** `sylveste-2nfd` (P0, transport interface), `sylveste-benl.6` (P0, Signal transport in intercom).

**Critical decision:** Target A2A natively. Sylveste's MCP plugins continue as MCP; agent↔agent flows go A2A. Don't invent a third protocol.

**Done when:** Intercom exposes A2A-compatible transport; Hermes can run on it; Skaffen Go can subscribe; Codex can route to Hassease through it.

**Effort:** 3–4 weeks.

#### 3. Autonomy A:L3 closed-loop wiring (the cost story for Mythos)
**Why third:** Mythos launch narrative is "Sylveste proves cost efficiency through closed-loop calibration." Two of five loops are fully wired; routing is 2.5/4. Finishing this is mostly *plumbing*, not new design.

**Beads in flight:** `sylveste-myyw` (P0, all three calibration loops fire autonomously), `sylveste-oyrf` (P0, longitudinal cost-calibration + launch artifacts).

**Done when:** SessionEnd hook auto-writes `routing-calibration.json`; override proposals auto-generate from canary data; `data/cost-trajectory.csv` updates every 6 hours; 10 consecutive sprints with no manual calibration.

**Effort:** 2–3 weeks.

### Tier 2 — Spike now, decide by Mythos + 1 month

#### 4. Adopt Temporal under Intercore (substrate consolidation)
**Why now:** OpenAI Agents SDK + Temporal GA on 2026-03-23 is the industry baseline. Intercore's runs/dispatches/locks subsystem solves a subset of what Temporal+Agents now solves natively. Refactor Intercore to be the *policy + evidence* layer over a Temporal substrate.

**Decision:** Run a 2-week integration spike. Wire one Sylveste dispatch flow through Temporal as Activity. Measure: cost-per-second, observability fidelity, evidence compatibility, ops complexity. File `docs/research/assess-temporal-2026q2.md` with verdict.

**Why not skip:** The longer Intercore tries to do durability + scheduling + policy, the more the durable-exec gap with the industry compounds. Better to make the call early, in the Mythos window, while there's time to refactor.

#### 5. Adopt Langfuse self-hosted under Interspect (eval substrate)
**Why now:** Langfuse (ClickHouse-acquired Jan 2026) is the only OSS-first eval platform that handles self-hosted at scale. Interspect's evidence schema in Dolt is increasingly idiosyncratic; the calibration *policy* is what matters.

**Decision:** Self-host Langfuse on zklw (or sleeper-service successor). Pipe Interspect evidence to Langfuse traces. Keep Sylveste's routing-override policy on top. File `docs/research/assess-langfuse-2026q2.md` with verdict.

**Why not skip:** Same logic as Temporal. The eval/observability commodity is converging; Sylveste's edge is the closed-loop policy, not the storage engine.

#### 6. Gridfire v1 = MCP OAuth Resource Indicators
**Why now:** RFC 8707 Resource Indicators are now *required* in MCP clients. This is capability-scoped tokens — exactly the primitive Gridfire was designing in long-form. Adopt the standard for Gridfire v1; reserve the unforgeable-token + delegation work for v2.

**Decision:** Update Gridfire spec to use MCP Resource Indicators as the v1 implementation. Defer the v2 design until v1 is in production. Sketch the migration path in `docs/canon/authz-token-model.md`.

### Tier 3 — Defensive moves (in parallel)

7. **Migrate intermute/interlock to native SDK hooks** (`TeammateIdle`, `TaskCompleted`, `ConfigChange`). Keep Sylveste's coordination *policy* (reservations, conflict resolution). Don't maintain bottom-up parallels of what the SDK now provides.
8. **Generated-agent retention + pack-scoped loading** (`sylveste-7zw2`). Hundreds of `fd-*` agents loading eagerly is a startup cost we shouldn't pay.
9. **Flux-review cost/concurrency controls + ephemeral read-only mode** (`sylveste-2o0s`). The review engine is load-bearing for Mythos; its cost should be observable.
10. **Nested-checkout freshness gate in doctor** (`sylveste-x1rf`). The interlock-fix-exists-but-nested-checkout-was-stale incident is exactly the class of failure Sylveste should prevent.

### What to deprioritize

- **Custom durable-execution code in Intercore.** Temporal+Agents SDK ate this.
- **Custom eval pipeline schemas in Interspect.** Langfuse + OTEL ate this.
- **Bottom-up coordination primitives that overlap Anthropic SDK hooks.**
- **Microrouter architecture work** (already correctly killed on 6.2% coverage measurement).
- **Inventing a private agent-transport protocol.** A2A is the standard.
- **Browser/desktop automation features** (Codex Remote Computer Use + Goal Mode). Differentiate on Signal/Telegram personality + phased-gate receipts, not on remote-desktop.

---

## What's defensibly Sylveste (the moat)

Stripped of substrate, what's left for Sylveste to own?

1. **The OODARC flywheel** — evidence earns authority (L0–L5), explicit progressive trust. No Big Lab has shipped this as a coherent product. Every action has a receipt; every receipt feeds calibration; every calibration adjusts routing/triage. This is policy, not plumbing — uncopyable in 3 months.
2. **Phased sprint gates** — brainstorm → strategy → plan → execute → review → ship. Codex Goal Mode is open-ended; Clavain's value is the *gate model + receipts that compound across sprints*. The phased model survives Mythos.
3. **Multi-agent review (interflux)** — explicitly *different from* multi-agent execution. Execution converges to single-agent-with-tools (89% Gartner). Review benefits from diversity. Sylveste's flux-review fan-out + cross-track convergence is on the right side of that distinction; sharpen it in docs.
4. **Plugin composition policy** — strong defaults, replaceable policy, mechanism/policy separation. Install packs (Tier 1 #1) make this concrete.
5. **Self-building proof** — Sylveste builds Sylveste with its own tools. This is a trust-earning artifact no Big Lab can replicate without an equivalent open-source self-building demonstration.
6. **Signed-receipt standards** — *opportunity*, not yet built. Industry talks about "verifiable AI" but no one has shipped HMAC-signed action receipts at scale. Sylveste's Dolt-backed evidence + a sign-and-verify layer = a defensible portable-evidence primitive.

---

## Recommended execution order

1. **This week** (P0 quick win): `sylveste-wkjf` — Normalize interflux skill IDs across Claude manifest, commands, Codex installer. Adds doctor assertions. Unblocks Codex.
2. **Next 1–2 weeks**: Plugin inventory ledger + install profile packs + drift gate (`b4ch`, `i0sa`).
3. **Next 1 week**: Nested-checkout freshness gate (`x1rf`).
4. **Weeks 2–4** (parallel): A:L3 routing calibration wiring (`myyw`, `oyrf`).
5. **Weeks 2–5** (parallel): Transport abstraction targeting A2A (`2nfd`, `benl.6`).
6. **Weeks 3–5**: Temporal + Langfuse spike + assess docs. Decision by week 5.
7. **Weeks 4–8** (after A2A lands): Hermes overlay, Skaffen Go, Hassease M1 — the user-facing Mythos features (`22oi`, `benl`, `heh8`, `nr6x`).
8. **Weeks 6–8**: SDK hook migration (`TeammateIdle`/`TaskCompleted`/`ConfigChange`); generated-agent retention (`7zw2`); flux-review cost controls (`2o0s`).
9. **Weeks 8–10**: 10 consecutive sprints of autonomous calibration as Mythos proof-cycle.

**Critical path:** Plugin inventory → A2A transport → A:L3 wiring → 10-sprint proof. The substrate adoptions (Temporal, Langfuse) and SDK migrations are parallel work, not on the critical path.

---

## Decision the user needs to make

The biggest open question is **whether to adopt Temporal + Langfuse as substrates inside the Mythos window, or defer them until post-launch.** The case for inside-the-window: cleaner story at launch ("Sylveste sits on production-grade open-source substrate"), no parallel-systems debt accreting through Q3. The case for after: less risk to the 8-10 week critical path; refactor while live traffic exists to ground decisions.

The recommendation here is **spike now, decide by week 5**. The spike is cheap; the option value is real; the decision shouldn't depend on guesswork.
