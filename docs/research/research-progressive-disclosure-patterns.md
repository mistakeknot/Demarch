# Progressive Disclosure Patterns for AI Agent Memory Systems

**Research Date**: 2026-02-17
**Context**: Evaluating tiered memory retrieval approaches for intermem (Claude Code plugin)
**Goal**: Avoid dumping all memory into context when only some is relevant

---

## Executive Summary

Progressive disclosure in agent memory systems aims to balance context completeness against token efficiency by revealing information in layers—showing summaries first, detailed content on demand. Three approaches emerge from current research and practice:

1. **Multi-file tiers** (index → summary → detail): Proven in software documentation, 40–60% token reduction, requires explicit Read calls
2. **Collapsible sections** (HTML `<details>`, comments): NOT effective for LLMs—they parse raw text, not rendered output
3. **MCP-based retrieval** (query API): Most flexible, 50–100 MB overhead, enables dynamic context assembly

**Key finding**: Claude Code auto-loads ONLY `CLAUDE.md` and `AGENTS.md` exactly—no pattern matching. Multi-file strategies require agents to explicitly Read additional tiers, which works but relies on agent discipline. MCP tools offer the most control but add infrastructure complexity.

---

## Background: The Context Efficiency Problem

### Token Cost Reality

From LLM pricing research ([LLM Cost Comparison](https://www.vellum.ai/llm-cost-comparison), [Silicon Data 2026](https://www.silicondata.com/blog/llm-cost-per-token)):

- **Poorly tuned retrieval** (e.g., fetching 10 chunks instead of 2) inflates input tokens by 3–4×
- **Index-based approaches** reduce input token bloat by **40–60%** compared to full documentation injection
- **Caching static content** (system prompts, boilerplate) prevents repeated re-tokenization
- At production scale, even fractional per-interaction savings translate to thousands of dollars monthly

### Current State: AGENTS.md as Flat File

- intermem promotes stable auto-memory entries to `AGENTS.md` and `CLAUDE.md`
- Claude Code loads these files as plain text at session start—no query API
- Current state: `AGENTS.md` ~200 lines, loaded entirely into every session
- Problem: As memory accumulates, irrelevant context pollutes the prompt

---

## Approach 1: Multi-File Tiers

### Architecture

Split documentation into indexed layers:

```
AGENTS-index.md       → Section titles + one-line summaries (always loaded)
AGENTS-summary.md     → Paragraph-level summaries per section
AGENTS-detail.md      → Full implementation notes, gotchas, examples
AGENTS.md             → Legacy compatibility or meta-index
```

Alternative pattern (from [OpenDevise](https://opendevise.com/blog/standard-project-structure-for-docs/)):

```
docs/
  index.adoc          → Public API gateway
  quickstart/
    index.adoc        → Feature overview
    detail.adoc       → Deep dive
  architecture/
    index.adoc
    modules.adoc
```

### Claude Code Auto-Load Behavior

**Critical finding** from [Claude Code docs](https://code.claude.com/docs/en/skills) and [builder.io guide](https://www.builder.io/blog/claude-md-guide):

- Claude Code looks for **exactly** `CLAUDE.md` and `AGENTS.md` (case-sensitive)
- **Nested `CLAUDE.md` files** in subdirectories ARE auto-loaded when Claude accesses files in that directory
- **No pattern matching**: `AGENTS-*.md` or `CLAUDE-summary.md` are NOT auto-loaded
- `--add-dir` directories do NOT auto-load their `CLAUDE.md` unless `CLAUDE_CODE_ADDITIONAL_DIRECTORIES_CLAUDE_MD=1` is set

### Practical Implications

To implement multi-file tiers:

1. **Index in AGENTS.md**: Keep AGENTS.md as a thin table-of-contents with pointers to detail files
2. **Agent discipline required**: Agents must explicitly `Read(AGENTS-detail.md)` when drilling down
3. **Directory-scoped loading**: Use nested `AGENTS.md` in subdirectories for automatic context expansion when working in that area

**Example AGENTS.md index pattern**:

```markdown
# Project Memory (Quick Reference)

## Git Workflow
See `docs/memory/git-workflow.md` for full details.
- Always use signed commits
- Pre-commit hook runs linters

## Build System
See `docs/memory/build-system.md`
- Run `uv run` not `pip install`
- Build outputs to `dist/`

## MCP Integration
See `docs/memory/mcp-integration.md`
- 11 tools via interlock plugin
- Unix socket preferred, TCP fallback
```

### Token Efficiency

From [AlphaIterations LLM Cost Guide](https://medium.com/@alphaiterations/llm-cost-estimation-guide-from-token-usage-to-total-spend-fba348d62824):

- **Index file**: ~50–150 tokens (section headers + one-liners)
- **Full detail**: ~1,500–3,000 tokens (typical AGENTS.md)
- **Savings**: 90–95% token reduction for sessions that don't need full context
- **Cost**: Agents must remember to drill down when needed

### Real-World Examples

Projects using tiered documentation ([SitePoint](https://www.sitepoint.com/organize-project-files/), [WebDevSimplified React](https://blog.webdevsimplified.com/2022-07/react-folder-structure/)):

- **README → docs/** pattern: Top-level overview linked to deeper tiers
- **index.js as public API**: Each feature folder has `index.js` exposing only public methods
- **Layered architecture**: UI layer separate from Data layer, each with own docs
- **Hierarchical modules**: Sub-folders with sub-modules, each self-documented

### When Agents Drill Into Deeper Tiers

Triggering conditions for expanding to detail docs:

1. **Explicit user mention**: "Check the memory about git workflow"
2. **Error/conflict**: Pre-commit hook failure → read git-workflow.md for troubleshooting
3. **Contextual cues**: Editing `.github/workflows/` → auto-read CI/CD docs if nested `CLAUDE.md` exists there
4. **Agent uncertainty**: "I don't have enough context for this task" → proactive Read of detail files

---

## Approach 2: Collapsible Sections

### Mechanisms Considered

- **HTML `<details>` tag**: Expandable disclosure widget
- **HTML comments**: `<!-- hidden content -->`
- **Markdown fold markers**: Custom comment syntax

### LLM Visibility Analysis

From [MDN `<details>` docs](https://developer.mozilla.org/en-US/docs/Web/HTML/Reference/Elements/details) and [arXiv Hidden-Comment Injection](https://arxiv.org/html/2602.10498):

**Critical finding**: **Collapsible sections DO NOT hide content from LLMs**

- LLMs parse **raw source text**, not rendered HTML
- HTML `<details>` content is fully visible in raw markup regardless of `open` attribute
- HTML comments `<!-- ... -->` are fully visible to LLMs and pose a **security risk** (prompt injection vector)
- "The `open` attribute only affects visual rendering in browsers—it does not strip or exclude the enclosed text from the document."

### Security Implications

From [arXiv paper on Hidden-Comment Injection](https://arxiv.org/html/2602.10498):

> "An attacker can introduce hidden text into a skill document without changing its visible 'clean' content. LLMs were influenced by malicious instructions embedded in a hidden HTML comment appended to an otherwise legitimate Skill document."

**Recommendation**: Developers should **not rely on hidden regions** (HTML comments, CSS `display:none`) being harmless—the model-facing text should be reviewable, or hidden content should be stripped before entering the model context.

### Markdown Processing

From [Markdown for LLMs guide](https://copymarkdown.com/markdown-for-llm/) and [Crawl4AI docs](https://docs.crawl4ai.com/core/markdown-generation/):

- LLMs ignore `.md` files during web crawling ([Longato analysis](https://www.longato.ch/llm-md-files/))—GPTBot, ClaudeBot prioritize HTML-rendered content
- Markdown is valuable as **authoring format**, not as a visibility filter
- **No lazy-loading mechanism** in Markdown—entire file is consumed as text

### Verdict on Collapsible Sections

**Not viable** for progressive disclosure with LLMs:

- ❌ `<details>` tag does not hide content from LLMs
- ❌ HTML comments are visible and pose security risks
- ❌ No Markdown-native mechanism for collapsed content
- ✅ Only useful for **human-readable documentation** rendered in browsers

---

## Approach 3: MCP-Based Retrieval

### Architecture

Expose intermem as an MCP server with query tools:

```json
{
  "mcpServers": {
    "intermem": {
      "type": "stdio",
      "command": "${CLAUDE_PLUGIN_ROOT}/bin/intermem-mcp",
      "env": {
        "INTERMEM_DB": "${PROJECT_ROOT}/.intermem/metadata.db"
      }
    }
  }
}
```

**Tools exposed**:
- `get_memory(query, detail_level)` → Returns matching entries at requested verbosity
- `search_memory(keywords, limit)` → Semantic or keyword-based search
- `list_topics()` → List available memory categories
- `get_topic_summary(topic)` → Summary of a specific area

### MCP Server Overhead

From [Claude Code MCP setup guide](https://code.claude.com/docs/en/mcp) and [KSRed MCP guide](https://www.ksred.com/claude-code-as-an-mcp-server-an-interesting-capability-worth-understanding/):

**Resource usage**:
- Claude Code normal operation: 200–500 MB memory
- MCP server mode: **+50–100 MB overhead**
- Long-running process handling multiple client connections
- Token warning at **10,000 tokens** per tool output (default max: 25,000)

**Setup complexity**:
- TypeScript/Node.js or Python MCP SDK
- Zod schema validation for tool arguments
- DSN configuration in `plugin.json` or `.mcp.json`
- Tool naming: `mcp__plugin_<name>_<server>__<tool>`

### Implementation Example (from Interlock)

Interlock plugin demonstrates MCP integration ([interlock plugin.json](https://github.com/mistakeknot/interlock/blob/main/.claude-plugin/plugin.json)):

```json
{
  "mcpServers": {
    "interlock": {
      "type": "stdio",
      "command": "${CLAUDE_PLUGIN_ROOT}/bin/launch-mcp.sh",
      "args": [],
      "env": {
        "INTERMUTE_SOCKET": "/var/run/intermute.sock",
        "INTERMUTE_URL": "http://127.0.0.1:7338"
      }
    }
  }
}
```

**Interlock provides 11 tools**: `reserve_files`, `release_files`, `check_conflicts`, `my_reservations`, `send_message`, `fetch_inbox`, `list_agents`, `negotiate_release`, `respond_to_release`, etc.

### MCP Memory Plugins in the Wild

From GitHub search ([claude-memory topic](https://github.com/topics/claude-memory)):

#### 1. **claude-mem** ([thedotmack](https://github.com/thedotmack/claude-mem))
- Automatically captures tool usage, generates semantic summaries
- Compresses with agent-sdk, injects into future sessions
- Beta: "Endless Mode" biomimetic memory architecture

#### 2. **mcp-knowledge-graph** ([shaneholloman](https://github.com/shaneholloman/mcp-knowledge-graph))
- Knowledge graph persistence across conversations
- Named databases (work, personal, health)
- Automatic project-local memory via `.aim` directories

#### 3. **claude-memory-plugin** ([GaZmagik](https://github.com/GaZmagik/claude-memory-plugin))
- Semantic search using embeddings
- Contextual gotcha injection via hooks
- Directed graph relationships between memories

#### 4. **git-notes-memory** ([mourad-ghafiri](https://github.com/mourad-ghafiri/git-notes-memory))
- Git-based knowledge graph using `git notes`
- Branch-aware, survives across branches
- **Token-efficient tiered retrieval** (relevant to our use case)

#### 5. **Official MCP Memory Server** ([modelcontextprotocol](https://github.com/modelcontextprotocol/servers))
- `@modelcontextprotocol/server-memory`
- Knowledge graph-based persistence in JSONL
- Tools: add, search, update, delete memories

### MCP + intermem Integration

intermem already has `metadata.db` (SQLite) with:
- Entry provenance
- Citation extraction
- Confidence scoring
- Audit trail

**Potential MCP tools**:

```python
# Tool 1: Query memory entries
mcp__plugin_intermem_intermem__query_memory(
    keywords: List[str],
    min_confidence: float = 0.3,
    limit: int = 5
) -> List[MemoryEntry]

# Tool 2: Get topic summary
mcp__plugin_intermem_intermem__summarize_topic(
    topic: str  # e.g., "git-workflow", "mcp-integration"
) -> str

# Tool 3: Validate citation
mcp__plugin_intermem_intermem__check_citation(
    entry_hash: str
) -> CitationStatus

# Tool 4: List available topics
mcp__plugin_intermem_intermem__list_topics() -> List[str]
```

**Query strategy**:

1. Agent sees index in auto-loaded `AGENTS.md`: "Git workflow, MCP integration, build system"
2. Agent calls `query_memory(keywords=["git", "pre-commit"], limit=3)`
3. MCP server queries `metadata.db`, returns top 3 entries with confidence scores
4. Agent receives relevant context without full dump

### Interaction with Auto-Loaded Files

From [MCP + RAG discussion](https://www.cognee.ai/blog/deep-dives/model-context-protocol-cognee-llm-memory-made-simple):

**Complementary, not replacement**:

- `CLAUDE.md` / `AGENTS.md`: High-level orientation, always-available facts
- MCP tools: On-demand retrieval for specific queries
- "RAG can be used to supplement retrieval-augmented generation... searching the database as a tool rather than passing the retriever in every LLM invocation allows for more strategic use."

**Best practice**:

- Keep `AGENTS.md` as a **topic directory** with one-liners
- Use MCP tools to **lazy-load details** on demand
- Avoid duplicating content between static files and MCP-retrieved data

### Docker MCP Toolkit (Reducing Setup Overhead)

From [Docker MCP Toolkit blog](https://www.docker.com/blog/add-mcp-servers-to-claude-code-with-mcp-toolkit/):

- 200+ pre-built, containerized MCP servers
- One-click deployment
- Automatic credential handling
- No dependency conflicts, consistent across platforms

**For intermem**: Could package as Docker container to simplify cross-project setup

---

## Academic & Industry Memory Systems

### MemGPT / Letta

From [MemGPT paper](https://arxiv.org/abs/2310.08560) and [Letta docs](https://docs.letta.com):

**Architecture**:
- **Tier 1 (in-context)**: Core memory blocks (persona, user info)—analogous to RAM
- **Tier 2 (out-of-context)**: Archival memory, recall memory—analogous to disk

**Self-editing memory**:
- Agents control data movement between tiers via function calls
- Tools: `memory_replace`, `memory_insert`, `archival_memory_insert`, `conversation_search`

**Key insight**: "Virtual context management" creates illusion of unlimited memory while working within fixed context limits

**Evaluation**: Tested on document analysis (large docs exceeding context window) and multi-session chat (long-term user interaction)

### FadeMem: Biologically-Inspired Forgetting

From [FadeMem paper](https://arxiv.org/abs/2601.18642) and [co-r-e summary](https://www.co-r-e.com/method/agent-memory-forgetting):

**Problem**: LLMs lack selective forgetting → catastrophic forgetting at context boundaries or information overload within them

**Solution**: Dual-layer memory with **adaptive exponential decay**:

- **Long-term Memory Layer (LML)**: High-importance memories, slow decay (half-life ~11.25 days)
- **Short-term Memory Layer (SML)**: Low-importance memories, rapid decay (half-life ~5.02 days)

**Decay function**: `R = e^(-t/S)` where R is retention, t is time, S is strength

**Importance-based decay**: Higher importance → slower decay rate λ

**Memory consolidation**: Accessing a memory increases its strength (mimicking human reinforcement)

**Performance**: Outperforms Mem0 while using **45% less storage**

**Biological inspiration**: Ebbinghaus forgetting curve (1880s)—memory decays exponentially, but important/frequently accessed memories persist longer

### A-MEM: Zettelkasten-Inspired Agent Memory

From [A-MEM paper](https://arxiv.org/abs/2502.12110):

**Structure**: Note-based memory units with:
- LLM-generated keywords and tags
- Contextual descriptions
- Dynamically constructed links to semantically related memories

**Memory evolution**: New experiences retroactively refine context and attributes of existing notes, mirroring human associative learning

### MemoryBank: Dynamic Memory with Forgetting Curve

From [MemoryBank paper](https://arxiv.org/pdf/2305.10250):

**Forgetting mechanism**: Inspired by Ebbinghaus curve
- Memory strength S increases by 1 when recalled
- Time t resets to 0 on access
- Decay probability based on `R = e^(-t/S)`

**User portrait building**: Progressively refines understanding of user personality through continuous interaction

### ICLR 2026 MemAgents Workshop

From [workshop proposal](https://openreview.net/pdf?id=U51WxL382H):

**Open challenges**:
- Catastrophic forgetting
- Retrieval efficiency
- Memory structure choices (structured vs. unstructured, symbolic vs. neural, graph vs. vector)
- Interfaces between external and in-weights stores

**Key competencies**:
1. **Accurate Retrieval**: Needle-in-haystack extraction
2. **Test-Time Learning**: In-context adaptation
3. **Long-Range Understanding**: Global summarization
4. **Conflict Resolution**: Updating prior facts with new evidence

### RAG Evolution: From Retrieval to "Context Engine"

From [RAGFlow 2025 review](https://ragflow.io/blog/rag-review-2025-from-rag-to-context) and [Squirro RAG in 2026](https://squirro.com/squirro-blog/state-of-rag-genai):

**Progressive disclosure techniques**:

- **Layered Query Retrieval (LQR)**: Hierarchical planning over multi-hop questions
- **Sparse Context Selection**: Efficient sparse reformulations for recall + speed
- **RQ-RAG**: Decomposes multi-hop queries into latent sub-questions
- **GMR (Generative Multi-hop Retrieval)**: Autoregressively formulates complex queries
- **Adaptive retrieval toggling**: Toggle retrieval based on query uncertainty, avoid unnecessary context

**2025–2026 shift**: RAG evolving from "specific pattern" to "Context Engine" with intelligent retrieval

**Agentic RAG**: Using agent planning/reflection to enhance RAG process itself

**Multimodal contexts**: Emerging demand for systems understanding text, images, video simultaneously

---

## Tiered Memory Taxonomies

From [Agent Memory Paper List](https://github.com/Shichun-Liu/Agent-Memory-Paper-List) and [Memory Survey](https://arxiv.org/abs/2512.13564):

### Functional Taxonomy

- **Factual memory**: Domain knowledge, facts, trivia
- **Experiential memory**: Task history, past interactions
- **Working memory**: Current session context, scratchpad

### Temporal Taxonomy

- **Immediate context**: Last N turns in conversation
- **Session memory**: Current interaction episode
- **Long-term memory**: Cross-session persistence

### Structural Taxonomy

- **Flat**: Single store (vector DB or key-value)
- **Tiered**: Hierarchical (working → episodic → archival)
- **Graph-based**: Relational links between memories
- **Hybrid**: Vector + graph (e.g., A-MEM, Cognee)

### Retrieval Strategy Taxonomy

- **Recency-based**: Time decay (Ebbinghaus curve)
- **Similarity-based**: Vector embeddings, cosine distance
- **Importance-based**: Salience scoring, user-tagged priority
- **Frequency-based**: Access count, reinforcement on retrieval
- **Hybrid**: Mix-of-Experts gating, learned weights

---

## Comparison Table: Three Approaches for intermem

| Aspect | Multi-File Tiers | Collapsible Sections | MCP-Based Retrieval |
|--------|------------------|----------------------|---------------------|
| **Token efficiency** | 90–95% reduction for sessions not needing full context | 0% (LLMs see all content) | 40–60% reduction via targeted queries |
| **Auto-load behavior** | Only `AGENTS.md` and `CLAUDE.md` auto-loaded; detail files require explicit Read | All content in single file, fully loaded | Index in `AGENTS.md`, details fetched on demand via tools |
| **Agent discipline required** | High—must remember to drill down | None (but ineffective) | Low—tools are discoverable, prompts guide usage |
| **Implementation complexity** | Low—just file splits + doc conventions | Very low (but doesn't work) | Medium—MCP server + schema + tool registration |
| **Resource overhead** | None (static files) | None | +50–100 MB for MCP server process |
| **Dynamic context assembly** | Manual via Read calls | Not possible | Yes—query-driven, adaptive |
| **Interaction with existing metadata.db** | None—separate from SQLite state | None | Direct—queries use existing DB |
| **Graceful degradation** | Agents see index, can choose to ignore detail files | All context always present | Agents see index, tools available but optional |
| **Real-world examples** | Software docs (OpenDevise), React projects | None for LLMs (only browser UIs) | claude-mem, mcp-knowledge-graph, git-notes-memory |
| **Best for** | Projects with stable, categorized memory | Not recommended | Projects with large, queryable memory corpus |

---

## Recommendations for intermem

### Short-Term (Phase 1): Multi-File Tiers

**Rationale**: Low complexity, immediate token savings, no infrastructure changes

**Implementation**:

1. **AGENTS.md as index**:
   ```markdown
   # Project Memory Index

   ## Git Workflow
   - Signed commits required
   - Pre-commit hook runs linters
   - See `docs/memory/git-workflow.md` for troubleshooting

   ## MCP Integration
   - 11 tools via interlock
   - See `docs/memory/mcp-setup.md` for configuration
   ```

2. **Detail files in docs/memory/**:
   - `docs/memory/git-workflow.md` (full gotchas, examples)
   - `docs/memory/mcp-setup.md` (tool descriptions, schemas)
   - `docs/memory/build-system.md` (commands, flags, troubleshooting)

3. **Promotion target**: intermem promotes to detail files, updates index with one-liners

4. **Agent prompting**: Add to `CLAUDE.md`:
   ```markdown
   When you need detailed context, check the index in AGENTS.md
   for pointers to memory files in docs/memory/. Use the Read tool
   to access them on demand.
   ```

**Pros**:
- ✅ Immediate 90–95% token reduction for sessions not needing full context
- ✅ No MCP overhead
- ✅ Works with existing file-based workflow
- ✅ Graceful: agents see index, can drill down as needed

**Cons**:
- ❌ Relies on agent discipline to drill down
- ❌ No semantic search—agents must guess which file to read
- ❌ Manual updates to index when promoting new entries

### Medium-Term (Phase 2): MCP Retrieval Layer

**Rationale**: Once memory corpus is large (500+ entries), query-driven retrieval becomes essential

**Implementation**:

1. **MCP server** (TypeScript or Python):
   - Tool: `query_memory(keywords, min_confidence, limit)`
   - Tool: `list_topics()`
   - Tool: `summarize_topic(topic)`
   - Backend: Queries `metadata.db` using FTS5 or embedding similarity

2. **Keep index in AGENTS.md**: "For detailed memory, use `/intermem:query <keywords>`"

3. **Promotion flow**: intermem continues writing to detail files (for human readability) but also indexes into `metadata.db` for MCP queries

4. **Hybrid approach**: Static index for overview, MCP for search

**Pros**:
- ✅ Semantic search across entire memory corpus
- ✅ Agents don't need to guess filenames
- ✅ Confidence scoring filters stale entries
- ✅ Scales to thousands of entries

**Cons**:
- ❌ +50–100 MB memory overhead
- ❌ MCP setup complexity (schema, tool registration)
- ❌ Requires maintaining both detail files (for humans) and DB index (for MCP)

### Long-Term (Phase 3): Adaptive Decay + Knowledge Graph

**Rationale**: Align with state-of-the-art memory research (FadeMem, A-MEM)

**Features**:

1. **Ebbinghaus-inspired decay**:
   - Track last-accessed timestamp per entry
   - Decay confidence score over time: `R = e^(-t/S)`
   - Boost confidence on retrieval (reinforcement)

2. **Knowledge graph links**:
   - Extract semantic relationships between entries
   - "Git workflow" → "Pre-commit hooks" → "Linter config"
   - Multi-hop queries: "How does MCP relate to build system?"

3. **Proactive retrieval**:
   - Pre-edit hook checks file path, auto-queries relevant memory
   - "Editing `.github/workflows/ci.yml` → fetch CI/CD memory"

**Pros**:
- ✅ Aligned with academic best practices
- ✅ Automatic relevance decay prevents stale facts
- ✅ Relational queries enable complex context assembly

**Cons**:
- ❌ High implementation complexity
- ❌ Requires LLM calls for link generation and decay tuning
- ❌ May be overkill for small projects (<100 entries)

---

## Key Findings Summary

1. **Claude Code auto-loads ONLY `CLAUDE.md` and `AGENTS.md` exactly**—no pattern matching for `AGENTS-*.md` variants. Multi-file strategies require explicit Read calls.

2. **Collapsible sections (HTML `<details>`, comments) DO NOT hide content from LLMs**—they parse raw source text, not rendered output. Not viable for progressive disclosure.

3. **Multi-file tiers offer 90–95% token reduction** for sessions not needing full context, with low implementation complexity. Requires agent discipline to drill down.

4. **MCP-based retrieval adds +50–100 MB overhead** but enables semantic search, dynamic context assembly, and scales to large memory corpora. Best for 500+ entries.

5. **Token efficiency research shows 40–60% reduction** via indexed retrieval vs. full documentation. At scale, this translates to significant cost savings.

6. **Biological forgetting mechanisms (Ebbinghaus curve)** are state-of-the-art in agent memory—FadeMem achieves 45% storage reduction vs. Mem0 while improving relevance.

7. **RAG is evolving into "Context Engines"** with layered query retrieval (LQR), adaptive toggling, and multi-hop reasoning—progressive disclosure is a core research direction.

8. **Real-world MCP memory plugins** (claude-mem, git-notes-memory, mcp-knowledge-graph) demonstrate token-efficient tiered retrieval patterns already in production.

9. **Hybrid approaches win**: Static index in `AGENTS.md` for orientation + MCP tools for on-demand retrieval balances simplicity and power.

10. **Interlock plugin is a reference model** for intermem MCP integration—Go binary, stdio transport, 11 tools, ~100 MB overhead in practice.

---

## Sources

### Claude Code Documentation
- [Claude Code MCP Integration](https://code.claude.com/docs/en/mcp)
- [How to Write a Good CLAUDE.md](https://www.builder.io/blog/claude-md-guide)
- [CLAUDE.md Files: Customizing Claude Code](https://claude.com/blog/using-claude-md-files)
- [AGENTS.md Convention](https://pnote.eu/notes/agents-md/)

### LLM Memory Research (2025–2026)
- [MemGPT: Towards LLMs as Operating Systems](https://arxiv.org/abs/2310.08560)
- [FadeMem: Biologically-Inspired Forgetting](https://arxiv.org/abs/2601.18642)
- [A-MEM: Agentic Memory for LLM Agents](https://arxiv.org/abs/2502.12110)
- [Memory in the Age of AI Agents Survey](https://arxiv.org/abs/2512.13564)
- [ICLR 2026 MemAgents Workshop Proposal](https://openreview.net/pdf?id=U51WxL382H)
- [Agent Memory Paper List (GitHub)](https://github.com/Shichun-Liu/Agent-Memory-Paper-List)

### MCP & Memory Plugins
- [Model Context Protocol Examples](https://modelcontextprotocol.io/examples)
- [MCP + Cognee: LLM Memory Made Simple](https://www.cognee.ai/blog/deep-dives/model-context-protocol-cognee-llm-memory-made-simple)
- [MCP Servers Repository (GitHub)](https://github.com/modelcontextprotocol/servers)
- [claude-mem Plugin](https://github.com/thedotmack/claude-mem)
- [mcp-knowledge-graph Plugin](https://github.com/shaneholloman/mcp-knowledge-graph)
- [claude-memory-plugin](https://github.com/GaZmagik/claude-memory-plugin)
- [git-notes-memory Plugin](https://github.com/mourad-ghafiri/git-notes-memory)

### RAG & Context Efficiency
- [RAG 2025 Year-End Review: From RAG to Context](https://ragflow.io/blog/rag-review-2025-from-rag-to-context)
- [RAG in 2026: Bridging Knowledge and Generative AI](https://squirro.com/squirro-blog/state-of-rag-genai)
- [Retrieval-Augmented Generation Survey (arXiv)](https://arxiv.org/html/2506.00054v1)
- [RAG Prompt Engineering Guide](https://www.promptingguide.ai/research/rag)

### Token Cost & LLM Pricing
- [LLM Cost Per Token 2026 Guide](https://www.silicondata.com/blog/llm-cost-per-token)
- [LLM Cost Estimation Guide](https://medium.com/@alphaiterations/llm-cost-estimation-guide-from-token-usage-to-total-spend-fba348d62824)
- [LLM Cost Comparison (Vellum)](https://www.vellum.ai/llm-cost-comparison)

### HTML/Markdown & LLM Visibility
- [HTML `<details>` Element (MDN)](https://developer.mozilla.org/en-US/docs/Web/HTML/Reference/Elements/details)
- [Hidden-Comment Injection in LLM Agents (arXiv)](https://arxiv.org/html/2602.10498)
- [Markdown for LLMs Guide](https://copymarkdown.com/markdown-for-llm/)
- [Do LLMs Use .md Files? Analysis of Crawl Behaviour](https://www.longato.ch/llm-md-files/)

### Documentation Patterns
- [Standard Project Structure for Docs (OpenDevise)](https://opendevise.com/blog/standard-project-structure-for-docs/)
- [How to Organize Project Files (SitePoint)](https://www.sitepoint.com/organize-project-files/)
- [React Project Structure (WebDevSimplified)](https://blog.webdevsimplified.com/2022-07/react-folder-structure/)

### Ebbinghaus Forgetting Curve
- [Forgetting Curve (Wikipedia)](https://en.wikipedia.org/wiki/Forgetting_curve)
- [FadeMem: Why Teaching AI to Forget](https://www.co-r-e.com/method/agent-memory-forgetting)
- [MemoryBank: Enhancing LLMs with Long-Term Memory](https://arxiv.org/pdf/2305.10250)

---

## Next Steps for intermem

1. **Phase 1 (Immediate)**: Implement multi-file tier structure
   - Split `AGENTS.md` into index + detail files
   - Update promotion logic to write to `docs/memory/<topic>.md`
   - Add index-update step after promotion

2. **Phase 2 (After 500+ entries)**: Add MCP query layer
   - Build `intermem-mcp` server (TypeScript or Python)
   - Expose `query_memory()`, `list_topics()`, `summarize_topic()` tools
   - Query against existing `metadata.db`

3. **Phase 3 (Research)**: Experiment with adaptive decay
   - Track last-accessed timestamp per entry
   - Implement Ebbinghaus-style confidence decay
   - Evaluate impact on retrieval relevance

4. **Monitoring**: Add to interstat plugin
   - Track Read calls to detail files (are agents drilling down?)
   - Track MCP tool usage (which queries are common?)
   - Measure token savings via context length before/after

---

**End of Research Document**
