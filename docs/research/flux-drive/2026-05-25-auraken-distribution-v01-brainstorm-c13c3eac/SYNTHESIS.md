<!-- flux-drive:synthesis -->
<!-- run_uuid: 57272bdd-9eb0-42d1-8ae7-ed79e4d7aa8a -->

# Flux-drive Synthesis — Auraken Distribution v0.1 Brainstorm

**Target:** `docs/brainstorms/2026-05-25-auraken-distribution-v01-brainstorm.md`
**Bead:** `sylveste-heh8`
**Run UUID:** `57272bdd-9eb0-42d1-8ae7-ed79e4d7aa8a`
**Date:** 2026-05-25
**Agents:** fd-distribution-installer-safety, fd-mcp-server-packaging, fd-skill-bundle-conformance, fd-versioning-compatibility, fd-onboarding-ux (5 Project Agents, Stage 1, all completed)

> **Cross-run note:** `OUTPUT_DIR` shows files from a concurrent flux-drive run with different `run_uuid` values (`fed42cc6-…`, `1e048f43-…`, etc., agents `fd-tea-ceremony-densho`, `fd-aoidos-formulaic-epic`, `fd-perfumery-grasse-composition`, etc.). Those are excluded from this synthesis — see the run-isolation caveat in `references/run-isolation.md` (also flagged below as a finding for the operator).

## Verdict

**Ship-blocking issues exist.** Three P0 findings and sixteen P1 findings span all five specialist domains. The brainstorm is **structurally sound** (correct framing, sensible scope discipline via `excluded_from_v01`, right approach choice (A)) but **mechanically underspecified** in three areas that must be resolved before plan-phase can commit to implementation:

1. **The dist bundle does not yet contain a working MCP server.** server.py imports `auraken.lenses` from a path that resolves only inside the monorepo (P0 × 2). Either vendor the Python package or switch to the Go binary — the brainstorm reads both ways and commits to neither.
2. **install.sh's six-step contract is non-atomic.** Step 5 (venv + YAML config write) has no rollback story; a partial failure leaves a half-configured Hermes profile (P0).
3. **MANIFEST.yaml compatibility claims are unverified.** Model identifiers mix short and dated forms, Hermes lower bound has no cited evidence, Go binary tag is not verified to exist.

The right plan-phase artifacts to unblock these: (a) build-dist.sh + state-transition table + INSTALL-SMOKE.md transcript; (b) explicit Python-vs-Go decision for lens selection; (c) compatibility-evidence table backing each MANIFEST claim.

## Triage Result

| Agent | Score | Stage | Finding count | Severity distribution |
|---|---|---|---|---|
| fd-distribution-installer-safety | 7 | 1 | 7 | P0:1 P1:3 P2:2 P3:1 |
| fd-mcp-server-packaging | 7 | 1 | 8 | P0:2 P1:3 P2:2 P3:1 |
| fd-skill-bundle-conformance | 7 | 1 | 7 | P0:0 P1:3 P2:3 P3:1 |
| fd-versioning-compatibility | 7 | 1 | 8 | P0:0 P1:4 P2:3 P3:1 |
| fd-onboarding-ux | 7 | 1 | 8 | P0:0 P1:3 P2:3 P3:2 |
| **Total** | | | **38** | **P0:3 P1:16 P2:13 P3:6** |

Scoring: base=3 (core overlap) + domain_boost=+2 (auraken-distribution match) + project_bonus=+1 + domain_agent=+1 = 7 each. All Stage 1, no expansion needed. Concurrency cap `MAX_CONCURRENT_AGENTS=3` honored via two dispatch waves.

## P0 Findings (ship-blocking)

### P0-1 — `AURAKEN_SRC` resolves to a monorepo-relative path (mcp-server-packaging F1)

server.py:41 uses `_HERE.parents[3] / "src"` to find `auraken.lenses`. After install, `_HERE.parents[3]` is `~/` and the import target doesn't exist. Every user install fails at server startup with `ModuleNotFoundError`; Hermes silently logs the MCP failure; `/auraken` partially loads (skill yes, lens_select no). **Fix:** vendor or shell-out (see P0-2).

