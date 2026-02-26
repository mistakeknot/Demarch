# Research: Coldwine View and Data Layer for "Create Sprint" Action

**Date:** 2026-02-25  
**Task:** Understand Coldwine TUI view, SQLite data layer, and how to wire a "Create Sprint" action  
**Scope:** `/home/mk/projects/Demarch/apps/autarch/`

---

## Executive Summary

**Key Finding:** Coldwine uses a **domain-driven model** (Spec → Epic → Story → Task) separate from Intercore's sprint abstraction. There is NO `Sprint` type in the Coldwine data model. To add "Create Sprint", you must:

1. Wire `*intercore.Client` into `ColdwineView` (not currently available)
2. Add a `sprintCreatedMsg` message type
3. Implement the command action to call `ic sprint create` via the intercore client
4. Handle the response message with data reload

---

## 1. Coldwine TUI View Architecture

### File: `/home/mk/projects/Demarch/apps/autarch/internal/tui/views/coldwine.go` (398 lines)

#### ColdwineView Struct (lines 16-32)
```go
type ColdwineView struct {
    client      *autarch.Client      // HTTP client to Intermute (NO intercore.Client)
    epics       []autarch.Epic
    stories     []autarch.Story
    tasks       []autarch.Task
    selected    int
    width, height int
    focused     string               // "document" or "chat"
    shell       *pkgtui.ShellLayout
    chatPanel   *pkgtui.ChatPanel
    chatHandler *ColdwineChatHandler
}
```

**Critical:** The `ColdwineView` has `*autarch.Client` only. No `*intercore.Client` field. This must be added.

#### Message Types (lines 30-32, 95-106)
```go
type epicsLoadedMsg struct {
    epics   []autarch.Epic
    stories []autarch.Story
    tasks   []autarch.Task
    err     error
}

type epicCreatedMsg struct {
    epic autarch.Epic
    err  error
}

type storyCreatedMsg struct {
    story autarch.Story
    err   error
}

type taskCreatedMsg struct {
    task autarch.Task
    err  error
}
```

**No `sprintCreatedMsg` exists yet.** You'll need to add one.

#### Update() Method (lines 119-218)

Message handling includes:
- `tea.WindowSizeMsg` (127-132) — window resize
- `epicsLoadedMsg` (134-146) — stores data on successful load
- `epicCreatedMsg` (149-156) — adds system feedback + reloads data
- `storyCreatedMsg` (157-164) — adds system feedback + reloads data
- `taskCreatedMsg` (165-171) — adds system feedback + reloads data
- `pkgtui.SidebarSelectMsg` (173-181) — selection change
- `tea.KeyMsg` (183-218) — keyboard input (NavUp, NavDown, Refresh, Enter)

**Pattern:** Message handler → system feedback to chatPanel → `v.loadData()` to refresh

#### Data Loading (lines 98-113)
```go
func (v *ColdwineView) loadData() tea.Cmd {
    client := v.client
    return func() tea.Msg {
        epics, _ := client.ListEpics()      // autarch.Client methods
        stories, _ := client.ListStories()
        tasks, _ := client.ListTasks()
        return epicsLoadedMsg{epics: epics, stories: stories, tasks: tasks}
    }
}
```

This **does NOT interact with intercore**. It's purely Intermute domain data (Spec/Epic/Story/Task).

#### Commands() Method (lines 354-397)

Returns `[]tui.Command` with three entries:

```go
func (v *ColdwineView) Commands() []tui.Command {
    return []tui.Command{
        {
            Name: "New Epic",
            Description: "Create a new epic",
            Action: func() tea.Cmd {
                client := v.client
                return func() tea.Msg {
                    title := fmt.Sprintf("Untitled Epic — %s", time.Now().Format("Jan 2 15:04"))
                    e, err := client.CreateEpic(autarch.Epic{Title: title})
                    return epicCreatedMsg{epic: e, err: err}
                }
            },
        },
        // "New Story" (lines 369-382)
        // "New Task" (lines 385-393)
    }
}
```

**Pattern for new commands:**
1. Define a message type (e.g., `sprintCreatedMsg`)
2. Add a `Command` entry with an `Action` that returns a `tea.Cmd` closure
3. The closure calls the client method and returns the message
4. Add a case in `Update()` to handle the message

