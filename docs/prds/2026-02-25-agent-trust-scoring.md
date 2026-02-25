# PRD: Agent Trust and Reputation Scoring

**Bead:** iv-ynbh

## Problem

Flux-drive review agents are dispatched based on static triage scores with no learning. Irrelevant agents (e.g., fd-game-design on CLI tools) waste tokens every review cycle, and there is no mechanism to reward agents that consistently produce actionable findings.

## Solution

A closed-loop feedback system: record whether findings are accepted or discarded at resolve-time, compute per-agent per-project trust scores, and apply trust as a multiplier on triage scores so high-precision agents get priority.

## Features

### F1: Evidence Collection (Resolve Hook)

**What:** Hook into `/clavain:resolve` to emit interspect evidence events when findings are acted on.

**Acceptance criteria:**
- [ ] When a finding is fixed (accepted), emit `finding_accepted` event with agent_name, project, finding_id, severity, review_run_id
- [ ] When a finding is dismissed (discarded), emit `finding_discarded` event with the same fields
- [ ] Finding-to-agent mapping reads from synthesis `findings.json` agent attribution
- [ ] Events are written to the interspect evidence table (existing SQLite schema, new event types)
- [ ] Works silently -- no user-visible output, no blocking on write failures

### F2: Trust Computation Engine

**What:** Compute trust scores from evidence with per-agent per-project scoping and global fallback.

**Acceptance criteria:**
- [ ] `trust_score(agent, project)` returns a float 0.05-1.0
- [ ] Per-project score: `accepted / (accepted + discarded)` weighted by severity (P0=4x, P1=2x, P2=1x, P3=0.5x)
- [ ] Global score: same formula across all projects for a given agent
- [ ] Blend formula: `trust = (w * project_score) + ((1-w) * global_score)` where `w = min(1.0, project_reviews / 20)`
- [ ] Floor at 0.05 -- never fully exclude an agent
- [ ] Exponential decay: events older than 30 days get halved weight, 60 days quartered, etc.
- [ ] Scores cached in interspect state; cache invalidated when new evidence arrives
- [ ] Returns 1.0 (neutral) when no evidence exists for the (agent, project) pair AND no global data

### F3: Triage Integration

**What:** Apply trust multiplier to existing flux-drive triage scoring during Phase 1.2 agent selection.

**Acceptance criteria:**
- [ ] Triage scoring reads trust scores for each candidate agent
- [ ] Existing score multiplied by trust_score: `final_score = base_score * trust_multiplier`
- [ ] Trust scores loaded once at triage start (not per-agent query)
- [ ] Documented in flux-drive launch.md Phase 1.2 scoring section
- [ ] When trust data is unavailable (no interspect DB, error), fall back to multiplier=1.0 (no change)
- [ ] Trust multiplier visible in triage debug output (when FLUX_DEBUG=1)

### F4: Trust Observability

**What:** Query and display trust scores for debugging and monitoring.

**Acceptance criteria:**
- [ ] `_interspect_trust_report` function outputs a table: agent | project | trust | reviews | accepted | discarded
- [ ] Accessible via `/clavain:interspect-evidence` or a new `/clavain:trust-status` command
- [ ] Shows both per-project and global scores
- [ ] Highlights agents below 0.3 trust (potential suppression candidates)
- [ ] Works from lib-interspect.sh (no external dependencies)

## Non-goals

- Modifying agent prompts based on trust (future: low-trust agents could get extra guidance)
- Post-dispatch redundancy elimination (that's AgentDropout, iv-qjwz)
- Token budget allocation by trust (future extension)
- Cross-AI trust (Oracle/GPT review agents have different trust dynamics)
- Automatic agent exclusion -- trust only affects priority, never removes an agent

## Dependencies

- Interspect overlay system (iv-vrc4) -- done
- Existing interspect evidence tables in SQLite
- Synthesis `findings.json` with agent attribution (already produced by intersynth)
- `/clavain:resolve` workflow (existing)

## Open Questions

1. **Decay half-life:** 30 days proposed. Should this be configurable per-project?
2. **Severity weights:** P0=4x proposed. Are these the right ratios?
3. **Minimum reviews for project-specific weight:** 20 proposed (full weight). The brainstorm also mentions 5 as a directional signal threshold -- should we start blending at 5?
