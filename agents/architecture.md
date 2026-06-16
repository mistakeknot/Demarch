# Architecture

## Overview

Sylveste is the physical monorepo for the open-source autonomous software development agency platform. It contains six pillars: **Intercore** (`/core`) the orchestration kernel, **Clavain** (`/os/Clavain`) the agent OS and reference agency, **Skaffen** (`/os/Skaffen`) the sovereign agent runtime, **Interverse** (`/interverse`) the companion plugin ecosystem, **Autarch** (`/apps`) the TUI surfaces, and **Interspect** (cross-cutting profiler, currently in Interverse). Plus `sdk/` for shared libraries (interbase). Each module keeps its own `.git` as a nested independent repo. The root `Sylveste/` also has a `.git` for the monorepo skeleton (scripts, docs, CLAUDE.md). Git operations apply to the nearest `.git`; verify with `git rev-parse --show-toplevel`.

## Glossary

| Term | Meaning |
|------|---------|
| **Pillar** | One of the 6 top-level components of Sylveste: Intercore, Clavain, Skaffen, Interverse, Autarch, Interspect. Organizational term — use "layer" (L1/L2/L3) for architectural dependency. |
| **Layer** | Architectural dependency level: L1 (Kernel/Intercore), L2 (OS/Clavain + Drivers/Interverse), L3 (Apps/Autarch). Interspect is cross-cutting. |
| **Beads** | File-based issue tracker (`bd` CLI). Each project can have a `.beads/` database. All active tracking is at Sylveste root. |
| **Plugin** | A Claude Code extension (skills, commands, hooks, agents, MCP servers) installed from the marketplace. |
| **MCP** | Model Context Protocol — enables plugins to expose tools as server processes that Claude Code calls directly. |
| **Driver** | A companion plugin (part of the Interverse pillar) that extends Clavain with one capability. Also called "companion plugin." |
| **Marketplace** | The `interagency-marketplace` registry at `core/marketplace/` — JSON catalog of all published plugins. |
| **Skaffen** | Sovereign agent runtime — standalone Go binary with OODARC agent loop, multi-provider support, and TUI (via masaq). L2, peers with Clavain. |
| **Interspect** | Adaptive profiler pillar — reads kernel event surfaces, proposes OS configuration changes. Cross-cutting (not a layer). Current measurement caveats are documented in `docs/research/interspect-event-validity-and-outcome-attribution.md`. Skill calibration (extends the existing agent-routing loop to `source_kind='skill'`) is in design — see `docs/plans/2026-06-16-interspect-skill-calibration.md`. |

## Directory Layout

Each subproject has its own CLAUDE.md and AGENTS.md — read those before editing. Use `ls apps/ core/ interverse/ os/ sdk/` to discover modules.

| Path | Pillar | Notes |
|------|--------|-------|
| `apps/Autarch/` | Autarch | TUI interfaces (Bigend, Gurgeh, Coldwine, Pollard) |
| `apps/Intercom/` | Autarch | Multi-runtime AI assistant (Claude, Gemini, Codex) |
| `os/Clavain/` | Clavain | Autonomous software agency (L2 OS) |
| `os/Skaffen/` | Skaffen | Sovereign agent runtime (L2 OS) |
| `os/Zaka/` | Zaka | Universal CLI agent driver — tmux steering (L2 OS) |
| `os/Alwe/` | Alwe | Universal agent observation layer — CASS + MCP (L2 OS) |
| `os/Ockham/` | Ockham | Factory governor — intent, authority, anomaly, dispatch (L2 OS) |
| `core/intercore/` | Intercore | Orchestration kernel — Go CLI `ic` (L1) |
| `core/intermute/` | Intercore | Multi-agent coordination service (Go) |
| `core/marketplace/` | Intercore | Plugin marketplace registry |
| `core/agent-rig/` | Intercore | Agent rig configuration (TypeScript/Node) |
| `core/interband/` | Intercore | Sideband communication protocol (Go) |
| `core/interbench/` | Intercore | Plugin benchmarking harness (Go) |
| `interverse/` | Interverse | Companion plugins — each has own docs; count plugin manifests with `find interverse -maxdepth 3 -path '*/.claude-plugin/plugin.json' \| wc -l` |
| `sdk/interbase/` | — | Shared integration SDK (Bash/Go/Python) |
| `masaq/` | — | Shared Bubble Tea component library (Go) — themes, keys, viewport, priompt |
| `docs/` | — | Platform-level docs only (brainstorms, research, solutions) |

> **Docs convention:** `Sylveste/docs/` is for platform-level work only. Each subproject keeps its own docs.
> **Artifact naming:** See [`CONVENTIONS.md`](../CONVENTIONS.md) for canonical paths.

## Key Dependency Chains

```
Clavain (L2) → interlock → intermute (L1)    # file coordination
Clavain (L2) → interflux → intersearch        # multi-agent review
Clavain (L2) → interwatch → interpath/interdoc # doc freshness → generator dispatch
interject → intersearch                        # ambient discovery
interdeep → interject                          # deep research extraction + search
Clavain (L2) → intertrust                     # agent trust scoring
interpulse → interband → interline/intermem   # context pressure → statusline/memory
Clavain (L2) → interphase                     # phase tracking, gates, discovery
Skaffen (L2) → masaq                          # TUI components, themes
Skaffen (L2) → intercore (L1)                 # provider/tool system via Intercore bridge
Skaffen (L2) → Zaka (L2)                      # tmux agent steering
Skaffen (L2) → Alwe (L2)                      # CASS observation
Zaka (L2) + Alwe (L2) = Zakalwe               # two halves: steer + observe
Ockham (L2) → Clavain dispatch scoring          # intent → dispatch weights
Ockham (L2) → Alwe                              # anomaly detection queries
Meadowsyn (L3) → Ockham (L2)                   # UI → governor
interlab → interlock                           # delta sharing — mutation broadcast across sessions
```

Standalone plugins (no cross-deps): intercache, interchart, intercheck, intercraft, interdev, interfluence, interform, interhelm, interkasten, interknow, interlearn, interleave, interlens, intermap, intermix, intermonk, intermux, intername, internext, interpeer, interplug, interpub, interrank, interscribe, intership, intersight, interskill, interslack, interspect, interstat, intersynth, intertest, intertrace, intertrack, intertree, tldr-swinton, tool-time, tuivision.

## Compatibility

Historical symlinks at `/root/projects/<name>` previously pointed into this monorepo. These have been removed. The canonical path is `~/projects/Sylveste/`.
