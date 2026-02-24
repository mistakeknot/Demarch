# Intermap: Project-Level Code Mapping — Implementation Plan
**Phase:** executing (as of 2026-02-24T01:38:59Z)

> **For Claude:** REQUIRED SUB-SKILL: Use clavain:executing-plans to implement this plan task-by-task.

**Goal:** Complete the Intermap extraction from tldr-swinton, fix existing bugs, then add cross-project dependency graphs, architecture pattern detection, and live change awareness.

**Architecture:** Go MCP server (mark3labs/mcp-go) + Python analysis engine (AST/tree-sitter). 6 existing tools, 3 new ones. JSON-over-stdio subprocess bridge between Go and Python. Two-level caching (Go: 5min TTL LRU, Python: in-process mtime-keyed).

**Tech Stack:** Go 1.22+ (mcp-go SDK), Python 3.11+ (ast, tree-sitter optional), SQLite-free (stateless cache only)

---

## Review Findings (flux-drive, 2026-02-23)

**Agents:** Architecture, Correctness, Quality/Style — all three reviewed against live codebase.

### Required Amendments (apply during execution)

**P0 — Compile blockers:**
1. **Tasks 7/8/9 Go registration:** Use `server.ServerTool` factory functions + `s.AddTools()`, NOT `server.AddTool()` inline. Use `req.GetArguments()` + type assertion, NOT `req.Params.Arguments`. Use `jsonResult(result)`, NOT `mcp.NewToolResultText(result)`.
2. **Task 3 broken import:** After moving `vendor/workspace.py` → `intermap/workspace.py`, line 241 `from .tldrsignore import ...` must become `from .ignore import ...`. Plan's grep won't catch this.

**P1 — Wrong results:**
3. **Task 7 go.mod regex:** Must handle block-form `replace (...)`. Fix: match `\S+\s+=>\s+(\.\./\S+)` without anchoring on `replace` keyword.
4. **Task 9 git error check:** Add `if result.returncode != 0` after second `git diff` subprocess call.
5. **Tasks 7/8/9 tests:** Use `tmp_path` fixture-based synthetic repos, not just live `DEMARCH_ROOT`. Remove vacuous `if "interlock" in projects:` guard.
6. **Tasks 7/8/9 dispatch:** Use explicit `args.get("key", default)` not `**args`, matching existing `analyze.py` style.
7. **Task 1 incomplete:** Also fix `test_analyze.py` hardcoded paths (lines 8, 9, 22, 40).
8. **Task 3 dirty_flag.py:** Do NOT promote to first-class module. Remove `use_session` code path from `change_impact.py` at extraction time.

**P2 — Fix during implementation:**
9. `_discover_projects`: Add `.git` dir check to match Go `registry.Scan()`.
10. `project_lookup`: Use `setdefault` to handle duplicate project names.
11. pyproject.toml regex: `[\w-]+` for hyphenated package names.
12. `_scan_plugin_deps`: Remove generic substring scan, keep only explicit env-var patterns.
13. `_symbol_overlaps`: Remove proximity heuristic, use direct `line_number in changed_lines` only.
14. Hunk parser: Parse both `-` and `+` sides of `@@` header; handle `count=0`.
15. HTTP handler regex: Require router-like receiver prefix to avoid false positives.
16. FastMCP regex: Use `\([^)]*\)` instead of `\(\s*\)` to match named-argument decorators.

---

## Task 1: Fix existing test paths (pre-existing bugs)

**Files:**
- Modify: `internal/registry/registry_test.go`
- Modify: `python/tests/test_code_structure.py`

**Step 1: Fix registry test path**

The `findInterverseRoot` helper looks for the old `/root/projects/Interverse/` path. Update to use the monorepo structure.

```go
// internal/registry/registry_test.go — replace findInterverseRoot
func findInterverseRoot(t *testing.T) string {
	t.Helper()
	// Walk up from test dir to find Demarch monorepo root
	dir, err := os.Getwd()
	if err != nil {
		t.Skipf("cannot get working directory: %v", err)
	}
	for dir != "/" {
		if _, err := os.Stat(filepath.Join(dir, "interverse")); err == nil {
			return dir
		}
		dir = filepath.Dir(dir)
	}
	t.Skip("not running inside Demarch monorepo")
	return ""
}
```

**Step 2: Fix Python test path**

```python
# python/tests/test_code_structure.py — update hardcoded path
# OLD: "/root/projects/Interverse/plugins/intermap"
# NEW: Use __file__ to resolve relative to test location
import os
INTERMAP_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
```

Update `test_code_structure_python` to use `INTERMAP_ROOT` instead of the hardcoded path.

**Step 3: Run tests to verify fixes**

Run: `cd interverse/intermap && go test ./... && PYTHONPATH=python python3 -m pytest python/tests/ -v`
Expected: All tests pass

**Step 4: Commit**

```bash
git add internal/registry/registry_test.go python/tests/test_code_structure.py
git commit -m "fix: update test paths for monorepo structure"
```

---

## Task 2: Audit existing MCP tools (F1)

**Files:**
- Create: `docs/audit/2026-02-23-intermap-tool-audit.md`

This is a research task — run each tool against real projects, document results.

**Step 1: Build the MCP binary**

Run: `cd interverse/intermap && go build -o bin/intermap-mcp ./cmd/intermap-mcp/`

