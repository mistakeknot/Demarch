# Demarch

A monorepo for building software with agents, where the review phases matter more than the building phases, and the point is not to remove humans from the loop but to make every moment in the loop count.

Demarch is the platform behind [Clavain](os/clavain/), a self-improving Claude Code agent rig that orchestrates the full development lifecycle from brainstorm to ship. It coordinates Claude, Codex, and GPT-5.2 Pro into something more useful than any of them alone.

## Quick start

Install Clavain and 30+ companion plugins in one command:

```bash
curl -fsSL https://raw.githubusercontent.com/mistakeknot/Demarch/main/install.sh | bash
```

Then open Claude Code and run:

```
/clavain:route
```

## What you get

- **Clavain**: the agent rig (brainstorm → strategy → plan → execute → review → ship)
- **33+ companion plugins**: multi-agent code review, phase tracking, doc freshness, semantic search, TUI testing (the inter-* constellation, because naming things is hard)
- **Multi-model orchestration**: Claude does the heavy lifting, Codex runs parallel tasks, GPT-5.2 Pro provides a second opinion via Oracle
- **Sprint management**: track work with Beads, auto-discover what to work on next

## Guides

| Guide | Who it's for | Time |
|-------|-------------|------|
| [Power User Guide](docs/guide-power-user.md) | Claude Code users adding Clavain to their workflow | 10 min read |
| [Full Setup Guide](docs/guide-full-setup.md) | Users who want the complete platform (Go services, TUI tools) | 30 min setup |
| [Contributing Guide](docs/guide-contributing.md) | Developers who want to modify or extend Demarch | 45 min setup |

## How it works

Most agent tools skip the product phases (brainstorm, strategy, specification) and jump straight to code generation. The thinking phases are where the real leverage is. Clavain makes them first-class:

1. **Discover**: scan backlog, surface ready work, recommend next task
2. **Brainstorm**: collaborative dialogue to explore the problem space
3. **Strategize**: structure ideas into a PRD with trackable features
4. **Plan**: write bite-sized implementation tasks with TDD
5. **Execute**: dispatch agents (Claude subagents or Codex) to implement
6. **Review**: multi-agent quality gates catch issues before shipping
7. **Ship**: land the change with verification and session reflection

## Architecture

Demarch is a monorepo with 5 pillars:

| Pillar | Layer | Description |
|--------|-------|-------------|
| [Intercore](core/intercore/) | L1 (Core) | Orchestration kernel: runs, dispatches, gates, events |
| [Intermute](core/intermute/) | L1 (Core) | Multi-agent coordination service (Go) |
| [Clavain](os/clavain/) | L2 (OS) | Self-improving agent rig: 16 skills, 55 commands |
| [Interverse](interverse/) | L2-L3 | 33+ companion plugins |
| [Autarch](apps/autarch/) | L3 (Apps) | TUI interfaces (Bigend, Gurgeh, Coldwine, Pollard) |

Additional infrastructure: [marketplace](core/marketplace/), [agent-rig](core/agent-rig/), [interbench](core/interbench/), [interband](core/interband/), [interbase](sdk/interbase/).

### Plugin ecosystem

[Interactive ecosystem diagram](https://mistakeknot.github.io/interchart/): explore how all plugins, skills, agents, and services connect.

All plugins are installed from the [interagency-marketplace](https://github.com/mistakeknot/interagency-marketplace).

### Naming convention

All module names are **lowercase** except **Clavain** (proper noun), **Demarch** (project name), **Interverse** (ecosystem name), and **Autarch** (proper noun).

## License

MIT
