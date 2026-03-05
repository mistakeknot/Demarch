---
title: Factory Substrate Implementation Plan
artifact_type: plan
bead: iv-ho3
prd: docs/prds/2026-03-05-factory-substrate.md
stage: plan
version: 1
---

# Factory Substrate — Implementation Plan

## Overview

Implementation plan for PRD iv-ho3: add a validation-first factory substrate to Clavain by adopting CXDB for artifact storage, building a scenario bank with satisfaction scoring, wiring evidence pipelines, and enforcing agent capability policies. The plan is organized into 6 features (F1-F6) matching the PRD and existing bead structure. Each step is a discrete, testable unit of work.

**Beads:** F1=iv-296, F2=iv-g36hy, F3+F4=iv-c2r, F5=iv-3ov, F6=iv-b46

**Dependency chain:**
```
F1 (iv-296) ──→ F2 (iv-g36hy) ──→ F3+F4 (iv-c2r) ──→ F5 (iv-3ov)
     └──────────→ F6 (iv-b46)
```

**Key files (existing):**
- `os/clavain/cmd/clavain-cli/main.go` — command router (switch-based, not Cobra)
- `os/clavain/cmd/clavain-cli/phase.go` — `cmdEnforceGate`, phase transitions
- `os/clavain/cmd/clavain-cli/exec.go` — subprocess wrappers (ic, bd, git)
- `os/clavain/cmd/clavain-cli/types.go` — JSON/data structures
- `os/clavain/hooks/session-start.sh` — SessionStart hook
- `os/clavain/hooks/lib-sprint.sh` — sprint state library
- `os/clavain/config/handoff-contracts.yaml` — artifact validation rules
- `os/clavain/go.mod` — Go 1.22, only dependency: gopkg.in/yaml.v3

---

## F1: CXDB Adoption + Service Lifecycle (iv-296)

### Step 1.1: CXDB Cross-Compilation CI

**Files:** New: `.github/workflows/cxdb-release.yml`

Create a GitHub Actions workflow that:
1. Checks out CXDB source from `github.com/strongdm/cxdb`
2. Cross-compiles `cxdb-server` Rust binary for 4 targets: linux-x86_64, linux-aarch64, darwin-x86_64, darwin-aarch64
3. Publishes binaries as a Demarch GitHub release (tagged `cxdb-v<version>`)
4. Uses `cross` for Rust cross-compilation (standard Rust cross-compilation toolchain)

**Acceptance:** `gh release view cxdb-v0.1.0` shows 4 binaries.

### Step 1.2: CXDB Type Bundle

**Files:** New: `os/clavain/config/cxdb-types.json`

Create `clavain-types.json` with field-level schemas for all 7 CXDB types as specified in the PRD:
- `clavain.phase.v1`, `clavain.dispatch.v1`, `clavain.artifact.v1`
- `clavain.scenario.v1`, `clavain.satisfaction.v1`
- `clavain.evidence.v1`, `clavain.policy_violation.v1`

Use the exact field schemas from the PRD (bead_id, phase, blob_hash, timestamp, etc.).

**Acceptance:** JSON parses cleanly; all 7 types present with all fields from PRD schemas.

### Step 1.3: CXDB Service Lifecycle Commands

**Files:**
- New: `os/clavain/cmd/clavain-cli/cxdb.go`
- Edit: `os/clavain/cmd/clavain-cli/main.go` (add 3 commands to switch)
- Edit: `os/clavain/cmd/clavain-cli/exec.go` (add `runCXDB()` helper)

Implement three commands:
- `cxdb-start` — starts `cxdb-server` from `.clavain/cxdb/cxdb-server`, writes PID to `.clavain/cxdb/cxdb.pid`, creates `.clavain/cxdb/data/` dir, registers type bundles from `cxdb-types.json`, runs health check
- `cxdb-stop` — reads PID file, sends SIGTERM, removes PID file
- `cxdb-status` — reads PID file, checks process alive, returns JSON with version and context count

Follow existing patterns from `exec.go`: `runCXDB(args...)` subprocess helper, fail-safe on unavailability.

**Acceptance:** `clavain-cli cxdb-start && clavain-cli cxdb-status` returns health JSON. `clavain-cli cxdb-stop` cleanly terminates.

### Step 1.4: Setup Download Integration

**Files:** Edit: `os/clavain/hooks/session-start.sh` (or new `os/clavain/cmd/clavain-cli/setup.go`)

Add CXDB binary download to `clavain setup`:
1. Detect platform (`uname -s`/`uname -m` → target triple)
2. Download correct binary from Demarch GitHub release
3. Install to `.clavain/cxdb/cxdb-server`, `chmod +x`
4. Verify binary runs (`--version`)

