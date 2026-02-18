# User & Product Review: interfluence Code-Switching PRD

**Reviewer:** Flux-drive User & Product Reviewer
**Date:** 2026-02-18
**Document:** `docs/prds/2026-02-18-interfluence-code-switching.md`
**Status:** READY FOR REVISION — Multiple critical UX gaps and missing user-facing validation

---

## Executive Summary

**Primary user:** Technical writers, developer advocates, and documentation maintainers who write across multiple contexts (blog posts, GitHub READMEs, commit messages, PRDs, Slack) and whose single voice profile currently produces output that "sounds wrong everywhere."

**Job to be done:** Automatically match the right writing voice to each file context without manual intervention, while preserving a shared authorial identity across all contexts.

**Critical findings:**
1. **Auto-classification UX is invisible and unverifiable** — users have no way to see or correct what the analyzer decided
2. **First-match-wins creates unpredictable behavior** — no documentation of order guarantees, no conflict resolution UI
3. **Delta model is technically sound but explanation-free** — users won't understand why changing the base doesn't affect their blog voice
4. **Missing onboarding path** — existing single-profile users face an invisible migration with no explanation
5. **No escape hatches** — users cannot inspect, override, or debug voice resolution decisions

**Recommendation:** Add transparent classification results, explicit conflict resolution, and progressive disclosure of the delta model before shipping. The architecture is solid, but users will be confused and unable to debug problems.

---

## Problem Validation

### Evidence Quality: ASSUMED

**Stated problem:** "A single flat voice profile averages across writing registers, producing output that sounds wrong in every context — too casual for docs, too stiff for blog posts."

**Evidence presented:** None. No user interviews, support tickets, or behavioral data showing:
- How many interfluence users write across multiple contexts
- How often they report voice mismatch issues
- Whether they've tried workarounds (multiple projects, manual profile edits)
- What registers cause the most pain (blog/docs assumed, not validated)

**User segmentation missing:**
- **New users** — will see complex voice config before understanding basic voice profiles
- **Single-context users** — will experience added complexity for zero value
- **Multi-context users** — assumed to exist, but how many? Are they early adopters who'll tolerate rough edges, or mainstream users who need polish?

**Severity assessment:** If this is a "nice to have" for 10% of users, the PRD should say so explicitly. If it's blocking adoption for a critical segment, provide evidence.

---

## UX Review

### 1. Auto-Classification UX: INVISIBLE AND UNVERIFIABLE

**F3 acceptance criteria (line 44):**
> "Analyzer classifies untagged corpus samples into contexts (blog, docs, or unclassified)"

**User perspective:** Where do I see this classification? How do I know it got it right?

**Missing flows:**
- **Post-analysis results display** — Show users: "I classified 8 samples as 'blog', 3 as 'docs', 2 as 'unclassified'. Review classifications?"
- **Review UI** — Let users see which samples went where and reclassify mistakes (e.g., "No, that README is actually a blog post style")
- **Confidence indicators** — If the analyzer is unsure, tell the user instead of guessing silently
- **Unclassified sample handling** — What happens to them? Are they ignored? Included in base? Used as negative examples?

**Current PRD:** F3 writes classifications back to `corpus-index.yaml` via the `tags` field (line 45), but there's no skill to **view** those tags. Users would need to manually open the YAML file.

**Proposal:** Add `/interfluence corpus` subcommand that shows samples grouped by classification, with inline reclassification:
```
Blog (8 samples):
- posts/2025-12-my-ai-rant.md [blog] — change to: [docs] [unclassified]
- ...

Docs (3 samples):
- README.md [docs]
- ...

Unclassified (2 samples):
- notes/scratch.md [unclassified] — assign to: [blog] [docs] [remove]
```

**Impact if not fixed:** Users will not trust the system. When voice application feels wrong, they won't know if the problem is classification, base/delta split, or profile quality. Debugging becomes impossible.

---

### 2. First-Match-Wins: UNPREDICTABLE AND UNDOCUMENTED

**F2 acceptance criteria (line 36):**
> "First-match-wins: voices checked in config order"

**Questions users will have:**
1. What is "config order"? The order I define keys in YAML? (YAML has undefined key order in most parsers!)
2. What happens if `posts/**` matches and I also have `**/*.md` for docs?
3. How do I debug which rule matched when a file gets the wrong voice?
4. Can I see a "voice resolution report" for my entire project?

