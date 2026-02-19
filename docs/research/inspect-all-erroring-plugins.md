# Plugin Error Inspection Report

**Date:** 2026-02-18
**Base path:** `/home/mk/.claude/plugins/cache/interagency-marketplace/`

## Executive Summary

All 10 erroring plugins share a combination of two root causes:

1. **Path resolution mismatch (8 of 10 plugins):** `plugin.json` references files like `./hooks/hooks.json` and `./skills/*.md` with paths relative to `.claude-plugin/`, but the actual files exist at the **plugin root** level (one directory up). The `.claude-plugin/` directory contains only `plugin.json` — no skills, hooks, agents, or commands were copied into it.

2. **Orphaned markers (10 of 10 plugins):** Every single plugin has an `.orphaned_at` file, meaning the marketplace considers them stale/disconnected from their source repos. This may cause Claude Code to skip loading them entirely.

3. **Missing plugin.json references (2 of 10 plugins):** interfluence and interflux have skills, commands, agents, and hooks that exist on disk but are **not declared** in `plugin.json`, so Claude Code never sees them.

---

## Per-Plugin Analysis

### 1. interstat (v0.1.0)

**Status:** ORPHANED

| Issue | Detail |
|-------|--------|
| Missing hooks | `./hooks/hooks.json` referenced in plugin.json, file exists at root but NOT in `.claude-plugin/` |
| Missing skills | `./skills/report.md`, `./skills/status.md`, `./skills/analyze.md` — all exist at root, not in `.claude-plugin/` |
| No MCP servers | N/A |

**plugin.json:**
```json
{
  "name": "interstat",
  "version": "0.1.0",
  "description": "Token efficiency benchmarking for agent workflows",
  "author": "MK",
  "hooks": "./hooks/hooks.json",
  "skills": ["./skills/report.md", "./skills/status.md", "./skills/analyze.md"]
}
```

**`.claude-plugin/` contents:** Only `plugin.json` (no hooks/, skills/ directories).

**Root-level files that should be referenced:**
- `hooks/hooks.json`, `hooks/post-task.sh`, `hooks/session-end.sh`
- `skills/report.md`, `skills/status.md`, `skills/analyze.md`

---

### 2. intersynth (v0.1.0)

**Status:** ORPHANED

| Issue | Detail |
|-------|--------|
| Missing hooks | `./hooks/hooks.json` referenced, exists at root only |
| Missing agents | `./agents/synthesize-review.md`, `./agents/synthesize-research.md` — exist at root only |
| No MCP servers | N/A |

**plugin.json:**
```json
{
  "name": "intersynth",
  "version": "0.1.0",
  "description": "Multi-agent synthesis engine...",
  "agents": ["./agents/synthesize-review.md", "./agents/synthesize-research.md"],
  "hooks": "./hooks/hooks.json"
}
```

**`.claude-plugin/` contents:** Only `plugin.json`.

---

### 3. interserve (v0.1.0)

**Status:** NOT orphaned

| Issue | Detail |
|-------|--------|
| Missing hooks | `./hooks/hooks.json` referenced, exists at root only |
| MCP server | `${CLAUDE_PLUGIN_ROOT}/bin/launch-mcp.sh` — file EXISTS and is executable |

**plugin.json:**
```json
{
  "name": "interserve",
  "version": "0.1.0",
  "description": "Interserve — Codex spark classifier and context compression via MCP",
  "hooks": "./hooks/hooks.json",
  "mcpServers": {
    "interserve": {
      "type": "stdio",
      "command": "${CLAUDE_PLUGIN_ROOT}/bin/launch-mcp.sh",
      "args": [],
      "env": {
        "INTERSERVE_DISPATCH_PATH": "/root/projects/Interverse/hub/clavain/scripts/dispatch.sh"
      }
    }
  }
}
```

**Note:** MCP command path is valid. Only issue is missing hooks file at `.claude-plugin/` level.

---

### 4. intermap (v0.1.0)

**Status:** ORPHANED

