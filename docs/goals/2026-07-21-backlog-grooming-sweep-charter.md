---
artifact_type: goal-charter
bead: Sylveste-j4k
complexity: C3
---

# Goal Charter — Backlog Grooming Sweep (>90d tail + priority re-level + epic health memo)

## Why (leverage)

Triage on 2026-07-21 found the Sylveste board materially misleading: 476 open
beads of which 228 are untouched >90 days, 121 carry P0/P1 (mostly March–May
vintage — priority inflation), and the in_progress lane was 81% fiction until
today's hygiene pass. A misleading board corrupts every downstream ritual that
reads it — `bd ready`, next-goal candidate generation, and the freshness checks
mk's feedback requires. One bounded sweep restores signal; hand-triage of 228
beads does not scale. Precedent for the payoff: today's 10-minute spot-check
alone found one shipped-but-open bead (Sylveste-dqo, closed with evidence) and
one under-prioritized recidivist (sylveste-bkrh, bumped P1).

## Scope

**In:**
- Every Sylveste bead with status `open` or `in_progress` and
  `updated_at` < 2026-04-22 (the >90d tail; 228 at charter time) gets exactly
  one verdict: `close-candidate (with evidence)` | `keep` | `re-level proposal`.
- Priority re-level proposals across the full open P0/P1 lanes (121 beads at
  charter time), including the ten April-era P0 strategic epics — proposals
  only, never applied without sign-off.
- Per-epic health memo for all open epics: children done %, last real activity
  (bulk-touch dates like the 2026-07-10 cluster discounted), blockers,
  malformed metadata (e.g. sylveste-18a titled "epic").
- Evidence-graded authority (mk, interview 2026-07-21): the sweep may
  `bd close` autonomously ONLY where acceptance criteria are demonstrably met
  by shipped commits or closed successor beads, with evidence linked in the
  close reason. Everything judgment-based — all other closes and ALL priority
  changes — goes to a sign-off table and is applied only after mk's in-session
  sign-off.
- Beads JSONL re-export + validator-checked push at completion (protocol per
  Sylveste-wch: `bd export > .beads/issues.jsonl`, never `bd backup sync`).

**Out:**
- Epic closes or demotions (flag-only memo — strategic charters are mk's).
- The fresh frontier (beads touched since 2026-04-22) beyond the P0/P1
  re-level lens.
- The 3rod/oyrf Mythos launch re-baseline (separate strategic decision,
  surfaced in triage 2026-07-21).
- Any edits to bead descriptions/titles (verdicts and closes only; malformed
  metadata is flagged, not repaired).

## Acceptance criteria

1. Committed sweep report `docs/research/2026-07-21-backlog-grooming-sweep.md`
   with a verdict line per in-scope stale bead; coverage count reconciled
   against a surfaced jq/bd count of the tail.
2. Evidence-verified closes applied with evidence-linked reasons; zero
   autonomous closes lacking verifiable shipped evidence.
3. Sign-off table surfaced for judgment closes + all re-levels; user-approved
   subset applied in-session; nothing applied without sign-off.
4. Epic health memo covers every open epic.
5. JSONL exported, committed, pushed; `beads_jsonl_dolt_sync ... ok` surfaced.

## Completion condition (literal, for /goal)

The backlog grooming sweep is complete when ALL of the following are surfaced
in-session: (1) a committed report docs/research/2026-07-21-backlog-grooming-sweep.md
containing one verdict line (close-candidate-with-evidence, keep, or
re-level-proposal) for every Sylveste bead that had status open or in_progress
and updated_at before 2026-04-22, with the report's bead count stated and
matching a jq or bd count of that tail surfaced in-session; (2) every
autonomous bd close surfaced with an evidence-linked reason citing a shipped
commit or closed successor bead, and an explicit statement that no autonomous
close lacked such evidence; (3) a sign-off table of proposed judgment closes
and proposed priority re-levels surfaced, with only the user-approved subset
applied via bd commands surfaced in-session; (4) a health memo surfaced
covering every open epic with children-done percentage and last-activity date;
(5) bd export to .beads/issues.jsonl committed and pushed with
beads_jsonl_dolt_sync ok surfaced. Or stop after 50 turns and surface a
partial-coverage accounting of verdicts completed versus the tail count.

## Successor obligations

At close, propose a successor per Goal Cadence. Natural candidates the sweep
will inform: the 3rod/oyrf Mythos launch re-baseline (if triage evidence says
the trigger fired), the Sylveste-ktz small-fix bundle (standing recommendation
from goal 7b585d72), or a second sweep tranche if partial coverage forced the
turn-bound stop. Fan-out execution routes per capability doctrine: bulk
review agents carry an explicit model param (sonnet), judgment synthesis and
evidence verification stay frontier-side.
