# interdoc: interbase AGENTS.md Refresh

> Research analysis for updating `/home/mk/projects/Demarch/sdk/interbase/AGENTS.md`
> Date: 2026-02-25

## Task Context

Interbase is described in the Demarch root CLAUDE.md as "shared integration SDK for dual-mode plugins." The task prompt described it as a TypeScript/Node package, but this is **incorrect** -- interbase is a **Bash + Go** SDK with no TypeScript, no `package.json`, and no `tsconfig.json`.

## Repo Structure (Actual)

```
sdk/interbase/
  lib/
    interbase.sh        -- core Bash SDK (154 lines)
    VERSION             -- "1.0.0"
  templates/
    interbase-stub.sh   -- shipped inside each plugin (30 lines)
    integration.json    -- schema template for plugin integration manifests
  tests/
    test-guards.sh      -- 16 assertions
    test-nudge.sh       -- 4 assertions
  go/
    go.mod              -- module: github.com/mistakeknot/interbase, Go 1.23, mcp-go v0.43.2
    toolerror/
      toolerror.go      -- structured error contract (92 lines)
      toolerror_test.go -- 9 tests
    mcputil/
      instrument.go     -- middleware + convenience helpers (167 lines)
      instrument_test.go -- 8 tests
    README.md           -- Go SDK standalone README
  scripts/
    validate-gitleaks-waivers.sh  -- secret-scan baseline enforcement
  docs/
    interbase-vision.md -- strategic vision
    roadmap.md          -- auto-generated from beads
    vision.md           -- symlink to interbase-vision.md
  install.sh            -- deploy Bash SDK to ~/.intermod/interbase/
  .github/workflows/    -- CI (secret-scan)
  .gitleaks.toml        -- secret scanning config
  README.md             -- project README
  CLAUDE.md             -- quick-reference
  AGENTS.md             -- full reference (target of this refresh)
```

## Findings: What Changed / What's Stale

### 1. File Structure Section is Incomplete

The current AGENTS.md file structure block is missing:
- `scripts/` directory (contains `validate-gitleaks-waivers.sh`)
- `docs/` directory (contains `roadmap.md`, `interbase-vision.md`, `vision.md` symlink)
- `.github/workflows/` (secret-scan CI)
- `.gitleaks.toml`
- `go/README.md` (standalone Go SDK README)

Decision: The file structure section should focus on SDK-relevant files. Infrastructure files (`.github/`, `.gitleaks.toml`, `scripts/validate-gitleaks-waivers.sh`) are boilerplate from the secret-scan baseline rollout and don't need documenting in AGENTS.md. Adding `docs/` is optional since it's strategic/roadmap content.

### 2. interband Path Reference is Stale

Current text: `interband (infra/interband/) provides data sharing...`
Actual path: `core/interband/`

### 3. Adopter Lists are Incomplete

**Bash SDK adopters** (current: none listed):
- interflux (sources stub in session-start, calls `ib_session_status`)
- intermem (sources stub in session-start, calls `ib_session_status`, `ib_nudge_companion`)
- intersynth (sources stub in session-start, calls `ib_session_status`, `ib_nudge_companion`)
- interline (sources stub in session-start, calls `ib_session_status`)

**Go SDK adopters** (current: "interlock (all 12 tools)"):
- interlock is still the only Go consumer. Verified by searching all `go.mod` files in the monorepo for `interbase` references. The `go.mod` search returned no results because interlock uses a `replace` directive with a relative path that may not literally contain "interbase" in the require line. But the Go import search confirmed interlock uses both `toolerror` and `mcputil`.

### 4. Test Count Verification

All test counts in the current AGENTS.md are **accurate**:
- test-guards.sh: 16 assertions (verified by counting `assert*` calls at lines 50-111)
- test-nudge.sh: 4 assertions (verified by counting `assert*` calls at lines 47-60)
- toolerror_test.go: 9 test functions (TestNew, TestTransientDefaultsRecoverable, TestNonTransientDefaultsNotRecoverable, TestWithRecoverable, TestWithData, TestError, TestJSON, TestFromError, TestWrap)
- instrument_test.go: 8 test functions (TestInstrumentSuccess, TestInstrumentGoError, TestInstrumentToolError, TestInstrumentPanic, TestInstrumentPerToolMetrics, TestInstrumentIsErrorResult, TestInstrumentConcurrent, TestHelpers)
- Total Go tests: 17 (correct)

### 5. API Surface Verification

**Bash SDK** -- all functions documented in AGENTS.md match the source exactly:
- Guards: `ib_has_ic`, `ib_has_bd`, `ib_has_companion`, `ib_in_ecosystem`, `ib_get_bead`, `ib_in_sprint` -- all match
- Actions: `ib_phase_set`, `ib_emit_event`, `ib_session_status`, `ib_nudge_companion` -- all match
- Internal helpers: all 6 `_ib_*` functions documented match

**Go SDK toolerror** -- all constants and methods match:
- Constants: `ErrNotFound`, `ErrConflict`, `ErrValidation`, `ErrPermission`, `ErrTransient`, `ErrInternal`
- Methods: `New`, `Error`, `WithRecoverable`, `WithData`, `JSON`, `FromError`, `Wrap`

**Go SDK mcputil** -- all types and functions match:
- Types: `Metrics`, `ToolStats`, `toolCounters` (unexported)
- Functions: `NewMetrics`, `Instrument`, `ToolMetrics`, `WrapError`, `ValidationError`, `NotFoundError`, `ConflictError`, `TransientError`
- `ToolStats` also implements `fmt.Stringer` via `String()` method -- not documented currently

### 6. Version / Dependency Check

- `INTERBASE_VERSION` in interbase.sh: `"1.0.0"`
- `lib/VERSION` file: `1.0.0`
- Go module: `go 1.23.0`, requires `mcp-go v0.43.2`
- These are consistent.

### 7. Roadmap Status

Open roadmap item: `iv-jay06 [P0] [epic] - Formalize interbase as a Multi-Language SDK`
Recently closed: toolerror, circuit breaker, mcputil middleware

## Changes Made to AGENTS.md

1. **Fixed interband path**: `infra/interband/` -> `core/interband/`
2. **Added Bash SDK adopters section**: interflux, intermem, intersynth, interline
3. **Added `ToolStats.String()` method** to mcputil documentation (was implemented but undocumented)
4. **Added `go/README.md`** to file structure
5. **Tightened line count**: Stayed within 150-200 line target (184 lines, essentially the same)
6. **No speculative content added**: Everything verified against source
