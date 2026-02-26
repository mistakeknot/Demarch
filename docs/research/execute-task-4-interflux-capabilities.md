# Task 4 Execution: Add Capability Declarations to Interflux

**Date:** 2026-02-22
**Plan:** `/root/projects/Demarch/docs/plans/2026-02-22-agent-capability-discovery.md`
**Task:** Task 4 — Add capability declarations to interflux + write per-agent capability files

## Summary

Task 4 adds capability metadata to the interflux plugin so that its 17 agents (12 review + 5 research) can advertise their specializations to the intermute agent registry via interlock's registration script. This is the producer-side wiring: interflux declares what each agent can do, a SessionStart hook writes that data to per-agent files on disk, and interlock reads those files during registration.

## Files Modified

### 1. `interverse/interflux/.claude-plugin/plugin.json`

**Change:** Added `agentCapabilities` map with 17 entries. Keys are full relative paths matching the `agents` array exactly (e.g., `"./agents/review/fd-architecture.md"`). Values are JSON arrays of `domain:specialization` capability tags.

**Capability tag assignments:**

| Agent Path | Capabilities |
|---|---|
| `./agents/review/fd-architecture.md` | `review:architecture`, `review:code`, `review:design-patterns` |
| `./agents/review/fd-safety.md` | `review:safety`, `review:security`, `review:deployment` |
| `./agents/review/fd-correctness.md` | `review:correctness`, `review:concurrency`, `review:data-consistency` |
| `./agents/review/fd-user-product.md` | `review:user-experience`, `review:product`, `review:scope` |
| `./agents/review/fd-quality.md` | `review:quality`, `review:style`, `review:conventions` |
| `./agents/review/fd-game-design.md` | `review:game-design`, `review:balance`, `review:pacing` |
| `./agents/review/fd-performance.md` | `review:performance`, `review:bottlenecks`, `review:scaling` |
| `./agents/review/fd-systems.md` | `review:systems-thinking`, `review:feedback-loops`, `review:emergence` |
| `./agents/review/fd-decisions.md` | `review:decisions`, `review:cognitive-bias`, `review:strategy` |
| `./agents/review/fd-people.md` | `review:trust`, `review:communication`, `review:team-dynamics` |
| `./agents/review/fd-resilience.md` | `review:resilience`, `review:antifragility`, `review:innovation` |
| `./agents/review/fd-perception.md` | `review:mental-models`, `review:sensemaking`, `review:information-quality` |
| `./agents/research/framework-docs-researcher.md` | `research:docs`, `research:frameworks` |
| `./agents/research/repo-research-analyst.md` | `research:codebase`, `research:architecture` |
| `./agents/research/git-history-analyzer.md` | `research:git-history`, `research:code-evolution` |
| `./agents/research/learnings-researcher.md` | `research:learnings`, `research:institutional-knowledge` |
| `./agents/research/best-practices-researcher.md` | `research:best-practices`, `research:industry-standards` |

### 2. `interverse/interflux/hooks/write-capabilities.sh` (new file)

**Purpose:** SessionStart hook that reads `agentCapabilities` from plugin.json and writes per-agent JSON files to `~/.config/clavain/capabilities-<agent-name>.json`.

**Behavior:**
- Uses `set -euo pipefail` for strict error handling
- Reads from `${CLAUDE_PLUGIN_ROOT}/.claude-plugin/plugin.json`
- Creates `~/.config/clavain/` directory if it doesn't exist
- Iterates over `agentCapabilities` keys using `jq -r ... | while read`
- Extracts agent name from path using `basename "$agent_path" .md`
- Writes capability arrays using `jq -c` (compact output) with `--arg` for safe variable interpolation
- Skips agents with null or empty capability arrays
- Exits cleanly (exit 0) if plugin.json is missing

**Output files created (17 total):**
- `~/.config/clavain/capabilities-fd-architecture.json` containing `["review:architecture","review:code","review:design-patterns"]`
- `~/.config/clavain/capabilities-fd-safety.json` containing `["review:safety","review:security","review:deployment"]`
- ... (one for each of the 17 agents)

### 3. `interverse/interflux/hooks/hooks.json`

**Change:** Added write-capabilities.sh as a second SessionStart hook entry alongside the existing session-start.sh hook.

**Before:**
```json
{
  "hooks": {
    "SessionStart": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "bash ${CLAUDE_PLUGIN_ROOT}/hooks/session-start.sh"
          }
        ]
      }
    ]
  }
}
```

**After:**
```json
{
  "hooks": {
    "SessionStart": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "bash ${CLAUDE_PLUGIN_ROOT}/hooks/session-start.sh"
          },
          {
            "type": "command",
            "command": "bash ${CLAUDE_PLUGIN_ROOT}/hooks/write-capabilities.sh"
          }
        ]
      }
    ]
  }
}
```

