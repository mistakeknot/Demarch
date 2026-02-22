# Flux-Drive Intermediate Finding Sharing — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use clavain:executing-plans to implement this plan task-by-task.

**Goal:** Enable parallel flux-drive reviewer agents to share high-severity findings via a JSONL file, so agents can adjust analysis at checkpoints and synthesis gets a richer timeline.

**Architecture:** Append-only `{OUTPUT_DIR}/peer-findings.jsonl` written by agents during analysis, read at checkpoints before final report. Synthesis reads the timeline for convergence tracking. A helper script provides filtered access. No new dependencies — pure prompt engineering + file I/O.

**Tech Stack:** Bash (helper script), markdown (prompt modifications), JSONL (finding format)

**Bead:** iv-905u | **Sprint:** iv-firp
**Phase:** planned (as of 2026-02-22T18:27:39Z)

---

## Review Fixes Applied

Flux-drive review (fd-architecture + fd-correctness) found 2 P0 and 7 P1 issues. All addressed:

| Fix | Finding | Change |
|-----|---------|--------|
| P0 atomic write | jq pipe to `>>` is two writes | Capture to variable, single `echo` append |
| P0 safe read | `jq -s` fails on partial trailing line | Filter lines with `grep '^{'` before parsing |
| P1 arg parsing | `filter="${2:-all}"` wrong after shift | Changed to `"${1:-all}"` |
| P1 naming collision | `findings.jsonl` vs `findings.json` | Renamed to `peer-findings.jsonl` |
| P1 template var | No resolution path documented | Added explicit substitution note |
| P1 test reliability | Concurrent test counted with `jq -s` | Count with `grep -c '^{'` + validate no corrupted lines |

---

## Task 1: Create Finding Schema Helper Script

**Files:**
- Create: `interverse/interflux/scripts/findings-helper.sh`

**Step 1: Write the helper script**

Create `interverse/interflux/scripts/findings-helper.sh` — a standalone Bash script that agents can source or call for reading/writing findings:

```bash
#!/usr/bin/env bash
# findings-helper.sh — read/write helpers for flux-drive intermediate findings
# Usage:
#   findings-helper.sh write <findings_file> <severity> <agent> <category> <summary> [file_refs...]
#   findings-helper.sh read <findings_file> [--severity blocking|notable|all]
set -euo pipefail

cmd="${1:-}"
shift || true

case "$cmd" in
  write)
    findings_file="$1"; shift
    severity="$1"; shift
    agent="$1"; shift
    category="$1"; shift
    summary="$1"; shift
    # Remaining args are file_refs
    refs="[]"
    if [[ $# -gt 0 ]]; then
      refs=$(printf '%s\n' "$@" | jq -R . | jq -s .)
    fi
    timestamp=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
    # Build JSON line in memory, then write as single atomic append (< PIPE_BUF)
    line=$(jq -n -c \
      --arg sev "$severity" \
      --arg agt "$agent" \
      --arg cat "$category" \
      --arg sum "$summary" \
      --arg ts "$timestamp" \
      --argjson refs "$refs" \
      '{severity:$sev, agent:$agt, category:$cat, summary:$sum, file_refs:$refs, timestamp:$ts}')
    echo "$line" >> "$findings_file"
    ;;
  read)
    findings_file="$1"; shift
    filter="${1:-all}"
    if [[ ! -f "$findings_file" ]]; then
      echo "[]"
      exit 0
    fi
    # Safe read: filter out incomplete trailing lines before parsing
    safe_content=$(grep -a '^{' "$findings_file" || true)
    if [[ -z "$safe_content" ]]; then
      echo "[]"
      exit 0
    fi
    case "$filter" in
      blocking) echo "$safe_content" | jq -s '[.[] | select(.severity == "blocking")]' ;;
      notable)  echo "$safe_content" | jq -s '[.[] | select(.severity == "notable")]' ;;
      all)      echo "$safe_content" | jq -s '.' ;;
      *)        echo "$safe_content" | jq -s '.' ;;
    esac
    ;;
  *)
    echo "Usage: findings-helper.sh {write|read} <findings_file> ..." >&2
    exit 1
    ;;
esac
```

