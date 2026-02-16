# Interstat Token Benchmarking — Implementation Plan
**Phase:** planned (as of 2026-02-16T03:55:17Z)

> **For Claude:** REQUIRED SUB-SKILL: Use clavain:executing-plans to implement this plan task-by-task.

**Goal:** Build the `interstat` Claude Code plugin that measures actual token consumption across agent workflows, answering: is p99 context < 120K tokens?

**Architecture:** PostToolUse:Task hook captures real-time events (agent name, wall clock, result length) into SQLite. A Python JSONL parser backfills actual token counts from Claude Code's conversation JSONL files (each subagent has its own `.jsonl` file — no correlation needed). Built-in SQL views answer the decision gate.

**Tech Stack:** Bash (hooks), Python + uv (JSONL parser), SQLite3, jq

**Critical Review Fixes Incorporated:**
- SQLITE_BUSY: `busy_timeout=5000` + fallback JSONL (fd-correctness Issue 1.1)
- Schema simplified to ~10 columns (fd-architecture recommendation)
- Per-session transactions in parser (fd-correctness Issue 5.1)
- Only parse completed sessions (fd-correctness Issue 5.2)
- WAL mode + `PRAGMA user_version` for migrations (fd-correctness Issues 6.1, 6.2)
- JSONL token data confirmed in `assistant` type entries at `.message.usage` (fd-architecture blocker RESOLVED)
- Each subagent has own JSONL file — no timestamp correlation needed (fd-correctness Issue 2.1 RESOLVED)

---

### Task 1: Plugin Scaffold

**Files:**
- Create: `plugins/interstat/.claude-plugin/plugin.json`
- Create: `plugins/interstat/hooks/hooks.json`
- Create: `plugins/interstat/scripts/init-db.sh`
- Create: `plugins/interstat/.gitignore`
- Create: `plugins/interstat/CLAUDE.md`

**Step 1: Create directory structure**

```bash
mkdir -p plugins/interstat/.claude-plugin plugins/interstat/hooks plugins/interstat/scripts plugins/interstat/skills
```

**Step 2: Write plugin.json**

```json
{
  "name": "interstat",
  "version": "0.1.0",
  "description": "Token efficiency benchmarking for agent workflows",
  "author": "MK",
  "hooks": "./hooks/hooks.json",
  "skills": [
    "./skills/report.md",
    "./skills/status.md",
    "./skills/analyze.md"
  ]
}
```

**Step 3: Write hooks.json (empty for now — hooks added in Task 3)**

```json
{
  "hooks": {}
}
```

**Step 4: Write init-db.sh**

This is the SQLite schema initialization script. Must be idempotent.

```bash
#!/usr/bin/env bash
# Idempotent SQLite schema creation for interstat
set -euo pipefail

DB_DIR="${HOME}/.claude/interstat"
DB="${DB_DIR}/metrics.db"

mkdir -p "$DB_DIR"

sqlite3 "$DB" <<'SQL'
PRAGMA journal_mode=WAL;
PRAGMA busy_timeout=5000;

-- Schema version tracking
-- Version 1: initial schema

CREATE TABLE IF NOT EXISTS agent_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,
    session_id TEXT NOT NULL,
    agent_name TEXT NOT NULL,
    invocation_id TEXT,
    wall_clock_ms INTEGER,
    result_length INTEGER,
    input_tokens INTEGER,
    output_tokens INTEGER,
    cache_read_tokens INTEGER,
    cache_creation_tokens INTEGER,
    total_tokens INTEGER,
    model TEXT,
    parsed_at TEXT
);

CREATE INDEX IF NOT EXISTS idx_agent_runs_session ON agent_runs(session_id);
CREATE INDEX IF NOT EXISTS idx_agent_runs_agent ON agent_runs(agent_name);
CREATE INDEX IF NOT EXISTS idx_agent_runs_timestamp ON agent_runs(timestamp);

-- Agent-level summary: average tokens, runs, efficiency
CREATE VIEW IF NOT EXISTS v_agent_summary AS
SELECT
    agent_name,
    COUNT(*) as runs,
    ROUND(AVG(input_tokens)) as avg_input,
    ROUND(AVG(output_tokens)) as avg_output,
    ROUND(AVG(total_tokens)) as avg_total,
    ROUND(AVG(wall_clock_ms)) as avg_wall_ms,
    ROUND(AVG(cache_read_tokens)) as avg_cache_read,
    model
FROM agent_runs
WHERE total_tokens IS NOT NULL
GROUP BY agent_name, model;

-- Invocation-level summary: total tokens for parallel agent groups
CREATE VIEW IF NOT EXISTS v_invocation_summary AS
SELECT
    invocation_id,
    session_id,
    MIN(timestamp) as started,
    COUNT(*) as agent_count,
    SUM(input_tokens) as total_input,
    SUM(output_tokens) as total_output,
    SUM(total_tokens) as total_tokens,
    MAX(wall_clock_ms) as wall_clock_ms
FROM agent_runs
WHERE invocation_id IS NOT NULL
GROUP BY invocation_id;

PRAGMA user_version = 1;
SQL

echo "interstat: database initialized at $DB"
```

