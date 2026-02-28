# Intertrace Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use clavain:executing-plans to implement this plan task-by-task.

**Goal:** Build the intertrace plugin — a cross-module integration gap tracer that accepts a bead ID, traces data flows from changed files, and reports unverified consumer edges ranked by evidence strength.

**Architecture:** Thin interverse plugin (no MCP server) with 3 shell library tracers (`trace-events.sh`, `trace-contracts.sh`, `trace-companion.sh`), one orchestrating skill (`/intertrace`), and one interflux review agent (`fd-integration`). Calls intermap MCP tools for structural data; gap detection logic lives in shell libs and the skill layer.

**Tech Stack:** Bash (shell libs), Markdown (skill, agent, docs), Python (structural tests), jq (JSON manipulation), intermap MCP tools (project_registry, code_structure, impact_analysis)

**Prior Learnings:**
- `docs/solutions/patterns/event-pipeline-shell-consumer-bugs-20260228.md` — hook_id must be in validate allowlist or pipeline is silently inert; `ic state set` reads stdin not positional args; scope IDs must match between get/set
- `docs/solutions/patterns/critical-patterns.md` — hooks.json format must use event-type object keys; plugin.json must explicitly declare skills/agents/hooks arrays
- `docs/solutions/patterns/set-e-arithmetic-and-accumulator-functions-20260222.md` — use `VAR=$((expr))` not `((VAR++))` under set -e; call accumulator functions with `|| true`
- `docs/solutions/patterns/hybrid-cli-plugin-architecture-20260223.md` — pure plugin pattern (no standalone CLI value outside Claude Code sessions)
- `docs/solutions/patterns/set-e-with-fallback-paths-20260216.md` — use `status=0; cmd || status=$?` for fallback paths

---

### Task 1: Create Plugin Directory Structure

**Files:**
- Create: `interverse/intertrace/.claude-plugin/plugin.json`
- Create: `interverse/intertrace/CLAUDE.md`
- Create: `interverse/intertrace/AGENTS.md`
- Create: `interverse/intertrace/PHILOSOPHY.md`
- Create: `interverse/intertrace/README.md`
- Create: `interverse/intertrace/LICENSE`
- Create: `interverse/intertrace/.gitignore`
- Create: `interverse/intertrace/scripts/bump-version.sh`

**Step 1: Create directory tree**

```bash
mkdir -p interverse/intertrace/{.claude-plugin,skills/intertrace,agents/review,lib,hooks,scripts,tests/structural,docs}
```

**Step 2: Write plugin.json**

Create `interverse/intertrace/.claude-plugin/plugin.json`:

```json
{
  "name": "intertrace",
  "version": "0.1.0",
  "description": "Cross-module integration gap tracer — traces data flows from shipped features to find unverified consumer edges.",
  "author": { "name": "mistakeknot" },
  "license": "MIT",
  "keywords": ["integration", "tracing", "data-flow", "gap-detection"],
  "skills": ["./skills/intertrace"],
  "agents": ["./agents/review/fd-integration.md"],
  "hooks": "./hooks/hooks.json"
}
```

**Step 3: Write hooks.json**

Create `interverse/intertrace/hooks/hooks.json`. Note: use event-type object keys, NOT a flat array (critical-patterns.md). For now, empty hooks — intertrace is manual-only.

```json
{
  "hooks": {}
}
```

**Step 4: Write CLAUDE.md**

Create `interverse/intertrace/CLAUDE.md`:

```markdown
# intertrace

> See `AGENTS.md` for full development guide.

## Overview

Cross-module integration gap tracer — 1 skill, 0 commands, 1 agent (fd-integration), 0 hooks, 0 MCP servers. Companion plugin for Clavain. Given a bead ID, traces data flows from changed files through the module graph. Reports unverified consumer edges ranked by evidence strength (P1/P2/P3) with optional bead creation.

## Quick Commands

```bash
# Test locally
cd tests && uv run pytest -q

