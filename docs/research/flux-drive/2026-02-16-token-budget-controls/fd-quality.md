### Findings Index

| Severity | ID | Section | Title |
|----------|----|---------|----------------------------------------------------|
| P1 | Q1 | Task 2 | Bash argument parsing uses shift incorrectly |
| P1 | Q2 | Task 2 | SQL injection vulnerability in model parameter |
| P1 | Q3 | Task 2 | Missing error handling for jq failures |
| P2 | Q4 | Task 2 | Race condition in DB access without locking |
| P2 | Q5 | Task 2 | Inconsistent quoting in YAML grep patterns |
| P2 | Q6 | Task 7 | Test uses Python for YAML validation but no dependency check |
| P2 | Q7 | Task 3 | Budget cut pseudocode doesn't handle min_agents edge case |
| P2 | Q8 | Task 5 | SQL query uses session_id without escaping |
| I1 | — | Task 2 | Add early validation for required dependencies |
| I2 | — | Task 7 | Tests should verify actual script output structure |
| I3 | — | Task 2 | Document fallback behavior when interstat unavailable |
| I4 | — | Task 1 | Add comment explaining slicing_multiplier rationale |
| I5 | — | Task 3 | Clarify slicing detection mechanism in Step 1.2c.2 |

**Verdict**: needs-changes

---

### Summary

The plan implements budget-aware agent dispatch with reasonable architecture and appropriate use of bash scripting. However, the bash script (estimate-costs.sh) contains multiple quality issues: incorrect argument parsing that will fail for valid input, SQL injection vulnerability in the model parameter, and missing error handling for jq failures. The test suite validates structure but not actual behavior, and the SQL queries in skills lack proper escaping. The YAML naming convention is clean but the grep-based parsing is fragile. Error handling patterns are inconsistent across tasks.

---

### Issues Found

**Q1. P1: Bash argument parsing uses shift incorrectly**
Lines 86-96 in estimate-costs.sh initialize MODEL to "--model" as a sentinel value, then test `if [[ "$MODEL" == "--model" ]]` to apply a default. This breaks when the user provides `--model claude-opus-4-6` because the shift logic only shifts by 2 for `--model`, but line 94 will still execute `shift` for unrecognized args, causing the model value to be lost. Additionally, the loop condition `while [[ $# -gt 0 ]]` combined with the catch-all `*) shift ;;` will consume all arguments without validation. Correct pattern: parse known flags with `case`, reject unknown flags with `echo "Unknown flag: $1" >&2; exit 1`, and don't use sentinel values for required parameters.

**Q2. P1: SQL injection vulnerability in model parameter**
Line 144 in estimate-costs.sh embeds `$MODEL` directly into SQL: `WHERE (model = '${MODEL}' OR model IS NULL)`. If a malicious actor controls the `--model` parameter (e.g., from a project-level config file), they can inject arbitrary SQL. Example: `--model "'; DROP TABLE agent_runs; --"`. Fix: use sqlite3 parameterized queries with `.parameter` or pre-validate MODEL against a whitelist of known model names.

**Q3. P1: Missing error handling for jq failures**
Lines 152-156 and 168-184 pipe JSON through jq without checking exit codes. If jq fails (invalid JSON, syntax error in filter), the script continues with empty/malformed output. The `|| echo "[]"` on line 149 only catches sqlite3 failures, not jq parse errors. Fix: capture jq exit codes or use `set -o pipefail` (already set) with explicit checks: `ESTIMATES=$(... | jq ... ) || { echo "Error: jq failed" >&2; exit 1; }`.

**Q4. P2: Race condition in DB access without locking**
estimate-costs.sh queries `~/.claude/interstat/metrics.db` at line 141 without any locking. If interstat is simultaneously writing to the DB (backfilling tokens at SessionEnd), sqlite3 may return `database is locked` errors. The script doesn't retry or handle SQLITE_BUSY. Best practice for read-only queries: add `-readonly` flag to sqlite3 invocation and/or add a retry loop with exponential backoff for locked database errors.

**Q5. P2: Inconsistent quoting in YAML grep patterns**
Lines 108 and 117 use `grep "^  ${agent_type}:"` and `grep "^slicing_multiplier:"` to parse YAML. The first pattern requires two spaces for indentation (correct for `agent_defaults` children), but this is fragile and undocumented. If budget.yaml is reformatted with different indentation, parsing silently fails and defaults to hardcoded values. Better: use `yq` (mentioned as "no yq dependency" in comment on line 103, but this is a false economy — adding yq would eliminate all the fragile grep/sed parsing) or at minimum document the required YAML structure and add indentation validation to tests.

