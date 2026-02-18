# Research: Claude Code File Loading and Context Management

**Date:** 2026-02-17
**Researcher:** Claude Sonnet 4.5
**Purpose:** Determine precise behavior of Claude Code's documentation auto-loading, HTML handling in markdown, MCP server architecture, and evaluate implementation options for intermem plugin.

---

## 1. Which Files Does Claude Code Auto-Load?

### CLAUDE.md Loading Behavior

**Confirmed facts from web search and documentation:**

1. **Root-level `CLAUDE.md`** — Loaded at session start from project root. This is the primary auto-loaded file.

2. **`.claude/rules/*.md`** — All markdown files in this directory are auto-loaded at session start with the same priority as root `CLAUDE.md`. No imports needed.

3. **Subdirectory `CLAUDE.md` files** — NOT loaded at session start. Only loaded when Claude actively reads files in that subdirectory.

4. **Parent directory `CLAUDE.md` files** — Claude reads all `CLAUDE.md` files ABOVE the current working directory (in parent directories). This is a Claude Code extension beyond the AGENTS.md standard.

5. **Global `~/CLAUDE.md`** (home directory) — Loaded at session start as global context.

**What about `--add-dir`?**

From the web search: "Skills defined in `.claude/skills/` within directories added via `--add-dir` are loaded automatically. However, CLAUDE.md files from `--add-dir` directories are **not** loaded by default. To load them, set `CLAUDE_CODE_ADDITIONAL_DIRECTORIES_CLAUDE_MD=1`."

**Pattern matching:** Claude Code looks for exact filenames (`CLAUDE.md`, not `CLAUDE-*.md` or `AGENTS-*.md`). No glob pattern support confirmed.

### AGENTS.md Loading Behavior

**Key finding:** Claude Code does NOT auto-load `AGENTS.md` by default. This is a different standard used by Cursor, Zed, OpenCode, and other AI coding tools.

From GitHub issue #6235 (Feature Request: Support AGENTS.md):
- AGENTS.md is an open standard for cross-tool AI agent context
- Claude Code only supports CLAUDE.md natively
- Workaround: symlink `AGENTS.md` → `CLAUDE.md` or reference it in CLAUDE.md with: "See AGENTS.md for full documentation"
- Subdirectory AGENTS.md files merge with root (per the AGENTS.md spec), but Claude Code doesn't implement this

**Subdirectory merging difference:**
- `AGENTS.md` standard: autodiscover subdirectory AGENTS.md files and merge them
- `CLAUDE.md` (Claude Code): only load subdirectory files when actively working in that subtree

**Parent directory discovery:**
- `CLAUDE.md`: Claude reads all parent dirs automatically
- `AGENTS.md` standard: does NOT yet support parent dir discovery (open issue in agentsmd/agents.md repo)

### Summary Table

| File | When Loaded | Notes |
|------|-------------|-------|
| `<project-root>/CLAUDE.md` | Session start | Primary auto-loaded file |
| `~/.claude/CLAUDE.md` | Session start | Global instructions |
| `.claude/rules/*.md` | Session start | Same priority as root CLAUDE.md |
| `<parent-dir>/CLAUDE.md` | Session start | All parents above CWD |
| `<subdir>/CLAUDE.md` | When reading files in subdir | NOT at session start |
| `--add-dir` CLAUDE.md | If `CLAUDE_CODE_ADDITIONAL_DIRECTORIES_CLAUDE_MD=1` | Off by default |
| `AGENTS.md` | Never (not supported) | Use symlink or reference workaround |
| `CLAUDE-*.md` or patterns | Never | No pattern matching |

---

## 2. How Does Claude Code Handle HTML in Markdown?

### HTML Comments

**No definitive answer found in documentation.** The search returned:
- Feature requests to add HTML comment markers to code blocks (e.g., `<!-- mdblk:{hash} lang:python -->`)
- No explicit documentation on whether `<!-- comment -->` content is stripped or appears in context

**Inference from standard markdown processing:**
- HTML comments in markdown are typically preserved in raw text (not rendered visually)
- Claude Code likely sees the full file content, including comments
- **Assumption:** HTML comments ARE visible in context (not stripped)

**Recommendation:** Test empirically by adding a comment to CLAUDE.md and checking if Claude responds to instructions inside it.

