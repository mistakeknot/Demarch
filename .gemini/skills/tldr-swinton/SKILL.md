---
name: tldr-swinton
description: "Token-efficient code reconnaissance for LLMs. Autonomous skills save 48-85% tokens via diff-context, semantic search, structural patterns, and symbol analysis. Includes MCP server for direct tool integration."
---
# Gemini Skill: tldr-swinton

You have activated the tldr-swinton capability.

## Base Instructions
# AGENTS.md - AI Agent Instructions for tldr-swinton

This document provides instructions for all AI coding assistants (Claude, Codex, etc.) working with the tldr-swinton codebase.

**Quick start for agents**: Run `tldrs quickstart` for a concise reference guide.

## Project Overview

tldr-swinton is a token-efficient code analysis tool for LLMs. It's a fork of llm-tldr with fixes for TypeScript and Rust support.

**Key directories:**
- `src/tldr_swinton/` - Main Python package
- `evals/` - Evaluation scripts for token efficiency

## Related Projects

| Project | What | Path |
|---------|------|------|
| **interbench** | Agent workbench: run capture + artifact store + eval/regression for tldrs outputs | `/root/projects/Interverse/infra/interbench` |

**interbench integration**: interbench captures tldrs runs as artifacts with metadata tagging, scores token efficiency, and A/B tests output formats. When adding new tldrs formats or flags, 4 files must be kept in sync:
- `/root/projects/Interverse/infra/interbench/scripts/regression_suite.json` — regression queries for each (command, format, flag) combination
- `/root/projects/Interverse/infra/interbench/scripts/ab_formats.py` — `DEFAULT_FORMATS` list for A/B testing
- `/root/projects/Interverse/infra/interbench/demo-tldrs.sh` — demo runs showcasing each format
- `/root/projects/Interverse/infra/interbench/scripts/score_tokens.py` — `parse_*` functions for scoring_hints formats

**Sync workflow** (automated):
```bash
# Check for gaps between tldrs capabilities and interbench coverage
tldrs manifest | python3 /root/projects/Interverse/infra/interbench/scripts/check_tldrs_sync.py

# Or use the Claude Code skill for guided remediation
/tldrs-interbench-sync
```

The `tldrs manifest` command produces a machine-readable JSON of all eval-relevant commands, formats, flags, and scoring hints. The sync check script reads this and reports coverage gaps across all 4 interbench files. The `bump-version.sh` script runs the sync check automatically and warns if gaps exist.

## Quick Reference

```bash
# Install (development)
uv pip install -e .
uv pip install -e ".[semantic-ollama]"  # FAISS backend: Ollama embeddings (768d, lightweight)
uv pip install -e ".[semantic-colbert]" # ColBERT backend: PyLate + PLAID (48d per-token, best quality, ~1.7GB PyTorch)
uv pip install -e ".[semantic]"  # FAISS + sentence-transformers fallback (includes torch)
uv pip install -e ".[full]"      # Full stack (includes Ollama + tiktoken)
uv pip install -e ".[structural]"  # Structural code search (ast-grep)

# Test commands
tldrs extract src/tldr_swinton/embeddings.py    # Extract file info
tldrs structure src/                             # Show code structure
tldrs find "authentication logic"                # Semantic search (requires index)
tldrs index .                                    # Build semantic index

# After code changes
find . -name "*.pyc" -delete && find . -name "__pycache__" -type d -exec rm -rf {} +
uv pip install -e .
```

Full workflow guide: see `docs/agent-workflow.md` or run `tldrs quickstart`.

## Dev Quickstart

```bash
# From repo root
uv pip install -e ".[full]"
tldrs --help

# Smoke check
tldrs extract src/tldr_swinton/embeddings.py
```

## Claude Code Plugin

The repo includes a Claude Code plugin at `.claude-plugin/`. Available commands:

| Command | Description |
|---------|-------------|
| `/tldrs-find <query>` | Semantic code search |
| `/tldrs-diff` | Diff-focused context for recent changes |
| `/tldrs-context <symbol>` | Symbol-level context |
| `/tldrs-structural <pattern>` | Structural code search (ast-grep patterns) |
| `/tldrs-quickstart` | Show quick reference guide |
| `/tldrs-extract <file>` | Extract file structure (functions, classes, imports) |

**Autonomous skills** (Claude invokes automatically based on task context):

