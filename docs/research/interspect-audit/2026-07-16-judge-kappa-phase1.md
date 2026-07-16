# LLM-Judge Reliability Audit — Phase 1 (Sylveste-06i.1)

Date: 2026-07-16
Bead: Sylveste-06i.1 (child of Sylveste-06i epic)
Pre-registration: `docs/research/2026-07-16-ecosystem-research-agenda.md`, top bet #3
Companion experiment: Sylveste-407 (holdout register — see `2026-07-16-holdout-register-phase1.md`, also parked)

## Pre-registered experiment and kill rule

> Re-run a frozen set of ~30 past reviews multiple times per judge across 2-3 model families; compute intra-judge kappa (test-retest), cross-family agreement, and the self-vs-other score delta (does a model score its own family's outputs higher?).
>
> **KILL RULE:** if intra-judge kappa >0.8, cross-family disagreement <10%, AND self-vs-other delta <5%, judges are reliable — record the calibration constants and skip building the reliability harness.

## Verdict: KILL RULE FAILS — build the reliability harness

The kill rule requires all three branches to pass. **Branch 1 (intra-judge kappa) fails decisively** — measured kappa is 0.56, well below the 0.8 threshold, indicating only moderate/substantial agreement (Landis & Koch scale) rather than the near-perfect agreement the threshold demands. Branches 2 and 3 are **not evaluable** in this pass (tooling/data gaps below) but the failure on branch 1 alone is sufficient to require the reliability harness — no combination of the other two branches passing would flip the verdict, since all three must pass.

This is an honest negative result: judge noise is real and non-trivial even within a single model family, on a single day, holding the prompt constant. flux-drive review scores feeding interspect evidence should not be trusted as ground truth without either (a) a calibration/discount layer, or (b) an ensemble/consensus mechanism, or (c) a documented acceptance that severity tiers below the CRITICAL/HIGH boundary are noisy.

## Design actually run

**Corpus:** 30 findings, frozen from `docs/research/flux-drive/` (351 `fd-*.md` review files across ~90 review directories). 3 findings sampled per review-agent type across the 10 core standing flux-drive review agents (architecture, correctness, systems, quality, decisions, safety, user-product, resilience, perception, performance) — the highest-severity finding from each sampled file, with full text, location, subject, and document-level verdict. Full manifest and extraction methodology: `/Users/sma/.claude/jobs/7b16ec73/tmp/lane-c/corpus/manifest.md`; structured corpus: `.../corpus/corpus.json`.

**Judges:** 1 judge family (Claude/Sonnet, in-context — this session is Sonnet 5). **Cross-family judging (OpenRouter-dispatched DeepSeek or similar) was infeasible** — see Tooling Gaps below. This collapses the design to the Claude-family-only branch specified in the task's feasibility-gate fallback.

**Repeats:** 3 independent judging rounds, each dispatched as a fresh, stateless Sonnet subagent (`general-purpose`, `model: sonnet`) with no shared context between rounds — this gives genuine test-retest independence (no risk of the "judge remembers its prior answer" contamination that would occur judging all 3 rounds in one continuous context). Each round judged all 30 items independently, scoring severity (CRITICAL/HIGH/MEDIUM/LOW) and a binary CONFIRM/REJECT verdict, using the same deterministic prompt template (`judge_prompt_template.md`) with no explicit temperature control exposed by the harness (subagent dispatch does not expose temperature as a parameter).

**Realized N:** 30 items × 3 repeats × 1 judge family = 90 judgments. This is the minimum viable end of the task's suggested range (15-30 items × 3 repeats × 2-3 judges) — shrunk from 2-3 judge families to 1 due to the OpenRouter feasibility-gate failure. **Power limitation, stated explicitly:** with only 1 judge family, this measures test-retest noise within Sonnet only; it says nothing about cross-family disagreement or self-preference, and 30 items gives wide bootstrap CIs (see below) — this is a spike-day lower bound on the noise floor, not a precision estimate.

## Feasibility gate: OpenRouter cross-family dispatch — UNAVAILABLE

One test call to `mcp__plugin_interflux_openrouter-dispatch__review_with_model` (model `deepseek/deepseek-chat`, trivial prompt) returned:

```json
{"error":"openrouter_401","message":"{\"error\":{\"message\":\"Missing Authentication header\",\"code\":401}}","latency_ms":133}
```

Root cause, traced to source: the MCP server (`~/.claude/plugins/cache/interagency-marketplace/interflux/0.2.74/mcp-servers/openrouter-dispatch/index.ts:8`) reads `process.env.OPENROUTER_API_KEY` at server-process startup and disables the tool entirely if unset — the server logs `"OPENROUTER_API_KEY not set — openrouter-dispatch MCP disabled."` on boot. A key exists on disk (`~/.cache/interfer/openrouter.key`) but it is not wired into the MCP server's process environment, and setting it requires restarting the MCP server with the env var present — not something available mid-session. Per the task's Step 2 instruction ("If unavailable/unauthenticated, run the Claude-family-only design"), this branch was taken.

**What's needed to close this gap:** wire `OPENROUTER_API_KEY` (sourced from `~/.cache/interfer/openrouter.key` or an equivalent secret store) into the `openrouter-dispatch` MCP server's launch environment (`scripts/launch-openrouter.sh` in the interflux plugin looks like the intended entry point — not inspected further, out of scope for this spike) and restart the MCP server. Once done, branches 2 (cross-family disagreement) and 3 (self-vs-other delta, partially — see below) become evaluable in a follow-up run.

## Self-vs-other: NOT EVALUABLE (data gap, not tooling gap)

Checked the full 351-file corpus (not just the frozen 30) for any provenance/model metadata identifying which LLM generated a given finding — frontmatter fields, `generated_by:`, `model:`, or explicit in-body statements. **None found in the 10 core review-agent types the corpus samples from.** (Independent validation noted 4 esoteric one-off fd files outside those types do carry `model: sonnet` frontmatter — uniformly sonnet, so they could not yield a self-vs-other contrast either.) flux-drive's `fd-*.md` output format has no field recording which model produced the review. This means self-vs-other cannot be computed from the existing corpus even with cross-family judging working, independent of the OpenRouter gap. Closing this requires flux-drive to start recording generating-model identity at write time — a product change to the review-agent output format, not a research-harness fix. Recommend filing that as a followup if the reliability harness is built.

## Results

Raw judge outputs (audit trail): `/Users/sma/.claude/jobs/7b16ec73/tmp/lane-c/raw/{round1,round2,round3}.jsonl` (30 lines each, `{item_number, severity, verdict}`), plus `stats_results.json` (full computed-statistics dump) and `corpus/corpus.json` (frozen 30-item corpus with original severities). Statistics computed via `/Users/sma/.claude/jobs/7b16ec73/tmp/lane-c/compute_stats.py` (pure Python — no numpy/scipy available in this environment; Fleiss' kappa, pairwise Cohen's kappa, and percentile bootstrap CIs implemented directly).

### Headline statistic 1: Intra-judge kappa (test-retest, severity, 4-tier scale)

| Metric | Value | 95% bootstrap CI (item-resampled, n=2000) |
|---|---|---|
| **Fleiss' kappa (3 rounds, 4 categories)** | **0.563** | [0.374, 0.745] |
| Mean pairwise Cohen's kappa | 0.567 | [0.375, 0.735] |
| Mean pairwise percent agreement | 73.3% | — |
| Exact match rate (all 3 rounds agree) | 60.0% (18/30) | — |

Per Landis & Koch (1977), kappa 0.563 falls in the "moderate" band (0.41-0.60), bordering "substantial" (0.61-0.80) — well short of the "almost perfect" (0.81-1.00) band the kill rule's >0.8 threshold requires. The CI's upper bound (0.745) does not reach 0.8 either, so this isn't a borderline call sensitive to bootstrap noise — the same judge, given the same finding text on 3 independent passes, disagrees with itself often enough that kappa cannot plausibly clear the bar with more data of this shape.

Pairwise breakdown (round1 vs round2, round1 vs round3, round2 vs round3):

| Pair | Cohen's kappa | % agreement |
|---|---|---|
| round1 vs round2 | 0.730 | 83.3% |
| round1 vs round3 | 0.435 | 66.7% |
| round2 vs round3 | 0.536 | 70.0% |

Round-to-round variance is itself notable — round1/round2 look reasonably consistent (kappa 0.73) but round3 disagrees more with both of the others, dragging the 3-way Fleiss kappa down. This is exactly the kind of instability a single-round spot-check would miss.

### Headline statistic 2: Cross-family disagreement — NOT EVALUABLE

OpenRouter dispatch unauthenticated (see Tooling Gaps). No cross-family data collected.

### Headline statistic 3: Self-vs-other score delta — NOT EVALUABLE

No provenance metadata in the corpus (see above). No self-vs-other data collected, independent of the OpenRouter gap.

### Secondary finding: systematic severity deflation vs. original flux-drive rating

Not part of the pre-registered kill-rule statistics, but visible immediately in the raw data and worth recording as it bears directly on the "judge noise/self-preference propagates into routing overrides" concern that motivated this audit: the re-judging Sonnet passes rated findings **at or below** the original flux-drive severity in the overwhelming majority of cases, across all 3 rounds. Of 30 items, only 2 (items 4, 5 — both `correctness` findings) were rated at the original severity in all 3 rounds; most CRITICAL-rated originals were re-judged HIGH or MEDIUM, and most HIGH-rated originals were re-judged MEDIUM or LOW.

| Original severity | n items | Re-judged at/above original (any round) | Re-judged below original (any round) |
|---|---|---|---|
| CRITICAL (9 items) | 9 | 3 | 9 (all 9 at least once) |
| HIGH (20 items) | 20 | 8 | 17 |
| MEDIUM (1 item) | 1 | 0 (LOW in all 3 rounds) | 1 |

This is consistent with (though not proof of) a hypothesis that flux-drive's original in-context review agents (which see the full reviewed artifact — plan, PRD, or diff — plus the review-agent's specialized lens instructions) systematically score more severely than a judge given only the extracted finding text and asked to re-score cold. That's a confound of this experiment's scope choice (re-judging the finding text, not re-running the full review — see manifest limitations), not necessarily evidence that flux-drive over-scores in production. It does mean: **do not use this audit's absolute severity levels as a "flux-drive over-scores" calibration constant** — the delta is at least partly an artifact of context stripped during corpus freezing. What it does establish cleanly is the test-retest noise floor (headline statistic 1), which used the same stripped-context conditions symmetrically across all 3 rounds.

