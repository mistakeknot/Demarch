# Temporal Durable-Execution Assessment — Q2 2026

**Assessed:** 2026-05-22
**Source:** https://temporal.io/ (Temporal 1.0 GA Jan 2026; $300M Series C Feb 2026); OpenAI Agents SDK + Temporal Python integration GA 2026-03-23
**Category:** Durable-execution substrate for agent orchestration
**Referenced from:** `docs/research/flux-research/sylveste-ecosystem-strategic-scan-2026q2-mythos-gate-e359cecd/SYNTHESIS.md` (Tier 2 #4), bead `sylveste-ewy3.1`

---

## What It Is

Temporal is an open-source durable-execution platform. Application code (in any of six SDK languages: Go, Java, Python, TypeScript, .NET, PHP) is structured into **Workflows** (deterministic orchestration logic) and **Activities** (non-deterministic effectful calls). The Temporal Service persists every workflow event to history so a workflow can be paused, crashed, redeployed, or replayed without losing state. Retries, timeouts, signals, and queries are declarative.

The 2026 shipping detail that matters for Sylveste: OpenAI Agents SDK now ships a Temporal integration (Python, GA 2026-03-23) that wraps every agent invocation as a Temporal Activity. "Durable agents" is now a one-import primitive in the Python ecosystem. Industry has converged: durable execution is no longer a custom-build concern.

## What Intercore Has Today

The dispatch subsystem is the closest analog in Sylveste. Concretely:

| Capability | Intercore today | Temporal equivalent |
|---|---|---|
| Dispatch lifecycle (`spawned`/`running`/`completed`/`failed`/`timeout`/`cancelled`) | `internal/dispatch/dispatch.go` state machine, SQLite-backed | Workflow + ActivityExecution states |
| Optimistic-concurrency status transitions (`ErrStaleStatus`) | UPDATE...RETURNING with row counting (`UpdateStatus`) | Workflow IDs + signal idempotency |
| Retry policy with backoff | `internal/dispatch/retry.go` `Retry()` + `ShouldRetry()` | Declarative `ActivityOptions.RetryPolicy` |
| Conflict detection | `internal/dispatch/conflict.go` | Workflow IDs + reuse policy |
| Process spawn (unix/windows) | `spawn_unix.go` / `spawn_windows.go` via `os/exec` | Out of scope — Temporal calls activities in-process |
| Telemetry collection | `internal/dispatch/telemetry.go` (token aggregation) | Activity inputs/outputs in history |
| Outcome recording | `outcome.go` + `DispatchEventRecorder` interface | Workflow completion + activity result history |
| Durability | SQLite WAL with `PRAGMA journal_mode = WAL` | Cassandra / MySQL / Postgres history backend |

The dispatch subsystem alone is **4,393 LOC** (`wc -l core/intercore/internal/dispatch/*.go`). Counting `runtrack`, `event`, `lifecycle`, `phase`, and `retry`-adjacent code, Intercore reimplements a sizeable portion of what Temporal ships as a battle-tested service.

## What Intercore Adds That Temporal Doesn't

Stripping the dispatch state machine still leaves substantial Sylveste-specific value:

1. **Phase model** — `internal/phase/` encodes the brainstorm → strategy → plan → execute → review → ship phased-gate workflow. Temporal can express phases as workflow steps, but Sylveste's phase semantics (gate conditions, evidence requirements, advancement rules) are policy.
2. **Routing calibration** — `internal/routing/` couples dispatch outcomes back to model-selection decisions. The OODARC closed loop is uncopyable substrate.
3. **Coordination locks** — `internal/lock/` and `internal/coordination/` provide file-reservation primitives across concurrent agents. Temporal has no equivalent; it would coordinate via signals or external locks.
4. **Cost accounting** — `internal/cost/` and `internal/budget/` aggregate token spend with phase attribution. Temporal tracks workflow execution time and Activity duration; token cost is not native.
5. **Discovery pipeline** — `internal/discovery/` embeds and triages signals across confidence tiers. Not a workflow concern.
6. **Project-local durability** — Intercore uses one SQLite file per project (`.clavain/intercore.db`), auto-discovered by walking up from CWD. Temporal requires a centralized cluster. The shape of "per-project durability" is genuinely different.

## Cost Model

**Sylveste's actual dispatch volume** (from interstat cost queries, 2026-04 baseline):

- ~50–200 dispatches per sprint
- ~5–30 sprints per active day
- Upper bound: ~6,000 dispatches/day = ~180K dispatches/month
- Temporal counts an "Action" per workflow signal, activity start, timer, etc. — typical ratio is 3–5 Actions per business-level "dispatch"
- Estimated monthly Action volume at current scale: **~720K to 1.2M Actions/month**

**Temporal Cloud at this volume:**
- First 5M Actions at $50/M → ~$36–60/month (within entry tier)
- Storage: ~$0.042/GBh active; with 30-day retention and ~1KB per dispatch history, ~$15/month
- Total: **~$50–75/month** for Sylveste's current activity, scaling sub-linearly

**Self-hosted Temporal Cluster on zklw:**
- Requires Cassandra OR MySQL 8+/Postgres 13+ as history store
- Minimum: 2GB RAM for service + 2GB for backend = 4GB sustained
- Plus: frontend / matching / history / worker services; minimum viable single-node is OK for dev but doesn't survive zklw reboot windows
- Real ops cost: backup the history DB, monitor task-queue lag, manage version upgrades (~quarterly)
- Verdict: self-host pays back only above ~10M Actions/month. At Sylveste's scale, Temporal Cloud is cheaper *and* simpler than self-host.

## Risks Named

1. **Determinism trap.** Temporal Workflows must be deterministic — same input must produce same execution trace on replay. LLM calls are not deterministic. Standard pattern: every LLM invocation wrapped as an Activity (Activities are not replayed; they emit a result to the workflow history). This is the OpenAI Agents SDK integration shape. Sylveste's existing `Dispatch` → process-spawn pattern maps cleanly to this: each agent invocation is one Activity.
2. **Vendor lock-in on history format.** Workflow state lives in Temporal's history; migrating off is non-trivial. Mitigation: Temporal is open source and Apache-2.0, can self-host if Cloud pricing changes. The history schema is documented.
3. **Operational drift if both paths coexist.** Two dispatch backends means two debugging paths and two consistency models. Mitigation: both write to Intercore's event log (`internal/event/`), so observation stays unified even when execution forks.
4. **Go SDK vs. Python SDK.** OpenAI's official Temporal integration is Python-only as of 2026-05. Intercore is Go. The integration *pattern* (workflow + activity wrapping) is portable to Go via the Temporal Go SDK (mature since 2019 — Temporal's canonical SDK), but Sylveste does not inherit the OpenAI integration "for free." This affects only Hassease / Skaffen, which spawn agents via subprocess; pure Intercore dispatch already works in Go.
5. **Project-local durability mismatch.** Sylveste's project-isolated SQLite per `.clavain/` directory is an explicit design choice (no shared cluster, no cross-project leakage). Centralized Temporal undoes this. Mitigation: use Temporal Namespaces per project; deferred until a Sylveste deployment serves multiple users.

