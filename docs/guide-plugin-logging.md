# Plugin Structured Logging Guide

This guide explains how to adopt structured JSON logging in Demarch plugins. Structured logging enables trace correlation across the kernel (Intercore), OS (Clavain), and plugins (Interverse) using shared environment variables.

## Why Structured Logging?

Demarch agents span multiple processes: the `ic` kernel CLI, Clavain bash hooks, Go MCP servers, and Python analysis bridges. When something goes wrong, ad-hoc `fmt.Fprintf` and `print()` calls produce unstructured text that cannot be correlated across process boundaries.

Structured logging solves this by:
- Outputting JSON lines to stderr (machine-parseable, greppable)
- Including `trace_id` and `span_id` fields from environment variables
- Using consistent field names across Go, Bash, and Python
- Enabling `ic events tail` to show correlated traces across all components

## Log Schema

All three language runtimes produce JSON with these common fields:

```json
{
  "level": "info",
  "msg": "description of what happened",
  "ts": "2026-02-26T14:30:00Z",
  "component": "plugin-name",
  "trace_id": "abcdef1234567890abcdef1234567890",
  "span_id": "1234567890abcdef"
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `level` | string | yes | `debug`, `info`, `warn`, `error` |
| `msg` | string | yes | Human-readable message |
| `ts` | string | yes | ISO 8601 UTC timestamp |
| `component` | string | recommended | Plugin or module name |
| `trace_id` | string | if available | From `IC_TRACE_ID` env var |
| `span_id` | string | if available | From `IC_SPAN_ID` env var |

Additional key-value fields may be added for context (e.g., `"error": "..."`, `"run_id": "..."`, `"file": "..."`).

## Go Plugins

Go plugins with MCP servers (intermap, intermux, interserve, interlock) use `log/slog` from the standard library.

### Standalone Pattern (Recommended for Plugins)

Since Go plugins have independent `go.mod` files and cannot import `intercore/internal/observability` without a module dependency, use `slog.NewJSONHandler` directly:

```go
package main

import (
    "log/slog"
    "os"
)

func main() {
    // Set up structured logging to stderr
    level := slog.LevelWarn
    switch os.Getenv("IC_LOG_LEVEL") {
    case "debug":
        level = slog.LevelDebug
    case "info":
        level = slog.LevelInfo
    case "warn":
        level = slog.LevelWarn
    case "error":
        level = slog.LevelError
    }

    handler := slog.NewJSONHandler(os.Stderr, &slog.HandlerOptions{Level: level})

    // Inject trace context from environment
    var attrs []slog.Attr
    if traceID := os.Getenv("IC_TRACE_ID"); traceID != "" {
        attrs = append(attrs, slog.String("trace_id", traceID))
    }
    if spanID := os.Getenv("IC_SPAN_ID"); spanID != "" {
        attrs = append(attrs, slog.String("span_id", spanID))
    }
    if len(attrs) > 0 {
        handler = handler.WithAttrs(attrs).(*slog.JSONHandler)
    }

    slog.SetDefault(slog.New(handler))

    // Now use slog throughout your plugin
    slog.Info("server starting", "version", "0.1.0")
    // ...
    if err := runServer(); err != nil {
        slog.Error("server failed", "error", err)
        os.Exit(1)
    }
}
```

### Using the Observability Package (Intercore-Adjacent Code)

Code within the `core/intercore` module can import the observability package directly:

```go
import "github.com/mistakeknot/intercore/internal/observability"

func main() {
    level := observability.ParseLevel(os.Getenv("IC_LOG_LEVEL"))
    slog.SetDefault(slog.New(observability.NewHandler(os.Stderr, level)))
}
```

The `observability.NewHandler` function automatically reads `IC_TRACE_ID`, `IC_SPAN_ID`, and `IC_PARENT_SPAN_ID` from the environment and injects them as attributes on every log record.

### Key Points for Go

- Always log to `os.Stderr` — stdout is reserved for MCP protocol communication
- Use `slog.Error("description", "error", err)` instead of `fmt.Fprintf(os.Stderr, ...)`
- Default level should be `slog.LevelWarn` to avoid noisy output during normal operation
- The `IC_LOG_LEVEL` env var lets users increase verbosity at runtime

## Bash Plugins

Bash hooks and scripts source `lib-log.sh` from the Clavain hooks directory.

### Setup

```bash
#!/usr/bin/env bash
# Source logging helpers (available automatically if lib.sh is sourced)
source "${BASH_SOURCE[0]%/*}/lib-log.sh" 2>/dev/null || true

