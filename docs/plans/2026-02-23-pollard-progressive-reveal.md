# Pollard Progressive Result Reveal Implementation Plan
**Phase:** executing (as of 2026-02-23T21:45:08Z)

> **For Claude:** REQUIRED SUB-SKILL: Use clavain:executing-plans to implement this plan task-by-task.

**Goal:** Make PollardView show results incrementally as each hunter completes, with spinner rows for in-progress hunters, instead of loading all insights once after everything finishes.

**Architecture:** Wire the existing `research.Coordinator` into `PollardView` (it's already used by Gurgeh views). PollardView will handle the same Bubble Tea messages (`HunterStartedMsg`, `HunterUpdateMsg`, `HunterCompletedMsg`, etc.) that `ResearchOverlay` already consumes. The sidebar shows hunter status badges and the document pane reveals findings progressively, sorted by relevance.

**Tech Stack:** Go, Bubble Tea, lipgloss, existing `internal/pollard/research` package

**Review fixes applied (flux-drive 2026-02-23):**
- P0: Wire `researchCoord.SetProgram(p)` after `tea.NewProgram` (otherwise messages never arrive)
- P0: Fix deadlock in `coordinator.StartRun` — release lock before `sendMsg`
- P1: Add `currentRunID` field, guard all message handlers against stale RunIDs
- Remove dead `researchOverlay` field (PollardView handles messages directly)
- Sort `hunterStatuses` map keys before iterating in `SidebarItems`
- Fix test panic: avoid `loadInsights` on nil client in `RunCompletedMsg` test

---

### Task 1: Accept Coordinator in PollardView constructor

**Files:**
- Modify: `apps/autarch/internal/tui/views/pollard.go:15-46`
- Modify: `apps/autarch/cmd/autarch/main.go:238-245`

**Step 1: Add coordinator field and update constructor**

In `pollard.go`, add a `coordinator` field to `PollardView` (no ResearchOverlay — PollardView handles messages directly):

```go
// Add to imports:
"github.com/mistakeknot/autarch/internal/pollard/research"

// Add fields to PollardView struct:
coordinator    *research.Coordinator

// Running state
currentRunID   string
hunterStatuses map[string]research.HunterStatus
runActive      bool
```

Update `NewPollardView` signature:

```go
func NewPollardView(client *autarch.Client, coordinator *research.Coordinator) *PollardView {
```

Initialize the new fields:

```go
return &PollardView{
    client:      client,
    coordinator: coordinator,
    shell:       pkgtui.NewShellLayout(),
    chatPanel:   chatPanel,
    chatHandler: chatHandler,
}
```

**Step 2: Update call sites**

In `cmd/autarch/main.go:238-245`, pass the GurgehConfig's coordinator to PollardView:

```go
researchCoord := research.NewCoordinator(nil)
// ... (existing gurgehCfg setup uses researchCoord) ...

app.SetDashboardViewFactory(func(c *autarch.Client) []tui.View {
    return []tui.View{
        views.NewBigendView(c),
        views.NewGurgehView(c, gurgehCfg),
        views.NewColdwineView(c),
        views.NewPollardView(c, researchCoord),
    }
})
```

Extract `researchCoord` to a local variable so both GurgehConfig and PollardView share the same instance.

**Critical: Wire SetProgram.** Find where `tea.NewProgram` is constructed (likely in `tui.Run` or `cmd/autarch/main.go`). After `p := tea.NewProgram(...)`, call `researchCoord.SetProgram(p)`. Follow the existing pattern for `logHandler.SetProgram(p)`. Without this, `Coordinator.sendMsg` is a silent no-op because `c.program == nil`.

In `cmd/testui/main.go:312`, update to pass `nil` coordinator (test harness):

```go
views.NewPollardView(c, nil),
```

**Step 3: Build to verify compilation**

Run: `cd /home/mk/projects/Demarch/apps/autarch && go build ./cmd/...`
Expected: Clean build

**Step 4: Commit**

```bash
git add internal/tui/views/pollard.go cmd/autarch/main.go cmd/testui/main.go
git commit -m "feat(pollard): accept research Coordinator in PollardView"
```

---

### Task 1b: Fix coordinator deadlock in StartRun

**Files:**
- Modify: `apps/autarch/internal/pollard/research/coordinator.go:62-98` (StartRun)

**Step 1: Fix the lock/sendMsg deadlock**

`StartRun` holds `c.mu.Lock()` then calls `c.sendMsg()` which tries `c.mu.RLock()` — this deadlocks because `sync.RWMutex` is not reentrant. Fix by collecting cancellation data under lock, releasing lock, then sending:

```go
func (c *Coordinator) StartRun(ctx context.Context, projectID string, hunterNames []string, topics []TopicConfig) (*Run, error) {
    c.mu.Lock()

    // Cancel any existing run (collect data before releasing lock)
    var cancelledRunID string
    if c.activeRun != nil {
        cancelledRunID = c.activeRun.RunID
        c.activeRun.Cancel()
    }

    // Create new run
    run := NewRunWithContext(ctx, projectID)
    c.activeRun = run

    for _, name := range hunterNames {
        run.RegisterHunter(name)
    }

    c.mu.Unlock()

    // Send cancellation message AFTER releasing lock (sendMsg acquires RLock)
    if cancelledRunID != "" {
        c.sendMsg(RunCancelledMsg{
            RunID:  cancelledRunID,
            Reason: "new run started",
        })
    }

    // Notify TUI of run start
    c.sendMsg(RunStartedMsg{
        RunID:     run.RunID,
        ProjectID: projectID,
        Hunters:   hunterNames,
    })

    go c.executeRun(run, hunterNames, topics)
    return run, nil
}
```

**Step 2: Run tests**

Run: `cd /home/mk/projects/Demarch/apps/autarch && go test -race ./internal/pollard/research/ -v`
Expected: PASS

**Step 3: Commit**

```bash
git add internal/pollard/research/coordinator.go
git commit -m "fix(research): prevent deadlock in StartRun when cancelling existing run"
```

---

### Task 2: Handle research messages in PollardView.Update

**Files:**
- Modify: `apps/autarch/internal/tui/views/pollard.go:87-161` (Update method)

**Step 1: Add research message handling to Update**

Add cases in the `switch msg := msg.(type)` block, before the `tea.KeyMsg` case:

```go
case research.RunStartedMsg:
    v.currentRunID = msg.RunID
    v.runActive = true
    v.hunterStatuses = make(map[string]research.HunterStatus)
    for _, name := range msg.Hunters {
        v.hunterStatuses[name] = research.HunterStatus{
            Name:   name,
            Status: research.StatusPending,
        }
    }
    return v, nil

case research.HunterStartedMsg:
    if msg.RunID != v.currentRunID {
        return v, nil // Stale run, ignore
    }
    if hs, ok := v.hunterStatuses[msg.HunterName]; ok {
        hs.Status = research.StatusRunning
        hs.StartedAt = time.Now()
        v.hunterStatuses[msg.HunterName] = hs
    }
    return v, nil

case research.HunterUpdateMsg:
    if msg.RunID != v.currentRunID {
        return v, nil // Stale run, ignore
    }
    // Progressive reveal: append new findings to sidebar
    for _, f := range msg.Findings {
        v.addFinding(f, msg.HunterName)
    }
    return v, nil

case research.HunterCompletedMsg:
    if msg.RunID != v.currentRunID {
        return v, nil // Stale run, ignore
    }
    if hs, ok := v.hunterStatuses[msg.HunterName]; ok {
        hs.Status = research.StatusComplete
        hs.FinishedAt = time.Now()
        hs.Findings = msg.FindingCount
        v.hunterStatuses[msg.HunterName] = hs
    }
    return v, nil

case research.HunterErrorMsg:
    if msg.RunID != v.currentRunID {
        return v, nil // Stale run, ignore
    }
    if hs, ok := v.hunterStatuses[msg.HunterName]; ok {
        hs.Status = research.StatusError
        hs.FinishedAt = time.Now()
        hs.Error = msg.Error.Error()
        v.hunterStatuses[msg.HunterName] = hs
    }
    return v, nil

case research.RunCompletedMsg:
    if msg.RunID != v.currentRunID {
        return v, nil // Stale run, ignore
    }
    v.runActive = false
    // Refresh full insights list from server for persistence
    return v, v.loadInsights()
```

**Step 2: Add the addFinding helper**

Add a method that converts a `research.Finding` to an `autarch.Insight` and appends it to the view's insights list. Insert sorted by relevance (descending):

```go
func (v *PollardView) addFinding(f research.Finding, hunterName string) {
    insight := autarch.Insight{
        ID:       f.ID,
        Title:    f.Title,
        Body:     f.Summary,
        Source:   f.Source,
        Category: f.SourceType,
        Score:    f.Relevance,
    }
    // Insert sorted by score descending
    idx := sort.Search(len(v.insights), func(i int) bool {
        return v.insights[i].Score < insight.Score
    })
    v.insights = append(v.insights, autarch.Insight{})
    copy(v.insights[idx+1:], v.insights[idx:])
    v.insights[idx] = insight
}
```

Add `"sort"` and `"time"` to imports.

**Step 3: Build to verify compilation**

Run: `cd /home/mk/projects/Demarch/apps/autarch && go build ./cmd/...`
Expected: Clean build

**Step 4: Commit**

```bash
git add internal/tui/views/pollard.go
git commit -m "feat(pollard): handle research messages for progressive reveal"
```

---

### Task 3: Render hunter status badges in sidebar

**Files:**
- Modify: `apps/autarch/internal/tui/views/pollard.go:182-201` (SidebarItems)
- Modify: `apps/autarch/internal/tui/views/pollard.go:164-179` (View)

**Step 1: Add hunter status header to sidebar**

Update `SidebarItems()` to prepend hunter status badges when a run is active:

```go
func (v *PollardView) SidebarItems() []pkgtui.SidebarItem {
    var items []pkgtui.SidebarItem

    // Show hunter status during active run
    // Sort keys for deterministic rendering (map iteration is random)
    if v.runActive && len(v.hunterStatuses) > 0 {
        names := make([]string, 0, len(v.hunterStatuses))
        for name := range v.hunterStatuses {
            names = append(names, name)
        }
        sort.Strings(names)
        for _, name := range names {
            status := v.hunterStatuses[name]
            icon := hunterStatusIcon(status.Status)
            label := fmt.Sprintf("%s %s", icon, name)
            if status.Findings > 0 {
                label += fmt.Sprintf(" (%d)", status.Findings)
            }
            items = append(items, pkgtui.SidebarItem{
                ID:    "hunter:" + name,
                Label: label,
                Icon:  icon,
            })
        }
    }

    // Append insight items
    for _, insight := range v.insights {
        title := insight.Title
        if title == "" && len(insight.ID) >= 8 {
            title = insight.ID[:8]
        }
        items = append(items, pkgtui.SidebarItem{
            ID:    insight.ID,
            Label: title,
            Icon:  categoryIcon(insight.Category),
        })
    }

    return items
}
```

**Step 2: Add hunterStatusIcon helper**

```go
func hunterStatusIcon(s research.Status) string {
    switch s {
    case research.StatusRunning:
        return "↻"
    case research.StatusComplete:
        return "✓"
    case research.StatusError:
        return "✗"
    case research.StatusPending:
        return "○"
    default:
        return "?"
    }
}
```

**Step 3: Update View() to show "scanning" state**

In `View()`, replace the loading check to also handle active runs:

```go
func (v *PollardView) View() string {
    if v.loading && !v.runActive {
        return pkgtui.LabelStyle.Render("Loading insights...")
    }

    if v.err != nil && !v.runActive {
        return tui.ErrorView(v.err)
    }

    sidebarItems := v.SidebarItems()
    document := v.renderDocument()
    chat := v.chatPanel.View()

    return v.shell.Render(sidebarItems, document, chat)
}
```

**Step 4: Build and verify**

Run: `cd /home/mk/projects/Demarch/apps/autarch && go build ./cmd/...`
Expected: Clean build

**Step 5: Commit**

```bash
git add internal/tui/views/pollard.go
git commit -m "feat(pollard): render hunter status badges in sidebar"
```

---

### Task 4: Add source attribution column to document pane

**Files:**
- Modify: `apps/autarch/internal/tui/views/pollard.go:220-267` (renderDocument)

**Step 1: Add source badge to insight detail rendering**

Update `renderDocument()` to show source attribution with a styled badge, and show a run-active header when hunters are running:

```go
func (v *PollardView) renderDocument() string {
    width := v.shell.LeftWidth()
    if width <= 0 {
        width = v.width / 2
    }

    var lines []string

    // Header with run status
    if v.runActive {
        running := 0
        complete := 0
        for _, hs := range v.hunterStatuses {
            switch hs.Status {
            case research.StatusRunning:
                running++
            case research.StatusComplete:
                complete++
            }
        }
        statusLine := fmt.Sprintf("Research: %d/%d hunters complete",
            complete, len(v.hunterStatuses))
        lines = append(lines, pkgtui.SubtitleStyle.Render(statusLine))
        lines = append(lines, "")
    }

    lines = append(lines, pkgtui.TitleStyle.Render("Insight Details"))
    lines = append(lines, "")

    if len(v.insights) == 0 {
        if v.runActive {
            lines = append(lines, pkgtui.LabelStyle.Render("Waiting for results..."))
        } else {
            lines = append(lines, pkgtui.LabelStyle.Render("No insights found"))
            lines = append(lines, "")
            lines = append(lines, pkgtui.LabelStyle.Render("Run Pollard hunters to gather research insights."))
        }
        return strings.Join(lines, "\n")
    }

    if v.selected >= len(v.insights) {
        lines = append(lines, pkgtui.LabelStyle.Render("No insight selected"))
        return strings.Join(lines, "\n")
    }

    i := v.insights[v.selected]

    lines = append(lines, fmt.Sprintf("Title: %s", i.Title))
    lines = append(lines, fmt.Sprintf("Category: %s  Source: %s", i.Category, i.Source))
    lines = append(lines, fmt.Sprintf("Score: %.2f", i.Score))
    lines = append(lines, "")

    if i.Body != "" {
        lines = append(lines, pkgtui.SubtitleStyle.Render("Summary"))
        wrapped := wordWrap(i.Body, width-4)
        lines = append(lines, wrapped...)
        lines = append(lines, "")
    }

    if i.URL != "" {
        lines = append(lines, fmt.Sprintf("URL: %s", i.URL))
    }

    if i.SpecID != "" {
        lines = append(lines, fmt.Sprintf("Linked Spec: %s", i.SpecID))
    }

    return strings.Join(lines, "\n")
}
```

**Step 2: Build and verify**

Run: `cd /home/mk/projects/Demarch/apps/autarch && go build ./cmd/...`
Expected: Clean build

**Step 3: Commit**

```bash
git add internal/tui/views/pollard.go
git commit -m "feat(pollard): source attribution and run-active status in document pane"
```

---

### Task 5: Wire "Run Research" command to Coordinator

**Files:**
- Modify: `apps/autarch/internal/tui/views/pollard.go:321-338` (Commands)
- Modify: `apps/autarch/internal/tui/views/pollard.go:75-84` (Init/Focus)

**Step 1: Implement the "Run Research" command**

Update the `Commands()` method to actually trigger a research run via the coordinator:

```go
func (v *PollardView) Commands() []tui.Command {
    return []tui.Command{
        {
            Name:        "Run Research",
            Description: "Execute Pollard hunters",
            Action: func() tea.Cmd {
                if v.coordinator == nil {
                    return nil
                }
                return func() tea.Msg {
                    hunterNames := []string{"competitor-tracker", "hackernews-trendwatcher", "github-scout"}
                    _, err := v.coordinator.StartRun(
                        context.Background(),
                        "default",
                        hunterNames,
                        nil,
                    )
                    if err != nil {
                        return insightsLoadedMsg{err: err}
                    }
                    return nil // Updates come via research messages
                }
            },
        },
        {
            Name:        "Link Insight",
            Description: "Link insight to a spec",
            Action: func() tea.Cmd {
                return nil
            },
        },
    }
}
```

Add `"context"` to imports.

**Step 2: Update ShortHelp to mention research**

```go
func (v *PollardView) ShortHelp() string {
    help := "↑/↓ navigate  ctrl+r refresh  ctrl+g model  tab focus  ctrl+b sidebar"
    if v.runActive {
        help = "↻ research active  " + help
    }
    return help
}
```

**Step 3: Build and verify**

Run: `cd /home/mk/projects/Demarch/apps/autarch && go build ./cmd/...`
Expected: Clean build

**Step 4: Commit**

```bash
git add internal/tui/views/pollard.go
git commit -m "feat(pollard): wire Run Research command to Coordinator"
```

---

### Task 6: Add tests for progressive reveal behavior

**Files:**
- Create: `apps/autarch/internal/tui/views/pollard_progressive_test.go`

**Step 1: Write test for message handling**

```go
package views

import (
    "testing"
    "time"

    "github.com/mistakeknot/autarch/internal/pollard/research"
)

// newTestPollardView creates a PollardView with nil client (safe for tests
// that don't trigger loadInsights).
func newTestPollardView() *PollardView {
    return NewPollardView(nil, nil)
}

func TestPollardView_RunStartedMsg(t *testing.T) {
    v := newTestPollardView()
    msg := research.RunStartedMsg{
        RunID:     "test-run",
        ProjectID: "test-proj",
        Hunters:   []string{"github-scout", "hackernews-trendwatcher"},
    }
    v.Update(msg)

    if !v.runActive {
        t.Error("expected runActive to be true after RunStartedMsg")
    }
    if v.currentRunID != "test-run" {
        t.Errorf("expected currentRunID 'test-run', got %q", v.currentRunID)
    }
    if len(v.hunterStatuses) != 2 {
        t.Errorf("expected 2 hunter statuses, got %d", len(v.hunterStatuses))
    }
    for _, name := range msg.Hunters {
        hs, ok := v.hunterStatuses[name]
        if !ok {
            t.Errorf("missing hunter status for %s", name)
        }
        if hs.Status != research.StatusPending {
            t.Errorf("expected pending status for %s, got %s", name, hs.Status)
        }
    }
}

func TestPollardView_HunterCompletedMsg(t *testing.T) {
    v := newTestPollardView()
    v.currentRunID = "test-run"
    v.runActive = true
    v.hunterStatuses = map[string]research.HunterStatus{
        "github-scout": {Name: "github-scout", Status: research.StatusRunning},
    }

    msg := research.HunterCompletedMsg{
        RunID:        "test-run",
        HunterName:   "github-scout",
        FindingCount: 3,
    }
    v.Update(msg)

    hs := v.hunterStatuses["github-scout"]
    if hs.Status != research.StatusComplete {
        t.Errorf("expected complete, got %s", hs.Status)
    }
    if hs.Findings != 3 {
        t.Errorf("expected 3 findings, got %d", hs.Findings)
    }
}

func TestPollardView_StaleRunIDIgnored(t *testing.T) {
    v := newTestPollardView()
    v.currentRunID = "current-run"
    v.runActive = true
    v.hunterStatuses = map[string]research.HunterStatus{
        "github-scout": {Name: "github-scout", Status: research.StatusRunning},
    }

    // Message from a stale run should be ignored
    msg := research.HunterCompletedMsg{
        RunID:        "old-run",
        HunterName:   "github-scout",
        FindingCount: 99,
    }
    v.Update(msg)

    hs := v.hunterStatuses["github-scout"]
    if hs.Status != research.StatusRunning {
        t.Errorf("expected status unchanged (running), got %s", hs.Status)
    }
}

func TestPollardView_AddFindingSortsByRelevance(t *testing.T) {
    v := newTestPollardView()

    v.addFinding(research.Finding{
        ID: "low", Title: "Low", Relevance: 0.3, CollectedAt: time.Now(),
    }, "test")
    v.addFinding(research.Finding{
        ID: "high", Title: "High", Relevance: 0.9, CollectedAt: time.Now(),
    }, "test")
    v.addFinding(research.Finding{
        ID: "mid", Title: "Mid", Relevance: 0.6, CollectedAt: time.Now(),
    }, "test")

    if len(v.insights) != 3 {
        t.Fatalf("expected 3 insights, got %d", len(v.insights))
    }
    // Sorted descending by score
    if v.insights[0].ID != "high" {
        t.Errorf("expected 'high' first, got %s", v.insights[0].ID)
    }
    if v.insights[1].ID != "mid" {
        t.Errorf("expected 'mid' second, got %s", v.insights[1].ID)
    }
    if v.insights[2].ID != "low" {
        t.Errorf("expected 'low' third, got %s", v.insights[2].ID)
    }
}

func TestPollardView_HunterStatusIcon(t *testing.T) {
    tests := []struct {
        status research.Status
        want   string
    }{
        {research.StatusRunning, "↻"},
        {research.StatusComplete, "✓"},
        {research.StatusError, "✗"},
        {research.StatusPending, "○"},
    }
    for _, tt := range tests {
        got := hunterStatusIcon(tt.status)
        if got != tt.want {
            t.Errorf("hunterStatusIcon(%s) = %q, want %q", tt.status, got, tt.want)
        }
    }
}

func TestPollardView_RunCompletedClearsRunActive(t *testing.T) {
    v := newTestPollardView()
    v.currentRunID = "test-run"
    v.runActive = true
    v.hunterStatuses = map[string]research.HunterStatus{
        "test": {Name: "test", Status: research.StatusComplete},
    }

    msg := research.RunCompletedMsg{
        RunID:         "test-run",
        TotalFindings: 5,
        Duration:      "2s",
    }
    // Note: RunCompleted handler calls loadInsights() which returns a tea.Cmd.
    // With nil client, the Cmd will fail if executed, but we only check state here.
    v.Update(msg)

    if v.runActive {
        t.Error("expected runActive to be false after RunCompletedMsg")
    }
}
```

**Step 2: Run tests**

Run: `cd /home/mk/projects/Demarch/apps/autarch && go test -race ./internal/tui/views/ -run TestPollardView -v`
Expected: All 6 tests PASS (including StaleRunIDIgnored)

**Step 3: Commit**

```bash
git add internal/tui/views/pollard_progressive_test.go
git commit -m "test(pollard): progressive reveal message handling"
```

---

### Task 7: Final integration build + full test suite

**Files:** None (verification only)

**Step 1: Build all binaries**

Run: `cd /home/mk/projects/Demarch/apps/autarch && go build ./cmd/...`
Expected: Clean build, no warnings

**Step 2: Run full test suite**

Run: `cd /home/mk/projects/Demarch/apps/autarch && go test -race ./...`
Expected: All packages PASS

**Step 3: Check plan items off**

Mark all checkboxes in this plan as done.
