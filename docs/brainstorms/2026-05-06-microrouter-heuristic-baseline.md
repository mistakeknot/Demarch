---
date: 2026-05-06
bead: sylveste-s3z6.19.1 (Phase 1)
parent_epic: sylveste-s3z6.19
status: decision-pending
supersedes: none
prereq_artifact: docs/research/microrouter-phase1/baseline-2026-05-06.txt (gitignored)
---

# Microrouter `.19.1` Phase 1 — Heuristic baseline measurement

## TL;DR

**The microrouter epic as scoped is solving the wrong problem.** The `agent-roles.yaml` heuristic covers only ~6% of subagent dispatches; the other 94% are agents the heuristic has never heard of. Adding a learned router on top of a heuristic that doesn't apply to most traffic is premature optimization. Recommendation: **kill the LoRA-distillation epic; replace with a much cheaper "extend the heuristic to cover Explore/Plan/general-purpose/generated-fd" bead.** If headroom remains after coverage extension, revisit then.

## Method

Per `.19.8`'s D2 decision rule and the oracle protocol picked 2026-05-06 (weak oracle, restricted to well-formed rows):

- Data source: `~/.claude/interstat/metrics.db` `agent_runs` table.
- Selection: rows where `agent_name != 'main-session'`, `model` non-null, `total_tokens > 0`, `model != '<synthetic>'`. **N = 1,586 subagent dispatches.**
- Hash-id agent_names (1,326 rows starting with `a` followed by 16 hex chars) are interstat's fallback when name didn't parse — for those rows, `subagent_type` is the authoritative agent identifier.
- Heuristic: `agent-roles.yaml` + `lib-routing.sh` clamping (min_model floor, max_model ceiling).
- Weak oracle: actual `model` dispatched is treated as optimal. Headroom = 1 − (heuristic_recommendation == oracle).
- Script + raw output: `docs/research/microrouter-phase1/baseline.py` and `baseline-2026-05-06.txt`.

## Results

### Coverage

| Category | n | heuristic-known | % |
|---|---|---|---|
| core-checker (fd-perception/resilience/decisions/people) | 11 | 11 | 100% |
| core-editor (fd-performance/user-product/game-design) | 20 | 20 | 100% |
| core-planner (fd-architecture/systems) | 19 | 19 | 100% |
| core-reviewer (fd-correctness/quality/safety) | 48 | 48 | 100% |
| **Subtotal: agents in agent-roles.yaml** | **98** | **98** | **6.2%** |
| builtin (Explore/Plan/general-purpose) | 322 | 0 | 0% |
| generated-fd (fd-* not in roles.yaml) | 15 | 0 | 0% |
| plugin-other (clavain:/intersynth:/code-reviewer) | 6 | 0 | 0% |
| other (uncategorized subagent_type fallbacks) | 1,145 | 0 | 0% |
| **Subtotal: heuristic uncovered** | **1,488** | **0** | **93.8%** |

### Headroom (where heuristic applies)

Aggregate agreement: **67/98 = 68.4%.** Headroom: 31.6%.

By role:
| Role | n | agree | rate |
|---|---|---|---|
| core-checker | 11 | 10 | 90.9% |
| core-editor | 20 | 18 | 90.0% |
| core-reviewer | 48 | 37 | 77.1% |
| core-planner | 19 | 2 | **10.5%** |

The planner role is the entire source of disagreement: heuristic says `opus` for fd-architecture/fd-systems, prod actually used `sonnet` 13× and `haiku` 4× across 19 dispatches.

### Model distribution in uncovered traffic

builtin (n=322): opus=137, haiku=119, sonnet=66 — well-balanced, not collapse.
other (n=1,145): opus=432, haiku=416, sonnet=297 — also balanced.
generated-fd (n=15): haiku=6, opus=6, sonnet=3.
Explore (n=135): haiku=88, opus=32, sonnet=15 — heavily haiku.
Plan (n=8): opus=6, haiku=2 — heavily opus.
general-purpose (n=181): opus=102 (incl. opus-4-7=32), sonnet=51, haiku=28 — heavily opus.

The uncovered traffic is **not** "everything goes to default sonnet." Production has been making real per-dispatch model choices that the routing.yaml + agent-roles.yaml never see — most likely via main-session model selection or per-call overrides downstream of the resolver.

## Interpretation

### Reframe of the original assumption

`.19.8`'s framing assumed: "is the heuristic close enough to optimal that a learned router isn't worth building?" The data exposes a different question: **the heuristic only knows about 12 reviewer agents. The other 94% of subagent traffic routes by mechanisms outside `agent-roles.yaml`.**

