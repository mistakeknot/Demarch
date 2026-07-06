# fc5 Phase 3 — thread plan acceptance criteria to validators (Sylveste-fc5.3)

Execution-grade plan. Author: fable. Repo: `os/Clavain` only. Do NOT run git commands; leave changes in the working tree.

**Context (verified review findings):** set-artifact is last-write-wins with no seal (f-034; `store.go:202` and `phase.go:341` confirmed); per-criterion results have no durable write (f-035); CXDB already computes a BLAKE3 BlobHash at set-artifact that nothing reads back (f-042) — reuse content-hash sealing rather than inventing new custody; validators today score their own findings, never the plan's criteria (doctrine Rule 3, `model-routing.md:93`). quality-gates already aggregates every `.clavain/verdicts/*.json` file, so a plan-conformance verdict written in that format integrates with zero changes to the aggregation.

**Design invariants:**
- Criteria format is machine-checkable-first: numbered items; each item MAY carry a fenced `check:` shell command whose exit code decides it; items without a command are judged by the validator against stated evidence.
- The criteria artifact is **sealed by content hash sidecar** (`<path>.seal` holding the SHA-256 hex of the file). The seal is self-contained (no bd/ic dependency), checked at set-time (write-once) and at validation-time (tamper detection). `CLAVAIN_RESEAL=1` is the explicit re-seal override.
- Per-criterion results persist as a `criteria-results` artifact (f-035) so Phase 4 has a source of record.

## Step 1 — artifact types: `os/Clavain/cmd/clavain-cli/phase.go`

In `knownArtifactTypes` (line ~322) add two entries:
```go
	"acceptance-criteria": true,
	"criteria-results":    true,
```

## Step 2 — write-once seal in `cmdSetArtifact` (same file, function at ~341)

Immediately after the `if !knownArtifactTypes[artifactType]` warning block and BEFORE the bd-state write, insert:

```go
	// Write-once seal for acceptance criteria (fc5.3, f-034): the standard a
	// validator judges against must not be rewritable after execution starts —
	// especially by an escalation-triggered re-plan that has seen why the
	// first attempt failed. Seal = content-hash sidecar; independent of bd/ic.
	if artifactType == "acceptance-criteria" {
		if err := sealArtifact(artifactPath); err != nil {
			return err
		}
	}
```

Add these functions at the end of phase.go:

```go
// sealArtifact enforces write-once semantics via a content-hash sidecar.
// First call writes <path>.seal; later calls verify the hash and refuse a
// changed file unless CLAVAIN_RESEAL=1.
func sealArtifact(path string) error {
	data, err := os.ReadFile(path)
	if err != nil {
		return fmt.Errorf("seal: cannot read %s: %w", path, err)
	}
	sum := sha256.Sum256(data)
	hexSum := hex.EncodeToString(sum[:])
	sealPath := path + ".seal"

	existing, rerr := os.ReadFile(sealPath)
	if rerr == nil {
		if strings.TrimSpace(string(existing)) == hexSum {
			return nil // unchanged content — idempotent re-register is fine
		}
		if os.Getenv("CLAVAIN_RESEAL") != "1" {
			return fmt.Errorf("acceptance-criteria is sealed (write-once); content changed since seal.\nSet CLAVAIN_RESEAL=1 to re-seal deliberately (this is an audit event)")
		}
		fmt.Fprintf(os.Stderr, "set-artifact: RESEAL of acceptance-criteria %s (old %.12s → new %.12s)\n", path, strings.TrimSpace(string(existing)), hexSum)
	}
	return os.WriteFile(sealPath, []byte(hexSum+"\n"), 0o644)
}

// verifySeal reports whether path's content still matches its seal sidecar.
func verifySeal(path string) error {
	sealPath := path + ".seal"
	want, err := os.ReadFile(sealPath)
	if err != nil {
		return fmt.Errorf("no seal found at %s", sealPath)
	}
	data, err := os.ReadFile(path)
	if err != nil {
		return fmt.Errorf("cannot read sealed file: %w", err)
	}
	sum := sha256.Sum256(data)
	if hex.EncodeToString(sum[:]) != strings.TrimSpace(string(want)) {
		return fmt.Errorf("SEAL MISMATCH: %s was modified after sealing", path)
	}
	return nil
}
```

Add imports `crypto/sha256` and `encoding/hex` (check `os`, `strings`, `fmt` are already imported — they are, per existing code).

Add a CLI verb so bash can check seals: find where clavain-cli subcommands are dispatched (main.go) and register `verify-seal` → 
```go
func cmdVerifySeal(args []string) error {
	if len(args) < 1 {
		return fmt.Errorf("usage: verify-seal <path>")
	}
	if err := verifySeal(args[0]); err != nil {
		return err
	}
	fmt.Println("seal ok")
	return nil
}
```

