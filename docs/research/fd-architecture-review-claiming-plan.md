# Architecture Review: Agent Claiming Protocol Plan

**Plan:** `docs/plans/2026-02-26-agent-claiming-protocol.md`
**Reviewer:** flux-drive architecture
**Date:** 2026-02-26
**Bead:** iv-sz3sf

---

## Summary Verdict

The plan is coherent and the targeted changes are small. The critical path (Batches 1-3) closes the collision gap without new infrastructure. Two issues need resolution before execution: the heartbeat boundary placement produces gratuitous load and belongs in a different plugin, and `bead_claim()` bridging adds a silent fallback that defeats the atomicity it is supposed to provide. Everything else is low-risk or cleanup.

---

## 1. Boundary and Coupling Analysis

### 1.1 The Three Identity Systems — Bridging Approach Is Partially Sound

**Existing systems:**
- `CLAUDE_SESSION_ID` — set in `os/clavain/hooks/session-start.sh`, unique UUID per session
- `INTERMUTE_AGENT_ID` / `INTERMUTE_AGENT_NAME` — set in `interverse/interlock/hooks/session-start.sh` via Intermute API call; these are already bridged to bead metadata by `os/clavain/hooks/bead-agent-bind.sh`
- `BD_ACTOR` — not currently set; all beads operations default to git user.name ("mistakeknot")

**What the plan proposes:** Add `BD_ACTOR = CLAUDE_SESSION_ID[:8]` in `os/clavain/hooks/session-start.sh`.

**What already exists but the plan ignores:** `bead-agent-bind.sh` already writes `INTERMUTE_AGENT_ID` and `INTERMUTE_AGENT_NAME` into bead metadata on every `bd update --claim` or `bd update --status=in_progress`. This is a fourth identity dimension the plan does not mention. The result after implementing the plan will be:
- `assignee` field = `BD_ACTOR` (session ID prefix, set by `--claim`)
- bead `metadata.agent_id` = `INTERMUTE_AGENT_ID` (UUID, set by `bead-agent-bind.sh`)
- bead `metadata.agent_name` = `INTERMUTE_AGENT_NAME` (human name from Intermute)
- `claimed_by` state = `CLAUDE_SESSION_ID` (full UUID, set by `bead_claim()`)
- `claimed_at` state = epoch int

**Issue:** Four overlapping identity representations on the same bead after a claim. The plan treats this as three systems; the actual number is four. The `bd-who` output will show `BD_ACTOR` (session prefix) while `bead-agent-bind.sh` overlap warnings will show `INTERMUTE_AGENT_NAME`. These are not the same string, so the human reading them gets two different names for the same agent on the same bead.

**Recommendation (must-fix):** The plan should decide which identity wins for bead assignee visibility and state it explicitly. The cleanest path: set `BD_ACTOR` to `INTERMUTE_AGENT_NAME` when interlock is installed and Intermute is reachable (the PRD cuts this as YAGNI, but the existing `bead-agent-bind.sh` already does the network call anyway, so there is no additional latency cost). If the PRD cut stands — session prefix is fine for v1 — then `bead-agent-bind.sh` should be updated to also write `agent_name` from `BD_ACTOR` so the two representations are at least consistent. Currently they will diverge.

**The session-start.sh layer choice is correct.** `BD_ACTOR` must be available before any hook runs, and `session-start.sh` is the right hook. The implementation in Batch 1 is minimal and additive.

### 1.2 Two Parallel Claiming Systems — The Bridge Has a Structural Problem

**Existing systems:**
- `bd update --claim` — atomic, sets `assignee` + `status=in_progress` in Dolt, fails on conflict
- `bead_claim()` / `bd set-state claimed_by/claimed_at` — soft advisory lock, TTL-based, lives in `lib-sprint.sh`

**What the plan proposes:** `bead_claim()` calls `bd update --claim` first; on Dolt lock timeout, falls back to the soft `bd set-state` path.

**Issue — the fallback defeats atomicity:** The soft-claim fallback on lock timeout means a session that hits contention silently proceeds with a non-atomic claim. Two sessions can both hit lock timeout simultaneously and both succeed with soft claims, which is exactly the collision scenario the plan is trying to prevent. The error type the plan checks ("lock|timeout") is a string grep on stderr, which is fragile — Dolt error messages are not a stable API.

The brainstorm document (Layer 1, Open Question 3) explicitly asks: "Should `sprint_claim()` and `bd update --claim` be unified or remain parallel systems?" The plan answers "bridge them" but the bridge has a silent degradation path that reintroduces the original bug under load.

