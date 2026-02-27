# Demarch — Agent Development Guide

## Overview

Demarch is the physical monorepo for the open-source autonomous software development agency platform. It contains five pillars: **Intercore** (`/core`) the orchestration kernel, **Clavain** (`/os`) the agent OS and reference agency, **Interverse** (`/interverse`) the companion plugin ecosystem, **Autarch** (`/apps`) the TUI surfaces, and **Interspect** (cross-cutting profiler, currently housed in Clavain). Plus `sdk/` for shared libraries (interbase). Each module keeps its own `.git` as a nested independent repo. The root `Demarch/` also has a `.git` for the monorepo skeleton (scripts, docs, CLAUDE.md). Git operations apply to the nearest `.git`; verify with `git rev-parse --show-toplevel`.

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

Each subproject has its own CLAUDE.md and AGENTS.md — read those before editing. Use `ls apps/ core/ interverse/ os/ sdk/` to discover modules.

| Path | Pillar | Notes |
|------|--------|-------|
| `apps/autarch/` | Autarch | TUI interfaces (Bigend, Gurgeh, Coldwine, Pollard) |
| `apps/intercom/` | Autarch | Multi-runtime AI assistant (Claude, Gemini, Codex) |
| `os/clavain/` | Clavain | Autonomous software agency (L2 OS) |
| `core/intercore/` | Intercore | Orchestration kernel — Go CLI `ic` (L1) |
| `core/intermute/` | Intercore | Multi-agent coordination service (Go) |
| `core/marketplace/` | Intercore | Plugin marketplace registry |
| `interverse/` | Interverse | Companion plugins — each has own docs (`ls interverse/ \| wc -l`) |
| `sdk/interbase/` | — | Shared integration SDK (Bash/Go/Python) |
| `docs/` | — | Platform-level docs only (brainstorms, research, solutions) |

> **Docs convention:** `Demarch/docs/` is for platform-level work only. Each subproject keeps its own docs.
> **Artifact naming:** See [`CONVENTIONS.md`](CONVENTIONS.md) for canonical paths.

## Key Dependency Chains

```
Clavain (L2) → interlock → intermute (L1)    # file coordination
Clavain (L2) → interflux → intersearch        # multi-agent review
interject → intersearch                        # ambient discovery
Clavain (L2) → intertrust                     # agent trust scoring
```

Standalone plugins (no cross-deps): interfluence, interkasten, tldr-swinton, intercache, intercheck, interstat, interpeer, intertest, interlens, intermap, intermux, interserve, tool-time, tuivision.

## Bead Tracking

All work is tracked at the **Demarch root level** using the monorepo `.beads/` database. Module-level `.beads/` databases are read-only archives of historical closed beads.

- Create beads from the Demarch root: `cd /root/projects/Demarch && bd create --title="[module] Description" ...`
- Use `[module]` prefix in bead titles to identify the relevant module (e.g., `[interlock]`, `[interflux]`, `[clavain]`)
- Filter by module: `bd list --status=open | grep -i interlock`
- Cross-module beads use multiple prefixes: `[interlock/intermute]`

### Label Taxonomy

Beads use a two-dimensional label system. Backfill/apply with `scripts/backfill-bead-labels.py`.

**Module labels** (`mod:<name>`) — which pillar/subproject the bead belongs to:
```bash
# Generate current list:
(echo "mod:clavain mod:demarch mod:autarch mod:intercom mod:interspect mod:tldrs"; \
 ls -d interverse/inter* core/inter* sdk/inter* 2>/dev/null | xargs -I{} basename {} | sed 's/^/mod:/') \
 | tr ' ' '\n' | sort | paste -d'  ' - - - - -
```

**Theme labels** (`theme:<name>`) — what kind of work:
```
theme:tech-debt  theme:performance  theme:security  theme:ux
theme:observability  theme:dx  theme:infra  theme:docs
theme:testing  theme:architecture  theme:coordination  theme:research
```

Labels are inferred from `[module]` bracket prefixes in titles and keyword patterns in title+description. The backfill script is idempotent and additive — it never removes existing labels.

### Bead Recovery Scripts

After data loss events, use these scripts to reconstruct missing beads:

| Script | Purpose |
|--------|---------|
| `scripts/replay-missing-beads-from-commit-manifest.py` | Recreate beads from a CSV of git commits where bead IDs appeared in commit messages but were missing from the database |
| `scripts/replay-missing-roadmap-beads.py` | Create placeholder beads for IDs referenced in `docs/roadmap.json` and `*roadmap*.md` files but absent from the database |
| `scripts/map_brainstorms_plans_to_beads.py` | Map `docs/brainstorms/` and `docs/plans/` markdown files to bead IDs via `**Bead:** ...` declarations; creates placeholder beads for unmatched docs |
| `scripts/backfill-bead-labels.py` | Apply module and theme label taxonomy to existing beads using heuristic detection (idempotent) |

