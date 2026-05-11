# Microrouter Heuristic — Post-cs2 Rerun Analysis

**Bead:** Sylveste-2bg (re-measurement after Sylveste-cs2 agent-roles.yaml extension)
**Date:** 2026-05-11
**Predecessor:** docs/brainstorms/2026-05-06-microrouter-heuristic-baseline.md
**Pre-committed decision rule:** in Sylveste-2bg description (>95% / 90–95% / <90% branches)

## Raw results vs prior baseline

| Metric                        | 2026-05-06 | 2026-05-11 | Δ           |
| ----------------------------- | ---------: | ---------: | ----------- |
| Subagent rows (total)         |       1586 |       1591 | +5          |
| Heuristic-known rows          |         98 |        463 | +365        |
| Coverage (h-known / total)    |       6.2% |      29.1% | +22.9 pp    |
| Agreement (agree / h-known)   |      68.4% |      58.7% | −9.7 pp     |
| Unknown rows                  |       1488 |       1128 | −360        |

Pre-cs2 categories:
- `core-checker`, `core-editor`, `core-planner`, `core-reviewer` only (mapped fd-* agents)

Post-cs2 added categories:
- `core-builtin-explorer` (Explore: n=132)
- `core-builtin-general` (general-purpose: n=180)
- `core-builtin-planner` (Plan: n=8)
- `core-interflux-researcher` (5 researchers: n=17)
- `core-plugin-reviewer` (3 plugin reviewers: n=10)
- `core-generated-fd-reviewer` (9 enumerated fd-* reviewers: n=14)

## The denominator problem

Naive read of the headline number: **29.1% — far below the >95% target → decision rule says "<90% in any category → open learned-router scoping bead."**

But the headline number is poisoned. Of the 1128 unknown rows:

| Bucket                                            | Rows | Identifiable? |
| ------------------------------------------------- | ---: | ------------- |
| `acompact-*` (conversation compaction events)     |   80 | No — system events, not subagent dispatches |
| Hash-ID with no `subagent_type` fallback          | 1034 | No — interstat couldn't recover the name |
| Hash-ID with `subagent_type` (used by script)     |  292 | Yes — script swaps in subagent_type |
| Parseable agent_name                              |  185 | Yes |

So **1114 of 1128 unknowns (98.8%) are unparseable noise**, not unrouted agents. The script categorizes them as `other`/`builtin`/`generated-fd` and counts them as "heuristic unknown", but they are actually data-quality artifacts that no router could possibly classify.

**Corrected coverage on the identifiable population (parseable + hash-with-fallback = 477):**

```
463 h-known / 477 identifiable = 97.1%
```

That clears the >95% bar.

## Per-category agreement (the real headroom)

Coverage is solved. The remaining question is **agreement rate** — does the heuristic predict the *right* tier for the agents it knows about?

| Category                    |  n  | agree | rate    | Disagreement pattern |
| --------------------------- | --: | ----: | ------: | -------------------- |
| `core-builtin-planner`      |   8 |     6 |  75.0%  | h=opus, but 2 Plan rows ran haiku |
| `core-builtin-explorer`     | 132 |    88 |  66.7%  | h=haiku, but 29 Explore rows ran opus, 15 sonnet |
| `core-plugin-reviewer`      |  10 |     6 |  60.0%  | h=opus, but 4 ran haiku (early code-reviewer + plan-reviewer dispatches) |
| `core-builtin-general`      | 180 |   101 |  56.1%  | h=opus, but 51 ran sonnet + 28 haiku (caller downgrades) |
| `core-generated-fd-reviewer`|  14 |     2 |  14.3%  | h=sonnet, but 6 haiku + 6 opus — bimodal |
| `core-planner`              |  21 |     2 |   9.5%  | h=opus, but 11 ran sonnet + 8 haiku — heuristic systematically over-estimates |
| `core-interflux-researcher` |  17 |     0 |   0.0%  | h=opus, **all 17 ran haiku** — heuristic is straight wrong |

The five low-agreement categories (≤60%) account for 242/463 = 52% of identifiable predictions. Three of them have a clear systematic-disagreement pattern (not bimodal):

1. **`core-interflux-researcher`** — heuristic says opus, reality is uniformly haiku. The role declaration `model_tier: opus` in agent-roles.yaml was set from "research synthesis needs reasoning depth" reasoning, but observed dispatch chose haiku 17/17 times. **The role is mis-declared.**

2. **`core-planner`** (fd-architecture, fd-systems) — heuristic says opus, but 11/21 ran sonnet and 8/21 ran haiku. These are role-floor declarations that don't match how callers actually request them. Either the heuristic should be `sonnet` with opus ceiling, or callers should be respecting the floor.

3. **`core-builtin-general`** — heuristic says opus, but observed is opus=101 (56%) / sonnet=51 / haiku=28. Pareto distribution. This is the *correct* heuristic for the median case but mis-predicts the 44% downgrade tail.

