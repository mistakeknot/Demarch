# Data Correctness Review: interfluence Code-Switching PRD

**PRD:** `docs/prds/2026-02-18-interfluence-code-switching.md`
**Reviewer:** Julik
**Date:** 2026-02-18

## Summary

This PRD adds context-aware voice profiles to interfluence through three new data files (voices/*.md, config.voices mapping, corpus-index.yaml context tags). The design has **4 high-severity data consistency issues** and **3 moderate-severity race/schema issues** that can silently corrupt user data or produce stale reads during normal operation.

The plugin is single-user (one Claude Code session at a time), so concurrent write contention is not a concern. However, **multi-step transactions spanning tool calls with no atomicity** create inconsistency windows, and **missing validation/reconciliation** allows config and filesystem to diverge permanently.

## Critical Findings (Must Fix Before Implementation)

### C1: Orphaned Voice Files (High Severity)

**Issue:** The PRD specifies that `profile_list` returns `["base", ...voices_from_config, ...files_in_voices_dir]` but does not define reconciliation semantics when these disagree.

**Failure scenario:**
1. User runs `/interfluence analyze`, which calls `profile_save(projectDir, content, "blog")` → writes `voices/blog.md`
2. Analyzer also updates config via `config_save({ voices: { blog: { applyTo: ["posts/**"] } } })`
3. These are **two separate tool calls with no transaction boundary**
4. If step 2 fails (process crash, context exhaustion, user interrupts), `blog.md` exists but is not in config
5. Apply skill reads config to resolve voice → `blog` not in config → falls back to base
6. User has a voice file that will never be used, and no indication it exists (unless they manually list the directory)

**Additional failure mode:**
1. User manually edits `config.yaml`, removes `blog` from the `voices` mapping (typo, intent to disable)
2. `voices/blog.md` still exists on disk
3. `profile_list` returns `["base", "blog"]` (because it scans the directory)
4. User applies blog voice with `--voice=blog`, it works (because apply merges base + delta from file)
5. But automatic path resolution never triggers it (because config has no `applyTo` pattern)
6. Config and filesystem are inconsistent, user gets unpredictable behavior

**Why this is high-severity:** Silent stale reads in production. User thinks they're getting context-specific voice, they're not. Or they think a voice is disabled (removed from config), but `--voice=blog` still works.

**Minimal fix:** Define a **single source of truth** and enforce it:

**Option A (config is truth):**
- `profile_list` returns only `base` + voices from config (ignores orphaned files)
- `profile_save(voice)` fails if voice is not in config with error: "Voice 'blog' not in config. Add it to config.voices first."
- Prevents orphans, but makes two-step initialization (write file, add to config) error-prone

**Option B (filesystem is truth, config is just patterns):**
- `analyze` skill writes voice files atomically, then updates config in a second step
- If config update fails, file exists but has no pattern → `profile_list` shows it, user can manually add pattern
- Apply skill treats config as optional: if `voices/blog.md` exists, `--voice=blog` works regardless of config
- Config's `voices` mapping is **only for path resolution**, not existence validation
- Add reconciliation check: if config references a voice that has no file, warn user during `profile_list` or `/interfluence` status

**Recommendation:** **Option B** with a reconciliation warning. Filesystem is persistent truth, config is just routing.

**Implementation checklist:**
- [ ] `profile_save(voice)` creates `voices/` dir and writes file unconditionally (no config check)
- [ ] `profile_get(voice)` reads `voices/{voice}.md` if exists, else error
- [ ] `profile_list()` returns `["base"] + all files in voices/ (without .md extension)`
- [ ] Apply skill: if voice file exists, use it (merge base + delta); if not, error
- [ ] Config schema: `voices` is optional; missing = base-only mode
- [ ] Status command warns: "Config references voice 'blog' but voices/blog.md not found"
- [ ] Status command warns: "Voice file 'docs.md' exists but not in config (won't auto-apply)"

---

### C2: Corpus Tag Update Without Synchronization (High Severity)

**Issue:** F3 specifies that the analyzer "classifies untagged corpus samples into contexts (blog, docs, or unclassified)" and "classification results written back to corpus-index.yaml via existing tags field." This is a **read-modify-write without row-level locking**.

**Failure scenario:**
1. Analyzer reads `corpus-index.yaml`, loads 10 samples with `tags: []`
2. Analyzer classifies samples 1-5 as `blog`, 6-8 as `docs`, 9-10 as `unclassified`
3. User runs `/interfluence ingest new-post.md` in a second session (or same session, different skill run)
4. Ingest calls `corpus_add`, which:
   - Calls `loadCorpusIndex()` → reads current YAML (still has old tags)
   - Appends new sample to `index.samples[]`
   - Calls `saveCorpusIndex()` → **overwrites the YAML file**
5. Analyzer finishes classification, calls `saveCorpusIndex()` with updated tags
6. **Last write wins.** Either the new sample is lost (if analyzer writes second), or the tag updates are lost (if ingest writes second)

**Why this is high-severity:** Silent data loss. User has samples in their corpus that are untagged (so they won't be grouped correctly in next analysis), or they have samples that are missing from the index entirely (orphaned files in `corpus/`).

**Current code evidence:**
```typescript
// corpus.ts, corpus_add
const index = loadCorpusIndex(projectDir);  // Read
index.samples.push(sample);                  // Modify
saveCorpusIndex(projectDir, index);         // Write
```

No locking, no version check, no merge semantics. Pure last-write-wins.

**Why single-user doesn't save you:** Even in a single Claude Code session, skills run sequentially but **operate on snapshots**. If analyzer is a background task (F3 is agent-driven, could be long-running), user can trigger other commands mid-analysis.

**Minimal fix (no locking required):** **Append-only tag log with compaction.**

**New design:**
1. Analyzer does NOT modify `corpus-index.yaml` directly
2. Instead, it writes to `corpus-tags-pending.yaml`:
   ```yaml
   - sampleId: sample-20260211-a3f2
     tags: [blog]
     classifiedAt: 2026-02-18T10:00:00Z
   - sampleId: sample-20260211-b7c1
     tags: [docs]
     classifiedAt: 2026-02-18T10:00:00Z
   ```
3. Next `corpus_list` or `corpus_get_all` reads both files and merges tags (pending overrides index)
4. Refine skill (or a new `corpus_compact` tool) applies pending tags to index atomically:
   ```typescript
   const index = loadCorpusIndex(projectDir);
   const pending = loadPendingTags(projectDir);
   for (const update of pending) {
     const sample = index.samples.find(s => s.id === update.sampleId);
     if (sample) sample.tags = update.tags;
   }
   saveCorpusIndex(projectDir, index);
   deletePendingTags(projectDir);  // Clear pending file
   ```
5. This is safe because compaction is user-triggered (via refine), not automatic

**Alternative fix (simpler, no new file):** **Analyzer only writes voice profiles, never mutates corpus.**

Classification happens in-memory during analysis (to group samples), but tags are NOT persisted. User manually tags samples via `corpus_add --tags blog` when ingesting, or via a new `corpus_tag <id> <tag>` tool.

**Recommendation:** **Alternative fix.** Tags are user intent, not inference. If user wants auto-tagging, they can run a separate classification pass and approve the results before persisting.

**Implementation checklist:**
- [ ] Remove "classification results written back to corpus-index.yaml" from F3
- [ ] Analyzer classifies in-memory to group samples for comparative analysis
- [ ] Classification is shown to user: "I grouped 5 samples as blog-style, 3 as docs-style..."
- [ ] User manually tags via `corpus_add --tags` or new `mcp_interfluence_corpus_tag(sampleId, tags)` tool
- [ ] Next analysis uses existing tags + in-memory classification if tags are missing

---

### C3: Config Schema Migration (Moderate Severity)

**Issue:** F2 adds a new `voices` key to `config.yaml` with "old configs without voices key load without error (default: no voices = base only)" but does not specify **forward compatibility** (what happens if a newer version with voices is read by an older plugin version).

**Current code:**
```typescript
// profile.ts, config_get
if (existsSync(configPath)) {
  config = yaml.load(readFileSync(configPath, "utf-8")) as interfluenceConfig;
} else {
  config = DEFAULT_CONFIG;
}
```

**TypeScript cast assumes the YAML structure matches the interface.** If YAML has `voices: { blog: { applyTo: [...] } }` but `interfluenceConfig` interface doesn't have that field (old plugin version), **yaml.load silently discards it** (or includes it as unknown property).

**Failure scenario:**
1. User updates to v0.2.0 (with voices), runs `/interfluence analyze`, config.yaml gains `voices` key
2. User downgrades to v0.1.0 (plugin cache issue, manual rollback, whatever)
3. Old plugin reads config, **silently ignores `voices` key**, uses base profile only
4. User edits config to change a voice pattern, plugin never reads it (no tool exists)
5. User upgrades back to v0.2.0, their manual edits are lost (because old plugin's `config_save` overwrote without the voices key)

**Why this is moderate (not high):** Only affects users who downgrade or run mixed versions. But **data loss is silent** (config edits are dropped).

**Minimal fix:** **Schema versioning.**

```yaml
# config.yaml
schemaVersion: 2
mode: auto
voices:
  blog:
    applyTo: ["posts/**"]
```

```typescript
interface interfluenceConfig {
  schemaVersion?: number;  // Optional for v1 backward compat
  mode: "auto" | "manual";
  voices?: Record<string, { applyTo: string[] }>;  // Optional, added in v2
  // ...
}

const CURRENT_SCHEMA_VERSION = 2;

function loadConfig(projectDir: string): interfluenceConfig {
  const configPath = getConfigPath(projectDir);
  if (!existsSync(configPath)) {
    return { ...DEFAULT_CONFIG, schemaVersion: CURRENT_SCHEMA_VERSION };
  }

  const raw = yaml.load(readFileSync(configPath, "utf-8")) as any;
  const version = raw.schemaVersion ?? 1;

  if (version > CURRENT_SCHEMA_VERSION) {
    throw new Error(
      `Config schema version ${version} is newer than this plugin (${CURRENT_SCHEMA_VERSION}). Update interfluence plugin.`
    );
  }

  // Migrate v1 → v2
  if (version === 1) {
    raw.voices = {};
    raw.schemaVersion = 2;
  }

  return raw as interfluenceConfig;
}

function saveConfig(projectDir: string, config: interfluenceConfig): void {
  config.schemaVersion = CURRENT_SCHEMA_VERSION;
  writeFileSync(getConfigPath(projectDir), yaml.dump(config), "utf-8");
}
```

**Implementation checklist:**
- [ ] Add `schemaVersion` to `interfluenceConfig` interface (optional, default 1)
- [ ] `config_get` checks version, migrates if needed, errors if too new
- [ ] `config_save` always writes current schema version
- [ ] Document migration path in CHANGELOG

---

### C4: Voice Profile Merge Semantics Undefined (Moderate Severity)

**Issue:** F4 specifies "Merged profile = base sections + delta override sections (delta wins per-section)" but does not define what a "section" is or how merge conflicts are resolved.

**Ambiguity:**
- Is a section a markdown H2 (`## Sentence Structure`)?
- What if base has `## Vocabulary & Diction` and delta has `## Vocabulary`? Do these merge or conflict?
- What if delta has a new section that base doesn't have (e.g., `## Commit Message Style`)? Is this appended?
- What if base and delta both have the same H2, but different H3 subsections? Section-level merge or text-level merge?

**Failure scenario:**
1. User has base profile with `## Tone & Voice` containing 3 paragraphs of guidance
2. Blog voice delta has `## Tone & Voice` with 1 paragraph ("be more casual")
3. Apply skill merges: does delta replace the entire section (losing 2 paragraphs of guidance), or does it append?
4. If replacement, user loses cross-context guidance
5. If append, user gets contradictory guidance ("be formal" from base + "be casual" from delta)

**Why this is moderate:** Doesn't corrupt data files, but produces wrong output (voice mismatch). User will notice, but may not understand why.

**Minimal fix:** **Define strict merge semantics in PRD.**

**Recommended semantics (section-level replace):**
```markdown
Base profile:
## Sentence Structure
Base guidance here.

## Tone & Voice
Base tone guidance.

Delta (blog):
## Tone & Voice
Blog-specific tone override.

## Cultural References
Blog-specific references.

Merged result (for blog context):
## Sentence Structure
Base guidance here.  ← Inherited from base (delta has no override)

## Tone & Voice
Blog-specific tone override.  ← Delta replaces base section entirely

## Cultural References
Blog-specific references.  ← New section from delta, appended
```

**Implementation:**
```typescript
function mergeProfiles(base: string, delta: string): string {
  const baseSections = parseMarkdownSections(base);   // { "Sentence Structure": "...", ... }
  const deltaSections = parseMarkdownSections(delta);

  const merged = { ...baseSections };  // Start with base
  for (const [heading, content] of Object.entries(deltaSections)) {
    merged[heading] = content;  // Delta overrides or adds
  }

  return sectionsToMarkdown(merged);
}

function parseMarkdownSections(md: string): Record<string, string> {
  const sections: Record<string, string> = {};
  const lines = md.split("\n");
  let currentHeading: string | null = null;
  let currentContent: string[] = [];

  for (const line of lines) {
    if (line.startsWith("## ")) {
      if (currentHeading) {
        sections[currentHeading] = currentContent.join("\n").trim();
      }
      currentHeading = line.slice(3).trim();
      currentContent = [];
    } else if (currentHeading) {
      currentContent.push(line);
    }
  }

  if (currentHeading) {
    sections[currentHeading] = currentContent.join("\n").trim();
  }

  return sections;
}
```

**Implementation checklist:**
- [ ] Define section = H2-delimited block (everything from `## Heading` until next `## or EOF`)
- [ ] Delta section with same H2 as base → replace base section entirely
- [ ] Delta section with new H2 → append to merged profile
- [ ] Order: base sections first (in original order), then delta-only sections (in delta order)
- [ ] Document in F4 acceptance criteria and in apply skill implementation notes

---

## Moderate Issues (Should Fix)

### M1: Learning Hook Context Tag Collision (Moderate)

**Issue:** F5 specifies learning log entries gain context tag: `--- TIMESTAMP | PATH | CONTEXT:blog ---`. But F5 also says "No match → tag as CONTEXT:base".

**Problem:** If user edits `posts/draft.md` and the hook infers `CONTEXT:blog`, but then user removes the `blog` voice from config before running `/interfluence refine`, the refine skill will see entries tagged `CONTEXT:blog` but no `blog` voice exists.

**Failure mode:** Refine skill crashes or silently drops those learnings.

**Fix:** Learning log is append-only. Context tags are **immutable snapshots of routing state at log time**. If a voice is deleted later, refine skill should warn: "Found 3 learnings tagged CONTEXT:blog, but blog voice no longer exists. Apply to base?"

**Implementation checklist:**
- [ ] Refine skill validates context tags against current voice list
- [ ] If mismatch, prompt user: "Apply blog-context learnings to base, or skip?"
- [ ] Do not silently drop or error

---

### M2: Analyzer Agent Long-Running Failure (Low-Moderate)

**Issue:** F3 specifies analyzer is an agent (Opus, deep analysis). If analysis takes 2 minutes and user's context exhausts mid-run, **partial results are lost** (no checkpointing).

**Failure mode:**
1. User has 50 samples, 100k words
2. Analyzer starts comparative analysis, classifies 40 samples, begins generating base profile
3. Context exhaustion kills the session
4. No voice profiles written (profile_save never called)
5. User reruns `/interfluence analyze`, starts from scratch

**Fix (low-priority, post-MVP):** Checkpoint progress.

```typescript
// Analyzer writes intermediate state
await profile_save(projectDir, partialBaseProfile, "__checkpoint_base");
await profile_save(projectDir, partialBlogDelta, "__checkpoint_blog");

// On restart, check for checkpoints:
const checkpoints = profile_list(projectDir).filter(v => v.startsWith("__checkpoint_"));
if (checkpoints.length > 0) {
  // Resume from checkpoint
}
```

Not critical for MVP (analysis is user-triggered, they can retry), but worth noting.

---

### M3: Glob Pattern First-Match Ambiguity (Low)

**Issue:** F2 specifies "first-match-wins: voices checked in config order" but YAML dicts are **unordered** in the spec (though js-yaml preserves insertion order in practice).

**Problem:** User writes:
```yaml
voices:
  blog:
    applyTo: ["posts/**"]
  docs:
    applyTo: ["**/*.md"]
```

For file `posts/new-post.md`, both patterns match. Does `blog` win (because it's listed first), or `docs` (because `**/*.md` is more general)?

**Fix:** Specify iteration order explicitly.

**Recommendation:** Use an array instead of a dict to guarantee order:

```yaml
voices:
  - name: blog
    applyTo: ["posts/**"]
  - name: docs
    applyTo: ["docs/**/*.md"]
  - name: base
    applyTo: ["**/*"]  # Catch-all, last
```

Or document: "Order is undefined if using dict syntax. Use array syntax for deterministic matching."

**Implementation checklist:**
- [ ] Document iteration order in F2 acceptance criteria
- [ ] Test case: overlapping patterns, verify first-match
- [ ] Consider array syntax for clarity (breaking change, decide now)

---

## Missing Validation & Invariants

### V1: Voice Name Validation

**Missing:** No constraints on voice names. User could create voice named `"../../etc/passwd"` or `"blog.md"` (with extension).

**Risk:** Path traversal, filename collisions, confusing UX.

**Fix:**
```typescript
function validateVoiceName(name: string): void {
  if (name === "base") throw new Error("'base' is reserved");
  if (name.includes("/") || name.includes("\\")) throw new Error("Voice name cannot contain path separators");
  if (name.includes(".")) throw new Error("Voice name cannot contain dots");
  if (!/^[a-z0-9-]+$/.test(name)) throw new Error("Voice name must be lowercase alphanumeric + hyphens only");
}
```

Call this in `profile_save(voice)` before writing.

---

### V2: Corpus Index Integrity Check

**Missing:** No validation that every sample in `corpus-index.yaml` has a corresponding file in `corpus/`, or vice versa.

**Risk:** Orphaned files (file exists, not in index) or dangling references (index entry, file deleted).

**Fix:** Add `corpus_verify` tool or make `corpus_list` show warnings:

```
Corpus: 10 samples, 5000 words

Warnings:
- sample-123.md exists in corpus/ but not in index (orphaned)
- sample-456 in index but file missing (dangling reference)
```

---

## Testing Recommendations

### T1: Filesystem-Config Divergence Test

1. Create voice file `voices/blog.md`
2. Do NOT add to config
3. Run `profile_list` → should return `["base", "blog"]` (file exists)
4. Run apply with `--voice=blog` → should work (file is truth)
5. Run apply on `posts/new.md` (matching hypothetical blog pattern) → should use base (no config pattern)

### T2: Tag Update During Ingest

1. Start analyzer (background task, slow)
2. Mid-analysis, run `corpus_add new-sample.md`
3. Analyzer completes, verify new sample is still in index
4. Verify tags are applied to old samples

(If using append-only fix, this should pass. If using current RMW approach, this will fail.)

### T3: Schema Downgrade

1. Create config with v2 schema (voices key)
2. Manually edit `schemaVersion: 3` (future version)
3. Run `config_get` → should error with "schema too new" message
4. Verify config file is not corrupted

### T4: Voice Merge

1. Create base with `## Sentence Structure` and `## Tone & Voice`
2. Create blog delta with `## Tone & Voice` (different content) and `## Cultural References`
3. Apply to a file with `--voice=blog`
4. Verify merged profile has:
   - Base's `Sentence Structure` section
   - Blog's `Tone & Voice` section (not base's)
   - Blog's `Cultural References` section