### `<details>` Tags

**No evidence found** that Claude Code has special handling for `<details>` tags.

**Expected behavior (based on markdown processing):**
- `<details>` tags are rendered as HTML in markdown viewers
- In plain text context (like LLM processing), they appear as raw HTML tags
- NO "load on demand" or collapse mechanism for LLM context

**Implication:** Putting content inside `<details>` does NOT reduce context window usage. The full text is loaded.

### Context Window Management

From web search:
- Claude Code has a 200k token context window (Sonnet 4.5)
- Anthropic recently increased Sonnet to 1M tokens, but best practices still recommend keeping context focused
- **CLAUDE.md strategy:** "Keep it concise. One option: break up information into separate markdown files and reference them inside the CLAUDE.md file."

**NO native "load on demand" mechanism for markdown sections.** All loaded files consume full context.

**Workaround patterns:**
1. Split into multiple files (e.g., `.claude/rules/architecture.md`, `.claude/rules/troubleshooting.md`)
2. Reference external files: "See `docs/detailed-guide.md` for full reference" (Claude reads on demand when needed)
3. Use skills with `references/` subdirectory (loaded only when skill is invoked)

---

## 3. Claude Code Plugin MCP Servers

### How to Register an MCP Server

**Three methods:**

#### Method 1: Inline in `plugin.json`

Place `mcpServers` key directly in `.claude-plugin/plugin.json`:

```json
{
  "name": "my-plugin",
  "version": "0.1.0",
  "description": "Plugin with MCP server",
  "author": {"name": "MK", "email": "mk@example.com"},
  "mcpServers": {
    "my-server": {
      "type": "stdio",
      "command": "bash",
      "args": ["${CLAUDE_PLUGIN_ROOT}/scripts/start-mcp.sh"],
      "env": {
        "API_KEY": "value"
      }
    }
  }
}
```

#### Method 2: Separate `.mcp.json` File

Create `.mcp.json` at plugin root:

```json
{
  "mcpServers": {
    "my-server": {
      "command": "node",
      "args": ["${CLAUDE_PLUGIN_ROOT}/server/index.js"],
      "env": {}
    }
  }
}
```

**Evidence:** Both `tuivision` and `serena` plugins use this pattern.

#### Method 3: User-Level Config

Manually edit `~/.config/Claude/claude_desktop_config.json` (not plugin-specific, but documented for completeness):

```json
{
  "mcpServers": {
    "my-server": {
      "type": "stdio",
      "command": "npx",
      "args": ["-y", "mcp-package-name"]
    }
  }
}
```

### Plugin MCP Server Lifecycle

**From plugin-development.md:**
- Plugins define MCP servers in `.mcp.json` at plugin root OR inline in `plugin.json`
- When plugin is enabled, its MCP servers start automatically
- Plugin MCP servers work identically to user-configured servers

**Environment variables available:**
- `${CLAUDE_PLUGIN_ROOT}` — absolute path to plugin install directory
- `${CLAUDE_PROJECT_DIR}` — user's project root
- Custom env vars can be set in the `env` object

### Overhead (Startup Time, Memory)

**No hard numbers found in documentation.**

**Inferences from examples:**
- **Serena plugin** (official): Uses `uvx --from git+https://github.com/oraios/serena serena start-mcp-server` (on-demand install, likely 1-3s startup)
- **Interject plugin** (custom): Uses `uv run --directory ${CLAUDE_PLUGIN_ROOT} interject-mcp` (2-5s startup with embedding model load)
- **Tuivision plugin** (custom): Uses `bash ${CLAUDE_PLUGIN_ROOT}/scripts/start.sh` (instant if no dependencies)

**Memory:** Each MCP server is a separate process. Python servers with ML models (like interject with sentence-transformers) can consume 200-500MB. Simple servers are <50MB.

**Context window impact:** "Each enabled MCP server adds tool definitions to Claude's system prompt, consuming part of your context window even when not actively used." (From MCP setup guide)

**Recommendation:** MCP servers are appropriate for tools with:
- Complex state (databases, file watchers)
- External integrations (APIs, services)
- Heavy computation (embeddings, analysis)

