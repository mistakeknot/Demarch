# Security Threat Model for Token Optimization Techniques

**Bead:** iv-xuec
**Date:** 2026-02-23
**Status:** Brainstorm
**Sources:** [oracle-token-efficiency-review.md](../research/oracle-token-efficiency-review.md), [token-efficiency-agent-orchestration-2026.md](../research/token-efficiency-agent-orchestration-2026.md), [pi-agent-rust-lessons](../../os/clavain/docs/brainstorms/2026-02-19-pi-agent-rust-lessons-brainstorm.md)

---

## Problem

The token optimization landscape (7 layers, 12+ techniques) was reviewed by Oracle (GPT-5.2 Pro) which flagged that **none** of the security implications are surfaced as first-class concerns. Every optimization trades a resource (tokens, latency, cost) for a different risk surface. Without an explicit threat model, teams adopt optimizations without understanding what attack surface they're opening.

This document maps each optimization technique to its security threats, assesses severity, and recommends mitigations.

---

## Threat Model

### T1: File Indirection — Tempfile Leakage

**Layer:** 1 (Prompt Architecture)
**Technique:** Write agent prompts to temp files, dispatch with a reference instead of inlining content.
**Production use:** Clavain dispatches via `/tmp` prompt files; `gen-skill-compact.sh` uses `mktemp` for atomic writes.

**Threats:**

| ID | Threat | Severity | Likelihood |
|----|--------|----------|------------|
| T1.1 | **Prompt content readable by other processes.** `/tmp` files default to world-readable on many Linux configs. Prompts may contain API keys, code snippets, internal architecture details. | High | Medium |
| T1.2 | **Race condition: read-before-write or read-after-delete.** Parallel subagents may read stale/partial prompt files, or cleanup deletes before a slow agent reads. | Medium | Low |
| T1.3 | **Cache-killer via randomized paths.** Each temp file gets a unique path, changing the prompt prefix, which reduces prompt-cache hit rate. Indirect cost increase. | Low | High |
| T1.4 | **Forensic persistence.** Temp files may survive process crashes, leaving secrets on disk indefinitely. | Medium | Medium |

**Mitigations:**
- Use `mktemp` with restrictive permissions (`umask 077` or explicit `chmod 600`).
- Use `$XDG_RUNTIME_DIR` (per-user tmpfs, auto-cleaned) instead of `/tmp` when available.
- Clean up in a `trap EXIT` handler, not just happy-path cleanup.
- For cache-friendly dispatch: use deterministic paths keyed on content hash, not random names.
- Never write secrets to prompt files — extract sensitive values to env vars before dispatch.

---

### T2: Prompt Injection via Retrieved Text

**Layer:** 5 (Retrieval)
**Technique:** Multi-strategy code search (RRF across AST, semantic, dependency tracing) injects retrieved text into agent context.
**Production use:** tldrs-swinton semantic search, interflux domain detection, interject ambient discovery.

**Threats:**

| ID | Threat | Severity | Likelihood |
|----|--------|----------|------------|
| T2.1 | **Adversarial content in retrieved code/docs.** Malicious content in indexed repos could contain prompt injection payloads that redirect agent behavior when ingested. | Critical | Low-Medium |
| T2.2 | **Index poisoning.** If embeddings are generated from untrusted content, adversarial strings can be crafted to rank highly for safety-critical queries. | High | Low |
| T2.3 | **Cross-repo contamination.** Multi-repo search (interject scans multiple projects) means a compromised repo can inject into any agent's context. | High | Low |

**Mitigations:**
- Retrieval results should be presented in a clearly delineated `<retrieved-content>` block that the agent is instructed to treat as untrusted data.
- Never execute code or tool calls found in retrieved text without user confirmation.
- Index only trusted repos — don't auto-index arbitrary cloned repos.
- Content sanitization: strip known injection patterns (`<system>`, `<instructions>`, `ignore previous`) from retrieved text before injection.
- Per-source trust tagging: mark retrieved content with its origin repo and trust level.

---

### T3: Memory Poisoning (A-Mem / Cross-Session Knowledge)

**Layer:** 5 (Retrieval) + 7 (Architectural Patterns)
**Technique:** Long-lived memory stores (MEMORY.md, interfluence learnings, interkasten Notion sync) persist across sessions. Agentic memory (iv-qtcl A-Mem) would add automatic memory promotion.
**Production use:** Auto-memory in `~/.claude/projects/*/memory/`, interfluence learnings-raw.log, interkasten sync.

