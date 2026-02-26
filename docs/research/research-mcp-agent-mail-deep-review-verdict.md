# mcp_agent_mail Deep Review — 10-Agent Synthesis Verdict

**Date:** 2026-02-24
**Target:** `/home/mk/projects/Demarch/research/mcp_agent_mail/`
**Goal:** Identify patterns Demarch should adopt, bugs to avoid, and architecture lessons for the Go coordination stack

---

## Review Agents

### Custom Prompt-Mode Agents (domain-specific)
| Agent | Focus | Key Contribution |
|-------|-------|------------------|
| fd-persistence-durability | SQLite+Git dual-write, WAL, circuit breaker | Dual-write crash window, WAL tuning, circuit breaker adoption |
| fd-messaging-protocol | Topic routing, pagination, delivery guarantees | Topic categorization (adopt), cursor superiority (keep), stale-ack TTL |
| fd-coordination-identity | Contact policies, registration tokens, window identity | 4-level access control (adopt), sender impersonation (avoid) |
| fd-tool-surface | Structured errors, tool filtering, instrumentation | Error contract (adopt), tool profiles (adopt), middleware pattern |
| fd-workflow-macros | Macro composition, atomicity, phase gates | Non-atomic macros (avoid for gates), flat composition (study) |

### Core Flux-Drive Agents
| Agent | Focus | Key Contribution |
|-------|-------|------------------|
| fd-architecture | Module boundaries, coupling, design patterns | 11k-line monolith analysis, 6 adopt / 6 avoid patterns |
| fd-correctness | Data consistency, race conditions, transaction safety | 11 findings: dual-write crash (P1), batch failure poisoning (P1), TOCTOU (P1) |
| fd-safety | Security threats, trust boundaries, credential handling | 10 findings: sender impersonation (High), contact policy bypass (High) |
| fd-quality | Naming, conventions, error handling, idioms | 10 findings: 11k monolith (Critical), 122 bare except blocks (High) |
| fd-performance | Query patterns, connection pool, scaling bottlenecks | 15 findings: pool size (must-fix), `func.lower()` (must-fix), full scans |

---

## STATUS: ADOPT SELECTIVELY

All 10 agents converge: mcp_agent_mail has **excellent infrastructure patterns** (circuit breaker, structured errors, tool instrumentation, commit queue, contact policies) inside a **structurally flawed container** (11k-line monolith, 122 bare except blocks, sender impersonation, 50-connection SQLite pool). The value is in extracting specific patterns, not using it as a reference architecture.

**Demarch's stack is already stronger** in pagination (cursors vs timestamps), phase atomicity (single transaction vs per-step commits), push notifications (WebSocket vs signal files), and concurrency control (optimistic WHERE vs IntegrityError catch).

---

## Top 15 Adoption Recommendations (Ranked by Cross-Agent Convergence)

### Tier 1: Adopt Now (high impact, low effort)

**1. Structured Error Contract** — `{type, message, recoverable, data}`
- **Converging agents:** fd-tool-surface (P0-1), fd-architecture (2.3), fd-quality (adopt list), fd-workflow-macros (P3-1)
- **Gap:** Interlock/Intermute return flat error strings. Agents cannot distinguish transient from permanent failures.
- **Action:** Define `ToolError` Go struct in interbase with error type catalog. Port all MCP servers.
- **Reference:** `app.py:306-321` — `ToolExecutionError(error_type, message, recoverable=True, data={})`

