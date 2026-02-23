---
name: interserve
description: "Interserve — Codex spark classifier and context compression via MCP"
---
# Gemini Skill: interserve

You have activated the interserve capability.

## Base Instructions
# Interserve

Codex spark classifier and context compression — an MCP server exposing three tools that delegate file reading and classification to Codex, saving Claude's context window for orchestration.

## Architecture

```
cmd/interserve-mcp/main.go    ← MCP stdio entrypoint
internal/tools/tools.go        ← tool registration + handler glue
internal/extract/              ← markdown section splitter (pure, no I/O)
internal/classify/             ← section-to-agent classifier (shells out to dispatch.sh)
internal/query/                ← file Q&A / summarize / extract (shells out to dispatch.sh)
hooks/pre-read-intercept.sh    ← PreToolUse:Read hook — suggests codex_query for large files
bin/launch-mcp.sh              ← auto-builds binary if missing, then exec's it
```

**Data flow:** Claude invokes MCP tool → `tools.go` handler → `classify` or `query` package writes a prompt to a temp file → shells out to `dispatch.sh --tier fast --sandbox read-only` → reads Codex output from temp file → returns structured JSON to Claude.

**Transport:** Stdio MCP (on-demand, no systemd). Launched by Claude Code via `bin/launch-mcp.sh`, which auto-builds the Go binary on first run.

## MCP Tools

| Tool | Purpose | Packages |
|------|---------|----------|
| `extract_sections` | Split markdown by `##` headings (honors fences, skips frontmatter) | `extract` |
| `classify_sections` | Route sections to flux-drive agents via Codex spark | `extract` → `classify` |
| `codex_query` | Delegate file reading to Codex — answer, summarize, or extract mode | `query` |

## Key Files

| File | Purpose |
|------|---------|
| `cmd/interserve-mcp/main.go` | Entrypoint — creates MCP server, registers tools, serves stdio |
| `internal/tools/tools.go` | Tool definitions, argument parsing, handler wiring |
| `internal/extract/extract.go` | `ExtractSections()` — fence-aware markdown splitter |
| `internal/classify/classify.go` | `Classify()` — dispatches to Codex, parses response, builds slicing map |
| `internal/classify/prompt.go` | `BuildPrompt()` + `DefaultAgents()` + `CrossCuttingAgents` |
| `internal/query/query.go` | `Query()` — reads files, dispatches to Codex, returns compact answer |
| `internal/query/prompt.go` | `BuildPrompt()` — mode-specific prompt builder (answer/summarize/extract) |
| `hooks/pre-read-intercept.sh` | PreToolUse:Read — blocks large file reads with codex_query suggestion |
| `bin/launch-mcp.sh` | Auto-build wrapper — builds binary if missing, then `exec`s it |
| `.claude-plugin/plugin.json` | Plugin manifest — MCP server config, env vars |

## Conventions

- **Go module:** `github.com/mistakeknot/interserve`, requires Go 1.23+
- **MCP library:** `github.com/mark3labs/mcp-go v0.43.2`
- **Temp file prefix:** `interserve-prompt-*`, `interserve-output-*`, `interserve-query-prompt-*`, `interserve-query-output-*`
- **Error handling:** Tools return `mcp.NewToolResultError()` (never panic). Classify/Query return structured error JSON with `status: "error"` or `"no_classification"`
- **Dispatch delegation:** All Codex CLI interaction goes through `dispatch.sh` — interserve never calls `codex` directly
- **Env var:** `INTERSERVE_DISPATCH_PATH` — path to dispatch.sh (defaults to clavain's copy)

## Classification Logic

1. `ExtractSections()` splits document by `##` headings (skips fenced code blocks and YAML frontmatter)
2. `BuildPrompt()` creates a classification prompt listing agent domains + section previews
3. Codex spark returns JSON mapping sections to agents with relevance (priority/context) and confidence
4. `buildResult()` normalizes assignments, filters unknown agents, and builds per-agent slicing maps
5. **Domain mismatch guard:** If no agent gets >10% priority lines, classification is marked failed
6. **80% threshold:** If an agent's priority sections cover ≥80% of lines, it gets the full document

**Default agents:** fd-safety, fd-correctness, fd-performance, fd-user-product, fd-game-design
**Cross-cutting (always included):** fd-architecture, fd-quality

## Hook Behavior

The `pre-read-intercept.sh` hook fires on `PreToolUse:Read` when interserve mode is active (`clodex-toggle.flag` exists):
- **Blocks** reads of code files ≥200 lines (first read only)
- **Allows** targeted reads (with offset), /tmp/ files, config/doc extensions, small files
- **Dedup:** Second read of same file in same session passes through (flag at `/tmp/interserve-read-denied-{session}-{hash}`)

## Development

```bash
# Build
go build -o bin/interserve-mcp ./cmd/interserve-mcp/

# Test (24 tests: classify 4, extract 8, query 12)
go test ./... -v

# Integration test (requires dispatch.sh + codex)
bash test/integration_test.sh

# Hook tests (9 tests)
bash test/hook_test.sh

# Syntax check
bash -n hooks/pre-read-intercept.sh
bash -n bin/launch-mcp.sh
```

## Gotchas

- Binary must be built before MCP server can start — `launch-mcp.sh` handles this automatically, but `go` must be in PATH
- `dispatch.sh` must exist at `INTERSERVE_DISPATCH_PATH` or the hardcoded default — server exits immediately if not found
- Codex spark responses sometimes include markdown code fences around JSON — both `classify` and `query` packages strip these via `stripCodeFences()`
- The `codex_query` tool name intentionally describes the function (not the provider) — it was NOT renamed during the clodex→interserve migration
- Query mode has file size limits: 1MB per file, 10k lines max (head 5k + tail 2k for oversized files)


