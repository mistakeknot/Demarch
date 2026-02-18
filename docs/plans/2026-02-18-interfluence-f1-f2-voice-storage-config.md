# interfluence F1+F2: Voice-Aware Profile Storage & Config Schema Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use clavain:executing-plans to implement this plan task-by-task.

**Goal:** Extend interfluence MCP server with voice-aware profile storage (F1) and config schema with voice resolution (F2) — the two foundational features that unblock all other code-switching features.

**Architecture:** Add an optional `voice` parameter to `profile_get`/`profile_save`, a new `profile_list` tool, and a `voices` array to `config.yaml` with a `resolveVoice(filePath, voices)` function using `minimatch` for glob pattern matching. Filesystem (`voices/` directory) is source of truth for voice existence; config is routing only.

**Tech Stack:** TypeScript, `@modelcontextprotocol/sdk`, `js-yaml`, `minimatch` (new dependency), esbuild

**PRD:** `docs/prds/2026-02-18-interfluence-code-switching.md` (F1, F2)
**Beads:** `iv-ashj` (F1), `iv-r5bm` (F2)

---

## Task 1: Add `minimatch` Dependency

**Files:**
- Modify: `plugins/interfluence/server/package.json`

**Step 1: Install minimatch**

Run:
```bash
cd /root/projects/Interverse/plugins/interfluence/server && npm install minimatch --save --cache /tmp/npm-cache
```

**Step 2: Install @types/minimatch**

Run:
```bash
cd /root/projects/Interverse/plugins/interfluence/server && npm install @types/minimatch --save-dev --cache /tmp/npm-cache
```

**Step 3: Verify**

Run:
```bash
cd /root/projects/Interverse/plugins/interfluence/server && node -e "const {minimatch} = require('minimatch'); console.log(minimatch('posts/hello.md', 'posts/**'))"
```
Expected: `true`

**Step 4: Commit**

```bash
cd /root/projects/Interverse/plugins/interfluence && git add server/package.json server/package-lock.json
git commit -m "chore(interfluence): add minimatch for voice glob resolution"
```

---

## Task 2: Extend `utils/paths.ts` with Voice Path Resolver

**Files:**
- Modify: `plugins/interfluence/server/src/utils/paths.ts:28-29`

**Step 1: Write the voice name validator and voice path resolver**

Add these two functions to `utils/paths.ts`, replacing the existing `getVoiceProfilePath` (line 28-30):

```typescript
const VOICE_NAME_RE = /^[a-z0-9][a-z0-9-]{0,30}[a-z0-9]$/;

export function isValidVoiceName(name: string): boolean {
  return VOICE_NAME_RE.test(name);
}

export function getVoicesDir(projectDir: string): string {
  const dir = join(getinterfluenceDir(projectDir), "voices");
  return dir;
}

export function getVoiceProfilePath(projectDir: string, voice?: string): string {
  if (!voice || voice === "base") {
    return join(getinterfluenceDir(projectDir), "voice-profile.md");
  }
  return join(getinterfluenceDir(projectDir), "voices", `${voice}.md`);
}
```

Key design points:
- `getVoiceProfilePath(projectDir)` still returns `voice-profile.md` — backward compatible
- `getVoiceProfilePath(projectDir, "blog")` returns `voices/blog.md`
- `getVoiceProfilePath(projectDir, "base")` returns `voice-profile.md` (explicit base)
- `getVoicesDir` does NOT auto-create the directory (created lazily on first save)
- `isValidVoiceName` enforces alphanumeric + hyphens, 2-32 chars

**Step 2: Add import for `readdirSync` at top of file**

Add `readdirSync` to the existing `fs` import:

```typescript
import { existsSync, mkdirSync, readdirSync } from "fs";
```

**Step 3: Add `listVoices` helper**

Add to `paths.ts` after the other exports:

```typescript
export function listVoices(projectDir: string): string[] {
  const voicesDir = getVoicesDir(projectDir);
  const voices: string[] = ["base"];
  if (existsSync(voicesDir)) {
    const files = readdirSync(voicesDir)
      .filter((f) => f.endsWith(".md"))
      .map((f) => f.replace(/\.md$/, ""))
      .sort();
    voices.push(...files);
  }
  return voices;
}
```

**Step 4: Verify build**

Run:
```bash
cd /root/projects/Interverse/plugins/interfluence/server && npx tsc --noEmit
```
Expected: No errors

**Step 5: Commit**

```bash
cd /root/projects/Interverse/plugins/interfluence && git add server/src/utils/paths.ts
git commit -m "feat(interfluence): voice-aware path resolver and voice name validation"
```

