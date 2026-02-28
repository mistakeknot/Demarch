---
title: "Stranger-Perspective Documentation Validation"
category: best-practices
severity: medium
tags: [documentation, validation, drift, onboarding, quality-gates]
created: 2026-02-28
root_cause: "Docs written at design time drift as the project evolves — counts, versions, build commands, and architectural definitions become stale without automated detection"
---

# Stranger-Perspective Documentation Validation

## Problem

Documentation written during feature planning (brainstorms, PRDs, guides) quickly becomes stale as the project evolves. The author doesn't notice because they have context — they know `make build` was replaced by `go build`, that plugin count grew from 12 to 40+, that a pillar definition changed. A stranger hitting these docs for the first time will fail silently or get confused.

## Drift Classes Discovered

The validation of Demarch's first-stranger experience (README, install script, 3 tier guides) found **23 issues** across 5 drift classes:

| Drift Class | Example | Count |
|------------|---------|-------|
| **Stale counts** | "12+ plugins" when actual is 40+ (26 default + 14 optional) | 4 |
| **Wrong build commands** | `make build` when no Makefile exists; should be `go build ./cmd/...` | 1 |
| **Architectural definition mismatch** | Pillar table listed Intermute (not a pillar) instead of Interspect | 2 |
| **Deprecated commands in examples** | `bd sync` shown as workflow step despite being a deprecated no-op | 2 |
| **Version/output staleness** | Doctor expected output showed v0.6.76 when actual is v0.6.110 | 3 |
| **Missing prerequisites** | Power user guide omitted jq and git (required by install.sh) | 1 |
| **Ambiguous paths** | `cd Demarch/core/intercore` without clarifying working directory | 3 |

## Solution Pattern

### 1. Dispatch a Stranger-Perspective Audit Agent

Use a sonnet-tier subagent with explicit instructions to "act as a stranger reading these docs for the first time." The agent checks:

- **Broken/dead links** — do referenced files exist?
- **Stale counts** — do hardcoded numbers match reality?
- **Command validity** — do build commands actually work?
- **Cross-doc consistency** — does one doc contradict another?
- **Prerequisites** — is everything needed actually listed?
- **Deprecated references** — are removed/changed tools still mentioned?

### 2. Fix Strategy: Prefer Dynamic Over Static

Where possible, replace hardcoded values with descriptions that age gracefully:

- Bad: `Companions: 12/12 installed` (stale within weeks)
- Good: "The output includes plugin version, MCP connections, beads CLI, companion plugin count, and hook status"
- Bad: `Plugin loaded: clavain v0.6.76`
- Good: Description of what to expect rather than exact output

### 3. When to Run

- **Before shipping** any user-facing documentation change
- **Periodically** (monthly) on all onboarding docs
- **After major architectural changes** (new pillars, renamed modules, deprecated commands)

## Key Insight

The author-stranger gap is the #1 doc quality risk. The author has compensating context that masks staleness — they read "12 plugins" and mentally substitute "whatever the current count is." A stranger reads "12 plugins," installs 38, and wonders if something went wrong. The fix is not better writing — it's systematic validation from a context-free perspective.

## Related

- interwatch doc-watch (automated drift detection, but measures freshness not correctness)
- docs/canon/doc-structure.md (structural conventions)
- interscribe (doc quality enforcement)
