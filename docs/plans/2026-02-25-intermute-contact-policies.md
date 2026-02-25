# Intermute Contact Policies — Sprint Plan

**Bead:** iv-t4pia
**Phase:** planned (as of 2026-02-25)
**Brainstorm:** docs/brainstorms/2026-02-25-intermute-contact-policies.md

## Sprint Scope

Add 4-level per-agent contact policy to Intermute (`open|auto|contacts_only|block_all`) with enforcement at the HTTP layer, thread-participant exception, auto-allow via file reservation overlap, and MCP tools in interlock. Default `open` — fully backward compatible.

Files: `core/intermute/internal/core/models.go`, `core/intermute/internal/storage/sqlite/schema.sql`, `core/intermute/internal/storage/sqlite/sqlite.go`, `core/intermute/internal/storage/storage.go`, `core/intermute/internal/http/handlers_messages.go`, `core/intermute/internal/http/handlers_agents.go`, `interverse/interlock/internal/tools/tools.go`, `interverse/interlock/internal/client/client.go`

## Task 1: Add ContactPolicy type and constants to core models

- [ ] Add to `core/intermute/internal/core/models.go`:
  - `ContactPolicy` string type with constants: `PolicyOpen`, `PolicyAuto`, `PolicyContactsOnly`, `PolicyBlockAll`
  - `ValidContactPolicy(s string) bool` helper
  - `ContactPolicy` field on `Agent` struct: `ContactPolicy ContactPolicy`
  - `ErrPolicyDenied` sentinel error

## Task 2: Schema migration — add contact_policy column and agent_contacts table

- [ ] Add migration function `migrateContactPolicy(db *sql.DB)` in `sqlite.go`:
  - `ALTER TABLE agents ADD COLUMN contact_policy TEXT NOT NULL DEFAULT 'open'`
  - Create `agent_contacts` table:
    ```sql
    CREATE TABLE IF NOT EXISTS agent_contacts (
      agent_id TEXT NOT NULL,
      contact_agent_id TEXT NOT NULL,
      created_at TEXT NOT NULL,
      PRIMARY KEY (agent_id, contact_agent_id)
    );
    CREATE INDEX IF NOT EXISTS idx_contacts_agent ON agent_contacts(agent_id);
    ```
- [ ] Call `migrateContactPolicy(db)` from `New()` constructor alongside existing migrations
- [ ] Add `agent_contacts` DDL to `schema.sql` for fresh databases
- [ ] Add `contact_policy` column to `agents` DDL in `schema.sql`

## Task 3: Add Store interface methods for contact policy

- [ ] Add to `storage.Store` interface:
  ```go
  SetContactPolicy(ctx context.Context, agentID string, policy core.ContactPolicy) error
  GetContactPolicy(ctx context.Context, agentID string) (core.ContactPolicy, error)
  AddContact(ctx context.Context, agentID, contactAgentID string) error
  RemoveContact(ctx context.Context, agentID, contactAgentID string) error
  ListContacts(ctx context.Context, agentID string) ([]string, error)
  IsContact(ctx context.Context, agentID, senderID string) (bool, error)
  HasReservationOverlap(ctx context.Context, project, agentA, agentB string) (bool, error)
  ```
- [ ] Add stub implementations in `InMemory` store (return `PolicyOpen` for GetContactPolicy, false for IsContact, etc.)

## Task 4: Implement SQLite store methods

- [ ] `SetContactPolicy`: UPDATE agents SET contact_policy = ? WHERE id = ?
- [ ] `GetContactPolicy`: SELECT contact_policy FROM agents WHERE id = ? (return `PolicyOpen` if not found)
- [ ] `AddContact`: INSERT OR IGNORE INTO agent_contacts (agent_id, contact_agent_id, created_at)
- [ ] `RemoveContact`: DELETE FROM agent_contacts WHERE agent_id = ? AND contact_agent_id = ?
- [ ] `ListContacts`: SELECT contact_agent_id FROM agent_contacts WHERE agent_id = ?
- [ ] `IsContact`: SELECT 1 FROM agent_contacts WHERE agent_id = ? AND contact_agent_id = ? LIMIT 1
- [ ] `HasReservationOverlap`: Query active reservations for both agents, use `glob.Overlap()` to check pattern intersection. SQL: two queries for each agent's active reservations, then Go-side overlap check (reuse existing `internal/glob` package)
- [ ] Persist `contact_policy` in `RegisterAgent` (read from `Agent.ContactPolicy` field, write to column)
- [ ] Read `contact_policy` in `scanAgent()` or wherever agents are loaded from DB rows

