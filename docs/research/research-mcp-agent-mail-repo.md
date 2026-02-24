# MCP Agent Mail Research — Architecture & Protocol Analysis

**Date:** 2026-02-24  
**Project:** `/home/mk/projects/Demarch/research/mcp_agent_mail`  
**Status:** Production multi-agent coordination server (FastMCP + HTTP + SQLite + Git)

---

## 1. Architecture Overview

### High-Level Design

```
┌─────────────────────────────────┐         ┌───────────────────────────┐
│ Coding Agents (Claude, Codex,   │  HTTP   │ mcp-agent-mail            │
│ Gemini, etc.)                   ├────────>│ FastMCP Server            │
│ • Call MCP tools                │         │ (Streamable HTTP only)    │
│ • Pull messages on demand       │         │ Transport: Streamable     │
└─────────────────────────────────┘         └───────────┬───────────────┘
                                                        │
                                        writes/reads/indexes
                                                        │
                            ┌───────────────────────────┼──────────────────┐
                            │                           │                  │
                    ┌───────v────────┐    ┌────────────v─────┐   ┌────────v───────┐
                    │ Per-Project     │    │ SQLite Database  │   │ Filesystem     │
                    │ Git Repos       │    │ (FTS5 indexing)  │   │ Archive        │
                    │ .mcp-mail/      │    │                  │   │ (messages/     │
                    │ ├─ agents/      │    │ • projects       │   │  agents/       │
                    │ ├─ messages/    │    │ • agents         │   │  files/)       │
                    │ ├─ file_        │    │ • messages       │   │                │
                    │ │ reservations/ │    │ • message_       │   │                │
                    │ └─ ...          │    │   recipients     │   │                │
                    └────────────────┘    │ • file_          │   └────────────────┘
                                          │   reservations   │
                                          │ • agent_links    │
                                          │ • contact_policy │
                                          └──────────────────┘
```

### Entry Points & Modules

**Core Python package:** `/home/mk/projects/Demarch/research/mcp_agent_mail/src/mcp_agent_mail/`

| Module | LoC | Purpose |
|--------|-----|---------|
| `app.py` | 11,382 | Main FastMCP application; 40+ async tool handlers; orchestrates messaging, identity, coordination |
| `storage.py` | 3,236 | Git archive operations; per-project file locking; commit queuing (batches for perf); attachment handling |
| `db.py` | 834 | SQLite async engine; connection pooling (WAL mode); circuit breaker pattern; schema setup |
| `models.py` | 210 | SQLModel definitions (Project, Agent, Message, FileReservation, AgentLink, WindowIdentity, etc.) |
| `config.py` | 486 | Settings via python-decouple; HttpSettings, DatabaseSettings, StorageSettings, LLM config |
| `cli.py` | 4,738 | Developer tooling: init, serve, debug, export, share, signing |
| `http.py` | 3,608 | Uvicorn/ASGI app wrapper; JWT/RBAC middleware; request logging |
| `llm.py` | 256 | LLM integration (LiteLLM); message summarization |
| `guard.py` | 716 | Pre-commit hook for file reservation enforcement (bash) |
| `utils.py` | 233 | Agent name generation (adjective+noun); validation; slugification |
| `rich_logger.py` | 975 | Rich console logging with colors, panels, progress bars |

**Transport:** FastMCP 2.0 (HTTP Streamable only; STDIO/SSE not exposed)  
**Database:** SQLite + aiosqlite + SQLModel ORM; WAL mode; FTS5 for message search  
**Storage:** Git repos per project; .mcp-mail/ subdirectory tree with messages/agents/files/  
**Concurrency:** asyncio; per-project file locks (SoftFileLock); async commit queue; circuit breaker

---

## 2. Core Protocol & Coordination Model

### Project Identity Model

**Projects are identified by absolute filesystem path (`human_key`).**