### P0-2 — Lens-selection backend vendoring strategy undefined (mcp-server-packaging F2)

server.py imports the legacy Python `auraken.lenses`. MANIFEST capability says `binary_required: …/auraken-lens@v0.1.0` (Go binary). The brainstorm does not commit to one path. The bundle layout (lines 32–48) includes neither the Python package nor the Go binary — only the MCP server and skill files. **Fix:** plan-phase decision; recommended is shell-out to the Go binary, consistent with the brainstorm's release-asset story.

### P0-3 — install.sh step 5 (venv + MCP config write) is non-atomic (installer-safety F1)

Three filesystem operations chained without staging or rollback. Power-loss, Ctrl-C, or write-permission failure between (a) venv build, (b) `pip install -e .`, and (c) `mcp_servers:` config snippet append leaves the user with a working venv that's not registered and a SKILL.md already copied. **Fix:** stage all step-5 writes to side paths; atomic `mv` at end.

## P1 Findings (gate-blocking, by domain)

### Installer mechanics

- F2 — Idempotency mechanism unspecified (marker-file model recommended)
- F3 — Version-gate ordering vs. profile mutation (need `PROFILE_WRITES_OK` invariant)
- F4 — Profile-discovery fallback ambiguity (need `HERMES_CONFIG_DIR` env support)

### MCP server packaging

- F3 — `pyproject.toml` missing `uvicorn`/`starlette` for http transport
- F4 — Unbounded `mcp>=1.0.0` invites 2.x breakage
- F5 — `trajectory.py` sibling-import contract needs `py-modules` directive

### Skill bundle conformance

- F1 — SKILL.md frontmatter missing `version`, `license`, `author`, `homepage`, `compatibility` — blocks v0.2 agentskills.io path
- F2 — `lens_select` invocation timing not enforceable across providers
- F3 — "Never" assertions are voice rules, not runtime constraints — register_check should be a runtime hook

### Versioning + compatibility

- F1 — Hermes `>=2026.4.0` lower bound has no cited evidence
- F2 — Model identifiers mix short and dated forms (claude-opus-4-7 vs. claude-haiku-4-5-20251001)
- F3 — Register drift annotated only in YAML comments; not data-visible
- F4 — `auraken-lens@v0.1.0` Go module tag is unverified

### Onboarding UX

- F1 — First `/auraken` invocation may leak Hermes skill-load boilerplate, violating SKILL.md's no-preamble rule on first contact
- F2 — INSTALL.md prerequisite ordering undefined (one-liner-before-prereqs risk)
- F3 — macOS-untested caveat placement (silent install-to-wrong-dir risk)

## Cross-cutting Themes

### Theme A — "Curated copy" is an unfinished concept

Three agents (mcp-server-packaging F1/F2/F6, versioning F2/F4/F7, skill-bundle F1) independently land on the same gap: the brainstorm names `dist/v0.1/` as "a curated copy + version stamps" without specifying which files cross from dev tree to dist, with what rewrites, with what version pinning. The unifying fix is a **scripts/build-dist.sh** that produces dist/v0.1/ from explicit file paths and rewrites — not `cp -r`. This single artifact closes F1/F6/F7 in mcp-packaging, F4/F8 in versioning, F1 in skill-conformance, and makes idempotency in installer-safety tractable (because dist is now a known-shape input).

### Theme B — Acceptance evidence is missing for every external claim

The brainstorm asserts: Hermes `>=2026.4.0`, models work, install.sh is idempotent, macOS is "expected to work", behavioral assertions in SKILL.md are enforced. None of these have cited evidence in the brainstorm or in the recon-spike artifacts. Plan phase needs **three evidence artifacts**:
1. A compatibility-evidence table (versioning F1/F2/F3/F4)
2. An install-smoke transcript (onboarding F1/F2; installer-safety F1/F5)
3. A SKILL.md behavioral spec → test-conversations.md mapping (skill-conformance F2/F3)

