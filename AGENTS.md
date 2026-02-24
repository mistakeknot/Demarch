# Demarch — Agent Development Guide

## Overview

Demarch is the physical monorepo for the open-source autonomous software development agency platform. It contains five pillars: **Intercore** (`/core`) the orchestration kernel, **Clavain** (`/os`) the agent OS and reference agency, **Interverse** (`/interverse`) 33+ companion plugins, **Autarch** (`/apps`) the TUI surfaces, and **Interspect** (cross-cutting profiler, currently housed in Clavain). Plus `sdk/` for shared libraries (interbase). Each module keeps its own `.git` as a nested independent repo. The root `Demarch/` also has a `.git` for the monorepo skeleton (scripts, docs, CLAUDE.md). Git operations apply to the nearest `.git`; verify with `git rev-parse --show-toplevel`.

## Agent Quickstart

1. Read this file (root `AGENTS.md`) — you're doing it now.
2. Run `bd ready` to see available work.
3. Before editing any module, read its local `AGENTS.md` (or `CLAUDE.md` as fallback).
4. Verify which repo you're in: `git rev-parse --show-toplevel`.
5. When done: `bd close <id>`, commit, `bd sync`, push.

## Instruction Loading Order

Use nearest, task-scoped instruction loading instead of reading every instruction file in the repo.

1. Read root `AGENTS.md` once at session start.
2. Before editing files in a module, read that module's local `AGENTS.md`.
3. If local `AGENTS.md` is missing, read that module's local `CLAUDE.md` as fallback.
4. For cross-module changes, repeat steps 2-3 for each touched module.
5. Resolve conflicts with this precedence: local `AGENTS.md` > local `CLAUDE.md` > root `AGENTS.md` > root `CLAUDE.md`.

## Glossary

| Term | Meaning |
|------|---------|
| **Pillar** | One of the 5 top-level components of Demarch: Intercore, Clavain, Interverse, Autarch, Interspect. Organizational term — use "layer" (L1/L2/L3) for architectural dependency. |
| **Layer** | Architectural dependency level: L1 (Kernel/Intercore), L2 (OS/Clavain + Drivers/Interverse), L3 (Apps/Autarch). Interspect is cross-cutting. |
| **Beads** | File-based issue tracker (`bd` CLI). Each project can have a `.beads/` database. All active tracking is at Demarch root. |
| **Plugin** | A Claude Code extension (skills, commands, hooks, agents, MCP servers) installed from the marketplace. |
| **MCP** | Model Context Protocol — enables plugins to expose tools as server processes that Claude Code calls directly. |
| **Driver** | A companion plugin (part of the Interverse pillar) that extends Clavain with one capability. Also called "companion plugin." |
| **Marketplace** | The `interagency-marketplace` registry at `core/marketplace/` — JSON catalog of all published plugins. |
| **Interspect** | Adaptive profiler pillar — reads kernel events, proposes OS configuration changes. Cross-cutting (not a layer). |

## Directory Layout