**Acceptance:** Fresh project, `clavain setup` downloads binary; `cxdb-start` succeeds.

### Step 1.5: SessionStart Auto-Start Hook

**Files:** Edit: `os/clavain/hooks/session-start.sh`

Add CXDB auto-start logic to the SessionStart hook:
1. Check if `.clavain/cxdb/cxdb-server` exists (skip if not installed)
2. Check PID file — if process alive, skip
3. If not running, call `clavain-cli cxdb-start` in background
4. Log startup result to stderr

**Acceptance:** New session with CXDB installed → CXDB starts automatically. Without CXDB → no error.

### Step 1.6: Tests for F1

**Files:** New: `os/clavain/cmd/clavain-cli/cxdb_test.go`

Unit tests:
- PID file management (write, read, stale detection)
- Platform detection logic
- Type bundle JSON parsing
- Health check response parsing

**Acceptance:** `go test ./cmd/clavain-cli/... -run TestCXDB` passes.

---

## F2: Sprint Execution Recording (iv-g36hy)

### Step 2.1: CXDB Go SDK Integration

**Files:** Edit: `os/clavain/go.mod`, `os/clavain/go.sum`

Add CXDB Go SDK dependency:
```
go get github.com/strongdm/ai-cxdb/clients/go
```

Verify no conflicts with existing `go.mod` (currently only yaml.v3). The SDK adds uuid, msgpack, blake3 transitive deps.

**Acceptance:** `go build ./cmd/clavain-cli/...` succeeds with new dependency.

### Step 2.2: CXDB Client Package

**Files:** New: `os/clavain/cmd/clavain-cli/cxdb_client.go`

Implement `pkg/cxdb/` equivalent functions (keep in cmd/ to match existing pattern — clavain-cli has no pkg/ dir):
- `cxdbConnect() (*cxdb.Client, error)` — connect to local CXDB server
- `cxdbSprintContext(client, beadID string) (uint64, error)` — get/create context for sprint
- `cxdbRecordPhase(client, ctx uint64, phase PhaseRecord) error` — record phase transition turn
- `cxdbRecordDispatch(client, ctx uint64, dispatch DispatchRecord) error` — record agent dispatch turn
- `cxdbStoreBlob(client, data []byte) (string, error)` — store blob, return BLAKE3 hash
- `cxdbForkSprint(client, ctx, turnID uint64) (uint64, error)` — O(1) fork
- `cxdbQueryByType(client, ctx uint64, typeID string) ([]Turn, error)` — typed query
- `cxdbAvailable() bool` — health check (like `icAvailable()`)

All functions return errors; callers decide whether to fail or continue (fail-safe pattern from exec.go).

**Acceptance:** Client compiles, connects to running CXDB, basic write/read roundtrip works.

### Step 2.3: Phase Transition Recording

**Files:** Edit: `os/clavain/cmd/clavain-cli/phase.go`

Wire `cmdAdvancePhase` to record phase transitions in CXDB:
1. After successful phase advance, call `cxdbRecordPhase()` with bead_id, from/to phase, artifact path, blob hash
2. If artifact exists, store it as blob via `cxdbStoreBlob()` and reference hash in phase record
3. CXDB write failures: log to stderr, do NOT block phase transition (Intercore is authoritative)

**Acceptance:** Advance a phase → CXDB turn exists with correct type and fields. CXDB down → phase still advances.

### Step 2.4: DAG Sync Command

**Files:**
- New: `os/clavain/cmd/clavain-cli/cxdb_sync.go`
- Edit: `os/clavain/cmd/clavain-cli/main.go` (add `cxdb-sync` and `cxdb-fork` commands)

Implement:
- `cxdb-sync <sprint-id>` — reads `ic run events <run-id>`, iterates events, backfills CXDB Turn DAG for any sprint. Idempotent (skips already-recorded turns by checking event ID).
- `cxdb-fork <sprint-id> <turn-id>` — calls `cxdbForkSprint()` for O(1) branch.

**Acceptance:** Run `cxdb-sync` on an existing sprint → turns appear in CXDB. Run again → no duplicates.

### Step 2.5: Tests for F2

**Files:** New: `os/clavain/cmd/clavain-cli/cxdb_client_test.go`

Unit tests:
- Client connection error handling (CXDB not running)
- Phase record serialization
- Blob store/retrieve roundtrip
- Sync idempotency (mock ic events)

**Acceptance:** `go test ./cmd/clavain-cli/... -run TestCXDBClient` passes.

