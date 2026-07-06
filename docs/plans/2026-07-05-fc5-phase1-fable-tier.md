# fc5 Phase 1 — fable tier + capability-routing agency spec (Sylveste-fc5.1)

Execution-grade plan. Author: fable (main loop). Executor: follow steps in order, exactly. Two independent git repos are touched — `os/Clavain` and `core/intercore` — do NOT run any git commands in either; leave all changes in the working tree.

**Design invariants (do not deviate):**
- `fable` is tier **4**, strictly above opus (3). Safety floors then never clamp it (floor comparison is `model_tier >= floor_tier`).
- **Window fallback, fail-closed:** whenever a resolver would return `fable` but the fable window is not open (`CLAVAIN_FABLE_AVAILABLE != "1"`), it returns `opus` instead. Unset/empty env means CLOSED. This makes every `fable` config value a strict, zero-regression upgrade of positions that resolve `opus` today.
- Fable appears in config ONLY where the current value is `opus` on planning/review-flavored positions. Never replace a `sonnet`/`haiku` value.
- Out of scope (already tracked elsewhere): routing_decisions provenance field for fallback (rides fc5.4 attribution work), agency-spec staleness/reload (f-014), agent-frontmatter routing (f-041).

## Step 1 — Go tier vocabulary: `core/intercore/internal/routing/routing.go`

In the `const` block add (after `TierOpus ModelTier = 3`):
```go
	TierFable   ModelTier = 4
```
In `ParseModelTier`, add before `default:`:
```go
	case "fable":
		return TierFable
```
In `String()`, add before `default:`:
```go
	case TierFable:
		return "fable"
```

## Step 2 — Go window fallback: `core/intercore/internal/routing/resolve.go`

Add at the end of the import block (if `os` is not already imported): `"os"`.

Add this helper near `applyFloor` (package-level function):
```go
// fableWindowOpen reports whether the frontier (fable) window is open.
// Fail-closed: only an explicit CLAVAIN_FABLE_AVAILABLE=1 opens it.
func fableWindowOpen() bool {
	return os.Getenv("CLAVAIN_FABLE_AVAILABLE") == "1"
}
```

In `ResolveModel`, insert between the "6. Ultimate fallback" block and the "Safety floor clamping" block:
```go
	// Fable-window fallback: fable resolves only while the window is open;
	// otherwise degrade to opus (fail-closed, never below today's tier).
	if result == "fable" && !fableWindowOpen() {
		result = "opus"
	}
```

## Step 3 — Go tests: `core/intercore/internal/routing/resolve_test.go`

Append these tests (match existing style; `testConfig()` is the shared fixture — do not modify it):
```go
func TestParseModelTierFable(t *testing.T) {
	if got := ParseModelTier("fable"); got != TierFable {
		t.Errorf("ParseModelTier(fable) = %d, want %d", got, TierFable)
	}
	if got := TierFable.String(); got != "fable" {
		t.Errorf("TierFable.String() = %q, want fable", got)
	}
	if TierFable <= TierOpus {
		t.Errorf("TierFable (%d) must rank above TierOpus (%d)", TierFable, TierOpus)
	}
}

func TestResolveModelFableWindowFallback(t *testing.T) {
	cfg := &Config{}
	cfg.Subagents.Defaults.Model = "fable"
	cfg.Subagents.Defaults.Categories = map[string]string{}
	cfg.Subagents.Phases = map[string]PhaseConfig{}
	cfg.Subagents.Overrides = map[string]string{}
	r := NewResolver(cfg)

	t.Setenv("CLAVAIN_FABLE_AVAILABLE", "")
	if got := r.ResolveModel(ResolveOpts{}); got != "opus" {
		t.Errorf("window closed: got %q, want opus", got)
	}
	t.Setenv("CLAVAIN_FABLE_AVAILABLE", "1")
	if got := r.ResolveModel(ResolveOpts{}); got != "fable" {
		t.Errorf("window open: got %q, want fable", got)
	}
}

func TestApplyFloorFableNotClamped(t *testing.T) {
	// The review's acceptance test (f-011): fable must resolve above every
	// floor — fallback semantics, never floor-clamp semantics.
	cfg := &Config{
		Roles: RolesConfig{
			Roles: map[string]RoleEntry{
				"safety": {MinModel: "sonnet", Agents: []string{"fd-safety"}},
			},
		},
	}
	cfg.Subagents.Defaults.Categories = map[string]string{}
	cfg.Subagents.Phases = map[string]PhaseConfig{}
	cfg.Subagents.Overrides = map[string]string{}
	r := NewResolver(cfg)
	if got := r.applyFloor("fd-safety", "fable"); got != "fable" {
		t.Errorf("fable vs sonnet floor: got %q, want fable (no clamp)", got)
	}
}
```
Note: if `RolesConfig`/`RoleEntry` field names differ from `TestApplyFloorUnknownTier`'s usage at resolve_test.go:261-283, copy that test's exact construction pattern instead.

