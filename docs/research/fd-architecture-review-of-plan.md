# Architecture Review: Interspect Routing Overrides Schema + Flux-Drive Reader
**Plan:** `/home/mk/projects/Demarch/docs/plans/2026-02-23-interspect-routing-overrides-schema.md`
**Bead:** iv-r6mf
**Date:** 2026-02-23
**Reviewer:** fd-architecture (Flux-Drive Architecture & Design Review)

---

## Summary

The plan is structurally sound for its stated scope. The cross-repo contract is explicit (JSON Schema as source of truth), the write-side and read-side separation is preserved, and the scope definition is semantically appropriate. Three issues require attention before implementation: a pre-flock timing hazard introduced by computing confidence and canary params outside the lock, a bash positional-param pattern that works but carries forward known fragility, and one schema extensibility gap that will force a version bump for bead iv-6liz. Everything else is optional cleanup.

---

## 1. Boundaries and Coupling

### 1.1 Cross-Repo Contract Architecture

The routing-overrides.json file is the integration seam between two separate git repos: `os/clavain/` (writer) and `interverse/interflux/` (reader). The plan correctly identifies this and addresses it by promoting the schema to a first-class artifact under `os/clavain/config/routing-overrides.schema.json`.

**Finding — schema ownership creates an implicit pull dependency.**

The schema lives in Clavain but flux-drive (interflux) must conform to it. The plan updates SKILL.md by hand, which is correct for a markdown-only protocol. However, the schema is not referenced from the flux-drive SKILL.md or SKILL-compact.md — the reader has no machine-readable pointer to the authoritative schema. This is acceptable for the current bead scope, but when iv-6liz (manual routing override support) ships, a human editing `.claude/routing-overrides.json` by hand has no way to discover the schema path from the reader side. Consider adding a one-line comment to the SKILL.md Step 1.2a.0 block:

```markdown
Schema: `os/clavain/config/routing-overrides.schema.json` (Clavain repo)
```

This is optional cleanup, not a boundary violation.

**Finding — the reader-side validation does not enforce version ceiling symmetrically.**

The plan adds `version > 1` rejection to the reader (Task 3, Step 3). The schema sets `"const": 1` on version. These are consistent. However, the schema uses `"additionalProperties": true` at the root object level, which is correct for forward compatibility, but the `canary_snapshot` definition uses `"additionalProperties": false`. If a future bead adds a field to `canary_snapshot` (for instance, iv-3r6q may need per-domain canary tracking), readers running the v1 schema will silently accept the unknown field in the JSON but the schema itself will fail validation. This is a minor inconsistency: root allows extras, canary does not. Recommend changing `canary_snapshot` to `"additionalProperties": true` to match root-level forward-compatibility intent.

**Finding — the `scope` definition uses `additionalProperties: false` on a type expected to grow.**

The `scope` definition locks down its properties. Bead iv-8fgu (pattern detection + propose flow) will likely need to add additional scope discriminants (e.g., `phase`, `agent_category`). With `additionalProperties: false`, any future scope field will fail schema validation on v1 readers that validate with strict tools. Since the plan intentionally defers scope enforcement to flux-drive's own logic (not a validator binary), this is low-risk for runtime behavior. But it is inconsistent with the forward-compat intent signalled by the root `additionalProperties: true`. Recommend changing `scope` to `"additionalProperties": true`.

### 1.2 Writer/Reader Separation

The plan correctly keeps confidence computation in the writer and treats the canary snapshot as a point-in-time record. The comment "DB is authoritative for live state" in the schema description is the right framing — the JSON snapshot is audit trail, not live truth. This is architecturally clean and the SKILL.md update (Task 4) correctly reflects it by displaying "canary: active, expires date" as informational-only.

**No layer violations detected.** Clavain writes, interflux reads. Interspect (housed in Clavain) does not import anything from interflux. The file contract (JSON) is the only coupling surface.

---

## 2. Pattern Analysis

### 2.1 The `shift 9` Pattern

The plan at Task 2, Step 5 introduces:

```bash
_interspect_apply_override_locked() {
    set -e
    local root="$1" filepath="$2" fullpath="$3" agent="$4"
    local reason="$5" evidence_ids="$6" created_by="$7"
    local commit_msg_file="$8" db="$9"
    shift 9
    local confidence="${1:-1.0}" canary_window_uses="${2:-20}" canary_expires_at="${3:-null}"
```

