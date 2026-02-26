# Synthesis: Agent Claiming Protocol Plan Review

**Bead:** iv-sz3sf
**Plan:** `docs/plans/2026-02-26-agent-claiming-protocol.md`
**Review Date:** 2026-02-26
**Reviewers:** Julik (correctness), flux-drive architecture, fd-safety
**Verdict:** NEEDS CHANGES (3 critical issues block execution)

---

## Executive Summary

The plan is fundamentally sound — it closes a real collision gap in agent work coordination using the existing `bd update --claim` atomic primitive. However, three **critical defects must be fixed before execution**:

1. **Silent soft-claim fallback** — Lock timeouts degrade to non-atomic claims that return success, reintroducing the collision the plan eliminates.
2. **Missing authorization check in bead_release()** — Any session can clear another session's active claim during transition windows.
3. **Heartbeat scope and boundary** — Wrong architectural home, wrong matcher (runs on every tool call), and unbounded env file growth.

Five additional **high-priority fixes** are needed for operational correctness and robustness. The plan is close to correct but must not ship in its current form.

---

## Critical Issues (Must Fix Before Execution)

### C1: Soft-Claim Fallback Returns Success When Claim Is Uncertain

**Location:** Batch 3, `bead_claim()` rewrite, lines 107–112

**Severity:** CRITICAL — enables the exact double-claim scenario the plan prevents

**The defect:**

```bash
if echo "$output" | grep -qi "lock\|timeout"; then
    # Dolt lock contention — fall back to legacy soft claim
    bd set-state "$bead_id" "claimed_by=$session_id" >/dev/null 2>&1 || true
    bd set-state "$bead_id" "claimed_at=$(date +%s)" >/dev/null 2>&1 || true
    return 0   # ← SUCCESS despite claim status unknown
fi
```

When `bd update --claim` times out after 15 seconds of Dolt lock contention, the code falls back to a soft advisory claim via `bd set-state` and returns exit code 0 (success). This means:

- Two agents hitting lock contention simultaneously both enter the fallback path
- Both succeed with soft claims (non-atomic, advisory-only)
- Both return 0, believing they hold exclusive access
- Both proceed to work the same bead in parallel
- This is the collision scenario the entire protocol exists to prevent

Dolt's 15-second lock timeout is not rare — with three agents heartbeating every 60s, one write is always in flight. The plan's own brainstorm acknowledges this risk but proposes a mitigation (fallback to soft claim) that is architecturally backwards. A lock timeout tells us "I couldn't acquire the lock to check" — not "the bead is free."

**Must fix:**

Remove the soft-claim fallback entirely. On lock timeout, fail hard:

```bash
bead_claim() {
    local bead_id="${1:?bead_id required}"
    local session_id="${2:-${CLAUDE_SESSION_ID:-unknown}}"
    command -v bd &>/dev/null || return 0

    local output retries=2 delay=1
    for (( i=0; i<retries; i++ )); do
        output=$(bd update "$bead_id" --claim 2>&1)
        if [[ $? -eq 0 ]]; then
            # Atomic claim succeeded
            bd set-state "$bead_id" "claimed_by=$session_id" >/dev/null 2>&1 || true
            bd set-state "$bead_id" "claimed_at=$(date +%s)" >/dev/null 2>&1 || true
            return 0
        fi

        if echo "$output" | grep -qi "already claimed"; then
            echo "Bead $bead_id already claimed by another agent" >&2
            return 1
        fi

        # Lock contention — retry once with backoff, then fail hard
        if (( i < retries-1 )); then
            sleep "$delay"
            delay=$(( delay * 2 ))
        fi
    done

    # All retries exhausted — fail (do NOT grant claim)
    echo "Bead $bead_id: could not acquire claim after $retries attempts (lock contention)" >&2
    return 1
}
```

The key change: lock timeouts return 1, forcing the caller to retry later. This is operationally correct — lock contention is transient.

---

### C2: `bead_release()` Clears Claims It Does Not Own

**Location:** Batch 3, `bead_release()` function definition

**Severity:** CRITICAL — enables cross-session claim interference during handoff

**The defect:**

