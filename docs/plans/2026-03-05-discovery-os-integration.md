---
artifact_type: plan
bead: iv-wie5i
stage: design
---
# Discovery OS Integration — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use clavain:executing-plans to implement this plan task-by-task.

**Bead:** iv-wie5i
**Goal:** Wire interject's scan output through the kernel discovery CLI so every discovery produces a durable kernel record, and gate bead creation by confidence tier.

**Architecture:** Scanner calls `ic discovery submit` via subprocess after scoring each discovery (all tiers). OutputPipeline gates bead creation: high=P2, medium=P4+pending_triage label, low=no bead. After bead creation, `ic discovery promote` links the kernel record to the bead. A triage skill and backlog sweep script complete the integration.

**Tech Stack:** Python (interject), Go CLI (`ic`), Bash (sweep script), SQLite (interject DB + intercore DB)

**Prior Learnings:**
- `docs/solutions/patterns/hybrid-cli-plugin-architecture-20260223.md` — CLI owns logic, plugin calls via subprocess. Validates the `ic` subprocess approach.
- `interverse/interject/src/interject/outputs.py:58-98` — Existing `bd create` subprocess pattern with `capture_output=True`, `timeout=10`, `FileNotFoundError` catch. Replicate for `ic` calls.
- `interverse/interject/tests/test_outputs.py:33-41` — Mock pattern: `patch("interject.outputs.subprocess.run")` returning `CompletedProcess`. Extend for `ic` calls.
- `docs/research/backlog-triage-post-e3.md` — 130 interject P3+ items in backlog. Validates sweep thresholds.
- `docs/solutions/patterns/set-e-with-fallback-paths-20260216.md` — Use `|| var=$?` pattern in bash scripts when commands may fail.
- `docs/solutions/patterns/event-pipeline-shell-consumer-bugs-20260228.md` — Check return codes carefully on `ic` subprocess calls; silent failures are common.

---

### Task 1: Add kernel submit helper to OutputPipeline

**Files:**
- Modify: `interverse/interject/src/interject/outputs.py`
- Test: `interverse/interject/tests/test_outputs.py`

**Step 1: Write the failing test**

Add to `tests/test_outputs.py`:

```python
def test_kernel_submit_called_on_process(
    tmp_path: Path, base_discovery: dict, mock_bd_cli
) -> None:
    """ic discovery submit is called for every processed discovery."""
    pipeline = OutputPipeline(docs_root=tmp_path, interverse_root=tmp_path)

    with patch("interject.outputs.subprocess.run") as run_mock:
        run_mock.return_value = subprocess.CompletedProcess(
            args=["ic"], returncode=0, stdout="disc-123\n", stderr=""
        )
        pipeline._submit_to_kernel(base_discovery)

    # Verify ic discovery submit was called with correct flags
    call_args = run_mock.call_args[0][0]
    assert call_args[0] == "ic"
    assert call_args[1] == "discovery"
    assert call_args[2] == "submit"
    assert any("--source=github" in a for a in call_args)
    assert any("--title=" in a for a in call_args)
    assert any("--score=" in a for a in call_args)
```

**Step 2: Run test to verify it fails**

Run: `cd interverse/interject && uv run pytest tests/test_outputs.py::test_kernel_submit_called_on_process -v`
Expected: FAIL with `AttributeError: 'OutputPipeline' object has no attribute '_submit_to_kernel'`

**Step 3: Implement `_submit_to_kernel` method**

Add to `OutputPipeline` in `outputs.py`, after `_create_bead`:

