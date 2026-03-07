---
artifact_type: brainstorm
bead: iv-nnxzo
stage: discover
---

# Memory Architecture Convergence Across Demarch

**Date:** 2026-03-07
**Bead:** iv-nnxzo (P1 research)

## The Landscape

Demarch has **10 memory-shaped systems** across 3 layers. Each was built to solve a specific problem. None was designed with the others in mind.

### System Map

| System | What it remembers | Storage | Scope | Decay |
|--------|------------------|---------|-------|-------|
| **Intercore kernel** | Run state, events, costs, routing, discoveries, sessions | SQLite (27 tables, .clavain/intercore.db) | Project | TTL-optional |
| **Interspect** | Agent accuracy evidence, canary windows, routing calibration | SQLite (.clavain/interspect/) | Project | Evidence: none; Canary: 14d |
| **Intermem** | Promoted facts from MEMORY.md → AGENTS.md/CLAUDE.md | SQLite + JSONL + Markdown | Project | 14d grace + -0.1/14d |
| **Interfluence** | Voice profiles, writing corpus, edit learnings | Filesystem (markdown + YAML) | Project | Manual refine |
| **Intercache** | Content-addressed file blobs, access patterns | SQLite + blob store (~/.intercache/) | Global | Manual invalidate |
| **Interknow** | Engineering patterns with provenance | Markdown files (config/knowledge/) | Project | 10-review archival |
| **Interject** | Discovery interest profile, scan results, feedback | SQLite (~/.interject/) + kernel mirror | Global + kernel | 30d implied |
| **Clavain auto-memory** | Session learnings, gotchas, topic files | Markdown (~/.claude/projects/) | Per-project | Manual |
| **Clavain compound docs** | Engineering solutions with YAML frontmatter | Markdown (docs/solutions/) | Project | Manual archive |
| **Session artifacts** | Sprint state, verdicts, checkpoints | .clavain/ filesystem | Project | Permanent |

## The Problem

### 1. Overlapping domains

Three systems store "engineering knowledge":
- **Interknow** (`config/knowledge/`) — patterns with provenance and decay
- **Clavain compound docs** (`docs/solutions/`) — categorized solutions with YAML frontmatter
- **Clavain auto-memory** (`~/.claude/projects/*/memory/`) — free-form learnings

A lesson discovered during debugging could reasonably live in any of these. Today, `/compound` writes to `docs/solutions/`, while `/interknow:compound` writes to `config/knowledge/`. Neither checks the other for duplicates.

### 2. No shared retrieval surface

Each system has its own read path:
- Intercache: `cache_lookup` (SHA256 key)
- Interknow: `/interknow:recall` (keyword match + optional qmd semantic)
- Interspect: `_interspect_get_classified_patterns()` (SQL query)
- Interject: `interject_inbox` (score filter)
- Clavain memory: Claude reads MEMORY.md at session start

There's no unified "what does the system know about X?" query. An agent asking about rate limiting patterns would need to check interknow, compound docs, MEMORY.md, and possibly interspect evidence — separately.

### 3. Inconsistent decay and retention

| System | Decay model | Problem |
|--------|-------------|---------|
| Intermem | -0.1/14d with hysteresis | Well-designed but only covers MEMORY.md → AGENTS.md promotion |
| Interknow | 10-review archival | Counts reviews, not time — stale knowledge can persist forever if unvisited |
| Interspect | Evidence: none | Evidence table grows unbounded |
| Intercore | TTL on state table only | 27 tables, most have no cleanup |
| Intercache | Manual invalidate | Blobs accumulate; no LRU or size-based eviction |
| All others | Manual / none | Hope someone notices |

### 4. Dual-store divergence risk

Interject maintains both a local SQLite DB and a kernel mirror (via `ic discovery submit`). The brainstorm for iv-wie5i explicitly chose dual-write as a transition strategy, but it creates a permanent divergence risk if not eventually converged.

### 5. No memory categories taxonomy

The systems don't agree on what "memory" means. Some store facts (interknow, compound docs), some store evidence (interspect), some store learned preferences (interfluence, interject interest profile), and some store operational state (intercore, session artifacts). There's no shared vocabulary for distinguishing these.

## Proposed Memory Categories

Based on the survey, I see 5 distinct categories of memory:

### C1: Operational State
**What:** Current status of runs, dispatches, sprints, locks, sessions.
**Examples:** intercore runs table, session artifacts, coordination locks.
**Characteristic:** Short-lived, high-write, consumed by orchestration logic.
**Owner:** Intercore kernel (already the authority).
**Decay:** TTL-based; completed runs can be pruned after N days.

### C2: Evidence & Calibration
**What:** Observations about agent behavior used to improve routing and trust.
**Examples:** Interspect evidence, canary windows, routing calibration, interject feedback signals.
**Characteristic:** Append-only, consumed by learning algorithms, feeds back into scoring/routing.
**Owner:** Split — interspect for agent evidence, interject for discovery evidence.
**Decay:** Sliding windows (interspect canary already does this); old evidence should be summarized and archived, not deleted.

### C3: Learned Preferences
**What:** Models trained from feedback — interest profiles, voice profiles, source weights.
**Examples:** Interject interest_profile, interfluence voice-profile.md, interject source_weights.
**Characteristic:** Slowly-evolving, compact (a vector + a few weights), derived from C2 evidence.
**Owner:** Plugin-local (each plugin owns its own model). Kernel doesn't need these.
**Decay:** Exponential moving average already handles staleness. No additional policy needed.

