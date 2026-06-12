<!-- flux-drive:complete -->
<!-- run_uuid: 57272bdd-9eb0-42d1-8ae7-ed79e4d7aa8a -->

# fd-skill-bundle-conformance — Review

**Target:** docs/brainstorms/2026-05-25-auraken-distribution-v01-brainstorm.md
**Lens:** Hermes ecosystem contributor reviewing SKILL.md for agentskills.io conformance and the bundle layout for skill-runtime correctness.

## Findings Index

- F1 (P1) — SKILL.md frontmatter has only `name` and `description`; no `version`, `license`, `author`, `homepage`, or `compatibility` — likely required by agentskills.io
- F2 (P1) — `lens_select` invocation timing ("at the start of each substantive turn") is not enforceable; SKILL.md cannot bind tool-call ordering deterministically across model providers
- F3 (P1) — "Never" assertions (never name the lens, never offer a menu, never describe what Auraken does) are behavioral norms that the Hermes runtime does not enforce; failure surface is voice drift on model substitution
- F4 (P2) — voice-rubric.md split risks documentation dead-zone: SKILL.md references voice rules that live in a sibling file the runtime does not load
- F5 (P2) — Mode-transition semantics ("when a task request shifts the mode") have no defined hook in Hermes's skill lifecycle; orphan-MCP-call risk if the model leaves `/auraken` mid-session
- F6 (P2) — OODARC five-motion loop documented in SKILL.md (lines 32–42) is invisible-by-design but appears in the file a user might `cat` post-install — leaks scaffolding to readers
- F7 (P3) — The `/ak` alias workaround (sibling SKILL.md with `name: ak`) per recon README is a sync footgun for v0.1; not addressed in brainstorm bundle layout

## Verdict

SKILL.md is **conformant enough for v0.1 self-distribution** (GitHub release + install.sh), but **insufficient for agentskills.io submission** as the brainstorm sequences v0.2. The frontmatter is missing fields any ecosystem registry would need, and the behavioral assertions are not machine-checkable. F1 is the blocker for the v0.2 agentskills.io path explicitly named in the brainstorm's distribution plan. F2 and F3 are deeper: SKILL.md tries to constrain model behavior with declarative rules in a runtime that has no constraint solver. These are inherent gaps, but plan phase should at least name them and document the validation strategy.

## Summary

The current SKILL.md is high-quality prose: clear voice, clear behavior, distinct from generic assistant patterns. It will work for users who run `/auraken` on Claude Opus 4.7 with a cooperative model. It will not deterministically constrain Hermes — that's not what SKILL.md is for. The brainstorm assumes (correctly) that the recon SKILL.md is "audience-neutral — no rewrite needed for v0.1" but does not address the frontmatter or runtime-enforcement gaps that block v0.2 agentskills.io submission. Plan phase needs to (a) extend frontmatter to the agentskills.io standard, (b) extract voice rubric properly with a runtime register_check rule, and (c) document the SKILL.md → behavior contract as best-effort, not enforced.

## Issues Found

### F1 — P1 — Frontmatter missing required ecosystem fields

**Where:** apps/Auraken/integrations/hermes/skills/auraken/SKILL.md lines 1–4:
```yaml
---
name: auraken
description: Cognitive augmentation mode for working through problems with real structure ...
---
```