| Issue | Detail |
|-------|--------|
| Missing hooks | `./hooks/hooks.json` referenced, exists at root only |
| Missing skills | `./skills/SKILL.md` — exists at root only |
| MCP server | `${CLAUDE_PLUGIN_ROOT}/bin/launch-mcp.sh` — file EXISTS and is executable |

**plugin.json:**
```json
{
  "name": "intermap",
  "version": "0.1.0",
  "hooks": "./hooks/hooks.json",
  "skills": ["./skills/SKILL.md"],
  "mcpServers": {
    "intermap": {
      "type": "stdio",
      "command": "${CLAUDE_PLUGIN_ROOT}/bin/launch-mcp.sh",
      "args": [],
      "env": {
        "INTERMUTE_URL": "http://127.0.0.1:7338",
        "PYTHONPATH": "${CLAUDE_PLUGIN_ROOT}/python"
      }
    }
  }
}
```

---

### 5. intermux (v0.1.0)

**Status:** NOT orphaned

| Issue | Detail |
|-------|--------|
| Missing hooks | `./hooks/hooks.json` referenced, exists at root only |
| Missing skills | `./skills/status/SKILL.md` — exists at root only |
| MCP server | `${CLAUDE_PLUGIN_ROOT}/bin/launch-mcp.sh` — file EXISTS and is executable |

**plugin.json:**
```json
{
  "name": "intermux",
  "version": "0.1.0",
  "hooks": "./hooks/hooks.json",
  "skills": ["./skills/status/SKILL.md"],
  "mcpServers": {
    "intermux": {
      "type": "stdio",
      "command": "${CLAUDE_PLUGIN_ROOT}/bin/launch-mcp.sh",
      "args": [],
      "env": {
        "INTERMUTE_URL": "http://127.0.0.1:7338",
        "TMUX_SOCKET": "/tmp/tmux-0/default"
      }
    }
  }
}
```

---

### 6. interject (v0.1.2)

**Status:** ORPHANED

| Issue | Detail |
|-------|--------|
| Missing hooks | `./hooks/hooks.json` referenced, exists at root only |
| Missing skills | 5 skills (`scan.md`, `discover.md`, `inbox.md`, `profile.md`, `status.md`) — all exist at root only |
| MCP server | `uv run --directory ${CLAUDE_PLUGIN_ROOT} interject-mcp` — `uv` on PATH, directory exists |
| **API key leak** | `EXA_API_KEY` hardcoded in plugin.json: `eba9629f-75e9-467c-8912-a86b3ea8d678` |

**plugin.json:**
```json
{
  "name": "interject",
  "version": "0.1.2",
  "skills": ["./skills/scan.md", "./skills/discover.md", "./skills/inbox.md", "./skills/profile.md", "./skills/status.md"],
  "hooks": "./hooks/hooks.json",
  "mcpServers": {
    "interject": {
      "type": "stdio",
      "command": "uv",
      "args": ["run", "--directory", "${CLAUDE_PLUGIN_ROOT}", "interject-mcp"],
      "env": {
        "EXA_API_KEY": "eba9629f-75e9-467c-8912-a86b3ea8d678"
      }
    }
  }
}
```

**Warning:** Hardcoded API key should be replaced with `${EXA_API_KEY}` env var reference.

---

### 7. interkasten (v0.3.12)

**Status:** ORPHANED

| Issue | Detail |
|-------|--------|
| Missing hooks | `./hooks/hooks.json` referenced, exists at root only |
| Missing skills | 3 skills (`layout/SKILL.md`, `onboard/SKILL.md`, `doctor/SKILL.md`) — all exist at root only |
| Missing commands | 2 commands (`onboard.md`, `doctor.md`) — both exist at root only |
| MCP server | `bash ${CLAUDE_PLUGIN_ROOT}/scripts/start-mcp.sh` — script exists |

