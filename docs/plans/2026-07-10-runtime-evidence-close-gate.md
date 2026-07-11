---
artifact_type: plan
bead: sylveste-6h7x
stage: execution
requirements:
  - Runtime evidence is explicitly applicable per run
  - phase:done fails closed without a fresh typed receipt
  - Receipt proves built and installed identity, fresh boot, health, live event, state delta, isolation, and cleanup
  - Managed bead closure uses the same verifier before authorization consumption
  - Recurring read-only reconciliation reports tracker and runtime evidence orphans
  - Missing-proof and valid-proof paths are observed through installed binaries on Clavain and zklw
---

# Runtime Evidence Close-Gate Implementation Plan

> **For agents:** Use `clavain:executing-plans`, `intertest:test-driven-development`, and `intertest:verification-before-completion`. Commit and push each repository as its logical unit lands.

**Bead:** `sylveste-6h7x`

**Goal:** Prevent `phase:done` and Clavain-managed bead closure until an explicitly gated run has a fresh, content-addressed receipt proving that the built artifact was installed, booted in isolation, healthy, causally handled a live event, changed state as expected, and cleaned up without ghost surfaces.

**Architecture:** Intercore owns enforcement. A versioned `pkg/runtimeproof` contract performs strict validation, and the terminal phase gate injects a hard `runtime_evidence` check whenever run metadata requires `runtime-evidence/v1`. Clavain owns activation and evidence collection: new labeled runs receive the requirement atomically at creation; already-in-progress work without a run requires an explicit audited adoption command that creates a `reflect,done` run with imported plan/source provenance rather than fabricating earlier lifecycle artifacts. The collector launches the installed executable itself with fresh nonce/event IDs, computes build/installed/runtime digests, compares tracked expectations with probe observations, writes host-local evidence outside the worktree, and registers it as a typed run artifact. The close wrapper reuses the verifier before consuming authorization and persists a sanitized proof summary in Beads for historical/cross-host reconciliation. `/reflect` records reflection only; the sprint lands, collects proof, then performs the terminal advance and gated close.

**V1 boundary:** File artifacts and local-host receipts only. Collector-verifiable loopback ports and private filesystem paths are the only accepted resource kinds. External databases, environment state, migrations, remote/shared endpoints, and every unknown resource kind fail as `UNVERIFIABLE`; provisioning them is deferred. Interhelm contributes health/smoke vocabulary but is not a runtime dependency. V1 does not infer whether a change needs runtime proof, sign cross-host receipts, retrofit historical beads, or build a general gate plugin registry.

## Prior Learnings

- `sylveste-5qv9` passed source tests while its CXDB binary was never installed; the live blob path silently returned an empty hash for weeks. Green source tests are not runtime evidence.
- The current `reflect -> done` rule accepts any reflection artifact, and `/reflect` advances before landing. The terminal transition must move after landing and proof.
- A shell wrapper alone is bypassable. The hard decision belongs in Intercore, while Clavain supplies operator workflow and a pre-token close check.
- `UNVERIFIABLE` is failure, not success. Missing, stale, skipped, degraded, uncorrelated, shared, or unverifiable evidence must fail closed.
- Documentation-only work must not inherit a runtime gate. Applicability is explicit through `close-gate:runtime-evidence` and durable run metadata.
- `bd orphans` checks commit references to open beads; it does not detect missing tracker records for plans/PRDs or completed runs with open beads. Reconciliation needs explicit directions and names.

## Receipt Contract

Intercore and Clavain share `runtime-evidence/v1`. Unknown fields are rejected so a misspelled required field cannot look valid.