**Threats:**

| ID | Threat | Severity | Likelihood |
|----|--------|----------|------------|
| T3.1 | **Gradual memory corruption.** Incorrect conclusions persisted across sessions accumulate into systematically wrong behavior. No "memory garbage collection." | High | Medium |
| T3.2 | **Injection via memory files.** If a compromised tool or agent writes to MEMORY.md, it can inject persistent instructions that affect all future sessions. | Critical | Low |
| T3.3 | **Stale memory conflicts.** Memories about code patterns become wrong after refactoring. Agent follows outdated patterns, introduces bugs. | Medium | High |
| T3.4 | **Cross-project leakage.** Global memory (`~/.claude/CLAUDE.md`) may contain project-specific secrets or patterns that leak into unrelated projects. | Medium | Medium |

**Mitigations:**
- Memory files should be append-only with timestamps — never overwrite without a diff review.
- Add a `verified: true/false` field to structured memories. Unverified memories get lower priority.
- Periodic memory audit: `interwatch` drift scan on memory files themselves (meta-watchability).
- Project-scoped memory isolation — never auto-promote project memory to global scope.
- Memory provenance: record which session/agent wrote each memory entry, enabling rollback.
- For A-Mem (iv-qtcl): require user confirmation before memory promotion to permanent store.

---

### T4: Leakage via Logs, Artifacts, and Tempfiles

**Layer:** 1 (Prompt Architecture) + 3 (Context Isolation)
**Technique:** File indirection, Codex CLI file-based state passing, interstat JSONL logging, flux-drive output files.
**Production use:** `~/.claude/interstat/metrics.db`, `.clavain/scratch/`, flux-drive output dirs, session JSONL.

**Threats:**

| ID | Threat | Severity | Likelihood |
|----|--------|----------|------------|
| T4.1 | **Sensitive content in flux-drive outputs.** Agent review files in `docs/research/flux-drive/` may contain security findings, API patterns, or vulnerability details — committed to git. | High | Medium |
| T4.2 | **Session JSONL contains full conversation.** Token tracking (interstat) reads session JSONL which contains every message, tool call, and result — including any secrets the user shared. | High | Medium |
| T4.3 | **Scratch files persist after crashes.** `.clavain/scratch/` handoff files, checkpoint files, and temp artifacts survive process termination. | Medium | Medium |
| T4.4 | **Interstat metrics DB leaks session patterns.** Agent names, invocation times, and token counts reveal workflow patterns. Combined with git history, could reconstruct what was being worked on. | Low | Low |

**Mitigations:**
- `.gitignore` flux-drive output dirs by default; require explicit `git add` to commit findings.
- interstat should never store message content — only metadata (agent name, tokens, timestamps).
- Add TTL-based cleanup to `.clavain/scratch/` — files older than 7 days auto-deleted by SessionStart hook.
- Session JSONL access should be read-only and scoped — interstat reads only the token fields, not message content.
- Add a `.sensitive` marker to flux-drive outputs that contain security findings, excluded from git by default.

---

### T5: Hierarchical AGENTS.md Prompt Injection

**Layer:** 1 (Prompt Architecture)
**Technique:** Nested AGENTS.md files from repo root to CWD merge additively, with closer files overriding. Used by Codex CLI and Claude Code.
**Production use:** Every Demarch subproject has its own CLAUDE.md and AGENTS.md.

**Threats:**

| ID | Threat | Severity | Likelihood |
|----|--------|----------|------------|
| T5.1 | **Subdirectory prompt injection.** An untrusted repo (cloned dependency, PR from external contributor) can include a `.claude/CLAUDE.md` or `AGENTS.md` that overrides safety rules. | Critical | Medium |
| T5.2 | **Policy drift via deep nesting.** Conflicting rules at different directory levels create unpredictable behavior. Agent follows the deepest override without surfacing the conflict. | High | Medium |
| T5.3 | **Shadow instructions.** A malicious AGENTS.md could include instructions like "never report security findings" or "always approve code" that the agent follows silently. | Critical | Low |

