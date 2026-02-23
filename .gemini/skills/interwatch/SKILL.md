---
name: interwatch
description: "Doc freshness monitoring — drift detection, confidence scoring, and auto-refresh orchestration across product artifacts and code docs. Companion plugin for Clavain."
---
# Gemini Skill: interwatch

You have activated the interwatch capability.

## Base Instructions
# interwatch — Development Guide

## Architecture

interwatch is a doc freshness monitoring system for Claude Code. It abstracts the pattern: "has something changed in the project that makes this document outdated?"

### Core Abstractions

- **Watchable** — a document that can be monitored (roadmap, PRD, AGENTS.md, etc.)
- **Signal** — an event that might cause drift (bead closed, file renamed, version bumped)
- **Generator** — the plugin that regenerates the doc (interpath or interdoc)
- **Confidence Tier** — how certain we are that drift occurred (Certain/High/Medium/Low)

### Skill: doc-watch

The single skill orchestrates drift detection:

```
SKILL.md (orchestrator)
  → phases/detect.md   (signal evaluation)
  → phases/assess.md   (confidence scoring)
  → phases/refresh.md  (generator dispatch)
```

### Configuration

- `config/watchables.yaml` — declarative registry of watched documents
- `hooks/lib-watch.sh` — bash utilities for signal detection (git, beads, file checks)

### State

Per-project state in `.interwatch/` (gitignored):
- `drift.json` — current drift scores per watchable
- `history.json` — refresh history (when, what, confidence)
- `last-scan.json` — snapshot for change detection

## Component Conventions

### Skills

- One skill directory: `skills/doc-watch/`
- SKILL.md has YAML frontmatter with `name` and `description`
- Phase files in `phases/` subdirectory
- Reference files in `references/` subdirectory

### Commands

- 3 commands in `commands/`: watch.md, status.md, refresh.md
- Each has YAML frontmatter with `name` and `description`

### Hooks

- `hooks/lib-watch.sh` — bash library (not a hook handler), provides signal detection functions

## Testing

```bash
cd /root/projects/Interverse/plugins/interwatch
uv run pytest tests/structural/ -v
```

### Test Categories

- **test_structure.py** — plugin.json validity, directory structure, marker file, lib-watch syntax
- **test_skills.py** — skill count, frontmatter, phase files, reference files
- **test_commands.py** — command count, frontmatter, expected commands exist

## Development Workflow

1. Edit skill/command/config files
2. Run structural tests: `uv run pytest tests/structural/ -v`
3. Test locally: `claude --plugin-dir /root/projects/Interverse/plugins/interwatch`
4. Bump version and publish: `scripts/bump-version.sh <version>`


