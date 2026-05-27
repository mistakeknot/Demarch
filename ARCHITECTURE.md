# Interagency Plugin Architecture

Auto-generated from `Sylveste/scripts/build-architecture-map.py`. 
DO NOT EDIT BY HAND — rerun the script to regenerate.

**Plugins surveyed:** 61

## Most-referenced plugins (hub nodes)

Plugins that many others depend on. Disabling these has wide blast radius.

| Plugin | Referenced by | Top consumers |
|---|---:|---|
| `intercheck` | 12 | interchart, interdoc, interfluence + 9 |
| `interflux` | 11 | interchart, interdeep, interkasten + 8 |
| `interspect` | 7 | interflux, interline, interphase + 4 |
| `interpath` | 6 | interchart, interkasten, interleave + 3 |
| `interlock` | 6 | interflux, interlab, interline + 3 |
| `interject` | 5 | interchart, interdeep, interphase + 2 |
| `interwatch` | 5 | interchart, interdoc, interkasten + 2 |
| `interdoc` | 5 | interchart, interkasten, interlore + 2 |
| `interphase` | 5 | interchart, interkasten, interline + 2 |
| `interstat` | 4 | interchart, interflux, interline + 1 |
| `intermem` | 4 | interchart, interlab, interpulse + 1 |
| `interleave` | 3 | interchart, interflux, interpath |
| `tool-time` | 3 | interchart, interspect, interwatch |
| `intermux` | 3 | interchart, intercheck, interpulse |
| `interpulse` | 3 | intercheck, intermux, intertrack |

## Plugins with most outbound dependencies (consumers)

Plugins that pull from many others. Most likely to break when peers change.

| Plugin | Outbound refs | Strong peers (count ≥ 3) |
|---|---:|---|
| `interwatch` | 19 | interdoc(14), interpath(11) |
| `interchart` | 18 | interkasten(4) |
| `interflux` | 15 | interstat(38), interrank(19), interknow(18), interspect(12), interpeer(12) |
| `interpath` | 8 | interwatch(16), interleave(6), interdoc(5) |
| `interline` | 7 | interspect(5), interlock(4), intercheck(4), interstat(3), interphase(3) |
| `interdeep` | 6 | interknow(4), interlens(3) |
| `interkasten` | 5 | interdoc(13), interwatch(9), interpath(8), interflux(4) |
| `interlab` | 4 | interlock(5) |
| `interdoc` | 3 | interwatch(6), interlore(4), intercheck(3) |
| `interpulse` | 3 | — |
| `interspect` | 3 | interflux(30), tool-time(7), interstat(3) |
| `intercheck` | 2 | — |
| `interlore` | 2 | — |
| `intermux` | 2 | — |
| `interphase` | 2 | interspect(6), interject(5) |

## Warnings — undeclared strong dependencies

These plugins reference others 3+ times in their own code but don't 
declare them in `peerDependencies`. Either declare the dependency or 
remove the references.

- **interchart** → missing: interkasten
- **interdeep** → missing: interknow, interlens
- **interdoc** → missing: intercheck, interlore, interwatch
- **interfer** → missing: interlab
- **interfluence** → missing: intercheck
- **interflux** → missing: intercept, interknow, interpeer, interrank, interspect, interstat, intersynth, intertrust
- **interject** → missing: intercheck
- **interkasten** → missing: interdoc, interflux, interpath, interwatch
- **interlab** → missing: interlock
- **interleave** → missing: interpath
- **interline** → missing: intercheck, interlock, interphase, interspect, interstat
- **interpath** → missing: interdoc, interleave, interwatch
- **interphase** → missing: interject, interspect
- **interplug** → missing: interskill
- **interscout** → missing: interject
- **interspect** → missing: interflux, interstat, tool-time
- **interstat** → missing: interflux
- **intertree** → missing: interkasten
- **intertrust** → missing: interspect
- **interwatch** → missing: interdoc, interpath
- **lattice** → missing: interlens
- **tldr-swinton** → missing: intercheck
- **tool-time** → missing: intercheck, interspect
- **tuivision** → missing: intercheck

