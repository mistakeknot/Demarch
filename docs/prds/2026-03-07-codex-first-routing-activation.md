---
artifact_type: prd
bead: iv-2s7k7
stage: strategized
---

# Codex-First Routing Activation

**Bead:** iv-2s7k7
**Date:** 2026-03-07

## Problem

All 4 layers of the Codex-first routing system are implemented but never tested or activated. The delegation mode sits at `shadow` (advisory), the evidence pipeline may not record outcomes, and the calibration feedback loop has never run with real data.

## Goal

Verify the entire pipeline works end-to-end, fix any breaks, and activate enforce mode so Claude automatically delegates eligible work to Codex CLI.

## Features

### F1: Pipeline Verification

Manually test each integration point:
- codex-delegate agent invocation from Claude
- dispatch.sh execution of Codex CLI from subagent context
- Verdict sidecar creation and parsing
- delegation_outcome event recording to interspect.db
- Calibration data generation
- Session-start policy injection with live stats

### F2: Pipeline Fixes

Fix any breaks discovered during verification:
- Codex CLI availability check (is it installed and authenticated?)
- DB path resolution in subagent context
- Outcome recording reliability
- Any missing wiring between components

### F3: Mode Activation

Switch `delegation.mode` from `shadow` to `enforce` in routing.yaml, verified by a real session that demonstrates automatic delegation.

## Non-Goals

- Layer 4 (PreToolUse advisory gate) — explicitly deferred
- Automated testing of the delegation pipeline
- Calibration threshold tuning (needs real usage data first)
- Token savings measurement (needs baseline data first)

## Success Metrics

- At least 1 real delegation_outcome event in interspect.db
- `/interspect:delegation-status` shows real data
- delegation.mode = `enforce` in routing.yaml
- Session-start context includes delegation policy with stats

## Risks

| Risk | Mitigation |
|------|------------|
| Codex CLI not installed | Check `command -v codex`, document as prerequisite |
| Pipeline has multiple breaks | Fix incrementally, each layer independently testable |
| Enforce mode too aggressive | Can revert to shadow with one-line config change |
