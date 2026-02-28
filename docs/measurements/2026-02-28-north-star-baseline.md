---
bead: iv-b46xi
date: 2026-02-28
type: measurement
status: baseline
---

# North Star Baseline: Cost per Landable Change

**Bead:** iv-b46xi

First measurement of the Demarch north star metric: **what does it cost to ship a reviewed, tested change?**

## Results

| Metric | Value |
|--------|-------|
| **USD per landable change** | **$1.17** |
| **Tokens per landable change** | **22,576** |
| Total token spend | 632,129 |
| Total USD cost (API pricing) | $32.80 |
| Commits produced | 28 |
| Sessions measured | 6 |
| Measurement window | 2026-02-27 09:11 UTC — 2026-02-28 01:01 UTC |

## Cost Breakdown by Model

| Model | Runs | Input Tokens | Output Tokens | Cost (USD) | % of Total |
|-------|------|-------------|---------------|------------|------------|
| claude-opus-4-6 | 21 | 28,490 | 408,676 | $31.08 | 94.7% |
| claude-sonnet-4-6 | 10 | 2,002 | 78,973 | $1.19 | 3.6% |
| claude-haiku-4-5 | 19 | 8,667 | 105,321 | $0.54 | 1.6% |

## Token Breakdown by Agent Type

| Agent | Runs | Tokens | % of Total |
|-------|------|--------|------------|
| main (host session) | 12 | 374,511 | 59.2% |
| Explore | 26 | 161,063 | 25.5% |
| general-purpose | 10 | 84,899 | 13.4% |
| Plan | 1 | 7,484 | 1.2% |
| learnings-researcher | 1 | 4,172 | 0.7% |

## Observations

1. **Output-dominant workload**: 593K output vs 39K input tokens (15:1 ratio). Agent workflows generate far more than they read in raw token terms. At Opus pricing ($75/MTok output vs $15/MTok input), output tokens drive 97% of cost.

2. **Opus dominates cost**: 21 of 50 runs used Opus (42%), but Opus accounts for $31.08 of $32.80 (94.7%). Model routing is the single biggest cost lever — even routing half of Explore subagents to Sonnet would save ~$8/day.

3. **Subagent overhead**: The main session (12 runs) consumes 59% of tokens, while 38 subagent runs consume 41%. Subagent orchestration adds significant token overhead but enables parallelism and specialization.

4. **$1.17/change is early data**: This baseline covers one day of intense development work (philosophy alignment docs, knowledge distillation, plugin vision docs — mostly documentation). Code-heavy sessions with testing may have different profiles.

## Methodology

- **Numerator (cost)**: Token counts from interstat's PostToolUse:Task hook + SessionEnd JSONL backfill. USD calculated using Anthropic API pricing (Feb 2026): Opus $15/$75 per MTok, Sonnet $3/$15, Haiku $1/$5.
- **Denominator (changes)**: Git commits within session time windows. `git log --after=<start> --before=<end>` for each session's min/max timestamp.
- **Session**: A Claude Code conversation, identified by `session_id`. Subagent runs are attributed to the parent session.

## Known Gaps

1. **Bead attribution**: `bead_id` was never populated (0/78 rows) because `CLAVAIN_BEAD_ID` is a conversation-context variable, not an environment variable. Fixed by adding session-scoped bead context files (`/tmp/interstat-bead-{session_id}`) and `set-bead-context.sh`. Future sessions will have bead attribution.

2. **Main session tokens not captured**: The main Claude Code session's token usage is only captured when `analyze.py` parses the JSONL file at session end. Real-time main session tracking is not yet implemented.

3. **No wall clock time**: `wall_clock_ms` is zero in all rows. This prevents efficiency metrics (tokens/minute, utilization rate).

4. **Commit count is approximate**: Some commits happen after the session's last recorded timestamp. The baseline uses conservative in-window counting.

5. **API vs subscription pricing**: Claude Code users on Max plan pay a flat subscription, not per-token. API pricing gives a comparable baseline for optimization decisions but doesn't reflect actual out-of-pocket cost.

## How to Reproduce

```bash
# Run the baseline query
bash interverse/interstat/scripts/cost-query.sh baseline --repo=/home/mk/projects/Demarch

# USD cost breakdown
bash interverse/interstat/scripts/cost-query.sh cost-usd

# Per-session detail
bash interverse/interstat/scripts/cost-query.sh per-session
```

## Next Steps

- Track cost-per-change over time as more sessions accumulate data
- Enable bead attribution to measure cost-per-bead (not just per-commit)
- Add model routing optimization: route Explore/general-purpose to Sonnet when Opus isn't needed
- Investigate wall_clock_ms population for efficiency metrics
