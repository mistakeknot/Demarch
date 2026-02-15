# User & Product Review: Clavain Boundary Restructure

**Reviewers:** Flux-drive User & Product Reviewer
**Date:** 2026-02-14
**Artifacts reviewed:**
- `/root/projects/Interverse/docs/plans/2026-02-14-clavain-boundary-restructure.md`
- `/root/projects/Interverse/docs/prds/2026-02-14-clavain-boundary-restructure.md`

## Executive Summary

This restructure removes command aliases and extracts domain-specific skills from Clavain into 4 new companion plugins. **Primary user impact: breaking changes to command invocations with no documented migration path.** The plan is technically sound but user-facing gaps could block adoption and create churn.

**Critical findings:**
1. **No migration guide** — Users typing `/clavain:lfg`, `/clavain:deep-review`, or `/clavain:agent-native-audit` will get "command not found" with no guidance
2. **Skill invocation ambiguity** — Plan doesn't specify whether moved skills change namespace (`/clavain:slack-messaging` → `/interslack:slack-messaging`?)
3. **Plugin proliferation without discoverability strategy** — Going from 13 to 17 companions, but no guidance on "which plugin has what I need"
4. **Missing opportunity for consolidation** — 4 single-skill plugins could be 1 "domain extensions" plugin with clearer value prop

**Recommendation:** Add Task 11 (migration guide), clarify skill invocation semantics, and consider bundling 3 of the 4 new plugins into a single `interextend` or `interdomain` plugin to reduce proliferation.

---

## Primary User & Job Context

**User:** Clavain power user (runs `/sprint`, `/flux-drive`, `/interpeer`, knows the companion ecosystem)
**Job to be done:** Continue using Clavain's workflow orchestration after the restructure without workflow interruption

**Evidence:** The PRD states users currently invoke:
- `/clavain:lfg` (alias for `/clavain:sprint`)
- `/clavain:deep-review` (alias for `/interflux:flux-drive`)
- `/clavain:cross-review` (alias for `/clavain:interpeer`)
- `/clavain:full-pipeline` (alias for `/clavain:sprint`)
- `/clavain:agent-native-audit` (command, moving to intercraft)

---

## User Experience Review

### CLI Command Ergonomics

**Breaking changes with zero migration guidance:**

1. **Deleted aliases** — 4 commands vanish: `/clavain:lfg`, `/clavain:full-pipeline`, `/clavain:cross-review`, `/clavain:deep-review`
   - Users who type these will get "command not found"
   - No plan to show "did you mean `/clavain:sprint`?" or similar help text
   - **Severity: High** — Breaks muscle memory with no recovery path

2. **Moved command** — `/clavain:agent-native-audit` becomes `/intercraft:agent-native-audit`
   - No mention of adding a deprecation stub that redirects with a warning
   - Users who haven't installed the new companion plugins will get "command not found"
   - **Severity: Medium** — Affects niche users, but total failure mode

3. **Skill namespace changes (unspecified)** — Plan doesn't say whether:
   - `/clavain:slack-messaging` becomes `/interslack:slack-messaging`
   - Or if skills are invoked without namespace (just `slack-messaging`)
   - Or if Clavain's skill loader finds skills in companion plugins transparently
   - **Severity: High** — Core UX question left undefined

**Recommendation:** Task 11 must include:
- Deprecation stubs for deleted commands that print "Alias removed. Use `/clavain:sprint` instead."
- Redirect stub for `agent-native-audit.md` in Clavain that prints "Moved to intercraft. Install via `/plugin install intercraft@interagency-marketplace`"
- Explicit documentation of skill invocation semantics post-move

### Discoverability & Help Experience

**Current state:** `/clavain:help` lists all 37 commands. After restructure: 32 commands.

**Gaps identified:**
1. **No "what moved where" reference** — Plan updates help.md to remove references but doesn't add a "Commands that moved" section
2. **No companion plugin discovery mechanism** — Users who type `/clavain:slack-messaging` (if it fails) have no guidance that they need to install `interslack`
3. **Plugin proliferation without index** — 17 companions total, no "which plugin has X" lookup

