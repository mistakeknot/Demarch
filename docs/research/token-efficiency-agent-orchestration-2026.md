---
title: "Token-Efficient Agent Orchestration: State of the Art (2026)"
date: 2026-02-15
type: research
tags: [token-efficiency, orchestration, multi-agent, codex, claude-code]
status: complete
methodology: 4-agent parallel research (web search + codebase analysis)
---

# Token-Efficient Agent Orchestration: State of the Art (2026)

## Executive Summary

Four parallel research agents scanned open-source orchestrators, academic papers, Claude Code / Codex CLI ecosystems, and Clavain's own codebase. The landscape shows seven optimization layers, each with quantified savings.

**Key quantitative findings:**
- AgentCoder: 56.9K tokens vs MetaGPT's 138.2K (59% reduction) via 3-agent architecture
- Subagent context isolation: 67% token reduction (LangChain research)
- File indirection: 70% context savings (Clavain production)
- Lazy tool loading: 88% baseline context reduction (task-orchestrator, code-mode-toon)
- Schema pruning: 15x cost reduction (RestMCP logistics case study)
- Prompt caching: 90% cost reduction for cached tokens (Anthropic)
- AgentDropout: 21.6% prompt + 18.4% completion token reduction
- MASAI: SWE-bench at <$2/issue via 5 modular sub-agents
- DeepCode: 75.9% on 3-paper eval via channel optimization framework
- A-Mem: 85-93% reduction in memory operation tokens
- LLMLingua: up to 20x prompt compression ratio
- Gist tokens: 26x compression, 40% FLOPs reduction

---

## Layer 1: Prompt Architecture — "Don't Ship What You Don't Need"

### File Indirection (Clavain, production)
Write full agent prompts to temp files, dispatch with a ~200-char reference instead of inlining ~3K chars. Drops 7-agent dispatch from ~28K to ~4K chars (70% reduction).

### Lazy Tool Discovery (Claude Code MCP ToolSearch, code-mode-toon, task-orchestrator)
Previously 30-60% of context consumed at startup by tool schemas. With lazy loading, cost is proportional to actual usage. task-orchestrator reports 88% baseline context reduction.

### Hierarchical AGENTS.md Overrides (Codex CLI)
Nested files from repo root to CWD merge additively, with closer files overriding. Default 32 KiB cap per file. Selective rule replacement eliminates redundancy.

### Schema Pruning (RestMCP "Distiller" pattern)
Strip JSON response schemas to task-relevant fields only. A logistics company went from $0.12/query to $0.008/query — 15x cost reduction.

---

## Layer 2: Model Routing — "Right Brain for the Job"

| Strategy | Savings | Example |
|----------|---------|---------|
| Tiered model selection | 3-5x cost | Haiku for research, Sonnet for reviews, Opus for orchestration (Clavain) |
| Dynamic complexity routing | Up to 80% | claude-router by 0xrdan routes to Haiku/Sonnet/Opus by query complexity |
| Opus effort levels | Variable | Opus 4.6 low/medium/high/max effort within same model |
| Non-LLM executors | 100% | AgentCoder uses Python scripts for test execution — no model inference |
| Amazon Bedrock routing | ~30% | Automatic routing between Sonnet and Haiku based on prompt complexity |

### AgentCoder's Lesson
Three lean agents (Programmer + Test Designer + non-LLM Executor) achieved 96.3% on HumanEval using 56.9K tokens — 59% less than MetaGPT's 5-agent architecture at 138.2K tokens.

---

## Layer 3: Context Isolation — "Subagents as Garbage Collection"

### The Core Insight
Multi-agent systems outperform single agents by 90.2% but consume 15× more tokens (LangChain research). The key is making that 15× happen in disposable subagent contexts, not the orchestrator's window.

### Claude Code Task Tool Pattern
Subagents farm out (X + Y) × N work to specialists which only return the final Z-token answers. The orchestrator never sees intermediate search results, grep output, or file contents — just conclusions.

- Explore subagent: Haiku-powered, read-only tools, returns summaries
- Background agents (run_in_background: true): True parallel execution
- Max effective parallelism: 3-4 concurrent subagents

### Codex CLI Orchestration
File-based state passing between agents. Artifact verification gates. Agents receive only role-specific context.

### OpenHands AgentDelegateAction
Event-sourced architecture. Delegation hands off subtasks to fresh contexts.

### MASAI Architecture
Five sub-agents, each with different strategies (ReAct, Chain-of-Thought). 28.33% SWE-bench resolution at < $2 per issue.

---

## Layer 4: Context Compression — "Distill, Don't Accumulate"

### Compaction Strategies Compared (Factory.ai evaluation)

