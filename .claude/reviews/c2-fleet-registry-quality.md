# Quality Review: C2 Fleet Registry Plan
**Plan:** `os/clavain/docs/plans/2026-02-22-c2-fleet-registry.md`
**Reviewer:** Flux-drive Quality & Style Reviewer
**Date:** 2026-02-22
**Scope:** Shell (Bash), YAML, bats tests

---

## Summary

The plan is well-structured and mostly sound. The lib-fleet.sh API design follows lib-routing.sh conventions closely. There are five areas requiring attention before implementation: naming inconsistency in one function, the yq dependency handling strategy needs to be made concrete, the test fixture coverage has a gap for the cost functions, the scan-fleet.sh frontmatter extraction approach is fragile, and the `source lib-fleet.sh` usage example in the API docs will not work without a path.

---

## 1. Naming Conventions

**Finding: Consistent with lib-routing.sh patterns — no renames needed.**

The `fleet_` prefix mirrors the `routing_` prefix from lib-routing.sh. The function names map cleanly:

| lib-routing.sh | lib-fleet.sh (planned) | Verdict |
|---|---|---|
| `routing_resolve_model` | `fleet_list` | consistent style |
| `routing_resolve_dispatch_tier` | `fleet_get` | consistent style |
| `routing_list_mappings` | `fleet_by_category` | consistent style |

The `fleet_by_*` pattern is idiomatic for filter functions in this codebase. No renaming issues found.

**One concern:** The internal guard variable is named `_FLEET_LOADED` in the plan. lib-routing.sh uses `_ROUTING_LOADED`. This is consistent with the pattern (prefix matches the library name). Confirm `_FLEET_LOADED` is unset in test `setup()` — this is easy to miss because test_routing.bats explicitly does `unset _ROUTING_LOADED` in setup and in `_source_routing()`. The equivalent for lib-fleet.sh must do `unset _FLEET_LOADED` in both places, or tests will share state across cases.

---

## 2. Shell Scripting Quality

### 2a. yq path not in default PATH — scripts will silently fail or need explicit handling

yq is installed at `~/.local/bin/yq`, which is not in every shell's PATH (particularly in bats test processes, subshells spawned by the pipeline, and codex/Claude Code hook contexts). The plan says "Scripts should check `command -v yq` and fail with a clear message," which is correct, but this needs to be concrete in the implementation:

```bash
# Required at the top of lib-fleet.sh and scan-fleet.sh
_fleet_require_yq() {
  if ! command -v yq >/dev/null 2>&1; then
    echo "lib-fleet: yq not found. Install from https://github.com/mikefarah/yq or add ~/.local/bin to PATH." >&2
    return 1
  fi
}
```

The plan currently says the check should exist but does not specify where it lives (each function? once at load time? a shared helper?). Recommend: check once at library load time inside `_fleet_load_cache` (or equivalent), fail early with a clear message pointing at the install path. Do not re-check on every function call — that would add overhead and clutter.

### 2b. No fallback for yq absence — by design, but document explicitly

lib-routing.sh works without yq because it uses a hand-rolled line-by-line parser. lib-fleet.sh will hard-depend on yq. This is acceptable (the plan explicitly notes yq was just installed for this purpose), but the non-goal list should say "no yq fallback" explicitly so no implementer adds one. Currently the plan is silent on this.

Recommend adding to the Non-goals section:
```
- **No yq fallback parser** — lib-fleet.sh hard-depends on yq v4+; fail fast if absent.
```

### 2c. scan-fleet.sh frontmatter extraction is fragile

The plan specifies:
```
Frontmatter extraction: sed -n '/^---$/,/^---$/p' + yq for parsing
```

This sed pattern has a known pitfall: it matches the first `---` and the **second** `---`, which means it will include the opening delimiter and the closing delimiter in the output. Running `yq` on that output will see the first `---` as a document separator and may emit warnings or parse the content as a new document depending on the yq version.

The correct pattern for extracting frontmatter content (excluding the delimiters) is:
```bash
# Extract content between first --- and second --- (exclusive of delimiters)
awk '/^---$/{f=!f; next} f{print}' "$agent_file" | head -50
```

Or with sed:
```bash
sed -n '1{/^---$/!q}; 2,/^---$/{ /^---$/d; p }' "$agent_file"
```

The awk version is clearer and safer. Either way, the plan should specify the exact extraction method rather than leaving it ambiguous — the implementer hitting this during F2 will waste time debugging yq parse errors on frontmatter with the delimiters included.

### 2d. scan-fleet.sh --in-place flag needs atomicity

The plan mentions `--in-place` as a flag that updates fleet-registry.yaml directly. Overwriting a YAML config in place without an atomic write risks corrupting the file if the script is interrupted. Recommend writing to a temp file and using `mv`:

