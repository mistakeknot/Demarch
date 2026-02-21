# Intermute Curl Pattern Analysis for iv-kcf6 Dedup

**Task:** Analyze all Intermute curl calls in Clavain's `session-start.sh` and `sprint-scan.sh` to identify deduplication opportunities for iv-kcf6.

**Date:** 2026-02-20

---

## Executive Summary

Clavain makes **5 distinct Intermute API calls** across two files:
- **session-start.sh:** 3 calls (health check, agents, reservations)
- **sprint-scan.sh:** 2 calls (health check, agents)

**Key finding:** The **`/api/agents` endpoint is called TWICE** in session-start.sh (lines 108 and 226 in sprint_check_coordination) with the same project parameter. The health check is also called twice with different timeout settings. This is the primary dedup target.

**Dedup strategy:** Extract the agents and reservations responses into cached variables in session-start.sh, pass them to sprint_check_coordination, and eliminate redundant health checks.

---

## 1. Curl Calls in session-start.sh (lines 99–127)

### Call 1: Health Check (Line 102)
```bash
curl -sf --connect-timeout 1 --max-time 2 "${_intermute_url}/health" >/dev/null 2>&1
```

**Line:** 102  
**Endpoint:** `/health`  
**Timeout:** `--connect-timeout 1`, `--max-time 2`  
**Purpose:** Quick reachability probe before attempting to fetch agents/reservations  
**Data used:** Boolean return only (checks exit status)  
**Context:** Auto-join Intermute sequence for interlock companion plugin  

### Call 2: Fetch Agents List (Line 108)
```bash
_agents_json=$(curl -sf --max-time 2 "${_intermute_url}/api/agents?project=$(basename "$(git rev-parse --show-toplevel 2>/dev/null)")" 2>/dev/null) || _agents_json=""
```

**Line:** 108  
**Endpoint:** `/api/agents?project=<project-name>`  
**Timeout:** `--max-time 2` (no `--connect-timeout`)  
**Purpose:** Fetch list of active agents for the current project  
**Data extracted:**
- `_agent_count` (line 110): `.agents | length`
- `_agent_names` (line 112): `[.agents[].name] | join(", ")`
- Full JSON stored in `_agents_json` for later use (line 237 in sprint_check_coordination)

**Data flow:**
1. Used immediately (lines 110–112) to construct companion context
2. **Passed to sprint_check_coordination** as parameter (implicit via global scope)
3. Re-read in sprint_check_coordination (line 226) for agent ID lookup

### Call 3: Fetch Reservations (Line 116)
```bash
_reservations_json=$(curl -sf --max-time 2 "${_intermute_url}/api/reservations?project=$(basename "$(git rev-parse --show-toplevel 2>/dev/null)")" 2>/dev/null) || _reservations_json=""
```

**Line:** 116  
**Endpoint:** `/api/reservations?project=<project-name>`  
**Timeout:** `--max-time 2` (no `--connect-timeout`)  
**Purpose:** Fetch active file reservations for the current project  
**Data extracted:**
- `_res_count` (line 118): `[.reservations[]? | select(.is_active == true)] | length`
- `_res_summary` (line 120): `[.reservations[]? | select(.is_active == true) | "\(.agent_id[:8])→\(.path_pattern)"] | join(", ")`

**Data flow:** Used only for companion context injection (lines 119–121); NOT passed to sprint_check_coordination

---

## 2. Curl Calls in sprint-scan.sh

The file includes the function `sprint_check_coordination()` (lines 215–277) which is **called twice**:
1. From `sprint_brief_scan()` (line 286) — used in session-start.sh
2. From `sprint_full_scan()` (line 373) — used in `/sprint-status` command

### Call 4: Health Check in sprint_check_coordination (Line 218)
```bash
curl -sf --connect-timeout 1 --max-time 1 "${intermute_url}/health" >/dev/null 2>&1 || return 1
```

**Line:** 218  
**Endpoint:** `/health`  
**Timeout:** `--connect-timeout 1`, `--max-time 1`  
**Purpose:** Quick reachability probe before attempting API calls  
**Data used:** Boolean return only  
**Context:** Standalone function, called independently from session-start

**DEDUP ISSUE:** This is a **2nd health check** — the first happened 16 lines earlier (line 102 in session-start.sh). Both check the same Intermute service but with slightly different timeout values (max-time 2 vs 1).

### Call 5: Fetch Agents List in sprint_check_coordination (Line 226)
```bash
agents_json=$(curl -sf --max-time 2 "${intermute_url}/api/agents?project=${project}" 2>/dev/null) || return 1
```

