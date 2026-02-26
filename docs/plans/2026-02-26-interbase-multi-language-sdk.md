# Interbase Multi-Language SDK Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use clavain:executing-plans to implement this plan task-by-task.

**Goal:** Formalize interbase as a spec-driven multi-language SDK where Bash, Go, and Python are equal peers, all implementing the same interface contract with YAML conformance tests preventing drift.

**Architecture:** Shared spec defines the contract (types, behaviors, fail-open semantics). Each language gets a native implementation — Bash expands the existing `lib/interbase.sh`, Go adds a new `interbase` root package alongside existing `toolerror`/`mcputil`, Python gets a new `interbase` package with `pyproject.toml`. YAML conformance tests run per-language thin runners to catch drift at PR time.

**Tech Stack:** Bash 4+, Go 1.23 (module `github.com/mistakeknot/interbase`), Python 3.11+ with Hatchling build system and `uv`, PyYAML for conformance runners, `mcp-go` v0.43.2.

---

### Task 1: Write the Interface Spec

**Files:**
- Create: `sdk/interbase/spec/interbase-spec.md`

**Step 1: Write the spec document**

Create `sdk/interbase/spec/interbase-spec.md` with the following structure. This is the authoritative reference — implementations must match it exactly.

```markdown
# Interbase SDK Interface Specification

Version: 2.0.0
Date: 2026-02-26

## Conventions

- **Fail-open:** Every guard function returns false/0/empty when its dependency
  is missing. Never raises an exception. Never blocks.
- **Silent no-op:** Every action function succeeds silently when its dependency
  is missing. Errors from underlying tools are logged to stderr but never
  propagated to the caller.
- **Environment variables:** Functions read from environment. They never write
  to environment (no side effects on env).

## Domain 1: Guards

### has_ic

Checks whether the `ic` (Intercore) CLI binary is available on PATH.

| Language | Signature | Return |
|----------|-----------|--------|
| Bash | `ib_has_ic` | exit code 0 (found) or 1 (missing) |
| Go | `func HasIC() bool` | true if found |
| Python | `def has_ic() -> bool` | True if found |

**Behavior:**
- Checks `$PATH` for an executable named `ic`
- Does NOT execute `ic` — only checks existence
- Returns false/1 if PATH is empty or ic is not found

### has_bd

Checks whether the `bd` (Beads) CLI binary is available on PATH.

| Language | Signature | Return |
|----------|-----------|--------|
| Bash | `ib_has_bd` | exit code 0/1 |
| Go | `func HasBD() bool` | bool |
| Python | `def has_bd() -> bool` | bool |

**Behavior:** Same as `has_ic` but for `bd` binary.

### has_companion

Checks whether a named companion plugin is installed in the Claude Code cache.

| Language | Signature | Return |
|----------|-----------|--------|
| Bash | `ib_has_companion NAME` | exit code 0/1 |
| Go | `func HasCompanion(name string) bool` | bool |
| Python | `def has_companion(name: str) -> bool` | bool |

**Behavior:**
- Scans `~/.claude/plugins/cache/*/NAME/*` for any matching directory
- Returns false if `name` is empty
- Does NOT check plugin version or health — just existence

### in_ecosystem

Returns true if the SDK was loaded from the centralized install (not a stub).

| Language | Signature | Return |
|----------|-----------|--------|
| Bash | `ib_in_ecosystem` | exit code 0/1 |
| Go | `func InEcosystem() bool` | bool |
| Python | `def in_ecosystem() -> bool` | bool |

**Behavior:**
- Bash: checks `_INTERBASE_SOURCE == "live"`
- Go/Python: checks that the centralized install exists at
  `~/.intermod/interbase/interbase.sh` (file existence, not sourcing)

### get_bead

Returns the current bead ID from the environment.

| Language | Signature | Return |
|----------|-----------|--------|
| Bash | `ib_get_bead` | stdout (bead ID or empty) |
| Go | `func GetBead() string` | string (empty if unset) |
| Python | `def get_bead() -> str` | str (empty if unset) |

**Behavior:** Reads `$CLAVAIN_BEAD_ID` environment variable. Returns empty
string if unset or empty.

### in_sprint

Returns true if there is an active sprint context (bead + ic run).

| Language | Signature | Return |
|----------|-----------|--------|
| Bash | `ib_in_sprint` | exit code 0/1 |
| Go | `func InSprint() bool` | bool |
| Python | `def in_sprint() -> bool` | bool |

**Behavior:**
- Returns false if `$CLAVAIN_BEAD_ID` is empty
- Returns false if `ic` is not on PATH
- Executes `ic run current --project=.` and returns true if exit code is 0
- Stderr/stdout from `ic` are suppressed

## Domain 2: Actions

### phase_set

Sets the phase on a bead via `bd set-state`.

| Language | Signature | Return |
|----------|-----------|--------|
| Bash | `ib_phase_set BEAD PHASE [REASON]` | exit code 0 (always) |
| Go | `func PhaseSet(bead, phase string, reason ...string)` | (no return) |
| Python | `def phase_set(bead: str, phase: str, reason: str = "") -> None` | None |

**Behavior:**
- If `bd` is not on PATH: silent no-op, return success
- Executes: `bd set-state BEAD "phase=PHASE"`
- If `bd` returns non-zero: log to stderr, return success anyway
- `reason` parameter is currently unused but reserved for future use

### emit_event

Emits an event via `ic events emit`.

| Language | Signature | Return |
|----------|-----------|--------|
| Bash | `ib_emit_event RUN_ID EVENT_TYPE [PAYLOAD]` | exit code 0 (always) |
| Go | `func EmitEvent(runID, eventType string, payload ...string)` | (no return) |
| Python | `def emit_event(run_id: str, event_type: str, payload: str = "{}") -> None` | None |

**Behavior:**
- If `ic` is not on PATH: silent no-op, return success
- Executes: `ic events emit RUN_ID EVENT_TYPE --payload=PAYLOAD`
- Default payload: `"{}"` (empty JSON object)
- If `ic` returns non-zero: log to stderr, return success anyway

### session_status

Prints ecosystem status to stderr.

| Language | Signature | Return |
|----------|-----------|--------|
| Bash | `ib_session_status` | exit code 0 (always), output on stderr |
| Go | `func SessionStatus() string` | status string |
| Python | `def session_status() -> str` | status string |

**Behavior:**
- Probes `bd` and `ic` availability
- If `ic` is available, probes `ic run current --project=.` for active run
- Bash: prints `[interverse] beads=active|not-detected | ic=active|not-initialized|not-detected` to stderr
- Go/Python: returns the same formatted string (caller decides where to print)

## Domain 3: Config + Discovery

### plugin_cache_path

Returns the filesystem path to a plugin's Claude Code cache directory.

| Language | Signature | Return |
|----------|-----------|--------|
| Bash | `ib_plugin_cache_path PLUGIN` | stdout (path or empty) |
| Go | `func PluginCachePath(plugin string) string` | string |
| Python | `def plugin_cache_path(plugin: str) -> str` | str |

**Behavior:**
- Scans `~/.claude/plugins/cache/*/PLUGIN/` directories
- Returns the path to the highest-versioned directory found
- Returns empty string if plugin not found or name is empty
- Does NOT validate the directory contents

### ecosystem_root

Returns the Demarch monorepo root directory.

| Language | Signature | Return |
|----------|-----------|--------|
| Bash | `ib_ecosystem_root` | stdout (path or empty) |
| Go | `func EcosystemRoot() string` | string |
| Python | `def ecosystem_root() -> str` | str |

**Behavior:**
- Reads `$DEMARCH_ROOT` if set
- Otherwise walks up from CWD looking for a directory containing
  `sdk/interbase/` as a heuristic
- Returns empty string if not found

### nudge_companion

Suggests installing a missing companion plugin. Rate-limited.

| Language | Signature | Return |
|----------|-----------|--------|
| Bash | `ib_nudge_companion COMPANION BENEFIT [PLUGIN]` | exit code 0 (always) |
| Go | `func NudgeCompanion(companion, benefit string, plugin ...string)` | (no return) |
| Python | `def nudge_companion(companion: str, benefit: str, plugin: str = "unknown") -> None` | None |

**Behavior:**
- If `companion` is empty: silent no-op
- If companion is already installed (`has_companion`): silent no-op
- If session budget exhausted (>=2 nudges this session): silent no-op
- If companion permanently dismissed (>=3 ignores): silent no-op
- Otherwise: print `[interverse] Tip: run /plugin install COMPANION for BENEFIT.` to stderr
- Increment session counter and record ignore in durable state
- Session state: `~/.config/interverse/nudge-session-${CLAUDE_SESSION_ID}.json`
- Durable state: `~/.config/interverse/nudge-state.json`
- Atomic dedup via `mkdir` (Bash) or file lock (Go/Python)

## Domain 4: MCP Contracts (Go + Python only)

### ToolError

Structured error type for MCP tool handlers.

**Wire format (JSON):**
```json
{
  "type": "NOT_FOUND",
  "message": "agent 'fd-safety' not registered",
  "recoverable": false,
  "data": {}
}
```

**Error types:**
| Constant | Wire value | Default recoverable |
|----------|-----------|-------------------|
| ErrNotFound | `"NOT_FOUND"` | false |
| ErrConflict | `"CONFLICT"` | false |
| ErrValidation | `"VALIDATION"` | false |
| ErrPermission | `"PERMISSION"` | false |
| ErrTransient | `"TRANSIENT"` | true |
| ErrInternal | `"INTERNAL"` | false |

**API (Go):**
```go
toolerror.New(errType, format, args...) *ToolError
te.WithRecoverable(bool) *ToolError
te.WithData(map[string]any) *ToolError
te.JSON() string
te.Error() string  // "[TYPE] message"
toolerror.FromError(err) *ToolError
toolerror.Wrap(err) *ToolError
```

**API (Python):**
```python
ToolError(err_type, message, **data)
te.with_recoverable(bool) -> ToolError
te.with_data(**kwargs) -> ToolError
te.json() -> str
str(te) -> "[TYPE] message"
ToolError.from_error(exc) -> ToolError | None
ToolError.wrap(exc) -> ToolError
```

### Metrics Middleware

Handler middleware for MCP tool handlers providing timing, error counting,
error wrapping, and panic/exception recovery.

**Go:** `mcputil.NewMetrics()` + `metrics.Instrument()` → `server.ToolHandlerMiddleware`
**Python:** `McpMetrics()` + `metrics.instrument()` → decorator/middleware callable
```

