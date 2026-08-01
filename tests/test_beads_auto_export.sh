#!/usr/bin/env bash
# Ordering tests for scripts/beads-auto-export.sh.
#
# The script creates a git commit from inside post-commit. That is the risky
# part, and the failure modes are all about ordering rather than logic:
# recursing forever, widening someone else's commit, committing nothing, or
# firing in the middle of a rebase. Each gets a scenario here.
#
# Runs entirely in a scratch repo against a stubbed `bd`, so it never reads or
# writes the real Dolt database.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SANDBOX="$(mktemp -d)"
trap 'rm -rf "$SANDBOX"' EXIT

fail() { echo "FAIL: $*" >&2; exit 1; }

# ─── fixture ──────────────────────────────────────────────────────────

mkdir -p "$SANDBOX/scripts" "$SANDBOX/.beads" "$SANDBOX/bin"
cp "$ROOT/scripts/beads-auto-export.sh" "$SANDBOX/scripts/"
cp "$ROOT/scripts/check_beads_jsonl_dolt_sync.py" "$SANDBOX/scripts/"

# Stub bd. DOLT_IDS drives what the "database" contains; `bd export` writes
# exactly those ids, `bd sql` lists them. That is the whole contract the
# auto-export script depends on.
cat > "$SANDBOX/bin/bd" <<'STUB'
#!/usr/bin/env bash
case "${1:-}" in
  sql)
    echo "id"
    echo "----"
    for id in $DOLT_IDS; do echo "$id"; done
    ;;
  export)
    out="${3:-.beads/issues.jsonl}"
    : > "$out"
    for id in $DOLT_IDS; do printf '{"id":"%s","title":"t"}\n' "$id" >> "$out"; done
    echo "Exported to $out"
    ;;
esac
exit 0
STUB
chmod +x "$SANDBOX/bin/bd"
export PATH="$SANDBOX/bin:$PATH"

cd "$SANDBOX"
git init -q && git config user.email t@t.invalid && git config user.name t
git config commit.gpgsign false

export DOLT_IDS="a b"
bd export --output .beads/issues.jsonl >/dev/null
echo seed > other.txt
git add -A && git commit -q -m "seed"

# Install the hook only now, so the seed commit does not trigger it.
mkdir -p .githooks
cat > .githooks/post-commit <<EOF
#!/bin/sh
"$SANDBOX/scripts/beads-auto-export.sh" || true
EOF
chmod +x .githooks/post-commit
git config core.hooksPath .githooks

jsonl_ids() { sed -n 's/.*"id":"\([^"]*\)".*/\1/p' .beads/issues.jsonl | sort | tr '\n' ' '; }

# ─── 1. a bead change is exported and committed on its own ────────────

echo "=== 1: Dolt ahead -> dedicated export commit, unrelated commit stays atomic ==="
export DOLT_IDS="a b c"
echo work > other.txt
git commit -q -m "unrelated work" -- other.txt

head_msg="$(git log -1 --format=%s)"
[ "$head_msg" = "beads: sync export (automated)" ] \
  || fail "expected an auto export commit at HEAD, got: $head_msg"

files="$(git show --name-only --format= HEAD | tr -d ' ')"
[ "$files" = ".beads/issues.jsonl" ] \
  || fail "auto commit touched more than the export: $files"

prev="$(git show --name-only --format= HEAD~1 | tr -d ' ')"
[ "$prev" = "other.txt" ] \
  || fail "the unrelated commit was widened to: $prev (must stay atomic)"

[ "$(jsonl_ids)" = "a b c " ] || fail "export content wrong: $(jsonl_ids)"
echo "PASS"

# ─── 2. no bead change -> no commit at all ────────────────────────────

echo "=== 2: nothing to export -> no commit, and no empty commit ==="
before="$(git rev-parse HEAD)"
echo work2 > other.txt
git commit -q -m "more work" -- other.txt
after_msg="$(git log -1 --format=%s)"
[ "$after_msg" = "more work" ] \
  || fail "an export commit was created with nothing to export: $after_msg"
[ "$(git rev-list --count "$before"..HEAD)" = "1" ] \
  || fail "expected exactly one new commit"
echo "PASS"

# ─── 3. re-entrancy ───────────────────────────────────────────────────

echo "=== 3: the export commit does not trigger another export commit ==="
export DOLT_IDS="a b c d"
echo work3 > other.txt
git commit -q -m "work3" -- other.txt
# Exactly two commits: the work, then one export. Not three, not a loop.
[ "$(git log -2 --format=%s | tr '\n' '|')" = "beads: sync export (automated)|work3|" ] \
  || fail "unexpected history: $(git log -3 --format=%s | tr '\n' '|')"
echo "PASS"

# ─── 4. JSONL ahead of Dolt -> refuse, never export ───────────────────

echo "=== 4: issues that exist only in the JSONL are never exported away ==="
# Simulate a pull that brought another machine's issue, not yet imported.
printf '{"id":"remote-only","title":"from zklw"}\n' >> .beads/issues.jsonl
git add .beads/issues.jsonl
git -c core.hooksPath=/dev/null commit -q -m "pulled remote issue"
echo work4 > other.txt
git commit -q -m "work4" -- other.txt 2>/dev/null

