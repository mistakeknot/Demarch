# PRD: Plugin Synergy — Cross-Plugin Interop Improvements
**Bead:** iv-vlg4

## Problem

The Interverse has 31 plugins that largely operate in isolation. Analytics plugins (intercheck, interstat, tool-time) collect data that no other plugin consumes. Three plugins independently detect staleness. Only 1 of 31 plugins uses the interbase SDK. These disconnections mean lost opportunities for ambient intelligence, automated feedback loops, and ecosystem health.

## Solution

Wire existing plugins together through interband signals, shared libraries, and interbase SDK adoption. This creates feedback loops (analytics → decisions), ambient awareness (pressure/coordination → statusline), and unified infrastructure (staleness detection, companion discovery).

## Features

### F1: Interband Signal Publishers
**What:** Add interband channel writes to intercheck (context pressure), interstat (budget alerts), and interlock (coordination state) so other plugins can consume their data.
**Acceptance criteria:**
- [ ] intercheck writes pressure level (green/yellow/orange/red) to `~/.interband/intercheck/pressure` after each PostToolUse evaluation
- [ ] interstat writes budget alert (percentage consumed) to `~/.interband/interstat/budget` when sprint token spend crosses 50%, 80%, 95% thresholds
- [ ] interlock already writes to `~/.interband/interlock/coordination` — verify format is documented
- [ ] Each signal uses atomic write (temp+mv) and includes timestamp + session ID
- [ ] Signals are fire-and-forget — publisher never blocks on consumer availability

### F2: Interline Statusline Enrichment
**What:** interline reads new interband channels and renders context pressure, coordination state, and budget alerts in the statusline.
**Acceptance criteria:**
- [ ] Statusline shows pressure indicator when intercheck signal exists: green dot (default), yellow/orange/red with color
- [ ] Statusline shows coordination state when interlock signal exists: "2 agents" or "conflict"
- [ ] Statusline shows budget warning when interstat signal exists: "87% budget" in orange/red
- [ ] Each indicator is independently toggleable via `~/.claude/interline.json` config
- [ ] Missing signals are silently ignored — no errors when companion plugins aren't installed
- [ ] No measurable latency increase (signals are file reads, not subprocess calls)

### F3: Interbase Batch Adoption
**What:** Adopt the interbase SDK stub in 6 high-value plugins: interline, intersynth, intermem, intertest, internext, tool-time.
**Acceptance criteria:**
- [ ] Each plugin has `hooks/interbase-stub.sh` copied from `sdk/interbase/templates/`
- [ ] Each plugin has `.claude-plugin/integration.json` with companion declarations
- [ ] Each plugin's session-start hook sources the stub
- [ ] `ib_nudge_companion()` calls added where cross-plugin value exists (e.g., interline nudges "install intercheck for pressure display")
- [ ] All 6 plugins pass `bash sdk/interbase/tests/test-guards.sh` in standalone mode (stubs are no-ops)
- [ ] Nudge budget respected: max 2 nudges per session across all plugins

### F4: Unified Staleness Library
**What:** Extract shared staleness scoring logic from interwatch, intermem, and interdoc into a reusable library. Each plugin keeps domain-specific models but delegates core scoring.
**Acceptance criteria:**
- [ ] Library provides `staleness_score(filepath)` returning 0-100 freshness score
- [ ] Library provides `staleness_notify(filepath, score)` writing to interband `staleness/changed`
- [ ] interwatch uses shared scoring instead of its own hash comparison
- [ ] intermem uses shared scoring for citation freshness (feeds into confidence penalty)
- [ ] interdoc uses shared scoring for drift detection threshold
- [ ] Library lives in `sdk/interbase/lib/staleness.sh` or a new `lib/staleness/` directory
- [ ] Each plugin's existing tests still pass after migration

### F5: Verdict-to-Bead Bridge
**What:** After flux-drive synthesis, auto-create beads for P0/P1 findings that aren't in the current sprint scope.
**Acceptance criteria:**
- [ ] intersynth's synthesis step checks verdict severity after `verdict_parse_all`
- [ ] P0/P1 findings without an existing matching bead get auto-created via `bd create`
- [ ] Created beads include verdict metadata: source agent, file path, finding summary
- [ ] Dedup check: `bd list | grep <keyword>` before creating to avoid duplicates
- [ ] Auto-created beads are P1 priority with type=bug for P0 findings, type=task for P1
- [ ] Feature is opt-in via `INTERSYNTH_AUTO_BEAD=true` environment variable

### F6: Cost-Aware Review Depth
**What:** Make interflux's `FLUX_BUDGET_REMAINING` env var always-on instead of sprint-only, and have interstat automatically set it.
**Acceptance criteria:**
- [ ] interstat writes remaining budget to interband `interstat/budget` (from F1)
- [ ] interflux's session-start hook reads `interstat/budget` and sets `FLUX_BUDGET_REMAINING` if present
- [ ] flux-drive's agent triage respects budget: fewer agents dispatched at <30% remaining
- [ ] Works without interstat installed (env var unset = unlimited budget)
- [ ] Override available: `FLUX_BUDGET_OVERRIDE=unlimited` disables budget-aware triage

### F7: Companion Plugin Dependency Graph
**What:** Machine-readable graph of which plugins enhance which others, consumed by `/clavain:doctor` for install guidance.
**Acceptance criteria:**
- [ ] `companion-graph.json` at Interverse root lists edges with { from, to, relationship, benefit }
- [ ] `/clavain:doctor` reads the graph and reports: "You have X but not Y — Z won't work"
- [ ] Graph includes all companion relationships identified in the brainstorm (12+ edges)
- [ ] Validation script checks graph against actual plugin directories (no stale entries)
- [ ] Graph is human-readable (formatted JSON with comments explaining each relationship)

### F8: Smart Checkpoint Triggers
**What:** When intercheck hits Orange context pressure AND intermem has unprocessed auto-memory entries, trigger intermem synthesis before context compaction.
**Acceptance criteria:**
- [ ] intercheck's pressure evaluation checks for pending intermem entries at Orange threshold
- [ ] If entries exist, intercheck emits interband signal `intercheck/checkpoint-needed`
- [ ] intermem's PostToolUse hook reads the signal and runs lightweight synthesis
- [ ] Synthesis runs in-band (not as a subagent) to avoid adding context pressure
- [ ] If intermem isn't installed, intercheck still functions normally (fail-open)
- [ ] Checkpoint trigger is rate-limited: max once per 15 minutes

## Non-goals

- **New MCP servers** — all integration happens through interband signals, library imports, and env vars
- **Breaking changes** — all features are additive; plugins work standalone without companions
- **UI/TUI components** — statusline changes are text-only, no interactive elements
- **Automated remediation** — signals trigger awareness and suggestions, not auto-fixes (except F5 bead creation which is opt-in)

## Dependencies

- interband protocol (already exists, documented in interphase)
- interbase SDK v1 (already exists at `sdk/interbase/`)
- beads CLI (`bd`) for F5 and F7
- interflux verdict system for F5
- Claude Code hook system for all features

## Open Questions

1. Should the unified staleness library (F4) live in interbase or as a separate shared lib?
2. Should F5 (verdict-to-bead) create beads immediately or queue them for user review?
3. What's the right threshold for F8 checkpoint triggers — Orange or Red pressure?
4. Should F7's companion graph also include "conflicts with" edges (plugins that shouldn't coexist)?
