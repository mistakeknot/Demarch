# Contributing Guide

**Time:** 45 minutes for full setup

**Prerequisites:** Everything in [Full Setup Guide](guide-full-setup.md), plus familiarity with Go and/or Claude Code plugin development.

## Clone the monorepo

```bash
git clone https://github.com/mistakeknot/Demarch.git
cd Demarch
```

Each subproject (`os/clavain`, `interverse/interflux`, `core/intermute`, etc.) keeps its own `.git` and GitHub repo. The monorepo is a development workspace, not a git monorepo.

## Project structure

```
os/clavain/           # Self-improving agent rig (L2)
interverse/           # 33+ companion plugins (L2-L3)
core/
  intercore/          # Orchestration kernel (L1)
  intermute/          # Multi-agent coordination service (L1)
  marketplace/        # Plugin marketplace registry
  agent-rig/          # Agent configuration
apps/
  autarch/            # TUI interfaces (L3)
  intercom/           # Multi-runtime AI assistant
sdk/
  interbase/          # Shared integration SDK
scripts/              # Shared scripts (interbump.sh)
docs/                 # Shared documentation
```

Layers describe dependency: L1 (core) has no upward dependencies, L2 (OS) depends on L1, L3 (apps) depends on L1+L2.

## Development workflow

### Trunk-based development

Commits go directly to `main`. No feature branches unless explicitly discussed. This keeps the feedback loop tight.

### Making changes

1. Read the subproject's `CLAUDE.md` and `AGENTS.md` for conventions
2. Create a bead to track work:
   ```bash
   bd create --title="What I'm doing" --type=task --priority=2
   ```
3. Work with Clavain:
   ```
   /clavain:route iv-<bead-id>
   ```
4. Commit and push to main

### Testing

| Component | Command | Notes |
|-----------|---------|-------|
| Autarch | `cd apps/autarch && go test -race ./...` | Always use `-race` flag |
| Intermute | `cd core/intermute && go test -race ./...` | |
| Intercore | `cd core/intercore && go test -race ./...` | |
| Plugins (syntax) | `bash -n hooks/*.sh` | Syntax check all hook scripts |
| Plugin (validate) | `/plugin-dev:plugin-validator` | Structural validation |

### Code review

All changes go through multi-agent review:

```
/clavain:quality-gates
```

This dispatches 7 specialized agents (architecture, safety, correctness, quality, user/product, performance, game design) to review your changes.

For cross-AI review (sends to GPT-5.2 Pro for a second opinion):

```
/interpeer
```

## Plugin development

### Local testing

Test a plugin locally without installing to marketplace:

```bash
claude --plugin-dir /path/to/your-plugin
```

### Plugin structure

```
your-plugin/
  .claude-plugin/
    plugin.json          # Manifest (name, version, description)
  commands/              # Slash commands (auto-discovered .md files)
  skills/                # Skills with SKILL.md descriptors
  hooks/
    hooks.json           # Hook bindings
    *.sh                 # Hook scripts
  agents/                # Agent definitions
```

### Publishing

After pushing changes:

```
/interpub:release <version>
```

This bumps version in all locations, commits, pushes, and updates the marketplace.

### Naming conventions

- All module names are **lowercase**: `interflux`, `intermute`, `interkasten`
- Exceptions: **Clavain** (proper noun), **Demarch** (project name), **Interverse** (ecosystem name), **Autarch** (proper noun), **Interspect** (proper noun)
- GitHub repos match: `github.com/mistakeknot/interflux`

## Key files

| File | Purpose |
|------|---------|
| `CLAUDE.md` | Quick reference for AI agents (per-subproject) |
| `AGENTS.md` | Comprehensive dev guide (per-subproject) |
| `plugin.json` | Plugin manifest |
| `agent-rig.json` | Plugin companion/dependency declarations |
| `.beads/` | Issue tracking database |

## What's next

Start working: `/clavain:route`

Read the workflow guide: [Power User Guide](guide-power-user.md)

Learn about the full platform: [Full Setup Guide](guide-full-setup.md)
