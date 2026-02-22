# Recent Brainstorms and Plans Analysis — Interverse Project

**Date:** 2026-02-16
**Analysis by:** Claude Opus 4.6 (Sonnet 4.5 agent)
**Scope:** Recent brainstorms (2026-02-16), plans, roadmap

---

## Executive Summary

The Interverse project is in an intense **token efficiency optimization phase** across multiple modules. Four major themes dominate recent activity:

1. **Token efficiency & cost optimization** — 7-finding synthesis from research, multi-layered approach (slicing, budgets, lazy loading, orchestrator patterns)
2. **Quality infrastructure** — Canary monitoring for routing overrides, code quality guards
3. **MCP server expansion** — New modules (interserve, intermap) extracting capabilities from monolithic components
4. **Cross-module integration** — Shared libraries, event contracts, unified operations HUD

The roadmap shows **112 open beads** across 28 modules, with P0 work blocking multiple downstream initiatives. The project is transitioning from breadth (many modules) to depth (optimization, quality, consolidation).

---

## Theme 1: Token Efficiency & Cost Optimization

### Research Foundation

`docs/research/token-efficiency-agent-orchestration-2026.md` (referenced in synthesis brainstorm) conducted a landscape analysis of agent orchestrators (myclaude, claude-flow, cco, systemprompt, AgentCoder, MASAI). Key finding: **no existing orchestrator does per-agent document slicing**. Seven optimization patterns identified:

1. Lead-orchestrator + specialized workers (AgentCoder: 59% reduction)
2. Cross-model specialization (myclaude: 4 backends with cost arbitrage)
3. Complexity-based dispatch (claude-flow: 3-tier routing)
4. Artifact-first handoffs (Clavain: 70% savings via file indirection)
5. Context compaction/resumable state (Factory.ai: 98.6% compaction)
6. Structured return formats (JSON Whisperer: 31% reduction)
7. Lazy skill loading (task-orchestrator: 88% baseline reduction)

### Active Implementation

**Bead iv-7o7n (P0): Flux-drive document slicing** — Blocking **iv-j7uy** (interserve MCP) which blocks **iv-zrmk** → **iv-5m8j** → **iv-tifk** (4-bead chain).

