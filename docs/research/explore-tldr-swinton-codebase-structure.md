# tldr-swinton Codebase Structure & Block-Level Compression Integration Plan

**Date**: 2026-02-25  
**Project**: tldr-swinton (Demarch/interverse)  
**Purpose**: Understand codebase architecture to implement "LongCodeZip block-level compression" (within-function block compression using tree-sitter AST + knapsack DP).

---

## 1. Directory Structure & Project Layout

```
/home/mk/projects/Demarch/interverse/tldr-swinton/
├── src/tldr_swinton/
│   ├── __init__.py
│   ├── cli.py                              # CLI entry point (tldrs, tldr-swinton commands)
│   ├── manifest.py                         # Machine-readable capability manifest for interbench
│   ├── presets.py                          # Preset bundles (compact, minimal, multi-turn)
│   └── modules/
│       ├── core/                           # Core analysis & compression pipelines
│       │   ├── mcp_server.py              # MCP server (FastMCP) + daemon lifecycle
│       │   ├── api.py                      # High-level API facade
│       │   ├── block_compress.py           # Block-level compression (AST + knapsack) ⭐
│       │   ├── zoom.py                     # Hierarchical zoom levels (L0-L4)
│       │   ├── contextpack_engine.py       # Context packing + budget allocation
│       │   ├── ast_extractor.py            # AST-based symbol extraction (FunctionInfo, ClassInfo)
│       │   ├── hybrid_extractor.py         # Language dispatch for extraction
│       │   ├── cfg_extractor.py            # Control-flow graph extraction
│       │   ├── dfg_extractor.py            # Data-flow graph extraction
│       │   ├── pdg_extractor.py            # Program dependency graph
│       │   ├── engines/
│       │   │   ├── difflens.py            # Diff-focused context (calls block_compress.py)
│       │   │   ├── astgrep.py             # Structural search (ast-grep)
│       │   │   ├── cfg.py, dfg.py, pdg.py, slice.py
│       │   │   ├── delta.py               # Delta-mode caching
│       │   │   └── ...
│       │   ├── token_utils.py             # Token counting utilities
│       │   ├── import_compress.py         # Import section compression
│       │   ├── strip.py                    # Comment/whitespace stripping
│       │   ├── type_pruner.py             # Type expansion pruning
│       │   ├── symbol_registry.py         # Symbol metadata cache
│       │   ├── daemon.py                   # Unix socket daemon
│       │   ├── project_index.py           # Project-wide symbol index
│       │   ├── output_formats.py          # Output format wrappers
│       │   ├── distill_formatter.py       # Distill/ultracompact formatting
│       │   └── ... (40+ other analysis modules)
│       ├── semantic/                      # Semantic search backends
│       │   ├── backend.py                  # SearchBackend protocol
│       │   ├── faiss_backend.py           # FAISS + BM25
│       │   ├── colbert_backend.py         # ColBERT (PyLate)
│       │   └── ...
│       ├── workbench/                     # Agent workbench UI
│       ├── bench/                         # Benchmarking CLI
│       └── vhs/                           # VHS content-addressed store
├── tests/
│   ├── test_block_compress.py             # Unit tests for block compression ⭐
│   ├── test_zoom.py                       # Zoom level formatting tests
│   ├── test_contextpack_engine.py         # Context packing tests
│   ├── test_difflens.py                   # Diff-context tests
│   └── ~90 other integration/unit tests
├── docs/
│   ├── QUICKSTART.md                      # Quick reference guide
│   ├── PRD.md                              # Product requirements
│   ├── agent-workflow.md                  # Agent workflow guide
│   ├── solutions/patterns/critical-patterns.md
│   └── plans/, research/, brainstorms/, feedback/
├── pyproject.toml                         # Build config + dependencies
├── AGENTS.md                              # Shared agent instructions (25KB)
├── CLAUDE.md                              # Claude Code-specific instructions
├── README.md                              # Main documentation (11KB)
└── scripts/
    ├── bump-version.sh                    # Version bumping + sync verification
    └── check-versions.sh                  # Pre-commit hook for version sync
```

---

## 2. Main Entry Points & MCP Server Registration