```bash
bead_release() {
    local bead_id="${1:?bead_id required}"
    command -v bd &>/dev/null || return 0
    bd update "$bead_id" --assignee="" --status=open >/dev/null 2>&1 || true
    bd set-state "$bead_id" "claimed_by=" >/dev/null 2>&1 || true
    bd set-state "$bead_id" "claimed_at=" >/dev/null 2>&1 || true
}
```

There is no check that the calling session owns the claim. `session-end-handoff.sh` calls `bead_release "$CLAVAIN_BEAD_ID"` — but if two sessions share the same `CLAVAIN_BEAD_ID` (possible if env vars are inherited), or if discovery auto-releases a claim due to stale `claimed_at`, then Agent B picks up the bead, and Agent A's session-end hook clears Agent B's legitimate claim.

This window is narrow but real in a multi-agent system.

**Must fix:**

Add authorization check:

```bash
bead_release() {
    local bead_id="${1:?bead_id required}"
    command -v bd &>/dev/null || return 0

    # Only release if we own the claim
    local current_claimer
    current_claimer=$(bd state "$bead_id" claimed_by 2>/dev/null) || current_claimer=""
    local our_session="${CLAUDE_SESSION_ID:-unknown}"

    if [[ -n "$current_claimer" && \
          "$current_claimer" != "(no claimed_by state set)" && \
          "$current_claimer" != "$our_session" ]]; then
        # Another session holds this claim — do not release
        return 0
    fi

    bd update "$bead_id" --assignee="" --status=open >/dev/null 2>&1 || true
    bd set-state "$bead_id" "claimed_by=" >/dev/null 2>&1 || true
    bd set-state "$bead_id" "claimed_at=" >/dev/null 2>&1 || true
}
```

---

### C3: Heartbeat Hook Belongs in `interphase`, Not `clavain`

**Location:** Batch 5, hook registration in `os/clavain/hooks/hooks.json`

**Severity:** CRITICAL (architectural) — silently excludes Codex sessions; wrong plugin ownership

**The defect:**

The heartbeat is placed in `os/clavain/hooks/hooks.json` where it only fires for Claude Code sessions running Clavain. But any agent using beads (including Codex sessions) may need claim refresh. The brainstorm explicitly asks this question; the plan chooses Clavain without justification.

Additionally, the hooks.json entry uses an empty matcher `{}` which fires the heartbeat script on **every single tool call** (Read, Glob, Grep, Bash, Edit, all of them). The script self-throttles at 60 seconds, but the process fork overhead is incurred on every call — at 5-15 tool calls per minute, this is 5-15 forks/min hitting the short-circuit.

**Must fix:**

1. **Move to interphase:** `interverse/interphase/hooks/hooks.json` and new `interverse/interphase/hooks/heartbeat.sh`. Interphase owns discovery and the `claimed_at` TTL; the heartbeat is a natural extension. Codex sessions with interphase installed will also get the heartbeat.

2. **Use specific matcher:** Replace `"matcher": {}` with `"matcher": "Bash|Edit|Write|MultiEdit"` to match active work, not passive reads. This halves the fork rate.

3. **Fix timeout:** Change `"timeout": 5000` to `"timeout": 5` (5 seconds, not 5000ms).

4. **Fix env file growth:** Do NOT append to `$CLAUDE_ENV_FILE`. The script grows unboundedly — one `export BEAD_LAST_HEARTBEAT=...` line per minute per session. Use a temp file instead:

```bash
#!/usr/bin/env bash
# PostToolUse heartbeat — runs on active work, fires at most once per 60s

[[ -n "${CLAVAIN_BEAD_ID:-}" ]] || exit 0
command -v bd &>/dev/null || exit 0

_hb_lock="/tmp/clavain-heartbeat-${CLAVAIN_BEAD_ID}-${CLAUDE_SESSION_ID:-unknown}"
_hb_mtime=$(stat -c %Y "$_hb_lock" 2>/dev/null || echo 0)
now=$(date +%s)
(( now - _hb_mtime < 60 )) && exit 0

# Touch lockfile and refresh claim
touch "$_hb_lock" 2>/dev/null || true
bd set-state "$CLAVAIN_BEAD_ID" "claimed_at=$now" >/dev/null 2>&1 || true
exit 0
```

---

## High-Priority Issues (Required for Correctness)