# Validate structure
ls skills/*/SKILL.md | wc -l          # Should be 1
ls agents/review/*.md | wc -l         # Should be 1
bash -n lib/trace-events.sh           # Syntax check
bash -n lib/trace-contracts.sh        # Syntax check
bash -n lib/trace-companion.sh        # Syntax check
python3 -c "import json; json.load(open('.claude-plugin/plugin.json'))"
```

## Design Decisions (Do Not Re-Ask)

- Thin plugin over intermap — no MCP server (stateless analyzer)
- Three data sources (phase 1): event bus, contracts, companion graph
- Evidence-strength ranking: P1 (declared + zero evidence), P2 (partial), P3 (docs-only)
- Report first, beads on confirm — no auto-creation
- Input model: bead ID → commits → changed files
- Shell libs for tracers, skill for orchestration
```

**Step 5: Write AGENTS.md**

Create `interverse/intertrace/AGENTS.md` following the standard boilerplate header plus plugin-specific sections. Include:
- Standard header (Canonical References, Philosophy Alignment Protocol)
- Quick Reference table (repo URL, namespace, manifest path, component counts)
- Overview (problem, solution, plugin type)
- Architecture (annotated directory tree)
- How It Works (tracer pipeline: bead → commits → files → producers → consumer verification → ranked report)
- Component Conventions (Skills, Agents, Libs)
- Integration Points table (intermap, intercore, interflux, beads)
- Testing section
- Validation Checklist

**Step 6: Write PHILOSOPHY.md**

Create `interverse/intertrace/PHILOSOPHY.md`:
- Purpose: automate integration gap discovery validated during iv-5muhg
- North Star: "Every cross-module data flow edge is either verified or surfaced as a gap"
- Working Priorities: 1. Accuracy (no false positives at P1), 2. Coverage (trace all declared edges), 3. Actionability (findings lead to beads)
- Standard Brainstorming/Planning Doctrine boilerplate
- Decision Filters specific to intertrace

**Step 7: Write README.md**

Create `interverse/intertrace/README.md` following the standard structure: What this does, Installation (marketplace two-step), Usage (slash command examples), Architecture (tree), Design decisions, License.

**Step 8: Write LICENSE**

Standard MIT license, copyright MK.

**Step 9: Write .gitignore**

```
node_modules/
__pycache__/
*.pyc
.venv/
.pytest_cache/
.claude/
.beads/
*.log
.DS_Store
```

**Step 10: Write bump-version.sh**

Create `interverse/intertrace/scripts/bump-version.sh`:

```bash
#!/usr/bin/env bash
set -euo pipefail
# Delegates to ic publish for version management
if command -v ic &>/dev/null; then
    ic publish "$@"
else
    echo "ic not found — install intercore CLI" >&2
    exit 1
fi
```

```bash
chmod +x interverse/intertrace/scripts/bump-version.sh
```

**Step 11: Initialize git repo**

```bash
cd interverse/intertrace && git init && git add -A && git commit -m "feat: initial plugin scaffold for intertrace"
```

**Step 12: Commit**

```bash
git add -A && git commit -m "feat: intertrace plugin scaffold (iv-4iy6g F1)"
```

---

### Task 2: Write Canon Doc & Root AGENTS.md Pointer

**Files:**
- Create: `docs/canon/mcp-server-criteria.md`
- Modify: root `AGENTS.md` (add pointer to new canon doc)

**Step 1: Write the canon doc**

Create `docs/canon/mcp-server-criteria.md`:

```markdown
# MCP Server Decision Criteria

When to create a new MCP server vs using skills + shell libraries.

## Create an MCP Server When

- **Persistent state across sessions** — database, cache, index that must survive between invocations (e.g., intercore SQLite, intersearch embeddings)
- **Expensive initialization** — sidecar process, model loading, file cache warming that amortizes over multiple calls (e.g., intermap Python bridge)
- **Real-time interactive queries** — streaming results, session monitoring, graph traversal that benefits from a persistent process (e.g., intermux tmux monitoring, interlens graph queries)
- **External service bridge** — proxy to an authenticated external API that needs connection management (e.g., interkasten Notion bridge)

## Use Skills + Shell Libraries When

- **Stateless analysis** — run, produce output, exit. No state to preserve between invocations
- **Calls existing MCP servers** — compose existing tools rather than duplicating their data access
- **Batch output** — results written to files, not queried interactively
- **Infrequent use** — less than once per session on average

## Examples

| Plugin | Type | Reason |
|--------|------|--------|
| intercore | MCP server | SQLite event store, persistent state |
| intermap | MCP server | Python sidecar, file cache, expensive init |
| interlock | MCP server | Reservation database, real-time queries |
| interkasten | MCP server | Notion API bridge |
| intersearch | MCP server | Embedding index, expensive init |
| intermux | MCP server | tmux session monitoring, real-time |
| intertrace | Skills + libs | Stateless analyzer, calls intermap, batch output |
| interwatch | Skills + libs | On-demand scanning, file-based state |
| intercheck | Skills + libs | Session-scoped analysis, no persistence needed |
```

**Step 2: Add pointer to root AGENTS.md**

Read root `AGENTS.md` and find the canonical references or standards section. Add a line pointing to the new canon doc:

```markdown
- [`docs/canon/mcp-server-criteria.md`](docs/canon/mcp-server-criteria.md) — when to create an MCP server vs using skills + shell libraries
```

**Step 3: Commit**

```bash
git add docs/canon/mcp-server-criteria.md AGENTS.md
git commit -m "docs: add MCP server decision criteria canon doc (iv-4iy6g F1)"
```

---

### Task 3: Write Structural Tests

**Files:**
- Create: `interverse/intertrace/tests/pyproject.toml`
- Create: `interverse/intertrace/tests/structural/conftest.py`
- Create: `interverse/intertrace/tests/structural/helpers.py`
- Create: `interverse/intertrace/tests/structural/test_structure.py`
- Create: `interverse/intertrace/tests/structural/test_skills.py`

**Step 1: Write test fixtures**

Create `interverse/intertrace/tests/pyproject.toml`:

```toml
[project]
name = "intertrace-tests"
version = "0.1.0"
requires-python = ">=3.12"
dependencies = ["pytest>=8.0", "pyyaml>=6.0"]

[tool.pytest.ini_options]
testpaths = ["structural"]
pythonpath = ["structural"]
```

Create `interverse/intertrace/tests/structural/conftest.py`:

```python
"""Shared fixtures for intertrace structural tests."""

import json
from pathlib import Path

import pytest


@pytest.fixture(scope="session")
def project_root() -> Path:
    """Path to the intertrace repository root."""
    return Path(__file__).resolve().parent.parent.parent


@pytest.fixture(scope="session")
def skills_dir(project_root: Path) -> Path:
    return project_root / "skills"


@pytest.fixture(scope="session")
def plugin_json(project_root: Path) -> dict:
    """Parsed plugin.json."""
    with open(project_root / ".claude-plugin" / "plugin.json") as f:
        return json.load(f)
```

Create `interverse/intertrace/tests/structural/helpers.py`:

```python
"""Shared helpers for intertrace structural tests."""

import yaml


def parse_frontmatter(path):
    """Parse YAML frontmatter from a markdown file."""
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---"):
        return None, text
    parts = text.split("---", 2)
    if len(parts) < 3:
        return None, text
    fm = yaml.safe_load(parts[1])
    body = parts[2]
    return fm, body
```

**Step 2: Write structure tests**

Create `interverse/intertrace/tests/structural/test_structure.py`:

```python
"""Tests for intertrace plugin structure."""

import json
import subprocess
from pathlib import Path


def test_plugin_json_valid(project_root):
    """plugin.json is valid JSON with required fields."""
    path = project_root / ".claude-plugin" / "plugin.json"
    assert path.exists(), "Missing .claude-plugin/plugin.json"
    data = json.loads(path.read_text())
    assert data["name"] == "intertrace"
    assert "version" in data
    assert "description" in data


def test_required_files_exist(project_root):
    """All required root files exist."""
    for f in ["README.md", "CLAUDE.md", "AGENTS.md", "PHILOSOPHY.md", "LICENSE", ".gitignore"]:
        assert (project_root / f).exists(), f"Missing required file: {f}"


def test_required_directories_exist(project_root):
    """All expected directories exist."""
    for d in ["skills", "agents", "lib", "scripts", "tests"]:
        assert (project_root / d).is_dir(), f"Missing directory: {d}"


def test_lib_scripts_syntax(project_root):
    """All lib/*.sh files pass bash syntax check."""
    lib_dir = project_root / "lib"
    if not lib_dir.is_dir():
        return
    for sh in lib_dir.glob("*.sh"):
        result = subprocess.run(
            ["bash", "-n", str(sh)],
            capture_output=True, text=True,
        )
        assert result.returncode == 0, f"Syntax error in {sh.name}: {result.stderr}"


def test_bump_version_executable(project_root):
    """scripts/bump-version.sh is executable."""
    script = project_root / "scripts" / "bump-version.sh"
    assert script.exists(), "Missing scripts/bump-version.sh"
    import os
    assert os.access(script, os.X_OK), "scripts/bump-version.sh is not executable"


def test_skills_referenced_in_plugin_json_exist(project_root, plugin_json):
    """Every skill listed in plugin.json exists on disk."""
    for skill_path in plugin_json.get("skills", []):
        skill_dir = project_root / skill_path.lstrip("./")
        assert skill_dir.is_dir(), f"Skill directory missing: {skill_path}"
        assert (skill_dir / "SKILL.md").exists(), f"Missing SKILL.md in {skill_path}"


def test_agents_referenced_in_plugin_json_exist(project_root, plugin_json):
    """Every agent listed in plugin.json exists on disk."""
    for agent_path in plugin_json.get("agents", []):
        agent_file = project_root / agent_path.lstrip("./")
        assert agent_file.exists(), f"Agent file missing: {agent_path}"
```

**Step 3: Write skill tests**

Create `interverse/intertrace/tests/structural/test_skills.py`:

```python
"""Tests for intertrace skill definitions."""

from pathlib import Path
from helpers import parse_frontmatter


def test_intertrace_skill_has_frontmatter(project_root):
    """intertrace skill has valid YAML frontmatter with description."""
    skill = project_root / "skills" / "intertrace" / "SKILL.md"
    assert skill.exists(), "Missing skills/intertrace/SKILL.md"
    fm, _ = parse_frontmatter(skill)
    assert fm is not None, "SKILL.md missing YAML frontmatter"
    assert "description" in fm, "SKILL.md frontmatter missing 'description'"


def test_fd_integration_agent_has_frontmatter(project_root):
    """fd-integration agent has valid YAML frontmatter."""
    agent = project_root / "agents" / "review" / "fd-integration.md"
    assert agent.exists(), "Missing agents/review/fd-integration.md"
    fm, _ = parse_frontmatter(agent)
    assert fm is not None, "fd-integration.md missing YAML frontmatter"
    assert "name" in fm, "Agent frontmatter missing 'name'"
    assert "description" in fm, "Agent frontmatter missing 'description'"
    assert "model" in fm, "Agent frontmatter missing 'model'"
```

**Step 4: Run tests to verify they fail (TDD red phase)**

```bash
cd interverse/intertrace/tests && uv run pytest -q
```

Expected: Some tests fail because skill and agent files don't exist yet. Structure tests should pass since Task 1 created the directories.

**Step 5: Commit**

```bash
cd interverse/intertrace && git add tests/ && git commit -m "test: structural test scaffold for intertrace"
```

---

### Task 4: Write Event Bus Tracer

**Files:**
- Create: `interverse/intertrace/lib/trace-events.sh`

**Step 1: Write trace-events.sh**

Create `interverse/intertrace/lib/trace-events.sh`. This library:

1. Takes a list of changed files as input (newline-separated)
2. Greps changed files for `ic events emit <type>` calls to find event producers
3. For each event type found, searches the monorepo for consumers:
   - Cursor registrations: `ic events tail.*--consumer=` patterns or `ic events cursor register` calls
   - Hook ID allowlists: case statements in `_validate_hook_id` functions that include the event type
   - Event handler patterns: functions containing the event type string in known consumer modules
4. Outputs JSON array of findings

```bash
#!/usr/bin/env bash
# Intertrace event bus tracer.
#
# Usage:
#   source lib/trace-events.sh
#   _trace_events_scan "/path/to/monorepo" "file1.sh\nfile2.go"
#
# Provides:
#   _trace_events_scan — scan changed files for event producers, verify consumers
#   _trace_events_find_producers — find ic events emit calls in files
#   _trace_events_verify_consumers — check consumer registrations for an event type

[[ -n "${_LIB_TRACE_EVENTS_LOADED:-}" ]] && return 0
_LIB_TRACE_EVENTS_LOADED=1

# Find all event types emitted in the given files.
# Args: $1=monorepo_root, $2=newline-separated file list
# Output: JSON array of {event_type, file, line}
_trace_events_find_producers() {
    local root="$1"
    local files="$2"
    local results="[]"

    while IFS= read -r file; do
        [[ -z "$file" ]] && continue
        local abs_path="$root/$file"
        [[ -f "$abs_path" ]] || continue

        # Match: ic events emit <type> (shell/Go invocations)
        local matches
        matches=$(grep -n 'ic events emit\|ic\.Events\.Emit\|events\.Emit' "$abs_path" 2>/dev/null) || continue

        while IFS= read -r match; do
            [[ -z "$match" ]] && continue
            local line_num="${match%%:*}"
            local line_text="${match#*:}"

            # Extract event type — patterns:
            # ic events emit <type> ...
            # ic events emit "<type>" ...
            local event_type=""
            event_type=$(echo "$line_text" | sed -n 's/.*ic events emit[[:space:]]*"\?\([a-zA-Z0-9_.]*\)"\?.*/\1/p')
            [[ -z "$event_type" ]] && event_type=$(echo "$line_text" | sed -n 's/.*Emit("\([^"]*\)".*/\1/p')
            [[ -z "$event_type" ]] && continue

            results=$(echo "$results" | jq \
                --arg et "$event_type" \
                --arg f "$file" \
                --argjson ln "$line_num" \
                '. + [{event_type: $et, file: $f, line: $ln}]')
        done <<< "$matches"
    done <<< "$files"

    echo "$results"
}

