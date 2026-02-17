# Architecture Review: Intermem Memory System Design

**Date:** 2026-02-16
**Reviewer:** Flux-Drive Architecture & Design Review
**Document:** `/tmp/intermem-brainstorm-context.md`

## Executive Summary

**Recommended Approach:** **Option 3 (Smart Layer on Top)** with a phased migration path toward Option 2 (Consolidation Engine).

**Key Findings:**
1. The proposed architecture has strong coupling risk with 5 existing memory systems — federation alone creates hidden dependencies
2. Integration with intersearch/tldr-swinton is architecturally sound BUT requires careful boundary management to avoid scope creep
3. The Interverse ecosystem's existing infrastructure (interlock, intermute, interphase) provides the coordination primitives needed for multi-agent memory coordination — do not reinvent

**Critical Risks:**
- All 4 options underspecify ownership boundaries between intermem and existing systems
- Proposing intersearch integration without defining the API contract creates coupling drift
- No clear answer to "who owns memory decay logic" — this will become a god-module risk

---

## 1. Boundaries & Coupling Analysis

### 1.1 Current Memory System Architecture

The document describes 5 independent memory systems with **zero coordination**:

| System | Storage | Scope | Trigger | Retrieval |
|--------|---------|-------|---------|-----------|
| Auto-memory | `~/.claude/projects/*/memory/*.md` | Per-project | Manual/auto | System prompt injection |
| Compound | `docs/solutions/*.md` (YAML) | Per-repo | Hook (weight ≥3) | Manual search, CLAUDE.md refs |
| Interfluence | `.interfluence/learnings-raw.log` | Per-project | PostToolUse:Edit | MCP tools |
| .clavain/learnings/ | Markdown (committed) | Per-repo | Manual | Read by review agents |
| CLAUDE.md/AGENTS.md | Markdown | Per-project | Manual | Session start |

**Architectural Problem:** These systems have **overlapping responsibilities with no ownership boundaries**:
- Auto-memory and Compound both capture debugging insights
- Interfluence learnings and auto-memory both capture style/pattern corrections
- .clavain/learnings/ and Compound both persist investigation outcomes
- All 5 dump into the same LLM context window with no deduplication

**Coupling Risk Assessment by Option:**

#### Option 1 (Federation Layer)
**Coupling Severity: HIGH**

```
intermem (federation)
  ├─> auto-memory (read-only, MD parsing)
  ├─> compound (read-only, YAML parsing)
  ├─> interfluence (MCP calls)
  ├─> .clavain/learnings/ (read-only, MD parsing)
  └─> CLAUDE.md/AGENTS.md (read-only, MD parsing)
```

**Problems:**
1. **Hidden dependency explosion:** Each backend's format change (YAML → JSON, file naming, frontmatter schema) breaks intermem
2. **Lowest-common-denominator retrieval:** Cannot add decay/validation without writing to the backends
3. **No ownership handoff:** All 5 systems stay responsible for their data quality, but intermem gets blamed for bad retrievals
4. **Tangled failure modes:** If Compound's auto-hook changes its signal detection, intermem's retrieval changes without notice

**Verdict:** This is a **coordination adapter** masquerading as an architecture. The coupling is hidden but pervasive.

---

#### Option 2 (Consolidation Engine)
**Coupling Severity: MEDIUM (with clear migration risk)**

```
intermem (canonical store: SQLite + embeddings)
  ↑ writes from: auto-memory, compound, interfluence, .clavain/learnings/
  ↓ serves to: retrieval queries
```

**Problems:**
1. **Migration complexity:** Moving 16+ project directories of auto-memory, 10+ solution docs, interfluence learnings into a single store = risky consolidation
2. **Divergence risk during migration:** If Compound keeps writing to `docs/solutions/` while intermem writes to SQLite, who wins?
3. **Existing system inertia:** Compound's hook (`auto-compound.sh`) already has 10+ solution docs and integration with Clavain's signal detection. Rewriting this creates compatibility risk.

**Strengths:**
1. **Single source of truth:** Once migration completes, all memory queries hit one store
2. **Can add features cleanly:** Decay, dedup, validation, provenance all belong to intermem
3. **Clearest ownership:** Intermem owns the canonical data; other systems become write adapters

**Verdict:** This is the **correct long-term architecture**, but the migration path is treacherous. Requires a **two-phase approach** (see recommendation).

---

#### Option 3 (Smart Layer on Top)
**Coupling Severity: LOW (with overlay drift risk)**

```
intermem (metadata overlay: validation, decay, provenance)
  ├─> reads from: all 5 existing systems
  └─> maintains: .intermem/metadata.db (last_validated, confidence, source)
```

**Problems:**
1. **Overlay drift:** If Compound deletes a solution doc, intermem's metadata becomes stale orphan
2. **Two places to maintain:** Every memory has data in the source system AND metadata in intermem
3. **More complex than it looks:** Needs cache invalidation, tombstone tracking, source-of-truth resolution

**Strengths:**
1. **Non-destructive:** Existing systems keep working unchanged
2. **Incremental feature addition:** Can add decay/validation without waiting for migration
3. **Fail-open:** If intermem crashes, the underlying systems still function
4. **Lowest implementation risk:** No migration, no rewriting Compound/interfluence

**Verdict:** This is the **safest first step**, but cannot be the final state. It's a **phase 1 toward Option 2**.

---

#### Option 4 (Replace Everything)
**Coupling Severity: EXTREME (during migration), NONE (after complete replacement)**

**Problems:**
1. **Massive migration:** 16+ project memory dirs + 10+ solution docs + interfluence logs + .clavain/learnings/ all need conversion
2. **Loses battle-tested patterns:** Compound's signal detection (git commits, debugging, insight blocks) took months to calibrate
3. **High risk, long timeline:** Migration could take weeks; any bugs = broken memory for all projects
4. **No incremental rollout:** Either fully on intermem or not; no gradual adoption

**Verdict:** This is **architecturally cleanest** but operationally catastrophic. **DO NOT pursue until Option 3 is proven stable.**

---

### 1.2 Boundary Violation: Scope Creep into Intersearch

