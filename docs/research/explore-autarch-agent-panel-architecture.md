# Autarch TUI Agent Panel Rendering Architecture

## Executive Summary

The Autarch TUI uses **Bubble Tea** (charmbracelet/bubbletea) as its core framework with a sophisticated **three-tier panel architecture**:

1. **Message-based streaming** via channels (not polling)
2. **Scroll-aware history buffer** with follow-tail auto-scroll
3. **Multi-panel layout system** (ShellLayout → SplitLayout → ChatPanel/DocPanel)

The architecture prioritizes **incremental streaming UI updates** with **clean separation between data model (ChatMessage[]) and rendering (renderHistory)**. Agent output is streamed via type-safe channel events, not buffered in bulk.

---

## 1. Core Data Model

### ChatMessage Structure
```go
// pkg/tui/chatpanel.go
type ChatMessage struct {
	Role    string // "user", "agent", "system"
	Content string
}

type ChatPanel struct {
	messages      []ChatMessage       // Complete history buffer
	scroll        int                 // Scroll offset (0 = bottom, +N = scroll up N lines)
	mdRenderer    *glamour.TermRenderer
	streaming     bool                // Agent actively streaming?
	status        string              // "Thinking...", "Responding...", ""
	chatState     ChatState           // ChatIdle | ChatThinking | ChatStreaming | ChatError
	handler       ChatHandler         // Receives user messages, returns event stream
	events        <-chan StreamMsg    // Active stream channel
	composer      *Composer           // Bottom input box
}
```

**Key design point**: Messages are stored in a **simple []ChatMessage slice**. All rendering complexity is in renderHistory().

---

## 2. Streaming & Output Model

### Stream Event Types (Type-Safe Union)
```go
// pkg/tui/chatstream.go
type StreamMsg interface {
	streamMsg() // marker method
}

// Text content streaming
type TextDelta struct {
	Text string
}

// Extended thinking (reasoning) states
type ReasoningStart struct{}
type ReasoningDelta struct {
	Text string
}
type ReasoningEnd struct {
	Duration time.Duration
}

// Tool calls (LLM function calling)
type ToolCallStart struct {
	ID   string
	Name string
}
type ToolCallInput struct {
	ID    string
	Input string
}
type ToolCallResult struct {
	ID      string
	Output  string
	IsError bool
}

// Terminal states
type StreamError struct {
	Err error
}
type StreamDone struct {
	FinishReason string
	SessionID    string // For multi-turn continuation
}
```

### Streaming Flow
```
User Input
    ↓
SubmitInput() creates context & spawns goroutine
    ↓
handler.HandleMessage(ctx, userMsg) → <-chan StreamMsg
    ↓
waitForStreamEvent(events) polled via tea.Cmd
    ↓
handleStreamChunk(StreamMsg)
    ├─ TextDelta: append to messages[last].Content
    ├─ ReasoningStart/Delta: toggle ChatThinking state
    ├─ ToolCall*: internal tracking (not rendered in base ChatPanel)
    ├─ StreamError: set last message content to "Error: ..."
    └─ StreamDone: finalize, enable multi-turn
```

### Handler Interface
```go
type ChatHandler interface {
	HandleMessage(ctx context.Context, userMsg string) (<-chan StreamMsg, error)
}

// Example: ClaudeChatHandler (pkg/tui/claude_handler.go)
type ClaudeChatHandler struct {
	CWD       string
	ExtraArgs []string
	Continue  bool
	SessionID string
}

func (h *ClaudeChatHandler) HandleMessage(ctx context.Context, userMsg string) (<-chan StreamMsg, error) {
	events, err := claude.RunStreaming(ctx, cwd, args)
	if err != nil {
		return nil, err
	}
	out := make(chan StreamMsg, 64)  // Buffered channel
	go func() {
		// Convert from claude.Event to StreamMsg types
		// Filter event types, map SessionID for multi-turn
	}()
	return out, nil
}
```

---

## 3. Scroll & Follow-Tail Mechanism

### Scroll Model
```go
type ChatPanel struct {
	scroll int  // Scroll offset: 0 = at bottom, 1+ = scrolled up N lines
}

func (p *ChatPanel) ScrollUp() {
	p.scroll++  // Show older messages
}

func (p *ChatPanel) ScrollDown() {
	if p.scroll > 0 {
		p.scroll--  // Show newer messages, approach bottom
	}
}

func (p *ChatPanel) ScrollToBottom() {
	p.scroll = 0  // Jump to latest
}
```

