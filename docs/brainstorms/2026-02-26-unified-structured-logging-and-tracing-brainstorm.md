# Unified Structured Logging and Tracing Across Boundaries

**Bead:** iv-yy1l3
**Date:** 2026-02-26
**Status:** Brainstorm

## What We're Building

A unified observability layer spanning all three Demarch architectural layers:

1. **Structured logging** — Replace ad-hoc `fmt.Fprintf(os.Stderr)` / `echo >&2` with machine-parseable structured output using `log/slog` (Go) and JSON log helpers (bash)
2. **Distributed tracing** — Propagate `trace_id` + `span_id` across process boundaries via environment variables (`IC_TRACE_ID`, `IC_SPAN_ID`), linking the event bus, audit log, interband sidebands, and bash hooks into a single causal chain

## Why This Approach

### Current State (Research Findings)

The codebase has 4 incompatible logging patterns:

| Layer | Current Pattern | Structured? | Trace Context |
|-------|----------------|-------------|---------------|
| ic CLI (`cmd/ic/`) | `fmt.Fprintf(os.Stderr, "ic: %s: %v")` | No | Via `--json` output only |
| ic scheduler | `log/slog` (stdlib) — 24 call sites | Yes | No |
| Clavain hooks | `echo "..." >&2` / `printf "..." >&2` | No | `session_id` only |
| Plugin hooks (bash) | `echo "[plugin] ..." >&2` / `echo "WARN: ..." >&2` | No | None |
| Plugin MCPs (Go) | `fmt.Fprintf(os.Stderr, "name: %v")` (fatal only) | No | None |
| Plugin MCPs (Python) | `logging.getLogger(__name__)` | Stdlib logger | None |
| Autarch | `log/slog` + custom TUI `LogHandler` | Yes | No |

The event bus has rich trace context (`EventEnvelope` has `TraceID`, `SpanID`, `ParentSpanID`) but it's **siloed** — not linked to `audit_log`, interband, or cross-process propagation. The only cross-layer correlation today is `CLAUDE_SESSION_ID`.

### Design Rationale

- **`log/slog` for Go**: Already used by scheduler (24 sites) and Autarch (130+ sites). Zero new dependencies — stdlib since Go 1.21. Extends existing patterns rather than introducing new ones.
- **JSON log helpers for bash**: Functions like `log_info`, `log_warn`, `log_error`, `log_debug` that emit JSON lines to stderr. Machine-parseable, grep-friendly, and carry trace context automatically.
- **Environment variable propagation for tracing**: `IC_TRACE_ID` and `IC_SPAN_ID` env vars. Simple, universal, works across all shells and spawned processes. No OpenTelemetry SDK dependency — can adopt OTel exporters later if needed.
- **Bottom-up rollout (L1 → L2 → L3)**: Intercore first (slog migration + trace schema), then Clavain (bash helpers + env propagation), then plugins opt-in. Each layer delivers standalone value.

## Key Decisions

1. **Go logging library: `log/slog` (stdlib)** — No external deps. Already proven in scheduler and Autarch. Autarch's custom `LogHandler` (TUI-aware, batched delivery) becomes a reference implementation for other consumers.

2. **Bash logging: JSON line helpers in `lib-log.sh`** — New shared library sourced by hooks. Emits `{"level":"info","msg":"...","ts":"...","trace_id":"...","span_id":"...","component":"clavain"}` to stderr. Log level filtering via `IC_LOG_LEVEL` env var (default: `info`).

3. **Trace propagation: Environment variables** — `IC_TRACE_ID` (= run_id when available, generated UUID otherwise) and `IC_SPAN_ID` (generated per operation). Parent span carried via `IC_PARENT_SPAN_ID`. Bash hooks set these before calling `ic` commands; `ic` reads them and populates `EventEnvelope`.

4. **Schema changes: `trace_id` column on `audit_log`** — Links audit entries to the event bus trace chain. Migration v23 (additive ALTER TABLE).

5. **No OpenTelemetry SDK** — Lightweight custom propagation now. The env var names and trace_id format are chosen to be OTel-compatible (128-bit hex trace ID, 64-bit hex span ID) so future OTel adoption is a non-breaking extension.

6. **Python plugins: stdlib `logging` with JSON formatter** — Add a shared `InterLogger` or JSON formatter that plugins can import. Reads `IC_TRACE_ID` from env and includes it in log records. Optional — plugins can adopt at their own pace.

## Trace Propagation Flow

