# Correctness Review: PRD — Static Routing Table (2026-02-21)

**Reviewer:** Julik (Flux-drive Correctness Reviewer)
**Date:** 2026-02-20
**Document under review:** `docs/prds/2026-02-21-static-routing-table.md`
**Supporting evidence read:** `scripts/dispatch.sh`, `config/dispatch/tiers.yaml`, `commands/model-routing.md`, `agents/review/*.md`, `agents/workflow/*.md`, `skills/interserve/SKILL.md`, `docs/research/research-current-model-routing.md`

---

## Invariants That Must Hold

Before evaluating individual concerns, these are the invariants the system depends on. Every finding below is grounded in at least one of them.

1. **Backward-compat invariant** — Any caller that currently omits `--phase` must observe identical behavior after the change. No silent drift, no new warnings that break scripts.
2. **Namespace separation invariant** — Dispatch tiers (`fast`/`deep`) and subagent model names (`haiku`/`sonnet`/`opus`/`inherit`) are different namespaces. Crossing them must be explicit and lossless.
3. **Config-absent invariant** — When `routing.yaml` is absent, every resolution path returns an empty string and callers use their existing defaults. No error exit, no warning spam.
4. **Override priority invariant** — Explicit flags (`--model`, `--tier`) always win over config. Config always wins over hardcoded defaults. This must hold transitively through all resolution levels.
5. **File-atomicity invariant** — The YAML parser must not read partially-written config. (Applies if routing.yaml is ever updated at runtime, e.g. by `/model-routing`.)
6. **Concurrent-caller invariant** — Multiple `dispatch.sh` invocations running in parallel (a normal state during parallel agent dispatch) must not interfere with each other's resolution results.

---

## Findings

### CRITICAL — C1: Namespace bridging is absent from the PRD schema

**Severity:** Critical
**Feature affected:** F1, F2, F3

**The gap.** The PRD's `phases:` section maps phase names to "model tiers" (e.g., `brainstorm: opus`). But `opus` is a Claude subagent tier name — it is not a valid value for the dispatch.sh tier system. dispatch.sh `resolve_tier_model` looks up entries under the YAML `tiers:` key in `tiers.yaml`, where valid names are `fast`, `deep`, `fast-clavain`, `deep-clavain`. There is no `opus` there, and there never should be — Codex CLI does not speak Claude model names.

Conversely, `model-routing.md` uses `haiku`/`sonnet`/`opus`/`inherit` to write agent frontmatter, not `fast`/`deep`.

The PRD treats these as a single tier namespace but they are two completely separate namespaces:

| Caller | Tier namespace | Valid values |
|--------|---------------|--------------|
| `dispatch.sh --tier` | Codex CLI tiers | `fast`, `deep`, `fast-clavain`, `deep-clavain` |
| Agent frontmatter `model:` | Claude subagent tiers | `haiku`, `sonnet`, `opus`, `inherit` |

`routing_resolve_model <phase> <category>` (F2) is supposed to serve both callers, but it returns one value. What type is that value? The PRD never says.

**Concrete failure.** Suppose routing.yaml contains:

```yaml
phases:
  execute: sonnet
```

dispatch.sh calls `routing_resolve_model "execute" ""`, gets `sonnet`, passes it as `--tier sonnet` to the dispatch integration. `resolve_tier_model "sonnet"` searches `tiers.yaml` for a block named `sonnet:`, finds nothing, prints a warning, and falls back to config.toml default — silently ignoring the routing config entry. The routing table looks correct to the operator but has zero effect on dispatch.

Alternatively, routing.yaml uses Codex tier names:

```yaml
phases:
  execute: deep
```

`/model-routing economy` reads this, resolves `deep` for the `execute` phase, then `sed`s `model: deep` into agent frontmatter. Claude subagent frontmatter with `model: deep` is an unknown tier; Claude Code's behavior on encountering an unknown model name in frontmatter is undefined (likely falls back to default, silently).

**Required fix.** routing.yaml must either:
- (a) Use **two distinct sections** — one for dispatch tiers, one for subagent tiers — with explicit typing; or
- (b) Use a **translation table** within the schema that maps abstract phase-to-intent (e.g., `quality: high`) to both dispatch tier AND subagent model, resolved by the appropriate library at call site; or
- (c) Require routing.yaml to use **only the subagent namespace** and document that dispatch.sh integration uses a fixed mapping (e.g., `haiku → fast`, `sonnet → fast`, `opus → deep`).

