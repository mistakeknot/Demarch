# Research Briefing: Plugin Modularity vs Consolidation

## Source Credibility Note

Most available research covers general microservices/monolith architecture, not AI agent plugin ecosystems specifically. Domain transfer is imperfect — video streaming latency != context window overhead, and team coordination costs for humans != tool injection costs for LLMs. The strongest evidence for our question comes from the AI-specific sources (Tier 1 below). General architecture sources provide useful analogies but should not be treated as direct evidence.

---

## SIDE A: Fine-Grained Modularity at Scale

### Tier 1: Direct Evidence

**VSCode Extension Host Architecture**
- 60,000+ extensions sustained through process-boundary isolation (separate Extension Host process), lazy loading via Activation Events, and marketplace discovery
- Extensions declare activation triggers (onCommand, onLanguage, etc.) — load only when relevant. Cost of N plugins is cost of *activated* plugins, not all plugins
- Bundling (esbuild/webpack) reduces "many small files" overhead: Azure Account extension activation -50%, Docker extension startup from 3.5s to <2s
- Power-law distribution in marketplace: median installs ~500, mean ~55K — long-tail enabled by modularity

**Terraform Provider Isolation**
- 3,000+ providers as separate OS processes communicating via gRPC (go-plugin framework)
- Provider panic does not crash Terraform Core — process-level fault isolation
- When providers were bundled with Terraform Core, any provider change required a Core release — "wasn't sustainable." Now AWS releases weekly, independent of Core cadence
- go-plugin framework: "used on millions of machines across many different projects"

**Harvard/MIT Mirroring Hypothesis**
- "Strong evidence to support the mirroring hypothesis" — organizational structure mirrors software architecture
- Critical finding: "the product developed by the loosely-coupled organization is significantly more modular"
- Physical separation doesn't just *correlate* with modularity — it *causes* it

### Tier 2: Supporting Evidence

**Neovim lazy.nvim**: Demand-driven loading solves coordination — 50+ plugins with sub-100ms startup. rocks.nvim provides real package management with version isolation. Per-plugin profiling enables targeted optimization.

**Kubernetes Operators**: CRDs provide typed contracts between independent operators. OLM uses SAT solver for dependency resolution. 82% production adoption (CNCF 2025 survey).

**Sam Newman**: Physical boundaries are a "ratchet" — resist erosion over time. Logical boundaries in a monolith require continuous policing. A monorepo can be a "migratory step" but real enforcement comes from service boundaries.

### Cross-Cutting Pattern

| Pattern | VSCode | lazy.nvim | Terraform | K8s Operators |
|---|---|---|---|---|
| Process isolation | Extension Host | Lua modules | Separate OS process | Separate pods |
| Lazy loading | Activation Events | Event/cmd triggers | Per-config loading | CRD watch |
| Registry | Marketplace 60K+ | GitHub + rocks | Registry 3K+ | OperatorHub.io |
| Crash containment | Host restart | Plugin unload | Provider != Core crash | Pod restart |
| Independent versions | Per-extension | Per-plugin | Per-provider | Per-operator |

**Key claim**: Modularity at scale is not inherently expensive. It becomes expensive only when loading, discovery, dependency resolution, and isolation infrastructure is missing.

---

## SIDE B: Consolidation Past a Threshold

### Tier 1: Direct Evidence

**Amazon Prime Video (2023)**
- Video Quality Analysis tool moved from microservices (Step Functions + S3 intermediate storage) to monolith (EC2/ECS with in-memory data transfer)
- Result: **90% reduction in infrastructure cost** with increased scaling capability
- Root cause: data flowed tightly between processing stages — distributing them across network boundaries created massive overhead for zero benefit
- **Domain caveat**: This was a data pipeline, not a plugin ecosystem. The boundary was at the wrong abstraction level — not evidence that modularity itself is wrong

**Segment (2018)**
- 140+ microservices for data integration destinations, adding ~3 new per month
- Tipping point: 3 FTEs spent keeping system alive, 120 diverging dependencies, 1-hour test suites
- After consolidation: tests dropped to milliseconds, shared library improvements increased 44%
- **Key insight**: When N services do structurally identical work (receive/transform/forward), you have 1 service with N configurations — not N services

**Uber DOMA**
- 2,200 critical microservices consolidated into **70 domains** with single gateways per domain
- Platform support costs **dropped an order of magnitude**
- Pattern: consolidation at the *domain* level, not back to a single monolith

### Tier 2: Supporting Evidence

**Nano-service anti-pattern** (Arnon Rotem-Gal-Oz, 2014): "A nanoservice is a service whose overhead outweighs its utility." Services in 10-100 lines range are functions masquerading as services.

**npm micro-library problems**:
- left-pad (11 lines) unpublished → React, Babel, Netflix, Spotify broken
- event-stream supply chain attack via maintainer handoff on transitive dependency
- 50.6% of npm dependencies never accessed at runtime (2024 study)
- 3,000+ malicious npm packages in 2024 alone

**Thought leaders**:
- Kelsey Hightower: "Monolithic applications will be back after people discover distributed monolithic applications"
- Martin Fowler: "Almost all successful microservice stories started with a monolith that got too big"
- DHH: Basecamp 3 — 25K lines serving millions from a monolith since 2003

**Success stories for consolidation**: Stack Overflow (1.3B monthly pageviews, 9 servers, ~12ms render), Shopify (2.8M lines Ruby, modular monolith with Packwerk boundary enforcement), Etsy (PHP monolith, migrated to cloud in 9 months).

### Key Thresholds

