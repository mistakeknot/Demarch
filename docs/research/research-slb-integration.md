# Assessment: slb (Simultaneous Launch Button)

**Date:** 2026-02-28
**Bead ID:** iv-58pym
**Source:** https://github.com/Dicklesworthstone/slb
**Task:** Evaluate integration/inspiration value for Demarch (os/clavain, interverse/interlock, core/intermute)

---

## What it is

A Go CLI implementing a **two-person rule** for destructive commands in multi-agent AI workflows. Before any dangerous command executes, it must be peer-reviewed and approved by another agent session. Commands are risk-classified into four tiers (CRITICAL/DANGEROUS/CAUTION/SAFE) via a shell-aware pattern engine, and approvals are cryptographically bound to the exact command via SHA-256 hash with HMAC-signed reviews. The daemon acts as a notary — commands always execute client-side in the requester's shell environment.

**Language/Stack:** Go 1.24, Cobra (CLI), Bubble Tea + Lipgloss (TUI), pure-Go SQLite (`modernc.org/sqlite`), `fsnotify` (file watching). No CGo required.

**Quality:** high

- 1,506 test functions across 89 test files
- Dedicated `internal/testutil/` with fixtures, mock executor, integration helpers
- E2e tests for multi-agent approval, risk tier matrix, path traversal security, git rollback
- Race condition tests in `internal/db/race_test.go`
- HMAC-signed reviews with tamper-detection
- Table-driven state machine (not switch chains)
- Five security gates before any execution
- E2e tests honestly document known gaps (case-insensitive bypasses, whitespace variants) as pending rather than passing — rare level of security honesty

---

## Architecture

| Package | Role |
|---|---|
| `cmd/slb/` | Binary entrypoint |
| `internal/cli/` | Cobra command handlers (~40 files, one per command) |
| `internal/core/` | Business logic: patterns, normalize, request, review, execute, statemachine, session, rollback, ratelimit |
| `internal/db/` | SQLite data layer: schema, types, enums, requests, reviews, sessions, patterns, outcomes |
| `internal/daemon/` | Background notary: IPC (Unix socket), TCP, hook_query, notifications, watcher |
| `internal/config/` | TOML config with hierarchical override (defaults < user < project < env < flags) |
| `internal/output/` | Multi-format: text, JSON, YAML, TOON (token-optimized) |
| `internal/integrations/` | Claude Code hooks.json generator, Cursor rules, Agent Mail |
| `internal/tui/` | Bubble Tea dashboard: agents, pending requests, activity feed |
| `internal/git/` | Git helpers for rollback capture |

SQLite schema (3 tables): `sessions` (agent identity + heartbeat), `requests` (full lifecycle with command hash, risk tier, status, rollback path), `reviews` (per-vote with HMAC signature). WAL mode, `busy_timeout=5s`, `synchronous=NORMAL`.

---

## Core Patterns

### 1. Four-Tier Command Classification

`PatternEngine` holds ordered regex buckets (safe, critical, dangerous, caution) behind `sync.RWMutex`. Classification flow:

1. **Normalize** — strip wrappers (`sudo`, `env`, `time`, `nohup`, etc.), extract inner commands from `bash -c '...'`, resolve relative paths
2. **Shell-aware compound splitting** — rune-by-rune scan tracking quote state; `&&`/`||`/`;` only split outside quotes (so `psql -c "DELETE FROM x; DROP TABLE y"` stays as one segment)
3. **Pattern precedence**: SAFE > CRITICAL > DANGEROUS > CAUTION, first match wins per segment. **Highest-risk segment wins** for compounds
4. **Parse-failure upgrade**: if shell tokenization fails, tier upgrades one step (fail-closed)

### 2. Five-Gate Execution Model

Before any command runs, five gates must pass in sequence:

| Gate | Check |
|---|---|
| 1. Status | Request must be `StatusApproved` |
| 2. Approval TTL | `approval_expires_at` not elapsed (30min standard, 10min CRITICAL) |
| 3. Command hash | `sha256(raw + cwd + argv_json + shell_bool)` must match stored hash |
| 4. Tier consistency | Current classification must not be stricter than approved tier |
| 5. First-executor-wins | Atomic CAS SQL: `UPDATE ... SET status='executing' WHERE status='approved'` |

