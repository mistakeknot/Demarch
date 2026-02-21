# Research: iv-mqm4 Session-Start Drift Summary Injection

**Date:** 2026-02-20  
**Bead:** iv-mqm4  
**Task:** Implement drift score injection into session-start.sh's additionalContext

## 1. Implementation Plan Reference

**File:** `/root/projects/Interverse/docs/plans/2026-02-19-session-start-drift-summary-injection.md` (lines 1-47)

### Plan Summary
- **Goal:** Expose drift risk early by injecting a compact Interwatch summary into session-start context when Medium/High/Certain drift is present
- **Scope:** Read `.interwatch/drift.json`, add concise summary to additionalContext only when severity threshold is met
- **Severity Filter:** `Medium+` (Medium, High, Certain confidence tiers)
- **Milestones:**
  1. Data contract + thresholds
  2. Hook implementation in session-start.sh
  3. UX guardrails (limit watchables, stay concise)
  4. Tests (missing file, malformed JSON, low-severity-only, mixed-severity cases)
  5. Documentation

### Validation Gates
- No session-start failures when Interwatch is absent or JSON is malformed
- Summary appears only for threshold-severity drift
- Summary stays concise and actionable

---

## 2. Session-Start Hook Structure

**File:** `/root/projects/Interverse/hub/clavain/hooks/session-start.sh` (lines 1-327)

### Context Injection Architecture

The hook builds `additionalContext` by assembling multiple context sections, then uses **priority-based shedding** to cap total length at 6000 characters (line 292).

#### Key Building Blocks (Order of Assembly)

1. **Lines 50-52:** `using_clavain_escaped` — Main skill introduction
2. **Lines 77-151:** `companion_context` — Alerts from detected companion plugins
   - Beads doctor warnings (lines 61-75)
   - Oracle availability (lines 77-80)
   - Interflux/interpath/interwatch/interlock detection (lines 82-133)
   - Interserve mode notice (lines 135-140)
3. **Lines 154:** `conventions` — Brief coding standards reminder
4. **Lines 157:** `setup_hint` — First-time user hint
5. **Lines 159-171:** `upstream_warning` — Staleness check on `docs/upstream-versions.json`
6. **Lines 173-180:** `sprint_context` — Active sprint via `sprint-scan.sh`
7. **Lines 182-193:** `discovery_context` — Work discovery via `lib-discovery.sh` (interphase)
8. **Lines 195-212:** `sprint_resume_hint` — Active sprint resume prompt
9. **Lines 214-233:** `handoff_context` — Previous session context (capped at 40 lines)
10. **Lines 235-285:** `inflight_context` — Background agent detection

#### Assembly (Line 291)
```bash
_full_context="${_context_preamble}${using_clavain_escaped}${companion_context}${conventions}${setup_hint}${upstream_warning}${sprint_context}${discovery_context}${sprint_resume_hint}${handoff_context}${inflight_context}"
```

#### Shedding Priority (Lines 292-314)
If `_full_context` exceeds 6000 characters, sections are removed in **reverse priority order**:
1. `inflight_context` (removed first)
2. `handoff_context`
3. `sprint_resume_hint`
4. `discovery_context`
5. `sprint_context`

#### JSON Output (Lines 316-324)
```json
{
  "hookSpecificOutput": {
    "hookEventName": "SessionStart",
    "additionalContext": "${_full_context}"
  }
}
```

### Plugin Discovery Pattern

**Line 91:** `_discover_interwatch_plugin()` — Pattern used to detect interwatch companion.

From `lib.sh` (lines 61-79):
```bash
# Discover the interwatch companion plugin root directory.
# First checks env var INTERWATCH_ROOT (set by Claude Code if plugin auto-loaded).
# Falls back to plugin cache patterns.
_discover_interwatch_plugin() {
    if [[ -n "${INTERWATCH_ROOT:-}" ]]; then
        echo "$INTERWATCH_ROOT"
        return 0
    fi
    # Cache search logic...
}
```