**Line:** 226  
**Endpoint:** `/api/agents?project=<project-name>`  
**Timeout:** `--max-time 2` (no `--connect-timeout`)  
**Purpose:** Fetch list of active agents (same as Call 2, but within sprint_check_coordination)  
**Data extracted:**
- Line 228: `.agents | length` → agent count
- Line 237: `.agents[] | "\(.name // .id[:8])"` → agent names
- Line 245: Agent ID lookup by name for reservation filtering

**DEDUP ISSUE:** This is a **2nd fetch of /api/agents** — the first happened in session-start.sh (line 108). Same endpoint, same project parameter, same data structure.

### Call 6: Fetch Reservations in sprint_check_coordination (Line 233)
```bash
reservations_json=$(curl -sf --max-time 2 "${intermute_url}/api/reservations?project=${project}" 2>/dev/null) || reservations_json=""
```

**Line:** 233  
**Endpoint:** `/api/reservations?project=<project-name>`  
**Timeout:** `--max-time 2` (no `--connect-timeout`)  
**Purpose:** Fetch active file reservations (same as Call 3)  
**Data extracted:**
- Line 248–249: Reservation list filtered by agent ID

**DEDUP ISSUE:** This is a **2nd fetch of /api/reservations** — the first happened in session-start.sh (line 116).

---

## 3. Timeout Settings Summary

| Call | Endpoint | --connect-timeout | --max-time | Total Timeout | File:Line |
|------|----------|-------------------|-----------|---------------|-----------|
| 1 | /health | 1s | 2s | 2s | session-start.sh:102 |
| 2 | /api/agents | none | 2s | 2s | session-start.sh:108 |
| 3 | /api/reservations | none | 2s | 2s | session-start.sh:116 |
| 4 | /health | 1s | 1s | 1s | sprint-scan.sh:218 |
| 5 | /api/agents | none | 2s | 2s | sprint-scan.sh:226 |
| 6 | /api/reservations | none | 2s | 2s | sprint-scan.sh:233 |

**Cumulative timeout if Intermute is down:**
- session-start.sh alone: 2s + 2s + 2s = **6s worst-case** (health fails fast in 1s, agents timeout in 2s, reservations timeout in 2s)
- + sprint-scan.sh if it also runs: **1s more** (health check) + 2s (agents) + 2s (reservations) = **3s additional**
- **Total: ~9 seconds** of blocking I/O if Intermute is unreachable

**Issue:** `--connect-timeout` is only used on `/health` checks, not on API calls. If Intermute service is "listening but not responding", the API calls will hang for the full `--max-time 2` (e.g., slow/stuck goroutine on the server).

---

## 4. Data Flow and Reuse Analysis

### session-start.sh Flow

```
Line 100-102: Set INTERMUTE_URL, check health
    ↓
Line 108: Fetch agents_json → store in _agents_json
    ├→ Line 110: Extract agent count
    ├→ Line 112: Extract agent names
    └→ Line 113-114: Inject into companion_context
    
Line 116: Fetch reservations_json → store in _reservations_json
    ├→ Line 118: Extract reservation count
    ├→ Line 120: Extract reservation summary
    └→ Line 121: Inject into companion_context
    
Line 171: Source sprint-scan.sh
Line 171: Call sprint_brief_scan()
    └→ Line 286 (in sprint-scan.sh): Call sprint_check_coordination()
        ├→ Line 218: Health check (REDUNDANT #1)
        ├→ Line 226: Fetch agents_json (REDUNDANT #2) ← SHOULD USE _agents_json from line 108
        ├→ Line 237: Extract agent names from freshly fetched JSON
        ├→ Line 245: Agent ID lookup
        └→ Line 233: Fetch reservations_json (REDUNDANT #3) ← SHOULD USE _reservations_json from line 116
```

### Key Insight: Global Variable Scope

The `_agents_json` variable is set in session-start.sh line 108 but **sprint_check_coordination expects to fetch it independently** (line 226). The function doesn't know about the prior fetch. This is the root cause of the dedup opportunity.

---

## 5. Deduplication Strategy (iv-kcf6)

### Option A: Cache and Pass (Recommended)

**Refactor sprint_check_coordination to accept optional cached responses:**

