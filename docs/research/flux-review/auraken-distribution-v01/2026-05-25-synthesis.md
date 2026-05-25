---
artifact_type: review-synthesis
method: flux-review
target: "docs/brainstorms/2026-05-25-auraken-distribution-v01-brainstorm.md"
target_description: "Brainstorm — Auraken Hermes distribution v0.1 (publishable bundle, GitHub release, eventually agentskills.io)"
tracks: 4
track_a_agents: [fd-distribution-installer-safety, fd-mcp-server-packaging, fd-skill-bundle-conformance, fd-versioning-compatibility, fd-onboarding-ux]
track_b_agents: [fd-instrument-kit-packaging, fd-typeface-retail-release, fd-field-guide-scope-discipline, fd-studio-preset-pack-onboarding]
track_c_agents: [fd-tea-ceremony-densho, fd-reliquary-translation, fd-perfumery-grasse-composition, fd-aoidos-formulaic-epic]
track_d_agents: [fd-eleusinian-mystai-token, fd-luthier-soundpost-transmission, fd-mycorrhizal-inoculum]
date: 2026-05-25
---

# Flux Review Synthesis — Auraken Distribution v0.1

## Caveats

- **OUTPUT_DIR collision between Track A and Tracks B/C.** Tracks A, B, and C all wrote to `flux-drive/...c13c3eac/`. The `findings.json` in that directory only enumerates Track B's four agents and lists Track A and Track C agents as "agents_foreign_skipped" — those are dispatch-level skips by the second flux-drive run, not signals that the agents failed. All twelve markdown reports for A/B/C are present and were synthesized below. Track D wrote to a clean `c909ce00/` directory with its own findings.json.
- **Pre-existing summary.md is Track C-only.** The `c13c3eac/summary.md` describes only Track C agents (reliquary, tea-ceremony, perfumery, aoidos) with verdict "risky." Its P0:1 P1:5 totals reflect only that track. Disregard for the full picture; this synthesis re-counts across all four tracks.
- **Track D filed four beads (sylveste-zjz3, sylveste-cemk, sylveste-pyl9, sylveste-u9cp).** Noted but not refiled. The convergence list below shows where these align with Tracks A/B/C findings.

## Critical Findings (P0/P1)

After dedup, twelve issues land at P0 or P1. Three are P0; the rest are P1.

### P0-1. install.sh's MCP-registration is non-atomic and writes config before binary is verified
- **Surfaced by:** fd-distribution-installer-safety F1 (Track A), fd-instrument-kit-packaging IKP-1 (Track B), partial convergence with fd-luthier-soundpost-transmission LU-01 (Track D, "deposit not voicing").
- **Tracks:** A + B + D (3 of 4).
- **Finding:** Step 5 of `install.sh` performs three sequential filesystem operations (venv build, `pip install -e .`, YAML config append) with no atomicity, no binary-existence gate before the config write, and no rollback. A partial failure or Ctrl-C between (a)+(b) and (c) leaves a working venv with no registration; a successful (c) with a broken binary leaves Hermes loading a phantom MCP forever. The recon README documents the manual procedure as direct edit of `~/.hermes/config.yaml` — install.sh inherits the lack of atomicity by default.
- **Fix:** Stage all step-5 writes to a sidecar (`config.yaml.auraken-stage`), `mv` atomically at the end, and gate the move on `command -v auraken-lens` returning 0. Add `trap` cleanup for partial-state recovery.

### P0-2. `AURAKEN_SRC` path resolution is monorepo-relative and breaks on every fresh install
- **Surfaced by:** fd-mcp-server-packaging F1 (Track A).
- **Tracks:** A only — but this is a verified, code-level finding traceable to `server.py:40-47` (`_HERE.parents[3] / "src"`), so single-track surfacing is sufficient.
- **Finding:** server.py computes `AURAKEN_SRC = _HERE.parents[3] / "src"` and then `from auraken.lenses import select_lenses`. Inside the monorepo this resolves; on a user's machine `_HERE.parents[3]` is `~/` or `/root/` and the import always fails. The bundle layout does not vendor `auraken.lenses`, and the MANIFEST's `binary_required` Go-binary clue contradicts the Python import path the running server still uses today.
- **Fix:** Decide F2 (vendor Python `auraken.lenses` into the bundle, or shell out to the Go binary). The brainstorm hints at the Go-binary path via `binary_required`, but server.py contradicts it. Resolve before any other release work — this is a 100% install failure.

### P0-3. curl-pipe-bash one-liner executes before any integrity check
- **Surfaced by:** fd-reliquary-translation REL-1 (Track C). Adjacent overlap with fd-typeface-retail-release TRR-1 (URL stability, Track B) and fd-distribution-installer-safety (no `--dry-run` in v0.1).
- **Tracks:** C primary, with B touching the URL-stability sub-issue.
- **Finding:** The published install path is `curl -fsSL .../install.sh | bash`. The release ships signed checksums, but the user never sees or runs `sha256sum -c` because the documented happy path doesn't pause. A supply-chain or CDN compromise executes arbitrary code before any inspection step.
- **Fix:** Make the canonical install a two-step (download → verify SHA256SUMS → bash), with the one-liner demoted to a "convenience, skips verification" footnote. Add a "Verify the download" section to INSTALL.md with the literal `sha256sum -c` command (also surfaced by fd-typeface-retail-release TRR-6).

