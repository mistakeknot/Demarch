---
artifact_type: review-synthesis
method: flux-review
target: docs/research/flux-review/sylveste-improvements-multi-axis/2026-05-04-target.md
target_description: Sylveste monorepo improvements across usability, token efficiency, and LLM-routing replacement
tracks: 4
track_a_agents: [fd-claude-code-hooks-economy, fd-mcp-server-hygiene, fd-prompt-cache-economics, fd-context-budget-orchestration, fd-llm-routing-replaceability]
track_b_agents: [fd-search-engine-ranking, fd-build-system-caching, fd-compiler-incremental-build, fd-ide-quick-actions]
track_c_agents: [fd-kalman-filter-fusion, fd-mpc-control-budget, fd-queueing-priority-scheduling, fd-ribosome-stall-rescue]
track_d_agents: [fd-polynesian-wayfinding-fusion, fd-glaciology-firn-densification, fd-medieval-scriptorium-rubrication]
date: 2026-05-04
total_findings: 91
p1_findings: 27
---

# Sylveste Multi-Axis Improvement Synthesis

Four parallel tracks at increasing semantic distance produced 91 findings (27 P1, 0 P0). The convergence pattern is unusually sharp: agent triage replacement, content-addressed caching, MEMORY.md restructuring, parallel-dispatch concurrency, and short-prefix routing each surfaced independently from 3-4 unrelated knowledge domains. The current state is a working but unoptimized orchestration layer where the cheapest wins (XS/S difficulty) compound to clear the ynh7-style "next 2,000+ tok/session" floor by a wide margin.

## Critical Findings (P0/P1) by Axis

### Token Efficiency

**BSC-1** (fd-build-system-caching) — Timestamped OUTPUT_DIR (`RUN_TS = $(date +%Y%m%dT%H%M)` at SKILL.md:112) embedded in every agent prompt defeats all cross-run prompt cache hits. Bazel-equivalent hermeticity violation. Fix: content-address OUTPUT_DIR via sha256. Savings: 21K tok/session. Difficulty: S.

**IC-01** (fd-compiler-incremental-build) — SessionStart hooks fire `bd prime`, `heal-dolt.sh`, `bd stats` on every startup/resume/clear regardless of state changes. Fix: `.claude/session-state.json` with git SHA + bead mtime + memory hash; skip if unchanged. Savings: 10-16K tok/hr on idle loops. Difficulty: S.

**C-01** (fd-prompt-cache-economics) — MEMORY.md orders churning sections (Active Projects, Active Brainstorms) above stable sections (Quick Reference, Discipline Lessons), invalidating ~6kt of cache per memory edit. Fix: reorder so churn lives at the bottom. Savings: 275-1500kt/week of cache-creation cost. Difficulty: XS.

**C-02** (fd-prompt-cache-economics) — bd prime double-fires on PreCompact + SessionStart-empty, walking the cache cursor twice through ~230 tok of static prose. Fix: covered by hooks-economy H-01/H-02. Savings: ~230 tok per compact event. Difficulty: XS.

**B-01** (fd-context-budget-orchestration) — MEMORY.md Active Projects + Active Brainstorms = 17 lines of cold-storage anchors that belong in beads, not memory. Fix: replace with single-line index pointing to `bd ready`. Savings: ~500-600 tok/session. Difficulty: XS.

**B-02** (fd-context-budget-orchestration) — ~150 skill descriptions repeat "Use when… / TRIGGER: / SKIP: / Examples:" framing for 3-5kt of compressible pattern. Fix: standardize a one-line schema, audit via interskill:audit. Savings: 2-4kt/session. Difficulty: M.

**B-03** (fd-context-budget-orchestration) — bd prime + heal-dolt + AGENTS.md beads-block triple-state the same protocol framing. Fix: keep canonical text in AGENTS.md, trim hooks to status-only. Savings: ~200-300 tok/session plus ~400 tok per compact event. Difficulty: S.

**M-01** (fd-mcp-server-hygiene) — 20 deferred OAuth tools (Notion/Gmail/Calendar/Drive) listed every session for <5% usage. Fix: workspace-aware `mcpProfile: dev` gating in settings.json. Savings: 600-1500 tok/session. Difficulty: S.

