# Go Module Path Alignment

**Bead:** iv-9hx1t.1
**Date:** 2026-02-24
**Complexity:** 2/5 (simple)
**Parent Epic:** iv-9hx1t (Go Module Path Alignment — Demarch Reorg)

## Problem

Two Go modules have non-canonical module paths that don't follow the `github.com/mistakeknot/<name>` convention:

| Module | Directory | Current Path | Expected Path |
|--------|-----------|-------------|---------------|
| intercore | `core/intercore/` | `github.com/mistakeknot/interverse/infra/intercore` | `github.com/mistakeknot/intercore` |
| interbench | `core/interbench/` | `github.com/interbench` | `github.com/mistakeknot/interbench` |

Additionally, autarch uses a `replace` directive pointing to a symlink (`../Intermute`) rather than the canonical relative path (`../../core/intermute`).

## Current State

### Module Inventory (9 in-scope modules)

| Directory | Module Path | Go Version | Status |
|-----------|------------|------------|--------|
| `core/intermute` | `github.com/mistakeknot/intermute` | 1.24 | OK |
| `core/interband` | `github.com/mistakeknot/interband` | 1.24.0 | OK |
| `core/intercore` | `github.com/mistakeknot/interverse/infra/intercore` | 1.22 | **FIX** |
| `core/interbench` | `github.com/interbench` | 1.24.0 | **FIX** |
| `apps/autarch` | `github.com/mistakeknot/autarch` | 1.24.0 | OK (replace needs update) |
| `interverse/interlock` | `github.com/mistakeknot/interlock` | 1.23.0 | OK |
| `interverse/intermap` | `github.com/mistakeknot/intermap` | 1.23.0 | OK |
| `interverse/intermux` | `github.com/mistakeknot/intermux` | 1.23.0 | OK |
| `interverse/interserve` | `github.com/mistakeknot/interserve` | 1.23.0 | OK |

### Cross-Module Dependencies

- **No external consumers** import `github.com/mistakeknot/interverse/infra/intercore` or `github.com/interbench` from outside their own modules.
- Intercore's internal imports all use its own module path prefix (self-referential).
- Interbench has zero cross-module imports.
- Autarch depends on intermute via `replace github.com/mistakeknot/intermute => ../Intermute` (symlink).
- The symlink `apps/Intermute → core/intermute` exists and is functional.

### GitHub Remotes

- `core/intercore` → `https://github.com/mistakeknot/intercore.git` (already matches target path)
- `core/interbench` → `https://github.com/mistakeknot/interbench.git` (already matches target path)

## Tasks

### Task 1: Fix intercore module path [~5 min]

**Risk: Low** — only internal imports, no external consumers.

1. Update `core/intercore/go.mod`:
   - `module github.com/mistakeknot/interverse/infra/intercore` → `module github.com/mistakeknot/intercore`
2. Find-and-replace all internal imports in `core/intercore/**/*.go` (30 files across cmd/ic/ and internal/, including test files):
   - `github.com/mistakeknot/interverse/infra/intercore/` → `github.com/mistakeknot/intercore/`
3. Run `go mod tidy`, `go build ./...`, and `go test ./...` in `core/intercore/`
4. Commit in intercore's own git repo

### Task 2: Fix interbench module path [~2 min]

**Risk: Low** — no cross-module imports at all.

1. Update `core/interbench/go.mod`:
   - `module github.com/interbench` → `module github.com/mistakeknot/interbench`
2. Find-and-replace the one self-referential import in `main.go` line 9:
   - `github.com/interbench/` → `github.com/mistakeknot/interbench/`
   - (Verify no other files use the module path prefix — review found only this one occurrence)
3. Run `go mod tidy`, `go build ./...`, and `go test ./...` in `core/interbench/`
4. Commit in interbench's own git repo

### Task 3: Clean up autarch replace directive [~2 min]

**Risk: Low** — the symlink already resolves to the correct target.

1. Update `apps/autarch/go.mod`:
   - `replace github.com/mistakeknot/intermute => ../Intermute` → `replace github.com/mistakeknot/intermute => ../../core/intermute`
2. Verify autarch still builds: `go build ./cmd/...` in `apps/autarch/`
3. Keep the `apps/Intermute` symlink for now (other apps/ modules may depend on it; schedule removal as separate follow-up after full audit)
4. Commit in autarch's own git repo

### Task 4: Document canonical policy + add CI guard [~5 min]

1. Add a `## Go Module Path Convention` section to root `AGENTS.md`:
   - Convention: `github.com/mistakeknot/<module-name>` for all first-party modules
   - Replace directives should use relative paths from the module's directory (no symlinks)
2. Add a simple shell script `scripts/check-go-module-paths.sh` that:
   - Finds all `go.mod` files (excluding paths matching `*/research/*`, `*/.external/*`, `*/testdata/*` — use path-prefix patterns, not basename matching)
   - Verifies each `module` directive matches `github.com/mistakeknot/<dirname>`
   - Exits non-zero if any mismatch found
3. Commit in the monorepo root

## Execution Order

Tasks 1 and 2 are independent (parallel-safe).
Task 3 depends on nothing (but logically follows 1-2).
Task 4 depends on 1-3 being complete (documents the final state).

## Acceptance Criteria

- [ ] All 9 Go modules declare `github.com/mistakeknot/<name>` paths
- [ ] `go build ./...` passes in all 9 module directories
- [ ] `go test ./...` passes in intercore and interbench (the changed modules)
- [ ] Autarch builds without the Intermute symlink (uses direct relative path)
- [ ] CI guard script exists and passes
- [ ] Convention documented in AGENTS.md

## Rollback

If any module breaks after path change:
- Revert the go.mod + import changes in that module's git repo
- Each module has independent git history, so rollback is isolated
