# Intermem Brainstorm: Dedicated Memory Plugin for Interverse
**Bead:** iv-3xm0

**Date:** 2026-02-16 (updated 2026-02-17)
**Status:** Complete — brainstorm finalized
**Decision:** Phased Option 3 (Smart Layer on Top), starting with Phase 0.5 (Memory Synthesis)
**Next step:** Strategy → PRD → Plan

---

## Core Idea

A dedicated memory plugin called **intermem** that unifies and enhances the fragmented memory infrastructure across the Interverse ecosystem. Leverages existing modules (Compound, Interfluence, interlock, intermute, intersearch) rather than replacing them.

---

## Existing Memory Infrastructure (5 Systems)

| System | Storage | Trigger | Retrieval | Scope |
|--------|---------|---------|-----------|-------|
| **Auto-memory** (CC built-in) | `~/.claude/projects/*/memory/*.md` | Manual or auto | System prompt injection (200 lines cap) | Per-project |
| **Compound** (Clavain) | `docs/solutions/*.md` with YAML frontmatter | Auto-hook (signal weight >= 3) | Manual search, CLAUDE.md refs | Per-repo |
| **Interfluence learnings** | `.interfluence/learnings-raw.log` | PostToolUse:Edit hook | MCP tools | Per-project, style-specific |
| **`.clavain/learnings/`** | Markdown in repo (committed) | Manual | Read by review agents | Per-repo |
| **CLAUDE.md / AGENTS.md** | Markdown files | Manual | Always loaded at session start | Per-project |

**Key problem:** 5 independent stores, zero coordination, overlapping responsibilities, no cross-referencing, no unified retrieval, no validation, no decay.

---

## Landscape Research (13 External Systems)

### Full Analysis

| System | Storage | Capture | Retrieval | Unique Strength |
|--------|---------|---------|-----------|-----------------|
| **claude-mem** (28.6k stars) | SQLite + Chroma vectors | 5 lifecycle hooks | 3-layer progressive disclosure | Semantic + keyword hybrid, 10x token savings |
| **claude-diary** | Markdown diary entries | PreCompact hook | Passive (CLAUDE.md merge) | Generative Agents reflections |
| **claude-brain** | Single `.mv2` binary | Auto-inject at start | Rust sub-ms search | Portable single file |
| **claude-supermemory** | Cloud (Supermemory) | Signal extraction hooks | Cloud API | Team sharing |
| **MemCP** (MIT CSAIL) | SQLite MAGMA 4-graph | PreCompact hooks | 5-tier degrading search | 218x token savings, context-as-variable |
| **memory-mcp** | JSON + CLAUDE.md | Stop/PreCompact hooks | Haiku LLM synthesis | Temporal decay ($0.001/extraction) |
| **ShieldCortex** | SQLite 3-tier | Hooks | ONNX embeddings + FTS5 | 6-layer security pipeline |
| **Nemp** | Plain JSON | Manual + suggest | Semantic keyword expansion | CLAUDE.md conflict detection |
| **Basic Memory** | Markdown knowledge graph | Manual (LLM writes) | SQLite + graph traversal | Human-readable, Obsidian-compatible |
| **mcp-memory-service** | SQLite + vectors | Smart auto-capture | Hybrid BM25 + vector | 5ms injection, web dashboard |
| **memory-keeper** | SQLite | Manual checkpoints | Full-text + regex | Checkpoint/restore |
| **Copilot Memory** | Repository-level | Automatic | Citation validation | Validates memories against current code |
| **Windsurf Cascade** | Workspace-scoped | Automatic | Relevance-based injection | Zero-cost, automatic |

### 7 Gaps in the Landscape

1. **No cross-project knowledge sharing** — almost everything is project-scoped
2. **No forgetting discipline** — most stores grow monotonically
3. **No memory validation on retrieval** — only Copilot checks if memories are still true
4. **Security is afterthought** — only ShieldCortex addresses memory poisoning
5. **No interoperable standard** — every system invents its own format
6. **No multi-agent memory coordination** — critical for Interverse
7. **No memory provenance** — no link to when/why a memory was created

### Sources

