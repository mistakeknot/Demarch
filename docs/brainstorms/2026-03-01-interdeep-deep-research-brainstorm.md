# interdeep — Deep Research Plugin Brainstorm

**Date:** 2026-03-01
**Status:** Draft
**Related:** Pollard (apps/autarch/internal/pollard/), interflux flux-research, intersearch

## What We're Building

**interdeep** — a new Interverse plugin that provides autonomous deep research capabilities accessible from any MCP-compatible agent (Claude Code, Gemini CLI, Codex, etc.). Similar to OpenAI's "Deep Research" and Autarch's Pollard, but as a standalone plugin in the Interverse ecosystem.

### Core Concept

interdeep provides **MCP tools + orchestration skills** — the host AI (Claude/Gemini/Codex) does the reasoning, planning, and synthesis. The plugin provides the search, extraction, and output formatting capabilities. This makes it model-agnostic: the research quality scales with whatever model the user is running.

### User Experience

Interactive research session that progressively builds a structured report:
1. User triggers `/interdeep:research "query"`
2. Plugin decomposes the query, searches multiple sources in parallel
3. Findings are reported progressively — user can steer the research at decision points
4. Final structured markdown report is captured to `docs/research/`

## Why This Approach

### Separate Plugin (Not Extending interflux)

- **interflux** is a code review + lightweight research tool — it optimizes for codebase-centric queries
- **interdeep** is a general-purpose research engine — it optimizes for external knowledge gathering
- Clean separation avoids bloating interflux with capabilities orthogonal to its core mission
- Different dependency profiles (interflux has no heavy extraction deps)

### Host-Agent-as-Brain (Not Dedicated Model)

- Works identically across Claude Code, Gemini CLI, Codex — no model-specific coupling
- No additional API keys beyond search providers
- Research quality scales with the user's chosen model
- Follows Interverse philosophy: plugins provide capabilities, not intelligence

### GPT-Researcher: Inspire + Port-Partially (Not Adopt)

GPT-Researcher is cloned into `research/gpt-researcher/` as a reference codebase. Per PHILOSOPHY.md's external tools verdict tiers, this is **inspire-only** + **port-partially** — not a runtime dependency:

- **Inspire-only:** The deep research recursion pattern (breadth→depth tree search with visited_urls tracking and 25k-word cap), the multi-agent editor→researcher→writer pipeline architecture
- **Port-partially:** Prompts (`prompts.py` — query expansion, report generation, source curation), individual retriever adapters (~30-80 lines each, no cross-deps), the `json-repair` library usage pattern
- **Not adopted:** The LangChain stack (too heavy), `unstructured` (overkill), the full `GPTResearcher` class (tightly coupled)

GPT-Researcher is heavily LangChain-coupled, so full adoption doesn't work. We extract the valuable parts (prompts, patterns, small adapters) and reimplement within Demarch's architecture. The clone in `research/` is reference material, not a dependency.

## Key Decisions

### 1. Search Providers: Compose Existing Plugins + Extend interject

**Philosophy alignment:** *"Each plugin does one thing well"* + *"Composition over capability."*

interdeep does NOT own search providers directly. Instead:

**Already available (compose via MCP/library):**

| Provider | Owner Plugin | How interdeep Uses It |
|----------|-------------|----------------------|
| Exa (semantic web) | `intersearch` | Import `intersearch.exa.multi_search()` |
| arXiv | `interject` | `interject_scan(source="arxiv")` |
| HackerNews | `interject` | `interject_scan(source="hackernews")` |
| GitHub | `interject` | `interject_scan(source="github")` |
| Anthropic docs | `interject` | `interject_scan(source="anthropic")` |

**New adapters (extend interject, not interdeep):**

| Provider | Type | API Key Required | Notes |
|----------|------|-----------------|-------|
| Tavily | Factual search + extract | Yes | New interject adapter |
| Brave | Privacy-focused web search | Yes | New interject adapter |
| PubMed | Medical research | No | New interject adapter |
| Semantic Scholar | Academic (broad) | No (rate limited) | New interject adapter |
| SearXNG | Self-hosted metasearch | No | New interject adapter |

**Design principle:** Search providers are interject's responsibility — it already has the adapter pattern, scoring pipeline, and deduplication. interdeep calls `interject_scan` and `interject_search`, never raw provider APIs. New providers are contributed upstream to interject. interdeep degrades gracefully based on which interject adapters are configured.

### 2. Content Extraction: trafilatura + Playwright Hybrid

Build our own extraction layer instead of depending on external services:

- **trafilatura** (Python) as the fast path — handles ~80% of pages in milliseconds, no browser needed
  - Used by Common Crawl, Internet Archive — battle-tested at scale
  - Extracts main content, strips boilerplate, outputs clean text/markdown
  - Handles PDFs, RSS feeds, sitemaps natively
- **Playwright** as the fallback — for JS-rendered SPAs and pages trafilatura can't parse
  - Only spawned when trafilatura fails or detects JS-heavy content markers
  - Reuses a persistent browser context to avoid cold-start overhead

**Reference:** Jina Reader (github.com/jina-ai/reader, Apache 2.0) for extraction heuristics, but we build lighter.

### 3. Output: Interactive + Report

- Research happens conversationally — progressive findings, user steering at decision points
- Final output: structured markdown report to `docs/research/<query-slug>/report.md`
- Report includes: sections, inline citations `[1]`, sources bibliography, confidence indicators
- Compatible with interknow compounding (findings become institutional knowledge)
- Compatible with intersynth synthesis (can be synthesized with other research)

### 4. Architecture: Orchestration + Extraction (Scoped Responsibility)

**Philosophy alignment:** *"Plugins are dumb and independent. The platform is smart and aware."*

interdeep owns exactly two things: (1) content extraction and (2) research orchestration. Search is interject's job. Synthesis is intersynth's job. Knowledge persistence is interknow's job. interdeep composes them.

```
interdeep/
├── .claude-plugin/
│   └── plugin.json                # Interverse plugin manifest
├── scripts/
│   ├── launch-mcp.sh             # Launches the MCP server
│   └── bump-version.sh           # Version management
├── src/interdeep/
│   ├── server.py                  # MCP server (Python, uv)
│   ├── extraction/               # Content extraction layer (interdeep OWNS this)
│   │   ├── trafilatura_ext.py    # trafilatura wrapper (fast path)
│   │   ├── playwright_ext.py     # Playwright fallback (JS pages)
│   │   └── hybrid.py             # Smart routing between the two
│   └── reports/                  # Report compilation (interdeep OWNS this)
│       └── markdown.py           # Structured markdown with citations
├── skills/
│   └── deep-research/
│       └── SKILL.md              # Orchestration prompt for host AI
├── agents/
│   ├── research-planner.md       # Query decomposition agent
│   ├── source-evaluator.md       # Source credibility assessment
│   └── report-compiler.md        # Final report assembly
├── commands/
│   └── research.md               # /interdeep:research command
├── config/
│   └── settings.yaml             # Extraction settings, report defaults
└── tests/
    ├── pyproject.toml
    └── structural/               # Plugin standard structural tests
```

Note: no `providers/` directory. Search providers live in interject. GPT-Researcher reference lives in `research/gpt-researcher/` at the Demarch monorepo root, not inside the plugin.

### 5. MCP Tools Exposed

All tools are stateless. Orchestration intelligence lives in the skill prompt, not in tools.

| Tool | Description | Owner rationale |
|------|-------------|-----------------|
| `extract_content` | URL → clean markdown (trafilatura + Playwright hybrid) | No existing plugin does content extraction |
| `extract_batch` | Multiple URLs → clean markdown, concurrent | Batch version of above |
| `compile_report` | Assemble findings + sources into structured markdown report | Report format is interdeep-specific |
| `research_status` | Show available companion plugins and their readiness | Composition health check |

## What We Compose (Not Rebuild)

### From Interverse Plugins (called via MCP tools, agents, or skills)

| Capability | Plugin | Mechanism |
|---|---|---|
| Web search (neural/semantic) | `intersearch` | Import `intersearch.exa.multi_search()` |
| Multi-source discovery (arXiv, HN, GitHub) | `interject` | `interject_scan`, `interject_search` MCP tools |
| Semantic search across corpus | `intersearch` | `embedding_index` + `embedding_query` MCP tools |
| Cross-session content cache | `intercache` | `cache_lookup` + `cache_store` MCP tools |
| Research synthesis | `intersynth` | Dispatch `synthesize-research` agent |
| Thinking gap detection | `interlens` | `detect_thinking_gaps` MCP tool |
| Cross-AI validation | `interpeer` | `deep` or `council` mode on final report |
| Context compression | `interserve` | `codex_query` for large doc summarization |
| Knowledge persistence | `interknow` | `/interknow:compound` after each session |
| Knowledge recall | `interknow` (qmd) | `qmd:vsearch` before each session |
| Domain detection | `intersense` | `detect-domains.py` to sharpen queries |
| Agent health monitoring | `intermux` | `agent_health` during parallel dispatch |
| Report skeleton pattern | `interleave` | LLM Islands for deterministic structure |
| Code-specific research | `tldr-swinton` | `distill`, `semantic` for codebase queries |

