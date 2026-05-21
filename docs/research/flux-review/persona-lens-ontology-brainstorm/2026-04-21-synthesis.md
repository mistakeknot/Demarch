---
artifact_type: review-synthesis
method: flux-review
target: "docs/brainstorms/2026-04-21-persona-lens-ontology-brainstorm.md"
target_description: "Persona/lens ontology unification brainstorm"
tracks: 2
track_a_agents: [fd-ontology-schema-discipline, fd-age-cypher-query-economics, fd-semantic-dedup-calibration, fd-triage-lift-measurement, fd-multi-store-ingestion-safety]
track_c_agents: [fd-perfumery-base-accord-composition, fd-sibu-classification-fit-check, fd-isnad-chain-integrity, fd-quipu-cord-typing-discipline, fd-noh-kata-canonical-form-drift]
date: 2026-04-21
bead: sylveste-b1ha
findings_total: 61
p0: 9
p1: 22
p2: 22
p3: 8
---

# Flux-Review Synthesis — Persona/Lens Ontology Unification Brainstorm

Two tracks, ten agents, 61 findings. Adjacent-domain specialists pressure-tested the five load-bearing engineering commitments (schema, AGE query plans, dedup calibration, measurement pre-registration, ingestion safety). Distant-domain agents applied structural isomorphisms from perfumery, Qing cataloging, hadith authentication, Inka quipu, and Noh transmission. The distant track independently converged on several of the same defects the adjacent track flagged — and surfaced one class of risk (tier laundering through `same-as`) that the adjacent track only partly saw.

## Critical Findings (P0/P1)

Nine P0s and twenty-two P1s. The strategy step cannot proceed cleanly without resolving these first. Grouped by the action each forces.

**1. The MVP Cypher query is not concretely plannable (ACQ-01, P0, Track A — fd-age-cypher-query-economics).** "Domain × discipline × effectiveness × community neighborhood" either collapses into a small index-friendly query (in which case the graph-DB case weakens) or requires the multi-hop traversal that is AGE's known weak spot. Recommendation: the plan's first child bead is a week-1 benchmark spike — load 10k then 100k synthetic edges, EXPLAIN ANALYZE the actual triage query, decide AGE-viable vs. redesign before Epic shape #4 begins. Write the EXPLAIN ANALYZE artifact into the epic plan as an acceptance gate.

**2. "Idempotent" is asserted without specifying the key (MIS-01, P0, Track A — fd-multi-store-ingestion-safety).** Default "idempotent" implementations create duplicates on second run; the semantic dedup pass then masks the bug by populating `same-as` at cosine 1.0. Recommendation: the ingestion child bead must specify idempotence key per importer (frontmatter `name` for fd-agents, explicit JSON `id` for Auraken/interlens), MERGE-on-key upsert semantics, and a regression test that runs the importer twice and asserts stable node count.

**3. Tier laundering via `same-as` (P0 — isnad, P1 — perfumery two-roses, P1 — sibu 互見, P1 — adjacent fd-semantic-dedup-calibration SDC-01/SDC-02).** See Cross-Track Convergence below — this is the highest-confidence finding of the review. Schema must distinguish source-independence from embedding similarity; dedup must emit `candidate-same-as` for human promotion, not `same-as`.

**4. Bridges edge is underspecified in three ways (P0 — quipu cord-typing, P1 — perfumery temporal layering, P1 — quipu bridge_score transit).** Symmetric vs. directed is undefined; temporal activation (immediate vs. sequential revelation) is absent; Auraken's lens-level `bridge_score` has no specified transform to AGE's edge-level `bridges.strength`. All three must be resolved in the DDL — cannot be retrofitted after Phase 2 ingestion writes 1000+ bridges edges.

**5. No canonical query authority across the three views (P0 — noh iemoto, echoes perfumery P2 projection drift and isnad effectiveness_score P1).** Each view (flux-drive triage, Hermes, Catalog) will implement "find persona for task" independently. Recommendation: designate flux-drive triage view as the iemoto reference implementation and extract selection logic into a versioned `ontology-queries` module; make Hermes and Catalog adapters, not reimplementers. Without this the ontology becomes three ontologies within 18 months.

