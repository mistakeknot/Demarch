---
artifact_type: review-synthesis
method: flux-review
target: "docs/brainstorms/2026-04-12-style-fingerprinting-go-port-brainstorm.md"
target_description: "Style fingerprinting Go port — literal port of Python regex/EMA to Go pkg/style/"
tracks: 4
track_a_agents: [fd-regex-compilation-unicode-fidelity, fd-ema-float-accumulation-parity, fd-json-wire-compatibility-struct-tags, fd-fingerprint-concurrency-model, fd-mirroring-instruction-determinism]
track_b_agents: [fd-credit-scoring-feature-parity, fd-spc-concurrent-accumulation, fd-forensic-linguistics-feature-validity, fd-localization-engineering-wire-compat]
track_c_agents: [fd-song-tea-assessment-multisensory-classification, fd-ottoman-hilye-proportional-script-reproduction, fd-polynesian-wayfinding-multisignal-accumulation, fd-medieval-bell-founding-spectral-compatibility]
track_d_agents: [fd-girih-pattern-duality, fd-san-tracking-accumulation, fd-khumbu-icefall-concurrent-route]
date: 2026-04-12
---

# Cross-Track Synthesis: Style Fingerprinting Go Port

## Critical Findings (P0)

### 1. Nil map panic and JSON null/empty-dict divergence (4/4 tracks)

**Convergence score: 4/4** — highest confidence finding.

- Track A (fd-json-wire-compat): nil maps serialize as `null`, Python expects `{}`
- Track B (fd-localization-engineering): nil map deserialization + first counter increment panics
- Track C (fd-ottoman-hilye): zero-value handling and omitempty semantics
- Track D (fd-girih-pattern-duality): empty-map must be `make(map[string]int)` in constructor

Go zero-value `ModeProfile` has nil maps for all vocabulary counters. Three failure modes: (1) Go writes nil map → JSON `null` → Python reads `None` → `None.get()` crashes, (2) Go reads Python's `{}` into nil Go map → first `counter["haha"]++` panics, (3) `omitempty` on map fields drops `{}` entirely from JSON. **Fix:** `NewModeProfile()` constructor initializes all maps with `make()`. Never use `omitempty` on map fields. Add `ensureMaps()` after JSON unmarshal.

### 2. Map iteration tie-breaking nondeterminism (4/4 tracks)

**Convergence score: 4/4**

- Track A (fd-mirroring-instruction-determinism): map iteration for max differs
- Track B (fd-credit-scoring-feature-parity): RE2/map determinism divergence
- Track C (fd-song-tea-assessment): tie-breaking nondeterministic in Go
- Track D (fd-san-tracking-accumulation): explicit priority order required

`ClassifyMode` and `DetectCurrentMode` both use `max()` over a map. Python's insertion-ordered dict makes ties deterministic (emotional > analytical > playful > ...). Go maps iterate randomly. A message like "i feel like the framework here is important" ties emotional and analytical — Python always returns emotional, Go returns random. Over 50 messages, per-mode fingerprints diverge. **Fix:** Define canonical priority slice `[]Mode{Emotional, Analytical, Playful, Intimate, Logistics, Update}`. Iterate the slice, not the map, to find max.

### 3. `emoji_density` byte count vs rune count (2/4 tracks)

**Convergence score: 2/4** (Track A + Track B)

- Track A (fd-regex-compilation-unicode-fidelity): `len(text)` gives bytes, not runes
- Track B (fd-localization-engineering-wire-compat): systematic 1.43x bias for emoji-heavy messages

Python `len("hello 😂")` = 7 (code points). Go `len("hello 😂")` = 10 (UTF-8 bytes). For any message with emoji, `emoji_density` is systematically lower in Go. This compounds through EMA into the stored fingerprint. **Fix:** Use `utf8.RuneCountInString(text)` for all length computations that feed the fingerprint.

### 4. Python crash bug in `build_instant_mirroring` (2/4 tracks)

**Convergence score: 2/4** (Track A + Track C)

- Track A (fd-mirroring-instruction-determinism): `.keys()` on a list raises AttributeError
- Track C (fd-song-tea-assessment): lines 536-542 are dead code that has never executed successfully

`compute_observables` returns `"laughter": ["haha"]` (a list). `build_instant_mirroring` line 537 calls `list(obs["laughter"].keys())[0]` — `.keys()` on a list raises `AttributeError`. Same at line 541 for affirmation. These branches crash for any message with laughter/affirmation tokens. Never executed in production. **Fix in Go:** Use `obs.Laughter[0]` (first slice element). Do not replicate the crash.

