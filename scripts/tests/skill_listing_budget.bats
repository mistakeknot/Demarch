#!/usr/bin/env bats
# Tests for check-skill-listing-budget.sh — the eager skill-listing byte gate.

SCRIPT="$BATS_TEST_DIRNAME/../check-skill-listing-budget.sh"

# Build a hermetic fixture plugins root with two SKILL.md files whose
# frontmatter descriptions have known byte sizes, so the gate's totals are
# deterministic and independent of the real ~/.claude/plugins.
setup() {
    FIXTURE="$BATS_TEST_TMPDIR/plugins"
    mkdir -p "$FIXTURE/alpha/skills/one" "$FIXTURE/beta/skills/two"
    # description: "AAAA...10" → 10 bytes of value
    cat >"$FIXTURE/alpha/skills/one/SKILL.md" <<'EOF'
---
name: one
description: AAAAAAAAAA
---
body
EOF
    # description: 20 bytes
    cat >"$FIXTURE/beta/skills/two/SKILL.md" <<'EOF'
---
name: two
description: BBBBBBBBBBBBBBBBBBBB
---
body
EOF
    export SKILL_PLUGINS_ROOT="$FIXTURE"
}

@test "within budget: total under budget exits 0" {
    SKILL_LISTING_BUDGET_BYTES=1000 run "$SCRIPT" --json
    [ "$status" -eq 0 ]
    [[ "$output" == *'"status":"ok"'* ]]
}

@test "over budget: total over budget exits 1" {
    SKILL_LISTING_BUDGET_BYTES=5 run "$SCRIPT"
    [ "$status" -eq 1 ]
    [[ "$output" == *"OVER BUDGET"* ]]
}

@test "json output reports total, budget, and status" {
    SKILL_LISTING_BUDGET_BYTES=1000 run "$SCRIPT" --json
    [ "$status" -eq 0 ]
    [[ "$output" == *'"total_bytes":'* ]]
    [[ "$output" == *'"budget_bytes":1000'* ]]
    [[ "$output" == *'"approx_tokens":'* ]]
}

@test "total reflects summed description bytes from fixtures" {
    # alpha=10 + beta=20 = 30 bytes
    SKILL_LISTING_BUDGET_BYTES=1000 run "$SCRIPT" --json
    [ "$status" -eq 0 ]
    [[ "$output" == *'"total_bytes":30'* ]]
}

@test "boundary: total exactly at budget passes (<=)" {
    SKILL_LISTING_BUDGET_BYTES=30 run "$SCRIPT"
    [ "$status" -eq 0 ]
}

@test "boundary: one byte under total fails" {
    SKILL_LISTING_BUDGET_BYTES=29 run "$SCRIPT"
    [ "$status" -eq 1 ]
}

@test "missing plugins root exits 2" {
    SKILL_PLUGINS_ROOT="/nonexistent-skill-budget-root" run "$SCRIPT"
    [ "$status" -eq 2 ]
    [[ "$output" == *"plugins root not found"* ]]
}

@test "unknown argument exits 2" {
    run "$SCRIPT" --bogus
    [ "$status" -eq 2 ]
}

@test "help flag exits 0 and prints usage" {
    run "$SCRIPT" --help
    [ "$status" -eq 0 ]
    [[ "$output" == *"check-skill-listing-budget"* ]]
}
