# interdeep Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use clavain:executing-plans to implement this plan task-by-task.

**Goal:** Build `interdeep`, an Interverse plugin that provides content extraction (trafilatura + Playwright hybrid) and deep research orchestration, composing with interject (search), intersynth (synthesis), interknow (knowledge), and other existing plugins.

**Architecture:** Python MCP server (`uv run`) exposing 4 stateless tools (`extract_content`, `extract_batch`, `compile_report`, `research_status`). Orchestration intelligence lives in a SKILL.md prompt. Plugin follows the Interverse plugin standard — `.claude-plugin/plugin.json`, structural tests, all required docs. New search provider adapters (Tavily, Brave, PubMed, Semantic Scholar, SearXNG) are contributed to interject, not owned by interdeep.

**Tech Stack:** Python 3.12+, `mcp>=1.0`, `trafilatura`, `playwright`, `aiohttp`, `json-repair`, hatchling build system, uv package manager

**Prior Learnings:**
- `docs/solutions/patterns/critical-patterns.md` — Graceful launcher scripts for external deps (exit 0 on missing), hooks.json record format
- `docs/solutions/patterns/hybrid-cli-plugin-architecture-20260223.md` — Evaluated but NOT using hybrid pattern (interdeep's extraction has no standalone CLI value outside agent sessions)
- `docs/solutions/patterns/synthesis-subagent-context-isolation-20260216.md` — Three-tier isolation for multi-agent orchestration (agents write files → synthesis subagent deduplicates → host reads compact return)
- `docs/solutions/patterns/search-surfaces.md` — Plugin composition map for interject, intersynth, interknow, intercache, interlens

---

## Task 1: Scaffold Plugin Structure

**Files:**
- Create: `interverse/interdeep/.claude-plugin/plugin.json`
- Create: `interverse/interdeep/pyproject.toml`
- Create: `interverse/interdeep/src/interdeep/__init__.py`
- Create: `interverse/interdeep/src/interdeep/server.py`
- Create: `interverse/interdeep/scripts/launch-mcp.sh`
- Create: `interverse/interdeep/scripts/bump-version.sh`
- Create: `interverse/interdeep/.gitignore`
- Create: `interverse/interdeep/LICENSE`

**Step 1: Create directory structure**

```bash
mkdir -p interverse/interdeep/.claude-plugin
mkdir -p interverse/interdeep/src/interdeep/extraction
mkdir -p interverse/interdeep/src/interdeep/reports
mkdir -p interverse/interdeep/skills/deep-research
mkdir -p interverse/interdeep/agents
mkdir -p interverse/interdeep/commands
mkdir -p interverse/interdeep/config
mkdir -p interverse/interdeep/scripts
mkdir -p interverse/interdeep/tests/structural
```

**Step 2: Create `pyproject.toml`**

```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "interdeep"
version = "0.1.0"
requires-python = ">=3.12"
dependencies = [
    "mcp>=1.0",
    "trafilatura>=2.0",
    "aiohttp>=3.9",
    "json-repair>=0.30",
]

[project.optional-dependencies]
browser = ["playwright>=1.40"]

[project.scripts]
interdeep-mcp = "interdeep.server:cli_main"

[tool.hatch.build.targets.wheel]
packages = ["src/interdeep"]
```

Note: `playwright` is optional — extraction degrades gracefully to trafilatura-only when playwright is not installed.

**Step 3: Create `.claude-plugin/plugin.json`**

```json
{
  "name": "interdeep",
  "version": "0.1.0",
  "description": "Deep research plugin — content extraction and research orchestration via MCP tools.",
  "author": { "name": "mistakeknot" },
  "license": "MIT",
  "keywords": ["research", "extraction", "deep-research", "trafilatura"],
  "skills": [
    "./skills/deep-research"
  ],
  "commands": [
    "./commands/research.md"
  ],
  "agents": [
    "./agents/research-planner.md",
    "./agents/source-evaluator.md",
    "./agents/report-compiler.md"
  ],
  "mcpServers": {
    "interdeep": {
      "command": "${CLAUDE_PLUGIN_ROOT}/scripts/launch-mcp.sh"
    }
  }
}
```

**Step 4: Create `scripts/launch-mcp.sh`**

This follows the graceful launcher pattern from `critical-patterns.md`:

```bash
#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

if ! command -v uv &>/dev/null; then
    echo "uv not found — interdeep MCP server disabled." >&2
    exit 0
fi

if ! uv run --directory "$PROJECT_ROOT" python -c "import trafilatura" 2>/dev/null; then
    echo "trafilatura not installed — running uv sync first..." >&2
    uv sync --directory "$PROJECT_ROOT" 2>&1 >&2
fi

exec uv run --directory "$PROJECT_ROOT" interdeep-mcp "$@"
```

Make executable: `chmod +x interverse/interdeep/scripts/launch-mcp.sh`

**Step 5: Create `scripts/bump-version.sh`**

```bash
#!/usr/bin/env bash
set -euo pipefail
if command -v ic &>/dev/null; then
    exec ic publish "${1:---patch}"
else
    echo "ic not available — use interbump.sh" >&2
    exit 1
fi
```

Make executable: `chmod +x interverse/interdeep/scripts/bump-version.sh`

**Step 6: Create `src/interdeep/__init__.py`**

```python
"""interdeep — Deep research content extraction and orchestration."""
__version__ = "0.1.0"
```

**Step 7: Create minimal `server.py` (stub — filled in Task 3)**

```python
"""interdeep MCP server — content extraction and research orchestration tools."""

import asyncio
import json
import logging

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import TextContent, Tool

logger = logging.getLogger("interdeep")
app = Server("interdeep")


def _ok(data: dict) -> list[TextContent]:
    return [TextContent(type="text", text=json.dumps(data, indent=2))]


def _err(msg: str) -> list[TextContent]:
    return [TextContent(type="text", text=json.dumps({"error": msg}))]


@app.list_tools()
async def list_tools() -> list[Tool]:
    return []


@app.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    return _err(f"Unknown tool: {name}")


async def main():
    async with stdio_server() as (read_stream, write_stream):
        await app.run(read_stream, write_stream, app.create_initialization_options())


def cli_main():
    asyncio.run(main())


if __name__ == "__main__":
    cli_main()
```

**Step 8: Create `.gitignore` and `LICENSE`**

`.gitignore`:
```
__pycache__/
*.pyc
.venv/
.pytest_cache/
.claude/
.beads/
*.log
*.egg-info/
dist/
build/
.ruff_cache/
```

`LICENSE`: Standard MIT, copyright "MK".

**Step 9: Initialize git repo and verify**

```bash
cd interverse/interdeep && git init && git add -A && git commit -m "feat: scaffold interdeep plugin"
```

**Step 10: Verify MCP server starts**

```bash
cd interverse/interdeep && uv sync && uv run interdeep-mcp &
PID=$!; sleep 2; kill $PID 2>/dev/null
echo "MCP server starts cleanly"
```

Expected: Server starts and waits for stdio input. No errors.

---

## Task 2: Content Extraction Layer (trafilatura)

**Files:**
- Create: `interverse/interdeep/src/interdeep/extraction/__init__.py`
- Create: `interverse/interdeep/src/interdeep/extraction/trafilatura_ext.py`
- Create: `interverse/interdeep/src/interdeep/extraction/models.py`
- Create: `interverse/interdeep/tests/test_extraction.py`

**Step 1: Create data models**

`src/interdeep/extraction/models.py`:

```python
"""Data models for extracted content."""

from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class ExtractionResult:
    url: str
    content: str  # clean markdown/text
    title: str = ""
    method: str = ""  # "trafilatura" | "playwright" | "failed"
    content_length: int = 0
    extracted_at: datetime = field(default_factory=datetime.utcnow)
    metadata: dict = field(default_factory=dict)

    def __post_init__(self):
        self.content_length = len(self.content)
```

**Step 2: Write failing test for trafilatura extraction**

`tests/test_extraction.py`:

```python
"""Tests for content extraction layer."""

import pytest
from interdeep.extraction.trafilatura_ext import extract_with_trafilatura
from interdeep.extraction.models import ExtractionResult


def test_extract_with_trafilatura_returns_result():
    """Extraction should return an ExtractionResult even on failure."""
    result = extract_with_trafilatura("https://example.com")
    assert isinstance(result, ExtractionResult)
    assert result.url == "https://example.com"
    assert result.method == "trafilatura"


def test_extract_with_trafilatura_empty_url():
    """Empty URL should return a failed result."""
    result = extract_with_trafilatura("")
    assert result.method == "failed"
    assert result.content == ""


def test_extract_from_html():
    """Direct HTML extraction should work without network."""
    from interdeep.extraction.trafilatura_ext import extract_from_html

    html = """
    <html><body>
    <article><h1>Test Title</h1><p>This is the main content of the article.</p></article>
    <footer>Copyright 2026</footer>
    </body></html>
    """
    result = extract_from_html(html, url="https://example.com/test")
    assert result.content_length > 0
    assert "main content" in result.content
    assert result.method == "trafilatura"
```

**Step 3: Run tests to verify they fail**

```bash
cd interverse/interdeep && uv run pytest tests/test_extraction.py -v
```

Expected: FAIL — `ModuleNotFoundError: No module named 'interdeep.extraction.trafilatura_ext'`

**Step 4: Implement trafilatura wrapper**

`src/interdeep/extraction/__init__.py`:

```python
"""Content extraction layer — trafilatura fast path + optional Playwright fallback."""
```

`src/interdeep/extraction/trafilatura_ext.py`:

```python
"""trafilatura-based content extraction — fast path for ~80% of web pages."""

import logging
from .models import ExtractionResult

logger = logging.getLogger("interdeep.extraction")


def extract_with_trafilatura(url: str, timeout: int = 10) -> ExtractionResult:
    """Fetch and extract main content from a URL using trafilatura."""
    if not url:
        return ExtractionResult(url="", content="", method="failed")
    try:
        import trafilatura

        downloaded = trafilatura.fetch_url(url)
        if downloaded is None:
            return ExtractionResult(url=url, content="", method="failed",
                                    metadata={"error": "fetch returned None"})
        return extract_from_html(downloaded, url=url)
    except Exception as e:
        logger.warning("trafilatura extraction failed for %s: %s", url, e)
        return ExtractionResult(url=url, content="", method="failed",
                                metadata={"error": str(e)})


def extract_from_html(html: str, url: str = "") -> ExtractionResult:
    """Extract main content from raw HTML string."""
    try:
        import trafilatura

        text = trafilatura.extract(
            html,
            url=url,
            include_links=True,
            include_formatting=True,
            include_tables=True,
            favor_precision=False,
            favor_recall=True,
            output_format="txt",
        )
        if text is None:
            return ExtractionResult(url=url, content="", method="failed",
                                    metadata={"error": "extraction returned None"})
        title = trafilatura.extract_metadata(html, url)
        title_str = title.title if title and title.title else ""
        return ExtractionResult(url=url, content=text, title=title_str,
                                method="trafilatura")
    except Exception as e:
        logger.warning("HTML extraction failed: %s", e)
        return ExtractionResult(url=url, content="", method="failed",
                                metadata={"error": str(e)})
```

**Step 5: Run tests to verify they pass**

```bash
cd interverse/interdeep && uv run pytest tests/test_extraction.py -v
```

Expected: 3 PASS

**Step 6: Commit**

```bash
cd interverse/interdeep && git add -A && git commit -m "feat: trafilatura content extraction layer"
```

---

## Task 3: Content Extraction Layer (Playwright Fallback + Hybrid Router)

**Files:**
- Create: `interverse/interdeep/src/interdeep/extraction/playwright_ext.py`
- Create: `interverse/interdeep/src/interdeep/extraction/hybrid.py`
- Modify: `interverse/interdeep/tests/test_extraction.py`

**Step 1: Write failing test for hybrid extraction**

Append to `tests/test_extraction.py`:

```python
def test_hybrid_extract_uses_trafilatura_first():
    """Hybrid should try trafilatura before playwright."""
    from interdeep.extraction.hybrid import extract_hybrid

    # Use a well-formed HTML page — trafilatura should handle it
    html = "<html><body><article><p>Simple content here.</p></article></body></html>"
    result = extract_hybrid(html=html, url="https://example.com")
    assert result.method == "trafilatura"
    assert result.content_length > 0


def test_hybrid_extract_url():
    """Hybrid should accept a URL and return a result."""
    from interdeep.extraction.hybrid import extract_hybrid

    result = extract_hybrid(url="https://example.com")
    assert isinstance(result, ExtractionResult)
    assert result.url == "https://example.com"
```

**Step 2: Run tests to verify they fail**

```bash
cd interverse/interdeep && uv run pytest tests/test_extraction.py::test_hybrid_extract_uses_trafilatura_first -v
```

Expected: FAIL — `ModuleNotFoundError: No module named 'interdeep.extraction.hybrid'`

**Step 3: Implement Playwright fallback**

`src/interdeep/extraction/playwright_ext.py`:

```python
"""Playwright-based content extraction — fallback for JS-rendered pages."""

import logging
from .models import ExtractionResult

logger = logging.getLogger("interdeep.extraction")

_PLAYWRIGHT_AVAILABLE = False
try:
    import playwright  # noqa: F401
    _PLAYWRIGHT_AVAILABLE = True
except ImportError:
    pass


async def extract_with_playwright(url: str, timeout: int = 30000) -> ExtractionResult:
    """Render page with headless browser and extract content."""
    if not _PLAYWRIGHT_AVAILABLE:
        return ExtractionResult(url=url, content="", method="failed",
                                metadata={"error": "playwright not installed"})
    if not url:
        return ExtractionResult(url="", content="", method="failed")
    try:
        from playwright.async_api import async_playwright
        from .trafilatura_ext import extract_from_html

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            await page.goto(url, timeout=timeout, wait_until="networkidle")
            html = await page.content()
            await browser.close()

        result = extract_from_html(html, url=url)
        result.method = "playwright"
        result.metadata["rendered"] = True
        return result
    except Exception as e:
        logger.warning("Playwright extraction failed for %s: %s", url, e)
        return ExtractionResult(url=url, content="", method="failed",
                                metadata={"error": str(e)})


def is_available() -> bool:
    return _PLAYWRIGHT_AVAILABLE
```

**Step 4: Implement hybrid router**

`src/interdeep/extraction/hybrid.py`:

```python
"""Hybrid extraction router — trafilatura fast path, Playwright fallback."""

import asyncio
import logging
from .models import ExtractionResult
from .trafilatura_ext import extract_with_trafilatura, extract_from_html
from . import playwright_ext

logger = logging.getLogger("interdeep.extraction")

MIN_CONTENT_LENGTH = 200  # below this, try playwright fallback


def extract_hybrid(url: str = "", html: str = "", timeout: int = 10) -> ExtractionResult:
    """Extract content using trafilatura first, Playwright fallback if needed."""
    # If raw HTML provided, extract directly
    if html:
        result = extract_from_html(html, url=url)
        if result.content_length >= MIN_CONTENT_LENGTH:
            return result
    # If URL provided, try trafilatura fetch + extract
    elif url:
        result = extract_with_trafilatura(url, timeout=timeout)
        if result.content_length >= MIN_CONTENT_LENGTH:
            return result
    else:
        return ExtractionResult(url="", content="", method="failed",
                                metadata={"error": "no url or html provided"})

    # Fallback to Playwright if trafilatura didn't get enough content
    if url and playwright_ext.is_available():
        logger.info("trafilatura insufficient (%d chars), falling back to Playwright: %s",
                     result.content_length, url)
        try:
            pw_result = asyncio.run(playwright_ext.extract_with_playwright(url))
            if pw_result.content_length > result.content_length:
                return pw_result
        except Exception as e:
            logger.warning("Playwright fallback failed: %s", e)

    return result  # return whatever trafilatura got, even if short


async def extract_hybrid_async(url: str = "", html: str = "",
                                timeout: int = 10) -> ExtractionResult:
    """Async version of extract_hybrid."""
    if html:
        result = extract_from_html(html, url=url)
        if result.content_length >= MIN_CONTENT_LENGTH:
            return result
    elif url:
        result = extract_with_trafilatura(url, timeout=timeout)
        if result.content_length >= MIN_CONTENT_LENGTH:
            return result
    else:
        return ExtractionResult(url="", content="", method="failed",
                                metadata={"error": "no url or html provided"})

    if url and playwright_ext.is_available():
        logger.info("trafilatura insufficient, falling back to Playwright: %s", url)
        pw_result = await playwright_ext.extract_with_playwright(url)
        if pw_result.content_length > result.content_length:
            return pw_result

    return result


async def extract_batch_async(urls: list[str], max_concurrent: int = 5) -> list[ExtractionResult]:
    """Extract content from multiple URLs concurrently."""
    semaphore = asyncio.Semaphore(max_concurrent)

    async def _extract(url: str) -> ExtractionResult:
        async with semaphore:
            return await extract_hybrid_async(url=url)

    return await asyncio.gather(*[_extract(url) for url in urls])
```

**Step 5: Run all extraction tests**

```bash
cd interverse/interdeep && uv run pytest tests/test_extraction.py -v
```

Expected: 5 PASS

**Step 6: Commit**

```bash
cd interverse/interdeep && git add -A && git commit -m "feat: playwright fallback and hybrid extraction router"
```

---

## Task 4: MCP Server Tools

**Files:**
- Modify: `interverse/interdeep/src/interdeep/server.py`
- Create: `interverse/interdeep/src/interdeep/reports/__init__.py`
- Create: `interverse/interdeep/src/interdeep/reports/markdown.py`
- Create: `interverse/interdeep/tests/test_server.py`

**Step 1: Write failing test for MCP tools**

`tests/test_server.py`:

```python
"""Tests for MCP server tool registration."""

import pytest
import asyncio
from interdeep.server import list_tools, call_tool


@pytest.fixture
def tools():
    return asyncio.run(list_tools())


def test_tools_are_registered(tools):
    names = [t.name for t in tools]
    assert "extract_content" in names
    assert "extract_batch" in names
    assert "compile_report" in names
    assert "research_status" in names


def test_extract_content_has_schema(tools):
    tool = next(t for t in tools if t.name == "extract_content")
    assert "url" in tool.inputSchema["properties"]
    assert "url" in tool.inputSchema["required"]


def test_unknown_tool_returns_error():
    result = asyncio.run(call_tool("nonexistent", {}))
    text = result[0].text
    assert "error" in text.lower() or "unknown" in text.lower()
```

**Step 2: Run tests to verify they fail**

```bash
cd interverse/interdeep && uv run pytest tests/test_server.py -v
```

Expected: FAIL — tools list is empty

**Step 3: Implement report compiler**

`src/interdeep/reports/__init__.py`:

```python
"""Report compilation for deep research outputs."""
```

`src/interdeep/reports/markdown.py`:

```python
"""Structured markdown report compilation with citations."""

from datetime import datetime


def compile_markdown_report(
    title: str,
    findings: list[dict],
    sources: list[dict],
    query: str = "",
    metadata: dict | None = None,
) -> str:
    """Compile findings and sources into a structured markdown report."""
    meta = metadata or {}
    now = datetime.utcnow().strftime("%Y-%m-%d")

    lines = [
        "---",
        f"title: \"{title}\"",
        f"date: {now}",
        f"query: \"{query}\"",
        f"sources_count: {len(sources)}",
        f"findings_count: {len(findings)}",
    ]
    if meta:
        for k, v in meta.items():
            lines.append(f"{k}: {v}")
    lines.extend(["---", "", f"# {title}", ""])

    if query:
        lines.extend([f"> **Research query:** {query}", ""])

    # Findings sections
    for i, finding in enumerate(findings, 1):
        section_title = finding.get("title", f"Finding {i}")
        content = finding.get("content", "")
        confidence = finding.get("confidence", "")
        lines.append(f"## {section_title}")
        if confidence:
            lines.append(f"*Confidence: {confidence}*")
        lines.extend(["", content, ""])

    # Sources bibliography
    if sources:
        lines.extend(["---", "", "## Sources", ""])
        for i, source in enumerate(sources, 1):
            url = source.get("url", "")
            title = source.get("title", url)
            relevance = source.get("relevance", "")
            line = f"{i}. [{title}]({url})"
            if relevance:
                line += f" — *{relevance}*"
            lines.append(line)
        lines.append("")

    return "\n".join(lines)
```

**Step 4: Implement full MCP server with all 4 tools**

Replace `src/interdeep/server.py` with the full implementation:

```python
"""interdeep MCP server — content extraction and research orchestration tools."""

import asyncio
import json
import logging
import shutil

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import TextContent, Tool

from interdeep.extraction.hybrid import extract_hybrid_async, extract_batch_async
from interdeep.extraction.models import ExtractionResult
from interdeep.reports.markdown import compile_markdown_report

logger = logging.getLogger("interdeep")
app = Server("interdeep")


def _ok(data: dict) -> list[TextContent]:
    return [TextContent(type="text", text=json.dumps(data, indent=2))]


def _err(msg: str) -> list[TextContent]:
    return [TextContent(type="text", text=json.dumps({"error": msg}))]


def _result_to_dict(r: ExtractionResult) -> dict:
    return {
        "url": r.url,
        "title": r.title,
        "content": r.content,
        "method": r.method,
        "content_length": r.content_length,
        "metadata": r.metadata,
    }


@app.list_tools()
async def list_tools() -> list[Tool]:
    return [
        Tool(
            name="extract_content",
            description="Extract clean text/markdown from a URL. Uses trafilatura (fast) with Playwright fallback for JS-rendered pages.",
            inputSchema={
                "type": "object",
                "properties": {
                    "url": {
                        "type": "string",
                        "description": "URL to extract content from",
                    },
                },
                "required": ["url"],
            },
        ),
        Tool(
            name="extract_batch",
            description="Extract content from multiple URLs concurrently. Returns results for each URL.",
            inputSchema={
                "type": "object",
                "properties": {
                    "urls": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of URLs to extract content from",
                    },
                    "max_concurrent": {
                        "type": "integer",
                        "description": "Max concurrent extractions (default 5)",
                        "default": 5,
                    },
                },
                "required": ["urls"],
            },
        ),
        Tool(
            name="compile_report",
            description="Compile research findings and sources into a structured markdown report with citations.",
            inputSchema={
                "type": "object",
                "properties": {
                    "title": {
                        "type": "string",
                        "description": "Report title",
                    },
                    "query": {
                        "type": "string",
                        "description": "Original research query",
                    },
                    "findings": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "title": {"type": "string"},
                                "content": {"type": "string"},
                                "confidence": {"type": "string"},
                            },
                        },
                        "description": "List of findings with title, content, and optional confidence",
                    },
                    "sources": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "url": {"type": "string"},
                                "title": {"type": "string"},
                                "relevance": {"type": "string"},
                            },
                        },
                        "description": "List of sources with url, title, and optional relevance",
                    },
                },
                "required": ["title", "findings", "sources"],
            },
        ),
        Tool(
            name="research_status",
            description="Show available companion plugins and their readiness for deep research.",
            inputSchema={
                "type": "object",
                "properties": {},
            },
        ),
    ]


@app.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    try:
        if name == "extract_content":
            return await _handle_extract_content(arguments)
        elif name == "extract_batch":
            return await _handle_extract_batch(arguments)
        elif name == "compile_report":
            return await _handle_compile_report(arguments)
        elif name == "research_status":
            return await _handle_research_status(arguments)
        else:
            return _err(f"Unknown tool: {name}")
    except Exception as e:
        logger.exception("Tool %s failed", name)
        return _err(str(e))


async def _handle_extract_content(args: dict) -> list[TextContent]:
    url = args.get("url", "")
    if not url:
        return _err("url is required")
    result = await extract_hybrid_async(url=url)
    return _ok(_result_to_dict(result))


async def _handle_extract_batch(args: dict) -> list[TextContent]:
    urls = args.get("urls", [])
    if not urls:
        return _err("urls is required and must be non-empty")
    max_concurrent = args.get("max_concurrent", 5)
    results = await extract_batch_async(urls, max_concurrent=max_concurrent)
    return _ok({
        "results": [_result_to_dict(r) for r in results],
        "total": len(results),
        "successful": sum(1 for r in results if r.method != "failed"),
    })


async def _handle_compile_report(args: dict) -> list[TextContent]:
    title = args.get("title", "Research Report")
    query = args.get("query", "")
    findings = args.get("findings", [])
    sources = args.get("sources", [])
    report = compile_markdown_report(
        title=title, findings=findings, sources=sources, query=query,
    )
    return _ok({"report": report, "word_count": len(report.split())})


async def _handle_research_status(args: dict) -> list[TextContent]:
    from interdeep.extraction import playwright_ext

    status = {
        "extraction": {
            "trafilatura": True,
            "playwright": playwright_ext.is_available(),
        },
        "companion_plugins": {
            "interject": shutil.which("interject-mcp") is not None or True,
            "intersynth": True,
            "interknow": True,
            "intercache": True,
            "interlens": True,
        },
        "note": "Companion plugin availability is best-effort. Use /interdeep:research to run a full research session.",
    }
    return _ok(status)


async def main():
    async with stdio_server() as (read_stream, write_stream):
        await app.run(read_stream, write_stream, app.create_initialization_options())


def cli_main():
    asyncio.run(main())


if __name__ == "__main__":
    cli_main()
```

**Step 5: Run server tests**

```bash
cd interverse/interdeep && uv run pytest tests/test_server.py -v
```

Expected: 3 PASS

**Step 6: Run all tests**

```bash
cd interverse/interdeep && uv run pytest tests/ -v
```

Expected: 8 PASS

**Step 7: Commit**

```bash
cd interverse/interdeep && git add -A && git commit -m "feat: MCP server with extract_content, extract_batch, compile_report, research_status tools"
```

---

## Task 5: Orchestration Skill (SKILL.md)

**Files:**
- Create: `interverse/interdeep/skills/deep-research/SKILL.md`
- Create: `interverse/interdeep/commands/research.md`

**Step 1: Create the orchestration skill**

`skills/deep-research/SKILL.md`:

This is the brain of interdeep — it tells the host AI (Claude/Gemini/Codex) how to orchestrate a deep research session using the MCP tools and companion plugins.

```markdown
---
name: deep-research
description: "Orchestrate a deep research session — searches multiple sources, extracts content, and compiles a structured report. Use when asked to research a topic in depth."
user_invocable: true
argument-hint: "<research query>"
---

# Deep Research Orchestration

You are conducting a deep research session. You have access to MCP tools for content extraction and report compilation, plus companion plugins for search, synthesis, and knowledge persistence.

## Available Tools

### interdeep (content extraction + reports)
- `extract_content(url)` — URL → clean markdown (trafilatura + Playwright)
- `extract_batch(urls)` — batch extraction, concurrent
- `compile_report(title, findings, sources, query)` — structured markdown report
- `research_status()` — check companion plugin availability

### Companion Plugins (compose, don't rebuild)
- **interject** — `interject_scan(source, hours)` and `interject_search(query)` for multi-source discovery (arXiv, HN, GitHub, Exa)
- **intersynth** — Dispatch `synthesize-research` agent for multi-agent synthesis
- **interknow** — `search/vector_search/deep_search` for prior knowledge recall
- **intercache** — `cache_lookup/cache_store` for cross-session content caching
- **interlens** — `detect_thinking_gaps` to find blind spots in research coverage

## Research Protocol

### Phase 1: Orient (understand the query)

1. Classify the query type:
   - **Landscape** — "What tools exist for X?" → broad survey, many sources
   - **Deep-dive** — "How does X work?" → focused technical exploration
   - **Decision** — "Should we use X or Y?" → comparative analysis with tradeoffs
   - **Exploratory** — unclear scope → start broad, narrow iteratively

2. Check prior knowledge:
   - Call `interknow:search` or `interknow:deep_search` with the query
   - If relevant prior research exists, build on it rather than starting from scratch

3. Decompose into sub-queries (2-5 depending on complexity):
   - Each sub-query should be independently searchable
   - Include both broad and specific formulations

### Phase 2: Search (gather sources)

4. Search multiple sources in parallel:
   - `interject_scan(source="exa")` — semantic web search
   - `interject_scan(source="arxiv")` — if academic topic
   - `interject_scan(source="hackernews")` — if tech/community topic
   - `interject_scan(source="github")` — if code/tool topic
   - Adapt source selection to query type

5. Retrieve and rank results:
   - `interject_search(query)` — semantic search across all stored discoveries
   - Filter by relevance score (>0.5 threshold)

### Phase 3: Extract (read the sources)

6. Extract content from top sources:
   - Use `extract_batch(urls)` for the top 5-10 URLs
   - Review extraction quality — if content is thin, try individual `extract_content` with different URLs

7. Progressively report findings to the user:
   - Share key findings as you discover them
   - Ask the user for direction at decision points: "Should I dig deeper into X or pivot to Y?"

### Phase 4: Synthesize (make sense of findings)

8. Check for thinking gaps:
   - Call `interlens:detect_thinking_gaps` with your current findings summary
   - Address any blind spots with targeted follow-up searches

9. Compile the report:
   - Use `compile_report(title, findings, sources, query)` to generate structured markdown
   - Save to `docs/research/<query-slug>/report.md`

### Phase 5: Persist (close the loop)

10. Compound durable findings:
    - If findings contain stable, reusable patterns, use `/interknow:compound` to persist them
    - Only compound facts confirmed by 2+ independent sources

11. Report to user:
    - Present a summary of key findings
    - Share the report path
    - Offer to dig deeper on any specific aspect

## Depth Modes

- **Quick** (default) — 1 round of search + extract. ~5 sources. 2-3 minutes.
- **Balanced** — 2 rounds with sub-query expansion. ~10-15 sources. 5-10 minutes.
- **Deep** — Recursive: initial findings generate follow-up queries, each explored at reduced breadth. ~20-30 sources. 15-30 minutes. Inspired by GPT-Researcher's breadth→depth recursion pattern.

The user can specify depth with: `/interdeep:research deep "query"` or by asking "go deeper" during a session.

## Output Contract

Every research session produces:
1. **Conversational findings** — progressive updates during the session
2. **Report artifact** — `docs/research/<query-slug>/report.md` with YAML frontmatter (date, query, sources_count, providers_used)
3. **Sources log** — embedded in the report as a bibliography section
```

**Step 2: Create the command**

`commands/research.md`:

```yaml
---
name: research
description: "Start a deep research session on a topic"
user_invocable: true
argument-hint: "[quick|balanced|deep] <research query>"
---

# /interdeep:research

Start a deep research session. Invokes the `deep-research` skill.

Usage:
- `/interdeep:research "What are the best MCP servers for code analysis?"` — quick mode (default)
- `/interdeep:research deep "How does trafilatura extract content?"` — deep mode
- `/interdeep:research balanced "Compare Exa vs Tavily for AI search"` — balanced mode
```

**Step 3: Commit**

```bash
cd interverse/interdeep && git add -A && git commit -m "feat: deep-research orchestration skill and /research command"
```

---

## Task 6: Subagent Definitions

**Files:**
- Create: `interverse/interdeep/agents/research-planner.md`
- Create: `interverse/interdeep/agents/source-evaluator.md`
- Create: `interverse/interdeep/agents/report-compiler.md`

**Step 1: Create research planner agent**

`agents/research-planner.md`:

```markdown
---
name: research-planner
description: "Decompose a research query into sub-queries with source routing. Use when starting a deep research session."
model: haiku
---

# Research Planner

You are a research planning agent. Given a research query, decompose it into searchable sub-queries and route each to the most appropriate sources.

## Input

You receive a research query and optional context (prior knowledge, domain classification).

## Output

Return a JSON object:

```json
{
  "query_type": "landscape|deep-dive|decision|exploratory",
  "sub_queries": [
    {
      "query": "specific searchable query",
      "sources": ["exa", "arxiv", "hackernews", "github"],
      "priority": 1
    }
  ],
  "depth_recommendation": "quick|balanced|deep",
  "rationale": "Brief explanation of decomposition strategy"
}
```

## Guidelines

- Generate 2-5 sub-queries depending on complexity
- Each sub-query should be independently searchable (no cross-references)
- Route to sources based on query nature:
  - Technical/code topics → exa, github, hackernews
  - Academic/research topics → arxiv, exa
  - Comparison/landscape → exa, hackernews, github
  - General knowledge → exa
- Priority 1 = most important, higher = lower priority
- If the query is already specific enough, return a single sub-query
```

**Step 2: Create source evaluator agent**

`agents/source-evaluator.md`:

```markdown
---
name: source-evaluator
description: "Evaluate source credibility and relevance for research findings. Use after content extraction to rank sources."
model: haiku
---

# Source Evaluator

You evaluate extracted content for credibility and relevance to the research query.

## Input

You receive:
- The original research query
- A list of extracted content results (url, title, content snippet, extraction method)

## Output

Return a JSON array of source evaluations:

```json
[
  {
    "url": "https://...",
    "relevance": "high|medium|low",
    "credibility": "high|medium|low",
    "key_finding": "One sentence summary of what this source contributes",
    "include_in_report": true
  }
]
```

## Evaluation Criteria

- **Relevance:** Does the content directly answer the research query or its sub-queries?
- **Credibility:** Is this an authoritative source? (official docs > blog posts > forums)
- **Freshness:** Is the information current? (check dates if available)
- **Uniqueness:** Does this source add information not found in other sources?
- Recommend `include_in_report: false` for low-relevance or low-credibility sources
```

**Step 3: Create report compiler agent**

`agents/report-compiler.md`:

```markdown
---
name: report-compiler
description: "Compile evaluated findings into a coherent research report. Use after source evaluation to produce the final output."
model: sonnet
---

# Report Compiler

You compile evaluated research findings into a structured, well-written report.

## Input

You receive:
- The original research query
- Evaluated findings (content + relevance + credibility scores)
- Source list with evaluations

## Output

A structured markdown report with:
1. **Executive summary** — 2-3 sentences answering the core question
2. **Key findings** — organized by theme, not by source
3. **Analysis** — synthesis across sources, identifying patterns, contradictions, and gaps
4. **Recommendations** — if the query type is "decision", include clear recommendations
5. **Sources** — bibliography with inline citations `[1]` throughout the text

## Guidelines

- Write for a technical audience but explain domain-specific terms
- Cite sources inline using numbered references `[1]`, `[2]`
- Highlight areas of disagreement between sources
- Flag information gaps where more research is needed
- Keep the report between 500-2000 words depending on query complexity
```

**Step 4: Commit**

```bash
cd interverse/interdeep && git add -A && git commit -m "feat: research-planner, source-evaluator, report-compiler agents"
```

---

## Task 7: Required Documentation

**Files:**
- Create: `interverse/interdeep/CLAUDE.md`
- Create: `interverse/interdeep/AGENTS.md`
- Create: `interverse/interdeep/PHILOSOPHY.md`
- Create: `interverse/interdeep/README.md`

**Step 1: Create `CLAUDE.md`** (≤80 lines per plugin standard)

```markdown
# interdeep

> See `AGENTS.md` for full development guide.

## Overview

Deep research plugin — 4 MCP tools (extract_content, extract_batch, compile_report, research_status), 1 skill (deep-research), 3 agents (research-planner, source-evaluator, report-compiler), 1 command (/research). Python MCP server with trafilatura + optional Playwright extraction. Composes with interject (search), intersynth (synthesis), interknow (knowledge), intercache (caching), interlens (thinking gaps).

## Quick Commands

```bash
# Run tests
cd tests && uv run pytest -q

# Start MCP server locally
uv run interdeep-mcp

# Check extraction works
uv run python -c "from interdeep.extraction.hybrid import extract_hybrid; print(extract_hybrid(url='https://example.com'))"
```

## Design Decisions (Do Not Re-Ask)

- Plugin owns extraction + orchestration only; search providers are interject's responsibility
- trafilatura fast path + optional Playwright fallback (graceful degradation)
- Host-agent-as-brain: MCP tools are stateless, orchestration intelligence lives in SKILL.md
- GPT-Researcher is inspire + port-partially, not a dependency
- No LangChain dependency — direct MCP protocol
```

**Step 2: Create `AGENTS.md`** (following plugin standard structure)

Write per the AGENTS.md template in plugin-standard.md, including: Canonical References, Quick Reference table, Overview, Architecture tree, How It Works sections for extraction and orchestration, Component Conventions, Integration Points table, Testing, and Known Constraints.

**Step 3: Create `PHILOSOPHY.md`**

Write per the PHILOSOPHY.md template: Purpose, North Star ("maximize research quality per token spent"), Working Priorities, Brainstorming/Planning Doctrine (standard boilerplate), Decision Filters specific to interdeep.

**Step 4: Create `README.md`**

Write per the README.md template: What this does (prose), Installation (marketplace two-step), Usage (slash command examples), Architecture (tree), Design decisions, License.

**Step 5: Commit**

```bash
cd interverse/interdeep && git add -A && git commit -m "docs: CLAUDE.md, AGENTS.md, PHILOSOPHY.md, README.md"
```

---

## Task 8: Structural Tests

**Files:**
- Create: `interverse/interdeep/tests/pyproject.toml`
- Create: `interverse/interdeep/tests/structural/conftest.py`
- Create: `interverse/interdeep/tests/structural/helpers.py`
- Create: `interverse/interdeep/tests/structural/test_structure.py`
- Create: `interverse/interdeep/tests/structural/test_skills.py`

**Step 1: Create test infrastructure**

`tests/pyproject.toml`:

```toml
[project]
name = "interdeep-tests"
version = "0.1.0"
requires-python = ">=3.12"
dependencies = ["pytest>=8.0", "pyyaml>=6.0"]

[tool.pytest.ini_options]
testpaths = ["structural"]
pythonpath = ["structural"]
```

`tests/structural/conftest.py`:

```python
import json
from pathlib import Path
import pytest

@pytest.fixture
def project_root():
    return Path(__file__).parent.parent.parent

@pytest.fixture
def skills_dir(project_root):
    return project_root / "skills"

@pytest.fixture
def plugin_json(project_root):
    pj = project_root / ".claude-plugin" / "plugin.json"
    return json.loads(pj.read_text())
```

`tests/structural/helpers.py`:

```python
import re

def parse_frontmatter(path):
    text = path.read_text()
    match = re.match(r"^---\s*\n(.*?)\n---", text, re.DOTALL)
    if not match:
        return {}
    import yaml
    return yaml.safe_load(match.group(1)) or {}
```

**Step 2: Create structural tests**

`tests/structural/test_structure.py`:

```python
import json
from pathlib import Path
import pytest

def test_plugin_json_valid(project_root):
    pj = project_root / ".claude-plugin" / "plugin.json"
    assert pj.exists()
    data = json.loads(pj.read_text())
    assert "name" in data
    assert "version" in data
    assert "description" in data
    assert "author" in data
    assert "skills" in data

def test_required_files_exist(project_root):
    for f in ["README.md", "CLAUDE.md", "AGENTS.md", "PHILOSOPHY.md", "LICENSE", ".gitignore"]:
        assert (project_root / f).exists(), f"{f} missing"

def test_scripts_executable(project_root):
    import os
    for script in (project_root / "scripts").glob("*.sh"):
        assert os.access(script, os.X_OK), f"{script.name} not executable"

def test_skills_exist_on_disk(project_root, plugin_json):
    for skill_path in plugin_json.get("skills", []):
        skill_dir = project_root / skill_path.lstrip("./")
        assert skill_dir.exists(), f"Skill {skill_path} not on disk"
        assert (skill_dir / "SKILL.md").exists(), f"SKILL.md missing in {skill_path}"

def test_commands_exist_on_disk(project_root, plugin_json):
    for cmd_path in plugin_json.get("commands", []):
        assert (project_root / cmd_path.lstrip("./")).exists(), f"Command {cmd_path} not on disk"

def test_agents_exist_on_disk(project_root, plugin_json):
    for agent_path in plugin_json.get("agents", []):
        assert (project_root / agent_path.lstrip("./")).exists(), f"Agent {agent_path} not on disk"
```

`tests/structural/test_skills.py`:

```python
from pathlib import Path
from helpers import parse_frontmatter

def test_skill_count(plugin_json):
    assert len(plugin_json.get("skills", [])) == 1

def test_skill_frontmatter(project_root, plugin_json):
    for skill_path in plugin_json.get("skills", []):
        skill_md = project_root / skill_path.lstrip("./") / "SKILL.md"
        fm = parse_frontmatter(skill_md)
        assert "name" in fm, f"{skill_md}: missing 'name' in frontmatter"
        assert "description" in fm, f"{skill_md}: missing 'description' in frontmatter"
```

**Step 3: Run structural tests**

```bash
cd interverse/interdeep/tests && uv run pytest -q
```

Expected: All PASS

**Step 4: Commit**

```bash
cd interverse/interdeep && git add -A && git commit -m "test: structural tests per plugin standard"
```

---

## Task 9: Extend interject with New Adapters

**Files:**
- Create: `interverse/interject/src/interject/sources/tavily.py`
- Create: `interverse/interject/src/interject/sources/brave.py`
- Create: `interverse/interject/src/interject/sources/pubmed.py`
- Create: `interverse/interject/src/interject/sources/semantic_scholar.py`
- Create: `interverse/interject/src/interject/sources/searxng.py`
- Modify: `interverse/interject/src/interject/scanner.py` (add to ADAPTER_CLASSES)
- Modify: `interverse/interject/config/default.yaml` (add config blocks)
- Modify: `interverse/interject/pyproject.toml` (add optional deps)
- Modify: `interverse/interject/.claude-plugin/plugin.json` (add env vars)

This task adds 5 new source adapters to interject, following the existing adapter pattern. Each adapter implements the `SourceAdapter` protocol: `name` attribute, `async fetch(since, topics)`, `async enrich(discovery)`.

**Step 1: Implement Tavily adapter**

`src/interject/sources/tavily.py` — Uses `aiohttp` to call Tavily Search API. Requires `TAVILY_API_KEY`. Returns web search results as `RawDiscovery` items.

**Step 2: Implement Brave adapter**

`src/interject/sources/brave.py` — Uses `aiohttp` to call Brave Search API. Requires `BRAVE_API_KEY`. Returns web results.

**Step 3: Implement PubMed adapter**

`src/interject/sources/pubmed.py` — Uses `aiohttp` to call NCBI E-utilities API. No API key required (rate limited to 3 req/sec). Returns medical/biological paper results.

**Step 4: Implement Semantic Scholar adapter**

`src/interject/sources/semantic_scholar.py` — Uses `aiohttp` to call Semantic Scholar API. No API key required (rate limited). Returns academic paper results across CS, bio, medicine.

**Step 5: Implement SearXNG adapter**

`src/interject/sources/searxng.py` — Uses `aiohttp` to call a local SearXNG instance. No API key, but requires `SEARXNG_URL` env var. Returns federated metasearch results.

**Step 6: Register all adapters in `scanner.py`**

Add to `ADAPTER_CLASSES`:

```python
"tavily":           ("interject.sources.tavily",           "TavilyAdapter"),
"brave":            ("interject.sources.brave",            "BraveAdapter"),
"pubmed":           ("interject.sources.pubmed",           "PubMedAdapter"),
"semantic_scholar": ("interject.sources.semantic_scholar", "SemanticScholarAdapter"),
"searxng":          ("interject.sources.searxng",          "SearXNGAdapter"),
```

**Step 7: Add config blocks to `default.yaml`**

Add `sources:` entries for each new adapter with `enabled: true` and sensible defaults.

**Step 8: Add env vars to `plugin.json`**

```json
"env": {
  "EXA_API_KEY": "${EXA_API_KEY}",
  "TAVILY_API_KEY": "${TAVILY_API_KEY}",
  "BRAVE_API_KEY": "${BRAVE_API_KEY}",
  "SEARXNG_URL": "${SEARXNG_URL}"
}
```

**Step 9: Commit in interject repo**

```bash
cd interverse/interject && git add -A && git commit -m "feat: add Tavily, Brave, PubMed, Semantic Scholar, SearXNG adapters for interdeep"
```

---

## Task 10: Integration Test and Publish

**Files:**
- No new files — integration verification

**Step 1: Verify interdeep MCP server starts**

```bash
cd interverse/interdeep && uv run interdeep-mcp &
PID=$!; sleep 3; kill $PID 2>/dev/null
echo "MCP server OK"
```

**Step 2: Verify extraction works end-to-end**

```bash
cd interverse/interdeep && uv run python -c "
from interdeep.extraction.hybrid import extract_hybrid
result = extract_hybrid(url='https://example.com')
print(f'Method: {result.method}, Length: {result.content_length}')
assert result.content_length > 0, 'Extraction failed'
print('OK')
"
```

**Step 3: Run all tests**

```bash
cd interverse/interdeep && uv run pytest tests/ -v
cd interverse/interdeep/tests && uv run pytest -q
```

**Step 4: Publish plugin**

```bash
cd interverse/interdeep && ic publish init
```

This creates the git repo, registers in marketplace, rebuilds cache, enables in settings. Restart session after init for hooks/skills to load.

**Step 5: Verify plugin loads in Claude Code**

After restarting session:
- Check `/interdeep:research` command is available
- Check `research_status` MCP tool returns companion plugin info
- Check `extract_content` MCP tool works

**Step 6: Final commit and push**

```bash
cd interverse/interdeep && git add -A && git commit -m "chore: integration verified, ready for use"
git push -u origin main
```
