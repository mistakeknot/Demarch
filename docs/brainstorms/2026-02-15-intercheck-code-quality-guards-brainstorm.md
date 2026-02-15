# Intercheck: Code Quality Guards & Session Health

## What We're Building

A new Claude Code plugin (`intercheck`) providing three PostToolUse hooks and one status skill:

1. **Context Monitor** — Time-decay pressure scoring with token estimation. Warns at thresholds, auto-checkpoints before context exhaustion.
2. **Syntax Check** — Validates Python, Shell, JSON, TOML, YAML, Go, TS/JS after every Edit/Write.
3. **Auto-Format** — Runs ruff, shfmt, gofmt, jq, prettier after edits. Silent, best-effort.
4. **`/intercheck:status`** — Session health dashboard.

## Why This Approach

Inspired by 4 discoveries from Interject's scan:
- "4 Hooks That Let Claude Code Run Autonomously" (DEV Community) — context monitor + syntax check pattern
- "Claude Code Tips From the Guy Who Built It" (Boris Cherny) — PostToolUse auto-formatter
- "Long Mem code agent cut 95% costs" (CoSave) — session state tracking patterns

We already have model routing (Clavain) and session handoff, but missing:
- **Early warning** before context exhaustion (currently only handoff AFTER death)
- **Immediate syntax feedback** (currently errors discovered many tool calls later)
- **Auto-formatting** (currently CI catches formatting, not the agent)

## Key Decisions

- **Plugin name**: `intercheck` (not interspect — that's evidence collection in Clavain)
- **Pure hooks plugin** — no MCP server, minimal footprint
- **Pressure model**: call count + time decay (0.5/10min) + heavy call bonus (1.5x for Read/Grep/Task) + cumulative token estimate (strlen/4)
- **Token thresholds**: 150k yellow, 180k orange, 200k red (alongside pressure score — whichever is higher wins)
- **Syntax check before format** — skip formatting if syntax is broken
- **Silent on success** — hooks only inject additionalContext on errors or threshold crossings
- **Formatters**: ruff (Python), shfmt (Shell), gofmt (Go), jq (JSON), prettier (TS/JS)
- **State file**: `/tmp/intercheck-${SESSION_ID}.json`

## Open Questions

None — all decisions made during brainstorm.