## Per-plugin detail

### `interbrowse` (v0.4.1)

Browser automation and competitive research for AI agents. UX teardowns, docs crawls, cross-cutting synthesis, and CUJ generation — the full research-to-design pipeline via agent-browser CLI.

- Skills: 5
- Commands: 5
- Agents: 2

### `intercache` (v0.2.1)

Cross-session semantic cache for Claude Code. Content-addressed blob storage, per-project manifests, and session tracking — reduces cold start time and eliminates redundant file reads across sessions.

- MCP servers: intercache
- Referenced by: interdeep, interlab, intersight

### `intercept` (v0.1.3)

Smart decision gates — haiku LLM decisions that distill into local models over time

- Referenced by: interchart, interflux

### `interchart` (v0.1.8)

Interactive ecosystem diagram — scans Interverse monorepo and generates a D3.js force graph showing all plugins, skills, MCP tools, hooks, and their relationships.

- Skills: 1
- Discovered refs: interkasten(4), interflux(2), intercheck(2), interstat(2), intermem(2), interject(2)

### `intercheck` (v0.2.2)

Code quality guards and session health monitoring

- Skills: 1
- Discovered refs: interpulse(2), intermux(1)
- Referenced by: interchart, interdoc, interfluence, interject, interline, intermux, interpulse, intertrack + 4

### `intercraft` (v0.1.3)

Agent-native architecture patterns — design, review, and audit for agent-first applications.

- Skills: 1
- Commands: 1
- Agents: 1
- Referenced by: interflux, interwatch

### `interdeep` (v0.1.6)

Deep research plugin — content extraction and research orchestration via MCP tools.

- MCP servers: interdeep
- Skills: 1
- Commands: 1
- Agents: 3
- Discovered refs: interknow(4), interlens(3), interject(2), interflux(2), intercache(2), intersynth(2)
- Referenced by: interflux

### `interdeploy` (v0.1.0)

Deploy monitoring and auto-fix — watches Vercel deployments after push, diagnoses build failures from logs, fixes code, and re-pushes until the deploy succeeds.

- Skills: 1

### `interdev` (v0.2.0)

Developer tooling for Claude Code — MCP CLI interaction and Claude Code reference.

- Skills: 2
- Referenced by: interplug, interwatch

### `interdoc` (v5.2.3)

Recursive AGENTS.md generator with integrated Oracle critique, CLAUDE.md harmonization, incremental updates, diff previews, and smart monorepo scoping. Cross-AI compatible.

- Skills: 1
- Commands: 1
- Discovered refs: interwatch(6), interlore(4), intercheck(3)
- Referenced by: interchart, interkasten, interlore, interpath, interwatch

### `interfer` (v0.1.0)

Local MLX-LM inference server for Apple Silicon. Custom serving layer with priority queuing, thermal-aware scheduling, and experiment hooks for Sylveste/Clavain.

- MCP servers: interfer
- Discovered refs: interlab(3)

### `interfluence` (v0.2.12)

Analyze your writing style and adapt Claude's output to sound like you. Ingest writing samples, build a voice profile, and apply it to any human-facing documentation or copy.

- MCP servers: interfluence
- Skills: 6
- Commands: 1
- Agents: 1
- Discovered refs: intercheck(3)
- Referenced by: interchart, interflux

### `interflux` (v0.2.70)

