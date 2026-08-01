#!/usr/bin/env bash
# Tests for the deletion half of the two-machine sync.
#
# `bd import` is upsert-only, so a bead deleted on one machine survives on the
# other and is written back out on its next export — the deletion undoes itself.
# scripts/beads_apply_deletions.py closes that, driven by an explicit ledger.
#
# The property that matters most is NOT "the named bead is deleted" — it is
# "nothing else is". An applier that deleted the whole database would satisfy
# every other assertion here, so scenario 4 exists to make the rest mean
# something.
#
# Runs against a stubbed `bd`, so it never touches a real Dolt database. The
# end-to-end proof on two real databases is a manual exercise; this is the
# regression guard.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SANDBOX="$(mktemp -d)"
trap 'rm -rf "$SANDBOX"' EXIT

fail() { echo "FAIL: $*" >&2; exit 1; }

mkdir -p "$SANDBOX/scripts" "$SANDBOX/.beads" "$SANDBOX/bin"
cp "$ROOT/scripts/beads_apply_deletions.py" "$SANDBOX/scripts/"
cp "$ROOT/scripts/beads-confirm-deletion.sh" "$SANDBOX/scripts/"

# Stub bd. DB holds "id<TAB>updated_at" per line and is the whole contract the
# applier depends on: show tells it what exists and when it changed, delete
# removes it, export serializes what is left.
cat > "$SANDBOX/bin/bd" <<'STUB'
#!/usr/bin/env bash
DB="${BD_STUB_DB:?}"
case "${1:-}" in
  show)
    id="$2"
    line="$(grep -m1 "^$id	" "$DB" 2>/dev/null || true)"
    if [ -z "$line" ]; then
      echo "Error fetching $id: no issue found matching \"$id\"" >&2
      exit 1
    fi
    printf '[{"id":"%s","status":"open","updated_at":"%s"}]\n' "$id" "$(printf '%s' "$line" | cut -f2)"
    ;;
  delete)
    id="$2"
    grep -v "^$id	" "$DB" > "$DB.tmp" 2>/dev/null || true
    mv "$DB.tmp" "$DB"
    echo "✓ Deleted $id"
    ;;
  export)
    out="${3:-.beads/issues.jsonl}"
    : > "$out"
    while IFS=$'\t' read -r id ts; do
      [ -n "$id" ] && printf '{"id":"%s","updated_at":"%s"}\n' "$id" "$ts" >> "$out"
    done < "$DB"
    echo "Exported to $out"
    ;;
  *) exit 0 ;;
esac
STUB
chmod +x "$SANDBOX/bin/bd"
export PATH="$SANDBOX/bin:$PATH"
export BD_STUB_DB="$SANDBOX/db"

cd "$SANDBOX"
git init -q .
git config user.email t@test; git config user.name tester

reset_db() {
  printf 'keep-1\t2026-07-01T00:00:00Z\ntarget\t2026-07-01T00:00:00Z\nkeep-2\t2026-07-01T00:00:00Z\n' > "$BD_STUB_DB"
}
ledger() { printf '%s\n' "$@" > .beads/deletions.jsonl; }
present() { grep -q "^$1	" "$BD_STUB_DB"; }

# ─── 1: a recorded deletion is applied ────────────────────────────────
echo "=== 1: a bead named in the ledger is deleted ==="
reset_db
ledger '{"id":"target","deleted_at":"2026-07-30T00:00:00Z","actor":"mk","machine":"zklw"}'
python3 scripts/beads_apply_deletions.py --quiet >/dev/null 2>&1
present target && fail "the bead named in the ledger survived"

# ─── 2: replay is a no-op ─────────────────────────────────────────────
echo "=== 2: replaying the ledger changes nothing ==="
before="$(cat "$BD_STUB_DB")"
python3 scripts/beads_apply_deletions.py --quiet >/dev/null 2>&1 || fail "replay errored"
[ "$before" = "$(cat "$BD_STUB_DB")" ] || fail "replaying the ledger was not idempotent"

# ─── 3: newer local work is refused, loudly ───────────────────────────
echo "=== 3: a bead changed here after the deletion was recorded is kept ==="
printf 'keep-1\t2026-07-01T00:00:00Z\ntarget\t2026-08-01T00:00:00Z\n' > "$BD_STUB_DB"
ledger '{"id":"target","deleted_at":"2026-07-30T00:00:00Z","actor":"mk","machine":"zklw"}'
warn="$(python3 scripts/beads_apply_deletions.py --quiet 2>&1 >/dev/null)"
present target || fail "work done after the deletion record was destroyed anyway"
case "$warn" in
  *"NOT deleting"*) ;;
  *) fail "refusing to delete was silent; the operator cannot resolve what they cannot see" ;;
