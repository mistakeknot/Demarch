# Correctness Review: Agent Claiming Protocol Plan

**Bead:** iv-sz3sf
**Plan file:** `docs/plans/2026-02-26-agent-claiming-protocol.md`
**Reviewer:** Julik (fd-correctness)
**Date:** 2026-02-26

---

## Invariants Required for Correct Operation

Before reviewing specific code, we must write down what must remain true. Correctness review is guesswork without invariants.

1. **Exclusive claim:** At most one agent holds a claim on any given bead at a time.
2. **Visible claim:** Any agent running discovery can see a live claim within one TTL interval.
3. **Bounded stale claim:** A claim from a crashed agent expires within TTL seconds (30min after the plan lands).
4. **Consistent state:** The `assignee` field in the beads DB and the `claimed_by`/`claimed_at` side-channel state agree. A bead cannot have `assignee=agent-A` while `claimed_by=agent-B`.
5. **No silent double-claim:** A claim failure must be surfaced to the caller; it must not return success when the claim was not acquired.
6. **Heartbeat monotonicity:** A heartbeat must never move `claimed_at` backward in time.
7. **Idempotent release:** Releasing an already-released or never-claimed bead is a no-op (must not corrupt state of a different, live claimer).

---

## Finding 1 — CRITICAL: Lock-Fallback Path Double-Claim (Batch 3)

### Location

`docs/plans/2026-02-26-agent-claiming-protocol.md`, Batch 3, proposed `bead_claim()` rewrite, lines 99–117.

### Invariant violated

Invariant 1 (exclusive claim) and Invariant 5 (no silent double-claim).

### The race in detail

The proposed code distinguishes two failure modes from `bd update --claim`:
- "already claimed" message → reject the caller (return 1)
- "lock" or "timeout" message → fall back to a soft claim via `bd set-state` (return 0)

Here is the exact interleaving that breaks Invariant 1:

```
Time  Agent A                           Agent B
T1    bd update iv-X --claim            bd update iv-X --claim
T2    → Dolt lock acquired by A         → Dolt lock: TIMEOUT (15s exceeded)
T3    A's claim succeeds.               B receives "timeout" in stderr
T4    A exits bead_claim → return 0     B's grep matches "timeout"
T5                                      B runs: bd set-state iv-X "claimed_by=B"
T6                                      B runs: bd set-state iv-X "claimed_at=now"
T7                                      B exits bead_claim → return 0
```

**Result at T7:** Both agents believe they hold the claim. A has `assignee=A` in the beads DB. B has `claimed_by=B` in the side-channel state. These disagree — Invariant 4 is also violated.

The next time discovery runs for either agent, the discovery logic at `lib-discovery.sh:340` checks `claimed_by_val`, which is now B's session ID. Discovery sees the bead as "claimed by B" (score -50). Agent A doesn't know it has a competitor. Both agents proceed in parallel on the same bead.

### Why this is production-level serious

Dolt's 15-second lock is not rare under concurrent activity. Three agents heartbeating simultaneously (one heartbeat every 60s each) means that on average one `bd set-state` call is in flight at any moment. A `bd update --claim` arriving while a heartbeat holds the lock will time out. The fallback will trigger. Two agents will both "succeed" in claiming the same bead and spend thousands of tokens on duplicated work.

### Root cause

The distinction between "lock timeout" and "claim conflict" is the right idea. The execution is wrong: on a lock timeout, the atomic claim was never tested — we have no information about whether the bead is free. Falling back to a non-atomic soft claim when we cannot acquire the lock gives no exclusion guarantee.

### Correct fix

On a lock timeout, retry the atomic claim once with exponential backoff (e.g., sleep 1, retry), then fail hard rather than fall back:

