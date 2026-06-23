---
title: Define and enforce the interflux-intersynth synthesis contract
date: 2026-06-22
bead: sylveste-te7b
status: brainstorm (pre-review) — FOR REVIEW, do not implement
authors: design-draft subagent
---

# interflux ↔ intersynth synthesis contract

## Frame

Flux-review of the interflux roadmap (`interverse/interflux/docs/research/flux-research/interflux-roadmap-priorities/repo-research-analyst.md`, finding #3, line 81-83) found that interflux's synthesis pipeline is **load-bearing on intersynth but the dependency is implicit**. The bead asks for a versioned synthesis contract covering: inputs, output schema, failure behavior, fallback behavior, and dependency declaration between the two plugins.

This is an architecture/contract decision, not a code task. The deliverable is this doc plus an explicit list of decisions the human must confirm before anyone writes the contract spec or touches the call sites.

**The exact words of the flux-review finding (verified at file:line):**

> `phases/synthesize.md` Step 3.2 delegates ALL synthesis work (collection, deduplication, move validation, discourse health, verdict writing) to `intersynth:synthesize-review` and `intersynth:synthesize-research`. The host agent never reads individual agent output files. This is an important architectural decision — it keeps agent prose out of the host context — but intersynth is a separate plugin with its own lifecycle. There is no documented interface contract between interflux and intersynth: no schema for the expected prompt parameters, no versioning of the delegation protocol, and no graceful degradation behavior if intersynth is unavailable. If intersynth's synthesis agents change their behavior or the plugin is absent, flux-drive synthesis silently breaks.
> — `repo-research-analyst.md:83`

## What the code actually does today (verified)

### The delegation call sites

`interverse/interflux/skills/flux-engine/phases/synthesize.md` Step 3.2 (line 45-98) issues two delegation calls depending on `MODE`:

**Review mode** (synthesize.md:69-80):
```
Task(intersynth:synthesize-review):
  OUTPUT_DIR={OUTPUT_DIR}
  VERDICT_LIB=auto
  MODE=flux-drive
  CONTEXT="Reviewing {INPUT_TYPE}: {INPUT_STEM} ({N} agents, {early_stop_note})"
  FINDINGS_TIMELINE={OUTPUT_DIR}/peer-findings.jsonl
  LORENZEN_CONFIG={lorenzen_config_json}
```

**Research mode** (synthesize.md:49-59):
```
Task(intersynth:synthesize-research):
  OUTPUT_DIR={OUTPUT_DIR}
  VERDICT_LIB=auto
  RESEARCH_QUESTION={RESEARCH_QUESTION}
  QUERY_TYPE={type}
  ESTIMATED_DEPTH={estimated_depth}
```

The same calls are duplicated/echoed in:
- `skills/flux-research/SKILL.md:243-264`
- `skills/flux-research/SKILL-compact.md:13,36`
- `skills/flux-engine/SKILL.md:339`
- `skills/flux-engine/SKILL-compact.md:295,301`

There is a **third** consumer outside interflux: `intersynth:synthesize-documents` is invoked by Clavain's `/compound` and `/reflect` flows (per intersynth AGENTS.md:13 and synthesize-documents.md:2). The bead names interflux↔intersynth, but the contract surface is actually intersynth's three agents against multiple callers. (See Open Question 6.)

### The input contract intersynth expects (verified)

The synthesis agents already document their own input parameters as prose under "Input Contract" headers:
- `intersynth/agents/synthesize-review.md:9-11` — `OUTPUT_DIR`, `VERDICT_LIB`, `CONTEXT`, `MODE`, `PROTECTED_PATHS`, `FINDINGS_TIMELINE` (optional), `LORENZEN_CONFIG` (optional).
- `intersynth/agents/synthesize-research.md:10-16` — `OUTPUT_DIR`, `VERDICT_LIB`, `RESEARCH_QUESTION`, `QUERY_TYPE`, `ESTIMATED_DEPTH`.
- `intersynth/agents/synthesize-documents.md:9-16` — cluster of docs, topic, existing solutions (described in prose, NOT as named prompt params).

**Mismatch already present:** synthesize-review documents `PROTECTED_PATHS` as an input (synthesize-review.md:11), but the interflux review-mode call site (synthesize.md:69-80) never passes it. So the documented input contract and the actual call site already disagree. This is the kind of silent drift the bead is about.

### The output contract intersynth produces (verified)

Review mode writes (synthesize-review.md:96-101):
- `{OUTPUT_DIR}/synthesis.md` — full human report.
- `{OUTPUT_DIR}/findings.json` — structured findings with a documented superset schema (convergence, stemma, reactions, hearsay, dwsq, discourse_health, etc.).
- `.clavain/verdicts/{agent}.json` via `lib-verdict.sh` (intersynth/hooks/lib-verdict.sh:21-49).
- A ≤15-line return string (synthesize-review.md:104-116).

**But there is a name collision in the docs.** synthesize-review.md:96-101 says it writes `synthesis.md`. The interflux phase file says the review path writes **`summary.md`** (synthesize.md:98, 102, 423) and the spec `docs/spec/core/synthesis.md` Step 7 (line 293-295) also says **`summary.md`**. So:
- Research mode: both sides agree on `synthesis.md`.
- Review mode: intersynth's agent doc says `synthesis.md`; interflux's phase + spec say `summary.md`.

This is an active, undetected contract disagreement on the output filename. (See Key Decision 4 and Open Question 1.)

### The findings.json schema is defined in TWO places that have diverged

- `docs/spec/core/synthesis.md` Step 6 (line 207-291) — the spec schema.
- `skills/flux-engine/phases/synthesize.md` Step 3.4a (line 180-216) — a *different, simpler* findings.json shape, plus `cost_report` (Step 3.4b, line 251-305).
- `intersynth/agents/synthesize-review.md:100` — yet a third description ("findings.json: Structured JSON with ... convergence, stemma, reactions, hearsay, co_located, cross_references, improvements, verdict, perspectives, dwsq, ...").

Three descriptions of the same artifact, owned by two repos, none referencing the others as canonical. There is no `schema_version` field anywhere in findings.json. (Note: this exact "result schema needs a version" problem is also the subject of sibling bead **sylveste-rrn4** for the interweave F5 QueryTemplate — same failure class, different subsystem.)

### Dependency declaration (verified)

- `interflux/.claude-plugin/plugin.json:73-82` lists `intersynth` under `peerDependencies` (alongside intercept, interknow, interpeer, interrank, interspect, interstat, intertrust).
- `interflux/.claude-plugin/integration.json` lists intersynth under `companions.recommended` — NOT under `integrated_features.requires`.

So the **declared** posture is "intersynth is a recommended companion, optional." The **actual** posture is "synthesis hard-fails without it, and the host is explicitly forbidden from reading agent files itself" (synthesize.md:47: "Do NOT read agent output files yourself"). The declaration and the runtime reality contradict each other. This is the core of the bug.

### Failure / fallback behavior (verified absent)

I grepped `skills/` and `docs/spec/` for any fallback path when intersynth is missing or its Task fails. Every *other* progressive enhancement in interflux has an explicit "skip if unavailable" fallback:
- qmd: "Skip entirely if qmd unavailable" (progressive-enhancements.md:35)
- interrank: "Skip silently if interrank MCP unavailable ... Never a gate" (progressive-enhancements.md:118)
- interstat: "Fallback: If interstat has no data yet ..." (synthesize.md:242)
- lib-routing: "Fallback: if lib-routing.sh unavailable, agents use frontmatter defaults" (launch.md:46)
- Oracle: "If the Oracle command fails or times out ... Do NOT block synthesis" (agent-roster.md:80)

**intersynth has none.** There is no documented behavior for: intersynth not installed, the synthesis Task erroring, the agent returning malformed output, or `synthesis.md`/`findings.json` not getting written. The synthesis spec's "Error Handling" table (synthesis.md:404-413) covers *agent-output* failures (timeout, malformed, all-agents-failed) but assumes the synthesizer itself runs. The one place the host is told NOT to fall back is also the one dependency with no fallback. This is the highest-severity gap.

### Versioning (verified absent)

- interflux: `0.2.70` (plugin.json:3).
- intersynth: `0.1.12` (intersynth/plugin.json:3).
- flux-drive-spec: `1.0.0` (docs/spec/README.md:2), explicitly "independent of interflux's version" (README.md:100).

No artifact ties an interflux version to an intersynth version, or to a "synthesis delegation protocol" version. intersynth could ship `0.2.0` changing its return-string format and nothing in interflux would notice until a review silently produced a malformed summary.

## Existing patterns to reuse (do not reinvent)

The interflux repo already has a **contracts** convention that this work should extend, not replace:

- `docs/spec/contracts/findings-index.md` — agent↔orchestrator output format contract.
- `docs/spec/contracts/completion-signal.md` — agent↔orchestrator completion-signal contract.

Both follow a fixed template: `# Title` → `> flux-drive-spec X.Y | Conformance: <level>` → Overview → Specification → "interflux Reference" → Conformance (MUST/SHOULD/MUST NOT/MAY). This is the right home and the right shape for a synthesis-delegation contract. The README.md "Contracts (Required)" table (README.md:34-40) is where a new contract gets registered.

The flux-review finding itself (repo-research-analyst.md:77) flags that "the intersynth delegation pattern ... has no spec coverage" — i.e., the spec already *wants* this document; it's a known hole.

## Proposed design

### One sentence

Write a new contract document `docs/spec/contracts/synthesis-delegation.md` that formalizes the interflux→intersynth delegation interface (input params, output artifacts, return-string shape, versioning, and a mandatory host-side fallback), add a `synthesis_protocol_version` field to the call/return surface, fix the declaration mismatch so intersynth is correctly marked as a hard runtime dependency of the synthesis phase, and add a thin conformance check.

### Component 1 — The contract document

New file: `interverse/interflux/docs/spec/contracts/synthesis-delegation.md`, registered in `docs/spec/README.md` Contracts table. Sections:

1. **Overview** — interflux delegates synthesis to intersynth to keep agent prose out of the host context; this contract is the interface between them.
2. **Input contract** — the canonical, named prompt parameters for each of the three modes (review / research / documents), marking each REQUIRED or OPTIONAL, with type and default. This is the single source of truth; both `synthesize.md` call sites and the intersynth agent docs reference it instead of re-declaring. Resolves the `PROTECTED_PATHS` drift.
3. **Output contract** — the exact artifacts each mode writes (filename, who reads it), the findings.json field set with a `schema_version`, and the return-string shape (line cap + required fields). Resolves the `synthesis.md` vs `summary.md` collision.
4. **Versioning** — a `synthesis_protocol_version` (e.g. `1.0`) carried in the delegation prompt and echoed in the return string + findings.json. Semver: major = breaking I/O change, minor = additive. Decoupled from both plugin versions and from flux-drive-spec, exactly as flux-drive-spec is decoupled from interflux's version (README.md:100).
5. **Failure & fallback behavior** — the missing piece. Defines:
   - **Detection**: intersynth absent (Task tool reports unknown agent), Task errors, or expected output files not written after return.
   - **Host fallback**: a documented degraded path. The host reads the Findings Indexes itself (≤30 lines/agent per the index-first rule in synthesis.md spec Step 2) and produces a minimal summary + deterministic verdict (P0→risky, P1→needs-changes, else safe — synthesis.md spec Step 5). This deliberately loses the discourse layer (reactions, Lorenzen, stemma, dwsq) but preserves the core review verdict. The fallback is explicitly labeled "degraded synthesis — intersynth unavailable" in user output so it is never silent.
   - **Version mismatch**: if the returned `synthesis_protocol_version` major differs from what interflux expects, warn and treat as degraded (don't trust the output schema).
6. **Dependency declaration** — states that intersynth is REQUIRED for full-fidelity synthesis and that the host MUST implement the degraded fallback so the plugin remains standalone-functional. Reconciles plugin.json/integration.json with reality.
7. **interflux Reference** — points at the call sites (synthesize.md:45-98) and intersynth agents.
8. **Conformance** — MUST/SHOULD/MUST NOT/MAY, matching the house template.

### Component 2 — Reconcile the declaration

Pick ONE coherent posture (see Key Decision 2) and make plugin.json, integration.json, and the contract agree. Recommended: keep intersynth as a `peerDependency` (it stays a separate plugin) but document in the contract that synthesis-phase fidelity is reduced without it, and require the host fallback so interflux degrades instead of breaking. This makes the existing "recommended companion" declaration *true* instead of a lie.

### Component 3 — Carry the protocol version on the wire

Add `SYNTHESIS_PROTOCOL_VERSION=1.0` to each delegation prompt (synthesize.md call sites) and require intersynth's return string to echo it. Cheap, additive, makes drift detectable. intersynth's agent docs add one line: "Echo `Protocol: {SYNTHESIS_PROTOCOL_VERSION}` in the return string."

### Component 4 — A thin conformance check (optional, recommended)

A test under `interflux/tests/` (or `intersynth/tests/`) that asserts: (a) the contract doc's documented input params are a superset of what the call sites pass, (b) the documented output filenames match what the spec + agents claim. This is the mechanism that keeps the contract from rotting — it is the same class of guard that `scripts/verify_frontmatter.py` already applies to agent frontmatter (verify_frontmatter.py:64 already enumerates `interverse/intersynth/agents`). (See Open Question 5 — which repo owns the test, given subrepo independence.)

### What this design deliberately does NOT do

- Does not move synthesis logic back into the host (the context-isolation win is real; the fix is a contract + fallback, not de-delegation).
- Does not merge interflux and intersynth into one plugin (they have independent lifecycles by design — intersynth README.md:39-43).
- Does not redesign findings.json. It version-stamps and points to one canonical definition; reconciling the three diverged copies is noted as follow-on (Open Question 2), not in scope here.
- Does not add research-side quality mechanisms (peer findings, source ranking during dispatch). That is finding #8 of the same flux-review (repo-research-analyst.md:110-118), a separate bead.

## Three options considered

**Option A — Documentation-only contract (conservative).** Write `synthesis-delegation.md` describing the existing I/O exactly as-is, fix the two doc collisions (`PROTECTED_PATHS`, `summary.md`/`synthesis.md`), no version field, no fallback code path beyond a documented "if intersynth missing, synthesis fails — install it." Cheapest. Closes the "no documented contract" half of the finding but leaves "no graceful degradation" open. Rejected as insufficient: the bead explicitly lists "failure behavior, fallback behavior" as required.

**Option B — Contract + version + mandatory fallback (balanced, recommended).** Components 1-3 above, plus the conformance check (Component 4) as a stretch. Closes the whole finding. Moderate cost: one new spec doc, ~3 small call-site edits, ~3 one-line agent-doc edits, one declaration reconciliation. Reversible (the fallback is additive; the version field is additive).

**Option C — Hardened delegation runtime (aggressive).** B plus: a real version-negotiation handshake, intersynth emitting a machine-checkable `synthesis-manifest.json` declaring its protocol version + capabilities, and interflux refusing to delegate on major-version mismatch. Highest assurance, highest cost, and probably over-engineered for two first-party plugins in one monorepo that ship together. Hold unless cross-repo/external-adopter pressure appears.

Recommendation: **Option B.**

## Key decisions the human must confirm

1. **Scope = Option B (contract + version + mandatory host fallback + thin conformance check)?** Or trim to Option A (docs-only) / expand to Option C (handshake)? The bead's wording ("failure behavior, fallback behavior") points at B as the floor.

2. **Dependency posture.** Confirm intersynth stays a `peerDependency` / recommended companion AND the host MUST implement a degraded fallback (so interflux is standalone-functional) — vs. promoting intersynth to a hard required dependency and having synthesis legitimately hard-fail without it (simpler, but breaks the "standalone" claim in integration.json:5). Recommendation: keep peer + require fallback.

3. **Fallback fidelity.** Confirm the degraded path = "host reads Findings Indexes, emits minimal summary + deterministic verdict, drops the discourse layer, labels output as degraded." Acceptable to lose reactions/Lorenzen/stemma/dwsq when intersynth is absent? (Alternative: no fallback, just a clear install error.)

4. **Canonical output filename for review mode.** intersynth's agent says `synthesis.md` (synthesize-review.md:96); interflux phase + spec say `summary.md` (synthesize.md:98, synthesis.md spec Step 7). Pick one as canonical and fix the other. Recommendation: `summary.md` for review (matches the spec, the larger surface), `synthesis.md` for research (both already agree). This means intersynth's synthesize-review.md gets corrected.

5. **Which repo owns the contract doc and the conformance test?** interflux owns the existing `docs/spec/contracts/` and the README registry, so the contract doc lives in interflux. But intersynth is the implementer. Confirm: contract doc in `interflux/docs/spec/contracts/`, with a back-reference added to `intersynth/CLAUDE.md`/`README.md`. Conformance test: in interflux (the consumer/spec owner) or intersynth (the producer)? Recommendation: interflux owns it; both are independent git subrepos, so this is a cross-repo coordination point, not a single commit.

6. **Contract surface = interflux↔intersynth only, or all three intersynth callers?** The bead names interflux↔intersynth, but `synthesize-documents` is consumed by Clavain `/compound` + `/reflect`, and Clavain keeps a backward-compat copy of `lib-verdict.sh` (intersynth README.md:37). Confirm: scope this contract to the two flux-driven agents (review/research) and note documents-synthesis + Clavain's lib-verdict copy as a follow-on, OR widen now to cover all three agents and the Clavain consumer.

## Open questions

1. Is `summary.md` vs `synthesis.md` (review mode) an actual runtime bug today, or does it work because the host re-derives the path from its own template and never trusts intersynth's filename claim? Worth a one-shot live `/flux-drive` run to see which file actually gets written before we "fix" the doc that's correct. (Verification-before-fix.)

2. The findings.json schema exists in three diverged descriptions (spec Step 6, synthesize.md Step 3.4a, synthesize-review.md:100). Reconciling them is bigger than this bead. File a follow-on, or fold a "canonical findings.json schema + schema_version" decision into this contract? Note the sibling bead **sylveste-rrn4** is the same problem class for interweave's QueryResult — worth a shared decision on how schema_version is stamped across the ecosystem.

3. Does any consumer actually parse intersynth's ≤15-line return string programmatically, or is it only read by a human/host LLM? If only read by an LLM, the "return-string shape" half of the contract can be SHOULD not MUST. (Determines how strict Component 3 needs to be.)

4. `VERDICT_LIB=auto` resolution (synthesize-research.md:38-45) reaches into `${CLAUDE_PLUGIN_ROOT}/hooks/lib-verdict.sh` — but whose plugin root? If the synthesis agent runs in intersynth's context, `CLAUDE_PLUGIN_ROOT` points at intersynth, which is correct; if dispatched oddly it could resolve wrong. Worth confirming the auto-resolution actually finds intersynth's copy and not Clavain's stale backward-compat copy. (Affects whether `lib-verdict.sh` belongs in the contract surface.)

5. Subrepo discipline: interflux and intersynth are independent git repos (per MEMORY: "Sylveste subprojects are independent git repos"). A change touching both is two commits in two repos that must land compatibly. Should the contract doc define a compatibility window (interflux N works with intersynth ≥ M) to make the two-commit dance safe? This is the practical reason the version field (Component 3) matters even inside one monorepo.

6. Is there appetite to also give the research path interflux-side quality mechanisms (flux-review finding #8, repo-research-analyst.md:110)? Out of scope for this contract, but the contract should not foreclose it (e.g., reserve a research peer-findings input param).

## Verification notes (claims checked against code)

- Delegation call sites: `interverse/interflux/skills/flux-engine/phases/synthesize.md:45-98` (verified by Read).
- intersynth input contracts: `synthesize-review.md:9-11`, `synthesize-research.md:10-16`, `synthesize-documents.md:9-16` (verified).
- `PROTECTED_PATHS` documented but not passed: synthesize-review.md:11 vs synthesize.md:69-80 (verified).
- Output filename collision: synthesize-review.md:96 (`synthesis.md`) vs synthesize.md:98/spec synthesis.md:295 (`summary.md`) (verified).
- No fallback for missing intersynth: grep of `skills/` + `docs/spec/` for fallback/degrade around synthesis returned only *other* subsystems' fallbacks (verified).
- Dependency declaration: `interflux/.claude-plugin/plugin.json:73-82` (peerDependencies) + `integration.json` companions.recommended (verified).
- Version skew: interflux 0.2.70, intersynth 0.1.12, flux-drive-spec 1.0.0, spec explicitly independent of interflux version (README.md:100) (verified).
- Contract house style: `docs/spec/contracts/completion-signal.md`, `findings-index.md`, README.md:34-40 contracts table (verified).
- Spec already wants this doc: repo-research-analyst.md:77 ("intersynth delegation pattern ... has no spec coverage") (verified).