**Step 2: Commit**

```bash
git add sdk/interbase/spec/interbase-spec.md
git commit -m "feat(interbase): add interface specification for multi-language SDK"
```

---

### Task 2: Go SDK — Guards + Actions + Config

**Files:**
- Create: `sdk/interbase/go/interbase.go`
- Create: `sdk/interbase/go/interbase_test.go`

**Step 1: Write the failing tests**

Create `sdk/interbase/go/interbase_test.go`:

```go
package interbase

import (
	"os"
	"os/exec"
	"path/filepath"
	"strings"
	"testing"
)

func TestHasIC_WhenPresent(t *testing.T) {
	if _, err := exec.LookPath("ic"); err != nil {
		t.Skip("ic not on PATH")
	}
	if !HasIC() {
		t.Error("HasIC() = false, want true (ic is on PATH)")
	}
}

func TestHasIC_WhenMissing(t *testing.T) {
	// Use empty PATH to ensure ic is not found
	old := os.Getenv("PATH")
	t.Setenv("PATH", "")
	defer os.Setenv("PATH", old)

	if HasIC() {
		t.Error("HasIC() = true, want false (empty PATH)")
	}
}

func TestHasBD_WhenPresent(t *testing.T) {
	if _, err := exec.LookPath("bd"); err != nil {
		t.Skip("bd not on PATH")
	}
	if !HasBD() {
		t.Error("HasBD() = false, want true (bd is on PATH)")
	}
}

func TestHasBD_WhenMissing(t *testing.T) {
	old := os.Getenv("PATH")
	t.Setenv("PATH", "")
	defer os.Setenv("PATH", old)

	if HasBD() {
		t.Error("HasBD() = true, want false (empty PATH)")
	}
}

func TestHasCompanion_Empty(t *testing.T) {
	if HasCompanion("") {
		t.Error("HasCompanion('') = true, want false")
	}
}

func TestHasCompanion_Nonexistent(t *testing.T) {
	if HasCompanion("this-plugin-does-not-exist-zzzz") {
		t.Error("HasCompanion for nonexistent plugin should be false")
	}
}

func TestGetBead_Set(t *testing.T) {
	t.Setenv("CLAVAIN_BEAD_ID", "iv-test123")
	if got := GetBead(); got != "iv-test123" {
		t.Errorf("GetBead() = %q, want %q", got, "iv-test123")
	}
}

func TestGetBead_Unset(t *testing.T) {
	t.Setenv("CLAVAIN_BEAD_ID", "")
	if got := GetBead(); got != "" {
		t.Errorf("GetBead() = %q, want empty", got)
	}
}

func TestInEcosystem_FileExists(t *testing.T) {
	// Create a temp file mimicking the installed copy
	tmp := t.TempDir()
	path := filepath.Join(tmp, "interbase.sh")
	os.WriteFile(path, []byte("#!/bin/bash"), 0644)

	t.Setenv("INTERMOD_LIB", path)
	if !InEcosystem() {
		t.Error("InEcosystem() = false, want true (file exists)")
	}
}

func TestInEcosystem_FileMissing(t *testing.T) {
	t.Setenv("INTERMOD_LIB", "/nonexistent/path/interbase.sh")
	if InEcosystem() {
		t.Error("InEcosystem() = true, want false (file does not exist)")
	}
}

func TestInSprint_NoBead(t *testing.T) {
	t.Setenv("CLAVAIN_BEAD_ID", "")
	if InSprint() {
		t.Error("InSprint() = true, want false (no bead)")
	}
}

func TestInSprint_NoIC(t *testing.T) {
	t.Setenv("CLAVAIN_BEAD_ID", "iv-test")
	old := os.Getenv("PATH")
	t.Setenv("PATH", "")
	defer os.Setenv("PATH", old)

	if InSprint() {
		t.Error("InSprint() = true, want false (no ic)")
	}
}

func TestPhaseSet_NoBD(t *testing.T) {
	old := os.Getenv("PATH")
	t.Setenv("PATH", "")
	defer os.Setenv("PATH", old)

	// Should succeed silently (fail-open) — no return value to check
	PhaseSet("bead-123", "planned")
}

func TestEmitEvent_NoIC(t *testing.T) {
	old := os.Getenv("PATH")
	t.Setenv("PATH", "")
	defer os.Setenv("PATH", old)

	// Should succeed silently (fail-open) — no return value to check
	EmitEvent("run-123", "test-event")
}

func TestSessionStatus_Format(t *testing.T) {
	status := SessionStatus()
	if !strings.HasPrefix(status, "[interverse]") {
		t.Errorf("SessionStatus() = %q, want prefix [interverse]", status)
	}
	if !strings.Contains(status, "beads=") {
		t.Errorf("SessionStatus() = %q, should contain beads=", status)
	}
	if !strings.Contains(status, "ic=") {
		t.Errorf("SessionStatus() = %q, should contain ic=", status)
	}
}

func TestPluginCachePath_Empty(t *testing.T) {
	if got := PluginCachePath(""); got != "" {
		t.Errorf("PluginCachePath('') = %q, want empty", got)
	}
}

func TestEcosystemRoot_EnvOverride(t *testing.T) {
	t.Setenv("DEMARCH_ROOT", "/test/demarch")
	if got := EcosystemRoot(); got != "/test/demarch" {
		t.Errorf("EcosystemRoot() = %q, want /test/demarch", got)
	}
}

func TestEcosystemRoot_Unset(t *testing.T) {
	t.Setenv("DEMARCH_ROOT", "")
	// Should return something or empty — just shouldn't panic
	_ = EcosystemRoot()
}
```

**Step 2: Run tests to verify they fail**

Run: `cd sdk/interbase/go && go test -v -run 'TestHasIC|TestHasBD|TestHasCompanion|TestGetBead|TestInEcosystem|TestInSprint|TestPhaseSet|TestEmitEvent|TestSessionStatus|TestPluginCachePath|TestEcosystemRoot' .`
Expected: FAIL — functions not defined

**Step 3: Write the implementation**

Create `sdk/interbase/go/interbase.go`:

