# Memory Lanes — routing policy across persistence systems

> Status: ACTIVE (2026-07-14, goal mk-5so). CanonGraph joins as the entity-graph lane.
> The failure mode this prevents: five memory systems all capturing the same fact
> ("memory sprawl"), or worse, capturing conflicting versions of it.

## The lanes

| System | Lane | Litmus test |
|---|---|---|
| **CanonGraph** (`sylveste` profile) | Entities, relationships, decisions-with-provenance | "Is this a fact about a *thing* (person, client, project, plugin, machine) or a *decision* that future sessions should query?" |
| **auto-memory + intermem** | Behavioral preferences, how-to-work-with-mk facts | "Is this about *how Claude should behave*, not about the world?" |
| **interknow** | Engineering patterns, solved problems, lessons | "Is this a reusable technique with evidence anchors (commits, files)?" |
| **`bd remember`** | Repo-scoped task insights | "Does this only matter inside one repo's task flow?" |

## Routing rules for proactive capture (the CanonGraph `capture` skill)

1. **Capture into CanonGraph** only facts expressible in the installed topology
   (Person, Machine, Project, Plugin, Client, Decision, Run — see
   `sylveste-topology.yaml`). Always `resolve` before `ingest`; set honest
   `confidence`; carry `source`.
2. **Do NOT capture into CanonGraph**: behavioral preferences ("mk prefers X
   response style"), engineering patterns ("SQLite WAL mode gotcha"), or
   transient task state. Those belong to their lanes above — leave them to the
   existing systems.
3. **Decisions are the highest-value capture.** A decision event should carry
   rationale, the deciding person, what it concerns (project/plugin), and — when
   an intercore run is active — a `decided_in` edge to the Run entity.
4. **One fact, one lane.** If a fact seems to fit two lanes, the *entity/decision*
   reading wins for CanonGraph only when the fact is about the world; the
   *behavioral* reading wins for auto-memory when it's about how to work.
   Never write both.
5. **Cross-references instead of duplication.** Auto-memory entries may point at
   graph entities by name ("see CanonGraph: Project canongraph") but must not
   restate graph facts; graph properties must not embed behavioral guidance.

## Audit method (gate for goal step 3)

After a working session: list new auto-memory entries, `bd memories` additions,
interknow entries, and `canongraph list` deltas. A double-capture = the same
fact appearing in two systems. Target: zero.