`CanExecute()` mirrors all 5 gates as a dry-check without side effects.

### 3. HMAC-Signed Reviews

Each review vote is signed: `HMAC-SHA256(sessionKey, requestID + decision + timestamp)`. Stored alongside the vote. `VerifyReview` recomputes and uses `hmac.Equal`. Three conflict resolution modes: any-rejection-blocks (default), first-wins, human-breaks-tie. Dynamic quorum scales MinApprovals down when reviewer pool is small.

### 4. Table-Driven State Machine

```
Pending   → [Approved, Rejected, Cancelled, Timeout]
Approved  → [Executing, Cancelled]
Executing → [Executed, ExecutionFailed, TimedOut, Approved]  ← re-approve possible
Timeout   → [Escalated]
Escalated → [Approved, Rejected]
```

The `Executing → Approved` back-edge allows retry after timeout without permanent stuck state. Terminal states: Executed, ExecutionFailed, TimedOut, Cancelled, Rejected.

### 5. Rollback System

Three capture backends with actual restore implementations:
- **rm → Filesystem**: tar.gz archive with size limits
- **git → Git**: HEAD, branch, diff patches (cached + working-tree separately), untracked files
- **kubectl → Kubernetes**: `kubectl get -o yaml` manifests

### 6. Daemon Architecture

Optional notary process on Unix socket (`/tmp/slb-<project-hash>.sock`). JSON-RPC 2.0: `hook_query` classifies commands and checks for pre-existing approvals. Forks self with `SLB_DAEMON_MODE=1`. TCP mode available for Docker/remote with session-key auth.

### 7. Claude Code Hook Integration

`slb hook install` writes `.claude/hooks.json` with a `pre_bash` hook. On block: guides agent to use `slb request`. Daemon-optional — works via file-poll without daemon.

---

## Relationship to destructive_command_guard (dcg)

slb and dcg (assessed in `assess-agent-farm-safety-repos.md`) solve overlapping but architecturally distinct problems:

| Dimension | dcg | slb |
|---|---|---|
| **Core model** | Single-agent guard (block/allow) | Multi-agent approval (request/review/execute) |
| **Decision** | Pattern match → immediate block/allow | Pattern match → require peer approval → execute |
| **Language** | Rust (SIMD-accelerated) | Go (pure-Go SQLite) |
| **Latency** | <1ms (pre-execution hot path) | Seconds (async approval workflow) |
| **State** | Stateless (config-only) | Stateful (SQLite request/review/session lifecycle) |
| **Safety model** | Prevent execution | Delay execution until peer-verified |
| **Install** | curl binary + hook entry | Go install + daemon |

**Key insight:** These are complementary layers, not alternatives. dcg is the fast pre-execution filter (blocks obviously dangerous commands instantly). slb is the deliberation layer (requires peer review for commands that are dangerous but legitimate in context). In a Clavain deployment:

1. dcg blocks at the hook level (microseconds, stateless)
2. slb handles the "this is dangerous but I need to do it" workflow (seconds, stateful, peer-verified)

---

## Integration Opportunities

### A. Adopt: Five-gate execution model for Clavain dispatch

The gate pattern (status + TTL + hash + tier-consistency + CAS) is directly applicable to Clavain's `dispatch.sh` and interlock's coordination layer. When Clavain dispatches a destructive plan task to a subagent, the five-gate pattern prevents:
- Double-execution (CAS)
- Stale approvals (TTL)
- Command tampering (hash binding)
- Risk escalation (tier consistency)

**Effort:** medium — port the gate interface, not the full approval workflow

### B. Adopt: HMAC-signed audit trail pattern

Clavain's sprint lifecycle produces decisions (gate approvals, quality-gate overrides, emergency skips) that currently have no tamper-evident record. The HMAC pattern — sign each decision with a session key so it can be verified later — is lightweight to add to `clavain-cli` sprint operations.

**Effort:** low — HMAC is stdlib Go, add to existing `record-phase` / `enforce-gate`

### C. Inspire: Table-driven state machine for sprint lifecycle

Clavain's sprint state machine is currently encoded in `/sprint`'s markdown instructions with implicit transitions. slb's explicit `validTransitions` map pattern would make sprint state transitions auditable, testable, and impossible to violate. The `Executing → Approved` back-edge (retry after timeout) maps to Clavain's "gate failed, fix, re-gate" pattern.

