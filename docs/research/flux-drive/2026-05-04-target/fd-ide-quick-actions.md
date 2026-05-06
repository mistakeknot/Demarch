# fd-ide-quick-actions — Slash Command Discoverability Review

**Reviewer:** fd-ide-quick-actions
**Date:** 2026-05-04
**Discipline:** IDE platform design (IntelliJ Code Actions, VSCode quick-fix, JetBrains intentions)

### Findings Index

| Severity | ID | Section | Title |
|----------|-----|---------|-------|
| P1 | IDE-01 | Intent Grouping | 58 plugins share "inter" prefix — prefix-based narrowing fails |
| P1 | IDE-02 | Semantic Collision | 6 distinct "review" commands across plugins — user can't tell which to invoke |
| P1 | IDE-03 | Semantic Collision | 6 "status" commands with no disambiguation heuristic |
| P2 | IDE-04 | Keyboard Ergonomics | High-frequency `/interflux:flux-drive` (21 chars) vs `/clavain:tdd` (11 chars) |
| P2 | IDE-05 | Context Relevance | No sprint-phase-aware command ranking — flat alphabetical listing |
| P2 | IDE-06 | Suggestion Fatigue | 111 commands + 121 skills in flat listing — user must scroll/read all |
| P2 | IDE-07 | Argument Hints | No `<args>` pattern hints at discovery time — trial-and-error required |
| P3 | IDE-08 | Verb Grouping | Commands grouped by plugin source, not user-intent verb |

**Verdict:** needs-changes

### Summary

Sylveste exposes 111 commands and 121 skills across 60+ plugins, but lacks IDE-grade discoverability discipline. Three critical gaps:

1. **Prefix collision**: 58 plugins share the "inter" prefix — typing `/inter` narrows from 232 options to... 58 plugins (minimal disambiguation).
2. **Semantic collision**: Commands like `/clavain:review`, `/interflux:flux-review`, `/interlore:review` are semantically similar but scoped differently — users invoke the wrong one 1-2 times per workflow.
3. **No ranking**: Unlike IntelliJ's recency+frequency+context ranking, all commands are alphabetical. Sprint-relevant commands aren't boosted during sprint phases.

Estimated total UX friction: 15-30 seconds/session on command discovery; ~200 tokens/session on clarifying wrong invocations.

---

### Issues Found

#### IDE-01 (P1): 58 Plugins Share "inter" Prefix — Prefix-Based Narrowing Fails

**Axis:** Usability
**Discipline Reference:** In IntelliJ, typing 3 characters in the action popup narrows results to <10 options. VSCode's Command Palette fuzzy-matches against action names, but the first 3-5 chars provide strong disambiguation.

**Current State:**
- 58 of 60+ plugins use `inter*` naming: interflux, interlock, interpath, intermem, etc.
- Typing `/inter` in Claude Code shows 58 plugins × ~2 commands each = ~116 options
- Typing `/interf` still shows 4 plugins: interflux, interfluence, interfer, interform

**File Reference:** All `interverse/*/.claude-plugin/plugin.json` (58 files)

**Proposal:** Introduce **semantic short-prefixes** as plugin aliases:
```json
{
  "name": "interflux",
  "aliases": ["fx", "flux", "review"],
  ...
}
```
Allow `/fx:flux-drive` (13 chars) as equivalent to `/interflux:flux-drive` (21 chars).

Alternatively, adopt **verb-first naming** for commands: `/review:flux` instead of `/interflux:flux-review`.

**Estimated Savings:**
- UX friction: -5 sec/session (prefix typing)
- Tokens: -50/session (fewer clarification turns)

**Difficulty:** S (schema change + plugin.json updates)
**Risk:** Alias collisions (two plugins claim `/fx`). Mitigate: AGENTS.md namespace registry + CI lint.

---

#### IDE-02 (P1): 6 Distinct "review" Commands — User Can't Tell Which to Invoke

