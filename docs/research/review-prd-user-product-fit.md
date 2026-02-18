# User & Product Review: intermem Phase 2 — Decay + Progressive Disclosure

**Reviewed:** 2026-02-18
**Reviewer:** Flux-drive (User & Product Reviewer)
**PRD:** `/root/projects/Interverse/docs/prds/2026-02-18-intermem-phase2-decay-progressive-disclosure.md`

---

## Executive Summary

**Primary User:** AI agents (Claude Code, future multi-agent systems) reading curated project documentation during session initialization and on-demand file access.

**Job to Complete:** Access relevant project knowledge fast enough to act on it, without paying token costs for stale or irrelevant context.

**Verdict:** The PRD bundles 5 features across 2 major UX shifts (decay + tiered structure) with unclear discovery UX, an invalid success metric, CLI complexity creep, and under-specified migration experience. This should be split into 2 phases. High risk of shipping structure changes that agents never use because discovery mechanisms aren't proven.

**Recommendation:** Split into Phase 2A (decay + archive) and Phase 2B (progressive disclosure). Validate that agents actually read `docs/intermem/` files before committing to tiered migration.

---

## 1. Decision Gate Validity — INVALID PROXY METRIC

### Problem Statement
**Gate:** ">50% bloat reduction" measured as AGENTS.md token count decrease after tiered migration.

**Critical flaw:** This measures **file size**, not **agent performance**. Smaller AGENTS.md only improves performance if:
1. Agents read AGENTS.md at session start (true)
2. Agents don't then read all the `docs/intermem/*.md` files anyway (unproven)
3. The index is sufficient for most tasks without drilling down (untested)

**What the gate should measure:**
- **Context utilization rate:** % of sessions where agent reads AGENTS.md but NOT detail files
- **Time-to-value:** Does the thin index enable agents to start work without delay?
- **Discovery success rate:** When an agent needs detail, do they find the right file?

**Evidence gap:** No user research on how agents currently navigate documentation. Do they:
- Read full AGENTS.md and absorb all content?
- Search for specific sections and skip the rest?
- Re-read on every context window refresh?

**Suggested revision:**
Replace ">50% bloat reduction" with:
- **Primary:** Agent reads detail files in <30% of sessions over a 2-week period
- **Secondary:** AGENTS.md token count decreases >50%
- **Tertiary:** No increase in "I couldn't find X" user corrections

---

## 2. Progressive Disclosure UX — DISCOVERY MECHANISM UNPROVEN

### Claimed Flow
1. Agent loads thin AGENTS.md index at session start (~50-150 tokens)
2. Agent sees section pointers like `See docs/intermem/git-workflow.md`
3. Agent uses Read tool on-demand when context requires detail

### Missing Pieces

**Trigger mechanism:** What causes an agent to drill down vs stay at index level?

The PRD assumes agents will:
- Recognize when they need more detail (true for humans, unproven for LLMs)
- Remember the index structure when context window refreshes (unlikely without re-reading)
- Correctly map task context to section slug (requires consistent naming)

**Discovery affordances:** How does an agent know what's in each detail file before reading it?

Current design:
- One-liner summary (first sentence, ~120 chars)
- Section name

Missing:
- Confidence/recency signals ("Last updated 3 days ago")
- Scope hints ("5 entries, 200 tokens")
- Keyword tags for search-ability

**Alternative hypothesis:** Agents will read AGENTS.md, see pointers, Read all detail files anyway "just in case," defeating the entire purpose.

**Test needed before shipping tiered structure:**
Create a mock tiered AGENTS.md in a test project, run 10 agent sessions, measure:
- How many detail files are read per session
- Whether agents re-read index on context refresh
- Whether agents cite detail file content or index-only content in their work

---

## 3. CLI Ergonomics — COMPLEXITY CREEP

### Current Flags (Phase 1)
- `--project-root <path>` (defaults to cwd)
- No other flags (validation runs implicitly)

### Phase 2 Adds 7 New Flags