**Step 5: Write .gitignore**

```
*.db
*.db-wal
*.db-shm
__pycache__/
.venv/
```

**Step 6: Write CLAUDE.md**

Minimal project doc for context.

**Step 7: Run init-db.sh to verify**

Run: `bash plugins/interstat/scripts/init-db.sh`
Expected: "interstat: database initialized at ~/.claude/interstat/metrics.db"

**Step 8: Verify schema**

Run: `sqlite3 ~/.claude/interstat/metrics.db ".schema"`
Expected: Shows `agent_runs` table, 3 indexes, 2 views.

Run: `sqlite3 ~/.claude/interstat/metrics.db "PRAGMA user_version"`
Expected: `1`

**Step 9: Run init-db.sh again (idempotency check)**

Run: `bash plugins/interstat/scripts/init-db.sh`
Expected: Succeeds without errors. Same schema.

**Step 10: Commit**

```bash
git add plugins/interstat/
git commit -m "feat(interstat): plugin scaffold with SQLite schema (F0)"
```

---

### Task 2: Write Failing Tests for PostToolUse Hook

**Files:**
- Create: `plugins/interstat/tests/test-hook.bats`

**Step 1: Install bats-core if needed**

Run: `which bats || (git clone https://github.com/bats-core/bats-core.git /tmp/bats-core && /tmp/bats-core/install.sh /usr/local)`

**Step 2: Write test file**

Write BATS tests that verify the hook's behavior. Tests should cover:

1. **Basic INSERT** — hook receives valid Task JSON, inserts row into SQLite
2. **Agent name extraction** — extracts `subagent_type` from tool input
3. **Session ID extraction** — extracts `.session_id` from hook JSON
4. **Graceful degradation** — if DB dir missing, exits 0 (not crash)
5. **SQLITE_BUSY fallback** — if DB is locked, writes to fallback JSONL
6. **Wall clock timing** — records non-zero wall_clock_ms
7. **Result length** — records result byte count
8. **Invocation ID** — generates UUID for grouping

Test helper should:
- Create a temp DB with init-db.sh
- Pipe sample hook JSON to the hook script via stdin
- Query SQLite to verify INSERT

Sample hook JSON payload (based on real PostToolUse:Task format):
```json
{
  "session_id": "test-session-001",
  "tool_name": "Task",
  "tool_input": {
    "prompt": "Review the code for quality issues",
    "subagent_type": "fd-quality",
    "description": "Quality review"
  },
  "tool_output": "Found 3 issues: ...",
  "start_time_ms": 1708070400000,
  "end_time_ms": 1708070405000
}
```

**Step 3: Run tests to verify they fail**

