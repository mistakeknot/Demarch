# Flux-Drive Resilience Review: Intermem Architecture Decision

**Reviewer:** fd-resilience (Flux-Drive Adaptive Capacity Agent)
**Document:** `/tmp/intermem-brainstorm-context.md`
**Date:** 2026-02-16
**Scope:** Architecture options for intermem memory plugin

---

## Executive Summary

This review evaluates four architecture options for intermem through the lens of adaptive capacity: antifragility, resource dynamics, creative constraints, and innovation patterns. The document presents a clear decision space but exhibits three critical blind spots:

1. **P1 BLIND SPOT**: No failure recovery analysis for the consolidation engine (Option 2) — what happens when the canonical store corrupts?
2. **P1 BLIND SPOT**: No staged risk analysis for MVP sequencing — which option allows smallest reversible bet?
3. **P2 MISSED LENS**: Blast radius analysis incomplete — impact of intermem failure on dependent systems underexplored

**Key Finding:** Option 3 (Smart Layer on Top) is the most antifragile choice when combined with proper MVP staging. Option 2 (Consolidation Engine) carries the highest adaptive capacity risk due to single-source-of-truth fragility.

---

## Review Framework

This review applies 12 cognitive lenses from the resilience and adaptation domain:

1. **Antifragility** — Systems that gain from disorder
2. **Graceful Degradation** — Designing for partial failure
3. **Redundancy vs. Efficiency** — Backup capacity vs. lean operations
4. **Creative Constraints** — Limitations driving innovation
5. **First Principles** — Reasoning from fundamentals
6. **Assumption Locks** — Inherited but invalid constraints
7. **Diminishing Returns** — When more effort produces less value
8. **Staging & Sequencing** — Breaking large bets into reversible steps
9. **Resource Bottleneck** — Single constraint limiting throughput
10. **Creative Destruction** — Dismantling the old for the new
11. **MVP Thinking** — Smallest experiment testing riskiest assumption
12. **Phoenix Moments** — Crises creating opportunities

---

## P1 Findings: Critical Blind Spots

### 1. Failure Recovery Missing for Option 2 (Consolidation Engine)

**Section:** Option 2 description (lines 17-21)
**Lens Applied:** Graceful Degradation, Antifragility
**Severity:** P1 (entire analytical frame absent)

**The Gap:**

Option 2 proposes a "single canonical store" where all existing systems become "write endpoints" feeding into intermem. The document acknowledges "risk of divergence" as a con but never analyzes what happens when the canonical store **fails, corrupts, or becomes unavailable**.

**Questions the document MUST answer:**

- **Storage corruption:** If the SQLite database corrupts (disk failure, process crash during write, schema migration error), can the system rebuild from source stores? If not, all memory is lost.
- **Embedding drift:** When the embedding model changes (OpenAI deprecates an endpoint, you switch providers, version upgrades), how do you re-embed 10,000+ memories without downtime?
- **Recovery time:** If intermem goes down, how long does it take to restore service? Minutes? Hours? Days?
- **Fallback path:** Can agents continue working with the old memory stores while intermem is being rebuilt, or does consolidation create a hard dependency?

**Why this matters:**

A single source of truth is the **opposite of antifragile**. It concentrates failure risk. In contrast, Option 1 (Federation Layer) and Option 3 (Smart Layer on Top) preserve the original stores as redundant backups. If intermem fails, agents degrade gracefully to direct file reads.

**Specific Recommendation:**

Before choosing Option 2, the document must include a "Failure Recovery" section analyzing:
1. Backup/restore strategy for the canonical store
2. Source store replay capability (can you rebuild from compound docs + auto-memory?)
3. Fallback modes when intermem is unavailable
4. Mean time to recovery (MTTR) for storage corruption

Without this analysis, Option 2 is **not production-ready**.

---

### 2. MVP Staging Missing — No Analysis of Reversible First Steps

**Section:** "Questions for Analysis" #4 (line 113)
**Lens Applied:** Staging & Sequencing, MVP Thinking
**Severity:** P1 (entire analytical frame absent)

**The Gap:**

The document asks "What's the minimum viable version that delivers the most value?" but provides **no analysis** of how to stage the four options from smallest bet to full vision. This is a critical omission because:

