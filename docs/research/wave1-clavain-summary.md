# Wave 1: Clavain Solution Docs Classification Summary

Reviewed 19 solution docs from `hub/clavain/docs/solutions/`. Cross-referenced against root CLAUDE.md, hub/clavain/CLAUDE.md, hub/clavain/AGENTS.md, and Interverse MEMORY.md.

## Findings

- **3 already covered** (prune candidates): hierarchical-config-resolution (duplicated verbatim in MEMORY.md B1 section), disable-model-invocation-blocks-skill-tool (superseded by the broader lfg-pipeline doc), settings-heredoc-permission-bloat (already propagated to root CLAUDE.md Settings Hygiene).
- **8 need MEMORY.md additions**: Most are Claude Code plugin schema lessons (MCP bootstrap wrappers, agent registry session lifecycle, mid-session publish symlinks, disable-model-invocation chaining, duplicate MCP registration). Two are cross-cutting monorepo patterns (glob depth prefixing, provenance tracking for LLM compounding).
- **1 needs CLAUDE.md update**: Oracle browser mode output rules (--write-output and --timeout) are missing from root CLAUDE.md's Oracle section despite being critical operational knowledge.
- **1 needs AGENTS.md update**: Agent consolidation grep sweep checklist belongs in clavain AGENTS.md under component conventions.
- **6 need no action**: Fine as historical solution docs (smoke test behavior, template consumers, content-assembly unification, Codex CLI flags, pytest conftest, beads ACL permissions).

## Priority Actions

1. Update root `~/.claude/CLAUDE.md` Oracle section with --write-output and --timeout rules (high impact, prevents data loss).
2. Add 8 plugin schema / cross-cutting lessons to Interverse MEMORY.md (prevents re-discovery).
3. Add agent rename/delete checklist to `hub/clavain/AGENTS.md` (prevents stale reference bugs).
4. Mark 3 docs as superseded/already-propagated to prevent future redundant propagation work.

## Cross-Cutting Lessons (apply beyond clavain)

8 of 19 docs contain lessons that apply to other modules: Oracle usage, plugin cache behavior, MCP registration, glob patterns in monorepos, LLM compounding provenance, agent registry lifecycle, disable-model-invocation semantics, and mid-session publish breakage.
