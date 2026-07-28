---
title: A ratio guard cannot see a shortfall
date: 2026-07-28
category: verification
supersedes_section: 2026-07-25-unattended-work-needs-a-stopped-signal.md § "alarm thresholds have two failure modes"
---

# A ratio guard cannot see a shortfall

## The claim being revised

`2026-07-25-unattended-work-needs-a-stopped-signal.md` argued that an alarm
threshold has two failure modes — too loose and it misses the failure, too tight
and it fires on legitimate change — and that the fix is to derive the threshold
from the data rather than pick it by feel. That reasoning produced interchart's
collapse guard: refuse to write when a scan returns under 50% of the previous
artefact's node count, a figure derived from 12 commits of history (worst
legitimate drop −22.9%, observed failure −97.6%).

The derivation was sound. The guard works. **It is also structurally incapable of
catching the defect that actually occurred**, and no re-tuning would have fixed
that.

## The worked example

`scan.js` located the Clavain hub with `path.join(ROOT, 'os', 'clavain')` —
hardcoded lowercase. macOS resolves that case-insensitively; Linux does not. So
the same commit, run on two machines:

| Machine | Nodes | Edges |
|---|---|---|
| Clavain (macOS) | 244 | 320 |
| zklw (Linux) | **219** | **287** |

219/244 = **0.90**. The guard's floor is 0.50. It was never close to firing —
and it should not have been, because a guard that trips at 0.90 would fire on
every real consolidation, which is exactly the "too tight" failure the original
doctrine warned about.

Both settings are wrong because **the question is unanswerable from the output**.
A 10% smaller diagram is what you see when the estate genuinely shrank by 10%,
and it is also what you see when the scanner silently failed to find one input.
Counting the result cannot distinguish those two worlds. There is no threshold
that separates them, so tuning is not the lever.

## The revision

**A ratio guard measures output. It can only detect failures that change output
by more than legitimate change does.** That makes it correct for catastrophe —
249 nodes to 6 — and blind to everything smaller. Do not ask it to do more; a
tighter number buys nothing but false alarms.

**Shortfall is detectable at the input, not the output.** A missing directory is
not a smaller estate. It is a question the tool could not answer, and the tool
knows that at the moment it happens. So:

> **Every generator must distinguish "this input was absent" from "this input was
> empty", and treat the former as fatal by default.**

Not a warning. A warning on stderr scrolls past in a 40-line generator run, which
is precisely how the Clavain hub disappeared for days.

## What this looks like in practice

`interchart/scripts/generate.sh` now has three guards, in this order:

| Guard | Detects | Exit |
|---|---|---|
| 1 — wrong root | the caller passed a non-monorepo path | 2 |
| **0 — missing input** | **an input the scanner asked for was absent** | **4** |
| 2 — collapse / floor | the scan returned implausibly little | 3 |

Guard 0 runs *before* the counting guards because it is strictly more
informative: it names the input that went missing, where a count can only say
"smaller than expected". `scan.js` marks content-dropping absences with a
`missing-input:` prefix; absences with a documented fallback (Interforge → an
external reference node) stay ordinary warnings. The escape hatch is
`INTERCHART_ALLOW_MISSING=1`, deliberately opt-in, because silently tolerating an
absent input is the entire defect.

## The wider pattern this belongs to

This is the fourth instance in one week of **correct where authored, wrong where
run**:

1. `interverse-inventory.yml` — gated its real steps behind `[ -d interverse ]`,
   which is never true on a runner because the monorepo gitignores `interverse/`.
   Green for months, checking nothing.
2. `generate.sh refuses bad input` — its `conftest.py` imported
   `interverse/_shared`, a separate repo absent from a standalone checkout, so
   collection aborted before any test ran. Passed locally; red from the day it
   was added.
3. `check-kimi-version-parity.py` — would have reported success after inspecting
   zero plugins, in the one checkout where zero plugins is the normal state.
4. `scan.js` — this one.

The common shape is not carelessness. In every case the artefact was correct in
the environment where it was written and reviewed, and the environment where it
*ran* differed in a way nobody modelled: a gitignore, a sibling repo, a
case-sensitive filesystem, an empty checkout.

**The generalisation: a check is only real where it runs.** Verifying it locally
verifies the local environment. So every check needs a way to say "I could not
run here" that is distinguishable from "I ran and found nothing wrong" — the
vacuity guard (`--require-plugins N` → exit 2), the missing-input guard (exit 4),
and the "did this workflow ever produce a non-skipped run" audit are all the same
idea applied at three different layers.

## The layer this does *not* cover

A generator whose output legitimately differs per machine is a separate problem,
and guard 0 does not solve it. Measured 2026-07-28 across the estate:

| Generator | Clavain | zklw |
|---|---|---|
| `gen-interverse-inventory.py` | 62 plugins, 67 warnings | 65 plugins, 77 warnings |
| `gen-skill-prefix-table.py` | 56 plugins, 81 commands | 55 plugins, **131** commands |
| `build-architecture-map.py` | 61 plugins, 26 warnings | 27 warnings |
| `interchart` scan | 249 nodes | 253 nodes |

Every one differs, because the two checkouts genuinely contain different
directories. Where the artefact is **tracked** — `ARCHITECTURE.json`,
`docs/diagrams/ecosystem.html` — that guarantees churn: each machine overwrites
the other's version, forever, and neither is wrong. Guard 0 cannot help, because
no input is missing; the estates really are different.

That needs a different answer — one designated generating machine, or a manifest
of expected inputs so "different" becomes "detectably incomplete". Tracked as a
separate item; recorded here so the two problems do not get conflated.
