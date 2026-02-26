# Flux-Drive Intermediate Findings — Synthesis Report

**Context:** Reviewing plan: flux-drive-intermediate-findings (2 agents, Stage 1 only)
**Agents:** 2 launched, 2 completed, 0 failed
**Verdict:** RISKY (requires major revisions before implementation)

---

## Verdict Summary

| Agent | Status | P0 | P1 | P2 | IMP | Summary |
|-------|--------|----|----|----|----|---------|
| fd-architecture | NEEDS_ATTENTION | 0 | 4 | 4 | 2 | Structural defects: shell args bug, namespace collision, unresolved template vars, broken test suite |
| fd-correctness | ERROR | 2 | 3 | 3 | 4 | Concurrency correctness: non-atomic appends, mid-write parse failures, unquiesced synthesis read |

**Overall Status: RISKY** — Two P0 issues in fd-correctness (concurrent data corruption) combine with four P1 blockers in fd-architecture to create a plan that will fail silently or noisily on first run.

---

## Critical Issues (P0)

### C1: JSONL Append Is Not Atomic — Concurrent Writers Corrupt Records

**Severity:** P0 | **Agent:** fd-correctness | **Convergence:** 1/2

The write path uses bare `>> "$findings_file"` without synchronization. On Linux, O_APPEND does not guarantee atomicity for writes exceeding PIPE_BUF (4096 bytes). Two concurrent `jq -n -c` processes can interleave their write syscalls, resulting in a corrupted record where Agent A's line end is split by Agent B's bytes.

**Evidence:** fd-correctness C1 section with concrete interleaving scenario showing byte-level corruption of JSON objects.

**Impact:** Findings silently lost or malformed in every run with 5+ parallel agents; synthesis receives incomplete or unparseable data.

---

### C2: `jq -s` Reads File Mid-Append — Parse Failure Silently Drops Findings

**Severity:** P0 | **Agent:** fd-correctness | **Convergence:** 1/2

The read path uses `jq -s` without copy-then-read or lock protection. When a writer has an incomplete line in progress, `jq -s` encounters partial JSON bytes. With `set -euo pipefail` active, the parse error causes silent exit. The agent interprets this as "no findings available" and proceeds without acknowledging blocking findings from peers.

**Evidence:** fd-correctness C2 section; scenario: fd-architecture reads while fd-safety is mid-write, then synthesis contradicts fd-architecture's report.

**Impact:** Read operations silently return empty when concurrent writes are active; synthesis contains unresolved contradictions between agents that were caused by transient race conditions, not genuine disagreement.

---

## Major Issues (P1)

### A1: `read` Subcommand Argument Parsing Bug — Filter Always Wrong

**Severity:** P1 | **Agent:** fd-architecture | **Convergence:** 2/2

In `findings-helper.sh`, the `read` case uses `shift` after reading `$1`, then reads `filter` as `${2:-all}`. After shift, the second original argument is now `$1`, not `$2`. The filter reads the *third* original parameter.

```bash
# Shell receives: read findings_file --severity blocking
# After outer shift: findings_file --severity blocking
# read) block:  findings_file="$1"  # OK
#               shift              # now: --severity blocking
#               filter="${2:-all}"  # reads blocking ✓ by accident
```

This works if `--severity` is always present, but the argument order is positionally fragile. Tests pass only because the flag happens to be in the expected position.

**Evidence:** fd-architecture A1 + fd-correctness C3 (both identify same bug with identical traces).

**Impact:** Severity filter unreliable; test 5 and 6 pass by coincidence; any caller that varies argument order gets silently wrong results.

---

### A2: `findings.jsonl` Name Collision with Synthesis Output

**Severity:** P1 | **Agent:** fd-architecture | **Convergence:** 1/2

The new peer findings file is named `findings.jsonl`. Synthesis also writes `findings.json` (different extension). These two nearly-identical names in the same OUTPUT_DIR create ambiguity for future tooling (intermap, interlearn indexing) and human readers. The synthesis agent has no explicit instruction to skip `findings.jsonl`, creating a footgun for future modifications.

**Recommended rename:** `peer-findings.jsonl` (makes ownership explicit).

**Impact:** Naming confusion in OUTPUT_DIR; future tool maintainers must explicitly handle the distinction.

---

### A3 & C8: Template Variables `{FINDINGS_HELPER}` and `{AGENT_NAME}` Have No Defined Resolution Path

**Severity:** P1 | **Agent:** fd-architecture (A3) + fd-correctness (C8) | **Convergence:** 2/2

The plan introduces `{FINDINGS_HELPER}` resolved to `${CLAUDE_PLUGIN_ROOT}/scripts/findings-helper.sh` at dispatch time. However:

1. **Dispatch-time substitution path undefined:** The plan says resolution happens "when constructing each agent's prompt" but does not specify WHERE in the orchestrator code the substitution occurs.

2. **Cache path instability (C8):** If interflux is updated mid-session, the old cache directory is deleted and paths in already-running agent prompts become invalid. The bump-version.sh symlink mitigation is not verified to cover scripts/ directory (only hooks/ noted in MEMORY).

