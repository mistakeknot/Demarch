# Brainstorm: Agent Claiming Protocol

**Bead:** iv-sz3sf
**Date:** 2026-02-26
**Status:** brainstorm

## Problem Statement

When multiple agents work concurrently on the same Demarch monorepo, there is no reliable way for them to:

1. **Claim work exclusively** — `bd update --status=in_progress` is a soft claim with no collision detection. Another agent can claim the same bead with no error.
2. **See who's working on what** — `bd list --status=in_progress` shows *what* is claimed but not *by whom*. There's no `bd who` command.
3. **Detect stale claims** — if an agent crashes, its claim persists forever. No heartbeat, no reaper.

This leads to wasted tokens (two agents independently brainstorm the same bead), confusion (agent picks up `iv-xesrg` not knowing another agent already started), and orphaned in-progress beads that never get released.

## What Already Exists

### Primitives That Work

| Primitive | Location | What It Does | Used? |
|-----------|----------|-------------- |-------|
| `bd update --claim` | beads CLI (Go) | Atomic claim: sets assignee + status=in_progress, **fails if already claimed by different actor** | **No** — nothing in the workflow calls it |
| `sprint_claim()` | `lib-sprint.sh:542` | Lock-guarded claim via intercore agent registration. Checks active sessions, auto-releases after 60min | **Yes** — but only for sprints, not regular beads |
| `bead_claim()` | `lib-sprint.sh` | Sets `claimed_by` and `claimed_at` bead state. Cross-session visibility | **Yes** — called by sprint_claim |
| Discovery score penalty | `lib-discovery.sh:336` | -50 score for beads claimed <2h ago by another session. Auto-releases stale claims >2h | **Yes** — but doesn't filter, just deprioritizes |
| `bd agent state/heartbeat/slot` | beads CLI (Go) | Full agent lifecycle: states (idle→running→working→stuck→done), heartbeat timestamps, slot-based work attachment | **No** — zero agent beads exist in DB |
| `$BD_ACTOR` env var | beads CLI (Go) | Actor identity for audit trail. Defaults to git user.name or $USER | **Not set** — all agents appear as "mistakeknot" |
| `$CLAUDE_SESSION_ID` | Clavain session-start hook | Unique session identifier exported to env | **Yes** — but not bridged to BD_ACTOR |
| mcp-agent-mail identity | mcp-agent-mail MCP server | `register_agent` with project, program, model, task. Persisted name | **Partially** — registered but not bridged to beads |
| interlock file reservations | `ic coordination reserve/release` | File-level edit intent tracking with heartbeat TTL | **Yes** — but no bridge to bead claims |

### The Gap Map

```
Agent Session Start
  ├─ Clavain hook: sets CLAUDE_SESSION_ID           ✓ exists
  ├─ mcp-agent-mail: registers identity             ✓ exists
  ├─ interlock: registers for file coordination     ✓ exists
  ├─ BD_ACTOR set to agent-distinguishable name     ✗ MISSING
  ├─ Agent bead created (bd agent state X running)  ✗ MISSING
  └─ Bead claimed via bd update --claim             ✗ MISSING (uses soft claim)

Agent Working
  ├─ Heartbeat keeping claim alive                  ✗ MISSING
  └─ "Who's working on what" visibility             ✗ MISSING

Agent Session End
  ├─ Claim released                                 ✗ MISSING (stale reaper exists at 2h)
  └─ Agent bead marked done                         ✗ MISSING
```

### Key Constraints

1. **Dolt DB lock is process-exclusive.** Two concurrent `bd` commands contend for a 15s lock. Under high concurrency, `bd update --claim` may timeout with a lock error, not a clean "already claimed" rejection. This limits how much we can rely on beads-level claiming for real-time coordination.

2. **Session IDs are opaque UUIDs.** `CLAUDE_SESSION_ID` is like `a1b2c3d4-e5f6-...` — not human-readable. We need a mapping to something meaningful (tmux pane, agent-mail name).

