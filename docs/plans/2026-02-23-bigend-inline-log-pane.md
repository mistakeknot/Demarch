# Bigend Inline Log Pane Implementation Plan
**Phase:** executing (as of 2026-02-23T20:06:47Z)

> **For Claude:** REQUIRED SUB-SKILL: Use clavain:executing-plans to implement this plan task-by-task.

**Goal:** Wire LogHandler + LogPane into the standalone Bigend entry points so logs are visible during TUI use and dumped to scrollback on exit, and add panic recovery to all TUI entry points.

**Architecture:** The unified `autarch tui` already has LogHandler, LogPane, scrollback dump, and inline mode. The standalone `cmd/bigend/main.go` and the `runBigendTUI()` path in `cmd/autarch/main.go` still use `slog.TextHandler` with suppressed log levels and no scrollback dump. We bring these up to parity with the unified app, and add panic recovery that's missing everywhere.

**Tech Stack:** Go, Bubble Tea, slog, `pkg/tui` (LogHandler, LogPane)

---

### Task 1: Wire LogHandler into standalone `cmd/bigend/main.go`

**Files:**
- Modify: `apps/autarch/cmd/bigend/main.go:40-49` (logging setup)
- Modify: `apps/autarch/cmd/bigend/main.go:126-134` (runTUI function)
- Modify: `apps/autarch/cmd/bigend/main.go:1-26` (imports)

**Step 1: Update imports**

Add `pkgtui` import to the import block:

```go
pkgtui "github.com/mistakeknot/autarch/pkg/tui"
```

**Step 2: Replace TextHandler with LogHandler in main()**

Replace lines 40-49:

```go
// Setup logging
logLevel := slog.LevelInfo
if *tuiMode {
    // Suppress logs in TUI mode to avoid interfering with display
    logLevel = slog.LevelError
}
logger := slog.New(slog.NewTextHandler(os.Stdout, &slog.HandlerOptions{
    Level: logLevel,
}))
slog.SetDefault(logger)
```

With:

```go
// Setup logging — TUI mode routes all levels through LogHandler to the log pane;
// non-TUI mode uses TextHandler on stdout.
var logHandler *pkgtui.LogHandler
if *tuiMode {
    logHandler = pkgtui.NewLogHandler(slog.LevelDebug)
    slog.SetDefault(slog.New(logHandler))
} else {
    slog.SetDefault(slog.New(slog.NewTextHandler(os.Stdout, &slog.HandlerOptions{
        Level: slog.LevelInfo,
    })))
}
```

**Step 3: Wire LogHandler into runTUI and add scrollback dump**

Replace the `runTUI` function:

```go
func runTUI(agg *aggregator.Aggregator, logHandler *pkgtui.LogHandler) {
    m := tui.New(agg, buildInfoString())
    p := tea.NewProgram(m, tea.WithAltScreen())

    if logHandler != nil {
        logHandler.SetProgram(p)
        defer logHandler.Close()
    }

    if _, err := p.Run(); err != nil {
        fmt.Printf("Error running TUI: %v\n", err)
        os.Exit(1)
    }
}
```

**Step 4: Update the call site to pass logHandler**

In `main()`, change `runTUI(agg)` to `runTUI(agg, logHandler)`.

**Step 5: Run existing tests to verify no regression**

Run: `cd /home/mk/projects/Demarch/apps/autarch && go build ./cmd/bigend/`
Expected: builds without errors

**Step 6: Commit**

```bash
git add apps/autarch/cmd/bigend/main.go
git commit -m "feat(bigend): wire LogHandler into standalone entry point

Route slog messages through LogHandler in TUI mode so logs are
visible via the Bubble Tea message system instead of being suppressed."
```

---

### Task 2: Wire LogHandler into deprecated `runBigendTUI()` in `cmd/autarch/main.go`