## Verdict: **port-partially**

Adopt Temporal as the durable-execution substrate for **new** dispatch flows; keep `ic dispatch` SQLite as the legacy path through the Mythos window; revisit full migration at Mythos+1 month.

Concretely:

- **New flows target Temporal:**
  - Hassease daemon (`sylveste-nr6x`) — long-running background work with explicit durability requirements, Temporal-native from day one.
  - Skaffen Go agent execution (`sylveste-benl`) — sovereign-agent runs need crash-resume; Temporal solves this without a custom retry-on-restart path.
  - Any new dispatch surface introduced for Mythos features.
- **Existing flows stay on `ic dispatch`:**
  - Clavain hook-driven dispatches (hundreds of integration points; the migration cost is not the bottleneck story for Mythos).
  - All currently-passing integration tests (`bash test-integration.sh` and `go test ./...`).
- **Unified observation layer:**
  - Both paths emit to `internal/event/` so Interspect cursors over kernel events still see a single stream.
  - `ic events tail` reads both Temporal-originated and SQLite-originated dispatch events.

This is **not** "inspire-only." It is genuine substrate adoption, scoped tight. It is **not** "adopt fully" — that would risk Mythos shipping under refactor-debt.

### Why not "adopt fully"

The Mythos window is 12 weeks. Migrating ~hundreds of Clavain hook integration points to a new dispatch backend, while simultaneously shipping Hermes + Skaffen + Hassease + closed-loop calibration, is a recipe for missing all four. The data also doesn't support it: Intercore's dispatch lifecycle isn't broken; it's just duplicated work that future flows shouldn't pay.

### Why not "inspire-only"

The OpenAI Agents SDK + Temporal integration is now baseline. New Sylveste agent surfaces compete in a world where competitors get crash-resume + observability + retries declaratively. Reimplementing this in Hassease and Skaffen would burn months and produce a worse substrate.

### Why not "skip"

