# interspect: `source_kind` discriminator migration — DRAFT

**Status:** draft, not yet applied
**Beads:** `sylveste-sfhq` (epic), `sylveste-sfhq.1` (this work), `sylveste-sfhq.2`, `sylveste-sfhq.3`
**Cross-ref:** `sylveste-s3z6.19.9` (separate `task_outcome` column; no conflict)
**Author:** session 5e2bad88, 2026-05-06

## Why

interspect's `evidence.source` column conflates "agent name" with "telemetry origin." To ingest tool-time pattern signals (and later interstat / galiana feeds) without polluting agent-routing math, we add `source_kind ∈ {agent, tool, pattern}` and filter the routing/scoring paths by `source_kind = 'agent'`.

The lineage columns (`source_event_id`, `source_table`, added in iv-w3ee6) anticipated multi-source ingestion but never landed the type discriminator. This finishes that work.

## Scope decision: filter where, not everywhere

Three classes of query touch `evidence.source`. The filter rule differs by class:

| Path | Filter | Reason |
|---|---|---|
| `_interspect_compute_agent_scores` (writes `routing-calibration.json`) | **MUST** `source_kind = 'agent'` | tool rows would corrupt model-routing decisions |
| `_interspect_get_routing_eligible` (proposes overrides) | **MUST** `source_kind = 'agent'` | tools aren't routable agents |
| Per-agent count queries (lines 641, 700, 1033, 1418, 1862) | **SHOULD** `source_kind = 'agent'` | defensive; prevents collisions when a tool/agent share names |
| `_interspect_get_classified_patterns` (line 548) | **NO FILTER** | pattern detection is what surfaces tool patterns; that's the point |
| `_interspect_get_overlay_eligible` | **SPLIT** | agent rows → prompt overlay; tool rows → CLAUDE.md patch (handled in `.3`) |
| Effectiveness queries with `source LIKE 'fd-%'` (4078, 4152, 4181) | **OPTIONAL** | already safe (tool names don't match `fd-%`); add filter for clarity |

## Migration SQL

Two locations in `lib-interspect.sh` need the column added:

### A. Fresh-DB path (the heredoc starting at line 137)

Add inside the `CREATE TABLE evidence (...)` block, after `project_type TEXT`:

```sql
project_type TEXT,
source_kind TEXT NOT NULL DEFAULT 'agent' CHECK (source_kind IN ('agent','tool','pattern'))
```

Add after the existing `CREATE INDEX` lines (~line 204):

```sql
CREATE INDEX IF NOT EXISTS idx_evidence_source_kind ON evidence(source_kind, source);
```

### B. Existing-DB migration path (the bash block at lines ~84-126)

Add alongside the other `ALTER TABLE evidence ADD COLUMN ...` lines (~line 113):

```bash
# Add source_kind discriminator (sylveste-sfhq.1: telemetry fusion)
# CHECK constraint can't be added by ALTER TABLE in SQLite — enforced at insert time
sqlite3 "$_INTERSPECT_DB" "ALTER TABLE evidence ADD COLUMN source_kind TEXT NOT NULL DEFAULT 'agent';" 2>/dev/null || true
sqlite3 "$_INTERSPECT_DB" "CREATE INDEX IF NOT EXISTS idx_evidence_source_kind ON evidence(source_kind, source);" 2>/dev/null || true
```

**Idempotency:** existing rows get `'agent'` via the `DEFAULT` clause. Re-running the ALTER on a populated DB returns "duplicate column" → swallowed by `|| true`. Same pattern as the other migrations.

**SQLite quirk:** ALTER TABLE cannot add a CHECK constraint. The check lives only on the fresh-DB path. Existing-DB enforcement happens at insert time:

### C. `_interspect_insert_evidence` validation

Add to `_interspect_insert_evidence` (after the `hook_id` validation at ~line 2770), accepting an optional 7th positional `source_kind`:

```bash
# Args: $1=session_id $2=source $3=event $4=override_reason $5=context_json $6=hook_id $7=source_kind (default: 'agent')
_interspect_insert_evidence() {
    local session_id="$1"
    local source="$2"
    local event="$3"
    local override_reason="${4:-}"
    local context_json="${5:-{}}"
    local hook_id="${6:-}"
    local source_kind="${7:-agent}"
    # ... existing validation ...
    case "$source_kind" in
        agent|tool|pattern) ;;
        *) echo "[interspect] invalid source_kind: $source_kind" >&2; return 1 ;;
    esac
    # ... rest of function, include source_kind in INSERT ...
}
```

Existing callers pass 6 args → `source_kind` defaults to `'agent'`. **No caller changes required for existing-call sites.**

### D. Hook-id allowlist

In `_interspect_validate_hook_id` (line ~2740), extend the `case` arm:

```bash
interspect-evidence|interspect-session-start|interspect-session-end|interspect-correction|interspect-consumer|interspect-disagreement|interspect-execution-defect|interspect-verdict|interspect-delegation|interspect-decomposition|interspect-reaction|sprint-review-calibration|tool-time-pattern)
```

(adds `tool-time-pattern` at the end).

## Query filter patches

Each location needs `AND e.source_kind = 'agent'` (or `AND source_kind = 'agent'` if no alias). Listed by line, with the keyword to grep for:

| Line | Function / context | Patch |
|---|---|---|
| 641 | `_interspect_check_routing_eligible` (agent total/wrong) | `WHERE (source = '${escaped}' …) AND source_kind = 'agent' AND event IN …` |
| 700 | same function, second copy | same patch |
| 1033 | `_interspect_get_overlay_eligible` total/wrong | `WHERE source = '${escaped_agent}' AND source_kind = 'agent' AND event IN …` |
| 1418 | propose-override path | same pattern |
| 1862 | session_count for agent | `WHERE source = '${escaped_agent}' AND source_kind = 'agent'` |
| 3261 | `_interspect_compute_agent_scores` main query | add `AND e.source_kind = 'agent'` to the `WHERE e.event IN (…)` clause |
| 4078, 4152, 4181 | fd-effectiveness queries | already safe via `LIKE 'fd-%'`; defensive filter optional |

**Do NOT** add the filter to:
- Line 548 (`_interspect_get_classified_patterns`) — pattern detection should see tool rows
- Line 2103, 2137 (per-session evidence count) — accurate session totals need everything

## Test plan

### Structural (`tests/structural/test_structure.py`)

Add to existing schema assertion test:

```python
def test_evidence_source_kind_column(tmp_db):
    cols = {c[1] for c in tmp_db.execute("PRAGMA table_info(evidence)")}
    assert "source_kind" in cols
    # Default check
    rows = tmp_db.execute("INSERT INTO evidence (ts, session_id, seq, source, event, context, project) "
                          "VALUES ('2026-05-06', 's1', 1, 'fd-safety', 'override', '{}', 'p') RETURNING source_kind")
    assert rows.fetchone()[0] == "agent"

def test_evidence_source_kind_index(tmp_db):
    indexes = {r[1] for r in tmp_db.execute("PRAGMA index_list(evidence)")}
    assert "idx_evidence_source_kind" in indexes
```

### Behavioral (new `tests/shell/test_source_kind_filter.sh`)

```bash
# Setup: insert 5 agent rows (fd-safety override events) + 5 tool rows (Bash tool_error_rate_high)
# Assert: _interspect_compute_agent_scores returns ONLY fd-safety
# Assert: _interspect_get_classified_patterns sees BOTH (count = 2 distinct sources)
# Assert: _interspect_get_routing_eligible returns ONLY fd-safety
# Cleanup: rm -rf $TMPDIR/.clavain
```

### Regression

These must pass unchanged after migration:
- `tests/shell/test_effectiveness.sh`
- `tests/shell/test_tune.sh`
- `tests/shell/test_cross_project.sh`

### Idempotency check

Manual smoke test before merging:

```bash
# 1. On fresh DB
rm -rf /tmp/test-interspect/.clavain
CLAUDE_PROJECT_DIR=/tmp/test-interspect bash -c "source hooks/lib-interspect.sh && _interspect_ensure_db"
sqlite3 /tmp/test-interspect/.clavain/interspect/interspect.db "PRAGMA table_info(evidence);" | grep source_kind
# → expect: source_kind|TEXT|1|'agent'|0

# 2. On populated DB (production-shape)
cp ~/projects/Sylveste/.clavain/interspect/interspect.db /tmp/test-existing.db
# Run ALTER manually, verify no data loss
sqlite3 /tmp/test-existing.db "ALTER TABLE evidence ADD COLUMN source_kind TEXT NOT NULL DEFAULT 'agent';"
sqlite3 /tmp/test-existing.db "SELECT COUNT(*), COUNT(DISTINCT source_kind) FROM evidence;"
# → expect: N rows, 1 distinct source_kind ('agent')

# 3. Re-run migration (idempotent path)
sqlite3 /tmp/test-existing.db "ALTER TABLE evidence ADD COLUMN source_kind TEXT NOT NULL DEFAULT 'agent';" 2>&1
# → expect: error "duplicate column", but no row corruption
```

## Reversibility

SQLite < 3.35 cannot DROP COLUMN. The reversal path is:

```sql
-- If we need to roll back:
CREATE TABLE evidence_new AS SELECT id, ts, session_id, seq, source, source_version, event,
    override_reason, context, project, project_lang, project_type,
    source_event_id, source_table, raw_override_reason, quarantine_until
    FROM evidence;
DROP TABLE evidence;
ALTER TABLE evidence_new RENAME TO evidence;
-- (recreate indexes)
```

Most users have SQLite ≥3.35 (released 2021), so `ALTER TABLE evidence DROP COLUMN source_kind` works for them. Document both paths in a `REVERT.md` if we need it.

**Rollback is annoying but possible.** This is the "irreversible-ish" tradeoff flagged in scoping.

## Open questions

1. **CHECK constraint enforcement on existing DBs.** Insert-time validation in `_interspect_insert_evidence` is the practical answer. Should we also add a one-time `CREATE TRIGGER` that enforces it for raw `sqlite3` writes? (Probably no — the trigger overhead isn't worth defending against unsanctioned writers.)

2. **Bootstrap weighting interaction.** `_interspect_compute_agent_scores` joins `sessions s` for `session_source` weighting. Tool-pattern evidence might come from sessions where `session_source = 'bootstrap'`. With the `source_kind = 'agent'` filter at the evidence level, this is irrelevant — but worth noting that `_INTERSPECT_CALIBRATION_MIN_NON_BOOTSTRAP` thresholds are unaffected.

3. **Pattern detection thresholds.** `_interspect_get_classified_patterns` uses `HAVING COUNT(*) >= 2` — fine for agent rows but tool patterns might fire much more frequently (one per session). Consider a per-`source_kind` `HAVING` threshold in `.2` or `.3`.

## Sequence

1. **`.1` (this draft):** schema + scoring filter + tests. Land alone, verify no regression in calibration outputs over a week.
2. **`.2`:** bridge script + SessionEnd hook. Wire tool-time → interspect; verify tool evidence appears with `source_kind=tool` and is invisible to scoring.
3. **`.3`:** `/interspect:tune` dual-mode. Generate first CLAUDE.md patch from a real tool pattern.

## Files to touch (`.1` only)

```
interverse/interspect/hooks/lib-interspect.sh   # schema, validation, query filters (~10 patches)
interverse/interspect/tests/structural/test_structure.py   # column + index assertions
interverse/interspect/tests/shell/test_source_kind_filter.sh   # new file
```

No plugin manifest changes, no hook-registration changes, no command changes (those land in `.2` and `.3`).
