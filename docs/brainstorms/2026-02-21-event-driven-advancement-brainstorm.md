# Event-Driven Advancement: Phase Transitions Trigger Auto-Dispatch

**Bead:** iv-r9j2
**Sprint:** iv-lype
**Date:** 2026-02-21
**Status:** Brainstorm complete

## What We're Building

Make the intercore kernel the **router** for sprint phase transitions — not just a signal emitter. When `ic run advance` fires, it returns the resolved action(s) for the next phase so the caller knows exactly what to do. Today, `sprint_next_step()` in lib-sprint.sh is a bash case statement that maps phases to commands. That logic moves into the kernel's `phase_actions` table, making the route inspectable, overridable, and available to both interactive (sprint skill) and autonomous (hook-based) consumers.

### The Gap Today

```
ic run advance → emits event → SpawnHandler (only fires for "executing")
                              → HookHandler (runs .clavain/hooks/on-phase-advance, 5s timeout)
                              → LogHandler (stderr)

sprint_advance() → calls ic run advance → parses result → returns to sprint SKILL.md
                                                           → SKILL.md calls sprint_next_step()
                                                           → case statement: phase → command name
                                                           → SKILL.md dispatches the command
```

**Problems:**
1. Routing table is in bash, invisible to kernel — `ic run status` can't show what happens next
2. SpawnHandler is hardcoded to "executing" only — no generalization
3. No late-binding for artifact references — sprint skill manually passes paths
4. No way to override routing mid-sprint without editing bash code
5. Interactive and autonomous modes share no routing infrastructure

### The Target

```
ic run create → registers phase_actions (templates with ${artifact:*} placeholders)

ic run advance → transitions phase (atomic, gated)
              → resolves phase_actions for to_phase
              → replaces ${artifact:plan} with actual path from run_artifacts
              → returns resolved actions in JSON result
              → fires PhaseEventCallback with actions in event payload

Interactive path:
  sprint_advance() → parses actions from ic run advance result
                   → returns action to sprint SKILL.md
                   → SKILL.md dispatches (replaces sprint_next_step case statement)

Autonomous path:
  on-phase-advance hook → reads actions from event JSON
                        → dispatches agents / commands directly
                        → no sprint skill involvement

Action.mode field → "interactive" (default) vs "autonomous" controls which path fires
```

## Why This Approach

### Hybrid registration (template-at-create + resolve-at-advance)

**Rejected alternatives:**
- **At-create only**: Can't reference artifacts that don't exist yet (plan path unknown at run creation). Would need placeholder resolution anyway.
- **Lazy registration only**: Route is invisible until each phase registers its successor. If a custom chain skips a phase, the registrar never runs. More surface area for ordering bugs.

**Hybrid wins:**
- Full route visible at `ic run status` from creation — the entire lifecycle is inspectable
- `${artifact:plan}` resolves at advance time from `run_artifacts` table — no early binding needed
- `ic run action update` provides mid-sprint override with audit trail
- Custom phase chains get custom actions atomically in one `ic run create` call

### Layered consumer (sprint skill + hook)

**Why both:**
- Interactive sessions (human in Claude Code) need the sprint skill to present options, handle errors, and ask for input on gate failures
- Autonomous runs (Codex dispatches, CI pipelines, portfolio relay) need the hook to auto-dispatch without human involvement
- The `mode` field on phase_actions controls which path fires — no code changes needed to switch between interactive and autonomous operation

## Key Decisions

1. **Routing lives in kernel** — `phase_actions` table in intercore schema, not bash case statement
2. **Hybrid registration** — Templates registered at run create, resolved at advance time
3. **Template variables are a closed set** — `${artifact:<type>}`, `${run_id}`, `${project_dir}` only. No general-purpose templating.
4. **Layered consumers** — Sprint skill for interactive, hook for autonomous. Action `mode` field controls routing.
5. **`ic run action update`** — Mid-sprint override with audit trail (escape hatch for dynamic routing)
6. **Backward compatible** — If no phase_actions exist for a phase, `ic run advance` returns no actions. Sprint skill falls back to `sprint_next_step()` during migration.
7. **SpawnHandler generalization** — Current hardcoded "executing" filter becomes one entry in phase_actions (type=spawn). SpawnHandler can eventually be retired or made action-aware.

## Schema Design