**Missing from PRD:**
- **Explicit ordering mechanism** — Recommend array syntax to guarantee order:
  ```yaml
  voices:
    - name: blog
      applyTo: ["posts/**", "blog/**"]
    - name: docs
      applyTo: ["docs/**", "README.md"]
  ```
- **Conflict detection** — Warn users at config save time if patterns overlap
- **Resolution logging** — When applying voice, show: "Matched 'blog' voice via pattern 'posts/**' (tried 2 patterns, stopped at first match)"

**Current PRD (line 58):** "Skill reports which voice was used: 'Applied blog voice to posts/new-post.md'" — This is **output** reporting, not **decision** reporting. Users need to understand *why* it matched.

**Proposal:** Add `--explain` flag to `/interfluence apply`:
```
$ /interfluence apply posts/new-post.md --explain
Voice resolution:
✓ Matched 'blog' via pattern 'posts/**'
✗ Skipped 'docs' (pattern 'docs/**' did not match)
→ Applied blog voice (base + 4 overrides)
```

**Impact if not fixed:** Users will create configs that work by accident, then break when they add a new pattern. Power users will demand a "voice resolution dry-run" tool within weeks of release.

---

### 3. Delta Model: TECHNICALLY SOUND, EXPLANATION-FREE

**Design (brainstorm line 21-23):**
> "Base profile (`voice-profile.md`) contains **cross-context invariants only** — the authorial DNA that persists regardless of register... Context voices (`voices/blog.md`, `voices/docs.md`) contain **only sections that differ from the base**"

**This is architecturally excellent.** It prevents sample-volume drift and makes base changes propagate automatically.

**User mental model:** Most users will assume `voice-profile.md` is a "generic fallback" and `voices/blog.md` is a "full profile for blog posts."

**Missing explanations:**
- **What goes in the base?** Users will want examples: "Use base for: humor style, em-dash usage, cultural references. Use deltas for: sentence length, formality, technical jargon handling."
- **How do I edit a delta?** If I want my blog voice to use shorter sentences, do I edit `voices/blog.md` directly? What if that section doesn't exist yet? Do I need to copy it from the base first?
- **What happens when I edit the base?** If I refine the base's "Humor" section, will it affect my docs voice? (Answer: yes, unless docs delta overrides it — but users won't know this.)

**Current PRD:** No user-facing documentation planned. The only explanation is in internal design docs (brainstorm line 24-26).

**Proposal:** Add `/interfluence explain-voices` subcommand that generates a plain-English summary:
```
Voice Profile Structure:

Base (voice-profile.md):
- Shared traits across all your writing
- Currently covers: Humor Style, Em-dash Usage, Cultural References
- Changes here affect ALL voices unless overridden

Blog (voices/blog.md):
- Overrides 3 base sections: Sentence Structure, Formality, Technical Handling
- Inherits 4 base sections: Humor Style, Em-dash Usage, ...

Docs (voices/docs.md):
- Overrides 2 base sections: Formality, Structure Patterns
- Inherits 5 base sections: ...
```

**Alternatively:** Embed this explanation directly in generated voice files as comments.

**Impact if not fixed:** Users will edit the wrong file, get confused when changes don't apply where expected, and conclude the feature is broken. Support burden will be high.

---

### 4. Migration Path: INVISIBLE AND RISKY

**Brainstorm open question #2 (line 99):**
> "Existing users have a single `voice-profile.md`. Treat it as the base profile automatically (no migration command needed)?"

**Answer from user perspective:** **No.** Silent migration is dangerous.

**Current user experience:**
1. User has interfluence working with a single profile
2. User upgrades plugin to v0.3.0
3. User runs `/interfluence analyze` to incorporate new writing samples
4. Analyzer silently reclassifies all corpus samples, splits profile into base + deltas
5. User's existing `voice-profile.md` is either overwritten or becomes base (unclear which)
6. User's next `/interfluence apply` behaves differently with no warning

**Missing from PRD:**
- **Migration detection** — On first run of new version, detect single-profile users and offer migration
- **Migration preview** — Show what would change: "I'll split your profile into base (5 sections) + blog (3 overrides) + docs (2 overrides). Proceed?"
- **Rollback path** — Let users revert to single-profile mode if multi-voice causes problems
- **Version compatibility** — F1 claims backward compatibility (line 24), but F3 changes analyzer behavior. How are these reconciled?