| Signal | Threshold | Source |
|---|---|---|
| Team size for microservices to pay off | >10-15 developers | Industry consensus 2025 |
| Infrastructure cost penalty of wrong boundaries | 10x | Amazon Prime Video |
| Maintenance FTE tax | 3 FTEs for 140 services | Segment |
| Service mesh per-unit overhead | 0.5 vCPU + 50MB per 1K RPS | Istio docs |
| Batch-deploy rate (distributed monolith signal) | 90% of teams | Gremlin |
| Uber consolidation ratio | 2,200 → 70 domains (31:1) | Uber DOMA |

---

## AI-SPECIFIC CONSTRAINTS (Most Relevant Cluster)

### The Token Tax (Tier 1 — Direct Evidence)

**Claude Code context pollution data**:
- 15 built-in tools: ~10,600 tokens before any MCP servers
- 4 MCP servers: ~15K tokens. 7+ servers: ~20K+ tokens
- Real-world 7-server config: **67,300 tokens (33.7% of 200K context)** for MCP tool definitions alone
- Extreme case: 144,802 tokens consumed by MCP tools — almost nothing left for work
- GitHub MCP server alone: ~46K tokens for 27 tools (~25% of Claude Sonnet's context)
- Anthropic internally: 134K tokens consumed by tool definitions before optimization

### Tool Count vs Accuracy (Tier 1)

| Configuration | Success Rate | Source |
|---|---|---|
| 50+ tools loaded | 60% | Jenova AI |
| 5-7 relevant tools | 92% | Jenova AI |
| Context-specific injection (3-7 tools) | 85% reduction in routing errors | Jenova AI |

**Three degradation mechanisms**:
1. **Context bloat**: Tool definitions consume reasoning space. 50+ tools eat 38.5% of 200K context
2. **Attention dilution / "lost in the middle"**: Models overlook tools in middle of long lists, even with 1M windows
3. **Name confusion**: Structurally similar API names cause misrouting

### Tool Search Solution (Tier 1 — Anthropic Engineering)

When Anthropic implemented Tool Search (defer all but core tools, load on-demand):
- Token overhead cut **85%** (77K → 8.7K for 50+ tools)
- Tool Search itself adds only ~500 tokens
- Accuracy **improved**: Opus 4 went from **49% → 74%**, Opus 4.5 from **79.5% → 88.1%**

**Key insight**: Fewer tools in context simultaneously means *better* selection accuracy. This is not a convenience optimization — it is an accuracy requirement.

### ChatGPT Plugin Ecosystem (Tier 2)

- Hard limit: 3 active plugins simultaneously
- ~1,039 plugins at peak; average user utilized 2 per month
- Deprecated entirely (March-April 2024), replaced by Custom GPTs with Actions
- Actions are more granular API endpoints that can be curated per-GPT
- **Signal**: The 3-plugin limit was implicit acknowledgment that LLMs cannot effectively reason about many tools simultaneously

### Scaling Patterns for AI Tool Loading

Three approaches have emerged:

1. **Tool Search / Lazy Loading** (Anthropic): Defer tool definitions, load on-demand. 85% token reduction, accuracy improvement.
2. **Code Mode** (Cloudflare): Replace thousands of tools with 2 meta-tools (`search()` + `execute()`). 2,500 endpoints → ~1K tokens (**99.9% reduction**).
3. **RAG-MCP** (community): Embed tool definitions in vector space, retrieve semantically. 50%+ token reduction, 200%+ accuracy improvement.

All three converge: **you cannot give an agent everything. The practical limit is 5-7 active tool definitions at a time.**

### Conway's Law for AI Teams

Traditional Conway's Law assumes high human communication cost. AI agents communicate at near-zero marginal cost (shared memory, structured messages). This means:
- Module boundaries should be drawn at the point where **tool count exceeds 5-7** — not at traditional organizational boundaries
- A single agent with too many tools degrades; multiple specialized agents with 5-7 tools each perform better
- The "team structure" for AI is really the **tool routing architecture**

---

## Synthesis: What the Research Converges On

### The Universal Principle

**Every modular boundary imposes a tax (coordination, infrastructure, context cost) that must be justified by a proportional benefit (independent deployment, fault isolation, independent evolution).** This is true for both human and AI systems — but the *nature* of the tax differs.

### Human Systems Tax

- Network latency per boundary (~3-100ms)
- Operational overhead per service (0.5 vCPU + 50MB per sidecar)
- Coordination FTEs (3 FTEs for 140 services at Segment)
- Dependency divergence across repos

### AI Agent Systems Tax

- **Token cost per tool definition** (~2K tokens per tool, 46K for GitHub's 27 tools)
- **Accuracy degradation** beyond 5-7 simultaneous tools (60% vs 92% success rate)
- **Attention dilution** — models lose track of tools in middle of long lists
- **Name confusion** between structurally similar tool names

### The Key Insight for Plugin Ecosystems

The research suggests the correct distinction is not "how many plugins exist" but "how many are active simultaneously":

- **Installation count can be large** — VSCode has 60K extensions, Terraform has 3K providers. The ecosystem scales through discovery and lazy loading.
- **Active count must be small** — 5-7 tool definitions in context at a time for AI agents, process isolation for traditional plugins.
- **The infrastructure that bridges the gap** — lazy loading, tool search, activation events, gRPC boundaries — is the actual engineering problem. Without it, you hit either the "nano-service" overhead (too many small things) or the "big ball of mud" (everything coupled). With it, modularity scales.

### Unanswered Questions

1. What is Demarch's actual token cost per plugin load? (interstat should have this data)
2. Does the monorepo working directory mask friction that agents in other contexts would experience?
3. Are the routing/glue plugins (interlock, interpath, intermap) genuinely independent concerns, or are they configurations of a single "agent coordination" capability?
4. What is the Uber DOMA equivalent for a 49-plugin AI ecosystem? Would consolidating into ~10 domains work?
