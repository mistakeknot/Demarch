# Interstat: Token Efficiency Benchmarking Framework

**Bead:** iv-jq5b
**Phase:** brainstorm (as of 2026-02-16T03:34:34Z)
**Date:** 2026-02-16
**Status:** brainstorm-complete

## What We're Building

A new plugin (`interstat`) that measures actual token consumption across all Clavain agent workflows. Two data collection layers:

1. **PostToolUse:Task hook** — lightweight, real-time event logging (agent name, wall clock, result length) to SQLite on every Task tool invocation.
2. **SessionEnd hook + CLI analyzer** — parses conversation JSONL files for actual token counts (input_tokens, output_tokens, cache_hit_tokens) and backfills the SQLite database.

The system tracks metrics at three granularity levels:
- **Workflow** — a full `/sprint` cycle (brainstorm → plan → execute → review → ship)
- **Invocation** — a single `/flux-drive` or `/flux-research` call
- **Agent** — each individual fd-* reviewer or research agent subprocess

Built-in analysis queries answer the decision gate: if p99 context < 120K tokens, hierarchical dispatch (iv-8m38) is unnecessary.

## Why This Approach

**Problem:** 8 beads (~25 person-days) proposed without validating which optimization is real. All 4 flux-drive reviewers + Oracle GPT-5.2 Pro flagged this as the critical gap. We're optimizing blind.

**Why hybrid collection:**
- Claude Code hooks don't expose token counts in their JSON payload — only tool name, session_id, result text
- Conversation JSONL files (`~/.claude/projects/*/conversations/*.jsonl`) contain full API response metadata including usage fields
- Real-time hook captures timing and agent identity; post-session parser captures actual token economics
- SessionEnd hook does lightweight logging (~2-5s); heavy JSONL parsing available via `interstat analyze` command

**Why a new plugin (not extending tool-time or Clavain):**
- tool-time tracks tool usage events (JSONL-based, no SQLite, different concern)
- Clavain has Galiana (discipline analytics) and Interspect (evidence tracking) — agent metrics is a cross-cutting concern that should be independently installable
- Clean separation: interstat measures, other plugins act on the measurements
- User chose `interstat` as the name

## Key Decisions

1. **Data source:** Hybrid — PostToolUse:Task hook for real-time events + conversation JSONL parsing for actual token counts
2. **Storage:** SQLite database at `~/.claude/interstat/metrics.db`
3. **Home:** New plugin `interstat` (not tool-time, not Clavain)
4. **Granularity:** Three-level hierarchy — workflow_id → invocation_id → agent_name
5. **Collection mode:** SessionEnd hook for lightweight auto-logging; `interstat analyze` CLI for heavy JSONL parsing
6. **Analysis:** Built-in queries for decision gates (p50/p90/p99 by agent, cost-per-finding) + raw SQLite access for ad-hoc
7. **Baseline target:** 50 real flux-drive invocations (each spawning 2-6 agents = 100-300 agent-level data points)

## Schema Design

```sql
CREATE TABLE agent_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,           -- ISO 8601
    session_id TEXT NOT NULL,          -- Claude Code session
    workflow_id TEXT,                   -- groups a full /sprint cycle
    invocation_id TEXT NOT NULL,        -- groups a single /flux-drive call
    agent_name TEXT NOT NULL,           -- e.g., fd-architecture, fd-correctness
    scope TEXT NOT NULL,                -- 'workflow' | 'invocation' | 'agent'

    -- From PostToolUse hook (real-time)
    wall_clock_ms INTEGER,
    result_length INTEGER,             -- proxy until JSONL parsed

    -- From JSONL parser (backfilled)
    input_tokens INTEGER,
    output_tokens INTEGER,
    cache_hit_tokens INTEGER,
    total_tokens INTEGER,              -- computed: input + output

    -- Outcome metrics
    findings_count INTEGER,
    findings_severity TEXT,            -- JSON array of severity counts

    -- Metadata
    model TEXT,                        -- e.g., claude-sonnet-4-5, claude-haiku-4-5
    target_file TEXT,                  -- what was being reviewed
    parsed_at TEXT                     -- when JSONL was parsed (NULL = not yet)
);

CREATE INDEX idx_agent_runs_session ON agent_runs(session_id);
CREATE INDEX idx_agent_runs_invocation ON agent_runs(invocation_id);
CREATE INDEX idx_agent_runs_agent ON agent_runs(agent_name);
CREATE INDEX idx_agent_runs_timestamp ON agent_runs(timestamp);

-- Built-in analysis views
CREATE VIEW v_agent_summary AS
SELECT
    agent_name,
    COUNT(*) as runs,
    AVG(input_tokens) as avg_input,
    AVG(output_tokens) as avg_output,
    AVG(total_tokens) as avg_total,
    AVG(wall_clock_ms) as avg_wall_ms,
    AVG(findings_count) as avg_findings,
    CASE WHEN AVG(findings_count) > 0
        THEN AVG(total_tokens) / AVG(findings_count)
        ELSE NULL
    END as tokens_per_finding
FROM agent_runs
WHERE scope = 'agent'
GROUP BY agent_name;

CREATE VIEW v_invocation_summary AS
SELECT
    invocation_id,
    MIN(timestamp) as started,
    COUNT(*) as agent_count,
    SUM(input_tokens) as total_input,
    SUM(output_tokens) as total_output,
    SUM(total_tokens) as total_tokens,
    MAX(wall_clock_ms) as wall_clock_ms,  -- parallel agents: max not sum
    SUM(findings_count) as total_findings
FROM agent_runs
WHERE scope = 'agent'
GROUP BY invocation_id;
```

