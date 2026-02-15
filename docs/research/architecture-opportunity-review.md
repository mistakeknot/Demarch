# Architectural Opportunity Review — Interverse Monorepo

**Date:** 2026-02-15
**Scope:** 22 plugins + 1 Go service + 1 hub (Clavain)
**Purpose:** Identify architectural gaps, fragile coupling, and missing infrastructure

---

## Executive Summary

The Interverse monorepo exhibits strong modularity with clear separation of concerns across 24 independent modules. However, several architectural opportunities exist to improve system-wide reliability, observability, and integration quality. Key findings:

1. **Cross-plugin coordination relies on implicit file contracts** — no schema validation or versioning for sideband files (`/tmp/clavain-*`, signal files)
2. **No unified health monitoring** — 22 plugins, 1 service, multiple MCP servers, but no system-wide observability
3. **Version coupling is manual and error-prone** — `interbump.sh` is centralized but still requires discipline
4. **Shared infrastructure is duplicated** — SQLite patterns, HTTP clients, signal emission, bash libraries all implemented per-module
5. **Missing CI/CD orchestration** — no monorepo-aware testing, no dependency graph awareness

---

## 1. Fragile Coupling Patterns (Needs Formalization)

### 1.1 Sideband File Protocol (interphase ↔ interline ↔ clavain)

**Current state:**
- `interphase` writes `/tmp/clavain-bead-${session_id}.json` (bead phase data)
- `clavain` writes `/tmp/clavain-dispatch-$$.json` (Codex dispatch state)
- `interlock` writes `/var/run/intermute/signals/{project-slug}-{agent-id}.jsonl` (coordination signals)
- `interline` reads all three sources for statusline rendering

**Fragility:**
- No schema validation — typos or structure changes silently break consumers
- No versioning — schema evolution requires coordinated changes across 3+ repos
- No error detection — missing files, malformed JSON, or partial writes degrade silently
- PID-based paths (`$$`) create cleanup issues across session crashes

**Opportunity: Sideband Protocol Library (`interband`)**

Create a shared Go/Bash library for structured sideband communication:

```go
// interband schema format
type SidebandMessage struct {
    Version   string                 `json:"version"`   // "1.0.0"
    Namespace string                 `json:"namespace"` // "interphase", "clavain", "interlock"
    Type      string                 `json:"type"`      // "bead_phase", "dispatch", "signal"
    SessionID string                 `json:"session_id"`
    Timestamp time.Time              `json:"timestamp"`
    Payload   map[string]interface{} `json:"payload"`
}
```

**Features:**
- Atomic writes via `write+rename` (no partial reads)
- Schema version negotiation (readers tolerate older writers)
- Centralized path logic: `~/.interband/{namespace}/{session_id}.json`
- Cleanup on session end via hook
- JSON Schema validation for common types
- Bash helper: `interband_write <namespace> <type> <json>`

**Integration points:**
- `/root/projects/Interverse/infra/interband/` (new module)
- Hook in `clavain`, `interphase`, `interlock`: source `interband.sh` lib
- `interline` consumes via `interband_read_all` instead of raw file parsing

---

### 1.2 Signal File Format (interlock → interline)

**Current state:**
- `interlock-signal.sh` emits JSONL to `/var/run/intermute/signals/{project}-{agent}.jsonl`
- Fields: `version`, `layer`, `icon`, `text`, `priority`, `timestamp`
- No rotation, no size limits, no schema enforcement

**Fragility:**
- Unbounded growth (long-running agents accumulate MB of signals)
- No schema validation (typos in `layer` or `priority` silently fail)
- Path construction duplicated in emitter and consumer
- No signal expiry (old signals never age out)

**Opportunity: Structured Signal Bus (integrate with `interband`)**

Extend `interband` with signal-specific features:

- **Time-windowed retention**: signals older than 1h auto-pruned
- **Size-bounded files**: rotate at 10KB, keep last 3 files
- **Schema enforcement**: enum validation for `layer`, `priority`, `icon`
- **Unified path logic**: `~/.interband/signals/{namespace}/{session_id}.jsonl`

