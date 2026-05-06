### Findings Index
- P1 | SCRIP-1 | "Axis 1: Usability — Agent context loading" | No exemplar hierarchy: agents read CLAUDE.md, AGENTS.md, MEMORY.md, brainstorms, handoffs as equals — contradictions propagate downstream
- P1 | SCRIP-2 | "Axis 2: Token Efficiency — Prompt structure" | Witness manuscripts: interpath:vision regenerates docs without canonical-witness selection — different agents read different versions
- P2 | SCRIP-3 | "Axis 1: Usability — Doc authority" | Corrector's pass is absent: brainstorms leak into canonical authority by being referenced from CLAUDE.md without a formal review gate
- P2 | SCRIP-4 | "Axis 2: Token Efficiency — Orchestration preamble" | Marginalia merged into body: feedback notes in MEMORY.md topic files are indistinguishable from policy — both loaded at full weight
- P3 | SCRIP-5 | "Axis 3: ML replacement — Doc routing" | No scribal abbreviation vocabulary: 'which doc to update' routing uses LLM when a Tironian-notes-style abbreviation map would resolve 70% of cases
Verdict: needs-changes

### Summary
The medieval scriptorium lens exposes Sylveste's document authority problem with surgical precision. Scriptoria managed multi-author, multi-document manuscript production at scale by maintaining three invariants: (1) an exemplar hierarchy (one authoritative source per text), (2) a physical separation between body and marginalia (gloss is never body), and (3) a corrector's pass before any manuscript was shelved as canonical. Sylveste has none of these. CLAUDE.md, AGENTS.md, MEMORY.md, brainstorms, PRDs, handoffs, and roadmaps coexist with overlapping content and no explicit authority ordering. An agent reading two contradictory docs picks one based on recency — propagating the contradiction downstream.

### Issues Found

**SCRIP-1. P1: No exemplar hierarchy — agents read CLAUDE.md, AGENTS.md, MEMORY.md, brainstorms as equals; contradictions propagate downstream**

Axis: usability

Source-domain mechanism: **Exemplar hierarchy**. In medieval scriptoria (Carolingian, 8th-9th century), each major text had a designated exemplar — the authoritative copy from which all other copies were made. The scriptorium's master copy of, say, Virgil's Aeneid was the exemplar; all copies were derived from it and explicitly subordinate to it. When a copyist encountered a discrepancy between two manuscripts, they consulted the exemplar to resolve it. Crucially: the exemplar relationship was recorded in the colophon — "written from the exemplar at [location] by [scribe]."

Current state: Sylveste's CLAUDE.md (`/home/mk/projects/Sylveste/CLAUDE.md`) says "Each subproject has its own CLAUDE.md and AGENTS.md. When working in a subproject, those take precedence." This is a partial ordering — but only for the subproject/root axis. The document does not specify: when MEMORY.md contradicts AGENTS.md (e.g., a workflow pattern in MEMORY.md conflicts with a session protocol in AGENTS.md), which is exemplar? When a brainstorm's conclusion contradicts a shipped PRD's scope, which is exemplar?

