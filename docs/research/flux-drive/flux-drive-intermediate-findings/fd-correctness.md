# Correctness Review: Flux-Drive Intermediate Finding Sharing

Reviewer: fd-correctness (Julik, Flux-drive Correctness Reviewer)
Date: 2026-02-22

---

### Findings Index

- P0 | C1 | "Task 1 — write command" | JSONL append is not atomic: concurrent writers corrupt records
- P0 | C2 | "Task 1 — read command" | `jq -s` reads file mid-append: partial last line silently dropped or crashes
- P1 | C3 | "Task 1 — read command" | `filter` variable reads `$2` after first `shift`, always evaluates as empty or wrong arg
- P1 | C4 | "Task 5 — Test 10" | Concurrent-write simulation cannot distinguish data loss from a timing window
- P1 | C5 | "Task 3 — Step 3.5" | Synthesis reads findings.jsonl while writers are still running (no quiesce boundary)
- P2 | C6 | "Task 1 — write command" | No validation of `severity` values; any string reaches the JSONL record
- P2 | C7 | "Task 6 — Step 3" | Run-isolation cleanup races the next run's writes in fast back-to-back runs
- P2 | C8 | "Task 2 — Peer Findings Protocol" | Template variable `{FINDINGS_HELPER}` resolved at dispatch not at install time — breaks portability
- IMP | I1 | "Task 1 — write command" | Use a lock file (`flock`) or write-to-tmp-then-append for safe concurrent appends
- IMP | I2 | "Task 1 — read command" | Guard `jq -s` with a file-size-stable wait or copy-then-read pattern
- IMP | I3 | "Task 5 — Test 10" | Replace background-job loop with explicit serialized concurrent writes through a real interleaving harness
- IMP | I4 | "Task 1 — write command" | Validate `severity` is one of `blocking|notable` before appending

Verdict: risky

---

### Summary

The plan introduces a shared JSONL append file written by multiple parallel bash subagents without any synchronization. On Linux, appends to a shared file from concurrent processes are atomic only when the write fits within `PIPE_BUF` (4096 bytes) and is directed at a pipe — regular file appends have no such guarantee. A jq JSON object from a verbose summary easily exceeds 4096 bytes, and even short records are vulnerable to split writes if an OS preemption occurs between the `jq -n -c` computation and the `>>` write. The read path ingests the file with `jq -s` at a moment when a writer may have an incomplete line in progress, producing either a JSON parse error (if `set -euo pipefail` is active) or silently dropping the last in-flight record. The integration test's concurrency simulation (`for i in {1..5}; do ... &; done; wait`) does not reproduce the split-write failure class: it only tests whether five complete records land, not whether any record arrives torn. The synthesis agent reads findings.jsonl before agents are guaranteed to have finished writing, creating a TOCTOU window. These three issues compose into a scenario where the on-call engineer sees synthesis reporting zero blocking findings when three were written, with no log evidence of what happened.

---

### Issues Found

**C1. P0: JSONL append is not atomic — concurrent writers corrupt records**

The write path is:

```bash
jq -n -c ... '{severity:$sev, ...}' >> "$findings_file"
```

`jq -n -c` produces a single line then exits; the shell then performs a `>>` append. Two problems:

1. The open-O_APPEND + write syscall sequence is atomic only if the kernel's write does not exceed `PIPE_BUF` (512 bytes on POSIX minimum, 4096 on Linux for regular files — but POSIX does NOT guarantee atomicity for regular-file O_APPEND writes beyond one page). `man 2 write` states: "If the O_APPEND flag of the file status flags is set, the file offset shall be set to the end of the file prior to each write and no intervening file modification operation shall occur between changing the file offset and the write operation." The "no intervening" guarantee applies to the single write syscall but not to the sequence `jq` → pipe → shell `>>` which may internally buffer and require multiple write(2) calls if the JSON line is large.

2. More practically: `jq` writes its output to stdout, which the shell redirects. The shell forks `jq`, `jq` produces output to its stdout fd, the shell performs the `>>` in the parent after `jq` exits. If two agents execute this sequence concurrently, the kernel serialises the individual write(2) calls but does NOT guarantee that write(2) for Agent A's line completes before Agent B's partial write begins in the same kernel scheduling quantum. On a multi-core machine (this is Linux 6.8 SMP), two `>>` writes can race even with O_APPEND.