| Path | Pillar | Description |
|------|--------|-------------|
| `apps/autarch/` | Autarch | Swappable TUI interfaces (Bigend, Gurgeh, Coldwine, Pollard) |
| `apps/intercom/` | Autarch | Multi-runtime AI assistant (Claude, Gemini, Codex) + messaging |
| `os/clavain/` | Clavain | Autonomous software agency — brainstorm to ship |
| *(housed in `os/clavain/`)* | Interspect | Adaptive profiler — evidence collection, pattern detection, routing overlays. Cross-cutting pillar; code is in Clavain's hooks/scripts, not a separate repo. |
| `core/intercore/` | Intercore | Orchestration kernel (Go) |
| `core/intermute/` | Intercore | Multi-agent coordination service (Go, SQLite) |
| `core/marketplace/` | Intercore | interagency plugin marketplace registry |
| `core/interbench/` | — | Eval harness for driver capabilities (Go CLI; tooling, not kernel) |
| `core/agent-rig/` | Intercore | Agent configuration |
| `core/interband/` | Intercore | Sideband protocol |
| `interverse/intercraft/` | Interverse | Agent-native architecture patterns and audit |
| `interverse/intercheck/` | Interverse | Code quality guards and session health monitoring (hooks) |
| `interverse/interdev/` | Interverse | MCP CLI developer tooling and tool discovery |
| `interverse/interdoc/` | Interverse | Recursive AGENTS.md generator with cross-AI critique |
| `interverse/interfluence/` | Interverse | Voice profile analysis and style adaptation (MCP) |
| `interverse/interflux/` | Interverse | Multi-agent document review + research engine (MCP) |
| `interverse/interform/` | Interverse | Design patterns and visual quality for interfaces |
| `interverse/interject/` | Interverse | Ambient discovery and research engine (MCP, Python) |
| `interverse/interkasten/` | Interverse | Bidirectional Notion sync with adaptive documentation (MCP) |
| `interverse/intersearch/` | Interverse | Shared embedding client + Exa semantic search (used by interject, interflux) |
| `interverse/interline/` | Interverse | Dynamic statusline for Claude Code |
| `interverse/interlock/` | Interverse | Multi-agent file coordination via intermute (MCP) |
| `interverse/internext/` | Interverse | Work prioritization and tradeoff analysis |
| `interverse/interpath/` | Interverse | Product artifact generator (roadmaps, PRDs, changelogs) |
| `interverse/interphase/` | Interverse | Phase tracking, gate validation, work discovery |
| `interverse/interpub/` | Interverse | Safe plugin version bumping and publishing |
| `interverse/interslack/` | Interverse | Slack integration via slackcli |
| `interverse/interstat/` | Interverse | Token efficiency benchmarking for agent workflows |
| `interverse/interwatch/` | Interverse | Doc freshness monitoring and drift detection |
| `interverse/interlearn/` | Interverse | Cross-repo institutional knowledge index |
| `interverse/interleave/` | Interverse | Deterministic skeleton + LLM islands pattern (spec + library) |
| `interverse/interlens/` | Interverse | Cognitive augmentation lenses (FLUX podcast) |
| `interverse/intermap/` | Interverse | Project-level code mapping + architecture analysis (MCP) |
| `interverse/intermem/` | Interverse | Memory management for agent sessions |
| `interverse/intermux/` | Interverse | Agent activity visibility + tmux monitoring (MCP) |
| `interverse/interpeer/` | Interverse | Cross-AI peer review (Oracle/GPT escalation) |
| `interverse/interserve/` | Interverse | Codex spark classifier + context compression (MCP) |
| `interverse/intersynth/` | Interverse | Multi-agent synthesis engine (verdict aggregation) |
| `interverse/intertest/` | Interverse | Engineering quality disciplines (TDD, debugging, verification) |
| `interverse/interchart/` | Interverse | Live ecosystem diagram generator (GitHub Pages) |
| `interverse/tldr-swinton/` | Interverse | Token-efficient code context via MCP server |
| `interverse/tool-time/` | Interverse | Tool usage analytics for Claude Code and Codex CLI |
| `interverse/tuivision/` | Interverse | TUI automation and visual testing via MCP server |
| `sdk/interbase/` | Interverse | Shared integration SDK for dual-mode plugins |
| `scripts/` | — | Cross-project scripts (interbump.sh) |
| `docs/` | — | **Platform-level** documentation only (cross-cutting brainstorms, research, solutions) |

> **Docs convention:** `Demarch/docs/` is for platform-level work only. Each subproject keeps its own docs at `Demarch/{core|os|interverse|apps|sdk}/<subproject>/docs/` (e.g., `interverse/interlock/docs/`, `core/intercore/docs/`).
>
> **Artifact naming convention:** See [`CONVENTIONS.md`](CONVENTIONS.md) for strict canonical roadmap/vision/PRD paths. Compatibility filenames are not part of the active convention.

## Module Relationships