### Data-quality note: verdict (CONFIRM/REJECT) statistic is degenerate, not clean

All 90 judgments (30 items × 3 rounds) returned CONFIRM; zero REJECT across the board. The computed Cohen's kappa for verdict is reported as 1.0 in `stats_results.json`, but this is a **degenerate result from zero outcome variance**, not evidence of perfect judge agreement — kappa's denominator (`1 - P_e`) is 0/0 when there's no between-category variance, and the script's guard clause returns 1.0 for that case rather than "undefined." Do not read 100% CONFIRM as a reliability finding; it more likely reflects (a) the corpus being pre-filtered to already-severe findings (median severity HIGH/CRITICAL in the original corpus), making REJECT a rare judgment for this population, and/or (b) a judge prompt that doesn't sufficiently invite skepticism. A future harness run should either include some corpus items pre-selected as likely-spurious (to get REJECT variance) or drop the verdict axis and focus purely on severity-tier reliability, which is where the real signal is.

## Limitations (stated explicitly per spike-day scope)

1. **1 judge family only**, not the target 2-3 — cross-family and self-vs-other are structurally unevaluable this run (tooling gap for cross-family, data gap for self-vs-other).
2. **30 items** is the low end of the suggested range; bootstrap CIs are correspondingly wide (Fleiss kappa CI width ~0.37). A production-grade calibration run should use more items once the harness exists.
3. **No temperature control.** Subagent dispatch (the mechanism used to get independent stateless judging passes) does not expose a temperature parameter. Some of the observed test-retest variance may be attributable to whatever the underlying platform's default sampling temperature is for Sonnet, rather than to the judging task's inherent ambiguity — this audit cannot separate those two contributions. A harness with direct API access (temperature=0, or an explicit swept range) would isolate this.
4. **Re-judging scope is the extracted finding, not the full original review.** Judges score the frozen finding text cold, not by re-reviewing the underlying plan/PRD/diff with the full flux-drive review-agent lens instructions. This is a deliberate scope choice (see manifest) to keep the audit measuring judge consistency on *re-scoring a presented finding* — the mechanism that actually feeds interspect evidence — rather than re-running full reviews, which would need frozen/reproducible source artifacts most flux-drive review targets don't have (many are brainstorms/PRDs since evolved or superseded).
5. Statistics were computed with a hand-rolled pure-Python implementation (no numpy/scipy in this environment) — Fleiss' kappa and Cohen's kappa formulas were implemented directly from their standard definitions and spot-checked against the observed/expected-agreement intermediate values (P_bar, P_e) printed alongside the final kappa; no cross-check against an established stats library was possible in this environment.

