# Brainstorm: Intercache — Cross-Session Semantic Cache

**Bead:** iv-p4qq
**Date:** 2026-02-23

## What We're Building

An MCP server that provides content-addressed caching, embedding persistence, and semantic deduplication across Claude Code sessions. Three goals:

1. **Cold start speed** — eliminate 2-5 min re-reads by caching file content (SHA256-keyed)
2. **Semantic deduplication** — track what was read last session, skip unchanged files
3. **Embedding persistence** — unify and persist tldr-swinton/intersearch indexes across sessions

## Why This Approach

### MCP server (chosen over library/CLI)

- Consistent with ecosystem pattern (interlock, intermux, interserve are all MCP servers)
- Persistent daemon — shared across concurrent sessions without file locking
- Tools are discoverable by Claude Code automatically
- Can serve multiple projects simultaneously (multi-tenant by project root)

### Content-addressed storage (chosen over path-based)

- SHA256 keying makes invalidation automatic — changed content = different key
- Deduplication is free — same content in different paths = one blob
- Consistent with interbench's blob store pattern

## Architecture

### Storage Layout

```
~/.intercache/
├── blobs/               # Content-addressed blob store (SHA256 → file content)
│   ├── ab/cd1234...     # 2-char prefix sharding
│   └── ...
├── index/               # Per-project index metadata
│   ├── <project-hash>/
│   │   ├── manifest.json    # File path → SHA256 mappings + timestamps
│   │   ├── embeddings.db    # SQLite: path → embedding vector
│   │   └── session-log.jsonl # What was read this/last session
│   └── ...
├── global/
│   ├── stats.db         # Cache hit rates, sizes, per-project metrics
│   └── config.json      # Global settings (max size, TTL, etc.)
└── server.pid           # Running server PID
```

### MCP Tools

| Tool | Purpose |
|------|---------|
| `cache_lookup` | Given file path + project root, return cached content if hash matches |
| `cache_store` | Store file content, compute SHA256, optionally embed |
| `cache_invalidate` | Invalidate entries by path pattern or project |
| `cache_warm` | Pre-warm cache for a project (read all tracked files) |
| `cache_stats` | Hit rate, size, per-project breakdown |
| `embedding_query` | Semantic search across cached embeddings |
| `embedding_index` | Trigger (re)indexing for a project |
| `session_track` | Record what files were read this session for dedup |
| `session_diff` | Compare current session reads vs last session |

### Invalidation Strategy

1. **Read-time validation:** On `cache_lookup`, stat the file and compare mtime + size. If changed, re-hash. If hash differs, invalidate.
2. **Git hook integration:** Post-commit hook calls `cache_invalidate --changed` using `git diff --name-only HEAD~1` to proactively invalidate changed files.
3. **TTL fallback:** Entries older than 7 days without access are evicted (configurable).

### Embedding Layer

- Reuse `intersearch` embedding client (all-MiniLM-L6-v2, 384d) as the default model
- Store vectors in per-project SQLite (consistent with intersearch's blob format)
- Support Ollama backends for larger models (bge-large, 1024d) — consistent with tldr-swinton
- Incremental indexing: only embed files that changed since last index

### Integration Points

| Plugin | Integration |
|--------|------------|
| **tldr-swinton** | Read `cache_lookup` before disk, write `cache_store` after analysis. Persist `.tldr/index/` vectors to intercache embeddings. |
| **intersearch** | Share embedding model and vector storage. Query intercache instead of per-session re-embedding. |
| **intermem** | Cache MEMORY.md content hashes for stability detection (supplement `.intermem/stability.jsonl`). |
| **interflux** | Cache domain profiles and knowledge files (flux-drive reads these every review). |
| **clavain** | SessionStart hook calls `cache_warm` for known project files. SessionEnd calls `session_track` flush. |

## Key Decisions

1. **MCP server, not library** — persistent daemon, multi-session safe, tool-discoverable
2. **SHA256 content-addressed** — automatic invalidation, free dedup
3. **Per-project indexes, global blob store** — blobs deduplicate across projects, indexes are project-scoped
4. **intersearch embedding model** — reuse existing 384d embeddings rather than building new infra
5. **Lazy embedding** — embed on first semantic query, not on every cache store (avoid wasted compute)
6. **Opt-in for plugins** — each plugin chooses to integrate, no automatic interception

## Open Questions

1. **Cache size limits** — What's a reasonable default? 1GB? 5GB? Per-project or global cap?
2. **Security** — Cached file content persists after session. Is this a privacy concern for sensitive repos? Need a `cache_purge --project` escape hatch.
3. **Concurrent writes** — Two sessions caching the same file simultaneously. SQLite WAL handles reads, but blob writes need atomic rename.
4. **Embedding model upgrades** — When intersearch upgrades models, old embeddings are invalid. Version the embedding model in the index metadata.
5. **Pre-warming scope** — Warm all tracked files or just files from last N sessions? git-tracked only?

## Non-Goals

- Not replacing tldr-swinton's AST analysis or structural search
- Not replacing intermem's promotion/demotion pipeline
- Not building a full-text search engine (use qmd/intersearch for that)
- Not caching API responses or LLM outputs (only source file content + embeddings)