NOT appropriate for:
- Simple transformations (use skills instead)
- One-time operations (use commands)
- Session-scoped state (use hooks with SessionStart context injection)

### Can MCP Tools Return Structured Data?

**Yes.** MCP tool responses are JSON objects. Claude Code presents them as text to the LLM, but the data structure is preserved.

**Example from interject server.py:**

```python
@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    if name == "interject_inbox":
        results = ctx["db"].get_discoveries_above_threshold(...)
        return [TextContent(
            type="text",
            text=json.dumps([{
                "id": r["id"],
                "title": r["title"],
                "score": r["score"],
                # ... more fields
            } for r in results], indent=2)
        )]
```

The LLM receives formatted JSON. It can parse and use selectively.

**Best practice:** Return structured JSON for data-heavy responses. The LLM can extract what's needed.

---

## 4. Intermem Plugin: Current Structure

### Files Discovered

```
/root/projects/Interverse/plugins/intermem/
├── .claude-plugin/
│   └── plugin.json          # Exists
├── CLAUDE.md                # Exists (48 lines)
├── skills/
│   └── synthesize/
│       └── SKILL.md         # Exists
├── intermem/                # Python library
│   ├── scanner.py
│   ├── stability.py
│   ├── citations.py
│   ├── validator.py
│   ├── dedup.py
│   ├── promoter.py
│   ├── pruner.py
│   ├── journal.py
│   └── metadata.py
├── pyproject.toml           # Exists
└── tests/
```

### Current plugin.json

```json
{
  "name": "intermem",
  "version": "0.1.0",
  "description": "Memory synthesis — graduates stable auto-memory facts to AGENTS.md/CLAUDE.md",
  "author": {
    "name": "mistakeknot",
    "email": "mistakeknot@vibeguider.org"
  },
  "skills": [
    "./skills/synthesize"
  ]
}
```

**No MCP server defined.** Current implementation is skill-only.

### Current Architecture (from CLAUDE.md)

**Phase 1 pipeline:** scan → stability → validate → dedup → approve → promote+prune

**Design decisions:**
- "No hooks (Clavain hook budget)"
- "No MCP server (skill-only)"
- "Python stdlib only (sqlite3 is stdlib)"

**Constraints:**
- `.intermem/` must be in `.gitignore` for target project
- Runs via `uv run python -m intermem --project-dir <path>`

---

## 5. Comparison: Serena vs Interject MCP Implementation

### Serena (Official Plugin)

**Structure:**
- External GitHub repo: `github.com/oraios/serena`
- Installed via `uvx --from git+https://github.com/oraios/serena serena start-mcp-server`
- No local source in plugin cache (fetched on demand)

**MCP config (.mcp.json):**
```json
{
  "serena": {
    "command": "uvx",
    "args": ["--from", "git+https://github.com/oraios/serena", "serena", "start-mcp-server"]
  }
}
```

**Tools offered (from name):**
- `read_file`, `create_text_file`, `list_dir`, `find_file`
- `replace_content`, `search_for_pattern`
- `get_symbols_overview`, `find_symbol`, `find_referencing_symbols`
- `replace_symbol_body`, `insert_after_symbol`, `rename_symbol`
- `write_memory`, `read_memory`, `list_memories`, `delete_memory`, `edit_memory`
- `execute_shell_command`
- `activate_project`, `switch_modes`, `get_current_config`

**Memory tools:** `write_memory`, `read_memory`, `list_memories`, `delete_memory`, `edit_memory`

**Implementation unknown** (external repo, not inspected).

### Interject (Custom Plugin)

**Structure:**
- Local plugin source: `/root/projects/Interverse/plugins/interject/`
- Python package with `pyproject.toml`
- Entry point: `interject-mcp = "interject.server:main"`

**MCP config (in plugin.json):**
```json
{
  "mcpServers": {
    "interject": {
      "type": "stdio",
      "command": "uv",
      "args": [
        "run",
        "--directory",
        "${CLAUDE_PLUGIN_ROOT}",
        "interject-mcp"
      ],
      "env": {
        "EXA_API_KEY": "eba9629f-75e9-467c-8912-a86b3ea8d678"
      }
    }
  }
}
```

