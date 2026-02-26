# Safety Review: 2026-02-23-interspect-routing-overrides-schema.md

**Reviewer:** fd-safety (Flux-Drive Safety Reviewer)
**Plan:** `/home/mk/projects/Demarch/docs/plans/2026-02-23-interspect-routing-overrides-schema.md`
**Date:** 2026-02-23
**Risk Classification:** Medium (new schema enforcement, writer extension, LLM-interpreted routing logic — no direct auth or credential changes, but introduces a git-committed trust artefact that can suppress a security agent)

---

## Threat Model for This Plan

- **Deployment path:** Shell hooks (`lib-interspect.sh`) run locally inside Clavain agent sessions. Not network-facing.
- **Untrusted inputs:**
  - `routing-overrides.json` — committed to git, writable by any contributor
  - Agent name argument (`$agent`) — validated by `_interspect_validate_agent_name` before use in SQL
  - `evidence_ids` JSON array — validated as a JSON array but content is not further sanitized
  - `FLUX_ROUTING_OVERRIDES_PATH` env var — validated by `_interspect_validate_overrides_path`
  - `scope.file_patterns` glob strings — read from the JSON and interpreted by the LLM (no shell glob expansion)
  - `wrong` and `total` shell variables — computed from `sqlite3` COUNT(*) queries (always integers)
- **Credential surface:** None. No credentials are stored or processed in this plan.
- **Irreversible changes:** The writer commits `routing-overrides.json` to git. Revert is possible via `git revert`, but the plan's Task 2 adds confidence + canary snapshot fields; those are snapshots and do not affect DB state.

---

## Finding 1: awk Shell Interpolation — Concrete Risk Is Lower Than It Appears, But The Pattern Is Still Wrong

**Severity:** Low-Medium (exploitable only under specific conditions; merits a fix regardless)

**Location:** Plan Task 2, Step 3, the proposed code:

```bash
confidence=$(awk "BEGIN {printf \"%.2f\", ${wrong}/${total}}")
```

This interpolates the shell variables `$wrong` and `$total` directly into the awk program string using a double-quoted shell string. If either variable contained shell metacharacters or awk-meaningful content, this would allow injection into the awk program.

**Actual risk analysis:**

Both `$wrong` and `$total` are produced by `sqlite3 "$db" "SELECT COUNT(*) FROM ..."`. SQLite COUNT(*) always returns a non-negative integer (e.g., `0`, `5`, `42`). The output of `COUNT(*)` cannot contain letters, spaces, slashes, or any shell/awk metacharacters. The `_interspect_sql_escape` function is applied to `$agent` in the WHERE clause, so SQL injection into the COUNT query itself is blocked.

However, the plan does NOT explicitly sanitize `$wrong` and `$total` before passing them to awk. There is no shell-level integer guard such as `[[ "$wrong" =~ ^[0-9]+$ ]]`. If a future code path assigns these variables from a different source (e.g., a config file or a different query that allows richer output), the interpolation becomes dangerous.

**Concrete exploitability today:** Very low. SQLite COUNT(*) output is constrained to digits. But the pattern is wrong and will become a real risk the moment the variable assignment is refactored.

**Mitigation (required):** Either validate that both values are integers before the awk call, or use awk's `-v` flag which does not involve shell word expansion into the awk program body:

```bash
# Safe alternative — no shell interpolation into awk program
confidence=$(awk -v w="$wrong" -v t="$total" 'BEGIN {printf "%.2f", w/t}')
```

Using `-v` passes values as awk variables, not as program text. This eliminates the injection surface entirely regardless of what `$wrong` and `$total` contain. This fix is one line and has no downside. The plan should use this form.

**Additionally:** Add a guard before the awk call:

```bash
if ! [[ "$total" =~ ^[0-9]+$ && "$wrong" =~ ^[0-9]+$ ]]; then
    echo "ERROR: unexpected non-integer from COUNT query (total='${total}' wrong='${wrong}')" >&2
    confidence="1.0"
fi
```

This makes the defensive intent explicit and protects against future refactoring that changes how `$wrong`/`$total` are populated.

---

## Finding 2: SQL Injection in Confidence Computation — Correctly Mitigated, With One Gap