```bash
# Instead of: yq ... > fleet-registry.yaml
tmpfile="$(mktemp)"
generate_registry > "$tmpfile"
mv "$tmpfile" "$fleet_registry_path"
```

This is a correctness concern, not just style. If scan-fleet.sh is run in a hook or pipeline and interrupted, the registry becomes empty or truncated.

### 2e. FLEET_FORMAT=json output control — potential IFS/quoting risk

The plan specifies `Set FLEET_FORMAT=json for JSON output`. When functions conditionally pipe through `yq -o json`, ensure that the yq invocation is not subject to word splitting on the filter expression. This is low risk but worth noting in the implementation: always quote yq filter strings.

### 2f. Missing strict mode recommendation

lib-routing.sh does not use `set -euo pipefail` — it is a sourced library, and strict mode in sourced files can cause unexpected exits in the parent shell. lib-fleet.sh should follow the same convention: no `set -euo pipefail` at the top level. However, scan-fleet.sh is an executable script and SHOULD use `set -euo pipefail`. The plan does not mention this. Add it to the F2 implementation note.

---

## 3. Test Strategy

### 3a. 5-agent fixture is sufficient — but one gap exists

The fixture coverage plan (2 review, 2 research, 1 workflow) covers all the query paths tested:
- `fleet_by_category` — 3 categories represented
- `fleet_by_capability` — needs at least 2 agents sharing a capability
- `fleet_within_budget` — needs agents on both sides of the budget threshold
- `fleet_check_coverage` — needs covered and uncovered capability

**Gap:** `fleet_by_source` and `fleet_cost_estimate` are in the public API (8 functions listed) but are not mentioned in the test plan. The test list covers 6 of 8 functions. Add at least one test for each missing function:

```
- fleet_by_source returns correct subset when fixture has agents from 2+ sources
- fleet_cost_estimate returns cold_start_tokens for a known agent
```

Since `fleet_cost_estimate` feeds `fleet_within_budget`, it is implicitly tested but should have a direct unit test.

### 3b. Setup/teardown pattern — confirm env var override is used

test_routing.bats uses `CLAVAIN_ROUTING_CONFIG` to inject a test fixture path. lib-fleet.sh needs an equivalent: `CLAVAIN_FLEET_CONFIG` (or similar) so tests can point at the fixture registry without relying on the script-relative discovery path. The plan does not name this env var. Recommend naming it `CLAVAIN_FLEET_REGISTRY` to match the file being referenced (`fleet-registry.yaml`) and document it in the public API block.

### 3c. scan-fleet.sh merge mode test is underspecified

The test plan says "Merge mode preserves hand-curated fields." This requires a fixture that has pre-existing hand-curated fields (`capabilities`, `models`, `cold_start_tokens`) and a scan result that would overwrite them — then the test asserts the curated fields survive. The plan does not specify what the pre-existing fixture looks like for this case. Add a note that the merge test needs two inputs: a "before" registry with curated fields and a mock agent directory that produces different auto-generated fields.

### 3d. No test for `_fleet_require_yq` failure path

The plan mentions the yq check but does not include a test for it. Add a test:
```bash
@test "lib-fleet fails with clear message when yq is absent" {
    run bash -c "PATH=/usr/bin:/bin source '$SCRIPTS_DIR/lib-fleet.sh' && fleet_list"
    [[ "$status" -ne 0 ]]
    [[ "$output" == *"yq not found"* ]]
}
```
This requires temporarily removing yq from PATH in the test process, which is straightforward with PATH manipulation.

---

## 4. yq as a New Dependency

### 4a. PATH is the primary risk

