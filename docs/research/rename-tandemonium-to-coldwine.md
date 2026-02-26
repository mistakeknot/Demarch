# Rename `.tandemonium` to `.coldwine` — Analysis & Execution Log

**Date:** 2026-02-24
**Scope:** `/home/mk/projects/Demarch/apps/autarch`

## Summary

Renamed all `.tandemonium` references to `.coldwine` and `tandemonium` to `coldwine` across 20 specified source files. Also renamed the `tandemoniumPlan` import alias to `coldwinePlan` in 2 files and changed `Use: "tandemonium"` to `Use: "coldwine"` in `internal/coldwine/cli/root.go`. Preserved `"tandemonium"` as a backward-compatible alias in `cmd/autarch/main.go` line 507.

## Files Modified — Replacement Counts

### `.tandemonium` → `.coldwine` replacements

| File | Count |
|------|-------|
| `internal/coldwine/cli/init_flow.go` | 3 |
| `internal/coldwine/cli/root.go` | 3 |
| `internal/coldwine/cli/commands/scan.go` | 1 |
| `internal/coldwine/cli/commands/plan.go` | 1 |
| `internal/coldwine/cli/commands/apply.go` | 2 |
| `internal/coldwine/cli/commands/doctor.go` | 1 |
| `internal/coldwine/cli/commands/agent.go` | 1 |
| `internal/coldwine/cli/commands/status.go` | 1 |
| `internal/coldwine/cli/commands/recover.go` | 1 |
| `internal/coldwine/tui/model.go` | 2 |
| `internal/coldwine/tui/watch.go` | 4 |
| `internal/coldwine/explore/explore_test.go` | 1 |
| `internal/autarch/local/source.go` | 6 |
| `internal/bigend/daemon/projects.go` | 6 |
| `pkg/shell/projects.go` | 1 |

**Subtotal: 34 `.tandemonium` → `.coldwine` replacements**

### Bare `tandemonium` → `coldwine` replacements

| File | Change | Count |
|------|--------|-------|
| `internal/coldwine/cli/root.go` | `Use: "tandemonium"` → `Use: "coldwine"` | 1 |
| `internal/coldwine/cli/root.go` | Example text (`tandemonium init`, `tandemonium apply`) → `coldwine` | 3 |
| `internal/coldwine/cli/root.go` | `tandemoniumPlan` → `coldwinePlan` (import alias + 4 usages) | 5 |
| `internal/coldwine/cli/commands/apply.go` | `tandemoniumPlan` → `coldwinePlan` (import alias + 1 usage) | 2 |
| `internal/coldwine/cli/commands/apply.go` | Example text + string literals (`"tandemonium"`) | 5 |
| `internal/coldwine/storage/db.go` | `tandemonium-db-` → `coldwine-db-` (temp dir prefix) | 1 |
| `pkg/plan/plan.go` | Comment: `praude, pollard, tandemonium` → `coldwine` | 1 |
| `internal/pollard/api/scanner.go` | Comment: `praude, tandemonium` → `coldwine` | 1 |
| `internal/pollard/cli/export.go` | String literal `"tandemonium"` + comment | 2 |
| `internal/bigend/web/server.go` | Comment: `has tandemonium` → `has coldwine` | 1 |
| `internal/coldwine/plan/plan.go` | `"tandemonium"` → `"coldwine"` (NewPlan tool name) | 1 |

**Subtotal: 23 bare `tandemonium` → `coldwine` replacements**

### Intentionally preserved

| File | Line | Reason |
|------|------|--------|
| `cmd/autarch/main.go:507` | `cmd.Aliases = []string{"tandemonium"}` | Backward-compatible CLI alias |

**Total: 57 replacements across 20 files, 1 intentional preservation**

## Files NOT in scope (still contain `.tandemonium`)

These files were NOT listed by the user and still reference `.tandemonium`. Most are either **legacy fallback code** (intentionally checking for `.tandemonium` as a migration path) or **test files** that test the legacy path detection:

### Legacy fallback code (intentional — DO NOT change)
- `internal/coldwine/project/paths.go:17,22` — checks `.coldwine` first, then legacy `.tandemonium`
- `internal/coldwine/cli/commands/task.go:372-373,412-417` — backward compat fallback to `.tandemonium`
- `internal/bigend/discovery/scanner.go:103-104,158-161` — discovers both `.coldwine` and `.tandemonium` directories

### Test files (may need updating in a separate pass)
- `internal/coldwine/tui/watch_test.go` — tests `.tandemonium` path detection
- `internal/coldwine/plan/plan_test.go` — creates `.tandemonium/plan` dir
- `internal/coldwine/config/config_test.go` — creates `.tandemonium` config dir (3 occurrences)
- `internal/coldwine/config/config.go` — default config path uses `.tandemonium`
- `internal/coldwine/project/paths_test.go` — tests `.tandemonium` dir detection
- `internal/coldwine/project/init_test.go` — expects `.tandemonium` subdirectories created
- `internal/coldwine/cli/commands/mail_test.go` — creates `.tandemonium` state/config (5 occurrences)
- `internal/coldwine/cli/commands/plan_test.go` — creates `.tandemonium/plan` dir
- `internal/coldwine/cli/commands/scan_test.go` — checks `.tandemonium/plan/exploration.md`
- `internal/coldwine/cli/commands/import_test.go` — checks `.tandemonium` absence (4 occurrences)
- `internal/coldwine/cli/root_test.go` — checks `.tandemonium` subdirectories (4 occurrences)

### Recommendation for out-of-scope files
- **Legacy fallback code**: Keep as-is — these intentionally support both directory names during migration.
- **Test files**: Should be updated in a follow-up pass. Tests currently create and check `.tandemonium` directories; they should be updated to use `.coldwine` (the new primary path), with separate tests for legacy `.tandemonium` fallback behavior.
- **config.go**: The default config path on line 56 should be updated to `.coldwine` in a follow-up, along with its tests.

## Verification

After all replacements, `grep -rn 'tandemonium'` across the 20 target files returns only the intentionally preserved alias in `cmd/autarch/main.go:507`.