**Recommendation (must-fix):** Remove the lock-timeout fallback from `bead_claim()`. Two options:

Option A (simpler): On lock timeout, fail the claim and return 1. Force callers to retry after a short delay. The PRD already accepts dolt contention as an acknowledged risk for 2-3 agents. Lock timeout (15s) is infrequent; forcing a retry is safe.

Option B (eliminating the parallel system): Keep only `bd update --claim` as the claiming primitive. Remove `bd set-state claimed_by/claimed_at` from `bead_claim()` entirely. The `claimed_by`/`claimed_at` state fields become redundant once `assignee` carries the actor identity and `lib-discovery.sh` reads `assignee` instead of `claimed_by`. This eliminates the parallel system rather than bridging it.

Option B requires changing the TTL check in `lib-discovery.sh` from reading `claimed_at` state to reading `updated_at` on the bead (already present in Dolt). This is more work but produces a single source of truth.

**The plan is right to keep both systems in the short term** — Option A is the correct v1 choice. Just remove the fallback so failure is visible rather than silent.

### 1.3 `sprint_claim()` Relationship to the Bridge

`sprint_claim()` (line 542, `lib-sprint.sh`) uses intercore serialization (`intercore_lock`) to guard the claim — a stronger guarantee than Dolt's process lock. After claiming via intercore, it calls `bead_claim()` for cross-session visibility.

After the plan's Batch 3, `bead_claim()` will call `bd update --claim`, meaning `sprint_claim()` will: (1) acquire intercore lock, (2) check intercore agent registry, (3) register agent in intercore, (4) call `bead_claim()` which calls `bd update --claim`, (5) also set `claimed_by`/`claimed_at` states.

This is five operations for one claim, with two different locking mechanisms. The plan does not address this layering. The critical concern is that `bd update --claim` inside the intercore lock will contend for the Dolt write lock while the intercore lock is held. If both locks are in play, any timeout in Dolt propagates into the intercore lock window, increasing the blast radius.

**Recommendation (must-fix):** `sprint_claim()` already provides the stronger guarantee via intercore. The `bead_claim()` call inside `sprint_claim()` should be demoted from "authoritative claim" to "audit trail write" — it should always call `bd set-state` directly (not `bd update --claim`) after the intercore lock succeeds. `bd update --claim` is the right primitive only for non-sprint beads claimed directly via route.md. The plan conflates these two call sites.

Concretely: split Batch 3 into two separate changes:
- For `sprint_claim()` context: keep `bead_claim()` using `bd set-state` (soft claim is fine here because intercore is the authoritative lock)
- For `route.md` direct claims: call `bd update --claim` directly, not via `bead_claim()`

---

## 2. Pattern Analysis

### 2.1 Heartbeat in PostToolUse — Wrong Architectural Boundary

**What the plan proposes:** Register a new `PostToolUse` hook in `os/clavain/hooks/hooks.json` with an empty matcher (`{}`) that fires on every tool call.

**Issue 1 — matcher `{}` fires on every tool call:** The existing PostToolUse hooks in `os/clavain/hooks/hooks.json` all use specific matchers (`Edit|Write|MultiEdit|NotebookEdit`, `Bash`). An empty matcher `{}` will fire the heartbeat script after every tool invocation — Read, Glob, Grep, TodoRead, Bash, Edit, everything. The script self-throttles via `BEAD_LAST_HEARTBEAT`, so only one `bd set-state` runs per 60 seconds, but the script is still launched as a subprocess on every tool call regardless. Claude Code hooks are process forks, not function calls.

At typical Claude Code usage rates (5-15 tool calls per minute), this is 5-15 additional subprocess forks per minute, each doing: env var read, `date +%s`, arithmetic, conditional exit. The 59 out of 60 forks that hit the short-circuit do minimal work, but the process overhead is non-trivial and accumulates in sessions with long planning/research phases.

**Issue 2 — wrong plugin ownership:** The heartbeat is a beads coordination concern, not a Clavain-specific concern. Any agent plugin (not just Clavain) might need to refresh a bead claim. Placing the heartbeat in `os/clavain/hooks/hooks.json` means the heartbeat only fires for Claude Code sessions running Clavain. Codex sessions (which also use beads) will not get the heartbeat. The brainstorm acknowledged this and suggested interphase (which already owns the discovery/claiming lifecycle) or interstat (which already has a PostToolUse hook) as alternative homes.

