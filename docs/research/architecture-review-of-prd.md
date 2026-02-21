# Architecture Review: B1 Static Routing Table PRD

**PRD:** `/root/projects/Interverse/hub/clavain/docs/prds/2026-02-20-static-routing-table.md`
**Brainstorm:** `/root/projects/Interverse/hub/clavain/docs/brainstorms/2026-02-20-static-routing-table-brainstorm.md`
**Date:** 2026-02-20
**Reviewer:** fd-architecture (Flux-drive Architecture & Design Reviewer)
**Full verdict:** `/root/projects/Interverse/.clavain/verdicts/fd-architecture.md`

---

## Methodology

All four focus questions were evaluated against the live codebase, not just the PRD text. Files read:
- `hub/clavain/docs/prds/2026-02-20-static-routing-table.md`
- `hub/clavain/docs/brainstorms/2026-02-20-static-routing-table-brainstorm.md`
- `hub/clavain/docs/clavain-vision.md`
- `hub/clavain/docs/roadmap.md`
- `hub/clavain/config/dispatch/tiers.yaml`
- `hub/clavain/scripts/dispatch.sh` (resolve_tier_model, lines 161-234)
- `hub/clavain/hooks/lib-interspect.sh` (routing override system, lines 490-750)
- `hub/clavain/hooks/lib-sprint.sh` (phase chain, line 125)
- `hub/clavain/commands/model-routing.md`
- `plugins/interflux/agents/review/*.md` (12 agents with model frontmatter)
- `plugins/intercraft/agents/review/*.md`, `plugins/intersynth/agents/*.md`
- `hub/clavain/.claude/agents/` (Interspect routing override consumers)

---

## Overall Verdict: CONDITIONAL PASS

2 must-fix issues, 3 flagged risks, 1 schema ambiguity.

The PRD is architecturally sound in its core framing: a single declarative config with a shell library consumer, no kernel coupling, clear OS-layer ownership. The nested inheritance schema composes cleanly for B2/B3 extension. The OS/Kernel boundary is correctly respected throughout.

Three structural problems require attention before implementation: a phase-name mismatch between the PRD schema and the live codebase, a conflict between the new routing.yaml `overrides` section and the existing `routing-overrides.json` managed by Interspect, and a path-discovery coupling risk when `lib-routing.sh` is called from companion plugin contexts. These are fixable within B1 scope with targeted PRD amendments. No architectural rewrites are needed.

---

## Focus Question 1: Does the Schema Compose Well with B2/B3?

**Yes, with one caveat.**

The nested inheritance schema is correctly structured for forward extension. B2 can add a `complexity_overrides` section that sits above `phases` in the resolution order without touching existing keys. B3 can add an `adaptive` section gated on a boolean flag, with the static path (B1) as fallback when adaptive is off. This is the zero-cost abstraction the brainstorm explicitly designs for and the vision's Stage 2/Stage 3 model routing architecture requires.

```yaml
# B1 base (routes correctly today)
phases:
  executing:
    categories:
      review: opus

# B2 extension (no schema break)
complexity_overrides:
  high:
    categories:
      review: opus

# B3 extension (gated, static fallback preserved)
adaptive:
  enabled: false
  source: interspect
```

The caveat: the `overrides` section (per-agent pins) will conflict with Interspect's existing `.claude/routing-overrides.json` system when B3 integrates Interspect. This is not a B2/B3 schema problem — it is a B1 scope problem. If unresolved in B1, B3 inherits two parallel override mechanisms with undefined precedence. See Finding 2 below.

The C2 dependency (agent fleet registry reads routing.yaml to build cost profiles) is cleanly satisfied: routing.yaml's category-to-model mappings are the canonical input for cost profile construction.

---

## Focus Question 2: Is the OS/Kernel Boundary Respected?

**Yes, cleanly.**

The PRD correctly places all routing policy in the OS layer (Clavain config + shell library). The vision's formulation — "the kernel doesn't know what 'brainstorm' means" — is honored throughout:

- `lib-routing.sh` makes no `ic` subprocess calls
- The audit trail (routing decisions as kernel events) is explicitly deferred to B2/B3 with the correct design: `ic event emit routing-decision ...` called after resolution, not before
- The kernel stores the event without interpreting it — mechanism, not policy
- The brainstorm explicitly rejects `ic routing resolve` as kernel primitive creep

No equivalent violation appears in the PRD. The boundary is clean.