Run: `cd /Users/sma/projects/Sylveste/core/intercore && go test ./internal/routing/` — must pass. Then `go build ./...` — must compile.

## Step 4 — Bash tier vocabulary: `os/Clavain/scripts/lib-routing.sh`

In `_routing_model_tier` (lines ~66-85), add directly after the `opus)` line group (after the three tier-3 `local:`/`flash-moe:` lines, before `*)`):
```sh
    fable)                              echo 4 ;;  # frontier tier — capability-routing doctrine
```

In `_routing_downgrade` (lines ~119-132), add before the `*)` arm:
```sh
    fable)              echo "opus" ;;
```

In `routing_resolve_model`: find the line near the end of the function where the safety floor is applied (search within the function for `_routing_apply_safety_floor`). Insert IMMEDIATELY BEFORE that call:
```sh
  # Fable-window fallback: fable resolves only while the window is open (fail-closed).
  if [[ "$result" == "fable" && "${CLAVAIN_FABLE_AVAILABLE:-0}" != "1" ]]; then
    echo "[fable-window] fable→opus (window closed) phase=${phase:-} agent=${agent:-}" >&2
    result="opus"
  fi
```
If the function has more than one return path that emits `$result`, place the fallback before the floor call on the main path only (there is one floor-application site).

Verify: `bash -n os/Clavain/scripts/lib-routing.sh` — clean.

## Step 5 — Bash functional test: `os/Clavain/tests/routing/fable-tier-test.sh` (new file; create dirs as needed)

```sh
#!/usr/bin/env bash
# fc5.1 acceptance: fable tier vocabulary + window fallback (bash resolver).
set -euo pipefail
cd "$(dirname "$0")/../.."
source scripts/lib-routing.sh

fail() { echo "FAIL: $1" >&2; exit 1; }

[[ "$(_routing_model_tier fable)" == "4" ]] || fail "_routing_model_tier fable != 4"
[[ "$(_routing_model_tier opus)" == "3" ]] || fail "opus tier changed"
[[ "$(_routing_downgrade fable)" == "opus" ]] || fail "_routing_downgrade fable != opus"

# Floor semantics: fable (4) vs a sonnet floor (2) must NOT clamp.
declare -A _ROUTING_SF_AGENT_MIN=( [fd-safety]="sonnet" )
[[ "$(_routing_apply_safety_floor fd-safety fable test)" == "fable" ]] || fail "fable clamped by sonnet floor"

echo "PASS: fable tier bash suite"
```
`chmod +x` it. Run: `bash os/Clavain/tests/routing/fable-tier-test.sh` — must print PASS.

## Step 6 — routing.yaml doctrine positions: `os/Clavain/config/routing.yaml`

Under `subagents.phases.brainstorm`, change `model: opus` → `model: fable` and add an inline comment `# frontier window; falls back to opus when closed (fc5.1)`. Change NOTHING else in the file (categories under brainstorm stay as they are).

## Step 7 — Agency specs: `os/Clavain/config/agency/*.yaml`

For each of the five specs, inspect its `models:` block. Apply exactly this rule: every `default:` or category value that is currently `opus` AND belongs to a planning/review position (phase names containing brainstorm/strategy/design/discover/planned, or category `review`) becomes `fable`. Values of `sonnet`/`haiku` are untouched. Known case from recon — `build.yaml`:
```yaml
models:
  planned:
    default: sonnet
    categories:
      review: fable      # was: opus
  executing:
    default: sonnet
    categories:
      review: opus       # execution-phase review stays opus (validator tier)
```
Note the asymmetry is intentional: plan review is frontier work (doctrine rule 1); execution-phase validation is the opus tier's job (rule 3). In discover/design/reflect/ship specs apply the same rule; if a spec has no `models:` block or no `opus` values in planning/review positions, leave it unchanged.