`~/.local/bin/yq` will not be in PATH for:
- bats test processes (unless the test environment inherits the developer's shell config)
- Claude Code hooks (which run in a sanitized environment)
- Any codex/dispatch subprocess that does not source `.bashrc`

Recommend that lib-fleet.sh prepend `~/.local/bin` to PATH if yq is not found via `command -v`:

```bash
_fleet_require_yq() {
  if ! command -v yq >/dev/null 2>&1; then
    # Try the known install location before failing
    if [[ -x "${HOME}/.local/bin/yq" ]]; then
      export PATH="${HOME}/.local/bin:${PATH}"
    else
      echo "lib-fleet: yq not found. Install: https://github.com/mikefarah/yq" >&2
      return 1
    fi
  fi
}
```

This is more robust than a hard failure when the binary exists but PATH is not set up.

### 4b. No fallback is correct — but version should be checked

The plan targets yq v4.52.4. The yq v4 API is incompatible with the older v3/v2 API (different filter syntax). If a system has an older yq installed, the library will fail with cryptic parse errors rather than a clear version message. A version check at load time is low cost:

```bash
_fleet_check_yq_version() {
  local ver
  ver="$(yq --version 2>&1 | grep -oE 'v[0-9]+' | head -1)"
  if [[ "$ver" != "v4" ]]; then
    echo "lib-fleet: yq v4 required (found ${ver:-unknown}). Install from https://github.com/mikefarah/yq" >&2
    return 1
  fi
}
```

This is a one-time check that prevents silent misbehavior with older yq installs.

### 4c. scan-fleet.sh should document the yq v4 filter syntax used

scan-fleet.sh is the first script to do YAML generation with yq (not just querying). The merge logic will use yq's `*+` merge operator or `env()` for injecting values. These are yq v4-specific. A comment block at the top of scan-fleet.sh should document the yq version requirement and the specific operators used, so future maintainers know which yq features are load-bearing.

---

## 5. Documentation Quality

### 5a. Public API block is sufficient but missing the env var override

The API block in the plan documents all 8 functions clearly with their output contract ("All functions output agent IDs newline-separated unless noted"). This is good. One omission: the config-finding path and the env var override are not documented. Add to the API block:

```bash
# Config resolution (same pattern as lib-routing.sh):
#   1. CLAVAIN_FLEET_REGISTRY env var (for testing/override)
#   2. Script-relative: ../config/fleet-registry.yaml
#   3. CLAVAIN_SOURCE_DIR/config/fleet-registry.yaml
#   4. Plugin cache: ~/.claude/plugins/cache/*/clavain/*/config/fleet-registry.yaml
```

This is necessary because callers (C3 Composer, sprint pipeline) need to know how to inject a different registry path in tests and CI.

### 5b. fleet_check_coverage return value semantics need a concrete example

The plan says "returns 0 when covered, 1 when missing." This is correct Unix semantics (0 = success = covered), but it is easy to invert. Add a concrete example to the API block:

```bash
# fleet_check_coverage domain_review multi_perspective
# → exit 0 if all capabilities are covered by at least one agent
# → exit 1 if any capability has no agent; prints missing capabilities to stderr
```

### 5c. fleet_get output format is underspecified

The plan says `fleet_get outputs full YAML block`. For the C3 Composer to consume this, the output format matters: does it output the agent as a top-level YAML document, or as a nested block under the agent ID key? This should be specified:

```yaml
# fleet_get fd-architecture outputs:
source: interflux
category: review
capabilities:
  - domain_review
# (agent ID key is NOT included — caller already has the ID)
```

Or alternatively the full subtree under the agent key. Either is fine, but the plan should commit to one form.

### 5d. FLEET_FORMAT=json is mentioned but not specified further

Is `FLEET_FORMAT=json` honored by all functions or only `fleet_get`? The plan says "All functions output agent IDs (newline-separated) unless noted. fleet_get outputs full YAML block. Set FLEET_FORMAT=json for JSON output." This implies json format applies to `fleet_get` output — but does it also change the newline-separated ID lists to a JSON array? Clarify in the API doc.

---

## 6. Minor Items

- **F1 acceptance criterion** uses `yq '.agents | keys | length'` — the correct yq v4 expression is `yq '.agents | keys | length'` which does work in v4, but only if the top-level key is `agents`. Confirm the schema uses `agents:` at the root (the example shows this, so it is fine). No change needed.

- **Execution order** in the plan says "Practical order: F1 → F3 → F2 → F4" which differs from the diagram showing F1 → F2 and F1 → F3 in parallel. The practical order is correct (lib-fleet.sh is simpler to verify than scan-fleet.sh). This is not a defect but could confuse an implementer — the diagram should note "practical implementation order differs from dependency graph."

- **Schema validation** in F1 says "validates with yq + ajv or python jsonschema." These are two very different toolchains. Pick one (python jsonschema is already used in the project given `pyproject.toml` in the tests dir) and specify it. Leaving it as "or" means the implementer makes an undocumented choice.

---

## Verdict

The plan is implementable as written. Fix the yq PATH handling and version check before starting F3 — these will cause silent failures in test and CI contexts if left as stated. The test gap for `fleet_by_source` and `fleet_cost_estimate` should be filled in F4. The frontmatter extraction pattern needs to be corrected in F2 before implementation to avoid debugging time. The documentation gaps are low priority but should be resolved before C3 Composer integration begins.

**Required fixes before implementation:**
1. Name the env var override (`CLAVAIN_FLEET_REGISTRY`) in the plan and API doc
2. Specify the yq PATH/version check strategy concretely
3. Correct the frontmatter extraction sed pattern (or switch to awk)
4. Add `fleet_by_source` and `fleet_cost_estimate` to the F4 test list
5. Add `set -euo pipefail` to scan-fleet.sh (executable script, not library)
6. Specify atomic write for `--in-place` in scan-fleet.sh

**Nice-to-have before C3 integration:**
1. Specify `fleet_get` output format (with or without agent ID key)
2. Clarify `FLEET_FORMAT=json` scope
3. Choose one schema validation tool (recommend python jsonschema)
