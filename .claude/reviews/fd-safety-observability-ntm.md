# NTM Safety & Observability Patterns - Analysis for Demarch

**Source:** `/home/mk/projects/Demarch/research/ntm/internal/`
**Date:** 2026-02-22
**Scope:** Safety, observability, cost tracking, audit, privacy, context management, resilience

---

## Executive Summary

NTM (by Dicklesworthstone) implements a comprehensive safety and observability stack for multi-agent orchestration across Claude, Codex, and Gemini agents running in tmux sessions. The codebase contains ~15 distinct subsystems totaling roughly 8,000+ lines of production Go code (excluding tests). The patterns are mature, well-tested, and directly applicable to Demarch's Intercore/Interverse architecture.

**Key finding:** NTM's strongest patterns are its tamper-evident audit trail, multi-strategy context estimation, proactive handoff generation, and the 6-invariant enforcement framework. These should be Demarch's top adoption priorities.

---

## 1. Approval Gates & Human-in-the-Loop Workflows

**Source:** `internal/approval/engine.go` (533 lines)

### Pattern Summary

The approval engine implements a full request/approve/deny lifecycle with:

- **SLB (Two-Person Rule):** Enforces that the approver cannot be the requester for sensitive operations. Delegates to an external SLB adapter when available, with graceful fallback to internal approvals.
- **Configurable Expiry:** Approvals expire after 24 hours by default, with per-request override capability.
- **Async Wait with Channel-Based Notification:** `WaitForApproval()` blocks on a per-approval channel that gets signaled on approve/deny/expire, with context-based timeout.
- **Event-Driven Architecture:** Every state transition emits events to an EventBus (`approval.requested`, `approval.approved`, `approval.denied`, `approval.expired`).
- **Best-Effort Notifications:** Notification failures never block the approval operation itself.
- **Stale Expiration Sweeping:** `ExpireStale()` batch-expires all pending approvals past their deadline.

### Key Types

```go
type RequestParams struct {
    Action        string        // "force_release", etc.
    Resource      string        // What's being acted on
    Reason        string        // Why approval is needed
    RequestedBy   string        // Agent or user identity
    CorrelationID string        // For distributed tracing
    RequiresSLB   bool          // Two-person rule
    ExpiresIn     time.Duration // Override default
}
```

### Relevance to Demarch

**High priority.** Interlock already handles file reservations; adding an approval engine for force-release and destructive operations would close a safety gap. The SLB pattern is directly applicable to multi-agent scenarios where one agent should not approve its own escalation.

**Adoption recommendation:**
- Implement in Intercore as a shared approval service
- Interlock can delegate force-release approvals to it
- Clavain can use it for destructive git operations
- Consider MCP transport for the approval request/response cycle

---

## 2. Tamper-Evident Audit Trail

**Source:** `internal/audit/logger.go` (578 lines), `internal/audit/query.go` (698 lines)

### Pattern Summary

The audit system implements a cryptographic hash-chain audit log:

- **Hash Chain:** Each entry includes `prev_hash` and a SHA-256 `checksum` computed over the entry-minus-checksum, creating a blockchain-like tamper-evident trail.
- **Sequence Numbers:** Monotonically increasing per session, enabling gap detection.
- **JSONL Storage:** Append-only `.jsonl` files organized by session and date (`{session}-{YYYY-MM-DD}.jsonl`).
- **Buffered Writing:** Configurable buffer size (default 10 entries) and flush interval (default 5 seconds) for performance.
- **Automatic Redaction:** All audit payloads are automatically redacted using the redaction engine before writing -- secrets never reach the audit log.
- **Privacy-Aware:** Checks `privacy.CanPersist()` before logging; skips entirely in privacy mode.
- **Integrity Verification:** `VerifyIntegrity()` walks the log file and validates the entire hash chain plus sequence numbers.

### Query System

The query subsystem provides:

- Time range, event type, actor, session, and target pattern filtering
- Full-text regex grep (applied pre-parse for efficiency)
- Streaming results via channels for memory efficiency
- In-memory indexing (`BuildIndex()`) for fast repeated queries
- Pagination with offset/limit
- Context-based timeout/cancellation

### Key Design Choices

