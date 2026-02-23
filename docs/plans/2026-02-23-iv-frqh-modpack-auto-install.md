# Plan: Modpack Auto-Install in clavain:setup

**Bead:** iv-frqh
**Phase:** executing (as of 2026-02-23T16:43:50Z)
**Date:** 2026-02-23
**Complexity:** 2/5 (simple)

## Problem

`clavain:setup` is a declarative command — it lists `claude plugin install` commands for the user to run manually. There's no automation: users copy-paste 20+ install commands one by one. The `agent-rig.json` manifest already categorizes plugins into core/required/recommended/optional, but setup.md doesn't leverage this programmatically.

The goal: when a user runs `/clavain:setup`, automatically install required + recommended plugins, confirm optional ones, and disable conflicts — all driven from `agent-rig.json` as the single source of truth.

## Design

### Approach: Shell script driven by agent-rig.json

Add a `scripts/modpack-install.sh` script to Clavain that:
1. Reads `agent-rig.json` to get plugin lists by category
2. Detects already-installed plugins (checks `~/.claude/plugins/cache/<marketplace>/<name>/`)
3. Installs missing required + recommended plugins automatically
4. Presents optional plugins via stdout for the setup command to use with AskUserQuestion
5. Disables conflicting plugins
6. Returns a JSON summary of what was installed/skipped/failed

### Why a script (not inline in setup.md)?

- setup.md is a skill — it's declarative instructions, not executable code
- A script can be tested, versioned, and called from both setup.md and programmatically
- The script reads agent-rig.json at runtime, so setup.md's inline lists become self-healing automatically

## Tasks

### Task 1: Create `scripts/modpack-install.sh` [DONE]

**File:** `os/clavain/scripts/modpack-install.sh`

Shell script that:
- Parses `agent-rig.json` using `jq` (already available on the system)
- Accepts flags: `--dry-run`, `--category=required|recommended|optional|all`, `--quiet`
- For each plugin in the category:
  - Check if already installed: `ls ~/.claude/plugins/cache/*/<name>/*/plugin.json 2>/dev/null`
  - If missing: `claude plugin install <source>`
  - Track results: installed, already-present, failed
- For conflicts: `claude plugin disable <source>` (skip if already disabled)
- Output JSON summary to stdout:
  ```json
  {
    "installed": ["interflux@interagency-marketplace", ...],
    "already_present": ["clavain@interagency-marketplace", ...],
    "failed": [],
    "disabled": ["code-review@claude-plugins-official", ...],
    "optional_available": ["interfluence@interagency-marketplace", ...]
  }
  ```

### Task 2: Update `commands/setup.md` to use the script [DONE]

Replace the manual install lists in Steps 2, 2b, and 3 with:

1. **Step 2 (required + recommended):** Run `scripts/modpack-install.sh --category=required` then `--category=recommended`. Report what was installed vs already present.

2. **Step 2b (optional):** Run `scripts/modpack-install.sh --dry-run --category=optional` to get the list of not-yet-installed optional plugins. Present via AskUserQuestion (multi-select). Install selected ones.

3. **Step 3 (conflicts):** Already handled by the script — conflicts are disabled during the required/recommended install pass. Just report results.

Keep the `<!-- agent-rig:begin/end -->` markers and inline lists as **fallback documentation** — if jq isn't available or the script fails, the setup command can still guide manual installation.

### Task 3: Add `--check-only` mode to the script [DONE]

When `--check-only` is passed:
- Don't install anything
- Output the same JSON summary but with `would_install` instead of `installed`
- This supports the existing `--check-only` flag in setup.md

## Files Changed

| File | Change |
|------|--------|
| `os/clavain/scripts/modpack-install.sh` | **New** — core install automation script |
| `os/clavain/commands/setup.md` | **Edit** — wire Steps 2/2b/3 to use the script |

## Non-Goals

- No changes to `agent-rig.json` schema — it already has the right structure
- No changes to `integration.json` or interbase SDK — ecosystem_only is a future concern
- No auto-install on session start — this is explicit `/clavain:setup` only
- No language server auto-detection — infrastructure plugins stay user-chosen

## Testing

- `bash -n scripts/modpack-install.sh` — syntax check
- `scripts/modpack-install.sh --dry-run --category=required` — verify detection logic
- `scripts/modpack-install.sh --check-only` — verify check-only mode
- Run `/clavain:setup` end-to-end in a test session