**Bash API:**
```bash
interband_signal <layer> <priority> <icon> <text>  # auto-adds timestamp, version, session_id
interband_signals_since <namespace> <timestamp>     # read with filtering
```

---

### 1.3 Environment Variable Contract (`INTERMUTE_*`, `CLAUDE_*`)

**Current state:**
- `INTERMUTE_AGENT_ID`, `INTERMUTE_URL`, `INTERMUTE_SOCKET` set by interlock session-start hook
- `CLAUDE_SESSION_ID` set by clavain session-start hook via `CLAUDE_ENV_FILE`
- `CLAUDE_PLUGIN_ROOT` set by Claude Code core
- No documentation of full contract, no validation

**Fragility:**
- New plugins must reverse-engineer which vars are available
- Typos in env var names cause silent failures (e.g., `INTERMUTE_AGENT_NAME` vs `AGENT_NAME`)
- No detection of missing required vars until runtime

**Opportunity: Environment Contract Registry**

Create `/root/projects/Interverse/docs/contracts/environment.md`:

```markdown
## Standard Environment Variables

| Variable | Set By | Required For | Format | Example |
|----------|--------|--------------|--------|---------|
| `CLAUDE_SESSION_ID` | clavain SessionStart | interphase, interline, interband | UUID | `abc-123-def` |
| `CLAUDE_PLUGIN_ROOT` | Claude Code core | All plugins | Path | `/path/to/plugin` |
| `INTERMUTE_AGENT_ID` | interlock SessionStart | clavain hooks, interlock tools | String | `agent-xyz` |
| `INTERMUTE_URL` | interlock SessionStart | interlock MCP server | URL | `http://127.0.0.1:7338` |
| `INTERMUTE_SOCKET` | interlock SessionStart (optional) | interlock MCP server | Path | `/var/run/intermute.sock` |
| `EXA_API_KEY` | User config | interject, interflux | String | `eba9629f-...` |
```

Add `scripts/check-env.sh` (sourced by plugins):
```bash
require_env CLAUDE_SESSION_ID CLAUDE_PLUGIN_ROOT
optional_env INTERMUTE_AGENT_ID INTERMUTE_URL
```

---

## 2. Missing Service-Layer Capabilities

### 2.1 No Health Aggregation Service

**Current state:**
- `intermute` has `/api/health` (Go service)
- `interkasten` has `interkasten_health` MCP tool (Node.js daemon)
- `interlock` checks `intermute` reachability in session-start hook
- No unified view of ecosystem health

**Opportunity: Health Aggregator Service (`interstatus`)**

Lightweight HTTP service that polls all registered modules:

```
GET /health → {
  "intermute": {"status": "healthy", "uptime": 3600, "last_check": "..."},
  "interkasten": {"status": "degraded", "error": "Notion API timeout"},
  "interlock": {"status": "healthy", "agents": 3},
  "tldr-swinton": {"status": "unknown", "reason": "no MCP connection"},
  ...
}
```

**Features:**
- Registry at `~/.config/interstatus/modules.yaml` (plugins self-register via hook)
- Polling every 30s with exponential backoff on failure
- Exposes Prometheus metrics for external monitoring
- `/clavain:health-status` command shows human-readable summary
- Auto-detects MCP servers via `plugin.json` parsing

**Integration:**
- `/root/projects/Interverse/services/interstatus/` (new Go service)
- Plugins add `SessionStart` hook to register with interstatus
- `interline` can show system-wide health in statusline

---

### 2.2 No Centralized Log Aggregation

**Current state:**
- `intermute` logs to stdout (systemd journal)
- MCP servers log to stderr (captured by Claude Code)
- Hook scripts log to `/var/log/claude-perms-watch.log` (permission watcher only)
- No way to correlate events across modules

**Opportunity: Structured Logging Service (`interlog`)**

Lightweight log aggregator with session-aware correlation:

```
POST /log → {
  "session_id": "...",
  "module": "interlock",
  "level": "warn",
  "message": "Conflict detected on file.go",
  "context": {"file": "file.go", "agent": "agent-xyz"}
}
```

**Features:**
- SQLite backend: `(timestamp, session_id, module, level, message, context_json)`
- Query API: `/logs?session_id=...&module=...&since=...`
- Auto-prune logs older than 7 days
- Bash helper: `interlog warn "message" '{"key":"val"}'`
- `/clavain:logs` command for interactive querying

**Integration:**
- Hook libraries (lib.sh, lib-gates.sh, lib-interspect.sh) call `interlog`
- MCP servers send structured logs to interlog instead of stderr
- Debugging workflow: `/clavain:logs --session --level=error` shows all errors in current session

---

### 2.3 No Background Job Scheduler

**Current state:**
- `interject` scans via manual skill invocation (`/interject:scan`)
- `interwatch` drift checks are on-demand
- `tool-time` uploads via cron or manual trigger
- No coordinated scheduling, no dependency awareness

**Opportunity: Job Scheduler Service (`interqueue`)**

Cron-like scheduler with job dependencies and session awareness:

```yaml
# ~/.config/interqueue/jobs.yaml
jobs:
  interject-scan:
    schedule: "0 */6 * * *"  # Every 6 hours
    command: "interject-mcp scan --incremental"
    depends_on: []

  tool-time-upload:
    schedule: "0 2 * * *"  # Daily at 2am
    command: "python3 /path/to/upload.py"
    depends_on: [interject-scan]  # Wait for scan to finish

  interwatch-drift:
    schedule: "0 8 * * 1"  # Weekly Monday 8am
    command: "bash /path/to/drift-check.sh"
    depends_on: []
