# Correctness Review: Agent Capability Discovery Plan
**Plan file:** `docs/plans/2026-02-22-agent-capability-discovery.md`
**Reviewer:** Julik (Flux-drive Correctness Reviewer)
**Date:** 2026-02-22

---

## Invariants That Must Hold

Before enumerating defects, state what must remain true after this change:

1. **Interface completeness**: every implementation of `Store` satisfies the updated `ListAgents` signature. No uncompiled caller remains at the old arity.
2. **Filter correctness**: `ListAgents(ctx, project, []string{"review:architecture"})` returns exactly agents that carry that capability and no others.
3. **NULL safety**: the SQLite query does not crash, return no rows, or silently mismatch when `capabilities_json` is NULL or the empty string `""`.
4. **Name-key agreement**: the key used in `agentCapabilities` in plugin.json matches the `name` field the agent actually registers with at runtime.
5. **Test assertion correctness**: integration test assertions match the data registered in the test setup.
6. **Bash payload safety**: the jq expression used to extract capabilities produces valid JSON for `--argjson`, never raw multi-line text.

---

## Finding 1 — CRITICAL: `json_each(NULL)` and `json_each('')` cause silent exclusion or HTTP 500

**Severity:** Critical (data integrity — silent agent exclusion or runtime error)

**Location:** `core/intermute/internal/storage/sqlite/sqlite.go`, Plan Task 1 Step 5

### The Problem

The plan's SQL fragment for capability filtering:

```sql
EXISTS (SELECT 1 FROM json_each(capabilities_json) WHERE json_each.value IN (?,?,...))
```

SQLite's `json_each()` behavior on bad input:

- `json_each(NULL)` — produces **zero rows**. `EXISTS` evaluates to false. The agent is silently excluded from capability-filtered queries. This is wrong for agents that simply predate the capabilities feature.
- `json_each('')` — raises a JSON parse error that propagates as a Go-level `sql.ErrRows` error, causing `ListAgents` to return `(nil, err)`. The HTTP handler converts this to an HTTP 500. **One agent with an empty-string column kills all capability-filtered requests.**
- `json_each('null')` — also produces zero rows (JSON null is not an array).

The existing scan code at lines 789-791 of `sqlite.go` already guards the Go layer:

```go
if err := json.Unmarshal([]byte(capsJSON), &caps); err != nil {
    log.Printf("WARN: corrupt capabilities_json for agent %s: %v", id, err)
}
```

But this runs _after_ the SQL WHERE clause has already filtered rows. The guard does nothing for the filtering path.

Whether agents actually have NULL or empty-string `capabilities_json` depends on what `RegisterAgent` writes when no capabilities are provided. The current `interlock-register.sh` does NOT send a `capabilities` field at all. If `RegisterAgent`'s INSERT does not coerce missing capabilities to `'[]'`, every agent registered today has a NULL or empty column, and the empty-string case is a live HTTP 500 risk post-rollout.

### Concrete Failure Narrative

1. Sixty agents are registered by the current `interlock-register.sh` (no capabilities in POST body). Their `capabilities_json` is NULL or `''` depending on the INSERT.
2. The plan is deployed.
3. An operator calls `GET /api/agents?project=myproject&capability=review:architecture`.
4. The SQL query hits the first agent with `capabilities_json = ''`.
5. `json_each('')` returns a parse error from SQLite.
6. `s.db.Query()` returns an error. `ListAgents` returns `(nil, err)`. Handler returns HTTP 500.
7. Every capability-filtered query fails until the bad row is repaired. The unfiltered `GET /api/agents` still works fine, masking the bug in smoke tests.

### Fix

Guard in SQL:

```sql
EXISTS (
  SELECT 1 FROM json_each(
    CASE
      WHEN capabilities_json IS NULL
        OR capabilities_json = ''
        OR capabilities_json = 'null'
      THEN '[]'
      ELSE capabilities_json
    END
  )
  WHERE json_each.value IN (?,?,...)
)
```

