# round-2 / probe-1 — findings index (fd-kernel-contract)

Scope: gate-mode-self-weakening cluster (f-043 upheld, f-048-adjacent upheld). Every site that
resolves gate_mode or an equivalent weakening lever, with its current default and whether a
weakening leaves a durable trace. [t] = has durable trace, [NO-TRACE] = zero durable trace.

## Go — os/Clavain/cmd/clavain-cli

- HIGH | fd-kernel-contract | cmd/clavain-cli/gate_calibration.go:186-189 | emitInterspectEvent calls `ic events add`, a subcommand that does NOT exist (events.go:18 supports only tail/cursor/emit/record/list-review/list-agency); rc=3 discarded by `_, _ =` — the only audit emitter on the gate path is silently dead [NO-TRACE]
- HIGH | fd-kernel-contract | cmd/clavain-cli/phase.go:341-350 | CLAVAIN_SKIP_GATE bypass claims an audit event (calibration_skip_gate) but routes through the dead emitter above — intended trace never lands [NO-TRACE effective]
- MEDIUM | fd-kernel-contract | cmd/clavain-cli/phase.go:353 | CLAVAIN_SKIP_HANDOFF env skips all handoff-contract checks, no event, no log beyond absence of output [NO-TRACE]
- HIGH | fd-kernel-contract | cmd/clavain-cli/phase.go:355-361 | agency-spec load error → gateMode="shadow" (handoff pre-check degrades to warn-only), no audit [NO-TRACE]
- HIGH | fd-kernel-contract | cmd/clavain-cli/phase.go:378-384 | agency-spec load error → gateMode="shadow" (satisfaction gate degrades to warn-only), no audit [NO-TRACE]
- MEDIUM | fd-kernel-contract | cmd/clavain-cli/phase.go:395-399 | no ic run for bead → gate skipped, stderr only [NO-TRACE]
- MEDIUM | fd-kernel-contract | cmd/clavain-cli/phase.go:401-404 | ic binary unavailable → return nil with not even a stderr line [NO-TRACE]
- MEDIUM | fd-kernel-contract | cmd/clavain-cli/phase.go:141 | CLAVAIN_SKIP_BUDGET env skips budget check, no audit [NO-TRACE]
- HIGH | fd-kernel-contract | cmd/clavain-cli/handoff.go:693-702 | getGateMode defaults "shadow" on spec error AND on missing key — diverges from bash default "enforce" (lib-sprint.sh:1089) [NO-TRACE]
- HIGH | fd-kernel-contract | cmd/clavain-cli/handoff.go:706-724 | getGateModeForPhase falls back to defaults then "shadow"; missing per-stage key silently weakens [NO-TRACE]
- MEDIUM | fd-kernel-contract | cmd/clavain-cli/satisfaction.go:322-326 | no satisfaction results → pass [NO-TRACE]
- MEDIUM | fd-kernel-contract | cmd/clavain-cli/satisfaction.go:350-353 | no holdout configured → pass [NO-TRACE]

## Bash — os/Clavain/hooks

- HIGH | fd-kernel-contract | hooks/lib-sprint.sh:1089-1090 | `gate_mode=off` returns 0 with zero output and zero event; contradicts "admin-controlled/trusted" comment at :1018-1020 since any project-level .clavain/agency-spec.yaml can set it [NO-TRACE]
- HIGH | fd-kernel-contract | hooks/lib-sprint.sh:1141-1144 | shadow mode always returns 0; would-block messages go to stderr only and only when a gate fails — a clean shadow pass leaves nothing anywhere [NO-TRACE durable]
- MEDIUM | fd-kernel-contract | hooks/lib-sprint.sh:1115-1117 | CLAVAIN_SKIP_GATE fail-closed override echoes stderr and the *block* message at :1119 advertises "(audited)" but no audit record is written on either path — overclaim [NO-TRACE]
- MEDIUM | fd-kernel-contract | hooks/lib-sprint.sh:1130-1132 | spec unavailable after ic gate passed → return 0 silently [NO-TRACE]
- LOW | fd-kernel-contract | hooks/lib-sprint.sh:1135-1139 | stage has no gates in spec → return 0 (absence of config acts as weakening) [NO-TRACE]
- LOW | fd-kernel-contract | hooks/lib-sprint.sh:1060-1062 | unknown spec gate type → stderr log + skip (fail-open) [stderr only]
- MEDIUM | fd-kernel-contract | hooks/lib-sprint.sh:1313-1314 | CLAVAIN_SKIP_BUDGET env skips budget check, no audit [NO-TRACE]
- INFO | fd-kernel-contract | hooks/lib-sprint.sh:1089 | bash default on missing spec is ENFORCE (`|| gate_mode="enforce"`) vs Go SHADOW — the cross-implementation divergence at the heart of f-048