**Issue 3 — env file append grows unboundedly:** The heartbeat writes `export BEAD_LAST_HEARTBEAT=$now` to `$CLAUDE_ENV_FILE` on every heartbeat (once per 60s). `CLAUDE_ENV_FILE` is append-only; over a long session this means hundreds of duplicate `export BEAD_LAST_HEARTBEAT=...` lines. The env file is read at session start, so this does not break anything, but it is resource waste and unexpected for a file that other hooks also write to. The existing session-start hook writes to this file once; the heartbeat would write to it continuously.

**Recommendation (must-fix for Issue 2, should-fix for Issues 1 and 3):**

For Issue 1: Use a specific matcher rather than `{}`. Heartbeat only needs to confirm liveness during active work. Match `Bash|Edit|Write` — tool calls that represent active editing work, not passive reads. This cuts the launch rate by roughly 50% without changing effectiveness.

For Issue 2: Move the heartbeat to `interverse/interphase/hooks/hooks.json`. Interphase already owns discovery and the `claimed_at` TTL logic. The heartbeat is a natural extension of that ownership. Interphase hooks fire for any session with interphase installed, not just Clavain sessions.

For Issue 3: Instead of appending to `CLAUDE_ENV_FILE`, write `BEAD_LAST_HEARTBEAT` to a dedicated temp file keyed by session ID (e.g., `/tmp/clavain-heartbeat-${CLAUDE_SESSION_ID}`). Read from that file instead of env. This avoids unbounded env file growth and does not require env file infrastructure at all.

### 2.2 `bd-who` as Standalone Script — Factoring Is Correct but Placement Is Wrong

**What the plan proposes:** New script at `scripts/bd-who`, symlinked to `~/.local/bin/bd-who`.

**Correct:** Shell wrapper over `bd list --json | jq` is the right approach for v1. No new Go command needed; the brainstorm correctly identifies this as fast-to-ship.

**Issue — `scripts/` is for shared repo tooling:** The existing `scripts/` directory contains repo maintenance scripts (`interbump.sh`, `audit-roadmap-beads.sh`, `sync-roadmap-json.sh`, etc.) — tools for operating the monorepo itself. `bd-who` is not a repo maintenance tool; it is an agent coordination tool that would be useful in any beads-managed project.

The correct placement is `interverse/interphase/scripts/bd-who` (interphase owns discovery and bead lifecycle visibility) or `os/clavain/scripts/bd-who` (if Clavain-specific). The symlink into `~/.local/bin` is appropriate in both cases.

**Minor issue — jq grouping produces unstable output:** The `group_by(.assignee // "unclaimed")` in jq groups by assignee alphabetically. If `BD_ACTOR` is an 8-char session prefix, entries will be sorted by session prefix character, not by recency or priority. Consider sorting by `max(.updated_at)` within each group so the most recently active assignee appears first.

**Minor issue — grep -oP in bead-agent-bind.sh:** This is not part of the plan, but the reviewer notes that `bead-agent-bind.sh` line 34 uses `grep -oP` (Perl regex), which is not portable to macOS BSD grep. This follows the pattern flagged in `MEMORY.md` (Shell Portability section). Not relevant to the claiming plan but worth noting for the next sweep.

### 2.3 Modifying route.md (Prompt Layer) — Correct Layer Choice With Incomplete Failure Handling

**What the plan proposes:** Replace `bd update --status=in_progress` with `bd update --claim` in two places in `os/clavain/commands/route.md`, with inline failure handling text.

**Layer choice is correct.** `route.md` is the command prompt that Claude executes as instructions. Putting claim instructions in the prompt layer is right because the LLM needs to understand the failure mode and respond to it (re-run discovery, inform the user). A bash library cannot do this — only the LLM can decide what to do next. The plan's reasoning here is sound.

**Issue — failure handling text is in two different places with different verbosity:** Batch 2 adds detailed failure handling to line 125 (discovery routing step 5) but the line 233 change (dispatch routing step 3) says only "Same replacement and failure handling as above." The two call sites are structurally different: line 125 is inside a discovery flow that can re-run naturally, while line 233 is in the dispatch flow where re-running discovery has a higher cost. The failure text should be tailored to each context.

**Recommendation (should-fix):** Write out the full failure handling for line 233 separately. It should say something closer to: "If `--claim` fails with 'already claimed', this bead was just claimed by another agent. Do not proceed with the current bead. Restart from Step 1 of the discovery flow." The route.md at line 233 is deeper in the workflow; the agent needs an explicit instruction to unwind.

---

## 3. Simplicity and YAGNI Assessment

### 3.1 The bead_release() Gap

