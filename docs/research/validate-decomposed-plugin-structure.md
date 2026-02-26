# Structural Validation: 12 Decomposed Interverse Plugins

**Date:** 2026-02-25
**Scope:** Read-only structural validation of the plugin decomposition
**Result:** 9/9 checks PASS

---

## Check 1: interflux -> intersense delegation

**PASS**

### interflux stub delegates to intersense

`interverse/interflux/scripts/detect-domains.py` is a 24-line stub that:
- Searches for the canonical `intersense/scripts/detect-domains.py` via monorepo path and marketplace cache
- Delegates via `os.execv(sys.executable, [sys.executable, str(candidate)] + sys.argv[1:])` -- correct exec-replace pattern
- Falls back to stderr error and `sys.exit(2)` if intersense not found

### intersense canonical copy exists

`interverse/intersense/scripts/detect-domains.py` exists (712 lines) as the canonical implementation. Header confirms: "Detect project domains using signals from flux-drive domain index."

### SKILL.md references `.claude/intersense.yaml`

`interverse/interflux/skills/flux-drive/SKILL.md` correctly references `.claude/intersense.yaml` in 3 places:
- Line 103: Cache check at `{PROJECT_ROOT}/.claude/intersense.yaml`
- Line 115: Script auto-caches to `.claude/intersense.yaml`
- Line 129: Read `content_hash` from `.claude/intersense.yaml`

No references to the old `.claude/flux-drive.yaml` found in the SKILL.md or SKILL-compact.md.

---

## Check 2: interflux -> interknow delegation

**PASS**

### interflux plugin.json has NO qmd MCP server

`interverse/interflux/.claude-plugin/plugin.json` has `mcpServers` with only one entry: `"exa"`. No `qmd` entry present. Confirmed via grep -- zero matches for "qmd" in that file.

### interknow plugin.json HAS qmd MCP server

`interverse/interknow/.claude-plugin/plugin.json` includes:
```json
"mcpServers": {
    "qmd": {
        "type": "stdio",
        "command": "${CLAUDE_PLUGIN_ROOT}/scripts/launch-qmd.sh",
        "args": ["mcp"]
    }
}
```

### launch.md references interknow tool namespace

`interverse/interflux/skills/flux-drive/phases/launch.md` line 27 references `mcp__plugin_interknow_qmd__vsearch` -- the correct interknow namespace. No references to the old `mcp__plugin_interflux_qmd__` namespace found.

---

## Check 3: intersearch MCP server

**PASS**

### plugin.json has mcpServers entry

`interverse/intersearch/.claude-plugin/plugin.json` declares:
```json
"mcpServers": {
    "intersearch": {
        "command": "uv",
        "args": ["--directory", "${CLAUDE_PLUGIN_ROOT}", "run", "intersearch-mcp"]
    }
}
```

### server.py exists and is functional

`interverse/intersearch/src/intersearch/server.py` exists. It:
- Imports `EmbeddingStore` from `.store`
- Creates `Server("intersearch")` instance
- Caches embedding stores per project root
- Exposes `embedding_index` and `embedding_query` tools (replacing the former intercache embedding tools)

---

## Check 4: intercache cleaned

**PASS**

### server.py has NO embedding references

Grep for `EmbeddingStore`, `embedding_index`, `embedding_query`, and `from.*embeddings` in `interverse/intercache/src/intercache/server.py` returned zero matches. The server imports only `Manifest`, `SessionTracker`, and `BlobStore` -- pure caching concerns.

### pyproject.toml has NO numpy dependency

Grep for `numpy` in `interverse/intercache/pyproject.toml` returned zero matches. The only runtime dependency is `mcp>=1.0.0`. Test-only deps are `pytest` and `pytest-asyncio`.

---

## Check 5: interdev lean

**PASS**

`interverse/interdev/.claude-plugin/plugin.json` declares exactly 2 skills:
1. `./skills/mcp-cli`
2. `./skills/working-with-claude-code`

No agents, commands, hooks, or MCP servers. The 3 skills that were extracted:
- `create-agent-skills` and `writing-skills` -> interskill
- `developing-claude-code-plugins` -> interplug

---

## Check 6: intercheck lean

**PASS**

### hooks declared

`interverse/intercheck/.claude-plugin/plugin.json` includes `"hooks": "./hooks/hooks.json"` and 1 skill (`./skills/status`).

### hooks.json has NO context-monitor reference

`interverse/intercheck/hooks/hooks.json` contains only 2 PostToolUse hooks matching `Edit|Write|NotebookEdit`:
1. `syntax-check.sh` (timeout 5s)
2. `auto-format.sh` (timeout 10s)

No reference to `context-monitor` anywhere in the hooks.json. Context monitoring has been fully extracted to interpulse.

---

## Check 7: New plugin structure

**PASS** -- All 6 new plugins have valid plugin.json files.

| Plugin | Valid JSON | Name | Version |
|--------|-----------|------|---------|
| intersense | YES | `intersense` | `0.1.0` |
| interknow | YES | `interknow` | `0.1.0` |
| intertree | YES | `intertree` | `0.1.0` |
| interskill | YES | `interskill` | `0.1.0` |
| interplug | YES | `interplug` | `0.1.0` |
| interpulse | YES | `interpulse` | `0.1.0` |

All files parse as valid JSON, names match directory names, and versions are consistent at 0.1.0.

### Additional structure details:

- **intersense**: Scripts-only plugin (no skills, hooks, or MCP servers)
- **interknow**: 2 skills (compound, recall), 1 MCP server (qmd), 1 hooks file
- **intertree**: 1 skill (layout), no hooks or MCP servers
- **interskill**: 2 skills (create, audit), no hooks or MCP servers
- **interplug**: 3 skills (create, validate, troubleshoot), no hooks or MCP servers
- **interpulse**: 1 skill (status), 1 hooks file

---

## Check 8: Marketplace

**PASS**

`core/marketplace/.claude-plugin/marketplace.json` contains exactly **39 plugin entries**. All 6 new plugins are present:

| New Plugin | In Marketplace |
|-----------|---------------|
| intersense | PRESENT |
| interknow | PRESENT |
| intertree | PRESENT |
| interskill | PRESENT |
| interplug | PRESENT |
| interpulse | PRESENT |

---

## Check 9: No undeclared hooks

**PASS**

For each plugin that has a `hooks/` directory, the plugin.json correctly declares a `"hooks"` key:

| Plugin | hooks/ dir exists | `"hooks"` in plugin.json |
|--------|------------------|--------------------------|
| interpulse | YES (`hooks.json`, `context-monitor.sh`) | YES (`"hooks": "./hooks/hooks.json"`) |
| interknow | YES (`hooks.json`, `session-start.sh`) | YES (`"hooks": "./hooks/hooks.json"`) |
| intercheck | YES (`hooks.json`) | YES (`"hooks": "./hooks/hooks.json"`) |

No undeclared hooks found.

---

## Summary

| # | Check | Result |
|---|-------|--------|
| 1 | interflux -> intersense delegation | PASS |
| 2 | interflux -> interknow delegation | PASS |
| 3 | intersearch MCP server | PASS |
| 4 | intercache cleaned | PASS |
| 5 | interdev lean (2 skills) | PASS |
| 6 | intercheck lean (no context-monitor) | PASS |
| 7 | 6 new plugin.json files valid | PASS |
| 8 | Marketplace has 39 entries + all 6 new | PASS |
| 9 | No undeclared hooks | PASS |

**Overall: 9/9 PASS. The decomposition is structurally complete and correct.**