---

## Task 3: Add Voice Resolution Function

**Files:**
- Create: `plugins/interfluence/server/src/utils/voice-resolution.ts`

**Step 1: Create the voice resolution module**

Create `server/src/utils/voice-resolution.ts`:

```typescript
import { minimatch } from "minimatch";

export interface VoiceConfig {
  name: string;
  applyTo: string[];
}

/**
 * Resolves which voice matches a file path.
 * Iterates voices in array order — first match wins.
 * Returns the matching voice name, or null if no match (use base).
 */
export function resolveVoice(
  filePath: string,
  voices: VoiceConfig[],
): string | null {
  for (const voice of voices) {
    for (const pattern of voice.applyTo) {
      if (minimatch(filePath, pattern, { matchBase: false })) {
        return voice.name;
      }
    }
  }
  return null;
}
```

**Step 2: Verify build**

Run:
```bash
cd /root/projects/Interverse/plugins/interfluence/server && npx tsc --noEmit
```
Expected: No errors

**Step 3: Commit**

```bash
cd /root/projects/Interverse/plugins/interfluence && git add server/src/utils/voice-resolution.ts
git commit -m "feat(interfluence): voice resolution function with first-match-wins glob matching"
```

---

## Task 4: Extend Config Interface and `config_get`/`config_save`

**Files:**
- Modify: `plugins/interfluence/server/src/tools/profile.ts:1-24` (imports and types)
- Modify: `plugins/interfluence/server/src/tools/profile.ts:76-139` (config tools)

**Step 1: Update the interface and default config**

In `profile.ts`, replace the `interfluenceConfig` interface (lines 12-17) and `DEFAULT_CONFIG` (lines 19-24):

```typescript
import { VoiceConfig } from "../utils/voice-resolution.js";

export interface interfluenceConfig {
  mode: "auto" | "manual";
  autoApplyTo: string[];
  exclude: string[];
  learnFromEdits: boolean;
  voices?: VoiceConfig[];
}

const DEFAULT_CONFIG: interfluenceConfig = {
  mode: "manual",
  autoApplyTo: ["*.md", "CHANGELOG*", "docs/**"],
  exclude: ["CLAUDE.md", "AGENTS.md", ".interfluence/**"],
  learnFromEdits: true,
};
```

**Step 2: Update `config_save` to accept `voices` parameter**

Replace the `config_save` tool registration (lines 103-139) with:

```typescript
  server.tool(
    "config_save",
    "Save the interfluence configuration. The voices array replaces the entire voices config (not merged) to preserve ordering.",
    {
      projectDir: z.string().describe("Absolute path to the project directory"),
      mode: z.enum(["auto", "manual"]).optional(),
      autoApplyTo: z.array(z.string()).optional(),
      exclude: z.array(z.string()).optional(),
      learnFromEdits: z.boolean().optional(),
      voices: z
        .array(
          z.object({
            name: z.string().describe("Voice name (alphanumeric + hyphens)"),
            applyTo: z.array(z.string()).describe("Glob patterns for file matching"),
          }),
        )
        .optional()
        .describe("Ordered array of voice configs. Replaces entire voices array if provided."),
    },
    async ({ projectDir, mode, autoApplyTo, exclude, learnFromEdits, voices }) => {
      const configPath = getConfigPath(projectDir);

      let config: interfluenceConfig;
      if (existsSync(configPath)) {
        config = yaml.load(readFileSync(configPath, "utf-8")) as interfluenceConfig;
      } else {
        config = { ...DEFAULT_CONFIG };
      }

      if (mode !== undefined) config.mode = mode;
      if (autoApplyTo !== undefined) config.autoApplyTo = autoApplyTo;
      if (exclude !== undefined) config.exclude = exclude;
      if (learnFromEdits !== undefined) config.learnFromEdits = learnFromEdits;
      if (voices !== undefined) config.voices = voices;

      writeFileSync(configPath, yaml.dump(config, { lineWidth: 120 }), "utf-8");

      return {
        content: [
          {
            type: "text" as const,
            text: `Configuration saved:\n${yaml.dump(config, { lineWidth: 120 })}`,
          },
        ],
      };
    },
  );
```

**Step 3: Verify build**

Run:
```bash
cd /root/projects/Interverse/plugins/interfluence/server && npx tsc --noEmit
```
Expected: No errors

**Step 4: Commit**

```bash
cd /root/projects/Interverse/plugins/interfluence && git add server/src/tools/profile.ts
git commit -m "feat(interfluence): extend config schema with voices array for voice routing"
```

---

## Task 5: Extend `profile_get`/`profile_save` with Voice Parameter