Three implications:

1. **A learned microrouter trained on 98 rows is pointless** — under any reasonable train/holdout split, per-tier sample sizes collapse to single digits. The "≥5,000 example floor" the synthesis named (P0-D coverage gate) was already aspirational; against the actual covered traffic it's hopeless.

2. **A learned microrouter trained on the full 1,586 rows would have to invent labels** for 94% of traffic that the heuristic has nothing to say about. Either you train it on *what production happened to choose* (assumes prod is optimal — that's the weak-oracle assumption inflated to a training signal), or you label by hand (1,488 rows × manual review = not happening).

3. **The cheap intervention that the synthesis didn't consider**: extend `agent-roles.yaml` to cover Explore, Plan, general-purpose, and the generated `fd-*` set. This is YAML edits + a few lib-routing.sh changes, not LoRA distillation. After that intervention, re-measure. If the extended heuristic agrees with production on >95% of traffic, kill the learned-router idea entirely. If not, we know exactly which agents resist heuristic capture and a learned router has a plausible scope.

### The planner-role anomaly

fd-architecture and fd-systems are heuristic→opus, prod→sonnet 13× and haiku 4×. Two readings:

- **Reading 1 (prod is right)**: opus is over-resourcing fd-architecture. The heuristic is wrong. Action: change fd-architecture/fd-systems to `model_tier: sonnet` in roles.yaml.
- **Reading 2 (prod is wrong)**: someone overrode model selection downstream and shipped under-resourced architectural reviews. The heuristic is right. Action: investigate whether those 17 reviews produced bad findings.

Without outcome labels we can't tell — and this is exactly the limitation of the weak-oracle approach the synthesis flagged. Recommend: log this as a follow-up investigation but don't let it block the bigger decision.

## Recommendation

**Kill the microrouter epic in its current form.** Open `.19-CLOSE` with this brainstorm referenced. Replace with a smaller bead family:

1. **`.19-CLOSE`** — close the LoRA-distillation epic with this measurement as evidence. Does NOT close `.19.5` factual corrections (those should land regardless as routing.yaml hygiene).

2. **NEW bead — heuristic coverage extension**. Extend `agent-roles.yaml` to cover Explore, Plan, general-purpose, generated `fd-*`. Pick `model_tier` defaults from observed production usage (Explore→haiku since haiku=88 of 135; Plan→opus since opus=6 of 8; etc.). Single PR.

3. **NEW bead — re-measure post-coverage**. After (2), re-run this script. If extended heuristic agreement with production is >95% across all categories, the routing question is settled. If <95%, the residual headroom defines a much narrower scope for a learned-router question — tracked then, not now.

4. **NEW bead — fd-architecture/fd-systems opus-vs-sonnet investigation**. Decide whether the heuristic or production is right. Light-weight: read 5 fd-architecture sonnet outputs, ask "did this need opus?" Manual judgement is cheap.

5. **`.19.5` corrections preserved** — resolver below `overrides[agent]`, port 8422, schema validator note, lib-routing.sh is Bash, explicit fall-through, rollback runbook, shadow log schema, privacy fail-closed. These are factual corrections to routing.yaml hygiene, useful regardless of the learned-router question.

6. **`.19.9` (pass@1 telemetry) is now optional**. With the LoRA path dead, pass@1 telemetry is no longer a hard prereq. It's still useful for general-purpose routing analysis — keep open as P2.

### Why this is the right call

The original epic carried implicit assumptions that the data falsifies: "routing-eligible traffic is dominated by agent-roles.yaml-covered agents," "the heuristic is close enough that the learned-router question is meaningful," "verdict outcomes provide oracle data." None of those hold. Three weeks of LoRA-distillation work on top of a 98-row covered-traffic surface is the kind of thing that ships and looks fine in eval and provides zero production value.

The honest path is to fix the cheap thing (heuristic coverage) first, re-measure, and only then decide whether the residual problem warrants ML.

## Open questions

- The 1,145 "other" rows have a long tail of subagent_type values. A second-pass categorization may reveal that some of them ARE in agent-roles.yaml under different namespacing — worth a 30-minute audit before the coverage-extension bead is scoped.
- Whether to retain `.19.4` (eval harness) for the *heuristic-coverage* re-measurement protocol. The leave-one-review-out CV machinery is overkill for a coverage check; a simple re-run of this script after each extension is sufficient.
