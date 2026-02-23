# PRD: Bigend Inline Log Pane

**Bead:** iv-omzb
**Date:** 2026-02-23

## Problem

Bigend runs in alt-screen mode and suppresses all slog output below ERROR level, meaning agent activity, operational logs, and debug information are invisible during TUI use and lost after exit.

## Solution

Wire the existing `LogHandler` + `LogPane` infrastructure into Bigend so logs appear in-app during use and dump to terminal scrollback on exit.

## Features

### F1: Wire LogHandler into Bigend Entry Point
**What:** Replace `slog.TextHandler(os.Stderr, &slog.HandlerOptions{Level: slog.LevelError})` with `LogHandler` in `cmd/bigend/main.go`, and call `SetProgram()` after the Bubble Tea program is created.
**Acceptance criteria:**
- [x] `cmd/bigend/main.go` creates a `LogHandler` instead of `TextHandler`
- [x] `LogHandler.SetProgram()` is called with the `tea.Program` before `Run()`
- [x] slog messages at all levels (DEBUG, INFO, WARN, ERROR) are routed to the TUI
- [x] No regression in existing Bigend startup/shutdown behavior

### F2: Integrate LogPane into All Tool Views
**What:** Ensure `LogPane` auto-show/hide works across all Bigend tool views (Coldwine, Pollard, etc.), not just the Gurgeh onboarding flow.
**Acceptance criteria:**
- [x] `LogBatchMsg` triggers auto-show in Bigend TUI regardless of active view
- [x] Log pane renders as bottom overlay when visible
- [ ] Auto-hide after configurable timeout (3s default) when no new logs arrive
- [x] Keyboard toggle to show/hide log pane manually (`ctrl+l`)
- [x] Log pane does not interfere with existing pane layout or navigation

### F3: Scrollback Dump on Exit
**What:** After `tea.Program.Run()` returns, dump all captured log entries to stdout so they appear in terminal scrollback.
**Acceptance criteria:**
- [x] On normal exit, `LogPane.Entries()` content is printed to stdout
- [x] Entries are formatted readably (timestamp, level, message) without ANSI color codes
- [x] Empty log buffer produces no output (no empty dump)
- [x] Works correctly when Bigend exits via Ctrl+C / `q` / fatal error

### F4: Panic Recovery
**What:** Add a `defer` recovery block that restores terminal state if Bigend panics.
**Acceptance criteria:**
- [x] `defer` block in `main()` catches panics and restores terminal (disable alt-screen, show cursor)
- [x] Panic message and stack trace are printed to stderr after terminal restore
- [x] Terminal is usable after a panic (not stuck in alt-screen or raw mode)

## Non-goals

- **True inline mode** (no alt-screen) — experimental in Bubble Tea, deferred
- **Runtime log level filtering** — YAGNI for now, existing level display suffices
- **FrankenTUI dirty row tracking** — optimization for later
- **Log persistence to file** — not needed; scrollback dump covers the use case

## Dependencies

- `pkg/tui/loghandler.go` — existing, no changes expected
- `pkg/tui/logpane.go` — existing, may need `Entries()` method for plain-text export
- `internal/tui/unified_app.go` — existing integration point
- `cmd/bigend/main.go` — primary modification target

## Open Questions

- ~~Does `LogPane` already expose an `Entries()` method for plain-text export, or does it need one?~~ Yes, `Entries()` already exists at `pkg/tui/logpane.go:129`.
- ~~What key binding for manual log pane toggle? (`L` seems natural, need to check conflicts)~~ Resolved: `ctrl+l` matches the unified app's binding.
