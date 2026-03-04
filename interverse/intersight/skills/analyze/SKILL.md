---
name: analyze
description: "Analyze a website's design system — extracts W3C DTCG tokens, component inventory, and layout analysis"
user_invocable: true
argument-hint: "<URL> [--depth tokens|standard|full] [--format json|markdown|tokens-only] [--fresh] [--pages /path1,/path2]"
allowed-tools: ["Bash", "Read", "Write", "mcp__playwright*"]
---

# intersight:analyze

Analyze a website and extract its design system as W3C DTCG tokens.

## Arguments

Parse the user's arguments from `$ARGUMENTS`:

- **URL** (required, positional) — The target URL to analyze. Must start with `http://` or `https://`.
- **--depth** (optional, default: `standard`) — Analysis depth: `tokens`, `standard`, or `full`
- **--format** (optional, default: `json`) — Output format: `json`, `markdown`, or `tokens-only`
- **--fresh** (optional) — Skip cache lookup, run full extraction
- **--pages** (optional) — Comma-separated relative paths for multi-page analysis (e.g., `/,/dashboard,/settings`)

If no URL is provided, ask the user: "What URL would you like to analyze?"

Validate the URL starts with `http://` or `https://`. If not, prepend `https://` and warn the user.

## State Tracking

Track these variables throughout execution:

```
url = <parsed URL>
depth = tokens | standard | full
format = json | markdown | tokens-only
fresh = true | false
pages = [<parsed page paths>] or ["/"]
dembrandt_available = true (until proven otherwise)
intercache_available = true (until proven otherwise)
phases_completed = []
warnings = []
extraction_results = {}
```

## Phase 0: Preflight

### 0a: Dependency checks

**Check Dembrandt:**
```bash
command -v npx >/dev/null 2>&1 && npx dembrandt --version 2>/dev/null
```
- If fails: set `dembrandt_available = false`, add warning: "Dembrandt not found. Continuing with DOM-only extraction. For better results: npm install -g dembrandt"
- Do NOT abort — DOM extraction works without Dembrandt.

**Check Playwright MCP:**
Attempt: `browser_navigate` to `about:blank`
- If fails (tool not found or connection error): ABORT with error:
  > "intersight requires Playwright MCP server to analyze websites. Install: `claude mcp add playwright npx @playwright/mcp@latest --snapshot-mode none` and add it to your Claude Code MCP settings (Settings > MCP Servers)."
- This is a hard requirement — cannot proceed without browser.

**Token optimization check:**
After confirming Playwright MCP is available, check whether the server was started with `--snapshot-mode none`. If every tool response includes a large accessibility snapshot (thousands of tokens of ARIA tree), warn the user:
> "Playwright MCP is running with default snapshot mode. For significantly lower token usage (~70-80% reduction per action), restart with `--snapshot-mode none`. The `browser_snapshot` tool still works independently — this only suppresses the auto-appended snapshots on every other tool response."

This optimization is strongly recommended because Intersight's pipeline makes 16-40 Playwright tool calls per analysis (depending on depth), and only Phase 4's `browser_snapshot` needs the accessibility tree. All other calls (`browser_navigate`, `browser_resize`, `browser_evaluate`, `browser_take_screenshot`, `browser_hover`) discard the snapshot.

### 0b: robots.txt compliance (mandatory)

Extract the target path from the URL:
```javascript
// e.g., https://example.com/dashboard → /dashboard
const targetPath = new URL(url).pathname;
```

Navigate to `<origin>/robots.txt`:
```
browser_navigate: <origin>/robots.txt
```

Read the `parseRobotsTxt.js` script from `${CLAUDE_PLUGIN_ROOT}/scripts/extraction/parseRobotsTxt.js`, replace `__TARGET_PATH__` with the actual target path, then evaluate:
```
browser_evaluate: <modified parseRobotsTxt.js content>
```

Parse the result:
- If `allowed: false`: ABORT with message:
  > "robots.txt disallows access to [path] for web crawlers (matched rule: [matchedRule]). intersight respects robots.txt. Suggestions: analyze a different page, or run against a local copy."
- If `allowed: true`: continue.

Also check meta robots tag after page navigation (in Phase 1).

### 0c: Cache lookup (if intercache available and not --fresh)

Only if `fresh` is false:
```
Attempt: cache_lookup(key="intersight:" + url + ":" + depth)
```
- If tool call fails (tool not found): set `intercache_available = false`, continue
- If cache hit: parse and return cached result immediately. Done.
- If cache miss: continue with extraction.

