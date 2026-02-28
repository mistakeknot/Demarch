# MCP Server Decision Criteria

When to create a new MCP server vs using skills + shell libraries.

## Create an MCP Server When

- **Persistent state across sessions** — database, cache, index that must survive between invocations (e.g., intercore SQLite, intersearch embeddings)
- **Expensive initialization** — sidecar process, model loading, file cache warming that amortizes over multiple calls (e.g., intermap Python bridge)
- **Real-time interactive queries** — streaming results, session monitoring, graph traversal that benefits from a persistent process (e.g., intermux tmux monitoring, interlens graph queries)
- **External service bridge** — proxy to an authenticated external API that needs connection management (e.g., interkasten Notion bridge)

## Use Skills + Shell Libraries When

- **Stateless analysis** — run, produce output, exit. No state to preserve between invocations
- **Calls existing MCP servers** — compose existing tools rather than duplicating their data access
- **Batch output** — results written to files, not queried interactively
- **Infrequent use** — less than once per session on average

## Examples

| Plugin | Type | Reason |
|--------|------|--------|
| intercore | MCP server | SQLite event store, persistent state |
| intermap | MCP server | Python sidecar, file cache, expensive init |
| interlock | MCP server | Reservation database, real-time queries |
| interkasten | MCP server | Notion API bridge |
| intersearch | MCP server | Embedding index, expensive init |
| intermux | MCP server | tmux session monitoring, real-time |
| intertrace | Skills + libs | Stateless analyzer, calls intermap, batch output |
| interwatch | Skills + libs | On-demand scanning, file-based state |
| intercheck | Skills + libs | Session-scoped analysis, no persistence needed |
