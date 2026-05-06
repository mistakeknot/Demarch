---
artifact_type: preregistration
bead: sylveste-2n8i
gate: G10
parent_prd: docs/prds/2026-04-21-persona-lens-ontology.md
corpus: docs/research/f6-ab-corpus/
harness: scripts/f6_ab_harness/
baseline_sha: f72d3cfd7d72a33c1a97ec37cfe99c5708a5fa0d
created: 2026-05-06
---

# F6 Measurement Pre-Registration — Lattice-Ontology Triage A/B

This document is the **frozen experimental contract** for the F6b A/B test (legacy flux-drive triage vs. lattice-ontology triage). It is committed *before* any ontology backend code lands so the metrics, baseline, thresholds, and analysis plan cannot be retrofitted to flatter the new backend. This is gate G10 (measurement pre-registration) made mechanical via bead dependency.

> Any change to this document after F6b begins is itself a falsification — the experiment must be re-baselined. F6b's ship-decision memo (`docs/research/f6-ab-decision.md`) must reference this file by SHA.

## Hypothesis

H1 (alternative): The lattice-ontology triage backend produces ≥ 15% lift on the primary metric (review-coverage-per-diff) at constant-or-lower cost-per-finding compared to the legacy flux-drive triage, evaluated on the held-out 30-diff corpus at `docs/research/f6-ab-corpus/`.

H0 (null): The ontology backend's review-coverage-per-diff is within ±5% of legacy at any cost. The redesign zone (5–15% lift) is treated as inconclusive — neither ship nor abandon — and triggers a redesign bead.

## Baseline

- **Baseline SHA:** `f72d3cfd7d72a33c1a97ec37cfe99c5708a5fa0d` (HEAD at F6a start, 2026-05-06).
- **Baseline backend:** the legacy flux-drive triage as documented in `interverse/interflux/skills/flux-drive/SKILL.md` Steps 1.0–1.3 at the baseline SHA. F6b's first action is a baseline run that records legacy metrics over the corpus into `docs/research/f6-baseline-results.jsonl`. That baseline file becomes immutable until the experiment ends.
- **Baseline lock:** the baseline run uses `--baseline-sha=f72d3cfd...` and the harness asserts the SHA matches `git rev-parse HEAD` of the working tree on each replay. If HEAD has moved, the harness aborts and asks the operator to check out the baseline before replaying — the legacy backend's behaviour is not stable across SHAs.

## Primary metric

**review-coverage-per-diff.** For each of the 30 diffs in the held-out corpus, compute the fraction of `expected_findings_themes` (from the ground-truth label) that are covered by the backend's emitted findings. Average across the corpus.

A finding "covers" a theme when:

1. The finding declares the theme via `Finding.themes` (exact match, case-insensitive after stripping), **or**
2. ≥ 60% of the theme's content tokens (length ≥ 3, lowercased, alphanumeric-split) appear in the union of `Finding.title` and `Finding.body`.

The 60% token-overlap threshold is itself a calibration choice. F6b *may* swap in an embedding-based matcher provided:

- the embedding model + version are committed in the F6b PRD before any A/B run,
- the matcher's threshold is calibrated against the F6a corpus (precision/recall reported), and
- the F6b ship-decision memo reports the primary metric under *both* matchers and confirms the decision is stable across them.

If only one matcher is run, the token-overlap matcher is the canonical reference.

## Secondary metrics

These are recorded for the ship-decision memo but do **not** override the primary-metric threshold.

1. **agent-selection F1 (macro).** For each diff, treat the backend's `agents_dispatched` as a predicted set against the ground-truth `expected_agents`. Compute precision, recall, F1 per diff; report macro-averages across the corpus. This is the discriminating-power signal for cases where ontology infers agents the legacy rules forbid.
2. **P0/P1 finding count.** Sum of findings with severity P0 or P1 across the corpus. Lift here is desirable but not gating; a backend that produces fewer P0/P1s but identical coverage is acceptable provided the missing severities are not ground-truth findings.
3. **cost-per-finding (USD).** Total backend USD divided by emitted findings. Computed via `interverse/interflux/scripts/estimate-costs.sh` per backend invocation. The ship threshold requires ontology cost-per-finding ≤ legacy cost-per-finding.
4. **wall-time-total (sec).** Sum of per-diff wall time. Reported for transparency; not gating.

The PRD also names **user-accepted-verdict-rate**. That metric requires longitudinal data after F6b ships and is **explicitly not gating** for the F6b ship/abandon decision. If it lands later, it can trigger a re-evaluation but cannot be used as ex-post justification at decision time.

## Discriminating subset

The 12 diffs labelled `discriminating: true` are the subset where legacy and ontology are expected to disagree on agent selection. The ship-decision memo reports primary + secondary metrics on the full 30-diff corpus *and* on the 12-diff discriminating subset. A backend that ships only because of non-discriminating-subset gains is suspect — F6b's reviewer must confirm the discriminating subset is also positive (no formal threshold; reviewer judgment).

