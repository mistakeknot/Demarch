---
date: 2026-05-06
topic: cross-plugin contract collision triage
beads: [sylveste-qow6, sylveste-0usg, sylveste-t0sz]
parent_findings: docs/research/2026-05-06-lattice-architectural-findings.md
---

# Collision triage — Sylveste cross-plugin contracts

The lattice flagged 12 cross-plugin name collisions in its v0b scan. On inspection, **8 of those are false positives** caused by the connector keying off filename stem rather than the `name:` frontmatter field — several plugins already self-namespace via `name: <plugin>-<command>`, which makes their slash invocation unambiguous. Of the four real collisions, three are cross-domain verb sharing that plugin namespacing already disambiguates, and one is a meaningful clash worth resolving.

## Connector finding

`interverse/lattice/src/lattice/connectors/architecture.py:453` keys the contract index off `command_path.stem` rather than the `name:` field in the file's YAML frontmatter. That over-reports collisions whenever a plugin self-namespaces its frontmatter (`name: clavain-status` rather than `name: status`). Several plugins do this already as a deliberate hygiene practice. The connector should read `name:` first and fall back to the stem only when frontmatter is missing or malformed. Filed as **sylveste-0usg (v0c.6)**.

## False positives — lattice over-reported

These collide on filename only; the `name:` field already disambiguates and the slash invocation is unambiguous:

| Lattice flag | Reality |
|---|---|
| `command:status` (6) | Only `interlore` and deprecated `interscout` keep `name: status`. Four self-namespace (`clavain-status`, `interlock-status`, `interpath-status`, `interwatch-status`) |
| `command:changelog` (2) | `interpath` uses `name: interpath-changelog`; clavain owns unqualified `/changelog` |
| `command:doctor` (2) | Both self-namespace (`clavain-doctor`, `interkasten-doctor`) |
| `command:review` (2) | `clavain` uses `name: clavain-review`; interlore owns unqualified `/review` |
| `skill:status` (4) | Three of four self-namespace (`interject-status`, `status-engine`, `interstat-status`); only `intersite` keeps bare `status` |
| `skill:analyze` (3) | All three self-namespace (`voice-analyze`, `design-analyze`, `interstat-analyze`) |
| `skill:report` (2) | Both self-namespace (`feature-report`, `interstat-report`) |
| `skill:scan` (2) | `interblog` uses `scan-engine`; only `interject` keeps `scan` |
| `skill:synthesize` (2) | `intermem` uses `memory-synthesis`; only `interbrowse` keeps `synthesize` |

Once the connector reads `name:` field, this list collapses to zero.

## Real collisions — verdicts

Four collisions remain after switching to `name:`-based detection.

### 1. `command:research` — interbrowse vs interdeep — **ACCEPT**

| Plugin | Description |
|---|---|
| interbrowse | Competitive research — identify competitors, parallel teardowns + docs-crawls, synthesize patterns + CUJs |
| interdeep | Start a deep research session on a topic |

Different domains: web-driven competitive research versus general deep agentic research. The plugin namespace cleanly disambiguates (`/interbrowse:research` vs `/interdeep:research`), and unqualified `/research` would be context-dependent regardless of policy. Both verbs are correct in their context.

**Action:** None. Document as cross-domain verb sharing.

### 2. `command:scan` — interblog vs interlore — **ACCEPT**

| Plugin | Description |
|---|---|
| interblog | Surface blog-worthy themes from the Demarch ecosystem |
| interlore | Scan decision artifacts for design patterns and philosophy drift |

Different objects of scan (blog story candidates versus design philosophy drift). Plugin namespace disambiguates.

**Action:** None.

### 3. `command:status` — interlore + deprecated interscout — **SELF-RESOLVING**

`interscout:status` was deprecated 2026-04-27 with a redirect to `/clavain:status`. Once the deprecation period ends and the file is removed, only `interlore:status` will remain claiming the unqualified verb, and even that is plugin-namespaced in invocation.

**Action:** Re-check after the next interscout cleanup. No new bead needed; existing deprecation will absorb this.

### 4. `command:setup` — clavain vs intership — **RENAME intership**

| Plugin | Description | Scope |
|---|---|---|
| clavain | Bootstrap Clavain for the active runtime (Codex or Claude Code) and verify health | Platform-level |
| intership | Customize Culture ship spinner verbs — pick books, add/remove ships, toggle mode | Plugin-specific cosmetic |

Clavain owns the platform-level "set up the system" semantics. intership's `setup` is a spinner-verb customizer — narrower scope, and a user typing `/setup` reasonably expects the platform-level one. The intership claim is the only real ambiguity worth resolving with a rename.

**Action:** Rename `intership:setup` to `intership:customize` (or similar). Filed as **sylveste-t0sz**.

## Recommended CI guard

Add a structural test that runs against the lattice's `cross_plugin_collisions` template (after the v0c.6 connector fix) and fails if any new collision appears on the `name:` axis. The list of accepted collisions is the two ACCEPT entries above; new entries require a triage update.

The test belongs in lattice's `tests/` directory, since lattice is the source of truth for the collision detection logic. It runs via `uv run pytest -k collisions` on the lattice repo, and the CI hook for the monorepo invokes lattice as a subprocess.

This is a small enough surface to land alongside the v0c.6 connector fix.

## Summary

| Category | Count |
|---:|---|
| Lattice-reported | 12 |
| False positives (connector bug) | 8 |
| Real, cross-domain (accept) | 2 |
| Real, self-resolving (deprecated path) | 1 |
| Real, action required (rename) | 1 |

Net work: one connector fix (v0c.6), one rename (intership), one CI guard.
