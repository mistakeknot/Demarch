# Beads Viewer Repos: Integration Assessment

**Date:** 2026-02-28
**Author:** Claude Sonnet 4.6 (automated assessment)
**Context:** Demarch uses `bd` CLI for beads tracking. Issues stored in `.beads/issues.jsonl` with 2,147 issues at time of assessment. Dashboard work lives in `apps/autarch/` (Bigend = web + TUI, Coldwine = task orchestration). Autarch uses Bubble Tea + Go stack.

---

## Summary

Three repos were examined:
1. `beads_viewer` (iv-6bomz) — Full-featured Go TUI + robot-mode CLI for beads. Production-grade, 56K+ lines of Go, extensive tests.
2. `beads_viewer-pages` (iv-ool7q) — Static GitHub Pages web dashboard backed by SQL.js (WASM) + SQLite for query, force-graph for dependency viz, Chart.js for analytics.
3. `beads_viewer_for_agentic_coding_flywheel_setup` (iv-hol58) — Minimal demonstration deployment of beads_viewer-pages with 3 test issues; the web UI code is byte-identical to beads_viewer-pages except page title.

---

## beads_viewer (iv-6bomz)

**What it is:** A keyboard-driven Go TUI and robot-mode CLI that reads `.beads/beads.jsonl` and provides graph-aware triage, Kanban, insights, and 40+ structured JSON output flags for AI agents.

**Language/Stack:** Go 1.25, Bubble Tea (Elm-arch TUI), Lipgloss, Glamour, Gonum (graph algorithms: PageRank, betweenness, HITS, eigenvector, critical path), SQLite FTS5 (modernc pure-Go), fsnotify (live reload), TOON (token-optimized output format).

**Quality:** High. 56,809 lines of Go across 80+ files in the `ui` package alone. Comprehensive test suite including property-based tests (pgregory/rapid), benchmarks, E2E tests, golden tests, race detector. CI configured. Performance profiling artifacts committed. Opportunity matrices documenting optimization work. AGENTS.md is 23KB with detailed instructions.

**Relevance to Demarch:** Autarch's Bigend is Demarch's multi-project mission control dashboard; beads_viewer is the most sophisticated beads viewer that exists, and Autarch currently has no graph-aware triage or dependency visualization for the 2,147 Demarch issues in `.beads/`.

**Integration opportunities:**

- **`--robot-*` flags pattern** — bv's 40+ robot-mode flags (`--robot-triage`, `--robot-next`, `--robot-plan`, `--robot-insights`, `--robot-graph`, etc.) with JSON/TOON output are immediately useful. Run `bv --robot-triage` against Demarch's `.beads/issues.jsonl` today without any code changes; the loader already supports `issues.jsonl` as a preferred filename.
- **`pkg/analysis/triage.go` — TriageResult struct** — The unified triage output (QuickRef, Recommendations, QuickWins, BlockersToClear, ProjectHealth, Alerts, Commands) is a clean JSON schema that Autarch's Bigend dashboard could consume. Adapt the struct directly into Autarch's beads integration layer.
- **`pkg/analysis/` — 9-metric graph engine** — PageRank, betweenness, HITS, critical path, eigenvector, k-core, cycles, topo sort, density. `gonum/graph` is already a Demarch dependency via Autarch. Port or import `pkg/analysis/` to add graph intelligence to `bd` or Bigend.
- **`pkg/drift/` — Drift detection** — Alert types for new cycles, PageRank changes, velocity drops, abandoned claims, potential duplicates. Directly applicable to Autarch's Coldwine sprint monitoring.
- **`pkg/recipe/` — Saved view configs** — YAML-defined filter/sort/view configurations. Useful pattern for Bigend's "saved views" / filter presets.
- **`pkg/agents/` — AGENTS.md injection** — Auto-injects beads workflow instructions into project AGENTS.md files. Demarch could adopt this pattern to keep all subproject AGENTS.md files current with the `bd`/`bv` workflow.
- **`pkg/watcher/` — Debounced file watcher** — Clean fsnotify wrapper with debounce, platform-specific detection, polling fallback. Useful for Autarch's live-reload feature in Bigend's daemon.
- **`pkg/ui/board.go` — Kanban swimlanes** — Swimlane mode (status / priority / type / label), inline card expansion, search-within-board. Adaptable to Bigend's TUI board tab.
- **`pkg/ui/velocity_comparison.go` — Velocity sparklines** — 4-week velocity by label with trend detection (accelerating/decelerating/erratic). Port to Bigend's sprint view.
- **`pkg/ui/label_dashboard.go` — Label health table** — Critical/warning/healthy label health sorted by severity. Port to Bigend.
- **`pkg/ui/sprint_view.go` — Sprint burndown** — Progress bars, days remaining, at-risk items. Direct analogue to Coldwine sprint tracking.

**Inspiration opportunities:**

