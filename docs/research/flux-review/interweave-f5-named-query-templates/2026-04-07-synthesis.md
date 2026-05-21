---
artifact_type: review-synthesis
method: flux-review
target: "docs/brainstorms/2026-04-07-interweave-f5-named-query-templates-brainstorm.md"
target_description: "F5: Named query templates for interweave ontology layer MCP tools"
tracks: 4
track_a_agents: [fd-mcp-tool-schema-discoverability, fd-query-template-protocol-design, fd-go-python-subprocess-bridge, fd-cross-connector-fan-out-reliability, fd-queryresult-serialization-contract]
track_b_agents: [fd-bi-report-template-registry, fd-reference-service-strategy, fd-regulatory-reporting-pipeline, fd-clinical-decision-support]
track_c_agents: [fd-edo-hangi-woodblock-registry, fd-aqrabadhin-compound-formulary, fd-marshallese-stick-chart-pattern, fd-ottoman-waqf-accounting-template]
track_d_agents: [fd-venetian-avogadori-di-comun-genealogical-registry, fd-yoruba-aroko-encoded-object-messaging, fd-syriac-masora-vocalization-intermediary-layer]
date: 2026-04-07
---

# Flux-Review Synthesis: F5 Named Query Templates

65 findings across 16 agents in 4 tracks. 3 P0, 27 P1, 26 P2, 9 P3.

## Critical Findings (P0)

### 1. Stdin/stdout deadlock on large payloads (Track A #7, convergence: 3/4 tracks)

