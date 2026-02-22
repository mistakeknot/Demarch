# Operational Notes & Research References

> Extracted from AGENTS.md. These are operational lessons and research references that inform specific modules but don't need to be in the main agent guide.

## Cross-Cutting Lessons

### Oracle CLI
- Never use `> file` redirect — use `--write-output <path>` (browser mode uses console.log)
- Never wrap with external `timeout` — use `--timeout <seconds>` flag
- Requires: `DISPLAY=:99 CHROME_PATH=/usr/local/bin/google-chrome-wrapper`

### Git Credential Lock
- **Root cause (mk user)**: Shared `server/.gitconfig` had `credential.helper = store --file /root/.claude/git-credentials` — mk can't access `/root/`, so `O_CREAT|O_EXCL` on lock file fails with ENOENT
- **Fix**: Removed credential helper from shared config (`dotfiles-sync/server/.gitconfig`); each user has own credential config in their `.gitconfig`
- **TODO (root)**: Replace root's `.gitconfig` symlink → real file with `[include] path=.../server/.gitconfig` + `[credential] helper = store --file /root/.claude/git-credentials`
- **Diagnosis trick**: `strace -e trace=openat,rename -f git push 2>&1 | grep "credential\|lock"` reveals which credential paths are attempted
- See `docs/solutions/environment-issues/git-credential-lock-multi-user-20260216.md`

### Tmux Cross-User Access (intermux)
- tmux needs 3 layers: directory perms (`711`), socket perms (`777`), and `server-access` ACL
- Fix: `chmod 711 /tmp/tmux-0 && chmod 777 /tmp/tmux-0/default && tmux server-access -a claude-user`
- Intermux uses `TMUX_SOCKET` env var → `-S` flag on all tmux commands

### Plugin Publishing (all plugins)
- **BUG**: A hook auto-runs `interbump.sh` on every `git push` from plugin repos, auto-incrementing in a loop. Use `bash scripts/bump-version.sh <version>` once and accept the version it produces.
- `claude plugins install` runs `--recurse-submodules` — set `update = none` in `.gitmodules` for data-only submodules

### Beads Tracker
- **Migrated from SQLite to Dolt** — storage at `.beads/dolt`, DB name `beads_iv`
- Use `bd` from `~/.local/bin/bd` (v0.52.0), NOT the old `/usr/local/bin/bd`
- `bd sync --from-main` and `bd sync --status` are **obsolete** — use plain `bd sync` only

### Agent Dispatch
- New agent `.md` files created mid-session NOT available as `subagent_type` until restart
- Workaround: `subagent_type: general-purpose` + paste full agent prompt
- Background agents from previous sessions survive context exhaustion

### modernc.org/sqlite (pure Go, no CGO)
- **CTE + UPDATE RETURNING not supported** — `WITH claim AS (UPDATE ... RETURNING 1) SELECT ...` fails with syntax error. Use direct `UPDATE ... RETURNING` with row counting (`rows.Next()`) instead.
- DSN `_pragma` unreliable — always set PRAGMAs explicitly after `sql.Open`
- `SetMaxOpenConns(1)` mandatory for WAL correctness in CLI tools
- Concurrent `sql.Open` from goroutines: first connection claims lock, others get SQLITE_BUSY before `busy_timeout` is set (PRAGMA hasn't run). Don't test concurrent migration from goroutines; test sequentially.

## Research References

- `new-modules-research.md` — embedding model comparisons and papers

### Search Improvements
- BM25 via `rank-bm25`: pure Python, complements vector search for identifiers
- RRF (Reciprocal Rank Fusion): ~20 lines to merge dense + sparse results
- Cross-encoder reranking: post-retrieval precision boost
- ast-grep: structural code search (tree-sitter based, 15k stars)

### Code Compression
- LongCodeZip (ASE 2025): 5.6x compression, training-free, two-stage
- DAST (ACL 2025): AST-aware compression using node information density
- ContextEvolve (Feb 2026 arxiv): multi-agent compression, 33% improvement + 29% token reduction

### Key Papers
- nomic-embed-code: ICLR 2025 (CoRNStack)
- CodeXEmbed: COLM 2025
- LoRACode: ICLR 2025
- LongCodeZip: ASE 2025
- DAST: ACL 2025
- Prompt Compression Survey: NAACL 2025 Oral
- ContextEvolve: arxiv 2602.02597 (Feb 2026)
- Kimi-Dev: SWE-Agent skill priors (60.4% SWE-bench Verified)
