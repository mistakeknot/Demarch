# Safety Review: Interspect F2 — Pattern Detection + Propose Flow

**Plan:** `docs/plans/2026-02-23-interspect-pattern-detection-propose-flow.md`
**Existing lib:** `os/clavain/hooks/lib-interspect.sh`
**Reviewer:** fd-safety (Flux-drive Safety Reviewer)
**Date:** 2026-02-23

---

## Threat Model

**Deployment context:** Local developer tooling. Runs as the developer's own Unix user inside the Clavain hook pipeline. No network exposure. Not a service endpoint. No external callers.

**Trusted inputs:** Agent names emitted by `_interspect_get_classified_patterns`, which originate from `sqlite3` rows normalized by the existing `_interspect_normalize_agent_name` function.

**Untrusted inputs:** `FLUX_ROUTING_OVERRIDES_PATH` environment variable. The `reason` argument passed to `_interspect_apply_propose`. `evidence_ids` JSON passed from callers. Any data stored in the SQLite evidence table that originated from user-facing hook events.

**Credentials:** None processed or generated in this plan. No secrets touched.

**Deployment path:** Library function in a sourced Bash file. Committed to git by the function itself via `git commit --no-verify -F <tmpfile>`. No external deploy step.

**Change risk classification: Medium.** No new trust boundary is crossed (local only, same user), but the `_interspect_apply_propose` function makes irreversible git commits that modify a file read by downstream flux-drive triage tools. Rollback requires an explicit `git revert`. The `--no-verify` flag on the commit is a standing governance bypass.

---

## Findings

### Finding 1 — HIGH: SQL injection via unescaped `source` column in `_interspect_get_routing_eligible`

**Location:** Plan Task 1, Step 3 — `_interspect_get_routing_eligible()` implementation, lines:

```bash
total=$(sqlite3 "$db" "SELECT COUNT(*) FROM evidence WHERE source = '${escaped}' AND event = 'override';")
wrong=$(sqlite3 "$db" "SELECT COUNT(*) FROM evidence WHERE source = '${escaped}' AND event = 'override' AND override_reason = 'agent_wrong';")
```

**The problem:** `$escaped` is derived from `$src`, which arrives from `_interspect_get_classified_patterns`. That function normalizes `source` values inside SQLite using `SUBSTR()`, so the normalized value is not stored — it is produced on the fly in the query result. The result is read into `$src` via a shell read loop and then re-escaped with `_interspect_sql_escape`. Escaping is applied, so this path is guarded. However, the guard has a subtle gap: `_interspect_validate_agent_name` is called before the escape, and its regex `^fd-[a-z][a-z0-9-]*$` only allows lowercase letters, digits, and hyphens — making injection characters impossible by the time `_interspect_sql_escape` sees the value. The escape is thus redundant but harmless. **The actual risk** is that `_interspect_get_routing_eligible` calls `_interspect_is_routing_eligible` on the same `$src`, and `_interspect_is_routing_eligible` performs its own SQL queries using `$escaped` derived from the passed agent name. That function contains a multi-source OR clause (line 502-503 in existing lib):

```bash
total=$(sqlite3 "$db" "SELECT COUNT(*) FROM evidence WHERE (source = '${escaped}' OR source = 'interflux:${escaped}' OR source = 'interflux:review:${escaped}') AND event = 'override';")
```

The string `'interflux:${escaped}'` concatenates a prefix to the escaped value and then embeds the result in a single-quoted SQL string. If `_interspect_sql_escape` were ever relaxed to allow colons (e.g., for legitimate interflux prefixes), and validation were also loosened, this concatenation pattern would become injection-susceptible. Currently safe because validation blocks all non-`fd-[a-z0-9-]` characters, but the implementation pattern is fragile — the defense is entirely in the validation regex, not in parameterized queries.

**Impact:** Low exploitability now given strict validation. High blast radius if validation is relaxed in a future change without updating the SQL patterns. The pattern trains contributors to write string-interpolated SQL queries.

**Mitigation:** Prefer SQLite CLI's `-cmd "PRAGMA query_only=1"` and parameterized queries. For this library specifically, the `_interspect_is_routing_eligible` OR-clause should use a `WITH vars AS (SELECT ? as agent)` approach or verify that the `interflux:` prefix concatenation is explicitly documented as safe-only-because-of-validation. Add a comment at the SQL site.

