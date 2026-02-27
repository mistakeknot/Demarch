---
title: Cross-Document Philosophy Alignment
category: patterns
tags: [documentation, philosophy, vision, roadmap, consistency, governance]
created: 2026-02-27
severity: medium
reuse: high
modules: [demarch]
---

# Cross-Document Philosophy Alignment

## Problem

A project with multiple living docs (PHILOSOPHY.md, vision, roadmap, AGENTS.md, CLAUDE.md, architecture, glossary, reference, README) develops **document drift** — the same concept described differently across docs, with increasingly contradictory claims. Hardcoded counts rot. Aspirational claims become permanent constraints. Terminology diverges.

This is especially acute when a new foundational doc (like PHILOSOPHY.md) is created *after* the operational docs it should govern. The existing docs encode ad-hoc decisions that may contradict the now-formalized philosophy.

## Symptoms

- The same concept has incompatible framings in different docs (e.g., "permanent safety boundary" in one doc, "trust threshold that softens" in another)
- Static counts disagree across docs (30+, 33+, 37, 42, 53 plugins)
- Priority items in the roadmap contradict values stated in the philosophy
- The philosophy describes something as critical but the roadmap has no item for it
- Publish/workflow entrypoints differ between quick-reference and comprehensive docs

## Root Cause

Documents are written at different times for different audiences. Each doc locally optimizes for its context without cross-referencing the others. Without a systematic alignment pass, drift compounds with every edit.

## Solution: Structured Cross-Document Alignment

### Phase 1: Create or formalize the authority doc

Interview the stakeholder in depth (16+ questions with options and tradeoffs). Consolidate to highest useful abstraction level. The philosophy doc becomes the source of truth for *why* decisions are made.

### Phase 2: Align aspirational docs (vision) against philosophy

Read both docs end-to-end. For each claim in the vision, check if the philosophy says something different. Classify disagreements:

| Type | Example | Resolution Pattern |
|------|---------|-------------------|
| **Contradiction** | "Permanent boundary" vs "trust threshold" | One doc has the more nuanced framing — update the other |
| **Missing qualifier** | "Not self-modifying" (categorical) | Add timescale/context qualifier |
| **Scope mismatch** | "Software dev specifically" vs "already general" | Distinguish product scope from platform scope |
| **Parallel concepts** | Two different autonomy ladders with different levels | Make both explicit, cross-reference |
| **Framing gap** | "Discipline before speed" vs "gates enable velocity" | Philosophy is usually the mature framing |

Present each disagreement to the stakeholder with options and a recommendation. Apply resolutions as edits.

### Phase 3: Align planning docs (roadmap) against philosophy

Different disagreement types emerge:

| Type | Example | Resolution Pattern |
|------|---------|-------------------|
| **Priority mismatch** | Philosophy says "instrument first" but measurement is P1 | Promote the bead priority |
| **Coverage gap** | Philosophy declares X critical but roadmap has no item | Create a new bead at appropriate priority |
| **Scope split** | Philosophy implies broader scope than current roadmap item | Split the bead (e.g., docs P0, interactive flow P1) |

### Phase 4: Align operational docs (AGENTS.md, CLAUDE.md, reference, glossary, architecture)

These are the docs agents actually read every session. Disagreement types:

| Type | Example | Resolution Pattern |
|------|---------|-------------------|
| **Stale absolute** | "Read-only — never writes to kernel" | Add "today:" qualifier matching philosophy |
| **Missing concept** | Architecture v3 doesn't name Gridfire | Add the name and cross-reference |
| **Entrypoint drift** | Different docs recommend different CLI commands | Verify what actually exists, align both |
| **Static inventory rot** | "37 modules" when count has changed | Replace with count-free prose or shell command |
| **Missing link** | README doesn't mention philosophy | Add section with brief summary |

### Phase 5: Verify historical docs are untouched

Research docs (`docs/research/`), brainstorms, plans, and PRDs are point-in-time snapshots. They should NOT be updated — their static counts and claims are historically accurate. Only update **living docs** (those that represent current truth).

## Key Insight: Disagreement Type Varies by Doc Layer

- **Vision ↔ Philosophy**: Contradictions and framing gaps (same concept, different claims)
- **Roadmap ↔ Philosophy**: Priority mismatches and coverage gaps (values not reflected in planning)
- **Operational ↔ Philosophy**: Stale absolutes and missing links (implementation docs lag behind strategy)

Each layer requires a different detection strategy. Don't apply the same template to all.

## Metrics

The three-session alignment pass across Demarch touched:
- 16 disagreements found and resolved (6 vision + 5 roadmap + 5 operational)
- 12 files edited
- 3 new beads created (disagreement pipeline, Gridfire epic, anti-Goodhart research)
- 1 priority promotion (north star metric P1 → P0)
- 1 static count fixed (missed in earlier sweep)

## Cross-References

- PHILOSOPHY.md — the authority doc created in this process
- docs/demarch-vision.md — aspirational doc aligned in Phase 2
- docs/demarch-roadmap.md — planning doc aligned in Phase 3
- docs/guides/naming-conventions.md — created as part of the same session