# Or source from a known path
CLAVAIN_HOOKS="${HOME}/.claude/plugins/cache/interagency-marketplace/clavain/latest/hooks"
source "${CLAVAIN_HOOKS}/lib-log.sh" 2>/dev/null || true
```

If your hook already sources `lib.sh`, logging is automatically available — `lib.sh` sources `lib-log.sh` internally.

### Usage

```bash
# Basic logging
log_info "starting analysis"
log_warn "file not found, falling back to default"
log_error "compilation failed"
log_debug "processing file" file="src/main.go"

# Key-value pairs for structured data
log_info "scan complete" files=42 duration_ms=150
log_error "hook failed" hook="pre-commit" exit_code=1

# Generate trace context for sub-operations
new_span=$(generate_span_id)
IC_SPAN_ID="$new_span" log_info "sub-operation started"
```

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `IC_LOG_LEVEL` | `info` | Minimum log level: `debug`, `info`, `warn`, `error` |
| `IC_TRACE_ID` | (unset) | 32-char hex trace ID, set by session-start.sh |
| `IC_SPAN_ID` | (unset) | 16-char hex span ID |
| `IC_LOG_COMPONENT` | caller basename | Override the component name in log output |

### Output

All output goes to stderr as JSON lines:

```json
{"level":"info","msg":"scan complete","ts":"2026-02-26T14:30:00Z","component":"my-hook","trace_id":"abcdef...","files":"42","duration_ms":"150"}
```

### Helper Functions

| Function | Description |
|----------|-------------|
| `log_debug "msg" [k=v ...]` | Debug level (filtered by default) |
| `log_info "msg" [k=v ...]` | Info level |
| `log_warn "msg" [k=v ...]` | Warning level |
| `log_error "msg" [k=v ...]` | Error level |
| `generate_trace_id` | Generate 32-char hex trace ID |
| `generate_span_id` | Generate 16-char hex span ID |

## Python Plugins

Python plugins (intersearch, interject, intercache, intermap Python bridge) use the `InterFormatter` from the shared SDK.

### Setup

The formatter lives at `sdk/interbase/python/interlogger.py`. Copy it into your plugin or add the SDK path to `PYTHONPATH`.

```python
# Replace this:
import logging
logger = logging.getLogger(__name__)

# With this:
from interlogger import setup_logging
logger = setup_logging("my-plugin")
```

### Usage

```python
# Basic logging
logger.info("server starting")
logger.warning("rate limit approaching")
logger.error("database connection failed")

# Structured extra fields
logger.info("indexed files", extra={"count": 42, "project": "/home/user/myproject"})

# Exception logging (includes error field in JSON)
try:
    process_file(path)
except Exception:
    logger.exception("file processing failed")