# Verify consumers for a given event type.
# Args: $1=monorepo_root, $2=event_type
# Output: JSON array of {module, verified, evidence, evidence_type}
_trace_events_verify_consumers() {
    local root="$1"
    local event_type="$2"
    local results="[]"

    # Strategy 1: Find cursor registrations that consume this event source
    local source_name="${event_type%%.*}"
    local cursor_files
    cursor_files=$(grep -rl "events tail.*--consumer\|events cursor register\|events list-review\|_consume.*events" "$root/interverse" "$root/os" 2>/dev/null) || true

    while IFS= read -r cfile; do
        [[ -z "$cfile" ]] && continue
        local module
        module=$(echo "$cfile" | sed "s|$root/||" | cut -d/ -f1-2)

        # Check if this file references our event type or its source
        if grep -q "$event_type\|$source_name" "$cfile" 2>/dev/null; then
            results=$(echo "$results" | jq \
                --arg mod "$module" \
                --arg ev "cursor/consumer referencing $event_type" \
                '. + [{module: $mod, verified: true, evidence: $ev, evidence_type: "cursor_registration"}]')
        fi
    done <<< "$cursor_files"

    # Strategy 2: Check hook_id allowlists (case statements in _validate_hook_id)
    local validate_files
    validate_files=$(grep -rl "_validate_hook_id\|validate_hook_id" "$root/interverse" 2>/dev/null) || true

    while IFS= read -r vfile; do
        [[ -z "$vfile" ]] && continue
        local module
        module=$(echo "$vfile" | sed "s|$root/||" | cut -d/ -f1-2)

        # Check if the allowlist includes this event type or a related hook_id
        if grep -q "$event_type\|${event_type//./-}" "$vfile" 2>/dev/null; then
            results=$(echo "$results" | jq \
                --arg mod "$module" \
                --arg ev "hook_id allowlist includes $event_type" \
                '. + [{module: $mod, verified: true, evidence: $ev, evidence_type: "hook_id_allowlist"}]')
        else
            # Found a validate function but it doesn't include our event type
            results=$(echo "$results" | jq \
                --arg mod "$module" \
                --arg ev "hook_id allowlist exists but does NOT include $event_type" \
                '. + [{module: $mod, verified: false, evidence: $ev, evidence_type: "hook_id_allowlist_missing"}]')
        fi
    done <<< "$validate_files"

    # Strategy 3: Check contract-ownership.md for declared consumers
    local contract_file="$root/docs/contract-ownership.md"
    if [[ -f "$contract_file" ]]; then
        local consumer_line
        consumer_line=$(grep -i "$event_type\|$source_name" "$contract_file" 2>/dev/null) || true
        if [[ -n "$consumer_line" ]]; then
            # Extract consumer names from the table row
            local consumers
            consumers=$(echo "$consumer_line" | awk -F'|' '{print $5}' | tr ',' '\n' | sed 's/^[[:space:]]*//' | sed 's/[[:space:]]*$//')
            while IFS= read -r consumer; do
                [[ -z "$consumer" ]] && continue
                results=$(echo "$results" | jq \
                    --arg mod "$consumer" \
                    --arg ev "declared in contract-ownership.md" \
                    '. + [{module: $mod, verified: false, evidence: $ev, evidence_type: "contract_declared"}]')
            done <<< "$consumers"
        fi
    fi

    echo "$results"
}