```bash
bead_claim() {
    local bead_id="${1:?bead_id required}"
    local session_id="${2:-${CLAUDE_SESSION_ID:-unknown}}"
    command -v bd &>/dev/null || return 0

    local output exit_code
    local retries=2
    local delay=1

    for (( i=0; i<retries; i++ )); do
        output=$(bd update "$bead_id" --claim 2>&1)
        exit_code=$?
        if [[ $exit_code -eq 0 ]]; then
            # Atomic claim succeeded — write legacy side-channel for discovery
            bd set-state "$bead_id" "claimed_by=$session_id" >/dev/null 2>&1 || true
            bd set-state "$bead_id" "claimed_at=$(date +%s)" >/dev/null 2>&1 || true
            return 0
        fi
        if echo "$output" | grep -qi "already claimed"; then
            echo "Bead $bead_id already claimed by another agent" >&2
            return 1
        fi
        # Lock contention — retry, do NOT fall back to soft claim
        if (( i < retries-1 )); then
            sleep "$delay"
            delay=$(( delay * 2 ))
        fi
    done

    # All retries exhausted — fail safely (do not grant claim)
    echo "Bead $bead_id: could not acquire claim after $retries attempts (lock contention)" >&2
    return 1
}
```

The critical change is: lock contention on `--claim` means the caller does not get a claim. Return 1. Do not issue soft `bd set-state` writes.

---

## Finding 2 — HIGH: TOCTOU in the Original `bead_claim()` Is Not Fixed

### Location

`os/clavain/hooks/lib-sprint.sh`, lines 1314–1343 (current implementation, not the proposed one).

This is a pre-existing issue, but the plan does not fix it. It should be called out because the plan's stated goal is correctness.

### The race

The current `bead_claim()` does:
1. Read `bd state bead_id claimed_by` (line 1321)
2. If no active claim found: write `bd set-state bead_id "claimed_by=session"` (line 1341)

Between step 1 and step 2, another agent can also read "no claim" and also proceed to write. Both writes succeed; the last writer wins the side-channel state. But both agents returned 0 from `bead_claim()` and believe they hold the claim.

The plan's Batch 3 is supposed to fix this with `bd update --claim`, but the fix is incomplete because:
- The fallback path (Finding 1 above) reintroduces the TOCTOU via soft `set-state`.
- If `bd` is missing (`command -v bd` fails at line 1317), the function returns 0 without claiming anything — this is a silent no-op that lets the caller proceed unchecked. This is a correctness risk but arguably acceptable as a degraded mode; it should be documented explicitly.

---

## Finding 3 — HIGH: Inconsistent State on Partial Failure After Successful Claim (Batch 3)

### Location

Proposed `bead_claim()`, success path, lines 100–103.

```bash
if output=$(bd update "$bead_id" --claim 2>&1); then
    bd set-state "$bead_id" "claimed_by=$session_id" >/dev/null 2>&1 || true
    bd set-state "$bead_id" "claimed_at=$(date +%s)" >/dev/null 2>&1 || true
    return 0
fi
```

### The problem

`bd update --claim` succeeded and set `assignee=BD_ACTOR` in the beads database. Then the two `bd set-state` calls fail (Dolt lock timeout, filesystem issue, or race). The function returns 0.

State after partial failure:
- `assignee` field = BD_ACTOR (correct, atomic)
- `claimed_by` side-channel = empty or stale from a previous claimer (incorrect)
- `claimed_at` side-channel = empty or stale (incorrect)

Discovery logic at `lib-discovery.sh:340` checks `claimed_by`, not `assignee`. It will not see this session's claim. Another agent running discovery sees no `claimed_by` value, applies no score penalty, and may pick up the same bead. That agent calls `bd update --claim` and gets correctly rejected because `assignee` is already set. It then sees the lock-fallback path (Finding 1), applies the soft claim, and returns 0.

Now: one agent holds the `assignee` lock, a different agent holds the soft `claimed_by` lock. Neither gets the full claim. Discovery cannot reason correctly about either.

### Invariant violated