**Proposal:** Add explicit migration flow:
```
$ /interfluence analyze
Detected single voice profile from interfluence v0.2.x.
Your corpus contains blog posts and docs. Split into context-specific voices? [y/N]

→ Yes: I'll create base + blog + docs voices
→ No: I'll keep your current single profile (you can split later with /interfluence split-voices)
```

**Impact if not fixed:** Early adopters (who gave you the corpus to build this feature) will have their working profiles changed without consent. Trust damage.

---

### 5. Voice Resolution Transparency: MISSING

**F4 acceptance criteria (line 58):**
> "Skill reports which voice was used: 'Applied blog voice to posts/new-post.md'"

**This is output reporting, not decision transparency.**

**Missing debug/preview flows:**
- **Dry-run mode** — `interfluence apply --dry-run posts/new-post.md` → shows which voice would apply and why, without actually rewriting
- **Project-wide voice map** — `interfluence map-voices` → lists all `.md` files in project with resolved voices
- **Override testing** — `interfluence apply --voice=docs posts/new-post.md --explain` → shows what changed vs auto-resolved voice

**Current PRD:** No mention of debugging tools. Users will rely on trial-and-error.

**Proposal:** Add `--dry-run` flag to all apply operations (both explicit and auto-mode once F89 ships).

**Impact if not fixed:** Users cannot answer "Will my new pattern work?" without actually applying it to files and checking the output.

---

### 6. Learning Hook Context Tagging: FRAGILE

**F5 acceptance criteria (line 68):**
> "Hook reads `voices` config to resolve file path → context"

**Open Question #1 (line 99):**
> "Learning hook config access — The shell hook currently reads `config.yaml` with basic grep. Adding voice resolution (glob matching) in bash may be fragile. Consider: tag as `CONTEXT:unknown` and let the refine skill resolve context at review time."

**User impact analysis:**
- If hook tags incorrectly, users won't notice until `/interfluence refine`
- If hook tags as `unknown`, users see learnings grouped by context but some are orphaned
- If glob matching in bash breaks, learnings are silently untagged

**Current PRD:** Leaves this as an open question, leans toward `CONTEXT:unknown` fallback (line 99-100).

**Recommendation:** Ship with `CONTEXT:unknown` fallback. Reasoning:
1. Learning hook runs on every edit — must be fast and never fail
2. Bash glob matching is error-prone (ask any CI pipeline maintainer)
3. False negatives (unknown) are recoverable; false positives (wrong context) corrupt the profile
4. Users review learnings interactively in `/interfluence refine` anyway — that's the right place to resolve ambiguity

**Missing from PRD:** How does the refine skill handle `CONTEXT:unknown` learnings? Acceptance criteria should cover:
- Show unknown learnings separately: "3 learnings from unknown contexts — assign them?"
- Let user tag them during review: "This edit to `scripts/deploy.sh` — is this [blog] [docs] [ignore]?"

**Impact if not fixed:** Learnings accumulate in `unknown` bucket, users never process them, continuous learning stops working.

---

### 7. Compare Skill: UNDERSPECIFIED

**F6 acceptance criteria (line 78):**
> "`/interfluence compare` shows which voice best matches a given text"

**Questions:**
1. Does it compare against all voices or just the resolved one?
2. Does it show match scores, or just "blog is 85% match, docs is 60%"?
3. Can users compare two files to see which contexts they belong to?
4. Can users compare a draft to their corpus to check if it "sounds like them" before committing?

**Brainstorm open question #3 (line 101):**
> "Should `/interfluence compare` show match scores against all voices, or just the inferred one?"

**Answer from user perspective:** **All voices, with ranking.** Users want diagnostic information, not just confirmation.

**Use cases:**
- "I wrote this blog post draft — does it sound like my other blog posts?" (single-voice match quality)
- "I'm not sure if this belongs in docs or blog" (multi-voice comparison for classification guidance)
- "This commit message doesn't feel right — show me what's off" (deviation analysis)

**Current PRD:** Compare is listed as a feature (F6) but has almost no specification beyond "best matches."

**Proposal:** Expand compare acceptance criteria:
```
- [ ] /interfluence compare <file> shows match scores for all voices
- [ ] Scores presented as: blog (85%), docs (60%), base (72%)
- [ ] Optional --explain flag shows which traits matched/mismatched
- [ ] Optional --suggest flag recommends adjustments: "Too formal for blog voice — consider contractions"
```

**Impact if not fixed:** Feature will ship as a binary "yes/no" match checker instead of a useful diagnostic tool. Users will request the full version within weeks.

---

## Product Validation

### Value Proposition

