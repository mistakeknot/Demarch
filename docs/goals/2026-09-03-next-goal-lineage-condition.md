# Goal condition — Next-goal lineage counterweight (ratified 2026-09-03)

mk ratified by reference ("great, please execute the above as the next /goal") the proposal in the closing exchange of goal c4cda02c: make the recommendation check mechanical, in `next-goal-verify.sh`, so a Next-goal block that merely continues the lineage of the last closed goals is refused unless it names the out-of-lineage item it beat. The text below is the orchestrating session's goal-shaped rendering of that proposal; nothing in it is mk's ruling in mk's voice.

```
/goal Refuse self-succession mechanically: a Next-goal recommendation that only continues the lineage of the last closed goals fails verification unless it names the out-of-lineage item it beat.

OUTCOME: the verify step that every Next-goal block already runs knows the lineage of the goals just closed and refuses a recommendation that repeats it. Verified by: `scripts/next-goal-verify.sh --recommend <id> [--beat <id>]` reads the closed goals from the ic store (newest first), derives each goal's lineage as the root epics of the beads bound to it (BeadID at mint, or beads labeled `ic_goal_id:<goal>`), and disqualifies a recommendation whose root epic matches the lineage of two or more of the four most-recent closed goals (a window, so a sibling session closing an unrelated goal in between does not reset it) unless `--beat` names an open candidate in the same block whose root epic is outside that lineage; a block whose every candidate shares the streak lineage is disqualified outright; unknown lineage (no ic, no bound beads) is reported as unavailable for that goal and never counted as a match; the Stop hook's existing verification warning carries the reason unchanged; demonstrated on the live store: `--recommend Sylveste-yibw.15` refused with the streak named, `--recommend Sylveste-balk` allowed; clavain published and this Mac refreshed, content-diffed against main. Stop after 8 turns.

GATE: silence is not a verdict, as the script already says of trackers: fail open only when the goal store or a tracker did not answer, never on a read that answered; the threshold and the override are documented where the block is documented; executor pass rate 5/5 code-correct, a gauge defect counts against the plan author; pilots launch outside the sandbox and are waited on by pid.

DONE WHEN: the script, its bats tests, and the block's guide are updated on Clavain main; the two live demonstrations are journaled with their JSON; clavain published and refreshed; the in-project memory rule's "proposed, not yet ratified" line replaced by a pointer to the mechanical check.

OUT: the candidate pool in next-goal-candidates.sh, the Stop hook's throttle, a leverage-line requirement (a habit, not a check), Pattern F residuals (Sylveste-yibw.13, .15), the interstat meter trio.
```
