# jawncite — schema design (build-ready spec)

**Date:** 2026-07-15
**Status:** ratified schema spec — resolves all 6 open design questions from the jawncite doctrine, plus 2 questions the design itself surfaced (lists, package naming/home). Build jawnflicks against this.
**Lineage:** [2026-07-14-jawncite-acclaim-graph.md] (the doctrine + the 6 questions) ← [2026-07-14-jawnverse-stack-doctrine.md] (stack doctrine + wikifeedia corrections f-003/f-007/f-016/f-019/f-024/f-025/f-026/f-030/f-033).
**Provenance:** interactive design session 2026-07-14→15; every decision below ratified by mk individually. Designed against the three real consumer shapes (uncrancher: ratings-as-signal; jawnflicks: lists-of-lists; jawncloud: source trust-tiers) with auraken/solwend as pure cross-domain readers. Bead: Sylveste-qi6.

---

## Decision summary

| # | Question | Decision |
|---|----------|----------|
| 1 | `entity_ref` polymorphism | **(c) thin jawncite-owned registry** — `entities` table with uuid anchor; citations carry ONE `entity_id` NOT NULL FK. Domains/kinds are config **rows, not DDL**. The exactly-one-of-N CHECK is eliminated structurally. |
| 2 | Trust model | **Unified kind-typed `sources`, scoped per-domain**; shared 1–4 tier scale, per-domain rubric + weights in `domains.config`. Citations carry `voice_source_id` (nullable) + `venue_source_id` (NOT NULL). Scoring is a jawncite-owned function; **no confidence column on citations**. |
| 3 | `ingest_method`/provenance | **Store the immutable fact, derive the tier**: `ingest_method` NOT NULL + nullable `verified_at`/`verified_by`. Provenance weight = per-domain config at scoring time. No stored `provenance_tier` (drift-prone cache). |
| 4 | Read API shape | **Materialized `entity_acclaim` table**, refreshed by a jawncite-owned TS scoring job after ingest; `scoring_version`-stamped; rank derived by `ORDER BY`, never stored. Not a SQL view (per-query aggregation too costly for uncrancher inline filtering); not an HTTP service (unbudgeted hop, f-006). |
| 5 | wikifeedia migration | **Dual-write now + idempotent history backfill** (mk's call, overriding the session recommendation of backfill-only). Dual-write is **fail-open**; the idempotent backfill doubles as the reconciliation sweep. No pgSchema retrofit (already declined — raw-SQL harness trap, stack doctrine). |
| 6 | Shared db-client | **`jawnlink`** (jawn-family name; npm `@jawnverse/jawnlink`, verified unclaimed 2026-07-15). Scoped because private packages must be scoped. |
| 6b | Code home | **Standalone private repos each**: `mistakeknot/jawncite` + `mistakeknot/jawnlink`. Driven by mk's direction to **unbundle platform code from solwend** so solwend is purely heliogeometry/viberouting. |
| S1 | Lists (surfaced) | **First-class `lists` table**; `citations.list_id` nullable FK; `rank_in_list` stays on the citation (edge property). The doctrine's atomic unit names *list* — jawnflicks's whole read shape starts from it. |

**Unchanged from doctrine:** jawncite = `pgSchema("jawncite")` in the **shared solwend Neon project** (the Neon console label is not affected by the code unbundling); identity/acclaim split with jawntology stands; port the *shape* from wikifeedia, rebuild scoring per-domain.

---

## 1. Entity reference — the thin registry

### Why (c) won

- **(b) FK to `jawntology.works` is impossible for a real consumer**: jawncloud is Vercel+Prisma — a different database entirely; its `MeasurementSource` rows can never be FK targets. It also forces non-works (restaurants, dishes, measurement sources) into a Work→Edition→Offer identity layer and builds on jawntology's bare-`pgTable`-in-`public` foundation (f-016).
- **(a) loose `(domain, entity_id)` tuple breaks the pure readers**: auraken/solwend rendering a cross-domain ranked list would need joins into every vertical's schema (including a foreign Prisma DB). And every dedup merge becomes an UPDATE sweep over the fact table.
- **(c) keeps FK integrity inside jawncite's boundary**, makes cross-DB consumers possible, defers (never forces) the jawntology join, and converts the N-scaling problem from constraint-rewriting DDL into config rows.

### Tables

```
jawncite.domains
  domain        text PK                  -- 'food' | 'screen' | 'garment' | …
  display_name  text NOT NULL
  rubric        text                     -- what earns trust_tier 1 in THIS domain (human-readable)
  config        jsonb NOT NULL DEFAULT '{}'
                -- tier_weights: {1: w, 2: w, 3: w, 4: w}
                -- method_weights: {manual: w, curated_import: w, feed_poll: w, llm_extract: w, api_pull: w}
                -- verified_boost, type_weights, recency half-life, … (scoring reads this; §6)
  created_at    timestamptz NOT NULL DEFAULT now()

jawncite.domain_kinds
  (domain, kind)  composite PK           -- ('screen','film'), ('screen','show'), ('screen','episode'),
  domain → domains                       --  ('food','restaurant'), ('food','dish'), ('garment','source')
  description     text

jawncite.entities
  entity_id              uuid PK DEFAULT gen_random_uuid()
  domain                 text NOT NULL → domains
  kind                   text NOT NULL;  (domain, kind) → domain_kinds  [composite FK]
  natural_key            text NOT NULL;  UNIQUE(domain, natural_key)
  display_name           text NOT NULL              -- render cache: pure readers never leave jawncite
  parent_entity_id       uuid → entities (nullable) -- episode→show, dish→restaurant; roll-up queries
  merged_into_entity_id  uuid → entities (nullable) -- dedup redirect; reads follow the pointer
  retired_at             timestamptz (nullable)     -- deliberate removal; acclaim history is never deleted
  created_at             timestamptz NOT NULL DEFAULT now()
  -- indexes: UNIQUE(domain, natural_key); (domain, kind); parent_entity_id partial WHERE NOT NULL
```

### Rules

- **Thin-registry bright line:** if a column describes the entity itself (year, genre, rating, measurements), it does **not** belong in `jawncite.entities`. The registry holds exactly four kinds of thing: identity anchor, render cache, hierarchy, redirect. Everything else is the vertical's or jawntology's problem.
- **Natural-key schemes are per-domain conventions**, documented here and enforced by writers (via jawnlink helpers), not constraints. Initial schemes:
  - `screen`: `imdb:tt2926810` (primary; matches uncrancher's key), `tmdb:…` fallback
  - `food` (wikifeedia backfill/dual-write): `wikifeedia:restaurant:<uuid>`, `wikifeedia:dish:<uuid>`
  - `garment` (latent): `jawncloud:src_<id>`
  - jawntology-native things: `jawntology:work:<uuid>` — makes the doctrine's one-hop join real by convention
  - A wrong-format key creates a dupe, which the redirect heals — degraded, not broken.
- **Merges are redirects, not rewrites.** Two keys for one real-world thing → set `merged_into_entity_id` on the loser; the citations fact table is never touched; reads resolve the pointer (jawnlink helper + scoring job both follow it). Reversal = clear the pointer. Same reversibility principle as `jawntology.same_as.retired_at`.
- **Identity resolution to jawntology lives in jawntology.** When a jawncite entity is discovered to be a jawntology work: `jawntology.same_as` row with `externalSource='jawncite'`, `externalId=<entity_id>`. **No jawntology FK column, no confidence machinery in jawncite** (melange f-018 honored structurally).
- **No DB cascade from vertical tables — by design.** A vertical deleting its catalog row does not delete acclaim history (a delisted film's citations are still history). Deliberate removals use `retired_at`.

## 2. Sources & trust

```
jawncite.sources
  source_id        uuid PK DEFAULT gen_random_uuid()
  domain           text NOT NULL → domains        -- trust is a per-domain judgment
  kind             text NOT NULL                  -- 'person' | 'outlet' | 'aggregator' | 'jury' | 'community'
                                                  -- (documented vocabulary, not constrained — rosters are hand-curated)
  name             text NOT NULL
  name_normalized  text NOT NULL;  UNIQUE(domain, name_normalized)
  trust_tier       smallint NOT NULL DEFAULT 3 CHECK (trust_tier BETWEEN 1 AND 4)
  url              text
  feed_url         text                           -- RSS/API attribution (wikifeedia publications.domain analog)
  is_active        boolean NOT NULL DEFAULT true
  notes            text                           -- 'd. 2018', roster provenance, etc.
  created_at       timestamptz NOT NULL DEFAULT now()
```

- **One unified table, not a critics/publications port.** Kinds are vocabulary, not structure; aggregators (Metacritic, RT), festival juries, and institutional sources fit without DDL.
- **Sources are scoped per-domain — deliberately.** NYT-food and NYT-screen are two rows: rosters are curated per-domain (f-024/f-026 — food-critic tiers say nothing about film trade press), and cross-domain source identity has zero consumer demand. If it ever matters it's a `jawntology.same_as` link.
- **Tier scale is shared** (1=canon, 2=respected, 3=default, 4=unvetted/community) so the scoring function is domain-agnostic; the *judgment* (rubric + tier→weight mapping) is per-domain in `domains`.
- **Sources as rankable subjects (jawncloud's read shape)** needs no special case: register the source *as an entity* — `(domain='garment', kind='source', natural_key='jawncite:source:<source_id>')` — and cite it like anything else. Assertor-sources and subject-sources stay in their own tables, linked by key convention.

## 3. Lists

```
jawncite.lists
  list_id          uuid PK DEFAULT gen_random_uuid()
  domain           text NOT NULL → domains
  venue_source_id  uuid NOT NULL → sources
  voice_source_id  uuid → sources (nullable)      -- "Jonathan Gold's 99 Essential…" has a voice; "BFI 100" may not
  title            text NOT NULL                  -- edition-specific: "Sight & Sound 2022" ≠ "… 2012"
  url              text
  published_at     date
  list_kind        text NOT NULL DEFAULT 'ranked' -- 'ranked' | 'unranked'
  item_count       integer                        -- expected size per the source, when known
  source_run_id    uuid → ingest_runs (nullable)
  created_at       timestamptz NOT NULL DEFAULT now()
  -- UNIQUE NULLS NOT DISTINCT (venue_source_id, title, published_at)  → idempotent list re-ingest
```

When the same string pair repeats across fact rows there's an entity hiding in the fact table — wikifeedia could smear list titles across citations because its queries never *started from* the list; jawnflicks's queries do.

## 4. Citations — the fact table

```
jawncite.citations
  citation_id      uuid PK DEFAULT gen_random_uuid()
  entity_id        uuid NOT NULL → entities ON DELETE RESTRICT   -- the whole Q1 answer, one column
  list_id          uuid → lists ON DELETE CASCADE (nullable)     -- NULL = standalone review/award/rating
  voice_source_id  uuid → sources (nullable)
  venue_source_id  uuid NOT NULL → sources
  citation_type    text NOT NULL      -- 'review' | 'list_mention' | 'award' | 'best_of' | 'rating'
  title            text               -- review headline; list members inherit lists.title
  url              text
  excerpt          text
  rank_in_list     smallint           -- edge property; CHECK (rank_in_list IS NULL OR list_id IS NOT NULL)
  rating_value     numeric (nullable) -- uncrancher/aggregator shape: IMDb 5.4, metascore 78, RT 94
  rating_scale     text (nullable)    -- '0-10' | '0-100' | 'percent' — interpret rating_value
  vote_count       integer (nullable) -- volume signal behind an aggregate rating
  cited_at         date               -- when the assertion was made; list members default lists.published_at
  ingest_method    text NOT NULL      -- 'manual' | 'curated_import' | 'feed_poll' | 'llm_extract' | 'api_pull'
                                      -- IMMUTABLE — set at write, never updated
  verified_at      timestamptz (nullable)   -- human vouched for an auto-extracted row (state, not tier edit)
  verified_by      text (nullable)
  source_run_id    uuid → ingest_runs (nullable, REAL .references() — f-030 fixed from line 1)
  created_at       timestamptz NOT NULL DEFAULT now()
```

**Deliberately absent:** `confidence_score` (dead column, f-025 — we do not port a corpse into greenfield), stored `provenance_tier` (derived at scoring time from `ingest_method` + verification via domain config; two columns encoding one fact drift).

**Indexes:**
- `(entity_id)`; `(venue_source_id)`; `(voice_source_id)` partial WHERE NOT NULL; `(list_id)` partial WHERE NOT NULL; `(cited_at)`
- **Idempotency (dual-write + backfill coexistence, §8):**
  - `UNIQUE (list_id, entity_id)` partial `WHERE list_id IS NOT NULL` — one membership per entity per list edition
  - `UNIQUE NULLS NOT DISTINCT (entity_id, venue_source_id, citation_type, url)` partial `WHERE list_id IS NULL` — standalone citation dedupe (requires PG15+; Neon qualifies)
  - All writers upsert `ON CONFLICT DO NOTHING` — re-runs and dual-write/backfill overlap are structurally safe.

## 5. Ingest machinery

```
jawncite.ingest_runs        -- merges wikifeedia.autonomous_runs + uncrancher.ingest_runs (both proven)
  run_id            uuid PK DEFAULT gen_random_uuid()
  domain            text → domains (nullable — cross-domain maintenance runs)
  source            text NOT NULL            -- 'bfi_rss' | 'wikifeedia_dualwrite' | 'wikifeedia_backfill' | …
  source_ref        text                     -- file name / feed URL / batch descriptor
  source_hash       text                     -- sha256 idempotency anchor (uncrancher pattern); NULL for feed polls
  started_at        timestamptz NOT NULL DEFAULT now()
  finished_at       timestamptz
  status            text NOT NULL DEFAULT 'running'   -- 'running' | 'success' | 'partial' | 'failed'
  entities_added    integer DEFAULT 0
  citations_added   integer DEFAULT 0
  lists_added       integer DEFAULT 0
  proposals_created integer DEFAULT 0
  auto_writes       integer DEFAULT 0
  errors            jsonb
  notes             text
  -- UNIQUE (source, source_hash) partial WHERE source_hash IS NOT NULL  → same file+version = no-op re-run

jawncite.pending_proposals  -- ported near-verbatim (zero entity coupling), + domain
  proposal_id       uuid PK DEFAULT gen_random_uuid()
  domain            text NOT NULL → domains          -- per-domain review queues
  proposal_type     text NOT NULL                    -- 'new_entity' | 'new_citation' | 'new_list' | 'new_source'
  payload           jsonb NOT NULL
  source_run_id     uuid NOT NULL → ingest_runs      -- REAL FK (f-030)
  source_url        text NOT NULL
  confidence_score  numeric(3,2) NOT NULL            -- the LIVE per-proposal confidence (this one has writers)
  status            text NOT NULL DEFAULT 'pending'  -- 'pending' | 'approved' | 'rejected'
  reviewed_at       timestamptz
  reviewed_by       text                             -- 'mk' | 'auto_approved'
  rejection_reason  text
  created_at        timestamptz NOT NULL DEFAULT now()
  -- index (status, created_at); index (domain, status)
```

Note the asymmetry that killed wikifeedia's `citations.confidence_score` doesn't apply here: `pending_proposals.confidence_score` is written per-proposal by the extractor and consumed by the review flow — it's live machinery, ported as-is.

## 6. Read layer — `entity_acclaim` + scoring

```
jawncite.entity_acclaim     -- materialized by the scoring job; readers do boring SELECTs
  (domain, kind, entity_id) composite PK; entity_id → entities
  score             numeric NOT NULL
  score_components  jsonb              -- explainability: the weighted parts (per-tier sums, method mix, rating blend)
  citation_count    integer NOT NULL DEFAULT 0
  list_count        integer NOT NULL DEFAULT 0
  last_cited_at     date
  computed_at       timestamptz NOT NULL
  scoring_version   text NOT NULL      -- recalibrations are auditable
  -- index (domain, kind, score DESC)  → rank is ORDER BY, never stored (no full-domain rewrite per refresh)
```

- **Plain table, not a Postgres matview:** the formula reads per-domain *config* (`domains.config`), which is miserable in view DDL; application-side materialization lets us stamp `scoring_version`.
- **Refresh:** jawncite-owned TS scoring job, run per-domain after each ingest run (acclaim moves slowly; staleness is bounded by ingest cadence). The job resolves `merged_into_entity_id` redirects and excludes `retired_at` entities.
- **Scoring shape (v1 — config-driven, NOT frozen in schema):**
  `score(entity) = Σ_citations [ tier_weight(source.trust_tier) × method_weight(ingest_method, verified) × type_weight(citation_type) × rank_factor(rank_in_list) ] (+ rating blend for 'rating' citations)` — every weight from `domains.config` with global defaults. Recalibration = config UPDATE + job re-run under a new `scoring_version`; **never** a fact-table backfill.
- **Consumer costs:** uncrancher inline lure filtering = one indexed join (or it denormalizes further, matching its existing `imdb_rating` pattern). auraken/solwend render ranked lists entirely from jawncite (`display_name` cache — no vertical-schema joins). jawncloud (out-of-DB, latent) reads via a read-only Neon role or a thin endpoint *when it becomes real* — deferred.

## 7. Consumer contracts

| Consumer | Writes | Reads |
|----------|--------|-------|
| **jawnflicks** (#1, forcing function) | `domains='screen'` + kinds film/show/episode; sources roster (trade press, Metacritic, RT, festival juries); lists + citations via jawnlink helpers; proposals for LLM-extracted rows below threshold | `entity_acclaim` (rankings), `lists` (browse lists-of-lists), citations-per-entity (provenance display) |
| **uncrancher** (#2, proof-of-generalization) | optional: `citation_type='rating'` rows from IMDb data (venue=IMDb `kind='aggregator'`) | `entity_acclaim` joined via `natural_key='imdb:<tt>'` for lure filtering |
| **wikifeedia** (#0, legacy) | dual-write (§8) into `domain='food'` | none required (its own tables remain its read path) |
| **jawncloud** (latent) | source-cites in `domain='garment'`; sources-as-entities convention | "best source" = `entity_acclaim` over `kind='source'` |
| **auraken / solwend** (pure readers) | — | `entity_acclaim` across domains; self-contained rendering via `display_name` |

## 8. wikifeedia: dual-write + backfill (Q5, as ratified)

mk chose **dual-write now** over the session's backfill-only recommendation. The build must honor these constraints:

1. **Fail-open, non-negotiable.** The jawncite write is wrapped so any failure (constraint, connectivity, schema drift) logs to the run's `errors` jsonb and **never aborts or delays wikifeedia's primary write**. The restaurant app's ingest must be exactly as reliable the day after as the day before.
2. **Dual-write covers new writes only** — the existing corpus needs the **one-time history backfill** regardless: restaurants → `entities(food/restaurant, natural_key='wikifeedia:restaurant:<uuid>')`, dishes → `entities(food/dish, parent→restaurant)`, citations mapped with `ingest_method='curated_import'` (or the method recorded on the original row via `auto_added`), critics/publications → `sources(domain='food')` with their existing trust tiers.
3. **The backfill IS the reconciliation sweep.** Because every write path upserts against the §4 uniqueness keys (`ON CONFLICT DO NOTHING`) and the backfill is idempotent via `ingest_runs.source_hash`, re-running it heals any dual-write misses. No separate drift-detection machinery.
4. **Rollback** = `DELETE FROM jawncite.citations/entities/sources … WHERE domain='food'` + remove the dual-write hook. wikifeedia itself is untouched by rollback.
5. **No pgSchema retrofit on wikifeedia** — already declined with reasoning recorded (raw-SQL idempotency harness references unqualified tables; risk lands on prod, reward on greenfield).

## 9. Repos, packages, unbundling (Q6/6b)

**Direction (mk, this session): unbundle platform code from solwend** — solwend is purely the heliogeometry/viberouting product. Consequences:

- **`mistakeknot/jawncite`** (new, private): the drizzle schema (`pgSchema("jawncite")`), migrations (`__drizzle_migrations__jawncite`), the scoring job, seed/config tooling, this spec's conventions. Publishes **`@jawnverse/jawncite`** (schema + types) for consumers.
- **`mistakeknot/jawnlink`** (new, private): the shared db-client — `pg`-direct vs `neon-http` dual-client idiom with the **corrected** driver comment (f-003/f-033), `getOrCreateEntity()` (upsert by `(domain, natural_key)`, redirect-aware), `citeInTx()` (entity upsert + citation insert, one transaction), read helpers for `entity_acclaim`. Publishes **`@jawnverse/jawnlink`**. Name verified unclaimed on npm (bare + scoped) 2026-07-15; scoped because private packages must be scoped.
- **Accepted cost of standalone-each:** a change touching schema + client helpers = 2 PRs / 2 releases with a version-skew window. Mitigate with conservative semver and jawncite pinning jawnlink minor versions.
- **The Neon project does not move.** "solwend" is a console label on shared DB infrastructure; `pgSchema` namespaces are the isolation. Env var: **`JAWNCITE_DATABASE_URL`** → the shared Neon project (own var, same project — the jawntology env-var precedent, correctly cited this time).
- **jawnflicks home:** the port spec's "monorepo-sibling under solwend/platform" lean is superseded by the unbundling — jawnflicks goes **standalone private repo** too (consistent with uncrancher). Confirm at build.
- **Follow-on direction (recorded, NOT this session's scope):** jawntology and wikifeedia code eventually migrate out of `solwend/platform/` to complete the unbundling.

## 10. Build discipline (inherited corrections, restated for the implementer)

- `pgSchema("jawncite")` on every table; **never bare `pgTable()`** (f-016).
- `extraConfig` callbacks return an **array** `(t) => [...]`, not an object (drizzle deprecation; TS6387).
- **No PostGIS** anywhere in jawncite (f-014).
- Real `.references()` on every FK named above — no convention-only links (f-030).
- `UNIQUE NULLS NOT DISTINCT` requires PG15+ — assert at migration time.
- Seed order: `domains` → `domain_kinds` → `sources` (rosters) before any citation ingest; `ingest_method` values documented in §4 are the complete v1 vocabulary.

## 11. Deliberately excluded (so nobody "helpfully" adds them)

- `citations.confidence_score` — the dead column stays dead (f-025).
- Stored `provenance_tier` / stored rank — both derivable; storing them creates drift/rewrite obligations.
- jawntology FK columns or resolution-confidence machinery in jawncite — identity is jawntology's layer (`same_as` with `externalSource='jawncite'`), f-018.
- Domain attributes on `entities` (year/genre/etc.) — thin-registry bright line, §1.
- HTTP read service — revisit only when out-of-project readers outnumber in-project ones.
- Cross-schema FKs into vertical tables — migration coupling for a cascade we don't want anyway.

## 12. Manual checklist (auth-gated, for mk)

1. Create/verify the **`jawnverse` npm org** (the CLI check hit an auth gate: `npm org ls jawnverse` → E401; log in first) — needed before `@jawnverse/jawnlink` / `@jawnverse/jawncite` can publish. https://www.npmjs.com/org/create
2. Create private repos **`mistakeknot/jawncite`** and **`mistakeknot/jawnlink`** (or approve their creation via `gh repo create --private`).

## 13. Sequencing

Doctrine path **(C) then (A)**, now concrete: this spec is (C) complete. Next: scaffold `mistakeknot/jawnlink` + `mistakeknot/jawncite` (schema + migrations + seed for `screen` and `food` domains), then **build jawnflicks against jawncite** as writer #1 — its ingest exercises lists/citations/proposals end-to-end; the wikifeedia dual-write + backfill lands once jawncite's schema has survived jawnflicks's first real ingest.
