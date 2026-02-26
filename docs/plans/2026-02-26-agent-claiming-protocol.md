# Plan: Agent Claiming Protocol

**Bead:** iv-sz3sf
**PRD:** [docs/prds/2026-02-26-agent-claiming-protocol.md](../prds/2026-02-26-agent-claiming-protocol.md)
**Date:** 2026-02-26

## Review Findings Applied

From flux-drive plan review (fd-correctness, fd-architecture, fd-safety):
- **P0 (all 3 agents):** Remove soft-claim fallback in `bead_claim()` — lock timeout must return 1, not silently succeed
- **P0 (correctness+safety):** `bead_release()` needs ownership check — don't release another agent's claim
- **P0 (architecture):** Heartbeat goes in interphase (not clavain), uses specific matcher, uses temp file (not env file)
- **H (architecture):** `sprint_claim()` already has intercore lock — inside sprint context, use `bd set-state` directly, not `bd update --claim`
- **H (correctness):** TTL 30min too aggressive for Oracle calls — use 45min
- **H (architecture):** `bead_release()` must not reset `--status=open` when called from sprint context
- **H (correctness):** BD_ACTOR only set on `startup` source, not `compact`/`resume`
- **H (correctness):** hooks.json schema must match existing format (string matcher, seconds timeout, `"type": "command"`)
- **S (architecture):** `bd-who` lives in `interverse/interphase/scripts/`, not top-level `scripts/`
- **S (architecture):** Best-effort release targets `SessionEnd` hook, not `Stop`

## Execution Batches

### Batch 1: Agent Identity (F1) — `BD_ACTOR` at Session Start

**Goal:** Every session gets a distinguishable actor name so `bd` operations are attributed correctly.

**Files:**
- `os/clavain/hooks/session-start.sh` — add BD_ACTOR export after CLAUDE_SESSION_ID (line ~25)

**Steps:**

1. After the `CLAUDE_SESSION_ID` export block (line 24), add:
   ```bash
   # Set BD_ACTOR to distinguishable identity for beads audit trail.
   # Use session ID prefix (8 chars) — unique per concurrent session.
   # Only set on startup, not compact/resume (session_id may change).
   if [[ "$_hook_source" == "startup" && -n "$_session_id" ]]; then
       _bd_actor="${_session_id:0:8}"
       echo "export BD_ACTOR='${_bd_actor}'" >> "$CLAUDE_ENV_FILE"
   fi
   ```

2. **Review fix applied:** Only set on `startup` source (not compact/resume) per fd-correctness F7. Value is single-quoted per fd-safety F4.

**Validation:**
- `bash -n os/clavain/hooks/session-start.sh`

---

### Batch 2: Atomic Claims in Route + Discovery (F2)

**Goal:** Replace soft claims with `bd update --claim` in all workflow entry points.

**Files:**
- `os/clavain/commands/route.md` — lines 125, 233
- `interverse/interphase/skills/beads-workflow/SKILL.md` — line 60

**Steps:**

1. **`os/clavain/commands/route.md` line 125** (Step 3.5, discovery routing):
   Replace `bd update "$CLAVAIN_BEAD_ID" --status=in_progress` with `bd update "$CLAVAIN_BEAD_ID" --claim`.
   Add failure handling:
   ```
   If `--claim` fails (exit code non-zero):
   - "already claimed" in error → tell user "Bead already claimed by another agent" and re-run discovery from Step 1
   - "lock" or "timeout" in error → retry once after 2 seconds; if still fails, tell user "Could not claim bead (database busy)" and re-run discovery from Step 1
   Do NOT fall back to --status=in_progress — a failed claim means exclusivity is not guaranteed.
   ```

2. **`os/clavain/commands/route.md` line 233** (Step 4c, dispatch routing):
   Same replacement. Failure handling tailored to context:
   ```
   If `--claim` fails (exit code non-zero):
   - Tell user "Bead was claimed by another agent while routing."
   - Do NOT proceed with the current bead.
   - Restart from Step 1 of the discovery flow to find unclaimed work.
   ```

3. **`interverse/interphase/skills/beads-workflow/SKILL.md` line 60**:
   ```
   bd update <id> --claim                 # Atomically claim (fails if already claimed)
   ```

**Validation:**
- Grep for remaining `--status=in_progress` in skill/command files (should only be in `bd list` queries)

---

### Batch 3: Bridge `bead_claim()` / `bead_release()` (F2 continued)

**Goal:** Two calling contexts for `bead_claim()`: (a) direct route claims use `bd update --claim`, (b) sprint claims (inside intercore lock) use soft `bd set-state` since intercore is the authoritative lock.

**Files:**
- `os/clavain/hooks/lib-sprint.sh` — `bead_claim()` at line 1314, `bead_release()` at line 1348

**Steps:**