**Must-fix: `shift 9` is the correct approach, but it creates a fragile interface.**

The existing `_interspect_apply_override_locked` function is already at 9 positional arguments ($1–$9). Bash requires `${9}` for single-digit params but in this specific usage the `local db="$9"` works correctly. The `shift 9` then resets `$1`–`$3` to confidence, canary_window_uses, and canary_expires_at.

This is technically valid bash but creates a maintenance hazard: the caller (`_interspect_apply_routing_override`, lines 652–654 in existing code and the plan's Task 2, Step 4 replacement) must pass exactly 12 positional arguments in the correct order, with no named-argument protection. The plan's line count comments (line ~652, line 677) will drift as the file changes. The `_interspect_flock_git` function bridges all args through a subshell, so there is no `$@` expansion issue, but the implicit contract between the two functions is invisible.

The cleaner alternative — which stays within the existing bash convention already used in the file — is to write confidence, canary_window_uses, and canary_expires_at into a temp file (or a shared env var prefixed with `_INTERSPECT_`) before calling flock, and read them back inside the locked function without passing through positional params at all. The `_INTERSPECT_CANARY_WINDOW_USES` and `_INTERSPECT_CANARY_WINDOW_DAYS` env vars already exist (used in the locked function body at lines 776–777 of the existing code), which means the canary params are already available inside the locked function via the environment — they do not need to be passed positionally at all.

**Recommended minimal fix:**

Remove the `confidence` and canary params from the `_interspect_flock_git` call entirely. Inside `_interspect_apply_override_locked`, compute confidence and canary params the same way the existing code at lines 757–798 already does. The DB query for wrong/total counts is already performed inside the lock (lines 758–770 in the existing locked function body for canary baseline). Adding the confidence computation there collapses the timing issue described in Section 2.2 and eliminates `shift 9` entirely.

The cost is one additional DB query inside the lock. Given the lock is already doing multiple DB inserts and a git commit, this is negligible.

### 2.2 Pre-Flock Timing Hazard (Confidence Computation)

**Must-fix: The plan computes confidence before entering the flock.**

Task 2, Step 3 places the confidence DB query in `_interspect_apply_routing_override` (outside flock). The query is:

```bash
total=$(sqlite3 "$db" "SELECT COUNT(*) FROM evidence WHERE source = '${escaped_agent_q}' AND event = 'override';")
wrong=$(sqlite3 "$db" "SELECT COUNT(*) FROM evidence WHERE source = '${escaped_agent_q}' AND event = 'override' AND override_reason = 'agent_wrong';")
```

The evidence table can receive concurrent writes from the `interspect-evidence.sh` hook (a PostToolUse hook that fires asynchronously during normal agent operation). If a new evidence row is inserted between the pre-flock confidence read and the flock-protected write, the confidence value stamped into routing-overrides.json will be stale by the time the file is written.

In practice the window is milliseconds and the severity is low (a slightly stale snapshot is acceptable as audit data). But the comment in the schema — "Snapshot — does not update" — implies the value is authoritative at creation time. A stale read undermines that claim.

The fix (move confidence computation inside the locked function) is described in Section 2.1 above and addresses both the timing hazard and the `shift 9` interface problem simultaneously.

**The canary `expires_at` computation has the same pre-flock issue** (Task 2, Step 3 also computes `canary_expires_at` before flock). The expires_at is `now + 14 days`, so a pre-flock computation is off by at most the time to acquire the lock — effectively zero. This is acceptable to leave as-is if the confidence computation is already moved inside.

### 2.3 Existing Canary Logic Inside the Locked Function

Examining the existing `_interspect_apply_override_locked` body (lines 748–801), the locked function already computes:
- `_interspect_compute_canary_baseline` (line 760)
- `expires_at` via `date -u -d "+14 days"` (line 776)
- Inserts into the `canary` table including `window_uses` and `window_expires_at` (line 793)

The plan proposes writing a *redundant* canary snapshot to the JSON file, separate from the DB insert. These two paths must stay in sync: if the DB canary insert fails (non-fatal, lines 795–797), the JSON snapshot will show "active" while the DB shows "applied-unmonitored". This is a minor inconsistency but acceptable given the schema's comment that "DB is authoritative." The non-fatal failure path for canary is already handled correctly in existing code; the JSON snapshot is advisory.

One concern: the existing locked function writes `window_uses = _INTERSPECT_CANARY_WINDOW_USES:-20` to the DB (line 793) while the proposed JSON snapshot writes `window_uses` from the positionally-passed `canary_window_uses` arg. If these diverge (e.g., the env var changes between the pre-flock and the in-lock DB insert), the JSON and DB will disagree on window_uses. This is eliminated by computing everything inside the lock from the same env var.

---

## 3. Schema Extensibility for Downstream Beads

### 3.1 iv-8fgu: Pattern Detection + Propose Flow

This bead adds automated detection of routing-eligible patterns and a propose flow. It will need to write proposed overrides with a status of `"proposed"` (not yet `"active"` exclusions). The current schema's `action` field is an enum: `["exclude"]`. A proposed override would likely need `action: "propose"` or a separate `status` field.

**Gap:** The v1 schema does not have an `action` value for "propose" or a lifecycle `status` field on overrides. iv-8fgu will either need to use a separate file (adding a new integration seam) or bump the schema to v2 for a new action value.

**Recommendation:** Add `"propose"` to the `action` enum now, while the schema is being written. It costs nothing and prevents a forced v2 bump for a bead already in the dependency chain. The flux-drive reader can safely ignore `action: "propose"` entries (they are not yet active exclusions). The schema comment on `action` already says "Currently only 'exclude' is supported" — this is the right framing, and adding "propose" to the enum is forward-compatible.

### 3.2 iv-6liz: Manual Routing Override Support

This bead enables human-authored entries in routing-overrides.json. The `overlays` array is already reserved for it (root-level property). The `created_by` field supports `"manual"` as a value. No schema changes needed. This bead is well-supported by the v1 schema as designed.

The one gap: iv-6liz users will not have a `confidence` value (confidence is computed from evidence, and manual overrides have no evidence). The schema marks `confidence` as optional with no constraint on its absence. The reader (Task 3) does not check for confidence. This is correct — no action needed.

### 3.3 iv-3r6q: Not Found in Open Beads

The bead iv-3r6q referenced in the review scope does not appear in the open bead list. Based on context (the schema is at v1 with canary and scope fields), if iv-3r6q relates to per-domain canary tracking or scope-aware canary windows, the current `canary_snapshot` definition with `additionalProperties: false` would block that extension. See Section 1.2 above.

---

## 4. Scope Definition: `domains AND file_patterns` Logic

Task 4, Step 1 specifies:

> If both are set, BOTH must match (AND logic).

**Finding: AND semantics are correct and necessary, but the empty-field semantics are underspecified.**

The schema definition for `scope` has no `required` fields — both `domains` and `file_patterns` are optional. The SKILL.md instruction handles the "both set" case (AND) and the "no scope field" case (global). But it does not define behavior when `scope` is present but empty: `{"scope": {}}`. Is an empty scope object treated as global (no restriction) or as "always-skip" (impossible to match)?

**Recommendation:** Add one sentence to the SKILL.md instruction: "If `scope` is present but has no `domains` and no `file_patterns`, treat it as a global override (equivalent to omitting `scope`)." This prevents ambiguity without changing the schema.

**The domain-matching logic has a precision issue.** The SKILL.md says "check if the current document's detected domain (from Step 1.1) matches any domain in the list." Step 1.1 sets a single detected domain from the domain profile system. Matching a single string against a list is correct. But the domain names in the schema description use examples like `'claude-code-plugin'` and `'tui-app'`, which match the domain directory names in `interverse/interflux/config/flux-drive/domains/`. The reader must use the exact slug (not a display name) for matching. The SKILL.md should specify this: "Match against the domain slug (the `domains/` directory basename), not a display label."

---

## 5. Task 3 Validation Behavior — Non-Blocking vs. Blocking

Task 3 adds schema-aware validation to `_interspect_read_routing_overrides`. The validation design mixes blocking and non-blocking checks:

- Version mismatch: blocks (returns empty, exit 1). Correct.
- Overrides not array: blocks (returns empty, exit 1). Correct.
- Missing agent/action on individual entries: non-blocking (warns, returns data, exit 0). Correct.

**Finding: The test for version validation (Task 3, Step 1) has a contradictory assertion.**

```bash
@test "read_routing_overrides validates version field" {
    echo '{"version":2,"overrides":[]}' > "${TEST_DIR}/.claude/routing-overrides.json"
    run _interspect_read_routing_overrides
    [ "$status" -eq 1 ]
    [[ "$output" == *'"version":1'* ]]  # Returns empty structure
    [[ "${lines[0]}" == *"WARN"* ]] || [[ "$output" == *"version"* ]]
```

The test asserts `[ "$status" -eq 1 ]` (correct: version mismatch should return exit 1), and simultaneously checks that `$output` contains `"version":1` (the empty structure). But the BATS `run` command captures both stdout and stderr into `$output`. The empty structure `{"version":1,"overrides":[]}` goes to stdout; the WARN goes to stderr. In BATS, `$output` captures stdout only; stderr goes to `$stderr` (in BATS 1.5+) or is mixed depending on version. The assertion `[[ "${lines[0]}" == *"WARN"* ]]` may fail if stderr is not captured into `$output`. This is a test correctness issue, not an architecture issue, but it will produce a false pass or false fail depending on BATS version.

**Recommendation:** Use `run -1 _interspect_read_routing_overrides` (BATS 1.5+ syntax) or redirect stderr: `run bash -c '_interspect_read_routing_overrides 2>&1'`. Alternatively, assert only on stdout (`$output`) for the empty structure and rely on the exit code for the blocking check.

---

## 6. Task 5 Integration Test — Cleanup Reliability

Task 5, Step 4 says "Remove the temporary `.claude/routing-overrides.json` if it was created." This is unscripted — it is a manual instruction with no automation. The integration test (Step 1) writes to `.claude/routing-overrides.json` in the working directory. If the test runs inside a Clavain project directory that already has a real `routing-overrides.json`, Step 4's cleanup will delete a production file.

**Must-fix:** The integration smoke test should write to a temp directory or use the `FLUX_ROUTING_OVERRIDES_PATH` env var to redirect the path: `FLUX_ROUTING_OVERRIDES_PATH=/tmp/test-overrides-$$.json`. This is consistent with how the BATS tests already use `TEST_DIR` and `HOME` overrides for isolation. The plan's Step 1 creates the file directly without overriding the path, making the integration test environment-sensitive.

---

## 7. Classifying Issues by Priority

### Must-Fix (structural or correctness)

1. **Pre-flock confidence computation timing hazard** (Task 2, Step 3) — compute confidence and canary params inside `_interspect_apply_override_locked` instead. Eliminates the TOCTOU window and the `shift 9` interface problem simultaneously. The existing locked function already has access to all needed state (DB path, env vars).

2. **Integration smoke test writes to live working directory** (Task 5, Step 1) — use `FLUX_ROUTING_OVERRIDES_PATH` override to redirect to a temp path, matching the BATS test isolation pattern already established.

3. **`action` enum missing `"propose"` value** — iv-8fgu is already in the dependency chain and will need this. Adding it now costs nothing and prevents a schema v2 bump for a bead already blocked on iv-r6mf.

### Should-Fix (precision or forward-compat)

4. **`canary_snapshot` and `scope` use `additionalProperties: false`** — inconsistent with root-level forward-compat intent. Change both to `additionalProperties: true`.

5. **Empty `scope` object behavior is undefined** — add one sentence to SKILL.md Step 1.2a.0: if `scope` is present but empty, treat as global.

6. **Domain-matching should specify slug-based matching** — SKILL.md should reference the `domains/` directory basename, not a display label.

### Optional Cleanup

7. **BATS test `$output` vs stderr distinction** (Task 3 tests) — tighten assertions to be explicit about stdout vs stderr capture.

8. **Schema not referenced from SKILL.md** — add a one-line pointer to the schema path for discoverability by iv-6liz manual editors.

---

## 8. What the Plan Gets Right

- The schema correctly uses `"additionalProperties": true` at the root level and on the `override` definition — the primary extensibility surface.
- The `overlays` array reservation for iv-6liz is a clean placeholder that adds no operational overhead.
- Using `jq --arg` / `--argjson` throughout (no shell interpolation into JSON) is the correct pattern and is consistent with existing code.
- The `confidence` value is clearly marked as a snapshot ("does not update") in both the schema description and the SKILL.md — this prevents consumers from treating it as live truth.
- The two-file approach (SKILL.md full protocol + SKILL-compact.md one-liner) is the established interflux pattern; updating both is correct.
- The read-side validation correctly distinguishes blocking errors (version mismatch, non-array overrides) from non-blocking warnings (missing agent/action on individual entries). This matches the principle that the reader should degrade gracefully on future extensions.
- TDD approach (write failing test, implement, verify) matches the `intertest` quality discipline established in the project.
