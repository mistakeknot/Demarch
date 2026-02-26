# Gemini CLI Setup Guide

**Time:** 5 minutes

**Prerequisites:**
- [Gemini CLI](https://github.com/google/gemini-cli) installed (`npm install -g @google/gemini-cli`)
- Git

## Fresh Install

Since Gemini CLI uses specialized `SKILL.md` instructions dynamically generated from the Interverse plugins, you should clone the `Demarch` monorepo to your machine. This gives you a permanent location to sync upstream changes and generate skills from.

1. **Clone the Demarch Repository**
   Choose a stable location (e.g., `~/projects` or `~/.gemini/demarch`):
   ```bash
   git clone --recursive https://github.com/mistakeknot/Demarch.git ~/.local/share/Demarch
   cd ~/.local/share/Demarch
   ```

2. **Run the Gemini Installer**
   This script will compile the phase documents into Gemini skills and link them globally:
   ```bash
   bash scripts/install-gemini-interverse.sh install
   ```

This generates all the required `SKILL.md` files locally and registers the directory (`~/.local/share/Demarch/.gemini/skills`) to your global `~/.gemini/skills` directory so you can invoke them via `gemini` in any project workspace.

## Verify

Check that the skills are linked in the global scope:

```bash
gemini skills list --all
```

You should see `clavain`, `interdoc`, `tool-time`, `interflux`, and the rest of the Interverse companion skills in the list.

## Update

When new features or upstream skills are added, pull the changes and re-run the installer to sync and re-generate your `SKILL.md` files.

```bash
cd ~/.local/share/Demarch
git pull
git submodule update --init --recursive
bash scripts/install-gemini-interverse.sh install
```

## Uninstall

If you ever wish to remove the Gemini skills globally:

```bash
cd ~/.local/share/Demarch
bash scripts/install-gemini-interverse.sh uninstall
```

Then you may safely remove the `Demarch` clone directory.

## Working with Clavain in Gemini CLI

Gemini CLI works directly with standard Bash commands via `run_command` tools and doesn't rely on Claude Code slash commands like `/clavain:route`.

To use your installed skills, you can use the built-in global `activate_skill` tool or let the Gemini CLI autonomously utilize them depending on the task context. 
