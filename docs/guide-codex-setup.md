# Codex CLI Setup Guide

**Time:** 10 minutes

**Prerequisites:**
- [Codex CLI](https://openai.com/index/codex/) installed
- Git

## Quick Install

If you already ran the main Demarch installer (`install.sh`), Codex skills were installed automatically. Verify with:

```bash
ls ~/.agents/skills/
```

Expected: `clavain`, `interdoc`, `tool-time`, `tldrs-agent-workflow`

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

This adds three companion skills to `~/.agents/skills/`:
- **interdoc** — AGENTS.md generator
- **tool-time** — token usage analytics (Codex variant)
- **tldrs-agent-workflow** — agent workflow helper

Restart Codex after installation.

## How It Works

Codex discovers skills via **`~/.agents/skills/`** — each subdirectory containing a `SKILL.md` is loaded at startup.

The installer creates symlinks (not copies), so skills update automatically when you pull:

```
~/.agents/skills/clavain           → ~/.codex/clavain/skills
~/.agents/skills/interdoc          → ~/.codex/interdoc/skills/interdoc
~/.agents/skills/tool-time         → ~/.codex/tool-time/skills/tool-time-codex
~/.agents/skills/tldrs-agent-workflow → ~/.codex/tldr-swinton/.codex/skills/tldrs-agent-workflow
```

Clavain commands are also available as prompt wrappers in `~/.codex/prompts/clavain-*.md`.

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
rm -rf ~/.codex/clavain ~/.codex/interdoc ~/.codex/tool-time ~/.codex/tldr-swinton
```

## Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| Skills not loaded after install | Codex not restarted | Quit and relaunch Codex CLI |
| `~/.agents/skills/` missing | Directory not created | `mkdir -p ~/.agents/skills` and re-run installer |
| Link points to wrong target | Stale symlink from old install | Delete the symlink and re-run installer |
| Companion repo clone fails | Network or auth issue | Check `git clone` manually: `git clone https://github.com/mistakeknot/interdoc.git ~/.codex/interdoc` |
| `install-codex-interverse.sh` not found | Cached Clavain is outdated | Run `agent-install.sh --update` to pull latest |
