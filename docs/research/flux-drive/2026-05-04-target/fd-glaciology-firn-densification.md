### Findings Index
- P1 | FIRN-1 | "Axis 1: Usability — Memory system" | MEMORY.md mutates in-place: provenance for feedback rules is destroyed at the moment of update
- P1 | FIRN-2 | "Axis 2: Token Efficiency — Orchestration preamble" | MEMORY.md active section carries archival content that has crossed close-off depth — dead weight on every session
- P2 | FIRN-3 | "Axis 1: Usability — Beads workflow" | Beads history has no annual-layer index — sprint boundaries are not used as layer markers for search or recall
- P2 | FIRN-4 | "Axis 1: Usability — Handoff docs" | Handoff docs carry no trapped-air signature: the project state at the time of writing is not recoverable from the doc
- P3 | FIRN-5 | "Axis 2: Token Efficiency — Memory system" | Hiatus unconformity is not detected: stale project lanes accumulate in MEMORY.md's Active Projects section without expiry
Verdict: needs-changes

### Summary
The glaciology firn model surfaces a structural provenance failure in Sylveste's knowledge layer. MEMORY.md at 132 lines / 120 budget has crossed close-off depth — it is no longer exchanging fresh provenance with the surface; instead, historical entries about completed projects remain in the active layer, consuming token budget on every session load. Firn does not edit in place: each year deposits a layer, and the layer below densifies on its own schedule. Sylveste edits in place, erasing the deposition record. A feedback rule updated without a timestamp loses its "why" the moment it is written.

### Issues Found

**FIRN-1. P1: MEMORY.md mutates in-place: provenance for feedback rules is destroyed at the moment of update**

Axis: usability (specifically: memory system UX, feedback loop fidelity)

Source-domain mechanism: **Firn layer-vs-edit-in-place**. Glaciologists drilling EPICA Dome C (Antarctica) can read atmospheric CO₂ from 800,000 years ago because each firn layer sealed its trapped-air content at deposition. The layer does not merge with the layer above it. Sylveste's MEMORY.md under `/home/mk/.claude/projects/-home-mk-projects-Sylveste/memory/MEMORY.md` uses `intermem:memory-tidy` to consolidate entries. When consolidation runs, "feedback_no_rhythm_reset.md: No stacked short sentences at paragraph end" is updated — but when was this rule added? Was it from a single session or confirmed across five? That provenance is gone.

Current state: `MEMORY.md` is a flat markdown file with sections (Discipline Lessons, Workflow Patterns, etc.). Entries are updated in place by `intermem:memory-tidy` and by agents during sessions. There is no per-entry timestamp, no edit history, no "deposition record." A reader cannot reconstruct whether a feedback rule is 2 days old or 2 months old, whether it was confirmed once or dozens of times.

Concrete failure scenario: An agent reading `feedback_voice_calibration_intersite.md` cannot tell whether this voice rule is recently active (worth enforcing strictly) or stale (user has evolved their preferences). The agent enforces it strictly. The user corrects the agent. The correction is added as a new entry. The old entry is still present. Two contradictory rules coexist. No session can resolve the conflict without reading the user's message history.

Proposal: Add a **deposition header** to each MEMORY.md entry (in the linked `.md` files under `memory/`):
```
---
deposited: 2026-02-14
last_confirmed: 2026-04-21
confirmation_count: 3
---
```
The `intermem:memory-tidy` skill should increment `confirmation_count` and update `last_confirmed` when an agent confirms the rule applies, rather than rewriting the entry body. The body is append-only after initial deposition; corrections add a new entry with `supersedes: <old-entry-id>` rather than overwriting. This is the firn model: new deposition on top, old layers preserved below.

Estimated savings: Primarily usability — agents can now prioritize rules by `last_confirmed` and `confirmation_count` rather than treating all rules as equally current. Secondary token savings: stale rules (last_confirmed > 90 days, confirmation_count < 2) can be excluded from session context automatically, reducing MEMORY.md effective size by an estimated 20-30 lines / ~800 tok/session.

Difficulty: M (multi-PR: modify `intermem:memory-tidy` to write deposition headers, update agents that write memory to use append-not-overwrite semantics, add staleness filter to MEMORY.md auto-load)

Risk: Append-only semantics require a consolidation mechanism (like firn sintering into ice). Without periodic compaction, MEMORY.md grows unboundedly. Mitigation: the close-off depth mechanism from FIRN-2 handles this.

---

**FIRN-2. P1: MEMORY.md active section carries archival content that has crossed close-off depth — dead weight on every session**

Axis: token-efficiency

Source-domain mechanism: **Firn close-off depth (~80m)**. At approximately 80m depth in an Antarctic firn column, the overburden pressure is sufficient to close off air exchange between the firn and the surface atmosphere. Below this depth, trapped air bubbles are sealed and the record is permanent. Above this depth, the firn is still exchanging gases with the surface. The key insight: the close-off depth is a phase transition, not a threshold. Material above it is active; material below it is archival.

