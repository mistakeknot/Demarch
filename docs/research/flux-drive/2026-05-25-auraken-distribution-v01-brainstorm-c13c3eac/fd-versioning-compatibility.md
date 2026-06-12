<!-- flux-drive:complete -->
<!-- run_uuid: 57272bdd-9eb0-42d1-8ae7-ed79e4d7aa8a -->

# fd-versioning-compatibility — Review

**Target:** docs/brainstorms/2026-05-25-auraken-distribution-v01-brainstorm.md
**Lens:** compatibility-engineer perspective on MANIFEST.yaml claims, model identifiers, and the precision of the stated compat ranges.

## Findings Index

- F1 (P1) — `hermes_agent: ">=2026.4.0"` lower bound has no test evidence cited; brainstorm does not name which API or config format introduced in 2026.4.0 is required
- F2 (P1) — `claude-opus-4-7` and `gpt-5.5` are short-form model identifiers; provider APIs require canonical dated suffixes for some calls and short forms for others — MANIFEST should be explicit about which the user copies into Hermes config
- F3 (P1) — "Observed register drift" for `gpt-5.5` is mentioned in the brainstorm but not modeled in MANIFEST.yaml; users have no way to read "tested-quality" from the model list
- F4 (P1) — `auraken-lens@v0.1.0` Go module version (MANIFEST capabilities block) is not verified as an existing git tag in the brainstorm; install.sh trying `go install` could 404
- F5 (P2) — `claude-haiku-4-5-20251001` uses a full dated suffix while `claude-opus-4-7` does not — inconsistent within the same MANIFEST block
- F6 (P2) — `excluded_from_v01` field is asserted as "doctrine" but is not part of any published schema; downstream tooling (e.g., agentskills.io scanners) may flag the unknown field
- F7 (P2) — SemVer pre-1.0 policy ("v0.1 → v0.2 may break installs") is mentioned in the brainstorm but the MANIFEST.yaml schema does not encode it; users have no signal except CHANGELOG.md after the break
- F8 (P3) — `schema: auraken-distribution/v1` is declared without a published schema URL; ecosystem validators cannot resolve it

## Verdict

The MANIFEST.yaml schema is **structurally sound but factually unverified.** Most claims (Hermes range, model list, binary version) are reasonable guesses, not tested ground truth. v0.1 must either (a) ship the test evidence behind each version range (one row per Hermes version × model pair, with pass/fail), or (b) downgrade the claims to "validated against X; expected to work on Y; untested elsewhere" — the brainstorm partially does the latter for platforms but not for models or Hermes versions.

The deeper risk is the precedent: v0.1 sets the **MANIFEST schema** that v0.2 and beyond must respect. Getting model-identifier convention, range-semantics, and schema discoverability wrong now compounds across releases.

## Summary

The brainstorm declares `compatibility.hermes_agent: ">=2026.4.0"` and a model matrix with both short-form and dated identifiers. None of these are pinned to specific evidence — no "tested on Hermes 2026.4.2, 2026.5.0, 2026.5.1" row, no "claude-opus-4-7-20260418 → passes; claude-opus-4-7-20251022 → register drift" note. The brainstorm's MEMORY.md context notes "Default all Clavain Codex dispatch tiers to gpt-5.5 (updated 2026-05-04, was gpt-5.4)" — model identifiers do shift over time, and the v0.1 MANIFEST will go stale by the time it lands on agentskills.io if it isn't actively maintained or sourced from a registry.

Plan phase needs a **compatibility-evidence table** as a deliverable separate from MANIFEST.yaml: one row per claimed combination, columns for evidence type (smoke test, dogfood, doc claim), date, and pass/fail. This becomes the source of truth for what MANIFEST asserts.

## Issues Found

### F1 — P1 — Hermes lower bound has no cited evidence

**Where:** brainstorm §"MANIFEST.yaml schema (v1)" line 58: `hermes_agent: ">=2026.4.0"        # minimum tested; bumps as testing widens`.

**Failure scenario:** install.sh refuses to install on Hermes 2026.3.x; the user upgrades to 2026.4.0 (the stated minimum); install succeeds but Hermes 2026.4.0 lacks a config-format change introduced in 2026.4.1 that install.sh step 5's `mcp_servers:` snippet depends on. User sees cryptic Hermes startup error after install completed cleanly. Or: the lower bound was set to 2026.4.0 because that's what the developer happens to run, with no actual 2026.4.0 boot test — and the recon spike was implicitly developed against 2026.5.x.