```
Clavain (L2 OS) uses these Interverse drivers:
  interphase, interline, interflux, interpath, interwatch,
  interlock, intercraft, interdev, interform, internext, interslack

Dependency chains:
  Clavain → interlock → intermute (L1 service)
  Clavain → interflux → intersearch (shared lib)
  interject → intersearch (shared lib)

interject (MCP)    ← ambient discovery engine, uses intersearch for embeddings + Exa
intersearch (lib)  ← shared embedding client + Exa search (used by interject, interflux)
intermute (service) ← used by interlock for file reservation + messaging
interpub           ← used to publish all plugins
interdoc           ← generates AGENTS.md for all projects
interfluence       ← standalone voice profiling
interkasten        ← standalone Notion sync
tldr-swinton       ← standalone code context MCP
intercheck         ← standalone code quality guards + context monitoring
interstat          ← standalone token efficiency benchmarking
intersynth         ← multi-agent synthesis (used by interflux)
interpeer          ← cross-AI peer review (Oracle/GPT escalation)
intertest          ← engineering quality disciplines (TDD, debugging)
interlearn         ← cross-repo institutional knowledge index
interlens          ← cognitive augmentation lenses
intermap           ← code mapping + architecture analysis MCP
intermux           ← agent activity visibility + tmux monitoring MCP
interserve         ← Codex spark classifier + context compression MCP
interchart         ← ecosystem diagram generator
tool-time          ← standalone usage analytics
tuivision          ← standalone TUI testing MCP
interbase (sdk)    ← shared integration SDK for dual-mode drivers
marketplace        ← registry for all published plugins
```

## Bead Tracking

All work is tracked at the **Demarch root level** using the monorepo `.beads/` database. Module-level `.beads/` databases are read-only archives of historical closed beads.

- Create beads from the Demarch root: `cd /root/projects/Demarch && bd create --title="[module] Description" ...`
- Use `[module]` prefix in bead titles to identify the relevant module (e.g., `[interlock]`, `[interflux]`, `[clavain]`)
- Filter by module: `bd list --status=open | grep -i interlock`
- Cross-module beads use multiple prefixes: `[interlock/intermute]`

### Roadmap

The platform roadmap is at [`docs/demarch-roadmap.md`](docs/demarch-roadmap.md) with machine-readable canonical output in [`docs/roadmap.json`](docs/roadmap.json). Regenerate both with `/interpath:roadmap` from the Demarch root. Auto-generate module-level roadmaps from beads with `scripts/generate-module-roadmaps.sh` or `/interpath:propagate`.

`scripts/sync-roadmap-json.sh` generates the canonical JSON rollup from the root roadmap and beads data. `scripts/generate-module-roadmaps.sh` auto-generates per-module `docs/roadmap.md` files from beads state.

## Naming Convention

- All module directory names are **lowercase** (hyphens allowed): `interflux`, `intermute`, `tldr-swinton`, `tool-time`
- In prose and documentation, use **lowercase**: `interflux provides review agents`
- Exception: **Demarch** (platform name) and the five pillar names: **Intercore**, **Clavain**, **Interverse**, **Autarch**, **Interspect**
- GitHub repos: `github.com/mistakeknot/<lowercase-name>`

## Prerequisites

Required tools (all pre-installed on this server):

| Tool | Used by | Purpose |
|------|---------|---------|
| `jq` | interbump, hooks | JSON manipulation |
| `uv` | tldr-swinton, interject, intersearch | Python package management |
| `go` (1.24+) | intermute, interlock, interbench | Go builds and tests |
| `node`/`npm` | interkasten | MCP server build |
| `python3` | tldr-swinton, tool-time, interject | CLI tools, analysis scripts |
| `bd` | all | Beads issue tracker CLI |

**Secrets** (in environment or dotfiles — never commit):
- `INTERKASTEN_NOTION_TOKEN` — Notion API token for interkasten sync
- `EXA_API_KEY` — Exa search API for interject and interflux research agents
- `SLACK_TOKEN` — Slack API for interslack

## Development Workflow

Each subproject under `apps/`, `os/`, `core/`, `interverse/`, and `sdk/` is an independent git repo with its own `.git`. The root `Demarch/` directory also has a `.git` for the monorepo skeleton (`scripts/`, `docs/`, `.beads/`, `CLAUDE.md`, `AGENTS.md`). **Git commands operate on whichever `.git` is nearest** — always verify with `git rev-parse --show-toplevel` if unsure which repo you're in. To work on a specific module:

```bash
cd interverse/interflux  # from repo root
# Each module has its own CLAUDE.md, AGENTS.md, .git
```

### Running and testing by module type

**Plugins (hooks/skills/commands only):**
```bash
claude --plugin-dir /root/projects/Demarch/interverse/<name>
# Structural tests (if present):
cd interverse/<name> && uv run pytest tests/structural/ -v
```

**MCP server plugins** (interkasten, interlock, interject, tldr-swinton, tuivision, interflux, intermux, intermap, interfluence, interserve):
```bash
# Build/install the server first, then test via Claude Code.
# Entrypoints vary — check each module's local AGENTS.md. Examples:
cd interverse/interkasten/server && npm install && npm run build && npm test
cd interverse/interlock && bash scripts/build.sh && go test ./...
cd interverse/tldr-swinton && uv tool install -e .  # installs `tldrs` CLI
```