**Files:**
- Modify: `plugins/interfluence/server/src/tools/profile.ts:26-74` (profile_get and profile_save tools)

**Step 1: Add imports to profile.ts**

Add these imports at the top of `profile.ts` (alongside existing imports):

```typescript
import {
  getVoiceProfilePath,
  getConfigPath,
  getLearningsRawPath,
  getLearningsPath,
  getVoicesDir,
  isValidVoiceName,
  listVoices,
} from "../utils/paths.js";
import { mkdirSync } from "fs";
```

Note: `mkdirSync` needs to be added to the existing `fs` import: `import { readFileSync, writeFileSync, existsSync, appendFileSync, mkdirSync } from "fs";`

**Step 2: Replace `profile_get` tool**

Replace the `profile_get` registration (lines 27-52) with:

```typescript
  server.tool(
    "profile_get",
    "Get a voice profile. Without voice param, returns the base profile. With voice param, returns the named voice delta.",
    {
      projectDir: z.string().describe("Absolute path to the project directory"),
      voice: z.string().optional().describe("Voice name (e.g. 'blog', 'docs'). Omit for base profile."),
    },
    async ({ projectDir, voice }) => {
      if (voice && voice !== "base" && !isValidVoiceName(voice)) {
        return {
          content: [
            {
              type: "text" as const,
              text: `Invalid voice name "${voice}". Use lowercase alphanumeric and hyphens, 2-32 characters.`,
            },
          ],
        };
      }

      const profilePath = getVoiceProfilePath(projectDir, voice);

      if (!existsSync(profilePath)) {
        const label = voice && voice !== "base" ? `Voice profile "${voice}"` : "Base voice profile";
        return {
          content: [
            {
              type: "text" as const,
              text: `${label} does not exist. ${voice ? `Expected at: ${profilePath}` : "Use /interfluence analyze to generate one from your corpus."}`,
            },
          ],
        };
      }

      const content = readFileSync(profilePath, "utf-8");
      return {
        content: [{ type: "text" as const, text: content }],
      };
    },
  );
```

**Step 3: Replace `profile_save` tool**

Replace the `profile_save` registration (lines 54-74) with:

```typescript
  server.tool(
    "profile_save",
    "Save or update a voice profile. Without voice param, saves the base profile. With voice param, saves a voice delta to voices/ directory.",
    {
      projectDir: z.string().describe("Absolute path to the project directory"),
      content: z.string().describe("The full voice profile markdown content"),
      voice: z.string().optional().describe("Voice name (e.g. 'blog', 'docs'). Omit for base profile."),
    },
    async ({ projectDir, content, voice }) => {
      if (voice && voice !== "base" && !isValidVoiceName(voice)) {
        return {
          content: [
            {
              type: "text" as const,
              text: `Invalid voice name "${voice}". Use lowercase alphanumeric and hyphens, 2-32 characters.`,
            },
          ],
        };
      }

      const profilePath = getVoiceProfilePath(projectDir, voice);

      // Create voices/ directory if saving a named voice
      if (voice && voice !== "base") {
        const voicesDir = getVoicesDir(projectDir);
        if (!existsSync(voicesDir)) {
          mkdirSync(voicesDir, { recursive: true });
        }
      }

      writeFileSync(profilePath, content, "utf-8");

      const label = voice && voice !== "base" ? `Voice profile "${voice}"` : "Base voice profile";
      return {
        content: [
          {
            type: "text" as const,
            text: `${label} saved to ${profilePath}`,
          },
        ],
      };
    },
  );
```

**Step 4: Verify build**

Run:
```bash
cd /root/projects/Interverse/plugins/interfluence/server && npx tsc --noEmit
```
Expected: No errors

**Step 5: Commit**

```bash
cd /root/projects/Interverse/plugins/interfluence && git add server/src/tools/profile.ts
git commit -m "feat(interfluence): add optional voice param to profile_get/profile_save"
```

---

## Task 6: Add `profile_list` Tool

**Files:**
- Modify: `plugins/interfluence/server/src/tools/profile.ts` (add new tool after `profile_save`)

**Step 1: Add `profile_list` tool registration**

Insert this tool registration after `profile_save` and before `config_get`:

