---
artifact_type: prd
bead: sylveste-heh8
stage: design
---

# PRD: Auraken Hermes Distribution v0.1

## Problem

The Auraken-Hermes overlay validated as a pattern in the 2026-04-17 recon spike (sylveste-4vbg) but has not shipped as a publishable artifact. The recon artifacts under `apps/Auraken/integrations/hermes/` are scattered, unversioned, and not installable by a third party. The MCP server's import paths are monorepo-relative (P0). There is no install script, no version manifest, no integrity verification, no public release. Until a bundle exists, downstream work (thinker-profile MCP, voice-corpus refresh, public demo instance) has no shape to land into, and the Mythos launch arc has no Auraken product to point at.

## Solution

Ship Auraken as a v0.1 distribution bundle: a self-contained, versioned directory under `apps/Auraken/integrations/hermes/dist/v0.1/` that any user with a working Hermes Agent install can install via a tagged GitHub release. v0.1 = the bundle as artifact, not the demo instance (v0.2) and not the thinker-profile track (v0.3). The bundle resolves three P0s (monorepo-relative imports, non-atomic installer, pre-verification curl|bash) and incorporates the "soundpost" decision (auraken-lens returns a single-object response shape — `{lens, rationale, next_question}` — so the never-offer-menu behavioral contract is geometrically enforced, not declarative).

## Strategy-Review Amendments (2026-05-25)

The PRD was reviewed by a 4-agent flux-drive (fd-decisions, fd-systems, fd-user-product, fd-quality). 11 distinct findings after dedup + verification carry into amendments here. Key correction: the Go lens library at `os/Skaffen/pkg/lens/` (Selector, loader, graph, etc.) IS shipped; only the `cmd/auraken-lens/` CLI binary wrapper is missing. The `sylveste-benl.1` bead has `artifact_closed` in labels but `status: open` — bead-state drift, filed for cleanup.

**Scope changes incorporated:**

1. **F10 added** — `cmd/auraken-lens` Go CLI binary wrapping `os/Skaffen/pkg/lens/.Selector`. Independent of F3 (which produces prebuilt binaries from this code). Reads stdin (user message + optional context), writes stdout (single-object soundpost response JSON), exit 0 on success / non-zero on error. ~150-300 LOC of Go.
2. **F1 owns canonical schema file** — `dist/v0.1/schemas/lens-response.schema.json` (JSON Schema for the single-object response). F2 (Python MCP) and F3 (Go binary) both reference it; F10 (CLI binary) outputs to it; F9 (smoke test) validates against it. Resolves the F2↔F3 circular schema dependency.
3. **F4 owns install.sh source-of-truth** — template at `apps/Auraken/dist/install.sh.in`. F7 build-dist.sh produces the released install.sh from the template (no string substitution beyond version). F8 packages the rendered file as a release asset.
4. **F8 two-phase release** — Phase 1: cut release with empty compatibility_evidence + draft status. Phase 2: F9 smoke run on the released bundle writes transcripts; F8 finalizes (or `auraken-distribution/v0.1.0` cuts a fast follow-up `v0.1.1` for the MANIFEST update). Decision in plan phase between in-place update and follow-up tag.
5. **F5 INSTALL.md adds "What Auraken does / why install"** — new AC item: 2-4 sentence value-prop section at the top of INSTALL.md written for a Hermes user who has never heard of Auraken. Not feature-list; user-facing outcome description.
6. **F8 release description + repo README link** — new AC items: release description (a) embeds a 2-paragraph value-prop, (b) links INSTALL.md, (c) links CHANGELOG. Sylveste root README adds a paragraph announcing the release with link.
7. **F6 voice-rubric.md adds explicit 0-10 scoring procedure** — new AC item: rubric defines what each score band means (0-3: not Auraken, 4-6: Auraken-leaning, 7-8: recognizably Auraken, 9-10: exemplary), how to score a transcript (count of mandatory-form violations, voice-fidelity calibration against signal-corpus reference), and who can apply the rubric (author-self + one external reader).
8. **F4 AC sharpens error semantics** — install.sh on missing binary: exit code 2, single human-readable line to stderr ("auraken-lens binary not found in /usr/local/bin; install aborted"), no partial filesystem state. F2 (Python MCP) on missing binary: returns `{empty: true, error: <msg>}` and the MCP server process stays alive.
9. **Dependencies section clarification** — PRD Dependencies now explicitly notes that sylveste-lfdy (cross-model voice generalization) and sylveste-whyj (Signal voice corpus) are **launch-prep for v0.2 demo**, not blockers on v0.1 ship. v0.1 ships with single-model (claude-opus-4-7) voice evidence; multi-model coverage and conversational-register calibration are v0.2 work.
10. **`sylveste-benl.1` bead admin** — close out the stale bead state. The library is shipped per `artifact_closed` label; status should be `closed`. Action: `bd close sylveste-benl.1`.

