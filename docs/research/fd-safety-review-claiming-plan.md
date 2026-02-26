# Safety Review: Agent Claiming Protocol Plan
**Plan:** `/home/mk/projects/Demarch/docs/plans/2026-02-26-agent-claiming-protocol.md`
**Brainstorm:** `/home/mk/projects/Demarch/docs/brainstorms/2026-02-26-agent-claiming-protocol.md`
**Date:** 2026-02-26
**Reviewer:** fd-safety (Flux-drive Safety Reviewer)
**Risk Classification:** Medium — new coordination surface, trust boundary between agents, no external network exposure, no credential handling

---

## Threat Model Assessment

This plan operates entirely within a single-machine, internal-tooling context. The system manages work coordination between multiple Claude Code agent sessions running locally. There is no public network exposure. The beads database (dolt) is local. Intermute is loopback-only (127.0.0.1:7338). The trust boundary is: sessions on the same machine are assumed to be co-operating agents run by the same user, not adversarial actors.

With that established, the realistic threats are:
- **Intra-agent trust violation**: one session maliciously or accidentally releasing/overwriting another session's claim
- **Shell injection**: unvalidated data from `bd` output or env vars being interpolated into shell commands
- **ENV file write contention**: concurrent hooks appending to the same file corrupting its content
- **Heartbeat amplification**: PostToolUse hook firing too frequently and saturating the dolt lock
- **Silent soft-claim fallback**: lock contention masking a real claim conflict, defeating the protocol's purpose
- **Information exposure**: `bd-who` surfacing sensitive bead titles to unintended consumers

---

## Finding 1 — CRITICAL: Soft-Claim Fallback Silently Defeats the Protocol

**Location:** `docs/plans/2026-02-26-agent-claiming-protocol.md`, Batch 3, `bead_claim()` rewrite, lines 107-112

**The code:**
```bash
# Distinguish lock contention from actual claim conflict
if echo "$output" | grep -qi "lock\|timeout"; then
    # Dolt lock contention — fall back to legacy soft claim
    bd set-state "$bead_id" "claimed_by=$session_id" >/dev/null 2>&1 || true
    bd set-state "$bead_id" "claimed_at=$(date +%s)" >/dev/null 2>&1 || true
    return 0   # <-- success return despite no atomic claim
fi
```

**Problem:** When `bd update --claim` fails due to dolt lock contention, the plan falls back to the legacy advisory `bd set-state` approach and returns exit code 0. This means the caller cannot tell whether the claim was atomic (exclusive via `--claim`) or soft (advisory via `set-state`). Two sessions hitting lock contention simultaneously will both fall through to `bd set-state`, both get `return 0`, both believe they hold the bead, and both start working. This is the exact collision the entire protocol is designed to prevent — and the silent success return actively hides the failure.

The brainstorm acknowledges this: "Two concurrent `bd` commands contend for a 15s lock. Under high concurrency, `bd update --claim` may timeout with a lock error, not a clean 'already claimed' rejection." But the proposed mitigation (fall back to soft claim + return 0) makes the protocol useless in the failure case that is most likely during actual contention: the moment two sessions simultaneously race to claim the same bead.

**Impact:** High probability of producing the wrong outcome in the exact concurrent-claim scenario the feature exists to prevent. Any "atomicity guarantee" advertised to callers in route.md and SKILL.md is false when dolt is under load.

**Mitigation options:**
1. Return a distinct exit code (e.g., 2) for "lock contention, claim status unknown" so callers can decide to retry or abort. Do not return 0 from the contention path.
2. Retry once with a 1-2 second sleep before falling back. The 15s dolt lock timeout means contention is transient — a single retry usually resolves it. If the retry also fails with "lock\|timeout", return exit code 2 (not 0, not 1).
3. If the soft-claim fallback must be kept for operational resilience, emit a distinct return code (e.g., 3 for "soft claim only, exclusivity not guaranteed") so callers can log a warning or degrade gracefully rather than treating it as equivalent to an atomic claim.

---

## Finding 2 — HIGH: ENV File Write Contention Between Concurrent Hooks

**Location:** Batch 1 (session-start.sh line 24) and Batch 5 (heartbeat.sh line 213)

**The pattern:**
```bash
# session-start.sh
echo "export BD_ACTOR=${_bd_actor}" >> "$CLAUDE_ENV_FILE"

# heartbeat.sh (PostToolUse, fires on every tool call)
echo "export BEAD_LAST_HEARTBEAT=$now" >> "$CLAUDE_ENV_FILE"
```