```go
type AuditEntry struct {
    Timestamp   time.Time              `json:"timestamp"`
    SessionID   string                 `json:"session_id"`
    EventType   EventType              `json:"event_type"`    // command, spawn, send, response, error, state_change
    Actor       Actor                  `json:"actor"`         // user, agent, system
    Target      string                 `json:"target"`
    Payload     map[string]interface{} `json:"payload"`
    PrevHash    string                 `json:"prev_hash,omitempty"`
    Checksum    string                 `json:"checksum"`
    SequenceNum uint64                 `json:"sequence_num"`
}
```

### Relevance to Demarch

**Highest priority.** This is the most mature subsystem in NTM and fills gaps across multiple Demarch pillars:

- **Intercore:** Session-level audit logging with hash chains
- **Interlock:** File reservation/release audit trail
- **Intercheck:** Integrity verification of audit logs
- **Clavain:** Agent action audit for brainstorm-to-ship pipeline

**Adoption recommendation:**
- Port the hash-chain audit logger as a shared Go library in `core/`
- Expose via MCP for plugin use
- The auto-redaction integration is critical -- audit logs must never contain secrets

---

## 3. Cost & Token Tracking

**Source:** `internal/cost/tracker.go` (358 lines), `internal/tokens/tokens.go` (276 lines)

### Cost Tracker Pattern

- **Per-Agent, Per-Session Tracking:** Tracks input/output tokens per agent within sessions. Agents identified by pane ID.
- **Model Pricing Table:** Hardcoded USD/1K-token pricing for Claude, OpenAI, and Gemini model families with prefix matching and date-suffix normalization.
- **Three Recording Methods:**
  - `RecordPrompt()`/`RecordResponse()` -- estimates tokens from text
  - `RecordTokens()` -- records exact counts when available
- **Persistence:** JSON serialization to `.ntm/costs.json`
- **Thread-Safe:** All operations protected by `sync.RWMutex`

### Token Estimation Pattern

- **Content-Type-Aware Estimation:** Different chars-per-token ratios for code (2.8), JSON (3.0), markdown (3.5), prose (4.0)
- **Auto-Detection:** `DetectContentType()` heuristically classifies text by examining first 4KB
- **Overhead Multiplier:** `EstimateWithOverhead()` accounts for hidden system prompts and tool definitions (1.2x-2.0x)
- **Context Limits Map:** Model-to-context-limit mapping for all major providers

### Relevance to Demarch

**High priority.** Interstat already targets token efficiency benchmarking; NTM's cost tracker provides the data collection layer.

**Adoption recommendation:**
- Integrate cost tracking into Intercore's orchestration kernel
- Expose via MCP for Interstat consumption
- The content-type-aware estimation is worth adopting for Interserve's context compression
- Pricing table should be externalized (YAML/JSON) rather than hardcoded

---

## 4. Metrics Collection & Prometheus Export

**Source:** `internal/metrics/collector.go` (518 lines), `internal/metrics/prometheus.go` (113 lines)

### Pattern Summary

- **Event-Bus-Driven Collection:** Subscribes to the global event bus and auto-records blocked commands, etc.
- **Four Metric Types:** API call counts, latency distributions (min/max/avg/p50/p95/p99), blocked commands, file conflicts
- **Tier-0 Targets:** Defines baseline and target values for critical metrics with automatic comparison:
  ```go
  var Tier0Targets = map[string]float64{
      "agent_bootstrap_calls":     1.0,  // Target: 1 per agent (was 4-5)
      "destructive_cmd_incidents": 0.0,  // Target: 0
      "file_conflicts":            0.0,  // Target: 0
      "cm_query_latency_ms":       50.0, // Target: <50ms
  }
  ```
- **Snapshot & Compare:** Save named snapshots, then compare two snapshots to find improvements and regressions
- **Prometheus Exposition:** Full Prometheus text format export with `ntm_` prefix, proper `# HELP`/`# TYPE` annotations, and label sanitization
- **SQLite Persistence:** Persists counters, latencies, blocked commands, and file conflicts to database tables

### Relevance to Demarch

**Medium-high priority.** The Tier-0 targets pattern is particularly valuable -- defining non-negotiable performance/safety targets that get automatically tracked and compared.

**Adoption recommendation:**
- Define Demarch-specific Tier-0 targets for Intercore
- The Prometheus export pattern is directly usable for monitoring
- Snapshot comparison enables CI/CD regression detection

---

## 5. Performance Profiling

