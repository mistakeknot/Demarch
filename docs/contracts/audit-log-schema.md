# Tool Invocation Audit Log — Schema

Produced by `~/.claude/hooks/log-tool-invocation.sh` (PostToolUse hook).
Consumed by `~/.claude/scripts/audit-summary.sh` and any downstream tool
calibration (e.g., interspect, future plugin-deprecation tooling).

## File location

```
~/.claude/audit.log       # current
~/.claude/audit.log.1.gz  # rotated when current exceeds 50 MB
```

## Line format

One JSON object per line (newline-delimited JSON). Fields:

| Field | Type | Meaning |
|---|---|---|
| `ts` | string (ISO 8601 UTC) | When the tool invocation ended |
| `session_id` | string | Claude Code session ID (empty if not set) |
| `tool` | string | Tool name. One of: `Skill`, `Agent`, `Bash`, `Read`, `Edit`, `Write`, `NotebookEdit` (per the PostToolUse matcher) |
| `name` | string | Identifier specific to the tool: skill name (`clavain:campaign`), subagent type (`interflux:fd-architecture`), file path (for Read/Edit/Write), or first 80 chars of the Bash description |
| `duration_ms` | integer | Wall-clock duration if provided by Claude Code; `0` otherwise |
| `exit_code` | integer | `0` for success, non-zero for failure |

Entries with no `tool` value are skipped (unusable for analysis).

## Example

```json
{"ts":"2026-05-27T17:39:51.643Z","session_id":"abc123","tool":"Skill","name":"clavain:campaign","duration_ms":42,"exit_code":0}
{"ts":"2026-05-27T17:40:02.001Z","session_id":"abc123","tool":"Agent","name":"interflux:fd-architecture","duration_ms":343944,"exit_code":0}
{"ts":"2026-05-27T17:40:15.500Z","session_id":"abc123","tool":"Edit","name":"/Users/sma/projects/Sylveste/scripts/foo.py","duration_ms":12,"exit_code":0}
```

## Privacy

The `name` field can contain file paths — paths under `/Users/<user>/` may
leak the local username. The log lives locally in `~/.claude/`; it should
not be uploaded to remote services without sanitization (`sed -E
's|/Users/[^/]+/|/Users/<user>/|g'`).

`tool_input` content beyond `name` is **not** captured. We never log
file contents, prompts, or command arguments.

## Rotation

When `audit.log` exceeds 50 MB, the hook renames it to `audit.log.1` and
gzips in the background. Older rotations (audit.log.2.gz etc.) are not
created — we keep one rotation generation. Manual archival is up to the
operator (cron job → external storage if long-term analysis is needed).

## Downstream consumers

- `~/.claude/scripts/audit-summary.sh` — 30-day report with per-tool and
  per-name counts and durations
- `interspect calibrate-audit` (Sylveste-xr3) — replays historical agent
  invocations through a prior scoring formula to detect calibration drift
- `interflux ← interspect evidence subscription` (Sylveste-fwd) — reads
  agent invocation counts + success rates to skip underperforming agents

## Versioning

This schema is v1. Adding new fields is additive (consumers must ignore
unknown fields). Removing fields or changing types is a breaking change
requiring a v2 marker, which would surface in a top-level
`{"_schema":2,...}` field added to new lines.
