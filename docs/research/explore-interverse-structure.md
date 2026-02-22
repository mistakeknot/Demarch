# Interverse Monorepo Structure Analysis

**Date:** 2026-02-14  
**Scope:** Root-level structure, scripts, plugins/interlock, docs, and all root files

---

## Executive Summary

The Interverse monorepo is a physical (not symlinked) aggregation of 14 Claude Code plugins, 1 service (intermute), 3 infrastructure projects, and 1 hub (Clavain) — all organized under `/root/projects/Interverse/`. The monorepo provides:

- **Unified version bumping** via `scripts/interbump.sh` (handles all 14 plugins + marketplace sync)
- **Hub-centric architecture** where Clavain (hub) coordinates smaller plugins (interdoc, interflux, interkasten, etc.)
- **Each subproject maintains its own `.git` repo** — not a git monorepo
- **Two documentation sources:** root-level `CLAUDE.md` (quick ref) and `AGENTS.md` (comprehensive dev guide)

---

## Root-Level Files

### Static Documentation
- **`CLAUDE.md`** (1,818 bytes)  
  Quick reference for the monorepo structure, naming conventions (all lowercase except Clavain/Interverse), and design decisions. Directs readers to subproject CLAUDE.md files for details.

- **`AGENTS.md`** (4,361 bytes)  
  Comprehensive agent development guide with directory layout, module relationships, naming conventions, development workflow, and mandatory "landing the plane" completion checklist (git push required).

### Hidden Directories
- **`.beads/`** — Beads database for session/conversation tracking
- **`.claude/`** — Claude Code plugin configuration and sessions
- **`.clavain/`** — Clavain (hub) configuration directory

### No README, Makefile, or .gitignore
The monorepo root contains only documentation and configuration — no traditional build files. Each subproject is independent.

---

## Root-Level `scripts/` Directory

**Location:** `/root/projects/Interverse/scripts/`  
**Contents:** 1 executable

### `interbump.sh` (7,640 bytes, executable)

**Purpose:** Unified version bumping for all Interverse plugins and marketplace.

**Key Features:**
- **Auto-discovers version files** in each plugin:
  - `.claude-plugin/plugin.json` (required)
  - `pyproject.toml` (Python plugins)
  - `package.json` (Node plugins)
  - `server/package.json` (MCP servers)
  - `agent-rig.json` (agent specs)
  - `docs/PRD.md` (markdown version string)

- **Marketplace synchronization:**
  - Locates `infra/marketplace/.claude-plugin/marketplace.json` by walking up directory tree
  - Falls back to legacy `../interagency-marketplace/` if monorepo layout fails
  - Updates marketplace version in single jq operation

- **Atomic file updates:**
  - JSON files: `jq` with temp file + rename (atomic)
  - TOML/Markdown: `sed` with platform-aware `-i` flag (macOS vs Linux)
  - Includes `--dry-run` mode for preview

- **Git workflow:**
  - Commits version bumps to plugin repo
  - `git pull --rebase` before push
  - Commits and pushes marketplace update separately
  - Both must succeed

- **Cache symlink bridging:**
  - Post-publish, creates symlinks in `~/.claude/plugins/cache/` for running sessions
  - Old version → real build dir → new version (tri-link chain)
  - Allows Stop hooks in running sessions to survive version transitions

- **Called from:** Each plugin's `scripts/bump-version.sh` thin wrapper (delegated pattern)
- **Must be run from:** Plugin root directory (where `.claude-plugin/` exists)
- **Usage:** `interbump.sh <version> [--dry-run]`
- **Validates:** Semver format (X.Y.Z with optional pre-release suffix)

---

## Plugins Directory

**Location:** `/root/projects/Interverse/plugins/`  
**Count:** 14 plugins (all lowercase names)

### Plugin Inventory

1. **`interdoc`** — AGENTS.md recursive generator with cross-AI critique
2. **`interfluence`** — Voice profile analysis and style adaptation
3. **`interflux`** — Multi-agent document review + research engine (7 review agents)
4. **`interkasten`** — Bidirectional Notion sync with adaptive documentation
5. **`interline`** — Dynamic statusline for Claude Code
6. **`interlock`** — MCP server for intermute file reservation and agent coordination ⭐
7. **`interpath`** — Product artifact generator (roadmaps, PRDs, changelogs)
8. **`interphase`** — Phase tracking, gate validation, work discovery
9. **`interpub`** — Safe plugin version bumping and publishing
10. **`interwatch`** — Doc freshness monitoring and drift detection
11. **`tldr-swinton`** — Token-efficient code context via MCP server
12. **`tool-time`** — Tool usage analytics for Claude Code and Codex CLI
13. **`tuivision`** — TUI automation and visual testing via MCP server