**Stated value:** Save users from manually switching between voice modes or maintaining multiple projects to get context-appropriate writing assistance.

**Clarity:** 7/10. The value is clear to users who already understand they have this problem. New users won't recognize the problem until they experience voice mismatch.

**Time-to-value:**
- **Existing single-profile users:** Negative on first use (migration friction), neutral after understanding delta model, positive once classification is accurate
- **New users:** Delayed — must build corpus, classify, generate profiles, then finally apply
- **Multi-context power users:** Immediate — this directly solves their current pain

**Adoption barriers:**
1. **Conceptual complexity** — Base/delta model is not intuitive
2. **Classification trust** — Users must trust auto-classification before they trust voice application
3. **Config syntax** — Glob patterns + ordering semantics are power-user territory

**Missing from PRD:** Progressive disclosure plan. How do new users discover this feature? Is it opt-in? Default on?

**Recommendation:** Make multi-voice opt-in during analyze:
```
$ /interfluence analyze
I found blog posts and docs in your corpus.
→ Generate separate voices for each context? (Recommended for multi-context writers)
→ Generate a single blended voice? (Simpler, works for most users)
```

---

### Scope Creep Analysis

**Claimed MVP scope (line 83-89):**
- Commit message voice → deferred
- Slack voice → deferred
- Composable layers → deferred
- Profile export/import → deferred
- Confidence metrics → deferred
- Auto-apply mode changes → deferred

**Actual scope creep:**
1. **F3 auto-classification** — This is a full ML classification problem dressed up as "the analyzer does comparative analysis." If corpus diversity is low, classification quality will be poor. No accuracy targets specified.
2. **F2 glob matching** — Pattern languages are API surface. First-match-wins is order-dependent. This has hidden complexity.
3. **F4 merged profile loading** — Section-level merging (line 59 "delta wins per-section") implies a structured profile format. Current profiles are markdown prose. How do you know where one section ends and another begins? Parser fragility risk.

**Missing from PRD:**
- **Classification accuracy targets** — What percentage of samples must be classified correctly for this to be useful?
- **Graceful degradation** — What if corpus has only 3 samples? What if all samples are one context?
- **Profile schema enforcement** — How do you merge delta sections if users hand-edited the base profile and broke section boundaries?

**F3 acceptance criteria (line 47-49):**
> "With only one context's samples, generates base + that one delta (graceful degradation)"
> "With no context diversity, generates a single base profile (current behavior)"

**This is good.** But what does "one context's samples" mean numerically? 1 sample? 3 samples? 10 samples?

**Recommendation:** Add minimum sample thresholds to acceptance criteria:
- 1-5 samples total → single base profile, warn user
- 6+ samples, all one context → base + one delta
- 6+ samples, 2+ contexts with 3+ samples each → full multi-voice

---

### Evidence Standards

**Data-backed findings:** None.

**Assumption-based reasoning:** Entire PRD.

**Key unvalidated assumptions:**
1. **Users write across multiple contexts** — assumed, not measured
2. **Blog and docs are the right two contexts** — chosen for "maximal difference," not user research
3. **Auto-classification will be accurate enough** — no prototype, no accuracy target
4. **First-match-wins is intuitive** — conflicts with CSS/firewall rule experience (last-match-wins or explicit priority)
5. **Users will understand the delta model** — no usability testing planned

**Recommendation:** Before full implementation, ship a prototype with:
- Manual classification (user tags samples during ingest)
- Explicit voice selection (no auto-resolution, must use `--voice` flag)
- Verbose output showing what's happening

Let 5-10 early users validate the model before building auto-classification.

---

## Missing Edge Cases

### 1. Partial Corpus Coverage

**Scenario:** User has 20 blog posts, 2 READMEs, 50 commit messages (not yet supported).

**Expected behavior:** Should docs voice be generated with only 2 samples? Or fall back to base?

**PRD coverage:** None.

**Recommendation:** Add per-voice minimum sample thresholds to config:
```yaml
voices:
  blog:
    applyTo: ["posts/**"]
    minSamples: 5  # Don't generate delta unless 5+ samples classified
  docs:
    applyTo: ["docs/**"]
    minSamples: 3
```

---

### 2. Mid-Session Classification Changes

**Scenario:** User ingests 5 new blog posts mid-project, re-runs `/interfluence analyze`.

**Expected behavior:**
- Preserve existing manual classification overrides?
- Reclassify everything from scratch?
- Only classify new samples?

