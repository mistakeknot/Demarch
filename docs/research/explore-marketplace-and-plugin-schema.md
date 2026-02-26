# Interagency Marketplace & Claude Code Plugin Schema Analysis

**Date:** 2026-02-24  
**Scope:** Marketplace architecture, plugin.json schema, plugin loading mechanism, and plugin examples

---

## 1. Marketplace Directory Structure

### Location
`/home/mk/projects/Demarch/core/marketplace/` — A standalone Git repository (has `.git/` directory)

### Directory Layout
```
core/marketplace/
├── .claude-plugin/
│   └── marketplace.json          # Central registry (source of truth)
├── .claude/
│   └── settings.local.json
├── plugins/                      # Plugin directories (mostly empty in source)
│   ├── interdoc/
│   ├── interflux/
│   ├── clavain/
│   └── ... (33 plugins total)
├── .clavain/                     # Clavain-specific config
├── docs/
│   ├── roadmap.md
│   ├── marketplace-roadmap.md
│   └── marketplace-vision.md
├── AGENTS.md                     # Full development guide
├── CLAUDE.md                     # Quick reference
├── PHILOSOPHY.md
├── README.md                     # User-facing docs
└── .remote-source                # Metadata file
```

### Key Observation
The `plugins/` directory in the source repo is **mostly empty** — plugins live in their own GitHub repos. The marketplace only hosts the **manifest** (marketplace.json) and documentation, not the actual plugin code.

---

## 2. Marketplace Cache Location

### GitHub Clone
`~/.claude/plugins/cache/interagency-marketplace/`

Contains **versioned subdirectories** for each plugin:
```
interagency-marketplace/
├── clavain/
│   ├── 0.6.62/
│   ├── 0.6.63/
│   ├── 0.6.77/
│   ├── 0.6.78/          # Latest
│   └── 0.6.69 -> 0.6.62 # Symlink (version alias)
├── interfluence/
│   ├── 0.2.7/
│   └── 0.2.8/
├── interlock/
│   ├── 0.2.2/
│   ├── 0.2.3/
│   └── ...
├── intership/
├── interject/
├── interform/
└── ... (33 plugins)
```

**Pattern:** Multiple versions cached locally, symlinks for aliases. Claude Code clones each version independently when first installed.

---

## 3. Central Marketplace Manifest: marketplace.json

### Location & Role
**File:** `/home/mk/projects/Demarch/core/marketplace/.claude-plugin/marketplace.json`

**Purpose:** Central registry listing all 33 plugins in the interagency-marketplace ecosystem.

### Schema Structure
```json
{
  "name": "interagency-marketplace",
  "owner": {
    "name": "MK",
    "email": "mistakeknot@vibeguider.org"
  },
  "metadata": {
    "description": "Claude Code plugins for interoperability...",
    "version": "1.0.0"
  },
  "plugins": [
    {
      "name": "plugin-name",
      "source": {
        "source": "url",
        "url": "https://github.com/mistakeknot/plugin-name.git"
      },
      "description": "What this plugin does",
      "version": "X.Y.Z",
      "keywords": ["tag1", "tag2", "tag3"],
      "strict": true
    },
    // ... 32 more plugins
  ]
}
```

### Critical Schema Rules
1. **source MUST be an object** with `{ "source": "url", "url": "..." }` — not a shorthand string
2. **All fields required:** name, source (as object), description, version, keywords, strict
3. **Version must match:** marketplace.json version MUST equal the plugin's .claude-plugin/plugin.json version (version drift = silent load failure)
4. **strict: true** — enables validation on the plugin schema itself
5. **name** — must match plugin.json name exactly

### Registry Statistics (33 plugins as of 2026-02-24)

**By category:**
- **Multi-agent review & research:** interflux (17 agents), intersynth, interpeer, intertest
- **Documentation & knowledge:** interdoc, interwatch, intermem, interlens
- **Coordination & observability:** interlock, intermux, intermap
- **Workflow & phase tracking:** interphase, internext, interpath
- **Developer tooling:** interdev, intercraft, interform
- **Integration & communication:** interslack, interkasten, interserve
- **Code analysis & tokens:** tldr-swinton, interstat, intercheck
- **Ambient discovery:** interject, intersearch
- **Publishing & style:** interpub, interfluence, intership
- **Core orchestration:** clavain (hub plugin with 37 commands)