Invariant 4 (consistent state between assignee field and side-channel).

### Fix

The `|| true` on the `set-state` calls suppresses errors silently. These calls should at minimum log a warning on failure, since a silent partial failure is exactly the kind of thing that causes a 3 AM incident:

```bash
if output=$(bd update "$bead_id" --claim 2>&1); then
    bd set-state "$bead_id" "claimed_by=$session_id" >/dev/null 2>&1 \
        || echo "WARN: bead_claim: failed to write claimed_by for $bead_id" >&2
    bd set-state "$bead_id" "claimed_at=$(date +%s)" >/dev/null 2>&1 \
        || echo "WARN: bead_claim: failed to write claimed_at for $bead_id" >&2
    return 0
fi
```

The deeper fix is to make discovery use `assignee` field from `bd show` rather than the side-channel `claimed_by` state. If `bd update --claim` atomically sets `assignee`, that field is the authoritative claim indicator. Relying on a side-channel that is written non-atomically after the fact guarantees drift.

---

## Finding 4 — HIGH: Heartbeat Appends Are Not Atomic (Batch 5)

### Location

`os/clavain/hooks/heartbeat.sh` (proposed), lines 212–213.

```bash
if [[ -n "${CLAUDE_ENV_FILE:-}" ]]; then
    echo "export BEAD_LAST_HEARTBEAT=$now" >> "$CLAUDE_ENV_FILE"
fi
```

### The problem

`CLAUDE_ENV_FILE` is a shared file sourced by all hooks in a session. Multiple PostToolUse hooks run concurrently after each tool use. The existing hooks already append to this file (session-start.sh lines 24, 31, 32, 174; interlock/session-start.sh lines 28, 49, 50; interflux/session-start.sh line 79).

The `>>` redirect operator is not atomic on Linux for appends longer than PIPE_BUF bytes (4096 bytes on most systems). The `echo "export BEAD_LAST_HEARTBEAT=$now"` line is short (~40 bytes), so it is within PIPE_BUF and the write itself is atomic. However:

1. **Stale read problem**: CLAUDE_ENV_FILE is sourced once per hook invocation (or at session start). It is not continuously re-evaluated. Writing `BEAD_LAST_HEARTBEAT=$now` to the file does not update the environment variable for the current hook process. The variable `BEAD_LAST_HEARTBEAT` in heartbeat.sh is read from the environment inherited at process start. The file append updates future processes, not the current one.

   This means the throttle check `(( now - last < 60 )) && exit 0` compares against the value as of when the hook process started. If a tool call completes very quickly (say, a fast Glob), the hook starts with BEAD_LAST_HEARTBEAT=T and immediately runs again. The second invocation also sees BEAD_LAST_HEARTBEAT=T from the old environment. Both heartbeats fire. The file gets two duplicate `export BEAD_LAST_HEARTBEAT=...` lines appended.

2. **Accumulating duplicate exports**: Every heartbeat appends a new line. The file grows unboundedly over a session. After 8 hours of work at one heartbeat per minute, the file will have ~480 `export BEAD_LAST_HEARTBEAT=...` lines. When Claude Code sources this file, it re-evaluates all 480 lines. This is a minor performance issue but becomes a correctness issue if the file is parsed line-by-line for some purpose.

3. **Concurrent heartbeats from multiple hooks**: The heartbeat hook is triggered on every PostToolUse. If a tool use fires multiple PostToolUse events (unusual but possible), two heartbeat processes start simultaneously, both read `BEAD_LAST_HEARTBEAT=T`, both pass the throttle check, both append to CLAUDE_ENV_FILE. Both also run `bd set-state claimed_at=now` simultaneously — two concurrent Dolt write operations.

### Correct fix

Use a lockfile instead of an environment variable for throttle state. Lockfiles survive across processes and can be checked atomically:

```bash
# In heartbeat.sh:
_hb_lock="/tmp/clavain-heartbeat-${CLAVAIN_BEAD_ID}-${CLAUDE_SESSION_ID:-unknown}"
_hb_mtime=$(stat -c %Y "$_hb_lock" 2>/dev/null || echo 0)
now=$(date +%s)
(( now - _hb_mtime < 60 )) && exit 0

# Create/touch lockfile atomically (best-effort)
touch "$_hb_lock" 2>/dev/null || true

# Run heartbeat
bd set-state "$CLAVAIN_BEAD_ID" "claimed_at=$now" >/dev/null 2>&1 || true
exit 0
```

This avoids CLAUDE_ENV_FILE entirely. The `touch` is a stat operation on a per-bead per-session temp file. No accumulation, no concurrent append risk, no import of stale env values.

---

## Finding 5 — HIGH: TTL Reduction to 30min Can Reap Active Long-Running Operations

### Location

`docs/plans/2026-02-26-agent-claiming-protocol.md`, Batch 5, step 3 and 4.

Changes `7200` (2h) to `1800` (30min) in both:
- `interverse/interphase/hooks/lib-discovery.sh` line 345
- `os/clavain/hooks/lib-sprint.sh` line 1332

### The problem

The heartbeat fires "on every tool use" but self-throttles to once per 60 seconds. PostToolUse hooks only fire when the AI uses a tool. Long-running operations that do not involve tool calls — Oracle review invocations, `claude --agent` subprocess calls, external system waits — produce no tool calls in the parent session for their entire duration.

The brainstorm explicitly acknowledges this (Layer 3 section): "Post-tool heartbeat doesn't fire during long-running operations (e.g., Oracle calls)." An Oracle call can take 10–30 minutes. Under 30min TTL, an agent waiting on Oracle will have its claim auto-reaped before Oracle finishes.

When discovery runs for another agent during this window, it sees `age_sec >= 1800` and runs the auto-release at lines 350–351:

```bash
bd set-state "$id" "claimed_by=" >/dev/null 2>&1 || true
bd set-state "$id" "claimed_at=" >/dev/null 2>&1 || true
```

This wipes the side-channel claim. The other agent now picks up the bead. When the original agent's Oracle call returns, it has no idea its claim was stolen. It continues working, writing artifacts, and closing the bead — while the second agent is also doing the same work.

The brainstorm mentions this risk but the plan does not add any mitigation. The plan says "Active agents never lose claims" — this is incorrect. An agent waiting on an external call for >30min is active but will lose its claim.

### Invariant violated

Invariant 3 (bounded stale claim) is the stated goal, but the 30min TTL violates a needed corollary: the TTL must be longer than any single non-tool-use operation.

### Fix options

Two viable options:

**Option A (recommended): Keep TTL at 2h but add a pre-Oracle heartbeat call.**

Before launching any long-running operation, the agent should explicitly refresh `claimed_at`. A skill-level instruction in the SKILL.md can document this:

```
Before invoking Oracle or any external agent call that may take >10min:
  bd set-state "$CLAVAIN_BEAD_ID" "claimed_at=$(date +%s)"
```

This is not automatic but it is correct. TTL stays at 2h which is long enough for any known operation.

**Option B: Set TTL to 45min, not 30min.**

A 45min window provides a buffer for most Oracle calls (typical P95 is 20-25min based on the brainstorm). It is still a 3x improvement over 2h. This is still wrong in principle but acceptable as a tradeoff if Option A is too operationally heavy.

Do not ship 30min TTL without either pre-Oracle heartbeat injection or a TTL >= 45min.

---

## Finding 6 — MEDIUM: `bead_release()` in Batch 3 Clears Claims It Does Not Own

### Location

`docs/plans/2026-02-26-agent-claiming-protocol.md`, Batch 3, proposed `bead_release()`.

