# Architecture Review: interfluence Code-Switching PRD

**Reviewed:** 2026-02-18
**Document:** `docs/prds/2026-02-18-interfluence-code-switching.md`
**Reviewer:** Flux Architecture & Design (Sonnet 4.5)
**Focus Areas:** Module boundaries, coupling, design patterns, anti-patterns, unnecessary complexity

---

## Executive Summary

**Overall Assessment:** STRUCTURALLY SOUND with one critical coupling risk and two simplification opportunities.

The PRD proposes a clean delta-over-base voice profile architecture with file-path-based resolution. The core design is architecturally coherent: base voice as invariants, context voices as deltas, merge at apply time. The storage model is simple and the MCP tool surface is minimal.

**Key Findings:**
1. **Critical:** Hook-to-config coupling creates a fragile bash glob-matching layer that bypasses the MCP abstraction (F5)
2. **Opportunity:** Delta merge logic is duplicated across skill and agent contexts without a shared contract
3. **Opportunity:** Config schema extension risks breaking existing `config_save` merge semantics

---

## 1. Boundaries & Coupling

### 1.1 MCP Tool Boundary (CLEAN)

**F1 (Voice-Aware Profile Storage)** correctly extends the MCP tool surface without breaking the existing abstraction:

- `profile_get(projectDir, voice?)` — optional param preserves backward compatibility
- `profile_save(projectDir, content, voice?)` — optional param, creates `voices/` dir lazily
- `profile_list(projectDir)` — new tool, no dependencies on existing tools

**Verified:** `utils/paths.ts` currently has no voice awareness; `getVoiceProfilePath(projectDir)` hardcodes `voice-profile.md`. The PRD proposes a clean extension: `getVoiceProfilePath(projectDir, voice?)` that conditionally returns `voices/${voice}.md` when `voice` is provided. This is single-responsibility path resolution with no leakage into corpus or config tools.

**Risk:** NONE. This is a textbook façade extension.

---

### 1.2 Config Schema Coupling (MODERATE RISK)

**F2 (Config Schema Extension)** adds a `voices` mapping to `config.yaml`:

```yaml
voices:
  blog:
    applyTo: ["posts/**", "blog/**"]
  docs:
    applyTo: ["docs/**", "README.md"]
```

**Current config structure:**

```typescript
export interface interfluenceConfig {
  mode: "auto" | "manual";
  autoApplyTo: string[];
  exclude: string[];
  learnFromEdits: boolean;
}
```

**Problem:** The PRD says "`config_save` accepts voices mapping (merge semantics — partial update)" but the current `config_save` tool uses **per-field optional params**, not a generic object merge:

```typescript
server.tool(
  "config_save",
  {
    mode: z.enum(["auto", "manual"]).optional(),
    autoApplyTo: z.array(z.string()).optional(),
    exclude: z.array(z.string()).optional(),
    learnFromEdits: z.boolean().optional(),
  },
  async ({ projectDir, mode, autoApplyTo, exclude, learnFromEdits }) => {
    // per-field assignment
  }
);
```

Adding `voices` requires either:

**Option A (Type-Safe):** Add a new typed parameter:

```typescript
voices: z.record(z.object({
  applyTo: z.array(z.string())
})).optional()
```

**Option B (Generic):** Accept a raw config object and merge it — **this breaks the existing tool contract** and loses zod validation.

**Recommendation:** Option A. The PRD should explicitly state that `config_save` gets a new `voices` parameter with a zod schema for the nested structure. This maintains the existing pattern and prevents schema drift.

**Impact:** If not specified, implementers may reach for Option B (generic merge) and lose type safety.

---

### 1.3 Hook-to-Config Coupling (HIGH RISK — ANTI-PATTERN)

**F5 (Learning Hook — Context Tagging)** proposes that the bash hook (`hooks/learn-from-edits.sh`) reads the `voices` config and performs glob matching to tag learning log entries with context.

**Current hook behavior:** Reads `config.yaml` with grep to check `learnFromEdits` boolean and `exclude` patterns.

```bash
LEARN_ENABLED=$(grep -E "^learnFromEdits:" "$CONFIG_FILE" | awk '{print $2}')
if echo "$RELATIVE_PATH" | grep -qE "^(CLAUDE\.md|AGENTS\.md|\.interfluence/)"; then
  exit 0
fi
```

**Proposed behavior:** Parse the `voices` config (nested YAML object with array values) and match `$FILE_PATH` against glob patterns in bash.

**Architectural problems:**

1. **Glob matching in bash is fragile:** The PRD proposes `applyTo: ["posts/**", "blog/**"]` — bash globbing doesn't natively handle `**` (recursive glob). You'd need `shopt -s globstar` and careful escaping, or shelling out to a Python/Node script, which breaks the "silent fast hook" contract.