```

**Features:**
- DAG execution (jobs wait for dependencies)
- Session isolation (jobs don't run during active Claude Code sessions)
- Retry logic with exponential backoff
- Logs to `interlog` for correlation
- `/clavain:jobs` command to view status and trigger manual runs

---

## 3. Duplicated Shared Infrastructure

### 3.1 SQLite Patterns (intermute, interkasten, tool-time, tldr-swinton, interject)

**Current duplication:**
- **Schema management**: each module has custom migration logic
- **Connection pooling**: reimplemented in Go (intermute), Node.js (interkasten), Python (interject, tldr-swinton)
- **Query builders**: raw SQL strings everywhere, no type safety
- **Backup/restore**: no standardized approach

**Opportunity: SQLite Library (`intersqlite`)**

Shared library with language-specific bindings:

**Go (`intersqlite/go`):**
```go
import "github.com/mistakeknot/intersqlite/go"

db := intersqlite.Open("app.db", &intersqlite.Config{
    Migrations: "./migrations/*.sql",
    Journal:    "WAL",
    Backup:     true,  // Auto-backup on schema change
})
```

**Python (`intersqlite/python`):**
```python
from intersqlite import Database

db = Database("app.db", migrations_dir="./migrations")
db.query("SELECT * FROM table WHERE id = ?", [123])
```

**Features:**
- Standardized migration format (`001_init.sql`, `002_add_column.sql`)
- Auto-backup before schema changes
- WAL mode by default
- Connection pooling with sane defaults
- Query logging to `interlog`
- Schema version tracking

**Integration:**
- `/root/projects/Interverse/infra/intersqlite/` (new library)
- Migrate `intermute`, `interkasten`, `interject`, `tldr-swinton`, `tool-time` to use it
- Reduces module-specific SQLite code by ~60%

---

### 3.2 HTTP Client Patterns (interlock, tool-time, clavain hooks)

**Current duplication:**
- `interlock/internal/client/client.go` — HTTP client for intermute API
- `tool-time/upload.py` — HTTP client for community API
- `clavain/hooks/bead-agent-bind.sh` — `curl` calls to intermute
- Each implements retry logic, timeout, error handling differently

**Opportunity: HTTP Client Library (`interhttp`)**

Standardized client with consistent retry/timeout/auth:

**Go:**
```go
import "github.com/mistakeknot/interhttp"

