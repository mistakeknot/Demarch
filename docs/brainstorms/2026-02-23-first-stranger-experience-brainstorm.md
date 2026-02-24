# First-Stranger Experience — Brainstorm
**Bead:** iv-t712t

**Date:** 2026-02-23
**Status:** Brainstorm complete, ready for strategy

## What We're Building

A complete onboarding experience so that a developer who has never seen Demarch can go from zero to running `/clavain:route` and getting work — in under 5 minutes.

Three deliverables:
1. **Root README.md** — user-facing landing page (replaces current developer-facing structure doc)
2. **install.sh** — curl-fetchable install script for Clavain + Interverse
3. **Validated first-run** — `/clavain:route` as the success moment

## Why This Approach

### Target Audience: Three Tiers

1. **Claude Code power user** — already has Claude Code, wants Clavain. Quick Start path (~2 min).
2. **AI-curious developer** — used Copilot/Cursor, not Claude Code. Full Setup guide needed.
3. **Open-source contributor** — wants to build/modify Demarch itself. Dev Setup with Go, tests, all pillars.

Progressive disclosure: README leads with Quick Start, links to deeper guides.

### Install Scope: Clavain + Interverse Only

The install script handles the plugin ecosystem:
- Check prerequisites (claude CLI, jq, git)
- Add interagency-marketplace
- Install clavain plugin
- Run `/clavain:setup` (auto-installs 12+ companions)
- Init beads in current project
- Verify with `/clavain:doctor`

Go stack (Intermute, Intercore/ic, Autarch) is optional and documented as add-on guides. Rationale: Clavain alone is fully functional. Go builds are fragile across platforms and would block 90% of users who don't need them.

### Success Moment: `/clavain:route` Works

The stranger runs `/clavain:route` with no arguments. Discovery finds beads or offers a fresh brainstorm. This proves:
- Plugin loaded correctly
- MCP servers connected
- Beads CLI working
- Sprint workflow functional

### Distribution: GitHub Raw

```bash
curl -fsSL https://raw.githubusercontent.com/mistakeknot/Demarch/main/install.sh | bash
```

Zero infrastructure. Updates on push to main. Short URL (get.demarch.dev) can be added later.

## Key Decisions

1. **Root README replaces current structure doc** — current README is developer-facing monorepo structure. New README leads with "what is this / why care / how to install" and pushes structure to an Architecture section at the bottom. Pillar READMEs stay as-is for deep dives.

2. **Install script is Clavain-only** — no Go builds, no systemd services. KISS. Full-platform install is a separate doc (docs/guide-full-setup.md) for Tier 2/3.

3. **Three guide tiers** — README Quick Start (inline), docs/guide-power-user.md (detailed), docs/guide-full-setup.md (everything including Go stack), docs/guide-contributing.md (dev setup).

4. **Prerequisites are checked, not installed** — install.sh verifies claude, jq, git exist and gives clear error messages if missing. Does NOT attempt to install them (too platform-specific, too opinionated).

5. **`/clavain:route` is the litmus test** — not `/doctor` (proves infrastructure, not workflow), not "complete a sprint" (too high a bar for first-run).

## Open Questions

1. **Should install.sh also init beads?** Beads is project-scoped (`bd init` in a repo). The install script runs outside any specific project. Maybe: init beads only if CWD is a git repo, skip otherwise with a hint.

2. **GitHub repo visibility** — Demarch repo is currently private(?). First-stranger experience requires the repo (or at least install.sh and marketplace) to be public. Needs owner decision on what to open-source.

3. **Claude Code marketplace access** — does `claude plugins marketplace add` work for any user, or does the marketplace need to be public/approved? Need to verify.

4. **Beads CLI distribution** — install.sh assumes `bd` is installed. How does a stranger get `bd`? Needs a pre-step or bundling.

## Scope Boundaries

**In scope:**
- Root README.md (replace existing)
- install.sh (Clavain + Interverse)
- docs/guide-power-user.md
- docs/guide-full-setup.md
- docs/guide-contributing.md
- Validation: actually run through as a stranger on a clean machine (or container)

**Out of scope (future work):**
- ic binary distribution (separate bead)
- Custom domain (get.demarch.dev)
- Video walkthrough
- Autarch TUI onboarding
- Automated CI for install script testing
