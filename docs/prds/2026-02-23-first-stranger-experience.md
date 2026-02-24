# PRD: First-Stranger Experience
**Bead:** iv-t712t

## Problem

No outside user has ever installed or run Demarch. There is no README explaining what it is, no install script, and no validated path from zero to working system. The project cannot grow beyond its author.

## Solution

Three-tier onboarding (Quick Start / Full Setup / Contributing) with a curl-fetchable install script, user-facing README, and a validated first-run that proves the system works by running `/clavain:route`.

## Features

### F1: Root README.md

**What:** Replace the current developer-facing monorepo structure README with a user-facing landing page.

**Acceptance criteria:**
- [ ] README.md leads with a one-line description of what Demarch is
- [ ] Quick Start section with curl install command (< 5 lines to working system)
- [ ] "What You Get" section listing key capabilities (Clavain, plugins, multi-agent review, sprint management)
- [ ] Links to three tier guides (power user, full setup, contributing)
- [ ] Architecture section preserves current monorepo structure info (moved to bottom)
- [ ] Pillar READMEs (os/clavain/, core/intermute/, etc.) remain unchanged

### F2: install.sh

**What:** Curl-fetchable bash script that installs Clavain + Interverse plugin ecosystem.

**Acceptance criteria:**
- [ ] Hosted at repo root, fetchable via `curl -fsSL https://raw.githubusercontent.com/mistakeknot/Demarch/main/install.sh | bash`
- [ ] Checks prerequisites: `claude` CLI, `jq`, `git` — clear error messages if missing
- [ ] Checks for `bd` (beads CLI) — warns if missing with install hint, does not block
- [ ] Adds interagency-marketplace via `claude plugins marketplace add`
- [ ] Installs clavain plugin via `claude plugins install`
- [ ] Runs `claude /clavain:setup` non-interactively (or equivalent setup steps)
- [ ] If CWD is a git repo, runs `bd init` — otherwise prints hint
- [ ] Runs `/clavain:doctor` equivalent checks as final verification
- [ ] Prints success message with "next steps: open Claude Code, run /clavain:route"
- [ ] Idempotent — safe to run multiple times
- [ ] Works on macOS and Linux (bash 4+)
- [ ] Has `--help` flag and `--dry-run` flag
- [ ] No Go builds, no systemd, no platform-specific package managers

### F3: Tier Guides

**What:** Three documentation guides for progressive-disclosure onboarding.

**Acceptance criteria:**
- [ ] `docs/guide-power-user.md` — Clavain workflow walkthrough: route → brainstorm → sprint → ship. Assumes Claude Code already installed. Includes common slash commands reference.
- [ ] `docs/guide-full-setup.md` — Everything in power user guide plus: Go stack (Intermute, Intercore/ic, Autarch), systemd services, Oracle setup. For users who want the full platform.
- [ ] `docs/guide-contributing.md` — Dev setup: clone monorepo, build all pillars, run tests, plugin development workflow, PR conventions. For open-source contributors.
- [ ] Each guide has a "Prerequisites" section listing exactly what's needed
- [ ] Each guide has an "Expected time" estimate
- [ ] Guides link to each other where relevant (progressive: "want more? see X")

### F4: First-Run Validation

**What:** Actually execute the install on a clean environment and verify `/clavain:route` works.

**Acceptance criteria:**
- [ ] Run install.sh on a clean Linux environment (container or fresh user account)
- [ ] Verify all install steps complete without error
- [ ] Open Claude Code, run `/clavain:route` — confirm it returns discovery results or brainstorm option
- [ ] Document any issues found and fix them in F1/F2/F3
- [ ] Write a validation report (can be inline in the bead notes)

## Non-goals

- **ic binary distribution** — Intercore binary packaging is a separate concern (future bead)
- **Custom domain** — get.demarch.dev URL shortening is nice-to-have, not blocking
- **Video walkthrough** — text-first, video later
- **Autarch TUI onboarding** — separate UX concern
- **CI for install script** — future P0 (iv-be0ik covers CI broadly)
- **Installing prerequisites** — script checks, not installs. Too platform-specific.

## Dependencies

- Demarch repo must be publicly accessible (or at minimum install.sh + marketplace repo)
- Claude Code marketplace `add` command must work for external users
- `bd` (beads CLI) distribution needs a documented install path

## Open Questions

1. **Beads CLI distribution** — how does a stranger install `bd`? Is it `go install`, npm, or a pre-built binary? This blocks F2's beads init step.
2. **Marketplace access** — does `claude plugins marketplace add` require the marketplace repo to be public? Need to verify.
3. **Non-interactive setup** — can `/clavain:setup` run without user interaction (e.g., auto-accept recommended plugins)? If not, install.sh may need to replicate setup steps directly.
