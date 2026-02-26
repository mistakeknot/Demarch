# Security Review: Interspect Approve-Override Feature

**File reviewed:** `/home/mk/projects/Demarch/os/clavain/hooks/lib-interspect.sh` (lines ~1158-1400)
**Schema reviewed:** `/home/mk/projects/Demarch/os/clavain/config/routing-overrides.schema.json`
**Date:** 2026-02-23
**Risk classification:** Medium (new write path into git history and SQLite; trust boundary is local developer session)

---

## Threat Model

**Deployment context:** Local developer tooling. Clavain runs inside a Claude Code session on a developer workstation. There is no network-facing exposure, no multi-tenant environment, and no external user input to these functions.

**Untrusted inputs:**
- `$1` (agent name): comes from a skill command argument typed or selected by the developer, or from a skill's own constructed string when it calls `_interspect_approve_override` programmatically. Not from the network.
- `FLUX_ROUTING_OVERRIDES_PATH` env var: set by the user or CI environment before sourcing the library.
- `confidence.json` and `protected-paths.json`: local config files, writable by the repo owner.
- `baseline_json` numeric fields: computed internally from a SQLite query over local evidence data.

**What is NOT in scope:** network attacker, untrusted third-party plugins calling these functions, multi-user privilege separation (single-developer tool).

**What IS in scope:** prompt injection via a maliciously crafted agent name leaking into git commit messages or SQL; path traversal via `FLUX_ROUTING_OVERRIDES_PATH`; the `--no-verify` bypass and its operational risk; residual SQL injection through un-escaped values.

---

## Findings

### Finding 1 — Medium: `filepath` inserted into SQL without `_interspect_sql_escape` (two locations)

**Location:** `lib-interspect.sh` lines 1350-1351 and 1388-1389 (inside `_interspect_approve_override_locked`).

**Code:**
```bash
sqlite3 "$db" "INSERT INTO modifications (..., target_file, ...) \
    VALUES ('${escaped_agent}', '${ts}', 'persistent', 'routing', '${filepath}', '${commit_sha}', ...)"

sqlite3 "$db" "INSERT INTO canary (file, ...) \
    VALUES ('${filepath}', '${commit_sha}', ...)"
```

`filepath` is the value of `FLUX_ROUTING_OVERRIDES_PATH` (defaulting to `.claude/routing-overrides.json`). It passes through `_interspect_validate_overrides_path` (which rejects absolute paths and `..` traversal) and `_interspect_validate_target` (allow-list check), but it is **never passed through `_interspect_sql_escape`** before being interpolated into SQL strings.

The same pattern exists in the parallel `_interspect_apply_override_locked` function at lines 963-964 and 1002-1003.

**Exploitability:** Low in practice, because `_interspect_validate_overrides_path` already restricts `filepath` to relative paths with no `..` component, and `_interspect_validate_target` checks the allow-list. The allow-list is loaded from a local JSON file. A path value like `.claude/routing-overrides.json` has no SQL-special characters. However, if the allow-list ever contains a path with a single quote (e.g., a project directory named `user's-project/.claude/routing-overrides.json`), this would break the SQL statement. The `commit_sha` value from `git rev-parse HEAD` is also un-escaped — it is always 40 hex characters in practice, so the risk is nil for that field.

**Mitigation:** Apply `_interspect_sql_escape` to `filepath` before interpolation. This is consistent with the pattern used for every other user-controlled field in the same function:
```bash
local escaped_filepath
escaped_filepath=$(_interspect_sql_escape "$filepath")
# then use ${escaped_filepath} in both INSERT statements
```

---

### Finding 2 — Low: Baseline numeric fields from jq interpolated directly into SQL without numeric validation

**Location:** `lib-interspect.sh` lines 1358-1385, specifically:
```bash
b_override_rate=$(echo "$baseline_json" | jq -r '.override_rate')
b_fp_rate=$(echo "$baseline_json" | jq -r '.fp_rate')
b_finding_density=$(echo "$baseline_json" | jq -r '.finding_density')
# ...
baseline_values="${b_override_rate}, ${b_fp_rate}, ${b_finding_density}, '${escaped_bwindow}'"
# inserted directly: VALUES (..., ${baseline_values}, 'active')
```

`baseline_json` is computed by `_interspect_compute_canary_baseline` from a chain of SQLite queries over local evidence. The numeric values come from `awk` `printf "%.4f"` formatting, which always produces a numeric string. Under normal operation these fields are safe. However, if `baseline_json` were somehow corrupted (e.g., by a hand-edited evidence DB, or a future code path that computes it differently), unvalidated content would flow into SQL.

**Exploitability:** Negligible. The entire flow is internal: SQLite aggregate → awk → jq output. No external input reaches these fields. The `b_override_rate == "NULL"` guard already handles the null case. The existing code comment at line 1549 acknowledges this concern for `escaped_ts` but not for the rate fields.

