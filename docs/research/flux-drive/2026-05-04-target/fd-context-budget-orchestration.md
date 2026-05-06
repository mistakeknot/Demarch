### Findings Index
- P1 | B-01 | "Budget: MEMORY.md 132/120 over budget; ~40 lines are cold-storage anchors that belong as topic-file references" | Active Projects + Active Brainstorms could move to a single index line each, deferring full content to topic files
- P1 | B-02 | "Budget: skill listings inflate per-turn cost via repeated 'Use when…' / 'Examples:' boilerplate" | ~100 skills × ~30-50 tok of repeated framing = 3-5kt/session of pattern repetition
- P1 | B-03 | "Budget: bd prime + heal-dolt + guard-enabled-plugins inject overlapping protocol setup" | Each hook re-establishes 'session is active, beads protocol applies, work tracking via bd' — 3 framings of the same constraint
- P2 | B-04 | "Budget: CLAUDE.md/AGENTS.md double-load via duplicate beads-protocol blocks" | AGENTS.md contains the BEGIN/END BEADS INTEGRATION block AND CLAUDE.md re-references the same constraints
- P2 | B-05 | "Budget: 'See AGENTS.md For ...' indirection — index never followed at runtime" | CLAUDE.md uses single-line references, but agents Read AGENTS.md anyway; the indirection adds 22 lines without saving load
- P3 | B-06 | "Budget: skill descriptions repeat the same TRIGGER / SKIP framing across the 100-skill listing" | Boilerplate detection: 'Use when X', 'Skip when Y', 'TRIGGER:', 'Examples:' — patterns that compress to a 1-line schema

Verdict: needs-changes

## Summary

The next sylveste-ynh7-style win sits in two compressible regions: (1) MEMORY.md's high-churn project lists, where a topic-file reference would replace 40+ lines of inline state, and (2) the per-skill description budget — across 100+ skills, the repeated `Use when… Examples: SKIP:` framing accounts for 3-5kt of session preamble that compresses to a unified short schema. A third region — bd-prime / heal-dolt / guard-enabled-plugins re-stating the same beads-protocol setup — adds 100-200 tok of redundancy across hooks. Targeted compression of these three regions plausibly clears the agent's "next 2,000+ tok/session win" floor.

## Issues Found

### B-01 (P1) — MEMORY.md Active Projects + Active Brainstorms = 17 lines of cold-storage anchors

**Axis:** token-efficiency
**Current state:** `/home/mk/.claude/projects/-home-mk-projects-Sylveste/memory/MEMORY.md` Active Projects section (lines visible in MEMORY.md context) lists ~12 entries each at 1-2 lines, plus Active Brainstorms with ~5 entries. Each entry follows the pattern `[topic_file.md](topic_file.md) — short description; status note`. Total ~17 lines / ~600 tokens. The format is essentially an index — full content lives in the linked topic_file.md. This is duplicating an index that the agent could derive on-demand by listing `~/.claude/projects/.../memory/project_*.md`.

The user's `feedback_always_file_followup_bead.md` and the user's stated working style ("durable anchors — beads, docs — not verbal bookmarks") imply that "active project" status belongs in beads, not in MEMORY.md inline. MEMORY.md's role is rapid-recall topic-files; the inline status notes ("Phase 1 executing", "Sprint at Step 3 (Write Plan)") are exactly the state beads track.

**Failure scenario:** Every session pays ~600 tokens for a status snapshot that goes stale within days. The user's `feedback_docs_match_codebase_not_memory.md` warns specifically against memory-as-target-shape — yet Active Projects encodes target shape (e.g., "Phase 1 executing" without verification it's still phase 1).

**Proposal:** Replace the Active Projects + Active Brainstorms blocks with two single-line index entries:
```
## Active Work
- Active project status: see `bd ready` and `bd list --status in_progress` (status lives in beads, not memory)
- Active brainstorms: see `docs/brainstorms/` (most recent first)
```
Move the per-project topic-files (project_meadowsyn.md, project_zakalwe.md, etc.) to a flat lookup that's only loaded when the agent calls them by name. The index-of-projects becomes one shell command, not 17 lines of memory.

**Estimated savings:** ~500-600 tok/session.
**Difficulty:** XS (memory edit).
**Risk:** Medium. Removes ambient status-awareness; agents may need an extra `bd list` round-trip when they want active-work context. Mitigated by the fact that `bd ready` is already in AGENTS.md Quick Reference.

### B-02 (P1) — Skill listings: ~100 skills × repeated framing = 3-5kt of compressible pattern

