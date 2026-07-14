# Jawnverse Stack Doctrine — Melange Synthesis

**Date:** 2026-07-14
**Loop:** flux-melange, 3 rounds, halt=DRY (yield 12→6→0), 33 findings, 25 upheld / 1 refuted, 15 slots.
**Goal:** best per-tier architecture/stack doctrine for jawnverse + gsvdotcom + solwend + wikifeedia — plus the concrete stack call for the film best-of aggregator.
**Weights:** taste. **Synthesis:** hand-written from the intact ledger (the workflow's synthesis agent hit a session limit; discovery completed clean).

> **Read this first.** The loop's job was to pressure-test my corpus brief, and its highest-heat findings **falsified three load-bearing claims in that brief**. The doctrine below is corrected against them. Where a section supersedes the brief, it says so.

---

## The eye of distance — what the loop actually found

The seed round confirmed the ecosystem is stack-split by tier (Python/uv for ingest+compute; TS/Drizzle/Neon for schema+web; Astro/Cloudflare for content; Swift/Neo4j as justified one-offs). That part held. **But the adaptive rounds spent their heat demolishing the brief's recommendations for the film aggregator, not the tier map.** Three corrections dominate the report; everything else is scaffolding around them.

### 🔴 CORRECTION 1 — The "proven split precedent" was false (f-027, f-032 · N2×R9, the joint-highest-risk cluster)

My brief claimed jawntology "already executed a separate-Neon-**project** carve-out the film aggregator should mirror." **This is wrong.** jawntology's own README states it is *"Colocated with Solwend's Neon `solwend` project."* jawntology has its own env var (`SOLWEND_JAWNTOLOGY_DATABASE_URL`) but that var **points into the same shared project**, and its tables use bare `pgTable()` → they land unqualified in `public` right next to wikifeedia's, colliding by name whenever the documented env-var fallback is exercised (f-032, converges f-016).

**Consequence:** "mirror jawntology → get your own project" was advice built on a misread. jawntology proves *env-var-per-package*, not *project-per-package*. The isolation guarantee people think they have (separate project) is **not** what's deployed.

### 🔴 CORRECTION 2 — There IS a proven middle isolation tier, and the brief erased it (f-023 · N3×R6, top-novelty upheld)

My brief asserted "there is NO schema-level namespacing isolating wikifeedia from restaurants from uncrancher." **False for uncrancher** — it declares `pgSchema("uncrancher")` and tracks migrations in a separate `__drizzle_migrations__uncrancher` table. That is a **working, proven middle option** between shared-`public` and separate-project: *same Neon project + a dedicated Postgres schema.* Cheaper than a new project, and it actually prevents the `public` name-collision that f-016 verified is otherwise universal (**zero** `pgSchema()` calls anywhere else in `platform/*/src` — every table, including jawntology's generically-named `places`, lands in bare `public`).

This is the single most useful thing the loop produced: **the isolation decision is a 3-point spectrum, not a binary**, and the cheapest correct point was invisible in my framing.

### 🔴 CORRECTION 3 — The "crown jewel" is a schema shape, not an engine (f-025 · N3×R6 · plus f-009/f-024/f-026)

My brief sold `confidence_score` + `trust_tier` as reusable *aggregation engine*. The loop grepped all four import phases: **`confidence_score` has no writer anywhere.** It's a nullable column with an unimplemented auto-write-threshold concept — there is no scoring *algorithm* to port. And `trust_tier` values come entirely from **two hardcoded seed arrays of named LA/NYC food critics + food publications**, with a rubric written in terms of specific restaurant critics (f-024). Film/TV has a structurally different trust landscape (trade press, Metacritic, RT Certified-Fresh aggregators) with **zero roster equivalent** (f-026).

**Consequence:** what ports is the **table *shape*** (polymorphic citation, rank_in_list, provenance columns, pending_proposals/autonomous_runs), not calibration *logic*. Re-scope "port the engine" to "port the schema; build the scoring." The ~60-70% figure was for *schema surface*; the *working calibration* that ports is closer to **0%** because it was never built.

---

## The doctrine (corrected, per tier)

A new jawnverse app author should be able to follow this without asking.

### 1. Data isolation — the rule the brief owed and never gave (supersedes brief §6.1)

Choose the **cheapest isolation point that satisfies the app's cross-query need**, not "new project by reflex":

| Need | Isolation point | Precedent | Cost |
|------|----------------|-----------|------|
| App must be live-queryable *with* solwend data (joins, shared geo) | **Shared project, `pgSchema("appname")`** | uncrancher (proven, f-023) | lowest — one line |
| App is its own product, no cross-DB joins, but you want one Neon bill/console | Shared project, `pgSchema` + own env var | (synthesized from uncrancher + jawntology-env-var) | low |
| App is a separable product with independent lifecycle/backups/blast-radius | **Separate Neon project** | *(no current precedent — jawntology is NOT one, f-027)* | highest — new project, no joins |

**For the film aggregator specifically:** it has **no reason to join solwend's geo/restaurant data**. Both the shared-schema and separate-project options are valid. Default to **separate Neon project** *only because* it's a genuinely separable consumer product with its own backup/lifecycle needs — but do so knowingly, not by misciting jawntology. If you ever want it queryable alongside jawntology's graph, use `pgSchema` in the shared project instead. **Never bare `pgTable()` in a shared project** — that's the f-016 collision trap.

**Codify, don't copy:** the `pg`-direct-vs-`neon-serverless`-pooled dual-client idiom is copy-pasted per repo with no shared package (f-003), and the PgBouncer/prepared-statement fix is one careless "simplification" from silently regressing in each new repo. Extract a tiny `@solwend/db-client` (or `@jawnverse/db-client`) package. Bonus: it fixes the **mislabeled db.ts comment** (f-033 — the header claims WebSocket/PgBouncer but the code imports `neon-http` and calls the stateless `neon()` client; that lie propagates into every copy-paste).

### 2. Backend/service tier — kill the false analogy (supersedes brief §5 headline)

The brief's "Python-ingest+TS-serve, exactly like spatial→jawntology" is a **workload mismatch** (f-004, f-012 · N1×R9). spatial is **CPU-bound geometric compute** (OSMnx/A*/rasters) feeding a *materialized index* via files/SQLite. wikifeedia's ingest is **I/O-bound Airtable polling** — a structured pull with no comparable compute load, and **no live HTTP citation-write seam exists anywhere in the tree** (f-012). Don't cargo-cult a compute-joint pattern onto an I/O-poll workload.

**Rule:** split ingest into a separate service *only when the ingest is CPU-bound or needs a different runtime/scaling profile than the serve path* (spatial qualifies; Airtable/RSS polling does not). For the film aggregator's actual workload — periodic list-scraping + LLM extraction — **a single TS service with a scheduled ingest job is the right default**; reach for a Python sidecar only if the LLM-extraction step grows into heavy local compute (embeddings, OCR, video). If you do split, the doctrine must specify whether ingest writes **direct-to-Neon** (schema hazard — needs the `pgSchema` discipline above) or **through the TS API** (an unbudgeted extra hop with latency/retry cost the brief never estimated, f-006).

### 3. Frontend / consumer apps — the one place the brief was right

Two canonical stacks, split by content-shape (the loop found no fault here):
- **App with dynamic data + auth** → Next.js `output: export` (static) on **Cloudflare Workers**, calling the platform over HTTP. Auth via Clerk or "Sign in with Solwend" OIDC. (solwend-web, jawntology-web, stepsdaddy.)
- **Content/editorial site** → **Astro on Cloudflare**, file-based content collections in git, no DB. (gsvdotcom canonical, jawnomicon/site.)
- **jawncloud's Vercel+Prisma is the outlier** — treat as legacy, not template. New apps: Drizzle + Cloudflare.
- Native (Swift/SPM) only when on-device capture/hardware demands it (jawnscope-ios). Neo4j only for genuinely graph-shaped ontology domains where a YAML-canon + rebuildable-graph split earns its keep (jawnomicon).

### 4. Deploy — the doctrine summary is lossy (f-005, f-015)

The real deploy topology is **four lanes, not three**: Cloudflare (static frontends) + Fly.io (Python compute APIs) + Neon (DB) + **zklw/systemd/cloudflared (MCP servers)** — the brief's "Cloudflare+Fly+Neon triad" silently drops the MCP lane and the Vercel outlier a reader would still hit. State all four, with the independent-movement rule: a split ingest/serve app in one repo still deploys its lanes independently (ingest→Fly or a Worker cron; serve→Cloudflare).

### 5. Ingest source is a *product* decision, not a technical detail (f-010, f-019 · the only taste-positive findings)

The brief framed Airtable-vs-RSS-vs-LLM as "a choice still open." The loop flagged this as the one genuine **asymmetry** (taste_kind=asymmetry): these sources have **materially different trust profiles** feeding the *same* numeric `confidence_score` field, and the schema has **no `ingest_method` column** to distinguish them (f-019). Airtable = human-curated, high implicit trust; RSS+LLM-extraction = model-dependent, lower trust. Porting the schema verbatim **silently conflates two provenance qualities under one number.**

**Doctrine:** if the film aggregator will mix curated and auto-extracted sources, **add an `ingest_method` / `provenance_tier` column before first ingest** — retrofitting it after citations accumulate is a migration + backfill. This is the highest-leverage schema *addition* the loop surfaced.

---

## The concrete call for the film best-of aggregator

Synthesizing all of the above:

- **Stack:** **TS / Drizzle / Neon**, matching the schema-owning platform camp. *Not* Python/uv — the workload is I/O-bound polling + LLM extraction, which sits fine in a scheduled TS job; the jawnbase resolution-chain reuse the brief imagined is a **technique conflation** (f-031: jawnbase is a code-side ranked-fallback over dataclasses; wikifeedia's trust_tier is a flat SQL column — they don't already agree, and picking Python buys you neither). Python only earns its place if LLM extraction later becomes heavy local compute.
- **What to port:** the citation table **shape** (`citations.ts`, `pipelines.ts`), `db.ts` (via the new shared client package, not copy-paste), the byline/domain **resolution machinery** in `critics.ts`. **Do not expect** working `confidence_score` calibration or reusable `trust_tier` seed data — both are film-domain rebuilds from scratch (f-025, f-024).
- **Schema changes before first ingest:** (a) polymorphic target CHECK is a **redesign to exactly-one-of-N**, not a 1-for-1 FK swap, because film/TV/episode is 3 targets not 2 (f-007); (b) add `ingest_method`/`provenance_tier` (f-019); (c) add real `.references()` FKs from `sourceRunId` → `autonomousRuns.runId` — currently convention-only, and that soft-link inherits into the port (f-030); (d) drop PostGIS from the new project entirely (f-014 — porting db.ts verbatim drags in PostGIS extension setup films never use).
- **Isolation:** own **separate Neon project** (it's a separable product), knowingly — not by misc. If you'd rather keep it joinable to jawntology later, use `pgSchema("jawnflicks")` in the shared project instead.
- **Repo shape:** the brief named none (f-013). The tree shows three patterns — monorepo sibling / extracted standalone repo / worktree-per-experiment. For a new separable product with its own DB and deploy: **standalone private repo** (`mistakeknot/jawnflicks` or similar), mirroring how uncrancher was extracted. Monorepo-sibling only if it needs to import `sdk/*` directly; worktree only for throwaway UI experiments.
- **Ingest source:** decide Airtable-vs-RSS+LLM as a **curation-breadth vs trust-quality product tradeoff** up front (f-010), and let that decision drive whether `provenance_tier` is even needed.

---

## Convergence (high-confidence commodity, per the melange demotion)

These are *trustworthy but unexciting* — multiple lenses agreed, so they're solid but not spice:
- Zero `pgSchema()` usage → universal `public` collision risk (f-016 ← f-001, f-002).
- solwend docs never mention jawntology despite its live deploy (f-020, f-028) — **make doc-currency a mechanically-checkable clause**, or the doctrine's own "follow without asking" prize rots the same way (f-020).
- `same_as` (entity-resolution) and `citations` (claim-attachment) both have "confidence" fields but solve different problems — don't conflate (f-018).

## Refuted / retired
- **f-008 (refuted):** the `reviewer_ratings` repoint being non-independent of `dishes.ts` didn't survive verification — the repoint is clean.
- **f-011 vs f-017 disagreement resolved:** `SOLWEND_WIKIFEEDIA_DATABASE_URL` is NOT a runtime fallback seam — wikifeedia's `db.ts` **hard-throws** on missing env var; the only fallback is jawntology's *build-time* `drizzle.config.ts` (f-021). So "de-facto shared URL" overstated a reusable seam.

---

## Bottom line

The tier map was right; **my recommendations for executing the film aggregator were wrong in three specific, correctable ways.** Net doctrine: **TS/Drizzle/Neon, own separate project (knowingly), port the schema *shape* not a mythical engine, add provenance/ingest-method columns before first write, extract the dual-client into a shared package, and stop citing jawntology as a separate-project precedent it never was.** The single highest-value discovery is that **isolation is a 3-point spectrum with a proven cheap middle (`pgSchema`) that the reflex-to-new-project throws away.**

---

## DECISIONS + LIVE-VERIFICATION (2026-07-14, post-doctrine session)

The doctrine above is a *snapshot* synthesis. When it came time to act, two user decisions and a live re-read of wikifeedia's current source refined it. **These override the doctrine's defaults where they conflict** — recorded here so the build session doesn't re-litigate.

### User decisions
1. **Isolation for the film aggregator → `pgSchema("jawnflicks")` in the SHARED `solwend` Neon project** — *not* a separate project. Rationale the user chose: keeps films joinable to jawntology's work/edition/offer graph later (a film IS a work with editions/offers — that join is real, not hypothetical), one Neon bill/console, cheapest correct point (proven by uncrancher). This reverses the doctrine's "separate project (knowingly)" default — the doctrine explicitly offered `pgSchema` as the alternative "if you'd rather keep it joinable to jawntology later," and the user took it.
2. **Fix wikifeedia at source before porting** — don't inherit the bugs the loop found.

### Live re-read of wikifeedia (2026-07-14) — what actually got verified against current `platform/wikifeedia/src`
- **f-033 (db.ts comment) — CONFIRMED + FIXED upstream.** The header claimed `getServerlessDb()` uses the "WebSocket driver" with "PgBouncer connection reuse." Reality: it imports `drizzle-orm/neon-http` and calls `neon()` — the *stateless HTTP* driver, no client-side pooling. **Fixed:** corrected the comment in place (comment-only, no schema change).
- **f-025 (dead confidence_score) — CONFIRMED + DOCUMENTED upstream.** `citations.confidence_score` is a nullable `numeric` with **no writer anywhere**. The LIVE confidence field is `pending_proposals.confidence_score` (`.notNull()`, written per-proposal). **Fixed:** added an UNIMPLEMENTED banner comment on the column so a port author can't cargo-cult it as working calibration. (Not dropped — dropping is a live-prod migration for zero functional gain.)
- **f-030 (soft-link sourceRunId) — CONFIRMED + DOCUMENTED upstream.** `citations.source_run_id` has no `.references()`. **Fixed:** added a comment flagging it as convention-only; the real FK is a port-time addition.
- **f-016 (bare pgTable → public) — CONFIRMED, but NOT retrofitted upstream (deliberate).** Every wikifeedia table is bare `pgTable()` in `public`.
- **f-007 (2-target polymorphic CHECK) — CONFIRMED.** `citations_exactly_one_target` enforces `restaurantId` XOR `restaurantDishId` (2 targets). Film/TV needs 3 (film/show/episode) → genuine redesign.
- **BONUS finding (not in the loop):** wikifeedia's `extraConfig` callbacks return an **object** `(t) => ({...})`, which drizzle-orm has **deprecated** in favor of returning an **array** `(t) => [...]`. Surfaced by `pnpm typecheck` (TS6387 ×3). The port must use the array form.

### The `pgSchema` retrofit trap (why "full upstream cleanup" was scoped DOWN)
The user chose "full upstream cleanup," but the live re-read found a hard blocker the doctrine's snapshot didn't know about: **wikifeedia has hand-written raw SQL** (`scripts/import/__tests__/idempotency.sql`, `worldwide_idempotency.sql`) that references the tables **unqualified** — `FROM citations`, `JOIN publications p`. Wrapping the live tables in `pgSchema("wikifeedia")` moves them out of `public` and **breaks exactly the idempotency test harness you'd use to verify a migration didn't corrupt data.** So `pgSchema` is "one line" for *greenfield* (nothing references the tables yet) but a search_path-breaking prod migration for a *live* app. **Decision: do NOT retrofit `pgSchema` or the live FK onto wikifeedia.** Their only beneficiary is the port, which gets both properties for free as new code. Risk would land on the running restaurant aggregator; reward lands on greenfield. Wrong trade — declined with the reasoning recorded.

### PORT SPEC — jawnflicks (build this in a dedicated session, do not auto-start)
Fresh schema in the SHARED `solwend` Neon project. Every correction below is "one line / free" precisely because there's no data to migrate:
- **Isolation:** `export const jawnflicks = pgSchema("jawnflicks")`; all tables via `jawnflicks.table(...)`. Migrations track in `__drizzle_migrations__jawnflicks`. Reuse `SOLWEND_WIKIFEEDIA_DATABASE_URL`'s *project* (own env var pointing at the same Neon project is fine; the schema namespace is the isolation, not the URL).
- **Port the SHAPE of:** `citations.ts` (critics/publications/citations), `pipelines.ts` (pending_proposals/autonomous_runs — verbatim, zero entity coupling), the byline/domain resolution machinery in `critics.ts`. **Do NOT port** `geography.ts`, PostGIS, or restaurant/dish tables. Drop PostGIS from the new schema entirely (f-014).
- **Corrections baked in from line 1:** (a) `pgSchema` not bare `pgTable`; (b) real `.references()` FK `source_run_id → autonomous_runs.run_id`; (c) polymorphic CHECK redesigned to **exactly-one-of-THREE** (`film_id` / `show_id` / `episode_id`), with matching partial indexes; (d) `ingest_method` / `provenance_tier` columns on `citations` **before first ingest** (retrofit = backfill); (e) `extraConfig` as array `(t) => [...]`, not object.
- **Do NOT expect to port:** working `confidence_score` calibration (never existed) or `trust_tier` seed data (two hardcoded food-critic arrays — film needs its own roster: trade press, Metacritic, RT Certified-Fresh, festival juries).
- **Shared client package:** extract `@solwend/db-client` (or `@jawnverse/db-client`) so the `pg`-direct-vs-`neon-http` dual-client idiom + the corrected comment live in ONE place, not copy-pasted per repo (f-003, f-033).
- **Repo shape:** the user chose `pgSchema` in the shared project, which pulls toward **monorepo-sibling under `solwend/platform/jawnflicks`** (it shares the Neon project and may import the shared db-client) rather than a fully standalone repo. Confirm at build time; standalone is still fine if you want independent deploy/versioning.
- **Ingest source:** decide Airtable (curated, high trust) vs RSS+LLM (auto, lower trust) up front — it drives whether `provenance_tier` needs >1 value (f-010).
