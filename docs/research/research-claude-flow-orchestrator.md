# Research: claude-flow (ruvnet/claude-flow) Orchestrator

**Date:** 2026-02-15
**Subject:** Architecture, token efficiency, MCP integration, delegation patterns, and Codex support
**Repo:** https://github.com/ruvnet/claude-flow
**Stats:** 14,089 stars, 1,658 forks, 465 open issues, MIT license, TypeScript, created 2025-06-02

---

## Executive Summary

claude-flow is an ambitious multi-agent orchestration framework for Claude Code that claims to deploy 60+ specialized agents in coordinated swarms. After deep investigation of the actual source code, wiki, issues, and architecture documents, the picture is more nuanced than the marketing suggests:

- **What works:** SQLite-based shared memory (`.swarm/memory.db`), MCP server registration with Claude Code, basic agent-type routing, and the HNSW vector index (a genuine from-scratch implementation).
- **What is aspirational:** The swarm consensus algorithms (Raft, Byzantine) are educational stubs not suitable for production. The worker dispatch is a mock that returns hardcoded results. The "Agent Booster" (WASM transforms) and "ReasoningBank" are partially implemented at best. Issue #653 documented that ~85% of MCP tools were mock/stub implementations returning success without doing anything.
- **What is useful to study:** The overall architecture *design* (queen-worker hierarchy, topology management, namespace-scoped memory, dual-mode orchestration) contains ideas worth extracting, even if the implementation doesn't fully deliver.

**Verdict for Interverse:** Several patterns are directly applicable to our Clavain/interlock stack. The shared-memory-via-SQLite approach mirrors what we already do. The MCP-as-coordination-layer pattern is worth studying. The token optimization claims should be treated with extreme skepticism. The actual multi-instance orchestration relies on spawning `claude -p` subprocesses, which is what Claude Code's native TeammateTool now does natively.

---

## 1. Architecture: Multi-Agent Orchestration

### 1.1 High-Level Flow

```
User -> CLI/MCP -> Router -> Swarm -> Agents -> Memory -> LLM Providers
                     ^                                        |
                     |________ learning loop ________________|
```

The system presents itself as an MCP server (`mcp__claude-flow__*`) that Claude Code can call. The core loop:

1. User invokes `npx claude-flow@alpha mcp start` (starts stdio MCP server)
2. Claude Code connects via `claude mcp add claude-flow npx claude-flow@alpha mcp start`
3. Tools like `swarm_init`, `agent_spawn`, `task_orchestrate` become available
4. The framework manages agent lifecycle, task queues, and shared memory

### 1.2 Queen-Worker Hierarchy (the "Swarm" abstraction)

The swarm model uses a biological metaphor with three queen types and eight worker specializations:

**Queens (coordinators):**
- **Strategic Queen** -- high-level planning, goal decomposition
- **Tactical Queen** -- task-level coordination, agent assignment
- **Adaptive Queen** -- dynamic rebalancing based on runtime metrics

**Workers (specialized agents):**
- Researcher, Coder, Analyst, Tester, Architect, Reviewer, Optimizer, Documenter

**Source:** `v3/@claude-flow/swarm/src/queen-coordinator.ts`

The `QueenCoordinator` class extends `EventEmitter` and scores agents across six dimensions:

| Dimension | Weight | What it measures |
|-----------|--------|-----------------|
| Capability match | 30% | Agent type alignment + specific skills |
| Load | 20% | Inverse of current workload |
| Performance history | 25% | Success rates from past outcomes |
| Health | 15% | Operational status |
| Availability | 10% | idle/busy/error state |

This scoring logic is genuinely implemented. However, the actual execution delegates to dependency-injected services (`swarm.assignTaskToDomain()`, `neural.findPatterns()`) which are not all fully realized.

### 1.3 Swarm Topologies

Four topologies are supported in the type system:

- **Hierarchical** (default) -- single coordinator enforces alignment
- **Mesh** -- peer-to-peer, all agents communicate directly
- **Ring** -- circular message passing
- **Star** -- central hub with spoke agents

Configuration example from docs:

```javascript
swarm_init({
  topology: "hierarchical",
  maxAgents: 8,
  strategy: "specialized"
})
```

**Source:** `v3/@claude-flow/swarm/src/topology-manager.ts`

### 1.4 How Agents Actually Run

This is the critical question. There are two layers:

**V2 (what users actually ran):**
The coordinator in `v2/src/cli/agents/coordinator.ts` does NOT actually spawn Claude CLI processes. It extends `BaseAgent` and simulates orchestration with `delay()` timeouts. The `allocateResources()` returns mock agent IDs ("Agent-001", "Agent-002"). The `coordinateTeam()` generates fictional metrics.