```json
{
  "schema_version": 1,
  "subject": {
    "bead_id": "sylveste-6h7x",
    "run_id": "run-id",
    "project_root": "/absolute/project/root",
    "git_head": "40-hex-sha",
    "host": "hostname",
    "created_at": "RFC3339"
  },
  "artifact": {
    "kind": "file",
    "build_path": "/absolute/build/path",
    "installed_path": "/absolute/install/path",
    "build_digest": "sha256:...",
    "installed_digest": "sha256:...",
    "runtime_digest": "sha256:..."
  },
  "boot": {
    "started_for_probe": true,
    "process_id": 123,
    "instance_nonce": "collector-generated",
    "observed_nonce": "same-value",
    "state": "VERIFIED"
  },
  "health": {
    "required_subsystems": ["store"],
    "observed": {"store": "healthy"},
    "failure_classes": {
      "startup": "VERIFIED",
      "dependency_injection": "NOT_APPLICABLE",
      "connection": "VERIFIED",
      "projection_catchup": "NOT_APPLICABLE"
    }
  },
  "event": {
    "event_id": "collector-generated",
    "observed_event_id": "same-value",
    "before_digest": "sha256:...",
    "after_digest": "sha256:...",
    "assertions": [
      {"name": "state-delta", "state": "VERIFIED", "evidence": "..."}
    ]
  },
  "surface_scan": {
    "expected": ["named-surface"],
    "observed": ["named-surface"],
    "missing": [],
    "unexpected": []
  },
  "isolation": {
    "resources": [
      {"kind": "port", "fingerprint": "sha256:redacted-resource-id", "ownership": "ephemeral"}
    ],
    "collisions": []
  },
  "cleanup": {"owned_resources_remaining": []}
}
```

Close-time validation requires: exact bead/run/root/current HEAD/current host; receipt time after run creation and no older than 24 hours; matching artifact-row content hash; absolute readable build/install regular files; build, installed, and runtime digests equal; fresh boot nonce and positive collector-started process ID; every required subsystem healthy; all four failure classes explicit and never failed/unverifiable; matching event IDs; different before/after digests; at least one assertion and all assertions `VERIFIED`; exact expected/observed surfaces with no missing/unexpected values; at least one collector-owned exclusive/ephemeral resource and no collisions; and no owned resources remaining after cleanup. Failure-class result values are the exact enums `VERIFIED`, `FAILED_VERIFICATION`, `UNVERIFIABLE`, and `NOT_APPLICABLE`; `NOT_APPLICABLE` is accepted only when the tracked config declared that class inapplicable.

Receipt/artifact reads are bounded and single-pass: reject symlinks, devices, FIFOs, sockets, non-regular files, receipts over 256 KiB, and executables over the configured 512 MiB ceiling. The exact receipt bytes that are hashed are the bytes decoded. Git resolution has a two-second timeout. Collector stdout/stderr are capped, child/probe environments are allowlisted, commands never use a shell, and timeout/error paths kill the full process group. Resource identifiers and environment values are never persisted; receipts store only SHA-256 resource fingerprints.

The tracked schema-v1 collector config owns the assertions: build path, platform-keyed installed paths, argv-array start command, argv-array probe command, timeouts, required subsystem names, failure-class applicability, required assertion names, expected surfaces, and required isolated resource kinds/ownership. Build/probe paths are project-relative; installed paths use explicit `darwin-arm64`/`linux-amd64` overrides. Only the documented `{project_root}` and `{installed_path}` tokens expand, then every path is canonicalized and revalidated; arbitrary environment interpolation and committed host-absolute build paths are forbidden. The canary may generate an untracked private config containing temporary absolute paths. The start command's executable must resolve to `installed_path`; Clavain launches it directly without a shell, records start time/PID, verifies it remains alive through the probe, and derives `runtime_digest` from the installed file. The child creates a fresh endpoint-discovery file after collector start; only loopback endpoints and collector-started loopback-port/private-path resources are accepted. A probe pointed at a pre-existing/shared endpoint cannot echo the fresh child nonce and fails. Database, environment, migration, remote endpoint, shared, or unknown resource observations fail closed even if the probe calls them isolated.

