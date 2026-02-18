# PRD: intermem Phase 2A — Decay + Demotion

**Bead:** iv-rkrm
**Date:** 2026-02-18
**Status:** PRD (revised after flux-drive review)
**Brainstorm:** `docs/brainstorms/2026-02-17-intermem-phase2-decay-progressive-disclosure.md`
**Research:** `docs/research/research-progressive-disclosure-patterns.md`, `docs/research/research-claude-code-file-loading.md`
**Reviews:** `docs/research/review-prd-data-correctness.md`, `docs/research/review-prd-architecture.md`, `docs/research/review-prd-user-product-fit.md`

---

## Problem

Intermem promotes stable auto-memory entries to AGENTS.md/CLAUDE.md, but nothing removes them. Over time, curated docs grow unboundedly — every session pays the token cost of loading all entries, including stale ones. Phase 1 prevents *new* stale entries from being promoted but doesn't address already-promoted entries or degrade confidence over time.

## Solution

Add a decay mechanism: entries that stop appearing in auto-memory lose confidence over time (time + recapture signal). When confidence drops below threshold, entries are demoted — removed from target docs and marked in metadata.db. If re-observed, they're re-promoted through the normal pipeline.

**Scope split (from flux-drive review):** Progressive disclosure (tiered files, multi-file promotion) is deferred to Phase 2B pending validation that agents benefit from tiered structure. Phase 2A focuses on the forgetting discipline that reduces bloat through better stale filtering.

---

## Review Findings Incorporated

| ID | Finding | Source | Resolution |
|----|---------|--------|------------|
| A1 | Sweeper.py redundant — duplicates validator.py | Architecture | Merged: add `sweep_all_entries()` to validator.py |
| A2 | Archiver.py false separation from promoter | Architecture | Merged: add `demote_entries()` to promoter.py |
| A3 | Decay in citations.py breaks pure function contract | Architecture | Separated: `apply_decay_penalty()` in validator.py |
| C1 | Archive/restore non-atomicity (4-step crash risk) | Correctness | Simplified: demotion is 2-step (remove + DB update), journaled |
| C2 | Confidence oscillation risk | Correctness | Added: `stale_streak` hysteresis (must be stale 2 consecutive sweeps) |
| C3 | Dual-state JSONL/SQLite divergence | Correctness | Documented: `last_seen` updated atomically in same upsert transaction |
| U1 | Decision gate measures file size, not agent behavior | User-Product | Revised success criteria |
| U2 | Scope too large (5 features, 2 UX shifts) | User-Product | Split: Phase 2A (decay) and Phase 2B (tiering) |
| U3 | Sweep is manual-only | User-Product | Added: note about automatic trigger as Phase 2B consideration |

---

## Features

### F1: Time-Based Confidence Decay

**What:** Add decay penalty based on `last_seen` age. Entries not re-observed in auto-memory for >14 days lose confidence progressively.

**Architecture:** Keep `compute_confidence()` pure (no time parameter). Add separate `apply_decay_penalty(confidence, last_seen, current_time)` function in validator.py. Validator calls both in sequence.

**Acceptance criteria:**
- [ ] `apply_decay_penalty()` returns confidence - (0.1 * floor(days_since_last_seen / 14)) for ages >14 days
- [ ] Penalty resets when entry reappears in a stability snapshot (last_seen updates via existing upsert)
- [ ] `intermem sweep` subcommand triggers a full re-validation + decay pass across all entries in metadata.db
- [ ] Sweep runs within a single SQLite transaction (read + decay + write, no interleaving)
- [ ] Entries with no citations and no re-observation for >28 days (base 0.5 - 0.2 = 0.3) hit the stale threshold
- [ ] Existing confidence signals (citation validity, snapshot count bonus) continue working unchanged
- [ ] All existing 119 tests pass unchanged

### F2: Demotion of Stale Promoted Entries

**What:** Remove stale entries from target docs (AGENTS.md/CLAUDE.md) when confidence drops below 0.3. Track demotion in metadata.db and journal. Re-promotion happens through the normal pipeline when entry reappears.

**Simplified from original F2:** No separate archive file. Demoted entries are tracked in metadata.db (status='demoted') and journal (state='demoted'). Recovery is through normal re-promotion, not a special restore path.

**Hysteresis (from correctness review):** Entry must be stale for 2 consecutive sweeps before demotion, preventing oscillation from flapping citations.