```python
# From app.py: ensure_project()
# CRITICAL RULE: Two agents in /data/projects/backend → SAME project
# /data/projects/backend vs /data/projects/frontend → DIFFERENT projects

Project model:
  - id: UUID (internal)
  - slug: Derived from human_key (lowercase, safe chars; stable/deterministic)
  - human_key: Absolute filesystem path (canonical identity)
  - created_at: ISO timestamp
  - archived_at: Optional (soft delete)
```

**Why:** Multiple agents working in the same directory coordinate via the same project; this naturally aligns with git repos and file-locking semantics.

### Agent Identity Model

Agents get **ephemeral but memorable identities** (adjective+noun, e.g., `GreenCastle`, `RedCat`).

```python
Agent model:
  - id: UUID (internal)
  - project_id: FK to Project
  - name: Memorable identifier (e.g., "GreenCastle")
  - program: Program name (e.g., "claude-code", "codex-cli", "gemini-cli")
  - model: Model identifier (e.g., "claude-opus-4-6", "gpt-5.1-codex")
  - task_description: Brief description of what this agent is doing
  - inception_ts: When agent was created
  - last_active_ts: Last tool call timestamp
  - attachments_policy: "inline" | "file" | "auto" (how to handle message attachments)
  - contact_policy: "open" | "auto" | "contacts_only" | "block_all" (who can message)
  - registration_token: Optional secret for secure agent handshake
  - retired_at: Optional (soft delete)
```

**Registration flow:**
1. `ensure_project(human_key)` — creates project (idempotent)
2. `register_agent(project_key, program, model, name=None)` → generates name if omitted, writes agents/<Name>/profile.json, commits
3. Agent now has identity; can send/receive messages, reserve files, coordinate

### Contact/Permission Model

**Agents are isolated by default.** Messaging between agents is opt-in via contact approval:

```python
AgentLink model (contact relationship):
  - a_project_id, a_agent_id: Requester (who wants to message)
  - b_project_id, b_agent_id: Target (who is being requested)
  - status: "pending" | "approved" | "blocked"
  - reason: Optional explanation
  - created_ts, expires_ts: TTL for pending requests (default 7 days)
  
contact_policy values:
  - "open": Anyone can message (no approval needed)
  - "auto": Default approval for known agents, approval for unknowns
  - "contacts_only": Only approved contacts can message
  - "block_all": No one can message (hard block)
```

**Workflow:**
1. Agent A calls `request_contact(from_agent=A, to_agent=B, reason="...")`
2. Creates AgentLink with status="pending"; sends intro message to B with `ack_required=true`
3. Agent B calls `respond_contact(accept=true)` to approve (or `accept=false` to deny)
4. Link status → "approved" or "blocked"; messaging is now allowed/denied

**Cross-project:** Agents can request contact across projects: `to_agent="project:slug#AgentName"`.

---

## 3. Messaging Protocol

### Message Model

```python
Message model:
  - id: Integer PK (auto-inc)
  - project_id: FK to Project
  - sender_id: FK to Agent
  - thread_id: Optional (groups related messages; format: alphanumeric, max 64 chars)
  - topic: Optional (topic tag for filtering; alphanumeric+hyphens, max 64 chars)
  - subject: Short title (visible in search, inbox listings)
  - body_md: GitHub-Flavored Markdown (links, code blocks, inline images)
  - importance: "low" | "normal" | "high" | "urgent" (user-facing metadata)
  - ack_required: Boolean (recipient must call acknowledge_message())
  - created_ts: ISO timestamp (UTC)
  - attachments: JSON array of attachment metadata (name, size, mime, hash)
  
MessageRecipient model (per-recipient state):
  - message_id: FK to Message
  - agent_id: FK to Agent
  - kind: "to" | "cc" | "bcc" (recipient type)
  - read_ts: Optional (when recipient marked as read)
  - ack_ts: Optional (when recipient acknowledged, if ack_required)
```

### Message Storage (Dual Persistence)

