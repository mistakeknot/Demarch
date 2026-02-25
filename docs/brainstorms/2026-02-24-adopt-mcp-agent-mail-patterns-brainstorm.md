# Adopt mcp_agent_mail Patterns

**Bead:** iv-bg0a0
**Phase:** brainstorm (as of 2026-02-25T07:16:49Z)

## What We're Building

Extracting high-value infrastructure patterns from the 10-agent deep review of mcp_agent_mail and adopting them into Demarch's interbase SDK, intermute, and interlock. The review identified 15 ranked recommendations — this sprint focuses on the P0 subset that unblocks the dependency chain.

## Why This Approach

**Adopt selectively, not wholesale.** The review verdict is clear: mcp_agent_mail has excellent infrastructure patterns (structured errors, circuit breaker, tool instrumentation) inside a structurally flawed container (11k-line monolith, 122 bare except blocks, sender impersonation). We extract specific patterns, not reference architecture.

**Sprint scope: P0 items only.** The epic blocks 15 children, but only 5 are P0. Closing the epic unblocks all children — the P1/P2 items can proceed independently in future sprints.

## Key Decisions

1. **Sprint scope:** 3 P0 items in interbase (ToolError, middleware, circuit breaker) + 2 decision/design items for intermute (sender identity, contact policies). The remaining 10 items stay as open beads, unblocked when this epic closes.

2. **ToolError contract (iv-gkory):** Go struct in `sdk/interbase/` with error type catalog: `NOT_FOUND`, `CONFLICT`, `PERMISSION_DENIED`, `INVALID_INPUT`, `UNAVAILABLE`, `INTERNAL`. Each error carries `Type`, `Message`, `Recoverable`, `Data`. Adopters wrap handler errors with `interbase.NewToolError(...)`.

3. **MCP tool middleware (iv-wnurj):** Shared handler wrapper in interbase that adds timing, error counting, structured error wrapping, and capability gating. Depends on ToolError being defined first. Pattern: `interbase.WrapHandler(handler, opts)` returns a handler with instrumentation.

4. **Circuit breaker (iv-q62fr):** Go implementation in interbase for SQLite operations. 5-failure threshold → 30s open → half-open probe. Critical lesson from review: only count *transient* errors (SQLITE_BUSY, timeout), NOT all errors.

5. **Sender identity decision (iv-osph4):** Mandatory. Intermute already has agent registration — enforce that `sender` in messages matches a registered agent. No anonymous messages.

6. **Contact policies (iv-t4pia):** 4-level model (`open | auto | contacts_only | block_all`) enforced at delivery time on ALL paths (send AND reply). Critical lesson: mcp_agent_mail's `reply_message` bypasses policy for local recipients — we must NOT replicate that bug.

7. **What Demarch already does better:** Keep cursor-based pagination (not timestamp), keep `MaxOpenConns(1)` for writes, keep separate handler/logic/data layers, keep `WHERE phase = ?` optimistic concurrency. Do NOT adopt mcp_agent_mail's 50-connection pool, `func.lower()` on indexed columns, or bare exception handling.

## Open Questions

None — the 10-agent review provides complete architectural guidance. Implementation is execution, not research.
