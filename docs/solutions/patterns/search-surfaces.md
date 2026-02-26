# Search and Embedding Surfaces

**Bead:** iv-dxsow

Seven MCP servers and libraries provide overlapping search and embedding capabilities across the Interverse. This document maps each surface, its tools, and when to use it.

## Decision Tree

```
What are you searching for?
│
├─ Code in the current project
│  ├─ By meaning/concept → tldr-swinton:semantic (needs semantic_index first)
│  ├─ By AST pattern     → tldr-swinton:structural_search
│  ├─ By symbol/function → tldr-swinton:context or intermap:impact_analysis
│  └─ By file structure  → intermap:code_structure or tldr-swinton:structure
│
├─ Code across projects (monorepo)
│  ├─ Cross-project deps → intermap:cross_project_deps
│  └─ Architecture patterns → intermap:detect_patterns
│
├─ Cached content from prior sessions
│  ├─ By embedding similarity → intersearch:embedding_query
│  ├─ By content hash         → intercache:cache_lookup
│  └─ Session diffs           → intercache:session_diff
│
├─ External web/research
│  ├─ Academic papers (arXiv)  → interject:interject_scan (source: arxiv)
│  ├─ General web search       → exa-mcp-server (via interflux)
│  └─ Hacker News/GitHub       → interject:interject_scan
│
├─ Research discoveries (ambient)
│  ├─ What's in my inbox?      → interject:interject_inbox
│  ├─ Search past discoveries  → interject:interject_search
│  └─ Trigger a new scan       → interject:interject_scan
│
└─ Documentation sections
   └─ Classify/extract sections → interserve:classify_sections
```

## Surface Catalog

### 1. tldr-swinton (code analysis)

**When:** You need to understand code structure, find symbols, or search by meaning within a single project.

| Tool | What it does |
|------|-------------|
| `semantic` | Meaning-based code search ("find error handling") |
| `semantic_index` | Build embedding index (run once before `semantic`) |
| `structural_search` | AST pattern matching via ast-grep |
| `context` | Get call graph around a function |
| `impact` | Reverse call graph (who calls this?) |
| `extract` | File analysis (functions, classes, imports) |
| `structure` | Project-wide directory + symbol overview |

**Embedding model:** Configurable (faiss with Ollama or colbert). Run `semantic_index()` before `semantic()`.

### 2. intermap (project mapping)

**When:** You need cross-project dependency graphs, architecture pattern detection, or git-aware change impact analysis.

| Tool | What it does |
|------|-------------|
| `code_structure` | Functions/classes/imports (Python bridge) |
| `impact_analysis` | Reverse call graph for a function |
| `change_impact` | Which tests to run for changed files |
| `cross_project_deps` | Monorepo dependency graph |
| `detect_patterns` | Architectural patterns (MCP tools, HTTP handlers, etc.) |
| `live_changes` | Git-diff annotated with affected symbols |
| `project_registry` | Scan workspace projects |
| `agent_map` | Which agents are working on which projects |

**Embedding model:** None. Uses AST parsing and git analysis.

### 3. intercache (cross-session cache)

**When:** You want to reuse analysis results across sessions or find similar content from prior work.

| Tool | Server | What it does |
|------|--------|-------------|
| `cache_lookup` | intercache | Find cached content by SHA256 hash |
| `cache_store` | intercache | Store content in content-addressed blob store |
| `embedding_index` | intersearch | Build embedding index over project files |
| `embedding_query` | intersearch | Find similar content by embedding |
| `session_track` | intercache | Track what this session has produced |
| `session_diff` | intercache | Compare current session with prior sessions |
| `cache_warm` | intercache | Pre-load cache for expected content |

**Embedding model:** nomic-ai/nomic-embed-text-v1.5 (768 dims, via intersearch).

### 4. interject (ambient discovery)

**When:** You want to discover relevant external content (papers, blog posts, repos) or search past discoveries.

| Tool | What it does |
|------|-------------|
| `interject_scan` | Trigger discovery scan (arXiv, HN, GitHub, Anthropic) |
| `interject_inbox` | View pending discoveries |
| `interject_search` | Semantic search over past discoveries |
| `interject_promote` | Promote a discovery to actionable |
| `interject_dismiss` | Dismiss irrelevant discovery |

**Embedding model:** Uses intersearch (all-MiniLM-L6-v2) for relevance scoring.

### 5. intersearch (shared library)

**When:** You're building a plugin that needs embedding or Exa search capabilities. Not an MCP server — a Python library.

- `intersearch.embeddings` — sentence-transformers wrapper (all-MiniLM-L6-v2)
- `intersearch.exa` — async Exa web search with highlight extraction
- Dependency for: interject, intercache

### 6. interserve (section classifier)

**When:** You need to classify or extract sections from markdown documents for delegation to Codex agents.

| Tool | What it does |
|------|-------------|
| `extract_sections` | Split markdown into titled sections |
| `classify_sections` | Assign domain labels to sections |
| `codex_query` | Query Codex about a topic |

**Embedding model:** None. Uses keyword scoring for classification.

### 7. exa-mcp-server (web search)

**When:** You need general web search results. External tool, not owned by Demarch.

- Accessed via interflux's MCP server configuration
- Requires `EXA_API_KEY` environment variable
- Installed via `npx -y exa-mcp-server`

## Overlap Analysis

| Capability | Primary | Secondary |
|-----------|---------|-----------|
| Semantic code search | tldr-swinton:semantic | — |
| Structural code search | tldr-swinton:structural | — |
| Call graph / impact | intermap:impact_analysis | tldr-swinton:impact |
| Code structure overview | tldr-swinton:structure | intermap:code_structure |
| Cross-project deps | intermap:cross_project | — |
| Embedding similarity | intersearch:embedding_query | — |
| Web search | exa-mcp-server | — |
| Research discovery | interject:scan/search | — |
| Section classification | interserve:classify | — |

**Key overlaps:**
- `impact_analysis` exists in both intermap and tldr-swinton. intermap uses Python AST analysis; tldr-swinton uses its own extraction. Use intermap for cross-file call graphs, tldr-swinton for single-function context.
- `code_structure` exists in both. intermap delegates to Python bridge; tldr-swinton extracts inline. Use tldr-swinton for quick single-file overview (cheaper), intermap for project-wide analysis.

## Embedding Standardization

All plugins use **all-MiniLM-L6-v2** (384 dimensions) from sentence-transformers. This was a deliberate choice to ensure embedding compatibility across:
- intercache (content-addressed cache)
- interject (discovery relevance scoring)
- intersearch (shared embedding library)

tldr-swinton supports multiple backends (faiss/colbert) and may use different models. Its embeddings are not cross-compatible with the intersearch family.
