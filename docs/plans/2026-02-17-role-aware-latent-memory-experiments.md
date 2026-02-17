# Role-aware Latent Memory — Implementation Plan
**Bead:** iv-wz3j
**Phase:** planned (as of 2026-02-17T00:00:00Z)

## Goal
Prototype role-aware memory layers and validate leakage prevention, retention, and token efficiency.

### Task 1: Memory taxonomy
- Define memory profiles in `interphase` (ephemeral / local / project-long).
- Add role labels for each memory write (planner, executor, reviewer, verifier).

### Task 2: Isolation and retention
- Implement namespace and scope checks in shared memory store.
- Add TTL and explicit purge APIs for task completion or failure.

### Task 3: Safety controls
- Add memory read/write audit hooks with optional denylist/allowlist rules.
- Add guardrail checks for sensitive key leakage and stale context injection.

### Task 4: Evaluation harness
- Add benchmark suite with intentional cross-role leakage probes.
- Track contamination rate, false suppression, and retrieval recall by role.

### Task 5: Productization criteria
- Define go/no-go thresholds and documentation for memory retention policies.
- Add toggles for conservative mode and default mode.
