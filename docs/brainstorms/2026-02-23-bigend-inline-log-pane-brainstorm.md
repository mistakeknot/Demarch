# Bigend Inline Log Pane — Brainstorm

**Bead:** iv-omzb
**Phase:** brainstorm (as of 2026-02-23T16:51:14Z)
**Date:** 2026-02-23
**Status:** Captured

## What We're Building

Wire the existing `LogHandler` + `LogPane` infrastructure (already in `pkg/tui/`) into Bigend so that agent output, slog messages, and operational logs appear within the TUI during use and dump to terminal scrollback on exit.

**Core deliverables:**
1. Replace `slog.TextHandler` with `LogHandler` in `cmd/bigend/main.go`
2. Integrate `LogPane` visibility into all Bigend tool views (Coldwine, Pollard, etc.)
3. Dump captured logs to stdout on normal exit (scrollback preservation)
4. Add panic recovery to restore terminal state on crash

## Why This Approach

### What already exists (80% built)

- **`pkg/tui/loghandler.go`** (~155 lines): `slog.Handler` implementation that routes log messages to a Bubble Tea program via `tea.Send()`. Non-blocking channel with 256 buffer, batched delivery (10 msgs or 100ms), thread-safe with `sync.Mutex` + `atomic.Bool`.
- **`pkg/tui/logpane.go`** (~132 lines): Viewport-based scrollable log display. Circular buffer (500 entries max), auto-scroll to bottom, color-coded by level (ERR red, WRN yellow, INF white, DBG muted), keyboard navigation (`g`/`G`/arrows).
- **`internal/tui/unified_app.go`**: Already has `logPane *pkgtui.LogPane` field, `LogPane()` getter, receives `LogBatchMsg`, and has `LogPaneAutoShowMsg` / `LogPaneScheduleAutoHideMsg` messages.
- **Gurgeh integration**: Already uses auto-show/hide during onboarding interviews.

### Why NOT FrankenTUI's TerminalWriter protocol

The bead originally referenced FrankenTUI's ANSI cursor save/restore approach. However:
- Bubble Tea already manages all terminal state (alt-screen, cursor, mouse)
- Low-level ANSI escapes would conflict with Bubble Tea's rendering pipeline
- The existing LogHandler approach is safer, more portable, and idiomatic Go/Bubble Tea
- FrankenTUI's dirty row tracking and budget degradation are optimization patterns worth borrowing *later*, not prerequisites for inline logging

### Why alt-screen + exit dump (not true inline mode)

- Bubble Tea's inline mode is experimental and has viewport sizing challenges
- Alt-screen provides the full dashboard/pane experience users expect
- Dumping logs on exit gives scrollback preservation without inline mode risks
- Simplest path: wire what exists, add exit dump

## Key Decisions

1. **Wire LogHandler, don't port TerminalWriter** — Bubble Tea-native approach is safer and 80% built
2. **Keep alt-screen** — Full TUI experience during use, scrollback dump on exit
3. **Auto-show/hide for all tools** — Not just Gurgeh; any tool that produces logs should trigger the log pane
4. **Scrollback dump on exit** — Call `LogPane.Entries()` after `tea.Program.Run()` returns, print to stdout
5. **Panic recovery** — `defer` block to restore terminal state if Bubble Tea crashes

## Open Questions

- **Log pane position**: Bottom overlay (current) vs dedicated split pane? (Start with bottom overlay, iterate later)
- **Filter by level at runtime?** LogPane shows all levels — should we add level filtering? (YAGNI for now)
- **Max entries**: 500 circular buffer — sufficient for agent sessions? (Start here, tune if needed)

## References

- `apps/autarch/docs/research/frankentui-research-synthesis.md` — FrankenTUI patterns (Tier 1 #3)
- `pkg/tui/loghandler.go` — Existing log handler
- `pkg/tui/logpane.go` — Existing log pane
- `internal/tui/unified_app.go` — UnifiedApp integration point
- `cmd/bigend/main.go` — Entry point to wire
