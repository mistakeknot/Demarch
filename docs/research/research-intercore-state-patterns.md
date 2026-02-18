# Research: Intercore State Management Patterns

**Date:** 2026-02-17
**Scope:** hub/clavain hooks, interphase plugin, infra/interband, and any existing intercore references

---

## 1. Existing `/tmp/clavain-*` Temp File Patterns

All temp files are written to `/tmp/` and keyed by `SESSION_ID` (UUID from `CLAUDE_SESSION_ID` env var) or PID (`$$`). They serve as inter-step communication and throttle sentinels.

### Currently Active Temp File Patterns

| Pattern | Purpose | Created By | Read By |
|---|---|---|---|
| `/tmp/clavain-stop-${SESSION_ID}` | Shared stop-hook sentinel — prevents cascade when one Stop hook fires | `auto-compound.sh`, `session-handoff.sh` | Both hooks (guard at top) |
| `/tmp/clavain-compound-last-${SESSION_ID}` | Throttle — at most once per 5 minutes | `auto-compound.sh` | `auto-compound.sh` |
| `/tmp/clavain-drift-last-${SESSION_ID}` | Throttle for drift check | `auto-drift-check.sh` | `auto-drift-check.sh` |
| `/tmp/clavain-handoff-${SESSION_ID}` | Once-per-session sentinel for handoff | `session-handoff.sh` | `session-handoff.sh` |
| `/tmp/clavain-dispatch-$$.json` | Live dispatch state for statusline (keyed by PID) | `scripts/dispatch.sh` | interline statusline renderer |
| `/tmp/clavain-bead-${SESSION_ID}.json` | Bead phase state for statusline (legacy path) | `interphase/hooks/lib-gates.sh` `_gate_update_statusline()` | interline statusline renderer |
| `/tmp/clavain-catalog-remind-${SESSION_ID}.lock` | Catalog reminder throttle | `catalog-reminder.sh` | `catalog-reminder.sh` |
| `/tmp/clavain-autopub.lock` | Auto-publish guard | `auto-publish.sh` | `auto-publish.sh` |
| `/tmp/clavain-discovery-brief-*.cache` | Discovery cache (session-keyed) | `lib-sprint.sh` `sprint_invalidate_caches()` | `lib-sprint.sh` |
| `/tmp/sprint-lock-${sprint_id}` | Mutex lock dir for sprint_set_artifact (PID-safe mkdir trick) | `lib-sprint.sh` | `lib-sprint.sh` |
| `/tmp/sprint-advance-lock-${sprint_id}` | Mutex lock dir for sprint_advance() | `lib-sprint.sh` | `lib-sprint.sh` |
| `/tmp/sprint-claim-lock-${sprint_id}` | Mutex lock dir for sprint_claim() | `lib-sprint.sh` | `lib-sprint.sh` |
| `/tmp/checkpoint-lock-*` | Mutex lock for checkpoint_write() | `lib-sprint.sh` | `lib-sprint.sh` |

### Key Code Locations

```
hub/clavain/hooks/auto-compound.sh     lines 48, 56   — STOP_SENTINEL, THROTTLE_SENTINEL
hub/clavain/hooks/session-handoff.sh   lines 35, 43   — STOP_SENTINEL, SENTINEL
hub/clavain/hooks/auto-drift-check.sh  lines ?        — clavain-stop, clavain-drift-last
hub/clavain/scripts/dispatch.sh        line 589        — STATE_FILE="/tmp/clavain-dispatch-$$.json"
plugins/interphase/hooks/lib-gates.sh  line 494        — _gate_update_statusline() → /tmp/clavain-bead-${session_id}.json
hub/clavain/hooks/lib-sprint.sh        line 880        — sprint_invalidate_caches() rm /tmp/clavain-discovery-brief-*.cache
```

### Notes on Shared Stop-Hook Sentinel
The pattern of a shared `/tmp/clavain-stop-${SESSION_ID}` was deliberately added (bead Clavain-8t5l) to prevent a compound-after-handoff loop. Both `auto-compound.sh` and `session-handoff.sh` write this sentinel at the top of their execution, and check it as a guard to prevent re-entry. The sentinel is cleaned up after 60 minutes via `find /tmp -name 'clavain-stop-*' -mmin +60 -delete`.