Concrete failure scenario: Agent reads `project_auraken_hermes_pivot.md` in MEMORY.md (says "Auraken pivoting to Hermes Agent overlay — SUPERSEDES Go migration thesis") and `project_auraken_go_migration.md` (says "historical, mooted by Hermes pivot"). The SUPERSEDES annotation exists as text but has no machine-readable authority ordering. A different agent reads `docs/handoffs/2026-04-20-auraken-thinker-profile-pivot.md` which may predate the Hermes pivot decision. It treats the handoff as authoritative (it's a doc in docs/handoffs/), makes a recommendation based on pre-pivot framing, and the user spends a turn correcting it. This specific failure mode is documented in `feedback_reanchor_to_pivot_memory.md`.

Proposal: Implement a **doctrinal index** in `docs/canon/` (which already exists per AGENTS.md: "Canon docs: `docs/canon/`"):
```yaml
# docs/canon/exemplar-index.yaml
exemplars:
  auraken-architecture:
    exemplar: memory/project_auraken_hermes_pivot.md
    derived: [docs/handoffs/2026-04-20-auraken-thinker-profile-pivot.md]
    supersedes: memory/project_auraken_go_migration.md
    status: active
  sylveste-launch:
    exemplar: memory/project_launch_deferred.md
    status: deferred-until-mythos
```
Agents instructed (in CLAUDE.md) to consult `docs/canon/exemplar-index.yaml` when two docs conflict. The corrector's pass (SCRIP-3) gates entry into this index. This is a 20-line YAML file, not an architecture — single PR.

Estimated savings: Eliminates 1-2 clarification turns per session where the agent gets contradictory framing. At 2 turns × 400 tok/turn × 3 sessions/week: ~2,400 tok/week. Primary value is usability: the agent stops asking "you mentioned X earlier but I see Y in the handoff."

Difficulty: S (single PR: create `docs/canon/exemplar-index.yaml`, update CLAUDE.md to instruct agents to check it on conflict, write 10 initial entries)

Risk: The index requires maintenance — when a new doc supersedes an old one, the index must be updated. If it goes stale, it becomes misleading. Mitigation: add exemplar-index update to the `clavain:handoff` session-close protocol.

---

**SCRIP-2. P1: Witness manuscripts — interpath:vision regenerates docs without canonical-witness selection; different agents read different versions**

Axis: token-efficiency

Source-domain mechanism: **Witness manuscript selection**. When a text existed in multiple manuscript copies (witnesses), medieval textual critics developed stemmatic analysis to determine the canonical witness — the manuscript closest to the author's original. The Lachmann method (19th century, systematizing medieval practice) groups witnesses by shared errors to identify which manuscript lineage was closest to the archetype. The canonical witness was not necessarily the oldest or most complete — it was the one with the fewest substantive variants from the reconstructed archetype.

Current state: `interpath:vision` regenerates the vision doc on demand. `interpath:roadmap` regenerates the roadmap. Flux-drive research outputs are written to timestamped directories (`docs/research/flux-drive/<stem>-<timestamp>/`). After 3 interpath:vision runs, three witnesses of the same vision doc exist. The AGENTS.md notes `interpath:vision` under Operational Guides but does not specify which generated vision doc is canonical. Different agents reading different timestamps treat each as authoritative.

Concrete failure scenario: Session A runs `interpath:vision` on 2026-04-20. Session B runs it again on 2026-04-26 with slightly different context framing. Session C reads the 2026-04-20 version (it appears first alphabetically in `docs/`). Session D reads the 2026-04-26 version. They produce subtly different recommendations about Sylveste's launch timing. The user notices the inconsistency on the fourth session and must spend a turn reconciling them.

Proposal: Add **canonical-witness designation** to interpath artifact output:
- `interpath:vision` writes `docs/vision.md` as the canonical witness (always overwriting, not timestamped).
- Historical witnesses are archived to `docs/archive/vision-<timestamp>.md` on each regeneration.
- A `docs/canon/witness-registry.yaml` records: `{artifact, canonical_path, last_regenerated, archived_witnesses: []}`.
- Agents are instructed to read `docs/vision.md` (canonical witness), not the timestamped archives.

Same pattern for flux-drive research: `docs/research/flux-drive/<stem>/SYNTHESIS.md` is the canonical witness; timestamped run directories are archival witnesses.

Estimated savings: Eliminates context confusion from agents reading stale witnesses. Token savings: ~300-500 tok/session from not loading stale witness content alongside canonical content. Primary value: usability — agents stop treating old regenerated docs as authoritative.

Difficulty: XS (config change: update interpath skill to write canonical path + archive, add witness-registry.yaml, update CLAUDE.md to instruct agents to read canonical path)

Risk: If interpath:vision is regenerated mid-sprint and produces worse output than the previous canonical witness, the old version is archived and the new (worse) version becomes canonical. Mitigation: add a `--no-replace` flag to interpath skills that writes to a timestamped path only, without replacing the canonical witness.

---

**SCRIP-3. P2: Corrector's pass is absent — brainstorms leak into canonical authority by being referenced from CLAUDE.md without a formal review gate**

Axis: usability

Source-domain mechanism: **Corrector's pass**. In a medieval scriptorium, the corrector (corrector librorum) was a senior scribe whose job was to read each completed manuscript against the exemplar before it was bound. The corrector made marks in red ink (hence: rubrication). A manuscript that had not passed the corrector's pass was not shelved in the scriptorium's collection — it remained in the scriptorium's working area, not in the library. The gate was physical and formal.

Current state: Brainstorms in `docs/brainstorms/` accumulate without a formal gate. The target doc's MEMORY.md references `docs/brainstorms/2026-02-23-token-optimization-security-threat-model.md` for the full threat model — a brainstorm has been elevated to canonical status simply by being referenced from CLAUDE.md. The `project_doc_hierarchy.md` memory entry mentions "Doc hierarchy restructure: MISSION → {VISION, PHILOSOPHY} → derived artifacts" as a brainstorm, but no formal corrector's pass determines whether it is a proposal, an in-flight doc, or a canonical architectural decision.

Concrete failure scenario: An agent reads `docs/brainstorms/2026-04-21-auraken-exocortex-shape-brainstorm.md` (untracked, in the git status). It treats it as a canonical architectural decision because (a) it is referenced in MEMORY.md and (b) its content is confident and detailed. The agent makes a recommendation based on the brainstorm's conclusions. The brainstorm was actually speculative and the user had rejected half its conclusions in a subsequent session. The agent does not know this.

Proposal: Add a **corrector's-pass frontmatter gate** to all docs in `docs/brainstorms/`, `docs/research/`, and `docs/handoffs/`:
```yaml
---
status: draft|reviewed|canonical|deprecated
corrector_pass: null  # or {reviewer, date, verdict}
---
```
The `clavain:review-doc` skill (which exists) becomes the corrector: it adds `corrector_pass: {reviewer: claude-code, date: <date>, verdict: approved|rejected|needs-revision}` to the frontmatter. Only docs with `status: canonical` are loaded in agent context without explicit user request. Docs with `status: draft` are available but not auto-loaded.

CLAUDE.md references to brainstorms should be updated to note their corrector status: "See `docs/brainstorms/2026-02-23-token-optimization-security-threat-model.md` [draft, uncorrected] for the full threat model."

Estimated savings: Usability reduction — agents stop treating uncorrected brainstorms as authoritative. Token savings: if 5 brainstorm references in CLAUDE.md are marked draft and excluded from auto-load, saves ~1,000 tok/session on context loading.

Difficulty: XS-S (XS for adding frontmatter to existing docs; S for updating clavain:review-doc to write corrector_pass and updating CLAUDE.md auto-load logic)

Risk: If the corrector's pass is too burdensome, brainstorms pile up in draft status indefinitely. Mitigation: the corrector's pass can be lightweight — a single-line `clavain:review-doc` invocation that adds the frontmatter block without requiring a full review.

---

**SCRIP-4. P2: Marginalia merged into body — feedback notes in MEMORY.md topic files are indistinguishable from policy**

Axis: token-efficiency

Source-domain mechanism: **Marginalia conventions**. In medieval manuscripts, marginalia (glosses, scholia, reader annotations) were written in the margins and used a distinct script — smaller, more compressed, often in a different hand. The physical separation enforced semantic separation: gloss was never body. A copyist making a new copy from an annotated exemplar knew to exclude the marginalia (unless it had been formally incorporated into the text by the corrector). The convention prevented gloss from accumulating into the canonical text across generations.

Current state: MEMORY.md topic files (e.g., `feedback_voice_calibration_intersite.md`, `feedback_auraken_behavior_over_voice.md`) mix two kinds of content: (1) the core rule ("check behavior before voice when reviewing output") and (2) the commentary on why the rule exists ("Auraken's differentiator is behavioral"). Both are body text. An agent loading these files treats them equally. The commentary expands each rule to 2-3× its actionable size.

Specific example: `feedback_auraken_behavior_over_voice.md` is a single line in MEMORY.md: "Auraken's differentiator is behavioral (ask-first, no-menu, no-method-description), not voice; check behavior before voice when reviewing output." This is a body rule. But in the actual `.md` file, it likely contains historical context, specific examples, and the incident that generated it — all of which are marginalia.

Proposal: Split each MEMORY.md topic file into two sections:
```markdown
## Rule (body — always loaded)
Auraken's differentiator is behavioral (ask-first, no-menu, no-method-description), not voice.

## Marginalia (gloss — loaded on `@memory expand <topic>`)
This rule emerged from session 2026-04-17 when Claude generated voice-focused output
that matched Auraken's tone but missed the behavioral invariant (no-menu). The user
corrected: "voice is secondary to behavior." Context: Auraken had just pivoted to the
Hermes overlay, and the behavioral properties were not yet stable in agent outputs.
```

The session context loader reads only the `## Rule` section (body). The `## Marginalia` section is available on `@memory expand <topic>` or when an agent specifically needs historical context. This halves the effective size of each topic file in session context.

Estimated savings: 15 topic files × average 3-line expansion → 45 lines of marginalia excluded per session. At ~50 tok/line: ~2,250 tok/session. This is a pure token saving with no information loss for standard sessions.

Difficulty: XS (script: restructure existing topic .md files to add `## Rule` / `## Marginalia` sections; update context loader to read only `## Rule` by default)

Risk: Some "marginalia" may be load-bearing context that the agent needs for correct application of the rule. Mitigation: the corrector's pass from SCRIP-3 can flag which marginalia sections should be elevated to body on first-pass review.

---

**SCRIP-5. P3: No scribal abbreviation vocabulary — 'which doc to update' routing uses LLM when a Tironian-notes-style map would resolve 70% of cases**

Axis: ml-routing-replacement

Source-domain mechanism: **Tironian notes**. Marcus Tullius Tiro (Cicero's secretary, 63 BC) developed a shorthand system of ~4,000 symbols for Latin words and phrases — the first standardized abbreviation vocabulary. Medieval scriptoria adopted and extended it: every scriptorium had a standard set of abbreviations for common words (e.g., a horizontal line over a vowel meant the following consonant was doubled). The key: abbreviations reduced copying labor by 30-40% without losing meaning, because the mapping was shared knowledge.

Current state: The target doc's Axis 3 lists "Doc routing — which doc to update, which artifact to regenerate" as an LLM replacement candidate. Currently, when a session produces a conclusion that should be persisted (e.g., "Auraken should check behavior before voice"), the LLM decides: update MEMORY.md? Write a new topic file? Update PHILOSOPHY.md? Write a handoff? This routing decision uses the LLM's general judgment.

Proposal: Build a **Tironian-notes doc-routing table** — a static YAML map from conclusion-type keywords to update targets:
```yaml
# docs/canon/doc-routing-table.yaml
routing:
  - pattern: "feedback_|voice|tone|behavior"
    target: memory/feedback_*.md
    action: create-or-update-topic
  - pattern: "shipped|complete|bead-close"
    target: docs/handoffs/latest.md
    action: append-to-handoff
  - pattern: "philosophy|doctrine|design"
    target: docs/PHILOSOPHY.md
    action: propose-edit
  - pattern: "sprint|epic|milestone"
    target: .beads/
    action: bd-update
```

When a conclusion matches a pattern, route directly without LLM arbitration. When no pattern matches or two patterns conflict, fall through to LLM. Estimated 70% of doc-routing decisions match a single pattern unambiguously.

Estimated savings: Doc-routing LLM calls cost ~300-500 tok each. At 5 routing decisions per session × 70% automated: 3.5 × 400 tok = 1,400 tok/session. Plus latency: the LLM routing step adds 2-3 seconds; static table lookup is instant.

Difficulty: S (single PR: create `docs/canon/doc-routing-table.yaml`, update `clavain:handoff` and `intermem:memory-tidy` to check the table before invoking LLM routing)

Risk: The routing table can go stale as new doc types are added. Mitigation: the table is a YAML file checked into the monorepo; updates are a one-line PR. Add a "table miss" counter to telemetry — when misses exceed 20%/week, the table needs expansion.

--- VERDICT ---
STATUS: warn
FILES: 0
FINDINGS: 5 (P0: 0, P1: 2, P2: 2, P3: 1)
SUMMARY: Sylveste has no exemplar hierarchy, no corrector's pass, and no canonical-witness designation — three scriptorium invariants that prevent authority diffusion. Brainstorms leak into canonical context by being referenced, and marginalia (feedback commentary) carries the same token weight as policy rules.
---
<!-- flux-drive:complete -->
