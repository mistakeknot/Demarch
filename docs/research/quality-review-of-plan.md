# Quality Review: 2026-02-23-pollard-hunter-resilience.md

> This file is a brief summary. Full review: `.claude/reviews/iv-xlpg-plan-quality.md`

Reviewed against:
- `/home/mk/projects/Demarch/docs/plans/2026-02-23-pollard-hunter-resilience.md`
- `/home/mk/projects/Demarch/apps/autarch/internal/pollard/hunters/hunter.go`
- `/home/mk/projects/Demarch/apps/autarch/internal/pollard/cli/scan.go`
- `/home/mk/projects/Demarch/apps/autarch/internal/pollard/api/scanner.go`
- `/home/mk/projects/Demarch/apps/autarch/internal/pollard/watch/watcher.go`

---

## Summary of Findings (iv-xlpg Pollard Hunter Resilience)

### BLOCKER — `Success()` semantic gap after HunterStatus migration

Task 1 replaces `Success()` with `return r.Status == HunterStatusOK`. Task 4 (`api/scanner.go`) only sets `Status` on the error path, not the partial-success path. After the migration, a hunt with `len(Errors) > 0` and `Status` still zero (`HunterStatusOK`) will be recorded as successful in the DB.

Fix: add `huntResult.Status = hunters.HunterStatusPartial` to the success path in `api/scanner.go` when `len(huntResult.Errors) > 0`.

### BUG — Pre-cancelled context reaches `h.Hunt`

`HuntWithRetry` calls `h.Hunt(ctx, cfg)` without checking `ctx.Err()` first. The proposed `fakeHunter` discards the context, so `TestHuntWithRetry_RespectsContextCancellation` will fail — the hunter returns `DNSError`, not `context.Canceled`.

Fix: add `if ctx.Err() != nil { return nil, ctx.Err() }` at the top of the retry loop body. Update `fakeHunter.Hunt` to check and return the context error.

### MINOR — `net.Error` catches non-retryable DNS errors

`errors.As(err, &netErr)` matches permanent network failures (`IsNotFound: true`). Tighten to `netErr.Timeout() || netErr.Temporary()`.

## What Is Sound

- `HunterStatus.String()` satisfies `fmt.Stringer` correctly — idiomatic
- `fakeHunter` pointer-receiver mutation is safe — `HuntWithRetry` is a sequential loop with no goroutine concurrency
- `hunterSummary` as a local type in `scan.go`'s closure is the right scope — CLI-only output, not needed by API or watcher
- All `%w` error wrapping is consistent with project conventions
- All new exported identifiers pass the 5-second naming rule
- No new dependencies — stdlib only

---

## Original Review (2026-02-22-agent-capability-discovery.md preserved below for history)

---

# Quality Review: 2026-02-22-agent-capability-discovery.md

Reviewed against:
- `/root/projects/Demarch/docs/plans/2026-02-22-agent-capability-discovery.md`
- `/root/projects/Demarch/core/intermute/internal/http/handlers_agents.go`
- `/root/projects/Demarch/core/intermute/internal/http/handlers_agents_test.go`
- `/root/projects/Demarch/interverse/interlock/scripts/interlock-register.sh`

---

## Finding 1: `agentHasAnyCapability` — naming and placement

**Severity: Low**

The plan places `agentHasAnyCapability` as a package-level free function in `storage.go`. Both the name and placement deserve scrutiny.

### Naming

The name is acceptable but slightly redundant. For an unexported function, "agent" is implied by its location adjacent to `InMemory.ListAgents`. The word "Any" implies a slice input without saying so in the signature. The existing codebase uses plain, verb-first names for unexported helpers (`handleListAgents`, `handleRegisterAgent`).

A more idiomatic alternative:

```go
// hasAnyCapability reports whether agentCaps contains at least one element from queryCaps.
func hasAnyCapability(agentCaps, queryCaps []string) bool {
```

The shortened name removes the redundant "agent" prefix. The call site reads identically:

```go
if len(capabilities) > 0 && !hasAnyCapability(agent.Capabilities, capabilities) {
```

### Should it be a method on Agent?

No. `agentHasAnyCapability` takes two `[]string` slices and has no need for any other `Agent` field. Attaching it as `(a core.Agent) HasAnyCapability(queryCaps []string) bool` would bind filtering query logic to the domain model in `core/`, which is the wrong layer. Storage query semantics belong in the storage package. Keep it as an unexported package-level function in `storage.go`, but use the shorter name above.

### Linear scan performance

The O(n*m) double loop is appropriate for the expected cardinality (2-5 caps per agent, 1-3 per query). No change needed.

---

## Finding 2: Test design — `TestListAgentsCapabilityFilter`

**Severity: Moderate — two correctness gaps, one convention miss**

### 2a. No guard for empty strings from comma-split (correctness risk)

The plan's handler parses `?capability=` via:

```go
capabilities = strings.Split(capParam, ",")
```