**Question:** Which specific Hermes change introduced in 2026.4.0 does the auraken bundle require? `skill_commands.py`'s cache-safe injection pattern (apps/Auraken/integrations/hermes/README.md §"Cache discipline")? The `mcp_servers:` config key? `lens_select` tool registration? Cite the smallest required feature.

**Smallest viable fix:** Plan phase: name the specific Hermes feature/API the bundle depends on. If unknown, set `hermes_agent: ">=X.Y"` where X.Y is the Hermes version the recon spike was actually validated against (or the dev machine version) — not an aspirational range. The MANIFEST comment "minimum tested; bumps as testing widens" is correct framing; the value should match what's actually tested.

### F2 — P1 — Model identifier short vs. dated form inconsistency

**Where:** brainstorm MANIFEST lines 60–66:
```yaml
  models:
    claude:
      - claude-opus-4-7              # primary validation target
      - claude-haiku-4-5-20251001
    openai:
      - gpt-5.5                      # observed register drift documented
      - gpt-5.4
```

**Failure scenario:** Anthropic's API accepts both short (`claude-opus-4-7`) and dated (`claude-opus-4-7-20260418`) identifiers, but `claude-haiku-4-5-20251001` uses the dated form. Behavior differs: the short form may alias to the latest minor that ships; the dated form locks to a specific snapshot. A v0.1 user who copies `claude-opus-4-7` into Hermes config gets whichever Opus 4.7 snapshot is current at session-start time, not the one validated. Register drift between snapshots is the exact failure mode the brainstorm acknowledges for gpt-5.5 — and the model list as written doesn't protect against the same issue for Claude.

OpenAI side: `gpt-5.5` is also a short-form alias. The Sylveste MEMORY.md notes "Default all Clavain Codex dispatch tiers to gpt-5.5 (updated 2026-05-04, was gpt-5.4); xhigh variants still suspect on ChatGPT-account auth" — provider-side this string moves under the user's feet.

**Question:** Should the v0.1 MANIFEST commit to dated identifiers for reproducibility, short-form for currency, or list both with a "tested-against (dated)" column? The brainstorm's framing is "primary validation target" — that strongly suggests dated.

**Smallest viable fix:** Pick one convention and apply consistently. Recommended: dated form everywhere (`claude-opus-4-7-20260418`, `gpt-5.5-20260504`); add a "compatible-aliases" sub-list for the short forms that documents the aliasing behavior.

### F3 — P1 — Register drift not modeled in schema

**Where:** brainstorm MANIFEST line 64: `      - gpt-5.5                      # observed register drift documented`.

The comment refers to "observed register drift" but MANIFEST.yaml itself does not encode quality. A user reading the YAML programmatically sees `gpt-5.5` listed under `models.openai` with no annotation; only the comment notes drift. Comments are not data — they don't survive YAML round-trip through schema validators or downstream tooling.

**Failure scenario:** agentskills.io scrapes the model list and presents it as "supported models" without rendering YAML comments. User sees gpt-5.5 listed, picks it, gets the voice drift that the comment was warning about. The brainstorm's voice-rubric work (F3 in fd-skill-bundle-conformance) is exactly the mitigation, but MANIFEST.yaml doesn't surface the dependency.

**Smallest viable fix:** Encode quality as data:
```yaml
  models:
    claude:
      - id: claude-opus-4-7-20260418
        quality: primary
    openai:
      - id: gpt-5.5-20260504
        quality: degraded
        notes: register drift; voice-rubric register_check recommended
```
This survives YAML parsers and ecosystem tooling.

### F4 — P1 — Go module tag is unverified

**Where:** brainstorm MANIFEST lines 76–77:
```yaml
  - id: auraken-lens
    type: mcp-server
    path: mcp-servers/auraken-lens/
    binary_required: github.com/mistakeknot/Sylveste/apps/Auraken/dist/auraken-lens@v0.1.0
```

**Failure scenario:** If the lens-binary distribution settles on option (b) (`go install`), users will execute `go install github.com/mistakeknot/Sylveste/apps/Auraken/dist/auraken-lens@v0.1.0`. Two ways this fails today:
1. The Go module path doesn't match a published module (Sylveste's repo structure has the binary at a different Go module root than the literal path above).
2. The `@v0.1.0` tag may not exist as a git tag at v0.1 release time — brainstorm's beads `benl.1` references "Go package, shipped" but no MANIFEST claim ties the tag to an actual git reference.