**Recommendation:**
- Add "Moved Commands & Skills" section to `/clavain:help` output
- Create `/clavain:companions` command that lists all companion plugins with one-line descriptions
- Or update `/clavain:setup` to print a companion plugin index

### Error Recovery & Affordances

**Failure mode: User doesn't install new companions**

If a user:
1. Upgrades Clavain (via `/plugin update clavain`)
2. Doesn't install the 4 new companions (interslack, interform, intercraft, interdev)
3. Tries to use `/clavain:slack-messaging` skill

What happens?
- Plan doesn't specify whether skills auto-load from companions or require explicit installation
- If skills fail silently, user gets "skill not found" with no actionable next step
- If skills auto-detect missing plugins, where's the prompt? "Install interslack? [y/n]"

**Recommendation:** Task 7 (update metadata) should include:
- Adding interslack, interform, intercraft, interdev to `agent-rig.json` recommended array (already planned)
- Testing failure modes: what happens when a user invokes a skill that lives in an uninstalled companion
- Documenting expected behavior in AGENTS.md

### Terminal-Specific Constraints

**No issues identified** — This is a structural refactor, not a UX surface change. Commands stay text-based, no new TUI interactions.

---

## Product Validation

### Problem Definition

**Claimed problem (from PRD):**
- Clavain's identity as "general-purpose engineering discipline" is diluted by domain-specific skills (Slack, design)
- Alias commands create multiple entry points for the same action (confusing routing)
- Boundary between hub and companions is blurred

**Evidence quality:** Assumption-based, not data-backed.
**Stated user pain:** None cited. This is architectural hygiene, not user-requested.

**Critical question:** Has a user ever said "I'm confused by Clavain's scope" or "I wish Slack integration was separate"?

**Recommendation:** This is valid technical debt cleanup but NOT a user pain point. Frame it as "architectural clarity" not "user value." If framed as user value, need evidence (support tickets, confusion signals, onboarding feedback).

### Solution Fit

**Does the solution address the problem?**

| Problem | Solution | Fit |
|---------|----------|-----|
| Domain skills dilute identity | Move 5 skills to domain plugins | ✅ Direct fit |
| Alias commands confuse routing | Remove 4 aliases | ✅ Direct fit |
| Blurred hub/companion boundary | Document boundary + move items | ✅ Direct fit |

**Alternative solutions NOT considered:**
1. **Keep aliases but mark them deprecated** — Gradual transition instead of hard break
2. **Bundle all domain skills into 1 plugin** — interslack + interform + interdev = 3 single-skill plugins (see Opportunity Cost below)
3. **Document boundary without moving code** — Ship clarity via AGENTS.md updates, defer code moves until user demand justifies

**Recommendation:** Plan is the right technical solution but needs a deprecation transition path (see Migration Strategy below).

### Scope Creep Check

**Features in scope:**
- F1: Remove alias commands ✅
- F2-F6: Move 5 skills + 1 agent + 1 command to 4 new plugins ✅
- F7: Update metadata ✅
- F8: Document boundary principles ✅

**Bundled "while we're here" work:** None detected. Scope is tight and well-defined.

### Opportunity Cost

**Creating 4 new plugins:**
- interslack (1 skill)
- interform (1 skill)
- interdev (1 skill)
- intercraft (1 skill + 1 agent + 1 command)

**Question:** Why not bundle interslack + interform + interdev into a single `interdomain` or `interextend` plugin?

**Current approach:**
- 4 separate plugins = 4 GitHub repos, 4 marketplace entries, 4 install commands, 4 plugin.json files to maintain
- User sees 17 total companions (was 13) — discoverability gets harder

**Alternative approach:**
- 1 bundled plugin `interdomain` with 3 skills (slack, design, mcp-cli) = 1 repo, 1 marketplace entry
- intercraft stays separate (agent-native cluster is substantive enough to justify standalone)
- User sees 14 total companions (was 13, +1 for interdomain)

**Trade-off:**
- Bundled: Simpler for users, single install, clearer "domain extensions" identity
- Separate: Each domain can evolve independently, users only install what they need

