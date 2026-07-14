# Sylveste

Sylveste orchestrates agents by human/machine comparative advantage.

It is an open-source agency platform for building software with agents: a kernel for evidence and events, operating layers for phase discipline and agent execution, and review loops that decide which work belongs to humans, which work belongs to machines, and which work needs both.

## Quick start

Install Clavain and the companion ecosystem in one command:

```bash
curl -fsSL https://raw.githubusercontent.com/mistakeknot/Sylveste/main/install.sh | bash
```

### Prerequisites

**Required:** [jq](https://jqlang.github.io/jq/), [Go 1.22+](https://go.dev/dl/), git

**Why Go?** The intercore kernel (`ic`) and `clavain-cli` are Go binaries built from source during installation. Go 1.22+ is the minimum; 1.24+ is recommended.

**Recommended:** Python 3.10+ with PyYAML, [Node.js 20+](https://nodejs.org/), [yq v4](https://github.com/mikefarah/yq)

Install takes ~2 minutes (power user) or ~30 minutes (full platform). Disk: ~2 GB core, ~5 GB with the complete companion set.

### Managing your installation

```bash
bash install.sh --update      # Update to latest (skip first-time setup)
bash install.sh --uninstall   # Remove all Sylveste components
bash install.sh --dry-run     # Preview what would happen
```

Then open Claude Code in your project and run:

```
/clavain:project-onboard
```

This sets up beads tracking, CLAUDE.md/AGENTS.md, docs structure, observability, and seeds your first roadmap. After that, use `/clavain:route` to start building.

## What you get

- **Comparative-advantage routing:** humans set intent and resolve judgment calls; agents execute bounded work and produce receipts.
- **Clavain:** the reference Claude Code rig for brainstorm → strategy → plan → execute → review → ship.
- **Interverse:** companion plugins that add review, phase tracking, doc freshness, semantic search, TUI testing, and other scoped capabilities.
- **Multi-model review:** Claude, Codex, and Oracle-style second opinions used where their different failure modes help.
- **Evidence loops:** Beads, Interstat, Interspect, and phase gates make work observable enough to improve routing over time.

## Guides

| Guide | Who it's for | Time |
|-------|-------------|------|
| [Power User Guide](docs/guide-power-user.md) | Claude Code users adding Clavain to their workflow | 10 min read |
| [Full Setup Guide](docs/guide-full-setup.md) | Users who want the complete platform (Go services, TUI tools) | 30 min setup |
| [Contributing Guide](docs/guide-contributing.md) | Developers who want to modify or extend Sylveste | 45 min setup |

## How it works

Most agent tools skip the product phases (brainstorm, strategy, specification) and jump straight to code generation. The thinking phases are where the real leverage is. Clavain makes them first-class:

1. **Discover**: scan backlog, surface ready work, recommend next task
2. **Brainstorm**: collaborative dialogue to explore the problem space
3. **Strategize**: structure ideas into a PRD with trackable features
4. **Plan**: write bite-sized implementation tasks with TDD
5. **Execute**: dispatch agents to implement bounded changes
6. **Review**: multi-agent quality gates catch issues before shipping
7. **Ship**: land the change with verification and session reflection

The result is not a claim that agents should replace developers. It is a workflow for deciding, with evidence, which parts of the loop machines can run and which parts still require human taste, context, or authority.

## Philosophy

Three principles, applied recursively: every action produces evidence, evidence earns authority, and authority is scoped and composed. The cycle compounds — more autonomy produces more data, more data improves routing, better routing cuts cost, lower cost enables more autonomy.

See [PHILOSOPHY.md](PHILOSOPHY.md) for the full design bets, tradeoffs, and convictions.

## Plugin ecosystem

The Interverse plugin layer is intentionally modular. Sylveste avoids listing every companion in this README because the useful public contract is the standard, not the inventory. See [docs/canon/plugin-standard.md](docs/canon/plugin-standard.md) for the plugin structure and [the interactive ecosystem diagram](https://generalsystemsventures.com/interchart/) for the current graph.

## Troubleshooting

| Problem | Symptom | Fix |
|---------|---------|-----|
| jq missing | `install.sh` exits immediately | `sudo apt install jq` or `brew install jq` |
| Go too old | Version check fails during install | Install Go 1.22+ from [go.dev](https://go.dev/dl/) |
| `ic` not found | Commands fail after install | Add `export PATH="$HOME/.local/bin:$PATH"` to your shell profile |
| ic build fails | Install exits with Go error | Check `go env GOPATH` and network access |
| Plugins missing | `/clavain:setup` shows gaps | Re-run `install.sh` with Claude Code running |
| `bd` hangs | Beads commands never return | Run `bash .beads/recover.sh` |

Run `/clavain:doctor` for a full health check.

## Architecture reference

Sylveste is a monorepo with six current pillars. This table is a map for contributors, not the public pitch.

| Pillar | Layer | Description |
|--------|-------|-------------|
| [Intercore](https://github.com/mistakeknot/intercore) | L1 (Core) | Orchestration kernel: runs, dispatches, gates, events |
| [Clavain](https://github.com/mistakeknot/Clavain) | L2 (OS) | Self-improving Claude Code agent rig |
| [Skaffen](os/Skaffen/) | L2 (OS) | Sovereign Go agent runtime |
| [Interverse](https://github.com/mistakeknot/interagency-marketplace) | L2-L3 | Companion plugin ecosystem |
| [Autarch](https://github.com/mistakeknot/Autarch) | L3 (Apps) | TUI interfaces (Bigend, Gurgeh, Coldwine, Pollard) |
| [Interspect](interverse/interspect/) | Cross-cutting | Agent performance profiler and routing optimizer |

Additional infrastructure: [Intermute](https://github.com/mistakeknot/intermute) (multi-agent coordination), [Intermesh](https://github.com/mistakeknot/intermesh) (retrieval-gated Agent Skills registry/router), [interbase](https://github.com/mistakeknot/interbase) (SDK), [interbench](https://github.com/mistakeknot/interbench), [interband](https://github.com/mistakeknot/interband).

### Naming convention

All module names are **lowercase** except proper nouns such as **Clavain**, **Sylveste**, **Interverse**, **Autarch**, **Interspect**, **Intercore**, and **Skaffen**.

## License

MIT