Run: `bats plugins/interstat/tests/test-hook.bats`
Expected: All tests FAIL (hook script doesn't exist yet)

**Step 4: Commit**

```bash
git add plugins/interstat/tests/
git commit -m "test(interstat): failing BATS tests for PostToolUse hook (F1)"
```

---

### Task 3: Implement PostToolUse:Task Hook

**Files:**
- Create: `plugins/interstat/hooks/post-task.sh`
- Modify: `plugins/interstat/hooks/hooks.json`

**Step 1: Write the hook script**

`hooks/post-task.sh` must:
1. Read JSON from stdin (`INPUT=$(cat)`)
2. Extract fields with jq:
   - `session_id` from `.session_id`
   - `agent_name` from `.tool_input.subagent_type` (fallback: parse `.tool_input.prompt` for agent type)
   - `wall_clock_ms` from `.end_time_ms - .start_time_ms` (if available) or measure via `/proc` uptime delta
   - `result_length` from `.tool_output | length`
   - `invocation_id` from `uuidgen` or `/proc/sys/kernel/random/uuid`
3. Run `init-db.sh` (idempotent, ensures DB exists)
4. INSERT into `agent_runs` with `PRAGMA busy_timeout=5000`
5. On SQLITE_BUSY (exit code 5 from sqlite3): append to `~/.claude/interstat/failed_inserts.jsonl`
6. Exit 0 always (never block the main session)

Key patterns (from intercheck, tool-time):
```bash
#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INPUT=$(cat)

# Extract fields
SESSION_ID=$(echo "$INPUT" | jq -r '.session_id // empty')
[[ -z "$SESSION_ID" ]] && exit 0

AGENT_NAME=$(echo "$INPUT" | jq -r '.tool_input.subagent_type // empty')
[[ -z "$AGENT_NAME" ]] && AGENT_NAME="unknown"

# ... rest of hook
```

**Step 2: Update hooks.json to register the hook**

```json
{
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "Task",
        "hooks": [
          {
            "type": "command",
            "command": "${CLAUDE_PLUGIN_ROOT}/hooks/post-task.sh",
            "timeout": 10
          }
        ]
      }
    ]
  }
}
```

**Step 3: Run tests**

Run: `bats plugins/interstat/tests/test-hook.bats`
Expected: All tests PASS

**Step 4: Manual integration test**

Run the hook with sample data piped to stdin:
```bash
echo '{"session_id":"manual-test","tool_name":"Task","tool_input":{"subagent_type":"fd-quality","prompt":"test"},"tool_output":"result text here"}' | bash plugins/interstat/hooks/post-task.sh
```

Verify: `sqlite3 ~/.claude/interstat/metrics.db "SELECT * FROM agent_runs WHERE session_id='manual-test'"`
Expected: 1 row with agent_name="fd-quality", result_length > 0

**Step 5: Commit**

```bash
git add plugins/interstat/hooks/
git commit -m "feat(interstat): PostToolUse:Task hook with SQLite INSERT (F1)"
```

---

### Task 4: Write Failing Tests for JSONL Parser

**Files:**
- Create: `plugins/interstat/tests/test-parser.bats`
- Create: `plugins/interstat/tests/fixtures/` (sample JSONL files)

**Step 1: Create test fixtures**

Create sample JSONL files mimicking Claude Code's format. Key structure from empirical observation:

**Main session JSONL** (`tests/fixtures/test-session.jsonl`):
```jsonl
{"type":"user","message":{"role":"user","content":"test"},"sessionId":"test-session","timestamp":"2026-02-16T10:00:00Z","uuid":"u1"}
{"type":"assistant","message":{"role":"assistant","content":"result","model":"claude-sonnet-4-5-20250929","usage":{"input_tokens":5000,"output_tokens":2000,"cache_read_input_tokens":3000,"cache_creation_input_tokens":1000}},"sessionId":"test-session","timestamp":"2026-02-16T10:00:05Z","uuid":"a1"}
```

**Subagent JSONL** (`tests/fixtures/subagents/agent-test-agent-1.jsonl`):
```jsonl
{"type":"assistant","message":{"role":"assistant","content":"Agent analysis...","model":"claude-sonnet-4-5-20250929","usage":{"input_tokens":15000,"output_tokens":8000,"cache_read_input_tokens":10000,"cache_creation_input_tokens":2000}},"sessionId":"test-session","agentId":"test-agent-1","timestamp":"2026-02-16T10:00:10Z","uuid":"sa1"}
{"type":"assistant","message":{"role":"assistant","content":"More analysis...","model":"claude-sonnet-4-5-20250929","usage":{"input_tokens":18000,"output_tokens":5000,"cache_read_input_tokens":15000,"cache_creation_input_tokens":500}},"sessionId":"test-session","agentId":"test-agent-1","timestamp":"2026-02-16T10:01:00Z","uuid":"sa2"}
```

**Step 2: Write test cases**

Tests should verify:
1. **Basic token extraction** — parser reads JSONL, sums `input_tokens` and `output_tokens` across all `assistant` entries
2. **Multi-turn aggregation** — 2 assistant entries for same agent → tokens summed correctly
3. **Cache token extraction** — `cache_read_input_tokens` and `cache_creation_input_tokens` extracted
4. **Model extraction** — model name captured from last assistant entry
5. **Idempotency** — parsing same file twice produces same result (no duplicate rows)
6. **Per-session transactions** — if one session's JSONL is malformed, other sessions still parse
7. **Completed session only** — parser skips sessions that appear active (have recent timestamps)
8. **Subagent file discovery** — parser finds `subagents/agent-*.jsonl` files

**Step 3: Run tests to verify they fail**

Run: `bats plugins/interstat/tests/test-parser.bats`
Expected: All tests FAIL (parser doesn't exist yet)

**Step 4: Commit**

```bash
git add plugins/interstat/tests/
git commit -m "test(interstat): failing tests + fixtures for JSONL parser (F2)"
```

---

### Task 5: Implement JSONL Parser

**Files:**
- Create: `plugins/interstat/scripts/analyze.py`
- Create: `plugins/interstat/pyproject.toml`

**Step 1: Write pyproject.toml**

```toml
[project]
name = "interstat"
version = "0.1.0"
requires-python = ">=3.10"

[tool.uv]
dev-dependencies = []
```

No external dependencies — only stdlib (`json`, `sqlite3`, `pathlib`, `argparse`, `datetime`).

**Step 2: Write analyze.py**

The parser must:

1. **Discover conversation directories**: Glob `~/.claude/projects/*/` for session dirs. Each session has a `{session-id}.jsonl` main file and optionally `{session-id}/subagents/agent-*.jsonl` files.

2. **Filter completed sessions only**: Skip sessions with a `*.jsonl` modified within the last 5 minutes (likely still active). Accept `--force` flag to override.

3. **Parse subagent JSONL files**: For each `agent-{id}.jsonl`:
   - Read all lines, filter for `type == "assistant"`
   - Sum `input_tokens`, `output_tokens` from `.message.usage`
   - Sum `cache_read_input_tokens`, `cache_creation_input_tokens` from `.message.usage`
   - Compute `total_tokens = input_tokens + output_tokens`
   - Extract `model` from last assistant entry
   - Extract `sessionId` from any entry

4. **Match to existing agent_runs rows**: Query SQLite for rows matching `session_id` and `parsed_at IS NULL`. If a matching row exists (from PostToolUse hook), UPDATE it. If no matching row exists, INSERT a new one (the hook may have missed it — SQLITE_BUSY fallback scenario).

5. **Process failed_inserts.jsonl**: Read `~/.claude/interstat/failed_inserts.jsonl`, INSERT each entry into agent_runs, then truncate the file.

6. **Transaction per session**: Wrap all UPDATEs/INSERTs for a single session in a transaction. ROLLBACK on error, log the error, continue to next session.

7. **Accept CLI flags**:
   - `--session <id>`: Parse only this session (used by SessionEnd hook)
   - `--force`: Parse even recently-modified sessions
   - `--dry-run`: Print what would be parsed without writing to DB

Key implementation notes:
- Use `sqlite3` module with `conn.execute("PRAGMA busy_timeout=5000")`
- Defensive JSONL parsing: `try/except` per line, skip malformed lines
- Check for required fields before accessing: `usage = entry.get("message", {}).get("usage", {})`
- Log to stderr, data to SQLite

**Step 3: Run parser tests**

Run: `bats plugins/interstat/tests/test-parser.bats`
Expected: All tests PASS

**Step 4: Run manual integration test**

```bash
# Parse all completed sessions
cd plugins/interstat && uv run scripts/analyze.py --dry-run
```

Expected: Lists discovered sessions and what would be parsed.

**Step 5: Commit**

```bash
git add plugins/interstat/scripts/analyze.py plugins/interstat/pyproject.toml
git commit -m "feat(interstat): JSONL parser with per-session transactions (F2)"
```

---

### Task 6: Report Skill (F3)

**Files:**
- Create: `plugins/interstat/skills/report.md`
- Create: `plugins/interstat/scripts/report.sh`

**Step 1: Write report.sh**

Shell script that queries SQLite and formats output. Must:

1. Check sample count: `SELECT COUNT(*) FROM agent_runs WHERE total_tokens IS NOT NULL`
2. If count < 10: "Insufficient data (N runs). Need at least 10 for preliminary results, 50 for reliable p99."
3. Show agent summary table from `v_agent_summary`
4. Show percentile analysis:
   - p50, p90, p95 of `total_tokens` (skip p99 until 100+ samples, use p95 instead)
   - Context limit analysis: count of runs over 100K and 150K input tokens
5. Show decision gate verdict:
   - If p95 total_tokens < 120K AND sample count >= 50: "VERDICT: SKIP hierarchical dispatch"
   - If p95 total_tokens >= 120K: "VERDICT: BUILD hierarchical dispatch"
   - If sample count < 50: "VERDICT: INSUFFICIENT DATA (N/50 runs)"

Percentile SQL (correct for any sample size):
```sql
SELECT total_tokens FROM agent_runs
WHERE total_tokens IS NOT NULL
ORDER BY total_tokens ASC
LIMIT 1 OFFSET CAST((SELECT COUNT(*) FROM agent_runs WHERE total_tokens IS NOT NULL) * 0.95 AS INTEGER);
```

Output format: aligned text columns readable in terminal.

**Step 2: Write report.md skill**

```yaml
---
name: report
description: "Show token efficiency analysis and decision gate verdict"
user_invocable: true
---
```

Skill body: Runs `${CLAUDE_PLUGIN_ROOT}/scripts/report.sh` and presents results.

**Step 3: Test manually**

Insert sample data, run report:
```bash
# Insert 5 test rows
for i in 1 2 3 4 5; do
  sqlite3 ~/.claude/interstat/metrics.db "INSERT INTO agent_runs (timestamp, session_id, agent_name, input_tokens, output_tokens, total_tokens, model, parsed_at) VALUES (datetime('now'), 'test', 'fd-quality', $((RANDOM % 50000 + 10000)), $((RANDOM % 20000 + 5000)), $((RANDOM % 70000 + 15000)), 'claude-sonnet-4-5', datetime('now'))"
done

bash plugins/interstat/scripts/report.sh
```

Expected: Table with 1 agent, "Insufficient data (5/50 runs)" message, no verdict.

**Step 4: Commit**

```bash
git add plugins/interstat/skills/report.md plugins/interstat/scripts/report.sh
git commit -m "feat(interstat): report skill with decision gate query (F3)"
```

---

### Task 7: Status Skill (F4)

**Files:**
- Create: `plugins/interstat/skills/status.md`
- Create: `plugins/interstat/scripts/status.sh`

**Step 1: Write status.sh**

Shell script showing collection progress:

1. Total agent_runs count
2. Runs with token data (parsed_at IS NOT NULL)
3. Runs pending parse (parsed_at IS NULL)
4. Unique sessions and unique agents
5. Progress toward 50-run baseline: `[████████░░░░] 23/50 (46%)`
6. Most recent 5 runs: timestamp, agent name, token status (parsed/pending)

Must complete in <1s (simple COUNT queries).

**Step 2: Write status.md skill**

```yaml
---
name: status
description: "Show collection progress and pending parse status"
user_invocable: true
---
```

**Step 3: Test manually**

Run: `bash plugins/interstat/scripts/status.sh`
Expected: Shows counts, progress bar, recent runs from test data.

**Step 4: Commit**

```bash
git add plugins/interstat/skills/status.md plugins/interstat/scripts/status.sh
git commit -m "feat(interstat): status skill with collection progress (F4)"
```

---

### Task 8: Analyze Skill + SessionEnd Hook

**Files:**
- Create: `plugins/interstat/skills/analyze.md`
- Create: `plugins/interstat/hooks/session-end.sh`
- Modify: `plugins/interstat/hooks/hooks.json`

**Step 1: Write analyze.md skill**

```yaml
---
name: analyze
description: "Parse conversation JSONL files and backfill token counts"
user_invocable: true
---
```

Skill body: Runs `uv run ${CLAUDE_PLUGIN_ROOT}/scripts/analyze.py` for full historical parse.

**Step 2: Write session-end.sh**

Lightweight SessionEnd hook that:
1. Reads session_id from stdin JSON
2. Runs `uv run scripts/analyze.py --session "$SESSION_ID"` (current session only)
3. Runs in background (non-blocking): `command </dev/null >/dev/null 2>&1 &`
4. Always exits 0

**Step 3: Update hooks.json**

Add SessionEnd hook alongside existing PostToolUse:

```json
{
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "Task",
        "hooks": [
          {
            "type": "command",
            "command": "${CLAUDE_PLUGIN_ROOT}/hooks/post-task.sh",
            "timeout": 10
          }
        ]
      }
    ],
    "SessionEnd": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "${CLAUDE_PLUGIN_ROOT}/hooks/session-end.sh",
            "timeout": 15
          }
        ]
      }
    ]
  }
}
```

**Step 4: Commit**

```bash
git add plugins/interstat/skills/analyze.md plugins/interstat/hooks/
git commit -m "feat(interstat): analyze skill + SessionEnd hook for auto-backfill (F2)"
```

---

### Task 9: Integration Test + Polish

**Files:**
- Create: `plugins/interstat/tests/test-integration.bats`
- Modify: `plugins/interstat/CLAUDE.md` (final version)

**Step 1: Write integration tests**

End-to-end tests that:
1. Init fresh DB → pipe hook JSON → run parser → run report → verify output
2. Parallel hook simulation: 4 concurrent hook invocations → all 4 rows inserted (busy_timeout works)
3. Fallback JSONL: lock DB, run hook → verify fallback file written → run parser → verify rows recovered
4. Full pipeline: hook capture → JSONL parse → report shows data → status shows progress

**Step 2: Run all tests**

Run: `bats plugins/interstat/tests/`
Expected: All tests PASS

**Step 3: Write final CLAUDE.md**

```markdown
# Interstat

Token efficiency benchmarking for agent workflows.

## Quick Start

```bash
bash scripts/init-db.sh          # Initialize SQLite database
/interstat:status                 # Check collection progress
/interstat:analyze                # Parse JSONL for token data
/interstat:report                 # Show decision gate analysis
```

## Data Flow

PostToolUse:Task hook → SQLite INSERT (real-time)
SessionEnd hook → JSONL parser → SQLite UPDATE (backfill)

## Database

Location: `~/.claude/interstat/metrics.db`
Schema version: 1 (tracked via PRAGMA user_version)
```

**Step 4: Commit**

```bash
git add plugins/interstat/
git commit -m "feat(interstat): integration tests + CLAUDE.md (F0-F4 complete)"
```

---

### Task 10: Marketplace Registration

**Files:**
- Modify: `infra/marketplace/marketplace.json`

**Step 1: Add interstat to marketplace**

Add entry to `marketplace.json`:
```json
{
  "name": "interstat",
  "version": "0.1.0",
  "description": "Token efficiency benchmarking for agent workflows",
  "repository": "https://github.com/mistakeknot/interstat",
  "keywords": ["token", "benchmarking", "metrics", "sqlite"]
}
```

**Step 2: Verify marketplace format**

Run: `python3 -c "import json; d=json.load(open('infra/marketplace/marketplace.json')); print(f'{len(d)} plugins')"` (adjust path as needed)

**Step 3: Commit**

```bash
git add infra/marketplace/marketplace.json
git commit -m "chore(interstat): register in marketplace"
```

---

## Dependency Graph

```
Task 1 (scaffold)
  ↓
Task 2 (hook tests) → Task 3 (hook impl)
  ↓
Task 4 (parser tests) → Task 5 (parser impl)
  ↓
Task 6 (report) ─── independent of parser but benefits from token data
Task 7 (status) ─── independent, works with hook-only data
Task 8 (analyze skill + SessionEnd)
  ↓
Task 9 (integration tests)
  ↓
Task 10 (marketplace)
```

Tasks 6 and 7 are independent of each other and can be parallelized.
Tasks 2-3 must complete before Tasks 4-5.
Task 8 depends on Task 5 (parser) and Task 3 (hook).

## Risk Notes

- **JSONL format is undocumented** — parser must be defensive. If Claude Code changes the format, the parser breaks. Mitigation: version-pin expectations, test against fixtures, graceful degradation.
- **SQLITE_BUSY under parallel dispatch** — 4 concurrent hooks competing for write lock. Mitigation: `busy_timeout=5000` + fallback JSONL + parser recovery.
- **Conversation dir path may vary** — currently `~/.claude/projects/{encoded-cwd}/{session-id}`. Mitigation: glob discovery, not hardcoded paths.