```python
def _submit_to_kernel(self, discovery: dict) -> str | None:
    """Submit discovery to kernel via ic CLI. Returns kernel discovery ID or None."""
    import json as _json
    import tempfile

    cmd = [
        "ic", "discovery", "submit",
        f"--source={discovery['source']}",
        f"--source-id={discovery.get('id', '')}",
        f"--title={discovery['title'][:200]}",
        f"--score={discovery.get('relevance_score', 0):.4f}",
    ]

    if discovery.get("summary"):
        cmd.append(f"--summary={discovery['summary'][:500]}")
    if discovery.get("url"):
        cmd.append(f"--url={discovery['url']}")

    # Write embedding to temp file if present
    embedding_file = None
    try:
        if discovery.get("embedding"):
            embedding_file = tempfile.NamedTemporaryFile(
                suffix=".bin", delete=False
            )
            if isinstance(discovery["embedding"], bytes):
                embedding_file.write(discovery["embedding"])
            else:
                embedding_file.write(bytes(discovery["embedding"]))
            embedding_file.close()
            cmd.append(f"--embedding={embedding_file.name}")

        # Write metadata to temp file if present
        metadata = discovery.get("raw_metadata")
        metadata_file = None
        if metadata:
            metadata_file = tempfile.NamedTemporaryFile(
                suffix=".json", mode="w", delete=False
            )
            if isinstance(metadata, str):
                metadata_file.write(metadata)
            else:
                _json.dump(metadata, metadata_file)
            metadata_file.close()
            cmd.append(f"--metadata={metadata_file.name}")

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=10,
        )

        if result.returncode == 0:
            kernel_id = result.stdout.strip()
            logger.info("Submitted to kernel: %s -> %s", discovery.get("id"), kernel_id)
            return kernel_id
        else:
            logger.warning("ic discovery submit failed (rc=%d): %s", result.returncode, result.stderr)

    except FileNotFoundError:
        logger.warning("ic CLI not found — kernel submit skipped (install intercore)")
    except subprocess.TimeoutExpired:
        logger.warning("ic discovery submit timed out")
    finally:
        import os
        if embedding_file and hasattr(embedding_file, "name"):
            try:
                os.unlink(embedding_file.name)
            except OSError:
                pass
        if metadata_file and hasattr(metadata_file, "name"):
            try:
                os.unlink(metadata_file.name)
            except OSError:
                pass

    return None
```

**Step 4: Run test to verify it passes**

Run: `cd interverse/interject && uv run pytest tests/test_outputs.py::test_kernel_submit_called_on_process -v`
Expected: PASS

**Step 5: Commit**

```bash
cd interverse/interject
git add src/interject/outputs.py tests/test_outputs.py
git commit -m "feat(interject): add _submit_to_kernel helper for ic discovery submit"
```

---

### Task 2: Add kernel promote helper to OutputPipeline

**Files:**
- Modify: `interverse/interject/src/interject/outputs.py`
- Test: `interverse/interject/tests/test_outputs.py`

**Step 1: Write the failing test**

```python
def test_kernel_promote_links_bead(tmp_path: Path, base_discovery: dict) -> None:
    """ic discovery promote is called after bead creation."""
    pipeline = OutputPipeline(docs_root=tmp_path, interverse_root=tmp_path)

    with patch("interject.outputs.subprocess.run") as run_mock:
        run_mock.return_value = subprocess.CompletedProcess(
            args=["ic"], returncode=0, stdout="promoted disc-123 -> iv-456\n", stderr=""
        )
        pipeline._promote_in_kernel("disc-123", "iv-456")

    call_args = run_mock.call_args[0][0]
    assert call_args == ["ic", "discovery", "promote", "disc-123", "--bead-id=iv-456"]
```

**Step 2: Run test to verify it fails**

Run: `cd interverse/interject && uv run pytest tests/test_outputs.py::test_kernel_promote_links_bead -v`
Expected: FAIL

**Step 3: Implement `_promote_in_kernel` method**

Add to `OutputPipeline`:

```python
def _promote_in_kernel(self, kernel_discovery_id: str, bead_id: str) -> bool:
    """Link kernel discovery record to bead via ic discovery promote."""
    try:
        result = subprocess.run(
            ["ic", "discovery", "promote", kernel_discovery_id, f"--bead-id={bead_id}"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode == 0:
            logger.info("Kernel promote: %s -> %s", kernel_discovery_id, bead_id)
            return True
        else:
            logger.warning("ic discovery promote failed (rc=%d): %s", result.returncode, result.stderr)
    except (FileNotFoundError, subprocess.TimeoutExpired) as e:
        logger.warning("ic discovery promote skipped: %s", e)
    return False
```

**Step 4: Run test to verify it passes**

Run: `cd interverse/interject && uv run pytest tests/test_outputs.py::test_kernel_promote_links_bead -v`
Expected: PASS

**Step 5: Commit**

```bash
cd interverse/interject
git add src/interject/outputs.py tests/test_outputs.py
git commit -m "feat(interject): add _promote_in_kernel helper for ic discovery promote"
```

---

### Task 3: Modify `process()` for tier-gated bead creation