**Mitigation:** Add a guard after extracting each field:
```bash
[[ "$b_override_rate" =~ ^-?[0-9]+(\.[0-9]+)?$ ]] || b_override_rate="NULL"
[[ "$b_fp_rate" =~ ^-?[0-9]+(\.[0-9]+)?$ ]] || b_fp_rate="NULL"
[[ "$b_finding_density" =~ ^-?[0-9]+(\.[0-9]+)?$ ]] || b_finding_density="NULL"
```
This collapses the four-field null branch correctly and mirrors the `_interspect_clamp_int` pattern already used for canary config fields.

---

### Finding 3 — Low: `_interspect_validate_overrides_path` does not reject trailing `..` without slash

**Location:** `lib-interspect.sh` lines 650-661:
```bash
_interspect_validate_overrides_path() {
    local filepath="$1"
    if [[ "$filepath" == /* ]]; then ...  # reject absolute
    if [[ "$filepath" == *../* ]] || [[ "$filepath" == */../* ]] || [[ "$filepath" == .. ]]; then
        # reject
    fi
    return 0
}
```

The check rejects `../foo`, `foo/../bar`, and exactly `..`. It does NOT reject `foo/..` (traversal at the end with no trailing slash) or `foo/bar/..`. In practice this matters only if `fullpath="${root}/${filepath}"` resolves to a path outside the repo root, which it would for `foo/..`.

**Exploitability:** Very low. Even if `filepath` is `foo/..`, after `mkdir -p "$(dirname "$fullpath")"` and `mv "$tmpfile" "$fullpath"`, the resolved path would be `${root}/foo/..` which `dirname` would reduce to `${root}` — writing to the repo root directory instead of a file. The `jq '.'` validation and `mv` would fail in a way that does not result in data loss or privilege escalation. The allow-list check via `_interspect_validate_target` would also reject any path not in the manifest.

**Mitigation:** Add `[[ "$filepath" == */.." ]]` to the rejection checks, or normalize the path after construction:
```bash
if [[ "$filepath" == *.. ]]; then
    echo "ERROR: FLUX_ROUTING_OVERRIDES_PATH must not end with '..' (got: ${filepath})" >&2
    return 1
fi
```

---

### Finding 4 — Informational: `--no-verify` on git commit bypasses pre-commit hooks

**Location:** `lib-interspect.sh` line 1333:
```bash
git -C "$root" commit --no-verify -F "$commit_msg_file"
```

The same pattern is used in `_interspect_apply_override_locked` (line ~870) and the revert path.

**Context:** This is an explicit design decision, noted in the surrounding comment ("Git add + commit"). The reasoning is that Interspect is an internal automation tool, not user-supplied code, and that pre-commit hooks would be triggered recursively or interfere with the automated commit flow.

**Security impact:** Pre-commit hooks in this repo include `hooks/auto-stop-actions.sh`, `hooks/interspect-evidence.sh`, and other Interspect hooks themselves. Bypassing them means:
1. Interspect's own evidence hooks do not fire on Interspect's own commits — which is correct behavior, avoiding recursive instrumentation.
2. Any lint or secret-scanning hooks configured for the project are also bypassed for these commits.
3. If a secret were to be introduced into `routing-overrides.json` (e.g., via a crafted reason string), the bypass would prevent detection by secret-scanning pre-commit hooks.

**The `_interspect_sanitize` and `_interspect_redact_secrets` functions are applied to evidence `context` fields before DB insertion**, but the `reason` field in the JSON file is NOT passed through `_interspect_sanitize` in the approve path. The approve path hardcodes the commit message to a safe template (`"Promoted from proposal to active exclusion"`) and the commit message file is written with `printf` using positional arguments — safe. The JSON `reason` field is carried forward from the existing `propose` entry (which was written by `_interspect_apply_propose_locked`). That function does apply `_interspect_sql_escape` to the reason before DB insertion, but it writes `reason` to the JSON file via `jq --arg reason "$reason"` which is injection-safe for JSON.

**Residual risk:** The `--no-verify` flag is the right choice here to prevent recursion, but it does skip any project-level secret scanners. Since the commit message is hardcoded and `reason` passes through `jq --arg` (safe), the direct secret leakage risk is low. The residual risk is a policy gap: if this project adds a secret-scanning pre-commit hook in the future, these commits will silently bypass it.

**Mitigation (operational):** Document in the function's header comment that `--no-verify` is intentional to prevent recursive hook firing, and note that secret sanitization is applied to DB content but not to the JSON `reason` field before git staging. Consider applying `_interspect_redact_secrets` to the `reason` field in `_interspect_apply_propose_locked` before writing it to JSON — that is the write point, not the approve path (approve only promotes; it does not change `reason`).

