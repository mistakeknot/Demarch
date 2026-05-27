# Hook warnings log — Schema and recipes

Produced by `~/.claude/hooks/lib-hook-log.sh` (sourced from individual
hook scripts). Captures cross-session signal that would otherwise vanish
when each session's stderr scrolls off.

## File location

```
~/.claude/hook-warnings.log       # current
~/.claude/hook-warnings.log.1.gz  # rotated when current exceeds 10 MB
```

## Line format

```
<iso-timestamp> [hook=<name>] [level=info|warn|error] [session=<id>] <message>
```

Field order is fixed. The message is free text — searchable by grep, not
intended to be parsed as JSON.

## Example entries

```
2026-05-27T20:30:00Z [hook=check-plugin-peers] [level=warn] [session=abc12345] 5 plugins missing declared peers
2026-05-27T20:31:14Z [hook=session-start-signal] [level=warn] [session=abc12345] beads unreachable (bd stats timeout)
2026-05-27T20:45:02Z [hook=interlock-subagent-stop] [level=info] [session=abc12345] released 3 reservations (agent=mk subagent=fluxA)
```

## Levels

| Level | Meaning |
|---|---|
| `info` | Normal operational event worth recording for trend detection (subagent release, session-start completion). No action needed. |
| `warn` | Something unexpected but non-fatal. Investigate if recurring (e.g. peer-validation finding many missing plugins; beads timeout). |
| `error` | Hook hit a real error (rare — most hooks fail open silently). Look at the message for context. |

## API for hook authors

In any hook script:

```bash
# shellcheck disable=SC1091
[[ -f "${HOME}/.claude/hooks/lib-hook-log.sh" ]] && source "${HOME}/.claude/hooks/lib-hook-log.sh" 2>/dev/null

# Optional, but harmless if library is missing
declare -f hook_log_warn >/dev/null 2>&1 && \
    hook_log_warn "my-hook-name" "something interesting happened"
```

Three wrappers: `hook_log_info`, `hook_log_warn`, `hook_log_error`. All
take `(hook_name, message)` and append one line. `hook_log` directly
takes `(hook_name, level, message)` for custom levels.

## Recipes (grep-friendly queries)

**Recent warnings, any hook:**
```bash
tail -50 ~/.claude/hook-warnings.log | grep level=warn
```

**Specific hook over the last 7 days:**
```bash
awk -v cutoff="$(date -u -v-7d +%Y-%m-%d 2>/dev/null || date -u -d '7 days ago' +%Y-%m-%d)" \
    '$1 >= cutoff' ~/.claude/hook-warnings.log \
    | grep '\[hook=interlock-subagent-stop\]'
```

**Count entries by hook:**
```bash
grep -oE '\[hook=[^]]+\]' ~/.claude/hook-warnings.log | sort | uniq -c | sort -rn
```

**Sessions that triggered warnings (deduplicated):**
```bash
grep -oE '\[session=[a-f0-9-]+\]' ~/.claude/hook-warnings.log | sort -u
```

**Frequency of a specific message pattern:**
```bash
grep 'beads unreachable' ~/.claude/hook-warnings.log | wc -l
```

## Rotation

When `hook-warnings.log` exceeds 10 MB, the library renames it to
`hook-warnings.log.1` and gzips in the background. Older rotations
(log.2.gz etc.) are not created — keep one rotation generation. Manual
archival is up to the operator.

10 MB threshold vs. audit.log's 50 MB: warnings are sparse (expected
~tens per day at most). 10 MB is many months of warnings.

## What hooks currently feed this log

| Hook | Levels | When |
|---|---|---|
| `~/.claude/hooks/check-plugin-peers.sh` | warn | When N > 0 plugins have undeclared/disabled peers |
| `~/.claude/hooks/session-start-signal.sh` | warn | beads unreachable OR peer_warnings > 0 |
| `interlock/hooks/subagent-stop.sh` | info | Per subagent that released reservations |

New hooks can opt in by sourcing `lib-hook-log.sh`. Old hooks that
don't source it are unaffected — stderr behavior preserved.

## Schema versioning

This is line-oriented text, not structured data — no `version:` field.
Backwards-compatible additions: extra `[key=value]` brackets before the
message are allowed. Breaking changes (changing field order, removing
fields) would require a v2 format and a parallel log file path.

## Related

- [audit-log-schema.md](audit-log-schema.md) — structured PostToolUse log (JSON, all tool calls)
- [routing-contract.md](routing-contract.md) — interspect ↔ interflux schema
- Source: Sylveste-bc3 / docs/research/flux-review/improve-toolchain-1d7a8b22/SYNTHESIS.md