**Axis:** token-efficiency
**Current state:** The skill listing surfaced in this session's system reminder shows ~150 entries (counting both built-in and plugin skills). Average description: 30-80 tokens. Many use repeated patterns:
- `Use this skill when the user asks ...`
- `TRIGGER when: ... SKIP: ...`
- `Examples: "<phrase>", "<phrase>"`
- `When ... Use ...`

These framing tokens (`Use when`, `Examples:`, `TRIGGER:`, `SKIP:`, `Also use when`, `Use ONLY when`) repeat across hundreds of skill descriptions and add up to a substantial fraction of the listing budget.

**Failure scenario:** Every session pays for re-stating the meta-pattern of skill triggering 100+ times in slightly different prose. Each new plugin compounds the cost.

**Proposal:** Standardize a one-line schema for skill descriptions:
```
<short capability sentence> | TRIGGER: <regex/keyword set> | EXAMPLES: <2 short>
```
Use a structured separator (`|`) so the harness/Skill router can parse without LLM cost. Migrate plugins one at a time via a `interskill:audit --compress` mode that flags non-conforming descriptions and proposes rewrites. Target: average description <40 tokens, total skill listing <4kt.

**Estimated savings:** Conservatively 2kt across 150 skills (15 tok/skill); aggressively 4kt (25 tok/skill). At 4kt, this hits the agent's "next 2,000+ tok/session win" target alone.
**Difficulty:** M (cross-plugin migration; requires plugin-author cooperation across the 77 enabled plugins).
**Risk:** Medium. Description format is a stable Claude Code surface; the schema change must preserve LLM routing accuracy. Pilot with 5-10 skills, measure routing-correctness vs baseline, then roll out.

### B-03 (P1) — bd prime + heal-dolt + guard-enabled-plugins: 3 hooks re-establish the same protocol framing

**Axis:** token-efficiency
**Current state:** Examining the three SessionStart-class hooks:
- `heal-dolt.sh + bd stats` — emits "beads available" or "Dolt unavailable, JSONL backup is source of truth"
- `bd prime` — 917-byte prose explaining beads workflow, session-close protocol, rules
- `guard-enabled-plugins.sh` — 0-byte success path; presumably emits enforcement output on failure

All three frame the same context: "this session uses beads; here's what's available." Plus AGENTS.md (loaded once at session start) contains the BEGIN/END BEADS INTEGRATION block which restates the same Quick Reference and Session Completion protocol that bd prime emits.

**Failure scenario:** ~300-400 tok of overlap across the SessionStart hook outputs and the AGENTS.md beads integration block. Agent has the protocol stated four times: settings.json hook output, settings.json second hook output, AGENTS.md Quick Reference, AGENTS.md "BEGIN BEADS INTEGRATION" block.

**Proposal:** Pick one canonical location (recommendation: AGENTS.md "BEGIN BEADS INTEGRATION" block) and trim the others to status-only. New SessionStart contract:
```
heal-dolt + bd-status: emit `[beads] N ready, M in-progress` (1 line)
bd prime: don't fire on SessionStart — only on PreCompact (and emit `[beads] reload protocol if needed: bd prime`)
guard-enabled-plugins: stay silent on success (current behavior); on failure emit single line
```
The protocol prose lives only in AGENTS.md (loaded once via Claude Code session preamble) — not re-injected per-hook.

**Estimated savings:** ~200-300 tok/session, plus ~400 tok per compact event (combines with fd-claude-code-hooks-economy H-01/H-02 + H-06 fixes).
**Difficulty:** S (settings.json edit + add `bd status` short-mode if not present).
**Risk:** Low. Agent already has the protocol via AGENTS.md.

### B-04 (P2) — CLAUDE.md → AGENTS.md double-loading: beads protocol stated in both

**Axis:** token-efficiency
**Current state:** `CLAUDE.md` (lines 20-22): `## See AGENTS.md For ... work tracking, ... operational guides.` Then `AGENTS.md` is loaded *anyway* (line 38 has the work-tracking block; lines 73-118 have the BEGIN/END BEADS INTEGRATION block). So CLAUDE.md's "See AGENTS.md" indirection isn't gating a deferred load — it's just narrative for the agent, while the harness loads both files.

**Failure scenario:** Agent has CLAUDE.md (23 lines) + AGENTS.md (118 lines) loaded together. The CLAUDE.md "See AGENTS.md For ..." pointer adds 4 lines of redundancy because AGENTS.md is loaded regardless. Net cost: ~30 tok of indirection that doesn't gate anything.