## Recommendation

Do not skip the reliability harness. The kill rule's first branch fails with enough margin (kappa 0.56 vs. 0.8 threshold, CI upper bound 0.745) that no plausible outcome on the other two branches changes the verdict. Concretely:

1. **File a followup bead** to fix the OpenRouter MCP auth wiring (`OPENROUTER_API_KEY` → `openrouter-dispatch` MCP server env) so cross-family judging becomes possible for a Phase 2 run.
2. **File a followup bead** to add generating-model provenance to flux-drive's `fd-*.md` output format (a `model:` frontmatter field or equivalent), enabling self-vs-other measurement once cross-family judging works.
3. **Design the reliability harness** with the severity-tier noise this audit found in mind: a naive single-pass judge score should not be trusted at face value for interspect evidence, particularly near the CRITICAL/HIGH and HIGH/MEDIUM boundaries where most of the observed disagreement concentrated. An ensemble-of-N (majority vote or median across N ≥ 3 judging passes) or an explicit uncertainty band around single-pass scores are both cheaper mitigations than solving judge determinism outright, and either would directly address the "second unguarded seam in the ioe7 calibration loop" framing that motivated this bet.

## Raw data pointers

All raw data copied into the repo (durable) at `docs/research/interspect-audit/2026-07-16-judge-kappa-phase1-data/`:

- Corpus: `corpus/corpus.json` (30 items), `corpus/manifest.md` (selection methodology)
- Judge prompt template: `judge_prompt_template.md`
- Raw judgments: `raw/round{1,2,3}.jsonl` (the audit trail — 30 lines each, `{item_number, severity, verdict}`)
- Computed statistics: `raw/stats_results.json`
- Statistics script: `compute_stats.py` (pure Python; re-runnable against any future round{N}.jsonl set with the same shape)

Session scratch copies also exist at `/Users/sma/.claude/jobs/7b16ec73/tmp/lane-c/` (not durable — may be reclaimed).