---

## Focus Question 3: Coupling Risks from Merging Dispatch Tiers?

**Low coupling risk, one lifecycle concern to document.**

Merging `dispatch.tiers` into `routing.yaml` is architecturally defensible at B1. Both sections are OS-layer policy, both are read-only by callers (dispatch.sh reads tiers, resolve_model reads phases), and the sections are syntactically independent. The single-file consolidation eliminates the current "why are there two config files" question.

The one concern: `dispatch.tiers` evolves when Codex model names change (external API contract), while `phases` evolves when sprint routing policy changes (Clavain internal). These are independent change axes. When Interspect in B3 is given authority to propose changes to the phases section, dispatch.sh also reads the same file. This is acceptable if ownership is documented clearly.

Concrete risk scenario: Interspect writes a proposed complexity_overrides patch to routing.yaml in B3. The patch tool uses line-based merge. A concurrent Codex model name update to `dispatch.tiers` touches the same file. The merge produces a malformed YAML block. dispatch.sh silently falls back to hardcoded defaults. Codex dispatches use the wrong model for one session before the corruption is detected.

This scenario is low probability at B1 scope. It becomes material only if Interspect or an external tool is given write access to routing.yaml. No fix needed for B1. Document the separation of mutators in routing.yaml's inline comments before B3 work begins.

---

## Focus Question 4: Resolution Order Ambiguity?

**Yes — two edge cases require PRD amendments before implementation.**

### Edge Case A: Phase Name Mismatch (Must-Fix)

The PRD schema uses phase keys `strategy`, `plan`, `execute`, `quality-gates`, `ship`. The actual ic phase chain in `hub/clavain/hooks/lib-sprint.sh:125` is:

```bash
phases_json='["brainstorm","brainstorm-reviewed","strategized","planned","plan-reviewed","executing","shipping","reflect","done"]'
```

Direct mismatches:

| PRD schema key | Actual ic phase name | Gap |
|---|---|---|
| `strategy` | `strategized` | Different names |
| `plan` | `planned` | Different names |
| `execute` | `executing` | Different names |
| `quality-gates` | Not a phase — display alias for `executing` | lib-sprint.sh:514 maps `executing` to `quality-gates` for display |
| `ship` | `shipping` | Different names |
| (missing) | `brainstorm-reviewed` | No schema entry |
| (missing) | `plan-reviewed` | No schema entry |
| (missing) | `reflect` | No schema entry |

The `quality-gates` case is the most dangerous. The PRD places the most important routing override (review=opus) on a key that will never be found by a caller passing the ic phase name `executing`. `resolve_model --phase executing --category review` will fail to match any `phases.executing` key (because the PRD schema uses `phases.execute`) and fall through to `defaults.categories.review: sonnet`. The review agent gets sonnet during quality-gates, not opus. The override is silently dropped with no error.

### Edge Case B: `--agent` Without `--category` Behavior Undefined

The PRD resolves Open Question 1 correctly by requiring `--category` to be caller-provided. But the F2 acceptance criteria for `resolve_model --agent <name>` do not specify what happens when `--category` is omitted. This leaves implementors to guess — likely resulting in either silent default returns (wrong model) or cryptic errors.

---

## Must-Fix 1: Align Phase Keys to ic Phase Names

The routing.yaml schema must use ic-canonical phase names as keys. The PRD must be amended.

Current PRD schema (incorrect):
```yaml
phases:
  strategy:    ...
  plan:        ...
  execute:     ...
  quality-gates:
    categories:
      review: opus
  ship:        ...
```

Correct schema (aligned to lib-sprint.sh:125):
```yaml
phases:
  brainstorm:
    model: opus
    categories:
      research: haiku
  brainstorm-reviewed:
    model: opus
  strategized:
    model: opus
  planned:
    model: sonnet
  plan-reviewed:
    model: sonnet
  executing:
    model: sonnet
    categories:
      review: opus    # quality-gates behavior lives here
  shipping:
    model: sonnet
  reflect:
    model: haiku
```

Alternatively, define an explicit caller-provided mapping layer in F2 acceptance criteria that maps display aliases (`quality-gates`) to ic phase names (`executing`) before resolution. Either approach must be explicit in acceptance criteria and in the test suite.

Files to amend: `hub/clavain/docs/prds/2026-02-20-static-routing-table.md` (F1 and F2 acceptance criteria), routing.yaml schema block in the brainstorm.

