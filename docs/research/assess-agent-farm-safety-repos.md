# Assessment: Agent Farm Safety Repos

**Date:** 2026-02-28
**Bead IDs:** iv-bu3vx (claude_code_agent_farm), iv-4gdfl (destructive_command_guard)
**Task:** Evaluate integration/inspiration value for Demarch

---

## claude_code_agent_farm (iv-bu3vx)

**What it is:** A Python orchestration framework that spawns and manages 20-50 parallel Claude Code (`cc`) agents in tmux panes to perform systematic codebase improvements (bug fixing, best-practices application, or coordinated multi-agent development).

**Language/Stack:** Python 3.13+, tmux, typer, rich; no compiled components. Single 2,990-line orchestrator script (`claude_code_agent_farm.py`) plus config JSONs and prompt `.txt` files.

**Quality:** medium-high

The code is well-structured, heavily commented, and defensively written:
- Exponential backoff on tmux retries
- Atomic file operations (fsync + rename) for the problems file
- File locking (`O_CREAT | O_EXCL`) to serialize Claude Code launches and prevent settings corruption
- Heartbeat files per agent (`/.heartbeats/agent00.heartbeat`) for stall detection
- Adaptive idle timeout calculated from rolling median of observed cycle times
- Settings backup/restore (tar.gz, size-bounded rotation) before and after runs
- Double Ctrl-C force-kill within a 3-second threshold
- Graceful shutdown with SIGINT/SIGTERM handlers
- Rich live dashboard with per-agent: status, cycle count, context %, runtime, heartbeat age, error count

There are no automated tests (only manual verification via the doctor command) and the design uses shell-scraping of tmux pane output to detect Claude Code state, which is inherently brittle. The prompts directory contains 40+ prompt templates covering essentially every major tech stack.

**Relevance to Demarch:** Directly parallels Clavain's subagent dispatch — the agent farm is the external standalone version of what Clavain's sprint workflows do inside Claude Code, and its coordination layer solves the same multi-agent conflict problem that interlock addresses.

---

### Integration opportunities

- **File-locking pattern for Claude Code launch serialization.** The `_acquire_claude_lock` / `_release_claude_lock` pattern (atomic `O_CREAT | O_EXCL` on `~/.claude/.agent_farm_launch.lock`) directly solves a real problem Clavain will face when dispatching multiple subagents: concurrent settings corruption. Port this into Clavain's dispatch infrastructure.

- **Heartbeat-based stall detection.** Per-agent heartbeat files updated every time an agent sends output to tmux, checked by the orchestrator against a configurable staleness threshold (default 120s). Clavain's `dispatch.sh` currently has no equivalent; adding heartbeat files to subagent sessions would allow the orchestrator to detect and restart hung agents without polling process lists.

- **Adaptive idle timeout.** Rolling median of observed agent cycle times, then `timeout = clamp(3 * median, 30, 600)`. This prevents both premature restarts (when agents are doing real work) and indefinite hangs. Directly adoptable in interlock or Clavain's monitor.

- **Settings backup/restore with size-bounded rotation.** The farm backs up `~/.claude/settings.json` and `~/.claude/statsig/` as a tar.gz before each run and rotates to keep the last 10 backups under 200 MB total. Useful for intercom's container isolation boundary — restore settings on container teardown.

- **Problems file as coordination primitive.** The approach of generating a single shared `combined_typechecker_and_linter_problems.txt` from linters/type-checkers and having agents claim random chunks (with seed-based randomization per agent instance) is a lightweight work-queue that requires no coordination server. This is simpler than interlock's full JSON registry for certain workloads.

- **Prompt variable substitution.** The `{chunk_size}` substitution pattern (expandable to any config key) in prompt templates is a minimal but useful templating layer for Clavain's prompt dispatch.

- **Settings corruption auto-recovery.** When an agent's tmux pane shows a settings error, the orchestrator kills that agent's `cc` instance, restores from backup, and relaunches — all without touching other agents. This pattern is directly relevant to Clavain's long-running sprint sessions.

- **Tmux pane title context indicators.** The `_update_pane_title` method encodes agent status emoji and context percentage in the tmux pane title (`[00] Working Context: 45%`). Clavain sessions could adopt this to give the operator a glance-view of all concurrent subagents.

---

### Inspiration opportunities

- **Cooperating agents via prompt-only coordination.** The most architecturally interesting insight: the full multi-agent coordination protocol (lock files, work registry, completed-work log, planned-work queue in `/coordination/`) is entirely driven by the prompt. No code enforces it. The LLM reads and writes JSON files using normal file tools. This demonstrates that interlock's coordination layer could be implemented as a pure-prompt protocol without any compiled MCP server, at least for simpler workflows.

- **Three workflow archetypes: bug-fix, best-practices, cooperating.** The clean separation into these three modes (each with its own prompt and config) maps well to how Clavain could organize sprint types. The best-practices mode (track implementation progress in a markdown file, compute completion %) is particularly applicable to Demarch's own codebase improvement runs.