# Main scan entrypoint.
# Args: $1=monorepo_root, $2=newline-separated changed file list
# Output: JSON object with producers and consumer_verification arrays
_trace_events_scan() {
    local root="$1"
    local files="$2"

    local producers
    producers=$(_trace_events_find_producers "$root" "$files")

    local all_findings="[]"

    # Deduplicate event types
    local event_types
    event_types=$(echo "$producers" | jq -r '.[].event_type' | sort -u)

    while IFS= read -r et; do
        [[ -z "$et" ]] && continue
        local consumers
        consumers=$(_trace_events_verify_consumers "$root" "$et")

        local producer_file
        producer_file=$(echo "$producers" | jq -r --arg et "$et" '[.[] | select(.event_type == $et)][0].file')

        all_findings=$(echo "$all_findings" | jq \
            --arg et "$et" \
            --arg pf "$producer_file" \
            --argjson consumers "$consumers" \
            '. + [{event_type: $et, producer: $pf, consumers: $consumers}]')
    done <<< "$event_types"

    echo "$all_findings"
}
```

**Step 2: Verify syntax**

```bash
bash -n interverse/intertrace/lib/trace-events.sh
```

Expected: No output (syntax OK).

**Step 3: Commit**

```bash
cd interverse/intertrace && git add lib/trace-events.sh && git commit -m "feat: event bus tracer shell library (iv-4iy6g F2)"
```

---

### Task 5: Write Contract Verifier

**Files:**
- Create: `interverse/intertrace/lib/trace-contracts.sh`

**Step 1: Write trace-contracts.sh**

Create `interverse/intertrace/lib/trace-contracts.sh`. This library:

1. Reads `docs/contract-ownership.md` (the contract ownership matrix)
2. Parses the two markdown tables (CLI Output Contracts, Event Payload Contracts)
3. For each row, extracts: command/event, schema, owner, consumers
4. For each declared consumer, greps the monorepo for code evidence of actual consumption
5. Outputs JSON findings with verified/unverified status

```bash
#!/usr/bin/env bash
# Intertrace contract verifier.
#
# Usage:
#   source lib/trace-contracts.sh
#   _trace_contracts_scan "/path/to/monorepo" "file1.sh\nfile2.go"
#
# Provides:
#   _trace_contracts_scan — verify contract consumers against code evidence
#   _trace_contracts_parse — parse contract-ownership.md tables

[[ -n "${_LIB_TRACE_CONTRACTS_LOADED:-}" ]] && return 0
_LIB_TRACE_CONTRACTS_LOADED=1

# Parse a markdown table section from contract-ownership.md.
# Args: $1=file_path, $2=section_header_pattern
# Output: JSON array of {command, schema, owner, consumers} rows
_trace_contracts_parse_table() {
    local file="$1"
    local section_pattern="$2"
    local results="[]"
    local in_section=0
    local in_table=0
    local header_skipped=0

    while IFS= read -r line; do
        # Detect section start
        if echo "$line" | grep -q "$section_pattern"; then
            in_section=1
            in_table=0
            header_skipped=0
            continue
        fi

        # Detect next section (stop)
        if [[ $in_section -eq 1 ]] && echo "$line" | grep -q '^## '; then
            break
        fi

        [[ $in_section -eq 0 ]] && continue

        # Skip non-table lines
        echo "$line" | grep -q '^|' || continue

        # Skip separator row (|---|---|...)
        if echo "$line" | grep -q '^|-'; then
            header_skipped=1
            continue
        fi

        # Skip header row
        if [[ $header_skipped -eq 0 ]]; then
            header_skipped=1
            continue
        fi

        # Parse table row: | Command | Schema | Owner | Consumers | Stability |
        local cmd schema owner consumers
        cmd=$(echo "$line" | awk -F'|' '{gsub(/^[[:space:]]+|[[:space:]]+$/,"",$2); print $2}')
        schema=$(echo "$line" | awk -F'|' '{gsub(/^[[:space:]]+|[[:space:]]+$/,"",$3); print $3}')
        owner=$(echo "$line" | awk -F'|' '{gsub(/^[[:space:]]+|[[:space:]]+$/,"",$4); print $4}')
        consumers=$(echo "$line" | awk -F'|' '{gsub(/^[[:space:]]+|[[:space:]]+$/,"",$5); print $5}')

        # Strip markdown formatting (backticks)
        cmd=$(echo "$cmd" | tr -d '`')

        [[ -z "$cmd" ]] && continue

        results=$(echo "$results" | jq \
            --arg cmd "$cmd" \
            --arg schema "$schema" \
            --arg owner "$owner" \
            --arg consumers "$consumers" \
            '. + [{command: $cmd, schema: $schema, owner: $owner, consumers: $consumers}]')
    done < "$file"

    echo "$results"
}