---

## 4. Individual Plugin Manifests: plugin.json

### Location per Plugin
`.claude-plugin/plugin.json` in each plugin's repository (e.g., `/home/mk/.claude/plugins/cache/interagency-marketplace/interject/0.1.7/.claude-plugin/plugin.json`)

### Schema Examples from Real Plugins

#### Example 1: Interject (MCP server + skills)
```json
{
  "name": "interject",
  "version": "0.1.7",
  "description": "Ambient discovery and research engine...",
  "author": {
    "name": "MK",
    "email": "mistakeknot@vibeguider.org"
  },
  "repository": "https://github.com/mistakeknot/interject",
  "homepage": "https://github.com/mistakeknot/interject#readme",
  "license": "MIT",
  "keywords": ["research", "discovery", "mcp-server"],
  "skills": ["./skills"],
  "mcpServers": {
    "interject": {
      "type": "stdio",
      "command": "${CLAUDE_PLUGIN_ROOT}/bin/launch-mcp.sh",
      "args": [],
      "env": {
        "EXA_API_KEY": "${EXA_API_KEY}"
      }
    }
  }
}
```

**Key features:**
- `skills` — array of relative paths (auto-discovered in directory)
- `mcpServers` — object with server name as key, config as value
- `type: "stdio"` — subprocess-based MCP server
- `${CLAUDE_PLUGIN_ROOT}` — expands to plugin directory at runtime
- Environment variables passed via `env` object

#### Example 2: Interform (Skills only, minimal)
```json
{
  "name": "interform",
  "version": "0.1.0",
  "description": "Design patterns and visual quality...",
  "author": { "name": "MK", "email": "mistakeknot@vibeguider.org" },
  "repository": "https://github.com/mistakeknot/interform",
  "license": "MIT",
  "keywords": ["design", "ui", "ux"],
  "skills": ["./skills/distinctive-design"]
}
```

#### Example 3: Intership (Commands + hooks, no MCP)
```json
{
  "name": "intership",
  "version": "0.1.0",
  "description": "Culture ship names as Claude Code spinner verbs...",
  "author": { "name": "mistakeknot" },
  "license": "MIT",
  "keywords": ["spinner", "culture", "banks"],
  "commands": ["./commands/setup.md"],
  "hooks": "./hooks/hooks.json"
}
```

#### Example 4: Clavain (Complex: multiple skills, MCP server, commands)
```json
{
  "name": "clavain",
  "version": "0.6.78",
  "description": "Self-improving agent rig — 4 agents, 55+ commands, 16 skills, 1 MCP server...",
  "author": { "name": "mistakeknot" },
  "license": "MIT",
  "keywords": ["multi-agent", "self-improving", "cross-ai-review", "oracle"],
  "mcpServers": {
    "context7": {
      "type": "http",
      "url": "https://mcp.context7.com/mcp"
    }
  }
}
```

### Universal plugin.json Fields

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `name` | string | Yes | Matches marketplace.json entry |
| `version` | string | Yes | Must match marketplace.json version |
| `description` | string | Yes | Human-readable purpose |
| `author` | object | Yes | `{name, email}` — MUST be object, not string |
| `repository` | string | No | GitHub/GitLab repo URL |
| `homepage` | string | No | Docs/readme URL |
| `license` | string | No | SPDX identifier (MIT, Apache-2.0, etc.) |
| `keywords` | string[] | No | Search tags |
| `skills` | string[] | No | Paths to skill directories/files |
| `commands` | string[] | No | Paths to command .md files |
| `agents` | string[] | No | Paths to agent definitions |
| `hooks` | string | No | Path to hooks.json file |
| `mcpServers` | object | No | MCP server configurations |

### mcpServers Configuration

Two types:

**Type 1: stdio (subprocess)**
```json
"mcpServers": {
  "server-name": {
    "type": "stdio",
    "command": "${CLAUDE_PLUGIN_ROOT}/bin/launch-mcp.sh",
    "args": ["arg1", "arg2"],
    "env": { "VAR": "value" }
  }
}
```

