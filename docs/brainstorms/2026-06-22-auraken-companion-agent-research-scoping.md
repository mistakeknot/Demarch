---
artifact_type: scoping
bead: sylveste-rcn8
date: 2026-06-22
author: backlog scope-spike agent (autonomous)
status: SCOPING — not executed, recommend PARK (mostly-redundant)
---

# Scoping: Auraken companion-agent research (Soren / Auren / Pi / Replika patterns)

**Bead:** sylveste-rcn8 (P1, research) — "Research leading personality-driven companion agents
(Soren/Nomi, Auren, Pi by Inflection, Replika, Character.ai) for patterns in: empathetic mirroring,
memory architecture, personality consistency, onboarding UX, conversational depth progression, and
user attachment. Identify foundational improvements for Auraken."

**This is a scoping doc, not the research. The platform doctrine is test-null-hypothesis-first: a
multi-day literature/competitive study needs a pre-registered kill rule before it runs. This doc
establishes that the null hypothesis is largely already confirmed — most of the bead's surface has
been covered, and the architecture pivot moots several of its dimensions. Recommendation: PARK; if
pursued, scope to a narrow residual delta with a hard kill rule.**

---

## 1. What the bead assumes vs. what Auraken actually ships

The bead reads as a *companion-app* competitive scan — the named comparables (Replika, Pi, Nomi,
Character.ai) are persistent-relationship emotional companions whose moats are exactly the dimensions
listed: long-horizon **memory architecture**, **user attachment**, and hosted **onboarding UX**.

Auraken is not that product, and has not been since the 2026-04 pivot. Verified against docs:

- **Stateless Hermes overlay, not a hosted companion.** The shipped distribution is a SKILL.md +
  an `auraken-lens` MCP that shells out to a Go binary and returns a single object
  `{lens, rationale, next_question}` (or `{empty: true}`).
  Source: `docs/prds/2026-05-25-auraken-distribution-v01.md:14-15`;
  `docs/brainstorms/2026-05-25-auraken-distribution-v01-brainstorm.md:14-18`.
- **No persistent profile/memory store in the shipped product.** The cold-start work
  (`sylveste-248r`, draft `docs/brainstorms/2026-06-22-auraken-onboarding-bootstrap-protocol.md`)
  explicitly documents that "web intake, profile seeding, phase-varying system prompts — assume
  infrastructure that the shipped product does not have." So the bead's "memory architecture" and
  hosted "onboarding UX" dimensions are aimed at a product Auraken deliberately is NOT building.
- **Anti-dependency is a stated philosophy principle.** Vision Key Decision #4: "Anti-dependency for
  cognitive augmentation (celebrate independence)."
  Source: `docs/brainstorms/2026-03-30-auraken-vision-expansion-brainstorm.md:18`.
  The companion-app north star is **engagement / attachment**; Auraken's is the opposite. Lifting
  "user attachment" patterns from Replika/Pi is not just redundant, it is *directionally wrong* for
  Auraken's thesis — the relevant question there is the inverse (how to be engaging WITHOUT
  manufacturing attachment), which is a design-ethics question, not a competitive-pattern scan.

## 2. The lens this bead asks for has already been run

flux-review already deployed an agent personaed as an **ex-companion-app personality designer**:

> "Conversational AI designer who led personality and dialogue design at a major AI companion company
> (Replika, Character.ai, or Pi.ai) and left because of concerns about emotional manipulation …
> Expert in dialogue act theory, pragmatics, Gricean maxims, and the psychology of parasocial
> [attachment]."
> — `fd-conversational-ai-personality`, `.claude/flux-gen-specs/auraken-use-case-landscape-adjacent.json`

That review produced concrete, Auraken-specific findings on exactly the bead's topics:

- **P1-3 — style-mirroring circuit breaker** (empathetic mirroring): mirror vocabulary/humor/
  directness, do NOT mirror distress/catastrophizing/self-deprecation.
- **P1-4 — negative-feedback recovery journey** (conversational depth / repair): the highest-risk
  conversational moment, currently undesigned.
- (Cognitive-augmentation agent) **P1-2 — lens-selection paradox & progressive scaffolding**
  (depth progression).
  Sources: `docs/research/flux-review/auraken-use-case-landscape/2026-03-30-synthesis.md:53-90`.