| Flag | Mode | Purpose |
|------|------|---------|
| `--sweep` | Standalone | Trigger full re-validation + decay pass |
| `--show-archived` | Query | List archived entries |
| `--search <keywords>` | Query | Search memory entries |
| `--list-topics` | Query | Show sections with counts |
| `--no-tiered` | Modifier | Disable progressive disclosure |
| `--migrate-to-tiered` | Standalone | One-shot migration |
| `--dry-run` | Modifier | Preview migration without writing |
| `--json` | Modifier | Structured output (future) |

**Discoverability problems:**

1. **Hidden modes:** 3 standalone operations (`--sweep`, `--migrate-to-tiered`, query flags) with no top-level `intermem <command>` structure
2. **Modifier scatter:** `--dry-run` only applies to `--migrate-to-tiered`, not obvious from `--help`
3. **Query UX split:** `--search`, `--list-topics`, `--show-archived` are 3 separate flags instead of `intermem query --type=search|topics|archived`

**Better structure:**

```bash
intermem validate [--project-root]           # Current behavior (default)
intermem sweep [--project-root]              # F1 decay pass
intermem query [--search|--topics|--archived] [--json]  # F5 queries
intermem migrate [--dry-run] [--project-root]  # F4 tiered migration
```

**Help text test:** Without reading the PRD, can a user discover:
- That `--sweep` should be run periodically (how often? by whom?)
- That `--migrate-to-tiered` is one-shot and irreversible (is it?)
- That `--no-tiered` must be set before first promotion to avoid migration later

**Current PRD has zero help text examples.** High risk of "how do I..." support questions.

---

## 4. Archive Visibility — "WHERE DID MY MEMORY GO?" RISK

### Archive Mechanism
- Promoted entry confidence drops <0.3 during sweep
- Entry removed from target doc (e.g., AGENTS.md or `docs/intermem/git-workflow.md`)
- Entry appended to `docs/intermem/.archived.md` with metadata

### Discovery Problem: Entry Disappears from Index

**User (human) scenario:**
1. Week 1: Entry promoted to AGENTS.md
2. Week 2-4: Entry not re-observed (user working in different area)
3. Week 5: `intermem sweep` runs, archives the entry
4. Week 6: User searches AGENTS.md for the entry, can't find it
5. User doesn't know `.archived.md` exists or how to search it

**Agent scenario:**
1. Agent reads AGENTS.md index, doesn't see entry
2. Agent doesn't know to check `.archived.md` (no pointer in index)
3. Agent re-learns the same lesson, creates duplicate stability entry
4. Duplicate promoted, original still archived → knowledge fragmentation

### Missing UX Layers

**Discovery affordances:**
- AGENTS.md should have a footer: `## Archived Entries\nSee docs/intermem/.archived.md for entries no longer actively used.`
- Tiered detail files should note when entries move to archive
- Archive file should have metadata table at top (not just appended entries)

**Recovery confirmation:**
When an archived entry is restored, how does the user know it happened?
- No notification mechanism specified
- Journal records state change but no human-facing output
- User might wonder why the same entry keeps appearing/disappearing

**Reversibility:**
Can a user manually restore an entry from archive? PRD only specifies automatic restore when confidence recovers. What if the decay threshold is wrong?

---

## 5. Migration Experience — UNDER-SPECIFIED ONE-SHOT OPERATION

### Claimed Behavior
`--migrate-to-tiered` splits flat AGENTS.md into tiered structure.

**Acceptance criteria:**
- Scans for `<!-- intermem -->` markers
- Creates detail files
- Rewrites AGENTS.md as index

### Missing Specifications

**Preview mechanism:**
- `--dry-run` shows "what would change" but format not specified
- Does it show file diffs? File list? Token count comparison?
- Can user inspect proposed detail files before committing?

**Failure modes:**
- What if AGENTS.md has no `<!-- intermem -->` markers? (Error? No-op?)
- What if markers are malformed or out of sync with metadata.db?
- What if `docs/intermem/` already exists with conflicting content?