**M-02** (fd-mcp-server-hygiene) — 60-character tool names (`mcp__plugin_interflux_openrouter-dispatch__review_with_model`) bloat the deferred listing. Fix: collapse `mcp__plugin_X_X__X` to `mcp__X__X`. Savings: 800-1300 tok/session. Difficulty: M.

**MPC-01** (fd-mpc-control-budget) — /sprint and /work loops have no prediction horizon; budget gates fire reactively after exhaustion. Fix: horizon-N planner reading session-state.json. Savings: ~2,000 tok/sprint bust. Difficulty: M.

**QT-01** (fd-queueing-priority-scheduling) — /flux-review fans out 16 agents without concurrency cap; M/M/∞ contention causes rate-limit retries with 30% token waste. Fix: `MAX_CONCURRENT=6` semaphore gate in phases/launch.md. Savings: ~24K tok/affected review. Difficulty: S.

**FIRN-2** (fd-glaciology-firn-densification) — MEMORY.md carries archival content past close-off depth; historical entries (e.g., `project_auraken_go_migration.md`) load every session. Fix: depth-tiered archiving via project_status field. Savings: ~600-1400 tok/session. Difficulty: S.

**FIRN-1** (fd-glaciology-firn-densification) — MEMORY.md mutates in-place; provenance for feedback rules is destroyed at update. Fix: deposition headers (`deposited`, `last_confirmed`, `confirmation_count`); append-not-overwrite. Savings: ~800 tok/session via staleness filter. Difficulty: M.

**SCRIP-2** (fd-medieval-scriptorium-rubrication) — interpath:vision/roadmap regenerate without canonical-witness designation; agents read different timestamped versions. Fix: canonical `docs/vision.md` + archived witnesses. Savings: ~300-500 tok/session. Difficulty: XS.

### Usability

**IDE-01** (fd-ide-quick-actions) — 58 plugins share the "inter" prefix; `/inter` yields 116 options, far above IDE convention of <10. Fix: semantic short-prefix aliases in plugin.json. Difficulty: S.

**IDE-02** (fd-ide-quick-actions) — 6 distinct "review" commands across plugins with no inline disambiguation. Fix: contextual scoping. Savings: -150 tok/session. Difficulty: S-M.

**IDE-03** (fd-ide-quick-actions) — 7 "status" commands with no context-aware routing. Fix: route based on sprint/git context. Savings: -100 tok/session. Difficulty: M.

**RB-01** (fd-ribosome-stall-rescue) — Stalled subagents (permission errors) silently wait the full 300s timeout. Fix: 60s no-output stall detection in flux-watch.sh, error stub + peer finding. Savings: 16 minutes wall-clock per stalled review. Difficulty: S.

**SCRIP-1** (fd-medieval-scriptorium-rubrication) — Agents read CLAUDE.md, AGENTS.md, MEMORY.md, brainstorms, handoffs as equals; contradictions propagate. Fix: `docs/canon/exemplar-index.yaml` with explicit authority ordering. Savings: ~2,400 tok/week of clarification turns. Difficulty: S.

**FIRN-1** (fd-glaciology-firn-densification, also tagged usability) — same as above; provenance destruction is both efficiency and usability cost.

### ML / Routing Replacement

**R-01** (fd-llm-routing-replaceability) — flux-engine agent triage scores all 679+ agents via LLM reasoning; embedding cosine over (target, agent persona) replaces base_score. Savings: 45-90kt/week of routing inference. Difficulty: S.

**R-02** (fd-llm-routing-replaceability) — Skill router pays LLM cost per turn to reach "no skill applicable"; regex + embedding pre-filter short-circuits. Savings: 1.5Mt/week of per-turn inference (200-500 tok × 5000 turns). Difficulty: M.

**SER-01** (fd-search-engine-ranking) — Agent triage skips two-tower BM25/embedding retrieval; full LLM cross-encoder reranking on every call. Fix: intersearch top-30 retrieval + LLM rerank. Savings: 35K tok/review (85%). Difficulty: M. Convergent with R-01.

**KF-01** (fd-kalman-filter-fusion) — Skill routing has no innovation gating; LLM invoked for cases where 3-4 cheap sensors (regex prefix, embedding cosine, frecency, token-count bucket) would converge. Savings: 300-400 tok/turn × ~88% of turns. Difficulty: M. Convergent with R-02 + POLY-2 + RB-03.