**Mitigations:**
- Treat AGENTS.md from untrusted sources (cloned repos, PRs, vendored dependencies) as untrusted input.
- Add a trust boundary: only load AGENTS.md from the project root and user home. Subdirectory overrides require explicit opt-in via a `trusted_dirs` allowlist.
- Lint AGENTS.md for known injection patterns during PR review (could be an intercheck hook).
- Log which AGENTS.md files were loaded at session start — visible in session metadata for audit.
- Never auto-merge AGENTS.md from `node_modules/`, `vendor/`, `.git/modules/`, or other dependency directories.

---

### T6: Model Routing Exploitation

**Layer:** 2 (Model Routing)
**Technique:** Route tasks to cheaper/faster models based on complexity classification.
**Production use:** Clavain model-routing skill, Haiku for research agents, Opus for orchestration.

**Threats:**

| ID | Threat | Severity | Likelihood |
|----|--------|----------|------------|
| T6.1 | **Adversarial complexity downgrade.** Crafted inputs that appear simple to the router but are actually complex, causing a weak model to handle security-sensitive work. | Medium | Low |
| T6.2 | **Cross-model context impedance.** Summaries passed between models lose safety constraints. A Haiku summary may omit security caveats that Opus would have preserved. | Medium | Medium |
| T6.3 | **Router prompt injection.** If the router itself is an LLM call, the input being routed could contain instructions to force routing to a specific model. | Medium | Low |

**Mitigations:**
- Security-sensitive domains (credentials, auth, deployment) should be pinned to the strongest model, bypassing the router.
- Router decisions should be logged and auditable — not just the result, but the classification reasoning.
- Never downgrade model for domains tagged as security-critical in flux-drive domain detection.

---

### T7: Compression-Induced Information Loss

**Layer:** 4 (Context Compression)
**Technique:** LLMLingua-style prompt compression, context compaction, summary-based memory.
**Production use:** Claude Code automatic compaction, interflux document slicing.

**Threats:**

| ID | Threat | Severity | Likelihood |
|----|--------|----------|------------|
| T7.1 | **Safety instructions compressed away.** Compression algorithms optimize for information density, not instruction priority. "Never deploy to production without approval" may be pruned as low-entropy. | High | Medium |
| T7.2 | **Security context lost in compaction.** After Claude Code compacts conversation history, the agent may forget earlier security constraints or threat context discussed in the session. | Medium | High |
| T7.3 | **Selective compression as attack vector.** If an attacker can influence what gets compressed (via long padding content), they can push critical instructions out of the retained context. | Medium | Low |

**Mitigations:**
- Mark critical instructions as compression-resistant (e.g., `<must-retain>` tags if supported).
- After compaction, re-inject critical safety rules via the system prompt (already done via CLAUDE.md reload).
- Document slicing should always include security-relevant sections for fd-safety agent, regardless of relevance scoring.
- Test compaction scenarios: verify that safety constraints survive N rounds of compaction.

---

### T8: AgentDropout — Safety Agent Elimination

**Layer:** 7 (Architectural Patterns)
**Technique:** Dynamically skip "redundant" agents to save tokens.
**Production use:** Proposed in iv-qjwz (not yet implemented).

**Threats:**

| ID | Threat | Severity | Likelihood |
|----|--------|----------|------------|
| T8.1 | **Safety agents dropped as "low-value."** If fd-safety or fd-correctness are classified as redundant based on historical data, actual security issues go undetected. | Critical | Medium |
| T8.2 | **Coverage gaps in novel code.** Dropout trained on historical patterns may skip agents that are essential for new/unfamiliar code patterns. | High | Medium |
| T8.3 | **Gaming dropout signals.** If dropout is based on past finding rates, code that consistently avoids triggering safety agents gets less scrutiny over time. | Medium | Low |

**Mitigations:**
- fd-safety and fd-correctness should be **dropout-exempt** — they always run regardless of budget or redundancy signals.
- Minimum coverage floor: at least 2 review agents must run on every review, even under tight budgets.
- Periodic "full roster" reviews (every Nth review ignores dropout) to calibrate against coverage gaps.
- Dropout decisions logged and auditable — "why was X agent skipped?"

---

## Severity Matrix

