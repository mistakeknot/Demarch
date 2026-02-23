# Intercache Implementation Plan

**Bead:** iv-p4qq
**Date:** 2026-02-23
**Phases:** 3 (Core → Session → Embeddings)

## Phase 1: Core Cache (MVP) — ~2 days

### Task 1.1: Plugin scaffold + MCP server
- Create `interverse/intercache/` with standard plugin structure
- `.claude-plugin/plugin.json` with MCP server declaration (stdio)
- `integration.json` declaring ecosystem_only=false
- Python MCP server at `server/intercache_server.py`
- ~0.5 day

### Task 1.2: Content-addressed blob store
- `server/store.py` — blob storage with SHA256 keying
- 2-char prefix sharding (`~/.intercache/blobs/ab/cd1234...`)
- Atomic writes: write to `.tmp` then `os.rename()`
- `store(content: bytes) -> str` returns SHA256 hash
- `lookup(hash: str) -> bytes | None`
- `delete(hash: str)`
- `stats() -> {blob_count, total_bytes}`
- ~0.5 day

### Task 1.3: Per-project manifest
- `server/manifest.py` — SQLite database per project
- Schema: `files(path TEXT PK, sha256 TEXT, mtime REAL, size INT, last_accessed TEXT)`
- `update(path, sha256, mtime, size)` — upsert mapping
- `lookup(path) -> {sha256, mtime, size} | None`
- `validate(path) -> bool` — stat file, compare mtime+size, re-hash if needed
- `list_stale(max_age_days=7) -> [path]`
- ~0.5 day

### Task 1.4: MCP tools (cache_lookup, cache_store, cache_invalidate, cache_stats)
- `cache_lookup(path, project_root)` — validate manifest, return blob content or miss
- `cache_store(path, content, project_root)` — hash, store blob, update manifest
- `cache_invalidate(path_pattern, project_root)` — delete matching manifest entries
- `cache_stats(project_root?)` — hit/miss rates, storage size
- ~0.5 day

## Phase 2: Session Intelligence — ~1 day

### Task 2.1: Session tracking
- `server/session.py` — per-project JSONL session log
- Record: `{session_id, path, timestamp, action: read|write}`
- `session_track(session_id, path, action)` — append to log
- `session_diff(current_session, prev_session)` — files read in prev but not current
- ~0.5 day

### Task 2.2: Cache warming + git hook
- `cache_warm(project_root)` — re-validate last N sessions' files, pre-populate manifest
- `hooks/post-commit.sh` — git post-commit hook that calls `cache_invalidate --changed`
- Only invalidates git-tracked files modified in the commit
- ~0.5 day

## Phase 3: Embedding Layer — ~2 days

### Task 3.1: Embedding storage
- `server/embeddings.py` — per-project SQLite with vector storage
- Schema: `embeddings(path TEXT PK, sha256 TEXT, model TEXT, vector BLOB, updated TEXT)`
- Reuse intersearch's `vector_to_bytes`/`bytes_to_vector` format
- Model version tracking in table metadata
- ~0.5 day

### Task 3.2: Embedding tools
- `embedding_index(project_root, paths?)` — embed files not yet indexed or changed
- `embedding_query(query, project_root, top_k=10)` — cosine similarity search
- Lazy loading: intersearch model loaded on first embedding call
- Incremental: only re-embed files where sha256 changed
- ~1 day

### Task 3.3: Integration documentation
- `AGENTS.md` with tool reference and integration patterns
- Example integration for tldr-swinton and interflux
- ~0.5 day

## Files Created

| File | Purpose |
|------|---------|
| `interverse/intercache/.claude-plugin/plugin.json` | Plugin manifest |
| `interverse/intercache/.claude-plugin/integration.json` | Ecosystem integration |
| `interverse/intercache/server/intercache_server.py` | MCP server entry point |
| `interverse/intercache/server/store.py` | Content-addressed blob store |
| `interverse/intercache/server/manifest.py` | Per-project file manifest |
| `interverse/intercache/server/session.py` | Session tracking |
| `interverse/intercache/server/embeddings.py` | Embedding storage + search |
| `interverse/intercache/hooks/post-commit.sh` | Git hook for invalidation |
| `interverse/intercache/CLAUDE.md` | Quick reference |
| `interverse/intercache/AGENTS.md` | Full development guide |