Additionally, verify what `RegisterAgent`'s INSERT writes when `Capabilities` is nil/empty. If it can write NULL or `''`, add a `DEFAULT '[]'` to the column definition or a `COALESCE(?, '[]')` in the INSERT. A one-time migration `UPDATE agents SET capabilities_json = '[]' WHERE capabilities_json IS NULL OR capabilities_json = ''` should run before deploying the filtering feature.

---

## Finding 2 — HIGH: Incomplete caller inventory — `client/client_test.go` not listed in Step 8

**Severity:** High (compile-time breakage blocks all tests)

**Location:** Plan Task 1 Step 8

The plan says: "Search for `ListAgents(` across intermute and update call sites to pass `nil`. Key callers: `client/client.go:172`, `sqlite_test.go`."

**Actual callers found by exhaustive grep (`grep -rn 'ListAgents(' core/intermute/`):**

| File | Lines | Status in plan |
|------|-------|----------------|
| `internal/storage/storage.go:30` | interface declaration | listed (implicitly) |
| `internal/storage/storage.go:241` | `InMemory.ListAgents` impl | listed |
| `internal/storage/sqlite/sqlite.go:765` | `Store.ListAgents` impl | listed |
| `internal/storage/sqlite/resilient.go:126,131` | `ResilientStore.ListAgents` | listed |
| `internal/http/handlers_agents.go:71` | handler call site | listed |
| `internal/storage/sqlite/sqlite_test.go:61,70,93` | three SQLite test calls | listed |
| `client/client.go:172` | exported HTTP client method | listed |
| **`client/client_test.go:92,119`** | **two test call sites** | **NOT listed** |

`client/client_test.go` calls `c.ListAgents(ctx, "")` (line 92) and `c.ListAgents(ctx, "override")` (line 119). These call the `client.Client.ListAgents` method, which is the HTTP-level client wrapper (distinct from the Store interface). If the plan changes `client.Client.ListAgents` to accept a capability parameter, these two lines will not compile.

Additionally, `internal/smoke_test.go` (332 lines) was not checked by the plan. It does not appear to call `ListAgents` directly (a targeted grep found no match), but the plan should confirm this explicitly.

### Fix

Add to Step 8: update `client/client_test.go:92` to `c.ListAgents(ctx, "", "")` and line 119 to `c.ListAgents(ctx, "override", "")` (or whatever the new signature is). Run `grep -rn 'ListAgents(' core/intermute/` before closing the step, not after.

---

## Finding 3 — HIGH: `client.Client.ListAgents` signature change is breaking toward all external import sites

**Severity:** High (API contract breakage — external callers not identified)

**Location:** Plan Task 1 Step 8, `core/intermute/client/client.go`

`client.Client.ListAgents` is an exported API. Any code outside `core/intermute` that imports `github.com/mistakeknot/intermute/client` and calls `ListAgents` will fail to compile.

The plan says "add `capability` param support" without specifying whether this is additive (new method) or breaking (changed signature). Potential external callers include `apps/autarch/` (the Bigend TUI), any agent-rig scripts that use the Go client, and any future callers.

The plan already demonstrates the correct pattern for the interlock client in Task 3 Step 2: it adds a new `DiscoverAgents` method alongside the existing `ListAgents`. The same approach should be applied to `core/intermute/client/client.go` — add `DiscoverAgents` with the capability parameter, leave `ListAgents` signature unchanged.

If a signature change is truly intended, enumerate all import sites across the monorepo before writing the plan. The plan currently lists none.

---

## Finding 4 — MEDIUM: jq `-r` flag on a JSON array produces multi-line plain text, not JSON — capabilities silently dropped

**Severity:** Medium (silent functional failure — no error surfaced anywhere)

**Location:** Plan Task 2 Step 1, `interverse/interlock/scripts/interlock-register.sh`

The plan's jq expression:

```bash
AGENT_CAPS=$(jq -r '.agentCapabilities // {} | to_entries[] | select(.key == "'"$AGENT_NAME"'") | .value' "$PLUGIN_JSON" 2>/dev/null)
```