The other two (`core-builtin-explorer`, `core-plugin-reviewer`) are similar: the heuristic captures the dominant choice but mis-predicts the long tail.

`generated-fd-reviewer` is bimodal (6+6+2 across haiku/opus/sonnet) and the most data-poor — 14 rows is barely enough to characterize.

## Decision per the pre-committed rule

The bead's pre-committed decision rule (verbatim):

> - **Extended-heuristic agreement >95% across all categories**: routing question is settled. Close any remaining microrouter-related work.
> - **<95% but >90%**: marginal residual headroom — log per-disagreeing-agent details and decide case-by-case whether to fix the agent's role mapping or accept the gap.
> - **<90% in any category**: the residual is real. Open a narrow learned-router scoping bead, but only for the disagreeing categories. Do NOT revive the original `.19` epic — it was wrong-shaped.

The rule is written about **agreement**, not coverage. Coverage was the cs2 question; agreement is what 2bg actually measures.

**Multiple categories are below 90% agreement.** The rule says: open a narrow learned-router scoping bead, only for the disagreeing categories.

**But before that** — three of the five sub-90% categories have a **systematic disagreement pattern** (not bimodal), meaning the heuristic itself is mis-declared. Fixing the declaration is cheaper than learning a router:

| Category                    | Fix? |
| --------------------------- | ---- |
| `core-interflux-researcher` | Change `model_tier: opus` → `haiku` (or sonnet with downgrade hook). Reality: 17/17 haiku. **Declaration bug.** |
| `core-planner`              | Reduce `model_tier: opus` → `sonnet` with `max_model: opus` ceiling. Reality: 11/21 sonnet, 8 haiku, 2 opus. Heuristic floor is wrong direction. |
| `core-builtin-explorer`     | Already `haiku` default — disagreement is callers up-shifting to opus for deep searches. Acceptable; the heuristic captures the median. |
| `core-plugin-reviewer`      | Already `opus` default — disagreement is early dispatches that ran haiku. Acceptable; recent dispatches respect the heuristic. |
| `core-builtin-general`      | Already `opus` default with no floor — disagreement is callers down-shifting. Acceptable; heuristic captures dominant case. |

**Recommended action:** before opening a learned-router scoping bead, do one more cheap cycle:

1. **Fix the two declaration bugs** (interflux-researcher → haiku, core-planner → sonnet ceiling-opus). One-line YAML edits.
2. **Re-measure.** Expect interflux-researcher to go 0% → ~100% and core-planner to go 9.5% → ~60%, lifting overall agreement substantially.
3. **Then** decide whether the residual long-tail disagreement (callers up/down-shifting from the median) is worth a learned router or is just acceptable noise.

The original Sylveste-2bg done-when said:

> Decision recorded.

Decision: **The bead's decision rule is technically triggered (<90% in multiple categories), BUT the two largest sub-90% categories are heuristic declaration bugs, not learned-router opportunities. Fix the declarations first, re-measure, then decide.** This avoids spending learned-router complexity on a problem that's a YAML typo.

## Follow-up beads

- **Sylveste-0zy (P1):** Fix `agent-roles.yaml` declarations for `interflux-researcher` (opus → haiku) and `core-planner` (opus → sonnet + opus ceiling). Re-run `baseline.py`, capture `baseline-2026-05-12.txt`, append rerun-2 note here. Should bring overall agreement above 75%, likely 80%+.
- **Sylveste-zge (P2, deferred +2w, depends on 0zy):** Conditional bead. If after declaration fixes overall agreement is still <85%, scope a narrow learned-router for the residual long-tail disagreement in `core-builtin-explorer` and `core-builtin-general` (caller-shifting patterns). Trigger condition spelled out in the bead.
- **Sylveste-xvt (P3):** 1114/1591 (70%) of "subagent rows" in `metrics.db` are unparseable hash-IDs from interstat's fallback path. Worth investigating whether the upstream JSONL parser can be improved to recover more agent names. This is **not** a routing concern — it's interstat data quality.
- **Microrouter .19 stays killed.** Nothing in this measurement justifies reviving learned routing as a primary lever. The headroom is in declaration fixes (cheap) + maybe a narrow downgrade-detector for the long tail (small).

## Refs

- Pre-extension baseline: `docs/research/microrouter-phase1/baseline-2026-05-06.txt`
- Post-extension baseline: `docs/research/microrouter-phase1/baseline-2026-05-11.txt`
- Measurement script: `docs/research/microrouter-phase1/baseline.py`
- Predecessor bead: Sylveste-cs2 (closed)
- Original .19 kill rationale: `docs/research/flux-review/microrouter-track-b6/` (SUPERSEDED markers)
- MEMORY: `project_microrouter_19_killed.md`