**Failure scenario:** v0.2 plans to submit to agentskills.io. Every existing skill registry (Hermes's own examples in apps/Auraken/research/hermes-agent/, agentskills.io public listings) has at least: `version`, `author`, `license`, `homepage`, and a `compatibility` block. Submission gets rejected for missing required metadata; v0.2 milestone slips while frontmatter is rewritten and re-tested. The brainstorm states v0.2 depends on v0.1 acceptance — F1 makes v0.1 SKILL.md a v0.2-blocker even though v0.1 itself ships fine without it.

**Question:** Has anyone audited the agentskills.io submission schema since the recon-spike SKILL.md was written? The bead `sylveste-heh8` reframe (2026-05-25) does not show this audit.

**Smallest viable fix:** Add the missing fields now (v0.1) so v0.2 inherits a submission-ready file:
```yaml
---
name: auraken
description: ...
version: 0.1.0
author: mistakeknot
homepage: https://github.com/mistakeknot/Sylveste/tree/main/apps/Auraken
license: MIT
compatibility:
  hermes_agent: ">=2026.4.0"
  mcp_servers:
    - auraken-lens
---
```
Source the `version` and `compatibility` block from MANIFEST.yaml at build time.

### F2 — P1 — `lens_select` invocation timing is not enforceable

**Where:** SKILL.md line 44 ("Use lens_select at the start of each substantive turn"), and the `lens_select` tool description in server.py:69 ("Call at the start of every substantive turn in Auraken mode").

**Failure scenario:** SKILL.md instructs the model to call `lens_select` at the start of each substantive turn. Hermes is provider-agnostic; on Claude Opus 4.7 this works well, on smaller models the call gets skipped or called after the first prose token, on GPT-5.x the call ordering differs. Behavior drifts visibly between providers — one Hermes user sees lens-driven questions, another sees ungrounded prose. The brainstorm's MANIFEST `compatibility.models` block lists both Claude and OpenAI without acknowledging this divergence.

**Question:** How does the recon spike's cache discipline (apps/Auraken/integrations/hermes/README.md §"Cache discipline") handle the case where the model skips the lens_select call? Does the OODARC loop degrade gracefully or does Auraken silently behave like a generic chatbot?

**Smallest viable fix:** SKILL.md adds a self-check pattern: "Before responding, verify lens_select was called this turn; if not, call it now." Voice-rubric.md (when extracted) adds a `register_check` rule that the response is rejected if it contains classification patterns ("This is a case of …") that indicate the model bypassed the lens.

### F3 — P1 — "Never" assertions are voice rules, not enforced constraints

**Where:** SKILL.md "Behavior" section (lines 11–22) and "Voice" section (lines 54–70).

The file uses absolute language: "Never offer a menu of problem types", "Never describe what Auraken does", "Never name the lens unless the user asks", "Avoid the rule-of-three", "Avoid tack-on em dashes", "Avoid AI vocabulary: 'delve,' 'foster,' …". These are voice rules. They are not runtime-enforced — no Hermes hook intercepts and rejects responses that name the lens or use "delve".

**Failure scenario:** Model substitution (claude-haiku-4-5 instead of opus-4-7) → response includes "Let me delve into this — there are three angles …". User experiences Auraken as a generic LLM with extra steps. No diagnostic surfaces because nothing in Hermes is wired to check.

**Smallest viable fix:** The brainstorm's mention of `voice-rubric.md` "extracted voice criteria for register_check" is the right move. Make register_check **a runtime hook** in the MCP server (not just docs): post-process the model's response, scan for forbidden tokens, return a `lens_select` result that contains the criticism on the next turn. Document this as a v0.1 capability so it's testable.

### F4 — P2 — voice-rubric.md split coherence risk

**Where:** brainstorm §"Bundle layout" lines 41–42:
```
skills/auraken/
    ├── SKILL.md
    └── voice-rubric.md   # extracted voice criteria for register_check
```

**Failure scenario:** SKILL.md is the file Hermes loads as the skill body. voice-rubric.md is a sibling file Hermes does **not** automatically load. If SKILL.md references the rubric ("see voice-rubric.md for register criteria") but the runtime never reads it, the rubric becomes documentation-for-humans, not behavior. Users who skim SKILL.md and skip the rubric file miss voice constraints; the voice section in SKILL.md duplicates rubric content; the two files drift.

**Question:** Does the brainstorm intend voice-rubric.md as (a) human-readable companion documentation, (b) machine-readable register_check input consumed by the MCP server, or (c) both with a single-source mechanism? It currently reads as (a) by default, but the "extracted voice criteria for register_check" framing implies (b).

**Smallest viable fix:** Decide in plan phase. If (b), the MCP server's `lens_select` tool also exposes a `register_check` tool that reads voice-rubric.md at startup. If (a), delete the rubric file and keep voice rules in SKILL.md only.

### F5 — P2 — Mode-transition has no Hermes hook

**Where:** SKILL.md lines 76–79 ("When Auraken mode ends — A task request shifts the mode … gracefully exit by doing the task as Hermes would. Auraken mode is a conversational posture …").

**Failure scenario:** User mid-Auraken-session says "draft this email". Per SKILL.md, the exchange shifts mode. But `lens_select` tool registration persists for the rest of the session; the model might continue calling it for a "draft this email" turn and waste tokens producing irrelevant lens metadata. Trajectory JSONL now contains lens selections for tasks that aren't substantive thinking turns — pollutes the LensBench training set.

**Question:** Does the SKILL.md mode-transition language correspond to a Hermes skill-deactivation hook, or is it advisory only? If advisory, what filters out non-Auraken-mode `lens_select` calls from the trajectory log?

**Smallest viable fix:** lens_select tool description (server.py:69) adds: "Do not call this for task execution requests (draft, fix, run, build). Empty result is correct for such turns." This is enforcement-by-prompt — works on cooperative models, fails on others, but at least documents the expected pattern.

### F6 — P2 — OODARC scaffolding leakage

**Where:** SKILL.md lines 32–42 (full OODARC five-motion documentation).

**Failure scenario:** User runs `cat ~/.hermes/skills/auraken/SKILL.md` post-install to understand what they just installed. They read "Every substantive turn moves through five motions, invisibly to the user: 1. Observe. … 2. Orient. … 3. Decide. … 4. Act. … 5. Reflect." The "invisibly to the user" framing is broken by the file being human-readable. Users learn the internal vocabulary, then notice it during a session, and the magic-camera framing degrades into algorithmic-checkbox framing.

**Note:** This is a design choice, not a bug. The brainstorm includes OODARC documentation in SKILL.md by reference (it inherits from the existing file). Worth flagging because the brainstorm's "audience-neutral" claim about the existing SKILL.md doesn't extend to "users won't read this and de-mystify the personality".

**Smallest viable fix:** Move OODARC to `skills/auraken/INTERNAL.md` (developer doc, not Hermes-loaded). SKILL.md keeps the runtime behavior; INTERNAL.md keeps the scaffolding doctrine. Reduces user-facing footprint.

### F7 — P3 — `/ak` alias workaround not in bundle layout

**Where:** apps/Auraken/integrations/hermes/README.md install §2 documents a workaround: copy SKILL.md to a sibling dir, sed-rewrite the `name:` field to `ak`. The brainstorm bundle layout does not include this. Bead `sylveste-ovux` is referenced for upstream alias support.

**Failure scenario:** v0.1 ships only `/auraken`. Users accustomed to typing `/ak` (per the recon spike) hit "command not found" and check the bundle for the alias. Either: (a) silently break the existing workflow, or (b) install.sh applies the sed-rewrite at install time, ending up with two files in the bundle that need to stay in sync.

**Smallest viable fix:** Plan-phase decision: either drop `/ak` from v0.1 with a CHANGELOG note ("the dual-name workaround is removed pending sylveste-ovux upstream"), or add `skills/ak/SKILL.md` to the bundle layout with a build-time sed-rewrite step.

## Improvements

- **Frontmatter completeness audit against agentskills.io** is a v0.1 deliverable, not v0.2. Cheap to do now, expensive to retrofit.
- **Wire register_check as a runtime feature**, not a documentation aspiration. If voice rules matter to v0.1, the MCP server enforces them; if they don't, voice-rubric.md is human-doc and SKILL.md should say so.
- **Move OODARC and the cache-discipline rationale into INTERNAL.md.** SKILL.md is the runtime spec; INTERNAL.md is the architecture doc. Users who `cat` the installed skill should see only what they can use.
- **Single-source `version` and `compatibility` from MANIFEST.yaml** into SKILL.md frontmatter via the build-dist.sh step (see fd-mcp-server-packaging F7). Prevents the version-drift class of issue across all bundle files.
