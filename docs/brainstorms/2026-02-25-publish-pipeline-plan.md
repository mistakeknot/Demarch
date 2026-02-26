# Implementation Plan: `ic publish`

**Date:** 2026-02-25
**Parent:** [publish-pipeline-overhaul.md](2026-02-25-publish-pipeline-overhaul.md)
**Status:** plan

---

## Overview

Replace the shell-based plugin publish pipeline (interbump.sh, auto-publish.sh, /interpub:release) with a Go-based `ic publish` subcommand in Intercore. Single version source of truth (`plugin.json`), SQLite state machine for recovery, comprehensive doctor, and a 5-line auto-publish hook.

---

## Implementation Phases

### Phase 1: Core Package (`internal/publish/`)

Foundation types, version handling, and plugin/marketplace discovery. No CLI wiring yet — just the library.

#### Task 1.1: Types and Constants (`publish.go`)

```go
// Phase represents a publish pipeline step
type Phase string
const (
    PhaseIdle         Phase = "idle"
    PhaseDiscovery    Phase = "discovery"
    PhaseValidation   Phase = "validation"
    PhaseBump         Phase = "bump"
    PhaseCommitPlugin Phase = "commit_plugin"
    PhasePushPlugin   Phase = "push_plugin"
    PhaseUpdateMarket Phase = "update_marketplace"
    PhaseSyncLocal    Phase = "sync_local"
    PhaseDone         Phase = "done"
)

// PublishState tracks an in-flight publish
type PublishState struct {
    ID          string
    PluginName  string
    FromVersion string
    ToVersion   string
    Phase       Phase
    PluginRoot  string
    MarketRoot  string
    StartedAt   int64
    UpdatedAt   int64
    Error       string // last error message, empty if clean
}

// Plugin represents a discovered plugin
type Plugin struct {
    Name       string
    Version    string // current version from plugin.json
    Root       string // absolute path to plugin root (parent of .claude-plugin/)
    PluginJSON string // absolute path to plugin.json
}

// VersionFile is a derived file that contains a version string
type VersionFile struct {
    Path    string
    Type    string // "json", "toml", "markdown"
    JSONKey string // e.g. ".version" for package.json
}

// BumpMode controls version increment behavior
type BumpMode int
const (
    BumpExact BumpMode = iota // explicit version string
    BumpPatch                 // X.Y.Z+1
    BumpMinor                 // X.Y+1.0
)

// PublishOpts configures a publish run
type PublishOpts struct {
    Mode    BumpMode
    Version string // only for BumpExact
    DryRun  bool
    Auto    bool   // suppress prompts, used by hook
    CWD     string // override working directory
}
```

**Tests:** Basic type construction, Phase ordering.

#### Task 1.2: Version Parsing (`version.go`)

```go
func ParseVersion(s string) (major, minor, patch int, pre string, err error)
func FormatVersion(major, minor, patch int, pre string) string
func BumpVersion(current string, mode BumpMode) (string, error)
func CompareVersions(a, b string) int // -1, 0, 1
```

Semver regex: `^(\d+)\.(\d+)\.(\d+)(-[a-zA-Z0-9.]+)?$`

**Tests:** Parse/format round-trip, bump modes, comparison, pre-release handling, invalid inputs.

#### Task 1.3: Plugin Discovery (`discovery.go`)

```go
// FindPluginRoot walks up from dir looking for .claude-plugin/plugin.json
func FindPluginRoot(dir string) (string, error)

// ReadPlugin reads plugin identity from plugin.json
func ReadPlugin(root string) (*Plugin, error)

// DiscoverVersionFiles finds all derived version files in a plugin
func DiscoverVersionFiles(root string) []VersionFile
```