### H1: Inconsistent State on Partial Failure After Atomic Claim

**Location:** Batch 3, `bead_claim()` success path, lines 100–103

**Severity:** HIGH — discovery cannot see claims that succeed atomically but fail in side-channel writes

**The issue:**

`bd update --claim` succeeds (atomic). Then the two `bd set-state` calls fail (lock timeout, or filesystem issue). The function returns 0 (success).

State after partial failure:
- `assignee` field = `BD_ACTOR` (atomic, correct)
- `claimed_by` side-channel = empty or stale (incorrect)
- `claimed_at` side-channel = empty or stale (incorrect)

Discovery checks `claimed_by`, not `assignee`. It doesn't see this claim. Another agent sees the bead as unclaimed, picks it up, and gets rejected by `--claim`. That agent then sees the lock-fallback (issue C1), applies a soft claim, and now two agents have different claim representations.

**Must fix:**

Replace `|| true` with logging so partial failures are visible:

```bash
if output=$(bd update "$bead_id" --claim 2>&1); then
    bd set-state "$bead_id" "claimed_by=$session_id" >/dev/null 2>&1 \
        || echo "WARN: bead_claim: failed to write claimed_by for $bead_id" >&2
    bd set-state "$bead_id" "claimed_at=$(date +%s)" >/dev/null 2>&1 \
        || echo "WARN: bead_claim: failed to write claimed_at for $bead_id" >&2
    return 0
fi
```

Longer-term: make discovery use `assignee` field from `bd show` rather than the side-channel `claimed_by` state. The atomic field is the source of truth; the side-channel should be audit trail only.

---

### H2: Heartbeat Throttle Is Not Reliable Across Concurrent Hook Processes

**Location:** Batch 5, heartbeat.sh, lines 204–206

**Severity:** HIGH — throttle depends on env var that isn't re-sourced between hook invocations

**The issue:**

```bash
now=$(date +%s)
last="${BEAD_LAST_HEARTBEAT:-0}"
(( now - last < 60 )) && exit 0
```

`BEAD_LAST_HEARTBEAT` is inherited from the environment at process start. It is not continuously re-evaluated. If Claude Code only sources `CLAUDE_ENV_FILE` between turns, not between hook invocations in the same turn, then:

1. Tool call 1 completes → heartbeat hook 1 starts with `last=T` → writes to env file
2. Tool call 2 completes immediately → heartbeat hook 2 starts with `last=T` (same stale value) → passes throttle check → both write

The throttle is unreliable. Over a session, you get duplicate heartbeat fires and duplicate `bd set-state` calls even though only one was intended per 60 seconds.

**Must fix:**

Use a file-based lock for throttle state (survives across processes):

```bash
_hb_lock="/tmp/clavain-heartbeat-${CLAVAIN_BEAD_ID}-${CLAUDE_SESSION_ID:-unknown}"
_hb_mtime=$(stat -c %Y "$_hb_lock" 2>/dev/null || echo 0)
now=$(date +%s)
(( now - _hb_mtime < 60 )) && exit 0

touch "$_hb_lock" 2>/dev/null || true
bd set-state "$CLAVAIN_BEAD_ID" "claimed_at=$now" >/dev/null 2>&1 || true
```

File mtimes are reliable across processes; env vars are not.

---

### H3: TTL Reduction to 30min Reaps Active Agents Waiting on External Calls

**Location:** Batch 5, lines 235–247 (TTL change from 7200 to 1800)

**Severity:** HIGH — agents lose claims while waiting on Oracle or external subprocess calls

**The issue:**

The heartbeat fires "on every tool use" (self-throttled to 60s). PostToolUse hooks do NOT fire during long-running operations that don't involve tool calls — Oracle review invocations (10–30 minutes), `claude --agent` subprocess calls (unbounded), external system waits.

Under 30min TTL, an agent waiting on Oracle for 20 minutes will have its claim auto-reaped by discovery before Oracle returns. When the agent's Oracle call completes, it has no idea its claim was stolen. It continues writing artifacts and closing the bead — while a second agent is doing the same work.

The brainstorm acknowledges this: "Post-tool heartbeat doesn't fire during long-running operations... An Oracle call can take 10–30 minutes." But the plan ships no mitigation. It claims "Active agents never lose claims" — this is incorrect. Active agents waiting on external calls for >30min will lose claims.