**Step 2: Make it executable**

Run: `chmod +x interverse/interflux/scripts/findings-helper.sh`

**Step 3: Test write + read manually**

Run:
```bash
tmpfile=$(mktemp /tmp/findings-test-XXXXXX.jsonl)
bash interverse/interflux/scripts/findings-helper.sh write "$tmpfile" "blocking" "fd-test" "api-conflict" "Test finding" "file.go:34"
bash interverse/interflux/scripts/findings-helper.sh read "$tmpfile" --severity blocking
bash interverse/interflux/scripts/findings-helper.sh read "$tmpfile" --severity notable
rm "$tmpfile"
```

Expected: First read returns array with 1 object. Second read returns `[]`. Verify schema fields present.

**Step 4: Test empty file handling**

Run:
```bash
bash interverse/interflux/scripts/findings-helper.sh read /tmp/nonexistent-file.jsonl
```

Expected: Returns `[]`

**Step 5: Commit**

```bash
git add interverse/interflux/scripts/findings-helper.sh
git commit -m "feat(interflux): add findings-helper.sh for intermediate finding read/write"
```

---

## Task 2: Add Peer Findings Protocol to Agent Prompt Template

**Files:**
- Modify: `interverse/interflux/skills/flux-drive/phases/launch.md` (the prompt template, lines ~285-440)

The prompt template in `launch.md` (Step 2.2, "Prompt template for each agent") defines what every reviewer agent receives. We need to insert a new `## Peer Findings Protocol` section into this template.

**Step 1: Read the current prompt template**

Read `interverse/interflux/skills/flux-drive/phases/launch.md` lines 281-440 to see the full template.

**Step 2: Add the Peer Findings Protocol section**

Insert a new section **after** the `## Research Escalation` section and **before** the closing ` ``` ` of the prompt template. The new section:

```markdown
## Peer Findings Protocol

Other reviewer agents are analyzing this artifact in parallel. You can share and receive high-severity findings via a shared findings file.

**Findings file**: `{OUTPUT_DIR}/peer-findings.jsonl`

### Writing findings (during your analysis)

When you discover a finding that other agents should know about, append it to the findings file. Only share findings at these severity levels:

- **blocking** — contradicts or invalidates another agent's likely analysis (e.g., "this API endpoint doesn't exist", "this data model was removed")
- **notable** — significant finding that may affect other agents' conclusions (e.g., "no authentication on admin endpoints", "critical race condition in shared state")

Do NOT share informational or improvement-level findings — those belong only in your report.

To write a finding, use the Bash tool:
```bash
bash {FINDINGS_HELPER} write "{OUTPUT_DIR}/peer-findings.jsonl" "<severity>" "{AGENT_NAME}" "<category>" "<summary>" "<file_ref1>" "<file_ref2>"
```

Where:
- `<severity>` is `blocking` or `notable`
- `<category>` is a short kebab-case tag (e.g., `api-conflict`, `auth-bypass`, `race-condition`)
- `<summary>` is a 1-2 sentence description
- `<file_ref>` entries are optional `file:line` references

### Reading peer findings (before your final report)

**Before writing your final report**, check for peer findings:

```bash
bash {FINDINGS_HELPER} read "{OUTPUT_DIR}/peer-findings.jsonl"
```

For each finding returned:
- **blocking**: You MUST acknowledge it in your report. If it affects your domain, adjust your analysis accordingly.
- **notable**: Consider whether it changes any of your recommendations. Note it if relevant.

