# PRD: Intercache — Cross-Session Semantic Cache

**Bead:** iv-p4qq
**Date:** 2026-02-23

## Problem

Claude Code re-reads the same files every session. Large repos spend 2-5 minutes in cold start. tldr-swinton builds per-session indexes that don't persist. intersearch re-embeds the same content repeatedly. There is no cross-session cache layer.

## Goal

Ship an MCP server (`intercache`) that provides content-addressed caching, embedding persistence, and semantic deduplication — reducing cold start time and eliminating redundant file reads across sessions.

## Core Capabilities

### F0: Content-Addressed Blob Store
- SHA256-keyed blob storage at `~/.intercache/blobs/`
- 2-char prefix sharding for filesystem scalability
- Atomic writes via tmp + rename pattern
- Deduplication across projects (same content = one blob)

### F1: Per-Project Manifest
- Path → SHA256 mapping with mtime/size for fast validation
- Session read log (what was accessed this/last session)
- Git integration: post-commit hook invalidates changed files

### F2: Embedding Persistence
- Per-project SQLite with path → embedding vector
- Reuse intersearch's all-MiniLM-L6-v2 (384d) as default model
- Incremental indexing: only embed changed files
- Model version in metadata for upgrade invalidation

### F3: MCP Tools
- `cache_lookup` — return cached content if hash matches current file
- `cache_store` — store file content with SHA256 key
- `cache_invalidate` — invalidate by path, pattern, or project
- `cache_warm` — pre-warm cache for a project's tracked files
- `cache_stats` — hit rate, size, per-project breakdown
- `embedding_query` — semantic search across cached embeddings
- `session_track` — record file accesses for dedup across sessions

### F4: Plugin Integration Hooks
- SessionStart: call `cache_warm` for last session's files
- PostCommit: call `cache_invalidate --changed` for modified files
- Other plugins: opt-in via MCP tool calls (no automatic interception)

## Non-Goals

- Full-text search engine (use qmd/intersearch)
- Caching API responses or LLM outputs
- Replacing tldr-swinton's AST analysis
- Replacing intermem's promotion pipeline
- Auto-intercepting file reads (too magical, security concern)

## Implementation Phases

### Phase 1: Core Cache (MVP)
- Content-addressed blob store + manifest
- `cache_lookup`, `cache_store`, `cache_invalidate`, `cache_stats` tools
- MCP server scaffold (stdio transport)
- ~2 days

### Phase 2: Session Intelligence
- Session read tracking and dedup
- `session_track`, `session_diff` tools
- Cache warming from last session's manifest
- Git post-commit hook for invalidation
- ~1 day

### Phase 3: Embedding Layer
- Per-project embedding storage (SQLite + intersearch model)
- `embedding_query`, `embedding_index` tools
- Incremental re-indexing on file change
- ~2 days

## Dependencies

- `intersearch` — embedding model and vector utilities
- `interbase` SDK — for ecosystem integration (nudge protocol, guard functions)
- Git — for post-commit invalidation hook

## Success Metrics

- Cold start time reduction: >50% for repos previously visited
- Cache hit rate: >80% for unchanged files between sessions
- Embedding persistence: 0 re-embedding calls for unchanged code between sessions

## Open Questions → Decisions

| Question | Decision |
|----------|----------|
| Cache size limit | 2GB global default, configurable via `config.json` |
| Security for sensitive repos | `cache_purge --project` wipes all cached data. No encryption at rest for v1. |
| Concurrent writes | Atomic blob writes (tmp + rename). SQLite WAL for manifest/embeddings. |
| Embedding model upgrades | Version in `meta.json`. Mismatch triggers full re-index. |
| Pre-warming scope | Files from last 3 sessions, git-tracked only, max 1000 files |
