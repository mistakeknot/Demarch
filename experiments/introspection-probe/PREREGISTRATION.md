# Pre-registration — Introspection Probe (Step 2)

> Locked **before** running activation capture on real weights. The design lives in
> [`DESIGN.md`](DESIGN.md); this file fixes the falsifiable claims, the locus-selection
> rule, and the controls so the analysis is not retrofitted to the data. Amendments after
> first capture must be logged in the "Amendments" section with a date and reason.

Status at lock time: GPU-independent analysis core (`src/probe.py`) implemented and tested
(10 tests, CPU-only). Activation capture + steering (`capture_activations`,
`steer_and_reelicit`) are interface stubs pending the GPU host (DESIGN §7). Behavioral
seed: the merged Step-1 logs (`../calibration-eval`) supply per-item correctness and
verbalized confidence.

## Subjects & data

- **Model tier:** a single small open-weight Hermes that fits the RTX 4090 in bf16
  (~7-8B; DESIGN §7). The exact checkpoint is confirmed present on the NousResearch HF org
  before locking the run (portal API access ≠ weight access). Mechanistic ladder is capped
  at this tier — a known asymmetry vs the behavioral ladder.
- **Items:** the same stimuli and correctness labels as Step 1 — `interest_domain.jsonl`
  plus the public-benchmark items already scored — so the internal signal is evaluated on
  exactly the behavioral footing.
- **Locus (pre-registered):** read at the **answer-commitment token** (the token fixing the
  MC letter). Secondary, reported separately, not part of the primary test: the
  confidence-number token (reading vs writing the report). Layers: full sweep; the reported
  primary locus is the **single layer with peak out-of-fold decoding AUROC on a held-out
  split**, selected by `layer_sweep` under nested cross-validation (no double-dipping).

## Hypotheses

| ID | Link (DESIGN §3) | Claim | Falsifiable test | Primary statistic |
|----|------|-------|------|------|
| **H1** | Existence | An internal signal encodes the model's *own* correctness | out-of-fold probe type-2 AUROC > 0.5 after difficulty controls | `ProbeResult.auroc`, difficulty-partialled |
| **H2** | Headroom | The internal signal knows more than the report says | `meta_d′(internal) > meta_d′(verbalized)` | paired bootstrap CI on the difference |
| **H3** | Coupling | The report **reads from** the signal | steering shifts verbalized confidence monotonically in α | slope of stated-conf vs α, vs random-direction control |
| **H4** | Domain | Grounding/headroom differ by `domain_type` | H1/H2 effect sizes vary across domains (ties to RQ2) | per-domain AUROC / meta-d′ gap |

**H3 makes the null informative:** if the decodable signal shifts under steering but the
report does not move, that *is* the finding — stated confidence is post-hoc/confabulated.
H3 is not "supported vs failed"; it is "grounded vs confabulated."

## Analysis plan

1. **Capture** activations at the locus over all items, all layers (`capture_activations`).
2. **H1:** `fit_confidence_probe` per layer (`layer_sweep`); pick the primary locus by peak
   held-out AUROC; report AUROC with item-difficulty (per-item public-benchmark difficulty
   / cross-model disagreement) partialled out.
3. **H2:** put internal, verbalized, and (if available) logprob signals on one type-2 SDT
   footing via `_calmetrics`; paired bootstrap over items for `meta_d′(internal) −
   meta_d′(verbalized)`.
4. **Dissociation set:** `dissociation_set(internal_conf, verbalized_conf)` → the Probe-C
   focus items (internal-high/verbal-low and internal-low/verbal-high).
5. **H3:** `confidence_direction` (diff-of-means, raw space) → `steer_and_reelicit` over an
   α-grid at the primary layer; fit the stated-conf-vs-α slope on the dissociation set and
   on the full set.
6. **H4:** repeat H1/H2 within each `domain_type`.

## Controls (preempt the reviewer — DESIGN §8)

- **Difficulty leakage:** partial out item difficulty; prefer items where samples/models
  disagree (own-uncertainty varies with input held fixed) so the probe cannot be reading
  input difficulty alone.
- **Double-dipping:** probe predictions are always out-of-fold; locus chosen on held-out
  AUROC under nested CV; never fit and evaluate on the same items.
- **Steering validity (H3):** norm-matched **random-direction** control (must do nothing);
  capability sanity check (steering must not merely break the model); cross-check whether
  the *answer* also changes (shared correctness signal vs report-only knob).
- **Temporal ordering:** confidence is verbalized *after* the answer in the prompt, so the
  answer-token signal genuinely precedes the report — supports a "leads/reads-from" reading
  if H3 holds.

## Decision rules

- Headline sequence **H2 → H3** (DESIGN §11 Q3): H2 (headroom) is cheaper and already a
  strong "knows more than it says" result; H3 (coupling) is the deeper but more
  failure-prone grounding claim. Report H2 regardless of H3 outcome.
- Effect sizes with bootstrap CIs over items; no NHST thresholds beyond the H1 chance
  baseline. Per-domain cells inherit Step-1's small-n caveat — reported as directional.

## Amendments

_None yet. Log dated changes here if the plan changes after first capture._
