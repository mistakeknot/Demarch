# PRD: Intercom H2 Last Mile — Bidirectional Agency Participation

**Bead:** iv-x6gd2
**Date:** 2026-02-28
**Status:** Draft
**Source:** [Brainstorm](../brainstorms/2026-02-28-intercom-h2-last-mile-brainstorm.md) | [Vision](../../apps/intercom/docs/intercom-vision.md)

## Problem

Intercom's H2 backend is fully wired in Rust (write operations, IPC dispatch, HTTP endpoints, event consumer) but container agents can't submit write intents and event reply bridging doesn't exist. Users receive gate approval notifications in Telegram but can't act on them — replies are treated as regular messages. H1 is 90% complete with one missing read tool.

## Solution

Wire the container-facing surface (5 write tools + MCP declarations) and close the event reply loop (inline buttons + callback handlers). Complete H1 by adding the last read tool. All work builds on existing, tested infrastructure — no new architectural decisions needed.

## Features

### F1: Container Write Tools
**What:** Expose 5 write operations to container agents across all runtimes (Claude MCP, Gemini, Codex), using the existing `queryKernel()` IPC bridge.

**Acceptance criteria:**
- [ ] `demarchCreateIssue(title, description?, priority?, type?, labels?)` in `container/shared/demarch-tools.ts`
- [ ] `demarchUpdateIssue(id, status?, priority?, title?, description?, notes?)` in `container/shared/demarch-tools.ts`
- [ ] `demarchCloseIssue(id, reason?)` in `container/shared/demarch-tools.ts`
- [ ] `demarchStartRun(title?, description?)` in `container/shared/demarch-tools.ts`
- [ ] `demarchApproveGate(gateId, reason?)` in `container/shared/demarch-tools.ts`
- [ ] Corresponding 5 MCP tool declarations in `container/agent-runner/src/ipc-mcp-stdio.ts`
- [ ] Write intents route through existing IPC bridge → host IPC dispatcher → Rust `/v1/demarch/write`
- [ ] Tiered safety enforced at host level: `CreateIssue`/`CloseIssue`/`UpdateIssue` auto-execute; `StartRun`/`ApproveGate` require human confirmation
- [ ] All writes restricted to main group by default (existing `require_main_group_for_writes` config)
- [ ] Tests: at least one integration test per write tool via IPC harness

### F2: Gate Approval via Telegram
**What:** When a gate needs approval, send inline keyboard buttons in Telegram. Handle button presses to approve/reject/defer gates through the kernel.

**Acceptance criteria:**
- [ ] `gate.pending` events render with Telegram `InlineKeyboardMarkup` (APPROVE / REJECT / DEFER buttons)
- [ ] Callback query handler in `telegram.rs` parses button data (`approve:{gate_id}`, `reject:{gate_id}`, `defer:{gate_id}`)
- [ ] Handler routes to `WriteOperation::ApproveGate` via `DemarchAdapter`
- [ ] Original message edited with result: "Gate approved by @user" / "Gate rejected by @user"
- [ ] Action recorded in kernel event log (timestamp, user, decision)
- [ ] WhatsApp fallback: keyword replies (`APPROVE <gate_id>`, `REJECT <gate_id>`) parsed in Node host
- [ ] Timeout: auto-defer after configurable period (default 1h) with notification
- [ ] First reply wins; duplicate replies get "already resolved" response
- [ ] Existing bead iv-902u6 closed upon completion

### F3: Budget/Run Event Actions
**What:** Add actionable buttons for budget exceeded and run completed events, similar to gate approval.

**Acceptance criteria:**
- [ ] `budget.exceeded` events render with EXTEND / CANCEL buttons
- [ ] EXTEND callback routes to budget extension intent
- [ ] CANCEL callback routes to run cancellation intent
- [ ] `run.completed` events render with summary text and optional START NEXT button
- [ ] Callback handlers in `telegram.rs` for both event types
- [ ] WhatsApp keyword fallback for both event types

### F4: demarch_research Tool (H1 Completion)
**What:** Add the missing 8th read tool to complete H1 at 100%.

**Acceptance criteria:**
- [ ] `research` query type handled in `src/query-handlers.ts` — executes `ic discovery search --json <query>`
- [ ] `ReadOperation::Research` variant added to Rust `demarch.rs` enum
- [ ] `demarchResearch(ctx, query)` in `container/shared/demarch-tools.ts`
- [ ] `demarch_research` MCP tool in `container/agent-runner/src/ipc-mcp-stdio.ts`
- [ ] Graceful fallback if `ic discovery` subcommand doesn't exist yet (return "research tool not available")

## Non-goals

- **H3 features** (role-based access, cross-channel continuity, voice adaptation) — separate iteration
- **New write operations** beyond the 5 defined in `WriteOperation` enum — scope frozen
- **Interbus integration** — direct `ic`/`bd` calls first, Interbus adapter is additive later
- **Container image rebuilds** — write tools use shared code (hot-reloaded), not runtime-specific code
- **Node→Rust migration** of remaining host features — separate workstream

## Dependencies

- `ic` and `bd` CLIs available on host (already required for H1 reads)
- `ic discovery search` subcommand for F4 (graceful fallback if missing)
- `ic gate override` subcommand for F2 (already used by Clavain gates)
- Telegram Bot API access for inline keyboards (already configured for Telegram channel)
- Grammy bot library (already a dependency) supports `InlineKeyboardMarkup`

## Open Questions

None — all architectural decisions resolved in the vision doc (v0.2). Implementation details are straightforward.