Add `preflight` to `phases_completed`.

## Phase 1: Setup

Navigate to the target URL:
```
browser_navigate: <url>
```

**Wait for page stability (SPA quiescence):**
Run via `browser_evaluate`:
```javascript
(() => {
  return new Promise(resolve => {
    let lastCount = document.querySelectorAll('*').length;
    let stableChecks = 0;
    const interval = setInterval(() => {
      const current = document.querySelectorAll('*').length;
      if (current === lastCount) stableChecks++;
      else { stableChecks = 0; lastCount = current; }
      if (stableChecks >= 3) { clearInterval(interval); resolve(JSON.stringify({ stable: true, elementCount: current })); }
    }, 500);
    setTimeout(() => { clearInterval(interval); resolve(JSON.stringify({ stable: false, elementCount: lastCount })); }, 5000);
  });
})()
```

**Challenge page detection:**
Run via `browser_evaluate`:
```javascript
(() => {
  const title = document.title.toLowerCase();
  const bodyText = (document.body?.innerText || '').substring(0, 500).toLowerCase();
  const indicators = ['just a moment', 'checking your browser', 'please wait', 'access denied',
                       'verify you are human', 'captcha', 'challenge-platform'];
  const detected = indicators.filter(i => title.includes(i) || bodyText.includes(i));
  return JSON.stringify({ challengeDetected: detected.length > 0, indicators: detected });
})()
```
- If `challengeDetected: true`: ABORT with:
  > "Target site served a bot-protection challenge (detected: [indicators]). intersight cannot bypass bot protection. Try analyzing a local dev server or a site without protection."

**Meta robots check:**
Run via `browser_evaluate`:
```javascript
(() => {
  const meta = document.querySelector('meta[name="robots"]');
  if (!meta) return JSON.stringify({ blocked: false });
  const content = (meta.getAttribute('content') || '').toLowerCase();
  const blocked = content.includes('noindex') || content.includes('nofollow');
  return JSON.stringify({ blocked, content: meta.getAttribute('content') });
})()
```
- If `blocked: true`: add warning: "Page has <meta name='robots' content='[content]'> — extraction may be restricted."
- Do NOT abort (meta robots is advisory for this use case, unlike robots.txt).

**Set viewport:**
```
browser_resize: { width: 1440, height: 900 }
```

**Content hash:**
Read and evaluate `${CLAUDE_PLUGIN_ROOT}/scripts/extraction/contentHash.js` via `browser_evaluate`.
Store the result as `content_hash`.

Add `setup` to `phases_completed`.

## Phase 2: Dembrandt Baseline

Skip if `dembrandt_available` is false.

Run via Bash:
```bash
npx dembrandt "<url>" --dtcg --json-only 2>/dev/null
```

- If succeeds: parse JSON output, store as `extraction_results.dembrandt`
- If fails (non-zero exit, invalid JSON, timeout after 30s): set `dembrandt_available = false`, add warning: "Dembrandt extraction failed. Continuing with DOM-only extraction."
- Do NOT abort on Dembrandt failure.

Add `dembrandt` to `phases_completed` (even if skipped — note in meta).

## Phase 3: DOM/CSS Extraction

For each extraction script, read the file from `${CLAUDE_PLUGIN_ROOT}/scripts/extraction/<name>.js` using the Read tool, then pass the full content to `browser_evaluate`.

Run these 7 scripts in sequence:

1. **extractCSSCustomProperties.js** → store as `extraction_results.customProperties`
2. **extractColorTokens.js** → store as `extraction_results.colors`
3. **extractTypography.js** → store as `extraction_results.typography`
4. **extractSpacing.js** → store as `extraction_results.spacing`
5. **extractShadowsAndBorders.js** → store as `extraction_results.shadowsAndBorders`
6. **extractBreakpoints.js** → store as `extraction_results.breakpoints`
7. **extractComponentInventory.js** → store as `extraction_results.components`

For each script:
- Parse the JSON result
- If `error` field present in result: add warning, continue with partial data
- If `count: 0` and no error: note low count but continue

**Low-count warning:** If total unique colors < 3 AND custom properties count is 0:
Add warning: "Very low token count detected. The site may use client-side rendering that wasn't fully hydrated, or the page may have minimal styling."

Add `dom_extraction` to `phases_completed`.