### JSON Escaping

**Line 53:** Uses `escape_for_json()` helper from `lib.sh` (line 214+).

Pattern for escaped multiline content in additionalContext:
```bash
companion_context="${companion_context}\\n- Companion alert: ${_escaped_content}"
```

Literal `\n` sequences in bash variables become newlines when rendered in the final JSON string.

---

## 3. Interwatch Drift JSON Format & Schema

### File Locations

- **Interverse root:** `/root/projects/Interverse/.interwatch/drift.json` (current example)
- **Clavain root:** `/root/projects/Interverse/hub/clavain/.interwatch/drift.json` (dated example)

### Complete Schema (From Real Data)

**Comprehensive drift.json structure** (`/.interwatch/drift.json`, lines 1-100):

```json
{
  "scan_date": "2026-02-20T21:30:00",
  "watchables": {
    "<watchable_name>": {
      "path": "docs/roadmap.md",
      "exists": true,
      "score": 3,
      "confidence": "Medium",
      "stale": false,
      "signals": {
        "<signal_type>": {
          "count": 1,
          "weight": 2,
          "score": 2,
          "detail": "Optional human-readable description"
        }
      },
      "recommended_action": "suggest-refresh",
      "generator": "interpath:artifact-gen",
      "generator_args": {
        "type": "roadmap"
      }
    }
  }
}
```

### Field Reference

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `scan_date` | ISO8601 string | Yes | Timestamp of last interwatch scan |
| `watchables` | Object | Yes | Map of watchable_name → details |
| `watchables.<name>.path` | String | Yes | Relative file path being watched |
| `watchables.<name>.exists` | Boolean | Yes | File exists in repo |
| `watchables.<name>.score` | Integer | Yes | Weighted drift score (0+) |
| `watchables.<name>.confidence` | String | Yes | Tier: "Green", "Low", "Medium", "High", "Certain" |
| `watchables.<name>.stale` | Boolean | Yes | File exceeds staleness_days threshold |
| `watchables.<name>.signals` | Object | Yes | Map of signal_type → count/weight/score/detail |
| `watchables.<name>.recommended_action` | String | Yes | "none", "suggest-refresh", "auto-refreshed" |
| `watchables.<name>.generator` | String | Yes | Plugin:skill for regeneration (e.g., "interpath:artifact-gen") |
| `watchables.<name>.generator_args` | Object | Yes | Arguments for the generator |
| `watchables.<name>.signals.<type>.count` | Integer | No | How many times signal fired |
| `watchables.<name>.signals.<type>.weight` | Integer | No | Signal weight from watchables.yaml |
| `watchables.<name>.signals.<type>.score` | Integer | No | count × weight |
| `watchables.<name>.signals.<type>.detail` | String | No | Optional detail string |

### Confidence Tiers

**From `/root/projects/Interverse/plugins/interwatch/skills/doc-watch/references/confidence-tiers.md` (lines 1-54):**

| Tier | Score Range | Staleness | Action |
|------|-------------|-----------|--------|
| **Green** | 0 | < threshold | No action — doc is current |
| **Low** | 1-2 | < threshold | Report only in status |
| **Medium** | 3-5 | any | Suggest refresh via AskUserQuestion |
| **High** | 6+ | any | Auto-refresh with brief note |
| **Certain** | any | any | Auto-refresh silently (deterministic signals: version/count mismatch) |

**iv-mqm4 Filter:** Inject when confidence is **Medium, High, or Certain** (NOT Green or Low).

---

## 4. Watchables Configuration

**File:** `/root/projects/Interverse/plugins/interwatch/config/watchables.yaml` (lines 1-69)

### Schema