### Auto-Scroll on New Message (Follow-Tail)
```go
func (p *ChatPanel) AddMessage(role, content string) {
	p.messages = append(p.messages, ChatMessage{Role: role, Content: content})
	// Auto-scroll to bottom when new message added
	if p.settings.AutoScroll {
		p.scroll = 0  // Follow-tail: jump to bottom
	}
}

// During streaming, also:
case TextDelta:
	if len(p.messages) == 0 || strings.ToLower(p.messages[len(p.messages)-1].Role) != "agent" {
		p.messages = append(p.messages, ChatMessage{Role: "agent", Content: e.Text})
	} else {
		last := &p.messages[len(p.messages)-1]
		last.Content += e.Text  // Append to last agent message
	}
	p.scroll = 0  // Auto-follow-tail during streaming
```

---

## 4. History Rendering (Scroll-Aware)

### renderHistory Algorithm
```go
func (p *ChatPanel) renderHistory(height int) string {
	// Phase 1: Build ALL lines (including wrapping, styling)
	var lines []string
	for _, msg := range p.messages {
		// Add role header
		// Render content (markdown for agent, plain for user)
		// Add blank line separator
	}
	
	// Phase 2: Apply scroll offset
	if len(lines) > height {
		start := len(lines) - height - p.scroll
		if start < 0 {
			start = 0
		}
		end := start + height
		if end > len(lines) {
			end = len(lines)
			start = end - height
		}
		lines = lines[start:end]
	}
	
	// Phase 3: Join and return
	return strings.Join(lines, "\n")
}
```

**Key insight**: The scroll offset is applied **after** building all content lines. This allows O(1) scroll without re-rendering the entire history.

### Markdown Rendering (Agent Messages Only)
```go
if strings.ToLower(msg.Role) == "agent" {
	// Render agent messages as markdown via glamour
	if r := p.markdownRenderer(contentWidth); r != nil {
		rendered, err := r.Render(msg.Content)
		if err == nil {
			rendered = strings.TrimSpace(rendered)
			contentStyle := lipgloss.NewStyle().PaddingLeft(2)
			lines = append(lines, contentStyle.Render(rendered))
		} else {
			// Fallback to plain text
		}
	}
} else {
	// User and system messages: plain text with word wrap
	wrapped := wrapText(msg.Content, contentWidth)
	for _, line := range strings.Split(wrapped, "\n") {
		lines = append(lines, contentStyle.Render(line))
	}
}
```

---

## 5. Layout System (Container Hierarchy)

```
UnifiedApp (main model)
├── TabBar (navigation: Bigend, Gurgeh, Coldwine, Pollard)
├── currentView (one of dashViews)
│   └── GurgehView / BigendView / etc.
│       ├── ShellLayout (3-pane: sidebar + split)
│       │   ├── Sidebar (left nav, collapsible with Ctrl+B)
│       │   └── SplitLayout (2-pane split)
│       │       ├── Left pane (document / spec browser)
│       │       │   └── DocPanel or custom doc viewer
│       │       └── Right pane (chat interface)
│       │           └── ChatPanel
│       │               ├── Composer (input box, multi-line)
│       │               ├── ChatHistory (scrollable via scroll offset)
│       │               ├── CommandPicker (slash command autocomplete)
│       │               └── AgentSelector (model/agent picker)
├── LogPane (bottom, toggled with Ctrl+L or /logs)
├── SignalsOverlay (agent signal notifications)
└── ChatSettingsPanel (model/temperature settings)
```

### Dimension Flow
```
WindowSizeMsg(W, H)
    ↓
UnifiedApp.Update()
    ↓
currentView.Update(msg)  // SplitLayout receives (W-6, H-4-2)
    ↓
ShellLayout.SetSize(W-6, H-6)
    ├─ Sidebar.SetSize(SidebarWidth, H)
    └─ SplitLayout.SetSize(contentWidth, H)
        ├─ ChatPanel.SetSize(RightWidth, RightHeight)
        │   ├─ Composer.SetSize(RightWidth, 12)
        │   └─ renderHistory uses (RightWidth-4, RightHeight - composerHeight - 1)
        └─ DocPanel.SetSize(LeftWidth, LeftHeight)
```

**Critical rule** (from CLAUDE.md): Always subtract chrome dimensions before passing to child views. Children only know about their allocated space.

---

## 6. Multi-Pane Output Panels

### DocPanel (Left Pane - Document Display)
```go
// pkg/tui/docpanel.go
type DocPanel struct {
	content   string
	viewport  viewport.Model
	width     int
	height    int
}

func (p *DocPanel) SetSize(width, height int) {
	p.viewport = viewport.New(width-2, height-1)
	p.viewport.SetContent(p.content)
}

func (p *DocPanel) View() string {
	// Header + viewport with scroll indicators
}
```

Uses **charmbracelet/bubbles/viewport** for scrolling.

### ChatPanel (Right Pane - Agent Output)
Already detailed above. Uses **manual scroll offset tracking** (not viewport).

