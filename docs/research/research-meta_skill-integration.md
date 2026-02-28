# Assessment: meta_skill (ms)

**Date:** 2026-02-28
**Bead ID:** iv-7d0ax
**Source:** https://github.com/Dicklesworthstone/meta_skill
**Task:** Evaluate integration/inspiration value for Demarch (os/clavain, interverse/interdoc, sdk/interbase)

---

## What it is

A local-first Rust CLI skill management platform that turns operational knowledge into structured, searchable, reusable `SKILL.md` artifacts. Provides dual persistence (SQLite + Git), hybrid search (BM25 + hash embeddings fused via RRF), adaptive suggestion ranking via Thompson sampling + UCB bandit, multi-layer security (ACIP prompt-injection defense + DCG command safety), and a native MCP server (12 tools) for AI agent integration. Skills can be hand-written, mined from CASS session transcripts, imported as bundles, or synced across machines via Git remotes.

**Language/Stack:** Rust (edition 2024, 1.85+), rusqlite (bundled SQLite), Tantivy (BM25), git2 (vendored OpenSSL), rayon (parallel indexing), ratatui (TUI), Cobra-style CLI. Single binary with aggressive LTO optimization.

**Quality:** high

- 12 SQL migrations with `PRAGMA user_version` tracking
- `unsafe_code = "deny"` at crate level
- `clippy::pedantic` + `clippy::nursery` enabled
- Tests: unit, integration, e2e, property (proptest), snapshot (insta), benchmarks (criterion)
- Principled MCP output safety: state-machine ANSI stripping + multi-layer JSON validation
- ~50 CLI subcommands, all with JSON robot mode
- Single-author, no external contributions accepted (velocity bounded)

---

## Architecture

| Module | Role |
|---|---|
| `core/` | `SkillSpec`, `SkillMetadata`, sections/blocks, layering, resolution, packing, progressive disclosure |
| `search/` | `HashEmbedder` (FNV-1a 384d), `VectorIndex` (in-memory HashMap), `Bm25Index` (Tantivy), RRF fusion, LRU cache |
| `storage/` | `Database` (rusqlite), `GitArchive` (git2), 12 inline SQL migrations |
| `suggestions/` | `SignalBandit` (Thompson + UCB), 8 signal arms, exponential decay, context modifiers |
| `security/` | ACIP (prompt injection defense), DCG (command safety), path policy, secret scanner |
| `cli/commands/mcp.rs` | MCP server (1940 lines), 12 tools, JSON-RPC 2.0 over stdio/TCP |
| `cass/` | Session mining pipeline: extraction → synthesis → quality → uncertainty → refinement |
| `bundler/` | Portable `.msb` skill packages with checksums |
| `sync/` | Git-based multi-machine sync with conflict resolution |
| `context/` | `ProjectDetector` — identifies 18 project types from marker files |

**Skill data model:**
```
SkillSpec
  ├── metadata: id, name, version, tags, requires[], provides[], context (project_types, file_patterns, tools, signals)
  ├── sections → blocks (Text | Code | Rule | Pitfall | Command | Checklist)
  ├── extends: Option<String>     -- single inheritance
  ├── includes: Vec<SkillInclude> -- composition (prepend/append)
  └── 4 layers: Base < Org < Project < User (higher wins, configurable conflict strategy)
```

---

## Core Patterns

### 1. Hybrid Search: BM25 + Hash Embeddings + RRF

Three-tier retrieval:
- **BM25** via SQLite FTS5 / Tantivy — lexical matching
- **Hash embeddings** — FNV-1a hash projected into 384 dimensions with bigram smoothing, cosine similarity (brute-force, O(n))
- **RRF fusion** (k=60.0, equal weights) — rank-based fusion that's stable across different score scales

**Hash embedding algorithm:** tokenize → for each unigram, FNV-1a hash → project into 384 dims via `fnv1a_hash_with_salt(token_hash, dim_i)`, map to `[-1,1]`, accumulate (bigrams at 0.5 weight) → L2-normalize. This is a deterministic, dependency-free alternative to neural embeddings. Semantically shallow (bag-of-words with hash projection) but works well for technical vocabulary.