| Skill | Trigger |
|-------|---------|
| `tldrs-session-start` | Before reading code for bugs, features, refactoring, tests, reviews, migrations |
| `tldrs-map-codebase` | Understanding architecture, exploring unfamiliar projects, onboarding |
| `tldrs-interbench-sync` | Syncing interbench eval coverage after tldrs capability changes |

**Hooks:**
- `PreToolUse` on **Serena replace_symbol_body** and **rename_symbol**: Runs `tldrs impact` to show callers before edits
- `PostToolUse` on **Read**: Runs compact `tldrs extract` on large code files (>300 lines, once per file per session)
- `SessionStart` (setup.sh): Checks tldrs install, semantic index, ast-grep availability; provides project summary

To use as a plugin:
```bash
/plugin install tldr-swinton   # From interagency-marketplace
```

## Codex Skill (Repo-Scoped)

The repo includes a Codex skill at:
`./.codex/skills/tldrs-agent-workflow/`

This skill mirrors `docs/agent-workflow.md` and is intended for agent onboarding.

## tldr-bench Datasets (Submodule)

Official benchmark datasets live in the `tldr-bench/data` submodule and are
stored in a separate repo: `https://github.com/mistakeknot/tldr-bench-datasets`.

Setup:
```bash
git submodule update --init --recursive
cd tldr-bench/data
git lfs install
git lfs pull
cd -
```

Dataset files are under `tldr-bench/data/data/`. Do not add large dataset files
directly to this repo; update the datasets repo instead and bump the submodule.

## Agent Workflow Checklist

- Read `docs/agent-workflow.md` first.
- Start with `tldrs diff-context --project . --budget 2000`.
- Use `tldrs context <entry>` with `--format ultracompact` and a budget.
- Use `tldrs structure` or `tldrs extract` to discover symbols before context.
- Only open full files when making edits.

## ContextPack Notes (Dev)

- `tldrs context --format json` returns ContextPack JSON (slices; signature-only slices have `code: null`).
- Each ContextPack slice now includes `etag` (signature + code hash).
- Ambiguous entries return candidate lists; re-run with `file.py:func`.
- For API tests, use `get_symbol_context_pack(..., etag=...)` to get `"UNCHANGED"`.

## Delta Context Mode (Multi-Turn Token Savings)

Delta mode tracks which symbols have been delivered to an LLM session and skips
re-sending unchanged code on subsequent calls. This can provide **~60% token savings**
in multi-turn conversations **when code is unchanged between calls**.

**Important caveats:**
- Delta savings collapse to near-zero if code changes between calls
- The 60% figure is conditional on unchanged code - actual savings vary
- Delta mode is most valuable for iterative Q&A, not active editing sessions

### Where Delta Mode Works

- **`diff-context`** (recommended): Full code bodies included, delta mode provides
  real token savings. Use `--session-id <id>` or `--delta` flag.
- **`context`**: Signatures-only by design (95% savings already), delta mode adds
  `[UNCHANGED]` markers but doesn't reduce output size significantly.

### Usage

```bash
# First call - full output, records deliveries
tldrs diff-context --project . --session-id my-session

# Second call - unchanged symbols have code omitted
tldrs diff-context --project . --session-id my-session
# Shows: "Delta: 134 unchanged, 0 changed (100% cache hit)"

# Auto-generate session ID
tldrs diff-context --project . --delta

# Disable delta even with session-id
tldrs diff-context --project . --session-id my-session --no-delta
```

### Design Rationale

The standard `context` command returns signatures-only. Adding code bodies would
defeat the purpose. Delta mode is most valuable with `diff-context` which includes
full code for changed files.

**Note:** The "95% token savings" claim compares signatures to full files. In practice,
agents need full code for editing, so real-world savings for editing workflows are
typically **20-35%** compared to naive file reading approaches.

Session state is stored in `.tldrs/state.sqlite3` and tracks:
- Session ID, repo fingerprint, language
- Per-symbol deliveries with etags (sha256 of signature+code)
- Sessions expire after 24 hours of inactivity

## MCP (Optional)

- MCP server requires `uv pip install mcp`.
- MCP context uses ContextPack for `json/json-pretty/ultracompact` formats.
- Semantic tools: `semantic()` (search), `semantic_index()` (build/rebuild), `semantic_info()` (metadata).
- `semantic_index()` routes through daemon (cache invalidation); `semantic_info()` calls backend directly.

## Output Caps (`--max-lines` / `--max-bytes`)