These are cheap to produce now and expensive to retrofit after release.

### Theme C — Privacy/observability is undersurfaced

Trajectory recording (server.py:139–148) writes a JSON line per `lens_select` call to `~/.hermes/auraken/trajectories/`. No agent explicitly flagged this as P0/P1, but **onboarding F8 (P3)** notes users won't discover the recording until they happen to `ls`. The brainstorm should at minimum document this in INSTALL.md "data collection" section. Consider whether v0.1 ships with trajectory recording opt-in or opt-out by default — current default is opt-out (`AURAKEN_TRAJECTORY_DIR` env override), which a privacy review (if commissioned) might flag.

### Theme D — Pre-launch UX decisions compound

Several P1/P2 findings (installer F5 exit-diagnostics, onboarding F1/F4 first-impression, skill-conformance F6 OODARC leakage) are about **what the user sees first**. v0.1 sets the tone for v0.2 and v0.3. The brainstorm's choice of approach A (decouple bundle from demo) makes this tractable — v0.1 has a small surface that's testable in isolation — but the surface still needs polish.

## Process Note: Concurrent-Run Race

This OUTPUT_DIR (`…-c13c3eac`) was used by **two flux-drive runs simultaneously** — the requested one (this synthesis, run_uuid `57272bdd-…`) and a parallel cross-track run with esoteric/orthogonal agents (run_uuid `fed42cc6-…` and others). The second run's pre-clean (per skill spec line "find {OUTPUT_DIR} -maxdepth 1 … -delete") deleted two of this run's finding files mid-execution; they were rewritten. This is the documented race condition in `phases/launch.md` ("two flux-drive invocations on the same target with overlapping execution share OUTPUT_DIR and can race"). For genuinely concurrent runs, the calling layer should pass `--output-dir <unique>` to force isolation.

Listing the foreign files for transparency (not part of this synthesis):
- `fd-aoidos-formulaic-epic.md`, `fd-field-guide-scope-discipline.md`, `fd-instrument-kit-packaging.md`, `fd-perfumery-grasse-composition.md`, `fd-reliquary-translation.md`, `fd-studio-preset-pack-onboarding.md`, `fd-tea-ceremony-densho.md`, `fd-typeface-retail-release.md`

## Recommendations

**Before plan phase begins:**

1. **Decide P0-2** (Python vendor vs. Go shell-out for lens selection). This blocks pyproject.toml shape, install.sh prerequisite check, and MANIFEST `binary_required` accuracy.
2. **Write `scripts/build-dist.sh`** as the canonical dist builder. Closes Theme A.
3. **Run the recon spike's `/auraken` invocation against a known Hermes version and capture the literal byte stream** — confirms whether F1 in onboarding-ux is a real or theoretical concern.

**During plan phase:**

4. **Author the state-transition table for install.sh** (six rows × four columns).
5. **Author the compatibility-evidence table** (one row per claimed Hermes × model × platform combination).
6. **Author INSTALL-SMOKE.md** (walkthrough transcript for a fresh-machine install).
7. **Extend SKILL.md frontmatter** to include `version`, `license`, `author`, `homepage`, `compatibility` — single-sourced from MANIFEST.yaml at build time.
8. **Define the register_check runtime hook** in voice-rubric.md — either it's a runtime feature (the MCP server enforces) or it's human-docs (and SKILL.md should say so).

**Out of scope for v0.1 (track separately):**

- F6 onboarding (one-liner-URL fragility) — workable with documentation; redirector is v0.2
- F8 versioning (machine-readable schema URL) — v0.2
- F8 mcp-server-packaging (package-layout refactor) — v0.2

## Bead Updates (suggested, not auto-applied)

- `sylveste-heh8` plan phase should include the three pre-plan items above as prerequisites
- Consider a sub-bead for the build-dist.sh artifact (touches mcp-packaging, versioning, installer-safety)
- Consider a sub-bead for the compatibility-evidence table (touches versioning + plan-phase smoke testing)