**Design tradeoff:** In-memory VectorIndex (HashMap) with no ANN — intentionally simple for hundreds to low-thousands of skills where brute-force beats HNSW overhead. Does not persist between processes.

### 2. Adaptive Suggestions via Bandit

`SignalBandit` with 8 arms: `Bm25`, `Embedding`, `Trigger`, `Freshness`, `ProjectMatch`, `FileTypeMatch`, `CommandPattern`, `UserHistory`.

Each arm: `Beta(prior.alpha + successes, prior.beta + failures)` with Thompson sampling + UCB bonus. Key feature: **exponential decay** (`successes *= 0.99` on each observation) prevents early-session bias from permanently skewing weights. Context modifiers per `(ContextKey, SignalType)` enable learned per-project preferences.

### 3. Progressive Disclosure + Pack Contracts

Five `DisclosureLevel`s: Minimal (~100 tokens), Overview (~500), Standard (~1500), Full (unbounded), Complete (full + scripts + refs), Auto.

**`ConstrainedPacker`** selects optimal subset of `SkillSlice`s within a token budget, respecting coverage quotas, mandatory slices, and novelty penalties. **Pack contracts** are named, persisted packing rules (`debug`, `refactor`, `codegen`) — reusable across sessions.

### 4. MCP Server (12 Tools)

Full JSON-RPC 2.0: `search`, `load`, `evidence`, `list`, `show`, `doctor`, `lint`, `suggest`, `feedback`, `index`, `validate`, `config`. ANSI safety is first-class — state-machine CSI/OSC escape stripper with post-serialization JSON validation. Runs as long-lived stdio loop or TCP.

### 5. Security Model

**ACIP (Agent Content Injection Prevention):** Trust hierarchy `User > Assistant > ToolOutput > File`. Static regex detection for injection keywords + sensitive patterns. Quarantine with audit trail, replay requires explicit flag.

**DCG integration:** 4-tier command safety classification built-in (SAFE/CAUTION/DANGER/CRITICAL). Critical commands require verbatim approval via env var.

### 6. CASS Mining Pipeline

Extract skills from Claude session transcripts: segment by phase → extract typed patterns (CommandRecipe, DiagnosticDecisionTree, Invariant, Pitfall, PromptMacro) → uncertainty quantification → synthesis → refinement. Sub-threshold patterns go to `uncertainty_queue` for future mining rounds.

---

## Overlap with Clavain's Skill System

| Dimension | meta_skill (`ms`) | Clavain (Interverse) |
|---|---|---|
| **Skill format** | `SKILL.md` with structured YAML frontmatter + typed sections/blocks | `SKILL.md` with simpler YAML frontmatter |
| **Discovery** | Config-driven path scanning + `ms index` | Plugin directory convention (`interverse/*/SKILL.md`) |
| **Search** | BM25 + hash embedding + RRF | None — skills injected by name/slug |
| **Suggestion** | Bandit-based adaptive recommendation | Hooks-based automatic injection |
| **Lifecycle** | Full CRUD + validation + lint + migrate + prune | Create via template, publish via `ic publish` |
| **Persistence** | SQLite + Git archive | Git only (skills are files) |
| **Token management** | Progressive disclosure levels + constrained packing | SKILL-compact.md pattern (manual) |
| **Inheritance** | `extends` + `includes` (multi-layer) | None |
| **Effectiveness tracking** | Feedback, outcomes, experiments, bandit | None |
| **Scale** | Hundreds to thousands | Dozens per plugin |

**Fundamental architectural difference:** Clavain treats skills as static markdown injected whole, selected by human/agent intent. `ms` treats skills as managed artifacts in a queryable system with learned relevance. These are complementary — `ms` would be a backing store, Clavain provides session-level enforcement.

---

## Integration Opportunities

### A. Inspire: Hash embedding + RRF for intersearch

intersearch currently uses Ollama embeddings (faiss backend) or ColBERT. The hash embedding approach (FNV-1a projected into 384d, zero dependencies, fully deterministic) is a compelling lightweight alternative for the faiss backend — especially when Ollama isn't available. RRF fusion is already well-understood; the contribution is the hash embedding algorithm itself.

**Effort:** medium — implement `HashEmbedder` in intersearch as a third backend option