**Files:**
- Modify: `interverse/interject/src/interject/outputs.py`
- Test: `interverse/interject/tests/test_outputs.py`

This is the core change: modify `process()` to accept a discovery_id, call `_submit_to_kernel`, gate bead creation by tier, and call `_promote_in_kernel` after.

**Step 1: Update existing tests to match new signature**

The `process()` method gains an optional `discovery_id` parameter. Update existing tests to pass it:

```python
# In test_high_tier_creates_brainstorm:
result = pipeline.process(base_discovery, "high", discovery_id="ij-github-test-1")

# In test_medium_tier_creates_briefing_only:
result = pipeline.process(medium_discovery, "medium", discovery_id="ij-github-test-1")

# In test_low_tier_no_output:
result = pipeline.process(base_discovery, "low", discovery_id="ij-github-test-1")
```

**Step 2: Write new tests for tier-gated behavior**

```python
def test_medium_tier_creates_p4_bead_with_pending_triage(
    tmp_path: Path, base_discovery: dict
) -> None:
    """Medium-tier creates a P4 bead with pending_triage label."""
    pipeline = OutputPipeline(docs_root=tmp_path, interverse_root=tmp_path)
    medium_discovery = dict(base_discovery)
    medium_discovery["confidence_tier"] = "medium"
    medium_discovery["relevance_score"] = 0.65

    with patch("interject.outputs.subprocess.run") as run_mock:
        run_mock.return_value = subprocess.CompletedProcess(
            args=["bd", "create"], returncode=0,
            stdout="Created issue: iv-789\n", stderr=""
        )
        result = pipeline.process(medium_discovery, "medium", discovery_id="ij-github-test-1")

    # Find the bd create call
    bd_calls = [c for c in run_mock.call_args_list if c[0][0][0] == "bd"]
    assert len(bd_calls) >= 1
    bd_args = bd_calls[0][0][0]
    assert "--priority=4" in bd_args
    assert any("pending_triage" in a for a in bd_args)


def test_low_tier_submits_to_kernel_but_no_bead(
    tmp_path: Path, base_discovery: dict
) -> None:
    """Low tier submits to kernel but creates no bead and no docs."""
    pipeline = OutputPipeline(docs_root=tmp_path, interverse_root=tmp_path)

    with patch("interject.outputs.subprocess.run") as run_mock:
        run_mock.return_value = subprocess.CompletedProcess(
            args=["ic"], returncode=0, stdout="disc-123\n", stderr=""
        )
        result = pipeline.process(base_discovery, "low", discovery_id="ij-github-test-1")

    assert result["tier"] == "low"
    assert "bead_id" not in result
    # ic discovery submit should still be called
    ic_calls = [c for c in run_mock.call_args_list if c[0][0][0] == "ic"]
    assert len(ic_calls) >= 1


def test_process_returns_kernel_id(
    tmp_path: Path, base_discovery: dict
) -> None:
    """process() returns kernel_discovery_id in result."""
    pipeline = OutputPipeline(docs_root=tmp_path, interverse_root=tmp_path)

    ic_result = subprocess.CompletedProcess(
        args=["ic"], returncode=0, stdout="disc-abc\n", stderr=""
    )
    bd_result = subprocess.CompletedProcess(
        args=["bd"], returncode=0, stdout="Created issue: iv-123\n", stderr=""
    )

    def side_effect(cmd, **kwargs):
        if cmd[0] == "ic":
            return ic_result
        return bd_result

    with patch("interject.outputs.subprocess.run", side_effect=side_effect):
        result = pipeline.process(base_discovery, "high", discovery_id="ij-github-test-1")

    assert result.get("kernel_discovery_id") == "disc-abc"
```

**Step 3: Rewrite `process()` method**

Replace the `process()` method in `OutputPipeline`:

```python
def process(
    self, discovery: dict, tier: str, discovery_id: str | None = None
) -> dict[str, Any]:
    """Process a scored discovery through the output pipeline.

    Args:
        discovery: Discovery dict from the database
        tier: Confidence tier ('high', 'medium', 'low')
        discovery_id: Local discovery ID for kernel linking

    Returns:
        Dict with keys: tier, bead_id, briefing_path, brainstorm_path,
        kernel_discovery_id (if kernel submit succeeded)
    """
    result: dict[str, Any] = {"tier": tier}

    # Submit to kernel for all tiers (durable record + events)
    kernel_id = self._submit_to_kernel(discovery)
    if kernel_id:
        result["kernel_discovery_id"] = kernel_id

    if tier == "low":
        # Kernel record only — no bead, no docs
        return result

    if tier == "medium":
        # P4 bead with pending_triage label
        bead_id = self._create_bead(discovery, tier, priority=4, labels=["pending_triage"])
        result["bead_id"] = bead_id

        # Write briefing doc (no brainstorm for medium)
        briefing_path = self._write_briefing(discovery)
        result["briefing_path"] = str(briefing_path)

    elif tier == "high":
        # P2 bead (unchanged behavior)
        bead_id = self._create_bead(discovery, tier, priority=2)
        result["bead_id"] = bead_id

        # Write briefing doc
        briefing_path = self._write_briefing(discovery)
        result["briefing_path"] = str(briefing_path)

        # Write brainstorm doc
        brainstorm_path = self._write_brainstorm(discovery)
        result["brainstorm_path"] = str(brainstorm_path)

    # Link kernel record to bead
    if kernel_id and result.get("bead_id"):
        self._promote_in_kernel(kernel_id, result["bead_id"])

    return result
```

**Step 4: Update `_create_bead` signature to accept priority and labels**

```python
def _create_bead(
    self, discovery: dict, tier: str,
    priority: int = 2, labels: list[str] | None = None
) -> str | None:
    """Create a bead via bd CLI."""
    title = f"[interject] {discovery['title'][:80]}"
    description = (
        f"Source: {discovery['source']} | {discovery['url']}\n\n"
        f"{discovery.get('summary', '')}\n\n"
        f"Relevance score: {discovery.get('relevance_score', 0):.2f}\n"
        f"Discovered: {discovery.get('discovered_at', '')}"
    )

    cmd = [
        "bd", "create",
        f"--title={title}",
        "--type=task",
        f"--priority={priority}",
        f"--description={description}",
    ]
    if labels:
        for label in labels:
            cmd.append(f"--label={label}")

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            cwd=str(self.interverse_root),
            timeout=10,
        )
        if result.returncode == 0:
            for line in result.stdout.splitlines():
                if "Created issue:" in line or "Created" in line:
                    parts = line.split()
                    for i, p in enumerate(parts):
                        if p.endswith(":") and i + 1 < len(parts):
                            return parts[i + 1]
                        if p.startswith("iv-"):
                            return p
        else:
            logger.warning("bd create failed: %s", result.stderr)
    except (subprocess.TimeoutExpired, FileNotFoundError) as e:
        logger.warning("Failed to create bead: %s", e)
    return None
```

**Step 5: Run all tests**

Run: `cd interverse/interject && uv run pytest tests/test_outputs.py -v`
Expected: All tests PASS

**Step 6: Commit**

```bash
cd interverse/interject
git add src/interject/outputs.py tests/test_outputs.py
git commit -m "feat(interject): tier-gated bead creation with kernel integration

High tier: P2 bead + briefing + brainstorm (unchanged)
Medium tier: P4 bead with pending_triage label + briefing
Low tier: kernel record only (no bead, no docs)
All tiers: ic discovery submit for durable kernel record
After bead creation: ic discovery promote links kernel record"
```

---

### Task 4: Update scanner to pass discovery_id to process()

**Files:**
- Modify: `interverse/interject/src/interject/scanner.py`

**Step 1: Update `scan_all` to pass discovery_id**

In `scanner.py`, line 162, change:

```python
# Old:
output_result = self.outputs.process(
    self.db.get_discovery(disc_id), tier
)

# New:
output_result = self.outputs.process(
    self.db.get_discovery(disc_id), tier, discovery_id=disc_id
)
```

**Step 2: Update promotion recording to use kernel_discovery_id**

In `scanner.py`, after the `process()` call (around line 167), update:

```python
# Old:
if output_result.get("bead_id"):
    priority = 2 if tier == "high" else 3
    self.db.record_promotion(
        disc_id, output_result["bead_id"], priority
    )

# New:
if output_result.get("bead_id"):
    priority = 2 if tier == "high" else (4 if tier == "medium" else 3)
    self.db.record_promotion(
        disc_id, output_result["bead_id"], priority
    )
```

**Step 3: Commit**

```bash
cd interverse/interject
git add src/interject/scanner.py
git commit -m "feat(interject): pass discovery_id to output pipeline, fix medium priority"
```