**Axis:** Usability
**Discipline Reference:** IntelliJ never shows two quick-fix actions with the same display name but different implementations. When scopes differ (e.g., "Extract Method" for class vs module), the popup disambiguates with context: "Extract Method (to companion object)".

**Current State:**
```
clavain:plan-review        — Lightweight 3-agent plan review
clavain:review-discipline  — Disciplined code review + feedback triage
clavain:review-doc         — Single-pass doc refinement
clavain:review             — PR-focused multi-agent review
interlore:review           — Philosophy pattern detection
interflux:flux-review      — Deep multi-agent review (any input)
```

User intent: "review this code" → which of 6?

**File References:**
- `os/Clavain/commands/review.md`
- `os/Clavain/commands/review-discipline.md`
- `os/Clavain/commands/review-doc.md`
- `os/Clavain/commands/plan-review.md`
- `interverse/interlore/commands/review.md`
- `interverse/interflux/commands/flux-review.md`

**Proposal:** Add **inline disambiguation hints** to skill descriptions visible at listing time:
```
/clavain:review           — PR-focused review (git diff context)
/interflux:flux-review    — Deep review (any file, multi-agent)
/clavain:review-discipline — Code review + reviewer feedback triage
```

Or: create a **router command** `/review` that asks one clarifying question:
- "PR or file?" → routes to appropriate implementation

**Estimated Savings:**
- UX friction: -10 sec/session (eliminate wrong-invocation retry)
- Tokens: -150/session (skip "that's not what I meant, try /other:review")

**Difficulty:** S (description updates) or M (router command)
**Risk:** Router adds latency. Mitigate: cache routing decision per session.

---

#### IDE-03 (P1): 6 "status" Commands With No Disambiguation

**Axis:** Usability
**Discipline Reference:** IntelliJ's "Show Usages" action is context-aware — invoked on a method, it shows method usages; on a class, class usages. The action name is the same but behavior differs by context.

**Current State:**
```
clavain:status         — Clavain workflow state
clavain:sprint-status  — Sprint workflow state + recommendations
interlock:status       — Agent reservation state
interpath:status       — Path artifact state
interlore:status       — Philosophy observation state
interscout:status      — Scout monitoring state
interwatch:status      — Doc watch state
```

User intent: "what's the status?" → which of 7?

**File References:**
- `os/Clavain/commands/status.md`
- `os/Clavain/commands/sprint-status.md`
- `interverse/interlock/commands/status.md`
- `interverse/interpath/commands/status.md`
- `interverse/interlore/commands/status.md`
- `interverse/interscout/commands/status.md`
- `interverse/interwatch/commands/status.md`

**Proposal:** Implement **context-aware status routing**:
- If in a sprint → `/status` routes to `clavain:sprint-status`
- If interlock session active → `/status` routes to `interlock:status`
- Default → composite status (Clavain + active plugins)

Or: rename to **noun-status** pattern: `/sprint-status`, `/lock-status`, `/path-status`

**Estimated Savings:**
- UX friction: -5 sec/session
- Tokens: -100/session

**Difficulty:** M (context detection + routing)
**Risk:** Context detection false positives. Mitigate: show "(guessed: sprint context)" in response.

---

#### IDE-04 (P2): High-Frequency Commands Have High Keystroke Cost

**Axis:** Usability
**Discipline Reference:** IntelliJ's most-used actions have keyboard shortcuts (Alt+Enter for quick-fix, Ctrl+Shift+A for action search). Frequently-used actions should be fastest to invoke.

**Current State:**
- `/interflux:flux-drive` (21 chars) — likely high-frequency review command
- `/interfluence:interfluence` (25 chars) — voice analysis
- `/interline:statusline-customize` (30 chars)
- vs. `/clavain:tdd` (11 chars), `/clavain:work` (12 chars)

No cass usage data available to confirm actual frequency, but review commands are likely 10x more frequent than statusline customization.

**File Reference:** All `*/.claude-plugin/plugin.json` command registrations

