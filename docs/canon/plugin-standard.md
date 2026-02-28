# Interverse Plugin Standard

The structural quality bar for every plugin in the Interverse ecosystem. Derived from consistency across 40+ repos. This is the canonical reference — not a suggestion.

## Required Files

Every plugin repo has these 6 root files:

| File | Purpose | Convention |
|------|---------|------------|
| `README.md` | User-facing docs | "What this does" (prose), Installation (marketplace two-step), Usage (slash commands), Architecture (tree) |
| `CLAUDE.md` | Claude Code config only | Overview paragraph, Quick Commands (bash), Design Decisions. No project knowledge — that goes in AGENTS.md |
| `AGENTS.md` | Cross-AI development guide | Standard boilerplate header + plugin-specific content (see below) |
| `PHILOSOPHY.md` | Design bets | Purpose, North Star, Working Priorities, Brainstorming/Planning Doctrine, Decision Filters |
| `LICENSE` | MIT license | Standard MIT text, copyright "MK" |
| `.gitignore` | Excludes | `node_modules/`, `__pycache__/`, `*.pyc`, `.venv/`, `.pytest_cache/`, `.claude/`, `.beads/`, `*.log`, OS/editor files |

## Required Directories

| Directory | Contents |
|-----------|----------|
| `.claude-plugin/` | `plugin.json` (source of truth for name, version, description, components) |
| `skills/` | One directory per skill, each containing `SKILL.md` |
| `scripts/` | At minimum `bump-version.sh` (delegates to `ic publish` or `interbump.sh`) |
| `tests/` | Structural pytest suite with `pyproject.toml` |

## Optional Directories

Present when the plugin needs them, absent otherwise:

| Directory | When present |
|-----------|-------------|
| `commands/` | Plugin provides slash commands (`.md` files with YAML frontmatter) |
| `agents/` | Plugin provides subagent definitions |
| `hooks/` | Plugin registers hooks (`hooks.json`) or provides hook libraries (`lib-*.sh`) |
| `config/` | Plugin has configuration files |
| `docs/` | Plugin has brainstorms, plans, PRDs, specs, or roadmaps |

## Skills Convention

Every skill lives in its own subdirectory under `skills/` and contains a `SKILL.md`:

```
skills/
├── analyze/
│   └── SKILL.md
├── status/
│   ├── SKILL.md
│   └── SKILL-compact.md    # Optional compact version
└── create/
    ├── SKILL.md
    ├── SKILL-compact.md
    ├── references/          # Optional supporting files
    └── templates/
```

### Why subdirectories, not flat files

The flat pattern (`skills/foo.md`) is **not valid**. Use `skills/foo/SKILL.md` instead because:

1. **Claude Code expects it** — the plugin loader resolves each `skills` entry in `plugin.json` as a directory and looks for `SKILL.md` inside it
2. **Companion files** — `SKILL-compact.md`, `references/`, `templates/`, and `workflows/` subdirs only work alongside `SKILL.md` in the same directory
3. **Discoverability** — `plugin.json` lists each skill directory individually (e.g., `./skills/analyze`, `./skills/status`), making the skill inventory explicit

### SKILL.md requirements

Every `SKILL.md` must have YAML frontmatter with at least `description`:

```yaml
---
description: "One sentence — what this skill does and when to use it."
---
```

Additional frontmatter fields (`name`, `user_invocable`, `allowed-tools`, `argument-hint`) are optional but recommended. The structural test suite validates that `description` exists.

### plugin.json skills array

List each skill directory individually — never list the bare `./skills` directory:

```json
{
  "skills": [
    "./skills/analyze",
    "./skills/status",
    "./skills/create"
  ]
}
```

**Wrong:** `"skills": ["./skills"]` — this expects `skills/SKILL.md` to exist at the top level, which is incorrect for multi-skill plugins.

## plugin.json Schema

```json
{
  "name": "plugin-name",
  "version": "X.Y.Z",
  "description": "One sentence — what it does and key stats.",
  "author": { "name": "mistakeknot" },
  "license": "MIT",
  "keywords": ["relevant", "keywords"],
  "skills": ["./skills/skill-name"],
  "commands": ["./commands/command-name.md"],
  "agents": ["./agents/category/agent-name.md"],
  "mcpServers": {}
}
```

- `name`, `version`, `description`, `author`, `skills` are required
- `commands`, `agents`, `mcpServers` only when the plugin has them
- `author.name` is `"mistakeknot"`, not `"MK"`
- Every path in `skills`/`commands`/`agents` must exist on disk

## AGENTS.md Structure

Every AGENTS.md opens with this boilerplate, then has plugin-specific content:

### Standard Header (identical across all plugins)