---

## 2. SQLite Schema and Data Model

### File: `/home/mk/projects/Demarch/apps/autarch/internal/coldwine/storage/schema.go` (188 lines)

#### MigrateV2 Creates Schema (line 103)

**Tables created:**
- `epics` (lines 107-115)
- `stories` (lines 118-130)
- `work_tasks` (lines 133-146)
- `agent_sessions`, `worktrees` (supporting tables)

#### Table Definitions

**epics:**
```sql
CREATE TABLE IF NOT EXISTS epics (
    id           TEXT PRIMARY KEY,
    feature_ref  TEXT,
    title        TEXT NOT NULL,
    status       TEXT,
    priority     TEXT,
    created_at   TEXT,
    updated_at   TEXT
);
```

**stories:**
```sql
CREATE TABLE IF NOT EXISTS stories (
    id           TEXT PRIMARY KEY,
    epic_id      TEXT NOT NULL,
    title        TEXT NOT NULL,
    description  TEXT,
    status       TEXT,
    priority     TEXT,
    complexity   TEXT,
    assignee     TEXT,
    created_at   TEXT,
    updated_at   TEXT
);
```

**work_tasks:**
```sql
CREATE TABLE IF NOT EXISTS work_tasks (
    id           TEXT PRIMARY KEY,
    story_id     TEXT NOT NULL,
    title        TEXT NOT NULL,
    description  TEXT,
    status       TEXT,
    priority     TEXT,
    assignee     TEXT,
    worktree_ref TEXT,
    session_ref  TEXT,
    created_at   TEXT,
    updated_at   TEXT
);
```

**Critical Finding:** Neither `epics`, `stories`, nor `work_tasks` have `run_id` or `sprint_id` columns. This is a **domain boundary**: 
- Coldwine data = Intermute domain (Spec/Epic/Story/Task)
- Sprint = Intercore domain (managed by `ic sprint create`)

### Epic Model File: `/home/mk/projects/Demarch/apps/autarch/internal/coldwine/storage/epic.go` (94 lines)

```go
func InsertEpic(db *sql.DB, e Epic) error {
    // INSERT into epics with e.ID, e.FeatureRef, e.Title, e.Status, e.Priority
    // Sets created_at/updated_at to time.Now().Format(time.RFC3339)
}

func ListEpics(db *sql.DB) ([]Epic, error)
func GetEpic(db *sql.DB, id string) (Epic, error)
func UpdateEpic(db *sql.DB, e Epic) error
func DeleteEpic(db *sql.DB, id string) error
```

Field names used: `ID`, `FeatureRef`, `Title`, `Status` (typed as `EpicStatus`), `Priority`, `CreatedAt`, `UpdatedAt`

### Client Model Types: `/home/mk/projects/Demarch/apps/autarch/pkg/autarch/models.go` (137 lines)

```go
type EpicStatus string
const (
    EpicStatusOpen       EpicStatus = "open"
    EpicStatusInProgress EpicStatus = "in_progress"
    EpicStatusDone       EpicStatus = "done"
)

type Epic struct {
    ID          string
    Project     string
    SpecID      string           // Foreign key to Spec
    Title       string
    Description string
    Status      EpicStatus
    CreatedAt   string
    UpdatedAt   string
}

type Story struct {
    ID                  string
    Project             string
    EpicID              string           // Foreign key to Epic
    Title               string
    AcceptanceCriteria  string
    Status              StoryStatus
    CreatedAt           string
    UpdatedAt           string
}

type Task struct {
    ID          string
    Project     string
    StoryID     string           // Foreign key to Story
    Title       string
    Agent       string
    SessionID   string
    Status      TaskStatus
    CreatedAt   string
    UpdatedAt   string
}
```

**No Sprint type exists in the autarch models.** Sprint is an Intercore concept, not an Intermute concept.

---

## 3. Command Palette Architecture

### File: `/home/mk/projects/Demarch/apps/autarch/internal/tui/palette.go` (390 lines)

#### Command Registration Pattern

Views pass commands to the palette via `SetCommands(cmds []Command)` (lines 49-53):

