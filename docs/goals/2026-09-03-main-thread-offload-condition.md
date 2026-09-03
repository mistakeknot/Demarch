Main-thread offload, instrumented: make the routing doctrine govern the tokens it was written for.

OUTCOME: execution work leaves the main thread and we can see it. Verified by:
(1) the meter is fixed first -- interstat cost.py carries Opus 5 / Fable 5 /
Fable 5.1 / Sonnet 5 rows with separate cache-read and cache-write rates, the
subagent parse gap (190/804 runs this month) is diagnosed and closed or
explained, a per-goal token profile (main vs subagent, by model, context
per turn) is a one-command report checked into interstat, and Sylveste-0pk
(economy|quality presets flattening the routing-table v2 phase overrides) is
fixed so the table under test cannot be silently flattened; (2) unpinned
spawns stop inheriting the main model -- a default subagent model of sonnet is
set at the settings level, the 48 unpinned spawn sites and 25 unpinned agent
files are pinned or documented as deliberate frontier-in-the-loop; (3) three
real goals run through the offload shape -- Fable main thread as thin
orchestrator, execution and test loops in fresh-context Sonnet subagents or
the codex lane, Opus validation against frozen criteria -- and each is
journaled with its token profile; (4) the offload architecture (Pattern F,
named integration owner) gets one flux-melange design review before the
pilots, not after; (5) pool drawdown is read from /usage at start and end of
the week and recorded against the API-equivalent profile, closing doctrine
Q1 on data.
Stop after 14 turns.

GATE: main-thread share of generated tokens on the three pilots must fall
from ~95% to <=50% AND plan-to-execution pass rate must not drop below the
measured 0.909 -- a cheaper goal that ships worse is a failure, not a saving.
No synthetic pilots: if three suitable real goals are not available in the
window, run what is and say so. Effort stays at xhigh for the frontier thread;
effort tuning is a separate experiment.

DONE WHEN: meter fixed and committed, spawn default set, three pilots
journaled with profiles, melange review filed, Q1 has a number, and the
doctrine section in model-routing.md is amended with the measured result.

OUT: re-deriving the per-stage model table (already melange-derived, v2),
local-model cascade (shadow table is empty; separate goal), the tripwire
beads mk-f0mz and Sylveste-55bc, autocompact threshold changes beyond one
measured trial.
