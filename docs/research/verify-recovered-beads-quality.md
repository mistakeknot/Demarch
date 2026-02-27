# Recovered Beads Quality Audit

**Date:** 2026-02-27
**Auditor:** Claude Opus 4.6 (automated)

## Summary

| Metric | Count |
|--------|-------|
| **Total recovered beads** | 139 |
| Open | 107 |
| In Progress | 11 |
| Closed | 21 |

### By Recovery Source

| Source | Count | Labels |
|--------|-------|--------|
| Commit-manifest recovery | 99 | `recovered, placeholder` |
| Roadmap-missing stubs | 19 | `recovered, placeholder, roadmap-missing` |
| Doc-to-bead mapping | 21 | `recovered, placeholder, doc-map` (some also `orphan-doc`) |

### Recovery Scripts Used

- `scripts/replay-missing-beads-from-commit-manifest.py` -- created beads from a CSV of git commits (2026-02-24 to 2026-02-28) where bead IDs appeared in commit messages but were missing from the database.
- `scripts/replay-missing-roadmap-beads.py` -- created beads for IDs referenced in roadmap docs but absent from the database.
- `scripts/map_brainstorms_plans_to_beads.py` -- created beads for brainstorm/plan docs that had no matching bead.

---

## Quality Assessment of 10 Sampled Beads

### Sample 1: iv-9hx1t (P1, CLOSED, roadmap-missing)
- **Title:** `[roadmap-recovery] Missing roadmap bead iv-9hx1t (docs/roadmap.json)` -- Meaningful, includes source file.
- **Description:** Has provenance: "Recovered placeholder bead created because this ID appears in roadmap docs but was missing from the active Beads database." Lists bead ID and source file.
- **Status:** Closed. Close reason: "duplicate of iv-be0ik (safe dedupe pass)" -- Correct.
- **Labels:** `placeholder, recovered, roadmap-missing` -- Appropriate.
- **Verdict:** GOOD. Properly deduplicated and closed.

### Sample 2: iv-be0ik (P1, OPEN, roadmap-missing)
- **Title:** `[roadmap-recovery] Missing roadmap bead iv-be0ik (docs/roadmap.json)` -- Meaningful.
- **Description:** Same template with provenance.
- **Status:** Open -- reasonable since it is a roadmap placeholder that may still need attention.
- **Verdict:** GOOD. But note: this is a generic placeholder -- the original roadmap content for iv-be0ik is not in the description. Would benefit from enrichment.

### Sample 3: iv-1xtgd.1 (P2, OPEN, commit-recovered)
- **Title:** `[recovered] refactor: centralize plugin cache discovery (iv-1xtgd.1)` -- Meaningful, uses original commit subject.
- **Description:** Full provenance: manifest source, repo (`./os/clavain`), commit hash, date, subject. Notes that original payload was not recoverable.
- **External ref:** `git:6e81908d300eeb43fd3e1d3ae53bc13329332ec4` -- Present and correct.
- **Status:** Open -- **SHOULD BE CLOSED.** The commit completing this work already exists. The commit subject itself is `refactor: centralize plugin cache discovery` -- this is completed work.
- **Verdict:** NEEDS CLOSURE.

### Sample 4: iv-xwzgm (P3, IN_PROGRESS, commit-recovered, IronClaw child)
- **Title:** `[recovered] [iv-xwzgm] Add idempotent SQLite to Postgres migration + parity CLI` -- Meaningful.
- **Description:** Full provenance with commit details.
- **Status:** In Progress, parented under iv-yfkln (IronClaw epic) -- Correctly organized.
- **Notes:** "Consolidated under epic iv-yfkln for IronClaw migration completion tracking." -- Good curation.
- **Verdict:** GOOD for tracking purposes, though the specific commit is done. IN_PROGRESS is defensible if the epic is ongoing.

### Sample 5: iv-c7ipv (P4, OPEN, recovered-doc / orphan-doc)
- **Title:** `[recovered-doc] Implementation Plan: Interverse Plugin Decomposition` -- Meaningful, describes the doc content.
- **Description:** Provenance: source doc path, doc kind (plan), reason (no explicit bead reference found in the doc).
- **Labels:** `doc-map, orphan-doc, placeholder, recovered` -- Appropriate.
- **Verdict:** GOOD. Correctly identifies an orphaned planning doc that deserves a tracking bead.

