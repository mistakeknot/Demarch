# Reinvented Wheels Audit — 2026-02-22

Audit of the Demarch monorepo for cases where bespoke code reinvents functionality
available in established, well-maintained open-source tools.

Scope: `os/clavain/` (11,417 lines across 30 scripts) and `interverse/` (33+ plugins).

## Priority 1 — High Impact

### 1. YAML Parsing State Machine → `yq`
- **File:** `os/clavain/scripts/lib-routing.sh` (680 lines)
- **What:** Hand-rolled bash YAML parser using regex state machine. Tracks 3 levels
  of nesting (subagents, dispatch, complexity), maintains state variables
  (`section`, `subsection`, `current_phase`), extracts values with `${BASH_REMATCH[]}`.
- **Replace with:** `yq` (already installed at `~/.local/bin/yq`)
- **Reduction:** ~680 → ~100 lines (yq queries + bash array assignment)
- **Interface change:** Partial — functions consuming parsed data keep their signatures;
  only the internal parsing changes. Config file format stays the same.
- **Risk:** Low — yq is battle-tested, config structure is well-defined YAML.

### 2. Duplicated Version Bump Scripts → shared `interbump.sh`
- **Files:** 15+ copies of `scripts/bump-version.sh` across interverse plugins
  (interdoc, interflux, interfluence, intercraft, interdev, ...)
- **What:** Each plugin independently implements SemVer bump: parse `plugin.json`,
  increment version, git commit/push. ~30 lines each = ~450 lines total.
- **Replace with:** `scripts/interbump.sh` (already exists in monorepo root!)
- **Reduction:** ~450 → 0 lines (delete all copies, use existing shared script)
- **Interface change:** Drop-in — interbump.sh already handles the same workflow.
- **Risk:** None — the shared script exists and works.

### 3. Link Rewriting Engine → `ast-grep` + structured tools
- **File:** `interverse/interdoc/scripts/drift-fix.sh` (382 lines)
- **What:** Custom link tracking/rewriting using sed/awk/grep chains. Detects
  renamed/deleted AGENTS.md files via git history, rewrites links, detects collisions.
- **Replace with:** `ast-grep` for structural search + `gomplate` for safe rewriting
- **Reduction:** ~382 → ~250 lines (~35% reduction)
- **Interface change:** Partial — output format stays the same, internals change.
- **Risk:** Medium — link rewriting has edge cases; needs thorough testing.

## Priority 2 — Medium Impact

### 4. Sprint Phase FSM → Lookup Table
- **File:** `os/clavain/hooks/lib-sprint.sh` (~200 lines of 1,270 total)
- **What:** 20+ `elif` branches mapping phase names to next steps:
  ```bash
  if [[ "$phase" == "brainstorm" ]]; then echo "discover_requirements"
  elif [[ "$phase" == "discover_requirements" ]]; then echo "implement"
  # ... 20 more branches
  ```
- **Replace with:** `declare -A PHASE_TRANSITIONS` lookup table
- **Reduction:** ~200 → ~30 lines
- **Interface change:** None — same function signatures, same outputs.
- **Risk:** Low — purely mechanical transformation.

### 5. Template Substitution → `envsubst`
- **File:** `os/clavain/scripts/dispatch.sh` (~150 lines of 710 total)
- **What:** Custom `{name}` placeholder replacement for prompt assembly. Parses
  `KEY: value` sections and replaces `{{KEY}}` in templates.
- **Replace with:** `envsubst` (POSIX) or `gomplate` (for conditionals/loops)
- **Reduction:** ~150 → ~50 lines
- **Interface change:** Minor — rename `{name}` to `${name}` syntax.
- **Risk:** Low.

### 6. Custom Test Harness → `bats-core`
- **Files:** `interverse/interdoc/tests/` (8 test files, ~500 lines total)
  Also: `os/clavain/tests/run-tests.sh` (80 lines), `smoke/run-smoke-tests.sh` (110 lines)
- **What:** Custom assertion framework using manual `diff`, exit code checking,
  setup/teardown boilerplate duplicated across test files.
- **Replace with:** `bats-core` (already installed)
- **Reduction:** ~500 → ~250 lines (~50% for interdoc tests)
- **Interface change:** Test files rewritten in bats syntax (`@test`, `assert_equal`).
  TAP output integrates with CI/CD.
- **Risk:** Low — bats is mature; migration is straightforward.

### 7. Interspect Evidence SQL → Parameterized Queries
- **File:** `os/clavain/hooks/lib-interspect.sh` (~400 lines of 1,923 total)
- **What:** Manual SQLite table creation via heredoc SQL, evidence insertion with
  hand-rolled string sanitization (ANSI strip, control char removal, secret
  redaction, injection prevention). SQL built by string concatenation.
