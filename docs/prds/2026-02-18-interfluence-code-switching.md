# PRD: interfluence Code-Switching — Context-Aware Voice Profiles

**Brainstorm:** `docs/brainstorms/2026-02-18-interfluence-code-switching-brainstorm.md`
**Reviews:** `docs/research/review-prd-architecture.md`, `docs/research/review-prd-data-correctness.md`, `docs/research/review-interfluence-code-switching-ux-product.md`

## Problem

A single flat voice profile averages across writing registers, producing output that sounds wrong in every context — too casual for docs, too stiff for blog posts. Users naturally code-switch and need their AI writing assistant to match the right voice to each context.

## Solution

Add context-aware voice profiles to interfluence. A base profile captures cross-context authorial DNA (invariants), while named sub-profiles (deltas) override specific sections for each context. Voice resolution is automatic via file path patterns, with manual override available.

**Design invariant:** Filesystem is source of truth for voice existence. Config is routing only (maps glob patterns to voices for auto-resolution). A voice file can exist without config routing; config routing without a file produces a warning.

## Features

### F1: Voice-Aware Profile Storage (MCP Server)

**What:** Extend `profile_get`/`profile_save` with an optional `voice` parameter and add a new `profile_list` tool. Store context profiles in a `voices/` subdirectory.

**Acceptance criteria:**
- [ ] `profile_get(projectDir)` returns base profile (backward compatible)
- [ ] `profile_get(projectDir, "blog")` returns `.interfluence/voices/blog.md`
- [ ] `profile_save(projectDir, content, "blog")` writes to `voices/blog.md`, creating `voices/` dir if needed — no config check required (filesystem is truth)
- [ ] `profile_list(projectDir)` returns `["base", ...files_in_voices_dir]` (scans filesystem, not config)
- [ ] Existing single-profile projects work unchanged (base = `voice-profile.md`)
- [ ] `utils/paths.ts` gains `getVoiceProfilePath(projectDir, voice?)` resolver
- [ ] Voice name validation: alphanumeric + hyphens only, max 32 chars

### F2: Config Schema Extension

**What:** Add a `voices` array to `config.yaml` that maps voice names to glob patterns, with first-match-wins resolution order. Array syntax guarantees ordering.

**Acceptance criteria:**
- [ ] Config schema supports ordered array:
  ```yaml
  voices:
    - name: blog
      applyTo: ["posts/**", "blog/**"]
    - name: docs
      applyTo: ["docs/**", "README.md"]
  ```
- [ ] `config_get` returns voices array
- [ ] `config_save` accepts voices array (replaces entire voices array, not merge — avoids ordering ambiguity)
- [ ] Resolution function: given a file path, iterates voices array in order, returns first matching voice name or `null` (base fallback)
- [ ] First-match-wins: voices checked in array order (guaranteed by array syntax)
- [ ] Old configs without `voices` key load without error (default: no voices = base only)
- [ ] Reconciliation warning: if config references a voice name with no corresponding `voices/{name}.md` file, `profile_list` includes a warning

### F3: Voice Analyzer — Comparative Analysis

**What:** Update the voice-analyzer agent to perform comparative analysis: group corpus samples by context, extract cross-context invariants as the base, and generate per-context deltas.

**Acceptance criteria:**
- [ ] Analyzer classifies untagged corpus samples into contexts (blog, docs, or unclassified) in-memory during analysis
- [ ] Classification is NOT persisted to corpus-index.yaml — classification happens fresh each analyze run (avoids stale tags, race conditions on read-modify-write)
- [ ] Analyzer presents classification summary to user before generating profiles: "Found 12 blog samples, 5 docs samples, 3 unclassified"
- [ ] Base profile generated from cross-context invariants only (not a blended average)
- [ ] Per-context deltas contain only H2 sections that differ from the base
- [ ] With only one context's samples, generates base + that one delta (graceful degradation)
- [ ] With no context diversity, generates a single base profile (current behavior)
- [ ] Don't generate empty deltas — if a context has no differences from base, skip the voice file

### F4: Apply Skill — Voice Resolution

**What:** Update the apply skill to resolve which voice to use from file path or explicit `--voice` flag, load the merged (base + delta) profile, and apply it.

