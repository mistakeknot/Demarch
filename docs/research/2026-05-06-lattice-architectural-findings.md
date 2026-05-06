---
date: 2026-05-06
topic: lattice architectural findings — first scan of Sylveste
beads: [sylveste-buz7, sylveste-uj9f, sylveste-vbcp]
commits:
  lattice: [9224d7b, 256ec47, 649ca1d]
  monorepo: [27daa8a1]
queries: 10 named templates registered in lattice
---

# Lattice findings — Sylveste architectural scan

The architectural lattice now indexes Sylveste's structural skeleton — pillars, plugins, contracts, and the consume edges between them — and answers Palantir-style questions about the platform without grep gymnastics. This doc summarizes what one's first run surfaced.

## Executive summary

Six findings stand out:

1. **clavain is the central coupling hub** — every detected plugin cycle routes through it, because clavain is the workflow frontend that other plugins reference while it also references their commands.
2. **Two pillars hold no plugins** — Intercore and Skaffen are libraries-and-services, not plugin-shaped. The 6-pillar mental model maps cleanly to four plugin-bearing pillars and two infrastructure pillars.
3. **Twelve cross-plugin namespace collisions** are real bug surfaces, with `/status` contested by six plugins.
4. **Interverse holds 87% of the platform's contract surface** (206 of 237 first-party contracts), which is structurally correct but worth naming.
5. **Confirmed-confidence consume signal is zero today** — `allowed-tools` frontmatter is sparse in the wild, so all 114 consume edges are prose-derived `probable`.
6. **Orphan contracts are widespread but mostly noise** — skills are agent-routed by description, so explicit prose references are rare by design.

## Snapshot

| Layer | Count |
|---|---|
| Pillars | 6 |
| Plugins (first-party) | 64 |
| Contracts | 323 |
| `member_of` edges (plugin → pillar) | 63 |
| `offers` edges (plugin → contract) | 323 |
| `consumes` edges (plugin → contract) | 114 |
| `consumes` confidence breakdown | 114 probable, 0 confirmed |

Reproducible via `cd interverse/lattice && uv run python scripts/architecture_report.py --contracts --leverage`.

## Pillar capability density

| Pillar | Layer | Plugins | MCP servers | Skills | Commands | Hooks | Total contracts |
|---|---|---:|---:|---:|---:|---:|---:|
| Interverse | mid | 60 | 20 | 89 | 57 | 40 | 206 |
| Clavain | L2 | 1 | 0 | 19 | 52 | 14 | 85 |
| Interspect | mid | 1 | 0 | 0 | 17 | 3 | 20 |
| Autarch | L3 | 1 | 0 | 3 | 0 | 0 | 3 |
| Intercore | L1 | 0 | 0 | 0 | 0 | 0 | 0 |
| Skaffen | L2 | 0 | 0 | 0 | 0 | 0 | 0 |

**What the shape says.** Interverse is the cognitive surface — most of the platform's published interface lives there. Clavain stands alone as the workflow frontend with a slash-command-heavy surface (52 commands, no MCP). Autarch's three skills mark it as an early-stage app. Intercore and Skaffen are pillars, but they manifest as Go libraries and daemons rather than plugins, so they don't appear in the contract count. That's not a bug in the lattice; it's a real fact about the architecture, and it argues for keeping pillar-membership explicit (as we do today via path heuristic) rather than collapsing pillars to plugins.

**One classification gap.** `apps/interblog` is the only plugin without a pillar mapping. Either the 6-pillar framing needs an explicit corner for blog-style apps, or interblog belongs under one of the existing pillars and the heuristic should learn it.

## Cross-plugin name collisions

Twelve contracts collide on (kind, name) across two or more plugins (hooks excluded since fan-in is the design intent for hooks):

| Kind | Name | Count | Plugins |
|---|---|---:|---|
| command | `status` | 6 | clavain, interlock, interlore, interpath, interscout, interwatch |
| skill | `status` | 4 | interject, interscout, intersite, interstat |
| command | `setup` | 3 | clavain, interlock, intership |
| skill | `analyze` | 3 | interfluence, intersight, interstat |
| command | `changelog` | 2 | clavain, interpath |
| command | `doctor` | 2 | clavain, interkasten |
| command | `research` | 2 | interbrowse, interdeep |
| command | `review` | 2 | clavain, interlore |
| command | `scan` | 2 | interblog, interlore |
| skill | `report` | 2 | interstat, intertrack |
| skill | `scan` | 2 | interblog, interject |
| skill | `synthesize` | 2 | interbrowse, intermem |

