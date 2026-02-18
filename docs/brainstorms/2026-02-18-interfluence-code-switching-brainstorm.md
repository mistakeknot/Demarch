# interfluence Code-Switching: Context-Aware Voice Profiles

**Date:** 2026-02-18
**Status:** Brainstorm complete
**Module:** plugins/interfluence

## What We're Building

Context-aware voice profiles for interfluence — the ability to maintain distinct writing voices for different contexts (blog posts vs GitHub READMEs) while sharing a common authorial DNA. Sub-profiles are **true deltas** that override specific sections of a base voice profile, with automatic resolution based on file path patterns.

## Why This Matters

People naturally code-switch. A single flat voice profile averages across registers, producing output that sounds wrong everywhere — too casual for docs, too stiff for blog posts. Code-switching lets the plugin match the *right* voice to each context.

## Key Decisions

### 1. Architecture: Named Sub-Profiles as Deltas (Option A + B ergonomics)

**Chosen over:** full standalone profiles per context, layered composition, and implicit context-only sections.

- Base profile (`voice-profile.md`) contains **cross-context invariants only** — the authorial DNA that persists regardless of register (vocabulary preferences, humor style, cultural references, universal anti-patterns)
- Context voices (`voices/blog.md`, `voices/docs.md`) contain **only sections that differ from the base**
- At apply time: load base, overlay delta sections, produce merged instructions
- Base changes auto-propagate to all contexts (no stale copies)

**Critical design choice:** The base is NOT a blended average of all samples. It's an extraction of what's **shared** across contexts. This prevents sample-volume drift (adding 10 blog posts doesn't make the base more blog-like). The analyzer does comparative analysis: group samples by context, identify invariants, then generate per-context deltas against those invariants.

### 2. Initial Contexts: Blog + Docs

Starting with two maximally different registers:
- **blog** — Substack personal writing (opinionated, personality-forward)
- **docs** — GitHub READMEs (instructional, scannable, welcoming)

More contexts (commit, slack, PRD) can be added later without architectural changes.

### 3. Corpus Tagging: Auto-Classify During Analyze

- Existing samples have no context tag — the voice-analyzer classifies them automatically during `/interfluence analyze`
- New samples added via `corpus_add` get **no context tag** at add time — classification always happens during analyze
- No new params on `corpus_add` (simpler UX)
- Corpus schema already has `tags?: string[]` — we use this field

### 4. Voice Resolution: First Match Wins

- Config maps voice names to glob patterns (ordered)
- First matching pattern wins when a file matches multiple voices
- No match → fall back to base profile
- Manual override: `--voice=blog` forces a specific context

```yaml
voices:
  blog:
    applyTo: ["posts/**", "blog/**"]
  docs:
    applyTo: ["docs/**", "README.md"]
```

### 5. No New MCP Tool for Corpus

Corpus tools unchanged. The only MCP changes are:
- `profile_get(projectDir, voice?)` — optional voice param
- `profile_save(projectDir, content, voice?)` — optional voice param
- `profile_list(projectDir)` — new tool, lists available voices

## Storage Layout

```
.interfluence/
├── voice-profile.md          # base voice (shared DNA)
├── voices/                   # per-context deltas
│   ├── blog.md               # overrides for blog posts
│   └── docs.md               # overrides for docs/READMEs
├── config.yaml               # gains 'voices' mapping
├── corpus-index.yaml         # samples gain context classification
├── corpus/
│   └── sample-*.md
└── learnings-raw.log
```

## What Changes Where

| Component | Change | Scope |
|-----------|--------|-------|
| `tools/profile.ts` | Add optional `voice` param to get/save, new `profile_list` | ~30 LOC |
| `utils/paths.ts` | Voice-aware path resolver | ~10 LOC |
| `tools/corpus.ts` | No changes (tags already exist) | 0 LOC |
| `config.yaml` schema | Add `voices` mapping, `defaultVoice` | ~15 LOC |
| `agents/voice-analyzer.md` | Multi-context analysis + auto-classification instructions | Prompt update |
| `skills/analyze.md` | Per-context analysis flow, corpus classification | Prompt update |
| `skills/apply.md` | Voice resolution from file path, `--voice` flag | Prompt update |
| `hooks/learn-from-edits.sh` | Tag learnings with inferred context | ~10 LOC |
| `skills/compare.md` | Multi-voice comparison | Prompt update |
| `commands/interfluence.md` | Route voice-related subcommands | Prompt update |

## Open Questions

1. **Should the learning hook infer context?** When an edit is logged, should the hook try to match the edited file path against voice patterns to tag the learning entry? (Leaning yes — enables per-context refine.)

2. **Profile migration** — Existing users have a single `voice-profile.md`. Treat it as the base profile automatically (no migration command needed)?

3. **Compare skill** — Should `/interfluence compare` show match scores against all voices, or just the inferred one?

## Out of Scope (Future)

- Commit message voice (needs git hook integration)
- Slack voice (needs interslack integration)
- PRD/spec voice (lower priority)
- Composable layers (Option C — only if two voices proves insufficient)
- Profile export/import across projects
- Confidence metrics per context
