# Interdoc Analysis: Intercom AGENTS.md Rewrite

**Date**: 2026-02-25
**Target**: `/home/mk/projects/Demarch/apps/intercom/AGENTS.md`
**Current size**: 300 lines
**Target size**: 250-300 lines

## Summary of Findings

### What Changed Since Last AGENTS.md

The AGENTS.md was written during the NanoClaw-only era and has since received incremental patches for the IronClaw replatform. The document now needs a cohesive rewrite that treats IronClaw as a first-class peer rather than an addendum.

### IronClaw (Rust) Architecture — Current State

The Rust workspace at `rust/` contains 3 crates totaling ~9,337 LOC with 129 tests:

1. **`intercomd`** (daemon) — Axum-based HTTP server with:
   - Telegram bridge (`/v1/telegram/{ingress,send,edit}`)
   - Demarch kernel adapter (`/v1/demarch/{read,write}`)
   - Slash command handler (`/v1/commands`)
   - Full Postgres persistence layer (`/v1/db/*` — 24 DB routes)
   - IPC watcher (filesystem-based, polls `data/ipc/`)
   - Event consumer (polls `ic events tail`)
   - Container orchestrator (message loop, group queue, scheduler) — behind `orchestrator.enabled` flag
   - Container runner (async Docker spawning with OUTPUT marker streaming)
   - Group registry sync (fetches from Node host callback)
   - CLI subcommands: `serve`, `print-config`, `inspect-legacy`, `migrate-legacy`, `verify-migration`

2. **`intercom-core`** (shared types) — Config, IPC types, container protocol, persistence layer (Postgres via tokio-postgres), Demarch adapter, runtime profiles

3. **`intercom-compat`** (migration) — SQLite inspection, SQLite-to-Postgres migration with checkpoint/dry-run/verification

### Strangler-Fig Pattern

The migration uses a clear strangler-fig pattern:

1. **IPC Delegation**: `IpcDelegate` trait in `intercomd/src/ipc.rs` — `HttpDelegate` forwards messages/tasks to Node host's callback server at `http://127.0.0.1:7341`. Demarch queries are handled natively in Rust.

2. **Node Callback Server**: `src/host-callback.ts` — lightweight HTTP server with endpoints:
   - `POST /v1/ipc/send-message` — send via Grammy/Baileys
   - `POST /v1/ipc/forward-task` — task management via SQLite
   - `GET /v1/ipc/registered-groups` — group registry for sync
   - `GET /healthz` — health check

3. **Telegram Routing**: When `INTERCOM_ENGINE=rust`, the Node Telegram channel calls `routeTelegramIngress()` to intercomd for routing decisions, then falls back to Node path if the bridge is unavailable.

4. **Orchestrator Feature Flag**: `orchestrator.enabled` (default: false) — when enabled, intercomd handles the full message loop, container spawning, and scheduling natively, bypassing Node entirely for those paths.

### Stale Content in Current AGENTS.md

1. **Missing orchestrator documentation** — The Rust orchestrator (message loop, queue, container runner, scheduler) is fully implemented but undocumented in AGENTS.md
2. **Missing Postgres persistence** — intercomd uses Postgres (via tokio-postgres) for production persistence, SQLite only for legacy/migration
3. **Missing event consumer** — kernel event push notifications (gate.pending, run.completed, budget.exceeded, phase.changed)
4. **Missing slash command handler** — `/help`, `/status`, `/model`, `/reset` ported to Rust with model catalog and side effects
5. **Missing migration CLI** — `inspect-legacy`, `migrate-legacy`, `verify-migration` subcommands
6. **Missing intercom.toml config** — TOML-based configuration for intercomd
7. **Missing container security in Rust** — mount allowlist, secret management ported to Rust
8. **`stream-accumulator.ts`** — real-time Telegram message editing with tool call streaming (undocumented)
9. **`summarizer.ts`** — conversation summary caching via GPT-5.3 Codex (undocumented)
10. **`host-callback.ts`** — Node callback server for strangler-fig (undocumented)
11. **`intercomd-client.ts`** — Node client for intercomd bridge (undocumented)
12. **`query-handlers.ts`** — Demarch query handlers on Node side (undocumented)
13. **`intercomd.service`** — systemd service for Rust daemon (undocumented)

### Accurate Content to Preserve

1. Architecture overview diagram (needs updating for dual-process model)
2. Container protocol (stdin JSON / stdout markers) — still accurate
3. Container images and runtime details — still accurate
4. Channel system and JID routing — still accurate
5. Container volumes — still accurate
6. Agent tools — still accurate
7. Security model — still accurate (needs Rust additions)
8. Gotchas — still accurate (need additions)

### New Files Not in Current AGENTS.md

| File | Purpose |
|------|---------|
| `src/host-callback.ts` | HTTP callback server for intercomd delegation |
| `src/intercomd-client.ts` | Client for intercomd bridge endpoints |
| `src/query-handlers.ts` | Demarch CLI query handlers (Node side) |
| `src/stream-accumulator.ts` | Real-time Telegram message editing |
| `src/summarizer.ts` | Conversation summary caching |
| `config/intercomd.service` | systemd unit for Rust daemon |
| `config/intercom.toml.example` | TOML config for intercomd |

### Design Decisions Confirmed

- TOML config for Rust daemon (not .env) — env vars for overrides only
- Postgres for Rust persistence, SQLite for legacy/migration only
- `orchestrator.enabled` feature flag for gradual Rust takeover
- Node callback server pattern (not gRPC or Unix sockets)
- `INTERCOM_ENGINE=rust` env var controls Node-side routing to intercomd
