# The Acclaim Graph — a universal "list of lists" substrate for GSV

**Date:** 2026-07-14
**Status:** VISION / architecture doctrine — *not a build spec.* The user chose "map the vision first, don't build."
**Provenance:** Extends the jawnverse stack doctrine ([2026-07-14-jawnverse-stack-doctrine.md](2026-07-14-jawnverse-stack-doctrine.md)), which was itself a flux-melange deep-review. This doc answers the question the doctrine's film-aggregator call *provoked*: "could we build something much bigger — not just movies/shows/restaurants but *everything* — that lots of GSV projects leverage?"

> **One-sentence thesis.** The thing worth building is not a film aggregator, and not a restaurant aggregator — it is the **domain-agnostic acclaim layer both of them (and fashion, fragrance, procgen, and a cross-domain recommender) are special cases of**: a provenance-weighted graph of *who asserted what about which entity, on which ranked list, with how much trust*. wikifeedia already proved the shape is domain-neutral; the move is to promote that shape from one vertical's internal tables to a shared substrate.

---

## 1. The core distinction this whole design rests on

There are **two different graphs** here, and the entire architecture depends on not fusing them. The flux-melange loop already flagged this seam without naming it (finding f-018: `same_as` and `citations` both carry a "confidence" field but *solve different problems* — "don't conflate them"):

| Graph | Question it answers | Owns | Today lives in |
|-------|--------------------|------|----------------|
| **Identity / Ontology** | "What *is* this entity? Is this the same thing as that?" | canonical IDs, `works`/`editions`/`offers`, `same_as` edges, entity resolution | **jawntology** (Postgres commerce graph; Neo4j where genuinely graph-shaped, cf. jawnomicon) |
| **Acclaim / Assertion** | "Who *said* this entity is good, and how much do we trust them?" | `sources`, `lists`, `citations`, `trust_tier`, `rank_in_list`, provenance | **wikifeedia** (food-coupled today; the shape is generic) |

**Why they must stay separate:**
- *Identity* is about **deduplication and canonicalization** — one film, many editions; one restaurant, many listings. Confidence here = "am I sure these two records are the same thing."
- *Acclaim* is about **claim attachment and weighting** — many critics, many lists, one film. Confidence here = "how much do I trust this assertion."
- Fusing them means a `confidence` column that means two incompatible things depending on row — the exact conflation f-018 warned against.

**The answer to "wikifeedia? jawntology? a mix?" is therefore: neither — a THIRD schema.** jawntology stays the identity layer. wikifeedia becomes the acclaim layer's *first consumer* (or its ancestor). The new shared substrate is `pgSchema("acclaim")`.

---

## 2. The substrate: `pgSchema("acclaim")` in the shared solwend Neon project

Building on the user's isolation decision in the stack doctrine (**`pgSchema` in the shared project, not a separate project** — keeps everything joinable, one Neon bill, cheapest correct point, proven by uncrancher):

```
                ┌──────────────────────────────────────────────┐
   IDENTITY     │  pgSchema("jawntology")                       │
                │  works · editions · offers · sellers · same_as│
                └───────────────────┬──────────────────────────┘
                                    │ canonical entity_id
                                    ▼   (JOIN, same Neon project)
                ┌──────────────────────────────────────────────┐
   ACCLAIM      │  pgSchema("acclaim")   ◀── the "list of lists" │
   (NEW)        │  sources · publications · lists · citations    │
                │  trust_tiers · rank_in_list · provenance_tier  │
                │  entity_ref  (polymorphic → ANY domain)        │
                └───────────────────┬──────────────────────────┘
                       ▲ write       │ read
          ┌────────────┼─────────────┼──────────────┬───────────┐
          │            │             │              │           │
     ┌────┴───┐  ┌─────┴────┐  ┌─────┴─────┐  ┌─────┴────┐  ┌───┴────┐
     │wikifeed│  │jawnflicks│  │fashion... │  │ jawncloud│  │auraken │
     │ (food) │  │  (film)  │  │ (garments)│  │(wardrobe)│  │(reader)│
     └────────┘  └──────────┘  └───────────┘  └──────────┘  └────────┘
        writes       writes        writes         writes      reads all
```

**The polymorphic `entity_ref` is the crux.** wikifeedia's `citations` table has two nullable target FK columns (`restaurant_id`, `restaurant_dish_id`) + a CHECK enforcing exactly-one. The melange loop already flagged (f-007) that this doesn't generalize — film needs 3 targets, fashion needs its own. So the substrate cannot use per-domain FK columns. Two candidate designs (decide at build time — see §6 open questions):

- **(A) Typed polymorphic ref:** `entity_type text` + `entity_id uuid` (no FK; type discriminates the target domain). Universal, but loses referential integrity (the f-030 soft-link problem, ecosystem-wide).
- **(B) Canonical-ID indirection via jawntology:** every citable entity across every vertical first gets a canonical `work`-like ID in jawntology's identity graph; `acclaim.citations.entity_ref` is a real FK to *that*. Referential integrity preserved; cost is every vertical must register its entities in the identity layer first. This is the more principled design and leans into the identity-vs-acclaim split — but it couples the acclaim graph's adoption to jawntology coverage.

---

## 3. Per-vertical consumer map

*(This section is anchored by a live survey of the four named projects — filled in below once the survey agent reports. Placeholders marked ⟨SURVEY⟩ until then.)*