**Type 2: http (remote)**
```json
"mcpServers": {
  "server-name": {
    "type": "http",
    "url": "https://mcp.service.com/mcp"
  }
}
```

---

## 5. Hooks System (hooks.json)

### Location
`/home/mk/projects/Demarch/os/clavain/hooks/hooks.json` — Clavain's hook definitions

### Schema Structure
```json
{
  "hooks": {
    "SessionStart": [
      {
        "matcher": "startup|resume|clear|compact",
        "hooks": [
          {
            "type": "command",
            "command": "${CLAUDE_PLUGIN_ROOT}/hooks/session-start.sh",
            "async": true
          },
          {
            "type": "command",
            "command": "${CLAUDE_PLUGIN_ROOT}/hooks/interspect-session.sh",
            "async": true
          }
        ]
      }
    ],
    "PostToolUse": [
      {
        "matcher": "Edit|Write|MultiEdit|NotebookEdit",
        "hooks": [
          {
            "type": "command",
            "command": "${CLAUDE_PLUGIN_ROOT}/hooks/interserve-audit.sh",
            "timeout": 5
          }
        ]
      },
      {
        "matcher": "Bash",
        "hooks": [
          {
            "type": "command",
            "command": "${CLAUDE_PLUGIN_ROOT}/hooks/auto-publish.sh",
            "timeout": 15
          }
        ]
      }
    ],
    "Stop": [ /* ... */ ],
    "SessionEnd": [ /* ... */ ]
  }
}
```

### Hook Events & Behavior

| Event | Matcher | Purpose | Can block? | Timeout |
|-------|---------|---------|-----------|---------|
| `SessionStart` | `startup\|resume\|clear\|compact` | Inject context at session start | No | N/A |
| `PostToolUse` | Tool name regex | React after tool use | Feedback only | 5-15s |
| `Stop` | N/A | Before session stops | Yes (`block`) | 5s |
| `SessionEnd` | `clear\|logout\|...` | After session ends | No | Async |

### Critical Hook Patterns in Clavain

1. **SessionStart**: Runs `session-start.sh` + `interspect-session.sh` (both async)
2. **PostToolUse on Edit/Write**: Runs `interserve-audit.sh` (5s timeout)
3. **PostToolUse on Bash**: Runs `auto-publish.sh` + `bead-agent-bind.sh` (15s + 5s)
4. **Stop event**: Runs `auto-stop-actions.sh` (can block session stop)
5. **SessionEnd**: Runs `dotfiles-sync.sh` (async — happens after session ends)

---

## 6. Plugin File Structure (Best Practices)

### Standard Layout
```
my-plugin/
├── .claude-plugin/
│   └── plugin.json          # Required manifest
├── skills/
│   └── skill-name/
│       ├── SKILL.md         # YAML frontmatter (name, description) + markdown workflow
│       └── references/      # Optional: docs, examples
├── commands/
│   └── command-name.md      # YAML frontmatter + slash command spec
├── agents/
│   └── agent-name.md        # YAML frontmatter (name, purpose) + system prompt
├── hooks/
│   ├── hooks.json           # Hook registrations
│   └── *.sh                 # Hook scripts (executable)
├── scripts/
│   └── *.sh                 # Utility scripts
├── CLAUDE.md                # Plugin-specific instructions
├── AGENTS.md                # Plugin development guide
├── README.md                # GitHub/marketplace docs
└── package.json             # Optional (for Node.js dependencies)
```

### Discovery Rules
- **Skills:** Auto-discovered from `skills/` directories (one skill per directory)
- **Commands:** Auto-discovered from `commands/*.md` files
- **Agents:** Auto-discovered from `agents/*.md` files
- **Hooks:** Explicitly listed in `hooks.json` file (not auto-discovered)

### SKILL.md Format
```markdown
---
name: skill-name
description: When Claude should invoke this skill (e.g., "when the user wants to review code")
---

# Skill Title

## Overview
What this skill does.

## Workflow
[Markdown steps, examples, command syntax]
```

---

## 7. Plugin Loading Mechanism

### Installation Flow

