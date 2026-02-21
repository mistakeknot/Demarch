# Module Highlight: interkasten

## Analysis

### Purpose & Core Value
interkasten is the bidirectional sync bridge between local project filesystems and Notion databases. It enables living documentation that stays synchronized across both mediums without requiring manual coordination. The module exposes 21 MCP tools covering project discovery, bidirectional sync orchestration, conflict resolution, and filesystem signal gathering — making it a comprehensive documentation infrastructure service.

### Key Technical Strengths

1. **Bidirectional Sync with Conflict Resolution**
   - Push (local → Notion) and pull (Notion → local) with 60-second polling
   - Three-way merge via `node-diff3` when both sides change the same document
   - Configurable conflict strategies (three-way-merge, local-wins, notion-wins, conflict-file)
   - Crash-safe WAL protocol: pending → target_written → committed → delete

2. **Agent-Native Architecture**
   - Tools expose raw filesystem signals (LOC, commit history, markers, file listings) rather than hardcoded decisions
   - No hardcoded classification, tagging, or cascade logic — agent intelligence drives all domain decisions
   - CRUD operations remain minimal and transparent, delegating composition to Claude Code skills

3. **Operational Safety**
   - Circuit breaker pattern prevents cascading Notion API failures
   - Content hashing (SHA-256) enables change detection and base deduplication
   - Soft-delete with 30-day retention aligned with Notion's trash policy
   - Path validation on all pull operations to prevent traversal attacks

4. **Cross-System Integration**
   - Beads issue sync: diff-based tracking of beads state pushed to Notion Issues database
   - Hierarchy support: `.beads` marker defines parent-child relationships, transparent traversal
   - Key doc tracking: URL columns in Notion Projects database for Vision, PRD, Roadmap, AGENTS.md, CLAUDE.md

### Development Maturity
- **Testing**: 130 tests (121 unit + 9 integration via @notionhq/client v5)
- **Tools**: 21 MCP tools organized by function (infrastructure, project management, hierarchy, sync, legacy)
- **Skills**: 3 interactive skills (layout discovery, onboarding, self-diagnosis)
- **Hooks**: 2 automated hooks (SessionStart status, Stop warning)
- **Open beads**: 12 (primarily P2 enhancements: webhook receiver, interphase integration, performance optimization)

## Module Highlight (Output Format)

### interkasten (plugins/interkasten)
v0.4.3. Bidirectional sync between local filesystems and Notion with three-way merge conflict resolution and crash-safe WAL recovery. Exposes 21 MCP tools for hierarchy discovery, raw signal gathering, and sync control — delegating classification and tagging to agent skills rather than hardcoding behavior.
