# Bigend Dirty Row Tracking — Brainstorm

**Bead:** iv-t217
**Phase:** brainstorm (as of 2026-02-23T16:06:21Z)
**Date:** 2026-02-23
**Status:** Decided

## What We're Building

Section-level dirty tracking for Bigend's dashboard renderer. Currently, every 2-second tick rebuilds the entire dashboard string (stats, runs, dispatches, sessions, agents, activity feed) through lipgloss, even when nothing changed. This adds a per-section cache that skips re-rendering for sections whose source data hasn't changed.

**Expected impact:** ~90% of render work skipped on stable frames (most ticks change zero or one section).

## Why This Approach

### Section-level cache with FNV data hashing

Each of the 6 dashboard sections gets:
- A **cached rendered string** (the lipgloss output from last render)
- An **FNV hash** of the source data that produced it

On `View()`, before rendering each section, hash its current data and compare against the cache. Cache hit → return stored string. Cache miss → render, store, return.

**Why this over alternatives:**
- **vs. full-frame hash:** Too coarse — any change anywhere forces full re-render. Section-level lets us skip 5 sections when only 1 changed.
- **vs. generation counters:** Requires aggregator changes (adding counter bumps on every mutation). Hashing is self-contained in the TUI layer — no cross-package coupling.
- **vs. cell-level bitmap (FrankenTUI Tier 2/3):** Overkill. Bigend renders through lipgloss string composition, not a cell grid. Bubble Tea's own internal differ handles line/cell-level diffing after we return the string. Our optimization target is the *rendering* cost, not the *diffing* cost.

## Key Decisions

1. **Granularity: 6 logical sections** — `stats`, `runs`, `dispatches`, `sessions`, `agents`, `activity`. These map to the existing `renderDashboard()` sub-calls.
2. **Hash function: FNV-1a (64-bit)** — stdlib `hash/fnv`, zero dependencies. Hash the relevant state fields per section (counts, IDs, timestamps).
3. **Cache storage: `map[sectionID]sectionEntry` on Model** — initialized in model constructor, invalidated on resize (width/height change forces full re-render).
4. **Resize invalidation** — Clear entire cache when `tea.WindowSizeMsg` is received, since lipgloss widths change.
5. **Tab-scoped caching** — Only the Dashboard tab uses section caching. Sessions/Agents tabs delegate to `bubbles/list.Model` which has its own update guards.
6. **No aggregator changes** — All dirty tracking is self-contained in `internal/bigend/tui/`. The aggregator API remains unchanged.

## Section → Data Mapping

| Section | Source Data | Hash Inputs |
|---------|------------|-------------|
| Stats | `state.Sessions`, `state.Agents`, `state.Projects`, `state.Kernel.Metrics` | lengths + key metric values |
| Active Runs | `state.Kernel.Runs` | run count + each run's ID/status/progress |
| Dispatches | `state.Kernel.Dispatches` | dispatch count + each dispatch ID/status |
| Recent Sessions | first 5 `state.Sessions` | session IDs + statuses |
| Registered Agents | first 5 `state.Agents` | agent IDs + statuses |
| Activity Feed | first 10 `state.Activities` | activity IDs + timestamps |

## Open Questions

- **Cache warm-up:** First render after startup always misses (cold cache). This is fine — the current behavior is full render every time anyway.
- **Hash collision risk:** FNV-64 has ~2^-32 collision probability per comparison. At 6 sections × 0.5 Hz tick = 3 hashes/sec, this is negligible. No need for full structural comparison as a fallback.

## References

- FrankenTUI research: `apps/autarch/docs/research/frankentui-research-synthesis.md` (Tier 1, Priority: High)
- Current renderer: `apps/autarch/internal/bigend/tui/render_dashboard.go`
- Model definition: `apps/autarch/internal/bigend/tui/model.go`
- ResizeCoalescer (already ported from FrankenTUI): `apps/autarch/pkg/tui/resize_coalescer.go`