---

### Finding 2 — HIGH: `_interspect_apply_propose_locked` receives `reason` and `evidence_ids` as positional shell arguments through `_interspect_flock_git`

**Location:** Plan Task 3, Step 3 — `_interspect_apply_propose()`, the `_interspect_flock_git` invocation:

```bash
flock_output=$(_interspect_flock_git _interspect_apply_propose_locked \
    "$root" "$filepath" "$fullpath" "$agent" "$reason" \
    "$evidence_ids" "$created_by" "$commit_msg_file")
```

**The problem:** `_interspect_flock_git` calls its first argument as a shell command with all remaining arguments passed positionally via `"$@"`:

```bash
# lib-interspect.sh line 1444
"$@"
```

This means `$reason` and `$evidence_ids` are passed as positional arguments to `_interspect_apply_propose_locked`. `$reason` is a free-text string. If `$reason` contains a value like `"--help"` or a flag resembling a bash function argument, it is passed as `$5` inside the locked function. This is safe at the locked function boundary because it is received with `local reason="$5"` — positional assignment is injection-safe.

However, `$reason` is later embedded directly into a `printf` call that writes the git commit message:

```bash
printf '[interspect] Propose excluding %s from flux-drive triage\n\nReason: %s\nEvidence: %s\nCreated-by: %s\n' \
    "$agent" "$reason" "$evidence_ids" "$created_by" > "$commit_msg_file"
```

This is safe: `printf` with `%s` does not interpret `$reason` as format string. The result is written to a temp file and passed to `git commit -F`. No injection into git. **However**, if `$reason` contains newlines, the commit message body will contain those newlines verbatim. Commit message parsers (e.g., `git log --oneline`) will show only the first line. The reason multi-line content reaches git is because the plan has no sanitization step for `$reason` before commit message construction. The plan's `$reason` argument is described as coming from the `_interspect_get_routing_eligible` output, so it is system-generated — but callers like `/interspect:propose` may accept user input for `reason`.

**Impact:** No code execution risk. Multi-line `$reason` could produce confusing git commit messages with apparently empty bodies or misleading diffs in `git log`. Low severity operationally but worth controlling because commit messages are audited for routing decisions.

**Mitigation:** Strip newlines and control characters from `$reason` before writing the commit message. Apply `_interspect_sql_escape` or a purpose-built `_interspect_sanitize_reason` that collapses whitespace and truncates. The existing `_interspect_sanitize` function is already available and strips control characters; it should be called on `$reason` in `_interspect_apply_propose` before constructing `$commit_msg_file`.

---

### Finding 3 — MEDIUM: `ALREADY_EXISTS` sentinel on stdout conflates skip with success; exploitable by crafted agent name

**Location:** Plan Task 3, Step 3 — `_interspect_apply_propose_locked`:

```bash
echo "ALREADY_EXISTS"
return 0
```

And in `_interspect_apply_propose`:

```bash
local commit_sha
commit_sha=$(echo "$flock_output" | tail -1)
echo "SUCCESS: Proposed excluding ${agent}. Commit: ${commit_sha}"
```

**The problem:** When a dedup skip occurs, the locked function outputs `ALREADY_EXISTS` to stdout with `return 0`. The outer function captures `flock_output`, checks exit code (0 = success), then reads the last line as the commit SHA and prints:

```
SUCCESS: Proposed excluding fd-game-design. Commit: ALREADY_EXISTS
```

This is misleading: no commit was created, but the function returns 0 and prints "SUCCESS" with a fake commit SHA. The test `"apply_propose skips if override already exists"` only checks that `$output` contains "already exists" — but the current implementation prints that string to `stderr`, while `SUCCESS:` goes to `stdout`. Under `bats run`, `$output` captures both. In production use, callers parsing stdout for a commit SHA will receive `ALREADY_EXISTS` as a value.

**Exploitability of the name collision:** The prompt asks whether an agent named `fd-already-exists` could be confused with the marker. The marker is `ALREADY_EXISTS` (uppercase, no hyphens). The agent name regex requires `fd-[a-z][a-z0-9-]*`, so `ALREADY_EXISTS` cannot be a valid agent name. The collision is impossible under current validation. However, the design still has the structural problem that a non-SHA sentinel rides on the same channel as a real commit SHA. This is a latent protocol ambiguity.