---

## F3+F4: Scenario Bank + Satisfaction Scoring (iv-c2r)

### Step 3.1: Scenario YAML Schema + Directory Convention

**Files:**
- New: `os/clavain/config/scenario-schema.yaml` (reference schema)

Define the v1 scenario YAML schema as documented in PRD (id, intent, mode, setup, steps with type discriminator, rubric with criterion/weight, risk_tags, holdout flag, schema_version).

Directory convention (created by commands, not by this step):
```
.clavain/scenarios/
  dev/           # failure-derived scenarios
  holdout/       # spec-derived + human-curated
  satisfaction/  # run results
```

**Acceptance:** Schema file parseable; matches PRD spec exactly.

### Step 3.2: Scenario CLI Commands

**Files:**
- New: `os/clavain/cmd/clavain-cli/scenario.go`
- Edit: `os/clavain/cmd/clavain-cli/main.go` (add 5 commands)

Implement:
- `scenario-create <name> [--holdout]` — scaffolds scenario YAML in appropriate directory (dev or holdout), populates with template fields
- `scenario-list [--holdout] [--dev]` — lists scenarios with metadata (id, intent, mode, step count, risk_tags)
- `scenario-validate` — validates all scenarios against schema (checks required fields, step types, rubric weights sum, schema_version)
- `scenario-generate --from-prd <path>` — reads PRD markdown, extracts acceptance criteria, generates holdout scenarios. Uses LLM agent dispatch (haiku) for extraction.
- Each command creates `.clavain/scenarios/` directory tree on first use

**Acceptance:** `scenario-create test-checkout && scenario-list` shows the new scenario. `scenario-validate` catches missing required fields.

### Step 3.3: Scenario Executor

**Files:** Edit: `os/clavain/cmd/clavain-cli/scenario.go` (add `cmdScenarioRun`)

Implement `scenario-run <pattern> [--sprint=<id>]`:
1. Glob match scenario files by pattern
2. For each matched scenario:
   a. Parse YAML, validate schema
   b. Spawn an executor agent (via `ic agent create` or fallback to Claude Code subagent dispatch)
   c. Agent follows scenario steps sequentially against actual codebase
   d. Record each step result (action taken, actual output, pass/fail per expect)
   e. Store trajectory as CXDB turns (`clavain.scenario.v1`)
3. Write results to `.clavain/scenarios/satisfaction/run-<id>.json`
4. Enforce: agents never write to `holdout/` (check after each step)

**Acceptance:** Run scenario against test project → trajectory recorded in CXDB, result JSON written.

### Step 3.4: Satisfaction Scoring

**Files:**
- New: `os/clavain/cmd/clavain-cli/satisfaction.go`
- Edit: `os/clavain/cmd/clavain-cli/main.go` (add `scenario-score` command)

Implement `scenario-score <run-id>`:
1. Load run result from `.clavain/scenarios/satisfaction/run-<id>.json`
2. For each scenario in run, invoke 3 LLM judges:
   - `fd-user-product` (UX/value)
   - `fd-correctness` (data integrity)
   - `fd-safety` (security)
3. Each judge scores per-criterion from rubric (0.0-1.0)
4. Take median of 3 judges per criterion
5. Compute overall score = weighted sum of criteria
6. Output: `satisfaction.json` with per_criterion_scores, overall_score, judge_model_version, trajectory CXDB ref, rationale
7. Record as CXDB turn (`clavain.satisfaction.v1`)
8. Judge failure: timeout 60s per scenario, bypass with warning after 3 consecutive failures
9. `--summary` flag: output pass/fail counts and aggregate satisfaction

**Acceptance:** Score a completed run → `satisfaction.json` exists with valid scores. Judge timeout → warning, not crash.

### Step 3.5: Closed-Loop Calibration

**Files:** Edit: `os/clavain/cmd/clavain-cli/satisfaction.go` (add `cmdScenarioCalibrate`)

Implement `scenario-calibrate`:
1. Query CXDB for all `clavain.satisfaction.v1` turns with sprint_outcome field set
2. Group by sprint outcome (merged/reverted/abandoned)
3. Compute optimal threshold that maximizes prediction accuracy (ROC-like)
4. Write calibrated threshold to `.clavain/satisfaction-calibration.json`
5. Minimum data: 20 sprints required; below that, use default 0.7

Follow the same 4-stage pattern as `calibrate-phase-costs` in budget.go:
- Stage 1: hardcoded 0.7 (from budget.yml)
- Stage 2: collect scores + outcomes
- Stage 3: calibrate
- Stage 4: calibrated threshold with 0.7 fallback

