# Structure Analysis: setup.md and doctor.md

## Overview

This analysis examines where generated markers would be inserted in `setup.md` and `doctor.md` to maintain hand-written prose while automating plugin and companion lists from `agent-rig.json`.

---

## File 1: setup.md

### File Path
`/root/projects/Interverse/os/clavain/commands/setup.md`

### High-Level Structure
- **Lines 1-5**: YAML frontmatter (name, description, argument-hint)
- **Lines 7-20**: Introduction and argument documentation
- **Lines 21-196**: 7 operational steps with bash commands and Python scripts

### Sections Containing Hardcoded Plugin Lists

#### Section 1: "Step 2: Install Required Plugins" (Lines 29-61)
**Exact line ranges:**
- Lines 34-43: `**From interagency-marketplace:**` list
  - `interdoc@interagency-marketplace`
  - `auracoil@interagency-marketplace`
  - `tool-time@interagency-marketplace`
  - `interphase@interagency-marketplace`
  - `interline@interagency-marketplace`
  - `interpath@interagency-marketplace`
  - `interwatch@interagency-marketplace`
  - `interlock@interagency-marketplace`

- Lines 45-53: `**From claude-plugins-official:**` list
  - `context7@claude-plugins-official`
  - `agent-sdk-dev@claude-plugins-official`
  - `plugin-dev@claude-plugins-official`
  - `serena@claude-plugins-official`
  - `security-guidance@claude-plugins-official`
  - `explanatory-output-style@claude-plugins-official`

- Lines 55-60: Language servers (conditional, user-selected)
  - gopls, pyright, typescript, rust-analyzer

**Marker placement:** This is where markers would go to regenerate from `agent-rig.json`.
- Start marker after line 31 (`Install these plugins from their marketplaces...`)
- End marker before line 62 (`## Step 3: Disable Conflicting Plugins`)

#### Section 2: "Step 3: Disable Conflicting Plugins" (Lines 62-75)
**Exact line ranges:** Lines 66-75
Hardcoded conflicts:
- `code-review@claude-plugins-official`
- `pr-review-toolkit@claude-plugins-official`
- `code-simplifier@claude-plugins-official`
- `commit-commands@claude-plugins-official`
- `feature-dev@claude-plugins-official`
- `claude-md-management@claude-plugins-official`
- `frontend-design@claude-plugins-official`
- `hookify@claude-plugins-official`

**Marker placement:** This entire bash block could be regenerated.
- Start marker after line 64 (`must be disabled to avoid duplicate agents:`)
- End marker before line 77 (`## Step 4: Verify MCP Servers`)

#### Section 3: "Step 6: Verify Configuration" (Lines 103-174)
**Exact line ranges:**
- Lines 116-127: Python `required` set (hardcoded plugin list)
  - 10 plugins listed
  - Could be generated from `agent-rig.json["plugins"]["required"]`

- Lines 129-138: Python `conflicts` set (hardcoded conflict list)
  - 8 plugins listed
  - Could be generated from `agent-rig.json["plugins"]["conflicts"]`

**Marker placement:** The entire Python script (lines 108-159) could have markers:
- Start marker after line 105 (`Run a final verification...`)
- End marker before line 161 (`Then check MCP servers and companions:`)

**Alternative approach:** More granular markers inside the Python script:
- Lines 116-127: `required = {...}` — marker around the set definition
- Lines 129-138: `conflicts = {...}` — marker around the set definition

### Hand-Written Prose to Preserve
- Lines 7-20: Introduction explaining arguments and scope
- Lines 21-28: "Step 1: Verify Clavain Itself" — explanation and rationale
- Lines 29-31: Preamble to plugin installation
- Lines 62-64: Preamble to conflicts section
- Lines 77-101: "Step 4" through "Step 5" — explanatory text
- Lines 103-105: Preamble to verification step
- Lines 140-160: Python verification logic (structure/comments should stay, only plugin lists change)
- Lines 161-174: Final MCP verification bash commands
- Lines 176-196: "Step 7: Summary" — handoff messaging

---

## File 2: doctor.md