**PRD coverage:** None.

**Recommendation:** Add to F3 acceptance criteria:
- Preserve samples with manual `tags` overrides
- Only auto-classify samples with no tags or `tags: []`

---

### 3. Voice Profile Conflicts During Collaborative Editing

**Scenario:** Two users working in same project (via git), both refine voice profiles, merge conflict in `voice-profile.md`.

**Expected behavior:** Merge tooling? Conflict resolution guide?

**PRD coverage:** None. (Not necessarily in scope, but should be documented as a known limitation.)

**Recommendation:** Add to non-goals: "Multi-user voice profile conflict resolution (use git merge tools)."

---

### 4. Empty Delta Files

**Scenario:** User's blog voice is identical to base (no overrides needed).

**Expected behavior:**
- Create empty `voices/blog.md`?
- Skip creating the file?
- Create file with explanatory comment?

**PRD coverage:** F2 line 31 says `profile_list` returns `["base", "blog", "docs"]` based on files in `voices/` dir — implying empty files would not be listed.

**Recommendation:** Don't create empty deltas. If classification finds no differences, don't write a voice file. Update `profile_list` to return only base + files that exist.

---

### 5. Glob Pattern Escaping

**Scenario:** User has file path like `posts/[draft]/my-post.md` (square brackets are glob special chars).

**Expected behavior:** Pattern `posts/[draft]/**` should match literally, not as character class.

**PRD coverage:** None. Glob library choice not specified.

**Recommendation:** Document glob library (likely `minimatch` in Node) and escaping rules in config schema comments.

---

### 6. Learning Log Context Tag Persistence

**Scenario:** User edits a file, hook logs it as `CONTEXT:blog`. User later changes voice config patterns. Old logs still have stale `blog` tag.

**Expected behavior:**
- Re-resolve context from file path during `/interfluence refine`?
- Trust the original tag?
- Show both and let user pick?

**PRD coverage:** F5 logs context at edit time (line 68), but no handling for config changes.

**Recommendation:** Add to F5 acceptance criteria:
- Refine skill re-resolves context from current config, shows both: "Logged as 'blog', now resolves as 'docs' — use [blog] [docs] [unknown]?"

---

## Flow Analysis

### Happy Path: New User, First Multi-Voice Setup

1. User installs interfluence
2. Runs `/interfluence ingest posts/ docs/`
3. Runs `/interfluence analyze`
4. **GAP:** Analyzer auto-classifies, user sees "Profile generated" but no classification results
5. User runs `/interfluence apply posts/new-post.md`
6. **GAP:** No explanation of why "blog" voice was chosen
7. User confused, gives up or asks for help

**Missing transitions:**
- Post-analyze classification summary
- Voice resolution explanation during apply

---

### Error Path: Misclassification

1. User's README is written in personal blog style (common for solo devs)
2. Analyzer classifies it as "blog" (correct style match)
3. Config maps `README.md` to "docs" voice (correct file type)
4. `/interfluence apply README.md` uses docs voice (first-match-wins from config)
5. Output feels wrong (docs voice applied to blog-style content)
6. **DEAD END:** User has no way to fix this. Can't reclassify the sample, can't override voice for one file.

**Missing recovery:**
- Per-file voice override (done: `--voice` flag exists)
- Sample reclassification UI (missing)
- "Does this sound right?" feedback loop (missing)

---

### Cancellation Path: User Wants to Revert to Single Profile

**Scenario:** User tries multi-voice, decides it's too complex, wants single profile back.

**Current PRD:** No exit path.

**Recommendation:** Add `/interfluence merge-voices` command:
- Merges all voice deltas back into base
- Deletes `voices/` directory
- Reverts config to single-profile mode

---

### Degraded Environment: Analyzer Fails to Classify

**Scenario:** Analyzer can't distinguish contexts (all samples are similar), returns all as "unclassified."

**Expected behavior:** Fall back to single base profile? Warn user? Proceed with empty deltas?

**PRD coverage:** F3 line 49 handles "no context diversity" → single base. But what about "attempted classification, all failed"?

**Recommendation:** Add to F3 acceptance criteria:
- If >80% of samples are unclassified, warn user and generate single base profile
- If 20-80% unclassified, generate base + deltas but flag unclassified samples for review

---

## Recommendations Summary

### Must-Fix Before Shipping (Adoption Blockers)