The probe command receives only an allowlisted base environment plus `CLAVAIN_RUNTIME_BEAD_ID`, `CLAVAIN_RUNTIME_RUN_ID`, `CLAVAIN_RUNTIME_GIT_HEAD`, `CLAVAIN_RUNTIME_INSTANCE_NONCE`, `CLAVAIN_RUNTIME_EVENT_ID`, `CLAVAIN_RUNTIME_PROCESS_ID`, and an endpoint-discovery file path. It returns observations only: observed nonce, subsystem states, failure-class results/evidence, observed event ID, before/after digests, named assertion results/evidence, observed surfaces, observed isolated resources, and collisions. It cannot choose required checks, expected surfaces, ownership, subject identity, or artifact digests. After probing, Clavain stops the process and independently confirms the process group plus declared loopback port/path resources are gone before recording cleanup success.

Receipts live under `${XDG_STATE_HOME:-~/.local/state}/clavain/runtime-evidence/<project-hash>/` with directory mode `0700` and file mode `0600`; they are never written under the repository. At close, Clavain persists only proof hash, source HEAD, run ID, verification timestamp, schema, and a host fingerprint in Beads state. Freshness and local paths apply only to close-time validation. The recurring audit validates local files only for active runs owned by the current host; for closed beads it validates the durable summary's shape/correlation and never treats an expired or remote host-local receipt as an orphan.

---

### Task 1: Add the strict shared receipt contract

**Repository:** `core/intercore`

**Files:**
- Create: `pkg/runtimeproof/runtimeproof.go`
- Create: `pkg/runtimeproof/runtimeproof_test.go`

1. Write table-driven failing tests for valid evidence and every fail-closed class: unknown/missing fields, wrong identity, stale/pre-run time, host mismatch, digest mismatch, failed/unverifiable health, nonce/process chronology mismatch, event mismatch, no state delta, empty/failed assertions, surface drift, shared/unknown resources, collisions, and incomplete cleanup.
2. Add adversarial file tests for symlink/FIFO/device/non-regular paths, oversized receipt/executable, mutation between hash and decode, and bounded Git timeout.
3. Implement strict single-pass JSON decoding, bounded SHA-256 file hashing, current Git HEAD/hostname resolution, sanitized proof summaries, and deterministic validation errors.
4. Keep filesystem, command, clock, and host inputs injectable in tests; production defaults use bounded local filesystem access, `git -C <root> rev-parse HEAD`, and `os.Hostname`.
5. Run `go test ./pkg/runtimeproof` and commit the Intercore unit.

### Task 2: Enforce the receipt in the Intercore kernel

**Repository:** `core/intercore`

**Files:**
- Modify: `internal/runtrack/store.go`
- Modify: `internal/runtrack/store_test.go`
- Modify: `internal/phase/gate.go`
- Modify: `internal/phase/gate_test.go`
- Modify: `internal/phase/tx_queriers.go`
- Modify: `internal/phase/machine_test.go`
- Modify: `internal/phase/store.go`
- Modify: `internal/phase/store_test.go`
- Modify: `cmd/ic/run_create.go`
- Modify: `cmd/ic/run_config.go`
- Modify/add tests under: `cmd/ic/`

1. Add failing store tests for `LatestActiveArtifactByType`, ordered by `created_at DESC, rowid DESC`, excluding rolled-back rows, and deterministic across same-second registrations. The gate validates the single newest active receipt and must not fall back to an older valid receipt when the newest is invalid.
2. Add failing gate tests proving an ordinary run retains the existing reflection rule, while metadata requirement `runtime-evidence/v1` injects a hard check that blocks missing/invalid evidence and accepts only a valid current receipt.
3. Add failing CLI/store tests for validated `--metadata=<object>` at create and transactional recursive-object `--metadata-merge=<object>` at set. Reject malformed/non-object JSON without changing the run. Once `runtime-evidence/v1` is present, make `close_gate.requirements` monotonic, `close_gate.bead_id` immutable, and `close_gate.adoption` immutable; reject removal, replacement, bead changes, and concurrent lost updates. Prove a required run is gated from its first observable state.
4. Implement the typed artifact lookup and `runtime_evidence` gate check. Injection is independent of per-run/spec/default rule selection and occurs only on a transition to `done` when metadata contains `close_gate.requirements: ["runtime-evidence/v1"]` plus `close_gate.bead_id`. This invariant is non-bypassable in V1: `--disable-gates`, priority-based disablement, skip reasons, and `ic gate override` must reject the required terminal transition with a structured audited reason rather than advance it.
5. Validate the artifact row hash and the receipt through `pkg/runtimeproof` inside the same phase-advance transaction. Any read, parse, identity, freshness, or validation error becomes structured gate failure evidence, not a process crash or fail-open warning.
6. Implement create/set metadata support with atomic store updates and audit events.
7. Run targeted tests, then `go test ./...` and `go vet ./...`; commit and push Intercore before updating Clavain's dependency.