- **Option 4 (Replace Everything)** is explicitly labeled "high risk, long timeline" but the document provides no alternative sequencing to de-risk it.
- **Option 2 (Consolidation)** creates a hard cutover point where you commit to the new architecture — if it fails after migration, rolling back is expensive.
- **Options 1 and 3** are inherently staged (additive, non-destructive) but the document doesn't recognize this as a strategic advantage.

**Questions the document MUST answer:**

1. **What's the smallest increment that tests the riskiest assumption?**
   - For Option 1: Can you start with read-only federation of 2 stores (e.g., auto-memory + compound) before adding all 5?
   - For Option 2: Can you run consolidation in shadow mode (write to canonical store but continue serving from originals) to validate the approach before cutover?
   - For Option 3: Can you add just validation metadata first (no decay, no cross-project) to prove the overlay pattern works?
   - For Option 4: Can you replace just one store (e.g., interfluence learnings) before touching the others?

2. **What's the rollback cost if the MVP fails?**
   - Option 1: Low — just stop querying the federation layer, revert to direct reads
   - Option 2: High — migration is one-way, rolling back requires restoring from backups
   - Option 3: Low — overlay is metadata-only, delete it and originals are untouched
   - Option 4: Catastrophic — you've destroyed the old stores, can't go back

3. **What's the learning checkpoint?** When do you decide whether to continue, pivot, or abandon?

**Why this matters:**

Without staged risk analysis, you can't make an informed decision. A "high risk, long timeline" option (Option 4) might be acceptable if staged properly, or unacceptable if it requires a big-bang cutover. The document treats these as static choices when they should be viewed as **risk sequencing decisions**.

**Specific Recommendation:**

Add a "Risk Staging Matrix" section that maps each option to:
- **Phase 1 MVP** (smallest reversible test)
- **Phase 2 Expansion** (add more stores, features, or scale)
- **Phase 3 Full Vision** (complete the architecture)
- **Rollback cost** at each phase
- **Decision gate** criteria (when to advance or retreat)

This transforms the decision from "which option?" to "which **sequence** minimizes irreversible commitments?"

---

### 3. Blast Radius Underexplored — Dependency Impact Analysis Missing

**Section:** "Interverse-Specific Considerations" (lines 98-106)
**Lens Applied:** Redundancy vs. Efficiency, Resource Bottleneck
**Severity:** P1 (blind spot with concrete risk)

**The Gap:**

The document mentions multi-agent coordination (interlock, intermute) and token efficiency (interstat) but never analyzes **what breaks if intermem is unavailable**. This is critical because:

- 20+ plugins in the ecosystem
- 5 existing memory stores that are currently working
- Multi-agent workflows with file coordination dependencies
- Clavain has 12 hooks already — adding intermem hooks increases failure surface

**Questions the document MUST answer:**

1. **Direct dependencies:** Which plugins/systems explicitly depend on intermem being available?
   - If Clavain's auto-compound hook expects intermem to validate memories before writing, what happens when intermem is down? Does compound doc creation fail?
   - If interlock expects intermem to store reservation provenance, does file coordination break?

2. **Implicit dependencies:** Which workflows degrade when intermem is unavailable?
   - Do agents continue to function with stale memory?
   - Do they retry failed memory writes and create backpressure?
   - Do they silently drop learnings?

3. **Cascading failures:** Can intermem failure trigger failures in other systems?
   - If intermem holds a lock on a SQLite database and crashes, does it deadlock other plugins?
   - If intermem is slow (embedding API timeout), does it block hook execution and freeze Claude Code sessions?

4. **Blast radius by option:**
   - **Option 1 (Federation):** Failure = queries fail, agents fall back to direct file reads (low blast radius)
   - **Option 2 (Consolidation):** Failure = all memory writes fail, agents can't learn (high blast radius)
   - **Option 3 (Smart Layer):** Failure = overlay unavailable, agents fall back to base stores (low blast radius)
   - **Option 4 (Replace Everything):** Failure = total memory system outage (catastrophic blast radius)

**Why this matters:**

Interverse already has a complex dependency graph with coordination primitives (interlock, intermute) and shared infrastructure (intersearch). Adding a centralized memory system creates a **new single point of failure** unless explicitly designed for graceful degradation.

**Specific Recommendation:**