---

## Must-Fix 2: Resolve Conflict Between routing.yaml `overrides` and `.claude/routing-overrides.json`

The existing Interspect system manages per-agent overrides at `.claude/routing-overrides.json` via `_interspect_apply_routing_override()` in `hooks/lib-interspect.sh`. This system:

- Records overrides with structured metadata (reason, evidence_ids, created_by, created timestamp)
- Commits changes to git atomically (flock + git commit inside `_interspect_flock_git`)
- Has 10+ bats-core tests in `tests/shell/test_interspect_routing.bats`
- Is consumed by `commands/interspect-propose.md`, `commands/interspect-status.md`, `commands/interspect-revert.md`

The PRD introduces a new `overrides` section in routing.yaml that also maps agent names to models and is described as "wins over everything." After B1, there are two files claiming per-agent override authority. `resolve_model --agent fd-architecture` will check routing.yaml's `overrides` and never consult `.claude/routing-overrides.json`. Interspect's override proposals have no effect on resolution until B3 integration is designed — and B3 will inherit an ambiguous precedence problem.

Three resolution options:

**Option C (recommended for B1):** Remove the `overrides` section from routing.yaml's B1 schema. Per-agent pinning is deferred to B2/B3 alongside Interspect integration. B1 resolves phase + category + defaults only. The `overrides: {}` placeholder is removed or kept as a comment-only stub with no resolution semantics. This is the smallest correct B1 scope and avoids the conflict entirely.

**Option A (if per-agent pinning is required in B1):** Migrate Interspect's write path to routing.yaml's `overrides` section. `lib-routing.sh` becomes the sole reader. `_interspect_apply_routing_override()` writes to routing.yaml atomically. `.claude/routing-overrides.json` is deprecated. This requires changing lib-interspect.sh and is significant scope for B1.

**Option B (avoid):** `lib-routing.sh` reads both files and composes with documented precedence (routing.yaml overrides win over routing-overrides.json, or vice versa). This preserves both write paths but establishes two sources of truth for the same concept. Debugging "why did this agent get this model?" becomes harder with each additional source.

The PRD must choose before plan phase begins.

---

## Flagged Risk 1: lib-routing.sh Config Discovery in Companion Contexts

`dispatch.sh`'s existing `resolve_tier_model()` already handles a three-location probe for `tiers.yaml`:

```bash
# scripts/dispatch.sh:183-189
if [[ -f "$script_dir/../config/dispatch/tiers.yaml" ]]; then
  config_file="$script_dir/../config/dispatch/tiers.yaml"
elif [[ -n "$source_dir" && -d "$source_dir" && -f "$source_dir/config/dispatch/tiers.yaml" ]]; then
  config_file="$source_dir/config/dispatch/tiers.yaml"
else
  config_root="$(find ~/.claude/plugins/cache -path '*/clavain/*/config/dispatch/tiers.yaml' 2>/dev/null | head -1)"
```

After B1, `lib-routing.sh` must locate `config/routing.yaml`. The PRD's F4 removes model frontmatter from companion plugins (interflux, intercraft, intersynth), making these companions dependent on routing.yaml for model resolution. But companion plugins run with their own working directory — not Clavain's source tree. The discovery contract for routing.yaml in companion contexts is unspecified.

F2 acceptance criteria must include a routing.yaml discovery contract. The simplest approach: reuse the same three-probe pattern from dispatch.sh with `CLAVAIN_SOURCE_DIR` as the override, cache probe as the fallback. F4 acceptance criteria must specify that companion plugin callers set the discovery env var correctly before removing their frontmatter.

Without this, companion frontmatter removal (F4) will silently break companion agents in any context where `CLAVAIN_SOURCE_DIR` is not set.

---

## Flagged Risk 2: Fallback Hardcodes Create a Phantom Config Surface

F2 specifies: "Falls back to hardcoded defaults if routing.yaml is missing or malformed (matches economy profile)."

The hardcoded fallback (research=haiku, review=sonnet, workflow=sonnet) must be kept in sync with routing.yaml's `defaults` section manually. If `/clavain:model-routing quality` is applied (writing `model: inherit` to routing.yaml) and routing.yaml is subsequently absent (conflict resolution, fresh clone without the config file), resolution silently falls back to economy. The user's quality mode selection disappears with no error.

Two mitigations:

1. Add a stderr warning whenever the fallback path is taken: `echo "WARN: routing.yaml not found, using hardcoded economy defaults" >&2`
2. Add routing.yaml to Clavain's tracked plugin files so it cannot be absent on install

Neither is complex. The lack of a warning is the more important gap — it makes debugging routing decisions silent.

---

## Flagged Risk 3: Category Resolution Without `--category` Behavior Undefined

`resolve_model --agent fd-architecture` (no `--category`) has no specified behavior in the acceptance criteria. The agent's category cannot be inferred without filesystem probing (the PRD's Open Question 1 correctly rejects this). Without a specification:

- Implementors may silently return `defaults.model` (wrong — ignores category)
- Or return an error (correct but undocumented)
- Or probe the filesystem anyway (violates the brainstorm's design decision)

F2 should specify: `resolve_model --agent <name>` without `--category` applies the `overrides` section only (if the agent has an override, return it) or produces an explicit error requiring the caller to provide `--category`. Category resolution without explicit `--category` is not supported in B1.

This closes the ambiguity without requiring agent registration and is consistent with the brainstorm's "caller knows" design.

---

## What Is Architecturally Sound

- **Schema extension path for B2/B3:** Correct. Nested inheritance composes without schema breaks for both complexity_overrides and adaptive sections.
- **OS/Kernel boundary:** Clean. No kernel coupling introduced in B1.
- **Shell library as sole consumer:** Correct. Sub-1ms resolution, no subprocess, testable in bats-core.
- **Dispatch tier merge:** Defensible at B1 scope. Sections are independent. Document separate mutators.
- **Phase as caller-provided, not ambient:** Correct. Keeps resolution deterministic and testable.
- **Companion frontmatter removal batched in one pass:** Correct. Avoids a partial state where some companions route via routing.yaml and others via frontmatter.
- **model-routing command rewrite (F4):** Correct direction. Moving from sed-on-frontmatter to routing.yaml editor eliminates the most fragile part of the current system. The sed pattern is error-prone and invisible to routing.yaml status reporting.
- **Hardcoded fallback as last resort:** Correct principle. The only problem is the absence of a warning when the fallback fires.

---

## Summary Table

| Finding | Severity | Required Action |
|---|---|---|
| Phase name mismatch (PRD schema vs lib-sprint.sh:125) | Must-fix | Align schema keys to ic phase names; specify mapping contract in F2 |
| Two override systems without merge plan | Must-fix | Choose: remove overrides from B1 (recommended), migrate interspect write path, or compose both with documented precedence |
| lib-routing.sh path discovery for companion contexts | Flagged | Add discovery contract to F2 acceptance criteria; F4 must specify env var setup |
| Dispatch+phases in one file, different lifecycles | Flagged | No schema change; add inline comment documenting separate mutators |
| Fallback hardcodes create phantom config surface | Flagged | Add stderr warning on fallback; ensure routing.yaml is tracked in plugin install |
| Category resolution without --category undefined | Schema ambiguity | Define: --agent without --category applies overrides-only or errors explicitly |

The PRD is implementable after addressing Must-Fix 1 and Must-Fix 2. The three flagged risks and schema ambiguity should be resolved in the acceptance criteria before the plan phase begins.

---

## Files Referenced

- `/root/projects/Interverse/hub/clavain/docs/prds/2026-02-20-static-routing-table.md`
- `/root/projects/Interverse/hub/clavain/docs/brainstorms/2026-02-20-static-routing-table-brainstorm.md`
- `/root/projects/Interverse/hub/clavain/docs/clavain-vision.md`
- `/root/projects/Interverse/hub/clavain/docs/roadmap.md`
- `/root/projects/Interverse/hub/clavain/config/dispatch/tiers.yaml`
- `/root/projects/Interverse/hub/clavain/scripts/dispatch.sh` (lines 161-234)
- `/root/projects/Interverse/hub/clavain/hooks/lib-interspect.sh` (lines 490-750)
- `/root/projects/Interverse/hub/clavain/hooks/lib-sprint.sh` (line 125)
- `/root/projects/Interverse/hub/clavain/commands/model-routing.md`
- `/root/projects/Interverse/plugins/interflux/agents/review/fd-architecture.md` (representative)
- `/root/projects/Interverse/plugins/intercraft/agents/review/agent-native-reviewer.md`
- `/root/projects/Interverse/plugins/intersynth/agents/synthesize-review.md`
