# Next-goal lineage counterweight: self-succession fails verification

Ratified by mk on 2026-09-03 by reference ("great, please execute the above as the next /goal") after asking, of goal c4cda02c's closing recommendation, "is this really the best next goal?" and then "how do we stop these incorrect goal recommendations? i thought we made fixes to this." The condition file beside this charter carries the goal-shaped rendering.

## Why

Three Pattern F goals in a row (1b53da77, c60de386, c4cda02c) each recommended the next, and the fourth recommendation passed every existing check: the provenance receipt (a tracker answered), the freshness gate (every cited bead open), the shape lint, the tradeoffs rule. It was still wrong, because the in-project rule derives candidates from the just-closed epic's children and residuals, which is recency by construction, and nothing asks whether the pick beats the best open item elsewhere. The existing gates verify that what a block cites is real and live; none asks whether it is the right thing, and none notices that a candidate has the same parent as the last three goals. A memory rule is the wrong place for the counterweight: the failure is a context-rich one that happens at the end of long sessions, exactly when a rule held in memory is least likely to be applied. The check has to be mechanical, like the freshness gate before it.

## Scope

In:
- `scripts/next-goal-verify.sh` gains `--recommend <id>` and `--beat <id>`, reads the closed goals of every discovered root's ic store (newest first, a window of four), derives each goal's lineage as the root epics of its bound beads (`BeadID` from the goal record, plus beads labeled `ic_goal_id:<goal>`, walked to their root through `parent`), and derives each candidate's root epic the same way. A recommendation whose root epic matches the lineage of at least two goals in the window is disqualified with the streak named, unless `--beat` names a candidate in the same run that is open and outside that lineage. When every candidate in the run shares the streak lineage, the run is disqualified with a reason that says to add one from `next-goal-candidates.sh` outside the named epic. A goal whose lineage cannot be derived (no ic on PATH, no bound beads) is reported as unknown and never counted as a match; when ic answered nothing anywhere, the lineage section reports unavailable and the rest of the verdict stands.
- Bats tests with stubbed `bd` and `ic`: streak refused; `--beat` with a valid out-of-lineage candidate allows; `--beat` naming an in-lineage or closed candidate does not; all-in-lineage run disqualified; unknown lineage not counted; missing ic reports unavailable, exit 0.
- `commands/next-goal.md` documents the rule, the window, the threshold, and the override.
- Two demonstrations on the live store, journaled with their JSON.
- clavain published from zklw and refreshed here with a content diff.
- The memory rule `feedback_next_goal_same_project` points at the check instead of carrying the proposal.

Out: the candidate pool, the Stop hook's throttle and wording, any leverage-line requirement, Pattern F residuals, the interstat meter trio.

## Gates

1. Silence is not a verdict: fail open only when a store or tracker did not answer.
2. The threshold (2 of the last 4) and the override are documented beside the block; changing them is a doc change, not a hidden constant.
3. Executor pass rate 5/5 code-correct; a gauge defect counts against the plan author. One fresh-session pilot under the live gate, launched outside the sandbox and waited on by pid.

## Interpretations recorded at mint

- "lineage": the root epic of a bead, found by following `parent` until null (depth capped at 8). A top-level bead is its own root.
- "bound beads" of a goal: the goal record's `BeadID` when non-null, plus every bead that carries the label `ic_goal_id:<goal id>` in any discovered root (`bd list --label … --all --json`).
- "the four most-recent closed goals": across the ic stores of every discovered root, merged and sorted by `ClosedAt` descending; goals from other projects in the window simply do not match.
- "demonstrated on the live store": run from `~/projects/Sylveste` with `--recommend Sylveste-yibw.15` (expected disqualified, streak c60de386 + c4cda02c) and `--recommend Sylveste-balk Sylveste-yibw.15` (expected ok for balk), JSON pasted into the journal.

## Completion condition

See the condition file. Or stop after 8 turns.

## Close (2026-09-03)

DONE WHEN met: `next-goal-verify.sh` v2 with `--recommend`/`--beat` and the lineage section, 19 bats tests, `commands/next-goal.md` updated (Clavain 432ea46); the refusal and the allowance demonstrated on the live stores and journaled with their JSON; clavain 0.6.306 published and refreshed, content-diffed; the in-project memory rule now carries the mechanical check in place of the proposal. GATE held. Executor and validator on strike 1; ten independent findings filed to the residuals bead labeled `ic_goal_id:ff7fd1a1`, none gate-relevant. Turn budget overrun: about 10 tool-bearing turns against 8, two of them a waiter cap that expired under a live validator. Interpretations held as recorded at mint.

## Successor obligations

The residuals bead (dedupe by goal ID across roots, append rather than overwrite the pick's status reason, numeric guard on the env thresholds, `ROOT_MEMO` by root and id, doc alignment for in_progress/blocked `--beat`); the Stop hook reads only `.ok`/`.disqualified`, so a successful override is invisible to it; the window is global across projects by design and may deserve a per-project view later.