client := interhttp.New(&interhttp.Config{
    BaseURL: "http://127.0.0.1:7338",
    Timeout: 5 * time.Second,
    Retries: 3,
})

var result map[string]interface{}
err := client.Get("/api/agents", &result)
```

**Bash:**
```bash
source /path/to/interhttp.sh
interhttp_get "http://127.0.0.1:7338/api/agents" > agents.json
interhttp_post "http://127.0.0.1:7338/api/messages" '{"from":"..."}' > response.json
```

**Features:**
- Exponential backoff retry (3 attempts)
- Circuit breaker for failing endpoints
- Structured error responses
- Auth header injection (`Authorization: Bearer`)
- Logs to `interlog`

---

### 3.3 Bash Hook Libraries (clavain, interphase, interlock)

**Current duplication:**
- `clavain/hooks/lib.sh` — `escape_for_json`, session ID parsing
- `interphase/hooks/lib-phase.sh` — bead state tracking
- `interlock/hooks/lib.sh` — similar JSON escaping

**Opportunity: Unified Hook Library (`interhooks`)**

Shared bash library sourced by all plugins:

```bash
# /root/projects/Interverse/infra/interhooks/lib.sh
source "$(dirname "${BASH_SOURCE[0]}")/json.sh"   # escape_for_json, parse_json
source "$(dirname "${BASH_SOURCE[0]}")/io.sh"      # safe_write, atomic_write
source "$(dirname "${BASH_SOURCE[0]}")/env.sh"     # require_env, optional_env
source "$(dirname "${BASH_SOURCE[0]}")/log.sh"     # log_info, log_warn, log_error → interlog
```

**Integration:**
- Each plugin's hook scripts source: `source "${INTERHOOKS_ROOT}/lib.sh"`
- `INTERHOOKS_ROOT` set by SessionStart hook (first plugin to load sets it)
- Reduces hook script duplication by ~40%

---

## 4. Missing External System Integrations

### 4.1 GitHub PR Integration (Close the Loop)

**Current gap:**
- `clavain` has `/clavain:claude-review` and `/clavain:codex-review` (GitHub Actions dispatch)
- Reviews run, post comments, but **no status check integration**
- PRs can merge before reviews complete
- No structured review state tracking

**Opportunity: GitHub Integration Service (`interhub`)**

GitHub App that bridges Interverse with GitHub PR workflow:

**Features:**
- **Status checks**: post "Review in progress" → "Review complete" on PR
- **Review comments**: structured feedback from flux-drive agents
- **PR labels**: auto-label based on review outcome (architecture-approved, safety-concern, etc.)
- **Webhook receiver**: trigger reviews on PR open/update
- **Review state tracking**: SQLite table of PR → review sessions
- **Diff context injection**: send PR diff to tldr-swinton for context, include in review

**API:**
```
POST /api/reviews → {
  "pr_url": "https://github.com/org/repo/pull/123",
  "agents": ["fd-architecture", "fd-safety"],
  "auto_comment": true
}
```

**Integration:**
- `/root/projects/Interverse/services/interhub/` (new Go service)
- GitHub App with PR read/write permissions
- Clavain skills trigger via `interhub_review` helper

---

### 4.2 CI Pipeline Integration (No Build Orchestration)

**Current gap:**
- Each module has independent `.git` and workflows
- No monorepo-aware testing (can't detect cross-module breakage)
- No dependency graph (can't determine "what needs retesting if X changes")

**Opportunity: Monorepo Build Orchestrator (`interbuild`)**

Dependency-aware build and test orchestrator:

**Features:**
- **Dependency graph**: parse `pyproject.toml`, `package.json`, `go.mod` for inter-module deps
- **Change detection**: `git diff` to find modified modules
- **Affected module resolution**: if `intersearch` changes, retest `interject` and `interflux`
- **Parallel builds**: run independent module tests in parallel
- **Caching**: skip tests if module unchanged and deps unchanged

**CLI:**
```bash
interbuild test --changed                 # Test only changed modules + dependents
interbuild test --all                     # Full monorepo test
interbuild graph                          # Visualize dependency graph
interbuild affected intersearch           # Show modules affected by intersearch change
```

**Integration:**
- CI workflow: `interbuild test --changed` on every commit
- Local development: `interbuild test` before pushing

---

### 4.3 Deployment State Tracking (No Rollback Visibility)

**Current gap:**
- `interpub` bumps versions and pushes to marketplace
- No tracking of "which version is live in production"
- No rollback tooling if a bad version is published

**Opportunity: Deployment Registry (`interdeploy`)**

Track version deployments and enable rollback:

**Features:**
- **Deployment log**: `(module, version, timestamp, environment, git_sha)`
- **Environment tracking**: dev, staging, production
- **Rollback command**: `interdeploy rollback <module> <env>` reverts to previous version
- **Version diff**: `interdeploy diff <module> <version1> <version2>` shows changelog

**Integration:**
- `interpub` calls `interdeploy deploy <module> <version> production` after push
- `/clavain:deploy-status` shows current versions across all modules

---

## 5. Missing Observability/Debugging Tooling

### 5.1 No Unified Plugin Registry

**Current gap:**
- Marketplace has `.claude-plugin/marketplace.json` (20 plugins)
- No runtime view of which plugins are **actually loaded** in a session
- No capability discovery ("which MCP tools are available right now?")

**Opportunity: Plugin Registry Service (`interplugins`)**

Runtime plugin introspection:

**Features:**
- **Loaded plugins**: list all plugins in current session with versions
- **Capability map**: enumerate all skills, commands, agents, MCP tools, hooks
- **Dependency resolution**: show plugin dependency graph (clavain → interphase → interline)
- **Conflict detection**: detect duplicate skills or commands across plugins

**API:**
```
GET /plugins → [
  {"name": "clavain", "version": "0.6.22", "skills": 23, "commands": 38, "hooks": 12},
  {"name": "interflux", "version": "0.2.1", "skills": 2, "agents": 12, "mcp_servers": 2},
  ...
]