The recommendation/discovery half of the companion experience was separately covered by the ambient
-recommendation research for `sylveste-muf`:
`docs/research/flux-drive/auraken-use-case-landscape/ambient-recommendation-research.md` (2026-03-31)
— berrypicking, information-foraging, prepared serendipity, browse-vs-search cognition.

The first-session / cold-start dimension is owned by **P1-1** (cold-start tier) and the in-flight
`sylveste-248r` onboarding draft (dated today).

**Net coverage map of the bead's six dimensions:**

| Bead dimension            | Already covered by                                        | Residual? |
|---------------------------|-----------------------------------------------------------|-----------|
| Empathetic mirroring      | flux-review P1-3 (circuit breaker)                         | thin      |
| Memory architecture       | MOOT — product is stateless overlay                       | none      |
| Personality consistency   | SKILL.md voice-rubric (PRD F6); cross-model port sylveste-gaid | thin  |
| Onboarding UX             | P1-1 + sylveste-248r (hosted-intake mooted by pivot)      | none      |
| Conversational depth      | flux-review P1-2 (scaffolding), P1-4 (repair)             | thin      |
| User attachment           | directionally wrong (anti-dependency principle)           | inverse   |

## 3. Evidence-base weakness on the named targets

- **"Soren" and "Auren" appear nowhere** in the repo, docs, or any source except this bead's text and
  the 2026-06-22 backlog-judgment-digest echoing it (`grep -rinE '\bsoren\b|\bauren\b' docs/` returns
  only the digest line). They are not verified comparables; "Auren" (Elysian Labs) and "Soren" are
  weakly-specified at best. A competitive scan anchored on under-specified names is low-signal.
- The strong comparables (Replika/Pi/Character.ai) are already represented through the flux-review
  persona above. Re-doing the scan as a standalone literature crawl would re-derive the same insights
  at higher cost.

## 4. The only residual worth a hypothesis

If anything survives, it is a **narrow design-tactics delta**, not a competitive scan: *which concrete
companion-design techniques transfer to a STATELESS, anti-dependency lens overlay?* Specifically the
turn-level tactics that need no persistent memory — mirroring registers, repair moves, depth pacing
within a single session, and the *anti-attachment* guardrails (the inverse lesson from companion-app
failure modes). Everything memory- or attachment-moat-shaped is out of scope by construction.

## 5. Pre-registered hypothesis, kill rule, method (if pursued)

- **Hypothesis (testable):** A focused review of stateless-transferable companion-design tactics
  surfaces ≥3 concrete, currently-unaddressed changes to the Auraken SKILL.md / lens-response contract
  that are NOT already captured in the 2026-03-30 flux-review synthesis or the sylveste-muf ambient
  research.
- **Phase-1 measurement (do this FIRST, ~1-2 hrs):** Re-read the two existing artifacts
  (`2026-03-30-synthesis.md`, `ambient-recommendation-research.md`) plus the SKILL.md voice-rubric, and
  enumerate which of the bead's six dimensions already have a designed answer. (This doc is most of
  that Phase-1 measurement.)
- **KILL RULE:** If Phase-1 shows the existing synthesis already addresses ≥4 of the 6 dimensions
  (it does — memory and onboarding are mooted, attachment is inverted, mirroring + depth are covered),
  **close sylveste-rcn8 MOOT** and do not run the standalone competitive scan. Only proceed past
  Phase-1 if ≥3 stateless-transferable residual tactics with no existing coverage are found.
- **Method (only if not killed):** 0.5-1 day. No broad web crawl; targeted reading of (a) responsible-
  -personality-design and parasocial-attachment literature for the *anti*-attachment guardrails,
  (b) single-session conversational repair/depth tactics. Output appends to the existing synthesis as
  a "stateless-overlay design delta" section; no new standalone doc, no new beads unless a residual
  tactic is concrete enough to be a SKILL.md edit.
- **Effort:** hours (Phase-1 alone resolves it; the full path is sub-1-day).

## 6. Recommendation: PARK (leaning MOOT)

The null hypothesis — "the companion-agent design space relevant to Auraken is already covered" — is
largely confirmed by the artifacts above. The bead's highest-value framings (memory, onboarding,
attachment) are mooted or inverted by the stateless-overlay + anti-dependency architecture; the
remaining framings (mirroring, consistency, depth) already have flux-review answers. Park behind
shipping v0.1; if it ever surfaces, run Phase-1 (the kill rule will most likely fire MOOT). Do not
launch a fresh multi-comparable competitive scan.