---

### Finding 5 — Low: Path traversal protection has a known gap in `_interspect_validate_overrides_path`

**Location:** `lib-interspect.sh` lines 650-661 and line 1177.

The function correctly rejects absolute paths and `..` in the middle or at the start of a path. However, two additional edge cases are not handled:

1. A path consisting solely of whitespace would pass the check and produce a confusing `fullpath` like `${root}/ `.
2. A path with embedded null bytes (uncommon in bash but possible if set from an environment variable containing nulls) would behave unpredictably.

Neither is exploitable in this local tooling context. The allow-list check provides a second layer. These are theoretical hardening opportunities.

---

### Finding 6 — Informational: Trust boundary for `_interspect_approve_override` is implicit

**Location:** The function has no caller authentication. Any code that sources `lib-interspect.sh` can call `_interspect_approve_override` with an arbitrary agent name.

**Current callers:**
- `/home/mk/projects/Demarch/os/clavain/commands/interspect-approve.md` (line 86, 152) — a Claude Code skill invoked by the developer
- `/home/mk/projects/Demarch/os/clavain/commands/interspect-propose.md` (line 114) — another skill

**Trust model:** Both callers are skills authored in the same repository, run inside Claude Code sessions. The developer must explicitly invoke `/interspect:approve` or `/interspect:propose`. There is no path for an external agent or automated hook to call approve autonomously — the hooks that fire automatically are `interspect-evidence.sh` and `interspect-session.sh`, which call evidence insertion functions, not `_interspect_approve_override`.

**Concern:** The `interspect-approve.md` skill has a batch-approve path that calls `_interspect_approve_override "$agent"` for each agent returned from a multi-select prompt. The `$agent` value comes from parsing `routing-overrides.json` via `jq -c '[.overrides[] | select(.action == "propose")]'` — the `.agent` field. If the JSON file were modified by an untrusted source to inject a crafted agent name that passes `_interspect_validate_agent_name` (which requires `^fd-[a-z][a-z0-9-]*$`), it would pass validation. The regex is strict enough that no shell metacharacter, SQL special character, or path separator can appear in a valid agent name. This is the strongest injection defense in the system.

**Conclusion:** The trust boundary is implicit but adequate because `_interspect_validate_agent_name` enforces a strict allowlist regex. The risk of AGENTS.md/CLAUDE.md prompt injection is separately governed by the project's stated `## Security: AGENTS.md Trust Boundary` policy.

---

### Finding 7 — Low: TOCTOU window between pre-check and flock acquisition

**Location:** `lib-interspect.sh` lines 1190-1204 (pre-check before `_interspect_flock_git`), then line 1265-1272 (re-check inside flock).

The code correctly performs a second check inside the flock for the "already excluded" race condition (returns exit code 2). This handles the TOCTOU correctly.

However, the file existence check at line 1202 (`[[ -f "$fullpath" ]]` before flock) and the corresponding check at line 1258 inside flock both exist. If the file is deleted between the two checks, the inside-flock check at line 1261-1262 will error correctly. No data loss or security concern — this is already correctly handled.

---

### Finding 8 — Informational: Schema `additionalProperties: true` allows schema drift without detection

**Location:** `/home/mk/projects/Demarch/os/clavain/config/routing-overrides.schema.json` lines 8 and 35:
```json
"additionalProperties": true
```

Set at both the root object and the `override` item level. This means any future code that writes extra fields (e.g., a future `approved_by`, `session_id`, or debug fields) will pass schema validation silently. Since `routing-overrides.json` is committed to git and read by flux-drive, unexpected extra fields could cause flux-drive parsing failures in future versions if it expects strict schema compliance.

The `scope` and `canary_snapshot` definitions use `"additionalProperties": false`, which is stricter. The inconsistency suggests the top-level and `override` definitions were intentionally left open for forward compatibility.

**Recommendation:** This is not a security issue but a schema governance gap. Consider adding a `$comment` or `description` note on the `additionalProperties: true` setting for `override` explaining which fields are reserved for future use, to prevent accidental field collisions. The `approved` field added in this change is correctly defined under the `override` properties.

---

### Finding 9 — Medium: `confidence` variable inserted into SQL without explicit numeric validation

**Location:** `lib-interspect.sh` lines 1282-1286 and 1350-1351:
```bash
if (( total > 0 )); then
    confidence=$(awk -v w="$wrong" -v t="$total" 'BEGIN {printf "%.2f", w/t}')
else
    confidence="1.0"
fi
# later:
sqlite3 "$db" "INSERT INTO modifications (..., confidence, ...) VALUES (..., ${confidence}, ...)"
```