Current state: MEMORY.md is noted in the target document as "over budget (132 lines / 120 budget)" under Axis 1. The `Active Projects` section in MEMORY.md contains entries for completed or deferred projects (e.g., `project_launch_deferred.md` — "Sylveste launch deferred 3 months"). These entries are in the same active layer as currently-active projects (interop, Ockham, lattice naming). Every session that loads MEMORY.md pays the token cost for all of them.

Concrete failure scenario: An agent starting a new session reads all 132 lines of MEMORY.md including the full `project_auraken_go_migration.md` entry ("(historical) Auraken→Skaffen Go migration; benl.1-4 shipped, benl.6-11 mooted by Hermes pivot"). This is historical context that the agent does not need for most tasks, but it cannot distinguish it from active context. The agent may use the now-superseded Go migration framing when answering Auraken-related questions (this failure mode is noted in the `feedback_reanchor_to_pivot_memory.md` memory entry itself).

Proposal: Apply the **close-off depth rule** to MEMORY.md tiering:
- **Surface firn** (active, mutable): entries where `last_confirmed` < 30 days OR `project_status = active`. Loaded every session.
- **Sintered firn** (recent, reference-only): entries 30-90 days old OR `project_status = deferred`. Loaded on demand (`@memory <topic>`).
- **Ice** (archival, permanent): entries > 90 days old AND `project_status = complete|historical`. Compressed to a 1-line reference entry. Not loaded unless explicitly requested.

`intermem:memory-tidy` should implement depth-tiering: when a project is marked complete, its MEMORY.md entry crosses close-off depth and compresses to: `[project_auraken_go_migration.md] Auraken Go migration (historical) — see docs/handoffs/2026-04-16-*.md for full record.`

Estimated savings: Based on the current 132-line MEMORY.md, approximately 30-40 lines (historical/deferred entries) would compress to 8-10 reference lines. Net reduction: ~600-700 tok/session on MEMORY.md load. Combined with FIRN-1's staleness filter: ~1,400 tok/session total.

Difficulty: S (single PR: add tiering logic to `intermem:memory-tidy`, add `project_status` field to memory topic files, update MEMORY.md auto-load to filter by depth tier)

Risk: Aggressive archiving could exclude a rule that is still relevant but not recently confirmed. The 90-day threshold may be too short for stable, slow-moving preferences. Mitigation: confirmation_count from FIRN-1 provides a secondary signal — high-confirmation-count entries stay in surface firn regardless of age.

---

**FIRN-3. P2: Beads history has no annual-layer index — sprint boundaries are not used as layer markers for search or recall**

Axis: usability (specifically: bead search/dedup workflow)

Source-domain mechanism: **Annual layer chronology**. Ice core scientists use annual layers (visible as alternating light/dark bands in winter vs summer deposition) to create a timeline without relying on absolute dating. Each annual layer has a thickness proportional to annual snowfall, and visible markers (volcanic tephra, cosmic ray events) create anchor points. The key: annual layers are the natural search unit for a time-ordered record.

Current state: Beads are stored in per-project Dolt at `.beads/dolt/` (v0.60.0). `bd list`, `bd search`, and `bd ready` operate across all beads regardless of when they were created. Sprint/bead documentation exists (`agents/beads-workflow.md`) but sprint boundaries are not used as index markers. A search for "routing bug" returns all matching beads from all time periods with no temporal grouping.

Proposal: Instrument **sprint-boundary layer markers** in the beads index:
- At sprint close (`clavain:land`), write a `sprint-layer` record to the beads Dolt DB: `{sprint_id, closed_at, bead_count, open_count}`.
- `bd search` adds a `--sprint` flag that filters to a specific sprint layer.
- `bd ready` shows the current sprint layer's beads first, with a separator before cross-sprint candidates.
- Annual layer analog: a weekly `bd layer` command emits a one-line summary of the sprint layer (beads opened, closed, still open), creating an annual-band equivalent.

Estimated savings: Usability reduction — "find that bead from the authz sprint" currently requires `bd search` with trial-and-error keywords. Sprint layer indexing reduces this to `bd list --sprint authz-v2`. Estimated: 2-3 repeated `bd search` invocations eliminated per session = 1 LLM turn saved.

Difficulty: S (single PR: add sprint-layer record to Dolt schema, update `bd search` and `bd ready` to accept `--sprint` filter)

Risk: Sprint boundaries may not be consistently marked (the user may not always run `clavain:land`). Mitigation: fall back to date-range grouping when sprint markers are absent. The feature degrades gracefully.

---

**FIRN-4. P2: Handoff docs carry no trapped-air signature — the project state at the time of writing is not recoverable**

Axis: usability (specifically: session continuity, handoff doc fidelity)