**6. Bi-temporal versioning conflates instance and schema change (P0 — sibu, P2 — noh schema_version).** `valid_from`/`valid_to` cannot distinguish "deprecated instance" from "schema migration artifact." Add `schema_version: semver` to all entities in migration 001. One column, irreversible to retrofit.

**7. Evidence nodes lack strength_grade (P0 — isnad jarh wa-ta'dil).** A lens citing a Nature paper and a lens citing a Medium post are indistinguishable under the `cites` schema. Add `strength_grade: enum[sahih, hasan, da'if, mawdu]` to Evidence and `transmitter_tier` to `cites` in initial DDL.

**8. Identity vs. versioning for edited Lenses is unspecified (OSD-02, P1, Track A — fd-ontology-schema-discipline).** Whether edits mutate the Lens node or create a superseding node determines ingestion, dedup, and triage query shapes. Recommend immutable Lens + `supersedes` + `lens_identity_uuid`. Freeze in strategy step.

**9. Domain/Discipline will collapse in practice (OSD-01 adjacent, P1 sibu 經部/子部 distant — converged).** Both tracks independently flag the same boundary failure. Before DDL, produce a concrete mapping of the existing 660 fd-agent `domains` + 291 Auraken `discipline` values; if >30% overlap, collapse to one type with `kind: {tag, formal-field}`.

**10. No primary metric committed, baseline not frozen, held-out corpus undefined, cost confound unaddressed (TLM-01 through TLM-05, all P1/P2, Track A — fd-triage-lift-measurement).** Collectively these make the MVP unmeasurable. A one-page pre-registration doc — primary metric (recommended: review-coverage-per-diff), baseline SHA frozen at Epic #4 day 1, 30-diff paired corpus, ship/abandon thresholds, cost-per-finding as secondary — is non-negotiable before triage code is written.

**11. Source-of-truth precedence undefined between Auraken and fd-agents (MIS-03, P1 adjacent; mirrors isnad P1 Source-as-label, P1 transmission chain).** Both tracks surface the same issue: Auraken lenses.json already extracted from flux-review-ep11, so some lenses are "owned" by two importers. Define per-field source precedence (Auraken owns effectiveness_score/bridge_score/community_id; fd-agent owns review questions/persona pairing) and make derives-from a reconstructible Transmission chain, not a terminal label.

## Cross-Track Convergence

Findings both tracks surfaced independently, ranked by convergence count. These are the highest-confidence signals of the review.

**Rank 1: Tier laundering via same-as (convergence 4/10, both tracks).** fd-isnad-chain-integrity (Track C) flagged this P0 as "semantic dedup conflates embedding similarity with source independence" — an LLM-batch lens inheriting tier-1 status via a 0.85-cosine same-as edge to a manually-authored lens. fd-perfumery-base-accord-composition (Track C) framed the same defect as "the two-roses collapse" — Persian-medicine-assayer and Akan-goldweight-metrology embed at 0.82 because both are pre-modern non-Western metrology, but they are culturally distinct lenses. fd-sibu-classification-fit-check (Track C) described it as `same-as` accumulating as the 互見 classification escape hatch. fd-semantic-dedup-calibration (Track A) surfaced the mechanical precursor: no model, no threshold, no calibration corpus, so same-as edges are "vibes-based merge-and-hope." The four framings converge on identical fixes: require `source_independence` and `corroborator_count` fields on same-as, emit `candidate-same-as` for curator promotion rather than automatic `same-as`, and embed essence-text-only (drop task_context) to prevent cross-store asymmetric similarity. The triple-distant convergence plus adjacent mechanical grounding is unusually strong evidence.

**Rank 2: Bi-temporal versioning is insufficient as specified (convergence 3/10, both tracks).** fd-sibu P0 and fd-noh P2 both independently flagged that schema-level changes collapse into the same timestamps as instance-level changes. fd-age-cypher-query-economics (ACQ-04) flagged the same column from a different angle — `valid_from`/`valid_to` filters will destroy index usage without a partial-index strategy. Convergent fix: add `schema_version: semver` and a `WHERE valid_to IS NULL` partial index in migration 001.

**Rank 3: View projection drift / no canonical authority (convergence 3/10, Track C only for canonical-form, Track A for query economics).** fd-noh P0 is the primary finding — no iemoto reference implementation. fd-perfumery P2 (concentration drift) and fd-isnad P1 (effectiveness_score has no derivation owner) independently describe the same structural defect: each view team will implement selection logic with its own interpretation. Track A's fd-age-cypher-query-economics ACQ-05 touches the same surface via the MCP adapter (per-query planning cost without a cache surfaces on interactive paths, so each caller independently experiences query-semantics drift). Convergent fix: extract `ontology-queries` as a versioned module; Hermes and Catalog are adapters, not reimplementers.

**Rank 4: Domain/Discipline boundary instability (convergence 2/10, both tracks).** fd-ontology-schema-discipline OSD-01 (adjacent) and fd-sibu-classification-fit-check P1 (distant) independently identify the same collapse. Track A frames it as a pragmatic ingestion failure (>40% overlap); Track C frames it as structural (the Qing jing/zi boundary problem). Same fix: dual-typing with `formalization_level: float` or collapse to one type with `kind:` property.

**Rank 5: Source as terminal label, not reconstructible chain (convergence 2/10, both tracks).** fd-multi-store-ingestion-safety MIS-03 (adjacent, source precedence undefined) and fd-isnad-chain-integrity P1 (distant, Source is terminal label not isnad chain) surface the same defect from mechanical and epistemic angles. Both converge on: replace monolithic Source with a Transmission chain with `transmitter`, `transmitter_tier`, `transmission_method`, `prior_transmission`.

## Domain-Expert Insights (Track A)

**Schema.** fd-ontology-schema-discipline's strongest contribution is OSD-02 — freezing the Lens identity model (immutable + supersedes + `lens_identity_uuid`) before DDL. This pervades ingestion, dedup, triage, and every view; no distant agent would have surfaced it because it requires knowledge of how AGE, upsert semantics, and edit concurrency interact.

**Query economics.** fd-age-cypher-query-economics ACQ-02 (AGE + pgvector integration has no stated plan) is pure adjacent-expert value — distant agents have no vocabulary for "CTE with Cypher subquery plus SQL vector filter vs. duplicated embeddings in vertex properties with no index." ACQ-05 (interlens MCP adapter needs a cached projection) is similarly adjacent-only.

**Dedup.** fd-semantic-dedup-calibration SDC-04 (cross-store asymmetric text density distorts embeddings — fd-agents have rich task_context, Auraken lenses lack it) is the most actionable single insight in the adjacent track. The fix (embed essence text not raw records, normalize length) is cheap and a precondition to any threshold calibration being meaningful.

**Measurement.** fd-triage-lift-measurement's whole package is adjacent-only value. The cost confound (TLM-04) is especially sharp: an ontology query that picks 7 agents vs. baseline 4 will mechanically find more P0/P1s without any quality improvement. Requires cost-per-finding as a mandatory secondary, not an afterthought.

**Ingestion.** fd-multi-store-ingestion-safety MIS-02 (filename is not a stable ID for fd-agents) and MIS-04 (partial-failure replay via per-entity transactions and a manifest log) are bread-and-butter adjacent expertise that would not appear in any structural-isomorphism review.

## Structural Insights (Track C)

**fd-isnad-chain-integrity.** The jarh wa-ta'dil grading matrix (P3) translates directly to schema: confidence × source_independence × corroborators → {mutawatir, sahih, ahad-da'if, related-to}. This is a new design direction — it replaces the single-threshold dedup policy with an equivalence authentication matrix. High transfer value, because Islamic hadith scholarship has centuries of lessons on exactly this problem. Also: the `InvocationEvent` pattern (P2) — MCP request logs as tawatur evidence — refines an existing decision (MCP log migration) by reframing logs as first-class provenance nodes.

**fd-perfumery-base-accord-composition.** Two distinct contributions. (i) Fixative lenses as reified ternary relationship (P1): Persona + Lens_A + Lens_B where Lens_A only works when Lens_C stabilizes it. Maps to interlens's `get_dialectic_triads` — a new design direction that preserves stability information that pairwise `bridges` edges lose. (ii) Temporal layering on bridges (P1): `activation_delay: enum[immediate, short, medium, long]` encoding base/heart/top-note timing. Refines an existing decision (bridges edge schema); cheap to add.

**fd-sibu-classification-fit-check.** Concept as 雜家 (residual catch-all, P1) is the sharpest distant-framing transfer. The Qing solution — split Concept into Concept/Primitive and Concept/Pattern with explicit admission criteria — is a concrete design direction the adjacent schema review (OSD-03) identified the same gap but stopped short of solving. Also reframes Task-context deferral as "classification escape rather than principled deferral" — adjacent review saw the same thing but framed it as cardinality concern; distant framing reveals it is ontological, not a database optimization.

**fd-quipu-cord-typing-discipline.** Cord-grammar transfer produces the most mechanical distant contribution: edges should carry structural weight equal to nodes. P0 bridge symmetry and P0 multi-edge `wields` discrimination are both low-level schema decisions where quipu's "different colored cords at the same attachment point mean different things" framing forces the schema to make explicit what AGE implicitly leaves as query-author choice.

**fd-noh-kata-canonical-form-drift.** The iemoto P0 is the single highest-leverage distant insight. It opens a new design direction (extract `ontology-queries` as a versioned module, make views adapters) that no adjacent agent surfaced — because the isomorphism is social (schools of transmission) rather than mechanical.

## Synthesis Assessment

**Overall quality.** The brainstorm is structurally sound — seven types, ten edges, three views, explicit MVP — but consistently uses aspirational language ("idempotent," "embedding-based," "measurable lift," "bi-temporal") where the strategy step needs commitments. The defects are not brainstorm-level; they are commitments that must land in the PRD and the children beads.

**Highest-leverage single commitment.** Designate flux-drive triage view as the iemoto canonical reference and extract selection logic into a versioned `ontology-queries` module before Phase 4 begins. This one move addresses the noh P0, the perfumery P2, the isnad effectiveness_score P1, the ACQ-05 MCP caching concern, and prevents the 18-month three-schools drift that would otherwise be structural. No other single commitment has this reach.

**Surprising finding.** The tier-laundering convergence. The adjacent track saw dedup needed calibration; only the distant track (three independent agents from Islamic, French, and Qing traditions) surfaced that unguarded `same-as` is an *automatic* tier-laundering vector — it happens during a routine Phase 3 run without any explicit merge operation, silently granting tier-1 status to LLM-generated lenses. No single track would have surfaced this; the mechanical critique from Track A stayed at threshold calibration, and any single distant agent would have been dismissible as vocabulary transfer.

**Semantic distance value.** Track C earned its distance on three findings: (i) the tier-laundering mechanism via source_independence (isnad, genuinely novel), (ii) the iemoto canonical-authority P0 (noh, genuinely novel — adjacent agents saw view drift but not the authority structure), and (iii) the fixative-triad schema (perfumery, new design direction). Track C restated-in-costume on two findings: the Domain/Discipline boundary (sibu's jing/zi framing is the same finding as OSD-01, more elegant but not additive) and the bi-temporal schema-vs-instance distinction (sibu's Qing-catalog framing adds flavor but the mechanical fix — `schema_version` column — is the same one any adjacent DB expert would propose). Quipu's cord-typing discipline felt like the weakest distance-earning — several of its findings (bridge symmetry, multi-edge `wields`) are issues any Cypher expert would flag; the quipu framing is decorative, not load-bearing. Net: distant track delivered ~3 of 31 findings with qualitatively different insight, ~15 that reframed adjacent findings usefully but non-additively, and ~13 that were either redundant or weaker expressions of adjacent findings.

**SHIP-READY to strategy? Yes, with a clear gate list.** The brainstorm itself is not defective. The findings are downstream commitments that the strategy PRD and children-beads design must lock in. The strategy step should open with a "Brainstorm-to-Plan Gate List" that captures the nine P0s as explicit decisions requiring sign-off before children beads are filed. If those gates are honored, the epic is shippable. If they are elided, the epic will fail in predictable ways the two tracks have already mapped.