Option (c) is the smallest correct fix. Option (a) is the most explicit and auditable.

Without resolving this, C1 means F3 (dispatch integration) and F4 (subagent integration) cannot both be correct simultaneously from the same routing.yaml.

---

### CRITICAL — C2: `--model` override priority breaks when routing.yaml is consulted before `--tier` resolution

**Severity:** Critical
**Feature affected:** F3

**The gap.** The PRD states:

> `--tier` and `--model` flags still override routing.yaml (explicit > config > default)

The acceptance criteria for F3 reads:

> When `--phase` is provided, resolves model from routing.yaml before falling back to `--tier`

This creates an ambiguous priority chain: `--model` > `routing.yaml(phase)` > `--tier` > default. But the PRD never specifies what happens when both `--phase` and `--tier` are provided.

Looking at existing dispatch.sh code (lines 379-389), the current logic is:

1. If `--tier` is set, call `resolve_tier_model`
2. Set `MODEL` from result
3. `MODEL` used in `codex exec -m $MODEL`

If `--phase` resolution is added before `--tier` resolution and also sets `MODEL`, then `--tier` will overwrite the phase-resolved model. That is probably correct (explicit wins), but the PRD's wording "before falling back to `--tier`" implies phase takes precedence over tier, which contradicts "explicit > config > default."

**Concrete failure scenario.** The Interserve skill currently dispatches with:

```bash
bash "$DISPATCH" --prompt-file "$TASK_FILE" --tier deep -C "$PROJECT_DIR"
```

After the change, if Interserve also passes `--phase execute`, the phase resolution fires and sets MODEL to whatever routing.yaml says for `execute`. Then `--tier deep` fires and overwrites MODEL with `gpt-5.3-codex`. The routing.yaml phase mapping is silently ignored even though it was explicitly set.

Or the reverse: phase resolution happens last and ignores `--tier`. Then explicit `--tier deep` from the skill is silently overridden by whatever routing.yaml says, breaking the explicit-wins contract.

**Required fix.** The PRD must document an unambiguous priority order for all three inputs:

```
--model > --tier > routing.yaml(phase) > routing.yaml(category) > tiers.yaml fallback > config.toml default
```

and the implementation must strictly implement that ordering.

---

### HIGH — H1: Missing phase name in routing.yaml produces silent wrong behavior, not a detectable error

**Severity:** High
**Feature affected:** F2, F3

**The gap.** F2 acceptance criteria state:

> Returns empty string (not error) when routing.yaml doesn't exist

This is correct for the file-absent case. But the PRD says nothing about what happens when routing.yaml exists but the requested phase is absent from it. The current acceptance criteria conflate file-absent with key-absent.

**Concrete failure.** routing.yaml exists and defines:

```yaml
phases:
  brainstorm: opus
  reflect: sonnet
```

dispatch.sh is called with `--phase execute`. The library searches routing.yaml, finds no `execute` key under `phases:`, and returns... what? If it returns empty string (matching the file-absent behavior), the caller uses `--tier` fallback. That is probably correct. But if the shell parser's YAML walking logic exits the `phases:` block without returning a value and falls through to a `category default` lookup, the wrong tier could be returned. The PRD does not specify which of these happens.

More insidiously: if the library returns the fallback tier (not empty string) when a phase is missing, that silently masks the misconfiguration. The operator believes the phase is routed by routing.yaml but it is actually using the tiers.yaml default.

**Required fix.** F2 must add an explicit acceptance criterion:

> When routing.yaml exists but the requested phase is not found, the function returns empty string (same as file-absent) AND emits a debug-level warning to stderr so that misconfiguration is detectable.

---

### HIGH — H2: Profile references a non-existent tier — produces silent wrong output

**Severity:** High
**Feature affected:** F1, F4

**The gap.** The PRD says routing.yaml will support:

```yaml
profiles:
  economy:
    research: haiku
    review: sonnet
  quality:
    research: inherit
    review: inherit
```

What happens when a profile entry names a model tier that doesn't exist in either namespace? For example:

```yaml
profiles:
  experimental:
    review: flash
```

