# Gemini CLI Integration Adapter

**Bead:** iv-m4cu
**Date:** 2026-02-22
**Status:** Planned

## Problem
Clavain and Interverse drivers (plugins, hooks, MCP servers) are currently tightly coupled to the Claude Code extension architecture (specifically, environmental hook interfaces, slash command structures, and agent instruction pre-loading). Gemini CLI uses different IPC for hooks (JSON over stdin/stdout vs env vars/exit codes), a different instruction-loading paradigm (Progressive Disclosure via `SKILL.md` vs context pre-loading), and standalone tools vs slash commands. To run the Interverse OS and drivers via Gemini CLI, an adapter layer is required.

## Strategy

We will implement an adapter layer rather than rewriting the core Go binaries or Python/Node MCP servers. This ensures compatibility with both environments.

### 1. Hook Adapter Bridge
**Goal:** Translate Gemini CLI JSON IPC to Claude Code hook environment expectations.
- **Input:** Reads JSON event payload from `stdin`.
- **Mapping:** Translates Gemini events (e.g., `BeforeTool`) to Claude Code events (e.g., `PreToolUse`).
- **Execution:** Sets environment variables (e.g., `CLAUDE_PROJECT_DIR` which Gemini provides as an alias) and calls the original Interverse hook script.
- **Output:** Captures the exit code and outputs `{"decision": "allow"}` or `{"decision": "deny", "reason": "..."}` to `stdout` as required by Gemini. Debug logs go to `stderr`.

### 2. MCP Server Registration
**Goal:** Expose existing Interverse MCP servers (e.g., `interflux`, `interkasten`, `tldr-swinton`) to Gemini CLI.
- Gemini natively supports MCP. We will add a setup script or instructions to register the existing `launch-mcp.sh` scripts in Gemini's `.gemini/settings.json` or via `gemini mcp add`.

### 3. Skill Generation (Progressive Disclosure)
**Component:** `scripts/gen-gemini-skills.sh`
**Goal:** Migrate from full context pre-loading to Gemini's on-demand `SKILL.md` loading.
- Extend the `Token-Efficient Skill Loading` pattern.
- Create a script that compiles existing phase docs (`phases/*.md`, `references/*.md`) and agent instructions into standalone Gemini `SKILL.md` files with required YAML frontmatter (`name` and `description`).
- These skills will be placed in a directory for Gemini to discover and activate via `activate_skill`.

### 4. Operations Skill
**Goal:** Replace Claude Code slash commands (e.g., `/interpub:release`).
- Create a Gemini skill (`interverse-ops`) that instructs the LLM to run the underlying scripts directly (e.g., `bash scripts/bump-version.sh <version>`) instead of attempting slash commands.

## Execution Steps
1.  **Draft Hook Adapter Bridge:** Create the initial shell script to translate Gemini `stdin` JSON into the environment structure expected by existing `hooks.json` scripts.
2.  **Test Hook Bridge:** Validate with a simple hook (like `intercheck`'s `PreToolUse` guard).
3.  **Implement Skill Generator:** Write the script to transform `AGENTS.md` and phase docs into valid `SKILL.md` structures with YAML frontmatter.
4.  **Create Operations Skill:** Draft `interverse-ops` to map old slash commands to CLI scripts.
5.  **Documentation:** Update `GEMINI.md` and `CLAUDE.md` with instructions on how to initialize the integration.