Add a "Blast Radius Analysis" section that includes:
1. **Dependency graph** showing which systems call intermem and what they do when it fails
2. **Failure modes table** mapping intermem outage types (crash, slow, corrupt data) to downstream impact
3. **Graceful degradation strategy** for each option (what's the fallback behavior?)
4. **Monitoring requirements** to detect and alert on intermem health (latency, error rate, staleness)

This is not just a technical concern — it's a **resilience architecture decision**. The document cannot evaluate options without understanding their blast radius.

---

## P2 Findings: Underexplored Lenses

### 4. Resource Bottleneck Risk for Option 2 (Consolidation Engine)

**Section:** Option 2 description (lines 17-21)
**Lens Applied:** Resource Bottleneck, Diminishing Returns
**Severity:** P2 (relevant frame mentioned but underexplored)

**The Gap:**

Option 2 proposes all writes flow through intermem for deduplication, decay scoring, and validation. This creates a **write bottleneck** if intermem becomes the critical path for memory operations. The document mentions "heavier infrastructure" as a con but doesn't explore the performance implications.

**What's missing:**

- **Throughput analysis:** If 10 concurrent agents are running (Clavain + 9 background workers), each generating memories at tool use boundaries (Edit hook → interfluence, compound signal accumulation), can intermem handle the write load?
- **Latency impact:** If deduplication requires semantic search across all existing memories (10,000+ embeddings), does that add 500ms to every write? Does that block agent progress?
- **Backpressure handling:** If intermem's write queue fills up, do hooks fail synchronously (blocking Claude Code) or drop writes silently (data loss)?

**Contrast with other options:**

- **Option 1 (Federation):** Reads are distributed across backends, no single bottleneck
- **Option 3 (Smart Layer):** Writes go to original stores first (fast), overlay updates asynchronously (non-blocking)
- **Option 4 (Replace Everything):** Same bottleneck risk as Option 2

**Specific Recommendation:**

Add a "Throughput Constraints" subsection under Option 2 that estimates:
- Expected write volume (memories/second during peak multi-agent load)
- Per-write latency budget (how long can a hook block?)
- Queue depth and overflow strategy (sync vs. async writes, retry vs. drop)
- Horizontal scaling path (can you shard the memory store by project? by time range?)

This transforms "heavier infrastructure" from a vague con into a **quantified design constraint**.

---

### 5. Assumption Lock: "Existing Stores Must Be Preserved"

**Section:** Option 3 and Option 4 trade-offs
**Lens Applied:** Assumption Locks, Creative Destruction
**Severity:** P2 (inherited constraint worth questioning)

**The Gap:**

The document treats "existing stores keep working unchanged" (Option 3 pro) and "loses battle-tested patterns" (Option 4 con) as unquestioned constraints. But this might be an **assumption lock** — an inherited belief that's no longer optimal.

**Questions to surface:**

1. **Are all 5 existing stores providing value, or are some legacy cruft?**
   - Auto-memory: 200-line cap, injected every session → this is working, preserve it
   - Compound docs: Signal-weighted, battle-tested → working, preserve it
   - Interfluence learnings: MCP-accessible, style-specific → working, preserve it
   - `.clavain/learnings/`: Manual markdown → is this redundant with compound? Could it be absorbed?
   - `CLAUDE.md/AGENTS.md`: Always loaded → definitely keep

2. **Is "non-destructive" always better?**
   - Option 3's "non-destructive" overlay sounds safe, but what if the overlay adds enough complexity that the combined system is **more brittle** than a clean rebuild?
   - Technical debt accumulates from compatibility layers. Is preserving 100% of existing behavior worth the long-term maintenance cost?

3. **What would first-principles memory design look like?**
   - If you were building from scratch with the lessons from 13 external systems (MemCP's 4-graph, claude-brain's single binary, memory-mcp's decay), would you create 5 separate stores? Probably not.
   - But that doesn't mean Option 4 (Replace Everything) is the answer — it means you should question whether Option 3's overlay is just "Option 4 with extra steps."

**Why this matters:**

The document is **anchored** to incremental thinking (Options 1-3) because the ecosystem is complex and change is risky. But sometimes **creative destruction** (Option 4) produces a simpler, more maintainable outcome. The key is **staging** (see Finding #2) — you don't have to choose "preserve everything" or "burn it down." You can replace one store at a time, learning as you go.

**Specific Recommendation:**

Add an "Assumption Check" section that asks:
- **Which existing stores are load-bearing vs. legacy?** (usage data, dependency graph)
- **What's the cost of maintaining compatibility?** (code complexity, performance overhead, maintenance burden)
- **Could a hybrid approach work?** (e.g., keep auto-memory + compound, replace the other 3)

This isn't a call to choose Option 4 — it's a call to **make the preservation decision explicit** rather than treating it as an unquestioned constraint.

---

### 6. Embedding Model Lock-In Risk (Options 2 & 4)

**Section:** Landscape research mentions MemCP 4-graph, claude-mem Chroma vectors (lines 69-83)
**Lens Applied:** Antifragility, Assumption Locks
**Severity:** P2 (relevant risk underexplored)

**The Gap:**

Options 2 and 4 both create a canonical embedding-backed store. The document mentions intersearch already has embeddings (line 105) but doesn't analyze the **lock-in risk** of embedding dependencies:

1. **Model versioning:** OpenAI's text-embedding-3-small is the current default, but what happens when they deprecate it or release v4? Do you re-embed all memories or maintain multiple embedding spaces?
2. **Provider switching:** If you start with OpenAI embeddings and later want to switch to Cohere or a local model (privacy, cost, latency), is that a full data migration?
3. **Embedding drift:** MemCP's research (line 75) mentions 218x token reduction via semantic indexing, but what's the accuracy loss? If embeddings don't capture exact matches (e.g., "bug in line 42" vs. "line 42 bug"), does retrieval fail?

**Why this matters:**

Embedding-backed stores are **less antifragile** than text-based stores because:
- Text files can be read by any tool (grep, editors, git)
- Embeddings require the exact model + API to be useful
- Vector databases add infrastructure dependencies (Chroma, Pinecone, or custom SQLite extensions)

**Contrast with other options:**

- **Option 1 (Federation):** No new embedding dependency, queries existing stores as-is
- **Option 3 (Smart Layer):** Could add embeddings for search but preserve text-based originals as fallback

**Specific Recommendation:**

Add an "Embedding Strategy" subsection that addresses:
- **Versioning strategy:** How to handle model upgrades without full re-embedding
- **Fallback retrieval:** Can you fall back to keyword search if embeddings fail?
- **Migration path:** If you need to switch embedding providers, what's the cost?

This is especially important because **intersearch already exists** — the document should explicitly analyze whether to reuse its embedding infrastructure or build something new.

---

## P3 Findings: Enhancement Opportunities

### 7. MVP Thinking: Test the Riskiest Assumption First

**Section:** "Questions for Analysis" #4 (line 113)
**Lens Applied:** MVP Thinking, First Principles
**Severity:** P3 (enrichment opportunity)

**The Opportunity:**

All four options share a common risky assumption: **that unified memory retrieval is actually valuable to agents**. The document assumes memory fragmentation is a problem but provides no evidence.

**Experiment to validate assumption:**

Before building any of the four options, run this experiment:

1. **Instrument existing memory reads:** Add logging to auto-memory injection and compound doc lookups to see how often memories are retrieved, how many are relevant, and how much token budget they consume.
2. **Synthetic federation test:** Manually create a "memory digest" that combines excerpts from all 5 stores for one project. Run a Clavain session and ask agents to solve a complex problem. Does unified retrieval improve outcome?
3. **User study:** Ask 5 users to identify their top 3 memory pain points. Is "fragmentation" on the list, or are the real problems "too much noise," "stale memories," or "can't find what I saw yesterday"?

**Why this matters:**

If the risky assumption is **wrong** — if agents don't actually benefit from unified retrieval — then the whole decision space collapses. You might discover that the real problem is **memory quality** (validation, decay), not **memory access** (federation, consolidation). In that case, the winning solution is much simpler: add validation hooks to existing stores, don't build a new memory layer at all.

**Specific Recommendation:**

Before choosing an architecture, run a **1-day validation experiment** that tests whether unified memory retrieval improves agent performance. This is the smallest possible MVP and it costs almost nothing.

---

### 8. Phoenix Moment: Memory Crisis as Opportunity

**Section:** Implicit in the document's motivation
**Lens Applied:** Phoenix Moments
**Severity:** P3 (reframing opportunity)

**The Opportunity:**

The document treats memory fragmentation as a problem to solve, but it could be reframed as an **opportunity** to rethink what agent memory should be.

**Current state:**
- 5 stores, each designed for a specific use case (auto-memory for sessions, compound for solutions, interfluence for style)
- No decay, no validation, no cross-project sharing (7 gaps from landscape, lines 89-96)
- Works but doesn't scale — Interverse has 20+ plugins and growing

**Phoenix moment:**
- The memory system is **constrained** by legacy decisions (5 separate stores), which creates **creative pressure** to unify
- But unification isn't the only solution — you could also **embrace fragmentation** and add a discovery layer (semantic search across heterogeneous stores without consolidation)
- Or you could **invert the problem**: instead of "how do I retrieve memories," ask "how do I prevent bad memories from being created?"

**Why this matters:**

The document is stuck in **solution space** (4 architecture options) without fully exploring **problem space** (what is memory for?). A phoenix moment reframe might reveal that:

- **Validation matters more than retrieval** → invest in pre-write filtering (ShieldCortex-style security, Copilot-style citation checking) rather than post-write indexing
- **Decay matters more than consolidation** → add TTLs to existing stores rather than building a new one
- **Provenance matters more than centralization** → add "who learned this, when, why" metadata to existing stores

**Specific Recommendation:**

Add a "Problem Reframe" section that asks:
- **What is memory for?** (retrieval? prevention of repeated mistakes? cross-session continuity? team knowledge sharing?)
- **What's the root cause of the current pain?** (fragmentation? noise? staleness? lack of trust?)
- **Could a non-architectural solution solve it?** (better prompts, tool use analytics, user training)

This isn't a call to abandon the architecture decision — it's a call to **validate that architecture is the right lever** before pulling it.

---

## Comparative Resilience Analysis

Evaluating the four options through the resilience lenses:

| Dimension | Option 1: Federation | Option 2: Consolidation | Option 3: Smart Layer | Option 4: Replace All |
|-----------|---------------------|------------------------|---------------------|---------------------|
| **Antifragility** | ✅ High — failures localized to single backend | ❌ Low — single source of truth is fragile | ✅ High — overlay failure → fallback to base | ❌ Very Low — no fallback, total dependence |
| **Graceful Degradation** | ✅ Excellent — partial failure = partial loss | ⚠️ Poor — canonical store outage = total loss | ✅ Excellent — overlay down → base stores work | ❌ None — memory system is all-or-nothing |
| **Redundancy** | ✅ 5 independent stores preserved | ❌ Redundancy eliminated by design | ✅ Base stores + overlay = double redundancy | ❌ No backup, canonical store only |
| **Resource Bottleneck** | ✅ Distributed reads, no single chokepoint | ❌ All writes through intermem (bottleneck risk) | ✅ Async overlay updates, no blocking writes | ⚠️ Same bottleneck risk as Option 2 |
| **Rollback Cost** | ✅ Low — stop federation, revert to direct reads | ❌ High — migration is one-way, needs restore | ✅ Very Low — delete overlay, originals intact | ❌ Catastrophic — destroyed old stores |
| **Blast Radius** | ✅ Small — intermem down = degraded search only | ❌ Large — intermem down = no memory writes | ✅ Small — intermem down = no validation/decay | ❌ Total — intermem down = agents blind |
| **MVP Staging** | ✅ Can federate 2 stores first, add rest later | ⚠️ Needs shadow mode to de-risk cutover | ✅ Can add validation first, defer other features | ❌ Requires phased replacement per store |

**Overall Resilience Ranking:**

1. **Option 3 (Smart Layer)** — Best resilience profile, incremental, reversible
2. **Option 1 (Federation)** — Good resilience, but limited feature set (can't add decay/validation)
3. **Option 2 (Consolidation)** — Poor resilience, high migration risk, bottleneck concerns
4. **Option 4 (Replace All)** — Worst resilience, catastrophic failure modes

---

## Recommended Architecture: Option 3 with Staged MVP

Based on the resilience analysis, **Option 3 (Smart Layer on Top) with proper MVP staging** is the optimal choice for Interverse.

### Why Option 3 Wins on Adaptive Capacity

1. **Non-destructive:** Existing stores continue working unchanged. If intermem fails, agents degrade gracefully to base stores (auto-memory, compound, interfluence).
2. **Incremental feature addition:** Can add validation first (P0), then decay (P1), then cross-project (P2), then provenance (P3). Each increment is reversible.
3. **Low blast radius:** Intermem failure only loses overlay features (validation, decay, cross-project search). Core memory reads/writes continue.
4. **Embedding flexibility:** Can use intersearch for semantic overlay without forcing all stores to adopt embeddings.
5. **Multi-agent compatible:** Overlay metadata (last validated, confidence score) can be written asynchronously without blocking hooks or coordination primitives (interlock).

### Staged MVP for Option 3

**Phase 1: Validation Overlay (2 weeks)**
- Add `.intermem/metadata.db` SQLite store (per-project)
- Schema: `(memory_path, last_validated, confidence, validation_method)`
- Hook: PreCompact reads memories, validates citations (Copilot-style), writes metadata
- Retrieval: Auto-memory injection checks metadata, skips low-confidence memories
- **Decision gate:** Does validation reduce stale memory injection by >30%? If not, pivot.

**Phase 2: Decay Overlay (2 weeks)**
- Add `last_accessed`, `access_count`, `ttl` fields to metadata
- Hook: SessionStart updates access timestamps, SessionEnd applies decay rules
- Retrieval: Auto-memory injection respects TTLs (e.g., "context" memories expire after 30 days per memory-mcp)
- **Decision gate:** Does decay reduce auto-memory bloat by >50%? If not, tune or pivot.

**Phase 3: Cross-Project Overlay (4 weeks)**
- Add `.intermem/global.db` at `/root/.claude/intermem/global.db`
- Import all project-level metadata into global store
- Add semantic search via intersearch (embeddings for memory excerpts)
- MCP tool: `intermem_search(query, scope="all_projects")`
- **Decision gate:** Do agents use cross-project search >10 times/week? If not, defer.

**Phase 4: Provenance Overlay (2 weeks)**
- Add `created_by, created_at, source_tool, reviewed_by` to metadata
- Integrate with interlock for "who learned this" attribution
- MCP tool: `intermem_provenance(memory_id)` returns full lineage
- **Decision gate:** User feedback — is provenance valuable or noise?

### Rollback Strategy per Phase

- **Phase 1 rollback:** Delete `.intermem/metadata.db`, revert PreCompact hook → no metadata, validation disabled
- **Phase 2 rollback:** Disable decay rules, keep metadata for validation → no TTL enforcement
- **Phase 3 rollback:** Stop global indexing, keep project-level metadata → no cross-project search
- **Phase 4 rollback:** Stop provenance tracking, keep semantic search → no attribution

At every phase, **base stores remain untouched**, so rollback cost is minimal.

---

## Risk Mitigation Checklist

Before implementing Option 3, address these resilience concerns:

### Storage Corruption (P0)
- [ ] Automated backup of `.intermem/metadata.db` on SessionEnd hook
- [ ] Corruption detection on SessionStart (SQLite PRAGMA integrity_check)
- [ ] Recovery script: delete corrupt metadata, rebuild from base stores

### Performance Bottleneck (P1)
- [ ] Async writes for metadata overlay (PostToolUse hook writes to queue, background worker flushes)
- [ ] Latency budget: metadata writes must complete in <50ms to avoid blocking hooks
- [ ] Monitoring: track queue depth, write latency, error rate

### Embedding Drift (P2)
- [ ] Store embedding model version in metadata (`embedding_model: "openai/text-embedding-3-small"`)
- [ ] Fallback to keyword search if embedding lookup fails
- [ ] Migration script for embedding model changes (re-embed in background, dual indexing during transition)

### Blast Radius (P1)
- [ ] Graceful degradation: if `.intermem/metadata.db` is unavailable, skip overlay and serve from base stores
- [ ] Circuit breaker: if metadata lookups fail >3 times in 10 seconds, disable overlay for 60 seconds
- [ ] Monitoring: alert if metadata read latency >100ms or error rate >5%

### Multi-Agent Coordination (P2)
- [ ] Metadata writes are append-only (no conflicting updates)
- [ ] If two agents validate the same memory concurrently, last write wins (timestamps decide)
- [ ] No exclusive locks on metadata — interlock coordination only applies to base stores

---

## Questions the Document Must Answer (Blocking Issues)

Before proceeding with ANY option, the document must address:

1. **Failure Recovery (P0):** For Option 2, what happens when the canonical store corrupts? Can you rebuild from source stores? What's the MTTR?

2. **MVP Staging (P0):** For each option, what's the Phase 1 MVP that tests the riskiest assumption with the lowest rollback cost?

3. **Blast Radius (P1):** For each option, what breaks downstream when intermem is unavailable? Map the dependency graph.

4. **Validation Experiment (P1):** Before building unified retrieval, run a 1-day experiment to test whether memory fragmentation is actually the problem. Instrument existing stores, measure relevance, ask users for pain points.

5. **Embedding Strategy (P2):** If using embeddings (Options 2, 3, 4), how do you handle model versioning, provider switching, and fallback to keyword search?

---

## Conclusion: Adaptive Capacity Scorecard

| Criterion | Option 1 | Option 2 | Option 3 | Option 4 |
|-----------|----------|----------|----------|----------|
| **Antifragility** | B+ | D | A | F |
| **Graceful Degradation** | A | C | A | F |
| **Rollback Cost** | A | D | A+ | F |
| **Resource Bottleneck** | A | C | A | C |
| **Blast Radius** | A | C | A | F |
| **MVP Staging** | A | B | A+ | D |
| **Feature Completeness** | C | A | A | A |
| **Migration Risk** | A | C | A+ | F |

**Overall Grade:**
- **Option 3 (Smart Layer):** A — Best resilience, lowest risk, fully reversible
- **Option 1 (Federation):** B+ — Good resilience, limited features
- **Option 2 (Consolidation):** C — High risk, poor failure recovery
- **Option 4 (Replace All):** F — Catastrophic failure modes, massive migration risk

**Final Recommendation:**

Build **Option 3 (Smart Layer on Top)** with the 4-phase MVP sequence outlined above. Each phase tests a key assumption (validation reduces staleness, decay reduces bloat, cross-project adds value, provenance is useful) with minimal irreversible commitment.

At every decision gate, you can:
- **Advance** if the feature delivers value
- **Pivot** if the feature doesn't work but the approach is sound
- **Retreat** if the entire overlay adds more complexity than value

This is the most **antifragile** path forward because it gains from learning rather than committing to a single architecture upfront.

---

## Appendix: Lens Coverage

**Lenses Applied (from 12 hardcoded):**
1. ✅ Antifragility — Options 1/3 gain from disorder (store failures), Option 2/4 don't
2. ✅ Graceful Degradation — Blast radius analysis
3. ✅ Redundancy vs. Efficiency — Federation preserves redundancy, consolidation eliminates it
4. ⚠️ Creative Constraints — Partially applied (see Assumption Lock analysis)
5. ⚠️ First Principles — Partially applied (MVP validation experiment)
6. ✅ Assumption Locks — "Existing stores must be preserved" questioned
7. ✅ Diminishing Returns — Resource bottleneck analysis
8. ✅ Staging & Sequencing — 4-phase MVP for Option 3
9. ✅ Resource Bottleneck — Write throughput concerns for Option 2
10. ⚠️ Creative Destruction — Touched in Assumption Lock section
11. ✅ MVP Thinking — Validation experiment, smallest reversible bets
12. ✅ Phoenix Moments — Memory crisis as opportunity to rethink problem space

**Lenses NOT Applied (out of scope for this document type):**
- Feedback loops, emergence, systems dynamics (reserved for fd-systems)
- Decision quality, uncertainty quantification (reserved for fd-decisions)
- Trust, power, communication (reserved for fd-people)
- Perception, sensemaking (reserved for fd-perception)

**MCP Enhancement:**
No Interlens MCP server detected in available tools. Review used fallback lens subset (12/288 lenses hardcoded in agent prompt). Full coverage requires Interlens MCP installation.

---

**NOTE**: This review focused on adaptive capacity and resilience. For architecture correctness (API design, data modeling), defer to `fd-architecture`. For implementation quality (code structure, testing), defer to `fd-quality`. For security (memory poisoning, credential leaks), defer to `fd-safety`.