---

## Risk Assessment

| Issue | Severity | Likelihood | Impact | User-Visible? | Data Loss? |
|-------|----------|------------|--------|---------------|------------|
| C1: Orphaned voice files | High | Medium | Stale reads, silent voice mismatch | No (silent) | No (stale) |
| C2: Corpus tag RMW race | High | Low-Med | Lost samples or tags | Yes (missing samples) | Yes |
| C3: Config schema forward compat | Moderate | Low | Config edits lost on downgrade | Yes (on downgrade) | Yes |
| C4: Merge semantics undefined | Moderate | High | Wrong voice applied | Yes (output wrong) | No |
| M1: Learning context tag orphan | Moderate | Low | Learnings dropped or misapplied | Yes (if voice deleted) | No |
| M2: Analysis checkpoint | Low | Low | Wasted work on retry | Yes (time cost) | No |
| M3: Glob match order | Low | Medium | Wrong voice auto-selected | Yes | No |

**Highest priority:** C2 (tag update race), C1 (orphaned files), C4 (merge semantics).

---

## Recommended Changes to PRD

### F1: Voice-Aware Profile Storage

**Add:**
- `getVoiceProfilePath(projectDir, voice?)` implementation detail:
  - If `voice` is `undefined` or `"base"`, return `.interfluence/voice-profile.md`
  - If `voice` is a string, return `.interfluence/voices/{voice}.md`
  - Validate voice name (alphanumeric + hyphens, no dots or slashes)