GET /capabilities → {
  "skills": ["brainstorming", "flux-drive", ...],
  "commands": ["/clavain:setup", "/interflux:review", ...],
  "mcp_tools": ["tldr_code_find", "interkasten_sync", ...]
}
```

**Integration:**
- SessionStart hook reports to `interplugins`
- `/clavain:plugins` command shows loaded plugins and capabilities
- Debugging: "Why isn't skill X available?" → check `interplugins` registry

---

### 5.2 No MCP Server Lifecycle Monitoring

**Current gap:**
- 10+ MCP servers across plugins (interject, interkasten, interflux:qmd, interflux:exa, interlock, tldr-swinton, tuivision, interfluence, clavain:context7)
- No visibility into which servers are running, crashed, or hung
- No automatic restart on crash

**Opportunity: MCP Server Manager (`intermcp`)**

Process supervisor for MCP servers:

**Features:**
- **Auto-discovery**: parse `plugin.json` files for `mcpServers` definitions
- **Lifecycle management**: start/stop/restart servers on demand
- **Health monitoring**: periodic ping (call `list_tools` to verify server is responsive)
- **Crash recovery**: auto-restart on failure with exponential backoff
- **Resource tracking**: monitor memory/CPU per server
- **Logs aggregation**: capture stderr from all servers, send to `interlog`

**API:**
```
GET /mcp/servers → [
  {"name": "interject", "status": "running", "pid": 12345, "uptime": 3600},
  {"name": "qmd", "status": "crashed", "last_error": "Connection refused"},
  ...
]

