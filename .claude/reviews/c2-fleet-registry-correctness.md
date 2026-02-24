# Correctness Review: C2 — Agent Fleet Registry

**Plan:** `os/clavain/docs/plans/2026-02-22-c2-fleet-registry.md`
**Reviewer:** Julik (fd-correctness)
**Date:** 2026-02-22
**Status:** NEEDS_ATTENTION — 8 findings, 3 HIGH, 4 MEDIUM, 1 LOW

---

## Invariants Under Review

Before examining the findings, these are the invariants the implementation must preserve:

1. **Merge invariant:** A curated field (capabilities, models, cold_start_tokens, tags) written by a human must survive any number of scan-fleet.sh invocations, even if the agent's source file is modified.
2. **Removal safety invariant:** Removing an agent's .md file must not silently corrupt the registry. The registry must either purge the stale entry or flag it — not quietly preserve a ghost entry that consumers treat as live.
3. **New-agent invariant:** An agent with no existing registry entry must receive a scaffold with sane defaults, not cause the script to fail or skip the entry.
4. **Sourcing idempotency invariant:** `_FLEET_LOADED` must guarantee that sourcing lib-fleet.sh multiple times in the same shell process produces the same behavior as sourcing it once.
5. **Consumer contract invariant:** Every lib-fleet.sh public function must return a consistent output format (newline-separated IDs, or full YAML block for fleet_get) regardless of the registry state.
6. **Schema invariant:** A fleet-registry.yaml that passes JSON Schema validation must be safe to consume by all public lib-fleet.sh functions.

---

## Finding 1 — HIGH: Ghost agents are silently preserved and treated as live

**Area:** F2 merge logic — stale entries

**The problem:**

The plan specifies merge semantics where generated fields overwrite and curated fields are preserved. The natural shell implementation of this is to iterate discovered agents, merge them into the existing registry, and write the result. The step that is unspecified is what happens to entries in the existing registry that have no corresponding .md file.

If an agent is renamed, moved to a different plugin, or deleted, scan-fleet.sh will not discover it. Its old entry survives in the registry. The C3 Composer and flux-drive triage will then dispatch to a `subagent_type` that no longer exists.

This is not a theoretical concern. The plan itself lists agents in `.claude/agents/` and notes they include "fd-cli-ux, fd-dispatch-efficiency, etc." These are project-local agents that will differ between repositories. Any project that installs Clavain will have different local agents, yet if someone runs scan-fleet.sh once with local agents present and then moves to a different project, the ghost entries remain.

**Concrete failure sequence:**
1. scan-fleet.sh runs in Project A, finds `.claude/agents/fd-dispatch-efficiency.md`, writes entry to registry.
2. Registry is committed to the clavain repo.
3. Clavain is deployed to Project B. scan-fleet.sh is not re-run (or is run with `--in-place` updating the committed file).
4. C3 Composer reads fleet-registry.yaml, selects `fd-dispatch-efficiency` for a task.
5. Claude Code's Task tool cannot find `interflux:review:fd-dispatch-efficiency` or `.claude/agents/fd-dispatch-efficiency.md` in Project B.
6. The dispatch silently fails or throws, depending on how C3 handles the error.

**Required fix:**

scan-fleet.sh must implement one of:
- **Tombstone mode (recommended):** Add an `orphaned_at` field to entries that exist in the registry but were not discovered in the current scan. Consumers must check `orphaned_at` absence before dispatching. The plan references `critical-patterns.md` which already describes this field for orphaned plugin entries — use the same pattern here.
- **Prune mode:** Remove undiscovered entries. Acceptable only if curated fields are backed up or the registry is under version control (which it will be).
- **Warn-and-preserve mode (minimum):** Log a warning to stderr listing entries not seen in the current scan. This at least makes the problem visible without silent data loss.

The plan must state which behavior is chosen. Defaulting to silent preservation is the wrong default.

---

## Finding 2 — HIGH: TOCTOU in frontmatter extraction — sed + yq pipeline is fragile

**Area:** F2 scan-fleet.sh, frontmatter parsing

**The problem:**

The plan specifies frontmatter extraction as `sed -n '/^---$/,/^---$/p'` piped to yq. This pattern has three correctness failures:

**A) The sed pattern matches the wrong range.** The regex `/^---$/,/^---$/p` matches from the first `---` to the second `---`, inclusive. It includes both delimiter lines in the output. When piped to `yq`, yq sees:

```yaml
---
name: fd-architecture
description: "..."
model: sonnet
---
```

This is a valid YAML document stream, but yq's behavior on the trailing `---` (which terminates the document in YAML spec) depends on the yq version. With yq v4, `yq '.name' <<< "---\nname: foo\n---"` returns `foo`, but if the file uses `---` as a separator between multiple documents (valid YAML), yq may parse both documents and concatenate, silently returning the first matching key only. Any agent file that has a multi-document YAML frontmatter (some generator tools produce these) will be misread.

**B) Files with no frontmatter cause silent empty output.** If an agent .md file has no `---` delimiters (valid for agent files — the plan notes "handles missing frontmatter gracefully" as a test case but does not specify the handling), the sed command outputs nothing. If the script does not check for empty output before constructing the registry entry, it will insert an agent with empty name and description fields. A name of `""` will corrupt any yq merge that uses the name as a map key.

**C) Tab characters in frontmatter break YAML validity.** Claude Code agent files sometimes use tabs for visual alignment in description strings (or tools writing them may). YAML does not allow tab indentation in block scalars. If yq encounters a tab-indented line in frontmatter, it errors. The plan does not specify error handling for yq parse failures in the frontmatter step.

**Concrete failure for (B):**

An agent file like `fd-cli-ux.md` begins with metadata from flux-gen (`generated_by`, `domain`, `generated_at`) before the usual `name`/`description` fields. If the generated metadata section uses a different frontmatter delimiter format, or if future flux-gen versions change the frontmatter structure, the sed extraction will produce unexpected YAML and yq will silently return `null` for the `name` field.

**Required fix:**

- Use `yq` directly to extract frontmatter from the file if yq supports it (yq v4 can read YAML files with leading `---`). Alternatively, extract the frontmatter block into a temp file with controlled delimiters before passing to yq.
- Explicitly check for empty `name` after extraction; skip and warn if empty.
- Wrap each yq invocation in error checking: `name=$(yq '.name' "$tmpfile" 2>/dev/null) || { echo "Warning: failed to parse frontmatter in $file" >&2; continue; }`.

---

## Finding 3 — HIGH: _FLEET_LOADED guard is insufficient when FLEET_REGISTRY_PATH changes between sources

**Area:** F3 lib-fleet.sh, source guard

**The problem:**

The pattern `[[ -n "${_FLEET_LOADED:-}" ]] && return 0` is copied from lib-routing.sh's `_ROUTING_LOADED` guard. In lib-routing.sh this is correct because the routing config path is resolved once and cached. The proposed lib-fleet.sh will do the same: resolve the registry path on first source, cache it, and skip on subsequent sources.

The failure case is when two different scripts source lib-fleet.sh with different `CLAVAIN_FLEET_CONFIG` (or equivalent) environment variables:

```bash
# Script A: fleet analysis tool
export CLAVAIN_FLEET_CONFIG=/tmp/test-registry.yaml
source lib-fleet.sh   # Resolves to test-registry.yaml, sets _FLEET_LOADED=1

# Script B: sprint pipeline (sourced by the same process as Script A)
source lib-fleet.sh   # _FLEET_LOADED is set → returns immediately
# fleet_list now reads from /tmp/test-registry.yaml, not the real registry
```

This is not hypothetical. The bats test suite for lib-routing.sh explicitly `unset _ROUTING_LOADED` in setup() for exactly this reason. But outside of tests, if the sprint pipeline sources lib-fleet.sh after any tool that has already sourced it with a different config, it gets stale data.

**More immediately:** The bats test for lib-fleet.sh will need to unset `_FLEET_LOADED` between tests (as the routing tests do). The test plan in F4 does not mention this. If tests run in a single shell process (as bats does by default), the first test's source will poison all subsequent tests.

**Required fix:**

- The guard must invalidate if `CLAVAIN_FLEET_CONFIG` (or the resolved path) has changed. lib-routing.sh stores `_ROUTING_CONFIG_PATH`; lib-fleet.sh should compare the cached path against the current resolution on every source and invalidate if they differ.
- Alternatively, name the invalidation variable `_FLEET_REGISTRY_PATH` and check both that it is set and that it matches the currently resolved path.
- F4 tests must unset `_FLEET_LOADED` and any cached path variable in setup() — the test plan must explicitly require this.