**Source:** `internal/profiler/profiler.go` (363 lines), `internal/profiler/recommendation.go` (221 lines)

### Pattern Summary

- **Global Singleton with No-Op Spans:** When disabled, `Start()` returns a lightweight no-op span with zero overhead
- **Phase-Based Aggregation:** Spans tagged with phases (startup, command, shutdown) for category-level timing
- **Parent-Child Span Tree:** `StartChild()` creates hierarchical spans
- **Automatic Recommendations:** Analyzes profile data against configurable thresholds:
  - Startup > 500ms = warning, > 1s = critical
  - Individual spans > 100ms = slow, > 500ms = very slow
  - Phase consuming > 50% of total time = warning
- **Memory-Bounded:** Hard cap at 10,000 spans
- **Dual Output:** JSON and human-readable text formats

### Relevance to Demarch

**Medium priority.** Useful for Intercore kernel performance tracking and Clavain pipeline profiling. The recommendations engine is a nice touch -- it turns raw profiling data into actionable suggestions.

---

## 6. Quota & Rate Limiting

**Source:** `internal/quota/` (7 files, ~500 lines total)

### Pattern Summary

- **Multi-Provider Abstraction:** Unified `QuotaInfo` struct for Claude, Codex, and Gemini with provider-specific parsers
- **PTY-Based Fetching:** Sends `/usage` commands to tmux panes and parses the output using regex patterns -- no API needed
- **Cached Polling:** 5-minute cache TTL, 2-minute poll interval, with per-pane background polling goroutines
- **Health Signals:** `IsHealthy()` (any quota < 90%), `HighestUsage()`, `IsStale()` methods on QuotaInfo
- **Provider-Specific Parsers:** Regex-based extraction of session usage, weekly usage, period/rolling usage, sonnet-specific usage, reset times, rate limit indicators

### Relevance to Demarch

**Medium priority.** The PTY-based quota fetching is clever but fragile (depends on CLI output format stability). For Demarch, consider API-based quota checking where available, with PTY as fallback.

**Adoption recommendation:**
- The `QuotaInfo` abstraction is worth adopting in Intercore
- The background polling with cache pattern is reusable
- The health threshold logic (90% = unhealthy) should inform Intermux's agent health display

---

## 7. Privacy & Redaction

**Source:** `internal/privacy/privacy.go` (210 lines), `internal/redaction/` (4 files, ~400 lines)

### Privacy Manager

- **Per-Session Privacy Mode:** Sessions can individually enable privacy mode
- **Operation-Level Granularity:** Six distinct persistence operations that can be independently blocked:
  - `OpCheckpoint`, `OpEventLog`, `OpPromptHistory`, `OpScrollback`, `OpExport`, `OpArchive`
- **Global + Session Override:** Global config sets defaults; sessions can escalate but not relax
- **Explicit Persist Escape Hatch:** `--allow-persist` flag for exports in privacy mode
- **Atomic Global Singleton:** Uses `atomic.Pointer[Manager]` for lock-free reads

### Redaction Engine

- **Four Modes:** Off, Warn (report-only), Redact (replace), Block (fail operation)
- **13 Secret Categories:** OpenAI keys, Anthropic keys, GitHub tokens, AWS access/secret keys, JWTs, Google API keys, private keys, database URLs, passwords, generic API keys, generic secrets, bearer tokens
- **Priority-Based Deduplication:** Higher-priority patterns (provider-specific, priority 100) take precedence over generic patterns (priority 30-50) when matches overlap
- **Deterministic Placeholders:** `[REDACTED:CATEGORY:hash8]` format using SHA-256 hash of category+content, enabling audit trail correlation without exposing secrets
- **Allowlist Support:** Regex-based allowlist to suppress known false positives
- **Category Disabling:** Individual categories can be disabled
- **Line/Column Enrichment:** `AddLineInfo()` adds source location to findings

### Key Detection Patterns (priority-ordered)

| Priority | Category | Pattern |
|----------|----------|---------|
| 100 | OPENAI_KEY | `sk-...T3BlbkFJ...` |
| 100 | ANTHROPIC_KEY | `sk-ant-...` |
| 100 | GITHUB_TOKEN | `gh[pousr]_...`, `github_pat_...` |
| 95 | PRIVATE_KEY | `-----BEGIN...PRIVATE KEY-----` |
| 90 | AWS_ACCESS_KEY | `AKIA...`, `ASIA...` |
| 85 | JWT | `eyJ...eyJ...` |
| 85 | DATABASE_URL | `postgres://user:pass@...` |
| 50 | PASSWORD | `password=...` |
| 40 | GENERIC_API_KEY | `api_key=...` |
| 30 | GENERIC_SECRET | `secret=...`, `token=...` |