**On-disk layout per project (.mcp-mail/):**

```
messages/YYYY/MM/
  <message_id>.md           # Canonical message (YAML frontmatter + GFM body)

agents/<AgentName>/inbox/YYYY/MM/
  <message_id>.md           # Recipient mailbox copy (read-only reference)

agents/<AgentName>/outbox/YYYY/MM/
  <message_id>.md           # Sender archive copy

file_reservations/
  <sha1(path_pattern)>.json # File reservation artifacts

attachments/YYYY/MM/
  <hash>.<ext>              # Inline or attached media (WebP, original)
```

**Message YAML frontmatter:**

```yaml
---
id: "msg_20251023_7b3dc3a7"
thread_id: "TKT-123"
project: "backend-repo"
from: "GreenCastle"
to: ["RedCat", "BlueLake"]
cc: []
bcc: []
subject: "Initial design feedback"
importance: "normal"
ack_required: false
topic: "architecture"
created_ts: "2025-10-23T14:22:33Z"
attachments:
  - name: "diagram.webp"
    size: 45000
    mime: "image/webp"
    hash: "abc123def456"
---
[GFM body here]
```

### Threading & Topics

**Threading:** Messages can be grouped by optional `thread_id` (e.g., `"TKT-123"`, `"sprint-2025-02"`) for conversation context.

**Topics:** Messages can be tagged with `topic` (e.g., `"architecture"`, `"api-design"`) for filtering and discovery across agents.

**Both are user-defined strings (alphanumeric+hyphens); no predefined enums.**

---

## 4. MCP Tool Surface (40+ Tools)

### Tool Clusters (organized by capability)

| Cluster | Tools | Purpose |
|---------|-------|---------|
| **SETUP** | ensure_project | Create/ensure project exists from directory path |
| **IDENTITY** | register_agent, create_agent_identity, whois, list_window_identities, rename_window, expire_window | Agent creation, lookup, session management |
| **MESSAGING** | send_message, reply_message, fetch_inbox, fetch_topic, mark_message_read, acknowledge_message | Core message send/receive |
| **SEARCH** | search_messages | Full-text search (BM25) over subject + body |
| **SUMMARY** | summarize_thread, summarize_recent, fetch_summary | LLM-powered thread/project digests |
| **CONTACT** | request_contact, respond_contact, list_contacts, set_contact_policy | Cross-agent contact approval |
| **FILE_RESERVATIONS** | file_reservation_paths, release_file_reservations, force_release_file_reservation, renew_file_reservations | File locking for coordination |
| **MACROS** | macro_start_session, macro_prepare_thread, macro_file_reservation_cycle, macro_contact_handshake | Workflow helpers (compound operations) |
| **PRODUCT** (optional) | ensure_product, products_link, search_messages_product, fetch_inbox_product, summarize_thread_product | Multi-tenant workspaces (if enabled) |

### Key Tools (Detailed)

#### `ensure_project(human_key: str) → dict`

Creates or returns existing project from absolute directory path. **Idempotent.**

```python
# Creates .mcp-mail/ subdir in human_key if it doesn't exist
# Initializes git repo if needed
# Returns: { id, slug, human_key, created_at }
```

#### `register_agent(project_key, program, model, name=None, task_description="") → dict`

Registers or updates agent. If `name` is omitted, generates random adjective+noun name (e.g., "GreenCastle").

```python
# Writes agents/<Name>/profile.json to git
# Returns: { id, name, program, model, task_description, inception_ts, last_active_ts, project_id }
```

#### `send_message(project_key, sender_name, to, subject, body_md, cc=[], bcc=[], ack_required=False, thread_id=None, topic=None, broadcast=False, ...) → dict`

Sends message to one or more recipients.