3. **Sprint claims ≠ bead claims.** `sprint_claim()` uses intercore locks + agent registration. `bd update --claim` uses beads-level assignee field. These are parallel systems with different TTLs (60min vs 2h) and different failure modes.

4. **No write-back from session-end.** Claude Code's `Notification` hook fires on session end but can't reliably write to the DB — the process may be shutting down. Heartbeat + TTL is more reliable than explicit release.

## Layer 1: Protocol (Wire `--claim` Into Workflow)

### Goal
Make claiming the default path so collisions are detected immediately, not after tokens are spent.

### Changes

**1a. Set `BD_ACTOR` to a distinguishable identity at session start**

In `os/clavain/hooks/session-start.sh`:
```bash
# Agent identity for beads audit trail
# Prefer agent-mail name > tmux pane > session ID prefix
agent_name=""
if command -v intermux-identity &>/dev/null; then
    agent_name=$(intermux-identity 2>/dev/null) || agent_name=""
fi
if [[ -z "$agent_name" ]]; then
    agent_name="${CLAUDE_SESSION_ID:0:8}"
fi
export BD_ACTOR="$agent_name"
# Persist to env file so hooks inherit it
echo "BD_ACTOR=$agent_name" >> "$CLAUDE_ENV_FILE"
```

**1b. Replace soft claims with atomic claims**

In `lib-discovery.sh` (discovery_scan_beads routing):
```bash
# Before: bd update "$CLAVAIN_BEAD_ID" --status=in_progress
# After:
bd update "$CLAVAIN_BEAD_ID" --claim 2>/dev/null
if [[ $? -ne 0 ]]; then
    # Claim failed — someone else has it
    log_warn "bead already claimed" bead_id="$CLAVAIN_BEAD_ID"
    # Re-run discovery excluding this bead
    ...
fi
```

In `/clavain:route` skill (Step 3.5 and Step 4c):
```
# Before: bd update "$CLAVAIN_BEAD_ID" --status=in_progress
# After:  bd update "$CLAVAIN_BEAD_ID" --claim
# Handle failure: tell user "another agent claimed this bead"
```

**1c. Bridge sprint_claim to use `bd update --claim`**

In `lib-sprint.sh` `bead_claim()`:
```bash
# Before: bd set-state "$bead_id" "claimed_by=$session_id" ...
# After:  bd update "$bead_id" --claim
# The --claim flag already sets assignee + in_progress atomically
```

### Tradeoffs

- (+) Immediate collision detection — no wasted tokens
- (+) Zero new infrastructure — `--claim` already exists
- (-) Dolt lock contention under simultaneous claims — degrades to lock timeout error, not clean rejection
- (-) `BD_ACTOR` defaults to git user.name which is "mistakeknot" for all agents — need the identity bridge

### Open Questions

1. Should `bd ready` auto-filter claimed beads, or just add a `--unclaimed` flag?
2. When `--claim` fails due to dolt lock (not claim conflict), should we retry once? The lock timeout is 15s which is a long wait.
3. Should `sprint_claim()` and `bd update --claim` be unified or remain parallel systems?

## Layer 2: Visibility (`bd who` + Agent Dashboard)

### Goal
Any agent (or human) can see at a glance: who is working on what, how fresh the claim is, and whether the agent is still alive.

### Changes

**2a. `bd who` command**

New beads CLI command that shows in-progress beads grouped by assignee:
```
$ bd who
mistakeknot/a1b2c3d4 (active 12m ago)
  ◐ iv-oq1h8 [P1] Cost-per-landable-change baseline
  ◐ iv-sz3sf [P2] Agent claiming protocol

mistakeknot/e5f6g7h8 (active 45m ago)
  ◐ iv-xesrg [P3] CI: build ic + bd before shell tests

Unclaimed in-progress:
  ◐ iv-yy1l3 [P1] Unified Structured Logging (epic)
  ◐ iv-5zoaq [P2] Unified Structured Logging (blocked)
```