**Problem:** Both session-start.sh and heartbeat.sh append to `$CLAUDE_ENV_FILE` with simple `>>` redirections. The existing session-start.sh already does this for `CLAUDE_SESSION_ID`, `IC_TRACE_ID`, and `IC_SPAN_ID`. Adding `BD_ACTOR` is low risk there since session-start fires once.

The heartbeat is a different risk profile. PostToolUse fires after every tool call. If two tool calls complete in rapid succession (e.g., parallel Bash + Read calls), two heartbeat.sh processes can run concurrently, both appending to `$CLAUDE_ENV_FILE`. On Linux, appends to the same file from two processes are not atomic for writes larger than PIPE_BUF (4096 bytes). A single `echo` line is small enough to be atomic in practice, but the real risk is interleaving of multiple writes in the same process: the heartbeat does two operations — first checking `$BEAD_LAST_HEARTBEAT` (read from env, not the file), then writing back to the file. There is a TOCTOU window between the throttle check and the file write. Two concurrent heartbeats both pass the throttle check at `last="${BEAD_LAST_HEARTBEAT:-0}"` (same stale env value) and both write. This is benign for heartbeat (both write the same timestamp) but demonstrates the pattern is not safe for a write that has semantic significance.

The more serious concern: if Claude Code processes `CLAUDE_ENV_FILE` as a sourced script and two concurrent writes produce a partially-overwritten line (unlikely for single `echo` but possible under load), the env file becomes unparseable and the session loses all exported env.

**Impact:** Medium. Heartbeat writes are idempotent (same value twice is fine). But the write pattern establishes a precedent that other contributors may follow for non-idempotent values.

**Mitigation:**
1. For the heartbeat specifically: use `flock "$CLAUDE_ENV_FILE"` around the write or write to a separate per-session temp file that gets merged at defined sync points.
2. Stronger: deduplicate the env file at write time. After appending, deduplicate with `sort -u` or use `grep -qxF "export BEAD_LAST_HEARTBEAT=..." "$CLAUDE_ENV_FILE" || echo "..." >> "$CLAUDE_ENV_FILE"` to prevent accumulation of stale heartbeat lines. Without deduplication, `$CLAUDE_ENV_FILE` will accumulate one `export BEAD_LAST_HEARTBEAT=...` line per minute per session indefinitely.
3. Minimum: the heartbeat should check whether the same value is already in the file and skip the write if so, using a grep guard: `grep -qF "export BEAD_LAST_HEARTBEAT=$now" "$CLAUDE_ENV_FILE" 2>/dev/null || echo "export BEAD_LAST_HEARTBEAT=$now" >> "$CLAUDE_ENV_FILE"`.

---

## Finding 3 — HIGH: Shell Injection in bead-agent-bind.sh (Existing File, Batch 3 Interacts)

**Location:** `/home/mk/projects/Demarch/os/clavain/hooks/bead-agent-bind.sh`, line 34 and line 93

This is an existing file that Batch 3 touches indirectly (it reads `bd update --claim` invocations from hook input). Two issues in the existing code that the plan inherits:

**Issue 3a — `grep -oP` on tool_input.command (line 34):**
```bash
ISSUE_ID=$(echo "$COMMAND" | grep -oP '(?<=bd (?:update|claim) )\S+' 2>/dev/null) || exit 0
```
The `ISSUE_ID` extracted from the raw shell command text is then passed to:
```bash
bd update "$ISSUE_ID" --metadata "{\"agent_id\":\"${INTERMUTE_AGENT_ID}\",\"agent_name\":\"${AGENT_NAME}\"}" 2>/dev/null || true
```
The `ISSUE_ID` is quoted in the `bd update` call so direct shell injection is blocked. However if a session runs `bd update "iv-foo; rm -rf ~" --claim`, the bead ID extracted by grep will be `iv-foo;` (including the semicolon — grep stops at whitespace, not semicolon). Bead IDs appear to be structured (e.g., `iv-sz3sf`), so in practice this is low risk. But the correct fix is to validate ISSUE_ID against a strict allowlist: `[[ "$ISSUE_ID" =~ ^[a-z]{2,4}-[a-z0-9]{5,}$ ]] || exit 0`.