### Task 3: Bind, collect, register, and verify evidence in Clavain

**Repository:** `os/Clavain`

**Files:**
- Modify: `cmd/clavain-cli/go.mod`
- Modify: `cmd/clavain-cli/go.sum` if required
- Create: `cmd/clavain-cli/runtime_evidence.go`
- Create: `cmd/clavain-cli/runtime_evidence_test.go`
- Modify: `cmd/clavain-cli/main.go`
- Modify: `cmd/clavain-cli/init.go`
- Modify: `cmd/clavain-cli/phase.go`
- Create: `cmd/clavain-cli/testdata/runtimefixture/main.go`
- Create: `cmd/clavain-cli/testdata/runtimeprobe/main.go`
- Create: `cmd/clavain-cli/testdata/runtime-evidence-canary.json`

1. Add failing tests for `runtime-evidence required`, `bind`, `adopt`, `collect`, and `verify`; label detection; label removal after binding; idempotent adoption; missing/malformed imported provenance; atomic metadata on new-run creation; collector-created nonce/event IDs; wrong start executable; premature child exit; stale endpoint file; pre-existing/shared endpoint; database/environment/migration/remote/unknown resource refusal; spoofed expectations/digests/ownership; command timeout/nonzero/malformed/oversized output; process-group cleanup; build/install mismatch; strict probe rejection; private atomic receipt write outside the worktree; typed artifact registration; durable summary generation; and stale/tampered verification.
2. Add the `runtime-evidence` command group:
   - `required <bead>` returns required when the label is present, the resolved run has sealed runtime-evidence metadata, or Beads contains the monotonic required-state marker. Managed close/sweep paths call this command rather than relying on the current label alone.
   - `bind <bead>` requires `close-gate:runtime-evidence` for first activation and an existing run, then atomically seals the durable requirement/bead ID and writes `runtime_evidence_required=1` to Beads state. Once bound, later label removal does not affect verification or closure. Normal new-sprint creation passes the same metadata in the initial `ic run create` call so there is no ungated window. If no run exists, `bind` fails with the explicit adoption command.
   - `adopt <bead> --project=<root> --provenance=<json>` is the only no-run attach path. It validates imported plan path/digest and source repository HEADs, creates a custom `reflect,done` run atomically with `close_gate.adoption` metadata, and persists `ic_run_id` plus phase. It cannot be selected implicitly by `sprint-init` or `sprint-advance`, and retries never create a second run.
   - `collect <bead> --config=<path>` first binds, loads schema-v1 config (build/install paths, start/probe argv, expectations, timeout), verifies build/install identity, launches `installed_path` itself with fresh identifiers and a new endpoint-discovery file, compares probe observations to config-owned expectations, stops the process group, verifies declared resources are gone, creates and validates the full receipt, atomically writes it under private host state, and registers type `runtime-evidence/v1` in Intercore and Beads.
   - `verify <bead>` uses durable requirement state rather than requiring the current label, requires the bound run, locates the newest typed artifact, rehashes and fully validates it against current state, and prints a compact JSON result with proof hash.
