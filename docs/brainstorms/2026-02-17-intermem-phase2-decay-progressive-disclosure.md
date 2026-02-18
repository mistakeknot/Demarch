# Brainstorm: intermem Phase 2 — Decay + Progressive Disclosure

**Bead:** iv-rkrm
**Phase:** brainstorm (as of 2026-02-18T06:44:06Z)
**Date:** 2026-02-17
**Status:** brainstorm
**Context:** Phase 0.5 (synthesis) and Phase 1 (validation overlay) are shipped. 119 tests pass. Plugin installed and validated against Interverse (42 entries, citation extraction, confidence scoring, stale filtering all working).

---

## 1. What We're Building

Phase 2 adds two capabilities that together solve the auto-memory growth problem:

**Decay** — Entries that stop being re-observed in auto-memory lose confidence over time. When confidence drops below threshold, entries are auto-archived (commented out) in target docs. If re-observed, they recover automatically.

**Progressive Disclosure** — Instead of promoting everything into a flat AGENTS.md, use a tiered structure: AGENTS.md becomes a thin index with one-liners, detail lives in `docs/intermem/<section>.md`. Agents load the index at session start; deeper context is available on demand via Read or CLI queries.

**Decision gate (from roadmap):** Reduces bloat >50%.

---

## 2. Problem Statement

### The growth problem

Auto-memory accumulates facts every session. Intermem promotes stable facts to AGENTS.md/CLAUDE.md. But nothing removes them. Over time:

- AGENTS.md grows unboundedly, consuming more context tokens every session
- Stale facts (about deleted files, renamed modules, outdated patterns) persist indefinitely
- All entries get equal weight — a critical architectural insight and an obsolete debugging note occupy the same context

### What Phase 1 solved (and didn't)

Phase 1 added citation validation — entries referencing deleted files get flagged as stale and excluded from *future* promotion. But it doesn't:

- Remove or archive already-promoted stale entries
- Degrade confidence over time for entries without broken citations
- Reduce the per-session token cost of loading curated docs
- Provide selective retrieval (everything or nothing)

---

## 3. Key Decisions

### D1: Decay signal — Time + Recapture

**Decision:** Entries decay based on `last_seen` age (when last observed in a stability snapshot), not wall-clock time alone. If auto-memory keeps re-writing a fact, that proves it's still relevant and resets the decay clock.

**Why not time-only:** A fact like "modernc.org/sqlite doesn't support CTE+UPDATE RETURNING" is equally true in 30 days. Penalizing it purely for age makes no sense. But if Claude keeps rediscovering and re-writing it, that *proves* it's still relevant.

**Why not access-frequency:** Tracking when an agent "reads" a memory entry would require instrumenting CLAUDE.md/AGENTS.md loads, which happen outside intermem's control. Too much complexity for uncertain value.

**Mechanism:**
- `last_seen` timestamp in metadata.db already tracks when an entry was last observed in a stability snapshot
- If `last_seen` is >14 days old, apply a confidence penalty (-0.1 per 14-day period, compounding)
- If the entry reappears in auto-memory, `last_seen` resets via the existing upsert, penalty disappears
- Existing `snapshot_count` bonus (+0.2 for 5+ snapshots) rewards persistence

### D2: Decay action — Auto-archive (moderate)

**Decision:** When confidence drops below 0.3, stale entries are commented out in target docs as `<!-- intermem:archived:<hash> ... -->` rather than deleted.

**Why not flag-only:** Creates reports humans must act on — adds work instead of reducing it. Doesn't achieve the >50% bloat gate because flagged entries still consume context.

**Why not auto-delete:** Irreversible. If the scoring model has a false positive, recovery requires the entry to re-enter auto-memory, stabilize (3+ snapshots), pass validation, and get re-promoted — weeks of latency.

**Why auto-archive wins:**
- HTML comments are invisible to agents (confirmed by research — but they still exist in the file for recovery)
- Actually wait — research showed LLMs DO see HTML comments in raw text. So we need a different archive mechanism.

**Revised approach:** Move archived entries to a separate file (`docs/intermem/.archived.md`) rather than commenting them out. This file is never auto-loaded. Entries can be restored by moving them back.

### D3: Progressive disclosure — Multi-file tiers

**Decision:** AGENTS.md becomes a thin index. Detail lives in `docs/intermem/<section>.md`.

**Research killed collapsible sections:** LLMs parse raw text — `<details>` tags and HTML comments are fully visible in context. Zero token savings. Security risk (prompt injection via hidden comments).

**Why multi-file over MCP:** intermem manages ~42 entries across one project. MCP adds +50MB overhead, tool definitions in every session's context, and a persistent process. Not justified at current scale.

