# fastmcp_rust Assessment

**Assessed:** 2026-02-28
**Repo path:** research/fastmcp_rust/
**Source:** github.com/Dicklesworthstone/fastmcp_rust (score 96)

---

## fastmcp_rust (iv-oktyg)

**What it is:** A batteries-included Rust MCP server framework that ports Python FastMCP to Rust, adding cancel-correct async, attribute macros for zero-boilerplate tool/resource/prompt registration, and structured concurrency via the author's custom `asupersync` runtime.

**Language/Stack:** Rust (nightly, Edition 2024), `asupersync` (custom structured-concurrency runtime replacing tokio), `serde`/`serde_json`, `clap`, `axum` for HTTP transport. Workspace of 9 crates: `fastmcp-core`, `fastmcp-protocol`, `fastmcp-transport`, `fastmcp-server`, `fastmcp-client`, `fastmcp-macros` (proc macros), `fastmcp-console`, `fastmcp-cli`, `fastmcp` (facade).

**Quality:** high — 124 Rust source files, ~105k lines total, 287 unit tests in the server crate alone, 35+ e2e protocol tests, 88+ e2e workflow tests, trybuild macro expansion tests, comprehensive module-level doc comments, a 6528-line dedicated test file, and a dependency upgrade log showing active maintenance as of 2026-02-19. The main limitation is the hard nightly requirement and dependency on the author's own unpublished ecosystem crates (`asupersync`, `rich_rust`).

**Relevance to Demarch:** Directly overlaps with the `intercomd` Rust daemon (currently hand-rolling Axum HTTP without MCP) and any future Demarch Rust MCP servers that need structured concurrency, timeout safety, and tool registration without JSON-RPC boilerplate.

---

## Architecture Summary

The crate layering is clean:

```
fastmcp (facade prelude)
  fastmcp-core       — McpContext, 4-valued Outcome, cancellation checkpoints, session state
  fastmcp-protocol   — JSON-RPC 2.0 types, MCP domain types, cursor pagination
  fastmcp-transport  — Transport trait; stdio (primary), SSE, WebSocket, HTTP, in-process memory
  fastmcp-server     — ServerBuilder (fluent API), Router (method dispatch), handler traits
  fastmcp-client     — subprocess spawning, handshake, tool/resource/prompt call APIs
  fastmcp-macros     — #[tool], #[resource], #[prompt] proc macros with auto JSON schema
  fastmcp-console    — rich stderr (banner, stats, traffic display); never touches stdout
  fastmcp-cli        — fastmcp run/inspect/install/dev/list/test/tasks commands
```

### Key design patterns

**1. `#[tool]` / `#[resource]` / `#[prompt]` proc macros**

The macro reads doc comments for descriptions and function parameter names/types to generate a JSON Schema and a `ToolHandler` trait impl. This eliminates the 100+ line boilerplate per tool in hand-rolled MCP servers:

```rust
#[tool(description = "Calculate sum")]
async fn add(ctx: &McpContext, a: i64, b: i64) -> i64 {
    ctx.checkpoint()?;
    a + b
}
```

The macro expands into a struct implementing `ToolHandler::definition()` (returning `Tool` with schema) and `ToolHandler::call_async()`.

**2. `McpContext` and the checkpoint model**

`McpContext` wraps `asupersync::Cx` and exposes cancellation-awareness to every handler. The `ctx.checkpoint()?` call is a zero-cost atomic flag check — it lets the server cancel in-flight handlers when a client disconnects or a budget expires, without silent Future drops. Critical sections use `ctx.masked()` to defer cancellation across I/O boundaries.

**3. Budget system (not bare timeouts)**

Each request gets a `Budget` (deadline + poll quota + cost quota), tracked as a product semiring. Handlers can inspect remaining budget and the server enforces it globally. This is superior to tokio `timeout()` wrappers because exhaustion is observable rather than a silent cancellation.

**4. 4-valued `Outcome<T, E>`**

`Ok(T)` / `Err(E)` / `Cancelled(Why)` / `Panicked(Msg)` — distinguishes client disconnect from handler logic failure from internal panics. Propagated across the router to produce correct JSON-RPC error responses.

**5. `ServerBuilder` fluent API**

```rust
Server::new("my-server", "1.0.0")
    .tool(add)
    .resource(read_config)
    .prompt(greeting_prompt)
    .request_timeout(30)
    .on_startup(|ctx| async { /* setup */ })
    .run_stdio();
```

Builder tracks capabilities (logging, tools, resources, prompts, tasks) and announces them in `initialize`. The `Router` holds `HashMap<String, BoxedToolHandler>` and dispatches by method name.

**6. Transport trait**

```rust
pub trait Transport: Send {
    fn recv(&mut self) -> McpResult<Option<JsonRpcMessage>>;
    fn send(&mut self, msg: JsonRpcMessage) -> McpResult<()>;
    fn close(&mut self);
}
```

Stdio is the primary implementation (NDJSON, stdout clean). SSE/WebSocket/HTTP/MemoryTransport also implemented. Two-phase send (`SendPermit`) is cancel-safe: the permit is acquired, serialization happens, then the write is committed — preventing partial writes on cancellation.

**7. Full feature coverage (v0.2, assessed 2026-01-28)**

FEATURE_PARITY.md reports ~100% parity with Python FastMCP v2.14.4:
- Full OAuth 2.0/2.1 + OIDC server
- Middleware chain (caching, rate limiting)
- Docket distributed task queue (memory + Redis backends)
- Server composition: `mount()` and `as_proxy()`
- Bidirectional sampling/elicitation protocols
- Tag filtering, component versioning, per-handler timeouts
- EventStore for SSE resumability
- CLI tooling: dev hot-reload, inspect, install (Claude Desktop / Cursor / Cline)