**Rollback plan:**
- PRD says "Idempotent: running twice produces same result" but not "reversible"
- If user wants to go back to flat structure, do they:
  - Delete `docs/intermem/`?
  - Re-run promotion with `--no-tiered`?
  - Manually copy content back to AGENTS.md?
- What happens to metadata.db `promoted_to_file` column?

**Confirmation UX:**
Should a destructive one-shot operation require explicit confirmation?
```bash
intermem migrate --dry-run  # Preview
# ... user reviews ...
intermem migrate --confirm  # Actual run
```

**State tracking:**
After migration, how does intermem remember the project is now in tiered mode?
- `.intermem-config.json` file?
- Marker in metadata.db?
- Presence of `docs/intermem/` directory?

If none, then `--no-tiered` flag must be passed on every future invocation to prevent re-tiering. That's a UX trap.

---

## 6. Scope Creep — 5 FEATURES, 2 ARCHITECTURES, 800 LINES

### Feature Count
1. F1: Time-based decay
2. F2: Auto-archive + restore
3. F3: Multi-file tiered promotion
4. F4: Tiered migration
5. F5: CLI query interface

### Two Major UX Shifts in One Iteration

**Shift 1: Content lifecycle (F1 + F2)**
- Adds temporal dimension to memory entries
- Introduces new archive file and states
- Changes promotion stability assumptions

**Shift 2: Information architecture (F3 + F4)**
- Complete restructure of how knowledge is organized
- Changes how agents discover and consume docs
- Migrates existing projects to new structure

**These are independent changes** that could ship separately:
- Phase 2A: Decay + archive (addresses stated problem: "stale entries not removed")
- Phase 2B: Progressive disclosure (new capability: "reduce per-session token cost")

### Risk of Bundling

**Validation burden:**
- If tiered structure doesn't work, was it the index design, the slugs, the one-liners, or the discovery UX?
- If decay is too aggressive, is it threshold (0.3), penalty (-0.1/14d), or detection (last_seen logic)?
- 5 features × unknown interactions = hard to debug

**User adoption:**
- Migration is optional (`--no-tiered` preserves Phase 1 behavior)
- If optional, will anyone migrate? If not, why build F3 + F4?
- If mandatory (or strongly recommended), are users forced to adopt unproven structure?

**Effort realism:**
800 new lines + 25-35 new tests is optimistic for 5 features with 2 new modules and schema migration.

---

## 7. User Impact Assessment

### Value Proposition Clarity

**Stated benefit:** "Reduce per-session token cost by removing stale entries and deferring detail loading."

**Who benefits:**
- **Agents:** Smaller AGENTS.md = faster session start (if index-only is sufficient)
- **Humans:** Easier to scan AGENTS.md (if tiered index is more readable)
- **Both:** Automatic archival prevents manual pruning

**Benefit timing:**
- Decay: Delayed (only after 14-28 days of non-observation)
- Tiered: Immediate (but requires migration, adds discovery friction)

**Failure modes:**
- Agent reads all detail files anyway → no token savings, extra Read tool calls
- Archive removes entry user needed → confusion, re-learning, duplicate promotion
- Migration breaks custom AGENTS.md formatting → user has to manually fix

### Segmentation

**New users:** Phase 2 is invisible (no entries to decay, no AGENTS.md to migrate). Benefit: starts with clean tiered structure.

**Existing users (post-Phase 1):** Must decide whether to migrate. Benefit: token reduction (if tiered works). Cost: migration risk, learning new structure.

**Power users:** May have heavily customized AGENTS.md with non-intermem content. Risk: migration mangles custom sections.

### Discoverability Barriers

**How does a user learn about:**
- `--sweep` (periodic maintenance)?
- `--migrate-to-tiered` (one-shot upgrade)?
- `.archived.md` (when entries vanish)?

**Current discovery paths:**
1. Read intermem AGENTS.md (not mentioned in PRD)
2. Run `intermem --help` (not shown in PRD)
3. Notice entries missing, investigate (reactive, not proactive)

