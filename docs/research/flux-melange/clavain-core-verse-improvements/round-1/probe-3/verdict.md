# probe-3 verdict — fd-kernel-contract (gate integrity cluster)

f-043 is CONFIRMED, and is worse than stated: every default kernel gate condition (core/intercore/internal/phase/gate.go:118-145) checks only the existence of records the agent under review creates itself — artifacts registered via `ic run artifact add` and verdicts parsed from the agent-written verdict sidecar (internal/dispatch/collect.go:80-84) — while the ship skill demands no verification at all (skills/ship/SKILL.md:8), the shipped fleet default for spec gates is shadow/warn-only (config/agency-spec.yaml:16), and hooks.json has no PreToolUse Bash matcher, so raw `git push`/`bd close` bypass the entire stack. The sole executed-proof gate, `runtime_evidence` via runtimeproof.VerifyFile, is opt-in through the `close-gate:runtime-evidence` label or `--runtime-evidence` flag and is used by exactly one bead across all ~/projects trackers. f-048 is PARTIAL: the self-weakening capability is real, but `commands/degraded-modes.yaml` is advisory-only (read by the agent per commands/sprint.md:579, never by code); the code-enforced lever is project-level `.clavain/agency-spec.yaml`, where `gate_mode: off` returns 0 silently at hooks/lib-sprint.sh:1090, `shadow` always passes at lib-sprint.sh:1141-1144, and the Go enforce-gate degrades to shadow on any spec-load error — with zero audit events anywhere on that path, contradicting the "admin-controlled" trust comment at lib-sprint.sh:1018-1020. The failure-direction split from f-042 persists verbatim: the Go enforce-gate fails open on a missing kernel (phase.go:394-404) while the bash twin now fails closed for design/ship (lib-sprint.sh:1114-1121), and the two lib-intercore.sh copies still diverge (214 diff lines) under an identical 1.1.0 version stamp. A new finding in the same region: budget enforcement is doubly inert — the budget gate passes when its querier is nil (gate.go:472-477) and the warning/exceeded events are dead because the recorder is nil at all four cmd/ic call sites, so overspend neither blocks nor leaves a durable trace. There is no documented failure-direction policy anywhere in contracts/, so each call site's behavior is folklore a plugin author cannot code against.

## Failure-direction classification (kernel/spec/ic unavailable or unconfigured)

| Call site | Direction |
|---|---|
| clavain-cli phase.go:394-399 (no ic run) | fail-open (skip, nil) |
| clavain-cli phase.go:401-404 (ic unavailable) | fail-open (nil) |
| clavain-cli phase.go:355-361,378-384 (spec load error → shadow) | fail-open (warn-only) |
| clavain-cli handoff.go:693-702 (getGateMode error → shadow) | fail-open |
| clavain-cli satisfaction.go:322-326,350-353 (no results/holdout → pass) | fail-open |
| lib-sprint.sh:1090 (agency-spec gate_mode=off, silent) | fail-open (unlogged) |
| lib-sprint.sh:1122-1123 (no ic run, non-safety stage) | fail-open |
| lib-sprint.sh:1141-1144 (shadow mode) | fail-open (logged) |
| lib-sprint.sh:1130-1132 (spec unavailable after ic gate) | fail-open |
| lib-sprint.sh:1060-1062 (unknown spec gate type → skip) | fail-open (logged) |
| lib-intercore.sh gate_check (both copies, ic down → 0) | fail-open |
| lib-intercore.sh gate_override (both copies, ic down → 0) | fail-open |
| lib-intercore.sh sentinel_check_or_legacy — Clavain copy (ic down → allow) | fail-open |
| intercore gate.go:472-477 (budget querier nil → GatePass) | fail-open |
| lib-sprint.sh:1114-1121 (no ic run, design/ship) | fail-closed (env escape, logged) |
| lib-intercore.sh sentinel_check_or_legacy — core copy (ic down → legacy temp-file throttle) | fail-closed (divergent twin) |
| bead-close.sh:41-119 (runtime-evidence required → verify or exit 1) | fail-closed |
| bead-close.sh:124-141 (token/policy gate) | fail-closed |
| intercore gate.go:301-324 (runtime-evidence terminal gate, non-overridable) | fail-closed |
| intercore gate.go:276-280,296-300,549-552 (nil runtrack/verdict querier, unknown check → GateFail) | fail-closed |
| ic run advance (default priority=1, hard block; run_lifecycle.go:79) | fail-closed |
| ic gate check dry-run (exit 1 on any fail incl. soft; gate.go:216-219) | fail-closed |

Tally: 14 fail-open, 8 fail-closed — with the fail-closed set concentrated in opt-in paths (label-gated close, non-default dry-run consumers) and the fail-open set covering every default path.

## Minimal fix shapes

- f-043: make an executed check the default close gate for P0/P1 beads — have ship delegate to landing-a-change verification unless a bead carries an explicit opt-out label, and add a PreToolUse Bash hook that routes `bd close` through bead-close.sh.
- f-048: emit a durable, typed audit event whenever gate_mode resolves to off/shadow, and refuse `off` for design/ship stages without a recorded explicit reason (mirroring CLAVAIN_SKIP_GATE).
- f-042/failure-direction: publish one failure-direction clause in contracts/ ("kernel-absent ⇒ fail-closed for design/ship, fail-open elsewhere, always logged") and align phase.go with lib-sprint.sh's stage-based split.
- Wrapper divergence: single-source lib-intercore.sh (generated copy with embedded checksum) and bump INTERCORE_WRAPPER_VERSION on any behavioral diff.
- Budget: pass a real event recorder at the four cmd/ic `budget.New(..., nil)` call sites and make the nil-querier gate path fail closed when budget_enforce=true.

REMEDIATION: Make the executed-verification close gate the default for P0/P1 beads and emit a durable audit event on every gate_mode=off/shadow resolution, so neither ship-by-self-report nor silent self-weakening can occur without leaving a trace.