- `profile_list(projectDir)` returns `["base"] + all filenames in voices/ (without .md extension, sorted alphabetically)`
- Filesystem is source of truth. Config is routing only. Orphaned files (in voices/ but not in config) are valid but won't auto-apply.

### F2: Config Schema Extension

**Add:**
- Config schema is versioned. Current version is 2. Version 1 is legacy (no voices key).
- `config_get` migrates v1 → v2 on read (adds empty `voices: {}`).
- `config_get` errors if schema version > 2 (future version, incompatible).
- `config_save` always writes `schemaVersion: 2`.
- Voice iteration order for glob matching is **insertion order** (js-yaml preserves this for dicts). Document this or use array syntax for explicitness.

### F3: Voice Analyzer

**Remove:**
- "Classification results written back to corpus-index.yaml via existing tags field"

**Replace with:**
- Analyzer classifies samples in-memory during analysis.
- Classification is shown to user for review: "I grouped 5 samples as blog-style based on mentions of 'users', 'shipped', 'this week'..."
- Tags are NOT automatically persisted. User manually tags via `corpus_add --tags` when ingesting.
- Future: add `corpus_tag(sampleId, tags)` tool for batch tagging after analysis.

### F4: Apply Skill

**Add:**
- Merge semantics are **section-level replacement**, where section = H2-delimited block.
- Delta sections with same H2 as base → replace base section entirely.
- Delta sections with new H2 → append to merged profile.
- Final order: base sections (original order), then delta-only sections (delta order).
- If voice file not found, error (do not fall back to base silently). User must use `--voice=base` explicitly.

