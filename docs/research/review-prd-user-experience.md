# UX & Product Review: PRD — Static Routing Table (iv-1kd4)

**Reviewer role:** Flux-drive User & Product Reviewer
**Document reviewed:** `docs/prds/2026-02-21-static-routing-table.md`
**Date:** 2026-02-21
**Primary user:** A single AI agent developer (mk) who configures and operates Clavain as an autonomous software engineering rig. The job-to-be-done is: declare a routing policy once, have it honored by both Codex dispatch and Claude subagents, without editing code.

---

## Part 1: Problem Validation

### Problem statement accuracy

The PRD correctly identifies three independent routing systems (dispatch tiers, agent frontmatter, Interspect overrides) that cannot share configuration. The research file (`research-current-model-routing.md`) confirms this gap precisely: "Dispatch != Subagent routing — Two separate systems (dispatch tiers vs. agent frontmatter); no unified configuration."

The pain is real and well-evidenced:
- Changing routing requires `sed -i` commands on agent frontmatter files
- Dispatch tiers (`tiers.yaml`) and agent models (`agents/*.md`) are set through completely different mechanisms with no shared vocabulary
- There is no single view of the full routing policy

**Assessment:** Problem is legitimate and well-scoped for a solo developer context. The "no single place to see routing policy" pain is particularly acute because `/clavain:model-routing status` only shows agent frontmatter, not dispatch tier assignments.

### Severity of pain

Medium-high for the target user. The current workaround (running `/clavain:model-routing economy` before economy-sensitive sprints) requires remembering to do it, and there is no way to confirm that the Codex dispatch side is configured compatibly. The asymmetry is a real cognitive tax.

---

## Part 2: Config Format Ergonomics

### F1: routing.yaml schema — FINDING: Intuitive but vocabulary gap needs resolution

**Severity: Medium**

The proposed schema maps phases to model tiers using terms like `brainstorm: opus`. This is natural to read. However, a vocabulary mismatch exists between the two routing systems that the PRD does not resolve:

- **Subagent side** uses: `haiku`, `sonnet`, `opus`, `inherit`
- **Dispatch side** uses: `fast`, `deep`, `fast-clavain`, `deep-clavain` (which map to GPT model strings)

The PRD acceptance criteria show examples like `brainstorm: opus` and `execute: sonnet` — these are subagent vocabulary. But F3 says dispatch.sh will "consult routing.yaml for phase-aware tier selection." Which vocabulary does routing.yaml speak? If it speaks Claude model names (`opus`, `sonnet`, `haiku`), then dispatch.sh must translate those to its own `fast`/`deep` tiers — a mapping that is both lossy (haiku has no dispatch equivalent) and coupled to decisions not yet made in this PRD.

If routing.yaml speaks tier vocabulary (`fast`, `deep`), then it is opaque to the subagent side where users think in model names.

**Action required:** The PRD must define which vocabulary routing.yaml uses, and provide a translation table if routing.yaml uses one vocabulary to serve both systems. The simplest resolution is to let routing.yaml use Claude model names (`haiku`, `sonnet`, `opus`, `inherit`) for all sections, and have `lib-routing.sh` map those to dispatch tiers when called from dispatch.sh. The mapping would be: opus→deep, sonnet→deep, haiku→fast (lossy but auditable). This translation logic must be explicit in the acceptance criteria.

### Self-documenting YAML and line-by-line parsing

The acceptance criteria say routing.yaml should be "self-documenting with inline comments." This is a good ergonomic commitment for a solo developer who will read this file infrequently. The `tiers.yaml` file does this well with `description:` fields per tier — routing.yaml should follow the same pattern.

The line-by-line YAML parsing requirement (matching the dispatch.sh pattern) is the right call. Introducing a YAML library dependency for a shell plugin would be a mistake. However, profiles add a new structural challenge: a profile section contains sub-keys that themselves contain phase/category mappings, creating three nesting levels versus the two levels in tiers.yaml. The parser will be more complex and that complexity is not acknowledged in the acceptance criteria.

---

## Part 3: Resolution Order

### F2: Resolution order — FINDING: Logically correct but will confuse in practice

**Severity: Medium**

The proposed resolution order is: per-agent override > phase-specific > category default > fallback.

This is a conventional priority chain and is logically sound. However, two usability issues arise:

**Issue 3a: Profiles are not in the resolution chain.**
The acceptance criteria for F2 do not mention profiles at all. F4 says `/model-routing economy` reads the `economy` profile and applies it to agent frontmatter. But does the active profile affect what `routing_resolve_model` returns? If the economy profile sets `brainstorm: haiku` and the phases section says `brainstorm: opus`, which wins when the economy profile is active? The resolution chain is incomplete until the profile's relationship to the phase/category layers is defined.