### LogPane (Bottom Log Viewer)
```go
// pkg/tui/logpane.go
type LogPane struct {
	viewport viewport.Model
	entries  []LogMsg        // Max 500 entries
	width    int
	height   int
}

const maxLogEntries = 500

func (p *LogPane) Update(msg tea.Msg) tea.Cmd {
	case LogBatchMsg:
		p.entries = append(p.entries, msg.Entries...)
		if len(p.entries) > maxLogEntries {
			p.entries = p.entries[len(p.entries)-maxLogEntries:]  // Rotate: keep newest
		}
		p.updateContent()
		p.viewport.GotoBottom()  // Auto-follow-tail
}
```

Also uses viewport with auto-follow-tail (GotoBottom).

---

## 7. Message Events & Update Loop

### Internal Message Types (internal/tui/messages.go)
```go
type AgentStreamMsg struct {
	Line string  // Single streaming line from agent
}

type AgentRunStartedMsg struct {
	What string
}

type AgentRunFinishedMsg struct {
	What string
	Err  error
	Diff []string
}

type SprintStreamLineMsg struct {
	Content string  // Streaming update (Gurgeh phase drafting)
}

type SprintStreamDoneMsg struct{}
```

These are **Tea Messages** (not StreamMsg). They're sent via `func() tea.Msg { ... }` commands.

### Update Flow in ChatPanel
```go
func (p *ChatPanel) Update(msg tea.Msg) (*ChatPanel, tea.Cmd) {
	// Spinner animation
	if msg, ok := msg.(spinner.TickMsg); ok && p.streaming {
		p.spinner.Update(msg)
		return p, cmd
	}
	
	// Stream startup
	case streamStartedMsg:
		p.events = typedMsg.events
		return p, waitForStreamEvent(p.events)  // Poll first event
	
	// Stream chunk arrived
	case StreamChunkMsg:
		return p.handleStreamChunk(typedMsg.Event)
	
	// Keyboard input
	case tea.KeyMsg:
		// Handle scroll, agent selector, command picker...
}

func waitForStreamEvent(events <-chan StreamMsg) tea.Cmd {
	return func() tea.Msg {
		if events == nil {
			return StreamChunkMsg{Event: StreamDone{FinishReason: "stop"}}
		}
		event, ok := <-events
		if !ok {
			return StreamChunkMsg{Event: StreamDone{FinishReason: "stop"}}
		}
		return StreamChunkMsg{Event: event}
	}
}
```

---

## 8. Agent-Specific Panel Implementations

### Gurgeh View (Spec Browser)
```go
// internal/tui/views/gurgeh.go
type GurgehView struct {
	shell       *pkgtui.ShellLayout
	chatPanel   *pkgtui.ChatPanel
	chatHandler *GurgehChatHandler  // Spec-aware handler
	onboarding  *GurgehOnboardingView
}

type GurgehChatHandler struct {
	client   *autarch.Client
	specID   string  // Current spec being discussed
}

func (h *GurgehChatHandler) HandleMessage(ctx context.Context, msg string) (<-chan StreamMsg, error) {
	// Send prompt with current spec context to Claude
	// Return stream of events
}
```

### Bigend View (Mission Control)
Similar structure: ShellLayout + ChatPanel, but with project-centric context.

### Coldwine View (Task Orchestration)
Task-focused chat handler with task state context.

### Pollard View (Research Intelligence)
Research-context-aware streaming.

---

## 9. Key Architectural Patterns

### 1. Event-Driven Streaming (Not Buffering)
- User input → handler spawns goroutine → returns channel
- Goroutine sends StreamMsg events incrementally
- TUI polls via `waitForStreamEvent()` command
- Each chunk updates state immediately (append to message, re-render)

**Benefit**: Low-latency, memory-efficient, responsive UI even for large outputs.

### 2. Scroll Offset Model
- Single `scroll: int` field tracks position
- renderHistory() slices lines array by offset
- No need for separate "viewport" abstractions for ChatPanel
- Auto-scroll on new message (p.scroll = 0) for follow-tail

**Benefit**: O(1) scroll, simple state synchronization.

### 3. Stateful Markdown Renderer
```go
func (p *ChatPanel) markdownRenderer(width int) *glamour.TermRenderer {
	if p.mdRenderer != nil && p.mdWidth == width {
		return p.mdRenderer
	}
	r, err := glamour.NewTermRenderer(...)
	p.mdRenderer = r
	p.mdWidth = width
	return r
}
```
Caches renderer per width to avoid expensive re-init on every render.

### 4. Composer + CommandPicker Integration
```
User types "/"
    ↓
updateCommandPicker() checks p.composer.Value()
    ↓
CommandPicker.Show(query) if not already visible
    ↓
User presses Tab/Enter to select command
    ↓
Composer.SetValue("/" + command + " ")
```