grep -q "remote-only" .beads/issues.jsonl \
  || fail "auto-export deleted an issue that existed only in the JSONL"
[ "$(git log -1 --format=%s)" = "work4" ] \
  || fail "auto-export committed despite an unsafe state"
echo "PASS"

# ─── 5. mid-sequence git operations are left alone ────────────────────

echo "=== 5: no commit is inserted while git is mid-sequence ==="
# Clear the unsafe state from scenario 4 first.
bd export --output .beads/issues.jsonl >/dev/null
git add .beads/issues.jsonl
git -c core.hooksPath=/dev/null commit -q -m "resync"

# Invoke the script directly rather than through a commit: git refuses a
# partial commit while MERGE_HEAD exists, so the commit that would trigger the
# hook cannot be made in this state anyway. What matters is that the script
# declines when it IS reached — via `git commit -a`, an amend, or a
# cherry-pick, all of which do fire post-commit mid-sequence.
export DOLT_IDS="a b c d e"
before="$(git rev-parse HEAD)"
touch "$(git rev-parse --git-dir)/MERGE_HEAD"
bash "$SANDBOX/scripts/beads-auto-export.sh" || true
rm -f "$(git rev-parse --git-dir)/MERGE_HEAD"
[ "$(git rev-parse HEAD)" = "$before" ] \
  || fail "an export commit was created while MERGE_HEAD was present"
git diff --quiet -- .beads/issues.jsonl \
  || fail "the export ran mid-merge and dirtied the working tree"
echo "PASS"

# Same guard, via CHERRY_PICK_HEAD, which post-commit genuinely does reach.
before="$(git rev-parse HEAD)"
touch "$(git rev-parse --git-dir)/CHERRY_PICK_HEAD"
bash "$SANDBOX/scripts/beads-auto-export.sh" || true
rm -f "$(git rev-parse --git-dir)/CHERRY_PICK_HEAD"
[ "$(git rev-parse HEAD)" = "$before" ] \
  || fail "an export commit was created during a cherry-pick"
echo "PASS"

# ─── 6. opt-out ───────────────────────────────────────────────────────

echo "=== 6: BEADS_NO_AUTO_EXPORT=1 disables it ==="
echo work6 > other.txt
BEADS_NO_AUTO_EXPORT=1 git commit -q -m "work6" -- other.txt
[ "$(git log -1 --format=%s)" = "work6" ] || fail "opt-out ignored"
echo "PASS"

# ─── 7. an uncommitted hand-export is still committed ─────────────────

echo "=== 7: a hand-run export that was never committed gets committed ==="
# The probe compares the working tree to Dolt, so after a manual export it
# reports "in sync" — while HEAD still holds the stale copy, and only HEAD is
# pushed. Committing on the probe alone leaves that change stranded forever.
export DOLT_IDS="a b c d e f"
bd export --output .beads/issues.jsonl >/dev/null   # by hand, not committed
git diff --quiet HEAD -- .beads/issues.jsonl && fail "fixture wrong: expected an uncommitted export"
echo work7 > other.txt
git commit -q -m "work7" -- other.txt
[ "$(git log -1 --format=%s)" = "beads: sync export (automated)" ] \
  || fail "an uncommitted export was left stranded: $(git log -1 --format=%s)"
git diff --quiet HEAD -- .beads/issues.jsonl \
  || fail "the export is still uncommitted after the hook ran"
echo "PASS"

# ─── 8. a broken probe complains instead of going quiet ───────────────

echo "=== 8: a failing probe warns loudly and exports nothing ==="
# The probe is the only thing standing between "beads changed" and "the export
# is committed". When it breaks, every commit still succeeds, so a silent skip
# looks exactly like a repo with no bead changes — which is how the mechanism
# this replaced managed to report success while going two days stale.
cat > "$SANDBOX/scripts/check_beads_jsonl_dolt_sync.py" <<'BROKEN'
import sys
print("simulated: bd sql failed (schema mismatch)", file=sys.stderr)
sys.exit(2)
BROKEN

export DOLT_IDS="a b c d e f g"
before="$(git rev-parse HEAD)"
echo work8 > other.txt
warn="$(git commit -q -m "work8" -- other.txt 2>&1 >/dev/null)"

[ "$(git log -1 --format=%s)" = "work8" ] \
  || fail "a broken probe still produced an export commit: $(git log -1 --format=%s)"
[ "$(git rev-list --count "$before"..HEAD)" = "1" ] \
  || fail "expected exactly one commit when the probe is broken"
case "$warn" in
  *"NOT being exported"*) ;;
  *) fail "a broken probe was silent; stderr was: $warn" ;;
esac
case "$warn" in
  *"schema mismatch"*) ;;
  *) fail "the underlying error was not surfaced; stderr was: $warn" ;;
esac
echo "PASS"

echo "PASS: beads-auto-export ordering"