### 2.1 CLI Entry Point (`cli.py`)
- **Command**: `tldrs` / `tldr-swinton`
- **Subcommands**: 33+ commands organized in functional domains
  - Extraction: `extract`, `structure`, `tree`, `imports`, `importers`
  - Analysis: `cfg`, `dfg`, `slice`, `calls`, `impact`, `dead`, `arch`, `change-impact`
  - Search: `find` (semantic), `search` (grep), `structural` (ast-grep)
  - Context: `context`, `diff-context`
  - Daemon: `daemon start|stop|status`
  - Introspection: `manifest`, `doctor`, `presets`

### 2.2 MCP Server Entry Point (`mcp_server.py`)
- **Command**: `tldr-mcp`
- **Architecture**: FastMCP wrapper + socket daemon
- **Tool Registration**: 1:1 mapping with CLI commands via `@mcp.tool()` decorator
- **Daemon Lifecycle**:
  - Detects if daemon running via socket at `/tmp/tldr-{hash}.sock`
  - Auto-starts daemon with `subprocess.Popen(..., start_new_session=True)`
  - Waits for daemon ready with 10s timeout
- **MCP Instructions** (in `_INSTRUCTIONS`):
  - Cost ladder (cheapest first): extract → structure → context → diff_context → impact → semantic
  - Emphasizes token efficiency and when to use each tool

### 2.3 Plugin Integration (`.claude-plugin/`)
- **Slash commands** (6):
  - `/tldrs-find`, `/tldrs-diff`, `/tldrs-context`, `/tldrs-extract`, `/tldrs-structural`, `/tldrs-quickstart`
- **Skills** (3, Claude-invoked automatically):
  - `tldrs-session-start` — runs diff-context before reading files
  - `tldrs-map-codebase` — understand unfamiliar projects
  - `tldrs-interbench-sync` — sync eval coverage with capabilities
- **Hooks** (3, automatic enforcement):
  - `setup.sh` — initialize cache, prebuild indexes
  - `pre-serena-edit.sh` — caller analysis before edits/renames
  - `post-read-extract.sh` — intercept Read to suggest recon tools

---

## 3. Existing Compression & Context Levels

### 3.1 Zoom Levels (ZoomLevel enum in `zoom.py`)

```python
L0 = 0  # Module map: file list + 1-line descriptions (minimal)
L1 = 1  # Symbol index: signatures + docstring first line
L2 = 2  # Body sketch: control-flow skeleton (tree-sitter AST traversal)
L3 = 3  # Windowed body: diff-relevant code windows
L4 = 4  # Full body: default (current uncompressed code)
```

**Key insight**: L2 (body sketch) already uses tree-sitter to extract control-flow structure. Block compression is orthogonal—it operates WITHIN L4 code when budget is tight.

### 3.2 Current Compression Strategies in `engines/difflens.py`

Three compression modes when processing diff context:

1. **`compress="two-stage"`** (DiffLens original):
   - Calls `_two_stage_prune(code, start, diff_lines, budget_tokens)`
   - Heuristic pruning: diff regions kept, adjacency bonus
   - NOT block-aware; greedy line-by-line selection

2. **`compress="blocks"`** (NEW, LongCodeZip-inspired):
   - Calls `compress_function_body(code, code_start, diff_lines, budget_tokens, language, use_ast=True)`
   - AST-based block segmentation → knapsack optimization
   - Returns `(compressed_code, block_count, dropped_blocks)` for metadata

3. **`compress="chunk-summary"`**:
   - Generates summary instead of full code
   - Used when budget too tight for even compressed body

**Integration point**: Line 731-741 in `difflens.py`:
```python
if code and compress in ("two-stage", "blocks"):
    if compress == "blocks":
        from ..block_compress import compress_function_body
        code, block_count, dropped_blocks = compress_function_body(...)
    else:
        code, block_count, dropped_blocks = _two_stage_prune(...)
```

---

## 4. Block Compression Implementation (`block_compress.py`)

**Status**: FULLY IMPLEMENTED (462 lines)  
**Paper**: LongCodeZip (ASE 2025, arXiv 2510.00446)

### 4.1 Block Segmentation

#### Option 1: AST-Based (`segment_by_ast()`)
- Uses tree-sitter to parse source into AST
- Identifies top-level statement nodes within function body
- Only extracts **direct children** (not nested scopes)
- Supported languages: `python`, `javascript`, `typescript`, `go`
- Block boundary types:
  - Python: `if_statement`, `for_statement`, `while_statement`, `try_statement`, `with_statement`, `match_statement`, `return_statement`, etc.
  - JavaScript/TypeScript: similar + `switch_statement`, `arrow_function`, etc.
  - Go: similar + `select_statement`, `defer_statement`, `go_statement`, etc.