# Verify that a declared consumer actually uses the contract.
# Args: $1=monorepo_root, $2=consumer_name, $3=command_or_event, $4=schema_name
# Output: JSON {verified, evidence}
_trace_contracts_verify_consumer() {
    local root="$1"
    local consumer="$2"
    local command="$3"
    local schema="$4"

    # Normalize consumer name to search paths
    # "Clavain bash" → os/clavain, "Interspect" → interverse/interspect, etc.
    local search_paths=()
    local consumer_lower
    consumer_lower=$(echo "$consumer" | tr '[:upper:]' '[:lower:]' | sed 's/[[:space:]]*$//')

    case "$consumer_lower" in
        *clavain*) search_paths+=("$root/os/clavain") ;;
        *autarch*) search_paths+=("$root/apps/autarch") ;;
        *interlock*) search_paths+=("$root/interverse/interlock") ;;
        *interspect*) search_paths+=("$root/interverse/interspect") ;;
        *interflux*) search_paths+=("$root/interverse/interflux") ;;
        *interwatch*) search_paths+=("$root/interverse/interwatch") ;;
        *intermap*) search_paths+=("$root/interverse/intermap") ;;
        *) search_paths+=("$root/interverse/$consumer_lower" "$root/os/$consumer_lower" "$root/apps/$consumer_lower") ;;
    esac

    # Extract the actual command name for searching (e.g., "run create" → "run create", "events tail" → "events tail")
    local search_term="$command"

    for sp in "${search_paths[@]}"; do
        [[ -d "$sp" ]] || continue

        # Search for the command string or schema name in consumer code
        local evidence
        evidence=$(grep -rl "$search_term\|$schema" "$sp" 2>/dev/null | head -3) || true

        if [[ -n "$evidence" ]]; then
            local first_file
            first_file=$(echo "$evidence" | head -1 | sed "s|$root/||")
            jq -n --arg ev "Found '$search_term' reference in $first_file" '{verified: true, evidence: $ev}'
            return
        fi
    done

    jq -n --arg ev "No code evidence for '$search_term' consumption in $consumer" '{verified: false, evidence: $ev}'
}

# Main scan entrypoint.
# Args: $1=monorepo_root, $2=newline-separated changed file list (used to scope which contracts to check)
# Output: JSON array of contract verification findings
_trace_contracts_scan() {
    local root="$1"
    local files="$2"
    local contract_file="$root/docs/contract-ownership.md"

    [[ -f "$contract_file" ]] || { echo "[]"; return; }

    local results="[]"

    # Parse CLI output contracts
    local cli_contracts
    cli_contracts=$(_trace_contracts_parse_table "$contract_file" "CLI Output Contracts")

    # Parse event payload contracts
    local event_contracts
    event_contracts=$(_trace_contracts_parse_table "$contract_file" "Event Payload Contracts")

    # Merge both
    local all_contracts
    all_contracts=$(echo "$cli_contracts" | jq --argjson ec "$event_contracts" '. + $ec')

    # For each contract, check if any changed file is in the owner module
    local count
    count=$(echo "$all_contracts" | jq 'length')
    local i=0
    while [[ $i -lt $count ]]; do
        local cmd consumers_str
        cmd=$(echo "$all_contracts" | jq -r ".[$i].command")
        local schema
        schema=$(echo "$all_contracts" | jq -r ".[$i].schema")
        consumers_str=$(echo "$all_contracts" | jq -r ".[$i].consumers")

        # Split consumers by comma
        local verified_list="[]"
        local unverified_list="[]"

        while IFS=',' read -ra consumer_arr; do
            for consumer in "${consumer_arr[@]}"; do
                consumer=$(echo "$consumer" | sed 's/^[[:space:]]*//' | sed 's/[[:space:]]*$//')
                [[ -z "$consumer" ]] && continue

                local verification
                verification=$(_trace_contracts_verify_consumer "$root" "$consumer" "$cmd" "$schema")
                local is_verified
                is_verified=$(echo "$verification" | jq -r '.verified')
                local evidence
                evidence=$(echo "$verification" | jq -r '.evidence')

                if [[ "$is_verified" == "true" ]]; then
                    verified_list=$(echo "$verified_list" | jq --arg c "$consumer" --arg e "$evidence" '. + [{consumer: $c, evidence: $e}]')
                else
                    unverified_list=$(echo "$unverified_list" | jq --arg c "$consumer" --arg e "$evidence" '. + [{consumer: $c, evidence: $e}]')
                fi
            done
        done <<< "$consumers_str"

        results=$(echo "$results" | jq \
            --arg cmd "$cmd" \
            --arg schema "$schema" \
            --argjson verified "$verified_list" \
            --argjson unverified "$unverified_list" \
            '. + [{contract: $cmd, schema: $schema, verified_consumers: $verified, unverified_consumers: $unverified}]')

        i=$((i + 1))
    done

    echo "$results"
}
```

**Step 2: Verify syntax**

```bash
bash -n interverse/intertrace/lib/trace-contracts.sh
```

**Step 3: Commit**

```bash
cd interverse/intertrace && git add lib/trace-contracts.sh && git commit -m "feat: contract verifier shell library (iv-4iy6g F3)"
```

---

### Task 6: Write Companion Graph Verifier

**Files:**
- Create: `interverse/intertrace/lib/trace-companion.sh`

**Step 1: Write trace-companion.sh**

Create `interverse/intertrace/lib/trace-companion.sh`. This library:

1. Reads `docs/companion-graph.json`
2. For each edge `{from, to, relationship, benefit}`, searches for code evidence linking the two modules
3. Reports verified edges, unverified edges, and bonus undeclared-but-actual edges found during scanning

```bash
#!/usr/bin/env bash
# Intertrace companion graph verifier.
#
# Usage:
#   source lib/trace-companion.sh
#   _trace_companion_scan "/path/to/monorepo"
#
# Provides:
#   _trace_companion_scan — verify companion-graph.json edges against code evidence
#   _trace_companion_verify_edge — check a single edge for code evidence