esac

# ─── 4: nothing else is touched ───────────────────────────────────────
# Without this, an applier that deleted everything would pass scenarios 1-3.
echo "=== 4: beads absent from the ledger are never deleted ==="
reset_db
ledger '{"id":"target","deleted_at":"2026-07-30T00:00:00Z","actor":"mk","machine":"zklw"}'
python3 scripts/beads_apply_deletions.py --quiet >/dev/null 2>&1
present keep-1 || fail "a bead not named in the ledger was deleted"
present keep-2 || fail "a bead not named in the ledger was deleted"

# ─── 5: an unusable ledger line is loud and non-zero ──────────────────
echo "=== 5: a malformed ledger line is reported, not skipped quietly ==="
reset_db
ledger '{"id":"target","deleted_at":"2026-07-30T00:00:00Z"}' 'not json at all'
out="$(python3 scripts/beads_apply_deletions.py --quiet 2>&1 >/dev/null)" && rc=0 || rc=$?
case "$out" in
  *"not a usable record"*) ;;
  *) fail "a malformed ledger line was skipped silently; a deletion could be lost" ;;
esac
[ "${rc:-0}" -ne 0 ] || fail "a malformed ledger line exited 0"

# ─── 6: the ledger is actually written ────────────────────────────────
# The regression this catches is the deletion path quietly ceasing to record
# intent, which looks identical to "no deletions happened lately".
echo "=== 6: confirming a deletion records it and exports ==="
reset_db
rm -f .beads/deletions.jsonl
git add -A >/dev/null 2>&1; git commit -q -m base >/dev/null 2>&1
bash scripts/beads-confirm-deletion.sh --delete-local target >/dev/null 2>&1 || true
[ -f .beads/deletions.jsonl ] || fail "confirming a deletion wrote no ledger entry"
grep -q '"id": "target"' .beads/deletions.jsonl || fail "the ledger entry does not name the deleted bead"
grep -q '"deleted_at"' .beads/deletions.jsonl || fail "the ledger entry carries no timestamp, so the guard cannot work"
grep -q '"target"' .beads/issues.jsonl && fail "the export still contains the deleted bead"

# ─── 7: recording a deletion that did not happen is refused ───────────
echo "=== 7: refusing to record a deletion for a bead that still exists ==="
reset_db
if bash scripts/beads-confirm-deletion.sh keep-1 >/dev/null 2>&1; then
  fail "recorded a deletion for a live bead — the other machine would act on a lie"
fi
present keep-1 || fail "the refusal deleted the bead anyway"

# ─── 8: refuses to export over another machine's unimported work ──────
# The regression: this script exports, and an export writes the local database
# over the shared file, so any bead the file has and this database lacks is
# destroyed by it. The first version called `bd export` directly and skipped
# the guard that beads-auto-export.sh applies for exactly this reason. On zklw,
# whose import had been killed mid-flight, confirming ONE deletion produced an
# export with SIX beads missing.
echo "=== 8: refusing to export when the local database is behind the file ==="
reset_db
rm -f .beads/deletions.jsonl
# The checker the script consults, stubbed to compare the file against the db.
cat > scripts/check_beads_jsonl_dolt_sync.py <<'CHECK'
import json, os, sys
db = os.environ["BD_STUB_DB"]
local = {l.split("\t")[0] for l in open(db) if l.strip()}
in_file = set()
for line in open(".beads/issues.jsonl"):
    line = line.strip()
    if line:
        in_file.add(json.loads(line)["id"])
print(json.dumps({"missing_in_dolt": sorted(in_file - local)}))
CHECK
# The file carries a bead this database has never seen — another machine's work.
{ printf '{"id":"keep-1"}\n{"id":"target"}\n{"id":"from-elsewhere"}\n'; } > .beads/issues.jsonl

if bash scripts/beads-confirm-deletion.sh --delete-local target >/dev/null 2>&1; then
  fail "exported over a bead this database had never imported"
fi
[ -f .beads/deletions.jsonl ] && fail "recorded a deletion it then refused to carry out"
grep -q 'from-elsewhere' .beads/issues.jsonl || fail "the other machine's bead was dropped from the file"
present target || fail "deleted locally before checking whether the export was safe"
rm -f scripts/check_beads_jsonl_dolt_sync.py

echo "all deletion-propagation scenarios passed"
