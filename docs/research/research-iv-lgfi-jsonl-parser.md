# Research: iv-lgfi "F2: Conversation JSONL Parser (Token Backfill)"

**Date:** 2026-02-20  
**Task ID:** iv-lgfi  
**Priority:** 2  
**Status:** Research complete — ready for implementation planning  

---

## Overview

The Conversation JSONL parser (iv-lgfi) is Phase F2 of the interstat plugin's token benchmarking architecture. It's responsible for:

1. **Discovering** Claude Code conversation JSONL files from `~/.claude/projects/*/`
2. **Parsing** JSONL lines to extract token usage metadata
3. **Backfilling** SQLite `agent_runs` table with actual token counts (unavailable during real-time hook execution)
4. **Correlating** JSONL entries with agent run records created by the PostToolUse:Task hook (iv-qi8j)

This is **F2 of 4** features in the interstat roadmap:
- **F1** (iv-qi8j): PostToolUse:Task hook (real-time event capture) — COMPLETED
- **F2** (iv-lgfi): Conversation JSONL parser (token backfill) — THIS TASK
- **F3** (iv-dkg8): Report skill (analysis + decision gate) — DEPENDS ON F2
- **F4** (iv-bazo): Status skill (collection progress) — DEPENDS ON F2

---

## Dependencies

**Blocking tasks (must complete first):**
- iv-dyyy — F1: PostToolUse:Task hook (already completed)
- iv-jq5b — SQLite schema + data integrity (already completed)

**Blocking this task:**
- iv-bazo — F4: interstat status skill
- iv-dkg8 — F3: interstat report skill

---

## Architecture Overview

### Two-Phase Data Collection

**Phase 1: Real-Time Hook (PostToolUse:Task)**
- Fires when an agent dispatch/tool invocation completes
- Captures event metadata: session_id, agent_name, subagent_type, description, invocation_id, result_length
- Writes immediately to SQLite agent_runs table with NULL token fields
- Hook: `/root/projects/Interverse/plugins/interstat/hooks/post-task.sh` (80 lines)

**Phase 2: Session-End JSONL Backfill (SessionEnd Hook)**
- Fires when a Claude Code session ends
- Extracts session_id from hook input
- **Non-blocking**: Background invocation of `analyze.py` with `--session $SESSION_ID --force`
- Scans `~/.claude/projects/$SESSION_ID/` for `*.jsonl` files
- Parses each file, aggregates token usage across all assistant messages
- Performs 3-strategy upsert to match hook records with JSONL data
- Updates NULL token fields in SQLite
- Hook: `/root/projects/Interverse/plugins/interstat/hooks/session-end.sh` (22 lines)

**Why two phases?**
- Hooks run in <100ms constraints; JSONL parsing is I/O intensive and can take seconds
- Real-time hooks capture event structure (which tools, what order, how many subagents) immediately
- JSONL backfill captures actual token counts that are only available after API responses are received

---

## SQLite Schema

**Database Location:** `~/.claude/interstat/metrics.db`

### agent_runs table (init-db.sh lines 14–31)

```sql
CREATE TABLE IF NOT EXISTS agent_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,              -- ISO-8601, from hook or JSONL
    session_id TEXT NOT NULL,             -- session identifier
    agent_name TEXT NOT NULL,             -- agent/subagent name
    invocation_id TEXT,                   -- UUID from hook
    subagent_type TEXT,                   -- e.g. "Explore", "Verify" (from hook)
    description TEXT,                     -- tool_input.description (from hook)
    wall_clock_ms INTEGER,                -- elapsed time in milliseconds
    result_length INTEGER,                -- tool_output length (bytes)
    input_tokens INTEGER,                 -- backfilled from JSONL
    output_tokens INTEGER,                -- backfilled from JSONL
    cache_read_tokens INTEGER,            -- backfilled from JSONL
    cache_creation_tokens INTEGER,        -- backfilled from JSONL
    total_tokens INTEGER,                 -- input + output (computed)
    model TEXT,                           -- model name from JSONL (e.g. claude-sonnet-4-5-20250929)
    parsed_at TEXT                        -- timestamp when JSONL parser ran
);

CREATE INDEX idx_agent_runs_session ON agent_runs(session_id);
CREATE INDEX idx_agent_runs_agent ON agent_runs(agent_name);
CREATE INDEX idx_agent_runs_timestamp ON agent_runs(timestamp);
CREATE INDEX idx_agent_runs_subagent_type ON agent_runs(subagent_type);
```