- [claude-mem](https://github.com/thedotmack/claude-mem)
- [claude-diary](https://github.com/rlancemartin/claude-diary)
- [claude-brain / memvid](https://github.com/memvid/claude-brain)
- [claude-supermemory](https://github.com/supermemoryai/claude-supermemory)
- [MemCP](https://github.com/maydali28/memcp)
- [memory-mcp](https://github.com/yuvalsuede/memory-mcp)
- [ShieldCortex](https://github.com/mkdelta221/claude-cortex)
- [Nemp](https://github.com/SukinShetty/Nemp-memory)
- [Basic Memory](https://github.com/basicmachines-co/basic-memory)
- [mcp-memory-service](https://github.com/doobidoo/mcp-memory-service)
- [memory-keeper](https://github.com/mkreyman/mcp-memory-keeper)
- [Copilot Memory](https://docs.github.com/en/copilot/concepts/agents/copilot-memory)
- [Windsurf Cascade](https://docs.windsurf.com/windsurf/cascade/memories)

---

## Architecture Options Evaluated

### Option 1: Federation Layer
intermem doesn't own storage — queries all existing stores through unified MCP interface ("memory router").

**Pros:** No migration, respects existing systems, lightweight, additive
**Cons:** Lowest common denominator retrieval, can't add decay/validation without owning data

### Option 2: Consolidation Engine
intermem owns single canonical store (SQLite + embeddings). Existing systems feed into it.

**Pros:** Single source of truth, can add all missing features, cleanest retrieval
**Cons:** Migration complexity, divergence risk, heavier infrastructure

### Option 3: Smart Layer on Top ← RECOMMENDED
intermem adds missing capabilities (validation, decay, cross-project, provenance) while leaving existing stores intact. Maintains metadata overlay.

**Pros:** Non-destructive, incremental, fail-open, lowest risk
**Cons:** Two systems to maintain, overlay can drift

### Option 4: Replace Everything
intermem subsumes all existing memory systems. Clean slate.

**Pros:** Cleanest architecture, no legacy
**Cons:** Massive migration, loses battle-tested patterns, high risk

---

## Flux-Drive Analysis (4 Agents)

### fd-architecture: Module Boundaries
- **Option 3 wins** — lowest coupling, read-only federation + metadata overlay
- Don't reuse tldr-swinton's ColBERT embeddings — different semantic space (code vs natural language). Use sentence-transformers
- Don't integrate intersearch yet — no public API exists (`__version__ = "0.1.0"` only). Vendor embeddings in Phase 1
- Reuse **intermute for multi-agent coordination**, don't reinvent locking
- Define explicit ownership: intermem owns retrieval/decay/dedup; Compound/Interfluence own capture triggers
- Anti-patterns flagged: God Module risk, Leaky Abstraction (Compound YAML exposure), Circular Dependency (Intermem ↔ Interfluence)
- Progressive disclosure (index → summary → detail) is a significant missed opportunity — must implement
- Full review: `intermem/docs/research/architecture-review-of-intermem.md`

### fd-decisions: Decision Quality
- **P1: Missing reversibility analysis** — never asked "what does rollback cost?"
  - Option 3: delete overlay (trivial)
  - Option 2: restore from backups (expensive)
  - Option 4: catastrophic (no rollback)
- **P1: No starter option** — all 4 options are full architectural commitments. Need "Option 0: instrument first"
- **P2: Anchoring bias toward Option 2** — landscape research heavy on consolidation systems primes us toward it
- **P2: Implicit decision criteria** — 7 gaps identified but not ranked by priority
- Need a **theory of change**: are agents suffering from fragmentation, or is the real problem memory quality?
- Validation experiments needed before committing to architecture
- Full review: `intermem/docs/research/decision-quality-review-of-intermem.md`

### fd-systems: Feedback Loops & Emergence
- **P1: Auto-capture death spiral** — more capture → more noise → worse retrieval → more debugging → MORE capture. No negative feedback loop designed
- **P1: Preferential attachment** — early/active agents dominate shared memory (Clavain with 12 hooks floods graph, crowding out other domains)
- **P2: Validation-decay hysteresis** — high-confidence memories become immortal (rich-get-richer), even if wrong. New correct memories can't displace entrenched incorrect ones without explicit invalidation
- **P2: Cross-project phase transition** — sharing is not linear, can cascade into monolithic shared context at ~8+ projects
- **P3: Options are pace layer strategies** — Option 1/3 have crumple zones (if intermem fails, base stores survive), Option 2/4 don't
- Forgetting discipline is a MISSING BALANCING LOOP — must design which trigger (time, access, validation, capacity, confidence)
- Full review: `intermem/docs/research/systems-thinking-review-of-intermem.md`

### fd-resilience: Antifragility
- **Option 3 scores A across every resilience dimension**
- **Option 2 scores C-D** (single source of truth = opposite of antifragile)
- **Option 4 scores F** (catastrophic failure modes)
- Proposed concrete 4-phase MVP with decision gates and rollback strategies
- Critical: **validate the assumption first** — run 1-day experiment to test whether unified retrieval actually helps agents
- Embedding lock-in risk: model versioning, provider switching, fallback to keyword search
- Full review: `intermem/docs/research/resilience-review-of-intermem.md`

---

## Emerging Consensus: Phased Option 3

### Risk-Sequenced Phases

| Phase | What | Decision Gate | Rollback Cost |
|-------|------|---------------|---------------|
| **0** | Instrument existing stores (usage frequency, staleness, relevance) | Is fragmentation actually the problem? | Zero |
| **0.5** | Memory synthesis: auto-memory → AGENTS.md/CLAUDE.md graduation | Do promoted facts stay stable? Does auto-memory stay under 200 lines? | Stop promoting, revert AGENTS.md edits |
| **1** | Validation overlay (`.intermem/metadata.db`, citation-checking) | Does validation reduce stale injections >30%? | Delete one SQLite file |
| **2** | Decay + progressive disclosure (TTLs, index→summary→detail) | Does decay reduce bloat >50%? | Disable decay rules |
| **3** | Cross-project search (global metadata, semantic embeddings) | Do agents use cross-project >10x/week? | Stop global indexing |
| **4** | Consolidation (Compound/Interfluence write through intermem) | Dual-write matches original outputs? | Revert hooks |

### Key Design Principles (from all 4 reviews)

1. **Design the growth limiter FIRST** — the balancing loop that prevents auto-capture death spiral
2. **Validate assumption before building** — is fragmentation the real problem, or is it memory quality?
3. **Vendor embeddings in Phase 1** — don't depend on intersearch (no API yet)
4. **Reuse intermute for coordination** — don't reinvent multi-agent locking
5. **Define ownership boundaries explicitly** — who owns capture vs retrieval vs decay vs dedup
6. **Progressive disclosure is mandatory** — index → summary → detail for token efficiency
7. **Every phase must be independently rollback-able** — delete overlay, base stores untouched

### Interverse-Specific Constraints

- **Hook budget**: Clavain already has 12 hooks. Start with MCP server + 1 SessionStart hook only
- **Token budget**: interstat tracks budgets. Memory injection must be token-aware (≤100 lines for intermem, alongside auto-memory's 200)
- **Multi-agent**: intermute handles coordination. intermem is a consumer, not a coordinator
- **Embedding model**: sentence-transformers (`all-MiniLM-L6-v2`) for natural language, NOT ColBERT (that's for code in tldr-swinton)
- **Circular dependency guard**: `.intermem/` must be excluded from Interfluence's `learn-from-edits.sh` hook

---

## Phase 0.5: Memory Synthesis (auto-memory → AGENTS.md/CLAUDE.md)

The missing balancing loop identified by fd-systems. Without this, auto-memory grows monotonically until the 200-line cap silently truncates hard-won lessons off the bottom.

### The Problem

```
Session learnings → auto-memory (fast capture)
                  → stays there forever (no graduation)
                  → 200-line cap truncates oldest entries
                  → valuable stable knowledge silently lost
```

### The Fix

```
Session learnings → auto-memory (fast capture, scratchpad)
                  → intermem periodic synthesis
                  → stable facts promoted to AGENTS.md/CLAUDE.md (curated reference)
                  → promoted items pruned from auto-memory (keeps it lean)
```

### How It Works

1. Read auto-memory files (`~/.claude/projects/*/memory/*.md`) for current project
2. Identify facts stable across 3+ sessions (not one-off observations)
3. Check if already in AGENTS.md/CLAUDE.md (dedup)
4. Propose promotions (user in the loop — interactive approval)
5. Write promoted facts to appropriate section of AGENTS.md or CLAUDE.md
6. Prune promoted items from auto-memory to reclaim space under 200-line cap

### Why This Lives in Intermem (Not Clavain)

- It's the core "smart layer" operation: read existing store, add intelligence, write curated output
- It's the designed **negative feedback loop** that prevents the auto-capture death spiral
- It establishes intermem's value before any MCP server or embeddings are built
- It's the simplest possible MVP that proves the concept: memory lifecycle management

### Trigger Options

- **Skill-based**: `/intermem:synthesize` — user-initiated, safest starting point
- **Hook-based**: SessionStart or Stop hook checks if auto-memory exceeds threshold (e.g., >150 lines) and suggests synthesis
- **Scheduled**: Periodic (weekly?) synthesis pass across all projects

### Open Design Questions

- Should synthesis require user approval for each promotion, or batch-approve?
- Should it run per-project or globally across all 16+ project memory dirs?
- Where do promoted facts go — AGENTS.md (shared with all agents) or CLAUDE.md (Claude Code only)?
  - Rule of thumb: structural/architectural facts → AGENTS.md, behavioral preferences → CLAUDE.md

---

## Open Questions (for next session)

1. **Phase 0 or Phase 1?** — Should we instrument existing stores first (gather data on what's used/ignored), or jump straight to validation overlay?
2. **MCP server language** — TypeScript (matches interfluence pattern) or Python (matches intersearch/tldr-swinton)?
3. **Storage location** — per-project `.intermem/` or global `~/.claude/intermem/`?
4. **Forgetting mechanism** — which trigger for decay: time, access, validation, capacity, confidence, or combination?
5. **Security redaction** — regex-based (simple) or LLM-based (more accurate but costs tokens)?

---

## Files Generated

- `intermem/docs/brainstorms/2026-02-16-intermem-brainstorm.md` — this file
- `intermem/intermem/docs/research/architecture-review-of-intermem.md` — fd-architecture full review
- `intermem/intermem/docs/research/decision-quality-review-of-intermem.md` — fd-decisions full review
- `intermem/intermem/docs/research/systems-thinking-review-of-intermem.md` — fd-systems full review
- `intermem/intermem/docs/research/resilience-review-of-intermem.md` — fd-resilience full review
