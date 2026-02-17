# Research: Claude Code Orchestrator (cco) by mohsen1

**Date:** 2026-02-15
**Repo:** [github.com/mohsen1/claude-code-orchestrator](https://github.com/mohsen1/claude-code-orchestrator)
**Package:** `@mohsen/claude-code-orchestrator` (npm, v1.3.0)
**Language:** TypeScript, Node.js 22+
**License:** MIT
**Stars:** ~13 (niche but actively developed)
**Created:** 2026-01-12, last updated 2026-02-14

---

## 1. Architecture

### 1.1 Core Stack

CCO is built on the **Claude Agent SDK** (`@anthropic-ai/claude-agent-sdk ^0.2.9`). It does NOT shell out to the `claude` CLI or use tmux -- it programmatically spawns Claude sessions via the SDK's `query()` function. Each session is a persistent Agent SDK conversation that can be resumed across tasks.

Key dependencies: `simple-git` (git operations), `commander` (CLI), `inquirer` (interactive setup), `zod` (config validation), `winston` (logging), `execa` (subprocess).

### 1.2 Two Operational Modes

**Flat Mode** (default when `workerCount <= groupSize` or `groupSize` is unset):
```
Architect (read-only, coordinates)
 +-- worker-1 (own worktree + branch)
 +-- worker-2
 +-- worker-N
```

**Hierarchical Mode** (when `workerCount > groupSize`):
```
Architect (Opus, read-only, main branch)
 +-- Tech Lead 1 (Sonnet, read-only, feat/cluster-1)
 |    +-- worker-1 (Sonnet, own worktree)
 |    +-- worker-2
 +-- Tech Lead 2 (Sonnet, read-only, feat/cluster-2)
      +-- worker-3
      +-- worker-4
```

Tested at scale: the monitoring observations doc shows a 24-worker run with 4 clusters of 6 workers each, plus 4 tech leads and 1 architect = 29 active sessions simultaneously.

### 1.3 CLI Interface

```bash
# Install globally
npm install -g @mohsen/claude-code-orchestrator

# Interactive setup (prompts for repo URL, branch, worker count, auth mode)
cco start

# With config directory
cco start --config ./my-config/

# Config directory contains:
#   orchestrator.json  - main configuration
#   api-keys.json      - optional API key rotation
```

The `cco start` command (defined in `src/cli/commands/start.ts`) either runs interactive prompts via `inquirer` or loads a config directory. It creates a timestamped log directory, initializes a crash logger, starts a memory monitor, and launches the orchestrator.

### 1.4 Session Lifecycle

Each agent role (architect, tech-lead, worker) gets a persistent `Session` object managed by `SessionManager`. Sessions track:
- `claudeSessionId` (Agent SDK session ID for resume)
- `worktreePath` (git worktree location)
- `branchName` (isolated branch)
- `taskHistory` (all prompts + results)
- `metrics` (token count, tool calls, task count)
- `authConfigIndex` (which API key to use)

Sessions are persisted to `sessions.json` for resume across process restarts (`autoResume: true` by default).

### 1.5 Orchestration Loop

The main loop runs continuously until max runtime (default 480 min = 8 hours):

1. **Pull latest** from remote
2. **Phase 1 - Planning**: Architect reads `PROJECT_DIRECTION.md` and codebase, outputs a JSON plan assigning goals to tech leads (hierarchical) or directly to workers (flat)
3. **Phase 2 - Assignment** (hierarchical only): Tech leads each create JSON work plans for their workers
4. **Phase 3 - Execution**: All workers run in parallel (`Promise.all`), each in their own worktree. As workers complete, they're immediately merged and potentially reassigned new work
5. **Phase 4 - Integration**: Feature branches merge to main (hierarchical) or worker branches merge to work branch (flat)
6. **Repeat** with next iteration

The flat mode implements a **continuous merge** pattern: `Promise.race` waits for any worker to finish, immediately merges it, then asks the architect for a new assignment for that worker. This keeps all workers busy.

---

## 2. Token Efficiency

### 2.1 Context Sharing

**CCO does NOT share context between instances.** Each session is an independent Agent SDK conversation. There is no shared memory bus, embedding store, or cross-session context injection.

The only implicit context sharing is through:
- **Git**: Workers see each other's committed code via git pulls
- **PROJECT_DIRECTION.md**: All agents read the same project direction file
- **Architect's JSON plans**: Parsed programmatically, not injected into worker prompts as shared context

### 2.2 Session Continuity (Context Reuse)

The key token efficiency feature is **session resume**. The SDK's `resume` option lets a session maintain its conversation history across multiple task executions:

```typescript
const queryOptions: SDKOptions = {
  resume: session.claudeSessionId,  // Resume existing conversation
  forkSession: options.forkSession,  // Or fork for exploration
  // ...
};
```

This means a worker that finishes task 1 and gets reassigned task 2 doesn't need to re-read the entire codebase -- it already has context from the previous task.

### 2.3 Context Compaction

`SessionManager` has a compaction mechanism triggered when `totalTokensUsed > compactThreshold` (default 80,000 tokens, ~80% of 100k context). Compaction:

1. Asks the current session to summarize its work so far
2. Clears the `claudeSessionId` (forcing a fresh session)
3. Resets `totalTokensUsed` to 0
4. The next prompt will start a new conversation with the summary as context

This is a basic "conversation summarization" approach, NOT a sophisticated token compression system. The summary prompt is:

> "Summarize the work done in this session so far: What files were created/modified? What features were implemented? What decisions were made and why? What's the current state of the task?"

### 2.4 Prompt Deduplication

**There is no prompt deduplication or compression.** Each agent gets full prompts with all context inlined. The architect's JSON plan and tech lead's assignments are passed as-is to worker prompts. No delta encoding, no shared references.

### 2.5 Real-World Token Multiplier

From HN discussion and web sources: running N parallel agents costs roughly **4-15x** a single session due to:
- Each agent independently reading/exploring the codebase
- No shared tool call cache (if worker-1 reads file X, worker-2 reads it again)
- Architect + tech lead overhead (planning queries consume tokens before workers start)

The monitoring doc shows 29 sessions for a 24-worker run. At roughly 80k tokens each, that's ~2.3M tokens per iteration.

---

## 3. Task Decomposition

### 3.1 LLM-Driven, Not Config-Driven

Task decomposition is **entirely LLM-driven at runtime**. The only user input is `PROJECT_DIRECTION.md` (high-level goals) and `orchestrator.json` (structural config like worker count).

The architect agent reads the codebase and produces a structured JSON plan:

```json
{
  "features": [
    {
      "lead": "lead-1",
      "featureBranch": "feat/auth",
      "goal": "Implement authentication system",
      "files": ["src/auth/", "src/middleware/"],
      "objectives": ["JWT token management", "OAuth2 flow"]
    }
  ]
}
```

### 3.2 Explicit Independence Constraint

The architect prompt enforces that **each feature area must be independent** -- no dependencies between tech leads or workers. This is the primary mechanism for avoiding conflicts at the planning level.

From the architect prompt:
> "Each Tech Lead should have an independent feature area (no dependencies)"

The flat mode prompt adds stronger anti-duplication guidance:
> "CRITICAL - NO DUPLICATE WORK: Each task/feature must be assigned to EXACTLY ONE worker. Do NOT assign the same work to multiple workers with different wording."

### 3.3 Fallback Handling

If the architect's JSON output fails to parse, CCO falls back to generic assignments:
```typescript
for (let i = 1; i <= workerCount; i++) {
  assignments.push({
    worker: `worker-${i}`,
    area: `Section ${i} from PROJECT_DIRECTION.md`,
    files: ['src/'],
    tasks: ['Read PROJECT_DIRECTION.md', 'Implement assigned section', 'Run tests'],
  });
}
```

### 3.4 Dynamic Reassignment

In flat mode, completed workers get new assignments dynamically. The architect is re-queried with the current project state and asked to either assign new work or declare "complete." This creates an adaptive work-stealing pattern.

### 3.5 Completion Detection

The architect can signal completion with `{"status": "complete", "reason": "..."}`. The orchestrator also checks for `"No more work"` in error messages to break the loop.

---

## 4. Codex Integration

### 4.1 Claude-Only

**CCO is Claude-only.** It uses the `@anthropic-ai/claude-agent-sdk` exclusively. There is no integration with OpenAI Codex CLI, Gemini CLI, or any other AI provider.

The model config supports three Claude tiers:
- `opus` (mapped to `claude-opus-4-5-20251101`)
- `sonnet` (mapped to `claude-sonnet-4-5-20250929`)
- `haiku` (mapped to `claude-haiku-4-5-20251001`)

By default, the `model` config applies to all agents (architect, tech leads, workers). The agent definitions hardcode model preferences: architect uses Opus, tech leads use Sonnet, workers use Sonnet.

### 4.2 Alternative Multi-Model Orchestrators

For Codex integration, separate projects exist:
- **[codex-orchestrator](https://github.com/kingbootoshi/codex-orchestrator)** by kingbootoshi: Delegates to OpenAI Codex agents via tmux. Designed for Claude-to-Codex delegation.
- **[claude-octopus](https://github.com/nyldn/claude-octopus)** by nyldn: Multi-model orchestrator supporting Claude, Codex, and Gemini CLI.
- **[myclaude](https://github.com/cexll/myclaude)**: Multi-backend supporting Codex, Claude, Gemini, OpenCode.

### 4.3 Auth Flexibility

While Claude-only for AI, CCO supports flexible auth backends via `api-keys.json`:
```json
[
  { "name": "direct", "apiKey": "sk-ant-..." },
  { "name": "z-ai-proxy", "env": { "ANTHROPIC_AUTH_TOKEN": "...", "ANTHROPIC_BASE_URL": "https://z.ai/..." } }
]
```

This means it can work through proxy providers like z.ai, though still using Claude models.

---

## 5. Coordination & Conflict Avoidance

### 5.1 Git Worktree Isolation

The primary isolation mechanism is **one git worktree per worker**. Each worker gets:
- A dedicated branch: `worker-1`, `worker-2`, etc.
- A dedicated directory: `workspace/worktrees/worker-1/`
- Full read-write access to their worktree

Workers cannot directly modify each other's files because they're in separate filesystem paths.

### 5.2 Git Operation Queue

The `GitOperationQueue` (`src/git/operation-queue.ts`) serializes git operations to prevent `.git/index.lock` contention:

**Bucketed locking:**
- Each worktree has its own queue -- local operations (add, commit, status) run in parallel across worktrees
- A global queue serializes shared operations (fetch, push, gc) that touch the shared `.git/objects`

**Auto-detection:**
- Read-only commands (`rev-parse`, `branch`, `log`, `diff`, `show`) skip the queue entirely
- Critical commands (`merge`, `push`, `commit`) get high priority
- Global commands (`fetch`, `push`, `gc`, `worktree`) use the global lock

**Retry logic:**
- Up to 3 retries with exponential backoff + jitter
- Retryable errors: `index.lock`, `another git process`, `timed out`
- Global failure circuit breaker at 50 total failures
- 50ms delay between operations for git resource release

### 5.3 Hook-Based Git Safety

`hooks.ts` implements a `GitOperationLock` as Pre/PostToolUse hooks on the `Bash` tool. Every bash command is checked for git patterns:

```typescript
function isGitCommand(command: string): boolean {
  return [/^git\s/, /^\s*git\s/, /&&\s*git\s/, /;\s*git\s/, /\|\s*git\s/]
    .some(pattern => pattern.test(command));
}
```

If it's a git command, the pre-hook acquires the lock; the post-hook releases it. This serializes all git operations across all sessions at the tool level.

### 5.4 Stale Lock Cleanup

Before every git operation, `clearStaleGitLocks()` scans the `.git` directory (up to 4 levels deep) for `.lock` files older than 2 minutes and removes them.

### 5.5 Merge Strategy

Merge conflict resolution is configurable via `mergeStrategy`:
- `auto-resolve` (default): Try `--theirs` first, fall back to `--ours`
- `theirs`: Always accept incoming changes
- `ours`: Always keep current branch
- `union`: Line-level union merge
- `skip`: Skip conflicting merges
- `fail`: Abort on any conflict

The auto-resolve strategy in practice:
1. Attempt `git merge` normally
2. On conflict, list unmerged files
3. For each file: try `git checkout --theirs`, if that fails try `git checkout --ours`
4. Stage all and commit

### 5.6 Tool Restrictions by Role

Architects and tech leads are **read-only** to prevent accidental writes to the main repo:
```typescript
architect: ['Read', 'Glob', 'Grep', 'Task']
techLead:  ['Read', 'Glob', 'Grep', 'Task']
worker:    ['Read', 'Write', 'Edit', 'Bash', 'Glob', 'Grep', 'Task']
```

### 5.7 Safety Hooks

Dangerous command patterns are blocked via regex:
- `rm -rf /`, `rm -rf ~`, fork bombs, `dd if=/dev/zero`
- `git push.*--force.*main` (force push to main)
- `chmod -R 777 /`

### 5.8 Clean State Enforcement

Before any merge/checkout, `ensureCleanGitState()` checks for uncommitted changes and does a hard reset if needed:
```
git merge --abort  (if merge in progress)
git reset --hard HEAD
git clean -fd
```

---

## 6. Observability & Monitoring

### 6.1 Logging

- Timestamped run log directories (`run-2026-02-15T...`)
- `combined.log` with Winston
- Throttled logging for high-frequency events (query starts batched at 10s, messages at 30s)
- Crash logger with synchronous writes for post-mortem

### 6.2 Memory Monitor

Adaptive memory thresholds based on worker count:
- Warning: 500MB + 50MB per worker
- Critical: 1000MB + 100MB per worker
- Maximum: 2000MB + 150MB per worker

For a 24-worker run: warning at 1700MB, critical at 3400MB, max at 5600MB.

### 6.3 Progress Reporting

Every 30 seconds, the orchestrator logs a status snapshot including session counts, task counts, and git stats (commits, merges, conflicts).

### 6.4 Event System

The orchestrator extends `EventEmitter` with typed events:
- `orchestrator:start/stop/pause/resume`
- `session:created/resumed/forked/expired/compacted`
- `task:start/complete/error`
- `tool:start/complete`
- `file:modified`
- `git:operation`
- `text:stream` (real-time output)
- `progress`

---

## 7. Comparison to Interverse Patterns

### 7.1 Where CCO Overlaps with Interlock

| Feature | CCO | Interlock |
|---------|-----|-----------|
| Isolation | Git worktrees (separate dirs) | Per-session `GIT_INDEX_FILE` |
| Locking | Async lock + operation queue | `mkdir` atomicity + reservation TTLs |
| Merge | Auto-resolve (theirs/ours) | Pre-commit validation + broadcast |
| Coordination | LLM-driven JSON plans | File reservation with 15min TTL |
| Scope | Separate repository clone | Same repository, same working dir |

### 7.2 Key Differences

1. **CCO clones the repo fresh** and creates worktrees from scratch. Interlock coordinates agents working in the *same* repo directory.
2. **CCO's coordination is implicit** (plan independent tasks) vs. Interlock's **explicit reservation system** (block/allow per-file).
3. **CCO has no real-time inter-agent communication.** Workers don't know about each other. Interlock has Intermute for real-time agent broadcasts.
4. **CCO is standalone** (npm package, runs outside Claude Code). Interlock is a Claude Code plugin that augments existing sessions.
5. **Token efficiency**: CCO has no shared context or tool call caching. Interlock/Clavain benefit from shared memory and beads.

### 7.3 What CCO Does Better

1. **Automatic session resume** via Agent SDK -- sessions survive across iterations without manual intervention
2. **API key rotation** for rate limit management -- automatic failover with round-robin
3. **Hierarchical scaling** -- tested at 24+ workers with cluster-based organization
4. **Complete hands-off operation** -- no human in the loop after `cco start`

### 7.4 What CCO Lacks

1. **No context sharing between agents** -- massive token waste on redundant codebase reads
2. **No file-level conflict prevention** -- relies on agents choosing non-overlapping files, with brute-force auto-resolve as fallback
3. **No semantic merge** -- `checkout --theirs` loses the target branch's changes entirely
4. **No support for non-Claude agents** -- no Codex, Gemini, or local model delegation
5. **No MCP integration** -- doesn't leverage MCP servers for shared state or tools

---

## 8. Sources

- [GitHub: mohsen1/claude-code-orchestrator](https://github.com/mohsen1/claude-code-orchestrator) -- full source code analysis
- [Hacker News: Orchestrate teams of Claude Code sessions](https://news.ycombinator.com/item?id=46902368) -- community discussion
- [Claude Code Docs: Agent Teams](https://code.claude.com/docs/en/agent-teams) -- official Anthropic multi-agent docs
- [GitHub: kingbootoshi/codex-orchestrator](https://github.com/kingbootoshi/codex-orchestrator) -- Codex delegation alternative
- [GitHub: nyldn/claude-octopus](https://github.com/nyldn/claude-octopus) -- multi-model orchestrator
- [Ona.com: How to run Claude Code in parallel](https://ona.com/stories/parallelize-claude-code) -- parallelization patterns