**Reference:** `test_routing.bats` line 14: `unset _ROUTING_LOADED` — same pattern required for fleet tests.

---

## Finding 4 — MEDIUM: yq invocation safety — unquoted variables and missing error propagation

**Area:** F3 lib-fleet.sh, all query functions

**The problem:**

The plan describes functions like `fleet_by_capability <capability>` and `fleet_within_budget <max_tokens> [category]`. These will compose yq expressions using shell variables. The canonical mistake is:

```bash
fleet_by_capability() {
  local cap="$1"
  yq ".agents | to_entries | .[] | select(.value.capabilities[] == \"$cap\") | .key" "$_FLEET_REGISTRY_PATH"
}
```

Three failure modes:

**A) Capability values with special characters.** If a capability name contains `.` or `*` or a quote, the interpolated yq expression will be syntactically invalid or will match more than intended. yq uses `select()` with string equality, but interpolated expressions bypass quoting. A capability like `multi_perspective` is safe; if a future capability is named `domain.review` (dotted), the expression becomes `.capabilities[] == "domain.review"` which yq will interpret as path notation, not string equality.

**B) Missing file handling.** If `_FLEET_REGISTRY_PATH` is empty (no config found, same as lib-routing.sh's "no config — all resolvers return empty" behavior), the yq call will fail with "file not found" on stderr but the function will return exit code 0 if the error is swallowed. Callers checking `fleet_by_capability` return code will see success with empty output — indistinguishable from "no agents have that capability."

**C) The `fleet_within_budget` numeric comparison.** `yq` performs string comparison by default. The expression `select(.value.cold_start_tokens <= $max)` where `$max` is a shell variable will either require `env` passing or string interpolation. If the value in the YAML is stored as a string (quotes around the number), yq string-compares "800" <= "500" which is true (lexicographic), giving wrong results.

**Required fix:**

- Use yq's `--arg` / environment variable passing for user-supplied values: `yq --arg cap "$cap" '.agents | to_entries | .[] | select(.value.capabilities[] == $cap) | .key'`.
- For numeric comparisons, cast explicitly in the yq expression: `select((.value.cold_start_tokens | tonumber) <= ($max | tonumber))`.
- Check `$_FLEET_REGISTRY_PATH` before every yq call; emit a clear error and return non-zero if absent.
- The plan says yq is the implementation approach, so enforce `set -e` discipline or per-call `|| return 1` in lib-fleet.sh functions.

---

## Finding 5 — MEDIUM: Removed-agent category ambiguity in merge — curated fields cannot be matched by position

**Area:** F2 merge logic — key collision on agent rename

**The problem:**

The merge semantics state: "generated fields overwrite, hand-curated fields are preserved from existing registry." The merge key is the agent ID (the YAML map key, e.g., `fd-architecture`). Curated fields are matched by agent ID.

If an agent is renamed — its .md file is renamed from `fd-old-name.md` to `fd-new-name.md` — scan-fleet.sh will:
1. Discover `fd-new-name` as a new agent with no existing curated fields → writes scaffold with defaults.
2. Not find `fd-old-name` in the filesystem → leaves the old entry untouched (per current unspecified behavior) or removes it.

The curated capabilities that were hand-authored for `fd-old-name` are silently orphaned. There is no mechanism to detect that `fd-old-name` and `fd-new-name` are the same agent. This is expected behavior for a static registry, but it should be explicitly documented as a known limitation and the `--dry-run` output should highlight new entries that appear alongside orphaned entries of the same category, making the rename pattern recognizable.

This is a correctness concern for the data lifecycle, not for the runtime behavior of a single scan.

**Required fix:**

- Document this limitation explicitly in scan-fleet.sh's `--help` output and in F1's schema comment.
- The `--dry-run` output should separately list: agents added, agents updated, agents not found (potential orphans). This makes the rename pattern visible without requiring special logic.

---

## Finding 6 — MEDIUM: JSON Schema validating YAML — tooling compatibility is underspecified

**Area:** F1 schema validation

**The problem:**

The plan says "validates with yq + ajv or python jsonschema." This is two different validation paths with different behavior:

**yq + ajv:** yq v4 does not have built-in JSON Schema validation. The workflow would be: `yq -o=json fleet-registry.yaml | ajv validate -s fleet-registry.schema.json -d /dev/stdin`. This requires both yq and ajv (npm package) to be installed. ajv is not listed as a dependency in the plan.

