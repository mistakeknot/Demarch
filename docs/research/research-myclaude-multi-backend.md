# Research: myclaude (cexll/myclaude) Multi-Backend Orchestration System

**Date:** 2026-02-15
**Repo:** [github.com/cexll/myclaude](https://github.com/cexll/myclaude) (2.3k stars, 262 forks, AGPL-3.0)
**Last pushed:** 2026-02-14
**Source evidence:** Go source code from `codeagent-wrapper/internal/`, skill SKILL.md files, config.json, hooks/

---

## 1. Architecture Overview

myclaude is a **Claude Code plugin** that transforms Claude Code into an orchestrator for multiple AI coding backends. It installs into `~/.claude/` and provides skills, hooks, agents, and a Go CLI wrapper binary (`codeagent-wrapper`) that abstracts backend differences.

### Layered Architecture

```
┌─────────────────────────────────────────────────────┐
│  Claude Code (the "brain" / planner)                │
│  - Reads SKILL.md instructions                      │
│  - Decides which agents to invoke                   │
│  - Calls codeagent-wrapper via Bash tool            │
├─────────────────────────────────────────────────────┤
│  Skills Layer (SKILL.md files)                      │
│  - /do   → 5-phase feature development              │
│  - /omo  → signal-driven multi-agent routing        │
│  - /codex, /gemini → direct backend delegation      │
├─────────────────────────────────────────────────────┤
│  codeagent-wrapper (Go CLI binary)                  │
│  - Backend abstraction (codex/claude/gemini/opencode)│
│  - Parallel execution with DAG scheduling           │
│  - Skill auto-detection and injection               │
│  - Session management and resume                    │
├─────────────────────────────────────────────────────┤
│  Backend CLIs (must be in PATH)                     │
│  - codex (OpenAI Codex CLI)                         │
│  - claude (Claude Code CLI, invoked headless)       │
│  - gemini (Google Gemini CLI)                       │
│  - opencode (OpenCode CLI, e.g., Grok)              │
└─────────────────────────────────────────────────────┘
```

### Key Design Principle: CLI Wrapping, Not API Embedding

The system does **not** embed model APIs directly. Instead, it wraps existing CLI tools:
- `codex e <prompt>` with `--json` output
- `claude -p <prompt> --output-format stream-json`
- `gemini -o stream-json <prompt>`
- `opencode run --format json <prompt>`

Each backend implementation is a Go struct that implements a `Backend` interface:

```go
type Backend interface {
    Name() string
    BuildArgs(cfg *config.Config, targetArg string) []string
    Command() string
    Env(baseURL, apiKey string) map[string]string
}
```

The registry is a simple map:
```go
var registry = map[string]Backend{
    "codex":    CodexBackend{},
    "claude":   ClaudeBackend{},
    "gemini":   GeminiBackend{},
    "opencode": OpencodeBackend{},
}
```

Backend selection defaults to `"codex"` if not specified. The `Select()` function does case-insensitive lookup.

---

## 2. Planner/Executor Split

**Yes, Claude Code is always the planner.** The architecture enforces a clear separation:

### Claude Code as Planner
- Reads the SKILL.md instructions (which are essentially prompting strategies for Claude Code itself)
- Analyzes the user's request
- Decides which agents to invoke and in what order
- Constructs prompts for each agent
- Interprets results and decides next steps

### codeagent-wrapper as Executor
- Receives a prompt string (via stdin or CLI arg)
- Selects the backend based on configuration
- Spawns the backend CLI process
- Parses JSON stream output
- Returns `agent_message` and `session_id` to Claude Code

### The `/do` Skill: 5-Phase Pipeline

The flagship workflow demonstrates the split clearly:

| Phase | Role | Agent | Backend | Mode |
|-------|------|-------|---------|------|
| 1. Understand | Read-only analysis | `code-explorer` | opencode | Parallel (4 agents) |
| 2. Clarify | Resolve ambiguities | Claude Code itself | N/A | Conditional (skip if score >= 8/10) |
| 3. Design | Architecture blueprint | `code-architect` | claude | Read-only |
| 4. Implement | Code changes + review | `develop` + `code-reviewer` | codex + claude | Parallel |
| 5. Complete | Document outcomes | Claude Code itself | N/A | Final |

Phase 1 runs **four parallel agents** to map the codebase. Phase 4 delegates all code edits to Codex via `codeagent-wrapper`, then runs Claude as a reviewer. Claude Code never writes code directly; it always delegates.

### The `/omo` Skill: Signal-Driven Routing

OmO is more dynamic than `/do`. It uses a **signal-based routing** approach:

1. **Code location unclear?** -> invoke `explore` agent (opencode/Grok)
2. **External API/library questions?** -> invoke `librarian` agent (claude-sonnet)
3. **High-risk changes?** -> invoke `oracle` agent (claude-opus)
4. **Implementation needed?** -> invoke `develop` (codex/GPT-5.2), `frontend-ui-ux-engineer` (gemini), or `document-writer` (gemini-flash)

The key principle: *"This skill is routing-first, not a mandatory explore -> oracle -> develop conveyor belt."* Agents are only invoked when their signal triggers.

---

## 3. Token Efficiency

### Direct Token Savings

myclaude achieves token efficiency through several mechanisms:

#### a) Backend Cost Arbitrage
The most significant token efficiency is **routing tasks to cheaper backends**. The default agent-to-backend mapping shows intentional cost tiering:

| Agent | Backend | Model | Implied Cost Tier |
|-------|---------|-------|-------------------|
| `oracle` (high-stakes analysis) | claude | claude-opus-4-5 | Expensive |
| `code-architect` | claude | (default) | Medium-high |
| `code-reviewer` | claude | (default) | Medium-high |
| `librarian` | claude | claude-sonnet-4-5 | Medium |
| `develop` (bulk code gen) | codex | gpt-4.1 / gpt-5.2 | Cheaper for code |
| `explore` (codebase scanning) | opencode | grok-code | Cheapest |
| `frontend-ui-ux-engineer` | gemini | gemini-3-pro | Varies |
| `document-writer` | gemini | gemini-3-flash | Cheapest |

This means high-volume code generation goes to Codex (OpenAI, optimized for code), while expensive reasoning (risk assessment, architecture) goes to Claude Opus. Documentation and exploration use the cheapest available backends.

#### b) Skill Injection Budget

The `ResolveSkillContent()` function enforces a **16,000-character budget** (~4K tokens) for injected skill context:

```go
const defaultSkillBudget = 16000 // chars, ~4K tokens
```

Skills are truncated to fit within this budget. This prevents context bloat when multiple skills are detected. Skills are also auto-detected from project tech stack (Go, Rust, Python, Node.js, Vue) and only injected if installed.

#### c) Conditional Phase Skipping

The `/do` skill skips Phase 2 (clarification) if the requirement completeness score is >= 8/10. The `/omo` skill explicitly instructs: "skip explore when exact file paths/line numbers already exist" and "skip oracle for low-risk, localized fixes."

#### d) Summary-Mode Output

The `GenerateFinalOutputWithMode()` function supports a `summaryOnly` mode that produces compressed execution reports. Instead of returning full agent messages, it extracts structured fields:
- `KeyOutput` (brief summary)
- `FilesChanged` (list)
- `Coverage` (percentage)
- `TestsPassed`/`TestsFailed`

This reduces the tokens Claude Code needs to process from backend results.

#### e) YAML Frontmatter Stripping

Skills have their YAML frontmatter stripped before injection, saving tokens on metadata that doesn't help the model.

### What It Does NOT Do

- **No prompt compression**: Prompts are passed through as-is (or via stdin for large ones). There's no summarization or compression layer.
- **No shared embedding store**: Each backend invocation is independent. There's no persistent vector store or RAG layer between agents.
- **No conversation history sharing**: Backend sessions are isolated. The only context sharing is through Claude Code's orchestration (passing outputs from prior agents as input to subsequent ones).

---

## 4. Orchestration Glue

### Primary Mechanism: File + Process

The orchestration is **process-based, not API-based, not MCP-based**:

1. **Claude Code** (the planner) runs inside a Claude Code session
2. It calls `codeagent-wrapper` via the **Bash tool** (i.e., `exec`)
3. `codeagent-wrapper` spawns the backend CLI as a **child process**
4. Communication happens via **stdin/stdout pipes** with JSON stream parsing
5. Results flow back to Claude Code via Bash tool output

### Detailed Flow

```
Claude Code
  │
  ├── [Bash tool] codeagent-wrapper --backend codex --parallel <<TASKS
  │     │
  │     ├── [subprocess] codex e --json <prompt1>
  │     │     └── stdout: JSON stream → parsed → agent_message
  │     │
  │     ├── [subprocess] gemini -o stream-json <prompt2>
  │     │     └── stdout: JSON stream → parsed → agent_message
  │     │
  │     └── [report] Combined task results → stdout
  │
  └── [reads stdout] Interprets results, decides next step
```

### Parallel Execution via DAG

For parallel tasks, the system uses a text-based config format with `---TASK---` and `---CONTENT---` delimiters:

```
---TASK---
id: analyze-backend
backend: codex
workdir: ./src
---CONTENT---
Analyze the backend architecture...

---TASK---
id: analyze-frontend
backend: gemini
dependencies:
---CONTENT---
Analyze the frontend components...

---TASK---
id: integrate
backend: claude
dependencies: analyze-backend, analyze-frontend
---CONTENT---
Based on prior analysis, design the integration...
```

The executor performs **topological sorting** of task dependencies, groups them into layers, and runs each layer concurrently with a configurable worker limit (`CODEAGENT_MAX_PARALLEL_WORKERS`).

### Context Pack Pattern (OmO)

Each agent invocation includes a structured context pack:
- Original user request (preserved throughout)
- Outputs from prior stages
- Known constraints and acceptance criteria

This is constructed by Claude Code in the prompt it passes to `codeagent-wrapper`. There is no automatic context forwarding; Claude Code must explicitly include prior outputs.

### Worktree Isolation

The system supports **git worktree isolation** for implementation tasks:
- `--worktree` flag creates an isolated git worktree per task
- `DO_WORKTREE_DIR` environment variable reuses an existing worktree across phases
- This prevents parallel agents from conflicting on the same working directory

### Recursion Prevention

When invoking Claude as a backend, the wrapper explicitly disables all settings sources:
```go
args = append(args, "--setting-sources", "")
```
This prevents the sub-Claude from loading the myclaude SKILL.md files and recursively invoking codeagent-wrapper.

### Session Resume

All backends support session resumption via session IDs:
- Codex: `codex e --json resume <session_id> <prompt>`
- Claude: `claude -p -r <session_id> <prompt>`
- Gemini: `gemini -r <session_id> <prompt>`

This enables multi-turn interactions where Claude Code can resume a backend session for follow-up work.

---

## 5. Configuration

### Three-Layer Configuration

#### Layer 1: `~/.codeagent/models.json` (Agent-to-Backend Mapping)

This is the primary configuration file. It maps named agents to backends, models, and prompt files:

```json
{
  "default_backend": "codex",
  "default_model": "gpt-4.1",
  "backends": {
    "codex": { "api_key": "..." },
    "claude": { "api_key": "..." },
    "gemini": { "base_url": "...", "api_key": "..." }
  },
  "agents": {
    "develop": {
      "backend": "codex",
      "model": "gpt-4.1",
      "prompt_file": "~/.codeagent/prompts/develop.md",
      "reasoning": "high",
      "yolo": true,
      "allowed_tools": ["Read", "Write", "Bash"],
      "disallowed_tools": []
    },
    "oracle": {
      "backend": "claude",
      "model": "claude-opus-4-5-20251101"
    },
    "explore": {
      "backend": "opencode",
      "model": "opencode/grok-code"
    }
  }
}
```

Resolution chain: per-agent config -> default_backend/default_model -> hardcoded "codex".

#### Layer 2: `config.json` (Module Enable/Disable)

Controls which skill modules are active:

```json
{
  "modules": {
    "do": { "enabled": true },
    "omo": { "enabled": false },
    "bmad": { "enabled": false },
    "essentials": { "enabled": false }
  }
}
```

Each module declares its own agent mappings (used during installation to populate `models.json`).

#### Layer 3: Environment Variables

Fine-grained overrides via `CODEAGENT_*` env vars (processed by Viper):
- `CODEAGENT_BACKEND` — override default backend
- `CODEAGENT_SKIP_PERMISSIONS` — skip Claude Code permission prompts (default: true)
- `CODEX_BYPASS_SANDBOX` — bypass Codex sandbox (default: true)
- `CODEAGENT_MAX_PARALLEL_WORKERS` — parallel execution limit
- `DO_WORKTREE_DIR` — reuse worktree across phases
- `GEMINI_MODEL`, `GEMINI_API_KEY` — Gemini configuration (from `~/.gemini/.env`)
- `ANTHROPIC_API_KEY`, `ANTHROPIC_BASE_URL` — Claude API configuration

#### Layer 4: Dynamic Agents

Agent prompt files placed in `~/.codeagent/agents/<name>.md` are automatically discoverable without `models.json` entries. They use `default_backend` and `default_model` from the config.

### Skill Auto-Detection

The system auto-detects project tech stack and injects relevant skills:

| Project Fingerprint | Injected Skill |
|---------------------|----------------|
| `go.mod` / `go.sum` | `golang-base-practices` |
| `Cargo.toml` | `rust-best-practices` |
| `pyproject.toml` / `setup.py` | `python-best-practices` |
| `package.json` | `vercel-react-best-practices` + `frontend-design` |
| `vue.config.js` / `vite.config.ts` | `vue-web-app` |

Skills are appended to the task prompt as `# Domain Best Practices` sections, within the 16K char budget.

---

## 6. Hooks

myclaude installs two Claude Code hooks:

1. **`pre-bash.py`** (PreToolUse:Bash) — Blocks destructive commands (`rm -rf /`, `dd if=`, fork bombs, etc.)
2. **`inject-spec.py`** (PreToolUse:Bash) — **DEPRECATED** (now a no-op). Skill injection moved into codeagent-wrapper itself.
3. **`log-prompt.py`** (UserPromptSubmit) — Logs user prompts for analytics.

The hooks are minimal; orchestration logic lives in the skills and codeagent-wrapper, not in hooks.

---

## 7. Comparison with Interverse Architecture

| Dimension | myclaude | Interverse |
|-----------|----------|------------|
| **Orchestration** | Claude Code as planner, CLI wrapper as executor | Clavain as hub, plugins as modules |
| **Backend diversity** | 4 backends (codex, claude, gemini, opencode) | Primarily Claude Code + Oracle (GPT-5.2 Pro for review) |
| **Communication** | Process spawning + JSON stream parsing | MCP servers, hooks, Intermute coordination service |
| **Parallel execution** | Built into codeagent-wrapper (DAG scheduler) | Clavain dispatch to multiple agents |
| **File coordination** | Git worktree isolation | Interlock reservation system |
| **Configuration** | models.json + env vars | Plugin manifests + plugin.json |
| **Token efficiency** | Backend cost arbitrage + skill budget caps | Compact skill mode + gen scripts |
| **Recursion prevention** | `--setting-sources ""` | N/A (different architecture) |

---

## 8. Key Takeaways

### What myclaude Does Well

1. **Clean abstraction layer**: The Go Backend interface is minimal and easy to extend to new backends.
2. **Cost-aware routing**: Mapping expensive reasoning to Claude Opus and bulk code gen to Codex/GPT is a pragmatic token savings strategy.
3. **Parallel DAG execution**: Topological sorting with dependency tracking and configurable concurrency limits is production-quality.
4. **Recursion prevention**: Disabling setting sources when invoking Claude as a backend is a simple but essential safety measure.
5. **Session resume**: Maintaining backend session IDs enables multi-turn interactions without re-sending full context.

### Limitations / Gaps

1. **No shared context store**: Each backend invocation starts fresh. Context sharing is manual (Claude Code must include prior outputs in prompts).
2. **No prompt compression**: Large prompts are passed through as-is. Only skill injection has a budget cap.
3. **CLI dependency**: Requires all backend CLIs installed in PATH. No fallback to API-only mode.
4. **Single-machine**: No distributed execution; all backends run as local subprocesses.
5. **No MCP integration**: Despite MCP being available in Claude Code, myclaude uses plain process spawning.

### Patterns Worth Adopting

1. **Backend cost tiering** — Routing bulk code generation to cheaper backends is a significant cost saver.
2. **Skill budget cap** — The 16K character limit for injected skills prevents context bloat.
3. **DAG-based parallel execution** — Topological sorting with layer-based concurrent execution is a clean pattern.
4. **Summary-mode output** — Extracting structured fields from verbose agent output reduces planner token costs.
5. **Conditional phase skipping** — Score-based phase gating avoids wasting tokens on unnecessary clarification.

---

## Sources

- [cexll/myclaude GitHub Repository](https://github.com/cexll/myclaude)
- [README_CN.md](https://github.com/cexll/myclaude/blob/master/README_CN.md)
- [codeagent-wrapper](https://github.com/cexll/myclaude/tree/master/codeagent-wrapper)
- [skills/codex](https://github.com/cexll/myclaude/tree/master/skills/codex)
- [skills/gemini](https://github.com/cexll/myclaude/tree/master/skills/gemini)
- [dev-workflow README](https://github.com/cexll/myclaude/blob/master/dev-workflow/README.md)
- [CHANGELOG.md](https://github.com/cexll/myclaude/blob/master/CHANGELOG.md)
- [Releases](https://github.com/cexll/myclaude/releases)
