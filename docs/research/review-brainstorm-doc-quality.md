# Review: intermem Phase 1 Brainstorm Doc Quality

**Source:** `docs/brainstorms/2026-02-18-intermem-phase1-validation-overlay.md`
**Reviewer:** Claude Haiku 4.5
**Date:** 2026-02-18

---

## 1. Gaps

- **No error handling strategy for metadata.db.** The doc defines schema and API but doesn't address what happens when SQLite is locked, corrupted, or missing at synthesis time. Given the "additive, zero-impact on JSONL pipeline" claim, the fallback behavior needs to be explicit: does synthesis abort, warn-and-continue, or silently skip validation?

- **`import_from_stability()` is underspecified.** Section 4.1 lists it as a method, but there's no description of what it does, what data it migrates, or when it triggers (first run? explicit flag?). This is a non-trivial migration path that could fail silently.

- **Decision gate measurement is circular.** Section 6 says "if even 10 of 32 candidates reference stale paths, that's 31% filtered — meeting the gate." This assumes stale paths exist in the test dataset, not that validation actually works. The measurement plan should define a controlled test (inject known-stale entries, verify they're caught), not rely on opportunistic discovery.

- **`/intermem:validate` behavior on missing metadata.db is undefined.** If the standalone skill is run before synthesis has ever been run (no DB yet), it's unclear whether it initializes the DB, errors out, or operates from scratch.

---

## 2. Contradictions

- **Section 3 (Q4) says validation runs "after stability scoring, before dedup."** But section 4.4 pipeline diagram shows: `scan → stability → [validate_citations] → dedup`. These are consistent, but the Q4 text also says validation runs as a standalone command on *already-promoted* entries — that's a different code path than the synthesis pipeline. The distinction between "pre-promotion filtering" vs "post-promotion auditing" needs to be clearer in the architecture diagram.

- **Section 5 defers `git log --follow` to Phase 2**, but the confidence scoring table in Q3 includes a `-0.2` weight for "Cited file path renamed" detected via `git log --follow`. This signal can't be used in Phase 1 if it's out of scope — the scoring model references a capability that won't exist.

---

## 3. Unclear Sections

- **"function_name" citation type** appears in the schema (`citation_type TEXT NOT NULL -- 'file_path' | 'module' | 'function' | 'pattern'`) and in `citations.py` (`grep in cited file`), but Section 5 explicitly defers function/symbol-level validation to Phase 2. It's unclear whether the citation type is extracted but left unchecked, or whether it shouldn't be in Phase 1 schema at all.

- **"pattern" citation type** is listed in the schema comment but never defined anywhere. What is a "pattern" citation? This appears to be a placeholder that slipped into the schema without definition.

- **Confidence threshold semantics:** The doc defines `< 0.3 = stale`, `< 0.1 = broken`, but never defines what "broken" means in practice — is it treated differently from "stale" in the pipeline? Does it trigger different behavior in `/intermem:validate`?

---

## 4. Scope Assessment

The scope is mostly well-bounded with a clear in/out list. Two concerns:

- **`import_from_stability()` is scope-bleed.** It's listed as in-scope (Section 5: "Import existing stability data into metadata.db on first run") but has no complexity estimate in Section 7 and no spec. This could be a hidden medium-complexity task.

- The standalone `/intermem:validate` skill adds a second user-facing surface area (beyond the pipeline integration) with distinct behavior. This is reasonable but doubles the test surface for Phase 1.

---

## 5. Architectural Justification Assessment

Generally well-justified. The SQLite choice cites ecosystem precedents (interspect, beads, interkasten). JSONL-as-source-of-truth deferral is explicitly argued and sound. The signal-based confidence scoring borrows from interwatch — justified by precedent.

One unjustified choice: **Why is the starting confidence 0.5 (neutral) rather than 1.0 (trusted until disproven)?** Starting at 0.5 means an entry with no extractable citations and no validation signals stays at 0.5 — below the promotion threshold? The doc doesn't say whether entries with confidence exactly 0.5 are promoted or filtered. This needs clarification.

---

## 6. Unidentified Risks

- **Regex false positives on citation extraction.** The doc acknowledges this as "medium risk" but doesn't name the specific failure mode: backtick-wrapped non-path tokens like `` `--write-output <path>` `` (listed in citation table as "CLI commands, not validatable") could be mistakenly classified as file paths if the regex isn't tight enough. Needs a concrete regex spec or an escape mechanism.

- **Performance at scale.** `os.path.exists()` is called per citation per entry. On a large project (thousands of entries, hundreds of citations each), this could slow synthesis meaningfully. No mention of batching, caching, or whether this is a concern.

- **Git subprocess in citations.py.** Phase 2 defers `git log --follow`, but even Phase 1 `validate_citation()` may need subprocess calls for edge cases. Running git subprocesses inside the synthesis pipeline creates a new failure mode (no git repo, slow git, detached HEAD) not addressed in risk assessment.

- **No mention of concurrent write safety.** The doc notes `busy_timeout = 5000` in Q2, but the WAL protocol used by journal.py for JSONL is not extended to metadata.db. If two synthesis runs overlap (e.g., two Claude sessions), citation_checks could have races.

---

## Summary of Issues to Fix Before PRD

1. Define fallback behavior when metadata.db is unavailable during synthesis.
2. Remove the rename-detection signal from the Phase 1 confidence scoring table (it's deferred to Phase 2).
3. Spec `import_from_stability()` or explicitly move it to Phase 2.
4. Clarify "function" and "pattern" citation types — either drop from Phase 1 schema or define them.
5. Define confidence=0.5 behavior: promoted or filtered?
6. Add a concrete regex spec or test cases for citation extraction to mitigate false positives.
7. Clarify "broken" vs "stale" behavioral distinction.