3. Add `runtime-evidence/v1` to known artifact types. Registration failures are fatal for this type rather than best-effort warnings.
4. Make new sprint creation inspect the explicit label/option and pass requirement metadata atomically. `sprint-init` and `sprint-advance` verify that labeled runs are already bound; they never adopt implicitly and must fail with an actionable command on missing/conflicting/malformed references.
5. Implement the HTTP fixture and probe under `testdata`: the fixture writes a fresh loopback endpoint file, reports the launch nonce and subsystem state, applies a unique event to isolated state, and exposes before/after digests; the probe returns observations only.
6. Run `go test ./...` from `cmd/clavain-cli`; commit the Clavain collector unit.

### Task 4: Put terminal transition and managed closes behind the gate

**Repository:** `os/Clavain`

**Files:**
- Modify: `commands/reflect.md`
- Modify: `commands/sprint.md`
- Modify: `commands/bead-sweep.md`
- Modify: `commands/campaign.md`
- Modify: `commands/clavain-doctor.md`
- Modify: `scripts/gates/bead-close.sh`
- Modify: `scripts/bead-close-shipped.sh`
- Modify: `scripts/bead-land.sh`
- Modify: `hooks/lib-sprint.sh`
- Modify: `skills/landing-a-change/SKILL.md`
- Modify: `skills/landing-a-change/SKILL-compact.md`
- Modify: `skills/ship/SKILL.md`
- Modify: `cmd/clavain-cli/children.go`
- Add/modify tests under: `tests/`, `scripts/gates/`, and `cmd/clavain-cli/`

1. Add failing structural and behavior tests proving `/reflect` cannot advance to `done`, a labeled close verifies before one-shot authorization consumption, invalid proof leaves the bead open, and sprint/campaign/sweep/child/doctor automation cannot raw-close a runtime-gated bead. The structural invariant covers executable Go, shell/hooks, and Clavain command/skill instructions. Its precise allowlist is: the canonical wrapper implementation; tests/fixtures; historical `docs/`; descriptive `README.md`, `scripts/gates/README.md`, `agent-rig.json`, and `hooks/lib-signals.sh`; and the generic project-onboard `AGENTS.md` template, which must work without Clavain installed. All managed close instructions and executable close sites must invoke the wrapper or skip gated beads.
2. Change `/reflect` to record/register reflection only.
3. In sprint Step 10: land and push, run the configured installed-runtime collector for labeled beads, call terminal `sprint-advance ... reflect`, then close through the canonical gate wrapper.
4. In `bead-close.sh`, call `runtime-evidence required`; when true, run `runtime-evidence verify` before token consumption and require the associated Intercore run to be completed. Record the sanitized proof summary (schema, proof hash, run ID, HEAD, timestamp, host fingerprint) in Beads state before close. Current label absence never downgrades a sealed run or required-state marker.
5. Route interactive managed-close documentation/scripts through `bead-close.sh`. Automated sweep/child paths must either call the wrapper with a valid context or explicitly skip runtime-gated beads and report why; they may not downgrade the requirement.
6. Run the focused shell/Bats suites and `go test ./...`; commit the workflow unit.

### Task 5: Add read-only orphan and ghost reconciliation

**Repository:** `os/Clavain`

**Files:**
- Create: `scripts/runtime-evidence-audit.sh`
- Create: `tests/test_runtime_evidence_audit.bats`
- Modify: `hooks/session-start.sh`
- Modify: `commands/clavain-doctor.md`

1. Add failing fixtures for each runtime-gated direction: labeled active bead with missing/conflicting run, completed run with open bead, local active run with missing/invalid receipt, closed gated bead with missing/malformed durable proof summary, and valid local/remote historical summaries.
2. Implement a read-only JSON audit limited to `close-gate:runtime-evidence` beads, run/artifact state, and durable summaries. It validates host-local receipt freshness only for current-host active runs and never treats remote/expired closed evidence as missing. It never closes, edits, or synthesizes tracker data.
3. Add a six-hour, lock-protected SessionStart invocation that is quiet on clean/unsupported repositories and emits only actionable findings. Add an explicit full audit to doctor.
4. Defer global plan/PRD-to-tracker reconstruction to `sylveste-xogc`; do not turn known historical inventory into SessionStart noise.
5. Run the audit Bats suite plus existing SessionStart/doctor tests; commit the reconciliation unit.

