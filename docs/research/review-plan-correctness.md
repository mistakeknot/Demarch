# Correctness Review: Broadcast Confirmation Flow Plan
**Reviewer:** Julik (Flux-drive Correctness Reviewer)
**Date:** 2026-02-23
**Plan:** `apps/autarch/docs/plans/2026-02-23-broadcast-confirmation-flow.md`
**Full review:** `/home/mk/projects/Demarch/.claude/reviews/fd-correctness-broadcast-plan.md`

---

## Invariants

1. Bubble Tea runs `Update()` and `View()` on the same goroutine — no mutex needed for palette fields accessed only from those two methods.
2. `tea.Cmd` callbacks run on a separate goroutine pool — closures that read palette fields from a `tea.Cmd` race with `Update()`.
3. `pendingCmd *Command` points into `p.commands` slice backing array — `SetCommands` invalidates this pointer.
4. `tmux.Client.run()` is safe for concurrent use — new `exec.Command` per call, no shared mutable state.
5. `sessionCache` is protected by `sync.RWMutex` — safe to read from goroutines.

---

## Finding 1 (HIGH): `pendingCmd *Command` Is a Dangling Pointer After `SetCommands`

`Selected()` returns `&p.commands[idx]` — a pointer into the slice's backing array. `pendingCmd` is assigned this pointer. `SetCommands(cmds)` replaces `p.commands` with a new slice, releasing the old backing array. After replacement, `pendingCmd` points to potentially collected memory.

In the current code, `updateCommands()` is only called at init, so this does not fire today. But the public `SetCommands` API, combined with the pointer-to-slice-element pattern, is a time bomb for any future "refresh commands" path.

**Fix:** Store a `Command` value copy, not a pointer:

```go
// struct field:
pendingCmd    Command
hasPendingCmd bool

// in updateCommandPhase:
p.pendingCmd = *cmd   // copy the value — includes the Action func
p.hasPendingCmd = true

// in Hide():
p.hasPendingCmd = false
```

---

## Finding 2 (HIGH): `Action` Closure Reads Palette Fields From a `tea.Cmd` Goroutine — Data Race

The integration test in Task 7 registers:

```go
Action: func() tea.Cmd {
    executedTarget = p.target        // reads p.target
    executedCounts = p.paneCounts    // reads p.paneCounts
    return nil
},
```

`Action()` is returned as a `tea.Cmd` from `updateConfirmPhase`. Bubble Tea runs `tea.Cmd` functions on a goroutine pool. At that point, `Update()` may be processing the next message on its goroutine and writing to `p.target` or `p.paneCounts`. This is a data race that `-race` will detect.

The same bug will appear in production when Task 6's TODO stubs are filled in and read `p.target` to know which panes to send keys to.

**Fix:** Capture the resolved `BroadcastAction` context before calling `Hide()` and before returning `action()` as a `tea.Cmd`:

```go
case "enter":
    if p.hasPendingCmd {
        action := p.pendingCmd.Action
        broadcastCtx := BroadcastAction{   // snapshot on Update() goroutine
            Target:     p.target,
            PaneCounts: p.paneCounts,
        }
        p.Hide()
        _ = broadcastCtx   // pass to the real action, not read from p
        return p, action() // action() must not close over p.*
    }
```

The `BroadcastAction` struct is already defined in the plan's `palette_types.go` — use it.

---

## Finding 3 (MEDIUM): `FetchPaneCounts` Closure Captures `a.sessionName` By Reference

```go
a.palette.FetchPaneCounts = func() tea.Msg {
    panes, err := a.tmuxClient.GetAgentPanes(a.sessionName) // a.sessionName read on goroutine
    ...
}
```

`a.sessionName` is a `string` field on `UnifiedApp`. The closure reads it from a `tea.Cmd` goroutine. If any future code path mutates `a.sessionName` from `Update()` concurrently, this is a data race on the string header.

**Fix:** Capture at closure creation time:

```go
sessionName := a.sessionName
a.palette.FetchPaneCounts = func() tea.Msg {
    panes, err := a.tmuxClient.GetAgentPanes(sessionName)
    ...
}
```

---

## Finding 4 (LOW): Colon Delimiter in `GetAgentPanes` Breaks on Pane Titles Containing Colons

```go
format := "#{pane_id}:#{pane_title}:#{session_name}"
parts := strings.SplitN(line, ":", 3)
```

A pane titled `"project: feature"` produces `%0:project: feature:dev`. `SplitN(..., ":", 3)` gives `["%0", "project", " feature:dev"]`. The session name is misidentified and the pane is filtered out. Pane counts are silently wrong.

**Fix:** Use tab delimiter (session names cannot contain tabs), matching the pattern in `client.go`'s `RefreshCache`:

```go
format := "#{pane_id}\t#{pane_title}\t#{session_name}"
parts := strings.SplitN(line, "\t", 3)
```

---

## Finding 5 (LOW): `&exec.ExitError{}` in Test Is Poor Practice

`exec.ExitError` has an unexported `ProcessState *os.ProcessState` field. The zero value has `ProcessState == nil`. Any call to `.ExitCode()` on the zero value panics. Use `fmt.Errorf("exit status 1")` instead — signals non-nil error without implying type.

---

## Non-Issues (Confirmed Correct)

- **`tmux.Client.run()` concurrent access:** Creates a new `exec.Command` per call — safe for concurrent goroutines.
- **`PaneCountMsg` delivery:** Delivered via Bubble Tea's message dispatch to `Update()` — `paneCounts` is only written from `Update()`, no race.
- **`Broadcast bool` zero value:** Backward compatible — existing `Command` literals default to `false`.
- **Phase state machine:** Transitions are linear and deterministic; all paths (including Esc back and ctrl+c close) are correctly handled.
- **`FetchPaneCounts` function field:** Set once at init, never mutated — reading from `Update()` is safe.
- **`Update()` / `View()` goroutine model:** Confirmed correct. No mutex needed for `phase`, `target`, `paneCounts` fields.