POST /mcp/restart/interject → {"status": "restarted", "pid": 12346}
```

**Integration:**
- SessionStart hook registers all `mcpServers` with `intermcp`
- `/clavain:mcp-status` shows server health
- Auto-restart on crash improves reliability

---

### 5.3 No Performance Profiling

**Current gap:**
- No instrumentation for slow operations (MCP tool calls, hook execution, skill invocation)
- No way to detect performance regressions across versions

**Opportunity: Performance Tracer (`interperf`)**

Lightweight distributed tracing for Interverse operations:

**Features:**
- **Trace spans**: track operation start/end with parent/child relationships
- **Instrumentation points**: hook entry/exit, MCP tool calls, SQL queries
- **Flamegraph export**: visualize slow operations
- **Regression detection**: compare p95 latency across versions

**API:**
```bash
# Hook instrumentation
interperf_start "pre-edit-hook"
# ... do work ...
interperf_end "pre-edit-hook"
```

**Integration:**
- Add `interperf` calls to all hooks, MCP servers, and hot paths
- `/clavain:perf` shows recent slow operations
- CI runs perf benchmarks, alerts on regressions

---

## 6. Data Flow Integrity Issues

### 6.1 No Validation of Bead Metadata (interphase → clavain → interline)

**Current gap:**
- `bd` CLI is the source of truth for bead state
- Hooks write metadata (`intermute_agent_id`, phase) to bead descriptions
- No schema enforcement — typos or malformed JSON silently corrupt state

**Opportunity: Bead Metadata Schema**

Define JSON Schema for bead metadata fields:

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "type": "object",
  "properties": {
    "phase": {"enum": ["planning", "executing", "verifying", "complete"]},
    "intermute_agent_id": {"type": "string", "pattern": "^[a-z0-9-]+$"},
    "priority": {"type": "integer", "minimum": 0, "maximum": 4}
  }
}
```

**Integration:**
- `interphase` validates metadata before writing to bead
- `bd` enforces schema on metadata fields
- Invalid metadata triggers warning in SessionStart hook

---

### 6.2 No Signal Ordering Guarantees (interlock signals)

**Current gap:**
- Signal files are append-only JSONL
- No sequence numbers or vector clocks
- Consumers can't detect dropped signals or reordering

**Opportunity: Sequenced Signal Protocol**

Add monotonic sequence numbers to signals:

```json
{
  "version": "1.0.0",
  "seq": 42,          // Per-session monotonic counter
  "session_id": "...",
  "timestamp": "...",
  "layer": "coordination",
  "event": "reserve",
  "payload": {...}
}
```

**Features:**
- Consumers detect gaps (seq 41 → 43 means 42 was dropped)
- Enables replay and event sourcing
- Supports out-of-order delivery with reordering

---

## 7. Cross-Module Integration Anti-Patterns

### 7.1 Tight Coupling via File Paths (interphase, interline, clavain)

**Current pattern:**
- `interphase` hardcodes `/tmp/clavain-bead-${session_id}.json`
- `interline` hardcodes same path for reads
- `clavain` hardcodes `/tmp/clavain-dispatch-$$.json`

**Risk:**
- Path changes require synchronized updates across repos
- No negotiation if paths conflict
- `/tmp` cleanup policies vary by OS

**Better pattern:**
- Use `interband` library with centralized path logic
- Environment variable override: `INTERBAND_DIR="${XDG_RUNTIME_DIR:-/tmp}/interband"`
- Schema versioning allows independent evolution

---

### 7.2 Implicit Load Order Dependencies

**Current pattern:**
- `clavain` SessionStart hook must run before `interphase` (sets `CLAUDE_SESSION_ID`)
- `interlock` must run before `interline` (provides `INTERMUTE_AGENT_ID`)
- No way to declare or enforce ordering

**Opportunity: Hook Dependency Declaration**

Extend `hooks.json` with dependency metadata:

```json
{
  "hooks": {
    "SessionStart": [{
      "matcher": "startup|resume",
      "hooks": [{
        "type": "command",
        "command": "session-start.sh",
        "requires": ["clavain", "interphase"]  // Run after these plugins' hooks
      }]
    }]
  }
}
```

Claude Code core sorts hooks by dependency graph before execution.

---

## 8. Recommendations by Priority

### P0 (Immediate Impact, Low Risk)

1. **`interband` sideband protocol library** — Fixes fragile file contracts (interphase, clavain, interlock, interline)
2. **Environment contract documentation** — Prevents silent failures from missing/misnamed env vars
3. **`interbump` versioning audit** — Ensure all 22 plugins use it correctly (check for version drift)