**Return type**: `list[CodeBlock] | None` (None signals fallback to indent-based)

#### Option 2: Indent-Based Fallback (`segment_by_indent()`)
- Splits at indentation-level transitions + blank lines
- Detects boundaries where indentation changes by 4+ spaces or becomes shallower
- Extracted from DiffLens `_split_blocks_by_indent()`
- **Always returns list** (never None)

#### Gap Filling (`_fill_gaps()`)
- After AST segmentation, fills uncovered line ranges (comments, blank lines) into adjacent blocks
- Prevents orphaned code between AST nodes

### 4.2 Block Scoring (`score_blocks()`)

Mirrors DiffLens `_two_stage_prune()` scoring:

```python
score = 0.0

# 1. Diff overlap: +10.0 per line overlapping with diff
for ln in block.lines:
    if ln in diff_set:
        score += 10.0

# 2. Control-flow keywords: +0.5 per line with if/for/while/return/etc.
for line in block.text.splitlines():
    if line.startswith(("if ", "for ", "while ", "return ", ...)):
        score += 0.5

# 3. Adjacency bonus: +3.0 for blocks adjacent to diff blocks
if block_idx - 1 or block_idx + 1 is in diff_block_indices:
    score += 3.0
```

**Returns**: `(scores: list[float], must_keep: set[int])`
- `must_keep` = diff-overlapping block indices (or `{0}` if no diff)

### 4.3 Knapsack Selection (`knapsack_select()`)

0/1 knapsack DP to select highest-value blocks within token budget.

```python
# Reserve budget for must-keep blocks
must_keep_cost = sum(sizes[i] for i in must_keep)
remaining_budget = max(0, budget_tokens - must_keep_cost)

# Build DP table (with scaling for large budgets)
# W ≤ 5000 for tractability; scale down if needed
dp[w] = max(dp[w], dp[w - size] + score)

# Traceback: reconstruct selected block indices
```

**Returns**: `list[int]` (sorted selected block indices)

### 4.4 Main Entry Point (`compress_function_body()`)

```python
def compress_function_body(
    code: str,
    code_start: int = 0,
    diff_lines: list[int] | None = None,
    budget_tokens: int | None = None,
    language: str = "python",
    use_ast: bool = True,
) -> tuple[str, int, int]:
    """Returns (compressed_code, block_count, dropped_blocks)"""
```

**Pipeline**:
1. Segment: AST → fallback to indent
2. Check if already fits (no compression needed)
3. Score: diff overlap + control-flow + adjacency
4. Select: knapsack DP with must-keep
5. Render: keep selected blocks, replace elided ranges with `# ... (N lines elided)` markers

**Return signature** matches DiffLens for drop-in compatibility.

---

## 5. Where Block Compression Integrates

### 5.1 Context Pipeline (`engines/difflens.py`)

**Flow**:
1. Load project index + symbol graph
2. Query diff symbols (changed code)
3. For each symbol, compute relevance + diff_line_list
4. **Compress function bodies** (line 731-741):
   ```python
   if compress == "blocks":
       code, block_count, dropped_blocks = compress_function_body(
           code,
           code_start=start,
           diff_lines=diff_line_list,
           budget_tokens=budget_tokens,
           language=language,
           use_ast=True,
       )
   ```
5. Pack into candidates with metadata (block_count, dropped_blocks)
6. Build ContextPack via `ContextPackEngine.build_context_pack()`
7. Delivery + attention tracking

### 5.2 Metadata Storage

**In Candidate/ContextPack**:
```python
meta: dict[str, object] = {}
if block_count:
    meta["block_count"] = block_count
if dropped_blocks:
    meta["dropped_blocks"] = dropped_blocks
```

Allows downstream tools to see compression stats.

### 5.3 Test Coverage

**`test_block_compress.py`** (306 lines):
- `TestSegmentByIndent`: fallback behavior (empty, single-line, indent transitions)
- `TestSegmentByAst`: Python AST parsing, unsupported languages → None
- `TestSegmentIntoBlocks`: dispatcher (prefer AST, fallback to indent)
- `TestScoreBlocks`: diff overlap, control-flow bonus, adjacency, default must-keep
- `TestKnapsackSelect`: all-fit, tight budgets, must-keep enforcement
- `TestCompressFunctionBody`: no-op when fits, elision markers, diff anchoring, AST-disabled path

---