- **Two-phase async computation pattern** — Phase 1 (instant: degree, density, topo sort) then Phase 2 (500ms timeout: PageRank, betweenness, etc.) with `status` field indicating `approx`/`skipped` for large graphs. Good model for Autarch's background analytics worker.
- **`--robot-docs` machine-readable docs** — `bv --robot-docs all` returns JSON docs for every robot command. Autarch could offer the same for its MCP tools.
- **Content hash caching** — `data_hash` field in every robot output enables agents to skip reprocessing unchanged data. Apply to Autarch's MCP server cache layer.
- **TOON (token-optimized output)** — bv integrates `toon-go` for compact token output. Autarch's MCP server could offer `--format toon` for agent-facing endpoints.
- **Tutorial system** (`pkg/ui/tutorial.go`) — Interactive onboarding inside TUI. Relevant for Autarch's onboarding flow.
- **AGENT_FRIENDLINESS_REPORT.md pattern** — Periodic structured audit of agent-facing CLI ergonomics. Worth adopting as a Demarch doc convention.

**Verdict:** port-partially

**Rationale:** The robot-mode CLI works against Demarch's `.beads/issues.jsonl` today with zero changes; the Go graph analysis packages (`pkg/analysis/`, `pkg/drift/`, `pkg/recipe/`) are production-ready and directly portable to Autarch's Go codebase, filling a critical gap in Autarch's beads intelligence layer.

---

## beads_viewer-pages (iv-ool7q)

**What it is:** A fully self-contained, offline-capable static web dashboard for a beads project: SQL.js (WASM SQLite) for query, force-graph (D3-based) for dependency DAG visualization, Chart.js for analytics, Alpine.js for reactivity, Tailwind for styling, vendored fonts — all served as flat files from GitHub Pages.

**Language/Stack:** Vanilla JavaScript (ES2020+), SQL.js (SQLite WASM), D3 / force-graph, Chart.js, Alpine.js, Tailwind CSS. No build step. Fully vendored for offline use (CSP: `default-src 'self'`). 10,542 lines across viewer.js (3,472), graph.js (3,847), charts.js (761), styles.css (2,374), hybrid_scorer.js (88).

**Quality:** High. Well-structured with explicit module headers, JSDoc, DIAGNOSTICS state machine, WASM memory management via `withSubgraph()` RAII pattern, OPFS caching, chunk-reassembly for large DBs, graceful fallback to pre-computed static JSON when WASM unavailable. The hybrid scorer (`hybrid_scorer.js`) mirrors a Go implementation and has an inline test runner (`hybrid_scorer.test.js`). Dracula-palette theme is consistent across all modules.

**Relevance to Demarch:** Autarch's Bigend already has a web server (`internal/bigend/web/`) with Go HTML templates. beads_viewer-pages provides a production-quality, zero-dependency frontend for exactly the dependency graph and analytics views that Bigend's web dashboard currently lacks.

**Integration opportunities:**

- **`graph.js` + force-graph WASM** — Production dependency graph visualization with multi-metric coloring (status, priority, PageRank, betweenness), critical path highlighting (gold glow), cycle detection (pink edges), pan/zoom, click-to-focus, filter panel, accessibility labels. This is the hardest component to build from scratch; adopt it directly.
- **`viewer.js` SQL.js pattern** — Client-side SQLite querying via WASM with OPFS caching and chunk-reassembly. Demarch's `.beads/beads.db` is already a SQLite file; ship it alongside the static page and the viewer queries it directly with FTS5 search. No server API needed for read-only views.
- **`charts.js`** — Burndown/burnup chart, label dependency heatmap, priority distribution pie, type breakdown bar. All Chart.js, all self-contained. Direct drop-in for Bigend's analytics tab.
- **`hybrid_scorer.js` HybridScorer** — Client-side graph-aware search ranking with configurable presets (default, bug-hunting, sprint-planning, impact-first, text-only). Port the preset system to Bigend's search UX.
- **Static JSON data protocol** — `data/meta.json`, `data/triage.json`, `data/project_health.json`, `data/graph_layout.json`, `data/history.json` as generated artifacts from `bv --robot-*`. Bigend could generate these as part of its build/export pipeline and serve them alongside the static viewer. The schema is stable (matches bv TriageResult).
- **WASM fallback pattern** — WASM_STATUS state machine with graceful fallback to pre-computed data. Apply to any WASM integration in Autarch.
- **Mobile-first responsive design** — PWA meta tags, viewport fit cover, apple-mobile-web-app-capable, dark mode with localStorage persistence, early flash prevention. The CSS/HTML patterns are directly reusable.

**Inspiration opportunities:**

- **Fully offline-capable dashboard** — No CDN, no API calls, fully vendored. This is a design constraint worth adopting for Bigend's "export dashboard" feature — ship everything needed to view the project offline.
- **CSP: self-contained security model** — The strict Content-Security-Policy (`default-src 'self'`) enforces zero external dependencies. Adopt for Autarch's exported reports.
- **`DIAGNOSTICS` state machine pattern** — Tracks wasm status, db source, load time, query count, query errors. Useful pattern for Autarch's MCP server health reporting.
- **OPFS caching for SQLite** — Browser-native file system API for caching large SQLite databases avoids network re-fetches on page reload. Worth adopting in any browser-side tool Autarch ships.