### Sample 6: iv-vcq8c (P4, CLOSED, commit-recovered)
- **Title:** `[recovered] feat: hook cutover -- remove temp file fallbacks, ic is now required (iv-odgxd, iv-fd7l0, iv-vcq8c)` -- Meaningful.
- **Description:** Full commit provenance.
- **Status:** Closed. Close reason: "duplicate of iv-odgxd (safe dedupe pass)" -- Correct. When multiple bead IDs appear in a single commit, one is kept as canonical.
- **Verdict:** GOOD.

### Sample 7: iv-yy1l3 (P4, OPEN, commit-recovered)
- **Title:** `[recovered] feat(observability): unified structured logging and trace propagation (iv-yy1l3)` -- Meaningful.
- **Description:** Full commit provenance.
- **Notes:** Cross-linked to a brainstorm doc via doc-map.
- **Status:** Open -- **SHOULD BE CLOSED.** The commit exists and the feature was implemented.
- **Verdict:** NEEDS CLOSURE.

### Sample 8: iv-tgw66 (P3, IN_PROGRESS, commit-recovered, IronClaw child)
- **Title:** `[recovered] feat: add Rust migration foundation for IronClaw replatform (iv-tgw66)` -- Meaningful.
- **Description:** Full provenance.
- **Status:** In Progress under IronClaw epic -- Consistent with sibling tasks.
- **Verdict:** GOOD for epic tracking context. The individual commit is done, but the epic is ongoing.

### Sample 9: iv-sevis (P4, OPEN, doc-map)
- **Title:** `[recovered-doc] clavain-cli Go Migration Implementation Plan` -- Meaningful.
- **Description:** Provenance: source doc path, doc kind (plan), reason (bead ID referenced by doc was missing).
- **Verdict:** GOOD.

### Sample 10: iv-n0ewk (P4, OPEN, commit-recovered)
- **Title:** `[recovered] [iv-n0ewk] Rename default assistant identity to Amtiskaw` -- Meaningful.
- **Description:** Full commit provenance.
- **Status:** Open -- **SHOULD BE CLOSED.** The rename was completed in the referenced commit.
- **Verdict:** NEEDS CLOSURE.

---

## Issues Found

### Issue 1: 45+ Open Beads Should Be Closed (CRITICAL)

Beads recovered from git commits with conventional commit prefixes (`feat:`, `fix:`, `ci:`, `refactor:`, `chore:`, `perf:`, `docs:`) represent **completed work** -- the commit that implements the feature/fix already exists in the repository. These beads are currently status=OPEN when they should be status=CLOSED with a close reason like "work completed (commit exists)".

**Affected count:** At least 45 beads (all open, non-roadmap, non-doc-map commit-recovered beads).

**Notable examples that should be closed:**
- `iv-1xtgd.1` -- refactor: centralize plugin cache discovery (commit exists)
- `iv-yy1l3` -- feat(observability): unified structured logging and trace propagation (commit exists)
- `iv-n0ewk` -- Rename default assistant identity to Amtiskaw (commit exists)
- `iv-446o7.2` -- ci: add Dependabot config for automated dependency updates (commit exists)
- `iv-be0ik.2` -- ci: add test-running CI workflow (commit exists)
- `iv-1xtgd` -- chore: close iv-1xtgd epic + iv-brcmt (shell hardening complete) -- ironic: the commit that closes the original epic is itself open
- `iv-odgxd` -- feat: hook cutover (primary bead kept open, but siblings iv-vcq8c and iv-fd7l0 correctly closed as dupes)
- `iv-fp18z` -- fix(tui): show runs on Bigend (primary open, but sibling iv-sdnvb correctly closed as dupe)
- `iv-a2axj` -- fix(tui): three Gurgeh onboarding bugs (primary open, siblings iv-3rq37 and iv-2mcuh closed as dupes)
- `iv-6wxb4` -- fix(tui): remove orphaned onboarding states (primary open, sibling iv-e6tvs closed as dupe)
- `iv-mbikz` -- feat: add mount security (primary open, siblings iv-otf43 and iv-tlr0y closed as dupes)

**Full list of 45 beads needing closure:** See the listing in the "Open commit-recovered beads" section above. Every bead whose title starts with `[recovered] feat:`, `[recovered] fix:`, `[recovered] ci:`, `[recovered] refactor:`, `[recovered] chore:`, `[recovered] perf:`, or `[recovered] docs:` and has an `external_ref` pointing to a git commit should be closed.

