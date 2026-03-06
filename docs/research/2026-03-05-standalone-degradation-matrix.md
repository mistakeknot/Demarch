---
artifact_type: research
bead: iv-lpfin
stage: discover
---

# Standalone Degradation Matrix for Interverse Plugins

**Bead:** iv-lpfin
**Date:** 2026-03-05
**Status:** Ground-truth audit complete

## Context

PHILOSOPHY.md defines two plugin tiers: **standalone** (default, degrade gracefully) and **kernel-native** (may require intercore). This document audits the actual degradation behavior of all 51 Interverse plugins across four dependency axes, identifies where reality diverges from the architecture's claims, and recommends fixes.

## Dependency Axes

| Axis | Present | Absent |
|------|---------|--------|
| **Intercore** (`ic` CLI) | Full kernel integration: events, state, discovery, runs | Plugin must handle `FileNotFoundError` / `command -v ic` failure |
| **Clavain** (OS layer) | Sprint lifecycle, skills, agents, hooks | Plugin operates as standalone MCP server or CLI tool |
| **Beads** (`bd` CLI) | Issue tracking, phase state, priority queries | Plugin must skip bead-dependent features |
| **External APIs** | Full source coverage (Exa, Notion, Slack) | Reduced source coverage, local-only fallback |

## Tier Classification

### Kernel-Native Plugins (3)

These plugins' core value IS the kernel integration. PHILOSOPHY.md correctly identifies them.

| Plugin | ic | bd | Clavain | Degrades without ic? | Gaps |
|--------|----|----|---------|---------------------|------|
| **interject** | Required | Optional | N | Scans work, but discoveries don't reach kernel records or trigger events. Output pipeline creates beads but `_submit_to_kernel` silently fails. | Correct: catches `FileNotFoundError` in outputs.py |
| **interspect** | Required | N | Companion | Evidence pipeline, review events, and routing optimization all need `ic events` and `ic state`. Without ic, interspect is a shell with no data. | Correct: commands reference `ic events list-review`, `ic state get/set` |
| **interphase** | N | Required | Companion | Phase tracking and gate validation depend on `bd` for state persistence. Without beads, all phase operations are no-ops. | Correct: lib-phase.sh guards on `command -v bd` |

### Clavain Companions (10)

These extend Clavain's workflow but have value as standalone MCP servers or skills.

| Plugin | ic | bd | Degrades without Clavain? | Fallback behavior |
|--------|----|----|--------------------------|-------------------|
| **interflux** | N | Optional | Yes — agents and skills work standalone. Flux-drive needs a Clavain plan file as input but agents are generic reviewers. | Agents produce verdicts independently. Knowledge from interknow still searchable. |
| **interpath** | N | Optional | Partially — artifact generation skills reference Clavain phase transitions. Roadmap/PRD/changelog skills work with any markdown docs. | Skills produce docs but skip phase-advance calls. |
| **interlock** | N | N | Yes — file reservation via intermute MCP works without Clavain. Skills add coordination protocol but MCP tools are self-contained. | 20 MCP tools all function. Skills guide agents but aren't required. |
| **intercraft** | N | N | Partially — agent-native audit skill references Clavain patterns. MCP tools are generic code structure tools. | Audit works but references Clavain-specific conventions. |
| **interline** | N | Optional | Partially — statusline reads from Clavain sideband files. Without Clavain, bead layer shows nothing, phase layer is empty. | Displays available layers only. `bead_query` layer disabled if `bd` absent. |
| **intersynth** | N | N | Yes — synthesis agents read output files and produce verdicts. Works with any multi-agent output, not just Clavain's. | Fully functional as standalone synthesis engine. |
| **interwatch** | N | Optional | Partially — doc-watch skill references Clavain `/status`. Core drift detection is standalone. | Drift scanning works. Status reporting degrades. |
| **interscribe** | N | N | Yes — documentation authoring is generic. | Fully standalone. |
| **interdev** | N | N | Yes — MCP CLI and Claude Code reference are generic dev tools. | Fully standalone. |
| **interspect** | Required | N | No — deeply coupled to Clavain's review pipeline via `ic events`. Listed here AND in kernel-native. | See kernel-native section above. |

### Standalone Plugins with Optional Dependencies (12)

These work independently but gain features with dependencies present.

| Plugin | Optional deps | What breaks without them | Fallback quality |
|--------|--------------|--------------------------|-----------------|
| **interstat** | bd (reads bead_id for attribution) | Token costs aren't attributed to beads. Core metrics still recorded. | Good — metrics work, attribution is bonus |
| **intermem** | bd (snapshot tracking) | Memory synthesis works. Bead-linked snapshot tracking disabled. | Good — core value preserved |
| **interkasten** | Notion token, bd | Without Notion: daemon runs, MCP tools work locally. Without bd: no bead sync. | Good — layered degradation |
| **interleave** | bd (bead queries for roadmaps) | Roadmap templates can't query bead state. Static templates still work. | Moderate — reduces usefulness |
| **intersearch** | Exa API key | Without Exa: embedding infrastructure still works (nomic-embed-text-v1.5 is local). Web search disabled. | Good — embeddings are the core |
| **interject** | Exa API key, bd | Without Exa: arXiv/HN/GitHub adapters still work. Without bd: beads not created, output pipeline silently degrades. | Good — graceful per-dependency |
| **interflux** | Exa API key | Without Exa: falls back to WebSearch. Research agents less capable but functional. | Good — explicit fallback |
| **interknow** | qmd binary | Without qmd: knowledge compounding works but semantic search over solutions is disabled. | Good — write path unaffected |
| **interpeer** | Oracle (browser-mode) | Without Oracle: peer review still works via Claude↔Codex exchange. Deep analysis mode unavailable. | Good — core feature preserved |
| **interslack** | Slack credentials | Without Slack creds: MCP server starts but all tools return errors. | Poor — no graceful message |
| **intercache** | None optional | Fully self-contained content-addressed cache. | Perfect — zero dependencies |
| **intermap** | None optional | Go MCP server + Python analysis are self-contained. | Perfect — zero dependencies |