**Structure:**
```
AGENTS.md                          # Index: section titles + one-liners (~50-150 tokens)
docs/intermem/
  git-workflow.md                  # Full details, gotchas, examples
  sqlite-patterns.md               # ...
  plugin-publishing.md             # ...
  .archived.md                     # Decayed entries (never auto-loaded)
```

**Token savings:** 90-95% reduction for sessions that don't need full context. Agents use Read tool to drill into specific sections when needed.

### D4: CLI queries — Deferred to Phase 2b or Phase 3

**Decision:** Add `--search`, `--list-topics` CLI flags to `__main__.py` for on-demand retrieval. Agents invoke via Bash when they need deeper context beyond the index.

**Why CLI over MCP:** Zero overhead — no persistent process, no tool definitions consuming context. Same query power via metadata.db. Natural evolution path: if CLI queries become frequent, promote to MCP.

### D5: Decay threshold — 14 days

**Decision:** 14 days without re-observation before confidence penalty begins. Matches the Phase 1 design intent.

**Rationale:** Two weeks is long enough for entries to reappear across normal development sessions (most projects have weekly activity patterns). Short enough that truly stale entries get caught within a month.

### D6: Detail file location — `docs/intermem/`

**Decision:** Detail files live in `docs/intermem/` within each project. Committed to git, human-readable, discoverable.

**Why not `.intermem/docs/`:** State directory is gitignored — detail files should be version-controlled and reviewable.

**Why not `.claude/memory/`:** Collocated with auto-memory source, which creates confusion about what's curated vs raw.

---

## 4. Architecture

### Decay flow

```
run_synthesis() or --sweep:
  1. Record snapshot in stability.jsonl (existing)
  2. Upsert entries in metadata.db (existing)
  3. For each entry in metadata.db:
     a. Check last_seen age
     b. If >14 days: apply time penalty to confidence
     c. If confidence < 0.3: mark status = 'stale'
  4. For stale entries that are promoted:
     a. Remove from target doc (AGENTS.md index or docs/intermem/<section>.md)
     b. Append to docs/intermem/.archived.md with metadata
     c. Record in journal (new state: 'archived')
  5. For archived entries that reappear in auto-memory:
     a. last_seen resets (upsert)
     b. Confidence recomputes (citations + recapture bonus)
     c. If confidence >= 0.3: restore from .archived.md to active docs
     d. Record in journal (new state: 'restored')
```

### Multi-file promotion flow

```
Current (Phase 1):
  promote_entries() → append to AGENTS.md with <!-- intermem --> markers

Phase 2:
  promote_entries() →
    1. Determine section from MemoryEntry.section
    2. Map section → docs/intermem/<section-slug>.md
    3. Append full entry to section file
    4. Update AGENTS.md index with one-liner + pointer
    5. Record mapping in metadata.db (entry_hash → file_path)
```

### Index format (AGENTS.md)

```markdown
# Project Memory Index

## Git Workflow
- Signed commits required; pre-commit hook runs linters
- See `docs/intermem/git-workflow.md` for troubleshooting and details

## SQLite Patterns (modernc.org/sqlite)
- CTE + UPDATE RETURNING not supported; use direct UPDATE RETURNING
- See `docs/intermem/sqlite-patterns.md` for full gotchas

## Plugin Publishing
- Interbump hook auto-runs on git push; use bump-version.sh manually
- See `docs/intermem/plugin-publishing.md` for workflow
```

### CLI query interface

```bash
# Search entries by keyword
uv run python -m intermem --search "sqlite" --project-root .
# Returns: matching entries with confidence, section, source file

# List all topics (sections)
uv run python -m intermem --list-topics --project-root .
# Returns: section names with entry counts and avg confidence

# Show stale/archived entries
uv run python -m intermem --show-archived --project-root .
# Returns: archived entries with reason and original confidence
```

---

## 5. Scope Control

### In scope (Phase 2)

- Time-based confidence decay (14-day threshold, compounding -0.1 per period)
- Auto-archive of stale promoted entries to `docs/intermem/.archived.md`
- Auto-restore of archived entries on re-observation
- Multi-file promotion: detail files in `docs/intermem/`, index in AGENTS.md
- Section-to-file mapping in promoter
- Index update logic (one-liner + pointer per section)
- `--sweep` CLI flag for manual re-validation + decay pass
- `--search` and `--list-topics` CLI flags for on-demand retrieval
- `--show-archived` CLI flag
- Journal states: 'archived', 'restored'
- Schema migration: add `last_sweep`, `archived_at`, `archived_to` columns
- Tests for all new modules (~25-35 new tests)
- All existing 119 tests must continue passing

### Out of scope (later phases)

