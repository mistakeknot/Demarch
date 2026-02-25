# ToolError — Structured MCP Error Contract

**Package:** `github.com/mistakeknot/interbase/toolerror`
**Bead:** iv-gkory (closed)
**Epic:** iv-bg0a0 (closed)

## Problem

Demarch MCP servers returned flat error strings: `"check conflicts: intermute 500: internal error"`. Agents had to parse error text with heuristics to decide whether to retry, adjust input, or give up. This was fragile — a rewording broke agent logic.

## Design Rationale

### Why structured errors

Agents need three things from an error:

1. **What went wrong** (type) — so they can branch on the error class, not parse English
2. **Is it worth retrying** (recoverable) — so they don't retry permanent failures or give up on transient ones
3. **Context for recovery** (data) — so they can adjust their next action (e.g., which agent holds a conflicting reservation)

### Why six types, not more

The type catalog maps to agent decision branches, not HTTP status codes. Agents generally have four responses to errors:

- **Retry unchanged** → `TRANSIENT`
- **Fix input and retry** → `VALIDATION`
- **Work around the resource** → `NOT_FOUND`, `CONFLICT`, `PERMISSION`
- **Give up** → `INTERNAL`

More granular types (e.g., `RATE_LIMITED` vs `SERVICE_UNAVAILABLE`) would not change agent behavior — both trigger retry. The `data` field carries specifics (like `retry_after`) when the type alone isn't enough.

### Why JSON in the error text, not a separate channel

MCP's tool result model has `isError: true` with a text content field. There's no structured error metadata channel. Putting JSON in the error text is the pragmatic choice — agents already parse MCP results as JSON. The alternative (a custom MCP extension) would require changes to every MCP client.

## Wire Format

When a ToolError is returned via `.JSON()`, agents receive this in the MCP tool result's error text:

```json
{
  "type": "NOT_FOUND",
  "message": "agent \"fd-safety\" not registered",
  "recoverable": false
}
```

With optional data:

```json
{
  "type": "CONFLICT",
  "message": "reservation conflict: 2 conflicts",
  "recoverable": true,
  "data": {
    "conflicts": [
      {"agent_id": "agent-2", "pattern": "src/*.go", "held_by": "agent-2"}
    ]
  }
}
```

With retry guidance:

```json
{
  "type": "TRANSIENT",
  "message": "rate limited",
  "recoverable": true,
  "data": {
    "retry_after": 30
  }
}
```

### JSON Schema

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "type": "object",
  "required": ["type", "message", "recoverable"],
  "properties": {
    "type": {
      "type": "string",
      "enum": ["NOT_FOUND", "CONFLICT", "VALIDATION", "PERMISSION", "TRANSIENT", "INTERNAL"]
    },
    "message": {
      "type": "string",
      "description": "Human-readable error description"
    },
    "recoverable": {
      "type": "boolean",
      "description": "Whether the operation may succeed if retried (possibly with modified input)"
    },
    "data": {
      "type": "object",
      "description": "Optional structured context for error recovery",
      "additionalProperties": true
    }
  },
  "additionalProperties": false
}
```

## Agent-Side Parsing

Agents receiving MCP tool errors from Demarch servers should:

1. **Try JSON parse** on the error text. If it fails, treat as a legacy unstructured error.
2. **Check `type`** to branch on error class.
3. **Check `recoverable`** to decide retry strategy.
4. **Read `data`** for context-specific recovery (conflict holders, retry delays, etc.)

### Recommended agent patterns

```
ON tool error:
  parsed = try_json_parse(error_text)
  IF parsed AND parsed.type EXISTS:
    SWITCH parsed.type:
      TRANSIENT:
        delay = parsed.data.retry_after OR default_backoff
        RETRY after delay (max 3 attempts)
      VALIDATION:
        LOG "bad input: {parsed.message}"
        FIX input and retry once
      NOT_FOUND:
        SKIP this resource, try alternatives
      CONFLICT:
        IF parsed.data.conflicts:
          NEGOTIATE release with holder
        ELSE:
          WAIT and retry
      PERMISSION:
        ESCALATE to user
      INTERNAL:
        LOG and GIVE UP
  ELSE:
    # Legacy unstructured error — treat as INTERNAL
    LOG and GIVE UP
```

## Adoption Guide

### For MCP server developers

1. Add interbase to your `go.mod`:
   ```
   require github.com/mistakeknot/interbase v0.0.0
   replace github.com/mistakeknot/interbase => ../../sdk/interbase/go
   ```

2. Import the package:
   ```go
   import "github.com/mistakeknot/interbase/toolerror"
   ```

3. Replace `mcp.NewToolResultError(fmt.Sprintf(...))` with structured errors:
   ```go
   // Before
   return mcp.NewToolResultError(fmt.Sprintf("not found: %v", err)), nil

   // After
   return mcp.NewToolResultError(toolerror.New(toolerror.ErrNotFound, "%v", err).JSON()), nil
   ```

4. For client wrappers with domain-specific error types, create a `toToolError()` mapping function. See `interverse/interlock/internal/tools/tools.go` for the reference implementation.

### Mapping HTTP status codes

If your MCP server wraps an HTTP API:

| HTTP Status | ToolError Type |
|-------------|---------------|
| 400, 422 | `VALIDATION` |
| 403 | `PERMISSION` |
| 404 | `NOT_FOUND` |
| 409 | `CONFLICT` |
| 429, 5xx | `TRANSIENT` |
| Other 4xx | `VALIDATION` or `INTERNAL` (case by case) |

### Mapping connection errors

Network failures (connection refused, timeout, DNS) should map to `TRANSIENT` — the service may come back.

## Adopters

| Module | Commit | Scope |
|--------|--------|-------|
| interlock | `49beddf` | All 12 MCP tool handlers |

Future adopters: intermute (when it gains MCP tools), intermap, interserve.

## Related

- **Bead iv-gkory** — implementation task (closed)
- **Bead iv-bg0a0** — parent epic "Adopt mcp_agent_mail patterns" (closed)
- **Bead iv-wnurj** — middleware bead (unblocked, uses ToolError for error propagation)
- `sdk/interbase/go/toolerror/toolerror.go` — source
- `interverse/interlock/internal/tools/tools.go` — reference adoption