### File Path
`/root/projects/Interverse/os/clavain/commands/doctor.md`

### High-Level Structure
- **Lines 1-4**: YAML frontmatter
- **Lines 7-22**: Introduction and scope documentation
- **Lines 24-248**: 6 major check sections with bash/Python code

### Sections Containing Hardcoded Lists

#### Section 1: "Check 4: Conflicting Plugins" (Lines 151-180)
**Exact line ranges:** Lines 163-172
Python `conflicts` list (hardcoded, 8 items):
```python
conflicts = [
    'code-review@claude-plugins-official',
    'pr-review-toolkit@claude-plugins-official',
    'code-simplifier@claude-plugins-official',
    'commit-commands@claude-plugins-official',
    'feature-dev@claude-plugins-official',
    'claude-md-management@claude-plugins-official',
    'frontend-design@claude-plugins-official',
    'hookify@claude-plugins-official',
]
```

**Marker placement:** 
- Start marker after line 162 (`conflicts = [`)
- End marker before line 173 (`]`)

**Alternative:** Entire Python block (lines 156-180) could regenerate from json.

#### Section 2: Companion plugin checks (Lines 54-149)
**NOT a single hardcoded list, but repetitive pattern:**

Each companion has nearly identical bash pattern:
- Lines 57-62: interphase check
- Lines 68-73: interline check
- Lines 79-84: interpath check
- Lines 90-95: interwatch check
- Lines 130-148: interlock check (more complex, includes intermute service health)

**Marker placement approach:** Could wrap entire companion section (Lines 54-149) with markers, but more surgical approach:
- Each companion check (7 total) follows identical pattern
- Could be generated from a list of companions with their script names and descriptions

### Hand-Written Prose to Preserve
- Lines 7-22: Introduction and scope explanation
- Lines 24-31: "Checks" preamble and MCP section explanation
- Lines 33-42: External tools check explanation
- Lines 44-52: Beads check explanation
- Lines 54-125: Section headers for companions (preserved), only the repeated bash patterns change
- Lines 151-180: Conflicting plugins section (preserved header/explanation, only the Python list changes)
- Lines 182-204: Skill budget check (entirely hand-written, should NOT be regenerated)
- Lines 206-212: Plugin version check (entirely hand-written, should NOT be regenerated)
- Lines 214-248: Output and recommendations section (hand-written, should NOT be regenerated)

---

## File 3: agent-rig.json

### File Path
`/root/projects/Interverse/os/clavain/agent-rig.json`

### Current Schema
```json
{
  "plugins": {
    "core": {
      "source": "clavain@interagency-marketplace",
      "description": "..."
    },
    "required": [
      {"source": "...", "description": "..."},
      ...
    ],
    "recommended": [
      {"source": "...", "description": "..."},
      ...
    ],
    "infrastructure": [
      {"source": "...", "description": "..."},
      ...
    ],
    "conflicts": [
      {"source": "...", "reason": "..."},
      ...
    ]
  },
  "mcpServers": {...},
  "tools": [...],
  "environment": {...}
}
```

**Key observations:**
- `plugins.required` has 2 items (lines 26-35)
- `plugins.recommended` has 13 items (lines 36-84)
- `plugins.infrastructure` has 4 items (lines 86-103)
- `plugins.conflicts` has 8 items (lines 104-137)
- All use consistent `source` / `description` or `source` / `reason` structure

**Mapping to setup.md:**
- `required` (2 items) → Step 2, from-interagency + from-official lists
- `recommended` → Additional Step 2 items
- `infrastructure` → Step 2, language servers section
- `conflicts` → Step 3, Step 6 Python script

---

## File 4: help.md

### File Path
`/root/projects/Interverse/os/clavain/commands/help.md`

**Finding:** No hardcoded plugin lists. This is a command reference file with:
- Lines 8-23: Daily drivers table (command names, descriptions, examples)
- Lines 24-94: By-stage organization (all commands, no plugin lists)

**No marker placement needed** — this file references commands, not plugins.

---

## File 5: upstream-sync.md