The most coherent design would be: active profile overrides phase defaults, making the full chain: per-agent override > phase (from active profile, falling back to `phases:` section) > category default > fallback. But this needs to be stated explicitly.

**Issue 3b: "Active profile" state storage is unspecified.**
`routing_active_profile` must return the currently active profile name. Where is this state stored? Candidates are: a file in `.claude/` (persistent across sessions), an environment variable (session-scoped), or a field in routing.yaml itself (static declaration). The PRD does not specify this. If it is an environment variable, then profile activation is ephemeral and not visible in `status`. If it is a file, there is now a second place that must be in sync with routing.yaml. This is a missing design decision that will force a guess at implementation time.

**Recommendation:** Add an `active_profile:` key to routing.yaml itself (e.g., `active_profile: economy`). The user edits one file to change the active profile. The command `/model-routing economy` writes this key. This makes the full policy visible in one file and avoids hidden state.

---

## Part 4: /model-routing Command UX

### F4: Command UX — FINDING: Mostly sensible, one backward-compatibility concern

**Severity: Low-Medium**

The current `/model-routing [economy|quality|status]` command uses sed to write model names into agent frontmatter files. The PRD's F4 changes this so the command reads a profile from routing.yaml and applies it. This is an improvement.

**Issue 4a: What does "apply it to agent frontmatter" mean?**
The acceptance criteria say the command "applies [the profile] to agent frontmatter." Does this still mean sed-editing the markdown files? Or does it mean writing an `active_profile:` key and having every agent dispatch consult routing.yaml at call time? These are very different implementations with very different failure modes.

If the command still edits frontmatter files, the files become the source of truth and routing.yaml is just a template — users will be confused about which to edit. If the command only sets an active profile and routing.yaml is consulted at dispatch time, the frontmatter files are no longer the source of truth and `grep -r '^model:' agents/` (which the current status command uses) will show stale data.

**Issue 4b: Status output will become confusing if both systems are active.**
The current status shows a clean table of agent models. After B1, status must show: active profile name, per-phase overrides in routing.yaml, per-agent overrides, and what each agent will actually use after resolution. This is more complex. The PRD acceptance criterion "shows current agent models AND the active routing.yaml profile" understates the problem when the two sources disagree.

**Issue 4c: Custom profiles — discoverability.**
The acceptance criterion `/model-routing <custom-profile>` with no argument hint means users cannot discover available profiles without opening routing.yaml or running status. The status output should enumerate all available profiles. This is a one-line addition to the design that prevents the feature from feeling like a black box.

