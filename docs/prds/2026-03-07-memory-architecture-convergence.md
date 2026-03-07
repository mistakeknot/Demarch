---
artifact_type: prd
bead: iv-nnxzo
stage: design
---

# PRD: Memory Architecture Convergence

## Problem

Demarch has 10 memory-shaped systems with overlapping domains, no shared retrieval surface, inconsistent decay policies, and no taxonomy for categorizing what memory is. Agents can't answer "what do we know about X?" without querying 4+ backends separately. Engineering knowledge lives in 3 places (interknow, compound docs, auto-memory) with no dedup.

## Solution

Establish a 5-category memory taxonomy (C1-C5), unify retrieval without merging storage, standardize decay on intermem's model, and converge the two curated knowledge systems (interknow + compound docs).

## Deliverables

### R1: Memory Categories Taxonomy (this document)

**What:** Formal definition of 5 memory categories with ownership rules.

| Category | Name | Owner | Decay model |
|----------|------|-------|-------------|
| C1 | Operational State | Intercore kernel | TTL-based (30d for completed runs) |
| C2 | Evidence & Calibration | Interspect + Interject | Rolling window (90d evidence, 14d canary) |
| C3 | Learned Preferences | Plugin-local | Exponential moving average (existing) |
| C4 | Curated Knowledge | docs/solutions/ | Provenance-based (10-review + 180d staleness) |
| C5 | Ephemeral Context | Plugin-local filesystem | Intermem promotion model (14d grace + decay) |

**Decision rule for "where does this go?":**
- Is it about current system status? → C1 (kernel)
- Is it an observation about agent/system behavior? → C2 (evidence)
- Is it a learned model parameter? → C3 (plugin-local)
- Is it a human-validated pattern or solution? → C4 (docs/solutions/)
- Is it a working note that might become permanent? → C5 (auto-memory → intermem promotion)

### R2: System Map

Each of the 10 systems mapped to its primary category, current state, and recommended next action:

| System | Primary Cat | Secondary | Change needed | Priority |
|--------|------------|-----------|---------------|----------|
| Intercore kernel | C1 | C2 bus | Add TTL for completed runs table | P3 |
| Interspect | C2 | — | Add 90d rolling window for old evidence | P3 |
| Intermem | C5→C4 bridge | — | None — gold standard for decay | — |
| Interfluence | C3 | C5 | None — preferences are plugin-local | — |
| Intercache | C5 | — | Add LRU eviction (size-based) | P3 |
| Interknow | C4 | — | Converge into docs/solutions/ | P2 |
| Interject | C2+C3 | — | Already kernel-native; no changes | — |
| Clavain auto-memory | C5 | — | Intermem handles promotion | — |
| Compound docs | C4 | — | Adopt provenance from interknow | P2 |
| Session artifacts | C1 | — | Already kernel-scoped | — |

### R3: Recommendations

**R3.1: Unify retrieval, not storage (P2)**
Add a unified `/recall` command that queries across C4 systems:
- Interknow entries (config/knowledge/)
- Compound docs (docs/solutions/index.json)
- MEMORY.md topic files
Returns ranked, deduplicated results with source attribution.
Don't merge storage — each system keeps its store.

**R3.2: Converge interknow + compound docs (P2)**
Move interknow entries into docs/solutions/ format. Compound docs adopt interknow's provenance model (lastConfirmed, decay counter, independent/primed flag). `/compound` becomes the single write path; `/recall` becomes the single read path.

**R3.3: Standardize decay on intermem's model (P3)**
Systems without decay adopt: grace period + linear decay + hysteresis.
- Interspect: 90d rolling window for evidence
- Intercore: 30d TTL for completed runs
- Intercache: size-based LRU eviction
- Interknow (post-convergence): 180d staleness check added to 10-review archival

**R3.4: Keep C3 (learned preferences) plugin-local (no action)**
Interest profiles (interject) and voice profiles (interfluence) stay in their plugins. The kernel provides the evidence (C2) that feeds these models, but the models themselves don't need kernel-level treatment.

**R3.5: Document the taxonomy in PHILOSOPHY.md (P2)**
Add a "Memory Architecture" section to PHILOSOPHY.md defining C1-C5 and the decision rule. This prevents future plugins from creating yet another knowledge store without checking if an existing category fits.

## Non-goals

- Migrating all memory into a single database (too fragile, no proven benefit)
- Cross-project knowledge sharing (future work; needs clear use case first)
- Real-time event streaming between memory systems (kernel event bus exists but wiring every system is premature)
- Replacing intercore's 27-table schema (it's the kernel; it stays)

## Dependencies

- R3.1 depends on intersearch (embedding-based retrieval across docs)
- R3.2 depends on agreement on provenance schema for compound docs
- R3.3 is independent per-system work
- R3.5 is a documentation task with no code dependencies
