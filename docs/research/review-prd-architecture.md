# Architecture Review: Static Routing Table PRD (B1)

**Reviewed:** 2026-02-21
**Document:** `docs/prds/2026-02-21-static-routing-table.md`
**Reviewer:** Flux-drive Architecture & Design Reviewer (Sonnet 4.6)
**Focus Areas:** Module boundaries, coupling, design patterns, anti-patterns, unnecessary complexity

---

## Summary

The PRD addresses a real and legitimate pain point: two independent routing systems with hardcoded policy. The core direction — declarative config, shell library, backward-compatible integration — is sound. However, the PRD carries one significant structural conflict, one unnecessary scope creep item, and one under-specified integration that will create debugging confusion at implementation time. These are fixable before work begins.

---

## 1. Boundaries & Coupling

### Finding 1 — CRITICAL: routing.yaml and tiers.yaml Govern Different Namespaces, But the PRD Conflates Their Output Types

**Location:** F1 schema, F3 dispatch integration, dependency statement ("routing.yaml extends but does not replace this")

`tiers.yaml` maps symbolic **tier names** (`fast`, `deep`, `fast-clavain`, `deep-clavain`) to **concrete Codex model strings** (`gpt-5.3-codex-spark`). The tier names are stable abstractions that insulate callers from model churn. This is a Codex CLI concern.

The PRD's `routing.yaml` maps phases and categories to values described with Claude model aliases (e.g., `brainstorm: opus`, `execute: sonnet`). These are Claude subagent model names, not Codex tier names. The two files operate in different namespaces for different runtimes.

This is structurally fine if the two systems stay separate. The problem is F3, which states that `dispatch.sh` should "consult routing.yaml for phase-aware tier selection." This means `lib-routing.sh` must return something that tiers.yaml and `dispatch.sh` understand — a Codex tier name (`fast`, `deep`) — not a Claude alias (`opus`, `sonnet`). But F4 applies the same `routing.yaml` to Claude subagent frontmatter, where the correct values are Claude model names, not Codex tier names.

Under the single-file design, `routing.yaml` must either:
- (A) Use Claude model names (`opus`, `sonnet`, `haiku`) — then F3 dispatch integration requires an implicit translation to Codex tiers, which is underdefined and error-prone, or
- (B) Use Codex tier names (`fast`, `deep`) — then F4 subagent integration must translate back to Claude model names, and the translation table lives nowhere specified.

The PRD says the config "extends but does not replace" tiers.yaml but does not define what values `routing.yaml`'s `phases:` section actually contains or how `lib-routing.sh` maps its output to each caller's requirement. "Extends but does not replace" is a design gesture, not a specification.

**What to fix.**

Split `routing.yaml` into two explicitly namespaced sections with documented value types:

```yaml
# config/routing.yaml

# For Claude subagents — values are Claude model aliases (haiku, sonnet, opus, inherit)
subagents:
  phases:
    brainstorm: opus
    execute: sonnet
  categories:
    research: haiku
    review: sonnet
  overrides:
    fd-safety: opus

# For Codex dispatch — values are tier names from config/dispatch/tiers.yaml
dispatch:
  phases:
    brainstorm: deep
    execute: fast
    review: fast
```

`lib-routing.sh` exposes two distinct resolver functions:
- `routing_resolve_subagent_model <phase> <category> [agent]` — returns a Claude model name consumed by `/model-routing`
- `routing_resolve_dispatch_tier <phase>` — returns a Codex tier name consumed by `dispatch.sh`

This makes the namespace boundary explicit, eliminates translation ambiguity, and preserves each caller's existing vocabulary.

---

### Finding 2 — MODERATE: Interserve-Mode Tier Remapping Creates Invisible Context-Dependence in routing.yaml Outputs

**Location:** F3 acceptance criteria — "resolves model from routing.yaml before falling back to `--tier`"

`dispatch.sh` already has a silent post-resolution remapping step: when `CLAVAIN_DISPATCH_PROFILE=interserve`, it translates `fast` → `fast-clavain` and `deep` → `deep-clavain` inside `resolve_tier_model`. This remapping is invisible to callers.

Under the proposed flow, `dispatch.sh --phase brainstorm` would resolve `brainstorm` → `deep` (from `routing.yaml`), pass `deep` to `resolve_tier_model`, which silently remaps it to `deep-clavain` in interserve mode. A `routing.yaml` author writing `brainstorm: deep` cannot know whether "deep" will be the actual tier or a remapped variant at execution time. `routing.yaml` is supposed to be a declarative single source of truth, but its effective output becomes context-dependent on an environment variable.

**What to fix.**

Document the layer boundary explicitly in both `routing.yaml`'s inline comments and `lib-routing.sh`'s header: `routing.yaml` declares base tier names (`fast`, `deep`); interserve-mode remapping is a post-resolution step inside `dispatch.sh` and is not routing.yaml's concern. This is already how the current system works. The PRD must state this separation clearly so implementers don't accidentally route around it.