**POLY-1** (fd-polynesian-wayfinding-fusion) — flux-engine triage relies on a single LLM oracle; three cheap signals (regex, file-extension, frecency) form a wayfinding fusion. Savings: ~1,200 tok/triage-run. Difficulty: M.

**POLY-2** (fd-polynesian-wayfinding-fusion) — Skill routing uses pure LLM classification; star-compass discretization into 4 keyword "houses" (WORK/REVIEW/RESEARCH/MEMORY) handles 60% directly. Savings: ~7,800 tok/session. Difficulty: S.

## Cross-Track Convergence

Ranked by convergence score. Each pattern surfaced independently across tracks at different semantic distances — the strongest signal flux-review can produce.

### 1. Agent-triage replacement via cheap-signal pre-filter (4/4 tracks)

**Convergence pattern**: flux-engine scores every agent via LLM reasoning when 60-90% of inputs would be resolved by deterministic signals (regex, embedding cosine, file extension, frecency).

**Independent surfacings**:
- Track A: R-01 (fd-llm-routing-replaceability) — "embedding cosine over (target, agent persona) replaces base_score; 45-90kt/week"
- Track B: SER-01 (fd-search-engine-ranking) — "two-tower BM25 + LLM rerank; 85% reduction; 35K tok/review"
- Track C: KF-03 (fd-kalman-filter-fusion) — "observability matrix; cheap sensors handle .py/.sh/.md typed inputs; 1,200 tok/triage"; POLY-1 framing the same gap
- Track D: POLY-1 (fd-polynesian-wayfinding-fusion) — "zenith + swell + cloud-mark fusion; regex + extension + frecency"

Track A frames it as routing economics ("you have embeddings in intersearch but unused for routing"). Track B frames it as the ranking-architecture mismatch (no candidate-gen stage). Track C frames it as Kalman observability (some states are observable from cheap sensors). Track D frames it as multi-signal navigator robustness.

**Combined confidence**: very high. **Recommended action**: implement `flux-agent score-relevance` with cached agent embeddings; ensemble with LLM scoring during 2-week shadow phase. S-M difficulty.

### 2. Skill-routing classifier replaces per-turn LLM evaluation (4/4 tracks)

**Convergence pattern**: every user turn invokes the LLM over a 150-skill listing to decide whether any skill fires. Most turns produce "no skill applicable" — the inference is wasted.

**Independent surfacings**:
- Track A: R-02 (fd-llm-routing-replaceability) — "per-turn LLM evaluation costs 200-500 tok × 5000 turns/week = 1.5Mt/week"
- Track B: SER-02 (fd-search-engine-ranking) — "skill routing has no retrieval stage — full ~8K-token skill listing every turn; embedding retrieval reduces to ~1.3K"
- Track C: KF-01 (fd-kalman-filter-fusion) — "skill routing has no Kalman fusion gate; 88% steady-state cheap-sensor agreement"; RB-03 (fd-ribosome-stall-rescue) — "signal-peptide pre-router on first 3 tokens routes 60-70% deterministically"
- Track D: POLY-2 (fd-polynesian-wayfinding-fusion) — "4-house star compass on WORK/REVIEW/RESEARCH/MEMORY keywords"

Track A treats it as pure cost economics. Track B as missing two-stage retrieval. Track C as missing innovation gating + signal peptides. Track D as missing horizon discretization.

**Combined confidence**: very high. **Recommended action**: SRP prefix table for /command inputs (RB-03, XS), then embedding cosine for the moderate band, full LLM only for the 0.5-0.7 ambiguous zone. S-M total.

### 3. MEMORY.md restructure (4/4 tracks)

**Convergence pattern**: MEMORY.md is over budget (132/120), mixes high-churn project state with stable feedback rules, mutates in-place destroying provenance, and accumulates archival content past its useful lifetime.

**Independent surfacings**:
- Track A: B-01 (fd-context-budget-orchestration) — "Active Projects + Active Brainstorms = 17 lines of cold-storage anchors that belong in beads"; C-01 (fd-prompt-cache-economics) — "churn-before-stable ordering invalidates ~6kt cache per edit"
- Track C: RB-02 (fd-ribosome-stall-rescue) — "no mRNA-decay half-life; expires_after frontmatter"; MPC-02 — "scattered constraint state needs single session-state.json"
- Track D: FIRN-1 (fd-glaciology-firn-densification) — "in-place mutation destroys deposition record; deposition headers"; FIRN-2 — "close-off depth tiering; archival content above active layer"; SCRIP-4 (fd-medieval-scriptorium-rubrication) — "marginalia merged with body; ~2,250 tok/session of commentary loaded as policy"