**Concrete interleaving that corrupts data:**

```
Agent A: jq produces: {"severity":"blocking","summary":"POST /api/agents already exists","file_refs":["internal/http/handlers.go:34"],"timestamp":"2026-02-22T18:00:00Z"}\n
Agent B: jq produces: {"severity":"notable","summary":"No auth on admin endpoints","file_refs":["internal/http/router.go:89"],"timestamp":"2026-02-22T18:00:00Z"}\n

kernel write ordering:
  1. Agent A write(fd, buf_A, 120 bytes)   → 120 bytes land at offset 0
  2. Agent B write(fd, buf_B[0:50], 50)    → 50 bytes land at offset 120
  3. Agent A write(fd, buf_A[120:], 0)     → (A already done, but B is not)
  4. Agent B write(fd, buf_B[50:], 70)     → 70 bytes land at offset 170
```

Result: file contains Agent A's record intact, then Agent B's record split by whatever Agent A's trailing bytes happened to be. `jq -s` on this file returns a parse error and `set -euo pipefail` in the read path causes the caller to exit non-zero silently.

In practice jq JSON lines for this use case are 150-300 bytes, so the probability of a mid-write preemption is low per-write but non-zero per run with 5-12 agents each writing 1-3 findings. Over hundreds of runs this failure becomes routine.

**Minimal fix:** Use `flock` to serialise the append:

```bash
(
  flock -x 200
  jq -n -c \
    --arg sev "$severity" \
    ... \
    '{severity:$sev, ...}' >> "$findings_file"
) 200>"${findings_file}.lock"
```

`flock -x` on a lock file serialises all concurrent appenders without touching the data file. The lock file is cheap to create and does not need cleanup (it is empty; its existence is harmless on the next run).

---

**C2. P0: `jq -s` reads file mid-append — partial last line silently dropped or parse error**

The read path:

```bash
jq -s '.' "$findings_file"
```

`jq -s` reads the entire file into memory and parses it as a stream of JSON values. If a writer is mid-write (has written 60 of 120 bytes of a line), `jq -s` reads those 60 bytes as the tail of the stream. The partial bytes are not valid JSON. `jq` exits non-zero with a parse error. Because the read is called from within `set -euo pipefail` (the helper script itself has `set -euo pipefail` at the top), the shell exits immediately with no output.

From the agent's perspective: `bash {FINDINGS_HELPER} read ...` returns exit code 1 with no JSON. The agent prompt says "If the findings file doesn't exist or is empty, proceed normally." The agent cannot distinguish an empty result from a mid-write parse failure, so it proceeds as if no peers have written anything — silently discarding all in-flight findings.

**Concrete scenario:** Agent fd-architecture finishes early and calls `read` at the exact moment Agent fd-safety is halfway through writing a blocking finding about an unauthenticated admin endpoint. fd-architecture proceeds without seeing the finding. Synthesis also reads the file; by then fd-safety has finished, so synthesis sees it — but fd-architecture's report has already concluded without acknowledging the blocking finding. Synthesis flags "remaining contradiction: fd-architecture does not acknowledge fd-safety's auth-bypass finding" — which is correct but was caused by a read race, not a genuine disagreement.

**Minimal fix:** Copy-then-read pattern:

```bash
local tmpread
tmpread=$(mktemp)
cp "$findings_file" "$tmpread"
jq -s '.' "$tmpread"
rm -f "$tmpread"
```

The `cp` reads a consistent snapshot under O_RDONLY. Any incomplete line at the copy boundary is at worst the last partial line, which can be handled with `jq -s '[.[]?]'` (permissive) or by accepting that very recent in-flight writes are not visible (which is the correct semantic: "check what peers have written so far"). Combined with the `flock` fix in C1, the lock ensures `cp` never captures a torn record.

Alternatively, with `flock` in place on writes, add a shared lock on reads:

```bash
(flock -s 200; jq -s '.' "$findings_file") 200>"${findings_file}.lock"
```

---