**plugin.json:**
```json
{
  "name": "interkasten",
  "version": "0.3.12",
  "mcpServers": {
    "interkasten": {
      "type": "stdio",
      "command": "bash",
      "args": ["${CLAUDE_PLUGIN_ROOT}/scripts/start-mcp.sh"],
      "env": {}
    }
  },
  "skills": ["./skills/layout/SKILL.md", "./skills/onboard/SKILL.md", "./skills/doctor/SKILL.md"],
  "commands": ["./commands/onboard.md", "./commands/doctor.md"],
  "hooks": "./hooks/hooks.json"
}
```

---

### 8. interfluence (v0.1.2)

**Status:** ORPHANED

| Issue | Detail |
|-------|--------|
| No hooks reference | plugin.json does not declare hooks — but `hooks/learn-from-edits.sh` exists on disk |
| No skills reference | plugin.json does not declare skills — but 5 skills exist: `analyze.md`, `apply.md`, `compare.md`, `ingest.md`, `refine.md` |
| No commands reference | plugin.json does not declare commands — but `commands/interfluence.md` exists |
| No agents reference | plugin.json does not declare agents — but `agents/voice-analyzer.md` exists |
| MCP server | `node ${CLAUDE_PLUGIN_ROOT}/server/dist/bundle.js` — bundle.js exists (1.1MB) |

**plugin.json (incomplete):**
```json
{
  "name": "interfluence",
  "version": "0.1.2",
  "description": "Analyze your writing style and adapt Claude's output...",
  "mcpServers": {
    "interfluence": {
      "type": "stdio",
      "command": "node",
      "args": ["${CLAUDE_PLUGIN_ROOT}/server/dist/bundle.js"],
      "env": {}
    }
  }
}
```

**Root cause:** plugin.json is minimal — only defines MCP server. All skills, commands, agents, and hooks exist on disk but are never declared, so Claude Code doesn't load them.

---

### 9. interflux (v0.2.0)

**Status:** ORPHANED

| Issue | Detail |
|-------|--------|
| No skills reference | plugin.json does not declare skills — but `skills/flux-drive/SKILL.md` and `skills/flux-research/SKILL.md` exist |
| No commands reference | plugin.json does not declare commands — but `commands/flux-drive.md`, `commands/flux-gen.md`, `commands/flux-research.md` exist |
| No agents reference | plugin.json does not declare agents — but 12 agent files exist under `agents/review/` and `agents/research/` |
| No hooks reference | OK — no hooks exist on disk either |
| MCP: qmd | `qmd mcp` — `qmd` found at `/home/mk/.bun/bin/qmd` |
| MCP: exa | `npx -y exa-mcp-server` with `${EXA_API_KEY}` env var (unresolved at runtime if not set) |

**plugin.json (incomplete):**
```json
{
  "name": "interflux",
  "version": "0.2.0",
  "mcpServers": {
    "qmd": { "type": "stdio", "command": "qmd", "args": ["mcp"] },
    "exa": {
      "type": "stdio",
      "command": "npx",
      "args": ["-y", "exa-mcp-server"],
      "env": { "EXA_API_KEY": "${EXA_API_KEY}" }
    }
  }
}
```

**Root cause:** plugin.json only declares MCP servers. 12 agents, 3 commands, and 2 skills are completely undeclared.

---

### 10. interlens (v2.2.2)

**Status:** ORPHANED

| Issue | Detail |
|-------|--------|
| **Relative MCP path** | MCP command is `node packages/mcp/index.js` — relative path with NO `${CLAUDE_PLUGIN_ROOT}` prefix. Will fail unless CWD happens to be the plugin root. |
| No skills/hooks/agents | None declared, none exist on disk for the plugin |
| Dependencies | `node_modules/` exists at root with `@modelcontextprotocol/sdk`, `node-fetch`, `express`, `cors` installed |

**plugin.json:**
```json
{
  "name": "interlens",
  "version": "2.2.2",
  "mcpServers": {
    "interlens": {
      "type": "stdio",
      "command": "node",
      "args": ["packages/mcp/index.js"]
    }
  }
}
```

**Root cause:** The MCP args use a relative path `packages/mcp/index.js` instead of `${CLAUDE_PLUGIN_ROOT}/packages/mcp/index.js`. This will fail to find the file at runtime unless the working directory is set to the plugin root.

