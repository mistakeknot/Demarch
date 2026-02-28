# Assessment: mcp_agent_mail Repos for Demarch Integration

**Date:** 2026-02-28
**Assessor:** Claude Sonnet 4.6
**Repos assessed:**
- `research/mcp_agent_mail/` (iv-gqqvm, score 98) — Python implementation
- `research/mcp_agent_mail_rust/` (iv-xvo5h, score 96) — Rust rewrite

**Demarch context for comparison:**
- `core/intermute/` — Go coordination service (HTTP + WebSocket), SQLite-backed, agent heartbeats, message routing, file reservations
- `interverse/interlock/` — Claude Code MCP plugin (Go binary, mark3labs/mcp-go), 11 tools, negotiated file release, git pre-commit enforcement
- `apps/intercom/` — Personal AI assistant with container isolation
- MCP servers are the plugin integration layer throughout Interverse

---

## Preliminary: What These Repos Are

Both repos implement the same concept — "Gmail for coding agents" — as an MCP server providing:

1. **Agent identity registration** — memorable names like `GreenCastle`, paired with program/model/project/task metadata
2. **Async mailbox protocol** — threaded inbox/outbox, subjects, CC/BCC, acknowledgments, importance levels
3. **Advisory file reservations** — TTL-based glob leases with optional exclusive mode, backed by git artifacts
4. **Agent directory (LDAP-style)** — whois, agent roster, activity tracking
5. **Git-backed archive** — every message/reservation stored as markdown files with git commits
6. **SQLite index** — FTS5 search, fast queries, connection pooling

The Python repo is the original (OSS, ~1700 stars). The Rust repo is a full rewrite targeting performance, stability, and a 15-screen TUI.

---

## mcp_agent_mail (iv-gqqvm)

**What it is:** A Python FastMCP HTTP server providing asynchronous mailbox coordination (identity, messaging, advisory file reservations, git-backed archive) for multi-agent coding environments.

**Language/Stack:** Python 3.14, FastMCP 2.x, FastAPI, SQLAlchemy async + aiosqlite, GitPython, filelock, litellm (LLM summarization), Pillow (WebP attachments), Typer CLI, Uvicorn/Gunicorn

**Quality:** high

Code quality assessment:
- `app.py` is 11,766 lines — enormous monolith, but well-structured with clear sections
- `storage.py` is 3,236 lines with detailed concurrency docstring explaining lock hierarchy, commit queue design, retry semantics
- 130+ test files covering concurrency, guards, identity, contact policy, security (XSS, path traversal), HTTP auth/rate limiting, and e2e multi-agent workflows
- CI/CD: GitHub Actions with nightly runs, Prometheus observability configs
- Deployment: Docker, Gunicorn, systemd unit, logrotate config — production-ready
- Documentation: 27KB AGENTS.md, detailed MCP server design guide, ADRs, performance baselines
- Active development with beads task tracking and beads interactions log

Maturity signals:
- `PLAN_TO_NON_DISRUPTIVELY_INTEGRATE_WITH_THE_GIT_WORKTREE_APPROACH.md` — thorough analysis of worktree coordination
- `PLAN_TO_ENABLE_EASY_AND_SECURE_SHARING_OF_AGENT_MAILBOX.md` — WASM static export with Ed25519 signing
- `docs/GUIDE_TO_OPTIMAL_MCP_SERVER_DESIGN.md` — research-backed design guide citing MCP ecosystem literature
- `AGENT_FRIENDLINESS_REPORT.md` — self-audit of agent ergonomics

**Relevance to Demarch:** Directly overlaps with intermute (coordination backend) and interlock (MCP reservation tools), but adds threaded messaging, LLM summarization, git-backed audit trails, and a richer tool vocabulary that Demarch's stack currently lacks.

**Integration opportunities:**
- **Advisory file reservation glob semantics** — the pathspec/wildmatch matching logic (`pathspec` library, `GitWildMatchPattern`) is more correct than interlock's current fnmatch. The Rust version implements symmetric fnmatch with archive reading and rename handling. Worth porting to interlock's Go backend.
- **Commit queue / write-behind batching** — the `_CommitQueue` pattern in `storage.py` (lines ~63-120) batches concurrent git writes to reduce index.lock contention. Intermute does individual git ops; this pattern would harden it under load.
- **Pre-commit chain runner** — the hook installer creates a composable `hooks.d/<hook>/*` chain-runner that respects `core.hooksPath` and existing hook frameworks. Interlock's pre-commit hook currently overwrites. This chain-runner pattern would make interlock non-destructive on repos that already use Husky or lefthook.
- **Build slots** — `acquire_build_slot` / `release_build_slot` tools for coordinating long-running build/watch processes. Demarch has no equivalent; this would prevent two agents from running `go build` or `npm dev` simultaneously.
- **Product bus** — cross-repo coordination via `ensure_product` + `products_link`. Frontend and backend agents in separate repos sharing one message bus. Intermute is single-project scoped; this pattern would let intercom and autarch agents coordinate across repo boundaries.
- **Macro tools pattern** — `macro_start_session`, `macro_prepare_thread`, `macro_file_reservation_cycle`, `macro_contact_handshake`. These compress multi-step flows into single MCP calls. Interlock could expose similar macros to reduce token overhead at session start.
- **Token-efficient robot CLI output** — the `toon` format (token-efficient compact encoding) delivered as a JSON envelope inside MCP responses. Worth adding to interlock's tools so agents can request compact responses when context budget is tight.
- **LLM-powered thread summarization** — `summarize_thread` tool invokes litellm to generate conversation digests. Useful for long-running beads threads where context has been lost.