**V3 (the rebuild):**
The dual-mode orchestrator (`v3/@claude-flow/codex/src/dual-mode/orchestrator.ts`) DOES spawn real child processes using Node's `spawn()`:

```typescript
const proc = spawn(command, args, {
  cwd: projectPath,
  env: { ...process.env, FORCE_COLOR: '0' },
  stdio: ['pipe', 'pipe', 'pipe']
});
```

Each worker gets CLI arguments including prompt text, output format, max turns, and model specifications. The command invoked is the `claude` CLI with `-p` flag for headless mode.

However, the worker dispatch service (`v3/@claude-flow/swarm/src/workers/worker-dispatch.ts`) is a **complete mock** -- no child_process imports, no Claude API calls, just simulated execution with `setTimeout(resolve, Math.min(ms, 10))` and hardcoded stub data.

**Bottom line:** The only real multi-instance mechanism is spawning `claude -p` subprocesses, which is essentially what Claude Code's native `TeammateTool` (Agent Teams / swarm mode) now does with tmux.

### 1.5 Consensus Algorithms

The codebase contains implementations for:
- Raft (`v3/@claude-flow/swarm/src/consensus/raft.ts`)
- Byzantine fault tolerance (`byzantine.ts`)
- Gossip protocol (`gossip.ts`)

**Assessment of Raft implementation:** This is a simplified educational prototype, not production-grade:
- Leader election exists but `requestVote()` only compares term numbers (no log matching)
- `appendEntries()` is a stub without conflict resolution
- All peer interactions use in-memory `Map` objects (no network communication)
- No disk-based persistence (required for Raft safety guarantees)
- `lastApplied` is tracked but entries are never applied to a state machine

### 1.6 Source Code Scale