If the findings file doesn't exist or is empty, proceed normally — you may be the first agent to finish.
```

**Step 3: Add `{FINDINGS_HELPER}` and `{AGENT_NAME}` to the template variables**

Earlier in `launch.md`, where OUTPUT_DIR and other template variables are set (around Step 2.0-2.1c), add documentation for the two new template variables:

```
FINDINGS_HELPER = ${CLAUDE_PLUGIN_ROOT}/scripts/findings-helper.sh
AGENT_NAME = <the agent's short name, e.g., fd-safety>
```

These are resolved at dispatch time when constructing each agent's prompt. The orchestrator (flux-drive skill) performs string substitution when building the Task prompt for each agent — replacing `{FINDINGS_HELPER}` with the absolute path `${CLAUDE_PLUGIN_ROOT}/scripts/findings-helper.sh` and `{AGENT_NAME}` with the agent's short name (e.g., `fd-safety`). This follows the same pattern already used for `{OUTPUT_DIR}` and `{REVIEW_FILE}`.

**Step 4: Verify the template renders correctly**

Read the modified `launch.md` and verify:
- The Peer Findings Protocol section is inside the prompt template backtick block
- `{FINDINGS_HELPER}`, `{OUTPUT_DIR}`, and `{AGENT_NAME}` are used consistently
- No orphaned backticks or broken markdown

**Step 5: Commit**

```bash
git add interverse/interflux/skills/flux-drive/phases/launch.md
git commit -m "feat(interflux): add Peer Findings Protocol to agent prompt template"
```

---

## Task 3: Add Findings Timeline to Synthesis Agent

**Files:**
- Modify: `interverse/intersynth/agents/synthesize-review.md`
- Modify: `interverse/interflux/skills/flux-drive/phases/synthesize.md`

**Step 1: Read the current synthesis agent**

Read `interverse/intersynth/agents/synthesize-review.md` to understand the full structure.

**Step 2: Add findings timeline input to synthesis agent**

In `synthesize-review.md`, in the `## Input Contract` section (line ~9), add a new parameter:

```markdown
- `FINDINGS_TIMELINE` — path to `peer-findings.jsonl` (optional; may not exist if no agents wrote findings)
```

**Step 3: Add timeline processing step to synthesis agent**

After step 3 ("Read Findings Indexes") and before step 4 ("Write verdicts"), insert a new step:

```markdown
### 3.5. Read Findings Timeline (optional)

If `FINDINGS_TIMELINE` is provided:

```bash
ls {FINDINGS_TIMELINE} 2>/dev/null
```

If the file exists:
1. Read it — each line is a JSON object with `severity`, `agent`, `category`, `summary`, `file_refs`, `timestamp`
2. Build a timeline of when agents discovered and shared findings
3. Use this in step 6 (Deduplicate) to:
   - Track **convergence via timeline**: if Agent A wrote a blocking finding AND Agent B's report acknowledges it, note "Agent B adjusted based on Agent A's finding" — this is stronger convergence than independent discovery
   - Detect **remaining contradictions**: if Agent A wrote a blocking finding about X but Agent B's report contradicts X without acknowledging the finding, flag this explicitly in the Conflicts section
   - **Attribute discovery**: when deduplicating, the agent that wrote the finding to the timeline first gets discovery credit (`"discovered_by": "agent_name"`)
4. Add a `## Findings Timeline` section to `synthesis.md` output:
   ```markdown
   ## Findings Timeline
   | Time | Agent | Severity | Category | Summary |
   |------|-------|----------|----------|---------|
   [one row per finding, ordered by timestamp]

   **Cross-agent adjustments:** [count] agents adjusted their analysis based on peer findings.
   **Unresolved contradictions:** [count or "None"]
   ```

If the file doesn't exist or is empty, skip this step entirely — synthesis proceeds as before.
```

**Step 4: Update synthesis invocation in flux-drive**

In `interverse/interflux/skills/flux-drive/phases/synthesize.md`, modify the synthesis Task invocation (Step 3.2, lines ~34-41) to pass the findings timeline:

Change the prompt from:
```
    OUTPUT_DIR={OUTPUT_DIR}
    VERDICT_LIB={CLAUDE_PLUGIN_ROOT}/../../os/clavain/hooks/lib-verdict.sh
    MODE=flux-drive
    CONTEXT="Reviewing {INPUT_TYPE}: {INPUT_STEM} ({N} agents, {early_stop_note})"