[[ -n "${_LIB_TRACE_COMPANION_LOADED:-}" ]] && return 0
_LIB_TRACE_COMPANION_LOADED=1

# Resolve a plugin name to its directory path(s).
# Args: $1=monorepo_root, $2=plugin_name
# Output: space-separated list of existing directory paths
_trace_companion_resolve_path() {
    local root="$1"
    local name="$2"
    local paths=()

    # Check common locations
    [[ -d "$root/interverse/$name" ]] && paths+=("$root/interverse/$name")
    [[ -d "$root/os/$name" ]] && paths+=("$root/os/$name")
    [[ -d "$root/apps/$name" ]] && paths+=("$root/apps/$name")
    [[ -d "$root/core/$name" ]] && paths+=("$root/core/$name")
    [[ -d "$root/sdk/$name" ]] && paths+=("$root/sdk/$name")

    echo "${paths[*]}"
}

# Verify a single companion-graph edge has code evidence.
# Args: $1=monorepo_root, $2=from_plugin, $3=to_plugin, $4=relationship
# Output: JSON {verified, evidence, evidence_type}
_trace_companion_verify_edge() {
    local root="$1"
    local from_plugin="$2"
    local to_plugin="$3"
    local relationship="$4"

    local from_paths to_paths
    from_paths=$(_trace_companion_resolve_path "$root" "$from_plugin")
    to_paths=$(_trace_companion_resolve_path "$root" "$to_plugin")

    [[ -z "$from_paths" ]] && {
        jq -n --arg ev "Plugin directory not found: $from_plugin" '{verified: false, evidence: $ev, evidence_type: "missing_plugin"}'
        return
    }

    # Search from_plugin's code for references to to_plugin
    for from_dir in $from_paths; do
        # Strategy 1: Direct name reference (import, source, require)
        local name_refs
        name_refs=$(grep -rl "$to_plugin\|lib-${to_plugin}" "$from_dir" --include='*.sh' --include='*.go' --include='*.py' --include='*.md' --include='*.json' 2>/dev/null | grep -v 'node_modules\|\.git\|__pycache__' | head -5) || true

        if [[ -n "$name_refs" ]]; then
            local first_file
            first_file=$(echo "$name_refs" | head -1 | sed "s|$root/||")
            local ref_count
            ref_count=$(echo "$name_refs" | wc -l | tr -d ' ')
            jq -n \
                --arg ev "Found $ref_count references to $to_plugin in $from_plugin (e.g., $first_file)" \
                '{verified: true, evidence: $ev, evidence_type: "code_reference"}'
            return
        fi

        # Strategy 2: Shell lib sourcing (find ... -path "*/lib-<to>*")
        local source_refs
        source_refs=$(grep -rl "lib-${to_plugin}\|plugins/cache.*${to_plugin}" "$from_dir" --include='*.sh' 2>/dev/null | head -3) || true

        if [[ -n "$source_refs" ]]; then
            local first_file
            first_file=$(echo "$source_refs" | head -1 | sed "s|$root/||")
            jq -n \
                --arg ev "Shell lib sourcing of $to_plugin found in $first_file" \
                '{verified: true, evidence: $ev, evidence_type: "shell_source"}'
            return
        fi
    done

    jq -n --arg ev "No code evidence for $from_plugin → $to_plugin ($relationship)" '{verified: false, evidence: $ev, evidence_type: "no_evidence"}'
}

# Main scan entrypoint.
# Args: $1=monorepo_root
# Output: JSON array of edge verification results
_trace_companion_scan() {
    local root="$1"
    local graph_file="$root/docs/companion-graph.json"

    [[ -f "$graph_file" ]] || { echo "[]"; return; }

    local edges
    edges=$(jq -c '.edges[]' "$graph_file" 2>/dev/null) || { echo "[]"; return; }

    local results="[]"

    while IFS= read -r edge; do
        [[ -z "$edge" ]] && continue
        local from_p to_p rel benefit
        from_p=$(echo "$edge" | jq -r '.from')
        to_p=$(echo "$edge" | jq -r '.to')
        rel=$(echo "$edge" | jq -r '.relationship')
        benefit=$(echo "$edge" | jq -r '.benefit')

        local verification
        verification=$(_trace_companion_verify_edge "$root" "$from_p" "$to_p" "$rel")
        local is_verified
        is_verified=$(echo "$verification" | jq -r '.verified')
        local evidence
        evidence=$(echo "$verification" | jq -r '.evidence')
        local evidence_type
        evidence_type=$(echo "$verification" | jq -r '.evidence_type')

        results=$(echo "$results" | jq \
            --arg from "$from_p" \
            --arg to "$to_p" \
            --arg rel "$rel" \
            --arg benefit "$benefit" \
            --argjson verified "$is_verified" \
            --arg ev "$evidence" \
            --arg et "$evidence_type" \
            '. + [{from: $from, to: $to, relationship: $rel, benefit: $benefit, verified: $verified, evidence: $ev, evidence_type: $et}]')
    done <<< "$edges"

    echo "$results"
}
```

**Step 2: Verify syntax**

```bash
bash -n interverse/intertrace/lib/trace-companion.sh
```

**Step 3: Commit**

```bash
cd interverse/intertrace && git add lib/trace-companion.sh && git commit -m "feat: companion graph verifier shell library (iv-4iy6g F4)"
```

---

### Task 7: Write /intertrace Skill

**Files:**
- Create: `interverse/intertrace/skills/intertrace/SKILL.md`

**Step 1: Write the skill**

Create `interverse/intertrace/skills/intertrace/SKILL.md`. This is the orchestrating skill that:

1. Accepts a bead ID as input
2. Resolves bead → commits → changed files
3. Runs all three tracers
4. Merges and ranks findings by evidence strength
5. Presents report via AskUserQuestion with bead creation options
6. Saves report to docs/traces/

```markdown
---
name: intertrace
description: "Cross-module integration gap tracer. Given a bead ID, traces data flows from changed files to find unverified consumer edges. Use after shipping a feature to discover integration gaps."
user_invocable: true
argument-hint: "<bead-id>"
---

# /intertrace — Cross-Module Integration Gap Tracer

Given a shipped feature (bead ID), trace its data flows through the module graph and report unverified consumer edges.

## Input

<intertrace_input> # </intertrace_input>

If no bead ID provided, ask: "Which bead should I trace? Provide a bead ID (e.g., iv-5muhg)."