**Verdict:** port-partially

**Rationale:** `graph.js` and `viewer.js` are production-ready components that directly solve Autarch's unbuilt dependency graph visualization and SQL-backed issue search; adopting them avoids months of frontend work and the static JSON protocol integrates cleanly with bv's existing `--robot-*` output.

---

## beads_viewer_for_agentic_coding_flywheel_setup (iv-hol58)

**What it is:** A minimal demonstration deployment of beads_viewer-pages configured for a 3-issue "Agent Flywheel" project, published to GitHub Pages.

**Language/Stack:** Identical to beads_viewer-pages — vanilla JS, SQL.js WASM, force-graph, Chart.js, Alpine.js, Tailwind. No build step. The only file-level differences from beads_viewer-pages are: `index.html` title (`Agent Flywheel Beads Viewer` vs `Beads Viewer Issues`), `data/` contains different JSON payloads (3 issues vs 487), and `graph-demo.html` is an additional standalone graph demo file (absent in beads_viewer-pages). `viewer.js`, `graph.js`, `charts.js`, `hybrid_scorer.js` are byte-identical.

**Quality:** Low-medium as a standalone artifact. The 3 test issues have no meaningful dependencies and the data dir has no `history.json` (only triage, meta, project_health, graph_layout). This is a template/scaffold repository, not a feature repo. The additional `graph-demo.html` is standalone Dracula-themed graph demo using force-graph directly — a useful isolated test harness.

**Relevance to Demarch:** This repo demonstrates the minimal setup needed to bootstrap a new project's beads web dashboard — useful as a starting template but not as an integration source since beads_viewer-pages contains all the same code with a richer data set.

**Integration opportunities:**

- **`graph-demo.html`** — A standalone ~300-line graph demo page that exercises force-graph with the Dracula palette and basic issue data. Useful as an isolated test harness when iterating on graph.js customizations for Autarch.
- **Template for new project dashboards** — The data/ directory structure (4 JSON files from bv robot commands) and the flat file layout serve as a reference for how to scaffold a new beads project dashboard quickly.
- **`hybrid_scorer.test.js`** — An inline self-test runner for HybridScorer (absent in beads_viewer-pages). Useful to carry along when porting the scorer.

**Inspiration opportunities:**

- **Minimal scaffold pattern** — The repo demonstrates what the smallest viable beads web dashboard deployment looks like: 4 JSON data files + 5 JS modules + 1 HTML file + vendored dependencies. Autarch's "export project dashboard" feature could target this minimal structure.
- **GitHub Pages deployment pattern** — Static assets committed directly to repo root, served via Pages. Simple model for Autarch's "publish dashboard" capability without requiring a server.

**Verdict:** inspire-only

**Rationale:** The JavaScript code is byte-identical to beads_viewer-pages which should be the actual integration source; this repo's only unique contribution is `graph-demo.html` (useful test harness) and the minimal 3-issue data scaffold as a template.

---

## Cross-Cutting Observations

### Compatibility with Demarch's .beads format

All three repos are built around the same beads format that Demarch uses. The loader in beads_viewer explicitly lists `issues.jsonl` as a supported filename (`PreferredJSONLNames = []string{"beads.jsonl", "issues.jsonl", "beads.base.jsonl"}`), meaning `bv` can run against Demarch's `.beads/` directory today without modification.

Demarch's issue format (`id`, `title`, `description`, `status`, `priority`, `issue_type`, `labels`, `dependencies`, `created_at`, `updated_at`, `closed_at`) maps directly to `pkg/model/types.go`'s `Issue` struct.

### Recommended Integration Sequence

1. **Now (zero code):** Run `bv --robot-triage` against Demarch's `.beads/` to get graph-aware triage. Install via `brew install dicklesworthstone/tap/bv`.
2. **Short-term (Autarch TUI):** Port `pkg/analysis/triage.go` TriageResult computation and `pkg/drift/` alert types into Autarch's Bigend. Add a beads triage panel to Bigend's TUI model.
3. **Medium-term (Autarch web):** Integrate `graph.js` + `viewer.js` into Bigend's web server (`internal/bigend/web/`) as a beads analytics tab. Use bv to generate static JSON data files and serve them alongside the templated HTML.
4. **Long-term (Autarch pipeline):** Generate the static beads dashboard as a CI artifact on every push via `bv --robot-triage > data/triage.json && bv --robot-graph > data/graph_layout.json` etc.

### Data Format Note

beads_viewer-pages uses a `beads.sqlite3` at repo root (not in `data/`) as its primary data source; the `data/` JSON files are pre-computed fallbacks. The SQLite DB is generated by `bd sync` or `bd export`. Demarch's `.beads/beads.db` is the same SQLite file — the viewer can query it directly via the SQL.js WASM frontend.

### Scoring Note

The high scores (98, 96, 97) appear to be interverse-internal scoring from an automated discovery pipeline. They correlate with actual quality: beads_viewer is genuinely excellent, beads_viewer-pages is solid, and beads_viewer_for_agentic_coding_flywheel_setup is a scaffold template. The scores appropriately rank them.
