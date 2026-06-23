---
title: Sylveste-s10 scoping closeout — small-local-model candidates are already built or redundant
date: 2026-06-22
bead: Sylveste-s10
status: scoping (recommend MOOT)
supersedes_decision: re-opening Phase-1 measurement for C'/E
---

# Sylveste-s10 scoping closeout

## TL;DR

Sylveste-s10 asked: *is there a narrow sub-10B local-specialist workload worth a Phase-1
measurement bead after the microrouter cluster wound down?* That question was already
answered on 2026-05-17 by a brainstorm + parallel flux-research + flux-drive review, all of
which survive on disk. Their two surviving candidates were **C′ (bd duplicate detection)**
and **E (flux-review dispatch pre-filter)**.

Re-verifying against current code/data (2026-06-22), **both have since been built under a
different epic**, and E is functionally already shipped:

- **C′ → shipped.** `sylveste-a4oj.9.3` ("bd create --check-dup: cosine + label overlap +
  recency over open beads") closed 2026-05-06 — *before* s10 was even scoped. The bead-dedup
  feature s10 wanted to "promote to Phase-1" was already done by the a4oj.9 epic.
- **E → shipped as a plugin.** `interverse/intertrust/README.md:3` — "Agent trust scoring for
  Claude Code. Tracks which review agents produce useful findings and which waste tokens …
  feeds that score back into dispatch priority so the good agents run first and the noisy ones
  get deprioritized." That is candidate E's entire value proposition, in production, installed.
  a4oj.9 item 2 ("Embedding-based agent-triage replacement (flux-agent score-relevance)")
  is the same workload, also already epic-tracked.

The kill rule s10 set for itself fires: **no candidate has both (a) measurable current pain
AND (b) >50% probability of >20% improvement over the next-best alternative**, because the
next-best alternative (the a4oj.9 / intertrust work) already exists. Recommend closing s10
**MOOT** with no Phase-1 followups.

This doc records *why* — including two data-integrity findings that further undercut the two
candidates even on their own terms — so the close is auditable and a future session doesn't
re-litigate.

## What s10 already produced (do not redo)

| Artifact | Path |
|---|---|
| Brainstorm (5 candidates, ranking, kill rule) | `docs/brainstorms/2026-05-17-small-local-model-rescoping.md` |
| flux-research synthesis (4 researchers, 27 sources) | `docs/research/flux-research/sub-10b-local-specialists-narrow-devtool-tasks-20260517T2357/SYNTHESIS.md` |
| flux-drive review synthesis (4 reviewers) | `docs/research/flux-drive/2026-05-17-small-local-model-rescoping-20260517T2357/SYNTHESIS.md` |
| Convergent verdict | recorded in `Sylveste-s10` bead NOTES |

The scoping *deliverable* s10 asked for ("a short doc … for each candidate: workload size,
current cost, kill-rule") is, in substance, already written across those three docs. The only
thing missing was a verification pass against current code — which is this doc.

## Candidate-by-candidate verification (2026-06-22)

### C′ — bd duplicate detection (embedding)
- **Status: built and closed.** `sylveste-a4oj.9.3`, closed 2026-05-06.
- **Ground truth never existed anyway.** `.beads/issues.jsonl` has 3,594 beads. There is **no
  `duplicate-of` relationship type** in the schema (relationship types present:
  `parent-child`, `blocks`, `relates-to`, `depends-on`, `discovered-from`, etc. — verified by
  parsing every `dependencies` entry). Only **7 of 3,594** beads mention "duplicate" in
  close_reason/resolution text. The flux-research call that C′ was "BLOCKED by ground-truth
  gap" is confirmed: there are ~7 fuzzy positives and zero structured labels — you cannot
  measure precision/recall on that. The shipped a4oj.9.3 sidesteps this by using a live
  cosine+recency gate at create-time (no offline eval), which is the correct call.
- **Verdict: MOOT — already shipped; offline measurement was never feasible.**

### E — flux-review dispatch pre-filter
- **Status: functionally shipped (intertrust) + epic-tracked (a4oj.9 item 2).**
- **Its "gold-standard ground truth" is an instrumentation artifact.** s10's NOTES and the
  flux-research synthesis both lean on "42.9% zero-output rate = immediate ground truth, no
  labeling needed." Re-checked `~/.claude/interstat/metrics.db` (now 8,264 runs, 3,475 with
  `output_tokens=0` = 42.0%): **every single `output_tokens=0` row also has
  `result_length=0/NULL`, and zero rows have `output_tokens=0` with `result_length>0`.** That
  perfect correlation means `output_tokens=0` is the parser failing to capture output, not "the
  agent ran and reported no findings." A genuine no-findings dispatch still emits output tokens
  ("nothing found here"). So E's label is "did our telemetry parse this run," not "was this
  dispatch useless." Training a classifier on that learns to predict parser gaps. This is
  exactly the *invisible false-negative feedback loop* fd-systems flagged (P1.4), made concrete.
- **The real flux-review corpus is tiny.** E targets flux-review triage specifically, not all
  agent dispatch. Flux-ish dispatches total **558**, and per-agent counts are single/low-double
  digits (fd-resilience: 4, fd-perception: 7, fd-decisions: 12). The 8,264 figure is every
  agent across every workflow — wrong denominator for E.
- **It duplicates intertrust.** `interverse/intertrust/README.md` describes precisely E's job
  and is installed. E is not "pioneering"; it is re-implementing in-house infrastructure.
- **Verdict: MOOT — redundant with intertrust; ground-truth signal is a telemetry artifact.**

### A (lens triage), C (P-tier/type), D (commit-msg scoring)
- Killed in the original brainstorm for sound reasons (corpus too small / regex-covered /
  judgment tasks with noisy labels). No re-litigation. **MOOT.**

### B — Explore-subagent dispatch resurrection
- Always *deferred*, not promoted: it depends on `Sylveste-9ve` diagnosing whether Explore
  dormancy (zero dispatches since 2026-04-21) is a *cost* problem (→ SLM could help) or a
  *workflow/instrumentation* problem (→ SLM irrelevant). That diagnosis is a 30-min git/log
  check, not an SLM project. **B does not belong to s10's scope.** It is correctly owned by
  Sylveste-9ve. No s10 followup needed; 9ve stays as-is.

## Honest recommendation

**Close Sylveste-s10 MOOT. File no Phase-1 followups.** (User to close — do not auto-close: this
is a P-level scoping bead and the close depends on accepting "already built elsewhere" as the
disposition, which warrants a human nod.)

The microrouter lesson generalizes one more step: not only is "we could fine-tune a model" not
enough — here, even the two candidates that *survived* skeptical review turned out to be either
already solved by cheaper non-SLM means (a4oj.9.3 create-time cosine gate; intertrust trust
scoring) or resting on a ground-truth signal that doesn't mean what it appears to. There is no
sub-10B *generative* local-specialist workload in the current Sylveste surface that clears the
bar. The honest disposition is to stop spending scoping cycles on this class until the workload
distribution materially changes.

### The one thing genuinely worth a *small* check (optional, not an SLM bead)

The interstat telemetry gap is a real bug independent of any model work: `output_tokens=0`
should not be silently equated with "no findings" anywhere downstream (interspect calibration,
intertrust scoring, any future analytics). If any of those systems treat 0-output as a quality
signal, they are training on a parser artifact. That is an **interspect/interstat data-quality
bead**, not a small-local-model bead — and it is the actual latent risk this scoping surfaced.
Worth one followup bead against interspect/interstat, severity P3, ~hours.

## Kill-rule trace (for the record)

s10's own kill rule: *"If no candidate has both (a) measurable current pain and (b) >50%
probability of >20% improvement from a sub-10B specialist over the next-best alternative,
close MOOT and do not file followups."*

- C′: next-best alternative (a4oj.9.3 cosine gate) **already shipped** → improvement margin = 0. Fails (b).
- E: next-best alternative (intertrust) **already shipped**; measurable pain (cost ~$5/mo, latency unvalidated) is negligible → fails both (a) and (b).
- A/C/D: fail at the brainstorm stage.
- B: out of scope (owned by Sylveste-9ve).

All candidates fail the rule. **MOOT is the pre-registered outcome.**