Build: `cd /Users/sma/projects/Sylveste/os/Clavain && go build ./...` (module root may be the repo root or cmd/clavain-cli — check for go.mod location and run from there). Also run any existing tests: `go test ./cmd/clavain-cli/ 2>/dev/null || true` (pass if no tests exist).

## Step 3 — criteria emission in `os/Clavain/commands/write-plan.md`

After the existing "After the plan is saved" block (lines ~26-31), append this section:

~~~markdown
**Then extract and seal the acceptance criteria** (fc5.3 — the validator's rubric):

The plan MUST contain a `## Acceptance Criteria` section: numbered items, each stating one observable, checkable outcome. Prefer machine-checkable items — append a fenced block to an item to make it executable:

```
1. All routing tests pass.
   ```check
   cd core/intercore && go test ./internal/routing/
   ```
```

Extract that section verbatim to `<plan_path minus .md>.criteria.md`, then register and seal it:

```bash
criteria_path="${plan_path%.md}.criteria.md"
awk '/^## Acceptance Criteria/{f=1} f && /^## /&& !/^## Acceptance Criteria/{f=0} f' "$plan_path" > "$criteria_path"
if [[ -s "$criteria_path" ]]; then
  clavain-cli set-artifact "$BEAD_ID" "acceptance-criteria" "$criteria_path"
  bd set-state "$BEAD_ID" "plan_author_model=${CLAUDE_MODEL:-${ANTHROPIC_MODEL:-unknown}}" 2>/dev/null || true
else
  echo "WARNING: plan has no '## Acceptance Criteria' section — validator will have no rubric (doctrine Rule 3)" >&2
fi
```

The seal (`.seal` sidecar) makes the criteria write-once: an escalation-triggered re-plan cannot silently rewrite the standard after seeing why execution failed. Re-sealing requires explicit `CLAVAIN_RESEAL=1`.
~~~

## Step 4 — plan-conformance validation in `os/Clavain/commands/quality-gates.md`

Insert a new phase section between the flux-drive dispatch (Phase 2) and the verdict-reading Phase 3, titled `## Phase 2b: Plan Conformance (acceptance criteria)`:

~~~markdown
## Phase 2b: Plan Conformance (acceptance criteria)

If the bead has a sealed acceptance-criteria artifact, validate execution against it — the validator judges ONLY the named criteria, never its own preferences (capability-routing doctrine Rule 3).

```bash
criteria_path=$(clavain-cli get-artifact "$CLAVAIN_BEAD_ID" "acceptance-criteria" 2>/dev/null) || criteria_path=""
if [[ -n "$criteria_path" && -f "$criteria_path" ]]; then
  # Tamper check first (fc5.3): a criteria file modified after sealing FAILS the gate outright.
  if ! clavain-cli verify-seal "$criteria_path"; then
    echo "GATE FAIL: acceptance-criteria seal mismatch — criteria were modified after sealing" >&2
    # write a FAILED plan-conformance verdict and skip the validator dispatch
  fi
fi
```

When the seal is intact, dispatch ONE validator subagent (Task tool, model **opus** — the validator tier; do not downgrade) with this prompt, substituting the criteria file content:

> You are a plan-conformance validator. Judge the working tree ONLY against these acceptance criteria — no other opinions, no scope expansion. For each numbered criterion: if it carries a fenced `check` block, run that command and let its exit code decide; otherwise verify the stated outcome directly (read files, run greps). Return a markdown table: `criterion | pass/fail | evidence (one line)`, then a final line `CONFORMANCE: PASS` (all pass) or `CONFORMANCE: FAIL` (any fail).

Persist the results (f-035 — Phase 4's source of record) and the verdict:

```bash
results_path="${criteria_path%.criteria.md}.criteria-results.md"
# (write the validator's table + CONFORMANCE line to $results_path)
clavain-cli set-artifact "$CLAVAIN_BEAD_ID" "criteria-results" "$results_path" 2>/dev/null || true

conf_status="CLEAN"; conf_findings=0
grep -q 'CONFORMANCE: FAIL' "$results_path" && { conf_status="NEEDS_ATTENTION"; conf_findings=$(grep -c '| *fail' "$results_path" || echo 1); }
mkdir -p .clavain/verdicts
jq -n --arg s "$conf_status" --argjson f "$conf_findings" --arg d "$results_path" \
  '{type:"plan-conformance", status:$s, model:"opus", tokens_spent:0, files_changed:0, findings_count:$f, summary:("plan conformance: " + $s), detail_path:$d, timestamp:(now|todate), session_id:(env.CLAUDE_SESSION_ID // "unknown")}' \
  > .clavain/verdicts/plan-conformance.json
```

A `NEEDS_ATTENTION` plan-conformance verdict fails the gate exactly like any other agent verdict (Phase 3 already aggregates `.clavain/verdicts/*.json`). If no acceptance-criteria artifact exists, skip this phase silently (pre-fc5.3 beads).
~~~

## Step 5 — smoke test script: `os/Clavain/tests/routing/criteria-seal-test.sh` (new)

```sh
#!/usr/bin/env bash
# fc5.3 acceptance: write-once seal + tamper detection via clavain-cli.
set -euo pipefail
CLI="${CLAVAIN_CLI:-$(cd "$(dirname "$0")/../.." && pwd)/bin/clavain-cli}"
command -v "$CLI" >/dev/null || CLI="clavain-cli"
tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT
f="$tmp/plan.criteria.md"
echo "1. thing holds" > "$f"

# Build a throwaway binary if bin/ is stale: prefer `go run`.
run_cli() { (cd "$(dirname "$0")/../.." && go run ./cmd/clavain-cli "$@"); }

run_cli set-artifact test-bead-fc53 acceptance-criteria "$f" || { echo "FAIL: first seal errored"; exit 1; }
[[ -f "$f.seal" ]] || { echo "FAIL: no seal sidecar"; exit 1; }
run_cli verify-seal "$f" || { echo "FAIL: fresh seal does not verify"; exit 1; }

echo "2. sneaky edit" >> "$f"
if run_cli set-artifact test-bead-fc53 acceptance-criteria "$f" 2>/dev/null; then
  echo "FAIL: re-register after edit should refuse"; exit 1
fi
run_cli verify-seal "$f" 2>/dev/null && { echo "FAIL: tamper not detected"; exit 1; }
CLAVAIN_RESEAL=1 run_cli set-artifact test-bead-fc53 acceptance-criteria "$f" || { echo "FAIL: explicit reseal refused"; exit 1; }
run_cli verify-seal "$f" || { echo "FAIL: reseal does not verify"; exit 1; }
echo "PASS: criteria seal suite"
```
`chmod +x` it. Note: `set-artifact` will print bd/ic warnings for the fake bead — that's fine; only the seal behavior (exit codes) is under test. If `go run ./cmd/clavain-cli` is not how this module runs (check go.mod location), adapt `run_cli` to the real build path — the plan's intent is: exercise the REAL binary's seal logic, not a copy.

## Acceptance Criteria (validator: mechanical, pass/fail)

1. **build**: clavain-cli builds — from the go.mod directory: `go build ./...` exits 0.
2. **artifact-types**: `grep -n '"acceptance-criteria": *true' os/Clavain/cmd/clavain-cli/phase.go` and `grep -n '"criteria-results": *true'` both hit.
3. **seal-functions**: `grep -n 'func sealArtifact' os/Clavain/cmd/clavain-cli/phase.go` and `grep -n 'func verifySeal'` hit; `grep -n 'CLAVAIN_RESEAL'` hits inside sealArtifact.
4. **cli-verb**: `grep -rn 'verify-seal' os/Clavain/cmd/clavain-cli/main.go` (or wherever subcommands dispatch) shows the registered verb.
5. **seal-suite**: `bash os/Clavain/tests/routing/criteria-seal-test.sh` prints `PASS: criteria seal suite` and exits 0.
6. **write-plan-threading**: `grep -n 'Acceptance Criteria' os/Clavain/commands/write-plan.md` shows the extraction section; `grep -n 'acceptance-criteria' os/Clavain/commands/write-plan.md` shows the set-artifact call; `grep -n 'plan_author_model' os/Clavain/commands/write-plan.md` hits (Phase 4 dependency).
7. **quality-gates-conformance**: `grep -n 'Phase 2b' os/Clavain/commands/quality-gates.md` hits; `grep -n 'plan-conformance' os/Clavain/commands/quality-gates.md` shows the verdict write to `.clavain/verdicts/plan-conformance.json`; `grep -n 'verify-seal' os/Clavain/commands/quality-gates.md` shows the tamper check runs BEFORE the validator dispatch.
8. **validator-tier**: the Phase 2b text pins the validator dispatch to model opus (grep `model **opus**` or equivalent) — doctrine Rule 3 tiering.
9. **no-commits**: `git -C /Users/sma/projects/Sylveste/os/Clavain log --oneline -1` unchanged from before execution.
