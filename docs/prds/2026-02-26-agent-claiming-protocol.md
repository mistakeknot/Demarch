# PRD: Agent Claiming Protocol

**Bead:** iv-sz3sf
**Brainstorm:** [docs/brainstorms/2026-02-26-agent-claiming-protocol.md](../brainstorms/2026-02-26-agent-claiming-protocol.md)
**Date:** 2026-02-26

## Problem

Multiple agents working on the same Demarch monorepo routinely collide on work items. Agent A picks up a bead, Agent B picks up the same bead minutes later, both spend tokens independently. There is no collision detection, no visibility into who is working on what, and no automatic cleanup when agents crash.

**Impact:** Wasted tokens (double-brainstorm, double-planning), confused humans ("who's working on this?"), orphaned in-progress beads that block the ready queue.

## Solution

Wire the existing `bd update --claim` atomic primitive into all workflow entry points, give agents distinguishable identities, and add heartbeat-based liveness so stale claims auto-expire.

## Features

### F1: Agent Identity at Session Start
Set `BD_ACTOR` to a distinguishable name when a Claude Code (or Codex) session begins. Priority cascade: session ID prefix (8 chars) as the default, with mcp-agent-mail name as a future enhancement.

**Acceptance Criteria:**
- `BD_ACTOR` is set and exported in `CLAUDE_ENV_FILE` during session-start hook
- All `bd` operations in the session use the actor name (visible in `bd show` audit)
- Two concurrent sessions on the same machine have different `BD_ACTOR` values

### F2: Atomic Claiming in Workflow Entry Points
Replace all `bd update --status=in_progress` calls with `bd update --claim`. Handle claim failures gracefully: inform the user/agent, re-run discovery to find unclaimed work.

**Acceptance Criteria:**
- `/clavain:route` uses `--claim` instead of `--status=in_progress`
- Discovery scan (`lib-discovery.sh`) uses `--claim` when routing to selected bead
- `sprint_claim()` / `bead_claim()` in `lib-sprint.sh` delegates to `bd update --claim`
- Claim failure shows actionable message: "Bead iv-XXXXX already claimed by <actor> — choosing next available work"
- Dolt lock timeout (not claim conflict) is distinguished from actual claim conflict

### F3: `bd who` Visibility Command
A shell script that shows in-progress beads grouped by assignee with staleness indicators.

**Acceptance Criteria:**
- `bd-who` (or `bd who` if beads supports external subcommands) produces grouped output
- Shows assignee, bead ID, title, priority, and time since last update
- Unclaimed in-progress beads shown in separate "Unclaimed" section
- Available to all agents via PATH

### F4: Claim Heartbeat
Post-tool hook refreshes `claimed_at` timestamp periodically so active agents' claims stay fresh.

**Acceptance Criteria:**
- Heartbeat fires at most once per 60 seconds (not every tool call)
- Updates `claimed_at` bead state for the active `CLAVAIN_BEAD_ID`
- Heartbeat failure is silent (never blocks tool execution)
- `BD_ACTOR` is set before heartbeat fires (dependency on F1)

### F5: Stale Claim Reaper (TTL Reduction)
Reduce the stale-claim TTL in discovery from 2h to 30min. Heartbeat (F4) keeps active claims alive; dead agents' claims expire faster.

**Acceptance Criteria:**
- Discovery auto-releases claims where `claimed_at` is >30min stale
- Active agents with heartbeat never have claims reaped
- Session-end hook (`Notification`) attempts explicit release (best-effort)

## Cut (YAGNI for v1)

- **Agent bead registration** (`bd agent state gt-X running`) — adds per-session overhead for minimal value over assignee-based claiming
- **Interlock bridge** — file reservations and bead claims are different scopes, no bridge needed
- **mcp-agent-mail name → BD_ACTOR bridge** — requires MCP tool call at session start which adds latency and a dependency. Session ID prefix is sufficient for v1
- **`bd ready --unclaimed` filter** — discovery already deprioritizes claimed beads; a flag can be added later
- **Intercore coordination as claiming backend** — avoids dolt lock contention but adds architectural complexity. Revisit if dolt locks become a practical problem with >3 agents

## Non-Goals

- Assigning work to specific agents (agents self-select from the ready queue)
- Priority-based claim arbitration (first-come-first-served is fine)
- Cross-repo claiming (beads DB is per-repo)

## Dependencies

- `bd update --claim` must work correctly (it does — tested)
- `CLAUDE_ENV_FILE` must be writable from session-start hook (it is)
- Dolt lock contention must be tolerable at current concurrency (2-3 agents) — accepted risk

## Success Metrics

- Zero duplicate brainstorms on the same bead within a 24h window
- `bd who` shows distinct actor names for concurrent agents
- Stale claims released within 30min (down from 2h)