**Missing onboarding:**
- Should migration be suggested after Phase 1 usage (e.g., "AGENTS.md is 1000 tokens, consider --migrate-to-tiered")?
- Should first sweep print archived count and suggest `--show-archived`?

---

## 8. Flow Analysis

### Happy Paths

**Path 1: Decay lifecycle (no tiering)**
1. Entry promoted to AGENTS.md (Phase 1)
2. 28 days pass, no re-observation
3. User runs `intermem sweep`
4. Entry archived to `docs/intermem/.archived.md`
5. Entry re-appears in auto-memory (user returns to that workflow)
6. Next sweep restores entry to AGENTS.md

**Path 2: Tiered migration + usage**
1. User runs `intermem migrate --dry-run`, reviews output
2. User runs `intermem migrate`, AGENTS.md becomes thin index
3. Agent session starts, reads AGENTS.md index
4. Agent sees `See docs/intermem/git-workflow.md`, uses Read tool
5. Agent uses detail, completes task

### Error Paths

**E1: Sweep never runs**
- Decay mechanism is manual (`--sweep` flag)
- If user forgets, entries never archive
- Stale entry problem persists
- **Missing:** Automatic sweep trigger (hook? cron? session end?)

**E2: Archive removes needed entry**
1. Entry archived after 28 days
2. User returns to workflow, expects entry in AGENTS.md
3. Entry missing, agent re-learns lesson
4. Duplicate stability entry created
5. Duplicate promoted, original still archived
6. **Recovery:** Next sweep restores original (but duplicate now exists)

**E3: Migration with custom AGENTS.md**
1. User has hand-written sections in AGENTS.md
2. User runs `intermem migrate`
3. Non-intermem content preserved (per acceptance criteria)
4. But section headers might collide (e.g., user has `## Git Workflow`, intermem wants to add `## Git Workflow` index)
5. **Missing:** Collision detection and user prompt

**E4: Agent doesn't drill down**
1. Agent reads thin AGENTS.md index
2. Task requires detail from `docs/intermem/testing.md`
3. Agent doesn't recognize need, attempts task with index-only info
4. Task fails or produces low-quality output
5. User corrects agent, agent then reads detail file
6. **Missing:** Feedback loop to track when index was insufficient

### Edge Cases

**Section slug collision:**
- "Git Workflow" → `git-workflow.md`
- "Git Workflows" → `git-workflows.md` (OK)
- "Git workflow" → `git-workflow.md` (collision, needs counter)
- PRD mentions counter suffix but not format (`git-workflow-2.md`?)

**Archive file growth:**
If 100 entries archive over time, `.archived.md` becomes huge.
- Does it need rotation or pruning?
- Should truly dead entries (archived >6 months, never restored) be deleted?

**Metadata.db divergence:**
- Entry archived from AGENTS.md
- User manually edits `.archived.md` to restore
- metadata.db still says `archived_at = <timestamp>`
- Next sweep doesn't know entry was manually restored
- **Missing:** Validation that doc state matches metadata.db state

**Cross-section references:**
If Git Workflow entry references Testing section, and both are tiered:
- Index shows `See docs/intermem/git-workflow.md`
- Detail file shows `See ## Testing` (relative link)
- **Missing:** Link rewriting to point to `docs/intermem/testing.md`

---

## 9. Evidence Standards Assessment

### Data-Backed Claims
- ✅ "Phase 1 prevents new stale entries" (implied from Phase 1 completion)
- ✅ "119 tests pass" (existing test suite)

### Assumption-Based Claims
- ❌ "Agents load only the index at session start; deeper context available on demand" (unproven agent behavior)
- ❌ ">50% token reduction" (depends on index-to-detail ratio, not measured)
- ❌ "First sentence is sufficient for index summary" (not tested for comprehension)
- ❌ "14-day penalty period is appropriate" (arbitrary threshold, no tuning data)

### Unresolved Questions That Could Invalidate Direction