### 5. Multi-Turn Continuation (SessionID Tracking)
```go
if mth, ok := p.handler.(MultiTurnHandler); ok {
	mth.SetContinue(true, e.SessionID)  // StreamDone carries SessionID
}

// Next interaction uses --resume <SessionID> in Claude CLI
```

---

## 10. Buffer & Memory Management

### ChatMessage Buffer
- **Unbounded**: No cap on message history
- **Append-only**: Messages never removed (except on ClearMessages/ResetSession)
- **Streaming appends**: TextDelta appends to last message.Content
- **Risk**: Very long conversations could exhaust memory; mitigation would require circular buffer

### Log Entry Buffer
- **Capped at 500 entries** (maxLogEntries)
- **Circular rotation**: Once full, old entries are discarded
- **AutoScroll**: GotoBottom() called on each batch

### Event Channel Buffer
- **64-entry buffer** in ClaudeChatHandler: `out := make(chan StreamMsg, 64)`
- **Non-blocking send** except when full (backpressure)

### Markdown Renderer Cache
- **Per-width caching**: Reused if width unchanged
- **No automatic invalidation**: Assumes width-based structure

---

## 11. Styling & Theme

### Color Palette (pkg/tui/colors.go)
```go
ColorPrimary   = "#7aa2f7"  // Blue (default text, headers)
ColorSecondary = "#bb9af7"  // Purple (agent role)
ColorWarning   = "#e0af68"  // Amber (fallback indicator)
ColorError     = "#f7768e"  // Red (errors)
ColorMuted     = "#565f89"  // Dark gray (secondary text)
```

### Rendering Styles
- **Agent messages**: Markdown via glamour + PaddingLeft(2)
- **User messages**: Plain text + Bold + ColorPrimary
- **Status indicator**: Spinner + "Thinking..." / "Responding..."
- **Empty state**: Italic + ColorMuted

---

## 12. Testing Infrastructure

### Test Files
- `pkg/tui/chatpanel_test.go` — ChatPanel scroll & message handling
- `pkg/tui/logpane_test.go` — LogPane entry rotation
- `internal/tui/views/gurgeh_test.go` — View integration
- `internal/tui/unified_app_test.go` — Full TUI flow

### Test Patterns
```go
// Setup
panel := NewChatPanel()
panel.SetSize(80, 20)

// Action
panel.AddMessage("user", "test")
result := panel.View()

// Assert
assert.Contains(t, result, "test")
```

---

## 13. Troubleshooting & Known Issues

### From Project CLAUDE.md & Memory
1. **lipgloss.Height() on ANSI strings**: Always use `ansi.Truncate` for visual-column slicing, not `[]rune`.
2. **Scroll mismatch**: If scroll appears broken, verify `chatPanel.scroll` is being reset to 0 on new message.
3. **Markdown rendering failures**: Glamour can fail; fallback to plain text is automatic.
4. **Viewport vs scroll offset**: ChatPanel uses manual scroll offset; DocPanel/LogPane use viewport bubble. Different models; don't mix.

---

## Summary: Architecture Decision Matrix

| Aspect | Choice | Rationale |
|--------|--------|-----------|
| **Streaming** | Channel-based events (StreamMsg) | Low-latency, type-safe, non-blocking |
| **History buffer** | []ChatMessage (unbounded) | Simplicity, append-only semantics |
| **Scroll model** | Manual offset (not viewport) | Fine-grained control, O(1) performance |
| **Auto-scroll** | p.scroll = 0 on new message | Follow-tail UX without polling |
| **Markdown** | Glamour (cached per-width) | Rich formatting, performance |
| **Layout** | ShellLayout → SplitLayout → panels | Composable, responsive fallback |
| **Log rotation** | Circular 500-entry buffer | Bounded memory, FIFO eviction |
| **Event channels** | 64-entry buffers | Backpressure safety, reasonable latency |

---

## Architectural Strengths
1. **Clean separation of concerns**: Data (ChatMessage[]), rendering (renderHistory), interaction (Update)
2. **Responsive streaming**: Non-blocking channels enable real-time UI updates
3. **Composable layout**: Panels are independently sized; nesting is explicit
4. **Type-safe events**: StreamMsg union prevents invalid state transitions
5. **Backward-compatible scroll**: Manual offset works with any layout, no abstraction leakage

## Extension Points for Future Work
1. **Message persistence**: Implement unbounded buffer replacement (e.g., RocksDB index)
2. **Advanced filtering**: Search/grep in chat history
3. **Rich media**: Embed images, code blocks with syntax highlighting
4. **Agent panel multiplexing**: Show multiple agent outputs side-by-side
5. **Checkpoint/restore**: Save scroll position, continue reading later