```go
// Package interbase provides the Go SDK for Demarch plugin integration.
//
// All guard functions are fail-open: they return false when their dependency
// is missing. All action functions are silent no-ops when dependencies are
// absent. This ensures plugins work in both standalone and ecosystem modes.
package interbase

import (
	"encoding/json"
	"fmt"
	"os"
	"os/exec"
	"path/filepath"
	"regexp"
	"strings"
)

// --- Guards ---

// HasIC returns true if the ic (Intercore) CLI is on PATH.
func HasIC() bool {
	_, err := exec.LookPath("ic")
	return err == nil
}

// HasBD returns true if the bd (Beads) CLI is on PATH.
func HasBD() bool {
	_, err := exec.LookPath("bd")
	return err == nil
}

// HasCompanion returns true if the named plugin is in the Claude Code cache.
func HasCompanion(name string) bool {
	if name == "" {
		return false
	}
	home, err := os.UserHomeDir()
	if err != nil {
		return false
	}
	pattern := filepath.Join(home, ".claude", "plugins", "cache", "*", name, "*")
	matches, err := filepath.Glob(pattern)
	return err == nil && len(matches) > 0
}

// InEcosystem returns true if the centralized interbase install exists.
func InEcosystem() bool {
	path := os.Getenv("INTERMOD_LIB")
	if path == "" {
		home, err := os.UserHomeDir()
		if err != nil {
			return false
		}
		path = filepath.Join(home, ".intermod", "interbase", "interbase.sh")
	}
	_, err := os.Stat(path)
	return err == nil
}

// GetBead returns the current bead ID from $CLAVAIN_BEAD_ID, or empty string.
func GetBead() string {
	return os.Getenv("CLAVAIN_BEAD_ID")
}

// InSprint returns true if there is an active sprint context (bead + ic run).
func InSprint() bool {
	if GetBead() == "" {
		return false
	}
	if !HasIC() {
		return false
	}
	cmd := exec.Command("ic", "run", "current", "--project=.")
	cmd.Stdout = nil
	cmd.Stderr = nil
	return cmd.Run() == nil
}

// --- Actions ---
// Action functions return nothing — they are guaranteed no-ops when
// dependencies are absent. Returning error would create dead code at
// every call site (the spec says errors are never propagated).

// PhaseSet sets the phase on a bead. Silent no-op without bd.
func PhaseSet(bead, phase string, reason ...string) {
	if !HasBD() {
		return
	}
	cmd := exec.Command("bd", "set-state", bead, fmt.Sprintf("phase=%s", phase))
	cmd.Stdout = nil
	cmd.Stderr = os.Stderr
	if err := cmd.Run(); err != nil {
		fmt.Fprintf(os.Stderr, "[interbase] bd set-state failed: %v\n", err)
	}
}

// EmitEvent emits an event via ic. Silent no-op without ic.
func EmitEvent(runID, eventType string, payload ...string) {
	if !HasIC() {
		return
	}
	p := "{}"
	if len(payload) > 0 && payload[0] != "" {
		p = payload[0]
	}
	cmd := exec.Command("ic", "events", "emit", runID, eventType, fmt.Sprintf("--payload=%s", p))
	cmd.Stdout = nil
	cmd.Stderr = os.Stderr
	if err := cmd.Run(); err != nil {
		fmt.Fprintf(os.Stderr, "[interbase] ic events emit failed: %v\n", err)
	}
}

// SessionStatus returns the ecosystem status string.
func SessionStatus() string {
	var parts []string

	if HasBD() {
		parts = append(parts, "beads=active")
	} else {
		parts = append(parts, "beads=not-detected")
	}

	if HasIC() {
		cmd := exec.Command("ic", "run", "current", "--project=.")
		cmd.Stdout = nil
		cmd.Stderr = nil
		if cmd.Run() == nil {
			parts = append(parts, "ic=active")
		} else {
			parts = append(parts, "ic=not-initialized")
		}
	} else {
		parts = append(parts, "ic=not-detected")
	}

	return fmt.Sprintf("[interverse] %s", strings.Join(parts, " | "))
}

// --- Config + Discovery ---

// PluginCachePath returns the cache path for a named plugin.
// Returns empty string if not found.
func PluginCachePath(plugin string) string {
	if plugin == "" {
		return ""
	}
	home, err := os.UserHomeDir()
	if err != nil {
		return ""
	}
	pattern := filepath.Join(home, ".claude", "plugins", "cache", "*", plugin, "*")
	matches, err := filepath.Glob(pattern)
	if err != nil || len(matches) == 0 {
		return ""
	}
	// Return highest-versioned match (last after sort — Glob returns sorted)
	return matches[len(matches)-1]
}

// EcosystemRoot returns the Demarch monorepo root directory.
// Checks $DEMARCH_ROOT first, then walks up from CWD.
func EcosystemRoot() string {
	if root := os.Getenv("DEMARCH_ROOT"); root != "" {
		return root
	}
	dir, err := os.Getwd()
	if err != nil {
		return ""
	}
	for {
		if _, err := os.Stat(filepath.Join(dir, "sdk", "interbase")); err == nil {
			return dir
		}
		parent := filepath.Dir(dir)
		if parent == dir {
			break
		}
		dir = parent
	}
	return ""
}

// NudgeCompanion suggests installing a missing companion. Silent no-op if rate-limited.
// Rate-limited to 2 nudges per session with durable dismiss after 3 ignores.
func NudgeCompanion(companion, benefit string, plugin ...string) {
	if companion == "" {
		return
	}
	if HasCompanion(companion) {
		return
	}

	p := "unknown"
	if len(plugin) > 0 && plugin[0] != "" {
		p = plugin[0]
	}

	// Session budget check — sanitize session ID for safe filename
	sid := sanitizeID(os.Getenv("CLAUDE_SESSION_ID"))
	if sid == "" {
		sid = "unknown"
	}
	stateDir := filepath.Join(userConfigDir(), "interverse")
	sessionFile := filepath.Join(stateDir, fmt.Sprintf("nudge-session-%s.json", sid))

	count := readNudgeCount(sessionFile)
	if count >= 2 {
		return
	}

	// Durable dismissal check
	stateFile := filepath.Join(stateDir, "nudge-state.json")
	if isNudgeDismissed(stateFile, p, companion) {
		return
	}

	// Emit nudge
	fmt.Fprintf(os.Stderr, "[interverse] Tip: run /plugin install %s for %s.\n", companion, benefit)

	// Record
	writeNudgeCount(sessionFile, count+1)
	recordNudge(stateFile, p, companion)
}

// --- Internal helpers ---

// sanitizeID strips non-alphanumeric characters from an ID for safe filenames.
var safeIDRe = regexp.MustCompile(`[^a-zA-Z0-9_-]`)

func sanitizeID(id string) string {
	return safeIDRe.ReplaceAllString(id, "")
}

func userConfigDir() string {
	if d := os.Getenv("XDG_CONFIG_HOME"); d != "" {
		return d
	}
	home, _ := os.UserHomeDir()
	return filepath.Join(home, ".config")
}

// nudgeSession is the JSON shape for session nudge budget files.
type nudgeSession struct {
	Count int `json:"count"`
}

// nudgeEntry is the JSON shape for per-companion nudge state.
type nudgeEntry struct {
	Ignores   int  `json:"ignores"`
	Dismissed bool `json:"dismissed"`
}

func readNudgeCount(path string) int {
	data, err := os.ReadFile(path)
	if err != nil {
		return 0
	}
	var s nudgeSession
	if err := json.Unmarshal(data, &s); err != nil {
		return 0
	}
	return s.Count
}

func writeNudgeCount(path string, count int) {
	os.MkdirAll(filepath.Dir(path), 0755)
	data, _ := json.Marshal(nudgeSession{Count: count})
	os.WriteFile(path, data, 0644)
}

func isNudgeDismissed(stateFile, plugin, companion string) bool {
	data, err := os.ReadFile(stateFile)
	if err != nil {
		return false
	}
	var state map[string]nudgeEntry
	if err := json.Unmarshal(data, &state); err != nil {
		return false
	}
	key := plugin + ":" + companion
	entry, ok := state[key]
	return ok && entry.Dismissed
}

func recordNudge(stateFile, plugin, companion string) {
	os.MkdirAll(filepath.Dir(stateFile), 0755)
	key := plugin + ":" + companion

	var state map[string]nudgeEntry
	data, err := os.ReadFile(stateFile)
	if err != nil {
		state = make(map[string]nudgeEntry)
	} else {
		if err := json.Unmarshal(data, &state); err != nil {
			state = make(map[string]nudgeEntry)
		}
	}

	entry := state[key]
	entry.Ignores++
	if entry.Ignores >= 3 {
		entry.Dismissed = true
	}
	state[key] = entry

	out, _ := json.Marshal(state)
	os.WriteFile(stateFile, out, 0644)
}
```

**Step 4: Run tests to verify they pass**

Run: `cd sdk/interbase/go && go test -v -run 'TestHasIC|TestHasBD|TestHasCompanion|TestGetBead|TestInEcosystem|TestInSprint|TestPhaseSet|TestEmitEvent|TestSessionStatus|TestPluginCachePath|TestEcosystemRoot' .`
Expected: PASS (all tests)

**Step 5: Run existing tests to check no regressions**

Run: `cd sdk/interbase/go && go test ./...`
Expected: PASS (all 17 existing + new tests)

**Step 6: Commit**

```bash
git add sdk/interbase/go/interbase.go sdk/interbase/go/interbase_test.go
git commit -m "feat(interbase): add Go SDK guards, actions, and config functions"
```

---

### Task 3: Python SDK — Guards + Actions + Config

**Files:**
- Create: `sdk/interbase/python/pyproject.toml`
- Create: `sdk/interbase/python/interbase/__init__.py`
- Create: `sdk/interbase/python/interbase/guards.py`
- Create: `sdk/interbase/python/interbase/actions.py`
- Create: `sdk/interbase/python/interbase/config.py`
- Create: `sdk/interbase/python/interbase/nudge.py`
- Create: `sdk/interbase/python/tests/test_guards.py`
- Create: `sdk/interbase/python/tests/test_actions.py`
- Create: `sdk/interbase/python/tests/test_config.py`

**Step 1: Create pyproject.toml**

```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "interbase"
version = "2.0.0"
description = "Shared integration SDK for Demarch Interverse plugins"
requires-python = ">=3.11"
license = "MIT"

[project.optional-dependencies]
test = ["pytest>=7.0"]

[tool.hatch.build.targets.wheel]
packages = ["interbase"]
```

**Step 2: Write the failing tests**

Create `sdk/interbase/python/tests/test_guards.py`:

```python
"""Tests for interbase guard functions."""
import os
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest
from interbase import has_ic, has_bd, has_companion, in_ecosystem, get_bead, in_sprint


def test_has_ic_when_missing():
    with patch.dict(os.environ, {"PATH": ""}):
        assert has_ic() is False


def test_has_bd_when_missing():
    with patch.dict(os.environ, {"PATH": ""}):
        assert has_bd() is False


def test_has_companion_empty_name():
    assert has_companion("") is False


def test_has_companion_nonexistent():
    assert has_companion("this-plugin-does-not-exist-zzzz") is False


def test_get_bead_set():
    with patch.dict(os.environ, {"CLAVAIN_BEAD_ID": "iv-test123"}):
        assert get_bead() == "iv-test123"


def test_get_bead_unset():
    with patch.dict(os.environ, {"CLAVAIN_BEAD_ID": ""}, clear=False):
        assert get_bead() == ""


def test_in_ecosystem_file_exists():
    with tempfile.NamedTemporaryFile(suffix=".sh") as f:
        with patch.dict(os.environ, {"INTERMOD_LIB": f.name}):
            assert in_ecosystem() is True


def test_in_ecosystem_file_missing():
    with patch.dict(os.environ, {"INTERMOD_LIB": "/nonexistent/path/interbase.sh"}):
        assert in_ecosystem() is False


def test_in_sprint_no_bead():
    with patch.dict(os.environ, {"CLAVAIN_BEAD_ID": ""}, clear=False):
        assert in_sprint() is False


def test_in_sprint_no_ic():
    with patch.dict(os.environ, {"CLAVAIN_BEAD_ID": "iv-test", "PATH": ""}):
        assert in_sprint() is False
```