### P1 (High Value, Medium Effort)

4. **`interstatus` health aggregator** — System-wide observability for 22-module ecosystem
5. **`intersqlite` shared library** — Reduces duplication across 5 SQLite-based modules
6. **`interhooks` bash library** — Consolidates duplicated hook utilities

### P2 (Strategic, Higher Effort)

7. **`interlog` structured logging** — Cross-module debugging and correlation
8. **`intermcp` MCP server manager** — Reliability for 10+ MCP servers
9. **`interbuild` monorepo orchestrator** — Dependency-aware testing, change detection

### P3 (Nice to Have)

10. **`interhub` GitHub integration** — Close the loop on PR review workflow
11. **`interqueue` job scheduler** — Coordinated background jobs (interject scans, drift checks)
12. **`interperf` performance tracer** — Regression detection and profiling

---

## 9. Concrete Next Steps

### Week 1: Foundation (Sideband Protocol)

1. Create `/root/projects/Interverse/infra/interband/`
2. Implement `lib.sh` (Bash) and `interband.go` (Go) with schema validation
3. Migrate `interphase`, `clavain`, `interlock`, `interline` to use `interband`
4. Add tests for schema versioning and atomic writes
5. Document contract in `docs/contracts/sideband-protocol.md`

### Week 2: Observability (Health + Logs)

1. Create `/root/projects/Interverse/services/interstatus/` (Go, ~500 LOC)
2. Implement health polling and registry management
3. Add `/clavain:health-status` command
4. Create `/root/projects/Interverse/services/interlog/` (Go, ~300 LOC)
5. Add `interlog` calls to top 5 busiest hooks (clavain, interphase, interlock)

### Week 3: Shared Libraries (SQLite + HTTP + Hooks)

1. Create `/root/projects/Interverse/infra/intersqlite/` (Go + Python bindings)
2. Migrate `intermute` to use `intersqlite` (validate no behavior change)
3. Create `/root/projects/Interverse/infra/interhttp/` (Go + Bash bindings)
4. Migrate `interlock` HTTP client to use `interhttp`
5. Create `/root/projects/Interverse/infra/interhooks/` (Bash)
6. Consolidate `lib.sh` from clavain, interphase, interlock

### Week 4: Monorepo Tooling (Build + Deploy)

1. Create `/root/projects/Interverse/services/interbuild/` (Go, ~800 LOC)
2. Implement dependency graph parsing (pyproject.toml, package.json, go.mod)
3. Add `interbuild test --changed` to CI
4. Create `/root/projects/Interverse/services/interdeploy/` (Go, ~400 LOC)
5. Add deployment tracking to `interpub` workflow

---

## 10. Success Metrics

**Coupling Reduction:**
- 50% fewer hardcoded file paths across plugins
- Schema validation on 100% of sideband messages
- Zero ad-hoc `curl` calls (all via `interhttp`)

**Reliability:**
- 95% health check pass rate across all modules
- MCP server crash recovery time < 5s
- Zero silent hook failures (all errors logged to `interlog`)

**Developer Experience:**
- <5 min to onboard a new plugin to shared infrastructure
- Dependency graph visualization shows all module relationships
- Performance regressions caught in CI before merge

**Observability:**
- Single dashboard shows health of all 22 plugins + 1 service
- Logs from all modules searchable by session ID
- MCP server resource usage visible in real-time

---

## Appendix A: Technology Stack Summary

| Module | Language | Key Dependencies | Database | External Services |
|--------|----------|------------------|----------|-------------------|
| **clavain** | Bash | jq, gh, oracle | None | Context7 (MCP) |
| **intermute** | Go 1.24 | modernc.org/sqlite, nhooyr/websocket | SQLite | None |
| **interlock** | Go + Bash | mark3labs/mcp-go | None (via intermute) | intermute HTTP |
| **interkasten** | TypeScript | Drizzle ORM, Notion SDK | SQLite | Notion API |
| **interject** | Python | sentence-transformers, FastMCP | SQLite | Exa, arXiv, HN |
| **interflux** | Bash | jq | None | qmd (MCP), Exa (MCP) |
| **tldr-swinton** | Rust + Python | tree-sitter, ast-grep | SQLite | None |
| **tuivision** | TypeScript | xterm.js, node-pty | None | None |
| **tool-time** | Python | Cloudflare Workers | SQLite | tool-time.org API |
| **interfluence** | TypeScript | FastMCP | None | None |
| **intersearch** | Python | sentence-transformers, aiohttp | None | Exa API |

