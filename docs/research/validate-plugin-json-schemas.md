# Plugin JSON Schema Validation

**Date:** 2026-02-18
**Purpose:** Compare all marketplace plugin.json files against the known-working intercheck plugin to identify schema issues.

## Reference: Known-Working Schema (intercheck 0.1.3)

```json
{
  "name": "intercheck",
  "version": "0.1.3",
  "description": "Code quality guards and session health monitoring",
  "author": {
    "name": "MK"
  },
  "hooks": "./hooks/hooks.json",
  "skills": [
    "./skills/status/SKILL.md"
  ]
}
```

**Required fields** (per Claude Code plugin schema):
- `name` — string
- `version` — string (semver)
- `description` — string

**Known optional fields:**
- `author` — object with `name` (and optionally `email`)
- `hooks` — string path
- `skills` — array of string paths
- `commands` — array of string paths
- `agents` — array of string paths
- `mcpServers` — object
- `license` — string
- `repository` — string
- `keywords` — array of strings

## Per-Plugin Analysis

### interstat 0.2.1 — CLEAN

```json
{
  "name": "interstat",
  "version": "0.2.1",
  "description": "Token efficiency benchmarking for agent workflows",
  "author": { "name": "MK" },
  "hooks": "./hooks/hooks.json",
  "skills": ["./skills/report.md", "./skills/status.md", "./skills/analyze.md"]
}
```

| Check | Result |
|-------|--------|
| `description` present? | Yes |
| `author` present? | Yes |
| Version matches directory? | Yes (0.2.1 = 0.2.1) |
| Extra/unknown fields? | None |
| **Verdict** | **OK** |

---

### intersynth 0.1.1 — 2 ISSUES

```json
{
  "name": "intersynth",
  "version": "0.1.0",
  "description": "Multi-agent synthesis engine — ...",
  "author": { "name": "MK", "email": "mistakeknot@vibeguider.org" },
  "repository": "https://github.com/mistakeknot/intersynth",
  "license": "MIT",
  "keywords": ["synthesis", "multi-agent", "verdict", "context-efficiency", "review"],
  "agents": ["./agents/synthesize-review.md", "./agents/synthesize-research.md"],
  "hooks": "./hooks/hooks.json"
}
```

| Check | Result |
|-------|--------|
| `description` present? | Yes |
| `author` present? | Yes |
| Version matches directory? | **NO — version says 0.1.0 but directory is 0.1.1** |
| Extra/unknown fields? | `repository`, `license`, `keywords` — likely ignored but harmless |
| **Verdict** | **VERSION MISMATCH** — `0.1.0` in plugin.json vs `0.1.1` cache directory |

---

### interserve 0.1.0 — 1 ISSUE

```json
{
  "name": "interserve",
  "version": "0.1.0",
  "description": "Interserve — Codex spark classifier and context compression via MCP",
  "hooks": "./hooks/hooks.json",
  "mcpServers": { ... }
}
```

| Check | Result |
|-------|--------|
| `description` present? | Yes |
| `author` present? | **NO — missing `author` field** |
| Version matches directory? | Yes (0.1.0 = 0.1.0) |
| Extra/unknown fields? | None |
| **Verdict** | **MISSING AUTHOR** |

---

### intermap 0.1.1 — 1 ISSUE

```json
{
  "name": "intermap",
  "version": "0.1.0",
  "description": "Project-level code mapping: ...",
  "author": { "name": "mistakeknot" },
  "license": "MIT",
  "hooks": "./hooks/hooks.json",
  "skills": ["./skills/SKILL.md"],
  "mcpServers": { ... }
}
```

| Check | Result |
|-------|--------|
| `description` present? | Yes |
| `author` present? | Yes |
| Version matches directory? | **NO — version says 0.1.0 but directory is 0.1.1** |
| Extra/unknown fields? | `license` — likely ignored but harmless |
| **Verdict** | **VERSION MISMATCH** — `0.1.0` in plugin.json vs `0.1.1` cache directory |

---

### intermux 0.1.0 — CLEAN

```json
{
  "name": "intermux",
  "version": "0.1.0",
  "description": "Agent activity visibility -- tmux monitoring, ...",
  "author": { "name": "MK" },
  "hooks": "./hooks/hooks.json",
  "skills": ["./skills/status/SKILL.md"],
  "mcpServers": { ... }
}
```