**Tools offered (from server.py):**
- `interject_scan` — Trigger discovery scan
- `interject_inbox` — Get high-score discoveries
- `interject_detail` — Get full discovery details
- `interject_promote` — Create bead from discovery
- `interject_dismiss` — Negative feedback
- `interject_profile` — View/edit interest profile
- `interject_status` — Health check
- `interject_search` — Semantic search across discoveries
- `interject_session_context` — Session-start briefing
- `interject_record_query` — Log user query for learning

**Server structure (server.py):**

```python
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import TextContent, Tool

def create_server(config: dict | None = None) -> tuple[Server, dict]:
    server = Server("interject")

    @server.list_tools()
    async def list_tools() -> list[Tool]:
        return [Tool(...), ...]

    @server.call_tool()
    async def call_tool(name: str, arguments: dict) -> list[TextContent]:
        # ... handle tools
        return [TextContent(type="text", text=json.dumps(result))]

    return server, ctx

async def run_server():
    server, ctx = create_server()
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, ...)

def main() -> None:
    asyncio.run(run_server())
```

**Key pattern:** `uv run --directory ${CLAUDE_PLUGIN_ROOT} <entry-point>` ensures dependencies are resolved from plugin's virtual environment.

---

## 6. MCP Server Design Patterns

### Pattern 1: External Package (Serena)

**Pros:**
- No local source to maintain in plugin repo
- Updates via `uvx` package manager
- Small plugin footprint

**Cons:**
- Network dependency on first run
- Harder to debug/modify
- Version pinning is opaque

### Pattern 2: Bundled Python Server (Interject)

**Pros:**
- Full control over implementation
- No external dependencies
- Easy to debug/test
- Virtual env isolation via `uv run --directory`

**Cons:**
- Plugin repo must include full Python package
- Larger plugin download
- Must manage dependencies in `pyproject.toml`

### Pattern 3: Shell Script Launcher (Tuivision)

**Pros:**
- Flexible — can do environment setup before starting server
- Easy to add conditional logic
- Can wrap complex startup sequences

**Cons:**
- Extra layer of indirection
- Must ensure script is executable in cache

**Example (tuivision .mcp.json):**
```json
{
  "mcpServers": {
    "tuivision": {
      "command": "bash",
      "args": ["${CLAUDE_PLUGIN_ROOT}/scripts/start.sh"]
    }
  }
}
```

### Pattern 4: Inline in plugin.json (Interlock, Clavain)

**Pros:**
- Single source of truth
- Easier to version-sync (one file)

**Cons:**
- `plugin.json` gets large if many servers/tools
- Harder to diff/review

**Example (interlock plugin.json):**
```json
{
  "name": "interlock",
  "mcpServers": {
    "interlock": {
      "type": "stdio",
      "command": "${CLAUDE_PLUGIN_ROOT}/bin/launch-mcp.sh",
      "env": {
        "INTERMUTE_URL": "http://127.0.0.1:7338"
      }
    }
  }
}
```

---

## 7. Implementation Recommendations for Intermem

### Current State

**Phase 1 (implemented):**
- Skill-only: `/intermem:synthesize`
- Runs as CLI: `uv run python -m intermem --project-dir <path>`
- No MCP server (by design choice documented in CLAUDE.md)

**Constraints from CLAUDE.md:**
- "No hooks (Clavain hook budget)" — hook slots are a limited resource
- "No MCP server (skill-only)" — current architecture decision
- Python stdlib only (sqlite3)

### Should Intermem Add an MCP Server?

**Arguments FOR:**
- **On-demand memory retrieval:** MCP tools could expose `intermem_search`, `intermem_get_entry`, `intermem_validate_citations` for mid-session use without invoking full synthesis pipeline
- **Background validation:** SessionStart hook could call MCP tool to check for stale promoted entries (validate-only mode)
- **Consistency with other plugins:** Interject, Interlock, Tuivision, Interserve all use MCP for stateful operations
- **Selective context loading:** MCP tool can return just relevant memory entries based on current task, rather than loading all of AGENTS.md

**Arguments AGAINST:**
- **Overhead:** Embedding model load (if semantic search is added) adds 200-500MB RAM + 2-5s startup
- **Complexity:** Current skill-based flow is simple and works
- **Context consumption:** Each MCP tool definition consumes prompt space even when unused
- **Violates current design constraint:** CLAUDE.md says "No MCP server (skill-only)"