These amendments add one feature (F10), tighten 7 acceptance criteria across F1/F2/F4/F5/F6/F8/F9, and add explicit cross-feature ownership for the install.sh template path and the lens-response schema.

## Features

### F1: Bundle scaffolding + MANIFEST.yaml v1 schema
**What:** Create `apps/Auraken/integrations/hermes/dist/v0.1/` directory with a `MANIFEST.yaml` carrying the v1 schema — compatibility (hermes_agent version range, models, providers), capabilities (with depends_on, min_distribution_version, type constraint to {skill, mcp-server, binary, asset}), compatibility_evidence (per-model rows with tested boolean + transcript path + voice_score), and human-readable excluded_from_v01 list with bead refs as parentheticals.

**Acceptance criteria:**
- [ ] `dist/v0.1/MANIFEST.yaml` exists with `schema: auraken-distribution/v1` and `version: 0.1.0`
- [ ] Schema validates against an explicit JSON Schema or YAML schema file under `dist/v0.1/`
- [ ] Every claim in `compatibility:` has a corresponding row under `compatibility_evidence:`
- [ ] `capabilities[].type` is one of {skill, mcp-server, binary, asset}; capabilities support optional `depends_on` and `min_distribution_version` fields
- [ ] `excluded_from_v01` entries are prose strings with bead refs as parentheticals (e.g., `- "thinker-profile MCP — proprietary reasoning frame extraction, planned for v0.3 (internal: sylveste-i0px)"`)
- [ ] Loading the YAML with `python3 -c "import yaml; yaml.safe_load(open('dist/v0.1/MANIFEST.yaml'))"` exits 0

### F2: auraken-lens MCP — Go-binary shell-out + soundpost response shape
**What:** Rewrite `apps/Auraken/integrations/hermes/mcp-servers/auraken-lens/server.py` to shell out to the `auraken-lens` Go binary (no Python import of `auraken.lenses`). The MCP tool returns a single object `{lens, rationale, next_question}` for thinking-through turns, or `null` (or `{empty: true}`) for factual turns. Schema-encoded; not declarative.

**Acceptance criteria:**
- [ ] `server.py` does NOT import from `auraken.lenses` or any monorepo-relative path
- [ ] The `lens_select` MCP tool's output schema is `{lens: str | null, rationale: str | null, next_question: str | null, empty: bool}` — never a list of lenses
- [ ] When the upstream binary is missing or returns malformed output, the tool returns `{empty: true, error: <human-readable>}` and the MCP server stays alive (does not crash Hermes)
- [ ] The Go binary location is resolved via (a) `AURAKEN_LENS_BIN` env var, then (b) `$PATH` lookup for `auraken-lens`, then (c) clear error
- [ ] pytest in `mcp-servers/auraken-lens/` verifies: shape contract holds for thinking-through input; null/empty path for factual input; graceful error on missing binary

### F3: Prebuilt Go binaries for release assets
**What:** Build the `auraken-lens` Go binary from `benl.1` for four targets (linux-amd64, linux-arm64, darwin-amd64, darwin-arm64). Produce SHA256 checksums alongside each binary. Tag the Go module at `auraken-lens@v0.1.0`.

**Acceptance criteria:**
- [ ] Build script under `apps/Auraken/dist/build-binaries.sh` (or equivalent location) produces all four binaries deterministically
- [ ] Each binary passes a smoke test: `<binary> --version` returns `auraken-lens v0.1.0`
- [ ] Each binary passes a contract test: emits the single-object response shape for known thinking-through input
- [ ] SHA256 checksums are recorded alongside each binary
- [ ] Go module tag `auraken-lens@v0.1.0` exists in git history with matching commit SHA

### F4: install.sh — atomic, gated, transmissive
**What:** Idempotent bash installer that (1) detects Hermes install + profile, (2) verifies Hermes version against MANIFEST compatibility, (3) downloads the right-platform binary, (4) builds + registers MCP via staging-dir + atomic mv with `trap EXIT` rollback, (5) gates the move on `command -v auraken-lens` + smoke invocation, (6) prints a transmissive close: literal first-invocation string, one-line what-to-expect, log paths, uninstall hint. Supports `--uninstall` flag.

