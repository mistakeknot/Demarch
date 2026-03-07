---
artifact_type: brainstorm
bead: iv-2s7k7
stage: brainstorm
---

# Codex-First Routing: Activation Sprint

**Bead:** iv-2s7k7
**Date:** 2026-03-07

## Reframing

The original bead describes "Build a 3-layer system" — but investigation reveals all 3 layers (plus a 4th) already exist. This is the same "packaging/activation gap" pattern seen in iv-zsio (interphase discovery) and iv-godia (routing decisions). The infrastructure is built; it's never been tested end-to-end or activated.

## What Already Exists

| Layer | Component | File | Status |
|-------|-----------|------|--------|
| L1 | codex-delegate agent | `os/clavain/agents/workflow/codex-delegate.md` | Built, 152 lines |
| L2 | Session-start policy injection | `os/clavain/hooks/session-start.sh:190-225` | Built, reads calibration data, injects policy with live stats, survives all shedding levels |
| L3a | Interspect delegation events | `interverse/interspect/hooks/lib-interspect.sh` | `interspect-delegation` in allowlist, `delegation_outcome` event schema defined |
| L3b | Calibration command | `interverse/interspect/commands/calibrate.md` | Built, computes per-category pass rates, writes `delegation-calibration.json` |
| L3c | Delegation status command | `interverse/interspect/commands/delegation-status.md` | Built, full reporting dashboard |
| L4 | Advisory gate (PreToolUse) | Not built | Explicitly deferred — not needed for activation |
| Config | routing.yaml delegation section | `os/clavain/config/routing.yaml:178-199` | Built, mode=shadow, categories defined, complexity ceiling C3, min pass rate 0.70 |

## What's Actually Needed

### 1. End-to-End Verification

**Test the full pipeline manually:**
1. Invoke codex-delegate agent with a simple task
2. Verify dispatch.sh executes Codex CLI successfully
3. Verify verdict sidecar is written
4. Verify delegation_outcome event is recorded in interspect.db
5. Run `/interspect:calibrate` — verify delegation-calibration.json is written
6. Run `/interspect:delegation-status` — verify stats display
7. Start new session — verify delegation policy appears in session context

**Likely failure points:**
- Codex CLI may not be installed or authenticated (`command -v codex`)
- dispatch.sh may need CWD or PATH adjustments in subagent context
- interspect DB path resolution may fail when called from codex-delegate subagent context
- The codex-delegate agent's outcome recording step (Step 6 in its system prompt) may not execute reliably

### 2. Fix Any Pipeline Breaks

Based on the B3 adaptive routing brainstorm (iv-i198), the evidence pipeline has a known issue: PostToolUse `agent_dispatch` events show 0 records in production. Root cause hypothesis is `_interspect_db_path()` failing in hook context. The same issue likely affects delegation outcomes.

### 3. Activate: Shadow -> Enforce

Once the pipeline is verified:
- Change `delegation.mode` from `shadow` to `enforce` in routing.yaml
- This changes the session-start injection language from "Consider using" to "MUST use" for matching categories

### 4. Smoke Test Enforce Mode

Run a real session with enforce mode active:
- Create a simple task (e.g., "add a test for function X")
- Verify Claude routes to codex-delegate instead of handling directly
- Verify the outcome is recorded
- Verify calibration data accumulates

## Scope Assessment

**Original estimate:** Effort 3 (moderate), building a 3-layer system
**Revised estimate:** Effort 2 (simple), verifying an existing pipeline and flipping a config flag

The main risk is that the pipeline has untested integration points that may need fixes. But the components themselves are all built.

## Acceptance Criteria

1. codex-delegate agent dispatches work to Codex CLI successfully
2. delegation_outcome events appear in interspect.db after delegation
3. `/interspect:delegation-status` shows real data
4. `/interspect:calibrate` writes delegation-calibration.json
5. Session-start injects delegation policy with live stats
6. routing.yaml delegation.mode is `enforce`
7. At least one real end-to-end delegation recorded and calibrated
