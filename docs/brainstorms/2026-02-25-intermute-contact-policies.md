# Brainstorm: Intermute Contact Policies — 4-Level Access Control

**Bead:** iv-t4pia
**Date:** 2026-02-25
**Status:** Brainstorm

## Problem

Intermute's messaging bus is currently open — any registered agent can send messages to any other agent in the same project. As the number of agents grows (fleet dispatches, multi-session coordination), agents need the ability to control who can message them.

The mcp-agent-mail reference implementation has contact policies but with a critical flaw: `reply_message` bypasses policy for local recipients (fd-safety F2). Demarch must enforce uniformly on ALL delivery paths.

## Design: Four Policy Levels

| Level | Behavior | Use case |
|---|---|---|
| `open` | Accept from anyone (default) | Most agents, backward compatible |
| `auto` | Auto-allow agents with overlapping file reservations | Collaborators on shared files |
| `contacts_only` | Explicit whitelist only | Sensitive agents (e.g., deployer) |
| `block_all` | Reject everything | Agent in shutdown/maintenance |

## Architecture Decisions

### 1. Enforcement at the HTTP layer (not MCP)

Policy enforcement belongs in `handleSendMessage()` in intermute, NOT in the interlock MCP tools. Reasons:
- Intermute is the single delivery path — ALL messages go through `POST /api/messages`
- Interlock's `send_message` tool is just one client; Go SDK `client.SendMessage()` is another
- The negotiation tools (`negotiate_release`, `respond_to_release`) also send messages via the client
- Enforcing at HTTP guarantees no bypass path exists (the mcp-agent-mail anti-pattern)

### 2. Contact policy stored on agents table

Add `contact_policy TEXT NOT NULL DEFAULT 'open'` to the `agents` table. This is a column, not metadata — it's load-bearing for delivery decisions.

For `contacts_only`, maintain a separate `agent_contacts` table (not a JSON array in metadata) so lookups are indexed.

### 3. Thread-participant exception

Replies within existing threads bypass `contacts_only` (but NOT `block_all`). This is natural — if you're already in a conversation, you should be able to reply. Implementation: check if sender appears in `thread_index` for the message's `thread_id`.

### 4. Auto-allow via file reservation overlap

The `auto` policy allows messages from agents who share file reservations in the same project. This uses the existing `file_reservations` table — check if both sender and recipient have active (non-expired, non-released) reservations with overlapping glob patterns. The `internal/glob/overlap.go` already has `Overlap()` function.

### 5. New Store methods

```go
// Contact policy
SetContactPolicy(ctx context.Context, agentID string, policy string) error
GetContactPolicy(ctx context.Context, agentID string) (string, error)

// Contact list (for contacts_only policy)
AddContact(ctx context.Context, agentID, contactAgentID string) error
RemoveContact(ctx context.Context, agentID, contactAgentID string) error
ListContacts(ctx context.Context, agentID string) ([]string, error)
IsContact(ctx context.Context, agentID, senderID string) (bool, error)

// Auto-allow check
HasReservationOverlap(ctx context.Context, project, agentA, agentB string) (bool, error)
```

### 6. Enforcement flow in handleSendMessage

```
for each recipient in msg.To + msg.CC + msg.BCC:
  policy = GetContactPolicy(recipient)
  switch policy:
    case "open": allow
    case "block_all": reject (HTTP 403, per-recipient)
    case "contacts_only":
      if IsContact(recipient, msg.From): allow
      elif msg.ThreadID != "" && isThreadParticipant(recipient, msg.From, msg.ThreadID): allow
      else: reject
    case "auto":
      if HasReservationOverlap(project, recipient, msg.From): allow
      elif IsContact(recipient, msg.From): allow
      elif msg.ThreadID != "" && isThreadParticipant(recipient, msg.From, msg.ThreadID): allow
      else: reject
```

**Partial delivery**: If a message has multiple recipients and some reject, the message is delivered to accepting recipients. Rejected recipients are returned in the response (not silently dropped).

### 7. MCP tools (in interlock)

Two new tools:
- `set_contact_policy` — set own policy level (open|auto|contacts_only|block_all)
- `get_contact_policy` — read own policy level

Contact management via metadata for now (add_contact/remove_contact can be future tools if needed). Initial launch: agents set their policy, the auto-allow heuristic handles most collaboration cases.

### 8. Schema migration

Add column to agents: `ALTER TABLE agents ADD COLUMN contact_policy TEXT NOT NULL DEFAULT 'open'`

New table:
```sql
CREATE TABLE IF NOT EXISTS agent_contacts (
  agent_id TEXT NOT NULL,
  contact_agent_id TEXT NOT NULL,
  created_at TEXT NOT NULL,
  PRIMARY KEY (agent_id, contact_agent_id)
);
```

## Scope Cuts

- **No contact request/approval flow** — agents can add contacts directly (trust the agent)
- **No per-project policies** — policy is per-agent globally (simplifies model)
- **No rate limiting** — separate concern, separate bead
- **No message rejection notifications** — sender gets error response, no async notification to recipient

## Risk

- **Performance**: Policy check adds 1-2 SQLite queries per recipient per message. For typical messages (1-3 recipients), this is negligible. For broadcast (many recipients), could add latency — but broadcast is a separate feature (iv-7kg37).
- **Backward compatibility**: Default is `open`, so all existing agents behave identically. Zero migration risk.
- **Auto-allow accuracy**: File reservation overlap is a heuristic. Two agents reserving `*.go` and `pkg/*.go` overlap, but they may not be collaborating on the same feature. Acceptable for initial launch — auto is opt-in.