Implementation: `bd list --status=in_progress --json | jq 'group_by(.assignee)'` + enrich with last-updated timestamp as staleness indicator.

This could be a Go command in beads, or a shell wrapper. Shell wrapper is faster to ship; Go command is more robust.

**2b. Discovery shows claim owner**

In `lib-discovery.sh`, when a bead is claimed by another session, the discovery output should show:
```
"claimed_by": "e5f6g7h8",
"claim_age_min": 45
```

And the presentation in `/clavain:route` should say:
```
⚡ iv-xesrg [P3] CI: build ic + bd before shell tests
  Claimed by e5f6g7h8 (45m ago) — skip? [y/N]
```

**2c. Agent bead registration (optional)**

Register a `gt:agent` bead for each session at startup:
```bash
# In session-start hook:
bd agent state "gt-${BD_ACTOR}" running 2>/dev/null || true
```

This creates a visible agent entity in the beads DB. Advantages:
- `bd agent show gt-a1b2c3d4` shows agent state + attached work
- `bd slot set gt-a1b2c3d4 hook iv-oq1h8` — explicit work attachment
- Agents become queryable: `bd list --label=gt:agent --status=open`

Disadvantage: another bead per session. Given 2572 beads already, this is noise unless there's a separate view.

### Tradeoffs

- (+) Human and agent can see collision before it happens
- (+) `bd who` is useful for debugging "what's this agent doing?"
- (-) Agent beads add per-session overhead — consider making them ephemeral (wisps)
- (-) `bd who` as a shell wrapper means another bd invocation (dolt lock)

### Open Questions

1. `bd who` as Go native command vs shell wrapper? Go is better long-term, shell is faster to ship.
2. Should agent beads be wisps (ephemeral, not exported to JSONL) or regular beads?
3. Should intermux's `list_agents` be bridged to beads agent registration? They track overlapping state (alive agents + what they're doing).

## Layer 3: Liveness (Heartbeat + Stale Reaper)

### Goal
Claims don't become permanent. If an agent dies, its work returns to the ready pool within a bounded time.

### Current State

- Discovery already auto-releases claims >2h old (line 348-351 of lib-discovery.sh)
- `sprint_claim()` auto-evicts sessions >60min old (line 576 of lib-sprint.sh)
- No periodic heartbeat — claim freshness is only checked when another agent runs discovery

### Design Options

**Option A: Heartbeat via post-tool hook (cheap, approximate)**

Every N tool calls, update claim freshness:
```bash
# In a lightweight post-tool hook (e.g., interphase or interstat):
heartbeat_interval=60  # seconds
last_heartbeat="${BEAD_LAST_HEARTBEAT:-0}"
now=$(date +%s)
if (( now - last_heartbeat > heartbeat_interval )); then
    bd set-state "$CLAVAIN_BEAD_ID" "claimed_at=$(date +%s)" 2>/dev/null || true
    export BEAD_LAST_HEARTBEAT="$now"
fi
```

- (+) No new daemon, no background process
- (-) Dolt lock contention on every heartbeat (mitigated by interval)
- (-) Only fires when agent is actively using tools — idle agent doesn't heartbeat

**Option B: Reaper as periodic sweep (explicit cleanup)**

A `bd reap` command (or cron job) that runs periodically:
```bash
bd list --status=in_progress --json | jq -r '.[] | select(.updated_at < (now - 7200)) | .id' | while read id; do
    bd update "$id" --status=open --assignee=""
    echo "Released stale claim: $id"
done
```

- (+) Clean separation — claiming doesn't need heartbeat
- (-) Requires something to run it (cron, session-start hook, or manual)
- (-) 2h TTL means up to 2h of wasted work if another agent picks up the same bead

**Option C: Combine — heartbeat keeps claims alive, reaper releases stale ones**