Source-domain mechanism: **Trapped-air signature**. When firn closes off at ~80m, the air bubbles sealed inside carry the exact atmospheric composition at that moment: CO₂ concentration, CH₄, δ¹⁸O (temperature proxy), and dust load. A glaciologist reading a 15,000-year-old ice core can reconstruct not just what the climate was, but what was actively changing (CO₂ rising vs stable, dust events). The trapped-air signature is context-at-deposition.

Current state: Handoff docs in `docs/handoffs/` (e.g., `2026-04-27-clavain-peer-coexistence-wave3.md`) describe the directive and dead ends. They do not carry the "atmospheric composition at deposition": the set of active beads at the time, the current model routing config, the exact MEMORY.md state, or the open questions that were in flight. A reader of the handoff must reconstruct context from git history, bead state, and memory — a lossy process.

Concrete failure scenario: A new session reads `2026-04-27-doc-monitoring-l1-shipped.md`. The doc says "shipped." But at the time of writing, there were 3 open follow-up beads for this work. The new session does not know those beads exist, starts fresh, and either duplicates work or misses the follow-up entirely. This is the "no trapped-air" failure: the doc sealed without capturing the active bead set.

Proposal: Add a **trapped-air block** to handoff doc template (`clavain:handoff`):
```yaml
# trapped-air-signature: context at close-off
active_beads: [sylveste-abc1, sylveste-def2]  # bd orphans output at time of write
open_questions: [...]
memory_version: sha256:<MEMORY.md hash at write time>
routing_config: <hash of config/routing.yaml>
```
This block is written automatically by `clavain:handoff` and is machine-readable. A session-start hook can diff `memory_version` against current MEMORY.md hash and warn: "MEMORY.md has diverged 18 lines since last handoff — consider reading handoff for context."

Estimated savings: Eliminates 1-2 exploratory tool calls per session to reconstruct handoff context. Estimated: 500-800 tok/session on context reconstruction.

Difficulty: S (single PR: update `clavain:handoff` to append trapped-air block, add session-start hook diff check)

Risk: Trapped-air block must be kept small (< 10 lines) or it bloats the handoff doc. The bead list is especially risky if a sprint has 30 open beads — use `bd orphans` (unlinked beads only) rather than `bd list --open`.

---

**FIRN-5. P3: Hiatus unconformity is not detected — stale project lanes accumulate in MEMORY.md's Active Projects section without expiry**

Axis: token-efficiency (and usability)

Source-domain mechanism: **Hiatus / unconformity**. In glaciology, a hiatus is a period with no deposition — visible in a core as a sharp boundary between layers with no transitional material. An unconformity is a stratigraphic gap. The key insight: the absence of a layer is itself data. When a glaciologist finds a hiatus at a known depth, they know something interrupted deposition — a volcanic winter, an ice-free period, a melt event. The gap is diagnostic.

Current state: MEMORY.md `Active Projects` section lists 14 active projects. Several of these (`project_meadowsyn.md`, `project_zakalwe.md`, `project_ockham.md`) may not have had active bead commits in the last several sprints. The system has no way to detect this — the entries remain "active" in MEMORY.md indefinitely. A session loading MEMORY.md reads all 14 entries regardless of whether the project had any activity in the last 90 days.

Proposal: Implement **hiatus detection as an unconformity signal**:
- Weekly (or per-session): check `bd list --project <name>` for each Active Projects entry. If no bead activity in 21 days, emit a `hiatus-signal` record.
- After two consecutive hiatus signals (42 days), move the project from `Active Projects` to a new `Hibernating` section in MEMORY.md.
- `Hibernating` entries are not loaded in the standard session preamble — they are loaded only when the project name appears in the user's input.
- The hiatus is itself recorded: "project_meadowsyn: no activity since 2026-04-12 (21 days)" — this is diagnostic context for future sessions.

Estimated savings: If 4/14 Active Projects entries are hibernating (280 tok each), removing them from active context: ~1,120 tok/session. Plus usability: agents stop suggesting meadowsyn options during Ockham sessions.

Difficulty: XS (config/script: add a weekly cron or SessionStart hook that runs hiatus detection via `bd list` per active project and updates MEMORY.md tiering)

Risk: A project that is genuinely active but has no bead-trackable work (pure brainstorm phase) would incorrectly trigger hiatus. Mitigation: also check for handoff doc recency and CLAUDE.md mentions in recent commits.

--- VERDICT ---
STATUS: warn
FILES: 0
FINDINGS: 5 (P0: 0, P1: 2, P2: 2, P3: 1)
SUMMARY: MEMORY.md has exceeded close-off depth — archival content mixed with active context costs ~1,400 tok/session on every load. Firn's layer-vs-edit-in-place model prescribes append-only deposition headers per entry and depth-tiered archiving via intermem:tidy.
---
<!-- flux-drive:complete -->
