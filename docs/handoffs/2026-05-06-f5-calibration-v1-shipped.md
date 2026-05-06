---
date: 2026-05-06
session: ea5b3e3d
topic: f5-calibration-v1-shipped
beads: [sylveste-46s, sylveste-71nz, sylveste-71nz.1, sylveste-71nz.2, sylveste-t2cs, sylveste-dsbl, sylveste-w8zv, sylveste-lwp7, sylveste-rm8w]
---

## Session Handoff — 2026-05-06 F5 calibration v1 shipped

### Directive

> Your job is to **tie-break the 16 low-confidence rows** in `docs/research/f5-calibration-corpus-2026-05-06.jsonl` (sorted lowest-confidence first), then **re-run the sweep** to refresh the V1 calibration artifact. The user paused the AskUserQuestion interview to check the handoff first; if they restart it, they want to be interviewed via AskUserQuestion (NOT prose), one row at a time, options [confirm Claude's call / flip to same / flip to similar / flip to distinct].
>
> Refresh command after edits:
> ```bash
> cd /home/mk/projects/Sylveste/interverse/lattice && \
>   uv run python -m scripts.sweep_thresholds \
>     --in /home/mk/projects/Sylveste/docs/research/f5-calibration-corpus-2026-05-06.jsonl \
>     --report /home/mk/projects/Sylveste/docs/research/f5-dedup-report-2026-05-06.md \
>     --artifact src/lattice/dedup/calibration-v1.json \
>     --target f_half --min-recall 0.85 \
>     --similar-target recall --similar-min-recall 0.95
> ```

- **Beads in flight:** `sylveste-71nz` (F5 parent, in_progress), `sylveste-71nz.2` (F5.5 calibration, in_progress)
- **Closed this session:** `sylveste-t2cs` (F4 connectors), `sylveste-71nz.1` (F5.4 curator CLI)
- **F5.5 acceptance still pending:** ≥50 hand-labeled pairs ✓ (66 labeled), threshold artifact ✓, dedup audit report ✓ — but PRD requires HUMAN labels; current labels are Claude's with confidence flags.

### Dead Ends

- **Auto-stage hook in monorepo bundles unstaged changes into commits without `-a`.** Discovered when `git add .beads/issues.jsonl && git commit` absorbed deletion of `docs/research/2026-05-06-collision-triage.md` (95 lines, parallel session work) plus stripped sections from `2026-05-06-lattice-architectural-findings.md`. Recovered via forward-fix commit `15f9d3fa` restoring from `4de114af`. **Lesson logged in memory `feedback_explicit_pathspec_commits.md`** — always use `git commit -- <pathspec>` in this repo.
- **Lexical TF-IDF baseline at threshold 0.5 on cross-source lens pairs returns the same 258 pairs as F4's `detect_duplicates` same-id matcher.** Lexical adds zero signal for auraken↔interlens because they share IDs AND text. Real F5 value is in intra-source dedup at low scores (where Conway's Mirror vs Strategy as Mask sits at 0.20 and lexical can't separate from noise). Semantic backend swap is justified for a V2 calibration but blocked on labels existing first.
- **bd close blocked by stale dependency edges** when the bead's framing has pivoted. `t2cs` had stale `depends_on` for `dsbl` (post-2026-05-04 rewrite that made dsbl a meta-tracker) and `b1ha` (epic — wrong directionality). Removed both before close. **Pattern:** when a feature's framing shifts, scan `bd dep list` BEFORE attempting close, not at close time.

### Context

- **F5.5 part (b) shipped, parts (a)/(c)/(d) effectively done with Claude-labeled corpus.** The PRD wanted ≥50 hand-labeled pairs by a human; we have 66 labeled by Claude with confidence scores. The 16 low-confidence rows are the actual "human-judgment-required" subset — labeling them tie-breaks the V1 calibration without making the user label all 66.
- **Calibration corpus structure:** 30 cross-source lens pairs (auraken↔interlens, mostly same-id same-content), 16 intra-auraken/interlens lens pairs (where calibration value lives — semantic distinctions like Care-Ing Capacity vs I Don't Care Meter), 20 intra-fd-agent persona pairs (mostly flux-gen naming variants).
- **V1 thresholds:** `candidate_same_as_min_cosine = 0.6250` (P=0.833, R=0.897, F0.5=0.845), `auto_similar_to_threshold = 0.4500` (P=0.745, R=0.974). Distribution: 39 same / 22 similar / 5 distinct.
- **Source independence convention:** All cross-source auraken↔interlens "same" pairs carry `source_independence=False` because interlens IS a derived subset of Auraken's library, not an independent transcription. All intra-source "same" pairs (flux-gen variants, redux lenses) also `source_independence=False`. There are NO `source_independence=True` rows in the V1 corpus — corpora aren't truly independent.
- **Resolver invariant for F5 dedup:** the curator promotes `candidate_same_as → same_as` only when `source_independence` is explicitly set; the curator CLI raises `ValueError` on accept-without-source_independence. G3 enforced as code, not just policy.
- **Subagent commit discipline:** explicit `git commit -- <paths>` worked cleanly for every commit AFTER the bundling incident (4 separate commits, all clean). Memory rule applied successfully. Future commits in this repo MUST follow the same pattern.
- **Key file paths for in-progress work:**
  - `/home/mk/projects/Sylveste/docs/research/f5-calibration-corpus-2026-05-06.jsonl` — labeled corpus (sorted low-confidence first; the 16 review candidates are at top)
  - `/home/mk/projects/Sylveste/docs/research/f5-dedup-report-2026-05-06.md` — sweep table
  - `/home/mk/projects/Sylveste/interverse/lattice/src/lattice/dedup/calibration-v1.json` — versioned artifact (regenerates from sweep)
  - `/home/mk/projects/Sylveste/interverse/lattice/scripts/sweep_thresholds.py` — sweep CLI
  - `/home/mk/projects/Sylveste/interverse/lattice/src/lattice/curator.py` — F5.4 curator (interactive + batch)
- **F5 critical path now:** F5.5 closure requires either (a) user accepts Claude's labels as V1 ground truth and closes 71nz.2, or (b) user tie-breaks 16 low-confidence rows and re-runs sweep before closing.
- **The 16 review rows cluster naturally:** care-attention budgeting (rows 1-2), iterative-shaping metaphors (3), responsibility-laundering naming collision (4, 7 — strongest tie-break candidate), fd-agent qualifier-substantiveness (5, 6), risk/migration adjacency (8, 9, 14), trust angles (10), lookahead lenses (11), systemic-problem (12), planning-uncertainty (13), feedback-loop variants (15, 16). Most are `similar` calls that could legitimately flip to `same` or `distinct`.

### Open beads (lattice family priority order)

| Bead | Pri | Title | Status |
|---|---|---|---|
| sylveste-71nz | P1 | F5: Semantic dedup with calibration + curator CLI | OPEN, in_progress |
| sylveste-71nz.2 | P1 | F5.5: Calibration corpus + threshold sweep + audit | OPEN, in_progress (parts b/c/d shipped; a is Claude-labeled) |
| sylveste-1j30 | P2 | F7: interlens MCP adapter swap | OPEN, blocked on F5 closure |
| sylveste-g939 | P1 | F6b: flux-drive triage backend swap + A/B | OPEN, blocked on F5+F6a |
| sylveste-2n8i | P1 | F6a: pre-registration + held-out corpus | OPEN, blocked on F2 (closed) — actually unblocked |
| sylveste-ukd3 | P2 | lattice-web V0 — static browse + search | OPEN, F2 unblocked it |
| sylveste-w8zv | P2 | github upstream rename mistakeknot/interweave → mistakeknot/lattice | OPEN |
| sylveste-lwp7 | P2 | bug: apply_lifecycle_transition mutates et.families | OPEN |
| sylveste-rm8w | P3 | bug: function diagnostic property mismatch | OPEN |