| Component | Files | Assessment |
|-----------|-------|------------|
| v3/@claude-flow/* (20 packages) | 191 dirs in CLI alone | Massive surface area |
| v2/src/ | 758 files | More mature but coordinator is mock |
| Total TS/JS files | ~2,109 | High volume, mixed quality |

---

## 2. Token Efficiency

### 2.1 Claimed Optimizations

The documentation claims 30-50% token reduction through four mechanisms:

| Mechanism | Claimed Savings | How |
|-----------|----------------|-----|
| ReasoningBank retrieval | -32% | Retrieve cached reasoning patterns instead of re-deriving |
| Agent Booster (WASM) | -15% | Skip LLM for simple code edits, do them locally |
| Response caching | -10% | Cache identical or near-identical queries |
| Request batching | -20% | Combine multiple small requests |

### 2.2 What's Actually Implemented

**ReasoningBank** (`v2/src/cli/simple-commands/memory.js`):
- Uses SQLite with 384-dimensional MiniLM embeddings (Xenova/all-MiniLM-L6-v2)
- Stores trajectories (interaction patterns) with confidence scores
- Semantic search via HNSW index for finding conceptually related past results
- The HNSW implementation (`v3/@claude-flow/memory/src/hnsw-index.ts`) is genuine -- from-scratch with BinaryMinHeap/BinaryMaxHeap, multi-layer navigation, cosine/Euclidean/dot-product distance metrics, and optional binary quantization

**Agent Booster:**
- Claims 352x faster code transforms via WASM AST analysis
- The actual worker-dispatch that would use this is a stub returning hardcoded data
- No independent verification of the 352x claim exists

**Shared Memory (the real token saver):**
The most genuinely useful token-efficiency pattern is the namespace-scoped shared memory:

```javascript
// Store findings for other agents
await mcp__claude-flow__memory_store({
  namespace: "collaboration",
  key: "auth-patterns",
  value: JSON.stringify(findings)
});

// Retrieve context without re-analyzing
const ctx = await mcp__claude-flow__memory_search({
  namespace: "collaboration",
  query: "auth patterns"
});
```

This is backed by SQLite with WAL mode, and entries support TTL expiration. Namespace isolation prevents cross-contamination between unrelated tasks. This is the most practical token-saving mechanism in the codebase.

### 2.3 3-Tier Model Routing (ADR-026)

The most interesting token-efficiency concept is complexity-based routing:

| Tier | Engine | Latency | Cost | Use Case |
|------|--------|---------|------|----------|
| Tier 1 | Agent Booster (WASM) | <1ms | $0 | Simple transforms, variable renames |
| Tier 2 | Haiku | ~500ms | $0.0002 | Low complexity (<30%) |
| Tier 3 | Sonnet/Opus | 2-5s | $0.003-0.015 | Complex reasoning (>30%) |

The routing logic detects task complexity and delegates accordingly. Simple code transforms that don't need LLM reasoning get handled locally. This is a sound architectural concept but the Tier 1 WASM implementation is largely aspirational.

### 2.4 Token Optimizer API

```typescript
import { getTokenOptimizer } from '@claude-flow/integration';

const optimizer = await getTokenOptimizer();
const ctx = await optimizer.getCompactContext("auth patterns");
await optimizer.optimizedEdit(file, oldStr, newStr, "typescript");
```

The `getCompactContext()` retrieves relevant context from the HNSW index rather than stuffing full files into the prompt. `optimizedEdit()` uses the Agent Booster for simple transforms and falls back to LLM for complex ones.

### 2.5 Honest Assessment

The shared-memory namespace approach genuinely reduces redundant work across agents. The HNSW implementation is real and functional. Everything else -- ReasoningBank's claimed 46% speedup, Agent Booster's 352x improvement, the "250% extension of subscription capacity" -- lacks independent verification and the implementations range from incomplete to mock.

---

## 3. MCP Integration

### 3.1 MCP Server Architecture

The MCP server (`v3/@claude-flow/mcp/src/server.ts`) is one of the more complete implementations in the codebase:

- Extends `EventEmitter`, implements `IMCPServer`
- Supports three transports: stdio (default), HTTP, WebSocket
- MCP 2025-11-25 specification compliant
- Rate limiting (per-session and burst)
- Resource subscriptions with change notifications
- Session management with timeout handling
- Connection pooling

**Four built-in system tools:**
1. `system/info` -- platform, version, runtime details
2. `system/health` -- health status with connection pool metrics
3. `system/metrics` -- server performance statistics
4. `tools/list-detailed` -- category-filtered tool enumeration

### 3.2 Tool Categories (87 claimed tools)

| Category | Count | Examples |
|----------|-------|---------|
| Swarm Management | 16 | swarm_init, agent_spawn, task_orchestrate, load_balance |
| Neural & AI | 15 | neural_train, neural_predict, pattern_recognize |
| Memory & Persistence | 10 | memory_store, memory_search, memory_backup |
| Performance & Analytics | 10 | performance_report, bottleneck_analyze, token_usage |
| GitHub Integration | 6 | github_repo_analyze, github_pr_manage |
| Dynamic Agent Architecture | 6 | daa_agent_create, daa_capability_match |
| Workflow & Automation | 8 | workflow_create, pipeline_create |
| System Utilities | 16 | sparc_mode, terminal_execute, security_scan |

### 3.3 Tool Invocation Pattern

```javascript
// Initialize swarm via MCP
await mcp__claude-flow__swarm_init({
  topology: "hierarchical",
  strategy: "auto",
  maxAgents: 8
});

// Spawn specialized agent
await mcp__claude-flow__agent_spawn({
  type: "coder",
  name: "ImplementationAgent",
  capabilities: ["typescript", "react", "nodejs"]
});

// Orchestrate workflow
await mcp__claude-flow__task_orchestrate({
  task: "Build authentication system",
  strategy: "parallel",
  priority: "high"
});
```

### 3.4 Critical Issue: Mock Tools (Issue #653)

A thorough analysis by user afewell-hh in August 2025 found that approximately **85% of the 87 MCP tools were mock/stub implementations**. Key findings:

- `agent_spawn` returns agent IDs but creates no functional agents
- `task_orchestrate` creates task IDs but no actual execution occurs
- `neural_status` returns generic success with no real neural data
- `performance_report` generates fake but realistic-looking metrics
- `github_repo_analyze` returns success without analysis

The reporter used 4-level validation (basic return codes -> output verification -> side-effect testing -> mock detection). The issue was closed as "completed" but independent verification of the fix is not available.

### 3.5 How MCP Coordination Actually Works

The practical coordination mechanism:

1. MCP server starts as stdio process
2. Claude Code connects and discovers tools
3. Claude Code calls `swarm_init` to set topology
4. Claude Code calls `agent_spawn` to create workers
5. Workers share state via `memory_store`/`memory_search` with namespace scoping
6. Task dependencies tracked in-process via the task orchestrator's Map-based graph

The MCP server itself is a reasonably well-implemented piece. The issue is that the tools it exposes largely delegate to incomplete backend services.

---

## 4. Delegation Patterns

### 4.1 Task Decomposition Strategies

Three decomposition approaches from the workflow orchestration wiki:

- **Functional:** Divide by domain (frontend, backend, infra, testing)
- **Layer-Based:** Divide by architecture tier (presentation, logic, data)
- **Feature-Based:** Divide by user-facing capability (auth, payments, admin)

### 4.2 Execution Strategies

| Strategy | When Used |
|----------|----------|
| Parallel | Independent tasks, maximize throughput |
| Sequential | Hard dependencies between tasks |
| Adaptive | Dynamic adjustment based on resource availability |
| Balanced | Even load distribution across agents |
| Stream-Chained | Real-time output piping between agents (A -> B -> C) |

### 4.3 Stream-JSON Chaining

The most novel delegation pattern: downstream agents start consuming upstream output before the upstream agent finishes. No intermediate files. Configuration is via dependency declarations:

```javascript
// Task B depends on Task A
// Output from A streams directly to B's input
{
  tasks: [
    { id: 'A', agent: 'researcher', task: 'Analyze codebase' },
    { id: 'B', agent: 'coder', task: 'Implement changes', depends: ['A'] }
  ]
}
```

Claimed 40-60% faster than file-based handoffs.

### 4.4 The Planner/Executor Split

The architecture has an explicit planner/executor separation:

**Planner (Queen/Coordinator):**
- Analyzes task complexity (0-1 score based on subtask count, dependency depth, priority, type, description length)
- Selects execution strategy (sequential, parallel, pipeline, fan-out-fan-in, hybrid)
- Assigns agents based on the 6-dimension scoring model (see Section 1.2)
- Maintains 2 backup agents for failover

**Executor (Workers):**
- Receive specific, scoped tasks
- Report progress via shared memory
- Results feed back into the learning system

In practice (v2), the coordinator is largely simulated. In v3, the queen-coordinator has real scoring and planning logic, but delegates to services that are partially stubbed.

### 4.5 Anti-Drift Measures

The framework emphasizes "anti-drift" -- preventing agents from wandering off-task:

- Hierarchical coordinators validate outputs against goals
- Short task cycles with verification gates
- Frequent checkpoints via post-task hooks
- "Do what has been asked; nothing more, nothing less" enforced in CLAUDE.md
- Max 8 agents per swarm to limit drift surface

### 4.6 Collaboration Templates

Pre-defined agent team compositions for common workflows:

| Template | Agent Pipeline |
|----------|---------------|
| feature | Architect -> Coder -> Tester -> Reviewer |
| security | Analyst -> Scanner -> Reporter |
| refactor | Architect -> Refactorer -> Tester |
| bugfix | Researcher -> Coder -> Tester |

---

## 5. Codex Integration

### 5.1 Dual-Mode Architecture

The `@claude-flow/codex` package (`v3/@claude-flow/codex/src/dual-mode/orchestrator.ts`) provides parallel execution between Claude Code and OpenAI Codex CLI:

**Rationale:** Single platforms offer one perspective. Dual-mode enables cross-validation, complementary reasoning styles, built-in code review, and parallel execution.

**Platform Strengths (as documented):**
- Claude: Architecture, security review, testing strategy, complex reasoning
- Codex: Implementation, performance optimization, bulk refactoring

### 5.2 Implementation Mechanism

The `DualModeOrchestrator` spawns both platforms as child processes:

```typescript
// Both platforms invoke the `claude` CLI
const proc = spawn(command, args, {
  cwd: projectPath,
  env: { ...process.env, FORCE_COLOR: '0' },
  stdio: ['pipe', 'pipe', 'pipe']
});
```

Workers receive CLI arguments: prompt, output format, max turns, model spec. Both platforms map to the same `claude` CLI command in the current implementation -- the Codex-specific backend is not fully differentiated.

### 5.3 Shared Memory Coordination

Workers coordinate via the `collaboration` namespace:

```bash
# Worker stores findings
npx claude-flow memory store --namespace collaboration --key auth-findings --value "..."

# Other worker retrieves
npx claude-flow memory search --namespace collaboration --query "auth"
```

Tasks include instructions for workers to poll memory at 500ms intervals for upstream dependencies.

### 5.4 Assessment

The dual-mode concept is architecturally sound but the implementation is partially stubbed. Both "Claude" and "Codex" workers currently spawn the same `claude` CLI. The actual Codex CLI (`codex`) integration -- with its different invocation patterns, sandbox model, and session semantics -- is not concretely implemented.

---

## 6. Comparison with Claude Code Native Features

### 6.1 Claude Code TeammateTool (Agent Teams)

Claude Code's built-in `TeammateTool` (discovered in v2.1.19, December 2025) provides native multi-agent coordination:

| Feature | claude-flow | TeammateTool (native) |
|---------|------------|----------------------|
| Group unit | Swarm | Team |
| Agent | Agent with types | Teammate with roles |
| Leader | Queen/Coordinator | Plan mode agent |
| Messaging | MessageBus | teammate_mailbox |
| Approval | ConsensusProposal | approvePlan/rejectPlan |
| Process backend | Node child_process | tmux (26 references in binary) |
| File persistence | SQLite | File-based mailbox (~/.claude/teams/) |

The 92% structural similarity between claude-flow's swarm model and TeammateTool suggests convergent evolution in a constrained design space. TeammateTool has the advantage of being built into Claude Code, so it doesn't need an MCP bridge.

### 6.2 What claude-flow Adds Beyond Native

- Vector search via HNSW index (native TeammateTool has no vector search)
- Four consensus algorithms (native has implicit majority)
- Topology configuration (mesh, ring, star, hierarchical)
- Cross-platform learning via shared memory namespaces
- Complexity-based model routing (Tier 1/2/3)
- 87 MCP tools (even if many are stubs, the tool framework exists)

---

## 7. Lessons for Interverse

### 7.1 Patterns Worth Adopting

1. **Namespace-scoped shared memory via SQLite:** This is what we already do with interlock's reservation system and intermute's coordination. claude-flow validates the pattern.

2. **Complexity-based task routing:** The 3-tier model (skip LLM for simple transforms, use cheap model for medium, expensive model for hard) is worth implementing in Clavain's dispatch logic.

3. **Anti-drift verification gates:** Short task cycles with checkpoint verification is a solid pattern for multi-agent reliability.

4. **Stream-JSON chaining:** Real-time output piping between agents without intermediate files could reduce latency in Clavain pipelines.

5. **Agent scoring model:** The 6-dimension weighted scoring (capability 30%, load 20%, history 25%, health 15%, availability 10%) is a reasonable starting point for agent selection.

### 7.2 Patterns to Avoid

1. **Aspirational documentation:** claude-flow's biggest weakness is documentation that describes planned features as if they exist. Our AGENTS.md/CLAUDE.md should always reflect current state.

2. **Mock tool implementations:** Having 87 tools where 85% are stubs undermines trust. Better to have 10 real tools than 87 fake ones.

3. **Over-engineering consensus:** In-process Raft consensus for agent coordination is unnecessary when the coordinating process is a single Node.js server. Our `mkdir`-based atomic locking is simpler and actually works.

4. **Repo size inflation:** 2,109 TS/JS files across v2 and v3 with significant duplication. Our monorepo approach with distinct per-module repos is cleaner.

### 7.3 Concrete Ideas for Implementation

1. **HNSW for Clavain's memory:** claude-flow's from-scratch HNSW implementation (with binary quantization) could be adapted for clavain's semantic search if we outgrow simple SQLite FTS.

2. **MCP tool categories:** Their tool organization (swarm, memory, neural, performance, workflow) maps roughly to our plugin structure (interlock, intermute, clavain, intercheck).

3. **Dual-mode orchestration:** Running Claude + Codex in parallel with shared memory is worth testing in clavain for cross-validation of code changes.

---

## 8. Sources

- [claude-flow GitHub repository](https://github.com/ruvnet/claude-flow)
- [CLAUDE.md - project instructions](https://github.com/ruvnet/claude-flow/blob/main/CLAUDE.md)
- [MCP Tools wiki](https://github.com/ruvnet/claude-flow/wiki/MCP-Tools)
- [Workflow Orchestration wiki](https://github.com/ruvnet/claude-flow/wiki/Workflow-Orchestration)
- [Issue #653: 85% of MCP Tools Are Mock/Stub](https://github.com/ruvnet/claude-flow/issues/653)
- [Issue #945: V3 Complete Rebuild announcement](https://github.com/ruvnet/claude-flow/issues/945)
- [Issue #958: Can't get V3 to perform work](https://github.com/ruvnet/claude-flow/issues/958)
- [Issue #798: ReasoningBank + Agent Booster alpha](https://github.com/ruvnet/claude-flow/issues/798)
- [Architectural Comparison: V3 vs TeammateTool (gist)](https://gist.github.com/ruvnet/18dc8d060194017b989d1f8993919ee4)
- [claude-flow npm package](https://www.npmjs.com/package/claude-flow)
- [Claude-Flow quickstart guide (Medium)](https://phann123.medium.com/claude-flow-by-reuven-cohen-ruvnet-agent-orchestration-platform-guide-for-quickstart-3f95ccc3cafc)
- [Claude Flow v3 marketing site](https://claude-flow.ruv.io/)
