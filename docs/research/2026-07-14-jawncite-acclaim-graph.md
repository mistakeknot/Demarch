# jawncite — the domain-agnostic acclaim/citation graph

**Date:** 2026-07-14
**Status:** architecture doctrine (naming + scope decided; schema design PENDING a dedicated session)
**Lineage:** escalated from [2026-07-14-jawnverse-stack-doctrine.md]. That doc scoped a single film aggregator (jawnflicks). The user's insight — *"we could be building something much bigger; not just movies and shows and restaurants but everything, leveraged by lots of other GSV projects"* — promoted the citation **shape** from wikifeedia's internal tables to a shared substrate. This doc captures that module.

---

## What jawncite IS (one sentence)

**A domain-agnostic acclaim graph: the canonical record of "who asserted what about which entity, on what list, at what rank, with how much trust" — a provenance-weighted claims layer that any GSV vertical writes citations into and any consumer reads rankings out of, joined to jawntology for entity identity.**

The atomic unit is a **citation**: *(source, entity_ref, list, rank, trust_tier, provenance)*. Rankings are what *emerge* when you aggregate trust-weighted citations. The name names the unit: verticals **cite into** jawncite; readers **aggregate cites out of** it.

## The three-layer split (resolves "wikifeedia? jawntology? a mix?")

It is **neither** — jawncite is a new peer module. The clean decomposition the melange loop pointed at (finding f-018: `same_as` and `citations` both carry "confidence" but solve *different* problems — "don't conflate them"):

```
  jawntology  — IDENTITY / ontology layer
    "what IS this entity" — works, editions, offers, same_as, canonical IDs
        │ entity_ref (canonical id)
        ▼
  jawncite    — ACCLAIM / assertion layer   ★ NEW MODULE
    "who SAID what about it, how much do we trust them"
    sources · lists · citations · trust_tier · provenance · entity_ref (polymorphic)
        ▲ write            ▼ read
  ┌─────┴──────┬───────────┴────────┬──────────────┬─────────────┐
  wikifeedia   jawnflicks           jawncloud       auraken        solwend
  (food, c#0)  (film/TV, c#1)       (garments,      (cross-domain  (commerce
                                     latent)         reader)        join reader)
```

- **jawntology stays put.** Identity/ontology. jawncite's `entity_ref` joins against `jawntology.works` (etc.) for canonical identity + dedup.
- **wikifeedia is consumer #0** — its citation tables ARE jawncite's shape (the melange loop proved critics/publications/citations are domain-neutral; only the two target-FK columns + food-critic seed rosters are domain-specific). Either retrofit wikifeedia to point at jawncite, or let jawncite supersede it over time.
- jawncite lives in the **shared solwend Neon project** as `pgSchema("jawncite")`, so `jawncite.citations JOIN jawntology.works ON entity_ref = work_id` is a one-liner. (Same pgSchema discipline the user chose for jawnflicks; same discipline uncrancher already proves.)

## Consumer map (grounded by a live disk survey 2026-07-14 + user intent)

