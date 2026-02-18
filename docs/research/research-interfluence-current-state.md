# interfluence Current State Research
**Date:** 2026-02-18
**Purpose:** Understand current architecture for multi-voice/context-aware profile support

## Executive Summary

interfluence is a voice profile plugin for Claude Code that analyzes writing corpora and adapts AI-generated text to match a user's style. Current architecture is **single-profile-per-project** with a clear prose-based voice profile format. The codebase shows explicit plans for **context-specific multi-voice support** (blog vs commit vs PRD) deferred to post-MVP. Key integration points for multi-voice are: profile storage/retrieval, corpus tagging, config schema, and the voice-analyzer agent prompt.

**Critical finding:** The architecture is well-positioned for multi-voice extension. All profile operations go through two MCP tools (`profile_get`/`profile_save`), corpus samples already support tags, and the config system is extensible. No fundamental refactoring needed.

---

## 1. Profile Management (`server/src/tools/profile.ts`)

### Current Implementation

**Profile Storage:**
- Single file: `.interfluence/voice-profile.md`
- Plain markdown, human-readable prose format
- Path resolution: `getVoiceProfilePath(projectDir)` → `${projectDir}/.interfluence/voice-profile.md`

**MCP Tools:**

```typescript
profile_get(projectDir: string)
  → Returns voice-profile.md content as text
  → Returns "no profile exists" message if file missing

profile_save(projectDir: string, content: string)
  → Writes full voice-profile.md content
  → Used by analyze and refine skills
```

**Key Design Choice:**
- Prose profiles, not numeric parameters
- Rationale: "Claude follows 'uses em-dashes for asides' better than 'punctuation_variety: 0.8'"
- Profile format includes: Overview, Sentence Structure, Vocabulary, Tone & Voice, Structure Patterns, Cultural References, Anti-Patterns
- Each section has: prose description, direct quotes from corpus, "Do this / Not this" transformation pairs

### Multi-Voice Extension Points

1. **Profile path resolution** — currently hardcoded to single `voice-profile.md`
   - Extension: `getVoiceProfilePath(projectDir, context?: string)`
   - Could resolve to `voice-profile-{context}.md` or subdirectory structure

2. **Profile retrieval** — tools already take arbitrary content
   - Extension: Add optional `context` parameter to `profile_get`/`profile_save`
   - Backward compatible: default context = main/default