**Kernel** (intercore):
```bash
cd core/intercore
go build -o ic ./cmd/ic   # produces the `ic` CLI binary
go test ./...              # run all tests
./ic --help                # verify
```

**Service** (intermute):
```bash
cd core/intermute
go run ./cmd/intermute     # starts on :7338
go test ./...              # run all tests
```

**Infra** (interbench):
```bash
cd core/interbench && go build -o interbench . && ./interbench --help
```

### Publishing

In Claude Code chat, use the interpub slash command:

```
/interpub:release <version>
```

Or from a terminal, use the bump script directly:

```bash
cd interverse/interflux
scripts/bump-version.sh 0.2.1            # bump + commit + push
scripts/bump-version.sh 0.2.1 --dry-run  # preview only
```

Both methods call the same underlying engine (`scripts/interbump.sh`). All `/interpath:*`, `/interpub:*`, etc. are **Claude Code slash commands** — run them inside a Claude Code session, not from a terminal.

## Plugin Dev/Publish Gate

Applies to work in `os/clavain/` and `interverse/*`.

Before claiming a plugin release is complete:

1. Run module-appropriate checks from **Running and testing by module type**.
2. Publish only via supported entrypoints:
   - Claude Code: `/interpub:release <version>`
   - Terminal (from plugin root): `scripts/bump-version.sh <version>`
   - Optional preflight: `scripts/bump-version.sh <version> --dry-run`
3. Do not hand-edit version files or marketplace versions for normal releases; `scripts/interbump.sh` is the source of truth.
4. Release is complete only when both pushes succeed:
   - plugin repo push
   - `core/marketplace` push
5. If the plugin includes hooks, preserve the post-bump/cache-bridge behavior from `interbump` (do not bypass with ad-hoc scripts).
6. After publish, restart Claude Code sessions so the new plugin version is picked up.

### Ecosystem Diagram (interchart)

After any change that adds, removes, or renames a plugin, skill, agent, MCP server, or hook, regenerate the live ecosystem diagram:

```bash
bash interverse/interchart/scripts/regenerate-and-deploy.sh  # from repo root
```

This scans the monorepo, rebuilds the HTML, and pushes to GitHub Pages. No manual intervention needed — just run the command as a final step.

### Cross-repo changes

When a change spans multiple repos (e.g., adding an MCP tool to interlock that requires an intermute API change):

1. Make changes in each repo independently
2. Commit and push the **dependency first** (e.g., intermute before interlock)
3. Reference the same Interverse-level bead in both commit messages
4. Always verify you're in the right repo: `git rev-parse --show-toplevel`

## Version Bumping (interbump)

All plugins and Clavain share a single version bump engine at `scripts/interbump.sh`. Each module's `scripts/bump-version.sh` is a thin wrapper that delegates to it.

### How it works

1. Reads plugin name and current version from `.claude-plugin/plugin.json` via **jq**
2. Auto-discovers version files: `plugin.json` (always), plus `pyproject.toml`, `package.json`, `server/package.json`, `agent-rig.json`, `docs/PRD.md` if they exist
3. Finds marketplace by walking up from plugin root looking for `core/marketplace/` (monorepo layout), falling back to `../interagency-marketplace` (legacy sibling checkout)
4. Runs `scripts/post-bump.sh` if present (runs after version file edits but before git commit)
5. Updates all version files (jq for JSON, sed for toml/md)
6. Updates marketplace.json via `jq '(.plugins[] | select(.name == $name)).version = $ver'`
7. Git add + commit + `pull --rebase` + push (both plugin and marketplace repos)
8. Creates cache symlinks in `~/.claude/plugins/cache/` so running Claude Code sessions' plugin Stop hooks (which reference the old version path) continue to resolve after the version directory is renamed

### Post-bump hooks

Modules with extra work needed between version edits and git commit use `scripts/post-bump.sh`:

| Module | Post-bump action |
|--------|-----------------|
| `os/clavain/` | Runs `gen-catalog.py` to refresh skill/agent/command counts |
| `interverse/tldr-swinton/` | Reinstalls CLI via `uv tool install`, checks interbench sync |

### Adding a new plugin