Three tracks (A, C, D) saw it as token efficiency; Track D's firn lens added the provenance/append-only insight that A missed; Track D's scriptorium lens added the body-vs-marginalia separation that C missed.

**Combined confidence**: very high. **Recommended action**: reorder churn-after-stable (XS), move Active Projects to `bd ready` indirection (XS), add `expires_after` + `last_confirmed` frontmatter (S), split topic files into `## Rule` / `## Marginalia` (XS). Combined: ~3-4kt/session.

### 4. Content-addressed caching / dirty-bit propagation (3/4 tracks)

**Convergence pattern**: outputs include timestamps that defeat deterministic caching; tools rebuild from scratch when state hasn't changed.

**Independent surfacings**:
- Track A: C-05 (fd-prompt-cache-economics) — "REVIEW_FILE timestamp in flux-drive subagent prompts defeats cross-agent cache"
- Track B: BSC-1 (fd-build-system-caching) — "RUN_TS in OUTPUT_DIR; 0% cross-run cache hit; 21K tok/session"; BSC-2 — "epoch timestamp in temp file paths"; IC-01 (fd-compiler-incremental-build) — "session-warm cache pattern; gen-skill-compact.sh manifest pattern not generalized"; IC-02 — "module roadmap rebuilds 63 modules per bead change; 95% reduction"; IC-03 — "flux-drive triage not memoized by (target_hash, agent_hash)"
- Track C: MPC-02 (fd-mpc-control-budget) — "constraint state needs session-state.json"

Track A and B converge sharply on the same root: the gen-skill-compact.sh manifest pattern correctly content-addresses but isn't generalized. Both Track A's C-05 and Track B's BSC-1 cite the same SKILL.md:112 line.

**Combined confidence**: very high. **Recommended action**: generalize `lib-freshness.sh` from gen-skill-compact.sh manifest pattern; sha256-address OUTPUT_DIR; write session-state.json on SessionStart; gate hooks on dirty bit. S total.

### 5. Parallel-dispatch concurrency cap (2/4 tracks)

**Convergence pattern**: flux-review fans out 16 agents simultaneously, exceeding Anthropic API concurrent-session limits, causing 30% retry overhead.

**Independent surfacings**:
- Track B: BSC-3 (fd-build-system-caching) — "tool results not shared across parallel fan-out; 10-15K tok/run"
- Track C: QT-01 (fd-queueing-priority-scheduling) — "M/M/k contention; Erlang C predicts 30% retry waste; MAX_CONCURRENT=6"

**Combined confidence**: high. **Recommended action**: semaphore gate in phases/launch.md (one-line change). XS-S.

### 6. Streaming/partial-result synthesis (2/4 tracks)

**Convergence pattern**: synthesis blocks on slowest agent (max-latency policy) when partial-result synthesis would proceed at 80th-percentile.

**Independent surfacings**:
- Track C: QT-02 (fd-queueing-priority-scheduling) — "head-of-line blocking; --partial-ok 0.80"
- Track C: RB-06 (fd-ribosome-stall-rescue) — "co-translational folding; downstream synthesis begins before upstream completes"

Two within-track surfacings; not cross-track but mechanism-aligned with QT-01 dispatch issue.

**Combined confidence**: medium-high. **Recommended action**: timeout-and-proceed policy in flux-watch.sh + `interflux:fetch-findings` streaming mode. S.

### 7. Bead deduplication via embedding (3/4 tracks)

**Convergence pattern**: `bd search` before `bd create` is workflow-discipline-dependent LLM judgment; embedding cosine + label overlap + recency form a deterministic three-signal gate.

**Independent surfacings**:
- Track A: R-03 (fd-llm-routing-replaceability)
- Track C: KF-02 (fd-kalman-filter-fusion) — "steady-state Kalman; 4,250 tok/session; cosine > 0.85 + label overlap + status=open"
- Track D: POLY-5 (fd-polynesian-wayfinding-fusion) — "bird homing tertiary signal; 3-gram exact + cosine + recency"

**Combined confidence**: high. **Recommended action**: `bd create --check-dup` with embedding lookup. S.