### P1 issues after dedup

| # | Title | Tracks | Agents |
|---|-------|--------|--------|
| P1-A | No partial-install rollback (`trap EXIT`) | A + B | fd-distribution-installer-safety F1 (adjacent), fd-instrument-kit-packaging IKP-2 |
| P1-B | No post-install smoke test / "take check" | A + B + D | fd-distribution-installer-safety (implied via F1), fd-instrument-kit-packaging IKP-3, fd-mycorrhizal-inoculum MY-01 |
| P1-C | Binary distribution mechanism deferred (option a vs b) — installer hits undefined state; `go install` points to HEAD | A + B + C | fd-mcp-server-packaging F2, fd-instrument-kit-packaging IKP-4, fd-typeface-retail-release TRR-3, fd-reliquary-translation REL-4 |
| P1-D | No Hermes prerequisite preflight (assumption undeclared) | A + B | fd-distribution-installer-safety F4, fd-field-guide-scope-discipline FGSD-2, fd-instrument-kit-packaging (implied) |
| P1-E | SKILL.md frontmatter missing agentskills.io-required fields (version, license, author, homepage, compatibility) | A | fd-skill-bundle-conformance F1 |
| P1-F | `lens_select` invocation timing not enforceable; "never X" voice rules not enforced; voice-rubric is recipe not constraint | A + C + D | fd-skill-bundle-conformance F2/F3, fd-perfumery-grasse-composition PGC-3 (signature vs accord), fd-luthier-soundpost-transmission LU-02/LU-04 |
| P1-G | MANIFEST has no provenance/authentica (no `manifest_sha256`, no `canonical_source`); no installation receipt post-install | C | fd-tea-ceremony-densho TCD-1/TCD-2, fd-reliquary-translation REL-2 |
| P1-H | Hermes-version lower bound `>=2026.4.0` has no cited evidence; identifier convention inconsistent (short vs dated); register-drift encoded as YAML comment rather than data | A | fd-versioning-compatibility F1/F2/F3 |
| P1-I | First `/auraken` invocation may leak Hermes scaffolding (contradicts SKILL.md "no preamble") | A | fd-onboarding-ux F1 |
| P1-J | INSTALL.md ordering undefined — one-liner above prerequisites; macOS-untested caveat placement | A + B | fd-onboarding-ux F2/F3, fd-field-guide-scope-discipline FGSD-2 |
| P1-K | install.sh next-steps prints components, not invocation + first command + voice + take-check ("no top-note", "no deikteria") | B + C + D | fd-studio-preset-pack-onboarding SPPO-1/SPPO-2, fd-perfumery-grasse-composition PGC-1/PGC-2, fd-eleusinian-mystai-token EL-01, fd-mycorrhizal-inoculum MY-01 |
| P1-L | `excluded_from_v01` uses internal bead IDs (opaque to outsiders); `auraken-distribution/v1` schema URL unresolvable; `excluded_from_v01` not part of any published schema | A + B | fd-versioning-compatibility F6/F8, fd-field-guide-scope-discipline FGSD-1 |

## Cross-Track Convergence

Findings independently surfaced by 2+ tracks, ranked by convergence score.

### 4-track convergence

**None.** No single finding was named by all four tracks. The closest is the bundle of "install.sh step 6 is functionally complete but transmissively/onboardingly empty" — see the 3-track entries below.

### 3-track convergence