---

## 2. Existing `intercore` Module or Directory

**None found.** There is no `intercore` module, directory, plugin, or file in the Interverse monorepo. Searching confirmed zero results:

```bash
find /root/projects/Interverse -type d -name "intercore"  # No output
grep -r "intercore" /root/projects/Interverse/hub/clavain/ # No output
```

The namespace `intercore` is completely unclaimed.

---

## 3. How Hooks Read/Write State Between Steps

### Primary State Mechanisms (in order of precedence)

**A. Beads state fields (`bd set-state` / `bd state`)**
- Primary persistence for all lifecycle phases, sprint metadata, session claims
- Example: `bd set-state "$sprint_id" "phase=executing"` / `bd state "$sprint_id" phase`
- Used by: `lib-phase.sh`, `lib-sprint.sh`, `lib-gates.sh`
- Storage: `.beads/bd.db` SQLite (per-project)

**B. interband structured sideband protocol (`~/.interband/`)**
- JSON envelope files with schema version, namespace, type, session_id, timestamp, payload
- Atomic writes: mktemp + mv
- Used for: dispatch state (clavain:dispatch), bead phase (interphase:bead), coordination signals (interlock:coordination_signal)
- Channels observed in `~/.interband/`: `clavain/dispatch/`, `interphase/bead/`
- Library: `infra/interband/lib/interband.sh`
- Retention policy: clavain:dispatch = 6h, interphase:bead = 24h, default = 24h

**C. `/tmp/clavain-*.json` files (legacy sideband)**
- Flat JSON files for statusline consumption (legacy path kept for backward compat)
- `/tmp/clavain-dispatch-$$.json`: updated by dispatch.sh's awk JSONL parser in real time
- `/tmp/clavain-bead-${SESSION_ID}.json`: written by `_gate_update_statusline()` in interphase/lib-gates.sh
- These are the "legacy" channel; interband is the "preferred" channel
- Both are written on every update; interline reads interband first, falls back to legacy

**D. `.clavain/scratch/` directory (project-relative)**
- `inflight-agents.json`: manifest of background agents (written by `_write_inflight_manifest()` in lib.sh)
- `handoff-${TIMESTAMP}-${SESSION_SHORT}.md`: timestamped handoff files (written by session-handoff.sh)
- `handoff-latest.md`: symlink to newest handoff file
- Pruned to last 10 timestamped files

**E. `.clavain/checkpoint.json` (project-relative)**
- Sprint checkpoint: tracks current bead, phase, plan_path, git_sha, completed_steps, key_decisions
- Written by `checkpoint_write()` in `lib-sprint.sh`
- Protected by `/tmp/checkpoint-lock-*` mkdir mutex
- Cleared at sprint start or shipping via `checkpoint_clear()`

**F. `~/.clavain/telemetry.jsonl` (global append-only log)**
- All phase transitions, gate checks, enforcement decisions appended here
- Never blocked, never read back by hooks (observability only)
- Written by `_phase_log_transition()`, `_gate_log_check()`, `_gate_log_advance()`, `_gate_log_enforcement()`, `_gate_log_desync()`

---

## 4. What `lib-gates.sh` Uses for Phase Tracking Storage

`lib-gates.sh` in the interphase plugin (the real implementation, not the clavain shim) uses **dual persistence**:

### Primary: Beads state field
```bash
phase_set() {
    bd set-state "$bead_id" "phase=$phase"
}
phase_get() {
    bd state "$bead_id" phase
}
```
Reads/writes via `bd` CLI to `.beads/bd.db` SQLite.

### Secondary: Artifact file headers
```bash
_gate_write_artifact_phase() {
    # Inserts/updates "**Phase:** <value> (as of <timestamp>)" line
    # in files under docs/brainstorms/ and docs/plans/
}
_gate_read_artifact_phase() {
    grep '^\*\*Phase:\*\*' "$filepath" | head -1 | sed ...
}
```
Written to Markdown artifact files as `**Phase:** executing (as of 2026-02-17T...)`

### Desync detection
`phase_get_with_fallback()` reads both, warns if they disagree:
```
WARNING: phase desync for $bead_id — beads=$bead_phase, artifact=$artifact_phase
```

