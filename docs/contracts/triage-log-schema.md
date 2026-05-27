# Triage decision log — Schema

Produced by **interflux's flux-engine skill** at Step 1.2b (after final
scoring, before dispatch). One JSON line per agent considered, per
triage run.

Consumed by `interverse/interflux/scripts/triage-stats.py` for
skip-rate / score-contribution analysis. Enables measuring whether
`quality_signal_adjust` (Sylveste-fwd) is actually causing useful skips.

## File location

```
<project root>/.clavain/interflux/triage.jsonl
```

The file is **per-project** (lives under the project's `.clavain/`),
not global. Each project that runs flux-engine gets its own log.

## Line format

One JSON object per line. Fields:

| Field | Type | Meaning |
|---|---|---|
| `ts` | string (ISO 8601 UTC) | When the triage decision was made |
| `session_id` | string | Claude Code session ID |
| `run_id` | string | Per-triage-run identifier (8-char hash of input). All agents in one triage share this ID. |
| `input_stem` | string | Kebab-case identifier for what's being triaged (file stem, dir basename, or topic) |
| `input_type` | enum | `file` \| `directory` \| `diff` \| `text` \| `research` |
| `agent` | string | Agent identifier (e.g. `fd-architecture`, `repo-research-analyst`) |
| `category` | enum | `core` \| `cognitive` \| `research` \| `project` |
| `base` | int (0-3) | Base score component |
| `domain_boost` | int (0-2) | Domain injection criteria match |
| `project_bonus` | int (0-1) | CLAUDE.md/AGENTS.md presence |
| `domain_agent` | int (0-1) | flux-gen domain agent match |
| `tier_bonus` | float (-1 to +1) | From `.claude/agents/.index.yaml` |
| `quality_signal_adjust` | float (-1 to +0.5) | From interspect calibration (Sylveste-fwd) |
| `final_score` | float | Sum of components |
| `selected` | bool | Was the agent dispatched? |
| `stage` | int \| null | `1` (Stage 1 dispatch), `2` (Stage 2 expansion pool), or null if not selected |
| `skip_reason` | string | Free-text reason if `selected: false`. Examples: `"score 1.5 below threshold"`, `"interspect hit_rate 0.32 < 0.40"`, `"override exclude (interspect)"` |

### Optional / future fields

| Field | Type | Meaning |
|---|---|---|
| `outcome` | enum | (Future) `verdict_strong` \| `verdict_weak` \| `dispatched_no_response` — back-filled after dispatch. Out of scope for v1. |
| `tokens_used` | int | (Future) Actual tokens consumed if this agent ran. |

## Example entries

A single triage with 4 agents, 2 selected:

```json
{"ts":"2026-05-27T20:00:00Z","session_id":"abc","run_id":"7c4e9f1a","input_stem":"auth-refactor","input_type":"diff","agent":"fd-architecture","category":"core","base":3,"domain_boost":2,"project_bonus":1,"domain_agent":0,"tier_bonus":0.5,"quality_signal_adjust":0,"final_score":6.5,"selected":true,"stage":1,"skip_reason":""}
{"ts":"2026-05-27T20:00:00Z","session_id":"abc","run_id":"7c4e9f1a","input_stem":"auth-refactor","input_type":"diff","agent":"fd-safety","category":"core","base":3,"domain_boost":2,"project_bonus":1,"domain_agent":0,"tier_bonus":1.0,"quality_signal_adjust":0.5,"final_score":7.5,"selected":true,"stage":1,"skip_reason":""}
{"ts":"2026-05-27T20:00:00Z","session_id":"abc","run_id":"7c4e9f1a","input_stem":"auth-refactor","input_type":"diff","agent":"fd-correctness","category":"core","base":2,"domain_boost":0,"project_bonus":1,"domain_agent":0,"tier_bonus":0,"quality_signal_adjust":-1,"final_score":2,"selected":false,"stage":null,"skip_reason":"interspect hit_rate 0.32 < 0.40"}
{"ts":"2026-05-27T20:00:00Z","session_id":"abc","run_id":"7c4e9f1a","input_stem":"auth-refactor","input_type":"diff","agent":"fd-game-design","category":"core","base":0,"domain_boost":0,"project_bonus":1,"domain_agent":0,"tier_bonus":0,"quality_signal_adjust":0,"final_score":0,"selected":false,"stage":null,"skip_reason":"pre-filter: no game-simulation domain detected"}
```

## Append semantics

- Each Step 1.2b run emits a *batch* of lines (one per agent in the
  triage candidate pool, including pre-filtered ones with `base: 0`).
- All lines from the same run share `run_id` and `ts` (to the second).
- Append is line-buffered; no atomic-batch guarantee. Concurrent
  triages in the same project (rare) may interleave. Filter by
  `run_id` to reconstruct individual runs.

## Privacy

Logs `input_stem` (kebab-case identifier, NOT content). No file
contents or prompt text persisted. Logs are local to the project's
`.clavain/` directory — not committed by default (add to `.gitignore`
if the project commits `.clavain/` for other reasons).

## Rotation

No automatic rotation in v1. Expected volume: a few KB per
flux-engine run × low frequency = months to reach 100 MB. If the file
exceeds 50 MB, manually move to `.clavain/interflux/triage.jsonl.1`
and gzip.

## Consumers

- `triage-stats.py` — emits per-agent skip rate, `quality_signal_adjust`
  contribution histogram, run count over a window.
- Future: feed into interspect's evidence DB for closed-loop
  calibration (the agent triage decisions become a source of
  meta-evidence about whether interspect's calibration is helping or
  hurting).

## Versioning

Schema v1 (this document). Adding new fields is additive; consumers
must ignore unknown fields. Removing or retyping a field requires v2
and a `_schema` field in new lines.

## Related

- [routing-contract.md](routing-contract.md) — interspect ↔ interflux schema (overrides)
- [audit-log-schema.md](audit-log-schema.md) — PostToolUse invocation log
- [hook-warnings-schema.md](hook-warnings-schema.md) — sibling cross-session log
- Source: Sylveste-nyt / docs/research/flux-review/improve-toolchain-1d7a8b22/SYNTHESIS.md