**Acceptance:** With <20 sprints → uses 0.7. With mocked 20+ → writes calibrated threshold.

### Step 3.6: Satisfaction Gate Integration

**Files:** Edit: `os/clavain/cmd/clavain-cli/phase.go`

Wire satisfaction gate into `cmdEnforceGate`:
1. After existing handoff contract checks, add satisfaction check for the `shipping` phase
2. Load threshold: calibrated (if exists) → `.clavain/budget.yml` override → 0.7 default
3. Query latest holdout satisfaction score for current sprint
4. If score < threshold → gate fails (blocks ship)
5. Check for holdout access violations → invalidate contaminated scores
6. Respect `CLAVAIN_SKIP_GATE` with auditable reason (already exists)
7. Gate mode from agency-spec (enforce/shadow) applies here too

**Acceptance:** Sprint with holdout satisfaction 0.5 + threshold 0.7 → gate blocks. `CLAVAIN_SKIP_GATE=true` → gate passes with warning.

### Step 3.7: Tests for F3+F4

**Files:** New: `os/clavain/cmd/clavain-cli/scenario_test.go`, `satisfaction_test.go`

Tests:
- Scenario YAML parsing + validation (valid, missing fields, bad types)
- Scenario list with filters
- Satisfaction score computation (median of 3 judges, weighted criteria)
- Calibration threshold calculation
- Gate integration (pass/fail/skip scenarios)

**Acceptance:** All scenario and satisfaction tests pass.

---

## F5: Evidence Pipeline Wiring (iv-3ov)

### Step 5.1: Evidence Pack Structure

**Files:**
- New: `os/clavain/config/evidence-manifest-schema.yaml`
- New: `os/clavain/cmd/clavain-cli/evidence.go`
- Edit: `os/clavain/cmd/clavain-cli/main.go`

Define evidence pack structure:
```
.clavain/evidence/<case>/
  manifest.yml       # provenance, type, replay instructions
  <attached files>
```

Implement:
- `evidence-to-scenario <finding-id>` — converts an Interject scan finding to dev scenario steps (writes to `.clavain/scenarios/dev/`, never `holdout/`)
- Evidence manifest schema: source_plugin, evidence_type, session_id, phase, timestamp, replay_instructions

**Acceptance:** Convert a finding → scenario YAML exists in dev/. Manifest validates against schema.

### Step 5.2: Interspect Evidence Recording Hook

**Files:** Edit: `os/clavain/hooks/session-start.sh` or new hook in `hooks/`

Wire Interspect profiler events to CXDB:
1. On profiler event emission (Interspect hook_id allowlist), record as CXDB turn (`clavain.evidence.v1`)
2. Source_plugin: "interspect", evidence_type: profiler event type
3. Attach blob hash for full profiler output

This is a hook integration — the Interspect hook emits events, this code catches and records them.

**Acceptance:** Interspect profiler event → CXDB evidence turn exists.

### Step 5.3: Flux-Drive Regression → Dev Scenario

**Files:** Edit: `os/clavain/cmd/clavain-cli/evidence.go`

Wire flux-drive review findings to dev scenarios:
1. When flux-drive review detects a regression finding (severity: error), auto-create dev scenario
2. Extract action/expect pairs from the finding description
3. Write to `.clavain/scenarios/dev/fd-<finding-hash>.yaml`
4. Never write to holdout (enforced by hardcoded path check)

**Acceptance:** Flux-drive regression finding → dev scenario YAML created.

### Step 5.4: Interstat Token Attachment

**Files:** Edit: `os/clavain/cmd/clavain-cli/cxdb_client.go`

Attach interstat token data to dispatch turns in CXDB:
1. After recording a dispatch turn, query interstat for session token counts
2. Store token breakdown as blob in CXDB CAS
3. Reference blob hash in dispatch turn

**Acceptance:** Dispatch turn in CXDB includes token data blob reference.

### Step 5.5: Sprint Failure Evidence Packs

**Files:** Edit: `os/clavain/cmd/clavain-cli/evidence.go`

Auto-generate evidence packs on sprint failure:
1. Hook into sprint failure detection (sprint abandoned or test failure)
2. Collect: relevant logs, CXDB trajectory, bead state, last few git commits
3. Write to `.clavain/evidence/<bead-id>/manifest.yml` + attachments
4. Record as CXDB evidence turn

**Acceptance:** Failed sprint → evidence pack exists at `.clavain/evidence/<id>/`.

---

## F6: Agent Capability Policies + Holdout Enforcement (iv-b46)

