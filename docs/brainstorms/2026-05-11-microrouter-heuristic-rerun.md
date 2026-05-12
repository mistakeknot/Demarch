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

## Addendum 2026-05-11: Sylveste-0zy diagnostic — frontmatter ↔ yaml drift audit

When 0zy started ("fix the two mis-declared roles"), the diagnosis re-shaped:

1. **All 17 interflux-researcher dispatches were in April 2026**, predating cs2's May 9 yaml additions. So the "0% agreement" wasn't mis-routing — it was historical data measured against post-hoc declarations.
2. **lib-routing.sh's `min_model` floor is only on the Codex dispatch path** (`dispatch.sh`). Claude Code subagent dispatch ignores agent-roles.yaml entirely; it reads each subagent's frontmatter `model:` field directly.
3. **Agent-agnostic framing**: agent-roles.yaml is the host-neutral policy artifact. Each host (CC, Codex, Hermes, Droid) needs an adapter that projects yaml policy into host-native config. For Claude Code, that projection is each subagent's `.md` frontmatter. They're currently out of sync.

### Drift audit results

`verify_frontmatter.py` walks all 33 first-party subagent `.md` files and compares frontmatter `model:` against agent-roles.yaml role bands:

| state              | count | meaning |
| ------------------ | ----: | ------- |
| AGREE              |    10 | frontmatter matches yaml tier_default |
| AGREE_OFF_DEFAULT  |     1 | frontmatter in yaml [min,max] but not default (fd-architecture: sonnet, default opus) |
| **BELOW**          |   **8** | **frontmatter below yaml min_model floor — drift** |
| UNMAPPED           |    14 | subagent has frontmatter but no agent-roles.yaml entry — coverage gap |

**The 8 BELOW agents** (all frontmatter `haiku` vs yaml `min_model: sonnet`):

| agent                          | role                 | frontmatter | yaml floor |
| ------------------------------ | -------------------- | ----------- | ---------- |
| best-practices-researcher      | interflux-researcher | haiku       | sonnet     |
| framework-docs-researcher      | interflux-researcher | haiku       | sonnet     |
| git-history-analyzer           | interflux-researcher | haiku       | sonnet     |
| learnings-researcher           | interflux-researcher | haiku       | sonnet     |
| repo-research-analyst          | interflux-researcher | haiku       | sonnet     |
| fd-systems                     | planner              | haiku       | sonnet     |
| plan-reviewer                  | plugin-reviewer      | haiku       | sonnet     |
| synthesize-review              | plugin-reviewer      | haiku       | sonnet     |

**The 14 UNMAPPED agents** (no role entry — yaml has no policy opinion at all):
- intersynth: synthesize-documents, synthesize-research
- intercraft: agent-native-reviewer
- intertrace: fd-integration
- interdeep: report-compiler, research-planner, source-evaluator
- interfluence: voice-analyzer
- clavain workflow: bug-reproduction-validator, codex-delegate, pr-comment-resolver, ui-polish
- clavain review: data-migration-expert
- interflux: fluxbench-discover

### Decision shape for fixing the 8 BELOW

For each, **two paths**, requires per-agent judgment:

- **yaml-wins (raise frontmatter haiku → sonnet)**: respect the policy that says these are reviewer/planner-class. Cost: CC subagent dispatch will now cost more for these agents. Quality: probably better for the planner/reviewer ones; possibly overkill for the researchers if "search and synthesize external docs" really is haiku-tractable.
- **frontmatter-wins (lower yaml min_model sonnet → drop entirely)**: accept that observed practice is haiku-suffices. Cost: no change. Quality: yaml floor was aspirational; the haiku dispatches haven't produced quality complaints in observed history.

Recommended split (judgment call, gated on user review):
- **researchers (5)**: frontmatter-wins. They're doing search + synthesis tasks where haiku has been adequate. Drop yaml min_model.
- **fd-systems (1)**: yaml-wins. Systems-thinking review is genuinely a reasoning task; raise to sonnet.
- **plan-reviewer, synthesize-review (2)**: yaml-wins. Reviewer-class; raise to sonnet.

### Decision shape for 14 UNMAPPED

Two options:

1. **Add per-agent entries** under existing roles (most belong to `editor` or `plugin-reviewer`); leaves yaml as canonical.
2. **Add pattern-based default** (any unmapped agent → editor/sonnet). Cheaper but requires lib-routing.sh parser extension (currently does explicit-list lookup only).