1. Create `scripts/bump-version.sh` (copy any existing 5-line wrapper)
2. Ensure `.claude-plugin/plugin.json` has `name` and `version` fields
3. Add an entry to `core/marketplace/.claude-plugin/marketplace.json`
4. If the plugin needs pre-commit work, add `scripts/post-bump.sh`

## Operational Guides

Consolidated reference guides — read the relevant guide before working in that area.

| Guide | When to Read | Path |
|-------|-------------|------|
| Repo Operations | Before editing root-tracked files, pushing, or adding links to subprojects | `docs/guides/repo-ops.md` |
| Plugin Troubleshooting | Before debugging plugin errors, creating hooks, publishing | `docs/guides/plugin-troubleshooting.md` |
| Shell & Tooling Patterns | Before writing bash hooks, jq pipelines, or bd commands | `docs/guides/shell-and-tooling-patterns.md` |
| Multi-Agent Coordination | Before multi-agent workflows, subagent dispatch, or token analysis | `docs/guides/multi-agent-coordination.md` |
| Data Integrity Patterns | Before WAL, sync, or validation code in TypeScript | `docs/guides/data-integrity-patterns.md` |
| Beads 0.51 Upgrade | Before unpinning/upgrading beads in Interverse | `docs/guides/beads-0.51-upgrade-plan.md` |

## Critical Patterns

Patterns that bite every session. Each learned from a production failure.

**1. hooks.json format** — Event types are **object keys** (`"SessionStart": [...]`), NOT array elements with `"type"` field. Wrong format silently ignored.

**2. Compiled MCP servers need launcher scripts** — `plugin.json` must point to `bin/launch-mcp.sh` (tracked), not the binary (gitignored). No `postInstall` hook exists.

**3. `.orphaned_at` markers block plugin loading** — After version bumps or cache manipulation: `find ~/.claude/plugins/cache -maxdepth 4 -name ".orphaned_at" -not -path "*/temp_git_*" -delete`

**4. Valid hook events (14 total)** — `SessionStart`, `UserPromptSubmit`, `PreToolUse`, `PermissionRequest`, `PostToolUse`, `PostToolUseFailure`, `Notification`, `SubagentStart`, `SubagentStop`, `Stop`, `TeammateIdle`, `TaskCompleted`, `PreCompact`, `SessionEnd`. Invalid events silently ignored.

**5. jq null-slice** — `null[:10]` is a runtime error (exit 5), NOT null. Fix: `(.field // [])[:10]`. Shell functions returning JSON must return `{}`, never `""`.

**6. Billing tokens ≠ effective context** — Cache hits are free for billing but consume context. Decision gates about context limits MUST use `input + cache_read + cache_creation`, never `input + output`.

## Compatibility

Symlinks at `/root/projects/<name>` point into this monorepo for backward compatibility with scripts, configs, and Claude Code session history that reference old paths. These can be removed once all references are updated.

## Landing the Plane (Session Completion)

**When ending a work session**, you MUST complete ALL steps below. Work is NOT complete until `git push` succeeds.

**MANDATORY WORKFLOW:**

1. **File beads for remaining work** - `bd create` for anything that needs follow-up
2. **Run quality gates** (if code changed) - Tests, linters, builds
3. **Update issue status** - Close finished work, update in-progress items
4. **PUSH TO REMOTE** - This is MANDATORY:
   ```bash
   git pull --rebase
   bd sync              # compatibility sync step (0.50.x syncs, 0.51+ no-op)
   git push
   git status  # MUST show "up to date with origin"
   ```
5. **Clean up** - Clear stashes, prune remote branches
6. **Verify** - All changes committed AND pushed
7. **Hand off** - Provide context for next session

**CRITICAL RULES:**
- Work is NOT complete until `git push` succeeds
- NEVER stop before pushing - that leaves work stranded locally
- NEVER say "ready to push when you are" - YOU must push
- If push fails, resolve and retry until it succeeds
- External contributors: push to your fork and open a PR instead

<!-- bv-agent-instructions-v1: beads commands and workflow covered in "Bead Tracking" section above -->

## Operational Notes & Research

Operational lessons (Oracle CLI, git credentials, tmux, SQLite gotchas, plugin publishing) and research references (search improvements, code compression, key papers) are in [docs/guides/agents-operational-notes.md](docs/guides/agents-operational-notes.md).
