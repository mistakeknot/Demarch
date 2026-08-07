# round-2 / probe-1 verdict — fd-kernel-contract (gate-mode-self-weakening fix surface)

The cluster is fully scoped. Exhaustive enumeration found **27 weakening-resolution sites**
(30 call sites with the four `budget.New(nil)` wirings counted separately); **23 leave zero
durable trace** when they weaken. The decisive new fact: the one audit emitter that was
supposed to cover the Go gate path, `emitInterspectEvent`
(os/Clavain/cmd/clavain-cli/gate_calibration.go:186-189), calls `ic events add` — a subcommand
that does not exist (core/intercore/cmd/ic/events.go:18 accepts only
`tail|cursor|emit|record|list-review|list-agency`). The error is swallowed by `_, _ =`, so the
`calibration_skip_gate` "audit event" advertised at phase.go:343-348 has never landed anywhere.
The working ingestion path is `ic events record --source=interspect --type=<t> --payload=<json>`
(events.go:461+), durable in the kernel DB.

## Resolution-site inventory (default per site)

| # | Site | Lever | Current default | Trace on weaken |
|---|------|-------|-----------------|-----------------|
| 1 | phase.go:341-350 | CLAVAIN_SKIP_GATE | bypass allowed | intended event, DEAD emitter |
| 2 | phase.go:353 | CLAVAIN_SKIP_HANDOFF | handoff checks on; env skips all | none |
| 3 | phase.go:355-361 | spec load error | → shadow (warn-only) | none |
| 4 | phase.go:378-384 | spec load error (satisfaction) | → shadow | none |
| 5 | phase.go:395-399 | no ic run | skip gate | stderr only |
| 6 | phase.go:401-404 | ic unavailable | skip gate | none at all |
| 7 | phase.go:141 | CLAVAIN_SKIP_BUDGET | budget on; env skips | none |
| 8 | handoff.go:693-702 | getGateMode | shadow on error/missing | none |
| 9 | handoff.go:706-724 | getGateModeForPhase | stage override → defaults → shadow | none |
| 10 | satisfaction.go:322-326 | no results | pass | none |
| 11 | satisfaction.go:350-353 | no holdout | pass | none |
| 12 | lib-sprint.sh:1089-1090 | gate_mode=off | spec-driven; **missing spec → ENFORCE** | none (silent return 0) |
| 13 | lib-sprint.sh:1141-1144 | gate_mode=shadow | always pass | stderr only, and only on would-block |
| 14 | lib-sprint.sh:1115-1117 | CLAVAIN_SKIP_GATE | escape hatch | stderr; "(audited)" claim false |
| 15 | lib-sprint.sh:1130-1132 | spec unavailable post-ic-gate | pass | none |
| 16 | lib-sprint.sh:1135-1139 | no stage gates | pass | none |
| 17 | lib-sprint.sh:1060-1062 | unknown gate type | skip | stderr |
| 18 | lib-sprint.sh:1313-1314 | CLAVAIN_SKIP_BUDGET | env skips | none |
| 19 | gate.go:472-477 (intercore) | budget querier nil | GatePass | none |
| 20 | cmd/ic ×4 (dispatch.go:443, gate.go:74, run_lifecycle.go:218, run_config.go:428) | nil EventRecorder | budget events dead (f-V4) | none |
| 21 | routing/config.go:111-113 | complexity.mode | **off** (and inert — no consumer) | none |
| 22 | lib-gates.sh:354-358 | CLAVAIN_DISABLE_GATES | enforcement on; env kills all | telemetry.jsonl best-effort |
| 23 | lib-gates.sh:136-138 | CLAVAIN_GATE_FAIL_CLOSED | **false** (strict opt-in) | none |
| 24 | lib-gates.sh:323-336,427-435 | CLAVAIN_SKIP_GATE | bypass w/ reason | bd notes + telemetry [t] |
| 25 | lib-gates.sh:361-363 | missing inputs | allow | none |
| 26 | lib-gates.sh:386-389 | tier=none | pass | telemetry |
| 27 | lib-gates.sh:450-457 | tier=soft | pass | telemetry |

Bash/Go divergence (f-048 core): bash defaults **enforce** on missing spec
(lib-sprint.sh:1089, `|| gate_mode="enforce"`), Go defaults **shadow** (handoff.go:696,701,723;
phase.go:360,383). Same missing-spec condition, opposite enforcement posture.

## Audit-gap verdict

Existing machinery that COULD carry the trace:

- `ic events record --source=interspect|agency` — durable, working, accepts idempotency keys.
  Requires only `payload.agent_name` for interspect source. **This is the right vehicle.**
- `ic events emit` — alive but locked to review source / two event types; not usable for gate events.
- `internal/audit.Logger` (kernel) — durable, but no CLI surface and wired to coordination, not gates.
- interphase `_gate_log_enforcement` → `~/.clavain/telemetry.jsonl` — local file, best-effort
  (`|| true`), not queryable fleet-wide, but it is the only thing currently tracing anything.