**Inspiration opportunities:**
- **"Advisory, not mandatory" reservation philosophy** — the explicit design choice to use TTL-based leases with a git hook for enforcement rather than hard locks avoids deadlock when agents die. Interlock currently has cooperative semantics but could articulate this more clearly in its protocol.
- **Semi-persistent identity design** — identities exist for a task lifetime, not forever. No ringleader agents whose death breaks the system. This is a better model than interlock's current per-session identity that vanishes immediately on disconnect.
- **Anti-broadcast design** — the explicit "no reply-all" design decision. Agents should message specific recipients, not broadcast. Intermute's message routing doesn't enforce this, but it could add warnings or metering for broadcast patterns.
- **`HumanOverseer` injection** — the web UI's ability to inject high-priority messages that bypass contact policy, alerting agents to pause and handle human instructions. Interlock/intercom have no human escalation path into agent coordination.
- **Contact policy system** — agents define policies (allow-all, allowlist, blocklist) controlling who can message them. Intermute routes everything to everyone; selective contact policies would reduce agent distraction.
- **Resource URIs for fast reads** — `resource://inbox/{Agent}`, `resource://thread/{id}` etc. let agents do fast lookups without full tool calls. Interlock exposes everything as tools; adding read-only resources would halve the token overhead for status checks.
- **Deployment validation bundle** — `am share export` + `am share deploy verify-live` lets operators validate a deployed instance against a known-good snapshot. Useful pattern for Interverse plugin health checks.

**Verdict:** inspire-only

**Rationale:** The Python codebase directly overlaps with intermute + interlock, but Demarch's coordination layer is already built in Go; adopting Python would fragment the stack, and the Rust rewrite (iv-xvo5h) supersedes the Python version for any deeper integration work.

---

## mcp_agent_mail_rust (iv-xvo5h)

**What it is:** A production-grade Rust rewrite of mcp_agent_mail exposing 34 MCP tools across 9 clusters, a 15-screen TUI operations console, robot CLI mode, and git-backed archive — designed for zero-deadlock concurrent operation under sustained multi-agent load.

**Language/Stack:** Rust (nightly), workspace of 12 crates; `asupersync` (structured async runtime, no Tokio), `fastmcp_rust` (MCP protocol), `sqlmodel_rust` (SQLite ORM), `frankentui` (TUI), `frankensearch` (hybrid lexical+semantic search), `beads_rust` (task tracking), `toon_rust` (compact encoding), `git2` (libgit2 bindings)

**Quality:** high

Code quality assessment:
- 12-crate workspace with strict dependency layering (core -> db/storage -> tools -> server/cli)
- `#![forbid(unsafe_code)]` across all crates
- `storage/src/lib.rs` is 11,139 lines — covers archive init, lock hierarchy with `OrderedMutex`/`OrderedRwLock` enforcing global lock rank ordering (10 defined ranks), commit coalescer with write-behind queue, WebP attachment pipeline
- Global lock hierarchy formally defined in `lock_order.rs` with runtime enforcement in debug builds — serious deadlock prevention engineering
- Conformance test harness (`mcp-agent-mail-conformance` crate) runs against Python reference implementation, comparing 23 tools and 23+ resources output-by-output
- E2E test suites: 50+ shell scripts covering stdio, HTTP, guard, macros, share, dual-mode, stress load, fault injection, doom loops, crash-restart recovery
- Performance benchmarks with flamegraph SVGs in `benches/`; stress test results: 30 agents × 5 messages = 150/150 success; 49 RPS sustained 30s with p99=2.6s; 0 errors across 10-test gauntlet
- `FEATURE_PARITY.md` tracks each feature with implementation evidence and verification status
- `VISION.md` captures 10-day design sessions in detail; `PROPOSED_ARCHITECTURE.md` defines lock ordering and dependency mapping
- `TODO.md` shows all tasks checked off — project is feature-complete

