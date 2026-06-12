---
artifact_type: brainstorm
bead: sylveste-heh8
stage: discover
---

# Brainstorm — Auraken Hermes distribution v0.1

**Date:** 2026-05-25
**Bead:** sylveste-heh8 — Ship publishable Auraken Hermes distribution as Mythos launch artifact
**Complexity:** 3 (medium)

## What We're Building

A **publishable v0.1 of Auraken as a Hermes Agent distribution.** Auraken is shipped as a self-contained directory under `apps/Auraken/integrations/hermes/dist/v0.1/` that anyone with a working Hermes install can drop into their setup and end up with the Auraken personality + lens-selection MCP loaded. Distribution channel: a tagged GitHub release with an `install.sh` that copies the SKILL.md into the user's Hermes profile and registers the auraken-lens MCP. Eventual second channel: agentskills.io submission.

v0.1 is the *bundle as artifact*. Not a public demo instance, not a polished landing page, not the thinker-profile MCP — those are v0.2 and v0.3.

## Why This Approach

Three approaches considered (A minimal-now, B bundle+demo, C wait-for-profile). Chose **A** because:

- **Decouples bundle correctness from demo operations.** Approach B couples agentskills-conformance, install-script quality, and version-pinning with demo-VM provisioning, bot credentials, abuse defense, and PII risk. Independent failure modes shouldn't ride the same ship.
- **The artifact is testable in isolation.** You can install v0.1 on a fresh Hermes laptop and verify it works without standing up a demo. v0.2 then adds the demo with a stable artifact to deploy.
- **Iteration cost is lower.** v0.1 → v0.2 → v0.3 in three sprints over ~2 months fits the deferred Mythos launch window and lets each release validate against the previous.
- **The recon spike already did ~80% of the bundle-content work.** What v0.1 adds is structure (MANIFEST.yaml, install.sh, INSTALL.md, version pinning), not new content.
- **agentskills.io is the open standard.** Hermes README declares compatibility; the existing SKILL.md frontmatter already conforms. No bespoke distribution mechanism to invent.

## Synthesis-Driven Amendments (2026-05-25)

This brainstorm was reviewed by a 4-track flux-review (16 agents across adjacent / orthogonal / distant / esoteric semantic distances). Synthesis at `docs/research/flux-review/auraken-distribution-v01/2026-05-25-synthesis.md`. Three P0 findings and a "soundpost" P1 promote into the Key Decisions below before strategy. Twelve more findings carry forward into the plan as scope items rather than direction changes.

**P0-1 resolved → Python-vendoring decision committed.** `auraken-lens/server.py:40-47` currently does `_HERE.parents[3] / "src"` which only resolves inside the Sylveste monorepo. Every external install hits `ModuleNotFoundError`. Two options: (a) vendor the `auraken.lenses` Python module into the bundle; (b) shell out to the Go `auraken-lens` binary from `benl.1`. The MANIFEST already hints at (b) via `binary_required`. **Decision: (b)** — shell out to the Go binary. Aligns the MCP server's runtime with what MANIFEST declares; removes a Python-packaging surface (no need to vendor a sub-module from the monorepo); makes the bundle multi-platform via prebuilt Go binaries per OS/arch. server.py rewrite is in scope for v0.1.

**P0-2 resolved → install.sh atomicity + binary-verification gate.** Step 5 of install.sh writes the MCP YAML config block before any binary check. A partial failure or successful-config-write-with-broken-binary leaves Hermes loading a phantom MCP forever. **Decision:** all step-5 writes stage to a sidecar (`config.yaml.auraken-stage`); atomic `mv` at the end; the move is gated on `command -v auraken-lens` returning 0 AND a smoke invocation succeeding. Add `trap EXIT` cleanup for partial-state recovery (revert sidecar, restore prior config, report what was undone).

