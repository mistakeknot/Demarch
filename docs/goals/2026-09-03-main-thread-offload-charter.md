# Main-thread offload, instrumented: make the routing doctrine govern the tokens it was written for

Ratified by mk on 2026-09-03 (pasted /goal text, recorded verbatim in the condition file beside this charter, with one amendment mk accepted: Sylveste-0pk folded into the meter-fix clause). Chosen over the tripwire goal (mk-f0mz + Sylveste-55bc) because it changes the 85% of spend rather than the 15%.

## Why

A 30-day transcript profile (2026-08-04..09-03, 87K assistant messages, ~$13.9K API-equivalent) shows the main thread carries 85% of spend and 95% of generated tokens. The routing table in `os/Clavain/config/routing.yaml` and the doctrine in `commands/model-routing.md` (v2, melange-derived 2026-07-27) route execution to Sonnet, but they only apply to subagent spawns. Sonnet subagents generated 2.1M tokens in the window; the main thread generated 51.7M. The doctrine's Pattern F (execution routing) names no integration owner, and its Q1 (Fable-main vs Opus-main dose) has been open since July because nothing measures pool drawdown. Meanwhile interstat parsed 190 of 804 subagent runs and prices Fable at Opus rates, so no routing change can currently be graded.

## Scope

In:
- The meter: `interverse/interstat/scripts/cost.py` pricing rows for Opus 5 / Fable 5 / Fable 5.1 / Sonnet 5 with cache-read and cache-write priced separately; the subagent parse gap diagnosed and closed or explained; a one-command per-goal token profile (main vs subagent, by model, context per turn) checked into interstat; Sylveste-0pk (economy|quality presets flattening the v2 phase overrides).
- Spawn defaults: a settings-level default subagent model of sonnet; the unpinned spawn sites in Clavain and interflux commands/skills and the unpinned agent files pinned or documented as deliberate frontier-in-the-loop.
- Three real goals through the offload shape (Fable main thread as thin orchestrator; execution and test loops in fresh-context Sonnet subagents or the codex lane; Opus validation against frozen criteria), each journaled with its token profile.
- One flux-melange design review of the offload architecture (Pattern F, with a named integration owner) before the pilots.
- Pool drawdown from `/usage` at start and end of the week, recorded against the API-equivalent profile; doctrine Q1 closed on data or left explicitly open with the number that exists.
- `commands/model-routing.md` amended with the measured result.

Out:
- Re-deriving the per-stage model table (already melange-derived, v2).
- The local-model cascade (`local_routing_shadow` is empty; separate goal).
- The tripwire beads mk-f0mz and Sylveste-55bc as deliverables.
- Autocompact threshold changes beyond one measured trial.
- Effort tuning (stays xhigh on the frontier thread).

## Gates

1. Main-thread share of generated tokens on the three pilots falls from ~95% to <=50%.
2. Plan-to-execution pass rate does not drop below the measured 0.909 (n=11). A cheaper goal that ships worse is a failure, not a saving.
3. No synthetic pilots: if three suitable real goals are not available in the window, run what is and say so.
4. The meter is fixed before any pilot is graded.

## Interpretations recorded at mint

- "Three real goals": the goal's own execution-grade items qualify as pilot workloads — the meter fix, Sylveste-0pk, and Sylveste-d3m phase 1 (shadow wiring of `--to auto --class` across Clavain dispatch) are real open work with judgeable acceptance, and running them through plan → Sonnet execute → Opus validate makes the goal its own first customer. If a better-shaped real goal arrives mid-window it may substitute.
- "Pool drawdown from /usage": the agent cannot read `/usage`; mk supplies two readings (start of window, end of window). Without them Q1 stays open and the charter records the API-equivalent number alone.
- "Named integration owner": a person or a standing session role recorded in `model-routing.md`, not a bead assignee.
- "Default subagent model at the settings level": whichever Claude Code setting or environment variable makes unpinned `Agent` spawns resolve to sonnet without touching each call site; verified by a spawn with no model param reporting sonnet.

## Completion condition

See the condition file. Or stop after 14 turns.

## Successor obligations

Whatever the three profiles show is still on the main thread after offload (likely: context hygiene / autocompact as its own measured goal), the local-model cascade if the shadow table gets its first rows, and the tripwire pair in the next estate pass.

## Close (2026-09-03)

DONE WHEN met: meter fixed and committed (interstat 8672cc3, 40b7f85); spawn default set (`CLAUDE_CODE_SUBAGENT_MODEL=sonnet`, both settings files); three pilots plus two fix-forwards journaled with profiles (Clavain 1920900, d580a35, f12603e); melange review filed; Q1 has a start number (one account: week 78% / Fable 96%, main-thread cost share 30% of the session by Claude Code's own accounting); doctrine amended. GATE not met: execution-only main-thread share of generated tokens 92% (limit 50%), cost share 65% (baseline 85%). Plan-to-execution pass rate held: 5/5 executor runs code-correct; the two blocked runs were gauge defects in the orchestrator's plans. Condition item 4 partially missed: the melange was dispatched before the pilots but landed after them. Gate verdict and the proposed replacement metric are mk's to rule; nothing in this close redefines the gate.