**Schema versioning:** `PRAGMA user_version = 2` (set in init-db.sh line 75)

**Views created:**
- `v_agent_summary` — aggregates by agent_name/model (line 46–58)
- `v_invocation_summary` — aggregates by invocation_id (line 60–73)

---

## JSONL Format

### File Discovery

**Locations scanned:**
- `~/.claude/projects/<session-id>/` (main session JSONL)
- `~/.claude/projects/<session-id>/subagents/agent-*.jsonl` (subagent JSONLs)

**File patterns:**
- Main: `test-session-1.jsonl`
- Subagents: `subagents/agent-fd-quality.jsonl`, `subagents/agent-a76c7a5.jsonl`

**Freshness filter (discover_candidates, analyze.py:70–100):**
- Default: skip files modified <5 minutes ago (RECENT_WINDOW_SECONDS = 300)
- Override: `--force` flag to parse recently-modified files

### Line Format

Each line is a JSON object with fields:

```json
{
  "type": "user|assistant",
  "message": {
    "role": "user|assistant",
    "content": "...",
    "model": "claude-sonnet-4-5-20250929",    // assistant only
    "usage": {                                 // assistant only
      "input_tokens": 5000,
      "output_tokens": 2000,
      "cache_read_input_tokens": 3000,
      "cache_creation_input_tokens": 1000
    }
  },
  "sessionId": "test-session-1",
  "timestamp": "2026-02-16T10:00:05Z",
  "uuid": "a1",
  "agentId": "fd-quality"                    // subagent files only
}
```

**Token fields in usage object:**
- `input_tokens` — fresh tokens processed
- `output_tokens` — tokens generated
- `cache_read_input_tokens` — tokens read from prompt cache (not re-processed)
- `cache_creation_input_tokens` — tokens written to prompt cache for future reuse

### Test Fixtures

**Location:** `/root/projects/Interverse/plugins/interstat/tests/fixtures/sessions/`

**test-session-1.jsonl (3 lines):**
- Line 1: user message ("test")
- Line 2: assistant with usage (5000 input, 2000 output, 3000 cache_read, 1000 cache_creation)
- Line 3: assistant with usage (6000 input, 3000 output, 4000 cache_read, 500 cache_creation)

**test-session-1/subagents/agent-fd-quality.jsonl (2 lines):**
- Line 1: assistant (15000 input, 8000 output, 10000 cache_read, 2000 cache_creation)
- Line 2: assistant (18000 input, 5000 output, 15000 cache_read, 500 cache_creation)

**malformed.jsonl (3 lines):**
- Line 1: valid assistant entry
- Line 2: "this is not json" (parse error)
- Line 3: assistant with empty message dict (skipped)

---

## analyze.py Implementation Details

**File:** `/root/projects/Interverse/plugins/interstat/scripts/analyze.py` (534 lines)

### Constants & Configuration

```python
RECENT_WINDOW_SECONDS = 5 * 60                                    # 300s freshness window
DEFAULT_DB_PATH = Path.home() / ".claude" / "interstat" / "metrics.db"
DEFAULT_CONVERSATIONS_DIR = Path.home() / ".claude" / "projects"
FAILED_INSERTS_PATH = Path.home() / ".claude" / "interstat" / "failed_inserts.jsonl"
```

### Key Functions

**1. discover_candidates(conversations_dir, session_filter, force) → list[dict]**
- Recursively scans conversations_dir for `*.jsonl` files
- Returns list of {path, subagent, session_hint, agent_name} dicts
- Filters by session_filter if provided
- Skips files modified <5 minutes ago unless --force is set
- Used by main() to find files to parse

