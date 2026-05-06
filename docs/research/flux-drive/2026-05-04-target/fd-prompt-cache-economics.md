### Findings Index
- P1 | C-01 | "Cache: MEMORY.md ordering puts churn before stable" | Active Projects + Active Brainstorms sit mid-file; Quick Reference + Discipline Lessons (stable) sit before; new-project additions invalidate trailing topic-file index
- P1 | C-02 | "Cache: bd prime double-fire invalidates per-event" | Each bd prime fire moves the cache cursor; the H-01/H-02 hook double-fire from fd-claude-code-hooks-economy compounds into wasted cache window
- P2 | C-03 | "Cache: ScheduleWakeup / /loop defaults likely cluster at 5min TTL boundary" | Common polling intervals risk landing exactly at 5-minute prompt-cache TTL — worst case for steady-state polling cost
- P2 | C-04 | "Cache: dynamic date string at top of context invalidates daily" | `Today's date is 2026-05-04` injected as system reminder rolls daily — content downstream cannot cache cross-day
- P2 | C-05 | "Cache: subagent dispatch prompts vary per-call (per-agent custom prompts)" | flux-drive Stage 1 fan-out emits per-agent prompts; cache reuse across the parallel dispatch is constrained by REVIEW_FILE path embedding the timestamp
- P3 | C-06 | "Cache: cass session-start auto-reindex sleeps may cross TTL on idle systems" | SessionStart hook chain can take >5min in worst case (heal-dolt + bd stats + bd prime + cass reindex), inviting cold-cache restart on resume

Verdict: needs-changes

## Summary

Sylveste's preamble structure shows two cache-cursor anti-patterns. First, MEMORY.md orders active-project state (most-churning section) above stable references like Quick Reference and Discipline Lessons — every new project entry invalidates the cache for everything below it, defeating the auto-load benefit. Second, the bd-prime double-fire identified by fd-claude-code-hooks-economy means each compact event walks the cache cursor twice through static text, paying full cache-creation cost on the second fire when it should have been a cache-read hit. The next ynh7-style win after content trim is *ordering* — moving stable text before churning text and aligning hook fires to cache-stable boundaries.

## Issues Found

### C-01 (P1) — MEMORY.md churning sections sit before stable sections, defeating cross-session caching

**Axis:** token-efficiency
**Current state:** `/home/mk/.claude/projects/-home-mk-projects-Sylveste/memory/MEMORY.md` is 132 lines. Section order observed:
1. Environment (~3 lines, semi-stable)
2. Quick Reference (~10 lines, stable)
3. Discipline Lessons (~30 lines, stable — append-only)
4. Fleet Registry & Cost Estimation (~15 lines, semi-stable)
5. Workflow Patterns (~20 lines, stable — append-only)
6. Infrastructure (~2 lines)
7. Strategic (~2 lines, semi-stable)
8. People & Corpora (~2 lines)
9. **Active Projects (~12 lines, HIGH CHURN — projects added/removed weekly)**
10. **Active Brainstorms (~5 lines, HIGH CHURN)**
11. Topic Files (~25 lines, mostly stable)
12. Session Continuity (~2 lines, churns every handoff)

The high-churn Active Projects and Session Continuity sections sit *between* large stable blocks (Discipline Lessons / Workflow Patterns above; Topic Files below). Every new project entry invalidates the cache for the Topic Files index and Session Continuity tail.

**Failure scenario:** User adds a new project to Active Projects (e.g., the recent flux-drive entries from 2026-04-26). The MEMORY.md cache region — let's call it ~6kt — is invalidated, even though only ~50 tok actually changed. Across a week with 5-7 memory edits, that's 30-40kt of cache misses where 350 tok of new content would suffice.

**Proposal:** Reorder MEMORY.md so churning sections sit at the *bottom*. Target order:
1. Environment + Quick Reference (stable header)
2. Discipline Lessons (append-only — extends cleanly)
3. Workflow Patterns (append-only)
4. Topic Files (mostly stable — index of references)
5. People & Corpora, Infrastructure, Strategic
6. Fleet Registry (semi-stable)
7. **Active Projects** (high churn — at bottom)
8. **Active Brainstorms** (high churn)
9. **Session Continuity** (rolls every handoff — last)

Cache cursor lands after the stable block. Memory edits in Active Projects only invalidate the small tail.

**Estimated savings:** Cache-creation tokens drop on memory-edit sessions. If a memory edit currently triggers 6kt of cache miss and would trigger ~500 tok after reorder, that's 5.5kt × frequency-of-memory-edit. At 5 edits/week × ~50 sessions affected, ~275-1500kt/week of cache-creation cost reclaimed. (Cache-read tokens are ~10% of cache-creation, so the steady-state win is real but smaller.)
**Difficulty:** XS (one-file reorder).
**Risk:** Low. Memory contents are unchanged; only layout moves. User may have muscle-memory for section positions.