Version file discovery logic (ported from interbump.sh):
- Always: `.claude-plugin/plugin.json`
- If exists: `pyproject.toml`, `package.json`, `server/package.json`, `agent-rig.json`, `Cargo.toml`
- Drop: `docs/PRD.md` (was inconsistently handled — interbump updated it, auto-publish didn't)

**Tests:** Fixture plugin dirs with various combinations, walk-up from nested dirs.

#### Task 1.4: Marketplace Operations (`marketplace.go`)

```go
// FindMarketplace locates marketplace.json via walk-up algorithm
func FindMarketplace(from string) (string, error)

// ReadMarketplaceVersion reads a plugin's version from marketplace.json
func ReadMarketplaceVersion(marketRoot, pluginName string) (string, error)

// UpdateMarketplaceVersion writes a new version for a plugin
func UpdateMarketplaceVersion(marketRoot, pluginName, version string) error

// ListMarketplacePlugins returns all plugin names and versions
func ListMarketplacePlugins(marketRoot string) (map[string]string, error)

// RegisterPlugin adds a new plugin entry to marketplace.json
func RegisterPlugin(marketRoot string, plugin *Plugin) error

// CCMarketplacePath returns the CC marketplace checkout path (if it exists)
func CCMarketplacePath() string

// SyncCCMarketplace copies marketplace.json from monorepo to CC checkout
func SyncCCMarketplace(marketRoot, pluginName, version string) error
```

Walk-up algorithm (from interbump.sh): walk up 4 levels looking for `core/marketplace/.claude-plugin/marketplace.json`. Fallback to `~/.claude/plugins/marketplaces/interagency-marketplace/`.

**Tests:** Walk-up with fixture dirs, marketplace.json read/write, plugin not found.

#### Task 1.5: Git Operations (`git.go`)

```go
// GitStatus checks if worktree is clean
func GitStatus(dir string) (clean bool, err error)

// GitRemoteReachable checks if origin HEAD is accessible
func GitRemoteReachable(dir string) error

// GitAdd stages specific files
func GitAdd(dir string, files ...string) error

// GitCommit creates a commit with the given message
func GitCommit(dir, message string) error

// GitPullRebase runs git pull --rebase
func GitPullRebase(dir string) error

// GitPush runs git push (never force, never amend)
func GitPush(dir string) error

// GitHeadCommit returns the current HEAD SHA
func GitHeadCommit(dir string) (string, error)

// GitRevert reverts the last N commits (for rollback)
func GitRevert(dir string, n int) error
```

All use `exec.Command("git", "-C", dir, ...)` — no shell, no injection.

**Tests:** Integration tests with `git init` in `t.TempDir()`.

#### Task 1.6: Cache Management (`cache.go`)

```go
const CacheBase = "~/.claude/plugins/cache/interagency-marketplace"

// RebuildCache copies plugin source to cache, excluding .git
func RebuildCache(pluginName, version, srcRoot string) error

// CleanOrphans removes dirs with .orphaned_at markers
func CleanOrphans() (count int, bytesFreed int64, err error)

// StripGitDirs removes .git/ from all cache entries
func StripGitDirs() (count int, bytesFreed int64, err error)

// CreateSymlinks creates version bridge symlinks for hook continuity
func CreateSymlinks(pluginName, oldVersion, newVersion string) error

// ListCacheEntries returns all cached plugin versions
func ListCacheEntries() (map[string][]CacheEntry, error)
```

Key change from interbump.sh: use `cp` with `--exclude=.git` or use a Go copy that skips `.git` dirs. No more archiving entire git repos into cache.

**Tests:** Cache rebuild, orphan detection, symlink creation.

#### Task 1.7: Installed Plugins Management (`installed.go`)

```go
const InstalledPath = "~/.claude/plugins/installed_plugins.json"

// ReadInstalled reads the installed_plugins.json file
func ReadInstalled() (*InstalledPlugins, error)

// UpdateInstalled patches version and installPath for a plugin
func UpdateInstalled(pluginName, version, installPath string) error
```

Atomic write: write to temp file, rename. No jq dependency.

**Tests:** Read/write round-trip, atomic write on failure.

---

### Phase 2: State Machine (`internal/publish/state.go`)

SQLite-backed publish state for recovery.

#### Task 2.1: Schema

New table in `internal/db/schema.sql`:

```sql
-- v21: publish state tracking
CREATE TABLE IF NOT EXISTS publish_state (
    id         TEXT PRIMARY KEY,
    plugin     TEXT NOT NULL,
    from_ver   TEXT NOT NULL,
    to_ver     TEXT NOT NULL,
    phase      TEXT NOT NULL DEFAULT 'idle',
    root       TEXT NOT NULL,
    market     TEXT NOT NULL,
    started_at INTEGER NOT NULL DEFAULT (unixepoch()),
    updated_at INTEGER NOT NULL DEFAULT (unixepoch()),
    error      TEXT NOT NULL DEFAULT ''
);
```

Bump `currentSchemaVersion` to 21 in `db.go`.

#### Task 2.2: Store Operations

```go
type Store struct { db *sql.DB }

func (s *Store) Create(ctx context.Context, state *PublishState) error
func (s *Store) Update(ctx context.Context, id string, phase Phase, err string) error
func (s *Store) Get(ctx context.Context, id string) (*PublishState, error)
func (s *Store) GetActive(ctx context.Context, pluginName string) (*PublishState, error)
func (s *Store) Complete(ctx context.Context, id string) error
func (s *Store) List(ctx context.Context) ([]*PublishState, error)
```

**Tests:** State transitions, active detection, concurrent access.

---

### Phase 3: Publish Engine (`internal/publish/engine.go`)

The orchestrator that ties everything together.

#### Task 3.1: Engine

```go
type Engine struct {
    store *Store
    opts  PublishOpts
}

func NewEngine(db *sql.DB, opts PublishOpts) *Engine

// Publish runs the full pipeline
func (e *Engine) Publish(ctx context.Context) error

// Resume picks up from a failed phase
func (e *Engine) Resume(ctx context.Context, stateID string) error

// Rollback reverts a partial publish
func (e *Engine) Rollback(ctx context.Context, stateID string) error
```

Phase sequence:
1. **Discovery** — `FindPluginRoot`, `ReadPlugin`, `DiscoverVersionFiles`, `FindMarketplace`
2. **Validation** — `GitStatus` (both repos clean), `GitRemoteReachable` (both), run `validate-plugin.sh` if present, run `post-bump.sh` if present
3. **Bump** — Write new version to `plugin.json`, patch all derived files, verify all match
4. **CommitPlugin** — `GitAdd` changed files, `GitCommit`, `GitPullRebase`
5. **PushPlugin** — `GitPush` (never force, never amend)
6. **UpdateMarketplace** — `UpdateMarketplaceVersion`, git add/commit/pull/push marketplace
7. **SyncLocal** — `RebuildCache`, `UpdateInstalled`, `SyncCCMarketplace`, `CreateSymlinks`
8. **Done** — Clear state, print summary

Each phase updates the SQLite state before and after execution. On failure, the state records which phase failed and the error message.

**Tests:** Full pipeline against fixture repos (git init, write plugin.json, etc.). Mock network calls for push.

---

### Phase 4: Doctor (`internal/publish/doctor.go`)

#### Task 4.1: Health Checks

```go
type Finding struct {
    Severity string // "error", "warning", "info"
    Category string // "drift", "cache", "schema", "hooks"
    Plugin   string
    Message  string
    Fix      string // description of auto-fix action
}

type DoctorOpts struct {
    Fix  bool
    JSON bool
}

func RunDoctor(ctx context.Context, opts DoctorOpts) ([]Finding, error)
```

Checks (absorbing validate-plugin.sh):
1. **Version drift**: plugin.json vs marketplace.json for all plugins
2. **Installed drift**: installed_plugins.json vs marketplace.json
3. **CC marketplace desync**: diff monorepo vs CC checkout
4. **Orphaned cache dirs**: scan for `.orphaned_at`
5. **Missing cache entries**: cross-ref installed paths
6. **`.git` in cache**: scan cache for `.git/`
7. **Cache version mismatch**: plugin.json inside cache vs dir name
8. **Missing bump-version.sh wrappers**: scan interverse/*/
9. **Stale publish state**: incomplete publishes in SQLite
10. **plugin.json schema**: required fields, unrecognized keys, author format
11. **Undeclared hooks**: hooks on disk but not in plugin.json
12. **Hardcoded secrets**: env vars in mcpServers
13. **Unregistered plugins**: plugin dirs not in marketplace.json

Each check returns findings. With `--fix`, auto-repair where safe.

**Tests:** Fixture marketplace with various drift scenarios.

---

### Phase 5: CLI Wiring (`cmd/ic/publish.go`)

#### Task 5.1: Subcommand Router

```go
func cmdPublish(ctx context.Context, args []string) int {
    if len(args) == 0 {
        printPublishUsage()
        return 3
    }
    switch args[0] {
    case "doctor":  return cmdPublishDoctor(ctx, args[1:])
    case "clean":   return cmdPublishClean(ctx, args[1:])
    case "status":  return cmdPublishStatus(ctx, args[1:])
    case "init":    return cmdPublishInit(ctx, args[1:])
    default:
        // Treat as version: ic publish 0.3.0
        // Or flag: ic publish --patch
        return cmdPublishRun(ctx, args)
    }
}
```

#### Task 5.2: Wire into main.go

Add `case "publish"` to the switch and usage text.

#### Task 5.3: Implement each sub-handler

- `cmdPublishRun` — parse flags (`--patch`, `--minor`, `--dry-run`, `--auto`, `--cwd`), detect resume scenario, run engine
- `cmdPublishDoctor` — parse `--fix`, `--json`, run doctor
- `cmdPublishClean` — parse `--dry-run`, run `CleanOrphans` + `StripGitDirs`
- `cmdPublishStatus` — parse `--all`, show current plugin or all plugins
- `cmdPublishInit` — parse `--name`, register new plugin in marketplace

**Tests:** CLI flag parsing, exit codes.

---

### Phase 6: Hook + Skill Rewiring

#### Task 6.1: Replace auto-publish.sh

Replace `os/clavain/hooks/auto-publish.sh` (213 lines) with thin wrapper:

```bash
#!/usr/bin/env bash
[[ "$TOOL_NAME" == "Bash" ]] || exit 0
[[ "$EXIT_CODE" == "0" ]] || exit 0
[[ "$TOOL_INPUT" =~ git\ push ]] || exit 0
[[ "$TOOL_INPUT" =~ --force|-f\ |--no-verify ]] && exit 0

ic publish --auto --cwd "$CWD" 2>/dev/null
exit 0
```

Auto mode behavior in the engine:
- Use sentinel package with per-plugin scope: `sentinel.Check("autopub", pluginName, 30)`
- Auto-increment patch
- Suppress all interactive prompts
- Never amend, never force-push
- Create a new commit for the version bump

#### Task 6.2: Replace /interpub:release skill

Replace `interverse/interpub/commands/release.md` with thin wrapper that runs `ic publish <version>`.

#### Task 6.3: Update bump-version.sh wrappers

All existing `scripts/bump-version.sh` wrappers become:
```bash
#!/usr/bin/env bash
exec ic publish "$@"
```

---

### Phase 7: Migration and Cleanup

#### Task 7.1: Run doctor --fix

Execute `ic publish doctor --fix` to resolve all existing drift:
- Sync 4 known version drifts
- Clean 30 orphaned cache dirs
- Strip .git from cache entries
- Rebuild missing cache entries

#### Task 7.2: Deprecation notices

Add deprecation banner to `scripts/interbump.sh`:
```bash
echo "WARNING: interbump.sh is deprecated. Use 'ic publish' instead." >&2
```

#### Task 7.3: Update documentation

- Root AGENTS.md: update publish workflow
- Root CLAUDE.md: update publish references
- interverse/interpub/CLAUDE.md: update
- core/marketplace/CLAUDE.md: update

---

## File Manifest

### New files

| File | Lines (est.) | Purpose |
|------|-------------|---------|
| `internal/publish/publish.go` | ~80 | Types, constants, errors |
| `internal/publish/version.go` | ~60 | Version parsing and bumping |
| `internal/publish/version_test.go` | ~100 | Version tests |
| `internal/publish/discovery.go` | ~100 | Plugin + version file discovery |
| `internal/publish/discovery_test.go` | ~120 | Discovery tests |
| `internal/publish/marketplace.go` | ~180 | Marketplace read/write/sync |
| `internal/publish/marketplace_test.go` | ~150 | Marketplace tests |
| `internal/publish/git.go` | ~120 | Git operations |
| `internal/publish/git_test.go` | ~100 | Git integration tests |
| `internal/publish/cache.go` | ~150 | Cache management |
| `internal/publish/cache_test.go` | ~100 | Cache tests |
| `internal/publish/installed.go` | ~80 | installed_plugins.json |
| `internal/publish/installed_test.go` | ~80 | Installed tests |
| `internal/publish/state.go` | ~100 | SQLite publish state |
| `internal/publish/state_test.go` | ~80 | State tests |
| `internal/publish/engine.go` | ~250 | Publish orchestrator |
| `internal/publish/engine_test.go` | ~200 | Engine tests |
| `internal/publish/doctor.go` | ~300 | Health checks + auto-repair |
| `internal/publish/doctor_test.go` | ~200 | Doctor tests |
| `cmd/ic/publish.go` | ~200 | CLI subcommand router |
| **Total** | **~2,650** | |

### Modified files

| File | Change |
|------|--------|
| `cmd/ic/main.go` | Add `case "publish"` + usage line |
| `internal/db/schema.sql` | Add `publish_state` table |
| `internal/db/db.go` | Bump schema version to 21 |
| `os/clavain/hooks/auto-publish.sh` | Replace 213 lines with 6 lines |
| `interverse/interpub/commands/release.md` | Replace with thin `ic publish` wrapper |
| `scripts/interbump.sh` | Add deprecation banner |

---

## Execution Order

The phases above are ordered by dependency. Within each phase, tasks are independent and can be parallelized. Suggested execution batches:

1. **Batch 1** (foundation, parallelizable): Tasks 1.1, 1.2, 1.5, 1.6, 1.7
2. **Batch 2** (depends on 1.1, 1.2): Tasks 1.3, 1.4
3. **Batch 3** (depends on 1.*): Task 2.1, 2.2
4. **Batch 4** (depends on all above): Task 3.1
5. **Batch 5** (depends on 3): Task 4.1
6. **Batch 6** (depends on 3, 4): Tasks 5.1, 5.2, 5.3
7. **Batch 7** (depends on 6): Tasks 6.1, 6.2, 6.3
8. **Batch 8** (depends on 7): Tasks 7.1, 7.2, 7.3

---

## Open Design Notes

1. **Cache copy without .git**: Use Go's `filepath.WalkDir` with a skip on `.git` dirs instead of `cp -a`. More control, no external dependency.
2. **Marketplace JSON editing**: Use `encoding/json` with `json.RawMessage` to preserve unknown fields and formatting (don't round-trip through a typed struct that drops fields).
3. **Sentinel reuse**: The existing `internal/sentinel` package is exactly what we need for per-plugin dedup. Just use `sentinel.Check("autopub", pluginName, 30)`.
4. **DB access for publish**: `ic publish` may run outside a `.clavain/` project (e.g., in a plugin root). Use a global publish DB at `~/.intercore/publish.db` rather than the project-local `intercore.db`, since publish state is per-user not per-project.
5. **Dropping PRD.md version**: interbump updated `docs/PRD.md`, auto-publish didn't. Since we're going single-source, drop PRD.md from the version file list entirely. Versions in markdown are informational and can be wrong.