Recovered beads are tagged `recovered, placeholder` so they are distinguishable from original data. See `docs/research/verify-recovered-beads-quality.md` for the audit report from the 2026-02-27 recovery.

### Roadmap

The platform roadmap is at [`docs/demarch-roadmap.md`](docs/demarch-roadmap.md) with machine-readable canonical output in [`docs/roadmap.json`](docs/roadmap.json). Regenerate both with `/interpath:roadmap` from the Demarch root. Auto-generate module-level roadmaps from beads with `scripts/generate-module-roadmaps.sh` or `/interpath:propagate`.

`scripts/sync-roadmap-json.sh` generates the canonical JSON rollup from the root roadmap and beads data. `scripts/generate-module-roadmaps.sh` auto-generates per-module `docs/roadmap.md` files from beads state.

## Go Module Path Convention

All first-party Go modules declare canonical module paths matching `github.com/mistakeknot/<module-name>`, where `<module-name>` matches the directory basename (e.g., `core/intercore` declares `github.com/mistakeknot/intercore`).

- **Replace directives** use relative filesystem paths from the module's own directory (e.g., `../../core/intermute`), never symlinks.
- **CI guard**: `scripts/check-go-module-paths.sh` validates all in-scope `go.mod` files. Excludes `research/`, `.external/`, and `testdata/` directories.
- Third-party or vendored modules (under `.external/`, `research/`) are exempt from this convention.

## Prerequisites

Required tools (all pre-installed on this server):

| Tool | Used by | Purpose |
|------|---------|---------|
| `jq` | interbump, hooks | JSON manipulation |
| `uv` | tldr-swinton, interject, intersearch, intercache, interfin | Python package management |
| `go` (1.24+) | intermute, intercore, interlock, interbench | Go builds and tests |
| `node`/`npm` | interkasten | MCP server build |
| `python3` | tldr-swinton, tool-time, interject, intercache | CLI tools, analysis scripts |
| `bd` | all | Beads issue tracker CLI |

**Secrets** (in environment or dotfiles — never commit):
- `INTERKASTEN_NOTION_TOKEN` — Notion API token for interkasten sync
- `EXA_API_KEY` — Exa search API for interject and interflux research agents
- `SLACK_TOKEN` — Slack API for interslack

## Design Doctrine

> For the full design philosophy (core bets, autonomy model, failure stance, etc.), see [`PHILOSOPHY.md`](PHILOSOPHY.md).

### Brainstorming
1. Start from outcomes and failure modes, not implementation details.
2. Generate at least three options: conservative, balanced, and aggressive.
3. Explicitly call out assumptions, unknowns, and dependency risk across modules.
4. Prefer ideas that improve clarity, reversibility, and operational visibility.

### Planning
1. Convert selected direction into small, testable, reversible slices.
2. Define acceptance criteria, verification steps, and rollback path for each slice.
3. Sequence dependencies explicitly and keep integration contracts narrow.
4. Reserve optimization work until correctness and reliability are proven.

### Decision Filters
- Does this reduce ambiguity for future sessions?
- Does this improve reliability without inflating cognitive load?
- Is the change observable, measurable, and easy to verify?
- Can we revert safely if assumptions fail?

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

**MCP server plugins** (intercache, interflux, interfluence, interject, interkasten, interlock, intermap, intermux, interserve, tldr-swinton, tuivision):
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

Three entrypoints to the same engine — use whichever fits your context:

**1. Go CLI (preferred when `ic` is built):**
```bash
cd interverse/interflux
ic publish --patch               # auto-increment patch version
ic publish 0.2.1                 # bump to exact version
ic publish --dry-run             # preview only
ic publish doctor --fix          # detect and auto-repair drift
```

**2. Claude Code slash command:**
```
/interpub:release <version>
```

**3. Shell wrapper (terminal fallback):**
```bash
cd interverse/interflux
scripts/bump-version.sh 0.2.1            # bump + commit + push
scripts/bump-version.sh 0.2.1 --dry-run  # preview only
```

All three call the same underlying engine. `/interpub:*` and other slash commands are **Claude Code slash commands** — run them inside a Claude Code session, not from a terminal.

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
| Secret Scanning Baseline | Before rolling out or auditing secret scanning policy across repos | `docs/guides/secret-scanning-baseline.md` |
| Interband Sideband Protocol | Before working on sideband communication between agents | `docs/guides/interband-sideband-protocol.md` |
| Beads 0.51 Upgrade | For completed migration status and post-migration operations | `docs/guides/beads-0.51-upgrade-plan.md` |

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