Skipping commits Sylveste to maintaining the dispatch state machine indefinitely. Temporal 1.0 + the OpenAI integration mark the industry-baseline moment; "skip" would compound technical debt for 12+ months until the next forced re-examination.

## What Survives 12-Month Re-Examination

If, 12 months from now, someone re-opens this question, the verdict should still hold under these conditions:

- Temporal Cloud pricing stays in the $50/M Actions range or cheaper (currently entry tier).
- Sylveste dispatch volume stays under 100M Actions/month (single-user / small-team scale).
- Intercore continues to own phase, routing, calibration, locks, and discovery; Temporal continues to own durability, retries, observability.
- Both backends keep writing to the kernel event log.

If any of these change — particularly if Sylveste scales to multi-tenant SaaS — the verdict should flip to "adopt fully with centralized Temporal Cluster" or "self-host Cluster on dedicated infra." The dual-path approach is a forking gate, not a permanent architecture.

## Practical Next Steps

### Phase 1 — Spike (1 sprint, within ewy3.1)

1. **Stand up Temporal Cloud namespace** for Sylveste dev. Free tier covers the spike. Document the namespace identifier in `core/intercore/CLAUDE.md`.
2. **Wire one dispatch flow as a Temporal Workflow.** Candidate: a Skaffen test-run dispatch (single Activity, well-bounded scope). Use Temporal Go SDK.
3. **Mirror writes to Intercore event log.** Activity completion hook emits to `internal/event/` with the same envelope shape as today's dispatch events.
4. **Measure:**
   - Latency per dispatch (Temporal vs. SQLite path)
   - Action count per dispatch (informs cost projection)
   - Observability fidelity (does the Temporal Web UI history match the Intercore event timeline?)
   - Crash-resume test (kill worker mid-dispatch, verify resume)

### Phase 2 — Targeted integration (post-spike, Mythos window)

5. **Hassease daemon ships on Temporal directly** (`sylveste-nr6x` acceptance criteria gain a "durable-execution backend = Temporal" line). Activity = each tool invocation; workflow = the daemon's outer loop.
6. **Skaffen Go sovereign-agent runs ship on Temporal** (`sylveste-benl` follow-up bead). Each Phase becomes an Activity; the OODARC loop is the workflow.
7. **Document the dual-path contract** in `core/intercore/AGENTS.md`: when to use `ic dispatch` (legacy hooks, sync flows), when to use Temporal (new async/durable flows).

### Phase 3 — Decision gate (Mythos+1 month)

8. Re-run cost + ops measurements at 4 weeks of production traffic.
9. File decision bead: "full migration of `ic dispatch` to Temporal, or maintain dual-path?" Decide based on (a) operational drift cost, (b) developer cognitive load, (c) Mythos+1mo dispatch volume.

## Follow-Up Beads to File

- **`sylveste-ewy3.1.1`** (P1, blocked-on-ewy3.1) — Stand up Temporal Cloud dev namespace; document credentials path.
- **`sylveste-ewy3.1.2`** (P1) — Wire first Skaffen test-dispatch as Temporal Workflow; mirror to event log.
- **`sylveste-ewy3.1.3`** (P0, links to `sylveste-nr6x`) — Hassease daemon uses Temporal as durable substrate.
- **`sylveste-ewy3.1.4`** (P0, links to `sylveste-benl`) — Skaffen sovereign-agent runs use Temporal workflows.
- **`sylveste-ewy3.1.5`** (P2) — Decision gate at Mythos+1mo: full migration vs. dual-path. Pre-filed; opens on calendar trigger.

## References

- Temporal 1.0 release notes (Jan 2026): https://temporal.io/blog/temporal-1-0
- Temporal pricing (Q2 2026): https://temporal.io/pricing
- Temporal Go SDK docs: https://docs.temporal.io/develop/go
- OpenAI Agents SDK + Temporal integration (GA 2026-03-23): https://temporal.io/blog/announcing-openai-agents-sdk-integration
- Synthesis source: `docs/research/flux-research/sylveste-ecosystem-strategic-scan-2026q2-mythos-gate-e359cecd/SYNTHESIS.md` (Tier 2 #4, framework-docs-researcher.md "Existential Risk #1")
- Intercore dispatch subsystem: `core/intercore/internal/dispatch/` (4,393 LOC, 21 files)
- Intercore vision (cross-reference): `core/intercore/docs/intercore-vision.md`
- PHILOSOPHY (External Tools doctrine): `PHILOSOPHY.md` § "Adopt mature external tools rather than rebuild"
- Beads: `sylveste-ewy3.1` (this assessment), `sylveste-ewy3` (parent epic), `sylveste-ewy3.2` (Langfuse parallel assess).
