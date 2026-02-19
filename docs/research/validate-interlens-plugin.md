# Plugin Validation Report: interlens

**Date:** 2026-02-18
**Plugin Path:** `/home/mk/.claude/plugins/cache/interagency-marketplace/interlens/2.2.3/`
**Validator:** Claude Opus 4.6

---

## Plugin: interlens v2.2.3
Location: `/home/mk/.claude/plugins/cache/interagency-marketplace/interlens/2.2.3/`

---

## Summary

The interlens plugin is an MCP-only plugin (no commands, agents, skills, or hooks) that exposes a cognitive augmentation toolkit of 288 FLUX analytical lenses via an MCP server. The plugin manifest is valid and the MCP bundle exists and appears functional. However, there are **3 version drift issues** and several minor structural concerns. Overall, the plugin passes validation with warnings.

| Category | Status |
|----------|--------|
| Manifest (plugin.json) | PASS |
| MCP Server | PASS (with warnings) |
| File Organization | PASS (with warnings) |
| Security | PASS |
| Commands | N/A (none defined) |
| Agents | N/A (none defined) |
| Skills | N/A (none defined) |
| Hooks | N/A (none defined) |

---

## Critical Issues (0)

None.

---

## Major Issues (1)

### 1. Version Drift Across Three Locations

Three different version numbers exist in the plugin:

| Location | Version |
|----------|---------|
| `plugin.json` → `version` | **2.2.3** |
| `package.json` (root) → `version` | **2.2.3** |
| `packages/mcp/package.json` → `version` | **2.2.1** |
| `packages/mcp/index.js` → Server constructor | **1.0.0** |
| `packages/mcp/dist/bundle.mjs` → Server constructor | **1.0.0** |

**Impact:** The MCP server identifies itself to clients as version `1.0.0` regardless of the actual plugin version, which can cause confusion during debugging and version verification. The `packages/mcp/package.json` version `2.2.1` is behind the plugin manifest version `2.2.3`, suggesting the npm package version was not bumped when the plugin was last published.

**Fix:**
- Update `packages/mcp/index.js` line 26 to use a dynamic version or at least `2.2.3`
- Update `packages/mcp/package.json` version to `2.2.3`
- Rebuild the bundle (`dist/bundle.mjs`) after updating

---

## Warnings (5)

### 1. `.claude-plugin/` Contains Only plugin.json

```
.claude-plugin/
  plugin.json       (664 bytes)
```

The plugin directory has no `commands/`, `agents/`, `skills/`, or `hooks/` subdirectories. This is valid for an MCP-only plugin, but worth noting -- all plugin functionality comes exclusively from the MCP server.

**Recommendation:** Consider adding at minimum a slash command (e.g., `/interlens:search`) or a skill document that explains how to use the lenses effectively, so that the plugin is discoverable without MCP tool listing.

### 2. MCP Server Uses Relative Path Without `${CLAUDE_PLUGIN_ROOT}`

In `plugin.json`:
```json
"mcpServers": {
  "interlens": {
    "type": "stdio",
    "command": "node",
    "args": ["packages/mcp/dist/bundle.mjs"]
  }
}
```

The path `packages/mcp/dist/bundle.mjs` is relative. Claude Code resolves this relative to the plugin root, which works in the marketplace cache. However, best practice is to use `${CLAUDE_PLUGIN_ROOT}/packages/mcp/dist/bundle.mjs` for explicit portability.

**Recommendation:** Use `${CLAUDE_PLUGIN_ROOT}/packages/mcp/dist/bundle.mjs` in the args.

### 3. CHANGELOG.md Does Not Document v2.2.3

The changelog's most recent entry is `[2.1.0] - 2025-11-24`. There are no entries for versions 2.2.0 through 2.2.3.

**Recommendation:** Add changelog entries for all published versions.

### 4. Large Files Included in Plugin Cache