**Step 2: Test project_registry**

```bash
echo '{"jsonrpc":"2.0","method":"tools/call","params":{"name":"project_registry","arguments":{"root":"/home/mk/projects/Demarch"}},"id":1}' | \
  PYTHONPATH=python CLAUDE_PLUGIN_ROOT=. ./bin/intermap-mcp
```

Document: How many projects found? Correct languages? Missing projects? Response time?

**Step 3: Test resolve_project**

```bash
echo '{"jsonrpc":"2.0","method":"tools/call","params":{"name":"resolve_project","arguments":{"path":"/home/mk/projects/Demarch/core/intermute/internal/http/handlers.go"}},"id":2}' | \
  PYTHONPATH=python CLAUDE_PLUGIN_ROOT=. ./bin/intermap-mcp
```

Document: Correct project resolution? Edge cases (root files, nested dirs)?

**Step 4: Test code_structure**

```bash
echo '{"jsonrpc":"2.0","method":"tools/call","params":{"name":"code_structure","arguments":{"project":"/home/mk/projects/Demarch/core/intermute","language":"go"}},"id":3}' | \
  PYTHONPATH=python CLAUDE_PLUGIN_ROOT=. ./bin/intermap-mcp
```

Document: Correct function/class extraction? Missing symbols? Go vs Python accuracy?

**Step 5: Test impact_analysis**

```bash
echo '{"jsonrpc":"2.0","method":"tools/call","params":{"name":"impact_analysis","arguments":{"project":"/home/mk/projects/Demarch/core/intermute","target":"HandleAgentRegister","language":"go"}},"id":4}' | \
  PYTHONPATH=python CLAUDE_PLUGIN_ROOT=. ./bin/intermap-mcp
```

Document: Correct caller chains? Depth accuracy? False positives?

**Step 6: Test change_impact**

```bash
echo '{"jsonrpc":"2.0","method":"tools/call","params":{"name":"change_impact","arguments":{"project":"/home/mk/projects/Demarch/core/intermute","use_git":true}},"id":5}' | \
  PYTHONPATH=python CLAUDE_PLUGIN_ROOT=. ./bin/intermap-mcp
```

Document: Correct test identification? Does it find real affected tests?

**Step 7: Test agent_map (with intermute running)**

```bash
echo '{"jsonrpc":"2.0","method":"tools/call","params":{"name":"agent_map","arguments":{"root":"/home/mk/projects/Demarch"}},"id":6}' | \
  INTERMUTE_URL=http://127.0.0.1:7338 PYTHONPATH=python CLAUDE_PLUGIN_ROOT=. ./bin/intermap-mcp
```

Document: Graceful degradation when intermute is down? Correct overlay when running?

**Step 8: Write audit report**

Create `docs/audit/2026-02-23-intermap-tool-audit.md` with findings, bug list, and priority recommendations for each tool.

**Step 9: Commit**

```bash
git add docs/audit/
git commit -m "docs: intermap MCP tool audit report"
```

---

## Task 3: Extract Python modules from vendor (F3 — iv-vwj3)

**Files:**
- Remove: `python/intermap/vendor/` (entire directory)
- Modify: `python/intermap/code_structure.py` (update imports)
- Modify: `python/intermap/change_impact.py` (update imports)
- Create: `python/intermap/workspace.py` (from vendor)
- Create: `python/intermap/ignore.py` (from vendor/tldrsignore.py)

**Step 1: Copy vendored files to proper locations**

Move `vendor/workspace.py` → `python/intermap/workspace.py`
Move `vendor/tldrsignore.py` → `python/intermap/ignore.py`
Move `vendor/dirty_flag.py` → `python/intermap/dirty_flag.py`

Review each file and update any internal `from .vendor.` imports to direct `from .` imports.

**Step 2: Update all import references**

Search all Python files for `from .vendor` or `from intermap.vendor` and replace with direct imports:
- `from .vendor.workspace import ...` → `from .workspace import ...`
- `from .vendor.tldrsignore import ...` → `from .ignore import ...`
- `from .vendor.dirty_flag import ...` → `from .dirty_flag import ...`

**Step 3: Remove vendor directory**

```bash
rm -rf python/intermap/vendor/
```

**Step 4: Run Python tests**

Run: `PYTHONPATH=python python3 -m pytest python/tests/ -v`
Expected: All tests pass with new import paths

**Step 5: Verify MCP tools still work**

Run the same MCP tool tests from Task 2 Steps 2-6 against the extraction — output must be identical.

**Step 6: Commit**

```bash
git add python/intermap/ && git rm -r python/intermap/vendor/
git commit -m "refactor: extract vendored Python modules to proper intermap imports"
```

---

## Task 4: Remove moved tools from tldr-swinton (F4 — iv-mif9)

**Files:**
- Modify: `../tldr-swinton/` — MCP server source, plugin.json, docs

**Step 1: Identify tools to remove**

Tools that duplicate intermap: `structure` (→ code_structure), `impact` (→ impact_analysis), `change_impact` (→ change_impact).

**IMPORTANT:** Do NOT remove tools yet — first verify that the intermap versions produce equivalent or better output. Compare the responses from Task 2 audit against running the same queries through tldr-swinton.

**Step 2: Add deprecation warnings**

In tldr-swinton's MCP tool handlers for `structure`, `impact`, and `change_impact`, add a response field:
```json
{"deprecated": true, "use_instead": "intermap:code_structure"}
```

