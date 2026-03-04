# Architecture

## Overview

Demarch is the physical monorepo for the open-source autonomous software development agency platform. It contains five pillars: **Intercore** (`/core`) the orchestration kernel, **Clavain** (`/os`) the agent OS and reference agency, **Interverse** (`/interverse`) the companion plugin ecosystem, **Autarch** (`/apps`) the TUI surfaces, and **Interspect** (cross-cutting profiler, currently housed in Clavain). Plus `sdk/` for shared libraries (interbase). Each module keeps its own `.git` as a nested independent repo. The root `Demarch/` also has a `.git` for the monorepo skeleton (scripts, docs, CLAUDE.md). Git operations apply to the nearest `.git`; verify with `git rev-parse --show-toplevel`.

## Glossary

| Term | Meaning |
|------|---------|
| **Pillar** | One of the 5 top-level components of Demarch: Intercore, Clavain, Interverse, Autarch, Interspect. Organizational term — use "layer" (L1/L2/L3) for architectural dependency. |
| **Layer** | Architectural dependency level: L1 (Kernel/Intercore), L2 (OS/Clavain + Drivers/Interverse), L3 (Apps/Autarch). Interspect is cross-cutting. |
| **Beads** | File-based issue tracker (`bd` CLI). Each project can have a `.beads/` database. All active tracking is at Demarch root. |
| **Plugin** | A Claude Code extension (skills, commands, hooks, agents, MCP servers) installed from the marketplace. |
| **MCP** | Model Context Protocol — enables plugins to expose tools as server processes that Claude Code calls directly. |
| **Driver** | A companion plugin (part of the Interverse pillar) that extends Clavain with one capability. Also called "companion plugin." |
| **Marketplace** | The `interagency-marketplace` registry at `core/marketplace/` — JSON catalog of all published plugins. |
| **Interspect** | Adaptive profiler pillar — reads kernel events, proposes OS configuration changes. Cross-cutting (not a layer). |

## Directory Layout

Each subproject has its own CLAUDE.md and AGENTS.md — read those before editing. Use `ls apps/ core/ interverse/ os/ sdk/` to discover modules.

| Path | Pillar | Notes |
|------|--------|-------|
| `apps/autarch/` | Autarch | TUI interfaces (Bigend, Gurgeh, Coldwine, Pollard) |
| `apps/intercom/` | Autarch | Multi-runtime AI assistant (Claude, Gemini, Codex) |
| `os/clavain/` | Clavain | Autonomous software agency (L2 OS) |
| `core/intercore/` | Intercore | Orchestration kernel — Go CLI `ic` (L1) |
| `core/intermute/` | Intercore | Multi-agent coordination service (Go) |
| `core/marketplace/` | Intercore | Plugin marketplace registry |
| `interverse/` | Interverse | Companion plugins — each has own docs (`ls interverse/ | wc -l`) |
| `sdk/interbase/` | — | Shared integration SDK (Bash/Go/Python) |
| `docs/` | — | Platform-level docs only (brainstorms, research, solutions) |

> **Docs convention:** `Demarch/docs/` is for platform-level work only. Each subproject keeps its own docs.
> **Artifact naming:** See [`CONVENTIONS.md`](../CONVENTIONS.md) for canonical paths.

## Key Dependency Chains

```
Clavain (L2) → interlock → intermute (L1)    # file coordination
Clavain (L2) → interflux → intersearch        # multi-agent review
Clavain (L2) → interwatch → interpath/interdoc # doc freshness → generator dispatch
interject → intersearch                        # ambient discovery
interdeep → interject                          # deep research extraction + search
Clavain (L2) → intertrust                     # agent trust scoring
```

Standalone plugins (no cross-deps): interfluence, interkasten, tldr-swinton, intercache, intercheck, interstat, interpeer, intertest, interlens, intermap, intermux, tool-time, tuivision.

## Compatibility

Symlinks at `/root/projects/<name>` point into this monorepo for backward compatibility with scripts, configs, and Claude Code session history that reference old paths. These can be removed once all references are updated.
