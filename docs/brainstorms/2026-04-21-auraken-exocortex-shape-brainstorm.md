---
artifact_type: brainstorm
stage: discover
related_beads:
  - sylveste-i0px  # Auraken thinker-profile system (parent)
  - sylveste-2xzz  # Schema v1 (current leaf)
  - sylveste-am7w  # Meadows validation gate
  - sylveste-22oi  # Hermes pivot epic
  - sylveste-heh8  # Auraken-as-Hermes deployment
related_memories:
  - project_auraken_hermes_pivot.md
  - project_auraken_thinker_profile_system  # implicit in handoff doc
  - user_ai_space_goal.md
---

# Auraken as Exocortex — Product Shape Brainstorm

## What This Is

A **shape question**, not an implementation question. The thinker-profile system (sylveste-i0px) is currently framed as Auraken's *internal proprietary moat*: a curated roster of thinker-profiles (Meadows, Appleton, Wei, Rao, Thompson-or-sub) extracted from public corpora and used invisibly inside Auraken to critique, reframe, or reason. Per PHILOSOPHY.md principle 8, frameworks apply invisibly by default, revealable on request.

The question on the table: what if Auraken's best form is an **exocortex** where a power user (Alex as archetype) can (a) pour their own writing in and query themselves, and/or (b) handcraft additional thinker-profiles bespoke to their own problem space — *using the same pipeline Auraken uses internally*?

This doc names three product shapes, the tensions between them, and where a flux-review can pressure-test before schema v1 locks.

## The Three Shapes

### Shape A: Internal Moat (status quo in handoff)

**What ships.** Auraken-the-companion with a pre-curated profile roster baked in. Users never see the profiles directly. They get "an assistant that seems unusually good at noticing leverage points and epistemic-status drift." The profiles are an engineering asset owned by Auraken.

**Who it serves.** General Auraken users — the cognitive-augmentation-companion target.

**Moat.** Curation quality + validation discipline (Meadows 12-point rediscovery gate). Competitors can't replicate without equivalent corpus work.

**Economics.** Single-product subscription. Value compounds per-profile-added on Auraken's roadmap.

### Shape B: Self-Corpus Exocortex

**What ships.** Auraken-plus-upload. User points Auraken at their own writing (essays, notes, journals, drafts). Pipeline extracts *their* frames and moves from *their* corpus. Auraken can now: recall forgotten connections, surface inconsistency between past-self and present-self, dialogue with user-as-past-thinker, flag when new writing diverges from established voice.

**Who it serves.** Power users with substantial personal corpora. Alex's archetype: writer, researcher, anyone with 50K+ words of accumulated thinking who wants their past self queryable.

**Moat.** Same pipeline as Shape A. Consent is clean — user owns the corpus. Privacy is the differentiator (local-first or signed retention terms).

**Economics.** Higher price tier or professional add-on. Stickiness is extreme once a user's corpus is indexed.

### Shape C: Handcrafted-Thinker Substrate

**What ships.** Auraken-plus-authoring. User assembles bespoke thinker-profiles for thinkers *not* in the curated roster: a niche philosopher, a domain expert, a dead relative's letters, a fictional character the user wants to dialogue with. Pipeline extracts frames/moves; user curates, edits, annotates. Profile becomes a critic/interlocutor available alongside the curated roster.

**Who it serves.** Advanced practitioners. Researchers with their own reading lists. Writers building internal councils. People with specific cognitive companions they want to instantiate.

**Moat.** Platform-shape, not roster-shape. Auraken becomes the authoring substrate for personal thinker-councils. Network effects possible via profile-sharing (opt-in).

**Economics.** Platform play. Could be tiered (free: curated roster / paid: self-authoring / enterprise: team-shared profiles). Legal surface area expands — third-party thinker data at scale.

## Tensions Worth Surfacing

### Tension 1: Moat direction

Shape A's moat is *curation quality*. Shape C's moat is *the substrate*. These are genuinely different bets. Shape A rewards patient investment in a small roster; Shape C rewards building a good authoring UX and letting users populate. The engineering overlap is large (same pipeline) but the business discipline diverges: Shape A says "ship more profiles"; Shape C says "ship better authoring."

### Tension 2: PHILOSOPHY principle collision