1. **Add classification results UI** — Users must see and correct what the analyzer decided
2. **Document first-match-wins ordering** — Use array syntax or explicit priority field
3. **Add voice resolution transparency** — `--explain` and `--dry-run` flags
4. **Explicit migration flow** — Don't silently change existing users' profiles
5. **Handle `CONTEXT:unknown` learnings** — Refine skill must let users classify them

### Should-Fix for Better UX (Quality of Life)

6. **Add `/interfluence explain-voices`** — Teach users the delta model
7. **Expand compare skill** — Show all voice scores, not just best match
8. **Add minimum sample thresholds** — Don't generate deltas from 1-2 samples
9. **Add `--dry-run` to apply** — Let users test voice resolution without file edits
10. **Add merge-voices exit path** — Let users revert to single profile

### Nice-to-Have (Post-v0.3.0)

11. **Project-wide voice map** — `interfluence map-voices` to preview all files
12. **Sample reclassification UI** — Fix analyzer mistakes without manual YAML editing
13. **Per-voice minimum sample config** — Graceful degradation with uneven corpus
14. **Glob pattern conflict detection** — Warn at config save if patterns overlap

---

## Opportunity Cost Assessment

**Claimed effort (brainstorm line 82-93):** ~65 LOC + 5 prompt updates.

**Actual effort estimate with UX fixes:**
- MCP server changes: ~100 LOC (profile, config, paths)
- Skill updates: ~200 LOC (analyze, apply, new corpus/explain-voices skills)
- Classification UI: ~150 LOC (new corpus management skill)
- Migration flow: ~50 LOC (version detection + user prompt)
- Testing: ~100 LOC (validate delta merging, glob matching, classification accuracy)
- **Total: ~600 LOC** (not counting documentation and user testing)

**Comparison to stated non-goals:**
- Commit message voice (git hook integration) — likely similar effort
- Auto-apply mode changes (F89 integration) — already deferred
- Confidence metrics — could ship partial version (classification confidence only) for <50 LOC

**Is this the highest-value next feature?**

**Alternative user requests** (speculative, since no data provided):
- "Let me import writing samples from Notion" (interkasten integration, brainstorm line 107)
- "Show me before/after diffs when applying voice" (trust-building for new users)
- "Let me set voice preferences without building a corpus" (faster onboarding)

**Recommendation:** If usage data shows single-profile users are satisfied, defer multi-voice until adoption grows. If early adopters are blocked, ship with reduced scope:
- Manual classification only (no auto-classification in v0.3.0)
- Explicit `--voice` flag required (no auto-resolution in v0.3.0)
- Verbose output showing all decisions

Ship the MVP, validate with 10 users, then add auto-classification in v0.4.0.

---

## Final Verdict

**Ship as specified?** No.

**Ship with revisions?** Yes, if:
1. Classification results are visible and editable
2. Voice resolution is transparent (explain mode)
3. Migration is explicit and user-controlled
4. Learning hook uses `CONTEXT:unknown` fallback (not fragile bash glob matching)

**Defer for more research?** Consider it if:
- No usage data showing multi-context need exists
- Early adopter feedback suggests single profile is sufficient
- Effort estimate grows beyond 1-2 weeks of focused dev time

**Core architecture (base + deltas):** Excellent. Ship it.

**UX surface (auto-classification, first-match-wins, migration):** Needs work before users will trust it.

---

## Open Questions for Product Owner

1. **How many current interfluence users write across multiple contexts?** (Instrumentation needed)
2. **What evidence exists that blog/docs are the right two contexts?** (User interviews? Support tickets?)
3. **What is the acceptable classification accuracy threshold?** (80%? 90%? 95%?)
4. **Is multi-voice opt-in or default-on?** (Affects onboarding flow)
5. **What happens if a user has 50 blog posts and 2 READMEs?** (Should docs voice even be generated?)
6. **Who is the target user for v0.3.0?** (Early adopters who tolerate rough edges, or mainstream users who need polish?)

---

## Document Quality Assessment

**Strengths:**
- Clear problem statement (even if not validated)
- Solid technical architecture (delta model)
- Explicit non-goals (scope control)
- Graceful degradation paths (F3 lines 47-49)
- Open questions acknowledged (brainstorm lines 96-102)

**Weaknesses:**
- No user evidence or data
- No UX flows or wireframes
- No error handling or edge case coverage
- No migration plan
- No debugging/transparency tools
- No success metrics or acceptance validation
- Effort estimate too optimistic

**Recommendation:** Treat this as a technical design doc (which it does well) and pair it with a UX spec before implementation.
