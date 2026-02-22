# Quality & Style Review: PRD 2026-02-21-static-routing-table.md

**Reviewed by:** Flux-drive Quality & Style Reviewer
**Date:** 2026-02-21
**Document:** `/root/projects/Interverse/docs/prds/2026-02-21-static-routing-table.md`
**Brainstorm reference:** `/root/projects/Interverse/os/clavain/docs/brainstorms/2026-02-20-static-routing-table-brainstorm.md`
**Languages in scope:** Shell (Bash), YAML

---

## Summary

The PRD is well-structured and the brainstorm it derives from is thoughtful. However, there are meaningful divergences between the brainstorm's schema and the PRD's acceptance criteria that will create implementation confusion. The function names proposed in the PRD are inconsistent with the codebase's naming pattern. The `profiles:` section introduces YAML nesting depth that the documented line-by-line parser cannot handle without a non-trivial extension. These issues are concrete blockers for an implementer reading only the PRD.

---

## Finding 1 — Schema Mismatch: PRD Invents `categories:`, `profiles:`, and `overrides:` at Top Level; Brainstorm Has a Different Structure

**Severity: HIGH — will cause implementation divergence**

### Detail

The PRD (F1) defines this top-level schema:

```yaml
phases:      # phase-name → model tier
categories:  # category-name → default model
overrides:   # agent-name → model
profiles:    # named profile → (economy, quality, custom)
```

The brainstorm (the agreed-upon design) defines a structurally different schema:

```yaml
defaults:
  model: sonnet
  categories:
    research: haiku
    review: sonnet
phases:
  brainstorm:
    model: opus
    categories:
      research: haiku
dispatch:
  tiers: ...
  fallback: ...
overrides: {}
```

The differences are:
1. `categories:` in the PRD is a flat top-level section. In the brainstorm, categories live nested under `defaults:` and optionally under each `phases:<name>:` block. The brainstorm's design is more powerful (per-phase category overrides) and is the design the shell library would need to implement.
2. `profiles:` does not appear in the brainstorm at all. The brainstorm explicitly says `/clavain:model-routing economy` writes to `defaults:`, not to a profile selector. The PRD's F4 implies a `routing_active_profile` getter exists, which requires a top-level `active_profile:` field or similar mechanism — none of which is in the brainstorm schema.
3. The brainstorm schema includes `dispatch:` as a first-class section (replacing `tiers.yaml`). The PRD's F1 schema mentions neither `dispatch:` nor migration of `tiers.yaml`. The PRD's F3 says `dispatch.sh` consults routing.yaml for phase-to-model, but the dependency section says "routing.yaml extends but does not replace" `tiers.yaml`. This contradicts the brainstorm's Key Decision 2 ("The dispatch: section replaces tiers.yaml").

**Fix:** The PRD should commit to one schema — either the brainstorm's nested-inheritance schema or the PRD's flat schema — and state explicitly whether `tiers.yaml` is migrated into `routing.yaml` or remains separate. The brainstorm schema is the better design (it supports per-phase category overrides and is the basis the shell library must parse). The PRD's flat schema loses that capability.

---

## Finding 2 — Function Naming: `routing_active_profile` Breaks the Codebase Convention

**Severity: MEDIUM — naming inconsistency that will outlive this PR**

### Detail

The codebase uses a consistent `<module>_<verb>_<noun>` pattern for all lib-*.sh functions:

```
sprint_find_active      sprint_read_state     sprint_set_artifact
intercore_run_advance   intercore_run_create  intercore_dispatch_spawn
verdict_parse_all       verdict_count_by_status
checkpoint_step_done    checkpoint_validate
```

The PRD proposes `routing_active_profile` (F2), which is `<module>_<adjective>_<noun>` — inverted verb-noun order with an adjective. Every other function in the codebase uses verb-first: `read_`, `find_`, `get_`, `set_`, `list_`, `resolve_`, `check_`, `write_`, `parse_`, `count_`.

The other two proposed functions follow the convention correctly:
- `routing_resolve_model` — correct (`resolve` is the verb)
- `routing_list_mappings` — correct (`list` is the verb)

**Fix:** Rename `routing_active_profile` to `routing_get_active_profile` to match the verb-first pattern.

---

## Finding 3 — Parser Complexity: Nested `profiles:` Section Cannot Be Handled by the Existing Line-by-Line Pattern

**Severity: HIGH — implementation risk**

### Detail

The existing line-by-line parser in `dispatch.sh` (`resolve_tier_model`) handles exactly 3 levels of YAML depth:

```
tiers:          ← level 1: section sentinel
  fast:         ← level 2: tier name block
    model: ...  ← level 3: scalar value
```

The parser tracks two boolean state flags (`in_tiers`, `in_tier`) and breaks on sibling keys. This is manageable.

The PRD's `profiles:` section (F1) requires parsing 4 levels minimum:

```
profiles:         ← level 1: section sentinel
  economy:        ← level 2: profile name block
    categories:   ← level 3: nested object
      research: haiku  ← level 4: scalar value
```