**Proposal:** CLAUDE.md should either (a) be the canonical short index and the harness loads it alone, deferring AGENTS.md to on-demand `Read`; or (b) be merged into AGENTS.md if the harness will always co-load. Today's hybrid pays the cost of (b) while pretending to be (a). Recommendation: (a). Trim AGENTS.md to topic-guide table + the BEADS INTEGRATION block; rely on agents using `Read agents/architecture.md` etc. on demand.

**Estimated savings:** If full AGENTS.md becomes deferred: ~118 lines × ~10 tok/line ≈ 1.2kt/session minus the (already-loaded) CLAUDE.md content. Net: 600-1000 tok/session.
**Difficulty:** M (changes the load-order contract; depends on Claude Code harness behavior — verify whether AGENTS.md is auto-loaded or only on first agent dispatch).
**Risk:** Medium. If agents lose ambient AGENTS.md context, complex tasks (publishing, architecture decisions) may need explicit `Read agents/architecture.md` calls earlier. Acceptable trade.

### B-05 (P2) — CLAUDE.md "See AGENTS.md For" stub adds lines without saving load

**Axis:** token-efficiency
**Current state:** Lines 20-22 of CLAUDE.md: `## See AGENTS.md For\n\nArchitecture, naming conventions, plugin collision rules, work tracking, git workflow, publishing, critical patterns, design doctrine, operational guides.` This is 4 lines of pointer text. Per B-04, AGENTS.md loads regardless, so the pointer doesn't actually defer anything — it's narrative redundancy.

**Failure scenario:** ~30-40 tok of session preamble is meta-text about file organization rather than content.

**Proposal:** Either (a) delete the section if AGENTS.md auto-loads alongside CLAUDE.md; or (b) replace with a one-liner: `Specialized topics: see AGENTS.md.`

**Estimated savings:** ~30 tok/session (small, but trivially safe).
**Difficulty:** XS.
**Risk:** None.

### B-06 (P3) — Skill description boilerplate: TRIGGER/SKIP/Examples patterns are uniformly repetitive

**Axis:** token-efficiency
**Current state:** Examining a sample of skill descriptions in this session's listing:
- `claude-api`: `... TRIGGER when: code imports anthropic/@anthropic-ai/sdk; user asks for the Claude API ... SKIP: file imports openai/other-provider SDK ...` (~150 tok)
- `claude-md-management:claude-md-improver`: `Audit and improve CLAUDE.md files in repositories. Use when user asks to check, audit, update, improve, or fix CLAUDE.md files. Scans for all CLAUDE.md files, evaluates quality against templates ... Also use when the user mentions ...` (~80 tok)
- Most skills follow a `<verb> <object>. Use when <conditions>. Examples: <list>.` shape.

**Failure scenario:** This is the same problem as B-02 viewed from the data side: the *patterns* themselves can be templated. A registry-level schema (`description`, `trigger_keywords[]`, `skip_keywords[]`, `examples[]`) would let the harness assemble the natural-language hint for the LLM with minimal duplicated framing.

**Proposal:** This is B-02's implementation. Track here as a P3 follow-on for a structured schema (vs. B-02's compress-in-place).

**Estimated savings:** Subsumed by B-02.
**Difficulty:** Subsumed by B-02.
**Risk:** Subsumed by B-02.

## Improvements

1. **Memory hygiene script:** `scripts/memory-hygiene.sh` that surfaces lines older than 30 days where last_used < 30d-ago, plus topic_files referenced from MEMORY.md but not opened in the last 30d. Pair with `/intermem:tidy` to make pruning regular.
2. **Skill description audit:** `scripts/skill-listing-cost.sh` that emits per-skill (token count, framing-pattern count, redundancy score). Output ranks skills by compression potential.
3. **Add `docs/canon/preamble-budget.md`** as a single source of truth: budget per region (CLAUDE.md ≤ 30 lines, MEMORY.md ≤ 120 lines, AGENTS.md ≤ 100 lines, skill descriptions ≤ 40 tok each, MCP instructions ≤ 100 tok each). Wire into a CI check that fails PRs increasing any region without justification.
4. **Move project-status from MEMORY.md to beads-only.** Establishes the principle: ambient state lives in tooling-queryable surfaces (beads, git, CLI), not in memory snapshots.

<!-- flux-drive:complete -->

--- VERDICT ---
STATUS: warn
FILES: 0 changed
FINDINGS: 6 (P0: 0, P1: 3, P2: 2, P3: 1)
SUMMARY: MEMORY.md Active Projects = 600 tok of cold-storage status that belongs in beads; skill descriptions repeat 'Use when/Examples/TRIGGER' framing for ~3-5kt across 100+ skills; bd-prime + heal-dolt + AGENTS.md beads-block triple-state the same protocol. Combined potential: 2.5-5kt/session win — clears the next-ynh7 floor.
---