**Must fix — Option A (recommended):**

Keep TTL at 2h. Add skill-level instruction to manually refresh before Oracle:

```bash
# In os/clavain/skills/using-clavain/SKILL.md:
Before invoking Oracle or any external agent call that may take >10 min:
  bd set-state "$CLAVAIN_BEAD_ID" "claimed_at=$(date +%s)"
```

**Or Option B:**

Set TTL to 45min instead of 30min (provides buffer for most Oracle calls, ~P95 is 20–25min). Still a 3x improvement over 2h.

**Do not ship 30min without mitigation.** The protocol is correct, but the TTL is not safe for the known failure mode.

---

### H4: Four Overlapping Identity Systems on Same Bead

**Location:** Batch 1 and existing `bead-agent-bind.sh`

**Severity:** HIGH — operator confusion and logging inconsistency

**The issue:**

After the plan, a single bead claim carries four distinct identity strings:
- `assignee` field = `BD_ACTOR` (session prefix, 8 chars, set by `--claim`)
- `metadata.agent_id` = `INTERMUTE_AGENT_ID` (UUID, set by `bead-agent-bind.sh`)
- `metadata.agent_name` = `INTERMUTE_AGENT_NAME` (human name from Intermute, set by `bead-agent-bind.sh`)
- `claimed_by` state = `CLAUDE_SESSION_ID` (full UUID, set by `bead_claim()`)

When `bd-who` shows assignee (8-char session prefix) but `bead-agent-bind.sh` logs overlap warnings with INTERMUTE_AGENT_NAME, the human reading them sees two different names for the same agent on the same bead. This is confusing and error-prone.

**Must fix:**

Define canonical display identity. Options:

1. **Option A (recommended):** Set `BD_ACTOR` to `INTERMUTE_AGENT_NAME` when interlock is installed (make network call in session-start if needed; `bead-agent-bind.sh` already does this). Ensures display consistency.

2. **Option B:** Update `bead-agent-bind.sh` to also write `agent_name` from `BD_ACTOR` so both representations are consistent. Document this in the code.

At minimum, document the four-identity multiplicity in MEMORY.md so future reviewers understand why `bd-who` and logs show different names.

---

### H5: `sprint_claim()` Conflates Two Claiming Contexts

**Location:** Batch 3, interaction between `bead_claim()` and `sprint_claim()`

**Severity:** HIGH — misuse of `bd update --claim` inside a stronger intercore lock

**The issue:**

`sprint_claim()` (line 542, lib-sprint.sh) acquires an intercore lock (the authoritative guarantee). Then it calls `bead_claim()` which (after Batch 3) calls `bd update --claim` (a weaker Dolt-level lock). This means:

1. Intercore lock acquired
2. Intercore agent registry checked
3. Agent registered in intercore
4. `bead_claim()` calls `bd update --claim` (acquires Dolt write lock)
5. Also set `claimed_by`/`claimed_at` states

Five operations for one claim, mixing two locking mechanisms. If Dolt times out while the intercore lock is held, the blast radius expands.

The architecture review notes: `bd update --claim` is the right primitive for `route.md` direct claims (no intercore). Inside `sprint_claim()`, the soft claim via `bd set-state` is fine because intercore is the authoritative lock.

**Must fix:**

Split the implementation:
- Inside `sprint_claim()`: call `bead_claim()` but have it use `bd set-state` directly (soft claim as audit trail), not `bd update --claim`
- Outside `sprint_claim()` (route.md flow): call `bd update --claim` directly, not via `bead_claim()`

Restructure `bead_claim()` to accept a parameter flag or split into two functions: `bead_claim_atomic()` and `bead_claim_soft()`.

---

## Medium-Priority Issues (Should Fix)

### M1: BD_ACTOR Stability on Session Resume/Compact

**Location:** Batch 1, `BD_ACTOR` extraction from session_id

**Severity:** MEDIUM — may lock agents out of their own beads after compaction

**The issue:**

When a session is compacted or resumed, the `session_id` in the hook input may be a different value than the original. If `BD_ACTOR` changes, subsequent `bd update --claim` calls will use a new actor identity. The beads DB will have `assignee=old-prefix` but `BD_ACTOR=new-prefix`, causing claim rejection on the same bead.

