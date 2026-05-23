# Langfuse Eval/Observability Substrate Assessment — Q2 2026

**Assessed:** 2026-05-23
**Source:** https://langfuse.com (Langfuse v3, OSS Apache-2.0); ClickHouse acquired Langfuse January 2026; self-host remains free
**Category:** LLM eval + tracing + observability substrate for agent systems
**Referenced from:** `docs/research/flux-research/sylveste-ecosystem-strategic-scan-2026q2-mythos-gate-e359cecd/SYNTHESIS.md` (Tier 2 #5), bead `sylveste-ewy3.2`

---

## What It Is

Langfuse is an open-source LLM-observability platform. It provides per-request traces (with nested spans), evaluation runs against datasets, prompt versioning, cost tracking, and a UI for browsing/filtering execution history. The OSS-first leader after ClickHouse's January 2026 acquisition — Langfuse remains Apache-2.0 and self-hostable for free; ClickHouse provides the analytical-storage backend the cloud offering already used.

Industry shape in 2026-Q2: eval and observability are commoditizing. Langfuse competes with Braintrust, Arize Phoenix, Laminar, MLflow, and Latitude. Langfuse is the OSS pick because self-host is genuinely supported and the Cloud free tier (50K units/month) covers small teams.

## What Interspect + Interstat Have Today

Two distinct surfaces. Interspect owns *qualitative evidence* (which agent did what, was it good, should routing change). Interstat owns *quantitative cost* (tokens by phase, cost-per-landable-change). Concretely:

| Capability | Sylveste today | Langfuse equivalent |
|---|---|---|
| Per-Task tool-use evidence | `interspect-evidence.sh` PostToolUse hook → SQLite at `.clavain/interspect/interspect.db` | `langfuse.trace()` + `langfuse.span()` |
| Session lifecycle | `interspect-session.sh` (SessionStart) + `interspect-session-end.sh` (Stop) | trace with input/output and end-time |
| Agent identifier tags | flux-drive agent ID in evidence rows | trace name + tags |
| Outcome classification | Counting-rule thresholds applied via `/interspect` | dataset runs + eval scores |
| Routing-override proposal | `/interspect:propose` reads SQLite patterns | custom — would query Langfuse traces via API |
| Canary monitoring | 20 uses or 14 days, 20% regression alert via SessionStart hook | not native — would need bespoke job |
| Per-bead cost queries | `cost-query.sh` with 15 modes against `~/.claude/interstat/metrics.db` | ClickHouse SQL via Langfuse query API |
| Cost-per-landable-change | `cost-query.sh baseline` joins token totals with `ic landed summary` | not native — derived metric |
| Per-project isolation | One SQLite per project at `.clavain/interspect/` | Langfuse "projects" within a workspace |
| Bead correlation | `bead_id` column in interstat metrics + ic landed_changes join | trace metadata field |

`hooks/lib-interspect.sh` is **114KB** of shell. Interstat's `cost-query.sh` is ~700 lines of SQL-generating bash. Together they encode a meaningful amount of evidence-pipeline logic — but only a fraction of that is the *policy* (canary windows, override proposals, regression alerts). Most of the volume is plumbing that Langfuse already provides.

## What Sylveste Adds That Langfuse Doesn't

The substrate-policy split here is sharper than the Temporal case:

1. **Canary monitoring policy** — "20 uses or 14 days, 20% regression alert" is a Sylveste invariant. Langfuse can store the data; it doesn't fire the alert.
2. **Routing-override proposal logic** — `/interspect:propose` synthesizes evidence into actionable overrides written to `.claude/routing-overrides.json`. The proposal heuristics are Sylveste's calibration policy.
3. **Bead correlation** — `cost-query.sh by-bead` and `cost-snapshot` answer "how much did sylveste-ewy3.1 cost?" Langfuse traces can carry `bead_id` metadata, but the bead is a Sylveste concept; the join logic (landed_changes + traces) stays in Sylveste.
4. **Cost-per-landable-change baseline** — the north-star metric. Defined as `total_session_cost / landed_changes_count` over a window. Langfuse has cost tracking per trace; the *landable-change* denominator comes from `ic landed`.
5. **Per-project SQLite isolation** — Sylveste deliberately stores evidence per-`.clavain/` directory. Langfuse centralizes by default; "one project = one Langfuse project" forces a setup decision Sylveste's local-first model avoids.
6. **OODARC integration** — the closed-loop calibration pattern that consumes interspect evidence to mutate routing/scoring is the Sylveste moat. Langfuse is a passive observer; OODARC is the active policy that turns observation into adjustment.

## Cost Model

**Sylveste's actual evidence volume** (from interstat baselines and synthesis estimates):

- ~10 sessions/day current; project to ~30/day at Mythos launch
- Each session: ~10–50 Task tool uses → ~10–50 evidence records
- Evidence records: ~300/day current, ~1.5K/day at Mythos = **~9K–45K records/month**
- Langfuse counts a "unit" per ingestion event (trace, span, generation). Each session ≈ 1 trace + ~20 observations = ~20 units
- Projected monthly units: ~6K (current) to ~30K (Mythos launch single-user)

**Langfuse Cloud at this volume:** within the free **Hobby tier** (50K units/month, 30-day retention, 2 users). $0/month.

**Langfuse Cloud at multi-user / multi-project scale:** Core tier at $29/month covers 100K units, 90-day retention, unlimited users. Adequate for Mythos+90d.

**Self-hosted on zklw:**
- Required services: PostgreSQL (already running for Intercom), ClickHouse (**new dependency**), Redis (**new**), S3-compatible blob storage (MinIO if no AWS — **new**)
- Minimum container footprint: ~6–10GB RAM sustained (ClickHouse 2GB minimum + Postgres 1GB + Redis 0.5GB + Worker 1GB + Web 1GB + buffer)
- Ops burden: ClickHouse upgrades, blob storage backup, S3 endpoint config, Helm or Docker Compose orchestration
- Real cost: meaningful infra investment. Pays back only at volumes where Cloud's $199/mo Pro tier (100K units) gets exceeded — i.e., 1M+ units/month, which is roughly 10x Mythos+90d projection.

The cost calculus inverts Temporal's: self-host pays back later for Langfuse because the required infra (ClickHouse, Redis, S3) is heavier than Temporal's (Postgres or MySQL). Sylveste's pre-launch scale doesn't justify the ops investment.

## Risks Named

1. **ClickHouse acquisition concentration.** ClickHouse owns the company now; license is still Apache-2.0 but the OSS commitment depends on continued ClickHouse strategy. Mitigation: assess docs are revisitable; if license posture shifts, the fork value of the OSS code is real (Phoenix, Laminar are alternatives).
2. **Per-project isolation pattern mismatch.** Sylveste's "one SQLite per `.clavain/` directory" model preserves project boundaries cleanly. Langfuse "one trace per project" model centralizes by default. For solo-developer Sylveste this is mostly an org chart question; for multi-tenant Sylveste it matters. Deferred until multi-tenant is on the table.
3. **Bespoke evidence schema migration cost.** Interspect's evidence table has specific columns (`outcome`, `pattern_match`, `signal_dim`) tied to the routing-proposal heuristics in `/interspect:propose`. Migration requires either (a) preserving these as Langfuse trace metadata + rewriting the proposal logic to query Langfuse, or (b) dual-write to both stores during transition. (b) is the safer path.
4. **OTEL convention drift.** Anthropic's Claude Code is emitting OpenTelemetry context (`v0.2.113+`). Langfuse accepts OTEL ingestion. Sylveste's evidence schema is *not* OTEL-shaped today. Adopting OTEL is the wider-leverage move — Langfuse adoption falls out of it. Order matters: OTEL first, Langfuse second.
5. **Loss of bash-hook simplicity.** The current interspect hook is `lib-interspect.sh` + SQLite — runs anywhere bash + sqlite3 exist. Langfuse SDK is Python/TypeScript; either adds a runtime dependency to Clavain hooks (complicated) or means hooks POST JSON over HTTP (workable but new failure mode if Langfuse is down).
6. **Dolt evidence pipeline already in flight.** `interspect_events` kernel table is consumed via `ic interspect query`. Two storage substrates for the same evidence creates the same dual-path drift risk named in `assess-temporal-2026q2.md`. Mitigation: write the dual-path contract explicitly *before* the spike, not after.

## Verdict: **port-partially**

Same shape as the Temporal verdict for the same structural reason — substrate-consolidation is real, but big-bang migration during the Mythos window risks shipping under refactor-debt. Concretely:

- **Adopt Langfuse Cloud (Hobby tier) as a dual-write target** for evidence during the spike window. Free; zero ops cost. Validates the assumption that Langfuse can hold Interspect's evidence shape.
- **Keep SQLite as the primary store** through Mythos. Routing-override proposals, canary monitoring, and `cost-query.sh` continue reading from SQLite. No production query path moves yet.
- **Adopt OpenTelemetry trace conventions in Interspect evidence emission first.** This is the higher-leverage shift — it future-proofs evidence regardless of which eval backend wins. Langfuse adoption then becomes a configuration change, not a schema change.
- **Defer self-hosted Langfuse** until Mythos+1mo decision gate. At pre-launch volume the Cloud free tier covers usage; the multi-service self-host (ClickHouse + Redis + Postgres + S3) doesn't pay back yet.
- **Decision gate at Mythos+1mo:** based on dual-write fidelity + post-launch volume, decide (a) full migration to Langfuse-as-primary + self-host, (b) Cloud-as-primary + SQLite retired, or (c) keep SQLite primary indefinitely with Langfuse as ecosystem-compatibility export.

### Why not "adopt fully"

The bead's acceptance criterion #1 calls for a self-hosted instance on zklw with PostgreSQL + ClickHouse + Redis. At Sylveste's pre-launch scale (~10 sessions/day) this is a 6–10GB RAM investment for ~6K units/month of traffic — Cloud free tier covers it ten times over. Self-host is the right answer at scale; it's the wrong answer pre-launch.

### Why not "inspire-only"

Eval substrates are converging. Building bespoke evidence collection now and forcing a later migration costs more than starting the alignment now (OTEL + dual-write). Inspire-only here means "we'll deal with it later" — which is what Sylveste has already been doing, and the assess process is explicitly designed to break that loop.

### Why not "skip"

Skipping commits Sylveste to maintaining `lib-interspect.sh` (114KB shell monolith) and `cost-query.sh` (~700 LOC bash) indefinitely. Both are working today; both are debt that grows. Aligning evidence emission to OTEL + adopting a dual-write target buys insurance against forced migration when the bash monoliths break under scale.

## What Survives 12-Month Re-Examination

The verdict holds under these conditions:

- Langfuse remains Apache-2.0 OSS post-acquisition; ClickHouse continues sponsoring the project as a strategic loss-leader.
- Sylveste evidence volume stays under 1M units/month (single-user / small-team scale).
- Anthropic's OTEL convention shipping in Claude Code stays the default; the agent ecosystem standardizes on OTEL ingestion.
- The Interspect policy layer (canary monitoring, override proposals) stays Sylveste's responsibility — never migrated to Langfuse.

If any of these change — particularly if Langfuse license shifts, or if Sylveste hits Mythos+6mo with multi-tenant traffic — the verdict should flip to "self-host Langfuse + full migration" or "explore Laminar / Arize Phoenix as OSS alternatives." The Cloud Hobby + dual-write approach is a forking gate, not a permanent shape.

## Practical Next Steps

### Phase 1 — OTEL alignment (precondition for Langfuse)

1. **Audit Interspect evidence schema for OTEL compatibility.** Map current evidence columns (`outcome`, `pattern_match`, `signal_dim`) to OTEL span attributes. Document the gap.
2. **Add OTEL emission to `interspect-evidence.sh`** as a feature-flagged write alongside SQLite. Default off; enable per-project via `.clavain/interspect/config.yaml`.
3. **Verify Claude Code OTEL context propagation reaches the hook.** `v0.2.113+` ships this; confirm trace IDs are available in the PostToolUse hook environment.

### Phase 2 — Langfuse Cloud spike (within ewy3.2)

4. **Stand up Langfuse Cloud Hobby project** for Sylveste dev. Free; no credit card. Document the project ID + API keys path in `interverse/interspect/CLAUDE.md`.
5. **Wire dual-write from `interspect-evidence.sh`:** every Task PostToolUse emits to both SQLite (primary) and Langfuse (shadow). Use the same evidence shape; Langfuse trace name = agent ID, span attributes = evidence columns.
6. **Run dual-write for one observation window (14 days, ~150 traces).** Verify Langfuse holds the full evidence shape — no data loss, no schema drift.
7. **Measure:**
   - Hook latency added by dual-write (target: <50ms p95)
   - Unit count consumed in the window (validates cost model)
   - Langfuse UI usefulness for evidence browsing (qualitative)
   - Can `/interspect:propose` heuristics run from Langfuse query API instead of SQLite? (Spike a side-by-side comparison.)

### Phase 3 — Decision gate (Mythos+1mo)

8. Re-measure unit volume and self-host ROI at 4 weeks of post-launch traffic.
9. File decision bead: "migrate Interspect primary store to Langfuse (Cloud or self-host), or keep SQLite + Langfuse as compatibility shadow?"

## Follow-Up Beads to File

- **`sylveste-ewy3.2.1`** (P1) — OTEL alignment audit + feature-flagged emission in `interspect-evidence.sh`.
- **`sylveste-ewy3.2.2`** (P1) — Langfuse Cloud Hobby project setup + dual-write spike (14-day observation window).
- **`sylveste-ewy3.2.3`** (P2) — Mythos+1mo decision gate: Langfuse primary vs. SQLite primary + Langfuse shadow.
- **`sylveste-ewy3.2.4`** (P2, blocked-on-3) — If self-host wins at the gate: file scoping epic for ClickHouse + Redis + S3 deployment on zklw (or successor).

## References

- Langfuse pricing (Q2 2026): https://langfuse.com/pricing
- Langfuse self-hosting docs: https://langfuse.com/self-hosting
- Langfuse acquisition by ClickHouse: https://clickhouse.com/blog/clickhouse-acquires-langfuse (Jan 2026)
- Synthesis source: `docs/research/flux-research/sylveste-ecosystem-strategic-scan-2026q2-mythos-gate-e359cecd/SYNTHESIS.md` (Tier 2 #5, best-practices-researcher.md Finding #3)
- Interspect implementation: `interverse/interspect/hooks/lib-interspect.sh`, `interverse/interspect/hooks/interspect-evidence.sh`
- Interstat queries: `interverse/interstat/scripts/cost-query.sh`
- Sister assessment (parallel substrate consolidation): `docs/research/assess-temporal-2026q2.md`
- PHILOSOPHY (External Tools doctrine): `PHILOSOPHY.md` § "Adopt mature external tools rather than rebuild"
- Beads: `sylveste-ewy3.2` (this assessment), `sylveste-ewy3` (parent epic), `sylveste-ewy3.1` (Temporal parallel verdict).