**C3. P1: `filter` variable in read command reads `$2` after first `shift` — always empty or wrong**

The read case in `findings-helper.sh`:

```bash
read)
  findings_file="$1"; shift
  filter="${2:-all}"
```

After `shift`, `$1` is gone. The remaining positional parameters are renumbered: what was `$2` is now `$1`, what was `$3` is now `$2`. But `filter` is assigned from `${2:-all}` — which is now the *third* original argument (the one after `--severity`). The call signature from Task 1 is:

```
findings-helper.sh read <findings_file> --severity blocking
```

After the outer `shift` (consuming `cmd`), positional params are: `$1=findings_file`, `$2=--severity`, `$3=blocking`. Inside `read)`: `findings_file="$1"` consumes `$1=findings_file`. Then `shift` makes `$1=--severity`, `$2=blocking`. Then `filter="${2:-all}"` sets `filter=blocking`. This looks correct for the `--severity` form.

But the integration test (Test 5) calls:

```bash
bash "$HELPER" read "$FINDINGS" --severity blocking
```

Let's trace again carefully with `set -euo pipefail` and the outer `shift || true`:

- Script receives: `$1=read`, `$2=$FINDINGS`, `$3=--severity`, `$4=blocking`
- `cmd="${1:-}"` → `cmd=read`; `shift || true` → `$1=$FINDINGS`, `$2=--severity`, `$3=blocking`
- `case "$cmd"` → `read)` branch
- `findings_file="$1"` → `findings_file=$FINDINGS`; `shift` → `$1=--severity`, `$2=blocking`
- `filter="${2:-all}"` → `filter=blocking` ✓

This works for the `--severity X` form when `--severity` is passed. But the `--severity` flag itself is consumed by `$1` and never checked — it is silently discarded. The filter is set from `$2` (the value after `--severity`), which happens to be the severity value. This is a positional dependency on the flag being present: if the caller passes only one extra arg (e.g., `read "$FINDINGS" all`), then after the inner `shift`, `$1=all` and `$2` is unset, so `filter="${2:-all}"` → `filter=all`. The argument is effectively ignored.

More seriously: the plan's Step 3 test in Task 1 calls:

```bash
bash interverse/interflux/scripts/findings-helper.sh read "$tmpfile" --severity blocking
```

This works by accident. But the implementation does NOT parse `--severity` as a flag — it just takes the second positional parameter after `findings_file` regardless of what comes before it. If any caller omits `--severity` and passes the severity value directly, or changes argument order, the filter silently defaults to `all`.

**The read command should either:**
- Parse `--severity` explicitly with `while [[ $# -gt 0 ]]; do case "$1" in --severity) filter="$2"; shift 2;; esac; done`, or
- Remove the `--severity` flag syntax entirely and use positional: `read <file> [blocking|notable|all]`

The current code is internally consistent but only by coincidence and is fragile to any caller variation.

---

**C4. P1: Concurrent-write simulation in Test 10 cannot detect split-write data corruption**

Test 10:

```bash
for i in {1..5}; do
  bash "$HELPER" write "$FINDINGS" "notable" "fd-agent-$i" "test-$i" "Concurrent finding $i" &
done
wait
total=$(jq -s 'length' "$FINDINGS")
assert_eq "7 total findings after concurrent writes" "7" "$total"
```

This test checks that 7 records exist in the file after 5 concurrent appends. It cannot detect the following failure modes:

1. **Split write producing a garbled record**: If two writes race and interleave bytes, `jq -s 'length'` on the corrupted file will fail with parse error, causing `jq` to exit non-zero. With `set -euo pipefail` in the test script, this exits the test with no assertion — the test does not count as FAIL but as script crash. The test runner would report a bash error, not an assertion failure.

2. **Silent record drop**: If a write fails (e.g., `jq` process is killed mid-write due to signal) and the error is not caught, `total` could be 6. The assertion would catch this — but only if the script doesn't crash first from the parse error described above.

3. **Serialized writes masquerading as concurrent**: On a lightly loaded single-core system or with short `jq` execution time, the five background jobs may execute serially by luck, passing the test without exercising true concurrency. The test gives no signal about whether real interleaving occurred.

