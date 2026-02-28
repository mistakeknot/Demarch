---
bead: iv-4iy6g
type: prd
date: 2026-02-28
status: active
---

# PRD: Intertrace — Cross-Module Integration Tracer

## Problem

Integration gaps between Demarch modules are invisible until someone manually reads PHILOSOPHY.md, greps the codebase, and traces data flows by hand. The iv-5muhg sprint proved this costs real time — 5 gaps across 4 modules, all found only by manual investigation. Shipped features silently fail to reach consumers that should receive their data.

## Solution

A Clavain companion plugin (`intertrace`) that, given a bead ID, traces the data flow from the feature's changed files through the module graph and identifies consumers that are declared but not wired. Reports findings ranked by evidence strength for human triage, with optional bead creation.

## Features

### F1: Plugin Skeleton & Project Scaffolding
**What:** Standard interverse plugin structure plus the MCP server criteria canon doc.
**Acceptance criteria:**
- [ ] `interverse/intertrace/` follows plugin-standard.md (6 root files, plugin.json, tests/)
- [ ] `docs/canon/mcp-server-criteria.md` written with server vs skill decision criteria
- [ ] Root `AGENTS.md` has pointer to the new canon doc
- [ ] `ic publish init` registers plugin in marketplace
- [ ] Structural tests pass (`uv run pytest -q tests/structural/`)

### F2: Event Bus Tracer
**What:** Shell library that traces `ic events emit` calls to their consumers, checking cursor registrations and hook_id allowlists.
**Acceptance criteria:**
- [ ] `lib/trace-events.sh` finds all `ic events emit <type>` calls in a set of changed files
- [ ] For each event type, identifies modules with cursor registrations (via `ic events tail --consumer=` patterns)
- [ ] Checks hook_id allowlists in consumer modules (grep for case statements in `_validate_hook_id` patterns)
- [ ] Returns structured output: `{"event_type": "...", "producer": "...", "consumers": [{"module": "...", "verified": true/false, "evidence": "..."}]}`
- [ ] Catches the iv-5muhg hook_id allowlist gap when tested against those commits

### F3: Contract Verifier
**What:** Shell library that parses `contract-ownership.md` and verifies declared consumers have code evidence.
**Acceptance criteria:**
- [ ] `lib/trace-contracts.sh` parses contract-ownership.md consumer declarations
- [ ] For each declared consumer, greps codebase for evidence of actual consumption (CLI calls, import references, schema usage)
- [ ] Returns structured output: `{"contract": "...", "declared_consumers": [...], "verified": [...], "unverified": [...]}`
- [ ] Handles the common contract format (table rows with Owner | Consumers | Stability columns)

### F4: Companion Graph Verifier
**What:** Shell library that reads `companion-graph.json` and verifies each edge has code evidence.
**Acceptance criteria:**
- [ ] `lib/trace-companion.sh` reads `docs/companion-graph.json` edge list
- [ ] For each `{from, to, relationship}` edge, searches for import/call/source evidence between the two modules
- [ ] Uses intermap's `code_structure` and `impact_analysis` tools for verification where available
- [ ] Returns structured output: `{"edge": "...", "verified": true/false, "evidence": "..."}`
- [ ] Reports undeclared-but-actual edges found during verification (bonus findings)

### F5: /intertrace Slash Command & Output Model
**What:** The main skill that orchestrates tracers and presents findings.
**Acceptance criteria:**
- [ ] `skills/intertrace.md` accepts a bead ID as input
- [ ] Resolves bead → commits → changed files via `bd show` + `git log --grep`
- [ ] Calls intermap `code_structure` on changed files to identify new producers
- [ ] Runs all enabled tracers (F2, F3, F4) and merges results
- [ ] Ranks findings by evidence strength: P1 (declared + zero evidence), P2 (partial evidence), P3 (docs-only gap)
- [ ] Presents ranked report via AskUserQuestion with options: create beads for selected, create all, save report only
- [ ] Saves report to `docs/traces/YYYY-MM-DD-<bead-id>-trace.md`
- [ ] When tested against iv-5muhg, rediscovers at least 3 of the 4 integration gaps (#1, #2/#3, #5)

### F6: fd-integration Review Agent
**What:** Interflux review agent that runs during flux-drive when diffs touch multiple modules.
**Acceptance criteria:**
- [ ] `agents/review/fd-integration.md` follows interflux agent format (YAML frontmatter + review approach sections)
- [ ] Triggers when changed files span 2+ modules (detected by intermap `resolve_project`)
- [ ] Reviews for: missing event consumer registrations, missing hook_id allowlist entries, undocumented lib-*.sh sourcing, missing companion-graph.json entries for new cross-plugin dependencies
- [ ] Produces findings in standard flux-drive format (P0-P3 with evidence + recommendation)
- [ ] Registered in interflux's agent roster (plugin.json agents field)

## Non-goals

- **Full monorepo scan** (`/intertrace --scan`) — deferred to phase 3
- **Auto-updating companion-graph.json** — report only, no auto-mutation
- **Shell lib sourcing tracer** — deferred to phase 2 data sources
- **AGENTS.md prose parsing** — deferred to phase 3 data sources
- **Post-ship hook** (auto-run on `bd close`) — manual invocation only for now
- **New MCP server** — thin plugin, no server process

## Dependencies

- **intermap MCP server** — `project_registry`, `code_structure`, `impact_analysis` tools
- **intercore** — `ic events` CLI for event type enumeration
- **beads** — `bd show`, `bd create` for bead resolution and gap bead creation
- **contract-ownership.md** — must exist at `core/intercore/contracts/contract-ownership.md`
- **companion-graph.json** — must exist at `docs/companion-graph.json`
- **interflux** — agent registration for fd-integration (F6)

## Open Questions

- Should `cross_project_deps` in intermap be extended to detect event-bus edges? (Could benefit both intermap and intertrace)
- What domain_boost values should fd-integration get in flux-drive's scoring model? (Needs testing to calibrate)
