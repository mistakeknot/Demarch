#!/usr/bin/env bash
# Tests for scripts/beads-import-merged.sh.
#
# The script exists to make the post-merge import cheap: a full `bd import` of
# .beads/issues.jsonl is ~49s and would run on every pull. It hands bd only the
# rows the merge changed.
#
# Cheap is easy to fake. A filter that imports NOTHING is faster still, and
# every timing check passes while another machine's work never lands — the
# invisible failure this entire path exists to prevent. So every scenario here
# asserts on what bd was actually given, never on whether the script succeeded.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SANDBOX="$(mktemp -d)"
trap 'rm -rf "$SANDBOX"' EXIT

fail() { echo "FAIL: $*" >&2; exit 1; }

mkdir -p "$SANDBOX/scripts" "$SANDBOX/.beads" "$SANDBOX/bin"
cp "$ROOT/scripts/beads-import-merged.sh" "$SANDBOX/scripts/"
chmod +x "$SANDBOX/scripts/beads-import-merged.sh"

# Stub bd: copy whatever file it was asked to import to a known place, so each
# scenario can assert on the exact batch rather than on an exit code.
cat > "$SANDBOX/bin/bd" <<'STUB'
#!/usr/bin/env bash
if [ "${1:-}" = import ]; then
  cp "$2" "$IMPORTED_TO"
  echo "Imported $(grep -c . "$2") issues"
fi
STUB
chmod +x "$SANDBOX/bin/bd"
export PATH="$SANDBOX/bin:$PATH"
export IMPORTED_TO="$SANDBOX/imported.jsonl"

cd "$SANDBOX"
git init -q .
git config user.email t@test; git config user.name tester

row() { printf '{"id":"%s","updated_at":"%s"}\n' "$1" "$2"; }

{ row a 2026-07-01T00:00:00Z; row b 2026-07-01T00:00:00Z; } > .beads/issues.jsonl
git add -A >/dev/null; git commit -q -m base
base="$(git rev-parse HEAD)"

imported_ids() { grep -o '"id":"[^"]*"' "$IMPORTED_TO" 2>/dev/null | sed 's/.*:"//;s/"//' | sort | tr '\n' ' '; }
reset_import() { rm -f "$IMPORTED_TO"; }

# ─── 1: only the added row is imported ────────────────────────────────
echo "=== 1: a merge that adds a row imports that row, and only it ==="
reset_import
{ row a 2026-07-01T00:00:00Z; row b 2026-07-01T00:00:00Z; row c 2026-08-01T00:00:00Z; } > .beads/issues.jsonl
git commit -q -m "add c" -- .beads/issues.jsonl
bash scripts/beads-import-merged.sh "$base" >/dev/null 2>&1
[ -f "$IMPORTED_TO" ] || fail "nothing was imported; another machine's bead would be invisible"
[ "$(imported_ids)" = "c " ] || fail "expected only 'c', got '$(imported_ids)'"

# ─── 2: an untouched JSONL imports nothing at all ─────────────────────
echo "=== 2: a merge that does not touch bead state calls bd not at all ==="
reset_import
prev="$(git rev-parse HEAD)"
echo "unrelated" > README.md
git add README.md >/dev/null; git commit -q -m "unrelated change"
bash scripts/beads-import-merged.sh "$prev" >/dev/null 2>&1
[ -f "$IMPORTED_TO" ] && fail "imported on a merge that changed no bead state"

# ─── 3: a modified row imports the NEW text ───────────────────────────
echo "=== 3: an updated row is imported as its new version ==="
reset_import
prev="$(git rev-parse HEAD)"
{ row a 2026-07-01T00:00:00Z; row b 2026-09-09T00:00:00Z; row c 2026-08-01T00:00:00Z; } > .beads/issues.jsonl
git commit -q -m "update b" -- .beads/issues.jsonl
bash scripts/beads-import-merged.sh "$prev" >/dev/null 2>&1
[ "$(imported_ids)" = "b " ] || fail "expected only 'b', got '$(imported_ids)'"
grep -q '2026-09-09' "$IMPORTED_TO" || fail "imported the pre-merge text of the row, not the merged one"

# ─── 4: a removed row is not an import's business ─────────────────────
echo "=== 4: a row that only disappears imports nothing ==="
reset_import
prev="$(git rev-parse HEAD)"
{ row a 2026-07-01T00:00:00Z; row b 2026-09-09T00:00:00Z; } > .beads/issues.jsonl
git commit -q -m "drop c" -- .beads/issues.jsonl
bash scripts/beads-import-merged.sh "$prev" >/dev/null 2>&1
[ -f "$IMPORTED_TO" ] && fail "a deletion was fed to the importer; deletions travel through the ledger"

# ─── 5: unknown ref falls back to the whole file ──────────────────────
# Slow beats wrong. If the script cannot tell what changed and imports nothing,
# a machine's work silently never arrives.
echo "=== 5: an unresolvable before-ref imports everything ==="
reset_import
bash scripts/beads-import-merged.sh "nosuchref-deadbeef" >/dev/null 2>&1
[ -f "$IMPORTED_TO" ] || fail "imported nothing when it could not determine the diff"
[ "$(imported_ids)" = "a b " ] || fail "expected the whole file, got '$(imported_ids)'"

# ─── 6: the file header is never mistaken for a row ───────────────────
echo "=== 6: the diff's '+++ b/...' header is not imported as a bead ==="
grep -q '^+++' "$IMPORTED_TO" 2>/dev/null && fail "a diff header leaked into the import batch"

echo "all import-merged scenarios passed"