The plan doesn't document whether Claude Code's compact event preserves session_id. If it changes, this is a P0. If it's preserved, low severity.

**Should fix:**

Verify Claude Code's compact behavior. If session_id changes on compact:

```bash
_hook_source=$(echo "$HOOK_INPUT" | jq -r '.source // "startup"' 2>/dev/null) || _hook_source="startup"
if [[ "$_hook_source" == "startup" && -n "$_session_id" ]]; then
    _bd_actor="${_session_id:0:8}"
    echo "export BD_ACTOR=${_bd_actor}" >> "$CLAUDE_ENV_FILE"
fi
# On resume/compact: BD_ACTOR is already set from startup, do not change
```

---

### M2: `bead_release()` Should Not Reset Bead Status to `open`

**Location:** Batch 3, `bead_release()` function

**Severity:** MEDIUM — conflicts with sprint bead lifecycle management

**The issue:**

`bead_release()` calls `bd update "$bead_id" --assignee="" --status=open`. But `sprint_release()` also interacts with intercore run agents. Setting `status=open` during a bead release may conflict with the sprint run state in intercore.

`sprint_release()` (line 603, lib-sprint.sh) calls `bead_release()` and should not reset the bead status.

**Should fix:**

Add a status-preserving variant or parameter:

```bash
bead_release() {
    local bead_id="${1:?bead_id required}"
    local preserve_status="${2:-false}"  # If true, don't change status
    command -v bd &>/dev/null || return 0

    [[ authorization check code from C2 ]]

    if [[ "$preserve_status" == "true" ]]; then
        bd update "$bead_id" --assignee="" >/dev/null 2>&1 || true
    else
        bd update "$bead_id" --assignee="" --status=open >/dev/null 2>&1 || true
    fi
    bd set-state "$bead_id" "claimed_by=" >/dev/null 2>&1 || true
    bd set-state "$bead_id" "claimed_at=" >/dev/null 2>&1 || true
}

# In sprint_release() at line 603:
bead_release "$bead_id" true  # preserve status for sprint lifecycle
```

---

### M3: JSON Validation on hooks.json Entry

**Location:** Batch 5, step 2 (hooks.json entry schema)

**Severity:** MEDIUM — proposed schema is invalid; hook won't fire

**The issue:**

The proposed hooks.json entry in the plan uses an incorrect schema:

```json
{
  "type": "PostToolUse",
  "matcher": {},
  "hooks": [...]
}
```

Actual hooks.json structure uses event name as key:

```json
{
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "...",
        "hooks": [
          {"type": "command", "command": "...", "timeout": 5}
        ]
      }
    ]
  }
}
```

**Should fix:**

Use correct schema:

```json
{
  "matcher": "Bash|Edit|Write|MultiEdit",
  "hooks": [
    {
      "type": "command",
      "command": "${CLAUDE_PLUGIN_ROOT}/hooks/heartbeat.sh",
      "timeout": 5
    }
  ]
}
```

This entry gets added to the existing `PostToolUse` array.

---

### M4: `bead_release()` Best-Effort Call Placement

**Location:** Batch 5, step 5 (session-end release)

**Severity:** MEDIUM — ambiguous hook target; Stop vs SessionEnd

**The issue:**

The plan says "check if Clavain has a Stop/Notification hook" without resolving where to add the release. The existing hooks are `SessionEnd` (runs `dotfiles-sync.sh`) and `Stop` (runs `auto-stop-actions.sh`).

The Stop hook fires mid-session (e.g., compound checks). Adding `bead_release()` there would release claims during these checks, which is wrong.

**Should fix:**

Target SessionEnd explicitly:

```bash
# In os/clavain/hooks/hooks.json, SessionEnd event
{
  "type": "SessionEnd",
  "hooks": [
    {
      "type": "command",
      "command": "${CLAUDE_PLUGIN_ROOT}/hooks/session-end-release.sh",
      "timeout": 5
    }
  ]
}
```

New file `os/clavain/hooks/session-end-release.sh`:

```bash
#!/usr/bin/env bash
# Best-effort claim release on clean session exit
[[ -n "${CLAVAIN_BEAD_ID:-}" ]] && command -v bd &>/dev/null || exit 0
bead_release "$CLAVAIN_BEAD_ID" 2>/dev/null || true
exit 0
```

---

## Low-Priority Issues (Nice-to-Have)

### L1: route.md Failure Handling Text for Dispatch Context

**Location:** Batch 2, line 233 (dispatch routing step 3)

The dispatch context is deeper in the workflow. The failure text should be explicit about unwinding:

```
If `--claim` fails with "already claimed", this bead was just claimed by another agent.
Do not proceed with dispatch. Restart from Step 1 of the discovery flow.
```

---

### L2: Script Placement for `bd-who`

**Location:** Batch 4, `scripts/bd-who`

Top-level `scripts/` is for repo maintenance. `bd-who` is an agent coordination tool. Prefer:
- `interverse/interphase/scripts/bd-who` (interphase owns discovery) or
- `os/clavain/scripts/bd-who` (if Clavain-specific)

---

### L3: Portable grep in `bead-agent-bind.sh`

**Location:** Pre-existing, `bead-agent-bind.sh` line 34

Uses `grep -oP` (Perl regex, not portable to macOS). Use `grep -Eo` instead for portable scripts.

---

## Deployment Checklist

Before execution:

- [ ] **C1** — Remove soft-claim fallback; add retry loop with hard failure
- [ ] **C2** — Add ownership check to `bead_release()`
- [ ] **C3** — Move heartbeat to interphase, fix matcher, fix timeout, replace env file with temp file
- [ ] **H1** — Add logging to side-channel write failures
- [ ] **H2** — Replace env-var throttle with file-based lock
- [ ] **H3** — Choose TTL mitigation (pre-Oracle heartbeat or 45min TTL)
- [ ] **H4** — Define canonical identity or ensure consistency
- [ ] **H5** — Split `bead_claim()` to separate sprint vs route contexts
- [ ] **M1** — Verify Claude Code compact behavior on session_id
- [ ] **M2** — Add status-preserving variant for sprint context
- [ ] **M3** — Validate hooks.json schema before merge
- [ ] **M4** — Use SessionEnd hook, not Stop hook

---

## Validation After Fixes

1. `bash -n os/clavain/hooks/{session-start,heartbeat,lib-sprint}.sh`
2. `python3 -c "import json; json.load(open('os/clavain/hooks/hooks.json'))"`
3. Manual: Two sessions attempt simultaneous `bd update <same-bead> --claim` — second fails with "already claimed" (not success)
4. Manual: Session A claims bead X, Session B picks it up after A releases — Session A's session-end should not clear Session B's claim
5. Manual: `bd-who` shows current in-progress beads, grouped by assignee (all 8-char session prefixes or all agent names, consistently)
6. Manual: Heartbeat fires during work session, `claimed_at` updates roughly every 60 seconds
7. Manual: `$CLAUDE_ENV_FILE` line count grows bounded (at most one new line per minute)

---

## Final Verdict

**Status:** NEEDS CHANGES

**Recommendation:** Return to execution team with the three critical fixes (C1, C2, C3) as mandatory blockers. High-priority fixes (H1-H5) must be completed before merge. Medium-priority fixes should go in before v1 ships. Low-priority fixes can be deferred to follow-up.

**Effort to fix:** ~3 hours (mostly in bead_claim rewrite, heartbeat refactor, TTL mitigation).

**Risk after fixes:** LOW — the protocol is sound once the fallback and authorization gaps are closed.

---

## Key Learnings for Future Agent Coordination Features

1. **Never fall back silently on lock timeouts.** Timeouts mean "I couldn't tell" not "the resource is free." Make failure visible.
2. **Authorize all release operations.** Releasing another agent's claim is an authorization violation disguised as cleanup.
3. **Know the heartbeat semantics.** PostToolUse hooks don't fire during long-running operations. If you rely on heartbeats for TTL guarantees, verify the operation won't exceed TTL without periodic tool calls.
4. **Use atomic primitives when available.** `bd update --claim` is atomic. `bd set-state` is not. Don't mix them as if they're equivalent.
5. **Avoid four-layer identity systems.** If four different fields on the same record represent the same logical entity, pick one canonical field and derive others from it.