**Impact:** Callers (including future `/interspect:propose` skill code) that check `commit_sha` validity will silently accept `ALREADY_EXISTS` as a SHA, which will fail `git show ALREADY_EXISTS` or similar downstream operations. No security impact, but operational correctness risk.

**Mitigation:** Return a distinct exit code for the skip case (e.g., exit 2) and handle it explicitly in the outer function. Or emit the `ALREADY_EXISTS` marker to stderr only and return 0 with an empty stdout. The outer function should detect the empty-SHA case and emit "INFO: already overridden" rather than "SUCCESS". Update the tests to verify stdout is empty on skip and exit code is 2.

---

### Finding 4 — MEDIUM: `FLUX_ROUTING_OVERRIDES_PATH` validation has a traversal bypass for paths ending in `..`

**Location:** `os/clavain/hooks/lib-interspect.sh` lines 522-533, `_interspect_validate_overrides_path`:

```bash
if [[ "$filepath" == *../* ]] || [[ "$filepath" == */../* ]] || [[ "$filepath" == .. ]]; then
```

**The problem:** This regex does not catch `foo/..` (trailing `..` without trailing slash). The path `foo/..` resolves to the parent of `foo`, which is the git root. An attacker who can set `FLUX_ROUTING_OVERRIDES_PATH=foo/..` would cause `fullpath="${root}/foo/.."` which resolves to `$root`. Subsequent `jq '.' > "${fullpath}.tmp.$$"` would write a file named `$root/.tmp.$$`, and `mv` would rename it to `$root/..` — which on Linux resolves to the parent directory and fails `mv` with "is a directory". So in practice the write would fail before causing harm, but the `mkdir -p "$(dirname "$fullpath")"` call would attempt to `mkdir -p "$root/foo"` which is benign. The `_interspect_validate_target` check is the second layer of defense and would reject any path not in the allow-list.

The `_interspect_validate_target` function (lines 280-305) checks against `_INTERSPECT_PROTECTED_PATHS` and `_INTERSPECT_ALLOW_LIST`. If `.claude/routing-overrides.json` is in the allow-list but `foo/..` is not, the traversal is stopped at the target validation step. However, this means the traversal defense is provided by the allow-list, not by the path validator — and the path validator has a documented gap.

**Impact:** Low in practice due to allow-list backstop. Medium as documentation: the path validator should be the primary defense and it has a known incomplete pattern.

**Mitigation:** Add `|| [[ "$filepath" == *.. ]]` (trailing `..` without slash) to the traversal check in `_interspect_validate_overrides_path`. Also add a check for paths containing `/.` (hidden components other than `../`) if those are unintended. This makes the primary validator complete and the allow-list a secondary defense in depth.

---

### Finding 5 — MEDIUM: `_interspect_get_overlay_eligible` uses associative array accumulation with no validation of `$ec`, `$sc`, `$pc` as integers

**Location:** Plan Task 2, Step 3 — `_interspect_get_overlay_eligible()`:

```bash
agent_total[$src]=$(( ${agent_total[$src]:-0} + ec ))
```

**The problem:** `$ec`, `$sc`, `$pc` come from the `_interspect_get_classified_patterns` output, which reads them from SQLite `COUNT(*)` results. SQLite `COUNT(*)` always returns a non-negative integer, so in practice these values are safe. However, the shell arithmetic `$(( ... + ec ))` does not validate that `$ec` is numeric. In Bash, `$((expr))` with a non-numeric operand silently evaluates to 0 in some shells and raises an error in strict-mode shells. With `set -e` (which the locked functions use), a non-numeric `ec` value would cause the function to exit unexpectedly.

The deeper issue: `_interspect_get_overlay_eligible` does NOT call `set -e`, so arithmetic errors silently produce 0. This could suppress a reporting row rather than corrupting data, so the blast radius is low.

**Impact:** Silent suppression of a pattern row if `_interspect_get_classified_patterns` ever emits a non-numeric count (e.g., due to SQLite error messages interleaved with output). Low severity.

**Mitigation:** Validate that `ec`, `sc`, `pc` match `[0-9]+` before arithmetic. Or use `sqlite3` with explicit `-noheader -csv` flags and validate the separator is `|` not a tab. The existing `_interspect_get_classified_patterns` uses `-separator '|'` but does not set `-noheader`, so a future SQLite warning on stderr could not interleave — stdout is clean. Document this assumption.