**P0-3 resolved → canonical two-step install path.** The brainstorm's curl-pipe-bash one-liner executes before any integrity check. The reliquary-translation lens flagged this directly ("vessel opened before bishop's seal inspected"); release-engineering convention requires the same. **Decision:** two-step install is the canonical path documented at the top of INSTALL.md (`curl -O ... && sha256sum -c checksums.txt && bash install.sh`). The one-liner is demoted to a labeled "convenience shortcut" further down with explicit warning. Release assets include `checksums.txt` + GPG-signed `checksums.txt.asc`. INSTALL.md documents how to verify before running.

**Soundpost decision (P1, highest-leverage) → `auraken-lens` single-object response shape.** The most architectural finding from the 4-track review. The auraken-lens MCP tool currently returns a list (`lenses: [...]`). The behavioral contract in SKILL.md depends on the model honoring "never offer a menu" + "one to three questions, count follows lens_select return." Both are declarative — they degrade under model substitution, register drift, prompt injection. **Decision:** the MCP tool returns a single object: `{lens, rationale, next_question}` for thinking-through turns; `null` or `{empty: true}` for factual turns. The schema is the constraint — there is no list for the model to render as a menu. This collapses three other findings (SKILL.md "never X" enforcement, voice-rubric.md being a constraint not a recipe, MANIFEST `binary_behavior_contract`) into a single architectural decision. v0.1 ships with this shape; the lens-binary's output format changes correspondingly (benl.1 binary shells return the same single-object shape).

**Voice-rubric.md structure decided.** All four tracks flagged voice-rubric.md as the most underspecified file in the bundle layout. **Decision:** voice-rubric.md uses a two-section schema — `## Mandatory Form` (what holds across registers, models, and contexts: opening-question discipline, no-menu posture, lens-paired-question count contract) and `## Permitted Variation` (what shifts by register, model family, or user-energy). Each section gives 3-5 concrete examples and 1-2 anti-patterns. Distinguishes the artifact's role from a "voice recipe" (drift-prone) to a "voice constraint" (testable).

**MANIFEST.yaml gains evidence fields.** Three tracks flagged that MANIFEST currently asserts compatibility without evidence. **Decision:** MANIFEST adds `compatibility_evidence:` with per-model rows (`{model: claude-opus-4-7, tested: true, smoke_transcript: tests/transcripts/v0.1-opus-4-7.md, voice_score: 8/10}`). Untested entries are marked `tested: false` with rationale. The matrix becomes a license certificate, not a shipping manifest.

**`excluded_from_v01` becomes human-readable.** Three tracks flagged that bead IDs (`sylveste-i0px`, `sylveste-whyj`) are opaque to external readers. **Decision:** the list uses prose descriptors (`- thinker-profile MCP — proprietary reasoning frame extraction, planned for v0.3`) with bead IDs as a parenthetical (`(internal: sylveste-i0px)`).

**Aoidos-formulaic-epic finding accepted → MANIFEST capabilities schema is extension-ready.** The current capabilities schema requires a migration to add v0.3 thinker-profile. **Decision:** capabilities entries support `depends_on:` (list of capability ids), `min_distribution_version:` (semver of the auraken-distribution itself), and `type:` is constrained to the set `{skill, mcp-server, binary, asset}`. Two comment lines define the type range; new types in future versions extend the set.

**install.sh step 6 (next-steps output) is a transmissive close.** All three esoteric agents converged on the same finding from different angles — the closing output is the bundle's most-squandered surface. **Decision:** step 6 prints (a) the literal first invocation to type (`/auraken` plus an opening probe sentence), (b) a one-line "what to expect on first turn" framing, (c) where logs and trajectories go, (d) how to uninstall. No capability enumeration. Drafted in INSTALL.md as the literal text before any code is written.

The remaining synthesis findings carry into the plan as scope items; they refine sub-decisions rather than altering the v0.1 frame.

## Key Decisions

