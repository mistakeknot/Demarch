# Contributing Guide

**Time:** 45 minutes for full setup

**Prerequisites:** Everything in [Full Setup Guide](guide-full-setup.md), plus familiarity with Go and/or Claude Code plugin development.

## Fork and clone

1. Fork the repo you want to contribute to on GitHub
2. Clone your fork:

```bash
git clone https://github.com/<your-username>/Demarch.git
cd Demarch
```

Each subproject (`os/clavain`, `interverse/interflux`, `core/intermute`, etc.) keeps its own `.git` and GitHub repo. If you're contributing to a subproject, fork and clone that repo directly.

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

### Branch and PR

All external contributions come through pull requests:

1. Create a feature branch from `main`:
   ```bash
   git checkout -b your-branch-name
   ```
2. Make your changes, following the subproject's `CLAUDE.md` and `AGENTS.md` conventions
3. Run tests (see [Testing](#testing) below)
4. Push your branch and open a PR against `main`

**Branch protection is enabled** on `main` for all product repos. Direct pushes are blocked for non-admins. PRs require at least one approving review before merge.

### Commit conventions

Use [Conventional Commits](https://www.conventionalcommits.org/):

```
feat(scope): add new feature
fix(scope): fix the bug
refactor(scope): restructure without behavior change
docs(scope): documentation only
ci(scope): CI/CD changes
test(scope): test additions or fixes
```

Keep commits focused. One logical change per commit.

### Testing

Run the relevant tests before opening a PR:

| Component | Command | Notes |
|-----------|---------|-------|
| Autarch | `cd apps/autarch && go test -race ./...` | Always use `-race` flag |
| Intermute | `cd core/intermute && go test -race ./...` | |
| Intercore | `cd core/intercore && go test -race ./...` | |
| Go modules | `go build ./... && go vet ./... && go test -race ./...` | Standard for all Go repos |
| Plugins (syntax) | `bash -n hooks/*.sh` | Syntax check all hook scripts |
| Plugin (validate) | `/plugin-dev:plugin-validator` | Structural validation |

CI runs automatically on PRs. All checks must pass before merge.

### Code review

PRs are reviewed by maintainers. For larger changes, the maintainer may run multi-agent review:

```
/clavain:quality-gates
```

This dispatches specialized agents (architecture, safety, correctness, quality) to review changes. You don't need to run this yourself — the maintainer will.

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

Read the [Power User Guide](guide-power-user.md) for advanced workflows.

Learn about the full platform: [Full Setup Guide](guide-full-setup.md)