```

To:
```
    OUTPUT_DIR={OUTPUT_DIR}
    VERDICT_LIB={CLAUDE_PLUGIN_ROOT}/../../os/clavain/hooks/lib-verdict.sh
    MODE=flux-drive
    CONTEXT="Reviewing {INPUT_TYPE}: {INPUT_STEM} ({N} agents, {early_stop_note})"
    FINDINGS_TIMELINE={OUTPUT_DIR}/peer-findings.jsonl
```

**Step 5: Verify changes are consistent**

Read both modified files and verify:
- The `FINDINGS_TIMELINE` parameter name matches between invocation and input contract
- The timeline step number doesn't conflict with existing steps
- The output section format is valid markdown

**Step 6: Commit**

```bash
git add interverse/intersynth/agents/synthesize-review.md interverse/interflux/skills/flux-drive/phases/synthesize.md
git commit -m "feat(intersynth): add findings timeline to synthesis agent"
```

---

## Task 4: Add `fetch_peer_findings` Helper Command

**Files:**
- Create: `interverse/interflux/commands/fetch-findings.md`

Since the interflux MCP servers are external tools (qmd, exa) and adding a custom MCP server would require a Node.js bootstrap, we implement this as a lightweight Claude Code command that agents or users can invoke. The helper script from Task 1 does the heavy lifting.

**Step 1: Create the command file**

Create `interverse/interflux/commands/fetch-findings.md`:

```markdown
---
name: fetch-findings
description: Fetch peer findings from a flux-drive review session. Use to inspect what findings agents have shared during a parallel review.
allowed-tools: Bash, Read
---

# Fetch Peer Findings

Retrieve findings from a flux-drive intermediate findings file.

## Usage

`/interflux:fetch-findings <output_dir> [--severity blocking|notable|all]`

## Execution

1. Parse arguments:
   - `output_dir` (required): The flux-drive output directory
   - `severity` (optional, default "all"): Filter by severity level

2. Run the helper:
   ```bash
   bash ${CLAUDE_PLUGIN_ROOT}/scripts/findings-helper.sh read "{output_dir}/peer-findings.jsonl" --severity {severity}
   ```

3. Parse the JSON output and present in a readable table:
   ```
   ## Peer Findings ({count} total)

   | Time | Agent | Severity | Category | Summary |
   |------|-------|----------|----------|---------|
   | ... | ... | ... | ... | ... |
   ```

4. If no findings exist, report: "No peer findings shared yet."
```

**Step 2: Register the command in plugin.json**

In `interverse/interflux/.claude-plugin/plugin.json`, add to the `"commands"` array:

```json
"./commands/fetch-findings.md"
```

**Step 3: Verify plugin.json is valid JSON**

Run: `python3 -c "import json; json.load(open('interverse/interflux/.claude-plugin/plugin.json'))"; echo "valid"`

Expected: `valid`

**Step 4: Commit**

```bash
git add interverse/interflux/commands/fetch-findings.md interverse/interflux/.claude-plugin/plugin.json
git commit -m "feat(interflux): add fetch-findings command for peer findings access"
```

---

## Task 5: Integration Test — End-to-End Finding Flow

**Files:**
- Create: `interverse/interflux/tests/test-findings-flow.sh`

This task creates a script that validates the full flow: write findings, read them, verify schema, simulate the synthesis timeline read.

**Step 1: Write the integration test**

Create `interverse/interflux/tests/test-findings-flow.sh`:

```bash
#!/usr/bin/env bash
# Integration test: findings write → read → synthesis timeline
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
HELPER="$SCRIPT_DIR/scripts/findings-helper.sh"
TMPDIR=$(mktemp -d /tmp/findings-test-XXXXXX)
FINDINGS="$TMPDIR/peer-findings.jsonl"
PASS=0
FAIL=0

assert_eq() {
  local desc="$1" expected="$2" actual="$3"
  if [[ "$expected" == "$actual" ]]; then
    echo "  PASS: $desc"
    ((PASS++))
  else
    echo "  FAIL: $desc"
    echo "    expected: $expected"
    echo "    actual:   $actual"
    ((FAIL++))
  fi
}