- **Replace with:** Python `sqlite3.execute(..., (?, ?))` parameterized queries
- **Reduction:** ~400 → ~150 lines (centralize sanitization in Python layer)
- **Interface change:** Partial — bash callers would invoke Python script instead
  of inline SQL.
- **Risk:** Medium — sanitization logic is security-critical; needs careful migration.

### 8. Template Code Generation → Jinja2
- **File:** `interverse/interflux/scripts/generate-agents.py` (~200 lines of 578 total)
- **What:** Python f-string based Markdown generation for agent files. Multi-line
  format strings with conditional sections.
- **Replace with:** Jinja2 templates (already used elsewhere in the project)
- **Reduction:** ~200 → ~80 lines (templates in separate `.j2` files)
- **Interface change:** Minor — template files added, Python rendering simplified.
- **Risk:** Low.

### 9. Process Management → `supervisord` or systemd user units
- **Files:** `interverse/interlock/scripts/interlock.sh`, `bin/launch-mcp.sh`,
  `hooks/stop.sh` (~120 lines across 3 files)
- **What:** Manual PID tracking, signal dispatch, process cleanup for MCP servers.
  No restart policies, no crash recovery, no log rotation.
- **Replace with:** `supervisord` (manages all MCP server processes centrally)
- **Reduction:** ~120 → ~40 lines (supervisord config + thin wrapper)
- **Interface change:** Partial — launch/stop scripts become supervisord commands.
- **Risk:** Medium — changes operational model for MCP servers.

## Priority 3 — Low Impact / Acceptable

### 10. GitHub API Parsing → `gh --jq`
- **File:** `os/clavain/scripts/upstream-check.sh` (~40 lines of 191)
- **What:** `gh api ... | jq -r '.field'` chains that could use `gh api --jq`.
- **Replace with:** `gh api --jq` flag
- **Reduction:** ~40 → ~20 lines
- **Drop-in:** Yes
- **Risk:** None

### 11. jq Boilerplate → Helper Functions
- **File:** `interverse/interline/scripts/statusline.sh` (~50 lines of 453)
- **What:** 15+ identical `jq -r "$1" "$config" | grep -v '^null$'` calls.
- **Replace with:** Define jq helper functions at script top, or extract to shared lib.
- **Reduction:** ~50 → ~20 lines
- **Drop-in:** Yes
- **Risk:** None

### 12. Sentinel/Throttle Check → `flock`
- **File:** `os/clavain/hooks/lib-intercore.sh` (~50 lines of 585)
- **What:** Temp file modification time for throttling with TOCTOU race condition.
- **Replace with:** `flock` for proper locking
- **Reduction:** ~50 → ~20 lines
- **Risk:** Low — but intercore migration may make this moot.

## Not Reinvented (Confirmed Acceptable)

| Pattern | File | Reason |
|---------|------|--------|
| Fuzzy dedup | `intermem/dedup.py` | Uses stdlib `difflib.SequenceMatcher` appropriately |
| Content hashing | `interflux/content-hash.py` | Uses stdlib `hashlib` appropriately |
| Bash FSM (interphase) | `interphase/hooks/lib-phase.sh` | Idiomatic bash, ~80 lines, not worth a library |
| curl + jq for APIs | `interkasten/hooks/setup.sh` | Standard pattern, not a reinvention |
| Upstream sync (Python) | `os/clavain/scripts/clavain_sync/` | Well-architected Python, shell version deprecated |
| CLI arg parsing | Various `getopts` usage | Idiomatic bash, not worth docopt dependency |

## Summary

| # | Finding | Lines Saved | Effort | Priority |
|---|---------|-------------|--------|----------|
| 1 | lib-routing.sh → yq | ~580 | Medium | HIGH |
| 2 | 15x bump-version.sh → interbump.sh | ~450 | Low | HIGH |
| 3 | drift-fix.sh → ast-grep | ~130 | Medium | HIGH |
| 4 | lib-sprint.sh FSM → lookup table | ~170 | Low | MEDIUM |
| 5 | dispatch.sh templates → envsubst | ~100 | Low | MEDIUM |
| 6 | interdoc tests → bats-core | ~250 | Medium | MEDIUM |
| 7 | lib-interspect.sh SQL → parameterized | ~250 | High | MEDIUM |
| 8 | generate-agents.py → Jinja2 | ~120 | Low | MEDIUM |
| 9 | MCP launchers → supervisord | ~80 | High | MEDIUM |
| 10 | upstream-check.sh → gh --jq | ~20 | Low | LOW |
| 11 | statusline.sh jq → helpers | ~30 | Low | LOW |
| 12 | lib-intercore.sh → flock | ~30 | Low | LOW |
| | **Total** | **~2,210** | | |

Estimated net reduction: ~2,210 lines of bespoke infrastructure code replaced by
calls to established tools. The top 3 items alone account for ~1,160 lines.