```bash
bead_release() {
    local bead_id="${1:?bead_id required}"
    command -v bd &>/dev/null || return 0
    bd update "$bead_id" --assignee="" --status=open >/dev/null 2>&1 || true
    bd set-state "$bead_id" "claimed_by=" >/dev/null 2>&1 || true
    bd set-state "$bead_id" "claimed_at=" >/dev/null 2>&1 || true
}
```

### The problem

There is no ownership check before release. Any agent that calls `bead_release(bead_id)` — including an agent that never held the claim — will silently clear the `assignee` and `claimed_by` fields.

The session-end-handoff hook at `os/clavain/hooks/session-end-handoff.sh` line 116–119 calls:

```bash
if [[ -n "${CLAVAIN_BEAD_ID:-}" ]] && command -v bd &>/dev/null; then
    source "${BASH_SOURCE[0]%/*}/lib-sprint.sh" 2>/dev/null || true
    bead_release "$CLAVAIN_BEAD_ID" 2>/dev/null || true
fi
```

If two agents are working on the same project and `CLAVAIN_BEAD_ID` is set to the same value in both environments (possible if the env var is inherited from a shared parent), one agent's session-end will clear the other agent's claim.

More concretely: if the discovery auto-release path (Finding 5) mistakenly cleared `claimed_by` after a long Oracle wait, and then Agent B picked up the bead, Agent A's session-end hook will call `bead_release` on Agent B's active claim, clearing it.

### Fix

Add an ownership check to `bead_release`:

```bash
bead_release() {
    local bead_id="${1:?bead_id required}"
    local session_id="${2:-${CLAUDE_SESSION_ID:-unknown}}"
    command -v bd &>/dev/null || return 0

    # Only release if we own the claim
    local current_claimer
    current_claimer=$(bd state "$bead_id" claimed_by 2>/dev/null) || current_claimer=""
    if [[ -n "$current_claimer" \
          && "$current_claimer" != "(no claimed_by state set)" \
          && "$current_claimer" != "$session_id" ]]; then
        # Someone else holds this claim — do not release
        return 0
    fi

    bd update "$bead_id" --assignee="" --status=open >/dev/null 2>&1 || true
    bd set-state "$bead_id" "claimed_by=" >/dev/null 2>&1 || true
    bd set-state "$bead_id" "claimed_at=" >/dev/null 2>&1 || true
}
```

This check does introduce a tiny TOCTOU (between checking and releasing, another agent could take ownership), but for a release path the race direction is safe — worst case we skip a release, not perform one we shouldn't.

---

## Finding 7 — MEDIUM: BD_ACTOR Identity from Session ID Prefix Is Not Stable Across Session Resume

### Location

`docs/plans/2026-02-26-agent-claiming-protocol.md`, Batch 1.

```bash
if [[ -n "$_session_id" ]]; then
    _bd_actor="${_session_id:0:8}"
    echo "export BD_ACTOR=${_bd_actor}" >> "$CLAUDE_ENV_FILE"
fi
```

### The problem

When a session is compacted or resumed (source = "compact" or "resume"), the `session_id` in the hook input may be a different value than the original session's ID. The SessionStart hook runs on all trigger types: "startup|resume|clear|compact" (hooks.json line 5).

If a compact event assigns a new session ID, `BD_ACTOR` will be set to a new 8-character prefix. All subsequent `bd update --claim` calls will use the new actor identity. The beads database will have `assignee=old-prefix` but `BD_ACTOR=new-prefix`. The `bd update --claim` atomicity check compares `BD_ACTOR` against the stored `assignee`. If they differ, the claim will be rejected — the agent will be locked out of its own claimed bead after a compaction.

### Verification needed

The plan does not document whether Claude Code's compact event preserves session_id or generates a new one. If it is preserved, this finding is low severity. If it changes, it is a P0 — the agent will lose access to its own bead claim after every context compaction.

The session-start hook at line 9–10 already detects the source type:

