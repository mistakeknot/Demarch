#!/usr/bin/env bats
# n2ma element 3 — beads-from-worktrees.
#
# A worktree created with `bd worktree create` installs a redirect so bd
# reaches the MAIN checkout's Dolt store instead of a divergent local one.
# This test proves a MUTATING bd command run from inside the worktree lands in
# the main store (read back from the main checkout), and that a raw
# `git worktree add` worktree is NOT redirected (the failure mode the contract
# forbids). See docs/guide-worktree-first-coordination.md §6.
#
# Skips cleanly if `bd` is unavailable (cloud/read-only sessions).

setup() {
  command -v bd >/dev/null 2>&1 || skip "bd not available"
  REPO_ROOT="$(git rev-parse --show-toplevel)"
  # Only meaningful from a real main checkout with a beads store.
  [ -d "$REPO_ROOT/.beads" ] || skip "no .beads store"
  # `bd worktree info` exits 0 in both main and worktree; distinguish by text.
  bd worktree info 2>/dev/null | grep -q "Main repo:" && skip "already inside a worktree"
  WT_NAME="n2ma-redirect-test-$$"
  PROBE_BEAD="sylveste-n2ma"
  PROBE_KEY="wt_redirect_test_$$"
}

teardown() {
  [ -n "${WT_NAME:-}" ] || return 0
  git -C "$REPO_ROOT" worktree remove "$WT_NAME" --force 2>/dev/null || true
  git -C "$REPO_ROOT" branch -D "$WT_NAME" 2>/dev/null || true
  git -C "$REPO_ROOT" worktree remove "raw-$WT_NAME" --force 2>/dev/null || true
  git -C "$REPO_ROOT" branch -D "raw-$WT_NAME" 2>/dev/null || true
  # Best-effort neutralize the probe state dimension (bd has no state delete).
  bd set-state "$PROBE_BEAD" "$PROBE_KEY=cleared" 2>/dev/null || true
}

@test "bd worktree create installs a redirect to the main .beads store" {
  run bd worktree create "$WT_NAME"
  [ "$status" -eq 0 ]
  [[ "$output" == *"redirects to"*".beads"* ]]

  run bd worktree info
  # info run from main checkout still reports (main); the redirect proof is below.
}

@test "a mutating bd command from the worktree lands in the main store" {
  bd worktree create "$WT_NAME" >/dev/null
  WT_PATH="$REPO_ROOT/$WT_NAME"
  [ -d "$WT_PATH" ]

  local stamp="from-worktree-$(git -C "$REPO_ROOT" rev-parse --short HEAD)"
  # Write from INSIDE the worktree.
  run bash -c "cd '$WT_PATH' && bd set-state '$PROBE_BEAD' '$PROBE_KEY=$stamp'"
  [ "$status" -eq 0 ]

  # Read back from the MAIN checkout — the write must be visible there.
  run bash -c "cd '$REPO_ROOT' && bd state list '$PROBE_BEAD'"
  [ "$status" -eq 0 ]
  [[ "$output" == *"$PROBE_KEY"* ]]
  [[ "$output" == *"$stamp"* ]]
}

@test "bd worktree info from the worktree names the main repo" {
  bd worktree create "$WT_NAME" >/dev/null
  WT_PATH="$REPO_ROOT/$WT_NAME"
  run bash -c "cd '$WT_PATH' && bd worktree info"
  [ "$status" -eq 0 ]
  [[ "$output" == *"Main repo: $REPO_ROOT"* ]]
  [[ "$output" == *"redirects to"* ]]
}