**Recommendation:** Consider bundled approach. Current plan optimizes for "modularity" but users pay complexity tax. Single-skill plugins feel like over-segmentation unless each has a clear independent trajectory.

### Success Metrics

**PRD states risks but no success criteria.**

**Missing:**
- How will we know this worked? (Qualitative: "boundary is clearer to contributors"? Quantitative: "plugin install count increases"?)
- What user feedback validates the change? (New users onboard faster? Existing users adapt without support requests?)

**Recommendation:** Add success signals to PRD:
- "No user confusion about command location" (measure: zero support requests about missing commands in first 2 weeks post-release)
- "Contributor PRs target correct plugin" (measure: zero misdirected PRs in first month)
- "Companion plugin adoption rate" (measure: % of Clavain users who install interslack/interform/intercraft/interdev)

---

## User Impact Assessment

### Value Proposition

**For existing Clavain users:**
- **Claimed benefit:** "Clearer Clavain identity, domain skills organized logically"
- **Actual user experience:** Commands and skills move, muscle memory breaks, 4 new plugins to discover

**For new Clavain users:**
- **Claimed benefit:** "Easier to understand what Clavain does vs what companions do"
- **Actual user experience:** No change until they read AGENTS.md. If they type `/clavain:lfg` from a tutorial, it fails.

**Value vs cost trade-off:**
**Cost:** Existing users adapt to breaking changes (aliases gone, commands moved).
**Benefit:** Architectural clarity, better separation of concerns.
**Winner:** Benefits are long-term (maintainability, contributor onboarding). Costs are immediate (user churn, support burden).

**Recommendation:** This is a "pay now, benefit later" change. Requires migration support to justify the cost.

### User Segmentation

**Impacted users:**

| Segment | Impact | Mitigation |
|---------|--------|-----------|
| **Power users** (use aliases daily) | High — `/lfg`, `/deep-review` break | Deprecation warnings, clear migration guide |
| **Sprint users** (use `/sprint` directly) | Low — primary command unchanged | None needed |
| **Domain skill users** (Slack, design) | Medium — skill namespace changes (unspecified) | Document invocation method |
| **New users** (following tutorials/docs) | High if docs reference old commands | Update all docs/examples/tutorials |
| **Casual users** (occasional Clavain use) | Low — can adapt incrementally | Help text improvements |