| Method | Compression | Quality (1-5) |
|--------|------------|---------------|
| OpenAI /responses/compact | 99.3% | 3.35 |
| Anthropic SDK | ~85% | 3.56 |
| Factory Anchored | 98.6% | 3.70 |

Critical insight: "tokens per task not tokens per request" — aggressive compression forces re-fetching.

### LLMLingua (Microsoft Research)
Up to 20x compression ratio. Available in LangChain and LlamaIndex.

### Gist Tokens
26x compression, 40% FLOPs reduction. Requires fine-tuning.

### Structured Summarization (Factory.ai)
Persistent summary with explicit sections. 85-93% reduction in memory operation tokens.

### Prompt Caching (Anthropic/OpenAI)
- Anthropic: 90% cost reduction for cached tokens, 80% latency reduction
- Critical tradeoff: summarization breaks cached representations

---

## Layer 5: Retrieval Architecture — "Pull, Don't Push"

### Multi-Strategy Code Search (State of the Art)
Five strategies with Reciprocal Rank Fusion (RRF):
1. Vector similarity (embeddings)
2. Full-text search (BM25)
3. AST symbol lookup
4. Path matching
5. Dependency tracing

### AST-Level Semantic Search (AutoCodeRover)
38% SWE-bench resolution using only 14.7 API calls and 55.5K input tokens.

### Two-Stage Retrieval
Fast vector store → LLM re-ranking. Clavain's tldr-swinton already implements this.

---

## Layer 6: Output Efficiency — "Patches Over Rewrites"

### Patch-Based Edits
- OpenAI apply_patch: Gold standard, model specifically trained on this
- JSON Whisperer (RFC 6902): 31% token reduction vs. full regeneration
- TOON (Token-Oriented Object Notation): 30-90% token reduction
- Verdict-based filtering: CLEAN vs NEEDS_ATTENTION

---

## Layer 7: Architectural Patterns — "Systems, Not Tricks"

### DeepCode's Channel Optimization
1. Blueprint Distillation — compress source docs into high-signal plans
2. Stateful Code Memory — concise indexed state
3. Conditional RAG — bridge gaps on demand
4. Closed-Loop Error Correction — feedback as corrective signal

Result: 75.9% on 3-paper evaluation, surpassing PhD-level experts (72.4%).

### AgentDropout
Dynamic redundancy elimination. 21.6% prompt token reduction, 18.4% completion reduction.

### Reflection-Driven Trajectory Pruning (Agent-R)
Splice at first detectable error. Prevent compounding token waste.

### Self-Organized Agents (SoA)
Auto-scales agent count by problem complexity. 5% accuracy improvement on HumanEval.

---

## What Clavain Already Does vs. Opportunities

### Already In Production

| Technique | Implementation | Savings |
|-----------|---------------|---------|
| File indirection | Prompt files in /tmp/, 200-char dispatch | 70% |
| Model routing | Haiku research / Sonnet review / Opus orchestrate | 3-5x |
| Hybrid Codex routing | Interserve toggle for implementation | 89% |
| AST-based retrieval | tldr-swinton MCP server | 60-80% |
| Background agents | run_in_background for parallel work | Context isolation |
| Compact skill loading | SessionStart hook injects routing table | Startup efficiency |

### High-Value Opportunities

| Technique | Source | Expected Savings | Bead |
|-----------|--------|-----------------|------|
| Hierarchical dispatch (meta-agent) | Clavain brainstorm | 98% parent context | iv-quk4 |
| Token ledger + budget gating | Gap analysis | Cost visibility | iv-8m38 |
| AgentDropout for flux-drive | arxiv:2503.18891 | 20% token reduction | iv-qjwz |
| Blueprint distillation | DeepCode | Noise filtering | iv-6i37 |
| Prompt compression | LLMLingua | 20x compression | iv-19oc |
| Agentic memory (A-Mem) | arxiv:2502.12110 | 85-93% memory ops | iv-qtcl |
| Trajectory pruning | Agent-R | Stop wasted work | iv-ffo5 |
| Trust-weighted triage | Gap analysis + interspect | Skip low-value agents | iv-ynbh |

---

## Appendix: Flux-Drive Review Findings (2026-02-15)

Four specialized reviewers (fd-architecture, fd-systems, fd-user-product, fd-performance) identified gaps in this document. Key findings:

### P0: Document Slicing (Not in Original Research)
Each fd-* agent receives the FULL document. Slicing (summary + relevant sections per agent) would save 50-70% of total flux-drive tokens. This is the highest-impact optimization and was missed because the research drew from external sources, not the internal audit (`audit-flux-drive-token-flow.md`). Bead: iv-7o7n.

### P1: Compression Breaks Prompt Caching (Anti-Pattern)
LLMLingua/gist tokens invalidate Anthropic's 90% cache discount on recurring prompts. Net WORSE for flux-drive's stable agent prompts. iv-19oc scoped to one-shot workflows only.