2. **Duplicates resolution logic:** The apply skill will already have voice resolution logic (file path → voice name). The hook would reimplement this in bash, creating two parallel resolution paths that can diverge.

3. **Bypasses the MCP abstraction:** The hook directly parses `config.yaml` instead of calling an MCP tool. This is acceptable for a boolean flag (`learnFromEdits`) but problematic for structured resolution logic.

4. **YAGNI risk:** The PRD's open question #1 asks "Should the learning hook infer context?" This suggests uncertainty. If context tagging in the hook isn't strictly required for F5's acceptance criteria, it's premature complexity.

**Alternative (Simple):** Tag learnings as `CONTEXT:unknown` in the hook, defer resolution to the refine skill:

```bash
# Hook (unchanged except tag format)
cat >> "$LOG_FILE" << ENTRY

--- ${TIMESTAMP} | ${RELATIVE_PATH} | CONTEXT:unknown ---
OLD: ${OLD_STRING}
NEW: ${NEW_STRING}
ENTRY
```

Then during `/interfluence refine`, Claude resolves the context from the file path using the `config_get` tool and updates the profile accordingly.

**Recommendation:** Remove context inference from F5. Keep the hook simple and stateless. Let the refine skill (which already has access to the full MCP toolset and voice resolution logic) handle context classification at review time.

**Impact:** Prevents bash glob-matching fragility and eliminates a duplicated resolution path.

---

### 1.4 Skill-to-MCP Boundary (CLEAN)

**F4 (Apply Skill — Voice Resolution)** correctly uses MCP tools for all data access:

1. Read `config_get` to retrieve the `voices` mapping
2. Match file path against patterns (in TypeScript skill context, not bash)
3. Call `profile_get(projectDir, "base")` to load base
4. Call `profile_get(projectDir, "blog")` to load delta
5. Merge and apply

**Risk:** NONE. This is the correct layer for voice resolution logic.

---

## 2. Pattern Analysis

### 2.1 Delta Merge Pattern (DESIGN RISK — NO SHARED CONTRACT)

**The PRD specifies merge semantics in prose:**

> "Merged profile = base sections + delta override sections (delta wins per-section)"

But there's no schema or interface that enforces what a "section" is. Voice profiles are freeform markdown. The current format (from AGENTS.md) is:

```
## Overview
[prose]

## Sentence Structure
[prose]

## Vocabulary & Diction
[prose]

## Tone & Voice
[prose]
```

**How does the delta override work?**

**Option A (Heading-based merge):** Parse both profiles as markdown, identify H2 sections, delta sections replace base sections with the same heading.

**Option B (Full replacement):** Delta profile replaces the entire base (no merge). This contradicts the "delta" concept.

**Option C (Append-only):** Delta sections are appended to base sections. This doesn't match "delta wins."

**Problem:** The PRD doesn't specify the merge algorithm, and there's no code reference for it. This is a **hidden complexity point** — markdown section merging is nontrivial (requires parsing, heading normalization, handling missing sections).

**Where is the merge implemented?**

- **F3 (Voice Analyzer)** generates deltas: "Per-context deltas contain only sections that differ from the base"
- **F4 (Apply Skill)** consumes the merged profile: "Merged profile = base sections + delta override sections"

So the analyzer generates deltas, but the apply skill performs the merge. Neither has a shared specification.

**Recommendation:**

1. **Define the merge contract explicitly in the PRD:** "A section is defined as a markdown H2 heading and all content until the next H2. Delta sections with matching headings replace base sections. Delta sections with new headings are appended. Base sections not in the delta are preserved."

2. **Specify where the merge happens:** Should the `profile_get` tool perform the merge server-side (when `voice` is provided, return the merged content)? Or should the apply skill call `profile_get("base")` and `profile_get("blog")` separately and merge in the skill prompt? The PRD says "load the merged (base + delta) profile" but doesn't specify the implementation boundary.

3. **Prevent drift between analyzer and apply:** If the analyzer generates deltas using heading-based sections, but the apply skill merges using a different rule, they'll diverge. Codify the section definition in the voice-analyzer agent prompt.

**Impact:** Without a shared merge contract, the analyzer may generate deltas that the apply skill can't correctly merge, leading to broken voice application.

---

### 2.2 First-Match-Wins Resolution (CLEAN PATTERN)

**F2** specifies "first-match-wins" for voice resolution. This is a standard pattern (Nginx location blocks, iptables rules, etc.) and has clear semantics: order matters, first match terminates search.

**Risk:** NONE. The pattern is well-understood.