This is a non-breaking change that signals migration without removing functionality.

**Step 3: Update tldr-swinton documentation**

Update tldr-swinton README.md and CLAUDE.md to note the deprecation and point to intermap for project-level analysis.

**Step 4: Bump tldr-swinton version**

Use `scripts/bump-version.sh` or manual version bump in plugin.json.

**Step 5: Commit in tldr-swinton repo**

```bash
cd ../tldr-swinton
git add -A && git commit -m "deprecate: mark structure/impact/change_impact as deprecated (use intermap)"
```

---

## Task 5: Close already-done beads (F2)

**Step 1: Verify iv-728k (Go MCP scaffold)**

Confirm: Go binary builds (`go build ./...`), MCP server responds to `tools/list`, all 6 tools registered.

**Step 2: Verify iv-h3jl (Project registry + path resolver)**

Confirm: `project_registry` scans workspace correctly, `resolve_project` maps paths to projects.

**Step 3: Close beads**

```bash
bd close iv-728k --reason="Verified: Go MCP server builds, serves 6 tools via stdio transport"
bd close iv-h3jl --reason="Verified: project_registry scans monorepo, resolve_project maps paths correctly"
```

**Step 4: Close extraction beads when done**

```bash
bd close iv-vwj3 --reason="Python modules extracted from vendor/ to direct imports"
bd close iv-mif9 --reason="Deprecated structure/impact/change_impact in tldr-swinton, pointing to intermap"
```

---

## Task 6: Write vision and roadmap docs (F5 — iv-3kz0v)

**Files:**
- Modify: `docs/intermap-vision.md` (replace stub)
- Modify: `docs/intermap-roadmap.md` (replace stub)
- Create: `docs/roadmap.json`

**Step 1: Write vision doc**

Replace the stub `docs/intermap-vision.md` with real content following the convention (see interlearn-vision.md for format):
- Version/date header
- Core Idea: spatial awareness layer for multi-agent development
- Why This Exists: agents need structural understanding beyond file contents
- Current State: 6 MCP tools, Go+Python, project-level analysis
- Direction: cross-project deps, pattern detection, live awareness
- Design Principles: stateless (cache-only), Go host + Python engine, subprocess isolation, graceful degradation

**Step 2: Write roadmap doc**

Replace the stub `docs/intermap-roadmap.md` with now/next/later format:
- Now: audit fixes, extraction cleanup
- Next: cross-project deps (F6), pattern detection (F7)
- Later: live awareness (F8), deeper intermute integration, multi-language expansion

**Step 3: Create roadmap.json**

```json
{
  "module_summary": "Intermap provides project-level code mapping via MCP tools: registry, call graphs, impact analysis, architecture detection, and agent overlay.",
  "roadmap": {
    "now": [
      {"id": "IMAP-N1", "title": "Complete tldr-swinton extraction and fix test paths.", "priority": "P1"},
      {"id": "IMAP-N2", "title": "Audit all 6 tools for accuracy, performance, and integration gaps.", "priority": "P1"}
    ],
    "next": [
      {"id": "IMAP-N3", "title": "Cross-project dependency graph MCP tool.", "priority": "P2"},
      {"id": "IMAP-N4", "title": "Architecture pattern detection MCP tool.", "priority": "P2"}
    ],
    "later": [
      {"id": "IMAP-L1", "title": "Live change awareness via git-diff with structural annotation.", "priority": "P2"},
      {"id": "IMAP-L2", "title": "Deeper intermute integration (agent activity heatmaps).", "priority": "P3"}
    ]
  }
}
```

**Step 4: Close bead and commit**

```bash
bd close iv-3kz0v --reason="Vision, roadmap, and roadmap.json written"
git add docs/ && git commit -m "docs: write real intermap vision, roadmap, and roadmap.json"
```

---

## Task 7: Cross-project dependency graph MCP tool (F6 — iv-80s4e)

**Files:**
- Create: `python/intermap/cross_project.py`
- Create: `python/tests/test_cross_project.py`
- Modify: `python/intermap/analyze.py` (add dispatch route)
- Modify: `internal/tools/tools.go` (register new MCP tool)

**Step 1: Write failing tests for Python module**

```python
# python/tests/test_cross_project.py
import os
import pytest
from intermap.cross_project import scan_cross_project_deps

DEMARCH_ROOT = os.environ.get("DEMARCH_ROOT", "/home/mk/projects/Demarch")

def test_go_module_deps():
    """intercore depends on modernc.org/sqlite; intermap depends on mcp-go."""
    result = scan_cross_project_deps(DEMARCH_ROOT)
    projects = {p["project"]: p for p in result["projects"]}
    assert "intermap" in projects
    # intermap has no internal project deps (only external)

def test_plugin_deps():
    """interlock references intermute; interject references intersearch."""
    result = scan_cross_project_deps(DEMARCH_ROOT)
    projects = {p["project"]: p for p in result["projects"]}
    if "interlock" in projects:
        dep_names = [d["project"] for d in projects["interlock"]["depends_on"]]
        assert "intermute" in dep_names

def test_output_structure():
    result = scan_cross_project_deps(DEMARCH_ROOT)
    assert "projects" in result
    assert "total_projects" in result
    for p in result["projects"]:
        assert "project" in p
        assert "depends_on" in p
        for dep in p["depends_on"]:
            assert "project" in dep
            assert "type" in dep  # "go_module", "python_path", "plugin_ref"
            assert "via" in dep   # the specific import/reference
```

