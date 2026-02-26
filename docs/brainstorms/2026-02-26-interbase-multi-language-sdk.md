# Brainstorm: Formalize Interbase as a Multi-Language SDK

**Bead:** iv-jay06
**Date:** 2026-02-26
**Status:** brainstorm
**Complexity:** 4/5 (complex)

## Problem Statement

Interbase is the shared integration SDK for Demarch's plugin ecosystem. Today it exists as:
- A **154-line Bash library** (`lib/interbase.sh`) with a 30-line stub shipped per plugin
- **Go packages** (`toolerror` + `mcputil`) for MCP server error contracts and middleware
- **No Python bindings** at all

This creates three pain points:
1. **Go MCP servers reinvent the wheel** — interlock, intermap, intermux, tuivision all need capability detection, config loading, and phase tracking but have no shared SDK for it
2. **Python is a second-class citizen** — detect-domains.py, intermap's Python bridge, and future Python hooks can't call `ib_has_ic()` or `ib_phase_set()`
3. **Ecosystem fragmentation** — three languages doing the same things differently, with no contract ensuring consistent behavior

## Current State

### Bash SDK (4 adopters: interflux, interline, intermem, intersynth)
- **Guards (fail-open):** `ib_has_ic`, `ib_has_bd`, `ib_has_companion`, `ib_in_ecosystem`, `ib_get_bead`, `ib_in_sprint`
- **Actions (no-op without deps):** `ib_phase_set`, `ib_emit_event`, `ib_session_status`
- **Discovery:** `ib_nudge_companion` (max 2/session, durable dismiss state)
- **Shared DB:** `interkasten-db.sh` — SQLite accessors for project hierarchy

### Go SDK (toolerror + mcputil, used by interlock)
- **toolerror:** Structured error contract (6 error types, JSON wire format, recoverable flag)
- **mcputil:** Handler middleware with metrics, error wrapping, panic recovery

### Python SDK
- Does not exist.

## Vision

**Interbase becomes a formally specified multi-language SDK** where Bash, Go, and Python are equal peers, all implementing the same interface contract.

### Architecture: Shared Spec, Native Implementations

```
sdk/interbase/
  spec/              ← Interface contract (types, behaviors, YAML test cases)
  lib/               ← Bash implementation (existing, expanded)
  go/                ← Go implementation (existing + new packages)
  python/            ← Python implementation (new)
  tests/
    conformance/     ← Language-agnostic YAML test cases
    runners/         ← Per-language test runners (~50 lines each)
```

**Key principle:** No cross-language calls. Each language gets a native, ergonomic implementation. Consistency is enforced by conformance tests, not by runtime dependencies.

### SDK Contract — Four Domains

#### 1. Guards (Capability Detection)
Fail-open functions that detect ecosystem tools and companions.

| Function | Bash | Go | Python |
|----------|------|-----|--------|
| `has_ic` | `ib_has_ic` | `interbase.HasIC()` | `interbase.has_ic()` |
| `has_bd` | `ib_has_bd` | `interbase.HasBD()` | `interbase.has_bd()` |
| `has_companion` | `ib_has_companion NAME` | `interbase.HasCompanion(name)` | `interbase.has_companion(name)` |
| `in_ecosystem` | `ib_in_ecosystem` | `interbase.InEcosystem()` | `interbase.in_ecosystem()` |
| `get_bead` | `ib_get_bead` | `interbase.GetBead()` | `interbase.get_bead()` |
| `in_sprint` | `ib_in_sprint` | `interbase.InSprint()` | `interbase.in_sprint()` |

**Behavior:** All guards return false/empty when the capability is missing. Never error. Never block.

#### 2. Actions (Phase Tracking + Events)
Side-effecting functions that are no-ops when dependencies are missing.

| Function | Bash | Go | Python |
|----------|------|-----|--------|
| `phase_set` | `ib_phase_set BEAD PHASE [REASON]` | `interbase.PhaseSet(bead, phase, ...reason)` | `interbase.phase_set(bead, phase, reason=None)` |
| `emit_event` | `ib_emit_event RUN TYPE [PAYLOAD]` | `interbase.EmitEvent(run, typ, ...payload)` | `interbase.emit_event(run, typ, payload=None)` |
| `session_status` | `ib_session_status` | `interbase.SessionStatus()` | `interbase.session_status()` |

**Behavior:** Functions succeed silently when `bd`/`ic` are unavailable. Errors from underlying tools are logged to stderr but never propagated.