**Proposal:** Add **short aliases** for top-10 commands by expected frequency:
| Long form | Short alias |
|-----------|-------------|
| `/interflux:flux-drive` | `/fd` or `/flux` |
| `/clavain:sprint` | `/sp` |
| `/clavain:review` | `/rv` |
| `/clavain:work` | `/wk` |
| `/clavain:recall` | `/rc` |

**Estimated Savings:**
- UX friction: -8 chars × 5 invocations/session × 0.1 sec/char = -4 sec/session
- Tokens: negligible

**Difficulty:** S (alias registry in plugin.json schema)
**Risk:** Alias collision. Mitigate: reserved alias list in AGENTS.md.

---

#### IDE-05 (P2): No Sprint-Phase-Aware Command Ranking

**Axis:** Usability
**Discipline Reference:** VSCode's Command Palette shows recently-used commands first. IntelliJ's Intentions show context-relevant actions above generic ones (e.g., "Implement methods" only appears when cursor is on a class missing implementations).

**Current State:**
- During a sprint, `/clavain:sprint-status`, `/clavain:work`, `/clavain:verify` should rank higher
- During review phase, `/interflux:flux-drive`, `/clavain:review`, `/clavain:resolve` should rank higher
- No phase detection or ranking exists — all commands shown alphabetically

**File Reference:** `os/Clavain/.claude-plugin/plugin.json` (no ranking metadata)

**Proposal:** Add **phase-aware ranking** to skill listing:
1. Detect current phase from interphase or sprint context
2. Boost commands tagged with that phase
3. Add `phase_relevance` field to command metadata:
```json
{
  "commands": [{
    "path": "./commands/work.md",
    "phase_relevance": ["execute", "sprint"]
  }]
}
```

**Estimated Savings:**
- UX friction: -10 sec/session (less scrolling/searching)
- Tokens: -50/session (fewer "what command should I use?" queries)

**Difficulty:** M (phase detection + ranking sort)
**Risk:** Phase misdetection. Mitigate: show "(phase: execute)" indicator.

---

#### IDE-06 (P2): 232 Options in Flat Listing — Suggestion Fatigue

**Axis:** Usability
**Discipline Reference:** IntelliJ's action search caps visible results at ~15, with "Show All" expansion. VSCode's Command Palette shows ~10 with scroll. Neither shows 200+ options at once.

**Current State:**
- 111 commands + 121 skills = 232 total options
- System reminder lists all skills alphabetically
- `/clavain:help` organizes by stage but only for Clavain commands (52 of 232)

**File Reference:** System prompt skill listing (in `<system-reminder>` blocks)

**Proposal:** Implement **progressive disclosure** for skill listing:
1. **Tier 1 (always shown):** 10-15 "daily drivers" based on frequency
2. **Tier 2 (on demand):** Phase-relevant commands
3. **Tier 3 (search only):** All 232 options

Add `/commands` or `/actions` skill that provides IDE-like filtering:
```
/commands review     — shows review-related commands only
/commands --phase execute  — shows execute-phase commands
```

**Estimated Savings:**
- Tokens: -500/session (smaller skill listing in preamble)
- UX friction: -15 sec/session (less scanning)

**Difficulty:** M (tiered listing + search skill)
**Risk:** Users miss commands not in Tier 1. Mitigate: clear "more commands..." indicator.

---

#### IDE-07 (P2): No Argument Hints at Discovery Time

**Axis:** Usability
**Discipline Reference:** IntelliJ shows parameter hints inline: `extractMethod(selectedCode: Expression, targetClass: Class)`. VSCode's Command Palette shows argument syntax in description.

**Current State:**
- `/clavain:work` accepts a plan path but user must know this
- `/interflux:flux-drive` accepts a file path but syntax unclear
- No `<args>` pattern visible in skill listing
- User must trial-and-error or read SKILL.md

**File Reference:** All command `.md` files (args documented in body, not frontmatter)