```python
# Parameters:
#   - to/cc/bcc: List of agent names (or broadcast=True for all agents)
#   - topic: Optional tag for filtering (alphanumeric+hyphens)
#   - thread_id: Optional grouping (alphanumeric, max 64 chars)
#   - importance: "low" | "normal" | "high" | "urgent"
#   - ack_required: If true, recipient must call acknowledge_message()
#   - attachment_paths: Extra files to attach (auto-converted to WebP)
#   - convert_images: Override server default for image inlining
#   - broadcast: If true and to=[], send to all agents (respects contact_policy)
#   - auto_contact_if_blocked: If true, auto-request contact for blocked agents

# Returns:
#   { deliveries: [{ project, payload }], count: N }
```

**Respects contact_policy:** If recipient has contact_policy="block_all", send fails (or auto-requests contact if `auto_contact_if_blocked=true`).

#### `fetch_inbox(project_key, agent_name, since_ts=None, limit=20, urgent_only=False, topic=None, include_bodies=False) → list[dict]`

Polls inbox for unread/unacked messages.

```python
# Returns list of messages with: { id, subject, from, created_ts, importance, ack_required, kind, [body_md] }
# Filter by:
#   - since_ts: ISO timestamp (messages strictly newer than this)
#   - urgent_only: Only high/urgent importance
#   - topic: Only messages with this tag
#   - include_bodies: Include full Markdown body (saves context if false)
```

**Poll-based (not streaming).** Agents call this periodically to check for new messages.

#### `file_reservation_paths(project_key, agent_name, paths, ttl_seconds=3600, exclusive=True, reason="") → dict`

Request file reservations (advisory leases) on code repo files.

```python
# Parameters:
#   - paths: List of glob patterns relative to workspace (e.g., ["src/api/*.py", "config/settings.yaml"])
#   - ttl_seconds: Expiry time (minimum 60s)
#   - exclusive: True = exclusive intent (conflicts reported), False = shared/observe
#   - reason: Explanation for audit trail

# Returns:
#   {
#     granted: [{ id, path_pattern, exclusive, reason, expires_ts }],
#     conflicts: [{ path, holders: [...] }]
#   }

# Semantics:
#   - Glob matching is symmetric (fnmatchcase bidirectional)
#   - Conflicts reported if overlapping exclusive reservation exists from another agent
#   - Artifacts written to file_reservations/<sha1>.json in git
#   - Server enforces on .mcp-mail/ paths; code repo enforcement via pre-commit hook
```

#### `release_file_reservations(project_key, agent_name, file_reservation_ids=None, paths=None) → dict`

Release active reservations.

```python
# If both ids and paths are omitted: release ALL active reservations
# Returns: { released: N, released_at: timestamp }
```

#### `request_contact(project_key, from_agent, to_agent, to_project=None, reason="", ttl_seconds=604800, register_if_missing=True) → dict`

Request contact approval to message another agent.

```python
# Sends intro message with ack_required=true
# Creates AgentLink with status="pending"
# If register_if_missing=true and target agent doesn't exist, creates it (best effort)

# Cross-project: to_agent can be "project:slug#AgentName" or use to_project parameter
```

#### `respond_contact(project_key, to_agent, from_agent, accept: bool, ttl_seconds=2592000) → dict`

Approve or deny contact request.

```python
# If accept=true: AgentLink status → "approved"
# If accept=false: AgentLink status → "blocked"
```

#### `search_messages(project_key, query: str, limit=20) → list[dict]`

Full-text search over messages (subject + body).

```python
# Uses SQLite FTS5 with BM25 ranking
# Query syntax: "phrase", prefix*, boolean (AND/OR)
# Returns: [{ id, subject, importance, ack_required, created_ts, thread_id, from }]
```

#### `summarize_thread(project_key, thread_id, include_examples=False, llm_mode=True) → dict`

Summarize a thread or multiple threads (aggregate).

```python
# Single thread: detailed summary with participants, key points, action items
# Multi-thread (comma-separated IDs): aggregate digest across threads
#
# If llm_mode=true: Uses LLM to refine summary (LiteLLM via config)
# Returns: { thread_id, summary: { participants, key_points, action_items }, examples [...] }
```