**Acceptance criteria:**
- [ ] Running install.sh twice in a row produces no errors and no duplicate config blocks
- [ ] Aborting (Ctrl-C) at any step leaves the system in either the original state OR a fully-installed state — never partially installed
- [ ] If the Hermes binary is not found, install.sh exits with a clear actionable error before touching any files
- [ ] If `command -v auraken-lens` fails after staging, install.sh reverts the staging dir and exits with the failure mode reported
- [ ] Step 6 output includes the literal string `/auraken what are you working through?` (or similar opening invocation) — not a list of capabilities
- [ ] `bash install.sh --uninstall` removes the skill, the MCP config block, and offers (with confirmation) to remove trajectories
- [ ] Tested in a clean Docker container against a vanilla Hermes install

### F5: INSTALL.md + canonical two-step install path
**What:** User-facing install documentation. Leads with the canonical two-step path (`curl -O ... && sha256sum -c ... && bash install.sh`) as the recommended approach. One-liner (`curl ... | bash`) is documented further down as a labeled convenience shortcut with an explicit warning. Includes prerequisites, what-to-expect-on-first-turn, and uninstall.

**Acceptance criteria:**
- [ ] `dist/v0.1/INSTALL.md` exists
- [ ] Two-step install path is the first install instruction users see
- [ ] One-liner appears only after the two-step, labeled "convenience shortcut" with a warning about piping unverified scripts to bash
- [ ] Prerequisites section names: working Hermes install with version range, profile to install into, recommended (not required) CLIProxyAPI
- [ ] "What to expect on first turn" section gives 2-3 sentences describing Auraken's opening behavior so users can distinguish correct behavior from defects
- [ ] Uninstall section documents `install.sh --uninstall` invocation + manual cleanup steps
- [ ] All commands in INSTALL.md are copy-pasteable (no placeholders for user to fill in beyond an obvious profile name)

### F6: SKILL.md + voice-rubric.md for the bundle
**What:** Copy/curate `skills/auraken/SKILL.md` from the recon spike into `dist/v0.1/skills/auraken/`. Author a new `voice-rubric.md` with two-section schema — `## Mandatory Form` (what holds across registers, models, contexts) and `## Permitted Variation` (what shifts) — each with 3-5 concrete examples and 1-2 anti-patterns.

**Acceptance criteria:**
- [ ] `dist/v0.1/skills/auraken/SKILL.md` exists with valid agentskills.io-compatible YAML frontmatter (`name`, `description`, `version: 0.1.0`, `metadata.hermes.tags`, `related_skills`)
- [ ] SKILL.md is identical to or curated-from the recon-spike SKILL.md; any divergences are documented in the bundle CHANGELOG
- [ ] `dist/v0.1/skills/auraken/voice-rubric.md` exists with the two-section schema
- [ ] Each section has 3-5 concrete examples and 1-2 anti-patterns
- [ ] SKILL.md references voice-rubric.md as a normative constraint document (not optional reading)

### F7: build-dist.sh — reproducible bundle assembly
**What:** Bash script under `apps/Auraken/dist/build-dist.sh` (or similar) that takes the dev tree (`apps/Auraken/integrations/hermes/{skills,mcp-servers}/`) and produces `dist/v0.1/` as a curated, deterministic release directory. Idempotent: running it twice produces byte-identical output.

**Acceptance criteria:**
- [ ] `bash apps/Auraken/dist/build-dist.sh v0.1` produces `apps/Auraken/integrations/hermes/dist/v0.1/`
- [ ] Running the script twice produces byte-identical output (deterministic file ordering, no timestamps in files)
- [ ] The script validates that all required source files exist before writing
- [ ] The script does NOT include monorepo-only files (CLAUDE.md, AGENTS.md, .bak files, __pycache__)
- [ ] The script's exit code is 0 only when the resulting bundle passes structural validation (MANIFEST.yaml present, SKILL.md present, install.sh present, all referenced binaries present)

### F8: GitHub release + signed checksums + CHANGELOG
**What:** Tag the release as `auraken-distribution/v0.1.0`. Release assets: bundle tarball (`auraken-distribution-v0.1.0.tar.gz`), `checksums.txt` (SHA256 of every file in the bundle), `checksums.txt.asc` (GPG-signed checksums), `install.sh` for the one-liner shortcut. CHANGELOG.md v0.1.0 entry documenting bundle contents + what's deferred.