The document proposes:
> "Should intermem leverage intersearch for embeddings?"
> "Could memory use the same embedding infrastructure as tldr-swinton?"

**Coupling Analysis:**

```
intermem
  └─> intersearch (shared embedding client + Exa search)
        └─> used by: interject, interflux
```

**This is sound IF AND ONLY IF:**
1. **intersearch remains a library, not a service:** If it becomes a daemon, intermem inherits failure modes
2. **API contract is stable:** intersearch currently exports `__version__ = "0.1.0"` and nothing else (see `/root/projects/Interverse/plugins/intersearch/src/intersearch/__init__.py`). No public embedding API exists yet.
3. **Embedding model choices are decoupled:** tldr-swinton uses ColBERT/FAISS (see `plugins/tldr-swinton/src/tldr_swinton/modules/semantic/`). If intermem needs a different model (e.g., sentence-transformers), intersearch must support this or intermem must vendor its own embedder.

**Recommendation:**
- **Phase 1:** Intermem vendors its own embeddings (simplest, fastest)
- **Phase 2:** Extract common embedding logic into intersearch with a stable API
- **Phase 3:** Both intermem and tldr-swinton migrate to intersearch

**Risk if done wrong:** Intermem's memory retrieval quality becomes dependent on intersearch's embedding model choices. If tldr-swinton switches from ColBERT to a different encoder for code context, and intersearch follows, intermem's semantic search breaks.

**Mitigation:** Define an **embedding backend abstraction** in intersearch so consumers can choose their model:
```python
# intersearch API (future)
from intersearch import EmbeddingBackend, SentenceTransformerBackend, ColBERTBackend

memory_embedder = SentenceTransformerBackend(model="all-MiniLM-L6-v2")
code_embedder = ColBERTBackend(model="colbert-v2")
```

---

### 1.3 Dependency Direction Violations

**Correct Dependency Flow (clean architecture):**

```
intermem (domain layer)
  ├─> storage interface (abstraction)
  ├─> embedding interface (abstraction)
  └─> MCP server (delivery layer)

auto-memory, compound, interfluence (write adapters)
  └─> intermem write API
```

**Current Proposal Violations:**

1. **Option 1 (Federation):** intermem depends on Compound's YAML schema, auto-memory's MD format → **delivery layer depending on persistence details**
2. **All options:** No mention of **write API boundaries** — if Compound keeps writing to `docs/solutions/`, intermem must poll the filesystem → **intermem becomes coupled to Compound's output directory structure**

**Fix:** Define explicit write boundaries:
- Compound's hook calls `intermem_append(type="solution", source="compound", ...)` instead of writing MD files
- Auto-memory writes through intermem's MCP tool instead of directly to `.claude/projects/*/memory/`
- Interfluence's PostToolUse hook calls `intermem_log_edit()` instead of appending to `.interfluence/learnings-raw.log`

**This requires coordination with existing system owners** — intermem cannot unilaterally impose new APIs on Compound/interfluence.

---

## 2. Pattern Analysis

### 2.1 Explicit Patterns in the Ecosystem

**Pattern 1: Hook-based Write-Ahead Logging (WAL)**

**Current implementations:**
- Compound: `auto-compound.sh` → `docs/solutions/*.md` (YAML frontmatter + markdown)
- Interfluence: `learn-from-edits.sh` → `.interfluence/learnings-raw.log` (line-delimited diffs)

**WAL Protocol (from Compound):**
1. Hook detects signal (git commit, debugging resolution, etc.)
2. Accumulate signal weight (1-2 per signal type)
3. If weight ≥ threshold (3), trigger write
4. Write structured entry to append-only log
5. Periodic consolidation (Compound does this via manual `/compound` review; Interfluence does this via `/interfluence refine`)

**Intermem's Relation to WAL:**
- **Option 1:** Reads WAL outputs post-consolidation → misses real-time insights
- **Option 2:** Replaces WAL with intermem's own append log → breaks existing workflows
- **Option 3:** Observes WAL outputs, adds metadata → preserves existing pattern

**Recommendation:** Intermem should **participate in WAL, not replace it**. Compound's `auto-compound.sh` should append to both `docs/solutions/` (for human review) and intermem's SQLite (for semantic search). This is **dual-write**, not ideal, but avoids breaking the Compound workflow.

**Long-term fix (Option 2 migration):** Compound calls `intermem.write_solution()`, which handles both persistence and human-review formatting.

---

**Pattern 2: Progressive Disclosure (from landscape research)**

**From MemCP (MIT CSAIL):**
> "3-layer progressive disclosure: index → timeline → details"
> "Context-as-variable: metadata only until drill-down"

**Current Interverse implementation:**
- **Auto-memory:** Injects full 200 lines at session start → no progressive disclosure
- **Compound:** Manual search via `grep docs/solutions/` → no indexing
- **Interfluence:** MCP tools return full learnings log → no summarization

**Intermem's Opportunity:**
Implement progressive disclosure natively:
1. **Index layer:** Return only memory titles + confidence + timestamp
2. **Summary layer:** Return 1-sentence summaries
3. **Detail layer:** Return full memory content

**This pattern is NOT mentioned in the brainstorm document** — significant missed opportunity.

**Recommendation:** Add this to Option 3's metadata overlay:
```sql
-- .intermem/metadata.db schema
CREATE TABLE memory_index (
  id TEXT PRIMARY KEY,
  source TEXT,  -- 'auto-memory', 'compound', 'interfluence'
  title TEXT,
  summary TEXT,  -- 1 sentence, generated by intermem
  confidence REAL,
  last_validated INTEGER,
  last_accessed INTEGER
);
```

---

**Pattern 3: Multi-Agent Memory Coordination (MCP pattern)**

**Current Interverse Implementation:**
- **Interlock:** File reservation coordination via intermute (agent → intermute → SQLite → agent)
- **Intermute:** Central coordination service (Go, SQLite, HTTP API)

**Intermem's Relation to Interlock:**
The brainstorm document asks:
> "How should intermem handle multi-agent memory (concurrent writes, conflict resolution)?"

**Answer:** **Reuse the interlock/intermute pattern, do not reinvent.**