### Task 6: Verify source, publish, and deploy

**Repositories:** `core/intercore`, `os/Clavain`, root `Sylveste`

1. Add `scripts/runtime-evidence-canary.sh` plus tests. It compiles the fixture and probe from `cmd/clavain-cli/testdata`, copies the fixture from a build path to a distinct temporary install path, writes a temporary collector config, and exercises source-built `ic`/Clavain in an isolated temporary project before release.
2. Run full Intercore and Clavain quality gates, the source integration canary, plugin validation, installer doctors, and root tracker audits.
3. Under exclusive repository ownership, bump and publish Intercore and Clavain through their existing release paths, including all generated version manifests, PRD/version references, release binaries/checksums, and marketplace metadata those tools mutate. Deploy both hosts and verify installed versions plus source/install parity. No completion claim or final receipt is made from the pre-release canary.

### Task 7: Run exact-release canaries and close

**Repositories:** `core/intercore`, `os/Clavain`, root `Sylveste`

**Files:**
- Create: `docs/evidence/2026-07-10-runtime-evidence-close-gate.md`
- Modify: `docs/sylveste-roadmap.md`
- Regenerate: `docs/roadmap.json`
- Regenerate: `docs/backlog.md`

1. Against the exact installed release on Clavain, retain three outcomes:
   - Missing receipt: `ic run advance` blocks `reflect -> done` with `runtime_evidence` in structured gate evidence and the close wrapper refuses before token consumption.
   - Shared/unverifiable runtime: a probe aimed at a pre-existing fixture endpoint fails nonce/child/resource ownership checks, and separate database/environment/migration resource observations fail as `UNVERIFIABLE`; none can emit a receipt.
   - Valid receipt: the collector-launched installed fixture registers a receipt, the terminal advance succeeds, close verification succeeds, cleanup is independently observed, and the audit is clean.
2. Repeat all three outcomes on zklw using its exact installed binaries and host-local receipts. Record installed versions/digests, source HEADs, proof hashes, and gate event IDs in the evidence document. The evidence document lives in root Sylveste, while the gated run uses the Clavain project root, so recording evidence cannot invalidate the receipt HEAD.
3. Add `close-gate:runtime-evidence` to `sylveste-6h7x`; explicitly adopt it into a `reflect,done` run rooted at the Clavain repository with the committed implementation plan digest plus exact Intercore/Clavain source HEADs as imported provenance. Register a genuine reflection, collect the final exact-release receipt, perform the terminal gate path, and close through the wrapper. Do not synthesize brainstorm/plan/review/verdict artifacts for work that predated its run.
4. Confirm the delivered contract satisfies `Sylveste-4b5.2` (boot, health, named failure classes, state delta) and `Sylveste-4b5.11` (shared-runtime refusal). Close them if their acceptance criteria are fully observed; otherwise update them with the precise remaining gap. Record that Interhelm vocabulary was copied into a self-contained contract, not linked as a runtime dependency.
5. Under exclusive root-tracker ownership, persist the sanitized proof summary, flush canonical Dolt state to `.beads/issues.jsonl`, regenerate the roadmap/backlog, update the curated roadmap, run root audits, and push canonical Dolt plus Git state.

## Completion Evidence

- A stored hard gate event from an installed binary for the missing-receipt failure.
- A stored successful terminal event bound to a valid `runtime-evidence/v1` receipt.
- Receipt proof hashes from both Clavain and zklw.
- A stored shared-runtime refusal from each host.
- Installed/source version and digest parity on both hosts.
- `runtime-evidence-audit.sh --json` clean for `sylveste-6h7x`.
- Intercore `go test ./...` and `go vet ./...` green.
- Clavain Go, shell/Bats, structural CI, plugin validation, and installer doctors green.
- Root roadmap audit green, canonical tracker pushed, and all three repositories up to date with origin.