Principle 8 endorses invisible framework application. Shape A honors this natively. Shape B is neutral (user's own frames applied to user's own writing — no opacity concern). Shape C partially violates: user-authored profiles have provenance visible to the author by construction, and profile-sharing makes them visible to recipients. Is that a problem or a feature? Principle 8 says default-invisible, revealable on ask. Shape C makes "reveal" the default for some profiles. Needs reconciliation.

### Tension 3: Camera vs engine

PHILOSOPHY anti-dependency: preserve cognitive struggle. Shape B risks becoming the engine, not the camera — user leans on Auraken to remember instead of building their own memory. Shape A and C are less exposed (they reframe rather than recall). Is self-corpus recall a principle violation or a legitimate extension? The line: does retrieval replace the user's thinking, or prompt it?

### Tension 4: Consent surface area

Shape A: industry-default consent (public corpora, no individual opt-in at extraction time). Shape B: user consents to their own corpus — trivial. Shape C: user is extracting third-party data into load-bearing profiles. Even if the user is the only consumer, the extraction still happened. If profile-sharing ships, consent becomes a product-level legal question, not a curation-ops question.

### Tension 5: Validation discipline

Meadows gate (rediscover 12 leverage points) is the quality bar for Shape A. Shape B inherits a weaker version (does the pipeline rediscover *the user's* framework from their writing? The user is the ground truth, but they may not be able to articulate what the pipeline should find). Shape C has no validation gate — user-authored profiles ship at whatever quality the user accepts. Does the product need a "profile health score" surfaced to the user, and what does unhealthy mean?

### Tension 6: Pivot cost against Hermes roadmap

Current Auraken is pivoting to Hermes-overlay (sylveste-22oi). Shape A fits that cleanly — personality + MCP + skill pack. Shape B requires corpus ingestion UX (new surface). Shape C requires authoring UX (significantly more new surface). How much of the Hermes pivot needs to harden before exocortex shapes are addressable? Does exocortex pull Auraken back toward a standalone product and away from the overlay?

## Assumptions Worth Challenging

1. **Alex is representative.** The archetypal power user may not have a population behind him sufficient to support Shape B economics.
2. **Self-corpus extraction works.** The pipeline is designed for thinkers with enough corpus *and* canonical structure (Meadows essays, Appleton digital garden). A user's mixed journals + drafts + Slack-like notes may be too noisy.
3. **Handcrafting produces usable profiles.** Curation discipline (spotting overfitting, rarity-weighting, scope-metadata consistency) is nontrivial. Asking users to do it well is a UX research question with no data yet.
4. **Network effects are reachable.** Profile-sharing assumes users want to share and that shared profiles transfer. Transfer is an empirical question (does a profile someone else built feel useful to me?).
5. **Principle 8 scales.** It's a design principle for a companion. Does it still hold when profiles are user-visible authoring artifacts?
6. **Internal moat and platform substrate can coexist.** Can Auraken ship both the curated roster *and* the authoring substrate without the economics collapsing one into the other?

## What a Flux-Review Can Help With

- **fd-decisions**: Reversibility of schema-v1 commitment, option framing, explore/exploit balance on which shape to validate first.
- **fd-systems**: Feedback loops between shapes (does Shape B usage feed Shape A curation? Does Shape C dilute Shape A brand?).
- **fd-user-product**: Problem validation for Shape B/C users, scope creep risk against Hermes pivot, MVP definition.
- **fd-people**: Trust dynamics around user-authored profiles, power/authority when profiles are shared across teams.
- **fd-resilience**: Antifragility of each shape under adversarial use (prompt injection via uploaded corpus, users who build bad profiles and blame Auraken).
- **fd-perception**: Mental-model risks — is "exocortex" an accurate metaphor or one that creates the wrong expectations?

## What This Doc Is NOT

- Not a commitment. Schema v1 can accommodate all three shapes with one field (`profile_origin: curated | user_authored | self_corpus`) — that decision is cheap and I flagged it separately.
- Not a roadmap. Sequencing (A first, then B, then C?) is exactly what the review should help pressure-test.
- Not abandoning the current directive. Schema v1 + validator (sylveste-2xzz) is still next. This is a scope pause before the schema locks assumptions.