**Impact:** Agents receive prompts with invalid paths on mid-session plugin updates, causing runtime failures; orchestrator code path ambiguous, easy to implement wrong.

---

### A4: New Shell Test Bypasses Established Python Structural Test Suite

**Severity:** P1 | **Agent:** fd-architecture | **Convergence:** 1/2

Task 4 adds `commands/fetch-findings.md` as a fourth command and registers it in plugin.json. The existing Python test (`tests/structural/test_commands.py`) asserts exactly 3 commands:

```python
assert len(files) == 3  # line 17
```

This assertion will fail immediately. The plan creates a parallel shell test in `tests/test-findings-flow.sh` but makes no mention of updating the structural tests. The Python test suite is the canonical correctness gate.

**Impact:** CI/test suite broken on first day; implementation halts at structural test failure.

---

### C4: Concurrent-Write Simulation Cannot Detect Data Corruption

**Severity:** P1 | **Agent:** fd-correctness | **Convergence:** 1/2

Test 10 forks 5 background writers and checks that 7 records exist:

```bash
for i in {1..5}; do ... &; done; wait
total=$(jq -s 'length' "$FINDINGS")
assert_eq "7 total findings" "7" "$total"
```

This cannot detect split-write corruption (C1 scenario). If two writes interleave and corrupt a record, `jq -s` fails with parse error, causing the script to exit non-zero — the test is reported as a crash, not a FAIL assertion. The test gives false confidence that concurrent safety is validated.

**Impact:** Test passes without detecting the primary failure mode it claims to address; P0 bugs ship with no test coverage.

---

### C5: Synthesis Reads findings.jsonl While Agents May Still Be Writing

**Severity:** P1 | **Agent:** fd-correctness | **Convergence:** 1/2

