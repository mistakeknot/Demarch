# Interspect F2: Routing-Eligible Pattern Detection + Propose Flow

**Bead:** iv-8fgu

## Context

Interspect F1 (iv-r6mf) shipped the formal JSON Schema for `routing-overrides.json` and the flux-drive reader. The schema supports two actions: `"exclude"` (active) and `"propose"` (informational). The `/interspect:propose` command (`os/clavain/commands/interspect-propose.md`) defines the full UX spec for the propose flow.

**What exists today:**
- **Evidence collection**: `interspect-evidence.sh` hook captures `agent_dispatch` events; `/interspect:correction` captures manual `override` events with reasons (`agent_wrong`, `deprioritized`, `already_fixed`)
- **Pattern classification**: `_interspect_get_classified_patterns()` groups evidence by (source, event, override_reason) and classifies as "ready" / "growing" / "emerging" using counting rules (>=5 events, >=3 sessions, >=2 projects)
- **Routing eligibility check**: `_interspect_is_routing_eligible()` validates agent_wrong_pct >= 80%, checks blacklist, validates agent name
- **Override existence check**: `_interspect_override_exists()` checks routing-overrides.json for existing entries
- **Override writer**: `_interspect_apply_routing_override()` handles the full read-modify-write-commit-record flow inside flock with canary monitoring
- **Overlay writer**: `_interspect_write_overlay()` handles prompt tuning overlays with token budget, sanitization, and canary
- **Schema**: `routing-overrides.schema.json` supports `"propose"` action (informational only, not excluded by flux-drive)

**What's missing (the gap):**
1. No `_interspect_apply_propose()` function — writing `action: "propose"` entries to routing-overrides.json
2. The `/interspect:propose` command exists as spec but has no skill (SKILL.md) implementation
3. No batch proposal orchestration — the command describes multi-select UX but nothing drives it
4. No overlay proposal flow — the 40-79% wrong band is documented but not implemented

## Gap Analysis

The propose flow bridges two existing systems:
- **Input**: Evidence DB (populated by correction hook + evidence hook)
- **Output**: routing-overrides.json (read by flux-drive) + overlay files (read by flux-drive domain injection)

The propose command spec is detailed and well-defined. The implementation work is:

### 1. Library Functions (lib-interspect.sh)

**`_interspect_apply_propose()`** — Write a `"propose"` action entry to routing-overrides.json. Similar to `_interspect_apply_routing_override()` but:
- Action is `"propose"` not `"exclude"`
- No canary monitoring needed (proposal is informational)
- Still needs dedup check (don't propose same agent twice)
- Still needs flock for atomicity
- Lighter weight: no DB modification record or canary record needed

**`_interspect_get_routing_eligible()`** — Convenience wrapper that:
1. Calls `_interspect_get_classified_patterns()`
2. Filters for "ready" classification
3. Filters for `_interspect_is_routing_eligible()`
4. Filters out already-overridden agents
5. Returns eligible agents with their evidence stats

**`_interspect_get_overlay_eligible()`** — Similar but for 40-79% wrong band:
1. Calls `_interspect_get_classified_patterns()`
2. Filters for "ready" classification
3. Filters for agent_wrong_pct 40-79%
4. Checks for existing overlays
5. Returns eligible agents

### 2. Command Enhancement (interspect-propose.md)

The command spec is already comprehensive. The skill needs to:
- Source lib-interspect.sh
- Call the library functions above
- Present results via AskUserQuestion (batch multi-select)
- Handle evidence detail viewing
- Apply overrides/proposals for selected agents
- Handle overlay proposals separately

### 3. Propose vs Exclude Decision

**Option A: Propose-then-approve (two-step)**
- `/interspect:propose` writes `"propose"` entries
- User later runs `/interspect:approve <agent>` to promote propose→exclude
- Pro: Safer, lets user observe before committing
- Con: Extra command, friction may prevent adoption

**Option B: Direct exclude with propose as audit trail**
- `/interspect:propose` shows proposals, user selects, directly applies `"exclude"`
- `"propose"` entries only created if user explicitly defers ("save for later")
- Pro: Matches the command spec (it says "apply overrides for selected agents")
- Con: Less cautious

**Option C: Propose by default, approve on cross-cutting** (Recommended)
- Normal agents: selected → directly applied as `"exclude"` (matches command spec)
- Cross-cutting agents (fd-architecture, fd-quality, fd-safety, fd-correctness): selected → written as `"propose"` first, require explicit second confirmation
- Pro: Balances safety with friction; extra caution only where it matters most
- Con: Slightly more complex flow

## Recommendation

**Option C** — Direct exclude for most agents, propose-first for cross-cutting agents.

The command spec already describes this pattern: cross-cutting agents require "Yes, exclude despite warning" confirmation. We extend this to a two-step flow: propose → approve, where the proposal is visible in `/interspect:status` and triage notes.

## Design Decisions

1. **`_interspect_apply_propose()`** reuses the existing locked write pattern but with `action: "propose"` and no canary/modification records
2. **Propose entries** appear in flux-drive triage as informational: `[proposed: fd-game-design (100% irrelevant)]`
3. **Promotion**: `/interspect:approve <agent>` replaces propose→exclude (future F3 work, not in this bead)
4. **Growing patterns**: Shown as progress indicators, not proposals. Users see what's approaching threshold.
5. **Overlay proposals**: Deferred to a separate step in the command flow (after routing proposals)
6. **Evidence detail viewing**: Query last 5 corrections per agent, format as human-readable summaries

## Scope

**In scope for iv-8fgu:**
- `_interspect_apply_propose()` library function
- `_interspect_get_routing_eligible()` convenience wrapper
- `_interspect_get_overlay_eligible()` convenience wrapper
- Integration test for pattern detection + propose flow
- Update `/interspect:propose` command to call new library functions
- Verify flux-drive reads `"propose"` entries correctly (already handled by iv-r6mf)

**Out of scope:**
- `/interspect:approve` command (F3: iv-gkj9)
- Canary monitoring for proposals (proposals are informational)
- Overlay auto-draft via LLM (command spec describes it but it's a nice-to-have)
- Prompt tuning overlays integration testing (separate from routing overrides)

## Testing Strategy

1. **Unit tests** for `_interspect_get_routing_eligible()` — mock evidence DB with known patterns
2. **Unit tests** for `_interspect_apply_propose()` — verify JSON output, dedup, atomicity
3. **Integration test**: populate evidence → detect patterns → apply propose → verify file
4. **Edge cases**: empty evidence, blacklisted agents, already-overridden agents, cross-cutting agents
