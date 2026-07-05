# DEEPEN Review Probe — fd-routing-kernel-mechanics (round 2, probe 0)

**Target:** `docs/brainstorms/2026-07-05-autonomous-capability-routing-intercore.md`
**Lens:** kernel-mechanics (resolution-order determinism, precedence completeness, dual-resolver split-brain, clamp/fallback ordering)
**North star:** maximize verified novelty×risk surface until dry
**Mode:** confirm/refute cluster `c-fable-clamp-universality`, finding `f-017`

## Findings Index

1. [P1] CONFIRMED — `f-017` is real and understates the surface: at least three independent resolvers/injection points reach a dispatch `Model` field with zero safety-floor clamp, not just "session-model detection" — `ic route dispatch`/`ResolveDispatchTier` (Go), `ic dispatch spawn --model` (Go CLI flag), and `CLAVAIN_MODEL` env injection (bash hook) all bypass `ResolveModel`/`applyFloor` entirely.
2. [P0] `retry.go`'s `Retry()` copies `orig.Model` verbatim with no re-resolution or re-clamp — the planned Phase 2 two-strikes escalation ladder (sonnet→opus→fable) has no hook point in the current struct; if escalation is implemented as "mutate Model and call Retry," the mutated value skips `ResolveModel`/`applyFloor` on the escalated attempt.
3. [P2] `_routing_model_tier`/`_routing_downgrade` (bash) and `ParseModelTier` (Go) have no "fable" case today — an unrecognized tier string is treated as tier 0 / `TierUnknown`, which both codebases interpret as "skip the floor comparison," not "reject" — so a bug that leaves fable unrecognized fails *open* (unclamped) rather than *closed*.
4. [P3] Agent frontmatter `model:` fields (751 files, `.claude/agents/` + `os/Clavain/agents/` + `interflux/agents/`) are a fourth, wholly separate selection surface with zero fable value present today and no mechanism proposed in Phases 1-4 to route it through `ic route model` at all.

---

## Finding 1 — CONFIRMED (understated): dispatch/CLI/env call sites bypass the clamp, not just session-model detection

**Severity:** P1

**Where:**
- `core/intercore/internal/routing/resolve.go:91-103` — `ResolveDispatchTier(tier string) string`
- `core/intercore/cmd/ic/route.go:181-251` — `cmdRouteDispatch` (backs `ic route dispatch`)
- `core/intercore/cmd/ic/dispatch.go:59` (`cmdDispatchSpawn`, per background survey) — `Model: f.String("model", "")`
- `core/intercore/internal/dispatch/spawn.go:22,84-86,165-179` — `SpawnOptions.Model` → `Dispatch.Model` → `-m` CLI arg
- `os/Clavain/hooks/session-start.sh:361-378` — `CLAVAIN_MODEL` env injection from external `sprint-env-vars` CLI

**What:** The prior finding (`f-017`) framed the gap narrowly ("resolution calls and session-model detection are committed; subagent/dispatch call sites aren't confirmed"). The actual enumeration shows the gap is wider and structural, not just unconfirmed:

