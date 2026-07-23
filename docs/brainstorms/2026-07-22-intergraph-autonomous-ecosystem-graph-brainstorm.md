# Intergraph: Autonomous Self-Tuning Ecosystem Graph
**Bead:** Sylveste-8sp

## What We're Building

A plugin at `interverse/intergraph` that maintains a living graph of the Sylveste
ecosystem — nodes for plugins, skills, agents, MCP servers, hooks, services, and
repos; edges for how they *actually* connect — and keeps that graph true over time
by re-tuning edge weights from observed behavior.

interchart tells you what the ecosystem *declares*. intergraph tells you what it
*actually is*. The two compose: intergraph becomes the data source, interchart
stays the human-facing renderer (intergraph emits the scan JSON interchart already
consumes).

### Primary use cases (layered)
1. **Redundancy detection** — surface overlapping capabilities from evidence, not
   description-regex heuristics (today's scanner flags 38 overlap pairs that all
   need manual triage)
2. **Connection opportunities** — two tools that constantly co-occur in sessions
   but share no declared edge are a candidate integration; the graph finds these
   as a query, not an insight
3. **Agent-usable impact analysis** — an MCP query interface so any agent on any
   host can ask `neighbors(X)`, `path(A,B)`, `impact(file)`, `dead_nodes(days)`
   before changing something
4. **Drift reporting** — declared edges vs. observed edges, in both directions

## Why This Approach

### Three signal layers, increasing in value
1. **Declared structure (cheap, static).** What interchart's scanner already does,
   plus plugin.json manifests, SKILL.md frontmatter, hooks.json/settings.json
   wiring, `.mcp.json` / `.claude.json` server configs, package manifests. This is
   the skeleton.
2. **Real logic and routing.** How things actually connect: MCP tool schemas via
   live introspection (mcp-cli already does this on-demand), hook event → handler
   wiring, `interlab-route-heuristics.sh` and dispatch.sh's Zaka adapters,
   skill-to-skill `Skill` invocations and `/command` references across plugins,
   and code-level call graphs via `tldrs calls` / `tldrs impact` — that capability,
   at ecosystem scale.
3. **Observed behavior (the autotune).** cass session histories show which skills,
   commands, and MCP tools actually get invoked and which co-occur in the same
   sessions; beads already carries dependency edges (bv computes PageRank/critical
   path over them); git co-change shows cross-repo coupling. Edge weights =
   observed frequency with time decay, recomputed on each ingest.

### Boring storage, smart queries
- SQLite + JSON export. The ecosystem is ~250 nodes / ~320 edges — a graph DB
  (Kùzu, Neo4j) is ceremony at this scale.
- The intelligence lives in the ingestors and the query layer, not the store.

### Alternatives considered
- **Extend interchart's scan.js** — interchart is a static snapshot generator with
  regex-heuristic overlaps; bolting runtime ingest and weight decay onto it would
  blur its one job (rendering). Keep interchart pure, feed it better data.
- **Graph DB (Kùzu/Neo4j)** — real graph queries but heavy ops for ~250 nodes;
  SQLite recursive CTEs cover neighborhood/path queries fine at this scale.
- **intertrace as the substrate** — intertrace is a one-shot integration-gap
  tracer run per bead; intergraph gives it (and everything else) a persistent
  substrate instead. intertrace becomes a consumer.

## Key Decisions

1. **Sibling plugin, not interchart fork** — `interverse/intergraph`, same layout
   conventions as interchart.
2. **SQLite + JSON export** — no external services; JSON export is the interchart
   contract and the agent-readable dump.
3. **MCP server as the primary interface** — agents query the graph at runtime;
   humans get interchart's rendering of the same data.
4. **Weight = observed frequency with time decay** — edges the ecosystem actually
   uses stay strong; unused declared edges fade into drift reports.
5. **Three-phase sequencing** (below) — each phase ships queryable value; no big
   bang.

## Sequencing

| Phase | Scope | Value on landing |
|-------|-------|------------------|
| 1. MVP | Static + manifest ingestors, SQLite store, MCP query server, interchart JSON export | Declared graph agents can query; interchart rendered from real data |
| 2. Autotune | cass behavioral ingestor: edge weights, time decay, dead-node and missing-edge detection | Redundancy + connection-opportunity queries from evidence |
| 3. Code edges | tldrs call-graph ingest per repo | True impact analysis (`impact(file)` across the ecosystem) |

## Existing Pieces It Absorbs or Feeds

- **interchart** — stays as renderer; its regex overlap detector gets replaced by
  weighted evidence
- **intertrace** — gains a persistent graph instead of one-shot traces
- **tldrs** — provides code-level edges (phase 3)
- **bv / beads** — work-graph analysis pattern; beads deps become an edge source
- **mcp-cli** — live MCP tool-schema introspection pattern for layer 2
- **cass / alwe** — session-history behavioral signal for layer 3

## Open Questions

- Weight decay half-life: days or weeks? (Decide with real cass data in phase 2.)
- Should `suggested_connections()` require a minimum co-occurrence count, or rank
  purely by lift? Start with a count threshold; refine on triage experience.
- Cross-machine scope: zklw repos are canonical for many projects — does the
  ingestor run per-machine and merge, or run on zklw only? Defer to phase 2.