### Bundle layout
```
apps/Auraken/integrations/hermes/dist/v0.1/
├── MANIFEST.yaml             # version, capability list, model matrix, Hermes compat range
├── INSTALL.md                # user-facing install instructions
├── install.sh                # installer (copies SKILL.md, registers MCP, prints next steps)
├── CHANGELOG.md              # bumps documented here from v0.2 onward
├── skills/
│   └── auraken/
│       ├── SKILL.md          # copied/symlinked from ../../skills/auraken/SKILL.md
│       └── voice-rubric.md   # extracted voice criteria for register_check
└── mcp-servers/
    └── auraken-lens/
        ├── README.md
        ├── pyproject.toml    # pinned: mcp>=X, lens-binary path declared
        ├── server.py
        └── trajectory.py
```
The existing source files at `apps/Auraken/integrations/hermes/{skills,mcp-servers}/` stay as the *development* tree; v0.1 is a curated copy + version stamps. Future versions live in sibling `v0.2/`, `v0.3/` dirs — no in-place mutation of v0.1 after release.

### MANIFEST.yaml schema (v1)
```yaml
schema: auraken-distribution/v1
version: 0.1.0
released: 2026-05-XX

compatibility:
  hermes_agent: ">=2026.4.0"        # minimum tested; bumps as testing widens
  models:
    claude:
      - claude-opus-4-7              # primary validation target
      - claude-haiku-4-5-20251001
    openai:
      - gpt-5.5                      # observed register drift documented
      - gpt-5.4
  providers:
    - openai-compatible              # via CLIProxyAPI or direct
    - anthropic-native

capabilities:
  - id: auraken-personality
    type: skill
    path: skills/auraken/
  - id: auraken-lens
    type: mcp-server
    path: mcp-servers/auraken-lens/
    binary_required: github.com/mistakeknot/Sylveste/apps/Auraken/dist/auraken-lens@v0.1.0

excluded_from_v01:                   # explicit non-goals; pre-emptive scope guard
  - thinker-profile-mcp              # → v0.3 (sylveste-i0px)
  - voice-corpus-refresh             # → v0.2 (sylveste-whyj)
  - cross-model-voice-rubric         # → v0.2 (sylveste-lfdy)
  - public-demo-instance             # → v0.2 (new sub-bead under heh8)
```
The `excluded_from_v01` list is doctrine — it answers "is this in v0.1?" without re-litigating each time.