1. **User runs:** `claude plugin install <plugin-name>@<marketplace>`
2. **Claude Code:**
   - Looks up marketplace manifest (from `~/.claude/plugins/marketplaces/`)
   - Finds plugin entry in marketplace.json
   - Clones the plugin's GitHub repo to `~/.claude/plugins/cache/<marketplace>/<plugin>/<version>/`
   - Updates `~/.claude/plugins/installed_plugins.json` (master registry)
3. **Session Start:**
   - Loads `plugin.json` from cache
   - Registers skills, commands, agents, hooks
   - Spawns MCP servers (type: "stdio" or connects to http)
   - Injects SessionStart hooks into LLM context

### Cache Structure
```
~/.claude/plugins/
├── cache/
│   ├── interagency-marketplace/
│   │   ├── clavain/0.6.78/
│   │   │   ├── .claude-plugin/plugin.json
│   │   │   ├── skills/
│   │   │   ├── commands/
│   │   │   ├── hooks/
│   │   │   └── ...
│   │   ├── interflux/0.2.27/
│   │   └── ...
│   └── ...
├── installed_plugins.json      # Master registry
├── known_marketplaces.json     # Marketplace sources
└── marketplaces/
    ├── interagency-marketplace/
    │   └── marketplace.json    # Local copy (from /plugin marketplace update)
    └── ...
```

### Version Handling
- Multiple versions of a plugin can be cached simultaneously
- `installed_plugins.json` tracks which version is **active**
- Symlinks in cache (e.g., `0.6.73 -> 0.6.62`) are **aliases** — `0.6.73` and `0.6.62` are the same code
- Version mismatch = silent failure: if marketplace.json says `0.2.7` but cache has `0.2.6`, the plugin won't load

---

## 8. Plugin Schema Validation & Best Practices

### Validation Rules (from Claude Code)

1. **plugin.json validation:**
   - `name` must match marketplace.json entry name
   - `version` must match marketplace.json version exactly
   - `author` must be an object `{name, email}` — NOT a string
   - `license` should be SPDX identifier
   - All paths (`skills`, `commands`, `hooks`) must be relative and exist

2. **marketplace.json validation:**
   - `source` must be object: `{"source": "url", "url": "..."}`
   - `version` must match plugin's plugin.json version
   - `strict: true` enables additional validation

3. **Hook validation:**
   - hooks.json must be valid JSON
   - `command` must be executable
   - `timeout` in seconds (default 60, configurable 1-300)

### Common Mistakes (Anti-patterns)

| Problem | Cause | Fix |
|---------|-------|-----|
| Plugin silently doesn't load | Version mismatch between marketplace.json and plugin.json | Sync versions using `/interpub:release` or `bump-version.sh` |
| Author field rejected | `author: "string"` instead of `author: {name, email}` | Use object with name + email |
| source field fails to parse | Using shorthand `"mistakeknot/plugin"` instead of object | Use `{"source": "url", "url": "https://github.com/..."}` |
| Hooks don't fire | Hooks registered in plugin.json but hooks.json is missing | Create `hooks/hooks.json` with proper event definitions |
| MCP server fails to start | Missing launcher script or bad env vars | Use `${CLAUDE_PLUGIN_ROOT}` to reference files; verify env vars exist |
| Old plugin version loads after update | Cache not cleared | Run `rm -rf ~/.claude/plugins/cache/<marketplace>/<plugin>` then reinstall |

---

## 9. Marketplace Publishing Workflow

### For Plugin Authors

**Step 1: Create plugin in source repo**
```
mistakeknot/my-plugin.git
├── .claude-plugin/plugin.json
├── skills/
├── commands/
├── hooks/
└── README.md
```

**Step 2: Publish source**
```bash
git add -A && git commit -m "v0.1.0: initial release"
git push
```

**Step 3: Register in marketplace**

Edit `/home/mk/projects/Demarch/core/marketplace/.claude-plugin/marketplace.json`:
```json
{
  "name": "my-plugin",
  "source": {"source": "url", "url": "https://github.com/mistakeknot/my-plugin.git"},
  "description": "What it does",
  "version": "0.1.0",
  "keywords": ["tag1", "tag2"],
  "strict": true
}
```

