# Research Evaluation: Plugin Modularity vs Consolidation for AI Agents

## Assessment Date
2026-03-02

## Key Findings

### Strongest Evidence (Tier 1)
- **Claude Code #3406, #11364** (context pollution) — HIGH credibility, direct evidence
- **npm incidents** (left-pad, event-stream, 2024 bloat study) — HIGH credibility for supply chain risk
- **Anthropic tool use blog** (need to verify recency) — HIGH credibility for AI-specific patterns
- **ChatGPT plugin deprecation** — Real ecosystem signal but reasoning unpublished

### Partial Relevance (Tier 2)
- Terraform/go-plugin: Proven RPC model; subprocess ≠ in-process tool calling
- VSCode Extension Host: Process isolation works; IDE ≠ agent execution
- Amazon Prime Video: Real consolidation case; video streaming ≠ tool calling
- Fowler/Newman: Good principles; lack AI specificity

### Low Relevance (Skip)
- K8s, Istio, OSGi, CNCF surveys — infrastructure focus
- 2014-2018 microservices papers — predate modern AI
- Segment 2018, Rotem-Gal-Oz 2014 — aged

## Critical Biases

### Domain Transfer Bias (HIGH RISK)
Video streaming latency != context window costs. Data pipeline scaling != tool calling. These don't transfer.

### Recency Bias (MEDIUM RISK)
Pro-consolidation sources are old (2014-2018); AI tool ecosystems are 2022+. ChatGPT plugins deprecated but reasons unknown.

### Architecture-Aligned Bias (MEDIUM RISK)
All architecture docs favor their own model. Look for post-mortems on failures.

### Vendor Bias (MEDIUM RISK)
OpenAI never published technical reasons for plugin deprecation. Writer/Cloudflare MCP posts have inherent conflict of interest.

## Evidence Gaps

### Must Fill
1. **AI cost model**: N modular tools vs 1 consolidated — measure token overhead, reasoning degradation
2. **ChatGPT postmortem**: Search OpenAI GitHub, Discord, eng-blog for technical analysis
3. **LLM framework choices**: LangChain, AutoGen, CrewAI modularity decisions
4. **Demarch/Interverse metrics**: Real context pollution data from interstat

### Should Fill
- Supply chain risk comparison across Terraform, Go, Python plugin ecosystems
- 2024-2026 AI tool architecture papers
- Engineer interviews (5-10 AI framework teams)

## What to Include in Report

### YES (High confidence)
- Claude context pollution evidence
- npm supply chain incidents (with caveat on ecosystem differences)
- Terraform/go-plugin architecture (with caveat on execution model)
- Amazon Prime Video case (with caveat on video ≠ tools)
- Fowler/Newman principles (applicable to AI teams)

### YES with Caveats
- ChatGPT deprecation (business decision? technical cost? unclear)
- BFCL V4 (accuracy benchmark; doesn't compare modularity)
- Shopify Packwerk (monolith boundary enforcement; distributed tools unclear)
- VSCode (process isolation proven; IDE ≠ agent)

### NO (Skip)
- K8s, Istio, OSGi, CNCF, WJARR
- 2014-2018 microservices papers
- Generic vendor MCP posts

## Confidence Statements

| Statement | Confidence | Reason |
|-----------|-----------|--------|
| "Modular tools cause context pollution" | HIGH | Claude evidence is direct |
| "Supply chain risk increases with modularity" | MEDIUM | npm proven; other ecosystems unknown |
| "Consolidation reduces operational complexity" | MEDIUM | proven for web/video; AI transfer unclear |
| "Best architecture for AI tools is X" | NONE | no domain-specific studies exist |

## For Next Researcher

1. This research collection is 70% general software architecture, 30% AI-specific
2. All general software sources need careful extrapolation (domain transfer bias is real)
3. The biggest missing piece is a quantified cost model for context window overhead
4. ChatGPT plugin deprecation is a major signal but unexplained — find technical postmortem
5. Don't make a recommendation without internal Demarch/Interverse metrics