| Check | Result |
|-------|--------|
| `description` present? | Yes |
| `author` present? | Yes |
| Version matches directory? | Yes (0.1.0 = 0.1.0) |
| Extra/unknown fields? | None |
| **Verdict** | **OK** |

---

### interject 0.1.5 — 2 ISSUES

```json
{
  "name": "interject",
  "version": "0.1.2",
  "description": "Ambient discovery and research engine. ...",
  "author": { "name": "MK", "email": "mistakeknot@vibeguider.org" },
  "repository": "https://github.com/mistakeknot/interject",
  "homepage": "https://github.com/mistakeknot/interject#readme",
  "license": "MIT",
  "keywords": ["research", "discovery", ...],
  "skills": [...],
  "commands": [],
  "hooks": "./hooks/hooks.json",
  "mcpServers": { ... }
}
```

| Check | Result |
|-------|--------|
| `description` present? | Yes |
| `author` present? | Yes |
| Version matches directory? | **NO — version says 0.1.2 but directory is 0.1.5** |
| Extra/unknown fields? | `repository`, `homepage`, `license`, `keywords` — likely ignored but harmless |
| Empty `commands` array? | `"commands": []` — technically valid but unusual, could be removed |
| **Verdict** | **VERSION MISMATCH** — `0.1.2` in plugin.json vs `0.1.5` cache directory |

**Note:** The `interject` mcpServers section includes an **exposed API key** (`EXA_API_KEY`) hardcoded in the env. This is a security concern — should use `${EXA_API_KEY}` variable reference instead.

---

### interkasten 0.4.1 — CLEAN

```json
{
  "name": "interkasten",
  "version": "0.4.1",
  "description": "Living bridge between your projects folder and Notion — ...",
  "author": { "name": "mistakeknot", "email": "mistakeknot@vibeguider.org" },
  "repository": "https://github.com/mistakeknot/interkasten",
  "license": "MIT",
  "keywords": ["notion", "sync", ...],
  "mcpServers": { ... },
  "skills": [...],
  "commands": [...],
  "hooks": "./hooks/hooks.json"
}
```

| Check | Result |
|-------|--------|
| `description` present? | Yes |
| `author` present? | Yes |
| Version matches directory? | Yes (0.4.1 = 0.4.1) |
| Extra/unknown fields? | `repository`, `license`, `keywords` — likely ignored but harmless |
| **Verdict** | **OK** |

---

### interfluence 0.2.0 — CLEAN

```json
{
  "name": "interfluence",
  "version": "0.2.0",
  "description": "Analyze your writing style and adapt Claude's output ...",
  "author": { "name": "mistakeknot", "email": "mistakeknot@vibeguider.org" },
  "hooks": "./hooks/hooks.json",
  "mcpServers": { ... }
}
```

| Check | Result |
|-------|--------|
| `description` present? | Yes |
| `author` present? | Yes |
| Version matches directory? | Yes (0.2.0 = 0.2.0) |
| Extra/unknown fields? | None |
| **Verdict** | **OK** |

---

### interflux 0.2.14 — CLEAN

```json
{
  "name": "interflux",
  "version": "0.2.14",
  "description": "Multi-agent review and research with scored triage, ...",
  "author": { "name": "mistakeknot" },
  "license": "MIT",
  "keywords": ["review", "research", ...],
  "skills": [...],
  "commands": [...],
  "agents": [...],
  "mcpServers": { ... }
}
```

| Check | Result |
|-------|--------|
| `description` present? | Yes |
| `author` present? | Yes |
| Version matches directory? | Yes (0.2.14 = 0.2.14) |
| Extra/unknown fields? | `license`, `keywords` — likely ignored but harmless |
| Missing `hooks`? | No `hooks` field — not required, but unusual compared to other plugins |
| **Verdict** | **OK** (no hooks is valid) |

---

### interlens 2.2.3 — CLEAN

```json
{
  "name": "interlens",
  "version": "2.2.3",
  "description": "288 FLUX cognitive lenses for structured thinking — ...",
  "author": { "name": "mistakeknot" },
  "license": "MIT",
  "keywords": ["flux", "lenses", ...],
  "mcpServers": { ... }
}
```