**Acceptance criteria:**
- [ ] When a promoted entry's `stale_streak` reaches 2 during sweep, it is removed from its target doc
- [ ] `stale_streak` increments each sweep where confidence < 0.3, resets to 0 when confidence >= 0.3
- [ ] Demotion is journaled: journal records state `'demoted'` with entry hash, target file, removal timestamp
- [ ] Journal-based crash recovery: if demotion started but didn't complete (entry removed from doc, DB not updated), next sweep detects and repairs
- [ ] Schema migration: add `stale_streak INTEGER DEFAULT 0` and `demoted_at TEXT` columns to `memory_entries`
- [ ] `intermem query --demoted` lists demoted entries with reason, original confidence, and timestamp
- [ ] If entry reappears in auto-memory and passes validation with confidence >= 0.3, it goes through normal promotion pipeline (dedup recognizes it as novel since it's no longer in target docs)

### F3: CLI Query Interface

**What:** Add subcommands for on-demand metadata.db queries. Restructured as subcommands (from architecture review) instead of flat flags.

**Acceptance criteria:**
- [ ] `intermem query --search <keywords>` returns matching entries (LIKE query on content_preview + section) with confidence, section, source file
- [ ] `intermem query --topics` returns section names with entry counts and average confidence
- [ ] `intermem query --demoted` returns demoted entries with demotion reason, original confidence, and timestamp
- [ ] All queries respect `--project-root` for metadata.db location
- [ ] Output is human-readable table format by default, with `--json` flag for structured output
- [ ] Returns exit code 0 on success, 1 on no results, 2 on error

---

## Non-Goals (Phase 2A)

- Multi-file tiered promotion (deferred to Phase 2B after agent behavior validation)
- Tiered migration command (deferred to Phase 2B)
- Separate archive file (replaced by simpler demotion in metadata.db)
- MCP server (deferred to Phase 3)
- Semantic/embedding-based search (Phase 3)
- Cross-project memory sharing (Phase 3, bead iv-xswd)
- Automatic sweep trigger (Phase 2B consideration — hook or session-end integration)
- Ebbinghaus exponential decay curve (start with linear compounding, tune later)

---

## Dependencies

- **Phase 1 complete:** metadata.db, citations.py, validator.py, _util.py all exist and tested (119 tests)
- **Python stdlib only:** sqlite3, pathlib, re, hashlib, datetime — no new dependencies
- **Existing target docs:** Must have `<!-- intermem -->` markers from Phase 1 promotions (or be empty)

---

## Open Questions (Resolved)

1. **Decay compounding cap:** Existing clamp to [0.0, 1.0] is sufficient. No additional floor needed.

2. **Archive vs demotion:** Demotion (remove from doc + DB tracking) instead of archive file. Simpler, fewer crash-safety concerns, recovery through normal re-promotion.

3. **Oscillation prevention:** `stale_streak` hysteresis — must be stale for 2 consecutive sweeps (28+ days minimum) before demotion.

---

## Success Criteria

1. **Decay mechanism works:** Synthetic test with known-stale entries (last_seen >28 days, no citations) catches 100% and marks them for demotion
2. **Demotion works:** At least 1 entry demoted during Interverse sweep, or synthetic test demonstrates full demotion lifecycle
3. **Re-promotion works:** Demoted entry that reappears in auto-memory goes through normal promotion pipeline successfully
4. **No regression:** All existing 119 tests pass unchanged
5. **Rollback:** Disabling decay (skip `apply_decay_penalty()`) restores Phase 1 behavior exactly

---

## Technical Constraints

- **Python stdlib only** — no new dependencies
- **No hooks** — Clavain hook budget constraint continues
- **No MCP server** — skill-only architecture continues
- **No new modules** — extend validator.py, promoter.py, metadata.py (from architecture review)
- **Additive schema** — metadata.db gains columns via ALTER TABLE, no breaking changes
- **Single-transaction sweep** — read + decay + write in one transaction, no concurrent interleaving

---

## Effort Estimate

| Component | New/Modified | Lines (est.) |
|---|---|---|
| `intermem/validator.py` | Modified | ~80 (sweep_all_entries, apply_decay_penalty) |
| `intermem/promoter.py` | Modified | ~40 (demote_entries) |
| `intermem/metadata.py` | Modified | ~50 (schema migration, query methods, stale_streak) |
| `intermem/journal.py` | Modified | ~10 (new 'demoted' state) |
| `intermem/__main__.py` | Modified | ~50 (sweep subcommand, query subcommand) |
| `tests/test_validator.py` | Modified | ~80 (decay, sweep, hysteresis tests) |
| `tests/test_promoter.py` | Modified | ~30 (demotion tests) |
| `tests/test_metadata.py` | Modified | ~30 (query, stale_streak tests) |

Total: **0 new modules**, 5 modified files, ~370 lines new code, ~15-20 new tests.

---

## Phase 2B: Progressive Disclosure (Deferred)

**Gate:** Validate that agents benefit from tiered structure before building it.

**Validation plan:**
1. Create a mock tiered AGENTS.md in a test project (manual split)
2. Run 10 agent sessions, measure detail-file read rate
3. If agents read detail files in <30% of sessions, proceed to F3 (tiered promotion) + F4 (migration)
4. If agents read everything anyway (>70%), redesign discovery mechanism or abandon tiering

**Deferred features:**
- F3: Multi-file tiered promotion (`docs/intermem/<section>.md`)
- F4: One-shot migration (`intermem migrate`)
- CLI queries for tiered structure
- Section-to-slug mapping
