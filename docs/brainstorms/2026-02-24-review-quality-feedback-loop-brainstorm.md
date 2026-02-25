# Review Quality Feedback Loop

**Bead:** iv-6dqrj
**Phase:** brainstorm (as of 2026-02-25T06:50:33Z)

## What We're Building

A feedback loop that feeds interflux review agent verdict outcomes back into interspect's evidence store. Currently, interspect records agent *dispatch* events (via PostToolUse on Task calls) but never learns how those agents performed. Intersynth aggregates findings into verdict JSON files, but that data dead-ends — interspect's routing/override classification uses only manual override history.

Closing this loop enables interspect to detect underperforming agents automatically (e.g., an agent that consistently produces zero findings or only P2s) and make routing override proposals based on actual verdict impact rather than just human corrections.

## Why This Approach

**PostToolUse hook on intersynth completion (Approach A):**

- Hooks are the right pattern per Demarch's design principle: "Hooks handle per-file automatic enforcement (zero cooperation needed)"
- Zero changes needed in quality-gates or flux-drive callers
- Fires automatically whenever intersynth synthesize-review completes
- Filter on tool_input containing "intersynth:synthesize-review" subagent_type

Rejected alternatives:
- **lib-verdict.sh inline (B):** Couples verdict writing to interspect — wrong dependency direction (intersynth shouldn't know about interspect)
- **Post-synthesis script in callers (C):** Requires every caller to remember to invoke — fragile, violates single enforcement point

## Key Decisions

1. **New event type:** `verdict_recorded` — distinct from `agent_dispatch` and `override`
2. **Evidence schema extension:** Store verdict metadata in the existing `context` JSON column rather than adding new columns — keeps the schema stable and backward compatible
3. **Context JSON payload:**
   ```json
   {
     "verdict_status": "CLEAN|NEEDS_ATTENTION",
     "finding_count": 3,
     "p0_count": 0,
     "p1_count": 1,
     "p2_count": 2,
     "convergence_avg": 1.5,
     "agent": "fd-architecture",
     "detail_path": ".clavain/quality-gates/fd-architecture.md"
   }
   ```
4. **Hook trigger:** PostToolUse on Task tool — filter by `tool_input` matching intersynth subagent_type. Parse the output directory from the tool result to find verdict files.
5. **Interspect query enrichment:** Add `_interspect_get_agent_quality_score()` that aggregates verdict_recorded events to compute a quality score (0-1.0) based on finding frequency, severity distribution, and convergence.

## Open Questions

None — the integration points are well-defined. The main risk is parsing the Task tool output reliably to find the verdict directory, but the quality-gates skill always uses `.clavain/quality-gates/` or `.clavain/verdicts/`.