### Relevance to Demarch

**Highest priority.** The redaction engine should be a core shared library.

**Adoption recommendation:**
- Port redaction engine to `core/` as a shared Go package
- Integrate into Intercore's message routing (redact before inter-agent communication)
- Integrate into Intercheck's code quality guards
- The privacy manager pattern is directly applicable to Clavain sessions
- The deterministic placeholder format enables post-hoc audit without secret exposure

---

## 8. Context Window Management

**Source:** `internal/context/` (12 files, ~3,500+ lines -- the largest subsystem)

### Multi-Strategy Estimation

Four estimation strategies ordered by confidence:

1. **Robot Mode (0.95 confidence):** Parses direct context usage from agent's robot mode JSON output
2. **Cumulative Tokens (0.70 confidence):** Sums input+output tokens with 0.7x compaction discount
3. **Message Count (0.60 confidence):** Estimates from message count * 1,500 tokens/message
4. **Duration/Activity (0.30 confidence):** Time-based heuristic using activity level

The monitor tries each strategy and returns the highest-confidence available result.

### Predictive Exhaustion

- **Ring Buffer Velocity Tracking:** Stores token samples in a ring buffer (64 slots), calculates tokens-per-minute velocity over a 5-minute sliding window
- **Exhaustion Prediction:** Projects when context will be exhausted based on current velocity
- **Velocity Trend Detection:** Compares first-half vs second-half velocity to detect acceleration
- **Threshold Actions:** Warn at 70% + < 15 min to exhaustion; compact at 75% + < 8 min to exhaustion

### Compaction Before Rotation

The "try compaction before rotation" philosophy:

1. **Builtin Compaction:** Try `/compact` for Claude Code (10s timeout)
2. **Summarize Request:** Ask agent for structured summary (30s timeout)
3. **Evaluate Results:** Must achieve >= 10% usage reduction to be considered successful
4. **Pre-Rotation Check:** Final check after compaction -- skip rotation if compaction brought usage below threshold

### Proactive Handoff Generation ("Compound, Don't Compact")

The `HandoffTrigger` monitors all agents and proactively generates handoff documents:

- Background polling every 30 seconds
- Warning callbacks at 70% usage, handoff generation at 75%
- Per-agent cooldown (5 minutes) to prevent spam
- Handoff enrichment from transcript files
- Written as auto-handoff files for pickup by new sessions

### Handoff Summary Structure

```go
type HandoffSummary struct {
    CurrentTask   string   // What the agent was working on
    Progress      string   // What's been accomplished
    KeyDecisions  []string // Technical decisions made
    ActiveFiles   []string // Files being modified
    Blockers      []string // Issues for next agent
    RawSummary    string   // Full agent response
    TokenEstimate int      // Summary size
}
```

### Rotation History & Audit

Full rotation lifecycle tracking with:
- Detailed `RotationRecord` entries in JSONL format
- Statistics aggregation (success rate, by agent type, by method, compaction effectiveness)
- Pruning by count and time

### Relevance to Demarch

**Highest priority.** This is the most sophisticated subsystem and directly maps to Demarch's needs:

**Adoption recommendation:**
- **Intercore:** Adopt the multi-strategy context estimation for all agent types
- **Clavain:** The predictive exhaustion + proactive handoff pattern is exactly what Clavain needs for its brainstorm-to-ship pipeline
- **Intermux:** The context monitor's per-agent state feeds directly into agent visibility
- **Interserve:** The "Compound, Don't Compact" philosophy aligns with context compression goals
- **Intercheck:** Rotation history statistics enable quality tracking

---

## 9. Health Checking

**Source:** `internal/health/health.go` (558 lines)

### Pattern Summary

