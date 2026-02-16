# PRD: Interstat — Token Efficiency Benchmarking Framework

**Bead:** iv-jq5b
**Date:** 2026-02-16
**Brainstorm:** [2026-02-16-interstat-token-benchmarking-brainstorm.md](../brainstorms/2026-02-16-interstat-token-benchmarking-brainstorm.md)

## Problem

8 optimization beads (~25 person-days) were proposed without any primary measurements of actual token consumption. All 4 flux-drive reviewers flagged this as the critical gap — we're optimizing blind. Before building hierarchical dispatch, model routing, or context compression, we need to know what agents actually cost.

## Solution

A new Claude Code plugin (`interstat`) that instruments agent subprocesses via hooks, parses conversation JSONL for actual token counts, stores everything in SQLite, and provides built-in analysis queries that answer the key decision gate: is p99 context actually exceeding 120K tokens?

## Features

### F0: Plugin Scaffold + SQLite Schema
**What:** Create the `interstat` plugin with proper Claude Code plugin structure, SQLite database initialization, and the `agent_runs` table with indexes and views.
**Acceptance criteria:**
- [ ] Plugin directory at `plugins/interstat/` with valid `plugin.json`
- [ ] SQLite database created at `~/.claude/interstat/metrics.db` on first hook execution
- [ ] Schema includes `agent_runs` table, 4 indexes, `v_agent_summary` and `v_invocation_summary` views
- [ ] `init-db.sh` script handles idempotent schema creation (safe to run multiple times)
- [ ] Plugin installable via `claude plugins install`

### F1: PostToolUse:Task Hook (Real-Time Event Capture)
**What:** A hook that fires on every `Task` tool invocation, extracting agent name, session ID, invocation context, and wall clock timing, then inserting a row into SQLite.
**Acceptance criteria:**
- [ ] Hook registered in `hooks/hooks.json` as `PostToolUse` with `tool_name: "Task"`
- [ ] Extracts `agent_name` (from `subagent_type` or prompt), `session_id`, `invocation_id` (generated UUID grouping parallel dispatches)
- [ ] Records `wall_clock_ms` and `result_length` as real-time metrics
- [ ] INSERT completes in <50ms (no blocking on main session)
- [ ] Graceful degradation: if SQLite is locked or missing, log warning and exit 0
- [ ] Generates `workflow_id` from session + workflow context (sprint bead ID if available)

### F2: Conversation JSONL Parser (Token Backfill)
**What:** A Python script that reads Claude Code conversation JSONL files, extracts API response usage metadata (input_tokens, output_tokens, cache_hit_tokens), and backfills the SQLite rows created by F1.
**Acceptance criteria:**
- [ ] Python script at `scripts/analyze.py` runnable via `uv run`
- [ ] Discovers conversation JSONL files from `~/.claude/projects/*/conversations/`
- [ ] Parses `usage` fields from API response entries in the JSONL
- [ ] Correlates JSONL entries to `agent_runs` rows by session_id + agent_name + timestamp proximity
- [ ] Updates `input_tokens`, `output_tokens`, `cache_hit_tokens`, `total_tokens`, `model`, `parsed_at`
- [ ] Idempotent: re-running on already-parsed sessions is a no-op
- [ ] SessionEnd hook triggers lightweight version (current session only)
- [ ] `interstat analyze` skill triggers full historical parse

### F3: Built-In Analysis Queries (`interstat report`)
**What:** A skill/command that runs the decision gate query and agent efficiency analysis against the SQLite database and presents formatted results.
**Acceptance criteria:**
- [ ] `interstat report` skill outputs: run count, p50/p90/p99 tokens by agent, tokens-per-finding ratio, decision gate verdict
- [ ] Decision gate query: "if p99 < 120K → SKIP hierarchical dispatch"
- [ ] Context limit analysis: how many runs exceed 100K/150K input tokens
- [ ] Cost-per-finding ranking: which agents are most expensive relative to findings produced
- [ ] Output is readable in terminal (formatted table or aligned text)
- [ ] Handles <50 runs gracefully: "Insufficient data (N/50 runs), results may not be representative"

### F4: Collection Status (`interstat status`)
**What:** A skill/command that shows how many runs have been captured, how many are pending JSONL parsing, and progress toward the 50-run baseline.
**Acceptance criteria:**
- [ ] Shows: total agent_runs, runs with token data, runs pending parse, unique sessions, unique agents
- [ ] Progress bar or fraction toward 50-invocation baseline target
- [ ] Lists most recent 5 runs with timestamp, agent name, and token status (parsed/pending)
- [ ] Runs in <1s (simple COUNT queries)

## Non-goals

- Dashboard or web visualization (use SQLite CLI or DB browser)
- Upload or telemetry (local-only, no cloud storage)
- Real-time alerting on token budget exceedance
- Integration with Galiana topology experiments (defer until baseline data exists)
- Automatic model routing based on metrics (that's iv-8m38, blocked by this bead)

## Dependencies

- **Claude Code conversation JSONL format** — internal, undocumented, may change. Parser must be defensively coded.
- **SQLite3** — available on system (verified: used by beads, intermute, tldr-swinton)
- **Python + uv** — for JSONL parser (existing pattern in tool-time)
- **jq** — for shell hook JSON parsing (existing pattern in all hooks)

## Open Questions

1. **JSONL correlation** — when flux-drive dispatches 4 agents in parallel, how do we match JSONL entries to specific agents? Best hypothesis: match by `subagent_type` field in the Task tool input within the JSONL. Needs empirical validation against a sample JSONL file.
2. **Invocation grouping** — how to detect that 4 Task calls are part of the same `/flux-drive` invocation vs. independent calls? Timestamp clustering (within 2s) + same session is the likely heuristic.
3. **JSONL format** — need to inspect actual conversation JSONL structure before writing the parser. This is a prereq for F2.
