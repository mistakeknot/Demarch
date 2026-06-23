---
title: Small-local-model (sub-10B) scoping re-check — Sylveste-s10 is overtaken by parallel work
date: 2026-06-22
bead: Sylveste-s10
status: scoping (re-check after backlog sweep)
supersedes: docs/brainstorms/2026-05-17-small-local-model-rescoping.md (does not delete; updates the conclusion)
---

# Sylveste-s10 scoping re-check

## TL;DR

The scoping work for `Sylveste-s10` was **already done on 2026-05-17** — a brainstorm,
a 4-agent flux-drive review, and a 4-agent flux-research session all exist and converge.
That work surfaced exactly two promotable candidates: **C′** (bd duplicate detection via
embeddings) and **E** (flux-review dispatch pre-filter). As of 2026-06-22, *both have been
overtaken by parallel work that landed under different bead lineages*:

- **C′ is shipped + tracked.** Lexical dup-check shipped in `sylveste-a4oj.9.3`
  (commit `59d9cc36`: `scripts/lib-bd-dup-check.py`, `scripts/bd-create-checked.sh`).
  The embedding extension C′ recommended is already filed as the open bead
  `sylveste-a4oj.9.3.1` ("Semantic-embedding dup detection (extends 9.3 lexical baseline)").
- **E is largely subsumed by interspect.** `interspect-propose` +
  `interspect-override` already analyze the same interstat `agent_runs` dispatch outcomes
  and propose/apply agent exclusions from flux-drive triage. The flux-drive review of s10
  flagged this exact overlap (finding P1.5) and asked for a 30-min discovery before Phase-1.
  That discovery is now answered: the overlap is real and the infrastructure exists.

**Recommendation: close `Sylveste-s10` as MOOT.** Its kill rule already requires a candidate
with both (a) measurable current pain and (b) >50% probability of >20% improvement over the
next-best alternative. With C′ shipped/filed and E covered by interspect, no remaining
candidate clears that bar. Do not file new followups under s10; if the embedding-dedup path
needs work, it lives at `sylveste-a4oj.9.3.1`.

## Verification (file:line / data, not memory)

| Claim | Evidence | Status |
|-------|----------|--------|
| s10 scoping already produced | `docs/brainstorms/2026-05-17-small-local-model-rescoping.md` + `docs/research/flux-drive/2026-05-17-small-local-model-rescoping-20260517T2357/SYNTHESIS.md` + `docs/research/flux-research/sub-10b-local-specialists-narrow-devtool-tasks-20260517T2357/SYNTHESIS.md` | confirmed |
| s10 bead still open | `.beads/issues.jsonl`: `Sylveste-s10 | in_progress | P3` | confirmed |
| C′ lexical dedup shipped | bead `sylveste-a4oj.9.3` close_reason: "Shipped TF-IDF lexical dup detection in commit 59d9cc36" | confirmed |
| C′ embedding extension filed | bead `sylveste-a4oj.9.3.1` open: "Semantic-embedding dup detection (extends 9.3 lexical baseline)" | confirmed |
| E's data signal still live | `~/.claude/interstat/metrics.db` `agent_runs`: 8,264 rows, 42.0% zero-output (research cited 7,615 / 42.9%) | confirmed, fresher |
| E overlaps existing infra | `interverse/interspect/commands/interspect-propose.md` ("Detect routing-eligible patterns and propose agent exclusions") + `interspect-override.md`; both read interstat dispatch outcomes | confirmed |
| No E bead filed | grep of `.beads/issues.jsonl` for prefilter/dispatch-classifier patterns → none | confirmed |

## Why this is MOOT, not park

The microrouter cluster taught the platform that "we *could* fine-tune/build a model" is
not enough — the workload must demand it, and the cheap baseline (heuristic / existing infra)
must be visibly weak. Re-running the s10 kill rule per-candidate on 2026-06-22:

- **C′:** Pain was real, but the cheap baseline (TF-IDF lexical) was *not* tried at scoping
  time and has since shipped. The remaining marginal lift (lexical → embedding) is now its
  own scoped bead with the correct parent. s10 has nothing left to decide here.
- **E:** Cost savings were already judged "negligible (~$5/mo)" in the 2026-05-17 brainstorm;
  the only live motivation was latency, which was never benchmarked and which the flux-drive
  review rated "latency-attractive, recall-risky." More decisively, the *function* exists in
  interspect. Building an embedding classifier to do what evidence-thresholded exclusion
  already does is a duplicate, not an improvement — fails kill-rule clause (b).
- **A, B, C(P-tier), D:** Already killed/deferred at scoping time; nothing changed.

## If the user still wants a generative SLM bet (the honest residual)

The 2026-05-17 flux-research surfaced one candidate *outside* the original 5 that nobody has
acted on: a **code-quality / correctness binary classifier** trained on the LCB corpus
(4,438 gold-labeled, compiler-validated examples), with CommitBench precedent that fine-tuned
3B–7B models beat zero-shot Haiku on code classification, and a real latency win
(~50ms local vs ~300–500ms API) on a *synchronous* path. This is the only residual that
is (a) genuinely generative/learned-model-shaped, (b) backed by clean external + internal
ground truth, and (c) not already covered by shipped infra.

But it does **not** belong under s10 — s10 is a routing/dev-tooling scoping bead and this is
an interfer/code-eval workload. If pursued, file a *fresh* Phase-1 measurement bead in the
interfer/benchmark orbit, pre-registered with the kill rule below. Do not reopen s10 to host it.

## Recommended disposition

1. **Close `Sylveste-s10` MOOT** with a note pointing at `sylveste-a4oj.9.3` (C′ shipped),
   `sylveste-a4oj.9.3.1` (C′ embedding extension, open), and interspect (E subsumed).
   *(Do not close in this session — flagged for the workstation per cloud/bead discipline.)*
2. **Do not file followups under s10.** The embedding-dedup work has a home.
3. **Optional, separate bead (not s10):** code-quality LCB classifier Phase-1, if and only
   if the user is in interfer-eval mode and wants a learned-model bet with a real latency path.