### P1: No Primary Measurements
Zero data on actual Clavain token usage. This is a literature review, not a product roadmap. Benchmarking framework needed before implementing any optimization. Bead: iv-jq5b.

### P2: Savings Are Not Additive
File indirection + AgentDropout + context isolation all address orchestrator bloat. They overlap. The percentages in this document cannot be summed.

### P2: Inter-Layer Feedback Loops
Compression ↔ retrieval loop (compression changes embeddings → vector search degrades → more fetching → more compression needed). Token efficiency paradox (over-optimization → quality degradation → retries → higher total cost). Bead: iv-dthn.

### P2: Layer 7 Needs Restructure
Layer 7 is a catch-all. Blueprint Distillation = L4, AgentDropout = L3, Trajectory Pruning = L6. Should become "Meta-Orchestration" (patterns spanning multiple layers).

### P2: Dependency Graph Corrections
- iv-8m38 (token ledger) is FOUNDATIONAL — prerequisite for iv-qjwz, iv-ynbh, iv-6i37
- iv-quk4 can be prototyped directly (pattern proven in OpenHands/MASAI)
- iv-qjwz and iv-ynbh are partially mutually exclusive

### P3: Missing Patterns
Agent-scoped tooling, differential context updates, adaptive token budgets, hybrid symbolic-neural routing, crumple zones (intentional over-provisioning for resilience). Bead: iv-eaeq.

### Corrected A-Mem Claim
The 85-93% reduction is for memory OPERATION tokens, not total session tokens. iv-qtcl description updated.

### Oracle GPT-5.2 Pro Cross-AI Review (2026-02-15)
Novel findings not caught by Claude-based reviewers: (1) Missing measurement spec — document mixes chars, tokens, dollars, FLOPs, compression ratios without consistent accounting model. (2) "Token efficiency ≠ cost efficiency" — provider pricing differs by input vs output tokens. (3) File indirection may shift tokens rather than save them if agents read file content into context. (4) Security threat model missing: tempfile leakage, prompt injection via retrieval, memory poisoning, repo-level prompt injection via AGENTS.md. (5) Per-layer pitfall catalog. Bead: iv-xuec (security). Full review: `docs/research/token-efficiency-review-findings.md`.

---

## Orchestrator Deep Dives (2026-02-15 update)

Parallel research into 5 orchestrators + Clavain's interserve, focusing on how each maximizes token efficiency when delegating to subagents.

### Orchestrator Comparison Matrix

| Feature | claude-flow | cco | myclaude | SystemPrompt | Clavain/interserve |
|---------|------------|-----|----------|-------------|----------------|
| **Multi-agent** | Mock swarm (v2), real spawn (v3) | Agent SDK sessions | CLI wrapper subprocess | Single process | Claude subagents + Codex CLI |
| **Token efficiency** | Shared memory (SQLite), mostly aspirational | Session resume only | Cost arbitrage + skill caps + summary mode | None | Dispatch templates, compact skills |
| **Backend diversity** | Claude only (Codex package stubbed) | Claude only | 4 backends (Codex, Claude, Gemini, OpenCode) | Claude only | Claude + Codex CLI |
| **Coordination** | SQLite shared memory + MCP | Git worktrees + operation queue | Git worktrees | None | Interlock reservations + Intermute |
| **DAG scheduling** | Dependency declarations (partial) | Flat/hierarchical mode | Topological sort with layers | N/A | Parallel dispatch via Task tool |

### Key Findings Per Orchestrator