1. **`ResolveDispatchTier` (Go) never calls `applyFloor`.** Compare `ResolveModel` (resolve.go:36-87), which explicitly clamps at lines 82-84 (`result = r.applyFloor(opts.Agent, result)`), against `ResolveDispatchTier` (resolve.go:91-103), which does a bare 3-hop map lookup (`cfg.Dispatch.Tiers[tier].Model`) and `return`s with no floor logic at all. These are structurally separate methods over separate config tables (`Config.Dispatch.*` vs `Config.Subagents.*`/`Config.Roles`) sharing only the `*Resolver` receiver. The bash mirror (`lib-routing.sh:1225-1255`, `routing_resolve_dispatch_tier`) is the same shape: delegates to `ic route dispatch --tier=` with no `CLAVAIN_RUN_ID` gate at all (unlike `routing_resolve_model`'s gate at line 903) and no call to `_routing_apply_safety_floor` anywhere in the function.
2. **`ic dispatch spawn --model <raw>` is unclamped by construction.** `cmdDispatchSpawn` takes a raw CLI flag string straight into `SpawnOptions.Model`, which is written to `Dispatch.Model` and the spawned process's `-m` arg with zero calls to `routing.ResolveModel`/`ResolveDispatchTier` anywhere in the path.
3. **`CLAVAIN_MODEL` env var is a fourth injection path**, written by an external `sprint-env-vars` CLI (Composer, outside this repo) via `session-start.sh:369-374`, entirely outside `lib-routing.sh`'s function surface. (Note: grep confirms nothing in-repo currently *reads* `CLAVAIN_MODEL` — see Finding 3 for why this matters for Phase 1 wiring, not as a live bypass today.)

**Evidence:**
```go
// resolve.go:91-103 — no applyFloor call anywhere in this function
func (r *Resolver) ResolveDispatchTier(tier string) string {
	for hops := 0; hops < 3; hops++ {
		if t, ok := r.cfg.Dispatch.Tiers[tier]; ok {
			return t.Model
		}
		if fb, ok := r.cfg.Dispatch.Fallback[tier]; ok {
			tier = fb
		} else {
			break
		}
	}
	return ""
}
```
```bash
# lib-routing.sh:1225-1233 — no CLAVAIN_RUN_ID gate, no safety-floor call
routing_resolve_dispatch_tier() {
  if command -v ic >/dev/null 2>&1; then
    local _ic_result
    _ic_result=$(ic route dispatch --tier="$1" 2>/dev/null) && { echo "$_ic_result"; return 0; }
  fi
  ...
```
Currently this is *low-risk in practice* because `config/routing.yaml:72-91`'s `dispatch.tiers` only contains Codex model IDs (`gpt-5.3-codex*`, `gpt-5.3-codex-spark*`) — no Claude tier name, no "fable", reaches this table today. The risk is latent: the moment Phase 1 or later adds a Claude-tier alias to `dispatch.tiers` (or anything calls `ic dispatch spawn --model fable` directly, which nothing currently prevents), it ships unclamped.

**Suggestion:** Smallest viable fix: add a floor-clamp call inside `ResolveDispatchTier` (Go) and `routing_resolve_dispatch_tier` (bash) mirroring `ResolveModel`'s `applyFloor` step, even though it's a no-op today (no agent context to clamp against at the tier level) — this makes the invariant "every path that returns a model string clamps it" enforceable by a single grep/test rather than by convention. For `ic dispatch spawn --model`, add a validation step that runs the flag value through `ParseModelTier`/floor lookup when an `--agent` is also supplied, and reject (or clamp) unrecognized/sub-floor values instead of passing them through silently.

**Verdict:** CONFIRMED, and broader than stated. `f-017`'s hedge ("aren't confirmed to hit the same clamp") should become an assertion: they don't, by construction, on at least three call sites.

---

## Finding 2 — Two-strikes escalation (Phase 2) has no clamp-safe re-resolution hook in `retry.go`

**Severity:** P0

**Where:** `core/intercore/internal/dispatch/retry.go:121` (`Retry()`), read against the Phase 2 plan text ("Extend `internal/dispatch/retry.go` with an escalation policy: attempts 1-2 same model, attempt 3 re-dispatches at the next tier up").

**What:** `Retry()` currently builds the retried `Dispatch` as `Model: orig.Model` — a direct field copy, matching the brainstorm doc's own gap #2 ("`retry.go` copies the dispatch config verbatim including `Model:` — same-model retry only"). The plan proposes extending this to step the model up a tier on attempt 3. But there is no existing seam for "compute the next tier, then re-run it through `ResolveModel`/`applyFloor`" — the natural implementation is to mutate the tier string in-place (e.g. `sonnet→opus→fable`) and pass it straight to the same `Model: *string` field that today reaches `-m` with no validation (Finding 1, item 2). If Phase 2 is implemented as "downgrade/upgrade the string, then call the existing spawn path," the escalated attempt inherits the same unclamped route as `ic dispatch spawn --model`, meaning a low-trust agent whose safety floor should cap it at sonnet could reach fable on the escalation hop with no floor check at all — silently, since `routing_decisions` (per the lens's own P1 severity example) only logs the final model, not that escalation bypassed clamping.