### File Path
`/root/projects/Interverse/os/clavain/commands/upstream-sync.md`

**Finding:** No hardcoded plugin lists. This is a procedural guide for:
- Lines 15-26: Automated pipeline explanation
- Lines 29-70: Steps for syncing upstream repos
- Lines 71-80: Quick reference table (tools → repos → skills, not plugin lists)

**No marker placement needed** — this file is entirely hand-written process documentation.

---

## Summary: Exact Marker Insertion Points

### setup.md

| Section | Start Line | End Line | Type | Scope |
|---------|-----------|---------|------|-------|
| Step 2: Marketplace Plugins | After 31 | Before 62 | Plugin list generation | `plugins.required` + `plugins.recommended` |
| Step 2: Language Servers | After 55 | Before 61 | Conditional plugin selection | `plugins.infrastructure` |
| Step 3: Conflicts | After 64 | Before 77 | Conflict list generation | `plugins.conflicts` |
| Step 6: Python verification (required set) | Inside 116 | Inside 127 | Python set definition | `plugins.required` |
| Step 6: Python verification (conflicts set) | Inside 129 | Inside 138 | Python set definition | `plugins.conflicts` |

### doctor.md

| Section | Start Line | End Line | Type | Scope |
|---------|-----------|---------|------|-------|
| Companion checks (section) | After 53 | Before 150 | Bash pattern generation | All companions from recommended |
| Check 4: Conflicts (Python list) | Inside 163 | Inside 172 | Python list definition | `plugins.conflicts` |

---

## Generated Marker Format Recommendation

Use comment-based markers (consistent with existing codebase style):

**For Markdown (setup.md, doctor.md):**
```markdown
<!-- GENERATED START: plugin-list -->
<!-- GENERATED END: plugin-list -->
```

**For Python/Bash blocks inside markdown:**
```python
# GENERATED START: plugin-conflicts
conflicts = [...]
# GENERATED END: plugin-conflicts
```

**Generator responsibilities:**
1. Read `agent-rig.json`
2. Extract plugin lists by category
3. Match line ranges in setup.md / doctor.md
4. Replace content between markers, preserving:
   - Markdown structure (headers, lists formatting)
   - Python/Bash syntax (function signatures, variable names)
   - Explanatory comments above/below

---

## Key Architectural Findings

1. **setup.md and doctor.md use the same hardcoded lists** for:
   - Required plugins (10 items in setup.md Step 6, but only 2 in agent-rig.json)
   - Conflicts (8 items in both)

2. **Discrepancy in setup.md Step 6:**
   - The Python verification script checks 10 required plugins
   - But agent-rig.json only lists 2 under `required`
   - Missing 8: `interdoc`, `auracoil`, `tool-time`, `interphase`, `interline`, `interpath`, `interwatch`, `interlock`
   - These are in `recommended` in agent-rig.json, but verified as if `required` in setup.md

3. **Companion plugin checks in doctor.md:**
   - Hardcoded bash patterns for: interphase, interline, interpath, interwatch, interlock
   - These are all in `plugins.recommended`, not separate
   - interslack, interform, intercraft, interdev are in `recommended` but NOT checked in doctor.md

4. **Infrastructure plugins (language servers):**
   - setup.md mentions 4 LSP plugins (gopls, pyright, typescript, rust-analyzer)
   - agent-rig.json lists these under `infrastructure` with same list

---

## Recommendations for Generator Implementation

1. **Normalize agent-rig.json:** Consider adding `companions` category separate from `recommended`, since doctor.md specifically checks them.

2. **Update setup.md Step 6 verification:** Make Python script check both `required` AND `recommended`, or update agent-rig.json to include all 10 under `required`.

3. **Generate doctor.md companion checks:** Loop over `recommended` plugins that have known script paths (interphase, interline, interpath, interwatch, interlock).

4. **Use atomic replacement:** Generator should read both files, replace all marked sections, write back atomically to avoid partial updates.

5. **Validation:** Generator should warn if a plugin in agent-rig.json isn't covered by markers in setup.md/doctor.md, indicating missing coverage.