Create `sdk/interbase/python/tests/test_actions.py`:

```python
"""Tests for interbase action functions."""
import os
from unittest.mock import patch

from interbase import phase_set, emit_event, session_status


def test_phase_set_no_bd():
    with patch.dict(os.environ, {"PATH": ""}):
        # Should succeed silently (fail-open)
        phase_set("bead-123", "planned")


def test_emit_event_no_ic():
    with patch.dict(os.environ, {"PATH": ""}):
        emit_event("run-123", "test-event")


def test_session_status_format():
    status = session_status()
    assert status.startswith("[interverse]")
    assert "beads=" in status
    assert "ic=" in status
```

Create `sdk/interbase/python/tests/test_config.py`:

```python
"""Tests for interbase config functions."""
import os
from unittest.mock import patch

from interbase import plugin_cache_path, ecosystem_root


def test_plugin_cache_path_empty():
    assert plugin_cache_path("") == ""


def test_ecosystem_root_env_override():
    with patch.dict(os.environ, {"DEMARCH_ROOT": "/test/demarch"}):
        assert ecosystem_root() == "/test/demarch"


def test_ecosystem_root_unset():
    with patch.dict(os.environ, {"DEMARCH_ROOT": ""}, clear=False):
        # Should return something or empty — just shouldn't raise
        ecosystem_root()
```

**Step 3: Run tests to verify they fail**

Run: `cd sdk/interbase/python && uv run pytest tests/ -v`
Expected: FAIL — module `interbase` not found

**Step 4: Write the implementation**

Create `sdk/interbase/python/interbase/__init__.py`:

```python
"""Interbase — Shared integration SDK for Demarch Interverse plugins.

All guard functions are fail-open: they return False when their dependency
is missing. All action functions are silent no-ops when dependencies are
absent.
"""

from interbase.guards import (
    has_ic,
    has_bd,
    has_companion,
    in_ecosystem,
    get_bead,
    in_sprint,
)
from interbase.actions import phase_set, emit_event, session_status
from interbase.config import plugin_cache_path, ecosystem_root
from interbase.nudge import nudge_companion

__version__ = "2.0.0"

__all__ = [
    "has_ic",
    "has_bd",
    "has_companion",
    "in_ecosystem",
    "get_bead",
    "in_sprint",
    "phase_set",
    "emit_event",
    "session_status",
    "plugin_cache_path",
    "ecosystem_root",
    "nudge_companion",
]
```

Create `sdk/interbase/python/interbase/guards.py`:

```python
"""Guard functions — fail-open capability detection."""

from __future__ import annotations

import glob
import os
import shutil
import subprocess


def has_ic() -> bool:
    """Return True if the ic (Intercore) CLI is on PATH."""
    return shutil.which("ic") is not None


def has_bd() -> bool:
    """Return True if the bd (Beads) CLI is on PATH."""
    return shutil.which("bd") is not None


def has_companion(name: str) -> bool:
    """Return True if the named plugin is in the Claude Code cache."""
    if not name:
        return False
    home = os.path.expanduser("~")
    pattern = os.path.join(home, ".claude", "plugins", "cache", "*", name, "*")
    return len(glob.glob(pattern)) > 0


def in_ecosystem() -> bool:
    """Return True if the centralized interbase install exists."""
    path = os.environ.get("INTERMOD_LIB", "")
    if not path:
        home = os.path.expanduser("~")
        path = os.path.join(home, ".intermod", "interbase", "interbase.sh")
    return os.path.isfile(path)


def get_bead() -> str:
    """Return the current bead ID from $CLAVAIN_BEAD_ID, or empty string."""
    return os.environ.get("CLAVAIN_BEAD_ID", "")


def in_sprint() -> bool:
    """Return True if there is an active sprint context (bead + ic run)."""
    if not get_bead():
        return False
    if not has_ic():
        return False
    try:
        result = subprocess.run(
            ["ic", "run", "current", "--project=."],
            capture_output=True,
            timeout=5,
        )
        return result.returncode == 0
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        return False
```

Create `sdk/interbase/python/interbase/actions.py`:

```python
"""Action functions — silent no-ops when dependencies are absent."""

from __future__ import annotations

import subprocess
import sys

from interbase.guards import has_bd, has_ic


def phase_set(bead: str, phase: str, reason: str = "") -> None:
    """Set the phase on a bead via bd. Silent no-op without bd."""
    if not has_bd():
        return
    try:
        subprocess.run(
            ["bd", "set-state", bead, f"phase={phase}"],
            capture_output=True,
            timeout=10,
        )
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError) as exc:
        print(f"[interbase] bd set-state failed: {exc}", file=sys.stderr)


def emit_event(run_id: str, event_type: str, payload: str = "{}") -> None:
    """Emit an event via ic. Silent no-op without ic."""
    if not has_ic():
        return
    try:
        subprocess.run(
            ["ic", "events", "emit", run_id, event_type, f"--payload={payload}"],
            capture_output=True,
            timeout=10,
        )
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError) as exc:
        print(f"[interbase] ic events emit failed: {exc}", file=sys.stderr)


def session_status() -> str:
    """Return the ecosystem status string."""
    parts: list[str] = []

    if has_bd():
        parts.append("beads=active")
    else:
        parts.append("beads=not-detected")

    if has_ic():
        try:
            result = subprocess.run(
                ["ic", "run", "current", "--project=."],
                capture_output=True,
                timeout=5,
            )
            if result.returncode == 0:
                parts.append("ic=active")
            else:
                parts.append("ic=not-initialized")
        except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
            parts.append("ic=not-initialized")
    else:
        parts.append("ic=not-detected")

    return f"[interverse] {' | '.join(parts)}"
```

Create `sdk/interbase/python/interbase/config.py`:

```python
"""Config + discovery functions."""

from __future__ import annotations

import glob
import os


def plugin_cache_path(plugin: str) -> str:
    """Return the cache path for a named plugin. Empty if not found."""
    if not plugin:
        return ""
    home = os.path.expanduser("~")
    pattern = os.path.join(home, ".claude", "plugins", "cache", "*", plugin, "*")
    matches = sorted(glob.glob(pattern))
    return matches[-1] if matches else ""


def ecosystem_root() -> str:
    """Return the Demarch monorepo root. Checks $DEMARCH_ROOT then walks up."""
    root = os.environ.get("DEMARCH_ROOT", "")
    if root:
        return root
    try:
        d = os.getcwd()
    except OSError:
        return ""
    while True:
        if os.path.isdir(os.path.join(d, "sdk", "interbase")):
            return d
        parent = os.path.dirname(d)
        if parent == d:
            break
        d = parent
    return ""
```

Create `sdk/interbase/python/interbase/nudge.py`:

```python
"""Companion nudge protocol — rate-limited install suggestions."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

from interbase.guards import has_companion


def nudge_companion(
    companion: str, benefit: str, plugin: str = "unknown"
) -> None:
    """Suggest installing a missing companion. Silent no-op if rate-limited."""
    if not companion:
        return
    if has_companion(companion):
        return

    # Sanitize session ID for safe filenames
    import re
    sid = re.sub(r"[^a-zA-Z0-9_-]", "", os.environ.get("CLAUDE_SESSION_ID", "unknown"))
    state_dir = Path(
        os.environ.get("XDG_CONFIG_HOME", os.path.expanduser("~/.config"))
    ) / "interverse"
    session_file = state_dir / f"nudge-session-{sid}.json"
    state_file = state_dir / "nudge-state.json"

    # Session budget
    count = _read_session_count(session_file)
    if count >= 2:
        return

    # Durable dismissal
    if _is_dismissed(state_file, plugin, companion):
        return

    # Atomic dedup via mkdir — matches Bash pattern. First caller wins.
    state_dir.mkdir(parents=True, exist_ok=True)
    flag = state_dir / f".nudge-{sid}-{plugin}-{companion}"
    try:
        flag.mkdir()  # atomic: fails if already exists
    except FileExistsError:
        return  # another hook already emitted this nudge

    # Emit nudge
    print(
        f"[interverse] Tip: run /plugin install {companion} for {benefit}.",
        file=sys.stderr,
    )

    # Record state
    _write_session_count(session_file, count + 1)
    _record_nudge(state_file, plugin, companion)


def _read_session_count(path: Path) -> int:
    try:
        data = json.loads(path.read_text())
        return int(data.get("count", 0))
    except (FileNotFoundError, json.JSONDecodeError, ValueError):
        return 0


def _write_session_count(path: Path, count: int) -> None:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({"count": count}))
    except OSError:
        pass


def _is_dismissed(state_file: Path, plugin: str, companion: str) -> bool:
    try:
        data = json.loads(state_file.read_text())
        key = f"{plugin}:{companion}"
        entry = data.get(key, {})
        return entry.get("dismissed", False) is True
    except (FileNotFoundError, json.JSONDecodeError):
        return False


def _record_nudge(state_file: Path, plugin: str, companion: str) -> None:
    try:
        state_file.parent.mkdir(parents=True, exist_ok=True)
        key = f"{plugin}:{companion}"
        try:
            data = json.loads(state_file.read_text())
        except (FileNotFoundError, json.JSONDecodeError):
            data = {}
        entry = data.get(key, {"ignores": 0, "dismissed": False})
        entry["ignores"] = entry.get("ignores", 0) + 1
        if entry["ignores"] >= 3:
            entry["dismissed"] = True
        data[key] = entry
        state_file.write_text(json.dumps(data))
    except OSError:
        pass
```