```bash
sprint_check_coordination() {
    local intermute_url="${INTERMUTE_URL:-http://127.0.0.1:7338}"
    local agents_json="${1:-}"  # Accept as parameter
    local reservations_json="${2:-}"
    
    # Skip health check if responses already provided
    if [[ -z "$agents_json" ]]; then
        curl -sf --connect-timeout 1 --max-time 1 "${intermute_url}/health" >/dev/null 2>&1 || return 1
        agents_json=$(curl -sf --connect-timeout 1 --max-time 2 "${intermute_url}/api/agents?project=${project}" 2>/dev/null) || return 1
    fi
    
    if [[ -z "$reservations_json" ]]; then
        reservations_json=$(curl -sf --connect-timeout 1 --max-time 2 "${intermute_url}/api/reservations?project=${project}" 2>/dev/null) || reservations_json=""
    fi
    
    # ... rest of function using local agents_json and reservations_json variables
}
```

**Changes in session-start.sh:**
- Line 108-125: Fetch once, store in `_agents_json` and `_reservations_json`
- Line 171: Pass to sprint_check_coordination: `sprint_brief_scan "$_agents_json" "$_reservations_json"`

**Changes in sprint-scan.sh:**
- Update `sprint_brief_scan()` signature to accept optional params
- Pass through to `sprint_check_coordination()`
- Line 373: Call without parameters if no cache available (backward compat): `sprint_check_coordination` (for /sprint-status command)
- Function handles both cases internally

**Benefits:**
- Eliminates 2 redundant API calls (agents + reservations) in session-start flow
- Maintains backward compatibility (sprint_full_scan can still call independently)
- Reduces startup latency by ~4s on first session start
- Single timeout spec for API calls (standardize on `--connect-timeout 1 --max-time 2`)

### Option B: Global Cache Variable

Less elegant but simpler:

```bash
# In session-start.sh after line 116
export INTERMUTE_AGENTS_CACHE="$_agents_json"
export INTERMUTE_RESERVATIONS_CACHE="$_reservations_json"

# In sprint_check_coordination
agents_json="${INTERMUTE_AGENTS_CACHE:-}"  # Use cache if available
if [[ -z "$agents_json" ]]; then
    agents_json=$(curl -sf --max-time 2 "${intermute_url}/api/agents?project=${project}" 2>/dev/null) || return 1
fi
```

**Issue:** Export pollutes the environment, less functional purity.

### Option C: Helper Function for Intermute Communication

Extract a reusable function to consolidate all Intermute calls:

```bash
_intermute_fetch() {
    local endpoint="$1"
    local project="${2:-}"
    local timeout="${3:-2}"
    
    local url="${INTERMUTE_URL:-http://127.0.0.1:7338}/${endpoint}"
    [[ -n "$project" ]] && url="${url}?project=${project}"
    
    curl -sf --connect-timeout 1 --max-time "$timeout" "$url" 2>/dev/null || return 1
}

# Usage in session-start.sh
_agents_json=$(_intermute_fetch "api/agents" "$(basename "$(git rev-parse --show-toplevel 2>/dev/null)")" 2) || _agents_json=""
_reservations_json=$(_intermute_fetch "api/reservations" "..." 2) || _reservations_json=""
```

**Benefit:** Consolidates timeout, error handling, URL construction — easier to test and update.

---

## 6. Current Inefficiencies in Detail

### Health Check Redundancy

**session-start.sh line 102** and **sprint-scan.sh line 218** both check `/health` but:
- Different timeouts (2s vs 1s)
- Checked sequentially (not in parallel)
- No caching between them
- If Intermute is slow but alive, both will timeout

### Agent List Redundancy (Most Critical)

**session-start.sh line 108** and **sprint-scan.sh line 226**:
- Fetch same endpoint (`/api/agents?project=<name>`)
- Extracted into separate JSON variables
- Each subsequent parse (lines 110, 112, 228, 237, 245) wastes CPU re-parsing the same data
- Could be fetched once and parsed multiple times

### Reservation List Redundancy

**session-start.sh line 116** and **sprint-scan.sh line 233**:
- Same endpoint, same timeout
- Only used if agent count > 0
- No cross-file sharing

### Missing Timeout on API Calls

- Lines 108, 116, 226, 233: No `--connect-timeout`, only `--max-time`
- If Intermute accepts connections but hangs on response, will wait full 2s per call
- Recommended: Add `--connect-timeout 1` to all API calls for faster failure detection

---

## 7. Line-by-Line Reference

### session-start.sh