echo "=== Test 1: Empty file read ==="
result=$(bash "$HELPER" read "$TMPDIR/nonexistent.jsonl")
assert_eq "empty read returns []" "[]" "$result"

echo "=== Test 2: Write blocking finding ==="
bash "$HELPER" write "$FINDINGS" "blocking" "fd-correctness" "api-conflict" \
  "POST /api/agents already exists with incompatible semantics" \
  "internal/http/handlers.go:34"
count=$(jq -s 'length' "$FINDINGS")
assert_eq "one line written" "1" "$count"

echo "=== Test 3: Write notable finding ==="
bash "$HELPER" write "$FINDINGS" "notable" "fd-safety" "auth-bypass" \
  "No authentication on admin endpoints" \
  "internal/http/router.go:89" "internal/http/middleware.go:12"
count=$(jq -s 'length' "$FINDINGS")
assert_eq "two lines total" "2" "$count"

echo "=== Test 4: Read all findings ==="
all=$(bash "$HELPER" read "$FINDINGS")
all_count=$(echo "$all" | jq 'length')
assert_eq "read all returns 2" "2" "$all_count"

echo "=== Test 5: Read blocking only ==="
blocking=$(bash "$HELPER" read "$FINDINGS" --severity blocking)
blocking_count=$(echo "$blocking" | jq 'length')
assert_eq "read blocking returns 1" "1" "$blocking_count"

echo "=== Test 6: Read notable only ==="
notable=$(bash "$HELPER" read "$FINDINGS" --severity notable)
notable_count=$(echo "$notable" | jq 'length')
assert_eq "read notable returns 1" "1" "$notable_count"

echo "=== Test 7: Schema validation ==="
first=$(jq -s '.[0]' "$FINDINGS")
has_severity=$(echo "$first" | jq 'has("severity")')
has_agent=$(echo "$first" | jq 'has("agent")')
has_category=$(echo "$first" | jq 'has("category")')
has_summary=$(echo "$first" | jq 'has("summary")')
has_refs=$(echo "$first" | jq 'has("file_refs")')
has_ts=$(echo "$first" | jq 'has("timestamp")')
assert_eq "has severity" "true" "$has_severity"
assert_eq "has agent" "true" "$has_agent"
assert_eq "has category" "true" "$has_category"
assert_eq "has summary" "true" "$has_summary"
assert_eq "has file_refs" "true" "$has_refs"
assert_eq "has timestamp" "true" "$has_ts"

echo "=== Test 8: file_refs is array ==="
refs_type=$(echo "$first" | jq '.file_refs | type')
assert_eq "file_refs is array" '"array"' "$refs_type"

echo "=== Test 9: Multiple file_refs ==="
second=$(jq -s '.[1]' "$FINDINGS")
refs_count=$(echo "$second" | jq '.file_refs | length')
assert_eq "second finding has 2 refs" "2" "$refs_count"

echo "=== Test 10: Concurrent append simulation ==="
# Launch 5 concurrent writes, each atomic (< PIPE_BUF)
for i in {1..5}; do
  bash "$HELPER" write "$FINDINGS" "notable" "fd-agent-$i" "test-$i" "Concurrent finding $i" &
done
wait
# Verify all lines are valid JSON (no interleaving corruption)
total=$(grep -c '^{' "$FINDINGS")
assert_eq "7 total findings after concurrent writes" "7" "$total"
invalid=$(grep -v '^{' "$FINDINGS" | grep -v '^$' | wc -l)
assert_eq "no corrupted lines" "0" "$invalid"

# Cleanup
rm -rf "$TMPDIR"