```bash
_hook_source=$(echo "$HOOK_INPUT" | jq -r '.source // "startup"' 2>/dev/null) || _hook_source="startup"
```

The fix is to only set `BD_ACTOR` on `startup`, not on `compact`/`resume`, and to persist it to a stable file (not just CLAUDE_ENV_FILE which may be re-evaluated):

```bash
if [[ "$_hook_source" == "startup" && -n "$_session_id" ]]; then
    _bd_actor="${_session_id:0:8}"
    echo "export BD_ACTOR=${_bd_actor}" >> "$CLAUDE_ENV_FILE"
fi
# On resume/compact: BD_ACTOR is already set in environment from startup
```

---

## Finding 8 — MEDIUM: PostToolUse Heartbeat Hook JSON Format Is Invalid

### Location

`docs/plans/2026-02-26-agent-claiming-protocol.md`, Batch 5, step 2.

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

### The problem

Looking at the existing `hooks.json` structure (the actual file at `os/clavain/hooks/hooks.json`), the JSON schema is:

```json
{
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "Edit|Write|...",
        "hooks": [
          {
            "type": "command",
            "command": "...",
            "timeout": 5
          }
        ]
      }
    ]
  }
}
```

The plan's proposed JSON uses a different (incorrect) schema:
- The plan wraps each entry with `"type": "PostToolUse"` at the top level, but the actual format uses the event name as a key in the `"hooks"` object.
- `"timeout": 5000` — the existing hooks use `"timeout": 5` (seconds, not milliseconds). Using 5000 would mean a 5000-second timeout.
- `"matcher": {}` — existing matchers are strings (regex patterns), not objects.
- `"type": "command"` is missing from the inner hook definition.

If this invalid JSON is merged into hooks.json as written, either the file will fail JSON parsing (if the object structure is wrong) or the hook will never fire (if "matcher": {} matches nothing). Neither outcome is a data corruption issue, but it silently breaks the heartbeat feature entirely.

### Fix

The correct entry to add to the existing `PostToolUse` array in hooks.json:

```json
{
  "matcher": ".*",
  "hooks": [
    {
      "type": "command",
      "command": "${CLAUDE_PLUGIN_ROOT}/hooks/heartbeat.sh",
      "timeout": 5
    }
  ]
}
```

And run `python3 -c "import json; json.load(open('hooks/hooks.json'))"` as the plan already specifies in validation.

---

## Finding 9 — LOW: `bd-who` Has Cosmetic JQ Logic Error

### Location

`docs/plans/2026-02-26-agent-claiming-protocol.md`, Batch 4, step 1.

```bash
echo "$ip_json" | jq -r '
    group_by(.assignee // "unclaimed") | .[] |
    "  \(.[0].assignee // "unclaimed") (\(length) beads)" as $header |
    [$header] + [.[] | "    ◐ \(.id) [\(.priority // "?")] \(.title)"] |
    .[]
'
```

### The problem

`group_by(.assignee // "unclaimed")` does not group by the fallback string. In jq, `group_by(f)` groups elements by the value of `f`. When `.assignee` is null, `null // "unclaimed"` evaluates to `"unclaimed"`. This is correct for grouping.

However, the group header `.[0].assignee // "unclaimed"` re-evaluates `.assignee` on the first element, which is still `null`. The `// "unclaimed"` alternative kicks in and shows "unclaimed". This is actually correct.

The cosmetic issue: when all beads are unclaimed (assignee is null for all), the output shows:

```
  unclaimed (N beads)
    ◐ iv-xxx ...
```

This is the intended behavior. No correctness issue.

However: `jq` exits with code 5 when the input is an empty array and the pipe tries to iterate with `.[]`. This would cause `bd-who` to exit with a non-zero status even when the "No in-progress beads" guard already handles the empty case correctly. The guard runs before the jq call, so this is only reached when `$count -gt 0`. No issue.

This finding is low severity — the logic is correct, the cosmetics are acceptable.

---