3. **Profile merge logic** — currently analyze/refine merge with existing profile
   - Extension: Context-aware merge (don't mix blog and commit learnings)

---

## 2. Corpus Management (`server/src/tools/corpus.ts`, `server/src/utils/corpus-index.ts`)

### Current Schema

**CorpusSample interface:**

```typescript
interface CorpusSample {
  id: string;                    // sample-YYYYMMDDHHMMSS-XXXX
  filename: string;              // stored in .interfluence/corpus/
  source: "file" | "url" | "clipboard" | "inline";
  sourceUrl?: string;
  sourcePath?: string;
  title?: string;
  addedAt: string;               // ISO timestamp
  wordCount: number;
  analyzed: boolean;             // flag for incremental analysis
  tags?: string[];               // ← ALREADY SUPPORTS TAGS
}

interface CorpusIndex {
  samples: CorpusSample[];
}
```

**Storage:**
- Index: `.interfluence/corpus-index.yaml`
- Sample files: `.interfluence/corpus/sample-{id}.md`

**MCP Tools:**
- `corpus_add(projectDir, filePath, title?, tags?)`
- `corpus_add_text(projectDir, text, title, source, sourceUrl?, tags?)`
- `corpus_list(projectDir)` — shows all samples with metadata
- `corpus_get(projectDir, sampleId)` — retrieve single sample
- `corpus_get_all(projectDir)` — concatenated samples for analysis
- `corpus_remove(projectDir, sampleId)`

### Multi-Voice Extension Points

1. **Tags field** — already exists, currently unused for filtering
   - Extension: Tag samples with context (e.g., `["blog", "technical"]`, `["commit-message"]`)
   - Add `context` tag during ingestion based on user hint or file pattern

2. **corpus_get_all filtering** — currently returns all samples
   - Extension: `corpus_get_all(projectDir, filterByTags?: string[])`
   - Enables context-specific corpus retrieval for analysis

3. **analyzed flag** — currently boolean (for incremental analysis feature)
   - Extension: `analyzedFor?: string[]` — track which contexts have consumed this sample
   - Allows multi-context analysis without re-processing

---

## 3. Config System (`server/src/tools/profile.ts`)

### Current Schema

```typescript
interface interfluenceConfig {
  mode: "auto" | "manual";
  autoApplyTo: string[];         // glob patterns
  exclude: string[];             // glob patterns
  learnFromEdits: boolean;
}

const DEFAULT_CONFIG = {
  mode: "manual",
  autoApplyTo: ["*.md", "CHANGELOG*", "docs/**"],
  exclude: ["CLAUDE.md", "AGENTS.md", ".interfluence/**"],
  learnFromEdits: true,
};
```

**Storage:** `.interfluence/config.yaml`

**MCP Tools:**
- `config_get(projectDir)`
- `config_save(projectDir, mode?, autoApplyTo?, exclude?, learnFromEdits?)`

### Multi-Voice Extension Points

1. **Auto-apply context routing** — currently single voice
   - Extension: `autoApplyTo` becomes map of context → patterns
   ```yaml
   mode: auto
   autoApplyContexts:
     blog: ["blog/**/*.md", "posts/**/*.md"]
     commit: ["CHANGELOG.md"]
     docs: ["docs/**/*.md", "README.md"]
   exclude: ["CLAUDE.md", "AGENTS.md"]
   ```

2. **Default context** — needed for backward compatibility
   - Extension: `defaultContext: "main"` or `defaultContext: "blog"`

3. **Learning routing** — currently all edits go to single log
   - Extension: `learnFromEdits: { blog: true, commit: false }` — per-context learning

---

## 4. Voice Analyzer Agent (`agents/voice-analyzer.md`)

### Current Implementation

**Agent role:** Opus-powered literary analyst for deep corpus analysis

**Input:** Calls `corpus_get_all` to retrieve all samples

**Output:** Structured markdown voice profile with sections:
1. Overview (2-3 sentence summary)
2. Sentence Structure (patterns, length, punctuation)
3. Vocabulary & Diction (register, favorites, avoidances)
4. Tone & Voice (relationship to reader, humor, confidence)
5. Structure Patterns (organization, headers, transitions)
6. Cultural References (what they reference and how)
7. Anti-Patterns (what to never do)

**Instructions to agent:**
- Be specific, not generic
- Quote actual text as examples
- Provide "Do this / Not this" transformation pairs
- Note confidence levels if corpus is small
- Respect the human's authentic voice

**Allowed tools:**
- `mcp_interfluence_corpus_get_all`
- `mcp_interfluence_corpus_get`
- `mcp_interfluence_corpus_list`
- `mcp_interfluence_profile_get`
- `mcp_interfluence_profile_save`
- `mcp_interfluence_learnings_get_raw`

### Multi-Voice Extension Points

1. **Corpus filtering instruction** — currently analyzes all samples
   - Extension: "Analyze only samples tagged with `{context}`"
   - Pass context as parameter to agent invocation

2. **Profile merge instructions** — currently "merge new insights with existing profile"
   - Extension: "Merge insights into the `{context}` voice profile, keeping other contexts unchanged"

3. **Context-specific dimensions** — some dimensions vary by context
   - Example: Blog voice may care about "Cultural References", commit voice may not
   - Extension: Context-specific section templates

---

## 5. Apply Skill (`skills/apply.md`)

### Current Implementation

**Trigger phrases:** "apply my voice", "rewrite in my style", "make this sound like me"

**Process:**
1. Load voice profile via `profile_get`
2. Read target content (file or inline text)
3. Rewrite content following profile (preserves facts, transforms voice)
4. Present rewrite with 2-3 specific adaptations noted
5. Apply changes if user approves

**Key constraint:** "NEVER change the meaning or technical accuracy of content"

**Allowed tools:**
- `mcp_interfluence_profile_get`
- `Read`, `Write`, `Edit`

### Multi-Voice Extension Points

1. **Profile selection** — currently loads single profile
   - Extension: "Which voice should I use?" prompt or context inference
   - Context inference from file path (e.g., `blog/*.md` → blog voice)

2. **Voice comparison** — currently single voice application
   - Extension: "Try both blog and docs voices, show side-by-side"

---

## 6. Learn-From-Edits Hook (`hooks/learn-from-edits.sh`)

### Current Implementation

**Hook type:** PostToolUse on `Edit` tool

**Trigger conditions:**
1. Tool is `Edit` (not Write — full file creation less useful for learning)
2. `.interfluence/` dir exists in project tree
3. File not excluded (CLAUDE.md, AGENTS.md, `.interfluence/**`)
4. `learnFromEdits: true` in config

**Behavior:**
- Silently logs `OLD_STRING` → `NEW_STRING` diff to `.interfluence/learnings-raw.log`
- No per-edit Claude call (batched review during `/interfluence refine`)

**Log format:**
```
--- 2026-02-18T10:30:00Z | path/to/file.md ---
OLD: original text
NEW: edited text
```

### Multi-Voice Extension Points

1. **Context tagging** — currently no context in log entries
   - Extension: Infer context from file path patterns (match against config)
   - Log entry: `--- TIMESTAMP | PATH | CONTEXT:blog ---`

2. **Context-aware batch review** — currently all diffs reviewed together
   - Extension: `/interfluence refine --context blog` — review only blog-context learnings
   - Prevents cross-contamination (commit edits don't affect blog profile)

---

## 7. Other Skills

### Ingest (`skills/ingest.md`)

**Current:** Add samples from files, directories, URLs
**Multi-voice extension:** Prompt user for context tags during ingestion
  - "What context is this sample? (blog/commit/docs/other)"
  - File path pattern hints: `blog/*.md` → auto-tag `blog`

### Refine (`skills/refine.md`)

**Current:** Interactive profile editing, batch learning review
**Multi-voice extension:**
  - Select which profile to refine
  - Filter learnings by context
  - Cross-context learning detection: "This edit was in a commit message but affects your blog voice too. Apply to both?"

### Compare (`skills/compare.md`)

**Current:** Diagnose voice match quality for single profile
**Multi-voice extension:**
  - Compare text against multiple profiles: "This sounds 80% like your blog voice, 40% like your commit voice"
  - Suggest best-fit context

---

## 8. Roadmap & Explicit Multi-Voice Plans

### From AGENTS.md

**MVP (current):**
- Ingest, Analyze, Apply, Refine, Config, Learn
- Single profile per project

**Post-MVP (explicitly planned):**
- **Context-specific voice profiles (blog vs commit vs PRD)** ← PRIMARY GOAL
- Multi-source weighting
- `/interfluence compare` A/B testing (partially implemented)
- Notion API direct ingestion
- Profile export/import
- Incremental analysis (`--incremental` flag)

### From README.md

> "Context-specific sub-profiles (your docs voice vs. your commit message voice vs. your Slack voice) are on the roadmap. For now, one profile per project."

### From docs/roadmap.json

```json
{
  "now": [
    {"id": "IFLE-N1", "title": "Improve voice-profile feature stability on short profile sample sets.", "priority": "P1"}
  ],
  "next": [
    {"id": "IFLE-N2", "title": "Enable profile export/import for per-repo or per-team style governance.", "priority": "P2"},
    {"id": "IFLE-N3", "title": "Add confidence metrics for style adaptation suggestions.", "priority": "P2"},
    {"id": "IFLE-L1", "title": "Introduce style-aware output gating inside interphase workflow.", "priority": "P2"}
  ]
}
```

**Note:** Multi-voice not in roadmap.json yet, but explicitly in AGENTS.md/README.md post-MVP list.

---

## 9. Existing Voice Profile Example

### Structure (from `.interfluence/voice-profile.md`)

The plugin's own voice profile (analyzing the author's blog post) demonstrates the format:

1. **Overview** — 3 sentences capturing core voice
2. **Sentence Structure** — medium-to-long sentences, parenthetical asides, em-dashes, semicolons
3. **Vocabulary & Diction** — "I find" construction, coined terms, technical jargon used casually
4. **Tone & Voice** — peer-to-peer, dry humor, genuine enthusiasm, self-aware
5. **Structure Patterns** — layered openings (epigraph → values → aside → roadmap), generous attribution
6. **Cultural References** — McLuhan/Ong/Scott, Dune, Simpsons, "in this house we believe" meme
7. **Anti-Patterns** — never corporate-speak, never thought-leader posture, never humorless >2 paragraphs, never explain references, never passive voice for opinions, never abstract over specific, never talk down, never omit attribution

**Key insight:** Each section has prose description + direct quotes + "Do this / Not this" pairs. This format is context-agnostic — works equally well for "blog voice" or "commit voice" with different content.

---

## 10. Multi-Voice Implementation Strategy (Informed by Current Architecture)

### Phase 1: Storage & Retrieval (MCP Server Changes)

1. **Profile path resolver:**
   ```typescript
   getVoiceProfilePath(projectDir: string, context: string = "default")
     → ${projectDir}/.interfluence/profiles/${context}.md
   ```

2. **Update MCP tools:**
   ```typescript
   profile_get(projectDir: string, context?: string)
   profile_save(projectDir: string, content: string, context?: string)
   ```

3. **Backward compatibility:** Default context = "default" or read from config

### Phase 2: Corpus Filtering (Corpus Tools)

1. **Enhance corpus_get_all:**
   ```typescript
   corpus_get_all(projectDir: string, filterByTags?: string[])
   ```

2. **Tag inference during ingestion:**
   - Match file path against config patterns → auto-tag
   - Prompt user: "What context is this? (blog/commit/docs)"

### Phase 3: Config Schema Extension

1. **Add context routing:**
   ```yaml
   mode: auto
   defaultContext: main
   contexts:
     blog:
       autoApplyTo: ["blog/**/*.md", "posts/**/*.md"]
       learnFromEdits: true
     commit:
       autoApplyTo: ["CHANGELOG.md"]
       learnFromEdits: false
     docs:
       autoApplyTo: ["docs/**/*.md", "README.md"]
       learnFromEdits: true
   exclude: ["CLAUDE.md", "AGENTS.md"]
   ```

2. **Config migration:** Auto-upgrade old config.yaml to new schema

### Phase 4: Voice Analyzer Context Awareness

1. **Pass context to agent:**
   - Agent invocation: "Analyze corpus samples tagged `blog` to generate `blog` voice profile"
   - Use filtered `corpus_get_all(projectDir, ["blog"])`

2. **Context-specific profile templates:**
   - Blog: all sections
   - Commit: drop "Cultural References", emphasize "Structure Patterns" (conventional commits)
   - Docs: emphasize "Tone & Voice" (instructional vs conversational)

### Phase 5: Skill Updates

1. **Apply skill:**
   - Infer context from file path or ask user
   - Load appropriate profile: `profile_get(projectDir, inferredContext)`

2. **Refine skill:**
   - List available contexts, let user select
   - Filter learnings by context tag

3. **Ingest skill:**
   - Ask for context during ingestion
   - Apply file path pattern matching for auto-tagging

### Phase 6: Learning Hook Enhancement

1. **Context inference in hook:**
   - Match edited file path against config patterns
   - Tag log entry: `--- TIMESTAMP | PATH | CONTEXT:blog ---`

2. **Learnings storage:**
   - Option A: Single log with context tags (current approach, filter during refine)
   - Option B: Separate logs per context (`.interfluence/learnings-blog.log`)

---

## 11. References to "voice", "context", "mode" in Codebase

### Searched patterns: `voice|context|mode` (case-insensitive)

**Key findings:**
- "voice" appears 100+ times — always refers to voice profile/analysis
- "context" appears in corpus samples (project context for agents) — NOT voice context
- "mode" appears only as config field (`auto` vs `manual`)
- **No existing multi-voice implementation** — all "context" references are about project/codebase context, not voice context

**Implication:** "context" is the right term for multi-voice feature (blog context, commit context), but needs clear naming to avoid confusion with "project context" or "codebase context". Consider "voice context" or "profile context" as explicit terminology.

---

## 12. Data Integrity Considerations

### Current Guarantees

1. **Atomic writes:** MCP tools use `writeFileSync` (synchronous, atomic on most filesystems)
2. **No concurrent access:** Plugin runs in single Claude Code session
3. **Index-corpus sync:** Corpus index is source of truth, orphaned files ignored

### Multi-Voice Challenges

1. **Profile proliferation:** Multiple profiles per project (blog, commit, docs)
   - Mitigation: Profile list command, profile metadata in index

2. **Corpus tag consistency:** Samples might be relevant to multiple contexts
   - Mitigation: Allow multi-tagging (`tags: ["blog", "docs"]`)

3. **Learning cross-contamination:** Edit in docs affects blog profile
   - Mitigation: Explicit context tagging in learnings, user approval before cross-apply

4. **Config complexity:** Context routing rules can conflict
   - Mitigation: Validation on `config_save`, clear precedence rules

---

## 13. Token Efficiency Considerations

### Current Token Usage

- **Analyze (Opus):** Loads entire corpus via `corpus_get_all`, generates full profile (high tokens)
- **Apply:** Loads profile + target file, rewrites (medium tokens)
- **Refine:** Loads profile + learnings, interactive editing (medium tokens)

### Multi-Voice Impact

1. **Per-context analysis:** Multiple Opus calls instead of one
   - Mitigation: Incremental analysis (only analyze new samples for changed contexts)

2. **Profile bloat:** Multiple profiles loaded during auto-apply
   - Mitigation: Context inference → load only relevant profile

3. **Corpus filtering:** Reduced token usage per analysis (smaller corpus per context)
   - Benefit: Faster, cheaper analysis

**Net impact:** Slightly higher total tokens (multiple profiles), but lower per-operation tokens (focused context).

---

## 14. User Experience Considerations

### Current UX

- Simple: One profile per project
- Explicit: Manual mode default, user calls `/interfluence apply`
- Transparent: Profile is readable markdown

### Multi-Voice UX Challenges

1. **Context selection friction:** User must specify context for each operation
   - Mitigation: Smart defaults (infer from file path), remember last context

2. **Profile discovery:** Which profiles exist? What context to use?
   - Mitigation: `/interfluence status` shows all contexts, sample counts, last analyzed

3. **Learning confusion:** "Why didn't my edit update the profile?"
   - Mitigation: Post-edit notification: "Learned from edit (context: blog)"

4. **Migration path:** Existing users have single `voice-profile.md`
   - Mitigation: Auto-detect old profile, prompt: "Rename to 'main' context or keep as default?"

---

## 15. Key Takeaways for Multi-Voice Implementation

### What's Already Built

1. **Tags in corpus schema** — infrastructure exists, just needs usage
2. **Extensible config** — YAML schema can add contexts without breaking changes
3. **Profile prose format** — context-agnostic, works for any voice type
4. **Modular tools** — MCP tools are narrow, easy to extend with optional params

### What Needs Building

1. **Profile path routing** — context parameter throughout stack
2. **Context inference logic** — file path pattern matching
3. **Corpus filtering** — tag-based `corpus_get_all`
4. **Learning context tagging** — hook enhancement
5. **Skill UX** — context selection/inference in ingest, apply, refine

### Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Corpus tag inconsistency | Wrong samples in context | Validation during ingestion, tag review UI |
| Profile cross-contamination | Blog learnings affect commits | Explicit context isolation, user approval for cross-apply |
| Config complexity | User confusion, conflicts | Clear examples, validation, safe defaults |
| Backward compatibility break | Existing users disrupted | Auto-migration, "default" context for old profiles |
| Token usage spike | Cost increase | Incremental analysis, context inference to avoid loading all profiles |

### Recommended Next Steps

1. **Spike:** Prototype context parameter in `profile_get`/`profile_save`, test with existing `.interfluence/`
2. **Schema design:** Finalize config.yaml context routing structure
3. **Tag strategy:** Decide single-tag vs multi-tag, auto-inference rules
4. **UX flow:** Wireframe context selection in skills (ingest, apply, refine)
5. **Migration plan:** Test auto-upgrade of existing single-profile projects

---

## 16. Appendix: File Paths Reference

```
/root/projects/Interverse/plugins/interfluence/
├── .claude-plugin/
│   └── plugin.json                     # Plugin manifest, MCP server config
├── server/
│   ├── src/
│   │   ├── index.ts                    # MCP server entry point
│   │   ├── tools/
│   │   │   ├── corpus.ts               # Corpus CRUD tools
│   │   │   └── profile.ts              # Profile, config, learnings tools
│   │   └── utils/
│   │       ├── corpus-index.ts         # CorpusSample interface, index loader
│   │       └── paths.ts                # Path resolution helpers
│   ├── dist/bundle.js                  # Esbuild bundle (committed)
│   └── package.json
├── skills/
│   ├── ingest.md                       # Add samples to corpus
│   ├── analyze.md                      # Generate voice profile
│   ├── apply.md                        # Rewrite in user's voice
│   ├── refine.md                       # Interactive profile editing
│   └── compare.md                      # Diagnose voice match
├── agents/
│   └── voice-analyzer.md               # Opus literary analyst
├── hooks/
│   └── learn-from-edits.sh             # PostToolUse on Edit
├── commands/
│   └── interfluence.md                 # /interfluence router
├── docs/
│   └── roadmap.json                    # Module roadmap
├── .interfluence/                      # Plugin's own profile
│   ├── voice-profile.md
│   ├── corpus-index.yaml
│   └── corpus/
│       └── sample-20260212054902-0fek.md
├── CLAUDE.md                           # Quick reference
└── AGENTS.md                           # Full development guide
```

**Per-project data structure** (when user runs `/interfluence ingest`):
```
user-project/
└── .interfluence/
    ├── voice-profile.md                # Current: single profile
    ├── profiles/                       # Future: multi-voice
    │   ├── default.md
    │   ├── blog.md
    │   ├── commit.md
    │   └── docs.md
    ├── config.yaml
    ├── corpus-index.yaml
    ├── corpus/
    │   └── sample-*.md
    ├── learnings-raw.log               # Current: single log
    └── learnings-blog.log              # Future: per-context logs (optional)
```

---

## 17. Code Snippets Reference

### Current Profile Storage

```typescript
// server/src/utils/paths.ts
export function getVoiceProfilePath(projectDir: string): string {
  return join(getinterfluenceDir(projectDir), "voice-profile.md");
}

// Multi-voice extension:
export function getVoiceProfilePath(
  projectDir: string,
  context: string = "default"
): string {
  const profilesDir = join(getinterfluenceDir(projectDir), "profiles");
  if (!existsSync(profilesDir)) {
    mkdirSync(profilesDir, { recursive: true });
  }
  return join(profilesDir, `${context}.md`);
}
```

### Current Corpus Schema

```typescript
// server/src/utils/corpus-index.ts
export interface CorpusSample {
  id: string;
  filename: string;
  source: string;
  sourceUrl?: string;
  sourcePath?: string;
  title?: string;
  addedAt: string;
  wordCount: number;
  analyzed: boolean;
  tags?: string[];  // ← Already exists, ready for context tags
}
```

### Current Config Schema

```typescript
// server/src/tools/profile.ts
export interface interfluenceConfig {
  mode: "auto" | "manual";
  autoApplyTo: string[];
  exclude: string[];
  learnFromEdits: boolean;
}

// Multi-voice extension (example):
export interface interfluenceConfigV2 {
  mode: "auto" | "manual";
  defaultContext: string;
  contexts: {
    [contextName: string]: {
      autoApplyTo: string[];
      learnFromEdits: boolean;
    };
  };
  exclude: string[];
}
```

---

## 18. Summary for Implementation

**Current State:**
- Single voice profile per project
- All infrastructure modular and extensible
- Corpus already supports tags (unused)
- Config system is YAML, easy to extend
- Explicit post-MVP plan for context-specific profiles

**Extension Surface:**
1. Profile path routing (5 LOC change)
2. Corpus filtering by tags (10 LOC change)
3. Config schema v2 (20 LOC change)
4. Context inference from file paths (30 LOC change)
5. Learning hook context tagging (15 LOC change)
6. Skill UX for context selection (50 LOC change)

**Total estimated LOC:** ~130 lines of TypeScript + ~100 lines of skill/agent prompt updates

**Risk level:** Low. No breaking changes to data structures, all backward compatible via defaults.

**Recommended approach:** Incremental rollout
1. Add context param to profile tools (optional, default="default")
2. Add corpus filtering by tags
3. Update skills to pass context (hardcode "default" first)
4. Add config v2 schema with auto-migration
5. Add context inference logic
6. Update learning hook
7. Update skill prompts for context selection UX

---

**End of Research Document**