`confidence` is not quoted in the SQL. `total` and `wrong` come from `sqlite3 "$db" "SELECT COUNT(*) FROM evidence WHERE source = '${escaped_agent}' ..."`. The `$escaped_agent` is SQL-escaped, but the COUNT(*) result — an integer string from SQLite — is assigned to `total` and `wrong`. These are then passed as `-v` arguments to `awk`, which is safe (awk `-v` does not allow injection). The awk output is always a `%.2f`-formatted float.

**Risk:** If `total` or `wrong` were somehow non-numeric (e.g., SQLite prints an error message to stdout instead of the count), `awk` might produce `0` or a NaN, which could corrupt the SQL. In practice, `sqlite3` outputs errors to stderr not stdout, so `total` and `wrong` will always be digit strings or empty. An empty string passed to `(( total > 0 ))` is treated as 0, falling to `confidence="1.0"`. This path is safe.

**Mitigation (hardening):** Add explicit numeric guards on `total` and `wrong`:
```bash
[[ "$total" =~ ^[0-9]+$ ]] || total=0
[[ "$wrong" =~ ^[0-9]+$ ]] || wrong=0
```
This eliminates any ambiguity and is defensive against future SQLite behavior changes.

---

## Deployment and Operational Review

### Rollback Assessment

The approve operation is **partially reversible**:

1. **JSON file change:** Reversible via `/interspect:revert <agent>`, which reads the existing `exclude` entry, downgrades it back to `propose`, and commits. The revert path exists at line 1405 onwards.
2. **Git commit with `--no-verify`:** The commit becomes part of git history. The revert creates a new commit; it does not squash or amend the approve commit. Under incident pressure, `git revert HEAD` or the `/interspect:revert` skill both work.
3. **SQLite modifications record:** The `modifications` table INSERT at line 1350-1351 has no corresponding DELETE in the revert path. This is documented as intentional — DB records are append-only audit trail.
4. **SQLite canary record:** The `canary` table INSERT is also append-only. Revert sets `status = 'applied-unmonitored'` on the modification but does not delete the canary row. This is correct — the canary row is historical.

**Pre-deploy invariant:** A `propose` entry must exist for the agent. Enforced by the pre-check (line 1192-1203) and the inside-flock re-check (line 1266-1272).

**Rollback feasibility:** High. The revert skill is documented and callable under incident pressure. The git history is clean (no amend, no force-push). The DB records are non-destructive. Confidence: high for code rollback; medium for DB (audit trail divergence is harmless but irreversible).

---

### Summary Table

| # | Finding | Severity | Exploitability | Recommended Action |
|---|---------|----------|----------------|-------------------|
| 1 | `filepath` unescaped in SQL INSERT (modifications + canary) | Medium | Low (constrained by allow-list) | Apply `_interspect_sql_escape` to `filepath` before SQL interpolation |
| 2 | Baseline numeric floats unvalidated before SQL interpolation | Low | Negligible (internal data path) | Add `=~ ^-?[0-9]+(\.[0-9]+)?$` guards on `b_override_rate`, `b_fp_rate`, `b_finding_density` |
| 3 | `validate_overrides_path` misses trailing `..` pattern | Low | Very low (allow-list blocks it) | Add `[[ "$filepath" == *.. ]]` rejection clause |
| 4 | `--no-verify` bypasses project secret scanners | Info/Policy | Low (commit message is hardcoded template) | Document intent; consider applying `_interspect_redact_secrets` to `reason` at propose-write time |
| 5 | `validate_overrides_path` does not reject whitespace-only paths | Info | Negligible | Hardening only; not blocking |
| 6 | No caller authentication on `_interspect_approve_override` | Info | None (agent name regex is strict; skills are local) | No action needed; document trust assumption |
| 7 | TOCTOU between pre-check and flock | Info | None (inside-flock re-check is correct) | Already handled correctly; no action |
| 8 | Schema uses `additionalProperties: true` inconsistently | Info | None | Add `$comment` on intended fields; not a security issue |
| 9 | `confidence` SQL interpolation — `total`/`wrong` not guarded for non-numeric | Low | Negligible (SQLite COUNT(*) always numeric) | Add `=~ ^[0-9]+$` guards on `total` and `wrong` before awk call |

---

## Go/No-Go Assessment

**Go with mitigations.** No finding is blocking for a local developer tooling deployment. The highest-priority fix is Finding 1 (apply `_interspect_sql_escape` to `filepath` in the two INSERT statements), which is a one-line fix per statement and eliminates a latent SQL injection vector that would become exploitable if the allow-list ever includes a path with a single-quote character.

Findings 2 and 9 are defensive hardening that are worth doing given they follow the established pattern in the same file. All remaining findings are informational and can be tracked as follow-up improvements.

The `--no-verify` flag (Finding 4) is the correct choice for preventing recursive hook invocation. The commit message template and the existing sanitization on `reason` (written at propose time via `jq --arg`) mean no secret leakage path exists in the current implementation.