### Hybrid Approach: Skill + Lightweight MCP Server

**Recommendation:** Add a minimal MCP server for query-time operations only. Keep synthesis pipeline as skill.

**MCP tools to add:**
1. `intermem_search` — Semantic search across stable memory entries (from `.intermem/metadata.db`)
2. `intermem_validate_citations` — Check if a file path or module reference is still valid
3. `intermem_check_staleness` — Report promoted entries with broken citations (for session start)

**What stays as skill:**
- Full synthesis pipeline (scan → stability → validate → dedup → approve → promote)
- User-driven approval workflow
- Promotion and pruning (writes to AGENTS.md/CLAUDE.md)

**Implementation:**
```json
{
  "name": "intermem",
  "version": "0.2.0",
  "skills": ["./skills/synthesize"],
  "mcpServers": {
    "intermem": {
      "type": "stdio",
      "command": "uv",
      "args": [
        "run",
        "--directory",
        "${CLAUDE_PLUGIN_ROOT}",
        "intermem-mcp"
      ]
    }
  }
}
```

**New entry point in pyproject.toml:**
```toml
[project.scripts]
intermem = "intermem.__main__:main"          # existing CLI
intermem-mcp = "intermem.mcp_server:main"    # new MCP server
```

**Startup cost mitigation:**
- Delay embedding model load until first search (lazy init)
- Use lightweight sqlite queries for validation tools
- No session-start auto-scan (only on-demand)

### Alternative: Stay Skill-Only, Use Hook for Stale Detection

If MCP server is too heavy:

**Add a SessionStart hook** that:
1. Checks if `--validate-only` mode detects stale entries
2. Injects context warning if staleness detected: "⚠️ 3 promoted memory entries have broken citations. Run `/intermem:synthesize --validate-only` to review."

**Pros:**
- No MCP server overhead
- Still provides proactive staleness detection
- Fits within existing architecture

**Cons:**
- No mid-session memory search
- No on-demand citation validation

---

## 8. HTML in Markdown: Load-on-Demand Alternatives

Since `<details>` tags don't reduce context consumption, here are alternatives:

### Option 1: Separate Files + References

**Pattern:**
```markdown
## Architecture

Core architecture is documented in `docs/architecture/core-system.md`.

Key decision: use WAL protocol for atomic promotions (see `docs/architecture/wal-protocol.md`).
```

**Pros:**
- Only loads full doc when Claude reads it
- Clear separation of reference vs. quick-reference
- Easy to maintain separate docs

**Cons:**
- Fragmentation (many small files)
- Claude must know to ask for the file

### Option 2: Skill References

**Pattern:**
```
plugins/intermem/
├── skills/
│   └── synthesize/
│       ├── SKILL.md
│       └── references/
│           ├── validation-rules.md
│           ├── citation-patterns.md
│           └── troubleshooting.md
```

**Skill frontmatter:**
```yaml
---
name: synthesize
description: Memory synthesis pipeline
references:
  - validation-rules.md
  - citation-patterns.md
---
```

**Pros:**
- References loaded only when skill is invoked
- Co-located with skill logic
- Claude Code native pattern

**Cons:**
- Only useful for skill-scoped context
- Not available outside skill invocation

### Option 3: MCP Tool for Selective Doc Retrieval

**New MCP tool:**
```python
Tool(
    name="intermem_get_doc_section",
    description="Retrieve a specific documentation section on demand",
    inputSchema={
        "type": "object",
        "properties": {
            "section": {
                "type": "string",
                "enum": ["validation", "citations", "troubleshooting", "architecture"]
            }
        }
    }
)
```

**Implementation:**
```python
if name == "intermem_get_doc_section":
    section = arguments["section"]
    doc_path = Path(PLUGIN_ROOT) / "docs" / f"{section}.md"
    return [TextContent(type="text", text=doc_path.read_text())]
```

**Pros:**
- True on-demand loading
- Claude can request specific sections mid-session
- No AGENTS.md bloat

**Cons:**
- Requires MCP server
- Claude must know which sections exist (needs tool description or initial context list)

---

## 9. Key Findings Summary

