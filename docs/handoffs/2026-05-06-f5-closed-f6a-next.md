---
date: 2026-05-06
session: ea5b3e3d
topic: f5-closed-f6a-next
beads: [sylveste-46s, sylveste-71nz, sylveste-71nz.1, sylveste-71nz.2, sylveste-t2cs, sylveste-2n8i, sylveste-g939, sylveste-1j30, sylveste-ukd3, sylveste-lf3b, sylveste-05rf, sylveste-lwp7, sylveste-rm8w, sylveste-w8zv]
---

## Session Handoff — 2026-05-06 F5 closed, F6a next

### Directive

> Your job is to **start sylveste-2n8i (F6a: Measurement Pre-registration + Held-Out Corpus)**. This is the gate that mechanically enforces G10's commit-before-code ordering: BEFORE F6b writes any triage backend code, commit the pre-registration doc, the labeled 30-diff held-out corpus, and the A/B harness scaffolding. Read `bd show sylveste-2n8i` and PRD section F6a at `docs/prds/2026-04-21-persona-lens-ontology.md`.
>
> Acceptance criteria:
> - `docs/research/f6-measurement-preregistration.md` committed (primary metric: review-coverage-per-diff; secondary: P0/P1 count, cost-per-finding, user-accepted-verdict-rate; baseline SHA frozen at F6a start; thresholds: ship ≥15% lift at constant-or-lower cost; abandon <5%)
> - 30-diff paired held-out corpus at `docs/research/f6-ab-corpus/` with ground-truth agent-selection labels
> - A/B harness scaffolding (runner only — can execute legacy or yet-to-exist ontology backend, records findings/agents/cost per diff)
> - Sign-off gate enforced via bead dependency
>
> The corpus labeling is human-time (~2hr per PRD §Dependencies). The harness scaffolding + pre-registration doc are code-time.

- **F5 fully closed this session.** sylveste-71nz, 71nz.1, 71nz.2 all done. Full dedup + curator + calibration shipped: candidate=0.625 / similar=0.450 thresholds, 66-pair corpus (16 human-validated), 73 new tests, full lattice suite at 427/427.
- **Follow-up beads filed (don't block F6a, P2):** sylveste-lf3b (rename misleading-prefix fd-agents), sylveste-05rf (auraken lens cleanup for cross-referencing pairs).

### Dead Ends

- **Auto-stage hook in monorepo bundles unstaged changes into commits without `-a`.** Discovered when `git add .beads/issues.jsonl && git commit` absorbed parallel-session deletions. Recovered via forward-fix `15f9d3fa`. Memory `feedback_explicit_pathspec_commits.md` filed; **always use `git commit -- <pathspec>` in this repo**. Applied successfully across all subsequent commits this session.
- **Lexical TF-IDF baseline at threshold 0.5 on cross-source lens pairs returns the same 258 pairs as F4's `detect_duplicates` same-id matcher.** Lexical adds zero signal for auraken↔interlens because they share IDs AND text. Real F5 value is intra-source dedup at low scores; semantic backend swap is justified for V2 calibration but blocked on a richer corpus.
- **Tie-break interview surfaced two findings calibration math couldn't catch:** (1) misleading fd-agent lexical prefixes (e.g., `fd-evidence-pipeline-integrity` is NOT a specialization of `fd-evidence-pipeline` — entirely different review concerns); (2) Auraken lens authoring drift (Systems Thinking literally references N-Ply Thinking in its definition). Both became follow-up beads (lf3b, 05rf) instead of being absorbed silently.
- **bd close blocked by stale `depends_on` edges** when bead framing pivots — for both 71nz.2 and 71nz, parent-epic was carrying as `depends_on` (wrong directionality). Pattern: scan `bd dep list <id>` BEFORE attempting close, not at close time.

### Context

- **F5 deliverables that F6a will consume:**
  - `interverse/lattice/src/lattice/dedup/calibration-v1.json` — threshold artifact (F6b will read this when picking the candidate-same-as floor for ontology-backend dispatch)
  - `interverse/lattice/src/lattice/curator.py` — apply-labels command can replay any labeled corpus, including the F6a 30-diff held-out one if F6a structures labels the same way
  - `interverse/lattice/scripts/sweep_thresholds.py` — sweep harness; F6a's measurement pre-reg can reuse the precision/recall machinery if metrics are framed as binary outcomes
- **F5 enforcement is in code:** curator CLI raises `ValueError` on accept-without-source_independence; G3 is not policy-only.
- **Source independence convention from F5:** all cross-source auraken↔interlens "same" pairs and all intra-source flux-gen variants carry `source_independence=False`. There are NO `source_independence=True` rows in the V1 corpus — the corpora aren't truly independent. F6a should plan for the same shape: 30-diff corpus needs DIFFERENT-PROJECT or DIFFERENT-LANGUAGE labelers if independence is the goal.
- **F6 critical path:** F6a (pre-reg + corpus + harness) → F6b (backend swap + A/B + ship decision). F6b is the MVP milestone of the b1ha epic. F6a is mechanical commit-ordering enforcement.
- **Working-tree mods NOT mine:** `docs/research/2026-05-06-lattice-architectural-findings.md` and `docs/sylveste-vision.md` were modified by parallel sessions during this conversation. Don't touch them; they belong to other agents' work.
- **Stash state:** stash@{0} contains parallel-session "interblog non-pillar" resolution (6 lines for `lattice-architectural-findings.md`). Don't pop it without coordination — that's the parallel session's in-flight work.

### Open beads (priority order)

| Bead | Pri | Title | Status |
|---|---|---|---|
| sylveste-2n8i | P1 | **F6a: pre-registration + held-out corpus** | OPEN, ready (NEXT SESSION DIRECTIVE) |
| sylveste-g939 | P1 | F6b: flux-drive triage backend swap + A/B | OPEN, blocked on F6a |
| sylveste-1j30 | P2 | F7: interlens MCP adapter swap | OPEN, ready (F5 closed) |
| sylveste-ukd3 | P2 | lattice-web V0 — static browse + search | OPEN, ready (F2 closed) |
| sylveste-lf3b | P2 | Rename misleading-prefix fd-agents (F5 follow-up) | OPEN |
| sylveste-05rf | P2 | Auraken lens cleanup for cross-referencing pairs (F5 follow-up) | OPEN |
| sylveste-w8zv | P2 | github upstream rename mistakeknot/interweave → mistakeknot/lattice | OPEN |
| sylveste-lwp7 | P2 | bug: apply_lifecycle_transition mutates et.families | OPEN |
| sylveste-rm8w | P3 | bug: function diagnostic property mismatch | OPEN |