- **Concurrent Per-Pane Checks:** Checks all panes in parallel (bounded to 8 concurrent) with context cancellation
- **Multi-Signal Status:** Combines process status, activity level, error patterns, and rate limit detection
- **PID-Based Liveness:** Primary signal from `/proc` child process checking; text pattern matching only as fallback
- **Progress Stage Detection:** Pattern-matching against agent output to detect work phase (starting, working, finishing, stuck, idle) with weighted confidence scoring
- **Activity Levels:** Active (< 30s since change), Idle (prompt visible), Stale (> 5m no change)
- **Aggregate Summary:** Session-level rollup with worst-status propagation

### Relevance to Demarch

**High priority.** Intermux already provides agent visibility; NTM's health checking provides the signal quality that Intermux needs.

**Adoption recommendation:**
- The PID-based liveness pattern should replace text-only detection in Intermux
- The progress stage detection is valuable for Clavain's pipeline monitoring
- The weighted confidence scoring pattern is reusable for any heuristic detection

---

## 10. Invariant Enforcement

**Source:** `internal/invariants/invariants.go` (463 lines)

### The 6 Non-Negotiable Invariants

| ID | Name | Enforcement |
|----|------|-------------|
| `no_silent_data_loss` | No Silent Data Loss | Destructive commands blocked; force-release requires SLB approval; all file ops auditable |
| `graceful_degradation` | Graceful Degradation | Missing tools = reduced capability + clear warnings, never failure |
| `idempotent_orchestration` | Idempotent Orchestration | Register = upsert; reserve = extend TTL; spawn = attach-if-exists |
| `recoverable_state` | Recoverable State | SQLite state store; event log replay; tmux survives process death |
| `auditable_actions` | Auditable Actions | Reservations, releases, blocks, approvals logged with correlation IDs |
| `safe_by_default` | Safe-by-Default | auto_push=false; auto_commit=false; force_release=approval; destructive=blocked |

### Checker Framework

The `Checker` verifies all invariants at runtime via `ntm doctor`:
- Checks for policy.yaml existence
- Checks for logs directory and audit files
- Checks for pre-commit guards
- Checks for state.db and events.jsonl
- Reports pass/warning/error per invariant with detailed findings

### Relevance to Demarch

**Highest priority.** This is the most important pattern to adopt.

**Adoption recommendation:**
- Define Demarch-specific invariants (the NTM 6 are a strong starting point)
- Implement a checker in Intercheck that runs as a hook/skill
- Enforce invariants in CI/CD (fail builds that violate invariants)
- Add Demarch-specific invariants:
  - **Plugin Isolation:** Plugins cannot modify each other's state
  - **Audit Completeness:** Every MCP call is logged
  - **Secret Hygiene:** No secrets in CLAUDE.md, settings, or logs

---

## 11. Resilience & Recovery

**Source:** `internal/resilience/manifest.go` (89 lines), `internal/resilience/monitor.go` (779 lines)

### Pattern Summary

- **Spawn Manifest:** Persisted JSON describing session configuration (agents, types, models, commands) for recovery
- **Background Health Monitoring:** Periodic health checks with configurable interval (default 10s)
- **PID-Based Crash Detection:** Primary signal from shell PID child liveness; text-pattern fallback with debounce
- **Debounced Restart:** Consecutive failure threshold (default 3) for text-based detection; PID-dead is immediate
- **IsWorking Guard:** Never interrupt agents that are actively producing output, even if error text is detected
- **Final PID Guard:** Last-second liveness check before injecting restart commands to prevent injecting keystrokes into a recovered agent
- **Rate Limit Tracking:** Per-provider rate limit history with Codex-specific AIMD throttling
- **Rotation Assistance:** Auto-suggests or auto-triggers rotation when rate limited
- **Max Restart Limit:** Configurable cap with notification on exceeded limit
- **Event Emission:** All crash/restart/rate-limit events emitted for webhooks and notifications
- **Graceful Shutdown:** WaitGroup-based cleanup of all background goroutines

### Key Safety Pattern: Three Guard Layers

```
1. PID-alive guard: Skip crash handling if process is actually running
2. IsWorking guard: Skip if agent is actively producing output
3. Final PID guard: Last check before injecting restart command
```

This prevents the most dangerous failure mode: injecting spawn commands as literal keystrokes into a running agent.

### Relevance to Demarch

**High priority.** Intercore needs this level of resilience sophistication.