---

### Task 5: Create `/interject:triage` skill

**Files:**
- Create: `interverse/interject/skills/triage/SKILL.md`

**Step 1: Create the skill directory and file**

```bash
mkdir -p interverse/interject/skills/triage
```

**Step 2: Write SKILL.md**

```markdown
---
name: triage
description: Batch review pending_triage beads — promote or dismiss interject discoveries
user_invocable: true
---

# /interject:triage

Batch review beads created by interject with `pending_triage` status. Promote worthy items (raise priority to P2) or dismiss stale ones.

## Usage

When the user invokes `/interject:triage`, follow the behavior below.

## Arguments

- `--limit=N` — Maximum items per batch (default: 5, max: 20)
- `--source=NAME` — Filter to a specific source (arxiv, github, hackernews, etc.)

## Behavior

1. **List pending items:**
   Run: `bd list --label=pending_triage --status=open --json`
   Parse the JSON output to get bead IDs, titles, priorities.

2. **Enrich with discovery data:**
   For each bead, extract the source URL and score from the bead description (format: `Source: <source> | <url>` and `Relevance score: <score>`).

3. **Present batch via AskUserQuestion:**
   Show items in a numbered list with:
   - Title (without `[interject]` prefix)
   - Source and URL
   - Relevance score
   - One-line summary (from bead description)

   Options per item (multiSelect):
   - "Promote 1, 2, 3..." — Select items to promote
   - "Dismiss all" — Close all items in this batch
   - "Skip batch" — Leave all for later
   - "Done" — Stop triaging

4. **Process selections:**
   For promoted items:
   - `bd update <id> --priority=2`
   - `bd update <id> --remove-label=pending_triage`
   - If kernel discovery ID is available: `ic discovery feedback <kernel_id> --signal=promote --actor=human`

   For dismissed items:
   - `bd close <id> --reason="triage-dismissed"`
   - If kernel discovery ID is available: `ic discovery feedback <kernel_id> --signal=dismiss --actor=human`

5. **Report summary:**
   ```
   Triage complete: N promoted, M dismissed, K skipped
   Remaining pending: <count>
   ```

6. **Loop:** If items remain and user didn't choose "Done", present the next batch.
```

**Step 3: Commit**

```bash
cd interverse/interject
git add skills/triage/SKILL.md
git commit -m "feat(interject): add /interject:triage skill for pending_triage batch review"
```

---

### Task 6: Write backlog sweep script

**Files:**
- Create: `scripts/backlog-sweep.sh`

**Step 1: Write the script**

