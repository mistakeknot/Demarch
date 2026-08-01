#!/usr/bin/env bash
# .beads/metadata.json must not travel between machines.
#
# It names which database this checkout talks to -- dolt_database, dolt_mode,
# and historically dolt_server_port, which bd itself warns "can cause
# cross-project data leakage". Those are properties of the machine, not of the
# project, and git is a channel between machines.
#
# The failure is silent and total. In the two-machine sandbox built for
# Sylveste-n6xc, a second `bd init` committed its own metadata.json -- bd init
# makes its own git commit, which is easy not to expect -- the other repo pulled
# it, and that machine started answering from a database that was not its own.
# Every isolation check in that sandbox still passed, because each was reading
# its own .beads/ PATH, and the paths were still different. Only the database
# behind them had collapsed.
#
# So every assertion here is on the connected database, by content: a bead that
# exists in exactly one of the two repositories. A path cannot answer that
# question and neither can a config file; only the database can.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SANDBOX="$(mktemp -d)"
trap 'rm -rf "$SANDBOX"' EXIT

fail() { echo "FAIL: $*" >&2; exit 1; }
command -v bd >/dev/null 2>&1 || { echo "SKIP: bd not installed"; exit 0; }

# bd's own actor, and any inherited hooks, would otherwise leak this repo's
# configuration into the sandbox.
export BEADS_ACTOR=isolation-test
HOOKS="$SANDBOX/inert-hooks"; mkdir -p "$HOOKS"

git_quiet() { git -C "$1" -c core.hooksPath="$HOOKS" "${@:2}"; }

setup_repo() {   # setup_repo <dir> <prefix>
  mkdir -p "$1"
  git -C "$1" init -q .
  git -C "$1" config user.email t@test
  git -C "$1" config user.name "$2"
  git -C "$1" config core.hooksPath "$HOOKS"
}

# A bead that exists in exactly one database is the only honest probe for
# "which database am I talking to".
sees() {         # sees <dir> <issue-id>
  (cd "$1" && bd show "$2" >/dev/null 2>&1)
}

# ─── the world both scenarios start from ──────────────────────────────
build_pair() {   # build_pair <root> <track-metadata: yes|no>
  local root="$1" track="$2"
  local remote="$root/remote.git" a="$root/A" b="$root/B"
  git init -q --bare "$remote"

  setup_repo "$a" machine-A
  (cd "$a" && bd init --prefix aaa >/dev/null 2>&1) || return 1
  if [ "$track" = "no" ]; then
    echo "metadata.json" >> "$a/.beads/.gitignore"
    git_quiet "$a" rm -q --cached .beads/metadata.json >/dev/null 2>&1 || true
  fi
  (cd "$a" && bd create "only in A" -p 3 --json >/dev/null 2>&1)
  A_ONLY="$(cd "$a" && bd list --json 2>/dev/null | python3 -c 'import json,sys; print(json.load(sys.stdin)[0]["id"])')"
  (cd "$a" && bd export --output .beads/issues.jsonl >/dev/null 2>&1)
  git_quiet "$a" add -A >/dev/null 2>&1
  git_quiet "$a" commit -q -m "A" >/dev/null 2>&1
  git_quiet "$a" branch -M main >/dev/null 2>&1
  git_quiet "$a" remote add origin "$remote"
  git_quiet "$a" push -q -u origin main

  # B is cloned from A's pushed history -- not initialised independently.
  # Two repos built from an empty remote have unrelated histories and cannot
  # merge, which quietly turns every later step into a no-op.
  git -c core.hooksPath="$HOOKS" clone -q "$remote" "$b"
  git -C "$b" config user.email t@test
  git -C "$b" config user.name machine-B
  git -C "$b" config core.hooksPath "$HOOKS"
  (cd "$b" && bd init --prefix bbb >/dev/null 2>&1) || return 1
  return 0
}

echo "=== 0: THIS repository does not track its own pointer ==="
# The scenarios below all run in a sandbox, and a sandbox cannot notice that the
# change never landed here. It did not, once: `git rm --cached` staged the
# removal and a pathspec commit naming the same file re-added it from the
# working tree, so the ignore rule shipped against a still-tracked path and did
# nothing. Both the commit and CI were satisfied.
if git -C "$ROOT" ls-files --error-unmatch .beads/metadata.json >/dev/null 2>&1; then
  fail ".beads/metadata.json is tracked in this repository; the ignore rule at
      .beads/.gitignore has no effect on a path git is already tracking.
      Fix with:  git rm --cached .beads/metadata.json  (then commit the INDEX,
      not a pathspec naming that file)"
fi
[ -f "$ROOT/.beads/metadata.json" ] || echo "    (note: no local metadata.json — bd bootstrap has not run here)"

