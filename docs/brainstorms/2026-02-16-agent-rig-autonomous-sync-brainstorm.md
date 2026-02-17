# Agent-Rig Autonomous Sync

**Date:** 2026-02-16
**Bead:** iv-m8kb
**Status:** Design complete

## What We're Building

A fully autonomous system that keeps Clavain's installer manifests (`agent-rig.json`, `setup.md`, `doctor.md`) in sync with the actual Interverse plugin ecosystem, so that `/clavain:setup` always installs the complete rig with one command.

## The Problem

The Interverse has grown from ~10 plugins to 25+ but the installer manifests haven't kept up:

- **agent-rig.json** lists 17 plugins. The ecosystem has 25+ in the marketplace.
- **interflux** (the review engine powering `/flux-drive`) is completely absent from both `agent-rig.json` and `setup.md`.
- **setup.md** and **agent-rig.json** disagree on what to install (setup has interphase/interline/interpath/interwatch/interlock; agent-rig doesn't).
- **doctor.md** only checks 5 companions but the rig depends on 10+.
- New plugins (interject, intercheck, interstat, internext, etc.) were published to the marketplace but never added to the installer.
- `interclode` and `auracoil` are in agent-rig.json but may not exist in the monorepo (need verification).

## Why This Approach

### Approach: Generated + Self-Healing Hybrid

**agent-rig.json is the single source of truth.** A generator script produces the plugin lists in `setup.md` and `doctor.md` from agent-rig.json. If the generated lists ever drift (someone edits agent-rig.json but forgets to regenerate), setup.md includes a self-heal instruction that tells Claude Code to re-derive from agent-rig.json at runtime.

**Why not pure runtime?** (setup.md just says "read agent-rig.json")
- Token cost on every `/setup` run
- Less human-readable — can't audit the install list by reading the file
- Non-deterministic — relies on Claude Code interpreting instructions consistently

**Why not pure generation?** (no runtime fallback)
- Fragile — drift is silent and undetected until someone runs `/setup` and gets a stale list

**Hybrid gets both:**
- Static lists are human-readable, zero-cost, auditable via git diff
- Self-heal catches drift automatically without a separate CI check
- Generator runs in Clavain's post-bump hook (already exists for gen-catalog)

### Trigger: Clavain's post-bump.sh

The generator runs every time Clavain is version-bumped via `interbump.sh`. This is the natural moment to snapshot the ecosystem because:
- Clavain is bumped more frequently than individual plugins
- It's already the integration point (post-bump.sh runs gen-catalog)
- Version bumps happen before publish, so the generated lists are committed with the release

### Curation: Clavain decides, drift detector warns

Plugins don't opt themselves into agent-rig.json. The tier assignments (required/recommended/optional) are curated by Clavain's maintainer. A drift detector warns when marketplace plugins exist that aren't in any tier, so new plugins don't get silently forgotten.

## Key Decisions

1. **agent-rig.json gains an `optional` tier** — for plugins that are useful but not part of the core experience (interpub, interlens, interstat, etc.)
2. **Generator script** (`scripts/gen-agent-rig-docs.sh` or Python) reads agent-rig.json and writes plugin lists into setup.md and doctor.md
3. **Marker format** — use fenced markers in setup.md/doctor.md that Claude Code can parse:
   ```
   <!-- agent-rig:begin:recommended -->
   (generated plugin install commands)
   <!-- agent-rig:end:recommended -->
   ```
4. **Self-heal instruction** — setup.md includes a preamble: "If the lists below appear stale or incomplete, read `agent-rig.json` directly and derive the install commands from the `plugins` object."
5. **Drift detector** — the generator also checks `infra/marketplace/marketplace.json` for plugins not in any agent-rig.json tier and emits warnings
6. **Verification script** in setup.md is also generated — the Python `required` and `conflicts` sets come from agent-rig.json, not hand-maintained
7. **post-bump.sh integration** — Clavain's existing post-bump hook calls the generator after gen-catalog

## Architecture

```
agent-rig.json (source of truth)
    │
    ├─▶ scripts/gen-agent-rig-docs.sh (generator)
    │       │
    │       ├─▶ commands/setup.md (plugin lists between markers)
    │       ├─▶ commands/doctor.md (companion checks between markers)
    │       └─▶ WARNINGS if marketplace has uncurated plugins
    │
    ├─▶ setup.md self-heal (runtime fallback)
    │       "If lists look stale, read agent-rig.json directly"
    │
    └─▶ marketplace.json (drift comparison target)

Trigger: scripts/post-bump.sh → calls gen-agent-rig-docs.sh
```

## Tier Classification (Proposed)

### Required (must have for Clavain to function)
- context7 (MCP docs)
- explanatory-output-style (output formatting)

### Recommended (core Clavain experience)
- interdoc (AGENTS.md generation)
- interflux (review engine — flux-drive, flux-research)
- interphase (phase tracking, gates, discovery)
- interline (statusline renderer)
- interpath (product artifact generation)
- interwatch (doc freshness monitoring)
- interlock (multi-agent coordination)
- intercheck (code quality guards)
- tldr-swinton (token-efficient code context)
- tool-time (tool usage analytics)
- interslack (Slack integration)
- interform (design patterns)
- intercraft (agent-native architecture)
- interdev (MCP CLI tooling)
- serena (semantic coding tools)
- plugin-dev (plugin development)
- agent-sdk-dev (Agent SDK)
- security-guidance (security best practices)

### Optional (useful extensions, ask user)
- interfluence (voice profiles)
- interject (ambient research)
- internext (work prioritization)
- interstat (token analytics)
- interkasten (Notion sync)
- interlens (cognitive lenses)
- intersearch (shared embeddings)
- interserve (Codex classifier)
- interpub (plugin publishing)
- tuivision (TUI testing)
- intermux (terminal multiplexing)

### Infrastructure (language-specific, ask user)
- gopls-lsp, pyright-lsp, typescript-lsp, rust-analyzer-lsp

### To Verify
- auracoil — in agent-rig.json recommended, not in Interverse plugins/. External? Deprecated?
- interclode — in agent-rig.json recommended, not in Interverse plugins/. External? Deprecated?

## Open Questions

1. Should the self-heal instruction be a separate skill that setup.md loads, or inline in the command?
2. Should doctor.md also gain optional-tier checks, or only recommended+required?
3. Should the drift detector fail the bump (exit non-zero) or just warn?

## Implementation Steps

1. Verify auracoil and interclode status — remove or document
2. Add `optional` tier to agent-rig.json schema
3. Populate all tiers with current ecosystem plugins
4. Write `scripts/gen-agent-rig-docs.sh` generator
5. Add markers to setup.md and doctor.md
6. Run generator to populate initial lists
7. Add self-heal preamble to setup.md
8. Integrate into post-bump.sh
9. Add marketplace drift detection
10. Test full cycle: bump → generate → verify setup works