**What the test validates:** That 5 sequential-in-practice appends produce 5 correct records. That is not evidence of concurrent safety.

**Minimal improvement:** Check for write integrity by comparing expected record count with `jq -s 'length'` AND verify each record is valid JSON:

```bash
if ! total=$(jq -s 'length' "$FINDINGS" 2>/dev/null); then
  echo "  FAIL: concurrent writes corrupted the JSONL file (parse error)"
  ((FAIL++))
fi
```

More importantly: the only reliable concurrency test is stress-repetition (run 1000 times and check for corruption) or lock-based serialisation that makes the race impossible. The test as written gives false confidence.

---

**C5. P1: Synthesis reads findings.jsonl while parallel agents may still be writing**

Task 3 Step 3 inserts a synthesis step that reads `FINDINGS_TIMELINE` (= `{OUTPUT_DIR}/findings.jsonl`). The synthesis agent is launched from synthesize.md Step 3.2, which is reached only after `Step 3.0: Verify all agents completed`. This means all reviewer agents have finished their `.md` files before synthesis begins.

However, the Peer Findings Protocol in the agent prompt says:

> "When you discover a finding ... append it to the findings file."

Agents are instructed to write to findings.jsonl **during** their analysis, not only at the end. The `.md.partial` → `.md` rename is the completion signal for the orchestrator. An agent can write to findings.jsonl at any point during its run — including the same time another agent is in its reading phase.

The orchestrator only waits for `.md` files. It does not wait for findings.jsonl to be stable. An agent that completes its `.md` file (rename complete) may be in the middle of a final write to findings.jsonl — because the protocol says "before writing your final report, check for peer findings" and writing the findings.jsonl entry happens BEFORE renaming `.md.partial` to `.md`. So by the time synthesis runs, all agents have completed — but the last agent to write to findings.jsonl may have had its write interrupted by the process completing and not flushed.

More specifically: the typical bash file descriptor flush on process exit is not guaranteed to be observed by a concurrent `jq -s` reader unless `fsync` or `close` has returned. Shell scripts do not call `fsync`. On Linux with writeback caching, this is almost always fine — but the synthesis read of findings.jsonl should occur after a brief sync barrier or after confirming the file's line count matches expectations.

**This is a lower probability issue than C1/C2** but the window exists: if the synthesis subagent begins reading findings.jsonl within milliseconds of the last reviewer completing, it may see a partially-flushed file. Practical fix: add `sync` after the agent loop and before synthesis dispatch, or accept this as best-effort (the protocol already says synthesis proceeds normally if file is missing/empty).

---

**C6. P2: No validation of `severity` values — any string reaches the JSONL record**

The write command accepts `severity` as a raw argument and passes it directly to `jq`:

```bash
severity="$1"; shift
...
--arg sev "$severity" \
'{severity:$sev, ...}'
```

An agent that calls:

```bash
bash findings-helper.sh write "$findings" 'blocking"; rm -rf /' fd-test ...
```