### Fully Standalone Plugins (26)

These have no meaningful external dependencies beyond being Claude Code plugins. They are MCP servers with self-contained functionality.

`interchart`, `intercheck`, `interdeep`, `interdoc`, `interfluence`, `interform`, `interlens`, `intermonk`, `intermux`, `intername`, `internext`, `interplug`, `interpub`, `interpulse`, `interrank`, `interserve`, `intership`, `intersense`, `interskill`, `intertest`, `intertrace`, `intertrack`, `intertree`, `intertrust`, `tldr-swinton`, `tool-time`, `tuivision`

## Gap Analysis

### High-Priority Gaps (reality diverges from claim)

| Gap | Severity | Plugin | Issue | Fix |
|-----|----------|--------|-------|-----|
| G1 | **High** | interslack | No graceful degradation when Slack credentials missing. MCP server starts but every tool call fails with raw error. | Add credential check at server init; return human-readable "Slack not configured" message. |
| G2 | **Medium** | interline | Claims standalone but statusline is nearly empty without Clavain+beads. Three core layers (bead, phase, sprint signals) produce nothing. | Document that interline's primary value requires Clavain. Consider reclassifying as companion. |
| G3 | **Medium** | interleave | Roadmap templates call `bd` without guarding. If beads absent, templates may error. | Add `command -v bd` guard before bead queries. |

### Correctly Degrading (aspirations match reality)

| Pattern | Plugins | Mechanism |
|---------|---------|-----------|
| `FileNotFoundError` catch on subprocess | interject (outputs.py) | `except FileNotFoundError: logger.warning(...)` |
| `command -v bd` guard in bash | interphase (lib-phase.sh, lib-discovery.sh) | `if ! command -v bd &>/dev/null; then return 0; fi` |
| Optional API key check | intersearch, interflux | Config-level check, feature gating |
| Sideband file fallback | interline | Checks multiple paths, shows available data only |
| MCP tool isolation | interlock, intermap, tldr-swinton | Each tool handles its own errors |

### Architecture Observations

1. **The "all plugins have MCP servers" pattern is the key standalone enabler.** MCP tools are inherently isolated — each tool call handles its own errors. A plugin with 10 tools and 3 broken (due to missing deps) still provides 7 working tools.

2. **Clavain companions are NOT broken without Clavain** — they're just less useful. The MCP tools work; the skills and agents degrade. This is correct behavior but should be documented.

3. **Beads is the most common optional dependency** (11 plugins). The `command -v bd` guard is well-established. No plugin hard-fails without beads except interphase (which is kernel-native).

4. **Intercore is NOT a universal dependency.** The agent's scan showed "Y" for all plugins, but this is misleading — most plugins don't call `ic` directly. The "intercore dependency" is the plugin infrastructure itself (Claude Code's plugin loading), not explicit `ic` CLI calls. True `ic` callers: interject (outputs.py), interspect (hooks/lib-interspect.sh), interphase (indirectly via intercore state).

## Recommended Actions

1. **Fix G1 (interslack):** Add credential check at MCP server initialization. Return structured error: `{"error": "Slack not configured. Set SLACK_BOT_TOKEN."}` instead of raw exception.

2. **Fix G2 (interline):** Add note to CLAUDE.md: "Primary value requires Clavain and beads. Without them, statusline shows only basic session info." Not a reclassification — interline genuinely works standalone, just with reduced layers.

3. **Fix G3 (interleave):** Add `command -v bd` guard before bead queries in roadmap templates.

4. **Update PHILOSOPHY.md examples:** The standalone tier lists `interlock` as an example, which is correct — it does degrade gracefully. But it should also mention a non-companion standalone (e.g., `intercache` or `intermap`) to show the full spectrum.

5. **Add `/doctor` checks:** `clavain:doctor` should verify that kernel-native plugins have their dependencies installed. Currently it checks MCP servers but not `ic`/`bd` availability.

## Summary Matrix (Compact)

```
                    ic absent    bd absent    Clavain absent    External absent
Kernel-native(3)    BROKEN       varies       varies            N/A
Companions(10)      OK           varies       REDUCED           varies
Optional-dep(12)    OK           REDUCED      OK                REDUCED
Standalone(26)      OK           OK           OK                OK
```

BROKEN = core functionality unavailable
REDUCED = some features disabled, core works
OK = no impact