**Issue 3b — Unquoted metadata interpolation (line 93):**
```bash
bd update "$ISSUE_ID" --metadata "{\"agent_id\":\"${INTERMUTE_AGENT_ID}\",\"agent_name\":\"${AGENT_NAME}\"}" 2>/dev/null || true
```
`INTERMUTE_AGENT_ID` and `INTERMUTE_AGENT_NAME` come from env vars. If these are set to values containing JSON metacharacters (e.g., `"` or `}`), the metadata JSON will be malformed and may either fail silently or, depending on how `bd` parses it, cause unexpected behavior. Should use `jq -nc` to build the JSON safely (same pattern recommended in MEMORY.md under "JSON injection in hook heredocs").

**Impact:** Medium. These are an internal-tooling context with co-operating agents. But if a session's env vars are set to unexpected values (e.g., via a malformed tool output), the metadata write becomes a reliability risk.

**Mitigation:** Use `jq -nc --arg agent_id "$INTERMUTE_AGENT_ID" --arg agent_name "$AGENT_NAME" '{agent_id: $agent_id, agent_name: $agent_name}'` to construct the metadata JSON.

---

## Finding 4 — MEDIUM: BD_ACTOR is Not Validated Before Writing to ENV File

**Location:** Batch 1, session-start.sh addition

**The code:**
```bash
_bd_actor="${_session_id:0:8}"
echo "export BD_ACTOR=${_bd_actor}" >> "$CLAUDE_ENV_FILE"
```

**Problem:** `_session_id` comes from `jq -r '.session_id // empty'` on the Claude Code hook input JSON. The plan trusts that this is always a clean UUID. If it is, `${_session_id:0:8}` is an 8-character hex/hyphen substring — safe for env var values.

However, the env file line is written as `export BD_ACTOR=${_bd_actor}` without quoting the value. If `_bd_actor` ever contains whitespace or shell metacharacters (e.g., if the session_id format changes or an edge case produces a non-UUID), the unquoted `echo "export BD_ACTOR=${_bd_actor}"` produces a valid-looking but syntactically broken env file line. Compare with the existing pattern in the same file:
```bash
echo "export CLAUDE_SESSION_ID=${_session_id}" >> "$CLAUDE_ENV_FILE"
```
This is the same unquoted pattern already used in the codebase, so the plan matches existing precedent. The risk is the same as the existing code. However, the fix is trivial: `echo "export BD_ACTOR='${_bd_actor}'"` or double-quoted: `echo "export BD_ACTOR=\"${_bd_actor}\""`.

**Impact:** Low in practice since session IDs are UUIDs. But worth fixing for consistency and future-proofing.

---

## Finding 5 — MEDIUM: bead_release() Has No Caller Authorization Check

**Location:** Batch 3, `bead_release()` rewrite

**The code:**
```bash
bead_release() {
    local bead_id="${1:?bead_id required}"
    command -v bd &>/dev/null || return 0
    bd update "$bead_id" --assignee="" --status=open >/dev/null 2>&1 || true
    bd set-state "$bead_id" "claimed_by=" >/dev/null 2>&1 || true
    bd set-state "$bead_id" "claimed_at=" >/dev/null 2>&1 || true
}
```

**Problem:** Any session can call `bead_release` with any bead ID and it will unconditionally reset status to open and clear the assignee. There is no check that the calling session is the one that holds the claim. The session-end-handoff.sh already calls this:
```bash
if [[ -n "${CLAVAIN_BEAD_ID:-}" ]] && command -v bd &>/dev/null; then
    source "${BASH_SOURCE[0]%/*}/lib-sprint.sh" 2>/dev/null || true
    bead_release "$CLAVAIN_BEAD_ID" 2>/dev/null || true
fi
```
That call is appropriately scoped to `CLAVAIN_BEAD_ID` which belongs to the current session. But nothing prevents a future caller (or a bug in routing) from calling `bead_release` on a bead owned by a different session.

The brainstorm question asks: "could an agent maliciously release another agent's claim?" — in the current single-user trust model, this is a bug risk rather than a security risk. But it becomes a coordination bug when a session-end hook fires with a stale `CLAVAIN_BEAD_ID` that another session has since legitimately claimed.

**Impact:** Medium. In the concurrent-agents scenario, a session that exits while another session has legitimately taken over the same bead will release the new session's claim. The window is short but real.