**Files:**
- Modify: `apps/autarch/cmd/autarch/main.go:374-385` (runBigendTUI function)
- Modify: `apps/autarch/cmd/autarch/main.go:275-283` (logging setup in bigendCmd)
- Modify: `apps/autarch/cmd/autarch/main.go:333-334` (call site)

**Step 1: Update logging setup in bigendCmd RunE**

Replace lines 275-283:

```go
// Setup logging
logLevel := slog.LevelInfo
if tuiMode {
    logLevel = slog.LevelError
}
logger := slog.New(slog.NewTextHandler(os.Stdout, &slog.HandlerOptions{
    Level: logLevel,
}))
slog.SetDefault(logger)
```

With:

```go
// Setup logging — TUI mode routes through LogHandler to log pane.
// TODO(bigend-deprecation): Remove this block when the bigend --tui path is deleted.
// Duplicates the logging setup in cmd/bigend/main.go intentionally (deprecated code
// does not justify a new abstraction).
var logHandler *pkgtui.LogHandler
if tuiMode {
    logHandler = pkgtui.NewLogHandler(slog.LevelDebug)
    slog.SetDefault(slog.New(logHandler))
} else {
    slog.SetDefault(slog.New(slog.NewTextHandler(os.Stdout, &slog.HandlerOptions{
        Level: slog.LevelInfo,
    })))
}
```

**Step 2: Update call site and function signature**

Change `return runBigendTUI(agg)` to `return runBigendTUI(agg, logHandler)`.

**Step 3: Update runBigendTUI function**

Replace lines 374-385:

```go
func runBigendTUI(agg *aggregator.Aggregator, logHandler *pkgtui.LogHandler) error {
    fmt.Fprintln(os.Stderr, "\033[33m⚠ Deprecation warning: bigend --tui is deprecated.\033[0m")
    fmt.Fprintln(os.Stderr, "  Use: autarch tui --tool=bigend")
    fmt.Fprintln(os.Stderr, "  Web server mode (bigend without --tui) remains available.")
    fmt.Fprintln(os.Stderr)

    m := bigendTui.New(agg, buildInfoString())
    p := tea.NewProgram(m, tea.WithAltScreen())

    if logHandler != nil {
        logHandler.SetProgram(p)
        defer logHandler.Close()
    }

    _, err := p.Run()
    return err
}
```

**Step 4: Verify pkgtui import exists**

Check that `pkgtui "github.com/mistakeknot/autarch/pkg/tui"` is already imported in `cmd/autarch/main.go`. If not, add it.

**Step 5: Build check**

Run: `cd /home/mk/projects/Demarch/apps/autarch && go build ./cmd/autarch/`
Expected: builds without errors

**Step 6: Commit**

```bash
git add apps/autarch/cmd/autarch/main.go
git commit -m "feat(bigend): wire LogHandler into deprecated bigend --tui path

Parity with unified autarch tui entry point. Route slog through
LogHandler instead of suppressing to LevelError."
```

---

### Task 3: Add LogPane integration to Bigend's standalone TUI model

**Files:**
- Modify: `apps/autarch/internal/bigend/tui/model.go:254-286` (Model struct)
- Modify: `apps/autarch/internal/bigend/tui/model.go:352-423` (New function)
- Modify: `apps/autarch/internal/bigend/tui/model.go:470-861` (Update function)
- Modify: `apps/autarch/internal/bigend/tui/model.go:1012-1063` (View function)
- Modify: `apps/autarch/internal/bigend/tui/model.go:1104-1135` (footer)
- Modify: `apps/autarch/internal/bigend/tui/model.go:1152-1187` (applyResize)

The Bigend standalone TUI (`internal/bigend/tui/model.go`) does NOT have a LogPane — unlike UnifiedApp. We need to add it.

**Step 1: Add LogPane fields to Model struct**

Add after the `dashCache` field (line 285):

```go
logPane        *shared.LogPane
logPaneVisible bool
logPaneAutoShown bool
```

