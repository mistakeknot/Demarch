# Goal 1b53da77 — pilot journal (main-thread offload, instrumented)

Session aa2bb078, 2026-09-03. Pilot window opened 18:06:55Z. Orchestrator: Fable 5.1 main thread at effort xhigh. Executors: Sonnet 5 subagents, fresh context, one plan file each. Validators: Opus 5 subagents, judging only the plan's VERIFY block, then reporting what the gauge missed.

## Pilots

| Pilot | Work | Executor commit | Validator | Gauge defects (orchestrator's) | Beyond the gauge (validator found) |
|---|---|---|---|---|---|
| 1 | interstat meter: Claude 5 pricing rows, message.id dedupe, lane report, profile.py | 50f47b3 → cherry-picked to interstat main as 8672cc3 | PASS | plan asserted branch `main`; checkout was on `sweep/2026-09-02` | last-model attribution overstates Fable 5.1 5.8x (measured); `<synthetic>` at $0 zeroes 30 whole-session rows; structural skills test red at HEAD; `uv run` rewrites uv.lock |
| 1b | dominant-model attribution, never `<synthetic>`; structural test un-redded; `--frozen`; table rebuilt | 4fa4628 (sweep branch; cherry-pick pending validator) | pending | verify asserted a whole-table state that pruned files + a concurrent old-parser writer make unreachable; corrected to a parsed_at-scoped assertion | executor isolated the real subagent-parse-gap root cause: upsert keyed on session+agent_name collapses N files onto one row (Sylveste-balk) |
| 2 | Sylveste-0pk: routing-mode.sh replaces inline seds, doctrine phases protected, bats suite; spawn examples name a model | 1920900 (Clavain main, pushed) | PASS | none | quality→economy not an involution on non-doctrine categories (Sylveste-koeo); `status` hides the dose-guard lines |
| 3 | Sylveste-d3m phase 1: executor shadow mode, parity corpus log, interserve passes `--to auto --class` | d580a35 (Clavain main, pushed) | PASS | none on criteria | shadow mode wrote two rows per dispatch, second with post-fallback `would_route`; resolver log had no dry-run guard |
| 3b | single logging site, pre-fallback would-route, dry-run guard | f12603e (Clavain main, pushed) | PASS | verify line expected a grep count the plan's own comment text could not produce; executor refused to commit until corrected | `off` mode still logs a synthetic `would_route` (filterable by mode) |

Plan-to-execution pass rate this goal: executors applied every plan verbatim (5/5 code-correct); 2 of 5 runs were blocked by a defect in the plan's own VERIFY block, never by the code. That is the doctrine's pilot-1 result reproduced: "the plan's emitted text is simultaneously the artifact and an input to a checker the same author wrote."

Validator value (design-doc Q-A): every one of the five validations passed on criteria, and four of the five surfaced a real defect the verify block did not check, two of which became fix-forward pilots (1b, 3b). Against this goal's data the validator is not "only cost".

## Token profile

`profile.py --session aa2bb078-ee16-4c32-9f97-01ef7dbdec61 --since 2026-09-03T18:06:55Z` (first-line dedupe verified exact: every streamed line of a message carries identical usage, 763/763 checked):

| lane | msgs | output | cache read | $ equiv |
|---|---|---|---|---|
| main (Fable 5.1, 344K/turn) | 38 | 87K | 12.7M | 19 |
| executors + validators (Sonnet 5 / Opus 5 / Haiku) | 275 | 7K | 24.0M | 10 |
| melange review workflow (not execution) | 616 | 10K | 39.8M | 28 |

Execution-only (main vs its executors and validators): main-thread share of API-equivalent cost **65%** (30-day baseline 85%); share of generated tokens **92%** (baseline 95%). **The gate (<=50% generated tokens) is NOT met, and the proposed cost-share replacement is not met either.** A first reading in this journal said 35% cost share; it counted the melange review's agents as offloaded execution and is withdrawn. Reason for the shape of the result: with execution-grade plans the executor copies, so generated tokens follow plan authorship; and the orchestrator's 38 turns at 344K context cost more than every executor and validator combined. Offload alone: 85% -> 65%. Below 50% needs the orchestrator's own context to shrink.

## Melange review

Dispatched 11:08 PT before any pilot ran; finished 14:44 PT after all of them (3h37m: 5 rounds to DRY, codex mirror through its own rounds, parley to equilibrium). Condition item 4 asked for the review before the pilots; it was started before and landed after, so it could not gate the pilot shape — recorded as a partial miss. 48 findings, 43 upheld, 5 refuted, 39 surfaced. Corner: f-041, the interspect verdict register exists and Pattern F never writes to it (fail-open at three layers; schema cannot tell replay from independent confirmation) — these five verdicts exist only in this table. Confirmed by the pilots: plan staleness (pilot 1's branch), isolation (pilot 1b's concurrent old-parser writer), frozen-criteria defects (2 of 5 runs). Refuted by the pilots: "the validator structurally cannot add information". Q-A had the wrong premise: replay adds nothing (5/5 PASS), the second channel adds everything (6 defects). One contested topic for mk: amend or retract the transcribed Q-A sentence (amended in place pending ruling). Synthesis: os/Clavain/docs/research/flux-melange/main-thread-offload-pattern-f/2026-09-03-synthesis.md; equilibrium.md beside it.

## Q1 — pool drawdown

**Q1 start reading (mk, `/usage`, 2026-09-03 ~11:45 PT).** Week (all models) **78%** used; week (Fable) **96%** used; both reset Sep 5 12:00 PT; +50% weekly-limit promo through Sep 13. Session (4h wall, this goal plus the verdict goal before it): $87.79 — Fable 5.1 main $26.61, Sonnet subagents $24.24, Opus subagents $30.21, Haiku $4.10, Fable 5 $2.63 → main-thread cost share **30%**, agreeing with profile.py's 35%. Two facts the API-equivalent view could not show: (1) the Fable sub-cap is the binding constraint — 96% consumed against 78% of the shared pool with two days left, so Fable-main across parallel sessions exhausts the Fable bucket before the week ends while the pool still has headroom; (2) Claude Code bills the main thread's cache writes at the 1-hour-TTL rate (2× base: $20/MTok on Fable 5.1 — the $26.61 reconciles only at that rate) and subagents at the 5-minute rate (1.25×), so profile.py's flat cache-write rate undercounts the main lane by ~$5.6 on this session. Usage-page attribution for the last 24h: 83% from subagent-heavy sessions, 68% while 4+ sessions ran in parallel, 66% at >150K context, 18% from interflux, 11% from workflow subagents. End-of-week reading due before Sep 5 12:00 PT.