### 8. Doc authority / canonical witness (2/4 tracks)

**Convergence pattern**: brainstorms, handoffs, regenerated artifacts coexist with no authority ordering; agents pick stale versions.

**Independent surfacings**:
- Track D: SCRIP-1 (fd-medieval-scriptorium-rubrication) — "exemplar-index.yaml"; SCRIP-2 — "canonical witness designation"; SCRIP-3 — "corrector's pass frontmatter gate"
- Adjacent A finding: B-04 (fd-context-budget-orchestration) — "CLAUDE.md/AGENTS.md double-load; pointer doesn't gate deferred load"

**Combined confidence**: medium. **Recommended action**: `docs/canon/exemplar-index.yaml` + canonical paths for interpath outputs. S.

## Top 10 Recommended Actions

1. **MEMORY.md restructure (reorder + churn-to-bottom + topic-file frontmatter)**
   Axis: token-efficiency + usability. Difficulty: S (composite XS pieces). Savings: ~3-4kt/session.
   Source: B-01, C-01, FIRN-1, FIRN-2, RB-02, SCRIP-4 (4/4 tracks). The single highest-leverage change because six independent reasoning paths converged on the same target file.

2. **Content-address OUTPUT_DIR + REVIEW_FILE (kill timestamps)**
   Axis: token-efficiency. Difficulty: S. Savings: 21K tok/session.
   Source: BSC-1, BSC-2, C-05 (3/4 tracks). Single-line sha256 substitution at SKILL.md:112 unlocks all cross-run prompt cache.

3. **Concurrency cap on /flux-review (MAX_CONCURRENT=6 semaphore)**
   Axis: token-efficiency + usability. Difficulty: S. Savings: ~24K tok/affected review + 30% retry waste eliminated.
   Source: QT-01, BSC-3. One-line change in phases/launch.md.

4. **SessionStart dirty-bit cache (`.claude/session-state.json`)**
   Axis: token-efficiency. Difficulty: S. Savings: 10-16K tok/hr idle + enables MPC-01 + B-03.
   Source: IC-01, MPC-02, B-03. Generalize gen-skill-compact.sh manifest pattern to lib-freshness.sh.

5. **Signal-peptide / SRP prefix router for skill routing**
   Axis: ml-routing-replacement. Difficulty: S. Savings: ~7,800 tok/session (60% short-circuit).
   Source: R-02, SER-02, KF-01, RB-03, POLY-2 (4/4 tracks). Auto-generate prefix table from skill manifest; LLM only on table miss.

6. **Embedding-based agent-triage replacement (`flux-agent score-relevance`)**
   Axis: ml-routing-replacement. Difficulty: M. Savings: 45-90kt/week (≈4.5kt × 10-20 runs).
   Source: R-01, SER-01, KF-03, POLY-1 (4/4 tracks). Cached agent embeddings + cosine; LLM only for 0.5-0.7 ambiguous band.

7. **MCP server hygiene: gate Anthropic OAuth tools + collapse name prefixes**
   Axis: token-efficiency. Difficulty: S + M. Savings: ~2-3kt/session combined.
   Source: M-01, M-02, M-03. Workspace-aware mcpProfile; trim `mcp__plugin_X_X__X` redundancy; move tldr-swinton instructions to per-tool description.

8. **Stall-rescue detection in flux-watch.sh (60s no-output → error stub)**
   Axis: usability. Difficulty: S. Savings: 16 minutes per stalled review.
   Source: RB-01. Direct Pelota/Hbs1 mapping; emits peer finding for transparency.

9. **Embedding-based bead dedup (`bd create --check-dup`)**
   Axis: ml-routing-replacement. Difficulty: S. Savings: ~4,250 tok/session.
   Source: R-03, KF-02, POLY-5 (3/4 tracks). Cosine over open beads + label overlap; user-confirmation gate above 0.7.

10. **Plugin/skill prefix disambiguation + canonical witness designation for interpath outputs**
    Axis: usability + token-efficiency. Difficulty: S. Savings: ~300-500 tok/session + significant friction reduction.
    Source: IDE-01/02/03, SCRIP-2. Semantic short-prefix aliases; `docs/vision.md` canonical + archived witnesses.

## Domain-Expert Insights (Track A)