---

### Finding 6 — MEDIUM: `git commit --no-verify` bypasses all pre-commit hooks, including security hooks

**Location:** Plan Task 3, Step 3 — `_interspect_apply_propose_locked` line:

```bash
git commit --no-verify -F "$commit_msg_file"
```

This is identical to the existing pattern in `_interspect_apply_override_locked` (line 815 of lib).

**Context:** This is a local developer tool committing to the developer's own repo. `--no-verify` prevents infinite recursion when Clavain hooks trigger interspect, which in turn would trigger Clavain hooks. The existing lib uses this pattern and it is documented implicitly by the architecture.

**Risk:** Any pre-commit hook performing secret scanning, lint, or policy checks is bypassed for these automated commits. If a future version of `$reason` or a `confidence.json` config file contains a credential and is written to `routing-overrides.json`, that commit would bypass secret scanning.

**Impact:** Residual risk dependent on operational discipline (no secrets in reason strings or evidence IDs). The `_interspect_redact_secrets` and `_interspect_sanitize` functions exist and would eliminate known credential patterns if applied to `$reason` before commit. The plan does not call these on `$reason`.

**Mitigation:** Call `_interspect_sanitize "$reason"` in `_interspect_apply_propose` before constructing the commit message. This applies the existing redaction pipeline and eliminates the credential-in-commit-message risk. This also addresses Finding 2 (newline stripping). The `evidence_ids` argument is already validated as a JSON array by `jq`; its values should also be subject to length limits to prevent commit message bloat.

---

### Finding 7 — LOW: Cross-cutting agent list is hardcoded in `_interspect_is_cross_cutting`

**Location:** Plan Task 4, Step 3:

```bash
_interspect_is_cross_cutting() {
    local agent="$1"
    case "$agent" in
        fd-architecture|fd-quality|fd-safety|fd-correctness) return 0 ;;
        *) return 1 ;;
    esac
}
```

**The problem:** Adding a new cross-cutting agent requires editing `lib-interspect.sh` directly. If the list is not updated when a new cross-cutting agent is deployed, that agent loses its extra safety gate in the propose flow — it would be eligible for exclusion proposals without the additional review step intended for structural-coverage agents.

**Impact:** No security risk. Operational correctness risk if fleet evolves without updating this function.

**Mitigation:** Source the list from `confidence.json` under a `cross_cutting_agents` key (already loaded by `_interspect_load_confidence`). The `_interspect_is_cross_cutting` function would then read `_INTERSPECT_CROSS_CUTTING_AGENTS` (an array populated from the config). This makes the list maintainable without code changes and keeps it co-located with other confidence thresholds. Default to the current four if the key is absent.

---

### Finding 8 — LOW: `tmpfile` uses PID suffix but not a temp directory — collision possible during parallel runs

**Location:** Plan Task 3, Step 3 — `_interspect_apply_propose_locked`:

```bash
local tmpfile="${fullpath}.tmp.$$"
echo "$merged" | jq '.' > "$tmpfile"
```

**The problem:** `$$` is the PID of the parent shell process. Inside the `_interspect_flock_git` subshell, `$$` is the parent's PID (not the subshell's PID), which is stable across calls in the same session. Two concurrent calls — blocked by flock — would serialize correctly, but if flock fails to acquire and two processes proceed (e.g., due to a stale lock file on an NFS mount), both would write to the same `tmpfile` path, then race on `mv`. This is the same pattern used in `_interspect_apply_override_locked` (line 802) so the risk profile is unchanged by this plan.

**Impact:** Requires flock to fail, which requires an adversarial or broken filesystem. Extremely low in practice.

**Mitigation:** Use `mktemp` for the tmpfile (same directory, random suffix) instead of `$$.tmp`. This eliminates the collision entirely. Example: `local tmpfile; tmpfile=$(mktemp "${fullpath}.XXXXXX")`. The `mktemp` pattern is already used for `$commit_msg_file` in the outer function, demonstrating the convention is known.

---

### Finding 9 — LOW: `_interspect_get_routing_eligible` calls `_interspect_is_routing_eligible` per agent, which itself queries the blacklist per call — O(n) SQLite queries in a loop