## Step 1: Resolve Bead to Changed Files

```bash
# Get bead metadata
bd show "<bead_id>"

# Find commits that reference this bead
commits=$(git log --all --oneline --grep="<bead_id>" --format="%H")

# Get changed files from those commits
changed_files=""
for commit in $commits; do
    files=$(git diff-tree --no-commit-id --name-only -r "$commit")
    changed_files="$changed_files\n$files"
done

# Deduplicate
changed_files=$(echo -e "$changed_files" | sort -u | grep -v '^$')
```

If no commits found for the bead ID, tell the user and offer to trace from a git diff range instead.

Display: `Found N files changed across M commits for <bead_id>`

## Step 2: Run Tracers

Source the three tracer libraries and run them. The tracer libraries are at:
- `interverse/intertrace/lib/trace-events.sh`
- `interverse/intertrace/lib/trace-contracts.sh`
- `interverse/intertrace/lib/trace-companion.sh`

### 2a: Event Bus Tracer
Find the intertrace plugin directory (check `~/.claude/plugins/cache/interagency-marketplace/intertrace/` or the development path), source `lib/trace-events.sh`, and call:
```bash
source "$INTERTRACE_ROOT/lib/trace-events.sh"
event_findings=$(_trace_events_scan "$MONOREPO_ROOT" "$changed_files")
```

### 2b: Contract Verifier
```bash
source "$INTERTRACE_ROOT/lib/trace-contracts.sh"
contract_findings=$(_trace_contracts_scan "$MONOREPO_ROOT" "$changed_files")
```

### 2c: Companion Graph Verifier
```bash
source "$INTERTRACE_ROOT/lib/trace-companion.sh"
companion_findings=$(_trace_companion_scan "$MONOREPO_ROOT")
```

## Step 3: Merge and Rank Findings

Combine all findings into a single ranked list using evidence-strength scoring:

**P1 (high confidence gap):**
- Contract declares consumer + zero code evidence (from trace-contracts unverified_consumers)
- Event type emitted + zero cursor registrations (from trace-events with no verified consumers)
- Companion-graph edge + zero import/call evidence (from trace-companion with verified=false)

**P2 (medium confidence):**
- Event type exists + consumer module exists but allowlist missing (trace-events hook_id_allowlist_missing)
- Contract consumer partially verified (some evidence but incomplete)

**P3 (low confidence / docs only):**
- Undeclared edges found in code but not in companion-graph.json (bonus findings)
- Weak grep matches only

## Step 4: Present Report

Display the ranked findings in a clear format:

```
Integration Trace for <bead_id>: <bead_title>

Files traced: N (across M commits)
Tracers run: event-bus, contracts, companion-graph

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
GAPS FOUND: X

P1: <description>
    Source: <which tracer found this>
    Evidence: <what was checked and found missing>
    Impact: <why this matters>

P2: ...

P3: ...
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

Then use **AskUserQuestion** with options:
1. "Create beads for P1 gaps" — create feature beads for high-confidence gaps only
2. "Create beads for all gaps" — create beads for every finding
3. "Save report only" — write to docs/traces/ without creating beads

## Step 5: Create Beads (if chosen)

For each gap that should become a bead:
```bash
bd create --title="Integration gap: <description>" --type=bug --priority=<1|2|3> --description="Found by intertrace tracing <bead_id>. <evidence details>"
```

## Step 6: Save Report

Write findings to `docs/traces/YYYY-MM-DD-<bead_id>-trace.md` with the full report including all findings, evidence, and any beads created.

```

**Step 2: Commit**

```bash
cd interverse/intertrace && git add skills/ && git commit -m "feat: /intertrace slash command skill (iv-4iy6g F5)"
```

---

### Task 8: Write fd-integration Review Agent

**Files:**
- Create: `interverse/intertrace/agents/review/fd-integration.md`

**Step 1: Write the agent definition**

Create `interverse/intertrace/agents/review/fd-integration.md` following the interflux agent format:

```markdown
---
name: fd-integration
description: "Flux-drive Integration reviewer — evaluates cross-module data flow completeness, event consumer registration, contract verification, and companion-graph accuracy. Examples: <example>user: \"Review this diff that adds a new event type\" assistant: \"I'll use the fd-integration agent to verify consumer registrations and allowlists.\" <commentary>New event types need registered consumers and hook_id allowlist entries.</commentary></example> <example>user: \"Check if this cross-module change has integration gaps\" assistant: \"I'll use the fd-integration agent to trace data flow edges and verify wiring.\" <commentary>Cross-module changes need verified integration at each boundary.</commentary></example>"
model: sonnet
---

You are the Flux-drive Integration Reviewer: the agent who ensures cross-module data flows are completely wired. You trace edges from producers to consumers and flag gaps where declared integration points lack code evidence.

## First Step (MANDATORY)

Before reviewing, read:
1. The project's `CLAUDE.md` and `AGENTS.md` for architecture context
2. `docs/companion-graph.json` for declared module relationships
3. `docs/contract-ownership.md` for declared producer/consumer contracts

Write down the integration edges that the diff under review could affect before examining code.

## Review Approach

### 1. Event Producer/Consumer Completeness

For any new `ic events emit` call or event type:
- Verify a cursor consumer is registered for the event source
- Check that any consumer module's `_validate_hook_id` allowlist includes the new event type or hook_id
- Flag if an event is emitted but no module is documented as consuming it

Watch for the silent-pipeline pattern: `_interspect_insert_evidence` calls with unregistered hook_ids silently fail (return 1 swallowed by `|| true`).

### 2. Contract Consumer Verification

For any change touching a contract surface (CLI output format, event payload schema):
- Check that all declared consumers in `contract-ownership.md` actually reference the changed command/schema
- Flag if a new consumer is added to code but not declared in the ownership matrix
- Flag if `ic state set` is called with positional args instead of stdin (common misuse — value must be piped)

### 3. Companion Graph Accuracy

For any new cross-module dependency (import, source, MCP tool call):
- Check if the edge exists in `docs/companion-graph.json`
- Flag undocumented coupling (new dependency not in the graph)
- Flag if a new `lib-*.sh` is sourced across plugin boundaries without declaration

### 4. Shell Library Integration

For any new shell library (`lib-*.sh`) or function that crosses module boundaries:
- Verify the discovery pattern works (the `find ~/.claude/plugins/cache -path "*/lib-*.sh"` pattern)
- Check that the sourcing module handles the case where the library is not installed
- Flag hardcoded paths to plugin cache directories

## Prioritization

- **P0:** Silent pipeline failure — event/evidence that is emitted but silently dropped (missing allowlist, wrong stdin/arg pattern)
- **P1:** Missing consumer — declared integration with zero code evidence
- **P2:** Undocumented coupling — code dependency without companion-graph or contract entry
- **P3:** Documentation drift — companion-graph edge that no longer has code backing
```

