# PRD: Interspect F2 — Pattern Detection + Propose Flow

**Bead:** iv-8fgu

## Problem

Interspect collects evidence about agent behavior but has no automated way to surface routing-eligible patterns to the user. The `/interspect:propose` command spec exists but the library functions that power it are missing. Users must manually analyze evidence to decide which agents to exclude.

## Solution

Implement the pattern detection pipeline and propose flow: library functions that query classified patterns, filter for routing/overlay eligibility, and a propose writer that creates `"propose"` entries in routing-overrides.json. The `/interspect:propose` command orchestrates the full UX.

## Features

### F1: Pattern Detection Helpers
**What:** Convenience functions that wrap `_interspect_get_classified_patterns()` with eligibility filtering.
**Acceptance criteria:**
- [ ] `_interspect_get_routing_eligible()` returns agents with "ready" classification, >=80% agent_wrong, not blacklisted, not already overridden
- [ ] `_interspect_get_overlay_eligible()` returns agents with "ready" classification, 40-79% agent_wrong, checking existing overlays
- [ ] Both return pipe-delimited output: `agent|event_count|session_count|project_count|agent_wrong_pct`
- [ ] Both handle empty evidence gracefully (return empty, no errors)

### F2: Propose Writer
**What:** Write `"propose"` action entries to routing-overrides.json using the existing atomic write pattern.
**Acceptance criteria:**
- [ ] `_interspect_apply_propose()` writes an override with `action: "propose"` (not "exclude")
- [ ] Dedup check inside flock: skip if agent already has ANY override (propose or exclude)
- [ ] Git commit with descriptive message: `[interspect] Propose excluding <agent>`
- [ ] No canary monitoring or modification record (proposals are informational)
- [ ] Returns SUCCESS with commit SHA on success

### F3: Integration Tests
**What:** Automated tests for the full detect → propose → verify pipeline.
**Acceptance criteria:**
- [ ] Test: populate evidence DB → get_routing_eligible returns expected agents
- [ ] Test: apply_propose writes correct JSON with "propose" action
- [ ] Test: propose dedup prevents duplicate proposals
- [ ] Test: already-excluded agent is not proposed
- [ ] Test: cross-cutting agent detection returns correct agents
- [ ] Test: overlay-eligible filtering at 40-79% band

## Non-goals

- `/interspect:approve` command (F3: iv-gkj9)
- Overlay auto-draft via LLM (nice-to-have for later)
- Canary monitoring for proposals
- Changes to flux-drive SKILL.md (already handles "propose" from iv-r6mf)

## Dependencies

- iv-r6mf (shipped): routing-overrides.json schema with "propose" action
- lib-interspect.sh: existing pattern classification + override writer infrastructure

## Open Questions

None — the command spec and library infrastructure are well-defined.