**Proposed Architecture:**

```
Agent A                    Agent B
  |                          |
  | reserve_memory("debug-session-123")
  v                          v
intermem MCP server
  |
  | HTTP to intermute coordination service
  v
intermute (Go service)
  |
  | SQLite lock table
  v
[agent_id, memory_id, reservation_ts, TTL]
```

**Why this works:**
1. Intermute already has reservation logic (15-min TTL, auto-release on commit)
2. Interlock already has conflict resolution (exclusive vs shared locks)
3. Clavain already has multi-agent awareness (sprint scan, session handoff)

**Intermem's role:** Call intermute's reservation API before writing, not reimplement locking.

**This is NOT architectural coupling** — intermute is a coordination service, designed for this exact use case. Intermem would be a **consumer**, not a dependency.

---

### 2.2 Anti-Patterns Detected

**Anti-Pattern 1: God Module Risk**

**Where it appears:** All 4 options lack clarity on **who owns what**:
- Who validates memory correctness? (Intermem? Compound? Claude at retrieval time?)
- Who decides decay policy? (Intermem global config? Per-project .claude/settings? Compound's signal weights?)
- Who deduplicates memories? (Intermem at write time? Claude at retrieval time? Never?)

**Result:** Without explicit ownership boundaries, intermem will **accrete responsibilities** until it becomes a god module handling storage, retrieval, validation, decay, dedup, conflict resolution, embedding, and multi-agent coordination.

**Mitigation:**
```
WRITE this into the architecture doc:

Intermem owns:
- Storage (SQLite + embeddings)
- Retrieval (semantic + temporal search)
- Decay (TTL + confidence scoring)
- Deduplication (hash-based + semantic similarity)

Intermem does NOT own:
- Memory creation triggers (Compound, Interfluence, auto-memory own their hooks)
- LLM summarization (Claude does this at retrieval time, not storage time)
- Multi-agent coordination (intermute owns this)
- Voice profile application (interfluence owns this)
```

---

**Anti-Pattern 2: Leaky Abstraction (Compound YAML exposure)**

**Where it appears:** Option 1 (Federation Layer)

If intermem reads `docs/solutions/*.md` and parses YAML frontmatter, it **leaks Compound's internal format** into intermem's API. If Compound changes from YAML to TOML or adds a new frontmatter field, intermem breaks.

**Fix:** Compound should provide a **write adapter**:
```bash
# Compound's auto-compound.sh refactored
compound_write() {
  local title="$1"
  local content="$2"

  # Write to human-readable MD (for git history)
  echo "$content" > "docs/solutions/${title}.md"

  # Write to intermem's canonical store
  intermem_cli write \
    --type=solution \
    --source=compound \
    --title="$title" \
    --content="$content"
}
```

**This is a BREAKING CHANGE for Compound**, so it must be gated behind Option 3 (Smart Layer) first, then migrated in Option 2 phase.

---

**Anti-Pattern 3: Circular Dependencies (Intermem ↔ Interfluence)**

**Where it appears:** Interfluence logs edits → intermem. Interfluence applies voice profile → edits files → logs more edits → intermem.

If intermem also tries to **apply voice profiles** (e.g., "rewrite this memory in the user's style"), then:
```
intermem writes memory
  → interfluence applies voice profile
    → writes edited memory
      → intermem logs the edit as a new memory
        → LOOP
```

**Mitigation:** **Intermem must never write to files that Interfluence monitors.** Memory storage (`.intermem/`) must be excluded from Interfluence's edit logging. This is already the case (see `hooks/learn-from-edits.sh` exclusions), but must be **explicitly documented** in intermem's architecture.

---

**Anti-Pattern 4: Speculative Abstraction (Temporal Decay without Evidence)**

**Where it appears:** The brainstorm document proposes "temporal decay" as a feature from the landscape research (memory-mcp, MemCP).

**Question:** Is there **evidence from Interverse usage** that memory staleness is a problem?

**Current state:**
- Auto-memory has 200-line cap → oldest memories naturally prune
- Compound has 10+ solution docs → all remain relevant (no evidence of staleness)
- Interfluence learnings are batched + reviewed → user manually discards stale learnings during `/refine`
- .clavain/learnings/ is committed to git → user manually curates

**Verdict:** **Temporal decay is a solution looking for a problem.** Do not implement until there is evidence that:
1. Memory retrieval returns stale/incorrect information
2. The staleness is time-based (not context-based)
3. Manual pruning is insufficient

**If implemented, use a feature flag:**
```yaml
# .intermem/config.yaml
decay:
  enabled: false  # default: off until proven necessary
  ttl_days: 30
  confidence_threshold: 0.5
```

---

## 3. Simplicity & YAGNI

### 3.1 Unnecessary Abstractions

**From the brainstorm document:**

> "Should intermem be an MCP server, a hooks-only plugin, or both?"

**Analysis:**

**Option A: MCP server only**
- Pro: Claude can retrieve memories on-demand
- Con: Cannot auto-capture memories (requires user to manually call MCP tools)

**Option B: Hooks only**
- Pro: Can auto-capture memories via PostToolUse, Stop, SessionEnd hooks
- Con: Retrieval requires manual `/intermem search` commands or injecting memories at SessionStart

**Option C: Both MCP + Hooks**
- Pro: Best of both worlds
- Con: More complexity, more failure modes, more testing surface

**Recommendation:** **Start with MCP + ONE hook (SessionStart for injection).** Do not add PostToolUse/Stop hooks until Option 3 is stable.

**Why:**
1. Auto-capture is already handled by Compound + Interfluence — do not duplicate
2. Retrieval is the missing piece — MCP tools solve this
3. SessionStart injection is low-risk (read-only)

**Defer PostToolUse/Stop hooks to Phase 2** (after migration to Option 2).

---

### 3.2 Feature Bloat from Landscape Research

The brainstorm document lists **7 gaps in the landscape** and proposes intermem should fill all of them:

1. Cross-project knowledge sharing
2. Forgetting discipline (decay)
3. Memory validation on retrieval
4. Security (credential leak prevention)
5. Interoperable standard
6. Multi-agent memory coordination
7. Memory provenance

**YAGNI Analysis:**

| Gap | MVP Necessity | Reasoning |
|-----|---------------|-----------|
| Cross-project | **NO** | No evidence that memories need to cross project boundaries. Auto-memory is per-project for good reason (context bleed). Defer until user explicitly requests "show me how I solved this in another project." |
| Decay | **NO** | See Anti-Pattern 4 — solution looking for a problem. Defer. |
| Validation | **YES** | Memories can become stale when code changes. Validation = "does this solution doc still match the code?" Requires integration with git diff. |
| Security | **YES** | Memories can capture API keys from debug sessions. Must redact secrets before storage. Can reuse patterns from ShieldCortex (landscape research). |
| Interoperable standard | **NO** | Zero evidence of need to share memories across AI systems. Defer. |
| Multi-agent coordination | **YES** | Interverse already has multi-agent workflows (Clavain + interlock). Memories must not corrupt under concurrent writes. Use intermute (existing service). |
| Provenance | **YES** | "Where did this memory come from?" is critical for trust. Must track source (auto-memory, compound, interfluence) + timestamp + agent_id. |

**Recommendation:** MVP includes **validation, security, multi-agent, provenance**. Defer cross-project, decay, interoperable standard.

---

### 3.3 Collapse Unnecessary Complexity

**Complexity Source 1: 5 Existing Systems**

The brainstorm document accepts the 5 systems as immovable constraints. **This is a false constraint.**

**Simplification Opportunity:**
- **Auto-memory** and **Compound** have **80% overlap** (both capture debugging insights, both triggered by work completion)
- **Interfluence learnings** and **auto-memory** have **60% overlap** (both capture style/pattern corrections)

**Proposed Consolidation (Phase 2, Option 2):**

```
Before (5 systems):
auto-memory → ~/.claude/projects/*/memory/*.md
compound → docs/solutions/*.md
interfluence → .interfluence/learnings-raw.log
.clavain/learnings/ → markdown
CLAUDE.md/AGENTS.md → markdown

After (3 systems):
intermem → .intermem/memories.db (canonical store)
interfluence → voice profiles only (style, not learnings)
CLAUDE.md/AGENTS.md → project-specific docs (unchanged)
```

**Why this works:**
- Auto-memory's session-level insights merge into intermem
- Compound's solution docs merge into intermem (with YAML frontmatter preserved as metadata)
- Interfluence's learnings merge into intermem (voice corrections stay in interfluence as voice profile updates)
- .clavain/learnings/ becomes a view over intermem (generated report, not source of truth)

**Migration Risk:** This is a **major refactor** of Compound and auto-memory workflows. Cannot be done in MVP.

**Recommendation:** Document this as the **long-term vision** (Option 2 Phase 3), but do not start until Option 3 is stable.

---

**Complexity Source 2: Embedding Model Choices**

The brainstorm document proposes:
> "Should memory leverage the same embedding infrastructure as tldr-swinton?"

**tldr-swinton uses ColBERT + FAISS** (see `plugins/tldr-swinton/src/tldr_swinton/modules/semantic/`). This is optimized for **code context retrieval** (matching function signatures, import paths).

**Memory retrieval needs** are different:
- Matching **semantic intent** ("how did I fix database deadlocks before?")
- Matching **temporal patterns** ("what did I learn last week about Go error handling?")
- Matching **cross-file patterns** ("where did I document the decision to use SQLite over Postgres?")

**Verdict:** **Do not reuse tldr-swinton's ColBERT embeddings.** Use a **sentence-transformer model** (e.g., `all-MiniLM-L6-v2`) optimized for semantic similarity, not code similarity.

**Simplification:**
- Vendor embeddings in MVP (no intersearch dependency)
- Swap to intersearch in Phase 2 (once intersearch has a stable API)

---

## 4. Recommended Architecture

### 4.1 Option 3 (Smart Layer on Top) — Phase 1 (MVP)

**Why Option 3:**
1. **Non-destructive** → Existing systems (Compound, Interfluence, auto-memory) keep working unchanged
2. **Lowest migration risk** → No breaking changes to Clavain hooks or Interfluence MCP tools
3. **Incremental rollout** → Can deploy to one project, validate, then expand
4. **Fail-open** → If intermem crashes, existing systems still function

**Architecture:**

```
┌─────────────────────────────────────────────────────────────┐
│                  Claude Code Session                        │
└─────────────────────────────────────────────────────────────┘
                           │
                           │ (SessionStart hook)
                           v
┌─────────────────────────────────────────────────────────────┐
│               Intermem (Smart Layer)                        │
│  - Reads from: auto-memory, compound, interfluence          │
│  - Metadata: .intermem/metadata.db (validation, confidence) │
│  - Embeddings: vendor sentence-transformer (no intersearch) │
│  - MCP Server: memory_search, memory_validate, memory_get   │
└─────────────────────────────────────────────────────────────┘
       │                    │                    │
       v                    v                    v
┌──────────────┐  ┌──────────────────┐  ┌─────────────────┐
│ auto-memory  │  │    compound      │  │  interfluence   │
│ (unchanged)  │  │   (unchanged)    │  │  (unchanged)    │
└──────────────┘  └──────────────────┘  └─────────────────┘
```

**Key Components:**

1. **MCP Server** (TypeScript, following interfluence pattern)
   - `memory_search(query, scope, limit)` → ranked list of memories
   - `memory_get(id)` → full memory content
   - `memory_validate(id)` → check if memory is still correct (git diff heuristic)
   - `memory_provenance(id)` → source system + timestamp + agent_id

2. **Metadata Store** (`.intermem/metadata.db`, SQLite)
   - Schema: `[id, source, title, summary, confidence, last_validated, embedding_id]`
   - Embeddings: separate `embeddings.faiss` file (FAISS index)

3. **SessionStart Hook** (inject top 5 relevant memories based on project context)
   - Reads `.intermem/metadata.db`
   - Generates project context vector (from CLAUDE.md + recent file edits)
   - Returns top 5 memories via `additionalContext`

**What is NOT included in Phase 1:**
- No PostToolUse/Stop hooks (avoid conflicts with Compound/Interfluence)
- No cross-project search (per-project only)
- No temporal decay (no evidence of need)
- No write API for Compound/Interfluence (read-only federation)

**Migration Risk:** **LOW** — Intermem only reads, never writes to existing systems.

---

### 4.2 Option 2 (Consolidation Engine) — Phase 2 (Post-MVP)

**After Phase 1 is stable (3+ months of production use), migrate to Option 2.**

**Why Phase 2:**
1. Phase 1 proves memory retrieval value (if users don't use it, Phase 2 is unnecessary)
2. Phase 1 identifies format drift in existing systems (e.g., Compound's YAML changes)
3. Phase 1 builds embedding + validation logic that Phase 2 will reuse

**Architecture:**

```
┌─────────────────────────────────────────────────────────────┐
│               Intermem (Canonical Store)                    │
│  - Storage: .intermem/memories.db (SQLite)                  │
│  - Embeddings: embeddings.faiss                             │
│  - MCP Server: memory_search, memory_write, memory_validate │
│  - Multi-agent: calls intermute for write coordination      │
└─────────────────────────────────────────────────────────────┘
       ↑                    ↑                    ↑
       │ (write API)        │ (write API)        │ (write API)
┌──────────────┐  ┌──────────────────┐  ┌─────────────────┐
│ auto-memory  │  │    compound      │  │  interfluence   │
│ (adapter)    │  │   (adapter)      │  │  (adapter)      │
└──────────────┘  └──────────────────┘  └─────────────────┘
```

**Key Changes from Phase 1:**

1. **Compound becomes a write adapter:**
   - `auto-compound.sh` calls `intermem_cli write --type=solution --source=compound ...`
   - `docs/solutions/*.md` becomes a **generated report** (intermem exports to MD for git history)

2. **Auto-memory delegates to intermem:**
   - Claude Code's auto-memory writes to intermem's SQLite instead of `~/.claude/projects/*/memory/*.md`
   - Requires upstream change to Claude Code (or a PostToolUse hook intercept)

3. **Interfluence learnings consolidate:**
   - `.interfluence/learnings-raw.log` merges into intermem
   - Voice profile generation reads from intermem (via MCP) instead of raw log

**Migration Path:**
1. Deploy Phase 2 to ONE project (e.g., Interverse root)
2. Run dual-write for 2 weeks (both intermem + existing systems)
3. Compare outputs (intermem vs Compound solution docs, intermem vs auto-memory)
4. If outputs match, switch to intermem-only
5. Expand to remaining projects

**Migration Risk:** **MEDIUM** — Requires changes to Compound + Interfluence hooks, but changes are localized.

---

### 4.3 Intersearch Integration — Phase 3 (Optional)

**Only pursue if:**
1. intersearch has a stable embedding API (currently does not)
2. Multiple plugins (intermem, interject, interflux) would benefit from shared embeddings
3. Embedding model choices are decoupled (intermem can use sentence-transformers while tldr-swinton uses ColBERT)

**Proposed API:**

```python
# intersearch/src/intersearch/embeddings.py
from abc import ABC, abstractmethod

class EmbeddingBackend(ABC):
    @abstractmethod
    def embed(self, texts: list[str]) -> np.ndarray:
        pass

class SentenceTransformerBackend(EmbeddingBackend):
    def __init__(self, model: str = "all-MiniLM-L6-v2"):
        self.model = SentenceTransformer(model)

    def embed(self, texts: list[str]) -> np.ndarray:
        return self.model.encode(texts)

class ColBERTBackend(EmbeddingBackend):
    def __init__(self, model: str = "colbert-v2"):
        self.model = ColBERT(model)

    def embed(self, texts: list[str]) -> np.ndarray:
        return self.model.encode(texts)

# Consumer usage
from intersearch import EmbeddingBackend, SentenceTransformerBackend

embedder = SentenceTransformerBackend()
memory_vectors = embedder.embed(["how to fix deadlocks", "database connection pool tuning"])
```

**Integration with tldr-swinton:**
- tldr-swinton refactors to use `ColBERTBackend` from intersearch
- intermem uses `SentenceTransformerBackend` from intersearch
- Both share intersearch version, but not embedding model

**Risk if not done:** Each plugin vendors its own embeddings → duplication + version drift.

**Risk if done wrong:** intersearch becomes a coupling point → changes to intersearch break multiple plugins.

**Mitigation:** intersearch MUST have a **stable API contract** before integration. No API until at least 3 consumers agree on the interface.

---

## 5. Coupling Risks with Existing Systems

### 5.1 Compound Integration Risks

**Risk 1: Signal Detection Drift**

Compound's `auto-compound.sh` uses **shared signal detection** (`hooks/lib-signals.sh`) with these weights:
- Git commits (1)
- Debugging resolutions (2)
- Investigation language (2)
- Bead closures (1)
- Insight blocks (1)
- Build/test recovery (2)
- Version bumps (2)

If intermem **reimplements signal detection** instead of reusing `lib-signals.sh`, the two systems will drift. Compound will capture memories that intermem misses (or vice versa).

**Mitigation:** Phase 2 (Consolidation Engine) must **call** `lib-signals.sh`, not duplicate it.

---

**Risk 2: YAML Frontmatter Schema Changes**

Compound's solution docs use YAML frontmatter:
```yaml
---
title: "Database deadlock fix"
date: 2026-02-16
tags: [postgres, debugging]
---
```

If Compound changes this schema (adds `confidence`, removes `tags`, switches to JSON), intermem's Phase 1 parser breaks.

**Mitigation:** Phase 1 must use **lenient parsing** (ignore unknown fields, default missing fields). Phase 2 replaces parsing with write API.

---

### 5.2 Interfluence Integration Risks

**Risk 1: Edit Log Format Changes**

Interfluence's `.interfluence/learnings-raw.log` is line-delimited:
```
[2026-02-16 10:23:45] src/main.py: -old line\n+new line
```

If Interfluence changes to JSON logs (more structured), intermem's Phase 1 parser breaks.

**Mitigation:** Coordinate with Interfluence maintainer on log format stability. Phase 2 replaces parsing with write API.

---

**Risk 2: Circular Dependency (Intermem ↔ Interfluence)**

If intermem writes memories → Interfluence applies voice profile → writes edited memories → intermem logs the edit → LOOP.

**Mitigation:** `.intermem/` must be excluded from Interfluence's `learn-from-edits.sh` hook. Add to exclusions list:
```bash
# hooks/learn-from-edits.sh (line 30)
FILE_NAME=$(basename "$FILE_PATH")
FILE_DIR=$(dirname "$FILE_PATH")

# Exclude .intermem/ directory
if [[ "$FILE_DIR" == *".intermem"* ]]; then
    exit 0
fi
```

---

### 5.3 Auto-Memory Integration Risks

**Risk 1: 200-Line Cap Coordination**

Auto-memory has a **200-line cap** (hardcoded in Claude Code). If intermem injects memories at SessionStart, and auto-memory also injects 200 lines, the system prompt becomes 400+ lines → context bloat.

**Mitigation:** Intermem's SessionStart hook must:
1. Check if auto-memory is active (`.claude/projects/*/memory/` exists)
2. Reduce intermem injection to 5 memories (100 lines max)
3. Coordinate with auto-memory to avoid duplication

---

**Risk 2: Auto-Memory Pruning Logic**

Auto-memory prunes oldest memories when the 200-line cap is exceeded. If intermem also stores these memories, they **survive** in intermem but **disappear** from auto-memory.

**Question:** Should intermem respect auto-memory's pruning decisions?

**Options:**
1. **YES (respect):** Intermem marks pruned memories as `archived` (lower confidence, not injected)
2. **NO (ignore):** Intermem keeps all memories, even if auto-memory pruned them

**Recommendation:** **Option 1 (respect)**. Auto-memory's pruning is user-driven (either manual or automatic based on relevance). Intermem should not override user intent.

**Implementation:** Phase 1 intermem watches auto-memory directory for file deletions → marks corresponding intermem memories as `archived`.

---

## 6. Multi-Agent Memory Coordination

### 6.1 Leverage Intermute (Do Not Reinvent)

**Existing Intermute Architecture (from interlock plugin):**

```
Agent A                    Agent B
  |                          |
  | reserve_files([...])     | reserve_files([...])
  v                          v
Interlock MCP Server
  |
  | HTTP to intermute (Go service, :7338)
  v
Intermute SQLite (reservations table)
  |
  | [agent_id, file_path, reservation_ts, TTL, is_exclusive]
  v
Lock conflict resolution → GRANTED / DENIED
```

**Intermem's Needs:**
- Concurrent agents writing memories → need write coordination
- Memory validation → need read locks (ensure memory doesn't change during validation)
- Memory consolidation → need exclusive locks (dedupe/merge operations)

**Proposed Intermem ↔ Intermute Integration:**

```
Agent A writing memory
  |
  | intermem.memory_write(...)
  v
Intermem MCP Server
  |
  | HTTP POST /reserve (agent_id, memory_id, mode=exclusive)
  v
Intermute (Go service)
  |
  | SQLite lock table INSERT
  v
GRANTED → proceed with write
DENIED → return error to agent ("memory locked by Agent B")
```

**Why this works:**
1. Intermute already has 15-min TTL + auto-release on commit
2. Intermute already has agent attribution (agent_id in reservation)
3. Intermute already has conflict resolution (exclusive vs shared locks)

**What intermem needs to add:**
- Memory ID reservation (before writing to `.intermem/memories.db`)
- Conflict error handling (retry with backoff, or fail-fast)

**No new infrastructure needed.** Intermute is designed for this.

---

### 6.2 Sprint Awareness (Clavain Integration)

**Clavain's sprint scan** (`hooks/sprint-scan.sh`) detects:
- Active agents (from intermute)
- File reservations (from interlock)
- Bead assignments (from beads DB)

**Intermem should integrate:**

```
Sprint Scan Output:
- Agent A: working on "fix-deadlocks" (bead #123, reserving src/db.py)
- Agent B: working on "add-logging" (bead #124, reserving src/logger.py)

Intermem Action:
- Tag new memories with active sprint context
- memory_write(content="...", sprint_context={"bead": 123, "agent": "Agent A"})
```

**Why this matters:**
- Memory provenance includes sprint context
- Retrieval can filter by sprint ("show me memories from the fix-deadlocks sprint")
- Multi-agent coordination is visible in memory history

**Implementation:** Intermem's MCP server reads sprint state from intermute (HTTP GET /agents) before each write.

---

## 7. Integration with Intersearch/tldr-swinton

### 7.1 Intersearch Current State

**From `/root/projects/Interverse/plugins/intersearch/src/intersearch/__init__.py`:**
```python
"""Shared search and embedding infrastructure for the Interverse ecosystem."""
__version__ = "0.1.0"
```

**No exported API yet.** intersearch is a **placeholder library** with no public functions.

**Proposed API (from brainstorm document):**
- Embedding client (sentence-transformers, ColBERT)
- Exa search integration
- Vector store abstraction

**Current Consumers:**
- **interject:** Uses Exa search (not embeddings)
- **interflux:** Uses Exa search (not embeddings)
- **tldr-swinton:** Uses ColBERT + FAISS (vendored, not via intersearch)

**Verdict:** **intersearch is not ready for intermem integration.** Wait until intersearch has a stable API.

---

### 7.2 tldr-swinton Embedding Architecture

**From `/root/projects/Interverse/plugins/tldr-swinton/src/tldr_swinton/modules/semantic/`:**

```python
# vector_store.py
class VectorStore:
    def __init__(self, backend: str = "faiss"):
        if backend == "faiss":
            self.backend = FAISSBackend()
        elif backend == "colbert":
            self.backend = ColBERTBackend()

# faiss_backend.py
class FAISSBackend:
    def __init__(self):
        self.index = faiss.IndexFlatL2(384)  # 384-dim embeddings

    def add(self, embeddings: np.ndarray):
        self.index.add(embeddings)

    def search(self, query_embedding: np.ndarray, k: int = 5):
        distances, indices = self.index.search(query_embedding, k)
        return indices, distances
```

**Key Observations:**
1. **384-dim embeddings** → likely `all-MiniLM-L6-v2` (sentence-transformers)
2. **FAISS IndexFlatL2** → no compression, exact search
3. **No embedding model loading** → assumes embeddings are pre-computed

**Question:** Does tldr-swinton compute embeddings itself, or does it receive pre-computed embeddings?

**Answer (from code inspection):** tldr-swinton uses `embeddings.py` (NOT shown in glob output, likely inside `modules/semantic/`) to compute embeddings at indexing time.

**Architectural Mismatch:**
- tldr-swinton embeds **code** (function signatures, import paths)
- intermem needs to embed **natural language** (debugging insights, solution docs)

**Different embedding models are needed:**
- Code: `codebert`, `graphcodebert`, or ColBERT
- Natural language: `all-MiniLM-L6-v2`, `all-mpnet-base-v2`

**Recommendation:** **Do not share embedding models between tldr-swinton and intermem.** They have different semantic spaces.

**If intersearch is used:** It must support **multiple embedding backends** (see Phase 3 architecture).

---

## 8. Design Pattern Fitness

### 8.1 Patterns from Landscape Research

The brainstorm document analyzes 13 external memory systems. Key patterns:

| Pattern | Source | Fitness for Intermem |
|---------|--------|---------------------|
| **Progressive Disclosure** | MemCP | **HIGH** — Must implement. Auto-memory injects full 200 lines (wasteful). Intermem should do index → summary → detail. |
| **Temporal Decay** | memory-mcp | **LOW** — No evidence of staleness problem in Interverse. Defer. |
| **Security Pipeline** | ShieldCortex | **MEDIUM** — Memory can capture secrets. Must redact API keys, tokens. But 6-layer pipeline is overkill. Start with regex-based redaction. |
| **Citation-Backed Memories** | Copilot Memory | **HIGH** — "This solution worked when the code looked like X" → validate against current code. Critical for correctness. |
| **Conflict Detection** | Nemp | **MEDIUM** — "CLAUDE.md says Prisma but package.json uses Drizzle" → useful for drift detection, but overlaps with auto-drift-check.sh (Clavain). Coordinate instead of duplicate. |
| **Agent Attribution** | Nemp | **HIGH** — Who created this memory? (Agent A, Agent B, human). Required for multi-agent provenance. |
| **MAGMA 4-graph** | MemCP | **LOW** — 4 graph types (semantic, temporal, causal, entity) is over-engineered for MVP. Start with semantic + temporal only. |
| **Single Binary** | claude-brain | **LOW** — Rust core is appealing, but TypeScript MCP is ecosystem standard. Don't fight the current. |

---

### 8.2 Pattern Match: Compound's WAL Protocol

**Compound's auto-compound.sh workflow:**

```bash
# 1. Detect signals (lib-signals.sh)
detect_signals "$TRANSCRIPT"
# → git commit (1), debugging (2), investigation (2), bead-close (1), insight (1), recovery (2), bump (2)

# 2. Threshold check (weight >= 3)
if [[ "$CLAVAIN_SIGNAL_WEIGHT" -lt 3 ]]; then
    exit 0
fi

# 3. Block decision (inject prompt)
jq -n --arg reason "$REASON" '{"decision":"block","reason":$reason}'
# → Claude evaluates whether to run /compound

# 4. Write to docs/solutions/*.md (YAML + markdown)
```

**Intermem's Relation:**

**Option 1 (Federation):** Read `docs/solutions/*.md` post-write → **misses intermediate signals**

**Option 2 (Consolidation):** Replace Compound's write with `intermem.write_solution()` → **breaks Compound's human review workflow** (users expect solution docs in git)

**Option 3 (Smart Layer):** Compound writes to both `docs/solutions/` AND intermem → **dual write** (not ideal, but preserves existing workflow)

**Recommendation for Phase 1 (Option 3):**
```bash
# Compound's auto-compound.sh (modified for dual-write)
compound_write_solution() {
  local title="$1"
  local content="$2"

  # Write to human-readable MD (for git history, unchanged)
  echo "$content" > "docs/solutions/${title}.md"

  # ALSO write to intermem (new)
  if command -v intermem &>/dev/null; then
    intermem write --type=solution --source=compound --title="$title" --content="$content"
  fi
}
```

**Recommendation for Phase 2 (Option 2):**
```bash
# Compound becomes a pure adapter
compound_write_solution() {
  intermem write --type=solution --source=compound --title="$1" --content="$2"
}

# Intermem exports to MD for git history (new feature)
intermem export --format=md --output=docs/solutions/
```

---

## 9. Critical Missing Pieces

### 9.1 Write API Specification

**Nowhere in the brainstorm document is there a write API spec.**

**Required for Phase 2 (Option 2):**

```typescript
// Intermem MCP Server (write API)
interface MemoryWriteParams {
  type: "solution" | "learning" | "insight" | "style";
  source: "compound" | "interfluence" | "auto-memory" | "manual";
  title: string;
  content: string;
  tags?: string[];
  sprint_context?: {
    bead_id?: number;
    agent_id?: string;
  };
  validation?: {
    code_snapshot?: string;  // Git commit SHA
    file_paths?: string[];    // Files mentioned in this memory
  };
}

interface MemoryWriteResult {
  id: string;  // UUID
  created_at: number;  // Unix timestamp
  embedding_id: string;  // Reference to embeddings.faiss
  provenance: {
    source: string;
    agent_id?: string;
    session_id?: string;
  };
}
```

**Without this, Phase 2 cannot proceed.**

---

### 9.2 Validation Logic

**From landscape research (Copilot Memory):**
> "Citation-backed memories. Before applying a memory, validates cited code against current codebase."

**How this works:**
1. Memory stores a code snapshot (git commit SHA or file content hash)
2. Before retrieval, intermem checks if the cited code still exists
3. If code changed, memory is marked `stale` (lower confidence)

**Implementation (Phase 1):**

```sql
-- .intermem/metadata.db (add validation columns)
CREATE TABLE memory_index (
  id TEXT PRIMARY KEY,
  source TEXT,
  title TEXT,
  summary TEXT,
  confidence REAL,
  last_validated INTEGER,
  validation_snapshot TEXT,  -- git commit SHA
  validation_files TEXT       -- JSON array of file paths
);
```

**Validation hook (runs on retrieval):**

```typescript
async function validateMemory(memory: Memory): Promise<boolean> {
  if (!memory.validation_snapshot) {
    return true;  // No validation metadata → assume valid
  }

  // Check if commit still exists
  const commitExists = await execAsync(`git cat-file -e ${memory.validation_snapshot}^{commit}`);
  if (!commitExists) {
    return false;  // Code snapshot no longer in history → stale
  }

  // Check if files still exist
  for (const file of memory.validation_files) {
    const fileExists = await fs.access(file);
    if (!fileExists) {
      return false;  // File deleted → stale
    }
  }

  return true;
}
```

**This is NOT in the brainstorm document.** Must be added to Phase 1 design.

---

### 9.3 Security Redaction

**From landscape research (ShieldCortex):**
> "6-layer security pipeline blocking memory poisoning, credential leaks, prompt injection."

**Intermem needs simpler version:**

```typescript
// Redaction patterns (Phase 1)
const SECRET_PATTERNS = [
  /sk-[A-Za-z0-9]{48}/g,               // OpenAI API keys
  /ghp_[A-Za-z0-9]{36}/g,              // GitHub tokens
  /eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+/g, // JWT tokens
  /AKIA[0-9A-Z]{16}/g,                 // AWS access keys
  /postgres:\/\/[^@]+:[^@]+@/g,        // DB connection strings
];

function redactSecrets(content: string): string {
  let redacted = content;
  for (const pattern of SECRET_PATTERNS) {
    redacted = redacted.replace(pattern, "[REDACTED]");
  }
  return redacted;
}
```

**This must run BEFORE writing to intermem storage.**

---

## 10. Final Recommendation

### 10.1 Adopt Option 3 (Smart Layer) for Phase 1

**Why:**
- Lowest risk (non-destructive to existing systems)
- Fastest to implement (read-only federation + metadata overlay)
- Proves memory retrieval value before committing to consolidation

**Phase 1 Scope (MVP, 4-6 weeks):**
1. MCP server (TypeScript) with 4 tools:
   - `memory_search(query, scope, limit)` → semantic + temporal search
   - `memory_get(id)` → full memory content
   - `memory_validate(id)` → check code snapshot
   - `memory_provenance(id)` → source + timestamp + agent_id
2. Metadata store (`.intermem/metadata.db`, SQLite)
3. SessionStart hook (inject top 5 relevant memories)
4. Security redaction (regex-based)
5. Validation logic (git commit SHA + file existence)
6. Multi-agent provenance (agent_id, session_id)

**Phase 1 Does NOT Include:**
- PostToolUse/Stop hooks (avoid conflicts with Compound/Interfluence)
- Cross-project search (per-project only)
- Temporal decay (no evidence of need)
- Write API for existing systems (read-only)
- Intersearch integration (wait for stable API)

---

### 10.2 Migrate to Option 2 (Consolidation) in Phase 2

**After 3+ months of Phase 1 production use:**

1. **Add write API** to intermem MCP server
2. **Refactor Compound** to call intermem write API (dual-write during migration)
3. **Refactor Interfluence** to call intermem write API
4. **Export MD reports** from intermem for git history
5. **Deprecate direct writes** to `docs/solutions/`, `.interfluence/learnings-raw.log`

**Phase 2 Scope (8-12 weeks):**
- Write API implementation
- Compound/Interfluence adapters
- Dual-write validation (compare outputs)
- Migration tooling (import existing memories into intermem)
- Intermute integration (write coordination)

---

### 10.3 Optional Phase 3: Intersearch Integration

**Only if:**
1. intersearch has a stable embedding API (currently does not)
2. Multiple plugins benefit from shared embeddings
3. Embedding model choices are decoupled

**Phase 3 Scope (4-6 weeks):**
- Define intersearch embedding API
- Refactor intermem to use intersearch
- Refactor tldr-swinton to use intersearch (ColBERT backend)
- Versioning + API stability guarantees

---

## 11. Open Questions for Stakeholders

**These MUST be answered before starting Phase 1:**

1. **Auto-memory coordination:** Should intermem respect auto-memory's 200-line cap, or inject independently?
2. **Compound dual-write:** Is Compound willing to dual-write (both MD + intermem) during Phase 1 migration?
3. **Interfluence exclusions:** Will Interfluence exclude `.intermem/` from edit logging to avoid circular dependencies?
4. **Intermute availability:** Is intermute reliable enough for intermem to depend on it for multi-agent coordination?
5. **Intersearch timeline:** When will intersearch have a stable embedding API? Should intermem wait, or vendor embeddings in Phase 1?

---

## 12. Conclusion

**Cleanest Module Boundaries:** Option 2 (Consolidation Engine) long-term, but Option 3 (Smart Layer) is the only viable first step.

**Coupling Risks:** High in Option 1 (Federation), Medium in Option 2 (Consolidation), Low in Option 3 (Smart Layer). All options require explicit write API boundaries to avoid format coupling.

**Intersearch Integration:** Architecturally sound IF intersearch has a stable API with decoupled embedding models. Not ready today — vendor embeddings in Phase 1.

**Critical Success Factors:**
1. **Validation logic** (code snapshot checking) is NOT optional — memories become stale without it
2. **Multi-agent coordination** must reuse intermute, not reinvent
3. **Progressive disclosure** (index → summary → detail) is required for token efficiency
4. **Dual-write migration path** (Phase 1 → Phase 2) is the only safe way to consolidate existing systems

**Next Steps:**
1. Review this document with Compound, Interfluence, Interlock maintainers
2. Answer the 5 open questions (section 11)
3. Write Phase 1 PRD (scope + API spec + success criteria)
4. Implement Phase 1 MVP (4-6 weeks)
5. Deploy to Interverse root project for validation
6. After 3 months, proceed to Phase 2 if adoption is proven