`flash` is not in the Claude subagent tier namespace, and it is not in tiers.yaml. The `/model-routing experimental` command will happily `sed` `model: flash` into every agent frontmatter file. Claude Code encounters `model: flash` and silently falls back to its default. No error is surfaced to the operator.

Additionally: what if the profile section is empty or partially written? The line-by-line YAML parser (which the PRD calls for — "no external YAML library") is vulnerable to valid-looking but semantically incomplete YAML. For example:

```yaml
profiles:
  economy:
    # incomplete: no tier entries yet
```

The parser returns empty, callers use existing defaults, and the operator has no indication the profile failed to apply.

**Required fix.** `routing_resolve_model` (or a separate `routing_validate` function) must check that every tier value in the profile is a member of the valid set for the target namespace. For subagent profiles: `{haiku, sonnet, opus, inherit}`. Validation should run at load time (once) and emit a warning for unknown values before applying any changes.

---

### HIGH — H3: tiers.yaml and routing.yaml disagree — no conflict resolution defined

**Severity:** High
**Feature affected:** F1, F3

**The gap.** The PRD states:

> Existing `config/dispatch/tiers.yaml` — routing.yaml extends but does not replace this

But it gives no rule for what happens when the two files disagree. Specifically: if routing.yaml says `phases: { execute: deep }` and tiers.yaml maps `deep: { model: gpt-5.3-codex }`, they are consistent. But what if a future change updates tiers.yaml to rename `deep` → `deep-v2` (new model released), while routing.yaml still says `execute: deep`? Resolution: `deep` is missing from tiers.yaml, `resolve_tier_model` returns empty with a warning, routing falls back to config.toml default, and the operator sees a mystery degradation.

This is the same layered-config freshness problem that plagues most multi-file routing systems: files can drift out of sync with no guardian enforcing consistency.

**More immediate conflict scenario.** Suppose routing.yaml says:

```yaml
phases:
  execute: fast
```

And tiers.yaml has a `fallback` section that says `fast: deep` (used when the Spark model is unavailable). dispatch.sh's existing `resolve_tier_model` function implements that fallback, so `fast` resolves to `gpt-5.3-codex` without the operator knowing. The routing.yaml entry appears to say "use fast for execute" but silently runs `gpt-5.3-codex` when Spark is down. This is not a new bug — it exists today — but routing.yaml adds a new layer where the effective model is two hops away from what the operator configured.

**Required fix.** Document the authority hierarchy explicitly in the PRD:

1. routing.yaml names a **logical tier** (e.g., `fast`)
2. tiers.yaml resolves that logical tier to a **concrete model ID**
3. routing.yaml never names concrete model IDs directly (that would bypass tiers.yaml)

Any tier name in routing.yaml that does not exist in tiers.yaml is a validation error, surfaced at load time.

---

### MEDIUM — M1: Per-function-call caching has a race window in concurrent parallel dispatch

**Severity:** Medium
**Feature affected:** F2

**The gap.** F2 acceptance criteria state:

> Caches parsed config for the duration of a single function call (no redundant file reads within one resolution)

"Per-function-call" cache means the cache lives for the duration of one invocation of `routing_resolve_model`, not across calls. This is effectively no cache — each invocation re-reads the file.

This is fine for correctness in the single-call case, but the PRD's description hints at a shell global variable as the cache mechanism (standard practice in bash libs). If it is a shell-level global (e.g., `_ROUTING_CACHE="$parsed_content"`), it persists for the duration of the shell process.

In Clavain's parallel dispatch pattern, multiple `dispatch.sh` invocations run concurrently as separate subprocesses. Each is its own bash process, so they do not share globals — no cache coherence problem there.

However, there is a specific race window if `/model-routing <profile>` is run while parallel agents are dispatching:

1. Agent A starts, calls `routing_resolve_model`, reads routing.yaml, gets `deep` for phase `execute`.
2. Operator runs `/model-routing quality` which calls `sed -i` on agent frontmatter AND (if F4 is implemented) writes to routing.yaml to set the active profile.
3. Agent B starts, calls `routing_resolve_model`, reads routing.yaml mid-write (if routing.yaml is being atomically replaced — fine; if it is being updated in-place via `sed -i` — not fine).