**Step 2: Run tests to verify they fail**

Run: `PYTHONPATH=python python3 -m pytest python/tests/test_cross_project.py -v`
Expected: ImportError (module doesn't exist yet)

**Step 3: Implement cross_project.py**

```python
# python/intermap/cross_project.py
"""Cross-project dependency detection for monorepo structures."""

import os
import re
import json
from pathlib import Path


def scan_cross_project_deps(root: str) -> dict:
    """Scan a monorepo root and detect cross-project dependencies.

    Detects:
    - Go module dependencies (go.mod replace directives + import paths)
    - Python path dependencies (pyproject.toml path deps, relative imports)
    - Plugin dependencies (MCP server references, skill invocations in plugin.json)

    Returns:
        {
            "root": str,
            "projects": [{
                "project": str,
                "path": str,
                "depends_on": [{"project": str, "type": str, "via": str}]
            }],
            "total_projects": int,
            "total_edges": int
        }
    """
    projects = _discover_projects(root)
    project_lookup = {p["name"]: p["path"] for p in projects}

    results = []
    total_edges = 0
    for proj in projects:
        deps = []
        deps.extend(_scan_go_deps(proj["path"], project_lookup))
        deps.extend(_scan_python_deps(proj["path"], project_lookup))
        deps.extend(_scan_plugin_deps(proj["path"], project_lookup))
        # Deduplicate
        seen = set()
        unique_deps = []
        for d in deps:
            key = (d["project"], d["type"])
            if key not in seen:
                seen.add(key)
                unique_deps.append(d)
        total_edges += len(unique_deps)
        results.append({
            "project": proj["name"],
            "path": proj["path"],
            "depends_on": unique_deps,
        })

    return {
        "root": root,
        "projects": results,
        "total_projects": len(results),
        "total_edges": total_edges,
    }


def _discover_projects(root: str) -> list[dict]:
    """Find projects by walking known monorepo dirs for .git markers."""
    projects = []
    for group_dir in ["interverse", "core", "os", "sdk", "apps"]:
        group_path = os.path.join(root, group_dir)
        if not os.path.isdir(group_path):
            continue
        for name in sorted(os.listdir(group_path)):
            proj_path = os.path.join(group_path, name)
            if os.path.isdir(proj_path):
                projects.append({"name": name, "path": proj_path, "group": group_dir})
    return projects


def _scan_go_deps(project_path: str, project_lookup: dict) -> list[dict]:
    """Detect Go replace directives pointing to sibling projects."""
    gomod = os.path.join(project_path, "go.mod")
    if not os.path.isfile(gomod):
        return []
    deps = []
    with open(gomod) as f:
        content = f.read()
    # Match replace directives: replace github.com/mistakeknot/foo => ../bar
    for match in re.finditer(r'replace\s+\S+\s+=>\s+(\.\./\S+)', content):
        rel = match.group(1)
        abs_path = os.path.normpath(os.path.join(project_path, rel))
        target_name = os.path.basename(abs_path)
        if target_name in project_lookup:
            deps.append({"project": target_name, "type": "go_module", "via": f"replace => {rel}"})
    return deps


def _scan_python_deps(project_path: str, project_lookup: dict) -> list[dict]:
    """Detect Python path dependencies in pyproject.toml."""
    pyproject = os.path.join(project_path, "pyproject.toml")
    if not os.path.isfile(pyproject):
        return []
    deps = []
    with open(pyproject) as f:
        content = f.read()
    # Match path dependencies: name = {path = "../sibling"}
    for match in re.finditer(r'(\w+)\s*=\s*\{[^}]*path\s*=\s*"([^"]+)"', content):
        name, rel = match.group(1), match.group(2)
        abs_path = os.path.normpath(os.path.join(project_path, rel))
        target_name = os.path.basename(abs_path)
        if target_name in project_lookup:
            deps.append({"project": target_name, "type": "python_path", "via": f"{name} path={rel}"})
    return deps


def _scan_plugin_deps(project_path: str, project_lookup: dict) -> list[dict]:
    """Detect plugin references via MCP server env vars and skill invocations."""
    deps = []
    # Check plugin.json for INTERMUTE_URL or other service references
    for pjson_path in [
        os.path.join(project_path, "plugin.json"),
        os.path.join(project_path, ".claude-plugin", "plugin.json"),
    ]:
        if not os.path.isfile(pjson_path):
            continue
        with open(pjson_path) as f:
            try:
                manifest = json.load(f)
            except json.JSONDecodeError:
                continue
        # Check MCP server env vars for service URLs
        for srv in (manifest.get("mcpServers") or {}).values():
            for key, val in (srv.get("env") or {}).items():
                if "INTERMUTE" in key.upper() and "intermute" in project_lookup:
                    deps.append({"project": "intermute", "type": "plugin_ref", "via": f"env.{key}"})
                # Generic: look for project names in env values
                if isinstance(val, str):
                    for proj_name in project_lookup:
                        if proj_name in val.lower() and proj_name != os.path.basename(project_path):
                            deps.append({"project": proj_name, "type": "plugin_ref", "via": f"env.{key}"})
    return deps
```

**Step 4: Add dispatch route**

Add to `python/intermap/analyze.py` dispatch function:
```python
elif command == "cross_project_deps":
    from .cross_project import scan_cross_project_deps
    return scan_cross_project_deps(project, **args)
```

**Step 5: Register Go MCP tool**

Add to `internal/tools/tools.go` in `RegisterAll()`:

```go
server.AddTool(mcp.NewTool("cross_project_deps",
    mcp.WithDescription("Map cross-project dependencies in a monorepo — Go module deps, Python path deps, plugin references"),
    mcp.WithString("root", mcp.Description("Monorepo root directory"), mcp.Required()),
), func(ctx context.Context, req mcp.CallToolRequest) (*mcp.CallToolResult, error) {
    root := stringOr(req.Params.Arguments, "root", "")
    if root == "" {
        return mcp.NewToolResultError("root is required"), nil
    }
    result, err := bridge.Run(ctx, "cross_project_deps", root, map[string]any{})
    if err != nil {
        return mcp.NewToolResultError(err.Error()), nil
    }
    return mcp.NewToolResultText(result), nil
})
```

**Step 6: Run tests**

Run: `cd interverse/intermap && go build ./... && PYTHONPATH=python python3 -m pytest python/tests/test_cross_project.py -v`
Expected: All tests pass

**Step 7: Commit**

```bash
git add python/intermap/cross_project.py python/tests/test_cross_project.py internal/tools/tools.go python/intermap/analyze.py
git commit -m "feat: add cross_project_deps MCP tool for monorepo dependency mapping"
```

---

## Task 8: Architecture pattern detection MCP tool (F7 — iv-dta9w)

**Files:**
- Create: `python/intermap/patterns.py`
- Create: `python/tests/test_patterns.py`
- Modify: `python/intermap/analyze.py` (add dispatch route)
- Modify: `internal/tools/tools.go` (register new MCP tool)

**Step 1: Write failing tests**

```python
# python/tests/test_patterns.py
import os
import pytest
from intermap.patterns import detect_patterns

DEMARCH_ROOT = os.environ.get("DEMARCH_ROOT", "/home/mk/projects/Demarch")

def test_go_handler_chain():
    """intermute has HTTP handler chains (router → handler functions)."""
    result = detect_patterns(os.path.join(DEMARCH_ROOT, "core/intermute"), language="go")
    types = {p["type"] for p in result["patterns"]}
    assert "handler_chain" in types or "http_handlers" in types

def test_python_mcp_registration():
    """interject has FastMCP tool registrations."""
    result = detect_patterns(os.path.join(DEMARCH_ROOT, "interverse/interject"), language="python")
    types = {p["type"] for p in result["patterns"]}
    assert "mcp_tools" in types or "fastmcp_server" in types

def test_output_structure():
    result = detect_patterns(os.path.join(DEMARCH_ROOT, "core/intermute"), language="go")
    assert "patterns" in result
    assert "project" in result
    for p in result["patterns"]:
        assert "type" in p
        assert "location" in p
        assert "confidence" in p  # 0.0-1.0
        assert "description" in p
```

**Step 2: Run tests to verify they fail**

Run: `PYTHONPATH=python python3 -m pytest python/tests/test_patterns.py -v`
Expected: ImportError

**Step 3: Implement patterns.py**

```python
# python/intermap/patterns.py
"""Architecture pattern detection for codebases."""

import os
import re
from pathlib import Path


def detect_patterns(project_path: str, language: str = "auto") -> dict:
    """Detect architectural patterns in a project.

    Pattern types:
    - http_handlers: HTTP route registrations and handler functions
    - mcp_tools: MCP tool registrations (Go mcp-go or Python FastMCP)
    - middleware_stack: Middleware chain patterns
    - interface_impl: Interface definitions with implementations
    - cli_commands: CLI command group patterns (cobra, click)
    - plugin_skills: Claude Code skill directory patterns
    - test_suite: Test organization patterns

    Returns:
        {
            "project": str,
            "language": str,
            "patterns": [{"type": str, "location": str, "confidence": float, "description": str}],
            "total_patterns": int
        }
    """
    if language == "auto":
        language = _detect_language(project_path)

    patterns = []
    if language == "go":
        patterns.extend(_detect_go_patterns(project_path))
    elif language == "python":
        patterns.extend(_detect_python_patterns(project_path))
    # Cross-language patterns
    patterns.extend(_detect_plugin_patterns(project_path))

    return {
        "project": project_path,
        "language": language,
        "patterns": patterns,
        "total_patterns": len(patterns),
    }


def _detect_language(project_path: str) -> str:
    if os.path.isfile(os.path.join(project_path, "go.mod")):
        return "go"
    if os.path.isfile(os.path.join(project_path, "pyproject.toml")):
        return "python"
    if os.path.isfile(os.path.join(project_path, "package.json")):
        return "typescript"
    return "unknown"


def _detect_go_patterns(project_path: str) -> list[dict]:
    patterns = []
    for root, dirs, files in os.walk(project_path):
        dirs[:] = [d for d in dirs if d not in {".git", "vendor", "node_modules"}]
        for fname in files:
            if not fname.endswith(".go"):
                continue
            fpath = os.path.join(root, fname)
            rel = os.path.relpath(fpath, project_path)
            try:
                content = Path(fpath).read_text(errors="replace")
            except OSError:
                continue

            # HTTP handler registrations
            handlers = re.findall(r'(?:HandleFunc|Handle|Get|Post|Put|Delete)\s*\(\s*"([^"]+)"', content)
            if len(handlers) >= 2:
                patterns.append({
                    "type": "http_handlers",
                    "location": rel,
                    "confidence": min(0.9, 0.5 + len(handlers) * 0.1),
                    "description": f"{len(handlers)} HTTP routes registered",
                })

            # MCP tool registrations (mcp-go)
            tools = re.findall(r'mcp\.NewTool\s*\(\s*"([^"]+)"', content)
            if tools:
                patterns.append({
                    "type": "mcp_tools",
                    "location": rel,
                    "confidence": 0.95,
                    "description": f"{len(tools)} MCP tools: {', '.join(tools[:5])}",
                })

            # Interface definitions
            interfaces = re.findall(r'type\s+(\w+)\s+interface\s*\{', content)
            if interfaces:
                patterns.append({
                    "type": "interface_impl",
                    "location": rel,
                    "confidence": 0.85,
                    "description": f"Interfaces: {', '.join(interfaces[:5])}",
                })

            # Middleware patterns
            if re.search(r'func\s+\w+Middleware|\.Use\(|next\.ServeHTTP', content):
                patterns.append({
                    "type": "middleware_stack",
                    "location": rel,
                    "confidence": 0.8,
                    "description": "HTTP middleware chain detected",
                })

            # CLI command patterns (cobra)
            cobra_cmds = re.findall(r'&cobra\.Command\s*\{[^}]*Use:\s*"([^"]+)"', content, re.DOTALL)
            if cobra_cmds:
                patterns.append({
                    "type": "cli_commands",
                    "location": rel,
                    "confidence": 0.9,
                    "description": f"Cobra commands: {', '.join(cobra_cmds[:5])}",
                })
    return patterns


def _detect_python_patterns(project_path: str) -> list[dict]:
    patterns = []
    for root, dirs, files in os.walk(project_path):
        dirs[:] = [d for d in dirs if d not in {".git", "__pycache__", "venv", ".venv", "node_modules"}]
        for fname in files:
            if not fname.endswith(".py"):
                continue
            fpath = os.path.join(root, fname)
            rel = os.path.relpath(fpath, project_path)
            try:
                content = Path(fpath).read_text(errors="replace")
            except OSError:
                continue

            # FastMCP tool registrations
            tools = re.findall(r'@\w+\.tool\s*\(\s*\)\s*\n\s*(?:async\s+)?def\s+(\w+)', content)
            if tools:
                patterns.append({
                    "type": "mcp_tools",
                    "location": rel,
                    "confidence": 0.95,
                    "description": f"{len(tools)} FastMCP tools: {', '.join(tools[:5])}",
                })

            # Click CLI commands
            click_cmds = re.findall(r'@\w+\.command\s*\([^)]*\)\s*\n\s*def\s+(\w+)', content)
            if click_cmds:
                patterns.append({
                    "type": "cli_commands",
                    "location": rel,
                    "confidence": 0.9,
                    "description": f"Click commands: {', '.join(click_cmds[:5])}",
                })
    return patterns


def _detect_plugin_patterns(project_path: str) -> list[dict]:
    """Detect Claude Code plugin structure patterns."""
    patterns = []
    # Skill directories
    skills_dir = os.path.join(project_path, "skills")
    if os.path.isdir(skills_dir):
        skill_dirs = [d for d in os.listdir(skills_dir) if os.path.isdir(os.path.join(skills_dir, d))]
        skill_files = [f for f in os.listdir(skills_dir) if f.endswith(".md")]
        total = len(skill_dirs) + len(skill_files)
        if total > 0:
            patterns.append({
                "type": "plugin_skills",
                "location": "skills/",
                "confidence": 0.95,
                "description": f"{total} skills detected",
            })

    # Hook registrations
    hooks_json = os.path.join(project_path, "hooks", "hooks.json")
    if os.path.isfile(hooks_json):
        patterns.append({
            "type": "plugin_hooks",
            "location": "hooks/hooks.json",
            "confidence": 0.95,
            "description": "Hook registrations detected",
        })

    return patterns
```

**Step 4: Add dispatch route and register MCP tool**

Add to `python/intermap/analyze.py`:
```python
elif command == "detect_patterns":
    from .patterns import detect_patterns
    return detect_patterns(project, **args)
```

Add to `internal/tools/tools.go` in `RegisterAll()`:
```go
server.AddTool(mcp.NewTool("detect_patterns",
    mcp.WithDescription("Detect architectural patterns: HTTP handlers, MCP tools, middleware, interfaces, CLI commands, plugin structures"),
    mcp.WithString("project", mcp.Description("Project root directory"), mcp.Required()),
    mcp.WithString("language", mcp.Description("Language (go, python, auto)"), mcp.DefaultString("auto")),
), func(ctx context.Context, req mcp.CallToolRequest) (*mcp.CallToolResult, error) {
    project := stringOr(req.Params.Arguments, "project", "")
    if project == "" {
        return mcp.NewToolResultError("project is required"), nil
    }
    lang := stringOr(req.Params.Arguments, "language", "auto")
    result, err := bridge.Run(ctx, "detect_patterns", project, map[string]any{"language": lang})
    if err != nil {
        return mcp.NewToolResultError(err.Error()), nil
    }
    return mcp.NewToolResultText(result), nil
})
```

**Step 5: Run tests**

Run: `cd interverse/intermap && go build ./... && PYTHONPATH=python python3 -m pytest python/tests/test_patterns.py -v`
Expected: All tests pass

**Step 6: Commit**

```bash
git add python/intermap/patterns.py python/tests/test_patterns.py internal/tools/tools.go python/intermap/analyze.py
git commit -m "feat: add detect_patterns MCP tool for architecture pattern detection"
```

---

## Task 9: Live change awareness MCP tool (F8 — iv-54iqe)

**Files:**
- Create: `python/intermap/live_changes.py`
- Create: `python/tests/test_live_changes.py`
- Modify: `python/intermap/analyze.py` (add dispatch route)
- Modify: `internal/tools/tools.go` (register new MCP tool)

**Step 1: Write failing tests**

```python
# python/tests/test_live_changes.py
import os
import pytest
from intermap.live_changes import get_live_changes

DEMARCH_ROOT = os.environ.get("DEMARCH_ROOT", "/home/mk/projects/Demarch")

def test_output_structure():
    """Output should have changes list with structural annotations."""
    result = get_live_changes(
        os.path.join(DEMARCH_ROOT, "interverse/intermap"),
        baseline="HEAD",
    )
    assert "project" in result
    assert "baseline" in result
    assert "changes" in result
    assert isinstance(result["changes"], list)
    assert "total_files" in result

def test_change_has_symbols():
    """If any files changed, changes should include symbol info."""
    result = get_live_changes(
        os.path.join(DEMARCH_ROOT, "interverse/intermap"),
        baseline="HEAD~3",  # Look back a few commits
    )
    for change in result["changes"]:
        assert "file" in change
        assert "status" in change  # modified, added, deleted
        assert "symbols_affected" in change
```

**Step 2: Run tests to verify they fail**

Run: `PYTHONPATH=python python3 -m pytest python/tests/test_live_changes.py -v`
Expected: ImportError

**Step 3: Implement live_changes.py**

```python
# python/intermap/live_changes.py
"""Live change awareness — git-diff based change detection with structural annotation."""

import os
import re
import subprocess
from .extractors import DefaultExtractor


def get_live_changes(project_path: str, baseline: str = "HEAD", language: str = "auto") -> dict:
    """Detect changes since baseline and annotate with affected symbols.

    Uses git diff to find changed files, then extracts which functions/classes
    were affected by the changes (not just line numbers).

    Args:
        project_path: Project root (must be in a git repo)
        baseline: Git ref to diff against (HEAD, branch name, commit SHA)
        language: Language hint for extraction (auto-detects if "auto")

    Returns:
        {
            "project": str,
            "baseline": str,
            "changes": [{
                "file": str,
                "status": str,  # "modified", "added", "deleted", "renamed"
                "hunks": [{"old_start": int, "new_start": int, "new_count": int}],
                "symbols_affected": [{"name": str, "type": str, "line": int}]
            }],
            "total_files": int,
            "total_symbols_affected": int
        }
    """
    changes = _get_git_diff(project_path, baseline)
    extractor = DefaultExtractor()
    total_symbols = 0

    for change in changes:
        fpath = os.path.join(project_path, change["file"])
        symbols = []

        if change["status"] != "deleted" and os.path.isfile(fpath):
            try:
                extraction = extractor.extract(fpath)
                changed_lines = set()
                for hunk in change["hunks"]:
                    start = hunk["new_start"]
                    count = hunk["new_count"]
                    changed_lines.update(range(start, start + count))

                # Find functions whose line range overlaps with changed lines
                for func in extraction.functions:
                    if func.line_number in changed_lines or _symbol_overlaps(func.line_number, changed_lines):
                        symbols.append({"name": func.name, "type": "function", "line": func.line_number})

                for cls in extraction.classes:
                    if cls.line_number in changed_lines or _symbol_overlaps(cls.line_number, changed_lines):
                        symbols.append({"name": cls.name, "type": "class", "line": cls.line_number})
                    for method in cls.methods:
                        if method.line_number in changed_lines or _symbol_overlaps(method.line_number, changed_lines):
                            symbols.append({"name": f"{cls.name}.{method.name}", "type": "method", "line": method.line_number})
            except Exception:
                pass  # Extraction failure is non-fatal

        change["symbols_affected"] = symbols
        total_symbols += len(symbols)

    return {
        "project": project_path,
        "baseline": baseline,
        "changes": changes,
        "total_files": len(changes),
        "total_symbols_affected": total_symbols,
    }


def _symbol_overlaps(symbol_line: int, changed_lines: set, window: int = 20) -> bool:
    """Check if a symbol's approximate range overlaps with changed lines."""
    return any(abs(symbol_line - line) < window for line in changed_lines)


def _get_git_diff(project_path: str, baseline: str) -> list[dict]:
    """Run git diff and parse into structured changes."""
    try:
        # Get file list with status
        result = subprocess.run(
            ["git", "diff", "--name-status", baseline],
            capture_output=True, text=True, cwd=project_path, timeout=10,
        )
        if result.returncode != 0:
            return []

        files = {}
        for line in result.stdout.strip().split("\n"):
            if not line:
                continue
            parts = line.split("\t")
            status_code = parts[0][0]  # M, A, D, R
            fname = parts[-1]
            status = {"M": "modified", "A": "added", "D": "deleted", "R": "renamed"}.get(status_code, "modified")
            files[fname] = {"file": fname, "status": status, "hunks": []}

        # Get hunk details
        result = subprocess.run(
            ["git", "diff", "--unified=0", baseline],
            capture_output=True, text=True, cwd=project_path, timeout=10,
        )
        current_file = None
        for line in result.stdout.split("\n"):
            if line.startswith("+++ b/"):
                current_file = line[6:]
            elif line.startswith("@@ ") and current_file and current_file in files:
                match = re.search(r'\+(\d+)(?:,(\d+))?', line)
                if match:
                    start = int(match.group(1))
                    count = int(match.group(2) or 1)
                    files[current_file]["hunks"].append({
                        "old_start": start,
                        "new_start": start,
                        "new_count": count,
                    })

        return list(files.values())
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return []
```

**Step 4: Add dispatch route and register MCP tool**

Add to `python/intermap/analyze.py`:
```python
elif command == "live_changes":
    from .live_changes import get_live_changes
    return get_live_changes(project, **args)
```

Add to `internal/tools/tools.go` in `RegisterAll()`:
```go
server.AddTool(mcp.NewTool("live_changes",
    mcp.WithDescription("Git-diff based change detection with structural annotation — shows which functions/classes were affected by recent changes"),
    mcp.WithString("project", mcp.Description("Project root directory"), mcp.Required()),
    mcp.WithString("baseline", mcp.Description("Git ref to diff against (HEAD, branch, SHA)"), mcp.DefaultString("HEAD")),
), func(ctx context.Context, req mcp.CallToolRequest) (*mcp.CallToolResult, error) {
    project := stringOr(req.Params.Arguments, "project", "")
    if project == "" {
        return mcp.NewToolResultError("project is required"), nil
    }
    baseline := stringOr(req.Params.Arguments, "baseline", "HEAD")
    result, err := bridge.Run(ctx, "live_changes", project, map[string]any{"baseline": baseline})
    if err != nil {
        return mcp.NewToolResultError(err.Error()), nil
    }
    return mcp.NewToolResultText(result), nil
})
```

**Step 5: Run all tests**

Run: `cd interverse/intermap && go build ./... && go test ./... && PYTHONPATH=python python3 -m pytest python/tests/ -v`
Expected: All tests pass

**Step 6: Commit**

```bash
git add python/intermap/live_changes.py python/tests/test_live_changes.py internal/tools/tools.go python/intermap/analyze.py
git commit -m "feat: add live_changes MCP tool for git-diff based change awareness"
```

---

## Task 10: Update plugin manifest and integration test

**Files:**
- Modify: `.claude-plugin/plugin.json` (update description, version)
- Modify: `CLAUDE.md` (update tool table)
- Modify: `README.md` (update tool list)

**Step 1: Update plugin.json**

Bump version to `0.2.0`. Update description to reflect 9 tools.

**Step 2: Update CLAUDE.md tool table**

Add the 3 new tools to the MCP Tools table:

```
| cross_project_deps | Python | Monorepo dependency graph |
| detect_patterns    | Python | Architecture pattern detection |
| live_changes       | Python | Git-diff change awareness |
```

**Step 3: Update README.md**

Add new tools to the MCP Tools list and update the description paragraph.

**Step 4: Full integration test**

Build and run all 9 tools through the MCP server to verify end-to-end:

```bash
cd interverse/intermap
go build -o bin/intermap-mcp ./cmd/intermap-mcp/
echo '{"jsonrpc":"2.0","method":"tools/list","id":1}' | PYTHONPATH=python CLAUDE_PLUGIN_ROOT=. ./bin/intermap-mcp
```

Verify 9 tools listed. Then run each new tool:

```bash
# cross_project_deps
echo '{"jsonrpc":"2.0","method":"tools/call","params":{"name":"cross_project_deps","arguments":{"root":"/home/mk/projects/Demarch"}},"id":2}' | PYTHONPATH=python CLAUDE_PLUGIN_ROOT=. ./bin/intermap-mcp

# detect_patterns
echo '{"jsonrpc":"2.0","method":"tools/call","params":{"name":"detect_patterns","arguments":{"project":"/home/mk/projects/Demarch/core/intermute"}},"id":3}' | PYTHONPATH=python CLAUDE_PLUGIN_ROOT=. ./bin/intermap-mcp

# live_changes
echo '{"jsonrpc":"2.0","method":"tools/call","params":{"name":"live_changes","arguments":{"project":"/home/mk/projects/Demarch/interverse/intermap","baseline":"HEAD~5"}},"id":4}' | PYTHONPATH=python CLAUDE_PLUGIN_ROOT=. ./bin/intermap-mcp
```

**Step 5: Commit and close remaining beads**

```bash
git add .claude-plugin/plugin.json CLAUDE.md README.md
git commit -m "feat: bump to v0.2.0 with 9 MCP tools (3 new: cross_project_deps, detect_patterns, live_changes)"

bd close iv-dl72x --reason="Audit complete, bugs fixed, report written"
bd close iv-80s4e --reason="cross_project_deps tool shipped and tested"
bd close iv-dta9w --reason="detect_patterns tool shipped and tested"
bd close iv-54iqe --reason="live_changes tool shipped and tested"
```