---

## Differences from the Official MCP Rust SDK (`rmcp`)

| Dimension | fastmcp_rust | rmcp (official) |
|-----------|-------------|-----------------|
| Runtime | asupersync (cancel-correct) | tokio |
| Cancellation | ctx.checkpoint() cooperative | manual |
| Outcome type | 4-valued | 2-valued Result |
| Macros | #[tool], #[resource], #[prompt] | manual trait impl |
| Middleware | built-in chain (caching, rate limiting) | manual |
| Auth | OAuth 2.0/2.1, OIDC, JWT built in | minimal |
| Task queue | Docket (SEP-1686) | not included |
| Unsafe code | forbidden | allowed |
| Stability | nightly + author-ecosystem deps | stable |

The official `rmcp` crate is more conservatively scoped; `fastmcp_rust` is a full batteries-included framework with more opinions.

---

## Limitations and Risks

1. **Nightly required** — Rust 2024 Edition features lock this to nightly toolchain. Any Demarch crate adopting it must also use nightly, which is acceptable for experimental work but a policy decision for production.

2. **`asupersync` is the author's own crate** — Not from the broader Rust async ecosystem. If `asupersync` diverges or goes unmaintained, the dependency is load-bearing. The author also has a "no external contributions" policy (stated in README), meaning the project is a one-person effort.

3. **`rich_rust` dependency** — Another author-owned crate for console output. Similar risk.

4. **Single-threaded server loop** — The main loop is sequential (stated in limitations). Acceptable for stdio MCP servers that process one request at a time, but constraining for high-throughput HTTP transports.

5. **Sibling directory dependency** — `asupersync` is referenced as `"0.2"` on crates.io; this is now resolved from crates.io (the Cargo.toml shows `asupersync = "0.2"` in workspace.dependencies), so the sibling-dir requirement mentioned in older docs appears to have been resolved.

6. **Early API** — v0.2, explicitly "API may change before 1.0."

---

## Integration Opportunities

- **Replace hand-rolled JSON-RPC in `intercomd`**: `intercomd` currently exposes Axum HTTP routes with no MCP framing. If there is a future need for `intercomd` to expose an MCP interface, adopting `fastmcp-server` would replace custom JSON-RPC dispatch with `#[tool]` annotations on existing handler functions.

- **Proc macro pattern for new Rust MCP servers**: If Demarch adds any new Rust-based MCP server (e.g., an `interbase` Rust SDK companion, or a high-performance Interspect MCP interface), the `#[tool]` macro pattern eliminates boilerplate. The macro crate (`fastmcp-macros`) is self-contained enough to be ported or used as a reference.

- **`McpContext` / Budget pattern for `intercomd`**: Even without adopting the full framework, the budget-based timeout model (observable remaining budget, graceful cancellation vs hard timeout) is implementable with standard tokio using a `CancellationToken` + `Instant`. The fastmcp_rust code is a clear reference for how to wire this.

- **`fastmcp-transport` MemoryTransport for testing**: The in-process `MemoryTransport` that bridges two channel endpoints is a clean test harness pattern that could be ported into any Demarch Rust MCP server's test suite without pulling in the full framework.

- **4-valued `Outcome` type**: The `Ok/Err/Cancelled/Panicked` distinction is independently valuable as a design pattern for any long-running Rust async handler in Demarch. Could be modeled in `intercomd` without adopting `asupersync`.

- **`fastmcp-console` stderr discipline**: The explicit contract that stdout carries only NDJSON JSON-RPC and all human output goes to stderr (with rich formatting) is a pattern Demarch Rust MCP servers should follow. `fastmcp-console` is a reference for how to implement this cleanly.

---

## Inspiration Opportunities

- **Fluent server builder pattern**: The `Server::new().tool(...).resource(...).run_stdio()` chain is a clean ergonomic API that `interbase` or any future Demarch Rust MCP SDK should emulate, whether or not the framework itself is adopted.

- **Tag-based component filtering**: Tools/resources/prompts can have tags, and the server's list operations support `include_tags`/`exclude_tags` with AND/OR logic. This is a useful dynamic capability scoping pattern for Autarch or Intercore tool registries.

- **Checkpoint-based cancellation philosophy**: The design principle that every long-running async section should call `ctx.checkpoint()` to yield a cancellation point — rather than hoping tokio Future drops land correctly — is worth propagating into Demarch's Rust async patterns generally.

- **`Outcome<T, E>` error taxonomy**: Decoupling "expected failure" from "cancellation" from "panic" produces cleaner error telemetry. Demarch's agent execution pipelines (Autarch, Intercore) could benefit from a similar taxonomy in their task result types.

- **Middleware chain architecture**: The request/response middleware pattern (`on_request()` / `on_response()` / `on_error()`) with built-in `ResponseCachingMiddleware` and `RateLimitingMiddleware` is directly applicable to any Demarch component that routes tool calls through a dispatch layer.

- **MCPConfig file format**: The JSON/TOML server registry config (`mcp_config.rs`) that maps server names to stdio commands or URLs is a useful standard format for Demarch's plugin ecosystem config.

---

## Verdict: `inspire-only`

**Rationale:** The framework is high-quality and architecturally sound, but the hard nightly requirement and load-bearing dependency on a one-author crate ecosystem (`asupersync`, `rich_rust`) make wholesale adoption impractical for production Demarch Rust components; the design patterns — proc macro tool registration, budget-based timeouts, 4-valued outcomes, checkpoint cancellation, transport trait separation, and fluent server builder — are worth borrowing directly into any new Demarch Rust MCP server work.
