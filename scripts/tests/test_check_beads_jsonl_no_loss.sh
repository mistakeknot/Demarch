#!/usr/bin/env bash
# Exercise the no-loss guard, including a replay of the 2026-08-04 incident.
#
# Runs against a throwaway git repo. Nothing here touches the real .beads.
set -uo pipefail
CHECK="${1:-$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." >/dev/null 2>&1 && pwd -P)/check_beads_jsonl_no_loss.py}"
T=$(mktemp -d); trap 'rm -rf "$T"' EXIT
pass=0; fail=0
ck() { if [[ "$2" == "$1" ]]; then printf '  PASS  %s\n' "$3"; pass=$((pass+1));
       else printf '  FAIL  %s (want rc=%s, got rc=%s)\n' "$3" "$1" "$2"; fail=$((fail+1)); fi }

mkjsonl() { # mkjsonl <file> <prefix> <n>
  : > "$2.tmp"
  for i in $(seq 1 "$3"); do printf '{"id":"%s-%04d","status":"open"}\n' "$2" "$i"; done > "$1"
}

git init -q "$T/repo"; cd "$T/repo"
git config user.email t@t; git config user.name t; git config commit.gpgsign false
mkdir -p .beads scripts
cp "$CHECK" scripts/check_beads_jsonl_no_loss.py
mkjsonl .beads/issues.jsonl sylveste 500
git add -A; git commit -qm seed

run() { # run <staged-content-file> -> rc
  git show :'.beads/issues.jsonl' > "$T/staged.jsonl" 2>/dev/null || cp "$1" "$T/staged.jsonl"
  python3 scripts/check_beads_jsonl_no_loss.py --staged-file "$1" >"$T/out.txt" 2>&1
  echo $?
}

# --- 1. the incident: a foreign database exported over this file --------------
mkjsonl "$T/foreign.jsonl" mk 458
rc=$(run "$T/foreign.jsonl")
ck "1" "$rc" "foreign export (458 mk-* over 500 sylveste-*) is REFUSED"
grep -q "WRONG DIRECTORY" "$T/out.txt" \
  && { echo "  PASS  names the wrong-directory cause"; pass=$((pass+1)); } \
  || { echo "  FAIL  message did not name the cause"; fail=$((fail+1)); }

# --- 2. a legitimate superset export passes ----------------------------------
mkjsonl "$T/superset.jsonl" sylveste 504
rc=$(run "$T/superset.jsonl")
ck "0" "$rc" "superset export (500 -> 504, nothing dropped) passes"

# --- 3. an identical export passes -------------------------------------------
cp .beads/issues.jsonl "$T/same.jsonl"
rc=$(run "$T/same.jsonl")
ck "0" "$rc" "unchanged export passes"

# --- 4. dropping ONE id is still a refusal (not a percentage threshold) ------
head -n 499 .beads/issues.jsonl > "$T/oneless.jsonl"
rc=$(run "$T/oneless.jsonl")
ck "1" "$rc" "dropping a single id is refused (no silent tolerance band)"

# --- 5. ...unless it is recorded as a deliberate deletion --------------------
printf '{"id":"sylveste-0500"}\n' > .beads/deletions.jsonl
rc=$(run "$T/oneless.jsonl")
ck "0" "$rc" "the same drop passes once recorded in .beads/deletions.jsonl"
rm -f .beads/deletions.jsonl

# --- 6. explicit override ----------------------------------------------------
rc=$(BEADS_ALLOW_JSONL_SHRINK=1 python3 scripts/check_beads_jsonl_no_loss.py \
       --staged-file "$T/oneless.jsonl" >/dev/null 2>&1; echo $?)
ck "0" "$rc" "BEADS_ALLOW_JSONL_SHRINK=1 overrides deliberately"

# --- 7. unparseable staged content is CANNOT ASSESS, not 'nothing lost' -----
printf 'this is not json\n' > "$T/garbage.jsonl"
rc=$(run "$T/garbage.jsonl")
ck "2" "$rc" "unparseable staged content => exit 2 (blocks), not 0"

# --- 8. an EMPTY staged file is a total loss, not a clean pass --------------
: > "$T/empty.jsonl"
rc=$(run "$T/empty.jsonl")
ck "1" "$rc" "empty staged export => refused (0 ids is not 'no change')"

# --- 9. missing staged file is CANNOT ASSESS -------------------------------
rc=$(python3 scripts/check_beads_jsonl_no_loss.py --staged-file "$T/nope.jsonl" >/dev/null 2>&1; echo $?)
ck "2" "$rc" "unreadable staged file => exit 2"

# --- 10. end to end: the hook actually blocks a real commit ----------------
cat > .git/hooks/pre-commit <<'EOF'
#!/usr/bin/env sh
_s=$(git diff --cached --name-only 2>/dev/null || true)
case "$_s" in
  *".beads/issues.jsonl"*)
    f=$(mktemp); git show :'.beads/issues.jsonl' > "$f" 2>/dev/null
    python3 scripts/check_beads_jsonl_no_loss.py --staged-file "$f"; rc=$?
    rm -f "$f"; [ $rc -ne 0 ] && exit $rc ;;
esac
exit 0
EOF
chmod +x .git/hooks/pre-commit
cp "$T/foreign.jsonl" .beads/issues.jsonl
git add .beads/issues.jsonl
git commit -qm "replay the incident" >"$T/commit.txt" 2>&1; crc=$?
ck "1" "$([[ $crc -ne 0 ]] && echo 1 || echo 0)" "a real commit of the foreign export is BLOCKED"
ck "500" "$(git show HEAD:.beads/issues.jsonl | wc -l | tr -d ' ')" "HEAD still holds the original 500 ids"

echo
echo "no-loss guard: $pass passed, $fail failed"
[[ "$fail" -eq 0 ]] || exit 1