**Adoption recommendation:**
- The three-guard pattern should be adopted for any agent restart mechanism
- The spawn manifest pattern enables crash recovery across Clavain sessions
- The AIMD throttle for rate-limited agents is worth adopting for multi-agent scenarios
- Webhook event emission pattern aligns with Interslack integration

---

## 12. Implementation Priority Matrix

### Tier 1 -- Implement First (Foundational Safety)

| Pattern | NTM Source | Demarch Target | Effort |
|---------|-----------|----------------|--------|
| **Invariant Framework** | `internal/invariants/` | Intercheck | Medium |
| **Redaction Engine** | `internal/redaction/` | `core/` shared lib | Medium |
| **Tamper-Evident Audit** | `internal/audit/` | Intercore | High |
| **Approval Engine** | `internal/approval/` | Intercore + Interlock | Medium |

### Tier 2 -- Implement Next (Operational Observability)

| Pattern | NTM Source | Demarch Target | Effort |
|---------|-----------|----------------|--------|
| **Context Estimation** | `internal/context/monitor.go` | Intercore + Intermux | High |
| **Predictive Exhaustion** | `internal/context/predictor.go` | Clavain | Medium |
| **Health Checking** | `internal/health/` | Intermux | Medium |
| **Cost Tracking** | `internal/cost/` | Intercore + Interstat | Medium |

### Tier 3 -- Implement Later (Advanced Capabilities)

| Pattern | NTM Source | Demarch Target | Effort |
|---------|-----------|----------------|--------|
| **Proactive Handoff** | `internal/context/handoff_trigger.go` | Clavain | High |
| **Resilience Monitor** | `internal/resilience/` | Intercore | High |
| **Privacy Manager** | `internal/privacy/` | Intercore | Low |
| **Profiler** | `internal/profiler/` | Intercore | Low |
| **Quota Tracking** | `internal/quota/` | Intermux | Medium |
| **Metrics + Prometheus** | `internal/metrics/` | Intercore | Medium |

---

## 13. Key Design Principles Observed

1. **Best-Effort Side Effects:** Notifications, event emissions, and persistence never block core operations. Errors are logged but not propagated.

2. **Thread Safety via RWMutex:** Every stateful component uses `sync.RWMutex` with consistent lock ordering. Read-heavy paths use RLock.

3. **Pluggable Fetchers/Adapters:** External dependencies (tmux, SLB, process checking) are behind interfaces with test doubles.

4. **Graceful Degradation Everywhere:** Missing tools, failed operations, and unavailable services produce warnings, never crashes.

5. **JSONL for Append-Only Data:** Audit logs, rotation history, and pending rotations all use JSONL for crash-safe append-only storage.

6. **Deterministic Hashing for Audit:** SHA-256 hash chains in audit logs; deterministic redaction placeholders for correlation.

7. **Background Goroutines with Clean Shutdown:** All background loops use context cancellation + WaitGroup for graceful shutdown.

8. **Test Hooks Pattern:** Production functions stored in package-level variables that tests can override (e.g., `sendKeysFn`, `sleepFn`).

---

## 14. Anti-Patterns to Avoid

1. **Hardcoded Pricing Tables:** NTM embeds model pricing in Go source. Demarch should externalize this to a YAML/JSON config that can be updated without recompilation.

2. **PTY-Based Quota Fetching:** Clever but fragile. Prefer API-based approaches where available.

3. **Global Singletons:** NTM uses several (`global` profiler, `defaultManager` for privacy, `DefaultRotationHistoryStore`). These complicate testing and multi-tenant scenarios. Prefer explicit dependency injection.

4. **Regex-Based CLI Output Parsing:** The quota parsers are regex-heavy and will break when CLI output formats change. Where possible, use structured output (`--json` flags) or APIs.

---

## 15. Immediate Action Items for Demarch

1. **Define Demarch's invariants** -- Start with NTM's 6, add plugin isolation, MCP audit completeness, and secret hygiene.

2. **Port the redaction engine** -- This is the highest-impact, lowest-effort adoption. Every component that logs, transmits, or persists text should run through redaction first.

3. **Implement hash-chain audit logging** -- The tamper-evident pattern is critical for multi-agent compliance. Start with Intercore session events.

4. **Design the context estimation interface** -- Even if initial implementations are simple (message count), the interface should support the full strategy pattern from day one.

5. **Add approval gates to Interlock force-release** -- The current force-release flow in agent-mail should require explicit approval with audit trail.