**Question:** Does `go install github.com/mistakeknot/Sylveste/apps/Auraken/dist/auraken-lens@v0.1.0` succeed today against a clean Go cache?

**Smallest viable fix:** Plan phase: run `go install` against a clean module cache from a checkout that does not include local replace directives; capture the output. If it fails, fix the module path in MANIFEST before publishing v0.1.

### F5 — P2 — Identifier-form inconsistency within Claude list

**Where:** brainstorm MANIFEST lines 62–63:
```yaml
      - claude-opus-4-7
      - claude-haiku-4-5-20251001
```

Same issue as F2 but specifically within a single model family: opus uses short form, haiku uses dated. If the convention is "primary uses short, secondary uses dated" the rationale should be in a comment or schema doc. Currently reads as accidental.

**Smallest viable fix:** Same convention everywhere (see F2 fix).

### F6 — P2 — `excluded_from_v01` not part of published schema

**Where:** brainstorm MANIFEST lines 79–84.

The field is "doctrine — it answers 'is this in v0.1?' without re-litigating each time". Useful internally. Risk: it's an ad-hoc field in a public artifact. agentskills.io schema validators (when v0.2 submits) may reject unknown fields, or strip them, or surface them as warnings. Even self-distribution: a user running a generic YAML linter against the bundle gets unrecognized-key warnings.

**Question:** Is `auraken-distribution/v1` a Sylveste-private schema or intended for agentskills.io? If private, fine — but flag that v0.2 needs to map `excluded_from_v01` into whatever standard exclusion mechanism exists upstream.

**Smallest viable fix:** Either (a) move `excluded_from_v01` to a separate file (`SCOPE.md` or `excluded.yaml`) so MANIFEST.yaml conforms to a smaller schema, or (b) namespace it under `x-sylveste:` (or similar) so consumers can ignore unknown extensions cleanly.

### F7 — P2 — SemVer pre-1.0 policy is undisclosed in MANIFEST

**Where:** brainstorm §"Versioning" line 112: "v0.1 → v0.2 may break installs (intentional). v0.2 prints a clear migration note in install.sh."

The MANIFEST.yaml has no `pre_release: true` or `breaking_changes_allowed: true` field. A consumer reading MANIFEST.yaml alone cannot tell that v0.1 → v0.2 is permitted to break. They have to read CHANGELOG.md or INSTALL.md.

**Failure scenario:** Tooling that auto-upgrades distributions (hypothetical) sees v0.2 released and pulls it, expecting SemVer minor-bump compatibility per public conventions. Install breaks because v0.1 → v0.2 changed install.sh's profile-write semantics. The user has no upstream warning to surface.

**Smallest viable fix:** Add to MANIFEST.yaml:
```yaml
stability: pre-release
breaking_changes_between_minors: true
upgrade_notes_path: CHANGELOG.md
```

### F8 — P3 — Schema URL not resolvable

**Where:** brainstorm MANIFEST line 52: `schema: auraken-distribution/v1`.

There is no URL or path resolving this schema. Downstream validators (jsonschema, ajv, yamale) cannot fetch a schema document. Internal docs only.

**Smallest viable fix:** v0.2 — publish `schemas/auraken-distribution-v1.json` (jsonschema) in the Sylveste repo. v0.1 can defer; flag in CHANGELOG that the schema is not yet machine-validatable.

## Improvements

- **Compatibility-evidence table as a plan-phase deliverable.** One row per (Hermes version × model × platform) tested combination. Columns: evidence type (smoke / dogfood / doc-claim), date, pass/fail, notes. MANIFEST.yaml renders from this table.
- **Pick a model-identifier convention and document it.** Dated everywhere is the safest default for reproducibility.
- **Encode quality as data, not comments.** Anything a downstream tool should see needs to be a YAML key.
- **`go install` smoke test in CI.** Before tagging the release, run `go install` against a clean GOPATH and verify the binary actually builds at the tagged commit. Cheap, prevents F4.
- **Single-source `version` everywhere.** MANIFEST.yaml is canonical (already noted in fd-mcp-server-packaging F7); SKILL.md frontmatter, pyproject.toml, and INSTALL.md derive at build time.
