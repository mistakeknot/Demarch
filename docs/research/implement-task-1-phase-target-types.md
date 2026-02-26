# Task 1 Implementation: Phase/Target Types and Broadcast Field

**Date:** 2026-02-23
**Status:** Complete

## Summary

Implemented Task 1 of the broadcast confirmation flow plan for the Autarch TUI. This task adds Phase/Target enums, PaneCounts struct, BroadcastAction struct, and a `Broadcast bool` field to the Command struct.

## Files Modified

### Created: `internal/tui/palette_types.go`

New file containing all broadcast-related type definitions:

- **`Phase` enum** (int): `PhaseCommand`, `PhaseTarget`, `PhaseConfirm` — represents the 3-phase palette flow. Has a `String()` method returning lowercase names.
- **`Target` enum** (int): `TargetAll`, `TargetClaude`, `TargetCodex`, `TargetGemini` — represents broadcast target groups. Has a `Label()` method returning display names (e.g., "All agents").
- **`PaneCounts` struct**: Holds live counts of agent panes by type (`Claude`, `Codex`, `Gemini` int fields). Has `Total()` and `ForTarget(Target)` methods.
- **`BroadcastAction` struct**: Holds resolved broadcast context (`Target` + `PaneCounts`) passed to the action closure at execution time.

### Created: `internal/tui/palette_types_test.go`

Test file with 4 test functions covering all new types:

- `TestPhaseString` — verifies all 3 Phase values produce correct string representations
- `TestTargetLabel` — verifies all 4 Target values produce correct display labels
- `TestPaneCountsTotal` — verifies Total() sums all pane counts
- `TestPaneCountsForTarget` — verifies ForTarget() returns correct count for each target including TargetAll

### Modified: `pkg/tui/view.go` (line 50)

Added `Broadcast bool` field to the `Command` struct:

```go
type Command struct {
    Name        string
    Description string
    Action      func() tea.Cmd
    Broadcast   bool // If true, enters target selection before executing
}
```

This field is available to both `pkg/tui` (canonical location) and `internal/tui` (via the existing type alias `Command = pkgtui.Command` in `internal/tui/view.go`).

## Architecture Notes

### Package Layout

The `internal/tui` package already has a `Command` type alias pointing to `pkg/tui.Command`. The new Phase/Target/PaneCounts/BroadcastAction types are defined directly in `internal/tui` because they are palette-specific implementation details, not part of the public `pkg/tui` API. The `Broadcast` field on `Command` lives in `pkg/tui` because it's part of the command registration contract that views use.

### Type Design Decisions

- **Phase and Target are `int` types with `iota`** — standard Go enum pattern, zero-cost, allows switch statements.
- **PaneCounts uses named fields** — more readable than a `map[Target]int` and enforces the known-set of agent types at compile time.
- **BroadcastAction is a value type** — safe to snapshot before `Hide()` (per plan review finding P1: no data race in action closures).

## Test Results

```
=== RUN   TestPhaseString
--- PASS: TestPhaseString (0.00s)
=== RUN   TestTargetLabel
--- PASS: TestTargetLabel (0.00s)
=== RUN   TestPaneCountsTotal
--- PASS: TestPaneCountsTotal (0.00s)
=== RUN   TestPaneCountsForTarget
--- PASS: TestPaneCountsForTarget (0.00s)
PASS
ok  	github.com/mistakeknot/autarch/internal/tui	1.139s
```

All 4 tests pass with `-race` flag enabled. The `go build ./internal/tui/...` command produces no errors.

One pre-existing test failure exists: `TestTabSwitchSendsWindowSizeToNewView` in `unified_app_test.go:325`. This is unrelated to the changes made here.

## What's Next (Task 2)

The next task in the plan will add phase-aware Update/View methods to the Palette struct, using the Phase/Target types defined here to drive the 3-phase flow: Command selection -> Target selection -> Confirmation -> Execute.