The proposed Go-Python bridge (per-call subprocess with pipe-based JSON) will deadlock when any template produces >64KB output. Multi-connector queries like `bead_context` with 50+ related entities will hit this limit. Track C (C-011) and Track D (S-1) independently flagged the bridge architecture as problematic — Track D recommends an independent Python MCP server (Open Question #1 option b) instead of modifying the Go adapter.

**Fix:** Decide the bridge architecture now. Two viable options: (a) persistent Python worker process with newline-delimited JSON-RPC over stdin/stdout, or (b) independent Python MCP server that the Go adapter proxies. Both eliminate the deadlock and amortize startup cost. The brainstorm must resolve Open Question #1 as a Key Decision.

### 2. Silent empty join on cross-subsystem ID mismatch (Track C #C-001)

When a template joins entities across subsystems, differing ID formats (beads native ID vs canonical ID vs cass session ID) produce empty relationship graphs with no error. The template returns a complete-looking result with zero connections. The design does not mandate resolution through `Crosswalk.resolve()` for all cross-subsystem joins.

**Fix:** Add Key Decision: "All cross-subsystem joins must resolve through `Crosswalk.resolve(subsystem, subsystem_id)`. Direct ID string comparison across subsystems is prohibited. `QueryTemplate.execute()` receives a `Crosswalk` reference and all templates use it for identity resolution."

### 3. Go adapter modification violates intermediary-layer contract (Track D #S-1)

Adding Python subprocess dispatch to the Go MCP adapter means the base layer (attp protocol) is modified to accommodate the annotation layer (query templates). This couples the adapter to template execution lifecycle concerns.

**Fix:** Same as P0 #1 — independent Python MCP server or persistent worker subprocess. The Go adapter should proxy, not execute.

## Cross-Track Convergence (4/4 tracks)

### QueryResult is critically underspecified (convergence: 4/4)

The single highest-confidence finding. All four tracks independently identified that the `QueryResult` dataclass description ("entities, relationships, metadata") is insufficient:

- **Track A** (fd-cross-connector-fan-out, fd-queryresult-serialization): No partial result marking. CanonicalID not JSON-serializable. No datetime format specified.
- **Track B** (3/4 agents: BI, REG, CDS): Untyped metadata. No error taxonomy. No source status. No freshness timestamps. No schema versioning.
- **Track C** (fd-ottoman-waqf, fd-aqrabadhin, fd-marshallese): Structural variation across templates. No completeness signaling. Temporal mixing between real-time and closed-bead data.
- **Track D** (Avogadori, Aroko, Masora): Gap annotations missing. Per-template typed response fields needed. Error policy unspecified.

**Synthesized fix:** Define `QueryResult` fully in the brainstorm:

```python
@dataclass
class QueryResult:
    entities: list[dict]           # flat list, canonical IDs as strings
    relationships: list[dict]      # flat list, source/target as canonical ID strings
    metadata: QueryResultMetadata  # typed, not dict[str, Any]

@dataclass
class QueryResultMetadata:
    template_name: str
    template_version: str
    execution_timestamp: str                    # RFC 3339
    subsystem_status: dict[str, str]           # connector_name -> ok/unavailable/partial/timeout
    data_freshness: dict[str, str]             # connector_name -> last_harvest RFC 3339
    unresolved_entities: list[str]             # IDs that couldn't be resolved
    staleness_warnings: list[str]              # human-readable staleness notes
    crosswalk_snapshot_age_seconds: int         # max(updated_at) age
```

### Tool discoverability: overlapping scopes (convergence: 3/4)

- Track A #1: `who_touched_file` vs `actor_activity` — inverse queries, indistinguishable descriptions
- Track B REF-1: `who_touched_file` implies completeness it can't deliver (cass-only coverage)
- Track D A-2: `entity_relationships` vs `related_artifacts` — indistinguishable from MCP schema

**Fix:** Each tool description must state its primary-key entity type and explicit scope. Rename `who_touched_file` to `session_actors_for_file` if it only covers cass sessions (Track C #C-007 concurs).

### Partial result / completeness signaling (convergence: 4/4)

All tracks independently found that agents cannot distinguish "no data" from "subsystem unavailable":
- Track A #10, Track B BI-1/REG-1/REG-3, Track C #C-003, Track D V-2

**Fix:** `subsystem_status` field in `QueryResultMetadata` (see QueryResult spec above).

### Data freshness / staleness (convergence: 3/4)

- Track A #12: No staleness signal for crosswalk data age
- Track B CDS-2/REG-4: No per-source freshness timestamps
- Track C C-006/C-010: Temporal mixing; stale crosswalk after re-harvest

**Fix:** `data_freshness` dict in `QueryResultMetadata`.

## Domain-Expert Insights (Track A)

**TemplateRegistry collision handling (Track A #4, P1):** ConnectorRegistry silently overwrites — acceptable for 3 hardcoded connectors. TemplateRegistry will have 8+ built-in plus user/plugin templates. Silent overwrite causes invisible behavior changes. Fix: raise ValueError on name collision.

**Template dependency injection (Track A #6, P2):** Brainstorm doesn't specify whether templates are stateless (dependencies per-call) or stateful (stored references). The connector pattern uses per-call injection (`harvest(crosswalk, mode)`). Fix: `execute(context: QueryContext) -> QueryResult` where `QueryContext` bundles crosswalk + registry + engine.

**Pagination defaults (Track A #3, P2):** Without default limits, `entity_timeline` can return unbounded results. Even deferred to F6, a default `limit=100` in the base protocol prevents runaway responses.

## Parallel-Discipline Insights (Track B)

**Template versioning (Track B BI-2, P1):** Enterprise BI platforms version report template schemas independently of source system schemas. When a template's output shape evolves, agents consuming old schemas break. Fix: add `version: str` to `QueryTemplate` ABC.

**Entity-family scope validation (Track B REF-2, P1):** Passing an Actor entity to `related_artifacts` (which only handles Artifact-family via the Structure rule) returns silently empty results. Fix: templates declare accepted entity families; `execute()` raises on out-of-scope input.

**Graph traversal bounds (Track B CDS-1, P1):** `related_artifacts` for a popular utility module returns 47+ artifacts with no relevance ranking. Agents exhaust context budgets. Fix: `max_results: int = 20` default; results ranked by `relationship_strength`.

**Cursor-based pagination (Track B improvement #4):** limit/offset is fragile against insertions during multi-page traversal. Cursor-based pagination is more robust for timeline queries.

## Structural Insights (Track C)

**Path normalization must be shared (Track C #C-009, P2):** `session_entities` and `entity_timeline` will independently re-implement file path resolution. The aqrabadhin formulary lens identified this as a "shared preparation method" — a single `resolve_entity()` composition primitive should serve all templates.

**Infrastructure vs ontology events (Track C #C-005, P1):** `entity_timeline` conflates harvest-refresh timestamps with semantic changes. A re-harvest burst looks like intense modification activity. Fix: `event_kind` field distinguishing `"ontology_change"` from `"infrastructure_sync"`.

**No reverse-direction queries (Track C #C-008, P2):** All 8 templates are forward lookups (entity → context). No template supports "find entities matching a relationship pattern." The engine supports this via `get_valid_relationship_types()` but no template exposes it.

## Frontier Patterns (Track D)

**Non-caching constraint absent from ABC (Track D V-1, P1):** The Venetian Avogadori genealogical registry lens identified that a "catalog of catalogs" must never cache owned data — but the `QueryTemplate` ABC has no mechanism to declare or enforce this constraint. Templates that cache connector results create a shadow data store, violating interweave's "finding-aid" principle.

**Join ordering unspecified (Track D V-3, P1):** For multi-connector templates, the order of connector invocations affects result completeness when connectors have dependencies (e.g., cass sessions reference bead IDs that must be resolved first). The brainstorm doesn't specify join ordering.

**Template-level error policy (Track D S-3, P1):** The Syriac masora lens identified that each template needs a declared error policy: fail-fast (abort on any connector failure) vs best-effort (return partial). The brainstorm assumes best-effort everywhere but some templates (e.g., `entity_relationships` which is a pure engine query) should fail-fast.

## Synthesis Assessment

- **Overall quality:** The brainstorm correctly identifies the key architectural decisions (one-tool-per-query, protocol class + registry, composing existing primitives) but leaves the `QueryResult` contract and Go-Python bridge architecture critically underspecified. These two gaps will compound during implementation if not resolved at the brainstorm level.
- **Highest-leverage improvement:** Define `QueryResult` and `QueryResultMetadata` as typed dataclasses with explicit fields for subsystem status, freshness, and unresolved entities. This single addition resolves findings from all 4 tracks.
- **Surprising finding:** Track C's P0 on silent empty joins from ID format mismatches (C-001) — the brainstorm implicitly assumes all cross-subsystem joins "just work" but the existing codebase has three different ID formats across connectors with no normalization mandate.
- **Semantic distance value:** The outer tracks (C/D) contributed qualitatively different insights. Track C found the silent-empty-join P0 that Track A's bridge specialist missed (different failure mode, same bridge). Track D identified the non-caching constraint and intermediary-layer violation — architectural principles that domain experts took for granted. The esoteric lenses were less productive for concrete fixes but surfaced design-principle gaps invisible from the inside.
