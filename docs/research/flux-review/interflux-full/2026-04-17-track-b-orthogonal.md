---
artifact_type: track-findings
track: B
distance: orthogonal
target: /home/mk/projects/Sylveste/interverse/interflux
target_description: interflux plugin (multi-agent review + research engine)
date: 2026-04-17
model: sonnet (review)
agents_applied_as_perspectives:
  - fd-academic-publishing (peer-review editorial workflow; NeurIPS/JMLR patterns)
  - fd-release-engineering (Chromium/Debian CI/CD, release-train discipline)
  - fd-doc-review-platform (Gerrit/Phabricator/Review Board patterns)
  - fd-standards-editing (W3C/IETF spec lifecycle)
---

# Track B — Orthogonal (Parallel-Discipline Findings)

These findings come from asking: "What does interflux look like to a practitioner whose field solved similar problems in a different industry?" The distance is one step out — parallel disciplines, not distant metaphors.

## B-P1-1: No "reviewer of record" concept — academic publishing would flag this immediately

Source domain: academic peer review (NeurIPS, journal editorial boards).

Every peer-reviewed publication has a **reviewer of record** — a named party accountable for the review artifact, with their identity on the line. Interflux's fd-* agents produce findings indexed by agent name (`fd-safety`, `fd-architecture`, etc.), but nowhere in the finding artifact is there a traceable **model × version × prompt-hash** triple. If a finding is later contested, you can't reproduce it: was this fd-safety running Opus 4.6 or 4.7? Was it the v5 severity calibration template or v6? The `flux_gen_version: 6` field exists in generated agent frontmatter but isn't carried into findings.

**Recommendation:** Every findings file should begin with a provenance block: `{agent_name, agent_version (frontmatter hash), model_id, model_api_version, prompt_template_version, project_state_commit_hash, reviewed_at}`. This is the editorial metadata academic reviewers supply by default and that interflux's machine-reviewers omit.

## B-P1-2: No errata / corrigendum path for retracted findings

Source domain: academic publishing.

When a peer-reviewed paper is retracted or corrected, the retraction is **linked to the original** — not a silent deletion. Interflux has `bd close --reason=...` for beads but no analogous mechanism for **findings** that later turn out to be wrong (false positives identified after fact). The `/interspect:correction` command exists but it's flagged as "record that an agent got something wrong" — this is reviewer-feedback, not a formal retraction tied to the specific finding ID. The orthogonal view: every finding should have a URL-like stable ID (e.g., `interflux://findings/2026-04-17T1432/fd-safety/F-03`) and retractions should be first-class artifacts.

## B-P1-3: "Master registry" pattern should have a release-engineering discipline

