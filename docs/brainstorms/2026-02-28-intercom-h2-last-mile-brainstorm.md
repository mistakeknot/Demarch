# Intercom H2 Last Mile — Brainstorm

**Bead:** iv-x6gd2
**Date:** 2026-02-28
**Status:** Ready for strategy
**Alignment:** Directly advances Intercom's H2 vision — making it a bidirectional agency participant, not just a read terminal. Core Demarch principle: every action produces evidence, and Intercom becomes the surface through which humans contribute that evidence from messaging.
**Conflict/Risk:** None — all architectural decisions were resolved in the vision doc (v0.2). This is pure implementation of decided designs.

---

## Context

Intercom is a dual-process personal AI assistant: Node host (channels, commands) + IronClaw (Rust daemon for orchestration, containers, Postgres, Telegram bridge). It faces humans via messaging channels (Telegram, WhatsApp) and runs container-isolated agents (Claude, Gemini, Codex).

The vision doc defines three horizons:
- **H1 (Agency-Aware Reads): ~90% complete.** 7 Demarch query types work end-to-end across all runtimes.
- **H2 (Agency Participant): Infrastructure built, surface not exposed.** Write operations defined in Rust, IPC dispatch exists, HTTP endpoints wired — but no container tools or event reply bridging.
- **H3 (Distributed Team Surface): Future.** Role-based access, cross-channel continuity, voice adaptation.

## The Gap

H2's backend is fully wired in Rust:
- `WriteOperation` enum: `CreateIssue`, `UpdateIssue`, `CloseIssue`, `StartRun`, `ApproveGate`
- `DemarchAdapter::execute_write()` with allowlist validation and main-group requirement
- `POST /v1/demarch/write` HTTP endpoint
- IPC dispatcher routes write query types to operations

What's missing is the **container-facing surface** and the **event reply loop**:

### Missing Piece 1: Container Write Tools

No write functions in `container/shared/demarch-tools.ts` (only reads). No write MCP tools in `container/agent-runner/src/ipc-mcp-stdio.ts` (only reads). Container agents literally cannot submit write intents.

**Needed:** 5 write wrapper functions + 5 MCP tool declarations. They use the same `queryKernel()` IPC bridge that reads use — the host-side IPC dispatcher in `ipc.rs` already routes write query types.

### Missing Piece 2: Event Reply Bridging

The event consumer in `events.rs` sends Telegram notifications for `gate.pending`, `run.completed`, `budget.exceeded`, `phase.changed`. But:
- Notifications are text-only (no inline keyboard buttons)
- No callback query handler in `telegram.rs` for button presses
- No text command parser to intercept "APPROVE gate-123" replies
- User replies go nowhere — they're treated as regular messages

**Needed:** Inline button rendering on gate notifications + callback handler that routes APPROVE/REJECT to `WriteOperation::ApproveGate`.

### Missing Piece 3: demarch_research (H1 completion)

The vision specified 8 read tools. 7 are implemented. `demarch_research` (Pollard query or `ic discovery search`) is missing. Small scope, completes H1 100%.

## Proposed Work

### Task 1: Container Write Tools

Add to `container/shared/demarch-tools.ts`:
```
demarchCreateIssue(ctx, title, description?, priority?, type?, labels?)
demarchUpdateIssue(ctx, id, status?, priority?, title?, description?, notes?)
demarchCloseIssue(ctx, id, reason?)
demarchStartRun(ctx, title?, description?)
demarchApproveGate(ctx, gateId, reason?)
```

Add corresponding MCP tools to `container/agent-runner/src/ipc-mcp-stdio.ts` for Claude runtime. These call `queryKernel()` with write query types — the IPC bridge handles everything.

**Tiered safety (from vision doc):**
- Auto-execute: `CreateIssue`, `CloseIssue` (reversible, non-policy-governing)
- Human-confirm: `ApproveGate`, `StartRun` (policy-governing — host posts confirmation request to chat, waits for explicit human reply)

Tier enforcement lives in the host-side IPC handler, not in the container tools. Container tools just submit intents.

### Task 2: Event Reply Bridging (Gate Approval)

In `events.rs`: When sending `gate.pending` notification, include Telegram inline keyboard buttons (APPROVE / REJECT / DEFER).

In `telegram.rs`: Add callback query handler that:
1. Parses button callback data (`approve:{gate_id}`, `reject:{gate_id}`, `defer:{gate_id}`)
2. Routes to `WriteOperation::ApproveGate` via the Demarch adapter
3. Edits the original message with the result ("Gate approved by @user")
4. Records the action in kernel event log

Fallback for WhatsApp (no inline buttons): Parse keyword replies (`APPROVE <gate_id>`, `REJECT <gate_id>`).

Timeout: Configurable (default 1h), auto-defer on expiry with notification. First reply wins; duplicates get "already resolved."

### Task 3: Budget/Run Event Actions

Similar to gate approval but for `budget.exceeded` and `run.completed`:
- Budget exceeded: EXTEND / CANCEL buttons → `ic budget extend` or `ic run cancel`
- Run completed: VIEW RESULTS / START NEXT buttons → read-only links or `ic run create`

Lower priority than gate approval — gate blocking is the critical path.

### Task 4: demarch_research Tool (H1 Completion)

Add `demarch_research` to complete H1:
- Query type: `research`
- Host handler: Execute `ic discovery search --json` or future Pollard API
- Container tool: `demarchResearch(ctx, query)`
- MCP tool: `demarch_research`

Small scope, can be done in parallel with other tasks.

## Existing Beads (Link or Close)

These existing beads map to this work:
- **iv-902u6** (gate approval via Telegram) → Task 2
- **iv-wjbex** (sprint status push notifications) → Already working (events.rs sends notifications). Close or verify.
- **iv-niu3a** (discovery triage via messaging) → Partially addressed by Task 1 (`demarchNextWork` read exists, `demarchCreateIssue` write enables acting on it). May need a dedicated "triage flow" skill.
- **iv-elbnh** (session continuity across model switches) → Bug, separate from H2 last mile. Keep open.

## Risk Assessment

**Low risk overall.** The hard architectural decisions are made. The backend is tested (129+ Rust tests). This is surface wiring.

- **Security:** Write tools go through the same allowlist + main-group validation as the HTTP endpoint. No new attack surface.
- **Backward compatibility:** Additive only — new tools, new handlers. Nothing changes for existing reads.
- **Testing:** Each write tool can be tested via the existing IPC test harness. Gate approval needs integration test with Telegram Bot API mock.

## Decision Log

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Write tool IPC mechanism | Same `queryKernel()` as reads | IPC dispatcher already routes write types. No new mechanism needed. |
| Tier enforcement location | Host-side IPC handler | Containers can't self-promote. Host validates and applies tier policy. |
| Gate approval UX | Inline buttons (Telegram) + keyword fallback (WhatsApp) | Resolved in vision doc Q4. One-tap, structured, no parsing ambiguity. |
| Timeout behavior | Auto-defer after 1h | Resolved in vision doc. Configurable, first-reply-wins. |

---

*Brainstorm complete. Ready for strategy phase: create PRD with task breakdown, dependency ordering, and bead creation.*