### Deep Dive: `plugins/interlock/`

**Quick Reference (`CLAUDE.md`):**
- **Overview:** MCP server wrapping intermute's HTTP API for file reservation and agent coordination
- **Scope:** 9 tools, 4 commands, 2 skills, 3 hooks
- **Role:** Companion plugin for Clavain (hub)
- **Build:** `bash scripts/build.sh` (Go binary)
- **Test:** `go test ./...`
- **Validate:** `python3 -c "import json; json.load(open('.claude-plugin/plugin.json'))"`

**Design Decisions:**
- Go binary for MCP server (mark3labs/mcp-go), bash for hooks
- Unix socket preferred, TCP fallback for intermute connection
- Advisory-only PreToolUse:Edit hook, mandatory git pre-commit enforcement
- Join-flag gating: all hooks check `~/.config/clavain/intermute-joined`

**Plugin Configuration (`plugin.json`):**
```json
{
  "name": "interlock",
  "version": "0.1.0",
  "description": "MCP server for intermute file reservation and agent coordination...",
  "author": { "name": "mistakeknot" },
  "license": "MIT",
  "keywords": ["mcp", "file-reservation", "agent-coordination", "intermute", ...],
  "mcpServers": {
    "interlock": {
      "type": "stdio",
      "command": "${CLAUDE_PLUGIN_ROOT}/bin/interlock-mcp",
      "env": {
        "INTERMUTE_SOCKET": "/var/run/intermute.sock",
        "INTERMUTE_URL": "http://127.0.0.1:7338"
      }
    }
  }
}
```

**MCP Server Details:**
- **Type:** stdio (standard input/output, not HTTP)
- **Binary location:** `${CLAUDE_PLUGIN_ROOT}/bin/interlock-mcp` (built by `scripts/build.sh`)
- **Connection:** Defaults to Unix socket (`/var/run/intermute.sock`), falls back to TCP (`http://127.0.0.1:7338`)
- **Tools:** 9 (reserve, release, conflict check, messaging, agent listing)
- **Status:** v0.1.0

---

## Hub Directory

**Location:** `/root/projects/Interverse/hub/`  
**Contents:** 1 subdirectory

### `os/clavain/`

- **Role:** Core engineering discipline plugin (proper noun: Clavain)
- **Scope:** Skills, agents, commands, hooks
- **Architectural role:** Hub coordinating other plugins (interdoc, interflux, interkasten, interline, interpath, interwatch)
- **Service dependency:** Uses intermute for multi-agent coordination (via interlock plugin)

---

## Services Directory

**Location:** `/root/projects/Interverse/services/`  
**Contents:** 1 service

### `services/intermute/`

- **Role:** Multi-agent coordination service (orchestration backbone)
- **Implementation:** Go + SQLite
- **Port:** 7338 (TCP fallback)
- **Socket:** `/var/run/intermute.sock` (preferred)
- **Used by:** Clavain (hub), accessed via interlock (MCP plugin)

---

## Infrastructure Directory

**Location:** `/root/projects/Interverse/infra/`  
**Contents:** 3 subdirectories

1. **`infra/agent-rig`** — Agent specification framework
2. **`infra/interbench`** — Benchmarking infrastructure
3. **`infra/marketplace`** — Plugin marketplace registry  
   - Contains `.claude-plugin/marketplace.json` (registry of all published plugins)
   - Updated atomically by `interbump.sh` during each plugin release
   - Maintains version sync across 14 plugins

---

## Docs Directory

**Location:** `/root/projects/Interverse/docs/`  
**Structure:**

```
docs/
├── brainstorms/          ← Research notes
│   └── 2026-02-14-clavain-vs-modules-boundary-analysis.md
├── research/             ← Investigation findings
│   ├── check-all-gh-repos-for-beads.md
│   ├── check-inter-module-repos-for-beads.md
│   ├── find-hardcoded-logic-in-interkasten-tools.md
│   └── generate-resilientstore-wrapper.md
└── docs → /root/projects/dotfiles-sync/common/projects/docs [symlink]
```

**Shared Documentation:**
- **Brainstorms:** 1 file
  - `2026-02-14-clavain-vs-modules-boundary-analysis.md` — Analysis of hub vs module responsibilities

- **Research:** 4 files
  - `check-all-gh-repos-for-beads.md` — Audit of Beads database across GitHub repos
  - `check-inter-module-repos-for-beads.md` — Beads verification for inter-module repos
  - `find-hardcoded-logic-in-interkasten-tools.md` — Investigation of hardcoded logic in Notion sync
  - `generate-resilientstore-wrapper.md` — Research on resilient storage patterns

