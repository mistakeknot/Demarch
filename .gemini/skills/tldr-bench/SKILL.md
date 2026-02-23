---
name: tldr-bench
description: "Interverse driver capability: tldr-bench"
---
# Gemini Skill: tldr-bench

You have activated the tldr-bench capability.

## Base Instructions
# AGENTS.md - AI Agent Instructions for tldr-bench

This repo contains token-efficiency benchmarks for tldr-swinton.

## Quickstart (uv)

```bash
uv venv
uv pip install -e ".[dev]"
PYTHONPATH=tldr-bench uv run python tldr-bench/scripts/run_bench.py --help
```

## Rules

- Use `tldrs`, not `tldr`.
- Prefer `uv run` for scripts/tests.
- Do not commit anything under `tldr-bench/results/` (gitignored).
- For CLI frontier runs, use the shim and capture token counts via JSONL logging.

## Common Commands

```bash
# List tasks
PYTHONPATH=tldr-bench uv run python tldr-bench/scripts/run_bench.py --tasks track_context --list-tasks

# Track A (static/context)
PYTHONPATH=tldr-bench uv run python tldr-bench/scripts/run_bench.py --tasks track_context --variant baselines --print-results

# Start shim (enable JSONL logging in config)
PYTHONPATH=tldr-bench uv run --with fastapi --with uvicorn python tldr-bench/tldr_bench/shim/server.py --config tldr-bench/shim/config.toml

# Track B (frontier via shim)
PYTHONPATH=tldr-bench uv run python tldr-bench/scripts/run_bench.py --tasks track_frontier --variant baselines --allow-cli --shim-log-path /tmp/tldr-shim.jsonl --print-results
```

## Apple Silicon (arm64) SWE-bench

```bash
# Build a single SWE-bench instance image for arm64
PYTHONPATH=tldr-bench uv run python tldr-bench/scripts/build_swebench_arm64.py \\
  --instance-id django__django-11333

# Use arm64 images during OpenHands SWE-bench runs
export SWE_BENCH_ARCH=arm64
export SWE_BENCH_IMAGE_PREFIX=swebench
export OPENHANDS_DOCKER_PLATFORM=linux/arm64
```

## Tests

```bash
PYTHONPATH=tldr-bench uv run --with pytest python -m pytest tldr-bench/tests -v
```