```typescript
  server.tool(
    "profile_list",
    "List all available voice profiles. Returns base + any voices from the voices/ directory. Warns about config/filesystem mismatches.",
    {
      projectDir: z.string().describe("Absolute path to the project directory"),
    },
    async ({ projectDir }) => {
      const voices = listVoices(projectDir);

      // Check for config/filesystem reconciliation warnings
      const warnings: string[] = [];
      const configPath = getConfigPath(projectDir);
      if (existsSync(configPath)) {
        const config = yaml.load(readFileSync(configPath, "utf-8")) as interfluenceConfig;
        if (config.voices) {
          for (const vc of config.voices) {
            if (!voices.includes(vc.name)) {
              warnings.push(
                `Warning: Config references voice "${vc.name}" but voices/${vc.name}.md not found`,
              );
            }
          }
          // Check for voice files not in config (informational, not an error)
          const configNames = config.voices.map((v) => v.name);
          for (const v of voices) {
            if (v !== "base" && !configNames.includes(v)) {
              warnings.push(
                `Info: Voice file "${v}" exists but has no routing in config (won't auto-resolve from file paths)`,
              );
            }
          }
        }
      }

      let text = `Available voices: ${JSON.stringify(voices)}`;
      if (warnings.length > 0) {
        text += "\n\n" + warnings.join("\n");
      }

      return {
        content: [{ type: "text" as const, text }],
      };
    },
  );
```

**Step 2: Verify build**

Run:
```bash
cd /root/projects/Interverse/plugins/interfluence/server && npx tsc --noEmit
```
Expected: No errors

**Step 3: Commit**

```bash
cd /root/projects/Interverse/plugins/interfluence && git add server/src/tools/profile.ts
git commit -m "feat(interfluence): add profile_list tool with reconciliation warnings"
```

---

## Task 7: Build Bundle and Verify

**Files:**
- Modify: `plugins/interfluence/server/dist/bundle.js` (auto-generated)

**Step 1: Run full build**

```bash
cd /root/projects/Interverse/plugins/interfluence/server && npm run build
```
Expected: No errors, `dist/bundle.js` updated

**Step 2: Verify the bundle loads**

```bash
cd /root/projects/Interverse/plugins/interfluence/server && node -e "import('./dist/bundle.js').then(() => console.log('Bundle loads OK')).catch(e => console.error('FAIL:', e.message))"
```
Expected: `Bundle loads OK` (server will fail to connect transport but the import should succeed)

**Step 3: Commit the bundle**

```bash
cd /root/projects/Interverse/plugins/interfluence && git add server/dist/bundle.js
git commit -m "build(interfluence): rebuild bundle with voice-aware profile storage and config"
```

---

## Task 8: Manual Integration Test

**Step 1: Reinstall the plugin**

```bash
claude plugins install /root/projects/Interverse/plugins/interfluence
```

**Step 2: Test in a new Claude Code session**

Start a new Claude Code session and test these flows:

1. **Base profile (backward compat):**
   - Call `profile_get(projectDir)` → should return existing base profile or "no profile" message
   - Call `profile_save(projectDir, "test content")` → should save to `voice-profile.md`

2. **Named voice:**
   - Call `profile_save(projectDir, "# Blog Delta\n\n## Sentence Structure\nKeep it short.", "blog")` → should create `voices/blog.md`
   - Call `profile_get(projectDir, "blog")` → should return the blog delta content
   - Call `profile_list(projectDir)` → should return `["base", "blog"]`

3. **Config with voices:**
   - Call `config_save(projectDir, { voices: [{ name: "blog", applyTo: ["posts/**"] }] })` → should save config with voices array
   - Call `config_get(projectDir)` → should show voices array

4. **Validation:**
   - Call `profile_save(projectDir, "content", "INVALID NAME!")` → should return validation error

5. **Reconciliation warnings:**
   - Call `config_save` with voice name "docs" (no file exists) → then `profile_list` → should show warning about missing file

**Step 3: If all tests pass, commit a version bump**

```bash
cd /root/projects/Interverse/plugins/interfluence && bash scripts/bump-version.sh 0.2.0
```

---

## Summary

| Task | What | Files | Est. |
|------|------|-------|------|
| 1 | Add minimatch dep | package.json | 2 min |
| 2 | Voice path resolver + validator | utils/paths.ts | 5 min |
| 3 | Voice resolution function | utils/voice-resolution.ts (new) | 3 min |
| 4 | Config schema extension | tools/profile.ts (config_save) | 5 min |
| 5 | profile_get/save voice param | tools/profile.ts | 5 min |
| 6 | profile_list tool | tools/profile.ts | 5 min |
| 7 | Build bundle | dist/bundle.js | 2 min |
| 8 | Integration test + version bump | manual | 10 min |

**Total:** ~8 tasks, ~37 minutes of implementation work.

**Dependency chain:** Tasks 1-6 are sequential (each builds on prior). Task 7 depends on all. Task 8 depends on 7.