## intercore kernel

- HIGH | fd-kernel-contract | internal/phase/gate.go:472-477 | budget gate returns GatePass when querier is nil — configured budget_enforce silently inert [NO-TRACE]
- HIGH | fd-kernel-contract | cmd/ic/dispatch.go:443, cmd/ic/gate.go:74, cmd/ic/run_lifecycle.go:218, cmd/ic/run_config.go:428 | all four budget.New(...) call sites pass nil EventRecorder — budget_warning/budget_exceeded events dead (f-V4); overspend neither blocks nor records [NO-TRACE]
- LOW | fd-kernel-contract | internal/routing/config.go:111-113 | complexity.mode defaults "off"; no consumer enforces the mode outside config tests — defined-but-inert weakening lever [NO-TRACE]

## interverse — interphase

- MEDIUM | fd-kernel-contract | interphase/hooks/lib-gates.sh:354-358 | CLAVAIN_DISABLE_GATES=true bypasses ALL gate enforcement; trace is a best-effort append to ~/.clavain/telemetry.jsonl (`|| true`) [weak trace]
- MEDIUM | fd-kernel-contract | interphase/hooks/lib-gates.sh:136-138 | strict/fail-closed mode opt-in via CLAVAIN_GATE_FAIL_CLOSED, default false — permissive-by-default with no trace that strict mode was off [NO-TRACE]
- LOW | fd-kernel-contract | interphase/hooks/lib-gates.sh:323-336,427-435 | CLAVAIN_SKIP_GATE hard-tier bypass writes bd notes + telemetry — the ONLY bypass path fleet-wide with a genuinely durable trace [t]
- LOW | fd-kernel-contract | interphase/hooks/lib-gates.sh:361-363 | missing bead_id/target → allow, no log [NO-TRACE]
- INFO | fd-kernel-contract | interphase/hooks/lib-gates.sh:386-389,450-457 | tier=none and tier=soft always pass; logged to telemetry.jsonl only [weak trace]

## Env-var weakening levers (complete set found)

`CLAVAIN_SKIP_GATE` (phase.go:341, lib-sprint.sh:1115, lib-gates.sh:351), `CLAVAIN_SKIP_HANDOFF`
(phase.go:353), `CLAVAIN_SKIP_BUDGET` (phase.go:141, lib-sprint.sh:1314),
`CLAVAIN_SKIP_CANARY` (skills/landing-a-change/SKILL.md:85), `CLAVAIN_ALLOW_UNSAFE`
(scripts/dispatch.sh:427), `CLAVAIN_DISABLE_GATES` (lib-gates.sh:354),
`CLAVAIN_GATE_FAIL_CLOSED` (lib-gates.sh:137 — inverted: enables enforcement).

## Tally

- Weakening-resolution sites: **27** (30 call sites counting the four budget.New(nil) wirings separately)
- Sites with zero durable trace on weakening: **23** (includes phase.go:341-350 whose trace is intended-but-dead)
- Sites with a real durable trace: **4** — all in interverse/interphase/hooks/lib-gates.sh (bd notes + telemetry.jsonl)