### C-02 (P1) — bd prime double-fire walks the cache cursor twice through static text

**Axis:** token-efficiency
**Current state:** Per fd-claude-code-hooks-economy H-01/H-02: `bd prime` is registered for both PreCompact and SessionStart-empty-matcher. On a compact event both fire. Each fire emits ~917 bytes (~230 tok) of static prose. The first fire creates a cache region. The second fire emits the *same content* but at a new cache offset (because intervening content moved the cursor) — paying cache-creation cost again instead of cache-read.

**Failure scenario:** Long session triggers auto-compact at the 80% mark. PreCompact bd-prime fires (cache-create 230 tok). Compact happens. SessionStart-empty bd-prime fires immediately after (cache-create another 230 tok at new offset). Static content paid for twice in the same minute.

**Proposal:** Fix the hook double-fire (see fd-claude-code-hooks-economy H-01/H-02). Beyond that: ensure the hook output is deterministic byte-for-byte across consecutive fires. Today `bd prime` may include non-deterministic elements (timestamp, current bead count) — verify with `diff <(bd prime) <(bd prime)` and stabilize any non-deterministic fields if found.

**Estimated savings:** ~230 tok cache-creation reclaimed per compact event (already counted by hooks-economy H-01).
**Difficulty:** XS (covered by H-01/H-02 fix).
**Risk:** None.

### C-03 (P2) — ScheduleWakeup / /loop defaults likely cluster around 5-minute prompt-cache TTL boundary

**Axis:** token-efficiency
**Current state:** The Anthropic prompt cache TTL is 5 minutes (300 seconds). Sylveste's `/loop` skill description states "Run a prompt or slash command on a recurring interval (e.g. /loop 5m /foo)." If users default to `5m` (the example interval), wakeups land *exactly* at the cache TTL boundary — the worst case, where on each wakeup the cache has *just* expired. Sleeps slightly under 5m would amortize within the cache window; sleeps significantly over 5m wouldn't matter (cold cache anyway). The 300s ± 30s zone is the highest-cost zone.

**Failure scenario:** A user starts `/loop 5m /sprint-status`. Each tick, the cache from the previous tick has just expired by 0-60s, causing full preamble cache-creation cost (~5-10kt) every 5 minutes instead of cache-read at <1kt. Across 12 ticks/hour the difference is ~50-100kt/hour wasted.

**Proposal:** Change `/loop` default and example interval to `4m` (240s) — comfortably inside the 5-min TTL, preserving cache hits across consecutive ticks. Or: introduce `/loop --cache-aware` which sets interval to `min(user_interval, 240)` and warns if user_interval > 240. Document the 5-minute TTL boundary in `interlab` / `interlock` skill docs.

**Estimated savings:** Conditional on usage. For active /loop users, ~50% reduction in preamble cache-creation cost per tick over the 5min boundary. At 1-2kt/tick × 12 ticks/hour = 12-24kt/hour reclaimed.
**Difficulty:** XS (default change in /loop).
**Risk:** Low. Tighter polling interval is a slight behavior change but well within usability.

### C-04 (P2) — Daily date stamp injected at preamble top invalidates downstream cache every midnight

**Axis:** token-efficiency
**Current state:** The system context injected in this session contains `# currentDate\nToday's date is 2026-05-04.` This text changes daily. Where it sits in the preamble determines what cache tail it invalidates. If it sits *before* CLAUDE.md / MEMORY.md content (typical placement for "system context" injection), then every day-rollover invalidates everything downstream.

**Failure scenario (frame as question):** Does the daily date stamp sit before or after MEMORY.md in the assembled preamble? If before, the first session of each new day pays full cache-creation cost for MEMORY.md + skill listings + deferred tools — even though only ~30 tokens changed.

**Proposal:** Verify ordering with a debug log of the actual sent context (Claude Code may expose this via `--debug-context` or similar). If date sits before stable content: file an upstream Claude Code bug or work around by stripping the harness-injected date and reinjecting at preamble end via a SessionStart hook.

**Estimated savings:** Conditional on verification. If date currently invalidates 10kt of downstream content, fix saves ~10kt × first-session-of-day × 365 = ~3.6Mt/year per active user.
**Difficulty:** XS (verify); S (workaround if confirmed).
**Risk:** None.

### C-05 (P2) — flux-drive subagent dispatch embeds REVIEW_FILE timestamp, defeating cross-agent cache

