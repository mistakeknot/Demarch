<!-- flux-drive:complete -->
# fd-config-resolver-architecture — Microrouter Track B6 Schema & Resolver Architecture Review

**Persona**: Configuration-driven systems architect designing layered policy resolver chains, API schema versioning, and middleware pipelines.
**Scope**: schema extension correctness, six-track chain integrity, endpoint architecture, zero-cost-bypass guarantee. Anti-overlap with cascade design, LoRA pipeline, eval methodology, rollout safety (covered by sibling agents).

## Findings Index

| # | Severity | Title |
|---|----------|-------|
| 1 | **P0** | Endpoint `localhost:8421/route` collides with B5 interfer server on the same port (port 8421 confirmed in code) |
| 2 | **P0** | "Bump `routing-overrides.schema.json`" targets the wrong file — that schema is for flux-drive interspect overrides, not routing.yaml validation |
| 3 | **P0** | "Clavain Go resolver (path TBD)" — the resolver is `scripts/lib-routing.sh` (Bash), not Go; design assumption is wrong |
| 4 | **P1** | Six-track chain order is encoded in code/comments, not config — accidental reorder is undetectable in code review |
| 5 | **P1** | Zero-cost bypass guarantee for `mode = off` is asserted but not testable as written |
| 6 | **P1** | `microrouter.ineligible_agents` and `subagents.overrides` safety-floor list are not converged at config-load time |
| 7 | **P2** | No JSON Schema for routing.yaml itself — schema bump won't catch mode typos like "enforc" |
| 8 | **P2** | `endpoint:` in routing.yaml is a string; should be a structured `{host, port, path}` to support future routing |

## Verdict

**REWORK BEFORE INTEGRATION.** Three P0s rooted in factual inaccuracies in the bead bodies: (a) the endpoint conflict with B5 is a confirmed breakage, (b) the schema-bump target is a misidentification of which schema validates routing.yaml (there is no such validator in the repo), and (c) the resolver is Bash, not Go. None of these are subtle — they are visible in the codebase right now. The integration bead `.19.5` cannot be picked up for implementation until these three facts are reconciled.

## Summary

The B6 schema and resolver insertion proposal makes three specific architectural assumptions that the codebase contradicts:

1. **Endpoint architecture**: `microrouter.endpoint: "http://localhost:8421/route"` (INPUT.md:343). Confirmed by code inspection (`interverse/interfer/server/__main__.py:22` defaults to port 8421; `scripts/lib-routing.sh:457-459` parses the B5 endpoint from the `local_models` section, currently `http://localhost:8421` per `routing.yaml:729`). The proposed B6 endpoint and the existing B5 endpoint share a port. Either (a) they're the same server with two paths (in which case the schema must say so), (b) they're different servers (in which case the port collision is a deployment failure), or (c) B6 takes over the existing B5 path namespace (in which case B5's `/health` etc. break).

2. **Schema-bump target**: `routing-overrides.schema.json` (INPUT.md:340). I read the file (124 lines, project root `os/Clavain/config/routing-overrides.schema.json`). It is the schema for **flux-drive interspect overrides** — pattern `^fd-[a-z][a-z0-9-]*$` for agent names, action `exclude|propose`, scope with `domains`/`file_patterns`. It has *nothing to do with routing.yaml structure*. There is no JSON Schema in the repo for routing.yaml itself. The "schema bump" as written would either (a) corrupt the interspect schema or (b) silently no-op.

3. **Resolver location**: "Clavain Go resolver (path TBD — find it during implementation; likely `core/intercore` or `os/Clavain/internal`)" (INPUT.md:378). Searched: `find os/Clavain -name "*.go" | xargs grep -l routing.yaml` returns hits in CLI tooling (compose.go, budget.go, etc.) but none of them parse routing.yaml as the resolver — they consume model decisions made elsewhere. The actual resolver is `scripts/lib-routing.sh` (1475 lines, full state machine YAML parser), called from hooks and shell scripts. The proposal's assumption that there is a Go resolver is wrong.

These three findings together explain why bead `.19.5` is currently `BLOCKED` (confirmed by the dep-tree header at INPUT.md:12). The block is not just a dependency wait; the bead body assumes a system shape that doesn't match the codebase.

## Issues Found

### P0 — Endpoint port collision with B5 interfer server

`routing.yaml:729` (B5): `endpoint: "http://localhost:8421"`. The proposed `routing.yaml` `microrouter.endpoint: "http://localhost:8421/route"` (INPUT.md:343) shares the port.

Code confirmation:
- `interverse/interfer/server/__main__.py:22` — interfer server starts on `--port 8421` by default.
- `interverse/interfer/server/mcp.py:14` — MCP client uses `INTERFERE_URL = "http://localhost:8421"`.
- `scripts/lib-routing.sh:761` — B5 health check is `curl -sf --max-time 1 "${_ROUTING_B5_ENDPOINT}/health"`.

If the proposal intends two separate processes both binding port 8421, the second one fails to bind. If it intends one process serving both `/health` (B5) and `/route` (B6), the schema must document this and the interfer server must be modified to add the new endpoint — that work is not scoped in any bead in this epic.

The cascade-design sibling's "garbage response" P1 partly relates to this: under collision, the resolver hitting `localhost:8421/route` may receive a 404 from the existing interfer server and treat it as "endpoint unreachable," falling through to B3 silently with no diagnostic that distinguishes "endpoint down" from "endpoint up but path missing."

**Concrete remedy:** Choose one of:
1. **Same server, two paths**: Add `/route` to the interfer server (`server/__main__.py`). Schema documents this with `endpoint: "http://localhost:8421"` and `route_path: "/route"` separately. Add the work to either `.19.5` or a new bead.
2. **Different servers**: Move B6 to a new port, e.g., `localhost:8422/route`. Update `.19.5` to specify the port explicitly. The interfer server modification work is then unnecessary.
3. **Subdomain routing**: If both servers are eventually expected to grow, route them under a path prefix (`localhost:8421/v1/local-route`, `localhost:8421/v1/microroute`).

Recommend option (2) for v0 — minimal blast radius, no interfer server modification. Re-evaluate when v1 comes around.

### P0 — `routing-overrides.schema.json` is the wrong target file for routing.yaml schema bumps

I read `os/Clavain/config/routing-overrides.schema.json`. Its `$id` is `routing-overrides.schema.json`, `title` is "Interspect Routing Overrides", description is "Agent exclusion and override configuration for flux-drive triage. Written by Interspect (lib-interspect.sh), read by flux-drive (SKILL.md Step 1.2a.0)."

It validates documents like:
```json
{ "version": 1, "overrides": [{ "agent": "fd-foo", "action": "exclude", "reason": "..." }] }
```

It has *nothing* in it about subagents, complexity tiers, calibration, or local_models. The proposal's plan to add a `microrouter:` section to *this* file would fail validation immediately (the schema's top-level `required` is `["version", "overrides"]`, and `additionalProperties: true` for the root is permissive but the `microrouter` content wouldn't be validated by anything).

There is no JSON Schema validator for routing.yaml in the repo. `lib-routing.sh` is the de facto validator (it warns "routing.yaml exists but no subagent defaults were parsed — possible malformed config" at line 514) but it doesn't run as a pre-commit check.

**Concrete remedy:**
1. Drop the reference to `routing-overrides.schema.json` from bead `.19.5`. That file is unrelated.
2. If the team wants a routing.yaml validator, **create one as new work**: write `routing.schema.json`, run it via `ajv-cli` or similar in CI. This is a meaningful improvement but is *not* a single-bead "schema bump" — it requires schema authoring for the existing 5 tracks plus B6.
3. If a validator is out of scope for this epic, document explicitly in `.19.5` "Done when" that there is no schema-level validation for routing.yaml and that misconfiguration is caught at parse time by `lib-routing.sh` warnings.

### P0 — There is no Go resolver; the resolver is `scripts/lib-routing.sh`

INPUT.md:378: `Clavain Go resolver (path TBD — find it during implementation; likely core/intercore or os/Clavain/internal)`.

Confirmed by code inspection:
- `os/Clavain/scripts/lib-routing.sh` — 1475 lines, sourced as a Bash library, exposes `routing_resolve_model`, `routing_resolve_agents`, `routing_classify_complexity`, `routing_resolve_model_complex`. The state machine at lines 201-583 parses routing.yaml directly.
- All callers I traced are shell-side: `hooks/lib-sprint.sh`, `hooks/session-start.sh`, `scripts/clodex-toggle.sh`, `scripts/dispatch.sh`, `scripts/routing-b5-shadow-report.sh`.
- The Go side (`cmd/clavain-cli/*.go`) hits `routing.yaml` for things like `compose.go` and `budget.go` but not for resolution; the actual model-tier decision is shell-scripted.

The proposal's plan to add a microrouter HTTP call from "the Go resolver" is making the wrong shape. To insert B6 in the existing chain, the work is in Bash:
- Add the parsing block for the `microrouter:` section (analogous to `_routing_load_cache`'s `local_models` section at lines 451-491).
- Add a runtime function (e.g., `_routing_apply_microrouter`) that does the HTTP call with `curl --max-time` matching `timeout_ms`, parses the response, validates against `tier_mappings`, and returns the chosen tier or empty on fall-through.
- Wire it into `routing_resolve_model_complex` between B2 and B3 (or wherever the cascade-design sibling's chain-reordering ends up).
- Add tests (Bash + bats? — verify how lib-routing.sh is currently tested).

This is a substantively different effort than "drop a Go middleware in." It's roughly the same complexity but lives in a different language and requires the team to be comfortable in a 1500-line Bash codebase.

**Concrete remedy:** Update `.19.5` "Files touched" to:
- `os/Clavain/scripts/lib-routing.sh` — new parser block + new runtime function + wiring
- `os/Clavain/config/routing.yaml` — new section
- Tests for resolver chain (router on/off, agent ineligible, timeout, garbage response)

Drop the Go and `routing-overrides.schema.json` references from "Files touched."

### P1 — Six-track chain order is encoded in code, not config

The current resolution order (`routing.yaml:517-518` documents it):

> kernel overrides > complexity override > overrides[agent] > calibration > phases[phase].categories[cat] > phases[phase].model > defaults.categories[cat] > defaults.model

This order is encoded in `lib-routing.sh` and only described in routing.yaml comments. There is no machine-readable list. Adding B6 means:

1. Edit lib-routing.sh to insert a new step at the right position.
2. Edit routing.yaml comments to reflect the new order.
3. *Hope* code review catches if those two diverge.

Adding a 7th track later (and a planned `.19.7` confidence-cascade verifier is essentially that) compounds the problem. The cascade-design sibling has the same finding from the cascade-correctness angle.

**Concrete remedy:**
1. **Short-term (in `.19.5`)**: Add the new chain order to routing.yaml as a *YAML list*, not a comment:
   ```yaml
   resolution_chain:
     - kernel
     - complexity
     - microrouter      # NEW
     - overrides_agent
     - calibration
     - phases_categories
     - phases_model
     - defaults_categories
     - defaults_model
   ```
   The list is documentation today, but tomorrow lib-routing.sh can parse it and *honor* the configured order. That's the second step.
2. **Medium-term (a follow-up bead)**: Make lib-routing.sh consume `resolution_chain` as authoritative. Then chain reordering is a config diff reviewable in a single PR.

This is the highest-leverage long-term improvement. Cost: a few hundred lines of refactor in lib-routing.sh. Benefit: every future track addition is a config change.

### P1 — Zero-cost bypass for `mode = off` is asserted but not testable

Existing precedent: `routing.yaml:606-608` says of B2 complexity, "Zero-cost guarantee: when mode=off, routing_resolve_model behaves identically to B1 with no extra function calls, no config parsing, no overhead."

The B6 proposal does not make this guarantee explicitly, but the operator expectation is the same — `mode: off` should be a true zero-cost bypass.

Two questions:

1. **What "zero-cost" means** for B6: no HTTP call (yes, obvious), but also: no JSON parse of the `microrouter:` section, no MLX model load, no curl invocation, no shadow-log open. The bar is "the routing.yaml without a `microrouter:` section is byte-for-byte equivalent to one with `microrouter.mode: off`."
2. **How it's tested**: there's no current test verifying the B2/B3/B5 zero-cost claims. Adding such a test for B6 establishes a pattern; not adding one perpetuates the gap.

**Concrete remedy:** Add to `.19.5` "Done when": "`microrouter.mode: off` adds zero HTTP calls and zero seconds of latency vs. a routing.yaml without the section, verified by a unit test." The test counts curl invocations or hooks `_routing_apply_microrouter` to assert it's not called.

### P1 — `ineligible_agents` and `subagents.overrides` safety lists not converged

(Cross-referenced with cascade-design sibling's same finding from a different angle.)

`subagents.overrides` (`routing.yaml:540-544`) lists fd-safety and fd-correctness in qualified form with model `sonnet`. `microrouter.ineligible_agents` (INPUT.md:347) lists them in bare form. There is no convergence check.

**Concrete remedy:** In `lib-routing.sh`'s `_routing_load_cache`, after parsing both sections, compute the intersection: any agent in `subagents.overrides` with `min_model = sonnet` (semantic: "this agent has a safety floor") must be in `microrouter.ineligible_agents`. Emit a `Warning:` to stderr (matching the existing pattern at line 514) if not. Add a unit test that verifies the warning fires on a config where the lists diverge.

### P2 — No JSON Schema for routing.yaml itself

The routing.yaml file has no validator. Typos like `mode: enforc` (missing 'e') or `mode: enable` (typo) are accepted silently — `lib-routing.sh:454` reads the literal value into the cache, and subsequent comparisons with `[[ "$mode" == "enforce" ]]` are false, so the system silently behaves as `mode: off`.

This is a long-standing gap (B2-B5 share it) but B6 is a good time to address it because:

- The resolver chain is getting more complex; misconfigurations get harder to catch.
- A JSON Schema makes the documented chain-order from P1 enforceable.

**Concrete remedy:** Out of scope for `.19.5`, but worth a follow-up bead. Author `routing.schema.json` covering all six tracks, run via `ajv-cli` in CI (or a Go validator that reuses an existing YAML library — the team is comfortable in Go for tooling). Estimate: 1 day of work, reusable forever.

### P2 — `endpoint:` in routing.yaml is a string; should be structured

The current B5 `endpoint: "http://localhost:8421"` and the proposed B6 `endpoint: "http://localhost:8421/route"` parse the URL with regex (`lib-routing.sh:458`). String parsing of URLs is fragile:

- Trailing slash handling (`localhost:8421/` vs `localhost:8421`)
- Path appending (B6's hardcoded `/route` vs config-supplied path)
- Future TLS support (`https://...`) requires resolver-level changes

**Concrete remedy:** Suggest (not mandate) that v1 of the schema introduce structured endpoints:
```yaml
microrouter:
  endpoint:
    host: localhost
    port: 8422
    path: /route
    scheme: http
```
This is incremental; v0 can keep the URL-string form as long as the resolver normalizes it (strip trailing slash, append `/route` if path is missing, etc.) and `_routing_apply_microrouter` builds the URL from validated parts.

## Improvements

- **Add a `routing.schema.json`** to enable IDE autocomplete and CI validation. This is the single largest config-quality improvement available.
- **Move chain order to YAML list**, parsed and honored by lib-routing.sh. Makes B6 (and future tracks) a structural insertion, not a code edit.
- **Promote `lib-routing.sh` from "Bash library" to first-class component** with a CHANGELOG and version field. It's 1500 lines and load-bearing; it deserves the discipline.
- **Add a `clavain config validate` CLI command** that runs lib-routing.sh's parsers in dry-run mode and reports any warnings. Today the warnings only fire when a hook runs.

## Anti-Overlap (handed off to siblings)

- Resolver chain semantics, mode interactions, response validation → **fd-routing-cascade-design**
- Loss design, training pipeline, judge augmentation → **fd-lora-distillation-pipeline**
- Holdout integrity, gate construction → **fd-eval-methodology-holdout**
- Shadow-soak runbook, rollback procedure, degradation alerting → **fd-production-rollout-safety**