- **Context percentage detection via tmux scraping.** Four regex patterns against `Context left until auto-compact: N%` and variants. When context drops below threshold (default 20%), the orchestrator sends `/clear` rather than restarting — a lighter-weight recovery. Clavain's long-running sessions should implement this distinction (context-clear vs full restart).

- **Active probe for shell readiness.** Rather than passive pattern matching on prompt appearance (fragile across shell themes), the orchestrator sends `echo AGENT_FARM_READY_<random>` and waits for the echo in captured output. Robust and shell-agnostic. Clavain's subagent launch should adopt this.

- **One-key broadcast of `/clear` to all agents.** `tmux bind-key C-r` in the controller window to send `/clear` to every agent pane simultaneously. Simple but operationally valuable for Clavain's monitor window.

- **Dynamic chunk sizing.** `chunk_size = clamp(total_lines // num_agents // 2, 10, configured_max)` as problems are fixed. This automatically gives agents smaller chunks as the problem set shrinks — worth applying wherever Clavain distributes work across agents.

- **HTML run report generation.** The orchestrator emits a post-run HTML report with stats, commit diffs, and agent timelines. Intercom or Autarch could expose similar run reports via its web UI.

---

**Verdict:** port-partially

**Rationale:** The lock, heartbeat, adaptive-timeout, and settings-recovery patterns are immediately portable to Clavain's dispatch infrastructure, and the cooperating-agents protocol demonstrates that interlock's coordination layer can be expressed as a pure-prompt protocol — which is worth validating before building compiled infrastructure.

---

## destructive_command_guard (iv-4gdfl)

**What it is:** A high-performance Rust binary (`dcg`) that installs as a `PreToolUse` hook for Claude Code (and Gemini CLI, Copilot CLI, OpenCode, Aider) and blocks destructive shell commands before they execute.

**Language/Stack:** Rust (stable toolchain), async MCP server mode via `rust_mcp_sdk`, SIMD-accelerated pattern matching via `memchr` + `aho-corasick` + `regex`. Binary install via `curl | bash`. ~68k lines of Rust source across 30 source files.

**Quality:** high

- 70 test files, fuzz targets, Codecov CI integration, 40+ architecture/design docs, ADRs, pattern audit logs
- Layered config: system → user → project → env (TOML, with presence-aware merging to distinguish "explicitly false" from "unset")
- 49+ modular security packs (organized as `category.subcategory`, e.g. `core.git`, `database.postgresql`), each independently enable/disableable
- Three-tier heredoc/inline-script scanning pipeline: Tier 1 trigger (RegexSet, <100μs), Tier 2 extraction (<1ms), Tier 3 AST-grep match (<5ms), all fail-open
- Context-aware evaluation: classifies each command span as Executed / Argument / InlineCode / Data / HeredocBody / Comment — only checks destructive patterns in Executed/InlineCode/HeredocBody spans. This eliminates false positives like `git commit -m "Fix rm -rf detection"`
- Confidence scoring for ambiguous matches
- Per-agent trust levels (`agents.claude-code.trust_level = "high"`)
- Interactive bypass with TTY detection (auto-disables if stdin is not a TTY, i.e. agent-invoked), random verification code (prevents automated bypass)
- `allow-once` flow: blocked commands generate a short code that the human can type to allow a single execution without modifying config
- MCP server mode (`dcg mcp-server`) exposing `check_command`, `scan_file`, `explain_pattern` tools
- Git branch-aware strictness: stricter on protected branches
- JSON robot-mode output (`--robot` / `DCG_ROBOT=1`), structured exit codes (0=allow, 1=deny, 2=warn, 3=config, 4=parse, 5=io)
- CI scan mode with SARIF output for pre-commit and GitHub Actions integration

**Relevance to Demarch:** Demarch's current agent safety relies on container isolation (intercom) and Claude Code permission prompts. dcg is a complementary pre-execution layer that blocks at the tool invocation level — directly relevant to Clavain's `PreToolUse` hook infrastructure and to any agent farm that uses `--dangerously-skip-permissions`.

---

### Integration opportunities

- **Direct installation as a Clavain hook.** dcg is already designed for the `PreToolUse` Claude Code hook slot. It can be installed alongside Clavain's existing hooks via `hooks.json` without code changes. This is the highest-leverage path: get the safety layer in place immediately.

- **Pack-based configuration via `.dcg.toml`.** Clavain and intercom can ship project-local `.dcg.toml` files (committed to subproject roots) that enable the relevant packs. For example, intercom containers running database workloads should enable `database.postgresql`, `database.redis`; Autarch's agent sessions should enable `core.git`, `core.filesystem`, `platform.github`, `infrastructure.terraform`.

- **MCP server mode for interlock.** `dcg mcp-server` exposes `check_command` as an MCP tool. Interlock's orchestrator could call this tool before dispatching any Bash command to a subagent — a pre-dispatch safety check that happens at the coordination layer rather than at the agent boundary.