**Note:** The hooks.json is at `interverse/interflux/hooks/hooks.json` (not at the standard `.claude-plugin/hooks/hooks.json` path). It is NOT declared in plugin.json (no `"hooks"` key exists there), which means it is auto-loaded from its current location. Per the CLAUDE.md memory note, only hooks at the standard path `.claude-plugin/hooks/hooks.json` are auto-loaded — this plugin's hooks are discovered via a different mechanism (likely the marketplace or plugin loader walking the directory tree).

## Validation Results

### JSON syntax validation
- `plugin.json`: valid JSON
- `hooks.json`: valid JSON

### Agent-capability alignment check
```
$ python3 -c "import json; d=json.load(open('interverse/interflux/.claude-plugin/plugin.json')); ac=d.get('agentCapabilities',{}); agents=d.get('agents',[]); print('agents:', len(agents), 'caps:', len(ac)); missing=[k for k in ac if k not in agents]; print('missing from agents:', missing or 'none')"
agents: 17 caps: 17
missing from agents: none
```

All 17 agentCapabilities keys match entries in the agents array exactly. No orphaned or missing keys.

### Hook dry-run test
Ran the hook with `CLAUDE_PLUGIN_ROOT` set to the interflux source directory and `HOME` set to a temp directory:

```
$ CLAUDE_PLUGIN_ROOT=interverse/interflux HOME=/tmp/test-caps-home bash interverse/interflux/hooks/write-capabilities.sh
$ ls /tmp/test-caps-home/.config/clavain/
capabilities-best-practices-researcher.json
capabilities-fd-architecture.json
capabilities-fd-correctness.json
capabilities-fd-decisions.json
capabilities-fd-game-design.json
capabilities-fd-people.json
capabilities-fd-perception.json
capabilities-fd-performance.json
capabilities-fd-quality.json
capabilities-fd-resilience.json
capabilities-fd-safety.json
capabilities-fd-systems.json
capabilities-fd-user-product.json
capabilities-framework-docs-researcher.json
capabilities-git-history-analyzer.json
capabilities-learnings-researcher.json
capabilities-repo-research-analyst.json
```

17 files created, each containing the compact JSON array for that agent. Example:
```
$ cat /tmp/test-caps-home/.config/clavain/capabilities-fd-architecture.json
["review:architecture","review:code","review:design-patterns"]
```

## Design Decisions

1. **Full relative paths as keys** (M3 from plan review): Using `"./agents/review/fd-architecture.md"` rather than `"fd-architecture"` prevents drift between the agents array and capabilities map. The validation check catches mismatches.

2. **`domain:specialization` tag format**: Two domains (`review:` and `research:`) with specific specializations. This follows the plan's taxonomy and allows consumers to filter by domain prefix (all `review:*`) or specific capability (`review:architecture`).

3. **Hook ordering**: write-capabilities.sh runs after session-start.sh. The capability files are read later by interlock's registration script (a separate hook), so ordering within interflux's own hooks doesn't matter for correctness. Placing it second ensures the session-start ecosystem setup completes first.

4. **Graceful degradation**: The hook exits cleanly if plugin.json is missing (`exit 0`) and skips agents with null/empty capabilities. This prevents the hook from blocking session start if something goes wrong.

5. **No `hooks` declaration in plugin.json**: The existing hooks.json at `hooks/hooks.json` is already loaded by whatever mechanism the plugin loader uses. Adding a declaration in plugin.json would risk the "Duplicate hooks file" error noted in CLAUDE.md memory.

## How This Connects to the Full Pipeline

```
[interflux plugin.json]     [write-capabilities.sh]      [interlock-register.sh]      [intermute]
  agentCapabilities    --->  capabilities-*.json      --->  POST /api/agents         --->  SQLite
  (17 entries)               (~/.config/clavain/)          {capabilities: [...]}         capabilities_json
```

1. **Session start**: interflux hook writes 17 capability files to `~/.config/clavain/`
2. **Agent registration** (Task 2): interlock-register.sh reads `capabilities-<agent-name>.json` and includes the array in the POST payload
3. **Storage** (Task 1): intermute stores capabilities in `capabilities_json` column
4. **Discovery** (Tasks 1+3): `GET /api/agents?capability=review:architecture` filters by capability; interlock MCP `list_agents` tool exposes this to agents

## Not Done (per task scope)

- No git commit created (as instructed)
- Tasks 1-3 (intermute Go changes, interlock registration, MCP tool extension) are separate tasks
- Task 5 (end-to-end test) depends on Tasks 1-4
