---
artifact_type: probe
probe: cost_attribution
bead: sylveste-3xl3.1.4
date: 2026-05-06
verdict: lead-only
verdict_basis: architecture-and-source
docs_url: https://code.claude.com/docs/en/agent-teams
source_path: interverse/interstat/scripts/cost-query.sh
---

# F1.3 — Cost Attribution Probe

**Verdict: `lead-only`** — interstat aggregates by `session_id` only; teammates run as separate sessions, so per-teammate iteration is required.

## Evidence

### `interstat session-cost` aggregation logic

`interverse/interstat/scripts/cost-query.sh` line 247-275 (the `session-cost)` case):

```sql
SELECT
    '$sid' as session_id,
    COUNT(*) as agent_runs,
    COALESCE(SUM(input_tokens),0) as input_tokens,
    ...
FROM agent_runs
WHERE session_id = '$sid' AND total_tokens > 0
```

The aggregation filters strictly by a single `session_id`. There is no `parent_session_id` join, no child-session enumeration, and no team-config awareness. **A `lead-id` query returns ONLY the lead's tokens.**

### Agent-teams architecture

From `https://code.claude.com/docs/en/agent-teams`:

> "Each teammate has its own context window."

> "Token costs scale linearly: each teammate has its own context window and consumes tokens independently."

> "Higher: each teammate is a separate Claude instance" (from the subagents-vs-teams comparison table)

> "Team config: `~/.claude/teams/{team-name}/config.json`" — "The team config contains a `members` array with each teammate's name, agent ID, and agent type."

Each teammate is a distinct Claude Code session with a distinct `session_id`. The team config's `members` array carries the per-teammate `agent ID`, which downstream maps to the interstat `session_id` (or to a session_id discoverable via the team config's runtime state).

## Plan implication

Plan F5.2 already provides for this case:

> "Else (lead-only OR unknown): call `interstat session-cost --session=<id>` per teammate and sum."

This branch is now confirmed as the **only** path — there is no `aggregated` case to short-circuit on. F5.2 can be simplified: always iterate per-teammate session IDs from the team config (`~/.claude/teams/{team-name}/config.json` → `members[].agent ID`), call `session-cost` per teammate, sum totals into the synthesis frontmatter.

The plan's transient-empty handling (5-second grace + retry + `incomplete` marker) remains essential — teammate logs may not have flushed by the time `cost_capture.sh` runs.

### Refinement to F5.2 (carry-forward into implementation)

Replace the verdict-branched logic with a single path:

1. Read `~/.claude/teams/{team_name}/config.json`.
2. Extract `members[].agent_id` (or runtime equivalent — TBD when the team config schema is inspected at first runtime use; verify field name from a real team-config emission before merge).
3. For each member ID, call `interstat session-cost --session=<id>` with one retry + 5-second grace.
4. Sum `cost_usd`. If any member returns zero rows after retry, mark `synthesis_cost_usd: incomplete` and `cost_attribution_gap: <list of unflushed members>`. Do not present a partial sum.

## Corroborating signal: subagent precedent

The Sylveste codebase already runs subagents that bill against their own session IDs (the existing `flux-drive` agent pool is the canonical example), and `interstat`'s reporting is per-session. The architecture has never assumed parent-aggregation. The agent-teams design follows the same per-session-id model, just with an explicit `members` array tying them together via the team config.

## Status

No design-breaking finding. F5.2 is cleared to proceed with the simplified single-path (always per-teammate iteration) implementation. The team-config field name for member session IDs is the only TBD — verifiable at first runtime spawn during F4 smoke test.
