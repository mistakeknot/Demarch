---
artifact_type: corpus_readme
bead: sylveste-2n8i
gate: G10
parent_prd: docs/prds/2026-04-21-persona-lens-ontology.md
baseline_sha: f72d3cfd7d72a33c1a97ec37cfe99c5708a5fa0d
created: 2026-05-06
---

# F6 A/B Corpus — Held-Out Diff Set

This corpus is the **frozen evaluation set** for the F6b A/B test (legacy flux-drive triage vs. lattice-ontology triage). It is committed *before* any ontology backend code lands so the metrics, diff selection, and ground-truth labels cannot be retrofitted to flatter the new backend. This is gate G10 (measurement pre-registration) made mechanical via bead dependency.

## Corpus shape

- **30 diffs** drawn from real merged commits in this monorepo, sampled to exercise the full flux-drive review-agent roster (technical agents fd-architecture / fd-correctness / fd-quality / fd-safety / fd-performance / fd-user-product / fd-game-design and cognitive agents fd-systems / fd-decisions / fd-people / fd-resilience / fd-perception).
- Each row in `manifest.jsonl` references a commit SHA + summary + label pointer. Diffs are materialized at runtime via `git show <sha>` so the corpus stays compact and stays in lockstep with git history.
- Per-diff ground-truth labels live at `labels/<diff_id>.json` and capture (a) which agents *should* fire, (b) which finding themes a thorough review should surface, (c) labeler rationale. See `labels/_schema.json` for the schema.
- A small `diffs/` directory holds materialized snapshots only for diffs whose source commits are at risk of mutation (rebase, force-push). When `diffs/<diff_id>.diff` exists, the harness prefers it over the SHA replay; this is the audit fallback.

## Diff selection criteria

Each candidate diff was scored against four dimensions:

1. **Roster coverage** — does this diff plausibly trigger ≥ 1 review agent? Diffs that touch only beads-tracker noise, untracked output, or generated artifacts are excluded.
2. **Domain spread** — diffs are spread across detected project domains (web-api, cli-tool, ml-pipeline, claude-code-plugin, library-sdk, tui-app) per flux-drive Step 1.0.1.
3. **Size variety** — small (<200 lines), medium (200–1000), large (≥1000, slicing-eligible per `phases/slicing.md`). V1 distribution: 11 small, 11 medium, 8 large.
4. **Discriminating power** — diffs where legacy and ontology backends are *expected* to disagree on agent selection are preferred over diffs where both backends would trivially agree. Discriminating diffs are flagged `discriminating: true` in labels.

## Ground-truth labeling protocol

- **Labeler:** Anyone with operational fluency in flux-drive's roster (Step 1.2a pre-filter rules, Step 1.2b scoring, the 12-agent technical/cognitive split). The author of F5 (which closed the lattice dedup calibration) labeled the V1 set.
- **Per diff** the labeler reads the unified diff, identifies which of the 12 review agents *should* fire based on the diff's content (changed files, hunks, languages, domains), and records:
  - `expected_agents` — flat list of agent names that *must* fire (precision floor; missing any of these is a recall miss for the system under test).
  - `expected_findings_themes` — list of 2–6 short prose themes a thorough review *should* surface (e.g., `"adds new API endpoint without input validation"`, `"introduces shared mutable state without synchronization"`). These are the ground-truth findings used for the primary metric (review-coverage-per-diff).
  - `rationale` — 1–3 sentences explaining the label, especially for non-obvious choices.
  - `complexity` — small | medium | large (matches Step 1.1 Diff Profile).
  - `discriminating` — true if legacy and ontology backends are expected to disagree on agent selection; false otherwise.
  - `human_validated` — false on V1 (single labeler). Flips to true after sign-off review (see Sign-off below).
- **Source independence convention:** F5 established that auraken↔interlens corpora aren't truly independent. F6 corpus is built by a single labeler (claude-opus-4-7) who also closed F5; therefore `source_independence: false` is the default. A second-labeler pass on a 5-diff sub-sample is recommended before F6b's ship-decision so at least the discriminating diffs have inter-rater agreement.

## Metrics computed against this corpus

See `docs/research/f6-measurement-preregistration.md` for the formal definitions, ship/abandon thresholds, and baseline SHA lock. Briefly:

- **Primary metric: review-coverage-per-diff** — fraction of `expected_findings_themes` covered by the backend's emitted findings, averaged over all 30 diffs. A finding "covers" a theme when a reviewer (or simple keyword match harness) marks the finding as addressing that theme.
- **Secondary metrics:** P0/P1 finding count, cost-per-finding (USD via `estimate-costs.sh`), agent-selection F1 (precision/recall over `expected_agents`), user-accepted-verdict-rate (deferred to longitudinal data once F6b ships; not gated for ship/abandon decision in F6b).

## Sign-off

Before F6b may begin, this corpus and the pre-registration doc must be signed off. Sign-off is enforced via bead dependency `sylveste-g939 (F6b)` blocked by `sylveste-2n8i (F6a)`. Reviewer must:

1. Spot-check ≥ 5 random labels for plausibility.
2. Confirm primary + secondary metric definitions match expected agent behavior.
3. Confirm baseline SHA is frozen and recorded.
4. Mark sign-off in bead notes: `bd update sylveste-2n8i --notes 'F6a sign-off: <reviewer> <date>'`.

## Provenance

- `manifest.jsonl` — one row per diff (schema in `labels/_schema.json`).
- `labels/_schema.json` — JSON-schema fragment for label files.
- `labels/<diff_id>.json` — per-diff ground-truth labels.
- `diffs/<diff_id>.diff` — materialized diff snapshot (audit fallback only; absent when `manifest.jsonl` SHA replay is sufficient).

## Harness

The runner that consumes this corpus is at `scripts/f6_ab_harness/`. See its README for usage. The harness has two backends:

- `legacy` — wraps the current flux-drive triage (Steps 1.0–1.3 of `interverse/interflux/skills/flux-drive/SKILL.md`). On F6a ship, this is a stub raising `NotImplementedError("F6b will land this")`. F6b lands the real wrapper.
- `ontology` — wraps the lattice-template-based triage (`select_personae_for_task` and friends). On F6a ship, this is a stub raising `NotImplementedError("F6b will land this")`. F6b lands the real wrapper.

The harness *runner*, *metrics module*, *Backend protocol*, and *test fake* all ship in F6a so F6b cannot regress the contract.