```bash
#!/usr/bin/env bash
set -euo pipefail

# One-time backlog sweep: defer or close stale interject beads.
# Usage: bash scripts/backlog-sweep.sh [--apply]
#
# Dry-run by default. Pass --apply to execute changes.
# Only targets beads with [interject] title prefix.
# Never touches P0/P1 beads.

APPLY=false
STALE_DAYS=30
MIN_CLOSE_PRIORITY=3  # P3+ only

for arg in "$@"; do
    case "$arg" in
        --apply) APPLY=true ;;
        --stale-days=*) STALE_DAYS="${arg#*=}" ;;
        *) echo "Usage: $0 [--apply] [--stale-days=N]"; exit 1 ;;
    esac
done

export BEADS_DIR="${BEADS_DIR:-$(git rev-parse --show-toplevel 2>/dev/null)/.beads}"

if ! command -v bd >/dev/null 2>&1; then
    echo "Error: bd CLI not found" >&2
    exit 1
fi

echo "Backlog sweep — $(date -Iseconds)"
echo "Mode: $( $APPLY && echo 'APPLY' || echo 'DRY-RUN' )"
echo "Stale threshold: ${STALE_DAYS} days"
echo "---"

now=$(date +%s)
stale_threshold=$((now - STALE_DAYS * 86400))

deferred=0
closed=0
skipped=0
candidates=0

# Get all open beads as JSON
beads_json=$(bd list --status=open --json 2>/dev/null) || {
    echo "Error: bd list failed" >&2
    exit 1
}

# Process each bead
echo "$beads_json" | jq -c '.[]' | while IFS= read -r bead; do
    title=$(echo "$bead" | jq -r '.title // ""')
    id=$(echo "$bead" | jq -r '.id // ""')
    priority=$(echo "$bead" | jq -r '.priority // 4')
    updated=$(echo "$bead" | jq -r '.updated_at // ""')

    # Only target [interject] beads
    [[ "$title" != "[interject]"* ]] && continue

    # Never touch P0/P1
    [[ "$priority" -le 1 ]] && continue

    # Check staleness (updated_at as ISO date)
    if [[ -n "$updated" ]]; then
        updated_epoch=$(date -d "$updated" +%s 2>/dev/null) || continue
        [[ "$updated_epoch" -gt "$stale_threshold" ]] && continue
    fi

    # Check for phase state (has human touched this?)
    phase=$(bd state "$id" phase 2>/dev/null) || phase=""
    if [[ -n "$phase" && "$phase" != *"no "* ]]; then
        # Has phase state — skip, human has interacted
        continue
    fi

    candidates=$((candidates + 1))

    if [[ "$priority" -ge "$MIN_CLOSE_PRIORITY" ]]; then
        # P3+ → close
        if $APPLY; then
            bd close "$id" --reason="stale-sweep: ${STALE_DAYS}d inactive, no phase state" 2>/dev/null || true
            echo "CLOSED: $id — $title (P${priority})"
        else
            echo "WOULD CLOSE: $id — $title (P${priority})"
        fi
        closed=$((closed + 1))
    else
        # P2 → defer only
        if $APPLY; then
            bd update "$id" --status=deferred 2>/dev/null || true
            echo "DEFERRED: $id — $title (P${priority})"
        else
            echo "WOULD DEFER: $id — $title (P${priority})"
        fi
        deferred=$((deferred + 1))
    fi
done

skipped=$((candidates - closed - deferred))

echo "---"
echo "Summary: ${candidates} candidates, ${closed} closed, ${deferred} deferred, ${skipped} skipped"
if ! $APPLY; then
    echo "(dry-run — pass --apply to execute)"
fi
```

**Step 2: Make executable**

```bash
chmod +x scripts/backlog-sweep.sh
```

**Step 3: Test dry-run mode**

Run: `bash scripts/backlog-sweep.sh`
Expected: Lists candidates with "WOULD CLOSE" / "WOULD DEFER" prefixes, no changes made.

**Step 4: Commit**

```bash
git add scripts/backlog-sweep.sh
git commit -m "feat: add backlog sweep script for stale interject beads

Dry-run by default. --apply to execute.
Closes P3+ interject beads with no phase state and >30d inactivity.
Defers P2. Never touches P0/P1."
```

---

### Task 7: Update interject CLAUDE.md for kernel-native status

**Files:**
- Modify: `interverse/interject/CLAUDE.md`

**Step 1: Add kernel-native section**

Add after the "## MCP Server" section:

```markdown
## Kernel-Native Plugin

Interject is a **kernel-native** plugin (see PHILOSOPHY.md § Plugin Tiers). It requires intercore (`ic` CLI) for full functionality. Without intercore, scans still work but discoveries won't produce kernel records, events, or feedback loop data.

Key integration points:
- `outputs.py` calls `ic discovery submit` after scoring (all tiers)
- `outputs.py` calls `ic discovery promote` after bead creation (medium+high)
- `/interject:triage` calls `ic discovery feedback` for closed-loop learning
```

**Step 2: Commit**

```bash
cd interverse/interject
git add CLAUDE.md
git commit -m "docs(interject): document kernel-native plugin status"
```

---

### Task 8: Run full test suite and verify

**Files:** None (verification only)

**Step 1: Run interject tests**

Run: `cd interverse/interject && uv run pytest tests/ -v`
Expected: All tests pass, including new kernel integration tests.

**Step 2: Verify ic CLI flags match**

Run: `ic discovery submit --help 2>&1 || ic 2>&1 | grep -A2 "discovery submit"`
Verify: `--source`, `--source-id`, `--title`, `--score`, `--summary`, `--url`, `--embedding`, `--metadata` flags exist.

**Step 3: Verify bd create supports --label flag**

Run: `BEADS_DIR=.beads bd create --help 2>&1 || echo "check bd docs"`
Note: If `--label` is not supported by `bd create`, Task 3's `_create_bead` needs adjustment — use `bd update <id> --label=pending_triage` as a follow-up call instead.

**Step 4: Final commit if any fixes needed**

```bash
git add -A
git commit -m "fix: address test suite findings from integration verification"
```