### Statusline sideband
`_gate_update_statusline()` also writes to:
1. `~/.interband/interphase/bead/${session_id}.json` (preferred)
2. `/tmp/clavain-bead-${session_id}.json` (legacy fallback)

---

## 5. What `lib-discovery.sh` Uses for State

The **clavain shim** at `hub/clavain/hooks/lib-discovery.sh` delegates to the real implementation in the interphase plugin:

```bash
# From hub/clavain/hooks/lib-discovery.sh (shim)
if [[ -n "$_BEADS_ROOT" && -f "${_BEADS_ROOT}/hooks/lib-discovery.sh" ]]; then
    source "${_BEADS_ROOT}/hooks/lib-discovery.sh"  # Real implementation
else
    # No-op stubs
    discovery_scan_beads() { echo "DISCOVERY_UNAVAILABLE"; }
    infer_bead_action() { echo "brainstorm|"; }
    discovery_log_selection() { return 0; }
fi
```

The real `plugins/interphase/hooks/lib-discovery.sh` scans the `.beads/` directory and reads `bd list --json` plus per-bead state via `bd state`. It outputs structured JSON to stdout for programmatic consumption by callers. Discovery caches are written to `/tmp/clavain-discovery-brief-*.cache` and invalidated by `sprint_invalidate_caches()`.

---

## 6. Existing SQLite Databases

Many SQLite databases exist in the project. All are `.db` files:

### Per-project `.beads/` databases (primary data store)
```
hub/clavain/.beads/bd.db        — Beads issue + state store
hub/clavain/.beads/beads.db     — Beads sync state
/root/projects/Interverse/.beads/beads.db
plugins/interkasten/.beads/bd.db + beads.db
plugins/tldr-swinton/.beads/bd.db + beads.db
services/intermute/.beads/bd.db + beads.db
... (most subprojects have .beads/bd.db)
```

### Per-project `.clavain/interspect/` databases
```
hub/clavain/.clavain/interspect/interspect.db    — Interspect session analytics
plugins/interflux/.clavain/interspect/interspect.db
plugins/interkasten/.clavain/interspect/interspect.db
plugins/interlock/.clavain/interspect/interspect.db
plugins/intermux/.clavain/interspect/interspect.db
plugins/interstat/.clavain/interspect/interspect.db
/root/projects/Interverse/.clavain/interspect/interspect.db
infra/marketplace/.clavain/interspect/interspect.db
```

### Plugin-specific databases
```
services/intermute/intermute.db         — Intermute multi-agent coordination store
plugins/tldr-swinton/.tldrs/tldrs_state.db  — tldr-swinton semantic index state
plugins/tldr-swinton/.tldrs/attention.db    — tldr-swinton attention analytics
plugins/tldr-swinton/.workbench/state.db    — tldr-swinton workbench state
hub/clavain/.tldrs/attention.db             — tldr attention for clavain
```

### beads.db vs bd.db distinction
- `bd.db`: Issue + state records (read/written by the `bd` CLI)
- `beads.db`: Sync metadata (used by beads remote sync machinery)

---

## 7. Language and Runtime

### Hooks and Libraries
**All Bash** (`#!/usr/bin/env bash`). The entire hooks infrastructure — lib.sh, lib-gates.sh, lib-phase.sh, lib-discovery.sh, lib-signals.sh, lib-sprint.sh, lib-verdict.sh, lib-interspect.sh, all hook scripts — is written in bash with `set -euo pipefail`.

**Key bash capabilities used:**
- `jq` for all JSON construction/parsing (external dependency, checked at top of each script)
- `awk` / `gawk` for JSONL stream parsing in dispatch.sh (live Codex event stream)
- `mkdir` as atomic mutex for concurrency control (POSIX atomic on Linux)
- `mktemp` + `mv` for atomic file writes

### Other components
- **infra/interband**: Pure bash library (`lib/interband.sh`) with a Go test file (`interband_test.go`) for protocol validation
- **services/intermute**: Go service (has `go.mod`, Go source files)
- **plugins (TypeScript/Node)**: interlock, intermap, intermux, interkasten, etc. — all Node.js/TypeScript MCP servers
- **plugins (Python)**: tldr-swinton uses Python (`.venv/`, `uv`)