**2. `@instrument_tool` Middleware Pattern**
- **Converging agents:** fd-architecture (2.1), fd-quality (adopt #1), fd-tool-surface (P0-2), fd-performance (Pattern A)
- **Gap:** Each Demarch MCP server implements ad-hoc error handling, no centralized metrics/timing/capability gating.
- **Action:** Create shared mcp-go middleware wrapping tool handlers with timing, error counting, structured error wrapping, capability checks, and retry logic.
- **Reference:** `app.py:378-669` — centralized retry, metrics, capability enforcement, logging, EMFILE handling

**3. Topic-Based Message Categorization**
- **Converging agents:** fd-messaging-protocol (P1-1), fd-architecture (adopt list)
- **Gap:** Intermute has recipient-based routing only. Late-joining agents cannot discover conversations.
- **Action:** Add `topic TEXT` column to Intermute messages table, index on `(project, topic)`, add `TopicMessages()` to Store interface.

**4. Contact Policies (4-Level Per-Agent Access Control)**
- **Converging agents:** fd-coordination-identity (P0-2), fd-messaging-protocol (P2-5), fd-safety (F2 — bypass to avoid)
- **Gap:** No access control on Demarch messaging. Any registered agent can send to any other.
- **Action:** Add `contact_policy` to Intermute Agent model (`open|auto|contacts_only|block_all`). Enforce at delivery time on ALL paths (send AND reply — mcp_agent_mail's reply_message bypasses this, per fd-safety F2).
- **Critical lesson:** mcp_agent_mail's `reply_message` does NOT enforce contact policy for local recipients. If Demarch adopts this, enforce uniformly.

**5. Circuit Breaker on DB Layer**
- **Converging agents:** fd-persistence-durability (P0-4), fd-architecture (2.4), fd-correctness (CC-05 — fix scope), fd-performance (Pattern A), fd-workflow-macros (P2-3)
- **Gap:** Demarch SQLite uses `MaxOpenConns(1)` + WAL + 5s busy timeout but no circuit breaker for sustained contention.
- **Action:** Port the circuit breaker pattern (5-failure threshold, 30s open, half-open probe, jitter backoff) as a shared Go package.
- **Critical lesson from fd-correctness CC-05:** Only count retried-and-exhausted *transient* errors. mcp_agent_mail counts ALL OperationalErrors, masking real bugs as "circuit breaker open".

### Tier 2: Near-Term (medium effort, high value)

**6. Tool Filtering Profiles for Context Reduction**
- **Converging agents:** fd-tool-surface (P0-3), fd-architecture (2.2), fd-quality (adopt list)
- **Gap:** Combined tool surface across Demarch MCP servers exceeds 80 tools. No filtering.
- **Action:** Named clusters + profile-based tool exposure (`full`/`core`/`minimal`). The 70% context reduction is critical for agent performance.

**7. Stale-Ack TTL Views**
- **Source:** fd-messaging-protocol (P0-2)
- **Gap:** Intermute has `ack_required` and `ack_at` columns but no overdue-ack query.
- **Action:** Add `InboxStaleAcks(ctx, project, agentID, ttlSeconds, limit)` to Intermute Store interface. Trivial given existing schema.

**8. Document Idempotency Contracts on All MCP Tools**
- **Source:** fd-tool-surface (P2-2)
- **Gap:** No Demarch MCP server documents idempotency. Agents retry aggressively without knowing if it's safe.
- **Action:** Add `Idempotent: yes/no` to every tool description across all Demarch MCP servers.

**9. Window Identity for Session Persistence**
- **Source:** fd-coordination-identity (P2-1)
- **Gap:** Interlock loses agent identity on session restart.
- **Action:** Window-identity table mapping tmux UUIDs to persistent agent names. TTL-based lifecycle prevents orphans.

**10. Commit Queue with Path-Conflict Batching**
- **Converging agents:** fd-architecture (2.5), fd-performance (Pattern B), fd-correctness (CC-02 — fix isolation)
- **If applicable:** Only adopt if Interlock adds git-backed audit trails. Batch non-conflapping writes.
- **Critical lesson from fd-correctness CC-02:** mcp_agent_mail's batch failure propagates to ALL batched callers. A Go implementation MUST fall back to sequential on batch failure to preserve isolation.
- **Critical lesson from fd-performance Finding 7:** The 50ms batch wait adds latency for zero benefit in single-agent scenarios. Use 5ms or triggered-flush model.

### Tier 3: Future Consideration

**11. FTS5 Full-Text Search**
- **Source:** fd-messaging-protocol (P2-3), fd-safety (F4 — safe parameterized pattern)
- **Action:** Add `fts_messages` virtual table with trigger-based sync. Use parameterized FTS5 MATCH (safe per fd-safety F4), avoid f-string SQL construction in the LIKE fallback.

**12. "Return Full Context" Pattern for CLI Operations**
- **Source:** fd-workflow-macros (P2-2)
- **Action:** Return new phase + next gate requirements + active agent count in a single response from `Advance()`.

**13. AsyncFileLock with Owner Metadata Sidecar**
- **Converging agents:** fd-architecture (2.6), fd-correctness (adopt list), fd-performance (Pattern E)
- **If applicable:** `.lock` + `.lock.owner.json` with dual-condition staleness (PID liveness + age). Correct for cross-process coordination without a central service.

**14. LRU Repo Cache with Time-Based Eviction**
- **Converging agents:** fd-architecture (2.7, 3.2), fd-correctness (adopt list — but fix CC-07), fd-performance (Pattern D)
- **If applicable:** Use time-since-last-use eviction, NOT `sys.getrefcount()`. Reference counts in CPython are unreliable.
- **Critical lesson from fd-correctness CC-07:** The lock-free fast path (`peek()` outside any lock) can return an evicted/closed Repo. Use reference counting or eliminate the lock-free path.

**15. `hmac.compare_digest` for Constant-Time Token Comparison**
- **Source:** fd-safety (adopt #1)
- **Action:** Adopt everywhere Demarch compares secrets. Already correct in mcp_agent_mail's BearerAuthMiddleware.

---

## What Demarch Already Does Better

Confirmed by both custom and core agent sets:

| Dimension | Demarch | mcp_agent_mail | Confirming Agents |
|-----------|---------|----------------|-------------------|
| Pagination | Cursor-based (monotonic uint64) | Timestamp-based (`since_ts`) — gap/duplicate risk | fd-messaging-protocol, fd-correctness |
| Phase transitions | Single atomic SQLite transaction | Per-step individual commits — no rollback | fd-workflow-macros, fd-correctness |
| Push notifications | WebSocket broadcast | Best-effort signal files | fd-messaging-protocol |
| Tool schema weight | Client-embedded identity (2-5 params) | Per-call identity (7-17 params) | fd-tool-surface |
| Concurrency control | `WHERE phase = ?` optimistic concurrency | IntegrityError catch (insert-only) | fd-workflow-macros, fd-correctness |
| Code structure | Separate handler/logic/data layers | 11k-line monolith, all tools as nested closures | fd-architecture, fd-quality |
| SQLite pool size | `MaxOpenConns(1)` | 50-connection pool (wrong for single-writer DB) | fd-correctness CC-06, fd-performance #1 |
| Error transparency | Errors propagated | 122 bare `except Exception:` blocks | fd-quality #3 |

---

## What NOT to Adopt

| Pattern | Reason | Source Agents |
|---------|--------|---------------|
| Timestamp-based pagination | Cursors strictly superior | fd-messaging-protocol |
| Signal-file notifications | WebSocket push strictly superior | fd-messaging-protocol |
| Non-atomic macros for phase gates | Breaks TOCTOU guarantees | fd-workflow-macros, fd-correctness |
| Git dual-write on hot path | Too expensive for real-time; crash window (CC-01) | fd-persistence-durability, fd-correctness |
| 3x file amplification | Canonical + outbox + inbox wasteful | fd-persistence-durability |
| 50-connection SQLite pool | Creates thundering herd, wastes memory/FDs | fd-correctness CC-06, fd-performance #1 |
| Nested tool closures in factory | Prevents extraction, creates 11k monolith | fd-architecture, fd-quality |
| Optional sender_token | Complete sender impersonation possible | fd-safety F1, fd-coordination-identity |
| `func.lower()` on indexed columns | Disables index, full scan on every lookup | fd-performance #2, #4 |
| Bare `except Exception: pass` | Silently swallows business logic failures | fd-quality #3 |
| `format` param on every tool | API surface pollution; belongs in transport | fd-quality #2 |
| Feature-flag parallel architectures | Disabled stubs inline with real tools | fd-architecture 2.9 |
| Fuzzy matching on every lookup failure | Full table scan + SequenceMatcher on error path | fd-architecture 2.10, fd-performance #3 |
| Per-call `project_key` + `agent_name` | Client-embedded identity is leaner | fd-tool-surface |
| `contextlib.suppress(Exception)` around crypto | Silent JWT verification skip possible | fd-safety F10 |
| f-string SQL with `text()` | Maintenance-landmined injection risk | fd-safety F4 |

---

## Critical Bugs Found (Do Not Replicate)

### P1 Correctness Bugs (fd-correctness)

**CC-01: Dual-Write Crash Window.** SQLite commits before Git write. Process crash after DB commit leaves message in SQLite but not in Git archive. No write-ahead tombstone, no startup recovery scan, no `archive_failed` marker. If Demarch ever does dual-write, implement saga with compensating action.

**CC-02: Batch Commit Failure Poisons All Callers.** One bad file in a batched commit causes ALL batched agents to receive the error. Three innocent agents get "permission denied" for a file they never touched. Fix: fall back to sequential on batch failure.

**CC-03: `needs_init` TOCTOU.** Variable only assigned on new-repo path; early return on existing-repo path means `if needs_init:` raises `UnboundLocalError`. Currently masked by control flow but fragile.

### High Security Findings (fd-safety)

**F1: Sender Impersonation.** `sender_token` is optional. Any agent knowing another's name can send messages as them. The `verified_sender` flag is computed but never used downstream. Forged messages become part of the permanent Git audit trail.

**F2: Contact Policy Bypass in reply_message.** Local recipients in `reply_message` skip contact policy checks entirely. An agent with `block_all` still receives replies routed through `reply_message`. The same bypass does NOT exist in `send_message`, which correctly enforces policies.

**F3: Guard Bypass via Env Var.** `AGENT_MAIL_BYPASS=1` skips pre-commit guard. Guard is also off by default (`WORKTREES_ENABLED` and `GIT_IDENTITY_ENABLED` both default to false).

### Quality Critical (fd-quality)

**11,382-line monolith.** All 47 tools defined as nested closures inside `build_mcp_server()`. `send_message` alone is ~997 lines. The closure pattern prevents extraction to separate files. If Demarch ever builds a similar server, establish module boundaries early.

**122 bare `except Exception:` blocks.** ~80 are in business logic paths with no logging, not just infrastructure fallbacks. Auto-handshake failures in `send_message` can go completely unrecorded.

### Performance Must-Fix (fd-performance)

**50-connection pool for SQLite.** SQLite is single-writer. Pool of 50 creates 50 threads all serializing at the write lock. Correct: 5-10 connections for readers, `MaxOpenConns(1)` for writes.

**`func.lower()` on indexed columns.** Used on `Message.topic`, `Agent.name`, and others. Disables all relevant indexes, causing full scans on every `fetch_inbox` and `_get_agent` call. Fix: normalize at write time.

**Closed session re-use in send_message.** Thread-participant lookup queries a session after the `async with get_session()` block exits. The `DetachedInstanceError` is silently swallowed, breaking reply auto-allow logic. Every thread reply takes the full contact enforcement path unnecessarily.

---

## Cross-Agent Convergence Map

Findings independently identified by 3+ agents:

| Finding | Agents | Consensus |
|---------|--------|-----------|
| Structured error contract is #1 adoption priority | tool-surface, architecture, quality, macros | Unanimous |
| `@instrument_tool` middleware pattern | architecture, quality, tool-surface, performance | Unanimous |
| Circuit breaker (adopt the pattern, fix the scope) | persistence, architecture, correctness, performance, macros | Unanimous with qualification |
| 11k monolith is the primary structural problem | architecture, quality, performance | Unanimous |
| 50-connection pool is wrong for SQLite | correctness, performance | Unanimous |
| Sender impersonation is the #1 security risk | safety, identity | Unanimous |
| Contact policies worth adopting (but fix reply bypass) | identity, messaging, safety | Adopt with fix |
| `func.lower()` disabling indexes | performance (2 findings), correctness | Unanimous |
| Advisory model validates Intercore soft gates | macros, persistence | Convergent validation |
| Commit queue concept correct, implementation needs tuning | architecture, performance, correctness | Adopt concept, fix details |

---

## Architecture Comparison Matrix (Updated)

| Dimension | mcp_agent_mail | Demarch Stack |
|-----------|---------------|---------------|
| Language | Python (FastMCP) | Go (mcp-go, net/http) |
| Transport | HTTP (poll) + signal files | HTTP + WebSocket (push) |
| Pagination | Timestamp-based | Cursor-based (monotonic) |
| Persistence | SQLite + Git dual-write (crash window) | SQLite only |
| Code structure | 11k-line monolith, nested closures | Separate handler/logic/data layers |
| Message routing | Named recipients + topic tags | Named recipients only |
| Delivery guarantee | At-least-once (no dedup) | At-least-once (cursor dedup) |
| Ack tracking | Per-recipient with stale TTL views | Per-recipient, no stale queries |
| Search | FTS5 + BM25 | None |
| Access control | 4-level contact policy (bypassed in reply) | None |
| Error contract | Structured `{type, recoverable, data}` | Flat strings |
| Instrumentation | Centralized `@instrument_tool` | Ad-hoc per tool |
| Tool filtering | 4 profiles (70% context reduction) | None |
| Macros | 4 composite tools (non-atomic) | None |
| Phase state | N/A | Single atomic transaction |
| File coordination | Advisory reservations with TTL | Lock-based reservations with TTL |
| Broadcast | Built-in with policy filtering | Not implemented |
| Connection pool | 50 (wrong for SQLite) | MaxOpenConns(1) (correct) |
| Error handling | 122 bare except blocks | Explicit error propagation |
| Index discipline | `func.lower()` disables indexes | Expression indexes or write-time normalization |
| Identity verification | Optional sender_token (impersonation risk) | N/A (not yet implemented) |

---

## Source Agent Reports

### Custom Agents (flux-gen prompt mode)
| Agent | Key Findings |
|-------|-------------|
| fd-persistence-durability | Dual-write ordering risk, WAL tuning patterns, circuit breaker |
| fd-messaging-protocol | Topic routing (adopt), cursor superiority (keep), stale-ack TTL |
| fd-coordination-identity | Contact policies (adopt), registration token gaps, window identity |
| fd-tool-surface | Structured errors (adopt), tool filtering profiles, instrumentation wrapper |
| fd-workflow-macros | Non-atomic macros (avoid for gates), flat composition, return-full-context |

### Core Agents
| Agent | Output File | Key Findings |
|-------|------------|-------------|
| fd-architecture | `interflux/docs/research/fd-architecture-review-mcp-agent-mail.md` | 11k monolith, nested closures, duplicate `_norm_remote`, 6 adopt / 6 avoid |
| fd-correctness | `interflux/docs/research/fd-correctness-review-mcp-agent-mail.md` | CC-01 dual-write crash (P1), CC-02 batch failure (P1), CC-03 TOCTOU (P1), 8 more |
| fd-safety | `interflux/docs/research/fd-safety-review-mcp-agent-mail.md` | F1 sender impersonation (High), F2 contact bypass (High), F3 guard bypass, 7 more |
| fd-quality | `interflux/docs/research/fd-quality-review-mcp-agent-mail.md` | 11k monolith (Critical), 122 bare excepts (High), `format` pollution, duplicates |
| fd-performance | `interflux/docs/research/fd-performance-review-mcp-agent-mail.md` | Pool size (must-fix), `func.lower()` (must-fix), full scans, closed session bug |
