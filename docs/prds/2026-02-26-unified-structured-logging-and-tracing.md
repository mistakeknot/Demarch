# PRD: Unified Structured Logging and Tracing Across Boundaries

**Bead:** iv-yy1l3
**Date:** 2026-02-26
**Sprint:** iv-5zoaq

## Problem

Demarch has 4 incompatible logging patterns across its 3 architectural layers (L1 kernel, L2 OS, L3 plugins) with no structured output and no cross-layer trace correlation. Debugging multi-agent workflows requires manually correlating `session_id` across disparate stderr streams — the event bus has `TraceID`/`SpanID` fields in `EventEnvelope` but they're siloed from the audit log, interband, and bash hooks.

## Solution

Adopt `log/slog` (Go stdlib) for all Go code, JSON log helpers (`lib-log.sh`) for bash hooks, and lightweight environment variable trace propagation (`IC_TRACE_ID`, `IC_SPAN_ID`) across process boundaries. No external dependencies — OTel-compatible format for future adoption.

## Features

### F1: Observability Package (`internal/observability/`)

**What:** Foundation package providing slog handler factory, trace context extraction from environment, and span ID generation.

**Acceptance criteria:**
- [ ] `NewHandler(w io.Writer)` returns `slog.JSONHandler` with trace context attributes auto-injected
- [ ] `TraceFromEnv()` reads `IC_TRACE_ID`, `IC_SPAN_ID`, `IC_PARENT_SPAN_ID` from environment
- [ ] `GenerateSpanID()` returns 16-char hex string using `crypto/rand`
- [ ] `GenerateTraceID()` returns 32-char hex string using `crypto/rand`
- [ ] Handler adds `trace_id`, `span_id`, `component` attributes to every log record when env vars present
- [ ] Unit tests cover: env parsing, span generation, handler output format

### F2: Intercore slog Migration

**What:** Replace all `fmt.Fprintf(os.Stderr)` and `fmt.Fprintf(logw)` calls in Intercore with `slog` calls using the F1 observability package.

**Acceptance criteria:**
- [ ] All `cmd/ic/*.go` files (~17) migrated from `fmt.Fprintf(os.Stderr, "ic: ...")` to `slog.Error()`/`slog.Warn()`
- [ ] `internal/event/handler_log.go`, `handler_hook.go`, `handler_spawn.go` migrated from `fmt.Fprintf(logw)` to `slog`
- [ ] `internal/portfolio/relay.go` migrated from `fmt.Fprintf(logw)` to `slog`
- [ ] `internal/sentinel/sentinel.go` migrated from `fmt.Fprintf(os.Stderr)` to `slog`
- [ ] `cmd/ic/main.go` initializes slog default handler via `observability.NewHandler(os.Stderr)`
- [ ] `--verbose` flag maps to `slog.LevelInfo`, `-vv` maps to `slog.LevelDebug`, default is `slog.LevelWarn`
- [ ] `IC_LOG_LEVEL` env var overrides flag-based level (debug/info/warn/error)
- [ ] JSON output format always (no text handler)
- [ ] `--json` flag for structured data output (stdout) remains unchanged — separate concern from logging (stderr)
- [ ] All existing tests pass with new logging (no behavioral change)
- [ ] No new external dependencies added

### F3: Trace Schema and Event Wiring

**What:** Add `trace_id` column to `audit_log` table and wire environment trace context into `EventEnvelope` population.

**Acceptance criteria:**
- [ ] Migration v23: `ALTER TABLE audit_log ADD COLUMN trace_id TEXT NOT NULL DEFAULT ''`
- [ ] `internal/event/store.go` `defaultDispatchEnvelope` reads `IC_TRACE_ID`/`IC_SPAN_ID` from env when present (overrides synthetic defaults)
- [ ] `defaultCoordinationEnvelope` same env var reading
- [ ] `internal/phase/event_envelope.go` default envelope reads from env
- [ ] `internal/audit/` (or wherever audit_log writes happen) populates `trace_id` from env
- [ ] `ic events tail` output includes trace_id when present
- [ ] Migration test covers v22→v23 upgrade
- [ ] Existing event tests pass (additive change, no breakage)