The plugin cache is 3.1 MB total. Notable large files:
- `pnpm-lock.yaml` — 432 KB (not needed at runtime)
- `packages/mcp/dist/bundle.mjs` — 504 KB (the actual MCP server)
- `apps/` directory — entire Flask API, React web frontend, benchmark suite, Python scripts

For a plugin that only uses the MCP bundle, all of `apps/`, `pnpm-lock.yaml`, `pnpm-workspace.yaml`, benchmark files, and Python scripts are unnecessary weight.

**Recommendation:** Add a `.pluginignore` or equivalent mechanism to exclude `apps/`, `pnpm-lock.yaml`, benchmark files, and other non-runtime assets from the marketplace distribution.

### 5. HTTP URLs in Web App Frontend (localhost references)

Found `http://` URLs in `apps/web/`:
- `apps/web/package.json` line 19: `http://localhost:5003/api/v1`
- `apps/web/package.json` line 47: `http://localhost:5003`
- `apps/web/src/hooks/useBackgroundLoader.js`: `http://localhost:5003/api/v1`
- `apps/web/src/components/useLenses.js`: `http://localhost:5003/api/v1`
- `apps/web/src/services/cacheService.js`: `http://localhost:5001/api/v1`

These are all development-mode defaults (falling back to localhost when no env var is set) and are not used by the MCP server. No security issue, but they would be eliminated if `apps/web/` were excluded from the plugin distribution.

---

## Component Summary

| Component | Count Found | Valid |
|-----------|-------------|-------|
| Commands | 0 | N/A |
| Agents | 0 | N/A |
| Skills | 0 | N/A |
| Hooks | Not present | N/A |
| MCP Servers | 1 configured | Valid |

### MCP Server Details

**Server name:** `interlens`
**Type:** stdio
**Command:** `node packages/mcp/dist/bundle.mjs`
**Bundle exists:** Yes (504 KB, esbuild output)
**Bundle executable:** Yes (`#!/usr/bin/env node` shebang)

**MCP Tools (18 total):**

| Tool | Description |
|------|-------------|
| `search_lenses` | Search for FLUX lenses by query string |
| `get_lens` | Get detailed info about a specific lens |
| `get_lenses_by_episode` | Get lenses from a specific FLUX episode |
| `get_related_lenses` | Find related lenses |
| `analyze_with_lens` | Analyze text through a specific lens |
| `combine_lenses` | Combine multiple lenses for novel insights |
| `get_lens_frames` | Get thematic frames grouping related lenses |
| `find_lens_journey` | Find conceptual path between two lenses |
| `find_bridge_lenses` | Find lenses bridging disparate concepts |
| `find_contrasting_lenses` | Find paradoxical/contrasting lenses |
| `get_central_lenses` | Get most central lenses in the network |
| `get_lens_neighborhood` | Explore conceptual neighborhood around a lens |
| `random_lens_provocation` | Get random lens for creative provocation |
| `detect_thinking_gaps` | Analyze conceptual coverage blind spots |
| `suggest_thinking_mode` | Recommend best thinking mode for a problem |
| `synthesize_solution` | Synthesize insights from multiple lens applications |
| `refine_lens_application` | Iteratively improve a lens application |
| `get_dialectic_triads` | Get thesis/antithesis/synthesis triads |
| `get_lens_progressions` | Get learning progressions between lenses |

**MCP Resources (4):**
- `lens://all` — All FLUX lenses
- `lens://frames` — Thematic frames
- `lens://episodes` — Lenses by episode
- `lens://graph` — Relationship graph

**External API dependency:** The MCP server calls `https://interlens-api-production.up.railway.app/api/v1` (configurable via `INTERLENS_API_URL` env var). The API URL uses HTTPS.

**Local modules bundled into the MCP server:**
- `lib/thinking-modes.js` — Six thinking modes (systems thinking, creative, etc.)
- `lib/belief-statements.js` — SaLT-inspired belief statement generation
- `lib/quality-evaluation.js` — Quality scoring
- `lib/synthesis.js` — Solution synthesis
- `lib/refinement.js` — Iterative application refinement