**2. parse_jsonl(path, session_hint, agent_name) → dict | None**
- Opens and reads JSONL file line-by-line
- Skips blank lines
- Logs malformed JSON lines but continues
- Fails silently if >50% of lines fail to parse
- Extracts sessionId from first line (fallback to session_hint)
- Filters for "type": "assistant" entries with message.usage dict
- **Aggregates tokens across ALL assistant lines:**
  ```python
  input_tokens += as_int(usage.get("input_tokens"))
  output_tokens += as_int(usage.get("output_tokens"))
  cache_read_tokens += as_int(usage.get("cache_read_input_tokens"))
  cache_creation_tokens += as_int(usage.get("cache_creation_input_tokens"))
  ```
- Extracts model and timestamp from any assistant entry
- Returns dict with aggregated metrics or None on error

**3. upsert_agent_run(conn, run, parsed_at) → None**
- **3-strategy match** to find hook-inserted row (lines 149–180):
  1. Exact match: session_id + agent_name (from filename) + NULL input_tokens
  2. Fallback: session_id + invocation_id (if both JSONL and hook have this data)
  3. Fallback: session_id + timestamp range (within ±5 seconds)
- Updates matched row with aggregated token counts
- Preserves subagent_type/description from hook if present
- Sets parsed_at = current timestamp

**4. write_session_runs(conn, grouped_runs, parsed_at) → None**
- Transactional batch writer
- Calls upsert_agent_run for each parsed run
- Commits only on success

**5. replay_failed_inserts(conn) → None**
- Reads failed_inserts.jsonl (from PostToolUse hook failures)
- Attempts to insert each entry
- Truncates file on success (indicating recovery)

**6. print_dry_run(grouped_runs, failed_insert_entries) → None**
- Prints pending inserts and failed-insert replay (if --dry-run set)
- Does not modify DB

### Argument Parser

```bash
./analyze.py [--session SESSION_ID] [--force] [--dry-run] [--db PATH] [--conversations-dir PATH]
```