**Implementation note:** The PRD doesn't specify whether the `voices` config is an array (preserving insertion order) or an object (YAML object key order is preserved in js-yaml, but not guaranteed in all parsers). Recommendation: Use a YAML array of objects to make order explicit:

```yaml
voices:
  - name: blog
    applyTo: ["posts/**", "blog/**"]
  - name: docs
    applyTo: ["docs/**", "README.md"]
```

Or rely on YAML 1.2 ordered maps and document that key order matters.

---

### 2.3 Lazy Directory Creation (ANTI-PATTERN RISK)

**F1** says "creating `voices/` dir if needed" when `profile_save` is called with a voice name.

**Current pattern in `utils/paths.ts`:**

```typescript
export function getCorpusDir(projectDir: string): string {
  const dir = join(getinterfluenceDir(projectDir), "corpus");
  if (!existsSync(dir)) {
    mkdirSync(dir, { recursive: true });
  }
  return dir;
}
```

This is lazy directory creation — fine for `corpus/` (populated by user action), but risky for `voices/`.

**Problem:** If `profile_get(projectDir, "blog")` is called but `voices/blog.md` doesn't exist, the current code returns "No voice profile exists yet" (see `profile_get` implementation, line 36-44). But if `voices/` dir doesn't exist, should the tool create it?

**Recommendation:** `profile_save` creates `voices/` dir lazily (as stated). `profile_get` does NOT create dirs. `profile_list` creates `voices/` dir only when listing (so an empty list means "no voices," not "directory doesn't exist").

**Impact:** Clarifies when filesystem state changes occur.

---

### 2.4 Backward Compatibility (CLEAN PATTERN)

**F1** correctly preserves backward compatibility:

- `profile_get(projectDir)` returns `voice-profile.md` (base)
- Existing projects with no `voices/` dir work unchanged

**F2** correctly handles missing `voices` config:

- "Old configs without `voices` key load without error (default: no voices = base only)"

**Risk:** NONE. This follows the standard optional-field-with-default pattern.

---

## 3. Simplicity & YAGNI

### 3.1 Premature Abstraction: `defaultVoice` Config (YAGNI)

**The brainstorm mentions `defaultVoice` in the storage table:**

> "config.yaml schema | Add `voices` mapping, `defaultVoice`"

But the PRD doesn't specify what `defaultVoice` does. The resolution logic is:

1. Match file path against `voices` mapping → return voice name
2. No match → return `null` (base fallback)

**When would `defaultVoice` be used?**

- If you want a non-base fallback? But the entire design assumes base = invariants = correct fallback.
- If you want to override the fallback for specific projects? But why not just add a catch-all pattern to `voices`?

**Recommendation:** Remove `defaultVoice` from the PRD unless there's a concrete use case. The current "no match = base" rule is simple and sufficient.

**Impact:** Reduces config surface area and prevents confusion about fallback precedence.

---

### 3.2 Unnecessary Tool: `profile_list` (BORDERLINE YAGNI)

**F1** adds `profile_list(projectDir)` to return `["base", "blog", "docs"]`.

**Who uses this?**