**Axis:** token-efficiency
**Current state:** Per `phases/launch.md` Step 2.1c: `REVIEW_FILE = /tmp/flux-drive-${INPUT_STEM}-${TS}.md` where `TS = $(date +%s)`. All agents in a Stage 1 dispatch reference this file. But the agent prompt itself includes `Read this file: /tmp/flux-drive-myname-1777878620.md` — the timestamp is unique per dispatch. So between two consecutive flux-drive runs (e.g., one for Track A, one for Track B during the current 2026-05-04-target review), the prompt prefix differs by the timestamp segment, defeating cache reuse across runs.

**Failure scenario:** User runs `/flux-drive` twice in a session (Track A then Track B), each dispatching 5 agents in parallel. Each of the 10 agent prompts re-creates cache for the agent system prompt + project context, because the timestamp in the file path varies the prompt prefix.

**Proposal:** Move the timestamp from filename to a content header. Use a stable filename like `/tmp/flux-drive-current.md` (overwritten each run) or `/tmp/flux-drive-${INPUT_STEM}.md` (overwrite-stable). Subagents Read by stable name; the in-session "this is the latest" semantics are managed by the orchestrator. Then place the timestamp inside the file as the first line for traceability.

**Estimated savings:** Per multi-track flux-drive run, ~500-2000 tok cache-creation reclaimed across parallel agents. At 2-5 runs/day, ~1-10kt/day.
**Difficulty:** S (modify launch.md Step 2.1c contract; ensure no race between concurrent flux-drive instances).
**Risk:** Medium — concurrent flux-drive runs would step on the shared filename. Mitigation: lock-file or PID-suffixed name where the PID is known to all subagents in that run.

### C-06 (P3) — Long SessionStart hook chain may cross 5-min TTL on idle resume

**Axis:** token-efficiency
**Current state:** SessionStart hooks chain: `heal-dolt.sh → bd stats → bd prime → guard-enabled-plugins.sh → cass auto-reindex (background, but per MEMORY.md "auto-indexes cass when stale >1hr (background)")`. On a fresh `--resume` of a session paused 6+ hours, the user's elapsed wall-clock between previous session end and resume already exceeded the 5-min TTL, so cache is cold regardless. But on a resume after a *short* pause (e.g., 4-6 minutes), the cumulative SessionStart latency could push the resume past the TTL boundary.

**Failure scenario (frame as question):** If the user pauses mid-session for 4 minutes and then resumes, do the SessionStart hooks (network calls in heal-dolt, possible cass invocations) take >60s, pushing the user past the 5-min TTL window when they would have made it otherwise?

**Proposal:** Profile SessionStart total wall time on a representative project. If consistently <30s, no action. If >60s in any case, move the slowest hooks (cass background reindex, network-touching health checks) to async-detached background and let the agent-facing hooks complete in <10s.

**Estimated savings:** Conditional. Per cold-cache restart on resume = ~5-10kt of cache-creation forfeit.
**Difficulty:** S (profile + hook reorder).
**Risk:** Low. Async-detached health checks may surface their failures less loudly; mitigate with a notify-only retry on next SessionStart.

## Improvements

1. **Document the cache-cursor model in `docs/canon/preamble-engineering.md`** (new doc). Stable text first; churn last; per-session deltas at the very bottom. This becomes the design rule for every future preamble-trim PR (sylveste-ynh7 follow-ups).
2. **Add a debug helper:** `scripts/dump-preamble.sh` that captures the ordered preamble structure (CLAUDE.md → MEMORY.md → skill listings → deferred tools → hooks output → date stamp), counts tokens per region, and color-codes stable vs churning. Useful for verifying C-04 and C-01 fixes empirically.
3. **Pin /loop and ScheduleWakeup defaults below 5-minute TTL in plugin docs.** Add a `# Cache-aware polling` section to interlab/interlock SKILL.md.
4. **Cache-stable subagent prompts:** Adjust `phases/launch.md` so Stage 1 dispatches share the agent persona (system prompt) prefix exactly across all agents in the run, with per-agent variation only in the trailing `Focus Area` section. This maximizes prefix-cache reuse.

<!-- flux-drive:complete -->

--- VERDICT ---
STATUS: warn
FILES: 0 changed
FINDINGS: 6 (P0: 0, P1: 2, P2: 3, P3: 1)
SUMMARY: MEMORY.md churn-before-stable ordering invalidates ~6kt cache region per memory edit; bd prime double-fire wastes cache cursor. Plus /loop default likely lands on 5min TTL boundary and the flux-drive review-file timestamp defeats cache reuse across consecutive runs. Cache-aware reorder is the next ynh7 win.
---