**Cache architecture (fd-prompt-cache-economics)**: The cache-cursor model is the under-articulated framework — stable text first, churn last. Three findings (C-01, C-03, C-05) all derive from this single principle but apply at different scopes (file, hook output, subagent prompt). The /loop default at 5min boundary (C-03) is a specific failure mode of cache-aware polling that no other track surfaced — wakeups land exactly at the worst-case TTL boundary; 240s default fixes it.

**MCP economics (fd-mcp-server-hygiene)**: The deferred-tool listing surfaces what is actually loaded — and the OAuth integrations cluster (Notion/Gmail/Calendar/Drive) is paid every dev session for <5% usage. M-03 surfaced the tldr-swinton 600-token instructions block as a per-server cost ladder that's marketing copy; this is generalizable across plugins via a "instructions= must fit in 100 tokens" rule.

**Routing economics (fd-llm-routing-replaceability)**: Five replaceable LLM-routing decisions with concrete feature vectors and precision floors. R-05 (voice fidelity) is unusual because the user has already named the load-bearing markers (em-dash density, contrastive reframes, "one's" usage) in feedback memory — the stylometric features are pre-specified.

**Context budget (fd-context-budget-orchestration)**: B-02's skill-description boilerplate audit (~3-5kt of repeated TRIGGER/SKIP/Examples framing) is the highest single-target token win. B-03's three-hooks-state-the-same-protocol is a reuse-not-rebuild lesson — AGENTS.md is the canonical source, hooks should emit status only.

## Parallel-Discipline Insights (Track B)

**Search engine ranking → agent triage (SER-01)**: Two-tower architecture mismatch. Sylveste skips the BM25/embedding candidate-gen stage and applies LLM cross-encoder reranking to all 679 agents — backwards from production search. Fix: intersearch top-30 + LLM rerank.

**Bazel hermeticity → prompt cache (BSC-1, BSC-2)**: Bazel rejects build inputs containing `$(date +%s)` because they defeat content-addressed caching. Sylveste embeds `RUN_TS` at SKILL.md:112 — same pathology, same fix.

**TypeScript watch mode → SessionStart hooks (IC-01)**: tsc only recompiles changed files; Sylveste's hooks fire `bd prime` regardless of state. The dirty-bit + manifest pattern from gen-skill-compact.sh is the local prior art — generalize it.

**IDE prefix narrowing → plugin disambiguation (IDE-01)**: IntelliJ convention — 3-5 chars typed should narrow to <10 options. Sylveste's `/inter` yields 116. Salsa/IntelliJ context-action ranking (IDE-03) maps directly to context-aware status routing.

## Structural Insights (Track C)

**Kalman innovation gating (KF-01)**: invoke the expensive sensor (LLM) only when cheap sensors disagree. Each routing decision has 3-4 measurable cheap signals; the Kalman gain formula gives the math for when their fused variance crosses a threshold. Implementable today as `lib-fusion.sh` (KF-I1).

**MPC receding-horizon (MPC-01)**: budget gates today are bang-bang (run until limit). Horizon-N planning estimates cost feedforward and replans. Requires constraint-state object (MPC-02 = session-state.json) — already specified at S difficulty. Implementable.

**M/M/k queueing (QT-01)**: Erlang C formula predicts 30% retry waste at the 16-agent fan-out tier. Concurrency cap is the textbook fix. Implementable in <10 lines.

**Ribosome rescue (RB-01)**: Pelota/Hbs1 detect empty A-site (no output for N seconds) → split ribosome, degrade peptide. Maps directly to flux-watch.sh stall detection. Already designed at S difficulty.

**No-go decay (RB-04)**: track finding-action rate per agent → down-weight low-signal agents in future triage. Requires CASS analytics pipeline — partially implementable; finding-ID-to-commit-message cross-reference is the missing piece.

## Frontier Patterns (Track D)

