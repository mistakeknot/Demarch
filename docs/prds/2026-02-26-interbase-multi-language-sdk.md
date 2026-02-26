# PRD: Interbase Multi-Language SDK

**Bead:** iv-jay06
**Date:** 2026-02-26
**Status:** strategized

## Problem

Demarch's plugin ecosystem spans three languages (Bash, Go, Python) but the shared SDK only covers Bash fully and Go partially. Go MCP servers reinvent capability detection and config loading. Python has no SDK at all. There is no formal contract ensuring consistent behavior across implementations.

## Solution

Formalize interbase as a spec-driven multi-language SDK where Bash, Go, and Python are equal peers. Each language gets a native implementation. Consistency is enforced by YAML conformance tests, not cross-language calls.

## Features

### F1: Interface Spec Document
**What:** Write a formal interface specification defining all SDK functions, their types, behaviors, error semantics, and fail-open guarantees.
**Acceptance criteria:**
- [ ] `sdk/interbase/spec/interbase-spec.md` exists with function-by-function definitions
- [ ] Each function specifies: signature per language, return type, fail-open behavior, side effects
- [ ] Spec covers all 4 domains: guards, actions, MCP contracts, config+discovery
- [ ] Open questions from brainstorm (interband depth, Python packaging, version coupling, Python hooks) are resolved with decisions

### F2: Go SDK — Guards + Actions + Config
**What:** Expand the Go SDK beyond toolerror/mcputil to include capability detection, phase tracking, event emission, and config loading.
**Acceptance criteria:**
- [ ] `sdk/interbase/go/interbase.go` exports: `HasIC`, `HasBD`, `HasCompanion`, `InEcosystem`, `GetBead`, `InSprint`
- [ ] `sdk/interbase/go/interbase.go` exports: `PhaseSet`, `EmitEvent`, `SessionStatus`
- [ ] `sdk/interbase/go/interbase.go` exports: `PluginCachePath`, `EcosystemRoot`, `NudgeCompanion`
- [ ] All guards return false when tools are missing (fail-open)
- [ ] All actions are silent no-ops when dependencies are absent
- [ ] Unit tests cover happy path and degraded mode for each function
- [ ] Existing `toolerror` and `mcputil` packages unchanged (no breaking changes)

### F3: Python SDK — Guards + Actions + Config
**What:** Create a new Python SDK package implementing the same guard, action, and config functions as Go and Bash.
**Acceptance criteria:**
- [ ] `sdk/interbase/python/interbase/` is a valid Python package (with `__init__.py`)
- [ ] Exports: `has_ic`, `has_bd`, `has_companion`, `in_ecosystem`, `get_bead`, `in_sprint`
- [ ] Exports: `phase_set`, `emit_event`, `session_status`
- [ ] Exports: `plugin_cache_path`, `ecosystem_root`, `nudge_companion`
- [ ] All guards return False when tools are missing (fail-open)
- [ ] All actions are silent no-ops when dependencies are absent
- [ ] Nudge protocol respects max 2/session and durable dismiss state
- [ ] `pyproject.toml` with `uv` as the build system
- [ ] Unit tests with pytest

### F4: Python MCP Contracts
**What:** Port `toolerror` and `mcputil` patterns to Python for use by Python MCP servers.
**Acceptance criteria:**
- [ ] `sdk/interbase/python/interbase/toolerror.py` — `ToolError` class with 6 error types, JSON wire format, `recoverable` flag
- [ ] `sdk/interbase/python/interbase/mcputil.py` — handler middleware with timing, error wrapping, metrics
- [ ] Wire format matches Go implementation exactly (same JSON keys, same type strings)
- [ ] Unit tests verify wire format parity with Go

### F5: YAML Conformance Test Suite
**What:** Define language-agnostic test cases in YAML with thin per-language test runners.
**Acceptance criteria:**
- [ ] `sdk/interbase/tests/conformance/guards.yaml` — test cases for all guard functions
- [ ] `sdk/interbase/tests/conformance/actions.yaml` — test cases for all action functions
- [ ] `sdk/interbase/tests/conformance/config.yaml` — test cases for config/discovery functions
- [ ] `sdk/interbase/tests/conformance/mcp.yaml` — test cases for error wire format
- [ ] `sdk/interbase/tests/runners/run_bash.sh` — Bash test runner
- [ ] `sdk/interbase/tests/runners/run_go.sh` — Go test runner (uses `go test`)
- [ ] `sdk/interbase/tests/runners/run_python.sh` — Python test runner (uses `pytest`)
- [ ] All three runners pass all applicable YAML test cases
- [ ] MCP tests run only for Go and Python (Bash excluded)

### F6: Expand Bash SDK Config Functions
**What:** Add `plugin_cache_path` and `ecosystem_root` functions to the existing Bash SDK, replacing hardcoded paths in consumers.
**Acceptance criteria:**
- [ ] `ib_plugin_cache_path PLUGIN` returns the cache path for a given plugin name
- [ ] `ib_ecosystem_root` returns the Demarch monorepo root or empty if not in ecosystem
- [ ] Existing Bash SDK functions unchanged (backward compatible)
- [ ] Stub updated to include no-op versions of new functions
- [ ] Existing 4 adopters continue to work without changes

### F7: First Adopter Migrations
**What:** Migrate at least one Go MCP server and one Python consumer to use the new SDK, validating the real-world ergonomics.
**Acceptance criteria:**
- [ ] One Go MCP server (intermap or interlock) imports `interbase` guards+config instead of ad-hoc detection
- [ ] One Python consumer (detect-domains.py or intermap bridge) imports `interbase` Python package
- [ ] Both consumers work in standalone mode (no ecosystem) and integrated mode
- [ ] Migration documented as a pattern for other plugins to follow

## Non-goals

- Replacing the Bash layer with Go/Python
- Creating a single binary that all languages call
- Supporting languages beyond Bash, Go, Python in v1
- Building a plugin framework (interbase is a library)
- Interband data access (typed SQLite wrappers) — deferred to a follow-up iteration

## Dependencies

- Existing Bash SDK (`sdk/interbase/lib/interbase.sh` v1.0.0)
- Existing Go packages (`sdk/interbase/go/toolerror/`, `sdk/interbase/go/mcputil/`)
- `mcp-go` v0.43.2 (Go MCP server library)
- Python 3.11+ with `uv` for package management
- `bd` and `ic` CLIs (for testing integrated mode)

## Open Questions (Resolved)

1. **Interband data access depth** → Deferred. Keep as separate concern for now. SDK stays focused on guards, actions, config, MCP.
2. **Python packaging** → Local path install via `uv` (editable install from monorepo). No PyPI for now.
3. **Version coupling** → Conformance tests gate releases. Implementations can lag as long as they pass the latest conformance suite.
4. **Hook authoring in Python** → Thin Bash wrapper calling `python3 -m interbase.hook`. Bash hook file sources interbase-stub.sh then delegates to Python.