**Proposal:** Add **args hint** to command frontmatter, surfaced in listing:
```yaml
---
name: clavain-work
args: "[plan-file]"
args_hint: "Path to plan .md file"
---
```

Listing shows: `/clavain:work [plan-file]` — Path to plan .md file

**Estimated Savings:**
- UX friction: -5 sec/session (no trial-and-error)
- Tokens: -100/session (no "what does /work accept?" queries)

**Difficulty:** XS (frontmatter field + listing enhancement)
**Risk:** None significant.

---

#### IDE-08 (P3): Commands Grouped by Plugin, Not Intent Verb

**Axis:** Usability
**Discipline Reference:** IntelliJ groups intentions by category ("Refactor", "Generate", "Navigate"), not by contributing plugin. Users think in verbs: "I want to refactor" not "I want JetBrains-refactor-plugin action".

**Current State:**
- `/clavain:review`, `/interflux:flux-review`, `/interlore:review` scattered by plugin
- No "Review" group showing all review commands
- No "Setup" group showing all setup commands

**File Reference:** System prompt skill listing organization

**Proposal:** Add **verb-based grouping** to `/help` and skill listing:
```
## Review
/clavain:review           — PR-focused (git diff)
/interflux:flux-drive     — Deep multi-agent (any file)
/clavain:review-doc       — Doc refinement
/interlore:review         — Philosophy patterns

## Setup
/clavain:setup            — Bootstrap Clavain
/interlock:setup          — File reservation
/intership:setup          — Ship workflow
```

**Estimated Savings:**
- UX friction: -10 sec/session (mental model matches listing)
- Tokens: negligible

**Difficulty:** S (help.md restructure + skill listing enhancement)
**Risk:** Verb categorization ambiguous for some commands. Mitigate: allow multi-category tagging.

---

### Improvements

1. **Alias registry** (IDE-01, IDE-04): Add `aliases` field to plugin.json schema. Reserve common short prefixes (`/fd`, `/sp`, `/wk`, `/rv`). CI lint for collision detection.

2. **Router commands** (IDE-02, IDE-03): Create `/review` and `/status` router skills that ask one disambiguation question or use context to route automatically.

3. **Phase-aware ranking** (IDE-05): Tag commands with `phase_relevance` in frontmatter. Boost phase-relevant commands in listings. Integrate with interphase phase detection.

4. **Progressive disclosure** (IDE-06): Tier skill listing into daily-drivers, phase-relevant, and search-only. Add `/commands [filter]` skill for IDE-like search.

5. **Args hints** (IDE-07): Add `args` and `args_hint` to command frontmatter. Surface in skill listing as `/command [args]`.

6. **Verb grouping** (IDE-08): Restructure `/clavain:help` by intent verb. Tag commands with `verb_category` for cross-plugin grouping.

---

### Token Efficiency Estimates

| Finding | Token Savings/Session | Implementation Cost |
|---------|----------------------|---------------------|
| IDE-01 Aliases | 50 | S |
| IDE-02 Review Router | 150 | M |
| IDE-03 Status Router | 100 | M |
| IDE-06 Tiered Listing | 500 | M |
| IDE-07 Args Hints | 100 | XS |
| **Total** | **900** | |

### ML Routing Replacement Candidates

| Decision | Current | ML Alternative | Input Vector | Precision Floor |
|----------|---------|----------------|--------------|-----------------|
| Review type routing | LLM prompt | Classifier (context → review type) | git state + file types + recent commands | 85% |
| Status type routing | LLM prompt | Rule-based + phase detection | interphase state + active plugins | 95% |
| Phase detection | Manual or LLM | Classifier (session history → phase) | recent 10 commands + bead state | 80% |

**Most viable ML replacement:** Review-type routing. Input: `{has_git_diff, file_extension, is_pr_context, recent_commands}`. Output: `{flux-drive, review, review-doc, plan-review}`. Training data: 10K+ sessions with skill invocations from cass. Estimated LLM-cost savings: 150 tokens/session on disambiguation.

<!-- flux-drive:complete -->