## Ship / Abandon / Redesign thresholds

Computed as `(ontology_primary - legacy_primary) / legacy_primary`.

| Lift on primary metric | Cost-per-finding constraint | Decision |
|---|---|---|
| ≥ +15% | ontology ≤ legacy | **SHIP** — flag default flips to `ontology`; epic DoD #1 met |
| ≥ +15% | ontology > legacy | **REDESIGN** — feature reopens to reduce cost; epic pauses |
| +5% to +15% (inclusive at edges) | any | **REDESIGN** — inconclusive lift; reopens with explicit scope |
| < +5% or negative | any | **ABANDON** — DoD #1 NOT MET; epic reopens as redesign per PRD §F6b |

If the legacy baseline review-coverage-per-diff is itself < 0.10 (i.e., legacy is failing at the corpus, not just being beaten), the experiment is paused and the corpus / ground-truth labels are reviewed before any decision binds — a 15% lift on a 5% baseline is meaningless.

## Analysis plan

The F6b execution work performs, in order:

1. **Pre-flight** — verify HEAD == baseline SHA, harness imports cleanly, corpus manifest validates against `labels/_schema.json`.
2. **Baseline replay** — run legacy backend over the 30-diff corpus. Persist results to `docs/research/f6-baseline-results.jsonl`. Compute and persist metrics to `docs/research/f6-baseline-metrics.json`. Mark this file **immutable** (do not amend after the ontology run begins).
3. **Ontology replay** — run ontology backend over the same corpus. Persist results to `docs/research/f6-ontology-results.jsonl`. Compute and persist metrics to `docs/research/f6-ontology-metrics.json`.
4. **Threshold application** — compute the lift table; apply the decision matrix above. Record the decision in `docs/research/f6-ab-decision.md` with explicit reference to this pre-registration doc's commit SHA and the immutable baseline metrics file.
5. **Discriminating-subset cross-check** — repeat (3) and threshold application on the 12-diff discriminating subset. Reviewer confirms decision is stable.
6. **Sign-off** — reviewer signs F6b's bead with the decision verdict + the SHAs of the four immutable artefacts (pre-reg, baseline-metrics, ontology-metrics, decision memo).

## Robustness checks

- **Outlier-removal sanity check.** Drop the largest 3 diffs by line count. If the decision flips, report it in the memo and treat as redesign.
- **Single-labeler caveat.** V1 corpus is single-labeler (`claude-opus-4-7`). At least 5 diffs from the discriminating subset must be re-labelled by a second labeler before F6b ships. Disagreement rate above 30% on the 5-diff sub-sample triggers a corpus rebuild.
- **No retroactive theme expansion.** Ground-truth `expected_findings_themes` cannot be added after the ontology run begins. If a reviewer believes the corpus missed a theme, file a follow-up bead — do not amend the corpus during the experiment.

## Anti-patterns explicitly forbidden

These are listed verbatim so the F6b reviewer can refuse the ship-decision memo if any appear:

- Re-running the ontology backend until its score crosses the threshold and reporting only the favourable run.
- Selectively filtering corpus diffs ("this one was unfair") after seeing the results.
- Tuning the token-overlap threshold or embedding matcher *after* seeing ontology results to recover a passing score.
- Counting non-emitted findings as "covered because the backend's metadata implies it" — only `Finding.themes` and the title+body token overlap count.
- Closing F6b with a non-SHIP outcome and *also* closing the parent epic `sylveste-b1ha` as done. Per PRD §Success Metrics: F6b non-SHIP → epic DoD #1 NOT MET → epic reopens as redesign.

## Sign-off (F6a)

Before F6b may begin, this document must be signed off alongside the corpus. Signature lives in bead `sylveste-2n8i` notes. Reviewer must:

1. Confirm baseline SHA is frozen and matches the corpus's recorded baseline.
2. Confirm primary + secondary metric definitions are complete and unambiguous.
3. Confirm the threshold matrix is exhaustive and the redesign zone is non-empty.
4. Confirm the analysis plan ordering enforces baseline-before-ontology and immutability-of-baseline.

## Provenance

- Pre-registration doc — this file. Commit before F6b begins; do not amend after.
- Held-out corpus — `docs/research/f6-ab-corpus/` (30 diffs, manifest.jsonl + labels/<diff_id>.json).
- A/B harness scaffolding — `scripts/f6_ab_harness/` (runner, metrics, Backend protocol; backends are stubs at F6a).
- Baseline replay artefacts — `docs/research/f6-baseline-results.jsonl` + `docs/research/f6-baseline-metrics.json` (created in F6b step 2; immutable thereafter).
- Ontology replay artefacts — `docs/research/f6-ontology-results.jsonl` + `docs/research/f6-ontology-metrics.json` (created in F6b step 3).
- Ship-decision memo — `docs/research/f6-ab-decision.md` (created in F6b step 4).