The `context`, `diff-context`, and `slice` commands support optional post-format
output truncation. These are opt-in — no behavior change without them.

```bash
# Cap context output to 20 lines
tldrs context main --project . --max-lines=20

# Cap diff-context to 4KB
tldrs diff-context --project . --max-bytes=4096

# Both caps together
tldrs context main --project . --max-lines=50 --max-bytes=2048

# Slice with line cap
tldrs slice src/app.py handle_request 42 --max-lines=10
```

When output is truncated, a marker is appended:
`[TRUNCATED: output exceeded --max-lines=20]`

For JSON output (`slice`), the `lines`/`slices` array is trimmed from the end
and `"truncated": true` is added to the result dict. Output remains valid JSON.

## Module Selection (Agents)

Preferred order when gathering context:

```bash
# 1) Diff-first context for recent changes
tldrs diff-context --project . --budget 2000

# 2) Symbol-level context for a specific entry
tldrs context <entry> --project . --depth 2 --budget 2000 --format ultracompact

# 3) Structure / extract for files or folders
tldrs structure src/
tldrs extract path/to/file.py

# 4) Semantic search (requires index)
tldrs index .
tldrs find "authentication logic"

# 5) Structural code search (requires ast-grep-py)
tldrs structural 'def $FUNC($$$ARGS): return None' --lang python

# 6) Deep analysis helpers (optional)
tldrs slice <file> <func> <line>
tldrs cfg <file> <function>
tldrs dfg <file> <function>

# 7) Machine-readable capability manifest (for tooling/eval sync)
tldrs manifest --pretty
```

For large outputs, store as VHS refs:

```bash
tldrs context <entry> --project . --output vhs
tldrs context <entry> --project . --include vhs://<hash>
```

If `tldrs-vhs` isn't on PATH (non-interactive shells), set:

```bash
export TLDRS_VHS_CMD="$HOME/tldrs-vhs/.venv/bin/tldrs-vhs"
```

## Compression Modes

The `--compress` flag on `diff-context` supports two experimental modes:

- **`two-stage`**: Indent-aware block detection + 0/1 knapsack DP for block selection.
  Scores blocks by diff overlap (10x), adjacency (3x), and control-flow keywords (0.5x).
  Saves 35-73% tokens with `--budget` constraint.
- **`chunk-summary`**: Replaces code with LLM-ready summaries (signature + key lines).
  Saves 85-95% but loses implementation detail.

### Promotion Gate

Experimental compression modes **must not be promoted to default** until they pass:
- **>=10% additional savings** vs the current diff+deps baseline on `evals/difflens_eval.py`
- **No regressions** on `evals/agent_workflow_eval.py`
- **At least one manual spot check** on a real repo (correctness/readability)

## Architecture

### Core Extraction Pipeline

```
CLI (cli.py)
    ↓
API layer (api.py)
    ↓
extract_file() → HybridExtractor.extract()
    ↓
Language-specific extraction:
  - Python: Native AST (ast_extractor.py)
  - TypeScript/Rust/Go/etc: tree-sitter (hybrid_extractor.py)
  - Fallback: Pygments signatures
    ↓
ModuleInfo with FunctionInfo objects
    ↓
.to_dict() for JSON serialization
```

### Semantic Search Pipeline (v0.7.5)

```
tldrs index .  → index.py:build_index()
                      ↓
               backend.py:get_backend("auto"|"faiss"|"colbert")
                      ↓
               ┌──────────────────────┬─────────────────────────┐
               │  FAISSBackend        │  ColBERTBackend          │
               │  (faiss_backend.py)  │  (colbert_backend.py)    │
               │  768d single-vector  │  48d per-token (PLAID)   │
               │  Ollama/SentenceT    │  PyLate + LateOn-Code    │
               └──────┬───────────────┴──────────┬──────────────┘
                      ↓                          ↓
               .tldrs/index/{meta.json}    .tldrs/index/plaid/
               vectors.faiss, units.json   PLAID index files

tldrs find "query" → index.py:search_index()
                          ↓
                    Lexical fast-path for identifiers (BM25 exact match)
                          ↓
                    Backend.search() → hybrid RRF fusion (semantic + BM25)
```

**SearchBackend Protocol** (`backend.py`): `build()`, `search()`, `load()`, `save()`, `info()`.
Both backends implement this runtime-checkable protocol. `get_backend("auto")` reads
existing index metadata to select the right backend, or prefers ColBERT if available.