`strings.Split("review:architecture,", ",")` returns `["review:architecture", ""]`. An empty string in the capabilities filter will never match any agent capability, which is safe, but the empty string will also be passed into the SQLite `json_each ... IN (?, ?)` query as a literal empty string placeholder, potentially confusing query plans and returning incorrect zero results when at least one valid capability is present.

The handler should trim and filter:

```go
for _, c := range strings.Split(capParam, ",") {
    if c = strings.TrimSpace(c); c != "" {
        capabilities = append(capabilities, c)
    }
}
```

The test suite should include:

```go
{"trailing comma ignored", "?project=proj-a&capability=review:architecture,", 2},
```

Without this test, the parse bug can silently regress.

### 2b. No agent with empty capabilities in fixture

None of the three registered agents has an empty `[]string{}` capabilities slice. An agent with no capabilities should always be excluded when a capability filter is active. The `agentHasAnyCapability` / `hasAnyCapability` function correctly handles this (returns `false` for empty `agentCaps`), but the test suite does not exercise it. Add a fourth agent:

```go
{"agent-nocaps", []string{}},
```

Then verify the "single match" count remains 2, not 3.

### 2c. Missing HTTP status check

`TestListAgents` and `TestListAgentsProjectFilter` both assert `resp.StatusCode != http.StatusOK`. The proposed `TestListAgentsCapabilityFilter` skips this check and decodes directly. Add the status assertion after each `http.Get` call to match existing convention.

---

## Finding 3: `cap` variable name shadows the Go builtin

**Severity: Low — readability and linter warning**

In the SQLite implementation (Task 1, Step 5):

```go
for i, cap := range capabilities {
    capPlaceholders[i] = "?"
    args = append(args, cap)
}
```

`cap` shadows the Go builtin `cap()`. This does not cause a bug here because the builtin is not called inside the loop body. However:

1. `go vet` does not warn about this. `gocritic` and `revive` do. If either linter is added to CI it will fire on this line.
2. Any future contributor who adds a `make([]T, 0, cap(existing))` call inside this loop will introduce a silent type-error or panic depending on context.
3. The outer parameter is already named `capabilities` (plural), making `capability` (singular) the natural loop variable — it is unambiguous and consistent with the naming convention in the InMemory implementation where the loop variables are `qc` and `ac`.

Fix:

```go
for i, capability := range capabilities {
    capPlaceholders[i] = "?"
    args = append(args, capability)
}
```

---

## Finding 4: Self-correcting comment in integration test

**Severity: Low — must be cleaned up before merge**

In `TestCapabilityDiscoveryEndToEnd` (Task 5, Step 1), lines 494–495:

```go
// Should match fd-architecture (has review:architecture) and repo-analyst (has research:architecture)
// Wait — repo-analyst has research:architecture, not review:architecture. Should only match fd-architecture.
```

This is a thinking-aloud artifact from plan authoring that must not survive into committed code. Two concrete problems:

1. It documents the author's momentary confusion, not the system's behavior. Future readers encounter the old wrong assumption, then the correction, and have to mentally reconcile both. This creates doubt where none should exist.
2. The assertion immediately below (`if len(result.Agents) != 1`) already communicates the expectation. The comment adds noise, not signal.

Replace both lines with a single tight comment:

```go
// Only fd-architecture has review:architecture; repo-analyst carries research:architecture (different domain prefix).
```

Or omit entirely — the test assertion is self-evident.

---

## Finding 5: Bash script — jq fallback pattern has two correctness problems

**Severity: Moderate — one is an injection-class issue, one produces silently broken payloads**

The proposed capability extraction in Task 2, Step 1:

```bash
AGENT_CAPS=$(jq -r '.agentCapabilities // {} | to_entries[] | select(.key == "'"$AGENT_NAME"'") | .value' "$PLUGIN_JSON" 2>/dev/null)
if [[ -n "$AGENT_CAPS" ]] && [[ "$AGENT_CAPS" != "null" ]]; then
    CAPABILITIES="$AGENT_CAPS"
fi
```

### 5a. AGENT_NAME is injected into the jq filter string (injection risk)

`$AGENT_NAME` is shell-interpolated directly into the jq filter using `'"$AGENT_NAME"'` quoting. An agent name containing a single quote, backslash, or jq metacharacter silently breaks the jq expression (the `2>/dev/null` swallows the parse error). The result is `AGENT_CAPS=""` and capabilities silently fall back to `"[]"`.

This is the exact problem `--arg` exists to solve — and the script already uses it at line 37 for the POST payload. Use it here too:

```bash
AGENT_CAPS=$(jq -rc --arg name "$AGENT_NAME" \
    '.agentCapabilities[$name] // empty' \
    "$PLUGIN_JSON" 2>/dev/null)
```

`--arg name "$AGENT_NAME"` passes the value as a safe jq variable, handling any string content correctly.

### 5b. `.value` with `-r` produces multi-line output, not compact JSON

`.agentCapabilities["fd-architecture"]` is a JSON array. The original expression `.to_entries[] | select(.key == ...) | .value` with `-r` pretty-prints the array:

```
[
  "review:architecture",
  "review:code"
]
```

This multi-line string is then passed to `--argjson capabilities "$CAPABILITIES"` in the POST body. `--argjson` requires valid JSON. Whether this parses correctly depends on jq version — some accept multi-line, some do not. The result is a payload that may or may not include capabilities depending on the runtime jq version, with no error surfaced.

The fix is to use `-c` (compact output) and the direct key access form, as shown in 5a:

```bash
AGENT_CAPS=$(jq -rc --arg name "$AGENT_NAME" \
    '.agentCapabilities[$name] // empty' \
    "$PLUGIN_JSON" 2>/dev/null)
```

`-rc` gives compact single-line JSON. Direct key access `.agentCapabilities[$name]` is cleaner than `to_entries[] | select(.key == $name) | .value` and avoids the spurious outer transformation.

### 5c. Graceful fallback is correct

The outer guard `[[ -n "$PLUGIN_JSON" ]] && [[ -f "$PLUGIN_JSON" ]]` and the `2>/dev/null` suppression are correct — plugin.json is optional and agents without a manifest should register with `"[]"` rather than fail. No change needed here.

---

## Finding 6: Integration test — decode errors unchecked

**Severity: Low — convention miss**

Both decode calls in `TestCapabilityDiscoveryEndToEnd` discard the error:

```go
json.NewDecoder(resp.Body).Decode(&result)
...
json.NewDecoder(resp2.Body).Decode(&result2)
```

Every other test in `/root/projects/Demarch/core/intermute/internal/http/handlers_agents_test.go` checks the decode error with `if err := ...; err != nil { t.Fatalf(...) }`. The integration test should match this convention. A decode failure with no check causes the subsequent length assertion to fail with a misleading "expected 1, got 0" rather than "decode failed: unexpected EOF".

---

## Finding 7: `DiscoverAgents` parameter type hides multi-value semantics

**Severity: Low**

The `DiscoverAgents` client method (Task 3, Step 2) takes `capability string`:

```go
func (c *Client) DiscoverAgents(ctx context.Context, capability string) ([]Agent, error) {
    path := "/api/agents?project=" + url.QueryEscape(c.project)
    if capability != "" {
        path += "&capability=" + url.QueryEscape(capability)
    }
```

The handler parses `?capability=` with `strings.Split(capParam, ",")`, so callers passing `"review:architecture,review:safety"` to `DiscoverAgents` get OR matching — but the `string` type signature does not communicate this. A caller reading only the method signature has no way to know comma-separation is meaningful.

The store interface takes `[]string`. The handler produces `[]string`. The client is the only layer using `string`. Change the parameter to `[]string` and join in the client:

```go
func (c *Client) DiscoverAgents(ctx context.Context, capabilities []string) ([]Agent, error) {
    path := "/api/agents?project=" + url.QueryEscape(c.project)
    if len(capabilities) > 0 {
        path += "&capability=" + url.QueryEscape(strings.Join(capabilities, ","))
    }
    ...
}
```

The MCP tool handler wraps the single tool argument string:

```go
capability, _ := req.Params.Arguments["capability"].(string)
var caps []string
if capability != "" {
    caps = strings.Split(capability, ",")
}
agents, err := c.DiscoverAgents(ctx, caps)
```

This keeps the wire format (comma-separated query param) as an encoding detail inside the client, not leaked into callers.

---

## Summary of Required Changes

| # | File | Issue | Action |
|---|------|-------|--------|
| 1 | `storage.go` | `agentHasAnyCapability` name is redundant | Rename to `hasAnyCapability` |
| 2a | `handlers_agents.go` | No filter for empty strings from comma-split | Add trim+filter loop when parsing `?capability=` |
| 2b | `handlers_agents_test.go` | Missing empty-capabilities agent in fixture | Add `{"agent-nocaps", []string{}}` and verify exclusion |
| 2c | `handlers_agents_test.go` | Missing HTTP status checks in new test | Add `StatusOK` assertion after each `http.Get` |
| 3 | `sqlite.go` Step 5 | `cap` loop variable shadows builtin | Rename to `capability` |
| 4 | Integration test | Self-correcting comment | Replace two lines with one accurate comment |
| 5a | `interlock-register.sh` | `$AGENT_NAME` injected into jq filter | Use `--arg name "$AGENT_NAME"` |
| 5b | `interlock-register.sh` | `.value` produces multi-line array output | Use `-rc` and `.agentCapabilities[$name] // empty` |
| 6 | Integration test | Decode errors unchecked | Add `if err := json.Decode(...); err != nil` guards |
| 7 | `client.go` Step 2 | `string` param hides multi-value semantics | Change to `[]string`, join inside client |

**Highest risk:** 5b (silently broken capability payload on registration, version-dependent jq behavior) and 2a (empty-string in SQLite IN clause from trailing comma in query param).

**Quickest wins:** 3 (rename one variable), 4 (replace two comment lines), 1 (rename one function).