**python jsonschema:** `yq -o=json fleet-registry.yaml | python3 -m jsonschema --instance /dev/stdin fleet-registry.schema.json`. This requires `jsonschema` Python package (installable via `uv run`). The `--instance` flag reads from stdin in newer versions but from a file path in older versions; the exact version matters.

Neither path is the same as how agency-spec.schema.json is currently validated (the existing schema uses draft-07, which jsonschema Python handles correctly, but the plan does not specify a draft version for fleet-registry.schema.json).

**Specific gotcha:** YAML integers and floats are not validated as JSON numbers when round-tripped through yq to JSON unless yq emits them without quotes. The `cold_start_tokens` field (integer) may be emitted as a JSON string `"800"` by some yq output modes, causing JSON Schema `type: integer` validation to fail spuriously. The agency-spec.schema.json avoids this by using `type: string` for all numeric-looking fields (like `version`), but for `cold_start_tokens` being used in numeric comparisons, `type: integer` is the correct schema type.

**Required fix:**

- Pick one validation path and list the tool as a dependency (recommend `python3 -m jsonschema` with `uv run`; consistent with existing project tooling).
- Specify the JSON Schema draft version in the schema's `$schema` field (use draft-07, matching agency-spec.schema.json).
- Test the round-trip explicitly: `yq -o=json fleet-registry.yaml | python3 -m jsonschema ...` in the F4 bats tests, not just "schema validates" as a manual acceptance step.
- Add a test case with a `cold_start_tokens` value to verify it survives the YAML→JSON round-trip as a number, not a string.

---

## Finding 7 — MEDIUM: fleet_check_coverage return code contract is ambiguous under partial coverage

**Area:** F3 lib-fleet.sh, fleet_check_coverage

**The problem:**

The plan specifies: "fleet_check_coverage returns 0 when covered, 1 when missing." The function signature is `fleet_check_coverage <capability...>`. For a single missing capability from a list of three, the semantics are underspecified:

- Does it return 1 on any missing capability (AND semantics — all must be covered)?
- Does it return 0 if at least one capability is covered (OR semantics)?
- Does it return a count of missing capabilities as the exit code?

The C3 Composer will use this function to decide whether a stage can run. The sprint pipeline uses it to validate agent availability before committing to a work unit. If the semantics are AND (all required capabilities must be covered) and the implementation uses OR, C3 may dispatch stages that lack a required capability.

This is not a test coverage gap; the test plan includes a `fleet_check_coverage` test. The gap is that the test plan only tests the binary case (covered vs missing), not partial coverage. The function contract must be stated in the implementation before tests are written.

**Required fix:**

- Define the contract explicitly in lib-fleet.sh's function comment: "Returns 0 if ALL listed capabilities are covered by at least one available agent. Returns 1 if ANY listed capability has no covering agent. Prints uncovered capabilities to stdout."
- Add a test case: `fleet_check_coverage covered_cap missing_cap` where `covered_cap` exists and `missing_cap` does not — must return 1 and print `missing_cap`.

---

## Finding 8 — LOW: The _FLEET_LOADED guard interacts badly with subshell invocation of lib-fleet functions

**Area:** F3 lib-fleet.sh, sourcing model

**The problem:**

The plan says the library is "sourced by sprint pipeline, flux-drive triage, and future C3 Composer." In the sprint pipeline (a bash script), sourcing lib-fleet.sh works as expected. But flux-drive triage is invoked from within Claude Code's tool environment, where each tool call may spawn a fresh subshell depending on how the pipeline invokes individual steps.

If flux-drive triage runs as `bash -c "source lib-fleet.sh; fleet_by_category review"`, `_FLEET_LOADED` is not inherited from the parent environment (bash subshells do not inherit non-exported variables). The guard will not fire, and the library will re-initialize on every call — which is correct behavior, but it means `declare -g` variables in lib-fleet.sh must not assume they persist across invocations.

lib-routing.sh uses `declare -g` for its cache variables. This is correct in the sourcing model but will cause subtle bugs if lib-fleet.sh is ever invoked in a subshell with `export _FLEET_LOADED=1` — the guard fires but the `declare -g` associative arrays are not exported and are empty.

**Required fix:**