1. **Rewrite `bead_claim()`** — retry on lock contention, never fall back to soft claim:
   ```bash
   # Usage: bead_claim <bead_id> [session_id] [--soft]
   # --soft: skip atomic bd update --claim, write advisory state only
   #         (used by sprint_claim which has its own intercore lock)
   bead_claim() {
       local bead_id="${1:?bead_id required}"
       local session_id="${2:-${CLAUDE_SESSION_ID:-unknown}}"
       local soft=false
       [[ "${3:-}" == "--soft" ]] && soft=true
       command -v bd &>/dev/null || return 0

       if [[ "$soft" == true ]]; then
           # Sprint context: intercore lock is authoritative, just write audit trail
           bd set-state "$bead_id" "claimed_by=$session_id" >/dev/null 2>&1 || true
           bd set-state "$bead_id" "claimed_at=$(date +%s)" >/dev/null 2>&1 || true
           return 0
       fi

       # Direct claim: use atomic bd update --claim with retry
       local output retries=2 delay=1
       for (( i=0; i<retries; i++ )); do
           if output=$(bd update "$bead_id" --claim 2>&1); then
               # Atomic claim succeeded — write legacy state for discovery
               bd set-state "$bead_id" "claimed_by=$session_id" >/dev/null 2>&1 \
                   || echo "WARN: bead_claim: failed to write claimed_by for $bead_id" >&2
               bd set-state "$bead_id" "claimed_at=$(date +%s)" >/dev/null 2>&1 \
                   || echo "WARN: bead_claim: failed to write claimed_at for $bead_id" >&2
               return 0
           fi
           # Check if actual claim conflict (not lock contention)
           if echo "$output" | grep -qi "already claimed"; then
               echo "Bead $bead_id already claimed by another agent" >&2
               return 1
           fi
           # Lock contention — retry (do NOT fall back to soft claim)
           if (( i < retries-1 )); then
               sleep "$delay"
               delay=$(( delay * 2 ))
           fi
       done

       echo "Bead $bead_id: could not acquire claim after $retries attempts (lock contention)" >&2
       return 1
   }
   ```

2. **Update `sprint_claim()` call** at line ~593 to pass `--soft`:
   ```bash
   # Before: bead_claim "$sprint_id" "$session_id" || true
   # After:
   bead_claim "$sprint_id" "$session_id" --soft || true
   ```

3. **Rewrite `bead_release()` with ownership check and status-preserving option**:
   ```bash
   # Usage: bead_release <bead_id> [--keep-status]
   # --keep-status: clear assignee/claim but don't reset to open (for sprint context)
   bead_release() {
       local bead_id="${1:?bead_id required}"
       local keep_status=false
       [[ "${2:-}" == "--keep-status" ]] && keep_status=true
       command -v bd &>/dev/null || return 0

       # Only release if we own the claim (or claim is empty/stale)
       local current_claimer
       current_claimer=$(bd state "$bead_id" claimed_by 2>/dev/null) || current_claimer=""
       local our_session="${CLAUDE_SESSION_ID:-unknown}"
       if [[ -n "$current_claimer" \
             && "$current_claimer" != "(no claimed_by state set)" \
             && "$current_claimer" != "$our_session" ]]; then
           return 0  # Another session holds this — don't release
       fi

       if [[ "$keep_status" == false ]]; then
           bd update "$bead_id" --assignee="" --status=open >/dev/null 2>&1 || true
       else
           bd update "$bead_id" --assignee="" >/dev/null 2>&1 || true
       fi
       bd set-state "$bead_id" "claimed_by=" >/dev/null 2>&1 || true
       bd set-state "$bead_id" "claimed_at=" >/dev/null 2>&1 || true
   }
   ```

4. **Update `sprint_release()` call** to use `--keep-status`:
   Find where `sprint_release()` calls `bead_release` and pass `--keep-status`.

**Validation:**
- `bash -n os/clavain/hooks/lib-sprint.sh`

---

### Batch 4: `bd-who` Visibility Script (F3)

**Goal:** A script any agent can run to see who's working on what.

**Files:**
- `interverse/interphase/scripts/bd-who` (NEW)

**Steps:**

1. Create `interverse/interphase/scripts/bd-who`:
   ```bash
   #!/usr/bin/env bash
   # Show in-progress beads grouped by assignee
   set -euo pipefail

   command -v bd &>/dev/null || { echo "bd not found" >&2; exit 1; }
   command -v jq &>/dev/null || { echo "jq not found" >&2; exit 1; }

   ip_json=$(timeout 10 bd list --status=in_progress --json 2>/dev/null) || ip_json="[]"
   count=$(echo "$ip_json" | jq 'length')

   if [[ "$count" -eq 0 ]]; then
       echo "No in-progress beads."
       exit 0
   fi

   echo "$ip_json" | jq -r '
       group_by(.assignee // "unclaimed") | .[] |
       "  \(.[0].assignee // "unclaimed") (\(length) beads)" as $header |
       [$header] + [.[] | "    ◐ \(.id) [\(.priority // "?")] \(.title)"] |
       .[]
   '
   ```

2. `chmod +x interverse/interphase/scripts/bd-who`
3. `ln -sf /home/mk/projects/Demarch/interverse/interphase/scripts/bd-who /home/mk/.local/bin/bd-who`