**The `-r` (raw-output) flag tells jq to print JSON strings without quotes. Applied to an array, it prints each element on its own line.**

For `AGENT_NAME=fd-architecture` with value `["review:architecture","review:code","review:design-patterns"]`, `-r` outputs:

```
review:architecture
review:code
review:design-patterns
```

This is not valid JSON. When this multi-line string is passed to:

```bash
jq -n --argjson capabilities "$AGENT_CAPS" ...
```

jq fails with a parse error. Because the outer `2>/dev/null` on the registration curl suppresses stderr, the failure is invisible. `CAPABILITIES` will remain `"[]"` (the default), and the agent registers with no capabilities. No error is surfaced to the operator, no exit code change, no log line.

**Additionally:** the expression inlines `$AGENT_NAME` via string concatenation into the jq filter: `select(.key == "'"$AGENT_NAME"'")`. A tmux window title containing a single quote (e.g., `fd-architecture's session`) will break the jq syntax. Use `--arg` instead.

### Concrete Failure Narrative

1. Deployment completes. `fd-architecture` agent starts, `CLAUDE_PLUGIN_ROOT` is set, `plugin.json` is present.
2. `AGENT_CAPS` is set to three lines of plain text.
3. `jq -n --argjson capabilities "$AGENT_CAPS"` fails with `Invalid numeric literal`. Error goes to stderr, which is suppressed.
4. The entire registration `jq -n ...` command fails, causing `RESPONSE` to be empty.
5. `AGENT_ID=$(echo "" | jq -r '.agent_id // empty')` returns empty. `[[ -n "$AGENT_ID" ]] || exit 1` fires.
6. The hook exits 1. Agent is not registered. Capabilities feature is silently not working.

### Fix

Use `-c` (compact JSON output) instead of `-r`, and use `--arg` for the key lookup:

```bash
AGENT_CAPS=$(jq -c --arg name "$AGENT_NAME" \
    '.agentCapabilities // {} | .[$name] // empty' \
    "$PLUGIN_JSON" 2>/dev/null)
```

`-c` preserves the JSON array structure. `.[$name]` is safe against shell injection. `// empty` produces empty output (not `null`) when the key is absent, preserving the existing `-n` guard.

---

## Finding 5 — MEDIUM: Integration test registers `"repo-analyst"` but the real agent name is `"repo-research-analyst"`

**Severity:** Medium (test does not cover the real code path; misleading test data)

**Location:** Plan Task 5 Step 1, integration test setup

The integration test registers:

```go
{"repo-analyst", []string{"research:codebase", "research:architecture"}},
```

The actual agent file is `interverse/interflux/agents/research/repo-research-analyst.md` with frontmatter `name: repo-research-analyst`. The `agentCapabilities` map in Task 4 uses the key `"repo-research-analyst"`. The real agent would register under whatever name `AGENT_NAME` resolves to at runtime — most likely `repo-research-analyst` if the tmux window title is set correctly.

The integration test is self-consistent (its own registration and assertion agree), so the test itself passes. But it tests a hypothetical agent named `repo-analyst` that does not exist in the plugin manifest. Any human reading the test will be confused, and future capability assertions against this agent will have to track two names.

The inline comment at line 494-496 correctly self-corrects the OR-domain logic:

```go
// Wait — repo-analyst has research:architecture, not review:architecture. Should only match fd-architecture.
```

This comment confirms the author noticed the domain distinction. The assertion `!= 1` is correct for querying `review:architecture`. No logic error here, only naming inconsistency.

### Fix

Rename `"repo-analyst"` to `"repo-research-analyst"` in the test setup. No assertion changes needed.

---

## Finding 6 — LOW: Comma-in-capability URL encoding resolves correctly but is undocumented

**Severity:** Low (documentation gap, not a bug)

**Location:** Plan Task 3 Step 2, `interverse/interlock/internal/client/client.go`

The `DiscoverAgents` method uses `url.QueryEscape(capability)`. If `capability` is `"review:architecture,review:safety"`, the commas are encoded as `%2C`. Net/http's `r.URL.Query().Get()` decodes `%2C` back to `,` before `strings.Split` runs. The round-trip is safe.