| Check | Result |
|-------|--------|
| `description` present? | Yes |
| `author` present? | Yes |
| Version matches directory? | Yes (2.2.3 = 2.2.3) |
| Extra/unknown fields? | `license`, `keywords` — likely ignored but harmless |
| Missing `hooks`? | No `hooks` field — not required |
| **Verdict** | **OK** |

---

## Summary Table

| Plugin | description | author | Version Match | Extra Fields | Issues |
|--------|:-----------:|:------:|:-------------:|:------------:|--------|
| intercheck 0.1.3 | yes | yes | yes | none | **Reference (clean)** |
| interstat 0.2.1 | yes | yes | yes | none | None |
| intersynth 0.1.1 | yes | yes | **NO (0.1.0)** | repo, license, keywords | Version mismatch |
| interserve 0.1.0 | yes | **NO** | yes | none | Missing author |
| intermap 0.1.1 | yes | yes | **NO (0.1.0)** | license | Version mismatch |
| intermux 0.1.0 | yes | yes | yes | none | None |
| interject 0.1.5 | yes | yes | **NO (0.1.2)** | repo, homepage, license, keywords | Version mismatch + hardcoded API key |
| interkasten 0.4.1 | yes | yes | yes | repo, license, keywords | None |
| interfluence 0.2.0 | yes | yes | yes | none | None |
| interflux 0.2.14 | yes | yes | yes | license, keywords | None |
| interlens 2.2.3 | yes | yes | yes | license, keywords | None |

## Key Findings

### 1. Version Mismatches (3 plugins)

The most common issue: the `version` field in plugin.json does not match the cache directory version. This means the marketplace index (which determines the directory name) has been bumped but the plugin.json inside was never updated.

| Plugin | plugin.json version | Cache directory version | Delta |
|--------|--------------------:|------------------------:|-------|
| intersynth | 0.1.0 | 0.1.1 | +0.0.1 |
| intermap | 0.1.0 | 0.1.1 | +0.0.1 |
| interject | 0.1.2 | 0.1.5 | +0.0.3 |

**Root cause:** The `interbump` script (or manual version bumping) updates the marketplace index and possibly the repo tag, but does not update the `version` field inside `plugin.json` itself. Or the plugin was re-published with a new marketplace version without rebuilding/updating the plugin source.

**Impact:** Unclear — Claude Code may use the marketplace index version (directory name) for display, or may use the plugin.json version internally. If it uses plugin.json, the user sees a stale version. If there is a version consistency check, it could cause silent failures.

### 2. Missing Author (1 plugin)

**interserve** is the only plugin missing the `author` field entirely. All other plugins have it. While `author` may not be strictly required by the runtime schema, it is a best practice and present in every other plugin.

### 3. Hardcoded API Key (1 plugin)

**interject** has `"EXA_API_KEY": "eba9629f-75e9-467c-8912-a86b3ea8d678"` hardcoded directly in the mcpServers env. Compare with interflux which correctly uses `"EXA_API_KEY": "${EXA_API_KEY}"` (environment variable reference). This is a security issue — the key is exposed in the plugin cache, git history, and marketplace distribution.

### 4. Extra Fields (Harmless)

Several plugins include npm-style metadata fields (`repository`, `homepage`, `license`, `keywords`) that are not part of the Claude Code plugin schema. These are almost certainly ignored by the runtime and cause no issues, but they add noise. Six plugins have at least one of these.

### 5. No Structural Schema Violations

All plugins have valid JSON, correct field types, and proper structure for their mcpServers, skills, commands, agents, and hooks references. No plugin is missing the core required fields (`name`, `version`, `description`).

## Recommended Fixes

### Priority 1: Version Mismatches
Update `plugin.json` version fields in the source repos for intersynth, intermap, and interject to match their current marketplace versions. Then republish.

Alternatively, ensure `interbump` updates the `version` field in `plugin.json` as part of its bump workflow.

### Priority 2: Hardcoded API Key
Replace the hardcoded EXA_API_KEY in interject's plugin.json with `"${EXA_API_KEY}"` and republish. Rotate the exposed key.

### Priority 3: Missing Author
Add `"author": { "name": "MK" }` to interserve's plugin.json.

### Priority 4: Clean Up Extra Fields (Optional)
Remove `repository`, `homepage`, `license`, and `keywords` from plugin.json files if they are not used by the Claude Code runtime. This is cosmetic only.