- MCP server (deferred until corpus > 200 entries or multi-project use)
- Semantic/embedding-based search (Phase 3, requires intersearch)
- Cross-project memory sharing (Phase 3, bead iv-xswd)
- Knowledge graph links between entries
- Proactive retrieval (hooks that auto-query based on current file)
- Ebbinghaus-curve decay (exponential) — start with linear penalty, can tune later

### Risk assessment

- **Low risk:** Decay is additive — doesn't break existing JSONL pipeline
- **Low risk:** Multi-file promotion is a new code path alongside (not replacing) direct AGENTS.md writes. Can fall back with `--no-tiered` flag.
- **Medium risk:** Auto-archive could have false positives if confidence model is miscalibrated. Mitigation: archived entries are recoverable, and `--show-archived` provides visibility.
- **Medium risk:** Section-to-file mapping needs a slug generation strategy. Mitigation: use simple `section.lower().replace(' ', '-')` with collision handling.
- **Rollback cost:** Delete `docs/intermem/`, remove index from AGENTS.md, restore flat promotion. Low impact.

---

## 6. Decision Gate Measurement

To validate the >50% bloat reduction:

1. **Before measurement:** Count total lines/tokens in AGENTS.md (flat, pre-Phase 2)
2. **After measurement:** Count lines/tokens in AGENTS.md (index-only, post-Phase 2)
3. **Bloat reduction:** `1 - (after / before)` — expect 80-95% reduction in always-loaded tokens
4. **Decay measurement:** Run synthesis on Interverse. Count entries archived vs total. Even 1 entry archived validates the mechanism.
5. **Recovery test:** Manually add a known-stale entry to auto-memory, let it stabilize, verify it gets archived. Then re-add it, verify it gets restored.

---

## 7. Open Questions

### Q1: Should we migrate existing promoted entries to multi-file on first run?

Option A: Yes, one-time migration. Split current AGENTS.md by section headers, create docs/intermem/ files, rewrite AGENTS.md as index. Clean but complex.

Option B: No, only new promotions use multi-file. Existing AGENTS.md content stays flat until manually reorganized. Simpler but leaves legacy bloat.

**Leaning toward A** — the whole point is reducing bloat, so leaving the existing flat content defeats the purpose. The migration is deterministic (parse by `## Section` headers) and can be a `--migrate-to-tiered` one-shot command.

### Q2: How should the index one-liners be generated?

Option A: First sentence of the entry content. Simple but may be too detailed or not descriptive enough.

Option B: First N characters (e.g., 80 chars) truncated. Consistent length but may cut mid-sentence.

Option C: Section header is the one-liner. Only works if entries have meaningful section headers.

**Leaning toward A** — first sentence is usually the most informative. If it's too long, truncate at 120 chars with ellipsis.

### Q3: Should decay compound or cap?

Current thinking: -0.1 per 14-day period (so -0.2 at 28 days, -0.3 at 42 days). With base 0.5, an entry with no citations hits stale (0.3) after 28 days, and reaches 0.0 after 70 days.

Alternative: Single -0.1 penalty (non-compounding). Slower decay but less aggressive.

**Leaning toward compounding** — entries that haven't been seen in 70 days are almost certainly stale. Compounding ensures they eventually get archived rather than hovering at 0.4 forever.

---

## 8. Effort Estimate

| Component | Complexity | New/Modified |
|---|---|---|
| Decay logic in confidence scoring | Low | Modified: citations.py |
| Sweeper module (re-validation + decay pass) | Medium | New: sweeper.py |
| Auto-archive logic | Medium | New: archiver.py |
| Auto-restore logic | Medium | In archiver.py |
| Multi-file promoter updates | Medium | Modified: promoter.py |
| Index generation | Low | New: indexer.py or in promoter.py |
| Section-to-file mapping | Low | In _util.py or promoter.py |
| CLI flags (--sweep, --search, --list-topics, --show-archived) | Low | Modified: __main__.py |
| One-time migration (--migrate-to-tiered) | Medium | In __main__.py |
| Journal states (archived, restored) | Low | Modified: journal.py |
| Schema migration | Low | Modified: metadata.py |
| Tests | Medium | ~25-35 new tests |

Total: ~2 new modules, ~5 modified files, ~500-700 lines new code. Estimated: full day session.

---

## 9. Research References

- `docs/research/research-progressive-disclosure-patterns.md` — Full analysis of multi-file, collapsible, and MCP approaches
- `docs/research/research-claude-code-file-loading.md` — Claude Code auto-loading behavior, MCP patterns
- `docs/research/research-memory-validation-patterns.md` — Phase 1 research (staleness patterns)
- FadeMem paper (arXiv:2601.18642) — Ebbinghaus-inspired decay for LLM agents
- A-MEM paper (arXiv:2502.12110) — Zettelkasten-inspired agent memory with dynamic links
- MemGPT/Letta — Tiered memory (in-context vs archival) with self-editing