**What this means.** When a user types `/status`, only one of six plugins resolves the unqualified form. Skill names compete for the same agent-routing slot. Some collisions are fine (each plugin's `/<plugin>:status` is unique and reachable), but the shorthand routing is a real bug source. Six plugins claiming `status` invites silent regressions when reorder or rename happens.

**Suggested action.** Either reserve common verbs (`status`, `setup`, `scan`, `analyze`, `doctor`) as documented namespaces with a single canonical owner, or add a structural test that flags new collisions in CI before they merge.

### Resolution: triage complete (sylveste-qow6, 2026-05-06)

Full triage in `docs/research/2026-05-06-collision-triage.md`. Headline: 8 of 12 lattice-reported collisions are connector false positives (it keys off filename stem, not the `name:` frontmatter field that several plugins already self-namespace via). Of the four real collisions:

- `command:research`, `command:scan` — accept as cross-domain verb sharing
- `command:status` — self-resolving via existing `interscout` deprecation
- `command:setup` — rename `intership:setup` → `intership:customize` (sylveste-t0sz)

Connector fix filed as sylveste-0usg (v0c.6). After it lands the collision detection becomes useful and a CI guard becomes worth adding alongside.

## Plugin-level dependency cycles

Four cycles surface in the consume graph, all centered on clavain:

| Length | Cycle |
|---:|---|
| 2 | clavain ↔ interlock |
| 2 | clavain ↔ interpath |
| 2 | clavain ↔ interwatch |
| 3 | clavain → interpath → interwatch → clavain |

**Why clavain dominates.** Clavain is the platform's command frontend. Other plugins reference its commands in their skills and docs. Clavain references their commands too, since its workflows orchestrate them. The result is a hub-and-spoke pattern that produces cycles when the spokes acknowledge the hub back.

**Whether this matters.** Cycles of length two between a frontend and its peers are tolerable in markdown-reference terms but become real risks if these plugins ever import each other's code or share lifecycle dependencies. The 3-cycle (clavain → interpath → interwatch → clavain) is more interesting because it implies coupling that no two-plugin pair captures alone.

**Suggested action.** Treat clavain as a known coupling hub and accept the cycle pattern, but consider whether interpath ↔ interwatch is genuinely necessary — that pair is the real coupling beneath the 3-cycle.

### Resolution: interpath ↔ interwatch is intentional (sylveste-8jx0, 2026-05-06)

After reading both AGENTS.md files, the back-reference is a deliberate **sensor/generator pattern**:

- interwatch detects drift, writes `.interwatch/drift.json`, dispatches `interpath:artifact-gen`
- `/interpath:all` reads `.interwatch/drift.json` to drive batch refresh
- The shared file is a **published contract**, not a code dependency

Both AGENTS.md files now carry an explicit "Architectural cycle (intentional)" note pointing back at this finding. The lattice's edge model treats markdown references as plugin-level edges, which collapses producer→artifact→consumer chains into apparent cycles. The clean fix is on the lattice side: a `FileContract` entity type would represent `.interwatch/drift.json` as a first-class node, replacing the cycle with a directed chain (interwatch → file → interpath). Filed as a v0c extension.

## Top leverage contracts

The contracts most other plugins reference, ranked by inbound consume count (self-references excluded):

| Inbound | Kind | Reference |
|---:|---|---|
| 3 | command | `/clavain:status` |
| 2 | command | `/interwatch:watch` |
| 2 | command | `/interpeer:interpeer` |
| 1 | command | `/clavain:brainstorm` |
| 1 | command | `/clavain:strategy` |
| 1 | command | `/clavain:compound` |
| 1 | command | `/interkasten:onboard` |
| 1 | command | `/interspect:interspect-propose` |
| 1 | skill | `/interpulse:pressure` |
| 1 | command | `/interpath:propagate` |

**What the distribution says.** The leverage curve is shallow today — three consumers is the platform's blast-radius peak. That tracks with consumer extraction being prose-only, so the count under-reads real consumption. The clavain cluster (status / brainstorm / strategy / compound / doctor / setup) shows clavain's commands are the most-named surfaces in other plugins' docs, which matches the cycle finding.

**Suggested action.** Treat `/clavain:status` and `/interwatch:watch` as load-bearing — changes to their interfaces deserve a wider review surface than a single-plugin diff would suggest.

## MCP server inventory

Twenty MCP servers, all stdio transport. Only interflux exposes more than one server (exa + openrouter-dispatch). Servers and their host plugins:

`intercache`, `interdeep`, `interfer`, `interfluence`, `interflux:exa`, `interflux:openrouter-dispatch`, `interject`, `interkasten`, `interknow:qmd`, `interlab`, `interlens`, `interlock`, `intermap`, `intermix`, `intermux`, `interrank`, `intersearch`, `interseed`, `tldr-swinton:tldr-code`, `tuivision`.

Most plugins follow the convention `plugin_name == server_name`. Three exceptions: interflux, interknow, tldr-swinton — useful to know if any future tool naming-convention check expects strict plugin-server match.

## Orphan contracts (signal interpretation)

| Kind | Count flagged orphan |
|---|---:|
| MCP server | 20 |
| Skill | 111 |
| Command | 111 |
| Hook | 57 |

**Why every MCP server is orphan.** Consumer extraction looks for `mcp__<server>__<tool>` in markdown. Real platform consumption happens at runtime, not via doc reference. So the orphan flag here means "no plugin documentation explicitly names this MCP tool," not "this server is unused."

**Why so many skill/command orphans.** Skills are agent-invoked by description, not by `/<plugin>:<skill>` typed reference. Commands get invoked by users in actual sessions, not by other plugins' markdown. So the orphan list is "no documented inter-plugin invocation," which is mostly the expected default.

**What it's actually useful for.** The orphan list works as a proxy for *documentation coverage* — the contracts that no other plugin's docs mention. That's a real signal for "underexplained surfaces," just not the "delete me" signal it might first appear to be.

## Method and limitations

**Connector** — `lattice.connectors.architecture.ArchitectureConnector` walks `{interverse, core, os, apps}` for `.claude-plugin/plugin.json` and the four contract surfaces. Skips vendored trees (`research/`, `node_modules/`, `.wrangler/`).

**Consumer extraction** — `_arch_consumers.py` parses SKILL.md and command markdown for two regex patterns: `/<plugin>:<name>` and `mcp__<server>__<tool>`. YAML `allowed-tools` frontmatter when present yields confirmed-confidence edges; prose matches yield probable.

**What it cannot see.**

- **Unqualified slash refs** (`/sprint`, `/help`) are not extracted. They route ambiguously and would need collision-resolution heuristics. Deferred to v0c.
- **Code-level imports** (Python imports, Go imports) are intermap's territory; lattice stays at the manifest+markdown surface.
- **Granular MCP tool consumption** — lattice resolves to the server level, not the individual tool. Tool-level granularity needs MCP introspection (calling each server's `tools/list`).
- **Runtime invocations** — what users actually type and what Claude actually calls during sessions is the truth that prose references approximate.

**What v0c could add.** Unqualified slash resolution with a precedence model, MCP tool-level extraction via introspection, a Service entity type for long-running daemons (intermux, intermap-mcp, interop), and a periodic re-harvest hook so the lattice stays fresh against the live tree.

## How to explore further

```bash
cd interverse/lattice
uv run python scripts/architecture_report.py                    # pillar + plugin overview
uv run python scripts/architecture_report.py --contracts        # capability matrix + collisions + MCP inventory
uv run python scripts/architecture_report.py --leverage         # top inbound + cycles
uv run python scripts/architecture_report.py --pillar Interverse  # all plugins in a pillar
```

Programmatic access via the named query templates registered in `lattice.templates`:

```
architecture_summary           plugins_by_pillar
contract_inventory             pillar_capability_matrix
cross_plugin_collisions        mcp_server_inventory
leverage_by_inbound_count      change_impact_for_contract
orphan_contracts               circular_dependencies
```

Each is invocable through the lattice MCP worker (`python -m lattice.worker`) once the architectural ontology has been ingested.