**Step 2: Initialize LogPane in New()**

Add to the Model return in `New()`, after `dashCache: newSectionCache()`:

```go
logPane: shared.NewLogPane(),
```

**Step 3: Add LogPane getter**

Add after the `New()` function:

```go
// LogPane returns the log pane for scrollback dump on exit.
func (m *Model) LogPane() *shared.LogPane {
    return m.logPane
}
```

**Step 4: Handle LogBatchMsg in Update()**

Route `LogBatchMsg` **before** the main `switch msg := msg.(type)` block (matches UnifiedApp convention — log messages should never be swallowed by downstream handlers):

```go
// At the top of Update(), before the main switch:
if batch, ok := msg.(shared.LogBatchMsg); ok {
    cmd := m.logPane.Update(batch)
    if !m.logPaneVisible {
        m.logPaneVisible = true
        m.logPaneAutoShown = true
    }
    return m, cmd
}
```

**Step 5: Add `ctrl+l` key toggle for log pane**

First, add to the `keyMap` struct:

```go
ToggleLogs key.Binding
```

Add to `var keys` initialization:

```go
ToggleLogs: key.NewBinding(
    key.WithKeys("ctrl+l"),
    key.WithHelp("ctrl+l", "logs"),
),
```

In the KeyMsg handling section, add a new case (inside the main `switch` block, after the ToggleRuns handler around line 773):

```go
case key.Matches(msg, keys.ToggleLogs):
    m.logPaneVisible = !m.logPaneVisible
    m.logPaneAutoShown = false
    // Reflow layout to account for log pane height change
    return m.applyResize(tea.WindowSizeMsg{Width: m.width, Height: m.height}), nil
```

Note: `ctrl+l` matches the unified app's binding exactly, providing consistent muscle memory. The `applyResize` call ensures child panes are resized to account for the 10-row log pane appearing/disappearing.

**Step 6: Render LogPane in View()**

In the `View()` method, before the footer is added to `parts` (around line 1061), add:

```go
if m.logPaneVisible && !m.logPane.Empty() {
    parts = append(parts, m.logPane.View())
}
```

**Step 7: Size the LogPane in applyResize()**

In `applyResize()`, add after line 1156 (`m.height = msg.Height`):

```go
m.logPane.SetSize(msg.Width, 10)
logPaneHeight := 0
if m.logPaneVisible {
    logPaneHeight = 10
}
```

Then update the `h` calculation from `h := m.height - 6` to:

```go
h := m.height - 6 - logPaneHeight
```

**Step 8: Add `ctrl+l` to footer help and helpExtras**

In `renderFooter()`, add before the `ctrl+c` entry:

```go
HelpKeyStyle.Render("ctrl+l") + HelpDescStyle.Render(" logs • ") +
```

In `helpExtras()`, add:

```go
shared.HelpBindingFromKey(keys.ToggleLogs),
```

**Step 9: Build and test**

Run: `cd /home/mk/projects/Demarch/apps/autarch && go build ./cmd/bigend/`
Expected: builds without errors

**Step 10: Commit**

```bash
git add apps/autarch/internal/bigend/tui/model.go
git commit -m "feat(bigend): add LogPane with auto-show and L toggle

LogPane renders as bottom overlay when logs arrive. Auto-shows on
first log message, toggleable with ctrl+l. Sized at 10 rows.
Reflows layout on toggle via applyResize."
```

---

### Task 4: Add scrollback dump on exit to standalone Bigend

**Files:**
- Modify: `apps/autarch/cmd/bigend/main.go` (runTUI function)

**Step 1: Add scrollback dump after Run()**

Update the `runTUI` function to dump logs on exit:

```go
func runTUI(agg *aggregator.Aggregator, logHandler *pkgtui.LogHandler) {
    m := tui.New(agg, buildInfoString())
    p := tea.NewProgram(m, tea.WithAltScreen())

    if logHandler != nil {
        logHandler.SetProgram(p)
        defer logHandler.Close()
    }

    if _, err := p.Run(); err != nil {
        fmt.Printf("Error running TUI: %v\n", err)
        os.Exit(1)
    }

    // Dump log history to scrollback after alt-screen exits.
    // Unlike the unified app (which only dumps in inline mode), standalone Bigend
    // always uses alt-screen, so p.Run() returning means alt-screen is already
    // restored. Entries printed here appear in terminal scrollback.
    entries := m.LogPane().Entries()
    if len(entries) > 0 {
        fmt.Println("\n--- Log History ---")
        for _, e := range entries {
            fmt.Printf("[%s] %s: %s\n", e.Time.Format("15:04:05"), e.Level, e.Message)
        }
    }
}
```

Note: We need `m` to be a `*Model` (pointer receiver for `LogPane()`). Check that `tui.New()` returns a value that supports this — it returns `Model` (value), but `LogPane()` has a pointer receiver. We'll need to take the address or change the receiver. Since `LogPane()` is a getter that only reads, change it to a value receiver in Task 3.

**Step 2: Adjust Task 3's LogPane getter to use value receiver**

In Task 3 Step 3, use a value receiver instead:

```go
func (m Model) LogPane() *shared.LogPane {
    return m.logPane
}
```

This works because `logPane` is a pointer field — the copied Model still points to the same LogPane.

**Step 3: Build check**

Run: `cd /home/mk/projects/Demarch/apps/autarch && go build ./cmd/bigend/`
Expected: builds without errors

**Step 4: Commit**

```bash
git add apps/autarch/cmd/bigend/main.go
git commit -m "feat(bigend): dump log history to scrollback on exit

After alt-screen exits, print captured log entries to stdout so they
appear in terminal scrollback. Skips if no entries captured."
```

---

### Task 5: Add panic recovery to all TUI entry points

**Files:**
- Modify: `apps/autarch/cmd/bigend/main.go` (runTUI function)
- Modify: `apps/autarch/cmd/autarch/main.go:374` (runBigendTUI function)
- Modify: `apps/autarch/internal/tui/unified_app.go:978` (Run function)

**Step 1: Write a shared panic recovery helper in pkg/tui**

Create helper in `apps/autarch/pkg/tui/recover.go`:

```go
package tui

import (
    "fmt"
    "os"
    "runtime/debug"
)

// RestoreTerminalOnPanic recovers from a panic, resets the terminal display,
// prints the panic value and stack trace to stderr, and calls os.Exit(1).
//
// Must be called via defer at the start of a TUI entry point:
//
//   defer pkgtui.RestoreTerminalOnPanic()
//
// Note: os.Exit bypasses all remaining deferred functions. Any cleanup
// defers registered after this one (e.g., logHandler.Close()) will not
// run on panic. This is acceptable since the process is terminating.
func RestoreTerminalOnPanic() {
    if r := recover(); r != nil {
        // CSI sequences to restore terminal:
        // \033[?1049l = disable alt-screen
        // \033[?25h   = show cursor
        // \033[0m     = reset attributes
        fmt.Fprint(os.Stderr, "\033[?1049l\033[?25h\033[0m\n")
        fmt.Fprintf(os.Stderr, "panic: %v\n\n", r)
        fmt.Fprint(os.Stderr, string(debug.Stack()))
        os.Exit(1)
    }
}
```

**Step 2: Write tests for RestoreTerminalOnPanic**

Create `apps/autarch/pkg/tui/recover_test.go`:

```go
package tui

import (
    "bytes"
    "os"
    "os/exec"
    "strings"
    "testing"
)

func TestRestoreTerminalOnPanic_NoPanic(t *testing.T) {
    // Verify RestoreTerminalOnPanic is a no-op when there's no panic
    func() {
        defer RestoreTerminalOnPanic()
        // No panic — should return normally
    }()
}

func TestRestoreTerminalOnPanic_ResetsTerminalAndExits(t *testing.T) {
    if os.Getenv("TEST_PANIC_SUBPROCESS") == "1" {
        defer RestoreTerminalOnPanic()
        panic("test panic message")
    }

    cmd := exec.Command(os.Args[0], "-test.run=TestRestoreTerminalOnPanic_ResetsTerminalAndExits")
    cmd.Env = append(os.Environ(), "TEST_PANIC_SUBPROCESS=1")
    var stderr bytes.Buffer
    cmd.Stderr = &stderr
    err := cmd.Run()

    exitErr, ok := err.(*exec.ExitError)
    if !ok {
        t.Fatalf("expected ExitError, got %T: %v", err, err)
    }
    if exitErr.ExitCode() != 1 {
        t.Errorf("expected exit code 1, got %d", exitErr.ExitCode())
    }

    output := stderr.String()
    if !strings.Contains(output, "\033[?1049l") {
        t.Error("stderr missing alt-screen disable sequence")
    }
    if !strings.Contains(output, "\033[?25h") {
        t.Error("stderr missing cursor show sequence")
    }
    if !strings.Contains(output, "test panic message") {
        t.Error("stderr missing panic message")
    }
}
```

**Step 3: Run tests**

Run: `cd /home/mk/projects/Demarch/apps/autarch && go test ./pkg/tui/ -run TestRestoreTerminal -v -race`
Expected: PASS (both no-panic and subprocess tests)

**Step 4: Add defer to standalone Bigend runTUI**

In `cmd/bigend/main.go` `runTUI()`, add as the first line:

```go
defer pkgtui.RestoreTerminalOnPanic()
```

**Step 5: Add defer to deprecated runBigendTUI**

In `cmd/autarch/main.go` `runBigendTUI()`, add as the first line:

```go
defer pkgtui.RestoreTerminalOnPanic()
```

**Step 6: Add defer to unified Run()**

In `internal/tui/unified_app.go` `Run()`, add as the first line (after opts processing):

```go
defer pkgtui.RestoreTerminalOnPanic()
```

**Step 7: Build all entry points**

Run: `cd /home/mk/projects/Demarch/apps/autarch && go build ./cmd/bigend/ && go build ./cmd/autarch/`
Expected: both build without errors

**Step 8: Run full test suite**

Run: `cd /home/mk/projects/Demarch/apps/autarch && go test ./pkg/tui/... ./internal/tui/... -race -count=1`
Expected: all pass

**Step 9: Commit**

```bash
git add apps/autarch/pkg/tui/recover.go apps/autarch/pkg/tui/recover_test.go apps/autarch/cmd/bigend/main.go apps/autarch/cmd/autarch/main.go apps/autarch/internal/tui/unified_app.go
git commit -m "feat(tui): add panic recovery to all TUI entry points

RestoreTerminalOnPanic() restores terminal state (disables alt-screen,
shows cursor) on panic so the terminal is usable after a crash."
```

---

### Task 6: Final integration test and cleanup

**Files:**
- Test: all modified files

**Step 1: Build all binaries**

Run: `cd /home/mk/projects/Demarch/apps/autarch && go build ./cmd/...`
Expected: all build without errors

**Step 2: Run full test suite with race detector**

Run: `cd /home/mk/projects/Demarch/apps/autarch && go test ./... -race -count=1 -timeout=120s`
Expected: all pass

**Step 3: Verify LogHandler integration manually**

The `--tui` flag activates the log handler. Verify the binary runs:

Run: `cd /home/mk/projects/Demarch/apps/autarch && timeout 3 go run ./cmd/bigend/ --tui 2>&1 || true`
Expected: TUI starts (may error on missing config, but should not panic)

**Step 4: Commit if any fixups needed**

Only if Step 2 or 3 revealed issues.