- **Custom packs for Demarch-specific tooling.** dcg supports YAML-defined custom packs in `.dcg/packs/*.yaml`. Demarch could define packs for its own dangerous CLI commands: `bd close --all`, `mutagen sync pause`, `egcleanup`, `ic publish --force`, etc.

- **CI scan mode for pre-commit.** The scan mode (`dcg scan --format sarif`) can be integrated into Demarch's CI pipelines to catch committed scripts containing destructive commands before they reach production.

- **Agent detection for trust tiering.** dcg detects Claude Code via `CLAUDE_CODE=1` or `CLAUDE_SESSION_ID`. Demarch's subagent spawner could set `CLAUDE_CODE=1` and then configure `agents.claude-code.trust_level = "high"` (or `"low"` for untrusted prompts) rather than blocking everything equally.

---

### Inspiration opportunities

- **Three-tier evaluation pipeline.** The `evaluator.rs` pipeline (allow-overrides → block-overrides → heredoc scan → quick-reject → context sanitize → normalize → pack registry → safe patterns → destructive patterns) is the most sophisticated implementation of pre-execution analysis seen in this space. Clavain's `PreToolUse` hooks could adopt this tiered pattern: cheap checks first, expensive checks only when needed.

- **Context span classification.** Classifying command spans as Executed / Argument / InlineCode / Data eliminates a major class of false positives without requiring full shell parsing. Any pattern-matching hook in Clavain's ecosystem should consider this before regex-matching the entire command string.

- **Whitelist-first architecture.** Safe patterns are compiled and checked before destructive patterns, in a single pass. This is the correct default for any hook that might accidentally block legitimate operations. Clavain's hooks should audit whether they follow this ordering.

- **Interactive bypass with TTY detection.** The `interactive.rs` module disables the bypass dialog when stdin is not a TTY (detecting agent-invoked context automatically), and when active, requires typing a random verification code within a timeout. This prevents automated bypass while keeping the tool usable for human operators. Valuable pattern for any Clavain hook that currently shows a confirmation prompt.

- **Allow-once with short codes.** Rather than permanently adding commands to an allowlist (which requires config file writes), dcg can issue a short ephemeral code for a single-use bypass. This keeps the allowlist clean while supporting one-off exceptions. Applicable to Clavain's permission prompt system.

- **Modular pack system design.** The two-level hierarchy (category → sub-pack), where enabling `kubernetes` enables all `kubernetes.*` sub-packs but individual sub-packs can still be disabled, is a clean model for Clavain's configurable safety policies across different project types.

- **Fail-open philosophy.** dcg is explicit that unrecognized commands are always allowed, parse errors always allow, timeouts always allow. Safety is achieved by never blocking legitimate workflows — only known-dangerous patterns are blocked. This is the correct default for an agent hook and should be documented as a principle in Clavain's hook authoring guide.

- **Normalized pattern matching.** `normalize.rs` strips absolute paths from binary names (`/usr/bin/git` → `git`) before matching. Without this, patterns like `r"git\s+reset"` miss commands invoked via full path. Any Clavain hook doing command classification should apply this normalization.

- **Graduated response by severity.** Critical (always deny) / High (deny, allowlistable) / Medium (warn, continue) / Low (log only). This avoids the all-or-nothing binary of block vs allow and maps well to how Clavain could tier its own enforcement.

- **Per-pack keyword quick-reject.** Before evaluating any pack's patterns, dcg checks whether the command contains any keyword associated with that pack (e.g. `git`, `rm`, `docker`). Packs with no matching keywords are skipped entirely. This is the key performance optimization that keeps total latency under 1ms on non-matching commands.

---

**Verdict:** adopt

**Rationale:** dcg is production-ready, low-latency, and directly installable into Clavain's existing hook infrastructure today without any porting effort — the integration path is simply adding it to `hooks.json` and committing a project-local `.dcg.toml` — while its design patterns (evaluation pipeline tiering, context span classification, whitelist-first, fail-open, per-agent trust levels) are the highest-quality implementations of pre-execution safety analysis available in the open-source Claude Code ecosystem.

---

## Comparative Summary

| Dimension | claude_code_agent_farm | destructive_command_guard |
|---|---|---|
| Language | Python | Rust |
| Size | 2,990 lines | ~68k lines |
| Tests | None (doctor check only) | 70 test files + fuzz |
| Docs | README + prompts | 40+ design docs + ADRs |
| Install effort | High (Python venv, tmux setup) | Low (curl-install binary) |
| Integration path | Port patterns to Clavain dispatch | Install hook + config file |
| Primary value | Orchestration patterns, coordination protocol | Pre-execution safety enforcement |
| Verdict | port-partially | adopt |

**Priority order:** dcg first (zero-effort install, immediate safety win), then port agent farm patterns (lock, heartbeat, adaptive timeout) into Clavain's dispatch infrastructure during the next sprint that touches subagent coordination.