```
Claude Code session
  │ CLAUDE_SESSION_ID=abc123
  │
  ├─ hook: session-start.sh
  │    source lib-log.sh
  │    export IC_TRACE_ID=$run_id   (or generate if no run)
  │    export IC_SPAN_ID=$(generate_span)
  │    log_info "session started" session_id="$CLAUDE_SESSION_ID"
  │
  ├─ ic run advance $run_id
  │    reads IC_TRACE_ID, IC_SPAN_ID from env
  │    slog.Info("advancing phase", "trace_id", traceID, "span_id", spanID)
  │    sets EventEnvelope.TraceID = traceID
  │    sets audit_log.trace_id = traceID
  │
  ├─ ic dispatch spawn --name=agent-1 ...
  │    child process inherits IC_TRACE_ID (same trace)
  │    generates new IC_SPAN_ID (new span)
  │    sets IC_PARENT_SPAN_ID = caller's span
  │    EventEnvelope.ParentSpanID = parent span
  │
  └─ interband sideband write
       Envelope.SessionID already present
       trace_id available in env for correlation
```

## Scope Per Layer

### L1: Intercore (Go)

- Migrate `cmd/ic/*.go` from `fmt.Fprintf(os.Stderr)` to `slog` (~17 subcommand files)
- Migrate `internal/event/handler_log.go`, `handler_hook.go`, `handler_spawn.go` from `fmt.Fprintf(logw)` to `slog`
- Migrate `internal/portfolio/relay.go` and `internal/sentinel/sentinel.go`
- Add `internal/observability/` package: slog handler factory, trace context extraction from env, span ID generation
- Add `trace_id` column to `audit_log` table (migration v23)
- Populate `EventEnvelope.TraceID`/`SpanID` from env vars (extend `defaultDispatchEnvelope`, `defaultCoordinationEnvelope`)
- Keep `--json` flag behavior unchanged (structured data output is separate from structured logging)

### L2: Clavain (Bash)

- New `hooks/lib-log.sh`: `log_info`, `log_warn`, `log_error`, `log_debug` functions
- JSON line format to stderr with `trace_id`, `span_id`, `component`, `timestamp`
- `IC_LOG_LEVEL` env var for filtering (debug/info/warn/error)
- `generate_span()` function using `/dev/urandom` or `openssl rand`
- Update `lib-intercore.sh` to set `IC_TRACE_ID` before `ic` calls
- Update `lib-sprint.sh` to propagate trace context through sprint lifecycle
- Migrate key hooks (`session-start.sh`, `session-handoff.sh`) to use `log_*` functions

### L3: Plugins (opt-in)

- Publish `lib-log.sh` as a shared library plugins can source
- Go MCP servers: add slog setup in `main.go` (read `IC_TRACE_ID` from env)
- Python MCP servers: provide JSON formatter that reads `IC_TRACE_ID`
- Document the convention in plugin development guide
- Migration path: plugins adopt at their own pace, no forced upgrade

## What We're NOT Building

- **No OpenTelemetry SDK** — env var propagation is sufficient for now
- **No tracing backend** (Jaeger, Zipkin, Tempo) — structured logs + trace IDs enable `grep`/`jq` correlation
- **No log aggregation service** — logs stay on stderr, consumed by callers or redirected to files
- **No changes to `--json` output format** — structured logging is diagnostic (stderr), not data output (stdout)
- **No breaking changes to EventEnvelope** — only additive population of existing fields
- **No mandatory plugin migration** — L3 adoption is opt-in

## Open Questions

1. **slog handler for ic CLI**: Should `ic` use `slog.NewJSONHandler` (JSON to stderr) or `slog.NewTextHandler` (human-readable to stderr)? JSON is more consistent with bash helpers but less human-friendly for direct CLI use. Could be controlled by `IC_LOG_FORMAT=json|text` env var.

2. **Log level default**: Should `ic` default to `warn` (quiet, only errors/warnings) or `info` (chattier but more useful for debugging)? The `--verbose` flag already exists — could map to `debug` level.

3. **Span ID format**: 16-char hex (OTel-compatible, 64-bit) or shorter base36 (matches run_id format)? Hex is future-proof for OTel but less ergonomic.

4. **Interband trace enrichment**: Should we also add `trace_id` to the interband `Envelope` struct (belt + suspenders) or rely solely on env vars? Env vars cover all paths; interband enrichment would be redundant but explicit.

## Estimated Scope

- **L1 (Intercore)**: ~15-20 files touched, 1 migration, 1 new package
- **L2 (Clavain)**: ~5-8 files touched, 1 new lib
- **L3 (Plugins)**: Documentation + optional adoption helpers
- **Risk**: Low for logging (additive), medium for tracing (cross-cutting env var contract)