**Evidence:** `retry.go:121` — `Model: orig.Model` is the entire model-selection logic today; nothing downstream of it re-invokes `routing.Resolver`. Escalation as described in Phase 2 ("attempt 3 re-dispatches at the next tier up") requires new code that doesn't exist yet, and the plan doesn't specify whether that new code calls `ResolveModel`/`applyFloor` or just string-bumps `Model` and re-spawns via the same `SpawnOptions.Model` seam already shown to skip clamping.

**Suggestion:** Phase 2's acceptance criteria should explicitly require the escalation step to call `ResolveModel`/`applyFloor` (or the bash `_routing_apply_safety_floor`) with the *original* agent context before writing the escalated `Model`, and `routing_decisions`/escalation evidence should record `floor_applied` for the escalation hop specifically — not just the pre-existing resolution. This is a one-field addition to the escalation evidence schema (Phase 2/4), not an architecture change.

**Verdict:** New failure mode introduced by the plan, not a pre-existing bug — today's same-model retry has nothing to clamp (model doesn't change), but tier-stepping escalation as scoped in Phase 2 walks directly into the unclamped seam identified in Finding 1 unless the plan is explicit about routing the escalated value back through the resolver.

---

## Finding 3 — Unknown-tier strings fail open (clamp-skipped), not fail-closed, on both sides of the fast-path split

**Severity:** P2

**Where:**
- `os/Clavain/scripts/lib-routing.sh:68-85` (`_routing_model_tier`) and `:122-132` (`_routing_downgrade`)
- `core/intercore/internal/routing/routing.go:17-28` (`ParseModelTier`, per background survey) and `resolve.go`'s `applyFloor` (treats `TierUnknown` as "skip clamping" per background survey's note on line ~138)

**What:** Neither `_routing_model_tier` (bash) nor `ParseModelTier` (Go) has a case for `"fable"` today — confirmed by `grep -rni fable core/intercore/` returning zero hits, and by `_routing_model_tier`'s bash `case` statement (haiku/sonnet/opus/local:*/flash-moe:* only, `*) echo 0`). This means:
- Bash: `_routing_apply_safety_floor` computes `model_tier=$(_routing_model_tier "$model")`; for `model="fable"`, this returns `0`, and the clamp logic (`lib-routing.sh:107-112`) only *warns* when the **floor** tier is 0 (invalid floor), but does nothing special when the **model** tier is 0 other than the numeric comparison `model_tier -lt floor_tier` — `0 -lt <floor>` is true for any real floor, so today a literal "fable" string passed through `_routing_apply_safety_floor` would actually get incorrectly clamped down to the floor (since unknown model tier reads as tier 0, the lowest possible) — the opposite failure direction from what the lens flagged, but still a silent misclassification that would make the whole Phase 1 fable tier appear to "just work" in shadow-mode manual testing (any agent with a floor set would silently downgrade fable→floor) while masking that `_routing_model_tier` was never updated.
- `_routing_downgrade("fable")` falls to `*) echo "${1:-haiku}"` — i.e. echoes "fable" back **unchanged**. This is the escalation-ladder-adjacent function; if any code path calls downgrade on an unrecognized string expecting a step-down, it gets a no-op instead, silently.