#### 3. MCP Contracts (Go + Python)
Structured error types and handler middleware for MCP servers.

**Error types (6):** NOT_FOUND, CONFLICT, VALIDATION, PERMISSION, TRANSIENT, INTERNAL
**Wire format:** `{"type": "...", "message": "...", "recoverable": bool, "data": {}}`
**Middleware:** Timing, error wrapping, panic recovery, metrics collection

Go already has this (`toolerror` + `mcputil`). Python gets equivalent packages.

Bash does not need MCP contracts (hooks don't run MCP servers).

#### 4. Config + Discovery
Shared configuration loading and ecosystem path resolution.

| Function | Bash | Go | Python |
|----------|------|-----|--------|
| `plugin_cache_path` | (hardcoded today) | `interbase.PluginCachePath(plugin)` | `interbase.plugin_cache_path(plugin)` |
| `ecosystem_root` | (hardcoded today) | `interbase.EcosystemRoot()` | `interbase.ecosystem_root()` |
| `nudge_companion` | `ib_nudge_companion` | `interbase.NudgeCompanion(...)` | `interbase.nudge_companion(...)` |

**Behavior:** Path functions return best-effort results. Nudge protocol respects max 2/session and durable dismiss state.

### Conformance Testing: YAML Test Cases

```yaml
# tests/conformance/guards.yaml
tests:
  - name: has_ic_when_present
    setup:
      PATH: includes ic binary
    call: has_ic
    expect: true

  - name: has_ic_when_missing
    setup:
      PATH: excludes ic binary
    call: has_ic
    expect: false

  - name: phase_set_without_bd
    setup:
      PATH: excludes bd binary
    call: phase_set
    args: ["bead-123", "planned"]
    expect_error: false  # fail-open
    expect_side_effect: none

  - name: nudge_budget_exhausted
    setup:
      nudge_count: 2
    call: nudge_companion
    args: ["intercheck", "context pressure"]
    expect_side_effect: none  # budget exhausted, silent no-op
```

Each language has a thin test runner (~50 lines) that:
1. Reads YAML test cases
2. Sets up environment per `setup` block
3. Calls the native function
4. Asserts expected result and side effects

### Consumers

**Bash adopters (existing 4 + expand):** interflux, interline, intermem, intersynth → all other hook-based plugins
**Go adopters (new):** interlock, intermap, intermux, tuivision, intersearch, interserve — all Go MCP servers
**Python adopters (new):** intermap bridge, detect-domains.py, future Python hooks, future Python MCP servers

### Stub Pattern (Preserved)

The existing stub pattern is preserved — each plugin ships a 30-line Bash stub that falls back to inline no-ops. This ensures standalone mode (no ecosystem) continues to work with zero dependencies.

For Go and Python: the SDK is an optional import. If not available, MCP servers degrade to flat error strings and no metrics. Guard functions return false (assume nothing available).

## Open Questions

1. **Interband data access depth** — Should the SDK expose typed SQLite accessors (like `interkasten-db.sh`) in Go and Python, or keep that as a separate concern?
2. **Python packaging** — Should the Python SDK be a PyPI package, a local path install via `uv`, or a vendored copy in each plugin?
3. **Version coupling** — When the spec changes, do all three implementations need to update atomically, or can they lag independently (with conformance tests gating releases)?
4. **Hook authoring in Python** — Claude Code hooks are Bash-invoked. How does a Python hook get called? Thin Bash wrapper that calls `python3 -m interbase.hook`?

## Risks

| Risk | Mitigation |
|------|------------|
| Triple maintenance burden | Conformance tests catch drift at PR time |
| Go/Python SDK unused (YAGNI) | Start with consumers that exist today (intermap, interlock) |
| Python runtime dependency | Python SDK is optional — fail-open like Bash |
| Spec becomes bottleneck | Keep spec minimal — add functions only when 2+ consumers need them |

## Non-Goals

- Replacing the Bash layer with Go/Python (Bash stays for hooks)
- Creating a single binary that all languages call (rejected in architecture decision)
- Supporting languages beyond Bash, Go, Python in v1
- Building a plugin framework (interbase is a library, not a framework)

## Success Criteria

1. All three language SDKs pass the same conformance test suite
2. At least 2 Go MCP servers adopt the Go SDK guards + config
3. At least 1 Python consumer uses the Python SDK
4. The spec document is the authoritative reference (not any single implementation)
5. Existing Bash adopters see zero breaking changes
