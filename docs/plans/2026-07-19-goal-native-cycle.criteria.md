## Acceptance Criteria

1. Full intercore suite green, including the new goal package.
   ```check
   cd /Users/sma/projects/Sylveste/core/intercore && go test ./...
   ```
2. Exclusive fenced close demonstrated under the race detector.
   ```check
   cd /Users/sma/projects/Sylveste/core/intercore && go test -race ./internal/goal/ -run 'TwoSessionRace|Acquire|Finish'
   ```
3. Condition lint gates minting: valid conditions exit 0, undemonstrable ones exit 1.
   ```check
   cd /Users/sma/projects/Sylveste/core/intercore && go build -o /tmp/ic-ac ./cmd/ic && /tmp/ic-ac goal lint-condition --text="tests pass, or stop after 5 turns" && ! /tmp/ic-ac goal lint-condition --text="make it feel nice"
   ```
4. DefaultChain untouched: legacy 9-phase chain still resolves for nil-Phases runs.
   ```check
   cd /Users/sma/projects/Sylveste/core/intercore && go test ./internal/phase/ -run 'Chain|Resolve' && grep -A11 "var DefaultChain" pkg/phase/phase.go | grep -q Strategized
   ```
5. clavain-cli suite green with goal-mint + blast-radius bump.
   ```check
   cd /Users/sma/projects/Sylveste/os/Clavain/cmd/clavain-cli && go test ./...
   ```
6. Entity-backed cadence hook is tested and fail-open.
   ```check
   cd /Users/sma/projects/Sylveste/os/Clavain && bats tests/shell/goal_audit.bats
   ```
7. Sideband envelope matches the interline reader contract.
   ```check
   cd /Users/sma/projects/Sylveste/os/Clavain/cmd/clavain-cli && go test -run Sideband ./...
   ```
8. Ritual + wiring docs exist and reference each other.
   ```check
   grep -q "lint-condition" /Users/sma/projects/Sylveste/os/Clavain/commands/goal-form.md && grep -q "goal-form" /Users/sma/projects/Sylveste/os/Clavain/commands/route.md && grep -q "goal audit" /Users/sma/projects/Sylveste/os/Clavain/commands/next-goal.md
   ```
9. E2E lifecycle green.
   ```check
   cd /Users/sma/projects/Sylveste/core/intercore && go test ./internal/goal/ -run E2E
   ```