### F5: Learning Hook

**Add:**
- Context tags are immutable snapshots. If a voice is deleted after logging, refine skill prompts user: "Apply 3 blog-context learnings to base, or skip?"
- Learning log format: `--- TIMESTAMP | PATH | CONTEXT:blog ---` (context is resolved at log time, not refine time).

---

## Open Questions (from PRD)

### Q1: Learning Hook Config Access

**PRD says:** "The shell hook currently reads config.yaml with basic grep. Adding voice resolution (glob matching) in bash may be fragile. Consider: tag as CONTEXT:unknown and let the refine skill resolve context at review time."

**Julik's take:** Agree. Shell hooks should be dumb and fast. Glob matching in bash is brittle (especially with `**` recursive globs, which require bash 4+ and `shopt -s globstar`).

**Recommendation:**
- Hook tags as `CONTEXT:unknown` always (or omits context tag entirely)
- Refine skill resolves context from path at review time using config's current voice patterns
- This also solves M1 (context tag orphan issue) — no tags, no orphans

**Updated F5:**
- Hook logs: `--- TIMESTAMP | PATH ---` (no context tag)
- Refine skill resolves context per entry using current config
- If path doesn't match any pattern, treated as base context

---

## Conclusion

This PRD has a solid conceptual design (filesystem as truth, config as routing), but the implementation details have **4 critical gaps** that will cause silent data inconsistency or loss in normal use:

1. **Orphaned voice files** (config/filesystem disagree, no reconciliation)
2. **Tag update race** (read-modify-write without locking)
3. **Schema migration** (forward compatibility undefined)
4. **Merge semantics** (section-level vs text-level unclear)

All four are fixable with the proposed changes above. None require architectural changes, just explicit semantics and validation in the MCP tools.

**Recommendation: Do not implement until C1-C4 are resolved in the PRD.** Otherwise, users will hit data corruption in normal workflows (especially C2), and fixing it post-launch requires migration scripts and user intervention.

The single-user assumption holds for concurrency, but **multi-step transactions without atomicity** still create inconsistency windows. Append-only logs and "filesystem is truth" semantics are the right defensive patterns here.
