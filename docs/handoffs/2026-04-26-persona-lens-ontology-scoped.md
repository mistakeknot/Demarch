---
date: 2026-04-26
session: acb78ead
topic: persona-lens-ontology-scoped
beads: [sylveste-b1ha, sylveste-j5vi, sylveste-r3jf, sylveste-dsbl, sylveste-t2cs, sylveste-71nz, sylveste-2n8i, sylveste-g939, sylveste-1j30]
---

## Session Handoff — 2026-04-26 persona/lens ontology epic scoped

### Directive
> Your job is to begin executing the persona/lens ontology epic. Start by `bd ready` — F1 (sylveste-j5vi, Cypher benchmark spike) and F2 (sylveste-r3jf, D/D audit + module scaffold) are both unblocked P1s; pick one and run `/route` on it. Verify the epic shape via `cat docs/plans/2026-04-21-persona-lens-ontology-epic-execution.md`.
- Epic: **sylveste-b1ha** in_progress (kept open as parent — DO NOT close)
- Children (all OPEN, dep-wired): F1 j5vi, F2 r3jf, F3 dsbl←F1+F2, F4 t2cs←F3, F5 71nz←F4, F6a 2n8i←F2, F6b g939←F2+F5+F6a, F7 1j30←F2+F5
- Critical path: F1→F3→F4→F5→F6b = 7.5w dedicated lane / 15-18w interleaved
- F1 has an abandon branch: if AGE p95 > 2s at 100k edges, F3 blocks until redesign
- F6b abandon means Epic DoD #1 NOT MET — epic reopens, all-children-closed is necessary-but-not-sufficient
- Fallback: if neither F1 nor F2 fits the next session's available time, run `/clavain:next-work` to surface the highest-impact unblocked task across all Sylveste epics

### Dead Ends
- First Track A design subagent failed silently with permission error — wrote 5 specs in-context as fallback, generate-agents.py picked them up. If you re-run flux-review fan-out, dispatch the agent with explicit Write tool grant or use the inline-spec fallback pattern.
- `clavain-cli advance-phase` and `set-state epic_dod=<long-json>` consistently throw `state set failed: invalid JSON payload` errors — cosmetic, the artifact registry (set-artifact / get-artifact) is the actual source of truth. Do NOT chase these errors; verify with `clavain-cli get-artifact <bead> <type>`.
- Long DoD JSON > 500 chars rejects via bd's title length validation. Compress to short {c,auto} keys; full criteria live in PRD anyway.
- Tried full 4-track flux-review on a scoping brainstorm (auto-triage said 4) — trimmed to 2 tracks (adjacent + distant) per budget memory; that was correct. Distant track earned cost on exactly one finding (tier-laundering convergence). For non-ontology code review, drop distant tracks entirely.

### Context
- **Scoping sprint pattern.** This bead sylveste-b1ha was created as "scope an epic, not implement" per user choice at brainstorm Phase 0. Steps 5-8 of /clavain:sprint were skipped intentionally. The PRD lists this as a discipline note in the reflection — file follow-up bead for `/clavain:sprint --scoping` mode if you want to formalize.
- **The 11 gates G1-G11** are the load-bearing artifact. Every child bead's acceptance criteria reference specific gates by name. Plan review fails if any gate is elided in a child's implementation plan. Mapping table: `docs/prds/2026-04-21-persona-lens-ontology.md` end of file.
- **Apache AGE chosen over Neo4j/TerminusDB/Dgraph** — see `docs/research/assess-ontology-stores-2026-04-21.md`. Reason: Auraken already runs Postgres + pgvector; AGE is a Postgres extension (zero new ops surface). The whole "right-sized Palantir-style" framing rests on this — if AGE non-viable per F1 benchmark, the storage choice itself reopens.
- **Three pre-existing stores being unified:** `.claude/agents/fd-*.md` (660), `/home/mk/projects/auraken-web/data/lenses.json` (291), `/home/mk/projects/Sylveste/interverse/interlens/` plugin (288 via MCP). interlens MCP already ships graph-shaped tools (`find_bridge_lenses`, `get_dialectic_triads`) without a graph DB underneath — that's the tell.
- **Tier-laundering finding** (G3): cross-domain convergence from isnad + perfumery + sibu agents. The whole reason same-as has `source_independence` and `corroborator_count` fields and emits `candidate-same-as` for curator promotion (not auto-`same-as`). If you find yourself "simplifying" the dedup pipeline in F5, re-read G3 first.
- **F7 dependency**: depends on F2 + F5, NOT F6 — runs in parallel with F6a/F6b. The original DAG had F7←F6 incidentally; PRD review caught it.
- **CLAVAIN_SPRINT_OR_WORK=1** env var bypasses bd-push-dolt's TTY confirmation gate. Required when pushing beads non-interactively after a vetted sprint flow.
- **Generated agents**: 10 fd-* agents in `.claude/agents/` (5 adjacent for F1-F5 review domains + 5 distant: perfumery/sibu/isnad/quipu/noh). They're gitignored (regeneratable from `.claude/flux-gen-specs/persona-lens-ontology-brainstorm-{adjacent,distant}.json`) but landed and useful for any future ontology review.
- **Auraken pivot tension**: Auraken is pivoting to Hermes overlay (sylveste-heh8). Coordinate F3 migration timing with that team — don't introduce AGE schema while Auraken's own schema is mid-refactor.