### C4: Curated Knowledge
**What:** Human-validated patterns, solutions, and reference material.
**Examples:** Interknow entries, compound docs, canon docs.
**Characteristic:** High-quality, reviewed, cross-referenced. Written by humans or by agents with human approval.
**Owner:** Project-level docs (docs/solutions/, config/knowledge/).
**Decay:** Provenance-based (interknow's 10-review archival is the right idea; compound docs need similar).

### C5: Ephemeral Context
**What:** Per-session working memory — auto-memory, intercache blobs, intermediate results.
**Examples:** MEMORY.md topic files, intercache blobs, intermem stability snapshots.
**Characteristic:** High-volume, low-ceremony, may or may not be promoted to C4.
**Owner:** Plugin-local filesystem.
**Decay:** intermem's promotion + decay model is the gold standard here. Apply similar to others.

## Key Decisions

### D1: Don't merge storage — unify retrieval

**Decision:** Keep each system's storage where it is. Add a unified retrieval API.

**Rationale:** Migrating 10 systems into a shared store would be a massive, fragile project. The real problem isn't where data lives — it's that there's no single query surface. A thin retrieval layer that queries across systems and returns ranked results solves the pain without the migration risk.

**Shape:** A new `/recall` command (or extension of interknow's recall) that:
1. Queries interknow entries (keyword + semantic)
2. Searches compound docs index.json
3. Searches MEMORY.md topic files
4. Optionally queries interspect evidence
5. Returns ranked, deduplicated results with source attribution

### D2: Adopt intermem's decay model as the standard

**Decision:** Systems that lack decay should adopt intermem's approach: grace period + linear decay + hysteresis.

**Rationale:** Intermem already solved the hard problems — false-positive demotion prevention via hysteresis, crash recovery via WAL journal, re-activation of demoted entries. Rather than inventing new decay models per system, standardize on intermem's pattern.

**Affected systems:**
- Interspect evidence: add 90-day rolling window for old evidence (keep summaries)
- Intercore runs: add 30-day TTL for completed runs
- Intercache: add LRU eviction when blob store exceeds size threshold
- Interknow: keep 10-review archival but add 180-day staleness check

### D3: Converge interknow and compound docs

**Decision:** Merge interknow and compound docs into a single "curated knowledge" system.

**Rationale:** Both store engineering patterns with metadata. The only differences are:
- Storage format (interknow: config/knowledge/, compound: docs/solutions/)
- Metadata (interknow: YAML frontmatter with provenance; compound: YAML with problem_type)
- Tooling (interknow: /recall; compound: /compound)

The convergence path: compound docs adopt interknow's provenance model (lastConfirmed, decay counter), and interknow entries move to docs/solutions/ (already the more natural location for project-scoped knowledge).

### D4: Keep learned preferences plugin-local

**Decision:** Interject's interest profile and interfluence's voice profile stay in their respective plugins. No kernel-level treatment.

**Rationale:** These are ML model parameters specific to each plugin's domain. Centralizing them adds coupling without benefit — no other system needs to read interject's topic_vector or interfluence's voice profile. The kernel provides the evidence (C2) that feeds into these models, but the models themselves belong to the plugins.

### D5: Intercore is the single owner for C1 and the event bus for C2

**Decision:** All operational state flows through intercore. All evidence producers emit events to the kernel event bus.

**Rationale:** This is already the direction. Interspect writes to kernel event tables. Interject submits discoveries to kernel. The gap is that some systems still maintain local-only state that should be kernel events (e.g., intercache hit/miss stats, interfluence learning signals).

**Not now:** This is an aspiration, not an immediate action. The kernel event bus exists but adding emitters to every system would be premature optimization.

## What This Means for Each System

| System | Category | Recommended change | Priority |
|--------|----------|-------------------|----------|
| Intercore | C1 + C2 event bus | Add TTL for completed runs | P3 |
| Interspect | C2 | Add 90-day evidence rolling window | P3 |
| Intermem | C5 → C4 bridge | Already well-designed; no changes needed | — |
| Interfluence | C3 + C5 | No changes; preferences are plugin-local | — |
| Intercache | C5 | Add LRU eviction (size-based) | P3 |
| Interknow | C4 | Converge with compound docs | P2 |
| Interject | C2 + C3 | Already kernel-native; keep dual-write for now | — |
| Clavain memory | C5 | Intermem handles promotion; no changes | — |
| Compound docs | C4 | Converge with interknow; add provenance | P2 |
| Session artifacts | C1 | Already kernel-scoped; no changes | — |

## Open Questions

1. **Unified retrieval latency.** Querying 4+ backends per recall could be slow. Should we pre-index into a single search corpus (via intersearch embeddings), or query on-demand with caching?

2. **Cross-project memory.** Currently only Clavain auto-memory and intercache are cross-project. Should curated knowledge (C4) be shareable across projects? If so, via symlinks, a shared docs/ directory, or a dedicated cross-project store?

3. **Interknow + compound docs migration.** Which direction? Move interknow entries into docs/solutions/ (simpler, fewer tools to maintain) or move compound docs into config/knowledge/ (more structured, better provenance)? Leaning toward docs/solutions/ since it's already got 73 entries and human-readable organization.
