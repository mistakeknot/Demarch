# Brainstorm: Window Identity for Agent Session Persistence (iv-uk7c3)

**Bead:** iv-uk7c3
**Date:** 2026-02-25

## Problem

Interlock agent identity is tied to `CLAUDE_SESSION_ID` which changes on every session restart. This means:
- New agent registration on every restart → new agent ID
- Lost reservations (keyed by old agent ID)
- Lost coordination context (inbox, threads, contacts)
- Multi-session agents hitting `ErrActiveSessionConflict` (5-min staleness window)

## Design Decision: Separate `window_identities` table

**Why not add `window_uuid` to the `agents` table?** Because a window identity is a stable mapping that spans multiple ephemeral agent sessions. The agents table has one row per session (with `session_id`). Window identity should be a lookup table that resolves *before* agent registration.

## Architecture

```
Window UUID (stable per tmux pane)
    ↓ lookup
window_identities table → stable agent_id + display_name
    ↓ reuse
agents table → re-register with SAME agent_id, new session_id
    ↓ preserves
reservations, inbox, contacts (all keyed by agent_id)
```

## Window UUID Source Priority

1. `INTERLOCK_WINDOW_ID` env var (explicitly set, highest stability)
2. Derived from `TMUX_PANE` via SHA1 UUID namespace (`uuid.NewSHA1(interlock_ns, TMUX_PANE)`)
3. None → fall back to current per-session behavior

## Schema

```sql
CREATE TABLE IF NOT EXISTS window_identities (
  id TEXT PRIMARY KEY,
  project TEXT NOT NULL,
  window_uuid TEXT NOT NULL,
  agent_id TEXT NOT NULL,        -- stable agent_id to reuse
  display_name TEXT NOT NULL,
  created_at TEXT NOT NULL,
  last_active_at TEXT NOT NULL,
  expires_at TEXT                 -- NULL = no expiry, TTL-based cleanup
);
CREATE UNIQUE INDEX uq_window_project ON window_identities(project, window_uuid);
```

## Lifecycle

- **Session start:** Resolve window UUID → lookup in window_identities → if found, reuse `agent_id` for registration
- **Session stop:** Touch `last_active_at`, do NOT expire (windows persist across sessions)
- **Explicit leave:** Expire window identity + release reservations
- **Cleanup:** Background or on-demand sweep of expired entries (expires_at < now)

## MCP Tools (3 new)

1. `list_window_identities` — list active windows for the project
2. `rename_window` — update display_name
3. `expire_window` — set expires_at = now (soft delete)

## HTTP Endpoints (intermute)

- `POST /api/windows` — upsert by (project, window_uuid), touch last_active_at
- `GET /api/windows?project=X` — list non-expired entries
- `DELETE /api/windows/{id}` — expire (set expires_at = now)

## Changes Required

1. **Intermute schema** — new `window_identities` table + migration
2. **Intermute Store interface** — `UpsertWindowIdentity`, `ListWindowIdentities`, `ExpireWindowIdentity`
3. **Intermute HTTP handlers** — 3 new endpoints
4. **Interlock client** — `UpsertWindow`, `ListWindows`, `ExpireWindow` methods
5. **Interlock MCP tools** — 3 new tools (20 total)
6. **Interlock register script** — resolve window UUID, lookup/create identity, reuse agent_id
7. **Interlock join command** — set `INTERLOCK_WINDOW_ID` from TMUX_PANE