**Mitigation:** Add an authorization check to `bead_release`:
```bash
bead_release() {
    local bead_id="${1:?bead_id required}"
    command -v bd &>/dev/null || return 0
    # Only release if we hold the claim (or if claim is stale/empty)
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

## Finding 6 — MEDIUM: Heartbeat PostToolUse Registration Uses Broad Matcher (DoS / Lock Flooding)

**Location:** Batch 5, hooks.json entry

**The proposed registration:**
```json
{
  "type": "PostToolUse",
  "matcher": {},
  "hooks": [
    {
      "command": "bash ${CLAUDE_PLUGIN_ROOT}/hooks/heartbeat.sh",
      "timeout": 5000
    }
  ]
}
```

**Problem 1 — Empty matcher fires on every tool call.** The existing PostToolUse hooks use specific matchers (`"Edit|Write|MultiEdit|NotebookEdit"`, `"Bash"`). The heartbeat uses `{}` (empty object, meaning match all). During a heavy session using Bash, Read, Glob, Grep, and Edit tools in rapid succession, this fires the heartbeat script on every single tool call. The script self-throttles at the bash level via `(( now - last < 60 ))`, but the process spawn overhead is incurred for every tool call even when the throttle rejects.

**Problem 2 — The throttle depends on an env var that may not be current.** The check is:
```bash
last="${BEAD_LAST_HEARTBEAT:-0}"
(( now - last < 60 )) && exit 0
```
`$BEAD_LAST_HEARTBEAT` is inherited from the env at process start. But env vars written via `echo >> $CLAUDE_ENV_FILE` are not instantly available to the next hook invocation — they depend on when Claude Code re-reads the env file. If Claude Code only re-sources `CLAUDE_ENV_FILE` between turns (not between hook invocations), then `BEAD_LAST_HEARTBEAT` is stale for all hook invocations within the same turn. Multiple heartbeats within one turn (if a tool calls generates multiple PostToolUse events) will all see the same `last=0` or the last turn's value, all pass the throttle check, and all write to the env file. The throttle is not reliable as written.

**Problem 3 — Each heartbeat invokes `bd set-state` which acquires the dolt lock.** Under rapid tool use, this can produce 5-10 dolt lock acquisitions per minute even with the throttle failing to prevent duplicates. Combined with an agent running discovery (`bd list --json`) simultaneously, this can cause 15-second lock wait stalls during normal workflow.

**Impact:** Operational. Not a security issue but a significant deployment risk that degrades all bd operations during active sessions.

**Mitigation:**
1. Use a specific matcher instead of empty matcher. The heartbeat only needs to fire occasionally, not on every tool call. A matcher like `"Bash"` would limit it to Bash tool uses (most common unit of real work). Or use a counter-based approach rather than time-based (every 10th tool call, not every 60s).
2. Use a file-based lock for the throttle check: `touch -d "60 seconds ago" /tmp/hb_thresh; [ /tmp/clavain-hb-$$ -nt /tmp/hb_thresh ] && exit 0; touch /tmp/clavain-hb-$$`. File mtimes are reliable across processes; env vars are not.
3. Set timeout to 2000ms, not 5000ms. Heartbeat should be near-instant; if dolt is under lock contention for >2s, the heartbeat should abandon, not wait.

---

## Finding 7 — LOW: BD_ACTOR Uniqueness (8 chars of UUID)

**Location:** Batch 1

**Analysis:** A UUID is 32 hex characters with dashes, e.g., `a1b2c3d4-e5f6-7890-abcd-ef1234567890`. Taking the first 8 characters gives `a1b2c3d4`. For two concurrent sessions on the same machine, both UUIDs are generated by Claude Code's session manager. The probability of a collision on the first 8 hex characters is 1/16^8 = approximately 1 in 4 billion. For 2-5 concurrent sessions per machine, collision probability is negligible.

**Not a spoofing risk.** In the single-user, same-machine trust model, there is no adversarial actor that would attempt to set `BD_ACTOR` to match another session's value. Any session can already call `bd update` directly.

**Concern worth noting:** The `BD_ACTOR` is used in `bd` audit trail attribution. If the audit trail is used for forensics ("who changed this bead"), the session ID prefix is sufficient for distinguishing concurrent sessions on one machine but is not globally unique across machines or time (a UUID prefix from session A today can collide with session B on a different machine). If the audit trail ever needs to be cross-machine, include a machine ID or hostname prefix.

**Impact:** Low, within stated scope. No action required for v1.

---

## Finding 8 — LOW: bd-who Information Exposure

**Location:** Batch 4, `scripts/bd-who`

**The code:**
```bash
ip_json=$(bd list --status=in_progress --json 2>/dev/null) || ip_json="[]"
```

**Analysis:** `bd list --status=in_progress --json` dumps all in-progress bead titles, IDs, priorities, and assignees. Bead titles may contain sensitive project names, client names, or security-relevant task descriptions (e.g., "Fix auth bypass in API gateway").

**Threat model assessment:** In this single-user, local-only context, any agent running `bd-who` is already a trusted agent with access to the beads database. The script does not expose data to new principals. The symlink install target `~/.local/bin/bd-who` puts it on `$PATH` for the current user only.

**Not a concern in current threat model.** No action required.

---

## Deployment Risk Summary

### Rollback Feasibility

| Batch | Rollback Feasibility | Notes |
|-------|----------------------|-------|
| 1 (BD_ACTOR) | Trivially reversible | Additive env var; sessions without it behave as before |
| 2 (route claims) | Reversible | Text replacement in prompt/skill files; revert with git |
| 3 (bead_claim rewrite) | Reversible | One function in lib-sprint.sh; old code in git |
| 4 (bd-who) | Trivially reversible | New script; remove symlink |
| 5 (heartbeat + TTL) | Partially irreversible | TTL reduction to 1800s will cause claims that were valid under 7200s to be auto-released. Beads claimed before the TTL reduction may be prematurely reaped on the next discovery scan. |

**TTL reduction rollback path:** Claims released by the 1800s reaper (instead of 7200s) cannot be un-released without manual `bd update --status=in_progress` for each affected bead. If agents are mid-work during the TTL reduction deploy, they may lose their claims within 30 minutes of the deploy. Mitigation: deploy the heartbeat *before* reducing the TTL, ensuring active sessions refresh their `claimed_at` before the shorter TTL takes effect.

### Pre-Deploy Checks (Concrete Pass/Fail)

1. `bash -n os/clavain/hooks/session-start.sh` — exits 0
2. `bash -n os/clavain/hooks/heartbeat.sh` — exits 0 (after file creation)
3. `python3 -c "import json; json.load(open('os/clavain/hooks/hooks.json'))"` — exits 0 after hooks.json edit
4. `bash -n os/clavain/hooks/lib-sprint.sh` — exits 0 after bead_claim rewrite
5. Manual: start two sessions, both attempt `bd update <same-bead> --claim` — second should fail with "already claimed"
6. Manual: verify `bd-who` shows at least one in-progress bead correctly grouped by assignee
7. Verify `$CLAUDE_ENV_FILE` does not accumulate duplicate `BEAD_LAST_HEARTBEAT` lines after 5 minutes of session activity

### Post-Deploy Verification

- Check `bd list --status=in_progress --json | jq '.[].assignee'` — should show 8-char session ID prefixes, not "mistakeknot"
- Check `bd state <active-bead> claimed_at` — timestamp should update roughly every 60 seconds during active work
- Monitor `$CLAUDE_ENV_FILE` line count growth rate — should be bounded by heartbeat interval

---

## Go / No-Go Assessment

**Conditional Go.** The plan is sound in intent and the implementation is close to correct. Three issues should be fixed before landing:

1. **Finding 1 (critical):** The soft-claim fallback returning exit code 0 must be changed to return a distinct exit code (2 or 3) so callers know the claim was not atomic. This is a one-line fix in `bead_claim()`.

2. **Finding 5 (medium):** `bead_release()` should check that the caller holds the claim before releasing. Prevents session-end hooks from releasing another session's legitimate claim during handoff transitions.

3. **Finding 6 (medium):** The heartbeat hook's empty matcher `{}` should be replaced with a specific matcher (e.g., `"Bash"`) to prevent process-spawn overhead on every tool call, and the timeout should be reduced to 2000ms.

Findings 2, 3, 4, 7, 8 are low-risk or informational and can be addressed in follow-up.

**Deployment sequencing for Batch 5:** Deploy heartbeat first (without TTL change), let it run for one day to confirm active sessions are refreshing `claimed_at`, then reduce TTL from 7200 to 1800. Do not reduce TTL in the same commit as adding the heartbeat — if the heartbeat has a bug and doesn't fire, existing claims will be reaped prematurely.