---

## Security Assessment

### Credentials
- No hardcoded API keys, tokens, or secrets found in any source file
- All API keys are read from environment variables (`OPENAI_API_KEY`, `SUPABASE_KEY`, `SUPABASE_URL`)
- `.env.example` files contain only placeholder values (`your_supabase_project_url`, etc.)
- `.gitignore` correctly excludes `.env` files

### Network
- MCP server API base URL uses HTTPS: `https://interlens-api-production.up.railway.app/api/v1`
- HTTP URLs found only in development-mode React app defaults (localhost fallbacks)
- GitHub Actions workflow uses `${{ secrets.* }}` for credentials

### MCP Server
- Uses `@modelcontextprotocol/sdk` v0.5.0 (older but functional)
- Server uses stdio transport (no network listener)
- No file system writes except to local `.cache/` directory for API response caching

---

## Positive Findings

1. **Valid JSON in plugin.json** — Parses cleanly with `jq`, all required fields present, name is kebab-case compatible
2. **Well-structured MCP server** — 18 tools with clear descriptions, proper input schemas with required fields, comprehensive error handling
3. **HTTPS for external API** — Production API uses HTTPS, no cleartext API communication
4. **No secrets in source** — All credentials properly read from environment variables
5. **Bundled distribution** — esbuild bundle means no `node_modules` needed at runtime
6. **Rich tool ecosystem** — Creative thinking tools (journey, bridge, contrasts, triads, progressions) plus analytical tools (search, analyze, gap detection, synthesis)
7. **Proper `.gitignore`** — Covers `node_modules/`, `.env`, `__pycache__/`, `.DS_Store`
8. **LICENSE file present** — MIT license
9. **README.md present** — Describes repo layout, quick start, and deployment

---

## Recommendations

### Priority 1: Fix Version Drift
Synchronize all version strings to `2.2.3`:
- `packages/mcp/package.json` version field
- `packages/mcp/index.js` Server constructor version
- Rebuild `dist/bundle.mjs`

### Priority 2: Add CHANGELOG Entries
Document what changed in versions 2.2.0, 2.2.1, 2.2.2, and 2.2.3 in `CHANGELOG.md`.

### Priority 3: Slim Down Plugin Distribution
The marketplace cache contains the full monorepo (API backend, React frontend, Python scripts, benchmark suite, pnpm-lock.yaml). Only `packages/mcp/dist/bundle.mjs` and `plugin.json` are needed at runtime. Consider:
- Adding a `.pluginignore` or build step that strips non-essential files
- At minimum, exclude: `apps/`, `pnpm-lock.yaml`, `packages/mcp/benchmark/`, `packages/mcp/docs/plans/`

### Priority 4: Use `${CLAUDE_PLUGIN_ROOT}` in MCP Args
Change from relative path to explicit variable for portability:
```json
"args": ["${CLAUDE_PLUGIN_ROOT}/packages/mcp/dist/bundle.mjs"]
```

### Priority 5: Consider Adding a Slash Command or Skill
An MCP-only plugin is less discoverable than one with slash commands. A simple `/interlens:search <query>` command or a skill document explaining the FLUX lens methodology would help users discover the plugin's capabilities without needing to know about MCP tools.

### Priority 6: Update MCP SDK
The `@modelcontextprotocol/sdk` dependency is at `^0.5.0`. Consider updating to the latest stable version for protocol improvements and bug fixes.

---

## Overall Assessment

**PASS** (with warnings)

The interlens plugin is a well-implemented MCP-only plugin that provides a rich set of cognitive augmentation tools. The plugin manifest is valid, the MCP server bundle exists and is properly structured with 18 tools and 4 resources, and there are no security issues. The main concern is version drift across three locations (plugin manifest, npm package, and MCP server constructor), which should be fixed to avoid confusion. The plugin would also benefit from slimming down its distribution size by excluding non-runtime files (the full monorepo weighs 3.1 MB when only ~500 KB is needed).