## Phase 4: Structural Analysis (standard + full only)

Skip if `depth` is `tokens`.

**Accessibility tree:**
```
browser_snapshot
```
Store the snapshot output. Use it to identify:
- Navigation patterns (nav elements, landmark roles)
- Primary interactive elements (buttons, links, inputs)
- Page structure (headings hierarchy, sections)

Note: `extractComponentInventory.js` already ran in Phase 3. Use its output for the component list.

Add `structural` to `phases_completed`.

## Phase 5: Visual Analysis (standard + full only)

Skip if `depth` is `tokens`.

**Screenshots:**

For `standard` depth:
```
browser_take_screenshot
```
Capture 1 desktop screenshot (viewport already set to 1440x900).

For `full` depth, capture 3 screenshots:
1. Desktop (1440x900) — already set
2. Tablet: `browser_resize: { width: 768, height: 1024 }` then `browser_take_screenshot`
3. Mobile: `browser_resize: { width: 375, height: 812 }` then `browser_take_screenshot`
4. Restore viewport: `browser_resize: { width: 1440, height: 900 }`

**Claude vision analysis:**

For each screenshot, analyze with this prompt:
> "Analyze this website screenshot for design system characteristics:
> 1. **Layout pattern** — What layout pattern is used? (sidebar-main, holy grail, single column, grid, etc.)
> 2. **Visual hierarchy** — How does the page guide the eye? What's most prominent?
> 3. **Color harmony** — Are colors consistent? What palette strategy? (monochromatic, complementary, analogous)
> 4. **Information density** — Is the page sparse, moderate, or dense with information?
> 5. **Responsive indicators** — Any visible responsive design patterns?"

Store vision analysis as `extraction_results.visualAnalysis`.

Add `visual` to `phases_completed`.

## Phase 6: Interaction States (full only)

Skip if `depth` is not `full`.

From the component inventory (Phase 3), identify up to 5 primary interactive elements:
- Buttons (highest priority)
- Links
- Input fields

For each interactive element, extract hover state changes:
1. Capture default styles via `browser_evaluate`:
```javascript
(() => {
  const el = document.querySelector('<selector>');
  if (!el) return JSON.stringify({ found: false });
  const s = getComputedStyle(el);
  return JSON.stringify({
    found: true,
    backgroundColor: s.backgroundColor,
    color: s.color,
    borderColor: s.borderColor,
    boxShadow: s.boxShadow,
    transform: s.transform,
    opacity: s.opacity
  });
})()
```

2. Hover: `browser_hover: <selector>`

3. Capture hover styles with the same script above.

4. Diff: compare default vs hover styles and record changes.

Also extract focus ring patterns:
```javascript
(() => {
  const focusable = document.querySelectorAll('button, a, input, select, textarea, [tabindex]');
  const rings = new Set();
  for (let i = 0; i < Math.min(focusable.length, 10); i++) {
    focusable[i].focus();
    const s = getComputedStyle(focusable[i]);
    const ring = s.outlineWidth + ' ' + s.outlineStyle + ' ' + s.outlineColor;
    if (s.outlineStyle !== 'none') rings.add(ring);
  }
  document.activeElement?.blur();
  return JSON.stringify({ focusRings: Array.from(rings) });
})()
```

Store as `extraction_results.interactionStates`.

Add `interactions` to `phases_completed`.

## Phase 7: Synthesis

Merge all extraction results into W3C DTCG format.

### Merge Algorithm

1. **Custom properties are the primary token source.** Each CSS custom property from `extractCSSCustomProperties.js` that represents a design token (color, spacing, typography) becomes a named token in the output. Use the `resolvedValue` field for the actual token value.

2. **Computed colors fill gaps.** Colors from `extractColorTokens.js` that don't match any custom property's `resolvedValue` are added as unnamed tokens (e.g., `color.extracted-1`, `color.extracted-2`).

3. **Dembrandt provides token names.** For any Dembrandt token whose value matches a DOM custom property's resolved value, use Dembrandt's semantic name as the token name. On value conflicts, DOM value wins (reflects runtime state).

4. **Multi-page conflicts** (when `--pages` is used): When the same CSS custom property name has different resolved values across pages, report BOTH values with page context in `warnings`. Use the value with higher total frequency.

5. **Track completeness.** Set `intersight:meta.phases_completed` and `intersight:meta.dembrandt_available`.

### Build Output Structure