For B2/B3, if `routing.yaml` needs to express interserve-specific overrides, that can be added as a separate `dispatch.interserve_overrides:` section. Mark it out of scope for B1.

---

### Finding 3 — LOW: dispatch.sh's YAML Parser Is a Load-Bearing Implementation Detail That lib-routing.sh Must Replicate Exactly

**Location:** F2 — "Uses line-by-line YAML parsing consistent with dispatch.sh pattern"

The existing parser in `resolve_tier_model` handles three specific structural patterns in `tiers.yaml`: a top-level `tiers:` section, two-space-indented tier keys, and four-space-indented `model:` values within each tier block. It detects section exit by watching for a line that starts with a lowercase letter at column 0.

`routing.yaml` will have a more complex nested structure (`subagents:` → `phases:` → key-value pairs, `categories:` → key-value pairs, `overrides:` → key-value pairs). The existing parser's section-exit heuristic (any top-level lowercase letter terminates the current section) works because `tiers.yaml` has only two top-level sections. With `routing.yaml`'s deeper nesting, the same heuristic becomes ambiguous — `phases:` under `subagents:` looks like a top-level key to a regex that examines indentation level.

**What to fix.**

Before writing `lib-routing.sh`, write down the exact YAML shape that the file will have — including indent depths and the nesting structure — and verify that the planned parsing logic correctly handles it. Add this to the acceptance criteria: "Parsing is verified against a sample routing.yaml with all four sections populated (phases, categories, overrides, and the dispatch section)." The "consistent with dispatch.sh pattern" criterion is underspecified because `routing.yaml` is structurally more complex than `tiers.yaml`.

---

## 2. Pattern Analysis

### Finding 4 — MODERATE: lib-routing.sh Placed in `hooks/` Is a Layer Signal Violation

**Location:** F2 — "Shell library (`hooks/lib-routing.sh`)"

The existing `hooks/lib-*.sh` files are support libraries for hook execution context: `lib-sprint.sh` manages sprint state for hooks, `lib-gates.sh` provides gate checks within hooks, `lib-intercore.sh` wraps `ic` CLI calls invoked by hooks. They all exist to serve hooks (PostToolUse, SessionStart, etc.) running inside Claude Code's event model.

`lib-routing.sh` would be called by two callers that are not hooks:
1. `scripts/dispatch.sh` — a standalone shell script invoked by Codex CLI agents
2. `commands/model-routing.md` — a Claude command, not a hook

Placing `lib-routing.sh` in `hooks/` makes `dispatch.sh` depend on a path that signals "hook internals." Any future developer reading `dispatch.sh` will find `source "$SCRIPT_DIR/../hooks/lib-routing.sh"` and reasonably wonder whether this is intentional. The `hooks/` directory communicates lifecycle ownership; a shared config reader library does not belong there.

**What to fix.**

Place `lib-routing.sh` in `scripts/` alongside `dispatch.sh`. Both F3 and F4 callers can source it from there. If a hook later needs routing resolution (plausible in B2, e.g., a session-start hook that auto-applies a profile), the hook sources from `scripts/` — that direction is less surprising than the reverse.

Do not introduce a new `lib/` top-level directory for a single file. The overhead of a new directory for one library exceeds the clarity benefit; use `scripts/` for B1.

---

### Finding 5 — LOW: "Caches parsed config for the duration of a single function call" Is Not Caching

**Location:** F2 — "Caches parsed config for the duration of a single function call (no redundant file reads within one resolution)"

Any function that reads a file once to resolve a value performs no redundant reads "within one resolution" by definition. This describes normal function behavior, not caching. True caching means storing parsed state between multiple calls within the same shell process.

In practice, `dispatch.sh` calls model resolution exactly once per invocation, so multi-call caching is irrelevant for B1. The criterion as written is not testable.

**What to fix.**

Replace with a concrete criterion: "`routing_resolve_subagent_model` and `routing_resolve_dispatch_tier` read `routing.yaml` at most once per shell process by storing the parsed sections in shell variables on first call and skipping re-reads on subsequent calls within the same process." This is implementable with a standard variable-guard pattern and is the correct specification if interoperability with a future B2 hook (which calls resolution multiple times in a session) is intended.

---

## 3. Simplicity and YAGNI

### Finding 6 — MODERATE: The `profiles:` Concept Adds a State-Tracking Problem That B1 Does Not Solve

**Location:** F1 — "Supports `profiles:` section defining named routing profiles", F2 — `routing_active_profile`, F4 — `/model-routing economy|quality|<custom-profile>`

The profiles feature requires answering a question the PRD does not address: **how is the active profile persisted between invocations?**

The current `/model-routing economy` command works by physically editing agent frontmatter files with `sed`. After the command runs, the frontmatter is the state. There is no separate "active profile" concept — the files are the source of truth.

If `routing.yaml` adds a `profiles:` section and `routing_active_profile` must report the currently active profile, that selection must be stored somewhere between command invocations. The options are:

1. Written to a state file (e.g., `.clavain/routing-profile`) on each `/model-routing <profile>` call — adds a new state file with stale-on-manual-edit behavior.
2. Inferred by reading all agent frontmatter and pattern-matching against profile definitions — expensive, fragile when models are mixed.
3. Not persisted — `routing_active_profile` always returns "unknown" — making it nearly useless.

None of these are specified in the PRD. None are resolved by B1's static-config-only scope.

The profiles concept itself — named mapping sets in `routing.yaml` — is correct and should stay. Named profiles in the config file are pure data. What is premature is `routing_active_profile` (a function that queries runtime state) and the profile-name display in `/model-routing status`.

**What to fix.**

Remove `routing_active_profile` from F2's acceptance criteria. Remove the "active profile name" display from the F2 `routing_list_mappings` function and from F4's status output. The `/model-routing status` command can continue to show which model each agent currently has (the existing grep behavior), without needing to name the profile that produced it. Profile-activation tracking is a natural B2 addition when the system gains complexity-aware routing and needs to explain its current selection. Add it to the non-goals section.

---

### Finding 7 — LOW: Fallthrough Behavior When routing.yaml Exists But a Phase Is Missing Is Not Specified

**Location:** F2 — "Returns empty string (not error) when routing.yaml doesn't exist"

The PRD specifies graceful degradation when the file is entirely absent. It does not specify behavior when the file exists but the requested phase or category key is absent — which is the common partial-population case during initial adoption.

If `routing_resolve_dispatch_tier "shipping"` is called and `shipping` is not in the `dispatch.phases:` section, does the function return empty string, return the category default, or return the fallback tier? The stated resolution order (per-agent > phase > category > fallback) implies a missing phase should fall through to category, then to fallback. But this needs an explicit criterion, not an implicit reading of a priority diagram.

**What to fix.**

Add one acceptance criterion: "When the requested phase is not present in `routing.yaml`, resolution falls through to category default, then to the configured fallback value, then to empty string. A missing phase is not an error and does not log a warning."

---

## Pattern Observations (Non-Blocking)

**The line-by-line YAML parser replication is the right call for B1.** Introducing an external YAML library (`yq`, `python yaml`) adds a dependency to a shell plugin system that explicitly avoids them. The existing pattern in `resolve_tier_model` is already proven and understood by the codebase. Replicating it in `lib-routing.sh` is the correct consistency choice; see Finding 3 for the caveat about `routing.yaml`'s more complex nesting requiring the parser to handle deeper structure.

**The `--phase` flag addition to dispatch.sh is a clean, additive change.** Existing callers that do not pass `--phase` get identical behavior. This is the lowest-risk integration surface possible and the PRD correctly enforces that invariant.

**The sed-based frontmatter editing in `/model-routing` is not an architecture concern for B1.** It works, it is implicitly validated by usage, and the PRD does not propose changing the mechanism — only the source of truth for which values to apply. That is the correct scope.

**The B1 → B2 → B3 evolution path is coherent.** With the two-section `routing.yaml` structure (Finding 1), complexity-aware routing in B2 can add a resolver that reads runtime signals without changing the config schema. Adaptive routing in B3 can write back to a state file that `lib-routing.sh` consults on load. The config shape proposed in F1 does not foreclose either evolution.

---

## Verdict by Finding

| # | Severity | Finding | Required Action |
|---|----------|---------|-----------------|
| 1 | CRITICAL | routing.yaml value namespace conflicts: Claude model aliases vs. Codex tier names used by dispatch.sh | Split routing.yaml into `subagents:` and `dispatch:` sections; expose two resolver functions in lib-routing.sh |
| 2 | MODERATE | Interserve-mode tier remapping is a silent post-resolution step invisible to routing.yaml authors | Document the layer boundary explicitly; lib-routing.sh returns base tiers only; interserve remapping stays in dispatch.sh |
| 3 | LOW | routing.yaml's nested structure is more complex than tiers.yaml; the existing parsing heuristic may not generalize | Validate parser against full sample routing.yaml before implementation; add sample-validation criterion to F2 |
| 4 | MODERATE | lib-routing.sh in `hooks/` misrepresents ownership; dispatch.sh is not a hook | Move lib-routing.sh to `scripts/`; hooks source from scripts if needed in B2 |
| 5 | LOW | "Caches parsed config for the duration of a single function call" is not a testable criterion | Rewrite as a variable-guard criterion with a concrete process-scoped caching contract |
| 6 | MODERATE | `routing_active_profile` and active-profile status display require state persistence that B1 does not define | Remove active-profile tracking from B1 acceptance criteria; defer to B2 non-goals |
| 7 | LOW | Fallthrough behavior when a phase key is absent but the file exists is unspecified | Add one explicit acceptance criterion for partial-file fallthrough |

**Must-fix before implementation:** Findings 1 and 6. Finding 1 is a design decision that shapes the API surface of `lib-routing.sh` — resolving it after code is written costs significantly more than doing so now. Finding 6 removes a state-tracking problem that has no solution in B1's scope.

**Can be fixed during implementation:** Findings 2, 3, 4, 5, 7. These are clarifications that reduce implementation confusion but do not change the API shape.