### Key Data Structures

**FunctionInfo** (`ast_extractor.py:27`):
```python
@dataclass
class FunctionInfo:
    name: str
    params: list[str]
    return_type: str | None
    docstring: str | None
    is_method: bool = False
    is_async: bool = False
    decorators: list[str] = field(default_factory=list)
    line_number: int = 0
    language: str = "python"  # Controls signature() output format
```

The `language` field is critical - it determines the output format of `signature()`:
- `"typescript"` → `async function name(params): Type`
- `"rust"` → `fn name(params) -> Type`
- `"python"` (default) → `def name(params) -> Type`

**ModuleInfo** (`ast_extractor.py:131`): Container for file analysis results.

**CodeUnit** (`semantic/backend.py`): Minimal metadata for semantic search results (id, name, file, line, unit_type, signature, file_hash).

### Language Support

Language detection happens in multiple places:
1. `cli.py:EXTENSION_TO_LANGUAGE` - Maps file extensions to language names
2. `hybrid_extractor.py:_detect_language()` - Runtime detection from extension
3. `api.py:get_code_structure()` - Auto-detection for single files

## Critical Rules

### Import Convention

All internal imports MUST use relative imports:
```python
# CORRECT
from .hybrid_extractor import HybridExtractor
from .ast_extractor import FunctionInfo

# WRONG - imports from old llm-tldr package!
from tldr.hybrid_extractor import HybridExtractor
```

### Language Field Required

When creating `FunctionInfo` objects for non-Python languages, ALWAYS set the `language` field:
```python
FunctionInfo(
    name=func_name,
    params=params,
    return_type=return_type,
    docstring=None,
    language="typescript",  # REQUIRED for correct signature format
)
```

### Function Name Cleaning

TypeScript/JavaScript function names must be cleaned of modifiers:
```python
for prefix in ("export ", "async ", "default "):
    if name.startswith(prefix):
        name = name[len(prefix):]
```

### Embeddings Must Be L2-Normalized (FAISS Backend)

FAISS IndexFlatIP expects normalized vectors for cosine similarity:
```python
embedding = embedding / np.linalg.norm(embedding)  # Required!
```
This is handled internally by `_l2_normalize()` in `faiss_backend.py`. ColBERT uses per-token
late interaction scoring (MaxSim), not cosine — normalization is not needed there.

### Incremental Index Updates

Both backends support incremental updates: only new/changed files get re-embedded.
- **FAISS**: reconstructs vectors for unchanged files via `faiss.reconstruct()`
- **ColBERT**: uses PLAID `add_documents()` for incremental adds. Cannot delete — triggers
  full rebuild when deletions >= 20% of index. Hard rebuild forced after 50 incremental updates.

## Common Tasks

### Adding a New Language

1. Add tree-sitter grammar to `pyproject.toml` dependencies
2. Add extension mapping in `cli.py:EXTENSION_TO_LANGUAGE`
3. Add signature format in `FunctionInfo.signature()` (`ast_extractor.py`)
4. Add extraction method in `HybridExtractor` (`hybrid_extractor.py`)
5. Add to language maps in `api.py:get_code_structure()`

### Fixing Signature Formatting

The `FunctionInfo.signature()` method (`ast_extractor.py:39-84`) handles all signature formatting. Each language has a branch:

```python
if self.language in ("typescript", "tsx", "javascript"):
    return f"{async_prefix}function {self.name}({params_str}){ret}"
elif self.language == "rust":
    return f"{async_prefix}fn {self.name}({params_str}){ret_rust}"
# ... etc
```

### Semantic Search Backends

Two backends available via the `SearchBackend` protocol:

| Backend | Model | Dimensions | Install | Quality |
|---------|-------|-----------|---------|---------|
| **FAISS** | `nomic-embed-text-v2-moe` (475M) | 768d single-vector | `[semantic-ollama]` | Good |
| **ColBERT** | `LateOn-Code-edge` (17M) | 48d per-token | `[semantic-colbert]` | Best (late interaction) |

```bash
# FAISS backend (lightweight, Ollama embeddings)
uv pip install -e ".[semantic-ollama]"
ollama pull nomic-embed-text-v2-moe
tldrs index . --backend faiss

# ColBERT backend (best quality, requires PyTorch ~1.7GB)
uv pip install -e ".[semantic-colbert]"
tldrs index . --backend colbert

# Auto-detect: uses existing index's backend, or prefers ColBERT if available
tldrs index . --backend auto

# Force full rebuild (reset incremental updates)
tldrs index . --rebuild

# Check index info
tldrs index --info
```