Read the schema template from `${CLAUDE_PLUGIN_ROOT}/scripts/extraction/schema.json`.

Populate each section:

**`intersight:meta`:**
- `source_url`: the analyzed URL
- `analyzed_at`: current ISO timestamp
- `analysis_depth`: the depth mode used
- `pages_analyzed`: list of page paths analyzed
- `tool_version`: "0.1.0"
- `content_hash`: from Phase 1
- `dembrandt_available`: boolean
- `phases_completed`: list of phase names
- `warnings`: accumulated warnings

**`color` group:** Merge custom properties (color-type) + Dembrandt color tokens + extracted computed colors. Format each as:
```json
{
  "color-name": {
    "$type": "color",
    "$value": "#hex or rgb(...)",
    "$description": "Frequency: N, source: custom-property/dembrandt/computed"
  }
}
```

**`dimension` group:** From spacing extraction. Format each as:
```json
{
  "space-Npx": {
    "$type": "dimension",
    "$value": "Npx",
    "$description": "Frequency: N"
  }
}
```

**`typography` group:** From typography extraction. Each unique type scale entry:
```json
{
  "type-scale-N": {
    "$type": "typography",
    "$value": {
      "fontFamily": "...",
      "fontSize": "...",
      "fontWeight": N,
      "lineHeight": "...",
      "letterSpacing": "..."
    },
    "$description": "Frequency: N, used in: tag1, tag2"
  }
}
```

**`shadow` group:** From shadows extraction.

**`border` group:** From borders extraction.

**`intersight:components`:** Array from component inventory.

**`intersight:ux_flow`:** (standard + full only) From structural analysis — navigation patterns, primary actions, information density assessment.

**`intersight:visual_analysis`:** (standard + full only) From Claude vision analysis — layout pattern, visual hierarchy, responsive behavior.

### Format Output

Based on `--format`:

**`json` (default):** Output the full DTCG JSON with all extensions.

**`markdown`:** Generate a human-readable report:
```markdown
# Design System Analysis: <domain>

**URL:** <url>
**Analyzed:** <timestamp>
**Depth:** <depth>

## Color Palette
[Table of colors with hex, frequency, source]

## Typography Scale
[Table of type entries with font, size, weight, frequency]

## Spacing Scale
[Table of spacing values with frequency]

## Shadows & Borders
[Tables]

## Breakpoints
[List of responsive breakpoints]

## Component Inventory (if standard+)
[Table of components with frequency, variants]

## Layout Analysis (if standard+)
[Vision analysis summary]

## Interaction States (if full)
[Hover/focus state changes]

---
*Generated by intersight v0.1.0 — [phases_completed]*
```

**`tokens-only`:** Output bare DTCG tokens (color, dimension, typography, shadow, border groups only — no `$extensions`).

### Write output file

Always write the JSON output to a local file:
```
./intersight-analysis-<domain>-<timestamp>.json
```
where `<domain>` is the URL's hostname with dots replaced by dashes, and `<timestamp>` is YYYYMMDD-HHmmss.

Tell the user: "Output written to: [filepath]"

### Cache result (if intercache available)

If `intercache_available` is true:
```
cache_store(key="intersight:" + url + ":" + depth, value=<json output>, ttl=604800)
```
(7-day TTL = 604800 seconds)

Add `synthesis` to `phases_completed`.

## Multi-Page Analysis

If `--pages` was specified:

1. Parse comma-separated paths into a list.
2. For each page path:
   a. Navigate to `<origin><path>`
   b. Run Phases 1-6 for this page (skip Phase 0 — already done)
   c. Store per-page results
   d. If not localhost: wait 10 seconds between pages (rate limiting for third-party sites)
3. Merge results across pages:
   - Tokens: union, with higher-frequency value winning on name conflicts
   - Components: merge inventories, accumulate frequencies
   - Warnings: include per-page context for conflicts
4. Proceed to Phase 7 synthesis with merged results.

## Error Handling

If any phase fails:
1. Log which phase failed and the error message
2. Add to warnings
3. Continue to the next phase if possible (Phases 2-6 can fail independently)
4. Phase 7 (synthesis) works with whatever data was collected

Only Phase 0 (Playwright MCP missing, robots.txt blocked) and Phase 1 (navigation failure, challenge page) are hard failures that abort the entire skill.

Report at the end:
- Which phases completed successfully
- Any warnings accumulated
- What data is available vs missing