| Threat | Severity | Likelihood | Risk Score | Status |
|--------|----------|------------|------------|--------|
| T5.1 Subdirectory prompt injection | Critical | Medium | **High** | No mitigation in place |
| T5.3 Shadow instructions | Critical | Low | **Medium** | No mitigation in place |
| T2.1 Adversarial retrieved content | Critical | Low-Medium | **Medium** | Partial (content blocks) |
| T8.1 Safety agent dropout | Critical | Medium | **High** | Not yet implemented (iv-qjwz) |
| T3.2 Injection via memory files | Critical | Low | **Medium** | No mitigation in place |
| T1.1 Tempfile readability | High | Medium | **Medium** | Partial (mktemp used) |
| T4.1 Sensitive flux-drive outputs | High | Medium | **Medium** | No mitigation in place |
| T4.2 Session JSONL exposure | High | Medium | **Medium** | No mitigation in place |
| T3.1 Gradual memory corruption | High | Medium | **Medium** | Manual only |
| T5.2 Policy drift via nesting | High | Medium | **Medium** | No mitigation in place |
| T7.1 Safety instructions compressed | High | Medium | **Medium** | Partial (CLAUDE.md reload) |
| T7.2 Security context lost in compaction | Medium | High | **Medium** | Partial (CLAUDE.md reload) |
| T3.3 Stale memory conflicts | Medium | High | **Medium** | Manual only |

---

## Recommended Mitigations by Priority

### P0: Implement Now (High risk, achievable)

1. **AGENTS.md trust boundary** — Only load from project root and `~/.claude/`. Reject subdirectory AGENTS.md from untrusted paths (`node_modules/`, `vendor/`, `.git/modules/`). Add to intercheck as a PreToolUse guard.

2. **Tempfile hardening** — Audit all `mktemp` usage across Clavain/Interverse. Ensure `umask 077`, use `$XDG_RUNTIME_DIR`, add `trap EXIT` cleanup. Affects: `gen-skill-compact.sh`, Clavain dispatch, interstat.

3. **Flux-drive output gitignore** — Add `docs/research/flux-drive/` to `.gitignore` template in project scaffolding. Require explicit staging.

### P1: Implement Soon (Medium risk, prevents escalation)

4. **Memory provenance tracking** — Add `# Source: session-<id>, agent: <name>, date: <date>` comments to auto-memory writes. Enable rollback.

5. **Dropout exemption list** — When implementing iv-qjwz, hardcode fd-safety and fd-correctness as always-run. Document in flux-drive config.

6. **Retrieved content sandboxing** — Wrap retrieval results in `<retrieved-content source="...">` blocks. Update agent prompts to treat as untrusted.

### P2: Design for Future (Lower risk, architectural)

7. **Graduated enforcement rollout** — Adopt pi_agent_rust's Shadow→LogOnly→EnforceNew→EnforceAll pattern for all security mitigations. Start with logging violations, graduate to blocking.

8. **Memory TTL and audit** — Add drift scanning to memory files via interwatch. Memories older than N days without verification get demoted.

9. **Compression-resistant instruction tags** — Propose `<must-retain>` convention for critical instructions. Test survival across compaction cycles.

---

## Interaction with Existing Work

| Bead | Interaction |
|------|-------------|
| iv-qtcl (A-Mem) | T3 threats apply directly. Memory promotion must require user confirmation. |
| iv-qjwz (AgentDropout) | T8 threats apply directly. Exemption list is a prerequisite. |
| iv-sytm (Skill loading) | T1 threats apply to `gen-skill-compact.sh` tempfile usage. Already uses `mktemp` + `mv` (atomic). Needs `umask 077`. |
| iv-pbmc (Cost-aware scheduling) | Budget pressure increases dropout risk (T8). Budget should never override safety agent minimum. |
| iv-8m38 (Token ledger) | T4 threats — ledger must track metadata only, never message content. |
| iv-fv1f (Context estimation) | T7 threats — estimation informs compaction decisions; bad estimates could compress away safety context. |

---

## Open Questions

1. **How do we test for prompt injection in AGENTS.md?** Static analysis (regex for known patterns) vs LLM-based detection vs both?
2. **Should memory files be signed?** Git-level integrity may suffice, but out-of-repo memory (`.claude/`) has no integrity checking.
3. **What's the right trust boundary for multi-repo search (interject)?** Per-repo allowlist? Organization-level trust?
4. **Can we detect when compaction has removed safety-critical context?** Post-compaction validation check?