**ColBERT limits:** PLAID indexes can't delete documents — rebuild triggers at >= 20% deletions.
Centroid drift enforced: hard rebuild after 50 incremental updates, warning at 20.

**Concurrency:** Both backends use `threading.RLock` with snapshot pattern for safe concurrent
build/search. Build swaps state atomically under lock; search snapshots state under lock then
releases before expensive operations.

## Debugging

### Verify Correct Module Loaded

```bash
python -c "import tldr_swinton; print(tldr_swinton.__file__)"
python -c "from tldr_swinton.hybrid_extractor import HybridExtractor; import inspect; print(inspect.getfile(HybridExtractor))"
```

### Test Extraction Directly

```bash
python -c "
from tldr_swinton.hybrid_extractor import HybridExtractor
e = HybridExtractor()
r = e.extract('path/to/file.ts')
for f in r.functions[:3]:
    print(f'{f.name}: {f.language} -> {f.signature()}')
"
```

### Check for Import Issues

```bash
grep -r "from tldr\." src/tldr_swinton/ --include="*.py"
```
Should return empty - all imports should be relative (`.`).

### Check Index Health

```bash
tldrs index --info                    # Show index stats
ls -la .tldrs/index/                   # Check index files exist
```

## Testing

### Manual Testing

```bash
# TypeScript - should show "function" not "def"
tldrs extract path/to/file.ts | grep signature

# Rust - should show "fn" not "def"
tldrs extract path/to/file.rs | grep signature

# Single file structure - should work and detect language
tldrs structure path/to/file.ts | grep language
```

### After Making Changes

1. Clear Python cache:
   ```bash
   find . -name "*.pyc" -delete
   find . -name "__pycache__" -type d -exec rm -rf {} +
   ```

2. Reinstall in development mode:
   ```bash
   uv pip install -e .
   ```

3. Verify the correct module is loaded:
   ```bash
   python -c "import tldr_swinton; print(tldr_swinton.__file__)"
   ```

### Evals

```bash
# Token efficiency eval (basic)
python evals/token_efficiency_eval.py

# Semantic search eval
python evals/semantic_search_eval.py

# Agent workflow eval (realistic Claude Code scenarios)
python evals/agent_workflow_eval.py
```

The agent workflow eval tests real token savings for code modification tasks (not just search output vs raw code).

## File Reference

| File | Purpose |
|------|---------|
| `cli.py` | CLI entry point, argument parsing |
| `api.py` | High-level API functions |
| `ast_extractor.py` | Data structures, Python extraction |
| `hybrid_extractor.py` | Multi-language extraction via tree-sitter |
| `cfg_extractor.py` | Control flow graph extraction |
| `dfg_extractor.py` | Data flow graph extraction |
| `pdg_extractor.py` | Program dependency graph |
| `signature_extractor_pygments.py` | Fallback signature extraction |
| `semantic/backend.py` | SearchBackend protocol, CodeUnit, SearchResult, get_backend() factory |
| `semantic/faiss_backend.py` | FAISSBackend — Ollama/sentence-transformers + FAISS IndexFlatIP |
| `semantic/colbert_backend.py` | ColBERTBackend — PyLate + PLAID indexing (LateOn-Code-edge) |
| `semantic/index.py` | Thin orchestrator: build_index(), search_index() |
| `semantic/embeddings.py` | Backward-compat shim (re-exports from faiss_backend) |
| `semantic/vector_store.py` | Backward-compat shim (aliases FAISSBackend) |
| `semantic/bm25_store.py` | BM25 keyword index for hybrid search (RRF fusion) |
| `semantic/semantic.py` | Original 5-layer semantic search (legacy) |
| `engines/astgrep.py` | Structural code search via ast-grep |
| `engines/delta.py` | Delta-mode orchestration (session tracking, etag comparison) |
| `manifest.py` | Machine-readable capability manifest for eval sync |

## Operational Notes

### Embedding Model
- Current: `nomic-embed-text-v2-moe` (475M, 768d, MoE)
- **NOT** `nomic-embed-code` (7.1B, 3584d) — that's `manutic/nomic-embed-code`, not drop-in
- Jina-code-0.5b evaluated (896d, SOTA): NOT adopting yet, not on Ollama