### 5. `BuildMirroring` pointer capture race (2/4 tracks)

**Convergence score: 2/4** (Track A + Track D)

- Track A (fd-fingerprint-concurrency-model): must not leak internal map references through lock
- Track D (fd-khumbu-icefall): `*ModeProfile` pointer captured under lock, fields read after release = fatal `throw("concurrent map read and map write")`

If `BuildMirroring()` does `fp.mu.Lock(); profile := fp.modes[mode]; fp.mu.Unlock(); // read profile.laughter`, a concurrent `Update()` can modify the map during iteration — Go runtime calls `throw()`, a non-recoverable fatal crash. **Fix:** Copy all `ModeProfile` fields into a local value struct under the lock, release, then generate text from the copy.

### 6. EMA operator order and alpha boundary precision (2/4 tracks)

**Convergence score: 2/4** (Track A + Track D)

- Track A (fd-ema-float-accumulation-parity): verified bit-identical with correct operator form
- Track D (fd-san-tracking-accumulation): `old*(1-alpha)+new*alpha` must not be refactored to `old+alpha*(new-old)` (catastrophic cancellation). Alpha `n >= 5` applies to pre-increment n — switch at 6th message, not 5th.

Track A confirmed EMA is bit-identical when the operator form is preserved. Track D identified the precision gap: which `n` (pre- or post-increment) triggers the alpha switch. Python reads n before incrementing, so `n >= 5` applies to the value before `profile["n"] = n + 1`. The effective switch is at the 6th message (n=5 going in). **Fix:** Preserve operator form exactly. Use pre-increment n for alpha check.

## Domain-Expert Insights (Track A)

### Clean bills of health (important for scoping)
- **RE2 compatibility confirmed:** All ~50 regex patterns are RE2-safe (no lookahead/lookbehind/backreferences). Emoji ranges compile identically in Go.
- **EMA arithmetic verified:** Bit-identical between Python and Go for a 20-step sequence when operator form is preserved.
- **Mutex design correct:** `sync.Mutex` on `Fingerprint` is the right granularity.
- **Word boundary behavior:** Identical for all English-text patterns.

### Key Track A findings not in convergence
- Mode context note strings must be copied character-for-character (they enter LLM system prompts directly)
- All `map[string]int` fields need explicit `make()` after JSON unmarshal

## Parallel-Discipline Insights (Track B)

### New findings from orthogonal domains
- **`UpdateCadence` + `Update` TOCTOU window** (SPC agent): separate lock acquisitions allow interleaving that corrupts cadence-message-count correlation during bursts. Fix: `UpdateWithCadence(obs, burstSize)` combined method.
- **`intensifier`/`hedge` singular/plural mismatch** (localization agent): Python maps `"intensifiers"` observable to `"intensifier"` profile key. Go struct must use `json:"intensifier"` (singular) on `ModeProfile`, `Intensifiers` (plural) on `Observables`.
- **`strings.Fields` not `strings.Split`** (forensic linguistics agent): Python `text.split()` matches Go `strings.Fields(text)`. `strings.Split(text, " ")` breaks on leading whitespace.
- **`message_length` and `emoji_count` omitted from brainstorm** (localization agent): Both appear in `compute_observables` output and must be in the Go `Observables` struct.
- **`BuildMirroring` guard must be inside lock** (SPC agent): `message_count < 3` check must happen after lock acquisition.

## Structural Insights (Track C)

### Song dynasty tea assessment — premature classification risk
Mode classification runs inside `compute_observables`. Currently safe because mode doesn't gate observable extraction. If someone adds mode-conditional extraction later, the coupling becomes a P1 anchoring bug. Document this as a design invariant.

### Polynesian wayfinding — absent mode staleness
Per-mode EMA has no decay for absent modes. A mode unseen for 100 messages retains its stale profile indefinitely. Known limitation, not a porting bug. Document for future consideration.

### Medieval bell founding — spectral compatibility
The JSON wire format is like a tuned bell: all numeric fields must agree in precision. Float serialization diverges at the byte level (Python `0.39199999999999996` vs Go `0.392`). Golden-file tests must compare decoded float64 values, not raw JSON strings.

### Duplicate laughter labels are intentional
Both `\bhaha(?:ha)*\b` and `\bahaha\b` return label `"haha"`. A message with "ahaha" increments the counter by 2. Go must not deduplicate labels.

## Frontier Patterns (Track D)

