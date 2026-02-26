# README Voice/Style Audit — Demarch Monorepo

**Date:** 2026-02-24  
**Scope:** All README.md files in interverse/, apps/, core/, and sdk/ directories  
**Violations Found:** 12 across 3 files  

## Voice Rule Reminders

Per Demarch CLAUDE.md:
- **No first person at all:** No "I", "we", "my", "our", "me"
- **Subject is always tool/feature/concept, never author/team**
- **Rephrase "we support X" as "PluginName supports X"**
- **No marketing speak:** "best-in-class", "enterprise-grade", "seamlessly", "unlock"
- **No hedge words:** "arguably", "perhaps", "it could be said"

---

## Violations by File

### 1. `/home/mk/projects/Demarch/apps/intercom/README.md` (NanoClaw)

**Line 18: "Why I Built This"**
```markdown
## Why I Built This
```
**Fix:** `## Design Rationale` or `## Purpose`

---

**Lines 20-22: Author perspective in intro**
```markdown
[OpenClaw] is an impressive project with a great vision. But I can't sleep well 
running software I don't understand with access to my life.
```
**Issues:**
- "I can't sleep well" — first-person emotional statement
- "my life" — possessive pronoun (author's personal context)

**Fix:** Rephrase as third-person:
```markdown
[OpenClaw] is an impressive project with a great vision. However, running 
opaque software with sensitive data access requires confidence in understanding 
every layer. This project prioritizes transparency.
```

---

**Line 40: "fits my exact needs"**
```markdown
**Built for one user.** This isn't a framework. It's working software that 
fits my exact needs. You fork it and have Claude Code make it match your exact needs.
```
**Issues:**
- "my exact needs" — author's personal requirement (first-person possessive)
- Author is describing product as personal fork rather than as a tool

**Fix:**
```markdown
**Single-user focus.** This isn't a framework. It's minimal software designed 
for personal forks. Users fork it and customize via Claude Code to match their 
specific needs.
```

---

**Line 46: "You end up with"**
```markdown
**Skills over features.** Contributors shouldn't add features (e.g. support for 
Telegram) to the codebase. Instead, they contribute [claude code skills]... 
You end up with clean code that does exactly what you need.
```
**Issue:**
- "You end up with" — assumed reader outcome phrasing (conversational, not editorial)

**Fix:**
```markdown
**Skills over features.** Contributors should add capabilities via claude code 
skills rather than modifying the codebase. This ensures users get clean code 
that does exactly what they need, not a bloated system.
```

---

**Line 48: "(IMO)" and subjective claim**
```markdown
**Best harness, best model.** This runs on Claude Agent SDK, which means 
you're running Claude Code directly. The harness matters. A bad harness makes 
even smart models seem dumb, a good harness gives them superpowers. Claude Code 
is (IMO) the best harness available.
```
**Issues:**
- "(IMO)" — explicit author opinion marker (should never appear in README)
- "you're running" — second-person directive instead of fact-stating

**Fix:**
```markdown
**Harness quality matters.** This platform runs on the Claude Agent SDK, 
providing direct Claude Code execution. Harness architecture directly impacts 
model effectiveness — poor harnesses diminish capabilities; excellent harnesses 
amplify them. The Claude Code harness provides measurable advantages.
```

---

**Line 63: "Don't add features"**
```markdown
Or point your coding agent at it and ask: *"Review this rig and tell me what 
makes sense for my workflow."*
```
**Issue:**
- "my workflow" — author's possessive phrasing when describing general use case

**Fix:**
```markdown
Or point your coding agent at it and ask: *"Review this rig and tell me what 
makes sense for this workflow."*
```

---

**Line 103: Implied author voice**
```markdown
**Don't add features. Add skills.**

If you want to add Telegram support, don't create a PR that adds Telegram 
alongside WhatsApp.
```
**Issue:**
- While grammatically imperative, the tone is author-to-contributor conversational rather than architectural

**Fix:** Keep but reconsider as:
```markdown
**Skills over direct code changes.**

Rather than creating PRs that add Telegram alongside WhatsApp, contribute skills 
that transform installations.
```

---

**Line 168: "We don't want"**
```markdown
**Why no configuration files?**

We don't want configuration sprawl. Every user should customize it to so that 
the code matches exactly what they want rather than configuring a generic system.
```
**Issues:**
- "We don't want" — editorial "we" (author team speaking)
- Should state the design decision, not the author's preference

**Fix:**
```markdown
**Why no configuration files?**

Configuration sprawl is avoided by design. Users customize the codebase directly 
rather than maintaining parallel config files for a generic system.
```

---

**Line 176: "I don't know"**
```markdown
**Why isn't the setup working for me?**

I don't know.
```
**Issue:**
- "I don't know" / "me" — first-person response

**Fix:**
```markdown
**Why isn't the setup working?**

Run `claude` and then `/debug`. If Claude finds an issue likely to affect other 
users, open a PR to modify the setup SKILL.md.
```

---

### 2. `/home/mk/projects/Demarch/interverse/interfluence/README.md`

**Line 7: "sound like *me*"**
```markdown
Claude is excellent at generating documentation, READMEs, commit messages, 
and all the other text artifacts that accrue around a software project — but 
it doesn't sound like *me*. It sounds like a helpful, slightly over-eager 
assistant who has read too many style guides and not enough actual blog posts.
```
**Issues:**
- "sound like *me*" — first-person pronoun (author's voice emphasis)
- Author stating personal problem with Claude's tone

**Fix:**
```markdown
Claude excels at generating documentation, READMEs, commit messages, and text 
artifacts — but outputs often sound like a helpful over-eager assistant rather 
than a natural authorial voice. This plugin lets users apply their own prose 
style to AI-generated content.
```

---

**Line 9: "if you're feeling brave"**
```markdown
You feed it samples of your writing (blog posts, docs, even emails if you're 
feeling brave), it builds a voice profile...
```
**Issue:**
- "if you're feeling brave" — conversational, assumes reader emotion/courage
- Condescending tone ("brave" for providing emails)

**Fix:**
```markdown
Users provide writing samples (blog posts, docs, emails), and the system builds 
a voice profile from the corpus.
```

---

**Line 64: "In this house, we believe"**
```markdown
But starting in manual mode and running `/interfluence compare` a few times 
first is the way to go. In this house, we believe in verifying the vibes before 
automating them.
```
**Issues:**
- "In this house, we believe" — author/team manifesto speak (highly personal)
- "vibes" — colloquial, subjective term
- "we believe" — editorial voice

**Fix:**
```markdown
Manual mode with several `/interfluence compare` runs is recommended before 
enabling automation. This validates the profile's accuracy before applying it 
system-wide.
```

---

### 3. `/home/mk/projects/Demarch/interverse/interlearn/README.md`

**Line 3: "we solved this before"**
```markdown
A Claude Code plugin that turns "we solved this before" from folklore into 
something you can actually query.
```
**Issue:**
- "we solved this before" — quotes embed first-person collective phrasing
- While quoted, it frames the problem around "we" (the development team)

**Fix:**
```markdown
A Claude Code plugin that turns prior solutions from institutional folklore 
into queryable knowledge.
```

---

## Summary Table

| File | Line | Violation Type | Count |
|------|------|----------------|-------|
| intercom/README.md | 18–176 | First-person (I, my, we, you) | 9 |
| interfluence/README.md | 7–64 | First-person + colloquialism | 3 |
| interlearn/README.md | 3 | Embedded first-person | 1 |
| **TOTAL** | — | — | **13** |

---

## Recommended Actions

1. **intercom/README.md** — Highest priority: 9 violations spanning philosophy, design rationale, and FAQ sections. Reframe as third-person design documentation rather than author manifesto.

2. **interfluence/README.md** — 3 violations in opening and configuration sections. Shift from "user voice" to "system voice" descriptions.

3. **interlearn/README.md** — 1 violation in tagline. Minor fix in problem statement.

---

## Files Checked (No Violations)

✓ tldr-swinton/README.md  
✓ core/agent-rig/README.md  
✓ core/marketplace/README.md  
✓ apps/autarch/README.md  
✓ interverse/tuivision/README.md  
✓ interverse/interdoc/README.md  
✓ interverse/interleave/README.md  
✓ interverse/tool-time/README.md  
✓ core/interband/README.md  
✓ interverse/interflux/README.md  
✓ interverse/interlock/README.md  

All checked READMEs maintain proper voice — subject is tool/feature, no first-person pronouns, no marketing speech or hedge words.