**Step 2: Commit**

```bash
cd interverse/intertrace && git add agents/ && git commit -m "feat: fd-integration review agent (iv-4iy6g F6)"
```

---

### Task 9: Run Tests and Fix

**Files:**
- Possibly modify: any files from Tasks 1-8 that cause test failures

**Step 1: Run structural tests**

```bash
cd interverse/intertrace/tests && uv run pytest -q
```

Expected: All tests pass (plugin.json, required files, skill frontmatter, agent frontmatter, lib syntax, directory structure).

**Step 2: If any tests fail, fix the issue**

Read the test output, identify the failure, fix the source file, and re-run.

**Step 3: Run syntax checks on all shell libs**

```bash
bash -n interverse/intertrace/lib/trace-events.sh
bash -n interverse/intertrace/lib/trace-contracts.sh
bash -n interverse/intertrace/lib/trace-companion.sh
```

Expected: No output (all syntax OK).

**Step 4: Commit any fixes**

```bash
cd interverse/intertrace && git add -A && git commit -m "fix: structural test fixes for intertrace"
```

---

### Task 10: Register Plugin in Marketplace

**Files:**
- Modify: `core/marketplace/.claude-plugin/marketplace.json`

**Step 1: Create GitHub repo**

```bash
cd interverse/intertrace && gh repo create mistakeknot/intertrace --public --source=. --push
```

**Step 2: Register in marketplace**

If `ic publish init` is available:
```bash
cd interverse/intertrace && ic publish init
```

Otherwise, manually add to `core/marketplace/.claude-plugin/marketplace.json`:

```json
{
  "name": "intertrace",
  "source": {
    "source": "url",
    "url": "https://github.com/mistakeknot/intertrace.git"
  },
  "description": "Cross-module integration gap tracer — traces data flows from shipped features to find unverified consumer edges.",
  "version": "0.1.0",
  "keywords": ["integration", "tracing", "data-flow", "gap-detection"],
  "strict": true
}
```

**Step 3: Commit marketplace changes**

```bash
cd core/marketplace && git add . && git commit -m "feat: register intertrace in marketplace" && git push
```

**Step 4: Verify plugin loads**

```bash
# Populate cache
mkdir -p ~/.claude/plugins/cache/interagency-marketplace/intertrace/0.1.0
cp -r interverse/intertrace/* ~/.claude/plugins/cache/interagency-marketplace/intertrace/0.1.0/
rm -rf ~/.claude/plugins/cache/interagency-marketplace/intertrace/0.1.0/.git
# Clean orphan markers
find ~/.claude/plugins/cache -maxdepth 4 -name ".orphaned_at" -not -path "*/temp_git_*" -delete
```

**Step 5: Commit**

```bash
cd interverse/intertrace && git add -A && git commit -m "chore: marketplace registration complete"
```

---

### Task 11: Integration Test — Trace iv-5muhg

**Files:**
- None (validation only)

**Step 1: Run /intertrace against the ground truth bead**

Invoke the skill manually in a test session or source the libraries directly:

```bash
cd /home/mk/projects/Demarch
source interverse/intertrace/lib/trace-events.sh
source interverse/intertrace/lib/trace-contracts.sh
source interverse/intertrace/lib/trace-companion.sh

# Get changed files from iv-5muhg
commits=$(git log --all --oneline --grep="iv-5muhg" --format="%H")
changed_files=""
for commit in $commits; do
    files=$(git diff-tree --no-commit-id --name-only -r "$commit")
    changed_files="$changed_files
$files"
done
changed_files=$(echo "$changed_files" | sort -u | grep -v '^$')

echo "Changed files:"
echo "$changed_files"
```

**Step 2: Run event bus tracer**

```bash
event_findings=$(_trace_events_scan "/home/mk/projects/Demarch" "$changed_files")
echo "$event_findings" | jq '.'
```

Expected: Should find `disagreement_resolved` event type and check for consumer registrations. Should flag any missing allowlist entries.

**Step 3: Run contract verifier**

```bash
contract_findings=$(_trace_contracts_scan "/home/mk/projects/Demarch" "$changed_files")
echo "$contract_findings" | jq '.[] | select(.unverified_consumers | length > 0)'
```

Expected: Should find `events tail` contract with Interspect as a declared consumer and verify it's wired.

**Step 4: Run companion graph verifier**

```bash
companion_findings=$(_trace_companion_scan "/home/mk/projects/Demarch")
echo "$companion_findings" | jq '.[] | select(.verified == false)'
```

Expected: Should report any unverified edges in companion-graph.json.

**Step 5: Evaluate results**

Check that intertrace rediscovers at least 3 of the 4 integration gaps from iv-5muhg:
1. interspect hook_id not in allowlist
2. `ic state set` stdin vs positional args / scope ID mismatch
3. galiana/interwatch not consuming disagreement events

If fewer than 3 are found, identify which tracer needs improvement and fix it.

**Step 6: Commit any fixes**

```bash
cd interverse/intertrace && git add -A && git commit -m "fix: tracer improvements from iv-5muhg validation"
```

---

### Task 12: Final Polish and Push

**Files:**
- Possibly modify: various docs

**Step 1: Final test run**

```bash
cd interverse/intertrace/tests && uv run pytest -q
```

Expected: All tests pass.

**Step 2: Push intertrace repo**

```bash
cd interverse/intertrace && git push origin main
```

**Step 3: Push monorepo changes (canon doc, AGENTS.md pointer)**

```bash
cd /home/mk/projects/Demarch && git add docs/canon/mcp-server-criteria.md AGENTS.md && git commit -m "docs: MCP server criteria canon doc + AGENTS.md pointer (iv-4iy6g)" && git push
```

**Step 4: Close beads**

```bash
bd close iv-d7l1z iv-b1ulc iv-limdj iv-f9bwi iv-zzl95 iv-ayhh7
bd close iv-4iy6g --reason="intertrace plugin shipped with 3 tracers, /intertrace skill, fd-integration agent"
```

**Step 5: Sync beads**

```bash
bash .beads/push.sh
```