```yaml
watchables:
  - name: string               # Unique identifier (roadmap, prd, vision, agents-md)
    path: string               # Relative path (docs/roadmap.md, AGENTS.md)
    generator: string          # Plugin:skill (interpath:artifact-gen, interdoc:interdoc)
    generator_args: map        # Arguments for generator
    signals:                   # List of monitored signals
      - type: string           # Signal type (bead_closed, version_bump, etc.)
        weight: int            # Contribution to drift score
        description: string    # Human-readable explanation
        threshold: int         # Optional: minimum count before fires
    staleness_days: int        # Days before doc considered stale
```

### Current Watchables (From Production Config)

1. **roadmap** (lines 2-19)
   - Path: `docs/roadmap.md`
   - Generator: `interpath:artifact-gen` (type: roadmap)
   - Staleness: 7 days
   - Signals: bead_closed (w=2), bead_created (w=1), version_bump (w=3), brainstorm_created (w=1)

2. **prd** (lines 21-35)
   - Path: `docs/PRD.md`
   - Generator: `interpath:artifact-gen` (type: prd)
   - Staleness: 14 days
   - Signals: component_count_changed (w=3), companion_extracted (w=3), version_bump (w=2)

3. **vision** (lines 37-48)
   - Path: `docs/vision.md`
   - Generator: `interpath:artifact-gen` (type: vision)
   - Staleness: 30 days
   - Signals: companion_extracted (w=2), research_completed (w=1)

4. **agents-md** (lines 50-69)
   - Path: `AGENTS.md`
   - Generator: `interdoc:interdoc`
   - Staleness: 14 days
   - Signals: file_renamed (w=3), file_deleted (w=3), file_created (w=2), commits_since_update (w=1, threshold: 20)

---

## 5. Drift Detection Logic

**File:** `/root/projects/Interverse/plugins/interwatch/skills/doc-watch/phases/detect.md` (lines 1-80)

### Signal Evaluation Patterns

Each signal type has a bash detection pattern (examples):

| Signal | Detection | Example |
|--------|-----------|---------|
| `bead_closed` | `bd list --status=closed` since doc mtime | Count beads closed after doc's last modification |
| `bead_created` | Compare `bd list --status=open` count | New open beads since last scan |
| `version_bump` | Compare `plugin.json` version vs doc header version | `plugin_version != doc_version` → drift |
| `component_count_changed` | Count actual skills/commands vs doc claims | `ls skills/*/SKILL.md \| wc -l` vs documented count |
| `file_renamed` / `file_deleted` / `file_created` | `git diff --name-status` since doc mtime | Git status changes in skills/, commands/, agents/ |
| `commits_since_update` | `git rev-list --count HEAD --since=@doc_mtime` | Number of commits after doc edit |
| `brainstorm_created` | `find docs/brainstorms/ -newer $DOC_PATH` | Brainstorms newer than doc |
| `companion_extracted` | Check plugin cache for new companions | New companion plugins not mentioned in doc |

### Confidence Assessment Logic

**File:** `/root/projects/Interverse/plugins/interwatch/skills/doc-watch/phases/assess.md` (lines 1-54)

**Scoring Formula:**
```
drift_score = sum(signal_weight × signal_count for each signal)
```

**Confidence Mapping:**
- Score 0 + within staleness: **Green**
- Score 1-2 + within staleness: **Low**
- Score 3-5: **Medium**
- Score 6+: **High**
- Score any + exceeds staleness_days: **High** (override)
- Deterministic signal (version_bump or component_count_changed with mismatch): **Certain**

---

## 6. Brainstorm & Related Context

**File:** `/root/projects/Interverse/hub/clavain/docs/brainstorms/2026-02-14-auto-drift-check-brainstorm.md` (lines 1-101)

### Architecture Context

This iv-mqm4 task is complementary to the **auto-drift-check** Stop hook (Clavain-iwuy brainstorm):

- **Session-start drift injection (iv-mqm4):** Show stale drift state at session beginning
- **Auto-drift-check (Stop hook):** Trigger `/interwatch:watch` scan when work is shipped (lower threshold, faster feedback)

### Signal Definitions (From Brainstorm, Lines 61-72)