| Line | Code | Purpose | Timeout | Output |
|------|------|---------|---------|--------|
| 100 | `_intermute_url=...` | Set URL from env or default | N/A | var set |
| 102 | `curl -sf --connect-timeout 1 --max-time 2 /health` | Check reachability | 2s | boolean (exit code) |
| 108 | `curl -sf --max-time 2 /api/agents?project=...` | Fetch agents | 2s | `_agents_json` |
| 110 | `jq '.agents \| length'` | Parse agent count | N/A | `_agent_count` |
| 112 | `jq -r '[.agents[].name] \| join(...)'` | Parse agent names | N/A | `_agent_names` |
| 114 | Inject into companion_context | Display | N/A | String |
| 116 | `curl -sf --max-time 2 /api/reservations?project=...` | Fetch reservations | 2s | `_reservations_json` |
| 118 | `jq '[.reservations[]? \| select(.is_active == true)] \| length'` | Parse reservation count | N/A | `_res_count` |
| 120 | `jq -r '[.reservations[]? ...] \| join(...)'` | Parse reservation summary | N/A | `_res_summary` |
| 121 | Inject into companion_context | Display | N/A | String |
| 171 | `source sprint-scan.sh` | Load functions | N/A | Code loaded |
| 171 | `sprint_brief_scan` | Invoke coordination check | 3s+ | `sprint_context` |

### sprint-scan.sh

| Line | Function | Code | Purpose | Timeout | Output |
|------|----------|------|---------|---------|--------|
| 215–277 | `sprint_check_coordination()` | Full function | Check agents/reservations | 6s | String or 1 (error) |
| 218 | (within function) | `curl -sf --connect-timeout 1 --max-time 1 /health` | Reachability | 1s | boolean |
| 226 | (within function) | `curl -sf --max-time 2 /api/agents?project=...` | Fetch agents | 2s | `agents_json` |
| 228 | (within function) | `jq '.agents \| length'` | Parse count | N/A | `count` |
| 237 | (within function) | `jq -r '.agents[] \| ...'` | Parse names | N/A | `agent_list` |
| 233 | (within function) | `curl -sf --max-time 2 /api/reservations?project=...` | Fetch reservations | 2s | `reservations_json` |
| 248–249 | (within function) | `jq -r --arg aid ... [.reservations[]? \| select(...)]` | Filter by agent ID | N/A | `agent_files` |
| 286 | (in sprint_brief_scan) | `sprint_check_coordination` | Call function | 6s+ | `coord_status` |
| 373 | (in sprint_full_scan) | `sprint_check_coordination` | Call function | 6s+ | `coord_status` |

---

## 8. Recommendations for iv-kcf6

### Priority 1: Eliminate Redundant API Calls

**Action:** Refactor sprint_check_coordination to accept cached JSON responses as optional parameters.

**Files affected:**
- `/root/projects/Interverse/hub/clavain/hooks/session-start.sh` (lines 100–171)
- `/root/projects/Interverse/hub/clavain/hooks/sprint-scan.sh` (lines 215–286)

**Expected impact:**
- Reduce session-start latency by ~4 seconds (2 fewer curl calls × 2s timeout)
- Eliminate parsing redundancy (agents JSON parsed 3× → 2×)
- Maintain full backward compatibility (independent calls still work)

### Priority 2: Consolidate Timeout Handling

**Action:** Create `_intermute_fetch()` helper function to standardize `--connect-timeout 1 --max-time 2` across all API calls.

**Benefit:** Reduces timeout-related hangs, easier to adjust globally.

### Priority 3: Reduce Health Check Redundancy

**Action:** Cache health status result in session-start.sh, share with sprint_check_coordination.

**Benefit:** Save 1s per session start if Intermute is reachable.

---

## 9. Test Cases for iv-kcf6

1. **Session start with Intermute up** — Should see agents/reservations injected into companion context in <1s (currently ~6s)
2. **Session start with Intermute down** — Should fail fast (<2s total, currently hangs 6s waiting for timeouts)
3. **Session start with Intermute slow** — Should timeout gracefully, companion context injected with empty agents (currently may block sprint_brief_scan)
4. **sprint_brief_scan standalone** — Should still work independently, fetching agents/reservations without prior session-start calls
5. **Concurrent deduplication** — If agent count is 0, reservations should not be fetched (already happens, verify not broken)

---

## Appendix: Intermute API Contract

Based on curl calls observed:

| Endpoint | Method | Query Params | Response Format | Purpose |
|----------|--------|--------------|-----------------|---------|
| `/health` | GET | none | plain text OK or HTTP error | Liveness check |
| `/api/agents?project=<name>` | GET | `project` | JSON `{"agents": [{id, name, ...}]}` | List active agents for project |
| `/api/reservations?project=<name>` | GET | `project` | JSON `{"reservations": [{agent_id, path_pattern, is_active, ...}]}` | List active file reservations |

**Note:** No error handling for invalid project names observed. Clavain silently treats empty responses as no agents/reservations.