### Step 6.1: Policy Schema + CLI

**Files:**
- New: `os/clavain/config/default-policy.yaml`
- New: `os/clavain/cmd/clavain-cli/policy.go`
- Edit: `os/clavain/cmd/clavain-cli/main.go` (add `policy-check`, `policy-show`)

Define `.clavain/policy.yml` schema:
```yaml
phases:
  build:
    deny_paths:
      - ".clavain/scenarios/holdout/**"
    deny_tools: []
  quality-gates:
    allow_paths: ["**"]
    allow_tools: ["**"]
```

Implement:
- `policy-check <agent> <action> [--path=<path>]` — evaluates action against current phase policy, returns JSON `{"allowed": bool, "reason": "string"}`
- `policy-show` — displays current policy in human-readable table
- Policy uses Intercore phase state (not agent self-report) via `runIC("run", "phase", runID)`

**Acceptance:** `policy-check build-agent read --path=.clavain/scenarios/holdout/test.yaml` → denied. Same path in quality-gates phase → allowed.

### Step 6.2: SessionStart Holdout Exclusion (Preventive)

**Files:** Edit: `os/clavain/hooks/session-start.sh`

Add holdout context exclusion during Build phase:
1. Check current sprint phase via `ic run phase`
2. If phase is `executing` (Build): add `.clavain/scenarios/holdout/` to agent context exclusion list
3. This is the preventive layer — implementation agents never see holdout files
4. Validation agents during `shipping` phase get full access

**Acceptance:** During build phase, holdout files are excluded from agent context. During quality-gates, they're visible.

### Step 6.3: Holdout Access Audit Trail (Detective)

**Files:** Edit: `os/clavain/cmd/clavain-cli/policy.go`

Record holdout access violations:
1. Any `policy-check` call that touches holdout paths during build phase → record as CXDB turn (`clavain.policy_violation.v1`)
2. Fields: bead_id, agent_name, phase, action, target path, policy_rule
3. `enforce-gate` queries for violations → invalidates satisfaction scores

**Acceptance:** Holdout access during build → violation turn in CXDB. Gate check finds violation → scores invalidated.

### Step 6.4: Minimum Hardcoded Holdout Denial

**Files:** Edit: `os/clavain/cmd/clavain-cli/scenario.go`

Ensure holdout protection ships with F3 (before full policy framework):
1. All scenario write commands (`scenario-create`, `scenario-generate`) refuse to write to `holdout/` when called by non-human agents
2. `scenario-run` refuses to modify files in `holdout/`
3. Simple path check: `strings.Contains(path, "/holdout/")` → deny for agent callers

**Acceptance:** Agent attempting to write holdout scenario → error. Human CLI → allowed (--holdout flag).

### Step 6.5: Tests for F6

**Files:** New: `os/clavain/cmd/clavain-cli/policy_test.go`

Tests:
- Policy evaluation (allow/deny for each phase)
- Holdout path denial
- Violation recording
- Gate invalidation on contaminated scores

**Acceptance:** All policy tests pass.

---

## Execution Order

The steps should be executed in feature order (F1→F2→F3+F4→F5→F6) due to dependencies, but within each feature, steps are sequential. The one exception is Step 6.4 (minimum holdout denial) which should ship alongside F3 steps.

| Phase | Steps | Bead | Est. Complexity |
|-------|-------|------|-----------------|
| F1: CXDB Setup | 1.1-1.6 | iv-296 | High (cross-compilation, service lifecycle) |
| F2: Recording | 2.1-2.5 | iv-g36hy | High (SDK integration, sync logic) |
| F3+F4: Scenarios | 3.1-3.7 + 6.4 | iv-c2r | Very High (executor, scoring, calibration, gate) |
| F5: Evidence | 5.1-5.5 | iv-3ov | Medium (wiring existing plugins) |
| F6: Policies | 6.1-6.3, 6.5 | iv-b46 | Medium (policy framework, audit trail) |

## Risks

1. **CXDB Go SDK compatibility** — only current dep is yaml.v3. Must verify uuid/msgpack/blake3 don't conflict. Mitigation: test `go mod tidy` early (Step 2.1).
2. **Cross-compilation CI** — Rust cross-compilation for 4 targets can be flaky. Mitigation: use `cross` crate, test on CI before anything depends on binaries.
3. **LLM judge reliability** — 3-judge scoring introduces latency and non-determinism. Mitigation: 60s timeout, bypass after 3 failures, median reduces variance.
4. **Holdout contamination** — If preventive exclusion fails, detective audit is the safety net. Mitigation: defense in depth is the explicit architectural choice.
