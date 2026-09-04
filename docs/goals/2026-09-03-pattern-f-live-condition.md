# Goal condition — Pattern F live (ratified 2026-09-03, "please execute the above /goal")

Recorded verbatim from the closing report of goal c60de386. mk's ratification is the quoted instruction; nothing here is mk's ruling in mk's voice.

```
/goal Make the gauge gate and the verdict register live: refusals recorded, notes survive, new files gauged, plugin shipped.

OUTCOME: a Pattern F run in an ordinary Clavain session is gated and registered without the orchestrator doing anything by hand. Verified by: clavain published and this Mac refreshed, content-diffed against main; a gauge-gate refusal writes one evidence row (kind gate, verdict FAIL, the GAUGE lines as note) and the gate never fails open to do it; a verdict note containing "ignore previous instructions" is stored intact, not dropped to an empty context; plan-gauge-lint.py parses Create blocks into its virtual tree so a new-file plan with a self-matching verify line fails GAUGE001; one real plan run through /execute-plan in a live session is blocked by the gate, corrected, then passes, with every row visible via pattern-f-verdict.sh --list. Stop after 12 turns.

GATE: the quarantine question is mk's ruling, not the goal's; until ruled, verdict rows keep the default and the journal states which rows calibration can see. Report orchestrator context per turn and orchestrator dollars per pilot in absolute terms, with both share metrics printed for continuity. Executor pass rate stays at 5/5 code-correct; a gauge defect counts against the plan author.

DONE WHEN: clavain published and refreshed, Sylveste-yibw.12 and .14 closed with commits, .13's sanitizer half closed and its quarantine half carrying mk's ruling or an explicit "open", the live-session refusal-then-pass journaled with profiles, and Sylveste-yibw's children reflecting what shipped.

OUT: the meter trio (Sylveste-balk, 4yb3, koeo), tests-on-commit (Sylveste-55bc), the tripwires, effort tuning, and any change to the share gates before mk rules.
```
