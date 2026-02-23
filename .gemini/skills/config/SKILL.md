---
name: config
description: "Interverse driver capability: config"
---
# Gemini Skill: config

You have activated the config capability.

## Base Instructions
# Clavain Engineering Conventions

> Installed by agent-rig. These conventions complement your project's CLAUDE.md.

## Tool Usage Discipline
- Prefer Read/Edit/Grep tools over Bash for file operations
- Always Read a file before Edit — never edit blind
- Use Glob for file search (not find/ls), Grep for content search (not grep/rg)
- Reserve Bash for system commands that require shell execution

## Settings Hygiene
- Never use heredocs in Bash tool calls — Write the content first, reference the file
- Never use multi-line for/while loops in Bash — use one-liners or temp scripts
- Never inline long prompts in Bash — write to temp file, reference it
- Keep Bash commands short and wildcard-friendly (start with recognizable prefix)
- Shell fragments (do, done, fi) in settings are always bugs from broken loop approvals

## Git Workflow
- Trunk-based development: commit directly to main unless explicitly asked otherwise
- Do not create feature branches or worktrees for normal work
- Session close checklist: git status → git add → commit → push

## Continuous Learning
Record insights to project memory immediately when you:
- Discover a subtle bug (root cause + fix pattern)
- Hit a library/framework gotcha
- Find an architectural fact
- Get corrected by the user
- Solve a debugging puzzle

Record the "why" — not just "do X" but "do X because Y breaks otherwise."

## Documentation Standards
Every non-trivial project needs:
- **CLAUDE.md** — Minimal quick reference (overview, status, quick commands, design decisions)
- **AGENTS.md** — Comprehensive dev guide (architecture, setup, API, troubleshooting)

Keep CLAUDE.md short. Troubleshooting, architecture, and workflows belong in AGENTS.md.

## Unexpected Changes Policy
When encountering unexpected local changes:
- Report that files exist
- Do not inspect, stage, or edit without explicit user instruction

## Workflow Patterns
After plan simplification (reviewers cut scope), preserve cut research in an "Original Intent" section with trigger-to-feature mappings for future iterations.