**Who benefits:**
- Contributors (clearer boundaries for PRs)
- Future users (Clavain's scope is more understandable)

**Who is harmed:**
- Existing power users with muscle memory
- Tutorial/blog authors whose content references deleted commands

**Recommendation:** Prioritize power user migration over new user clarity. Power users drive adoption and community.

### Time-to-Value

**Immediate payoff:** None. Users get breaking changes on day 1.
**Session-level payoff:** None. Workflow is same, just commands are renamed.
**Long-term payoff:** Clearer mental model, easier to learn companion ecosystem.

**Delayed payoff interval:** Weeks to months (as users internalize new structure).

**Recommendation:** Announce as "v1.0 breaking change" with clear migration period. Give 2-4 weeks of deprecation warnings before hard removal.

### Reversibility & Confidence

**If this fails, can users roll back?**
- Yes — users can pin to Clavain v0.6.13 (current) and not upgrade
- No migration path backwards (can't auto-reinstall deleted aliases)

**Failure modes:**
1. **Mass user confusion** — Support requests spike, users abandon Clavain
2. **Plugin proliferation backlash** — Users complain about "too many plugins to install"
3. **Tutorial rot** — Existing tutorials break, new users can't onboard

**Confidence-restoring mechanisms (missing from plan):**
- No rollback guide
- No "what if users don't install new plugins" fallback
- No A/B test or gradual rollout strategy

**Recommendation:** Add rollback section to migration guide. Consider phased rollout: deprecation warnings first, hard removal in next version.

---

## Flow Analysis

### End-to-End User Flows

**Flow 1: Power user runs `/clavain:lfg` (muscle memory)**

| Step | Current behavior | Post-restructure behavior (no migration) | Post-restructure behavior (with migration) |
|------|------------------|------------------------------------------|-------------------------------------------|
| 1. User types `/clavain:lfg` | Command loads | "Command not found" | "Alias removed. Use `/clavain:sprint` instead." |
| 2. Claude loads skill | `using-clavain` routes to sprint | N/A | `using-clavain` routes to sprint |
| 3. Sprint executes | Normal | N/A | Normal |

**Missing transition:** Deprecation stub in step 1.

**Flow 2: User runs `/clavain:agent-native-audit`**

| Step | Current behavior | Post-restructure behavior (no companion) | Post-restructure behavior (with companion) |
|------|------------------|------------------------------------------|-------------------------------------------|
| 1. User types command | Command loads | "Command not found" | "Install intercraft first" (if smart) or works if installed |
| 2. Command reads references | Loads from `skills/agent-native-architecture/references/` | N/A | Loads from intercraft plugin root |
| 3. Audit report generated | Normal | N/A | Normal |

**Missing paths:**
- What happens if user types command but intercraft isn't installed?
- Does Clavain show "Install intercraft@interagency-marketplace"?
- Or silent failure?

**Flow 3: User invokes `/clavain:slack-messaging` skill**

| Current | Post-restructure |
|---------|------------------|
| `/clavain:slack-messaging` (?) | `/interslack:slack-messaging` (?) or just `slack-messaging` (?) |

**Undefined:** Plan doesn't specify skill invocation semantics.

**Missing flows:**
- Skill invocation via `/skill` command vs inline reference
- How companion plugin skills are discovered by Clavain's routing

### Happy Paths, Error Paths, Recovery

**Happy path:** User upgrades Clavain, installs 4 new companions via rig installer, adapts to new command names.

**Error path 1: User doesn't install new companions**
- Outcome: Skills fail to load
- Recovery: (Unspecified — no error message guidance in plan)

**Error path 2: User types deleted alias**
- Outcome: "Command not found"
- Recovery: (Unspecified — no deprecation stub)

**Error path 3: User follows old tutorial**
- Outcome: Commands fail, user confused
- Recovery: (Unspecified — no tutorial update plan)

**Recommendation:** Add error recovery paths to Task 7 (metadata update) or new Task 11 (migration).

### Edge Cases

**Edge case 1: User has Clavain v0.6.13, companion v0.1.0**
- intercraft expects agent-native-architecture cluster in its own repo
- But Clavain still has it
- Conflict? Duplication?

**Edge case 2: User installs intercraft but not Clavain**
- intercraft is "companion plugin" but has standalone command
- Does it work independently?

**Edge case 3: User upgrades Clavain but marketplace lags**
- Clavain v0.7.0 removes skills
- Marketplace still lists old companion versions
- User can't find interslack because it's not published yet

**Recommendation:** Task 8 (marketplace) and Task 9 (git init) should happen BEFORE Clavain v0.7.0 ships. Otherwise users are in a broken state.

---

## Evidence Standards

**Data-backed findings:** None. This review is based on plan inspection, not user research.

**Assumption-based reasoning:**
- "Users will be confused by deleted commands" — Assumption, not observed
- "Power users use aliases daily" — Plausible but not measured
- "17 plugins is too many" — Subjective threshold, not validated

**Unresolved questions that could invalidate direction:**
1. **Do users actually use the aliases?** If `/lfg` is rarely invoked, removing it is low-risk. If it's muscle memory for 50% of users, high-risk.
2. **Will users install 4 new plugins?** If rig installer handles it transparently, fine. If users must manually install, adoption may stall.
3. **Is plugin proliferation a real UX problem?** 13 vs 17 companions — does this cross a cognitive threshold where users feel overwhelmed?

**Recommendation:** Before implementation, check:
- `/plugin usage` or tool-time data: how often are aliases invoked?
- User onboarding logs: do new users install companions or just Clavain standalone?
- Survey: "17 plugins feels like: (a) too many (b) manageable (c) fine"

---

## Focus Areas (Prioritized by User Impact)

### 1. Migration Guidance (Critical — Blocks User Success)

**Issue:** No documented migration path for users upgrading from v0.6.x to v0.7.0.

**User outcome impact:** Users type familiar commands, get "not found," abandon workflow.

**Recommendation:**
- Add Task 11: Create MIGRATION.md with:
  - Command mapping table (old → new)
  - Skill namespace changes
  - Companion install instructions
  - Rollback procedure (pin to v0.6.13)
- Update Clavain README with "Upgrading to v0.7.0" section
- Post to Clavain community (if exists) with heads-up 2 weeks before release

### 2. Skill Invocation Semantics (Critical — UX Undefined)

**Issue:** Plan doesn't specify whether moved skills change invocation method.

**User outcome impact:** Users don't know how to invoke skills post-move.

**Recommendation:**
- Document in Task 7 or Task 11:
  - "Skills in companion plugins are invoked via namespace: `/interslack:slack-messaging`"
  - Or: "Skills are auto-discovered across all installed plugins, invoke as `slack-messaging`"
  - Or: "Clavain's routing table includes companion skills transparently"
- Add examples to each new plugin's README

### 3. Error Messages & Recovery (High — Adoption Risk)

**Issue:** Plan doesn't specify what users see when they invoke deleted/moved commands.

**User outcome impact:** Silent failures or cryptic errors create support burden.

**Recommendation:**
- Add deprecation stubs for deleted aliases (print helpful message, don't fail silently)
- Add redirect stub for agent-native-audit (detect missing intercraft, print install command)
- Test failure modes: what happens when user invokes skill from uninstalled companion

### 4. Plugin Proliferation (Medium — Discovery Risk)

**Issue:** 4 new plugins (13 → 17 companions) without improved discovery.

**User outcome impact:** Users don't know which plugin has what they need.

**Recommendation:**
- Short-term: Update `/clavain:help` or `/clavain:setup` with companion index
- Long-term: Consider consolidating interslack + interform + interdev into single `interdomain` plugin (see Opportunity Cost above)
- Add "See also: interslack for Slack integration" to Clavain README where relevant

---

## Design Decision Recommendations

### Decision 1: Deprecation vs Hard Removal

**Options:**
- A. Remove aliases immediately (current plan)
- B. Keep aliases, add deprecation warnings for 1 version, remove in v0.8.0
- C. Keep aliases indefinitely, mark as "legacy"

**User outcome:**
- A: Breaking change, users must adapt now
- B: Gradual transition, users warned before break
- C: No break, but aliases clutter help output forever

**Recommendation:** Option B. Add deprecation warnings in v0.7.0, remove in v0.8.0. Gives users time to adapt.

**Implementation:** Alias commands print: "⚠️ `/lfg` is deprecated. Use `/sprint` instead. This alias will be removed in v0.8.0."

### Decision 2: Bundle vs Separate Plugins

**Options:**
- A. 4 separate plugins (current plan)
- B. Bundle interslack + interform + interdev into `interdomain`, keep intercraft separate
- C. Bundle all 4 into `interextend`

**User outcome:**
- A: Maximum modularity, 17 total companions
- B: Reduced install burden (14 companions), clearer "domain extensions" identity
- C: Single install, but intercraft cluster doesn't fit thematically

**Recommendation:** Option B. Bundle minimal domain skills, keep substantive intercraft standalone.

**Value prop:**
- `interdomain`: "Domain-specific extensions — Slack, design, dev tools"
- `intercraft`: "Agent-native architecture — review, audit, patterns"

### Decision 3: Migration Timeline

**Options:**
- A. Ship v0.7.0 immediately (breaking changes)
- B. Ship v0.7.0 with deprecation warnings, v0.8.0 with removals (2-version transition)
- C. Ship v0.7.0-beta, gather feedback, iterate

**User outcome:**
- A: Fast iteration, high churn risk
- B: Smooth transition, longer timeline
- C: Community validation, delayed ship

**Recommendation:** Option B if shipping to community. Option A if this is single-user (you).

**Evidence needed:** Is Clavain installed by others? If yes → B. If no → A.

---

## Final Recommendation

**Ship this restructure** — it's technically sound and improves maintainability. But add:

1. **Task 11: Migration guide** (MIGRATION.md + deprecation stubs)
2. **Clarify skill invocation semantics** (namespace or auto-discovery?)
3. **Test error recovery flows** (missing companion, deleted command)
4. **Consider plugin bundling** (interdomain = slack + design + mcp-cli)
5. **Add success metrics** (zero support requests, contributor PR accuracy)

**Smallest change set for meaningful improvement:**
- Keep current 4-plugin plan
- Add deprecation stubs (not full removal) for aliases in v0.7.0
- Add MIGRATION.md with command mapping table
- Update marketplace BEFORE shipping Clavain v0.7.0 (avoid broken state)

**If timeline allows, consider:**
- Bundling interslack + interform + interdev → reduces 17 companions to 14
- 2-version deprecation (warn in v0.7.0, remove in v0.8.0)
- Community feedback period (ship beta, iterate)

---

## Appendix: User Flow Diagrams

### Current State: User runs `/clavain:lfg`
```
User types `/clavain:lfg`
  ↓
Clavain loads lfg.md
  ↓
lfg.md: "Alias for /clavain:sprint"
  ↓
Sprint executes
```

### Proposed State (no migration): User runs `/clavain:lfg`
```
User types `/clavain:lfg`
  ↓
"Command not found"
  ↓
User confused, searches docs
  ↓
Finds MIGRATION.md (if it exists)
  ↓
Retries with `/clavain:sprint`
```

### Proposed State (with deprecation): User runs `/clavain:lfg`
```
User types `/clavain:lfg`
  ↓
Deprecation stub loads
  ↓
"⚠️ /lfg is deprecated. Use /sprint instead. Removing in v0.8.0."
  ↓
User adapts command
```

---

## Appendix: Command Mapping Table (for MIGRATION.md)

| Old Command | New Command | Notes |
|-------------|-------------|-------|
| `/clavain:lfg` | `/clavain:sprint` | Alias removed |
| `/clavain:full-pipeline` | `/clavain:sprint` | Alias removed |
| `/clavain:cross-review` | `/clavain:interpeer` | Alias removed |
| `/clavain:deep-review` | `/interflux:flux-drive` | Use interflux directly |
| `/clavain:agent-native-audit` | `/intercraft:agent-native-audit` | Moved to intercraft |

**Skills moved:**

| Old Invocation | New Invocation | Plugin |
|----------------|----------------|--------|
| `/clavain:slack-messaging` | `/interslack:slack-messaging` (?) | interslack |
| `/clavain:distinctive-design` | `/interform:distinctive-design` (?) | interform |
| `/clavain:mcp-cli` | `/interdev:mcp-cli` (?) | interdev |
| `/clavain:agent-native-architecture` | `/intercraft:agent-native-architecture` (?) | intercraft |
| `/clavain:finding-duplicate-functions` | (stays in tldr-swinton, not Clavain) | tldr-swinton |

*(Question marks indicate invocation method unspecified in plan)*

---

## Appendix: Plugin Proliferation Analysis

**Current companion count:** 13
- interdoc, tldr-swinton, tuivision, tool-time, clavain, interflux, interphase, interline, interpath, interwatch, interfluence, interkasten, interlock, interpub

**Post-restructure count:** 17
- +4: interslack, interform, intercraft, interdev

**Cognitive load threshold:**
Research on human working memory (Miller's Law, "7±2 items") suggests 17 plugins may exceed casual user's ability to hold mental model.

**Mitigation strategies:**
1. Group by category in help output (core / domain / infrastructure)
2. Create `/companions` command with searchable index
3. Auto-install rig companions via `/setup` (reduce decision burden)
4. Bundle single-skill plugins (reduce total count)

**Recommendation:** Current plan relies on rig installer (`npx @gensysven/agent-rig install`) to handle complexity. This works IF users use rig. If users install piecemeal, 17 is too many.

**Evidence needed:** What % of Clavain users use rig vs manual install?

---

**End of Review**