**Step 4: Publish marketplace**
```bash
git add -A && git commit -m "feat: add my-plugin"
git push
```

**Step 5: User installs**
```bash
claude plugin marketplace add mistakeknot/interagency-marketplace
claude plugin install my-plugin
```

### For Updates

Use `/interpub:release 0.2.0` (recommended) or:
```bash
# In plugin source repo:
scripts/bump-version.sh 0.2.0
# → bumps plugin.json + updates marketplace.json, commits, pushes
```

**Then restart Claude Code.**

---

## 10. Key Design Decisions (Demarch)

1. **External repos only** — Plugins live in separate GitHub repos under `mistakeknot/`, not in Demarch monorepo
2. **Version synchronization critical** — marketplace.json version MUST match plugin.json version
3. **All fields required** — No optional fields in marketplace.json
4. **Strict object format** — source field is always `{source: "url", url: "..."}`, never shorthand
5. **No fields in cache** — Never edit ~/.claude/plugins/cache/; always edit source repo
6. **Session restart required** — Hooks, skills, commands, MCP configs all load at SessionStart
7. **Hooks have matchers** — Different hooks fire for different tool types (Edit vs Write vs Bash)

---

## 11. Summary: The Three Layers

### Layer 1: Marketplace Manifest
- **File:** `/home/mk/projects/Demarch/core/marketplace/.claude-plugin/marketplace.json`
- **Role:** Central registry of 33 plugins
- **Managed by:** Marketplace maintainer
- **Users see:** Plugin descriptions, versions, source URLs

### Layer 2: Plugin Manifests
- **Files:** Each plugin's `.claude-plugin/plugin.json`
- **Role:** Declares skills, commands, agents, hooks, MCP servers
- **Managed by:** Plugin author
- **Claude Code reads:** At session start to register capabilities

### Layer 3: Plugin Code
- **Files:** Skills/, commands/, hooks/, agents/ directories
- **Role:** Actual implementation
- **Loaded by:** Claude Code at session start
- **Validation:** SKILL.md YAML frontmatter, command.md format, hooks.json schema

---

## 12. Plugin Examples from Marketplace

### clavain (0.6.78) — Monolithic Hub
- **Type:** Multi-agent framework
- **Contains:** 4 agents, 55+ commands, 16 skills, 10 hooks, 1 MCP (context7)
- **Role:** Orchestrates entire Demarch workflow
- **Companions:** 31 other plugins (refactored from clavain as complexity grew)

### interflux (0.2.27) — Multi-Agent Review
- **Type:** Distributed review engine
- **Contains:** 17 agents (12 review + 5 research), 4 commands, 2 skills, 2 MCP servers
- **Role:** Scored triage, domain detection, parallel agent routing
- **Companion to:** clavain

### interdoc (5.1.1) — Documentation Generator
- **Type:** Pure skills (no MCP)
- **Role:** Generates AGENTS.md recursively with structural auto-fix
- **Cross-AI:** Works with Claude Code and Codex CLI

### interject (0.1.7) — Ambient Discovery
- **Type:** MCP server + skills
- **Server type:** stdio (subprocess)
- **Role:** Scans arXiv, HN, GitHub, Anthropic docs, Exa
- **Integration:** Embedding-based recommendation engine

### interpub (0.1.3) — Release Automation
- **Type:** Command + skill
- **Role:** `scripts/bump-version.sh` wrapper
- **Prevents:** Manual version sync errors

---

## Conclusion

The interagency-marketplace is a **3-layer system**:

1. **Marketplace level** — `marketplace.json` is the single source of truth for the 33-plugin ecosystem
2. **Plugin level** — Each plugin has a `plugin.json` manifest declaring its capabilities
3. **Implementation level** — Skills, commands, agents, hooks, and MCP servers provide the actual functionality

Version synchronization is **critical**: marketplace.json version must match plugin.json version exactly, otherwise the plugin loads silently fails (no error, just doesn't work). The `/interpub:release` command automates this to prevent drift.

The cache at `~/.claude/plugins/cache/interagency-marketplace/` mirrors the marketplace structure with version directories and symlinks for aliases. Session restart is always required after plugin changes because hooks, skills, and MCP configs are loaded at SessionStart.