**Step 5: Run tests to verify they pass**

Run: `cd sdk/interbase/python && uv run pytest tests/ -v`
Expected: PASS (all tests)

**Step 6: Commit**

```bash
git add sdk/interbase/python/
git commit -m "feat(interbase): add Python SDK — guards, actions, config, nudge"
```

---

### Task 4: Python MCP Contracts

**Files:**
- Create: `sdk/interbase/python/interbase/toolerror.py`
- Create: `sdk/interbase/python/interbase/mcputil.py`
- Create: `sdk/interbase/python/tests/test_toolerror.py`
- Create: `sdk/interbase/python/tests/test_mcputil.py`

**Step 1: Write the failing tests**

Create `sdk/interbase/python/tests/test_toolerror.py`:

```python
"""Tests for interbase.toolerror — wire format parity with Go."""
import json

from interbase.toolerror import ToolError, ERR_NOT_FOUND, ERR_TRANSIENT, ERR_INTERNAL


def test_new_error_has_correct_type():
    te = ToolError(ERR_NOT_FOUND, "agent 'x' not found")
    assert te.type == "NOT_FOUND"
    assert te.message == "agent 'x' not found"
    assert te.recoverable is False


def test_transient_default_recoverable():
    te = ToolError(ERR_TRANSIENT, "db busy")
    assert te.recoverable is True


def test_with_recoverable_override():
    te = ToolError(ERR_NOT_FOUND, "msg").with_recoverable(True)
    assert te.recoverable is True


def test_with_data():
    te = ToolError(ERR_NOT_FOUND, "msg").with_data(file="main.go")
    assert te.data == {"file": "main.go"}


def test_json_wire_format():
    te = ToolError(ERR_NOT_FOUND, "agent 'fd-safety' not registered")
    parsed = json.loads(te.json())
    assert parsed["type"] == "NOT_FOUND"
    assert parsed["message"] == "agent 'fd-safety' not registered"
    assert parsed["recoverable"] is False
    # data should be omitted when empty (match Go omitempty)
    assert "data" not in parsed or parsed["data"] == {}


def test_json_with_data():
    te = ToolError(ERR_NOT_FOUND, "msg").with_data(file="main.go")
    parsed = json.loads(te.json())
    assert parsed["data"] == {"file": "main.go"}


def test_str_format():
    te = ToolError(ERR_NOT_FOUND, "agent gone")
    assert str(te) == "[NOT_FOUND] agent gone"


def test_wrap_regular_exception():
    exc = ValueError("bad value")
    te = ToolError.wrap(exc)
    assert te.type == "INTERNAL"
    assert "bad value" in te.message


def test_wrap_tool_error():
    original = ToolError(ERR_NOT_FOUND, "gone")
    wrapped = ToolError.wrap(original)
    assert wrapped is original


def test_from_error_found():
    te = ToolError(ERR_NOT_FOUND, "gone")
    found = ToolError.from_error(te)
    assert found is te


def test_from_error_not_found():
    exc = ValueError("nope")
    assert ToolError.from_error(exc) is None
```

**Step 2: Run tests to verify they fail**

Run: `cd sdk/interbase/python && uv run pytest tests/test_toolerror.py -v`
Expected: FAIL — module not found

**Step 3: Write implementation**

Create `sdk/interbase/python/interbase/toolerror.py`:

```python
"""Structured MCP error contract — wire-format compatible with Go toolerror."""

from __future__ import annotations

import json
from typing import Any

# Error type constants — must match Go wire values exactly.
ERR_NOT_FOUND = "NOT_FOUND"
ERR_CONFLICT = "CONFLICT"
ERR_VALIDATION = "VALIDATION"
ERR_PERMISSION = "PERMISSION"
ERR_TRANSIENT = "TRANSIENT"
ERR_INTERNAL = "INTERNAL"

_DEFAULT_RECOVERABLE = {
    ERR_NOT_FOUND: False,
    ERR_CONFLICT: False,
    ERR_VALIDATION: False,
    ERR_PERMISSION: False,
    ERR_TRANSIENT: True,
    ERR_INTERNAL: False,
}


class ToolError(Exception):
    """Structured error for MCP tool handlers.

    Carries enough context for agents to make retry and fallback decisions.
    Wire format matches Go's toolerror.ToolError exactly.
    """

    def __init__(self, err_type: str, message: str, **data: Any) -> None:
        super().__init__(message)
        self.type: str = err_type
        self.message: str = message
        self.recoverable: bool = _DEFAULT_RECOVERABLE.get(err_type, False)
        self.data: dict[str, Any] = dict(data) if data else {}

    def with_recoverable(self, recoverable: bool) -> ToolError:
        """Override the recoverable flag. Returns self for chaining."""
        self.recoverable = recoverable
        return self

    def with_data(self, **kwargs: Any) -> ToolError:
        """Set data fields. Returns self for chaining."""
        self.data.update(kwargs)
        return self

    def json(self) -> str:
        """Serialize to JSON wire format matching Go's encoding/json output."""
        obj: dict[str, Any] = {
            "type": self.type,
            "message": self.message,
            "recoverable": self.recoverable,
        }
        if self.data:
            obj["data"] = self.data
        return json.dumps(obj, separators=(",", ":"))

    def __str__(self) -> str:
        return f"[{self.type}] {self.message}"

    @classmethod
    def from_error(cls, exc: BaseException) -> ToolError | None:
        """Extract a ToolError from an exception. Returns None if not one."""
        if isinstance(exc, ToolError):
            return exc
        return None

    @classmethod
    def wrap(cls, exc: BaseException) -> ToolError:
        """Convert any exception to ToolError. Passthrough if already one."""
        if isinstance(exc, ToolError):
            return exc
        return cls(ERR_INTERNAL, str(exc))
```

Create `sdk/interbase/python/interbase/mcputil.py`:

```python
"""MCP tool handler middleware — timing, error wrapping, metrics."""

from __future__ import annotations

import time
import traceback
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, Callable


@dataclass
class ToolStats:
    """Snapshot of metrics for a single tool."""

    calls: int = 0
    errors: int = 0
    total_duration_ns: int = 0

    @property
    def total_duration_s(self) -> float:
        return self.total_duration_ns / 1_000_000_000

    def __str__(self) -> str:
        return f"calls={self.calls} errors={self.errors} duration={self.total_duration_s:.3f}s"


@dataclass
class McpMetrics:
    """Collects per-tool call metrics for MCP servers."""

    _tools: dict[str, ToolStats] = field(default_factory=lambda: defaultdict(ToolStats))

    def tool_metrics(self) -> dict[str, ToolStats]:
        """Return a snapshot of metrics for all tools."""
        return dict(self._tools)

    def instrument(self, tool_name: str, handler: Callable) -> Callable:
        """Wrap a tool handler with timing, error counting, and error wrapping.

        Args:
            tool_name: The MCP tool name for metric grouping.
            handler: The original handler callable.

        Returns:
            Wrapped handler that collects metrics.
        """
        stats = self._tools[tool_name]

        def wrapper(*args: Any, **kwargs: Any) -> Any:
            stats.calls += 1
            start = time.monotonic_ns()
            try:
                result = handler(*args, **kwargs)
                return result
            except Exception:
                stats.errors += 1
                raise
            finally:
                stats.total_duration_ns += time.monotonic_ns() - start

        return wrapper
```

**Step 4: Run tests**

Run: `cd sdk/interbase/python && uv run pytest tests/test_toolerror.py tests/test_mcputil.py -v`
Expected: PASS

**Step 5: Update `__init__.py` exports**

Modify `sdk/interbase/python/interbase/__init__.py` — add toolerror and mcputil to exports:

```python
from interbase.toolerror import ToolError, ERR_NOT_FOUND, ERR_CONFLICT, ERR_VALIDATION, ERR_PERMISSION, ERR_TRANSIENT, ERR_INTERNAL
from interbase.mcputil import McpMetrics, ToolStats
```

Add to `__all__`:
```python
    "ToolError",
    "ERR_NOT_FOUND",
    "ERR_CONFLICT",
    "ERR_VALIDATION",
    "ERR_PERMISSION",
    "ERR_TRANSIENT",
    "ERR_INTERNAL",
    "McpMetrics",
    "ToolStats",
```

**Step 6: Commit**

```bash
git add sdk/interbase/python/interbase/toolerror.py sdk/interbase/python/interbase/mcputil.py sdk/interbase/python/tests/test_toolerror.py sdk/interbase/python/tests/test_mcputil.py sdk/interbase/python/interbase/__init__.py
git commit -m "feat(interbase): add Python MCP contracts — toolerror + mcputil"
```

---

### Task 5: YAML Conformance Test Suite

**Files:**
- Create: `sdk/interbase/tests/conformance/guards.yaml`
- Create: `sdk/interbase/tests/conformance/actions.yaml`
- Create: `sdk/interbase/tests/conformance/config.yaml`
- Create: `sdk/interbase/tests/conformance/mcp.yaml`
- Create: `sdk/interbase/tests/runners/run_bash.sh`
- Create: `sdk/interbase/tests/runners/run_go.sh`
- Create: `sdk/interbase/tests/runners/run_python.sh`
- Create: `sdk/interbase/tests/runners/conformance_go_test.go`
- Create: `sdk/interbase/tests/runners/conformance_python_test.py`