### B. Inspire: Pack contracts for SKILL-compact.md automation

Clavain's SKILL-compact.md pattern is manual (author writes a condensed version). `ms`'s pack contracts formalize this: define packing rules (budget, mandatory sections, coverage quotas), and the packer selects the optimal subset. This could automate compact generation.

**Effort:** medium — would require a packer that understands SKILL.md structure

### C. Inspire: Bandit-based signal weighting for interwatch

interwatch uses fixed signal weights defined in `watchables.yaml`. The bandit pattern (8 arms, Thompson + UCB, exponential decay) could adaptively learn which signals are actually predictive of real drift vs noise. Over time, signal weights would self-tune per project.

**Effort:** high — requires feedback signal (did the refresh actually help?), which interwatch doesn't currently capture

### D. Inspire: ANSI-safe MCP output pattern

The state-machine ANSI stripper + post-serialization JSON validator is production-grade. Any Demarch MCP server that might receive rich terminal output (tldr-swinton, intermap) should adopt this pattern to prevent ANSI bleeding into JSON-RPC responses.

**Effort:** low — port the sanitizer as a library function

### E. Inspire: Progressive disclosure levels for skill injection

Instead of binary "inject full SKILL.md or SKILL-compact.md", offer graduated levels (Minimal/Overview/Standard/Full) based on context (how much budget remains, how relevant the skill is to the current task). This is a token optimization that compounds across sessions.

**Effort:** medium — requires token counting + skill sectioning in the injection path

### F. Skip: Uncertainty queue from CASS mining

The uncertainty queue pattern (sub-threshold patterns deferred to future mining) is elegant but requires a CASS-like session store that Demarch doesn't have. The compound docs system (`/compound`) is the closest analog but stores solutions, not raw session transcripts.

---

## Skip Opportunities

- **Full `ms` deployment as a tool.** The binary is heavyweight (vendored OpenSSL, Tantivy, ratatui) and solves a problem Clavain doesn't yet have (managing thousands of skills). Demarch has ~50 skills across all plugins — well within the "just use files" regime.

- **SQLite + Git dual persistence.** Over-engineered for Demarch's scale. Git-only persistence is sufficient for dozens of skills.

- **ACIP security model.** Demarch has its own trust boundary model (documented in the security threat model brainstorm). Adopting ACIP's taxonomy would create a competing model.

- **Skill inheritance/composition.** Clavain skills are self-contained markdown files that work well without inheritance. Adding `extends`/`includes` semantics would add complexity without clear benefit at current scale.

- **Bundler / sync.** Demarch uses the plugin marketplace (interagency-marketplace) for skill distribution. A separate `.msb` bundle format would fragment the distribution story.

---

## Verdict: inspire-only

**Rationale:** meta_skill is an impressive system — arguably the most sophisticated skill management platform in the open-source Claude Code ecosystem. Its patterns (hash embeddings, bandit weighting, pack contracts, progressive disclosure, ANSI-safe MCP output) are genuinely novel and well-implemented. However, it solves a scale problem Demarch doesn't have yet (managing hundreds-to-thousands of skills) and its architecture is fundamentally different from Clavain's (queryable database vs. file-based plugin convention).

The right approach is to extract patterns as they become needed:
- **Now:** ANSI-safe MCP output (low effort, high value for any MCP server)
- **Soon:** Hash embeddings as a lightweight intersearch backend (medium effort, fills a real gap when Ollama isn't available)
- **Later:** Progressive disclosure levels and pack contracts when SKILL-compact.md automation becomes a priority
- **Maybe:** Bandit-based signal weighting when interwatch has a feedback loop

Per MEMORY.md guidance: inspiration and pattern extraction, not replication of a well-maintained external project.

---

## Follow-Up Beads

1. **Port ANSI-safe MCP output sanitizer to Demarch MCP servers** — prevent ANSI bleeding in tldr-swinton, intermap JSON-RPC responses (P3, effort: low)
2. **Add hash embedding backend to intersearch** — FNV-1a 384d deterministic embeddings as zero-dependency alternative to Ollama (P3, effort: medium)
3. **Investigate progressive disclosure levels for Clavain skill injection** — graduated token budgets instead of binary full/compact (P4, effort: medium)