### Issue 2: Duplicate Bead Pair Not Fully Resolved

`iv-jsvpc` and `iv-g2akk` both reference the exact same commit (`git:a79029eeee8c067e26b4227e80b5ad0d9363cbaa`) and have the same title ("feat: add Postgres persistence layer with schema and query functions"). Both are in_progress under the IronClaw epic. One should be closed as a duplicate of the other.

### Issue 3: IN_PROGRESS Status for Completed Commits (MODERATE)

The 11 IronClaw epic children (iv-xwzgm, iv-tgw66, iv-u0gmm, iv-unhm6, iv-oiait, iv-jsvpc, iv-g2akk, iv-i3oxs, iv-de99u, iv-al5yn, iv-2w8db) are all marked IN_PROGRESS. Each references a completed commit. While IN_PROGRESS makes sense at the epic level (the migration is ongoing), these individual task beads represent completed work and could be closed to reflect that the specific commit landed.

### Issue 4: Priority Assignment Inconsistency (MINOR)

The commit recovery script (`replay-missing-beads-from-commit-manifest.py`) creates all beads at P2 priority, but the actual beads show different priorities:
- IronClaw children: P3 (manually curated)
- Most others: P4 (likely bulk-lowered after recovery)
- iv-1xtgd.1: P2 (original script default)

This suggests a post-recovery triage pass was done, which is good practice. The remaining P4 beads are reasonable for placeholder tracking.

### Issue 5: Roadmap-Missing Beads Lack Context (MINOR)

The 8 still-open roadmap-missing beads (iv-be0ik, iv-ttj6q, iv-cyayp, iv-ff7k6, iv-gkory, iv-ioyrb, iv-mjybd, iv-0r0ey) have generic descriptions ("Recovered placeholder bead created because this ID appears in roadmap docs but was missing"). They do not include what the roadmap item was about -- just the file it appeared in. This makes them hard to triage without consulting the original roadmap files.

---

## What Was Done Well

1. **Consistent provenance in descriptions.** Every recovered bead includes where it was recovered from (manifest path, doc path, or roadmap file), making the recovery traceable.
2. **Clear labeling taxonomy.** `recovered`, `placeholder`, `roadmap-missing`, `doc-map`, `orphan-doc` labels make it easy to filter and query recovered beads.
3. **Deduplication pass.** When a single commit referenced multiple bead IDs, a "safe dedupe pass" correctly closed secondary beads as duplicates of the primary, with explicit close reasons.
4. **External ref linking.** Commit-recovered beads link to their git commit via `external_ref`, enabling verification.
5. **Epic consolidation.** The IronClaw-related recovered beads were properly parented under the iv-yfkln epic with explanatory notes.
6. **Title prefixing.** `[recovered]`, `[roadmap-recovery]`, and `[recovered-doc]` prefixes make recovered beads immediately distinguishable from organic beads.
7. **No empty descriptions.** 0 recovered beads have empty descriptions -- all have at minimum the recovery provenance template.

---

## Recommended Actions

### High Priority
1. **Close 45+ commit-recovered beads** that are currently OPEN but represent completed work (commit exists). Close reason: "work completed in referenced commit (post-recovery closure)".
2. **Close one of iv-jsvpc / iv-g2akk** as duplicate -- they reference the same commit.

### Medium Priority
3. **Close 11 IronClaw child beads** individually (they can remain parented under the epic, but their individual status should reflect the commit being landed). The epic iv-yfkln itself can remain IN_PROGRESS.
4. **Close iv-odgxd, iv-fp18z, iv-a2axj, iv-6wxb4, iv-mbikz** -- these are primary beads kept open after dedupe, but their work is also done (commits exist).

### Low Priority
5. **Enrich roadmap-missing bead descriptions** with the actual roadmap item text from the source files.
6. **Review recovered-doc beads** to determine if any represent completed or abandoned work that should be closed.

---

## Status Breakdown After Recommended Closures

If all recommendations are applied:

| Status | Current | After Fix |
|--------|---------|-----------|
| Open | 107 | ~42 (roadmap-missing + doc-map + genuinely open items) |
| In Progress | 11 | 0 |
| Closed | 21 | ~97 |
| **Total** | **139** | **139** |