## Data Collection Architecture

```
PostToolUse:Task hook                    SessionEnd hook
  │                                        │
  ├─ reads JSON stdin                      ├─ lightweight: log session end time
  ├─ extracts: agent_name, session_id      │
  ├─ measures: wall_clock_ms               │
  ├─ INSERT into agent_runs                │
  │  (input/output_tokens = NULL)          │
  │                                        │
  └─ real-time, <50ms overhead             │
                                           │
                     `interstat analyze`  ←─┘  (can also run manually)
                       │
                       ├─ finds conversation JSONL files
                       ├─ parses API response usage metadata
                       ├─ matches to existing agent_runs rows
                       ├─ UPDATE: backfills token counts
                       └─ ~2-5s per session
```

## Decision Gate Queries

```sql
-- THE decision gate: is hierarchical dispatch needed?
SELECT
    CASE WHEN percentile_p99 < 120000
        THEN 'SKIP hierarchical dispatch (iv-8m38)'
        ELSE 'BUILD hierarchical dispatch'
    END as decision
FROM (
    SELECT MAX(total_tokens) as percentile_p99  -- approximate: use proper percentile after 50+ runs
    FROM v_invocation_summary
    ORDER BY total_tokens
    LIMIT 1 OFFSET (SELECT CAST(COUNT(*) * 0.99 AS INTEGER) FROM v_invocation_summary)
);

-- Which agents are most expensive per finding?
SELECT agent_name, runs, avg_total, avg_findings, tokens_per_finding
FROM v_agent_summary
ORDER BY tokens_per_finding DESC;

-- Are we actually hitting context limits?
SELECT agent_name,
    COUNT(CASE WHEN input_tokens > 100000 THEN 1 END) as over_100k,
    COUNT(CASE WHEN input_tokens > 150000 THEN 1 END) as over_150k,
    COUNT(*) as total
FROM agent_runs WHERE scope = 'agent'
GROUP BY agent_name;
```

## Open Questions

1. **JSONL format stability** — conversation JSONL structure is internal to Claude Code. If the format changes, the parser breaks. Mitigation: version-pin the parser, test against sample files.
2. **Multi-agent session correlation** — when `/flux-drive` dispatches 4 agents in parallel via Task tool, how do we correlate which JSONL entries belong to which agent? Likely via the task prompt content or agent type parameter.
3. **Privacy** — should metrics be uploadable (like tool-time) or strictly local? Starting local-only.
4. **Galiana integration** — Galiana already runs topology experiments. Should interstat feed into Galiana, or remain independent? Defer until we have baseline data.

## Scope / YAGNI Boundaries

**In scope (v1):**
- Plugin scaffold (interstat)
- SQLite schema + migrations
- PostToolUse:Task hook for real-time event capture
- SessionEnd hook for lightweight logging
- `interstat analyze` command for JSONL parsing
- `interstat report` command with built-in decision gate queries
- `interstat status` command showing collection progress (N runs captured)

**Out of scope (defer):**
- Dashboard / visualization (just use SQLite CLI or DB browser)
- Upload / telemetry (local-only for now)
- Real-time alerting on token budget exceedance
- Integration with Galiana topology experiments
- Automatic model routing based on metrics (that's iv-8m38)