The plan updates `bead_release()` to add `bd update "$bead_id" --assignee="" --status=open`. However, `bead_release()` is called from `sprint_release()` (line 603) and must interact correctly with the sprint lifecycle. `sprint_release()` also interacts with intercore run agents. Changing `bead_release()` to call `bd update --assignee="" --status=open` means a sprint bead will be set back to `status=open` during sprint release, which may conflict with intercore's view of the sprint state.

`sprint_release()` handles the run agent cleanup separately from the bead state. If the bead is set to `open` by `bead_release()` while the sprint run is still active in intercore, there is a state inconsistency.

**Recommendation (must-fix):** Add a parameter to `bead_release()` to control whether it should reset status to `open`, or create a separate `bead_unclaim()` that only clears assignee without changing status. The `sprint_release()` call site at line 603 should call the status-preserving variant.

### 3.2 Session-End Best-Effort Release — Missing From Stop Hook

The plan adds best-effort release to the "session-end" or Notification hook. The existing hooks show there is no Notification hook in `os/clavain/hooks/hooks.json`; there is a `SessionEnd` hook (runs `dotfiles-sync.sh`) and a `Stop` hook (runs `auto-stop-actions.sh`). The plan says "check if Clavain has a Stop/Notification hook" without resolving this — it will need to be added to the existing `Stop` hook or `SessionEnd` hook.

**Critical constraint:** The `Stop` hook already uses `auto-stop-actions.sh`, which calls `intercore_check_or_die` to serialize stop actions. Adding `bead_release()` to the Stop hook must come after that check, or the release will run on every Stop event (including mid-session compound checks), releasing claims that should stay active.

The `SessionEnd` hook is the safer location — it fires only on actual session termination, not on mid-session stops. The plan should target `SessionEnd` explicitly, not leave it ambiguous.

### 3.3 TTL Reduction Is Safe But Asymmetric

The plan changes 7200s to 1800s in two files:
- `interverse/interphase/hooks/lib-discovery.sh` line 345 — stale-claim TTL
- `os/clavain/hooks/lib-sprint.sh` line 1332 — bead_claim() TTL

If only one file is updated (e.g., Batch 5 is partially executed), the two TTL values diverge. Discovery would release claims that bead_claim() still considers fresh (if discovery is updated first) or vice versa. The plan's execution order lists these as parallel steps in Batch 5 — they should be treated as a single atomic change.

### 3.4 No New Abstractions Are Introduced — Good

The plan adds no new interfaces, types, or architectural layers. Every change reuses existing primitives (`bd update --claim`, `bd set-state`, `CLAUDE_ENV_FILE`, existing hook registration). This is the correct level of complexity for a v1 protocol.

---

## 4. Integration Risk Assessment

### 4.1 Dolt Lock Contention Is the Dominant Risk

The plan acknowledges this explicitly (PRD Dependencies section). The practical risk at 2-3 agents is low, but the fallback in `bead_claim()` must be removed (see Section 1.2) or the fallback itself becomes an undetected failure mode.

The heartbeat adds another Dolt write per minute per active session. With 3 sessions, that is 3 writes per minute to a process-exclusive Dolt lock. The heartbeat writes are to `bd set-state` (a KV write, not a full commit), so they are lighter than `bd update`. Check whether `bd set-state` acquires the same Dolt write lock as `bd update` — if it does, the heartbeat rate should be reduced from 60s to 120s.

### 4.2 bead-agent-bind.sh Is Invisible to the Plan