Approach: Always-on **interserve MCP server** (Go stdio, delegates to Codex spark via dispatch.sh). Per-agent temp files with:
- Priority sections (full content)
- Context sections (1-line summaries)
- 80% threshold (if agent's priority ≥80% of doc, send full)
- Cross-cutting agents (fd-architecture, fd-quality) always get full doc
- Domain mismatch guard (>10% check prevents classification failure)

Token economics: 50-70% reduction (75k → 25-37k tokens per 5-agent review). Classification cost: ~500-1k spark tokens (not Claude tokens).

**Bead iv-8m38 (P0): Token budget controls + cost-aware dispatch** — Blocks **iv-qjwz** (AgentDropout), **iv-6i37** (blueprint distillation).

Approach: Variant A+D hybrid (flux-drive internal budget + historical cost estimates from interstat). Budget config per review type (plan: 150K, brainstorm: 80K, diff-small: 60K, repo: 300K). Triage defers low-scoring agents when budget tight. Cost report in synthesis (actual vs estimated).

Measurement definitions (Oracle requirement):
- **Billing tokens** (input + output) for budget caps
- **Effective context** (input + cache_read + cache_creation) for context window decisions
- Critical distinction: billing can differ from effective by 600x+ due to cache hits

**Bead iv-1zh2 (Clavain token-efficiency synthesis)** — Parent tracker for 7 sub-beads implementing each finding.

Implementation phases:
- Phase A (1-2 days): Model declarations, output contracts, skill catalog split, max_turns on dispatches
- Phase B (2-3 days): Verdict file schema, artifact handoffs, sprint orchestrator reads verdicts not raw output
- Phase C (3-5 days): Complexity classifier, phase skipping, tier-based cost tracking
- Phase D (2-3 days): Checkpoint schema, sprint resume from checkpoint, agent verdict persistence

**Trio (iv-ked1, iv-hyza, iv-kmyj)** — Three independent improvements compounding to 30-50% reduction:
1. **iv-ked1**: Skill injection budget cap (16K chars, ~4K tokens) — writing-skills is 18.6KB (needs trim)
2. **iv-hyza**: Summary-mode output extraction — universal verdict header, orchestrator reads <500 chars not 2-10K
3. **iv-kmyj**: Conditional phase skipping — complexity 1-2 skip brainstorm/strategy/review, whitelist per tier

### Dependency Chains

```
iv-7o7n (slicing) → iv-j7uy (interserve) → iv-zrmk (classification) → iv-5m8j (temp files) → iv-tifk (integration)
                                ↓
                          iv-8m38 (budget) → iv-qjwz (AgentDropout), iv-6i37 (blueprint)
                                ↓
                          iv-1zh2 (synthesis) → iv-1zh2.1..7 (7 sub-beads)
```

**Critical path:** iv-7o7n → iv-j7uy is the P0 gate. Slicing reduces per-agent tokens by 50-70%, which makes budget controls (iv-8m38) more accurate and AgentDropout (iv-qjwz) more effective.

---

## Theme 2: Quality Infrastructure

### Interspect Canary Monitoring (iv-cylo)

**Blocks 6 downstream beads**: iv-rafa (meta-learning), iv-ukct (revert command), iv-t1m4 (prompt tuning), iv-5su3 (autonomous mode), iv-jo3i (verdict engine), iv-sisi (statusline integration).

Approach: Active monitoring for routing overrides (when interspect excludes an agent). Three proxy metrics:
1. **Override rate** (overrides/session) — increase suggests remaining agents produce findings the excluded one would have caught differently
2. **FP rate** (agent_wrong / total overrides) — increase may indicate excluded agent provided complementary coverage
3. **Finding density** (corrections/session) — drop suggests excluded agent was primary contributor

Window: 20 uses OR 14 days (whichever first). Baseline computed from last 20 sessions before override. Alert threshold: >20% degradation relative to baseline, with 0.1 absolute noise floor.

Alert surface:
1. `/interspect:status` — shows canary verdict, sample count, progress
2. Session-start injection — "⚠️ Canary alert: routing override for {agent} may have degraded review quality. Run `/interspect:status` for details or `/interspect:revert {agent}` to undo."
3. Statusline (iv-sisi, downstream)

No auto-revert — human triggers revert manually via `/interspect:revert`.

### Intercheck Code Quality Guards (brainstorm 2026-02-15)

Syntax validation, auto-formatting, session health monitoring. Not yet in execution phase.

---

## Theme 3: MCP Server Expansion

### Interserve (iv-j7uy)

**New module:** Go stdio MCP server for Codex spark classification. Extracts section classification from inline LLM (which was 4.7k token overhead). Two tools:
1. `extract_sections` — split by `##`, skip code blocks/frontmatter
2. `classify_sections` — per-agent relevance scoring via dispatch.sh --tier fast

Replaces 5-variant experiment (Python script, inline LLM, etc.). Spark wins: semantic understanding, near-zero cost (~$0.001-0.003), always-on reusability, 0 Claude tokens.

Enables beyond slicing:
- Summary-mode output extraction (iv-hyza)
- Conditional phase skipping (iv-kmyj)
- Complexity routing (iv-jdow)

### Intermap (iv-aose)

**New module:** Extracts project-level code analysis from tldr-swinton. Moves ~209KB of Python (6 modules) into a Go MCP server that shells out to Python subprocess:
- `cross_file_calls.py`, `analysis.py`, `project_index.py`, `change_impact.py`, `diagnostics.py`, `durability.py`

Leaves tldr-swinton focused on file/symbol-level context (extraction, compression, semantic search).

New capabilities intermap adds:
- Project registry (discover all projects in workspace)
- Cross-project dependency graph
- Agent overlay (consume intermux data to show who's working where)
- CWD-to-project resolution

Rationale: tldr-swinton is 1.4MB across 80+ files. `core/` module alone is 1.1MB. Natural seam exists at graph/architecture cluster.

---

## Theme 4: Cross-Module Integration

### Integration Program (iv-z1a0)

Parent tracker blocking:
- **iv-z1a1**: Inter-module event bus + event contracts
- **iv-z1a2**: Interline as unified operations HUD
- **iv-z1a4**: Interkasten context into discovery and sprint intake

### Shared Libraries

- **iv-lwsf**: Shared HTTP client library (interhttp) for Go + bash
- **iv-tkc6**: Shared bash hook library (interhooks) for clavain/interphase/interlock
- **iv-jmua**: Shared SQLite library (intersqlite) for 6 modules

### Interlock Phase 4a (iv-d72t, in progress)

Reservation negotiation protocol. Blocks 5 items (iv-1aug, iv-5ijt, iv-6u3s, iv-2jtj). Touches intermute HTTP API.

---

## Roadmap Snapshot

**112 open beads** across 28 modules. 9 blocked by upstream dependencies.

### Now (P0-P1)

- **iv-7o7n** (flux-drive slicing) — P0, blocks iv-j7uy → entire slicing chain
- **iv-8m38** (token budget controls) — blocks iv-qjwz, iv-6i37
- **iv-cylo** (canary monitoring) — blocks 6 items
- **iv-d72t** (interlock negotiation, in progress) — blocks 5 items

### Next (P2)

Token efficiency continuation:
- iv-zrmk, iv-5m8j, iv-tifk (slicing chain continuation)
- iv-qjwz (AgentDropout — dynamic redundancy elimination)
- iv-hyza (summary-mode output extraction)
- iv-ked1, iv-kmyj (skill budget cap, phase skipping)

Interstat benchmarking pipeline:
- iv-dyyy (plugin scaffold) → blocks iv-qi8j, iv-lgfi, iv-dkg8, iv-bazo
- Real-time event capture, JSONL parser, analysis queries

Interspect routing overrides:
- iv-r6mf (routing-overrides.json schema) → blocks iv-8fgu, iv-6liz, iv-gkj9, iv-2o6c

### Modules Without Roadmaps

None — all 28 modules have roadmap artifacts.

---

## Patterns in User/Team Focus

### January → Early February

- **Breadth expansion** — Many new modules (intercheck, intercraft, interdev, internext, interstat, interlens)
- **MCP server pattern solidified** — Go stdio servers (interlock, intermux, tuivision) proven
- **Bidirectional sync shipped** — interkasten v0.4.0 (three-way merge)

### Mid-February (2026-02-15 onwards)

- **Token efficiency obsession** — 7-finding research → synthesis → trio → flux-drive slicing → budget controls → interstat
- **Quality gates tightening** — Canary monitoring, code quality guards, session health
- **Consolidation phase** — Extracting shared patterns (interhttp, interhooks, intersqlite), extracting monolithic components (intermap from tldr-swinton)

### 2026-02-16 (today)

- **6 new brainstorms** created today (token efficiency synthesis, trio, budget controls, slicing, canary, intermap)
- **4 new plans** created today (token efficiency, budget controls, slicing, canary)
- **4 new PRDs** created today (matching the plans)
- Intense research activity (21 interject-prefixed research docs — appears to be an ambient discovery engine pulling in external sources)

---

## Cross-Cutting Observations

### Interject Activity

21 research docs prefixed with `2026-02-16-interject-*` suggest an ambient research engine (interject plugin) is pulling in external sources about:
- Multi-agent orchestration frameworks (LangChain, LangGraph, AutoGen)
- MCP marketplace and security
- AI workflow automation tools
- Claude Code plugin development
- Code quality analysis with LLMs

This appears to be feeding the token-efficiency research.

### Oracle (GPT-5.2 Pro) Integration

Oracle review explicitly flagged "no primary measurements" as #1 gap. This drove the measurement definitions requirement in iv-8m38 (billing vs effective context distinction).

Oracle is used for cross-AI review (flux-drive triage includes Oracle agent when available). Requires `DISPLAY=:99 CHROME_PATH=/usr/local/bin/google-chrome-wrapper` and browser mode (10-30+ min per review).

### Flux-Drive as Hub

Flux-drive (interflux) is the nexus for many optimization efforts:
- Document slicing (iv-7o7n, iv-tifk)
- Budget controls (iv-8m38)
- Routing overrides (interspect)
- Agent contracts/verdicts (iv-1zh2.4, iv-1zh2.6)

Currently v0.2.11, 19 open beads (most of any module except clavain). Phase: "quality and operations."

### Clavain as Orchestrator

Clavain (os/clavain, v0.6.30) is the orchestrator hub. 23 skills, 4 agents, 51 commands, 19 companions. 372 beads closed, 0 open locally (all work tracked at Interverse level).

Sprint workflow is the primary interface for multi-step work. Current focus: outcome measurement, interspect analytics activation, sprint workflow resilience.

### Interstat as Measurement Foundation

New module (v0.1.0, 4 open beads). PostToolUse:Task hook captures real-time agent dispatch data. SessionEnd hook backfills token data from session JSONL.

Enables:
- Historical per-agent cost estimates (for iv-8m38 budget controls)
- Token benchmarking (iv-dyyy pipeline)
- Before/after comparisons for optimization claims

---

## Key Decisions Made

1. **Semantic classification via spark tier** (iv-7o7n) — not keyword matching, not inline LLM
2. **Budget enforcement: soft warning** (iv-8m38) — not hard block, user can override
3. **Canary monitoring: no auto-revert** (iv-cylo) — human triggers revert manually
4. **Trunk-based development** — commit directly to main, no feature branches
5. **Token-efficiency over model quality for classification** — spark tier is cheapest, good enough for section assignment
6. **Billing tokens ≠ effective context** — decision gates must distinguish (Oracle requirement)

---

## Open Questions Across Plans

### From token-efficiency synthesis (iv-1zh2)

1. Should contracts be enforced or advisory? Rec: advisory initially, enforce after 2 weeks
2. Where do verdict files live? Rec: `.clavain/verdicts/` (persistent, git-ignored, cleaned at sprint start)
3. Complexity classifier: LLM or heuristic? Rec: heuristic (file count, keywords), save LLM for ambiguous cases

### From budget controls (iv-8m38)

1. Cold start: what if interstat has no data for an agent? Rec: default estimate (40K review, 15K research)
2. Should budget config specify model routing per agent? Not for v1, but config should anticipate
3. Slicing interaction: use post-slicing averages? How to handle transition period? Open

### From canary monitoring (iv-cylo)

1. What's a "use"? Rec: count sessions with at least one evidence event
2. Baseline window size configurable? Yes: confidence.json (canary_window_uses: 20, canary_min_baseline: 15)
3. Alert threshold config? Yes: canary_alert_pct: 20 (%), canary_noise_floor: 0.1

---

## Risk Areas

### Token Optimization Risks

- **Over-summarization** (Finding 4): Workers compress away actionable detail. Fix: verdicts include file:line refs
- **Misclassification** (Finding 3): "Simple" task turns complex mid-execution. Fix: complexity can revise upward, never downward
- **Contract drift** (Finding 6): Agent .md says one thing, output says another. Fix: validation hook checks compliance

### Interserve Risks (from PRD review)

- **Python import chain pulls in too much of tldr-swinton**: Audit and break deps
- **Subprocess overhead**: Acceptable for project-level queries (cache call graphs)
- **Two MCP servers confuses agents**: Clear tool descriptions (intermap=project, tldr=file)

### Canary Risks (from plan review)

- **Baseline computation slow for large DBs**: Index on `sessions.start_ts` exists
- **Session-end hook adds latency**: Fail-open, skip if no active canaries
- **Stale checkpoints**: Checkpoint includes git SHA, resume validates HEAD matches

---

## Recommended Next Actions (Based on Patterns)

1. **Unblock P0 chain** — iv-7o7n (slicing) → iv-j7uy (interserve) is the critical path
2. **Measurement infrastructure first** — iv-dyyy (interstat scaffold) before claiming optimization wins
3. **Consolidate before expanding** — Shared libraries (interhttp, interhooks, intersqlite) reduce duplication
4. **Canary monitoring gates routing overrides** — iv-cylo blocks autonomous mode (iv-5su3) and verdict engine (iv-jo3i)
5. **Document extraction patterns** — Intermap extraction from tldr-swinton is a template for future refactorings

---

## Appendix: File Counts

- **20 brainstorms** (2026-02-14 to 2026-02-16)
- **24 plans** (2026-02-14 to 2026-02-16)
- **5 PRDs** (2026-02-16 only)
- **21 research docs** (2026-02-16, interject-prefixed)
- **4 solution pattern docs** (guards, WAL protocol, sync workflow, git credential)
- **Roadmap** (1 markdown, 1 JSON — auto-generated)

Most active dates: **2026-02-16** (today) — 6 brainstorms, 4 plans, 5 PRDs, 21 research docs.

---

## Conclusion

The Interverse project is in a **mature optimization phase**. The breadth phase (28 modules, 112 open beads) is transitioning to depth (token efficiency, quality gates, consolidation). The P0 work (slicing, budget controls, canary monitoring) blocks multiple downstream initiatives. The team is systematically addressing technical debt (shared libraries, extraction, measurement) while pursuing aggressive performance targets (50-70% token reduction).

The research → synthesis → PRD → plan → execution pipeline is well-oiled. Oracle (GPT-5.2 Pro) is integrated for cross-AI review. Interject provides ambient discovery. Interstat enables measurement. The orchestrator (Clavain) is stable and in daily use.

Next 2-4 weeks will determine if the token optimization claims (30-90% reductions) hold in production. The measurement infrastructure (interstat) is the key — no optimization claim is credible without before/after data.

