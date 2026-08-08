# Findings Index — round-4 / probe-0

Lens: `fd-ecosystem-consolidation` (platform-consolidation architect).
Target: f-155 — "lattice vs intergraph vs canongraph — three graph plugins with overlapping purpose;
duplication cost real but unquantified; possible merge candidate."
Demand evidence used: `~/.claude/plugins/installed_plugins.json`, `~/.claude.json` mcpServers,
`os/Clavain/agent-rig.json`, `core/marketplace/.claude-plugin/marketplace.json`,
`.kimi-code/mcp.json`, grep for cross-repo consumers, per-repo git log, live test runs.

**VERDICT ON f-155: PARTIALLY CONFIRMED / MERGE SCOPE REFUTED.** The three-way merge is refuted —
canongraph is a different domain (user-world memory graph, external product, live consumers) and must
coexist. The duplication cost is confirmed and now quantified, but it sits between **lattice and
intergraph only**: both ingest cass session histories and tldrs code structure into a SQLite graph over
the Sylveste ecosystem, and lattice (8.3k LOC, 488 passing tests) has zero external consumers, two
divergent checkouts of the same repo inside one monorepo, and a live SessionStart hook harvesting a
database nothing reads.

```
SEVERITY | fd-ecosystem-consolidation | path | finding [t]
```

CRITICAL | fd-ecosystem-consolidation | interverse/lattice | Orphaned platform: lattice is 49 src files / 8,329 LOC Python + Go (cmd/, internal/) + 42 test files (488 tests pass, verified this probe) with ZERO external consumers — nothing outside the plugin imports `lattice`, reads `.lattice/crosswalk.db`, or invokes its engine; the only cross-repo mentions are historical docs (Clavain strategy.md's "lattice reconciliation", a 2026-04 worktree plan) [2026-08-06]
CRITICAL | fd-ecosystem-consolidation | core/interweave + interverse/lattice | One plugin, two divergent checkouts, three names: both dirs are checkouts of github.com/mistakeknot/interweave (plugin name "lattice"). core/interweave is at 09a7f94 and carries the in-progress rename (src/interweave/); interverse/lattice is one commit ahead (8532bd2 kimi manifest) but lacks src/interweave/ — they have diverged and neither is a superset. Census, routing, and marketplace tooling see two different plugins [2026-08-06]
HIGH | fd-ecosystem-consolidation | interverse/lattice/src/lattice/connectors/{cass,tldr_code}.py vs interverse/intergraph/intergraph/{behavior,code}.py | Duplicated ingest machinery: lattice's cass connector and tldr-code connector harvest the same two sources intergraph's behavior.py (session-history co-occurrence) and code.py (tldrs import analysis) already ingest — two parallel implementations of "cass + tldrs → SQLite graph" over the same ecosystem [2026-08-06]
HIGH | fd-ecosystem-consolidation | interverse/lattice/hooks/sessionstart-reharvest.sh | Hook with no consumer: lattice's SessionStart hook (registered in kimi.plugin.json + hooks/hooks.json) background-harvests crosswalk.db on every session start inside the Sylveste monorepo — recurring session-start cost maintaining a database no agent or command queries [2026-08-06]
MEDIUM | fd-ecosystem-consolidation | interverse/intergraph | Confirmed hidden gem (round-3 probe-2 upheld): working code (22 tests pass), live DB (274 nodes / 2,332 edges incl. 1,830 co-occurs behavioral edges), MCP registered in Sylveste/.kimi-code/mcp.json, interchart consumes its export format (interchart/data/scan.json matches `intergraph export` shape) — the strongest of the three internal candidates and the natural consolidation target [2026-08-06]
MEDIUM | fd-ecosystem-consolidation | interverse/intergraph | Partial wiring: intergraph's MCP server is registered for Kimi only (.kimi-code/mcp.json); it is absent from Claude Code installs, agent-rig profiles, and marketplace.json (f-033/f-124 ghost, already upheld) — its "queryable from any MCP host" premise holds for exactly one host [2026-08-06]
LOW | fd-ecosystem-consolidation | ../canongraph (external) | Distinct domain, real demand: canongraph is a user-world memory graph (people/projects/decisions with provenance), an external product (jvattimo1, forked), registered as a user-scope MCP server in ~/.claude.json, consumed by 5 Clavain commands (/recall treats it as the C3 entity-graph source) + upstream-sync-engine skill, with 5 ops docs and a drift-check service under ops/canongraph/ — NOT a merge candidate with either internal plugin [2026-08-06]
LOW | fd-ecosystem-consolidation | core/marketplace/.claude-plugin/marketplace.json | Asymmetry note: canongraph (external) is marketplace-listed while the two internal graph plugins are not — discovery currently favors the plugin that needs it least [2026-08-06]
