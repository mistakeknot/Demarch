---
artifact_type: brainstorm
bead: sylveste-sn7.6
stage: discover
date: 2026-05-06
prior_research:
  - docs/research/flux-review/tuivision-token-optimization/2026-04-02-synthesis.md
  - interverse/tuivision/docs/annotated-format-spec.md
---

# tuivision sn7.6: motif / L0 LOD level for polling agents

## What We're Building

A new `format=motif` value on the existing `get_screen` MCP tool that returns a content-hashed structural summary at ~20–50 tokens per call, with caller-supplied `since_hash` to short-circuit unchanged poll ticks at ~22 tokens.

**Unchanged tick (the dominant case):**
```
[L0 80x24 cursor=hidden hash=a3f1 unchanged_since=12.1s]
```

**Changed tick:**
```
[L0 80x24 cursor=12,8 hash=b7e2 changed_lines=3 dominant=g styled=12 last_change=0.4s]
```

This sits below the existing `text` (~250 tok), `compact` (~280 tok), `annotated` (~400–800 tok), and `full` (~12K tok) formats as the L0 layer of the LOD ladder being tracked separately as sn7.16.

## Why This Approach

The choreographic-notation finding in the 2026-04-02 synthesis identified that agents polling long-running TUIs pay 200–400 tokens per tick when 15 would answer "still running." The bead description framed this as a pattern-recognition problem ("requires screen-state pattern recognition") and cited a build/test motif example. After repo scan, the real win is structural, not semantic:

1. **The dominant cost is repeated identical ticks**, not failure to extract domain content. A 20-tick poll session over a 10-second build pays 200×20 = 4000 tokens today; with hash-based unchanged-skip, it pays 22×19 + 45 = 463 tokens — a 9× reduction without any heuristic recognizer library.

2. **`wait_for_screen_change` already handles silent polling** (debounced PTY-data wait). Layering motif-with-hash on `get_screen` lets callers compose: `wait_for_screen_change` → `get_screen format=motif since_hash=X`. This keeps the wait/summarize responsibilities separate.

3. **No recognizer registry to maintain.** Option B (heuristic recognizers per TUI class) would have created a per-app maintenance burden and pulled tuivision into a domain-classification responsibility it shouldn't own. Option C (caller-supplied regex extractors) is a viable follow-up bead but adds API surface that should wait for evidence callers want it.

4. **Composes with already-shipped infrastructure.** Reuses the structural preamble pattern (`[screen 80x24 cursor=12,8]` from `getAnnotatedText`), the existing density-threshold pass (modal-color suppression already counts styled cells), and `session.lastActivityAt` in `session-manager.ts:26`.

5. **Hash-based fingerprinting beats text-diff.** `wait_for_screen_change` currently compares plain text via `getScreenText()` — a 16-byte content hash over the cell buffer is cheaper to store, distinguishes color-only changes, and is what callers want to compare anyway.

## Key Decisions

| Decision | Choice | Rationale |
|---|---|---|
| API surface | New `format=motif` on `get_screen` | Smallest surface; composes with existing wait tools; no overload of wait semantics |
| Pattern mechanism | Generic structural summary, no recognizers | YAGNI; the cache hit dominates; recognizers can be added per-app by callers |
| Cache key | Caller-passed `since_hash` parameter | Server-side cache state would couple sessions; caller-passed is stateless and explicit |
| Hash algorithm | First 4 hex chars of SHA-1 over cell buffer | 16-bit collision risk acceptable for a poll-session deduplication signal; SHA-1 is fast in node and already a JS standard |
| `last_change` source | New `lastScreenChangeAt: Date` on Session, updated when hash changes | `lastActivityAt` tracks PTY input which fires for cursor blinks and keepalives; need a distinct screen-mutation timestamp |
| `changed_lines` source | Diff against previous hash's line-text array, kept on Session | Bounded memory: keep only the most recent line-hash array per session |
| `dominant` color | Reuse `getAnnotatedText` modal-color logic | Already implemented and validated; lift into shared helper |
| Schema field | Add `schema: 1` like other formats; bump on breaking change | Already part of the `ScreenResponse` envelope from the F3 default-flip work |
| Forward-compat to sn7.16 | This format IS the L0 of the L0/L1/L2/L3 ladder | Naming chosen to match: `motif` is the name; L0 is the ladder slot |

## Open Questions

1. **Should `dominant` color collapse to a semantic group** (`error`/`success`/`warning`/`info`/`neutral` from `SEMANTIC_COLOR_GROUPS` in terminal-renderer.ts:58) **or stay as a single-char palette code** (`r`/`g`/`y`/`b`/`w`)? The semantic group is more agent-actionable but loses information. *Resolution candidate:* return both — `dominant=g/success` — costs 4 extra tokens.

2. **What happens when `since_hash` is stale?** (Caller passed a hash from 30s ago, screen has changed twice since.) Two options: (a) treat as "changed, full motif," (b) report `unchanged_since=null changed_count=2 hash=current`. Option (a) is simpler; option (b) gives the caller a "you missed N changes" signal. *Lean:* (a) for v1, add (b) only if requested.

3. **Should `wait_for_screen_change` start emitting hashes** so callers get them for free? Tempting but out of scope for this bead — it would touch the wait response shape, which is a coordination concern with sn7.8 (diff/delta mode). *Decision:* defer; create follow-up bead if proven useful.

4. **Hash stability across resize.** A terminal resize changes the cell buffer dimensions and therefore the hash, even if the visible content is "the same." Acceptable: resize is an explicit operation, callers can re-baseline.

5. **Is the 22-token unchanged-tick estimate realistic?** Need to validate with cl100k tokenizer on `[L0 80x24 cursor=hidden hash=a3f1 unchanged_since=12.1s]`. *To do during plan phase.*

6. **Should `changed_lines` be a count or a list of indices?** A count is cheaper (`changed_lines=3`); a list (`changed_lines=2,7,18`) lets the caller decide whether to fetch full state. *Lean:* count for v1; the indices version is a sn7.8-class concern.