- The apply skill doesn't need it (it resolves voice from file path or `--voice` flag)
- The analyze skill doesn't need it (it generates voices, not lists them)
- The compare skill *might* use it to show match scores against all voices (PRD open question #3)

**Alternatives:**

- The compare skill can call `profile_get` for each known voice (base + voices from config)
- A `/interfluence status` command can show available voices by reading the config, not listing files

**Recommendation:** Keep `profile_list` if compare skill (#F6) needs it. Otherwise, defer until there's a concrete consumer.

**Impact:** Small. `profile_list` is ~10 LOC and doesn't add coupling. Not worth blocking the PRD, but worth questioning during implementation.

---

### 3.3 Comparative Analysis vs. Classification (COMPLEXITY RISK)

**F3 (Voice Analyzer — Comparative Analysis)** proposes:

1. Classify untagged corpus samples into contexts (blog, docs, unclassified)
2. Extract cross-context invariants as the base
3. Generate per-context deltas

**Step 1 is a classification task.** The PRD says "Analyzer classifies untagged corpus samples" but doesn't specify the classification mechanism:

- **Supervised:** User pre-tags samples, analyzer uses tags as ground truth
- **Unsupervised:** Analyzer clusters samples by similarity, infers context labels
- **Heuristic:** Analyzer matches samples against known corpus sources (e.g., "posts/" → blog, "docs/" → docs)

**Step 2 is a set subtraction task:** What's shared across all contexts?

**Step 3 is a diff task:** For each context, what differs from the invariants?

**Problem:** This is a multi-stage analysis pipeline with fuzzy boundaries. If the analyzer misclassifies a sample (tags a blog post as "docs"), the base profile will be polluted with blog-specific patterns, and the blog delta will be incomplete.

**Fallback cases (F3 acceptance criteria):**

- "With only one context's samples, generates base + that one delta (graceful degradation)"
- "With no context diversity, generates a single base profile (current behavior)"

**These imply the analyzer infers contexts automatically.** But classification accuracy isn't in the acceptance criteria. What if the analyzer can't confidently classify 50% of the corpus? Does it tag them as "unclassified" and exclude them from base extraction? Or force them into a context and risk polluting the base?

**Recommendation:**

1. **Make classification opt-in for MVP:** Require users to manually tag samples during ingest (add a `--context=blog` flag to the ingest skill). The analyzer then uses these tags as ground truth. Defer auto-classification to post-MVP.

2. **OR: Specify classification heuristics explicitly:** "Analyzer classifies samples by matching `corpus-index.yaml`'s `sourcePath` field against the `voices` config's `applyTo` patterns. Samples that don't match any pattern are tagged `unclassified` and excluded from delta generation."

3. **Add acceptance criteria for classification accuracy:** "Analyzer reports classification confidence per sample. If fewer than 3 samples per context, warns user and skips delta generation for that context."

**Impact:** Prevents silent misclassification from degrading voice quality.

---

## 4. Missing Specifications

### 4.1 Migration Path for Existing Profiles

**Open question #2:** "Existing users have a single `voice-profile.md`. Treat it as the base profile automatically (no migration command needed)?"

**Answer:** YES, but the PRD should specify what happens to samples in existing projects:

- Existing `corpus-index.yaml` has samples with `tags: []` (no context)
- When `/interfluence analyze` is run post-upgrade, those samples need classification

**Recommendation:** Add to F3 acceptance criteria: "Analyzer classifies samples with no context tag. Existing samples in upgraded projects are classified on first analyze."

---

### 4.2 Error Handling for Missing Voices

**Scenario:** User runs `/interfluence apply --voice=blog` but `voices/blog.md` doesn't exist.

**What happens?**

- Does `profile_get(projectDir, "blog")` return an error?
- Does the apply skill fall back to base?
- Does it warn the user and ask them to run analyze first?

**Recommendation:** Add to F4 acceptance criteria: "If `--voice=X` is provided but `voices/X.md` doesn't exist, report error: 'Voice "X" not found. Available voices: [list]. Run /interfluence analyze to generate missing voices.'"

---

### 4.3 Refine Skill Integration

**F5** says "Refine skill can filter learnings by context" but the refine skill isn't mentioned in F6 (Skill & Command Updates).

**Question:** Does the refine skill need voice awareness? If learnings are tagged with context, should refining the blog voice only show blog learnings?

**Recommendation:** Add to F6: "`/interfluence refine --voice=blog` filters learnings to blog context and updates `voices/blog.md` only."

---

## 5. Summary of Recommendations

### Must Fix (Blocks Architecture Coherence)

1. **F2:** Specify that `config_save` gets a new `voices` parameter with a zod schema (not a generic merge).
2. **F4:** Define the markdown section merge algorithm explicitly (heading-based merge with replacement semantics).
3. **F5:** Remove context inference from the learning hook. Tag as `CONTEXT:unknown`, resolve in refine skill.

### Should Fix (Prevents Implementation Drift)

4. **F3:** Specify classification mechanism (manual tags vs. heuristic vs. unsupervised) and add accuracy/confidence criteria.
5. **F4:** Add error handling for missing voices when `--voice=X` is provided.
6. **F6:** Specify refine skill voice-filtering behavior.

### Consider (Simplification Opportunities)

7. **F2:** Remove `defaultVoice` config field unless there's a concrete use case.
8. **F3:** Simplify comparative analysis to use manual tags for MVP, defer auto-classification.

---

## 6. Final Assessment

**Structurally sound design with one critical coupling issue and two opportunities for simplification.**

The delta-over-base architecture is correct. The MCP tool boundary is clean. The first-match-wins resolution pattern is standard.

**The primary risk is F5's hook-to-config coupling**, which creates a bash glob-matching layer that duplicates resolution logic and bypasses the MCP abstraction. Removing context inference from the hook eliminates this fragility.

**The secondary risk is F4's undefined merge contract**, which could lead to drift between the analyzer (delta generator) and apply skill (delta consumer). Codifying the section definition and merge algorithm prevents this.

**The tertiary risk is F3's unspecified classification mechanism**, which could silently degrade voice quality if samples are misclassified. Requiring manual tags for MVP or specifying heuristics addresses this.

With these fixes, the PRD is ready for implementation.