**Step 1: Write the YAML test cases**

Create `sdk/interbase/tests/conformance/guards.yaml`:

```yaml
# Conformance tests for guard functions.
# All guards are fail-open: they return false when the dependency is missing.
domain: guards

tests:
  - name: has_ic_when_missing
    setup:
      PATH: ""  # empty PATH ensures ic is not found
    call: has_ic
    expect: false

  - name: has_bd_when_missing
    setup:
      PATH: ""
    call: has_bd
    expect: false

  - name: has_companion_empty_name
    call: has_companion
    args: [""]
    expect: false

  - name: has_companion_nonexistent
    call: has_companion
    args: ["this-plugin-does-not-exist-zzzz"]
    expect: false

  - name: get_bead_set
    setup:
      CLAVAIN_BEAD_ID: "iv-test123"
    call: get_bead
    expect: "iv-test123"

  - name: get_bead_unset
    setup:
      CLAVAIN_BEAD_ID: ""
    call: get_bead
    expect: ""

  - name: in_ecosystem_file_missing
    setup:
      INTERMOD_LIB: "/nonexistent/path/interbase.sh"
    call: in_ecosystem
    expect: false

  - name: in_sprint_no_bead
    setup:
      CLAVAIN_BEAD_ID: ""
    call: in_sprint
    expect: false

  - name: in_sprint_no_ic
    setup:
      CLAVAIN_BEAD_ID: "iv-test"
      PATH: ""
    call: in_sprint
    expect: false
```

Create `sdk/interbase/tests/conformance/actions.yaml`:

```yaml
# Conformance tests for action functions.
# All actions are silent no-ops when dependencies are absent.
domain: actions

tests:
  - name: phase_set_without_bd
    setup:
      PATH: ""
    call: phase_set
    args: ["bead-123", "planned"]
    expect_error: false

  - name: emit_event_without_ic
    setup:
      PATH: ""
    call: emit_event
    args: ["run-123", "test-event"]
    expect_error: false

  - name: session_status_format
    call: session_status
    expect_contains: "[interverse]"
    expect_contains_all: ["beads=", "ic="]
```

Create `sdk/interbase/tests/conformance/config.yaml`:

```yaml
# Conformance tests for config + discovery functions.
domain: config

tests:
  - name: plugin_cache_path_empty
    call: plugin_cache_path
    args: [""]
    expect: ""

  - name: ecosystem_root_env_override
    setup:
      DEMARCH_ROOT: "/test/demarch"
    call: ecosystem_root
    expect: "/test/demarch"

  - name: ecosystem_root_unset_no_crash
    setup:
      DEMARCH_ROOT: ""
    call: ecosystem_root
    expect_no_error: true
```

Create `sdk/interbase/tests/conformance/mcp.yaml`:

```yaml
# Conformance tests for MCP contracts (Go + Python only).
# Bash is excluded — hooks don't run MCP servers.
domain: mcp
languages: [go, python]

tests:
  - name: toolerror_not_found_wire_format
    call: toolerror_new
    args: ["NOT_FOUND", "agent gone"]
    expect_json:
      type: "NOT_FOUND"
      message: "agent gone"
      recoverable: false

  - name: toolerror_transient_default_recoverable
    call: toolerror_new
    args: ["TRANSIENT", "db busy"]
    expect_json:
      type: "TRANSIENT"
      message: "db busy"
      recoverable: true

  - name: toolerror_with_data
    call: toolerror_new_with_data
    args: ["NOT_FOUND", "gone"]
    data:
      file: "main.go"
    expect_json:
      type: "NOT_FOUND"
      message: "gone"
      recoverable: false
      data:
        file: "main.go"

  - name: toolerror_str_format
    call: toolerror_str
    args: ["NOT_FOUND", "agent gone"]
    expect: "[NOT_FOUND] agent gone"

  - name: toolerror_wrap_passthrough
    call: toolerror_wrap_tool_error
    args: ["NOT_FOUND", "gone"]
    expect_json:
      type: "NOT_FOUND"
      message: "gone"

  - name: toolerror_wrap_generic
    call: toolerror_wrap_generic
    args: ["bad value"]
    expect_json:
      type: "INTERNAL"
      expect_message_contains: "bad value"
```

**Step 2: Write the per-language runners**

Create `sdk/interbase/tests/runners/run_bash.sh`:

```bash
#!/usr/bin/env bash
# Conformance test runner for Bash interbase SDK.
# Reads YAML test cases and executes against lib/interbase.sh.
#
# SECURITY: Uses allowlisted env vars instead of eval. YAML values are
# never executed as shell code. Pipe subshell avoided via process substitution.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SDK_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
CONFORMANCE_DIR="$SCRIPT_DIR/../conformance"

source "$SDK_ROOT/lib/interbase.sh"

pass=0
fail=0
skip=0

# Allowlisted env vars that setup blocks can set
declare -A ALLOWED_SETUP_VARS=([PATH]=1 [CLAVAIN_BEAD_ID]=1 [INTERMOD_LIB]=1 [DEMARCH_ROOT]=1)

run_test() {
    local yaml_file="$1"

    # Skip MCP tests for Bash
    local languages
    languages=$(grep '^languages:' "$yaml_file" 2>/dev/null || echo "")
    if [[ -n "$languages" ]] && [[ "$languages" != *"bash"* ]]; then
        echo "SKIP  $yaml_file (not for bash)"
        return
    fi

    # Parse tests using Python, output tab-delimited fields (no eval)
    # Format: name\tcall\targ0\tsetup_json\texpect_type\texpect_value
    while IFS=$'\t' read -r name call arg0 setup_json expect_type expect_value; do
        # Save and apply setup via allowlist
        local old_path="${PATH}" old_bead="${CLAVAIN_BEAD_ID:-}" old_intermod="${INTERMOD_LIB:-}" old_demarch="${DEMARCH_ROOT:-}"
        if [[ -n "$setup_json" && "$setup_json" != "{}" ]]; then
            while IFS=$'\t' read -r skey sval; do
                if [[ -n "${ALLOWED_SETUP_VARS[$skey]+x}" ]]; then
                    export "$skey=$sval"
                fi
            done < <(echo "$setup_json" | python3 -c "
import json, sys
d = json.load(sys.stdin)
for k, v in d.items():
    print(f'{k}\t{v}')
")
        fi

        # Execute
        local result="" exit_code=0
        case "$call" in
            has_ic) ib_has_ic; exit_code=$?; result=$( (( exit_code == 0 )) && echo "true" || echo "false") ;;
            has_bd) ib_has_bd; exit_code=$?; result=$( (( exit_code == 0 )) && echo "true" || echo "false") ;;
            has_companion) ib_has_companion "$arg0"; exit_code=$?; result=$( (( exit_code == 0 )) && echo "true" || echo "false") ;;
            get_bead) result=$(ib_get_bead) ;;
            in_ecosystem) ib_in_ecosystem; exit_code=$?; result=$( (( exit_code == 0 )) && echo "true" || echo "false") ;;
            in_sprint) ib_in_sprint; exit_code=$?; result=$( (( exit_code == 0 )) && echo "true" || echo "false") ;;
            phase_set) ib_phase_set "bead-123" "planned"; result="no_error" ;;
            emit_event) ib_emit_event "run-123" "test-event"; result="no_error" ;;
            session_status) result=$(ib_session_status 2>&1) ;;
            plugin_cache_path) result=$(ib_plugin_cache_path "$arg0" 2>/dev/null || echo "") ;;
            ecosystem_root) result=$(ib_ecosystem_root 2>/dev/null || echo "") ;;
            *) echo "SKIP  $name (unknown: $call)"; skip=$((skip + 1)); continue ;;
        esac

        # Restore
        export PATH="$old_path" CLAVAIN_BEAD_ID="$old_bead" INTERMOD_LIB="$old_intermod" DEMARCH_ROOT="$old_demarch"

        # Assert
        case "$expect_type" in
            exact)
                if [[ "$result" == "$expect_value" ]]; then
                    echo "PASS  $name"; pass=$((pass + 1))
                else
                    echo "FAIL  $name: got '$result', expected '$expect_value'"; fail=$((fail + 1))
                fi ;;
            contains)
                if [[ "$result" == *"$expect_value"* ]]; then
                    echo "PASS  $name"; pass=$((pass + 1))
                else
                    echo "FAIL  $name: '$result' missing '$expect_value'"; fail=$((fail + 1))
                fi ;;
            no_error) echo "PASS  $name"; pass=$((pass + 1)) ;;
            skip) skip=$((skip + 1)) ;;
        esac
    done < <(python3 -c "
import yaml, json, sys
with open('$yaml_file') as f:
    data = yaml.safe_load(f)
for t in data.get('tests', []):
    name = t.get('name', '')
    call = t.get('call', '')
    args = t.get('args', [''])
    arg0 = str(args[0]) if args else ''
    setup = json.dumps(t.get('setup', {}))
    if 'expect' in t:
        etype, evalue = 'exact', str(t['expect'])
    elif 'expect_error' in t:
        etype, evalue = ('no_error', '') if not t['expect_error'] else ('error', '')
    elif 'expect_contains' in t:
        etype, evalue = 'contains', t['expect_contains']
    elif 'expect_no_error' in t:
        etype, evalue = 'no_error', ''
    else:
        etype, evalue = 'skip', ''
    print(f'{name}\t{call}\t{arg0}\t{setup}\t{etype}\t{evalue}')
")
}

for yaml_file in "$CONFORMANCE_DIR"/*.yaml; do
    run_test "$yaml_file"
done

echo ""
echo "Results: $pass passed, $fail failed, $skip skipped"
[[ "$fail" -eq 0 ]]
```