---

## Issue Summary Matrix

| Plugin | Version | Orphaned | Hooks Missing | Skills Missing | Agents Missing | Commands Missing | MCP Issue | Undeclared Assets |
|--------|---------|----------|---------------|----------------|----------------|-----------------|-----------|-------------------|
| interstat | 0.1.0 | YES | YES (path) | YES (path) | — | — | N/A | — |
| intersynth | 0.1.0 | YES | YES (path) | — | YES (path) | — | N/A | — |
| interserve | 0.1.0 | no | YES (path) | — | — | — | OK | — |
| intermap | 0.1.0 | YES | YES (path) | YES (path) | — | — | OK | — |
| intermux | 0.1.0 | no | YES (path) | YES (path) | — | — | OK | — |
| interject | 0.1.2 | YES | YES (path) | YES (path) | — | — | OK (key leak) | — |
| interkasten | 0.3.12 | YES | YES (path) | YES (path) | — | YES (path) | OK | — |
| interfluence | 0.1.2 | YES | — | — | — | — | OK | 5 skills, 1 cmd, 1 agent, 1 hook |
| interflux | 0.2.0 | YES | — | — | — | — | OK (env var) | 2 skills, 3 cmds, 12 agents |
| interlens | 2.2.2 | YES | — | — | — | — | RELATIVE PATH | — |

## Root Causes

### 1. Path Resolution Bug (affects 8 plugins)

When `plugin.json` declares `"hooks": "./hooks/hooks.json"`, Claude Code resolves this relative to the `.claude-plugin/` directory (where `plugin.json` lives). But the actual files are at the plugin root level:

```
plugin-root/
├── .claude-plugin/
│   └── plugin.json          ← references ./hooks/hooks.json
├── hooks/
│   └── hooks.json            ← actual file lives HERE
├── skills/
│   └── *.md                  ← actual files live HERE
└── ...
```

**Fix options:**
- A) Change paths in plugin.json to use `../hooks/hooks.json` (ugly, fragile)
- B) Copy/symlink skills/hooks/agents/commands into `.claude-plugin/` during publish
- C) Fix the marketplace publisher to resolve paths relative to plugin root, not `.claude-plugin/`

### 2. Incomplete plugin.json (affects 2 plugins)

interfluence and interflux have rich file structures with skills, commands, agents, and hooks — but their `plugin.json` files only declare MCP servers. The assets exist on disk but are invisible to Claude Code.

**Fix:** Update plugin.json for both plugins to declare all existing assets.

### 3. Relative MCP Path (affects 1 plugin)

interlens uses `"args": ["packages/mcp/index.js"]` without `${CLAUDE_PLUGIN_ROOT}` prefix.

**Fix:** Change to `"args": ["${CLAUDE_PLUGIN_ROOT}/packages/mcp/index.js"]`.

### 4. Universal Orphan Status (affects 10 of 10 plugins)

Every plugin has an `.orphaned_at` marker file. This likely means the marketplace's link between the cached plugin and its source repository is broken. Depending on how Claude Code handles orphaned plugins, this could cause them to be skipped during loading.

### 5. Hardcoded API Key (affects 1 plugin)

interject has `EXA_API_KEY` hardcoded as a literal value instead of using `${EXA_API_KEY}` env var reference.

## Recommended Fixes (Priority Order)

1. **Fix path resolution in publisher** — The marketplace publish step should either (a) resolve relative paths from plugin root, not `.claude-plugin/`, or (b) copy referenced files into `.claude-plugin/` during publish.

2. **Update interfluence and interflux plugin.json** — Add all existing skills, commands, agents, and hooks to the manifest.

3. **Fix interlens MCP path** — Prefix with `${CLAUDE_PLUGIN_ROOT}/`.

4. **Investigate orphan markers** — Determine why all plugins are orphaned and whether this blocks loading. Consider a bulk re-link or re-publish.

5. **Remove hardcoded API key from interject** — Replace with `${EXA_API_KEY}` env var reference.

6. **Re-publish all 10 plugins** after fixes are applied to source repos.