## 6. Tree-Sitter Integration

### 6.1 Parser Caching (`zoom.py`)

```python
@lru_cache(maxsize=None)
def _get_parser(language: str):
    """Cached tree-sitter parser per language."""
    norm = _normalize_language(language)
    lang = _tree_sitter_language(norm)
    if lang is None:
        return None
    return Parser(lang)  # Cached for lifetime
```

**Supported languages**:
- Core (in dependencies): python, javascript, typescript, go
- Optional (install `[all]`): rust, java, c, cpp, ruby, kotlin, swift, scala, lua, elixir, csharp

### 6.2 Language Normalization

```python
_LANGUAGE_ALIASES = {
    "py": "python", "js": "javascript", "jsx": "javascript",
    "ts": "typescript", "tsx": "typescript", "go": "go",
}
```

### 6.3 Tree-Sitter Usage

**In `block_compress.py`**:
- `segment_by_ast()`: parses source, walks top-level AST children, extracts line ranges
- `_find_body_children()`: if single function/class, descends into its body

**In `zoom.py`** (L2 sketch extraction):
- `extract_body_sketch()`: walks all AST nodes, emits control-flow keywords (if/for/while/return/etc.)
- `_sketch_line()`: formats each control-flow node as indented keyword line

### 6.4 Error Handling

- **Parse failure**: logs and continues (graceful degradation)
- **Missing parser**: returns None, triggers fallback
- **Unsupported language**: returns None, triggers indent-based segmentation

---

## 7. Python Package Structure

### 7.1 Dependencies (`pyproject.toml`)

**Core**:
```
tree-sitter>=0.21.0
tree-sitter-{python,javascript,typescript,go,rust,java,c,cpp,ruby}>=0.21.0
pygments>=2.0
pathspec>=0.11.0
ast-grep-py>=0.30
```

**Optional**:
- `semantic-ollama`: FAISS + local embeddings (768d, lightweight)
- `semantic-colbert`: PyLate ColBERT (48d per-token, best quality, ~1.7GB PyTorch)
- `semantic`: FAISS + sentence-transformers (includes torch)
- `mcp-server`: MCP protocol support

### 7.2 Entry Points

```toml
[project.scripts]
tldr-swinton = "tldr_swinton.cli:main"
tldrs = "tldr_swinton.cli:main"
tldr-mcp = "tldr_swinton.modules.core.mcp_server:main"
```

### 7.3 Build System

- **Backend**: hatchling
- **Python**: ≥3.10
- **Wheels**: `src/tldr_swinton/` → `site-packages/tldr_swinton/`

---

## 8. Test Structure & Patterns

### 8.1 Test Organization

**By concern**:
- `test_block_compress.py` — block segmentation, scoring, knapsack, end-to-end compression
- `test_zoom.py` — zoom level formatting (L0-L4)
- `test_difflens.py` — diff-context diff_lines extraction + scoring
- `test_contextpack_engine.py` — budget allocation + context packing
- `test_two_stage_prune.py` — original DiffLens pruning (baseline)

### 8.2 Common Patterns

```python
# Sample code fixtures
PYTHON_FUNCTION = "def foo(x):\n    if x:\n        return x + 1\n    return 0"
PYTHON_MULTIBLOCK = "..."

# Assertions
assert block.start_line == 0
assert block.end_line == 5
assert block.token_count > 0

# Optional skip for missing tree-sitter
try:
    import tree_sitter_python
    can_parse_ast = True
except ImportError:
    can_parse_ast = False

if not can_parse_ast:
    pytest.skip("tree-sitter-python not installed")
```

### 8.3 Running Tests

```bash
pytest tests/test_block_compress.py -v
pytest tests/ -k "block_compress" -v
```

---

## 9. Integration Points for Implementation

### 9.1 Where to Add Block-Level Compression Features

**Current state**: Basic block compression fully implemented.

**Potential enhancements** (if extending):

1. **Smarter block scoring**:
   - Add heuristics: data-flow impact, variable use counts
   - Integration point: `score_blocks()` in `block_compress.py`

2. **Relevance estimation**:
   - Use `contexttiness` metrics (connection to query)
   - Integration: pass relevance scores to knapsack via block metadata

3. **Language-specific block boundaries**:
   - Add more granular split logic (e.g., Rust match arms as blocks)
   - Integration: extend `_BLOCK_BOUNDARY_NODES` in `block_compress.py`