The existing `bead-agent-bind.sh` hook fires on every `bd update --claim` (matched by the hook's case statement). After the plan's changes, every successful `bd update --claim` from `route.md` will trigger `bead-agent-bind.sh`, which makes a network call to Intermute to check agent online status. This is correct behavior, but the plan does not mention it.

If Intermute is offline, `bead-agent-bind.sh` exits at line 11 (`[[ -n "${INTERMUTE_AGENT_ID:-}" ]] || exit 0`) — the hook fast-exits when `INTERMUTE_AGENT_ID` is not set. If the plan sets `BD_ACTOR` (session prefix) but not `INTERMUTE_AGENT_ID`, `bead-agent-bind.sh` will be a no-op for sessions without interlock. This is the correct behavior and requires no change, but the plan should acknowledge it.

### 4.3 `bd-who` Adds Another Dolt Read

`bd-who` calls `bd list --status=in_progress --json`, which reads from Dolt. Under high concurrency, this read may block behind write locks held by claiming operations. The script has no timeout on the `bd list` call. Add `--timeout 5s` or equivalent if `bd` supports it, or wrap with `timeout 5 bd list ...`.

---

## 5. Ranked Findings

### Must-Fix (Correctness / Boundary Violations)

**M1. Remove the lock-timeout fallback from bead_claim().**
The fallback to soft-claim on Dolt timeout silently introduces the exact collision scenario the plan eliminates. On timeout, return 1 and let the caller retry. File: `os/clavain/hooks/lib-sprint.sh`, Batch 3.

**M2. Do not call `bd update --claim` inside sprint_claim().**
`sprint_claim()` already has the authoritative intercore lock. Inside `sprint_claim()`, `bead_claim()` should write `bd set-state` directly (soft claim as audit trail), not delegate to `bd update --claim`. The `bd update --claim` path is correct only for `route.md` direct claims. Files: `os/clavain/hooks/lib-sprint.sh`, Batch 3.

**M3. Add a status-preserving variant of bead_release().**
Setting `--status=open` in `bead_release()` will conflict with sprint bead lifecycle. `sprint_release()` calls `bead_release()` and should not reset the bead to open. Introduce a flag or separate function. File: `os/clavain/hooks/lib-sprint.sh`, Batch 3.

**M4. Resolve the four-identity conflict before shipping.**
After the plan, a single bead claim carries four distinct identity strings: `assignee` (BD_ACTOR prefix), `metadata.agent_id` (INTERMUTE_AGENT_ID UUID), `metadata.agent_name` (INTERMUTE name), `claimed_by` state (CLAUDE_SESSION_ID UUID). The `bd-who` output and the `bead-agent-bind.sh` overlap warning will report different names for the same agent. Define which field is the canonical display identity. At minimum, document this in the implementation so future reviewers understand the multiplicity.

### Should-Fix (Maintainability / Correctness Under Edge Cases)

**S1. Move the heartbeat hook to interphase, not clavain.**
Placing it in clavain silently excludes Codex sessions. Interphase owns the discovery/TTL lifecycle and is the correct home. Files: `interverse/interphase/hooks/hooks.json` + new `interverse/interphase/hooks/heartbeat.sh`, Batch 5.

**S2. Replace env-file heartbeat state with a temp file.**
`CLAUDE_ENV_FILE` is append-only; writing `export BEAD_LAST_HEARTBEAT=...` every 60s over a 4-hour session produces 240 lines. Write to `/tmp/clavain-heartbeat-${CLAUDE_SESSION_ID}` instead. File: `os/clavain/hooks/heartbeat.sh`, Batch 5.

**S3. Use a specific matcher for the heartbeat PostToolUse hook.**
Empty matcher `{}` forks the heartbeat script on every tool call including passive reads. Use `Bash|Edit|Write|MultiEdit` to match active-work tool calls only. This halves launch rate without affecting liveness semantics.

**S4. Target SessionEnd, not Stop or Notification, for best-effort release.**
Stop hook fires mid-session; SessionEnd fires on actual termination. Release must go in SessionEnd to avoid releasing active claims during compound checks. File: `os/clavain/hooks/hooks.json`, Batch 5.

**S5. Treat TTL changes in both files as a single atomic batch step.**
List them as a single step in Batch 5, not two independent steps. Divergent TTLs between `lib-discovery.sh` and `lib-sprint.sh` create inconsistent stale-claim behavior.

### Low-Priority (Cleanup)

**L1. Customize failure handling text for route.md line 233 separately from line 125.**
The dispatch routing context needs explicit "restart from discovery" instruction, not just a reference to the failure handling at line 125.

**L2. Move `bd-who` to interphase/scripts/ or os/clavain/scripts/, not top-level scripts/.**
Top-level `scripts/` is for repo maintenance tooling. `bd-who` is an agent coordination tool.

**L3. Add a timeout to the `bd list` call in `bd-who`.**
Prevents indefinite blocking if Dolt is locked by a concurrent write.

---

## 6. What Is Correct and Should Not Change

- **Batch 1 (BD_ACTOR from session ID prefix)** — minimal, additive, correct layer choice. No issues.
- **Batch 2 (route.md claim replacement)** — correct layer choice. Only the failure text completeness needs work (L1 above).
- **Batch 4 (bd-who script)** — correct primitive choice (jq over bd JSON). Only placement and minor UX details need adjustment.
- **F5 TTL reduction from 7200 to 1800** — correct direction. The heartbeat makes active claims immune to reaping, so 30min is safe.
- **Cutting agent bead registration, mcp-agent-mail bridge, and intercore backend** — all correct YAGNI calls for v1.
- **The brainstorm's Option C recommendation** (heartbeat + TTL) — architecturally sound. The implementation just needs the boundary corrections above.