cannot inject through jq (jq's `--arg` is safe; it does not evaluate shell). However, an agent that passes a severity of `all` or `informational` or an empty string produces a record with an invalid severity value. When the synthesis agent reads the timeline and tries to categorize findings, it finds records with severity `""` or `all` that do not match `blocking` or `notable`. The plan says synthesis will "track convergence via timeline" and "attribute discovery" — none of that logic handles unknown severity gracefully.

**Fix:** Validate in the write command:

```bash
case "$severity" in
  blocking|notable) ;;
  *) echo "findings-helper: invalid severity '$severity' (must be blocking or notable)" >&2; exit 1 ;;
esac
```

---

**C7. P2: Run-isolation cleanup races the next run's writes in fast back-to-back invocations**

Task 6 Step 3 adds `findings.jsonl` to the run-isolation cleanup:

```bash
find {OUTPUT_DIR} -maxdepth 1 -type f \( -name "*.md" -o -name "*.md.partial" -o -name "findings.jsonl" \) -delete
```

This `find -delete` runs at the start of Phase 2 (Step 2.0). If a user runs flux-drive twice in rapid succession on the same OUTPUT_DIR and the second run begins Phase 2 cleanup before the first run's synthesis agent has finished reading `findings.jsonl`, the cleanup deletes the file mid-read. `jq -s` on an unlinked but open file descriptor continues reading correctly (Linux unlink semantics: the inode persists until the last file descriptor closes). So this is not a corruption risk for the current run. However, the synthesis agent uses `ls {FINDINGS_TIMELINE} 2>/dev/null` to check file existence — if the file has been unlinked, `ls` returns exit code 1 and synthesis skips the timeline step, discarding all findings from the previous run's cleanup window.

This is a narrow race (two runs on the same OUTPUT_DIR within seconds of each other) and is prevented by using timestamped OUTPUT_DIRs, which the plan already recommends as an option. But the non-timestamped case is explicitly supported and should be documented as "do not run two instances against the same OUTPUT_DIR concurrently."

---

**C8. P2: `{FINDINGS_HELPER}` resolved at dispatch time — breaks when plugin cache path changes**

The agent prompt template uses:

```
bash {FINDINGS_HELPER} write "{OUTPUT_DIR}/findings.jsonl" ...
```

Where `FINDINGS_HELPER = ${CLAUDE_PLUGIN_ROOT}/scripts/findings-helper.sh` is documented as resolved at dispatch time. `${CLAUDE_PLUGIN_ROOT}` resolves to the plugin's installed cache directory at the moment the flux-drive skill runs. If the interflux plugin is updated mid-session (version bump → cache update), the old cache directory is deleted and the path embedded in already-running agent prompts becomes invalid. The MEMORY.md notes: "Mid-session publish breaks Stop hooks: Claude Code bakes hook paths at session start. When marketplace push triggers cache update, old version dir is deleted. `bump-version.sh` creates old->new symlink as mitigation."

The same symlink mitigation from bump-version.sh that protects hooks would also protect agent prompts — but the plan does not mention that this mitigation must be verified to cover the scripts/ directory. If the symlink only covers the hooks/ directory (as suggested by the MEMORY note), agents that have already received prompts with `{FINDINGS_HELPER}` pointing to the old cache path will fail when they try to call the script.

**Minimal fix:** Use an absolute path to the canonical (non-cache) location of the script, or verify that bump-version.sh's symlink covers the scripts/ subdirectory, and document this dependency.

---

### Improvements

**I1. Use `flock` for serialized appends (addresses C1)**

Replace the bare `>> "$findings_file"` with an `flock -x` around the jq-plus-append sequence. The lock file path `${findings_file}.lock` is natural, zero-overhead for sequential cases, and prevents byte-interleave corruption across concurrent processes. Include `trap 'rm -f "${findings_file}.lock"' EXIT` at script top only if the process is the lock creator — or simply leave the lock file (empty, harmless).

**I2. Copy-then-read pattern prevents mid-write jq parse failure (addresses C2)**

Before `jq -s`, atomically copy the file to a temp path and read from the copy. This eliminates the race between reads and in-progress writes without requiring the reader to hold a lock. A shared flock on reads is also acceptable if write lock discipline (I1) is in place.

**I3. Strengthen Test 10 to detect corruption, not just count (addresses C4)**

After `wait`, run `jq -s '.' "$FINDINGS" > /dev/null` before counting — if this fails, emit a FAIL assertion explicitly. Add a loop that runs Test 10 ten times to catch timing-dependent failures that pass on a single run.

**I4. Validate severity at write time (addresses C6)**

A four-line `case` guard before the `jq -n -c` call prevents invalid severity values from entering the JSONL file. This is cheap, makes the contract self-enforcing, and makes synthesis logic simpler (it can trust severity is always `blocking` or `notable`).

---

--- VERDICT ---
STATUS: fail
FILES: 5 changed
FINDINGS: 8 (P0: 2, P1: 3, P2: 3)
SUMMARY: The plan introduces concurrent JSONL appends without synchronisation; two P0 issues (non-atomic appends, mid-write `jq -s` parse failure) can silently drop or corrupt findings in every parallel review run. The integration test does not reproduce the failure class it claims to validate. Fix with `flock`-serialised writes and a copy-then-read pattern before this ships.
---

<!-- flux-drive:complete -->