| Vertical | Domain entity | Consumption shape | Notes |
|----------|--------------|-------------------|-------|
| **wikifeedia** | restaurants, dishes | WRITE (it *is* the origin) + READ | Becomes acclaim's ancestor/first consumer; migration path in §5 |
| **jawnflicks** (planned) | films, shows, episodes | WRITE (ingest best-of lists) + READ (ranked corpus) | The forcing function; doctrine already specced it |
| **fashionsomething** | ⟨SURVEY⟩ garments? | ⟨SURVEY⟩ | Rust project — cross-language consumer (reads via API/SQL, doesn't share the TS client) |
| **jawncloud** | wardrobe/style/SKU | ⟨SURVEY⟩ | TS/Prisma/Neon — could read acclaim to rank/recommend |
| **auraken** | cross-domain (movie/food/etc) | READ (the universal reader) | ⟨SURVEY⟩ — if it's a recommender, it's the ultimate downstream: recommends over acclaim signal across ALL verticals at once |
| **uncrancher** | procgen | READ? (acclaim as generation input) | ⟨SURVEY⟩ — "acclaim as procgen seed" is the most speculative consumer; flag as a stretch unless survey says otherwise |

**auraken is the payoff that makes the substrate worth it.** A per-vertical aggregator is just "wikifeedia again, for films." The *shared* substrate only earns its abstraction cost if something reads *across* domains — and a cross-domain recommender ("you love Tarkovsky and natural-wine bars, here's a coat and a fragrance") is exactly that. **The substrate's value is proportional to how real auraken is.** (Survey confirms.)

---

## 4. Why a shared substrate, and the honest risk

**The pull toward it (real leverage):**
- wikifeedia already proved the citation shape is domain-neutral (melange: only the 2 target FKs + seed rosters are food-specific).
- Every vertical otherwise re-implements the same critic/publication/trust-tier/rank machinery — the copy-paste the doctrine already flagged (f-003 on the db-client alone).
- A cross-domain reader (auraken) is *impossible* without a shared schema — you can't `JOIN` five per-vertical citation tables that don't share a shape.

**The push against it (premature universalization — the failure mode to respect):**
- **Rule of three.** You have arguably *one* real consumer (wikifeedia, food) and one *planned* (jawnflicks, film). Fashion/jawncloud/auraken consumption is inferred, not proven. Extracting a generic substrate before the 2nd consumer is *built* is the classic way to get an abstraction that fits neither.
- The polymorphic `entity_ref` (§2) is genuinely hard to get right, and getting it wrong is a migration on every vertical's citation data.
- The trust-tier calibration is **per-domain and non-portable** (melange f-024/f-025: wikifeedia's tiers are hardcoded *food critics*; film needs its own roster; fashion needs another). The substrate can share the *schema* for trust tiers but **not the values or the scoring** — so "shared acclaim graph" is shared *structure*, per-domain *content*. Be honest that the reuse is narrower than it feels.

**Resolution (why "map first, build jawnflicks, generalize on the 2nd real consumer" is the sequencing):**
Design jawnflicks's schema *domain-neutrally from line 1* (`entity_ref` not `film_id`, `sources` not `critics`, `provenance_tier` present) so that extraction to `pgSchema("acclaim")` is a **lift-and-shift, not a rewrite**, the moment fashion or auraken becomes a real second consumer. You get the substrate's future without paying the premature-abstraction tax now. This doc *is* the map that makes that extraction cheap when the time comes.

---

## 5. wikifeedia migration path (when the substrate is real)

wikifeedia is the ancestor; it should not be stranded. Two options, lowest-risk first:

- **(Coexist)** Leave wikifeedia's tables as-is in `public`. The new `acclaim` schema is a fresh design; wikifeedia keeps running unchanged as the food vertical, and is *retrofitted to read/write acclaim* only if/when there's a reason. **Recommended** — the melange loop already proved wrapping live wikifeedia in a schema breaks its raw-SQL idempotency harness (the pgSchema-retrofit trap, documented in the stack doctrine). Don't repeat that.
- **(Absorb)** Migrate wikifeedia's citation data into `acclaim` with `entity_type='restaurant'`. Cleaner long-term, but it's a live-prod data migration on the running restaurant aggregator — defer until the substrate is proven by ≥2 greenfield consumers.

---

## 6. Open questions for the build session (do NOT decide here)

1. **entity_ref design:** typed-polymorphic (A) vs canonical-ID-via-jawntology (B)? (B) is more principled but couples adoption to identity-graph coverage. **This is the single biggest design decision.**
2. **Is auraken real enough to justify the substrate now,** or does the substrate wait until auraken is actually being built? (Survey informs; user decides.)
3. **Cross-language access:** fashionsomething is Rust. Does it read `acclaim` via raw SQL against Neon, via a thin HTTP API (the spatial→jawntology pattern), or not at all? The shared `@jawnverse/db-client` (TS) doesn't serve Rust.
4. **Trust-tier governance:** per-domain rosters are non-portable. Who curates the film/fashion/fragrance trust tiers, and is that a manual seed (wikifeedia's approach) or does it need its own tooling?
5. **Does uncrancher (procgen) genuinely consume acclaim,** or is "acclaim as generation input" a forced fit? (Survey; lean skeptical.)

---

## 7. Bottom line

The user's instinct is correct: the valuable object is **the universal acclaim layer, not any single vertical**. The clean architecture is a **three-way split** — `jawntology` (identity) + a new `pgSchema("acclaim")` (assertion/acclaim) + per-vertical writers, with a cross-domain reader (auraken) as the payoff that justifies the abstraction. The right *sequencing*, given only one built consumer today, is: **write this map (done), build jawnflicks domain-neutrally so extraction is a lift-and-shift, and promote to the shared `acclaim` schema on the second real consumer** — not before. That respects the rule of three while keeping the "everything" future one cheap migration away.

The single highest-leverage design decision deferred to the build session is the **polymorphic `entity_ref`** (typed vs. canonical-ID-via-jawntology) — get that right and every vertical plugs in; get it wrong and it's a migration on all of them.