**Defaults:**
- --db: `~/.claude/interstat/metrics.db`
- --conversations-dir: `~/.claude/projects/`
- --session: scans all sessions (no filter)
- --force: respects freshness window (don't parse active files)

---

## Session-End Hook Integration

**File:** `/root/projects/Interverse/plugins/interstat/hooks/session-end.sh` (22 lines)

```bash
INPUT=$(cat)  # reads SessionEnd hook payload

SESSION_ID="$(printf '%s' "$INPUT" | jq -r '(.session_id // "")' 2>/dev/null || printf '')"

if [ -z "$SESSION_ID" ] || [ "$SESSION_ID" = "null" ]; then
  exit 0  # ignore if no session_id
fi

# Background: parse just this session (non-blocking)
(
  cd "${SCRIPT_DIR}/.." && uv run "$ANALYZE_SCRIPT" --session "$SESSION_ID" --force
) </dev/null >/dev/null 2>&1 &

exit 0
```

**Key design:**
- **Non-blocking:** backgrounds the Python script
- **Session-scoped:** `--session $SESSION_ID` limits parsing to current session only
- **Fresh files:** `--force` ensures recently-written JSONL files are parsed
- **Error isolated:** stdout/stderr suppressed (no hook failures from parse errors)

---

## Data Flow Example

**Scenario:** Agent dispatch at 10:00:05Z in session "test-session-1"

### Step 1: PostToolUse:Task Hook (10:00:05Z)

Hook receives:
```json
{
  "session_id": "test-session-1",
  "tool_input": {
    "subagent_type": "Explore",
    "description": "Scan codebase for patterns"
  },
  "tool_output": "Found 42 matches...",
  "timestamp": "2026-02-16T10:00:05Z"
}
```

SQLite insert (post-task.sh line 39–57):
```sql
INSERT INTO agent_runs (
  timestamp, session_id, agent_name, subagent_type, description, invocation_id, result_length
) VALUES (
  '2026-02-16T10:00:05Z',
  'test-session-1',
  'Explore',
  'Explore',
  'Scan codebase for patterns',
  'abc123...',
  '20'  -- length of tool_output
);
```

**Result:** Row with id=1, all token fields = NULL

### Step 2: Session Ends (10:15:00Z)

SessionEnd hook fires, invokes:
```bash
uv run analyze.py --session test-session-1 --force
```

### Step 3: JSONL Discovery & Parsing

discover_candidates finds:
- `~/.claude/projects/test-session-1/main.jsonl` (mtime < 5 min ago, OK with --force)
- `~/.claude/projects/test-session-1/subagents/agent-explore.jsonl`

parse_jsonl for main.jsonl:
- Reads 3 lines (user, assistant, assistant)
- Filters for type="assistant" entries
- Aggregates: 5000 + 6000 = 11000 input, 2000 + 3000 = 5000 output, etc.
- Returns: {session_id: "test-session-1", agent_name: "main-session", input_tokens: 11000, ...}

parse_jsonl for subagents/agent-explore.jsonl:
- Extracts session_id from file: "test-session-1"
- Extracts agent_name from filename: "explore"
- Aggregates: 15000 + 18000 = 33000 input, 8000 + 5000 = 13000 output, etc.
- Returns: {session_id: "test-session-1", agent_name: "explore", input_tokens: 33000, ...}

### Step 4: Upsert to SQLite

For the "explore" run:
1. **Strategy 1:** Exact match session_id + agent_name + NULL input_tokens
   - Matches if session="test-session-1", agent_name="Explore" (from hook), input_tokens=NULL
   - Found: id=1 (from step 1)
2. **Update row 1:**
   ```sql
   UPDATE agent_runs SET
     timestamp='2026-02-16T10:00:05Z',
     agent_name='explore',
     input_tokens=33000,
     output_tokens=13000,
     cache_read_tokens=25000,
     cache_creation_tokens=2500,
     total_tokens=46000,
     model='claude-sonnet-4-5-20250929',
     parsed_at='2026-02-16T10:15:30Z'
   WHERE id=1
   ```

**Result:** agent_runs table now has complete token data for the run

---

## Error Handling & Resilience

### Malformed JSONL (malformed.jsonl test case)

1. **Line 1 (valid):** Processed normally
2. **Line 2 ("this is not json"):** 
   - json.JSONDecodeError caught, logged as warning
   - **Not added to entries list**
   - Parsing continues
3. **Line 3 (empty message dict):**
   - JSON valid but no usage object
   - Skipped (not in assistant_entries)
4. **Result:** If >50% of lines fail, entire file is skipped with ERROR log

### Failed Database Inserts

When PostToolUse hook encounters SQLite errors (line 38–77 in post-task.sh):

1. Insert attempt fails (insert_status ≠ 0)
2. Row written to `failed_inserts.jsonl`:
   ```json
   {
     "timestamp": "2026-02-16T10:00:05Z",
     "session_id": "test-session-1",
     "agent_name": "Explore",
     "subagent_type": "Explore",
     "description": "Scan codebase for patterns",
     "invocation_id": "abc123...",
     "result_length": 20
   }
   ```
3. On next session end, `replay_failed_inserts()` attempts recovery
4. File truncated on successful replay

---

## Key Implementation Details

### Type Coercion Helpers (analyze.py)

```python
def as_int(value: object) -> int:
    """Coerce to int, default 0 if missing/invalid."""
    if value is None: return 0
    try: return int(value)
    except (TypeError, ValueError): return 0

def as_opt_int(value: object) -> int | None:
    """Coerce to int, return None if missing/invalid."""
    if value is None: return None
    try: return int(value)
    except (TypeError, ValueError): return None

def as_str(value: object) -> str | None:
    """Coerce to str if non-empty string, else None."""
    if isinstance(value, str) and value: return value
    return None
```

**Why?** JSONL can have missing fields, malformed values, null values. These helpers prevent cascading failures.

### Subagent Path Inference

```python
def is_subagent_file(path: Path) -> bool:
    return path.parent.name == "subagents" and path.name.startswith("agent-") and path.suffix == ".jsonl"

def session_hint_for_path(path: Path, subagent: bool) -> str | None:
    # For subagent: parent is session dir (e.g., "test-session-1")
    # For main: stem is session name (e.g., "test-session-1.jsonl" → "test-session-1")
    if subagent:
        parent = path.parent.parent
        return parent.name if parent.name else None
    return path.stem

def agent_name_for_path(path: Path, subagent: bool) -> str:
    # For main: always "main-session"
    # For subagent: extract from filename (e.g., "agent-explore.jsonl" → "explore")
    if not subagent:
        return "main-session"
    stem = path.stem
    if stem.startswith("agent-"):
        return stem[len("agent-") :]
    return stem
```

### Timestamp Fallback Chain

1. First assistant entry in file (most recent API response)
2. Any entry with timestamp field
3. Fallback: current UTC time via utc_now_iso()

### Total Tokens Calculation

```python
"total_tokens": input_tokens + output_tokens
```

**Note:** Does NOT include cache_read or cache_creation in total. These are breakdowns of input_tokens (tokens that were cached vs fresh).

---

## Execution Flow

### Main Script Entry Point

```python
def main() -> int:
    parse_args()  # CLI: --session, --force, --dry-run, --db, --conversations-dir
    discover_candidates(...)
    group by session_id
    if --dry-run:
        print_dry_run(...) and exit(0)
    replay_failed_inserts(conn)
    write_session_runs(conn, grouped_runs, parsed_at)
    return 0
```

### Session-End Hook Invocation

```bash
# From Claude Code SessionEnd event
uv run analyze.py --session test-session-1 --force
```

- Runs in background (non-blocking)
- Scoped to single session (faster than full scan)
- --force ensures fresh files are parsed
- Errors logged but don't affect hook exit code

---

## Testing Strategy (from test fixtures)

**Test fixture location:** `/root/projects/Interverse/plugins/interstat/tests/fixtures/sessions/`

**test-session-1.jsonl:**
- 3 lines: 1 user, 2 assistant entries
- Tests: basic JSONL parsing, token aggregation

**test-session-1/subagents/agent-fd-quality.jsonl:**
- 2 lines: assistant entries with distinct token counts
- Tests: subagent path inference, per-agent aggregation

**malformed.jsonl:**
- 3 lines: valid, invalid JSON, valid with missing fields
- Tests: error resilience, >50% failure threshold

---

## Open Questions & Assumptions

### Q1: UUID Uniqueness in Hook Records

The hook generates `invocation_id` via `/proc/sys/kernel/random/uuid`. Assumption: each agent dispatch gets a unique UUID. If multiple dispatches within same ms, UUIDs still differ. ✓ Assumption valid.

### Q2: Subagent Agent-Name Inference

Subagent files named `agent-<name>.jsonl`. Question: Can agent names have hyphens or special chars? Current code: `agent-explore` → `explore` (strip prefix). If agent is `agent-fd-quality.jsonl`, code extracts `fd-quality`. ✓ Assumption valid (stem handling is correct).

### Q3: Total Tokens Semantics

Is total_tokens = input + output (ACTUAL TOKENS) or input + output + cache_read (EFFECTIVE TOKENS FOR QUOTA)?

From JSONL and schema: `total_tokens: input_tokens + output_tokens` (line 180 in analyze.py). Cache read/creation are **components** of the input_tokens count, not additional. This is Claude API semantics: cache_read_input_tokens are already in input_tokens. ✓ Correct.

### Q4: Hook vs Parser Timestamp

If hook and JSONL have different timestamps, which wins? Parser strategy: Use JSONL timestamp if available, else fallback to hook timestamp. Assumption: JSONL timestamp is more accurate (last_message_ts). ✓ Reasonable.

### Q5: Subagent_type vs Agent_name Collision

Hook may write subagent_type="Explore" and agent_name="Explore". Parser extracts agent_name="explore" (lowercase) from filename. Do they match? Strategy 1 uses agent_name + session + NULL tokens. Different case, but agent_name col is overwritten by parser. ✓ Match strategy handles this.

---

## Related Roadmap Items

- **iv-qi8j** (F1: PostToolUse:Task hook) — COMPLETE — Provides real-time event capture
- **iv-dyyy** (metrics schema) — COMPLETE — Foundation for iv-lgfi
- **iv-jq5b** (SQLite schema) — COMPLETE — Schema for agent_runs table
- **iv-dkg8** (F3: Report skill) — BLOCKS iv-lgfi — Depends on F2 completion
- **iv-bazo** (F4: Status skill) — BLOCKS iv-lgfi — Depends on F2 completion
- **iv-v81k** — Repository-aware benchmark expansion — Future enhancement

---

## File References

### Plugin Structure

| Path | Purpose | Lines |
|------|---------|-------|
| `/root/projects/Interverse/plugins/interstat/plugin.json` | Plugin metadata | 11 |
| `/root/projects/Interverse/plugins/interstat/README.md` | User documentation | 50 |
| `/root/projects/Interverse/plugins/interstat/CLAUDE.md` | Quick reference | Brief |
| `/root/projects/Interverse/plugins/interstat/AGENTS.md` | Dev guide | 31 |
| `/root/projects/Interverse/plugins/interstat/PHILOSOPHY.md` | Design principles | 37 |

### Implementation Files

| Path | Purpose | Lines |
|------|---------|-------|
| `scripts/init-db.sh` | SQLite schema creation | 79 |
| `scripts/analyze.py` | JSONL parser (target of iv-lgfi) | 534 |
| `scripts/status.sh` | Status report (depends on F2) | TBD |
| `scripts/report.sh` | Analysis report (depends on F2) | TBD |
| `hooks/post-task.sh` | Real-time hook (F1 complete) | 80 |
| `hooks/session-end.sh` | Session-end trigger for parser | 22 |

### Test Fixtures

| Path | Lines | Purpose |
|------|-------|---------|
| `tests/fixtures/sessions/test-session-1.jsonl` | 3 | Basic JSONL with token data |
| `tests/fixtures/sessions/test-session-1/subagents/agent-fd-quality.jsonl` | 2 | Subagent aggregation |
| `tests/fixtures/sessions/malformed.jsonl` | 3 | Error resilience |

---

## Schema Diagram

```
Claude Code Session
├── Main JSONL (~/.claude/projects/SESSION_ID/*.jsonl)
│   ├── user messages
│   └── assistant messages (with usage.input_tokens, cache_read_input_tokens, etc.)
└── Subagent JSONLs (~/.claude/projects/SESSION_ID/subagents/agent-*.jsonl)
    └── assistant messages (per subagent)

SessionEnd Hook → analyze.py --session SESSION_ID --force
├── discover_candidates(~/.claude/projects/) → paths[]
├── parse_jsonl(path) → {session_id, agent_name, input_tokens, output_tokens, cache_read_tokens, cache_creation_tokens, model}
└── upsert_agent_run(conn, run) → UPDATE agent_runs SET ... WHERE [strategy 1|2|3]

SQLite Database (~/.claude/interstat/metrics.db)
└── agent_runs (id, timestamp, session_id, agent_name, ..., input_tokens, output_tokens, cache_read_tokens, cache_creation_tokens, total_tokens, model, parsed_at)
    ├── Index: session_id
    ├── Index: agent_name
    ├── Index: timestamp
    └── View: v_agent_summary (aggregates by agent + model)
```

---

## Summary

The Conversation JSONL parser (iv-lgfi) is a **critical Phase F2 component** that:

1. **Discovers** JSONL files from all session directories
2. **Parses** line-by-line with error resilience
3. **Aggregates** token usage across all assistant messages per file
4. **Matches** JSONL records to hook-inserted rows via 3-strategy heuristics
5. **Backfills** NULL token fields in SQLite
6. **Handles** edge cases: malformed JSONL, missing fields, subagent path inference

**Key technical insights:**
- Aggregation is done per JSONL file (one file = one agent run)
- Cache tokens are **components** of input_tokens, not additions
- Timestamp comes from JSONL (most accurate)
- Subagent name inference via filename (agent-*.jsonl pattern)
- 3-strategy match handles hook/JSONL correlation with fallbacks
- Non-blocking hook design keeps session-end latency < 100ms

**Ready for:** Implementation planning and coding (no additional research needed).