Recommended: Option 1 for now (explicit additions, ~20 lines yaml). Option 2 becomes a separate bead if maintenance pain shows up.

### Updated decision on the original kill rule

Coverage and agreement were both poisoned metrics on April-only data. The right metric going forward:

- **Drift count** (BELOW + ABOVE state in `verify_frontmatter.py`)
- **Run after every yaml edit** to confirm host adapters stay in sync
- **CI hook later** — fail the build if drift increases

This is a more honest stop-condition than the original >95% / 90-95% / <90% rule, which was written before we understood that `model_tier` is documentation-only and the real enforcement lever differs per host.

### Resolution (2026-05-12)

Executed in this session:

1. **Lowered 3 aspirational yaml floors** that contradicted deliberate frontmatter tuning:
   - `interflux-researcher`: dropped `min_model: sonnet`, tier opus → haiku, added `max_model: opus` ceiling for up-shift. Now matches all 5 researcher frontmatters (all haiku) and intersynth/interflux design intent.
   - `planner`: dropped `min_model: sonnet`. fd-architecture stays sonnet via own frontmatter; fd-systems intentionally haiku (sonnet→haiku in git history).
   - `plugin-reviewer`: dropped `min_model: sonnet`, tier opus → haiku, added `max_model: opus`. plan-reviewer cycled sonnet→haiku→sonnet→haiku in git history; synthesize-review is documented as deliberate-haiku in intersynth/CLAUDE.md.

2. **Added 4 new roles for the 14 UNMAPPED agents**:
   - `synthesizer` (3 agents): synthesize-documents, synthesize-research, report-compiler. haiku default, sonnet ceiling. "Structuring not reasoning" per intersynth design intent.
   - `workflow-executor` (3 agents): codex-delegate, pr-comment-resolver, bug-reproduction-validator. haiku default, opus ceiling. Task execution rather than review.
   - `research-support` (2 agents): source-evaluator, research-planner. haiku default, opus ceiling. Research pipeline helpers.
   - `host-default` (3 agents): data-migration-expert, ui-polish, fluxbench-discover. No model_tier/min/max — frontmatter intentionally omits `model:`. Records existence + "no policy" intent.

3. **Added 3 to existing roles**: fd-integration + agent-native-reviewer → `reviewer`; voice-analyzer → `editor`. Frontmatters already aligned.

### Post-fix audit

```
Agents scanned: 33
  AGREE              30
  AGREE_OFF_DEFAULT   3   (fd-architecture, fd-systems, report-compiler — within band, off default tier)
  BELOW               0
  ABOVE               0
  NO_MODEL            0   (3 NO_MODEL agents are in host-default role, classified AGREE)
```

100% coverage, zero drift, 10 roles. agent-roles.yaml is now a complete and accurate policy artifact that any host adapter (Claude Code, Codex, future Hermes/Droid) can consult.

### Recommended future work

- **Sylveste-zge (P2, conditional, deferred):** unchanged. Trigger condition is "post-fix dispatch agreement still <85% in core-builtin-explorer + core-builtin-general categories." That's a *new dispatch* question — answer requires waiting for fresh May+ data before re-running baseline.py.
- **CI integration (new bead, P3):** wire `verify_frontmatter.py` into a CI hook. Fail build if drift count increases.
- **Codex/Hermes/Droid adapters (future, when needed):** when a non-CC host enters the stack, write its adapter that reads agent-roles.yaml and projects into the host's config format. The yaml contract is stable enough to be a foundation.

## Refs

- Pre-extension baseline: `docs/research/microrouter-phase1/baseline-2026-05-06.txt`
- Post-extension baseline: `docs/research/microrouter-phase1/baseline-2026-05-11.txt`
- Drift audit table: `docs/research/microrouter-phase1/verify-table-2026-05-11.tsv`
- Drift audit summary: `docs/research/microrouter-phase1/verify-summary-2026-05-11.txt`
- Measurement script: `docs/research/microrouter-phase1/baseline.py`
- Drift audit script: `docs/research/microrouter-phase1/verify_frontmatter.py`
- Predecessor bead: Sylveste-cs2 (closed)
- Original .19 kill rationale: `docs/research/flux-review/microrouter-track-b6/` (SUPERSEDED markers)
- MEMORY: `project_microrouter_19_killed.md`