**1. install.sh step 6 next-steps output is hollow at the threshold (Tracks B + C + D)**
- Track B (fd-studio-preset-pack-onboarding SPPO-1): "describes components, not invocation — no copy-pasteable first command."
- Track C (fd-perfumery-grasse-composition PGC-1): "top-note absent — utilitarian next-steps with no Auraken voice."
- Track D (fd-eleusinian-mystai-token EL-01): "man-page enumeration, not a deikteria — the threshold is unmarked."
- Track D also (fd-mycorrhizal-inoculum MY-01): "colonization assumed, never observed — no take-check after deposit."
- **Framings differ by depth:** Track B wants concrete UX (copy-pasteable command); Track C wants composed voice (a top-note in the installer's last words); Track D wants an initiatory gesture and a 48-hour mycelial check. The same install.sh step 6 sits at the structural location of all four critiques.
- **Convergence: 3 of 4 tracks** (or arguably 4 if you count fd-onboarding-ux F4 in Track A asking for a literal template — though A frames it as DX vagueness, not threshold-emptiness).

**2. install.sh has no Hermes prerequisite + profile-substrate preflight (Tracks A + B + D)**
- Track A (fd-distribution-installer-safety F4): "Profile-discovery fallback is undefined when zero profiles exist or when Hermes uses non-default config dir."
- Track B (fd-field-guide-scope-discipline FGSD-2): "No Hermes prerequisite check — assumption undeclared and unverified." Also fd-instrument-kit-packaging IKP-5 (platform-matrix undeclared).
- Track D (fd-mycorrhizal-inoculum MY-02): "No substrate-readiness check — install.sh detects Hermes version but not profile composition."
- Track D (fd-luthier-soundpost-transmission LU-01): "install.sh constitutes placement, not voicing — instrument is deposited, not adjusted to the room."
- **Framings differ:** Track A wants `HERMES_CONFIG_DIR` honored and zero-profile case handled; Track B wants a preflight that fails fast with an upstream-installer link; Track D wants profile contents inspected for competing personality SKILL.md files and conflict warnings. All three converge on "step 1 of install.sh is missing meaningful detection work."
- **Convergence: 3 of 4 tracks.**

**3. Bundle ships voice without provenance / authentication / token-of-receipt (Tracks A + C + D)**
- Track A (fd-skill-bundle-conformance F1): SKILL.md frontmatter missing version/license/author/homepage/compatibility (agentskills.io-required).
- Track C (fd-tea-ceremony-densho TCD-1/TCD-2): No installation receipt; MANIFEST is a shipping manifest, not a license certificate. fd-reliquary-translation REL-2: MANIFEST contains no authentica (no `manifest_sha256`).
- Track D (fd-eleusinian-mystai-token EL-03): No symbolon — voice-rubric.md is machine-legible criteria, not an object the initiate carries.
- **Framings:** A is ecosystem-conformance (registry-required fields); C is institutional-custody (sealed receipt, canonical-source claim); D is initiatory-token (symbol the user carries forward). All three identify "the bundle ships the substance but no witness-marker that the user / auditor / future-self can hold." Fixes stack cleanly: extend frontmatter (A) + add `canonical_source` and `manifest_sha256` to MANIFEST (C) + add human-facing header to voice-rubric.md describing what the user will notice in themselves (D).
- **Convergence: 3 of 4 tracks.**

### 2-track convergence

**4. Binary distribution mechanism deferred — installer hits an undefined slot (Tracks A + B + C)**
- fd-mcp-server-packaging F2 (Track A): Python `auraken.lenses` import vs. Go binary path is ambiguous.
- fd-instrument-kit-packaging IKP-4 (Track B): no installer placeholder.
- fd-typeface-retail-release TRR-3 (Track B): `go install` points to HEAD — tarball not self-contained.
- fd-reliquary-translation REL-4 (Track C): chain-of-custody analysis prefers option (a) decisively.
- fd-aoidos-formulaic-epic AFE-3 (Track C): the binary acquisition step is an undefined formulaic slot.
- **Convergence: 3 of 4 tracks.** Resolution: pick option (a) — vendor binaries in the release tarball — and document option (b) only as a fallback pinned to a version tag.

**5. MANIFEST schema is structurally premature — extension grammar, qualifier fields, identity-role missing (Tracks A + B + C)**
- fd-versioning-compatibility F2/F3/F5/F6 (Track A): identifier convention, tested-vs-inferred qualifier, register-drift as comment-not-data.
- fd-typeface-retail-release TRR-2/TRR-5 (Track B): `tested:` vs `expected:` distinction; `stability:` field absent.
- fd-aoidos-formulaic-epic AFE-1 (Track C): capability schema has no extension grammar for v0.3's thinker-profile.
- fd-perfumery-grasse-composition PGC-3 (Track C): `identity_role` field (signature vs heart vs accord) absent.
- fd-luthier-soundpost-transmission LU-05 (Track D): `binary_behavior_contract` separate from API version.
- **Convergence: 4 of 4 tracks if Track D's LU-05 counts here. Effective 3-4 of 4.** The MANIFEST schema needs four additions before being frozen: `quality`/`status` per model, `stability: pre-release`, `identity_role:` per capability, extension grammar comment for future capability types.

**6. voice-rubric.md is underspecified — schema role, human-vs-machine purpose, structural vs example-based criteria (Tracks A + B + C + D)**
- fd-skill-bundle-conformance F4 (Track A): SKILL.md references rubric but runtime doesn't load it — coherence risk.
- fd-studio-preset-pack-onboarding SPPO-3 (Track B): no self-description for practitioners.
- fd-tea-ceremony-densho TCD-3 (Track C): no katachi/permitted-variation schema.
- fd-luthier-soundpost-transmission LU-04 (Track D): recipe transmission decays; needs structural prohibitions.
- fd-eleusinian-mystai-token EL-03 (Track D): needs human-readable symbolon header.
- **Convergence: 4 of 4 tracks.** Highest cross-track convergence in the entire review. The fix is coherent: voice-rubric.md becomes a structured artifact with three sections — (1) human-readable symbolon header (what the user will notice in themselves), (2) mandatory form / katachi (structural prohibitions, machine-checkable), (3) permitted variation (style range). One file, three voices, single source for register_check.

**7. SKILL.md "never X" assertions and `lens_select` ordering are not runtime-enforced (Tracks A + D)**
- fd-skill-bundle-conformance F2/F3 (Track A): tool-call ordering not enforceable; "never name the lens" is a voice rule, not a constraint.
- fd-luthier-soundpost-transmission LU-02/LU-03 (Track D): SKILL.md declarative not structural; auraken-lens MCP API shape is unconstrained (returning a list of lenses enables menu-offering even if SKILL.md forbids it).
- **Convergence: 2 of 4 tracks.** Track D's framing is the higher-leverage one: the structural fix is to make `lens_select` return `{lens, rationale, next_question}` — a single object — so the geometry of the tool schema prevents menu-offering regardless of model posture. Wire register_check as a runtime hook in the MCP server rather than docs.

**8. CHANGELOG framing / proem / "what to expect" — INSTALL.md lacks user-facing identity entry (Tracks B + C + D)**
- fd-studio-preset-pack-onboarding SPPO-2/SPPO-5 (Track B): no "What to expect" section; CHANGELOG framed as dev artifact not net-new practitioner intro.
- fd-aoidos-formulaic-epic AFE-4 (Track C): proem absent — INSTALL.md opens in medias res.
- fd-perfumery-grasse-composition PGC-2 (Track C): packaging surface composed as scaffold, not identity.
- fd-eleusinian-mystai-token EL-02/EL-04 (Track D): MANIFEST capabilities list preempts gripping impression; "What We're Building" lacks transmissive success criterion.
- **Convergence: 3 of 4 tracks.** INSTALL.md needs a two-paragraph opening (lineage statement + what changes in a Hermes session after install) before any prerequisites or commands.

**9. One-liner URL stability + tag format (Tracks A + B)**
- fd-onboarding-ux F6 (Track A): URL fragile to repo rename.
- fd-typeface-retail-release TRR-1/TRR-4 (Track B): repo-routed URL fragile; forward-slash tag format ambiguous.
- **Convergence: 2 of 4 tracks.** Fix: vanity redirector (`get.auraken.sh` via the existing Cloudflare worker) or accept fragility and document it; consider `auraken-v0.1.0` flat tag scheme.

**10. Single-source `version` across files (Tracks A internal convergence)**
- fd-mcp-server-packaging F7: pyproject.toml `0.0.1` vs MANIFEST `0.1.0`.
- fd-skill-bundle-conformance F1 (implied via missing `version` in frontmatter).
- fd-versioning-compatibility F2: identifier conventions.
- **Within-track-A convergence**, not cross-track, but worth surfacing: build-time substitution from MANIFEST.yaml prevents the entire drift class. Surface as `scripts/build-dist.sh`.

## Domain-Expert Insights (Track A)

The five Track A agents surfaced findings that required Hermes / MCP / agentskills.io / SemVer / packaging expertise.

### Packaging mechanics

- **fd-mcp-server-packaging F1 / F2 / F5** is the most consequential single Track A discovery: server.py is monorepo-relative today and the bundle layout does not vendor the Python `auraken.lenses` package the server imports. Three sub-findings stack: (a) `AURAKEN_SRC` path resolution breaks, (b) the Python-vs-Go binary contradiction in the brainstorm itself, (c) `trajectory.py` sibling-import contract requires `[tool.setuptools] py-modules = ["server", "trajectory"]` in pyproject.toml or the entry-point `auraken-lens-mcp` fails on import.
- **fd-mcp-server-packaging F3 / F4**: http-mode runtime imports (`uvicorn`, `starlette`) are missing from `dependencies`; `mcp>=1.0.0` has no upper bound and will be broken silently by any 2.x release.
- **fd-mcp-server-packaging F6**: dev tree contains `server.py.bak-pre-auth-*` and `__pycache__/` — a naive `cp -r` ships them. Curation needs explicit file list, not `cp -r`.

### Installer atomicity

- **fd-distribution-installer-safety F1 / F2 / F3** model install.sh as a state machine where the brainstorm describes only the success path. F1 (atomicity), F2 (idempotency mechanism unspecified — `cp -r` vs marker-file vs checksum-diff), and F3 (version-gate ordering — does any profile-mutating syscall happen before step 3 passes?) need a state-transition table as a plan-phase deliverable. Six rows × {touches?, atomic?, rollback?, exit-template} forces every gap into the open.
- **fd-distribution-installer-safety F4**: `HERMES_CONFIG_DIR` env override is unhandled; default `~/.hermes/` profile walk is fragile.

### Skill conformance

- **fd-skill-bundle-conformance F1**: SKILL.md frontmatter has only `name` and `description`. Every existing skill registry needs at minimum `version`, `author`, `license`, `homepage`, `compatibility`. Doing this in v0.1 is cheap; retrofitting for the v0.2 agentskills.io submission is expensive.
- **fd-skill-bundle-conformance F2 / F3**: SKILL.md's "Use lens_select at the start of each substantive turn" and the "never X" voice rules are declarative and not runtime-enforced. On model substitution (Haiku, gpt-5.5), behavior drifts. The proposed fix is `register_check` as an actual MCP runtime hook, not a documented aspiration.
- **fd-skill-bundle-conformance F6**: OODARC scaffolding in SKILL.md is "invisible to the user" yet ships in a human-readable file. Move to `INTERNAL.md` so users `cat`ing the installed skill see only what they can use.

### Versioning precision

- **fd-versioning-compatibility F1**: `hermes_agent: ">=2026.4.0"` has no evidence — neither a specific config-format change nor a feature anchor.
- **fd-versioning-compatibility F2 / F5**: Claude opus uses short form, haiku uses dated form, gpt uses short form — inconsistent and provider-aliasing-prone. Pick dated everywhere for reproducibility; surface short forms as compatible-aliases.
- **fd-versioning-compatibility F3**: register drift is encoded as a YAML comment. agentskills.io scrapers won't render comments. Encode as data (`quality: degraded`, `notes: ...`).
- **fd-versioning-compatibility F4**: `go install ...@v0.1.0` was not verified against a clean Go cache — may 404.

### Onboarding UX

- **fd-onboarding-ux F1**: First `/auraken` invocation may leak Hermes skill-load scaffolding ("Skill auraken loaded. Available tools: lens_select") before the model's first token. SKILL.md's "no preamble" contract applies only to model output, not Hermes runtime. Needs a fresh-install transcript capture and either a config flag to suppress or an INSTALL.md known-issues note.
- **fd-onboarding-ux F5**: No uninstall mechanism is specified. Install.sh's "Uninstall: see docs" without a tested uninstall.sh becomes weekly "I broke Hermes" support load.
- **fd-onboarding-ux F8**: Trajectory logging is enabled by default to `~/.hermes/auraken/trajectories/` and not surfaced in install.sh next-steps. Privacy-surprise risk — Auraken's pitch is "thinking partner," not "thinking surveillance."

## Parallel-Discipline Insights (Track B)

Four orthogonal-domain agents mapped operational patterns from their professional disciplines.

### fd-instrument-kit-packaging — boutique instrument kits

- **Practice:** every kit ships with a "soundcheck card" that tells the assembler what a correctly-assembled instrument should sound like on first play. Maps to: install.sh smoke test (IKP-3) and the brainstorm's missing post-install verification gate. Without a smoke test, 80% of assembly failures are invisible until the practitioner opens a real Hermes session.
- **Practice:** kit makers ship binaries (pre-cut parts) rather than source (raw lumber + measurements). Maps to: prefer option (a) vendored binary over option (b) `go install` for the lens binary (IKP-4).

### fd-typeface-retail-release — independent type designers

- **Practice:** font releases distinguish "tested in" from "expected to work in" applications because customers who pin a version expect the validated behavior. Maps to: `tested:` / `expected:` distinction in MANIFEST model matrix (TRR-2) — the brainstorm's existing register-drift comment confirms the distinction is real.
- **Practice:** type retailers use direct CDN URLs and never repo-routed paths because foundry renames break old downloads. Maps to: one-liner URL stability (TRR-1) — verify install.sh URL resolves to `objects.githubusercontent.com/...`, or front it with a vanity redirector.
- **Practice:** "Verify the download" is a standard section in every commercial font INSTALL.md. Maps to: TRR-6 — the brainstorm mentions signed checksums in release assets but never tells users how to verify them.

### fd-field-guide-scope-discipline — field naturalist publishing

- **Practice:** field guide editions name what's not yet covered using practitioner-readable taxonomies, never internal SKU codes. Maps to: `excluded_from_v01` uses bead IDs (FGSD-1) — replace with "thinker-profile MCP — adds memory of past sessions, planned for v0.3" not "thinker-profile-mcp → sylveste-i0px".
- **Practice:** every field guide has a "Required equipment" section as the first thing the reader sees. Maps to: Hermes prerequisite preflight (FGSD-2) — install.sh assumes Hermes presence without explicit check; INSTALL.md must have prerequisites before the one-liner.
- **Practice:** field guides explicitly state what they are NOT a guide to (the additive-overlay principle) — "this guide covers mushrooms of the Pacific Northwest; for British Columbia coastal species see X." Maps to: FGSD-3 — additive-overlay framing belongs in INSTALL.md, not just in the brainstorm.

### fd-studio-preset-pack-onboarding — photography preset packs

- **Practice:** every preset pack ships a "Before / After" sample image showing what the user should see on first apply. Maps to: SPPO-2 — INSTALL.md needs a "What to expect" section so practitioners can recognize correct behavior on first contact (ask-first style, no menus, lens-selection without method descriptions).
- **Practice:** "Next steps" outputs in pro photo software always include the literal first command, never a description of the invocation. Maps to: SPPO-1 — install.sh next-steps should print "$ hermes\n> /auraken hello" not "invoke /auraken to begin."
- **Practice:** preset packs include a self-describing header in every secondary file because users will open them in any order. Maps to: SPPO-3 — voice-rubric.md needs a self-description so practitioners don't dismiss it as an internal dev artifact.

## Structural Insights (Track C)

Four distant-domain agents found structural isomorphisms.

### fd-tea-ceremony-densho — iemoto lineage transmission

- **Isomorphism:** densho scrolls = installation receipt; iemoto certification = `canonical_source` claim in the MANIFEST. Maps to: TCD-1 / TCD-2 — install.sh should write a sealed `auraken-install-receipt.yaml` (version, source_tag, sha256 of MANIFEST, install timestamp, profile) into the installed skills/auraken/ dir. The MANIFEST itself needs a `canonical_source:` field pointing at the canonical release URL. Together these establish that a particular install is a recognized lineage transmission, not a tampered fork.
- **Isomorphism:** katachi (inviolable form) vs allowed variation. Maps to: TCD-3 — voice-rubric.md needs two explicit sections distinguishing structural prohibitions from stylistic adaptation range. Concrete improvement.
- **Isomorphism:** lineage rename vs evolution-within-lineage. Maps to: TCD-4 — SemVer pre-1.0 policy needs a "lineage doctrine" paragraph naming which changes (SKILL.md identity, lens-MCP behavioral contract) require a lineage flag and which (compatibility updates, capability additions) are non-lineage. Open question that the brainstorm needs to answer before v0.2 ships.

### fd-reliquary-translation — medieval reliquary craft

- **Isomorphism:** authentica (sealed document inside the vessel) = `manifest_sha256` + signature. Maps to: REL-2 — add `manifest_sha256:` to the MANIFEST schema now, before it's frozen. Concrete improvement.
- **Isomorphism:** translatio ritual (the rite by which a relic moves from one shrine to another) requires custody during transport. Maps to: REL-1 — curl-pipe-bash is custody-broken; canonical install must verify the seal before opening the vessel.
- **Isomorphism:** retirement ritual when a relic is superseded. Maps to: REL-5 — open question for v0.2: how does a v0.1 install learn it has been superseded? `superseded_by:` field in MANIFEST.

### fd-perfumery-grasse-composition — French perfumery

- **Isomorphism:** top/heart/base notes vs the first-60-seconds composition of any encounter. Maps to: PGC-1 / PGC-2 — install.sh's next-steps output is the top-note; treating it as documentation infrastructure squanders the highest-leverage identity moment. Writing task, not engineering task. Concrete improvement: draft install.sh's literal terminal output in the brainstorm, in Auraken voice.
- **Isomorphism:** signature accord vs substitutable heart material. Maps to: PGC-3 — capabilities need an `identity_role:` field. `auraken-personality: signature` (removal = identity loss), `auraken-lens: heart` (changes require lineage note, not rename).
- **Isomorphism:** stranger's-skin test. Maps to: PGC-4 — open question that ties to onboarding's macOS-untested issue. Concrete improvement: troubleshooting section in INSTALL.md.

### fd-aoidos-formulaic-epic — oral epic transmission

- **Isomorphism:** formulaic type-scenes (arming, feast, ship-launch) admit substitution at named slots. Maps to: AFE-2 — install.sh should be authored as a template with externalized variables (`DIST_NAME`, `SKILL_DIR`, `INVOKE_NAME`) so a sibling Hermes distribution can reuse it. Two-hour refactor in v0.1; breaking change if deferred to v0.2.
- **Isomorphism:** metrical extension grammar — the formula has slots that admit nouns of the right metrical weight. Maps to: AFE-1 — MANIFEST capability schema needs an extension grammar (`type: skill | mcp-server | [future: thinker-profile]`) and an optional `depends_on:` field so v0.3 fills a known slot rather than re-opening the schema.
- **Isomorphism:** Homeric proem (invocation that names the work before the recitation). Maps to: AFE-4 — INSTALL.md needs a two-paragraph opening before the prereqs and commands. Open question that's easily answered.

## Frontier Patterns (Track D)

Three esoteric-domain agents surfaced patterns no inner track produced.

### fd-eleusinian-mystai-token — Greek mystery initiation

- **Pattern:** kataleptike phantasia ("gripping impression") is destroyed by epoptika (full sight) being delivered before mystika (preparatory encounter). The MANIFEST capabilities list, by enumerating "auraken-personality" and "auraken-lens" before the user has invoked anything, preempts the gripping impression. **Why unexpected:** Track A criticized the same MANIFEST as schema-incomplete; Track D criticizes its very enumeration as sequence-violating. The fix differs: A wants more fields, D wants INSTALL.md to defer the capabilities list (collapsible, end-of-doc).
- **Pattern:** symbolon — the token an initiate carries away that re-anchors the look in later encounters. **Why unexpected:** no inner-track agent thought to ask "what does the user keep that re-orients them?" Voice-rubric.md is the only candidate. The fix is small (a three-sentence human-readable header) and the design direction is new: the bundle should ship one user-facing object whose function is to reactivate the look, not document it.
- **Pattern:** ritual gradient (Lesser Mysteries → Greater Mysteries → epopteia). Maps loosely onto v0.1 → v0.2 → v0.3 but the brainstorm justifies the gradient by project-management rather than initiatory pacing. This opens a refinement direction more than a concrete fix: reframe `excluded_from_v01` in INSTALL.md so users know what's withheld for ritual reasons, not just scope reasons. P3-level — useful framing, not blocking.

### fd-luthier-soundpost-transmission — Cremonese violin-making

- **Pattern:** the soundpost is what makes a violin sound like a particular maker's instrument. Removing it leaves a working but generic wooden box. Maps to: the auraken-lens MCP's tool schema is currently unconstrained — if it can return a list of lenses, a generic model can offer a menu even if SKILL.md forbids it. **Why unexpected:** no Track A agent reviewing the MCP server reached for "the schema's geometry is the constraint, not the prompt." The fix is structural: server.py's primary tool should return `{lens, rationale, next_question}` — a single object — so the schema itself prevents menu-offering. **This is arguably the highest-leverage single technical change in the entire review.** One-line schema constraint that makes the never-offer-menu posture robust against model substitution.
- **Pattern:** voicing (adjusting the instrument to the room) vs deposit (delivering it). Maps to: install.sh step 3.5 — inspect destination profile for competing personality skills before depositing SKILL.md. This refines the "no Hermes prerequisite check" finding from Tracks A/B by extending it to "no profile-composition check" — a richer substrate-readiness inspection.
- **Pattern:** transmission-by-geometry vs transmission-by-recipe. Maps to: voice-rubric.md should be structural prohibitions, not example-based criteria. Examples decay across model versions; prohibitions don't. Converges with Track C's katachi finding but adds the prohibition framing.

### fd-mycorrhizal-inoculum — matsutake forestry

- **Pattern:** colonization vs deposit. Inoculum landing in soil is not the same as mycelium forming a symbiotic relationship with a host tree. Without a take-check (mycelial threads visible at 48-72 hours), failed inoculations look identical to successful ones. Maps to: MY-01 — install.sh has no post-install verification of whether the looking-discipline is establishing in the first conversation. **Why unexpected:** Track A/B treated "smoke test" as a binary-executes check; Track D extends it to "does the user notice the right shape in their own thinking?" The fix is a step 6.5 that prints a literal observation prompt: "After your first /auraken conversation, check: did it open with a question rather than a statement?"
- **Pattern:** substrate-readiness. Soil pH, moisture, competing organisms, host species — none of which "Hermes version >= 2026.4.0" captures. Maps to: MY-02 — profile-composition check at install time. Converges with the luthier voicing finding (LU-01) — same structural insight from two distant domains.
- **Pattern:** colonization window (first 48-96 hours). Maps to: MY-04 — INSTALL.md needs a "§ First Week" section describing the colonization window. **Why unexpected:** no inner-track agent thought to specify that user retention depends on a first-week ritual. New design direction: the bundle's documentation must teach the user what early colonization looks like.
- **Pattern:** active vs passive instrument. trajectory.py is named for tracking but the brainstorm doesn't say whether it actively reshapes calling-habits (colonization) or passively records them (deposit-only). Open question.

## Synthesis Assessment

**Overall quality of the brainstorm.** The brainstorm is structurally sound — Approach A (bundle-as-artifact) is the right call, the v0.1/v0.2/v0.3 split is coherent, the bundle layout names the right pieces, and the "Out of Scope" discipline is exemplary. But the brainstorm is operationally underspecified in three areas: (1) install.sh fails to model partial-failure / atomicity / idempotency / preflight detection, (2) the MCP server is monorepo-relative today and the bundle doesn't vendor or shell-out cleanly, and (3) the packaging surfaces (INSTALL.md, install.sh stdout, MANIFEST.yaml comments, voice-rubric.md) are described as scaffold rather than composed as part of the distribution's identity surface.

**Highest-leverage improvement (single change with the most impact).** Constrain `auraken-lens`'s primary tool schema to return a single-lens response shape `{lens, rationale, next_question}` rather than a list (fd-luthier-soundpost-transmission LU-03). This is one-sentence schema constraint, but it makes the never-offer-menu and ask-first posture robust against model substitution, register drift, and prompt-injection. Every other behavioral protection in SKILL.md is declarative and degrades with the model. This one is geometric and doesn't degrade. It also implies a structural register_check rather than a documentary one, which collapses three other findings (SKILL.md "never X" enforcement, voice-rubric.md as constraints not recipe, MANIFEST `binary_behavior_contract`) into a single architectural decision.

**Surprising finding (no single track would surface alone).** The convergence of "the install.sh step-6 next-steps output is structurally empty" across four distinct framings — DX (Track B), composition (Track C), initiation (Track D), and colonization (Track D) — surfaces a finding no single track would have produced as decisively. Each framing alone is "soft" (voice, ritual, ecology), but four independent agents pointing at the same six-line terminal output as the bundle's most-squandered surface is hard signal. The fix is a writing task with very high leverage: those final six lines printed by install.sh are the user's first encounter with anything Auraken-shaped. Currently they're going to be utilitarian. They should be composed in the brainstorm now, before implementation begins, and they should do four things: (1) say a literal first command (`> /auraken hello`), (2) carry Auraken voice (top-note), (3) frame the encounter rather than describe the tool (deikteria), (4) tell the user what to look for after the first conversation to know the discipline is establishing (take-check).

**Semantic distance value.** The outer tracks (C/D) contributed insights qualitatively different from inner tracks (A/B), not merely vocabulary translations. Specifically:
- **Track A could not have found** the soundpost-as-schema-geometry insight (LU-03). It's a frontier-domain structural import: the constraint is in the API shape, not in the prompt. Track A reviewed the MCP server's packaging correctness; Track D asked what kind of artifact the server is in the lineage of (Cremonese luthier object, not Python script).
- **Track A could not have found** the symbolon insight (EL-03) — the idea that voice-rubric.md must serve as a human-facing token, not just machine criteria. Track A's frontmatter conformance finding sits adjacent but in a different register.
- **Track B could not have found** the colonization-window framing (MY-04) — the first-week ritual. B's "What to expect" finding (SPPO-2) is necessary but stops at one paragraph; D extends to a structured first-week protocol.
- **Track C could not have found** the kataleptike phantasia ordering problem (EL-02) — that MANIFEST.yaml enumerating capabilities before the user encounters them violates initiatory sequence. C reached for authentica and proem; only D framed enumeration-as-spoiler.
- Where C and D *do* overlap with A/B (atomicity, prerequisites, take-checks), they don't merely restate — they add a new fix vocabulary (canonical_source, identity_role, deikteria, substrate-readiness) that makes the fixes more actionable as a coherent design language. The bundle now has a vocabulary for what kind of artifact it is, not just a list of things it must do.

The outer tracks earned their cost.

## Counts

- **Total findings synthesized across 16 agent reports:** 67 distinct issues (after intra-agent grouping).
- **P0/P1 count after dedup:** 15 (3 P0, 12 P1).
- **Convergence buckets:**
  - 4-track convergence: 1 finding (voice-rubric.md underspecified — A+B+C+D).
  - 3-track convergence: 7 findings (install.sh step 6 empty; preflight missing; provenance absent; binary mechanism deferred; MANIFEST schema premature; INSTALL.md proem/identity missing; binary-vs-Go ambiguity).
  - 2-track convergence: 4 findings (SKILL.md non-enforced rules; one-liner URL fragility; MCP shape unconstrained; rollback absent).
- **Single-track P0/P1 findings worth keeping:** 5 (AURAKEN_SRC monorepo path — code-verified single source; SKILL.md frontmatter ecosystem fields; first-/auraken-leak; Hermes version evidence; identifier consistency).

## Recommended Plan-Phase Deliverables

These follow directly from the convergent findings above. Each is a small artifact:

1. **install.sh state-transition table** (Track A): six rows, four columns.
2. **`scripts/build-dist.sh`** (Track A + C): explicit file list, version stamping, dist-tree integrity check.
3. **Compatibility-evidence table** (Track A): one row per Hermes × model × platform tested combination.
4. **install.sh terminal-output draft** (Track B + C + D): the literal six lines, written in Auraken voice, in the brainstorm itself.
5. **INSTALL.md outline with section ordering** (Track A + B + C + D): proem → prereqs → platforms → install (verify + one-liner) → what happens → what to expect → first-week protocol → troubleshooting → uninstall.
6. **voice-rubric.md three-section structure** (Track A + B + C + D): symbolon header / katachi (structural prohibitions) / permitted variation.
7. **MANIFEST.yaml v2 schema additions before freeze**: `canonical_source`, `manifest_sha256`, `stability: pre-release`, `identity_role` per capability, `quality/status` per model, extension-grammar comment for capability types, `depends_on` optional field.
8. **`auraken-lens` single-lens response shape decision** (Track D): one-sentence constraint in the brainstorm before plan phase.
9. **Binary distribution decision** (Track A + B + C): commit to option (a) vendor binaries, with option (b) pinned to `@v0.1.0` as fallback. Smoke-test `go install` against a clean cache before tagging.
10. **uninstall.sh** (Track A): reverses the six steps via the install marker file.