Best of both worlds:
1. Post-tool hook updates `claimed_at` every 60s (Option A)
2. Discovery scan (which already runs) reaps claims where `claimed_at` is >30min stale
3. Reduce TTL from 2h to 30min since heartbeat keeps active claims fresh

- (+) Faster recovery (30min vs 2h)
- (+) Active agents never lose claims
- (-) More moving parts

**Option D: Session-end hook release (explicit but unreliable)**

```bash
# In Notification hook (session end):
if [[ -n "$CLAVAIN_BEAD_ID" ]]; then
    bd update "$CLAVAIN_BEAD_ID" --status=open --assignee="" 2>/dev/null || true
fi
```

- (+) Immediate release on clean exit
- (-) Process may be killed before hook runs
- (-) Doesn't help with crashes

### Recommended: Option C

Heartbeat + reduced TTL. The heartbeat is cheap (one `bd set-state` per minute), and the reaper is already built into discovery. Just reduce the TTL from 2h to 30min.

### Tradeoffs

- (+) Claims auto-expire in bounded time
- (+) No new infrastructure — reuses existing discovery reaper
- (-) 30min is still a long time for wasted parallel work
- (-) Post-tool heartbeat doesn't fire during long-running operations (e.g., Oracle calls)

### Open Questions

1. What TTL? 30min is a compromise between false-positive reaping (agent is alive but slow) and wasted work.
2. Should the heartbeat be in interphase (owns beads workflow) or interstat (already has post-tool hook)?
3. Should `bd update --claim` respect an existing claim from the *same* actor? Currently `bd update --claim` succeeds if assignee matches actor — is that correct for re-entrant sessions?

## Cross-Cutting Concerns

### Dolt Lock Contention

The biggest architectural risk. Dolt's process-exclusive lock means:
- Two agents claiming simultaneously → one gets 15s timeout error
- Heartbeat from 3 agents → serialized, each waiting for lock
- `bd who` during active claims → may block

**Mitigation options:**
1. Accept it — contention is rare in practice (agents claim different beads)
2. Move claim state to a separate lightweight store (file-based, not dolt)
3. Use intercore coordination locks (`ic coordination reserve`) as the claiming primitive instead of `bd update --claim`

Option 3 is interesting: intercore already has row-level locking via SQLite WAL mode. The coordination subsystem was built for exactly this pattern (file reservations with heartbeat TTL). Extending it to bead reservations would avoid the dolt contention entirely.

### Identity Unification

Currently three identity systems:
- `BD_ACTOR` (beads) — git user.name, same for all agents
- `CLAUDE_SESSION_ID` (clavain) — UUID, unique but opaque
- mcp-agent-mail name (intermute) — human-readable, unique per project+session

**Proposal:** Bridge mcp-agent-mail name → BD_ACTOR:
1. Session-start: call `register_agent` → get assigned name (e.g., "StrictMajor")
2. Set `BD_ACTOR="StrictMajor"`
3. All `bd` operations now attributed to a readable name
4. `bd who` shows "StrictMajor" not "a1b2c3d4"

Dependency: mcp-agent-mail must be running. Fall back to session ID prefix if unavailable.

### Relationship to Interlock

Interlock handles **file** reservations. Beads handles **work item** claims. These are complementary:
- Agent claims bead `iv-xesrg` (work intent)
- Agent reserves `os/clavain/.github/workflows/plugin-tests.yml` (file intent)

No bridge needed — they're different scopes. But the UX should be consistent: if you claimed the bead, you should be able to reserve its files without extra ceremony.

## Summary: Phased Rollout

| Phase | Scope | Effort | Impact |
|-------|-------|--------|--------|
| **Layer 1** | Wire `--claim`, set BD_ACTOR, update route/discovery | 2h | Collision detection works |
| **Layer 2** | `bd who` command, discovery shows claim owner | 3h | Visibility of who's doing what |
| **Layer 3** | Heartbeat in post-tool hook, reduce TTL to 30min | 2h | Stale claims auto-release |

Total: ~7h across all three layers. Each is independently valuable and can ship separately.