### F4: Bash Log Helpers (`lib-log.sh`)

**What:** Shared bash library providing structured JSON logging functions for Clavain hooks and plugins.

**Acceptance criteria:**
- [ ] `hooks/lib-log.sh` provides: `log_debug`, `log_info`, `log_warn`, `log_error`
- [ ] Output format: `{"level":"info","msg":"...","ts":"2026-02-26T12:00:00Z","trace_id":"...","span_id":"...","component":"..."}` to stderr
- [ ] `IC_LOG_LEVEL` env var filters output (debug < info < warn < error), default: `info`
- [ ] `generate_trace_id` function: 32-char hex via `/dev/urandom`
- [ ] `generate_span_id` function: 16-char hex via `/dev/urandom`
- [ ] Auto-reads `IC_TRACE_ID`, `IC_SPAN_ID` when sourced — injects into all log calls
- [ ] `IC_LOG_COMPONENT` env var sets the `component` field (default: basename of calling script)
- [ ] Works on both Linux and macOS (portable shell, no bashisms beyond associative arrays)
- [ ] Unit tests via bats or inline test function

### F5: Clavain Trace Propagation

**What:** Wire `IC_TRACE_ID`/`IC_SPAN_ID` environment variables through the Clavain hook lifecycle so all `ic` CLI calls inherit trace context.

**Acceptance criteria:**
- [ ] `lib-intercore.sh` sets `IC_TRACE_ID` from active run ID before `ic` calls (if available)
- [ ] `lib-sprint.sh` propagates trace context through sprint lifecycle operations
- [ ] `session-start.sh` generates `IC_TRACE_ID` (from run_id or fresh) and `IC_SPAN_ID` at session start
- [ ] `session-handoff.sh` passes trace context to successor session
- [ ] `lib-discovery.sh` uses `log_info`/`log_warn` instead of bare `echo >&2`
- [ ] At least 3 key hooks migrated from `echo >&2` to `log_*` functions as proof-of-concept
- [ ] Trace context visible in `ic events tail` output after a hook → ic CLI → event bus flow

### F6: Plugin Adoption Guide and Python Formatter

**What:** Documentation and optional helpers for L3 plugin adoption of structured logging and trace propagation.

**Acceptance criteria:**
- [ ] `docs/guide-plugin-logging.md` documents the structured logging convention for all 3 languages (Go/bash/Python)
- [ ] Python `interlogger.py` (or similar) provides JSON formatter reading `IC_TRACE_ID` from env
- [ ] Go MCP server template shows slog setup with `observability.NewHandler()`
- [ ] At least 1 Go plugin MCP server migrated as reference (intermap or interlock)
- [ ] At least 1 Python plugin migrated as reference (intersearch or intermap Python layer)
- [ ] `lib-log.sh` published to a location plugins can source (symlink or copy convention documented)

## Non-goals

- OpenTelemetry SDK integration (future iteration)
- Tracing backend (Jaeger/Zipkin/Tempo) deployment
- Log aggregation or centralized log storage
- Changes to `--json` stdout data output format
- Breaking changes to `EventEnvelope` wire format
- Mandatory plugin migration (L3 is opt-in)
- Interband envelope changes (env vars cover all paths)

## Dependencies

- Go 1.22+ (provides `log/slog` since 1.21)
- Existing schema migration framework (from iv-npvnv — just completed)
- `EventEnvelope` struct (already has TraceID/SpanID/ParentSpanID fields)

## Open Questions

None — all resolved during brainstorm:
- Log format: JSON always
- Default level: warn (--verbose=info, -vv=debug)
- Span format: 16-char hex (OTel-compatible)
- Propagation: environment variables only (no interband changes)