**Location:** Plan Task 1, Step 3:

```bash
eligible_result=$(_interspect_is_routing_eligible "$src")
```

**Context:** `_interspect_is_routing_eligible` runs two `sqlite3` queries (blacklist check, then count queries) plus the earlier calls to `_interspect_get_classified_patterns` which runs one batch query. For a typical fleet of 7-16 agents, this is at most ~48 SQLite calls — not a performance concern for interactive tooling.

**Impact:** No security issue. Noted as a latent scalability issue if the agent fleet grows significantly or if the function is called in a CI hot path.

**Mitigation:** Not required for this plan. Document the per-agent query cost in the function header if scaling becomes a concern.

---

## Non-Issues (Explicitly Cleared)

**SQL injection via `_interspect_sql_escape` consistency:** The plan consistently applies `_interspect_sql_escape` before every SQLite interpolation and also calls `_interspect_validate_agent_name` first. The escape is applied correctly and consistently in all three SQL query sites in `_interspect_get_routing_eligible`. No gap found.

**`git -F <tempfile>` for commit message:** Using `-F` with a temp file is the correct injection-safe pattern. The alternative (`-m "$reason"`) would allow shell expansion and newline injection. The existing lib uses this pattern correctly and the new `_interspect_apply_propose` follows it.

**`jq --arg` for JSON construction:** All JSON object construction in `_interspect_apply_propose_locked` uses `jq -n --arg` and `--argjson` rather than string interpolation. This is correct and eliminates JSON injection.

**`_interspect_validate_target` allow-list:** The allow-list provides a hard backstop against writing to arbitrary paths. Combined with `_interspect_validate_overrides_path`, the defense-in-depth for path traversal is adequate for the local threat model, modulo the gap described in Finding 4.

**Network exposure:** None. All operations are local filesystem and local `sqlite3`. No ports, no sockets, no HTTP.

**Credential exposure:** The functions do not generate, store, or transmit credentials. The `_interspect_redact_secrets` pipeline exists and would catch common patterns if applied to `$reason` (see Finding 6 for the gap).

---

## Go / No-Go Recommendation

**Go with mitigations** for Findings 2, 3, and 6 before merging.

- Finding 2 and 6 share a single fix: call `_interspect_sanitize "$reason"` in `_interspect_apply_propose` before constructing `$commit_msg_file`. This strips control characters, redacts credentials, and eliminates newline injection in the commit message. Cost: 1 line.
- Finding 3: Change the `ALREADY_EXISTS` path to return exit code 2 from the locked function and handle it explicitly in the outer function. Print "INFO: override already exists, skipping" to stderr and return 0 with empty stdout. Cost: ~5 lines + test update.
- Finding 4: Add `|| [[ "$filepath" == *.. ]]` to `_interspect_validate_overrides_path`. Cost: 1 line in existing lib, not in the plan itself — note as a concurrent fix.

Findings 1, 5, 7, 8, 9 are low-severity and can be addressed in follow-on iterations or noted as technical debt. Finding 7 (hardcoded cross-cutting list) is the highest-priority of the low findings because it creates a maintenance trap for a future agent addition.

---

## Summary Table

| # | Severity | Area | One-line summary | Fix required before merge? |
|---|----------|------|-----------------|---------------------------|
| 1 | High (latent) | SQL | Fragile string-interpolated SQL — safe only due to validation regex | No — document the defense dependency |
| 2 | High | Shell | `$reason` not sanitized before commit message — newlines pass through | Yes |
| 3 | Medium | Protocol | `ALREADY_EXISTS` sentinel on stdout conflates skip with SHA | Yes |
| 4 | Medium | Path | Traversal validator misses trailing `..` without slash | No — allow-list backstops; fix in lib |
| 5 | Medium | Arithmetic | `$ec`/`$sc`/`$pc` not validated as integers before arithmetic | No |
| 6 | Medium | Credential | `--no-verify` bypasses secret scanning; `$reason` not redacted | Yes (via Finding 2 fix) |
| 7 | Low | Config | Cross-cutting list hardcoded; must update lib to add agents | No |
| 8 | Low | Concurrency | `tmpfile` uses PID not `mktemp` — same pattern as existing lib | No |
| 9 | Low | Performance | Per-agent SQLite queries in loop — not a current concern | No |