**Q1: Do agents actually defer detail file reads?**
If agents read all detail files anyway (defensive behavior), tiered structure adds no value and increases complexity.

**Q2: Is 0.3 the right stale threshold?**
PRD shows calculation (base 0.5 - 0.2 = 0.3) but no justification for why 0.3 is "stale enough to archive but recoverable."

**Q3: Should sweep be automatic?**
Manual `--sweep` flag means decay only happens when user remembers to run it. If this is meant to be invisible maintenance, why manual?

---

## 10. Recommendations

### Immediate Changes to PRD

**1. Replace success metric**
- Remove ">50% bloat reduction" as primary gate
- Add "Agent reads detail files in <30% of sessions" as primary
- Add token reduction as secondary

**2. Specify discovery UX**
- Add archive footer to AGENTS.md
- Add scope hints to index one-liners (token count, entry count)
- Specify help text for all CLI flags

**3. Detail migration experience**
- Add confirmation prompt for `--migrate-to-tiered`
- Specify `--dry-run` output format (diffs? file list?)
- Add rollback procedure

**4. Split into 2 phases**

**Phase 2A: Decay + Archive (ships first)**
- F1: Time-based confidence decay
- F2: Auto-archive + restore
- F5: CLI query interface (search, topics, archived)
- Success: 1+ entry archived in Interverse, restore works

**Phase 2B: Progressive Disclosure (ships after validation)**
- Prototype tiered index in 1 test project
- Measure agent detail-file read rate over 10 sessions
- If <30% read rate, proceed to F3 + F4
- If >70% read rate, abandon tiering or redesign trigger mechanism

### Open Questions to Resolve Before Starting

1. **Automatic sweep:** Should decay run on session end, or stay manual?
2. **Index sufficiency:** What % of tasks can be completed with index-only context?
3. **Archive retention:** Should archived entries ever be deleted (e.g., after 6 months)?
4. **Tiered config:** How does a project remember it's in tiered mode?

### Risk Mitigation

**High risk: Tiered structure unused**
- **Mitigation:** Ship decay first, validate tiering in isolation
- **Fallback:** If agents don't use tiering, at least decay reduces AGENTS.md size

**Medium risk: Archive visibility**
- **Mitigation:** Add explicit archive pointer to AGENTS.md footer
- **Fallback:** `--show-archived` flag makes recovery discoverable

**Medium risk: Migration breaks custom docs**
- **Mitigation:** Collision detection, confirmation prompt, dry-run preview
- **Fallback:** `--no-tiered` preserves Phase 1 behavior

---

## Conclusion

**Primary user:** AI agents reading curated docs.

**Job to complete:** Access relevant knowledge without paying token cost for stale/irrelevant context.

**Current PRD fitness:** 4/10
- ✅ Addresses real problem (unbounded AGENTS.md growth)
- ✅ Decay mechanism is sound (time + recapture)
- ❌ Success metric measures wrong thing (file size, not agent behavior)
- ❌ Progressive disclosure UX unproven (no evidence agents will defer detail reads)
- ❌ CLI complexity creep (7 new flags, 3 operation modes, hidden in flat structure)
- ❌ Migration experience under-specified (no preview format, rollback, or confirmation)
- ❌ Archive visibility gap (entries vanish, user doesn't know where to look)
- ❌ Scope too large (5 features, 2 UX shifts, 800 lines in one iteration)

**Recommended path forward:**
1. Split into Phase 2A (decay) and 2B (tiering)
2. Ship 2A first with query CLI and archive footer
3. Validate tiering hypothesis with prototype + agent session measurement
4. Only proceed to 2B if agents demonstrate <30% detail-file read rate
5. Redesign CLI as subcommands (`intermem sweep`, `intermem query`, `intermem migrate`)
6. Add migration preview, confirmation, and rollback docs

**Why this matters:**
If agents read all detail files anyway, tiering adds complexity without benefit. Decay is valuable on its own. Don't bundle unproven architecture changes with solid lifecycle improvements.