### The `bd` CLI
Beads CLI (`bd`) is a compiled binary (Go) invoked by all the bash hooks. It reads/writes `.beads/bd.db`. This is the single authoritative state store for issue and phase data.

---

## 8. Architecture Summary

### State Layers (from most persistent to most ephemeral)

```
LAYER 1 — Permanent
  .beads/bd.db                    ← bd set-state / bd state (phase, sprint metadata, claims)
  docs/brainstorms/*.md           ← **Phase:** artifact headers (secondary)
  docs/plans/*.md                 ← **Phase:** artifact headers (secondary)

LAYER 2 — Session-persistent (cross-session)
  .clavain/checkpoint.json        ← Sprint resume state (current bead, phase, steps done)
  .clavain/scratch/handoff-*.md  ← Session handoff files (kept up to 10)
  ~/.clavain/telemetry.jsonl      ← Append-only phase/gate telemetry

LAYER 3 — Session-scoped (cleared at end / TTL)
  ~/.interband/clavain/dispatch/${PID}.json   ← Dispatch progress (6h TTL)
  ~/.interband/interphase/bead/${SID}.json    ← Bead phase for statusline (24h TTL)
  /tmp/clavain-bead-${SID}.json               ← Legacy bead phase sideband

LAYER 4 — Ephemeral (runtime only)
  /tmp/clavain-dispatch-$$.json               ← Live dispatch state (deleted on EXIT)
  /tmp/clavain-stop-${SID}                    ← Stop hook sentinel (60min TTL)
  /tmp/clavain-compound-last-${SID}           ← Compound throttle (60min TTL)
  /tmp/clavain-drift-last-${SID}              ← Drift throttle
  /tmp/clavain-handoff-${SID}                 ← Handoff once-per-session guard
  /tmp/clavain-discovery-brief-*.cache        ← Discovery cache (invalidated on phase change)
  /tmp/sprint-lock-${sprint_id}/              ← Mutex (rmdir on release)
  /tmp/sprint-advance-lock-${sprint_id}/      ← Mutex
  /tmp/sprint-claim-lock-${sprint_id}/        ← Mutex
  /tmp/checkpoint-lock-*/                     ← Mutex
  .clavain/scratch/inflight-agents.json       ← In-flight agent manifest (runtime)
```

### Key Design Patterns

1. **Fail-safe by convention**: All hook functions return 0 on error, never block workflow. `set -euo pipefail` is set but every bd/jq call has `|| true` fallback.

2. **Atomic writes everywhere**: `mktemp + mv` for files, `mkdir` for mutexes. No direct write-in-place.

3. **Dual persistence for phase**: Primary in beads (permanent), secondary in artifact file headers (readable by humans/git). Desync detection warns but doesn't block.

4. **Shim delegation pattern**: Clavain's hook libs are thin shims that delegate to installed interphase/interflux plugins. Falls back to no-op stubs if plugins not installed.

5. **Interband as preferred channel**: `/tmp/clavain-bead-${SID}.json` is "legacy", `~/.interband/interphase/bead/${SID}.json` is "preferred". Both written simultaneously, consumers fall back from preferred to legacy.

6. **Plugin discovery via filesystem**: lib.sh `_discover_beads_plugin()` finds interphase by scanning `~/.claude/plugins/cache/*/interphase/*/hooks/lib-gates.sh` — no registry, no MCP.

---

## Files Examined

```
hub/clavain/hooks/lib.sh
hub/clavain/hooks/lib-gates.sh            (shim → interphase)
hub/clavain/hooks/lib-discovery.sh        (shim → interphase)
hub/clavain/hooks/lib-signals.sh
hub/clavain/hooks/lib-sprint.sh
hub/clavain/hooks/auto-compound.sh
hub/clavain/hooks/session-handoff.sh
hub/clavain/scripts/dispatch.sh
plugins/interphase/hooks/lib-gates.sh     (real implementation)
plugins/interphase/hooks/lib-phase.sh     (real implementation)
infra/interband/lib/interband.sh
hub/clavain/tests/shell/dispatch_parser.bats
hub/clavain/tests/shell/auto_compound.bats
hub/clavain/tests/shell/auto_drift_check.bats
hub/clavain/tests/shell/test_lib_sprint.bats
hub/clavain/.beads/issues.jsonl           (for historical context on Clavain-8t5l, Clavain-oijz)
```