This is correct behavior but should be documented in the method comment. The MCP tool description says "Comma-separated for OR matching" — callers should know they can pass `"review:architecture,review:safety"` as a single string.

---

## Finding 7 — LOW: `InMemory.ListAgents` ordering is non-deterministic vs. SQLite `ORDER BY last_seen DESC`

**Severity:** Low (test fragility, not correctness)

**Location:** `internal/storage/storage.go:241`, Plan Task 1 Step 4

`InMemory.ListAgents` iterates `m.agents` (a `map[string]core.Agent`). Go map iteration is intentionally non-deterministic. The SQLite implementation uses `ORDER BY last_seen DESC`. Any test that uses `InMemory` and checks ordering (not just count) will be flaky.

The plan's tests only check `len(result.Agents)`, so existing tests are safe. Note this divergence for future test authors.

---

## Finding 8 — LOW: `agentCapabilities` key must match runtime `AGENT_NAME` — not guaranteed by any mechanism

**Severity:** Low (operational — capabilities silently not registered for agents with mismatched names)

**Location:** Plan Task 2/Task 4

`AGENT_NAME` is resolved at runtime via tmux window title, a config file, or a fallback of `claude-<session-prefix>`. None of these is guaranteed to match the agent's filename or the key in `agentCapabilities`. If the tmux window title is `"Flux Drive"` instead of `"fd-architecture"`, the `agentCapabilities` lookup finds nothing and capabilities default to `[]`.

This is an inherent architectural limitation of the approach — the plugin manifest cannot know at runtime which agent is executing in which shell. The plan should document this as a known operational requirement: each agent session must set its tmux window title (or `~/.config/clavain/intermute-agent-name`) to the canonical agent name before the registration hook fires.

---

## Summary Table

| # | Severity | Location | Issue |
|---|----------|----------|-------|
| 1 | CRITICAL | SQLite `ListAgents`, Task 1 Step 5 | `json_each(NULL)`/`json_each('')` — silent agent exclusion or HTTP 500 on capability-filtered queries |
| 2 | HIGH | Task 1 Step 8 | `client/client_test.go:92,119` not in caller inventory; compile breakage |
| 3 | HIGH | Task 1 Step 8 | `client.Client.ListAgents` signature change breaks external callers; no import-site inventory |
| 4 | MEDIUM | Task 2 Step 1, bash script | jq `-r` on array produces multi-line non-JSON; capabilities silently dropped, zero error output |
| 5 | MEDIUM | Task 5 Step 1 | Test registers `"repo-analyst"` but real agent is `"repo-research-analyst"` |
| 6 | LOW | Task 3 Step 2 | Comma in capability URL-encodes safely but is undocumented |
| 7 | LOW | Task 1 Step 4 | InMemory has non-deterministic ordering vs. SQLite `ORDER BY last_seen DESC` |
| 8 | LOW | Task 2/Task 4 | Runtime `AGENT_NAME` may not match `agentCapabilities` key; no enforcement mechanism |

---

## Priority Order for Fixes

1. **Finding 1 (CRITICAL)**: Add the SQL `CASE` guard for NULL/empty `capabilities_json` before writing a single line of implementation. Verify and fix the `RegisterAgent` INSERT. Run a migration on any existing data.

2. **Finding 4 (MEDIUM, but silent)**: Change `-r` to `-c` and use `--arg name` in the jq extraction. This is a one-line fix that prevents capabilities from being silently dropped on every real-world registration.

3. **Finding 2 (HIGH)**: Add `client/client_test.go:92,119` to the Step 8 caller list. Run the grep before closing Step 8.

4. **Finding 3 (HIGH)**: Decide: breaking signature change (enumerate all import sites) or new `DiscoverAgents` method alongside existing `ListAgents` (consistent with what Task 3 already does for the interlock client). Recommend the latter.

5. **Finding 5 (MEDIUM)**: Rename `"repo-analyst"` to `"repo-research-analyst"` in the integration test. Two-character edit.