```go
func (p *Palette) SetCommands(cmds []Command) {
    p.commands = cmds
    p.recomputeMatches()   // Fuzzy match over cmd.Name
}
```

#### Command Type Definition: `/home/mk/projects/Demarch/apps/autarch/internal/tui/palette_types.go`

```go
type Command struct {
    Name        string            // Display name ("New Epic")
    Description string            // Help text
    Broadcast   bool              // If true, target phase follows
    Action      func() tea.Cmd    // Returns a tea.Cmd (closure that returns tea.Msg)
}
```

#### Palette Flow

1. **Show()** (lines 62-71): Opens palette, sets `PhaseCommand`, focuses input
2. **Update()** (lines 106-134): Dispatches by phase:
   - `PhaseCommand`: Fuzzy match over `cmd.Name`, navigate with up/down, Enter selects
   - If `cmd.Broadcast=true`: Switch to `PhaseTarget` (select All/Claude/Codex/Gemini)
   - `PhaseConfirm`: Confirm execution
3. **Selected()** (lines 92-104): Maps fuzzy match index back to original command
4. **Enter on normal command** (lines 154-170): Hides palette and runs `cmd.Action()`

#### How ColdwineView Registers Commands

In `coldwine.go` lines 354-397, `Commands()` returns the slice. The palette likely calls this during initialization or on-demand to populate `p.commands`.

---

## 4. Chat Handler and Slash Commands

### File: `/home/mk/projects/Demarch/apps/autarch/internal/tui/views/coldwine_chat_handler.go` (110 lines)

`ColdwineChatHandler` is a **stream bridge** that sends chat input to Claude CLI:

```go
type ColdwineChatHandler struct {
    cwd             string
    continueSession bool
    sessionID       string
    mu              sync.RWMutex
}

func NewColdwineChatHandler(cwd string) *ColdwineChatHandler
func (h *ColdwineChatHandler) HandleMessage(ctx context.Context, userMsg string) (<-chan pkgtui.StreamMessage, error)
func (h *ColdwineChatHandler) SetContinue(cont bool)
func (h *ColdwineChatHandler) ResetSession()
```

**HandleMessage() flow:**
1. Sets a fixed system prompt for Coldwine
2. Reads `continueSession` state (thread-safe via mutex)
3. Builds Claude CLI args: `claude --system-prompt <...> -p "<userMsg>"` (or `--resume <sessionID>` or `-c`)
4. Calls `claude.RunStreaming(ctx, h.cwd, args)` (external CLI invocation)
5. Converts Claude events (text/thinking/tool/result) to `pkgtui.StreamMessage` types
6. Returns a channel of stream messages

**Key limitation:** No slash command parser. Slash commands are NOT implemented in this handler. User input is sent as plain text to Claude's system prompt.

---

## 5. Intercore Client Integration

### File: `/home/mk/projects/Demarch/apps/autarch/pkg/intercore/client.go` (>617 lines)

**Intercore is available via a Go client in the autarch package:**

#### Client API
```go
type Client struct {
    binPath string
    dbPath  string
    timeout time.Duration
}

func New(opts ...Option) (*Client, error)
func Available() bool   // Returns true if ic binary is available

// Example operations:
func (c *Client) DispatchSpawn(ctx context.Context, runID string, opts ...DispatchOption) (string, error)
func (c *Client) DispatchStatus(ctx context.Context, dispatchID string) (*Dispatch, error)
func (c *Client) DispatchList(ctx context.Context, active bool) ([]Dispatch, error)
func (c *Client) GateCheck(ctx context.Context, runID string) (*GateResult, error)
func (c *Client) ArtifactAdd(ctx context.Context, runID, phase, path, artifactType string) error
func (c *Client) StateSet(ctx context.Context, key, scope, jsonValue string) error
func (c *Client) RunAgentAdd(ctx context.Context, runID, agentType string, name, dispatchID string) (string, error)
```

**Full operations list:** Dispatch, Gate, Artifact, State, Lock, RunAgent, Sentinel operations (see `operations.go` lines 1-270)

**Critical finding:** No `sprint create` method in operations.go yet. You'd need to:
1. Add `SprintCreate(ctx context.Context, runID string) (string, error)` to operations
2. Implement it calling `ic sprint create --run-id <runID>`

#### How Intercore is Used in main.go

