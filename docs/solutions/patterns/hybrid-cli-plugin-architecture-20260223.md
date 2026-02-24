---
title: "Hybrid CLI + Plugin Architecture for Interverse Modules"
category: patterns
severity: medium
date: 2026-02-23
tags: [architecture, plugin-design, cli, interverse, separation-of-concerns, skills]
related: [hooks-vs-skills-separation-plugin-20260211, cli-plugin-low-agent-adoption-vs-mcp-20260211]
---

## Problem

Some Interverse modules provide functionality that has standalone value beyond Claude Code sessions — expense tracking, data processing, report generation. Building these as pure plugins (hooks + skills + MCP) couples the core logic to Claude Code's runtime, making the tool untestable from terminal and unusable without an active session.

Building them as pure CLI tools misses the opportunity for AI-assisted workflows (ambiguous classification, natural language querying, interactive review).

## Investigation

Analyzed existing Interverse modules and found two prior patterns:

| Pattern | Example | Limitation |
|---------|---------|------------|
| Pure plugin (skills only) | interpath, interwatch | Cannot run from terminal without Claude Code |
| CLI with MCP wrapper | tldr-swinton | MCP adds complexity; tool descriptions compete for context budget |

Neither pattern cleanly separates "core tool logic" from "AI-assisted workflows".

## Solution

Split into two locations in the monorepo:

```
apps/<name>/              → standalone Python/Go CLI (the real tool)
  src/<name>/
  config/
  tests/
  pyproject.toml

interverse/<name>/        → Interverse plugin (thin wrapper)
  plugin.json
  skills/
  CLAUDE.md
```

**The CLI** owns all data, logic, and persistence. It's independently installable, testable, and scriptable. No Claude Code dependency.

**The plugin** provides only SKILL.md files — no hooks, no MCP server. Skills are prompts that tell Claude how to invoke the CLI via Bash, plus reasoning instructions for handling ambiguous cases (classification, matching, analysis).

### Key principles

1. **Skills don't need code** — they're prompts that describe when and how to invoke existing CLI commands. The "code" is the CLI tool itself.

2. **AI adds reasoning, not data flow** — the CLI handles all I/O, persistence, and report generation. Claude's contribution is reasoning about edge cases: "this transaction description doesn't match any rule, but the raw text mentions Tailscale."

3. **The plugin depends on the CLI, never the reverse** — the CLI must work without the plugin installed. The plugin's skills assume the CLI is available.

4. **Keep the plugin surface area minimal** — one skill per workflow, not one skill per CLI command. Skills orchestrate multi-step flows (ingest + categorize + report gaps), not individual operations.

### When to use this pattern

- The tool has value as a standalone CLI (not just Claude Code integration)
- The tool processes data that benefits from AI reasoning on edge cases
- Users may want to script/cron the tool without Claude Code
- The core logic is complex enough to warrant its own test suite

### When NOT to use this pattern

- The tool is purely a Claude Code enhancement (use pure plugin)
- The tool needs real-time MCP integration (use MCP server pattern)
- The tool is simple enough to live entirely in a SKILL.md prompt

## Example: interfin

```
apps/interfin/           → Python CLI: CSV ingest, PDF extraction, SQLite, reports
interverse/interfin/     → 4 skills: /ingest (guided), /review (conversational),
                            /link (receipt matching), /audit (validation)
```

The CLI handles all data processing. The plugin's `/interfin:review` skill lets you ask "what did I spend on AI tools this quarter?" — Claude reads the SQLite DB and reasons about the answer. The CLI alone can generate the same report via `interfin report --year 2026`, just without conversational interaction.