**Polynesian wayfinding (POLY-1, POLY-2)**: multi-signal fusion + star-compass discretization. Maps surgically: 4-house keyword classifier (POLY-2) and 3-signal triage fusion (POLY-1) are concrete, S-difficulty, and converge with three other tracks. **Genuinely useful** — produced a stronger framing of skill routing than the inner tracks alone (the discreteness insight that 4 houses cover 60% of routes is not present in Track A's R-02).

**Polynesian (POLY-3)**: continuous-float scoring should be 4-bucket discrete. Token saving is small (150-200) but the prompt-engineering principle generalizes. **Useful but minor**.

**Glaciology firn (FIRN-1, FIRN-2)**: append-only deposition headers + close-off depth tiering. **Genuinely useful** — Track A's MEMORY.md analysis missed the provenance issue (when was a feedback rule added? confirmed how often?). The firn lens forces this question. FIRN-4's trapped-air-signature handoff frontmatter is also novel: machine-readable bead+memory hash at handoff close, with diff alert on next session.

**Glaciology (FIRN-3, FIRN-5)**: annual layer indexing + hiatus detection. Sprint-boundary layer markers in beads are useful (`bd list --sprint authz-v2`); hiatus detection is more speculative — projects with active brainstorm phases would false-positive. **Mixed: FIRN-3 useful, FIRN-5 stays poetic**.

**Medieval scriptorium (SCRIP-1, SCRIP-2)**: exemplar hierarchy + canonical witness selection. **Genuinely useful** — Track A's B-04 (CLAUDE.md/AGENTS.md double-load) noted the doc-pointer-doesn't-gate-load problem; SCRIP-1's exemplar-index.yaml gives the explicit machine-readable authority ordering that resolves it. SCRIP-2's canonical witness pattern resolves interpath:vision regeneration drift that no inner track addressed.

**Scriptorium (SCRIP-3, SCRIP-4)**: corrector's pass frontmatter + body-vs-marginalia split. SCRIP-4 (rule vs commentary in feedback files) is concrete and meaningfully large (~2,250 tok/session); SCRIP-3 (status: draft|reviewed|canonical) is structural and complementary. **Both useful**.

**Scriptorium (SCRIP-5)**: Tironian-notes doc-routing table. Useful but small impact (~1,400 tok/session); essentially a generalization of the signal-peptide pattern from RB-03 to a different decision surface.

## Synthesis Assessment

**Overall current-state quality**: Sylveste's orchestration is a working but unoptimized v1 — the architecture is sound (per-project Dolt, content-addressed prior art in gen-skill-compact.sh, intersearch embeddings already available) but the patterns aren't generalized. The cheap wins are unusually cheap: 5 of the top 10 actions are S-or-XS difficulty. The expensive wins (M-difficulty embedding-based routing) replace the system's largest invisible cost (~1.5Mt/week of skill-routing inference).

**Highest-leverage single change**: MEMORY.md restructure (action #1). Six independent reasoning paths converged on this file at different semantic distances — a convergence score this high indicates the issue is structural, not stylistic. Reordering churn-to-bottom (XS), moving Active Projects to `bd ready` (XS), adding `expires_after` (S), and splitting Rule/Marginalia (XS) compounds to ~3-4kt/session with effort under one day.

**Most surprising finding**: SCRIP-2's canonical-witness designation for interpath outputs. No inner-track agent considered that interpath:vision regenerating without overwriting creates a stemmatic textual-criticism problem — multiple witnesses of the same text with no canonical designation. The medieval-manuscript framing produced this because manuscript reproduction is structurally identical to artifact regeneration. The fix (always-overwrite canonical path + archive timestamped witnesses) is XS but no Track A/B/C agent surfaced it.

**Semantic distance value**: Tracks C and D contributed qualitatively different insights, not vocabulary restatement. Track C's structural-mechanism focus produced concrete implementation patterns that Track A's domain-expert findings stated as "do this" without the underlying principle (KF-01's variance-weighted fusion vs R-02's "embedding pre-filter" gives the mathematical condition for when the gate fires). Track D's frontier patterns produced two novel findings (FIRN-1 provenance, SCRIP-2 canonical witness) that no inner track surfaced. The signal-peptide framing (RB-03) is the same finding as KF-01/R-02 but its specific implementation (auto-generate prefix table from skill manifest commands) is more concrete than KF-01's "fusion layer." Net: outer tracks earn their seat — they're not noise.

The convergence pattern itself (4/4 on agent triage, skill routing, and MEMORY.md) is the strongest possible evidence that these aren't artifacts of any single agent's framing. The orthogonal-domain experts saw the same gaps as the adjacent-domain experts.

## Implementation Sequencing

### Phase 1 — One-week sprint (XS difficulty, high savings)

Goal: clear 5kt/session of preamble cost + unlock cache hits.

- **MEMORY.md reorder**: churn-to-bottom; Active Projects → `bd ready` indirection (B-01, C-01, FIRN-2). XS. ~1.5kt/session.
- **MEMORY.md topic-file split**: `## Rule` / `## Marginalia` (SCRIP-4). XS. ~2.25kt/session.
- **Content-address OUTPUT_DIR + REVIEW_FILE**: replace `RUN_TS` with sha256 (BSC-1, BSC-2, C-05). S. ~21kt/session on cache-eligible runs.
- **Concurrency cap on /flux-review**: MAX_CONCURRENT=6 semaphore (QT-01). S. 30% retry waste eliminated.
- **MCP OAuth gating**: `mcpProfile: dev` setting; suppress Notion/Gmail/Calendar/Drive (M-01). S. ~1kt/session.
- **tldr-swinton instructions trim**: move cost-ladder text to per-tool description (M-03). XS. ~500 tok/session.
- **/loop default to 240s**: stay inside 5min cache TTL (C-03). XS. ~12-24kt/hr on active loops.
- **Stall-rescue detection in flux-watch.sh** (RB-01). S. 16 min/stalled review.
- **Canonical witness designation for interpath outputs** (SCRIP-2). XS. Stops drift between regenerated artifacts.

Combined Phase 1 estimated savings: ~25-30kt/session token + significant UX wins.

### Phase 2 — One-month effort (S difficulty, multi-finding alignment)

Goal: dirty-bit + routing replacement infrastructure.

- **`.claude/session-state.json` + lib-freshness.sh** (IC-01, MPC-02, IC-06): generalize gen-skill-compact.sh manifest pattern. S. Unlocks idle-loop savings + MPC-01 budget planning.
- **Signal-peptide prefix router for skill routing** (R-02, RB-03, POLY-2, KF-01): auto-generate prefix table from skill manifest. S. ~7.8kt/session.
- **`bd create --check-dup`**: embedding lookup over open beads (R-03, KF-02, POLY-5). S. ~4.25kt/session.
- **`flux-agent score-relevance`**: cached agent embeddings + cosine pre-filter for triage (R-01, SER-01, KF-03, POLY-1). S. ~45-90kt/week.
- **Plugin prefix disambiguation + review/status command scoping** (IDE-01, IDE-02, IDE-03). S-M. UX.
- **Memory deposition headers + `expires_after`** (FIRN-1, RB-02): append-not-overwrite semantics. M. Provenance + staleness.
- **`docs/canon/exemplar-index.yaml`**: doc authority ordering (SCRIP-1). S. Eliminates doc-conflict friction.
- **Hook priority scheduling + circuit breaker** (QT-04, QT-03). S-M. Per-turn latency bounded.

Combined Phase 2 estimated savings: ~10-15kt/session + 60-100kt/week routing savings.

### Phase 3 — Quarter-class (M+ difficulty, infrastructure-class)

Goal: replace LLM-routing economics + MPC budget control + cross-session caching.

- **Skill-description schema standardization** (B-02): cross-plugin migration via interskill:audit --compress. M. ~2-4kt/session.
- **MCP tool-name prefix collapse** (M-02): registry rename + alias migration. M. ~800-1300 tok/session.
- **MPC horizon-N planner in /sprint** (MPC-01): cost-model.yaml + receding-horizon replanner + control-effort minimization (MPC-04). M. ~2kt/sprint bust + budget-aware tier downgrade.
- **Cross-session findings cache** (BSC-4, BSC-5): content-hash-keyed; incremental rerun on small fix. L. ~96kt/repeat-review, 384kt/incremental-rerun.
- **Streaming synthesis** (RB-06, QT-02): co-translational folding via `interflux:fetch-findings` streaming mode. M. 2-3 min/large review.
- **No-go decay agent down-weighting** (RB-04): finding-action-rate tracking via CASS + git/bead cross-ref. M. 10-20% triage budget over time.
- **Distillation pipeline** (R-I1): Intercept-style Haiku → log → xgboost for R-01/R-02 if simple cosine misses precision floor. M-L.
- **Voice fidelity stylometric scorer** (R-05, KF-04): em-dash density + contrastive-reframe regex + sentence-length distribution. S, deferred to Phase 3 because of low aggregate volume. ~630 tok/session.

Combined Phase 3 estimated savings: structural win — replaces the system's largest invisible cost (per-turn skill routing inference) and most expensive primitive (full /flux-review re-run).
