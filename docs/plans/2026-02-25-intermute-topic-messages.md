# Plan: Intermute Topic-Based Message Categorization

**Bead:** iv-00liv
**Complexity:** 2/5 (simple)
**Scope:** core/intermute + interverse/interlock

## Context

Intermute currently has recipient-based routing only. An agent joining a project mid-sprint cannot find relevant conversation threads unless explicitly added as a recipient. This adds a `topic` field to messages so late-joining or oversight agents can discover conversations by topic.

Builds on iv-t4pia (contact policies) which just shipped — same files, same patterns.

## Tasks

### Task 1: Add Topic field to Message model
**Files:** `internal/core/models.go`
- Add `Topic string` field to `Message` struct (after `Subject`)
- No new types needed — topics are free-form strings

### Task 2: Schema migration — add topic column + index
**Files:** `internal/storage/sqlite/schema.sql`, `internal/storage/sqlite/sqlite.go`
- Add `topic TEXT` column to `messages` table in schema.sql
- Add `CREATE INDEX idx_messages_project_topic ON messages(project, topic)` composite index
- Add `migrateTopicColumn()` function in sqlite.go: `ALTER TABLE messages ADD COLUMN topic TEXT DEFAULT ''`
- Create the index in migration too
- Call from `initSchema()` after existing migrations

### Task 3: Update Store interface + InMemory stubs
**Files:** `internal/storage/storage.go`
- Add `TopicMessages(ctx context.Context, project, topic string, cursor uint64, limit int) ([]core.Message, error)` to Store interface
- Add InMemory implementation (filter by topic from existing messages)

### Task 4: SQLite store implementation
**Files:** `internal/storage/sqlite/sqlite.go`, `internal/storage/sqlite/resilient.go`
- Update `AppendEvent` INSERT to include `topic` column
- Update all message SELECT queries to read `topic` column
- Lowercase topic at write time (`strings.ToLower`) — NOT at query time (fd-performance lesson)
- Implement `TopicMessages()` — SELECT from messages WHERE project=? AND topic=? AND cursor>? ORDER BY rowid LIMIT ?
- Add `ResilientStore.TopicMessages()` wrapper (CircuitBreaker + RetryOnDBLock)

### Task 5: HTTP layer — accept topic on send, add topic query endpoint
**Files:** `internal/http/handlers_messages.go`, `internal/http/service.go`
- Add `Topic string` to `sendMessageRequest` and `apiMessage` structs
- Pass `req.Topic` (lowercased) through to `msg.Topic` in `handleSendMessage`
- Add `handleTopicMessages()` handler — GET `/api/topics/{project}/{topic}` with `since_cursor` and `limit` query params
- Register route in service.go

### Task 6: Interlock MCP tools — update send_message + add list_topic_messages
**Files:** `interverse/interlock/internal/tools/tools.go`, `interverse/interlock/internal/client/client.go`
- Add optional `topic` parameter to existing `send_message` tool schema
- Pass topic through in client `SendMessage` request
- Add `list_topic_messages` MCP tool: params (project, topic, since_cursor, limit)
- Add `TopicMessages()` client method calling GET `/api/topics/{project}/{topic}`
- Update tool count comment (14 → 15 tools)

### Task 7: Tests
**Files:** `internal/storage/sqlite/topic_test.go`
- `TestTopicMessages_SendAndQuery` — send messages with topics, query by topic, verify cursor pagination
- `TestTopicMessages_CaseNormalization` — send with "BUILD" topic, query with "build", verify match
- `TestTopicMessages_NoTopic` — messages without topic don't appear in topic queries
- `TestTopicMessages_CrossProject` — topics are project-scoped, don't leak across projects

## Dependency Chain
Task 1 → Task 2 → Task 3 → Task 4 → Task 5 → Task 6 (sequential, each builds on prior)
Task 7 can run after Task 4.

## Risk Assessment
- **Low risk.** Same mechanical pattern as contact policies (column add, migration, store method, handler, MCP tool).
- **One nuance:** Lowercasing at write time means existing messages (before migration) have no topic. The migration defaults to empty string, and queries for empty topic should return nothing (not all messages).