**claude-flow** (14k stars, ruvnet/claude-flow): ~85% of 87 MCP tools are mock/stub (Issue #653). Genuine patterns: namespace-scoped SQLite shared memory with HNSW vector search, 3-tier complexity routing (WASM → Haiku → Opus), stream-JSON chaining between agents, 6-dimension weighted agent scoring (capability 30%, history 25%, load 20%, health 15%, availability 10%). Full report: `docs/research/research-claude-flow-orchestrator.md`.

**cco** (~13 stars, mohsen1/claude-code-orchestrator): Built on Agent SDK (not CLI). Git worktree isolation per worker with bucketed operation queue. Session resume across task reassignments. Context compaction at 80k tokens. Tested at 24 workers / 29 sessions. 4-15x cost multiplier. No context sharing between agents. Full report: `docs/research/research-cco-orchestrator.md`.

**myclaude** (2.3k stars, cexll/myclaude, AGPL): **Most token-relevant.** Go CLI wrapper (`codeagent-wrapper`) with 4 backends. Key patterns: (1) Cost arbitrage — Opus for reasoning, Codex for code gen, Gemini Flash for docs, Grok for exploration. (2) 16K char skill injection budget. (3) Conditional phase skipping (score >= 8/10 → skip clarification). (4) Summary-mode output extraction (structured fields vs verbose text). (5) DAG scheduler with topological sorting. (6) Recursion prevention via `--setting-sources ""`. Full report: `docs/research/research-myclaude-multi-backend.md`.

**SystemPrompt** (139 stars): NOT a multi-agent system — spawns one Claude CLI process per task via Docker TCP bridge. No token efficiency, no task decomposition, no inter-agent coordination. One useful pattern: MCP resource subscriptions with `task://` URI scheme. Full report: `docs/research/research-systemprompt-orchestrator.md`.

### The Unsolved Problem: Agent Context Sharing

Every orchestrator re-reads the full codebase per agent. This is the single biggest token waste:

| Orchestrator | Context sharing mechanism | Cost multiplier |
|-------------|--------------------------|-----------------|
| claude-flow | SQLite shared memory (partial) | Unknown (mostly mock) |
| cco | Via git commits only | 4-15x |
| myclaude | Manual (planner forwards output) | ~3-5x |
| SystemPrompt | None | 1x (single agent) |
| Clavain | Intermute broadcast | ~2-3x |

**Flux-drive document slicing (iv-7o7n) directly attacks this** by giving each agent only relevant sections. No other orchestrator does per-agent content slicing.

### Actionable Patterns for Clavain

| Pattern | Source | Priority | Expected Impact |
|---------|--------|----------|-----------------|
| Summary-mode output extraction | myclaude | P1 | ~2-5k tokens/agent result |
| Skill injection budget cap (16K chars) | myclaude | P1 | Prevents context bloat |
| Conditional phase skipping | myclaude | P2 | Skip unnecessary work |
| Backend cost arbitrage (Gemini/Grok for cheap tasks) | myclaude | P2 | 3-5x on routed tasks |
| Session resume for Codex dispatches | cco | P2 | Avoid codebase re-reading |
| Complexity-based model skip (no-LLM for trivial) | claude-flow | P3 | 100% for simple transforms |
| Stream-JSON chaining (no intermediate files) | claude-flow | P3 | 40-60% latency reduction |

---

## Sources

### Frameworks & Tools
- [OpenHands Agent SDK](https://arxiv.org/pdf/2511.03690)
- [MASAI](https://masai-dev-agent.github.io/) — arxiv:2406.11638
- [DeepCode](https://arxiv.org/abs/2512.07921)
- [AutoCodeRover](https://aiagentstore.ai/ai-agent/autocoderover)
- [claude-flow](https://github.com/ruvnet/claude-flow)
- [code-mode-toon](https://github.com/ziad-hsn/code-mode-toon)
- [claude-router](https://github.com/0xrdan/claude-router)

### Research
- [AgentDropout](https://arxiv.org/abs/2503.18891)
- [LLMLingua](https://llmlingua.com/)
- [Gist Tokens](https://arxiv.org/abs/2304.08467)
- [Factory.ai Compression Evaluation](https://factory.ai/news/evaluating-compression)
- [AgentCoder](https://arxiv.org/html/2312.13010v3)
- [TodoEvolve](https://arxiv.org/html/2602.07839)
- [TU Wien Thesis](https://repositum.tuwien.at/bitstream/20.500.12708/224666/1/Hrubec%20Nicolas%20-%202025%20-%20Reducing%20Token%20Usage%20of%20Software%20Engineering%20Agents.pdf)
- [A-Mem](https://arxiv.org/pdf/2502.12110)

### Guides & Best Practices
- [Anthropic Context Engineering](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents)
- [Claude Code Subagent Docs](https://code.claude.com/docs/en/sub-agents)
- [Codex CLI AGENTS.md Guide](https://developers.openai.com/codex/guides/agents-md/)
- [RestMCP Token Optimization](https://www.restmcp.io/blog/reducing-token-costs-agentic-workflows.html)
- [Context Engineering for AI Agents](https://www.getmaxim.ai/articles/context-engineering-for-ai-agents-production-optimization-strategies/)

### Orchestrator Deep Dives (added 2026-02-15)
- [cco (claude-code-orchestrator)](https://github.com/mohsen1/claude-code-orchestrator) — Agent SDK multi-session orchestrator
- [myclaude](https://github.com/cexll/myclaude) — Multi-backend workflow (Codex, Claude, Gemini, OpenCode)
- [systemprompt-code-orchestrator](https://github.com/systempromptio/systemprompt-code-orchestrator) — MCP task runner
- [codex-orchestrator](https://github.com/kingbootoshi/codex-orchestrator) — Claude-to-Codex delegation
- [claude-octopus](https://github.com/nyldn/claude-octopus) — Multi-model orchestrator
- Detailed per-orchestrator reports: `docs/research/research-{claude-flow,cco,myclaude,systemprompt}-orchestrator.md`