**Evidence:**
```bash
# lib-routing.sh:68-85
_routing_model_tier() {
  case "${1:-}" in
    haiku) echo 1 ;;
    sonnet) echo 2 ;;
    opus) echo 3 ;;
    *) echo 0 ;;   # <-- "fable" lands here today
  esac
}
# lib-routing.sh:122-132
_routing_downgrade() {
  case "${1:-}" in
    opus) echo "sonnet" ;;
    sonnet) echo "haiku" ;;
    haiku) echo "haiku" ;;
    *) echo "${1:-haiku}" ;;   # <-- "fable" echoed back unchanged, not downgraded
  esac
}
```
Phase 1's own acceptance criteria list "add `fable` to ... `_routing_model_tier` in `lib-routing.sh`" as explicit scope — so this is a known Phase 1 TODO, not an oversight the plan is unaware of. The risk is sequencing: if the agency-spec wiring (loading `fable` into `agency.models.*`) ships before `_routing_model_tier`/`ParseModelTier` are updated, the interim state silently misclamps rather than erroring, and nothing in the plan's Phase 1 acceptance criteria ("`routing_resolve_model --phase=planned --category=planning` → fable (or opus fallback)") would catch the tier-comparison bug specifically, since a manual test of the *fallback* path looks correct by coincidence (unknown tier reads as lowest, floor comparison forces a clamp that happens to often be the desired opus/sonnet outcome for a low-trust context) while being wrong for the general case (a high-trust agent with no floor set would still get whatever `applyFloor`'s early-return-on-no-floor logic does — need the Phase 1 PR to add an explicit test for an agent *with* a floor set receiving `fable`).

**Suggestion:** Phase 1's acceptance criteria should add one explicit test: `_routing_apply_safety_floor` (or Go `applyFloor`) called with `model=fable` and a real floor (e.g. `min_model: sonnet`) must NOT clamp fable down (frontier should never be blocked by a floor meant to raise a minimum), and must correctly recognize fable as tier 4 (above opus) in both `_routing_model_tier` and `ParseModelTier` before the agency spec is wired to select it. This is a same-PR sequencing note, not new scope.

**Verdict:** Confirmed gap, correctly scoped by the plan's own Phase 1 task list, but the plan doesn't call out the *order* dependency (tier-table update must land before/atomically-with agency-spec wiring) or a test for the "fable + floor" interaction specifically — worth a one-line acceptance-criteria addition.

---

## Finding 4 — Agent frontmatter `model:` is a fourth selection surface the plan never mentions routing through the kernel

**Severity:** P3

**Where:** `.claude/agents/*.md`, `os/Clavain/agents/{review,workflow}/*.md`, `interverse/interflux/agents/{research,review}/*.md` — 751 files with `model:` frontmatter (731 `sonnet`, 96 `opus`, 60 `inherit`, 54 `haiku`, plus scattered literal model-ID strings and non-Claude models for cross-provider agents).

**What:** This is Claude Code's own Task-tool subagent model selection — a build-time/file-level literal, entirely independent of `lib-routing.sh`/`ic route`. It's the mechanism that actually determines what model a dispatched subagent (fd-safety, fd-architecture, etc.) runs on when invoked via the `Agent`/Task tool, as opposed to a Codex/Bash dispatch. Zero files declare `model: fable` today, and it's unclear whether Claude Code's frontmatter schema even accepts "fable" as a value (it's an internal/alias name for a specific Claude model version, not a documented frontmatter enum value). None of the four phases in the plan mention this surface at all — Phase 1's "wire `/sprint` to `ic agency load` the spec when the session model is fable" only affects the bash/kernel resolution layer that presumably feeds *dispatch.sh*-driven Codex calls and the `routing_resolve_agents`/`routing_resolve_model_complex` path that determines *which model string gets passed to a dispatch*, but subagent frontmatter is a separate, static, per-file declaration that the routing kernel has no lever over.

**Evidence:** `grep -rn "^model:" .claude/agents/*.md | ... | sort | uniq -c` shows the full distribution above; `grep -rn "fable" .claude/agents/*.md` and equivalent for `os/Clavain/agents/` and `interflux/agents/` return zero hits. `routing_resolve_agents` (`lib-routing.sh:1382`) resolves a *model string* for a named agent for **dispatch purposes** (Codex/interserve), but nothing in this repo writes that resolved value back into an agent's own frontmatter `model:` field, nor does Claude Code's Task tool consult `ic route model` before spawning a subagent with its frontmatter-declared model.

**Suggestion:** Not a bug in the current plan's stated scope (fable/escalation is scoped to Clavain-orchestrated dispatch, not Claude Code's native Task-tool subagent spawning) — flag as an open question for the plan's "Design considerations" section: does "fable does planning/architecture" extend to review-agent subagents like fd-architecture (currently pinned to `model: sonnet` in frontmatter), and if so, is frontmatter-level routing in scope for a future phase, or explicitly out of scope? Worth one sentence in the doc to prevent scope-creep surprise later.

**Verdict:** Not a bug — a scope-boundary gap. Flagging as a question per the lens's "frame uncertain findings as questions" guidance: should Phase 5 (Go router parity) or a Phase 6 also cover frontmatter-level model selection, or is that permanently out of the kernel's reach by design?

