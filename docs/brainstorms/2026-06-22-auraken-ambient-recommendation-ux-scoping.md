---
artifact_type: scope-spike
bead: sylveste-muf
title: "[auraken] Research: ambient recommendation UX — window shopping vs. over-indexed personalization"
date: 2026-06-22
status: scoping-only
recommend: likely-moot
author: scoping-subagent
---

# Scoping: Auraken ambient recommendation UX research (sylveste-muf)

## TL;DR

**Recommend: likely-moot.** The deliverable this bead asks for already substantially
exists. `sylveste-muf` is dated to "Robinson NTS, 2026-03-30 9:18 AM." That same
window-shopping insight, from the same conversation on the same day, was fed into the
`fd-museum-experience-ambient-discovery` agent of the 2026-03-30 Auraken use-case-landscape
flux-review. That review produced concrete design fixes for ambient/browse-mode
recommendation; it did not leave the question open. Six of the bead's seven research
questions map onto findings that already shipped in
`docs/research/flux-review/auraken-use-case-landscape/2026-03-30-synthesis.md`. The
seventh (affiliate UX) was answered there as a *blocking P0*, not an open research item.

Auraken is also an out-of-tree product (`~/projects/transfer/auraken`) and a P3 bead;
on this machine, MEMORY directs priority to interfere/local-LLM work. This bead should
be closed as superseded by the existing review, with at most a thin "extract the ambient
recommendation design into the Auraken PRD" follow-up if/when Auraken commerce work is
actually scheduled.

## What the bead asks for

Research-only deliverable: leading companion/recommender patterns and seven questions
about ambient ("window shopping") vs over-indexed ("Portland → Patagonia") personalization,
how the Auraken lens system should approach recommendations, browse-mode vs search-mode
cognition, agency-preserving patterns, the deep-context moat vs ProductRecs, and
affiliate/referral UX that avoids the "aggressive salesperson" feel.

## Evidence — what already exists (verified file:line)

All in `docs/research/flux-review/auraken-use-case-landscape/2026-03-30-synthesis.md`:

- **Q1 (why ambient works) + Q2 (why explicit personalization feels wrong)** —
  Finding MU-2 / P1-13 (line 187-191): "Individual recommendations served with individual
  rationales are search results, not discoveries. The Robinson window-shopping insight works
  through adjacency." Fix: surface 2-4 item curated collections connected by non-obvious
  themes. Reinforced by Intelligence-Analysis signal/noise calibration (line ~451): tag
  product mentions as high-noise, weight them below cognitive-augmentation signal — directly
  the "don't over-index on one signal" point.
- **Q3 (how the lens system should approach recommendations)** — MU-1 / P1-12 (line 173):
  explicit mode transitions + user-initiated "gallery mode." Gallery-mode entry point spelled
  out at line 441-444. Use Case Composition Map (P1-14, line ~201) defines the augmentation/
  commerce boundary the lens system must respect.
- **Q4 (browse-mode vs search-mode literature)** — Intelligence-Analysis puzzle-vs-mystery
  routing (line ~459): products are mostly puzzles (a best answer exists), career decisions
  mysteries; layer on Cynefin to route between recommendation and augmentation modes. This is
  the browse/search cognition split, operationalized.
- **Q5 (agency-preserving patterns)** — Constitutional kyo/jitsu framing (line 537): default
  to kyo (ambient awareness, resist persuasion); shift to jitsu only on active-intent signals.
- **Q6 (deep-context moat / entity model)** — Persian-carpet open question (line 468): does the
  four-category entity taxonomy extend to recommendation context, or does ambient recommendation
  need new entity types (purchase history, aesthetic prefs, budget, brand affinity)? This is the
  moat question, already posed as the concrete schema decision.
- **Q7 (affiliate/referral UX without the salesperson feel)** — Answered, and escalated:
  **P0-2** (line ~33) "Affiliate monetization creates undisclosed fiduciary conflict" — deep
  context + affiliate incentive is the single highest reputational risk; resolve before
  recommendations ship. Plus the "gift shop problem" (line 331) and commerce-as-exhibition
  framing (line 446): recommendations should feel like thinking tools, never interrupt
  augmentation. The bead treats affiliate UX as open research; the review treats it as a
  blocking design constraint.

Only the **competitor-pattern survey** (Soren/Nomi, Auren, Pi, Replika, Character.ai) named
in the *bead title* is genuinely not in that review — but that is a different bead
(`sylveste-rcn8`, the companion-agent research spike), not this one. `sylveste-muf` is the
*ambient-recommendation* angle specifically.

## Unverifiable claim in the bead

The bead leans on a ProductRecs cross-reference ("../productrecs … complementary, not
competing"). No `productrecs` directory exists in `~/projects`, in the monorepo, or anywhere
reachable on this machine (checked `~/projects`, repo `apps/*`, and a maxdepth-5 system scan).
The "Auraken solves browse-mode, ProductRecs solves search-mode" framing cannot be grounded
against an artifact that is not present. Any pursuit would have to first locate or reconstruct
ProductRecs, inflating scope.

## Hypothesis (testable)

> A fresh, standalone ambient-recommendation UX research pass on Auraken will surface
> **>=3 actionable design decisions not already present** in the 2026-03-30
> use-case-landscape flux-review (the `fd-museum-experience-ambient-discovery` track).

If it cannot clear that bar, the bead is redundant and should close superseded.

## Pre-registered KILL RULE (test-null-hypothesis-first)

Phase 1 = a 1-2 hour audit, NOT a multi-week research project:

1. Read the `fd-museum-experience-ambient-discovery` findings (MU-1..MU-n) and the
   commerce/gift-shop sections of the 2026-03-30 synthesis in full.
2. For each of the 7 bead questions, mark Covered / Partial / Gap against that review.

**Kill condition:** if >=5 of 7 questions are Covered or Partial (current count from this
scoping pass: 6 Covered/Partial, 1 Gap = the competitor survey owned by `sylveste-rcn8`),
close `sylveste-muf` as **superseded** (not MOOT — the work was done, just elsewhere) and
file at most ONE thin follow-up: "Extract ambient-recommendation design (gallery mode, MU-2
adjacency, kyo/jitsu default, P0-2 affiliate firewall) into the Auraken commerce PRD." Do NOT
launch a new flux-review or literature survey.

**Proceed condition:** only if Phase 1 finds >=3 genuine Gaps AND Auraken commerce is an
actively scheduled epic (it is not, as of 2026-06-22). Even then, fold the new questions into
the *existing* review's open-question list rather than starting fresh.

## Method (if it ran at all)

Phase 1 audit only (above). No new agent dispatch, no web research, no model calls. The
"leading companion agents" survey belongs to `sylveste-rcn8` and should not be duplicated here.

## Effort

- Phase 1 audit: **hours** (1-2h read + map).
- The bead as literally written (full competitor survey + 7-question literature pass +
  ProductRecs comparison): days-to-weeks — but that scope is not justified given the kill rule.

## Honest recommendation: likely-moot

The motivating insight was already routed into a max-quality 4-track flux-review the same
day it was captured, and that review produced shippable design decisions for every angle this
bead raises except the competitor survey (which is a different bead). This is the
parallel/redundant-research pattern the platform's "shipped-state reconciliation" doctrine
(sylveste-sk5s) and the memory note *feedback_docs_match_codebase_not_memory* exist to catch:
a bead proposing fresh research where the answer already sits in `docs/research/`. Close it
superseded; do not spend a research cycle re-deriving MU-1/MU-2/P0-2.
