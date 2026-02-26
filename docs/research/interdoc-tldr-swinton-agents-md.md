# interdoc Analysis: tldr-swinton AGENTS.md

**Date**: 2026-02-25
**Plugin**: tldr-swinton (v0.7.14)
**Source**: `/home/mk/projects/Demarch/interverse/tldr-swinton/AGENTS.md`
**Original size**: 668 lines

## Analysis Summary

The tldr-swinton AGENTS.md is the largest plugin AGENTS.md in the Interverse at 668 lines. It contains significant bloat from accumulated version history, duplicate content with CLAUDE.md, stale references to pre-monorepo paths, and verbose sections that can be extracted to topic files.

## Issues Found

### 1. Stale References (P0)

- **Pre-monorepo paths**: Lines 19-25, 30 reference `/root/projects/Interverse/infra/interbench` -- this is now at `/home/mk/projects/Demarch/core/interbench`
- **Stale skill name**: Line 593 says "ashpool-sync" but the actual skill is `tldrs-interbench-sync`
- **Pre-restructure source paths**: File Reference table (lines 563-583) uses flat paths like `cli.py`, `api.py`, `ast_extractor.py` -- actual paths are now under `src/tldr_swinton/modules/core/` and `src/tldr_swinton/modules/semantic/`

### 2. Duplicate Content with CLAUDE.md (P1)

Both files document:
- Plugin commands (6 slash commands) -- AGENTS.md lines 78-84, CLAUDE.md lines 22-27
- Skill descriptions -- AGENTS.md lines 89-93, CLAUDE.md lines 29-33
- Hook descriptions -- AGENTS.md lines 95-98, CLAUDE.md lines 65-69
- Plugin install instructions -- both files
- interbench sync workflow -- both files

**Resolution**: AGENTS.md should be the canonical source. CLAUDE.md should reference AGENTS.md for shared content and only contain Claude-specific items (publish runbook, Claude-specific notes).

### 3. Version History Bloat (P1)

Lines 609-668 (60 lines) of version history. This is changelog content, not agent instructions. Should be extracted to a separate file or removed entirely (the git log serves this purpose).

### 4. Inaccurate Plugin Structure Documentation (P1)

- AGENTS.md says "3 skills" (line 592) -- actually 4 skills in plugin.json (finding-duplicate-functions was added)
- AGENTS.md says "PostToolUse:Read hook" but doesn't mention PreToolUse:Serena hooks accurately
- AGENTS.md references `hooks.json` format but actual hooks.json has different structure than described

### 5. MCP Tools Not Fully Documented (P2)

AGENTS.md mentions MCP tools briefly (lines 193-198) but doesn't list the 24 actual tools registered in `mcp_server.py`. The MCP server is the primary interface for agents -- it deserves proper documentation.

**Actual MCP tools** (from mcp_server.py):
- Navigation: `tree`, `structure`, `search`, `extract`
- Context: `context`, `diff_context`, `distill`, `delegate`
- Flow analysis: `cfg`, `dfg`, `slice`
- Codebase analysis: `impact`, `dead`, `arch`, `calls`
- Import analysis: `imports`, `importers`
- Semantic search: `semantic`, `semantic_index`, `semantic_info`
- Quality: `diagnostics`, `change_impact`, `verify_coherence`
- Structural search: `structural_search`
- Admin: `hotspots`, `status`

### 6. Verbose Sections That Can Be Compressed (P2)

- Delta Context Mode (lines 143-192): 50 lines for a feature that's a flag on two commands. Can be 15 lines.
- Compression Modes (lines 269-284): 16 lines. Can be 8 lines.
- Semantic Search Backends (lines 443-476): 34 lines with full install instructions. Can be 15 lines.
- Module Selection (lines 225-267): 43 lines repeating the agent-workflow.md decision tree. Should just reference it.
- Common Tasks > Adding a New Language (lines 420-428): Step list that belongs in a contributor guide, not agent instructions
- Debugging section (lines 479-511): 33 lines of debugging commands. Useful but verbose.
- Testing section (lines 513-559): 47 lines. Most of this is standard practice, not tldr-specific.

### 7. Extracted Content Sizing

Content candidates for extraction to `docs/dev-reference.md`:
- Version History: ~60 lines
- Debugging commands: ~33 lines
- Testing procedures: ~47 lines
- Adding new languages: ~9 lines
- Common task procedures: ~20 lines
Total extractable: ~169 lines (well over the 80-line threshold)

## Rewrite Plan

### Target Structure (300-400 lines)

1. **Header + Overview** (~10 lines)
2. **Quick Reference** (~25 lines) - install, smoke test
3. **Architecture** (~35 lines) - extraction pipeline, semantic pipeline, source layout
4. **MCP Tools** (~50 lines) - full tool catalog with cost ladder
5. **Plugin Structure** (~25 lines) - skills, hooks, commands (accurate)
6. **CLI Commands** (~30 lines) - decision tree referencing agent-workflow.md
7. **Critical Rules** (~30 lines) - import convention, language field, normalization
8. **Key Data Structures** (~20 lines) - FunctionInfo, ModuleInfo, CodeUnit
9. **Semantic Search** (~20 lines) - backends, install, build
10. **Delta Context** (~15 lines) - condensed
11. **Compression** (~8 lines) - condensed
12. **Output Caps** (~10 lines)
13. **Operational Notes** (~15 lines) - embedding model, gotchas, do-not-adopt
14. **Related Projects** (~15 lines) - interbench with corrected paths
15. **Dev Reference** (~10 lines) - pointer to docs/dev-reference.md

### Extracted to `docs/dev-reference.md`

- Version history
- Debugging procedures
- Testing procedures
- Adding new language walkthrough
- Detailed backend install instructions
- ContextPack notes
- VHS ref storage details

### Changes to CLAUDE.md

No changes needed -- CLAUDE.md is already properly structured with Claude-specific content (publish runbook) and references to AGENTS.md. The duplicate command/skill listings in CLAUDE.md are acceptable since CLAUDE.md is the first file Claude Code reads and having them there aids quick orientation.

## Files Modified

1. `/home/mk/projects/Demarch/interverse/tldr-swinton/AGENTS.md` -- rewritten (668 -> ~370 lines)
2. `/home/mk/projects/Demarch/interverse/tldr-swinton/docs/dev-reference.md` -- new, extracted content
