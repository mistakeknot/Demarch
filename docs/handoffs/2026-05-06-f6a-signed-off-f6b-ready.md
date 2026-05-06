---
date: 2026-05-06
session: 2bfc5864
topic: f6a-signed-off-f6b-ready
beads: [sylveste-g939, sylveste-y6m7, sylveste-1j30, sylveste-ukd3, sylveste-lf3b, sylveste-05rf, sylveste-w8zv, sylveste-lwp7, sylveste-rm8w]
commit: d6cf80a8884df412238f72c8e115a5d6523676a1
supersedes: 2026-05-06-f6a-shipped-signoff-pending.md
---

## Session Handoff — 2026-05-06 F6a signed off, F6b (sylveste-g939) is next P1

### Directive

> **Begin sylveste-g939 (F6b: flux-drive triage backend swap + A/B execution + ship decision).** F6a is signed off and closed; the held-out 30-diff corpus, pre-registration doc, and harness scaffolding are frozen. F6b is unblocked and in `bd ready`.
>
> Pre-reg lives at `docs/research/f6-measurement-preregistration.md` (committed at SHA `d6cf80a8` — the F6b decision memo must reference this exact SHA per pre-reg §Provenance). Baseline SHA for the legacy replay is `f72d3cfd7d72a33c1a97ec37cfe99c5708a5fa0d` (the harness CLI requires `--baseline-sha` and asserts `git rev-parse HEAD == baseline_sha` at replay time).
>
> F6b's analysis-plan ordering (pre-reg §Analysis plan) is non-negotiable: pre-flight → baseline replay (legacy backend, results immutable) → ontology replay → threshold application → discriminating-subset cross-check → reviewer sign-off. The pre-reg's anti-patterns list (§Anti-patterns explicitly forbidden) is the reviewer's verbatim refusal checklist — re-running ontology until favourable, selective filtering, post-hoc threshold tuning, etc.
>
> Robustness check: at least 5 diffs from the 12-diff discriminating subset must be re-labelled by a second labeler before F6b *ships*. Disagreement >30% on the 5-diff sub-sample triggers a corpus rebuild. This is in pre-reg §Robustness; surface it to whoever picks F6b up so the second-labeler pass is queued early, not at the last minute.

### Dead Ends

- **Parent-epic `depends_on` model artifact (sylveste-y6m7).** During F6a sign-off the close attempt failed because sylveste-2n8i had `depends_on: sylveste-b1ha` — a circular gate, since b1ha (the parent epic) can't close until F6b decides ship/abandon, but F6a needed to close to *unblock* F6b. Same edge existed on sylveste-g939 (F6b), sylveste-r3jf (F2, closed), sylveste-j5vi (F1, closed). 71nz (F5) and t2cs (F4) did NOT have it — the pattern is inconsistent across the b1ha epic's children. This session: closed 2n8i with `--force` and removed the b1ha edge from g939 via `bd dep remove`. Filed sylveste-y6m7 (P3) to audit other open epics (sylveste-iaqg, sylveste-oyrf, sylveste-myyw, sylveste-22oi) for the same pattern and document the convention (features should NOT have `depends_on` to their parent epic — that relationship lives in the PRD label and epic_dod).
- **Lattice repo index corruption persists.** `interverse/lattice/` still has the bad git-object error (`fatal: unable to read fad91ef8...`) from the 2026-05-06-f6a-shipped-signoff-pending handoff. HEAD is healthy at `dcbefa49`; working-tree files are intact and the 442-test suite runs green. Do NOT autonomously repair — may be a parallel session's unfinished work. F6b's ontology backend will need to import `interverse/lattice/src/lattice/templates/` at land time; that import works fine despite the index corruption (the corruption is only on `git status`/`git add`, not on file reads). If F6b commits *to lattice*, ask the user first.
- **`bd backup sync` still no-op.** "no backup destination configured." The protocol step ran, did nothing harmful. JSONL still gets auto-exported via the post-write hook (3126 issues, verified). To genuinely enable, run `bd backup init <path>` once.
- **Parallel session activity is heavy.** While this session was working, a parallel session committed `edd5964f` (flux-explore --teams plan landed, sylveste-3xl3.1 deferred) on top of `d6cf80a8`, and the latest.md symlink had already been updated to point to the parallel session's handoff before this one wrote. Working tree shows MM on CLAUDE.md, .claude/settings.json, docs/sylveste-vision.md, docs/research/2026-05-06-lattice-architectural-findings.md, interverse/intership/README.md — none of these are this session's. Don't pop the stash; don't touch the parallel mods.
- **15 bead orphans flagged by `bd orphans`.** They are from parallel-session commits that named beads in messages without closing them (e.g., sylveste-3xl3.1, sylveste-9lp). Not this session's to clean — the actor whose commits triggered the orphan state should run `bd orphans` and close.