And if profiles mirror the brainstorm's per-phase category overrides, 5 levels:

```
profiles:
  economy:
    phases:
      brainstorm:
        categories:
          research: haiku   ← level 6
```

The existing parser cannot handle this. Each additional nesting level requires a new boolean state flag and a new sibling-detection branch. At 4+ levels the parser becomes a hand-rolled state machine that is error-prone, hard to test, and will silently return empty string on malformed nesting — which the PRD's acceptance criteria say is the correct fallback behavior (F2: "returns empty string when routing.yaml doesn't exist"). Silent empty-string return on malformed deep nesting is indistinguishable from missing-file return. A caller cannot tell whether routing.yaml was absent or whether the profile section had malformed indentation.

The PRD's F2 acceptance criterion "uses line-by-line YAML parsing consistent with dispatch.sh pattern" directly conflicts with F1's `profiles:` section unless profiles are designed as flat key-value blocks (no nesting inside the profile).

**Fix option A (preferred):** Restrict the `profiles:` section to flat key-value pairs only — a profile is just a named set of top-level defaults:

```yaml
profiles:
  economy: { research: haiku, review: sonnet, workflow: sonnet }
  quality: { research: inherit, review: inherit, workflow: inherit }
active_profile: economy
```

This is parseable with the existing 3-level technique. A profile is just an alternative `defaults.categories` block. The parser reads `profiles:<name>:<category>: <model>` — same depth as `tiers:<name>:model: <value>`.

**Fix option B:** Acknowledge that `profiles:` requires a more capable parser and explicitly scope the parser design in F2 to handle 4-level nesting. This is not wrong, but adds implementation complexity. Document the approach in F2's acceptance criteria rather than referencing the dispatch.sh pattern which handles only 3 levels.

---

## Finding 4 — Resolution Signature Inconsistency: PRD vs. Brainstorm API

**Severity: MEDIUM — creates confusion for the implementer**

### Detail

The PRD (F2) specifies this function signature:

```bash
routing_resolve_model <phase> <category> [agent-name]
```

Positional arguments, phase first.

The brainstorm (Key Decision 3) specifies named flags:

```bash
resolve_model --phase execute --category review
resolve_model --agent fd-architecture
```

Flag-based, making any argument optional without requiring positional-arg gymnastics (e.g., how do you call with agent-name but no category using positionals?).

The brainstorm's flag-based API is more consistent with dispatch.sh's own style (`--tier`, `--phase`, `--model`, `--inject-docs`). It also makes partial calls unambiguous: `resolve_model --agent fd-architecture` does not require passing a sentinel value for `<phase>` and `<category>`.

Additionally, the brainstorm's function is named `resolve_model`, without the `routing_` prefix, which would conflict with the codebase convention (the lib prefix should be the module namespace — calling it just `resolve_model` risks shadowing if multiple libs are sourced). The PRD correctly namespaces it as `routing_resolve_model`. The signature shape (flags vs. positionals) is the real issue.

**Fix:** Align F2's acceptance criteria to use named flags:

```bash
routing_resolve_model --phase <phase> [--category <category>] [--agent <agent-name>]
```

This is consistent with dispatch.sh's flag style, unambiguous when arguments are omitted, and readable in hook callsites: `routing_resolve_model --phase "$SPRINT_PHASE" --category review`.

---

## Finding 5 — Naming Gap: `profiles:` Feature Is Described in F1 and F4 but Has No Corresponding Acceptance Criterion in F2

**Severity: MEDIUM — completeness gap**

### Detail

F1 acceptance criterion 5 says: "Supports `profiles:` section defining named routing profiles (e.g., economy, quality) that can be activated."

F4 says: `/model-routing economy` reads the `economy` profile from routing.yaml.

F4 also adds `/model-routing <custom-profile>` as a new subcommand.

However, F2 (Config Reader Library) has no acceptance criterion for:
- Reading the `active_profile:` field (or whatever mechanism activates a profile)
- Layering a profile's values into the resolution chain
- What resolution priority a profile has (does it override `phases:`? override `defaults:`? sit between them?)

F2 mentions `routing_active_profile` returns the active profile name, but does not specify:
- Whether "active profile" is stored in routing.yaml as `active_profile: economy`
- Or in a runtime state file (like an env var or beads state key)
- What happens when `routing_resolve_model` is called and an active profile is set — does it use the profile's values instead of `defaults:`?

Without this, F2 is underspecified for any implementation that touches profiles.

**Fix:** Add to F2:
- An acceptance criterion for how the active profile is stored and read (in-file vs. state file — and justify the choice given the PRD says the file is declarative config, not mutable runtime state)
- An acceptance criterion that specifies the resolution order including profiles: per-agent override > phase > active profile > defaults > fallback
- Clarify whether `routing_active_profile` reads from the YAML file (`active_profile:` key) or from beads/environment state

---

## Finding 6 — Caching Claim Is Unimplementable as Written