**What works well:** The backward-compatibility requirement (if routing.yaml doesn't exist, economy/quality behave identically to today) is correctly specified. This is the right zero-regression constraint for a solo developer who may not immediately create routing.yaml after upgrading.

---

## Part 5: Scope Assessment

### Profiles — FINDING: Over-engineered for B1

**Severity: High**

This is the most important product-level finding.

The core B1 value proposition is: "declare phase-to-model mapping in one config file, consulted by both dispatch and subagents." That requires F1 (schema), F2 (reader library), F3 (dispatch integration), and F4 (command update). It does not require profiles.

The `profiles:` section in F1 adds named routing configurations that can be switched at will. This sounds convenient, but it introduces:
- The "active profile" state storage problem (see Part 3, Issue 3b)
- The resolution order ambiguity between profile settings and phases section (Part 3, Issue 3a)
- Implementation complexity in the line-by-line YAML parser (three nesting levels)
- Ambiguity about what `/model-routing economy` does when routing.yaml exists vs. when it does not

The current user already has economy/quality modes via the existing command. Profiles in routing.yaml would duplicate that concept with a different implementation. The user would have two ways to express the same intent.

**A cleaner B1 scope would be:**
1. routing.yaml has a flat `phases:` section and a flat `overrides:` section (no profiles, no categories)
2. `/model-routing status` shows the phase-level policy from routing.yaml
3. `routing_resolve_model <phase> <category> [agent]` resolves model for any dispatch call
4. dispatch.sh consults routing.yaml when `--phase` is provided
5. Profiles and categories are deferred to B2 or a dedicated follow-up

This smaller scope eliminates all three of the resolution-order ambiguity issues identified above, produces a 40-line routing.yaml versus a 100-line one, and reduces the parser complexity to match the existing tiers.yaml parser.

**Evidence standard:** This is a product judgment call, not data-backed. The argument is that the user's stated pain ("no single place to see policy") is solved by the flat schema alone. The additional flexibility of profiles is speculative benefit that introduces real complexity cost.

---

## Part 6: Time-to-Value

### FINDING: Good for dispatch side, delayed for subagent side

**Severity: Low**

If the user creates routing.yaml with a phases section and runs a sprint, the first measurable benefit is that the right Codex model is used for each phase without manual tier selection. This is immediate and observable.

For the subagent side, the benefit depends on whether `/model-routing` reads routing.yaml at command time or whether agents consult routing.yaml at dispatch time. If the former, the user runs the command once and gets the same result as today (just with less typing). If the latter (agents consult routing.yaml directly), the user sees model changes reflected without running any command — which is a better UX but requires more implementation work.

The PRD should specify which approach is taken for the subagent side. The dispatch-time consultation model is strictly better from a UX perspective and should be the B1 target.

---

## Part 7: Flow Analysis

### Happy path: User creates routing.yaml and runs sprint

1. User creates `config/routing.yaml` using the documented schema
2. Sprint starts, dispatch.sh is called with `--phase brainstorm`
3. `routing_resolve_model brainstorm "" ""` returns `opus` (or equivalent tier)
4. Dispatch proceeds with correct model
5. User runs `/model-routing status` and sees the full policy in one view

**Gap in step 1:** There is no scaffolding or example routing.yaml provided. The user must construct the file from reading the schema documentation in routing.yaml itself. Given the vocabulary mismatch (Claude names vs. dispatch tiers), this is a real friction point for the first-use experience. The acceptance criteria should include: "routing.yaml includes commented-out example sections for common use cases (economy, quality, mixed)." This doubles as self-documentation and first-use scaffolding.

### Error path: Phase name in routing.yaml does not match sprint phase name

Sprint phases from `lib-sprint.sh` are named things like `brainstorm`, `plan`, `execute`, `review`, `ship`. If the user writes `execution:` in routing.yaml instead of `execute:`, the resolver returns empty string and falls back to default behavior silently. The user would have no way to know the config is being ignored.

**Missing:** The `routing_list_mappings` function (F2 acceptance criteria) partially addresses this by showing the full table, but only if the user runs it. There should be a warning logged to stderr when `routing_resolve_model` is called with a phase name that does not appear in routing.yaml and the file exists. "No routing rule for phase 'execution' in routing.yaml — using default" is an actionable message. This is a missing acceptance criterion.

### Cancellation path: User removes routing.yaml mid-sprint

The PRD correctly specifies that when routing.yaml doesn't exist, behavior is identical to current. But if routing.yaml is removed or becomes unreadable mid-sprint, the reader library must degrade gracefully. The acceptance criterion "Returns empty string (not error) when routing.yaml doesn't exist" covers the no-file case but not the unreadable/malformed case. A malformed routing.yaml that causes the parser to crash would be worse than no file at all.

**Missing acceptance criterion:** When routing.yaml exists but cannot be parsed, log a warning to stderr and return empty string (fall through to existing defaults). Never exit non-zero from `routing_resolve_model` — callers must be protected from config errors.

### Edge case: Interserve mode active

The current dispatch.sh applies `fast` → `fast-clavain` remapping when interserve mode is active. If routing.yaml maps `execute: sonnet` and the user has defined `sonnet` to mean `fast` tier, and interserve mode is active, the correct resolved model is `fast-clavain`. The PRD does not address how interserve mode interacts with routing.yaml phase assignments. The interserve remapping logic must run after routing.yaml resolution, not before, and this sequencing must be specified.

---

## Part 8: Developer Ergonomics

### lib-routing.sh placement and portability

The PRD proposes `hooks/lib-routing.sh` as the location for the reader library. This is consistent with the existing pattern (lib-sprint.sh, lib-interspect.sh are in hooks/). However, lib-routing.sh will be called from scripts/dispatch.sh, which is in a different directory. The existing tiers.yaml resolver in dispatch.sh uses `BASH_REMATCH` and a local parser without sourcing any library. Adding a sourced library from a different directory adds path-resolution complexity.

The existing pattern in dispatch.sh for locating tiers.yaml (checking relative paths, then CLAVAIN_SOURCE_DIR, then plugin cache) would need to be replicated for lib-routing.sh. Alternatively, the routing resolution logic could live in dispatch.sh directly (alongside the tier resolver), keeping dispatch.sh self-contained and the hooks/ library for the command side only.

**Recommendation:** Either place the reader in `scripts/lib-routing.sh` (alongside dispatch.sh) with a stub shim in `hooks/` that sources it, or embed the phase-resolution logic directly in dispatch.sh and expose only `routing_list_mappings` and `routing_active_profile` via the hooks/ library (since those are only needed by the command, not dispatch). This avoids the cross-directory sourcing problem.

### No-external-YAML constraint

The line-by-line parsing requirement is correct and consistent with the project pattern. But the acceptance criteria should specify what happens with YAML features that users might try: block scalars, inline lists, quoted strings, anchors. The safe answer is "not supported — use simple key: value format only" and the schema file should document this explicitly.

---

## Part 9: Open Questions the PRD Leaves Unanswered

These are questions that would force implementation-time guessing if not resolved in the PRD:

1. **Vocabulary:** Does routing.yaml use Claude model names (opus/sonnet/haiku/inherit) or dispatch tier names (fast/deep)? If model names, how does lib-routing.sh translate to dispatch tiers?

2. **Active profile state:** Where is the currently active profile stored? File, environment variable, or key in routing.yaml?

3. **Profile and phase relationship:** When a profile is active, does it replace the phases section or merge with it? Which wins if both define a rule for the same phase?

4. **Subagent dispatch-time vs. command-time:** Does routing.yaml affect subagents at dispatch time (every Task call consults it) or only when the user runs `/model-routing <profile>` (which then edits frontmatter)?

5. **Interserve mode sequencing:** Does interserve mode remapping run before or after routing.yaml resolution? What is the intended behavior when both are active?

6. **Phase name validation:** Is there a known enumeration of valid phase names that routing.yaml should validate against, or are phase names arbitrary strings that callers must spell consistently?

---

## Summary Table

| # | Finding | Severity | Feature | Recommended Action |
|---|---------|----------|---------|-------------------|
| 1 | Vocabulary mismatch: routing.yaml examples use subagent names (opus/sonnet), but dispatch uses tier names (fast/deep). No translation defined. | High | F1, F2, F3 | Define canonical vocabulary and explicit translation in PRD |
| 2 | Profiles are over-engineered for B1. They introduce state storage and resolution-order problems not present without them. | High | F1, F4 | Defer profiles to B2; ship flat phases + overrides only |
| 3 | Active profile state storage is unspecified. Implementation will guess at a file, env var, or routing.yaml key. | High | F2, F4 | Add `active_profile:` key to routing.yaml itself; specify in PRD |
| 4 | Resolution order is incomplete — profile's relationship to phases section is undefined. | Medium | F2 | Define full 5-level chain or eliminate profiles from B1 |
| 5 | Missing error message when routing.yaml exists but phase name is not found in it. Silent fallback is invisible. | Medium | F2 | Add acceptance criterion: warn to stderr on unknown phase lookup |
| 6 | "Apply to agent frontmatter" is ambiguous — sed-edit or dispatch-time consultation? The two architectures have opposite source-of-truth implications. | Medium | F4 | Specify: agents consult routing.yaml at dispatch time (not sed) |
| 7 | Interserve mode interaction with routing.yaml resolution is unspecified. | Medium | F3 | Specify sequencing: routing.yaml resolution first, then interserve remapping |
| 8 | Cross-directory sourcing of lib-routing.sh by dispatch.sh adds path-resolution complexity not acknowledged. | Low-Medium | F2, F3 | Relocate library or embed dispatch-side logic in dispatch.sh |
| 9 | No example routing.yaml provided. Users must construct from schema comments alone. | Low | F1 | Acceptance criterion: include commented example blocks for economy and quality patterns |
| 10 | Malformed routing.yaml error handling not specified (only missing-file case is covered). | Low | F2 | Add: parser errors must degrade gracefully (warn + return empty) |

---

## Product Recommendation

Ship B1 in two parts:

**B1a (recommended immediate scope):**
- routing.yaml with `phases:` and `overrides:` sections only (no profiles, no categories)
- `lib-routing.sh` with `routing_resolve_model` and `routing_list_mappings`
- dispatch.sh `--phase` flag integration
- `/model-routing status` shows routing.yaml phase policy alongside current agent models
- Backward-compatible when routing.yaml is absent

**B1b (follow-up, after B1a is in use):**
- Profiles section in routing.yaml
- `active_profile:` state management
- `/model-routing <custom-profile>` support
- Category defaults section

This split gives the user the core value (single config file, dispatch-aware routing) immediately, while deferring the design questions (profiles, state storage, resolution order) until there is real usage data to inform them. The vocabulary problem and the interserve sequencing problem must be resolved before any implementation begins.

---

*File: `/root/projects/Interverse/docs/research/review-prd-user-experience.md`*
