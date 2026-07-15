# Recall Lanes — the four retrieval surfaces and how to query them

> Companion to `memory-lanes.md` (which governs *capture* routing). This documents
> *recall*: where knowledge lives, how to query each lane, and what provenance each
> carries. `/clavain:recall` fans out across all four (goal mk-1pd).

| # | Lane | What lives there | Query interface | Provenance shape |
|---|------|------------------|-----------------|------------------|
| 1 | **CanonGraph** (`sylveste` profile, zklw:3943) | Typed entities + relationships + decisions-with-rationale (who/what/why-decided) | MCP `mcp__canongraph__resolve` (exact name→entity), `mcp__canongraph__query` (named: `decisions_for_project`, `decisions_in_run`, `projects_on_machine`, `plugins_maintained_by`, `upstreams`, `projects_for_client`), `mcp__canongraph__search` (semantic, ingested docs) | Per-event `source` / `confidence` (0–1) / `actor` in an immutable log; entity_id; ask "why do you believe this" via event replay |
| 2 | **interknow/qmd** | Engineering patterns, solved problems (`config/knowledge/*.md`), plus `docs/solutions/**` via intersearch | MCP `mcp__plugin_interknow_qmd__query` (sub-queries: `lex` BM25 / `vec` semantic / `hyde`; always pass `intent`), `multi_get`/`get` for retrieval | YAML frontmatter: `provenance: independent\|primed`, `lastConfirmed`, evidence anchors (paths, SHAs), decay-to-archive after 10 unconfirmed reviews |
| 3 | **Auto-memory files** | Behavioral prefs, how-to-work facts, project bootstrap pointers | Read `MEMORY.md` index + topic files at `~/.claude/projects/<proj>/memory/`; Grep with context | `# [date:YYYY-MM-DD]` comments; index line per memory; `[[name]]` cross-links |
| 4 | **bd memories** | Repo-scoped task insights | `bd memories <keyword>` (CLI, cwd-sensitive — run from the repo) | Bead ids + timestamps in the shared Dolt DB |

## Merge order (provenance-ranked)

Graph entities/decisions (typed, event-sourced, confidence-scored) → interknow confirmed
patterns (`independent` > `primed`, recent `lastConfirmed` first) → memory files → bd
insights. Dedupe cross-lane restatements: when a memory file *points at* a graph entity
(the lane policy's cross-reference rule), show the graph entity and cite the pointer.

## Lane-selection heuristic for a question

- "what/who is X", "what did we decide about X", "where does X live" → **graph first**
- "how do we handle X", "what do we know about <technique>" → **qmd first**
- "how should you behave / what does mk prefer" → **memory files first**
- "what happened in this repo's tasks" → **bd first**

All four always run in `/recall`; the heuristic just orders presentation when results tie.
