# Contract Ownership Matrix

Maps each Intercore contract surface to its owner, consumers, and versioning policy.

## CLI Output Contracts

| Command | Output Schema | Owner | Consumers | Stability |
|---------|--------------|-------|-----------|-----------|
| `run create` | `cli/run-status.json` | Intercore | Clavain bash, Autarch Go | Stable |
| `run status` | `cli/run-status.json` | Intercore | Clavain bash, Autarch Go | Stable |
| `run advance` | `cli/run-status.json` | Intercore | Clavain bash | Stable |
| `run list` | `cli/run-list-item.json` | Intercore | Clavain bash, Autarch Go | Stable |
| `run tokens` | `cli/run-tokens.json` | Intercore | Clavain bash | Stable |
| `run budget` | `cli/run-budget.json` | Intercore | Clavain bash | Stable |
| `run agent list` | `cli/run-agent.json` | Intercore | Clavain bash | Stable |
| `run artifact list` | `cli/run-artifact.json` | Intercore | Clavain bash | Stable |
| `dispatch spawn` | `cli/dispatch-status.json` | Intercore | Clavain bash | Stable |
| `dispatch status` | `cli/dispatch-status.json` | Intercore | Clavain bash, Autarch Go | Stable |
| `dispatch list` | `cli/dispatch-list-item.json` | Intercore | Clavain bash | Stable |
| `dispatch tokens` | `cli/dispatch-tokens.json` | Intercore | Clavain bash | Stable |
| `coordination reserve` | `cli/coordination-reserve.json` | Intercore | Interlock MCP | Stable |
| `coordination release` | `cli/coordination-lock.json` | Intercore | Interlock MCP | Stable |
| `coordination conflicts` | `cli/coordination-conflict.json` | Intercore | Interlock MCP | Stable |
| `gate check` | `cli/gate-check.json` | Intercore | Clavain bash | Stable |
| `discovery list` | `cli/discovery-item.json` | Intercore | Clavain bash | Stable |
| `discovery profile` | `cli/discovery-profile.json` | Intercore | Clavain bash | Stable |
| `events tail` | `cli/event.json` | Intercore | Clavain bash, Interspect | Stable |
| `scheduler stats` | `cli/scheduler-stats.json` | Intercore | Clavain bash | Stable |
| `lane list` | `cli/lane.json` | Intercore | Clavain bash | Stable |
| `config get` | inline map | Intercore | Clavain bash | Unstable |

## Event Payload Contracts

| Event Type | Schema | Owner | Consumers |
|-----------|--------|-------|-----------|
| `phase.advance` | `events/phase-advance.json` | Intercore | Clavain hooks, Interspect |
| `dispatch.status_change` | `events/dispatch-status-change.json` | Intercore | Clavain hooks, Interspect |
| `interspect.*` | `events/interspect-signal.json` | Intercore | Interspect |

<!-- Traceability (iv-k0kgq, iv-xm17j): consumers are indirect, not string-matchable.
     Clavain hooks: intercore handler_hook.go maps SourcePhase/SourceDispatch to
     .clavain/hooks/on-phase-advance and on-dispatch-change (convention-based dispatch).
     Interspect: ic events tail --all --consumer=interspect-consumer in lib-interspect.sh
     _interspect_consume_kernel_events() — generic cursor consumer, no event type filter. -->

## Versioning Policy

**Stable contracts:**
- Field additions: non-breaking (consumers MUST ignore unknown fields)
- Field renames: BREAKING (requires override file)
- Field removals: BREAKING (requires override file)
- Type changes: BREAKING (requires override file)
- Nullable to non-nullable: BREAKING

**Breaking change process:**
1. Create `contracts/overrides/YYYY-MM-DD-<description>.md` with migration notes
2. CI allows the schema diff for that cycle
3. Notify consumers manually (future: automated cross-repo PRs)
4. Remove override after consumers migrate