Validate: `ic agency validate --all --spec-dir=/Users/sma/projects/Sylveste/os/Clavain/config/agency` exits 0 (if `ic` is not on PATH, run `cd /Users/sma/projects/Sylveste/core/intercore && go run ./cmd/ic agency validate --all --spec-dir=/Users/sma/projects/Sylveste/os/Clavain/config/agency`).

## Step 8 — Window detection: `os/Clavain/hooks/session-start.sh`

Find where the hook assembles exported env/context near its beginning (grep for `export` statements or the env-injection section). Add a self-contained block (do not restructure anything):
```sh
# --- Fable-window detection (fc5.1) ---
# Fail-closed: only explicit evidence opens the window. Honor a pre-set value.
if [[ -z "${CLAVAIN_FABLE_AVAILABLE:-}" ]]; then
  _clavain_session_model="${CLAUDE_MODEL:-${ANTHROPIC_MODEL:-${MODEL:-}}}"
  if [[ "$_clavain_session_model" == *fable* ]]; then
    export CLAVAIN_FABLE_AVAILABLE=1
  else
    export CLAVAIN_FABLE_AVAILABLE=0
  fi
fi
```
If the hook communicates context via stdout rather than exports, ALSO append a line to its stdout context output: `Fable window: ${CLAVAIN_FABLE_AVAILABLE}` (find the section that already echoes advisory lines and match its style). Verify `bash -n os/Clavain/hooks/session-start.sh`.

## Acceptance Criteria (validator: check each mechanically; pass/fail only)

1. **go-tests**: `cd /Users/sma/projects/Sylveste/core/intercore && go test ./internal/routing/` exits 0, and the output shows `TestParseModelTierFable`, `TestResolveModelFableWindowFallback`, `TestApplyFloorFableNotClamped` all ran (use `go test -run 'Fable' -v ./internal/routing/` to confirm all three PASS).
2. **go-build**: `cd /Users/sma/projects/Sylveste/core/intercore && go build ./...` exits 0.
3. **bash-tier**: `grep -nE 'fable\)\s+echo 4' /Users/sma/projects/Sylveste/os/Clavain/scripts/lib-routing.sh` matches exactly once, and `grep -nE 'fable\)\s+echo "opus"' .../lib-routing.sh` matches exactly once (downgrade arm).
4. **bash-syntax**: `bash -n` clean on both `os/Clavain/scripts/lib-routing.sh` and `os/Clavain/hooks/session-start.sh`.
5. **bash-functional**: `bash /Users/sma/projects/Sylveste/os/Clavain/tests/routing/fable-tier-test.sh` prints `PASS: fable tier bash suite` and exits 0.
6. **fallback-in-resolver**: `grep -n 'CLAVAIN_FABLE_AVAILABLE' /Users/sma/projects/Sylveste/os/Clavain/scripts/lib-routing.sh` shows the fallback inside `routing_resolve_model` positioned before the `_routing_apply_safety_floor` call (verify by reading the surrounding 10 lines).
7. **yaml-doctrine**: `grep -n 'model: fable' /Users/sma/projects/Sylveste/os/Clavain/config/routing.yaml` hits under the brainstorm phase; `grep -rn 'fable' /Users/sma/projects/Sylveste/os/Clavain/config/agency/` shows fable ONLY in planning/review positions and `grep -rn 'sonnet' .../config/agency/` counts are unchanged from before (no sonnet position was upgraded — compare against `git -C /Users/sma/projects/Sylveste/os/Clavain diff config/agency/` which must show only opus→fable changes).
8. **agency-validate**: the `ic agency validate --all --spec-dir=.../config/agency` command from Step 7 exits 0.
9. **window-detection**: `grep -n 'CLAVAIN_FABLE_AVAILABLE' /Users/sma/projects/Sylveste/os/Clavain/hooks/session-start.sh` shows the fail-closed detection block.
10. **no-commits**: `git -C /Users/sma/projects/Sylveste/os/Clavain log --oneline -1` and `git -C /Users/sma/projects/Sylveste/core/intercore log --oneline -1` show the same HEADs as before execution (executor made no commits; working trees dirty is expected).