The protocol instructs agents to write findings.jsonl **during analysis**, not only at completion. Synthesis runs after all `.md` files complete (the orchestrator's completion signal). However, the last agent to write may have an in-flight append at the exact moment synthesis begins reading. With writeback caching, the read may capture a partially-flushed file.

Combined with C1 and C2, this creates a TOCTOU window where synthesis silently observes an incomplete view of findings.

**Impact:** Synthesis findings incomplete or corrupt, with no log evidence that a read race occurred.

---

## Debt Issues (P2)

### A5: Synthesis Step Numbering Gap — "3.5" Is Unusual

**Severity:** P2 | **Agent:** fd-architecture | **Convergence:** 1/2

The plan inserts "step 3.5" into synthesize-review.md, which uses standard step numbers (1-8). The decimal notation is inconsistent with existing patterns. Should renumber as step 4+ or use `3b` format.

**Impact:** Agent confusion during implementation; unclear instruction ordering.

---

### A6: Task 6 Step 3 Modifies `launch.md` But Is Scoped Under SKILL-compact.md Task

**Severity:** P2 | **Agent:** fd-architecture | **Convergence:** 1/2

Task 6 is titled "Update Flux-Drive SKILL.md Compact Version" but Step 3 modifies `launch.md` (different file). The cross-file modification is buried in the task and may be missed if an implementor concludes SKILL-compact.md doesn't exist and skips the task entirely.

**Impact:** Cleanup pattern in launch.md may not be applied; findings.jsonl cleanup incomplete in subsequent runs.

---

### A7: Nested Backtick Code Fences in Agent Prompt Template

**Severity:** P2 | **Agent:** fd-architecture | **Convergence:** 1/2

The agent prompt template is delimited by ```` ``` ```` (lines 285-440 in launch.md). The new "Peer Findings Protocol" section contains its own triple-backtick code blocks. Triple-backtick fences cannot nest in markdown. The first inner ` ``` ` will terminate the outer template block prematurely.

**Fix:** Use indented code blocks (4-space) or `~~~` alternative fence syntax.

**Impact:** Agent receives truncated prompt; Peer Findings Protocol section lost.

---

### C6: No Validation of `severity` Values

**Severity:** P2 | **Agent:** fd-correctness | **Convergence:** 1/2

The write command accepts `severity` as a raw argument without validation. An agent can pass `severity=""` or `severity="all"` and produce invalid records. Synthesis logic expecting `blocking` or `notable` will silently skip unrecognized values.

**Fix:** Add `case "$severity"` guard before `jq -n -c`.

**Impact:** Malformed records in timeline; synthesis logic complexity increases.

---

### C7: Run-Isolation Cleanup Races Next Run's Writes

**Severity:** P2 | **Agent:** fd-correctness | **Convergence:** 1/2

Task 6 Step 3 adds findings.jsonl to the cleanup pattern. If two flux-drive runs execute on the same OUTPUT_DIR in rapid succession, cleanup from run 1 may delete the findings.jsonl before synthesis has finished reading it. The synthesis read uses `ls` to check file existence; on unlink, `ls` returns 1 and synthesis skips the timeline step.

**Mitigation:** Use timestamped OUTPUT_DIRs (already recommended as an option).

**Impact:** Low probability but documented race; can be prevented via usage discipline (doc note required).

---

## Nice-to-Have Issues (IMP)

### A9: Defer `fetch-findings` Command (YAGNI)

**Severity:** IMP | **Agent:** fd-architecture | **Convergence:** 1/2

The command adds a fourth `commands/` file, requires test suite updates, and has no current users (only debug use). The helper script already provides the capability.

**Recommendation:** Defer to follow-up; keep this plan's diff minimal.

---

### A10: Define Sync Rule Between `launch.md` and `SKILL-compact.md`

**Severity:** IMP | **Agent:** fd-architecture | **Convergence:** 1/2

After Task 6 adds cleanup to `launch.md`, the compact skill's description becomes silently incomplete. Add a one-line note in SKILL-compact.md: "findings.jsonl is also cleared (see launch.md Step 2.0)."

---

### I1, I2, I3, I4: Concurrency Improvements

**Severity:** IMP (addressing P0/P1) | **Agent:** fd-correctness | **Convergence:** 4/4

- **I1:** Use `flock -x` for serialized appends (prevents C1)
- **I2:** Copy-then-read pattern (prevents C2)
- **I3:** Strengthen Test 10 to detect corruption, run 10x (validates C4 fix)
- **I4:** Validate severity values at write time (prevents C6)

---

## Files Affected

- **Agent Reports:**
  - `/home/mk/projects/Demarch/docs/research/flux-drive/flux-drive-intermediate-findings/fd-architecture.md`
  - `/home/mk/projects/Demarch/docs/research/flux-drive/flux-drive-intermediate-findings/fd-correctness.md`

- **Verdict Files:**
  - `.clavain/verdicts/fd-architecture.json`
  - `.clavain/verdicts/fd-correctness.json`

---

## Conflicts & Convergence

**Convergence Summary:**

| Finding | fd-arch | fd-correct | Convergence |
|---------|---------|-----------|-------------|
| `read` arg parsing (A1=C3) | ✓ | ✓ | 2/2 |
| `{FINDINGS_HELPER}` path (A3=C8) | ✓ | ✓ | 2/2 |
| Non-atomic appends (C1) | — | ✓ | 1/2 |
| Mid-write parse failure (C2) | — | ✓ | 1/2 |
| Concurrent Test 10 invalid (C4) | — | ✓ | 1/2 |
| Synthesis unquiesced read (C5) | — | ✓ | 1/2 |
| Naming collision (A2) | ✓ | — | 1/2 |
| Test suite breakage (A4) | ✓ | — | 1/2 |

**No contradictions.** fd-correctness discovered concurrency-specific issues; fd-architecture discovered structural/integration issues. Both sets are valid and complementary.

---

## Recommendations

### Before Implementation

1. **Fix P0 (concurrency correctness):**
   - Add `flock` serialization to write path (I1)
   - Replace bare `jq -s` with copy-then-read pattern (I2)
   - Add `sync` barrier after agent loop before synthesis dispatch (C5 mitigation)

2. **Fix P1 (structural defects):**
   - Rewrite `read` case to parse `--severity` flag explicitly (A1/C3)
   - Rename `findings.jsonl` → `peer-findings.jsonl` (A2)
   - Define exact substitution path for `{FINDINGS_HELPER}` and `{AGENT_NAME}` in orchestrator (A3/C8)
   - Update `tests/structural/test_commands.py` to assert 4 commands or defer `fetch-findings` (A4)
   - Verify bump-version.sh symlink covers scripts/ directory for cache migration (C8 mitigation)

3. **Fix P2 (integration debt):**
   - Renumber synthesis steps or clarify "3.5" → "3b" (A5)
   - Move launch.md cleanup to its own task or explicit conditional (A6)
   - Replace nested backtick fences with indented or `~~~` syntax (A7)
   - Add severity validation guard (C6)
   - Document non-concurrent OUTPUT_DIR usage (C7 mitigation)
   - Add note to SKILL-compact.md about cleanup sync (A10)

4. **Defer:**
   - `fetch-findings` command (A9) — post-shipping follow-up

### For Implementation Teams

- Review fd-correctness's concurrency analysis first — these are the runtime failure modes.
- Apply I1, I2, I3, I4 concurrency fixes together; they form a cohesive locking + read-safety strategy.
- Run Test 10 in a loop (10+x) after fixes to catch timing-dependent failures.
- Document the non-concurrent OUTPUT_DIR usage assumption in SKILL-compact.md or launch.md.

---

## Summary

The plan's transport design (append-only JSONL in OUTPUT_DIR) is sound and integration is optional. However, **two P0 issues guarantee silent data loss or corruption in every parallel run**, and **four P1 blockers will cause immediate implementation failures** (shell bug, namespace collision, unresolved template paths, broken test suite). These are all fixable within the current scope and timeline. Once P0/P1 are resolved, P2 issues are low-cost to address in-band during each task.

**Verdict: RISKY (requires major revisions). Do not proceed to implementation until P0 and P1 are resolved.**

---

*Report generated 2026-02-22. Complete agent analyses available in output directory.*