File: `/home/mk/projects/Demarch/apps/autarch/cmd/autarch/main.go` (605 lines)

**Intercore setup** (lines 122-138):
```go
mgr, err := internalIntermute.NewManager(
    internalIntermute.WithAddr(":0"),                // Auto-bind
    internalIntermute.WithDataDir(projectPath),
)
if err != nil {
    return err
}
port := mgr.Port()
client := autarch.NewClient(mgr.URL())
client.WithFallback(local.NewLocalSource(projectPath))
```

**Passed to TUI** (lines 140-142):
```go
app := tui.NewUnifiedApp(client)
// ... later ...
return tui.Run(client, app, tui.RunOpts{ ... })
```

**Dashboard factory** (lines 239-244):
```go
app.SetDashboardViewFactory(func(c *autarch.Client) []tui.View {
    return []tui.View{
        NewBigendView(c),
        NewColdwineView(c),
        NewGurgehView(c, config),
        NewPollardView(c),
    }
})
```

**Finding:** The `*autarch.Client` is passed to views, but **NOT the intercore client**. Intercore operations are available via the separate `intercore.Client` package, but it's not currently wired into views.

---

## 6. How "New Epic" Works (End-to-End)

### User Flow

1. **Open palette** → User presses key (e.g., Cmd+K)
2. **Type "new epic"** → Fuzzy match
3. **Select command** → Hit Enter
4. **Command.Action() called:**
   ```go
   client := v.client  // Reference to *autarch.Client
   return func() tea.Msg {
       title := "Untitled Epic — Feb 25 14:32"
       e, err := client.CreateEpic(autarch.Epic{Title: title})
       return epicCreatedMsg{epic: e, err: err}
   }
   ```
5. **Message handler in Update()** (lines 149-156):
   ```go
   case epicCreatedMsg:
       if msg.err != nil {
           v.chatPanel.AddMessage("system", fmt.Sprintf("Failed to create epic: %v", msg.err))
           return v, nil
       }
       v.chatPanel.AddMessage("system", fmt.Sprintf("Created epic: %s", msg.epic.Title))
       return v, v.loadData()  // Reload all data
   ```
6. **loadData() emits epicsLoadedMsg** → UI updates with new epic

---

## 7. How to Add "Create Sprint" Action

### Prerequisites

1. **Add SprintCreate to intercore.Client:**
   - File: `/home/mk/projects/Demarch/apps/autarch/pkg/intercore/operations.go`
   - Add method:
     ```go
     func (c *Client) SprintCreate(ctx context.Context, runID string) (string, error) {
         return c.execText(ctx, "sprint", "create", "--run-id="+runID)
     }
     ```

2. **Wire intercore.Client into ColdwineView:**
   - Modify `ColdwineView` struct to include `*intercore.Client` field
   - Update `NewColdwineView()` constructor to accept/store it
   - Update `main.go` to pass it when creating views

### Implementation Steps

1. **Add message type** (in `coldwine.go` after line 106):
   ```go
   type sprintCreatedMsg struct {
       sprintID string
       err      error
   }
   ```

2. **Add command** (in `Commands()` method, line 393+):
   ```go
   {
       Name:        "Create Sprint",
       Description: "Start a new sprint in Intercore",
       Action: func() tea.Cmd {
           iclient := v.iclient  // NEW FIELD
           return func() tea.Msg {
               runID := fmt.Sprintf("sprint-%d", time.Now().UnixNano())
               sprintID, err := iclient.SprintCreate(context.Background(), runID)
               return sprintCreatedMsg{sprintID: sprintID, err: err}
           }
       },
   }
   ```

3. **Add Update() handler** (after line 171):
   ```go
   case sprintCreatedMsg:
       if msg.err != nil {
           v.chatPanel.AddMessage("system", fmt.Sprintf("Failed to create sprint: %v", msg.err))
           return v, nil
       }
       v.chatPanel.AddMessage("system", fmt.Sprintf("Created sprint: %s", msg.sprintID))
       // No data reload needed unless sprint affects epic list
       return v, nil
   ```

### Wiring Diagram