### File Loading
1. **CLAUDE.md is auto-loaded** from project root, parent dirs, and `.claude/rules/*.md` at session start
2. **AGENTS.md is NOT auto-loaded** by Claude Code (use symlink or reference)
3. **No pattern matching** — only exact `CLAUDE.md` filename
4. **Subdirectory CLAUDE.md** loaded only when working in that subtree (not at session start)
5. **`--add-dir` CLAUDE.md** requires `CLAUDE_CODE_ADDITIONAL_DIRECTORIES_CLAUDE_MD=1` env var

### HTML in Markdown
1. **HTML comments likely visible** in context (not stripped), but not documented
2. **`<details>` tags do NOT collapse** in LLM context — full text is loaded
3. **No native load-on-demand mechanism** — all loaded files consume full context
4. **Workarounds:** separate files with references, skill references, or MCP tool for selective retrieval

### MCP Servers
1. **Three registration methods:** inline in `plugin.json`, separate `.mcp.json`, or user config
2. **Auto-start on plugin enable** — no manual setup needed
3. **Overhead:** 1-5s startup for Python servers, 200-500MB RAM if using ML models
4. **Context cost:** Tool definitions consume prompt space even when unused
5. **Structured data:** MCP tools can return JSON, LLM parses selectively
6. **Environment:** `${CLAUDE_PLUGIN_ROOT}` and `${CLAUDE_PROJECT_DIR}` available

### Intermem Current State
1. **No MCP server** (by design: "skill-only")
2. **48-line CLAUDE.md** — well under bloat threshold
3. **Python library** with CLI entry point (`intermem.__main__:main`)
4. **SQLite state** in `.intermem/metadata.db`
5. **Validation pipeline implemented** (Phase 1)

---

## 10. Sources

### Claude Code Documentation & Loading Behavior
- [Using CLAUDE.MD files: Customizing Claude Code for your codebase](https://claude.com/blog/using-claude-md-files)
- [Writing a good CLAUDE.md | HumanLayer Blog](https://www.humanlayer.dev/blog/writing-a-good-claude-md)
- [How to use AGENTS.md in Claude Code](https://aiengineerguide.com/blog/how-to-use-agents-md-in-claude-code/)
- [Feature Request: Support AGENTS.md. · Issue #6235](https://github.com/anthropics/claude-code/issues/6235)
- [How to Write a Good CLAUDE.md File](https://www.builder.io/blog/claude-md-guide)
- [Specify automated inclusion for AGENTS.md for parent folders. · Issue #39](https://github.com/agentsmd/agents.md/issues/39)
- [A Complete Guide To AGENTS.md](https://www.aihero.dev/a-complete-guide-to-agents-md)
- [AGENTS.md becomes the convention](https://pnote.eu/notes/agents-md/)

### MCP Server Setup & Configuration
- [Connect Claude Code to tools via MCP - Claude Code Docs](https://code.claude.com/docs/en/mcp)
- [Add MCP Servers to Claude Code - Setup & Configuration Guide | MCPcat](https://mcpcat.io/guides/adding-an-mcp-server-to-claude-code/)
- [Configuring MCP Tools in Claude Code - The Better Way - Scott Spence](https://scottspence.com/posts/configuring-mcp-tools-in-claude-code)
- [How to Setup Claude Code MCP Servers | ClaudeLog](https://claudelog.com/faqs/how-to-setup-claude-code-mcp-servers/)

### Context Window & Markdown Handling
- [Claude Code overview - Claude Code Docs](https://code.claude.com/docs/en/overview)
- [How to Customize Claude Code Status Bar to Monitor Context Window](https://pasqualepillitteri.it/en/news/162/claude-code-status-bar-context-monitor-guide)
- [Managing Context Window in Claude Code | VibeCoding Best Practices](https://jenochs.github.io/vibecoding/page3.html)

### Local Plugin Analysis
- `/home/mk/.claude/plugin-development.md` — Plugin structure, lifecycle, MCP registration patterns
- `/root/projects/Interverse/plugins/intermem/CLAUDE.md` — Current architecture and constraints
- `/home/mk/.claude/plugins/cache/interagency-marketplace/interject/0.1.5/` — MCP server implementation example
- `/home/mk/.claude/plugins/cache/claude-plugins-official/serena/` — Official MCP plugin example
