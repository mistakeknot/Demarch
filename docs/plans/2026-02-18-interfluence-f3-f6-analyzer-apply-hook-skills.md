# interfluence F3-F6: Analyzer, Apply, Hook, Skills Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use clavain:executing-plans to implement this plan task-by-task.

**Goal:** Update voice analyzer agent, apply skill, learning hook, and command router for multi-voice code-switching support.

**Architecture:** F3 is prompt engineering (voice-analyzer agent gains comparative analysis instructions). F4 is prompt + MCP tool wiring (apply skill gains voice resolution). F5 is a bash hook tweak (add CONTEXT:unknown tag). F6 is skill/command updates.

**PRD:** `docs/prds/2026-02-18-interfluence-code-switching.md` (F3-F6)
**Beads:** `iv-ulll` (F3), `iv-91jw` (F4), `iv-14vn` (F5), `iv-mwbv` (F6)

---

## Task 1: F3 — Update Voice Analyzer Agent for Comparative Analysis

**Files:**
- Modify: `plugins/interfluence/agents/voice-analyzer.md`

Update the agent to:
1. Classify corpus samples by context (blog vs docs) in-memory
2. Present classification summary before generating profiles
3. Extract cross-context invariants as base profile
4. Generate per-context deltas with only differing H2 sections
5. Save base via profile_save(projectDir), deltas via profile_save(projectDir, content, voice)
6. Handle graceful degradation (single context → base + one delta, no diversity → single base)
7. Skip empty deltas

Add `mcp_interfluence_profile_list` to allowed-tools.

## Task 2: F4 — Update Apply Skill for Voice Resolution

**Files:**
- Modify: `plugins/interfluence/skills/apply.md`

Update the skill to:
1. Accept optional `--voice=<name>` argument
2. Load config via config_get, resolve voice from file path using voices array
3. If --voice provided, use that (override). If auto-resolved, use that. Else use base.
4. Load base profile via profile_get(projectDir)
5. If voice != base, load delta via profile_get(projectDir, voice)
6. Merge: H2 sections from delta replace matching H2 sections in base
7. Report which voice was used and why in output

Add `mcp_interfluence_config_get, mcp_interfluence_profile_list` to allowed-tools.

## Task 3: F5 — Update Learning Hook for CONTEXT:unknown Tagging

**Files:**
- Modify: `plugins/interfluence/hooks/learn-from-edits.sh`

Simple change: add `CONTEXT:unknown` to the log entry format line.
Change: `--- ${TIMESTAMP} | ${RELATIVE_PATH} ---`
To:     `--- ${TIMESTAMP} | ${RELATIVE_PATH} | CONTEXT:unknown ---`

## Task 4: F5 (continued) — Update Refine Skill for Context-Aware Learning Review

**Files:**
- Modify: `plugins/interfluence/skills/refine.md`

Update to:
1. Load config to get voices mapping
2. When reviewing learnings tagged CONTEXT:unknown, resolve context from file path using current config
3. Present unresolved entries to user: "3 learnings from unknown contexts — assign them?"
4. When proposing profile updates, ask which voice they apply to (base, blog, docs)
5. Save updates to the correct voice via profile_save(projectDir, content, voice)

Add `mcp_interfluence_config_get, mcp_interfluence_profile_list` to allowed-tools.

## Task 5: F6 — Update Compare Skill for Multi-Voice

**Files:**
- Modify: `plugins/interfluence/skills/compare.md`

Update to:
1. Load all voices via profile_list
2. Compare text against each voice (base merged with each delta)
3. Show match scores for all voices with ranking
4. If file path provided, note which voice would auto-resolve from config

Add `mcp_interfluence_profile_list, mcp_interfluence_config_get` to allowed-tools.

## Task 6: F6 — Update Analyze Skill for Multi-Voice

**Files:**
- Modify: `plugins/interfluence/skills/analyze.md`

Update to:
1. Mention that analysis now produces base + context-specific voice deltas
2. After analysis, show classification summary and voice count
3. Reference profile_list to show available voices

Add `mcp_interfluence_profile_list` to allowed-tools.

## Task 7: F6 — Update Command Router

**Files:**
- Modify: `plugins/interfluence/commands/interfluence.md`

Add:
- `apply <file> --voice=<name>` — Apply with explicit voice selection
- `compare` — Show multi-voice match scores
- `voices` — List available voice profiles (maps to profile_list)

Add `mcp_interfluence_profile_list` to allowed-tools.

## Task 8: Build, Commit, Verify

No TypeScript changes needed for F3-F6 (all prompt/skill changes).
Commit all changes, push, close beads.