### From Open Source (dependencies, not forks)
- **trafilatura** (Apache 2.0) — Content extraction engine, pip dependency
- **Playwright** (Apache 2.0) — Headless browser fallback, pip dependency

### From GPT-Researcher (inspire + port-partially)
- Prompts: query expansion, report generation, source curation (~900 lines of pure text)
- Deep research recursion pattern: breadth→depth tree with visited_urls tracking
- `json-repair` library: tolerant JSON parsing for LLM outputs
- Individual retriever adapter patterns (structure reference for new interject adapters)

## Evidence Design (PHILOSOPHY.md Alignment)

*"Every action produces evidence. Evidence earns authority."*

### Research Session as OODARC Loop

| OODARC Phase | Research Session Equivalent | Evidence Produced |
|---|---|---|
| **Observe** | Scan sources, extract content | Raw findings, source URLs, extraction metadata |
| **Orient** | Classify query type, score source relevance | Query decomposition, source credibility scores |
| **Decide** | Select which threads to pursue deeper | Research plan (sub-queries, depth/breadth allocation) |
| **Act** | Execute searches, dispatch agents, compile report | Report artifact, citations, synthesis |
| **Reflect** | Was the research useful? What was missed? | Session bead (outcome feedback), interknow compound entries |

### Receipts

- **Research session bead** — Created when `/interdeep:research` starts, closed when report is delivered. Contains: query, sub-queries explored, sources consulted, provider costs, report path, outcome feedback.
- **Report artifact** — `docs/research/<query-slug>/report.md` with provenance metadata in YAML frontmatter: date, query, sources count, providers used, total tokens, session bead ID.
- **Source log** — `docs/research/<query-slug>/sources.json` — every URL consulted, extraction method used, relevance score, whether it contributed to the final report. Replayable.
- **interknow entries** — Stable findings (confirmed across 2+ sessions) are compounded automatically via `/interknow:compound`.

### Feedback Loop

Research quality improves over time through:
1. **Source quality tracking** — Sources that contribute to accepted reports earn higher scores in future sessions
2. **Provider reliability** — Track which providers returned useful results per query type (academic vs. technical vs. landscape)
3. **Extraction success rate** — Track trafilatura vs. Playwright fallback rates to tune the routing threshold
4. **Cross-session dedup** — interknow recall prevents re-researching known topics; intercache prevents re-fetching known URLs

### Measurement

Per PHILOSOPHY.md: *"Instrument first, optimize later."*

- **Outcome metric:** Was the report used? (bead closed with positive outcome vs. abandoned)
- **Proxy metrics:** Sources per query, extraction success rate, synthesis coverage, time-to-report
- **Anti-gaming:** Diverse query types in evaluation, human spot-checks on source relevance scores

## Open Questions

1. **Research persistence** — Should research sessions be resumable? (e.g., save state to `.interdeep/sessions/`)
2. **Rate limiting** — How to handle provider rate limits gracefully across parallel searches? (interject's responsibility or interdeep's?)
3. **Caching** — Use intercache MCP tools, or does extraction need its own cache? (intercache is content-addressed, may be sufficient)
4. **Deduplication** — interject handles source-level dedup. interdeep handles content-level dedup via intersearch embeddings?
5. **Depth control** — How does the user control research depth? (quick/balanced/deep modes like Pollard? Token budget? Time limit?)
6. **interject adapter contribution** — Do we extend interject with 5 new adapters (Tavily, Brave, PubMed, Semantic Scholar, SearXNG) as part of this work, or track separately?
7. **Streaming** — Progressive findings via MCP notifications, or purely through the skill's conversation flow?

## Philosophy Alignment Summary

| Principle | How interdeep Aligns |
|---|---|
| **Every action produces evidence** | Research sessions create beads, reports include provenance metadata, source logs are replayable |
| **Evidence earns authority** | Source quality scores improve over time; provider reliability is tracked; extraction success rates are measured |
| **Authority is scoped and composed** | interdeep owns only extraction + orchestration. Search = interject. Synthesis = intersynth. Knowledge = interknow. MCP tools are stateless; orchestration intelligence lives in the skill prompt. |
| **Plugins are dumb and independent** | MCP tools are stateless utilities. The host AI (Claude/Gemini/Codex) provides the reasoning. The skill prompt provides the orchestration. |
| **External tools: adopt, don't rebuild** | trafilatura and Playwright are pip dependencies. GPT-Researcher is inspire + port-partially. Search providers are composed from interject, not rebuilt. |
| **Self-building** | interdeep will be used to research improvements to interdeep (and other Demarch modules). Agent friction during research sessions is signal for technical debt. |