- Budget warning/exceeded events — **dead per f-V4** (nil recorder at all four call sites); cannot
  carry anything until recorders are wired.
- `emitInterspectEvent` — **dead** (nonexistent subcommand). Fixing this one line revives the
  intended skip-gate audit at phase.go:346 with no other changes.

Net: 23/27 sites weaken silently. The 4 traced sites are all in interphase lib-gates.sh and use
an ad-hoc file, not the kernel event spine — so there is no single place to query
"when did any gate weaken, anywhere?"

## Policy vacuum

Confirmed: no failure-direction policy exists. `core/intercore/contracts/` holds event/CLI
schemas only; `degraded-modes.yaml` is advisory (settled f-048); fail-open/fail-closed language
appears only in scattered research notes and one autoship PRD. Draft policy:

> **Gate failure-direction policy.** Every gate resolution defaults to *enforce*; a gate that
> cannot reach its evidence (kernel absent, spec unloadable, querier nil, unknown check type)
> fails **closed** for the safety stages (design, ship) and fails **open** elsewhere — and in
> either case emits a durable `gate_mode_resolved` event to the kernel event spine recording
> mode, stage, reason, and actor. `shadow` is an explicit, per-project opt-in that always emits
> that event on every resolution; `off` is forbidden for design/ship unless accompanied by a
> recorded reason (mirroring CLAVAIN_SKIP_GATE) and may be set only by editing the project-level
> `.clavain/agency-spec.yaml` — never by env var, never by default, never silently. Any env-var
> bypass (CLAVAIN_SKIP_GATE, CLAVAIN_SKIP_HANDOFF, CLAVAIN_SKIP_BUDGET, CLAVAIN_DISABLE_GATES)
> must emit the same event before returning. A weakening that leaves no trace is a bug,
> regardless of direction.

## Minimal fix shape (3 files)

1. **os/Clavain/cmd/clavain-cli/handoff.go** — make `getGateMode`/`getGateModeForPhase` default
   `enforce` (unifying with bash), and add a `resolveGateMode(targetPhase)` wrapper that, on any
   non-enforce resolution (off/shadow/spec-error fallback), calls `emitInterspectEvent(
   "gate_mode_resolved", "mode=<m> stage=<s> reason=<r>")`. The two hardcoded `"shadow"`
   fallbacks at phase.go:360,383 route through it (two-line edit). Companion one-liner in the
   same package: gate_calibration.go:188 `runIC("events","add",...)` →
   `runIC("events","record","--source=interspect","--type="+eventType,"--payload=...")` —
   without it the new events go to the same void as calibration_skip_gate.
2. **os/Clavain/hooks/lib-sprint.sh** — in `enforce_gate`: emit the same
   `ic events record --source=interspect --type=gate_mode_resolved` (best-effort, guarded by
   `intercore_available`) on the `off` path (:1090), the shadow path (:1141), and the
   CLAVAIN_SKIP_GATE override (:1115), making the existing "(audited)" message true.
3. **core/intercore/contracts/gate-failure-direction.md** — the policy paragraph above, so both
   implementations and future gates have one citable contract.

Files 1+2 deliver (a) unified defaults and (b) audit events on every default-path non-enforce
resolution; file 3 delivers (c). Deferred to keep the set minimal: wiring real recorders at the
four `budget.New(nil)` sites (belongs with the f-V4 fix), aligning phase.go's fail-open no-run
paths with lib-sprint.sh's stage-based fail-closed split (f-042 fix), and adding the PreToolUse
Bash matcher (f-043 fix).

## New findings in-region

- **emitInterspectEvent dead emitter** (gate_calibration.go:188) — highest-leverage single line
  in the cluster; reviving it fixes the trace gap for the one bypass that already tries to audit.
- **complexity.mode lever** (internal/routing/config.go:111-113): defaults `off` and has no
  behavioral consumer — inert config surface that looks like a routing safety floor.
- **CLAVAIN_DISABLE_GATES** (interphase lib-gates.sh:354): kills ALL enforcement with one env
  var; not present in clavain-cli or lib-sprint.sh, so behavior differs by which enforce_gate
  implementation runs.
- **"(audited)" overclaim** (lib-sprint.sh:1119): user-facing text promises an audit trail that
  no code writes.
- hooks.json confirmed: PreToolUse matches only `Edit|Write|MultiEdit` — no Bash matcher, so raw
  `git push`/`bd close` bypass all of the above (settled f-043, re-verified this round).

REMEDIATION: Unify bash/Go on enforce-by-default and route every non-enforce gate resolution
through a fixed `ic events record` audit emitter (handoff.go + lib-sprint.sh +
contracts/gate-failure-direction.md), so no gate can weaken — by config, env var, or broken
dependency — without a durable, queryable trace.