**Acceptance criteria:**
- [ ] Git tag `auraken-distribution/v0.1.0` exists pointing at the release commit
- [ ] GitHub release page exists with title `Auraken Hermes Distribution v0.1.0`
- [ ] Release assets include: tarball, checksums.txt, checksums.txt.asc, install.sh
- [ ] checksums.txt.asc verifies against a known public key documented in INSTALL.md
- [ ] `dist/v0.1/CHANGELOG.md` v0.1.0 entry lists: bundle contents, what changed from recon-spike (mostly: structure, manifest, install script, server.py rewrite), what's deferred to v0.2/v0.3 with explicit non-goals
- [ ] Release description on GitHub links to INSTALL.md and CHANGELOG.md inside the bundle

### F9: E2E install smoke + compatibility_evidence
**What:** End-to-end test that runs install.sh in a clean environment (Docker container or VM), invokes the installed `/auraken` skill from Hermes, captures the response, and confirms (a) it doesn't violate behavioral contracts (no menu, opens with a question, ≤3 questions on thinking-through turn), (b) the lens MCP response shape is the single-object soundpost. Transcripts feed MANIFEST `compatibility_evidence` entries.

**Acceptance criteria:**
- [ ] `tests/e2e/install-smoke.sh` (or equivalent) runs in a clean Docker container against a vanilla Hermes install
- [ ] Test runs at least one scenario from `apps/Auraken/integrations/hermes/test-conversations.md` against the installed bundle
- [ ] Test records the full transcript to `tests/transcripts/v0.1-<model>.md`
- [ ] At minimum, claude-opus-4-7 transcript is captured and scored against voice-rubric.md (target: 8/10 recognizably Auraken)
- [ ] Captured transcripts are referenced in MANIFEST `compatibility_evidence.<model>.smoke_transcript`
- [ ] Untested models in MANIFEST are marked `tested: false` with rationale (e.g., "bucket capacity insufficient at release time")
- [ ] Test produces a pass/fail signal usable in CI

## Non-goals

- Thinker-profile MCP (sylveste-i0px — planned for v0.3)
- Voice corpus refresh / Signal-corpus ingest (sylveste-whyj — planned for v0.2)
- Cross-model voice rubric application (sylveste-lfdy — planned for v0.2)
- Public demo instance / Discord or Telegram bot (separate sub-bead of heh8 for v0.2)
- agentskills.io submission (waits until v0.2 has a demo)
- Trajectory-collection centralized backend (file-based JSONL is sufficient for v0.1)
- Landing page (auraken-web is separate)
- SOUL.md generalization beyond what the recon-spike SKILL.md already covers (current is already audience-neutral)
- Windows-native support (Hermes itself requires WSL2; v0.1 supports the same surface)
- WSL2 testing (Linux-amd64 only confirmed; WSL2 marked `tested: false` in MANIFEST)

## Dependencies

- Hermes Agent v2026.4.0+ installed (user-side; we don't vendor)
- benl.1 Go package built and tagged at `auraken-lens@v0.1.0` (internal — same Sylveste monorepo)
- CLIProxyAPI (user-side, recommended not required)
- agentskills.io standard (Hermes-declared compatibility; we conform)
- The reframed `sylveste-heh8` bead description
- Strategy memory `project_auraken_hermes_pivot.md` + reconciliation note

## Open Questions

(Most resolved by synthesis-driven amendments; remaining items for plan phase.)

1. **Where does build-dist.sh live in the monorepo?** Likely `apps/Auraken/dist/` parallel to the existing `apps/Auraken/integrations/`. Plan phase confirms.
2. **GPG signing identity for checksums.txt.asc** — use mistakeknot's existing GPG key, or generate a project-specific key for release signing? Plan phase decides.
3. **Smoke test isolation** — clean Docker container is canonical; whether to also run on a fresh VM is open. Container is sufficient for v0.1.
4. **Trajectory disclosure default** — opt-in (user must enable) vs documented-opt-out (default-on, disclosed). Plan phase decides; brainstorm Open Question #7.
5. **macOS testing** — defer to v0.2; v0.1 ships macOS untested, claimed in MANIFEST with honest `tested: false` annotation.
6. **CI integration timing** — should F8 and F9 run from GitHub Actions for v0.1, or is manual release acceptable? Lean manual for v0.1 (one-time release; CI value emerges at v0.2+).