## Task 5: Enforce contact policy in handleSendMessage

- [ ] Add `checkContactPolicy` method to `Service` in `handlers_messages.go`:
  ```go
  func (s *Service) checkContactPolicy(ctx context.Context, project string, msg core.Message) (allowed []string, denied []string, err error)
  ```
  For each recipient in `msg.To + msg.CC + msg.BCC`:
  - Get recipient's policy via `store.GetContactPolicy(recipientID)`
  - `open`: allow
  - `block_all`: deny
  - `contacts_only`: allow if `IsContact(recipient, msg.From)` OR (msg.ThreadID != "" AND sender is thread participant)
  - `auto`: allow if `HasReservationOverlap(project, recipient, msg.From)` OR `IsContact(recipient, msg.From)` OR (thread participant check)
- [ ] Thread participant check: query `thread_index` for `(project, thread_id, sender)` existence
- [ ] Add `IsThreadParticipant(ctx, project, threadID, agent string) (bool, error)` to Store interface + both implementations
- [ ] In `handleSendMessage`, after existing validation, call `checkContactPolicy`:
  - Filter `msg.To`, `msg.CC`, `msg.BCC` to only allowed recipients
  - If ALL recipients denied: return HTTP 403 with JSON `{"error": "policy_denied", "denied": [...]}`
  - If SOME denied: proceed with allowed recipients, include `denied` in response
  - If all allowed: proceed as before (no behavior change)
- [ ] Update `sendMessageResponse` to include optional `denied []string` field

## Task 6: Add MCP tools to interlock

- [ ] Add `SetContactPolicy(ctx, policy string) error` to interlock `client.Client`
  - HTTP: PATCH /api/agents/{id}/metadata — OR — add new endpoint POST /api/agents/{id}/policy
  - Decision: add dedicated endpoint `POST /api/agents/{id}/policy` — contact_policy is a column, not metadata
- [ ] Add `GetContactPolicy(ctx) (string, error)` to interlock `client.Client`
  - HTTP: GET /api/agents/{id}/policy
- [ ] Add HTTP handlers in intermute `handlers_agents.go`:
  - `handleAgentPolicy` for GET/POST on `/api/agents/{id}/policy`
- [ ] Add route in `router_domain.go` for `/api/agents/{id}/policy`
- [ ] Register MCP tools in interlock `tools.go`:
  - `set_contact_policy` tool: params `policy` (required, enum: open|auto|contacts_only|block_all)
  - `get_contact_policy` tool: no params, returns current policy
- [ ] Update `RegisterAll` to add the two new tools (14 total)

## Task 7: Tests

- [ ] Unit tests in `core/intermute/internal/storage/sqlite/`:
  - Test `SetContactPolicy` + `GetContactPolicy` round-trip
  - Test `AddContact`, `RemoveContact`, `ListContacts`, `IsContact`
  - Test `HasReservationOverlap` with overlapping and non-overlapping patterns
  - Test `IsThreadParticipant`
- [ ] Integration test for policy enforcement in `handleSendMessage`:
  - `open` policy: message delivered
  - `block_all` policy: HTTP 403
  - `contacts_only` + not a contact: denied
  - `contacts_only` + is a contact: allowed
  - `contacts_only` + thread participant: allowed
  - `auto` + reservation overlap: allowed
  - `auto` + no overlap, not contact: denied
  - Partial delivery: 2 recipients, one open, one block_all → message to open, denied for block_all
- [ ] Run `go test -race ./...` in intermute
- [ ] Run `go test ./...` in interlock

## Task 8: Documentation and close

- [ ] Update `core/intermute/AGENTS.md` with contact policy section
- [ ] Update `interverse/interlock/AGENTS.md` with new tools
- [ ] Commit in intermute, interlock, Demarch root
- [ ] Close iv-t4pia
- [ ] Push