```sql
CREATE TABLE IF NOT EXISTS phase_actions (
  id INTEGER PRIMARY KEY,
  run_id TEXT NOT NULL REFERENCES runs(id),
  phase TEXT NOT NULL,              -- the to_phase that triggers this action
  action_type TEXT NOT NULL DEFAULT 'command',  -- command | spawn | hook
  command TEXT NOT NULL,            -- /clavain:work, /interflux:flux-drive, etc.
  args TEXT,                        -- JSON array, may contain ${artifact:<type>} placeholders
  mode TEXT NOT NULL DEFAULT 'interactive',  -- interactive | autonomous | both
  priority INTEGER DEFAULT 0,      -- ordering when multiple actions per phase
  created_at INTEGER DEFAULT (unixepoch()),
  updated_at INTEGER DEFAULT (unixepoch()),
  UNIQUE(run_id, phase, command)    -- prevent duplicate registrations
);
```

### Default Action Template (Standard Sprint)

```json
{
  "brainstorm":       {"command": "/clavain:strategy", "mode": "interactive"},
  "strategized":      {"command": "/clavain:write-plan", "mode": "interactive"},
  "planned":          {"command": "/interflux:flux-drive", "args": ["${artifact:plan}"], "mode": "interactive"},
  "plan-reviewed":    {"command": "/clavain:work", "args": ["${artifact:plan}"], "mode": "both"},
  "executing":        {"command": "/clavain:quality-gates", "mode": "interactive"},
  "shipping":         {"command": "/clavain:reflect", "mode": "interactive"}
}
```

### CLI Surface

```bash
# Register actions at run create (new --actions flag)
ic run create --project=. --goal="..." --actions='{"planned": {"command": "/interflux:flux-drive", "args": ["${artifact:plan}"]}}'

# Or register individually
ic run action add <run_id> --phase=planned --command=/interflux:flux-drive --args='["${artifact:plan}"]'

# List actions for a run
ic run action list <run_id> [--phase=<p>]

# Override mid-sprint
ic run action update <run_id> --phase=planned --command=/clavain:interpeer --args='["${artifact:plan}"]'

# ic run advance output gains actions array
ic run advance <run_id>
# → {"advanced": true, "from_phase": "strategized", "to_phase": "planned",
#    "actions": [{"type": "command", "command": "/interflux:flux-drive", "args": ["docs/plans/2026-02-21-foo.md"], "mode": "interactive"}]}
```

### Template Variable Resolution

At advance time, when resolving `${artifact:<type>}`:
1. Query `run_artifacts WHERE run_id=? AND type=?` (or `phase=? AND type IS NULL`)
2. If found: substitute the artifact's `path` column value
3. If not found: leave the placeholder — caller sees `${artifact:plan}` and knows the artifact hasn't been registered yet. This is an error the caller can surface.

Closed set of variables:
- `${artifact:<type>}` — resolves from `run_artifacts` table
- `${run_id}` — current run ID
- `${project_dir}` — project directory from runs table

## Migration Path

1. **Phase 1 (this sprint):** Add `phase_actions` table + `ic run action` CLI + resolution in `ic run advance` output. Sprint skill reads actions from advance result but falls back to `sprint_next_step()` if no actions exist.
2. **Phase 2 (next sprint):** `sprint_create` populates default actions. `sprint_next_step()` reads from kernel instead of case statement. Deprecate bash case statement.
3. **Phase 3 (future):** Hook-based autonomous dispatch. SpawnHandler becomes an action consumer. Portfolio relay dispatches cross-project actions.

## Open Questions

1. **Should `ic run advance` auto-dispatch autonomous actions?** Or should it always return them and let the hook handler dispatch? (Leaning toward: always return, let consumers decide — separation of concerns.)
2. **Action execution tracking** — Should we record whether an action was dispatched/completed? (Leaning toward: yes, via dispatch_events linkage, but Phase 2.)

## Risks

- **Template resolution failure**: If `${artifact:plan}` can't resolve because no artifact was registered, advance succeeds but action args are unresolved. Mitigation: caller checks for unresolved placeholders and surfaces error.
- **Schema migration**: Adding a table is additive-only (safe). No existing data changes.
- **Backward compatibility**: No actions = no change in behavior. Sprint skill falls back to existing routing.

## Out of Scope

- General-purpose workflow DSL (explicit non-goal per intercore roadmap)
- Auto-generating prompts or agent configurations (that's Clavain OS layer)
- Hook auto-dispatch implementation (Phase 3, not this sprint)