| Consumer | Real today? | Read / Write | Evidence |
|----------|-------------|--------------|----------|
| **uncrancher** | ✅ built, strongest fit | READ-leaning, could WRITE | Already denormalizes `works.imdbRating`/`imdbVotes` "to rank lures without a separate lookup"; its films×tropes + `ingest_runs` tables are literally citation/provenance-shaped. Same Neon project, same `pgSchema` discipline. **This is the proof-of-generalization second consumer.** |
| **jawnflicks** | 🔨 to build (consumer #1) | WRITE (ingest lists) + READ (rank) | The forcing function. Ports wikifeedia's shape into film/TV. |
| **jawncloud** | ◐ latent | WRITE source-cites + READ "best source" | `MeasurementSource.sourceType` (`OFFICIAL\|RETAILER\|COMMUNITY\|USER_SUBMITTED`) is structurally identical to jawncite's source/trust_tier model. BUT it just pruned its `Review`/rating model (2026-07-11) and docs say recommendation substrate is "unbuilt, reference-first not fame-first." Real isomorphism, latent demand. |
| **auraken** | ⚠ intended, not on disk | READ (universal cross-domain reader) | User: "auraken would use this for better movie/food/etc recommendations." The `transfer/auraken` path on disk is a chat-analytics scratch dir with no code — the real recommender is unbuilt/elsewhere. **This is the "universal reader" role: recommends over jawncite acclaim signal across every vertical.** |
| **solwend** | ⚠ intended (platform) | READ (commerce join) | User named it. The platform joins jawncite acclaim to jawntology commerce → "acclaimed things you can actually acquire." Loops back to the media-server/intake stack. |

**Mirage (cut from scope):** `fashionsomething` — now a Rust/Bevy spatial game ("how you live is the gameplay"), no entity catalog, no ratings. Its "Signal" is acclaim-*flavored* but there's nothing to cite. Do not design for it.

## Why a shared substrate is justified NOW (not premature)

Rule-of-three: abstract when you have 2–3 concrete instances, not 1 and a dream. jawncite has **two real consumers with genuinely different read/write shapes** (uncrancher: ratings-as-ranking-signal; jawnflicks: lists-of-lists) plus one latent (jawncloud) plus two intended readers (auraken, solwend). That is exactly the evidence band that says "design for extraction, prove it with the different-shaped second consumer" — uncrancher being a *different domain shape already in the same Neon project* is what validates the abstraction instead of guessing it.

The failure mode to avoid: designing the generic `entity_ref` + trust model against only jawnflicks's needs, then discovering uncrancher/jawncloud want a different shape. **Mitigation: design the schema against uncrancher AND jawnflicks together** (the two built/building shapes), treat jawncloud's `sourceType` tiers as a third validation point, and leave auraken/solwend as pure readers (no schema demands, just query the aggregate).

## Open design questions (for the dedicated schema session — NOT decided yet)

1. **`entity_ref` polymorphism.** How does a citation point at "any entity across any domain"? Options: (a) `(entity_type, entity_id)` tuple with no FK (loose, flexible, no referential integrity); (b) FK to a `jawntology.works`-style canonical entity table (tight, but forces every cited thing to be a jawntology work first); (c) a jawncite-owned `entities` registry that mirrors/links jawntology. The melange loop already flagged the polymorphic-CHECK redesign for jawnflicks (2→3 targets); jawncite generalizes that to N domains → the exactly-one-of-N CHECK doesn't scale, so this needs a real design (likely a `domain` discriminator + `entity_id`, joined to jawntology by convention).
2. **Trust model.** wikifeedia's `trust_tier` is hardcoded food-critic seed arrays; `confidence_score` was never implemented. jawncite needs trust to be **per-domain-configurable** (film trade press vs food critics vs garment measurement sources are different rosters) — probably `sources` carry a `domain` + `trust_tier`, and the aggregate scoring is a jawncite-owned function, not per-vertical.
3. **`ingest_method`/`provenance_tier`** (melange f-019): curated (high trust) vs auto-extracted (model-dependent) sources feed the same score → must be distinguishable BEFORE first ingest. This becomes a first-class jawncite column, not a jawnflicks afterthought.
4. **Read API shape.** auraken/solwend are pure readers wanting "rank entities in domain D by weighted acclaim." Is that a SQL view, a materialized ranking table (refreshed on ingest), or a service? uncrancher wants it cheap enough to filter lures inline.
5. **wikifeedia migration path.** Retrofit-in-place (risky — the pgSchema retrofit trap: wikifeedia's raw-SQL idempotency harness references tables unqualified, documented in the stack doctrine) vs supersede-and-dual-write vs leave-as-legacy-consumer-zero.
6. **`@jawnverse/db-client`** shared package (melange f-003/f-033) — jawncite is the natural home / first user of the extracted dual-client idiom.

## Sequencing — NOT yet chosen by the user

The user named the module before picking a build sequence. Candidate paths (decide next):
- **(A) Neutral-jawnflicks-then-extract:** build jawnflicks with domain-neutral schema (entity_ref/sources/trust_tier), extract to `pgSchema("jawncite")` when uncrancher repoints. Lowest risk, abstraction validated by real 2nd consumer.
- **(B) Extract jawncite now:** commit to the shared schema from day 1, design against uncrancher+jawnflicks together, migrate wikifeedia in. Max leverage; designs the generic API before jawnflicks teaches what the shape needs.
- **(C) Doctrine-first:** this doc + a full schema design pass (entity_ref, trust model, read API, migration) as a written deliverable before any code, then scope the build as a `/goal`.

**Recommendation:** With 5 prospective consumers of genuinely different read/write shapes, **(C) then (A)** — finish this doctrine into a schema design (resolve the 6 open questions above, especially `entity_ref` polymorphism and the trust model, against uncrancher + jawnflicks + jawncloud's three real shapes), THEN build jawnflicks against that design so the "neutral schema" is actually correct rather than guessed. Big-bang (B) risks a generic API designed before the first real vertical exercises it.

---

## Provenance of this doc
Established in the 2026-07-14 session that also (a) shipped the jawnverse stack doctrine, (b) fixed wikifeedia's f-033/f-025 comment bugs at source, (c) ran the private media-server migration. User decisions captured here: module name **jawncite** (jawn- family, atomic-unit naming); consumer list includes auraken + solwend (intended readers) beyond the disk survey; identity(jawntology)/acclaim(jawncite) split. Schema design and sequencing deliberately deferred to a focused session — this doc is the brief for it.