**Validation:**
- `bd-who` runs and shows grouped output

---

### Batch 5: Heartbeat + TTL Reduction (F4, F5)

**Goal:** Active agents keep claims fresh; stale claims expire in 45min instead of 2h.

**Deployed in two phases:** heartbeat first, TTL reduction after confirming heartbeat works.

**Files:**
- `interverse/interphase/hooks/hooks.json` (NEW or update) — register PostToolUse heartbeat
- `interverse/interphase/hooks/heartbeat.sh` (NEW)
- `interverse/interphase/hooks/lib-discovery.sh` — line 345, change 7200 to 2700
- `os/clavain/hooks/lib-sprint.sh` — line 1332, change 7200 to 2700

**Steps:**

1. **Create `interverse/interphase/hooks/heartbeat.sh`** — uses temp file for throttle, not env file:
   ```bash
   #!/usr/bin/env bash
   # PostToolUse heartbeat — refresh claim timestamp at most once per 60s
   # Uses temp file mtime for throttle (reliable across concurrent hooks)

   [[ -n "${CLAVAIN_BEAD_ID:-}" ]] || exit 0
   command -v bd &>/dev/null || exit 0

   _hb_file="/tmp/clavain-heartbeat-${CLAVAIN_BEAD_ID}-${CLAUDE_SESSION_ID:-unknown}"
   _hb_mtime=$(stat -c %Y "$_hb_file" 2>/dev/null || echo 0)
   now=$(date +%s)
   (( now - _hb_mtime < 60 )) && exit 0

   # Touch lockfile atomically, then update claim freshness
   touch "$_hb_file" 2>/dev/null || true
   bd set-state "$CLAVAIN_BEAD_ID" "claimed_at=$now" >/dev/null 2>&1 || true

   exit 0
   ```

2. **Register heartbeat in interphase hooks.json** — create or update `interverse/interphase/hooks/hooks.json`:
   Add to the `PostToolUse` array (using correct hooks.json schema):
   ```json
   {
     "matcher": "Bash|Edit|Write|MultiEdit",
     "hooks": [
       {
         "type": "command",
         "command": "${CLAUDE_PLUGIN_ROOT}/hooks/heartbeat.sh",
         "timeout": 2
       }
     ]
   }
   ```

3. **Reduce TTL to 45min (2700s)** — both files atomically in same commit:
   - `interverse/interphase/hooks/lib-discovery.sh` line 345: `7200` → `2700`
   - `os/clavain/hooks/lib-sprint.sh` line 1332: `7200` → `2700`

4. **Best-effort release in SessionEnd hook**:
   Add to existing SessionEnd handler (not Stop — Stop fires mid-session):
   ```bash
   # Release bead claim on clean session exit (best-effort, may not fire on crash)
   if [[ -n "${CLAVAIN_BEAD_ID:-}" ]] && command -v bd &>/dev/null; then
       _our_session="${CLAUDE_SESSION_ID:-unknown}"
       _claimer=$(bd state "$CLAVAIN_BEAD_ID" claimed_by 2>/dev/null) || _claimer=""
       if [[ -z "$_claimer" || "$_claimer" == "(no claimed_by state set)" || "$_claimer" == "$_our_session" ]]; then
           bd update "$CLAVAIN_BEAD_ID" --assignee="" --status=open >/dev/null 2>&1 || true
           bd set-state "$CLAVAIN_BEAD_ID" "claimed_by=" >/dev/null 2>&1 || true
           bd set-state "$CLAVAIN_BEAD_ID" "claimed_at=" >/dev/null 2>&1 || true
       fi
       # Clean up heartbeat temp file
       rm -f "/tmp/clavain-heartbeat-${CLAVAIN_BEAD_ID}-${_our_session}" 2>/dev/null || true
   fi
   ```

**Validation:**
- `bash -n interverse/interphase/hooks/heartbeat.sh`
- `python3 -c "import json; json.load(open('interverse/interphase/hooks/hooks.json'))"`
- Verify `claimed_at` updates during active session
- TTL values are the same in both files (2700)

---

## Batch Dependency Graph

```
Batch 1 (identity) ─────────────────────────────────┐
    ↓                                                │
Batch 2 (route/discovery claims)                     │
    ↓                                                │
Batch 3 (lib-sprint bridge) ──── depends on Batch 1  │
    ↓                                                │
Batch 4 (bd-who) ─── independent                     │
    ↓                                                │
Batch 5a (heartbeat) ──── depends on Batch 1 ────────┘
    ↓ (confirm heartbeat works)
Batch 5b (TTL 7200→2700) ──── atomic across both files
```

## Estimated Effort

| Batch | Files | Effort | Risk |
|-------|-------|--------|------|
| 1 | 1 | 15min | Low |
| 2 | 3 | 30min | Low |
| 3 | 1 | 30min | Medium — review fixes add complexity |
| 4 | 1 new | 15min | Low |
| 5 | 4 | 45min | Medium — new hook, TTL change |

**Total: ~2.5 hours**