**Merge contract:** Profiles are markdown with H2 (`##`) section delimiters. Merge algorithm:
1. Parse base into H2-keyed sections (section title → content)
2. Parse delta into H2-keyed sections
3. For each delta section: replace matching base section (title match) or append if new
4. Concatenate remaining base sections (those not overridden)

**Acceptance criteria:**
- [ ] When applying to a file, infer voice from file path using config's `voices` array (first match wins)
- [ ] `--voice=blog` overrides path inference
- [ ] `--voice=blog` works if `voices/blog.md` exists, regardless of config routing
- [ ] No match → use base profile only
- [ ] Merged profile = base H2 sections + delta H2 override sections (delta wins per-section-title)
- [ ] Skill reports which voice was used and why: "Applied blog voice to posts/new-post.md (matched pattern 'posts/**')"

### F5: Learning Hook — Context Tagging

**What:** Update the learn-from-edits hook to tag learning log entries with context. Hook tags as `CONTEXT:unknown`; the refine skill resolves context at review time.

**Rationale (resolved from Open Question #1):** Glob matching in bash is fragile and bypasses the MCP abstraction. False negatives (`unknown`) are recoverable in the refine skill; false positives (wrong context from buggy bash matching) would corrupt the learning stream.

**Acceptance criteria:**
- [ ] Hook always tags as `CONTEXT:unknown` — no config reading or glob matching in bash
- [ ] Log entry format: `--- TIMESTAMP | PATH | CONTEXT:unknown ---`
- [ ] Refine skill resolves `unknown` entries by reading current config and matching file path → context
- [ ] Refine skill presents unresolved entries to user: "3 learnings from unknown contexts — assign them?"
- [ ] If config changes after logging, refine skill uses current config (not stale log tag)

### F6: Skill & Command Updates

**What:** Update analyze, compare, and command router skills for multi-voice awareness.

**Acceptance criteria:**
- [ ] `/interfluence analyze` triggers comparative analysis (F3 flow)
- [ ] `/interfluence compare` shows match scores for all voices with ranking: "blog (85%), docs (60%), base (72%)"
- [ ] `/interfluence` command help mentions voice-related options
- [ ] `/interfluence apply --voice=<name>` documented in command router

## Non-goals

- Commit message voice (needs git hook integration)
- Slack voice (needs interslack integration)
- Composable layers (Option C — only if two voices proves insufficient)
- Profile export/import across projects
- Confidence metrics per context
- Auto-apply mode changes (auto mode + voice resolution is future work)
- Classification persistence to corpus-index.yaml (classification is ephemeral, happens fresh each analyze)
- Multi-user voice profile conflict resolution (use git merge tools)
- `--dry-run` / `--explain` flags for apply (post-MVP diagnostic tooling)
- `/interfluence explain-voices` command (post-MVP, delta model education)
- `/interfluence merge-voices` revert command (post-MVP escape hatch)

## Dependencies

- interfluence MCP server (TypeScript, esbuild bundle)
- Existing corpus with `tags` field in schema (used for manual tagging only, not auto-classification)
- Voice-analyzer agent (Opus model)

## Resolved Questions

1. **Learning hook config access** — Resolved: hook tags `CONTEXT:unknown`, refine skill resolves context using current config at review time. No glob matching in bash.

2. **Corpus tag persistence** — Resolved: classification is in-memory only during analyze. No read-modify-write on corpus-index.yaml. Avoids race conditions and stale tags.

3. **Source of truth** — Resolved: filesystem (voices/ directory) is truth for voice existence. Config is routing only (glob patterns for auto-resolution). Orphaned files are fine; orphaned config entries produce warnings.

4. **Config ordering** — Resolved: array syntax (not object keys) guarantees first-match-wins ordering. YAML object key order is implementation-defined; arrays are ordered by spec.

## Open Questions

1. **Bundle rebuild** — Server changes require `esbuild` bundle rebuild and plugin reinstall. Plan for this in execution.

2. **Migration UX** — Existing single-profile users: treat `voice-profile.md` as base automatically (no migration needed). But first `/interfluence analyze` with diverse corpus should explain what's happening: "I'll split your profile into base + context voices." Exact UX TBD during implementation.