#### `list_contacts(project_key, agent_name) → dict`

List all contact links (approved, pending, blocked).

```python
# Returns contact relationships for the agent
```

---

## 5. State Management & Database

### SQLite Schema (Key Tables)

**Projects table:**
```sql
CREATE TABLE projects (
  id UUID PRIMARY KEY,
  slug VARCHAR UNIQUE NOT NULL,         -- Derived from human_key
  human_key VARCHAR UNIQUE NOT NULL,    -- Absolute directory path
  created_at DATETIME NOT NULL,
  archived_at DATETIME                  -- Soft delete
);
```

**Agents table:**
```sql
CREATE TABLE agents (
  id UUID PRIMARY KEY,
  project_id UUID NOT NULL,
  name VARCHAR NOT NULL,                -- e.g., "GreenCastle"
  program VARCHAR,                      -- e.g., "claude-code"
  model VARCHAR,                        -- e.g., "claude-opus-4-6"
  task_description VARCHAR,
  inception_ts DATETIME,
  last_active_ts DATETIME,              -- Updated on each tool call
  attachments_policy VARCHAR,           -- "inline" | "file" | "auto"
  contact_policy VARCHAR,               -- "open" | "auto" | "contacts_only" | "block_all"
  registration_token VARCHAR,
  retired_at DATETIME,
  UNIQUE(project_id, name)
);
```

**Messages table:**
```sql
CREATE TABLE messages (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  project_id UUID NOT NULL,
  sender_id UUID NOT NULL,
  thread_id VARCHAR,                    -- Optional thread grouping
  topic VARCHAR,                        -- Optional topic tag
  subject VARCHAR NOT NULL,
  body_md TEXT,                         -- GFM markdown
  importance VARCHAR,                   -- "low", "normal", "high", "urgent"
  ack_required BOOLEAN,
  created_ts DATETIME,
  attachments JSON                      -- Array of attachment metadata
);
```

**MessageRecipient table (per-recipient state):**
```sql
CREATE TABLE message_recipients (
  message_id INTEGER,
  agent_id UUID,
  kind VARCHAR,                         -- "to", "cc", "bcc"
  read_ts DATETIME,                     -- When marked read
  ack_ts DATETIME,                      -- When acknowledged
  PRIMARY KEY(message_id, agent_id, kind)
);
```

**FileReservation table:**
```sql
CREATE TABLE file_reservations (
  id UUID PRIMARY KEY,
  project_id UUID NOT NULL,
  agent_id UUID NOT NULL,
  path_pattern VARCHAR,                 -- Glob pattern (e.g., "src/**/*.py")
  exclusive BOOLEAN,                    -- True = exclusive, False = shared
  reason VARCHAR,                       -- Explanation for audit
  created_ts DATETIME,
  expires_ts DATETIME,                  -- TTL expiry
  released_ts DATETIME,                 -- When manually released
  UNIQUE(project_id, agent_id, path_pattern)
);
```

**AgentLink table (contact relationships):**
```sql
CREATE TABLE agent_links (
  id UUID PRIMARY KEY,
  a_project_id UUID,
  a_agent_id UUID,                      -- Requester
  b_project_id UUID,
  b_agent_id UUID,                      -- Target
  status VARCHAR,                       -- "pending" | "approved" | "blocked"
  reason VARCHAR,
  created_ts DATETIME,
  updated_ts DATETIME,
  expires_ts DATETIME                   -- TTL for pending
);
```

**FTS5 Virtual Table (for search):**
```sql
CREATE VIRTUAL TABLE fts_messages USING fts5(
  message_id UNINDEXED,
  subject,
  body,
  content=messages,
  content_rowid=id
);
```

Triggers keep FTS index in sync with messages table.

### Concurrency & Locking