```

### Output

All output goes to stderr as JSON lines:

```json
{"level": "info", "msg": "indexed files", "ts": "2026-02-26T14:30:00Z", "component": "intersearch", "trace_id": "abcdef...", "count": 42, "project": "/home/user/myproject"}
```

### API Reference

**`InterFormatter`** — `logging.Formatter` subclass that produces JSON lines with trace context.

**`setup_logging(name, level="INFO")`** — Configure a named logger with JSON output to stderr.
- `name`: Logger name (appears as `component` in JSON)
- `level`: Default log level, overridden by `IC_LOG_LEVEL` env var
- Returns: configured `logging.Logger`

### Environment Variables

Same as Bash: `IC_LOG_LEVEL`, `IC_TRACE_ID`, `IC_SPAN_ID`. The formatter reads these on every log call (not cached at setup time), so runtime changes take effect immediately.

## Trace Propagation

### How Trace Context Flows

1. **Session start**: `session-start.sh` generates `IC_TRACE_ID` (32-char hex) and `IC_SPAN_ID` (16-char hex) and writes them to `CLAUDE_ENV_FILE`
2. **Environment inheritance**: All child processes (hooks, `ic` CLI, MCP servers) inherit these env vars automatically via the process environment
3. **Kernel logging**: The `ic` binary reads `IC_TRACE_ID` from env and includes it in slog output and event envelopes
4. **Audit trail**: The `audit_log` table includes a `trace_id` column populated from `IC_TRACE_ID`
5. **Event envelopes**: `EventEnvelope.TraceID` is populated from env, falling back to run ID

```
session-start.sh
  |-- generates IC_TRACE_ID + IC_SPAN_ID
  |-- exports to CLAUDE_ENV_FILE
  |
  +-- hook-1.sh (inherits IC_TRACE_ID)
  |     |-- log_info "..." --> JSON with trace_id
  |     +-- ic run advance  --> ic reads IC_TRACE_ID from env
  |
  +-- mcp-server (inherits IC_TRACE_ID)
  |     +-- slog.Info("...") --> JSON with trace_id
  |
  +-- python-bridge (inherits IC_TRACE_ID)
        +-- logger.info("...") --> JSON with trace_id
```

### Generating New Span IDs

When a plugin starts a sub-operation that you want to trace independently, generate a new span ID while preserving the parent trace:

**Go:**
```go
import "crypto/rand"
import "encoding/hex"

func newSpanID() string {
    b := make([]byte, 8)
    rand.Read(b)
    return hex.EncodeToString(b)
}
```

**Bash:**
```bash
new_span=$(generate_span_id)
export IC_PARENT_SPAN_ID="$IC_SPAN_ID"
export IC_SPAN_ID="$new_span"
```

**Python:**
```python
import os
import secrets
new_span = secrets.token_hex(8)
os.environ["IC_PARENT_SPAN_ID"] = os.environ.get("IC_SPAN_ID", "")
os.environ["IC_SPAN_ID"] = new_span
```

## Testing Trace Correlation

### Verify Environment Variables

```bash
# In a Claude Code session:
echo "trace=$IC_TRACE_ID span=$IC_SPAN_ID"
# Expected: 32-char hex trace, 16-char hex span
```

### Verify JSON Output

```bash
# Test bash logging
source os/clavain/hooks/lib-log.sh
IC_TRACE_ID=test123 log_info "test" key=val
# Expected on stderr: {"level":"info","msg":"test","ts":"...","component":"bash","trace_id":"test123","key":"val"}

# Test Python logging
cd sdk/interbase/python
IC_TRACE_ID=test123 python3 -c "
from interlogger import setup_logging
logger = setup_logging('test')
logger.info('hello')
"
# Expected on stderr: {"level": "info", "msg": "hello", "ts": "...", "component": "test", "trace_id": "test123"}
```

### Verify Event Correlation

```bash
# After running an ic operation with IC_TRACE_ID set:
ic events tail --all | jq '.trace_id'
# Should show the same trace_id as your IC_TRACE_ID env var
```

### Verify Audit Trail

```bash
# Check that audit entries include trace_id
ic --db .clavain/intercore.db <<< "SELECT trace_id FROM audit_log ORDER BY created_at DESC LIMIT 5;"
```

## Migration Checklist

When migrating a plugin to structured logging:

- [ ] Replace `fmt.Fprintf(os.Stderr, ...)` (Go) or `print(..., file=sys.stderr)` (Python) with structured log calls
- [ ] Replace `logging.getLogger(__name__)` (Python) with `setup_logging("plugin-name")`
- [ ] Ensure all log output goes to stderr (stdout is reserved for MCP protocol)
- [ ] Include meaningful context in log messages: run IDs, file paths, durations, error details
- [ ] Test with `IC_LOG_LEVEL=debug` to verify all levels work
- [ ] Test with `IC_TRACE_ID=test123` to verify trace context appears in output
- [ ] Keep usage/help text as plain `fmt.Fprintf(os.Stderr, ...)` — only operational messages become structured logs