**Effort:** medium — requires refactoring sprint state from markdown-implicit to code-explicit

### D. Inspire: Dynamic quorum for quality-gates

slb's `checkDynamicQuorum` scales MinApprovals down when the reviewer pool is small (with a configurable floor). Clavain's quality-gates dispatch 7 review agents — if some fail or timeout, dynamic quorum would allow the gate to pass with fewer verdicts rather than blocking indefinitely.

**Effort:** low — add quorum logic to `verdict_count_by_status` in lib-verdict.sh

### E. Inspire: Parse-failure tier upgrade

When slb can't parse a command (unbalanced quotes, complex escapes), it upgrades the risk tier one step rather than allowing it. Clavain hooks that parse shell commands should adopt this fail-closed principle — unknown syntax gets stricter treatment, not looser.

**Effort:** trivial — a one-line addition to any pattern-matching hook

### F. Inspire: Emergency execute with SHA-256 acknowledgment

slb's emergency-execute requires the operator to compute `sha256(command)` and pass it as `--ack`. This forcing function ensures the operator has explicitly read and acknowledged the exact command. Applicable to Clavain's `CLAVAIN_SKIP_GATE='reason'` override — currently just a string reason, could require a hash acknowledgment.

**Effort:** low — add hash check to `enforce-gate` override path

---

## Skip Opportunities

- **Full slb daemon deployment.** The daemon is heavyweight for Demarch's current use case (single-user, single-machine). The patterns are valuable; the full client-server architecture is overkill until Demarch runs multi-user agent fleets.

- **Rollback capture system.** Well-implemented but Clavain already has git-based rollback via worktrees. The tar.gz filesystem capture and kubectl manifest capture are interesting but not needed.

- **Bubble Tea TUI dashboard.** Autarch already has Bigend for agent monitoring. Another TUI adds no value.

- **Agent Mail integration.** Demarch has interject for cross-agent messaging. Different protocol, same purpose.

---

## Known Gaps / Concerns

- **Pattern engine is regex-based with documented bypasses.** Case-insensitive variants (`RM -RF`), whitespace variants, quoted-arg forms are known gaps documented in e2e tests. These are inherent to regex-based classification and not easily fixable.

- **`risk.go` stub.** The `ClassifyRisk` function always returns `RiskTierDangerous` — the real classification goes through `PatternEngine.ClassifyCommand()`. This is a dead-code artifact, not a bug, but suggests some internal API cleanup was deferred.

- **`slb patterns list --json` panics** due to `-t` shorthand collision between global `--toon` and command-local `--tier`. Trivial fix (change shorthand) but shipped as-is.

- **SQLite per-project means no cross-project coordination** without explicit config. Fine for Demarch's monorepo but would be a friction point in a multi-repo setup.

---

## Verdict: inspire-only

**Rationale:** slb is a well-engineered system with several excellent patterns (five-gate execution, HMAC audit trail, table-driven state machine, dynamic quorum, parse-failure upgrade). However, Demarch already has dcg for the pre-execution safety layer (verdict: adopt from the earlier assessment) and interlock for multi-agent coordination. slb's value to Demarch is in its **patterns and design principles**, not its runtime. The five-gate model, HMAC signing, and dynamic quorum are worth porting as concepts into Clavain's existing infrastructure rather than deploying slb as a separate system.

The full daemon/client architecture solves a problem Demarch doesn't yet have (multi-user agent fleets with formal peer approval workflows). If that need emerges, slb would be a strong candidate for adoption — but today, extracting patterns is the right move.

---

## Follow-Up Beads

1. **Port five-gate execution pattern to clavain-cli enforce-gate** — add TTL, command hash, and CAS to existing gate infrastructure (P3, effort: medium)
2. **Add HMAC signing to sprint phase transitions** — tamper-evident audit trail for gate approvals and overrides (P3, effort: low)
3. **Add dynamic quorum to quality-gates** — allow gate to pass with fewer verdicts when agents fail/timeout (P3, effort: low)
4. **Add parse-failure tier upgrade to pattern-matching hooks** — fail-closed principle for unrecognized command syntax (P4, effort: trivial)
