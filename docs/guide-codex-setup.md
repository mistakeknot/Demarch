# Codex CLI Setup Guide

**Time:** 10 minutes

**Prerequisites:**
- [Codex CLI](https://openai.com/index/codex/) installed
- Git

## Quick Install

If you already ran the main Demarch installer (`install.sh`), Codex skills were installed automatically. Verify with:

```bash
find ~/.agents/skills -mindepth 1 -maxdepth 1 -type l -printf '%f\n' | sort
```

Expected: `clavain` plus the current set of companion skills discovered from recommended Interverse plugins.

A healthy install typically includes links such as:
`agent-native-architecture`, `artifact-gen`, `beads-workflow`, `coordination-protocol`, `doc-watch`, `flux-drive`, `interdoc`, `intermap`, `interpeer`, `mcp-cli`, `memory-synthesis`, `memory-tidy`, `next-work`, `status`, `systematic-debugging`, `test-driven-development`, `tldrs-agent-workflow`, `tool-time`, `verification-before-completion`, and `working-with-claude-code`.

For the exact source of truth, run:

```bash
bash ~/.codex/clavain/scripts/install-codex-interverse.sh doctor
```

If any are missing, run:

```bash
bash os/clavain/scripts/install-codex-interverse.sh install
```

## Fresh Install (standalone)

If you only use Codex (no Claude Code), install Clavain skills directly:

```bash
curl -fsSL https://raw.githubusercontent.com/mistakeknot/Clavain/main/.codex/agent-install.sh | bash -s -- --update --json
```

This clones Clavain into `~/.codex/clavain` and links `~/.agents/skills/clavain`.

Then install companion skills:

```bash
bash ~/.codex/clavain/scripts/install-codex-interverse.sh install
```

This reconciles the full Codex companion ecosystem:
- Updates or clones all recommended Interverse repos declared in `os/clavain/agent-rig.json`
- Links every companion skill discovered under `skills/**/SKILL.md` with valid frontmatter
- Generates Clavain prompt wrappers in `~/.codex/prompts/clavain-*.md`
- Generates companion prompt wrappers in `~/.codex/prompts/<plugin>-<command>.md`
- Rewrites Clavain prompt references so companion commands route through those generated prompts

Restart Codex after installation.

## How It Works

Codex discovers skills via **`~/.agents/skills/`** — each linked subdirectory containing a `SKILL.md` is loaded at startup.

The installer creates symlinks (not copies), so skills update automatically when the linked repo updates. Example links:

```
~/.agents/skills/clavain                → ~/.codex/clavain/skills
~/.agents/skills/flux-drive             → ~/.codex/interflux/skills/flux-drive
~/.agents/skills/flux-research          → ~/.codex/interflux/skills/flux-research
~/.agents/skills/interdoc               → ~/.codex/interdoc/skills/interdoc
~/.agents/skills/intermap               → ~/.codex/intermap/skills
~/.agents/skills/interpeer              → ~/.codex/interpeer/skills/interpeer
~/.agents/skills/memory-synthesis       → ~/.codex/intermem/skills/synthesize
~/.agents/skills/memory-tidy            → ~/.codex/intermem/skills/tidy
~/.agents/skills/next-work              → ~/.codex/internext/skills/next-work
~/.agents/skills/tool-time              → ~/.codex/tool-time/skills/tool-time-codex
~/.agents/skills/tldrs-agent-workflow   → ~/.codex/tldr-swinton/.codex/skills/tldrs-agent-workflow
```

The exact companion set is intentionally dynamic: it follows the current recommended plugin list in `agent-rig.json` and the skills each repo exposes via `SKILL.md` frontmatter.

Clavain commands are also available as prompt wrappers in `~/.codex/prompts/clavain-*.md`, and companion commands are generated as `~/.codex/prompts/<plugin>-<command>.md`.

## Verify

```bash
bash ~/.codex/clavain/scripts/install-codex-interverse.sh doctor
```

For machine-readable output:

```bash
bash ~/.codex/clavain/scripts/install-codex-interverse.sh doctor --json
```

## Update

```bash
bash ~/.codex/clavain/.codex/agent-install.sh --update
bash ~/.codex/clavain/scripts/install-codex-interverse.sh install
```

Restart Codex after updating.

## Migrating from Legacy Patterns

If you previously used **superpowers**, **compound-engineering**, or the old `~/.codex/skills/*` bootstrap:

1. Run the ecosystem installer — it automatically cleans up legacy artifacts:
   ```bash
   bash ~/.codex/clavain/scripts/install-codex-interverse.sh install
   ```
   This removes:
   - Superpowers prompt wrappers from `~/.codex/prompts/`
   - Legacy skill symlinks from `~/.codex/skills/`
   - Warns about the superpowers clone directory (`~/.codex/superpowers/`)

2. Remove any old bootstrap block in `~/.codex/AGENTS.md` that references `superpowers-codex bootstrap` or legacy Codex bootstrap commands.

3. Optionally remove the superpowers clone:
   ```bash
   rm -rf ~/.codex/superpowers
   ```

4. For Claude Code users: the root `install.sh` also removes the `superpowers-marketplace` and `every-marketplace` from Claude Code's known marketplaces.

5. Verify `~/.agents/skills/*` links exist and restart Codex.

The new path (`~/.agents/skills/`) is Codex's native discovery mechanism. The old path (`~/.codex/skills/`) still works if you set `CLAVAIN_LEGACY_SKILLS_LINK=1`, but is deprecated.

## Uninstall

```bash
bash ~/.codex/clavain/scripts/install-codex-interverse.sh uninstall
bash ~/.codex/clavain/scripts/install-codex.sh uninstall
```

Optionally remove the clone:

```bash
rm -rf ~/.codex/clavain
# Optional: also remove companion clones managed under ~/.codex/
# Examples: ~/.codex/interdoc ~/.codex/interflux ~/.codex/intermap ~/.codex/intermem
```

## Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| Skills not loaded after install | Codex not restarted | Quit and relaunch Codex CLI |
| `~/.agents/skills/` missing | Directory not created | `mkdir -p ~/.agents/skills` and re-run installer |
| Link points to wrong target | Stale symlink from old install | Delete the symlink and re-run installer |
| Companion repo clone fails | Network or auth issue | Check `git clone` manually: `git clone https://github.com/mistakeknot/interdoc.git ~/.codex/interdoc` |
| Doctor warns about a companion skill missing frontmatter `name` | The companion repo has an invalid `SKILL.md` header | Update the repo, then re-run `install-codex-interverse.sh install` |
| `install-codex-interverse.sh` not found | Cached Clavain is outdated | Run `agent-install.sh --update` to pull latest |