### Girih pattern duality — dual-representation architecture
The `global` keyword collision (Go reserved word → struct field must be `Global` with `json:"global"` tag) is a non-obvious failure. IDE autocomplete won't add the tag. A table-driven struct tag test (assert 15 ModeProfile fields each have matching JSON tags against the Python keylist) catches this class of error automatically.

### San tracking — the observation-to-instruction pipeline must preserve inferential coherence
The four-stage pipeline (extract → classify → accumulate → instruct) mirrors the San tracker's chain from spoor to pursuit decision. Each stage's output must be valid input for the next. The alpha discontinuity at n=5 (sensitivity jumps UP) is counterintuitive but intentional — golden tests must encode this explicitly at n=4, n=5, n=6.

### Khumbu icefall — minimal mutex, never held during string generation
`BuildMirroring` must copy fields under lock, release, then generate text. This resolves both the pointer-capture P0 and the contention P1 (lock held during string concatenation blocks concurrent `Update` calls). Single fix, two issues resolved.

## Synthesis Assessment

**Overall quality of the brainstorm:** Strong. The approach (literal port, JSON wire compatibility, thread-safe Fingerprint) is correct. The 7 key decisions are well-reasoned. The brainstorm correctly identifies the concurrent operation constraint as the primary design driver.

**Highest-leverage improvement:** Add `NewModeProfile()` constructor with mandatory map initialization, and add a table-driven struct tag test asserting all 15 ModeProfile fields + 4 Fingerprint top-level fields have correct JSON tags matching the Python keylist. These two changes prevent the two highest-convergence P0s (nil map panic, field name drift).

**Surprising finding:** The Python crash bug in `build_instant_mirroring` (lines 536-542) — `.keys()` called on a list. This code has never executed successfully in production, meaning no user has ever benefited from instant mirroring when their first messages contain laughter tokens. The Go port is an opportunity to fix this silently.

**Semantic distance value:** The outer tracks (C/D) produced qualitatively different insights from the inner tracks (A/B). Track A confirmed RE2 compatibility and EMA bit-parity (reassurance). Track B found the `emoji_density` byte/rune divergence and `UpdateCadence` TOCTOU (actionable implementation bugs). Track C found the Python crash bug and duplicate-label preservation requirement (source-code archaeology). Track D found the alpha boundary pre/post-increment ambiguity and the copy-under-lock pattern for `BuildMirroring` (concurrency architecture). Each track's most valuable finding was distinct — no redundancy.

## Consolidated P0 Checklist for Write-Plan

1. [ ] `NewModeProfile()` initializes all maps with `make(map[string]int)` — no nil maps ever
2. [ ] Never use `omitempty` on vocabulary counter map fields
3. [ ] `ensureMaps()` called after JSON unmarshal
4. [ ] `ClassifyMode` and `DetectCurrentMode` use canonical priority slice for tie-breaking
5. [ ] `emoji_density` uses `utf8.RuneCountInString(text)`, not `len(text)`
6. [ ] `message_length` uses `utf8.RuneCountInString(text)` for parity
7. [ ] `BuildInstantMirroring` uses `obs.Laughter[0]`, not `.keys()` — fix the Python bug
8. [ ] `BuildMirroring` copies ModeProfile fields under lock, releases, generates text from copy
9. [ ] EMA uses `old*(1-alpha) + new*alpha` operator form exactly
10. [ ] Alpha check uses pre-increment n (`n >= 5` before `n = n + 1`)
11. [ ] All Fingerprint mutations share single `sync.Mutex` (including `UpdateCadence`)
12. [ ] Table-driven struct tag test: 15 ModeProfile fields + 4 Fingerprint fields match Python keys

## Consolidated P1 Checklist for Write-Plan

1. [ ] Go `\w`/`\b` are ASCII-only — document English-text assumption
2. [ ] `UpdateWithCadence(obs, burstSize)` combined method for atomic paired updates
3. [ ] `intensifier`/`hedge` singular JSON tags on ModeProfile, plural field names on Observables
4. [ ] Use `strings.Fields(text)` not `strings.Split(text, " ")`
5. [ ] `message_length` and `emoji_count` in Observables struct
6. [ ] `BuildMirroring` guard `< 3` inside lock acquisition
7. [ ] Mode context note strings copied character-for-character
8. [ ] Duplicate laughter labels preserved (no deduplication)
9. [ ] `is_multi_sentence` uses `regexp.Split(text, -1)` to preserve trailing empties
10. [ ] `go test -race` with 50 concurrent goroutines on same Fingerprint
11. [ ] Golden-file comparison uses decoded float64 equality, not byte-string diff
12. [ ] Mode weights as named constants (`weightEmotional = 3`, etc.)