```markdown
# <plugin-name> — Development Guide

## Canonical References
1. [`PHILOSOPHY.md`](./PHILOSOPHY.md) — direction for ideation and planning decisions.
2. `CLAUDE.md` — implementation details, architecture, testing, and release workflow.

## Philosophy Alignment Protocol
Review [`PHILOSOPHY.md`](./PHILOSOPHY.md) during:
- Intake/scoping
- Brainstorming
- Planning
- Execution kickoff
- Review/gates
- Handoff/retrospective

For brainstorming/planning outputs, add two short lines:
- **Alignment:** ...
- **Conflict/Risk:** ...

If a high-value change conflicts with philosophy, either:
- adjust the plan to align, or
- create follow-up work to update `PHILOSOPHY.md` explicitly.
```

### Plugin-Specific Sections (in this order)

1. **Quick Reference** — table with repo URL, namespace, manifest path, component counts, license
2. **Release workflow** — `scripts/bump-version.sh <version>` command
3. **Overview** — problem, solution, plugin type, current version
4. **Architecture** — annotated directory tree in code block
5. **How It Works** — subsections for each major workflow
6. **Component Conventions** — per-type subsections (Skills, Commands, Hooks, Agents, Scripts)
7. **Integration Points** — table of relationships with other plugins
8. **Testing** — how to run tests
9. **Validation Checklist** — bash commands to verify component counts
10. **Known Constraints** — gotchas and limitations

Not every plugin needs every section. Omit sections that would be empty or trivial.

## CLAUDE.md Structure

Claude Code configuration only. No project knowledge.

```markdown
# <plugin-name>

> See `AGENTS.md` for full development guide.

## Overview
<One paragraph: component counts, architecture, companion context.>

## Quick Commands
<bash code block: test locally, validate structure, manifest check>

## Design Decisions (Do Not Re-Ask)
<Bullet list of key architectural decisions>
```

Target: 30-60 lines. Hard cap: 80 lines. If it's longer, project knowledge has leaked in.

## PHILOSOPHY.md Structure

```markdown
# <plugin-name> Philosophy

## Purpose
<One paragraph: what, role in Demarch, component counts.>

## North Star
<One sentence: the single optimizable metric.>

## Working Priorities
<3 bullets, ordered by importance.>

## Brainstorming Doctrine
<4 numbered items — identical boilerplate across all plugins.>

## Planning Doctrine
<4 numbered items — identical boilerplate across all plugins.>

## Decision Filters
<4 bullet questions specific to this plugin.>

## Evidence Base
<Brainstorms/plans analyzed, representative artifacts.>
```

## README.md Structure

```markdown
# <plugin-name>

<One sentence.>

## What this does
<2-4 paragraphs of prose. No bullet lists in this section.>

## Installation
<Marketplace two-step: add marketplace, install plugin.>

## Usage
<Slash command examples in code blocks.>

## Architecture
<Directory tree in code block with inline annotations.>

## Design decisions
<Bullet list of key tradeoffs.>

## License
MIT
```

No badges. No CI shields. No changelogs.

## Structural Tests

Every plugin has `tests/` with:

```
tests/
├── pyproject.toml          # name: <plugin>-tests, requires-python >= 3.12
├── uv.lock                 # Locked deps
└── structural/
    ├── conftest.py          # project_root, skills_dir, plugin_json fixtures
    ├── helpers.py           # parse_frontmatter(path)
    ├── test_structure.py    # plugin.json validity, required files, script executability
    └── test_skills.py       # Skill count, frontmatter validation
```

### pyproject.toml

```toml
[project]
name = "<plugin>-tests"
version = "0.1.0"
requires-python = ">=3.12"
dependencies = ["pytest>=8.0", "pyyaml>=6.0"]

[tool.pytest.ini_options]
testpaths = ["structural"]
pythonpath = ["structural"]
```

### Minimum test coverage

- `plugin.json` is valid JSON with required fields
- Every skill/command/agent listed in plugin.json exists on disk
- Required root files exist (README, CLAUDE, AGENTS, PHILOSOPHY, LICENSE, .gitignore)
- All scripts are executable
- Component counts match expected values
- SKILL.md files have valid YAML frontmatter with `name` and `description`

Run with: `cd tests && uv run pytest -q`

## Version Management

- Source of truth: `.claude-plugin/plugin.json` `version` field
- Marketplace must match: `core/marketplace/.claude-plugin/marketplace.json`
- Bump script: `scripts/bump-version.sh` delegates to `ic publish` (preferred) or `interbump.sh` (fallback)
- Auto-publish hook runs `ic publish --auto` on `git push` (when configured)

## Marketplace Registration

Each plugin has an entry in `core/marketplace/.claude-plugin/marketplace.json`:

```json
{
  "name": "plugin-name",
  "source": {
    "source": "url",
    "url": "https://github.com/mistakeknot/<plugin-name>.git"
  },
  "description": "Marketplace listing copy (may differ slightly from plugin.json).",
  "version": "X.Y.Z",
  "keywords": ["relevant", "keywords"],
  "strict": true
}
```

All 6 fields required. URL must end with `.git`. Version must match plugin.json.
