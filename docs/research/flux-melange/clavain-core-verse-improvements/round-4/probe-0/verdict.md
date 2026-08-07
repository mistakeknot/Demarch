# Verdict — round-4 / probe-0 — fd-ecosystem-consolidation

Probe: confirm or refute f-155 ("lattice vs intergraph vs canongraph — three graph plugins with
overlapping purpose; duplication cost real but unquantified; possible merge candidate").

## Verdict on f-155

**Partially confirmed; the three-way merge is refuted.** The duplication is real but bilateral:
lattice and intergraph are two internal implementations of "harvest cass + tldrs (+ manifests) into
a queryable SQLite graph over the Sylveste ecosystem." canongraph is a different domain entirely —
a user-world memory graph — with live consumers; it is not a merge candidate with either.

## Capability map

| | lattice (repo: interweave) | intergraph | canongraph (external) |
|---|---|---|---|
| Domain | Cross-subsystem entity ontology (artifacts, processes, actors, relationships, evidence) | Ecosystem structure graph (plugins, skills, commands, hooks, MCP servers) | User-world memory (people, projects, decisions, documents) |
| Nodes/edges | 5 type families, 7 interaction rules, relational-calculus engine | Namespaced nodes; `part-of`, `provides-*`, `fires-hook`, `references`, `co-occurs`, `calls` edges | Entity types per topology; event-sourced provenance, confidence |
| Storage | `.lattice/crosswalk.db` (SQLite, per-project) | `data/intergraph.db` (SQLite) | SQLite, per-profile, redaction support |
| Ingest sources | cass, tldrs, beads, interlens, architecture docs, fd-agents, auraken lenses | manifests/SKILL.md/hooks (declared), cass sessions (observed, 14d half-life), tldrs Go imports + regex (code) | Agent-driven capture via MCP + /context-init interview |
| Interface | Python engine + templates; SessionStart reharvest hook | MCP stdio (8 `graph_*` tools) + CLI | MCP server + CLI + 2 skills |
| Size | 49 src py / 8,329 LOC + Go cmd/internal; 42 test files (488 pass) | 7 py / 955 LOC; 3 test files (22 pass) | 20 py / 4,904 LOC; 61 test files; CI, Docker, PyPI |
| Demand evidence | Off-marketplace, off-rig, uninstalled, **zero external consumers** | Off-marketplace, off-rig, uninstalled; MCP live in `.kimi-code/mcp.json`; interchart consumes its export; live DB 274 nodes / 2,332 edges | Marketplace-listed; user-scope MCP in `~/.claude.json`; 5 Clavain commands + 1 skill call it; 5 ops docs + drift-check service |

## Overlap quantification

- **Shared mechanism, not shared domain (all three):** each hand-rolls SQLite-graph-store + MCP/CLI
  query surface. Conceptual overlap only; no shared node vocabulary. Merging on this basis would
  conflate three domains.
- **Real duplication (lattice ∩ intergraph):** both ingest cass session histories
  (`lattice/connectors/cass.py` vs `intergraph/behavior.py`) and tldrs code structure
  (`lattice/connectors/tldr_code.py` vs `intergraph/code.py`) into a SQLite graph of the same
  ecosystem. ~2 of lattice's 8 connectors are functionally re-implemented in intergraph.
- **Duplication cost, now quantified:**
  - ~8.3k LOC + 42 test files + Go scaffolding maintained for zero consumers (lattice).
  - Two divergent checkouts of the same repo in one monorepo (`core/interweave` @09a7f94 with the
    `src/interweave` rename; `interverse/lattice` @8532bd2 with the kimi manifest) — every touch
    requires a reconciliation decision; tooling sees two plugins.
  - Three names for one plugin (repo `interweave`, plugin `lattice`, dirs `interweave`/`lattice`) —
    routing/registry confusion compounds f-029/f-033.
  - SessionStart hook spends session-start budget harvesting a DB nothing queries.
  - Consumer confusion is demonstrable: f-155 itself, and round-3 probe-2's census having to
    classify "third overlapping graph plugin."

## Recommendation: MERGE lattice into intergraph; COEXIST canongraph with a documented boundary

- **intergraph absorbs lattice.** intergraph is the natural target: smaller, already wired (Kimi MCP,
  interchart frontend), already flagged a hidden gem, and its three-layer signal model is a superset
  frame — lattice's unique connectors (beads, interlens, architecture docs, fd-agents) port cleanly
  as additional ingest layers if their entity detail is wanted. Lattice's ontology/rules engine is
  its only irreducible piece; with zero consumers it has not earned portability.
- **Migration:** (1) decide whether lattice's extra connectors are wanted as intergraph ingest
  layers — if yes, port beads/interlens/architecture (skip cass/tldrs, already covered); (2) retire
  the lattice SessionStart hook; (3) delete one checkout and archive the interweave repo with a
  pointer to intergraph; (4) publish intergraph to the marketplace (fixes its f-033 ghost status).
- **canongraph COEXISTs.** Boundary paragraph:

  > **Graph-plugin boundary.** *canongraph* owns the user-world memory graph: durable facts about
  > people, projects, decisions, and documents, captured with provenance as the user works — it
  > answers "what do we know about X?" *intergraph* owns the ecosystem structure graph: how Sylveste's
  > own plugins, skills, hooks, and MCP servers connect, behaviorally and in code — it answers "how
  > does the ecosystem fit together, and what breaks if I change Y?" Neither stores the other's
  > entities; Clavain `/recall` queries canongraph for world facts and intergraph (when published)
  > for ecosystem impact. A third internal ontology layer (lattice) was retired into intergraph in
  > round-4 consolidation.

- **RETIRE (not merge) as the acceptable fallback:** if the connector port is judged not worth it,
  lattice can simply be retired — its "finding-aid test" (delete lattice, everything still works)
  currently passes, which is the cleanest retirement signal a plugin can give.

## REMEDIATION

Warranted. In order:
1. Retire `interverse/lattice/hooks/sessionstart-reharvest.sh` from kimi.plugin.json + hooks/hooks.json (stop harvesting an unread DB).
2. Collapse the two checkouts: keep one, delete the other, archive the `interweave` repo with a pointer to intergraph.
3. Port lattice's beads/interlens/architecture connectors into intergraph as ingest layers, or explicitly decline in the archive note.
4. Publish intergraph to `core/marketplace/.claude-plugin/marketplace.json` and add it to an agent-rig profile (resolves its f-033 ghost slot).
5. Add the boundary paragraph above to the graph plugins' READMEs and the ecosystem docs index.

REMEDIATION: merge lattice into intergraph (port unique connectors or retire outright, kill the
SessionStart hook, collapse the dual checkouts), publish intergraph, and document the
canongraph=world-memory / intergraph=ecosystem-structure boundary.