4. **Multi-pass compression**:
   - First pass: function-level (current)
   - Second pass: within-class blocks, within-module blocks
   - Integration: add `compress_class_body()`, `compress_module_body()`

5. **Elision rendering improvements**:
   - Interactive "expand elided block" command
   - Integration: `format_at_zoom()` + output format wrappers

### 9.2 Key Files to Understand for Extensions

| File | Purpose | Touchpoints |
|------|---------|-----------|
| `block_compress.py` | Block segmentation + knapsack | AST node types, scoring, DP algorithm |
| `engines/difflens.py` | Diff context pipeline | Compression call site, metadata flow |
| `zoom.py` | Zoom level formatting | L2 sketch, control-flow skeleton |
| `contextpack_engine.py` | Budget allocation | Token budgeting, slice ordering |
| `token_utils.py` | Token counting | Estimate accuracy for knapsack |
| `ast_extractor.py` | Symbol extraction | Language-aware signatures |

---

## 10. Architecture Summary

```
┌─────────────────────────────────────────────────────────────┐
│ User/Agent (Claude Code, CLI, MCP Client)                  │
└────────────────────┬────────────────────────────────────────┘
                     │
        CLI (cli.py) │ or MCP (mcp_server.py)
                     ↓
┌─────────────────────────────────────────────────────────────┐
│ Project Index (project_index.py)                            │
│ - Symbol registry, call graph, file sources                 │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ↓
┌─────────────────────────────────────────────────────────────┐
│ Context Pipeline (engines/difflens.py)                      │
│ 1. Query diff symbols                                       │
│ 2. Compute relevance + diff lines                           │
│ 3. Extract code for each symbol                             │
│ 4. ★ COMPRESS function bodies (block_compress.py)          │
│ 5. Pack into candidates                                     │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ↓
┌─────────────────────────────────────────────────────────────┐
│ ContextPackEngine (contextpack_engine.py)                   │
│ - Budget allocation (tokens remaining)                      │
│ - Zoom level formatting (zoom.py)                           │
│ - Type pruning, import compression                          │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ↓
┌─────────────────────────────────────────────────────────────┐
│ Output Formatting (output_formats.py)                       │
│ - JSON, ultracompact, cache-friendly, etc.                  │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ↓
         User receives ContextPack
      (slices with code, metadata, stats)
```

**Key compression integration**:
- Input: Full function body code + diff_lines + budget
- Processing: Segment → Score → Knapsack Select → Render with elision markers
- Output: Compressed code + metadata (block_count, dropped_blocks)
- Consumption: ContextPackEngine uses compressed code in packing, metadata for delivery tracking

---

## 11. Related Documentation

- **AGENTS.md** (669 lines): Comprehensive agent instructions, architecture, tools, debugging
- **README.md** (296 lines): CLI surface, commands, presets, output formats
- **CLAUDE.md**: Claude Code plugin setup, version bumping, publishing workflow
- **docs/PRD.md**: Product requirements and vision
- **docs/QUICKSTART.md**: Quick reference guide for common tasks

---

## Summary for Implementation

**To implement within-function block-level compression (LongCodeZip)**:

1. **Already implemented**: `block_compress.py` provides full AST+knapsack pipeline
2. **Integration point**: Called from `engines/difflens.py` line 734 when `compress="blocks"`
3. **Tree-sitter usage**: Via `zoom.py:_get_parser()` and `block_compress.py:segment_by_ast()`
4. **Test coverage**: `test_block_compress.py` with 306 lines of behavioral tests
5. **Metadata flow**: block_count, dropped_blocks tracked in Candidate.meta dict
6. **Zoom levels**: L2 (sketch) separate from L4 (full); block compression orthogonal
7. **Fallback strategy**: Indent-based segmentation for unsupported languages
8. **Extension points**: Scoring heuristics, language-specific boundaries, multi-pass compression

**Key files to review before extending**:
- `/home/mk/projects/Demarch/interverse/tldr-swinton/src/tldr_swinton/modules/core/block_compress.py` (462 lines)
- `/home/mk/projects/Demarch/interverse/tldr-swinton/src/tldr_swinton/modules/core/engines/difflens.py` (850+ lines, lines 731-741 are integration)
- `/home/mk/projects/Demarch/interverse/tldr-swinton/src/tldr_swinton/modules/core/zoom.py` (263 lines)
- `/home/mk/projects/Demarch/interverse/tldr-swinton/tests/test_block_compress.py` (306 lines)