### Context

- **F6a artefacts (frozen, do not amend):**
  - Pre-reg: `docs/research/f6-measurement-preregistration.md` at commit `d6cf80a8`. Threshold matrix Row 3 fixed in this session ("+5% to <+15%, 5% inclusive, 15% exclusive") — Row 1 (`≥ +15%` SHIP) now has clean ownership of the 15% boundary per H1 intent.
  - Corpus: `docs/research/f6-ab-corpus/` — manifest.jsonl + labels/_schema.json + 30 d##-*.json labels. All 12 fd-agents present (fd-game-design at floor=1 on d23 only — the corpus is now locked, so any d23 relabel that drops game-design breaks coverage discipline). 12/30 discriminating, complexity 11/11/8 small/medium/large.
  - Harness: `scripts/f6_ab_harness/` — runner.py, metrics.py, cli.py, backends/{base,legacy,ontology,fake}.py. 3/3 tests pass. End-to-end smoke 30/30 diffs materialise via `git show`. LegacyBackend + OntologyBackend stubs raise NotImplementedError; runner specifically catches this and routes to `aggregate.skipped` (any *other* exception still crashes — by design, so the stub→implementation boundary is explicit).
- **F6b implementation contract:** LegacyBackend.triage and OntologyBackend.triage replace the NotImplementedError stubs. The Backend protocol exposes `agents_dispatched`, `findings.{title,body,themes,severity,agent}`, `cost_usd`, `wall_time_sec`, `backend_metadata`. Metrics are computed from these fields — primary (review-coverage-per-diff with 60% token-overlap matcher) and secondaries (agent-F1, P0/P1, cost-per-finding, wall-time). F6b *may* swap in an embedding matcher provided pre-reg §Primary-metric conditions are met (model+version pre-registered, calibrated against F6a corpus, decision stable across both matchers).
- **Sign-off note location:** sylveste-2n8i's notes carry the 4-item checklist verdict + the audit-trail summary (corpus stats, harness pass count, 15%-fix commit SHA). When F6b's decision memo is written, reference both the pre-reg SHA (`d6cf80a8`) and 2n8i's sign-off note for traceability.
- **Push state at session close:**
  - Git: HEAD is `edd5964f` (parallel session's commit on top of mine). origin/main is identical. No git push needed from this session.
  - Beads: pushed via `CLAVAIN_SPRINT_OR_WORK=1 bash .beads/push.sh` — gate satisfied non-interactively (env var bypass per memory `reference_bd_push_dolt_gate.md`). 2n8i close, g939 dep-remove, and y6m7 creation are all on the bead Dolt remote.

### Open beads (priority order)

| Bead | Pri | Title | Status |
|---|---|---|---|
| sylveste-g939 | P1 | F6b: flux-drive triage backend swap + A/B execution + ship decision | OPEN, ready |
| sylveste-1j30 | P2 | F7: interlens MCP adapter swap | OPEN, ready (F5 closed) |
| sylveste-ukd3 | P2 | lattice-web V0 — static browse + search | OPEN, ready (F2 closed) |
| sylveste-lf3b | P2 | Rename misleading-prefix fd-agents (F5 follow-up) | OPEN |
| sylveste-05rf | P2 | Auraken lens cleanup for cross-referencing pairs (F5 follow-up) | OPEN |
| sylveste-w8zv | P2 | github upstream rename mistakeknot/interweave → mistakeknot/lattice | OPEN |
| sylveste-lwp7 | P2 | bug: apply_lifecycle_transition mutates et.families | OPEN |
| sylveste-y6m7 | P3 | Audit + clean parent-epic depends_on edges in b1ha (and other epics) | OPEN (filed this session) |
| sylveste-rm8w | P3 | bug: function diagnostic property mismatch | OPEN |