Standard signals used across Clavain hooks:

| Signal | Weight | Pattern |
|--------|--------|---------|
| Git commit | 1 | `"git commit"` in transcript |
| Bead closed | 1 | `"bd close"` in transcript |
| Version bump | 2 | `bump-version\|interpub:release` |
| Debugging resolution | 2 | "that worked", "it's fixed" |
| Investigation language | 2 | "the issue was", "turned out" |
| Build/test recovery | 2 | FAIL → pass pattern |
| Insight block | 1 | `★ Insight` marker |

**Note:** iv-mqm4 uses **interwatch's confidence tiers** (from drift.json), not transcript signals.

---

## 7. Helper Functions Available

**File:** `/root/projects/Interverse/hub/clavain/hooks/lib.sh` (extracted lines, per codex_query)

### Plugin Discovery Functions

```bash
_discover_interwatch_plugin()    # Line 64 — discover interwatch plugin root
_discover_interflux_plugin()     # Line 26 — discover interflux plugin root
_discover_interpath_plugin()     # Line 45 — discover interpath plugin root
_discover_interlock_plugin()     # Line 83 — discover interlock plugin root
_discover_beads_plugin()         # Line 7  — discover interphase plugin root
```

All follow pattern:
1. Check env var (e.g., `INTERWATCH_ROOT`)
2. Fallback to plugin cache pattern search
3. Return plugin root directory or empty string

### JSON Escaping

```bash
escape_for_json()  # Line 214 — escape string for JSON embedding
```

Handles:
- Backslash escaping (`\ → \\`)
- Quote escaping (`" → \"`)
- Control character escaping (tabs, newlines, etc.)

Used like: `escaped=$(escape_for_json "$content")`

---

## 8. Integration Points in session-start.sh

### Where Drift Injection Should Go

**Recommended insertion point:** After **companion_context** assembly (lines 135-151) and before **conventions** reminder (line 154).

**Rationale:**
- Drift is a companion alert (like beads/oracle/intermute notifications)
- Similar urgency/actionability as Intermute reservations
- Comes before static guidance (conventions/setup/upstream)
- Gives drift highest visibility after using-clavain content

### Template Pattern (From Existing Code)

Model from Intermute injection (lines 107-118):

```bash
# Interserve detection → companion_context build
if [[ -n "$interlock_root" ]]; then
    # Fetch data via CLI/API
    _agents_json=$(curl -sf ... 2>/dev/null) || _agents_json=""
    
    # Parse and format (with graceful fallback)
    _agent_count=$(echo "$_agents_json" | jq '.agents | length' 2>/dev/null) || _agent_count="0"
    
    if [[ "$_agent_count" -gt 0 ]]; then
        # Build alert string with escaped content
        _agent_names=$(echo "$_agents_json" | jq -r '[.agents[].name] | join(", ")' 2>/dev/null)
        _agent_names=$(escape_for_json "$_agent_names")
        companion_context="${companion_context}\\n- Intermute: ${_agent_count} agent(s) online (${_agent_names})"
    fi
fi
```

### Expected Output Format

One-line-per-watchable format (concise, high-signal):

```
- Drift detected (Medium+): roadmap (score 3, Medium), agents-md (score 4, Medium)
  Run `/interwatch:status` for details, `/interwatch:watch` to refresh.
```

Or with detail:

```
- Drift detected: roadmap — bead closed + brainstorm created (Medium). Run /interwatch:watch to refresh.
```

---

## 9. Missing/Stale File Scenarios

### Graceful Degradation Requirements

**From plan (line 38-39):** "No session-start failures when Interwatch is absent or JSON is malformed."

**Implementation guards needed:**

1. **Missing .interwatch directory:** Silent skip (not an error)
2. **Missing drift.json file:** Silent skip
3. **Malformed JSON:** Catch with `2>/dev/null` and fallback to empty string
4. **No Medium+ confidence items:** Don't inject anything (low-signal)
5. **Interwatch not installed:** Already handled by `_discover_interwatch_plugin()` returning empty

