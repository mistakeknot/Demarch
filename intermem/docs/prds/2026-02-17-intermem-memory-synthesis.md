# PRD: Intermem Phase 0.5 — Memory Synthesis
**Bead:** iv-3xm0

## Problem

Claude Code's auto-memory (`~/.claude/projects/*/memory/*.md`) grows monotonically until the 200-line cap silently truncates stable, hard-won lessons off the bottom. There is no graduation path — valuable knowledge that has proven stable across many sessions stays in the same ephemeral scratchpad as one-off observations.

## Solution

Build the **intermem** plugin's first capability: a memory synthesis system that reads auto-memory files, identifies stable facts, and promotes them to curated reference documents (AGENTS.md/CLAUDE.md) with user approval. Promoted items are pruned from auto-memory to reclaim space.

This is the designed **negative feedback loop** that prevents the auto-capture death spiral identified by fd-systems analysis.

## Features

### F1: Auto-Memory Scanner
**What:** Read and parse auto-memory files for the current project, extracting individual facts/entries with metadata.
**Delivery:** Skill-invoked module (not a standalone MCP server). Called by `/intermem:synthesize` skill.
**Acceptance criteria:**
- [ ] Reads all `*.md` files from the project's auto-memory directory (`~/.claude/projects/<encoded-cwd>/memory/`)
- [ ] Parses entries into structured data: content, section heading, approximate line range
- [ ] Handles markdown formatting (headers, bullet lists, code blocks) without corrupting entries
- [ ] Reports total line count and warns when approaching 200-line cap (>150 lines)

### F2: Stability Detection
**What:** Identify facts that have remained stable across multiple sessions, distinguishing durable knowledge from one-off observations.
**Design note (flux-drive):** File mtime is per-file, not per-entry — any edit to auto-memory updates all entries' mtime. Must use per-entry content hashing stored in `.intermem/stability.jsonl` to track entry-level history across sessions.
**Acceptance criteria:**
- [ ] Maintains a per-entry content hash store (`.intermem/stability.jsonl`) that persists across sessions
- [ ] On each scan, records entry hashes with timestamp; compares against prior snapshots
- [ ] Entries unchanged across 3+ snapshots scored "stable"; 1-2 snapshots "recent"; changed since last snapshot "volatile"
- [ ] Flags entries that were recently modified (unstable — skip for promotion)
- [ ] First run (no prior snapshots) records baseline — all entries scored "recent", none promoted. Builds history for future runs

### F3: Deduplication Checker
**What:** Check candidate promotions against existing AGENTS.md and CLAUDE.md content to avoid inserting duplicate knowledge.
**Acceptance criteria:**
- [ ] Reads target documents (AGENTS.md, CLAUDE.md) and extracts existing facts
- [ ] Compares candidate entries against existing content using fuzzy string matching (not exact — catches rephrased duplicates)
- [ ] Reports match confidence: exact duplicate (hash match), likely duplicate (>80% similarity), novel
- [ ] Auto-skips only exact hash matches; fuzzy matches (>80%) are flagged for interactive review in F4, never silently dropped
- [ ] Suggests merging when a candidate refines an existing entry rather than duplicating it

### F4: Interactive Promotion
**What:** Present stable, non-duplicate entries to the user for approval, then write approved entries to the correct section of AGENTS.md or CLAUDE.md.
**Acceptance criteria:**
- [ ] Presents candidates grouped by target document (AGENTS.md vs CLAUDE.md)
- [ ] Routing rule: structural/architectural facts → AGENTS.md, behavioral preferences → CLAUDE.md
- [ ] Batch approval UX: presents numbered list, user can "approve 1,3,5-8 / reject 2 / edit 4" in one command (not one-at-a-time)
- [ ] Fuzzy-match candidates from F3 shown with "[similar to existing]" annotation for informed decision
- [ ] Appends approved entries to end of closest matching section with `<!-- intermem -->` marker comment (smart section insertion deferred to Phase 1)
- [ ] Preserves existing document structure and formatting
- [ ] Produces a summary of what was promoted and where

### F5: Auto-Memory Pruner
**What:** Remove promoted entries from auto-memory files to reclaim space under the 200-line cap.
**Design note (flux-drive):** F4 promotion and F5 pruning must be atomic. Uses a promotion journal (`.intermem/promotion-journal.jsonl`) — entries are journaled before writing to target, then pruned from auto-memory. On crash recovery, replays incomplete journal entries.
**Acceptance criteria:**
- [ ] Only prunes entries that were successfully promoted (verified via promotion journal)
- [ ] Promotion journal records: entry hash, target file, target section, timestamp, status (pending/committed/pruned)
- [ ] Re-verifies target file content hash before pruning (detects concurrent edits during approval window)
- [ ] Removes the entry cleanly without leaving orphaned headers or blank lines
- [ ] Reports space reclaimed (lines removed) and new total line count
- [ ] Creates a backup of auto-memory before pruning (`.bak` file)
- [ ] Dry-run mode available (show what would be pruned without modifying)
- [ ] On startup, checks for incomplete journal entries and offers to resume or discard

## Non-goals

- **No standalone MCP server in this phase** — features are exposed as a skill (`/intermem:synthesize`) backed by a Python/bash module. MCP tools may wrap the module but no separate server process
- **No embeddings or vector search** — fuzzy string matching for dedup is sufficient for Phase 0.5
- **No cross-project synthesis** — operates on current project's auto-memory only
- **No automatic triggering** — user-initiated via skill only (hooks come in a later phase)
- **No decay/TTL system** — that's Phase 2
- **No multi-agent coordination** — single-agent operation only

## Dependencies

- Claude Code plugin system (skills, MCP tools)
- Access to `~/.claude/projects/*/memory/` directories
- Read/write access to project AGENTS.md and CLAUDE.md files
- No external libraries required for Phase 0.5

## Technical Constraints

- **Hook budget:** Clavain already has 12 hooks. Start with MCP tools + 1 skill only, no hooks
- **Token budget:** Memory injection must be token-aware (intermem content kept under 100 lines alongside auto-memory's 200)
- **Circular dependency guard:** `.intermem/` must be excluded from Interfluence's `learn-from-edits.sh` hook
- **Plugin structure:** Follow standard Interverse plugin layout (plugin.json, CLAUDE.md, AGENTS.md, skills/, tools/)

## Resolved Questions (from flux-drive review)

1. **Session tracking for stability:** ~~How to count "sessions"?~~ → Use per-entry content hashing in `.intermem/stability.jsonl`. Each `/intermem:synthesize` invocation is a "snapshot". Entries unchanged across 3+ snapshots are stable.
2. **Section targeting:** ~~How to identify the right section?~~ → Phase 0.5 appends to closest matching section with `<!-- intermem -->` marker. Smart insertion deferred to Phase 1.
3. **Fuzzy matching threshold:** Start at 80%. Fuzzy matches go to interactive review (never silently dropped). Only exact hash matches auto-skip.

## Remaining Open Questions

1. **Implementation language:** Python (matches intersearch/tldr-swinton) or bash (simpler, no deps)? Leaning Python for fuzzy matching and JSON handling.
2. **Zero-candidates UX:** What to show when first run finds no stable entries? Needs clear messaging: "Building baseline — run again after your next few sessions."