**Q6. P2: Test uses Python for YAML validation but no dependency check**
Test 1 (line 464) runs `python3 -c "import yaml; yaml.safe_load(...)"` without checking if PyYAML is installed. If yaml module is missing, test fails with ImportError instead of a clear message. The existing detect-domains.py script (lines 32-35 in that file) shows the correct pattern: wrap yaml import in try/except and print a clear error. Test suite should either vendor this check or document PyYAML as a test-time dependency in AGENTS.md.

**Q7. P2: Budget cut pseudocode doesn't handle min_agents edge case**
Lines 236-242 in Task 3 describe the budget cut algorithm: `if cumulative + agent.est_tokens > BUDGET_TOTAL and agents_selected >= min_agents`. This logic has an off-by-one error when `min_agents=2` and both top-scoring agents individually exceed the budget. The pseudocode will select the first agent (agents_selected=0, condition false), then select the second (agents_selected=1, condition false), then defer the third (agents_selected=2, condition true). But if agent 1 costs 90K and agent 2 costs 80K, cumulative is 170K before checking agent 3. If budget is 150K, the condition `cumulative + agent3 > 150K` is true BUT we've already violated the budget at agent 2. Correct: track `agents_selected` incrementally and check cumulative AFTER addition, not before.

**Q8. P2: SQL query uses session_id without escaping**
Lines 327-328 in Task 5 embed `{current_session_id}` and `{launched_agents_quoted}` into SQL without specifying how to escape them. Session IDs are UUIDs (safe), but the instructions don't clarify this. If session_id ever contains quotes or is user-controlled, this becomes SQL injection. The comment says "launched_agents_quoted" but doesn't show the quoting implementation. Correct: show example of safe quoting: `WHERE session_id = '${SESSION_ID}' AND agent_name IN ('agent1', 'agent2')` with explicit single-quote wrapping per agent name.

---

### Improvements

**I1. Add early validation for required dependencies**
estimate-costs.sh depends on `sqlite3`, `jq`, and the budget.yaml file. Add explicit checks at the top of the script (after argument parsing): `command -v sqlite3 >/dev/null || { echo "Error: sqlite3 not found" >&2; exit 1; }` and same for jq. Check that `$BUDGET_FILE` exists before calling `get_default`. This provides clear error messages instead of cryptic failures deep in the script. Rationale: follows defensive scripting best practices and improves debuggability.

**I2. Tests should verify actual script output structure**
Test 6 (lines 505-510) checks that estimate-costs.sh produces valid JSON with a `defaults` key, but doesn't validate the structure of `estimates` (should be object with `est_tokens`, `sample_size`, `source` keys) or that numeric values are actually numbers. Add: `jq -e '.estimates | to_entries[] | select(.value.est_tokens | type != "number")' >/dev/null && fail "estimates contains non-numeric tokens"`. Rationale: structure validation catches regressions in the jq transform logic.

**I3. Document fallback behavior when interstat unavailable**
Lines 139-158 query interstat DB with fallback to empty estimates if DB doesn't exist or query fails. This is the correct graceful degradation pattern, but it's only mentioned in passing in Task 3 line 249 ("No-data graceful degradation"). Add a comment in the script at line 139: `# Graceful degradation: if interstat DB doesn't exist or has no data, all agents use defaults from budget.yaml`. Rationale: makes the fallback path explicit for future maintainers.

**I4. Add comment explaining slicing_multiplier rationale**
budget.yaml line 50 sets `slicing_multiplier: 0.5` without explanation. Why 0.5x? Is this empirically derived or a conservative guess? Add comment: `# 0.5x multiplier: agents reviewing sliced sections see less content (typically 1-2 sections vs full doc)`. Rationale: documents the assumption for future tuning when actual slicing data is available.

**I5. Clarify slicing detection mechanism in Step 1.2c.2**
Line 229 in Task 3 says "If slicing is active AND agent is NOT cross-cutting (fd-architecture, fd-quality): multiply estimate by slicing_multiplier". But the skill doesn't specify how to detect "slicing is active". Is this from a flag file? A variable in the skill execution context? The compact skill doesn't mention slicing detection in Step 1.2c. Add explicit instruction: "Slicing is active if `slicing_map` variable is populated (set by Phase 2 slicing.md)." Rationale: prevents ambiguity during implementation.

---

<!-- flux-drive:complete -->