- **Symlink:** `docs/` links to external shared documentation store (`/root/projects/dotfiles-sync/common/projects/docs`)

---

## Module Dependency Graph

```
clavain (hub)
├── interphase  (phase tracking, gates)
├── interline   (statusline rendering)
├── interflux   (multi-agent review + research)
├── interpath   (product artifact generation)
└── interwatch  (doc freshness monitoring)

intermute (service) ← used by clavain for multi-agent coordination
  └── accessed via interlock (MCP plugin)

interpub           ← publishes all plugins
interdoc           ← generates AGENTS.md for all projects
interfluence       ← standalone voice profiling
interkasten        ← standalone Notion sync
tldr-swinton       ← standalone code context MCP
tool-time          ← standalone usage analytics
tuivision          ← standalone TUI testing MCP

infra/marketplace  ← registry for all plugins
  └── updated by interbump.sh during releases
```

---

## Key Design Facts

### Naming Convention
- **All lowercase:** `interflux`, `intermute`, `interkasten`
- **Exceptions:** `Clavain` (hub, proper noun), `Interverse` (monorepo name)
- **GitHub repos:** Match directory names: `github.com/mistakeknot/interflux`

### Independent Git Repos
- Each subproject has its own `.git` directory
- NOT a git monorepo (no parent `.git` at Interverse root)
- `interbump.sh` handles cross-repo version sync and marketplace updates

### Atomic Version Bumping
- Single `interbump.sh` call from any plugin directory
- Updates up to 6 version locations per plugin (plugin.json, package.json, pyproject.toml, etc.)
- Syncs marketplace in separate git push
- Cache symlink bridging keeps Stop hooks alive across versions

### Physical Monorepo Structure
- Monorepo lives at `/root/projects/Interverse/` (not symlinked)
- Legacy compat symlinks exist at `/root/projects/<name>` pointing into this monorepo
- `AGENTS.md` explicitly states: "Physical monorepo, not symlinks — projects live here, old locations are symlinks back"

### Development Workflow
**Mandatory "landing the plane" steps at session end:**
1. File issues for remaining work
2. Run quality gates (tests, linters, builds)
3. Update issue status
4. **PUSH TO REMOTE** (mandatory — work is NOT complete until `git push` succeeds)
5. Clean up (stashes, prune branches)
6. Verify all changes committed AND pushed
7. Hand off for next session

---

## Summary Statistics

| Component | Count | Details |
|-----------|-------|---------|
| Total Plugins | 14 | interdoc, interfluence, interflux, interkasten, interline, interlock, interpath, interphase, interpub, interwatch, tldr-swinton, tool-time, tuivision |
| Hub Projects | 1 | clavain |
| Services | 1 | intermute |
| Infra Projects | 3 | agent-rig, interbench, marketplace |
| Root Scripts | 1 | interbump.sh (version bumping orchestrator) |
| Root Documentation | 2 | CLAUDE.md, AGENTS.md |
| Research Docs | 4 | Shared investigation/brainstorm notes |
| Root Config Dirs | 3 | .beads, .claude, .clavain |

---

## Files and Directories at Monorepo Root

```
/root/projects/Interverse/
├── AGENTS.md                 (comprehensive dev guide, 4,361 bytes)
├── CLAUDE.md                 (quick reference, 1,818 bytes)
├── .beads/                   (Beads database)
├── .claude/                  (Claude Code plugin config)
├── .clavain/                 (Clavain hub config)
├── hub/                      (1 subdirectory: clavain)
├── plugins/                  (14 subdirectories: all lowercase names)
├── services/                 (1 subdirectory: intermute)
├── infra/                    (3 subdirectories: agent-rig, interbench, marketplace)
├── docs/                     (brainstorms/, research/, symlink to external docs/)
└── scripts/                  (1 executable: interbump.sh)
```

---

## Next Steps / Follow-Up Investigations

1. **interbump.sh cache symlink behavior** — Test how multi-version symlinks survive plugin restarts
2. **Interlock MCP server internals** — Full MCP tool/command/hook inventory (mentioned as 9 tools, 4 commands, 2 skills, 3 hooks)
3. **Plugin dependency graph** — Check for circular dependencies or undocumented cross-module calls
4. **Marketplace registry completeness** — Verify all 14 plugins are registered in `infra/marketplace/marketplace.json`
5. **Subproject CLAUDE.md/AGENTS.md** — Each subproject has own docs that take precedence over root-level
