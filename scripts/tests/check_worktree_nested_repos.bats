#!/usr/bin/env bats
# n2ma element 4 — nested-repo doctor check.
#
# check-worktree-nested-repos.sh must: be silent (exit 0) in the main checkout,
# and WARN (exit 1) with the absent nested repos listed when run from a ROOT-repo
# worktree. See docs/guide-worktree-first-coordination.md §5, §7.

setup() {
  REPO_ROOT="$(git rev-parse --show-toplevel)"
  CHECK="$REPO_ROOT/scripts/check-worktree-nested-repos.sh"
  [ -x "$CHECK" ] || skip "check script not present/executable"
  # Only meaningful from the main root repo (has interverse/ + core/).
  [ -d "$REPO_ROOT/interverse" ] && [ -d "$REPO_ROOT/core" ] || skip "not the root repo"
  WT_REL=".claude/worktrees/n2ma-doctor-bats-$$"
  WT="$REPO_ROOT/$WT_REL"
}

teardown() {
  [ -n "${WT:-}" ] || return 0
  git -C "$REPO_ROOT" worktree remove "$WT" --force 2>/dev/null || true
  git -C "$REPO_ROOT" branch -D "n2ma-doctor-bats-$$" 2>/dev/null || true
}

@test "silent and exit 0 in the main checkout" {
  run bash -c "cd '$REPO_ROOT' && '$CHECK'"
  [ "$status" -eq 0 ]
  [ -z "$output" ]
}

@test "json reports in_worktree:false in the main checkout" {
  run bash -c "cd '$REPO_ROOT' && '$CHECK' --json"
  [ "$status" -eq 0 ]
  [[ "$output" == *'"in_worktree":false'* ]]
}

@test "warns and exits 1 from a root-repo worktree, listing absent nested repos" {
  git -C "$REPO_ROOT" worktree add "$WT" -b "n2ma-doctor-bats-$$" >/dev/null 2>&1
  [ -d "$WT" ]

  run bash -c "cd '$WT' && WORKTREE_CHECK_CWD='$WT' '$CHECK'"
  [ "$status" -eq 1 ]
  [[ "$output" == *"ROOT-repo worktree"* ]]
  [[ "$output" == *"nested repos are ABSENT"* ]]
  [[ "$output" == *"$REPO_ROOT"* ]]

  run bash -c "cd '$WT' && WORKTREE_CHECK_CWD='$WT' '$CHECK' --json"
  [ "$status" -eq 1 ]
  [[ "$output" == *'"root_repo":true'* ]]
  [[ "$output" == *'"status":"warn"'* ]]
  [[ "$output" == *'core/intercore'* ]]
}