echo ""
echo "Results: $PASS passed, $FAIL failed"
[[ $FAIL -eq 0 ]] && exit 0 || exit 1
```

**Step 2: Make it executable**

Run: `chmod +x interverse/interflux/tests/test-findings-flow.sh`

**Step 3: Run the test**

Run: `bash interverse/interflux/tests/test-findings-flow.sh`

Expected: All 10+ assertions PASS, exit code 0.

**Step 4: Fix any failures**

If any assertions fail, fix `findings-helper.sh` from Task 1 and re-run.

**Step 5: Commit**

```bash
git add interverse/interflux/tests/test-findings-flow.sh
git commit -m "test(interflux): add integration test for findings flow"
```

---

## Task 6: Update Flux-Drive SKILL.md Compact Version

**Files:**
- Modify: `interverse/interflux/skills/flux-drive/SKILL-compact.md` (if it exists)
- Modify: `interverse/interflux/skills/flux-drive/SKILL.md` (if compact doesn't exist)

The main SKILL.md references a compact version. If it exists, it also needs the findings protocol additions.

**Step 1: Check for compact version**

Run: `ls interverse/interflux/skills/flux-drive/SKILL-compact.md 2>/dev/null`

**Step 2: If compact exists, add findings setup to its dispatch section**

Find the section where OUTPUT_DIR is set up and agent prompts are constructed. Add:
- `FINDINGS_HELPER` variable setup alongside OUTPUT_DIR
- Reference to the Peer Findings Protocol (which lives in the full prompt template in `launch.md`)

If compact doesn't exist (the comment in SKILL.md says "if it exists"), this task becomes a no-op — the changes in Task 2 (launch.md) are sufficient.

**Step 3: Add run-isolation cleanup for peer-findings.jsonl**

In the run isolation section (launch.md Step 2.0, line ~10-13), add `peer-findings.jsonl` to the cleanup:

```bash
find {OUTPUT_DIR} -maxdepth 1 -type f \( -name "*.md" -o -name "*.md.partial" -o -name "peer-findings.jsonl" \) -delete
```

This ensures stale findings from a previous run don't contaminate the new run.

**Step 4: Commit**

```bash
git add interverse/interflux/skills/flux-drive/
git commit -m "feat(interflux): add peer-findings.jsonl to run isolation cleanup"
```

---

## Task 7: Version Bump and Documentation

**Files:**
- Modify: `interverse/interflux/.claude-plugin/plugin.json` (version bump)
- Modify: `interverse/interflux/CLAUDE.md` or `interverse/interflux/AGENTS.md` (document the feature)

**Step 1: Bump version in plugin.json**

In `interverse/interflux/.claude-plugin/plugin.json`, change `"version"` from `"0.2.19"` to `"0.2.20"`.

**Step 2: Update description in plugin.json**

Update the `"description"` field to mention intermediate findings:

```json
"description": "Multi-agent review and research with scored triage, domain detection, content slicing, intermediate finding sharing, and knowledge injection. 17 agents (12 review + 5 research), 4 commands, 2 skills, 2 MCP servers. Companion plugin for Clavain."
```

Note: commands count increases from 3 to 4 (added `fetch-findings`).

**Step 3: Add feature documentation to AGENTS.md**

In `interverse/interflux/AGENTS.md`, add a section documenting the intermediate findings feature:

```markdown
## Intermediate Finding Sharing

During parallel flux-drive reviews, agents can share high-severity findings via `{OUTPUT_DIR}/peer-findings.jsonl`.

**Severity levels:**
- `blocking` — contradicts another agent's analysis (MUST acknowledge)
- `notable` — significant finding that may affect others (SHOULD consider)

**Helper script:** `scripts/findings-helper.sh`
- `write <file> <severity> <agent> <category> <summary> [file_refs...]`
- `read <file> [--severity blocking|notable|all]`

**Timeline in synthesis:** The synthesis agent reads the findings timeline for convergence tracking and contradiction detection.

**Command:** `/interflux:fetch-findings <output_dir> [--severity ...]` — inspect shared findings.
```

**Step 4: Commit**

```bash
git add interverse/interflux/.claude-plugin/plugin.json interverse/interflux/AGENTS.md
git commit -m "docs(interflux): document intermediate findings feature, bump to 0.2.20"
```
