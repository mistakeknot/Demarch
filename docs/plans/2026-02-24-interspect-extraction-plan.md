# Interspect Extraction Plan

**Bead:** iv-88cp2
**Brainstorm:** docs/brainstorms/2026-02-24-interspect-extraction-brainstorm.md

## Phase 1: Plugin Scaffold + Hooks + Library

### Task 1.1: Create plugin scaffold
- [x] Create `interverse/interspect/` directory structure:
  ```
  interspect/
  ├── .claude-plugin/plugin.json
  ├── .git (init)
  ├── hooks/
  │   └── hooks.json
  ├── commands/
  ├── config/defaults/
  ├── CLAUDE.md
  └── LICENSE
  ```
- [x] Write `plugin.json` manifest (name: interspect, version: 0.1.0)
- [x] Write `hooks.json` with 3 hook bindings (SessionStart, PostToolUse:Task, Stop)

### Task 1.2: Move hook scripts and library
- [x] Copy `os/clavain/hooks/lib-interspect.sh` → `interverse/interspect/hooks/lib-interspect.sh`
- [x] Copy `os/clavain/hooks/interspect-session.sh` → `interverse/interspect/hooks/interspect-session.sh`
- [x] Copy `os/clavain/hooks/interspect-evidence.sh` → `interverse/interspect/hooks/interspect-evidence.sh`
- [x] Copy `os/clavain/hooks/interspect-session-end.sh` → `interverse/interspect/hooks/interspect-session-end.sh`
- [x] Update `source` paths in the 3 hook scripts to reference `lib-interspect.sh` relative to the new plugin root (not Clavain's `$SCRIPT_DIR`)

### Task 1.3: Update state paths in lib-interspect.sh
- [x] Change `.clavain/interspect/` references to `.interspect/`
- [x] Change `.claude/routing-overrides.json` to `.interspect/routing-overrides.json`
- [x] Add migration function `_interspect_migrate_state()` that:
  1. Checks if `.clavain/interspect/` exists and `.interspect/` does not
  2. Moves the directory: `mv .clavain/interspect .interspect`
  3. Creates symlink: `ln -s ../../.interspect .clavain/interspect`
  4. Moves routing overrides if they exist at old location
- [x] Call migration from `_interspect_ensure_db()` (runs on first use)

### Task 1.4: Remove interspect hooks from Clavain
- [x] Remove 3 interspect entries from `os/clavain/hooks/hooks.json`
- [x] Delete `os/clavain/hooks/interspect-session.sh`
- [x] Delete `os/clavain/hooks/interspect-evidence.sh`
- [x] Delete `os/clavain/hooks/interspect-session-end.sh`
- [x] Delete `os/clavain/hooks/lib-interspect.sh`
- [x] Update `os/clavain/CLAUDE.md` to remove interspect syntax check lines

### Task 1.5: Add companion discovery for interspect
- [x] Add `_discover_interspect_plugin()` to `os/clavain/hooks/lib.sh` (add to batch find pattern)
- [x] Update `_discover_all_companions()` to include interspect pattern

### Task 1.6: Verify Phase 1
- [x] `bash -n` all new hook scripts
- [x] `python3 -c "import json; json.load(open(...))"` on both plugin.json and hooks.json
- [x] Source lib-interspect.sh and verify `_interspect_ensure_db` creates `.interspect/`
- [x] Verify Clavain's hooks.json no longer references interspect scripts
- [x] Commit Phase 1

## Phase 2: Move Commands

### Task 2.1: Move command files
- [x] Copy all 12 `os/clavain/commands/interspect*.md` → `interverse/interspect/commands/`
- [x] Update any `${CLAUDE_PLUGIN_ROOT}` references in command files to point to interspect plugin root
- [x] Remove 12 interspect command files from `os/clavain/commands/`

### Task 2.2: Update Clavain plugin.json
- [x] Remove 12 interspect commands from Clavain's `plugin.json` commands list
- [x] Add interspect commands to `interverse/interspect/.claude-plugin/plugin.json`

### Task 2.3: Add command aliases in Clavain (transition period)
- [x] Add a note in Clavain's CLAUDE.md that `/clavain:interspect*` commands have moved to `/interspect:*`
- [x] Commit Phase 2

## Phase 3: Cleanup and Polish

### Task 3.1: Write CLAUDE.md and AGENTS.md for interspect plugin
- [x] CLAUDE.md: overview, quick commands, design decisions
- [x] Include syntax check commands for all hook scripts

### Task 3.2: Extract default configs
- [x] Write `config/defaults/confidence.json` with default thresholds
- [x] Write `config/defaults/protected-paths.json` with empty defaults
- [x] Update lib-interspect.sh to copy defaults on first init if no user config exists

### Task 3.3: Final cleanup
- [x] Remove any dead interspect references from remaining Clavain files
- [x] Update Demarch root CLAUDE.md to add interspect to the interverse listing
- [x] `git init` in interspect dir, initial commit
- [x] Commit Phase 3 in Clavain (removal of dead references)

## Files Changed

### Clavain (os/clavain/)
- `hooks/hooks.json` — remove 3 interspect bindings
- `hooks/lib.sh` — add interspect to batch companion discovery
- `hooks/lib-interspect.sh` — **deleted** (moved)
- `hooks/interspect-session.sh` — **deleted** (moved)
- `hooks/interspect-evidence.sh` — **deleted** (moved)
- `hooks/interspect-session-end.sh` — **deleted** (moved)
- `commands/interspect*.md` (12 files) — **deleted** (moved)
- `CLAUDE.md` — remove interspect syntax checks
- `.claude-plugin/plugin.json` — remove interspect commands

### Interspect (interverse/interspect/) — **new**
- `.claude-plugin/plugin.json` — manifest
- `hooks/hooks.json` — 3 hook bindings
- `hooks/lib-interspect.sh` — core library (2661 lines)
- `hooks/interspect-session.sh` — SessionStart hook
- `hooks/interspect-evidence.sh` — PostToolUse hook
- `hooks/interspect-session-end.sh` — Stop hook
- `commands/interspect*.md` (12 files)
- `config/defaults/confidence.json`
- `config/defaults/protected-paths.json`
- `CLAUDE.md`

### Demarch root
- `CLAUDE.md` — add interspect to interverse listing