**Database (SQLite):**
- WAL (Write-Ahead Logging) mode enabled for concurrent readers
- `max_connections`: Conservative pool size to prevent FD exhaustion
- `busy_timeout`: 60s gives writers time to complete during checkpoint
- Circuit breaker pattern: After 5 failures, fast-fail for 30s (prevents thundering herd)

**Archive (Git operations):**
- Per-project `.archive.lock` (SoftFileLock, cross-platform, doesn't require OS support)
- Per-project `.commit.lock` (serializes git commits)
- Commit queue with batching: Non-conflicting commits batched together to reduce lock contention
- Lock metadata (`.owner.json`) enables stale lock detection & cleanup
- Exponential backoff + jitter on transient failures (git index.lock handling)

**In-process (Python):**
- `asyncio.Lock` per project prevents re-entrant lock acquisition within same process
- Async contexts guarantee no blocking threads

---

## 6. Concurrency & Conflict Resolution

### File Reservation Conflict Detection

**Glob matching:** Symmetric (`fnmatchcase(a,b)` OR `fnmatchcase(b,a)`). Examples:

```
Agent A reserves "src/api/*.py"
Agent B reserves "src/api/users.py"
→ Conflict! (users.py matches api/*.py)

Agent A reserves "src/**"
Agent B reserves "config/**"
→ No conflict (different trees)
```

**Advisory, not enforced within MCP:** Reservations are advisory at the MCP tool level. Agents are expected to honor them. If violated:
- Pre-commit hook in code repo detects and rejects commits touching reserved files
- Server logs violations in audit trail

### Stale Lock Cleanup

- Locks include metadata (process ID, timestamp)
- When acquiring a lock, server checks if holder's last activity > TTL; if so, cleans up stale lock
- Explicit `force_release_file_reservation(reservation_id)` allows overriding stale holds (with optional notification to previous holder)

---

## 7. Identity & Session Management

### Agent Lifecycle

1. **Creation:** `register_agent()` or `create_agent_identity()` (latter always creates new with fresh name)
   - Agent name is **memorable** (adjective+noun, e.g., GreenCastle, RedCat, BlueStone)
   - Bound to program/model pair and project
   - `inception_ts` set at creation
   - `last_active_ts` updated on each tool call

2. **Active Use:** Agent polls inbox, sends messages, coordinates via file reservations

3. **Retirement:** `retired_at` set when agent is no longer active (soft delete; not removed from history)

### Window Identities (Session Tracking)

For terminal/browser sessions (tmux panes, browser windows), optional lightweight tracking:

```python
WindowIdentity model:
  - window_uuid: Persistent session identifier
  - display_name: Human-friendly name (e.g., "pane-1", "claude-code-backend")
  - created_ts, last_active_ts: Lifecycle
  - expires_ts: Auto-cleanup TTL
```

Tools: `list_window_identities()`, `rename_window()`, `expire_window()`

---

## 8. Attachment & Image Handling

### Inline vs File Storage

**Attachment policy (per agent):**
- `"inline"`: Small images (<50KB) embedded as base64; large images as separate files
- `"file"`: All images stored separately
- `"auto"`: Server default (typically inline for small, file for large)

### Image Processing

- Images auto-converted to **WebP** (reduces size by ~60-80%)
- Original optionally kept (configurable)
- Inline images in markdown: `![alt](path)` or `![alt](data:image/webp;base64,...)`
- Attachment metadata stored in message JSON: `[{ name, size, mime, hash }]`

---

## 9. Project Archive Structure

### On-Disk Layout

```
<workspace>/.mcp-mail/
├── .git/                              # Git repo for all archive data
│
├── agents/
│   ├── GreenCastle/
│   │   ├── profile.json               # Agent metadata (program, model, task, etc.)
│   │   ├── inbox/YYYY/MM/
│   │   │   └── <msg_id>.md            # Messages received
│   │   └── outbox/YYYY/MM/
│   │       └── <msg_id>.md            # Messages sent
│   │
│   └── RedCat/
│       └── ...
│
├── messages/YYYY/MM/
│   └── <msg_id>.md                    # Canonical message (master copy)
│
├── file_reservations/
│   ├── <sha1(path1)>.json             # Reservation artifact
│   ├── <sha1(path2)>.json
│   └── ...
│
├── attachments/YYYY/MM/
│   ├── <hash>.webp                    # Processed images
│   ├── <hash>.orig                    # Original (if kept)
│   └── ...
│
├── .archive.lock                      # Lock file for concurrent access
└── .owner.json                        # Lock metadata (PID, timestamp)
```

**Git commits:** Each message send, file reservation, or agent action creates a commit (tagged by tool cluster).

---

## 10. API & Configuration

### Environment Variables (`.env`)

**Database:**
- `DATABASE_URL`: SQLite path or connection string
- `DATABASE_ECHO`: SQL logging (true/false)
- `DATABASE_POOL_SIZE`, `DATABASE_MAX_OVERFLOW`: Connection pool tuning

**HTTP Server:**
- `HTTP_HOST`: Bind address (default: 127.0.0.1)
- `HTTP_PORT`: Port (default: 8000)
- `HTTP_BEARER_TOKEN`: Optional Bearer auth
- `JWT_ENABLED`, `JWT_SECRET`, `JWT_JWKS_URL`: JWT auth (optional)

**Storage:**
- `STORAGE_ROOT`: Filesystem root for .mcp-mail/ repos (default: ~/.mcp-mail)
- `GIT_AUTHOR_NAME`, `GIT_AUTHOR_EMAIL`: Git identity for commits
- `INLINE_IMAGE_MAX_BYTES`: Threshold for WebP inlining (default: 50000)

**Messaging:**
- `LLM_ENABLED`: Enable LLM summarization (default: false)
- `LLM_DEFAULT_MODEL`: Model for summaries (e.g., "claude-opus-4-6")
- `LLM_CACHE_BACKEND`: "memory" or "redis"

**Tool Filtering:**
- `TOOLS_FILTER_ENABLED`: Expose subset of tools (default: false)
- `TOOLS_FILTER_PROFILE`: "full" | "core" | "minimal" | "messaging" | "custom"
- `TOOLS_FILTER_CLUSTERS`: Cluster names to include/exclude

---

## 11. Error Handling & Resilience

### Error Types

**ToolExecutionError** with structured types:
- `NOT_FOUND`: Agent/project/message not found
- `CONFLICT`: File reservation conflict; contact already exists
- `PERMISSION_DENIED`: Contact policy violation; insufficient capabilities
- `INVALID_INPUT`: Malformed parameters (thread_id, path patterns, etc.)
- `UNAVAILABLE`: Circuit breaker open; database unreachable
- `INTERNAL`: Unexpected server error

**Recoverable flag:** Set to true if caller can retry (transient failure).

### Retry Strategy

- Database locks: Exponential backoff (0.1s → 8s, max 7 retries)
- Git index.lock: Retry + stale cleanup
- Circuit breaker: Fail fast after 5 consecutive failures, half-open after 30s

---

## 12. Key Design Decisions & Trade-offs

### Why Git + SQLite (Dual Persistence)?

1. **Git provides:**
   - Auditable history (who did what, when)
   - Diffing & blame for messages/reservations
   - Offline-capable (local clones)
   - Familiar UX (agents can `git log` or view in editor)

2. **SQLite provides:**
   - Efficient indexing (FTS5 for search)
   - Relational queries (thread summaries, contact graphs)
   - Atomic transactions (ACID)
   - Lightweight (single file, no server)

### Why Memorable Agent Names (not UUIDs)?

1. **Adjective+noun is human-readable:** Easier to reference in messages, logs, UI
2. **Ephemeral:** Not bound to human identity; can be regenerated
3. **Prevents confusion:** A UUID looks like a bug; "GreenCastle" is intentional
4. **Unique per project:** Collisions rare; format allows validation

### Why Contact Approval?

1. **Privacy/isolation by default:** Agents don't accept unsolicited messages
2. **Explicit handshake:** Reveals agent existence; can be private
3. **Spam prevention:** Malicious agents can't flood innocent ones
4. **TTL:** Pending requests expire; can be revisited

### Why File Reservations (Advisory)?

1. **Voluntary coordination:** Agents choose to respect leases; not OS-level locks
2. **Graceful degradation:** If an agent ignores a reservation, it's detectable (pre-commit hook)
3. **Low overhead:** No kernel calls; just database rows
4. **Git-aware:** Artifacts are versioned & auditable

---

## 13. Known Limitations & Future Work

### Current Constraints

1. **SQLite single-writer:** Under very high concurrency, lock contention possible (mitigated by commit queue)
2. **Message ordering:** Within a thread, ordering is by creation timestamp (not strict happens-before)
3. **No encryption:** Messages stored in plaintext; encryption at rest not yet implemented
4. **No message expiry:** Messages archived forever (manual cleanup only)
5. **Contact links are unidirectional:** A→B approval doesn't imply B→A

### Optional Features (Conditional Code)

- **Product-level scope:** If `worktrees_enabled=true`, additional tools for multi-workspace coordination
- **Build slot management:** Conditional tools for CI resource coordination
- **Custom tool filtering:** Reduce tool set for minimal clients

---

## 14. Integration Points & Extensibility

### For New AI Agent Frameworks

1. **HTTP endpoint:** POST to `/mcp/` with JSON-RPC 2.0 request
2. **MCP client library:** Use official MCP client (TypeScript, Python, Go)
3. **Tool discovery:** Call `tools/list` to enumerate available tools
4. **Auth:** Bearer token or JWT (if enabled)

### For Custom Tools

1. **Hook into FastMCP:** Use `@mcp.tool()` decorator in app.py
2. **Leverage existing models:** Import from models.py; query via db.get_session()
3. **Persist to git:** Use storage.write_message_bundle(), write_file_reservation_records()
4. **Update last_active_ts:** Call _record_recent(tool_name, project, agent)

---

## 15. Testing & Quality

### Test Coverage

- **Seam tests** (shell/BATS): Integration tests with real database, git repos
- **Unit tests:** Database models, FTS queries, lock handling
- **E2E tests:** Full message lifecycle (send → receive → search → summarize)
- **Benchmarks:** Baseline metrics (message latency, search throughput, commit queue stats)

### Quality Gates

- **Pre-commit hook** (`guard.sh`): Checks file reservations before git commits
- **Type checking:** Mypy/Pyright on models, app.py
- **Linting:** Ruff (flake8 + isort + pyupgrade)
- **Instrumentation:** Tool metrics tracking (requests, errors, latency by cluster)

---

## Summary

**MCP Agent Mail** is a production-ready multi-agent coordination platform built on FastMCP (HTTP), SQLite (FTS5), and Git. It provides:

1. **Identity:** Ephemeral memorable names (adjective+noun) bound to program/model pairs
2. **Messaging:** GFM markdown with threading, topics, importance, and ack semantics
3. **Contact:** Approval workflow to prevent spam; respects agent privacy preferences
4. **Coordination:** File reservations (glob-matched, TTL-based) for avoiding conflicts
5. **Search:** Full-text indexing with BM25 ranking; thread summarization via LLM
6. **Audit:** Git history for all messages, reservations, agent actions
7. **Resilience:** Circuit breaker, exponential backoff, stale lock cleanup
8. **Extensibility:** FastMCP hooks allow custom tools; dual persistence (Git + SQLite) enables rich queries

All agent interactions are **asynchronous, poll-based, and opt-in** — fitting naturally into headless CLI workflows.

