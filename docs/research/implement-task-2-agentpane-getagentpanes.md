# Task 2 Implementation: AgentPane struct and GetAgentPanes method

## Summary

Successfully implemented Task 2 of the broadcast confirmation flow plan. Added the `AgentPane` struct, `GetAgentPanes` method, `detectAgentType` function, and three new `AgentType` constants to the tmux client package.

## Files Modified

### 1. `internal/bigend/tmux/detector.go` -- Added AgentType constants

Added three new constants to the existing `AgentType` const block:

```go
AgentGemini  AgentType = "gemini"
AgentUser    AgentType = "user"
AgentUnknown AgentType = "unknown"
```

These were appended after the existing `AgentClaude`, `AgentCodex`, `AgentAider`, `AgentCursor` constants. The alignment was adjusted to keep all values vertically aligned (added extra space to existing entries to match the longest name `AgentUnknown`).

### 2. `internal/bigend/tmux/client.go` -- Added AgentPane struct, GetAgentPanes, detectAgentType

Appended at the end of the file (after `AttachSession`):

- **`AgentPane` struct**: Contains `ID` (tmux pane ID like `%0`), `AgentType` (reusing the type from `detector.go`), and `Title` (raw pane title).

- **`GetAgentPanes(session string) ([]AgentPane, error)`**: Enumerates all tmux panes using `list-panes -a -F` with tab-delimited format (matching the `RefreshCache` pattern for safety with colons in pane titles). Filters to the specified session. Returns `nil, nil` (empty list, no error) when tmux is unavailable ("no server running" or "no sessions" stderr).

- **`detectAgentType(title string) AgentType`**: Classifies agent type from pane title using case-insensitive substring matching. Priority order: Claude > Codex > Gemini > User (bash/zsh) > Unknown.

### 3. `internal/bigend/tmux/agent_panes_test.go` -- New test file

Created with 4 test functions:

| Test | Purpose |
|------|---------|
| `TestGetAgentPanes_ParsesOutput` | Verifies parsing of 4-pane tab-delimited output, checking ID and AgentType for each |
| `TestGetAgentPanes_FiltersBySession` | Verifies session filtering (3 panes, 2 in target session) |
| `TestGetAgentPanes_EmptyOnNoServer` | Verifies graceful degradation when tmux server is not running |
| `TestDetectAgentType` | Table-driven test covering 10 title patterns across all 5 agent types |

Uses `fakeRunnerPanes` struct following the project convention established in `client_actions_test.go` (a different fake runner type name to avoid redeclaration conflict since both files are in the same package).

## Test Results

All 7 tests in the package pass (4 new + 3 existing), with `-race` flag:

```
=== RUN   TestGetAgentPanes_ParsesOutput
--- PASS: TestGetAgentPanes_ParsesOutput (0.00s)
=== RUN   TestGetAgentPanes_FiltersBySession
--- PASS: TestGetAgentPanes_FiltersBySession (0.00s)
=== RUN   TestGetAgentPanes_EmptyOnNoServer
--- PASS: TestGetAgentPanes_EmptyOnNoServer (0.00s)
=== RUN   TestDetectAgentType
=== RUN   TestDetectAgentType/claude-agent
=== RUN   TestDetectAgentType/Claude_Code
=== RUN   TestDetectAgentType/codex-agent
=== RUN   TestDetectAgentType/Codex_CLI
=== RUN   TestDetectAgentType/gemini-agent
=== RUN   TestDetectAgentType/Gemini_Pro
=== RUN   TestDetectAgentType/user-shell
=== RUN   TestDetectAgentType/bash
=== RUN   TestDetectAgentType/zsh
=== RUN   TestDetectAgentType/something-else
--- PASS: TestDetectAgentType (0.00s)
=== RUN   TestClientNewSessionCommand
--- PASS: TestClientNewSessionCommand (0.00s)
=== RUN   TestClientRenameSessionCommand
--- PASS: TestClientRenameSessionCommand (0.00s)
=== RUN   TestClientKillSessionCommand
--- PASS: TestClientKillSessionCommand (0.00s)
PASS
ok  	github.com/mistakeknot/autarch/internal/bigend/tmux	1.013s
```

Package also builds cleanly with `go build ./internal/bigend/tmux/...` (no output = no errors).

## Design Decisions

1. **Tab-delimited format**: Matches the existing `RefreshCache` pattern in `client.go` line 99. Colons in pane titles would break colon-delimited parsing, so tabs are safer.

2. **Graceful degradation**: `GetAgentPanes` returns `nil, nil` (not an error) when tmux is unavailable, matching the `RefreshCache` pattern for "no server running" / "no sessions" stderr.

3. **`detectAgentType` as package-level function**: Not a method on `Client` or `Detector` because it operates purely on a string title with no state needed. The test file can call it directly. Placed in `client.go` alongside `GetAgentPanes` since it's its primary consumer.

4. **Separate fake runner type**: Named `fakeRunnerPanes` (not `fakeRunner`) to avoid redeclaring the type already defined in `client_actions_test.go`. Both files are in the same `tmux` test package.

5. **Uses `c.run()` helper**: The `GetAgentPanes` method uses the injectable `c.run()` method (which delegates to `Runner` interface) rather than calling `exec.Command` directly. This is what makes the fake runner testing work.

## Potential Concerns

- **`detectAgentType` priority**: If a pane title contained multiple keywords (e.g., "claude-codex-bridge"), the first match wins (Claude in this case). This seems unlikely in practice but worth noting.

- **Aider and Cursor not handled by `detectAgentType`**: The function currently maps to Claude/Codex/Gemini/User/Unknown. Aider and Cursor AgentType constants exist in `detector.go` but are not part of the pane title detection. This matches the task spec and can be extended later if needed.