## Finding 10 — LOW: `bead-agent-bind.sh` Still Has TOCTOU on Metadata

### Location

`os/clavain/hooks/bead-agent-bind.sh`, lines 41–46. Pre-existing issue, not introduced by the plan.

```bash
CURRENT_META=$(bd show "$ISSUE_ID" --json 2>/dev/null | jq -r '.metadata // empty' 2>/dev/null) || CURRENT_META=""
EXISTING_AGENT=$(echo "$CURRENT_META" | jq -r '.agent_id // empty' 2>/dev/null) || EXISTING_AGENT=""

if [[ -n "$EXISTING_AGENT" && "$EXISTING_AGENT" == "$INTERMUTE_AGENT_ID" ]]; then
    exit 0
fi
```

The read-then-write pattern on metadata has the same TOCTOU as the original `bead_claim`. The plan does not modify this file, so it is pre-existing. But the plan's stated goal includes correctness of the claiming system end-to-end. This hook fires after every successful `bd update --claim` and can still overwrite another agent's metadata. With Finding 1 already enabling double claims, this hook can also emit false "overlap" warnings to both agents in rapid succession, adding noise that makes debugging harder.

Call it out for awareness, not as a blocker on the plan.

---

## Summary of Findings

| # | Severity | Location | Finding |
|---|----------|----------|---------|
| 1 | CRITICAL | Batch 3, bead_claim() fallback path | Lock-timeout fallback silently grants claim via soft set-state — two agents can both "succeed" on the same bead |
| 2 | HIGH | lib-sprint.sh:1314–1343 (existing) | TOCTOU in original bead_claim() is not fully fixed — plan's fix reintroduces the same race in the fallback |
| 3 | HIGH | Batch 3, success path | Partial failure after atomic claim leaves assignee/claimed_by in inconsistent state; discovery ignores assignee |
| 4 | HIGH | Batch 5, heartbeat.sh | CLAUDE_ENV_FILE append pattern: throttle state not shared across concurrent hook processes; file grows unboundedly |
| 5 | HIGH | Batch 5, TTL 30min | 30min TTL expires active agents waiting on Oracle (10–30min); brainstorm documents the risk but plan ships no mitigation |
| 6 | MEDIUM | Batch 3, bead_release() | No ownership check — any agent can clear another agent's active claim |
| 7 | MEDIUM | Batch 1, BD_ACTOR on resume | BD_ACTOR may change on compact/resume if session_id changes, locking agent out of its own claimed bead |
| 8 | MEDIUM | Batch 5, hooks.json entry | PostToolUse hook JSON uses wrong schema and likely wrong timeout unit (5000 vs 5) |
| 9 | LOW | Batch 4, bd-who | Minor jq cosmetic issue; correct behavior |
| 10 | LOW | bead-agent-bind.sh (pre-existing) | TOCTOU on metadata write, pre-existing, amplified by double-claim risk |

---

## Mandatory Pre-Ship Changes

The plan must not ship without fixing findings 1, 3, 4, and 5. These are the issues that cause two agents to silently work on the same bead, produce inconsistent state, or have a claim reaped during active work.

1. **Finding 1**: Remove the `|| true` soft-claim fallback entirely. Lock timeout returns 1.
2. **Finding 3**: Replace `|| true` on set-state with logged warnings; document that discovery should use `assignee` field, not only the side-channel.
3. **Finding 4**: Replace CLAUDE_ENV_FILE append for heartbeat state with a `/tmp/` lockfile keyed by `bead_id + session_id`.
4. **Finding 5**: Either keep TTL at 2h (add pre-Oracle heartbeat to SKILL.md) or set TTL to 45min minimum. 30min is not safe.

Finding 6 (ownership check in bead_release) and Finding 8 (hooks.json schema) are required before this works correctly. Finding 7 (BD_ACTOR stability) should be verified against Claude Code's compact behavior before shipping.