**Severity: LOW — acceptance criterion needs clarification**

### Detail

F2 states: "Caches parsed config for the duration of a single function call (no redundant file reads within one resolution)."

"The duration of a single function call" is the wrong caching boundary. A single call to `routing_resolve_model` reads the file once by definition (there is no recursion). The meaningful caching concern is: if `dispatch.sh` calls `routing_resolve_model` multiple times (once per dispatched agent), should the file be re-read each time?

The brainstorm parser in dispatch.sh has no caching — each call to `resolve_tier_model` re-reads `tiers.yaml`. That is acceptable because the file is small and dispatch is not called in a tight loop.

If the intent is "within a single shell script execution (e.g., a hook that calls routing_resolve_model for N agents), parse the file once," then caching requires a global associative array populated on first call:

```bash
declare -A _ROUTING_CACHE
_routing_load_once() {
  [[ -n "${_ROUTING_CACHE[loaded]:-}" ]] && return 0
  # ... parse routing.yaml into _ROUTING_CACHE ...
  _ROUTING_CACHE[loaded]=1
}
```

This is the correct pattern (same as `_SPRINT_LOADED=1` guard in lib-sprint.sh).

**Fix:** Change the acceptance criterion to: "Parses routing.yaml once per shell process execution; uses a global associative array cache so N calls within one hook/script do not cause N file reads."

---

## Finding 7 — `--phase` Flag Name in Dispatch.sh Conflicts with Codex's Own Flag Namespace

**Severity: LOW — worth noting before implementation**

### Detail

F3 says `dispatch.sh` accepts a new `--phase <name>` flag. The current `dispatch.sh` argument parser passes unknown flags through to `codex exec` via `EXTRA_ARGS`. The flag-passthrough code at lines 354-358 currently passes unrecognized flags through:

```bash
-*)
  # Unknown flag — pass through as boolean (no value consumed)
  EXTRA_ARGS+=("$1")
  shift
```

If Codex CLI ever adds a `--phase` flag of its own (it is a plausible addition for model routing or experiment tracking), the dispatch.sh parser would intercept it before Codex sees it — breaking passthrough. This is a latent namespace collision.

This is minor because Codex's flag namespace is not currently documented as including `--phase`, but it is worth noting in the PRD as a known risk.

**Fix:** Note in F3's implementation notes that `--phase` must be consumed by dispatch.sh before the passthrough block, which is already how `--tier` is handled. No schema change needed; just implementation care.

---

## Finding 8 — `routing.yaml` Location Question Is Left Open but the Answer Is Implied

**Severity: LOW — open question that should be closed**

### Detail

The PRD's Open Questions section asks: "Should routing.yaml live at `config/routing.yaml` (alongside dispatch tiers) or at project root?"

The brainstorm answers this: it places the file at `config/routing.yaml` and the brainstorm's Key Decision 2 explicitly migrates `tiers.yaml` into `routing.yaml` (same `config/` directory). The `dispatch.sh` file-discovery logic (lines 183-189) already knows how to find `config/dispatch/tiers.yaml` relative to the script directory. The same pattern would apply to `config/routing.yaml`.

This is not a genuine open question — it was decided in the brainstorm. The PRD should close it.

**Fix:** Remove from Open Questions. State as decided: `config/routing.yaml`, alongside `config/dispatch/tiers.yaml` (or replacing it per brainstorm Key Decision 2).

---

## Summary Table

| # | Finding | Severity | Area |
|---|---------|----------|------|
| 1 | Schema mismatch between PRD (flat sections) and brainstorm (nested inheritance) | HIGH | F1 schema |
| 2 | `routing_active_profile` breaks verb-first naming convention | MEDIUM | F2 naming |
| 3 | `profiles:` nesting depth exceeds what line-by-line parser can handle | HIGH | F1/F2 parser |
| 4 | Positional arg signature vs. brainstorm's named-flag API | MEDIUM | F2 API |
| 5 | F2 has no acceptance criteria for profile-in-resolution-chain behavior | MEDIUM | F2 completeness |
| 6 | Caching criterion describes wrong boundary ("single function call") | LOW | F2 correctness |
| 7 | `--phase` flag risk: latent Codex flag namespace collision | LOW | F3 risk |
| 8 | Open question about `config/` location is already answered by brainstorm | LOW | F1 completeness |

---

## What Does Not Need Changing

- The zero-fallback-on-missing-file design (F2: "returns empty string when routing.yaml doesn't exist") is correct and consistent with how `resolve_tier_model` in dispatch.sh handles missing `tiers.yaml`.
- `routing_list_mappings` and the intent of `routing_resolve_model` are good names; only the third function and signature shape need adjustment.
- The resolution priority order (per-agent override > phase-specific > category default > fallback) stated in F2 is correct and consistent with the brainstorm.
- F3's "when `--phase` is NOT provided, behavior is identical to current" is the right backward-compatibility guarantee.
- F4's `/model-routing <custom-profile>` generalization is a good extension of the existing `economy`/`quality` binary.
