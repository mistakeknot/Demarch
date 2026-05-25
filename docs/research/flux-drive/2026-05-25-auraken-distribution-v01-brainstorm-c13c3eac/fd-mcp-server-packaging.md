<!-- flux-drive:complete -->
<!-- run_uuid: 57272bdd-9eb0-42d1-8ae7-ed79e4d7aa8a -->

# fd-mcp-server-packaging — Review

**Target:** docs/brainstorms/2026-05-25-auraken-distribution-v01-brainstorm.md
**Lens:** Python packaging maintainer perspective on whether dist/v0.1/mcp-servers/auraken-lens/ works when extracted by a user with no access to the Sylveste monorepo.

## Findings Index

- F1 (P0) — `AURAKEN_SRC` resolves to `_HERE.parents[3] / "src"` (server.py:41), which is monorepo-relative and breaks on tarball extraction
- F2 (P0) — server.py imports `from auraken.lenses import select_lenses` (line 47) from the **legacy standalone Python daemon at apps/Auraken/src/**; the dist bundle has no documented vendoring strategy for this import
- F3 (P1) — `pyproject.toml` lists only `mcp>=1.0.0`; http-mode runtime imports `uvicorn`, `starlette`, and (indirectly) `httpx` are missing from `dependencies`
- F4 (P1) — `mcp>=1.0.0` lower bound has no upper bound; MCP SDK 2.x release breaks the installed server
- F5 (P1) — `trajectory.py` is imported via `sys.path.insert(0, str(_HERE))` (server.py:49) — this works only because server.py and trajectory.py sit in the same dir; the bundle must preserve this layout exactly through pyproject.toml's `py-modules` directive
- F6 (P2) — Development tree contains `server.py.bak-pre-http-*` and `server.py.bak-pre-auth-*` + `__pycache__/`; no curation step specified for the dist tarball
- F7 (P2) — `pyproject.toml` `version = "0.0.1"` does not match the bundle version `0.1.0` declared in MANIFEST.yaml
- F8 (P3) — `[project.scripts] auraken-lens-mcp = "server:main"` assumes a flat-layout package; will fail if the user `pip install`s the bundle from a layout where server.py is nested

## Verdict

The MCP server is **not currently packageable as a release artifact.** F1 alone is ship-blocking: every fresh install will fail with `ModuleNotFoundError: No module named 'auraken'` at server startup. F2 compounds it — even if AURAKEN_SRC is fixed, the import depends on the legacy daemon's Python package, which is not part of any obvious distribution boundary.

The brainstorm correctly identifies the bundle as "a curated copy" but the curation it does not specify is precisely the part that makes external distribution work: which imports get vendored, which paths get rewritten, which extras get added. Plan phase needs a one-page "what goes in dist/v0.1/mcp-servers/auraken-lens/" deliverable that addresses F1 and F2 explicitly.

## Summary

server.py is written as a development-tree script that reaches up the monorepo to import `auraken.lenses` from `apps/Auraken/src/`. This is fine for the recon spike running inside the monorepo. It is not fine for a tarball extracted to `/tmp/auraken-v0.1.0/`, which is the entire premise of the v0.1 bundle. The brainstorm's bundle layout (lines 32–48) does **not** include `apps/Auraken/src/auraken/lenses/` — only the MCP server and skill files. So either (a) the bundle needs to vendor `auraken.lenses` (and its transitive Python deps), or (b) the MCP server needs to be rewritten to shell out to the Go binary (the brainstorm's binary-distribution path), or (c) `auraken.lenses` ships as a published PyPI package. The brainstorm picks none of these.

## Issues Found

### F1 — P0 — AURAKEN_SRC path resolution breaks for all users

**Where:** apps/Auraken/integrations/hermes/mcp-servers/auraken-lens/server.py:40–47.

```python
_HERE = Path(__file__).resolve().parent
_DEFAULT_AURAKEN_SRC = _HERE.parents[3] / "src"
AURAKEN_SRC = Path(os.environ.get("AURAKEN_SRC", _DEFAULT_AURAKEN_SRC))
if str(AURAKEN_SRC) not in sys.path:
    sys.path.insert(0, str(AURAKEN_SRC))
from auraken.lenses import select_lenses  # noqa: E402
```

**Failure scenario:** Inside the monorepo, `_HERE` is `…/apps/Auraken/integrations/hermes/mcp-servers/auraken-lens/`, so `_HERE.parents[3]` is `…/apps/Auraken/`, so `AURAKEN_SRC = …/apps/Auraken/src/`, and the import resolves. After install.sh step 5 installs the MCP into the user's profile (e.g., `~/.hermes/mcp-servers/auraken-lens/`), `_HERE.parents[3]` is `~/` (or `/root`), and `~/src/auraken/lenses.py` does not exist. ImportError at server startup — Hermes logs an MCP-failed message that 99% of users will not check, and `lens_select` simply never returns results.

**Smallest viable fix (depends on F2 decision):**
- If vendoring: copy `apps/Auraken/src/auraken/lenses/` into `dist/v0.1/mcp-servers/auraken-lens/auraken/` and change line 41 to `_DEFAULT_AURAKEN_SRC = _HERE`. The package becomes self-contained.
- If shelling out to the Go binary: delete lines 40–47 entirely; `call_tool` invokes the `auraken-lens` Go binary via subprocess and parses its JSON output.

### F2 — P0 — `auraken.lenses` import vendoring strategy is undefined

**Where:** brainstorm §"Bundle layout" (lines 32–48) and §"Decision deferred to plan phase" (lines 105–109).

The brainstorm's bundle layout includes `mcp-servers/auraken-lens/{pyproject.toml, server.py, trajectory.py}` but **not** the `auraken.lenses` Python package this MCP server imports from. The brainstorm discusses the **Go lens-selection binary** under §"auraken-lens binary distribution" ("vendors a pre-built binary per platform"), but `auraken.lenses` in server.py:47 is a **separate Python module** (per apps/Auraken/CLAUDE.md: "The legacy standalone Python daemon under src/auraken/ awaits absorption into the Hermes overlay"). The Go-binary plan does not cover this Python dependency.

**Question:** Is the v0.1 bundle's lens-selection backend (a) the legacy Python `select_lenses` function, or (b) the Go `auraken-lens` binary? The brainstorm reads both ways. server.py today uses (a); MANIFEST capability `binary_required: …/auraken-lens@v0.1.0` reads as (b).

**Smallest viable fix:** Plan phase decides one. Recommended: switch server.py to shell out to the Go binary (consistent with the brainstorm's release-asset story); deprecate the Python `select_lenses` import path for the dist bundle.

### F3 — P1 — http-mode dependencies missing from pyproject.toml

**Where:** apps/Auraken/integrations/hermes/mcp-servers/auraken-lens/pyproject.toml lines 8–10; vs server.py lines 198–205:

```python
def _main_http(host: str, port: int) -> None:
    import contextlib
    import hmac
    import uvicorn
    from mcp.server.streamable_http_manager import StreamableHTTPSessionManager
    from starlette.applications import Starlette
    from starlette.responses import PlainTextResponse
    from starlette.routing import Mount
```

**Failure scenario:** A user does `pip install auraken-lens-mcp` (or the equivalent from the dist tarball), runs the server with `AURAKEN_LENS_TRANSPORT=http`, and gets `ModuleNotFoundError: No module named 'uvicorn'`. The error is at request-time, not install-time, so the install appears successful.

**Smallest viable fix:** Add `[project.optional-dependencies] http = ["uvicorn", "starlette"]` and document `pip install 'auraken-lens-mcp[http]'`. Alternatively, move them to `dependencies` if v0.1 always wants http available.

### F4 — P1 — Unbounded `mcp` lower bound

**Where:** pyproject.toml line 9: `"mcp>=1.0.0"`.

**Failure scenario:** Even once MCP SDK 1.x exists, an unbounded `>=` lets pip install mcp 2.x if released, which is presumed to contain breaking API changes (`Server`, `NotificationOptions`, `stdio_server`, `streamable_http_manager` are all SDK surface that's churned). v0.1 installs done weeks apart will pull different mcp versions silently.

**Smallest viable fix:** Replace `"mcp>=1.0.0"` with the narrowest range that includes the version this server is tested against. Document the tested version in MANIFEST.yaml `compatibility` block.

### F5 — P1 — `trajectory.py` sibling-import contract

**Where:** server.py:49: `sys.path.insert(0, str(_HERE))` + `from trajectory import TrajectoryCapture`.

This works because server.py and trajectory.py are sibling files. But: if the dist tarball is `pip install`ed (per pyproject.toml's `[project.scripts]`), setuptools may not treat trajectory.py as a module of the same package — the current pyproject.toml has no `[tool.setuptools.py-modules]` or `[tool.setuptools.packages.find]` directive.

**Failure scenario:** `pip install .` from the bundle root succeeds, creates the `auraken-lens-mcp` entry point, but the entry point's `main()` fails on `from trajectory import TrajectoryCapture` because the trajectory.py file was not packaged.

**Smallest viable fix:** Add `[tool.setuptools] py-modules = ["server", "trajectory"]` to pyproject.toml, or refactor into a package directory with `__init__.py`.

### F6 — P2 — Backup file + cache contamination in dist tarball

**Where:** apps/Auraken/integrations/hermes/mcp-servers/auraken-lens/ contains `server.py.bak-pre-auth-20260504T161631Z`, `server.py.bak-pre-http-20260504T080102Z`, and `__pycache__/`.

**Failure scenario:** A naive `cp -r` of the dev tree into `dist/v0.1/mcp-servers/auraken-lens/` ships these. Tarball is larger than needed; old auth-less and http-less server snapshots leak into release. Security-conscious users see two `.bak` files and wonder what changed.

**Smallest viable fix:** Curation step in the release pipeline uses an explicit file list (or `.distignore`). Recommended: write a `scripts/build-dist.sh` that creates dist/v0.1/ from explicit paths, not `cp -r` from the dev tree.

### F7 — P2 — Version drift between pyproject.toml and MANIFEST.yaml

**Where:** pyproject.toml line 4: `version = "0.0.1"`; brainstorm MANIFEST.yaml: `version: 0.1.0`.

**Failure scenario:** A user running `pip show auraken-lens-mcp` sees 0.0.1, but reads "Auraken Hermes distribution v0.1.0" in INSTALL.md and `cat MANIFEST.yaml`. Version skew in the wild becomes a support load.

**Smallest viable fix:** Bump pyproject.toml to `0.1.0` as part of the dist-curation step. Optionally: single-source the version from MANIFEST.yaml via a build-time substitution.

### F8 — P3 — Entry-point/script-name conventions

**Where:** pyproject.toml lines 12–13: `auraken-lens-mcp = "server:main"`.

The entry-point points at the top-level module `server` (not a package). Works in a flat-layout pip install but is fragile if a user inadvertently has a `server.py` higher on `sys.path`. Convention: package the code as `auraken_lens_mcp/__init__.py` + `auraken_lens_mcp/server.py` and reference `auraken_lens_mcp.server:main`. Refactor in v0.2 — not blocking for v0.1 if F5 is addressed.

## Improvements

- **Write `scripts/build-dist.sh`** as the canonical release-tarball builder. Reads MANIFEST.yaml, copies an explicit file list, runs F1/F6/F7 fixes deterministically, verifies the result with `pip install` into a tmp venv.
- **Add a smoke test** to the dist bundle: `dist/v0.1/scripts/verify-install.sh` that runs `pip install` against a tmp venv and invokes the entry-point. Catches F1/F3/F5 before release.
- **Single-source the version.** MANIFEST.yaml is canonical; pyproject.toml derives. Current dual-source guarantees drift.
- **Decide F2 in plan phase before scoping install.sh.** The vendor-vs-shell-out-to-binary decision changes pyproject.toml's `dependencies` substantially.
