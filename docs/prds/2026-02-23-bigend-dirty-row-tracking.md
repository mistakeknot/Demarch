# PRD: Bigend Section-Level Dirty Row Tracking

## Problem

Bigend's dashboard re-renders all 6 sections through lipgloss on every 2-second tick, even when underlying data hasn't changed. This wastes CPU cycles on string composition, style computation, and layout joins for frames that are identical to the previous one.

## Solution

Add a section-level render cache with FNV-1a data hashing. Each dashboard section caches its rendered string and the hash of its source data. On `View()`, compare hashes before rendering — cache hits return the stored string, skipping ~90% of render work on stable frames.

## Features

### F1: Section cache infrastructure
**What:** Define section cache types, FNV hashing helpers, and integrate into Model.
**Acceptance criteria:**
- [ ] `sectionID` enum covers all 6 dashboard sections (stats, runs, dispatches, sessions, agents, activity)
- [ ] `sectionEntry` struct holds rendered string + FNV-64 hash
- [ ] `sectionCache map[sectionID]sectionEntry` field added to `Model`
- [ ] Cache initialized in model constructor (`New()` or `Init()`)
- [ ] `hashData()` helper produces deterministic FNV-64 hashes from arbitrary state fields
- [ ] Unit tests verify hash stability (same input → same hash) and sensitivity (different input → different hash)

### F2: Dashboard render integration
**What:** Wire section cache into `renderDashboard()` so each sub-section checks the cache before rendering.
**Acceptance criteria:**
- [ ] Each of the 6 dashboard sections calls through a cache-checking wrapper
- [ ] Cache hit returns stored string without calling the section's render function
- [ ] Cache miss renders, stores result + hash, then returns
- [ ] Dashboard renders identically to the pre-cache version (no visual regression)
- [ ] Sections that depend on terminal width (all of them via lipgloss) include width in hash inputs

### F3: Resize and tab-switch invalidation
**What:** Clear section cache on events that change layout geometry or visible content.
**Acceptance criteria:**
- [ ] `tea.WindowSizeMsg` clears the entire section cache
- [ ] Tab switch clears cache (different tabs render different content in the same area)
- [ ] Filter activation/deactivation clears cache for affected sections
- [ ] No stale content visible after resize or tab switch

## Non-goals

- Cell-level or row-level dirty bitmaps (FrankenTUI Tier 2/3) — Bubble Tea handles sub-row diffing
- Aggregator-side generation counters — keeping changes self-contained in TUI layer
- Caching for Sessions/Agents list tabs — `bubbles/list.Model` has its own update guards
- Run pane or terminal pane caching — these have existing content-equality guards

## Dependencies

- `hash/fnv` (stdlib — no external deps)
- Existing `aggregator.State` struct shape (read-only dependency)
- Existing `renderDashboard()` sub-functions for each section

## Open Questions

None — all resolved in brainstorm phase.
