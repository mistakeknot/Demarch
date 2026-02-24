# Demarch

Autonomous software development agency platform — brainstorm, plan, execute, review, and ship with multi-agent orchestration.

## Quick Start

Install Clavain and 30+ companion plugins in one command:

```bash
curl -fsSL https://raw.githubusercontent.com/mistakeknot/Demarch/main/install.sh | bash
```

Then open Claude Code and run:

```
/clavain:route
```

## What You Get

- **Clavain** — AI workflow engine: brainstorm → strategy → plan → execute → review → ship
- **33+ companion plugins** — multi-agent code review, phase tracking, doc freshness, semantic search, TUI testing
- **Multi-model orchestration** — Claude, Codex, and GPT-5.2 Pro working together
- **Sprint management** — track work with Beads, auto-discover what to work on next

## Guides

| Guide | Who It's For | Time |
|-------|-------------|------|
| [Power User Guide](docs/guide-power-user.md) | Claude Code users adding Clavain to their workflow | 10 min read |
| [Full Setup Guide](docs/guide-full-setup.md) | Users who want the complete platform (Go services, TUI tools) | 30 min setup |
| [Contributing Guide](docs/guide-contributing.md) | Developers who want to modify or extend Demarch | 45 min setup |

## How It Works

Clavain orchestrates a disciplined development lifecycle:

1. **Discover** — scan backlog, surface ready work, recommend next task
2. **Brainstorm** — collaborative dialogue to explore the problem space
3. **Strategize** — structure ideas into a PRD with trackable features
4. **Plan** — write bite-sized implementation tasks with TDD
5. **Execute** — dispatch agents (Claude subagents or Codex) to implement
6. **Review** — multi-agent quality gates catch issues before shipping
7. **Ship** — land the change with verification and session reflection

## Architecture

Demarch is a monorepo with 5 pillars:

| Pillar | Layer | Description |
|--------|-------|-------------|
| [Intercore](core/intercore/) | L1 (Core) | Orchestration kernel — runs, dispatches, gates, events |
| [Intermute](core/intermute/) | L1 (Core) | Multi-agent coordination service (Go) |
| [Clavain](os/clavain/) | L2 (OS) | Self-improving agent rig — 16 skills, 55 commands |
| [Interverse](interverse/) | L2-L3 | 33+ companion plugins |
| [Autarch](apps/autarch/) | L3 (Apps) | TUI interfaces (Bigend, Gurgeh, Coldwine, Pollard) |

Additional infrastructure: [marketplace](core/marketplace/), [agent-rig](core/agent-rig/), [interbench](core/interbench/), [interband](core/interband/), [interbase](sdk/interbase/).

### Plugin Ecosystem

[Interactive Ecosystem Diagram](https://mistakeknot.github.io/interchart/) — explore how all plugins, skills, agents, and services connect.

All plugins are installed from the [interagency-marketplace](https://github.com/mistakeknot/interagency-marketplace).

### Naming Convention

All module names are **lowercase** except **Clavain** (proper noun), **Demarch** (project name), **Interverse** (ecosystem name), and **Autarch** (proper noun).

## License

MIT