Create `sdk/interbase/tests/runners/run_go.sh`:

```bash
#!/usr/bin/env bash
# Conformance test runner for Go interbase SDK.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SDK_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

cd "$SDK_ROOT/go"
go test -v -run TestConformance ./... -tags conformance 2>&1 || exit 1
echo "Go conformance: PASS"
```

Create `sdk/interbase/tests/runners/run_python.sh`:

```bash
#!/usr/bin/env bash
# Conformance test runner for Python interbase SDK.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SDK_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

cd "$SDK_ROOT/python"
uv run pytest tests/test_conformance.py -v 2>&1 || exit 1
echo "Python conformance: PASS"
```

**Step 3: Write Go conformance bridge test**

Create `sdk/interbase/go/conformance_test.go`:

```go
//go:build conformance

package interbase

import (
	"encoding/json"
	"os"
	"path/filepath"
	"strings"
	"testing"

	"gopkg.in/yaml.v3"
)

type conformanceSuite struct {
	Domain    string            `yaml:"domain"`
	Languages []string          `yaml:"languages,omitempty"`
	Tests     []conformanceTest `yaml:"tests"`
}

type conformanceTest struct {
	Name             string            `yaml:"name"`
	Setup            map[string]string `yaml:"setup,omitempty"`
	Call             string            `yaml:"call"`
	Args             []string          `yaml:"args,omitempty"`
	Expect           any               `yaml:"expect,omitempty"`
	ExpectError      *bool             `yaml:"expect_error,omitempty"`
	ExpectContains   string            `yaml:"expect_contains,omitempty"`
	ExpectNoError    *bool             `yaml:"expect_no_error,omitempty"`
}

func TestConformance(t *testing.T) {
	confDir := filepath.Join("..", "tests", "conformance")
	files, err := filepath.Glob(filepath.Join(confDir, "*.yaml"))
	if err != nil {
		t.Fatalf("glob conformance dir: %v", err)
	}

	for _, f := range files {
		data, err := os.ReadFile(f)
		if err != nil {
			t.Fatalf("read %s: %v", f, err)
		}
		var suite conformanceSuite
		if err := yaml.Unmarshal(data, &suite); err != nil {
			t.Fatalf("parse %s: %v", f, err)
		}

		// Skip if language-restricted and Go is not listed
		if len(suite.Languages) > 0 {
			found := false
			for _, l := range suite.Languages {
				if l == "go" {
					found = true
					break
				}
			}
			if !found {
				t.Logf("SKIP %s (not for go)", f)
				continue
			}
		}

		for _, tc := range suite.Tests {
			t.Run(tc.Name, func(t *testing.T) {
				// Apply setup
				for k, v := range tc.Setup {
					t.Setenv(k, v)
				}
				runConformanceCall(t, tc)
			})
		}
	}
}

func runConformanceCall(t *testing.T, tc conformanceTest) {
	t.Helper()

	switch tc.Call {
	case "has_ic":
		got := HasIC()
		assertBool(t, got, tc.Expect)
	case "has_bd":
		got := HasBD()
		assertBool(t, got, tc.Expect)
	case "has_companion":
		arg := ""
		if len(tc.Args) > 0 {
			arg = tc.Args[0]
		}
		got := HasCompanion(arg)
		assertBool(t, got, tc.Expect)
	case "get_bead":
		got := GetBead()
		assertString(t, got, tc.Expect)
	case "in_ecosystem":
		got := InEcosystem()
		assertBool(t, got, tc.Expect)
	case "in_sprint":
		got := InSprint()
		assertBool(t, got, tc.Expect)
	case "phase_set":
		err := PhaseSet("bead-123", "planned")
		if tc.ExpectError != nil && !*tc.ExpectError && err != nil {
			t.Errorf("expected no error, got %v", err)
		}
	case "emit_event":
		err := EmitEvent("run-123", "test-event")
		if tc.ExpectError != nil && !*tc.ExpectError && err != nil {
			t.Errorf("expected no error, got %v", err)
		}
	case "session_status":
		got := SessionStatus()
		if tc.ExpectContains != "" && !strings.Contains(got, tc.ExpectContains) {
			t.Errorf("got %q, want contains %q", got, tc.ExpectContains)
		}
	case "plugin_cache_path":
		arg := ""
		if len(tc.Args) > 0 {
			arg = tc.Args[0]
		}
		got := PluginCachePath(arg)
		assertString(t, got, tc.Expect)
	case "ecosystem_root":
		got := EcosystemRoot()
		if tc.Expect != nil {
			assertString(t, got, tc.Expect)
		}
	default:
		t.Skipf("unknown function: %s", tc.Call)
	}
}

func assertBool(t *testing.T, got bool, expect any) {
	t.Helper()
	if expect == nil {
		return
	}
	var want bool
	switch v := expect.(type) {
	case bool:
		want = v
	case string:
		want = v == "true"
	}
	if got != want {
		t.Errorf("got %v, want %v", got, want)
	}
}

func assertString(t *testing.T, got string, expect any) {
	t.Helper()
	if expect == nil {
		return
	}
	want := ""
	switch v := expect.(type) {
	case string:
		want = v
	default:
		b, _ := json.Marshal(v)
		want = string(b)
	}
	if got != want {
		t.Errorf("got %q, want %q", got, want)
	}
}
```

Add `gopkg.in/yaml.v3` to `go.mod` (already an indirect dependency).

**Step 4: Write Python conformance bridge test**

Create `sdk/interbase/python/tests/test_conformance.py`:

```python
"""Conformance test runner — reads YAML test cases, runs against Python SDK."""

from __future__ import annotations

import json
import os
from pathlib import Path
from unittest.mock import patch

import pytest
import yaml

import interbase
from interbase.toolerror import ToolError

CONFORMANCE_DIR = Path(__file__).resolve().parent.parent.parent / "tests" / "conformance"


def load_suites():
    """Load all YAML conformance suites."""
    suites = []
    for f in sorted(CONFORMANCE_DIR.glob("*.yaml")):
        data = yaml.safe_load(f.read_text())
        languages = data.get("languages", [])
        if languages and "python" not in languages:
            continue
        for tc in data.get("tests", []):
            suites.append(pytest.param(tc, id=tc["name"]))
    return suites


@pytest.mark.parametrize("tc", load_suites())
def test_conformance(tc):
    setup = tc.get("setup", {})
    env_patch = {}
    for k, v in setup.items():
        env_patch[k] = str(v)

    with patch.dict(os.environ, env_patch, clear=False):
        call = tc["call"]
        args = tc.get("args", [])

        if call in ("has_ic", "has_bd", "has_companion", "in_ecosystem",
                     "get_bead", "in_sprint", "phase_set", "emit_event",
                     "session_status", "plugin_cache_path", "ecosystem_root"):
            func = getattr(interbase, call)
            result = func(*args)
        elif call == "toolerror_new":
            te = ToolError(args[0], args[1])
            result = json.loads(te.json())
        elif call == "toolerror_new_with_data":
            te = ToolError(args[0], args[1]).with_data(**tc.get("data", {}))
            result = json.loads(te.json())
        elif call == "toolerror_str":
            te = ToolError(args[0], args[1])
            result = str(te)
        elif call == "toolerror_wrap_tool_error":
            te = ToolError(args[0], args[1])
            result = json.loads(ToolError.wrap(te).json())
        elif call == "toolerror_wrap_generic":
            result = json.loads(ToolError.wrap(ValueError(args[0])).json())
        else:
            pytest.skip(f"unknown function: {call}")
            return

        # Assert
        if "expect" in tc:
            expected = tc["expect"]
            if isinstance(expected, bool):
                assert result is expected, f"got {result!r}, want {expected!r}"
            else:
                assert result == expected, f"got {result!r}, want {expected!r}"
        if "expect_error" in tc and not tc["expect_error"]:
            pass  # no error raised = pass
        if "expect_contains" in tc:
            assert tc["expect_contains"] in str(result)
        if "expect_json" in tc:
            expected = tc["expect_json"]
            for k, v in expected.items():
                if k == "expect_message_contains":
                    assert v in result.get("message", "")
                else:
                    assert result.get(k) == v, f"key {k}: got {result.get(k)!r}, want {v!r}"
```

Add `pyyaml` to `pyproject.toml` test dependencies:

```toml
[project.optional-dependencies]
test = ["pytest>=7.0", "pyyaml>=6.0"]
```

**Step 5: Run all conformance tests**

Run: `bash sdk/interbase/tests/runners/run_go.sh`
Run: `bash sdk/interbase/tests/runners/run_python.sh`
Run: `bash sdk/interbase/tests/runners/run_bash.sh`
Expected: All PASS

**Step 6: Commit**

```bash
git add sdk/interbase/tests/
git add sdk/interbase/go/conformance_test.go
git add sdk/interbase/python/tests/test_conformance.py
git add sdk/interbase/python/pyproject.toml
git commit -m "feat(interbase): add YAML conformance test suite with per-language runners"
```

---

### Task 6: Expand Bash SDK Config Functions