```
main.go
├─ Create intercore.Client (via New())
├─ Create *autarch.Client (Intermute)
└─ NewColdwineView(autarchClient, intercoreClient)  ← ADD PARAM
    ├─ Store both clients
    └─ Commands() method can now call both:
        ├─ autarchClient.CreateEpic() → epicCreatedMsg
        └─ intercoreClient.SprintCreate() → sprintCreatedMsg
```

---

## 8. Key Design Insights

### Domain Separation

| Domain | System | Client | Data | Tables |
|--------|--------|--------|------|--------|
| **Spec/Epic/Story/Task** | Intermute (REST API) | `*autarch.Client` | Stored in `.coldwine/*.db` | epics, stories, work_tasks |
| **Sprint/Run/Dispatch** | Intercore (CLI binary) | `*intercore.Client` | Stored in `.clavain/intercore.db` | N/A (Go binary interaction) |

Coldwine operates in the **Intermute domain**. To add sprint operations, you're bridging into the **Intercore domain**.

### Message Flow Pattern

All actions follow this pattern:
```
Command.Action() → tea.Cmd
    → tea.Msg (e.g., epicCreatedMsg)
    → Update() handles msg
    → Returns tea.Cmd (e.g., v.loadData())
    → That cmd returns tea.Msg (e.g., epicsLoadedMsg)
    → Update() handles that msg
    → View state updates
    → View() re-renders
```

### No Sprint Persistence in Coldwine

Creating a sprint in Intercore does NOT automatically:
- Create an epic in Coldwine
- Link sprints to epics
- Store sprint metadata in the Coldwine database

If you want that bidirectional sync, you'd need to:
1. Store the sprint ID in Coldwine (add column to epics table)
2. On CreateSprint success, insert an epic with that sprint ID
3. On LoadData, enrich epics with sprint status from Intercore

This is a **design decision** to be made: are sprints truly separate from epics, or do they represent "active epics"?

---

## 9. Files Changed Summary

| File | Change | Lines |
|------|--------|-------|
| `pkg/intercore/operations.go` | ADD `SprintCreate()` method | ~10 |
| `internal/tui/views/coldwine.go` | ADD `iclient` field, `sprintCreatedMsg` type, command, handler | ~40 |
| `cmd/autarch/main.go` | MODIFY `NewColdwineView()` call to pass intercore client | ~5 |

---

## 10. Testing Strategy

1. **Unit test the intercore client:**
   - Mock `ic sprint create` output
   - Verify `SprintCreate()` parses sprint ID correctly

2. **Integration test the command:**
   - Create a ColdwineView with a real intercore client
   - Trigger "Create Sprint" command
   - Verify `sprintCreatedMsg` is returned
   - Verify Update() handles it and shows system message

3. **E2E test:**
   - Run `autarch tui --skip-onboard`
   - Open Coldwine tab
   - Open palette, select "Create Sprint"
   - Verify system message appears
   - Run `ic sprint list` to confirm sprint was created

---

## Appendix: File Locations

- `/home/mk/projects/Demarch/apps/autarch/internal/tui/views/coldwine.go` (ColdwineView, messages, Commands())
- `/home/mk/projects/Demarch/apps/autarch/internal/tui/views/coldwine_chat_handler.go` (Chat handler, no slash commands)
- `/home/mk/projects/Demarch/apps/autarch/internal/coldwine/storage/schema.go` (SQLite schema, MigrateV2)
- `/home/mk/projects/Demarch/apps/autarch/internal/coldwine/storage/epic.go` (Epic CRUD)
- `/home/mk/projects/Demarch/apps/autarch/pkg/autarch/client.go` (Intermute HTTP client)
- `/home/mk/projects/Demarch/apps/autarch/pkg/autarch/models.go` (Spec, Epic, Story, Task types)
- `/home/mk/projects/Demarch/apps/autarch/pkg/intercore/client.go` (Intercore CLI client)
- `/home/mk/projects/Demarch/apps/autarch/pkg/intercore/operations.go` (Intercore operations)
- `/home/mk/projects/Demarch/apps/autarch/cmd/autarch/main.go` (View wiring, client initialization)
- `/home/mk/projects/Demarch/apps/autarch/internal/tui/palette.go` (Palette architecture)
- `/home/mk/projects/Demarch/apps/autarch/internal/tui/palette_types.go` (Command type)