### Plugin Structure
- 3 skills: session-start, map-codebase, ashpool-sync
- MCP server `tldr-code` for direct tool calls
- PostToolUse:Read hook (`post-read-extract.sh`) — provides value for large files
- PreToolUse hooks REMOVED (CC bug #17088 noise)

### Gotchas
- Ollama naming: community models use `user/model` format. Always `ollama pull` to verify
- ThreadPoolExecutor + local GPU Ollama: no speedup (GPU serializes internally)
- `--compress blocks`: AST-based segmentation + 0/1 knapsack DP, indent fallback

### Do NOT Adopt
- Stack Graphs: archived Sept 2025
- LSP: conflicts with offline/static analysis approach
- pylate-rs for LateOn-Code-edge: projection head missing, dimension mismatch

## Version History

- **0.7.5** - ColBERT late-interaction search backend
  - Added `SearchBackend` protocol (`backend.py`) with dual backend support
  - Added `ColBERTBackend` via PyLate + PLAID indexing (LateOn-Code-edge, 17M params, 48d/token)
  - Refactored FAISS code into `FAISSBackend` implementing the same protocol
  - Added `semantic_index()` and `semantic_info()` MCP tools for agent parity
  - Thread-safe concurrent build/search via RLock snapshot pattern
  - PLAID centroid drift enforcement (hard rebuild at 50 incremental updates)
  - New optional dep group: `[semantic-colbert]` for pylate
  - `embeddings.py` and `vector_store.py` are now backward-compat shims

- **0.6.2** - interbench sync automation, plugin effectiveness improvements
  - Added `tldrs manifest` — machine-readable JSON of all eval-relevant capabilities
  - Added `/tldrs-interbench-sync` skill for guided interbench eval coverage sync
  - Added `check_tldrs_sync.py` sync check script (reads manifest, reports gaps in 4 interbench files)
  - Broadened skill triggers to match more task types (debug, refactor, tests, migrate)
  - Added Grep `PreToolUse` hook (same suggest-recon as Read hook) — later removed (v0.5+)
  - Setup hook now emits usage guidance for any repo
  - `bump-version.sh` warns if interbench coverage has gaps

- **0.6.1** - Delta engine extraction, parser caching
  - Extracted delta-mode orchestration from `cli.py` into `engines/delta.py`
  - Cached tree-sitter parsers in `cross_file_calls.py` via `@lru_cache`

- **0.6.0** - Wave 2+3 features wired into pipeline
  - Wired Wave 2 and Wave 3 prompt-cache-friendly features into the output pipeline

- **0.5.0** - Skill-first plugin, structural search, compression upgrades
  - Plugin restructured: 4 focused skills replace 1 broad skill
  - Added `tldrs structural` - ast-grep tree-sitter pattern matching
  - Added `@lru_cache` to 14 tree-sitter parser factory functions
  - Upgraded `_two_stage_prune` with indent-based blocks + knapsack DP
  - Added BM25 hybrid search (RRF fusion with semantic search)
  - Upgraded embedding model to `nomic-embed-text-v2-moe` (475M MoE)
  - Added `--max-lines` / `--max-bytes` output caps
  - New optional dep group: `[structural]` for ast-grep-py

- **0.4.0** - Output caps, benchmark infrastructure
  - Added `--max-lines` / `--max-bytes` to context, diff-context, slice
  - Added benchmark harness (`tldrs bench`)
  - Disabled non-demonstrable benchmark variants

- **0.3.0** - Embedding and search upgrades
  - Switched Ollama model to `nomic-embed-text-v2-moe`
  - Added BM25 hybrid search with RRF fusion
  - Parallelized Ollama embedding calls

- **0.2.0** - Semantic search with Ollama support
  - Added `tldrs index` - Build semantic index with Ollama or sentence-transformers
  - Added `tldrs find` - Natural language code search
  - Added `embeddings.py` - Multi-backend embedding support (Ollama/HuggingFace)
  - Added `vector_store.py` - FAISS wrapper with persistent storage
  - Added `index.py` - Index management with incremental updates
  - Index stored in `.tldrs/index/` (vectors.faiss, units.json, meta.json)

- **0.1.0** - Initial fork with TypeScript/Rust signature fixes
  - Fixed `FunctionInfo.signature()` to be language-aware
  - Fixed function name cleaning for TypeScript
  - Fixed single file support in `structure` command
  - Fixed internal imports (tldr → tldr_swinton)