Multi-agent review and research with scored triage, domain detection, content slicing, intermediate finding sharing, and knowledge injection. 17 agents (12 review + 5 research), 7 commands, 1 skill (u

- MCP servers: exa, openrouter-dispatch
- Skills: 2
- Commands: 7
- Agents: 17
- Discovered refs: interstat(38), interrank(19), interknow(18), interspect(12), interpeer(12), intersynth(11)
- Referenced by: interchart, interdeep, interkasten, interline, interpath, interspect, interstat, intersynth + 3

### `interform` (v0.1.0)

Design patterns and visual quality for Claude Code — distinctive, production-grade interfaces.

- Skills: 1
- Referenced by: interwatch

### `interhelm` (v0.2.2)

Agent-as-operator runtime diagnostics — teaches agents to observe and control running applications via diagnostic HTTP servers and CLI tools.

- Skills: 4
- Agents: 1

### `interject` (v0.1.14)

Ambient discovery and research engine. Continuously scans arXiv, Hacker News, GitHub, and Anthropic docs for new capabilities, workflows, and tools relevant to your engineering ecosystem. Creates bead

- MCP servers: interject
- Skills: 5
- Discovered refs: intercheck(3)
- Referenced by: interchart, interdeep, interphase, interscout, interwatch

### `interkasten` (v0.4.25)

Living bridge between your projects folder and Notion — bidirectional sync with adaptive AI documentation and pagent workflow automation

- MCP servers: interkasten
- Skills: 3
- Commands: 3
- Discovered refs: interdoc(13), interwatch(9), interpath(8), interflux(4), interphase(1)
- Referenced by: interchart, intertree

### `interknow` (v0.1.5)

Knowledge compounding — durable pattern repository with provenance tracking, temporal decay, and semantic retrieval via qmd.

- MCP servers: qmd
- Skills: 2
- Referenced by: interdeep, interflux

### `interlab` (v0.4.8)

Autonomous experiment loop with mutation provenance tracking — init, run, log experiments with JSONL persistence, git isolation, SQLite mutation store, and ic events bridge.

- MCP servers: interlab
- Skills: 2
- Discovered refs: interlock(5), interskill(1), intercache(1), intermem(1)
- Referenced by: interfer

### `interlearn` (v0.1.0)

Cross-repo institutional knowledge index — indexes solution docs across the Interverse monorepo, enables unified search, and audits reflect coverage.

- Skills: 1

### `interleave` (v0.1.2)

Deterministic Skeleton with LLM Islands — token-efficient document generation via template-then-fill.

- Skills: 1
- Discovered refs: interpath(3)
- Referenced by: interchart, interflux, interpath

### `interlens` (v2.2.4)

288 FLUX cognitive lenses for structured thinking — MCP server with lens search, thinking mode workflows, belief statement generation, quality evaluation, and solution synthesis.

- MCP servers: interlens
- Referenced by: interdeep, interflux, lattice

### `interline` (v0.2.13)

Dynamic statusline for Claude Code — shows workflow phase, bead context, and Codex dispatch state. Integrates with Clavain and interphase.

- Commands: 2
- Discovered refs: interspect(5), interlock(4), intercheck(4), interstat(3), interphase(3), interflux(1)
- Referenced by: interlock, interpath, interwatch

### `interlock` (v0.2.14)

MCP server for intermute file reservation and agent coordination. 12 tools: reserve, release, conflict check, messaging, agent listing, negotiation, escalation. Companion plugin for Clavain.

- MCP servers: interlock
- Skills: 2
- Commands: 4
- Discovered refs: interline(1)
- Referenced by: interflux, interlab, interline, interpath, intersite, interwatch

### `interlore` (v0.1.0)

Philosophy observer — detects latent design patterns and philosophy drift from decision artifacts, proposes PHILOSOPHY.md updates.

- Skills: 1
- Commands: 3
- Discovered refs: interdoc(1), interpath(1)
- Referenced by: interdoc

### `intermap` (v0.1.7)

Project-level code mapping: project registry, call graphs, architecture analysis, agent overlay, cross-project dependencies, pattern detection, live changes. MCP server with 9 tools.

- MCP servers: intermap
- Skills: 1
- Referenced by: interchart

### `intermem` (v0.2.4)

Memory synthesis — graduates stable auto-memory facts to AGENTS.md/CLAUDE.md

- Skills: 2
- Discovered refs: interwatch(1)
- Referenced by: interchart, interlab, interpulse, interscribe

### `intermix` (v0.1.11)

Cross-repo matrix evaluation harness — run Skaffen against unfamiliar codebases, classify outcomes, track failure patterns.

- MCP servers: intermix
- Skills: 1

### `intermonk` (v0.1.2)

Hegelian dialectic reasoning — Electric Monk subagents for structured contradiction analysis and synthesis

- Skills: 1

### `intermux` (v0.1.8)

Agent activity visibility -- tmux monitoring, activity feeds, health detection. Enriches intermute with live context.

- MCP servers: intermux
- Skills: 1
- Discovered refs: interpulse(1), intercheck(1)
- Referenced by: interchart, intercheck, interpulse

### `intername` (v0.1.2)

Agent and agency naming for legible orchestration — memorable, deterministic identities across all surfaces.

- Commands: 2

### `internext` (v0.1.5)

Work prioritization and next-task analysis for Claude Code — tradeoff-aware recommendations from project state.

- Skills: 1
- Referenced by: interwatch

### `interpath` (v0.3.3)

Product artifact generator — roadmaps, PRDs, vision docs, changelogs, CUJs, and status reports from beads, brainstorms, and project state. Companion plugin for Clavain.

- Skills: 1
- Commands: 8
- Discovered refs: interwatch(16), interleave(6), interdoc(5), interflux(2), interphase(1), interline(1)
- Referenced by: interchart, interkasten, interleave, interlore, interscout, interwatch

### `interpeer` (v0.1.1)

Cross-AI peer review — quick (Claude↔Codex), deep (Oracle), council (multi-model), mine (disagreement extraction).

- Skills: 1
- Commands: 1
- Referenced by: interflux, interline

### `interphase` (v0.3.17)

Phase tracking, gate validation, and work discovery for the Beads issue tracker. Companion plugin for Clavain — adds lifecycle state management on top of the core beads plugin.

- Skills: 1
- Discovered refs: interspect(6), interject(5)
- Referenced by: interchart, interkasten, interline, interpath, interwatch

### `interplug` (v0.1.5)

Plugin development toolkit — lifecycle management, structure validation, and troubleshooting for Claude Code plugins

- Skills: 3
- Discovered refs: interskill(3), interdev(1)
- Referenced by: interskill

### `interpub` (v0.1.8)

Safe plugin publishing — bumps all version locations, validates sync, commits and pushes with confirmation.

- Commands: 2
- Referenced by: interwatch

### `interpulse` (v0.1.5)

Session context monitoring — pressure tracking, token estimation, threshold warnings

- Skills: 1
- Discovered refs: intermem(2), intercheck(1), intermux(1)
- Referenced by: intercheck, intermux, intertrack

### `interrank` (v0.3.1)

Snapshot-backed model/benchmark ranking MCP server for AgMoDB

- MCP servers: interrank
- Referenced by: interflux

### `interscout` (v0.1.2)

[DEPRECATED 2026-04-27] Roadmap refresh orchestrator. Functionality migrated to /schedule + /interject:scan + /interpath:all + /clavain:status. See README.md for migration. Plugin still works but new 

- Skills: 3
- Commands: 3
- Discovered refs: interject(23), interpath(2)

### `interscribe` (v0.1.2)

Documentation quality toolkit — enforces CLAUDE.md/AGENTS.md boundaries, applies progressive disclosure, deduplicates across doc hierarchy.

- Skills: 1
- Discovered refs: intermem(1)

### `intersearch` (v0.2.2)

Shared embedding and search infrastructure for the Interverse ecosystem — sentence-transformer embeddings, persistent vector store, and Exa web search.

- MCP servers: intersearch
- Skills: 1
- Referenced by: interchart, interwatch

### `interseed` (v0.1.0)

Idea garden: capture, refine, and graduate ideas from rough seeds to actionable plans.

- MCP servers: interseed

### `intership` (v0.3.3)

Culture ship names as Claude Code spinner verbs. Because why would you settle for 'Thinking...' when you could have 'Experiencing A Significant Gravitas Shortfall'?

- Commands: 1

### `intersight` (v0.1.5)

Automated UI/UX design analysis — extracts W3C DTCG tokens, component inventory, and layout analysis from any URL.

- Skills: 1
- Discovered refs: intercache(2)

### `intersite` (v0.1.0)

GSV portfolio site content generation and pipeline management

- Skills: 2
- Discovered refs: interlock(1)

### `interskill` (v0.1.3)

Skill authoring toolkit — unified skill creation, TDD-adapted testing, and audit. Consolidated from interdev's create-agent-skills and writing-skills.

- Skills: 2
- Discovered refs: interplug(1)
- Referenced by: interlab, interplug

### `interslack` (v0.1.0)

Slack integration for Claude Code — send messages, read channels, test integrations.

- Skills: 1
- Referenced by: interwatch

### `interspect` (v0.1.20)

Agent performance profiler and routing optimizer. Collects evidence about flux-drive agent accuracy, proposes routing overrides for underperforming agents, and monitors canary periods. Companion plugi

- Discovered refs: interflux(30), tool-time(7), interstat(3)
- Referenced by: interflux, interline, interphase, interstat, intertrust, interwatch, tool-time

### `interstat` (v0.3.0)

Token efficiency benchmarking, session analytics, and API-equivalent cost analysis for agent workflows

- Skills: 4
- Discovered refs: interflux(5), interspect(2)
- Referenced by: interchart, interflux, interline, interspect

### `intersynth` (v0.1.12)

Multi-agent synthesis engine — collects findings from parallel review/research agents, deduplicates, writes verdicts, produces compact summaries. Keeps agent output out of the host context.

- Agents: 3
- Discovered refs: interflux(1)
- Referenced by: interdeep, interflux

### `intertest` (v0.1.3)

Engineering quality disciplines — systematic debugging, test-driven development, and verification gates.

- Skills: 3

### `intertrace` (v0.1.2)

Cross-module integration gap tracer — traces data flows from shipped features to find unverified consumer edges.

- Skills: 1
- Agents: 1
- Referenced by: interflux

### `intertrack` (v0.1.4)

Feature-level success metric tracking for Demarch

- Skills: 2
- Discovered refs: interpulse(1), intercheck(1)

### `intertree` (v0.1.2)

Project hierarchy management — filesystem discovery, parent-child relationships, tagging, and layout orchestration

- Skills: 1
- Discovered refs: interkasten(4), interflux(1)

### `intertrust` (v0.1.3)

Agent trust scoring — reputation tracking, severity-weighted decay, and suppression candidates.

- Commands: 1
- Discovered refs: interspect(12), interflux(1)
- Referenced by: interflux

### `interwatch` (v0.5.0)

Doc freshness and correctness monitoring — auto-discovers watchable docs, detects drift via 17 signal types, scores confidence, dispatches generators for auto-refresh, and runs stranger-perspective co

- Skills: 1
- Commands: 5
- Discovered refs: interdoc(14), interpath(11), interphase(1), interline(1), interflux(1), interlock(1)
- Referenced by: interchart, interdoc, interkasten, intermem, interpath

### `lattice` (v0.2.0)

Generative ontology layer for agentic platforms — 5 composable type families, 7 interaction rules, multi-family membership, lifecycle transitions. Indexes entity metadata across subsystems and returns

- Discovered refs: interlens(12)

### `tldr-swinton` (v0.7.18)

Token-efficient code reconnaissance for LLMs. Autonomous skills save 48-85% tokens via diff-context, semantic search, structural patterns, and symbol analysis. Includes MCP server for direct tool inte

- MCP servers: tldr-code
- Skills: 4
- Commands: 6
- Discovered refs: intercheck(3)
- Referenced by: interchart, interwatch

### `tool-time` (v0.3.11)

Tool usage analytics for Claude Code. Tracks tool patterns via hooks, detects inefficiencies, and offers community comparison with anonymized data.

- Skills: 2
- Discovered refs: interspect(23), intercheck(3)
- Referenced by: interchart, interspect, interwatch

### `tuivision` (v0.2.1)

TUI automation and visual testing - Playwright for terminal applications. Spawn, interact with, and screenshot TUI apps.

- MCP servers: tuivision
- Skills: 1
- Discovered refs: intercheck(3)
- Referenced by: interpath, interwatch