**Files:**
- Modify: `sdk/interbase/lib/interbase.sh`
- Modify: `sdk/interbase/templates/interbase-stub.sh`
- Create: `sdk/interbase/tests/test-config.sh`

**Step 1: Write failing tests**

Create `sdk/interbase/tests/test-config.sh`:

```bash
#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
source "$SCRIPT_DIR/../lib/interbase.sh"

pass=0 fail=0

assert_eq() {
    local label="$1" got="$2" want="$3"
    if [[ "$got" == "$want" ]]; then
        echo "PASS  $label"
        pass=$((pass + 1))
    else
        echo "FAIL  $label: got '$got', want '$want'"
        fail=$((fail + 1))
    fi
}

assert_nonempty() {
    local label="$1" got="$2"
    if [[ -n "$got" ]]; then
        echo "PASS  $label"
        pass=$((pass + 1))
    else
        echo "FAIL  $label: got empty string"
        fail=$((fail + 1))
    fi
}

assert_empty() {
    local label="$1" got="$2"
    if [[ -z "$got" ]]; then
        echo "PASS  $label"
        pass=$((pass + 1))
    else
        echo "FAIL  $label: got '$got', want empty"
        fail=$((fail + 1))
    fi
}

# Test ib_plugin_cache_path
assert_empty "plugin_cache_path empty name" "$(ib_plugin_cache_path "")"
assert_empty "plugin_cache_path nonexistent" "$(ib_plugin_cache_path "this-plugin-does-not-exist-zzzz")"

# Test with a plugin we know exists (clavain)
if compgen -G "${HOME}/.claude/plugins/cache/*/clavain/*" &>/dev/null; then
    assert_nonempty "plugin_cache_path clavain" "$(ib_plugin_cache_path "clavain")"
fi

# Test ib_ecosystem_root with env override
export DEMARCH_ROOT="/test/demarch"
assert_eq "ecosystem_root env override" "$(ib_ecosystem_root)" "/test/demarch"
unset DEMARCH_ROOT

# Test ib_ecosystem_root walk-up (from inside SDK dir, should find monorepo root)
pushd "$SCRIPT_DIR" >/dev/null
result=$(ib_ecosystem_root)
popd >/dev/null
# We're inside sdk/interbase/tests — walking up should find parent with sdk/interbase
if [[ -n "$result" ]]; then
    assert_nonempty "ecosystem_root walk-up" "$result"
fi

echo ""
echo "Config tests: $pass passed, $fail failed"
[[ "$fail" -eq 0 ]]
```

**Step 2: Run test to verify it fails**

Run: `bash sdk/interbase/tests/test-config.sh`
Expected: FAIL — `ib_plugin_cache_path: command not found`

**Step 3: Add functions to interbase.sh**

Append to `sdk/interbase/lib/interbase.sh` before the end (after `ib_nudge_companion`):

```bash
# --- Config + Discovery ---

ib_plugin_cache_path() {
    local plugin="${1:-}"
    [[ -n "$plugin" ]] || return 0
    local matches
    matches=$(compgen -G "${HOME}/.claude/plugins/cache/*/${plugin}/*" 2>/dev/null | sort | tail -1)
    echo "${matches:-}"
}

ib_ecosystem_root() {
    if [[ -n "${DEMARCH_ROOT:-}" ]]; then
        echo "$DEMARCH_ROOT"
        return
    fi
    local dir
    dir="$(pwd)"
    while [[ "$dir" != "/" ]]; do
        if [[ -d "$dir/sdk/interbase" ]]; then
            echo "$dir"
            return
        fi
        dir="$(dirname "$dir")"
    done
}
```

**Step 4: Update the stub**

Add no-op versions to `sdk/interbase/templates/interbase-stub.sh`:

After `ib_session_status()  { return 0; }` add:

```bash
ib_plugin_cache_path() { echo ""; }
ib_ecosystem_root()    { echo ""; }
```

**Step 5: Run tests**

Run: `bash sdk/interbase/tests/test-config.sh`
Expected: PASS

Run: `bash sdk/interbase/tests/test-guards.sh`
Expected: PASS (16 tests — no regressions)

**Step 6: Commit**

```bash
git add sdk/interbase/lib/interbase.sh sdk/interbase/templates/interbase-stub.sh sdk/interbase/tests/test-config.sh
git commit -m "feat(interbase): add Bash config functions — plugin_cache_path, ecosystem_root"
```

---

### Task 7: First Adopter Migration — Intermap Go MCP Server (toolerror + mcputil)

> **Note (from flux-drive review):** Intermap's MCP server does NOT have ad-hoc
> `exec.LookPath("ic")` calls to replace. The migration focus is adopting
> `toolerror` + `mcputil` in its existing MCP tool handlers — replacing flat
> error strings with structured errors and adding metrics middleware.

**Files:**
- Modify: `interverse/intermap/cmd/intermap-mcp/main.go`
- Modify: `interverse/intermap/go.mod` (add interbase replace directive)

**Step 1: Read the intermap MCP server entrypoint**

Read: `interverse/intermap/cmd/intermap-mcp/main.go`

Identify MCP tool handlers that return flat error strings or `mcp.NewToolResultError("...")`.

**Step 2: Add interbase dependency**

Add to `interverse/intermap/go.mod`:

```
require github.com/mistakeknot/interbase v0.0.0
replace github.com/mistakeknot/interbase => ../../../sdk/interbase/go
```

**Step 3: Add mcputil middleware**

In the server creation code, add metrics middleware:

```go
import "github.com/mistakeknot/interbase/mcputil"

metrics := mcputil.NewMetrics()
s := server.NewMCPServer("intermap", version,
    server.WithToolHandlerMiddleware(metrics.Instrument()),
)
```

**Step 4: Replace flat error strings with toolerror**

In tool handlers, replace:
```go
return mcp.NewToolResultError("project not found"), nil
```
with:
```go
return mcputil.NotFoundError("project %q not found", name)
```

Replace generic error wrapping with `mcputil.WrapError(err)`.

**Step 5: Verify the server builds and tests pass**

Run: `cd interverse/intermap && go build ./cmd/intermap-mcp/`
Run: `cd interverse/intermap && go test ./...`
Expected: PASS

**Step 6: Commit**

```bash
git add interverse/intermap/
git commit -m "refactor(intermap): adopt interbase toolerror + mcputil for structured MCP errors"
```

---

### Task 8: First Adopter Migration — Python Hook (interflux session-start)

> **Note (from flux-drive review):** detect-domains.py does not have ad-hoc
> `shutil.which("ic")` calls to replace. The migration focus is demonstrating
> Python SDK usage in a hook context — the thin Bash wrapper pattern for
> Python hooks, using guards and session_status from Python.

**Files:**
- Create: `interverse/interflux/hooks/python-hook-example.py` (reference implementation)
- Create: `sdk/interbase/docs/migration-guide.md`

**Step 1: Write a Python hook reference implementation**

Create `interverse/interflux/hooks/python-hook-example.py`:

```python
#!/usr/bin/env python3
"""Example Python hook using interbase SDK.

Demonstrates the thin Bash wrapper → Python hook pattern.
The Bash hook file sources interbase-stub.sh then delegates to this script.
"""
try:
    import interbase
except ImportError:
    # Standalone mode — no SDK available, exit cleanly
    exit(0)

def main():
    # Guards — check what's available
    if interbase.in_ecosystem():
        status = interbase.session_status()
        # Use status for conditional hook behavior

    # Actions — safe to call even without deps
    bead = interbase.get_bead()
    if bead:
        interbase.phase_set(bead, "hook-fired")

if __name__ == "__main__":
    main()
```

**Step 2: Write migration guide**

Create `sdk/interbase/docs/migration-guide.md` documenting:
- How to add interbase Go SDK to an MCP server (replace directive, middleware, error helpers)
- How to add interbase Python SDK to a hook (thin wrapper pattern, try/except import)
- How to add interbase Python SDK to a standalone script (fail-open import)
- Before/after code examples from Task 7

**Step 3: Commit**

```bash
git add interverse/interflux/hooks/python-hook-example.py sdk/interbase/docs/migration-guide.md
git commit -m "docs(interbase): add migration guide and Python hook reference implementation"
```

---

### Task 9: Documentation + Version Bump

**Files:**
- Modify: `sdk/interbase/AGENTS.md`
- Modify: `sdk/interbase/CLAUDE.md`
- Modify: `sdk/interbase/lib/VERSION`
- Modify: `sdk/interbase/go/go.mod` (if needed for yaml dependency)
- Create: `sdk/interbase/go/README.md` (update)

**Step 1: Update VERSION**

Write `2.0.0` to `sdk/interbase/lib/VERSION`.

**Step 2: Update AGENTS.md**

Add sections for:
- Python SDK file structure
- Python function reference (guards, actions, config, toolerror, mcputil)
- Conformance test instructions
- Updated adopter table (add intermap Go + intersense Python)

**Step 3: Update CLAUDE.md**

Add quick commands for Python:

```bash
# Run Python tests
cd python && uv run pytest tests/ -v

# Run conformance tests (all languages)
bash tests/runners/run_bash.sh
bash tests/runners/run_go.sh
bash tests/runners/run_python.sh
```

**Step 4: Commit**

```bash
git add sdk/interbase/AGENTS.md sdk/interbase/CLAUDE.md sdk/interbase/lib/VERSION sdk/interbase/go/README.md
git commit -m "docs(interbase): update docs for v2.0.0 multi-language SDK"
```
