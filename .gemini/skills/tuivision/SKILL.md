---
name: tuivision
description: "TUI automation and visual testing - Playwright for terminal applications. Spawn, interact with, and screenshot TUI apps."
---
# Gemini Skill: tuivision

You have activated the tuivision capability.

## Base Instructions
# tuivision Development Guide

## Quick Reference

| Item | Value |
|------|-------|
| Language | TypeScript (ESM) |
| Node Version | 20+ |
| Build | `npm run build` |
| Entry Point | `dist/index.js` |

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                       tuivision                          │
├─────────────────────────────────────────────────────────┤
│  MCP Tools:                                              │
│  - spawn_tui    → Start a TUI in virtual terminal       │
│  - send_input   → Send keystrokes (raw or named keys)   │
│  - get_screen   → Get terminal state as JSON/text       │
│  - get_screenshot → Render to PNG/SVG image             │
│  - resize_session → Change terminal dimensions          │
│  - list_sessions  → List active sessions                │
│  - close_session  → Clean up a session                  │
├─────────────────────────────────────────────────────────┤
│  Core Components:                                        │
│  - SessionManager: PTY lifecycle, session tracking      │
│  - TerminalRenderer: xterm.js headless wrapper          │
│  - screenshot.ts: PNG/SVG rendering via node-canvas     │
└─────────────────────────────────────────────────────────┘
```

## Directory Structure

```
tuivision/
├── src/
│   ├── index.ts              # MCP server entry point
│   ├── session-manager.ts    # PTY session management
│   ├── terminal-renderer.ts  # xterm.js headless wrapper
│   ├── screenshot.ts         # Image rendering
│   └── tools/                # MCP tool implementations
│       ├── spawn.ts
│       ├── input.ts
│       ├── screen.ts
│       ├── screenshot.ts
│       ├── resize.ts
│       ├── list.ts
│       └── close.ts
├── dist/                     # Compiled output
├── package.json
└── tsconfig.json
```

## Development Setup

### Prerequisites

```bash
# System dependencies for node-canvas
apt install build-essential python3 libcairo2-dev libpango1.0-dev \
  libjpeg-dev libgif-dev librsvg2-dev

# Node dependencies
npm install
```

### Build & Test

```bash
npm run build

# Quick test
node -e "
const { SessionManager } = require('./dist/session-manager.js');
const { renderToPng } = require('./dist/screenshot.js');
const fs = require('fs');

const sm = new SessionManager();
const s = sm.spawn({ command: 'htop', cols: 120, rows: 35 });
setTimeout(() => {
  const screen = s.renderer.getScreenState();
  fs.writeFileSync('/tmp/test.png', renderToPng(screen));
  console.log('Screenshot saved to /tmp/test.png');
  sm.dispose();
}, 2000);
"
```

## Claude Code Integration

Add to MCP configuration:

```json
{
  "mcpServers": {
    "tuivision": {
      "command": "node",
      "args": ["/root/projects/Interverse/plugins/tuivision/dist/index.js"]
    }
  }
}
```

## MCP Tools Reference

### spawn_tui

```json
{
  "command": "htop",
  "cols": 80,
  "rows": 24,
  "env": { "TERM": "xterm-256color" },
  "cwd": "/home/user",
  "use_script": false,
  "answer_queries": false
}
```

Returns: `{ session_id, pid, cols, rows }`

**TTY Compatibility** (for Bubble Tea, Charm, and similar frameworks):
- `use_script`: Wraps command in `script` for `/dev/tty` access
- `answer_queries`: Auto-responds to ANSI terminal queries (ESC[6n, ESC]11;?, etc.)

For Bubble Tea apps, set both to `true`.

### send_input

```json
{
  "session_id": "abc-123",
  "input": "hello",           // Raw text
  "key": "enter",             // Named key
  "keys": ["up", "up", "enter"]  // Multiple keys
}
```

Named keys: `enter`, `tab`, `escape`, `backspace`, `delete`, `up`, `down`, `left`, `right`, `home`, `end`, `pageup`, `pagedown`, `f1`-`f12`, `ctrl+c`, `ctrl+d`, `ctrl+z`, `ctrl+l`, etc.

### get_screen

```json
{
  "session_id": "abc-123",
  "format": "text"  // or "compact" or "full"
}
```

- `text`: Plain text only
- `compact`: Text + cursor position
- `full`: Complete cell data with colors and attributes

### get_screenshot

```json
{
  "session_id": "abc-123",
  "format": "png",     // or "svg"
  "font_size": 14,
  "show_cursor": true
}
```

Returns: Image content block (base64 PNG or raw SVG)

## Code Patterns

### xterm.js Headless Import

The headless package exports CommonJS, so use:

```typescript
import xtermHeadless from "@xterm/headless";
const { Terminal } = xtermHeadless;
type TerminalType = InstanceType<typeof Terminal>;
```

### Color Extraction

Cell attribute methods return 0 or 1, not boolean:

```typescript
const bold = cell.isBold() === 1;
const fg = cell.getFgColor();     // 0-255 for palette
const isFgDefault = cell.isFgDefault();  // true if default fg
```

### Session Cleanup

Sessions auto-cleanup after 30 minutes. Manual cleanup:

```typescript
sessionManager.closeSession(sessionId);
sessionManager.dispose();  // Cleanup all sessions
```

## Known Issues

1. **node-canvas fonts**: May need system fonts installed for best rendering
2. **PTY on Windows**: node-pty has different behavior on Windows
3. **Large screens**: Very large terminal sizes may impact performance
4. **Bubble Tea apps**: Require `use_script: true` and `answer_queries: true` to render properly (they query terminal capabilities before rendering)

## Dependencies

| Package | Purpose |
|---------|---------|
| @modelcontextprotocol/sdk | MCP server framework |
| @xterm/headless | Terminal emulation (ANSI parsing) |
| node-pty | PTY management |
| canvas | PNG rendering |
| zod | Input validation |
| uuid | Session IDs |