Architecture highlights:
- **Dual-mode binary** — same binary serves as MCP stdio/HTTP server or operator CLI, with hard mode separation (wrong-mode calls return exit code 2 with explanation on stderr)
- **Write-behind queue (WBQ)** — git commits coalesced asynchronously, 9.1x batching ratio observed; eliminates index.lock storms under concurrent agents
- **WAL mode + 60s busy_timeout** — SQLite pool handles 4x oversubscription (60 threads on pool=15) with 0 timeouts
- **Stale lock recovery** — detects crashed-process lock files via PID checking, cleans them automatically
- **Tool filtering profiles** — full/core/minimal/messaging/custom; smaller models or security-restricted deployments can mount fewer tools
- **WASM crate** — browser-side TUI frontend via `mcp-agent-mail-wasm`
- **Robot mode** — 16 structured subcommands with toon/json/md output formats; designed for agent consumption in automated loops

**Relevance to Demarch:** The Rust codebase architecture — particularly its lock ordering system, WBQ storage layer, and dual-mode binary pattern — directly mirrors the design problems Demarch faces as intermute scales to support larger agent fleets and the Interverse plugin layer grows more complex.

**Integration opportunities:**
- **`OrderedMutex` / `OrderedRwLock` lock hierarchy pattern** — the deadlock prevention system in `mcp-agent-mail-core/src/lock_order.rs` assigns integer ranks to all locks and enforces acquisition order at runtime in debug builds. Intermute's current Go code uses sync.Mutex without ordering guarantees. Port this pattern to intermute's Go lock management.
- **Commit coalescer / write-behind queue design** — the WBQ (write-behind queue) in `storage/src/lib.rs` is the key innovation: rapid-fire archive writes are batched into far fewer git commits. The Go implementation in intermute could adopt this pattern to handle high-frequency bead/reservation updates without git contention.
- **Reservation conflict detection with `CompiledPattern`** — `reservations.rs` uses `mcp_agent_mail_core::pattern_overlap::CompiledPattern` for symmetric fnmatch overlap detection (two patterns conflict if they can match the same path). Interlock's Go reservation code does exact string matching; this pattern overlap approach is far more correct for glob-based reservations.
- **`mcp-agent-mail-guard` crate** — the Rust pre-commit guard installs a composable chain-runner that respects `core.hooksPath`, existing frameworks (Husky, lefthook), and handles pre-push STDIN tuples correctly. The interlock guard currently overwrites hooks. Port this chain-runner design to interlock.
- **Tool filtering profile system** — the `full/core/minimal/messaging/custom` profile system lets the same server serve different agent capability tiers. Interverse plugins could adopt this for progressive disclosure: a minimal profile for small models, full profile for Opus-class agents.
- **`am doctor` diagnostic + repair commands** — the `check`/`repair` subcommand pattern (detect stale locks, orphaned records, FTS desync, expired reservations) with dry-run preview and backup-before-modify safety. Intermute has no health/repair tooling; this pattern would benefit the Clavain setup workflow.
- **Browser state sync endpoint** — `GET /mail/ws-state` with delta polling via sequence numbers (intentionally HTTP polling, not WebSocket upgrade). Autarch/intercom could adopt this for agent dashboard state sync without maintaining WebSocket connections.
- **Dual-mode binary separation** — the hard enforcement that MCP server calls rejected from CLI mode and vice versa (exit code 2, deterministic stderr message). Interlock mixes operator commands and agent tools in the same surface; this separation would make the tool contract cleaner.

**Inspiration opportunities:**
- **Structured async without Tokio** — the entire async stack uses `asupersync` with `Cx`-threaded structured concurrency, cancel-correct channels, and deterministic testing with virtual time. Demarch's Go services use goroutines + channels, which is analogous, but the virtual time / deterministic testing aspect of asupersync is worth studying for intermute's test harness.
- **Conformance-driven development** — the Python implementation is the reference; the Rust port runs conformance tests on every CI run comparing output against captured Python fixtures. This approach would work well for Demarch's Go reimplementation of intermute features: capture HTTP response fixtures from the current implementation, run conformance against any future rewrite.
- **15-screen TUI as first-class operational interface** — frankentui's approach (semantic color tokens, no hardcoded ANSI, rounded borders, command palette, toast notifications, accessibility high-contrast mode) is the design language Autarch's agent monitoring UI should aspire to. The screen inventory (dashboard, messages, threads, agents, search, reservations, metrics, health, timeline, projects, contacts, explorer, analytics, attachments, archive browser) maps almost perfectly to what Autarch would need for fleet oversight.
- **`toon` output format as a first-class concern** — treating token-efficient compact encoding as an equal output format alongside json and md, with per-tool format parameters and environment variable defaults. Interlock currently returns verbose JSON everywhere; adding a toon/compact option would materially reduce agent context consumption.
- **Stale agent force-release with inactivity heuristics** — `force_release_file_reservation` uses inactivity detection (last heartbeat, last commit) to determine if a reservation holder is dead before releasing. Interlock's current logic relies solely on TTL; adding inactivity heuristics would make reservation cleanup more responsive.
- **Build slot concept** — dedicated TTL leases for long-running processes (watchers, dev servers, build daemons), separate from file reservations. Intermute treats all reservations the same; splitting file reservations from build process slots with different TTL semantics would reduce collision between static-analysis agents and build agents.
- **`HumanOverseer` bypass contact policy** — the web UI compose form creates messages from a special `HumanOverseer` identity that always reaches agents regardless of contact policy. This is the right model for Autarch's human escalation path: a privileged sender identity that bypasses normal routing rules.

