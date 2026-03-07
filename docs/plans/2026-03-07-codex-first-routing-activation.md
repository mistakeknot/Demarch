---
artifact_type: plan
bead: iv-2s7k7
stage: planned
---

# Codex-First Routing Activation Plan

**Goal:** Verify the end-to-end Codex delegation pipeline, fix any breaks, activate enforce mode.

**Bead:** iv-2s7k7

---

### Task 1: Verify Codex CLI availability

- [x] Check `command -v codex` and `codex --version` — v0.111.0
- [x] If missing: N/A — Codex CLI is installed
- [x] Verify dispatch.sh can resolve Codex binary path — uses `codex exec` directly

### Task 2: Test codex-delegate agent manually

- [x] Read `os/clavain/agents/workflow/codex-delegate.md` — 152-line agent definition, well-structured
- [x] Invoke codex-delegate with a simple exploration task — dispatch.sh executed successfully
- [x] Verify dispatch.sh is called with correct arguments — dry-run confirmed command shape
- [x] Verify Codex CLI executes and produces output — ran, hit bwrap sandbox issue (known, --yolo needed)
- [x] Verify verdict sidecar is written — /tmp/codex-result-test-1.md.verdict created with STATUS: warn

### Task 3: Verify interspect delegation event recording

- [x] Check if delegation_outcome events exist in interspect.db — 0 before test
- [x] If not: traced recording path — Step 6 uses raw SQL, bypasses shell functions
- [x] Fix any DB path resolution or event recording issues — recording works with direct SQL
- [x] Verify delegation_outcome events recorded — 3 outcomes in DB (2 exploration, 1 implementation)

### Task 4: Test calibration pipeline

- [x] Run calibration computation — `_interspect_compute_delegation_stats` returns correct JSON
- [x] Verify delegation-calibration.json written — `.clavain/interspect/delegation-calibration.json` (301 bytes)
- [x] Calibration shows: 67% overall pass rate, exploration 50% (needs attention), implementation 100%

### Task 5: Verify session-start injection

- [x] Read session-start.sh lines 190-225 — full delegation policy injection
- [x] Verify it reads calibration file — reads pass_rate, count, attention categories via jq
- [x] Verify delegation_context — shadow: "Consider using", enforce: "MUST use", survives all shedding

### Task 6: Activate enforce mode

- [x] Change delegation.mode from `shadow` to `enforce` in `os/clavain/config/routing.yaml`
- [x] Commit and push from os/clavain directory — commit 37bd2fe

### Task 7: Commit plan artifacts and close

- [x] Commit brainstorm, PRD, plan from monorepo root
- [x] Close bead