**Duplication targets:**
- **SQLite**: 6 modules (intermute, interkasten, interject, tldr-swinton, tool-time, interspect)
- **HTTP clients**: 4 modules (interlock, tool-time, clavain hooks, bead-agent-bind)
- **Bash JSON escaping**: 3 modules (clavain, interphase, interlock)
- **Signal/event emission**: 3 modules (interlock, lib-signals.sh, lib-interspect.sh)

---

## Appendix B: File Path Audit

**Hardcoded paths requiring centralization:**

```
/tmp/clavain-bead-${session_id}.json           → interphase, interline
/tmp/clavain-dispatch-$$.json                   → clavain, interline
/var/run/intermute/signals/*.jsonl              → interlock, interline
~/.config/clavain/intermute-joined              → interlock hooks (join flag)
~/.claude/interline.json                        → interline config
~/.interkasten/config.yaml                      → interkasten MCP server
~/.claude/plugins/cache/                        → session-start.sh cleanup
.beads/                                         → clavain, interphase (detection)
.interwatch/                                    → interwatch state
.tldrs/                                         → tldr-swinton state
.clavain/interspect/                            → interspect evidence DB
```

**Recommendation:** Move all to `${XDG_RUNTIME_DIR:-~/.local/run}/interverse/` with namespaced subdirs.

---

## Appendix C: Cross-Plugin Dependency Graph

```
clavain (hub)
├── interphase (phase tracking, gates, discovery)
├── interline (statusline, reads from clavain + interphase + interlock)
├── interflux (review agents, research, domain detection)
├── interpath (artifact generation)
├── interwatch (drift detection)
├── interlock (coordination, file reservations)
├── intercraft (agent-native architecture)
├── interdev (MCP CLI tooling)
├── interform (design patterns)
├── internext (prioritization)
└── interslack (Slack integration)

interject (MCP) ← depends on intersearch (embeddings + Exa)
interflux (MCP) ← depends on qmd (MCP), Exa (MCP)
interlock (MCP) ← depends on intermute (service)
interkasten (MCP) ← depends on Notion API

interpub ← used by all plugins (version bumping)
interdoc ← generates AGENTS.md for all projects
tool-time ← analyzes all plugins (ecosystem observatory)
tldr-swinton ← standalone code context (no deps)
tuivision ← standalone TUI testing (no deps)
interfluence ← standalone voice profiling (no deps)
marketplace ← registry for all 20 plugins
```

**Key insight:** Most plugins are leaf nodes depending on clavain. Only 4 have deep dependency chains (interject → intersearch, interlock → intermute, interflux → qmd/Exa, interkasten → Notion).

---

## Appendix D: Missing Tests by Module

| Module | Has Tests | Coverage | Gaps |
|--------|-----------|----------|------|
| intermute | ✅ | High (handlers, storage, domain) | WebSocket hub |
| interlock | ✅ | High (95 structural tests) | Hook integration |
| interkasten | ✅ | Medium (79 tests) | Error recovery |
| interject | ❌ | None | All code paths |
| interflux | ✅ | Low (domain detection only) | Agent routing |
| tldr-swinton | ❌ | None | All MCP tools |
| tuivision | ❌ | None | Session management |
| tool-time | ✅ | Medium (summarize, upload) | Dashboard |
| clavain | ❌ | None | Hook execution |
| interphase | ✅ | Low (phase tracking) | Gate validation |

**Recommendation:** Prioritize testing for `interject`, `tldr-swinton`, `tuivision` (all have complex MCP servers but zero tests).

---

**End of Report**
