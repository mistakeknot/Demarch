# Corpus Manifest — Sylveste-06i.1 Judge Kappa Audit

Frozen: 2026-07-16
Source: /Users/sma/projects/Sylveste/docs/research/flux-drive/ (351 fd-*.md review files across ~90 review directories)

## Selection method

1. Enumerated all `fd-*.md` review files at depth 2 under `docs/research/flux-drive/`, filtered to file size 4KB-20KB (excludes near-empty stub files and unusually long multi-review files that would bias judge context length).
2. Grouped by review-agent basename; selected the 10 most-frequent core review-agent types (architecture, correctness, systems, quality, decisions, safety, user-product, resilience, perception, performance) — these are flux-drive's standing review panel, as opposed to the long tail of one-off esoteric-lens agents (fd-japanese-sword-testing, fd-qanat-headwater-collection, etc.) generated per-review.
3. Randomly sampled 3 files per agent type (seeded shuffle) → 30 files.
4. Per file, extracted the single highest-severity finding (P0/CRITICAL preferred, then P1/HIGH, then P2/MEDIUM, then P3/LOW; ties broken by first-listed) with full text, location, document verdict, and subject line. Extraction delegated to a sonnet subagent under explicit no-fabrication instructions; spot-checked by the orchestrating session.

## Corpus shape

- 30 items, 3 per review-agent type (10 types), balanced by design.
- Severity distribution of extracted findings: 9 CRITICAL, 20 HIGH, 1 MEDIUM, 0 LOW (reflects that flux-drive findings indices are sorted most-severe-first and most reviewed docs had a P0 or P1 to lead with).
- Provenance/model metadata: **none found**. No file in the sampled 30 (nor in a broader grep across the full 351-file corpus) carries frontmatter or body text identifying which LLM/model generated the review. flux-drive's fd-*.md output format has no `model:`/`generated_by:` field.

## Files

See `corpus.json` for the full structured extraction (30 objects: item_number, source_file, review_agent, subject, finding_id, severity, location, summary, full_text, verdict, provenance_model).

## Known limitations

- **Self-vs-other measurement is NOT EVALUABLE.** No provenance metadata exists to identify which model family produced any given finding, so the self-vs-other score-delta sub-measurement cannot be computed from this corpus as constructed. This is a hard data-availability gap, not a judging-design gap — flux-drive would need to start recording generating-model identity in finding frontmatter for this to become measurable in a future run.
- Findings were extracted as (severity, location, summary, full_text) tuples without the full original review document. Judges re-score the finding using the SAME scale the corpus uses (severity tier CRITICAL/HIGH/MEDIUM/LOW) given the finding text and its stated location/subject — they do not re-review the full source artifact (plan/PRD/diff), because the underlying reviewed artifacts are not uniformly available/frozen and re-running full review would not be a re-judging of the SAME finding, it would be a fresh review. This is a scope choice: the audit measures judge consistency in *re-scoring a presented finding*, which is the mechanism that feeds interspect evidence (flux-drive review scores), not judge consistency in *conducting a review from scratch*.
- Only the single highest-severity finding per file was frozen (not all findings in each file) to keep the corpus size tractable at spike-day budget while preserving cross-agent-type diversity.
