# Goal ff7fd1a1 — journal (Next-goal lineage counterweight)

Orchestrating session aa2bb078 (Fable 5.1) mints, briefs, publishes, and closes; the code is one fresh headless session (pilot L) under the live gate (clavain 0.6.305), launched outside the sandbox and waited on by pid, per the lesson of goal c4cda02c.

## Pilot

| Pilot | Work | Session | Executor commit | Validator | Gauge defects (plan author's) | Beyond the gauge | Register rows |
|---|---|---|---|---|---|---|---|
| L | `next-goal-verify.sh --recommend/--beat`: lineage of the last four closed goals from the ic stores (BeadID plus `ic_goal_id:` labels, walked to root epics), refusal at two matches, `--beat` override, unknown lineage never counts, no ic = unavailable; seven bats tests; `commands/next-goal.md` | 3807a93b | 432ea46 (strike 1) | PASS (strike 1); all 8 VERIFY blocks re-run (bats 19 ok, sibling suites 44 ok, structural 903, both live demos true) | none (lint rc 0 on first save, 14 edits verbatim); two deviations stated in the plan: the whole-run refusal enters `disqualified` as a string because the provenance library joins that array, and one existing schema assertion moved from v1 to v2 | 10 registered: goals not deduped by ID across roots fronting one store; the window is global across projects (charter interpretation); `--recommend`/`--beat` are self-reports to a Stop hook that reads only `.ok` and `.disqualified`, and a successful override leaves the hook silent; `. + $ro` overwrites an in_progress/blocked pick's status reason; the all-in-lineage refusal runs only without `--recommend`, which the doc example always passes; a non-numeric MIN/WINDOW env breaks `--argjson` into an empty receipt; `ROOT_MEMO` keyed by id, not (root, id); in_progress/blocked `--beat` refused but undocumented; the live-verify steps left an untracked 1.2M `.beads/` store at the Clavain root (removed by the orchestrating session after checking it was untracked, empty, and born after the pilot's launch). All to the residuals bead labeled `ic_goal_id:ff7fd1a1` | 12 (all rc 0) |

## Live demonstrations

Run by the orchestrating session from `~/projects/Sylveste` against the real stores after 432ea46, before the publish (`CLAVAIN_PROVENANCE_DISABLE=1` so the demos do not overwrite this session's receipt).

Refused (exit 3): `next-goal-verify.sh --recommend Sylveste-yibw.15 Sylveste-yibw.15 Sylveste-balk`

```json
{"ok":false,"disqualified":["Sylveste-yibw.15"],"lineage":{"verdict":"disqualified","reason":"continues the lineage of 2 of the last 4 closed goals (c4cda02c, c60de386, epic Sylveste-yibw) — name the open out-of-lineage candidate it beat with --beat, or recommend that one","threshold":{"window":4,"min":2},"window":[{"id":"fdaae66d","roots":[],"unknown":true},{"id":"c4cda02c","roots":["Sylveste-yibw"],"unknown":false},{"id":"c60de386","roots":["Sylveste-yibw"],"unknown":false},{"id":"1b53da77","roots":[],"unknown":true}],"candidates":[{"id":"Sylveste-yibw.15","root_epic":"Sylveste-yibw","streak":["c4cda02c","c60de386"],"in_streak":true},{"id":"Sylveste-balk","root_epic":"Sylveste-balk","streak":[],"in_streak":false}]}}
```

Allowed (exit 0): `next-goal-verify.sh --recommend Sylveste-balk Sylveste-balk Sylveste-yibw.15`

```json
{"ok":true,"disqualified":[],"warnings":["Sylveste-yibw.15"],"lineage":{"verdict":"ok","reason":"Sylveste-balk (epic Sylveste-balk) is outside the lineage of the last 4 closed goals","candidates":[{"id":"Sylveste-balk","root_epic":"Sylveste-balk","streak":[],"in_streak":false},{"id":"Sylveste-yibw.15","root_epic":"Sylveste-yibw","streak":["c4cda02c","c60de386"],"in_streak":true}]}}
```

Two goals in the window (fdaae66d, closed by a sibling session while this goal ran, and 1b53da77, which bound no beads) have unknown lineage and count for nothing, as specified; the refusal rests on exactly the two goals that named Sylveste-yibw. The window is by close time across stores, so the next close in any project evicts 1b53da77 and the refusal then rests on the threshold itself.

## Token profile (execution lanes only)

| Pilot | lane | msgs | output | cache read | ctx/msg | $ equiv |
|---|---|---|---|---|---|---|
| L | main (Fable 5.1) | 16 | 80K | 1.6M | 107K | 6 |
| L | executor (Sonnet 5) | 38 | 10K | 3.1M | 83K | 1 |
| L | validator (Opus 5) | 21 | 4K | 1.5M | 74K | 1 |

Shares for continuity: cost 74%, generated tokens 91%; whole run $9 API-equivalent, $10.72 by Claude Code's accounting. Absolute: 107K per orchestrator message, in line with the two-bead briefs of goal c4cda02c (98–121K).

## Verdict register

Read back from the live register at close: session 3807a93b holds executor replay PASS 1, validator replay PASS 1, validator independent FAIL 10, all against 432ea46, all `--goal ff7fd1a1`. Replays 2 of 2 PASS carried no information; the independent channel carried ten findings, none gate-relevant, all filed.

## Close-out (2026-09-03, 23:45 PDT)

Shipped: Clavain 432ea46 on main; clavain 0.6.306 published from zklw (canary and probe green), Mac cache byte-identical to main for the script, the command doc, and the provenance library. DONE WHEN: script, bats (19), and `commands/next-goal.md` updated; both live demonstrations journaled with their JSON; published and refreshed; the memory rule now points at the check. GATE: silence is not a verdict held (unknown lineage never counted; no ic reports unavailable); threshold and override documented beside the block; 1 spawn, 1 commit, executor and validator on strike 1, code-correct 1/1; the pilot launched outside the sandbox and was waited on by pid (the first waiter's own 15-minute cap expired while the validator ran; the pilot was untouched). Turn budget: 8 stated, about 10 tool-bearing turns used. Applied to itself: the Next-goal block closing this goal was verified with `--recommend` before it was written.