**Severity:** Low (existing mitigation is sound, but the plan's confidence computation bypasses the pre-flock name validation)

**Location:** Plan Task 2, Step 3 — confidence computation block inside `_interspect_apply_routing_override`, which runs BEFORE the flock call.

The plan proposes querying evidence BEFORE entering the flock:

```bash
escaped_agent_q=$(_interspect_sql_escape "$agent")
total=$(sqlite3 "$db" "SELECT COUNT(*) FROM evidence WHERE source = '${escaped_agent_q}' ...")
wrong=$(sqlite3 "$db" "SELECT COUNT(*) FROM evidence WHERE source = '${escaped_agent_q}' ...")
```

This is correct. `_interspect_sql_escape` escapes single quotes (doubling them), backslashes, and strips control characters. The agent name also passes through `_interspect_validate_agent_name` earlier in the function, which enforces `^fd-[a-z][a-z0-9-]*$`. A string matching that regex contains no characters that SQL injection requires (no quotes, no semicolons, no comment markers).

**Gap:** The confidence computation block is positioned in the plan AFTER the existing pre-flock validation section ("Pre-flock validation (fast-fail)") but the plan text does not call `_interspect_validate_agent_name` explicitly in the shown snippet — it says "existing validation unchanged". Implementors must verify that `_interspect_validate_agent_name` remains the FIRST operation in the function, and that the confidence computation block appears AFTER it, not before. The plan's ordering is ambiguous. This should be made explicit in the code comment.

**Mitigation:** The plan is safe as described IF the ordering is respected. Add a comment: `# Agent name validated above via _interspect_validate_agent_name — safe to use in SQL with _interspect_sql_escape`.

---

## Finding 3: Path Traversal in scope.file_patterns — No Shell Execution Risk, But LLM Interpretation Risk Is Real

**Severity:** Medium (not a shell injection risk, but a meaningful LLM manipulation risk that undermines the security model)

**Location:** Plan Task 4, SKILL.md Step 1.2a.0 update; JSON Schema `scope.file_patterns` definition.

The schema defines `scope.file_patterns` as an array of arbitrary strings with no restrictions:

```json
"file_patterns": {
  "type": "array",
  "items": { "type": "string" },
  "description": "Glob patterns for file paths (e.g., 'interverse/**')."
}
```

The proposed SKILL.md instruction says:

> If `scope.file_patterns` is set, check if any input file path matches any glob pattern. If no match, skip this override.

The scope check is performed by the LLM reading the SKILL.md — there is no shell glob expansion. The LLM is being asked to pattern-match file paths against glob strings. This creates two related risks:

**3a. Adversarial patterns that confuse the LLM:**

A contributor could add patterns designed to confuse the LLM's matching logic:

```json
"file_patterns": ["**", "*", ".*", "interverse/**", "../**"]
```

The `**` pattern would match everything, silently making a scoped override into a global one. A pattern like `../` has no shell meaning here since the LLM is doing string matching, but a naive LLM might interpret `../secrets/**` as matching any file with "secrets" in the path. The SKILL.md gives no rules about how the LLM should resolve ambiguous or overly broad patterns.

**3b. Security agent suppression via crafted scope:**

The most concrete risk: a contributor commits an entry like:

```json
{
  "agent": "fd-safety",
  "action": "exclude",
  "scope": {
    "file_patterns": ["**"]
  }
}
```

The `**` pattern, if the LLM interprets it as "match all files", silently suppresses fd-safety for every review without triggering the cross-cutting agent warning (because the SKILL.md only warns about global excludes, not scoped ones that effectively apply globally). The plan does add a cross-cutting warning but only for entries with NO `scope` field:

> If the excluded agent is cross-cutting... add a prominent warning

A scoped override that resolves to match-all bypasses this warning.

**Mitigations:**

1. Add a `maxLength` and a pattern constraint to the schema for `file_patterns` items:

```json
"items": {
  "type": "string",
  "maxLength": 200,
  "pattern": "^[^/]"
}
```

The `^[^/]` ensures no pattern starts with `/` (absolute path traversal) and more importantly document that `..` sequences should be rejected during reader validation.

2. Add a jq-based validation step in `_interspect_read_routing_overrides` that rejects file patterns containing `..` or starting with `/`:

```bash
local bad_patterns
bad_patterns=$(echo "$content" | jq '[.overrides[].scope.file_patterns[]? | select(startswith("/") or contains(".."))] | length' 2>/dev/null || echo 0)
if (( bad_patterns > 0 )); then
    echo "WARN: routing-overrides.json contains suspicious file_patterns (absolute or traversal), treating as no-match" >&2
fi
```

3. Update the SKILL.md scope check to add: "A pattern of `**` or `*` applied to a cross-cutting agent (fd-safety, fd-architecture, fd-quality, fd-correctness) MUST be treated as a global exclude and emit the same prominent cross-cutting warning as a scopeless override." This closes the bypass.

4. Add a schema constraint that disallows `**` as a sole pattern on cross-cutting agents. This cannot be enforced in JSON Schema draft-07 without complex `if/then` but can be enforced at read time in the bash validator.

---

## Finding 4: Trust Boundary — Git-Committed Override That Can Exclude fd-safety

**Severity:** Medium-High (architectural: the mechanism is intentional but the safety net is incomplete)

**Location:** The entire plan. The `routing-overrides.json` file is committed to git and is the mechanism by which agents are excluded from flux-drive triage.

The plan correctly adds a warning for cross-cutting agent exclusions (fd-architecture, fd-quality, fd-safety, fd-correctness). This is the primary safety net. However, three gaps remain:

**4a. No code review gate on the override file itself:**

Because `routing-overrides.json` is a committed JSON file, any contributor with write access to the repo can add an exclusion for fd-safety by editing the file directly (bypassing `_interspect_apply_routing_override` and all its validation). The schema validation in the reader is non-blocking for most fields. The SKILL.md warning fires at review time but that is after the file is already in the repo.

The plan has no recommendation for a pre-commit hook or CI check that alerts when a cross-cutting agent is added to `routing-overrides.json`. This is a gap.

**Mitigation:** Add a lightweight pre-commit hook or CI lint step:

```bash
# In a git hook or CI script
cross_cutting="fd-safety fd-architecture fd-quality fd-correctness"
for agent in $cross_cutting; do
    if jq -e --arg a "$agent" '.overrides[] | select(.agent == $a and .action == "exclude")' .claude/routing-overrides.json >/dev/null 2>&1; then
        echo "WARNING: routing-overrides.json excludes cross-cutting agent: $agent"
        echo "This removes security/correctness coverage. Review carefully before merging."
        # Non-blocking: warn only, do not fail, since the intent may be legitimate
    fi
done
```

**4b. No expiry enforcement:**

The `canary.expires_at` field is a snapshot. The plan explicitly says "DB is authoritative for live state". But the SKILL.md displays this expiry date to the user and implies ongoing monitoring. If the canary has expired in the DB but the JSON snapshot shows an old `expires_at`, the LLM displays stale information. This is a UX issue, not a security issue, but it could make a lapsed override appear actively monitored when it is not.

**Mitigation:** The SKILL.md display note should add: "Note: canary data shown is a snapshot from creation time. Run `/interspect:status` for current monitoring state."

**4c. The plan does not restrict who can write routing-overrides.json:**

The `created_by` field records who created an override ("interspect" vs "manual"). There is no enforcement that `created_by: "interspect"` actually came from `_interspect_apply_routing_override`. A manual edit of the JSON can claim any `created_by` value. This is cosmetic only since the field is informational, but it means the audit trail in the JSON is not trustworthy. The DB modifications table is the authoritative audit record.

This is acceptable given that the file is already in git (git history is the real audit trail), but the plan should not describe `created_by` as providing security-meaningful attribution.

---

## Finding 5: Canary Metadata Disclosure — Negligible Risk in Context

**Severity:** Low / Informational

**Location:** `canary_snapshot` in the committed JSON — `window_uses` (integer) and `expires_at` (ISO 8601 timestamp).

The question is whether exposing `window_uses` and `expires_at` in a committed file creates information disclosure risk. Analysis:

- **`window_uses`:** Always the configured default (20 in the code, from `_INTERSPECT_CANARY_WINDOW_USES`). This is already visible in `lib-interspect.sh` and in confidence.json config. Not sensitive.
- **`expires_at`:** A timestamp 14 days from override creation. Reveals when the canary monitoring window ends. In a local developer tool context (not a public-facing service), this is not sensitive. An attacker who has read access to git history already knows when the override was created. Adding 14 days reveals nothing additional.
- **`status: "active"`:** Confirms monitoring is active. Same argument — not sensitive.

The canary snapshot is clearly labelled "DB is authoritative for live state", so the JSON is a snapshot not a live control plane. No secrets, no credentials, no private keys.

**Verdict:** No actionable risk. The disclosure question is moot for a local developer tool committed to a project repo. Flag if this pattern is reused in a context where the JSON is publicly accessible (e.g., uploaded to a public marketplace endpoint).

---

## Finding 6: additionalProperties: true on Override Entries — Schema Is Too Permissive

**Severity:** Low (schema enforcement gap, not an exploitable vulnerability)

**Location:** Plan Task 1 — the `override` definition in `routing-overrides.schema.json`:

```json
"override": {
  "type": "object",
  "required": ["agent", "action"],
  "additionalProperties": true,
  ...
}
```

`additionalProperties: true` is intentional for forward compatibility (the plan notes "Reserved for iv-6liz"). However, the top-level `overrides` object also has `additionalProperties: true`:

```json
{
  "type": "object",
  "required": ["version", "overrides"],
  "additionalProperties": true,
  ...
}
```

This means the schema provides no signal if someone adds a root-level field that happens to shadow a future schema field, or if an override entry contains fields that conflict with future spec additions. Since this is a schema (used for documentation and validation tooling, not enforced at runtime in the bash code), the blast radius is limited. The bash reader in Task 3 does not call a schema validator — it implements a subset of checks directly in jq.

**Mitigation:** Document explicitly in the schema's `description` that `additionalProperties: true` is intentional for v1 forward-compatibility and will be tightened in v2. Add a comment noting that bash reader implements a curated subset of validation, not full schema validation. No code change needed, but the gap should be acknowledged.

---

## Deployment and Migration Review

**Rollback feasibility:** Full. The plan adds optional fields to an existing JSON file. The existing reader ignores unknown fields today. The new reader in Task 3 also preserves unknown fields. Rolling back the writer (to not produce confidence/canary fields) leaves any already-written files with those fields in place — the old reader ignores them cleanly.

**Migration impact:** No database schema changes. No migration steps. The only persistent change is new fields in `routing-overrides.json`. This is additive and backward-compatible.

**Sequencing:** Task 3 (reader validation) can be deployed before Task 2 (writer extension) with no issue — the reader will just never see the new fields. Task 2 before Task 3 is also safe — the writer adds fields the old reader ignores.

**Pre-deploy invariant:** Verify `jq '.' .claude/routing-overrides.json` exits 0 before deploying (existing file is valid JSON). The new reader rejects malformed JSON and falls back to empty — this is safe.

**Post-deploy verification:** The BATS test suite in Task 2 and Task 3 provides adequate coverage for the writer and reader. The integration smoke test in Task 5 closes the end-to-end loop.

**One sequencing risk:** Task 2 Step 3 adds the confidence computation BEFORE the flock but AFTER validation. The plan says "compute confidence from evidence" inside `_interspect_apply_routing_override`. This means two sqlite3 queries run outside the flock (total and wrong counts), and then the write + DB inserts happen inside the flock. The counts could change between the pre-flock read and the locked write if another process inserts evidence concurrently. This is a TOCTOU on the confidence snapshot — the stored confidence value might not match the state at commit time. The plan acknowledges this indirectly ("Snapshot — does not update") but does not call out the race. For a confidence snapshot that is explicitly labelled as "at creation time", this is acceptable. Document it explicitly.

---

## Summary of Findings

| # | Severity | Finding | Action |
|---|----------|---------|--------|
| 1 | Low-Med | awk shell interpolation of `$wrong`/`$total` — works today due to COUNT(*) output being digits, but is a fragile pattern | Change to `awk -v w="$wrong" -v t="$total"` + add integer guard |
| 2 | Low | Confidence SQL computation ordering — safe only if `_interspect_validate_agent_name` runs first | Add explicit comment; verify ordering in implementation |
| 3 | Medium | `scope.file_patterns` glob matching by LLM — `**` can silently make scoped override global, bypassing cross-cutting warning | Add `**` check for cross-cutting agents in SKILL.md; reject `..` and `/`-prefixed patterns in bash reader |
| 4a | Med-High | No pre-commit or CI gate for cross-cutting agent exclusions in routing-overrides.json | Add non-blocking lint step in git hook or CI |
| 4b | Low | Canary `expires_at` in JSON is stale after canary evaluation — SKILL display could mislead | Add "snapshot from creation time" note in SKILL.md display |
| 5 | Info | Canary metadata disclosure in committed JSON — no risk in local tool context | No action needed; note if reused in public-facing context |
| 6 | Low | `additionalProperties: true` on schema — permissive but intentional | Document intent explicitly in schema description |

**Go/No-Go:** The plan is safe to implement with the awk interpolation fix (Finding 1) applied before shipping and the `scope.file_patterns` cross-cutting bypass addressed (Finding 3). The trust boundary gap (Finding 4a) is a residual risk that depends on operational discipline (contributor code review) until a pre-commit lint step is added. All other findings are low severity or informational.