### install.sh contract
Idempotent, prints what it's about to do, asks for confirmation, then:
1. Detects Hermes install location (`hermes --version`, fallback `~/hermes-*/hermes-agent` walk)
2. Asks which profile to install into (lists profiles in `~/.hermes-*/profiles/`)
3. Validates the Hermes version against MANIFEST.yaml `compatibility.hermes_agent`. Refuses if below; warns if above tested range.
4. Copies `skills/auraken/` into the chosen profile's `skills/`
5. Builds + registers the `auraken-lens` MCP server (reads `pyproject.toml`, installs into Hermes's MCP-server venv or system, writes a `mcp_servers:` config snippet)
6. Prints next steps: how to invoke `/auraken`, where logs go, how to uninstall

### Install path assumption
v0.1 assumes the user has Hermes already installed via the upstream `install.sh`. We do NOT vendor Hermes. We do NOT compete with `hermes-agent.nousresearch.com`. The Auraken installer is an *additive overlay* on a working Hermes install.

### Distribution mechanism
- Primary: GitHub release tagged `auraken-distribution/v0.1.0` against the Sylveste repo. Release assets: tarball of `dist/v0.1/`, signed checksums, install.sh.
- One-liner install: `curl -fsSL https://github.com/mistakeknot/Sylveste/releases/download/auraken-distribution/v0.1.0/install.sh | bash` (with the standard "review before piping to bash" caveat in INSTALL.md).
- Secondary (deferred): agentskills.io submission after v0.2 demo is up. Don't submit a tarball whose demo doesn't exist yet.

### auraken-lens binary distribution
The MCP server depends on the lens-selection binary from `benl.1` (Go package, shipped). v0.1 either:
- (a) Vendors a pre-built binary per platform in the release assets (linux-amd64, linux-arm64, darwin-arm64, darwin-amd64), OR
- (b) Documents `go install github.com/mistakeknot/Sylveste/...` as a prerequisite.

Decision deferred to plan phase. (a) is friendlier; (b) is smaller. Likely answer: (a) for v0.1 with (b) as fallback in INSTALL.md.

### Versioning
SemVer. v0.x = pre-1.0 — breaking changes allowed across minors. v0.1 → v0.2 may break installs (intentional). v0.2 prints a clear migration note in install.sh.

### CHANGELOG seed
v0.1.0 changelog entry written at release time. Lists what's in the bundle, what changed from the recon-spike (mostly: structure + manifest + install script), what's deferred to v0.2/v0.3.

## Open Questions

(Items moved to Resolved below following synthesis-driven amendments.)

1. ~~Lens binary distribution mechanism (a vs b above).~~ **Resolved:** shell out to Go binary; vendor prebuilt per-platform in release assets (linux-amd64, linux-arm64, darwin-arm64, darwin-amd64). See P0-1 amendment.
2. **Where does the bundle's CHANGELOG live: in the bundle, or at the dist/ level?** Probably bundle (so users can `cat dist/v0.1/CHANGELOG.md` post-install). v0.2 references v0.1 for migration notes. Defer to plan.
3. ~~Is `install.sh` POSIX-sh-only or can we use bash?~~ **Resolved:** bash. Matches Hermes installer convention.
4. **WSL2 / macOS / Linux support matrix for v0.1.** Linux confirmed primary; macOS-arm64 ships untested with `compatibility_evidence: {tested: false}` annotation. WSL2 left out of v0.1 — surface in MANIFEST. Plan phase confirms.
5. **Does install.sh require write access to the Hermes install dir, or only the profile dir?** Likely profile-only is sufficient since skills and mcp_servers config both live in the profile. Verify in plan.
6. **NEW (synthesis):** Trajectory capture for v0.1 — is `~/.hermes/auraken/trajectories/` the right path for an external user's Hermes install, or does that need to discover the user's actual hermes home? Recon spike wrote to `~/.hermes/` directly; an installed v0.1 must respect the user's Hermes profile location.
7. **NEW (synthesis):** Privacy / trajectory-recording disclosure — install.sh should print what data the lens MCP records and where; users must consent. Plan phase to decide opt-in default vs documented-opt-out default.
8. **NEW (synthesis):** Uninstall script — `install.sh --uninstall` flag or a separate `uninstall.sh`. Synthesis suggests treating uninstall as a first-class capability for v0.1 (mature distributions ship uninstall paths).

## Out of Scope (v0.1)

Listed explicitly so plan phase doesn't drift:
- Thinker-profile MCP (i0px) → v0.3
- Voice corpus refresh (whyj) → v0.2
- Cross-model voice rubric (lfdy) → v0.2
- Public-facing demo instance → v0.2
- agentskills.io submission → v0.2 (after demo)
- Landing page (auraken-web stays separate)
- SOUL.md generalization for non-mistakeknot users (current recon SKILL.md is already audience-neutral — no rewrite needed for v0.1)
- Trajectory-collection backend (file-based JSONL is good enough for v0.1; centralized backend is post-launch)

## Provenance

- Reframed bead description (sylveste-heh8) drives this brainstorm.
- Recon spike artifacts inventoried via direct filesystem inspection.
- Hermes-internal conventions (SKILL.md frontmatter, optional-skills layout, install.sh pattern) reviewed in `apps/Auraken/research/hermes-agent/`.
- Pivot memory `project_auraken_hermes_pivot.md` + reconciliation note (2026-05-25) define the strategic frame.
- Amtiskaw-vs-Auraken distinction (`project_amtiskaw_personal_agent.md`) prevents conflation.