**Verdict:** inspire-only

**Rationale:** The Rust codebase is production-quality and architecturally sophisticated, but Demarch's coordination layer (intermute) is already in Go and interlock is Go/bash — adopting a new Rust async runtime with custom crates (`asupersync`, `frankentui`, `fastmcp_rust`) would create a foreign dependency island; the right approach is to port specific patterns (lock ordering, WBQ, chain-runner hooks, reservation overlap detection) back into Go.

---

## Comparative Summary

| Dimension | mcp_agent_mail (Python) | mcp_agent_mail_rust (Rust) | Demarch (current) |
|-----------|------------------------|----------------------------|--------------------|
| Transport | HTTP (FastMCP, Streamable) | stdio + HTTP | HTTP + WebSocket (intermute) |
| Storage | SQLite + git archive | SQLite + git archive | SQLite only (no git archive) |
| File reservations | Advisory glob leases + git hook | Advisory glob leases + git hook | Advisory exact-match leases + git hook (interlock) |
| Agent messaging | Threaded mailbox, CC/BCC, ack | Same + 15-screen TUI | Basic routing, cursor-based inbox (intermute) |
| Cross-repo coordination | Product bus | Product bus | Not implemented |
| Audit trail | Git commit per message/reservation | Same + commit coalescer | No git-backed audit trail |
| Tooling | 34 tools / 20+ resources | 34 tools / 20+ resources | 11 tools (interlock) |
| Contact policy | Allowlist/blocklist | Same | None |
| Human escalation | HumanOverseer web form | Same | None |
| Token efficiency | toon format | toon + robot CLI | Standard JSON |
| Build slots | Yes | Yes | No |
| Test coverage | 130+ test files, 10-test stress gauntlet | 50+ e2e scripts, conformance harness | Go test suite (intermute) |

## Prioritized Adoption Recommendations

In priority order, these are the specific patterns most worth porting to Demarch:

1. **Lock ordering system with runtime enforcement** (from Rust) — prevents deadlock as intermute scales; 2-3 days Go implementation effort
2. **Write-behind commit queue / batching** (from either) — eliminates git index.lock storms under concurrent agents; the Python `_CommitQueue` is the more portable reference
3. **Composable chain-runner git hook installer** (from either) — makes interlock non-destructive on repos with existing hook frameworks; critical for wider adoption
4. **Glob pattern overlap detection** (from Rust `CompiledPattern`) — correct reservation conflict detection; current interlock exact-match approach misses overlapping patterns like `src/**` vs `src/auth/**`
5. **Advisory reservation TTL + inactivity heuristics for stale release** — current interlock relies solely on TTL; adding heartbeat-based inactivity detection would handle agent crashes more responsively
6. **Build slot concept** — separate TTL class for build/watch processes vs. file edit reservations; prevents build agents blocking edit agents
7. **Read-only resource URIs** — `resource://inbox/{Agent}`, `resource://reservations` etc. for fast reads without full tool calls; halves token overhead for status checks
8. **Macro tools** — `macro_start_session`, `macro_file_reservation_cycle` compressing multi-step flows into single calls; directly reduces coordination overhead in agent startup sequences

## Notes on What Not to Adopt

- **The Python server itself** — Demarch is Go/Rust; adding a Python FastMCP server dependency would fragment the stack. The patterns are valuable; the runtime is not.
- **The Rust async runtime** (`asupersync`) — this is a custom runtime replacing Tokio, with custom channel types and virtual time. It's impressive engineering for this project's internal needs, but adopting it in Demarch would require building expertise in a non-standard runtime with limited community support.
- **frankentui** — while the TUI design philosophy is inspiring, frankentui appears to be a custom framework tightly coupled to this project's Rust ecosystem. Autarch's TUI work should reference the design language (screen inventory, semantic color tokens, command palette patterns) rather than the library itself.
- **The full 34-tool surface** — Demarch's interlock works well with 11 tools. Adding 23 more tools would expand the context surface and potentially confuse agents about which tools to use. Selective addition is better than wholesale adoption.