- Export `_FLEET_LOADED` so subshell-sourcing chains work correctly: `export _FLEET_LOADED=1`.
- Document in lib-fleet.sh's header comment: "Source this file; do not invoke in subshells expecting parent state. Each subshell source will re-initialize from registry file."
- In tests, use the subshell pattern `run bash -c "source lib-fleet.sh; fleet_list"` to verify initialization succeeds in a fresh environment (same pattern used in lib-routing bats tests).

---

## Test Coverage Gaps

Beyond the individual findings above, the F4 test plan has these specific missing cases:

### Missing: stale-entry / ghost-agent test for scan-fleet.sh

The plan tests "Mock plugin directory with 3 agents → generates valid registry" and "Merge mode preserves hand-curated fields." It does not test: "Mock directory with 2 agents (one removed from previous scan) → stale entry is tombstoned/removed/flagged." This is the most important correctness property of the merge and is untested.

### Missing: yq not installed test

The plan says "Scripts should check `command -v yq` and fail with a clear message." There is no test that verifies this behavior. In a bats test, this can be simulated by `PATH=/usr/bin:/bin` (excluding `~/.local/bin`) or by temporarily renaming yq.

### Missing: concurrent read during write test for `--in-place` flag

scan-fleet.sh's `--in-place` flag writes to fleet-registry.yaml directly. If the sprint pipeline reads fleet-registry.yaml (via lib-fleet.sh) while scan-fleet.sh is writing it, the reader may see a partial file. This is a narrow window but real. The fix is for scan-fleet.sh to write to a temp file and atomically rename: `mv fleet-registry.yaml.tmp fleet-registry.yaml`. No test verifies this atomic rename behavior.

### Missing: FLEET_FORMAT=json output test

The plan specifies `FLEET_FORMAT=json` for JSON output from all functions. None of the planned tests exercise this mode. The Composer will likely consume JSON output. A test must verify that `FLEET_FORMAT=json fleet_by_category review` produces valid JSON with the correct structure.

### Missing: registry with zero agents test

`fleet_list` on an empty `agents: {}` block. yq returns an empty YAML document. The function must return exit 0 with empty output, not exit 1. Not tested.

### Missing: agent ID with dots or special characters

The plan's schema shows IDs like `fd-architecture`. If a project-local agent has an ID containing a dot (possible from flux-gen-generated files), yq map key access by that ID requires quoting in the yq expression. Not tested.

---

## Summary of Required Fixes (Prioritized)

| # | Severity | Fix |
|---|----------|-----|
| 1 | HIGH | Define and implement a stale-entry policy (tombstone or prune). No silent ghost entries. |
| 2 | HIGH | Frontmatter extraction: handle missing frontmatter, validate extracted name is non-empty, wrap yq in per-call error handling. |
| 3 | HIGH | `_FLEET_LOADED` guard must compare cached path vs current resolution; tests must `unset _FLEET_LOADED` in setup(). |
| 4 | MEDIUM | yq invocation: pass user values via `--arg`, not interpolation; explicit numeric casting for budget queries; fail clearly when registry is absent. |
| 5 | MEDIUM | Document rename/reparent limitation; `--dry-run` must show adds, updates, and orphans as separate lists. |
| 6 | MEDIUM | Specify one validation toolchain; ensure `cold_start_tokens` survives YAML→JSON round-trip as integer; add round-trip test. |
| 7 | MEDIUM | Define `fleet_check_coverage` AND/OR semantics in code comment; add partial-coverage test. |
| 8 | LOW | Export `_FLEET_LOADED`; add subshell invocation test; document sourcing model limitations. |

---

## Patterns from lib-routing.sh to Replicate (Do Not Diverge From)

lib-routing.sh established correct patterns for this problem domain. lib-fleet.sh should replicate them exactly:

- Config path resolution order: env var → script-relative → CLAVAIN_SOURCE_DIR → plugin cache
- Guard variable naming: `_FLEET_LOADED` at bottom of file (like `_ROUTING_LOADED=1` at line 680)
- Cache invalidation: `_FLEET_CACHE_POPULATED` separate from `_FLEET_LOADED`
- Malformed-config warning to stderr (lib-routing.sh line 313-315)
- Test helper `_source_fleet()` with `unset _FLEET_LOADED` + `export CLAVAIN_FLEET_CONFIG=...`

The existing routing tests at `tests/shell/test_routing.bats` are the correct template for F4.