echo "=== 1: with metadata.json tracked, B's bd init retargets A ==="
R1="$SANDBOX/tracked"; mkdir -p "$R1"
if ! build_pair "$R1" yes; then echo "    (skipped: bd init failed in the sandbox)"; exit 0; fi
A_ONLY_TRACKED="$A_ONLY"

sees "$R1/A" "$A_ONLY_TRACKED" || fail "A cannot see its own bead before anything happened"
sees "$R1/B" "$A_ONLY_TRACKED" && fail "B already answers from A's database; the sandbox is not isolated"

# bd init made its own commit in B. Push it and let A pull, exactly as a real
# pair would.
git_quiet "$R1/B" add -A >/dev/null 2>&1 || true
git_quiet "$R1/B" commit -q -m "B init" >/dev/null 2>&1 || true
git_quiet "$R1/B" push -q origin main 2>/dev/null || true
git_quiet "$R1/A" pull -q --no-rebase origin main 2>/dev/null || true

if git_quiet "$R1/A" ls-files --error-unmatch .beads/metadata.json >/dev/null 2>&1; then
  if sees "$R1/A" "$A_ONLY_TRACKED"; then
    echo "    A still sees its own bead -- the pointer travelled but did not take effect here."
    echo "    (embedded mode resolves the database relative to .beads/; the server-mode"
    echo "     port is the field that actually redirects. Recorded, not asserted.)"
  else
    echo "    reproduced: after pulling B's metadata.json, A can no longer see its own bead"
  fi
else
  fail "metadata.json was supposed to be tracked in this scenario"
fi

echo "=== 2: untracked, a pull cannot touch the local pointer ==="
R2="$SANDBOX/untracked"; mkdir -p "$R2"
build_pair "$R2" no || fail "could not build the untracked pair"
A_ONLY_UNTRACKED="$A_ONLY"

git_quiet "$R2/A" ls-files --error-unmatch .beads/metadata.json >/dev/null 2>&1 \
  && fail "metadata.json is still tracked; the change under test was not applied"

before="$(cat "$R2/A/.beads/metadata.json")"
git_quiet "$R2/B" add -A >/dev/null 2>&1 || true
git_quiet "$R2/B" commit -q -m "B init" >/dev/null 2>&1 || true
git_quiet "$R2/B" push -q origin main 2>/dev/null || true
git_quiet "$R2/A" pull -q --no-rebase origin main 2>/dev/null || true
after="$(cat "$R2/A/.beads/metadata.json")"

[ "$before" = "$after" ] || fail "a pull rewrote A's metadata.json even though it is untracked"

# The assertion that means something: A still answers from A's database.
sees "$R2/A" "$A_ONLY_UNTRACKED" || fail "A lost its own bead after pulling from B"
sees "$R2/B" "$A_ONLY_UNTRACKED" && fail "B answers from A's database -- the two collapsed into one"

echo "=== 3: the two databases stay distinct under content, not path ==="
# Non-vacuity for scenario 2. If bd were failing outright, every `sees` above
# would answer no and the test would pass while proving nothing.
(cd "$R2/B" && bd create "only in B" -p 3 >/dev/null 2>&1)
B_ONLY="$(cd "$R2/B" && bd list --json 2>/dev/null | python3 -c 'import json,sys; print(json.load(sys.stdin)[0]["id"])')"
[ -n "$B_ONLY" ] || fail "could not create a bead in B; the previous checks were vacuous"
sees "$R2/B" "$B_ONLY" || fail "B cannot see the bead it just created"
sees "$R2/A" "$B_ONLY" && fail "a bead created in B is visible in A without any sync"

echo "=== 4: a fresh clone can still bring bd up without a committed pointer ==="
# The cost of untracking: metadata.json is not in the clone, so something must
# regenerate it. If that needed hand-authoring, untracking would be trading one
# hazard for a worse one.
FRESH="$SANDBOX/fresh"
git -c core.hooksPath="$HOOKS" clone -q "$R2/remote.git" "$FRESH"
git -C "$FRESH" config core.hooksPath "$HOOKS"
[ -f "$FRESH/.beads/metadata.json" ] && fail "the clone carried a metadata.json; it is still tracked"
[ -f "$FRESH/.beads/issues.jsonl" ] || fail "the clone has no issues.jsonl; nothing to recover from"

(cd "$FRESH" && bd bootstrap >/dev/null 2>&1) || (cd "$FRESH" && bd init --prefix aaa >/dev/null 2>&1) \
  || fail "neither bd bootstrap nor bd init could bring up a fresh clone"
[ -f "$FRESH/.beads/metadata.json" ] || fail "bringing up the clone did not produce a metadata.json"
(cd "$FRESH" && bd import .beads/issues.jsonl >/dev/null 2>&1) || fail "the fresh clone could not import the tracked JSONL"
sees "$FRESH" "$A_ONLY_UNTRACKED" || fail "the fresh clone cannot see a bead the tracked JSONL carries"

echo "all metadata-isolation scenarios passed"