Source domain: release engineering (Debian apt archives, Chromium's rev pinning).

`config/flux-drive/model-registry.yaml` (235 lines, with a separate `.lock` file that is 0 lines!) is the effective "package index" for which review models are qualified. The `.lock` file pattern is used in package managers (npm, Cargo, uv) to pin resolved versions reproducibly. But here the `.lock` is **empty** — the pattern is cosmetic, not real. Release engineering would call this a footgun: developers seeing `.yaml.lock` will assume lockfile semantics that don't exist. Either populate it (resolve every listed model with its current pricing / context window / availability status) or delete it.

## B-P1-4: FluxBench scoring has no cold-start / canary discipline

Source domain: release engineering (staged rollouts, canary deploys).

`fluxbench-qualify.sh` runs a model against fixtures and writes qualified_baseline on first pass. Release engineering's equivalent is **cold-start canaries** — when a new model joins the fleet, its first K production uses should be shadowed (results logged, not affecting verdict). Interflux has `fluxbench-challenger.sh select` which does this — but the threshold is `>= promotion_threshold` runs, typically set in code defaults, and there's no **time-boxed** canary window. The pattern should be: new model → shadow for 7 days → review shadow metrics → promote or reject. Currently it's purely N-runs based, which can cluster in one bad week.

## B-P2-5: "Discourse" naming is jarring in a code-review context

Source domain: document-review platforms (Gerrit, Phabricator, Review Board).

Interflux uses "discourse" as a subsystem name (`discourse-fixative.yaml`, `discourse-lorenzen.yaml`, `discourse-sawyer.yaml`, `discourse-topology.yaml`, `discourse-health.sh`). A release-engineer or a Gerrit-user reading this project would read "discourse" as the discussion-forum software (`discourse.org`), not as Habermasian discourse ethics. Within Sylveste's own vocabulary this may be clear, but the public-facing plugin listing makes "Interflux — multi-agent review … discourse-fixative, discourse-lorenzen …" look like integration with Discourse the forum platform. Consider: `dialogue-*`, `colloquium-*`, or a prefix like `ifdh-*` (interflux discourse health) that removes the ambiguity.

## B-P2-6: Prompt template versioning uses an integer (`FLUX_GEN_VERSION = 6`) — SemVer would help

Source domain: standards editing (W3C RECs, IETF RFCs).

Standards bodies version their documents as `major.minor` with documented migration paths. Interflux's template version is a monotonic integer with the comment `# v5: severity calibration (severity_examples field + escalation instruction)` / `# v6: extended frontmatter (tier, domains, use_count, source_spec)`. A reader of an existing v5 agent file cannot tell what breaking-vs-additive changes happened between 5 and 6. If frontmatter additions are always additive (old agents still work), that should be `major=5` and 5.1, 5.2 are additions. A breaking change would be `major=6`. This matters because `regenerate-stale` mode compares `existing_version >= FLUX_GEN_VERSION` — a consumer can't tell which previous versions are safely regenerable.

## B-P2-7: No changelog entry format for agent-registry changes

Source domain: standards editing + release engineering.

The agent registry (`scripts/flux-agent.py`, 759 lines) tracks `use_count`, `last_used`, `tier` (proven/used/experimental) across agents. When an agent gets promoted from `used` → `proven`, there's no changelog record of **why** — no bead, no JSONL event, no git commit message explaining the criteria that made the promotion fire. Release engineering would expect: every tier transition emits an event to `data/flux-agent-events.jsonl` with `{agent_name, from_tier, to_tier, criteria_satisfied, use_count_at_transition, timestamp}`. Without this, the tiering system is a black box even to the project maintainer.

## B-P2-8: No "reviewer-author conflict of interest" declarations

Source domain: academic publishing.

When fd-architecture reviews the interflux plugin itself (which this review literally is), there's a structural conflict: the reviewer is part of the reviewed system. Academic venues handle this with COI declarations. Interflux has no concept of "this review is reflexive" — no warning when the review target is inside the reviewer's own codebase, no recusal mechanism. The orthogonal view: flag when `INPUT_PATH` is inside `${CLAUDE_PLUGIN_ROOT}` or shares a git root with loaded plugins, and add a meta-finding: `Reflexive review — findings may be biased by familiarity`.

## B-P2-9: `tests/fixtures/qualification/` has no golden-file regeneration protocol

Source domain: release engineering (golden file testing in compilers).

FluxBench qualification runs models against fixtures and compares metrics to `qualified_baseline`. When fixture content itself changes (bug fixed in ground-truth), existing baselines become invalid across **all** qualified models simultaneously. There's no versioning on fixtures — a fixture edit in git is a silent change that invalidates every prior qualification. Release engineering pattern: fixture directory includes `fixtures-version` or content-hash-addressed subdirs, and the baseline records which fixture version it was scored against.

## B-P2-10: SKILL.md is 301 lines; SKILL-compact.md is 326 lines — compact is longer

Source domain: standards editing.

A spec author would immediately flag this: the "compact" artifact is 8% longer than the canonical one. Either SKILL.md is under-documented (missing steps compact has) or SKILL-compact.md is mis-named (it's a parallel full version, not a compact summary). Looking at the content, SKILL-compact.md includes inline tables and spec text that SKILL.md delegates to phase files — so SKILL-compact is arguably **more complete in a single file**, not less content. The filename is a lie in the package sense. Rename or reconcile.

## Verdict

Viewed from parallel disciplines, interflux has the shape of a well-designed system but lacks the **editorial hygiene** those disciplines take for granted. Findings need provenance and stable IDs. The registry/lockfile pattern is cosmetic. Tier promotions and prompt-template changes lack changelog discipline. And the "discourse" naming will read as Discourse-the-forum to almost every first-time user. The parallel-discipline view adds a lot to the architectural view from Track A.