### Pattern

```bash
# Read drift.json with fallback
drift_file=".interwatch/drift.json"
if [[ -f "$drift_file" ]]; then
    drift_json=$(cat "$drift_file" 2>/dev/null) || drift_json=""
else
    drift_json=""
fi

# Parse with jq null-safety
if [[ -n "$drift_json" ]]; then
    drift_summary=$(echo "$drift_json" | jq -r '...' 2>/dev/null) || drift_summary=""
fi

# Only inject if summary is non-empty
if [[ -n "$drift_summary" ]]; then
    companion_context="${companion_context}\\n${drift_summary}"
fi
```

---

## 10. Key Implementation Decisions

### Severity Threshold
- **Include:** Medium, High, Certain
- **Exclude:** Green, Low
- **Reason:** Low-confidence items are noise; Medium+ requires user attention per interwatch tiers

### Watchables to Surface
- **Cap:** Show max 3 watchables per session-start (avoid context bloat)
- **Sort:** By score descending (highest risk first)
- **Format:** One-line summary per watchable

### Example Outputs

**Single watchable (High):**
```
- Drift detected: roadmap (score 9, High) — 3 beads closed, 1 version bump. Run /interwatch:watch.
```

**Multiple watchables (Medium+):**
```
- Drift detected (3 docs): roadmap (score 3, Medium), agents-md (score 4, Medium). Run /interwatch:status for details.
```

**No drift:**
```
[No injection — silence is golden]
```

### Context Budget
- **Target size:** 200-300 characters max (2-3 lines)
- **Shedding priority:** Drift injection is low-priority relative to inflight_context, so will be shed first if over 6000 char cap
- **Message:** Keep one-liner actionable — point to `/interwatch:watch` or `/interwatch:status`

---

## Summary

### Files to Read/Modify

| File | Purpose | Lines | Status |
|------|---------|-------|--------|
| `docs/plans/2026-02-19-session-start-drift-summary-injection.md` | Primary plan | 1-47 | ✓ Read |
| `hub/clavain/hooks/session-start.sh` | Target hook (edit after companion_context) | 1-327 | ✓ Read |
| `plugins/interwatch/config/watchables.yaml` | Watchable definitions | 1-69 | ✓ Read |
| `.interwatch/drift.json` (and examples) | Output schema to parse | — | ✓ Examined |
| `plugins/interwatch/skills/doc-watch/phases/assess.md` | Confidence tier logic | 1-54 | ✓ Read |
| `plugins/interwatch/skills/doc-watch/phases/detect.md` | Signal detection patterns | 1-80 | ✓ Read |
| `hub/clavain/hooks/lib.sh` | Helper functions (_discover_*, escape_for_json) | 1-262 | ✓ Extracted |

### Data Contract

**drift.json schema subset for iv-mqm4:**
- `scan_date`: Timestamp (informational)
- `watchables.<name>.path`: File path (for linking to docs)
- `watchables.<name>.score`: Drift score (0-10+)
- `watchables.<name>.confidence`: Tier (Green/Low/Medium/High/Certain)
- `watchables.<name>.recommended_action`: Action hint (suggest-refresh, auto-refreshed, none)

**Filter:** Include only items where `confidence` ∈ {Medium, High, Certain}

### Implementation Steps

1. ✓ Read drift.json at session-start, parse with jq (fallback to empty on error)
2. ✓ Filter for Medium+ confidence watchables
3. ✓ Cap output to max 3 watchables, 200-300 chars
4. ✓ Format as one-line-per-watchable alert
5. ✓ Inject into `companion_context` after interlock/intermute section (before conventions)
6. ✓ Gracefully handle missing/malformed JSON
7. ✓ Test: missing file, malformed JSON, low-severity-only, mixed-severity cases
8. ✓ Add documentation to AGENTS.md on drift injection behavior