**The `sed -i` partial-read scenario.** `sed -i` on most Linux implementations writes a temp file and renames it (atomic). But if `lib-routing.sh` reads routing.yaml via `while IFS= read -r line; do ...done < "$config_file"` (consistent with dispatch.sh's existing YAML parser pattern), that is a streaming read. The `open()` happens before the rename, so the process reads the old file to completion even if a rename occurs mid-read. This is safe.

But if the PRD intends to update the active profile within routing.yaml itself (not just agent frontmatter), and does so non-atomically (e.g., `sed -i 's/^active_profile:.*/active_profile: quality/' routing.yaml`), then there is a window where the file is truncated (some `sed` implementations truncate-then-write). A concurrent reader opening the file in that window gets a truncated parse.

**Concrete 3AM failure.** Ten parallel agents dispatched. Operator toggles `/model-routing quality` at second 0.1 of dispatch. Three agents read routing.yaml before the sed; seven read after. The session runs with mixed model tiers, some economy some quality, with no log indicating the divergence. One quality-mode agent burns Opus tokens on a task that was supposed to be haiku. Token budget exceeded, sprint blocked.

**Required fix.** Routing.yaml must be treated as read-only during a session. The "active profile" concept should be stored as a separate sentinel file (e.g., `.claude/routing-active-profile`) rather than written into routing.yaml. Reads of routing.yaml are then safe without any locking. `/model-routing` writes to the sentinel file atomically (write-temp-then-rename), and `routing_active_profile` reads from the sentinel.

Alternatively, if routing.yaml is never modified at runtime (only edited manually by the operator between sessions), document that constraint explicitly. The PRD currently does not.

---

### MEDIUM — M2: The `sed -i` in `/model-routing` will silently corrupt YAML frontmatter on agent files that lack a `model:` line

**Severity:** Medium
**Feature affected:** F4

**The gap.** The current `model-routing.md` command uses:

```bash
sed -i 's/^model: .*$/model: haiku/' agents/research/*.md
```

This pattern only fires if the file already contains a `model:` line in the frontmatter. If a new agent is added without a `model:` line (relying on Claude Code's default), the sed command produces no change and the agent silently uses its default rather than the requested profile.

The PRD does not add acceptance criteria that guard against this case. With the new routing.yaml system, `/model-routing <profile>` is more authoritative — operators will expect it to apply the profile to all agents. A missing `model:` line silently exempts the agent.

**Concrete failure.** A new agent `agents/workflow/migration-runner.md` is created without a `model:` line. Operator runs `/model-routing economy` before a high-volume sprint. The two existing workflow agents are set to `sonnet`. `migration-runner` defaults to `inherit` (parent session model, which is Opus). The sprint runs migration-runner at Opus prices while the operator believes economy mode is active.

**Required fix.** The apply step for profiles must either:
- (a) Insert `model: <tier>` if no `model:` line exists in the frontmatter block; or
- (b) Detect agents missing a `model:` line and warn explicitly: "Warning: migration-runner.md has no model: line — skipped."

Option (b) is the safer default (non-destructive, visible). Option (a) requires correctly inserting into YAML frontmatter without corrupting other fields, which is non-trivial with sed alone.

---

### MEDIUM — M3: `routing_list_mappings` and `routing_active_profile` have undefined output format — breaks future automation

**Severity:** Medium (low urgency now, high cost later)
**Feature affected:** F2

**The gap.** The PRD specifies:

> `routing_list_mappings` prints the full routing table for status display
> `routing_active_profile` returns the currently active profile name

Neither acceptance criterion specifies the output format. This matters because `/model-routing status` (F4) will call these functions and display their output. If the format is undocumented, the first implementer will choose something convenient, the second (B2 complexity-aware routing) will parse that output, and the third (B3 adaptive routing) will parse the second's interpretation.

Shell function output read by human eyes is easy. Shell function output consumed by other scripts is a contract that must be versioned.

**Required fix.** Add output format specs to F2 acceptance criteria. At minimum:

- `routing_list_mappings`: one line per mapping, format `<phase>: <tier>` or `<category>: <tier>`, stdout, no trailing whitespace.
- `routing_active_profile`: single word (profile name), stdout, empty string if no profile active.

---

### LOW — L1: Backward-compat guarantee is achievable but fragile without a guard test

**Severity:** Low (design concern)
**Feature affected:** F3, F4

**Assessment.** The backward-compat guarantee ("when routing.yaml is missing, behavior is identical to current") is mechanically achievable with the proposed design — the library returns empty, callers skip routing logic. The current code paths are preserved.

However, the guarantee is fragile in two ways:

1. **No automated verification.** There is no acceptance criterion requiring a test that runs dispatch.sh without routing.yaml and asserts the output is identical to the pre-change invocation. Without this test, any refactor of the tier resolution path could silently break the guarantee.

2. **The `--phase` flag changes stderr.** The current dispatch.sh produces no output to stderr for a successful `--tier deep` invocation (only on errors). If `--phase` support adds even a debug line ("No routing.yaml found, skipping phase resolution"), that is a change in behavior. Scripts that capture or assert on stderr (e.g., test harnesses, CI pipelines) will break.

**Required fix.** Add acceptance criteria:

> When `--phase` is provided and routing.yaml is absent, dispatch.sh produces no additional stderr output vs. the same invocation without `--phase`.

And require a regression test that captures the full stderr+stdout of a baseline invocation and asserts no diff after the change.

---

### LOW — L2: The PRD does not address the interflux agents' frontmatter

**Severity:** Low (scope acknowledgment concern)
**Feature affected:** F4

**The gap.** The PRD non-goals state:

> Interflux agent frontmatter management — This PRD covers Clavain's agents. Interflux agents can be wired in a follow-up.

But `/model-routing status` currently reports interflux agents in its output:

```
Review (2+7): [model] — plan-reviewer, data-migration (clavain) + fd-architecture, fd-safety, ...
```

The "7" are interflux agents. After this PRD ships, `/model-routing economy` will apply routing.yaml profiles to Clavain's 4 agents but leave the 7 interflux agents unchanged. The `/model-routing status` output will show a mixed state that is not explained to the operator.

This is a scope decision, not a bug, but it needs an explicit UI contract: the status output must distinguish "managed by routing.yaml" from "not managed, using agent-file default" so the operator is not confused.

---

## Summary Table

| ID | Severity | Feature | One-Line Description |
|----|----------|---------|----------------------|
| C1 | Critical | F1/F2/F3/F4 | Namespace bridging (dispatch tiers vs. subagent model names) is entirely absent from the schema; F3 and F4 cannot both be correct from the same routing.yaml without it |
| C2 | Critical | F3 | Priority order between `--model`, `--tier`, and `--phase` is ambiguous and contradictory in the PRD text |
| H1 | High | F2/F3 | Missing phase key in routing.yaml is undistinguishable from file-absent; misconfiguration is silent |
| H2 | High | F1/F4 | Profile entry with unknown tier name is silently applied to agent frontmatter; no validation at load time |
| H3 | High | F1/F3 | tiers.yaml and routing.yaml can drift out of sync with no guardian; tier names in routing.yaml are not validated against tiers.yaml |
| M1 | Medium | F2 | Active-profile update via `sed -i` on routing.yaml during parallel dispatch creates a race window for partial reads; sentinel-file pattern fixes it |
| M2 | Medium | F4 | Agents missing a `model:` frontmatter line are silently excluded from profile application |
| M3 | Medium | F2 | Output format of `routing_list_mappings` and `routing_active_profile` is unspecified; breaks downstream automation |
| L1 | Low | F3/F4 | Backward-compat guarantee is not verified by any acceptance criterion; stderr change risk under `--phase` |
| L2 | Low | F4 | Status output will show mixed managed/unmanaged agents without explanation after interflux is excluded from scope |

---

## Recommended Pre-Implementation Actions

In priority order:

1. **Resolve C1 first** — choose namespace strategy (a), (b), or (c) from the C1 finding and update routing.yaml schema and F2 acceptance criteria before any implementation starts. This decision propagates through every other feature.

2. **Fix C2 priority order** — write a one-line priority table in the PRD and have the dispatch.sh implementer sign off on it. It takes five minutes to write and avoids a class of bugs that are very hard to test for.

3. **Add load-time validation** — address H2 and H3 together by adding a `routing_validate` function called once at library load. It checks all tier names against both the subagent namespace and tiers.yaml. Any unknown name is a fatal error (or at minimum a loud warning). This eliminates the silent-corruption class.

4. **Sentinel file for active profile** — address M1 by separating the routing config (read-only) from the active-profile state (written by `/model-routing`). Write the sentinel atomically with rename.

5. **Add explicit edge-case acceptance criteria for H1 and M2** — these are wording changes to the PRD that take minutes and prevent real production surprises.
